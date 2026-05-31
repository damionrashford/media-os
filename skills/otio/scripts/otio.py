#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""otio.py — Wrapper around the OpenTimelineIO CLIs.

Dispatches to otioconvert / otiocat / otiostat / otiotool / otiopluginfo /
otioview. Non-interactive; prints every real command to stderr before running
it. Stdlib-only Python 3.

Usage:
    otio.py convert --input SRC --output DST [--preset ALIAS]
    otio.py cat --input A [--input B ...] [--output OUT]
    otio.py stat --input FILE
    otio.py tool --input SRC --output DST -- [otiotool args ...]
    otio.py plugins
    otio.py view --input FILE

Global flags: --dry-run, --verbose.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PRESETS = {
    "fcp7-to-fcpx": ("fcp_xml", "fcpx_xml"),
    "fcpx-to-fcp7": ("fcpx_xml", "fcp_xml"),
    "edl-to-otio": ("cmx_3600", "otio_json"),
    "otio-to-edl": ("otio_json", "cmx_3600"),
    "aaf-to-otio": ("aaf_adapter", "otio_json"),
    "otio-to-fcpx": ("otio_json", "fcpx_xml"),
    "otio-to-fcp7": ("otio_json", "fcp_xml"),
}


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry_run: bool) -> int:
    echo(cmd)
    if dry_run:
        return 0
    if shutil.which(cmd[0]) is None:
        print(
            f"error: {cmd[0]} not on PATH. Install OTIO: pip install OpenTimelineIO-Plugins",
            file=sys.stderr,
        )
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_convert(args: argparse.Namespace) -> int:
    cmd = ["otioconvert", "-i", str(args.input), "-o", str(args.output)]
    if args.preset:
        if args.preset not in PRESETS:
            print(
                f"error: unknown preset {args.preset!r}; choose from {list(PRESETS)}",
                file=sys.stderr,
            )
            return 2
        src_adapter, dst_adapter = PRESETS[args.preset]
        cmd += ["--input-adapter", src_adapter, "--output-adapter", dst_adapter]
    if args.extra:
        cmd += args.extra
    return run(cmd, dry_run=args.dry_run)


def cmd_cat(args: argparse.Namespace) -> int:
    cmd = ["otiocat"] + [str(p) for p in args.input]
    if args.output:
        cmd += ["-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_stat(args: argparse.Namespace) -> int:
    cmd = ["otiostat", str(args.input)]
    return run(cmd, dry_run=args.dry_run)


def cmd_tool(args: argparse.Namespace) -> int:
    cmd = ["otiotool", "-i", str(args.input), "-o", str(args.output)]
    if args.extra:
        cmd += args.extra
    return run(cmd, dry_run=args.dry_run)


def cmd_plugins(args: argparse.Namespace) -> int:
    cmd = ["otiopluginfo"]
    return run(cmd, dry_run=args.dry_run)


def cmd_view(args: argparse.Namespace) -> int:
    cmd = ["otioview", str(args.input)]
    return run(cmd, dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Wrapper around OpenTimelineIO CLIs. Non-interactive; prints "
            "every real command to stderr before executing."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("convert", parents=[parent], help="Convert between formats")
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.add_argument(
        "--preset", help=f"adapter-pair shortcut; choose from {list(PRESETS)}"
    )
    s.add_argument(
        "extra", nargs=argparse.REMAINDER, help="extra args for otioconvert (after --)"
    )
    s.set_defaults(fn=cmd_convert)

    s = sub.add_parser("cat", parents=[parent], help="Print or concatenate OTIO files")
    s.add_argument("--input", action="append", required=True, type=Path)
    s.add_argument("--output", type=Path, help="optional file to write (else stdout)")
    s.set_defaults(fn=cmd_cat)

    s = sub.add_parser("stat", parents=[parent], help="Print timeline stats")
    s.add_argument("--input", required=True, type=Path)
    s.set_defaults(fn=cmd_stat)

    s = sub.add_parser("tool", parents=[parent], help="Run otiotool transforms")
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="forward-through args for otiotool (after --)",
    )
    s.set_defaults(fn=cmd_tool)

    s = sub.add_parser("plugins", parents=[parent], help="List installed adapters")
    s.set_defaults(fn=cmd_plugins)

    s = sub.add_parser("view", parents=[parent], help="Launch otioview Qt GUI")
    s.add_argument("--input", required=True, type=Path)
    s.set_defaults(fn=cmd_view)

    return p


def main() -> int:
    args = build_parser().parse_args()
    # Strip leading `--` from REMAINDER if present.
    if hasattr(args, "extra") and args.extra and args.extra[0] == "--":
        args.extra = args.extra[1:]
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
