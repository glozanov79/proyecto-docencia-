"""
Jefe UCC — super agente orquestador.
Supervisa todos los mini-agentes de curso registrados en config/cursos.json.
No genera contenido él mismo: decide cuál(es) mini-agente(s) deben activarse,
y opcionalmente los ejecuta.

Cada curso define en su config/curso.json cuántos días de anticipación
necesita (campo "dias_anticipacion", 1 por defecto) — así un curso puede
prepararse una semana antes y otro un día antes, cada uno con su propio ritmo.

Uso:
    python jefe.py            -> solo muestra qué cursos tienen clase próxima
    python jefe.py --ejecutar -> además corre generar_clase.py de cada uno
    python jefe.py --fecha 2026-07-29 --ejecutar
                               -> simula que "hoy" es esa fecha (para pruebas)
"""

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent


def hoy():
    fake = os.environ.get("JEFE_FAKE_HOY")
    return date.fromisoformat(fake) if fake else date.today()


def cargar_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def sesion_para(fecha_iso, calendario):
    for s in calendario["sesiones"]:
        if s["fecha"] == fecha_iso:
            return s
    return None


def revisar_curso(curso_info):
    carpeta = (BASE / curso_info["carpeta"]).resolve()
    curso_path = carpeta / "config" / "curso.json"
    calendario_path = carpeta / "config" / "calendario.json"

    if not calendario_path.exists():
        return {"nombre": curso_info["nombre"], "estado": "sin_calendario", "carpeta": carpeta}

    anticipacion = cargar_json(curso_path).get("dias_anticipacion", 1) if curso_path.exists() else 1
    fecha_objetivo = (hoy() + timedelta(days=anticipacion)).isoformat()

    calendario = cargar_json(calendario_path)
    sesion = sesion_para(fecha_objetivo, calendario)

    base = {"nombre": curso_info["nombre"], "carpeta": carpeta, "fecha": fecha_objetivo, "anticipacion": anticipacion}

    if sesion is None:
        return {**base, "estado": "sin_clase"}

    nota = sesion.get("nota")
    if nota and any(k in nota.lower() for k in ("receso", "festivo", "cancelada", "suspendida")):
        return {**base, "estado": "receso_festivo", "nota": nota}

    return {**base, "estado": "clase_proxima", "semana": sesion["semana"]}


def main():
    ejecutar = "--ejecutar" in sys.argv

    if "--fecha" in sys.argv:
        os.environ["JEFE_FAKE_HOY"] = sys.argv[sys.argv.index("--fecha") + 1]

    cursos = cargar_json(BASE / "config" / "cursos.json")["cursos"]

    print(f"Jefe UCC — revisando {len(cursos)} curso(s) registrado(s) (hoy: {hoy().isoformat()})\n")

    pendientes = []
    for curso_info in cursos:
        if not curso_info.get("activo", True):
            continue
        resultado = revisar_curso(curso_info)
        cuando = f"{resultado['fecha']} (en {resultado['anticipacion']} día(s))" if "fecha" in resultado else ""

        if resultado["estado"] == "clase_proxima":
            print(f"✓ {resultado['nombre']}: clase el {cuando} — semana {resultado['semana']} — ACCIÓN REQUERIDA")
            pendientes.append(resultado)
        elif resultado["estado"] == "receso_festivo":
            print(f"— {resultado['nombre']}: receso/festivo el {cuando} ({resultado['nota']}) — sin acción")
        elif resultado["estado"] == "sin_clase":
            print(f"— {resultado['nombre']}: sin clase el {cuando}")
        else:
            print(f"⚠ {resultado['nombre']}: no se encontró config/calendario.json en {resultado['carpeta']}")

    if not pendientes:
        print("\nNada que preparar por ahora en ningún curso.")
        return

    print(f"\n{len(pendientes)} curso(s) requieren preparar la próxima clase.")

    if ejecutar:
        api_disponible = bool(os.environ.get("ANTHROPIC_API_KEY"))
        for p in pendientes:
            print(f"\n--- Ejecutando generar_clase.py de {p['nombre']} ---")
            resultado = subprocess.run(
                [sys.executable, "scripts/generar_clase.py"],
                cwd=p["carpeta"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            print(resultado.stdout)
            if resultado.returncode != 0:
                print(f"ERROR en {p['nombre']}:")
                print(resultado.stderr)
                continue

            marcador = p["carpeta"] / "salidas" / "ULTIMO_BRIEF.txt"
            if not marcador.exists():
                continue
            brief_path = p["carpeta"] / marcador.read_text(encoding="utf-8").strip()
            if not brief_path.exists():
                continue

            if not api_disponible:
                print("(ANTHROPIC_API_KEY no configurada — se omite presentación/taller/videos)")
                continue

            for script_extra in ("generar_presentacion.py", "generar_taller.py", "generar_videos.py"):
                print(f"\n--- Ejecutando {script_extra} de {p['nombre']} ---")
                r = subprocess.run(
                    [sys.executable, f"scripts/{script_extra}", str(brief_path)],
                    cwd=p["carpeta"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                print(r.stdout)
                if r.returncode != 0:
                    print(f"ERROR en {script_extra}:")
                    print(r.stderr)
    else:
        print("Corre con --ejecutar para generar los briefs automáticamente.")


if __name__ == "__main__":
    main()
