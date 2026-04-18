#!/usr/bin/env python3
"""spatial.py — helpers for ffmpeg spatial/binaural audio ops.

Subcommands:
    detect   probe channel layout + count
    binaural 5.1/7.1 -> binaural stereo (headphone or sofalizer)
    upmix    stereo -> 5.1/7.1 via `surround`
    widen    stereo widen + crossfeed
    split    one mono file per input channel
    remap    channel remap via `pan`
    join     N mono inputs -> multichannel output

Stdlib only. Non-interactive. Prints the exact ffmpeg command. `--dry-run`
and `--verbose` honored everywhere.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# ClockWise channel maps for the `headphone` filter. Order matters.
# ---------------------------------------------------------------------------
HEADPHONE_MAPS = {
    "stereo": "FL|FR",
    "2.1": "FL|FR|LFE",
    "3.0": "FL|FR|FC",
    "4.0": "FL|FR|FC|BC",
    "quad": "FL|FR|BL|BR",
    "5.0": "FL|FR|FC|BL|BR",
    "5.1": "FL|FR|FC|LFE|BL|BR",
    "5.1(side)": "FL|FR|FC|LFE|SL|SR",
    "6.1": "FL|FR|FC|LFE|BC|SL|SR",
    "7.1": "FL|FR|FC|LFE|BL|BR|SL|SR",
}


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def run_or_echo(cmd: Sequence[str], dry_run: bool, verbose: bool) -> int:
    """Echo the command; run unless --dry-run."""
    shown = " ".join(shlex.quote(c) for c in cmd)
    print(shown)
    if dry_run:
        return 0
    if verbose:
        eprint(f"[spatial] executing: {shown}")
    try:
        return subprocess.call(list(cmd))
    except FileNotFoundError as exc:
        eprint(f"[spatial] command not found: {exc}")
        return 127


def ffprobe_audio_stream(input_path: str) -> dict:
    """Return dict with keys channels, channel_layout, sample_rate, codec_name.

    Exits 2 on ffprobe failure.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=channels,channel_layout,sample_rate,codec_name",
        "-of",
        "json",
        input_path,
    ]
    try:
        out = subprocess.check_output(cmd, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        eprint(f"[spatial] ffprobe failed: {exc}")
        sys.exit(2)
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        eprint(f"[spatial] ffprobe returned invalid JSON: {exc}")
        sys.exit(2)
    streams = data.get("streams") or []
    if not streams:
        eprint(f"[spatial] no audio stream found in {input_path}")
        sys.exit(2)
    return streams[0]


def guess_layout(stream: dict) -> str:
    """Return layout string, falling back by channel count when unknown."""
    layout = stream.get("channel_layout") or ""
    if layout:
        return layout
    channels = int(stream.get("channels") or 0)
    fallback = {
        1: "mono",
        2: "stereo",
        3: "2.1",
        4: "quad",
        6: "5.1",
        7: "6.1",
        8: "7.1",
    }.get(channels, "")
    return fallback


def headphone_map_for_layout(layout: str) -> Optional[str]:
    if layout in HEADPHONE_MAPS:
        return HEADPHONE_MAPS[layout]
    # Normalize common aliases
    alias = {
        "5.1(back)": "5.1",
        "7.1(wide)": "7.1",
        "7.1(wide-side)": "7.1",
    }.get(layout)
    if alias:
        return HEADPHONE_MAPS[alias]
    return None


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------
def cmd_detect(args: argparse.Namespace) -> int:
    stream = ffprobe_audio_stream(args.input)
    layout = guess_layout(stream) or "unknown"
    channels = stream.get("channels")
    sr = stream.get("sample_rate")
    codec = stream.get("codec_name")
    print(
        json.dumps(
            {
                "input": args.input,
                "codec": codec,
                "channels": channels,
                "channel_layout": stream.get("channel_layout") or "",
                "channel_layout_guess": layout,
                "sample_rate": sr,
            },
            indent=2,
        )
    )
    if not stream.get("channel_layout"):
        eprint(
            "[spatial] note: layout is unset in the file; used fallback from channel count."
        )
    return 0


def cmd_binaural(args: argparse.Namespace) -> int:
    stream = ffprobe_audio_stream(args.input)
    layout = guess_layout(stream)
    channels = int(stream.get("channels") or 0)
    if channels < 3 and not args.sofa:
        eprint(
            f"[spatial] warning: input has {channels} channels; binaural from <3ch is usually pointless."
        )

    af_parts: List[str] = []
    if args.resample:
        af_parts.append(f"aresample={args.resample}")

    if args.sofa:
        af_parts.append(
            f"sofalizer=sofa={args.sofa}:type={args.sofa_type}:radius={args.sofa_radius}"
        )
    else:
        chan_map = args.channel_map or headphone_map_for_layout(layout)
        if not chan_map:
            eprint(
                f"[spatial] cannot determine ClockWise channel map for layout '{layout}'. "
                "Pass --channel-map 'FL|FR|FC|LFE|BL|BR' explicitly."
            )
            return 2
        af_parts.append(f"headphone={chan_map}")

    af = ",".join(af_parts)

    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vn",
        "-af",
        af,
    ]
    if args.codec:
        cmd += ["-c:a", args.codec]
    if args.bitrate:
        cmd += ["-b:a", args.bitrate]
    cmd.append(args.output)
    return run_or_echo(cmd, args.dry_run, args.verbose)


def cmd_upmix(args: argparse.Namespace) -> int:
    layout = args.layout
    af = f"surround=chl_out={layout}"
    if args.level_in is not None:
        af += f":level_in={args.level_in}"
    if args.level_out is not None:
        af += f":level_out={args.level_out}"

    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vn",
        "-af",
        af,
    ]
    if args.codec:
        cmd += ["-c:a", args.codec]
    if args.bitrate:
        cmd += ["-b:a", args.bitrate]
    cmd.append(args.output)
    return run_or_echo(cmd, args.dry_run, args.verbose)


def cmd_widen(args: argparse.Namespace) -> int:
    s = max(0.0, min(1.0, args.strength))
    # Map strength 0..1 to sensible stereowiden + crossfeed knobs.
    delay = 10 + int(20 * s)  # ms
    feedback = 0.15 + 0.25 * s  # 0.15..0.40
    cross = 0.20 + 0.30 * s  # 0.20..0.50
    drymix = 0.95 - 0.15 * s  # 0.95..0.80
    cf_strength = 0.30 + 0.30 * s  # 0.30..0.60
    af = (
        f"stereowiden=delay={delay}:feedback={feedback:.2f}"
        f":crossfeed={cross:.2f}:drymix={drymix:.2f},"
        f"crossfeed=strength={cf_strength:.2f}:range=0.5"
    )
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vn",
        "-af",
        af,
    ]
    if args.codec:
        cmd += ["-c:a", args.codec]
    if args.bitrate:
        cmd += ["-b:a", args.bitrate]
    cmd.append(args.output)
    return run_or_echo(cmd, args.dry_run, args.verbose)


def cmd_split(args: argparse.Namespace) -> int:
    stream = ffprobe_audio_stream(args.input)
    layout = guess_layout(stream)
    channels = int(stream.get("channels") or 0)
    if not layout:
        eprint(f"[spatial] cannot determine layout for {args.input}; pass --layout.")
        return 2
    if args.layout:
        layout = args.layout

    # Derive channel labels for splitting based on layout.
    layout_labels = {
        "mono": ["FC"],
        "stereo": ["FL", "FR"],
        "2.1": ["FL", "FR", "LFE"],
        "quad": ["FL", "FR", "BL", "BR"],
        "5.0": ["FL", "FR", "FC", "BL", "BR"],
        "5.1": ["FL", "FR", "FC", "LFE", "BL", "BR"],
        "5.1(side)": ["FL", "FR", "FC", "LFE", "SL", "SR"],
        "6.1": ["FL", "FR", "FC", "LFE", "BC", "SL", "SR"],
        "7.1": ["FL", "FR", "FC", "LFE", "BL", "BR", "SL", "SR"],
    }.get(layout)

    if not layout_labels:
        eprint(f"[spatial] unsupported layout for split: {layout}")
        return 2
    if len(layout_labels) != channels:
        eprint(
            f"[spatial] channel count {channels} does not match layout '{layout}' "
            f"({len(layout_labels)} labels). Continuing."
        )

    split_pads = "".join(f"[{lbl}]" for lbl in layout_labels)
    fc = f"[0:a]channelsplit=channel_layout={layout}{split_pads}"

    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-filter_complex",
        fc,
    ]
    for idx, lbl in enumerate(layout_labels):
        out_path = (
            args.output_pattern % idx
            if "%" in args.output_pattern
            else args.output_pattern.replace("{ch}", lbl).replace("{i}", str(idx))
        )
        cmd += ["-map", f"[{lbl}]", out_path]
    return run_or_echo(cmd, args.dry_run, args.verbose)


def cmd_remap(args: argparse.Namespace) -> int:
    # args.map expected format: "LAYOUT:EXPR"  e.g. "mono:c0=0.5*c0+0.5*c1"
    if ":" not in args.map:
        eprint("[spatial] --map must be 'LAYOUT:EXPR'")
        return 2
    layout, expr = args.map.split(":", 1)
    af = f"pan={layout}|{expr}"
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vn",
        "-af",
        af,
    ]
    if args.codec:
        cmd += ["-c:a", args.codec]
    if args.bitrate:
        cmd += ["-b:a", args.bitrate]
    cmd.append(args.output)
    return run_or_echo(cmd, args.dry_run, args.verbose)


def cmd_join(args: argparse.Namespace) -> int:
    if len(args.inputs) < 2:
        eprint("[spatial] join requires at least two input files")
        return 2
    layout = args.layout
    # Build amerge + pan graph.
    n = len(args.inputs)
    merge_inputs = "".join(f"[{i}:a]" for i in range(n))
    pan_assign = "|".join(f"c{i}=c{i}" for i in range(n))
    fc = f"{merge_inputs}amerge=inputs={n},pan={layout}|{pan_assign}[a]"

    cmd = ["ffmpeg", "-y" if args.overwrite else "-n"]
    for f in args.inputs:
        cmd += ["-i", f]
    cmd += ["-filter_complex", fc, "-map", "[a]"]
    if args.codec:
        cmd += ["-c:a", args.codec]
    if args.bitrate:
        cmd += ["-b:a", args.bitrate]
    cmd.append(args.output)
    return run_or_echo(cmd, args.dry_run, args.verbose)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="spatial.py", description=__doc__)
    p.add_argument(
        "--dry-run", action="store_true", help="print command but do not execute"
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="verbose diagnostics to stderr"
    )
    p.add_argument(
        "--overwrite", action="store_true", help="pass -y to ffmpeg (overwrite outputs)"
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect", help="probe channel layout + count")
    d.add_argument("--input", required=True)
    d.set_defaults(func=cmd_detect)

    b = sub.add_parser("binaural", help="5.1/7.1 -> binaural stereo")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    b.add_argument(
        "--sofa", help="path to a SOFA HRTF file; use sofalizer instead of headphone"
    )
    b.add_argument(
        "--sofa-type",
        default="freq",
        help="sofalizer type: freq or time (default freq)",
    )
    b.add_argument("--sofa-radius", default="1", help="sofalizer listener radius (m)")
    b.add_argument(
        "--channel-map",
        help="override ClockWise channel map (e.g. 'FL|FR|FC|LFE|BL|BR')",
    )
    b.add_argument(
        "--resample", help="insert aresample=RATE before binaural (e.g. 48000)"
    )
    b.add_argument("--codec", default="aac")
    b.add_argument("--bitrate", default="192k")
    b.set_defaults(func=cmd_binaural)

    u = sub.add_parser("upmix", help="stereo -> 5.1/7.1 via `surround`")
    u.add_argument("--input", required=True)
    u.add_argument("--output", required=True)
    u.add_argument("--layout", default="5.1", help="output layout (default 5.1)")
    u.add_argument("--level-in", type=float, default=None)
    u.add_argument("--level-out", type=float, default=None)
    u.add_argument("--codec", default="ac3")
    u.add_argument("--bitrate", default="448k")
    u.set_defaults(func=cmd_upmix)

    w = sub.add_parser("widen", help="stereo widen + crossfeed")
    w.add_argument("--input", required=True)
    w.add_argument("--output", required=True)
    w.add_argument(
        "--strength", type=float, default=0.5, help="0..1 widening amount (default 0.5)"
    )
    w.add_argument("--codec", default=None)
    w.add_argument("--bitrate", default=None)
    w.set_defaults(func=cmd_widen)

    s = sub.add_parser("split", help="one mono file per input channel")
    s.add_argument("--input", required=True)
    s.add_argument(
        "--output-pattern",
        required=True,
        help="printf-style pattern (e.g. 'ch_%%d.wav') or templated ('{ch}.wav' / '{i}.wav')",
    )
    s.add_argument("--layout", help="override detected layout (e.g. 5.1)")
    s.set_defaults(func=cmd_split)

    r = sub.add_parser("remap", help="channel remap via `pan`")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    r.add_argument(
        "--map",
        required=True,
        help="LAYOUT:EXPR, e.g. 'mono:c0=0.5*c0+0.5*c1' or 'stereo:c0=c0|c1=c0'",
    )
    r.add_argument("--codec", default=None)
    r.add_argument("--bitrate", default=None)
    r.set_defaults(func=cmd_remap)

    j = sub.add_parser("join", help="N mono inputs -> multichannel output")
    j.add_argument(
        "--inputs", nargs="+", required=True, help="one or more input files (mono each)"
    )
    j.add_argument("--output", required=True)
    j.add_argument("--layout", default="stereo", help="output channel layout")
    j.add_argument("--codec", default=None)
    j.add_argument("--bitrate", default=None)
    j.set_defaults(func=cmd_join)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
