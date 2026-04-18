#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
bsf.py - ffmpeg bitstream-filter runner.

Subcommands (each one wraps a common -bsf task with `-c copy`):

    mp4-to-ts          MP4/MOV (H.264 or HEVC) -> MPEG-TS, auto-picks h264_mp4toannexb
                       or hevc_mp4toannexb via ffprobe.
    ts-to-mp4          MPEG-TS (AAC audio) -> MP4, applies aac_adtstoasc.
    fix-packed-bframes Fix old DivX/XviD MP4s with mpeg4_unpack_bframes.
    level              Rewrite H.264 Level via h264_metadata=level=...
                       (HEVC inputs auto-switch to hevc_metadata=level=...).
    strip-sei          Drop SEI (NAL type 6) via filter_units=remove_types=6.
    trace              Dump SPS/PPS/slice header via trace_headers (read-only).
    zero-ts            Re-base PTS/DTS to 0 on video + audio via setts.

Every subcommand prints the exact ffmpeg command to stderr before running.

Examples:

    uv run bsf.py mp4-to-ts --input in.mp4 --output out.ts
    uv run bsf.py ts-to-mp4 --input in.ts --output out.mp4
    uv run bsf.py level --input in.mp4 --output out.mp4 --level 4.1
    uv run bsf.py strip-sei --input in.mp4 --output clean.mp4
    uv run bsf.py trace --input in.mp4 --stream v:0
    uv run bsf.py zero-ts --input in.mp4 --output zero.mp4
    uv run bsf.py fix-packed-bframes --input old.avi --output fixed.mp4 --dry-run
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# ffprobe helpers
# ---------------------------------------------------------------------------


def probe_codec(path: Path, stream: str = "v:0") -> str | None:
    """Return the codec_name for a given stream specifier, or None on failure."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                stream,
                "-show_entries",
                "stream=codec_name",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None
    data = json.loads(out or "{}")
    streams = data.get("streams", [])
    if not streams:
        return None
    return streams[0].get("codec_name")


def h264_or_hevc_bsf(codec: str | None) -> str:
    """Map ffprobe codec name -> matching *_mp4toannexb bsf."""
    if codec == "h264":
        return "h264_mp4toannexb"
    if codec in ("hevc", "h265"):
        return "hevc_mp4toannexb"
    raise SystemExit(
        f"error: cannot pick mp4toannexb bsf for video codec {codec!r}; "
        "only h264 and hevc are supported"
    )


def h264_or_hevc_metadata(codec: str | None) -> str:
    """Map ffprobe codec name -> matching *_metadata bsf."""
    if codec == "h264":
        return "h264_metadata"
    if codec in ("hevc", "h265"):
        return "hevc_metadata"
    raise SystemExit(
        f"error: cannot pick metadata bsf for video codec {codec!r}; "
        "only h264 and hevc are supported"
    )


# ---------------------------------------------------------------------------
# command builders (one per subcommand)
# ---------------------------------------------------------------------------


def base_cmd(verbose: bool) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info" if verbose else "warning",
        "-stats",
        "-y",
    ]


def cmd_mp4_to_ts(args: argparse.Namespace) -> list[str]:
    codec = probe_codec(args.input, "v:0")
    bsf = h264_or_hevc_bsf(codec)
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:v",
        bsf,
        "-f",
        "mpegts",
        str(args.output),
    ]


def cmd_ts_to_mp4(args: argparse.Namespace) -> list[str]:
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:a",
        "aac_adtstoasc",
        "-movflags",
        "+faststart",
        str(args.output),
    ]


def cmd_fix_packed_bframes(args: argparse.Namespace) -> list[str]:
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:v",
        "mpeg4_unpack_bframes",
        str(args.output),
    ]


def cmd_level(args: argparse.Namespace) -> list[str]:
    codec = probe_codec(args.input, "v:0")
    meta = h264_or_hevc_metadata(codec)
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:v",
        f"{meta}=level={args.level}",
        str(args.output),
    ]


def cmd_strip_sei(args: argparse.Namespace) -> list[str]:
    # H.264 SEI = NAL type 6; HEVC SEI prefix = 39, SEI suffix = 40.
    codec = probe_codec(args.input, "v:0")
    if codec in ("hevc", "h265"):
        types = "39|40"
    else:
        types = "6"
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:v",
        f"filter_units=remove_types={types}",
        str(args.output),
    ]


def cmd_trace(args: argparse.Namespace) -> list[str]:
    # trace_headers writes to stderr when output is discarded.
    flag = "-bsf:a" if args.stream.startswith("a") else "-bsf:v"
    select = "-c:a" if args.stream.startswith("a") else "-c:v"
    return base_cmd(True) + [  # force verbose so trace output shows
        "-i",
        str(args.input),
        "-map",
        f"0:{args.stream}",
        select,
        "copy",
        flag,
        "trace_headers",
        "-f",
        "null",
        "-",
    ]


def cmd_zero_ts(args: argparse.Namespace) -> list[str]:
    return base_cmd(args.verbose) + [
        "-i",
        str(args.input),
        "-c",
        "copy",
        "-bsf:v",
        "setts=ts=PTS-STARTPTS",
        "-bsf:a",
        "setts=ts=PTS-STARTPTS",
        str(args.output),
    ]


SUBCOMMANDS = {
    "mp4-to-ts": cmd_mp4_to_ts,
    "ts-to-mp4": cmd_ts_to_mp4,
    "fix-packed-bframes": cmd_fix_packed_bframes,
    "level": cmd_level,
    "strip-sei": cmd_strip_sei,
    "trace": cmd_trace,
    "zero-ts": cmd_zero_ts,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    def add_common(sp: argparse.ArgumentParser, *, needs_output: bool = True) -> None:
        sp.add_argument("--input", required=True, type=Path, help="Source media file")
        if needs_output:
            sp.add_argument(
                "--output", required=True, type=Path, help="Destination media file"
            )
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the ffmpeg command and exit 0 without running it",
        )
        sp.add_argument(
            "--verbose", action="store_true", help="Pass -loglevel info to ffmpeg"
        )

    add_common(
        sub.add_parser("mp4-to-ts", help="MP4/MOV -> TS with h264/hevc_mp4toannexb")
    )
    add_common(sub.add_parser("ts-to-mp4", help="TS -> MP4 with aac_adtstoasc"))
    add_common(
        sub.add_parser(
            "fix-packed-bframes", help="Apply mpeg4_unpack_bframes to old MP4/AVI"
        )
    )

    sp_level = sub.add_parser(
        "level", help="Rewrite H.264/HEVC Level via *_metadata bsf"
    )
    add_common(sp_level)
    sp_level.add_argument(
        "--level",
        required=True,
        help="Target level, e.g. 4.0 / 4.1 / 5.1 (passed verbatim to *_metadata)",
    )

    add_common(sub.add_parser("strip-sei", help="Drop SEI NAL units via filter_units"))

    sp_trace = sub.add_parser(
        "trace", help="Dump headers via trace_headers (read-only)"
    )
    add_common(sp_trace, needs_output=False)
    sp_trace.add_argument(
        "--stream",
        default="v:0",
        help="Stream specifier to trace, e.g. v:0, a:0 (default: v:0)",
    )

    add_common(sub.add_parser("zero-ts", help="Re-base PTS/DTS to zero via setts"))

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None and not args.dry_run:
        print("error: ffmpeg not on PATH", file=sys.stderr)
        return 2

    builder = SUBCOMMANDS[args.subcommand]
    cmd = builder(args)

    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)

    if args.dry_run:
        return 0

    out = getattr(args, "output", None)
    if out is not None:
        Path(out).parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
