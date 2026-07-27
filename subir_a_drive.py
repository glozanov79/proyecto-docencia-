"""
Sube archivos generados a Google Drive en carpetas específicas.
"""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).resolve().parent

# IDs de carpetas en Google Drive
CARPETAS = {
    "pensamiento-economico-agente": "1z3QOAgJheTBoxUc9HK6ZrggyzPB30uOm",
    "e-financial-agente": "1f1wvSMgzezVFpQpW-MkSoN60Y8MsNpGF"
}

TIPOS_MIME = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown"
}

def autenticar():
    """Autentica con Google Drive usando tokens.json"""
    import json
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    tokens_path = BASE / "ucc" / "config" / "tokens.json"

    with open(tokens_path) as f:
        tokens = json.load(f)

    creds = Credentials(
        token=tokens["token"],
        refresh_token=tokens.get("refresh_token"),
        token_uri=tokens.get("token_uri"),
        client_id=tokens.get("client_id"),
        client_secret=tokens.get("client_secret"),
        scopes=tokens.get("scopes")
    )

    # Refrescar si es necesario
    if creds.expired:
        creds.refresh(Request())

    return build("drive", "v3", credentials=creds)

def crear_carpeta_fecha(service, parent_folder_id, fecha):
    """Crea carpeta con la fecha de la clase"""
    nombre_carpeta = f"Semana 1 - {fecha}"

    # Verificar si ya existe
    query = f"name='{nombre_carpeta}' and '{parent_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()

    if results.get("files"):
        return results["files"][0]["id"]

    # Crear nueva carpeta
    file_metadata = {
        "name": nombre_carpeta,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id]
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    print(f"Folder created: {nombre_carpeta}")
    return folder.get("id")

def subir_archivo(service, folder_id, ruta_archivo):
    """Sube un archivo a Google Drive"""
    archivo = Path(ruta_archivo)

    file_metadata = {
        "name": archivo.name,
        "parents": [folder_id]
    }

    media = MediaFileUpload(
        str(archivo),
        mimetype=TIPOS_MIME.get(archivo.suffix, "application/octet-stream")
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"  OK {archivo.name}")
    return file.get("id")

def subir_curso(service, curso, carpeta_parent_id, fecha_clase):
    """Sube todos los archivos de un curso"""
    print(f"\n{curso}")

    # Crear carpeta con fecha
    folder_id = crear_carpeta_fecha(service, carpeta_parent_id, fecha_clase)

    # Encontrar archivos generados
    salidas_dir = BASE / "ucc" / "cursos" / curso / "salidas"

    # Buscar archivos en la carpeta más reciente de Semana
    semana_dirs = sorted([d for d in salidas_dir.iterdir() if d.is_dir() and "Semana" in d.name])

    if not semana_dirs:
        print("  WARNING: No se encontraron carpetas de salida")
        return

    semana_dir = semana_dirs[-1]

    # Subir archivos principales
    for ext in [".md", ".pptx", ".xlsx", ".docx"]:
        archivo = semana_dir / f"*{ext}"
        # Buscar archivo con patrón
        archivos = list(semana_dir.glob(f"*{ext}"))
        for archivo in archivos:
            subir_archivo(service, folder_id, archivo)

def main():
    """Sube archivos de E-Financial y Pensamiento Económico"""
    service = autenticar()

    cursos_config = [
        ("e-financial-agente", "1f1wvSMgzezVFpQpW-MkSoN60Y8MsNpGF", "2026-08-03"),
        ("pensamiento-economico-agente", "1z3QOAgJheTBoxUc9HK6ZrggyzPB30uOm", "2026-08-03")
    ]

    for curso, folder_id, fecha in cursos_config:
        subir_curso(service, curso, folder_id, fecha)

    print("\nOK - Process completed")

if __name__ == "__main__":
    main()
