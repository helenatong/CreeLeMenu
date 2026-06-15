"""Génération des cartes PDF (midi / soir) — TENUE SUR UNE SEULE PAGE.

Principe : on mesure d'abord la hauteur totale du contenu, puis on calcule
un facteur d'échelle pour que tout rentre sur une page A5 paysage. Polices,
interlignes et espacements sont réduits proportionnellement. S'il y a peu de
plats, l'échelle reste à 1.0 (on ne grossit pas au-delà du design d'origine).

La même fonction `_render` sert à mesurer (canvas=None) et à dessiner, ce qui
garantit que mesure et rendu ne divergent jamais.
"""
from __future__ import annotations

import io

import pandas as pd
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from . import config

PAGE_SIZE = landscape(A5)
MARGIN_TOP = 30
MARGIN_BOTTOM = 24
PRICE_RIGHT_PAD = 60  # distance du bord droit pour aligner les prix

# Échelle plancher : en deçà, le texte deviendrait illisible -> on accepte
# de dépasser légèrement plutôt que de rendre la carte inutilisable.
MIN_SCALE = 0.45


class Style:
    """Toutes les métriques de mise en page, dérivées d'un facteur d'échelle."""

    def __init__(self, scale: float = 1.0):
        self.scale = scale
        self.f_title = ("Helvetica-Bold", 16 * scale)
        self.f_section = ("Helvetica-Bold", 14 * scale)
        self.f_formula_sub = ("Helvetica-Bold", 8 * scale)
        self.f_formula_note = ("Helvetica", 6 * scale)
        self.f_name = ("Helvetica-Bold", 10 * scale)
        self.f_desc = ("Helvetica-Oblique", 8 * scale)
        self.f_price = ("Helvetica", 8 * scale)
        self.line_h = 12 * scale
        self.gap_after_title = 6 * scale
        self.gap_after_section = 20 * scale
        self.sep_gap = 6 * scale
        self.sep_half_width = 100 * scale


def _format_price(value) -> str:
    """18.0 -> '18€', 8.5 -> '8,50€' (format français). NaN -> ''."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return ""
    if pd.isna(f):
        return ""
    if float(f).is_integer():
        return f"{int(f)}€"
    return f"{f:.2f}".replace(".", ",") + "€"


def _render(c, style: Style, *, lunch: bool, sections: dict) -> float:
    """Dessine la carte si `c` est un canvas, sinon mesure seulement.

    Renvoie la hauteur totale consommée (points). Aucun saut de page :
    tout est rendu sur une seule page.
    """
    width, height = PAGE_SIZE
    center_x = width / 2
    price_x = width - PRICE_RIGHT_PAD
    max_w = width - 2 * PRICE_RIGHT_PAD
    top = height - MARGIN_TOP
    used = 0.0  # hauteur consommée (croît vers le bas)

    def y() -> float:
        return top - used

    def centered(text: str, font, extra: float) -> None:
        nonlocal used
        if c is not None:
            c.setFont(*font)
            c.drawCentredString(center_x, y(), text)
        used += font[1] + extra

    def separator() -> None:
        nonlocal used
        used += style.sep_gap
        if c is not None:
            c.line(center_x - style.sep_half_width, y(),
                   center_x + style.sep_half_width, y())
        used += style.sep_gap

    def dish(name: str, desc: str, price: str) -> None:
        nonlocal used
        desc_text = f", {desc}" if desc else ""
        nw = stringWidth(name, *style.f_name)
        dw = stringWidth(desc_text, *style.f_desc)

        if nw + dw <= max_w:
            if c is not None:
                x = (width - (nw + dw)) / 2
                c.setFont(*style.f_name)
                c.drawString(x, y(), name)
                c.setFont(*style.f_desc)
                c.drawString(x + nw, y(), desc_text)
                c.setFont(*style.f_price)
                c.drawRightString(price_x, y(), price)
            used += style.line_h
            return

        # Description trop large : nom + prix sur une ligne, desc repliée dessous.
        if c is not None:
            c.setFont(*style.f_name)
            c.drawCentredString(center_x, y(), name)
            c.setFont(*style.f_price)
            c.drawRightString(price_x, y(), price)
        used += style.line_h
        if desc:
            lines = simpleSplit(desc, style.f_desc[0], style.f_desc[1], max_w)
            if c is not None:
                c.setFont(*style.f_desc)
            for line in lines:
                if c is not None:
                    c.drawCentredString(center_x, y(), line)
                used += style.line_h - 2 * style.scale

    def section(title: str, df: pd.DataFrame, separator_after: bool) -> None:
        nonlocal used
        if df.empty:
            return
        centered(title, style.f_section, extra=style.gap_after_title)
        for _, row in df.iterrows():
            dish(
                name=str(row[config.COL_NAME]),
                desc="" if pd.isna(row[config.COL_SHORT]) else str(row[config.COL_SHORT]),
                price=_format_price(row[config.COL_PRICE]),
            )
        if separator_after:
            separator()
        used += style.gap_after_section

    items = list(sections.items())
    if lunch:
        if items:
            t0, d0 = items[0]
            section(f"{t0} (hors formule)", d0, separator_after=True)
        centered(f"Formule du midi {config.LUNCH_FORMULA_PRICE}", style.f_title, 4 * style.scale)
        centered(config.LUNCH_FORMULA_SUBTITLE, style.f_formula_sub, 3 * style.scale)
        centered(config.LUNCH_FORMULA_FOOTNOTE, style.f_formula_note, 2 * style.scale)
        used += style.gap_after_section * 0.5
        rest = items[1:]
        for i, (t, d) in enumerate(rest):
            section(t, d, separator_after=(i < len(rest) - 1))
    else:
        for i, (t, d) in enumerate(items):
            section(t, d, separator_after=(i < len(items) - 1))

    return used


def _fit_style(*, lunch: bool, sections: dict) -> Style:
    """Trouve la plus grande échelle (<= 1.0) qui fait tenir le contenu."""
    available = PAGE_SIZE[1] - MARGIN_TOP - MARGIN_BOTTOM
    scale = 1.0
    for _ in range(12):
        used = _render(None, Style(scale), lunch=lunch, sections=sections)
        if used <= available:
            break
        # La hauteur varie ~linéairement avec l'échelle : on vise le ratio,
        # avec une petite marge de sécurité, puis on re-mesure (le repli de
        # texte peut changer légèrement la hauteur).
        scale = max(MIN_SCALE, scale * (available / used) * 0.97)
    return Style(scale)


def _build(*, lunch: bool, sections: dict, title: str) -> bytes:
    style = _fit_style(lunch=lunch, sections=sections)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    c.setTitle(title)
    _render(c, style, lunch=lunch, sections=sections)
    c.save()  # une seule page : on n'appelle jamais showPage()
    return buffer.getvalue()


def build_lunch_pdf(sections: dict) -> bytes:
    """Carte midi (1 page). sections : {titre_affiché: dataframe}, ordonné."""
    return _build(lunch=True, sections=sections, title="Menu du midi")


def build_dinner_pdf(sections: dict) -> bytes:
    """Carte soir (1 page). sections : {titre_affiché: dataframe}, ordonné."""
    return _build(lunch=False, sections=sections, title="Menu du soir")
