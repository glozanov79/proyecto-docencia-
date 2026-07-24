"""
Mini-agente: Razonamiento Cuantitativo
Genera brief.md para la próxima sesión y actualiza el registro de continuidad.
NO produce presentaciones, imágenes ni ningún otro formato.
"""

import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent


def hoy():
    fake = os.environ.get("JEFE_FAKE_HOY")
    return date.fromisoformat(fake) if fake else date.today()


# ── Carga de archivos ──────────────────────────────────────────────────────

def cargar_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def leer_texto(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


# ── Lógica de calendario ───────────────────────────────────────────────────

def sesion_para(fecha_iso, calendario):
    for s in calendario["sesiones"]:
        if s["fecha"] == fecha_iso:
            return s
    return None


def es_receso_o_festivo(nota):
    if not nota:
        return False
    keywords = ("receso", "festivo", "no hay clase", "cancelada", "suspendida")
    return any(k in nota.lower() for k in keywords)


# ── Parseo del temario ─────────────────────────────────────────────────────

def tema_de_semana(semana, programa_md):
    """Extrae tema y recurso de la fila correspondiente a la semana en la tabla md."""
    for linea in programa_md.splitlines():
        partes = [c.strip() for c in linea.split("|") if c.strip()]
        if len(partes) >= 2 and partes[0] == str(semana):
            tema = partes[1] if len(partes) > 1 else "—"
            recurso = partes[2] if len(partes) > 2 else "—"
            return tema, recurso
    return "—", "—"


def objetivos_desde_tema(tema):
    """Genera objetivos de aprendizaje a partir del tema."""
    subtemas = [t.strip() for t in re.split(r"[;.]", tema) if t.strip()]
    objetivos = []
    for s in subtemas[:4]:
        objetivos.append(f"- Comprender y aplicar: {s.lower()}")
    objetivos.append("- Relacionar el tema con el proyecto de investigación del curso")
    return "\n".join(objetivos)


def contenido_clave_desde_tema(tema):
    """Convierte el tema en una lista de puntos de contenido."""
    subtemas = [t.strip() for t in re.split(r"[;.]", tema) if t.strip()]
    return "\n".join(f"- {s}" for s in subtemas)


# ── Generación del brief ───────────────────────────────────────────────────

def generar_brief(fecha_iso, sesion, curso, continuidad_md, programa_md):
    semana = sesion["semana"]
    tema, recurso = tema_de_semana(semana, programa_md)
    objetivos = objetivos_desde_tema(tema)
    contenido = contenido_clave_desde_tema(tema)

    tema_siguiente, _ = tema_de_semana(semana + 1, programa_md)
    proximo_tema = tema_siguiente if tema_siguiente != "—" else "Cierre del curso / no aplica"

    estructura = (
        f"- {curso['estructura_sesion']['presentacion_minutos']} min — presentación del tema\n"
        f"- {curso['estructura_sesion']['ejercicios_profesor_minutos']} min — ejercicios resueltos por el profesor\n"
        f"- {curso['estructura_sesion']['ejercicios_estudiantes_minutos']} min — ejercicios de los estudiantes"
    )

    nota = sesion.get("nota")
    alerta = f"\n## ⚠ Alerta de calendario\n{nota}\n" if nota else ""

    brief = f"""# Brief de clase — Semana {semana}
{alerta}
## Semana y fecha
- Semana: {semana} de {curso['duracion_semanas']}
- Fecha: {fecha_iso} ({curso['dia_clase']})
- Horario real: {curso['horario_real']} ({curso['duracion_real_minutos']} min efectivos)
- Curso: {curso['curso']} — {curso['universidad']}

## Tema de la clase
{tema}

## Objetivos de aprendizaje
{objetivos}

## Contenido clave a cubrir
{contenido}

### Estructura sugerida de la sesión
{estructura}

## Recursos oficiales del temario
- {recurso}

## Próximo tema (para el slide de cierre "La próxima clase")
{proximo_tema}

## Notas de continuidad
{continuidad_md.strip()}
"""
    return brief


# ── Actualización de continuidad ───────────────────────────────────────────

def actualizar_continuidad(fecha_iso, semana, tema, ruta):
    texto = leer_texto(ruta)

    def reemplazar(campo, valor):
        # campo se pasa SIN escapar — re.escape() se encarga aquí adentro.
        # El formato real del archivo es **campo:** (los dos puntos dentro del negrita).
        patron = rf"(\*\*{re.escape(campo)}:\*\*).*"
        return re.sub(patron, rf"\1 {valor}", texto)

    texto = reemplazar("Semana actual", f"{semana} (brief generado)")
    texto = reemplazar(
        "Próxima clase (semana + tema según el mapa)",
        f"Semana {semana} — {fecha_iso}"
    )

    estado_linea = f"**Estado de preparación semana {semana}:** brief generado ✓ (`salidas/Semana {semana:02d} - {fecha_iso}/brief.md`)"
    if "Estado de preparación semana" not in texto:
        texto = texto.rstrip() + f"\n{estado_linea}\n"
    else:
        texto = re.sub(
            r"\*\*Estado de preparación semana \d+:\*\*.*",
            estado_linea,
            texto
        )

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    curso = cargar_json(BASE / "config" / "curso.json")
    calendario = cargar_json(BASE / "config" / "calendario.json")

    # No generar viernes ni sábados
    dia_semana = hoy().weekday()  # 0=lunes, 4=viernes, 5=sábado
    if dia_semana in [4, 5]:
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        print(f"Hoy es {dias[dia_semana]}. No se genera material los viernes ni sábados.")
        return

    print(f"Mini-agente listo para: {curso['curso']} ({curso['universidad']})")
    print(f"Sesiones cargadas: {len(calendario['sesiones'])}")

    anticipacion = curso.get("dias_anticipacion", 1)
    fecha_objetivo = (hoy() + timedelta(days=anticipacion)).isoformat()
    sesion = sesion_para(fecha_objetivo, calendario)

    if sesion is None:
        print(f"Sin clase el {fecha_objetivo} (en {anticipacion} día(s)). Nada que preparar.")
        return

    nota = sesion.get("nota")
    if nota:
        print(f"AVISO — Semana {sesion['semana']} ({fecha_objetivo}) tiene una alerta de calendario:")
        print(f"  → {nota}")
        print("  Se genera el contenido de todas formas; la alerta queda en el brief.")

    print(f"Clase próxima: semana {sesion['semana']} — {fecha_objetivo} (en {anticipacion} día(s))")

    continuidad_md = leer_texto(BASE / "registro" / "continuidad.md")
    programa_md = leer_texto(BASE / "temario" / "programa_oficial.md")

    nombre_carpeta = f"Semana {sesion['semana']:02d} - {fecha_objetivo}"
    salida_dir = BASE / "salidas" / nombre_carpeta
    salida_dir.mkdir(parents=True, exist_ok=True)
    brief = generar_brief(fecha_objetivo, sesion, curso, continuidad_md, programa_md)
    (salida_dir / "brief.md").write_text(brief, encoding="utf-8")
    print(f"brief.md generado en: salidas/{nombre_carpeta}/brief.md")

    (BASE / "salidas" / "ULTIMO_BRIEF.txt").write_text(
        f"salidas/{nombre_carpeta}/brief.md", encoding="utf-8"
    )

    ruta_continuidad = BASE / "registro" / "continuidad.md"
    tema, _ = tema_de_semana(sesion["semana"], programa_md)
    actualizar_continuidad(fecha_objetivo, sesion["semana"], tema, ruta_continuidad)
    print("registro/continuidad.md actualizado.")


if __name__ == "__main__":
    main()
