#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""tether.py - gphoto2 wrapper for DSLR / mirrorless tethering.

Every subcommand shells out to `gphoto2` (or `libgphoto2`'s CLI surface).
Non-interactive. Every subcommand supports --dry-run and --verbose and
prints the exact gphoto2 command to stderr before running.

Usage:
    tether.py detect
    tether.py shoot [--download] [--count N] [--template TPL]
    tether.py preview [--fps N] [--duration SEC] [--dest DIR]
    tether.py preview --once --out FILE
    tether.py movie --duration SEC
    tether.py bulk-download --dest DIR [--delete]
    tether.py config-list
    tether.py config-get --key /main/.../X
    tether.py config-set --key /main/.../X --value V
    tether.py timelapse --interval SEC --count N --dest DIR [--template TPL]
    tether.py ptpip --host HOST [--port 15740] -- SUBCOMMAND [ARGS...]

Cameras: Canon, Nikon, Sony, Fujifilm, Panasonic, Olympus, Pentax, Leica, Hasselblad.
Live support list: http://gphoto.org/proj/libgphoto2/support.php
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time

DEFAULT_TEMPLATE = "%Y%m%d-%H%M%S-%n.%C"
PTPIP_DEFAULT_PORT = 15740


def echo_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)


def require_gphoto2() -> None:
    if shutil.which("gphoto2") is None:
        print(
            "error: gphoto2 not found on PATH. Install libgphoto2 + gphoto2 CLI.",
            file=sys.stderr,
        )
        sys.exit(127)


def run(cmd: list[str], dry_run: bool, cwd: str | None = None) -> int:
    echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.call(cmd, cwd=cwd)


def with_port(cmd: list[str], port: str | None) -> list[str]:
    """Prepend --port PORT if a ptpip port was set (by ptpip subcommand)."""
    if port:
        return [cmd[0], "--port", port] + cmd[1:]
    return cmd


def cmd_detect(args: argparse.Namespace) -> int:
    require_gphoto2()
    cmd = with_port(["gphoto2", "--auto-detect"], args.port)
    return run(cmd, args.dry_run)


def cmd_shoot(args: argparse.Namespace) -> int:
    require_gphoto2()
    cap = "--capture-image-and-download" if args.download else "--capture-image"
    template = args.template or DEFAULT_TEMPLATE
    rc = 0
    count = max(1, args.count)
    for i in range(count):
        cmd = with_port(["gphoto2", cap, "--filename", template], args.port)
        if args.force_overwrite:
            cmd.append("--force-overwrite")
        rc = run(cmd, args.dry_run)
        if rc != 0:
            return rc
        if args.interval and i + 1 < count:
            if args.verbose:
                print(f"[sleep] {args.interval}s", file=sys.stderr)
            if not args.dry_run:
                time.sleep(args.interval)
    return rc


def cmd_preview(args: argparse.Namespace) -> int:
    require_gphoto2()
    if args.once:
        out = args.out or "preview.jpg"
        cmd = with_port(
            ["gphoto2", "--capture-preview", "--filename", out, "--force-overwrite"],
            args.port,
        )
        return run(cmd, args.dry_run)
    # Loop mode
    dest = args.dest or "."
    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)
    fps = max(0.1, args.fps)
    period = 1.0 / fps
    deadline = time.time() + args.duration if args.duration else None
    i = 0
    while True:
        i += 1
        out = os.path.join(dest, f"preview-{i:06d}.jpg")
        cmd = with_port(
            ["gphoto2", "--capture-preview", "--filename", out, "--force-overwrite"],
            args.port,
        )
        rc = run(cmd, args.dry_run)
        if rc != 0:
            return rc
        if args.dry_run:
            # One iteration in dry-run mode.
            return 0
        if deadline and time.time() >= deadline:
            return 0
        if args.count and i >= args.count:
            return 0
        time.sleep(period)


def cmd_movie(args: argparse.Namespace) -> int:
    require_gphoto2()
    cmd = with_port(["gphoto2", f"--capture-movie={int(args.duration)}s"], args.port)
    return run(cmd, args.dry_run)


def cmd_bulk_download(args: argparse.Namespace) -> int:
    require_gphoto2()
    dest = args.dest
    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)
    cmd = with_port(["gphoto2", "--get-all-files", "--skip-existing"], args.port)
    if args.delete:
        cmd.append("--delete-all-files")
    return run(cmd, args.dry_run, cwd=dest)


def cmd_config_list(args: argparse.Namespace) -> int:
    require_gphoto2()
    cmd = with_port(["gphoto2", "--list-config"], args.port)
    return run(cmd, args.dry_run)


def cmd_config_get(args: argparse.Namespace) -> int:
    require_gphoto2()
    cmd = with_port(["gphoto2", "--get-config", args.key], args.port)
    return run(cmd, args.dry_run)


def cmd_config_set(args: argparse.Namespace) -> int:
    require_gphoto2()
    cmd = with_port(
        ["gphoto2", "--set-config", f"{args.key}={args.value}"],
        args.port,
    )
    return run(cmd, args.dry_run)


def cmd_timelapse(args: argparse.Namespace) -> int:
    require_gphoto2()
    if not args.dry_run:
        os.makedirs(args.dest, exist_ok=True)
    template = args.template or DEFAULT_TEMPLATE
    path_template = os.path.join(args.dest, template)
    rc = 0
    for i in range(args.count):
        cmd = with_port(
            ["gphoto2", "--capture-image-and-download", "--filename", path_template],
            args.port,
        )
        if args.force_overwrite:
            cmd.append("--force-overwrite")
        rc = run(cmd, args.dry_run)
        if rc != 0:
            return rc
        if i + 1 < args.count:
            if args.verbose:
                print(f"[sleep] {args.interval}s", file=sys.stderr)
            if not args.dry_run:
                time.sleep(args.interval)
    return rc


def cmd_ptpip(args: argparse.Namespace) -> int:
    """Set the ptpip port on args and dispatch the nested subcommand.

    Usage shape: `tether.py ptpip --host H [--port P] -- SUB [ARGS...]`
    """
    port_str = f"ptpip:{args.host}"
    if args.port_num and args.port_num != PTPIP_DEFAULT_PORT:
        port_str += f":{args.port_num}"
    # Re-parse the trailing command against the main parser, but inject
    # --port so the nested subcommand uses it.
    nested = list(args.nested)
    if not nested:
        print(
            "error: ptpip requires a trailing subcommand, e.g. `-- shoot --download`",
            file=sys.stderr,
        )
        return 2
    root = build_parser()
    # Inject --port as a global before the subcommand
    argv = ["--port", port_str] + nested
    new_args = root.parse_args(argv)
    return new_args.fn(new_args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="gphoto2 tethering wrapper (USB + PTP/IP).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--port",
        help="gphoto2 --port value (e.g. ptpip:192.168.1.100); normally set by `ptpip` subcommand",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("detect", help="list attached cameras (--auto-detect)")
    p1.add_argument("--verbose", action="store_true")
    p1.add_argument("--dry-run", action="store_true")
    p1.set_defaults(fn=cmd_detect)

    p2 = sub.add_parser("shoot", help="capture one or more photos")
    p2.add_argument("--download", action="store_true", help="pull file off camera")
    p2.add_argument("--count", type=int, default=1, help="number of shots")
    p2.add_argument("--interval", type=float, default=0, help="seconds between shots")
    p2.add_argument("--template", help="filename template (see gphoto2 --filename)")
    p2.add_argument("--force-overwrite", action="store_true")
    p2.add_argument("--verbose", action="store_true")
    p2.add_argument("--dry-run", action="store_true")
    p2.set_defaults(fn=cmd_shoot)

    p3 = sub.add_parser("preview", help="live-view preview (one frame or loop)")
    p3.add_argument("--once", action="store_true", help="grab a single preview frame")
    p3.add_argument("--out", help="(with --once) output filename")
    p3.add_argument(
        "--fps", type=float, default=2.0, help="loop frame rate (default 2)"
    )
    p3.add_argument("--duration", type=float, help="stop after N seconds")
    p3.add_argument("--count", type=int, help="stop after N frames")
    p3.add_argument("--dest", help="directory for loop output (default: cwd)")
    p3.add_argument("--verbose", action="store_true")
    p3.add_argument("--dry-run", action="store_true")
    p3.set_defaults(fn=cmd_preview)

    p4 = sub.add_parser("movie", help="record movie for N seconds")
    p4.add_argument("--duration", type=float, required=True)
    p4.add_argument("--verbose", action="store_true")
    p4.add_argument("--dry-run", action="store_true")
    p4.set_defaults(fn=cmd_movie)

    p5 = sub.add_parser("bulk-download", help="pull every file off the card")
    p5.add_argument("--dest", required=True, help="destination directory")
    p5.add_argument("--delete", action="store_true", help="delete after download")
    p5.add_argument("--verbose", action="store_true")
    p5.add_argument("--dry-run", action="store_true")
    p5.set_defaults(fn=cmd_bulk_download)

    p6 = sub.add_parser("config-list", help="list all config keys (--list-config)")
    p6.add_argument("--verbose", action="store_true")
    p6.add_argument("--dry-run", action="store_true")
    p6.set_defaults(fn=cmd_config_list)

    p7 = sub.add_parser("config-get", help="get one config key's value")
    p7.add_argument("--key", required=True)
    p7.add_argument("--verbose", action="store_true")
    p7.add_argument("--dry-run", action="store_true")
    p7.set_defaults(fn=cmd_config_get)

    p8 = sub.add_parser("config-set", help="set one config key")
    p8.add_argument("--key", required=True)
    p8.add_argument("--value", required=True)
    p8.add_argument("--verbose", action="store_true")
    p8.add_argument("--dry-run", action="store_true")
    p8.set_defaults(fn=cmd_config_set)

    p9 = sub.add_parser("timelapse", help="shoot at regular intervals")
    p9.add_argument(
        "--interval", type=float, required=True, help="seconds between shots"
    )
    p9.add_argument("--count", type=int, required=True, help="number of shots")
    p9.add_argument("--dest", required=True, help="output directory")
    p9.add_argument("--template", default=DEFAULT_TEMPLATE)
    p9.add_argument("--force-overwrite", action="store_true")
    p9.add_argument("--verbose", action="store_true")
    p9.add_argument("--dry-run", action="store_true")
    p9.set_defaults(fn=cmd_timelapse)

    p10 = sub.add_parser("ptpip", help="run a subcommand over PTP/IP (Wi-Fi)")
    p10.add_argument("--host", required=True, help="camera IP address")
    p10.add_argument(
        "--port-num",
        dest="port_num",
        type=int,
        default=PTPIP_DEFAULT_PORT,
        help=f"PTP/IP port (default {PTPIP_DEFAULT_PORT})",
    )
    p10.add_argument(
        "nested",
        nargs=argparse.REMAINDER,
        help="nested subcommand + args (prefix with --)",
    )
    p10.add_argument("--verbose", action="store_true")
    p10.add_argument("--dry-run", action="store_true")
    p10.set_defaults(fn=cmd_ptpip)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
