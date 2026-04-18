#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""oscctl.py — Send / receive / bundle Open Sound Control packets.

Stdlib only. UDP by default; TCP with length-prefix or SLIP framing on request.
Non-interactive. --dry-run prints the raw bytes; --verbose traces.

Subcommands:
    send     Build and send one OSC message.
    dump     Listen and pretty-print incoming packets.
    bundle   Send a bundle from a JSON file.
    ping     Send + wait briefly for a reply on the same socket.
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from pathlib import Path

NTP_EPOCH_OFFSET = 2208988800  # seconds between 1900-01-01 and 1970-01-01


# -----------------------------------------------------------------------------
# OSC builders
# -----------------------------------------------------------------------------


def _pad4(b: bytes) -> bytes:
    return b + b"\x00" * ((4 - len(b) % 4) % 4)


def _osc_string(s: str) -> bytes:
    return _pad4(s.encode("utf-8") + b"\x00")


def _osc_blob(b: bytes) -> bytes:
    return struct.pack(">i", len(b)) + _pad4(b)


def _osc_timetag(tt) -> bytes:
    if isinstance(tt, str):
        if tt in ("now", "immediate"):
            return struct.pack(">II", 0, 1)
        if tt.startswith("+"):
            delta = float(tt[1:])
            ts = time.time() + delta
        else:
            ts = float(tt)
    else:
        ts = float(tt)
    secs = int(ts)
    frac = int((ts - secs) * (1 << 32))
    return struct.pack(">II", secs + NTP_EPOCH_OFFSET, frac & 0xFFFFFFFF)


def build_message(address: str, args: list[tuple[str, object]]) -> bytes:
    tag = "," + "".join(t for t, _ in args)
    out = _osc_string(address) + _osc_string(tag)
    for t, v in args:
        if t == "i":
            out += struct.pack(">i", int(v))
        elif t == "f":
            out += struct.pack(">f", float(v))
        elif t == "h":
            out += struct.pack(">q", int(v))
        elif t == "d":
            out += struct.pack(">d", float(v))
        elif t == "s":
            out += _osc_string(str(v))
        elif t == "b":
            out += _osc_blob(
                v if isinstance(v, (bytes, bytearray)) else bytes.fromhex(str(v))
            )
        elif t in ("T", "F", "N", "I"):
            pass  # no payload
        elif t == "t":
            out += _osc_timetag(v)
        else:
            raise SystemExit(f"unsupported OSC type: {t}")
    return out


def build_bundle(
    timetag, messages: list[tuple[str, list[tuple[str, object]]]]
) -> bytes:
    out = b"#bundle\x00" + _osc_timetag(timetag)
    for addr, args in messages:
        pkt = build_message(addr, args)
        out += struct.pack(">i", len(pkt)) + pkt
    return out


# -----------------------------------------------------------------------------
# SLIP (OSC 1.1 TCP framing)
# -----------------------------------------------------------------------------

SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD


def slip_encode(data: bytes) -> bytes:
    out = bytearray([SLIP_END])
    for b in data:
        if b == SLIP_END:
            out += bytes([SLIP_ESC, SLIP_ESC_END])
        elif b == SLIP_ESC:
            out += bytes([SLIP_ESC, SLIP_ESC_ESC])
        else:
            out.append(b)
    out.append(SLIP_END)
    return bytes(out)


# -----------------------------------------------------------------------------
# OSC parser
# -----------------------------------------------------------------------------


def _read_osc_string(data: bytes, i: int) -> tuple[str, int]:
    end = data.index(b"\x00", i)
    s = data[i:end].decode("utf-8", errors="replace")
    end += 1
    end = (end + 3) & ~3
    return s, end


def parse_packet(data: bytes) -> dict:
    if data.startswith(b"#bundle\x00"):
        tt_sec, tt_frac = struct.unpack(">II", data[8:16])
        unix = (tt_sec - NTP_EPOCH_OFFSET) + tt_frac / (1 << 32)
        i = 16
        contents = []
        while i < len(data):
            (sz,) = struct.unpack(">i", data[i : i + 4])
            i += 4
            contents.append(parse_packet(data[i : i + sz]))
            i += sz
        return {"type": "bundle", "timetag": unix, "contents": contents}
    # message
    addr, i = _read_osc_string(data, 0)
    tag, i = _read_osc_string(data, i)
    args: list = []
    for t in tag[1:]:
        if t == "i":
            (v,) = struct.unpack(">i", data[i : i + 4])
            i += 4
            args.append(("i", v))
        elif t == "f":
            (v,) = struct.unpack(">f", data[i : i + 4])
            i += 4
            args.append(("f", v))
        elif t == "h":
            (v,) = struct.unpack(">q", data[i : i + 8])
            i += 8
            args.append(("h", v))
        elif t == "d":
            (v,) = struct.unpack(">d", data[i : i + 8])
            i += 8
            args.append(("d", v))
        elif t == "s":
            s, i = _read_osc_string(data, i)
            args.append(("s", s))
        elif t == "b":
            (sz,) = struct.unpack(">i", data[i : i + 4])
            i += 4
            blob = data[i : i + sz]
            i += sz
            i = (i + 3) & ~3
            args.append(("b", blob.hex()))
        elif t in ("T", "F", "N", "I"):
            args.append((t, None))
        elif t == "t":
            s, f = struct.unpack(">II", data[i : i + 8])
            i += 8
            args.append(("t", (s - NTP_EPOCH_OFFSET) + f / (1 << 32)))
        else:
            # unknown tag — stop to avoid infinite loops
            break
    return {"type": "message", "address": addr, "args": args}


# -----------------------------------------------------------------------------
# Subcommands
# -----------------------------------------------------------------------------


def _collect_args(
    raw: list[str], ns: argparse.Namespace | None = None
) -> list[tuple[str, object]]:
    """Parse sequential --int/--float/... flags into (type, value) tuples.

    Because argparse.REMAINDER swallows -- flags too, we also extract
    --dry-run/--verbose here and set them on the provided namespace.
    """
    args: list[tuple[str, object]] = []
    i = 0
    while i < len(raw):
        tok = raw[i]
        if tok == "--int":
            args.append(("i", int(raw[i + 1])))
            i += 2
        elif tok == "--float":
            args.append(("f", float(raw[i + 1])))
            i += 2
        elif tok == "--int64":
            args.append(("h", int(raw[i + 1])))
            i += 2
        elif tok == "--double":
            args.append(("d", float(raw[i + 1])))
            i += 2
        elif tok == "--string":
            args.append(("s", str(raw[i + 1])))
            i += 2
        elif tok == "--blob-hex":
            args.append(("b", bytes.fromhex(raw[i + 1])))
            i += 2
        elif tok == "--true":
            args.append(("T", None))
            i += 1
        elif tok == "--false":
            args.append(("F", None))
            i += 1
        elif tok == "--nil":
            args.append(("N", None))
            i += 1
        elif tok == "--impulse":
            args.append(("I", None))
            i += 1
        elif tok == "--timetag":
            args.append(("t", raw[i + 1]))
            i += 2
        elif tok == "--dry-run":
            if ns is not None:
                ns.dry_run = True
            i += 1
        elif tok == "--verbose":
            if ns is not None:
                ns.verbose = True
            i += 1
        else:
            raise SystemExit(f"unknown arg flag: {tok}")
    return args


def _send(
    payload: bytes, host: str, port: int, tcp: bool, framing: str, verbose: bool
) -> None:
    if tcp:
        s = socket.create_connection((host, port), timeout=5)
        try:
            if framing == "slip":
                frame = slip_encode(payload)
            else:
                frame = struct.pack(">i", len(payload)) + payload
            if verbose:
                sys.stderr.write(f"[tcp -> {host}:{port}] {frame.hex()}\n")
            s.sendall(frame)
        finally:
            s.close()
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if verbose:
            sys.stderr.write(f"[udp -> {host}:{port}] {payload.hex()}\n")
        s.sendto(payload, (host, port))
        s.close()


def cmd_send(args: argparse.Namespace) -> int:
    osc_args = _collect_args(args.args, args)
    payload = build_message(args.address, osc_args)
    if args.dry_run:
        print(payload.hex(" "))
        return 0
    _send(payload, args.host, args.port, args.tcp, args.tcp_framing, args.verbose)
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    spec = json.loads(Path(args.json).read_text())
    timetag = spec.get("timetag", "now")
    msgs = []
    for m in spec.get("messages", []):
        addr = m["address"]
        tup_args = [(a["type"], a.get("value")) for a in m.get("args", [])]
        msgs.append((addr, tup_args))
    payload = build_bundle(timetag, msgs)
    if args.dry_run:
        print(payload.hex(" "))
        return 0
    _send(payload, args.host, args.port, args.tcp, args.tcp_framing, args.verbose)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((args.bind, args.port))
    if args.dry_run:
        print(f"[dry-run] would listen on {args.bind}:{args.port}")
        s.close()
        return 0
    sys.stderr.write(f"listening on {args.bind}:{args.port} — Ctrl-C to stop\n")
    try:
        while True:
            data, addr = s.recvfrom(65535)
            parsed = parse_packet(data)
            print(json.dumps({"from": f"{addr[0]}:{addr[1]}", **parsed}, default=str))
            sys.stdout.flush()
    except KeyboardInterrupt:
        return 0
    finally:
        s.close()


def cmd_ping(args: argparse.Namespace) -> int:
    osc_args = _collect_args(args.args, args)
    payload = build_message(args.address, osc_args)
    if args.dry_run:
        print(payload.hex(" "))
        return 0
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 0))
    s.settimeout(args.wait)
    if args.verbose:
        sys.stderr.write(f"[udp -> {args.host}:{args.port}] {payload.hex()}\n")
    s.sendto(payload, (args.host, args.port))
    try:
        data, addr = s.recvfrom(65535)
        print(
            json.dumps(
                {"reply_from": f"{addr[0]}:{addr[1]}", **parse_packet(data)},
                default=str,
            )
        )
        return 0
    except socket.timeout:
        sys.stderr.write("no reply within --wait seconds\n")
        return 1
    finally:
        s.close()


# -----------------------------------------------------------------------------
# Argparse
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Open Sound Control CLI (UDP/TCP).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("send", help="send one OSC message")
    sp.add_argument("--host", required=True)
    sp.add_argument("--port", type=int, required=True)
    sp.add_argument("--tcp", action="store_true")
    sp.add_argument("--tcp-framing", choices=["length", "slip"], default="length")
    sp.add_argument("address")
    sp.add_argument("args", nargs=argparse.REMAINDER)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_send)

    sp = sub.add_parser("dump", help="listen for OSC packets")
    sp.add_argument("--port", type=int, required=True)
    sp.add_argument("--bind", default="0.0.0.0")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_dump)

    sp = sub.add_parser("bundle", help="send a bundle from JSON")
    sp.add_argument("--host", required=True)
    sp.add_argument("--port", type=int, required=True)
    sp.add_argument("--tcp", action="store_true")
    sp.add_argument("--tcp-framing", choices=["length", "slip"], default="length")
    sp.add_argument("--json", required=True, help="bundle spec JSON")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_bundle)

    sp = sub.add_parser("ping", help="send then wait briefly for reply")
    sp.add_argument("--host", required=True)
    sp.add_argument("--port", type=int, required=True)
    sp.add_argument("--wait", type=float, default=0.5)
    sp.add_argument("address")
    sp.add_argument("args", nargs=argparse.REMAINDER)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_ping)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
