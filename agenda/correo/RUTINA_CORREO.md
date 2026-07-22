# RUTINA_CORREO.md — Agente Correo (depende de Calendario)

**Comando de disparo:** "revisa mi correo"

> ⚠️ **Dependencia dura:** este agente NO revisa correo sin un snapshot
> **fresco** de la agenda. Si el snapshot falta o está viejo, primero corre
> el agente calendario (RUTINA_AGENDA.md).

## Paso 0 — Verificar la dependencia (obligatorio)
```bash
python correo/scripts/contexto_correo.py validar-frescura --horas 2
```
- Si responde **BLOQUEADO** → corre `RUTINA_AGENDA.md` y vuelve aquí.
- Si responde **OK** → continúa.

## Paso 1 — Cargar el contexto de agenda
```bash
python correo/scripts/contexto_correo.py contexto
```
Claude (Cadmo) lee ese bloque para tener presente qué clases/reuniones ya
existen mientras lee los correos.

## Paso 2 — Leer el correo (Gmail)
Revisar dos frentes en la cuenta `lozanogerman79@gmail.com`:
1. **Etiqueta `outlook-reenviado`** (correo institucional que Power Automate
   reenvía desde Outlook). Tras revisar, mover a papelera lo ya atendido.
2. **Inbox personal**, para lo que llegue directo a Gmail.

Para cada correo relevante, Claude extrae: remitente, asunto, **fecha
detectada** (si el texto menciona una), y palabras clave.

## Paso 3 — Clasificar prioridad
Aplicar `config/criterios.json` (alta / media / baja; la fecha límite
explícita sube un nivel). Reglas evaluadas de alta a baja: gana el primer
bloque que coincide.

## Paso 4 — Cruzar contra la agenda
```bash
python correo/scripts/contexto_correo.py cruzar --candidatos correos.json
```
El script devuelve tres grupos:
- **ya_en_agenda** → el correo se refiere a un evento que YA existe (solo
  informar; no proponer nada nuevo).
- **proponer_nuevo_evento** → trae una fecha que NO está en el calendario →
  Cadmo lo destaca como "agendar" (crear evento requiere tu confirmación
  explícita; nunca se crea solo).
- **sin_fecha_detectada** → solo clasificar y resumir.

## Paso 5 — Entregar el brief y registrar
Claude escribe el resumen en `correo/salidas/ULTIMA_REVISION.md`:
- Bloque por prioridad (alta primero).
- Por cada correo: remitente · asunto · prioridad · acción sugerida · si
  cruza con la agenda o propone evento nuevo.
- Al final: lista de "eventos a agendar" pendientes de tu confirmación.

## Límites
- **Nunca** se envían, borran definitivamente ni responden correos sin tu OK
  explícito por chat. Mover a papelera lo ya revisado de `outlook-reenviado`
  sí es parte de la rutina.
- **Nunca** se crea un evento de calendario sin tu confirmación.
- Pruebas: `JEFE_FAKE_HOY=2026-08-03`.
