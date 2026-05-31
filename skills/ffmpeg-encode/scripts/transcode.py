#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
transcode.py — preset-driven ffmpeg transcoder.

Each --preset maps to a concrete, opinionated ffmpeg argument list.
Prints the full ffmpeg command to stderr before running it, and exits
non-zero on ffmpeg failure.

Usage:
  uv run transcode.py --input IN --output OUT --preset web-mp4
  uv run transcode.py --input IN --output OUT --preset hevc-mkv --crf 20
  uv run transcode.py --input IN --output OUT --preset av1-mp4 --dry-run
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# preset name -> (default_crf, default_audio_kbps, arg_builder)
# arg_builder(crf, audio_kbps) -> list[str] of ffmpeg args (excluding -i / output)
Preset = dict[str, object]


def preset_web_mp4(crf: int, ab: int) -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        f"{ab}k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
    ]


def preset_hevc_mkv(crf: int, ab: int) -> list[str]:
    return [
        "-c:v",
        "libx265",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p10le",
        "-c:a",
        "libopus",
        "-b:a",
        f"{ab}k",
    ]


def preset_web_webm(crf: int, ab: int) -> list[str]:
    return [
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        str(crf),
        "-row-mt",
        "1",
        "-cpu-used",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "libopus",
        "-b:a",
        f"{ab}k",
    ]


def preset_av1_mp4(crf: int, ab: int) -> list[str]:
    return [
        "-c:v",
        "libsvtav1",
        "-preset",
        "6",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p10le",
        "-c:a",
        "libopus",
        "-b:a",
        f"{ab}k",
        "-movflags",
        "+faststart",
    ]


def preset_prores(crf: int, ab: int) -> list[str]:
    # CRF/bitrate are ignored for ProRes; profile 3 = HQ
    return [
        "-c:v",
        "prores_ks",
        "-profile:v",
        "3",
        "-pix_fmt",
        "yuv422p10le",
        "-c:a",
        "pcm_s16le",
    ]


def preset_archive(crf: int, ab: int) -> list[str]:
    # Near-visually-lossless HEVC master in MKV with FLAC audio.
    return [
        "-c:v",
        "libx265",
        "-preset",
        "slow",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p10le",
        "-x265-params",
        "profile=main10",
        "-c:a",
        "flac",
        "-compression_level",
        "8",
    ]


PRESETS: dict[str, tuple[int, int, object]] = {
    "web-mp4": (20, 128, preset_web_mp4),
    "hevc-mkv": (22, 128, preset_hevc_mkv),
    "web-webm": (32, 96, preset_web_webm),
    "av1-mp4": (30, 96, preset_av1_mp4),
    "prores": (0, 0, preset_prores),  # crf/ab ignored
    "archive": (18, 128, preset_archive),
}


def build_command(
    input_path: Path,
    output_path: Path,
    preset: str,
    crf: int | None,
    audio_bitrate: int | None,
    verbose: bool,
) -> list[str]:
    if preset not in PRESETS:
        raise SystemExit(f"unknown preset {preset!r}; choose from {list(PRESETS)}")
    default_crf, default_ab, builder = PRESETS[preset]
    effective_crf = crf if crf is not None else default_crf
    effective_ab = audio_bitrate if audio_bitrate is not None else default_ab

    args: list[str] = ["ffmpeg", "-hide_banner"]
    args += ["-loglevel", "info" if verbose else "warning", "-stats"]
    args += ["-y", "-i", str(input_path)]
    args += builder(effective_crf, effective_ab)  # type: ignore[operator]
    args += [str(output_path)]
    return args


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--input", required=True, type=Path, help="Source media file")
    p.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination file (extension sets container)",
    )
    p.add_argument("--preset", required=True, choices=sorted(PRESETS.keys()))
    p.add_argument(
        "--crf", type=int, default=None, help="Override preset CRF (ignored for prores)"
    )
    p.add_argument(
        "--audio-bitrate",
        type=int,
        default=None,
        help="Override audio bitrate in kbps (ignored for prores)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg command and exit 0 without running it",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Pass -loglevel info to ffmpeg"
    )
    args = p.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None and not args.dry_run:
        print("error: ffmpeg not on PATH", file=sys.stderr)
        return 2

    cmd = build_command(
        args.input, args.output, args.preset, args.crf, args.audio_bitrate, args.verbose
    )
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)

    if args.dry_run:
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
