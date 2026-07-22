#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jefe.py  —  Jefe del dominio AGENDA.

Orquesta dos agentes con una dependencia estricta:

        calendario  ──(produce snapshot)──▶  correo
        (agenda)                             (depende del snapshot)

El correo NUNCA se revisa sin un snapshot de agenda fresco. Este jefe lo
verifica y, si falta, bloquea el paso de correo y te dice qué correr.

Igual que en ucc/jefe.py, este script NO ejecuta los conectores (Gmail /
Google Calendar); eso lo hace Claude en la conversación siguiendo las RUTINAS.
El jefe lee config, valida el estado y te imprime el PROTOCOLO en orden.

Uso:
    python jefe.py                 # imprime el protocolo del día (orden + estado)
    python jefe.py --estado        # solo el estado de dependencia (fresco/bloqueado)
    python jefe.py --fecha 2026-08-03   # para pruebas
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(AQUI, "config", "agenda.json")
CONTEXTO_CORREO = os.path.join(AQUI, "correo", "scripts", "contexto_correo.py")


def cargar_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def estado_dependencia(cfg, fecha=None):
    """Corre la validación de frescura del agente correo y devuelve (ok, texto)."""
    horas = str(cfg.get("frescura_snapshot_horas", 2))
    env = dict(os.environ)
    if fecha:
        env["JEFE_FAKE_HOY"] = fecha
    try:
        r = subprocess.run(
            [sys.executable, CONTEXTO_CORREO, "validar-frescura", "--horas", horas],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
    except Exception as e:  # pragma: no cover
        return False, f"No se pudo validar el snapshot: {e}"
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def imprimir_protocolo(cfg, fecha=None):
    orden = cfg.get("orden_ejecucion", ["calendario", "correo"])
    rutas = cfg.get("rutas", {})
    ok, detalle = estado_dependencia(cfg, fecha)

    print("=" * 64)
    print(" JEFE AGENDA — protocolo del día")
    print(f" generado: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 64)
    print(f" Orden de ejecución: {' -> '.join(orden)}")
    print(f" Dependencia: correo requiere snapshot de calendario "
          f"< {cfg.get('frescura_snapshot_horas', 2)} h\n")

    print(" PASO 1 · CALENDARIO (agenda)")
    print(f"   Rutina: {rutas.get('rutina_calendario')}")
    print("   Claude lee Google Calendar (conector) y corre:")
    print("     python calendario/scripts/snapshot_agenda.py --eventos <eventos.json>")
    print(f"   Deja: {rutas.get('snapshot_agenda')}\n")

    print(" PASO 2 · CORREO  (depende del PASO 1)")
    if ok:
        print("   ESTADO: ✔ snapshot fresco — se puede revisar el correo.")
        print(f"   {detalle}")
        print(f"   Rutina: {rutas.get('rutina_correo')}")
        print("   Claude lee Gmail (etiqueta 'outlook-reenviado' + inbox) y corre:")
        print("     python correo/scripts/contexto_correo.py contexto")
        print("     python correo/scripts/contexto_correo.py cruzar --candidatos <correos.json>")
        print(f"   Deja: {rutas.get('ultima_revision_correo')}")
    else:
        print("   ESTADO: ✖ BLOQUEADO — falta snapshot fresco de calendario.")
        print(f"   {detalle}")
        print("   -> Ejecuta primero el PASO 1 y vuelve a correr el jefe.")
    print("=" * 64)
    return ok


def main():
    p = argparse.ArgumentParser(description="Jefe del dominio agenda.")
    p.add_argument("--estado", action="store_true",
                   help="Solo estado de dependencia (código de salida 0/1).")
    p.add_argument("--fecha", help="Fecha 'de hoy' YYYY-MM-DD (pruebas).")
    args = p.parse_args()

    cfg = cargar_config()
    if args.estado:
        ok, detalle = estado_dependencia(cfg, args.fecha)
        print(detalle)
        sys.exit(0 if ok else 1)

    ok = imprimir_protocolo(cfg, args.fecha)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
