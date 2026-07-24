"""
whatsapp_bot.py — Bot de WhatsApp para crear tareas académicas con confirmación.

Flujo:
1. Usuario envía tarea → Bot extrae y resume
2. Bot pregunta confirmación y guarda en Firestore
3. Usuario responde "sí" → Bot crea evento en Calendar + Tasks
4. Usuario responde "no" → Bot cancela

Requiere:
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
- ANTHROPIC_API_KEY
- GOOGLE_TOKENS_JSON (Google OAuth)
- GOOGLE_CLOUD_PROJECT (para Firestore)
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

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
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError as e:
    logger.error(f"ERROR: {e}")
    sys.exit(1)

app = Flask(__name__)

# ─── Credenciales ───────────────────────────────────────────────────────────

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "solar-dialect-408720")

TOKENS_PATH = Path(__file__).resolve().parent.parent / "config" / "tokens.json"
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ANTHROPIC_KEY]):
    logger.error("ERROR: Faltan credenciales")
    sys.exit(1)

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ─── Firebase Firestore ──────────────────────────────────────────────────────

try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
    db = firestore.client()
except Exception as e:
    logger.warning(f"Firebase init warning: {e}. Continuando sin estado persistente.")
    db = None

# ─── Claude System Prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un asistente especializado en extraer tareas academicas de mensajes en espanol.
Tu tarea es analizar el mensaje y extraer informacion sobre que tarea academica se debe realizar y cuando.

DEVUELVE UNICAMENTE JSON valido (sin markdown, sin explicacion) con esta forma exacta:
{
  "tarea": "descripcion clara de la tarea (verbo + objeto, maximo 80 caracteres)",
  "fecha_entrega": "YYYY-MM-DD o null si no se especifica",
  "urgencia": "alta|media|baja",
  "notas": "contexto adicional o null"
}

EXTRACCION DE FECHAS:
- "Manana" = dia siguiente a hoy
- "Antes del viernes" = viernes de esta semana (si ya paso, la proxima)
- "Para el 25 de julio" = 2025-07-25
- "El proximo lunes" = lunes proximo
- "Esta semana" = viernes de esta semana
- Si no menciona fecha especifica = null

URGENCIA:
- ALTA: "urgente", "HOY", "manana", "para ya", "asap", "ANTES de", "deadline"
- MEDIA: "para el", "antes del", "esta semana", "proxima semana"
- BAJA: "cuando puedas", "eventualmente", "algun momento", "sin prisa"

TAREA:
- Extrae la accion principal: "Entregar proyecto", "Estudiar capitulo 3", "Enviar ensayo"
- Si es vago, se especifico con lo que se menciona
- Elimina redundancias y relleno

NOTAS:
- Si menciona asignatura, profesor, o detalles = incluye en notas
- Si es simple = null
"""

# ─── Funciones de utilidad ──────────────────────────────────────────────────

def cargar_credenciales_google():
    """Carga credenciales de Google desde env o tokens.json."""
    creds_dict = None

    tokens_env = os.environ.get("GOOGLE_TOKENS_JSON")
    if tokens_env:
        try:
            creds_dict = json.loads(tokens_env)
            logger.debug("Credenciales cargadas desde env")
        except Exception as e:
            logger.error(f"ERROR parsando GOOGLE_TOKENS_JSON: {e}")

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


def analizar_con_claude(texto):
    """Usa Claude para extraer tarea del texto."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Mensaje: {texto}"}],
        )
        texto_resp = response.content[0].text.strip()
        inicio = texto_resp.find("{")
        fin = texto_resp.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            return json.loads(texto_resp[inicio:fin])
    except Exception as e:
        logger.error(f"ERROR Claude: {e}")
    return None


def guardar_tarea_pendiente(from_number, tarea_info):
    """Guarda tarea propuesta en Firestore."""
    if not db:
        return False
    try:
        db.collection("tareas_pendientes").document(from_number).set({
            "tarea_info": tarea_info,
            "timestamp": datetime.now()
        })
        return True
    except Exception as e:
        logger.error(f"ERROR guardando en Firestore: {e}")
        return False


def obtener_tarea_pendiente(from_number):
    """Obtiene tarea propuesta de Firestore."""
    if not db:
        return None
    try:
        doc = db.collection("tareas_pendientes").document(from_number).get()
        if doc.exists:
            return doc.to_dict().get("tarea_info")
    except Exception as e:
        logger.error(f"ERROR leyendo de Firestore: {e}")
    return None


def eliminar_tarea_pendiente(from_number):
    """Elimina tarea propuesta de Firestore."""
    if not db:
        return True
    try:
        db.collection("tareas_pendientes").document(from_number).delete()
        return True
    except Exception as e:
        logger.error(f"ERROR eliminando de Firestore: {e}")
        return False


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


def formatear_resumen(tarea_info):
    """Formatea resumen de tarea para mostrar."""
    fecha = tarea_info.get("fecha_entrega") or "Sin fecha"
    urgencia = (tarea_info.get("urgencia") or "normal").upper()
    return (
        f"📋 *Resumen*\n"
        f"✏️ {tarea_info['tarea']}\n"
        f"📅 {fecha}\n"
        f"⚡ {urgencia}\n\n"
        f"¿Confirmas? Responde *sí* o *no*"
    )


# ─── Rutas ──────────────────────────────────────────────────────────────────

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Webhook de Twilio para WhatsApp."""
    incoming_msg = request.values.get("Body", "").strip().lower()
    from_number = request.values.get("From")

    logger.info(f"Mensaje de {from_number}: '{incoming_msg}'")

    resp = MessagingResponse()

    # ─ Respuestas a confirmación ─
    if incoming_msg in ["sí", "si", "yes", "confirmo", "confirma", "ok", "okey"]:
        tarea_info = obtener_tarea_pendiente(from_number)
        if not tarea_info:
            resp.message("❌ No hay tarea pendiente. Envía una nueva.")
            return str(resp)

        creds = cargar_credenciales_google()
        if not creds:
            resp.message("⚠️ Error de autenticación. Intenta más tarde.")
            return str(resp)

        calendar_service = build("calendar", "v3", credentials=creds)
        tasks_service = build("tasks", "v1", credentials=creds)

        cal_ok = crear_calendar_event(calendar_service, tarea_info)
        task_ok = crear_google_task(tasks_service, tarea_info)

        eliminar_tarea_pendiente(from_number)

        if cal_ok or task_ok:
            resp.message(
                f"✅ ¡Tarea creada!\n"
                f"📝 {tarea_info['tarea']}\n"
                f"📅 {tarea_info.get('fecha_entrega', 'Sin fecha')}\n"
                f"⚡ {(tarea_info.get('urgencia') or 'normal').upper()}"
            )
        else:
            resp.message("❌ Error creando tarea. Intenta más tarde.")
        return str(resp)

    # ─ Cancelación ─
    if incoming_msg in ["no", "nope", "cancel", "cancela"]:
        if eliminar_tarea_pendiente(from_number):
            resp.message("❌ Tarea cancelada.")
        else:
            resp.message("No había tarea pendiente.")
        return str(resp)

    # ─ Nueva tarea ─
    if not incoming_msg:
        resp.message("👋 Envía una NUEVA tarea para crear un recordatorio.")
        return str(resp)

    logger.info(f"Analizando con Claude: '{incoming_msg}'")
    tarea_info = analizar_con_claude(incoming_msg)
    logger.info(f"Resultado de Claude: {tarea_info}")
    if not tarea_info:
        resp.message("❌ No entendí la tarea. Intenta: 'Proyecto final antes del viernes'")
        return str(resp)

    logger.info(f"Guardando tarea pendiente...")
    guardar_tarea_pendiente(from_number, tarea_info)
    logger.info(f"Enviando resumen...")
    resumen = formatear_resumen(tarea_info)
    logger.info(f"Resumen: {resumen}")
    resp.message(resumen)
    return str(resp)


@app.route("/debug", methods=["GET"])
def debug():
    """Debug endpoint."""
    tokens_env = os.environ.get("GOOGLE_TOKENS_JSON")
    return {
        "GOOGLE_TOKENS_JSON_exists": bool(tokens_env),
        "ANTHROPIC_API_KEY_exists": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "FIRESTORE_enabled": db is not None,
    }, 200


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=True, port=8080)
