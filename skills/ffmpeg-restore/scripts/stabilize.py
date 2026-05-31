#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Video stabilization helper for ffmpeg.

Subcommands:
    stabilize    Two-pass vid.stab (vidstabdetect + vidstabtransform).
    deshake      Single-pass builtin deshake filter.
    check-build  Report whether the local ffmpeg build supports vid.stab.

Examples:
    uv run scripts/stabilize.py check-build
    uv run scripts/stabilize.py stabilize --input in.mp4 --output out.mp4
    uv run scripts/stabilize.py stabilize --input in.mp4 --output out.mp4 \
        --smoothing 45 --zoom auto --shakiness 8 --accuracy 15 --sharpen
    uv run scripts/stabilize.py stabilize --input in.mp4 --output out.mp4 --zoom 5%
    uv run scripts/stabilize.py deshake --input in.mp4 --output out.mp4

Global options:
    --dry-run    Print the ffmpeg command(s) that would run, then exit.
    --verbose    Print progress to stderr.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[stabilize] {msg}", file=sys.stderr)


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        print("Error: ffmpeg not found on PATH", file=sys.stderr)
        sys.exit(2)
    return path


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    if dry_run:
        print(pretty)
        return 0
    _log(f"running: {pretty}", verbose)
    proc = subprocess.run(cmd)
    return proc.returncode


def _has_vidstab() -> bool:
    ffmpeg = _require_ffmpeg()
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    text = (out.stdout or "") + (out.stderr or "")
    return "vidstabdetect" in text and "vidstabtransform" in text


def _parse_zoom(raw: str) -> tuple[str, str]:
    """
    Return (key, value) to inject into the vidstabtransform arg list.

    "auto"       -> ("optzoom", "1")
    "5%" / "5"   -> ("zoom", "5")
    "0"          -> ("zoom", "0")
    """
    raw = raw.strip().lower()
    if raw in ("auto", "optzoom", "opt"):
        return ("optzoom", "1")
    if raw.endswith("%"):
        raw = raw[:-1]
    try:
        int(raw)
    except ValueError:
        print(
            f"Error: --zoom must be 'auto' or a number like '5' or '5%', got {raw!r}",
            file=sys.stderr,
        )
        sys.exit(2)
    return ("zoom", raw)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check_build(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    ok = _has_vidstab()
    print(f"ffmpeg: {ffmpeg}")
    print(
        f"vid.stab (vidstabdetect + vidstabtransform): {'AVAILABLE' if ok else 'MISSING'}"
    )
    if not ok:
        print("  Install a build with --enable-libvidstab (e.g. `brew install ffmpeg`)")
        print("  or fall back to: scripts/stabilize.py deshake ...")
    return 0 if ok else 1


def cmd_stabilize(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()

    if not args.dry_run and not _has_vidstab():
        print("Error: this ffmpeg build has no vid.stab support.", file=sys.stderr)
        print("Run: scripts/stabilize.py check-build", file=sys.stderr)
        return 2

    in_path = Path(args.input)
    if not args.dry_run and not in_path.exists():
        print(f"Error: input not found: {in_path}", file=sys.stderr)
        return 2

    out_path = Path(args.output)
    zoom_key, zoom_val = _parse_zoom(args.zoom)

    with tempfile.TemporaryDirectory(prefix="vidstab_") as tmp:
        trf = Path(tmp) / "transforms.trf"

        # Pass 1 — detect
        detect_vf = (
            f"vidstabdetect="
            f"shakiness={args.shakiness}:"
            f"accuracy={args.accuracy}:"
            f"result={trf}"
        )
        pass1 = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(in_path),
            "-vf",
            detect_vf,
            "-f",
            "null",
            "-",
        ]
        _log("pass 1/2 (vidstabdetect)", args.verbose)
        rc = _run(pass1, dry_run=args.dry_run, verbose=args.verbose)
        if rc != 0:
            return rc

        # Pass 2 — transform
        transform_parts = [
            f"input={trf}",
            f"smoothing={args.smoothing}",
            f"{zoom_key}={zoom_val}",
            f"crop={args.crop}",
        ]
        vf = "vidstabtransform=" + ":".join(transform_parts)
        if args.sharpen:
            vf += ",unsharp=5:5:0.8:3:3:0.4"

        pass2 = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(in_path),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            "copy",
            str(out_path),
        ]
        _log("pass 2/2 (vidstabtransform)", args.verbose)
        rc = _run(pass2, dry_run=args.dry_run, verbose=args.verbose)
        return rc


def cmd_deshake(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    in_path = Path(args.input)
    if not args.dry_run and not in_path.exists():
        print(f"Error: input not found: {in_path}", file=sys.stderr)
        return 2

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(in_path),
        "-vf",
        "deshake",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
        str(Path(args.output)),
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stabilize.py",
        description="Video stabilization helpers for ffmpeg (vid.stab + deshake).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print the command(s) and exit"
    )
    p.add_argument("--verbose", action="store_true", help="Print progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    # stabilize
    s = sub.add_parser("stabilize", help="Two-pass vid.stab stabilization")
    s.add_argument("--input", "-i", required=True, help="Input media file")
    s.add_argument("--output", "-o", required=True, help="Output media file")
    s.add_argument(
        "--smoothing",
        type=int,
        default=30,
        help="Smoothing window in frames (default: 30; ~1s at 30fps)",
    )
    s.add_argument(
        "--zoom",
        default="0",
        help='Zoom: "auto" (optzoom=1), or a percent like "5" / "5%%" (default: 0)',
    )
    s.add_argument(
        "--shakiness",
        type=int,
        default=5,
        choices=range(1, 11),
        metavar="1..10",
        help="Detect shakiness 1..10 (default: 5)",
    )
    s.add_argument(
        "--accuracy",
        type=int,
        default=15,
        choices=range(1, 16),
        metavar="1..15",
        help="Detect accuracy 1..15 (default: 15)",
    )
    s.add_argument(
        "--crop",
        default="black",
        choices=["black", "keep"],
        help="Border fill: black or keep previous pixels (default: black)",
    )
    s.add_argument(
        "--sharpen",
        action="store_true",
        help="Apply unsharp after transform to restore sharpness",
    )
    s.add_argument("--crf", type=int, default=18, help="libx264 CRF (default: 18)")
    s.add_argument("--preset", default="slow", help="libx264 preset (default: slow)")
    s.set_defaults(func=cmd_stabilize)

    # deshake
    d = sub.add_parser("deshake", help="Single-pass builtin deshake")
    d.add_argument("--input", "-i", required=True, help="Input media file")
    d.add_argument("--output", "-o", required=True, help="Output media file")
    d.add_argument("--crf", type=int, default=18, help="libx264 CRF (default: 18)")
    d.add_argument(
        "--preset", default="medium", help="libx264 preset (default: medium)"
    )
    d.set_defaults(func=cmd_deshake)

    # check-build
    c = sub.add_parser(
        "check-build", help="Report vid.stab availability in local ffmpeg"
    )
    c.set_defaults(func=cmd_check_build)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
