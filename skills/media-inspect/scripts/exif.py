#!/usr/bin/env python3
"""exif.py — argparse wrapper over ExifTool.

Subcommands:
  read            Dump tags (all, or a filtered list; optional JSON).
  write           Set one or more tags (repeatable --set KEY=VALUE).
  strip           Remove metadata: all, GPS only, or EXIF only.
  copy            Copy tags from a source file to a destination file.
  shift-dates     Shift AllDates by an ExifTool delta string ("Y:M:D h:m:s").
  gps             Set GPSLatitude/GPSLongitude with correct Ref tags.
  extract-thumbnail  Write the embedded thumbnail to a file.
  batch-rename    Rename files in a directory based on a date tag.
  sidecar         Create an XMP sidecar from a source file.

Global flags:
  --dry-run       Print the exiftool command but don't run it.
  --verbose       Print the exiftool command before running.

Stdlib only. Non-interactive. Requires `exiftool` on PATH.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from typing import Iterable, List, Sequence


def which_exiftool() -> str:
    path = shutil.which("exiftool")
    if not path:
        print(
            "error: `exiftool` not found on PATH. Install with:\n"
            "  brew install exiftool                    # macOS\n"
            "  sudo apt install libimage-exiftool-perl  # Debian/Ubuntu",
            file=sys.stderr,
        )
        sys.exit(127)
    return path


def run(cmd: Sequence[str], *, dry_run: bool, verbose: bool) -> int:
    if verbose or dry_run:
        print("+ " + " ".join(shlex.quote(c) for c in cmd))
    if dry_run:
        return 0
    try:
        completed = subprocess.run(cmd, check=False)
    except FileNotFoundError as exc:
        print(f"error: failed to execute {cmd[0]}: {exc}", file=sys.stderr)
        return 127
    return completed.returncode


def split_kv(s: str) -> tuple[str, str]:
    if "=" not in s:
        raise argparse.ArgumentTypeError(f"expected TAG=VALUE, got {s!r}")
    tag, _, value = s.partition("=")
    tag = tag.strip()
    if not tag:
        raise argparse.ArgumentTypeError(f"empty tag in {s!r}")
    return tag, value


def preserve_flags(preserve_mtime: bool) -> List[str]:
    flags = ["-overwrite_original"]
    if preserve_mtime:
        flags.insert(0, "-P")
    return flags


# ---------------- subcommand handlers ---------------- #


def cmd_read(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    cmd: List[str] = [exe]
    if args.json:
        cmd.append("-j")
    else:
        cmd.append("-g1")
    if args.tags:
        for t in args.tags:
            cmd.append(f"-{t}")
    cmd.append(args.input)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_write(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    if not args.set:
        print("error: at least one --set TAG=VALUE is required", file=sys.stderr)
        return 2
    cmd = [exe] + preserve_flags(args.preserve_mtime)
    for pair in args.set:
        tag, value = pair
        cmd.append(f"-{tag}={value}")
    cmd.append(args.input)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_strip(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    if args.gps_only and args.exif_only:
        print("error: pass at most one of --gps-only / --exif-only", file=sys.stderr)
        return 2
    cmd = [exe] + preserve_flags(args.preserve_mtime)
    if args.gps_only:
        cmd.append("-gps:all=")
    elif args.exif_only:
        cmd.append("-exif:all=")
    else:
        cmd.append("-all=")
    cmd.append(args.input)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_copy(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    cmd = [exe, "-TagsFromFile", args.src]
    if args.tags:
        for t in args.tags:
            cmd.append(f"-{t}")
    else:
        cmd.append("-all:all")
    cmd += preserve_flags(args.preserve_mtime)
    cmd.append(args.dst)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_shift_dates(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    delta = args.delta
    sign = "+" if not delta.startswith("-") else ""
    if delta.startswith(("+", "-")):
        sign = delta[0]
        delta = delta[1:]
    cmd = [exe] + preserve_flags(args.preserve_mtime)
    cmd.append(f"-AllDates{sign}={delta}")
    # Accept a file or a directory; recurse into dirs.
    if os.path.isdir(args.input):
        cmd += ["-r", args.input]
    else:
        cmd.append(args.input)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_gps(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    lat_ref = "N" if args.lat >= 0 else "S"
    lon_ref = "E" if args.lon >= 0 else "W"
    cmd = [exe] + preserve_flags(args.preserve_mtime)
    cmd += [
        f"-GPSLatitude={abs(args.lat)}",
        f"-GPSLatitudeRef={lat_ref}",
        f"-GPSLongitude={abs(args.lon)}",
        f"-GPSLongitudeRef={lon_ref}",
    ]
    cmd.append(args.input)
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_extract_thumbnail(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    cmd = [exe, "-b", "-ThumbnailImage", args.input]
    if args.verbose or args.dry_run:
        print(
            "+ "
            + " ".join(shlex.quote(c) for c in cmd)
            + f" > {shlex.quote(args.output)}"
        )
    if args.dry_run:
        return 0
    with open(args.output, "wb") as out:
        completed = subprocess.run(cmd, stdout=out, check=False)
    return completed.returncode


def cmd_batch_rename(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    if not os.path.isdir(args.dir):
        print(f"error: not a directory: {args.dir}", file=sys.stderr)
        return 2
    cmd = [
        exe,
        f"-FileName<{args.pattern}",
        "-d",
        args.format,
        "-r",
        args.dir,
    ]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_sidecar(args: argparse.Namespace) -> int:
    exe = which_exiftool()
    cmd = [exe, "-o", args.output, "-tagsFromFile", args.input]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------- CLI ---------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="exif.py",
        description="ExifTool wrapper: read/write/strip/copy/shift/gps/thumbnail/rename/sidecar.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the exiftool command, do not run"
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="print the exiftool command before running",
    )

    sub = p.add_subparsers(dest="command", required=True)

    # read
    sp = sub.add_parser("read", help="read metadata")
    sp.add_argument("--input", required=True)
    sp.add_argument("--tags", nargs="*", help="specific tag names (no leading dash)")
    sp.add_argument("--json", action="store_true", help="output JSON (-j)")
    sp.set_defaults(func=cmd_read)

    # write
    sp = sub.add_parser("write", help="write one or more tags")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--set",
        action="append",
        type=split_kv,
        metavar="TAG=VALUE",
        help="repeatable; e.g. --set Artist=Alice --set 'Copyright=(c) 2026'",
    )
    sp.add_argument(
        "--preserve-mtime", action="store_true", help="pass -P to preserve file mtime"
    )
    sp.set_defaults(func=cmd_write)

    # strip
    sp = sub.add_parser("strip", help="strip metadata")
    sp.add_argument("--input", required=True)
    sp.add_argument("--gps-only", action="store_true")
    sp.add_argument("--exif-only", action="store_true")
    sp.add_argument("--preserve-mtime", action="store_true")
    sp.set_defaults(func=cmd_strip)

    # copy
    sp = sub.add_parser("copy", help="copy tags between files")
    sp.add_argument("--src", required=True)
    sp.add_argument("--dst", required=True)
    sp.add_argument("--tags", nargs="*", help="specific tag names (default: all:all)")
    sp.add_argument("--preserve-mtime", action="store_true")
    sp.set_defaults(func=cmd_copy)

    # shift-dates
    sp = sub.add_parser("shift-dates", help="shift AllDates by Y:M:D h:m:s")
    sp.add_argument("--input", required=True, help="file or directory")
    sp.add_argument(
        "--delta",
        required=True,
        help='ExifTool delta, e.g. "0:0:0 1:0:0" (+1h) or "-0:0:1 0:0:0" (-1 day)',
    )
    sp.add_argument("--preserve-mtime", action="store_true")
    sp.set_defaults(func=cmd_shift_dates)

    # gps
    sp = sub.add_parser("gps", help="set GPSLatitude/GPSLongitude with Ref tags")
    sp.add_argument("--input", required=True)
    sp.add_argument("--lat", type=float, required=True)
    sp.add_argument("--lon", type=float, required=True)
    sp.add_argument("--preserve-mtime", action="store_true")
    sp.set_defaults(func=cmd_gps)

    # extract-thumbnail
    sp = sub.add_parser("extract-thumbnail", help="extract the embedded ThumbnailImage")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_extract_thumbnail)

    # batch-rename
    sp = sub.add_parser(
        "batch-rename", help="rename files in a directory using a date tag"
    )
    sp.add_argument("--dir", required=True)
    sp.add_argument(
        "--pattern",
        default="DateTimeOriginal",
        help="source tag (default: DateTimeOriginal)",
    )
    sp.add_argument(
        "--format",
        default="%Y%m%d_%H%M%S.%%le",
        help="strftime format; %%le = lowercase extension",
    )
    sp.set_defaults(func=cmd_batch_rename)

    # sidecar
    sp = sub.add_parser("sidecar", help="create an XMP sidecar from a source file")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True, help="destination .xmp path")
    sp.set_defaults(func=cmd_sidecar)

    return p


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
