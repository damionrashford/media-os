#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
advproto.py — advanced ffmpeg streaming protocols helper.

Subcommands:
    check         Report librist / libzmq / libshout availability in ffmpeg.
    rist-send     Encode + push over RIST as a caller.
    rist-listen   Receive/capture from a RIST listener URL to a file.
    zmq-serve     Start ffmpeg with a zmq-enabled filter graph (runtime-controllable).
    zmq-send      Send a command to a running ffmpeg zmq filter server (requires pyzmq).
    rtp-fec       Transmit RTP-MPEGTS with prompeg forward-error-correction.
    icecast       Push audio to an Icecast2 mountpoint.
    multicast     Stream MPEG-TS to a UDP multicast group.

All commands accept --dry-run (print the command without running) and --verbose.
Stdlib only; non-interactive.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[advproto] {msg}", file=sys.stderr)


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        print("Error: ffmpeg not found in PATH.", file=sys.stderr)
        sys.exit(127)
    return path


def _run(cmd: List[str], dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if dry_run:
        print(printable)
        return 0
    _log(f"exec: {printable}", verbose)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------
def cmd_check(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-buildconf"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except Exception as e:
        print(f"Error running ffmpeg -buildconf: {e}", file=sys.stderr)
        return 1

    libs = {"librist": False, "libzmq": False, "libshout": False}
    for line in out.splitlines():
        for lib in libs:
            if f"--enable-{lib}" in line:
                libs[lib] = True

    try:
        protos = subprocess.run(
            [ffmpeg, "-hide_banner", "-protocols"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.lower()
    except Exception:
        protos = ""

    print("ffmpeg advanced-protocol support:")
    print(f"  librist (RIST):            {'YES' if libs['librist'] else 'no'}")
    print(f"  libzmq  (ZMQ filter):      {'YES' if libs['libzmq']  else 'no'}")
    print(f"  libshout (Icecast):        {'YES' if libs['libshout'] else 'no'}")
    print()
    print("protocol list check:")
    for name in ("rist", "zmq", "icecast", "rtp", "udp"):
        print(f"  {name:<10s}: {'present' if name in protos else 'MISSING'}")
    return 0


# --------------------------------------------------------------------------
# rist-send
# --------------------------------------------------------------------------
def cmd_rist_send(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    url = args.url
    # If user passed a bare host:port style, leave as-is.
    if args.buffer and "buffer_size=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}buffer_size={args.buffer}"

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-re",
        "-i",
        args.input,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-b:v",
        args.bitrate,
        "-maxrate",
        args.bitrate,
        "-bufsize",
        args.bitrate,
        "-x264-params",
        "nal-hrd=cbr:force-cfr=1",
        "-g",
        "60",
        "-keyint_min",
        "60",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "48000",
        "-f",
        "mpegts",
        url,
    ]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# rist-listen
# --------------------------------------------------------------------------
def cmd_rist_listen(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-i",
        args.url,
        "-c",
        "copy",
        args.output,
    ]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# zmq-serve
# --------------------------------------------------------------------------
def _escape_zmq_bind(bind: str) -> str:
    # Inside -filter_complex, ':' and '/' inside option values must be escaped.
    return bind.replace(":", r"\:").replace("/", r"\/")


def cmd_zmq_serve(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    esc_bind = _escape_zmq_bind(args.bind_addr)
    # Build: [0:v] <user-filter> , zmq=bind_address=... [out]
    chain = f"[0:v]{args.filter_expr},zmq=bind_address={esc_bind}[out]"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-re",
        "-i",
        args.input,
        "-filter_complex",
        chain,
        "-map",
        "[out]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        args.output,
    ]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# zmq-send
# --------------------------------------------------------------------------
def cmd_zmq_send(args: argparse.Namespace) -> int:
    try:
        import zmq  # type: ignore
    except ImportError:
        print(
            "Error: pyzmq is not installed. Install with: pip install pyzmq",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(f"[dry-run] zmq REQ {args.addr} <- {args.command!r}")
        return 0

    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    try:
        sock.connect(args.addr)
        _log(f"connect {args.addr}", args.verbose)
        sock.send_string(args.command)
        reply = sock.recv_string()
        print(reply)
        # Success responses start with "0 " per ffmpeg's zmq filter.
        return 0 if reply.startswith("0 ") or reply.strip() == "0" else 2
    finally:
        sock.close(linger=0)
        ctx.term()


# --------------------------------------------------------------------------
# rtp-fec
# --------------------------------------------------------------------------
def cmd_rtp_fec(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    fec = f"prompeg=l={args.l}:d={args.d}"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-re",
        "-i",
        args.input,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-b:v",
        args.bitrate,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "rtp_mpegts",
        "-fec",
        fec,
        args.dst_url,
    ]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# icecast
# --------------------------------------------------------------------------
def cmd_icecast(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    # Guess codec + content-type from URL or default to MP3.
    codec = args.codec or "libmp3lame"
    fmt = args.format or "mp3"
    content_type = args.content_type or (
        "audio/mpeg" if fmt == "mp3" else "audio/ogg" if fmt == "ogg" else "audio/mpeg"
    )
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-re",
        "-i",
        args.input,
        "-c:a",
        codec,
        "-b:a",
        args.bitrate,
        "-content_type",
        content_type,
    ]
    if args.ice_name:
        cmd += ["-ice_name", args.ice_name]
    if args.ice_description:
        cmd += ["-ice_description", args.ice_description]
    if args.ice_genre:
        cmd += ["-ice_genre", args.ice_genre]
    if args.ice_public:
        cmd += ["-ice_public", "1"]
    cmd += ["-f", fmt, args.url]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# multicast
# --------------------------------------------------------------------------
def cmd_multicast(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    url = f"udp://{args.group}:{args.port}?pkt_size={args.pkt_size}&ttl={args.ttl}"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-re",
        "-i",
        args.input,
        "-c",
        "copy",
        "-f",
        "mpegts",
        url,
    ]
    return _run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="advproto.py",
        description="Advanced ffmpeg streaming protocols helper (RIST / ZMQ / prompeg / Icecast / multicast).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print the command instead of running it"
    )
    p.add_argument("--verbose", action="store_true", help="Print progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="Report librist/libzmq/libshout support.")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("rist-send", help="Encode + push over RIST (caller).")
    sp.add_argument("--input", "-i", required=True, help="Input file/URL")
    sp.add_argument(
        "--url",
        "-u",
        required=True,
        help='RIST URL, e.g. "rist://host:1234?buffer_size=1000&cname=s1"',
    )
    sp.add_argument("--bitrate", default="5M", help="Video bitrate (default: 5M)")
    sp.add_argument(
        "--buffer",
        type=int,
        default=None,
        help="Inject buffer_size=N (ms) if not already in URL",
    )
    sp.set_defaults(func=cmd_rist_send)

    sp = sub.add_parser("rist-listen", help="Receive from a RIST listener URL.")
    sp.add_argument(
        "--url",
        "-u",
        required=True,
        help='RIST listen URL, e.g. "rist://@:1234?buffer_size=500"',
    )
    sp.add_argument("--output", "-o", required=True, help="Output file (e.g. out.ts)")
    sp.set_defaults(func=cmd_rist_listen)

    sp = sub.add_parser(
        "zmq-serve", help="Start ffmpeg with a zmq-controllable filter graph."
    )
    sp.add_argument("--input", "-i", required=True, help="Input file/URL")
    sp.add_argument("--output", "-o", required=True, help="Output file/URL")
    sp.add_argument(
        "--bind-addr",
        default="tcp://127.0.0.1:5555",
        help='ZMQ bind address (default: "tcp://127.0.0.1:5555")',
    )
    sp.add_argument(
        "--filter-expr",
        required=True,
        help='Video filter chain, e.g. "drawtext=text=hello:x=10:y=10"',
    )
    sp.set_defaults(func=cmd_zmq_serve)

    sp = sub.add_parser(
        "zmq-send", help="Send a runtime command to a ffmpeg zmq server."
    )
    sp.add_argument(
        "--addr",
        default="tcp://localhost:5555",
        help='ZMQ REQ socket address (default: "tcp://localhost:5555")',
    )
    sp.add_argument(
        "--command",
        "-c",
        required=True,
        help='Command: "FILTER_INSTANCE PARAM VALUE" '
        '(e.g. "Parsed_drawtext_0 text world")',
    )
    sp.set_defaults(func=cmd_zmq_send)

    sp = sub.add_parser("rtp-fec", help="Transmit RTP-MPEGTS with prompeg FEC.")
    sp.add_argument("--input", "-i", required=True, help="Input file/URL")
    sp.add_argument(
        "--dst-url", required=True, help='Destination, e.g. "rtp://192.168.1.10:5000"'
    )
    sp.add_argument("--l", type=int, default=5, help="FEC columns (default: 5)")
    sp.add_argument("--d", type=int, default=5, help="FEC rows (default: 5)")
    sp.add_argument("--bitrate", default="4M", help="Video bitrate (default: 4M)")
    sp.set_defaults(func=cmd_rtp_fec)

    sp = sub.add_parser("icecast", help="Push audio to Icecast2.")
    sp.add_argument("--input", "-i", required=True, help="Input audio file/URL")
    sp.add_argument(
        "--url",
        "-u",
        required=True,
        help='Icecast URL "icecast://user:pass@host:port/mount"',
    )
    sp.add_argument("--bitrate", default="128k", help="Audio bitrate (default: 128k)")
    sp.add_argument("--codec", default=None, help="Audio codec (default: libmp3lame)")
    sp.add_argument(
        "--format",
        default=None,
        dest="format",
        help="Output muxer (default: mp3; use 'ogg' for Vorbis)",
    )
    sp.add_argument(
        "--content-type",
        default=None,
        help="Override HTTP content-type "
        "(default inferred: audio/mpeg for mp3, audio/ogg for ogg)",
    )
    sp.add_argument("--ice-name", default=None)
    sp.add_argument("--ice-description", default=None)
    sp.add_argument("--ice-genre", default=None)
    sp.add_argument(
        "--ice-public", action="store_true", help="List stream in public directory"
    )
    sp.set_defaults(func=cmd_icecast)

    sp = sub.add_parser("multicast", help="Stream MPEG-TS over UDP multicast.")
    sp.add_argument("--input", "-i", required=True, help="Input file/URL")
    sp.add_argument("--group", required=True, help="Multicast group (e.g. 239.0.0.1)")
    sp.add_argument("--port", type=int, required=True, help="UDP port")
    sp.add_argument(
        "--pkt-size",
        type=int,
        default=1316,
        help="MPEG-TS pkt_size, must be multiple of 188 (default: 1316)",
    )
    sp.add_argument(
        "--ttl", type=int, default=1, help="Multicast TTL (default: 1 = link-local)"
    )
    sp.set_defaults(func=cmd_multicast)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Basic sanity: pkt_size must be a multiple of 188
    if args.cmd == "multicast" and args.pkt_size % 188 != 0:
        print(
            f"Error: --pkt-size {args.pkt_size} is not a multiple of 188.",
            file=sys.stderr,
        )
        return 2

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
