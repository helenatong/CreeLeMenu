"""Persistance du catalogue.

En local (développement) : on écrit simplement dans data/menu.csv.
En ligne (Streamlit Community Cloud) : le disque est éphémère, donc à chaque
sauvegarde on réécrit aussi data/menu.csv DANS le dépôt GitHub via l'API.
Le dépôt sert ainsi de "base de données" gratuite et persistante.

L'activation se fait uniquement par la présence de secrets Streamlit
(section [github]). Sans secrets -> mode local automatique.
"""
from __future__ import annotations

import base64

import requests
import streamlit as st

from . import config

GITHUB_API = "https://api.github.com"
COMMIT_MESSAGE = "Mise à jour du menu via l'application"


def _github_config():
    """Lit st.secrets['github'] ; renvoie None si non configuré (mode local)."""
    try:
        gh = st.secrets["github"]
        return {
            "token": gh["token"],
            "repo": gh["repo"],            # ex. "monpseudo/restaurant-menu"
            "path": gh.get("path", "data/menu.csv"),
            "branch": gh.get("branch", "main"),
        }
    except Exception:
        return None


def is_remote_enabled() -> bool:
    return _github_config() is not None


def persist_remote(local_path=config.DATA_FILE) -> bool:
    """Pousse le CSV local vers GitHub si configuré. Renvoie True si publié."""
    cfg = _github_config()
    if cfg is None:
        return False

    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API}/repos/{cfg['repo']}/contents/{cfg['path']}"

    # L'API GitHub exige le SHA du fichier existant pour le remplacer.
    sha = None
    r = requests.get(url, headers=headers, params={"ref": cfg["branch"]}, timeout=15)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload = {
        "message": COMMIT_MESSAGE,
        "content": content_b64,
        "branch": cfg["branch"],
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    return True
