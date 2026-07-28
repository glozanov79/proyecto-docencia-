# contenido.schema.md — Contrato entre contenido y diseño
> `generar_presentacion.py` (diseño en código) lee un `contenido.json` con esta estructura.
> El paso con LLM SOLO produce este JSON: elige el `tipo` de cada diapositiva y entrega sus datos.
> No pone colores ni coordenadas — de eso se encarga el renderizador.

## Estructura raíz
```json
{
  "curso": "E-Financial",
  "semana": "Semana 1",
  "profesor": "Germán Lozano Vivas",
  "institucion": "Universidad Cooperativa de Colombia",
  "diapositivas": [ { "tipo": "...", ... }, ... ]
}
```
Cada diapositiva puede incluir `"notas_orador": "..."` (guion hablado, 4–8 líneas; va a las notas del PPTX, no a la diapositiva).

## Tipos de diapositiva y sus campos

| tipo | campos | render |
|---|---|---|
| `portada` | `titulo`, `subtitulo` | fondo verde a sangre, título grande |
| `agenda` | `titulo`, `frase_ancla`, `items[]` | lista numerada con círculos |
| `objetivos` | `titulo`, `frase_ancla`, `objetivos[]` | igual que agenda |
| `autores` | `titulo`, `frase_ancla`, `nodos[]` = `{anio,titulo,aporte}` | **línea de tiempo** (2–6 nodos) |
| `marco` | `titulo`, `frase_ancla`, `tarjetas[]` = `{titulo,texto}` | tarjetas (hasta 4) |
| `aplicacion_ia` | `titulo`, `frase_ancla`, `tarjetas[]` = `{titulo,texto}` | tarjetas (hasta 4) |
| `datos` | `titulo`, `frase_ancla`, `stats[]` = `{cifra,etiqueta,fuente}`, `grafico` = `{titulo,categorias[],valores[],num_format}` | stat callouts + gráfico nativo |
| `caso` | `titulo`, `frase_ancla`, `bloques[]` = `{etiqueta,texto}` (exactamente 4) | tarjeta de 4 bloques |
| `debate` | `titulo`, `frase_ancla`, `columna_a`/`columna_b` = `{titulo,puntos[]}` | dos columnas |
| `actividad` | `titulo`, `frase_ancla`, `tiempo`, `pasos[]` | pasos numerados + badge de tiempo |
| `sintesis` | `titulo`, `frase_ancla`, `ideas[]` (hasta 5) | 5 tarjetas numeradas |
| `cierre` | `titulo`, `frase_ancla`, `proximo_tema` | fondo verde (cierra el arco) |
| `referencias` | `titulo`, `items[]` | lista limpia, 2 columnas si es larga |

Cualquier `tipo` desconocido cae a un render genérico (título + `apoyos[]` en viñetas), así que el deck nunca se rompe.

## Reglas de datos (las hace cumplir el prompt de contenido)
- `frase_ancla`: afirmación completa ≤ 12 palabras (no un rótulo).
- Textos de apoyo: oraciones legibles ≤ 18 palabras.
- `cifra`: la cifra ya formateada como string ("USD 145 B", "~50 %").
- `grafico.valores`: números; `categorias` misma longitud.
- `nodos`, `tarjetas`, `bloques`, `ideas`, `pasos`: listas; el renderizador recorta al máximo permitido.
- Nunca objetos crudos ni texto placeholder.
