#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Lens correction, perspective, and geometric transforms via ffmpeg.

Subcommands:
    undistort-barrel     lenscorrection with negative k1 (GoPro, fisheye)
    undistort-pincushion lenscorrection with positive k1 (telephoto)
    lensfun              lensfun DB-driven correction (build-flag gated)
    perspective          4-corner warp for keystone fix
    vignette             add or remove vignette
    rotate               rotate by arbitrary degrees
    shear                skew (shx, shy)

Global flags: --dry-run prints the command without running; --verbose echoes.
Stdlib only. Non-interactive.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from typing import Sequence


def _build_base(
    input_path: str, vf: str, output_path: str, pix_fmt: str = "yuv420p"
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        input_path,
        "-vf",
        vf,
        "-pix_fmt",
        pix_fmt,
        "-c:a",
        "copy",
        output_path,
    ]


def _run(cmd: Sequence[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"$ {pretty}")
    if dry_run:
        return 0
    if shutil.which(cmd[0]) is None:
        print(f"error: {cmd[0]!r} not found in PATH", file=sys.stderr)
        return 127
    proc = subprocess.run(cmd, check=False)
    if verbose:
        print(f"[exit {proc.returncode}]")
    return proc.returncode


def cmd_undistort_barrel(args: argparse.Namespace) -> int:
    vf = f"lenscorrection=k1={args.k1}:k2={args.k2}:cx={args.cx}:cy={args.cy}"
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_undistort_pincushion(args: argparse.Namespace) -> int:
    # Same filter, user supplies positive k1.
    vf = f"lenscorrection=k1={args.k1}:k2={args.k2}:cx={args.cx}:cy={args.cy}"
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_lensfun(args: argparse.Namespace) -> int:
    parts = [
        f"make={args.make}",
        f"model={args.model}",
    ]
    if args.lens_model:
        parts.append(f"lens_model={args.lens_model}")
    if args.focal is not None:
        parts.append(f"focal_length={args.focal}")
    if args.aperture is not None:
        parts.append(f"aperture={args.aperture}")
    parts.append(f"mode={args.mode}")
    vf = "lensfun=" + ":".join(parts)
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_perspective(args: argparse.Namespace) -> int:
    corners = [c.strip() for c in args.corners.split(";") if c.strip()]
    if len(corners) != 4:
        print(
            "error: --corners must be 4 points 'x,y' separated by ';' (TL;TR;BL;BR)",
            file=sys.stderr,
        )
        return 2
    coords: list[tuple[str, str]] = []
    for c in corners:
        xy = c.split(",")
        if len(xy) != 2:
            print(f"error: bad corner {c!r}", file=sys.stderr)
            return 2
        coords.append((xy[0].strip(), xy[1].strip()))
    vf_parts = []
    for i, (x, y) in enumerate(coords):
        vf_parts.append(f"x{i}={x}:y{i}={y}")
    vf_parts.append(f"interpolation={args.interpolation}")
    vf_parts.append(f"sense={args.sense}")
    vf = "perspective=" + ":".join(vf_parts)
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_vignette(args: argparse.Namespace) -> int:
    vf = f"vignette=angle={args.angle}:mode={args.mode}"
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_rotate(args: argparse.Namespace) -> int:
    # Degrees to radians expression for ffmpeg's rotate filter.
    angle_expr = f"{args.degrees}*PI/180"
    if args.expand_canvas:
        vf = f"rotate={angle_expr}:ow=rotw({angle_expr}):oh=roth({angle_expr}):c={args.fill}"
    else:
        vf = f"rotate={angle_expr}:c={args.fill}"
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_shear(args: argparse.Namespace) -> int:
    vf = f"shear=shx={args.shx}:shy={args.shy}:interp={args.interp}"
    return _run(
        _build_base(args.input, vf, args.output),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--input", required=True, help="input media path")
    sp.add_argument("--output", required=True, help="output media path")
    sp.add_argument(
        "--dry-run", action="store_true", help="print command without running"
    )
    sp.add_argument("--verbose", action="store_true", help="echo exit code after run")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lens.py",
        description="Lens correction, perspective, and geometric transforms via ffmpeg.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # undistort-barrel
    sp = sub.add_parser(
        "undistort-barrel",
        help="Correct barrel (fisheye/wide) distortion with negative k1.",
    )
    _add_common(sp)
    sp.add_argument(
        "--k1",
        type=float,
        default=-0.3,
        help="radial coefficient 1 (negative for barrel undistort)",
    )
    sp.add_argument("--k2", type=float, default=0.0, help="radial coefficient 2")
    sp.add_argument(
        "--cx", type=float, default=0.5, help="normalized center x (default 0.5)"
    )
    sp.add_argument(
        "--cy", type=float, default=0.5, help="normalized center y (default 0.5)"
    )
    sp.set_defaults(func=cmd_undistort_barrel)

    # undistort-pincushion
    sp = sub.add_parser(
        "undistort-pincushion",
        help="Correct pincushion (telephoto) distortion with positive k1.",
    )
    _add_common(sp)
    sp.add_argument(
        "--k1",
        type=float,
        default=0.3,
        help="radial coefficient 1 (positive for pincushion undistort)",
    )
    sp.add_argument("--k2", type=float, default=0.0, help="radial coefficient 2")
    sp.add_argument("--cx", type=float, default=0.5)
    sp.add_argument("--cy", type=float, default=0.5)
    sp.set_defaults(func=cmd_undistort_pincushion)

    # lensfun
    sp = sub.add_parser(
        "lensfun",
        help="Correct using lensfun database (needs --enable-liblensfun build + DB).",
    )
    _add_common(sp)
    sp.add_argument("--make", required=True, help="camera make, e.g. GoPro")
    sp.add_argument("--model", required=True, help="camera model, e.g. HERO9 Black")
    sp.add_argument(
        "--lens-model",
        dest="lens_model",
        default=None,
        help="lens model string from lensfun DB",
    )
    sp.add_argument("--focal", type=float, default=None, help="focal length in mm")
    sp.add_argument("--aperture", type=float, default=None, help="aperture f-number")
    sp.add_argument(
        "--mode", default="geometry", choices=["geometry", "tca", "vignetting", "all"]
    )
    sp.set_defaults(func=cmd_lensfun)

    # perspective
    sp = sub.add_parser("perspective", help="4-corner warp (keystone / trapezoid fix).")
    _add_common(sp)
    sp.add_argument(
        "--corners",
        required=True,
        help='4 points in pixel coords: "x0,y0;x1,y1;x2,y2;x3,y3" (TL;TR;BL;BR)',
    )
    sp.add_argument("--interpolation", default="linear", choices=["linear", "cubic"])
    sp.add_argument("--sense", default="source", choices=["source", "destination"])
    sp.set_defaults(func=cmd_perspective)

    # vignette
    sp = sub.add_parser("vignette", help="Add or remove vignette.")
    _add_common(sp)
    sp.add_argument(
        "--angle", default="PI/5", help="cone half-angle in radians (smaller = harsher)"
    )
    sp.add_argument(
        "--mode",
        default="forward",
        choices=["forward", "backward"],
        help="backward = REMOVE vignette",
    )
    sp.set_defaults(func=cmd_vignette)

    # rotate
    sp = sub.add_parser("rotate", help="Rotate by arbitrary degrees.")
    _add_common(sp)
    sp.add_argument(
        "--degrees", type=float, required=True, help="rotation angle in DEGREES"
    )
    sp.add_argument(
        "--expand-canvas",
        action="store_true",
        help="auto-expand canvas via rotw()/roth()",
    )
    sp.add_argument("--fill", default="black", help="fill color for corners")
    sp.set_defaults(func=cmd_rotate)

    # shear
    sp = sub.add_parser("shear", help="Apply shear (skew).")
    _add_common(sp)
    sp.add_argument("--shx", type=float, default=0.2, help="x-shift per unit y")
    sp.add_argument("--shy", type=float, default=0.0, help="y-shift per unit x")
    sp.add_argument("--interp", default="bilinear", choices=["nearest", "bilinear"])
    sp.set_defaults(func=cmd_shear)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
