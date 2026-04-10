"""
Previsions.py — Prévisions de puissance maximale à J+1 ou J+2.
"""

import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from src.config import apply_global_settings
from src.i18n import init_language
from src.api import update_meteo, getPrevisions
from src.models import getPuissance

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

apply_global_settings()
texts   = init_language()
content = texts["Previsions"]

update_meteo()

MAE        = 1.6
DEBIT      = 12
MAX_POMPES = 6


# ---------------------------------------------------------------------------
# Calcul des prévisions
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, max_entries=2)
def getMeteoPrevisionsCompletes(nb_jours: int) -> list[dict] | None:
    """
    Calcule la puissance optimale pour chaque créneau de 15 min.
    Les données météo sont récupérées via getPrevisions() dans api.py.

    Args:
        nb_jours: 1 = demain, 2 = après-demain.

    Returns:
        Liste de dicts par créneau quart-horaire, ou None en cas d'erreur.
    """
    try:
        previsions = getPrevisions(nb_jours)
        if previsions is None:
            return None

        temps = previsions["temps"]
        t_ext = previsions["t_ext"]
        h_ext = previsions["h_ext"]
        p_ext = previsions["p_ext"]
        t_eau = previsions["t_eau"]

        # Calcul vectorisé : 96 créneaux × 7 configs → 672 prédictions
        nb_configs  = MAX_POMPES + 1
        idx_creneau = np.repeat(np.arange(96), nb_configs)
        idx_pompe   = np.tile(np.arange(nb_configs), 96)

        all_pmax = getPuissance(
            t_ext[idx_creneau], p_ext[idx_creneau],
            h_ext[idx_creneau], t_eau[idx_creneau],
            f_fogging=(idx_pompe * DEBIT).astype(float),
        )
        all_pmax   = np.array(all_pmax).reshape(96, nb_configs)
        p_base_arr = all_pmax[:, 0]

        resultats = []
        for i in range(96):
            best_nb = 0
            for nb_p in range(1, nb_configs):
                if all_pmax[i, nb_p] > (all_pmax[i, best_nb] + 1.5):
                    best_nb = nb_p

            p_calc = round(float(all_pmax[i, best_nb]), 2)
            p_b    = round(float(p_base_arr[i]), 2)

            resultats.append({
                "creneau":    temps[i].split("T")[1],
                "t_ext":      float(t_ext[i]),
                "p_ext":      float(p_ext[i]),
                "h_ext":      float(h_ext[i]),
                "t_eau":      float(t_eau[i]),
                "fog":        best_nb,
                "p_base":     p_b,
                "pmax":       p_calc,
                "delta":      round(p_calc - p_b, 2),
                "pmax_haute": round(p_calc + MAE, 2),
                "pmax_basse": round(p_b   - MAE, 2),
            })
        return resultats

    except Exception as e:
        st.error(f"❌ {content['err_previsions']} : {e}")
        return None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

jours_decalage = {
    content["label_date_1"]: 1,
    content["label_date_2"]: 2,
}

option   = st.selectbox(content["menu_date"], options=list(jours_decalage))
nb_jours = jours_decalage[option]

date_prev       = datetime.date.today() + datetime.timedelta(days=nb_jours)
titre_graphique = f"{content['label_graph']} {date_prev.strftime('%d/%m/%Y')}"

with st.spinner(content["spinner_previsions"]):
    data = getMeteoPrevisionsCompletes(nb_jours)

# ---------------------------------------------------------------------------
# Graphique Altair — axes et tooltips localisés
# ---------------------------------------------------------------------------

if data:
    df    = pd.DataFrame(data)
    y_min = df["pmax"].min() - 5
    y_max = df["pmax"].max() + 5
    scale = alt.Scale(domain=[y_min, y_max])

    # Tooltips localisés
    tooltips = [
        alt.Tooltip("creneau:N", title=content["label_tooltip_heure"]),
        alt.Tooltip("pmax:Q",    title=content["label_tooltip_pmax"]),
        alt.Tooltip("p_base:Q",  title=content["label_tooltip_base"]),
        alt.Tooltip("fog:Q",     title=content["label_tooltip_fog"]),
    ]

    bande = (
        alt.Chart(df)
        .mark_area(opacity=0.3, color="lightblue")
        .encode(
            x=alt.X("creneau:N", sort=None, title=content["label_axe_x"]),
            y=alt.Y("pmax_basse:Q", scale=scale, title=content["label_axe_y"]),
            y2="pmax_haute:Q",
        )
    )

    line_base = (
        alt.Chart(df)
        .mark_line(color="lightgrey", strokeDash=[5, 5])
        .encode(
            x=alt.X("creneau:N", sort=None, title=content["label_axe_x"]),
            y=alt.Y("p_base:Q",  scale=scale, title=content["label_axe_y"]),
            tooltip=tooltips,
        )
    )

    line_opti = (
        alt.Chart(df)
        .mark_line(color="#1f77b4", strokeWidth=3)
        .encode(
            x=alt.X("creneau:N", sort=None, title=content["label_axe_x"]),
            y=alt.Y("pmax:Q",    scale=scale, title=content["label_axe_y"]),
            tooltip=tooltips,
        )
    )

    chart = (
        (bande + line_base + line_opti)
        .properties(title=titre_graphique, width="container", height=400)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    # Tableau avec colonnes traduites
    with st.expander(content["label_detail"]):
        df_affichage = df.rename(columns={
            "creneau":    content["col_creneau"],
            "t_ext":      content["col_t_ext"],
            "p_ext":      content["col_p_ext"],
            "h_ext":      content["col_h_ext"],
            "t_eau":      content["col_t_eau"],
            "fog":        content["col_fog"],
            "p_base":     content["col_p_base"],
            "pmax":       content["col_pmax"],
            "delta":      content["col_delta"],
            "pmax_haute": content["col_pmax_haute"],
            "pmax_basse": content["col_pmax_basse"],
        })
        st.dataframe(df_affichage, use_container_width=True)