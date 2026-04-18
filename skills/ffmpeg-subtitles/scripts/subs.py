#!/usr/bin/env python3
"""ffmpeg subtitle helper: burn, mux, extract, convert.

Stdlib only. Non-interactive. Prints the exact ffmpeg command before running
(or only prints it in --dry-run).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Container -> subtitle codec mapping
# -----------------------------------------------------------------------------

MP4_LIKE = {".mp4", ".m4v", ".mov"}
MKV_LIKE = {".mkv"}
WEBM_LIKE = {".webm"}
TS_LIKE = {".ts", ".m2ts", ".mts"}

SRT_LIKE = {".srt"}
ASS_LIKE = {".ass", ".ssa"}
VTT_LIKE = {".vtt"}
SUB_LIKE = {".sub"}

# Standard named colors -> ASS &HAABBGGRR (alpha + BGR, not RGB).
NAMED_COLORS = {
    "white": "&H00FFFFFF",
    "black": "&H00000000",
    "red": "&H000000FF",
    "green": "&H0000FF00",
    "blue": "&H00FF0000",
    "yellow": "&H0000FFFF",
    "cyan": "&H00FFFF00",
    "magenta": "&H00FF00FF",
}


def sub_codec_for_container(ext: str) -> str:
    """Return the appropriate -c:s value for an output container extension."""
    ext = ext.lower()
    if ext in MP4_LIKE:
        return "mov_text"
    if ext in MKV_LIKE:
        return "srt"
    if ext in WEBM_LIKE:
        return "webvtt"
    if ext in TS_LIKE:
        return "dvbsub"
    raise ValueError(f"unknown/unsupported container extension: {ext}")


def escape_filter_path(path: str) -> str:
    """Escape a path for use inside a libavfilter graph.

    Three-level escape: shell already handled by shlex; we add filter-graph
    escaping (backslash before `:` and `\\`) and wrap with single quotes so
    commas/spaces inside the path are safe.
    """
    # Backslash-escape ':' and '\\' per libavfilter rules.
    escaped = path.replace("\\", r"\\").replace(":", r"\:")
    # Single-quote the whole thing so commas, spaces, and the escapes survive.
    return f"'{escaped}'"


def resolve_color(value: str) -> str:
    """Accept 'white' / 'red' / '&H00FFFFFF' / '#RRGGBB' and return ASS format."""
    v = value.strip()
    if v.startswith("&H") or v.startswith("&h"):
        return v
    if v.lower() in NAMED_COLORS:
        return NAMED_COLORS[v.lower()]
    if v.startswith("#") and len(v) == 7:
        rr, gg, bb = v[1:3], v[3:5], v[5:7]
        return f"&H00{bb}{gg}{rr}".upper().replace("X", "x")
    # Fall through: treat as already-ASS.
    return v


# -----------------------------------------------------------------------------
# Mode builders
# -----------------------------------------------------------------------------


def build_burn(args: argparse.Namespace) -> list[str]:
    subs = Path(args.subs)
    out_ext = Path(args.output).suffix.lower()
    if out_ext not in MP4_LIKE | MKV_LIKE | WEBM_LIKE:
        print(
            f"warning: burn-in output container {out_ext} is unusual", file=sys.stderr
        )

    # Pick filter based on subtitle format.
    if subs.suffix.lower() in ASS_LIKE:
        # ASS filter respects the file's own styling; no force_style.
        vf = f"ass={escape_filter_path(str(subs))}"
    else:
        # SRT / VTT / SUB -> subtitles filter, optional force_style.
        style_pairs = [
            f"Fontname={args.font}",
            f"Fontsize={args.size}",
            f"PrimaryColour={resolve_color(args.color)}",
            "OutlineColour=&H80000000",
            "BorderStyle=1",
            "Outline=2",
            "Shadow=0",
            f"MarginV={args.margin_v}",
            "Alignment=2",
        ]
        style = ",".join(style_pairs)
        vf = f"subtitles={escape_filter_path(str(subs))}:force_style='{style}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.video),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(args.output),
    ]
    return cmd


def build_mux(args: argparse.Namespace) -> list[str]:
    out_ext = Path(args.output).suffix.lower()
    codec = sub_codec_for_container(out_ext)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.video),
        "-i",
        str(args.subs),
        "-map",
        "0:v?",
        "-map",
        "0:a?",
        "-map",
        "1:s:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        codec,
    ]
    if args.lang:
        cmd += ["-metadata:s:s:0", f"language={args.lang}"]
    if args.default:
        cmd += ["-disposition:s:0", "default"]
    cmd.append(str(args.output))
    return cmd


def build_extract(args: argparse.Namespace) -> list[str]:
    out_ext = Path(args.output).suffix.lower()
    # Convert to the target format unless user asked to copy.
    if args.copy:
        codec_args = ["-c:s", "copy"]
    elif out_ext in SRT_LIKE:
        codec_args = ["-c:s", "srt"]
    elif out_ext in ASS_LIKE:
        codec_args = ["-c:s", "ass"]
    elif out_ext in VTT_LIKE:
        codec_args = ["-c:s", "webvtt"]
    else:
        codec_args = []  # let ffmpeg infer
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.input),
        "-map",
        f"0:s:{args.stream}",
        *codec_args,
        str(args.output),
    ]
    return cmd


def build_convert(args: argparse.Namespace) -> list[str]:
    in_ext = Path(args.input).suffix.lower()
    out_ext = Path(args.output).suffix.lower()
    if in_ext == out_ext:
        print(
            f"note: input and output both {in_ext}; ffmpeg will re-save",
            file=sys.stderr,
        )
    cmd = ["ffmpeg", "-y"]
    if args.charenc:
        cmd += ["-sub_charenc", args.charenc]
    cmd += ["-i", str(args.input)]
    # Explicit codec when writing to MKV-style sub extensions; for bare .srt /
    # .ass / .vtt, ffmpeg infers fine.
    cmd.append(str(args.output))
    return cmd


# -----------------------------------------------------------------------------
# CLI plumbing
# -----------------------------------------------------------------------------


def run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(pretty)
    if dry_run:
        return 0
    stderr = None if verbose else subprocess.DEVNULL
    return subprocess.run(cmd, stderr=stderr).returncode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="subs.py",
        description="Burn / mux / extract / convert subtitles with ffmpeg.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg command without running it.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Show ffmpeg stderr (progress + warnings).",
    )

    sub = p.add_subparsers(dest="mode", required=True)

    # burn
    b = sub.add_parser("burn", help="Hardcode subtitles into video (re-encodes).")
    b.add_argument("--video", required=True)
    b.add_argument("--subs", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--font", default="Arial")
    b.add_argument("--size", type=int, default=24)
    b.add_argument(
        "--color",
        default="white",
        help="Name ('white'/'red'), #RRGGBB, or ASS &HAABBGGRR.",
    )
    b.add_argument("--margin-v", type=int, default=60)
    b.add_argument("--crf", type=int, default=20)
    b.add_argument("--preset", default="medium")

    # mux
    m = sub.add_parser("mux", help="Soft-embed a subtitle track.")
    m.add_argument("--video", required=True)
    m.add_argument("--subs", required=True)
    m.add_argument("--output", required=True)
    m.add_argument(
        "--lang", default=None, help="ISO-639-2 code, e.g. 'eng', 'fra', 'spa'."
    )
    m.add_argument(
        "--default",
        action="store_true",
        help="Set default disposition on the muxed sub stream.",
    )

    # extract
    e = sub.add_parser("extract", help="Extract an embedded subtitle stream.")
    e.add_argument("--input", required=True)
    e.add_argument(
        "--stream", type=int, default=0, help="Subtitle stream index (0-based)."
    )
    e.add_argument("--output", required=True)
    e.add_argument(
        "--copy", action="store_true", help="Use -c:s copy (requires matching format)."
    )

    # convert
    c = sub.add_parser("convert", help="Convert between subtitle formats.")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument(
        "--charenc",
        default=None,
        help="Source charset, e.g. CP1252, ISO-8859-1, GB18030.",
    )

    args = p.parse_args(argv)

    builders = {
        "burn": build_burn,
        "mux": build_mux,
        "extract": build_extract,
        "convert": build_convert,
    }
    cmd = builders[args.mode](args)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
