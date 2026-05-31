#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""dovi.py — Wrapper around dovi_tool for Dolby Vision RPU authoring.

Non-interactive. Prints every real `dovi_tool` / `ffmpeg` / `mkvmerge` /
`MP4Box` command to stderr before running. Stdlib-only Python 3.

Usage:
    dovi.py info --input FILE [--summary] [--frame N]
    dovi.py extract-rpu --input HEVC --output RPU
    dovi.py inject-rpu --input HEVC --rpu-in RPU --output HEVC
    dovi.py editor --input RPU --json EDIT.json --output RPU
    dovi.py export --input RPU --output JSON
    dovi.py plot --input RPU --output PNG
    dovi.py convert --input HEVC --output HEVC --mode 2
    dovi.py demux --input HEVC --bl-out BL --el-out EL
    dovi.py mux --bl BL --el EL --output HEVC
    dovi.py remove --input HEVC --output HEVC
    dovi.py generate --input XML_OR_JSON --output RPU
    dovi.py pipeline --input MKV/MP4 --output MKV/MP4
        [--edit-json EDIT.json] [--convert-profile-7-to-81]
        [--strip-dv] [--info-only]

Global flags: --dry-run, --verbose.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry_run: bool, stdin=None) -> int:
    echo(cmd)
    if dry_run:
        return 0
    if shutil.which(cmd[0]) is None:
        print(f"error: {cmd[0]} not on PATH", file=sys.stderr)
        return 127
    try:
        return subprocess.run(cmd, check=False, stdin=stdin).returncode
    except KeyboardInterrupt:
        return 130


def cmd_info(args: argparse.Namespace) -> int:
    cmd = ["dovi_tool", "info", "-i", str(args.input)]
    if args.summary:
        cmd.append("--summary")
    if args.frame is not None:
        cmd += ["-f", str(args.frame)]
    return run(cmd, dry_run=args.dry_run)


def cmd_extract_rpu(args: argparse.Namespace) -> int:
    cmd = ["dovi_tool", "extract-rpu", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_inject_rpu(args: argparse.Namespace) -> int:
    cmd = [
        "dovi_tool",
        "inject-rpu",
        "-i",
        str(args.input),
        "--rpu-in",
        str(args.rpu_in),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_editor(args: argparse.Namespace) -> int:
    cmd = [
        "dovi_tool",
        "editor",
        "-i",
        str(args.input),
        "-j",
        str(args.json),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_export(args: argparse.Namespace) -> int:
    cmd = ["dovi_tool", "export", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_plot(args: argparse.Namespace) -> int:
    cmd = ["dovi_tool", "plot", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_convert(args: argparse.Namespace) -> int:
    cmd = [
        "dovi_tool",
        "--mode",
        str(args.mode),
        "convert",
        "-i",
        str(args.input),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_demux(args: argparse.Namespace) -> int:
    cmd = [
        "dovi_tool",
        "demux",
        "-i",
        str(args.input),
        "--bl-out",
        str(args.bl_out),
        "--el-out",
        str(args.el_out),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_mux(args: argparse.Namespace) -> int:
    cmd = [
        "dovi_tool",
        "mux",
        "--bl",
        str(args.bl),
        "--el",
        str(args.el),
        "-o",
        str(args.output),
    ]
    return run(cmd, dry_run=args.dry_run)


def cmd_remove(args: argparse.Namespace) -> int:
    cmd = ["dovi_tool", "remove", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def cmd_generate(args: argparse.Namespace) -> int:
    # dovi_tool generate takes --xml or --hdr10plus-json etc depending on source
    cmd = ["dovi_tool", "generate", "-i", str(args.input), "-o", str(args.output)]
    return run(cmd, dry_run=args.dry_run)


def _bsf_to_annexb(src: Path, dst: Path, *, dry_run: bool, verbose: bool) -> int:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning" if not verbose else "info",
        "-y",
        "-i",
        str(src),
        "-c:v",
        "copy",
        "-bsf:v",
        "hevc_mp4toannexb",
        "-an",
        "-sn",
        "-f",
        "hevc",
        str(dst),
    ]
    return run(cmd, dry_run=dry_run)


def _remux(hevc: Path, out: Path, *, dry_run: bool) -> int:
    if out.suffix.lower() == ".mkv":
        cmd = ["mkvmerge", "-o", str(out), str(hevc)]
    elif out.suffix.lower() in (".mp4", ".m4v"):
        cmd = ["MP4Box", "-add", f"{hevc}:dvhe=hvcC", str(out)]
    else:
        print(
            f"error: output extension {out.suffix!r} not supported; use .mkv or .mp4",
            file=sys.stderr,
        )
        return 2
    return run(cmd, dry_run=dry_run)


def cmd_pipeline(args: argparse.Namespace) -> int:
    in_path: Path = args.input
    out_path: Path = args.output
    if not in_path.exists() and not args.dry_run:
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="dovi_pipeline_"))
    annexb = tmp / "input.hevc"
    rpu = tmp / "rpu.bin"
    rpu_edited = tmp / "rpu-edited.bin"
    converted = tmp / "converted.hevc"
    injected = tmp / "injected.hevc"

    # Step 1: HEVC Annex-B
    rc = _bsf_to_annexb(in_path, annexb, dry_run=args.dry_run, verbose=args.verbose)
    if rc:
        return rc

    if args.info_only:
        rc = run(
            ["dovi_tool", "info", "--summary", "-i", str(annexb)],
            dry_run=args.dry_run,
        )
        return rc

    if args.strip_dv:
        stripped = tmp / "stripped.hevc"
        rc = run(
            [
                "dovi_tool",
                "remove",
                "-i",
                str(annexb),
                "-o",
                str(stripped),
            ],
            dry_run=args.dry_run,
        )
        if rc:
            return rc
        return _remux(stripped, out_path, dry_run=args.dry_run)

    # Step 2: extract RPU
    rc = run(
        ["dovi_tool", "extract-rpu", "-i", str(annexb), "-o", str(rpu)],
        dry_run=args.dry_run,
    )
    if rc:
        return rc

    # Step 3: optional edit
    rpu_for_inject = rpu
    if args.edit_json:
        rc = run(
            [
                "dovi_tool",
                "editor",
                "-i",
                str(rpu),
                "-j",
                str(args.edit_json),
                "-o",
                str(rpu_edited),
            ],
            dry_run=args.dry_run,
        )
        if rc:
            return rc
        rpu_for_inject = rpu_edited

    # Step 4: optional convert
    source_for_inject = annexb
    if args.convert_profile_7_to_81:
        rc = run(
            [
                "dovi_tool",
                "--mode",
                "2",
                "convert",
                "-i",
                str(annexb),
                "-o",
                str(converted),
            ],
            dry_run=args.dry_run,
        )
        if rc:
            return rc
        source_for_inject = converted

    # Step 5: inject RPU
    rc = run(
        [
            "dovi_tool",
            "inject-rpu",
            "-i",
            str(source_for_inject),
            "--rpu-in",
            str(rpu_for_inject),
            "-o",
            str(injected),
        ],
        dry_run=args.dry_run,
    )
    if rc:
        return rc

    # Step 6: remux
    return _remux(injected, out_path, dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Wrapper around dovi_tool. Non-interactive; prints every real "
            "command to stderr before running."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("info", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--summary", action="store_true")
    s.add_argument("--frame", type=int, default=None)
    s.set_defaults(fn=cmd_info)

    s = sub.add_parser("extract-rpu", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_extract_rpu)

    s = sub.add_parser("inject-rpu", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--rpu-in", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_inject_rpu)

    s = sub.add_parser("editor", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--json", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_editor)

    s = sub.add_parser("export", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("plot", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_plot)

    s = sub.add_parser("convert", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.add_argument("--mode", type=int, default=2)
    s.set_defaults(fn=cmd_convert)

    s = sub.add_parser("demux", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--bl-out", required=True, type=Path)
    s.add_argument("--el-out", required=True, type=Path)
    s.set_defaults(fn=cmd_demux)

    s = sub.add_parser("mux", parents=[parent])
    s.add_argument("--bl", required=True, type=Path)
    s.add_argument("--el", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_mux)

    s = sub.add_parser("remove", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_remove)

    s = sub.add_parser("generate", parents=[parent])
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.set_defaults(fn=cmd_generate)

    s = sub.add_parser("pipeline", parents=[parent], help="End-to-end MKV/MP4 pipeline")
    s.add_argument("--input", required=True, type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.add_argument("--edit-json", type=Path, default=None)
    s.add_argument("--convert-profile-7-to-81", action="store_true")
    s.add_argument("--strip-dv", action="store_true")
    s.add_argument("--info-only", action="store_true")
    s.set_defaults(fn=cmd_pipeline)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
