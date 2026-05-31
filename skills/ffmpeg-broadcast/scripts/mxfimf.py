#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
mxfimf.py — broadcast/film delivery helpers for MXF, IMF, ProRes, XDCAM, SMPTE timecode.

Subcommands:
    mxf-op1a       Mux to MXF OP1a (broadcast single-file).
    mxf-opatom     Fan out to MXF OP-Atom (one essence per file, Avid/IMF).
    prores-mov     Encode ProRes in MOV mezzanine.
    xdcam-hd422    Encode XDCAM HD422 50 Mbps CBR MXF.
    set-timecode   Stamp SMPTE timecode (DF uses `;`, NDF uses `:`).
    identify-imf   Heuristic: is this MXF an IMF essence?

Common options: --dry-run, --verbose. Stdlib only. Non-interactive.

Examples:
    uv run mxfimf.py mxf-op1a --input in.mov --output out.mxf --codec dnxhd --timecode "01:00:00:00"
    uv run mxfimf.py mxf-opatom --input in.mov --outdir /tmp/opatom --codec dnxhr
    uv run mxfimf.py prores-mov --input in.mov --output out.mov --profile 3
    uv run mxfimf.py xdcam-hd422 --input in.mov --output out.mxf
    uv run mxfimf.py set-timecode --input in.mov --output out.mov --tc "01:00:00;00" --drop-frame
    uv run mxfimf.py identify-imf --input suspect.mxf
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


# ---- helpers ----------------------------------------------------------------


def _require(bin_name: str) -> str:
    path = shutil.which(bin_name)
    if not path:
        print(f"error: required binary not found on PATH: {bin_name}", file=sys.stderr)
        sys.exit(2)
    return path


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    if verbose or dry_run:
        printable = " ".join(_shquote(c) for c in cmd)
        print(f"[cmd] {printable}", file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _shquote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'$`\\*?[](){}<>|&;"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


def _check_input(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        sys.exit(1)
    return p


def _ffprobe_json(ffprobe: str, path: str) -> dict:
    try:
        out = subprocess.check_output(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            stderr=subprocess.STDOUT,
        )
        return json.loads(out.decode("utf-8", errors="replace"))
    except subprocess.CalledProcessError as e:
        print(
            f"error: ffprobe failed: {e.output.decode(errors='replace')}",
            file=sys.stderr,
        )
        sys.exit(1)


def _validate_timecode(tc: str, *, allow_drop: bool = True) -> tuple[str, bool]:
    """Return (tc, is_drop_frame). DF uses `;` before frames, NDF uses `:`."""
    if len(tc) != 11 or tc[2] != ":" or tc[5] != ":":
        print(
            f"error: timecode must be HH:MM:SS:FF or HH:MM:SS;FF, got {tc!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    sep = tc[8]
    if sep == ";":
        if not allow_drop:
            print("error: drop-frame not allowed here", file=sys.stderr)
            sys.exit(1)
        return tc, True
    if sep == ":":
        return tc, False
    print(
        f"error: bad timecode separator {sep!r} (must be ':' or ';')", file=sys.stderr
    )
    sys.exit(1)


# ---- video codec argument builders -----------------------------------------


def _vcodec_args(codec: str) -> list[str]:
    """Return the -c:v ... argv fragment for a logical codec name."""
    if codec == "dnxhd":
        return ["-c:v", "dnxhd", "-b:v", "120M", "-pix_fmt", "yuv422p"]
    if codec == "dnxhr":
        # Raster-independent DNxHR HQ 4:2:2 8-bit.
        return ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-pix_fmt", "yuv422p"]
    if codec == "xdcam":
        return [
            "-c:v",
            "mpeg2video",
            "-pix_fmt",
            "yuv422p",
            "-b:v",
            "50M",
            "-maxrate",
            "50M",
            "-minrate",
            "50M",
            "-bufsize",
            "17M",
            "-flags",
            "+ildct+ilme",
            "-top",
            "1",
        ]
    if codec == "prores":
        return [
            "-c:v",
            "prores_ks",
            "-profile:v",
            "3",
            "-pix_fmt",
            "yuv422p10le",
            "-vendor",
            "apl0",
        ]
    print(f"error: unknown codec {codec!r}", file=sys.stderr)
    sys.exit(1)


# ---- subcommands -----------------------------------------------------------


def cmd_mxf_op1a(args: argparse.Namespace) -> int:
    ff = _require("ffmpeg")
    _check_input(args.input)
    cmd = [
        ff,
        "-y",
        "-i",
        args.input,
        *_vcodec_args(args.codec),
        "-c:a",
        "pcm_s24le",
        "-ar",
        "48000",
    ]
    if args.timecode:
        _validate_timecode(args.timecode)
        cmd += ["-timecode", args.timecode]
    cmd += ["-f", "mxf", args.output]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_mxf_opatom(args: argparse.Namespace) -> int:
    ff = _require("ffmpeg")
    fp = _require("ffprobe")
    _check_input(args.input)

    outdir = Path(args.outdir)
    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)

    info = _ffprobe_json(fp, args.input) if not args.dry_run else {"streams": []}
    audio_streams = [
        s for s in info.get("streams", []) if s.get("codec_type") == "audio"
    ]

    # Video essence
    vcmd = [ff, "-y", "-i", args.input, "-map", "0:v:0", *_vcodec_args(args.codec)]
    if args.timecode:
        _validate_timecode(args.timecode)
        vcmd += ["-timecode", args.timecode]
    vcmd += ["-f", "mxf_opatom", str(outdir / "video.mxf")]
    rc = _run(vcmd, dry_run=args.dry_run, verbose=args.verbose)
    if rc != 0:
        return rc

    # Audio essences (one per audio stream; each OP-Atom file is one essence).
    n_audio = len(audio_streams) if not args.dry_run else 1
    for i in range(n_audio):
        acmd = [
            ff,
            "-y",
            "-i",
            args.input,
            "-map",
            f"0:a:{i}",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            "-f",
            "mxf_opatom",
            str(outdir / f"audio_{i}.mxf"),
        ]
        rc = _run(acmd, dry_run=args.dry_run, verbose=args.verbose)
        if rc != 0:
            return rc
    return 0


def cmd_prores_mov(args: argparse.Namespace) -> int:
    ff = _require("ffmpeg")
    _check_input(args.input)
    if args.profile not in (0, 1, 2, 3, 4, 5):
        print(
            "error: --profile must be 0..5 (0=Proxy,1=LT,2=422,3=HQ,4=4444,5=4444 XQ)",
            file=sys.stderr,
        )
        return 1
    pix_fmt = "yuv422p10le" if args.profile <= 3 else "yuva444p10le"
    cmd = [
        ff,
        "-y",
        "-i",
        args.input,
        "-c:v",
        "prores_ks",
        "-profile:v",
        str(args.profile),
        "-pix_fmt",
        pix_fmt,
        "-vendor",
        "apl0",
        "-c:a",
        "pcm_s24le",
        "-ar",
        "48000",
        args.output,
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_xdcam_hd422(args: argparse.Namespace) -> int:
    ff = _require("ffmpeg")
    _check_input(args.input)
    cmd = [
        ff,
        "-y",
        "-i",
        args.input,
        *_vcodec_args("xdcam"),
        "-c:a",
        "pcm_s24le",
        "-ar",
        "48000",
        "-f",
        "mxf",
        args.output,
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_set_timecode(args: argparse.Namespace) -> int:
    ff = _require("ffmpeg")
    _check_input(args.input)
    tc, is_df = _validate_timecode(args.tc)
    if args.drop_frame and not is_df:
        print(
            "warning: --drop-frame set but timecode uses ':'; converting last ':' to ';'",
            file=sys.stderr,
        )
        tc = tc[:8] + ";" + tc[9:]
    if is_df and not args.drop_frame:
        print("note: timecode uses ';' so drop-frame is inferred", file=sys.stderr)
    cmd = [ff, "-y", "-i", args.input, "-c", "copy", "-timecode", tc, args.output]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_identify_imf(args: argparse.Namespace) -> int:
    fp = _require("ffprobe")
    _check_input(args.input)
    info = _ffprobe_json(fp, args.input)
    vstreams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    is_mxf = (info.get("format", {}).get("format_name", "") or "").startswith("mxf")
    hints: list[str] = []
    if not is_mxf:
        hints.append("container is not MXF; not an IMF essence")
    for s in vstreams:
        codec = s.get("codec_name", "")
        pix = s.get("pix_fmt", "")
        if codec in {"jpeg2000", "j2k"}:
            hints.append("JPEG 2000 essence — consistent with SMPTE ST 2067-20 IMF")
        if codec == "prores":
            hints.append("ProRes essence — consistent with SMPTE ST 2067-21 ProRes IMF")
        if (
            pix
            and "10" not in pix
            and "12" not in pix
            and codec in {"jpeg2000", "prores"}
        ):
            hints.append(f"warning: IMF usually >= 10-bit; saw pix_fmt={pix}")
    looks_like_imf = any("SMPTE ST 2067" in h for h in hints)
    result = {
        "input": args.input,
        "is_mxf": is_mxf,
        "looks_like_imf_essence": looks_like_imf,
        "hints": hints,
        "note": (
            "ffmpeg cannot author IMF CPL/PKL/ASSETMAP. "
            "Use Netflix Photon or asdcplib/asdcp-wrap to package."
        ),
    }
    print(json.dumps(result, indent=2))
    return 0


# ---- CLI -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mxfimf.py",
        description="MXF/IMF/ProRes/XDCAM/timecode helpers (ffmpeg wrappers).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--dry-run", action="store_true", help="Print command, do not run."
        )
        sp.add_argument(
            "--verbose", action="store_true", help="Print command to stderr."
        )

    s = sub.add_parser("mxf-op1a", help="Mux to MXF OP1a (broadcast single-file).")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--codec", choices=["dnxhd", "dnxhr", "xdcam", "prores"], default="dnxhd"
    )
    s.add_argument(
        "--timecode", help='SMPTE TC, e.g. "01:00:00:00" (NDF) or "01:00:00;00" (DF).'
    )
    _common(s)
    s.set_defaults(func=cmd_mxf_op1a)

    s = sub.add_parser(
        "mxf-opatom", help="Fan out to MXF OP-Atom (one essence per file)."
    )
    s.add_argument("--input", required=True)
    s.add_argument("--outdir", required=True)
    s.add_argument(
        "--codec", choices=["dnxhd", "dnxhr", "xdcam", "prores"], default="dnxhd"
    )
    s.add_argument("--timecode")
    _common(s)
    s.set_defaults(func=cmd_mxf_opatom)

    s = sub.add_parser("prores-mov", help="Encode ProRes in MOV mezzanine.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--profile",
        type=int,
        default=3,
        help="0=Proxy,1=LT,2=422,3=HQ (default),4=4444,5=4444 XQ",
    )
    _common(s)
    s.set_defaults(func=cmd_prores_mov)

    s = sub.add_parser("xdcam-hd422", help="Encode XDCAM HD422 50 Mbps CBR MXF.")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    _common(s)
    s.set_defaults(func=cmd_xdcam_hd422)

    s = sub.add_parser(
        "set-timecode", help="Stamp SMPTE timecode onto a stream-copy output."
    )
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--tc", required=True, help="HH:MM:SS:FF or HH:MM:SS;FF")
    s.add_argument(
        "--drop-frame",
        action="store_true",
        help="Force drop-frame (converts trailing ':' to ';' if needed).",
    )
    _common(s)
    s.set_defaults(func=cmd_set_timecode)

    s = sub.add_parser("identify-imf", help="Heuristic: is this MXF an IMF essence?")
    s.add_argument("--input", required=True)
    _common(s)
    s.set_defaults(func=cmd_identify_imf)

    return p


def main() -> None:
    args = build_parser().parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
