"""
Monitoring.py — Dashboard temps réel d'aide à la décision énergétique.
Évalue l'opportunité financière d'une montée/descente de charge
en croisant les déséquilibres réseau (Elia) et le coût marginal calculé.
"""

import asyncio
import datetime as dt
import time
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo

import dateutil.parser
import httpx
import numpy as np
import pandas as pd
import streamlit as st

from src.config import apply_global_settings
from src.i18n import init_language
from src.api import update_meteo, getMeteo, getTemperatureEau
from src.models import getPuissance, getRendement

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

apply_global_settings()
texts   = init_language()
content = texts["Monitoring"]

update_meteo()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CONFIG = {
    "PLAN_EXCEL":      "Plan_de_charge.xlsx",
    "SI_BUFFER_SIZE":  45,
    "Pgaz":            35,
    "Pco2":            75,
    "VOM":             4,
    "UPDATE_INTERVAL": 60,
    "P_MIN":           200,
    "TEST_CHARGE":     225,
    "GRADIENT_MW_MIN": 13.0,
    "LHV_VOL":         38.2,
}

_COULEURS_RECO = {
    "success": ("#d4edda", "#155724"),
    "warning": ("#fff3cd", "#856404"),
    "error":   ("#f8d7da", "#721c24"),
}

# ---------------------------------------------------------------------------
# Fonctions utilitaires — API Elia
# ---------------------------------------------------------------------------

def charger_plan() -> list | None:
    """Charge le plan de charge depuis le fichier Excel."""
    try:
        df = pd.read_excel(CONFIG["PLAN_EXCEL"], sheet_name=0, header=None, nrows=7)
        return pd.to_numeric(df.iloc[6, 1:97], errors="coerce").fillna(0).tolist()
    except Exception as e:
        st.warning(f"⚠️ {content['err_plan_charge']} : {e}")
        return None


async def get_elia_data(
    client: httpx.AsyncClient, dataset_id: str, nb: int = 1
) -> dict | list | None:
    """Interroge l'API Open Data d'Elia."""
    url       = f"https://opendata.elia.be/api/explore/v2.1/catalog/datasets/{dataset_id}/records"
    order_col = "predictiontimeutc" if dataset_id == "ods147" else "datetime"
    params    = {"limit": nb, "order_by": f"{order_col} DESC"}
    try:
        r = await client.get(url, params=params, timeout=10)
        if r.status_code == 200:
            res = r.json().get("results", [])
            return res if nb > 1 else (res[0] if res else None)
    except Exception as e:
        st.warning(f"⚠️ {content['err_api_elia']} ({dataset_id}) : {e}")
    return None


# ---------------------------------------------------------------------------
# Fonctions utilitaires — Calcul
# ---------------------------------------------------------------------------

def check_timing(api_data: dict, delta_p: float) -> dict:
    """Calcule la fenêtre d'action et le statut d'opportunité."""
    gradient        = CONFIG["GRADIENT_MW_MIN"]
    temps_rampe_min = delta_p / gradient
    maintenant      = dt.datetime.now(dt.timezone.utc)
    qualite         = api_data.get("predictionquality", 0)
    t_proche        = dateutil.parser.isoparse(api_data["predictions_forecastedtimeutc"])
    t_cible         = dateutil.parser.isoparse(api_data["systemimbalanceforecastdatetime"])
    delai_proche    = (t_proche - maintenant).total_seconds() / 60
    delai_cible     = (t_cible  - maintenant).total_seconds() / 60

    if qualite < 80:
        statut = "⚠️ SIGNAL DOUTEUX"
    elif 0 < delai_proche <= (temps_rampe_min + 0.5):
        statut = "🚀 ACTION IMMÉDIATE"
    elif qualite >= 80 and temps_rampe_min < delai_cible <= (temps_rampe_min + 5):
        statut = "⏱️ ANTICIPATION"
    else:
        statut = "VEILLE"

    return {
        "statut":       statut,
        "temps_rampe":  temps_rampe_min,
        "delai_proche": delai_proche,
        "qualite":      qualite,
    }


def generer_deck_performance(
    t_ext, p_ext, h_ext, t_eau, Pmin, Pmaxdd
) -> tuple[pd.DataFrame, float]:
    """Génère la table de performance vectorisée pour tous les paliers de charge."""
    pmax_limite = getPuissance(t_ext, p_ext, h_ext, t_eau)
    Pmaxdd      = min(Pmaxdd, pmax_limite)
    Pmin        = max(Pmin, CONFIG["P_MIN"])
    nb_points   = max(1, int(Pmaxdd - Pmin) + 1)
    pts         = np.linspace(Pmin, Pmaxdd, nb_points)
    etas        = getRendement(
        pts,
        [t_ext] * nb_points, [p_ext] * nb_points,
        [h_ext] * nb_points, [t_eau] * nb_points,
    )
    hr     = 360_000 / etas
    consos = (pts * 3_600) / ((etas / 100) * CONFIG["LHV_VOL"])

    df = pd.DataFrame({
        "SP":                 [f"{p:.0f} MW" for p in pts],
        "Puissance (MW)":     np.round(pts,    2),
        "Rendement (%)":      np.round(etas,   2),
        "Heat Rate (kJ/kWh)": np.round(hr,     1),
        "Conso Gaz (Nm3/h)":  np.round(consos, 0),
    })
    return df, pmax_limite


def generer_perfo(t_ext, p_ext, h_ext, t_eau, puissance) -> float:
    """Calcule le heat rate (kJ/kWh) — retourne toujours un float."""
    eta = getRendement(puissance, t_ext, p_ext, h_ext, t_eau)
    return float(np.mean(360_000 / eta))


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def afficher_recommandation(decision: str, color: str) -> None:
    """Affiche le bloc de recommandation avec sauts de ligne respectés."""
    fond, texte   = _COULEURS_RECO[color]
    html_decision = decision.replace("\n", "<br>")
    st.markdown(
        f"""
        <div style="
            background-color:{fond}; color:{texte};
            border-radius:8px; padding:16px; line-height:2; font-size:1rem;
        ">{html_decision}</div>
        """,
        unsafe_allow_html=True,
    )


def afficher_dashboard() -> None:
    """
    Lit les données depuis session_state et les affiche.
    Appelée à chaque rerun — persistance pendant le countdown.
    """
    if "monitoring_data" not in st.session_state:
        st.info("⏳ Chargement des données en cours...")
        return

    d = st.session_state.monitoring_data

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric(content["label_p_act"], f"{d['prod_plan']} MW")
    m_col2.metric(content["label_p_min"], f"{CONFIG['P_MIN']:.2f} MW")
    m_col3.metric(content["label_p_max"], f"{d['pmax_limite']:.2f} MW")
    m_col4.metric(content["label_CM"],    f"{d['cm_moyen']:.2f} €/MWh")

    r_col1, r_col2 = st.columns(2)
    r_col1.metric(content["label_SI"],   f"{d['si_mw']:.2f} MW")
    r_col2.metric(content["label_prix"], f"{d['prix_mwh']:.2f} €/MWh")

    if d["opp_valable"]:
        st.metric(content["label_NC"], f"{d['new_cons']:.2f} MW")

    st.markdown(content["label_reco"])
    afficher_recommandation(f"{d['sym']} {d['decision']}", d["color"])

    if d["opp_valable"]:
        t_col1, t_col2 = st.columns(2)
        t_col1.write(content["label_T_Rampe"].format(delta_p_aff=d["delta_p_aff"]))
        t_col2.write(content["label_T_5"].format(reste_t5=d["reste_t5"]))
        with st.expander(content["label_Details"]):
            st.dataframe(d["tableau_perf"], use_container_width=True)

    heure_belge = datetime.now(ZoneInfo("Europe/Brussels"))
    st.caption(
        content["label_MAJ"].format(
            heure_maj=heure_belge.strftime("%H:%M:%S"),
            qualite_api=d["qualite_api"],
        )
    )


# ---------------------------------------------------------------------------
# Cycle de mise à jour
# ---------------------------------------------------------------------------

async def run_update() -> None:
    """
    Effectue un cycle complet : API → calculs → stockage session_state.
    Météo via api.py centralisé, données réseau via Elia en async.
    """
    # Météo centralisée depuis api.py
    meteo_data = getMeteo()
    t_eau      = getTemperatureEau()

    if meteo_data is None or t_eau is None:
        st.warning(f"⚠️ {content['err_donnees_incompletes']}")
        return

    t_air, hum, press, _ = meteo_data

    # Données Elia en async
    async with httpx.AsyncClient() as client:
        si_elia, price_data, api_data = await asyncio.gather(
            get_elia_data(client, "ods169"),
            get_elia_data(client, "ods161"),
            get_elia_data(client, "ods147"),
        )

    if not all([si_elia, price_data, api_data]):
        st.warning(f"⚠️ {content['err_donnees_incompletes']}")
        return

    # Données réseau réelles depuis Elia
    si_mw    = si_elia.get("systemimbalance", 0)
    prix_mwh = price_data.get("price") or price_data.get("imbalanceprice", 0)

    prod_plan    = CONFIG["TEST_CHARGE"]
    prod_avec_SI = prod_plan + round(float(si_mw), 2)
    P_H_DEM      = max(prod_plan, prod_avec_SI)
    P_B_DEM      = min(prod_plan, prod_avec_SI)

    tableau_perf, pmax_limite = generer_deck_performance(
        t_air, press, hum, t_eau, P_B_DEM, P_H_DEM
    )
    hr_values = tableau_perf["Heat Rate (kJ/kWh)"]
    cm_moyen  = (
        ((hr_values / 3_600) * ((CONFIG["Pgaz"] * 1.11) + (0.202 * CONFIG["Pco2"])))
        + CONFIG["VOM"]
    ).mean()

    delta_p = abs(max(CONFIG["P_MIN"], min(prod_avec_SI, pmax_limite)) - prod_plan)
    timing  = check_timing(api_data, delta_p)
    statut, temps_rampe, delai_proche, qualite_api = (
        timing["statut"], timing["temps_rampe"],
        timing["delai_proche"], timing["qualite"],
    )

    t_proche       = dateutil.parser.isoparse(api_data.get("predictions_forecastedtimeutc"))
    maintenant_api = dateutil.parser.isoparse(api_data.get("predictiontimeutc"))
    reste_t5       = (t_proche - maintenant_api).total_seconds() / 60
    delta_p_aff    = delta_p / CONFIG["GRADIENT_MW_MIN"]

    opportunite      = (prix_mwh > cm_moyen) if si_mw > 0 else (cm_moyen > prix_mwh)
    gain_estime      = abs(prix_mwh - cm_moyen) * (delta_p / 60) * temps_rampe
    new_cons         = prod_plan + delta_p if prod_avec_SI > prod_plan else prod_plan - delta_p
    hr_new_cons      = generer_perfo(t_air, press, hum, t_eau, new_cons)
    cm_new_cons      = (
        ((hr_new_cons / 3_600) * ((CONFIG["Pgaz"] * 1.11) + (0.202 * CONFIG["Pco2"])))
        + CONFIG["VOM"]
    )
    gain_stab_estime = abs(prix_mwh - cm_new_cons) * (delta_p / 60)

    texte_gain = (
        content["label_action"]
        .replace("\\n", "\n")
        .format(
            gain_estime=gain_estime,
            gain_stab_estime=gain_stab_estime,
            delta_p_aff=delta_p_aff,
        )
    )

    if not opportunite:
        decision, sym, color, opp_valable = content["label_refus"], "🔴", "error",   False
    elif qualite_api < 80:
        decision, sym, color, opp_valable = content["label_wait"], "🟡", "warning", False
    else:
        decision, sym, color, opp_valable = texte_gain,            "🟢", "success", True

    st.session_state.monitoring_data = {
        "prod_plan":    prod_plan,
        "pmax_limite":  pmax_limite,
        "cm_moyen":     cm_moyen,
        "si_mw":        float(si_mw),
        "prix_mwh":     float(prix_mwh),
        "new_cons":     new_cons,
        "decision":     decision,
        "sym":          sym,
        "color":        color,
        "opp_valable":  opp_valable,
        "delta_p_aff":  delta_p_aff,
        "reste_t5":     reste_t5,
        "tableau_perf": tableau_perf,
        "qualite_api":  qualite_api,
    }


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    st.title(content["titre"])

    if "last_update_ts" not in st.session_state:
        st.session_state.last_update_ts = 0.0

    elapsed   = time.time() - st.session_state.last_update_ts
    remaining = max(0, int(CONFIG["UPDATE_INTERVAL"] - elapsed))

    if elapsed >= CONFIG["UPDATE_INTERVAL"] or st.session_state.last_update_ts == 0.0:
        with st.spinner("Mise à jour en cours..."):
            asyncio.run(run_update())
        st.session_state.last_update_ts = time.time()
        remaining = CONFIG["UPDATE_INTERVAL"]

    afficher_dashboard()

    st.caption(content["label_Timer"].format(seconds=remaining))
    time.sleep(1)
    st.rerun()


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()