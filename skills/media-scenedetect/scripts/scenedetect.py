#!/usr/bin/env python3
"""Thin wrapper over the PySceneDetect CLI (`scenedetect`).

Subcommands:
  check        — verify scenedetect is installed and on PATH.
  detect       — run a detector and print scene list as JSON.
  split        — split video at scene cuts (optionally stream-copy via mkvmerge).
  thumbnails   — save N images per scene into a directory.
  html-report  — generate self-contained HTML scene report.
  chapters     — emit an ffmetadata chapter file derived from detected scenes.

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence


# ---------------------------------------------------------------------------
# helpers


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(f"[scenedetect.py] {msg}", file=sys.stderr)


def _fmt_cmd(argv: Sequence[str]) -> str:
    def q(a: str) -> str:
        if any(c in a for c in " \t\"'\\"):
            return "'" + a.replace("'", "'\\''") + "'"
        return a

    return " ".join(q(a) for a in argv)


def _run(
    argv: Sequence[str], dry_run: bool, verbose: bool, capture: bool = False
) -> subprocess.CompletedProcess:
    print(f"+ {_fmt_cmd(argv)}", file=sys.stderr)
    if dry_run:
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    _log(verbose, f"executing (capture={capture})")
    return subprocess.run(
        argv,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def _require_input(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        sys.exit(2)
    return p


def _detector_args(
    method: str, threshold: float | None, min_duration: float | None
) -> list[str]:
    detectors = {
        "content": "detect-content",
        "adaptive": "detect-adaptive",
        "threshold": "detect-threshold",
        "hash": "detect-hash",
    }
    if method not in detectors:
        print(
            f"error: unknown --method {method!r}; choose from " f"{sorted(detectors)}",
            file=sys.stderr,
        )
        sys.exit(2)
    args: list[str] = [detectors[method]]
    if threshold is not None:
        args += ["-t", str(threshold)]
    if min_duration is not None:
        args += ["-m", str(min_duration)]
    return args


def _timecode_to_seconds(tc: str) -> float:
    # PySceneDetect timecode format: HH:MM:SS.mmm
    parts = tc.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


# ---------------------------------------------------------------------------
# subcommand: check


def cmd_check(args: argparse.Namespace) -> int:
    exe = shutil.which("scenedetect")
    if not exe:
        print("scenedetect: NOT FOUND on PATH")
        print("install: pip install 'scenedetect[opencv]'")
        return 1
    print(f"scenedetect: {exe}")
    cp = _run([exe, "version"], dry_run=False, verbose=args.verbose, capture=True)
    if cp.stdout:
        sys.stdout.write(cp.stdout.decode(errors="replace"))
    ff = shutil.which("ffmpeg") or "<missing>"
    mk = shutil.which("mkvmerge") or "<missing>"
    print(f"ffmpeg:      {ff}")
    print(f"mkvmerge:    {mk}")
    return cp.returncode


# ---------------------------------------------------------------------------
# subcommand: detect


def _parse_scenes_csv(csv_text: str) -> list[dict]:
    # PySceneDetect list-scenes CSV has one header row that starts with
    # "Timecode List:" then "Scene Number, Start Frame, ...".
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    # find header containing "Scene Number"
    start = 0
    for i, ln in enumerate(lines):
        if "Scene Number" in ln:
            start = i
            break
    reader = csv.DictReader(lines[start:])
    scenes: list[dict] = []
    for row in reader:

        def g(k: str, default: str = "") -> str:
            for key, val in row.items():
                if key and key.strip().lower() == k.lower():
                    return (val or default).strip()
            return default

        try:
            scenes.append(
                {
                    "scene": int(g("Scene Number") or 0),
                    "start_frame": int(g("Start Frame") or 0),
                    "start_seconds": float(g("Start Time (seconds)") or 0.0),
                    "start_timecode": g("Start Timecode"),
                    "end_frame": int(g("End Frame") or 0),
                    "end_seconds": float(g("End Time (seconds)") or 0.0),
                    "end_timecode": g("End Timecode"),
                    "length_frames": int(g("Length (frames)") or 0),
                    "length_seconds": float(g("Length (seconds)") or 0.0),
                    "length_timecode": g("Length (timecode)"),
                }
            )
        except ValueError:
            # skip malformed row
            continue
    return scenes


def _run_list_scenes(
    input_path: Path,
    method: str,
    threshold: float | None,
    min_duration: float | None,
    downscale: int | None,
    start: str | None,
    end: str | None,
    duration: str | None,
    dry_run: bool,
    verbose: bool,
) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "scenes.csv"
        argv: list[str] = ["scenedetect", "-i", str(input_path)]
        if downscale:
            argv += ["--downscale", str(downscale)]
        if start:
            argv += ["--start", start]
        if end:
            argv += ["--end", end]
        if duration:
            argv += ["--duration", duration]
        argv += _detector_args(method, threshold, min_duration)
        argv += ["list-scenes", "--no-output-file", "-o", str(tmp), "-f", csv_path.name]
        cp = _run(argv, dry_run=dry_run, verbose=verbose, capture=True)
        if dry_run:
            return []
        if cp.returncode != 0:
            sys.stderr.write(cp.stderr.decode(errors="replace"))
            sys.exit(cp.returncode)
        # Recent scenedetect writes to <outdir>/<video>-Scenes.csv; search.
        candidates = list(Path(tmp).glob("*.csv"))
        if not candidates:
            print("error: no CSV produced by list-scenes", file=sys.stderr)
            sys.exit(1)
        text = candidates[0].read_text()
        return _parse_scenes_csv(text)


def cmd_detect(args: argparse.Namespace) -> int:
    input_path = _require_input(args.input)
    scenes = _run_list_scenes(
        input_path,
        args.method,
        args.threshold,
        args.min_duration,
        args.downscale,
        args.start,
        args.end,
        args.duration,
        args.dry_run,
        args.verbose,
    )
    json.dump(
        {
            "input": str(input_path),
            "method": args.method,
            "threshold": args.threshold,
            "min_duration": args.min_duration,
            "scene_count": len(scenes),
            "scenes": scenes,
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# subcommand: split


def cmd_split(args: argparse.Namespace) -> int:
    input_path = _require_input(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    argv: list[str] = ["scenedetect", "-i", str(input_path), "-o", str(outdir)]
    argv += _detector_args(args.method, args.threshold, args.min_duration)
    argv += ["split-video"]
    if args.stream_copy:
        argv += ["-m"]  # use mkvmerge (stream-copy at keyframes)
    cp = _run(argv, dry_run=args.dry_run, verbose=args.verbose)
    return cp.returncode


# ---------------------------------------------------------------------------
# subcommand: thumbnails


def cmd_thumbnails(args: argparse.Namespace) -> int:
    input_path = _require_input(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    argv: list[str] = ["scenedetect", "-i", str(input_path), "-o", str(outdir)]
    argv += _detector_args(args.method, args.threshold, args.min_duration)
    argv += ["save-images", "-n", str(args.per_scene)]
    cp = _run(argv, dry_run=args.dry_run, verbose=args.verbose)
    return cp.returncode


# ---------------------------------------------------------------------------
# subcommand: html-report


def cmd_html_report(args: argparse.Namespace) -> int:
    input_path = _require_input(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    argv: list[str] = ["scenedetect", "-i", str(input_path)]
    argv += _detector_args(args.method, args.threshold, args.min_duration)
    argv += [
        "list-scenes",
        "save-images",
        "export-html",
        "-f",
        str(out.name),
        "-o",
        str(out.parent or "."),
    ]
    cp = _run(argv, dry_run=args.dry_run, verbose=args.verbose)
    return cp.returncode


# ---------------------------------------------------------------------------
# subcommand: chapters


def _scenes_to_ffmetadata(scenes: Iterable[dict]) -> str:
    buf = io.StringIO()
    buf.write(";FFMETADATA1\n")
    for s in scenes:
        start_ms = int(round(s["start_seconds"] * 1000))
        end_ms = int(round(s["end_seconds"] * 1000))
        if end_ms <= start_ms:
            end_ms = start_ms + 1
        buf.write("[CHAPTER]\n")
        buf.write("TIMEBASE=1/1000\n")
        buf.write(f"START={start_ms}\n")
        buf.write(f"END={end_ms}\n")
        buf.write(f"title=Scene {s['scene']:03d}\n")
    return buf.getvalue()


def cmd_chapters(args: argparse.Namespace) -> int:
    input_path = _require_input(args.input)
    scenes = _run_list_scenes(
        input_path,
        args.method,
        args.threshold,
        args.min_duration,
        args.downscale,
        args.start,
        args.end,
        args.duration,
        args.dry_run,
        args.verbose,
    )
    text = _scenes_to_ffmetadata(scenes)
    if args.dry_run:
        print(f"# would write {len(scenes)} chapters to {args.output}", file=sys.stderr)
        sys.stdout.write(text)
        return 0
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"wrote {len(scenes)} chapters -> {out}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# argparse


def _add_detector_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--method",
        default="content",
        choices=["content", "adaptive", "threshold", "hash"],
        help="detector (default: content)",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="detector threshold (detector-specific)",
    )
    p.add_argument(
        "--min-duration",
        type=float,
        default=None,
        help="minimum scene duration in seconds",
    )


def _add_range_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--downscale", type=int, default=None, help="process every Nth pixel (speed-up)"
    )
    p.add_argument("--start", default=None, help="start timecode HH:MM:SS[.mmm]")
    p.add_argument("--end", default=None, help="end timecode HH:MM:SS[.mmm]")
    p.add_argument("--duration", default=None, help="analyze duration HH:MM:SS[.mmm]")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scenedetect.py",
        description="Wrapper over the scenedetect CLI.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print commands without executing"
    )
    p.add_argument("--verbose", action="store_true", help="verbose logging to stderr")

    sub = p.add_subparsers(dest="subcommand", required=True)

    sp = sub.add_parser("check", help="verify scenedetect is installed")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("detect", help="detect scenes and print JSON scene list")
    sp.add_argument("--input", "-i", required=True)
    _add_detector_flags(sp)
    _add_range_flags(sp)
    sp.set_defaults(func=cmd_detect)

    sp = sub.add_parser("split", help="split video at detected scenes")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--outdir", "-o", required=True)
    _add_detector_flags(sp)
    sp.add_argument(
        "--stream-copy",
        action="store_true",
        help="use mkvmerge stream-copy (-m) instead of " "ffmpeg re-encode",
    )
    sp.set_defaults(func=cmd_split)

    sp = sub.add_parser("thumbnails", help="save images per scene")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--outdir", "-o", required=True)
    sp.add_argument(
        "--per-scene",
        "-n",
        type=int,
        default=3,
        help="images per scene (default 3: first/mid/last)",
    )
    _add_detector_flags(sp)
    sp.set_defaults(func=cmd_thumbnails)

    sp = sub.add_parser("html-report", help="write self-contained HTML report")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    _add_detector_flags(sp)
    sp.set_defaults(func=cmd_html_report)

    sp = sub.add_parser("chapters", help="emit ffmetadata chapter file from scene list")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    _add_detector_flags(sp)
    _add_range_flags(sp)
    sp.set_defaults(func=cmd_chapters)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
