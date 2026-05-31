#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""oiio.py - OpenImageIO CLI wrapper (iinfo / iconvert / idiff / maketx / oiiotool / ...).

Shells out to the real OIIO binaries. Non-interactive. Every subcommand
supports --dry-run and --verbose and prints the exact command to stderr
before running.

Usage:
    oiio.py info FILE [--stats]
    oiio.py convert --in IN --out OUT [--compression TYPE]
    oiio.py diff A B [--out DIFF] [--fail F] [--warn W]
    oiio.py grep --pattern PAT FILE [FILE...]
    oiio.py maketx --in IN --out OUT [--hdri] [--unpremult] [--monochrome-detect]
                    [--filter NAME] [--colorconvert FROM TO] [--tile N]
    oiio.py color --in IN --out OUT --from SPACE --to SPACE [--ocio PATH]
    oiio.py resize --in IN --out OUT --size WxH [--filter NAME]
    oiio.py crop --in IN --out OUT --box x,y,w,h
    oiio.py rotate --in IN --out OUT --degrees DEG
    oiio.py tool -- <raw oiiotool args...>

Docs: https://openimageio.readthedocs.io/en/latest/
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
            f"error: {tool} not found on PATH. Install OpenImageIO tools.",
            file=sys.stderr,
        )
        sys.exit(127)


def run(cmd: list[str], dry_run: bool) -> int:
    echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_info(args: argparse.Namespace) -> int:
    require("iinfo")
    cmd = ["iinfo", "-v"]
    if args.stats:
        cmd.append("--stats")
    cmd.append(args.file)
    return run(cmd, args.dry_run)


def cmd_convert(args: argparse.Namespace) -> int:
    require("iconvert")
    cmd = ["iconvert"]
    if args.compression:
        cmd += ["--compression", args.compression]
    cmd += [getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_diff(args: argparse.Namespace) -> int:
    require("idiff")
    cmd = ["idiff"]
    if args.out:
        cmd += ["-o", args.out]
    if args.fail is not None:
        cmd += ["--fail", str(args.fail)]
    if args.warn is not None:
        cmd += ["--warn", str(args.warn)]
    cmd += [args.a, args.b]
    return run(cmd, args.dry_run)


def cmd_grep(args: argparse.Namespace) -> int:
    require("igrep")
    cmd = ["igrep", args.pattern] + args.files
    return run(cmd, args.dry_run)


def cmd_maketx(args: argparse.Namespace) -> int:
    require("maketx")
    cmd = ["maketx"]
    if args.hdri:
        cmd.append("--hdri")
    if args.unpremult:
        cmd.append("--unpremult")
    if args.monochrome_detect:
        cmd.append("--monochrome-detect")
    if args.filter:
        cmd += ["--filter", args.filter]
    if args.colorconvert:
        src, dst = args.colorconvert
        cmd += ["--colorconvert", src, dst]
    if args.tile:
        cmd += ["--tile", str(args.tile), str(args.tile)]
    cmd += ["-o", args.out, getattr(args, "in")]
    return run(cmd, args.dry_run)


def cmd_color(args: argparse.Namespace) -> int:
    require("oiiotool")
    env = os.environ.copy()
    if args.ocio:
        env["OCIO"] = args.ocio
    cmd = ["oiiotool"]
    cmd += [getattr(args, "in")]
    cmd += ["--colorconvert", getattr(args, "from"), args.to]
    cmd += ["-o", args.out]
    echo_cmd(cmd)
    if args.dry_run:
        return 0
    return subprocess.call(cmd, env=env)


def cmd_resize(args: argparse.Namespace) -> int:
    require("oiiotool")
    cmd = ["oiiotool", getattr(args, "in")]
    if args.filter:
        cmd += ["--resize:filter=" + args.filter, args.size]
    else:
        cmd += ["--resize", args.size]
    cmd += ["-o", args.out]
    return run(cmd, args.dry_run)


def cmd_crop(args: argparse.Namespace) -> int:
    require("oiiotool")
    x, y, w, h = args.box.split(",")
    spec = f"{w}x{h}+{x}+{y}"
    cmd = ["oiiotool", getattr(args, "in"), "--crop", spec, "-o", args.out]
    return run(cmd, args.dry_run)


def cmd_rotate(args: argparse.Namespace) -> int:
    require("oiiotool")
    cmd = [
        "oiiotool",
        getattr(args, "in"),
        "--rotate",
        str(args.degrees),
        "-o",
        args.out,
    ]
    return run(cmd, args.dry_run)


def cmd_tool(args: argparse.Namespace) -> int:
    require("oiiotool")
    cmd = ["oiiotool"] + args.extra
    return run(cmd, args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="OpenImageIO CLI wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c1 = sub.add_parser("info", help="dump metadata (iinfo -v [--stats])")
    c1.add_argument("file")
    c1.add_argument("--stats", action="store_true")
    c1.add_argument("--verbose", action="store_true")
    c1.add_argument("--dry-run", action="store_true")
    c1.set_defaults(fn=cmd_info)

    c2 = sub.add_parser("convert", help="convert format (iconvert)")
    c2.add_argument("--in", required=True, dest="in")
    c2.add_argument("--out", required=True)
    c2.add_argument("--compression", help="e.g. zip, dwaa, zips, piz")
    c2.add_argument("--verbose", action="store_true")
    c2.add_argument("--dry-run", action="store_true")
    c2.set_defaults(fn=cmd_convert)

    c3 = sub.add_parser("diff", help="perceptual diff (idiff)")
    c3.add_argument("a")
    c3.add_argument("b")
    c3.add_argument("--out", help="output difference image")
    c3.add_argument("--fail", type=float)
    c3.add_argument("--warn", type=float)
    c3.add_argument("--verbose", action="store_true")
    c3.add_argument("--dry-run", action="store_true")
    c3.set_defaults(fn=cmd_diff)

    c4 = sub.add_parser("grep", help="search metadata (igrep)")
    c4.add_argument("--pattern", required=True)
    c4.add_argument("files", nargs="+")
    c4.add_argument("--verbose", action="store_true")
    c4.add_argument("--dry-run", action="store_true")
    c4.set_defaults(fn=cmd_grep)

    c5 = sub.add_parser("maketx", help="build tiled MIP-map texture (maketx)")
    c5.add_argument("--in", required=True, dest="in")
    c5.add_argument("--out", required=True)
    c5.add_argument("--hdri", action="store_true")
    c5.add_argument("--unpremult", action="store_true")
    c5.add_argument("--monochrome-detect", action="store_true")
    c5.add_argument("--filter")
    c5.add_argument(
        "--colorconvert",
        nargs=2,
        metavar=("FROM", "TO"),
        help="bake color transform during maketx",
    )
    c5.add_argument("--tile", type=int, help="tile size (default 64)")
    c5.add_argument("--verbose", action="store_true")
    c5.add_argument("--dry-run", action="store_true")
    c5.set_defaults(fn=cmd_maketx)

    c6 = sub.add_parser("color", help="OCIO color transform (--colorconvert)")
    c6.add_argument("--in", required=True, dest="in")
    c6.add_argument("--out", required=True)
    c6.add_argument("--from", required=True, dest="from", help="source color space")
    c6.add_argument("--to", required=True, help="destination color space")
    c6.add_argument("--ocio", help="path to config.ocio (default: $OCIO)")
    c6.add_argument("--verbose", action="store_true")
    c6.add_argument("--dry-run", action="store_true")
    c6.set_defaults(fn=cmd_color)

    c7 = sub.add_parser("resize", help="oiiotool --resize")
    c7.add_argument("--in", required=True, dest="in")
    c7.add_argument("--out", required=True)
    c7.add_argument("--size", required=True, help="WxH")
    c7.add_argument("--filter")
    c7.add_argument("--verbose", action="store_true")
    c7.add_argument("--dry-run", action="store_true")
    c7.set_defaults(fn=cmd_resize)

    c8 = sub.add_parser("crop", help="oiiotool --crop")
    c8.add_argument("--in", required=True, dest="in")
    c8.add_argument("--out", required=True)
    c8.add_argument("--box", required=True, help="x,y,w,h")
    c8.add_argument("--verbose", action="store_true")
    c8.add_argument("--dry-run", action="store_true")
    c8.set_defaults(fn=cmd_crop)

    c9 = sub.add_parser("rotate", help="oiiotool --rotate")
    c9.add_argument("--in", required=True, dest="in")
    c9.add_argument("--out", required=True)
    c9.add_argument("--degrees", required=True, type=float)
    c9.add_argument("--verbose", action="store_true")
    c9.add_argument("--dry-run", action="store_true")
    c9.set_defaults(fn=cmd_rotate)

    c10 = sub.add_parser("tool", help="raw oiiotool passthrough")
    c10.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help='arbitrary oiiotool args, prefix with --, e.g. "-- in.exr --add 2 -o out.exr"',
    )
    c10.add_argument("--verbose", action="store_true")
    c10.add_argument("--dry-run", action="store_true")
    c10.set_defaults(fn=cmd_tool)

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
