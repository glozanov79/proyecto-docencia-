#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_contenido.py  ·  PASO 1 del pipeline de presentaciones
---------------------------------------------------------------------------
Lee el brief de la clase, llama a Claude (API) con el prompt de contenido +
el perfil del curso, y GUARDA un contenido.json conforme a contenido.schema.md.
El renderizado (paso 2) lo hace generar_presentacion.py sobre ese JSON.

Uso:
    python generar_contenido.py <brief.md> [salida_contenido.json]

Requiere:
    - variable de entorno ANTHROPIC_API_KEY
    - pip install anthropic
Busca el perfil del curso (perfil.md) subiendo desde la carpeta del brief.
"""
import sys, os, json, re
from pathlib import Path
import anthropic

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000

# Ruta del módulo común (este archivo vive en ucc/comun/presentacion/)
AQUI = Path(__file__).resolve().parent
PROMPT_CONTENIDO = AQUI / "prompt-generar-contenido.md"
ESQUEMA = AQUI / "contenido.schema.md"


def _leer(p):
    return Path(p).read_text(encoding="utf-8") if Path(p).exists() else ""


def _buscar_perfil(brief_path):
    """Sube desde la carpeta del brief buscando un perfil.md (el del curso)."""
    d = Path(brief_path).resolve().parent
    for carpeta in [d, *d.parents]:
        cand = carpeta / "perfil.md"
        if cand.exists():
            return cand.read_text(encoding="utf-8")
        # no subir más allá de ucc/
        if carpeta.name == "ucc":
            break
    return "(sin perfil.md — usa criterios genéricos de la disciplina)"


def _extraer_json(texto):
    """Devuelve el objeto JSON aunque venga con ```json o texto alrededor."""
    t = texto.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        a, b = t.find("{"), t.rfind("}")
        if a != -1 and b != -1:
            return json.loads(t[a:b + 1])
        raise


def generar_contenido(brief_path, salida_path):
    brief = _leer(brief_path)
    if not brief:
        raise SystemExit(f"No se encontró/leyó el brief: {brief_path}")

    perfil = _buscar_perfil(brief_path)
    prompt_base = _leer(PROMPT_CONTENIDO)
    esquema = _leer(ESQUEMA)

    prompt = (
        f"{prompt_base}\n\n"
        f"=== CONTRATO (contenido.schema.md) ===\n{esquema}\n\n"
        f"=== PERFIL DEL CURSO (capa 2) ===\n{perfil}\n\n"
        f"=== BRIEF DE LA SESIÓN (capa 3) ===\n{brief}\n\n"
        "Devuelve SOLO el objeto JSON conforme al esquema, sin ```json ni texto adicional."
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Falta la variable de entorno ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = message.content[0].text.strip()
    print(f"DEBUG: Claude respondió con {len(texto)} caracteres")

    data = _extraer_json(texto)
    if "diapositivas" not in data or not isinstance(data["diapositivas"], list):
        raise SystemExit("El JSON no tiene una lista 'diapositivas' — revisa el prompt.")
    print(f"DEBUG: JSON parseado — {len(data['diapositivas'])} diapositivas")

    Path(salida_path).parent.mkdir(parents=True, exist_ok=True)
    Path(salida_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK · contenido guardado en {salida_path}")
    return salida_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_contenido.py <brief.md> [salida_contenido.json]")
        sys.exit(1)
    brief = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else str(Path(brief).parent / "salidas" / "contenido.json")
    generar_contenido(brief, salida)
