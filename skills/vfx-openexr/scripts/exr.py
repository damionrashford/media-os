#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""exr.py - OpenEXR CLI wrapper (exrheader / exrinfo / exrmaketiled / ...).

Shells out to the OpenEXR tools. Non-interactive. Every subcommand
supports --dry-run and --verbose and prints the exact command to stderr
before running.

Usage:
    exr.py header FILE
    exr.py info FILE
    exr.py tiled --in IN --out OUT [--tilesize N] [--rip]
    exr.py envmap --in IN --out OUT --type latlong|cube
    exr.py preview --in IN --out OUT [--size N]
    exr.py multipart pack --out OUT IN1 IN2 [IN3 ...]
    exr.py multipart unpack --in IN --dest DIR
    exr.py multiview pack --out OUT --left L.exr --right R.exr
    exr.py multiview unpack --in IN --dest DIR
    exr.py stdattr get FILE
    exr.py stdattr set --in IN --out OUT --attr NAME --value VAL
    exr.py check FILE
    exr.py to-aces IN OUT
    exr.py manifest FILE
    exr.py metrics FILE

Docs: https://openexr.com/en/latest/tools.html
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys


def echo_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)


def require(tool: str) -> None:
    if shutil.which(tool) is None:
        print(
            f"error: {tool} not found on PATH. Install OpenEXR tools.", file=sys.stderr
        )
        sys.exit(127)


def run(cmd: list[str], dry_run: bool) -> int:
    echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_header(args: argparse.Namespace) -> int:
    require("exrheader")
    return run(["exrheader", args.file], args.dry_run)


def cmd_info(args: argparse.Namespace) -> int:
    require("exrinfo")
    return run(["exrinfo", args.file], args.dry_run)


def cmd_tiled(args: argparse.Namespace) -> int:
    require("exrmaketiled")
    cmd = ["exrmaketiled"]
    if args.tilesize:
        cmd += ["-t", str(args.tilesize), str(args.tilesize)]
    if args.rip:
        cmd.append("-r")
    cmd += [getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_envmap(args: argparse.Namespace) -> int:
    require("exrenvmap")
    type_arg = args.type.lower()
    # exrenvmap <input-options> <output-options> in out
    # Input type is auto-detected from input latlong vs cube aspect; the
    # -latlong / -cube flags select the OUTPUT layout.
    if type_arg == "cube":
        flag = "-cube"
    elif type_arg == "latlong":
        flag = "-latlong"
    else:
        print(
            f"error: --type must be cube or latlong, got {args.type!r}", file=sys.stderr
        )
        return 2
    cmd = ["exrenvmap", flag, getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_preview(args: argparse.Namespace) -> int:
    require("exrmakepreview")
    cmd = ["exrmakepreview"]
    if args.size:
        cmd += ["-w", str(args.size)]
    cmd += [getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_multipart(args: argparse.Namespace) -> int:
    require("exrmultipart")
    if args.op == "pack":
        cmd = ["exrmultipart", "-combine", "-i"] + args.inputs + ["-o", args.out]
    else:
        os.makedirs(args.dest, exist_ok=True)
        cmd = ["exrmultipart", "-separate", "-i", getattr(args, "in"), "-o", args.dest]
    return run(cmd, args.dry_run)


def cmd_multiview(args: argparse.Namespace) -> int:
    require("exrmultiview")
    if args.op == "pack":
        cmd = [
            "exrmultiview",
            "-combine",
            "-i",
            args.left,
            args.right,
            "-v",
            "left",
            "right",
            "-o",
            args.out,
        ]
    else:
        os.makedirs(args.dest, exist_ok=True)
        cmd = ["exrmultiview", "-separate", "-i", getattr(args, "in"), "-o", args.dest]
    return run(cmd, args.dry_run)


def cmd_stdattr(args: argparse.Namespace) -> int:
    require("exrstdattr")
    if args.op == "get":
        return run(["exrstdattr", args.file], args.dry_run)
    # set: exrstdattr -<attr> <value> in out
    cmd = ["exrstdattr", f"-{args.attr}", args.value, getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_check(args: argparse.Namespace) -> int:
    require("exrcheck")
    return run(["exrcheck", args.file], args.dry_run)


def cmd_to_aces(args: argparse.Namespace) -> int:
    require("exr2aces")
    return run(["exr2aces", args.inpath, args.outpath], args.dry_run)


def cmd_manifest(args: argparse.Namespace) -> int:
    require("exrmanifest")
    return run(["exrmanifest", args.file], args.dry_run)


def cmd_metrics(args: argparse.Namespace) -> int:
    require("exrmetrics")
    return run(["exrmetrics", args.file], args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="OpenEXR CLI wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c1 = sub.add_parser("header", help="full header dump (exrheader)")
    c1.add_argument("file")
    c1.add_argument("--verbose", action="store_true")
    c1.add_argument("--dry-run", action="store_true")
    c1.set_defaults(fn=cmd_header)

    c2 = sub.add_parser("info", help="concise info (exrinfo)")
    c2.add_argument("file")
    c2.add_argument("--verbose", action="store_true")
    c2.add_argument("--dry-run", action="store_true")
    c2.set_defaults(fn=cmd_info)

    c3 = sub.add_parser("tiled", help="scanline to tiled (exrmaketiled)")
    c3.add_argument("--in", required=True, dest="in")
    c3.add_argument("--out", required=True)
    c3.add_argument("--tilesize", type=int, default=64)
    c3.add_argument("--rip", action="store_true", help="RIP-map instead of MIP-map")
    c3.add_argument("--verbose", action="store_true")
    c3.add_argument("--dry-run", action="store_true")
    c3.set_defaults(fn=cmd_tiled)

    c4 = sub.add_parser("envmap", help="latlong <-> cube (exrenvmap)")
    c4.add_argument("--in", required=True, dest="in")
    c4.add_argument("--out", required=True)
    c4.add_argument("--type", required=True, choices=["latlong", "cube"])
    c4.add_argument("--verbose", action="store_true")
    c4.add_argument("--dry-run", action="store_true")
    c4.set_defaults(fn=cmd_envmap)

    c5 = sub.add_parser("preview", help="embed preview thumbnail (exrmakepreview)")
    c5.add_argument("--in", required=True, dest="in")
    c5.add_argument("--out", required=True)
    c5.add_argument("--size", type=int, default=200)
    c5.add_argument("--verbose", action="store_true")
    c5.add_argument("--dry-run", action="store_true")
    c5.set_defaults(fn=cmd_preview)

    c6 = sub.add_parser("multipart", help="multi-part pack/unpack (exrmultipart)")
    c6.add_argument("op", choices=["pack", "unpack"])
    c6.add_argument("--out", help="(pack) output file")
    c6.add_argument("--in", dest="in", help="(unpack) input file")
    c6.add_argument("--dest", help="(unpack) destination directory")
    c6.add_argument("inputs", nargs="*", help="(pack) input EXRs in desired part order")
    c6.add_argument("--verbose", action="store_true")
    c6.add_argument("--dry-run", action="store_true")
    c6.set_defaults(fn=cmd_multipart)

    c7 = sub.add_parser("multiview", help="stereo multi-view (exrmultiview)")
    c7.add_argument("op", choices=["pack", "unpack"])
    c7.add_argument("--out")
    c7.add_argument("--left")
    c7.add_argument("--right")
    c7.add_argument("--in", dest="in")
    c7.add_argument("--dest")
    c7.add_argument("--verbose", action="store_true")
    c7.add_argument("--dry-run", action="store_true")
    c7.set_defaults(fn=cmd_multiview)

    c8 = sub.add_parser("stdattr", help="read/write standard attributes (exrstdattr)")
    c8.add_argument("op", choices=["get", "set"])
    c8.add_argument("file", nargs="?", help="(get) input file")
    c8.add_argument("--in", dest="in", help="(set) input file")
    c8.add_argument("--out", help="(set) output file")
    c8.add_argument("--attr", help="(set) attribute name, e.g. owner")
    c8.add_argument("--value", help="(set) attribute value")
    c8.add_argument("--verbose", action="store_true")
    c8.add_argument("--dry-run", action="store_true")
    c8.set_defaults(fn=cmd_stdattr)

    c9 = sub.add_parser("check", help="validate file (exrcheck)")
    c9.add_argument("file")
    c9.add_argument("--verbose", action="store_true")
    c9.add_argument("--dry-run", action="store_true")
    c9.set_defaults(fn=cmd_check)

    c10 = sub.add_parser("to-aces", help="re-tag for ACES 2065-1 (exr2aces)")
    c10.add_argument("inpath")
    c10.add_argument("outpath")
    c10.add_argument("--verbose", action="store_true")
    c10.add_argument("--dry-run", action="store_true")
    c10.set_defaults(fn=cmd_to_aces)

    c11 = sub.add_parser("manifest", help="read deep-ID manifest (exrmanifest)")
    c11.add_argument("file")
    c11.add_argument("--verbose", action="store_true")
    c11.add_argument("--dry-run", action="store_true")
    c11.set_defaults(fn=cmd_manifest)

    c12 = sub.add_parser("metrics", help="compression metrics (exrmetrics)")
    c12.add_argument("file")
    c12.add_argument("--verbose", action="store_true")
    c12.add_argument("--dry-run", action="store_true")
    c12.set_defaults(fn=cmd_metrics)

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
