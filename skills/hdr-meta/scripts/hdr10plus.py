#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""hdr10plus.py — Wrapper around hdr10plus_tool for HDR10+ metadata authoring.

Non-interactive. Prints every real `hdr10plus_tool` / `x265` / `ffmpeg` /
`mkvmerge` / `MP4Box` command to stderr before running. Stdlib-only Python 3.

Usage:
    hdr10plus.py extract --input HEVC/MKV --output JSON
    hdr10plus.py inject --input HEVC --json JSON --output HEVC
    hdr10plus.py remove --input HEVC --output HEVC
    hdr10plus.py editor --input JSON --config EDIT.json --output JSON
    hdr10plus.py plot --input JSON --output PNG
    hdr10plus.py x265-encode --input Y4M --metadata JSON --output HEVC
                            [--crf N] [--preset NAME] [--extra "…"]

Global flags: --dry-run, --verbose.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry_run: bool) -> int:
    echo(cmd)
    if dry_run:
        return 0
    if shutil.which(cmd[0]) is None:
        print(f"error: {cmd[0]} not on PATH", file=sys.stderr)
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_extract(args: argparse.Namespace) -> int:
    cmd = ["hdr10plus_tool", "extract", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_inject(args: argparse.Namespace) -> int:
    cmd = [
        "hdr10plus_tool",
        "inject",
        "-i",
        str(args.input),
        "-j",
        str(args.json),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_remove(args: argparse.Namespace) -> int:
    cmd = ["hdr10plus_tool", "remove", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_editor(args: argparse.Namespace) -> int:
    cmd = [
        "hdr10plus_tool",
        "editor",
        "-i",
        str(args.input),
        "-j",
        str(args.config),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_plot(args: argparse.Namespace) -> int:
    cmd = ["hdr10plus_tool", "plot", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_x265_encode(args: argparse.Namespace) -> int:
    """Emit an `x265` command that bakes HDR10+ at encode time via --dhdr10-info.

    By default this is dry-run-like: we print the command. With --run, we execute.
    """
    cmd = ["x265"]
    if str(args.input).endswith(".y4m"):
        cmd.append("--y4m")
    cmd += ["--input", str(args.input)]
    cmd += ["--crf", str(args.crf)]
    cmd += ["--preset", args.preset]
    cmd += [
        "--colorprim",
        "bt2020",
        "--transfer",
        "smpte2084",
        "--colormatrix",
        "bt2020nc",
        "--hdr10",
        "--hdr10-opt",
        "--repeat-headers",
    ]
    if args.metadata:
        cmd += ["--dhdr10-info", str(args.metadata)]
    if args.max_cll:
        cmd += ["--max-cll", args.max_cll]
    if args.master_display:
        cmd += ["--master-display", args.master_display]
    if args.extra:
        cmd += shlex.split(args.extra)
    cmd += ["--output", str(args.output)]

    echo(cmd)
    if not args.run:
        print(
            "\n(pass --run to execute; default is dry-run for x265-encode "
            "so you can review the command first)",
            file=sys.stderr,
        )
        return 0
    if shutil.which("x265") is None:
        print("error: x265 not on PATH", file=sys.stderr)
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Wrapper around hdr10plus_tool. Non-interactive; prints every "
            "real command to stderr before running."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_extract)

    s = sub.add_parser("inject", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--json", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_inject)

    s = sub.add_parser("remove", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_remove)

    s = sub.add_parser("editor", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--config", required=True, type=Path, help="edit JSON")
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_editor)

    s = sub.add_parser("plot", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_plot)

    s = sub.add_parser(
        "x265-encode",
        parents=[parent],
        help="Emit an x265 --dhdr10-info command (dry-run by default)",
    )
    s.add_argument("--input", required=True, type=Path, help="Y4M or YUV input")
    s.add_argument("--metadata", type=Path, default=None, help="HDR10+ metadata JSON")
    s.add_argument("--output", required=True, type=Path)
    s.add_argument("--crf", type=float, default=18.0)
    s.add_argument("--preset", default="slow")
    s.add_argument("--max-cll", help="e.g. '1000,400'")
    s.add_argument(
        "--master-display",
        help="e.g. 'G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)'",
    )
    s.add_argument("--extra", help="extra x265 args (quoted)")
    s.add_argument(
        "--run", action="store_true", help="actually run x265 (default: dry-run)"
    )
    s.set_defaults(fn=cmd_x265_encode)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
