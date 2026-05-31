#!/usr/bin/env python3
"""immersive.py — 360°/VR and stereoscopic 3D helpers built on ffmpeg's v360,
stereo3d, and framepack filters. Stdlib only, non-interactive.

Subcommands
-----------
  project     Convert between 360 projections (equirect, cubemap, eac, fisheye ...)
  flat-view   Render a rectilinear "virtual camera" view from a 360 source
  stereo3d    Convert between stereoscopic layouts (sbsl, tbl, ml ...)
  anaglyph    Flatten SBS/TAB stereo to an anaglyph (red-cyan etc.)
  framepack   Pack stereo into HDMI 1.4a compatible framepack formats

Every subcommand supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import List, Optional


# ---------------------------------------------------------------------------
# Friendly name → v360 type
# ---------------------------------------------------------------------------
PROJECTION_ALIASES = {
    "equirect": "e",
    "equirectangular": "e",
    "e": "e",
    "cubemap3x2": "c3x2",
    "c3x2": "c3x2",
    "cubemap6x1": "c6x1",
    "c6x1": "c6x1",
    "cubemap1x6": "c1x6",
    "c1x6": "c1x6",
    "eac": "eac",
    "flat": "flat",
    "rectilinear": "flat",
    "fisheye": "fisheye",
    "dfisheye": "dfisheye",
    "dualfisheye": "dfisheye",
    "hequirect": "hequirect",
    "half_equirectangular": "hequirect",
    "half-equirect": "hequirect",
    "vr180": "hequirect",
    "cylindrical": "cylindrical",
    "perspective": "perspective",
    "barrel": "barrel",
    "sinusoidal": "sinusoidal",
    "stereographic": "stereographic",
    "mercator": "mercator",
    "ball": "ball",
    "hammer": "hammer",
    "pannini": "pannini",
    "rfish": "rfish",
    "reverse-fisheye": "rfish",
}

STEREO3D_CODES = {
    "sbsl",
    "sbsr",
    "tbl",
    "tbr",
    "al",
    "ar",
    "ml",
    "mr",
    "abl",
    "abr",
    "arbg",
    "arcg",
    "arcc",
    "arch",
    "arcd",
    "aybd",
    "agmd",
    "agmg",
    "agmh",
    "irl",
    "irr",
    "icl",
    "icr",
    "hdmi",
}

ANAGLYPH_MODES = {
    "arbg",
    "arcg",
    "arcc",
    "arch",
    "arcd",
    "aybd",
    "agmd",
    "agmg",
    "agmh",
}

FRAMEPACK_MODES = {"sbs", "tab", "frameseq", "lines", "columns"}

INTERP_MODES = {
    "near",
    "linear",
    "cubic",
    "lanczos",
    "spline16",
    "gaussian",
    "mitchell",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def resolve_projection(name: str) -> str:
    key = name.strip().lower()
    if key not in PROJECTION_ALIASES:
        raise SystemExit(
            f"Unknown projection '{name}'. " f"Known: {sorted(set(PROJECTION_ALIASES))}"
        )
    return PROJECTION_ALIASES[key]


def run(cmd: List[str], dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    if dry_run or verbose:
        print(pretty)
    if dry_run:
        return 0
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        return 127


def parse_size(s: Optional[str]) -> Optional[tuple]:
    if not s:
        return None
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except Exception as exc:
        raise SystemExit(
            f"invalid --size '{s}', expected WxH (e.g. 1920x1080)"
        ) from exc


def build_ffmpeg(
    input_path: str,
    vf: str,
    output_path: str,
    crf: int = 18,
    extra_video: Optional[List[str]] = None,
    copy_audio: bool = True,
) -> List[str]:
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", vf]
    cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", "medium"]
    if extra_video:
        cmd += extra_video
    if copy_audio:
        cmd += ["-c:a", "copy"]
    cmd += [output_path]
    return cmd


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def cmd_project(args: argparse.Namespace) -> int:
    src = resolve_projection(args.from_)
    dst = resolve_projection(args.to)
    parts = [f"v360={src}:{dst}"]
    # Rotations
    if args.yaw:
        parts.append(f"yaw={args.yaw}")
    if args.pitch:
        parts.append(f"pitch={args.pitch}")
    if args.roll:
        parts.append(f"roll={args.roll}")
    # Input fisheye FOV, if given
    if args.ih_fov:
        parts.append(f"ih_fov={args.ih_fov}")
    if args.iv_fov:
        parts.append(f"iv_fov={args.iv_fov}")
    # Interpolation
    parts.append(f"interp={args.interp}")
    vf = ":".join(parts)
    cmd = build_ffmpeg(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_flat_view(args: argparse.Namespace) -> int:
    src = resolve_projection(args.from_)
    v360 = (
        f"v360={src}:flat"
        f":yaw={args.yaw}:pitch={args.pitch}:roll={args.roll}"
        f":h_fov={args.h_fov}:v_fov={args.v_fov}"
        f":interp={args.interp}"
    )
    size = parse_size(args.size)
    vf = v360
    if size:
        vf += f",scale={size[0]}:{size[1]}"
    cmd = build_ffmpeg(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_stereo3d(args: argparse.Namespace) -> int:
    src = args.from_.lower()
    dst = args.to.lower()
    for code, label in ((src, "--from"), (dst, "--to")):
        if code not in STEREO3D_CODES:
            raise SystemExit(
                f"unknown stereo3d code '{code}' for {label}. "
                f"Known: {sorted(STEREO3D_CODES)}"
            )
    vf = f"stereo3d={src}:{dst}"
    cmd = build_ffmpeg(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_anaglyph(args: argparse.Namespace) -> int:
    src = args.from_.lower()
    mode = args.mode.lower()
    if src not in STEREO3D_CODES:
        raise SystemExit(f"unknown input stereo code '{src}'")
    if mode not in ANAGLYPH_MODES:
        raise SystemExit(
            f"unknown anaglyph mode '{mode}'. Known: {sorted(ANAGLYPH_MODES)}"
        )
    vf = f"stereo3d={src}:{mode}"
    cmd = build_ffmpeg(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


def cmd_framepack(args: argparse.Namespace) -> int:
    mode = args.mode.lower()
    if mode not in FRAMEPACK_MODES:
        raise SystemExit(
            f"unknown framepack mode '{mode}'. Known: {sorted(FRAMEPACK_MODES)}"
        )
    vf = f"framepack={mode}"
    cmd = build_ffmpeg(args.input, vf, args.output)
    return run(cmd, args.dry_run, args.verbose)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="immersive.py",
        description="ffmpeg wrappers for 360/VR and stereoscopic 3D video.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    common_io = argparse.ArgumentParser(add_help=False)
    common_io.add_argument("--input", "-i", required=True, help="input media path")
    common_io.add_argument("--output", "-o", required=True, help="output media path")
    common_io.add_argument(
        "--dry-run",
        action="store_true",
        help="print the ffmpeg command without running it",
    )
    common_io.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="echo the ffmpeg command before running",
    )

    # project
    pr = sub.add_parser(
        "project", parents=[common_io], help="convert between 360 projections (v360)"
    )
    pr.add_argument(
        "--from",
        dest="from_",
        required=True,
        help=f"input projection ({sorted(set(PROJECTION_ALIASES))})",
    )
    pr.add_argument("--to", required=True, help="output projection")
    pr.add_argument(
        "--interp",
        default="cubic",
        choices=sorted(INTERP_MODES),
        help="interpolation (default: cubic)",
    )
    pr.add_argument("--yaw", type=float, default=0.0)
    pr.add_argument("--pitch", type=float, default=0.0)
    pr.add_argument("--roll", type=float, default=0.0)
    pr.add_argument(
        "--ih-fov",
        dest="ih_fov",
        type=float,
        default=None,
        help="input horizontal FOV (required for fisheye/dfisheye inputs)",
    )
    pr.add_argument(
        "--iv-fov",
        dest="iv_fov",
        type=float,
        default=None,
        help="input vertical FOV (required for fisheye/dfisheye inputs)",
    )
    pr.set_defaults(func=cmd_project)

    # flat-view
    fv = sub.add_parser(
        "flat-view",
        parents=[common_io],
        help="render a rectilinear virtual camera view from a 360 source",
    )
    fv.add_argument(
        "--from",
        dest="from_",
        default="equirect",
        help="input projection (default: equirect)",
    )
    fv.add_argument("--yaw", type=float, default=0.0)
    fv.add_argument("--pitch", type=float, default=0.0)
    fv.add_argument("--roll", type=float, default=0.0)
    fv.add_argument(
        "--h-fov",
        dest="h_fov",
        type=float,
        default=90.0,
        help="output horizontal FOV degrees (default: 90)",
    )
    fv.add_argument(
        "--v-fov",
        dest="v_fov",
        type=float,
        default=60.0,
        help="output vertical FOV degrees (default: 60)",
    )
    fv.add_argument(
        "--size", default="1920x1080", help="output WxH (default: 1920x1080)"
    )
    fv.add_argument("--interp", default="cubic", choices=sorted(INTERP_MODES))
    fv.set_defaults(func=cmd_flat_view)

    # stereo3d
    s3 = sub.add_parser(
        "stereo3d", parents=[common_io], help="convert stereoscopic 3D layouts"
    )
    s3.add_argument(
        "--from",
        dest="from_",
        required=True,
        help=f"input stereo code (e.g. sbsl, sbsr, tbl, tbr, ml, mr ...)",
    )
    s3.add_argument("--to", required=True, help="output stereo code")
    s3.set_defaults(func=cmd_stereo3d)

    # anaglyph
    an = sub.add_parser(
        "anaglyph", parents=[common_io], help="flatten SBS/TAB into anaglyph 3D"
    )
    an.add_argument(
        "--from", dest="from_", default="sbsl", help="input stereo code (default: sbsl)"
    )
    an.add_argument(
        "--mode",
        default="arcg",
        help=f"anaglyph mode (default: arcg). One of {sorted(ANAGLYPH_MODES)}",
    )
    an.set_defaults(func=cmd_anaglyph)

    # framepack
    fp = sub.add_parser(
        "framepack", parents=[common_io], help="HDMI 1.4a frame packing"
    )
    fp.add_argument(
        "--mode", required=True, help=f"framepack mode: {sorted(FRAMEPACK_MODES)}"
    )
    fp.set_defaults(func=cmd_framepack)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
