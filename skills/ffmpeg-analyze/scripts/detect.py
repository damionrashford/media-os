#!/usr/bin/env python3
"""Detect-and-act utilities for ffmpeg analysis filters.

Subcommands:
  crop       — autocrop via cropdetect; prints ready-to-use `crop=W:H:X:Y`.
  silences   — silencedetect; JSON array of {start, end, duration}.
  blacks     — blackdetect; JSON array of {start, end, duration}.
  freezes    — freezedetect; JSON array of {start, end, duration}.
  scenes     — scdet; JSON array of {time, score}.
  interlace  — idet; summary JSON with TFF/BFF/progressive/undetermined.
  stats      — signalstats summary (min/max/avg across frames).
  volume     — volumedetect; JSON with mean_db, max_db.

All subcommands wrap `ffmpeg` (stdlib only, non-interactive). Run with
`--dry-run` to see the exact command without executing it. `--verbose`
prints the raw ffmpeg stderr before parsing.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any


def _have_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        sys.exit(2)


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> str:
    """Run ffmpeg, return combined stderr+stdout text."""
    if dry_run:
        print("DRY RUN:", " ".join(shlex.quote(c) for c in cmd))
        return ""
    if verbose:
        print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    output = (proc.stderr or "") + (proc.stdout or "")
    if verbose:
        sys.stderr.write(output)
        sys.stderr.flush()
    # ffmpeg exits 0 on success even when filter matches found 0 results.
    # Non-zero is real (unreadable file, bad filter) — report it.
    if proc.returncode != 0 and not dry_run:
        print(
            f"warning: ffmpeg exited {proc.returncode}; output may be partial",
            file=sys.stderr,
        )
    return output


def _base_cmd(
    input_path: str,
    *,
    ss: float | None = None,
    t: float | None = None,
) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    cmd += ["-i", input_path]
    if t is not None:
        cmd += ["-t", str(t)]
    return cmd


# ---------------- crop ----------------

_CROP_RE = re.compile(r"crop=(\d+:\d+:\d+:\d+)")


def cmd_crop(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input, ss=args.sample_at, t=args.sample_duration)
    cmd += [
        "-vf",
        f"cropdetect=limit={args.limit}:round={args.round}",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    matches = _CROP_RE.findall(out)
    if not matches:
        print("error: cropdetect returned no crop= rectangles", file=sys.stderr)
        return 1
    final = matches[-1]
    print(f"crop={final}")
    return 0


# ---------------- silences ----------------

_SIL_START_RE = re.compile(r"silence_start:\s*([\-\d.]+)")
_SIL_END_RE = re.compile(
    r"silence_end:\s*([\-\d.]+)\s*\|\s*silence_duration:\s*([\-\d.]+)"
)


def cmd_silences(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += [
        "-af",
        f"silencedetect=noise={args.noise_db}dB:d={args.min_duration}",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    starts = [float(x) for x in _SIL_START_RE.findall(out)]
    ends_durs = [(float(e), float(d)) for e, d in _SIL_END_RE.findall(out)]
    results: list[dict[str, float]] = []
    # Pair them up. Any trailing start without end → silence to EOF (duration
    # unknown from this pass).
    for i, start in enumerate(starts):
        if i < len(ends_durs):
            end, dur = ends_durs[i]
            results.append({"start": start, "end": end, "duration": dur})
        else:
            results.append({"start": start, "end": -1.0, "duration": -1.0})
    print(json.dumps(results, indent=2))
    return 0


# ---------------- blacks ----------------

_BLACK_RE = re.compile(
    r"black_start:([\-\d.]+)\s+black_end:([\-\d.]+)\s+black_duration:([\-\d.]+)"
)


def cmd_blacks(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += [
        "-vf",
        f"blackdetect=d={args.min_duration}:pix_th={args.pix_thresh}",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    results = [
        {"start": float(s), "end": float(e), "duration": float(d)}
        for s, e, d in _BLACK_RE.findall(out)
    ]
    print(json.dumps(results, indent=2))
    return 0


# ---------------- freezes ----------------

_FREEZE_RE = re.compile(
    r"freeze_start:\s*([\-\d.]+).*?freeze_duration:\s*([\-\d.]+).*?freeze_end:\s*([\-\d.]+)",
    re.DOTALL,
)


def cmd_freezes(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += [
        "-vf",
        f"freezedetect=n={args.noise}:d={args.min_duration}",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    # freezedetect prints three separate lines per event; parse them
    # individually and zip by index.
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\-\d.]+)", out)]
    durs = [float(x) for x in re.findall(r"freeze_duration:\s*([\-\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([\-\d.]+)", out)]
    results: list[dict[str, float]] = []
    for i, start in enumerate(starts):
        results.append(
            {
                "start": start,
                "duration": durs[i] if i < len(durs) else -1.0,
                "end": ends[i] if i < len(ends) else -1.0,
            }
        )
    print(json.dumps(results, indent=2))
    return 0


# ---------------- scenes ----------------

_SCDET_LINE_RE = re.compile(
    r"lavfi\.scd\.score=([\d.]+).*?lavfi\.scd\.time=([\d.]+)",
    re.DOTALL,
)
# When using `scdet=s=1:t=N`, ffmpeg prints a line like:
#   [Parsed_scdet_0 @ ...] lavfi.scd.score: 14.24 lavfi.scd.time: 23.458
_SCDET_SIMPLE_RE = re.compile(
    r"lavfi\.scd\.score:\s*([\d.]+).*?lavfi\.scd\.time:\s*([\d.]+)"
)


def cmd_scenes(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += [
        "-vf",
        f"scdet=s=1:t={args.threshold}",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    pairs = _SCDET_SIMPLE_RE.findall(out)
    if not pairs:
        pairs = _SCDET_LINE_RE.findall(out)
    results = [{"time": float(t), "score": float(s)} for s, t in pairs]
    print(json.dumps(results, indent=2))
    return 0


# ---------------- interlace ----------------

_IDET_MULTI_RE = re.compile(
    r"Multi frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)"
)
_IDET_SINGLE_RE = re.compile(
    r"Single frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)"
)


def _decide(tff: int, bff: int, prog: int, undet: int) -> str:
    total = tff + bff + prog + undet
    if total == 0:
        return "unknown"
    if prog / total > 0.9:
        return "progressive"
    if tff > bff and tff > prog:
        return "interlaced-tff"
    if bff > tff and bff > prog:
        return "interlaced-bff"
    return "mixed-or-ambiguous"


def cmd_interlace(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += ["-vf", "idet", "-f", "null", "-"]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    result: dict[str, Any] = {}
    m_multi = _IDET_MULTI_RE.search(out)
    m_single = _IDET_SINGLE_RE.search(out)
    if m_multi:
        tff, bff, prog, undet = (int(x) for x in m_multi.groups())
        result["multi_frame"] = {
            "tff": tff,
            "bff": bff,
            "progressive": prog,
            "undetermined": undet,
        }
        result["decision"] = _decide(tff, bff, prog, undet)
    if m_single:
        tff, bff, prog, undet = (int(x) for x in m_single.groups())
        result["single_frame"] = {
            "tff": tff,
            "bff": bff,
            "progressive": prog,
            "undetermined": undet,
        }
    if not result:
        print("error: idet produced no summary (need more frames)", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


# ---------------- signalstats summary ----------------

_SIGSTAT_KEYS = (
    "YAVG",
    "YMIN",
    "YMAX",
    "UAVG",
    "UMIN",
    "UMAX",
    "VAVG",
    "VMIN",
    "VMAX",
    "SATAVG",
    "SATMIN",
    "SATMAX",
    "HUEAVG",
    "HUEMED",
    "TOUT",
    "VREP",
)


def cmd_stats(args: argparse.Namespace) -> int:
    # Use metadata=mode=print to dump all lavfi.signalstats.* keys to stderr.
    cmd = _base_cmd(args.input)
    cmd += [
        "-vf",
        "signalstats,metadata=mode=print",
        "-an",
        "-f",
        "null",
        "-",
    ]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    # Aggregate per-key across all frames.
    acc: dict[str, list[float]] = {k: [] for k in _SIGSTAT_KEYS}
    for key in _SIGSTAT_KEYS:
        pattern = re.compile(rf"lavfi\.signalstats\.{key}=([\-\d.]+)")
        acc[key] = [float(x) for x in pattern.findall(out)]
    summary: dict[str, Any] = {"frame_count": max(len(v) for v in acc.values() or [[]])}
    for key, values in acc.items():
        if not values:
            continue
        summary[key] = {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "n": len(values),
        }
    print(json.dumps(summary, indent=2))
    return 0


# ---------------- volume ----------------

_MEAN_RE = re.compile(r"mean_volume:\s*([\-\d.]+)\s*dB")
_MAX_RE = re.compile(r"max_volume:\s*([\-\d.]+)\s*dB")


def cmd_volume(args: argparse.Namespace) -> int:
    cmd = _base_cmd(args.input)
    cmd += ["-af", "volumedetect", "-vn", "-f", "null", "-"]
    out = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    mean = _MEAN_RE.search(out)
    mx = _MAX_RE.search(out)
    result = {
        "mean_db": float(mean.group(1)) if mean else None,
        "max_db": float(mx.group(1)) if mx else None,
    }
    print(json.dumps(result, indent=2))
    return 0


# ---------------- CLI ----------------


def _common_flags() -> argparse.ArgumentParser:
    """Parent parser so --dry-run/--verbose work either side of the subcommand."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--dry-run", action="store_true", help="print command, don't run"
    )
    parent.add_argument("--verbose", action="store_true", help="echo ffmpeg stderr")
    return parent


def build_parser() -> argparse.ArgumentParser:
    parents = [_common_flags()]
    p = argparse.ArgumentParser(
        prog="detect.py",
        description="ffmpeg detect-and-act utilities (stdlib only).",
        parents=parents,
    )
    sub = p.add_subparsers(dest="subcommand", required=True)

    sp = sub.add_parser("crop", help="autocrop via cropdetect", parents=parents)
    sp.add_argument("--input", required=True)
    sp.add_argument("--sample-at", type=float, default=10.0, help="seek seconds")
    sp.add_argument("--sample-duration", type=float, default=120.0, help="duration")
    sp.add_argument("--limit", type=int, default=24, help="black threshold 0-255")
    sp.add_argument("--round", type=int, default=2, help="dim rounding (2/4/16)")
    sp.set_defaults(func=cmd_crop)

    sp = sub.add_parser("silences", help="silencedetect -> JSON", parents=parents)
    sp.add_argument("--input", required=True)
    sp.add_argument("--noise-db", type=float, default=-30.0)
    sp.add_argument("--min-duration", type=float, default=0.5)
    sp.set_defaults(func=cmd_silences)

    sp = sub.add_parser("blacks", help="blackdetect -> JSON", parents=parents)
    sp.add_argument("--input", required=True)
    sp.add_argument("--min-duration", type=float, default=1.0)
    sp.add_argument("--pix-thresh", type=float, default=0.1)
    sp.set_defaults(func=cmd_blacks)

    sp = sub.add_parser("freezes", help="freezedetect -> JSON", parents=parents)
    sp.add_argument("--input", required=True)
    sp.add_argument("--noise", type=float, default=0.001)
    sp.add_argument("--min-duration", type=float, default=0.5)
    sp.set_defaults(func=cmd_freezes)

    sp = sub.add_parser("scenes", help="scdet -> JSON list of cuts", parents=parents)
    sp.add_argument("--input", required=True)
    sp.add_argument("--threshold", type=float, default=10.0, help="0-100 scale")
    sp.set_defaults(func=cmd_scenes)

    sp = sub.add_parser("interlace", help="idet summary", parents=parents)
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_interlace)

    sp = sub.add_parser(
        "stats", help="signalstats summary (min/max/avg)", parents=parents
    )
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("volume", help="volumedetect mean/max dB", parents=parents)
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_volume)

    return p


def main(argv: list[str] | None = None) -> int:
    _have_ffmpeg()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
