#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""usd.py - Pixar USD CLI wrapper (usdcat / usdview / usdchecker / usdrecord / usdzip / ...).

Shells out to the real USD toolset binaries. Non-interactive. Every
subcommand supports --dry-run and --verbose and prints the exact command
to stderr before running.

Usage:
    usd.py cat --in IN --out OUT [--flatten]
    usd.py info FILE
    usd.py validate FILE [--arkit] [--strict]
    usd.py view FILE
    usd.py record --in IN --camera PRIM --out TEMPLATE --frames START-END [--imageWidth W] [--renderer R]
    usd.py zip --dir DIR --out OUT.usdz
    usd.py unzip --in IN.usdz --dest DIR
    usd.py diff A B
    usd.py resolve PATH
    usd.py stitch-clips --clips-dir DIR --topology FILE --out OUT [--clip-path PRIM]

Docs: https://openusd.org/release/
Tools index: https://openusd.org/release/toolset.html
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import zipfile


def echo_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)


def require(tool: str) -> None:
    if shutil.which(tool) is None:
        print(
            f"error: {tool} not found on PATH. Install OpenUSD runtime.",
            file=sys.stderr,
        )
        sys.exit(127)


def run(cmd: list[str], dry_run: bool) -> int:
    echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_cat(args: argparse.Namespace) -> int:
    require("usdcat")
    cmd = ["usdcat", getattr(args, "in")]
    if args.flatten:
        cmd.append("--flatten")
    cmd += ["-o", args.out]
    return run(cmd, args.dry_run)


def cmd_info(args: argparse.Namespace) -> int:
    require("usdtree")
    require("usdchecker")
    rc = run(["usdtree", args.file], args.dry_run)
    if rc != 0:
        return rc
    return run(["usdchecker", args.file], args.dry_run)


def cmd_validate(args: argparse.Namespace) -> int:
    require("usdchecker")
    cmd = ["usdchecker"]
    if args.arkit:
        cmd.append("--arkit")
    if args.strict:
        cmd.append("--strict")
    cmd.append(args.file)
    return run(cmd, args.dry_run)


def cmd_view(args: argparse.Namespace) -> int:
    require("usdview")
    return run(["usdview", args.file], args.dry_run)


def cmd_record(args: argparse.Namespace) -> int:
    require("usdrecord")
    if "-" in args.frames:
        a, b = args.frames.split("-", 1)
        frames = f"{a}:{b}"
    else:
        frames = args.frames
    cmd = ["usdrecord", "--camera", args.camera, "--frames", frames]
    if args.imageWidth:
        cmd += ["--imageWidth", str(args.imageWidth)]
    if args.renderer:
        cmd += ["--renderer", args.renderer]
    cmd += [getattr(args, "in"), args.out]
    return run(cmd, args.dry_run)


def cmd_zip(args: argparse.Namespace) -> int:
    require("usdzip")
    # `usdzip` expects: output.usdz inputlayer [extra-assets...]
    # Common recipe: locate the root layer as any .usd*/.usdc/.usda in dir.
    root = None
    for fn in sorted(os.listdir(args.dir)):
        if fn.endswith((".usd", ".usda", ".usdc")):
            root = os.path.join(args.dir, fn)
            break
    if root is None:
        print(
            f"error: no root .usd/.usda/.usdc layer found in {args.dir}",
            file=sys.stderr,
        )
        return 2
    cmd = ["usdzip", "-r", args.out, root]
    return run(cmd, args.dry_run)


def cmd_unzip(args: argparse.Namespace) -> int:
    # `.usdz` is a zero-compression zip. `unzip` works, or Python stdlib.
    os.makedirs(args.dest, exist_ok=True)
    echo_cmd(["python3", "-m", "zipfile", "-e", getattr(args, "in"), args.dest])
    if args.dry_run:
        return 0
    with zipfile.ZipFile(getattr(args, "in"), "r") as zf:
        zf.extractall(args.dest)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    require("usddiff")
    return run(["usddiff", args.a, args.b], args.dry_run)


def cmd_resolve(args: argparse.Namespace) -> int:
    require("usdresolve")
    return run(["usdresolve", args.path], args.dry_run)


def cmd_stitch_clips(args: argparse.Namespace) -> int:
    require("usdstitchclips")
    cmd = [
        "usdstitchclips",
        "--clipPath",
        args.clip_path,
        "--templatePath",
        os.path.join(args.clips_dir, "frame.####.usd"),
        "--out",
        args.out,
    ]
    if args.topology:
        cmd += ["--topologyLayer", args.topology]
    if args.start is not None:
        cmd += ["--startTimeCode", str(args.start)]
    if args.end is not None:
        cmd += ["--endTimeCode", str(args.end)]
    return run(cmd, args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pixar USD CLI wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c1 = sub.add_parser("cat", help="convert/print USD between formats")
    c1.add_argument("--in", required=True, dest="in")
    c1.add_argument("--out", required=True)
    c1.add_argument("--flatten", action="store_true")
    c1.add_argument("--verbose", action="store_true")
    c1.add_argument("--dry-run", action="store_true")
    c1.set_defaults(fn=cmd_cat)

    c2 = sub.add_parser("info", help="show stage hierarchy + run usdchecker")
    c2.add_argument("file")
    c2.add_argument("--verbose", action="store_true")
    c2.add_argument("--dry-run", action="store_true")
    c2.set_defaults(fn=cmd_info)

    c3 = sub.add_parser("validate", help="run usdchecker (optionally --arkit)")
    c3.add_argument("file")
    c3.add_argument("--arkit", action="store_true", help="Apple .usdz rules")
    c3.add_argument("--strict", action="store_true", default=True)
    c3.add_argument("--verbose", action="store_true")
    c3.add_argument("--dry-run", action="store_true")
    c3.set_defaults(fn=cmd_validate)

    c4 = sub.add_parser("view", help="launch usdview GUI (requires Qt)")
    c4.add_argument("file")
    c4.add_argument("--verbose", action="store_true")
    c4.add_argument("--dry-run", action="store_true")
    c4.set_defaults(fn=cmd_view)

    c5 = sub.add_parser("record", help="offline Hydra render to image sequence")
    c5.add_argument("--in", required=True, dest="in")
    c5.add_argument("--camera", required=True, help="camera prim path")
    c5.add_argument(
        "--out", required=True, help='output template, e.g. "frame.####.png"'
    )
    c5.add_argument(
        "--frames", required=True, help="frame range: START-END or single int"
    )
    c5.add_argument("--imageWidth", type=int)
    c5.add_argument("--renderer", help="Storm, Embree, Arnold, Karma, RenderMan")
    c5.add_argument("--verbose", action="store_true")
    c5.add_argument("--dry-run", action="store_true")
    c5.set_defaults(fn=cmd_record)

    c6 = sub.add_parser("zip", help="pack a folder into .usdz")
    c6.add_argument("--dir", required=True, help="source directory")
    c6.add_argument("--out", required=True, help="output .usdz")
    c6.add_argument("--verbose", action="store_true")
    c6.add_argument("--dry-run", action="store_true")
    c6.set_defaults(fn=cmd_zip)

    c7 = sub.add_parser("unzip", help="extract .usdz package")
    c7.add_argument("--in", required=True, dest="in")
    c7.add_argument("--dest", required=True)
    c7.add_argument("--verbose", action="store_true")
    c7.add_argument("--dry-run", action="store_true")
    c7.set_defaults(fn=cmd_unzip)

    c8 = sub.add_parser("diff", help="structural diff between two stages")
    c8.add_argument("a")
    c8.add_argument("b")
    c8.add_argument("--verbose", action="store_true")
    c8.add_argument("--dry-run", action="store_true")
    c8.set_defaults(fn=cmd_diff)

    c9 = sub.add_parser("resolve", help="resolve an asset path")
    c9.add_argument("path")
    c9.add_argument("--verbose", action="store_true")
    c9.add_argument("--dry-run", action="store_true")
    c9.set_defaults(fn=cmd_resolve)

    c10 = sub.add_parser("stitch-clips", help="assemble a value-clips manifest")
    c10.add_argument("--clips-dir", required=True)
    c10.add_argument("--topology")
    c10.add_argument("--out", required=True)
    c10.add_argument("--clip-path", default="/Set")
    c10.add_argument("--start", type=int)
    c10.add_argument("--end", type=int)
    c10.add_argument("--verbose", action="store_true")
    c10.add_argument("--dry-run", action="store_true")
    c10.set_defaults(fn=cmd_stitch_clips)

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
