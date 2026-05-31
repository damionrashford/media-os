#!/usr/bin/env python3
"""denoise.py — ffmpeg denoise & restoration driver.

Subcommands:
  video   — spatial/temporal video denoise (hqdn3d/nlmeans/bm3d/atadenoise/fftdnoiz)
  grain   — film grain removal (removegrain=mode=11)
  audio   — audio denoise (afftdn/anlmdn/arnndn)
  sr      — DNN super-resolution (dnn_processing)

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import List


# ----- filter recipe tables -----------------------------------------------------

# video: (filter_name, strength_preset) -> filter string
VIDEO_RECIPES: dict[tuple[str, str], str] = {
    ("hqdn3d", "light"): "hqdn3d=2:1.5:3:2.25",
    ("hqdn3d", "medium"): "hqdn3d=4:3:6:4.5",
    ("hqdn3d", "heavy"): "hqdn3d=8:6:12:9",
    ("nlmeans", "light"): "nlmeans=s=0.6:p=5:r=11",
    ("nlmeans", "medium"): "nlmeans=s=1.0:p=7:r=15",
    ("nlmeans", "heavy"): "nlmeans=s=1.8:p=9:r=21",
    ("bm3d", "light"): "bm3d=sigma=3:block=4:bstep=2:group=1",
    ("bm3d", "medium"): "bm3d=sigma=10:block=4:bstep=2:group=1",
    ("bm3d", "heavy"): "bm3d=sigma=20:block=8:bstep=4:group=8",
    (
        "atadenoise",
        "light",
    ): "atadenoise=0a=0.01:0b=0.02:1a=0.01:1b=0.02:2a=0.01:2b=0.02:s=5",
    (
        "atadenoise",
        "medium",
    ): "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=9",
    (
        "atadenoise",
        "heavy",
    ): "atadenoise=0a=0.04:0b=0.08:1a=0.04:1b=0.08:2a=0.04:2b=0.08:s=15",
    ("fftdnoiz", "light"): "fftdnoiz=sigma=3:amount=0.7",
    ("fftdnoiz", "medium"): "fftdnoiz=sigma=8:amount=0.9",
    ("fftdnoiz", "heavy"): "fftdnoiz=sigma=15:amount=1.0",
}

VIDEO_FILTERS = ("hqdn3d", "nlmeans", "bm3d", "atadenoise", "fftdnoiz")
STRENGTHS = ("light", "medium", "heavy")

AUDIO_RECIPES: dict[str, str] = {
    "afftdn": "afftdn=nf=-25",
    "anlmdn": "anlmdn=s=7:p=0.002:r=0.002",
    # arnndn handled specially to inject model path
}


# ----- helpers ------------------------------------------------------------------


def log(msg: str, *, verbose: bool) -> None:
    if verbose:
        sys.stderr.write(msg + "\n")


def run_or_print(cmd: List[str], *, dry_run: bool, verbose: bool) -> int:
    printed = " ".join(shlex.quote(c) for c in cmd)
    print(printed)
    if dry_run:
        log("[dry-run] skipping execution", verbose=verbose)
        return 0
    log("[run] executing", verbose=verbose)
    return subprocess.call(cmd)


def build_ffmpeg(
    vf: str | None,
    af: str | None,
    input_path: str,
    output_path: str,
    extra: list[str] | None = None,
) -> List[str]:
    cmd: List[str] = ["ffmpeg", "-y", "-i", input_path]
    if vf:
        cmd += [
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-c:a",
            "copy",
        ]
    if af and not vf:
        cmd += ["-af", af, "-c:a", "pcm_s16le"]
    elif af and vf:
        # override audio codec if we're also filtering audio
        cmd = [c for c in cmd if c != "copy"]
        cmd += ["-af", af]
    if extra:
        cmd += extra
    cmd.append(output_path)
    return cmd


# ----- subcommand implementations ----------------------------------------------


def cmd_video(args: argparse.Namespace) -> int:
    key = (args.filter, args.strength)
    if key not in VIDEO_RECIPES:
        sys.stderr.write(f"error: unknown filter/strength combo: {key}\n")
        return 2
    vf = VIDEO_RECIPES[key]
    log(
        f"[video] filter={args.filter} strength={args.strength} -> {vf}",
        verbose=args.verbose,
    )
    cmd = build_ffmpeg(vf=vf, af=None, input_path=args.input, output_path=args.output)
    return run_or_print(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_grain(args: argparse.Namespace) -> int:
    vf = "removegrain=mode=11"
    log(f"[grain] -> {vf}", verbose=args.verbose)
    cmd = build_ffmpeg(vf=vf, af=None, input_path=args.input, output_path=args.output)
    return run_or_print(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_audio(args: argparse.Namespace) -> int:
    if args.method == "arnndn":
        if not args.rnnn_model:
            sys.stderr.write("error: --rnnn-model PATH is required for arnndn\n")
            return 2
        af = f"arnndn=m={args.rnnn_model}"
    else:
        af = AUDIO_RECIPES[args.method]
    log(f"[audio] method={args.method} -> {af}", verbose=args.verbose)
    cmd = ["ffmpeg", "-y", "-i", args.input, "-af", af, args.output]
    return run_or_print(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_sr(args: argparse.Namespace) -> int:
    # backend guessed from filename extension; TF default, openvino if .xml, native if .model
    model = args.model
    backend = args.backend
    if backend == "auto":
        if model.endswith(".xml"):
            backend = "openvino"
        elif model.endswith(".model"):
            backend = "native"
        else:
            backend = "tensorflow"
    vf = (
        f"dnn_processing=dnn_backend={backend}:model={model}:"
        f"input={args.input_tensor}:output={args.output_tensor}"
    )
    log(f"[sr] scale={args.scale} backend={backend} -> {vf}", verbose=args.verbose)
    cmd = build_ffmpeg(vf=vf, af=None, input_path=args.input, output_path=args.output)
    return run_or_print(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ----- argparse -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="denoise.py",
        description="ffmpeg denoise + restoration driver (video/grain/audio/sr)",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print command, do not execute"
    )
    p.add_argument("--verbose", action="store_true", help="verbose logging")

    sub = p.add_subparsers(dest="subcmd", required=True)

    # video
    pv = sub.add_parser("video", help="spatial/temporal video denoise")
    pv.add_argument("--input", "-i", required=True)
    pv.add_argument("--output", "-o", required=True)
    pv.add_argument("--strength", choices=STRENGTHS, default="medium")
    pv.add_argument("--filter", choices=VIDEO_FILTERS, default="hqdn3d")
    pv.set_defaults(func=cmd_video)

    # grain
    pg = sub.add_parser("grain", help="film grain removal (removegrain mode 11)")
    pg.add_argument("--input", "-i", required=True)
    pg.add_argument("--output", "-o", required=True)
    pg.set_defaults(func=cmd_grain)

    # audio
    pa = sub.add_parser("audio", help="audio denoise")
    pa.add_argument("--input", "-i", required=True)
    pa.add_argument("--output", "-o", required=True)
    pa.add_argument(
        "--method", choices=("afftdn", "anlmdn", "arnndn"), default="afftdn"
    )
    pa.add_argument(
        "--rnnn-model",
        dest="rnnn_model",
        default=None,
        help="path to .rnnn model (required for arnndn)",
    )
    pa.set_defaults(func=cmd_audio)

    # sr (super-resolution)
    ps = sub.add_parser("sr", help="DNN super-resolution (dnn_processing)")
    ps.add_argument("--input", "-i", required=True)
    ps.add_argument("--output", "-o", required=True)
    ps.add_argument(
        "--scale",
        type=int,
        choices=(2, 3, 4),
        default=2,
        help="informational only; actual scale is baked into the model",
    )
    ps.add_argument("--model", required=True, help="path to .pb / .xml / .model file")
    ps.add_argument(
        "--backend",
        choices=("auto", "tensorflow", "openvino", "native"),
        default="auto",
    )
    ps.add_argument(
        "--input-tensor",
        dest="input_tensor",
        default="x",
        help="model input tensor name (default: x)",
    )
    ps.add_argument(
        "--output-tensor",
        dest="output_tensor",
        default="y",
        help="model output tensor name (default: y)",
    )
    ps.set_defaults(func=cmd_sr)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
