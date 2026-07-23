"""
procesar_tareas_email.py — Lee emails de Gmail (etiqueta outlook-reenviado),
extrae tareas con fechas, y crea Google Calendar events + Google Tasks automáticamente.

Usa OAuth token de agenda/config/tokens.json (debe incluir Gmail, Calendar, Tasks scopes).

Uso:
    python procesar_tareas_email.py

Flujo:
  1. Lee Gmail (últimas 24h, etiqueta "outlook-reenviado")
  2. Claude analiza contenido → extrae tareas + fechas
  3. Crea Google Calendar events (con notificaciones iOS)
  4. Crea Google Tasks (linked a email)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    import anthropic
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: pip install anthropic google-auth-oauthlib google-api-python-client")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

TOKENS_PATH = Path(__file__).resolve().parent.parent / "config" / "tokens.json"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Eres un asistente que analiza emails y extrae tareas.
Dado un email, devuelve ÚNICAMENTE JSON válido (sin markdown, sin texto adicional) con esta forma:

{
  "tarea": "descripción clara de la tarea",
  "fecha_entrega": "YYYY-MM-DD o null si no se especifica",
  "urgencia": "alta|media|baja",
  "notas": "detalles adicionales o null"
}

REGLAS:
- Busca palabras clave: "entregar", "deadline", "antes del", "para el", "hasta el", "plazo"
- Si no hay fecha explícita, infiere del contenido o devuelve null
- urgencia: "alta" si menciona "urgente"/"ASAP"/"hoy"/"mañana", "baja" si es general
- Sé conciso en "tarea" (máx 100 caracteres)
"""


def cargar_credenciales():
    """Carga OAuth credentials de tokens.json."""
    if not TOKENS_PATH.exists():
        print(f"ERROR: {TOKENS_PATH} no existe")
        print("Ejecuta: python agenda/scripts/autorizar.py")
        sys.exit(1)

    with open(TOKENS_PATH, encoding="utf-8") as f:
        creds_dict = json.load(f)

    creds = Credentials.from_authorized_user_info(creds_dict, scopes=SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def leer_emails_gmail(service, max_resultados=10):
    """Lee emails de la etiqueta 'outlook-reenviado' de las últimas 24h."""
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    query = f'label:outlook-reenviado after:{hace_24h}'

    print(f"📧 Buscando emails: {query}")

    try:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_resultados
        ).execute()
    except Exception as e:
        print(f"ERROR Gmail API: {e}")
        return []

    mensajes = results.get("messages", [])
    print(f"   Encontrados: {len(mensajes)} emails")

    emails = []
    for msg in mensajes:
        try:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()

            headers = msg_data["payload"].get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(sin asunto)")
            from_addr = next((h["value"] for h in headers if h["name"] == "From"), "(desconocido)")

            # Extraer body
            body = ""
            if "parts" in msg_data["payload"]:
                for part in msg_data["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            import base64
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                            break
            else:
                data = msg_data["payload"].get("body", {}).get("data", "")
                if data:
                    import base64
                    body = base64.urlsafe_b64decode(data).decode("utf-8")

            emails.append({
                "id": msg["id"],
                "subject": subject,
                "from": from_addr,
                "body": body[:500],  # primeros 500 chars
            })
        except Exception as e:
            print(f"  ⚠ Error procesando mensaje: {e}")

    return emails


def analizar_email_con_claude(email_text):
    """Usa Claude para extraer tarea y fecha del email."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Email:\n\nAsunto: {email_text['subject']}\n\nContenido: {email_text['body']}"}
            ],
        )
        texto = response.content[0].text.strip()

        # Parsear JSON
        import re
        inicio = texto.find("{")
        fin = texto.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            json_str = texto[inicio:fin]
            return json.loads(json_str)
    except Exception as e:
        print(f"  ⚠ Error Claude: {e}")

    return None


def crear_calendar_event(service, tarea_info):
    """Crea un evento en Google Calendar."""
    if not tarea_info.get("fecha_entrega"):
        return None

    fecha = tarea_info["fecha_entrega"]
    event = {
        "summary": f"[Entrega] {tarea_info['tarea']}",
        "description": tarea_info.get("notas", ""),
        "start": {"date": fecha},
        "end": {"date": fecha},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "notification", "minutes": 24 * 60},  # 1 día antes
                {"method": "notification", "minutes": 60},       # 1 hora antes (iOS)
            ]
        },
    }

    try:
        created = service.events().insert(calendarId="primary", body=event).execute()
        return created.get("id")
    except Exception as e:
        print(f"  ⚠ Error Calendar: {e}")

    return None


def crear_google_task(service, tarea_info, event_url=None):
    """Crea una tarea en Google Tasks."""
    task = {
        "title": tarea_info["tarea"],
        "notes": tarea_info.get("notas", ""),
    }

    if tarea_info.get("fecha_entrega"):
        task["due"] = tarea_info["fecha_entrega"] + "T23:59:59Z"

    try:
        created = service.tasks().insert(tasklist="@default", body=task).execute()
        return created.get("id")
    except Exception as e:
        print(f"  ⚠ Error Tasks: {e}")

    return None


def main():
    if not ANTHROPIC_KEY:
        print("ERROR: ANTHROPIC_API_KEY no definida")
        sys.exit(1)

    print("🔐 Cargando credenciales OAuth...")
    creds = cargar_credenciales()

    gmail_service = build("gmail", "v1", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)
    tasks_service = build("tasks", "v1", credentials=creds)

    print("\n📧 Leyendo emails...")
    emails = leer_emails_gmail(gmail_service)

    if not emails:
        print("✓ Sin emails nuevos en outlook-reenviado")
        return

    print("\n🤖 Analizando contenido...")
    procesados = 0
    for email in emails:
        print(f"\n  • {email['subject'][:50]}...")

        tarea_info = analizar_email_con_claude(email)
        if not tarea_info:
            print("    ⚠ No se pudo extraer información")
            continue

        print(f"    Tarea: {tarea_info['tarea']}")
        print(f"    Fecha: {tarea_info.get('fecha_entrega', 'Sin fecha')}")
        print(f"    Urgencia: {tarea_info['urgencia']}")

        # Crear Google Calendar event
        event_id = crear_calendar_event(calendar_service, tarea_info)
        if event_id:
            print(f"    ✓ Evento Calendar creado")

        # Crear Google Task
        task_id = crear_google_task(tasks_service, tarea_info)
        if task_id:
            print(f"    ✓ Google Task creada")

        if event_id or task_id:
            procesados += 1

    print(f"\n✓ Procesadas {procesados}/{len(emails)} tareas")
    print("📱 Notificaciones enviadas a iPhone (24h antes y 1h antes)")


if __name__ == "__main__":
    main()
