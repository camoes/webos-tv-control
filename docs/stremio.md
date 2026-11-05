# Stremio en la LG MODELO-EJEMPLO

App: `io.strem.tv` v1.9.1 · cuenta `usuario1@example.com` · sin debrid (torrent directo).

## Configuración aplicada

Torrentio v0.0.15 instalado **en la cuenta** (no en la tele), con esta URL:

```
https://torrentio.strem.fun/sort=quality|qualityfilter=cam,scr,brremux,threed,dolbyvision/manifest.json
```

- `sort=quality` → ordena por calidad y luego por seeders (lo correcto sin debrid).
- `qualityfilter=cam,scr` → fuera CAM y screener.
- `brremux` → fuera REMUX de ~60 GB (sin debrid no se sostienen).
- `threed` → la tele no tiene 3D.
- `dolbyvision` → la app de webOS da pantalla negra/colores rotos con DV.

Validado desde el Mac: `manifest.json` → 200 con `streams`, y
`/stream/movie/tt0111161.json` devuelve torrents reales con seeders.

## Cómo se instala (no se puede desde la tele)

La app de LG **no permite añadir addons**: la pantalla de Addons solo tiene
**Sync addons**. Los addons se instalan en la cuenta y la tele los baja al sincronizar.

1. `web.stremio.com` → login con la cuenta.
2. Addons → **Add addon** → pegar la URL de arriba → **Install**.

## Trampa: la lista de addons se ve vacía aunque funcione

Bug abierto de Stremio en webOS ([#2660](https://github.com/Stremio/stremio-bugs/issues/2660)):
pulsas *Sync addons*, dice que sincronizó, y la pantalla de Addons sigue sin listarlos.

**La prueba buena es reproducir**: abrir una peli popular y pulsar ver. Si en la lista de
fuentes salen entradas de Torrentio con seeders, el addon está activo y el fallo es solo de UI.

Comprobado el 2026-10-31: sale Torrentio en las fuentes aunque la lista de Addons parezca vacía.

## Otras notas

- Logout/login en la tele no arregla el listado; el problema no es la sesión.
- El log de consultas de AdGuard **no sirve** como prueba: la tele resuelve por otra vía (solo
  aparecen decenas de consultas suyas, ninguna de torrentio, mientras la reproducción funciona).
- Sin debrid: la IP queda expuesta al swarm y la reproducción depende de seeders; los 4K grandes
  pueden bufferizar. Con debrid habría que reinstalar el addon con la API key y ordenar por
  calidad→tamaño.
