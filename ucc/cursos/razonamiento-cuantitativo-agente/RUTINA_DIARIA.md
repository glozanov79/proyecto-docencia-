# Rutina diaria — Razonamiento Cuantitativo

## Comando único (dáselo a Claude Code cada mañana)

```
Prepara la clase de mañana:

1. Ejecuta scripts/generar_clase.py para generar el brief del día
   (si no hay clase mañana, se detiene solo — no sigas con lo demás)

2. Con el contenido de ese brief.md, genera tú mismo (en esta sesión, sin
   llamar a ninguna API externa ni necesitar ANTHROPIC_API_KEY) los tres
   archivos en la misma carpeta salidas/AAAA-MM-DD/:

   a) presentacion.pptx — usando pptxgenjs, siguiendo exactamente los layouts
      de plantilla/plantilla_ucc_razonamiento_cuantitativo.pptx (lee sus notas
      con python-pptx para saber el orden y el propósito de cada slide) y las
      reglas de diseño que están en scripts/generar_presentacion.py (paleta
      UCC, íconos reales con react-icons+sharp, mínimo 10-12 slides, recordatorio
      de la clase pasada si aplica, cierre con adelanto del próximo tema)

   b) guia_videos.md — busca en internet 4-5 videos de YouTube REALES y
      verificados sobre el tema de la clase (nunca inventes links), con
      título, URL, y una línea de por qué sirve cada uno

   c) taller_semanaN.md Y taller_semanaN_import.csv — 8-10 ejercicios
      alineados con los subtemas del brief, en el formato de importación
      de preguntas que ya usamos antes (NewQuestion, ID, Title, QuestionText,
      Points, Difficulty, tipos MC/TF/SA/M/WR — revisa un taller anterior
      en salidas/ como referencia de formato si existe)

3. Muéstrame la lista de los 4 archivos generados (brief.md, presentacion.pptx,
   guia_videos.md, taller_semanaN_import.csv) con su ruta completa
```

Si no hay clase mañana (fin de semana, receso, festivo), el paso 1 se detiene solo y te avisa — no truena nada, simplemente no genera contenido ese día.

## Qué vas a encontrar en salidas/AAAA-MM-DD/ al terminar

- `brief.md` — el resumen de la clase
- `generador_slides.js` — el código que arma la presentación
- `presentacion.pptx` — la presentación final, lista para proyectar
- `guia_videos.md` — 4-5 videos de YouTube reales sobre el tema
- `taller_semanaN.md` y `taller_semanaN_import.csv` — el taller, listo para importar al repositorio de preguntas

## Después de dictar la clase (importante para la continuidad)

Actualiza manualmente `registro/continuidad.md` con lo que realmente pasó:
- Qué se alcanzó a ver
- Qué quedó pendiente
- Cualquier ajuste de fecha

Esto es lo que alimenta el "recordemos la clase pasada" de la semana siguiente — si no lo actualizas, ese bloque queda vacío.
