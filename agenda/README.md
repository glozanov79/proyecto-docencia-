# Dominio `agenda`

Tercer dominio de `proyecto-docencia/`, junto a `ucc/` y `unad/`. Lo invoca
`jefe_general.py`. Contiene dos agentes con **dependencia estricta**:

```
agenda/
├── jefe.py                      # orquesta y FUERZA el orden calendario → correo
├── config/
│   └── agenda.json              # cuentas, ventana de días, frescura, rutas
├── calendario/                  # AGENTE 1 — corre primero
│   ├── RUTINA_AGENDA.md         # cómo Claude lee Google Calendar
│   ├── scripts/snapshot_agenda.py
│   ├── ejemplo_eventos.json
│   └── salidas/agenda_actual.json   # ← snapshot que consume el correo
└── correo/                      # AGENTE 2 — DEPENDE del anterior
    ├── RUTINA_CORREO.md         # cómo Claude revisa Gmail y cruza con la agenda
    ├── config/criterios.json    # prioridad alta / media / baja
    ├── scripts/contexto_correo.py
    └── salidas/ULTIMA_REVISION.md
```

## La dependencia, en una frase
El agente de **correo** no revisa nada sin un **snapshot fresco** que produce
el agente de **calendario**. Así cada correo se lee sabiendo qué clases y
reuniones ya tienes: si el correo cae sobre un evento existente, solo informa;
si trae una fecha nueva, la marca como "agendar".

## Flujo diario (manual, como el resto del proyecto)
1. `python agenda/jefe.py` → te imprime el protocolo y el estado.
2. **Paso 1 — calendario:** dile a Cadmo *"revisa mi agenda"*. Lee Google
   Calendar y corre `snapshot_agenda.py` → deja `agenda_actual.json`.
3. **Paso 2 — correo:** dile *"revisa mi correo"*. Verifica frescura, carga el
   contexto, lee Gmail (etiqueta `outlook-reenviado` + inbox), clasifica,
   cruza contra la agenda y escribe `ULTIMA_REVISION.md`.

Si haces el paso 2 sin el paso 1, el sistema **bloquea** y te dice qué correr.

## Convenciones (iguales al resto del proyecto)
- Todo en UTF-8 explícito.
- Override de fecha para pruebas: `JEFE_FAKE_HOY=2026-08-03` o `--fecha`.
- Patrón `salidas/ULTIMA_*` para no adivinar rutas.
- Nada se envía, borra en definitiva ni se agenda sin tu confirmación por chat.

## Estado
- Gmail conectado (`lozanogerman79@gmail.com`).
- Outlook institucional → Gmail y Outlook → Google Calendar los mueve Power
  Automate cada hora; Google es la fuente única para `calendario`.
