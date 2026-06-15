"""Configuration centrale : chemins, noms de colonnes, catégories.

Tout ce qui est "magique" (chaînes répétées, chemins en dur) vit ici,
pour qu'une modification de schéma se fasse à un seul endroit.
"""
from pathlib import Path

# --- Chemins -----------------------------------------------------------------
# BASE_DIR = racine du projet (dossier parent de src/)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "menu.csv"
OUTPUT_DIR = BASE_DIR / "output"

CSV_SEP = ";"

# --- Colonnes du CSV ---------------------------------------------------------
COL_LUNCH = "FL_ON_LUNCH"
COL_DINNER = "FL_ON_DINNER"
COL_CATEGORY = "LB_CATEGORY"
COL_NAME = "LB_DISH_NAME"
COL_SHORT = "LB_DISH_SHORT_DESC"
COL_LONG = "LB_DISH_LONG_DESC"
COL_PRICE = "NBR_DISH_PRICE"

# Ordre canonique des colonnes (utilisé pour la sauvegarde et l'éditeur)
MENU_COLUMNS = [
    COL_LUNCH,
    COL_DINNER,
    COL_CATEGORY,
    COL_NAME,
    COL_SHORT,
    COL_LONG,
    COL_PRICE,
]


# --- Catégories --------------------------------------------------------------
class Category:
    COCKTAIL = "Cocktail"
    DESSERT = "Dessert"
    ENTREE = "Entrée"
    PLAT = "Plats"
    SUGGESTION = "Suggestions du chef"


ALL_CATEGORIES = [
    Category.COCKTAIL,
    Category.DESSERT,
    Category.ENTREE,
    Category.PLAT,
    Category.SUGGESTION,
]

# Sections imprimées dans chaque carte (titre affiché -> catégorie source)
LUNCH_SECTIONS = [
    ("Suggestions du chef", Category.SUGGESTION),
    ("Entrée", Category.ENTREE),
    ("Plat", Category.PLAT),
    ("Dessert", Category.DESSERT),
]

DINNER_SECTIONS = [
    ("Suggestions du chef", Category.SUGGESTION),
    ("Desserts maison", Category.DESSERT),
    ("Cocktails du moment", Category.COCKTAIL),
]

# Texte de la formule midi (centralisé pour éviter le "18€50" en dur)
LUNCH_FORMULA_PRICE = "18€50"
LUNCH_FORMULA_SUBTITLE = "(entrée + plat ou plat + dessert)"
LUNCH_FORMULA_FOOTNOTE = "du lundi au vendredi sauf jours fériés"
