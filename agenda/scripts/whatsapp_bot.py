"""
whatsapp_bot.py — Bot de WhatsApp para crear tareas verbales.

Recibe notas de voz → Transcribe → Extrae tarea → Crea Calendar + Tasks
Responde confirmación en WhatsApp.

Requiere:
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- ANTHROPIC_API_KEY
- Google OAuth tokens (calendario, tareas)

Uso (webhook en Cloud Run):
    gunicorn --bind :8080 whatsapp_bot:app
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from flask import Flask, request
    from twilio.rest import Client
    from twilio.twiml.messaging_response import MessagingResponse
    import anthropic
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import requests
except ImportError:
    print("ERROR: pip install flask twilio anthropic google-auth-oauthlib google-api-python-client requests")
    sys.exit(1)

app = Flask(__name__)

# Credenciales Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Credenciales Google
TOKENS_PATH = Path(__file__).resolve().parent.parent / "config" / "tokens.json"
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

# Credenciales Anthropic
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ANTHROPIC_KEY]):
    logger.error("ERROR: Faltan credenciales (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ANTHROPIC_API_KEY)")
    sys.exit(1)

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

SYSTEM_PROMPT = """Eres un asistente especializado en extraer tareas académicas de mensajes en español.
Tu tarea es analizar el mensaje y extraer información sobre qué tarea académica se debe realizar y cuándo.

DEVUELVE ÚNICAMENTE JSON válido (sin markdown, sin explicación) con esta forma exacta:
{
  "tarea": "descripción clara de la tarea (verbo + objeto, máx 80 caracteres)",
  "fecha_entrega": "YYYY-MM-DD o null si no se especifica",
  "urgencia": "alta|media|baja",
  "notas": "contexto adicional o null"
}

EXTRACCIÓN DE FECHAS:
- "Mañana" = día siguiente a hoy
- "Antes del viernes" = viernes de esta semana (si ya pasó, la próxima)
- "Para el 25 de julio" = 2025-07-25
- "El próximo lunes" = lunes próximo
- "Esta semana" = viernes de esta semana
- Si no menciona fecha específica = null

URGENCIA:
- ALTA: "urgente", "HOY", "mañana", "para ya", "asap", "ANTES de", "deadline"
- MEDIA: "para el", "antes del", "esta semana", "próxima semana"
- BAJA: "cuando puedas", "eventualmente", "algún momento", "sin prisa"

TAREA:
- Extrae la acción principal: "Entregar proyecto", "Estudiar capítulo 3", "Enviar ensayo"
- Si es vago, sé específico con lo que se menciona
- Elimina redundancias y relleno

NOTAS:
- Si menciona asignatura, profesor, o detalles = incluye en notas
- Si es simple = null
"""


def cargar_credenciales_google():
    """Carga credenciales de Google desde env o tokens.json."""
    creds_dict = None

    # Intentar desde variable de entorno (Cloud Run)
    tokens_env = os.environ.get("GOOGLE_TOKENS_JSON")
    logger.info(f"DEBUG: GOOGLE_TOKENS_JSON disponible: {bool(tokens_env)}, longitud: {len(tokens_env) if tokens_env else 0}")
    if tokens_env:
        try:
            creds_dict = json.loads(tokens_env)
            logger.debug("Credenciales cargadas desde env")
        except Exception as e:
            logger.error(f"ERROR parsando GOOGLE_TOKENS_JSON: {e}")

    # Fallback: intentar desde archivo
    if not creds_dict and TOKENS_PATH.exists():
        try:
            with open(TOKENS_PATH, encoding="utf-8") as f:
                creds_dict = json.load(f)
            logger.debug("Credenciales cargadas desde archivo")
        except Exception as e:
            logger.error(f"ERROR leyendo tokens.json: {e}")

    if not creds_dict:
        logger.error("No hay credenciales de Google disponibles")
        return None

    try:
        creds = Credentials.from_authorized_user_info(creds_dict, scopes=SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        return creds
    except Exception as e:
        logger.error(f"ERROR creando credenciales: {e}")
        return None


def descargar_audio(media_url):
    """Descarga archivo de audio de Twilio."""
    try:
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        response = requests.get(media_url, auth=auth)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.error(f"ERROR descargando audio: {e}")
    return None


def transcribir_audio(audio_content):
    """Transcribe audio usando Google Speech-to-Text (para Cloud Run)."""
    # Nota: En esta versión simplificada, asumimos que Twilio + Anthropic
    # pueden procesar. Para producción, usar google.cloud.speech
    return None


def analizar_con_claude(texto):
    """Usa Claude para extraer tarea del texto."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Mensaje: {texto}"}
            ],
        )
        texto_resp = response.content[0].text.strip()

        inicio = texto_resp.find("{")
        fin = texto_resp.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            return json.loads(texto_resp[inicio:fin])
    except Exception as e:
        logger.error(f"ERROR Claude: {e}")

    return None


def crear_calendar_event(service, tarea_info):
    """Crea evento en Google Calendar."""
    if not tarea_info.get("fecha_entrega"):
        return False

    try:
        event = {
            "summary": f"[Tarea WhatsApp] {tarea_info['tarea']}",
            "description": tarea_info.get("notas", ""),
            "start": {"date": tarea_info["fecha_entrega"]},
            "end": {"date": tarea_info["fecha_entrega"]},
        }
        service.events().insert(calendarId="primary", body=event).execute()
        return True
    except Exception as e:
        logger.error(f"ERROR Calendar: {e}")
        return False


def crear_google_task(service, tarea_info):
    """Crea tarea en Google Tasks."""
    try:
        task = {
            "title": tarea_info["tarea"],
            "notes": tarea_info.get("notas", ""),
        }
        if tarea_info.get("fecha_entrega"):
            task["due"] = tarea_info["fecha_entrega"] + "T23:59:59Z"

        service.tasks().insert(tasklist="@default", body=task).execute()
        return True
    except Exception as e:
        logger.error(f"ERROR Tasks: {e}")
        return False


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Webhook que recibe mensajes de WhatsApp desde Twilio."""
    incoming_msg = request.values.get("Body", "").strip()
    incoming_media_url = request.values.get("MediaUrl0")
    from_number = request.values.get("From")

    logger.info(f"Mensaje recibido desde {from_number}: '{incoming_msg}'")

    resp = MessagingResponse()

    if not incoming_msg and not incoming_media_url:
        resp.message("Hola 👋 Soy un bot de tareas. Envía un mensaje con tu tarea.")
        return str(resp)

    # Procesar mensaje de texto
    tarea_info = None
    if incoming_msg:
        logger.debug(f"Analizando con Claude: '{incoming_msg}'")
        tarea_info = analizar_con_claude(incoming_msg)
        logger.debug(f"Resultado de Claude: {tarea_info}")

    # TODO: Procesar audio (requiere transcripción)
    # if incoming_media_url:
    #     audio = descargar_audio(incoming_media_url)
    #     # Transcribir...

    if not tarea_info:
        logger.warning("No se extrajo información de la tarea")
        resp.message("❌ No entendí la tarea. Intenta: 'Proyecto final antes del viernes'")
        return str(resp)

    # Crear en Google Calendar + Tasks
    creds = cargar_credenciales_google()
    if not creds:
        logger.error("No se pudieron cargar credenciales de Google")
        resp.message("⚠️ Error de autenticación. Intenta más tarde.")
        return str(resp)

    calendar_service = build("calendar", "v3", credentials=creds)
    tasks_service = build("tasks", "v1", credentials=creds)

    cal_ok = crear_calendar_event(calendar_service, tarea_info)
    task_ok = crear_google_task(tasks_service, tarea_info)

    if cal_ok or task_ok:
        fecha_str = tarea_info.get("fecha_entrega", "sin fecha")
        urgencia = tarea_info.get("urgencia", "normal")
        resp.message(
            f"✅ Tarea creada\n"
            f"📝 {tarea_info['tarea']}\n"
            f"📅 {fecha_str}\n"
            f"⚡ {urgencia.upper()}"
        )
    else:
        resp.message("❌ Error creando tarea. Intenta más tarde.")

    return str(resp)


@app.route("/debug", methods=["GET"])
def debug():
    """Debug endpoint."""
    tokens_env = os.environ.get("GOOGLE_TOKENS_JSON")
    return {
        "GOOGLE_TOKENS_JSON_exists": bool(tokens_env),
        "GOOGLE_TOKENS_JSON_length": len(tokens_env) if tokens_env else 0,
        "ANTHROPIC_API_KEY_exists": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }, 200


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    # Local testing
    app.run(debug=True, port=8080)
