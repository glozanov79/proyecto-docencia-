"""
main.py — Cloud Function del dominio agenda.
Se ejecuta 6 veces al día vía Cloud Scheduler.
Lee Google Calendar y Gmail; envía un resumen por email.
"""

import json
import os
import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import secretmanager
from googleapiclient.discovery import build

DESTINATARIO = os.environ.get("DESTINATARIO", "lozanogerman79@gmail.com")
REMITENTE = "lozanogerman79@gmail.com"
VENTANA_DIAS = 7


def _get_secret(secret_id):
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project}/secrets/{secret_id}/versions/latest"
    resp = client.access_secret_version(request={"name": name})
    return resp.payload.data.decode("utf-8")


def _build_credentials():
    tokens = json.loads(_get_secret("agenda-tokens"))
    creds = Credentials(
        token=tokens.get("token"),
        refresh_token=tokens["refresh_token"],
        token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=tokens["client_id"],
        client_secret=tokens["client_secret"],
        scopes=tokens.get("scopes"),
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def _get_eventos(creds):
    svc = build("calendar", "v3", credentials=creds)
    ahora = datetime.utcnow()
    result = svc.events().list(
        calendarId="primary",
        timeMin=ahora.isoformat() + "Z",
        timeMax=(ahora + timedelta(days=VENTANA_DIAS)).isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime",
        maxResults=20,
    ).execute()

    hoy = date.today()
    eventos = []
    for item in result.get("items", []):
        inicio = item["start"].get("dateTime", item["start"].get("date", ""))
        fecha_str = inicio[:10]
        hora_str = inicio[11:16] if "T" in inicio else ""
        try:
            d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        dias = (d - hoy).days
        if dias < 0:
            continue
        cuando = "hoy" if dias == 0 else ("mañana" if dias == 1 else f"en {dias} días")
        eventos.append({
            "titulo": item.get("summary", "(sin título)"),
            "fecha": fecha_str,
            "hora": hora_str,
            "cuando": cuando,
            "ubicacion": item.get("location", ""),
        })
    return eventos


def _get_correos(creds, max_r=15):
    svc = build("gmail", "v1", credentials=creds)
    result = svc.users().messages().list(
        userId="me",
        q="is:unread newer_than:1d",
        maxResults=max_r,
    ).execute()

    correos = []
    for ref in result.get("messages", []):
        msg = svc.users().messages().get(
            userId="me",
            id=ref["id"],
            format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()
        hdrs = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        correos.append({
            "asunto": hdrs.get("Subject", "(sin asunto)"),
            "remitente": hdrs.get("From", ""),
        })
    return correos


def _construir_cuerpo(eventos, correos):
    hoy = date.today().isoformat()
    hora = datetime.now().strftime("%H:%M")
    lineas = [
        f"Resumen de agenda — {hoy}  {hora} hora Colombia",
        "=" * 55,
        "",
        f"CALENDARIO — próximos {VENTANA_DIAS} días",
        "-" * 40,
    ]
    if eventos:
        for e in eventos:
            hh = f" {e['hora']}" if e["hora"] else ""
            ubi = f"  @ {e['ubicacion']}" if e["ubicacion"] else ""
            lineas.append(f"  {e['fecha']}{hh}  {e['titulo']}  ({e['cuando']}){ubi}")
    else:
        lineas.append("  (sin eventos próximos)")

    lineas += ["", "CORREOS NO LEÍDOS (últimas 24 h)", "-" * 40]
    if correos:
        for c in correos:
            lineas.append(f"  {c['remitente']}")
            lineas.append(f"  → {c['asunto']}")
            lineas.append("")
    else:
        lineas.append("  (sin correos no leídos recientes)")

    return "\n".join(lineas)


def agenda_check(request=None):
    """Entrada de la Cloud Function (HTTP trigger)."""
    print("Revisión de agenda iniciada.")

    creds = _build_credentials()

    eventos = _get_eventos(creds)
    print(f"Eventos: {len(eventos)}")

    correos = _get_correos(creds)
    print(f"Correos no leídos: {len(correos)}")

    hoy = date.today().isoformat()
    hora = datetime.now().strftime("%H:%M")
    asunto = f"Agenda {hoy} {hora} — {len(eventos)} eventos · {len(correos)} correos"
    cuerpo = _construir_cuerpo(eventos, correos)

    app_password = _get_secret("agenda-gmail-password")
    msg = MIMEMultipart()
    msg["From"] = REMITENTE
    msg["To"] = DESTINATARIO
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(REMITENTE, app_password)
        smtp.send_message(msg)

    print(f"Email enviado a {DESTINATARIO}")
    return "OK", 200


if __name__ == "__main__":
    agenda_check()
