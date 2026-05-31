#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""dmxctl.py — DMX / Art-Net / sACN CLI.

Stdlib only. Wraps OLA CLIs when present; for sACN and Art-Net we also ship
pure-Python senders so the skill works without OLA.

Subcommands:
    list-devices     OLA ola_dev_info + ola_uni_info (or serial fallback)
    send-dmx         Wrap ola_streaming_client for universe output
    sacn-send        Pure-Python sACN E1.31 multicast sender
    artnet-poll      Broadcast OpPoll and collect ArtPollReply
    record           Wrap ola_recorder
    stream           Stdin-driven streaming DMX
    rdm-scan         Wrap ola_rdm_discover
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import struct
import subprocess
import sys
import time
import uuid


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _which(name: str) -> str | None:
    return shutil.which(name)


def _parse_slots(spec: str) -> list[int]:
    vals = [int(x) for x in spec.split(",") if x.strip() != ""]
    if any(v < 0 or v > 255 for v in vals):
        raise SystemExit("slot values must be 0..255")
    if len(vals) > 512:
        raise SystemExit("max 512 slots per universe")
    return vals


# -----------------------------------------------------------------------------
# sACN (E1.31) pure Python
# -----------------------------------------------------------------------------

E131_PORT = 5568
ACN_PREAMBLE = b"\x00\x10"  # preamble size=0x0010
ACN_POSTAMBLE = b"\x00\x00"
ACN_PACKET_ID = b"ASC-E1.17\x00\x00\x00"  # 12 bytes
VECTOR_ROOT_E131_DATA = 0x00000004
VECTOR_E131_DATA_PACKET = 0x00000002
VECTOR_DMP_SET_PROPERTY = 0x02

# A stable CID per process; spec allows arbitrary UUID
_CID = uuid.uuid4().bytes  # 16 bytes

# Per-universe sequence counter
_SEQ: dict[int, int] = {}


def build_sacn_packet(
    universe: int, slots: list[int], *, source_name: str = "Claude", priority: int = 100
) -> bytes:
    if universe < 1 or universe > 63999:
        raise SystemExit("universe must be 1..63999")
    if priority < 1 or priority > 200:
        raise SystemExit("priority must be 1..200")
    data = bytes(slots)
    if len(data) < 512:
        data = data + b"\x00" * (512 - len(data))  # pad to 512
    # DMP (Device Management Protocol) Layer
    dmp_body = (
        struct.pack(">B", VECTOR_DMP_SET_PROPERTY)
        + b"\xa1"  # address_type_and_data_type
        + struct.pack(
            ">HHH", 0, 1, 1 + len(data)
        )  # first prop addr, prop addr inc, prop count
        + b"\x00"  # start code (0x00 = dimmer)
        + data
    )
    dmp_flen = 0x7000 | (10 + len(dmp_body))
    dmp_layer = struct.pack(">H", dmp_flen) + dmp_body

    # Framing Layer
    seq = (_SEQ.get(universe, 0) + 1) & 0xFF
    _SEQ[universe] = seq
    source_name_b = source_name.encode("utf-8")[:63]
    source_name_b += b"\x00" * (64 - len(source_name_b))
    framing_body = (
        struct.pack(">I", VECTOR_E131_DATA_PACKET)
        + source_name_b
        + bytes([priority])
        + struct.pack(">H", 0)  # sync address
        + bytes([seq, 0])  # seq, options
        + struct.pack(">H", universe)
    )
    framing_full = framing_body + dmp_layer
    framing_flen = 0x7000 | (2 + len(framing_full))
    framing_layer = struct.pack(">H", framing_flen) + framing_full

    # Root Layer
    root_body = struct.pack(">I", VECTOR_ROOT_E131_DATA) + _CID
    root_full = root_body + framing_layer
    root_flen = 0x7000 | (2 + len(root_full))
    root = (
        ACN_PREAMBLE
        + ACN_POSTAMBLE
        + ACN_PACKET_ID
        + struct.pack(">H", root_flen)
        + root_full
    )
    return root


def cmd_sacn_send(args: argparse.Namespace) -> int:
    slots = _parse_slots(args.slots)
    pkt = build_sacn_packet(
        args.universe, slots, source_name=args.source_name, priority=args.priority
    )
    group = f"239.255.{(args.universe >> 8) & 0xFF}.{args.universe & 0xFF}"
    if args.dry_run:
        print(f"multicast group: {group}:{E131_PORT}")
        print(f"packet hex: {pkt.hex()}")
        return 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
    if args.repeat:
        interval = 1.0 / max(1.0, args.rate)
        try:
            while True:
                # rebuild for fresh sequence number
                pkt = build_sacn_packet(
                    args.universe,
                    slots,
                    source_name=args.source_name,
                    priority=args.priority,
                )
                sock.sendto(pkt, (group, E131_PORT))
                if args.verbose:
                    sys.stderr.write(
                        f"[sacn -> {group}:{E131_PORT}] seq={_SEQ[args.universe]} len={len(pkt)}\n"
                    )
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
    else:
        if args.verbose:
            sys.stderr.write(f"[sacn -> {group}:{E131_PORT}] len={len(pkt)}\n")
        sock.sendto(pkt, (group, E131_PORT))
    sock.close()
    return 0


# -----------------------------------------------------------------------------
# Art-Net poll
# -----------------------------------------------------------------------------

ARTNET_PORT = 6454


def build_artpoll() -> bytes:
    # "Art-Net\0" + OpCode OpPoll (0x2000, little-endian) + ProtVerHi/Lo (0,14) + TalkToMe + Priority
    return b"Art-Net\x00" + struct.pack("<H", 0x2000) + bytes([0, 14, 0x06, 0x00])


def parse_artpollreply(data: bytes) -> dict:
    if not data.startswith(b"Art-Net\x00"):
        return {}
    op = struct.unpack_from("<H", data, 8)[0]
    if op != 0x2100:
        return {}
    ip = ".".join(str(b) for b in data[10:14])
    port = struct.unpack_from("<H", data, 14)[0]
    short_name = data[26:44].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    long_name = data[44:108].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return {"ip": ip, "port": port, "short_name": short_name, "long_name": long_name}


def cmd_artnet_poll(args: argparse.Namespace) -> int:
    pkt = build_artpoll()
    if args.dry_run:
        print(f"broadcast 255.255.255.255:{ARTNET_PORT}")
        print(f"packet hex: {pkt.hex()}")
        return 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", ARTNET_PORT))
    sock.settimeout(0.5)
    sock.sendto(pkt, ("255.255.255.255", ARTNET_PORT))
    if args.verbose:
        sys.stderr.write("[artnet-poll] broadcast sent\n")
    found: list[dict] = []
    end = time.time() + args.timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(1500)
        except socket.timeout:
            continue
        info = parse_artpollreply(data)
        if info:
            info["reply_from"] = f"{addr[0]}:{addr[1]}"
            found.append(info)
    sock.close()
    if args.format == "json":
        print(json.dumps(found, indent=2))
    else:
        for f in found:
            print(f"{f['ip']}:{f['port']}\t{f['short_name']}\t{f['long_name']}")
    return 0 if found else 1


# -----------------------------------------------------------------------------
# OLA wrappers
# -----------------------------------------------------------------------------


def _require_ola(cmd: str) -> str:
    path = _which(cmd)
    if not path:
        raise SystemExit(
            f"{cmd} not found. Install OLA (brew install ola) and run `olad` first."
        )
    return path


def cmd_list_devices(args: argparse.Namespace) -> int:
    out: dict = {"platform": platform.system()}
    if _which("ola_dev_info"):
        r = subprocess.run(["ola_dev_info"], capture_output=True, text=True)
        out["ola_dev_info"] = r.stdout.strip().splitlines()
    if _which("ola_uni_info"):
        r = subprocess.run(["ola_uni_info"], capture_output=True, text=True)
        out["ola_uni_info"] = r.stdout.strip().splitlines()
    # Serial fallback
    serial_paths: list[str] = []
    for d in ("/dev", "/dev/serial/by-id"):
        try:
            for name in os.listdir(d):
                if (
                    "usbserial" in name.lower()
                    or "ttyusb" in name.lower()
                    or "enttec" in name.lower()
                ):
                    serial_paths.append(os.path.join(d, name))
        except OSError:
            pass
    out["serial_devices"] = serial_paths
    print(json.dumps(out, indent=2))
    return 0


def cmd_send_dmx(args: argparse.Namespace) -> int:
    _require_ola("ola_streaming_client")
    slots = _parse_slots(args.slots)
    slot_str = ",".join(str(s) for s in slots)
    cmd = ["ola_streaming_client", "-u", str(args.universe), "-d", slot_str]
    if args.verbose or args.dry_run:
        sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
    if args.dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_record(args: argparse.Namespace) -> int:
    _require_ola("ola_recorder")
    cmd = ["ola_recorder", "-u", str(args.universe), "-w", args.out]
    if args.verbose or args.dry_run:
        sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
    if args.dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_stream(args: argparse.Namespace) -> int:
    _require_ola("ola_streaming_client")
    if args.dry_run:
        sys.stderr.write(f"[dry-run] would stream stdin to universe {args.universe}\n")
        return 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        slots = _parse_slots(line)
        slot_str = ",".join(str(s) for s in slots)
        subprocess.call(
            ["ola_streaming_client", "-u", str(args.universe), "-d", slot_str]
        )
    return 0


def cmd_rdm_scan(args: argparse.Namespace) -> int:
    _require_ola("ola_rdm_discover")
    cmd = ["ola_rdm_discover", "-u", str(args.universe)]
    if args.full:
        cmd.append("--full")
    if args.verbose or args.dry_run:
        sys.stderr.write(f"[exec] {' '.join(cmd)}\n")
    if args.dry_run:
        return 0
    return subprocess.call(cmd)


# -----------------------------------------------------------------------------
# Argparse
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DMX / Art-Net / sACN CLI.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-devices")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_list_devices)

    sp = sub.add_parser("send-dmx", help="OLA ola_streaming_client wrapper")
    sp.add_argument("--universe", type=int, required=True)
    sp.add_argument("--slots", required=True, help="comma-separated 0..255 values")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_send_dmx)

    sp = sub.add_parser("sacn-send", help="pure-Python sACN E1.31 multicast")
    sp.add_argument("--universe", type=int, required=True)
    sp.add_argument("--slots", required=True)
    sp.add_argument("--priority", type=int, default=100)
    sp.add_argument("--source-name", default="Claude")
    sp.add_argument("--repeat", action="store_true", help="loop send at --rate Hz")
    sp.add_argument("--rate", type=float, default=44.0)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_sacn_send)

    sp = sub.add_parser("artnet-poll")
    sp.add_argument("--timeout", type=float, default=2.0)
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_artnet_poll)

    sp = sub.add_parser("record", help="wrap ola_recorder")
    sp.add_argument("--universe", type=int, required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_record)

    sp = sub.add_parser("stream", help="stream stdin to OLA universe")
    sp.add_argument("--universe", type=int, required=True)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_stream)

    sp = sub.add_parser("rdm-scan", help="wrap ola_rdm_discover")
    sp.add_argument("--universe", type=int, required=True)
    sp.add_argument("--full", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_rdm_scan)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
