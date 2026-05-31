#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
ffmpeg-normalize helper — EBU R128 loudness normalization wrapper.

Subcommands:
    check                                       Verify ffmpeg-normalize is installed.
    normalize --input I --output O [opts]       Normalize one file.
    preset    --input I --output O --platform P Normalize one file using a platform preset.
    batch     --indir D --outdir D2 [opts]      Batch-normalize a directory.

Presets (used by `preset` and optionally by `batch`):
    youtube         -t -14  -tp -1.0
    spotify         -t -14  -tp -1.0
    apple-podcasts  -t -16  -tp -1.5  -lrt 11
    ebu-broadcast   -t -23  -tp -2.0  -lrt 7
    atsc-a85        -t -24  -tp -2.0  -lrt 7

Examples:
    uv run normalize.py check
    uv run normalize.py normalize --input in.mp3 --output out.mp3 --target -16 --true-peak -1.5 --lra 11
    uv run normalize.py preset --input in.mp3 --output out.mp3 --platform apple-podcasts
    uv run normalize.py batch --indir episodes/ --outdir normalized/ --platform spotify
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PRESETS = {
    "youtube": {"target": -14.0, "true_peak": -1.0, "lra": None},
    "spotify": {"target": -14.0, "true_peak": -1.0, "lra": None},
    "apple-podcasts": {"target": -16.0, "true_peak": -1.5, "lra": 11.0},
    "ebu-broadcast": {"target": -23.0, "true_peak": -2.0, "lra": 7.0},
    "atsc-a85": {"target": -24.0, "true_peak": -2.0, "lra": 7.0},
}

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".ts"}


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def find_tool() -> str:
    path = shutil.which("ffmpeg-normalize")
    if not path:
        print(
            "Error: ffmpeg-normalize not installed. Run: pip install ffmpeg-normalize",
            file=sys.stderr,
        )
        sys.exit(2)
    return path


def default_codec_for(output: Path) -> list[str]:
    """Return sensible -c:a args based on output extension."""
    ext = output.suffix.lower()
    if ext == ".mp4" or ext == ".m4a":
        return ["-c:a", "aac", "-b:a", "192k"]
    if ext == ".mkv" or ext == ".mov" or ext == ".webm":
        return ["-c:a", "aac", "-b:a", "192k"]
    if ext == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "192k"]
    if ext == ".flac":
        return ["-c:a", "flac"]
    if ext == ".ogg" or ext == ".opus":
        return ["-c:a", "libopus", "-b:a", "128k"]
    # wav / default
    return []


def build_cmd(
    tool: str,
    inputs: list[Path],
    *,
    output: Path | None = None,
    outdir: Path | None = None,
    target: float,
    true_peak: float,
    lra: float | None,
    codec: str | None,
    bitrate: str | None,
    dry_run: bool,
    progress: bool,
    print_stats: bool,
    extra: list[str],
) -> list[str]:
    cmd: list[str] = [tool, *[str(i) for i in inputs]]
    if output is not None:
        cmd += ["-o", str(output)]
    if outdir is not None:
        cmd += ["-of", str(outdir)]
    cmd += ["-t", str(target), "-tp", str(true_peak)]
    if lra is not None:
        cmd += ["-lrt", str(lra)]
    if codec:
        cmd += ["-c:a", codec]
        if bitrate:
            cmd += ["-b:a", bitrate]
    elif output is not None:
        cmd += default_codec_for(output)
    if dry_run:
        cmd.append("--dry-run")
    if progress:
        cmd.append("--progress")
    if print_stats:
        cmd.append("--print-stats")
    cmd += extra
    return cmd


def run(cmd: list[str], verbose: bool) -> int:
    log("+ " + " ".join(cmd), verbose)
    result = subprocess.run(cmd)
    return result.returncode


def apply_preset(args: argparse.Namespace) -> dict:
    preset = PRESETS[args.platform]
    return {
        "target": preset["target"],
        "true_peak": preset["true_peak"],
        "lra": preset["lra"],
    }


def cmd_check(args: argparse.Namespace) -> int:
    tool = find_tool()
    log(f"ffmpeg-normalize found at: {tool}", True)
    result = subprocess.run([tool, "--version"], capture_output=True, text=True)
    sys.stdout.write(result.stdout or result.stderr)
    if shutil.which("ffmpeg") is None:
        print(
            "Warning: ffmpeg not found on PATH (ffmpeg-normalize needs it).",
            file=sys.stderr,
        )
        return 1
    return result.returncode


def cmd_normalize(args: argparse.Namespace) -> int:
    tool = find_tool()
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: input not found: {in_path}", file=sys.stderr)
        return 1
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_cmd(
        tool,
        [in_path],
        output=out_path,
        target=args.target,
        true_peak=args.true_peak,
        lra=args.lra,
        codec=args.codec,
        bitrate=args.bitrate,
        dry_run=args.dry_run,
        progress=False,
        print_stats=args.print_stats,
        extra=args.extra or [],
    )
    return run(cmd, args.verbose)


def cmd_preset(args: argparse.Namespace) -> int:
    p = apply_preset(args)
    args.target = p["target"]
    args.true_peak = p["true_peak"]
    args.lra = p["lra"]
    return cmd_normalize(args)


def cmd_batch(args: argparse.Namespace) -> int:
    tool = find_tool()
    indir = Path(args.indir)
    outdir = Path(args.outdir)
    if not indir.is_dir():
        print(f"Error: --indir is not a directory: {indir}", file=sys.stderr)
        return 1
    outdir.mkdir(parents=True, exist_ok=True)

    exts = AUDIO_EXTS | VIDEO_EXTS
    files = sorted(
        p for p in indir.iterdir() if p.is_file() and p.suffix.lower() in exts
    )
    if not files:
        print(f"Error: no media files (audio/video) in {indir}", file=sys.stderr)
        return 1

    if args.platform:
        p = apply_preset(args)
        args.target = p["target"]
        args.true_peak = p["true_peak"]
        args.lra = p["lra"]

    cmd = build_cmd(
        tool,
        files,
        outdir=outdir,
        target=args.target,
        true_peak=args.true_peak,
        lra=args.lra,
        codec=args.codec,
        bitrate=args.bitrate,
        dry_run=args.dry_run,
        progress=args.progress,
        print_stats=args.print_stats,
        extra=args.extra or [],
    )
    log(f"Batch: {len(files)} files -> {outdir}", args.verbose)
    return run(cmd, args.verbose)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ffmpeg-normalize helper: EBU R128 loudness normalization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Print invoked commands to stderr.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s_check = sub.add_parser("check", help="Verify ffmpeg-normalize is installed.")
    s_check.set_defaults(func=cmd_check)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--target",
        type=float,
        default=-23.0,
        help="Integrated loudness target in LUFS (default -23).",
    )
    common.add_argument(
        "--true-peak",
        dest="true_peak",
        type=float,
        default=-1.5,
        help="True peak ceiling dBFS (default -1.5).",
    )
    common.add_argument(
        "--lra",
        type=float,
        default=None,
        help="Loudness range target in LU (default: unset).",
    )
    common.add_argument(
        "--codec",
        default=None,
        help="Audio codec passed to -c:a (auto per extension if omitted).",
    )
    common.add_argument("--bitrate", default=None, help="Audio bitrate, e.g. 192k.")
    common.add_argument(
        "--dry-run", action="store_true", help="Print the ffmpeg-normalize plan only."
    )
    common.add_argument(
        "--print-stats", action="store_true", help="Emit loudnorm JSON stats."
    )
    common.add_argument(
        "--extra",
        nargs=argparse.REMAINDER,
        help="Extra args passed through to ffmpeg-normalize.",
    )

    s_norm = sub.add_parser("normalize", parents=[common], help="Normalize one file.")
    s_norm.add_argument("--input", required=True)
    s_norm.add_argument("--output", required=True)
    s_norm.set_defaults(func=cmd_normalize)

    s_preset = sub.add_parser(
        "preset", parents=[common], help="Normalize one file using a platform preset."
    )
    s_preset.add_argument("--input", required=True)
    s_preset.add_argument("--output", required=True)
    s_preset.add_argument("--platform", required=True, choices=sorted(PRESETS.keys()))
    s_preset.set_defaults(func=cmd_preset)

    s_batch = sub.add_parser(
        "batch", parents=[common], help="Batch-normalize a directory."
    )
    s_batch.add_argument("--indir", required=True)
    s_batch.add_argument("--outdir", required=True)
    s_batch.add_argument(
        "--platform",
        choices=sorted(PRESETS.keys()),
        default=None,
        help="Optional preset; overrides --target/--true-peak/--lra.",
    )
    s_batch.add_argument(
        "--progress", action="store_true", help="Show tqdm progress bar."
    )
    s_batch.set_defaults(func=cmd_batch)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
