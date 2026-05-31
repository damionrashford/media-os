#!/usr/bin/env python3
"""afx.py — ffmpeg creative / restoration audio effects front-end.

Stdlib only. Non-interactive. Prints the ffmpeg command and runs it (unless
--dry-run). Each subcommand maps to one of the recipes in SKILL.md.

Groups:
    modulation  : echo, chorus, flanger, phaser, tremolo, vibrato
    dynamics    : speechnorm, dialogue-enhance, limit (soft / psy)
    restoration : deckick (adeclick + adeclip chain)
    filter      : band (pass / reject / high / low)
    plugin      : ladspa, lv2

Usage:
    afx.py echo --input in.wav --output out.wav --delay-ms 600 --decay 0.4
    afx.py chorus --input in.wav --output out.wav
    afx.py speechnorm --input in.wav --output out.wav
    afx.py deckick --input vinyl.wav --output clean.wav
    afx.py limit --input master.wav --output final.wav --method psy
    afx.py ladspa --input in.wav --output out.wav --file cmt --plugin amp_stereo --params gain=10
    afx.py band --input in.wav --output out.wav --mode pass --freq-hz 1000 --q 2
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import List


def run(cmd: List[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(printable)
    if verbose:
        print(f"# argv = {cmd!r}", file=sys.stderr)
    if dry_run:
        return 0
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print("ERROR: ffmpeg not found on PATH", file=sys.stderr)
        return 127


def ffmpeg(
    input_: str, af: str, output: str, *, extra_out: List[str] | None = None
) -> List[str]:
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", input_, "-af", af]
    if extra_out:
        cmd.extend(extra_out)
    cmd.append(output)
    return cmd


def parse_kv_list(s: str | None) -> str:
    """Turn 'key=val,key2=val2' into '|'-joined LADSPA/LV2 control string."""
    if not s:
        return ""
    pairs = [p.strip() for p in s.split(",") if p.strip()]
    return "|".join(pairs)


# --- subcommand handlers --------------------------------------------------


def cmd_echo(a: argparse.Namespace) -> int:
    af = f"aecho=0.8:0.9:{int(a.delay_ms)}:{a.decay}"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_chorus(a: argparse.Namespace) -> int:
    af = "chorus=0.7:0.9:55:0.4:0.25:2"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_flanger(a: argparse.Namespace) -> int:
    af = f"flanger=delay=5:depth={a.depth}:speed={a.speed}"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_phaser(a: argparse.Namespace) -> int:
    af = f"aphaser=type={a.type}:speed={a.speed}"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_tremolo(a: argparse.Namespace) -> int:
    af = f"tremolo=f={a.hz}:d={a.depth}"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_vibrato(a: argparse.Namespace) -> int:
    af = f"vibrato=f={a.hz}:d={a.depth}"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_speechnorm(a: argparse.Namespace) -> int:
    af = "speechnorm=e=12.5:r=0.0001:l=1"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_dialogue_enhance(a: argparse.Namespace) -> int:
    af = "dialoguenhance"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_deckick(a: argparse.Namespace) -> int:
    # adeclick -> adeclip -> 30 Hz rumble supercut
    af = (
        "adeclick=window=55:overlap=75:arorder=8:threshold=2:burst=2,"
        "adeclip=window=55:overlap=75:arorder=8:threshold=10:hsize=1000:method=a,"
        "asupercut=cutoff=30:order=12"
    )
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_limit(a: argparse.Namespace) -> int:
    if a.method == "soft":
        af = "asoftclip=type=tanh"
    else:
        af = "apsyclip=level_in=1:level_out=1:clip=0.9"
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_ladspa(a: argparse.Namespace) -> int:
    parts = [f"ladspa=file={a.file}", f"plugin={a.plugin}"]
    ctrl = parse_kv_list(a.params)
    if ctrl:
        parts.append(f"c={ctrl}")
    af = ":".join(parts)
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_lv2(a: argparse.Namespace) -> int:
    parts = [f"lv2=p={a.plugin}"]
    ctrl = parse_kv_list(a.params)
    if ctrl:
        parts.append(f"c={ctrl}")
    af = ":".join(parts)
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


def cmd_band(a: argparse.Namespace) -> int:
    if a.mode == "pass":
        af = f"bandpass=f={a.freq_hz}:width_type=q:w={a.q}"
    elif a.mode == "reject":
        af = f"bandreject=f={a.freq_hz}:width_type=q:w={a.q}"
    elif a.mode == "high":
        af = f"highpass=f={a.freq_hz}"
    elif a.mode == "low":
        af = f"lowpass=f={a.freq_hz}"
    else:
        print(f"ERROR: unknown --mode {a.mode}", file=sys.stderr)
        return 2
    return run(ffmpeg(a.input, af, a.output), dry_run=a.dry_run, verbose=a.verbose)


# --- argument parser ------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="afx.py",
        description="ffmpeg creative & restoration audio effects (-af) front-end",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print the command but do not execute."
    )
    p.add_argument("--verbose", action="store_true", help="Echo parsed argv to stderr.")
    sub = p.add_subparsers(dest="command", required=True)

    def add_io(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--input", "-i", required=True, help="Input media file.")
        sp.add_argument("--output", "-o", required=True, help="Output media file.")

    sp = sub.add_parser("echo", help="aecho")
    add_io(sp)
    sp.add_argument("--delay-ms", type=int, default=1000)
    sp.add_argument("--decay", type=float, default=0.3)
    sp.set_defaults(func=cmd_echo)

    sp = sub.add_parser("chorus", help="chorus (fixed musical preset)")
    add_io(sp)
    sp.set_defaults(func=cmd_chorus)

    sp = sub.add_parser("flanger", help="flanger")
    add_io(sp)
    sp.add_argument("--speed", type=float, default=0.5, help="LFO Hz")
    sp.add_argument("--depth", type=float, default=2.0, help="LFO depth in ms")
    sp.set_defaults(func=cmd_flanger)

    sp = sub.add_parser("phaser", help="aphaser")
    add_io(sp)
    sp.add_argument(
        "--type", default="t", choices=["t", "s", "n"], help="triangle / sine / noise"
    )
    sp.add_argument("--speed", type=float, default=2.0)
    sp.set_defaults(func=cmd_phaser)

    sp = sub.add_parser("tremolo", help="tremolo (volume modulation)")
    add_io(sp)
    sp.add_argument("--hz", type=float, default=5.0)
    sp.add_argument("--depth", type=float, default=0.5)
    sp.set_defaults(func=cmd_tremolo)

    sp = sub.add_parser("vibrato", help="vibrato (pitch modulation)")
    add_io(sp)
    sp.add_argument("--hz", type=float, default=7.0)
    sp.add_argument("--depth", type=float, default=0.5)
    sp.set_defaults(func=cmd_vibrato)

    sp = sub.add_parser("speechnorm", help="speechnorm: intelligent speech leveler")
    add_io(sp)
    sp.set_defaults(func=cmd_speechnorm)

    sp = sub.add_parser("dialogue-enhance", help="dialoguenhance (5.1+ recommended)")
    add_io(sp)
    sp.set_defaults(func=cmd_dialogue_enhance)

    sp = sub.add_parser("deckick", help="de-click + de-clip + 30 Hz rumble kill")
    add_io(sp)
    sp.set_defaults(func=cmd_deckick)

    sp = sub.add_parser("limit", help="asoftclip (soft) or apsyclip (psy, broadcast)")
    add_io(sp)
    sp.add_argument("--method", default="psy", choices=["soft", "psy"])
    sp.set_defaults(func=cmd_limit)

    sp = sub.add_parser("ladspa", help="Host a LADSPA plugin")
    add_io(sp)
    sp.add_argument("--file", required=True, help="LADSPA library name (no .so)")
    sp.add_argument("--plugin", required=True, help="LADSPA plugin label")
    sp.add_argument("--params", default="", help="Comma-separated key=val controls")
    sp.set_defaults(func=cmd_ladspa)

    sp = sub.add_parser("lv2", help="Host an LV2 plugin")
    add_io(sp)
    sp.add_argument("--plugin", required=True, help="LV2 plugin URI")
    sp.add_argument("--params", default="", help="Comma-separated key=val controls")
    sp.set_defaults(func=cmd_lv2)

    sp = sub.add_parser("band", help="bandpass / bandreject / highpass / lowpass")
    add_io(sp)
    sp.add_argument("--mode", required=True, choices=["pass", "reject", "high", "low"])
    sp.add_argument("--freq-hz", type=float, required=True)
    sp.add_argument("--q", type=float, default=2.0, help="Q factor (pass/reject only)")
    sp.set_defaults(func=cmd_band)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
