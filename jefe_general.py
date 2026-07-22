"""
Jefe general — orquesta a los jefes de cada institución/dominio (ucc, unad, agenda).
No conoce cursos ni calendarios directamente — solo sabe qué "jefes" existen
y los ejecuta, mostrando el resultado de cada uno.

Uso:
    python jefe_general.py             -> revisa todos los jefes disponibles
    python jefe_general.py --ejecutar  -> además ejecuta lo que cada jefe indique
    python jefe_general.py --fecha 2026-08-04 --ejecutar
                                        -> simula que "hoy" es esa fecha (para pruebas)
"""

import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent

# Cada entrada es una carpeta hermana que debe tener su propio jefe.py
DOMINIOS = ["ucc", "unad", "agenda"]


def main():
    ejecutar = "--ejecutar" in sys.argv

    if "--fecha" in sys.argv:
        fecha_fake = sys.argv[sys.argv.index("--fecha") + 1]
        os.environ["JEFE_FAKE_HOY"] = fecha_fake
        print(f"(simulando 'hoy' = {fecha_fake})\n")

    # dominios que aceptan --ejecutar (los que tienen cursos que generar)
    SOPORTAN_EJECUTAR = {"ucc", "unad"}

    print("Jefe general — revisando todos los dominios registrados\n")

    for dominio in DOMINIOS:
        carpeta = BASE / dominio
        jefe_path = carpeta / "jefe.py"

        if not jefe_path.exists():
            print(f"— {dominio}: sin jefe.py todavía (pendiente de construir)\n")
            continue

        print(f"=== {dominio.upper()} ===")
        args = ["--ejecutar"] if (ejecutar and dominio in SOPORTAN_EJECUTAR) else []
        resultado = subprocess.run(
            [sys.executable, "jefe.py"] + args,
            cwd=carpeta,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(resultado.stdout)

        if dominio == "agenda":
            # agenda/jefe.py usa el código de salida como estado de negocio,
            # no como señal de error: 0 = correo habilitado, 1 = bloqueado
            # porque falta un snapshot de calendario fresco. Ninguno de los
            # dos casos es un fallo del script — solo un código fuera de
            # {0, 1} indica un error real.
            if resultado.returncode not in (0, 1):
                print(f"ERROR en el jefe de {dominio} (código {resultado.returncode}):")
                print(resultado.stderr)
        elif resultado.returncode != 0:
            print(f"ERROR en el jefe de {dominio}:")
            print(resultado.stderr)
        print()


if __name__ == "__main__":
    main()
