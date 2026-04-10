"""
Fogging.py — Analyse de l'impact du système de fogging sur la puissance.
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
content = texts["Fogging"]

DEBIT = 12

# Météo chargée systématiquement (cache TTL=600 → coût nul si déjà chargée)
update_meteo()

d = st.session_state.donnees

# Garde-fou
if d is None:
    st.error("Données météo indisponibles. Vérifiez votre connexion.")
    st.stop()

# Initialisation du slider pompes uniquement s'il n'existe pas encore
if "val_slider" not in st.session_state:
    st.session_state.val_slider = 0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_txt(nb: int, cle: str) -> str:
    """Retourne singulier ou pluriel selon nb."""
    return content[cle][0] if nb <= 1 else content[cle][1]

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

col_titre, col_bouton = st.columns(2, vertical_alignment="center")

with col_titre:
    st.subheader(content["titre"])
    afficher_heure_sync(d["last_update"], content["label_synchro"])

with col_bouton:
    st.markdown("<style>div.stButton {text-align: center;}</style>", unsafe_allow_html=True)
    if st.button(content["label_bouton"]):
        update_meteo()
        d = st.session_state.donnees
        if d is None:
            st.error("Données météo indisponibles. Vérifiez votre connexion.")
            st.stop()

# ---------------------------------------------------------------------------
# Calculs
# ---------------------------------------------------------------------------

with st.spinner(content["spinner_jumeau"]):
    p_base = getPuissance(d["t_air"], d["pres"], d["hum"], d["t_eau"])
    max_p  = getPuissance(
        d["t_air"], d["pres"], d["hum"], d["t_eau"],
        f_fogging=st.session_state.val_slider * DEBIT,
    )

# ---------------------------------------------------------------------------
# Tableau météo
# ---------------------------------------------------------------------------

stats = {
    content["label_temp_air"]: f"{d['t_air']} °C",
    content["label_pression"]: f"{d['pres']} mbara",
    content["label_humidite"]: f"{d['hum']} %",
    content["label_temp_eau"]: f"{d['t_eau']} °C",
}

rows_html = "".join(
    f"<tr><td>{k}</td><td class='valeur'>{v}</td></tr>"
    for k, v in stats.items()
)

st.markdown(f"""
<style>
    .no-border-table {{ width:100%; border-collapse:collapse !important; border:none !important; }}
    .no-border-table tr, .no-border-table td, .no-border-table th {{
        border:none !important; padding:8px 0;
    }}
    .valeur {{ text-align:right; }}
    .titre-tableau {{
        text-align:center; font-weight:bold;
        text-transform:uppercase; padding-bottom:10px;
    }}
</style>
<table class="no-border-table">
    <thead><tr><th colspan="2" class="titre-tableau">{content['label_meteo']}</th></tr></thead>
    <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Impact fogging
# ---------------------------------------------------------------------------

st.write(content["label_impact"])
st.slider(content["label_slider"], min_value=0, max_value=6, key="val_slider")

col_sans, col_avec = st.columns(2)
with col_sans:
    st.metric(content["label_sans"], f"{p_base:.2f} MW")
with col_avec:
    diff = max_p - p_base
    st.metric(
        label=content["label_avec"],
        value=f"{max_p:.2f} MW",
        delta=f"{diff:.2f} MW",
    )

label = get_txt(st.session_state.val_slider, "label_nb_pompe")
st.metric(content["label_etat"], f"{st.session_state.val_slider} {label}")