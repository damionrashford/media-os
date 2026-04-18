#!/usr/bin/env python3
"""cc.py — CEA-608/708 closed-caption helper around ffmpeg + ccextractor.

Subcommands:
  detect       Probe a file for embedded 608/708 SEI or c608/c708 tracks.
  preserve     Re-encode H.264 with `-a53cc 1` so SEI captions survive.
  extract      Shell out to `ccextractor` to produce a .srt (or other format).
  passthrough  Remux without re-encoding so SEI NAL units are preserved.

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg: str, *, verbose: bool = False, force: bool = False) -> None:
    if verbose or force:
        print(msg, file=sys.stderr)


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(_quote(arg) for arg in cmd)
    log(f"$ {printable}", verbose=True, force=verbose or dry_run)
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def _quote(arg: str) -> str:
    if any(c in arg for c in " \t\"'$`\\|&;<>()"):
        escaped = arg.replace("'", "'\\''")
        return f"'{escaped}'"
    return arg


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        hint = {
            "ffmpeg": "Install ffmpeg: brew install ffmpeg (macOS) / apt install ffmpeg.",
            "ffprobe": "ffprobe ships with ffmpeg: brew install ffmpeg.",
            "ccextractor": (
                "Install ccextractor: brew install ccextractor (macOS) / "
                "apt install ccextractor (Debian/Ubuntu). "
                "See https://www.ccextractor.org/"
            ),
        }.get(tool, f"Install {tool} and ensure it is on PATH.")
        print(f"error: required tool not found: {tool}\n{hint}", file=sys.stderr)
        sys.exit(127)
    return path


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


def cmd_detect(args: argparse.Namespace) -> int:
    require("ffprobe")
    require("ffmpeg")
    src = Path(args.input)
    if not src.exists():
        print(f"error: input not found: {src}", file=sys.stderr)
        return 2

    findings: dict[str, object] = {
        "input": str(src),
        "sei_a53_cc": False,
        "dedicated_cc_stream": None,
        "readeia608_hits": 0,
    }

    # 1) look for A53 CC side-data on the first ~20 video frames
    probe_cmd = [
        "ffprobe",
        "-loglevel",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "frame=side_data_list",
        "-read_intervals",
        "%+#20",
        "-of",
        "json",
        str(src),
    ]
    log(f"$ {' '.join(_quote(a) for a in probe_cmd)}", verbose=args.verbose)
    if not args.dry_run:
        try:
            result = subprocess.run(
                probe_cmd, capture_output=True, text=True, check=False
            )
            if result.stdout:
                data = json.loads(result.stdout or "{}")
                for frame in data.get("frames", []):
                    for sd in frame.get("side_data_list", []):
                        sd_type = (sd.get("side_data_type") or "").lower()
                        if "a53" in sd_type or "closed caption" in sd_type:
                            findings["sei_a53_cc"] = True
                            break
                    if findings["sei_a53_cc"]:
                        break
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log(f"ffprobe side-data check failed: {e}", verbose=args.verbose)

    # 2) look for a dedicated c608 / c708 / eia_608 subtitle stream
    stream_cmd = [
        "ffprobe",
        "-loglevel",
        "error",
        "-show_entries",
        "stream=index,codec_name,codec_type",
        "-of",
        "json",
        str(src),
    ]
    log(f"$ {' '.join(_quote(a) for a in stream_cmd)}", verbose=args.verbose)
    if not args.dry_run:
        try:
            result = subprocess.run(
                stream_cmd, capture_output=True, text=True, check=False
            )
            data = json.loads(result.stdout or "{}")
            for stream in data.get("streams", []):
                name = (stream.get("codec_name") or "").lower()
                if name in {"eia_608", "eia_708", "c608", "c708", "closed_caption"}:
                    findings["dedicated_cc_stream"] = {
                        "index": stream.get("index"),
                        "codec_name": name,
                    }
                    break
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log(f"ffprobe stream check failed: {e}", verbose=args.verbose)

    # 3) readeia608 filter sniff on the first ~10 seconds (picture line 21)
    read_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-t",
        "10",
        "-i",
        str(src),
        "-vf",
        "readeia608,metadata=mode=print",
        "-an",
        "-f",
        "null",
        "-",
    ]
    log(f"$ {' '.join(_quote(a) for a in read_cmd)}", verbose=args.verbose)
    if not args.dry_run:
        try:
            result = subprocess.run(
                read_cmd, capture_output=True, text=True, check=False
            )
            text = (result.stderr or "") + (result.stdout or "")
            findings["readeia608_hits"] = text.count("lavfi.readeia608")
        except FileNotFoundError as e:
            log(f"ffmpeg readeia608 sniff failed: {e}", verbose=args.verbose)

    print(json.dumps(findings, indent=2))
    has_cc = (
        findings["sei_a53_cc"]
        or findings["dedicated_cc_stream"] is not None
        or (
            isinstance(findings["readeia608_hits"], int)
            and findings["readeia608_hits"] > 0
        )
    )
    return 0 if has_cc or args.dry_run else 1


# ---------------------------------------------------------------------------
# preserve
# ---------------------------------------------------------------------------


def cmd_preserve(args: argparse.Namespace) -> int:
    require("ffmpeg")
    src = Path(args.input)
    dst = Path(args.output)
    if not args.dry_run and not src.exists():
        print(f"error: input not found: {src}", file=sys.stderr)
        return 2
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y" if args.overwrite else "-n",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-a53cc",
        "1",
        "-c:a",
        "copy",
        str(dst),
    ]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


def cmd_extract(args: argparse.Namespace) -> int:
    require("ccextractor")
    src = Path(args.input)
    dst = Path(args.output)
    if not args.dry_run and not src.exists():
        print(f"error: input not found: {src}", file=sys.stderr)
        return 2
    fmt_map = {".srt": "srt", ".vtt": "webvtt", ".ttml": "ttml", ".mcc": "mcc"}
    out_fmt = args.format or fmt_map.get(dst.suffix.lower(), "srt")
    cmd = ["ccextractor", str(src), "-o", str(dst), f"-out={out_fmt}"]
    if args.channel:
        cmd.extend([f"-{args.channel}"])  # ccextractor uses -1/-2/-cc1/-cc2 variants
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# passthrough
# ---------------------------------------------------------------------------


def cmd_passthrough(args: argparse.Namespace) -> int:
    require("ffmpeg")
    src = Path(args.input)
    dst = Path(args.output)
    if not args.dry_run and not src.exists():
        print(f"error: input not found: {src}", file=sys.stderr)
        return 2
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y" if args.overwrite else "-n",
        "-i",
        str(src),
        "-c",
        "copy",
        "-map",
        "0",
        str(dst),
    ]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cc.py",
        description="CEA-608/708 closed-caption helper (ffmpeg + ccextractor).",
    )
    p.add_argument("--dry-run", action="store_true", help="print commands; do not run")
    p.add_argument(
        "--verbose", action="store_true", help="echo commands before running"
    )

    sub = p.add_subparsers(dest="subcommand", required=True)

    pd = sub.add_parser("detect", help="probe for 608/708 captions")
    pd.add_argument("--input", required=True, help="source media file")
    pd.set_defaults(func=cmd_detect)

    pp = sub.add_parser("preserve", help="re-encode H.264 with -a53cc 1")
    pp.add_argument("--input", required=True)
    pp.add_argument("--output", required=True)
    pp.add_argument("--crf", type=int, default=20)
    pp.add_argument("--preset", default="medium")
    pp.add_argument("--overwrite", action="store_true", help="allow overwriting output")
    pp.set_defaults(func=cmd_preserve)

    pe = sub.add_parser("extract", help="extract CC to SRT/VTT via ccextractor")
    pe.add_argument("--input", required=True)
    pe.add_argument("--output", required=True)
    pe.add_argument(
        "--format",
        choices=["srt", "webvtt", "ttml", "mcc"],
        help="override format (default: infer from output suffix)",
    )
    pe.add_argument("--channel", help="ccextractor channel flag, e.g. 'cc1' or 'cc2'")
    pe.set_defaults(func=cmd_extract)

    pt = sub.add_parser("passthrough", help="remux with -c copy, preserving SEI CC")
    pt.add_argument("--input", required=True)
    pt.add_argument("--output", required=True)
    pt.add_argument("--overwrite", action="store_true")
    pt.set_defaults(func=cmd_passthrough)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
