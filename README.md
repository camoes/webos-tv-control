# tv-admin

Administración remota del televisor **LG MODELO-EJEMPLO** (webOS 22, `192.0.2.64`, cableado al puerto 3 del switch).

Estado: **control por SSAP funcionando y emparejado**. No hay SSH en la tele (el 9922 está cerrado),
así que la vía sin tocar el firmware es el WebSocket de control de webOS.

## Qué funciona hoy (verificado el 2026-10-31)

```bash
make probe        # reconocimiento de solo lectura
make pair         # emparejar (una vez; pide aceptar en pantalla)
make info         # modelo, serie, estado
make apps         # apps instaladas con su id
make volume       # volumen actual · make volume V=20 lo fija
make power        # Active / Screen Off / Active Standby…
make power-off    # apagar
make wake         # encender por Wake-on-LAN
make netinfo      # MACs + guarda TV_MAC para WoL
make button B=HOME
```

Salida real del equipo:

- `modelName: MODELO-EJEMPLO`, `serialNumber: XXXXXXXXXXXX`, `receiverType: DVB`
- MAC cableada `AC:5A:F0:00:00:03`, Wi-Fi `20:28:BC:00:00:01`, p2p `00:00:5E:00:53:02`
- volumen 5/100, `soundOutput: tv_external_speaker`

El protocolo es SSAP (el mismo que usan las apps de mando de LG), sobre `wss://192.0.2.64:3001`.
`scripts/ssap.py` es un cliente propio **sin dependencias**: WebSocket RFC 6455 a mano sobre sockets,
registro SSAP y comandos.

## Hallazgos del reconocimiento

| Puerto | Estado | Qué es |
| --- | --- | --- |
| 3001 | **abierto** | SSAP sobre TLS (WSS). La única vía de control que responde |
| 3000 | abierto pero inútil | SSAP en claro: el firmware **resetea** la conexión al recibir el upgrade HTTP |
| 9080 | abierto | `Server: NRDP/2024.1.6.0-601facad724`, responde `status=ok`. Plataforma de Netflix, no sirve para administrar |
| 22 / 9922 | cerrados | sin SSH: no hay Developer Mode activo |
| 80 / 443 / 8001 / 8002 | cerrados | sin web UI de administración |
| 9991 | cerrado | sin el servicio de root de los scripts de homebrew |

## Las tres vías, de menos a más invasiva

1. **SSAP (en uso)** — control tipo mando: encendido/apagado, volumen, entradas, apps, botones,
   lectura de estado y de la lista de apps. Requiere aceptar un aviso en pantalla **una vez**;
   la `client-key` resultante se guarda en `.env` (0600) y se reutiliza.
2. **SSH de Developer Mode** — `:9922`, usuario `prisoner`, clave RSA del portal de LG. Da shell real
   (`luna-send`, `ps`, `top`, copiar `.ipk`). Requisitos: cuenta LG, app *Developer Mode* en la tele,
   sesión de 1000 h que hay que renovar desde el mando. **No probado: el 9922 está cerrado.**
3. **Homebrew Channel / root** — control total, pero exige exploit por firmware, bloquea OTA y
   puede inutilizar el panel. Fuera de alcance salvo petición explícita.

## Trampas aprendidas (no repetirlas)

- **Un manifest propio empareja pero no da permisos.** Con `appId` inventado la tele acepta el
  emparejamiento y luego responde `401 insufficient permissions` a todo (solo `system/getSystemInfo`
  y `api/getServiceList` pasan). Hay que identificarse como *LG Remote App* (`appId: com.lge.test`)
  con la lista de 52 permisos: `scripts/pairing.json`, tomado de lgtv2 (MIT).
- **webOS 26 rechaza ese manifest** con `403 Pairing rejected: blacklisted certificate detected`.
  `register` reintenta sin el bloque `signed` automáticamente.
- **El 3000 no es un fallback en este firmware**: hay que ir por 3001 con TLS y certificado sin verificar.
- **No abrir muchas conexiones seguidas**: el handshake TLS empieza a agotar tiempo. Una sesión por
  proceso y reutilizarla para varias peticiones (es lo que hace el script).
- **`ssap://audio/getVolume` devuelve `payload.volumeStatus`**, no `payload.volume`.
- **Apagar sí, encender no**: `system/turnOff` funciona, pero SSAP no puede despertar la tele.
  Encender = Wake-on-LAN a la MAC cableada, y depende de que la tele tenga activado
  *Ajustes → General → Dispositivos → TV móvil encendida / Wake on LAN*. Sin probar todavía.

## SSH (Developer Mode) — activo desde 2026-10-31

```bash
ssh tv            # alias en ~/.ssh/config → prisoner@192.0.2.37:9922
scp fichero tv:/tmp/
```

- Clave: `~/.ssh/tv_webos` (la sirve la tele en `http://<ip>:9991/equipo`). **Viene cifrada con la
  passphrase que muestra la app Developer Mode**; sin ella SSH responde `Permission denied`. Se abre
  una vez con `ssh-keygen -p -P <passphrase> -N "" -f ~/.ssh/tv_webos` (queda una copia cifrada en
  `tv_webos.enc`).
- El servidor solo ofrece `ssh-rsa`, así que el alias lleva `HostKeyAlgorithms +ssh-rsa` y
  `PubkeyAcceptedAlgorithms +ssh-rsa`. Sin eso: *no matching host key type found*.
- **La IP la cambia el DHCP**: el 31/10 estaba en `.64` y tras activar Dev Mode pasó a `.37`.
  `TV_HOST` va en `.env` y el alias `tv` en `~/.ssh/config` hay que actualizarlo si cambia.
- La sesión de Dev Mode dura 1000 h y se renueva desde la app de la tele. Si expira, se cae el SSH.

Qué se puede hacer dentro (usuario `prisoner`, **sin root**):

- `ps`, `top`, `df`, `free`, `netstat`, `curl`, `wget`, `python3`, **`sqlite3`** (leer bases de datos
  de apps), `scp` a `/tmp`, `/media/developer/log` y `/media/developer/temp` (el resto de
  `/media/developer` es de root: `HOME` no es escribible).
- **`luna-send` es root-only** (`-rwx------`); el ejecutable accesible es `luna-send-pub`, y en esta
  tele devuelve vacío para las URIs probadas. Para llamar servicios, sigue siendo mejor SSAP desde el
  Mac (`scripts/ssap.py`), que ya tiene permisos.

## Stremio (configurado)

La app estaba instalada pero sin ningún addon de fuentes, así que no reproducía nada.
Ahora usa Torrentio desde la cuenta `usuario1@example.com` (la app de LG solo sincroniza;
no admite pegar URLs). Detalle, config exacta y la trampa del listado vacío: `docs/stremio.md`.

## Ficheros

- `scripts/ssap.py` — cliente SSAP y CLI (register, info, apps, volume, mute, input, power, power-off, wake, netinfo, launch, button, keys, type, request).
- `scripts/pairing.json` — manifest de emparejamiento (LG Remote App).
- `scripts/probe.sh` — reconocimiento de puertos/SSDP.
- `docs/stremio.md` — configuración de Stremio/Torrentio.
- `docs/apps.json` — las 37 apps de la tele con id y metadatos.
- `.env` — `TV_CLIENT_KEY`, `TV_MAC` (0600, ignorado por git).

## Estado y pendientes

Verificado: emparejamiento, queries de estado, volumen, apps, entradas, botones (`keys`/`type`),
apagado por SSAP y navegación del menú de la app.

Sin probar / fuera de alcance por decisión propia:

- **Encendido por Wake-on-LAN** (`make wake`): requiere apagar la tele y que tenga activado
  *Ajustes → General → Dispositivos → TV móvil encendida / Wake on LAN*.
- **SSH real**: solo existe activando *Developer Mode* (puerto 9922, usuario `prisoner`,
  sesión de 1000 h). Pasos en este README; no se ha activado.
- **Debrid**: sin suscribir. Si se contrata, reinstalar Torrentio con la API key y
  `sort=qualitysize` (ver `docs/stremio.md`).

## Cómo retomar

```bash
cd ~/Repos/tv-admin
make power            # ¿está encendida y responde?
make apps             # inventario
make volume V=15
./scripts/ssap.py keys LEFT DOWN DOWN DOWN DOWN ENTER   # menú lateral → Addons
```

