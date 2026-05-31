#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Shaka Packager helper — thin argparse wrapper around `packager`.

Does NOT re-encode. Assumes your renditions are already encoded to the
bitrates/resolutions you want to ship. Builds the right `packager`
command line for ClearKey / Widevine / multi-DRM / FairPlay workflows.

Subcommands:
    check               packager --version
    gen-clearkey-keys   emit a random 16-byte KID+key pair (hex)
    clearkey            package DASH+HLS with raw-key encryption
    widevine            package via Widevine license server
    multi-drm           Widevine + PlayReady combined
    fairplay-hls        HLS-only FairPlay (cbcs)

Examples:
    uv run scripts/shaka.py check
    uv run scripts/shaka.py gen-clearkey-keys
    uv run scripts/shaka.py clearkey \\
        --inputs-video 1080.mp4 720.mp4 \\
        --input-audio audio.m4a \\
        --keys "label=HD:kid=HEX:key=HEX" "label=SD:kid=HEX:key=HEX" \\
        --outdir out/
    uv run scripts/shaka.py widevine \\
        --inputs 1080.mp4 720.mp4 audio.m4a \\
        --key-server https://license.widevine.com/cenc/getcontentkey/PROVIDER \\
        --signer signer-name --aes-key KEY_HEX --aes-iv IV_HEX \\
        --outdir out/
    uv run scripts/shaka.py multi-drm \\
        --inputs 1080.mp4 audio.m4a \\
        --widevine-server https://license.widevine.com/... --signer X --aes-key K --aes-iv I \\
        --playready-server https://playready.example.com/rightsmanager.asmx \\
        --outdir out/
    uv run scripts/shaka.py fairplay-hls \\
        --inputs 1080.mp4 audio.m4a \\
        --keys "label=:kid=HEX:key=HEX" \\
        --outdir out/
"""

from __future__ import annotations

import argparse
import os
import secrets
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_EXT = {".mp4", ".m4v", ".mov", ".mkv", ".webm"}
AUDIO_EXT = {".m4a", ".aac", ".mp4", ".mka", ".webm", ".opus"}


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[shaka] {msg}", file=sys.stderr)


def require_packager() -> str:
    exe = shutil.which("packager")
    if not exe:
        print(
            "Error: `packager` not found on PATH.\n"
            "Install: brew install shaka-packager  (or see https://github.com/shaka-project/shaka-packager/releases)",
            file=sys.stderr,
        )
        sys.exit(2)
    return exe


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT and ext not in {".m4a", ".aac", ".opus"}:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    return "video"


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if dry_run or verbose:
        print(printable, file=sys.stderr if dry_run else sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def build_stream_descriptors(
    video_inputs: list[Path],
    audio_inputs: list[Path],
    outdir: Path,
    *,
    video_labels: list[str] | None = None,
) -> list[str]:
    descriptors: list[str] = []
    for i, vp in enumerate(video_inputs):
        out = outdir / vp.name
        label = video_labels[i] if video_labels and i < len(video_labels) else "HD"
        descriptors.append(f"in={vp},stream=video,output={out},drm_label={label}")
    for ap in audio_inputs:
        out = outdir / ap.name
        descriptors.append(f"in={ap},stream=audio,output={out}")
    return descriptors


def split_mixed(inputs: list[Path]) -> tuple[list[Path], list[Path]]:
    v, a = [], []
    for p in inputs:
        (a if classify(p) == "audio" else v).append(p)
    return v, a


# ---------- subcommands ----------


def cmd_check(args: argparse.Namespace) -> int:
    exe = require_packager()
    return subprocess.call([exe, "--version"])


def cmd_gen_keys(args: argparse.Namespace) -> int:
    kid = secrets.token_hex(16)
    key = secrets.token_hex(16)
    print(f"kid={kid}")
    print(f"key={key}")
    print(
        f"# ClearKey JSON for Shaka Player: "
        f'{{"{bytes_to_b64url(bytes.fromhex(kid))}":'
        f'"{bytes_to_b64url(bytes.fromhex(key))}"}}',
        file=sys.stderr,
    )
    return 0


def bytes_to_b64url(b: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _parse_keys(key_strs: list[str]) -> str:
    # user form: "label=HD:kid=HEX:key=HEX" -> packager form: "label=HD:key_id=HEX:key=HEX"
    parts = []
    for s in key_strs:
        parts.append(s.replace("kid=", "key_id="))
    return ",".join(parts)


def cmd_clearkey(args: argparse.Namespace) -> int:
    exe = require_packager()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    vids = [Path(p) for p in args.inputs_video]
    auds = [Path(p) for p in (args.input_audio or [])]

    labels = (
        args.labels
        if args.labels
        else [f"HD_{i}" if i == 0 else f"SD_{i}" for i in range(len(vids))]
    )
    descriptors = build_stream_descriptors(vids, auds, outdir, video_labels=labels)

    cmd = [exe, *descriptors, "--enable_raw_key_encryption"]
    cmd += ["--keys", _parse_keys(args.keys)]
    cmd += ["--protection_scheme", args.scheme]
    cmd += ["--segment_duration", str(args.segment_duration)]
    if args.clear_lead:
        cmd += ["--clear_lead", str(args.clear_lead)]
    cmd += ["--mpd_output", str(outdir / "manifest.mpd")]
    cmd += ["--hls_master_playlist_output", str(outdir / "master.m3u8")]

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_widevine(args: argparse.Namespace) -> int:
    exe = require_packager()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    vids, auds = split_mixed([Path(p) for p in args.inputs])
    labels = (
        args.labels
        if args.labels
        else [
            "HD" if i == 0 else ("SD" if i == 1 else f"VIDEO_{i}")
            for i in range(len(vids))
        ]
    )
    descriptors = build_stream_descriptors(vids, auds, outdir, video_labels=labels)

    cmd = [exe, *descriptors, "--enable_widevine_encryption"]
    cmd += ["--key_server_url", args.key_server]
    cmd += ["--signer", args.signer]
    cmd += ["--aes_signing_key", args.aes_key]
    cmd += ["--aes_signing_iv", args.aes_iv]
    if args.content_id:
        # hex-encode the content_id
        cmd += ["--content_id", args.content_id.encode().hex()]
    cmd += ["--protection_scheme", args.scheme]
    cmd += ["--segment_duration", str(args.segment_duration)]
    if args.clear_lead:
        cmd += ["--clear_lead", str(args.clear_lead)]
    cmd += ["--mpd_output", str(outdir / "manifest.mpd")]
    if not args.no_hls:
        cmd += ["--hls_master_playlist_output", str(outdir / "master.m3u8")]

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_multi_drm(args: argparse.Namespace) -> int:
    exe = require_packager()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    vids, auds = split_mixed([Path(p) for p in args.inputs])
    labels = (
        args.labels
        if args.labels
        else [
            "HD" if i == 0 else ("SD" if i == 1 else f"VIDEO_{i}")
            for i in range(len(vids))
        ]
    )
    descriptors = build_stream_descriptors(vids, auds, outdir, video_labels=labels)

    cmd = [exe, *descriptors]
    # Widevine
    cmd += [
        "--enable_widevine_encryption",
        "--key_server_url",
        args.widevine_server,
        "--signer",
        args.signer,
        "--aes_signing_key",
        args.aes_key,
        "--aes_signing_iv",
        args.aes_iv,
    ]
    # PlayReady alongside
    cmd += [
        "--enable_playready_encryption",
        "--playready_key_server_url",
        args.playready_server,
    ]
    cmd += ["--protection_scheme", args.scheme]
    cmd += ["--segment_duration", str(args.segment_duration)]
    if args.clear_lead:
        cmd += ["--clear_lead", str(args.clear_lead)]
    cmd += ["--mpd_output", str(outdir / "manifest.mpd")]
    cmd += ["--hls_master_playlist_output", str(outdir / "master.m3u8")]

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_fairplay_hls(args: argparse.Namespace) -> int:
    exe = require_packager()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    vids, auds = split_mixed([Path(p) for p in args.inputs])
    labels = args.labels if args.labels else ["" for _ in vids]
    descriptors = build_stream_descriptors(vids, auds, outdir, video_labels=labels)

    cmd = [exe, *descriptors, "--enable_raw_key_encryption"]
    cmd += ["--keys", _parse_keys(args.keys)]
    cmd += ["--protection_scheme", "cbcs"]  # cbcs is mandatory for FairPlay
    cmd += ["--segment_duration", str(args.segment_duration)]
    if args.clear_lead:
        cmd += ["--clear_lead", str(args.clear_lead)]
    cmd += ["--hls_master_playlist_output", str(outdir / "master.m3u8")]

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ---------- argparse ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="shaka.py",
        description="Shaka Packager helper — thin wrapper around `packager`.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the packager command but do not run it",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Echo the packager command to stderr"
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="packager --version")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser(
        "gen-clearkey-keys", help="Print a random KID+key pair (16 bytes each, hex)"
    )
    sp.set_defaults(func=cmd_gen_keys)

    sp = sub.add_parser(
        "clearkey", help="Package DASH+HLS with raw-key (ClearKey) encryption"
    )
    sp.add_argument(
        "--inputs-video",
        nargs="+",
        required=True,
        help="Pre-encoded video renditions (MP4)",
    )
    sp.add_argument("--input-audio", nargs="*", help="Pre-encoded audio tracks")
    sp.add_argument(
        "--keys",
        nargs="+",
        required=True,
        help='Keys like "label=HD:kid=HEX:key=HEX" (one or more)',
    )
    sp.add_argument(
        "--labels",
        nargs="*",
        help="DRM labels to apply to each video rendition in order",
    )
    sp.add_argument(
        "--scheme",
        choices=["cenc", "cens", "cbc1", "cbcs"],
        default="cbcs",
        help="Protection scheme (default cbcs, works for both DASH and HLS/FairPlay)",
    )
    sp.add_argument("--segment-duration", type=int, default=4)
    sp.add_argument(
        "--clear-lead", type=int, default=0, help="Seconds of unencrypted prefix"
    )
    sp.add_argument("--outdir", required=True)
    sp.set_defaults(func=cmd_clearkey)

    sp = sub.add_parser(
        "widevine", help="Package with Widevine license-server integration"
    )
    sp.add_argument("--inputs", nargs="+", required=True)
    sp.add_argument("--key-server", required=True, help="Widevine key_server_url")
    sp.add_argument("--signer", required=True)
    sp.add_argument("--aes-key", required=True, help="AES signing key (hex)")
    sp.add_argument("--aes-iv", required=True, help="AES signing IV (hex)")
    sp.add_argument(
        "--content-id", default=None, help="Content id (plain, auto hex-encoded)"
    )
    sp.add_argument("--labels", nargs="*")
    sp.add_argument(
        "--scheme", choices=["cenc", "cens", "cbc1", "cbcs"], default="cbcs"
    )
    sp.add_argument("--segment-duration", type=int, default=4)
    sp.add_argument("--clear-lead", type=int, default=0)
    sp.add_argument(
        "--no-hls", action="store_true", help="Skip HLS master playlist output"
    )
    sp.add_argument("--outdir", required=True)
    sp.set_defaults(func=cmd_widevine)

    sp = sub.add_parser(
        "multi-drm", help="Widevine + PlayReady combined, cbcs common encryption"
    )
    sp.add_argument("--inputs", nargs="+", required=True)
    sp.add_argument("--widevine-server", required=True)
    sp.add_argument("--playready-server", required=True)
    sp.add_argument("--signer", required=True)
    sp.add_argument("--aes-key", required=True)
    sp.add_argument("--aes-iv", required=True)
    sp.add_argument("--labels", nargs="*")
    sp.add_argument(
        "--scheme", choices=["cenc", "cens", "cbc1", "cbcs"], default="cbcs"
    )
    sp.add_argument("--segment-duration", type=int, default=4)
    sp.add_argument("--clear-lead", type=int, default=0)
    sp.add_argument("--outdir", required=True)
    sp.set_defaults(func=cmd_multi_drm)

    sp = sub.add_parser("fairplay-hls", help="HLS-only FairPlay (cbcs) via raw key")
    sp.add_argument("--inputs", nargs="+", required=True)
    sp.add_argument(
        "--keys", nargs="+", required=True, help='Keys like "label=:kid=HEX:key=HEX"'
    )
    sp.add_argument("--labels", nargs="*")
    sp.add_argument("--segment-duration", type=int, default=4)
    sp.add_argument("--clear-lead", type=int, default=0)
    sp.add_argument("--outdir", required=True)
    sp.set_defaults(func=cmd_fairplay_hls)

    return p


def main() -> int:
    # Ensure we play nicely in auto/non-interactive environments.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
