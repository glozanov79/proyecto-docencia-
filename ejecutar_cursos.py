#!/usr/bin/env python3
"""Ejecutar cursos específicos y generar todo el material."""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent / "ucc" / "cursos"

cursos = [
    "e-financial-agente",
    "pensamiento-economico-agente"
]

for curso in cursos:
    print(f"\n{'='*60}")
    print(f"Ejecutando: {curso}")
    print('='*60)

    # 1. Generar brief
    print("\n[1/4] Generando brief...")
    resultado = subprocess.run(
        [sys.executable, "scripts/generar_clase.py"],
        cwd=BASE / curso,
        text=True
    )

    if resultado.returncode != 0:
        print(f"Error en {curso}")
        continue

    # Obtener ruta del brief generado
    ultimo_brief = (BASE / curso / "salidas" / "ULTIMO_BRIEF.txt").read_text().strip()
    brief_path = BASE / curso / ultimo_brief

    if not brief_path.exists():
        print(f"Brief no encontrado: {brief_path}")
        continue

    # 2. Generar presentación
    print("[2/4] Generando presentación...")
    subprocess.run(
        [sys.executable, "scripts/generar_presentacion.py", str(brief_path)],
        cwd=BASE / curso,
        text=True
    )

    # 3. Generar taller
    print("[3/4] Generando taller...")
    subprocess.run(
        [sys.executable, "scripts/generar_taller.py", str(brief_path)],
        cwd=BASE / curso,
        text=True
    )

    # 4. Generar videos
    print("[4/4] Generando videos...")
    subprocess.run(
        [sys.executable, "scripts/generar_videos.py", str(brief_path)],
        cwd=BASE / curso,
        text=True
    )

    print(f"\nOK: {curso} - Material completo generado")

print("\n" + "="*60)
print("Proceso finalizado - Todo el material fue generado")
print("="*60)
