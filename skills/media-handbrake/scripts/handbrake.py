#!/usr/bin/env python3
"""HandBrakeCLI helper: presets, custom encodes, Apple devices, batch, inspect.

Stdlib only. Non-interactive. Safe to run unattended.

Subcommands:
  check          HandBrakeCLI version.
  list-presets   Print categorized preset names.
  encode         Run a built-in preset (-Z "Name").
  custom         Custom encoder/quality/tune.
  apple          Shortcut for Apple device presets.
  batch          Encode a directory recursively.
  inspect        Scan source and print (optionally JSON) info.

All subcommands accept --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HANDBRAKE = os.environ.get("HANDBRAKE_CLI", "HandBrakeCLI")

APPLE_PRESETS = {
    "iphone": "iPhone and iPod touch",
    "ipad": "iPad",
    "appletv": "Apple 1080p60 Surround",
    "4k": "Apple 2160p60 4K HEVC Surround",
}

# Accepted values for --encoder on the `custom` subcommand. HandBrake's actual
# enumeration is longer; this is the curated common subset.
ENCODERS = [
    "x264",
    "x264_10bit",
    "x265",
    "x265_10bit",
    "x265_12bit",
    "svt_av1",
    "svt_av1_10bit",
    "vp9",
    "vp9_10bit",
    "mpeg4",
    "mpeg2",
    "theora",
    "vt_h264",
    "vt_h265",
    "vt_h265_10bit",
    "nvenc_h264",
    "nvenc_h265",
    "nvenc_h265_10bit",
    "nvenc_av1",
    "qsv_h264",
    "qsv_h265",
    "qsv_h265_10bit",
    "qsv_av1",
    "vce_h264",
    "vce_h265",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _die(msg: str, code: int = 2) -> None:
    print(f"handbrake.py: {msg}", file=sys.stderr)
    sys.exit(code)


def _ensure_tool() -> None:
    if shutil.which(HANDBRAKE) is None:
        _die(
            f"{HANDBRAKE} not found on PATH. Install with:\n"
            f"  macOS:  brew install handbrake\n"
            f"  Linux:  sudo apt install handbrake-cli\n"
            f"  Or:     https://handbrake.fr/downloads2.php",
            127,
        )


def _run(
    cmd: list[str], *, dry_run: bool, verbose: bool, capture: bool = False
) -> subprocess.CompletedProcess | None:
    if dry_run or verbose:
        print("+ " + " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    if dry_run:
        return None
    if capture:
        return subprocess.run(
            cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    return subprocess.run(cmd, check=False)


def _require_file(path: Path, label: str = "input") -> None:
    if not path.exists():
        _die(f"{label} does not exist: {path}")


def _ensure_outdir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    _ensure_tool()
    cp = _run(
        [HANDBRAKE, "--version"],
        dry_run=args.dry_run,
        verbose=args.verbose,
        capture=True,
    )
    if cp is None:
        return 0
    sys.stdout.write(cp.stdout or "")
    sys.stderr.write(cp.stderr or "")
    return cp.returncode


def cmd_list_presets(args: argparse.Namespace) -> int:
    _ensure_tool()
    cp = _run(
        [HANDBRAKE, "--preset-list"],
        dry_run=args.dry_run,
        verbose=args.verbose,
        capture=True,
    )
    if cp is None:
        return 0
    # HandBrake writes the preset list to stderr.
    out = (cp.stderr or "") + (cp.stdout or "")
    sys.stdout.write(out)
    return cp.returncode


def _build_encode_cmd(
    inp: Path,
    out: Path,
    preset: str,
    *,
    two_pass: bool = False,
    optimize: bool = False,
    extras: list[str] | None = None,
) -> list[str]:
    cmd = [HANDBRAKE, "-i", str(inp), "-o", str(out), "-Z", preset]
    if two_pass:
        cmd.append("-2")
    if optimize:
        cmd.append("--optimize")
    if extras:
        cmd += extras
    return cmd


def cmd_encode(args: argparse.Namespace) -> int:
    _ensure_tool()
    inp, out = Path(args.input), Path(args.output)
    _require_file(inp)
    _ensure_outdir(out)
    cmd = _build_encode_cmd(
        inp, out, args.preset, two_pass=args.two_pass, optimize=args.optimize
    )
    cp = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return 0 if cp is None else cp.returncode


def cmd_custom(args: argparse.Namespace) -> int:
    _ensure_tool()
    inp, out = Path(args.input), Path(args.output)
    _require_file(inp)
    _ensure_outdir(out)

    cmd = [
        HANDBRAKE,
        "-i",
        str(inp),
        "-o",
        str(out),
        "-e",
        args.encoder,
        "-q",
        str(args.quality),
    ]
    if args.preset_name:
        cmd += ["--encoder-preset", args.preset_name]
    if args.tune:
        cmd += ["--encoder-tune", args.tune]
    if args.audio_bitrate is not None:
        cmd += ["-B", str(args.audio_bitrate)]
    # Sensible defaults.
    cmd += [
        "-E",
        "av_aac",
        "-a",
        "1",
        "--all-subtitles",
        "--subtitle-burned=none",
        "--auto-anamorphic",
    ]
    if args.optimize:
        cmd.append("--optimize")
    if args.two_pass:
        cmd.append("-2")
    cp = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return 0 if cp is None else cp.returncode


def cmd_apple(args: argparse.Namespace) -> int:
    _ensure_tool()
    device = args.device.lower()
    if device not in APPLE_PRESETS:
        _die(
            f"unknown --device: {args.device}. "
            f"Choose one of: {', '.join(APPLE_PRESETS)}"
        )
    inp, out = Path(args.input), Path(args.output)
    _require_file(inp)
    _ensure_outdir(out)
    cmd = _build_encode_cmd(
        inp, out, APPLE_PRESETS[device], two_pass=args.two_pass, optimize=True
    )
    cp = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return 0 if cp is None else cp.returncode


# Extensions HandBrake will happily ingest.
_INPUT_EXTS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".flv",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".mts",
    ".vob",
    ".3gp",
}


def cmd_batch(args: argparse.Namespace) -> int:
    _ensure_tool()
    indir, outdir = Path(args.indir), Path(args.outdir)
    if not indir.is_dir():
        _die(f"--indir is not a directory: {indir}")
    outdir.mkdir(parents=True, exist_ok=True)

    ext = args.output_ext.lstrip(".")
    rc_total = 0
    count = 0
    for src in sorted(indir.rglob("*")):
        if not src.is_file():
            continue
        if src.suffix.lower() not in _INPUT_EXTS:
            continue
        rel = src.relative_to(indir).with_suffix(f".{ext}")
        dst = outdir / rel
        if dst.exists() and not args.overwrite:
            if args.verbose:
                print(f"skip (exists): {dst}", file=sys.stderr)
            continue
        _ensure_outdir(dst)
        cmd = _build_encode_cmd(
            src, dst, args.preset, two_pass=args.two_pass, optimize=args.optimize
        )
        cp = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
        count += 1
        if cp is not None and cp.returncode != 0:
            print(f"FAILED ({cp.returncode}): {src}", file=sys.stderr)
            rc_total = cp.returncode
    if args.verbose or args.dry_run:
        print(f"batch: processed {count} file(s)", file=sys.stderr)
    return rc_total


def cmd_inspect(args: argparse.Namespace) -> int:
    _ensure_tool()
    inp = Path(args.input)
    _require_file(inp)
    cmd = [HANDBRAKE, "-i", str(inp), "--scan", "-t", "0"]
    if args.json:
        cmd.append("--json")
    cp = _run(cmd, dry_run=args.dry_run, verbose=args.verbose, capture=True)
    if cp is None:
        return 0
    # HandBrake writes scan output to stderr. When --json is set it still
    # interleaves log lines, so we surface both streams to the caller and
    # try to pluck the JSON document out if possible.
    out = cp.stdout or ""
    err = cp.stderr or ""
    if args.json:
        # Find the JSON object in the combined output.
        blob = out + err
        start = blob.find("{")
        end = blob.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(blob[start : end + 1])
                json.dump(obj, sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
                return cp.returncode
            except json.JSONDecodeError:
                pass
        # Fallback: dump raw.
        sys.stdout.write(blob)
    else:
        sys.stdout.write(out)
        sys.stderr.write(err)
    return cp.returncode


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="handbrake.py",
        description="HandBrakeCLI helper (presets, custom, Apple, batch, inspect).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the command that would run, then exit",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="echo the command before running"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # check
    sp = sub.add_parser("check", help="print HandBrakeCLI version")
    sp.set_defaults(func=cmd_check)

    # list-presets
    sp = sub.add_parser("list-presets", help="print built-in preset list")
    sp.set_defaults(func=cmd_list_presets)

    # encode
    sp = sub.add_parser("encode", help="encode with a built-in preset")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument(
        "--preset",
        "-Z",
        required=True,
        help='exact HandBrake preset name (e.g. "Fast 1080p30")',
    )
    sp.add_argument("--2pass", dest="two_pass", action="store_true")
    sp.add_argument(
        "--optimize",
        action="store_true",
        help="move moov atom to head (web/Mac-friendly MP4)",
    )
    sp.set_defaults(func=cmd_encode)

    # custom
    sp = sub.add_parser("custom", help="custom encoder / quality / tune")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument(
        "--encoder", required=True, choices=ENCODERS, help="video encoder backend"
    )
    sp.add_argument(
        "--quality",
        type=float,
        required=True,
        help="CRF for x264/x265 (typ 18-28); VT uses 0-100",
    )
    sp.add_argument(
        "--preset-name",
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
            "placebo",
        ],
        help="encoder speed preset (x264/x265)",
    )
    sp.add_argument(
        "--tune",
        choices=[
            "film",
            "grain",
            "animation",
            "psnr",
            "ssim",
            "fastdecode",
            "zerolatency",
            "stillimage",
        ],
        help="encoder tune",
    )
    sp.add_argument(
        "--audio-bitrate",
        type=int,
        default=128,
        help="AAC bitrate in kbps (default 128)",
    )
    sp.add_argument("--optimize", action="store_true")
    sp.add_argument("--2pass", dest="two_pass", action="store_true")
    sp.set_defaults(func=cmd_custom)

    # apple
    sp = sub.add_parser("apple", help="Apple device preset shortcut")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--device", required=True, choices=list(APPLE_PRESETS.keys()))
    sp.add_argument("--2pass", dest="two_pass", action="store_true")
    sp.set_defaults(func=cmd_apple)

    # batch
    sp = sub.add_parser("batch", help="encode every video under --indir")
    sp.add_argument("--indir", required=True)
    sp.add_argument("--outdir", required=True)
    sp.add_argument("--preset", "-Z", required=True)
    sp.add_argument(
        "--output-ext", default="mp4", help="output container extension (default: mp4)"
    )
    sp.add_argument("--2pass", dest="two_pass", action="store_true")
    sp.add_argument("--optimize", action="store_true")
    sp.add_argument(
        "--overwrite",
        action="store_true",
        help="re-encode even if output already exists",
    )
    sp.set_defaults(func=cmd_batch)

    # inspect
    sp = sub.add_parser("inspect", help="scan source and print info")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--json", action="store_true", help="request JSON scan output")
    sp.set_defaults(func=cmd_inspect)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
