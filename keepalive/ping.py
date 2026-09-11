"""
ping.py — Visite l'app Streamlit avec un navigateur headless pour
réinitialiser le compteur d'inactivité de Streamlit Community Cloud
(mise en veille automatique après 12h sans trafic réel).

Indépendant du code de l'app (pages/, src/) — dépendances propres
dans keepalive/requirements.txt.
"""

import sys

from playwright.sync_api import sync_playwright

APP_URL = "https://ccgt-twin.streamlit.app"


def ping(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=60_000, wait_until="networkidle")
        page.wait_for_timeout(5_000)
        browser.close()


if __name__ == "__main__":
    try:
        ping(APP_URL)
        print(f"OK — {APP_URL} visité avec succès.")
    except Exception as e:
        print(f"Echec du ping : {e}")
        sys.exit(1)
