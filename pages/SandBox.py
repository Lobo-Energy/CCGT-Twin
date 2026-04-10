"""
SandBox.py — Simulateur interactif du jumeau numérique.
Les sliders sont initialisés avec les valeurs météo réelles à la première visite.
"""

import streamlit as st
from src.config import apply_global_settings, afficher_heure_sync
from src.i18n import init_language
from src.api import update_meteo
from src.models import getPuissance

# ---------------------------------------------------------------------------
# Initialisation globale
# ---------------------------------------------------------------------------

apply_global_settings()
texts   = init_language()
content = texts["SandBox"]

DEBIT = 12

# ---------------------------------------------------------------------------
# Récupération des données météo (déjà en cache depuis Home.py)
# ---------------------------------------------------------------------------

if "donnees" not in st.session_state or st.session_state.donnees is None:
    success = update_meteo()
    if not success:
        st.error("Données météo indisponibles. Vérifiez votre connexion.")
        st.stop()

d = st.session_state.donnees

if d is None:
    st.error("Données météo indisponibles. Vérifiez votre connexion.")
    st.stop()

# ---------------------------------------------------------------------------
# Initialisation des sliders avec les valeurs météo — une seule fois
# CRITIQUE : affectation directe AVANT création des widgets
# ---------------------------------------------------------------------------

if "sliders_initialises" not in st.session_state:
    st.session_state["val_slider_temp_air"] = float(d["t_air"])
    st.session_state["val_slider_humidite"] = float(d["hum"])
    st.session_state["val_slider_pression"] = float(d["pres"])
    st.session_state["val_slider_temp_eau"] = float(d["t_eau"])
    st.session_state["val_slider_fogging"]  = 0
    st.session_state["sliders_initialises"] = True

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

st.title(content["titre"])

col_titre, col_bouton = st.columns([3, 1], vertical_alignment="center")

with col_titre:
    afficher_heure_sync(d["last_update"], content["label_synchro"])

with col_bouton:
    if st.button(content["label_bouton"]):
        if "sliders_initialises" in st.session_state:
            del st.session_state["sliders_initialises"]
        update_meteo()
        d = st.session_state.donnees
        if d is None:
            st.error("Données météo indisponibles. Vérifiez votre connexion.")
            st.stop()
        st.session_state["val_slider_temp_air"] = float(d["t_air"])
        st.session_state["val_slider_humidite"] = float(d["hum"])
        st.session_state["val_slider_pression"] = float(d["pres"])
        st.session_state["val_slider_temp_eau"] = float(d["t_eau"])
        st.session_state["val_slider_fogging"]  = 0
        st.session_state["sliders_initialises"] = True

# ---------------------------------------------------------------------------
# Calculs — p_base sur météo réelle, max_p sur valeurs courantes des sliders
# ---------------------------------------------------------------------------

with st.spinner(content["spinner_jumeau"]):
    p_base = getPuissance(
        d["t_air"], d["pres"], d["hum"], d["t_eau"]
    )
    max_p = getPuissance(
        st.session_state["val_slider_temp_air"],
        st.session_state["val_slider_pression"],
        st.session_state["val_slider_humidite"],
        st.session_state["val_slider_temp_eau"],
        f_fogging=st.session_state["val_slider_fogging"] * DEBIT,
    )

# ---------------------------------------------------------------------------
# Sliders — créés APRÈS l'initialisation session_state
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.slider(
        f"{content['label_temp_air']} (°C)",
        min_value=-15, max_value=40,
        key="val_slider_temp_air",
    )
    st.slider(
        f"{content['label_temp_eau']} (°C)",
        min_value=5, max_value=40,
        key="val_slider_temp_eau",
    )
with col2:
    st.slider(
        f"{content['label_humidite']} (%)",
        min_value=0, max_value=100,
        key="val_slider_humidite",
    )
    st.slider(
        f"{content['label_pression']} (mbara)",
        min_value=800, max_value=1200,
        key="val_slider_pression",
    )

st.slider(content["label_slider"], min_value=0, max_value=6, key="val_slider_fogging")

# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------

col_sans, col_avec = st.columns(2)
with col_sans:
    st.metric(content["label_puissance_base"], f"{p_base:.2f} MW")
with col_avec:
    diff = max_p - p_base
    st.metric(
        label=content["label_puissance_modifie"],
        value=f"{max_p:.2f} MW",
        delta=f"{diff:.2f} MW",
    )