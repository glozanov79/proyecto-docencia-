# RUTINA_AGENDA.md — Agente Calendario

**Comando de disparo:** "revisa mi agenda" / "actualiza el calendario"

Este agente corre **primero**. Deja un snapshot que el agente de correo
necesita para cruzar los mensajes contra tus eventos reales.

## Qué hace Claude (Cadmo)

1. **Lee Google Calendar** (calendario principal, cuenta
   `lozanogerman79@gmail.com`) vía el conector, para la ventana de días
   definida en `config/agenda.json` (`ventana_dias`, por defecto 7).
   - Power Automate ya sincroniza Outlook institucional → Google Calendar
     cada hora, así que el calendario de Google es la fuente única.

2. **Arma la lista de eventos** en este formato mínimo:
   ```json
   [
     {"titulo": "Clase E-Financial", "inicio": "2026-08-03T18:30:00", "fin": "2026-08-03T20:00:00", "ubicacion": "Campus UCC"},
     {"titulo": "Reunión de área",   "inicio": "2026-08-06T15:00:00"}
   ]
   ```

3. **Genera el snapshot** corriendo:
   ```bash
   python calendario/scripts/snapshot_agenda.py --eventos eventos.json
   ```
   (o pasando el JSON por stdin). Esto escribe
   `calendario/salidas/agenda_actual.json` con los campos normalizados
   (`fecha`, `hora_inicio`, `dias_desde_hoy`, `cuando`).

4. **Reporta** en el chat: cuántos eventos hay en la ventana y un listado
   corto ("hoy / mañana / en N días").

## Reglas
- Zona horaria: America/Bogota.
- Festivos y receso **no** ocultan eventos; se muestran igual.
- Si el conector de Calendar falla, avisa y **no** dejes un snapshot vacío
  silencioso (eso bloquearía el correo sin explicación).
- Para pruebas sin tocar el reloj real: `JEFE_FAKE_HOY=2026-08-03`.
