#!/usr/bin/env bash
# Reconocimiento de solo lectura del televisor. No empareja ni envía órdenes.
set -uo pipefail

TV_HOST="${TV_HOST:-192.0.2.64}"
PORTS=(22 80 443 3000 3001 3002 3005 9080 9922 9991)

say() { printf '%s\n' "$*"; }
hr()  { printf '%s\n' "------------------------------------------------------------"; }

say "objetivo: ${TV_HOST}"
hr

# 1. Presencia
if ping -c 2 -W 1000 "$TV_HOST" >/dev/null 2>&1; then
  say "ping:        responde"
else
  say "ping:        sin respuesta (puede estar apagada o filtrar ICMP)"
fi

# 2. Puertos TCP
say "puertos TCP:"
for p in "${PORTS[@]}"; do
  if nc -z -G 2 -w 2 "$TV_HOST" "$p" >/dev/null 2>&1; then
    say "  ${p}: abierto"
  else
    say "  ${p}: cerrado/filtrado"
  fi
done
hr

# 3. Identidad por SSDP (solo LG responde con su UDN/descripción)
say "SSDP (LG):"
ssdp=$(printf 'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n' \
  | nc -u -w 3 239.255.255.250 1900 2>/dev/null | tr -d '\r')
if [ -n "$ssdp" ]; then
  printf '%s\n' "$ssdp" | grep -iE 'LOCATION|SERVER|ST:|USN' | sort -u | head -20
else
  say "  sin respuesta SSDP"
fi
hr

# 4. Respuesta HTTP cruda del puerto SSAP, si está abierto
if nc -z -G 2 -w 2 "$TV_HOST" 3000 >/dev/null 2>&1; then
  say "HTTP :3000 (primeras líneas):"
  curl -s --max-time 5 "http://${TV_HOST}:3000/" | head -c 400
  say ""
else
  say "HTTP :3000 no disponible"
fi
