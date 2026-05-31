#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
SoX wrapper: non-interactive subcommands that shell out to `sox`.

Stdlib-only. Supports --dry-run (print command, do not execute) and --verbose
(echo the command to stderr before running).

Subcommands:
    check                 Show sox version + compiled-in audio file formats.
    info                  `sox --i INPUT` — header / format info.
    convert               Format / rate / bits / channels conversion.
    trim                  Extract a time slice.
    tempo                 Change speed, preserve pitch.
    pitch                 Change pitch (cents), preserve tempo.
    fade                  Apply fade-in / fade-out.
    silence-trim          Strip leading and internal silences.
    denoise               Two-pass noiseprof + noisered.
    normalize             Peak normalize via --norm (optionally to a target dBFS).
    synth                 Generate sine / pinknoise / whitenoise / brownnoise.
    concat                Concatenate inputs (must share rate/channels).
    mix                   Sum inputs with `-m`.
    stats                 `sox INPUT -n stats` — peak, RMS, DC offset, etc.

Examples:
    uv run scripts/sox.py check
    uv run scripts/sox.py info --input in.wav
    uv run scripts/sox.py convert --input in.wav --output out.flac --rate 48000 --bits 16
    uv run scripts/sox.py trim --input in.wav --output clip.wav --start 10 --duration 20
    uv run scripts/sox.py denoise --input in.wav --output clean.wav --noise-sample "0 1"
    uv run scripts/sox.py synth --output tone.wav --duration 3 --kind sine --freq 440
    uv run scripts/sox.py stats --input in.wav
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def require_sox() -> str:
    path = shutil.which("sox")
    if not path:
        die(
            "sox not found on PATH. Install with: brew install sox  (or apt-get install sox)"
        )
    return path


def run(cmd: list[str], *, verbose: bool, dry_run: bool) -> int:
    if verbose or dry_run:
        shown = " ".join(shlex_quote(c) for c in cmd)
        tag = "[dry-run] " if dry_run else "+ "
        print(f"{tag}{shown}", file=sys.stderr)
    if dry_run:
        return 0
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        die(str(e))
    return proc.returncode


def shlex_quote(s: str) -> str:
    # stdlib shlex.quote but inline to keep single-file clarity
    import shlex

    return shlex.quote(s)


def ensure_input(path: str) -> None:
    if not Path(path).exists():
        die(f"input not found: {path}")


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    sox = require_sox()
    rc = run([sox, "--version"], verbose=args.verbose, dry_run=args.dry_run)
    if rc != 0 and not args.dry_run:
        return rc
    # sox -h prints formats block to stdout; grep-free approach via python
    if args.dry_run:
        print(f"[dry-run] + {sox} -h", file=sys.stderr)
        return 0
    try:
        out = subprocess.run([sox, "-h"], capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        die(str(e))
    text = (out.stdout or "") + (out.stderr or "")
    for line in text.splitlines():
        if "AUDIO FILE FORMATS" in line or "AUDIO DEVICE DRIVERS" in line:
            print(line)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    return run([sox, "--i", args.input], verbose=args.verbose, dry_run=args.dry_run)


def cmd_convert(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [sox, args.input]
    # output file options go before the output filename
    out_opts: list[str] = []
    if args.rate is not None:
        out_opts += ["-r", str(args.rate)]
    if args.bits is not None:
        out_opts += ["-b", str(args.bits)]
    if args.channels is not None:
        out_opts += ["-c", str(args.channels)]
    cmd += out_opts + [args.output]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_trim(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [sox, args.input, args.output, "trim", str(args.start)]
    if args.duration is not None:
        cmd.append(str(args.duration))
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_tempo(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [sox, args.input, args.output, "tempo", str(args.factor)]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_pitch(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [sox, args.input, args.output, "pitch", str(args.cents)]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_fade(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    # fade <in-length> <stop-position> <out-length>
    # stop-position "-0" means "do not truncate; out-length measured from end"
    cmd = [
        sox,
        args.input,
        args.output,
        "fade",
        str(getattr(args, "in_", args.__dict__.get("in", 1))),
        "-0",
        str(args.out),
    ]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_silence_trim(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [
        sox,
        args.input,
        args.output,
        "silence",
        "1",
        "0.1",
        args.threshold,
        "-1",
        str(args.min_duration),
        args.threshold,
    ]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_denoise(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    parts = args.noise_sample.split()
    if len(parts) != 2:
        die('--noise-sample expects "START DURATION" (two space-separated numbers)')
    start, dur = parts
    profile_path = Path(tempfile.gettempdir()) / f"sox_noise_{os.getpid()}.prof"
    # pass 1: build profile
    cmd_prof = [
        sox,
        args.input,
        "-n",
        "trim",
        start,
        dur,
        "noiseprof",
        str(profile_path),
    ]
    rc = run(cmd_prof, verbose=args.verbose, dry_run=args.dry_run)
    if rc != 0 and not args.dry_run:
        return rc
    # pass 2: reduce
    cmd_red = [
        sox,
        args.input,
        args.output,
        "noisered",
        str(profile_path),
        str(args.sensitivity),
    ]
    rc = run(cmd_red, verbose=args.verbose, dry_run=args.dry_run)
    if not args.dry_run:
        try:
            profile_path.unlink(missing_ok=True)
        except Exception:
            pass
    return rc


def cmd_normalize(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    # --norm[=dB] — peak normalize; optional target dBFS (0 by default)
    norm = "--norm" if args.target == 0 else f"--norm={args.target}"
    cmd = [sox, norm, args.input, args.output]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_synth(args: argparse.Namespace) -> int:
    sox = require_sox()
    kind = args.kind
    cmd = [sox, "-n", args.output, "synth", str(args.duration), kind]
    # frequency only meaningful for tonal waveforms
    if kind in {"sine", "square", "triangle", "sawtooth", "trapezium"}:
        cmd.append(str(args.freq))
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_concat(args: argparse.Namespace) -> int:
    sox = require_sox()
    for f in args.inputs:
        ensure_input(f)
    cmd = [sox, *args.inputs, args.output]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_mix(args: argparse.Namespace) -> int:
    sox = require_sox()
    for f in args.inputs:
        ensure_input(f)
    cmd = [sox, "-m", *args.inputs, args.output]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


def cmd_stats(args: argparse.Namespace) -> int:
    sox = require_sox()
    ensure_input(args.input)
    cmd = [sox, args.input, "-n", "stats"]
    return run(cmd, verbose=args.verbose, dry_run=args.dry_run)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sox.py",
        description="Non-interactive SoX wrapper for common audio operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print command without executing"
    )
    p.add_argument(
        "--verbose", action="store_true", help="Echo command to stderr before running"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Show sox version + compiled formats").set_defaults(
        func=cmd_check
    )

    s = sub.add_parser("info", help="sox --i on an input")
    s.add_argument("--input", required=True)
    s.set_defaults(func=cmd_info)

    s = sub.add_parser("convert", help="Rate / bits / channels conversion")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--rate", type=int, default=None, help="Output sample rate in Hz (e.g. 48000)"
    )
    s.add_argument(
        "--bits", type=int, default=None, help="Output bit depth (8/16/24/32)"
    )
    s.add_argument(
        "--channels", type=int, default=None, help="Output channel count (1/2/6)"
    )
    s.set_defaults(func=cmd_convert)

    s = sub.add_parser("trim", help="Extract a time slice")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--start", required=True, help="Start time (seconds or hh:mm:ss)")
    s.add_argument(
        "--duration", default=None, help="Duration (optional; omit for until EOF)"
    )
    s.set_defaults(func=cmd_trim)

    s = sub.add_parser("tempo", help="Change tempo, preserve pitch")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--factor", type=float, required=True, help="Tempo factor (1.5 = 50%% faster)"
    )
    s.set_defaults(func=cmd_tempo)

    s = sub.add_parser("pitch", help="Change pitch (cents), preserve tempo")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--cents",
        type=int,
        required=True,
        help="Pitch shift in cents (200 = +2 semitones)",
    )
    s.set_defaults(func=cmd_pitch)

    s = sub.add_parser("fade", help="Fade-in / fade-out")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--in", dest="in_", type=float, default=1.0, help="Fade-in seconds")
    s.add_argument("--out", type=float, default=1.0, help="Fade-out seconds")
    s.set_defaults(func=cmd_fade)

    s = sub.add_parser("silence-trim", help="Strip leading and internal silences")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--threshold", default="1%", help="Amplitude threshold (e.g. 1%%, -40d)"
    )
    s.add_argument(
        "--min-duration", type=float, default=0.5, help="Minimum silence seconds"
    )
    s.set_defaults(func=cmd_silence_trim)

    s = sub.add_parser("denoise", help="Two-pass noiseprof + noisered")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--noise-sample",
        required=True,
        help='"START DURATION" in seconds pointing at pure-noise region (e.g. "0 1")',
    )
    s.add_argument(
        "--sensitivity", type=float, default=0.21, help="noisered sensitivity 0.0-1.0"
    )
    s.set_defaults(func=cmd_denoise)

    s = sub.add_parser("normalize", help="Peak normalize via --norm")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument(
        "--target", type=float, default=0.0, help="Target peak dBFS (default 0)"
    )
    s.set_defaults(func=cmd_normalize)

    s = sub.add_parser("synth", help="Generate synthetic waveform")
    s.add_argument("--output", required=True)
    s.add_argument("--duration", type=float, required=True, help="Seconds")
    s.add_argument(
        "--kind",
        choices=[
            "sine",
            "square",
            "triangle",
            "sawtooth",
            "trapezium",
            "pinknoise",
            "whitenoise",
            "brownnoise",
        ],
        default="sine",
    )
    s.add_argument(
        "--freq",
        type=float,
        default=440.0,
        help="Frequency in Hz (tonal waveforms only)",
    )
    s.set_defaults(func=cmd_synth)

    s = sub.add_parser("concat", help="Concatenate inputs")
    s.add_argument("--inputs", nargs="+", required=True)
    s.add_argument("--output", required=True)
    s.set_defaults(func=cmd_concat)

    s = sub.add_parser("mix", help="Sum inputs with -m")
    s.add_argument("--inputs", nargs="+", required=True)
    s.add_argument("--output", required=True)
    s.set_defaults(func=cmd_mix)

    s = sub.add_parser("stats", help="Peak / RMS / DC offset / crest factor")
    s.add_argument("--input", required=True)
    s.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
