#!/usr/bin/env python3
"""
hwaccel.py — detect ffmpeg hardware acceleration and build correct
end-to-end GPU transcode pipelines.

Subcommands
-----------
  detect     : print available hwaccels + hw encoders + platform guess.
  transcode  : build and (optionally) run an accelerated ffmpeg command.

Stdlib only. No prompts. No network.
"""

from __future__ import annotations

import argparse
import platform
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

ACCELS = ("nvenc", "qsv", "vaapi", "videotoolbox", "amf", "auto")
CODECS = ("h264", "hevc", "av1")

# ---------- ffmpeg probing ------------------------------------------------ #


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=15
        )
    except FileNotFoundError:
        return ""
    except subprocess.TimeoutExpired:
        return ""
    return (out.stdout or "") + (out.stderr or "")


def list_hwaccels() -> list[str]:
    text = _run(["ffmpeg", "-hide_banner", "-hwaccels"])
    accels: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("hardware"):
            continue
        if re.fullmatch(r"[a-z0-9_]+", line):
            accels.append(line)
    return accels


def list_hw_encoders() -> list[str]:
    text = _run(["ffmpeg", "-hide_banner", "-encoders"])
    encs: list[str] = []
    pat = re.compile(
        r"\s+[VA\.]+\s+(\S+)\s", re.I
    )  # rough line matcher for encoder lines
    for line in text.splitlines():
        m = pat.match(line)
        if not m:
            continue
        name = m.group(1)
        if re.search(r"(nvenc|qsv|vaapi|videotoolbox|amf|vulkan)$", name):
            encs.append(name)
    return encs


def list_hw_decoders() -> list[str]:
    text = _run(["ffmpeg", "-hide_banner", "-decoders"])
    decs: list[str] = []
    pat = re.compile(r"\s+[VA\.]+\s+(\S+)\s", re.I)
    for line in text.splitlines():
        m = pat.match(line)
        if not m:
            continue
        name = m.group(1)
        if re.search(r"(cuvid|_qsv|_vaapi|_videotoolbox)$", name):
            decs.append(name)
    return decs


# ---------- platform / auto-pick ------------------------------------------ #


def platform_guess() -> str:
    """Return a best-guess default accel name for this machine."""
    sysname = platform.system().lower()
    if sysname == "darwin":
        return "videotoolbox"
    encs = set(list_hw_encoders())
    accels = set(list_hwaccels())
    # NVIDIA first
    if any(e.endswith("_nvenc") for e in encs) and "cuda" in accels:
        return "nvenc"
    if sysname == "windows":
        if any(e.endswith("_amf") for e in encs):
            return "amf"
        if any(e.endswith("_qsv") for e in encs):
            return "qsv"
    # Linux Intel iGPU
    if any(e.endswith("_qsv") for e in encs) and "qsv" in accels:
        return "qsv"
    if "vaapi" in accels and any(e.endswith("_vaapi") for e in encs):
        return "vaapi"
    return "none"


# ---------- pipeline builder --------------------------------------------- #


@dataclass
class Plan:
    hwaccel_flags: list[str]
    vfilter: Optional[str]
    encoder: str
    encoder_flags: list[str]


def _scale_expr(accel: str, resolution: Optional[str]) -> Optional[str]:
    if not resolution:
        return None
    w, _, h = resolution.partition("x")
    if not w or not h:
        raise SystemExit(f"--resolution must be WxH, got {resolution!r}")
    if accel == "nvenc":
        return f"scale_cuda={w}:{h}:format=yuv420p"
    if accel == "qsv":
        return f"scale_qsv={w}:{h}"
    if accel == "vaapi":
        return f"scale_vaapi={w}:{h}:format=nv12"
    if accel in ("videotoolbox", "amf"):
        return f"scale={w}:{h}"
    return f"scale={w}:{h}"


def _encoder_name(accel: str, codec: str) -> str:
    if accel == "nvenc":
        return {"h264": "h264_nvenc", "hevc": "hevc_nvenc", "av1": "av1_nvenc"}[codec]
    if accel == "qsv":
        return {"h264": "h264_qsv", "hevc": "hevc_qsv", "av1": "av1_qsv"}[codec]
    if accel == "vaapi":
        if codec == "av1":
            return "av1_vaapi"
        return {"h264": "h264_vaapi", "hevc": "hevc_vaapi"}[codec]
    if accel == "videotoolbox":
        if codec == "av1":
            raise SystemExit("VideoToolbox does not support AV1 encode.")
        return {"h264": "h264_videotoolbox", "hevc": "hevc_videotoolbox"}[codec]
    if accel == "amf":
        if codec == "av1":
            return "av1_amf"
        return {"h264": "h264_amf", "hevc": "hevc_amf"}[codec]
    raise SystemExit(f"unknown accel {accel!r}")


def build_plan(accel: str, codec: str, quality: int, resolution: Optional[str]) -> Plan:
    hw: list[str] = []
    vf: Optional[str] = None
    enc = _encoder_name(accel, codec)
    eflags: list[str] = []
    scale = _scale_expr(accel, resolution)

    if accel == "nvenc":
        hw = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        vf = scale  # scale_cuda keeps frames on GPU
        eflags = [
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            str(quality),
            "-b:v",
            "0",
        ]
        if codec == "hevc":
            eflags += ["-pix_fmt", "p010le"] if quality < 20 else []
    elif accel == "qsv":
        hw = ["-hwaccel", "qsv", "-c:v", f"{codec}_qsv"]
        vf = scale
        eflags = [
            "-preset",
            "medium",
            "-global_quality",
            str(quality),
            "-look_ahead",
            "1",
        ]
    elif accel == "vaapi":
        hw = [
            "-vaapi_device",
            "/dev/dri/renderD128",
            "-hwaccel",
            "vaapi",
            "-hwaccel_output_format",
            "vaapi",
        ]
        parts = []
        if scale:
            parts.append(scale)
        parts.append("format=nv12|vaapi")
        parts.append("hwupload")
        vf = ",".join(parts)
        eflags = ["-rc_mode", "CQP", "-qp", str(quality)]
    elif accel == "videotoolbox":
        hw = ["-hwaccel", "videotoolbox"]
        vf = scale
        # VT uses -q:v (0-100, higher=better) for HEVC; -b:v for H.264.
        if codec == "hevc":
            vt_q = max(1, min(100, 100 - quality * 2))  # invert CRF-ish scale
            eflags = ["-tag:v", "hvc1", "-q:v", str(vt_q), "-allow_sw", "1"]
        else:
            # H.264 VT — use bitrate (rough mapping from quality knob)
            mbps = max(1, 20 - quality // 2)
            eflags = ["-b:v", f"{mbps}M", "-allow_sw", "1"]
    elif accel == "amf":
        hw = []  # AMF typically encode-only on the ffmpeg side
        vf = scale
        eflags = [
            "-rc",
            "vbr_latency",
            "-quality",
            "balanced",
            "-qp_i",
            str(quality),
            "-qp_p",
            str(quality),
        ]
    else:
        raise SystemExit(f"unsupported accel {accel!r}")

    return Plan(hwaccel_flags=hw, vfilter=vf, encoder=enc, encoder_flags=eflags)


def build_command(
    input_path: str,
    output_path: str,
    plan: Plan,
    overwrite: bool,
) -> list[str]:
    cmd: list[str] = ["ffmpeg", "-hide_banner"]
    if overwrite:
        cmd.append("-y")
    cmd += plan.hwaccel_flags
    cmd += ["-i", input_path]
    if plan.vfilter:
        cmd += ["-vf", plan.vfilter]
    cmd += ["-c:v", plan.encoder]
    cmd += plan.encoder_flags
    cmd += ["-c:a", "copy", output_path]
    return cmd


# ---------- CLI ----------------------------------------------------------- #


def cmd_detect(args: argparse.Namespace) -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found on PATH", file=sys.stderr)
        return 2
    print(f"Platform: {platform.system()} {platform.machine()}")
    print("\n-- ffmpeg -hwaccels --")
    accels = list_hwaccels()
    for a in accels:
        print(f"  {a}")
    print("\n-- HW encoders --")
    for e in list_hw_encoders():
        print(f"  {e}")
    print("\n-- HW decoders --")
    for d in list_hw_decoders():
        print(f"  {d}")
    guess = platform_guess()
    print(f"\nAuto-pick: {guess}")
    return 0


def cmd_transcode(args: argparse.Namespace) -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found on PATH", file=sys.stderr)
        return 2
    accel = args.accel
    if accel == "auto":
        accel = platform_guess()
        if accel == "none":
            print("auto: no hardware acceleration detected", file=sys.stderr)
            return 2
        if args.verbose:
            print(f"auto-picked accel: {accel}", file=sys.stderr)

    plan = build_plan(
        accel=accel,
        codec=args.codec,
        quality=args.quality,
        resolution=args.resolution,
    )
    cmd = build_command(args.input, args.output, plan, overwrite=args.overwrite)

    if args.verbose or args.dry_run:
        print(" ".join(shlex.quote(a) for a in cmd))
    if args.dry_run:
        return 0

    try:
        rc = subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130
    return rc


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="hwaccel.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("detect", help="list available HW acceleration on this machine")

    t = sub.add_parser("transcode", help="build an accelerated ffmpeg command")
    t.add_argument("--input", "-i", required=True)
    t.add_argument("--output", "-o", required=True)
    t.add_argument("--accel", choices=ACCELS, default="auto")
    t.add_argument("--codec", choices=CODECS, default="h264")
    t.add_argument(
        "--quality",
        type=int,
        default=23,
        help="CRF-like quality knob (NVENC -cq / QSV -global_quality / VAAPI -qp). Lower = better.",
    )
    t.add_argument("--resolution", help="WxH, e.g. 1920x1080. If omitted, keep source.")
    t.add_argument("--overwrite", "-y", action="store_true")
    t.add_argument("--dry-run", action="store_true", help="print the command only")
    t.add_argument("--verbose", "-v", action="store_true")

    args = p.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "detect":
        return cmd_detect(args)
    if args.cmd == "transcode":
        return cmd_transcode(args)
    p.error(f"unknown subcommand {args.cmd!r}")
    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(main())
