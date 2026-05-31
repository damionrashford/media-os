#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
afilter.py — ffmpeg audio-filter presets with 2-pass loudnorm support.

Presets (subcommands):
    loudnorm-yt        I=-14  LRA=11  TP=-1.5   (YouTube, Spotify)
    loudnorm-podcast   I=-16  LRA=11  TP=-1.5   (Apple Podcasts)
    loudnorm-ebu       I=-23  LRA=7   TP=-2.0   (EBU R128 broadcast)
    normalize-peak     peak-normalize via volumedetect (dB gain)
    mix-two            amix two inputs with SR+layout guards
    speed              atempo (auto-chains if factor outside 0.5..2.0)
    mono-downmix       pan stereo|5.1 -> mono
    denoise-simple     highpass=80,lowpass=16000,afftdn

Flags:
    --input FILE          primary input file for most presets
    --inputs A B          two inputs for mix-two
    --output FILE         output file (required for non dry-run)
    --two-pass            for loudnorm-* presets: measure then apply
    --factor FLOAT        for speed preset
    --dry-run             print ffmpeg command, do not run
    --verbose             echo each ffmpeg invocation to stderr

Examples:
    uv run afilter.py loudnorm-yt --input in.wav --output out.wav --two-pass
    uv run afilter.py mix-two --inputs voice.wav music.wav --output mix.wav
    uv run afilter.py speed --input in.wav --output fast.wav --factor 2.5
    uv run afilter.py mono-downmix --input stereo.wav --output mono.wav
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

LOUDNORM_TARGETS = {
    "loudnorm-yt": {"I": -14, "LRA": 11, "TP": -1.5},
    "loudnorm-podcast": {"I": -16, "LRA": 11, "TP": -1.5},
    "loudnorm-ebu": {"I": -23, "LRA": 7, "TP": -2.0},
}


def vprint(verbose: bool, *args) -> None:
    if verbose:
        print(*args, file=sys.stderr)


def run(
    cmd: list[str], dry_run: bool, verbose: bool, capture_stderr: bool = False
) -> str:
    vprint(verbose, "+", " ".join(shlex.quote(c) for c in cmd))
    if dry_run:
        return ""
    result = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE if capture_stderr else None,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        sys.exit(result.returncode)
    return result.stderr or ""


def parse_loudnorm_json(stderr_text: str) -> dict:
    """Extract the final {...} JSON block that loudnorm prints to stderr."""
    # Find the last {...} block.
    matches = list(re.finditer(r"\{[^{}]*\}", stderr_text, flags=re.DOTALL))
    if not matches:
        raise RuntimeError("loudnorm pass-1 produced no JSON block")
    for m in reversed(matches):
        try:
            data = json.loads(m.group(0))
            if "input_i" in data:
                return data
        except json.JSONDecodeError:
            continue
    raise RuntimeError("could not parse loudnorm JSON")


def loudnorm_filter(target: dict, measured: dict | None = None) -> str:
    parts = [f"I={target['I']}", f"LRA={target['LRA']}", f"TP={target['TP']}"]
    if measured is not None:
        parts += [
            f"measured_I={measured['input_i']}",
            f"measured_LRA={measured['input_lra']}",
            f"measured_TP={measured['input_tp']}",
            f"measured_thresh={measured['input_thresh']}",
            f"offset={measured['target_offset']}",
            "linear=true",
            "print_format=summary",
        ]
    else:
        parts.append("print_format=json")
    return "loudnorm=" + ":".join(parts)


def cmd_loudnorm(args, preset_name: str) -> None:
    target = LOUDNORM_TARGETS[preset_name]
    require(args.input, "--input")
    if args.two_pass:
        # Pass 1 — measure
        f1 = loudnorm_filter(target)
        pass1 = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            args.input,
            "-af",
            f1,
            "-f",
            "null",
            "-",
        ]
        stderr = run(pass1, args.dry_run, args.verbose, capture_stderr=True)
        if args.dry_run:
            # still need a plausible pass-2 preview
            placeholder = {
                "input_i": "-23.0",
                "input_lra": "7.0",
                "input_tp": "-2.0",
                "input_thresh": "-33.0",
                "target_offset": "0.0",
            }
            f2 = loudnorm_filter(target, placeholder)
        else:
            measured = parse_loudnorm_json(stderr)
            f2 = loudnorm_filter(target, measured)
        require(args.output, "--output")
        pass2 = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            args.input,
            "-af",
            f2,
            "-ar",
            "48000",
            args.output,
        ]
        run(pass2, args.dry_run, args.verbose)
    else:
        # Single-pass dynamic
        require(args.output, "--output")
        f = loudnorm_filter(target)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            args.input,
            "-af",
            f,
            "-ar",
            "48000",
            args.output,
        ]
        run(cmd, args.dry_run, args.verbose)


def cmd_normalize_peak(args) -> None:
    require(args.input, "--input")
    require(args.output, "--output")
    probe = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        args.input,
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    stderr = run(probe, args.dry_run, args.verbose, capture_stderr=True)
    if args.dry_run:
        gain_db = 0.0
    else:
        m = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", stderr)
        if not m:
            raise RuntimeError("volumedetect did not report max_volume")
        max_vol = float(m.group(1))
        gain_db = -max_vol  # bring peak to 0 dBFS
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        args.input,
        "-af",
        f"volume={gain_db}dB",
        args.output,
    ]
    run(cmd, args.dry_run, args.verbose)


def cmd_mix_two(args) -> None:
    if not args.inputs or len(args.inputs) != 2:
        die("mix-two needs --inputs A B (exactly two files)")
    require(args.output, "--output")
    a, b = args.inputs
    fc = (
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
        "[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
        "[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        a,
        "-i",
        b,
        "-filter_complex",
        fc,
        "-map",
        "[aout]",
        "-ar",
        "48000",
        args.output,
    ]
    run(cmd, args.dry_run, args.verbose)


def chain_atempo(factor: float) -> str:
    """Return an atempo chain covering the requested factor.

    Single-instance range enforced conservatively at [0.5, 2.0] for
    compatibility with older ffmpeg builds.
    """
    if factor <= 0:
        die("speed factor must be > 0")
    parts: list[str] = []
    remaining = factor
    if remaining >= 1.0:
        while remaining > 2.0:
            parts.append("atempo=2.0")
            remaining /= 2.0
        parts.append(f"atempo={remaining:.6f}")
    else:
        while remaining < 0.5:
            parts.append("atempo=0.5")
            remaining /= 0.5
        parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def cmd_speed(args) -> None:
    require(args.input, "--input")
    require(args.output, "--output")
    if args.factor is None:
        die("speed needs --factor FLOAT")
    af = chain_atempo(args.factor)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        args.input,
        "-af",
        af,
        args.output,
    ]
    run(cmd, args.dry_run, args.verbose)


def cmd_mono_downmix(args) -> None:
    require(args.input, "--input")
    require(args.output, "--output")
    # Works for stereo; ffmpeg pan expands channel names for 5.1 inputs too.
    af = "pan=mono|c0=0.5*c0+0.5*c1"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        args.input,
        "-af",
        af,
        "-ac",
        "1",
        args.output,
    ]
    run(cmd, args.dry_run, args.verbose)


def cmd_denoise_simple(args) -> None:
    require(args.input, "--input")
    require(args.output, "--output")
    af = "highpass=f=80,lowpass=f=16000,afftdn=nr=12:nf=-25"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        args.input,
        "-af",
        af,
        args.output,
    ]
    run(cmd, args.dry_run, args.verbose)


def require(value, flag: str) -> None:
    if not value:
        die(f"missing required flag: {flag}")


def die(msg: str) -> None:
    print(f"afilter.py: {msg}", file=sys.stderr)
    sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ffmpeg audio-filter presets (loudnorm, mix, speed, …)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="preset", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--input")
        sp.add_argument("--inputs", nargs="+")
        sp.add_argument("--output")
        sp.add_argument("--two-pass", action="store_true")
        sp.add_argument("--factor", type=float)
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--verbose", action="store_true")

    for name in (
        "loudnorm-yt",
        "loudnorm-podcast",
        "loudnorm-ebu",
        "normalize-peak",
        "mix-two",
        "speed",
        "mono-downmix",
        "denoise-simple",
    ):
        add_common(sub.add_parser(name))
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not Path(args.input).exists() if args.input else False:
        die(f"input not found: {args.input}")
    if args.inputs:
        for f in args.inputs:
            if not Path(f).exists():
                die(f"input not found: {f}")

    dispatch = {
        "loudnorm-yt": lambda: cmd_loudnorm(args, "loudnorm-yt"),
        "loudnorm-podcast": lambda: cmd_loudnorm(args, "loudnorm-podcast"),
        "loudnorm-ebu": lambda: cmd_loudnorm(args, "loudnorm-ebu"),
        "normalize-peak": lambda: cmd_normalize_peak(args),
        "mix-two": lambda: cmd_mix_two(args),
        "speed": lambda: cmd_speed(args),
        "mono-downmix": lambda: cmd_mono_downmix(args),
        "denoise-simple": lambda: cmd_denoise_simple(args),
    }
    dispatch[args.preset]()


if __name__ == "__main__":
    main()
