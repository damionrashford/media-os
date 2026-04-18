#!/usr/bin/env python3
"""frames.py — ffmpeg frame extraction and image I/O wrapper.

Subcommands:
  screenshot         Single still at a timestamp.
  every              One frame every N seconds (sequence dump).
  sheet              Contact sheet (tile=colsxrows).
  sprite             Sprite sheet sized for a web scrubber.
  gif                High-quality GIF via palettegen + paletteuse (two passes).
  images-to-video    Rebuild a video from a numeric/glob image sequence.

Stdlib only. Never prompts. Supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable


def _resolve_ffmpeg() -> str:
    """Locate ffmpeg; fall back to common macOS Homebrew paths."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.exists(candidate):
            return candidate
    print("error: ffmpeg not found on PATH", file=sys.stderr)
    sys.exit(2)


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if verbose or dry_run:
        print(printable, file=sys.stderr)
    if dry_run:
        return 0
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 127
    return proc.returncode


def _extend_common(cmd: list[str], extra: Iterable[str]) -> list[str]:
    cmd.extend(extra)
    return cmd


# ---------------- screenshot ----------------


def cmd_screenshot(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    cmd = [
        ff,
        "-hide_banner",
        "-y",
        "-ss",
        args.time,
        "-i",
        args.input,
        "-vframes",
        "1",
    ]
    vf_parts = []
    if args.width:
        vf_parts.append(f"scale={args.width}:-1")
    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]
    # JPEG quality flag only applies if output looks like JPG.
    lower = args.output.lower()
    if lower.endswith((".jpg", ".jpeg")):
        cmd += ["-q:v", "2"]
    elif lower.endswith(".png"):
        cmd += ["-c:v", "png"]
    cmd.append(args.output)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- every (sequence) ----------------


def cmd_every(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    # fps = 1/interval (frames per second): every `interval` seconds.
    fps_expr = f"1/{args.interval}"
    cmd = [ff, "-hide_banner", "-y", "-i", args.input, "-vf", f"fps={fps_expr}"]
    if args.output_pattern.lower().endswith((".jpg", ".jpeg")):
        cmd += ["-q:v", "2"]
    cmd.append(args.output_pattern)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- sheet (contact sheet) ----------------


def cmd_sheet(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    vf = f"fps=1/{args.interval},scale={args.width}:-1,tile={args.cols}x{args.rows}"
    cmd = [ff, "-hide_banner", "-y", "-i", args.input, "-vf", vf, "-frames:v", "1"]
    if args.output.lower().endswith((".jpg", ".jpeg")):
        cmd += ["-q:v", "2"]
    cmd.append(args.output)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- sprite sheet ----------------


def cmd_sprite(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    vf = (
        f"fps=1/{args.interval},scale={args.width}:-1,"
        f"tile={args.tile_cols}x{args.tile_rows}"
    )
    cmd = [ff, "-hide_banner", "-y", "-i", args.input, "-vf", vf, "-frames:v", "1"]
    if args.output.lower().endswith((".jpg", ".jpeg")):
        cmd += ["-q:v", "3"]
    cmd.append(args.output)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- gif (palettegen + paletteuse) ----------------


def cmd_gif(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    # Put the temp palette next to the output when possible.
    out_dir = os.path.dirname(os.path.abspath(args.output)) or "."
    with tempfile.NamedTemporaryFile(
        prefix="palette_", suffix=".png", dir=out_dir, delete=False
    ) as tmp:
        palette = tmp.name
    try:
        palettegen_vf = f"fps={args.fps},scale={args.width}:-1:flags=lanczos,palettegen=max_colors=256"
        pass1 = [
            ff,
            "-hide_banner",
            "-y",
            "-i",
            args.input,
            "-vf",
            palettegen_vf,
            palette,
        ]
        rc = _run(pass1, dry_run=args.dry_run, verbose=args.verbose)
        if rc != 0:
            return rc
        paletteuse_lavfi = (
            f"fps={args.fps},scale={args.width}:-1:flags=lanczos[x];"
            f"[x][1:v]paletteuse=dither=bayer:bayer_scale=5"
        )
        pass2 = [
            ff,
            "-hide_banner",
            "-y",
            "-i",
            args.input,
            "-i",
            palette,
            "-lavfi",
            paletteuse_lavfi,
            args.output,
        ]
        return _run(pass2, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        if not args.dry_run and os.path.exists(palette):
            try:
                os.remove(palette)
            except OSError:
                pass


# ---------------- images-to-video ----------------


def cmd_images_to_video(args: argparse.Namespace) -> int:
    ff = _resolve_ffmpeg()
    cmd = [ff, "-hide_banner", "-y", "-framerate", str(args.fps)]
    # Detect glob vs numeric pattern heuristically: '*' or '?' → glob.
    if any(ch in args.pattern for ch in "*?["):
        cmd += ["-pattern_type", "glob"]
    cmd += ["-i", args.pattern, "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd.append(args.output)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- argparse wiring ----------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="frames.py",
        description="ffmpeg wrapper for frame extraction and image I/O.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print the command, don't run it."
    )
    p.add_argument(
        "--verbose", action="store_true", help="Echo the command before running."
    )
    sub = p.add_subparsers(dest="mode", required=True)

    # screenshot
    sp = sub.add_parser("screenshot", help="Single still at a timestamp.")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--time", required=True, help="Timestamp, e.g. 00:01:30 or 90")
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--width", type=int, default=None)
    sp.set_defaults(func=cmd_screenshot)

    # every
    sp = sub.add_parser("every", help="One frame every N seconds.")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument(
        "--interval", type=float, default=10, help="Seconds between frames."
    )
    sp.add_argument("--output-pattern", required=True, help="e.g. 'thumb_%%04d.jpg'")
    sp.set_defaults(func=cmd_every)

    # sheet
    sp = sub.add_parser("sheet", help="Contact sheet (tile=colsxrows).")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--cols", type=int, default=4)
    sp.add_argument("--rows", type=int, default=4)
    sp.add_argument("--interval", type=float, default=5)
    sp.add_argument("--width", type=int, default=320)
    sp.add_argument("--output", "-o", required=True)
    sp.set_defaults(func=cmd_sheet)

    # sprite
    sp = sub.add_parser("sprite", help="Sprite sheet for a web scrubber.")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--width", type=int, default=160)
    sp.add_argument("--tile-cols", type=int, default=10)
    sp.add_argument("--tile-rows", type=int, default=10)
    sp.add_argument("--interval", type=float, default=10)
    sp.add_argument("--output", "-o", required=True)
    sp.set_defaults(func=cmd_sprite)

    # gif
    sp = sub.add_parser("gif", help="High-quality GIF (palettegen + paletteuse).")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--fps", type=int, default=15)
    sp.add_argument("--width", type=int, default=480)
    sp.add_argument("--output", "-o", required=True)
    sp.set_defaults(func=cmd_gif)

    # images-to-video
    sp = sub.add_parser("images-to-video", help="Image sequence → MP4.")
    sp.add_argument(
        "--pattern", required=True, help="e.g. 'img_%%04d.png' or 'img_*.png'"
    )
    sp.add_argument("--fps", type=int, default=30)
    sp.add_argument("--output", "-o", required=True)
    sp.set_defaults(func=cmd_images_to_video)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
