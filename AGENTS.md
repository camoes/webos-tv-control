# AGENTS.md — tv-admin

Control de un televisor LG MODELO-EJEMPLO por SSAP (WebSocket) y por SSH de
Developer Mode. Las reglas generales de trabajo están en la política global.

## Comandos

| Comando | Qué hace |
|---|---|
| `make verify` | **Gate de "hecho"**: compila `ssap.py`, valida `probe.sh` y `pairing.json` |
| `make probe` | Reconocimiento de solo lectura (puertos, SSDP) |
| `make info` / `apps` / `power` / `volume` | Consultas de estado |
| `make wake` / `power-off` / `button B=HOME` | Acciones sobre la tele |
| `make ssh` | Shell en la tele (`ssh tv`, prisoner@:9922) |

## Hechos del entorno

- SSAP en `wss://<TV_HOST>:3001`; `TV_HOST` por defecto en el Makefile pero **la IP
  cambia por DHCP** (.64 → .37 visto): resolverla antes de dar por roto el control.
- `pairing.json` guarda la clave del emparejamiento; es estado local, no se versiona.
- SSH: `~/.ssh/tv_webos`, requiere `+ssh-rsa`; `luna-send` es root-only.
- Algunas apps (p. ej. Stremio) usan Torrentio; no hay debrid contratado.

## Verificación

- `make verify` en verde antes de decir "hecho".
- Cualquier acción sobre la tele se confirma leyendo el estado real (`make power`,
  `make volume`), no por la ausencia de error del comando.
- Encender por WoL requiere la MAC guardada con `make netinfo`.

## Reglas

- No cambiar ajustes del televisor ni instalar apps sin aprobación explícita.
- No pegar `pairing.json` ni claves en el chat.

## Decisiones

`DECISIONS.md` guarda las decisiones con sus alternativas y consecuencias. Antes de
revertir una, añade una entrada nueva fechada; no edites la antigua.
