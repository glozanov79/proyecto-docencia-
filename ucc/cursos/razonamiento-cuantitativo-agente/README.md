# Mini-agente: Razonamiento Cuantitativo

Estructura de carpetas para el mini-agente de este curso. Este mismo patrón se replicará luego para los demás cursos (Finanzas Internacionales, IA e inversión, etc.), cada uno con su propia carpeta.

```
razonamiento-cuantitativo-agente/
├── config/
│   ├── curso.json          # Metadata del curso: universidad, horario, fecha de inicio
│   └── calendario.json     # Las 16 fechas de sesión + festivos/receso a considerar
├── temario/
│   └── programa_oficial.md # El mapa fijo de las 16 semanas con tema y recurso
├── registro/
│   └── continuidad.md      # Estado real de avance — se actualiza después de cada clase
├── salidas/
│   └── (vacío por ahora)   # Aquí quedará cada carpeta AAAA-MM-DD con presentación + videos + taller
└── scripts/
    └── generar_clase.py    # Punto de partida para Claude Code — falta implementar la generación real
```

## Próximo paso

Abrir esta carpeta en Claude Code y completar `scripts/generar_clase.py` para que:
1. Detecte si mañana toca clase
2. Genere el contenido real (presentación, videos, taller)
3. Guarde el resultado en `salidas/`
4. Actualice `registro/continuidad.md`
