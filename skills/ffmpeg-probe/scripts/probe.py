#!/usr/bin/env python3
"""
probe.py — stdlib-only wrapper around `ffprobe` for common inspection tasks.

Subcommands:
  summary   Human-readable container / video / audio summary.
  json      Full `-show_format -show_streams` JSON dump to stdout.
  field     Get a single field by dotted path (e.g. stream.v.fps).
  keyframes List keyframe PTS times (seconds, one per line).
  hdr       Print SDR / HDR10 / HLG / DolbyVision.
  compare   Side-by-side field diff of two inputs.

All subcommands accept `--verbose` (print the ffprobe command to stderr) and
`--dry-run` (print the command instead of running it). No network, no
third-party deps, no prompts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


# --------------------------------------------------------------------------- #
# ffprobe invocation
# --------------------------------------------------------------------------- #


def _ensure_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        print("ERROR: ffprobe not found in PATH. Install ffmpeg.", file=sys.stderr)
        sys.exit(127)
    return path


def _run(cmd: list[str], *, verbose: bool, dry_run: bool) -> str:
    if verbose or dry_run:
        print("$ " + " ".join(_shell_quote(c) for c in cmd), file=sys.stderr)
    if dry_run:
        return ""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr or "")
        sys.exit(e.returncode)
    return result.stdout


def _shell_quote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'$`\\"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


def _probe_json(
    inp: str,
    *,
    extra: list[str] | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    ffprobe = _ensure_ffprobe()
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-hide_banner",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
    ]
    if extra:
        cmd.extend(extra)
    cmd.append(inp)
    out = _run(cmd, verbose=verbose, dry_run=dry_run)
    if dry_run:
        return {}
    return json.loads(out or "{}")


# --------------------------------------------------------------------------- #
# helpers on the parsed JSON
# --------------------------------------------------------------------------- #


def _streams(data: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [s for s in data.get("streams", []) if s.get("codec_type") == kind]


def _fps(stream: dict[str, Any]) -> float | None:
    r = stream.get("r_frame_rate") or stream.get("avg_frame_rate") or "0/0"
    try:
        num, den = r.split("/")
        num, den = int(num), int(den)
        if den == 0:
            return None
        return num / den
    except (ValueError, AttributeError):
        return None


def _fmt_bytes(n: Any) -> str:
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "N/A"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if v < 1024:
            return f"{v:.2f} {unit}"
        v /= 1024
    return f"{v:.2f} PiB"


def _fmt_dur(s: Any) -> str:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return "N/A"
    h = int(v // 3600)
    m = int((v % 3600) // 60)
    sec = v - (h * 3600 + m * 60)
    return f"{h:02d}:{m:02d}:{sec:06.3f}"


def _fmt_bitrate(b: Any) -> str:
    try:
        v = int(b)
    except (TypeError, ValueError):
        return "N/A"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} Mb/s"
    if v >= 1_000:
        return f"{v / 1_000:.1f} kb/s"
    return f"{v} b/s"


def _get_field(data: dict[str, Any], query: str) -> Any:
    """Dotted-path lookup. Supported prefixes:
        format.<key>
        stream.v[.<key>]      (first video stream)
        stream.a[.<key>]      (first audio stream)
        stream.s[.<key>]      (first subtitle stream)
        stream.<idx>[.<key>]  (by original index)
    Special synthetic fields on stream.v: fps, resolution.
    """
    parts = query.split(".")
    if not parts:
        raise KeyError(query)
    head = parts[0]
    if head == "format":
        cur: Any = data.get("format", {})
        for p in parts[1:]:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        return cur
    if head == "stream":
        if len(parts) < 2:
            raise KeyError("stream query needs a selector, e.g. stream.v.width")
        sel = parts[1]
        if sel in ("v", "a", "s"):
            kind = {"v": "video", "a": "audio", "s": "subtitle"}[sel]
            streams = _streams(data, kind)
            if not streams:
                return None
            stream = streams[0]
        else:
            try:
                idx = int(sel)
            except ValueError:
                raise KeyError(f"unknown stream selector: {sel}")
            matches = [s for s in data.get("streams", []) if s.get("index") == idx]
            if not matches:
                return None
            stream = matches[0]
        if len(parts) == 2:
            return stream
        leaf = ".".join(parts[2:])
        # synthetic
        if leaf == "fps":
            return _fps(stream)
        if leaf == "resolution":
            w, h = stream.get("width"), stream.get("height")
            return f"{w}x{h}" if w and h else None
        cur = stream
        for p in parts[2:]:
            if isinstance(cur, dict):
                cur = cur.get(p)
            elif isinstance(cur, list):
                try:
                    cur = cur[int(p)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return cur
    raise KeyError(f"unknown query root: {head!r} (use 'format' or 'stream')")


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #


def cmd_summary(args: argparse.Namespace) -> int:
    data = _probe_json(args.input, verbose=args.verbose, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    fmt = data.get("format", {})
    print(f"File:       {fmt.get('filename', args.input)}")
    print(f"Container:  {fmt.get('format_long_name', fmt.get('format_name', 'N/A'))}")
    print(f"Duration:   {_fmt_dur(fmt.get('duration'))}")
    print(f"Size:       {_fmt_bytes(fmt.get('size'))}")
    print(f"Bitrate:    {_fmt_bitrate(fmt.get('bit_rate'))}")
    nb = len(data.get("streams", []))
    print(f"Streams:    {nb}")
    for s in _streams(data, "video"):
        fps = _fps(s)
        fps_s = f"{fps:.3f}" if fps is not None else "N/A"
        print(
            f"  [v:{s.get('index')}] {s.get('codec_name', '?')}"
            f" {s.get('width', '?')}x{s.get('height', '?')}"
            f" {fps_s} fps pix_fmt={s.get('pix_fmt', '?')}"
            f" bitrate={_fmt_bitrate(s.get('bit_rate'))}"
            f" color={s.get('color_space', '?')}/"
            f"{s.get('color_transfer', '?')}/"
            f"{s.get('color_primaries', '?')}"
        )
    for s in _streams(data, "audio"):
        print(
            f"  [a:{s.get('index')}] {s.get('codec_name', '?')}"
            f" {s.get('channels', '?')}ch ({s.get('channel_layout', '?')})"
            f" {s.get('sample_rate', '?')}Hz"
            f" bitrate={_fmt_bitrate(s.get('bit_rate'))}"
        )
    for s in _streams(data, "subtitle"):
        tags = s.get("tags", {}) or {}
        print(
            f"  [s:{s.get('index')}] {s.get('codec_name', '?')}"
            f" lang={tags.get('language', '?')}"
            f" title={tags.get('title', '')!r}"
        )
    return 0


def cmd_json(args: argparse.Namespace) -> int:
    data = _probe_json(args.input, verbose=args.verbose, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    data = _probe_json(args.input, verbose=args.verbose, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    try:
        value = _get_field(data, args.query)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if value is None:
        print("N/A")
        return 1
    if isinstance(value, (dict, list)):
        json.dump(value, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(value)
    return 0


def cmd_keyframes(args: argparse.Namespace) -> int:
    ffprobe = _ensure_ffprobe()
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-hide_banner",
        "-select_streams",
        "v:0",
        "-show_frames",
        "-show_entries",
        "frame=pkt_pts_time,best_effort_timestamp_time,pict_type",
        "-of",
        "json",
        args.input,
    ]
    out = _run(cmd, verbose=args.verbose, dry_run=args.dry_run)
    if args.dry_run:
        return 0
    data = json.loads(out or "{}")
    for f in data.get("frames", []):
        if f.get("pict_type") == "I":
            t = f.get("pkt_pts_time") or f.get("best_effort_timestamp_time")
            if t is not None:
                print(t)
    return 0


def cmd_hdr(args: argparse.Namespace) -> int:
    data = _probe_json(
        args.input,
        extra=[
            "-show_entries",
            "stream=color_transfer,color_primaries,color_space:"
            "stream_side_data_list=side_data_type",
        ],
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return 0
    vids = _streams(data, "video")
    if not vids:
        print("SDR")  # no video → treat as SDR default
        return 0
    v = vids[0]
    transfer = (v.get("color_transfer") or "").lower()
    primaries = (v.get("color_primaries") or "").lower()
    side = v.get("side_data_list") or []
    side_types = {(sd.get("side_data_type") or "").lower() for sd in side}
    if any("dolby vision" in t or "dovi" in t for t in side_types):
        print("DolbyVision")
        return 0
    if transfer == "arib-std-b67":
        print("HLG")
        return 0
    if transfer == "smpte2084" or primaries == "bt2020":
        print("HDR10")
        return 0
    print("SDR")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    if len(args.inputs) != 2:
        print("ERROR: compare requires exactly 2 inputs", file=sys.stderr)
        return 2
    a, b = args.inputs
    da = _probe_json(a, verbose=args.verbose, dry_run=args.dry_run)
    db = _probe_json(b, verbose=args.verbose, dry_run=args.dry_run)
    if args.dry_run:
        return 0

    def row(label: str, va: Any, vb: Any) -> None:
        mark = "  " if va == vb else "!="
        print(f"{mark} {label:<28} {str(va):<30} {str(vb):<30}")

    print(f"   {'field':<28} {a[-30:]:<30} {b[-30:]:<30}")
    fa, fb = da.get("format", {}), db.get("format", {})
    for k in ("format_name", "duration", "size", "bit_rate"):
        row(f"format.{k}", fa.get(k), fb.get(k))
    va = _streams(da, "video")
    vb = _streams(db, "video")
    if va and vb:
        sa, sb = va[0], vb[0]
        for k in (
            "codec_name",
            "width",
            "height",
            "pix_fmt",
            "r_frame_rate",
            "bit_rate",
            "color_space",
            "color_transfer",
            "color_primaries",
        ):
            row(f"v.{k}", sa.get(k), sb.get(k))
        row("v.fps_decimal", _fps(sa), _fps(sb))
    aa = _streams(da, "audio")
    ab = _streams(db, "audio")
    if aa and ab:
        sa, sb = aa[0], ab[0]
        for k in (
            "codec_name",
            "channels",
            "channel_layout",
            "sample_rate",
            "bit_rate",
        ):
            row(f"a.{k}", sa.get(k), sb.get(k))
    return 0


# --------------------------------------------------------------------------- #
# argparse wiring
# --------------------------------------------------------------------------- #


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print the ffprobe command to stderr before running.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffprobe command and exit without running.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="probe.py",
        description="ffprobe wrapper: summary / json / field / keyframes / hdr / compare.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("summary", help="Human-readable summary.")
    p.add_argument("--input", required=True)
    _add_common(p)
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("json", help="Full -show_format -show_streams JSON.")
    p.add_argument("--input", required=True)
    _add_common(p)
    p.set_defaults(func=cmd_json)

    p = sub.add_parser("field", help="Get one field by dotted path.")
    p.add_argument("--input", required=True)
    p.add_argument(
        "--query",
        required=True,
        help="Dotted path: format.duration, stream.v.width, "
        "stream.v.fps, stream.a.channels, stream.5.codec_name.",
    )
    _add_common(p)
    p.set_defaults(func=cmd_field)

    p = sub.add_parser("keyframes", help="List keyframe timestamps (seconds).")
    p.add_argument("--input", required=True)
    _add_common(p)
    p.set_defaults(func=cmd_keyframes)

    p = sub.add_parser("hdr", help="Print SDR / HDR10 / HLG / DolbyVision.")
    p.add_argument("--input", required=True)
    _add_common(p)
    p.set_defaults(func=cmd_hdr)

    p = sub.add_parser("compare", help="Side-by-side field diff of two files.")
    p.add_argument("--inputs", nargs=2, required=True, metavar=("A", "B"))
    _add_common(p)
    p.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
