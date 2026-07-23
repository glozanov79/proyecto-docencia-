"""
autorizar.py — autorización OAuth una sola vez.
Abre el navegador, pide permiso para Calendar, Gmail y Google Drive, y guarda
el refresh_token en agenda/config/tokens.json.

Uso:
    python agenda/scripts/autorizar.py
"""

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

sys.stdout.reconfigure(encoding="utf-8")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive",
]

AQUI = Path(__file__).resolve().parent.parent
CLIENT = AQUI / "config" / "oauth_client.json"
TOKENS = AQUI / "config" / "tokens.json"


def main():
    if not CLIENT.exists():
        print(f"ERROR: no encuentro {CLIENT}")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
    creds = flow.run_local_server(port=0)

    datos = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }

    TOKENS.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    print(f"✔ tokens guardados en: {TOKENS}")
    print(f"  refresh_token: {creds.refresh_token[:20]}...")


if __name__ == "__main__":
    main()
