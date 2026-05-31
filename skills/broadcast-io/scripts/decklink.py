#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""decklink.py - Blackmagic DeckLink capture and playback wrapper.

Shells out to `ffmpeg` with the decklink indev/outdev (-f decklink).
Non-interactive. Every subcommand supports --dry-run and --verbose and
prints the exact ffmpeg command to stderr before running.

Usage:
    decklink.py list-devices
    decklink.py list-formats --device "DeckLink Mini Recorder 4K"
    decklink.py capture --device "DeckLink Mini Recorder 4K" \
                        --format Hp60 --pixel uyvy422 --out grab.mov
    decklink.py play --device "DeckLink Mini Monitor" --in clip.mov \
                     --format Hp60
    decklink.py signal-gen --device "DeckLink Mini Monitor" \
                           --mode Hp60 --pattern smptebars
    decklink.py sdk-install
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys

ENCODE_PRESETS: dict[str, list[str]] = {
    "prores_proxy": ["-c:v", "prores_ks", "-profile:v", "0", "-pix_fmt", "yuv422p10le"],
    "prores_lt": ["-c:v", "prores_ks", "-profile:v", "1", "-pix_fmt", "yuv422p10le"],
    "prores_hq": ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
    "h264_crf20": [
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p",
    ],
    "hevc_crf20": [
        "-c:v",
        "libx265",
        "-crf",
        "20",
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p10le",
    ],
    "dnxhr_hq": ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-pix_fmt", "yuv422p"],
    "copy": ["-c:v", "copy"],
}

PATTERNS = {
    "smptebars": "smptebars",
    "smptehdbars": "smptehdbars",
    "testsrc": "testsrc",
    "testsrc2": "testsrc2",
    "rgbtestsrc": "rgbtestsrc",
    "black": "color=black",
    "gray": "color=gray",
}


def echo_cmd(cmd: list[str]) -> None:
    """Print the exact command to stderr so agents can audit."""
    print("+ " + " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print(
            "error: ffmpeg not found on PATH. Install ffmpeg built --enable-decklink.",
            file=sys.stderr,
        )
        sys.exit(127)


def run(cmd: list[str], dry_run: bool) -> int:
    echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def cmd_list_devices(args: argparse.Namespace) -> int:
    require_ffmpeg()
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "decklink",
        "-list_devices",
        "1",
        "-i",
        "dummy",
    ]
    return run(cmd, args.dry_run)


def cmd_list_formats(args: argparse.Namespace) -> int:
    require_ffmpeg()
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "decklink",
        "-list_formats",
        "1",
        "-i",
        args.device,
    ]
    return run(cmd, args.dry_run)


def cmd_capture(args: argparse.Namespace) -> int:
    require_ffmpeg()
    cmd = ["ffmpeg", "-hide_banner", "-f", "decklink"]
    if args.format:
        cmd += ["-format_code", args.format]
    if args.pixel:
        cmd += ["-raw_format", args.pixel]
    if args.duplex:
        cmd += ["-duplex_mode", args.duplex]
    cmd += ["-i", args.device]
    if args.encode:
        if args.encode not in ENCODE_PRESETS:
            print(
                f"error: unknown --encode {args.encode!r}. "
                f"Valid: {', '.join(sorted(ENCODE_PRESETS))}",
                file=sys.stderr,
            )
            return 2
        cmd += ENCODE_PRESETS[args.encode]
    else:
        cmd += ["-c:v", "copy", "-c:a", "copy"]
    if args.duration:
        cmd += ["-t", str(args.duration)]
    if args.overwrite:
        cmd.insert(1, "-y")
    cmd.append(args.out)
    return run(cmd, args.dry_run)


def cmd_play(args: argparse.Namespace) -> int:
    require_ffmpeg()
    cmd = ["ffmpeg", "-hide_banner", "-re", "-i", getattr(args, "in")]
    cmd += ["-pix_fmt", args.pixel]
    if args.scale:
        cmd += ["-vf", f"scale={args.scale},setsar=1"]
    cmd += ["-f", "decklink"]
    if args.format:
        cmd += ["-format_code", args.format]
    cmd.append(args.device)
    return run(cmd, args.dry_run)


def cmd_signal_gen(args: argparse.Namespace) -> int:
    require_ffmpeg()
    if args.pattern not in PATTERNS:
        print(
            f"error: unknown --pattern {args.pattern!r}. "
            f"Valid: {', '.join(sorted(PATTERNS))}",
            file=sys.stderr,
        )
        return 2
    pat = PATTERNS[args.pattern]
    video_src = f"{pat}=size={args.size}:rate={args.rate}"
    audio_src = f"sine=frequency={args.tone}:sample_rate=48000"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-re",
        "-f",
        "lavfi",
        "-i",
        video_src,
        "-f",
        "lavfi",
        "-i",
        audio_src,
        "-pix_fmt",
        args.pixel,
        "-f",
        "decklink",
        "-format_code",
        args.mode,
        args.device,
    ]
    if args.duration:
        cmd.insert(3, "-t")
        cmd.insert(4, str(args.duration))
    return run(cmd, args.dry_run)


def cmd_sdk_install(args: argparse.Namespace) -> int:
    # Print-only. No download, no file writes. This is the canonical,
    # non-interactive install summary for agents to relay to the user.
    lines = [
        "Blackmagic DeckLink SDK + driver install summary",
        "==================================================",
        "",
        "1. Desktop Video driver + runtime  (REQUIRED at runtime; no login)",
        "   https://www.blackmagicdesign.com/support/family/capture-and-playback",
        "   - Install, reboot. Provides libDeckLinkAPI.{so,dll,dylib}.",
        "",
        "2. Desktop Video SDK              (needed to BUILD ffmpeg --enable-decklink",
        "                                   or compile your own C++ code;",
        "                                   free Blackmagic developer account required)",
        "   https://www.blackmagicdesign.com/developer/product/capture-and-playback",
        "   - SDK ZIP contains: include/DeckLinkAPI.h, include/DeckLinkAPI.idl,",
        "     platform-specific dispatch shims, and Samples/.",
        "",
        "Official SDK samples (so you cite them correctly):",
        "   CapturePreview, LoopThroughPreview, SignalGenerator, StatusMonitor,",
        "   DeviceList, TestPattern, 3DVideoFrames, StreamOperations, FrameServer,",
        "   AudioMixer.",
        "",
        "NOT official samples (third-party bmdtools):",
        "   bmdcapture, bmdplay   <-  github.com/lu-zero/bmdtools",
        "",
        "Build ffmpeg against the SDK (Linux example):",
        "   ./configure --enable-decklink \\",
        "       --extra-cflags=-I/path/to/SDK/Linux/include",
    ]
    print("\n".join(lines))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Blackmagic DeckLink capture/playback wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-devices", help="enumerate DeckLink devices")
    p1.add_argument("--verbose", action="store_true")
    p1.add_argument("--dry-run", action="store_true")
    p1.set_defaults(fn=cmd_list_devices)

    p2 = sub.add_parser("list-formats", help="list display modes for one device")
    p2.add_argument("--device", required=True, help="exact device name (quoted)")
    p2.add_argument("--verbose", action="store_true")
    p2.add_argument("--dry-run", action="store_true")
    p2.set_defaults(fn=cmd_list_formats)

    p3 = sub.add_parser("capture", help="record an SDI/HDMI signal to a file")
    p3.add_argument("--device", required=True, help="exact device name (quoted)")
    p3.add_argument("--format", help="four-CC or index (e.g. Hp60, 4k60, 23)")
    p3.add_argument(
        "--pixel",
        default="uyvy422",
        help="ffmpeg pix_fmt (uyvy422, v210, r210, argb, bgra). default: uyvy422",
    )
    p3.add_argument("--duplex", choices=["full", "half"], help="duplex mode")
    p3.add_argument(
        "--encode",
        help=f"re-encode preset ({', '.join(sorted(ENCODE_PRESETS))})",
    )
    p3.add_argument("--duration", type=float, help="stop after N seconds")
    p3.add_argument("-y", "--overwrite", action="store_true", help="overwrite --out")
    p3.add_argument("--out", required=True, help="output file path")
    p3.add_argument("--verbose", action="store_true")
    p3.add_argument("--dry-run", action="store_true")
    p3.set_defaults(fn=cmd_capture)

    p4 = sub.add_parser("play", help="play a file out an SDI/HDMI output device")
    p4.add_argument("--device", required=True, help="exact device name (quoted)")
    p4.add_argument("--in", required=True, dest="in", help="input media file")
    p4.add_argument("--format", help="target four-CC or index (e.g. Hp60)")
    p4.add_argument("--pixel", default="uyvy422", help="pix_fmt for output")
    p4.add_argument("--scale", help='optional scale WxH, e.g. "1920:1080"')
    p4.add_argument("--verbose", action="store_true")
    p4.add_argument("--dry-run", action="store_true")
    p4.set_defaults(fn=cmd_play)

    p5 = sub.add_parser("signal-gen", help="generate a test pattern out SDI/HDMI")
    p5.add_argument("--device", required=True, help="exact device name (quoted)")
    p5.add_argument("--mode", required=True, help="four-CC (e.g. Hp60)")
    p5.add_argument(
        "--pattern",
        default="smptebars",
        help=f"test pattern ({', '.join(sorted(PATTERNS))})",
    )
    p5.add_argument(
        "--size", default="1920x1080", help="source size (default 1920x1080)"
    )
    p5.add_argument("--rate", default="60", help="source frame rate (default 60)")
    p5.add_argument("--pixel", default="uyvy422", help="output pix_fmt")
    p5.add_argument(
        "--tone", type=int, default=1000, help="audio tone frequency Hz (default 1000)"
    )
    p5.add_argument(
        "--duration", type=float, help="stop after N seconds (default: loop forever)"
    )
    p5.add_argument("--verbose", action="store_true")
    p5.add_argument("--dry-run", action="store_true")
    p5.set_defaults(fn=cmd_signal_gen)

    p6 = sub.add_parser(
        "sdk-install", help="print DeckLink SDK + driver install summary"
    )
    p6.add_argument("--verbose", action="store_true")
    p6.add_argument("--dry-run", action="store_true")
    p6.set_defaults(fn=cmd_sdk_install)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
