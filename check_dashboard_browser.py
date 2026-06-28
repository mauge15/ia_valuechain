#!/usr/bin/env python3
"""
Abre el dashboard en un navegador real y comprueba si cargó correctamente.

Instalación:
    pip install playwright
    playwright install chromium

Ejecución:
    python check_dashboard_browser.py

Resultado:
- Imprime OK o ERROR.
- Guarda una captura llamada dashboard_check.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://iavaluechain.streamlit.app/"
SCREENSHOT = Path("dashboard_check.png")

ERROR_TEXTS = [
    "This app has gone to sleep",
    "Oh no",
    "Error running app",
    "App is not running",
    "Page not found",
    "Connection error",
]


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})

        try:
            print(f"Abriendo: {URL}")
            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            # Espera a que Streamlit termine de cargar contenido visible.
            page.wait_for_load_state("networkidle", timeout=120_000)
            page.wait_for_timeout(5_000)

            body_text = page.locator("body").inner_text()
            final_url = page.url
            title = page.title()
            http_status = response.status if response else None

            page.screenshot(path=str(SCREENSHOT), full_page=True)

            print(f"HTTP inicial: {http_status}")
            print(f"URL final: {final_url}")
            print(f"Título: {title}")
            print(f"Captura: {SCREENSHOT.resolve()}")

            detected_errors = [
                text for text in ERROR_TEXTS
                if text.lower() in body_text.lower()
            ]

            # Streamlit suele renderizar al menos un contenedor principal.
            main_container = page.locator('[data-testid="stAppViewContainer"]')
            streamlit_loaded = main_container.count() > 0

            if detected_errors:
                print("ERROR: la página muestra un mensaje de fallo:")
                for error in detected_errors:
                    print(f"- {error}")
                return 2

            if not streamlit_loaded:
                print("ERROR: no se detectó el contenedor principal de Streamlit.")
                return 3

            if len(body_text.strip()) < 50:
                print("ERROR: la página cargó, pero casi no tiene contenido visible.")
                return 4

            print("OK: el dashboard se abrió y Streamlit renderizó contenido visible.")
            print("\nPrimeros 500 caracteres visibles:")
            print(body_text[:500])
            return 0

        except PlaywrightTimeoutError:
            try:
                page.screenshot(path=str(SCREENSHOT), full_page=True)
                print(f"Captura guardada: {SCREENSHOT.resolve()}")
            except Exception:
                pass
            print("ERROR: el dashboard no terminó de cargar dentro de 120 segundos.")
            return 5

        except Exception as exc:
            print(f"ERROR inesperado: {exc}")
            return 1

        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
