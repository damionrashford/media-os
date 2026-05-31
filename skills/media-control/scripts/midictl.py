#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""midictl.py — MIDI 1.0 send/dump + SMF parse/write.

Stdlib only. For port I/O, prefers `sendmidi`/`receivemidi` (gbevin), falls
back to ALSA `amidi`/`aseqdump` (Linux), and finally to `mido`/`rtmidi` if
those Python packages happen to be installed. SMF parsing/writing is pure
Python.

Non-interactive. --dry-run prints the bytes/commands it would send; --verbose
traces to stderr.

Subcommands:
    list-ports
    send note-on | note-off | cc | program | sysex
    dump               Monitor incoming events (uses receivemidi or aseqdump)
    monitor            Alias for dump
    smf-dump <file>    Parse a Standard MIDI File
    smf-write          Author a .mid from JSON events
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Tool detection
# -----------------------------------------------------------------------------


def _which(name: str) -> str | None:
    return shutil.which(name)


def _have_mido() -> bool:
    try:
        import mido  # type: ignore  # noqa: F401

        return True
    except ImportError:
        return False


# -----------------------------------------------------------------------------
# list-ports
# -----------------------------------------------------------------------------


def cmd_list_ports(args: argparse.Namespace) -> int:
    sys_name = platform.system()
    sendmidi = _which("sendmidi")
    amidi = _which("amidi")
    aconnect = _which("aconnect")
    out: dict = {"platform": sys_name, "tools": {}}
    if sendmidi:
        r = subprocess.run([sendmidi, "list"], capture_output=True, text=True)
        out["tools"]["sendmidi"] = r.stdout.strip().splitlines()
    if amidi:
        r = subprocess.run([amidi, "-l"], capture_output=True, text=True)
        out["tools"]["amidi"] = r.stdout.strip().splitlines()
    if aconnect:
        r = subprocess.run([aconnect, "-l"], capture_output=True, text=True)
        out["tools"]["aconnect"] = r.stdout.strip().splitlines()
    if _have_mido():
        import mido  # type: ignore

        out["tools"]["mido_inputs"] = mido.get_input_names()
        out["tools"]["mido_outputs"] = mido.get_output_names()
    if not out["tools"]:
        out["hint"] = (
            "no MIDI tool found. Install `sendmidi` (brew install gbevin/tools/sendmidi) "
            "or ALSA `amidi` (apt install alsa-utils), or pip install mido/python-rtmidi."
        )
    print(json.dumps(out, indent=2))
    return 0


# -----------------------------------------------------------------------------
# send
# -----------------------------------------------------------------------------


def _send_via_sendmidi(port: str, args: list[str], verbose: bool, dry_run: bool) -> int:
    cmd = ["sendmidi", "dev", port] + args
    if verbose or dry_run:
        sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _send_via_amidi(port: str, hex_bytes: str, verbose: bool, dry_run: bool) -> int:
    cmd = ["amidi", "-p", port, "-S", hex_bytes]
    if verbose or dry_run:
        sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _send_via_mido(port: str, msg_kwargs: dict, verbose: bool, dry_run: bool) -> int:
    if verbose or dry_run:
        sys.stderr.write(f"[mido] port={port!r} msg={msg_kwargs}\n")
    if dry_run:
        return 0
    import mido  # type: ignore

    with mido.open_output(port) as out:
        out.send(mido.Message(**msg_kwargs))
    return 0


def _channel_wire(ch_ui: int) -> int:
    if ch_ui < 1 or ch_ui > 16:
        raise SystemExit("--channel must be 1..16")
    return ch_ui - 1


def cmd_send(args: argparse.Namespace) -> int:
    kind = args.kind
    ch_wire = (
        _channel_wire(args.channel) if hasattr(args, "channel") and args.channel else 0
    )

    if _which("sendmidi"):
        if kind == "note-on":
            return _send_via_sendmidi(
                args.port,
                ["ch", str(args.channel), "on", str(args.note), str(args.velocity)],
                args.verbose,
                args.dry_run,
            )
        if kind == "note-off":
            return _send_via_sendmidi(
                args.port,
                [
                    "ch",
                    str(args.channel),
                    "off",
                    str(args.note),
                    str(args.velocity or 0),
                ],
                args.verbose,
                args.dry_run,
            )
        if kind == "cc":
            return _send_via_sendmidi(
                args.port,
                ["ch", str(args.channel), "cc", str(args.cc), str(args.value)],
                args.verbose,
                args.dry_run,
            )
        if kind == "program":
            return _send_via_sendmidi(
                args.port,
                ["ch", str(args.channel), "pc", str(args.program)],
                args.verbose,
                args.dry_run,
            )
        if kind == "sysex":
            hexs = args.hex.replace(" ", "").replace(":", "")
            b = bytes.fromhex(hexs)
            # sendmidi syx expects space-separated decimal bytes inside F0..F7
            if b[0] != 0xF0 or b[-1] != 0xF7:
                raise SystemExit("sysex must start with F0 and end with F7")
            inner = " ".join(str(x) for x in b[1:-1])
            return _send_via_sendmidi(
                args.port, ["syx", inner], args.verbose, args.dry_run
            )

    # ALSA amidi fallback: expects hex string
    if _which("amidi"):
        if kind == "note-on":
            h = f"{0x90 | ch_wire:02X} {args.note:02X} {args.velocity:02X}"
        elif kind == "note-off":
            h = f"{0x80 | ch_wire:02X} {args.note:02X} {(args.velocity or 0):02X}"
        elif kind == "cc":
            h = f"{0xB0 | ch_wire:02X} {args.cc:02X} {args.value:02X}"
        elif kind == "program":
            h = f"{0xC0 | ch_wire:02X} {args.program:02X}"
        elif kind == "sysex":
            h = args.hex
        else:
            raise SystemExit(f"unknown kind {kind}")
        return _send_via_amidi(args.port, h, args.verbose, args.dry_run)

    # mido fallback
    if _have_mido():
        if kind == "note-on":
            kw = {
                "type": "note_on",
                "channel": ch_wire,
                "note": args.note,
                "velocity": args.velocity,
            }
        elif kind == "note-off":
            kw = {
                "type": "note_off",
                "channel": ch_wire,
                "note": args.note,
                "velocity": args.velocity or 0,
            }
        elif kind == "cc":
            kw = {
                "type": "control_change",
                "channel": ch_wire,
                "control": args.cc,
                "value": args.value,
            }
        elif kind == "program":
            kw = {"type": "program_change", "channel": ch_wire, "program": args.program}
        elif kind == "sysex":
            hexs = args.hex.replace(" ", "")
            b = bytes.fromhex(hexs)
            if b[0] == 0xF0 and b[-1] == 0xF7:
                kw = {"type": "sysex", "data": list(b[1:-1])}
            else:
                raise SystemExit("sysex must be framed F0..F7")
        else:
            raise SystemExit(f"unknown kind {kind}")
        return _send_via_mido(args.port, kw, args.verbose, args.dry_run)

    raise SystemExit(
        "no MIDI output tool. Install `sendmidi` (brew install gbevin/tools/sendmidi), "
        "ALSA `amidi`, or Python `mido`/`python-rtmidi`."
    )


# -----------------------------------------------------------------------------
# dump / monitor
# -----------------------------------------------------------------------------


def cmd_dump(args: argparse.Namespace) -> int:
    if _which("receivemidi"):
        cmd = ["receivemidi", "dev", args.port]
        if args.verbose or args.dry_run:
            sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
        if args.dry_run:
            return 0
        return subprocess.call(cmd)
    if _which("aseqdump"):
        cmd = ["aseqdump", "-p", args.port]
        if args.verbose or args.dry_run:
            sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
        if args.dry_run:
            return 0
        return subprocess.call(cmd)
    raise SystemExit("install `receivemidi` (gbevin) or ALSA `aseqdump` to monitor")


# -----------------------------------------------------------------------------
# SMF parser
# -----------------------------------------------------------------------------


def _read_vlq(data: bytes, i: int) -> tuple[int, int]:
    val = 0
    while True:
        b = data[i]
        i += 1
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            return val, i


def smf_parse(path: Path) -> dict:
    data = path.read_bytes()
    if data[0:4] != b"MThd":
        raise SystemExit("not an SMF: missing MThd")
    hlen = struct.unpack(">I", data[4:8])[0]
    fmt, ntracks, division = struct.unpack(">HHH", data[8 : 8 + hlen])
    pos = 8 + hlen
    tracks = []
    for _ in range(ntracks):
        if data[pos : pos + 4] != b"MTrk":
            break
        tlen = struct.unpack(">I", data[pos + 4 : pos + 8])[0]
        pos += 8
        end = pos + tlen
        events = []
        running_status = 0
        while pos < end:
            delta, pos = _read_vlq(data, pos)
            b = data[pos]
            if b & 0x80:
                status = b
                pos += 1
            else:
                status = running_status
            if status in (0xF0, 0xF7):  # SysEx
                slen, pos = _read_vlq(data, pos)
                payload = data[pos : pos + slen]
                pos += slen
                events.append({"delta": delta, "type": "sysex", "data": payload.hex()})
                running_status = 0
            elif status == 0xFF:  # Meta
                mt = data[pos]
                pos += 1
                mlen, pos = _read_vlq(data, pos)
                payload = data[pos : pos + mlen]
                pos += mlen
                events.append(
                    {"delta": delta, "type": "meta", "meta": mt, "data": payload.hex()}
                )
                running_status = 0
            else:
                running_status = status
                hi = status & 0xF0
                ch = status & 0x0F
                if hi in (0xC0, 0xD0):  # 1 data byte
                    d1 = data[pos]
                    pos += 1
                    events.append(
                        {"delta": delta, "status": hi, "channel": ch, "data1": d1}
                    )
                else:
                    d1 = data[pos]
                    d2 = data[pos + 1]
                    pos += 2
                    events.append(
                        {
                            "delta": delta,
                            "status": hi,
                            "channel": ch,
                            "data1": d1,
                            "data2": d2,
                        }
                    )
        tracks.append(events)
        pos = end
    return {"format": fmt, "ntracks": ntracks, "division": division, "tracks": tracks}


def cmd_smf_dump(args: argparse.Namespace) -> int:
    parsed = smf_parse(Path(args.path))
    if args.format == "json":
        print(json.dumps(parsed, indent=2))
    else:
        print(
            f"format={parsed['format']} tracks={parsed['ntracks']} division={parsed['division']}"
        )
        for i, tr in enumerate(parsed["tracks"]):
            print(f"--- Track {i} ({len(tr)} events) ---")
            for e in tr:
                print(json.dumps(e))
    return 0


# -----------------------------------------------------------------------------
# SMF writer
# -----------------------------------------------------------------------------


def _write_vlq(n: int) -> bytes:
    if n < 0:
        raise ValueError("VLQ can't encode negatives")
    buf = bytearray([n & 0x7F])
    n >>= 7
    while n:
        buf.insert(0, 0x80 | (n & 0x7F))
        n >>= 7
    return bytes(buf)


def smf_write(
    events: list[dict], out_path: Path, *, ppq: int = 480, fmt: int = 1
) -> None:
    # Build a single MTrk (format 0/1 — if fmt=1 we still ship 1 track for simplicity)
    track = bytearray()
    for ev in events:
        delta = int(ev.get("delta", 0))
        track += _write_vlq(delta)
        t = ev["type"]
        if t == "tempo":
            bpm = float(ev.get("bpm", 120.0))
            uspq = int(60_000_000 / bpm)
            payload = uspq.to_bytes(3, "big")
            track += bytes([0xFF, 0x51, 0x03]) + payload
        elif t == "time-signature":
            num = int(ev.get("numerator", 4))
            den = int(ev.get("denominator", 4))
            track += bytes([0xFF, 0x58, 0x04, num, int.bit_length(den) - 1, 24, 8])
        elif t == "track-name":
            name = str(ev.get("name", "")).encode("utf-8")
            track += bytes([0xFF, 0x03]) + _write_vlq(len(name)) + name
        elif t == "note-on":
            ch = _channel_wire(int(ev["channel"]))
            track += bytes(
                [0x90 | ch, int(ev["note"]) & 0x7F, int(ev["velocity"]) & 0x7F]
            )
        elif t == "note-off":
            ch = _channel_wire(int(ev["channel"]))
            track += bytes(
                [0x80 | ch, int(ev["note"]) & 0x7F, int(ev.get("velocity", 0)) & 0x7F]
            )
        elif t == "cc":
            ch = _channel_wire(int(ev["channel"]))
            track += bytes([0xB0 | ch, int(ev["cc"]) & 0x7F, int(ev["value"]) & 0x7F])
        elif t == "program":
            ch = _channel_wire(int(ev["channel"]))
            track += bytes([0xC0 | ch, int(ev["program"]) & 0x7F])
        elif t == "sysex":
            data = bytes.fromhex(str(ev["data"]).replace(" ", ""))
            body = data[1:] if data[0] == 0xF0 else data
            track += bytes([0xF0]) + _write_vlq(len(body)) + body
        else:
            raise SystemExit(f"unsupported event type: {t}")
    # End-of-track
    track += _write_vlq(0) + bytes([0xFF, 0x2F, 0x00])

    # Header
    with out_path.open("wb") as f:
        f.write(b"MThd")
        f.write(struct.pack(">I", 6))
        f.write(struct.pack(">HHH", fmt, 1, ppq))
        f.write(b"MTrk")
        f.write(struct.pack(">I", len(track)))
        f.write(bytes(track))


def cmd_smf_write(args: argparse.Namespace) -> int:
    events = json.loads(Path(args.json).read_text())
    if args.dry_run:
        print(
            json.dumps(
                {
                    "would_write": args.out,
                    "events": len(events),
                    "ppq": args.ppq,
                    "format": args.format,
                }
            )
        )
        return 0
    smf_write(events, Path(args.out), ppq=args.ppq, fmt=args.format)
    print(args.out)
    return 0


# -----------------------------------------------------------------------------
# Argparse
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MIDI CLI: wire send/dump + SMF parse/write."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-ports", help="list available MIDI ports")
    sp.add_argument("--verbose", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(fn=cmd_list_ports)

    sp = sub.add_parser("send", help="send a MIDI message")
    send_sub = sp.add_subparsers(dest="kind", required=True)

    for name in ("note-on", "note-off"):
        c = send_sub.add_parser(name)
        c.add_argument("--port", required=True)
        c.add_argument("--channel", type=int, required=True, help="1..16")
        c.add_argument("--note", type=int, required=True)
        c.add_argument("--velocity", type=int, default=64)
        c.add_argument("--dry-run", action="store_true")
        c.add_argument("--verbose", action="store_true")
        c.set_defaults(fn=cmd_send)

    c = send_sub.add_parser("cc")
    c.add_argument("--port", required=True)
    c.add_argument("--channel", type=int, required=True)
    c.add_argument("--cc", type=int, required=True)
    c.add_argument("--value", type=int, required=True)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--verbose", action="store_true")
    c.set_defaults(fn=cmd_send)

    c = send_sub.add_parser("program")
    c.add_argument("--port", required=True)
    c.add_argument("--channel", type=int, required=True)
    c.add_argument("--program", type=int, required=True)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--verbose", action="store_true")
    c.set_defaults(fn=cmd_send)

    c = send_sub.add_parser("sysex")
    c.add_argument("--port", required=True)
    c.add_argument("--hex", required=True, help="e.g. 'F0 7E 7F 06 01 F7'")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--verbose", action="store_true")
    c.set_defaults(fn=cmd_send)

    for name in ("dump", "monitor"):
        sp = sub.add_parser(name, help="monitor incoming MIDI events")
        sp.add_argument("--port", required=True)
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--verbose", action="store_true")
        sp.set_defaults(fn=cmd_dump)

    sp = sub.add_parser("smf-dump", help="parse a Standard MIDI File")
    sp.add_argument("path")
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_smf_dump)

    sp = sub.add_parser("smf-write", help="author a .mid from JSON events")
    sp.add_argument("--json", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--ppq", type=int, default=480)
    sp.add_argument("--format", type=int, default=1)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_smf_write)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
