#!/usr/bin/env python3
"""Synthetic media generation via ffmpeg lavfi sources.

Stdlib only. Non-interactive. Prints the ffmpeg command it is about to run and
optionally runs it. Use ``--dry-run`` to print without executing.

Subcommands:
  bars            SMPTE (HD or PAL) bars + 1 kHz sine tone -> video file
  test-pattern    Engineering test pattern (testsrc / testsrc2 / rgbtestsrc /
                  yuvtestsrc / mandelbrot) -> video file
  color           Solid color plate -> video file
  tone            Sine tone -> audio file
  noise           anoisesrc (white / pink / brown / blue / velvet) -> audio file
  silence         anullsrc -> audio file (literal zeros)
  hald-identity   Identity Hald CLUT PNG (for LUT authoring)

Every subcommand accepts ``--output``, ``--dry-run`` and ``--verbose``.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import List, Sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_resolution(value: str) -> str:
    """Validate a WxH string and normalize it back to WxH."""
    try:
        w, h = value.lower().split("x")
        w_i, h_i = int(w), int(h)
    except Exception as exc:  # noqa: BLE001
        raise argparse.ArgumentTypeError(
            f"resolution must be WxH (e.g. 1920x1080), got {value!r}"
        ) from exc
    if w_i <= 0 or h_i <= 0:
        raise argparse.ArgumentTypeError(
            f"resolution components must be positive, got {value!r}"
        )
    return f"{w_i}x{h_i}"


def _run(cmd: Sequence[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {pretty}")
    if dry_run:
        return 0
    proc = subprocess.run(cmd, check=False)
    if verbose:
        print(f"ffmpeg exit code: {proc.returncode}")
    return proc.returncode


def _video_output_args(crf: int = 18) -> List[str]:
    return [
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        str(crf),
        "-preset",
        "medium",
    ]


def _aac_args(bitrate: str = "192k", sr: int = 48000) -> List[str]:
    return ["-c:a", "aac", "-b:a", bitrate, "-ar", str(sr)]


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def cmd_bars(ns: argparse.Namespace) -> List[str]:
    resolution = ns.resolution
    fps = ns.fps
    duration = ns.duration
    tone_hz = ns.tone_hz
    sr = ns.sample_rate

    if ns.pal:
        source = f"pal100bars=size={resolution}:rate={fps}"
    elif ns.hd:
        source = f"smptehdbars=size={resolution}:rate={fps}"
    else:
        # Default: HD bars if resolution >= 1280 wide, else classic smptebars.
        width = int(resolution.split("x")[0])
        source = (
            f"smptehdbars=size={resolution}:rate={fps}"
            if width >= 1280
            else f"smptebars=size={resolution}:rate={fps}"
        )

    tone = f"sine=frequency={tone_hz}:sample_rate={sr}"

    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-f",
        "lavfi",
        "-i",
        tone,
        "-t",
        str(duration),
        *_video_output_args(),
        *_aac_args(sr=sr),
        ns.output,
    ]
    return cmd


def cmd_test_pattern(ns: argparse.Namespace) -> List[str]:
    kind = ns.kind
    source = f"{kind}=size={ns.resolution}:rate={ns.fps}"
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-t",
        str(ns.duration),
        *_video_output_args(),
        ns.output,
    ]
    return cmd


def cmd_color(ns: argparse.Namespace) -> List[str]:
    source = (
        f"color=c={ns.color}:size={ns.resolution}:rate={ns.fps}"
        f":duration={ns.duration}"
    )
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        *_video_output_args(),
        ns.output,
    ]
    return cmd


def cmd_tone(ns: argparse.Namespace) -> List[str]:
    source = (
        f"sine=frequency={ns.hz}:sample_rate={ns.sample_rate}"
        f":duration={ns.duration}"
    )
    codec = "pcm_s16le" if ns.output.lower().endswith(".wav") else "aac"
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-c:a",
        codec,
    ]
    if codec == "aac":
        cmd += ["-b:a", "192k"]
    cmd += [ns.output]
    return cmd


def cmd_noise(ns: argparse.Namespace) -> List[str]:
    source = (
        f"anoisesrc=color={ns.color}:sample_rate={ns.sample_rate}"
        f":amplitude={ns.amp}:duration={ns.duration}"
    )
    codec = "pcm_s16le" if ns.output.lower().endswith(".wav") else "aac"
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-c:a",
        codec,
    ]
    if codec == "aac":
        cmd += ["-b:a", "192k"]
    cmd += [ns.output]
    return cmd


def cmd_silence(ns: argparse.Namespace) -> List[str]:
    source = f"anullsrc=channel_layout={ns.layout}:sample_rate={ns.sample_rate}"
    codec = "pcm_s16le" if ns.output.lower().endswith(".wav") else "aac"
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-t",
        str(ns.duration),
        "-c:a",
        codec,
    ]
    if codec == "aac":
        cmd += ["-b:a", "192k"]
    cmd += [ns.output]
    return cmd


def cmd_hald_identity(ns: argparse.Namespace) -> List[str]:
    source = f"haldclutsrc=level={ns.level}"
    cmd: List[str] = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source,
        "-frames:v",
        "1",
        ns.output,
    ]
    return cmd


# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="synth.py",
        description=(
            "Generate synthetic test media via ffmpeg lavfi sources. "
            "Prints the exact ffmpeg command; use --dry-run to skip execution."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the command without running ffmpeg",
    )
    p.add_argument(
        "--verbose", action="store_true", help="show ffmpeg exit code on completion"
    )

    sub = p.add_subparsers(dest="subcommand", required=True)

    # bars
    sp = sub.add_parser("bars", help="SMPTE bars + 1 kHz sine tone")
    sp.add_argument("--output", required=True)
    sp.add_argument("--duration", type=float, default=10.0)
    sp.add_argument("--resolution", type=_parse_resolution, default="1920x1080")
    sp.add_argument("--fps", type=int, default=30)
    sp.add_argument("--tone-hz", type=float, default=1000.0)
    sp.add_argument("--sample-rate", type=int, default=48000)
    group = sp.add_mutually_exclusive_group()
    group.add_argument("--pal", action="store_true", help="use pal100bars (PAL 100%)")
    group.add_argument("--hd", action="store_true", help="force smptehdbars (HD 100%)")
    sp.set_defaults(func=cmd_bars)

    # test-pattern
    sp = sub.add_parser("test-pattern", help="engineering test pattern")
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--kind",
        choices=["testsrc", "testsrc2", "rgbtestsrc", "yuvtestsrc", "mandelbrot"],
        default="testsrc2",
    )
    sp.add_argument("--duration", type=float, default=10.0)
    sp.add_argument("--resolution", type=_parse_resolution, default="1280x720")
    sp.add_argument("--fps", type=int, default=30)
    sp.set_defaults(func=cmd_test_pattern)

    # color
    sp = sub.add_parser("color", help="solid color plate")
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--color", default="red", help="named color, 0xRRGGBB, #RRGGBB, or 'random'"
    )
    sp.add_argument("--duration", type=float, default=5.0)
    sp.add_argument("--resolution", type=_parse_resolution, default="1920x1080")
    sp.add_argument("--fps", type=int, default=30)
    sp.set_defaults(func=cmd_color)

    # tone
    sp = sub.add_parser("tone", help="sine tone (audio only)")
    sp.add_argument("--output", required=True)
    sp.add_argument("--hz", type=float, default=1000.0)
    sp.add_argument("--duration", type=float, default=10.0)
    sp.add_argument("--sample-rate", type=int, default=48000)
    sp.set_defaults(func=cmd_tone)

    # noise
    sp = sub.add_parser("noise", help="anoisesrc (audio only)")
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--color", choices=["white", "pink", "brown", "blue", "velvet"], default="white"
    )
    sp.add_argument("--duration", type=float, default=10.0)
    sp.add_argument(
        "--amp", type=float, default=0.3, help="amplitude 0.0-1.0 (default 0.3)"
    )
    sp.add_argument("--sample-rate", type=int, default=48000)
    sp.set_defaults(func=cmd_noise)

    # silence
    sp = sub.add_parser("silence", help="anullsrc (digital silence)")
    sp.add_argument("--output", required=True)
    sp.add_argument("--duration", type=float, default=10.0)
    sp.add_argument(
        "--layout", default="stereo", help="channel layout (mono/stereo/5.1)"
    )
    sp.add_argument("--sample-rate", type=int, default=48000)
    sp.set_defaults(func=cmd_silence)

    # hald-identity
    sp = sub.add_parser(
        "hald-identity", help="identity Hald CLUT PNG for LUT authoring"
    )
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--level",
        type=int,
        default=8,
        help="Hald level N -> N^3 x N^3 image (default 8 = 512x512)",
    )
    sp.set_defaults(func=cmd_hald_identity)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    cmd = ns.func(ns)
    return _run(cmd, dry_run=ns.dry_run, verbose=ns.verbose)


if __name__ == "__main__":
    sys.exit(main())
