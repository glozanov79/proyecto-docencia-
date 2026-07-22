#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contexto_correo.py  —  Agente CORREO del dominio agenda.

DEPENDE del agente calendario: lee el snapshot
    calendario/salidas/agenda_actual.json
y con él hace tres cosas deterministas que Claude luego interpreta:

  1) valida-frescura : confirma que el snapshot existe y no está viejo.
                       Si no, el correo NO debe revisarse todavía (hay que
                       correr calendario primero). Esta es la dependencia.

  2) contexto        : imprime un bloque compacto de tu agenda próxima para
                       que Claude tenga presente qué eventos existen al leer
                       el correo.

  3) cruzar          : dada una lista de correos candidatos (con fecha y/o
                       palabras detectadas), marca cuáles se refieren a un
                       evento YA existente y cuáles proponen un evento NUEVO
                       que habría que agendar.

Uso:
    python contexto_correo.py validar-frescura [--horas 2]
    python contexto_correo.py contexto
    python contexto_correo.py cruzar --candidatos correos.json
    cat correos.json | python contexto_correo.py cruzar

Formato de cada correo candidato (todo opcional salvo asunto):
    {
      "asunto": "Reunión de área jueves",
      "remitente": "coordinacion@campusucc.edu.co",
      "fecha_detectada": "2026-08-06",     # fecha que Claude extrajo del texto
      "palabras": ["reunión", "acta"]
    }

Pruebas: --fecha 2026-08-03  o  JEFE_FAKE_HOY=2026-08-03
"""

import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_CORREO = os.path.dirname(AQUI)                    # .../agenda/correo
DIR_AGENDA = os.path.dirname(DIR_CORREO)              # .../agenda
SNAPSHOT = os.path.join(DIR_AGENDA, "calendario", "salidas", "agenda_actual.json")
CRITERIOS = os.path.join(DIR_CORREO, "config", "criterios.json")


def hoy(args_fecha=None):
    override = args_fecha or os.environ.get("JEFE_FAKE_HOY")
    if override:
        return datetime.strptime(override.strip(), "%Y-%m-%d").date()
    return date.today()


def cargar_snapshot():
    if not os.path.exists(SNAPSHOT):
        return None
    with open(SNAPSHOT, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_validar_frescura(args):
    snap = cargar_snapshot()
    if snap is None:
        print("BLOQUEADO: no existe el snapshot de agenda.")
        print("  -> Corre primero el agente calendario (RUTINA_AGENDA.md).")
        sys.exit(1)
    try:
        gen = datetime.fromisoformat(snap.get("generado", ""))
    except ValueError:
        print("BLOQUEADO: snapshot con fecha de generación ilegible; regéneralo.")
        sys.exit(1)

    edad = datetime.now() - gen
    limite = timedelta(hours=args.horas)
    horas = edad.total_seconds() / 3600
    if edad > limite:
        print(f"BLOQUEADO: el snapshot tiene {horas:.1f} h (límite {args.horas} h).")
        print("  -> Vuelve a correr el agente calendario antes de revisar correo.")
        sys.exit(1)

    print(f"OK: snapshot fresco ({horas:.1f} h). Se puede revisar el correo.")
    print(f"  eventos en agenda: {snap.get('total_eventos', 0)}")


def cmd_contexto(args):
    snap = cargar_snapshot()
    if snap is None:
        print("(sin snapshot de agenda — corre el agente calendario primero)")
        return
    eventos = snap.get("eventos", [])
    print("=== AGENDA PRÓXIMA (contexto para leer el correo) ===")
    print(f"referencia: {snap.get('fecha_referencia')}  |  eventos: {len(eventos)}")
    if not eventos:
        print("  (sin eventos en la ventana)")
        return
    for e in eventos:
        hh = f" {e['hora_inicio']}" if e.get("hora_inicio") else ""
        ubi = f"  @ {e['ubicacion']}" if e.get("ubicacion") else ""
        print(f"  - {e['fecha']}{hh}  {e['titulo']}  ({e['cuando']}){ubi}")


def _eventos_en_fecha(eventos, fecha_str):
    return [e for e in eventos if e.get("fecha") == fecha_str]


def _similitud_titulo(asunto, titulo):
    """Coincidencia simple por palabras compartidas (sin dependencias externas)."""
    a = {p for p in _norm(asunto).split() if len(p) > 3}
    t = {p for p in _norm(titulo).split() if len(p) > 3}
    if not a or not t:
        return 0.0
    return len(a & t) / len(a | t)


def _norm(s):
    s = (s or "").lower()
    tabla = str.maketrans("áéíóúü", "aeiouu")
    return s.translate(tabla)


def cmd_cruzar(args):
    snap = cargar_snapshot()
    if snap is None:
        print("BLOQUEADO: no hay snapshot; corre el agente calendario primero.",
              file=sys.stderr)
        sys.exit(1)
    eventos = snap.get("eventos", [])

    if args.candidatos:
        with open(args.candidatos, "r", encoding="utf-8") as f:
            candidatos = json.load(f)
    else:
        raw = sys.stdin.read().strip()
        candidatos = json.loads(raw) if raw else []
    if isinstance(candidatos, dict):
        candidatos = candidatos.get("correos") or candidatos.get("candidatos") or []

    ya_existen, nuevos, sin_fecha = [], [], []
    for c in candidatos:
        asunto = c.get("asunto", "")
        fecha = (c.get("fecha_detectada") or "").strip()
        if not fecha:
            sin_fecha.append(c)
            continue
        coincidencias = _eventos_en_fecha(eventos, fecha)
        mejor = None
        mejor_sim = 0.0
        for ev in coincidencias:
            sim = _similitud_titulo(asunto, ev.get("titulo", ""))
            if sim > mejor_sim:
                mejor, mejor_sim = ev, sim
        if coincidencias:
            ya_existen.append({"correo": c, "evento": mejor, "similitud": round(mejor_sim, 2)})
        else:
            nuevos.append(c)

    resultado = {
        "referencia": snap.get("fecha_referencia"),
        "ya_en_agenda": ya_existen,
        "proponer_nuevo_evento": nuevos,
        "sin_fecha_detectada": sin_fecha,
    }
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description="Agente correo: cruza con la agenda.")
    p.add_argument("--fecha", help="Fecha 'de hoy' YYYY-MM-DD (pruebas).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("validar-frescura", help="Verifica que el snapshot esté fresco.")
    s1.add_argument("--horas", type=int, default=2, help="Antigüedad máxima permitida.")
    s1.set_defaults(func=cmd_validar_frescura)

    s2 = sub.add_parser("contexto", help="Imprime la agenda próxima.")
    s2.set_defaults(func=cmd_contexto)

    s3 = sub.add_parser("cruzar", help="Cruza correos candidatos contra la agenda.")
    s3.add_argument("--candidatos", help="Archivo JSON con la lista de correos.")
    s3.set_defaults(func=cmd_cruzar)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
