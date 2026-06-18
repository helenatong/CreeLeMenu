"""Génération des cartes PDF (midi / soir) — UNE SEULE PAGE, REMPLIE AU MAX.

Format : A5 paysage + 3 cm de hauteur.

Auto-ajustement : on mesure la hauteur du contenu puis on calcule un facteur
d'échelle pour que le texte REMPLISSE la page (marges minimales en haut, bas,
droite). L'échelle peut dépasser 1.0 (police agrandie) quand il y a peu de
plats, ou descendre quand il y en a beaucoup — toujours sur une seule page.

L'agrandissement est plafonné horizontalement pour qu'aucun nom de plat ni
titre ne déborde, et pour que les noms ne chevauchent jamais la colonne des
prix (gouttière réservée symétriquement, bloc nom+desc centré dedans).

La même fonction `_render` sert à mesurer (canvas=None) et à dessiner.
"""
from __future__ import annotations

import io

import pandas as pd
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import getAscent, stringWidth
from reportlab.pdfgen import canvas

from . import config

# Page : A5 paysage, +3 cm en hauteur.
_W, _H = landscape(A5)
PAGE_SIZE = (_W, _H + 3 * cm)

# Marges volontairement faibles pour remplir la page.
MARGIN_TOP = 16
MARGIN_BOTTOM = 16
PRICE_RIGHT_PAD = 24   # marge droite (alignement des prix)
GAP_PRICE = 10         # espace mini entre le texte et le prix

MIN_SCALE = 0.45       # plancher de lisibilité
MAX_SCALE = 2.8        # plafond absolu (peu de plats)
SAFETY = 0.985         # vise légèrement sous la hauteur dispo


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


def _dish_row(row):
    name = str(row[config.COL_NAME])
    desc = "" if pd.isna(row[config.COL_SHORT]) else str(row[config.COL_SHORT])
    price = _format_price(row[config.COL_PRICE])
    return name, desc, price


def _render(c, style: Style, *, lunch: bool, sections: dict) -> float:
    """Dessine la carte si `c` est un canvas, sinon mesure seulement.

    Renvoie la hauteur consommée (du sommet du contenu vers le bas).
    Aucun saut de page.
    """
    width, height = PAGE_SIZE
    center_x = width / 2
    price_x = width - PRICE_RIGHT_PAD
    max_w = width - 2 * PRICE_RIGHT_PAD
    top = height - MARGIN_TOP - getAscent(style.f_section[0], style.f_section[1])
    used = 0.0

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
        price_w = stringWidth(price, *style.f_price)
        nw = stringWidth(name, *style.f_name)
        dw = stringWidth(desc_text, *style.f_desc)

        # Gouttière prix réservée des deux côtés -> bloc centré sans collision.
        allowed_block = max_w - 2 * (price_w + GAP_PRICE)

        if nw + dw <= allowed_block:
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

        # Nom (centré) + prix sur la 1re ligne ; description repliée en dessous.
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
            name, desc, price = _dish_row(row)
            dish(name, desc, price)
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


def _available(scale: float) -> float:
    """Hauteur utile pour `used` à une échelle donnée (marges + ascendante)."""
    s = Style(scale)
    return PAGE_SIZE[1] - MARGIN_TOP - MARGIN_BOTTOM - getAscent(
        s.f_section[0], s.f_section[1]
    )


def _max_scale_horizontal(*, lunch: bool, sections: dict) -> float:
    """Plafond d'échelle pour qu'aucun texte ne déborde en largeur.

    - textes centrés (titres, formule) : doivent tenir dans (largeur - marges)
    - ligne de plat : nom + prix ne doivent pas se chevaucher (gouttière 2x)
    """
    width = PAGE_SIZE[0]
    full = width - 2 * PRICE_RIGHT_PAD
    s1 = Style(1.0)
    cap = MAX_SCALE

    centered_texts = []  # (texte, police @scale1)
    items = list(sections.items())
    if lunch:
        if items:
            centered_texts.append((f"{items[0][0]} (hors formule)", s1.f_section))
        centered_texts.append((f"Formule du midi {config.LUNCH_FORMULA_PRICE}", s1.f_title))
        centered_texts.append((config.LUNCH_FORMULA_SUBTITLE, s1.f_formula_sub))
        centered_texts.append((config.LUNCH_FORMULA_FOOTNOTE, s1.f_formula_note))
        for t, _ in items[1:]:
            centered_texts.append((t, s1.f_section))
    else:
        for t, _ in items:
            centered_texts.append((t, s1.f_section))

    for text, font in centered_texts:
        w = stringWidth(text, *font)
        if w > 0:
            cap = min(cap, full / w)

    for df in sections.values():
        for _, row in df.iterrows():
            name, _desc, price = _dish_row(row)
            name_w = stringWidth(name, *s1.f_name)
            price_w = stringWidth(price, *s1.f_price)
            denom = name_w + 2 * (price_w + GAP_PRICE)
            if denom > 0:
                cap = min(cap, full / denom)

    return max(MIN_SCALE, cap)


def _fit_style(*, lunch: bool, sections: dict) -> Style:
    """Cherche l'échelle qui REMPLIT la page (peut agrandir ou réduire)."""
    hcap = _max_scale_horizontal(lunch=lunch, sections=sections)
    upper = min(MAX_SCALE, hcap)

    scale = 1.0
    for _ in range(20):
        used = _render(None, Style(scale), lunch=lunch, sections=sections)
        if used <= 0:
            break
        target = scale * (_available(scale) / used) * SAFETY
        target = max(MIN_SCALE, min(upper, target))
        if abs(target - scale) < 0.003:
            scale = target
            break
        scale = target

    # Garde-fou : garantir le maintien sur une seule page.
    for _ in range(8):
        used = _render(None, Style(scale), lunch=lunch, sections=sections)
        if used <= _available(scale) or scale <= MIN_SCALE:
            break
        scale = max(MIN_SCALE, scale * 0.97)

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