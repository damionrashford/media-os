#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""viscactl.py — Drive Sony VISCA PTZ cameras over serial or UDP:52381.

Stdlib only. pyserial is optional; without it, --transport serial exits with a hint.

Subcommands:
    pan-tilt    Pan/tilt drive (x/y signed speed) for a duration.
    zoom        Zoom tele/wide at variable speed for a duration.
    focus       Focus auto/manual/near/far.
    preset      save | recall | reset a preset number.
    power       on | off.
    home        Recall factory home position.
    reset       Recenter pan/tilt.
    raw         Send a raw hex packet.

Common flags:
    --transport {udp-ip,serial}   (default udp-ip)
    --host HOST --port PORT       (udp-ip, default 52381)
    --serial-port /dev/... --baud (serial, requires pyserial)
    --address 1..8                (1-7 normal, 8 broadcast)
    --dry-run                     print packet, skip send
    --verbose                     trace bytes to stderr

Every VISCA packet ends with 0xFF. First byte = 0x80 | address.
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import time

UDP_PORT_DEFAULT = 52381
UDP_TIMEOUT = 3.0

# -----------------------------------------------------------------------------
# VISCA packet builders
# -----------------------------------------------------------------------------


def _addr_byte(addr: int) -> int:
    if addr < 1 or addr > 8:
        raise ValueError(f"address must be 1..8 (got {addr})")
    return 0x80 | addr


def build_pan_tilt(addr: int, x: int, y: int) -> bytes:
    """x/y signed: negative left/down, positive right/up, zero stop. Speed magnitude 1..24."""
    abs_x = max(1, min(24, abs(x))) if x != 0 else 1
    abs_y = max(1, min(20, abs(y))) if y != 0 else 1
    dir_x = 0x03 if x == 0 else (0x01 if x < 0 else 0x02)
    dir_y = 0x03 if y == 0 else (0x01 if y > 0 else 0x02)  # y: +up=01, -down=02
    return bytes([_addr_byte(addr), 0x01, 0x06, 0x01, abs_x, abs_y, dir_x, dir_y, 0xFF])


def build_pan_tilt_stop(addr: int) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x06, 0x01, 0x01, 0x01, 0x03, 0x03, 0xFF])


def build_zoom_stop(addr: int) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x07, 0x00, 0xFF])


def build_zoom(addr: int, direction: str, speed: int) -> bytes:
    """direction tele|wide; speed 0..7. Stop via build_zoom_stop."""
    speed = max(0, min(7, speed))
    if direction == "tele":
        code = 0x20 | speed
    elif direction == "wide":
        code = 0x30 | speed
    else:
        raise ValueError("zoom direction must be tele or wide")
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x07, code, 0xFF])


def build_focus_mode(addr: int, mode: str) -> bytes:
    if mode == "auto":
        return bytes([_addr_byte(addr), 0x01, 0x04, 0x38, 0x02, 0xFF])
    if mode == "manual":
        return bytes([_addr_byte(addr), 0x01, 0x04, 0x38, 0x03, 0xFF])
    raise ValueError("focus mode must be auto or manual")


def build_focus_drive(addr: int, direction: str, speed: int) -> bytes:
    speed = max(0, min(7, speed))
    if direction == "far":
        code = 0x20 | speed
    elif direction == "near":
        code = 0x30 | speed
    else:
        raise ValueError("focus direction must be near or far")
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x08, code, 0xFF])


def build_focus_stop(addr: int) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x08, 0x00, 0xFF])


def build_preset(addr: int, action: str, number: int) -> bytes:
    if number < 0 or number > 255:
        raise ValueError("preset number must be 0..255")
    codes = {"reset": 0x00, "save": 0x01, "recall": 0x02}
    if action not in codes:
        raise ValueError(f"preset action must be one of {list(codes)}")
    lo = number & 0x7F  # Sony spec: preset id low 7 bits in last byte
    hi = (number >> 7) & 0x01
    # For 0..127 this collapses to the standard 8x 01 04 3F aa 0p FF form.
    if number <= 0x7F:
        return bytes([_addr_byte(addr), 0x01, 0x04, 0x3F, codes[action], lo, 0xFF])
    # Extended range: some cameras accept the 0..255 form as [0p 0p]
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x3F, codes[action], hi, lo, 0xFF])


def build_power(addr: int, on: bool) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x04, 0x00, 0x02 if on else 0x03, 0xFF])


def build_home(addr: int) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x06, 0x04, 0xFF])


def build_pt_reset(addr: int) -> bytes:
    return bytes([_addr_byte(addr), 0x01, 0x06, 0x05, 0xFF])


# -----------------------------------------------------------------------------
# Transports
# -----------------------------------------------------------------------------


class UDPTransport:
    """VISCA over UDP:52381 with the 8-byte payload header."""

    def __init__(self, host: str, port: int = UDP_PORT_DEFAULT, verbose: bool = False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.seq = 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(UDP_TIMEOUT)

    def _wrap(self, payload: bytes, kind: str) -> bytes:
        # payload type: 0x0100 = VISCA command, 0x0110 = VISCA inquiry
        if kind == "inquiry":
            ptype = 0x0110
        else:
            ptype = 0x0100
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        header = struct.pack(">HHI", ptype, len(payload), self.seq)
        return header + payload

    def send(self, payload: bytes, kind: str = "command") -> bytes:
        pkt = self._wrap(payload, kind)
        if self.verbose:
            sys.stderr.write(
                f"[udp-ip -> {self.host}:{self.port}] "
                f"hdr={pkt[:8].hex()} payload={payload.hex()}\n"
            )
        self._sock.sendto(pkt, (self.host, self.port))
        try:
            data, _ = self._sock.recvfrom(4096)
        except socket.timeout:
            return b""
        if self.verbose:
            sys.stderr.write(f"[udp-ip <- {self.host}:{self.port}] {data.hex()}\n")
        return data

    def close(self) -> None:
        self._sock.close()


class SerialTransport:
    """VISCA over RS-232/422/485 via pyserial (optional)."""

    def __init__(self, port: str, baud: int, verbose: bool = False):
        try:
            import serial  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise SystemExit(
                "pyserial not installed; run `pip install pyserial` or use --transport udp-ip"
            ) from e
        self.verbose = verbose
        self._ser = serial.Serial(
            port, baud, bytesize=8, parity="N", stopbits=1, timeout=2
        )

    def send(self, payload: bytes, kind: str = "command") -> bytes:
        if self.verbose:
            sys.stderr.write(f"[serial ->] {payload.hex()}\n")
        self._ser.write(payload)
        # Read until terminator 0xFF arrives twice (ACK + Completion)
        buf = b""
        deadline = time.time() + 2.0
        while time.time() < deadline:
            b = self._ser.read(1)
            if not b:
                break
            buf += b
            if buf.count(b"\xff") >= 2:
                break
        if self.verbose:
            sys.stderr.write(f"[serial <-] {buf.hex()}\n")
        return buf

    def close(self) -> None:
        self._ser.close()


def make_transport(args: argparse.Namespace):
    if args.transport == "udp-ip":
        if not args.host:
            raise SystemExit("--host is required for --transport udp-ip")
        return UDPTransport(args.host, args.port, verbose=args.verbose)
    return SerialTransport(args.serial_port, args.baud, verbose=args.verbose)


# -----------------------------------------------------------------------------
# Command helpers
# -----------------------------------------------------------------------------


def _emit_and_send(
    args: argparse.Namespace, payload: bytes, kind: str = "command"
) -> int:
    if args.dry_run:
        print(f"payload: {payload.hex(' ')}")
        if args.transport == "udp-ip":
            hdr = struct.pack(
                ">HHI", 0x0100 if kind == "command" else 0x0110, len(payload), 1
            )
            print(f"udp-ip header (seq=1): {hdr.hex(' ')}")
        return 0
    tx = make_transport(args)
    try:
        reply = tx.send(payload, kind=kind)
        if reply:
            print(reply.hex(" "))
    finally:
        tx.close()
    return 0


def _sleep_then_stop(
    args: argparse.Namespace, stop_payload: bytes, duration: float
) -> None:
    if args.dry_run or duration <= 0:
        return
    time.sleep(duration)
    tx = make_transport(args)
    try:
        tx.send(stop_payload)
    finally:
        tx.close()


def cmd_pan_tilt(args: argparse.Namespace) -> int:
    payload = build_pan_tilt(args.address, args.x, args.y)
    _emit_and_send(args, payload)
    if args.duration and args.duration > 0:
        _sleep_then_stop(args, build_pan_tilt_stop(args.address), args.duration)
    return 0


def cmd_zoom(args: argparse.Namespace) -> int:
    payload = build_zoom(args.address, args.direction, args.speed)
    _emit_and_send(args, payload)
    if args.duration and args.duration > 0:
        _sleep_then_stop(args, build_zoom_stop(args.address), args.duration)
    return 0


def cmd_focus(args: argparse.Namespace) -> int:
    if args.mode in ("auto", "manual"):
        payload = build_focus_mode(args.address, args.mode)
    elif args.mode in ("near", "far"):
        payload = build_focus_drive(args.address, args.mode, args.speed)
    else:
        raise SystemExit(f"unknown focus mode: {args.mode}")
    _emit_and_send(args, payload)
    if args.mode in ("near", "far") and args.duration and args.duration > 0:
        _sleep_then_stop(args, build_focus_stop(args.address), args.duration)
    return 0


def cmd_preset(args: argparse.Namespace) -> int:
    payload = build_preset(args.address, args.action, args.number)
    return _emit_and_send(args, payload)


def cmd_power(args: argparse.Namespace) -> int:
    payload = build_power(args.address, args.action == "on")
    return _emit_and_send(args, payload)


def cmd_home(args: argparse.Namespace) -> int:
    return _emit_and_send(args, build_home(args.address))


def cmd_reset(args: argparse.Namespace) -> int:
    return _emit_and_send(args, build_pt_reset(args.address))


def cmd_raw(args: argparse.Namespace) -> int:
    hex_str = args.hex.replace(" ", "").replace(":", "")
    payload = bytes.fromhex(hex_str)
    return _emit_and_send(args, payload)


# -----------------------------------------------------------------------------
# Argparse plumbing
# -----------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--transport", choices=["udp-ip", "serial"], default="udp-ip")
    p.add_argument("--host", default=os.environ.get("VISCA_HOST"))
    p.add_argument("--port", type=int, default=UDP_PORT_DEFAULT)
    p.add_argument("--serial-port", default=os.environ.get("VISCA_SERIAL_PORT"))
    p.add_argument("--baud", type=int, default=9600)
    p.add_argument(
        "--address", type=int, default=1, help="camera address 1..8 (8=broadcast)"
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VISCA PTZ CLI (serial or UDP:52381).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("pan-tilt", help="pan-tilt drive for a duration")
    _add_common(sp)
    sp.add_argument("--x", type=int, required=True, help="pan speed, signed (-24..24)")
    sp.add_argument("--y", type=int, required=True, help="tilt speed, signed (-20..20)")
    sp.add_argument("--duration", type=float, default=0.0, help="stop after N seconds")
    sp.set_defaults(fn=cmd_pan_tilt)

    sp = sub.add_parser("zoom", help="zoom tele/wide for a duration")
    _add_common(sp)
    sp.add_argument("--direction", choices=["tele", "wide"], required=True)
    sp.add_argument("--speed", type=int, default=4, help="0..7")
    sp.add_argument("--duration", type=float, default=0.0)
    sp.set_defaults(fn=cmd_zoom)

    sp = sub.add_parser("focus", help="focus auto/manual/near/far")
    _add_common(sp)
    sp.add_argument("--mode", choices=["auto", "manual", "near", "far"], required=True)
    sp.add_argument("--speed", type=int, default=4, help="0..7 (for near/far)")
    sp.add_argument("--duration", type=float, default=0.0)
    sp.set_defaults(fn=cmd_focus)

    sp = sub.add_parser("preset", help="save / recall / reset a preset")
    _add_common(sp)
    sp.add_argument("--action", choices=["save", "recall", "reset"], required=True)
    sp.add_argument("--number", type=int, required=True)
    sp.set_defaults(fn=cmd_preset)

    sp = sub.add_parser("power", help="power on/off")
    _add_common(sp)
    sp.add_argument("--action", choices=["on", "off"], required=True)
    sp.set_defaults(fn=cmd_power)

    sp = sub.add_parser("home", help="recall home position")
    _add_common(sp)
    sp.set_defaults(fn=cmd_home)

    sp = sub.add_parser("reset", help="pan-tilt reset / recenter")
    _add_common(sp)
    sp.set_defaults(fn=cmd_reset)

    sp = sub.add_parser("raw", help="send a raw hex packet")
    _add_common(sp)
    sp.add_argument("--hex", required=True, help="e.g. '81 01 04 00 02 FF'")
    sp.set_defaults(fn=cmd_raw)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except (ValueError, SystemExit) as e:
        if isinstance(e, SystemExit):
            raise
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
