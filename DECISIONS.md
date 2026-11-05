# DECISIONS.md — tv-admin

Registro de decisiones con alternativas reales. Formato: contexto, decisión,
consecuencias. Una decisión se supera con una entrada nueva fechada más arriba.

> Las entradas anteriores al 2026-11-01 están reconstruidas de la memoria del
> proyecto; la fecha es aproximada.

## 2026-11-01 — Gate `make verify`

**Contexto**: el repo solo tenía acciones contra la tele, que exigen que esté
encendida; no había ninguna comprobación que pudiera correr sin ella.
**Decisión**: `make verify` compila `ssap.py`, valida la sintaxis de `probe.sh` y
parsea `pairing.json` si existe.
**Alternativas**: un `make probe` como gate (descartado: requiere red y tele encendida).
**Consecuencias**: el gate es hermético, pero no demuestra que la tele responda; eso se
confirma con `make power` / `make info` después.

## 2026-10 (aprox.) — SSAP por WebSocket 3001 + SSH de Developer Mode

**Contexto**: el televisor no expone una API HTTP; se quería control y estado desde el Mac.
**Decisión**: SSAP en `wss://<TV_HOST>:3001` para control y estado, y SSH de Developer
Mode (`ssh tv` = prisoner@:9922 con `~/.ssh/tv_webos`) para inspección.
**Consecuencias**: la IP cambia por DHCP (.64 → .37 visto), así que `TV_HOST` no se
hardcodea en scripts; la clave de pairing (`scripts/pairing.json`) es estado local y no
se versiona; `luna-send` es root-only y no sirve para automatizar sin más.

## 2026-10 (aprox.) — Sin debrid para Stremio

**Contexto**: la tele reproduce con Torrentio desde la cuenta gratuita de Stremio.
**Decisión**: no contratar debrid por ahora.
**Consecuencias**: la reproducción depende de seeds; si aparecen cortes en contenido
poco popular, esta es la primera decisión a revisar.
