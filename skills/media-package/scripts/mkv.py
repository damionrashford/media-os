#!/usr/bin/env python3
"""
mkv.py — thin argparse wrapper around MKVToolNix (mkvmerge, mkvextract,
mkvpropedit, mkvinfo). Non-interactive, stdlib only.

Subcommands:
    identify            mkvmerge -J (JSON)
    merge               mkvmerge -o OUT INPUTS...
    split-time          mkvmerge -o OUT --split timestamps:T1,T2,...
    split-size          mkvmerge -o OUT --split size:N[K|M|G]
    extract-tracks      mkvextract tracks IN ID:OUT ...
    extract-chapters    mkvextract chapters IN [--simple]
    extract-attachments mkvextract attachments IN (dumps all to --outdir)
    edit                mkvpropedit IN --edit SELECTOR --set K=V ...
    default-flag        mkvpropedit IN --edit track:SEL --set flag-default=0|1
    add-attachment      mkvpropedit IN --add-attachment FILE --attachment-mime-type MIME
    replace-chapters    mkvpropedit IN --chapters CHAP.xml

Global flags:
    --dry-run           print command, do not execute
    --verbose           echo command to stderr before running

All non-zero returns from underlying tools propagate.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence


def _require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.stderr.write(f"error: '{tool}' not found in PATH. Install MKVToolNix.\n")
        sys.exit(127)
    return path


def _run(
    cmd: Sequence[str], dry_run: bool, verbose: bool, capture: bool = False
) -> subprocess.CompletedProcess:
    if verbose or dry_run:
        sys.stderr.write("+ " + " ".join(shlex.quote(c) for c in cmd) + "\n")
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


# ------------------------- subcommand handlers -------------------------


def cmd_identify(args: argparse.Namespace) -> int:
    mkvmerge = _require("mkvmerge")
    cmd = [mkvmerge, "-J", args.input]
    res = _run(cmd, args.dry_run, args.verbose, capture=True)
    if args.dry_run:
        return 0
    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode
    # Pretty-print JSON for humans
    try:
        parsed = json.loads(res.stdout)
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        sys.stdout.write(res.stdout)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    mkvmerge = _require("mkvmerge")
    cmd: List[str] = [mkvmerge, "-o", args.output]
    if args.title:
        cmd += ["--title", args.title]

    langs: Optional[List[str]] = None
    if args.languages:
        langs = [x.strip() for x in args.languages.split(",")]
        if len(langs) != len(args.inputs):
            sys.stderr.write(
                f"error: --languages count ({len(langs)}) must equal --inputs count "
                f"({len(args.inputs)}).\n"
            )
            return 2

    for idx, inp in enumerate(args.inputs):
        if langs is not None:
            # Apply to track 0 of each source file (safe default for single-track raw
            # essence files; inputs with multiple tracks should use mkvmerge
            # directly with per-track selectors).
            cmd += ["--language", f"0:{langs[idx]}"]
        cmd.append(inp)

    res = _run(cmd, args.dry_run, args.verbose)
    return res.returncode


def cmd_split_time(args: argparse.Namespace) -> int:
    mkvmerge = _require("mkvmerge")
    times = args.times.strip()
    cmd = [
        mkvmerge,
        "-o",
        args.output_pattern,
        "--split",
        f"timestamps:{times}",
        args.input,
    ]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_split_size(args: argparse.Namespace) -> int:
    mkvmerge = _require("mkvmerge")
    cmd = [
        mkvmerge,
        "-o",
        args.output_pattern,
        "--split",
        f"size:{args.size}",
        args.input,
    ]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_extract_tracks(args: argparse.Namespace) -> int:
    mkvextract = _require("mkvextract")
    pairs = [p.strip() for p in args.tracks.split(",") if p.strip()]
    for p in pairs:
        if ":" not in p:
            sys.stderr.write(f"error: --tracks entry '{p}' must be ID:OUT\n")
            return 2
    cmd = [mkvextract, "tracks", args.input, *pairs]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_extract_chapters(args: argparse.Namespace) -> int:
    mkvextract = _require("mkvextract")
    cmd = [mkvextract, "chapters", args.input]
    if args.simple:
        cmd.append("--simple")
    if args.dry_run:
        _run(cmd + [">", args.output], True, args.verbose)
        return 0
    if args.verbose:
        sys.stderr.write(
            "+ "
            + " ".join(shlex.quote(c) for c in cmd)
            + " > "
            + shlex.quote(args.output)
            + "\n"
        )
    with open(args.output, "w", encoding="utf-8") as fh:
        res = subprocess.run(cmd, check=False, text=True, stdout=fh)
    return res.returncode


def cmd_extract_attachments(args: argparse.Namespace) -> int:
    mkvmerge = _require("mkvmerge")
    mkvextract = _require("mkvextract")
    # Enumerate attachments via mkvmerge -J
    id_res = _run(
        [mkvmerge, "-J", args.input], args.dry_run, args.verbose, capture=True
    )
    if args.dry_run:
        sys.stderr.write(
            "(dry-run) cannot enumerate attachments without running "
            "mkvmerge; would extract all into "
            f"{args.outdir}\n"
        )
        return 0
    if id_res.returncode != 0:
        sys.stderr.write(id_res.stderr or "")
        return id_res.returncode

    data = json.loads(id_res.stdout)
    attachments = data.get("attachments", []) or []
    if not attachments:
        sys.stderr.write("no attachments in input\n")
        return 0

    os.makedirs(args.outdir, exist_ok=True)
    pairs = []
    for att in attachments:
        att_id = att.get("id")
        fname = att.get("file_name") or f"attachment_{att_id}"
        out = os.path.join(args.outdir, fname)
        pairs.append(f"{att_id}:{out}")
    cmd = [mkvextract, "attachments", args.input, *pairs]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_edit(args: argparse.Namespace) -> int:
    mkvpropedit = _require("mkvpropedit")
    if not args.set:
        sys.stderr.write("error: at least one --set K=V required\n")
        return 2
    cmd = [mkvpropedit, args.input, "--edit", args.track]
    for kv in args.set:
        if "=" not in kv:
            sys.stderr.write(f"error: --set value '{kv}' must be K=V\n")
            return 2
        cmd += ["--set", kv]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_default_flag(args: argparse.Namespace) -> int:
    mkvpropedit = _require("mkvpropedit")
    if args.value not in ("0", "1"):
        sys.stderr.write("error: --value must be 0 or 1\n")
        return 2
    selector = args.track
    if not selector.startswith("track:"):
        selector = f"track:{selector}"
    cmd = [
        mkvpropedit,
        args.input,
        "--edit",
        selector,
        "--set",
        f"flag-default={args.value}",
    ]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_add_attachment(args: argparse.Namespace) -> int:
    mkvpropedit = _require("mkvpropedit")
    cmd = [
        mkvpropedit,
        args.input,
        "--add-attachment",
        args.file,
    ]
    if args.mime:
        # --attachment-mime-type must come BEFORE --add-attachment in mkvpropedit.
        # Rebuild with correct order.
        cmd = [
            mkvpropedit,
            args.input,
            "--attachment-mime-type",
            args.mime,
            "--add-attachment",
            args.file,
        ]
    return _run(cmd, args.dry_run, args.verbose).returncode


def cmd_replace_chapters(args: argparse.Namespace) -> int:
    mkvpropedit = _require("mkvpropedit")
    cmd = [mkvpropedit, args.input, "--chapters", args.chapters_xml]
    return _run(cmd, args.dry_run, args.verbose).returncode


# ------------------------- argparse wiring -------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mkv.py",
        description="Thin wrapper around MKVToolNix CLI tools.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the command without executing"
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="echo the command to stderr before execution",
    )

    sub = p.add_subparsers(dest="subcommand", required=True)

    sp = sub.add_parser("identify", help="mkvmerge -J (JSON info)")
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_identify)

    sp = sub.add_parser("merge", help="merge inputs into one MKV")
    sp.add_argument("--output", required=True)
    sp.add_argument("--inputs", required=True, nargs="+")
    sp.add_argument("--title")
    sp.add_argument(
        "--languages",
        help="comma-separated ISO 639-2 or BCP-47 codes, one per input "
        "(applied to track 0 of each input)",
    )
    sp.set_defaults(func=cmd_merge)

    sp = sub.add_parser("split-time", help="split by absolute timestamps")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--output-pattern",
        required=True,
        help="e.g. part.mkv -> part-001.mkv, part-002.mkv, ...",
    )
    sp.add_argument("--times", required=True, help="comma-separated HH:MM:SS[.ms] list")
    sp.set_defaults(func=cmd_split_time)

    sp = sub.add_parser("split-size", help="split by output size")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output-pattern", required=True)
    sp.add_argument("--size", required=True, help="e.g. 500M, 4G, 700K")
    sp.set_defaults(func=cmd_split_size)

    sp = sub.add_parser("extract-tracks", help="mkvextract tracks IN ID:OUT,ID:OUT,...")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--tracks",
        required=True,
        help="comma-separated ID:OUTPATH pairs " "(e.g. 0:v.h264,1:a.ac3,2:s.srt)",
    )
    sp.set_defaults(func=cmd_extract_tracks)

    sp = sub.add_parser("extract-chapters", help="dump chapters to XML/OGM")
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument(
        "--simple", action="store_true", help="use --simple for OGM-style text output"
    )
    sp.set_defaults(func=cmd_extract_chapters)

    sp = sub.add_parser(
        "extract-attachments", help="extract all attachments to a directory"
    )
    sp.add_argument("--input", required=True)
    sp.add_argument("--outdir", required=True)
    sp.set_defaults(func=cmd_extract_attachments)

    sp = sub.add_parser("edit", help="mkvpropedit --edit SELECTOR --set K=V ...")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--track", required=True, help="selector, e.g. 'track:v1', 'track:a2', 'info'"
    )
    sp.add_argument("--set", action="append", default=[], help="K=V, repeatable")
    sp.set_defaults(func=cmd_edit)

    sp = sub.add_parser("default-flag", help="set flag-default on a track selector")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--track",
        required=True,
        help="selector after 'track:' (e.g. v1, a2, s1) or full " "'track:v1'",
    )
    sp.add_argument("--value", required=True, choices=["0", "1"])
    sp.set_defaults(func=cmd_default_flag)

    sp = sub.add_parser("add-attachment", help="attach a file in place")
    sp.add_argument("--input", required=True)
    sp.add_argument("--file", required=True)
    sp.add_argument("--mime", help="MIME type, e.g. application/x-truetype-font")
    sp.set_defaults(func=cmd_add_attachment)

    sp = sub.add_parser("replace-chapters", help="replace chapters from XML")
    sp.add_argument("--input", required=True)
    sp.add_argument("--chapters-xml", required=True)
    sp.set_defaults(func=cmd_replace_chapters)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
