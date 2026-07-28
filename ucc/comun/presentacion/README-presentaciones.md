# Sistema de presentaciones — dos pasos

El diseño ya no depende de que el modelo "recuerde" aplicarlo. Se separa en dos:

```
  perfil.md  +  datos de sesión  +  prompt-generar-contenido.md
                        │
                        ▼   (paso 1 · LLM)
                  contenido.json          ← QUÉ decir y QUÉ tipo de diapositiva
                        │
                        ▼   (paso 2 · Python determinista)
            generar_presentacion.py       ← CÓMO se ve (paleta, tipografía, layout)
                        │
                        ▼
                  presentacion.pptx
```

- **Paso 1 (contenido):** el LLM lee las tres capas y produce `contenido.json` (ver `contenido.schema.md`). Elige `tipo` por diapositiva y entrega los datos. No toca colores ni coordenadas.
- **Paso 2 (diseño):** `generar_presentacion.py` renderiza ese JSON con la identidad UCC fija en código. La función que dibuja cada tipo (portada, autores, caso, datos…) pinta siempre el verde y el layout correctos → **no puede salir feo ni azul**.

## Requisito
```
pip install python-pptx
```

## Ejecutar
```
python generar_presentacion.py contenido.json presentacion.pptx
```
Prueba incluida:
```
python generar_presentacion.py ejemplo_contenido.json demo.pptx
```

## Personalizar el diseño (un solo lugar)
En `generar_presentacion.py`, arriba:
- Bloque **PALETA**: reemplaza los HEX por los oficiales de la UCC.
- Constante **FONT**: pon la tipografía de la plantilla institucional.
Cambias eso una vez y aplica a los 7 cursos.

## Archivos
- `generar_presentacion.py` — renderizador (diseño en código).
- `contenido.schema.md` — contrato JSON (tipos de diapositiva y campos).
- `prompt-generar-contenido.md` — prompt del paso 1.
- `ejemplo_contenido.json` — ejemplo funcional (E-Financial, Semana 1).
- `perfiles/perfil-*.md` — capa 2, uno por curso.
