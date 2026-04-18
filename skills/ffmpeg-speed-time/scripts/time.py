#!/usr/bin/env python3
"""ffmpeg-speed-time: constant speed, reverse, freeze, loop, timelapse, speed ramp.

Stdlib only. Non-interactive. Prints the exact ffmpeg command it runs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fmt_cmd(cmd: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(c)) for c in cmd)


def _run(cmd: List[str], *, dry_run: bool, verbose: bool) -> int:
    if verbose or dry_run:
        print("+ " + _fmt_cmd(cmd), file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _atempo_chain(factor: float) -> str:
    """Return a comma-separated atempo filter chain that realizes `factor`.

    atempo supports [0.5, 100.0] per instance. We chain 0.5 or 2.0 stages
    and finish with a residual factor, giving a correct chain for any
    positive `factor` in the practical range.
    """
    if factor <= 0:
        raise ValueError(f"atempo factor must be positive, got {factor}")
    parts: List[str] = []
    f = factor
    while f < 0.5:
        parts.append("atempo=0.5")
        f /= 0.5  # undo this stage
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    # Residual stage (always within [0.5, 2.0]); skip if ~1.0.
    if not math.isclose(f, 1.0, abs_tol=1e-6):
        parts.append(f"atempo={f:.6f}")
    if not parts:
        parts.append("atempo=1.0")
    return ",".join(parts)


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def _ffprobe_fps(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    if "/" in out:
        n, d = out.split("/", 1)
        return float(n) / float(d) if float(d) else 0.0
    return float(out) if out else 0.0


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_speed(args: argparse.Namespace) -> int:
    """Constant speed (both V+A), pitch preserved."""
    k = args.factor  # output rate multiplier. 2.0 -> 2x (K<1 in setpts = K*PTS)
    setpts_k = 1.0 / k  # video PTS multiplier
    atempo_chain = _atempo_chain(k)

    vfilters: List[str] = []
    if args.smooth == "minterpolate":
        fps = args.fps or 60
        vfilters.append(
            "minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:"
            f"fps={fps}'"
        )
    vfilters.append(f"setpts={setpts_k:.6f}*PTS")
    if args.smooth == "minterpolate":
        vfilters.append("format=yuv420p")
    vchain = ",".join(vfilters)

    filter_complex = f"[0:v]{vchain}[v];[0:a]{atempo_chain}[a]"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.input),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        args.vcodec,
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        args.acodec,
        "-b:a",
        args.abitrate,
        str(args.output),
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_reverse(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.input),
        "-vf",
        "reverse",
        "-af",
        "areverse",
        "-c:v",
        args.vcodec,
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        args.acodec,
        "-b:a",
        args.abitrate,
        str(args.output),
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_freeze(args: argparse.Namespace) -> int:
    """Freeze first/last N seconds, or hold a mid-clip frame for --duration."""
    if args.at is not None:
        # Mid-clip freeze — requires source fps to compute frame index.
        fps = _ffprobe_fps(args.input) if not args.dry_run else (args.fps or 30.0)
        if args.fps:
            fps = args.fps
        frame_index = int(round(args.at * fps))
        extra_frames = int(round(args.duration * fps))
        # Audio: insert silence of `duration` seconds starting at `at`.
        vf = f"loop=loop={extra_frames}:size=1:start={frame_index}"
        af = (
            f"[0:a]atrim=0:{args.at},asetpts=N/SR/TB[a0];"
            f"anullsrc=r=48000:cl=stereo,atrim=0:{args.duration},asetpts=N/SR/TB[sil];"
            f"[0:a]atrim={args.at},asetpts=N/SR/TB[a1];"
            "[a0][sil][a1]concat=n=3:v=0:a=1[aout]"
        )
        filter_complex = f"[0:v]{vf}[vout];{af}"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(args.input),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            args.vcodec,
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            args.acodec,
            "-b:a",
            args.abitrate,
            str(args.output),
        ]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.end is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(args.input),
            "-vf",
            f"tpad=stop_mode=clone:stop_duration={args.end}",
            "-af",
            f"apad=pad_dur={args.end}",
            "-shortest",
            "-c:v",
            args.vcodec,
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            args.acodec,
            "-b:a",
            args.abitrate,
            str(args.output),
        ]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.start is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(args.input),
            "-vf",
            f"tpad=start_mode=clone:start_duration={args.start}",
            "-af",
            f"adelay={int(args.start * 1000)}:all=1",
            "-c:v",
            args.vcodec,
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            args.acodec,
            "-b:a",
            args.abitrate,
            str(args.output),
        ]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    print(
        "freeze: pass one of --start N | --end N | --at T --duration D", file=sys.stderr
    )
    return 2


def cmd_loop(args: argparse.Namespace) -> int:
    """Repeat the clip `--count` times total."""
    # -stream_loop N = play the source N+1 times. We want `count` total plays.
    n = max(0, args.count - 1)
    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        str(n),
        "-i",
        str(args.input),
    ]
    if args.reencode:
        cmd += [
            "-c:v",
            args.vcodec,
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            args.acodec,
            "-b:a",
            args.abitrate,
        ]
    else:
        cmd += ["-c", "copy"]
    cmd.append(str(args.output))
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_timelapse(args: argparse.Namespace) -> int:
    """Keep every `--every` Nth frame, output at `--fps`."""
    vf = f"setpts=PTS/{args.every},fps={args.fps}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(args.input),
        "-vf",
        vf,
        "-an",
        "-c:v",
        args.vcodec,
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        str(args.output),
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_ramp(args: argparse.Namespace) -> int:
    """Simple 2-step ramp: before start-time at `--from` speed, then switch to `--to`.

    Implemented as segment split + per-segment speed change + concat.
    This is a pragmatic approximation of a true ramp — good enough for
    most cinematic slow-downs. Supply --duration for the transition segment
    which uses the geometric mean of `from` and `to` as an intermediate
    speed, so you get three segments (pre, transition, post).
    """
    src_dur = _ffprobe_duration(args.input) if not args.dry_run else None

    t1 = args.start_time
    t2 = args.start_time + args.duration
    k_from = args.from_factor
    k_to = args.to_factor
    k_mid = math.sqrt(k_from * k_to)

    workdir = Path(tempfile.mkdtemp(prefix="ffmpeg_ramp_"))
    seg_pre = workdir / "seg_pre.mp4"
    seg_mid = workdir / "seg_mid.mp4"
    seg_post = workdir / "seg_post.mp4"
    list_file = workdir / "list.txt"

    def _speed_segment(
        inp: Path, out: Path, ss: Optional[float], to: Optional[float], factor: float
    ) -> int:
        setpts_k = 1.0 / factor
        atempo = _atempo_chain(factor)
        fc = f"[0:v]setpts={setpts_k:.6f}*PTS[v];[0:a]{atempo}[a]"
        cmd = ["ffmpeg", "-y"]
        if ss is not None:
            cmd += ["-ss", f"{ss}"]
        cmd += ["-i", str(inp)]
        if to is not None:
            cmd += ["-to", f"{to - (ss or 0.0)}"]
        cmd += [
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            args.vcodec,
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-c:a",
            args.acodec,
            "-b:a",
            args.abitrate,
            str(out),
        ]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    rc = _speed_segment(args.input, seg_pre, None, t1, k_from)
    if rc != 0:
        return rc
    rc = _speed_segment(args.input, seg_mid, t1, t2, k_mid)
    if rc != 0:
        return rc
    rc = _speed_segment(args.input, seg_post, t2, None, k_to)
    if rc != 0:
        return rc

    if not args.dry_run:
        list_file.write_text(
            f"file {shlex.quote(str(seg_pre))}\n"
            f"file {shlex.quote(str(seg_mid))}\n"
            f"file {shlex.quote(str(seg_post))}\n"
        )
    concat_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(args.output),
    ]
    return _run(concat_cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_encode_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--vcodec", default="libx264")
    p.add_argument("--crf", type=int, default=20)
    p.add_argument("--preset", default="medium")
    p.add_argument("--acodec", default="aac")
    p.add_argument("--abitrate", default="160k")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="time.py",
        description="ffmpeg speed / time remapping helper",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the command, do not run"
    )
    p.add_argument(
        "--verbose", action="store_true", help="print command before running"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("speed", help="constant speed change (V+A, pitch preserved)")
    sp.add_argument("--input", type=Path, required=True)
    sp.add_argument("--output", type=Path, required=True)
    sp.add_argument(
        "--factor",
        type=float,
        required=True,
        help="playback rate multiplier: 2.0 = 2x faster, 0.5 = half speed",
    )
    sp.add_argument(
        "--smooth",
        choices=["none", "minterpolate"],
        default="none",
        help="minterpolate for smoother slow-motion (slow render)",
    )
    sp.add_argument(
        "--fps",
        type=int,
        default=0,
        help="output fps for minterpolate (default 60 when --smooth=minterpolate)",
    )
    _add_encode_opts(sp)
    sp.set_defaults(func=cmd_speed)

    rp = sub.add_parser("reverse", help="reverse video AND audio (RAM-heavy)")
    rp.add_argument("--input", type=Path, required=True)
    rp.add_argument("--output", type=Path, required=True)
    _add_encode_opts(rp)
    rp.set_defaults(func=cmd_reverse)

    fp = sub.add_parser("freeze", help="freeze first/last/mid frame for N seconds")
    fp.add_argument("--input", type=Path, required=True)
    fp.add_argument("--output", type=Path, required=True)
    fp.add_argument("--start", type=float, help="freeze first frame for N seconds")
    fp.add_argument("--end", type=float, help="freeze last frame for N seconds")
    fp.add_argument("--at", type=float, help="mid-clip freeze at time T (seconds)")
    fp.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="mid-clip freeze duration (seconds, with --at)",
    )
    fp.add_argument(
        "--fps",
        type=float,
        default=0,
        help="override source fps for frame-index math (with --at)",
    )
    _add_encode_opts(fp)
    fp.set_defaults(func=cmd_freeze)

    lp = sub.add_parser("loop", help="repeat the clip N times")
    lp.add_argument("--input", type=Path, required=True)
    lp.add_argument("--output", type=Path, required=True)
    lp.add_argument("--count", type=int, required=True, help="total play count (>=1)")
    lp.add_argument(
        "--reencode", action="store_true", help="re-encode instead of stream copy"
    )
    _add_encode_opts(lp)
    lp.set_defaults(func=cmd_loop)

    tp = sub.add_parser("timelapse", help="keep every Nth frame; output at --fps")
    tp.add_argument("--input", type=Path, required=True)
    tp.add_argument("--output", type=Path, required=True)
    tp.add_argument("--every", type=int, required=True, help="keep every Nth frame")
    tp.add_argument("--fps", type=int, default=30, help="output fps (default 30)")
    _add_encode_opts(tp)
    tp.set_defaults(func=cmd_timelapse)

    rr = sub.add_parser(
        "ramp", help="speed ramp via segment split + per-segment speed + concat"
    )
    rr.add_argument("--input", type=Path, required=True)
    rr.add_argument("--output", type=Path, required=True)
    rr.add_argument(
        "--from",
        dest="from_factor",
        type=float,
        required=True,
        help="starting speed factor (1.0 = normal)",
    )
    rr.add_argument(
        "--to",
        dest="to_factor",
        type=float,
        required=True,
        help="target speed factor (0.25 = 4x slow-mo)",
    )
    rr.add_argument(
        "--start-time",
        type=float,
        required=True,
        help="time (seconds) at which the ramp begins",
    )
    rr.add_argument(
        "--duration", type=float, required=True, help="transition duration (seconds)"
    )
    _add_encode_opts(rr)
    rr.set_defaults(func=cmd_ramp)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
