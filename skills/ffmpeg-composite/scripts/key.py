#!/usr/bin/env python3
"""Chromakey / composite helper for ffmpeg.

Subcommands:
    key               Key a COLOR out of a clip; write an alpha-aware file.
    composite         Key the fg + despill + overlay on top of bg in one go.
    identity-transparent  Key a clip and export as ProRes 4444 (.mov) alpha mezzanine.

Notes:
    * Output container determines alpha handling. Known alpha-capable combos:
        .mov  + qtrle                         (lossless RGBA, big files)
        .mov  + prores_ks -profile:v 4444     (yuva444p10le, pro-finishing)
        .webm + libvpx-vp9 -pix_fmt yuva420p  (web)
        .mkv  + ffv1                          (lossless)
        .png  / %05d.png sequence             (fully portable)
    * Anything else (mp4+libx264, mp4+libx265, etc.) CANNOT carry alpha and the
      script will force a safe flatten over black if the user asks for it there.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# codec / container resolution
# --------------------------------------------------------------------------- #

ALPHA_CODEC_BY_EXT = {
    ".mov": ("prores_ks", ["-profile:v", "4444", "-pix_fmt", "yuva444p10le"]),
    ".webm": (
        "libvpx-vp9",
        ["-pix_fmt", "yuva420p", "-b:v", "4M", "-auto-alt-ref", "0"],
    ),
    ".mkv": ("ffv1", ["-pix_fmt", "yuva420p"]),
    ".png": ("png", []),
}

QTRLE_MOV = ("qtrle", [])  # legacy lossless RGBA option for .mov


def pick_alpha_codec(
    out_path: Path, prefer_qtrle: bool = False
) -> tuple[str, list[str], str]:
    """Return (codec, extra_args, pix_fmt_for_filter) for the requested output.

    pix_fmt_for_filter is what should be force-fed to the filtergraph via
    `,format=<pix_fmt>` so the encoder actually sees an alpha plane.
    """
    ext = out_path.suffix.lower()
    if ext == ".mov" and prefer_qtrle:
        return ("qtrle", [], "rgba")
    if ext in ALPHA_CODEC_BY_EXT:
        codec, extras = ALPHA_CODEC_BY_EXT[ext]
        pix = (
            "rgba"
            if codec == "png"
            else "yuva420p" if codec in ("libvpx-vp9", "ffv1") else "yuva444p10le"
        )
        return (codec, extras, pix)
    # Fallback: mp4, etc. Cannot carry alpha — warn and flatten.
    return ("libx264", ["-crf", "18", "-pix_fmt", "yuv420p"], "yuv420p")


# --------------------------------------------------------------------------- #
# filter graph builders
# --------------------------------------------------------------------------- #


def key_filter(method: str, color: str, similarity: float, blend: float) -> str:
    """Build the key-filter expression for a given method."""
    if method == "chromakey":
        return f"chromakey={color}:{similarity}:{blend}"
    if method == "colorkey":
        return f"colorkey={color}:{similarity}:{blend}"
    if method == "hsvkey":
        # Approximation: use similarity/blend, default hue=120 (green), s=0.7, v=0.3.
        # User can still pass a color hex (ignored for hue; we use standard green).
        return f"hsvkey=h=120:s=0.7:v=0.3:similarity={similarity}:blend={blend}"
    raise SystemExit(f"unknown key method: {method!r}")


def despill_filter(kind: str) -> str:
    if kind == "none":
        return ""
    if kind == "green":
        return "despill=type=green:mix=0.5:expand=0.1"
    if kind == "blue":
        return "despill=type=blue:mix=0.5:expand=0.1"
    raise SystemExit(f"unknown despill kind: {kind!r}")


def build_key_chain(
    method: str, color: str, similarity: float, blend: float, despill: str, pix_fmt: str
) -> str:
    """[0:v] -> key -> (despill) -> format=pix_fmt."""
    parts = [key_filter(method, color, similarity, blend)]
    df = despill_filter(despill)
    if df:
        parts.append(df)
    parts.append(f"format={pix_fmt}")
    return ",".join(parts)


# --------------------------------------------------------------------------- #
# command runners
# --------------------------------------------------------------------------- #


def run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(printable)
    if dry_run:
        return 0
    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except FileNotFoundError:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        return 127


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #


def cmd_key(args: argparse.Namespace) -> int:
    out = Path(args.output)
    codec, extra, pix = pick_alpha_codec(
        out, prefer_qtrle=(out.suffix.lower() == ".mov" and args.qtrle)
    )
    if codec == "libx264":
        print(
            f"warning: {out.suffix} cannot carry alpha; output will be flattened over black",
            file=sys.stderr,
        )
    chain = build_key_chain(
        args.method, args.color, args.similarity, args.blend, args.despill, pix
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        args.input,
        "-vf",
        chain,
        "-c:v",
        codec,
        *extra,
        "-c:a",
        "copy",
        str(out),
    ]
    return run(cmd, args.dry_run, args.verbose)


def cmd_composite(args: argparse.Namespace) -> int:
    out = Path(args.output)
    # Composite output goes to a flat-delivery codec unless user picks an alpha container.
    codec, extra, _ = pick_alpha_codec(out)
    if codec == "libx264":
        # Normal case: flat H.264 delivery.
        extra = ["-crf", str(args.crf), "-pix_fmt", "yuv420p"]
    key_chain = build_key_chain(
        args.method, args.color, args.similarity, args.blend, args.despill, "yuva444p"
    )
    filtergraph = (
        f"[0:v]{key_chain}[k];"
        f"[1:v][k]overlay{'=shortest=1' if args.shortest else ''}[out]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        args.fg,
        "-i",
        args.bg,
        "-filter_complex",
        filtergraph,
        "-map",
        "[out]",
        "-map",
        "0:a?",
        "-c:v",
        codec,
        *extra,
        str(out),
    ]
    return run(cmd, args.dry_run, args.verbose)


def cmd_identity_transparent(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.suffix.lower() != ".mov":
        print(
            f"warning: identity-transparent expects .mov (ProRes 4444); got {out.suffix}",
            file=sys.stderr,
        )
    chain = build_key_chain(
        args.method,
        args.color,
        args.similarity,
        args.blend,
        args.despill,
        "yuva444p10le",
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        args.input,
        "-vf",
        chain,
        "-c:v",
        "prores_ks",
        "-profile:v",
        "4444",
        "-pix_fmt",
        "yuva444p10le",
        "-c:a",
        "copy",
        str(out),
    ]
    return run(cmd, args.dry_run, args.verbose)


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #


def add_common_key_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--color",
        default="0x00FF00",
        help="key color hex (default 0x00FF00 pure green — almost never right; sample your footage)",
    )
    p.add_argument(
        "--similarity",
        type=float,
        default=0.10,
        help="color tolerance 0.01-0.30 typical (default 0.10)",
    )
    p.add_argument(
        "--blend",
        type=float,
        default=0.05,
        help="edge softness 0.00-0.20 typical (default 0.05)",
    )
    p.add_argument(
        "--method", choices=["chromakey", "colorkey", "hsvkey"], default="chromakey"
    )
    p.add_argument(
        "--despill",
        choices=["none", "green", "blue"],
        default="none",
        help="run despill after key (recommended: green for green screens)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="key.py",
        description="Chromakey / composite helper for ffmpeg.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print command, do not run"
    )
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    pk = sub.add_parser(
        "key",
        help="Key a color out of a clip; write with alpha if container supports it.",
    )
    pk.add_argument("--input", required=True)
    pk.add_argument("--output", required=True)
    pk.add_argument(
        "--qtrle",
        action="store_true",
        help="for .mov output, use qtrle (RGBA) instead of ProRes 4444",
    )
    add_common_key_args(pk)
    pk.set_defaults(func=cmd_key)

    pc = sub.add_parser(
        "composite", help="Key foreground + despill + overlay on background in one go."
    )
    pc.add_argument("--fg", required=True)
    pc.add_argument("--bg", required=True)
    pc.add_argument("--output", required=True)
    pc.add_argument(
        "--crf", type=int, default=18, help="x264 CRF for flat delivery (default 18)"
    )
    pc.add_argument(
        "--shortest",
        action="store_true",
        help="end output at the shorter-length stream via overlay=shortest=1",
    )
    add_common_key_args(pc)
    pc.set_defaults(func=cmd_composite)

    pi = sub.add_parser(
        "identity-transparent", help="Key and export ProRes 4444 .mov alpha mezzanine."
    )
    pi.add_argument("--input", required=True)
    pi.add_argument("--output", required=True, help="must be .mov")
    add_common_key_args(pi)
    pi.set_defaults(func=cmd_identity_transparent)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Light default: make composite's despill=green the practical default when user
    # forgets to set it, since fringe is near-universal.
    if getattr(args, "subcommand", None) == "composite" and args.despill == "none":
        args.despill = "green"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
