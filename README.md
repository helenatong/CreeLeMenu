# Création du menu

Application Streamlit pour composer et exporter en PDF les cartes du midi et du soir d'un restaurant.

## Structure

```
restaurant-menu/
├── app.py            # Interface Streamlit (UI uniquement)
├── src/
│   ├── config.py     # Chemins, noms de colonnes, catégories, sections
│   ├── data.py       # Lecture / écriture / filtrage du catalogue CSV
│   └── pdf.py        # Génération des PDF (renvoie des bytes)
├── data/
│   └── menu.csv      # Catalogue des plats (source de vérité)
├── output/           # PDF générés (optionnel)
└── requirements.txt
```

## Installation (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancement

```powershell
streamlit run app.py
```

## Utilisation

- **Modifier la carte** : éditer le catalogue complet, cocher Midi/Soir pour la disponibilité, sauvegarder.
- **Menu du midi / soir** : sélectionner les plats par section, générer puis télécharger le PDF.

## Format du CSV (`data/menu.csv`, séparateur `;`, sans colonne d'index)

| Colonne | Type | Description |
|---|---|---|
| FL_ON_LUNCH | 0/1 | Disponible le midi |
| FL_ON_DINNER | 0/1 | Disponible le soir |
| LB_CATEGORY | texte | Cocktail / Dessert / Entrée / Plats / Suggestions du chef |
| LB_DISH_NAME | texte | Nom du plat |
| LB_DISH_SHORT_DESC | texte | Description courte (imprimée) |
| LB_DISH_LONG_DESC | texte | Description longue (réserve) |
| NBR_DISH_PRICE | nombre | Prix en euros |
