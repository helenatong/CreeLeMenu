"""Interface Streamlit : composition et export des cartes midi / soir.

L'app ne fait QUE de l'UI : toute la logique vit dans src/.
Pattern d'export : on génère les bytes du PDF au clic, on les stocke en
session_state, puis on affiche un st.download_button (le serveur n'écrit
plus de fichier "fantôme" que personne ne peut récupérer).
"""
from datetime import date

import streamlit as st

from src import config, data, pdf, storage

ss = st.session_state


# --- Chargement du catalogue -------------------------------------------------
def get_catalogue():
    """Charge le catalogue une fois par session, le garde éditable en mémoire."""
    if "catalogue" not in ss or ss["catalogue"] is None:
        ss["catalogue"] = data.load_menu()
    return ss["catalogue"]


def reload_catalogue():
    ss["catalogue"] = data.load_menu()


# --- Composants réutilisables ------------------------------------------------
def service_tab(service: str, sections, build_pdf, label: str, state_key: str):
    """Construit un onglet de service (midi ou soir).

    - un multiselect par section, pré-rempli avec les plats activés (flag)
    - un bouton de génération -> bytes en session_state
    - un bouton de téléchargement
    """
    catalogue = get_catalogue()
    enabled = data.dishes_for_service(catalogue, service)

    chosen = {}
    for title, category in sections:
        options = data.names_by_category(catalogue, category)
        default = data.names_by_category(enabled, category)
        chosen[title] = st.multiselect(title, options=options, default=default)

    if st.button(label, key=f"btn_{service}"):
        section_dfs = {
            title: data.select_dishes(catalogue, names)
            for title, names in chosen.items()
        }
        ss[state_key] = build_pdf(section_dfs)
        st.success(f"{label} ✅ — votre PDF est prêt, téléchargez-le ci-dessous.")

    if ss.get(state_key):
        st.download_button(
            label="⬇️ Télécharger le PDF",
            data=ss[state_key],
            file_name=f"menu_{service}_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            key=f"dl_{service}",
        )


# --- Page --------------------------------------------------------------------
def main() -> None:
    st.set_page_config(layout="wide", page_title="Création du menu")
    st.title("Création du menu")

    tab_midi, tab_soir, tab_carte = st.tabs(
        ["☀️ Menu du midi", "🌙 Menu du soir", "🔧 Modifier la carte"]
    )

    with tab_midi:
        st.header("Composer la carte du midi")
        service_tab(
            service="lunch",
            sections=config.LUNCH_SECTIONS,
            build_pdf=pdf.build_lunch_pdf,
            label="Créer le menu du midi",
            state_key="pdf_lunch_bytes",
        )

    with tab_soir:
        st.header("Composer la carte du soir")
        service_tab(
            service="dinner",
            sections=config.DINNER_SECTIONS,
            build_pdf=pdf.build_dinner_pdf,
            label="Créer le menu du soir",
            state_key="pdf_dinner_bytes",
        )

    with tab_carte:
        st.header("Catalogue des plats")
        st.caption(
            "Cochez FL_ON_LUNCH / FL_ON_DINNER pour rendre un plat disponible "
            "au service correspondant, puis sauvegardez."
        )
        edited = st.data_editor(
            get_catalogue(),
            num_rows="dynamic",
            use_container_width=True,
            column_order=[
                config.COL_LUNCH,
                config.COL_DINNER,
                config.COL_CATEGORY,
                config.COL_NAME,
                config.COL_SHORT,
                config.COL_PRICE,
            ],
            column_config={
                config.COL_LUNCH: st.column_config.CheckboxColumn("Midi"),
                config.COL_DINNER: st.column_config.CheckboxColumn("Soir"),
                config.COL_CATEGORY: st.column_config.SelectboxColumn(
                    "Catégorie", options=config.ALL_CATEGORIES, required=True
                ),
                config.COL_NAME: st.column_config.TextColumn("Plat", required=True),
                config.COL_SHORT: st.column_config.TextColumn("Description"),
                config.COL_PRICE: st.column_config.NumberColumn(
                    "Prix (€)", format="%.2f", min_value=0
                ),
            },
            key="editor_catalogue",
        )

        if st.button("💾 Sauvegarder le catalogue"):
            # Les flags peuvent revenir en booléens depuis l'éditeur : on normalise.
            for flag in (config.COL_LUNCH, config.COL_DINNER):
                edited[flag] = edited[flag].fillna(0).astype(int)
            data.save_menu(edited)
            try:
                published = storage.persist_remote()
            except Exception as e:
                published = False
                st.warning(
                    "Sauvegarde locale faite, mais la publication en ligne a "
                    f"échoué : {e}"
                )
            reload_catalogue()
            if published:
                st.success("Catalogue sauvegardé et publié en ligne ✅")
            else:
                st.success("Catalogue sauvegardé ✅")


if __name__ == "__main__":
    main()
