#!/usr/bin/env python3
"""ivtc.py — inverse telecine / deinterlace / decimate / dejudder helper for ffmpeg.

Subcommands:
  detect       Run idet + vfrdet and report field-type and VFR statistics.
  ivtc         Canonical or pullup-based inverse telecine to 23.976p.
  deinterlace  True interlaced -> progressive (bwdif / yadif / w3fdif / estdif / kerndeint / mcdeint).
  decimate     mpdecimate-style duplicate-frame removal with PTS reset.
  dejudder     Remove 4/5-cycle telecine judder.

Global flags:
  --dry-run    Print the ffmpeg command without executing it.
  --verbose    Add -v info (default is -hide_banner -v error).

Stdlib only. Non-interactive. Prints the ffmpeg invocation before running it.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from typing import List, Tuple


FFMPEG = "ffmpeg"


def _shell(cmd: List[str]) -> str:
    return " ".join(shlex.quote(c) for c in cmd)


def _run(cmd: List[str], dry_run: bool, capture: bool = False) -> Tuple[int, str, str]:
    print("$ " + _shell(cmd), file=sys.stderr)
    if dry_run:
        return 0, "", ""
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    return proc.returncode, out, err


def _common_flags(verbose: bool) -> List[str]:
    return ["-hide_banner", "-nostdin"] + (
        ["-v", "info"] if verbose else ["-v", "error", "-stats"]
    )


# -------- detect --------


def _parse_idet(stderr: str) -> dict:
    """Pull the 'Multi frame detection' and 'Repeated Fields' lines from idet output."""
    result: dict = {
        "single": {},
        "multiple": {},
        "repeated": {},
        "raw": [],
    }
    for line in stderr.splitlines():
        s = line.strip()
        if "idet" not in s.lower() and "Parsed_idet" not in s:
            continue
        result["raw"].append(s)
        # match blocks like: "Single frame detection: TFF: 10 BFF: 2 Progressive: 988 Undetermined: 0"
        m = re.search(
            r"Single frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)",
            s,
        )
        if m:
            tff, bff, prog, und = map(int, m.groups())
            total = tff + bff + prog + und
            result["single"] = {
                "tff": tff,
                "bff": bff,
                "progressive": prog,
                "undetermined": und,
                "total": total,
            }
        m = re.search(
            r"Multi frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)",
            s,
        )
        if m:
            tff, bff, prog, und = map(int, m.groups())
            total = tff + bff + prog + und
            result["multiple"] = {
                "tff": tff,
                "bff": bff,
                "progressive": prog,
                "undetermined": und,
                "total": total,
            }
        m = re.search(
            r"Repeated Fields:\s*Neither:\s*(\d+)\s*Top:\s*(\d+)\s*Bottom:\s*(\d+)", s
        )
        if m:
            neither, top, bottom = map(int, m.groups())
            total = neither + top + bottom
            result["repeated"] = {
                "neither": neither,
                "top": top,
                "bottom": bottom,
                "total": total,
            }
    return result


def _parse_vfrdet(stderr: str) -> dict:
    """Pull VFR score from vfrdet."""
    for line in stderr.splitlines():
        m = re.search(r"VFR:(\S+)\s+CFR:(\S+)", line)
        if m:
            return {"vfr": m.group(1), "cfr": m.group(2), "raw": line.strip()}
        m = re.search(r"VFR:\s*([\d.]+)", line)
        if m:
            return {"vfr": m.group(1), "raw": line.strip()}
    return {}


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}%" if total else "n/a"


def cmd_detect(args: argparse.Namespace) -> int:
    common = _common_flags(args.verbose)
    idet_cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-filter:v",
        "idet",
        "-frames:v",
        str(args.frames),
        "-an",
        "-sn",
        "-f",
        "null",
        "-",
    ]
    rc1, _, err1 = _run(idet_cmd, args.dry_run, capture=True)
    if rc1 != 0 and not args.dry_run:
        sys.stderr.write(err1)
        return rc1

    vfrdet_cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-filter:v",
        "vfrdet",
        "-an",
        "-sn",
        "-f",
        "null",
        "-",
    ]
    rc2, _, err2 = _run(vfrdet_cmd, args.dry_run, capture=True)
    if rc2 != 0 and not args.dry_run:
        sys.stderr.write(err2)
        return rc2

    if args.dry_run:
        return 0

    idet = _parse_idet(err1)
    vfrdet = _parse_vfrdet(err2)

    print("\n=== idet ===")
    for bucket in ("single", "multiple"):
        d = idet.get(bucket, {})
        if not d:
            continue
        t = d["total"]
        print(
            f"  {bucket:>8} frames: TFF {_pct(d['tff'], t)}  BFF {_pct(d['bff'], t)}  "
            f"Progressive {_pct(d['progressive'], t)}  Undetermined {_pct(d['undetermined'], t)}  (n={t})"
        )
    r = idet.get("repeated", {})
    if r:
        t = r["total"]
        print(
            f"  repeated fields: Neither {_pct(r['neither'], t)}  Top {_pct(r['top'], t)}  "
            f"Bottom {_pct(r['bottom'], t)}  (n={t})"
        )

    print("\n=== vfrdet ===")
    if vfrdet:
        print("  " + vfrdet.get("raw", ""))
    else:
        print("  (no vfrdet output — filter may require --frames to be unbounded)")

    # Heuristic classification
    multi = idet.get("multiple", {})
    rep = idet.get("repeated", {})
    print("\n=== suggestion ===")
    if multi and rep:
        mt = multi["total"] or 1
        prog_pct = 100 * multi["progressive"] / mt
        inter_pct = 100 * (multi["tff"] + multi["bff"]) / mt
        rep_total = rep["total"] or 1
        rep_pct = 100 * (rep["top"] + rep["bottom"]) / rep_total
        if prog_pct >= 95 and rep_pct < 5:
            print("  -> progressive. No IVTC / deinterlace needed.")
        elif inter_pct >= 40 and rep_pct >= 20:
            print("  -> hard-telecined (3:2 pulldown). Use IVTC:")
            print("     ivtc --method fieldmatch  (canonical)")
        elif inter_pct >= 80 and rep_pct < 5:
            print("  -> true interlaced. Use deinterlace:")
            print("     deinterlace --filter bwdif [--double-rate]")
        elif prog_pct >= 80 and rep_pct >= 20:
            print(
                "  -> soft-telecined (flagged). Use `-vf repeatfields` or let the decoder handle RFF."
            )
        else:
            print("  -> mixed / ambiguous. Try:")
            print("     dejudder --cycle 4 THEN ivtc --method fieldmatch")
    return 0


# -------- ivtc --------


def cmd_ivtc(args: argparse.Namespace) -> int:
    if args.method == "fieldmatch":
        vf = (
            f"fieldmatch=order={args.order}:combmatch={args.combmatch},"
            "yadif=deint=interlaced,"
            "decimate"
        )
    elif args.method == "pullup":
        vf = "pullup,fps=24000/1001"
    else:
        raise SystemExit(f"unknown method: {args.method}")

    common = _common_flags(args.verbose)
    cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-vf",
        vf,
        "-r",
        "24000/1001",
        "-vsync",
        "cfr",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-y",
        args.output,
    ]
    rc, _, _ = _run(cmd, args.dry_run)
    return rc


# -------- deinterlace --------


def cmd_deinterlace(args: argparse.Namespace) -> int:
    mode_token = "send_field" if args.double_rate else "send_frame"
    f = args.filter_
    if f == "bwdif":
        vf = f"bwdif=mode={mode_token}:parity=auto:deint=all"
    elif f == "yadif":
        # yadif uses numeric mode: 0 send_frame, 1 send_field
        vf = f"yadif=mode={'1' if args.double_rate else '0'}:parity=-1:deint=0"
    elif f == "w3fdif":
        vf = f"w3fdif=filter=complex:mode={'field' if args.double_rate else 'frame'}:parity=auto:deint=all"
    elif f == "estdif":
        vf = f"estdif=mode={'field' if args.double_rate else 'frame'}:parity=auto:deint=all"
    elif f == "kerndeint":
        # kerndeint has no double-rate mode; always single-frame
        if args.double_rate:
            print(
                "note: kerndeint has no double-rate mode; producing single-rate output.",
                file=sys.stderr,
            )
        vf = "kerndeint=thresh=10:map=0:order=0:sharp=0:twoway=0"
    elif f == "mcdeint":
        # mcdeint needs 1-field-per-frame input -> chain yadif=1,mcdeint
        vf = "yadif=mode=1:parity=-1:deint=0,mcdeint=mode=fast:parity=bff:qp=1"
    else:
        raise SystemExit(f"unknown filter: {f}")

    common = _common_flags(args.verbose)
    cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-y",
        args.output,
    ]
    rc, _, _ = _run(cmd, args.dry_run)
    return rc


# -------- decimate --------


def cmd_decimate(args: argparse.Namespace) -> int:
    # mpdecimate + PTS reset. cycle/drop map to decimate filter too, but mpdecimate
    # uses hi/lo/frac thresholds. Expose both.
    if args.style == "mpdecimate":
        vf = (
            f"mpdecimate=hi={args.hi}:lo={args.lo}:frac={args.frac},"
            "setpts=N/FRAME_RATE/TB"
        )
    else:
        vf = f"decimate=cycle={args.cycle},setpts=N/FRAME_RATE/TB"

    common = _common_flags(args.verbose)
    cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-vf",
        vf,
        "-vsync",
        "cfr",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
        "-y",
        args.output,
    ]
    if args.target_fps:
        # insert -r before output
        cmd = cmd[:-3] + ["-r", args.target_fps] + cmd[-3:]
    rc, _, _ = _run(cmd, args.dry_run)
    return rc


# -------- dejudder --------


def cmd_dejudder(args: argparse.Namespace) -> int:
    vf = f"dejudder=cycle={args.cycle}"
    common = _common_flags(args.verbose)
    cmd = [
        FFMPEG,
        *common,
        "-i",
        args.input,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
        "-y",
        args.output,
    ]
    rc, _, _ = _run(cmd, args.dry_run)
    return rc


# -------- parser --------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ivtc.py",
        description="inverse telecine / deinterlace / decimate / dejudder via ffmpeg",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the ffmpeg command without running it",
    )
    p.add_argument(
        "--verbose", action="store_true", help="ffmpeg -v info instead of -v error"
    )
    sub = p.add_subparsers(dest="sub", required=True)

    d = sub.add_parser("detect", help="run idet + vfrdet and report statistics")
    d.add_argument("--input", "-i", required=True)
    d.add_argument(
        "--frames", type=int, default=500, help="frames to analyze (default 500)"
    )
    d.set_defaults(func=cmd_detect)

    i = sub.add_parser("ivtc", help="inverse telecine to 23.976p")
    i.add_argument("--input", "-i", required=True)
    i.add_argument("--output", "-o", required=True)
    i.add_argument("--method", choices=["fieldmatch", "pullup"], default="fieldmatch")
    i.add_argument("--order", choices=["auto", "tff", "bff"], default="auto")
    i.add_argument("--combmatch", choices=["none", "sc", "full"], default="full")
    i.add_argument("--crf", type=int, default=18)
    i.add_argument("--preset", default="slower")
    i.set_defaults(func=cmd_ivtc)

    de = sub.add_parser("deinterlace", help="true interlaced -> progressive")
    de.add_argument("--input", "-i", required=True)
    de.add_argument("--output", "-o", required=True)
    de.add_argument(
        "--filter",
        dest="filter_",
        choices=["bwdif", "yadif", "w3fdif", "estdif", "kerndeint", "mcdeint"],
        default="bwdif",
    )
    de.add_argument(
        "--double-rate", action="store_true", help="bob-deinterlace to 2x fps"
    )
    de.add_argument("--crf", type=int, default=18)
    de.add_argument("--preset", default="medium")
    de.set_defaults(func=cmd_deinterlace)

    dc = sub.add_parser("decimate", help="drop duplicate frames")
    dc.add_argument("--input", "-i", required=True)
    dc.add_argument("--output", "-o", required=True)
    dc.add_argument("--style", choices=["mpdecimate", "decimate"], default="mpdecimate")
    dc.add_argument(
        "--cycle", type=int, default=5, help="decimate cycle (default 5 for 30->24)"
    )
    dc.add_argument("--hi", type=int, default=64 * 12, help="mpdecimate hi threshold")
    dc.add_argument("--lo", type=int, default=64 * 5, help="mpdecimate lo threshold")
    dc.add_argument("--frac", type=float, default=0.33, help="mpdecimate frac")
    dc.add_argument("--target-fps", default="", help="force output -r, e.g. 24000/1001")
    dc.add_argument("--crf", type=int, default=18)
    dc.add_argument("--preset", default="medium")
    dc.set_defaults(func=cmd_decimate)

    dj = sub.add_parser("dejudder", help="remove telecine judder")
    dj.add_argument("--input", "-i", required=True)
    dj.add_argument("--output", "-o", required=True)
    dj.add_argument(
        "--cycle", type=int, default=4, help="4 film-to-NTSC, 5 PAL-to-NTSC, 20 mixed"
    )
    dj.add_argument("--crf", type=int, default=18)
    dj.add_argument("--preset", default="medium")
    dj.set_defaults(func=cmd_dejudder)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
