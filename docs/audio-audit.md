# Auditoría de audio en la tele (2026-10-31)

Pregunta: ¿hay grabaciones de audio hechas por la televisión sin consentimiento?

## Resultado

**No hay audio almacenado en la tele y no se detecta envío de audio con la tele en reposo.**
Lo único que puede contener voz está fuera de alcance (root) y todo apunta a un log, no a grabaciones.

## 1. Almacenamiento local

- Cero ficheros de audio (`.wav`, `.pcm`, `.m4a`, `.aac`, `.opus`, `.amr`, `.mp3`, `.flac`) en
  `/media`, `/tmp`, `/var`, `/opt` — búsqueda por extensión y por firma.
- `/media/internal/avs` (almacén de Alexa) contiene **solo configuración y estado**:
  - `deviceSettings`: `SpeechRecognizer.wakeWords = ["ALEXA"]`, `Alexa.DoNotDisturb = false`, locale `es-ES`.
  - `alerts.db` con **0 alertas**; `certifiedSender.db` con 5 mensajes de telemetría pendientes.
  - `data/`, `google-assistant-adapter/`, `vsk/`: **vacíos**.
  - `SpeakerManager_SpeakerManagerConfig` y `GUIClient_*`: vacías o solo versión de protocolo.
- **Sin grabar y con root**: `/tmp/app.voice.log` (82 KB, `0600 root`), `/media/cryptofs`,
  `/var/luna/preferences`. No hay PVR ni timeshift (`com.webos.service.pvr|recorder|recording`
  → `404`), no hay USB conectado y la tele no graba vídeo en su flash.

## 2. Tráfico con la tele en reposo (prueba de red)

Método: sensor `tshark` del puerto espejo (Perdigon, `:9101`), cliente `192.0.2.37`,
ventana 22:31 → 22:39 (8 min) sin tocar la tele ni el mando.

| Métrica | Valor |
| --- | --- |
| Subido por la tele | **28.8 KB** |
| Bajado a la tele | 0.01 MB |
| Destinos de voz (alexa/avs/speech/asr/tts) | **ninguno** |
| Dominios nuevos | ninguno |

Desglose de la subida: 27.9 KB a `www.youtube.com` (latido de la app en primer plano) y 0.9 KB a
`8.8.8.8`. Ningún envío a Amazon ni a Google más allá del DNS.

Referencia previa: en los primeros segundos del sensor sí había ~3 MB subidos a
`unagi-eu.amazon.com` (telemetría de Amazon; coincide con uso de apps de Amazon, no con voz).

## 3. Qué implica

- En reposo la tele no abre conexiones a servicios de voz ni sube audio.
- El micrófono está en el **mando**: al mantener pulsado el botón, el audio va a los servidores
  (Amazon/Google) por diseño; no se guarda en el televisor.
- Donde **sí** puede haber historial de voz es en la nube: historial de voz de Alexa
  (amazon.es → Alexa → Privacidad) y la cuenta LG (Privacidad → información de voz). Se borra
  desde esas webs, no desde la tele.

## 4. Límites de esta auditoría

- `prisoner` está enjaulado y sin root: no puede leer `/tmp/app.voice.log` ni `cryptofs`. Para
  descartar al 100 % habría que rootear (Homebrew), con sus riesgos (bloquea OTA).
- La captura es del puerto espejo del switch: cubre el tráfico de la tele por cable. No vería
  contenido dentro de TLS, solo destinos, volúmenes y momentos.

## Reproducir

```bash
cd ~/Repos/monitor_internet && make sensor-up
cd ~/Repos/tv-admin/.audit
curl -s http://192.0.2.46:9101/metrics | grep -E '^netviz_(client|flow)_bytes_total\{' > baseline.prom
# esperar 8-10 min sin tocar la tele
curl -s http://192.0.2.46:9101/metrics | grep -E '^netviz_(client|flow)_bytes_total\{' > snap2.prom
# diff por (client, dst, domain, proto) filtrando client="192.0.2.37"
cd ~/Repos/monitor_internet && make sensor-down
```
