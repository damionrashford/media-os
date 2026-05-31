#!/usr/bin/env python3
"""colorpro.py — OCIO / ACES / ICC color management wrapper around ffmpeg.

Stdlib only. Non-interactive.

Subcommands:
  check                              detect libOpenColorIO support + $OCIO config
  transform                          arbitrary pinput -> poutput via ocio filter
  aces-to-rec709                     preset: ACES2065-1 -> "Output - Rec.709"
  aces-to-dcip3                      preset: ACES2065-1 -> "Output - DCI-P3 D65"
  bake-lut                           use ociobake to emit a .cube (fallback path)
  attach-icc                         embed ICC profile via iccgen filter

Common flags: --dry-run, --verbose.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _log(verbose: bool, *parts: object) -> None:
    if verbose:
        print("[colorpro]", *parts, file=sys.stderr)


def _which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def _run(
    cmd: Sequence[str], *, dry_run: bool, verbose: bool, capture: bool = False
) -> subprocess.CompletedProcess:
    printable = " ".join(shlex.quote(str(c)) for c in cmd)
    if dry_run:
        print(f"DRY-RUN: {printable}")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    _log(verbose, "exec:", printable)
    return subprocess.run(
        list(cmd),
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def _require_ffmpeg() -> str:
    path = _which("ffmpeg")
    if not path:
        print("ERROR: ffmpeg not found on PATH", file=sys.stderr)
        sys.exit(2)
    return path


def _has_ocio_filter(ffmpeg: str) -> bool:
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.decode("utf-8", "replace")
    except OSError:
        return False
    for line in out.splitlines():
        # filter list lines look like " T.. ocio             V->V       ..."
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "ocio":
            return True
    return False


def _escape_filter_value(v: str) -> str:
    """Escape values embedded inside an ffmpeg filter argument list.

    ffmpeg filter arg syntax uses ':' as separator and '\\' as escape.
    Commas, colons, single-quotes and backslashes must be escaped.
    """
    out = []
    for ch in v:
        if ch in ("\\", ":", ",", "'", "[", "]"):
            out.append("\\")
        out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    has_ocio = _has_ocio_filter(ffmpeg)
    ocio_env = os.environ.get("OCIO")
    ociobake = _which("ociobake")
    ociocheck = _which("ociocheck")

    print(f"ffmpeg:          {ffmpeg}")
    print(
        f"ocio filter:     {'YES' if has_ocio else 'NO (rebuild with --enable-libocio or use bake-lut)'}"
    )
    print(f"$OCIO env:       {ocio_env or '(unset)'}")
    if ocio_env:
        print(f"  config exists: {'YES' if os.path.isfile(ocio_env) else 'NO'}")
    print(f"ociobake:        {ociobake or '(not found — install OpenColorIO tools)'}")
    print(f"ociocheck:       {ociocheck or '(not found)'}")
    return 0 if has_ocio or ociobake else 1


def _build_ocio_vf(
    pinput: str, poutput: str, config: Optional[str], look: Optional[str]
) -> str:
    pairs = []
    if config:
        pairs.append(f"config={_escape_filter_value(config)}")
    pairs.append(f"pinput={_escape_filter_value(pinput)}")
    pairs.append(f"poutput={_escape_filter_value(poutput)}")
    if look:
        pairs.append(f"look={_escape_filter_value(look)}")
    return "ocio=" + ":".join(pairs)


def _transform_pipeline(
    pinput: str, poutput: str, config: Optional[str], look: Optional[str]
) -> str:
    ocio = _build_ocio_vf(pinput, poutput, config, look)
    # float in for precision, 4:2:0 8-bit out for broad compatibility
    return f"format=gbrpf32le,{ocio},format=yuv420p"


def cmd_transform(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    if not _has_ocio_filter(ffmpeg):
        print(
            "ERROR: ffmpeg lacks the 'ocio' filter. Rebuild with --enable-libocio "
            "or use the 'bake-lut' subcommand + lut3d filter.",
            file=sys.stderr,
        )
        return 3
    vf = _transform_pipeline(args.pinput, args.poutput, args.config, args.look)
    cmd = [ffmpeg, "-hide_banner", "-y", "-i", args.input, "-vf", vf]
    if args.crf is not None:
        cmd += ["-c:v", "libx264", "-crf", str(args.crf)]
    cmd += ["-c:a", "copy", args.output]
    res = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return res.returncode


def cmd_aces_to_rec709(args: argparse.Namespace) -> int:
    args.pinput = "ACES2065-1"
    args.poutput = "Output - Rec.709"
    args.look = None
    args.config = None
    return cmd_transform(args)


def cmd_aces_to_dcip3(args: argparse.Namespace) -> int:
    args.pinput = "ACES2065-1"
    args.poutput = "Output - DCI-P3 D65"
    args.look = None
    args.config = None
    return cmd_transform(args)


def cmd_bake_lut(args: argparse.Namespace) -> int:
    ociobake = _which("ociobake")
    if not ociobake:
        print(
            "ERROR: ociobake not found. Install OpenColorIO CLI tools.", file=sys.stderr
        )
        return 2
    cmd = [
        ociobake,
        "--iconfig",
        args.config,
        "--inputspace",
        args.pinput,
        "--outputspace",
        args.poutput,
        "--format",
        args.format,
        "--lutsize",
        str(args.lutsize),
    ]
    printable = (
        " ".join(shlex.quote(str(c)) for c in cmd) + f" > {shlex.quote(args.output)}"
    )
    if args.dry_run:
        print(f"DRY-RUN: {printable}")
        return 0
    _log(args.verbose, "exec:", printable)
    with open(args.output, "wb") as fh:
        res = subprocess.run(cmd, check=False, stdout=fh, stderr=subprocess.PIPE)
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode("utf-8", "replace"))
    else:
        print(f"Wrote {args.output}")
    return res.returncode


def cmd_attach_icc(args: argparse.Namespace) -> int:
    ffmpeg = _require_ffmpeg()
    primaries = _escape_filter_value(args.primaries)
    trc = _escape_filter_value(args.trc)
    vf = f"iccgen=primaries={primaries}:trc={trc}"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        args.input,
        "-vf",
        vf,
        "-c:v",
        args.vcodec,
    ]
    if args.vcodec == "libx264":
        cmd += ["-crf", str(args.crf)]
    cmd += ["-c:a", "copy", args.output]
    res = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return res.returncode


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def _add_common(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--dry-run", action="store_true", help="print commands, don't execute"
    )
    sub.add_argument("--verbose", action="store_true", help="log commands to stderr")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="colorpro",
        description="OCIO/ACES/ICC color management wrapper around ffmpeg",
    )
    sp = p.add_subparsers(dest="command", required=True)

    pc = sp.add_parser("check", help="detect libOpenColorIO support + $OCIO")
    _add_common(pc)
    pc.set_defaults(func=cmd_check)

    pt = sp.add_parser("transform", help="arbitrary pinput -> poutput via ocio filter")
    pt.add_argument("--input", "-i", required=True)
    pt.add_argument("--output", "-o", required=True)
    pt.add_argument(
        "--pinput", required=True, help='input colorspace name (e.g. "ACES2065-1")'
    )
    pt.add_argument(
        "--poutput",
        required=True,
        help='output colorspace name (e.g. "Output - Rec.709")',
    )
    pt.add_argument("--config", help="explicit OCIO config path (else uses $OCIO)")
    pt.add_argument("--look", help="OCIO look / LMT name to apply")
    pt.add_argument(
        "--crf",
        type=int,
        default=18,
        help="x264 CRF (default 18); set None for stream copy",
    )
    _add_common(pt)
    pt.set_defaults(func=cmd_transform)

    pa = sp.add_parser("aces-to-rec709", help="preset: ACES2065-1 -> Rec.709")
    pa.add_argument("--input", "-i", required=True)
    pa.add_argument("--output", "-o", required=True)
    pa.add_argument("--crf", type=int, default=18)
    _add_common(pa)
    pa.set_defaults(func=cmd_aces_to_rec709)

    pd = sp.add_parser("aces-to-dcip3", help="preset: ACES2065-1 -> DCI-P3 D65")
    pd.add_argument("--input", "-i", required=True)
    pd.add_argument("--output", "-o", required=True)
    pd.add_argument("--crf", type=int, default=18)
    _add_common(pd)
    pd.set_defaults(func=cmd_aces_to_dcip3)

    pb = sp.add_parser("bake-lut", help="emit a .cube via ociobake (fallback path)")
    pb.add_argument("--config", required=True, help="path to config.ocio")
    pb.add_argument("--pinput", required=True)
    pb.add_argument("--poutput", required=True)
    pb.add_argument("--output", "-o", required=True, help="output .cube path")
    pb.add_argument(
        "--format",
        default="cinespace",
        help="ociobake format (cinespace|resolve_cube|...)",
    )
    pb.add_argument("--lutsize", type=int, default=33)
    _add_common(pb)
    pb.set_defaults(func=cmd_bake_lut)

    pi = sp.add_parser("attach-icc", help="embed ICC profile via iccgen filter")
    pi.add_argument("--input", "-i", required=True)
    pi.add_argument("--output", "-o", required=True)
    pi.add_argument(
        "--primaries",
        default="bt709",
        help="bt709|bt2020|smpte431|smpte432 (default bt709)",
    )
    pi.add_argument(
        "--trc",
        default="iec61966-2-1",
        help="iec61966-2-1 (sRGB) | bt709 | smpte2084 | arib-std-b67 (HLG)",
    )
    pi.add_argument("--vcodec", default="libx264")
    pi.add_argument("--crf", type=int, default=18)
    _add_common(pi)
    pi.set_defaults(func=cmd_attach_icc)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
