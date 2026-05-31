#!/usr/bin/env python3
"""Subtitle synchronization wrapper around alass and ffsubsync.

Subcommands:
  check          Report alass + ffsubsync + ffmpeg availability.
  sync           Auto-sync subtitle to video audio (tool: alass | ffsubsync | auto).
  sync-reference Align subtitle to a known-good reference subtitle.
  shift          Apply a constant time offset (no external tool needed).
  batch-sync     Sync every subtitle in a folder against matching video.

Stdlib only. Non-interactive. Writes SRT-style output (shift) or delegates
to the picked external tool (alass/ffsubsync) which controls format.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

VIDEO_EXTS = {".mkv", ".mp4", ".mov", ".avi", ".ts", ".m4v", ".webm", ".flv", ".wmv"}
SUB_EXTS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}


# --------------------------------------------------------------------------- #
# Utilities                                                                   #
# --------------------------------------------------------------------------- #


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[subsync] {msg}", file=sys.stderr)


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    display = " ".join(_quote(a) for a in cmd)
    _log(f"exec: {display}", verbose or dry_run)
    if dry_run:
        print(display)
        return 0
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 127


def _quote(a: str) -> str:
    if any(c in a for c in " \t\"'\\$"):
        return "'" + a.replace("'", "'\\''") + "'"
    return a


# --------------------------------------------------------------------------- #
# Subcommand: check                                                           #
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    tools = ["alass", "alass-cli", "ffsubsync", "ffmpeg", "ffprobe"]
    any_missing = False
    for t in tools:
        p = _which(t)
        status = p if p else "MISSING"
        print(f"{t:12s} {status}")
        if not p and t in {"ffmpeg"}:
            any_missing = True
    # alass is installed as either alass or alass-cli
    if not (_which("alass") or _which("alass-cli")):
        print("note: alass not found. Install: brew install alass")
    if not _which("ffsubsync"):
        print("note: ffsubsync not found. Install: pip install ffsubsync")
    return 1 if any_missing else 0


# --------------------------------------------------------------------------- #
# Subcommand: sync                                                            #
# --------------------------------------------------------------------------- #


def _alass_bin() -> Optional[str]:
    return _which("alass") or _which("alass-cli")


def _run_alass(
    reference: Path,
    subs: Path,
    output: Path,
    *,
    no_split: bool,
    split_penalty: Optional[float],
    dry_run: bool,
    verbose: bool,
) -> int:
    binp = _alass_bin() or "alass"
    if not _alass_bin() and not dry_run:
        print("error: alass not installed", file=sys.stderr)
        return 127
    cmd = [binp]
    if no_split:
        cmd.append("--no-split")
    if split_penalty is not None:
        cmd += ["--split-penalty", str(split_penalty)]
    cmd += [str(reference), str(subs), str(output)]
    return _run(cmd, dry_run=dry_run, verbose=verbose)


def _run_ffsubsync(
    reference: Path,
    subs: Path,
    output: Path,
    *,
    no_fix_framerate: bool,
    max_offset_seconds: Optional[float],
    dry_run: bool,
    verbose: bool,
) -> int:
    binp = _which("ffsubsync") or "ffsubsync"
    if not _which("ffsubsync") and not dry_run:
        print("error: ffsubsync not installed", file=sys.stderr)
        return 127
    cmd = [binp, str(reference), "-i", str(subs), "-o", str(output)]
    if no_fix_framerate:
        cmd.append("--no-fix-framerate")
    if max_offset_seconds is not None:
        cmd += ["--max-offset-seconds", str(max_offset_seconds)]
    return _run(cmd, dry_run=dry_run, verbose=verbose)


def cmd_sync(args: argparse.Namespace) -> int:
    video = Path(args.video)
    subs = Path(args.subs)
    output = Path(args.output)
    if not args.dry_run:
        if not video.exists():
            print(f"error: video not found: {video}", file=sys.stderr)
            return 2
        if not subs.exists():
            print(f"error: subs not found: {subs}", file=sys.stderr)
            return 2
    output.parent.mkdir(parents=True, exist_ok=True)

    tool = args.tool
    if tool == "auto":
        if _alass_bin():
            tool = "alass"
        elif _which("ffsubsync"):
            tool = "ffsubsync"
        else:
            print("error: neither alass nor ffsubsync found", file=sys.stderr)
            return 127
        _log(f"auto-picked tool: {tool}", args.verbose)

    if tool == "alass":
        rc = _run_alass(
            video,
            subs,
            output,
            no_split=args.no_split,
            split_penalty=args.split_penalty,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        if rc != 0 and args.fallback and _which("ffsubsync"):
            _log("alass failed; falling back to ffsubsync", True)
            rc = _run_ffsubsync(
                video,
                subs,
                output,
                no_fix_framerate=args.no_fix_framerate,
                max_offset_seconds=args.max_offset_seconds,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        return rc
    elif tool == "ffsubsync":
        return _run_ffsubsync(
            video,
            subs,
            output,
            no_fix_framerate=args.no_fix_framerate,
            max_offset_seconds=args.max_offset_seconds,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    else:
        print(f"error: unknown tool: {tool}", file=sys.stderr)
        return 2


# --------------------------------------------------------------------------- #
# Subcommand: sync-reference                                                  #
# --------------------------------------------------------------------------- #


def cmd_sync_reference(args: argparse.Namespace) -> int:
    ref = Path(args.reference_subs)
    subs = Path(args.subs)
    output = Path(args.output)
    if not args.dry_run:
        if not ref.exists():
            print(f"error: reference subs not found: {ref}", file=sys.stderr)
            return 2
        if not subs.exists():
            print(f"error: subs not found: {subs}", file=sys.stderr)
            return 2
    output.parent.mkdir(parents=True, exist_ok=True)

    tool = args.tool
    if tool == "auto":
        tool = "alass" if _alass_bin() else "ffsubsync"

    if tool == "alass":
        return _run_alass(
            ref,
            subs,
            output,
            no_split=args.no_split,
            split_penalty=args.split_penalty,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    elif tool == "ffsubsync":
        return _run_ffsubsync(
            ref,
            subs,
            output,
            no_fix_framerate=args.no_fix_framerate,
            max_offset_seconds=args.max_offset_seconds,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    else:
        print(f"error: unknown tool: {tool}", file=sys.stderr)
        return 2


# --------------------------------------------------------------------------- #
# Subcommand: shift (pure-Python SRT offset)                                  #
# --------------------------------------------------------------------------- #

_SRT_TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def _ms_to_srt(ms: int) -> str:
    if ms < 0:
        ms = 0
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_ = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_:03d}"


def _shift_line(line: str, delta_ms: int) -> str:
    m = _SRT_TIME_RE.search(line)
    if not m:
        return line
    h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(x) for x in m.groups())
    start = (h1 * 3600 + m1 * 60 + s1) * 1000 + ms1 + delta_ms
    end = (h2 * 3600 + m2 * 60 + s2) * 1000 + ms2 + delta_ms
    new = f"{_ms_to_srt(start)} --> {_ms_to_srt(end)}"
    return line[: m.start()] + new + line[m.end() :]


def cmd_shift(args: argparse.Namespace) -> int:
    subs = Path(args.subs)
    output = Path(args.output)
    if not args.dry_run and not subs.exists():
        print(f"error: subs not found: {subs}", file=sys.stderr)
        return 2
    delta_ms = int(round(args.seconds * 1000))
    _log(f"shift {subs} by {delta_ms} ms -> {output}", args.verbose or args.dry_run)
    if args.dry_run:
        print(f"# would shift {subs} by {delta_ms} ms -> {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    # Try utf-8-sig first (handles BOM), fall back to latin-1.
    try:
        text = subs.read_text(encoding="utf-8-sig")
        out_encoding = "utf-8"
    except UnicodeDecodeError:
        text = subs.read_text(encoding="latin-1")
        out_encoding = "latin-1"
    shifted = "\n".join(_shift_line(line, delta_ms) for line in text.splitlines())
    if text.endswith("\n"):
        shifted += "\n"
    output.write_text(shifted, encoding=out_encoding)
    print(f"wrote {output} (shifted {delta_ms/1000:+.3f}s)")
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: batch-sync                                                      #
# --------------------------------------------------------------------------- #


@dataclass
class Pair:
    video: Path
    subs: Path
    output: Path


def _match_pairs(video_dir: Path, subs_dir: Path, output_dir: Path) -> list[Pair]:
    videos = {p.stem: p for p in video_dir.iterdir() if p.suffix.lower() in VIDEO_EXTS}
    subs = {p.stem: p for p in subs_dir.iterdir() if p.suffix.lower() in SUB_EXTS}
    pairs: list[Pair] = []
    for stem, vpath in sorted(videos.items()):
        spath = subs.get(stem)
        if spath is None:
            # loose match: subs stem starts with video stem (handles .en, .eng)
            for sstem, sp in subs.items():
                if sstem.startswith(stem):
                    spath = sp
                    break
        if spath is None:
            continue
        out = output_dir / f"{spath.stem}.synced{spath.suffix}"
        pairs.append(Pair(vpath, spath, out))
    return pairs


def cmd_batch_sync(args: argparse.Namespace) -> int:
    vdir = Path(args.video_dir)
    sdir = Path(args.subs_dir)
    odir = Path(args.output_dir)
    if not args.dry_run:
        for d, name in ((vdir, "video-dir"), (sdir, "subs-dir")):
            if not d.is_dir():
                print(f"error: {name} not a directory: {d}", file=sys.stderr)
                return 2
    odir.mkdir(parents=True, exist_ok=True)
    pairs = _match_pairs(vdir, sdir, odir)
    if not pairs:
        print("no matching video/subtitle pairs found", file=sys.stderr)
        return 1
    _log(f"{len(pairs)} pair(s) to sync", args.verbose or args.dry_run)
    failures = 0
    for p in pairs:
        print(f"--> {p.video.name} + {p.subs.name} -> {p.output.name}")
        sub_args = argparse.Namespace(
            video=str(p.video),
            subs=str(p.subs),
            output=str(p.output),
            tool=args.tool,
            no_split=args.no_split,
            split_penalty=args.split_penalty,
            no_fix_framerate=args.no_fix_framerate,
            max_offset_seconds=args.max_offset_seconds,
            fallback=args.fallback,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        rc = cmd_sync(sub_args)
        if rc != 0:
            failures += 1
            print(f"!! failed: {p.subs.name}", file=sys.stderr)
    print(f"batch done: {len(pairs) - failures} ok, {failures} failed")
    return 0 if failures == 0 else 1


# --------------------------------------------------------------------------- #
# Arg parsing                                                                 #
# --------------------------------------------------------------------------- #


def _add_common_tool_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--tool", choices=["alass", "ffsubsync", "auto"], default="auto")
    sp.add_argument(
        "--no-split",
        action="store_true",
        help="alass: disable scene-split analysis (fast, linear only)",
    )
    sp.add_argument(
        "--split-penalty",
        type=float,
        default=None,
        help="alass: split penalty (higher = fewer splits; default ~7)",
    )
    sp.add_argument(
        "--no-fix-framerate",
        action="store_true",
        help="ffsubsync: disable framerate adjustment",
    )
    sp.add_argument(
        "--max-offset-seconds",
        type=float,
        default=None,
        help="ffsubsync: widen search window (default 60)",
    )
    sp.add_argument(
        "--fallback",
        action="store_true",
        help="sync: if alass fails, try ffsubsync automatically",
    )


def _add_common_flags(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "--dry-run", action="store_true", help="print the command(s) without executing"
    )
    sp.add_argument("--verbose", action="store_true", help="log actions to stderr")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="subsync",
        description="Wrapper over alass / ffsubsync for subtitle synchronization.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # check
    pc = sub.add_parser("check", help="report tool availability")
    _add_common_flags(pc)
    pc.set_defaults(func=cmd_check)

    # sync
    ps = sub.add_parser("sync", help="sync subtitle to video audio")
    ps.add_argument("--video", required=True)
    ps.add_argument("--subs", required=True)
    ps.add_argument("--output", required=True)
    _add_common_tool_args(ps)
    _add_common_flags(ps)
    ps.set_defaults(func=cmd_sync)

    # sync-reference
    pr = sub.add_parser(
        "sync-reference", help="sync subtitle against a known-good reference sub"
    )
    pr.add_argument("--reference-subs", required=True)
    pr.add_argument("--subs", required=True)
    pr.add_argument("--output", required=True)
    _add_common_tool_args(pr)
    _add_common_flags(pr)
    pr.set_defaults(func=cmd_sync_reference)

    # shift
    psh = sub.add_parser(
        "shift", help="apply a constant time offset (pure SRT rewrite)"
    )
    psh.add_argument("--subs", required=True)
    psh.add_argument("--output", required=True)
    psh.add_argument(
        "--seconds",
        type=float,
        required=True,
        help="positive = delay subs, negative = advance",
    )
    _add_common_flags(psh)
    psh.set_defaults(func=cmd_shift)

    # batch-sync
    pb = sub.add_parser("batch-sync", help="sync a folder of subtitles against videos")
    pb.add_argument("--video-dir", required=True)
    pb.add_argument("--subs-dir", required=True)
    pb.add_argument("--output-dir", required=True)
    _add_common_tool_args(pb)
    _add_common_flags(pb)
    pb.set_defaults(func=cmd_batch_sync)

    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
