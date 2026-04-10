"""
config.py — Configuration globale de l'application CCGT-Twin.
Gère les paramètres de page Streamlit, les secrets de configuration du site,
et les utilitaires partagés entre les pages.
"""

import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Configuration de la page Streamlit
# ---------------------------------------------------------------------------

def apply_global_settings() -> None:
    """Configure la page Streamlit et le logo global."""
    st.set_page_config(
        page_title="CCGT-Twin",
        page_icon="./assets/logo.svg",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.logo(image="./assets/logo.svg", size="large")


# ---------------------------------------------------------------------------
# Secrets / configuration géographique du site
# ---------------------------------------------------------------------------

def get_site_config() -> dict:
    """
    Retourne la configuration géographique depuis les secrets Streamlit.
    Repli sur des valeurs par défaut si secrets.toml est absent (dev local).
    """
    defaults = {
        "LAT_AIR":   43.4, "LON_AIR":   4.9,
        "LAT_WATER": 43.4, "LON_WATER": 4.9,
    }
    try:
        return dict(defaults, **st.secrets.get("site_config", {}))
    except Exception:
        return defaults


# ---------------------------------------------------------------------------
# Utilitaire — Affichage de l'heure de synchronisation
# ---------------------------------------------------------------------------

def afficher_heure_sync(ts: float, label: str, height: int = 25) -> None:
    """
    Affiche l'heure du dernier appel API dans le fuseau horaire local
    du navigateur de l'utilisateur.

    Le timestamp est stocké en UTC (time.time()) côté serveur et converti
    à l'affichage via JS — gère automatiquement heure d'été / hiver.

    Args:
        ts:     Timestamp Unix UTC (time.time()).
        label:  Texte du label (ex: "Dernière synchronisation").
        height: Hauteur du composant HTML en pixels (défaut: 25).
    """
    components.html(
        f"""
        <p style="font-size:0.85rem; color:gray; margin:0; padding:0;">
            {label} : <span id="heure_sync"></span>
        </p>
        <script>
            const date = new Date({ts} * 1000);
            document.getElementById("heure_sync").innerText =
                date.toLocaleTimeString();
        </script>
        """,
        height=height,
    )