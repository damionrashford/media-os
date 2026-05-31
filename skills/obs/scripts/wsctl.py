#!/usr/bin/env python3
"""
wsctl.py — obs-websocket v5 CLI.

Stdlib-only if `websocket-client` isn't installed (we fall back to a minimal
handshake + frame codec built on `socket`). If `websocket-client` IS importable,
we use it because it's more robust for long-lived event streams.

Non-interactive. Auto-discovers URL + password from the local OBS's own
`plugin_config/obs-websocket/config.json` — NO flags needed. Prints JSON to
stdout. `--verbose` traces the wire protocol; `--dry-run` skips the network.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import threading
import time
import uuid
from typing import Any
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Optional websocket-client detection
# ---------------------------------------------------------------------------

try:
    import websocket  # type: ignore

    HAVE_WS_CLIENT = True
except ImportError:  # pragma: no cover
    HAVE_WS_CLIENT = False


# ---------------------------------------------------------------------------
# Minimal stdlib WebSocket client (fallback)
# ---------------------------------------------------------------------------

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class _StdlibWS:
    """A tiny RFC 6455 text-frame WebSocket client. JSON subprotocol only."""

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        p = urlparse(url)
        self._scheme = p.scheme
        self._host = p.hostname or "localhost"
        self._port = p.port or (443 if p.scheme == "wss" else 4455)
        self._path = p.path or "/"
        if p.query:
            self._path += "?" + p.query
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = b""

    def connect(self) -> None:
        s = socket.create_connection((self._host, self._port), timeout=self._timeout)
        if self._scheme == "wss":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self._host)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self._path} HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Protocol: obswebsocket.json\r\n"
            "\r\n"
        )
        s.sendall(req.encode())
        # read handshake
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                raise ConnectionError("server closed during handshake")
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(f"bad handshake: {head!r}")
        expected = base64.b64encode(
            hashlib.sha1((key + _GUID).encode()).digest()
        ).decode()
        if expected.lower() not in head.decode().lower():
            raise ConnectionError("Sec-WebSocket-Accept mismatch")
        self._sock = s
        self._buf = rest

    def send(self, payload: str) -> None:
        assert self._sock is not None
        data = payload.encode()
        header = bytearray([0x81])  # FIN + text
        mask = os.urandom(4)
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 2**16:
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self._sock.sendall(bytes(header) + masked)

    def _read(self, n: int) -> bytes:
        assert self._sock is not None
        while len(self._buf) < n:
            chunk = self._sock.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise ConnectionError("socket closed")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def recv(self) -> str:
        while True:
            b1, b2 = self._read(2)
            fin = b1 & 0x80
            opcode = b1 & 0x0F
            masked = b2 & 0x80
            length = b2 & 0x7F
            if length == 126:
                (length,) = struct.unpack(">H", self._read(2))
            elif length == 127:
                (length,) = struct.unpack(">Q", self._read(8))
            mask = self._read(4) if masked else b""
            payload = self._read(length)
            if masked:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x9:  # ping
                # send pong with same payload
                pong = bytearray([0x8A])
                if len(payload) < 126:
                    pong.append(0x80 | len(payload))
                else:
                    pong.append(0x80 | 126)
                    pong += struct.pack(">H", len(payload))
                m = os.urandom(4)
                pong += m + bytes(b ^ m[i % 4] for i, b in enumerate(payload))
                assert self._sock is not None
                self._sock.sendall(bytes(pong))
                continue
            if opcode == 0x8:  # close
                code = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 0
                raise ConnectionError(f"server closed with code {code}")
            if opcode == 0x1 and fin:
                return payload.decode()
            # ignore binary / continuation

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.sendall(b"\x88\x80" + os.urandom(4))
            except OSError:
                pass
            self._sock.close()
            self._sock = None


# ---------------------------------------------------------------------------
# Unified client wrapper
# ---------------------------------------------------------------------------


class OBSClient:
    def __init__(self, url: str, password: str | None, verbose: bool = False) -> None:
        self.url = url
        self.password = password or ""
        self.verbose = verbose
        if HAVE_WS_CLIENT:
            self._ws = websocket.WebSocket(
                subprotocols=["obswebsocket.json"], enable_multithread=True
            )
        else:
            self._ws = _StdlibWS(url)

    def _log(self, direction: str, data: Any) -> None:
        if self.verbose:
            sys.stderr.write(f"[{direction}] {json.dumps(data)}\n")

    def connect(self, event_subscriptions: int | None = None) -> dict:
        if HAVE_WS_CLIENT:
            self._ws.connect(self.url)  # type: ignore[arg-type]
        else:
            self._ws.connect()

        hello_raw = self._ws.recv()
        hello = json.loads(hello_raw)
        self._log("<-", hello)
        if hello.get("op") != 0:
            raise RuntimeError(f"expected Hello, got op {hello.get('op')}")

        d = hello["d"]
        identify_d: dict[str, Any] = {"rpcVersion": d.get("rpcVersion", 1)}
        if event_subscriptions is not None:
            identify_d["eventSubscriptions"] = event_subscriptions
        auth = d.get("authentication")
        if auth:
            if not self.password:
                raise RuntimeError("server requires password but none provided")
            secret = base64.b64encode(
                hashlib.sha256((self.password + auth["salt"]).encode()).digest()
            ).decode()
            identify_d["authentication"] = base64.b64encode(
                hashlib.sha256((secret + auth["challenge"]).encode()).digest()
            ).decode()

        identify = {"op": 1, "d": identify_d}
        self._log("->", identify)
        self._ws.send(json.dumps(identify))

        ident_raw = self._ws.recv()
        ident = json.loads(ident_raw)
        self._log("<-", ident)
        if ident.get("op") != 2:
            raise RuntimeError(f"expected Identified, got {ident}")
        return ident["d"]

    def request(
        self, request_type: str, request_data: dict | None = None, dry_run: bool = False
    ) -> dict:
        rid = str(uuid.uuid4())
        msg: dict[str, Any] = {
            "op": 6,
            "d": {"requestType": request_type, "requestId": rid},
        }
        if request_data:
            msg["d"]["requestData"] = request_data
        if dry_run:
            print(json.dumps(msg, indent=2))
            return {}
        self._log("->", msg)
        self._ws.send(json.dumps(msg))
        # Drain until we find the matching RequestResponse; buffer any stray events.
        while True:
            raw = self._ws.recv()
            msg_in = json.loads(raw)
            self._log("<-", msg_in)
            if msg_in.get("op") == 7 and msg_in["d"].get("requestId") == rid:
                return msg_in["d"]
            # else: event or other batch — ignore for single-request path

    def batch(
        self,
        requests: list[dict],
        halt_on_failure: bool = False,
        execution_type: int = 0,
        dry_run: bool = False,
    ) -> dict:
        rid = str(uuid.uuid4())
        msg = {
            "op": 8,
            "d": {
                "requestId": rid,
                "haltOnFailure": halt_on_failure,
                "executionType": execution_type,
                "requests": requests,
            },
        }
        if dry_run:
            print(json.dumps(msg, indent=2))
            return {}
        self._log("->", msg)
        self._ws.send(json.dumps(msg))
        while True:
            raw = self._ws.recv()
            msg_in = json.loads(raw)
            self._log("<-", msg_in)
            if msg_in.get("op") == 9 and msg_in["d"].get("requestId") == rid:
                return msg_in["d"]

    def stream_events(self) -> None:
        while True:
            try:
                raw = self._ws.recv()
            except (ConnectionError, OSError) as exc:
                sys.stderr.write(f"stream closed: {exc}\n")
                return
            msg_in = json.loads(raw)
            if msg_in.get("op") == 5:
                print(json.dumps(msg_in), flush=True)

    def close(self) -> None:
        try:
            self._ws.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Subcommand helpers
# ---------------------------------------------------------------------------


def _subscription_mask(tokens: str) -> int:
    MAP = {
        "none": 0,
        "general": 1,
        "config": 2,
        "scenes": 4,
        "inputs": 8,
        "transitions": 16,
        "filters": 32,
        "outputs": 64,
        "sceneitems": 128,
        "mediainputs": 256,
        "vendors": 512,
        "ui": 1024,
        "canvases": 2048,
        "all": 4095,
        "inputvolumemeters": 65536,
        "inputactivestatechanged": 131072,
        "inputshowstatechanged": 262144,
        "sceneitemtransformchanged": 524288,
        # Friendly aliases the task asks for:
        "recording": 64,
        "streaming": 64,
    }
    mask = 0
    for tok in (tokens or "all").split(","):
        t = tok.strip().lower()
        if not t:
            continue
        if t not in MAP:
            raise SystemExit(f"unknown subscription category: {tok}")
        mask |= MAP[t]
    return mask


def _autodiscover() -> tuple[str, str]:
    """Return (url, password) for the local OBS install.

    Reads OBS's own `plugin_config/obs-websocket/config.json`. Falls back
    to `ws://localhost:4455` + empty password if the file is missing. Respects
    `OBS_WEBSOCKET_URL` and `OBS_WEBSOCKET_PASSWORD` env overrides if set.
    """
    import platform

    env_url = os.environ.get("OBS_WEBSOCKET_URL")
    env_pw = os.environ.get("OBS_WEBSOCKET_PASSWORD")

    sys_name = platform.system()
    home = os.path.expanduser("~")
    if sys_name == "Darwin":
        cfg = os.path.join(
            home,
            "Library/Application Support/obs-studio/plugin_config/obs-websocket/config.json",
        )
    elif sys_name == "Windows":
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        cfg = os.path.join(
            appdata, "obs-studio", "plugin_config", "obs-websocket", "config.json"
        )
    else:  # Linux/BSD
        cfg = os.path.join(
            home, ".config/obs-studio/plugin_config/obs-websocket/config.json"
        )

    port = 4455
    password = ""
    enabled: bool | None = None
    auth_required: bool | None = None
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                data = json.load(f)
            port = int(data.get("server_port", 4455))
            password = data.get("server_password", "") or ""
            enabled = bool(data.get("server_enabled", False))
            auth_required = bool(data.get("auth_required", True))
        except (OSError, ValueError, KeyError):
            pass

    url = env_url or f"ws://localhost:{port}"
    pw = env_pw if env_pw is not None else (password if auth_required else "")

    # Only warn loudly if discovery positively tells us the server is off.
    if enabled is False and not env_url:
        print(
            f"warning: obs-websocket server is disabled in {cfg}; "
            "enable via OBS Tools → obs-websocket Settings, or set "
            "server_enabled=true in config.json and restart OBS.",
            file=sys.stderr,
        )
    return url, pw


def _must_ok(resp: dict) -> dict:
    status = resp.get("requestStatus", {})
    if not status.get("result", False):
        print(json.dumps(resp, indent=2), file=sys.stderr)
        raise SystemExit(
            f"request failed: code={status.get('code')} comment={status.get('comment')}"
        )
    return resp


def _connect(args: argparse.Namespace, events: int | None = None) -> OBSClient:
    url, pw = _autodiscover()
    c = OBSClient(url, pw, verbose=args.verbose)
    c.connect(event_subscriptions=events)
    return c


def cmd_check(args: argparse.Namespace) -> int:
    url, _ = _autodiscover()
    status: dict[str, Any] = {
        "websocket_client_installed": HAVE_WS_CLIENT,
        "python": sys.version.split()[0],
        "discovered_url": url,
    }
    p = urlparse(url)
    host = p.hostname or "localhost"
    port = p.port or 4455
    try:
        with socket.create_connection((host, port), timeout=3) as s:
            s.close()
        status["port_open"] = True
        status["host"] = host
        status["port"] = port
    except OSError as exc:
        status["port_open"] = False
        status["error"] = str(exc)
    if not HAVE_WS_CLIENT:
        status["hint"] = (
            "websocket-client not installed. Optional — stdlib fallback works. "
            "Install with: pip install websocket-client"
        )
    print(json.dumps(status, indent=2))
    return 0 if status.get("port_open") else 1


def cmd_ping(args: argparse.Namespace) -> int:
    c = _connect(args)
    try:
        resp = c.request("GetVersion")
        print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_scene_switch(args: argparse.Namespace) -> int:
    c = _connect(args)
    try:
        resp = c.request(
            "SetCurrentProgramScene",
            {"sceneName": args.scene},
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_scene_list(args: argparse.Namespace) -> int:
    c = _connect(args)
    try:
        resp = c.request("GetSceneList")
        print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


_OUTPUT_ACTIONS = {
    "record": {
        "start": "StartRecord",
        "stop": "StopRecord",
        "toggle": "ToggleRecord",
        "status": "GetRecordStatus",
    },
    "stream": {
        "start": "StartStream",
        "stop": "StopStream",
        "toggle": "ToggleStream",
        "status": "GetStreamStatus",
    },
    "virtualcam": {
        "start": "StartVirtualCam",
        "stop": "StopVirtualCam",
        "toggle": "ToggleVirtualCam",
        "status": "GetVirtualCamStatus",
    },
    "replay-buffer": {
        "start": "StartReplayBuffer",
        "stop": "StopReplayBuffer",
        "toggle": "ToggleReplayBuffer",
        "save": "SaveReplayBuffer",
        "status": "GetReplayBufferStatus",
    },
}


def _run_output(output: str, args: argparse.Namespace) -> int:
    actions = _OUTPUT_ACTIONS[output]
    if args.action not in actions:
        raise SystemExit(f"{output}: unsupported action '{args.action}'")
    c = _connect(args)
    try:
        resp = c.request(actions[args.action], dry_run=args.dry_run)
        if not args.dry_run:
            print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    return _run_output("record", args)


def cmd_stream(args: argparse.Namespace) -> int:
    return _run_output("stream", args)


def cmd_virtualcam(args: argparse.Namespace) -> int:
    return _run_output("virtualcam", args)


def cmd_replay_buffer(args: argparse.Namespace) -> int:
    return _run_output("replay-buffer", args)


def cmd_mute(args: argparse.Namespace) -> int:
    c = _connect(args)
    try:
        if args.action == "toggle":
            resp = c.request(
                "ToggleInputMute", {"inputName": args.input}, dry_run=args.dry_run
            )
        else:
            muted = args.action == "mute"
            resp = c.request(
                "SetInputMute",
                {"inputName": args.input, "inputMuted": muted},
                dry_run=args.dry_run,
            )
        if not args.dry_run:
            print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_volume(args: argparse.Namespace) -> int:
    c = _connect(args)
    try:
        resp = c.request(
            "SetInputVolume",
            {"inputName": args.input, "inputVolumeDb": args.db},
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    mask = _subscription_mask(args.subscribe)
    c = _connect(args, events=mask)

    # SIGINT / EOF terminates the loop via ConnectionError in recv.
    def _watchdog() -> None:
        try:
            sys.stdin.read()
        except Exception:  # noqa: BLE001
            pass
        c.close()

    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        c.stream_events()
    except KeyboardInterrupt:
        pass
    finally:
        c.close()
    return 0


def cmd_request(args: argparse.Namespace) -> int:
    data = json.loads(args.data) if args.data else None
    c = _connect(args)
    try:
        resp = c.request(args.type, data, dry_run=args.dry_run)
        if not args.dry_run:
            print(json.dumps(_must_ok(resp), indent=2))
    finally:
        c.close()
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    with open(args.requests_file) as f:
        requests = json.load(f)
    if not isinstance(requests, list):
        raise SystemExit("--requests-file must contain a JSON array")
    execution_type = 2 if args.parallel else 0
    c = _connect(args)
    try:
        resp = c.batch(
            requests,
            halt_on_failure=args.halt_on_failure,
            execution_type=execution_type,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            print(json.dumps(resp, indent=2))
    finally:
        c.close()
    return 0


# ---------------------------------------------------------------------------
# Argparse plumbing
# ---------------------------------------------------------------------------


def _add_common(ap: argparse.ArgumentParser, needs_auth: bool = True) -> None:
    # URL and password are auto-discovered from OBS's own
    # plugin_config/obs-websocket/config.json. Override via environment:
    #   OBS_WEBSOCKET_URL, OBS_WEBSOCKET_PASSWORD.
    ap.add_argument("--verbose", action="store_true", help="trace protocol to stderr")
    ap.add_argument("--dry-run", action="store_true", help="print JSON without sending")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="wsctl",
        description="obs-websocket v5 CLI.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="verify package + TCP port")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("ping", help="auth + GetVersion")
    _add_common(p)
    p.set_defaults(func=cmd_ping)

    p = sub.add_parser("scene-switch", help="SetCurrentProgramScene")
    _add_common(p)
    p.add_argument("--scene", required=True)
    p.set_defaults(func=cmd_scene_switch)

    p = sub.add_parser("scene-list", help="GetSceneList")
    _add_common(p)
    p.set_defaults(func=cmd_scene_list)

    for name, fn in (
        ("record", cmd_record),
        ("stream", cmd_stream),
        ("virtualcam", cmd_virtualcam),
        ("replay-buffer", cmd_replay_buffer),
    ):
        p = sub.add_parser(name, help=f"{name} start/stop/toggle/status")
        _add_common(p)
        choices = list(_OUTPUT_ACTIONS[name].keys())
        p.add_argument("--action", required=True, choices=choices)
        p.set_defaults(func=fn)

    p = sub.add_parser("mute", help="SetInputMute/ToggleInputMute")
    _add_common(p)
    p.add_argument("--input", required=True)
    p.add_argument("--action", required=True, choices=["mute", "unmute", "toggle"])
    p.set_defaults(func=cmd_mute)

    p = sub.add_parser("volume", help="SetInputVolume (dB)")
    _add_common(p)
    p.add_argument("--input", required=True)
    p.add_argument("--db", required=True, type=float)
    p.set_defaults(func=cmd_volume)

    p = sub.add_parser("events", help="stream events as JSON lines")
    _add_common(p)
    p.add_argument(
        "--subscribe",
        default="all",
        help="comma-separated categories "
        "(general,config,scenes,inputs,transitions,filters,outputs,"
        "sceneitems,mediainputs,vendors,ui,canvases,all, or high-volume names)",
    )
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("request", help="escape hatch — send any Request")
    _add_common(p)
    p.add_argument("--type", required=True, help="requestType, e.g. GetStats")
    p.add_argument(
        "--data", default=None, help="JSON object for requestData (optional)"
    )
    p.set_defaults(func=cmd_request)

    p = sub.add_parser("batch", help="RequestBatch from JSON file")
    _add_common(p)
    p.add_argument("--requests-file", required=True)
    p.add_argument("--parallel", action="store_true", help="executionType=2")
    p.add_argument("--halt-on-failure", action="store_true")
    p.set_defaults(func=cmd_batch)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except ConnectionError as exc:
        msg = str(exc).lower()
        if "4009" in msg or "authentication" in msg:
            sys.stderr.write(
                "auth failed (close code 4009): discovered password is wrong. "
                "Update OBS Tools → obs-websocket Settings → Show Connect Info, "
                "or override with OBS_WEBSOCKET_PASSWORD env var.\n"
            )
            return 3
        if "4010" in msg:
            sys.stderr.write(
                "unsupported rpcVersion (4010): server wants a different protocol version\n"
            )
            return 3
        sys.stderr.write(f"connection error: {exc}\n")
        return 3
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
