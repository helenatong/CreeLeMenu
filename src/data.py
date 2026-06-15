"""Couche d'accès aux données du menu (CSV).

Responsabilité unique : lire / écrire / filtrer le catalogue de plats.
Aucune dépendance à Streamlit ni à reportlab -> testable isolément.
"""
from __future__ import annotations

import pandas as pd

from . import config


def load_menu(path=config.DATA_FILE) -> pd.DataFrame:
    """Charge le catalogue, nettoie et type les colonnes."""
    df = pd.read_csv(path, sep=config.CSV_SEP)

    # Supprime une éventuelle colonne d'index parasite ("Unnamed: 0")
    # héritée d'anciennes sauvegardes faites sans index=False.
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Garantit la présence de toutes les colonnes attendues.
    for col in config.MENU_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Typage : flags en entiers 0/1, prix en numérique.
    for flag in (config.COL_LUNCH, config.COL_DINNER):
        df[flag] = (
            pd.to_numeric(df[flag], errors="coerce").fillna(0).astype(int).clip(0, 1)
        )
    df[config.COL_PRICE] = pd.to_numeric(df[config.COL_PRICE], errors="coerce")

    # Colonnes texte : une colonne entièrement vide (ex. LB_DISH_LONG_DESC)
    # serait sinon inférée en float64 par pandas, ce que st.column_config
    # .TextColumn refuse d'éditer. On force donc le type "string".
    for col in (config.COL_CATEGORY, config.COL_NAME, config.COL_SHORT, config.COL_LONG):
        df[col] = df[col].astype("string")

    df = (
        df[config.MENU_COLUMNS]
        .sort_values([config.COL_CATEGORY, config.COL_NAME])
        .reset_index(drop=True)
    )
    return df


def save_menu(df: pd.DataFrame, path=config.DATA_FILE) -> None:
    """Écrit le catalogue. index=False évite l'empilement de colonnes."""
    df[config.MENU_COLUMNS].to_csv(
        path, sep=config.CSV_SEP, index=False, encoding="utf-8"
    )


def dishes_for_service(df: pd.DataFrame, service: str) -> pd.DataFrame:
    """Plats activés pour un service ('lunch' ou 'dinner')."""
    flag = config.COL_LUNCH if service == "lunch" else config.COL_DINNER
    return df[df[flag] == 1]


def names_by_category(df: pd.DataFrame, category: str) -> list[str]:
    """Liste triée des noms de plats d'une catégorie (pour les multiselect)."""
    return (
        df.loc[df[config.COL_CATEGORY] == category, config.COL_NAME]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )


def select_dishes(df: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """Sous-ensemble du catalogue correspondant aux noms choisis, dans l'ordre."""
    selected = df[df[config.COL_NAME].isin(names)].copy()
    # Conserve l'ordre de sélection de l'utilisateur.
    selected[config.COL_NAME] = pd.Categorical(
        selected[config.COL_NAME], categories=names, ordered=True
    )
    return selected.sort_values(config.COL_NAME).reset_index(drop=True)
