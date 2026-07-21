"""
Genera la presentación (.pptx) a partir de un brief.md, llamando a la API de Claude.

Requiere:
- Variable de entorno ANTHROPIC_API_KEY
- node + pptxgenjs instalados (npm install -g pptxgenjs, o local en el proyecto)

Uso:
    python generar_presentacion.py salidas/2026-08-05/brief.md
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from pptx import Presentation

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

PLANTILLA_PATH = Path(__file__).resolve().parent.parent / "plantilla" / "plantilla_ucc_razonamiento_cuantitativo.pptx"


def leer_layouts_de_plantilla(ruta):
    """Lee la plantilla .pptx y extrae la descripción de cada layout desde sus notas."""
    if not ruta.exists():
        return None
    p = Presentation(str(ruta))
    layouts = []
    for i, slide in enumerate(p.slides, 1):
        nota = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else "(sin descripción)"
        layouts.append(f"{i}. {nota}")
    return "\n".join(layouts)

SYSTEM_PROMPT = """Eres un diseñador experto de presentaciones académicas en PowerPoint.
Vas a recibir el brief de una clase universitaria y debes devolver ÚNICAMENTE un script
completo de Node.js que use la librería pptxgenjs para generar la presentación.

REGLAS DE DISEÑO OBLIGATORIAS:
- pres.layout = "LAYOUT_WIDE" (13.3" x 7.5") ANTES de agregar slides
- Colores hex SIN "#" y sin 8 dígitos: usa "1A2E4C" no "#1A2E4C"
- PALETA INSTITUCIONAL UCC (usar siempre, no inventar otra):
  verde oscuro "1B4332" (fondos de énfasis), aguamarina "00A99D" (color principal de acento),
  verde claro "52B788" (acento secundario), gris "52525B" (texto secundario),
  fondos tenues: aguamarina claro "E6F7F6", verde claro "EAF7EE"
- NUNCA agregues líneas de acento bajo los títulos, ni barras de color decorativas,
  ni franjas laterales — son señas distintivas de "hecho por IA"
- NUNCA fondo crema/beige por defecto — usa blanco (FFFFFF) o la paleta institucional
- Títulos 32pt+, cuerpo de texto 16-20pt (NUNCA menos de 15pt — letra pequeña
  es ilegible proyectada en un salón de clase)
- Cada slide debe tener un ÍCONO REAL (no solo formas/círculos de color):
  usa react-icons renderizado a SVG, rasterizado con sharp a PNG (≥256px), e
  insértalo con addImage. No dependas solo de rectángulos y círculos de relleno
  para dar variedad visual — un ícono temático (lightbulb, layers, robot, etc.)
  comunica mejor que una forma geométrica vacía
- Cada slide debe tener algo visual (ícono real, gráfico, o forma bien usada)
  — nunca solo título + viñetas
- Viñetas: usa bullet:true en cada item, nunca el carácter "•" literal
- Márgenes mínimos de 0.5" desde los bordes del slide
- Usa slide.addNotes() para notas del profesor si aplica, nunca texto en un cuadro visible
- SIEMPRE incluye un slide de "Aplicaciones en la vida real y con IA" del tema —
  dos columnas: una con un ejemplo de uso real/profesional, otra con un ejemplo
  relacionado con inteligencia artificial (modelos, herramientas de IA, o su uso interno)

NOTA: además de la presentación, cada clase requiere dos entregables adicionales que
NO genera este script — se generan por fuera, con búsqueda real:
1. Una guía de 4-5 videos de YouTube reales y verificados (con título, link y por qué
   sirve para el tema), NUNCA inventados — deben confirmarse con una búsqueda real.
2. Un taller de 8-10 ejercicios en Moodle, alineado con los subtemas del brief.
"""

ESTRUCTURA_FALLBACK = """ESTRUCTURA ESPERADA (no se encontró plantilla — usando estructura por defecto,
NUNCA menos de 10-12 slides para una sesión de 3 horas):
1. Slide de título (tema + curso + fecha)
2. SI el brief trae "Notas de continuidad" con información real de una clase anterior:
   agrega 2-3 slides de "Recordemos la clase pasada". Si está vacío, omite este bloque.
3. Slide de agenda/objetivos de aprendizaje (del tema de HOY)
4-5. Un slide de contexto/introducción al tema
6-10. Contenido clave: UN SUBTEMA POR SLIDE, con desarrollo real
11. Slide de aplicación en la vida real y con IA (dos columnas)
12. Slide de ejercicio/actividad práctica
13. Slide de cierre con la estructura de la sesión y recursos
14. Slide final "La próxima clase" — abre la puerta al siguiente tema
"""


def construir_system_prompt(layouts_plantilla):
    if layouts_plantilla:
        estructura = f"""ESTRUCTURA ESPERADA — SIGUE EXACTAMENTE ESTOS LAYOUTS, EN ESTE ORDEN,
tomados de la plantilla oficial del curso (adapta el número de slides de contenido
según cuántos subtemas traiga el brief, repitiendo el layout que corresponda,
pero sin romper el orden general: portada → recordatorio (si aplica) → agenda →
contenido → aplicaciones → actividad → cierre → próxima clase):

{layouts_plantilla}

Usa la paleta y reglas de diseño de arriba para llenar cada layout con el contenido
real del brief — no inventes layouts nuevos que no estén en esta lista."""
    else:
        estructura = ESTRUCTURA_FALLBACK

    return f"""{SYSTEM_PROMPT}
{estructura}

Cada subtema del "Contenido clave" del brief merece su propio slide con desarrollo real
(2-4 puntos explicativos o un ejemplo trabajado), no solo el título del subtema.

Responde ÚNICAMENTE con el código JavaScript, sin explicaciones, sin markdown,
sin ```js — el código debe poder guardarse directamente en un archivo .js y ejecutarse."""


def llamar_api(brief_texto, api_key, system_prompt):
    payload = {
        "model": MODEL,
        "max_tokens": 8000,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": f"Brief de la clase:\n\n{brief_texto}\n\nGenera el script pptxgenjs completo."}
        ],
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")


def main():
    if len(sys.argv) != 2:
        print("Uso: python generar_presentacion.py <ruta_al_brief.md>")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: define la variable de entorno ANTHROPIC_API_KEY antes de correr esto.")
        sys.exit(1)

    brief_path = Path(sys.argv[1])
    brief_texto = brief_path.read_text(encoding="utf-8")
    salida_dir = brief_path.parent

    layouts_plantilla = leer_layouts_de_plantilla(PLANTILLA_PATH)
    if layouts_plantilla:
        print(f"Plantilla encontrada en: {PLANTILLA_PATH}")
    else:
        print(f"AVISO: no se encontró la plantilla en {PLANTILLA_PATH} — usando estructura por defecto.")

    system_prompt = construir_system_prompt(layouts_plantilla)

    print("Llamando a la API de Claude para generar el diseño...")
    codigo_js = llamar_api(brief_texto, api_key, system_prompt)

    script_js = salida_dir / "generador_slides.js"
    script_js.write_text(codigo_js, encoding="utf-8")

    pptx_salida = salida_dir / "presentacion.pptx"
    print(f"Ejecutando node para generar {pptx_salida}...")
    resultado = subprocess.run(
        ["node", str(script_js)],
        cwd=salida_dir,
        capture_output=True,
        text=True,
    )
    print(resultado.stdout)
    if resultado.returncode != 0:
        print("ERROR generando la presentación:")
        print(resultado.stderr)
        sys.exit(1)

    print(f"✓ Presentación generada en: {pptx_salida}")


if __name__ == "__main__":
    main()
