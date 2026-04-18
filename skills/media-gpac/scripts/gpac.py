#!/usr/bin/env python3
"""GPAC / MP4Box wrapper — ISO-BMFF authoring and diagnostics.

Subcommands:
  check          MP4Box + gpac versions
  info           MP4Box -info (human summary)
  diso           MP4Box -diso (full box-tree XML dump)
  extract-track  MP4Box -raw TID (extract ES)
  fragment       MP4Box -frag (fragment MP4)
  dash           MP4Box -dash (DASH/CMAF package)
  encrypt        MP4Box -crypt (CENC ClearKey encrypt)
  decrypt        MP4Box -decrypt (CENC decrypt)
  remove-track   MP4Box -rem
  set-lang       MP4Box -lang TID=LANG
  split-time     MP4Box -splitx

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------- helpers ----------


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(_shquote(c) for c in cmd)
    if verbose or dry_run:
        print(f"$ {pretty}", file=sys.stderr)
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def _shquote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'$`\\|&;<>()*?[]{}"):
        return "'" + s.replace("'", "'\"'\"'") + "'"
    return s


def _require(tool: str) -> str:
    path = _which(tool)
    if not path:
        sys.exit(f"error: {tool} not found in PATH — install GPAC (brew install gpac)")
    return path


def _hex_clean(h: str) -> str:
    """Normalize hex: strip 0x prefix, lowercase, validate."""
    h = h.strip()
    if h.lower().startswith("0x"):
        h = h[2:]
    if not all(c in "0123456789abcdefABCDEF" for c in h):
        sys.exit(f"error: not a hex string: {h!r}")
    return h.lower()


def _hex_with_0x(h: str) -> str:
    return "0x" + _hex_clean(h)


# ---------- subcommands ----------


def cmd_check(args: argparse.Namespace) -> int:
    mp4box = _which("MP4Box")
    gpac = _which("gpac")
    print(f"MP4Box: {mp4box or 'not found'}")
    print(f"gpac:   {gpac or 'not found'}")
    if mp4box:
        subprocess.run([mp4box, "-version"])
    if gpac:
        subprocess.run([gpac, "-version"])
    return 0 if mp4box else 1


def cmd_info(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    return _run(
        [mp4box, "-info", args.input], dry_run=args.dry_run, verbose=args.verbose
    )


def cmd_diso(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    # -diso writes <input>_info.xml by default; we rename to args.output
    inp = Path(args.input)
    out = Path(args.output)
    default_out = inp.with_name(inp.stem + "_info.xml")
    rc = _run([mp4box, "-diso", str(inp)], dry_run=args.dry_run, verbose=args.verbose)
    if rc != 0 or args.dry_run:
        return rc
    if default_out != out:
        if out.exists():
            out.unlink()
        shutil.move(str(default_out), str(out))
    if args.verbose:
        print(f"wrote {out}", file=sys.stderr)
    return 0


def cmd_extract_track(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    # -raw TID writes <input>_trackTID.<ext>; rename to args.output
    inp = Path(args.input)
    rc = _run(
        [mp4box, "-raw", str(args.track), str(inp)],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0 or args.dry_run:
        return rc
    # find default output: <stem>_track<N>.* in inp's dir
    parent = inp.parent
    matches = sorted(parent.glob(f"{inp.stem}_track{args.track}.*"))
    if not matches:
        print(
            f"warning: MP4Box ran but no extracted file matched {inp.stem}_track{args.track}.*",
            file=sys.stderr,
        )
        return 1
    src = matches[0]
    dst = Path(args.output)
    if dst.exists():
        dst.unlink()
    shutil.move(str(src), str(dst))
    if args.verbose:
        print(f"wrote {dst}", file=sys.stderr)
    return 0


def cmd_fragment(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    cmd = [mp4box, "-frag", str(args.fragment_ms), "-out", args.output, args.input]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_dash(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    outdir = Path(args.outdir)
    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)
    manifest = outdir / "manifest.mpd"
    cmd = [
        mp4box,
        "-dash",
        str(args.segment_ms),
        "-frag",
        str(args.segment_ms),
        "-rap",
        "-segment-name",
        "seg_$RepresentationID$_$Number$",
        "-dash-profile",
        args.profile,
        "-out",
        str(manifest),
        args.input,
    ]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def _write_drm_xml(track_id: int, key_id: str, key: str, iv: str | None) -> Path:
    kid = _hex_with_0x(key_id)
    k = _hex_with_0x(key)
    iv_hex = _hex_with_0x(iv) if iv else "0x0123456789abcdef"
    iv_size = 8 if len(_hex_clean(iv_hex)) <= 16 else 16
    xml = f"""<GPACDRM>
  <CrypTrack trackID="{track_id}" IsEncrypted="1" IV_size="{iv_size}"
             first_IV="{iv_hex}" saiSavedBox="senc">
    <key KID="{kid}" value="{k}"/>
  </CrypTrack>
</GPACDRM>
"""
    fd, path = tempfile.mkstemp(prefix="gpac_drm_", suffix=".xml")
    with os.fdopen(fd, "w") as f:
        f.write(xml)
    return Path(path)


def cmd_encrypt(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    drm = _write_drm_xml(args.track, args.key_id, args.key, args.iv)
    try:
        if args.verbose:
            print(f"DRM XML: {drm}", file=sys.stderr)
        cmd = [mp4box, "-crypt", str(drm), "-out", args.output, args.input]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        if not args.keep_drm_xml:
            try:
                drm.unlink()
            except OSError:
                pass


def cmd_decrypt(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    drm = _write_drm_xml(args.track, args.key_id, args.key, args.iv)
    try:
        if args.verbose:
            print(f"DRM XML: {drm}", file=sys.stderr)
        cmd = [mp4box, "-decrypt", str(drm), "-out", args.output, args.input]
        return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        if not args.keep_drm_xml:
            try:
                drm.unlink()
            except OSError:
                pass


def cmd_remove_track(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    # Copy input -> output first, then edit in place, so input is preserved.
    if not args.dry_run:
        shutil.copy2(args.input, args.output)
    cmd = [mp4box, "-rem", str(args.track), args.output]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_set_lang(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    if not args.dry_run and args.output and args.output != args.input:
        shutil.copy2(args.input, args.output)
    target = args.output or args.input
    cmd = [mp4box, "-lang", f"{args.track}={args.lang}", target]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_split_time(args: argparse.Namespace) -> int:
    mp4box = _require("MP4Box")
    # -splitx START:END uses "HH:MM:SS:HH:MM:SS" composite form
    rng = f"{args.start}:{args.end}"
    cmd = [mp4box, "-splitx", rng, "-out", args.output_pattern, args.input]
    return _run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gpac.py",
        description="MP4Box / GPAC wrapper for ISO-BMFF authoring.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the command, don't run it"
    )
    p.add_argument(
        "--verbose", action="store_true", help="echo the command before running"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="MP4Box / gpac version")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("info", help="MP4Box -info")
    sp.add_argument("--input", "-i", required=True)
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("diso", help="MP4Box -diso (full box XML dump)")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True, help="output XML path")
    sp.set_defaults(func=cmd_diso)

    sp = sub.add_parser("extract-track", help="MP4Box -raw TID")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--track", type=int, required=True, help="1-based track ID")
    sp.add_argument("--output", "-o", required=True, help="raw ES output file")
    sp.set_defaults(func=cmd_extract_track)

    sp = sub.add_parser("fragment", help="MP4Box -frag (fragment MP4)")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--fragment-ms", type=int, default=4000)
    sp.set_defaults(func=cmd_fragment)

    sp = sub.add_parser("dash", help="MP4Box -dash (DASH/CMAF package)")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--outdir", "-d", required=True)
    sp.add_argument("--segment-ms", type=int, default=4000)
    sp.add_argument(
        "--profile", choices=["live", "onDemand", "main", "full"], default="live"
    )
    sp.set_defaults(func=cmd_dash)

    sp = sub.add_parser("encrypt", help="CENC encrypt (ClearKey)")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--track", type=int, default=1)
    sp.add_argument("--key-id", required=True, help="16-byte hex (KID)")
    sp.add_argument("--key", required=True, help="16-byte hex (content key)")
    sp.add_argument("--iv", default=None, help="first IV hex (8 or 16 bytes)")
    sp.add_argument(
        "--keep-drm-xml",
        action="store_true",
        help="keep generated drm.xml for inspection",
    )
    sp.set_defaults(func=cmd_encrypt)

    sp = sub.add_parser("decrypt", help="CENC decrypt")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--track", type=int, default=1)
    sp.add_argument("--key-id", required=True)
    sp.add_argument("--key", required=True)
    sp.add_argument("--iv", default=None)
    sp.add_argument("--keep-drm-xml", action="store_true")
    sp.set_defaults(func=cmd_decrypt)

    sp = sub.add_parser("remove-track", help="MP4Box -rem TID")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--output", "-o", required=True)
    sp.add_argument("--track", type=int, required=True)
    sp.set_defaults(func=cmd_remove_track)

    sp = sub.add_parser("set-lang", help="MP4Box -lang TID=LANG")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument(
        "--output",
        "-o",
        default=None,
        help="output path (if omitted, edits input in place)",
    )
    sp.add_argument("--track", type=int, required=True)
    sp.add_argument("--lang", required=True, help="ISO 639-2 3-letter code (e.g. jpn)")
    sp.set_defaults(func=cmd_set_lang)

    sp = sub.add_parser("split-time", help="MP4Box -splitx HH:MM:SS:HH:MM:SS")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument(
        "--output-pattern",
        "-o",
        required=True,
        help="output base name (MP4Box derives segment names)",
    )
    sp.add_argument("--start", required=True, help="HH:MM:SS")
    sp.add_argument("--end", required=True, help="HH:MM:SS")
    sp.set_defaults(func=cmd_split_time)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
