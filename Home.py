"""
Home.py — Page d'accueil de l'application CCGT-Twin.
"""

import streamlit as st
from src.config import apply_global_settings
from src.i18n import init_language
from src.api import update_meteo

# ---------------------------------------------------------------------------
# Initialisation — météo chargée en premier
# ---------------------------------------------------------------------------

apply_global_settings()
texts   = init_language()
content = texts["Home"]

# Chargement météo systématique (coût nul grâce au cache TTL=600)
update_meteo()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
<style>
.card-link {
    text-decoration: none !important;
    color: inherit !important;
    display: block;
    margin-bottom: 20px;
}
.module-card {
    background-color: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 12px;
    padding: 25px;
    min-height: 140px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    cursor: pointer;
}
.module-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.1);
    border-color: #ff4b4b;
}
.module-card:hover .card-title { color: #ff4b4b; }
.card-title {
    font-weight: bold;
    font-size: 1.2rem;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: color 0.3s ease;
}
.card-text { color: #5e6671; font-size: 0.95rem; line-height: 1.5; }
[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlock"] {
    align-items: flex-end;
    text-align: right;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

head_col1, _ = st.columns([0.8, 0.2])
with head_col1:
    st.title(content["titre"])
    st.subheader(content["sous_titre_1"])
    st.write(content["sous_titre_2"])

st.divider()

# ---------------------------------------------------------------------------
# Grille de modules
# ---------------------------------------------------------------------------

st.markdown(f"### {content['menu_titre']}")

MODULES = [
    {"icon": "🔍", "label": "Fogging",    "desc": content["menu_fog"], "target": "Fogging"},
    {"icon": "📈", "label": "Prévision",  "desc": content["menu_pre"], "target": "Previsions"},
    {"icon": "💰", "label": "Monitoring", "desc": content["menu_mon"], "target": "Monitoring"},
    {"icon": "🧪", "label": "SandBox",    "desc": content["menu_box"], "target": "SandBox"},
]

row1_cols = st.columns(2)
row2_cols = st.columns(2)

for col, module in zip(row1_cols + row2_cols, MODULES):
    with col:
        st.markdown(
            f"""
            <a href="{module['target']}" target="_self" class="card-link">
                <div class="module-card">
                    <div class="card-title">{module['icon']} {module['label']}</div>
                    <div class="card-text">{module['desc']}</div>
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.info(content["menu_info"], icon="ℹ️")
