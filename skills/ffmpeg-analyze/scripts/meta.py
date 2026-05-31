#!/usr/bin/env python3
"""
ffmpeg-metadata helper: set tags, author chapters, embed cover art, attach
files, strip metadata, and set disposition flags.

All operations use `-c copy` (no re-encoding). Stdlib only. Non-interactive.
Prints the ffmpeg command it runs. Use --dry-run to inspect without executing.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from typing import List, Optional, Sequence, Tuple


# ----------------------------------------------------------------------------
# command plumbing
# ----------------------------------------------------------------------------


def run_cmd(cmd: Sequence[str], *, dry_run: bool = False, verbose: bool = False) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    try:
        res = subprocess.run(list(cmd), check=False)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 127
    if verbose:
        print(f"(exit {res.returncode})", file=sys.stderr)
    return res.returncode


def parse_kv(pairs: Sequence[str]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"error: expected KEY=VALUE, got {p!r}")
        k, v = p.split("=", 1)
        k = k.strip()
        if not k:
            raise SystemExit(f"error: empty key in {p!r}")
        out.append((k, v))
    return out


def parse_stream_tag(spec: str) -> Tuple[str, str, str]:
    """
    'a:0:language=eng' -> ('a', '0', 'language=eng')
    'v:0:title=Main'   -> ('v', '0', 'title=Main')
    's:0:language=eng' -> ('s', '0', 'language=eng')
    """
    parts = spec.split(":", 2)
    if len(parts) != 3 or "=" not in parts[2]:
        raise SystemExit(
            f"error: stream-tag must look like TYPE:INDEX:KEY=VALUE, got {spec!r}"
        )
    stype, sindex, kv = parts
    if stype not in {"v", "a", "s", "t", "d"}:
        raise SystemExit(f"error: unknown stream type {stype!r} in {spec!r}")
    if not sindex.isdigit():
        raise SystemExit(f"error: stream index must be integer in {spec!r}")
    return stype, sindex, kv


# ----------------------------------------------------------------------------
# timestamps -> ffmetadata chapters
# ----------------------------------------------------------------------------


def ts_to_ms(ts: str) -> int:
    """
    '0:00'       -> 0
    '1:30'       -> 90000
    '1:02:03'    -> 3723000
    '1:02:03.500'-> 3723500
    """
    parts = ts.split(":")
    if not parts or len(parts) > 3:
        raise SystemExit(f"error: bad timestamp {ts!r}")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        raise SystemExit(f"error: bad timestamp {ts!r}")
    if len(nums) == 1:
        total = nums[0]
    elif len(nums) == 2:
        total = nums[0] * 60 + nums[1]
    else:
        total = nums[0] * 3600 + nums[1] * 60 + nums[2]
    return int(round(total * 1000))


def build_ffmetadata_from_timestamps(entries: Sequence[str]) -> str:
    """
    entries: ['0:00 Intro', '1:00 Main', '3:00 Outro']
    End of chapter N = start of chapter N+1; last chapter ends at 2^31-1 ms
    (ffmpeg will clamp to file duration on mux).
    """
    parsed: List[Tuple[int, str]] = []
    for e in entries:
        e = e.strip()
        if not e:
            continue
        if " " not in e:
            raise SystemExit(f"error: expected 'TIMESTAMP TITLE', got {e!r}")
        ts, title = e.split(" ", 1)
        parsed.append((ts_to_ms(ts), title.strip()))
    if not parsed:
        raise SystemExit("error: no chapter entries provided")
    parsed.sort(key=lambda x: x[0])
    lines = [";FFMETADATA1"]
    for i, (start, title) in enumerate(parsed):
        end = parsed[i + 1][0] if i + 1 < len(parsed) else 2_147_483_647
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start}")
        lines.append(f"END={end}")
        lines.append(f"title={title}")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------
# subcommands
# ----------------------------------------------------------------------------


def cmd_set(args: argparse.Namespace) -> int:
    cmd: List[str] = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-map",
        "0",
        "-c",
        "copy",
    ]
    for k, v in parse_kv(args.tags or []):
        cmd += ["-metadata", f"{k}={v}"]
    for spec in args.stream_tags or []:
        stype, sindex, kv = parse_stream_tag(spec)
        cmd += [f"-metadata:s:{stype}:{sindex}", kv]
    cmd.append(args.output)
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_chapters(args: argparse.Namespace) -> int:
    if bool(args.chapters_file) == bool(args.from_timestamps):
        raise SystemExit(
            "error: provide exactly one of --chapters-file or --from-timestamps"
        )
    tmp_path: Optional[str] = None
    try:
        if args.from_timestamps:
            content = build_ffmetadata_from_timestamps(args.from_timestamps)
            fd, tmp_path = tempfile.mkstemp(prefix="chapters_", suffix=".ffmetadata")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            meta_input = tmp_path
            if args.verbose:
                print(f"(wrote ffmetadata to {tmp_path})", file=sys.stderr)
                print(content, file=sys.stderr)
        else:
            meta_input = args.chapters_file

        cmd = [
            "ffmpeg",
            "-y" if args.overwrite else "-n",
            "-i",
            args.input,
            "-i",
            meta_input,
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c",
            "copy",
            args.output,
        ]
        return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        if tmp_path and not args.keep_tmp and not args.dry_run:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def cmd_extract_chapters(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-f",
        "ffmetadata",
        args.output,
    ]
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_cover(args: argparse.Namespace) -> int:
    # Map all of input 0 plus the image from input 1, then mark the image
    # as attached_pic. Works for MP3, MP4/M4A, MKV.
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-i",
        args.image,
        "-map",
        "0",
        "-map",
        "1:v",
        "-c",
        "copy",
        "-disposition:v:1",
        "attached_pic",
        "-metadata:s:v:1",
        "title=Cover",
        "-metadata:s:v:1",
        "comment=Cover (front)",
    ]
    # MP3s benefit from explicit ID3v2 version
    if args.output.lower().endswith(".mp3"):
        cmd += ["-id3v2_version", "3"]
    cmd.append(args.output)
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_attach(args: argparse.Namespace) -> int:
    mime = args.mimetype
    if mime is None:
        mime = _guess_mime(args.file)
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-map",
        "0",
        "-c",
        "copy",
        "-attach",
        args.file,
        "-metadata:s:t",
        f"mimetype={mime}",
        "-metadata:s:t",
        f"filename={os.path.basename(args.file)}",
        args.output,
    ]
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    table = {
        "ttf": "application/x-truetype-font",
        "otf": "application/vnd.ms-opentype",
        "woff": "font/woff",
        "woff2": "font/woff2",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "srt": "application/x-subrip",
        "ass": "text/x-ass",
        "ssa": "text/x-ssa",
        "txt": "text/plain",
        "xml": "text/xml",
        "pdf": "application/pdf",
    }
    return table.get(ext, "application/octet-stream")


def cmd_strip(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-map",
        "0",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c",
        "copy",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        args.output,
    ]
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_disposition(args: argparse.Namespace) -> int:
    cmd = [
        "ffmpeg",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-map",
        "0",
        "-c",
        "copy",
        f"-disposition:{args.stream}",
        args.flags,
        args.output,
    ]
    return run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ----------------------------------------------------------------------------
# argparse wiring
# ----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meta.py",
        description="ffmpeg metadata / chapter / cover art / attachment helper",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print command, do not execute"
    )
    p.add_argument("--verbose", action="store_true", help="extra log output")
    p.add_argument(
        "--overwrite", action="store_true", help="pass -y instead of -n to ffmpeg"
    )

    sub = p.add_subparsers(dest="op", required=True)

    # set
    sp = sub.add_parser("set", help="set container and/or per-stream tags")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--tags", nargs="*", metavar="KEY=VALUE", help="container-level tags"
    )
    sp.add_argument(
        "--stream-tags",
        nargs="*",
        metavar="TYPE:INDEX:KEY=VALUE",
        help="per-stream tags, e.g. a:0:language=eng",
    )
    sp.set_defaults(func=cmd_set)

    # chapters
    sp = sub.add_parser("chapters", help="add chapters to file")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--chapters-file", help="path to existing ffmetadata file")
    sp.add_argument(
        "--from-timestamps",
        nargs="*",
        metavar="'MM:SS TITLE'",
        help="inline chapter entries, e.g. '0:00 Intro' '1:00 Main'",
    )
    sp.add_argument(
        "--keep-tmp",
        action="store_true",
        help="do not delete auto-generated ffmetadata file",
    )
    sp.set_defaults(func=cmd_chapters)

    # extract-chapters
    sp = sub.add_parser("extract-chapters", help="dump chapters to ffmetadata file")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True, help="output .txt / .ffmetadata")
    sp.set_defaults(func=cmd_extract_chapters)

    # cover
    sp = sub.add_parser("cover", help="embed cover art / thumbnail")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--image", required=True, help="jpg/png cover art")
    sp.set_defaults(func=cmd_cover)

    # attach (MKV)
    sp = sub.add_parser("attach", help="attach file to MKV (font, image, etc.)")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--file", required=True, help="file to attach")
    sp.add_argument("--mimetype", help="override mimetype (auto-detected)")
    sp.set_defaults(func=cmd_attach)

    # strip
    sp = sub.add_parser("strip", help="remove all metadata and chapters")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_strip)

    # disposition
    sp = sub.add_parser("disposition", help="set disposition flags on a stream")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--stream", required=True, help="stream specifier, e.g. s:0, a:1, v:0"
    )
    sp.add_argument(
        "--flags",
        required=True,
        help="flags, e.g. '+default+forced' (add), 'default' (set), '0' (clear)",
    )
    sp.set_defaults(func=cmd_disposition)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
