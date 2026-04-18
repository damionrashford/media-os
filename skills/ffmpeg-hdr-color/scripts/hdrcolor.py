#!/usr/bin/env python3
"""HDR / color-space helper for ffmpeg.

Subcommands:
  detect            ffprobe-based HDR type classifier (SDR/HDR10/HDR10+/HLG/DoVi).
  hdr-to-sdr        Tone-map PQ HDR (HDR10 or DV p5) to BT.709 SDR.
  hlg-to-sdr        Tone-map HLG to BT.709 SDR.
  bt2020-to-bt709   SDR-to-SDR primaries/matrix/transfer conversion (no tone-map).

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from typing import Optional


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if verbose or dry_run:
        print(printable, file=sys.stderr)
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def _ffprobe_json(input_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=color_space,color_transfer,color_primaries,color_range,codec_name,width,height"
        ":stream_side_data=+",
        "-of",
        "json",
        input_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr.decode(errors="replace"))
        raise SystemExit(2)
    except FileNotFoundError:
        raise SystemExit("ffprobe not found on PATH")
    return json.loads(out.decode("utf-8", errors="replace"))


def _classify(probe: dict) -> dict:
    streams = probe.get("streams") or []
    if not streams:
        return {"type": "UNKNOWN", "reason": "no video stream"}
    s = streams[0]
    trc = (s.get("color_transfer") or "").lower()
    prim = (s.get("color_primaries") or "").lower()
    space = (s.get("color_space") or "").lower()
    side = s.get("side_data_list") or []
    side_types = [(d.get("side_data_type") or "") for d in side]

    has_dovi = any(
        "dovi" in t.lower() or "dolby vision" in t.lower() for t in side_types
    )
    has_hdr10plus = any(
        "hdr dynamic metadata" in t.lower() or "2094" in t.lower() for t in side_types
    )
    has_mastering = any(
        "mastering display" in t.lower() or "content light" in t.lower()
        for t in side_types
    )

    if has_dovi:
        kind = "DoVi"
    elif trc == "smpte2084" and has_hdr10plus:
        kind = "HDR10+"
    elif trc == "smpte2084":
        kind = "HDR10"
    elif trc in ("arib-std-b67", "bt2020-10", "bt2020-12") and prim == "bt2020":
        kind = "HLG" if trc == "arib-std-b67" else "BT2020-SDR"
    elif prim == "bt2020" and trc not in ("smpte2084", "arib-std-b67"):
        kind = "BT2020-SDR"
    else:
        kind = "SDR"

    return {
        "type": kind,
        "color_transfer": trc or None,
        "color_primaries": prim or None,
        "color_space": space or None,
        "side_data_types": side_types,
        "has_mastering_metadata": has_mastering,
        "has_hdr10plus_metadata": has_hdr10plus,
        "has_dovi_metadata": has_dovi,
        "codec_name": s.get("codec_name"),
        "width": s.get("width"),
        "height": s.get("height"),
    }


# ---------- filter chain builders ----------

_TAIL_TAGS = [
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-colorspace",
    "bt709",
    "-color_range",
    "tv",
]


def _vf_tonemap_pq(desat: float = 0.0, npl: int = 100) -> str:
    return (
        f"zscale=t=linear:npl={npl},format=gbrpf32le,"
        f"zscale=p=bt709,"
        f"tonemap=tonemap=hable:desat={desat},"
        f"zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
    )


def _vf_tonemap_hlg(desat: float = 0.0, npl: int = 100) -> str:
    return (
        f"zscale=t=linear:npl={npl}:tin=arib-std-b67,format=gbrpf32le,"
        f"zscale=p=bt709,"
        f"tonemap=tonemap=hable:desat={desat},"
        f"zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
    )


def _vf_libplacebo() -> str:
    return (
        "format=yuv420p10le,hwupload,"
        "libplacebo=tonemapping=bt.2390:colorspace=bt709:"
        "color_primaries=bt709:color_trc=bt709:format=yuv420p,"
        "hwdownload,format=yuv420p"
    )


def _vf_bt2020_to_bt709() -> str:
    return "zscale=primaries=709:transfer=709:matrix=709"


# ---------- subcommands ----------


def cmd_detect(args: argparse.Namespace) -> int:
    probe = _ffprobe_json(args.input)
    result = _classify(probe)
    print(json.dumps(result, indent=2))
    return 0


def _build_hdr_to_sdr_cmd(args: argparse.Namespace) -> list[str]:
    cmd: list[str] = ["ffmpeg", "-hide_banner", "-y"]
    if args.method == "libplacebo":
        cmd.extend(["-init_hw_device", "vulkan"])
    cmd.extend(["-i", args.input])
    if args.method == "libplacebo":
        vf = _vf_libplacebo()
    else:
        vf = _vf_tonemap_pq(desat=args.desat, npl=args.npl)
    cmd.extend(["-vf", vf])
    cmd.extend(["-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset])
    cmd.extend(["-c:a", "copy"])
    cmd.extend(_TAIL_TAGS)
    cmd.append(args.output)
    return cmd


def cmd_hdr_to_sdr(args: argparse.Namespace) -> int:
    cmd = _build_hdr_to_sdr_cmd(args)
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_hlg_to_sdr(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        args.input,
        "-vf",
        _vf_tonemap_hlg(desat=args.desat, npl=args.npl),
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
        *_TAIL_TAGS,
        args.output,
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_bt2020_to_bt709(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        args.input,
        "-vf",
        _vf_bt2020_to_bt709(),
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
        *_TAIL_TAGS,
        args.output,
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------- argparse ----------


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run", action="store_true", help="Print command, don't execute."
    )
    common.add_argument(
        "--verbose", action="store_true", help="Print command before executing."
    )

    p = argparse.ArgumentParser(
        prog="hdrcolor.py",
        description="HDR/color helper for ffmpeg.",
        parents=[common],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_detect = sub.add_parser(
        "detect", help="Classify HDR type via ffprobe.", parents=[common]
    )
    p_detect.add_argument("--input", required=True)
    p_detect.set_defaults(func=cmd_detect)

    p_hdr = sub.add_parser(
        "hdr-to-sdr", help="Tone-map PQ HDR to BT.709 SDR.", parents=[common]
    )
    p_hdr.add_argument("--input", required=True)
    p_hdr.add_argument("--output", required=True)
    p_hdr.add_argument("--method", choices=("tonemap", "libplacebo"), default="tonemap")
    p_hdr.add_argument("--crf", type=int, default=19)
    p_hdr.add_argument("--preset", default="medium")
    p_hdr.add_argument("--desat", type=float, default=0.0)
    p_hdr.add_argument("--npl", type=int, default=100)
    p_hdr.set_defaults(func=cmd_hdr_to_sdr)

    p_hlg = sub.add_parser(
        "hlg-to-sdr", help="Tone-map HLG to BT.709 SDR.", parents=[common]
    )
    p_hlg.add_argument("--input", required=True)
    p_hlg.add_argument("--output", required=True)
    p_hlg.add_argument("--crf", type=int, default=19)
    p_hlg.add_argument("--preset", default="medium")
    p_hlg.add_argument("--desat", type=float, default=0.0)
    p_hlg.add_argument("--npl", type=int, default=100)
    p_hlg.set_defaults(func=cmd_hlg_to_sdr)

    p_bt = sub.add_parser(
        "bt2020-to-bt709",
        help="SDR-to-SDR BT.2020 to BT.709 conversion.",
        parents=[common],
    )
    p_bt.add_argument("--input", required=True)
    p_bt.add_argument("--output", required=True)
    p_bt.add_argument("--crf", type=int, default=18)
    p_bt.add_argument("--preset", default="medium")
    p_bt.set_defaults(func=cmd_bt2020_to_bt709)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
