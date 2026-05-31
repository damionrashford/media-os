#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
whip.py — build and run ffmpeg WHIP publish commands.

Subcommands:
    check-build                       Report ffmpeg version + whip muxer availability.
    publish --input I --endpoint URL  Publish a file as live to a WHIP endpoint.
    publish-screen --endpoint URL     Publish screen + mic capture (avfoundation / x11grab / gdigrab).

Common options:
    --token TOK          Bearer token -> passed via -headers "Authorization: Bearer ...".
    --bitrate 2500k      Video bitrate (default 2500k).
    --resolution WxH     Scale output (default: native).
    --fps N              Frame rate (default 30).
    --audio-bitrate 128k Audio bitrate (default 128k).
    --profile baseline   H.264 profile: baseline or main (default baseline).
    --preset veryfast    x264 preset (default veryfast).
    --hwaccel auto|videotoolbox|nvenc|qsv|none
                         Swap libx264 for a hardware encoder (default none).
    --extra-header "K: V"
                         Add additional HTTP header (repeatable).
    --dry-run            Print the ffmpeg command without running it.
    --verbose            Echo command + ffmpeg stderr to terminal.

Examples:
    uv run scripts/whip.py check-build
    uv run scripts/whip.py publish --input clip.mp4 \\
        --endpoint 'https://whip.example.com/stream' --token $TOK --dry-run
    uv run scripts/whip.py publish-screen \\
        --endpoint 'http://localhost:8889/live/whip' --bitrate 3000k
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional


# ---------------------------- helpers ----------------------------


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        sys.exit(2)
    return path


def _ffmpeg_version() -> Optional[str]:
    try:
        out = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=False
        ).stdout
    except FileNotFoundError:
        return None
    m = re.search(r"ffmpeg version (\S+)", out)
    return m.group(1) if m else None


def _version_major(v: str) -> int:
    m = re.match(r"(\d+)", v or "")
    return int(m.group(1)) if m else 0


def _has_whip_muxer() -> bool:
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-muxers"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except FileNotFoundError:
        return False
    for line in out.splitlines():
        # format: " E whip            WHIP ..."
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in ("E", "D", "DE") and parts[1] == "whip":
            return True
    return False


def _video_encoder_args(args: argparse.Namespace) -> List[str]:
    hw = args.hwaccel
    if hw == "auto":
        sysname = platform.system()
        if sysname == "Darwin":
            hw = "videotoolbox"
        else:
            hw = "none"

    if hw == "videotoolbox":
        v = ["-c:v", "h264_videotoolbox", "-realtime", "1", "-profile:v", args.profile]
    elif hw == "nvenc":
        v = [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p1",
            "-tune",
            "ll",
            "-zerolatency",
            "1",
            "-profile:v",
            args.profile,
        ]
    elif hw == "qsv":
        v = ["-c:v", "h264_qsv", "-preset", args.preset, "-profile:v", args.profile]
    else:
        v = [
            "-c:v",
            "libx264",
            "-profile:v",
            args.profile,
            "-preset",
            args.preset,
            "-tune",
            "zerolatency",
            "-bf",
            "0",
        ]

    gop = str(int(args.fps) * 2)  # 2 second GOP
    v += [
        "-g",
        gop,
        "-keyint_min",
        gop,
        "-sc_threshold",
        "0",
        "-b:v",
        args.bitrate,
        "-maxrate",
        args.bitrate,
        "-bufsize",
        _double_rate(args.bitrate),
        "-pix_fmt",
        "yuv420p",
    ]
    return v


def _audio_encoder_args(args: argparse.Namespace) -> List[str]:
    return [
        "-c:a",
        "libopus",
        "-b:a",
        args.audio_bitrate,
        "-ar",
        "48000",
        "-ac",
        "2",
    ]


def _double_rate(rate: str) -> str:
    m = re.match(r"(\d+)([kKmM]?)", rate)
    if not m:
        return rate
    n = int(m.group(1)) * 2
    return f"{n}{m.group(2)}"


def _headers(args: argparse.Namespace) -> List[str]:
    headers: List[str] = []
    if args.token:
        headers.append(f"Authorization: Bearer {args.token}")
    for h in args.extra_header or []:
        headers.append(h)
    if not headers:
        return []
    joined = "".join(h + "\r\n" for h in headers)
    return ["-headers", joined]


def _scale_filter(args: argparse.Namespace) -> List[str]:
    if not args.resolution:
        return []
    return ["-vf", f"scale={args.resolution.replace('x', ':')}"]


def _run(cmd: List[str], args: argparse.Namespace) -> int:
    quoted = " ".join(shlex.quote(c) for c in cmd)
    if args.dry_run:
        print(quoted)
        return 0
    if args.verbose:
        print(f"+ {quoted}", file=sys.stderr)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


# ---------------------------- subcommands ----------------------------


def cmd_check_build(args: argparse.Namespace) -> int:
    _require_ffmpeg()
    ver = _ffmpeg_version() or "unknown"
    major = _version_major(ver)
    has = _has_whip_muxer()
    print(f"ffmpeg version: {ver}")
    print(f"major: {major}  (whip requires >= 7)")
    print(f"whip muxer present: {'yes' if has else 'NO'}")
    if major >= 7 and has:
        print("status: OK — ready to publish via WHIP")
        return 0
    if major < 7:
        print(
            "status: FAIL — upgrade ffmpeg to 7.0+ (brew upgrade ffmpeg, or static build)"
        )
    elif not has:
        print(
            "status: FAIL — this ffmpeg build lacks the whip muxer; install a full build"
        )
    return 1


def cmd_publish(args: argparse.Namespace) -> int:
    _require_ffmpeg()
    if not os.path.exists(args.input):
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2
    cmd: List[str] = ["ffmpeg", "-hide_banner"]
    if args.verbose:
        cmd += ["-loglevel", "info"]
    else:
        cmd += ["-loglevel", "warning"]
    cmd += ["-re", "-i", args.input]
    cmd += _scale_filter(args)
    cmd += ["-r", str(args.fps)]
    cmd += _video_encoder_args(args)
    cmd += _audio_encoder_args(args)
    cmd += _headers(args)
    cmd += ["-f", "whip", args.endpoint]
    return _run(cmd, args)


def _screen_capture_input(fps: int) -> List[str]:
    sysname = platform.system()
    if sysname == "Darwin":
        # avfoundation: "1:0" = first screen + first audio. User may override via env.
        dev = os.environ.get("WHIP_AVF_DEVICE", "1:0")
        return [
            "-f",
            "avfoundation",
            "-framerate",
            str(fps),
            "-capture_cursor",
            "1",
            "-i",
            dev,
        ]
    if sysname == "Linux":
        display = os.environ.get("DISPLAY", ":0.0")
        pulse = os.environ.get("WHIP_PULSE_SRC", "default")
        return [
            "-f",
            "x11grab",
            "-framerate",
            str(fps),
            "-i",
            display,
            "-f",
            "pulse",
            "-i",
            pulse,
        ]
    if sysname == "Windows":
        mic = os.environ.get("WHIP_DSHOW_MIC", "Microphone")
        return [
            "-f",
            "gdigrab",
            "-framerate",
            str(fps),
            "-i",
            "desktop",
            "-f",
            "dshow",
            "-i",
            f"audio={mic}",
        ]
    print(f"error: unsupported platform for screen capture: {sysname}", file=sys.stderr)
    sys.exit(2)


def cmd_publish_screen(args: argparse.Namespace) -> int:
    _require_ffmpeg()
    cmd: List[str] = ["ffmpeg", "-hide_banner"]
    cmd += ["-loglevel", "info" if args.verbose else "warning"]
    cmd += _screen_capture_input(args.fps)
    cmd += _scale_filter(args)
    cmd += _video_encoder_args(args)
    cmd += _audio_encoder_args(args)
    cmd += _headers(args)
    cmd += ["-f", "whip", args.endpoint]
    return _run(cmd, args)


# ---------------------------- CLI ----------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--token", default=None, help="Bearer token for Authorization header"
    )
    p.add_argument(
        "--extra-header",
        action="append",
        default=[],
        help='Extra HTTP header, e.g. "X-Foo: bar" (repeatable)',
    )
    p.add_argument("--bitrate", default="2500k", help="Video bitrate (default 2500k)")
    p.add_argument(
        "--audio-bitrate", default="128k", help="Audio bitrate (default 128k)"
    )
    p.add_argument(
        "--resolution", default=None, help="Output resolution WxH (default: native)"
    )
    p.add_argument("--fps", type=int, default=30, help="Frame rate (default 30)")
    p.add_argument(
        "--profile",
        default="baseline",
        choices=["baseline", "main"],
        help="H.264 profile (default baseline)",
    )
    p.add_argument(
        "--preset", default="veryfast", help="x264 preset (default veryfast)"
    )
    p.add_argument(
        "--hwaccel",
        default="none",
        choices=["auto", "videotoolbox", "nvenc", "qsv", "none"],
        help="Hardware encoder (default none = libx264)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print command only")
    p.add_argument("--verbose", action="store_true", help="Verbose output")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="whip.py",
        description="Build and run ffmpeg WHIP publish commands.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check-build", help="Verify ffmpeg 7+ with whip muxer")
    p_check.set_defaults(func=cmd_check_build)

    p_pub = sub.add_parser("publish", help="Publish a file as live via WHIP")
    p_pub.add_argument("--input", required=True, help="Input media file")
    p_pub.add_argument("--endpoint", required=True, help="WHIP endpoint URL")
    _add_common(p_pub)
    p_pub.set_defaults(func=cmd_publish)

    p_scr = sub.add_parser(
        "publish-screen", help="Publish screen + mic capture via WHIP"
    )
    p_scr.add_argument("--endpoint", required=True, help="WHIP endpoint URL")
    _add_common(p_scr)
    p_scr.set_defaults(func=cmd_publish_screen)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
