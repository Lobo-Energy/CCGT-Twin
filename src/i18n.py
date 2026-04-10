"""
i18n.py — Gestion des traductions et de la langue de l'interface.
"""

import json
import streamlit as st


@st.cache_data
def load_translations(lang: str) -> dict:
    """
    Charge le fichier JSON de traductions pour la langue donnée.
    Repli sur le français si le fichier est introuvable.

    Args:
        lang: Code langue (ex: 'fr', 'en').

    Returns:
        Dictionnaire des traductions.
    """
    try:
        with open(f"locales/{lang}.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Fichier de traduction introuvable : locales/{lang}.json — repli sur le français.")
        with open("locales/fr.json", encoding="utf-8") as f:
            return json.load(f)


def init_language() -> dict:
    """
    Initialise le sélecteur de langue dans la sidebar.

    Returns:
        Dictionnaire complet des traductions pour la langue sélectionnée.
    """
    LANGUAGES = {
        "fr": "🇫🇷 Français",
        "en": "🇬🇧 English",
        "es": "🇪🇸 Español",
        "it": "🇮🇹 Italiano",
    }

    if "lang" not in st.session_state:
        st.session_state.lang = "fr"

    current_idx = list(LANGUAGES).index(st.session_state.lang)
    new_lang = st.sidebar.selectbox(
        "Langue",
        options=list(LANGUAGES),
        format_func=lambda x: LANGUAGES[x],
        index=current_idx,
    )

    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

    return load_translations(st.session_state.lang)
