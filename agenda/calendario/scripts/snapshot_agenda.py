#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot_agenda.py  —  Agente CALENDARIO del dominio agenda.

Toma los eventos que Claude leyó de Google Calendar (vía el conector, en la
conversación) y los normaliza en un snapshot estable:

    calendario/salidas/agenda_actual.json

Ese snapshot es lo que consume el agente de CORREO. Por eso el correo depende
del calendario: si no hay snapshot fresco, el correo no sabe contra qué cruzar.

Entrada de eventos (cualquiera de las dos):
    - un archivo JSON con lista de eventos:   --eventos eventos.json
    - por stdin (JSON):                        cat eventos.json | snapshot_agenda.py

Formato mínimo de cada evento de entrada (campos flexibles):
    {
      "titulo": "Clase E-Financial",       # o "summary"
      "inicio": "2026-08-03T18:30:00",      # o "start"; ISO 8601
      "fin":    "2026-08-03T20:00:00",      # o "end" (opcional)
      "ubicacion": "Campus UCC",            # opcional
      "descripcion": "..."                  # opcional
    }

Pruebas: fija la fecha "de hoy" con  --fecha 2026-08-03  o  JEFE_FAKE_HOY=2026-08-03
"""

import argparse
import json
import os
import sys
from datetime import datetime, date

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# --- rutas ------------------------------------------------------------------
AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_CALENDARIO = os.path.dirname(AQUI)                 # .../agenda/calendario
SALIDAS = os.path.join(DIR_CALENDARIO, "salidas")
SNAPSHOT = os.path.join(SALIDAS, "agenda_actual.json")


def hoy(args_fecha=None):
    """Fecha 'de hoy', con soporte de override para pruebas."""
    override = args_fecha or os.environ.get("JEFE_FAKE_HOY")
    if override:
        return datetime.strptime(override.strip(), "%Y-%m-%d").date()
    return date.today()


def _primer_campo(evento, *nombres, defecto=""):
    for n in nombres:
        if n in evento and evento[n]:
            return evento[n]
    return defecto


def _parse_dt(valor):
    """Convierte un string ISO en (fecha 'YYYY-MM-DD', hora 'HH:MM') tolerante."""
    if not valor:
        return "", ""
    s = str(valor).strip().replace("Z", "")
    # separa fecha y hora sin depender de zona horaria
    if "T" in s:
        f, _, h = s.partition("T")
    elif " " in s:
        f, _, h = s.partition(" ")
    else:
        f, h = s, ""
    hora = h[:5] if len(h) >= 5 else ""
    return f, hora


def normalizar(eventos, fecha_hoy, ventana_dias):
    """Devuelve la lista de eventos normalizados dentro de la ventana."""
    salida = []
    for ev in eventos:
        titulo = _primer_campo(ev, "titulo", "summary", "title", defecto="(sin título)")
        inicio = _primer_campo(ev, "inicio", "start", "start_time")
        fin = _primer_campo(ev, "fin", "end", "end_time")
        fecha_ini, hora_ini = _parse_dt(inicio)
        _, hora_fin = _parse_dt(fin)

        if not fecha_ini:
            continue
        try:
            d = datetime.strptime(fecha_ini, "%Y-%m-%d").date()
        except ValueError:
            continue

        dias = (d - fecha_hoy).days
        if dias < 0 or dias > ventana_dias:
            continue  # fuera de la ventana

        salida.append({
            "titulo": titulo.strip(),
            "fecha": fecha_ini,
            "hora_inicio": hora_ini,
            "hora_fin": hora_fin,
            "dias_desde_hoy": dias,
            "cuando": _etiqueta_cuando(dias),
            "ubicacion": _primer_campo(ev, "ubicacion", "location"),
            "descripcion": _primer_campo(ev, "descripcion", "description"),
        })
    salida.sort(key=lambda e: (e["fecha"], e["hora_inicio"]))
    return salida


def _etiqueta_cuando(dias):
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "mañana"
    return f"en {dias} días"


def cargar_eventos(args):
    if args.eventos:
        with open(args.eventos, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            print("ERROR: no se recibieron eventos (ni --eventos ni stdin).",
                  file=sys.stderr)
            sys.exit(2)
        data = json.loads(raw)
    # acepta tanto una lista como {"eventos": [...]} o {"items": [...]}
    if isinstance(data, dict):
        data = data.get("eventos") or data.get("items") or []
    return data


def main():
    p = argparse.ArgumentParser(description="Genera el snapshot de agenda.")
    p.add_argument("--eventos", help="Archivo JSON con la lista de eventos.")
    p.add_argument("--fecha", help="Fecha 'de hoy' YYYY-MM-DD (pruebas).")
    p.add_argument("--ventana-dias", type=int, default=7,
                   help="Cuántos días hacia adelante incluir (def. 7).")
    args = p.parse_args()

    fecha_hoy = hoy(args.fecha)
    eventos = cargar_eventos(args)
    normalizados = normalizar(eventos, fecha_hoy, args.ventana_dias)

    os.makedirs(SALIDAS, exist_ok=True)
    snapshot = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "fecha_referencia": fecha_hoy.isoformat(),
        "ventana_dias": args.ventana_dias,
        "total_eventos": len(normalizados),
        "eventos": normalizados,
    }
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"Snapshot escrito: {SNAPSHOT}")
    print(f"  fecha de referencia: {fecha_hoy.isoformat()}")
    print(f"  eventos en ventana ({args.ventana_dias} días): {len(normalizados)}")
    for e in normalizados:
        hh = f" {e['hora_inicio']}" if e["hora_inicio"] else ""
        print(f"   - {e['fecha']}{hh}  {e['titulo']}  ({e['cuando']})")


if __name__ == "__main__":
    main()
