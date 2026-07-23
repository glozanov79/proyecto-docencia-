"""
enviar_briefs.py — recolecta los briefs generados en esta ejecución y los
envía por email a lozanogerman79@gmail.com.

Corre justo después de  python jefe_general.py --ejecutar.
Cada curso que generó materiales aporta:
  - el brief.md como cuerpo del email
  - taller.xlsx, videos.docx, presentacion.pptx como adjuntos (si existen)

Variables de entorno requeridas:
  GMAIL_APP_PASSWORD  — contraseña de aplicación de Gmail (no la contraseña normal)
  DESTINATARIO        — dirección a la que llega el correo (def. lozanogerman79@gmail.com)
"""

import os
import smtplib
import subprocess
import sys
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
REMITENTE = "lozanogerman79@gmail.com"
DESTINATARIO = os.environ.get("DESTINATARIO", REMITENTE)
APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ADJUNTOS_VALIDOS = {".xlsx", ".docx", ".pptx"}


def recolectar_briefs():
    """Encuentra todos los ULTIMO_BRIEF.txt y devuelve los briefs generados."""
    resultados = []
    for marcador in sorted(BASE.rglob("ULTIMO_BRIEF.txt")):
        ruta_rel = marcador.read_text(encoding="utf-8").strip()
        curso_dir = marcador.parent.parent          # .../cursos/{nombre}-agente
        brief_path = curso_dir / ruta_rel
        if not brief_path.exists():
            continue
        nombre = (
            curso_dir.name
            .replace("-agente", "")
            .replace("-", " ")
            .title()
        )
        resultados.append({
            "nombre": nombre,
            "brief": brief_path,
            "carpeta_salida": brief_path.parent,
        })
    return resultados


def construir_mensaje(briefs):
    msg = MIMEMultipart()
    msg["From"] = REMITENTE
    msg["To"] = DESTINATARIO
    hoy = date.today().isoformat()

    if not briefs:
        msg["Subject"] = f"Materiales de clase {hoy} — sin clases próximas"
        msg.attach(MIMEText(
            "No hay clases programadas para preparar en los próximos 7 días.",
            "plain", "utf-8"
        ))
        return msg

    msg["Subject"] = (
        f"Materiales de clase {hoy} — "
        + ", ".join(b["nombre"] for b in briefs)
    )

    cuerpo = [f"Materiales generados el {hoy} para {len(briefs)} curso(s).\n"]
    for b in briefs:
        sep = "=" * 60
        cuerpo.append(f"\n{sep}")
        cuerpo.append(f"  {b['nombre'].upper()}")
        cuerpo.append(f"{sep}")
        cuerpo.append(b["brief"].read_text(encoding="utf-8"))

    msg.attach(MIMEText("\n".join(cuerpo), "plain", "utf-8"))

    for b in briefs:
        for archivo in sorted(b["carpeta_salida"].iterdir()):
            if archivo.suffix in ADJUNTOS_VALIDOS:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(archivo.read_bytes())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{b["nombre"]} - {archivo.name}"',
                )
                msg.attach(part)

    return msg


def main():
    briefs = recolectar_briefs()
    print(f"Briefs encontrados: {len(briefs)}")
    for b in briefs:
        print(f"  · {b['nombre']}  →  {b['brief']}")

    if not APP_PASSWORD:
        print("GMAIL_APP_PASSWORD no configurada — se omite el envío de email.")
        sys.exit(0)

    msg = construir_mensaje(briefs)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(REMITENTE, APP_PASSWORD)
        smtp.send_message(msg)

    print(f"Email enviado a {DESTINATARIO}")

    # Subir a Google Drive
    print("\nSincronizando con Google Drive...")
    subir_script = BASE / "ucc" / "scripts" / "subir_a_drive.py"
    for b in briefs:
        brief_path = b["brief"]
        try:
            subprocess.run(
                ["python", str(subir_script), str(brief_path)],
                encoding="utf-8",
                check=False,
            )
        except FileNotFoundError:
            print(f"  ⚠ subir_a_drive.py no encontrado")


if __name__ == "__main__":
    main()
