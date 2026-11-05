# Perfil DNS de la tele (2026-10-31)

Cliente AdGuard `tele-lg` = `192.0.2.37`. Ventana analizada: 09:44 → 22:47 (la tele solo pasó a
usar AdGuard a las ~22:45, así que la mayor parte de la muestra es de la última hora).
**147 consultas, 44 dominios.** Sin aplicar ningún bloqueo.

## Composición (descontando dominios de prueba manuales)

| Categoría | Consultas | % | Ejemplos |
| --- | --- | --- | --- |
| Netflix · reproducción | 32 | 22 % | `api-global`, `secure`, `uiboot`, `nrdp51-appboot` |
| Netflix · analítica | 40 | 28 % | `customerevents` (18), `nrdp.prod.cloud` (11), `ichnaea` (10), `nrdp.logs` |
| CDN de Netflix | 10 | 7 % | `cdn-0.nflximg.com` |
| LG · sistema/updates | 14 | 10 % | `eic.tv.wiselg`, `eic-ngfts.lge`, `nextlgsdp`, `eic.lgtviot` |
| LG · publicidad | 8 | 5 % | `es.ad.lgsmartad.com` (6), `lge-static.ottera.tv` (2) |
| Amazon · telemetría | 4 | 3 % | `unagi-eu.amazon.com`, `…minerva.devices.a2z.com` |
| Google · funcional | 4 | 3 % | `connectivitycheck.gstatic.com`, `clients4.google.com` |
| Publicidad de terceros | 6 | 4 % | `googlesyndication`, `doubleclick`, `google-analytics`, `samsungads` |
| Otros / pruebas | 18 | 12 % | `example.com`, `wikipedia`, `apple`, `spotify`, `github` |

Los dominios "de pruebas" (`example.com`, `wikipedia.org`, `apple.com`, `spotify.com`, `github.com`,
`bbc.co.uk`, `cloudflare.com`, `whatsapp.net`) son de las comprobaciones manuales de DNS, no de la tele.

## Lectura

- **Netflix domina** (≈56 %): normal si la app estaba abierta. De eso, la mitad es funcional y la otra
  mitad es analítica de producto (`customerevents` = eventos de interfaz, `ichnaea` = analítica de red/
  geolocalización aproximada, `nrdp.*` = su pipeline de telemetría).
- **LG publica y mide**: `es.ad.lgsmartad.com` es el banner publicitario del sistema y
  `ottera.tv` la plataforma de datos/medición. `eic-ngfts.lge.com` y `nextlgsdp` son sistema y updates.
- **Amazon solo telemetría**: `unagi-eu.amazon.com` y el endpoint `minerva.devices.a2z.com` de
  dispositivos Amazon, sin flujos de vídeo en la muestra.
- **Ruido de publicidad de terceros** en una tele LG (`samsungads.com`, `doubleclick`): viene de SDKs
  dentro de alguna app/webview, no del sistema.
- **Nada de voz**: cero consultas a `alexa`, `avs.` o similares, coherente con la auditoría de audio.

## Si algún día se bloquea (no aplicado)

Nivel conservador (riesgo funcional nulo):

```
||es.ad.lgsmartad.com^$client=192.0.2.37
||lge-static.ottera.tv^$client=192.0.2.37
||eu-acr63.alphonso.tv^$client=192.0.2.37
```

Nivel fuerte (añade analítica de Netflix; reversible en un comando):

```
||customerevents.netflix.com^$client=192.0.2.37
||ichnaea.netflix.com^$client=192.0.2.37
||nrdp.logs.netflix.com^$client=192.0.2.37
```

No bloquear `api-global`, `secure`, `uiboot`, `nrdp51-appboot` ni `cdn-0.nflximg.com`: son
reproducción y catálogo.

## Límites

- 147 consultas en una hora de uso real es una muestra corta: para un perfil serio conviene dejarlo
  24 h y volver a agrupar.
- AdGuard solo ve **DNS**: no dice qué se envía dentro del TLS, solo a quién se pregunta. Para volumen
  y destinos reales hace falta el sensor del puerto espejo.
