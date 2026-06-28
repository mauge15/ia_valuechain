#!/usr/bin/env python3
"""
Comprueba un dashboard Streamlit aunque su contenido esté dentro de un iframe.

Instalación:
    pip install playwright
    playwright install chromium

Ejecución:
    python check_dashboard_browser.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://iavaluechain.streamlit.app/"
SCREENSHOT = Path("dashboard_check.png")

FATAL_TEXTS = [
    "This app has gone to sleep",
    "Error running app",
    "App is not running",
    "Page not found",
]


def frame_text(frame) -> str:
    try:
        return frame.locator("body").inner_text(timeout=5_000).strip()
    except Exception:
        return ""


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
        )

        try:
            print(f"Abriendo: {URL}")

            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            try:
                page.wait_for_load_state("networkidle", timeout=60_000)
            except PlaywrightTimeoutError:
                print("Aviso: Streamlit mantiene conexiones abiertas; continúo.")

            page.wait_for_timeout(15_000)

            # Captura antes de validar, para conservar evidencia visual.
            page.screenshot(path=str(SCREENSHOT), full_page=True)

            print(f"HTTP inicial: {response.status if response else None}")
            print(f"URL final: {page.url}")
            print(f"Título: {page.title()}")
            print(f"Frames detectados: {len(page.frames)}")
            print(f"Captura: {SCREENSHOT.resolve()}")

            all_text = []
            streamlit_markers = 0

            for index, frame in enumerate(page.frames):
                text = frame_text(frame)
                all_text.append(text)

                print(
                    f"Frame {index}: url={frame.url!r}, "
                    f"texto={len(text)} caracteres"
                )

                try:
                    streamlit_markers += frame.locator(
                        '[data-testid="stAppViewContainer"], '
                        '[data-testid="stMain"], '
                        '.stApp'
                    ).count()
                except Exception:
                    pass

            combined_text = "\n".join(text for text in all_text if text)
            combined_lower = combined_text.lower()

            detected_errors = [
                error for error in FATAL_TEXTS
                if error.lower() in combined_lower
            ]

            if detected_errors:
                print("ERROR: se detectó un mensaje de fallo:")
                for error in detected_errors:
                    print(f"- {error}")
                return 2

            # Tu app se carga dentro de iframe. Por eso el body de la página
            # principal puede tener 0 caracteres aunque el dashboard esté bien.
            has_iframe = page.locator("iframe").count() > 0
            has_content = len(combined_text) >= 50
            title_ok = "AI Infrastructure Radar" in page.title()

            print(f"Marcadores Streamlit: {streamlit_markers}")
            print(f"Hay iframe: {has_iframe}")
            print(f"Texto total en todos los frames: {len(combined_text)}")

            if not (has_content or streamlit_markers > 0 or (has_iframe and title_ok)):
                print("ERROR: no se pudo confirmar que el dashboard cargó.")
                return 3

            print("OK: el dashboard se abrió correctamente.")
            if combined_text:
                print("\nPrimeros 500 caracteres visibles:")
                print(combined_text[:500])

            return 0

        except Exception as exc:
            print(f"ERROR inesperado: {type(exc).__name__}: {exc}")

            try:
                page.screenshot(path=str(SCREENSHOT), full_page=True)
                print(f"Captura de error guardada: {SCREENSHOT.resolve()}")
            except Exception:
                pass

            return 1

        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
