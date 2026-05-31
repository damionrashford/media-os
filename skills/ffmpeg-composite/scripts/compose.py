#!/usr/bin/env python3
"""compose.py — build & run ffmpeg filter graphs for masking / compositing / plane ops.

Subcommands:
  mask-merge     3-input maskedmerge (source0 + source1 + mask)
  alpha-merge    2-input alphamerge (video + grayscale matte → yuva)
  alpha-extract  1-input alphaextract (rgba/yuva → grayscale mask)
  displace       3-input displace (base + xmap + ymap)
  planes         single-input plane surgery (extract / swap Y<->U / swap U<->V)
  blend          2-input blend with Photoshop-style modes
  rgbashift      chromatic aberration / per-channel shift

All subcommands accept --dry-run (print only) and --verbose (show full ffmpeg command).
Stdlib only. No interactive prompts.
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

ALPHA_CAPABLE_ENCODERS = {
    ".mov": ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"],
    ".mkv": ["-c:v", "ffv1", "-level", "3", "-pix_fmt", "yuva420p"],
    ".webm": ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30"],
    ".png": ["-c:v", "png"],
    ".tiff": ["-c:v", "tiff"],
}


def alpha_output_args(output: str) -> list[str]:
    """Pick encoder + pix_fmt that preserve alpha, based on output extension."""
    ext = Path(output).suffix.lower()
    if ext in ALPHA_CAPABLE_ENCODERS:
        return ALPHA_CAPABLE_ENCODERS[ext]
    # Fallback: mov + ProRes 4444
    sys.stderr.write(
        f"[compose] warning: extension {ext!r} may not support alpha; "
        "defaulting to ProRes 4444 (.mov recommended).\n"
    )
    return ALPHA_CAPABLE_ENCODERS[".mov"]


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    if dry_run or verbose:
        print(pretty)
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def cmd_mask_merge(a: argparse.Namespace) -> int:
    graph = (
        "[2:v]format=gray[m];"
        "[0:v]format=yuva420p[a];"
        "[1:v]format=yuva420p[b];"
        "[a][b][m]maskedmerge[out]"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.source0,
        "-i",
        a.source1,
        "-i",
        a.mask,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_alpha_merge(a: argparse.Namespace) -> int:
    graph = "[1:v]format=gray[m];[0:v][m]alphamerge[out]"
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.video,
        "-i",
        a.mask,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        *alpha_output_args(a.output),
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_alpha_extract(a: argparse.Namespace) -> int:
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.input,
        "-vf",
        "alphaextract,format=gray",
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_displace(a: argparse.Namespace) -> int:
    graph = (
        "[1:v]format=gray[x];"
        "[2:v]format=gray[y];"
        f"[0:v][x][y]displace=edge={a.edge}[out]"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.base,
        "-i",
        a.xmap,
        "-i",
        a.ymap,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_planes(a: argparse.Namespace) -> int:
    if a.op == "extract-y":
        vf = "format=yuv420p,extractplanes=y"
    elif a.op == "extract-u":
        vf = "format=yuv444p,extractplanes=u"
    elif a.op == "extract-v":
        vf = "format=yuv444p,extractplanes=v"
    elif a.op == "swap-uv":
        vf = "format=yuv444p,shuffleplanes=0:2:1:3"
    elif a.op == "swap-yu":
        vf = "format=yuv444p,shuffleplanes=1:0:2:3"
    else:
        raise SystemExit(f"unknown op {a.op!r}")
    cmd = [FFMPEG, "-y", "-i", a.input, "-vf", vf, a.output]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_blend(a: argparse.Namespace) -> int:
    graph = (
        "[0:v]format=gbrp[a];"
        "[1:v]format=gbrp[b];"
        f"[a][b]blend=all_mode={a.mode}:all_opacity={a.opacity},format=yuv420p[out]"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.source0,
        "-i",
        a.source1,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def cmd_rgbashift(a: argparse.Namespace) -> int:
    parts = []
    for flag, val in (
        ("rh", a.rh),
        ("rv", a.rv),
        ("gh", a.gh),
        ("gv", a.gv),
        ("bh", a.bh),
        ("bv", a.bv),
    ):
        if val != 0:
            parts.append(f"{flag}={val}")
    shift = ":".join(parts) if parts else "rh=0"
    vf = f"format=gbrp,rgbashift={shift},format=yuv420p"
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        a.input,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        a.output,
    ]
    return run(cmd, dry_run=a.dry_run, verbose=a.verbose)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compose.py",
        description="ffmpeg compositing, masking, and channel-ops helper.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print command but do not run"
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="print the full ffmpeg command before running",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    common.add_argument("--verbose", action="store_true", help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="subcmd", required=True)

    mm = sub.add_parser(
        "mask-merge",
        parents=[common],
        help="maskedmerge: 3-input compositing through a grayscale mask",
    )
    mm.add_argument("--source0", required=True, help="source kept where mask is white")
    mm.add_argument("--source1", required=True, help="source kept where mask is black")
    mm.add_argument("--mask", required=True, help="grayscale mask video/image")
    mm.add_argument("--output", required=True)
    mm.set_defaults(func=cmd_mask_merge)

    am = sub.add_parser(
        "alpha-merge",
        parents=[common],
        help="alphamerge: attach a grayscale matte as alpha onto a video",
    )
    am.add_argument("--video", required=True)
    am.add_argument("--mask", required=True)
    am.add_argument(
        "--output",
        required=True,
        help="output path (.mov/.mkv/.webm/.png picked for alpha)",
    )
    am.set_defaults(func=cmd_alpha_merge)

    ae = sub.add_parser(
        "alpha-extract",
        parents=[common],
        help="alphaextract: pull mask out of rgba/yuva input",
    )
    ae.add_argument("--input", required=True)
    ae.add_argument(
        "--output", required=True, help="grayscale output (.png, .mkv, etc.)"
    )
    ae.set_defaults(func=cmd_alpha_extract)

    dp = sub.add_parser(
        "displace",
        parents=[common],
        help="displace: warp base by xmap + ymap displacement",
    )
    dp.add_argument("--base", required=True)
    dp.add_argument("--xmap", required=True)
    dp.add_argument("--ymap", required=True)
    dp.add_argument("--output", required=True)
    dp.add_argument(
        "--edge", choices=["blank", "smear", "wrap", "mirror"], default="smear"
    )
    dp.set_defaults(func=cmd_displace)

    pl = sub.add_parser(
        "planes",
        parents=[common],
        help="plane surgery via extractplanes / shuffleplanes",
    )
    pl.add_argument("--input", required=True)
    pl.add_argument("--output", required=True)
    pl.add_argument(
        "--op",
        required=True,
        choices=["extract-y", "extract-u", "extract-v", "swap-uv", "swap-yu"],
        help="operation to perform on planes",
    )
    pl.set_defaults(func=cmd_planes)

    bl = sub.add_parser(
        "blend",
        parents=[common],
        help="spatial 2-input blend with Photoshop-style modes",
    )
    bl.add_argument("--source0", required=True)
    bl.add_argument("--source1", required=True)
    bl.add_argument("--output", required=True)
    bl.add_argument(
        "--mode",
        required=True,
        choices=[
            "screen",
            "multiply",
            "overlay",
            "difference",
            "addition",
            "darken",
            "lighten",
            "softlight",
            "hardlight",
            "dodge",
            "burn",
        ],
    )
    bl.add_argument(
        "--opacity", type=float, default=1.0, help="all_opacity 0.0–1.0 (default 1.0)"
    )
    bl.set_defaults(func=cmd_blend)

    rs = sub.add_parser(
        "rgbashift",
        parents=[common],
        help="per-channel pixel shift (chromatic aberration look)",
    )
    rs.add_argument("--input", required=True)
    rs.add_argument("--output", required=True)
    rs.add_argument("--rh", type=int, default=0, help="red horizontal shift (px)")
    rs.add_argument("--rv", type=int, default=0, help="red vertical shift (px)")
    rs.add_argument("--gh", type=int, default=0, help="green horizontal shift (px)")
    rs.add_argument("--gv", type=int, default=0, help="green vertical shift (px)")
    rs.add_argument("--bh", type=int, default=0, help="blue horizontal shift (px)")
    rs.add_argument("--bv", type=int, default=0, help="blue vertical shift (px)")
    rs.set_defaults(func=cmd_rgbashift)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # Two-pass: parse once to capture any global flags given before the
    # subcommand, then parse again; finally OR both so either position works.
    known, _ = parser.parse_known_args(argv)
    global_dry = bool(getattr(known, "dry_run", False))
    global_verbose = bool(getattr(known, "verbose", False))
    args = parser.parse_args(argv)
    args.dry_run = args.dry_run or global_dry
    args.verbose = args.verbose or global_verbose
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
