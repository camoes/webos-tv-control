#!/usr/bin/env python3
"""Cliente SSAP para el LG MODELO-EJEMPLO, sin dependencias externas.

SSAP es el protocolo de control de webOS sobre WebSocket:
  ws://<ip>:3000   (plano)
  wss://<ip>:3001  (TLS, certificado autofirmado)

Uso:
  ./ssap.py register                 # empareja: la tele pide aceptar con el mando
  ./ssap.py request <uri> [json]     # petición SSAP cruda
  ./ssap.py info                     # system/getSystemInfo + swInfo
  ./ssap.py apps                     # lista de apps instaladas
  ./ssap.py volume [0-100]           # lee o fija el volumen
  ./ssap.py mute on|off|status
  ./ssap.py input                    # entrada actual / lista de entradas
  ./ssap.py power-off                # apaga (no puede encender: ver README)
  ./ssap.py button <NAME>            # tecla del mando, p.ej. ENTER, HOME, UP

La `client-key` se guarda en .env (TV_CLIENT_KEY) y es reutilizable.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"


def _env_file_value(name: str) -> str | None:
    if not ENV.exists():
        return None
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return None


# TV_HOST también se puede fijar en .env (el DHCP de la tele cambia de IP)
HOST = os.environ.get("TV_HOST") or _env_file_value("TV_HOST") or "192.0.2.64"
# Este firmware (webOS 22 / MODELO-EJEMPLO) resetea el 3000 en claro: solo WSS en 3001.
PORT = int(os.environ.get("TV_PORT", "3001"))
USE_TLS = os.environ.get("TV_TLS", "1") != "0"

PAIRING = Path(__file__).resolve().parent / "pairing.json"


def pairing_template(unsigned: bool = False) -> dict:
    """Manifest de emparejamiento.

    Un manifest propio (appId inventado) empareja pero deja al cliente sin permisos:
    toda petición responde `401 insufficient permissions`. El de lgtv2 se identifica
    como la 'LG Remote App' (appId com.lge.test) y pide las 52 permisos de nivel
    superior, que es lo que la tele sí concede.
    """
    data = json.loads(PAIRING.read_text())
    if unsigned:
        data["manifest"].pop("signed", None)
    return data


# --------------------------------------------------------------------------- WS
class WS:
    """WebSocket mínimo (RFC 6455) sobre sockets: solo texto, sin extensiones."""

    def __init__(self, host: str, port: int, tls: bool, timeout: float = 10.0, path: str = "/"):
        raw = socket.create_connection((host, port), timeout=timeout)
        if tls:
            ctx = ssl._create_unverified_context()
            raw = ctx.wrap_socket(raw, server_hostname=host)
        self.sock = raw
        self._handshake(host, port, path)
        self._buf = b""

    def _handshake(self, host: str, port: int, path: str = "/") -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake: conexión cerrada")
            head += chunk
        status, _, rest = head.partition(b"\r\n\r\n")
        first_line = status.split(b"\r\n")[0]
        if b" 101 " not in first_line:
            raise ConnectionError(f"handshake rechazado: {first_line!r}")
        expected = base64.b64encode(
            hashlib.sha1(key.encode() + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()
        ).decode()
        if expected.lower().encode() not in status.lower():
            pass  # hay firmwares que omiten Accept; no abortamos por eso
        self._buf = rest

    def _read(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(8192)
            if not chunk:
                raise ConnectionError("conexión cerrada por la tele")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def send(self, text: str) -> None:
        payload = text.encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack("!H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _frame(self) -> tuple[int, bytes]:
        b0, b1 = self._read(2)
        opcode = b0 & 0x0F
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack("!H", self._read(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self._read(8))[0]
        if b1 & 0x80:  # servidor no debería enmascarar, pero por si acaso
            mask = self._read(4)
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(n)))
        else:
            data = self._read(n)
        return opcode, data

    def recv(self) -> str | None:
        while True:
            opcode, data = self._frame()
            if opcode == 0x1:  # texto
                return data.decode("utf-8", "replace")
            if opcode == 0x8:  # close
                return None
            if opcode == 0x9:  # ping -> pong
                self.sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
            # binario/continuación/pong: se ignoran

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


# ------------------------------------------------------------------------ SSAP
class SSAP:
    def __init__(self, host: str = HOST, port: int = PORT, tls: bool = USE_TLS):
        self.ws = WS(host, port, tls)
        self.seq = 0

    def _id(self) -> str:
        self.seq += 1
        return f"req{self.seq}"

    def call(self, uri: str, payload: dict | None = None, timeout: float = 10.0) -> dict:
        rid = self._id()
        msg = {"id": rid, "type": "request", "uri": uri}
        if payload:
            msg["payload"] = payload
        self.ws.sock.settimeout(timeout)
        self.ws.send(json.dumps(msg))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = self.ws.recv()
            if raw is None:
                raise ConnectionError("la tele cerró el socket")
            data = json.loads(raw)
            if data.get("id") == rid:
                return data
        raise TimeoutError(f"sin respuesta a {uri}")

    def register(self, client_key: str | None = None, timeout: float = 120.0,
                 unsigned: bool = False) -> dict:
        rid = self._id()
        payload: dict = pairing_template(unsigned)
        payload["pairingType"] = "PROMPT"
        if client_key:
            payload["client-key"] = client_key
        self.ws.send(json.dumps({"id": rid, "type": "register", "payload": payload}))
        print(f"→ register enviado a {HOST}:{PORT} (id {rid}); esperando a la tele…", flush=True)
        deadline = time.time() + timeout
        self.ws.sock.settimeout(5)
        while time.time() < deadline:
            try:
                raw = self.ws.recv()
            except socket.timeout:
                continue
            if raw is None:
                raise ConnectionError("la tele cerró el socket durante el emparejamiento")
            data = json.loads(raw)
            if data.get("id") != rid:
                continue
            if data.get("type") == "registered":
                return data
            if data.get("type") == "error":
                raise RuntimeError(f"emparejamiento rechazado: {data}")
        raise TimeoutError("no llegó 'registered'")


# ------------------------------------------------------------------------- env
def load_var(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def save_var(name: str, value: str) -> None:
    lines: list[str] = []
    if ENV.exists():
        lines = [l for l in ENV.read_text().splitlines() if not l.startswith(f"{name}=")]
    lines.append(f"{name}={value}")
    ENV.write_text("\n".join(lines) + "\n")
    ENV.chmod(0o600)


def load_key() -> str | None:
    return load_var("TV_CLIENT_KEY")


def save_key(key: str) -> None:
    save_var("TV_CLIENT_KEY", key)


# ------------------------------------------------------------------------ main
def open_session(attempts: int = 4, delay: float = 4.0) -> SSAP:
    key = load_key()
    if not key:
        sys.exit("no hay client-key: ejecuta primero  ./ssap.py register")
    last: Exception | None = None
    for i in range(attempts):
        try:
            s = SSAP()
            res = s.register(client_key=key, timeout=30)
            if res.get("type") != "registered":
                sys.exit(f"registro fallido: {res}")
            return s
        except (ConnectionError, TimeoutError, OSError) as exc:
            # la tele corta el handshake TLS si se abren conexiones muy seguidas
            last = exc
            time.sleep(delay * (i + 1))
    sys.exit(f"ERROR: no se pudo conectar con la tele: {last}")


def pointer_socket(s: "SSAP") -> WS:
    """Abre el socket de teclado del mando (botones y texto)."""
    info = s.call("ssap://com.webos.service.networkinput/getPointerInputSocket")
    path = info.get("payload", {}).get("socketPath", "")
    if not path:
        sys.exit(f"sin socketPath: {info}")
    rest = path.split("://", 1)[1]
    hostport, _, wpath = rest.partition("/")
    host, _, port_s = hostport.partition(":")
    return WS(host, int(port_s or 3000), USE_TLS, path="/" + wpath)


def press(ws: WS, name: str) -> None:
    ws.send(f"type:button\nname:{name.upper()}\n\n")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "help"

    if cmd == "register":
        try:
            s = SSAP()
            res = s.register(client_key=None, timeout=120)
        except RuntimeError as exc:
            # webOS 26 rechaza el manifest 'com.lge.test' (certificado en lista negra):
            # se reintenta sin el bloque 'signed', como hace lgtv2 2.0.1+.
            if "blacklisted" not in str(exc) and "403" not in str(exc):
                raise
            print("· manifest firmado rechazado; reintento sin 'signed'", flush=True)
            s = SSAP()
            res = s.register(client_key=None, timeout=120, unsigned=True)
        key = res.get("payload", {}).get("client-key")
        if not key:
            sys.exit(f"respuesta sin client-key: {res}")
        save_key(key)
        print(f"✓ emparejado; client-key guardada en {ENV}")
        try:
            info = s.call("ssap://com.webos.service.connectionmanager/getinfo").get("payload", {})
            wired = info.get("wiredInfo", {}).get("macAddress")
            if wired:
                save_var("TV_MAC", wired)
                print(f"✓ TV_MAC={wired} (WoL) guardada en {ENV}")
        except (ConnectionError, TimeoutError, RuntimeError, OSError):
            pass  # el MAC se puede leer luego con ./ssap.py netinfo
        print(json.dumps(res.get("payload", {}), indent=2, ensure_ascii=False))
        s.ws.close()
        return 0

    if cmd == "request":
        if len(argv) < 3:
            sys.exit("uso: ./ssap.py request <uri> ['{\"k\":1}']")
        payload = json.loads(argv[3]) if len(argv) > 3 else None
        s = open_session()
        print(json.dumps(s.call(argv[2], payload), indent=2, ensure_ascii=False))
        s.ws.close()
        return 0

    if cmd == "info":
        s = open_session()
        for uri in ("ssap://system/getSystemInfo", "ssap://com.webos.service.update/getCurrentSWInformation"):
            print(f"== {uri}")
            print(json.dumps(s.call(uri), indent=2, ensure_ascii=False))
        s.ws.close()
        return 0

    if cmd == "apps":
        s = open_session()
        res = s.call("ssap://com.webos.applicationManager/listLaunchPoints")
        for app in res.get("payload", {}).get("launchPoints", []):
            print(f"{app.get('id'):45s} {app.get('title')}")
        s.ws.close()
        return 0

    if cmd == "volume":
        s = open_session()
        if len(argv) > 2:
            res = s.call("ssap://audio/setVolume", {"volume": int(argv[2])})
        else:
            res = s.call("ssap://audio/getVolume")
        print(json.dumps(res.get("payload", res), indent=2, ensure_ascii=False))
        s.ws.close()
        return 0

    if cmd == "mute":
        s = open_session()
        if len(argv) > 2 and argv[2] in ("on", "off"):
            s.call("ssap://audio/setMute", {"mute": argv[2] == "on"})
            print(f"mute={argv[2]}")
        else:
            print(json.dumps(s.call("ssap://audio/getMute").get("payload"), indent=2))
        s.ws.close()
        return 0

    if cmd == "input":
        s = open_session()
        if len(argv) > 2 and argv[2] != "list":
            s.call("ssap://tv/switchInput", {"inputId": argv[2]})
            print(f"input -> {argv[2]}")
        else:
            cur = s.call("ssap://tv/getCurrentChannel")
            ext = s.call("ssap://com.webos.applicationManager/getForegroundAppInfo")
            print("foreground:", json.dumps(ext.get("payload"), ensure_ascii=False))
            print("channel:", json.dumps(cur.get("payload"), ensure_ascii=False))
        s.ws.close()
        return 0

    if cmd == "power-off":
        s = open_session()
        print(json.dumps(s.call("ssap://system/turnOff"), indent=2))
        s.ws.close()
        return 0

    if cmd == "power":
        s = open_session()
        print(json.dumps(s.call("ssap://com.webos.service.tvpower/power/getPowerState")
                         .get("payload"), indent=2))
        s.ws.close()
        return 0

    if cmd == "wake":
        mac = os.environ.get("TV_MAC") or load_var("TV_MAC")
        if not mac:
            sys.exit("falta TV_MAC (usa: ./ssap.py netinfo para leerla de la tele)")
        pkt = b"\xff" * 6 + bytes.fromhex(mac.replace(":", "")) * 16
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in ("255.255.255.255", "192.0.2.255"):
            for _ in range(3):
                sock.sendto(pkt, (target, 9))
        sock.close()
        print(f"magic packet enviado a {mac} (3×255.255.255.255, 3×192.0.2.255:9)")
        return 0

    if cmd == "netinfo":
        s = open_session()
        info = s.call("ssap://com.webos.service.connectionmanager/getinfo").get("payload", {})
        s.ws.close()
        wired = info.get("wiredInfo", {}).get("macAddress")
        wifi = info.get("wifiInfo", {}).get("macAddress")
        print(json.dumps(info, indent=2))
        if wired:
            save_var("TV_MAC", wired)
            print(f"TV_MAC={wired} guardada en {ENV}")
        return 0

    if cmd == "launch":
        if len(argv) < 3:
            sys.exit("uso: ./ssap.py launch <appId>   (ids: ./ssap.py apps)")
        s = open_session()
        print(json.dumps(s.call("ssap://system.launcher/launch", {"id": argv[2]}), indent=2))
        s.ws.close()
        return 0

    if cmd == "keys":
        if len(argv) < 3:
            sys.exit("uso: ./ssap.py keys LEFT DOWN ENTER …")
        s = open_session()
        ws = pointer_socket(s)
        s.ws.close()
        for name in argv[2:]:
            press(ws, name)
            print(f"· {name.upper()}")
            time.sleep(0.35)
        ws.close()
        return 0

    if cmd == "button":
        if len(argv) < 3:
            sys.exit("uso: ./ssap.py button <NAME>   (ENTER, HOME, UP, DOWN, LEFT, RIGHT, BACK, VOLUMEUP, …)")
        s = open_session()
        ws = pointer_socket(s)
        s.ws.close()
        press(ws, argv[2])
        time.sleep(0.2)
        ws.close()
        print(f"botón {argv[2].upper()} enviado")
        return 0

    if cmd == "type":
        if len(argv) < 3:
            sys.exit('uso: ./ssap.py type "texto a escribir"')
        s = open_session()
        text = " ".join(argv[2:])
        print(json.dumps(s.call("ssap://com.webos.service.ime/insertText",
                                {"text": text, "replace": 0}), ensure_ascii=False)[:400])
        s.ws.close()
        return 0

    print(__doc__)
    return 0 if cmd in ("help", "-h", "--help") else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except (ConnectionError, TimeoutError, RuntimeError) as exc:
        sys.exit(f"ERROR: {exc}")
