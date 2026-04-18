#!/usr/bin/env python3
"""ffmpeg-drm helper: key/IV generation, HLS AES-128 packaging, DASH CENC
packaging, and single-segment decryption.

Stdlib only. Non-interactive. Never logs key material unless --verbose.

Subcommands:
  gen-key          write 16 random bytes to a file
  gen-iv           print a 32-hex-char IV
  hls-aes128       build keyinfo + encrypt HLS VOD
  dash-cenc        encrypt to DASH CENC (ClearKey-compatible)
  decrypt-segment  openssl aes-128-cbc -d on one .ts segment

Examples:
  drm.py gen-key --output enc.key
  drm.py gen-iv
  drm.py hls-aes128 --input in.mp4 --outdir out \
      --key-url https://cdn.example.com/keys/enc.key --key enc.key
  drm.py dash-cenc --input in.mp4 --outdir out \
      --key abcdef0123456789abcdef0123456789 \
      --kid 11223344556677880011223344556677
  drm.py decrypt-segment --input seg.ts --key enc.key \
      --iv abcdef0123456789abcdef0123456789 --output plain.ts
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def log(msg: str, *, verbose: bool = False, force: bool = False) -> None:
    if force or verbose:
        print(msg, file=sys.stderr)


def redact(s: str, *, verbose: bool) -> str:
    if verbose:
        return s
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "..." + s[-2:]


def require_ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        sys.exit("error: ffmpeg not found on PATH")
    return ff


def require_openssl() -> str | None:
    return shutil.which("openssl")


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    # Never print raw key hex from argv in non-verbose mode.
    printable = " ".join(cmd) if verbose else _scrub_cmd(cmd)
    log(f"+ {printable}", verbose=True, force=True)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _scrub_cmd(cmd: list[str]) -> str:
    out: list[str] = []
    scrub_next = False
    sensitive = {
        "-hls_enc_key",
        "-hls_enc_iv",
        "-encryption_key",
        "-encryption_kid",
    }
    for tok in cmd:
        if scrub_next:
            out.append("<redacted>")
            scrub_next = False
            continue
        out.append(tok)
        if tok in sensitive:
            scrub_next = True
    return " ".join(out)


# ---------------------------------------------------------------------------
# gen-key / gen-iv
# ---------------------------------------------------------------------------
def cmd_gen_key(args: argparse.Namespace) -> int:
    path = Path(args.output)
    if path.exists() and not args.force:
        sys.exit(f"error: {path} exists (use --force to overwrite)")
    key = secrets.token_bytes(16)
    if args.dry_run:
        log(f"dry-run: would write 16 bytes to {path}", force=True)
        return 0
    path.write_bytes(key)
    os.chmod(path, 0o600)
    log(f"wrote 16-byte key -> {path}", force=True)
    if args.verbose:
        log(f"  key hex: {key.hex()}", verbose=True)
    return 0


def cmd_gen_iv(args: argparse.Namespace) -> int:
    iv = secrets.token_hex(16)  # 32 hex chars = 16 bytes
    print(iv)
    return 0


# ---------------------------------------------------------------------------
# hls-aes128
# ---------------------------------------------------------------------------
def cmd_hls_aes128(args: argparse.Namespace) -> int:
    ffmpeg = require_ffmpeg()
    key_path = Path(args.key).resolve()
    if not key_path.is_file():
        sys.exit(f"error: key file not found: {key_path}")
    if key_path.stat().st_size != 16:
        sys.exit(
            f"error: key file must be exactly 16 bytes "
            f"(got {key_path.stat().st_size})"
        )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    iv = args.iv or secrets.token_hex(16)
    if not HEX32_RE.match(iv):
        sys.exit("error: --iv must be 32 hex chars (16 bytes), no 0x prefix")

    keyinfo = outdir / "enc.keyinfo"
    keyinfo_text = f"{args.key_url}\n{key_path}\n{iv}\n"
    if args.dry_run:
        log(f"dry-run: would write keyinfo -> {keyinfo}", force=True)
    else:
        keyinfo.write_text(keyinfo_text)
        os.chmod(keyinfo, 0o600)
    log(
        f"keyinfo: url={args.key_url} key={key_path} iv={redact(iv, verbose=args.verbose)}",
        force=True,
    )

    playlist = outdir / "out.m3u8"
    seg_pattern = str(outdir / "seg_%03d.ts")

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.input),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-f",
        "hls",
        "-hls_time",
        str(args.segments),
        "-hls_playlist_type",
        "vod",
        "-hls_key_info_file",
        str(keyinfo),
        "-hls_segment_filename",
        seg_pattern,
    ]
    if args.rotate:
        cmd += ["-hls_flags", "periodic_rekey"]
    cmd.append(str(playlist))

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# dash-cenc
# ---------------------------------------------------------------------------
def cmd_dash_cenc(args: argparse.Namespace) -> int:
    ffmpeg = require_ffmpeg()
    if not HEX32_RE.match(args.key):
        sys.exit("error: --key must be 32 hex chars (16 bytes)")
    if not HEX32_RE.match(args.kid):
        sys.exit("error: --kid must be 32 hex chars (16 bytes)")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = outdir / "manifest.mpd"

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.input),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-encryption_scheme",
        args.scheme,
        "-encryption_key",
        args.key,
        "-encryption_kid",
        args.kid,
        "-f",
        "dash",
        "-use_template",
        "1",
        "-use_timeline",
        "1",
        "-init_seg_name",
        "init-$RepresentationID$.m4s",
        "-media_seg_name",
        "chunk-$RepresentationID$-$Number%05d$.m4s",
        str(manifest),
    ]
    log(
        f"dash-cenc scheme={args.scheme} "
        f"key={redact(args.key, verbose=args.verbose)} "
        f"kid={redact(args.kid, verbose=args.verbose)}",
        force=True,
    )
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------------------------------------------------------------------------
# decrypt-segment
# ---------------------------------------------------------------------------
def cmd_decrypt_segment(args: argparse.Namespace) -> int:
    openssl = require_openssl()
    if not openssl:
        log(
            "warning: openssl not found on PATH; cannot decrypt",
            force=True,
        )
        return 2

    key_path = Path(args.key)
    if not key_path.is_file():
        sys.exit(f"error: key file not found: {key_path}")
    if key_path.stat().st_size != 16:
        sys.exit("error: key file must be 16 bytes")
    if not HEX32_RE.match(args.iv):
        sys.exit("error: --iv must be 32 hex chars")

    key_hex = key_path.read_bytes().hex()
    cmd = [
        openssl,
        "aes-128-cbc",
        "-d",
        "-K",
        key_hex,
        "-iv",
        args.iv,
        "-in",
        str(args.input),
        "-out",
        str(args.output),
    ]
    # Always scrub key_hex for the echoed command.
    printable = [
        openssl,
        "aes-128-cbc",
        "-d",
        "-K",
        "<redacted>",
        "-iv",
        "<redacted>" if not args.verbose else args.iv,
        "-in",
        str(args.input),
        "-out",
        str(args.output),
    ]
    log(f"+ {' '.join(printable)}", force=True)
    if args.dry_run:
        return 0
    return subprocess.call(cmd)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="drm.py",
        description="ffmpeg DRM helper (HLS AES-128, DASH CENC, decrypt)",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print commands without executing"
    )
    p.add_argument(
        "--verbose", action="store_true", help="print full commands and key material"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen-key", help="generate a 16-byte AES key file")
    g.add_argument("--output", required=True)
    g.add_argument("--force", action="store_true")
    g.set_defaults(func=cmd_gen_key)

    iv = sub.add_parser("gen-iv", help="print a 32-hex-char IV")
    iv.set_defaults(func=cmd_gen_iv)

    h = sub.add_parser("hls-aes128", help="HLS AES-128 VOD packaging")
    h.add_argument("--input", required=True)
    h.add_argument("--outdir", required=True)
    h.add_argument(
        "--key-url", required=True, help="URL the player will fetch (line 1 of keyinfo)"
    )
    h.add_argument(
        "--key", required=True, help="path to 16-byte key file (line 2 of keyinfo)"
    )
    h.add_argument("--iv", default=None, help="32-hex IV; random if omitted")
    h.add_argument(
        "--segments", type=int, default=6, help="hls_time in seconds (default 6)"
    )
    h.add_argument(
        "--rotate", action="store_true", help="enable -hls_flags periodic_rekey"
    )
    h.set_defaults(func=cmd_hls_aes128)

    d = sub.add_parser("dash-cenc", help="DASH Common Encryption packaging")
    d.add_argument("--input", required=True)
    d.add_argument("--outdir", required=True)
    d.add_argument("--key", required=True, help="32 hex chars (16 bytes)")
    d.add_argument("--kid", required=True, help="32 hex chars (16 bytes)")
    d.add_argument(
        "--scheme", default="cenc-aes-ctr", choices=["cenc-aes-ctr", "cenc-aes-cbc"]
    )
    d.set_defaults(func=cmd_dash_cenc)

    x = sub.add_parser(
        "decrypt-segment", help="decrypt one AES-128-CBC TS segment via openssl"
    )
    x.add_argument("--input", required=True)
    x.add_argument("--key", required=True, help="path to 16-byte key file")
    x.add_argument("--iv", required=True, help="32 hex chars")
    x.add_argument("--output", required=True)
    x.set_defaults(func=cmd_decrypt_segment)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
