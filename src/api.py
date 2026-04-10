"""
api.py — Appels API météo centralisés et gestion du session_state.

Une seule fonction publique météo : getMeteo()
Une seule fonction publique eau   : getTemperatureEau()

Logique température eau (selon NEAR_SEA dans secrets) :
    True  → API Marine Open-Meteo (mer/océan)
    False → Estimation depuis température air (rivière, lac...)
"""

import time
import requests
import streamlit as st

from src.config import get_site_config
from src.i18n import load_translations


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _get_texts() -> dict:
    """
    Retourne les textes dans la langue courante du session_state.
    Repli sur le français si la langue n'est pas encore initialisée.
    """
    return load_translations(st.session_state.get("lang", "fr"))


def _estimer_temperature_eau(t_air: float, t_moy_jour: float) -> float:
    """
    Estime la température d'un cours d'eau inland depuis la température air.
    Formule empirique : pondération air actuel (30%) + moyenne journalière (70%)
    + offset thermique +2°C (inertie thermique du cours d'eau).

    Args:
        t_air:      Température air actuelle (°C).
        t_moy_jour: Température air moyenne journalière (°C).

    Returns:
        Température eau estimée (°C), minimum 0.5°C.
    """
    return max(0.5, round((t_air * 0.3) + (t_moy_jour * 0.7) + 2.0, 1))


# ---------------------------------------------------------------------------
# Fetch purs (sans appel UI — compatibles @st.cache_data)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def _fetch_meteo_air(lat: float, lon: float) -> tuple | None:
    """
    Récupère les conditions météo air via Open-Meteo.

    Returns:
        Tuple (t_air °C, humidité %, pression hPa, t_moy_jour °C) ou None.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,surface_pressure"
        f"&daily=temperature_2m_mean&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data    = response.json()
        current = data["current"]
        return (
            current["temperature_2m"],
            current["relative_humidity_2m"],
            current["surface_pressure"],
            data["daily"]["temperature_2m_mean"][0],
        )
    except requests.RequestException:
        return None


@st.cache_data(ttl=600)
def _fetch_meteo_mer(lat: float, lon: float) -> float | None:
    """
    Récupère la température de surface de la mer via API Marine Open-Meteo.

    Returns:
        Température de surface (°C) ou None.
    """
    url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={lat}&longitude={lon}&current=sea_surface_temperature"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()["current"]["sea_surface_temperature"]
    except requests.RequestException:
        return None


@st.cache_data(ttl=900)
def _fetch_previsions_air(
    lat: float, lon: float, nb_jours: int
) -> dict | None:
    """
    Récupère les prévisions météo air à 15 min pour J+1 ou J+2.

    Returns:
        Dict avec clés 'minutely_15' et 't_moy_jour', ou None.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&minutely_15=surface_pressure,temperature_2m,relative_humidity_2m"
        f"&daily=temperature_2m_mean"
        f"&timezone=auto&forecast_days={nb_jours}"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "minutely_15": data["minutely_15"],
            "t_moy_jour":  data["daily"]["temperature_2m_mean"][0],
        }
    except requests.RequestException:
        return None


@st.cache_data(ttl=900)
def _fetch_previsions_mer(
    lat: float, lon: float, nb_jours: int
) -> list | None:
    """
    Récupère les prévisions température mer horaires pour J+1 ou J+2.

    Returns:
        Liste des températures horaires (24 dernières valeurs) ou None.
    """
    url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=sea_surface_temperature&forecast_days={nb_jours}"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()["hourly"]["sea_surface_temperature"][-24:]
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# API publiques — avec gestion des erreurs localisées
# ---------------------------------------------------------------------------

def getMeteo() -> tuple | None:
    """
    Retourne les conditions météo air actuelles.

    Returns:
        Tuple (t_air °C, humidité %, pression hPa, t_moy_jour °C) ou None.
    """
    config = get_site_config()
    result = _fetch_meteo_air(config["LAT_AIR"], config["LON_AIR"])
    if result is None:
        st.warning(f"⚠️ {_get_texts()['Global']['err_api_air']}")
    return result


def getTemperatureEau() -> float | None:
    """
    Retourne la température eau selon la config NEAR_SEA :
    - True  → API Marine Open-Meteo
    - False → Estimation depuis température air

    Returns:
        Température eau (°C) ou None.
    """
    config   = get_site_config()
    near_sea = config.get("NEAR_SEA", True)

    if near_sea:
        result = _fetch_meteo_mer(config["LAT_WATER"], config["LON_WATER"])
        if result is None:
            st.warning(f"⚠️ {_get_texts()['Global']['err_api_eau']}")
        return result
    else:
        meteo = _fetch_meteo_air(config["LAT_AIR"], config["LON_AIR"])
        if meteo is None:
            st.warning(f"⚠️ {_get_texts()['Global']['err_api_eau']}")
            return None
        t_air, _, _, t_moy_jour = meteo
        return _estimer_temperature_eau(t_air, t_moy_jour)


def getPrevisions(nb_jours: int) -> dict | None:
    """
    Retourne les prévisions météo complètes (air + eau) pour J+1 ou J+2.
    Utilisée par Previsions.py — centralisée ici pour éviter les appels
    directs aux API dans les pages.

    Args:
        nb_jours: 1 = demain, 2 = après-demain.

    Returns:
        Dict avec clés :
            'temps'     : liste des créneaux horaires
            't_ext'     : array températures air (96 valeurs)
            'h_ext'     : array humidités (96 valeurs)
            'p_ext'     : array pressions (96 valeurs)
            't_eau'     : array températures eau (96 valeurs)
        ou None en cas d'erreur.
    """
    import numpy as np

    config   = get_site_config()
    near_sea = config.get("NEAR_SEA", True)

    # Prévisions air
    air = _fetch_previsions_air(
        config["LAT_AIR"], config["LON_AIR"], nb_jours
    )
    if air is None:
        st.warning(f"⚠️ {_get_texts()['Global']['err_api_air']}")
        return None

    m15        = air["minutely_15"]
    t_moy_jour = air["t_moy_jour"]

    temps = m15["time"][-96:]
    t_ext = np.array(m15["temperature_2m"][-96:],       dtype=float)
    h_ext = np.array(m15["relative_humidity_2m"][-96:], dtype=float)
    p_ext = np.array(m15["surface_pressure"][-96:],     dtype=float)

    # Prévisions eau
    if near_sea:
        sst = _fetch_previsions_mer(
            config["LAT_WATER"], config["LON_WATER"], nb_jours
        )
        if sst is None:
            st.warning(f"⚠️ {_get_texts()['Global']['err_api_eau']}")
            return None
        t_eau = np.array([sst[i // 4] for i in range(96)], dtype=float)
    else:
        t_eau_val = _estimer_temperature_eau(float(np.mean(t_ext)), t_moy_jour)
        t_eau     = np.full(96, t_eau_val, dtype=float)

    return {
        "temps": temps,
        "t_ext": t_ext,
        "h_ext": h_ext,
        "p_ext": p_ext,
        "t_eau": t_eau,
    }


# ---------------------------------------------------------------------------
# Mise à jour centralisée du session_state météo
# ---------------------------------------------------------------------------

def update_meteo() -> bool:
    """
    Appelle getMeteo() et getTemperatureEau() et stocke les résultats
    dans st.session_state.

    Le timestamp est stocké en UTC (time.time()) pour conversion
    côté navigateur via JS (fuseau horaire local, heure été/hiver).

    Returns:
        True si la mise à jour a réussi, False sinon.
    """
    meteo_data = getMeteo()
    t_eau      = getTemperatureEau()

    if meteo_data is None or t_eau is None:
        st.error(f"❌ {_get_texts()['Global']['err_meteo_maj']}")
        return False

    t_air, hum, pres, _ = meteo_data

    st.session_state.update({
        "val_slider_temp_air": t_air,
        "val_slider_humidite": hum,
        "val_slider_pression": pres,
        "val_slider_temp_eau": t_eau,
        "val_slider_fogging":  0,
        "donnees": {
            "t_air":       t_air,
            "hum":         hum,
            "pres":        pres,
            "t_eau":       t_eau,
            "last_update": time.time(),
        },
    })
    return True