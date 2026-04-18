#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-interpolate driver: AI frame interpolation (RIFE / FILM / PractCL).

Shells out to the open-source + commercial-safe models. Non-interactive
(no prompts). Prints every ffmpeg / rife-ncnn-vulkan command to stderr
before running it.

Subcommands:
    check          Report which backends are on PATH.
    install        Print install command for a model (no auto-install).
    video          Interpolate a video to a target fps (extract -> RIFE -> remux).
    images         Tween between two still images (1 midpoint, or N intermediate frames).
    slow-mo        Stretch video time by factor (2 / 4 / 8) without changing output fps.

Global flags:
    --dry-run      Print commands only; do not execute.
    --verbose      Stream extra progress to stderr.

Models supported (all commercial-safe):
    rife           RIFE — MIT (default)
    film           FILM — Apache 2.0
    practcl        PractCL — MIT

Explicitly NOT supported:
    DAIN           research-only license — not commercial-safe.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {pretty}", file=sys.stderr)
    if dry_run:
        return 0
    out = subprocess.run(cmd, check=False)
    return out.returncode


def ensure(path: Path, kind: str = "file") -> None:
    if not path.exists():
        die(f"{kind} not found: {path}")


# --------------------------------------------------------------------------- #
# Backend metadata
# --------------------------------------------------------------------------- #


MODELS = {
    "rife": {
        "binary": "rife-ncnn-vulkan",
        "license": "MIT",
        "repo": "https://github.com/nihui/rife-ncnn-vulkan",
        "upstream": "https://github.com/hzwer/Practical-RIFE",
        "default_model": "rife-v4.6",
    },
    "film": {
        "binary": None,
        "license": "Apache-2.0",
        "repo": "https://github.com/google-research/frame-interpolation",
        "upstream": "https://github.com/google-research/frame-interpolation",
        "default_model": "Style",
    },
    "practcl": {
        "binary": None,
        "license": "MIT",
        "repo": "https://github.com/fatheral/PractCL",
        "upstream": "https://github.com/fatheral/PractCL",
        "default_model": None,
    },
}


INSTALL_HINTS = {
    "rife": {
        "darwin": "Download release zip: https://github.com/nihui/rife-ncnn-vulkan/releases  (unzip, add folder with rife-ncnn-vulkan + models/ to PATH)",
        "linux": "Download release zip: https://github.com/nihui/rife-ncnn-vulkan/releases",
        "windows": "Download release zip: https://github.com/nihui/rife-ncnn-vulkan/releases",
    },
    "film": {
        "darwin": "uv pip install tensorflow mediapy   &&   git clone https://github.com/google-research/frame-interpolation",
        "linux": "uv pip install tensorflow mediapy   &&   git clone https://github.com/google-research/frame-interpolation",
        "windows": "uv pip install tensorflow mediapy   &&   git clone https://github.com/google-research/frame-interpolation",
    },
    "practcl": {
        "darwin": "git clone https://github.com/fatheral/PractCL   &&   uv pip install torch opencv-python numpy",
        "linux": "git clone https://github.com/fatheral/PractCL   &&   uv pip install torch opencv-python numpy",
        "windows": "git clone https://github.com/fatheral/PractCL   &&   uv pip install torch opencv-python numpy",
    },
}


# --------------------------------------------------------------------------- #
# check / install
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    result = {
        "models": {
            k: {
                "license": v["license"],
                "repo": v["repo"],
                "binary": v["binary"],
                "on_path": bool(v["binary"] and which(v["binary"])),
            }
            for k, v in MODELS.items()
        },
        "ffmpeg": {"on_path": bool(which("ffmpeg"))},
        "ffprobe": {"on_path": bool(which("ffprobe"))},
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    model = args.model
    if model not in INSTALL_HINTS:
        die(f"unknown model: {model}; choose from {sorted(INSTALL_HINTS)}")
    sysname = platform.system().lower()
    key = sysname if sysname in ("darwin", "linux", "windows") else "linux"
    print(f"# Install {model} ({MODELS[model]['license']}) on {sysname or 'unknown'}:")
    print(INSTALL_HINTS[model][key])
    print(f"# Repo: {MODELS[model]['repo']}")
    return 0


# --------------------------------------------------------------------------- #
# ffprobe helpers
# --------------------------------------------------------------------------- #


def probe_fps_rational(path: Path) -> str:
    ff = which("ffprobe") or die("ffprobe not on PATH")
    out = subprocess.check_output(
        [
            ff,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return out or "30/1"


def rational_to_float(r: str) -> float:
    if "/" in r:
        n, d = r.split("/", 1)
        return float(n) / float(d) if float(d) else float(n)
    return float(r)


def nearest_pow2_multiplier(src_fps: float, tgt_fps: float) -> int:
    """Smallest power-of-two multiplier so src_fps * m >= tgt_fps."""
    if tgt_fps <= src_fps:
        return 1
    ratio = tgt_fps / src_fps
    exp = max(1, math.ceil(math.log2(ratio)))
    return 2**exp


# --------------------------------------------------------------------------- #
# video pipeline
# --------------------------------------------------------------------------- #


def run_rife_folder(
    in_dir: Path,
    out_dir: Path,
    model_name: str,
    multiplier: int,
    *,
    gpu: Optional[int],
    dry_run: bool,
    verbose: bool,
) -> int:
    binary = which("rife-ncnn-vulkan") or die(
        "rife-ncnn-vulkan not on PATH — see: interp.py install rife"
    )
    # -n: number of output frames. 0 = default (2x). For multiplier 2^k pass -n 0 k times? No —
    # rife-ncnn-vulkan supports arbitrary -n OUTPUT_FRAMES, but the stable approach for 2/4/8x is
    # to iterate the 2x step k times to produce 2^k total.
    iterations = int(round(math.log2(multiplier)))
    if 2**iterations != multiplier:
        die(f"multiplier must be a power of two, got {multiplier}")
    current_in = in_dir
    for i in range(iterations):
        step_out = (
            out_dir.parent / f"{out_dir.name}_step{i}"
            if i < iterations - 1
            else out_dir
        )
        if not dry_run:
            step_out.mkdir(parents=True, exist_ok=True)
        cmd = [binary, "-i", str(current_in), "-o", str(step_out), "-m", model_name]
        if gpu is not None:
            cmd += ["-g", str(gpu)]
        rc = run(cmd, dry_run=dry_run, verbose=verbose)
        if rc != 0:
            return rc
        current_in = step_out
    return 0


def cmd_video(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input video")
    if not which("ffmpeg"):
        die("ffmpeg not on PATH")
    if args.model != "rife":
        die(
            "video pipeline here wraps RIFE only. For FILM/PractCL use their upstream CLIs — see SKILL.md Step 2."
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".interp_{inp.stem}"
    frames_in = work / "frames_in"
    frames_out = work / "frames_out"
    if not args.dry_run:
        frames_in.mkdir(parents=True, exist_ok=True)
        frames_out.mkdir(parents=True, exist_ok=True)

    src_fps_rat = probe_fps_rational(inp)
    src_fps = rational_to_float(src_fps_rat)
    log(f"source fps: {src_fps_rat} ({src_fps:.3f})", args.verbose)

    multiplier = nearest_pow2_multiplier(src_fps, float(args.fps))
    log(f"using multiplier {multiplier}x, then fps filter to {args.fps}", args.verbose)

    # (1) dump frames
    rc = run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(inp),
            "-qscale:v",
            "1",
            "-qmin",
            "1",
            "-qmax",
            "1",
            "-vsync",
            "0",
            str(frames_in / "%08d.png"),
        ],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc

    # (2) RIFE loop
    rc = run_rife_folder(
        frames_in,
        frames_out,
        args.rife_model,
        multiplier,
        gpu=args.gpu,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc

    # (3) remux: frames at src_fps*multiplier, then fps filter to args.fps, copy audio
    frame_rate = f"{src_fps * multiplier:.6f}"
    rc = run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            frame_rate,
            "-i",
            str(frames_out / "%08d.png"),
            "-i",
            str(inp),
            "-map",
            "0:v",
            "-map",
            "1:a?",
            "-vf",
            f"fps={args.fps}:round=near",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(args.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(out),
        ],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if rc == 0 and not args.keep_frames and not args.dry_run:
        shutil.rmtree(work, ignore_errors=True)
    return rc


# --------------------------------------------------------------------------- #
# slow-mo (stretch time)
# --------------------------------------------------------------------------- #


def cmd_slowmo(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input video")
    if not which("ffmpeg"):
        die("ffmpeg not on PATH")
    if args.model != "rife":
        die("slow-mo pipeline here wraps RIFE only.")
    if args.factor not in (2, 4, 8):
        die("--factor must be 2, 4, or 8")

    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".slowmo_{inp.stem}"
    frames_in = work / "frames_in"
    frames_out = work / "frames_out"
    if not args.dry_run:
        frames_in.mkdir(parents=True, exist_ok=True)
        frames_out.mkdir(parents=True, exist_ok=True)

    src_fps = rational_to_float(probe_fps_rational(inp))
    log(f"source fps: {src_fps:.3f}, factor: {args.factor}", args.verbose)

    rc = run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(inp),
            "-qscale:v",
            "1",
            "-qmin",
            "1",
            "-qmax",
            "1",
            "-vsync",
            "0",
            str(frames_in / "%08d.png"),
        ],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc

    rc = run_rife_folder(
        frames_in,
        frames_out,
        args.rife_model,
        args.factor,
        gpu=args.gpu,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc

    # Remux frames at SOURCE fps -> content plays N× slower. Drop audio (see SKILL.md gotcha).
    rc = run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{src_fps:.6f}",
            "-i",
            str(frames_out / "%08d.png"),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(args.crf),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if rc == 0 and not args.keep_frames and not args.dry_run:
        shutil.rmtree(work, ignore_errors=True)
    return rc


# --------------------------------------------------------------------------- #
# images (still tween)
# --------------------------------------------------------------------------- #


def cmd_images(args: argparse.Namespace) -> int:
    a = Path(args.first)
    b = Path(args.second)
    ensure(a, "first image")
    ensure(b, "second image")
    if args.model != "rife":
        die("image tweening here wraps RIFE only.")
    binary = which("rife-ncnn-vulkan") or die(
        "rife-ncnn-vulkan not on PATH — see: interp.py install rife"
    )

    if args.out and not args.out_dir:
        # single midpoint
        cmd = [
            binary,
            "-0",
            str(a),
            "-1",
            str(b),
            "-o",
            str(args.out),
            "-m",
            args.rife_model,
        ]
        if args.gpu is not None:
            cmd += ["-g", str(args.gpu)]
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if not args.out_dir:
        die("provide --out <file> (for 1 midpoint) OR --out-dir <dir> (for a sequence)")

    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    count = args.count if args.count and args.count > 0 else 1
    # Recursive bisection: each pass doubles the frames.
    # For an arbitrary count we upper-bound to next power of two and then subsample.
    k = max(1, math.ceil(math.log2(count + 1)))
    total_pow2 = 2**k - 1  # frames strictly between a and b
    log(f"requested {count}, producing {total_pow2} then trimming", args.verbose)

    # Seed list of ordered frame paths: [a, b]
    frames: list[Path] = [a, b]

    def bisect_pass(frames: list[Path], depth: int) -> list[Path]:
        new: list[Path] = [frames[0]]
        for i in range(len(frames) - 1):
            mid_path = out_dir / f"_pass{depth}_{i:05d}.png"
            cmd = [
                binary,
                "-0",
                str(frames[i]),
                "-1",
                str(frames[i + 1]),
                "-o",
                str(mid_path),
                "-m",
                args.rife_model,
            ]
            if args.gpu is not None:
                cmd += ["-g", str(args.gpu)]
            rc = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
            if rc != 0:
                sys.exit(rc)
            new.append(mid_path)
            new.append(frames[i + 1])
        return new

    for depth in range(k):
        frames = bisect_pass(frames, depth)

    # Drop the outer endpoints, then pick `count` evenly spaced tweens
    inner = frames[1:-1]
    if len(inner) > count:
        step = len(inner) / count
        picks = [inner[int(i * step)] for i in range(count)]
    else:
        picks = inner

    # Rename picks to ordered output names
    for i, src in enumerate(picks):
        dst = out_dir / f"{i + 1:04d}.png"
        if not args.dry_run:
            if dst.exists():
                dst.unlink()
            shutil.move(str(src), str(dst))
    # Clean up leftover pass files
    if not args.dry_run:
        for leftover in out_dir.glob("_pass*.png"):
            try:
                leftover.unlink()
            except OSError:
                pass
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="interp.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )
    p.add_argument("--verbose", action="store_true", help="Extra progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    # check / install
    pc = sub.add_parser("check", help="Report which backends are on PATH")
    pc.set_defaults(func=cmd_check)

    pi = sub.add_parser(
        "install", help="Print install command for a model (no auto-install)"
    )
    pi.add_argument("model", choices=list(INSTALL_HINTS.keys()))
    pi.set_defaults(func=cmd_install)

    # video
    pv = sub.add_parser("video", help="Interpolate a video to a target fps")
    pv.add_argument("--model", default="rife", choices=["rife", "film", "practcl"])
    pv.add_argument("--in", dest="inp", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument(
        "--fps",
        type=float,
        required=True,
        help="Target frames per second (e.g. 60, 120, 240)",
    )
    pv.add_argument(
        "--rife-model",
        default="rife-v4.6",
        help="RIFE ncnn model name under models/ (e.g. rife-v4.6, rife-anime-v4.6)",
    )
    pv.add_argument("--gpu", type=int, default=None)
    pv.add_argument("--crf", type=int, default=17)
    pv.add_argument("--keep-frames", action="store_true")
    pv.set_defaults(func=cmd_video)

    # slow-mo
    ps = sub.add_parser("slow-mo", help="Stretch time by a factor (audio dropped)")
    ps.add_argument("--model", default="rife", choices=["rife"])
    ps.add_argument("--in", dest="inp", required=True)
    ps.add_argument("--out", required=True)
    ps.add_argument("--factor", type=int, default=2, choices=[2, 4, 8])
    ps.add_argument("--rife-model", default="rife-v4.6")
    ps.add_argument("--gpu", type=int, default=None)
    ps.add_argument("--crf", type=int, default=17)
    ps.add_argument("--keep-frames", action="store_true")
    ps.set_defaults(func=cmd_slowmo)

    # images
    pim = sub.add_parser("images", help="Tween between two still images")
    pim.add_argument("--model", default="rife", choices=["rife"])
    pim.add_argument("first", help="first.png (t=0)")
    pim.add_argument("second", help="second.png (t=1)")
    pim.add_argument(
        "--out", help="Single midpoint output (mutually exclusive with --out-dir)"
    )
    pim.add_argument("--out-dir", help="Directory for N intermediate frames")
    pim.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of intermediate frames to produce into --out-dir",
    )
    pim.add_argument("--rife-model", default="rife-v4.6")
    pim.add_argument("--gpu", type=int, default=None)
    pim.set_defaults(func=cmd_images)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
