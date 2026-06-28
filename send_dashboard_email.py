#!/usr/bin/env python3
"""Envía por Gmail el resultado del chequeo y adjunta la captura."""

from __future__ import annotations

import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

SCREENSHOT = Path("dashboard_check.png")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta el secreto o variable {name}")
    return value


def main() -> int:
    email_user = required_env("EMAIL_USER")
    email_password = required_env("EMAIL_APP_PASSWORD")
    email_to = required_env("EMAIL_TO")
    result = os.getenv("DASHBOARD_RESULT", "unknown")

    now = datetime.now(ZoneInfo("Europe/Madrid"))
    is_ok = result == "success"

    message = EmailMessage()
    message["From"] = email_user
    message["To"] = email_to
    message["Subject"] = (
        f"{'✅' if is_ok else '❌'} Streamlit dashboard "
        f"{now:%Y-%m-%d %H:%M}"
    )

    message.set_content(
        "\n".join(
            [
                f"Resultado: {'OK' if is_ok else 'ERROR'}",
                f"Fecha: {now:%d/%m/%Y %H:%M %Z}",
                "URL: https://iavaluechain.streamlit.app/",
                "",
                (
                    "El navegador automatizado abrió el dashboard correctamente."
                    if is_ok
                    else
                    "El navegador automatizado no pudo validar el dashboard. "
                    "Revisa la captura y los logs de GitHub Actions."
                ),
            ]
        )
    )

    if SCREENSHOT.exists():
        message.add_attachment(
            SCREENSHOT.read_bytes(),
            maintype="image",
            subtype="png",
            filename=SCREENSHOT.name,
        )
    else:
        print("Aviso: no se encontró dashboard_check.png", file=sys.stderr)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(email_user, email_password)
        smtp.send_message(message)

    print(f"Email enviado a {email_to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
