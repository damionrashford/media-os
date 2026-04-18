#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""jackctl.py — wrap the JACK Audio Connection Kit CLIs.

Cross-platform wrapper around jackd, jack_lsp, jack_connect, jack_disconnect,
jack_cpu_load, jack_samplerate, jack_bufsize, jack_transport, jack_rec,
jack_iodelay, plus a simple passthrough to JackTrip.

Stdlib only. No interactive prompts. Prints every command to stderr before
running.

Usage:
    jackctl.py start [--backend alsa|coreaudio|portaudio|dummy] [--rate 48000]
                     [--period 256] [--nperiods 2] [--device <name>]
    jackctl.py stop
    jackctl.py status
    jackctl.py ports [--connections] [--types] [--input] [--output]
                     [--latency] [--properties]
    jackctl.py link <src> <dst>
    jackctl.py unlink <src> <dst>
    jackctl.py transport start|stop|locate <frames>
    jackctl.py latency [--capture-port <name>] [--playback-port <name>]
    jackctl.py record <file.wav> --channels c1 c2 ... [--duration N]
    jackctl.py jacktrip server [--channels 2]
    jackctl.py jacktrip client --host <ip> [--channels 2]

Every subcommand supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry: bool, verbose: bool) -> int:
    if verbose or dry:
        echo(cmd)
    if dry:
        return 0
    if shutil.which(cmd[0]) is None:
        print(
            f"error: '{cmd[0]}' not on PATH. Install JACK (Linux: jackd2; macOS: "
            "brew install jack; Windows: jackd installer).",
            file=sys.stderr,
        )
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


# ── subcommand handlers ────────────────────────────────────────────────────


def cmd_start(args: argparse.Namespace) -> int:
    # Choose a sensible default backend per OS.
    sysname = platform.system()
    default_backend = {
        "Linux": "alsa",
        "Darwin": "coreaudio",
        "Windows": "portaudio",
    }.get(sysname, "dummy")
    backend = args.backend or default_backend

    cli = ["jackd", "-R", "-d", backend]
    cli += ["-r", str(args.rate), "-p", str(args.period), "-n", str(args.nperiods)]
    if args.device:
        cli += ["-d", args.device]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_stop(args: argparse.Namespace) -> int:
    """Best-effort stop. jackd has no stop flag — SIGTERM does it.

    On JACK2 systems with D-Bus, prefer `jack_control exit`.
    """
    if shutil.which("jack_control") and not args.dry_run:
        rc = run(["jack_control", "exit"], dry=False, verbose=args.verbose)
        if rc == 0:
            return 0
    # Fallback: SIGTERM jackd processes owned by this user.
    return run(
        ["pkill", "-TERM", "-x", "jackd"], dry=args.dry_run, verbose=args.verbose
    )


def cmd_status(args: argparse.Namespace) -> int:
    # Three queries, printed back-to-back. jack_* tools exit non-zero if no server.
    for tool in ("jack_samplerate", "jack_bufsize", "jack_cpu_load"):
        rc = run([tool], dry=args.dry_run, verbose=args.verbose)
        if rc != 0 and not args.dry_run:
            print(
                f"note: {tool} exited {rc}; is a JACK server running?", file=sys.stderr
            )
    return 0


def cmd_ports(args: argparse.Namespace) -> int:
    cli = ["jack_lsp"]
    if args.connections:
        cli.append("-c")
    if args.types:
        cli.append("-t")
    if args.input:
        cli.append("-i")
    if args.output:
        cli.append("-o")
    if args.latency:
        cli.append("-l")
    if args.properties:
        cli.append("-p")
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_link(args: argparse.Namespace) -> int:
    return run(
        ["jack_connect", args.src, args.dst], dry=args.dry_run, verbose=args.verbose
    )


def cmd_unlink(args: argparse.Namespace) -> int:
    return run(
        ["jack_disconnect", args.src, args.dst], dry=args.dry_run, verbose=args.verbose
    )


def cmd_transport(args: argparse.Namespace) -> int:
    if args.action == "start":
        cli = ["jack_transport", "start"]
    elif args.action == "stop":
        cli = ["jack_transport", "stop"]
    elif args.action == "locate":
        if args.frames is None:
            print("error: 'locate' requires --frames", file=sys.stderr)
            return 2
        cli = ["jack_transport", "locate", str(args.frames)]
    else:
        print(f"unknown transport action: {args.action}", file=sys.stderr)
        return 2
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_latency(args: argparse.Namespace) -> int:
    # jack_iodelay runs a tone through a loopback and reports round-trip latency.
    # After it starts, the user must connect its ports to the capture/playback pair.
    cli = ["jack_iodelay"]
    if args.verbose or args.dry_run:
        echo(cli)
    if args.dry_run:
        return 0
    if shutil.which("jack_iodelay") is None:
        print("error: jack_iodelay not installed", file=sys.stderr)
        return 127
    # Auto-wire the loopback if both ports are specified.
    if args.capture_port and args.playback_port:
        print(
            "note: once jack_iodelay starts, run in another shell:\n"
            f"  jack_connect jack_delay:out {args.playback_port}\n"
            f"  jack_connect {args.capture_port} jack_delay:in",
            file=sys.stderr,
        )
    try:
        return subprocess.run(cli, check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_record(args: argparse.Namespace) -> int:
    cli = ["jack_rec", "-f", str(args.file)]
    cli += list(args.channels)
    if args.duration is not None:
        cli = ["timeout", str(args.duration)] + cli
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_jacktrip(args: argparse.Namespace) -> int:
    cli = ["jacktrip"]
    if args.role == "server":
        cli += ["-s"]
    elif args.role == "client":
        if not args.host:
            print("error: client mode needs --host", file=sys.stderr)
            return 2
        cli += ["-c", args.host]
    if args.channels is not None:
        cli += ["-n", str(args.channels)]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="JACK Audio Connection Kit (jackd + jack_*) wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the underlying command and exit 0",
        )
        sp.add_argument("--verbose", action="store_true")

    s = sub.add_parser("start", help="jackd with sensible per-OS defaults")
    s.add_argument("--backend", choices=["alsa", "coreaudio", "portaudio", "dummy"])
    s.add_argument("--rate", type=int, default=48000, help="Sample rate (Hz)")
    s.add_argument("--period", type=int, default=256, help="Period size (frames)")
    s.add_argument(
        "--nperiods",
        type=int,
        default=2,
        help="Number of periods (JACK1 default 2; USB often needs 3)",
    )
    s.add_argument("--device", help="Backend-specific device name (e.g. hw:0)")
    add_common(s)
    s.set_defaults(fn=cmd_start)

    s = sub.add_parser("stop", help="Stop the running JACK server")
    add_common(s)
    s.set_defaults(fn=cmd_stop)

    s = sub.add_parser(
        "status", help="Show jack_samplerate / jack_bufsize / jack_cpu_load"
    )
    add_common(s)
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("ports", help="jack_lsp — list ports and connections")
    s.add_argument("--connections", action="store_true", help="-c: show connections")
    s.add_argument("--types", action="store_true", help="-t: show port types")
    s.add_argument("--input", action="store_true", help="-i: input ports only")
    s.add_argument("--output", action="store_true", help="-o: output ports only")
    s.add_argument("--latency", action="store_true", help="-l: show latency")
    s.add_argument("--properties", action="store_true", help="-p: show properties")
    add_common(s)
    s.set_defaults(fn=cmd_ports)

    s = sub.add_parser("link", help="jack_connect <src> <dst>")
    s.add_argument("src", help="Source port (e.g. 'system:capture_1')")
    s.add_argument("dst", help="Destination port")
    add_common(s)
    s.set_defaults(fn=cmd_link)

    s = sub.add_parser("unlink", help="jack_disconnect <src> <dst>")
    s.add_argument("src")
    s.add_argument("dst")
    add_common(s)
    s.set_defaults(fn=cmd_unlink)

    s = sub.add_parser("transport", help="jack_transport start|stop|locate")
    s.add_argument("action", choices=["start", "stop", "locate"])
    s.add_argument(
        "--frames", type=int, help="Frame number for locate (required for locate)"
    )
    add_common(s)
    s.set_defaults(fn=cmd_transport)

    s = sub.add_parser("latency", help="jack_iodelay — measure round-trip latency")
    s.add_argument("--capture-port", help="Capture port (e.g. system:capture_1)")
    s.add_argument("--playback-port", help="Playback port (e.g. system:playback_1)")
    add_common(s)
    s.set_defaults(fn=cmd_latency)

    s = sub.add_parser("record", help="jack_rec — record to WAV from named ports")
    s.add_argument("file", type=Path, help="Output WAV file")
    s.add_argument(
        "--channels", nargs="+", required=True, help="Ports to record (space-separated)"
    )
    s.add_argument(
        "--duration", type=float, help="Stop after N seconds (wraps with `timeout`)"
    )
    add_common(s)
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser(
        "jacktrip", help="JackTrip — uncompressed multichannel UDP over internet"
    )
    s.add_argument("role", choices=["server", "client"])
    s.add_argument("--host", help="Peer IP/hostname (client mode)")
    s.add_argument("--channels", type=int, help="Channel count (-n)")
    add_common(s)
    s.set_defaults(fn=cmd_jacktrip)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
