#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
cut.py — ffmpeg helper for trim / segment / concat operations.

Modes:
  trim          Cut a clip between --start and --end (keyframe-fast by default,
                frame-accurate with --accurate).
  segment       Split an input into equal-length pieces via the segment muxer.
  concat-copy   Join inputs with identical codec parameters (stream copy).
  concat-filter Join inputs with mismatched codecs (re-encodes).

All modes support --dry-run (print the command and exit) and --verbose
(stream ffmpeg's stderr instead of capturing it).
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


def build_trim_cmd(
    inp: str, start: str, end: str, out: str, accurate: bool
) -> List[str]:
    cmd = ["ffmpeg", "-y", "-ss", start, "-i", inp, "-to", end]
    if accurate:
        cmd += [
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]
    else:
        cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    cmd += [out]
    return cmd


def build_segment_cmd(inp: str, seconds: float, pattern: str) -> List[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        inp,
        "-c",
        "copy",
        "-map",
        "0",
        "-f",
        "segment",
        "-segment_time",
        str(seconds),
        "-reset_timestamps",
        "1",
        pattern,
    ]


def write_concat_list(inputs: List[str], list_path: Path) -> None:
    """Write an ffmpeg concat-demuxer list file, escaping single quotes."""
    lines: List[str] = []
    for p in inputs:
        absolute = str(Path(p).resolve())
        # Escape ' as '\'' inside a single-quoted string.
        escaped = absolute.replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_concat_copy_cmd(list_path: Path, out: str) -> List[str]:
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        out,
    ]


def build_concat_filter_cmd(inputs: List[str], out: str) -> List[str]:
    cmd: List[str] = ["ffmpeg", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    n = len(inputs)
    streams = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    graph = f"{streams}concat=n={n}:v=1:a=1[v][a]"
    cmd += [
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        out,
    ]
    return cmd


def run(cmd: List[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"$ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    stderr = None if verbose else subprocess.PIPE
    proc = subprocess.run(cmd, stderr=stderr, text=True)
    if proc.returncode != 0:
        if not verbose and proc.stderr:
            sys.stderr.write(proc.stderr)
        print(f"ffmpeg exited with code {proc.returncode}", file=sys.stderr)
    return proc.returncode


def main(argv: List[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run", action="store_true", help="print the ffmpeg command and exit"
    )
    common.add_argument(
        "--verbose", action="store_true", help="stream ffmpeg stderr live"
    )

    parser = argparse.ArgumentParser(
        prog="cut.py",
        description="Trim, segment, and concatenate media with ffmpeg.",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="mode", required=True)

    t = sub.add_parser(
        "trim", help="cut one clip between --start and --end", parents=[common]
    )
    t.add_argument("--input", required=True)
    t.add_argument("--start", required=True, help="HH:MM:SS[.ms] or seconds")
    t.add_argument("--end", required=True, help="HH:MM:SS[.ms] or seconds (absolute)")
    t.add_argument("--output", required=True)
    t.add_argument(
        "--accurate", action="store_true", help="re-encode for frame-accurate cut"
    )

    s = sub.add_parser(
        "segment", help="split an input into N-second pieces", parents=[common]
    )
    s.add_argument("--input", required=True)
    s.add_argument("--seconds", type=float, required=True)
    s.add_argument("--pattern", required=True, help="output pattern e.g. out_%%03d.mp4")

    cc = sub.add_parser(
        "concat-copy", help="join identical-codec files (stream copy)", parents=[common]
    )
    cc.add_argument("--inputs", nargs="+", required=True)
    cc.add_argument("--output", required=True)

    cf = sub.add_parser(
        "concat-filter", help="join mismatched files (re-encodes)", parents=[common]
    )
    cf.add_argument("--inputs", nargs="+", required=True)
    cf.add_argument("--output", required=True)

    args = parser.parse_args(argv)

    if args.mode == "trim":
        cmd = build_trim_cmd(
            args.input, args.start, args.end, args.output, args.accurate
        )
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.mode == "segment":
        cmd = build_segment_cmd(args.input, args.seconds, args.pattern)
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.mode == "concat-copy":
        if len(args.inputs) < 2:
            print("concat-copy needs at least 2 --inputs", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory(prefix="cutpy_") as td:
            list_path = Path(td) / "list.txt"
            write_concat_list(args.inputs, list_path)
            print(f"# list.txt ({list_path}):", file=sys.stderr)
            print(list_path.read_text(), file=sys.stderr)
            cmd = build_concat_copy_cmd(list_path, args.output)
            return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.mode == "concat-filter":
        if len(args.inputs) < 2:
            print("concat-filter needs at least 2 --inputs", file=sys.stderr)
            return 2
        cmd = build_concat_filter_cmd(args.inputs, args.output)
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    parser.error(f"unknown mode {args.mode!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
