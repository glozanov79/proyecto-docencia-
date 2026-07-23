"""
Sube briefs, talleres, videos y presentaciones a Google Drive.
Usa el mismo OAuth token de agenda para autenticar.

Requiere:
- Credenciales en Secret Manager: agenda-tokens
- Google Drive API habilitada

Uso:
    python subir_a_drive.py salidas/2026-08-05/brief.md
"""

import json
import os
import sys
from pathlib import Path
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.api_core.exceptions import GoogleAPIError
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("ERROR: Instala google-auth-oauthlib, google-auth-httplib2, google-api-python-client")
    sys.exit(1)


SCOPES = ["https://www.googleapis.com/auth/drive"]


def cargar_credenciales():
    """Carga credenciales desde archivo tokens.json (mismo que agenda)."""
    tokens_path = Path(__file__).resolve().parent.parent / "agenda" / "config" / "tokens.json"

    if not tokens_path.exists():
        print(f"ERROR: No encontrado {tokens_path}")
        print("Ejecuta primero: python agenda/scripts/autorizar.py")
        sys.exit(1)

    with open(tokens_path, encoding="utf-8") as f:
        creds_dict = json.load(f)

    creds = Credentials.from_authorized_user_info(creds_dict, scopes=SCOPES)

    # Refresh si es necesario
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def obtener_o_crear_carpeta(service, nombre_carpeta, parent_id=None):
    """Obtiene o crea una carpeta en Drive. Retorna el ID."""
    query = f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Crear carpeta
    file_metadata = {
        "name": nombre_carpeta,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]

    carpeta = service.files().create(body=file_metadata, fields="id").execute()
    return carpeta.get("id")


def subir_archivo(service, ruta_archivo, nombre_en_drive, parent_id):
    """Sube un archivo a Drive en la carpeta parent_id."""
    file_metadata = {"name": nombre_en_drive, "parents": [parent_id]}
    media = MediaFileUpload(str(ruta_archivo), resumable=True)

    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")


def main():
    if len(sys.argv) != 2:
        print("Uso: python subir_a_drive.py <ruta_al_brief.md>")
        sys.exit(1)

    brief_path = Path(sys.argv[1])
    if not brief_path.exists():
        print(f"ERROR: No encontrado {brief_path}")
        sys.exit(1)

    salida_dir = brief_path.parent  # Directorio con los archivos
    curso_dir = salida_dir.parent.parent  # cursos/{curso}/
    curso_nombre = curso_dir.name
    fecha_str = salida_dir.name  # YYYY-MM-DD

    print(f"📤 Subiendo a Drive: {curso_nombre}/{fecha_str}/")

    creds = cargar_credenciales()
    service = build("drive", "v3", credentials=creds)

    # Crear carpeta del curso (root)
    carpeta_curso_id = obtener_o_crear_carpeta(service, curso_nombre)
    print(f"  ✓ Carpeta curso: {curso_nombre}")

    # Crear subcarpeta con la fecha
    carpeta_fecha_id = obtener_o_crear_carpeta(service, fecha_str, parent_id=carpeta_curso_id)
    print(f"  ✓ Carpeta fecha: {fecha_str}")

    # Archivos a subir
    archivos = [
        ("brief.md", "brief.md"),
        ("taller.xlsx", "taller.xlsx"),
        ("videos.docx", "videos.docx"),
        ("presentacion.pptx", "presentacion.pptx"),
    ]

    subidos = []
    for nombre_local, nombre_drive in archivos:
        ruta = salida_dir / nombre_local
        if ruta.exists():
            try:
                subir_archivo(service, ruta, nombre_drive, carpeta_fecha_id)
                print(f"  ✓ {nombre_drive}")
                subidos.append(nombre_drive)
            except GoogleAPIError as e:
                print(f"  ✗ {nombre_drive}: {e}")
        else:
            print(f"  - {nombre_drive} (no existe aún)")

    print(f"✓ Sincronizado: {len(subidos)} archivo(s)")


if __name__ == "__main__":
    main()
