#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Real-ESRGAN driver — image / video / batch upscaling via realesrgan-ncnn-vulkan.

Wraps the ncnn-vulkan binary (no Python/CUDA needed) for super-resolution, plus the
extract -> upscale -> remux video pipeline. Non-interactive: every shell command is
printed to stderr before it runs. Supports --dry-run and --verbose throughout.

Subcommands:
  image    upscale a single image
  video    upscale a video (frame pipeline, remux with original audio)
  batch    upscale every image in a folder
  install  print the platform install command (does NOT install)
  check    report which Real-ESRGAN / ffmpeg binaries are on PATH

Examples:
  realesrgan.py image --in photo.jpg --out photo_4x.png --model realesrgan-x4plus --scale 4
  realesrgan.py video --in clip.mp4 --out clip_4x.mp4 --model realesr-animevideov3 --scale 4
  realesrgan.py batch --in-dir photos/ --out-dir photos_4x/ --scale 4
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BIN = "realesrgan-ncnn-vulkan"
MODELS = ("realesr-animevideov3", "realesrgan-x4plus", "realesrgan-x4plus-anime", "realesrnet-x4plus")
RELEASES = "https://github.com/xinntao/Real-ESRGAN/releases"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def run(cmd: list[str], dry: bool, verbose: bool) -> int:
    """Print the exact command to stderr, then run it (unless dry-run)."""
    printable = " ".join(cmd)
    log(f"$ {printable}")
    if dry:
        return 0
    proc = subprocess.run(cmd, capture_output=not verbose, text=True)
    if proc.returncode != 0 and not verbose and proc.stderr:
        log(proc.stderr.strip())
    return proc.returncode


def require(tool: str, dry: bool = False) -> None:
    if shutil.which(tool) is None:
        if dry:
            log(f"# note: '{tool}' not on PATH (dry-run — continuing)")
            return
        log(f"error: '{tool}' not found on PATH. Run: realesrgan.py install")
        raise SystemExit(2)


def ffprobe_fps(path: str, dry: bool = False) -> str:
    """Return the source video's r_frame_rate as a rational string, e.g. '24000/1001'."""
    if dry and shutil.which("ffprobe") is None:
        return "<src_fps>"
    require("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "0", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    fps = (out.stdout or "").strip()
    return fps or "25"


def upscale_cmd(inp: str, outp: str, model: str, scale: int, tile: int, fmt: str) -> list[str]:
    cmd = [BIN, "-i", inp, "-o", outp, "-n", model, "-s", str(scale)]
    if tile:
        cmd += ["-t", str(tile)]
    if fmt:
        cmd += ["-f", fmt]
    return cmd


def cmd_image(a: argparse.Namespace) -> int:
    require(BIN, a.dry_run)
    return run(upscale_cmd(a.input, a.output, a.model, a.scale, a.tile, a.format), a.dry_run, a.verbose)


def cmd_batch(a: argparse.Namespace) -> int:
    require(BIN, a.dry_run)
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    # ncnn-vulkan accepts a directory for -i/-o and processes every file.
    return run(upscale_cmd(a.in_dir, a.out_dir, a.model, a.scale, a.tile, a.format), a.dry_run, a.verbose)


def cmd_video(a: argparse.Namespace) -> int:
    require(BIN, a.dry_run)
    require("ffmpeg", a.dry_run)
    fps = a.fps or ffprobe_fps(a.input, a.dry_run)
    log(f"# source fps = {fps}")
    workdir = Path(a.workdir) if a.workdir else Path(tempfile.mkdtemp(prefix="realesr_"))
    frames = workdir / "frames"
    up = workdir / "frames_up"
    frames.mkdir(parents=True, exist_ok=True)
    up.mkdir(parents=True, exist_ok=True)

    rc = run(["ffmpeg", "-y", "-i", a.input, "-qscale:v", "1", "-qmin", "1", "-qmax", "1",
              "-vsync", "0", str(frames / "%08d.png")], a.dry_run, a.verbose)
    if rc:
        return rc
    rc = run(upscale_cmd(str(frames), str(up), a.model, a.scale, a.tile, "png"), a.dry_run, a.verbose)
    if rc:
        return rc
    rc = run(["ffmpeg", "-y", "-framerate", fps, "-i", str(up / "%08d.png"), "-i", a.input,
              "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", a.preset,
              "-crf", str(a.crf), "-pix_fmt", "yuv420p",
              "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
              "-c:a", "copy", "-movflags", "+faststart", a.output], a.dry_run, a.verbose)
    if not a.keep_frames and not a.dry_run:
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        log(f"# frames kept in {workdir}")
    return rc


def cmd_install(a: argparse.Namespace) -> int:
    plat = sys.platform
    log("# Real-ESRGAN install (this command is printed, NOT run):")
    if plat == "darwin":
        log("brew install realesrgan-ncnn-vulkan   # if the tap exists, else download a release zip:")
    elif plat.startswith("linux"):
        log("# download the linux release zip (binary + bundled models/):")
    else:
        log("# download the windows release zip (binary + bundled models/):")
    log(f"#   {RELEASES}")
    log("# Python alternative (CUDA, --face_enhance, fractional --outscale):")
    log("uv pip install realesrgan basicsr")
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    for tool in (BIN, "ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        log(f"{'OK ' if path else 'MISSING'} {tool}{(' -> ' + path) if path else ''}")
    log(f"# models (pass with --model / -n): {', '.join(MODELS)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Parent parser holds the globals so they work BEFORE or AFTER the subcommand.
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--dry-run", action="store_true", help="print commands without running them")
    g.add_argument("--verbose", action="store_true", help="stream tool output instead of capturing")
    p = argparse.ArgumentParser(description="Real-ESRGAN upscaling driver (ncnn-vulkan).", parents=[g])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_model_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--model", default="realesrgan-x4plus", choices=MODELS, help="model name (-n)")
        sp.add_argument("--scale", type=int, default=4, choices=(2, 3, 4), help="upscale factor (-s)")
        sp.add_argument("--tile", type=int, default=0, help="tile size (-t); 0=auto, e.g. 256 caps VRAM")
        sp.add_argument("--format", default="png", choices=("png", "jpg", "webp"), help="output format (-f)")

    img = sub.add_parser("image", help="upscale a single image")
    img.add_argument("--in", dest="input", required=True)
    img.add_argument("--out", dest="output", required=True)
    add_model_args(img)
    img.set_defaults(func=cmd_image)

    bat = sub.add_parser("batch", help="upscale every image in a folder")
    bat.add_argument("--in-dir", dest="in_dir", required=True)
    bat.add_argument("--out-dir", dest="out_dir", required=True)
    add_model_args(bat)
    bat.set_defaults(func=cmd_batch)

    vid = sub.add_parser("video", help="upscale a video (frame pipeline)")
    vid.add_argument("--in", dest="input", required=True)
    vid.add_argument("--out", dest="output", required=True)
    vid.add_argument("--fps", default="", help="override source fps (default: ffprobe r_frame_rate)")
    vid.add_argument("--crf", type=int, default=17, help="x264 CRF for the remux (default 17)")
    vid.add_argument("--preset", default="slow", help="x264 preset (default slow)")
    vid.add_argument("--workdir", default="", help="frame scratch dir (default: a temp dir)")
    vid.add_argument("--keep-frames", action="store_true", help="don't delete the frame scratch dir")
    add_model_args(vid)
    vid.set_defaults(func=cmd_video, model="realesr-animevideov3")

    sub.add_parser("install", help="print the install command").set_defaults(func=cmd_install)
    sub.add_parser("check", help="report binaries on PATH").set_defaults(func=cmd_check)
    return p


def main() -> int:
    # Globals (--dry-run/--verbose) may appear anywhere; strip them so the
    # subparser can't clobber the value, then set them on the namespace.
    raw = sys.argv[1:]
    dry = "--dry-run" in raw
    verbose = "--verbose" in raw
    raw = [x for x in raw if x not in ("--dry-run", "--verbose")]
    args = build_parser().parse_args(raw)
    args.dry_run = dry
    args.verbose = verbose
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
