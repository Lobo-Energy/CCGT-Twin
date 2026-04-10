"""
models.py — Chargement des modèles ML et calculs via les jumeaux numériques.

Les features temporelles (Mois, Heure) sont calculées automatiquement
depuis datetime.now() si non fournies — aucun changement requis dans les pages.
"""

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime


# ---------------------------------------------------------------------------
# Chargement des modèles
# ---------------------------------------------------------------------------

@st.cache_resource
def load_model():
    """Charge et met en cache le modèle de prédiction de puissance maximale."""
    try:
        return joblib.load("./config/jumeau_pmax_v3_anonymisation.joblib")
    except FileNotFoundError:
        st.error("❌ Modèle de puissance introuvable : ./config/jumeau_pmax_v3_anonymisation.joblib")
        st.stop()


@st.cache_resource
def load_rendement():
    """Charge et met en cache le modèle de prédiction du rendement."""
    try:
        return joblib.load("./config/jumeau_rendement_v3_anonymisation.joblib")
    except FileNotFoundError:
        st.error("❌ Modèle de rendement introuvable : ./config/jumeau_rendement_v3_anonymisation.joblib")
        st.stop()


# ---------------------------------------------------------------------------
# Calcul de puissance
# ---------------------------------------------------------------------------

def getPuissance(
    t_ext, p_ext, h_ext, t_eau,
    f_fogging: float = 0,
    anti_ice: int = 0,
) -> float | np.ndarray:
    """
    Prédit la puissance maximale (MW) à partir des conditions environnementales.

    Accepte des scalaires ou des arrays NumPy/listes pour le calcul vectorisé.
    Le cast .astype(float) garantit la compatibilité XGBoost (pas de type object).

    Args:
        t_ext:     Température extérieure (°C).
        p_ext:     Pression extérieure (hPa).
        h_ext:     Humidité relative (%).
        t_eau:     Température eau condenseur (°C).
        f_fogging: Débit de fogging (L/h), défaut 0.
        anti_ice:  Anti-icing actif (0/1), défaut 0.

    Returns:
        Puissance prédite en MW — float si scalaire, ndarray sinon.
    """
    model     = load_model()
    is_scalar = not isinstance(t_ext, (list, pd.Series, np.ndarray))

    input_df = pd.DataFrame({
        "Outside_Temperature":          [t_ext]     if is_scalar else t_ext,
        "Outside_Pressure":             [p_ext]     if is_scalar else p_ext,
        "Outside_Moisture":             [h_ext]     if is_scalar else h_ext,
        "Condenser_Water_Inlet_T_Mean": [t_eau]     if is_scalar else t_eau,
        "GT_Fogging_Flow":              [f_fogging] if is_scalar else f_fogging,
        "GT_Anti_Ice":                  [anti_ice]  if is_scalar else anti_ice,
    }).astype(float)

    preds = model.predict(input_df)
    return float(preds[0]) if is_scalar else preds


# ---------------------------------------------------------------------------
# Calcul du rendement
# ---------------------------------------------------------------------------

def getRendement(
    puissance, t_ext, p_ext, h_ext, t_eau,
    mois: int | None = None,
    heure: int | None = None,
) -> float | np.ndarray:
    """
    Prédit le rendement thermique (%) à partir des conditions et de la puissance.

    Les features temporelles (Mois, Heure) sont calculées automatiquement
    depuis datetime.now() si non fournies — permet d'appeler la fonction
    sans modifier les pages existantes.

    Args:
        puissance: Puissance actuelle (MW) — scalaire ou array.
        t_ext:     Température extérieure (°C).
        p_ext:     Pression extérieure (hPa).
        h_ext:     Humidité relative (%).
        t_eau:     Température eau condenseur (°C).
        mois:      Mois (1-12). Si None → datetime.now().month
        heure:     Heure (0-23). Si None → datetime.now().hour

    Returns:
        Rendement prédit en % — float si scalaire, ndarray sinon.
    """
    model     = load_rendement()
    is_scalar = not isinstance(t_ext, (list, pd.Series, np.ndarray))

    # Features temporelles — calculées automatiquement si non fournies
    now   = datetime.now()
    mois  = mois  if mois  is not None else now.month
    heure = heure if heure is not None else now.hour

    # Longueur du batch pour les features scalaires répétées
    n = 1 if is_scalar else len(t_ext)

    input_df = pd.DataFrame({
        "P_nette":                      [puissance] if is_scalar else puissance,
        "Outside_Temperature":          [t_ext]     if is_scalar else t_ext,
        "Outside_Pressure":             [p_ext]     if is_scalar else p_ext,
        "Outside_Moisture":             [h_ext]     if is_scalar else h_ext,
        "Condenser_Water_Inlet_T_Mean": [t_eau]     if is_scalar else t_eau,
        "Mois":                         [mois]  * n,
        "Heure":                        [heure] * n,
    }).astype(float)

    rendement = model.predict(input_df)
    return float(rendement[0]) if is_scalar else rendement