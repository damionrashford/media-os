#!/usr/bin/env python3
"""
image.py — thin, scriptable wrapper around ImageMagick's `magick` CLI.

Every subcommand prints the exact `magick` / `mogrify` / `identify` / `montage`
command it will run. Pass `--dry-run` to print without executing. Pass
`--verbose` to also echo the command in execute mode.

Requires ImageMagick 7+ (`magick` on PATH). Stdlib only, non-interactive.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _magick_bin() -> str:
    """Locate the `magick` binary. Falls back to legacy split binaries on v6."""
    for candidate in ("magick",):
        if shutil.which(candidate):
            return candidate
    sys.stderr.write(
        "error: `magick` not found on PATH. Install ImageMagick 7+ "
        "(brew install imagemagick / apt install imagemagick).\n"
    )
    sys.exit(127)


def _print_cmd(cmd: Sequence[str]) -> None:
    sys.stdout.write("+ " + " ".join(shlex.quote(str(a)) for a in cmd) + "\n")
    sys.stdout.flush()


def _run(
    cmd: Sequence[str], *, dry_run: bool, verbose: bool, capture: bool = False
) -> subprocess.CompletedProcess | None:
    if dry_run or verbose:
        _print_cmd(cmd)
    if dry_run:
        return None
    return subprocess.run(
        list(cmd),
        check=False,
        text=True,
        capture_output=capture,
    )


def _check(result: subprocess.CompletedProcess | None) -> int:
    if result is None:
        return 0
    if result.returncode != 0:
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.returncode
    if result.stdout and not result.stdout.isspace():
        sys.stdout.write(result.stdout)
        if not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: check
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    _run([magick, "-version"], dry_run=args.dry_run, verbose=args.verbose)
    r = _run(
        [magick, "-list", "format"],
        dry_run=args.dry_run,
        verbose=args.verbose,
        capture=True,
    )
    if r is None:
        return 0
    lines = r.stdout.splitlines() if r.stdout else []
    interesting = {
        "JPEG",
        "PNG",
        "WEBP",
        "HEIC",
        "AVIF",
        "JXL",
        "TIFF",
        "GIF",
        "PDF",
        "PSD",
        "ICO",
        "BMP",
        "SVG",
    }
    found = {}
    for line in lines:
        token = line.strip().split(" ", 1)[0].upper().rstrip("*")
        if token in interesting and token not in found:
            found[token] = line.strip()
    print("\nFormat support on this build:")
    for fmt in sorted(interesting):
        print(f"  {fmt:<5} : {'YES' if fmt in found else 'no'}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: resize
# ---------------------------------------------------------------------------


def _resize_geometry(width: int | None, height: int | None, fit: str) -> str:
    if width is None and height is None:
        raise SystemExit("resize: --width or --height is required")
    w = str(width) if width else ""
    h = str(height) if height else ""
    geo = f"{w}x{h}"
    if fit == "inside":
        return geo  # default fit-inside
    if fit == "fill":
        return geo + "^"  # fill, will need -extent to crop
    if fit == "force":
        return geo + "!"  # force exact, may distort
    raise SystemExit(f"resize: unknown --fit {fit}")


def cmd_resize(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    geo = _resize_geometry(args.width, args.height, args.fit)
    cmd: list[str] = [magick, args.input, "-resize", geo]
    if args.fit == "fill":
        ext = f"{args.width or ''}x{args.height or ''}"
        cmd += ["-gravity", "center", "-extent", ext]
    if args.quality is not None:
        cmd += ["-quality", str(args.quality)]
    cmd += [args.output]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: thumb
# ---------------------------------------------------------------------------


def cmd_thumb(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd = [
        magick,
        args.input,
        "-thumbnail",
        f"{args.size}^",
        "-gravity",
        "center",
        "-extent",
        args.size,
        "-strip",
    ]
    if args.quality is not None:
        cmd += ["-quality", str(args.quality)]
    cmd += [args.output]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: convert
# ---------------------------------------------------------------------------


def cmd_convert(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd: list[str] = [magick, args.input]
    if args.strip:
        cmd += ["-strip"]
    if args.quality is not None:
        cmd += ["-quality", str(args.quality)]
    cmd += [args.output]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: crop
# ---------------------------------------------------------------------------


def cmd_crop(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd = [magick, args.input, "-crop", args.rect, "+repage", args.output]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: text
# ---------------------------------------------------------------------------


def cmd_text(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd: list[str] = [magick, args.input]
    if args.font:
        cmd += ["-font", args.font]
    cmd += [
        "-pointsize",
        str(args.size),
        "-fill",
        args.color,
        "-gravity",
        args.gravity,
        "-annotate",
        args.position,
        args.text,
        args.output,
    ]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: overlay (composite two images)
# ---------------------------------------------------------------------------


def cmd_overlay(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd = [
        magick,
        args.base,
        args.overlay,
        "-gravity",
        args.gravity,
        "-geometry",
        args.position,
        "-composite",
        args.output,
    ]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: montage
# ---------------------------------------------------------------------------


def cmd_montage(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    geo = f"{args.size}+5+5" if args.size else "+5+5"
    cmd = [
        magick,
        "montage",
        *args.inputs,
        "-geometry",
        geo,
        "-tile",
        args.tile,
        args.output,
    ]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: animate-gif
# ---------------------------------------------------------------------------


def cmd_animate_gif(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    cmd = [
        magick,
        "-delay",
        str(args.delay),
        "-loop",
        "0",
        *args.inputs,
        "-layers",
        "Optimize",
        args.output,
    ]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: pdf-to-png
# ---------------------------------------------------------------------------


def cmd_pdf_to_png(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pattern = str(outdir / "page_%03d.png")
    cmd = [
        magick,
        "-density",
        str(args.density),
        args.input,
        "-background",
        "white",
        "-alpha",
        "remove",
        "-alpha",
        "off",
        pattern,
    ]
    return _check(_run(cmd, dry_run=args.dry_run, verbose=args.verbose))


# ---------------------------------------------------------------------------
# Subcommand: identify (JSON)
# ---------------------------------------------------------------------------


def cmd_identify(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    fmt = (
        '{"file":"%f","format":"%m","width":%w,"height":%h,'
        '"quality":%Q,"colorspace":"%[colorspace]","depth":%z,'
        '"filesize":"%B"}'
    )
    cmd = [magick, "identify", "-format", fmt, args.input]
    result = _run(cmd, dry_run=args.dry_run, verbose=args.verbose, capture=True)
    if result is None:
        return 0
    if result.returncode != 0:
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.returncode
    try:
        obj = json.loads(result.stdout.strip().splitlines()[0])
    except Exception:
        sys.stdout.write(result.stdout)
        return 0
    print(json.dumps(obj, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: batch-resize
# ---------------------------------------------------------------------------


_IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".heic",
    ".avif",
    ".jxl",
    ".bmp",
    ".gif",
}


def cmd_batch_resize(args: argparse.Namespace) -> int:
    magick = _magick_bin()
    indir = Path(args.indir)
    outdir = Path(args.outdir)
    if not indir.is_dir():
        sys.stderr.write(f"error: --indir {indir} is not a directory\n")
        return 2
    outdir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        p for p in indir.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )
    if not files:
        sys.stderr.write(f"warning: no images in {indir}\n")
        return 0

    geo = _resize_geometry(args.width, args.height, args.fit)
    rc = 0
    for src in files:
        dst = outdir / src.name
        cmd: list[str] = [magick, str(src), "-resize", geo]
        if args.fit == "fill":
            cmd += [
                "-gravity",
                "center",
                "-extent",
                f"{args.width or ''}x{args.height or ''}",
            ]
        if args.quality is not None:
            cmd += ["-quality", str(args.quality)]
        if args.strip:
            cmd += ["-strip"]
        cmd += [str(dst)]
        r = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
        if r is not None and r.returncode != 0:
            sys.stderr.write(f"failed: {src}\n")
            rc = r.returncode
    return rc


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="image.py",
        description="Thin wrapper around ImageMagick's `magick` CLI.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print the command but do not execute."
    )
    p.add_argument(
        "--verbose", action="store_true", help="Echo each command before executing it."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("check", help="Report magick version + format support.")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("resize", help="Resize an image.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--width", type=int)
    s.add_argument("--height", type=int)
    s.add_argument(
        "--fit",
        choices=("inside", "fill", "force"),
        default="inside",
        help="inside=fit aspect, fill=cover+crop, force=distort",
    )
    s.add_argument("--quality", type=int)
    s.set_defaults(func=cmd_resize)

    s = sub.add_parser("thumb", help="Create a cropped center-filled thumbnail.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--size", default="200x200", help="e.g. 200x200")
    s.add_argument("--quality", type=int, default=82)
    s.set_defaults(func=cmd_thumb)

    s = sub.add_parser("convert", help="Change format / quality / strip metadata.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--quality", type=int)
    s.add_argument(
        "--strip", action="store_true", help="Remove EXIF/XMP/IPTC metadata."
    )
    s.set_defaults(func=cmd_convert)

    s = sub.add_parser("crop", help="Crop to WxH+X+Y.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--rect", required=True, help="Geometry e.g. 800x600+100+50")
    s.set_defaults(func=cmd_crop)

    s = sub.add_parser("text", help="Draw text on an image.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--font", default=None, help="Font name from `magick -list font`.")
    s.add_argument("--size", type=int, default=72, help="Point size.")
    s.add_argument("--position", default="+10+10", help="-annotate offset, e.g. +10+10")
    s.add_argument("--color", default="white")
    s.add_argument(
        "--gravity",
        default="NorthWest",
        help="NorthWest/North/NorthEast/West/Center/East/" "SouthWest/South/SouthEast",
    )
    s.set_defaults(func=cmd_text)

    s = sub.add_parser("overlay", help="Composite overlay onto base.")
    s.add_argument("--base", required=True)
    s.add_argument("--overlay", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--position", default="+10+10", help="-geometry offset from gravity anchor"
    )
    s.add_argument("--gravity", default="NorthWest")
    s.set_defaults(func=cmd_overlay)

    s = sub.add_parser("montage", help="Assemble a grid contact sheet.")
    s.add_argument("--inputs", nargs="+", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--tile", default="4x4", help="e.g. 4x4")
    s.add_argument(
        "--size",
        default="200x200",
        help="Per-cell size, e.g. 200x200. Empty string = native.",
    )
    s.set_defaults(func=cmd_montage)

    s = sub.add_parser("animate-gif", help="Build an animated GIF from frames.")
    s.add_argument("--inputs", nargs="+", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--delay", type=int, default=10, help="Centiseconds between frames. 10 = 100ms."
    )
    s.set_defaults(func=cmd_animate_gif)

    s = sub.add_parser("pdf-to-png", help="Rasterize a PDF to page_NNN.png.")
    s.add_argument("--input", required=True)
    s.add_argument("--outdir", required=True)
    s.add_argument("--density", type=int, default=300, help="DPI.")
    s.set_defaults(func=cmd_pdf_to_png)

    s = sub.add_parser("identify", help="Probe an image, emit JSON.")
    s.add_argument("--input", required=True)
    s.set_defaults(func=cmd_identify)

    s = sub.add_parser(
        "batch-resize", help="Resize every image in --indir into --outdir."
    )
    s.add_argument("--indir", required=True)
    s.add_argument("--outdir", required=True)
    s.add_argument("--width", type=int)
    s.add_argument("--height", type=int)
    s.add_argument("--fit", choices=("inside", "fill", "force"), default="inside")
    s.add_argument("--quality", type=int, default=85)
    s.add_argument("--strip", action="store_true")
    s.set_defaults(func=cmd_batch_resize)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
