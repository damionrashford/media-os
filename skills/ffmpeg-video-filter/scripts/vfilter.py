#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
vfilter.py — run common ffmpeg -vf / -filter_complex operations as presets.

Presets:
  scale-720p             scale=-2:720
  scale-1080p-letterbox  fit 1920x1080 with black bars
  watermark              overlay a PNG logo bottom-right (needs --watermark)
  deinterlace            yadif=1
  drawtext-timecode      running SMPTE timecode top-left (needs --text optional)
  hstack                 two videos side by side (needs --inputs "a.mp4,b.mp4")
  vstack                 two videos stacked vertically (needs --inputs ...)
  2x-speed               setpts=0.5*PTS (video only, audio dropped)

Custom:
  --custom --filter-string "scale=-2:720,eq=saturation=1.2"

Usage:
  uv run scripts/vfilter.py --preset scale-720p --input in.mp4 --output out.mp4
  uv run scripts/vfilter.py --preset watermark --input in.mp4 --watermark logo.png --output out.mp4
  uv run scripts/vfilter.py --preset hstack --inputs a.mp4,b.mp4 --output side.mp4
  uv run scripts/vfilter.py --custom --filter-string "scale=-2:720" --input in.mp4 --output out.mp4

Flags:
  --dry-run    print the ffmpeg command without running it
  --verbose    print progress to stderr
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


PRESETS = (
    "scale-720p",
    "scale-1080p-letterbox",
    "watermark",
    "deinterlace",
    "drawtext-timecode",
    "hstack",
    "vstack",
    "2x-speed",
)


# Default font paths per platform. drawtext needs an explicit fontfile on most
# static ffmpeg builds. The macOS path is the safest default for this machine.
DEFAULT_FONTFILE = "/System/Library/Fonts/Supplemental/Arial.ttf"


def _eprint(*a, **kw) -> None:
    print(*a, file=sys.stderr, **kw)


def _must_exist(path: str, label: str) -> None:
    if not Path(path).exists():
        _eprint(f"Error: {label} not found: {path}")
        sys.exit(1)


def build_command(args: argparse.Namespace) -> list[str]:
    """Assemble the ffmpeg argv for the selected preset or custom chain."""

    if args.custom:
        if not args.filter_string:
            _eprint("Error: --custom requires --filter-string")
            sys.exit(2)
        _must_exist(args.input, "input")
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            args.filter_string,
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            args.output,
        ]

    preset = args.preset
    if preset is None:
        _eprint("Error: pass --preset {...} or --custom --filter-string ...")
        sys.exit(2)

    if preset == "scale-720p":
        _must_exist(args.input, "input")
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            "scale=-2:720:flags=lanczos",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            args.output,
        ]

    if preset == "scale-1080p-letterbox":
        _must_exist(args.input, "input")
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            args.output,
        ]

    if preset == "watermark":
        if not args.watermark:
            _eprint("Error: --preset watermark requires --watermark PATH")
            sys.exit(2)
        _must_exist(args.input, "input")
        _must_exist(args.watermark, "watermark")
        fc = (
            "[1:v]format=yuva420p,scale=200:-1[wm];" "[0:v][wm]overlay=W-w-20:H-h-20[v]"
        )
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-i",
            args.watermark,
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            args.output,
        ]

    if preset == "deinterlace":
        _must_exist(args.input, "input")
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            "yadif=1,setsar=1",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "slow",
            "-c:a",
            "copy",
            args.output,
        ]

    if preset == "drawtext-timecode":
        _must_exist(args.input, "input")
        fontfile = args.fontfile or DEFAULT_FONTFILE
        _must_exist(fontfile, "fontfile")
        # Colons inside the timecode value must be escaped so the filter parser
        # does not treat them as option separators.
        vf = (
            f"drawtext=fontfile={fontfile}:"
            "timecode='00\\:00\\:00\\:00':rate=25:"
            "fontsize=32:fontcolor=white:"
            "box=1:boxcolor=black@0.5:boxborderw=8:"
            "x=20:y=20"
        )
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            args.output,
        ]

    if preset in ("hstack", "vstack"):
        if not args.inputs:
            _eprint(f"Error: --preset {preset} requires --inputs a.mp4,b.mp4")
            sys.exit(2)
        paths = [p.strip() for p in args.inputs.split(",") if p.strip()]
        if len(paths) < 2:
            _eprint(f"Error: --preset {preset} needs at least 2 inputs")
            sys.exit(2)
        for p in paths:
            _must_exist(p, "input")
        n = len(paths)
        # Normalize to equal height (hstack) or equal width (vstack) first.
        if preset == "hstack":
            chains = [f"[{i}:v]scale=-2:720[v{i}]" for i in range(n)]
        else:
            chains = [f"[{i}:v]scale=1280:-2[v{i}]" for i in range(n)]
        join = "".join(f"[v{i}]" for i in range(n)) + f"{preset}=inputs={n}[v]"
        fc = ";".join(chains + [join])
        cmd = ["ffmpeg", "-y"]
        for p in paths:
            cmd += ["-i", p]
        cmd += [
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-an",
            args.output,
        ]
        return cmd

    if preset == "2x-speed":
        _must_exist(args.input, "input")
        return [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-vf",
            "setpts=0.5*PTS",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-an",
            args.output,
        ]

    _eprint(f"Error: unknown preset: {preset}")
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ffmpeg video-filter presets or a custom -vf chain.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--preset", choices=PRESETS, help="Named preset to run.")
    parser.add_argument(
        "--custom",
        action="store_true",
        help="Run a custom -vf chain via --filter-string.",
    )
    parser.add_argument(
        "--filter-string", default=None, help="Custom -vf value (used with --custom)."
    )
    parser.add_argument(
        "--input", default=None, help="Primary input file (for single-input presets)."
    )
    parser.add_argument("--output", required=True, help="Output file.")
    parser.add_argument(
        "--watermark", default=None, help="Overlay image path (for --preset watermark)."
    )
    parser.add_argument(
        "--text", default=None, help="Reserved for future drawtext presets."
    )
    parser.add_argument(
        "--inputs",
        default=None,
        help="Comma-separated input paths (for hstack/vstack).",
    )
    parser.add_argument(
        "--fontfile",
        default=None,
        help=f"Font path for drawtext (default: {DEFAULT_FONTFILE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg command but do not execute.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print progress to stderr."
    )
    args = parser.parse_args()

    if not args.preset and not args.custom:
        parser.error("one of --preset or --custom is required")

    cmd = build_command(args)

    # Print exactly what will run so users can copy/paste or diff.
    print(" ".join(shlex.quote(c) for c in cmd))

    if args.dry_run:
        if args.verbose:
            _eprint("[dry-run] not executing")
        return

    if args.verbose:
        _eprint(f"[vfilter] running ffmpeg ({len(cmd)} args)")

    try:
        rc = subprocess.call(cmd)
    except FileNotFoundError:
        _eprint("Error: ffmpeg not on PATH")
        sys.exit(127)
    if rc != 0:
        _eprint(f"ffmpeg exited with code {rc}")
        sys.exit(rc)


if __name__ == "__main__":
    main()
