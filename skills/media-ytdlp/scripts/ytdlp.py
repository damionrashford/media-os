#!/usr/bin/env python3
"""yt-dlp subprocess wrapper for the media-ytdlp skill.

Stdlib-only argparse CLI. Subcommands mirror the most common recipes so the
agent (or a human) can invoke yt-dlp without remembering flag orderings.

Every command prints the exact yt-dlp invocation before running it. Pass
--dry-run to skip execution. Pass --verbose to forward -v to yt-dlp for
extractor tracebacks.

Usage:
    python3 ytdlp.py check
    python3 ytdlp.py list-formats --url URL
    python3 ytdlp.py download    --url URL [--quality best|1080p|720p|audio-mp3|audio-flac]
                                 [--output TEMPLATE] [--subs] [--cookies-browser chrome]
    python3 ytdlp.py playlist    --url URL --outdir DIR [--start N] [--end N] [--archive FILE]
    python3 ytdlp.py live        --url URL --output OUT
    python3 ytdlp.py audio       --url URL --output OUT --format mp3|m4a|flac|opus
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def which_or_die(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        print(f"error: required binary '{binary}' not found on PATH", file=sys.stderr)
        sys.exit(127)
    return path


def run(cmd: Sequence[str], *, dry_run: bool) -> int:
    quoted = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {quoted}", flush=True)
    if dry_run:
        return 0
    try:
        return subprocess.call(list(cmd))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run", action="store_true", help="print the command but do not execute"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="pass -v to yt-dlp for extractor tracebacks",
    )
    parser.add_argument(
        "--cookies-browser",
        metavar="BROWSER",
        help="pull cookies from a local browser (chrome, firefox, safari, edge, brave)",
    )
    parser.add_argument(
        "--rate-limit",
        metavar="RATE",
        help="throttle download bandwidth, e.g. 1M or 500K",
    )


def base_flags(args: argparse.Namespace) -> List[str]:
    out: List[str] = []
    if getattr(args, "verbose", False):
        out.append("-v")
    if getattr(args, "cookies_browser", None):
        out += ["--cookies-from-browser", args.cookies_browser]
    if getattr(args, "rate_limit", None):
        out += ["-r", args.rate_limit]
    return out


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    print("== yt-dlp ==")
    ytdlp = shutil.which("yt-dlp")
    if ytdlp:
        print(f"path: {ytdlp}")
        run([ytdlp, "--version"], dry_run=False)
    else:
        print(
            "yt-dlp: NOT FOUND (try `pip install -U yt-dlp` or `brew install yt-dlp`)"
        )

    print("\n== ffmpeg ==")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"path: {ffmpeg}")
        # only take the first line of version output
        out = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True
        ).stdout
        if out:
            print(out.splitlines()[0])
    else:
        print("ffmpeg: NOT FOUND (try `brew install ffmpeg`)")

    return 0 if (ytdlp and ffmpeg) else 1


def cmd_list_formats(args: argparse.Namespace) -> int:
    yt = which_or_die("yt-dlp")
    cmd = [yt, *base_flags(args), "-F", args.url]
    return run(cmd, dry_run=args.dry_run)


QUALITY_SELECTORS = {
    "best": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
    "480p": "bv*[height<=480]+ba/b[height<=480]",
    "audio-mp3": "ba/b",
    "audio-flac": "ba/b",
    "audio-m4a": "ba[ext=m4a]/ba/b",
    "audio-opus": "ba[ext=webm]/ba/b",
}


def cmd_download(args: argparse.Namespace) -> int:
    yt = which_or_die("yt-dlp")
    quality = args.quality or "best"
    if quality not in QUALITY_SELECTORS:
        print(
            f"error: unknown --quality {quality!r}; choose from {sorted(QUALITY_SELECTORS)}",
            file=sys.stderr,
        )
        return 2

    cmd: List[str] = [yt, *base_flags(args), "-f", QUALITY_SELECTORS[quality]]

    if quality.startswith("audio-"):
        audio_fmt = quality.split("-", 1)[1]
        cmd += ["-x", "--audio-format", audio_fmt, "--audio-quality", "0"]
    else:
        cmd += ["--merge-output-format", "mp4"]

    if args.subs:
        cmd += [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "en.*",
            "--convert-subs",
            "srt",
            "--embed-subs",
        ]

    if args.embed_metadata:
        cmd += ["--embed-thumbnail", "--embed-metadata", "--embed-chapters"]

    cmd += [
        "--restrict-filenames",
        "-o",
        args.output or "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        args.url,
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_playlist(args: argparse.Namespace) -> int:
    yt = which_or_die("yt-dlp")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    template = str(
        outdir / "%(playlist)s" / "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s"
    )
    cmd: List[str] = [
        yt,
        *base_flags(args),
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--restrict-filenames",
        "-o",
        template,
    ]

    if args.start is not None:
        cmd += ["--playlist-start", str(args.start)]
    if args.end is not None:
        cmd += ["--playlist-end", str(args.end)]
    if args.archive:
        cmd += ["--download-archive", args.archive]
    cmd.append(args.url)
    return run(cmd, dry_run=args.dry_run)


def cmd_live(args: argparse.Namespace) -> int:
    yt = which_or_die("yt-dlp")
    cmd = [
        yt,
        *base_flags(args),
        "--live-from-start",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mkv",
        "-o",
        args.output,
        args.url,
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_audio(args: argparse.Namespace) -> int:
    yt = which_or_die("yt-dlp")
    cmd = [
        yt,
        *base_flags(args),
        "-x",
        "--audio-format",
        args.format,
        "--audio-quality",
        "0",
        "--embed-thumbnail",
        "--embed-metadata",
        "-o",
        args.output,
        args.url,
    ]
    return run(cmd, dry_run=args.dry_run)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytdlp.py",
        description="yt-dlp subprocess wrapper (media-ytdlp skill).",
    )
    subs = parser.add_subparsers(dest="command", required=True)

    p_check = subs.add_parser("check", help="verify yt-dlp and ffmpeg are installed")
    p_check.set_defaults(func=cmd_check)

    p_fmt = subs.add_parser("list-formats", help="yt-dlp -F URL")
    p_fmt.add_argument("--url", required=True)
    add_common_flags(p_fmt)
    p_fmt.set_defaults(func=cmd_list_formats)

    p_dl = subs.add_parser("download", help="download a single URL")
    p_dl.add_argument("--url", required=True)
    p_dl.add_argument(
        "--quality",
        default="best",
        help="best | 1080p | 720p | 480p | audio-mp3 | audio-flac | audio-m4a | audio-opus",
    )
    p_dl.add_argument(
        "--output",
        help="output template (default: '%%(uploader)s - %%(title)s [%%(id)s].%%(ext)s')",
    )
    p_dl.add_argument(
        "--subs",
        action="store_true",
        help="fetch + embed English subs (incl. auto-generated)",
    )
    p_dl.add_argument(
        "--embed-metadata",
        action="store_true",
        help="embed thumbnail + metadata + chapters into the output container",
    )
    add_common_flags(p_dl)
    p_dl.set_defaults(func=cmd_download)

    p_pl = subs.add_parser("playlist", help="download an entire playlist or channel")
    p_pl.add_argument("--url", required=True)
    p_pl.add_argument("--outdir", required=True)
    p_pl.add_argument("--start", type=int, help="1-indexed playlist start item")
    p_pl.add_argument("--end", type=int, help="1-indexed playlist end item (inclusive)")
    p_pl.add_argument(
        "--archive", help="path to download-archive file (idempotent reruns)"
    )
    add_common_flags(p_pl)
    p_pl.set_defaults(func=cmd_playlist)

    p_live = subs.add_parser(
        "live", help="record a live stream from-the-start into MKV"
    )
    p_live.add_argument("--url", required=True)
    p_live.add_argument("--output", required=True)
    add_common_flags(p_live)
    p_live.set_defaults(func=cmd_live)

    p_audio = subs.add_parser(
        "audio", help="audio-only extract with embedded thumbnail + tags"
    )
    p_audio.add_argument("--url", required=True)
    p_audio.add_argument("--output", required=True)
    p_audio.add_argument(
        "--format", choices=["mp3", "m4a", "flac", "opus"], default="mp3"
    )
    add_common_flags(p_audio)
    p_audio.set_defaults(func=cmd_audio)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
