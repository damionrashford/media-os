#!/usr/bin/env python3
"""
grade.py - thin wrapper for ffmpeg color grading & LUT application.

Subcommands:
  lut                      Apply a 3D LUT from .cube / .3dl.
  haldclut                 Apply a Hald CLUT PNG.
  balance                  Apply colorbalance (shadows/mids/highlights R,G,B).
  selective                Apply selectivecolor to a named color (C,M,Y,K).
  match-bt601-to-bt709     Legacy BT.601 -> BT.709 matrix conversion.

Options common to all subcommands:
  --dry-run   Print the ffmpeg command instead of executing it.
  --verbose   Echo the command before running.

Stdlib only. Non-interactive.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

VALID_INTERP = {"nearest", "trilinear", "tetrahedral", "pyramid", "prism"}
VALID_SELECTIVE_COLORS = {
    "reds",
    "yellows",
    "greens",
    "cyans",
    "blues",
    "magentas",
    "whites",
    "neutrals",
    "blacks",
}


def die(msg: str, code: int = 2) -> None:
    print(f"grade.py: error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_triplet(s: str, name: str) -> tuple[float, float, float]:
    parts = s.split(",")
    if len(parts) != 3:
        die(f"--{name} expects 3 comma-separated floats, got {s!r}")
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        die(f"--{name} contains a non-float: {s!r}")


def parse_quad(s: str, name: str) -> tuple[float, float, float, float]:
    parts = s.split(",")
    if len(parts) != 4:
        die(f"--{name} expects 4 comma-separated floats C,M,Y,K, got {s!r}")
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        die(f"--{name} contains a non-float: {s!r}")


def validate_cube(path: str) -> None:
    p = Path(path)
    if not p.exists():
        die(f"LUT file not found: {path}")
    if not p.is_file():
        die(f"LUT path is not a file: {path}")
    suffix = p.suffix.lower()
    if suffix not in {".cube", ".3dl"}:
        die(f"LUT extension must be .cube or .3dl, got {suffix!r}")


def validate_input(path: str) -> None:
    if not Path(path).exists():
        die(f"input file not found: {path}")


def build_base_cmd(input_path: str, vf: str, output_path: str) -> List[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-c:a",
        "copy",
        output_path,
    ]


def build_filter_complex_cmd(
    input_path: str, second_input: str, filter_complex: str, output_path: str
) -> List[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-i",
        second_input,
        "-filter_complex",
        filter_complex,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-c:a",
        "copy",
        output_path,
    ]


def run(cmd: Sequence[str], dry_run: bool, verbose: bool) -> int:
    quoted = " ".join(shlex.quote(str(a)) for a in cmd)
    if verbose or dry_run:
        print(quoted)
    if dry_run:
        return 0
    return subprocess.call(list(cmd))


# ---------- subcommand handlers ----------


def cmd_lut(args: argparse.Namespace) -> int:
    validate_input(args.input)
    validate_cube(args.lut)
    if args.interp not in VALID_INTERP:
        die(f"--interp must be one of {sorted(VALID_INTERP)}")
    # Quote the file path inside the filter graph.
    vf = f"lut3d=file='{args.lut}':interp={args.interp}"
    cmd = build_base_cmd(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_haldclut(args: argparse.Namespace) -> int:
    validate_input(args.input)
    if not Path(args.clut).exists():
        die(f"CLUT PNG not found: {args.clut}")
    fc = "[0:v][1:v]haldclut=interp=tetrahedral"
    cmd = build_filter_complex_cmd(args.input, args.clut, fc, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_balance(args: argparse.Namespace) -> int:
    validate_input(args.input)
    rs, gs, bs = parse_triplet(args.shadows, "shadows")
    rm, gm, bm = parse_triplet(args.mids, "mids")
    rh, gh, bh = parse_triplet(args.highlights, "highlights")
    vf = (
        f"colorbalance="
        f"rs={rs}:gs={gs}:bs={bs}:"
        f"rm={rm}:gm={gm}:bm={bm}:"
        f"rh={rh}:gh={gh}:bh={bh}"
    )
    cmd = build_base_cmd(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_selective(args: argparse.Namespace) -> int:
    validate_input(args.input)
    if args.color not in VALID_SELECTIVE_COLORS:
        die(f"--color must be one of {sorted(VALID_SELECTIVE_COLORS)}")
    c, m, y, k = parse_quad(args.adjust, "adjust")
    # selectivecolor uses SPACE-separated 4-tuples, not commas.
    vf = f"selectivecolor={args.color}={c} {m} {y} {k}"
    cmd = build_base_cmd(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_match_bt601_to_bt709(args: argparse.Namespace) -> int:
    validate_input(args.input)
    vf = "colormatrix=bt601:bt709"
    cmd = build_base_cmd(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


# ---------- argparse plumbing ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="grade.py",
        description="ffmpeg color grading & LUT application wrapper.",
    )
    p.add_argument("--dry-run", action="store_true", help="print command; do not run")
    p.add_argument("--verbose", action="store_true", help="echo command before running")

    sub = p.add_subparsers(dest="subcmd", required=True)

    sp = sub.add_parser("lut", help="apply 3D LUT from .cube/.3dl")
    sp.add_argument("--input", required=True)
    sp.add_argument("--lut", required=True, help="path to .cube or .3dl")
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--interp",
        default="tetrahedral",
        help="nearest|trilinear|tetrahedral|pyramid|prism",
    )
    sp.set_defaults(func=cmd_lut)

    sp = sub.add_parser("haldclut", help="apply Hald CLUT PNG")
    sp.add_argument("--input", required=True)
    sp.add_argument("--clut", required=True, help="path to graded Hald CLUT PNG")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_haldclut)

    sp = sub.add_parser("balance", help="colorbalance shadows/mids/highlights")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--shadows", required=True, help="R,G,B (e.g. 0.15,0.05,-0.1)")
    sp.add_argument("--mids", required=True, help="R,G,B")
    sp.add_argument("--highlights", required=True, help="R,G,B")
    sp.set_defaults(func=cmd_balance)

    sp = sub.add_parser("selective", help="selectivecolor on a named color")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--color", required=True, help=f"one of {sorted(VALID_SELECTIVE_COLORS)}"
    )
    sp.add_argument(
        "--adjust",
        required=True,
        help="C,M,Y,K as comma-separated floats (e.g. 0,0,-0.5,0)",
    )
    sp.set_defaults(func=cmd_selective)

    sp = sub.add_parser(
        "match-bt601-to-bt709", help="legacy BT.601 -> BT.709 matrix conversion"
    )
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_match_bt601_to_bt709)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
