#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-upscale driver: AI super-resolution for images + video.

Shells out to the open-source + commercial-safe models:
    realesrgan-ncnn-vulkan    (BSD-3-Clause)
    realcugan-ncnn-vulkan     (MIT)
    waifu2x-ncnn-vulkan       (MIT)
    python inference_gfpgan.py (Apache 2.0)
    SwinIR / HAT python inference (Apache 2.0)

Subcommands:
    check          Report which backends are on PATH.
    install        Print platform-specific install command for a model (no auto-install).
    image          Upscale a single image.
    face-restore   GFPGAN face restoration (portraits).
    video          Upscale a video end-to-end (frames -> SR -> remux with audio).
    batch          Upscale every image in a folder.

Global flags:
    --dry-run      Print commands only; do not execute.
    --verbose      Stream stdout/stderr and extra progress info.

Stdlib only. Non-interactive (no prompts). Prints every ffmpeg / ncnn-vulkan
command to stderr before running it.

Models covered here are all open-source + commercial-safe:
    realesr   - Real-ESRGAN (photos, video frames)
    realcugan - Real-CUGAN (anime, illustrations)
    waifu2x   - waifu2x (classic anime)
    gfpgan    - GFPGAN (face restoration)
    swinir    - SwinIR (transformer photo SR)
    hat       - HAT (2023 SOTA photo SR)

Explicitly NOT supported (non-commercial or paid licenses):
    CodeFormer (S-Lab License, research-only)
    Topaz Video AI (commercial paid software)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".m4v", ".ts"}


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
# Backend discovery
# --------------------------------------------------------------------------- #


MODELS = {
    "realesr": {
        "binary": "realesrgan-ncnn-vulkan",
        "license": "BSD-3-Clause",
        "repo": "https://github.com/xinntao/Real-ESRGAN",
        "kinds": {"image", "video", "batch"},
        "default_model_name": "realesrgan-x4plus",
        "scales": {2, 3, 4},
    },
    "realcugan": {
        "binary": "realcugan-ncnn-vulkan",
        "license": "MIT",
        "repo": "https://github.com/nihui/realcugan-ncnn-vulkan",
        "kinds": {"image", "video", "batch"},
        "default_model_name": None,
        "scales": {2, 3, 4},
    },
    "waifu2x": {
        "binary": "waifu2x-ncnn-vulkan",
        "license": "MIT",
        "repo": "https://github.com/nihui/waifu2x-ncnn-vulkan",
        "kinds": {"image", "batch"},
        "default_model_name": None,
        "scales": {1, 2, 4, 8, 16, 32},
    },
    "gfpgan": {
        "binary": None,  # python module
        "license": "Apache-2.0",
        "repo": "https://github.com/TencentARC/GFPGAN",
        "kinds": {"face-restore"},
        "default_model_name": "1.4",
        "scales": {1, 2, 4},
    },
    "swinir": {
        "binary": None,
        "license": "Apache-2.0",
        "repo": "https://github.com/JingyunLiang/SwinIR",
        "kinds": {"image"},
        "default_model_name": "real_sr",
        "scales": {2, 3, 4},
    },
    "hat": {
        "binary": None,
        "license": "Apache-2.0",
        "repo": "https://github.com/XPixelGroup/HAT",
        "kinds": {"image"},
        "default_model_name": None,
        "scales": {2, 3, 4},
    },
}


def cmd_check(args: argparse.Namespace) -> int:
    found = {}
    for key, info in MODELS.items():
        bin_name = info["binary"]
        found[key] = {
            "license": info["license"],
            "repo": info["repo"],
            "binary": bin_name,
            "on_path": bool(bin_name and which(bin_name)),
        }
    found["ffmpeg"] = {"binary": "ffmpeg", "on_path": bool(which("ffmpeg"))}
    found["ffprobe"] = {"binary": "ffprobe", "on_path": bool(which("ffprobe"))}
    print(json.dumps(found, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# install (print-only; never auto-install)
# --------------------------------------------------------------------------- #


INSTALL_HINTS = {
    "realesr": {
        "darwin": "Download release zip: https://github.com/xinntao/Real-ESRGAN/releases  (unzip, put realesrgan-ncnn-vulkan on PATH)",
        "linux": "Download release zip: https://github.com/xinntao/Real-ESRGAN/releases  or apt/pacman package 'realesrgan'",
        "windows": "Download release zip: https://github.com/xinntao/Real-ESRGAN/releases  (extract, add folder to PATH)",
    },
    "realcugan": {
        "darwin": "Download release zip: https://github.com/nihui/realcugan-ncnn-vulkan/releases",
        "linux": "Download release zip: https://github.com/nihui/realcugan-ncnn-vulkan/releases",
        "windows": "Download release zip: https://github.com/nihui/realcugan-ncnn-vulkan/releases",
    },
    "waifu2x": {
        "darwin": "brew install waifu2x   (tap: nihui/waifu2x-ncnn-vulkan)   OR download release zip",
        "linux": "apt / pacman: waifu2x-ncnn-vulkan   OR download release zip",
        "windows": "Download release zip: https://github.com/nihui/waifu2x-ncnn-vulkan/releases",
    },
    "gfpgan": {
        "darwin": "uv pip install gfpgan basicsr realesrgan facexlib",
        "linux": "uv pip install gfpgan basicsr realesrgan facexlib",
        "windows": "uv pip install gfpgan basicsr realesrgan facexlib",
    },
    "swinir": {
        "darwin": "git clone https://github.com/JingyunLiang/SwinIR && uv pip install torch opencv-python numpy basicsr",
        "linux": "git clone https://github.com/JingyunLiang/SwinIR && uv pip install torch opencv-python numpy basicsr",
        "windows": "git clone https://github.com/JingyunLiang/SwinIR && uv pip install torch opencv-python numpy basicsr",
    },
    "hat": {
        "darwin": "git clone https://github.com/XPixelGroup/HAT && uv pip install torch opencv-python numpy basicsr",
        "linux": "git clone https://github.com/XPixelGroup/HAT && uv pip install torch opencv-python numpy basicsr",
        "windows": "git clone https://github.com/XPixelGroup/HAT && uv pip install torch opencv-python numpy basicsr",
    },
}


def cmd_install(args: argparse.Namespace) -> int:
    model = args.model
    if model not in INSTALL_HINTS:
        die(f"unknown model: {model}; choose from {sorted(INSTALL_HINTS)}")
    sysname = platform.system().lower()
    key = sysname if sysname in ("darwin", "linux", "windows") else "linux"
    hint = INSTALL_HINTS[model].get(key, INSTALL_HINTS[model]["linux"])
    print(f"# Install {model} ({MODELS[model]['license']}) on {sysname or 'unknown'}:")
    print(hint)
    print(f"# Repo: {MODELS[model]['repo']}")
    return 0


# --------------------------------------------------------------------------- #
# image / batch (ncnn-vulkan models)
# --------------------------------------------------------------------------- #


def build_ncnn_cmd(
    model: str,
    inp: str,
    out: str,
    scale: int,
    model_name: Optional[str],
    tile: Optional[int],
    fmt: Optional[str],
    gpu_id: Optional[int],
) -> list[str]:
    info = MODELS[model]
    binary = info["binary"]
    if not binary or not which(binary):
        die(f"{binary or model} not on PATH — run: upscale.py install {model}")
    cmd = [binary, "-i", inp, "-o", out, "-s", str(scale)]
    name = model_name or info.get("default_model_name")
    if name:
        cmd += ["-n", name]
    if tile is not None:
        cmd += ["-t", str(tile)]
    if fmt:
        cmd += ["-f", fmt]
    if gpu_id is not None:
        cmd += ["-g", str(gpu_id)]
    return cmd


def cmd_image(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input image")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.model in ("realesr", "realcugan", "waifu2x"):
        if args.scale not in MODELS[args.model]["scales"]:
            die(
                f"{args.model} supports scales {sorted(MODELS[args.model]['scales'])}, got {args.scale}"
            )
        cmd = build_ncnn_cmd(
            args.model,
            str(inp),
            str(out),
            args.scale,
            args.model_name,
            args.tile,
            args.fmt,
            args.gpu,
        )
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.model == "swinir":
        die(
            "swinir runs via SwinIR/main_test_swinir.py — see SKILL.md Step 2 Recipe C."
        )
    if args.model == "hat":
        die(
            "hat runs via HAT/hat/test.py with an -opt YAML — see SKILL.md Step 2 Recipe D."
        )
    if args.model == "gfpgan":
        die("use 'face-restore' subcommand for gfpgan.")
    die(f"unknown model: {args.model}")


def cmd_batch(args: argparse.Namespace) -> int:
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    ensure(in_dir, "input directory")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.model not in ("realesr", "realcugan", "waifu2x"):
        die(
            f"batch mode only supports ncnn-vulkan models (realesr/realcugan/waifu2x), got {args.model}"
        )

    cmd = build_ncnn_cmd(
        args.model,
        str(in_dir),
        str(out_dir),
        args.scale,
        args.model_name,
        args.tile,
        args.fmt,
        args.gpu,
    )
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# --------------------------------------------------------------------------- #
# face-restore (GFPGAN)
# --------------------------------------------------------------------------- #


def cmd_face_restore(args: argparse.Namespace) -> int:
    if args.model != "gfpgan":
        die("face-restore currently supports --model gfpgan only")
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input image")
    out.parent.mkdir(parents=True, exist_ok=True)

    # GFPGAN expects dir-in / dir-out. Create a scratch dir with the single input.
    work_in = out.parent / f".gfpgan_in_{inp.stem}"
    work_out = out.parent / f".gfpgan_out_{inp.stem}"
    work_in.mkdir(parents=True, exist_ok=True)
    work_out.mkdir(parents=True, exist_ok=True)

    # Copy via hardlink if possible, else cp-like copy
    target = work_in / inp.name
    if not args.dry_run:
        try:
            if target.exists():
                target.unlink()
            os.link(inp, target)
        except OSError:
            shutil.copy2(inp, target)

    cmd = [
        sys.executable,
        "-m",
        "gfpgan.inference_gfpgan",
        "-i",
        str(work_in),
        "-o",
        str(work_out),
        "-v",
        str(args.version),
        "-s",
        str(args.scale),
    ]
    if args.bg_upsampler:
        cmd += ["--bg_upsampler", args.bg_upsampler]
    if args.cpu:
        cmd += ["--device", "cpu"]

    rc = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if rc != 0:
        return rc

    if not args.dry_run:
        # GFPGAN writes to work_out/restored_imgs/<name>.png — move out
        restored = work_out / "restored_imgs" / inp.with_suffix(".png").name
        if not restored.exists():
            # try same name preserved
            alt = work_out / "restored_imgs" / inp.name
            if alt.exists():
                restored = alt
        if not restored.exists():
            die(f"GFPGAN did not produce {restored}; check logs")
        shutil.move(str(restored), str(out))
        shutil.rmtree(work_in, ignore_errors=True)
        shutil.rmtree(work_out, ignore_errors=True)
    return 0


# --------------------------------------------------------------------------- #
# video (frame pipeline)
# --------------------------------------------------------------------------- #


def probe_fps(path: Path) -> str:
    """Return r_frame_rate (e.g. '24000/1001') via ffprobe."""
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
    return out or "30"


def cmd_video(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input video")
    if args.model not in ("realesr", "realcugan"):
        die(f"video mode supports --model realesr | realcugan (got {args.model})")
    if not which("ffmpeg"):
        die("ffmpeg not on PATH")

    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".upscale_{inp.stem}"
    frames_in = work / "frames_in"
    frames_out = work / "frames_out"
    if not args.dry_run:
        frames_in.mkdir(parents=True, exist_ok=True)
        frames_out.mkdir(parents=True, exist_ok=True)

    src_fps = probe_fps(inp)
    log(f"source fps: {src_fps}", args.verbose)

    # Step 1: dump PNG frames
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

    # Step 2: upscale frames (directory in/out)
    cmd = build_ncnn_cmd(
        args.model,
        str(frames_in),
        str(frames_out),
        args.scale,
        args.model_name,
        args.tile,
        "png",
        args.gpu,
    )
    rc = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if rc != 0:
        return rc

    # Step 3: remux
    rc = run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            src_fps,
            "-i",
            str(frames_out / "%08d.png"),
            "-i",
            str(inp),
            "-map",
            "0:v",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(args.crf),
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
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
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="upscale.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )
    p.add_argument("--verbose", action="store_true", help="Extra progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    # check
    pc = sub.add_parser("check", help="Report which backends are on PATH")
    pc.set_defaults(func=cmd_check)

    # install
    pi = sub.add_parser(
        "install", help="Print install command for a model (no auto-install)"
    )
    pi.add_argument("model", choices=list(INSTALL_HINTS.keys()))
    pi.set_defaults(func=cmd_install)

    # image
    pim = sub.add_parser("image", help="Upscale a single image")
    pim.add_argument(
        "--model",
        required=True,
        choices=["realesr", "realcugan", "waifu2x", "swinir", "hat"],
    )
    pim.add_argument("--scale", type=int, default=4)
    pim.add_argument("--in", dest="inp", required=True)
    pim.add_argument("--out", required=True)
    pim.add_argument(
        "--model-name",
        default=None,
        help="ncnn-vulkan -n model name (e.g. realesrgan-x4plus)",
    )
    pim.add_argument(
        "--tile", type=int, default=None, help="ncnn-vulkan tile size; 0 = auto"
    )
    pim.add_argument("--fmt", default="png", choices=["png", "jpg", "webp"])
    pim.add_argument("--gpu", type=int, default=None)
    pim.set_defaults(func=cmd_image)

    # face-restore
    pfr = sub.add_parser("face-restore", help="GFPGAN face restoration")
    pfr.add_argument("--model", default="gfpgan", choices=["gfpgan"])
    pfr.add_argument("--in", dest="inp", required=True)
    pfr.add_argument("--out", required=True)
    pfr.add_argument("--scale", type=int, default=2)
    pfr.add_argument(
        "--version", default="1.4", help="GFPGAN model version: 1.2 / 1.3 / 1.4"
    )
    pfr.add_argument(
        "--bg-upsampler", default="realesrgan", choices=["realesrgan", "none"]
    )
    pfr.add_argument("--cpu", action="store_true", help="Force CPU device")
    pfr.set_defaults(func=cmd_face_restore)

    # video
    pv = sub.add_parser("video", help="Upscale a video (frame pipeline)")
    pv.add_argument("--model", required=True, choices=["realesr", "realcugan"])
    pv.add_argument("--in", dest="inp", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument("--scale", type=int, default=2)
    pv.add_argument("--model-name", default=None)
    pv.add_argument("--tile", type=int, default=None)
    pv.add_argument("--gpu", type=int, default=None)
    pv.add_argument("--crf", type=int, default=18)
    pv.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep the intermediate frames directory",
    )
    pv.set_defaults(func=cmd_video)

    # batch
    pb = sub.add_parser("batch", help="Upscale every image in a folder")
    pb.add_argument(
        "--model", required=True, choices=["realesr", "realcugan", "waifu2x"]
    )
    pb.add_argument("--scale", type=int, default=4)
    pb.add_argument("--in-dir", required=True)
    pb.add_argument("--out-dir", required=True)
    pb.add_argument("--model-name", default=None)
    pb.add_argument("--tile", type=int, default=None)
    pb.add_argument("--fmt", default="png", choices=["png", "jpg", "webp"])
    pb.add_argument("--gpu", type=int, default=None)
    pb.set_defaults(func=cmd_batch)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
