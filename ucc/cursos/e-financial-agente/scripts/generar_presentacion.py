"""Genera presentacion PowerPoint profesional desde brief."""

import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def leer_brief(ruta):
    return Path(ruta).read_text(encoding="utf-8") if Path(ruta).exists() else None

def extraer_campo(texto, titulo):
    inicio = texto.find(f"## {titulo}")
    if inicio == -1:
        return ""
    inicio = texto.find("\n", inicio) + 1
    fin = texto.find("\n## ", inicio)
    if fin == -1:
        fin = len(texto)
    return texto[inicio:fin].strip()

def crear_presentacion(brief_path):
    brief = leer_brief(brief_path)
    if not brief:
        print(f"ERROR: No se pudo leer {brief_path}")
        return False

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    COLOR_PRINCIPAL = RGBColor(0, 102, 204)
    COLOR_TEXTO = RGBColor(51, 51, 51)

    def agregar_slide_titulo(titulo, subtitulo=""):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = COLOR_PRINCIPAL

        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(2))
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(54)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

        if subtitulo:
            sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.8), Inches(9), Inches(1.5))
            sub_frame = sub_box.text_frame
            sub_frame.word_wrap = True
            p = sub_frame.paragraphs[0]
            p.text = subtitulo
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(220, 220, 220)

    def agregar_slide_contenido(titulo, items):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        barra = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.8))
        barra.fill.solid()
        barra.fill.fore_color.rgb = COLOR_PRINCIPAL
        barra.line.color.rgb = COLOR_PRINCIPAL

        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9), Inches(0.6))
        title_frame = title_box.text_frame
        p = title_frame.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

        content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(8.4), Inches(5.8))
        content_frame = content_box.text_frame
        content_frame.word_wrap = True

        for item in items:
            if item.strip():
                p = content_frame.add_paragraph()
                p.text = item.strip().lstrip("-").strip()
                p.font.size = Pt(18)
                p.font.color.rgb = COLOR_TEXTO
                p.space_before = Pt(6)
                p.space_after = Pt(6)

    tema = extraer_campo(brief, "Tema de la clase").split('\n')[0]
    semana_info = extraer_campo(brief, "Semana y fecha")
    objetivos_texto = extraer_campo(brief, "Objetivos de aprendizaje")
    contenido_texto = extraer_campo(brief, "Contenido clave a cubrir")
    recursos_texto = extraer_campo(brief, "Recursos oficiales del temario")
    proximo_tema = extraer_campo(brief, "Proxima tema")

    fecha = ""
    for linea in semana_info.split('\n'):
        if "Fecha:" in linea:
            fecha = linea.split("Fecha:")[1].strip()
            break

    agregar_slide_titulo(tema, f"Semana 1\n{fecha}")
    agregar_slide_contenido("Agenda", ["Objetivos", "Contenido", "Actividades", "Recursos"])
    
    objetivos = [l.strip() for l in objetivos_texto.split('\n') if l.strip()]
    agregar_slide_contenido("Objetivos", objetivos)

    agregar_slide_contenido("Tema", [tema])
    
    contenido = [l.strip() for l in contenido_texto.split('\n') if l.strip()]
    agregar_slide_contenido("Contenido Clave", contenido[:6])

    recursos = [l.strip() for l in recursos_texto.split('\n') if l.strip()]
    agregar_slide_contenido("Recursos", recursos if recursos else [recursos_texto])

    agregar_slide_contenido("Actividades", ["Presentacion", "Ejercicios profesor", "Actividades grupo", "Q&A"])
    agregar_slide_contenido("Proxima Clase", [proximo_tema if proximo_tema else "Siguiente tema"])
    agregar_slide_contenido("Cierre", ["Resumen", "Preguntas", "Tareas"])

    output_dir = Path(brief_path).parent
    output_path = output_dir / "presentacion.pptx"
    prs.save(str(output_path))
    print(f"OK: presentacion.pptx")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_presentacion.py <ruta_brief>")
        sys.exit(1)
    crear_presentacion(sys.argv[1])
