#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Cross-platform ffmpeg capture wrapper.

Subcommands:
    list-devices [--platform auto|mac|win|linux]
    screen      --output O [--fps 30] [--crop WxH+X+Y] [--audio auto|none|<name>] [--duration N]
    webcam      --output O --device NAME [--fps 30] [--size 1280x720]
    audio-only  --output O --device NAME

Global options:
    --dry-run    Print the ffmpeg command instead of running it.
    --verbose    Echo the chosen command to stderr before exec.

Examples:
    python3 capture.py list-devices
    python3 capture.py screen --output out.mp4 --fps 30 --audio auto
    python3 capture.py screen --output clip.mp4 --crop 1280x720+100+100 --duration 15
    python3 capture.py webcam --output cam.mp4 --device "FaceTime HD Camera" --size 1280x720
    python3 capture.py audio-only --output voice.wav --device "MacBook Pro Microphone"

Stdlib only. Non-interactive. No external dependencies.
"""

from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess
import sys
from typing import Optional


# ---------- platform detection ----------


def detect_platform(override: str = "auto") -> str:
    if override != "auto":
        return override
    s = platform.system().lower()
    if s == "darwin":
        return "mac"
    if s == "windows":
        return "win"
    return "linux"


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        print("Error: ffmpeg not found on PATH.", file=sys.stderr)
        sys.exit(2)
    return path


# ---------- device listing ----------


def list_devices_mac() -> str:
    """Run `ffmpeg -f avfoundation -list_devices true -i ""` and return stderr."""
    require_ffmpeg()
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-f",
            "avfoundation",
            "-list_devices",
            "true",
            "-i",
            "",
        ],
        capture_output=True,
        text=True,
    )
    # ffmpeg writes the list to stderr and exits non-zero (no real input).
    return proc.stderr or proc.stdout


def list_devices_win() -> str:
    require_ffmpeg()
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-list_devices",
            "true",
            "-f",
            "dshow",
            "-i",
            "dummy",
        ],
        capture_output=True,
        text=True,
    )
    return proc.stderr or proc.stdout


def list_devices_linux() -> str:
    """Best-effort enumeration across v4l2 + pulse + x11."""
    out = []
    out.append("=== X11 display ===")
    import os

    out.append(f"DISPLAY={os.environ.get('DISPLAY', '(unset)')}")

    out.append("\n=== V4L2 video devices (/dev/video*) ===")
    import glob

    vids = sorted(glob.glob("/dev/video*"))
    if not vids:
        out.append("(none found)")
    for v in vids:
        out.append(v)
        if shutil.which("v4l2-ctl"):
            p = subprocess.run(
                ["v4l2-ctl", "-d", v, "--info"], capture_output=True, text=True
            )
            out.append(p.stdout.strip() or p.stderr.strip())

    out.append("\n=== PulseAudio sources ===")
    if shutil.which("pactl"):
        p = subprocess.run(
            ["pactl", "list", "sources", "short"], capture_output=True, text=True
        )
        out.append(p.stdout.strip() or "(pactl returned nothing)")
    else:
        out.append("(pactl not installed)")

    out.append("\n=== ALSA capture devices ===")
    if shutil.which("arecord"):
        p = subprocess.run(["arecord", "-L"], capture_output=True, text=True)
        out.append(p.stdout.strip() or "(arecord returned nothing)")
    else:
        out.append("(arecord not installed)")

    return "\n".join(out)


def cmd_list_devices(args: argparse.Namespace) -> int:
    plat = detect_platform(args.platform)
    if plat == "mac":
        text = list_devices_mac()
    elif plat == "win":
        text = list_devices_win()
    else:
        text = list_devices_linux()
    print(text)
    return 0


# ---------- avfoundation parser for macOS ----------

_AVF_VIDEO_HEADER = re.compile(r"AVFoundation video devices:", re.I)
_AVF_AUDIO_HEADER = re.compile(r"AVFoundation audio devices:", re.I)
_AVF_ITEM = re.compile(r"\[(\d+)\]\s+(.*)")


def parse_avfoundation(
    text: str,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Return (video_devices, audio_devices) as lists of (index, name)."""
    section = None
    video: list[tuple[int, str]] = []
    audio: list[tuple[int, str]] = []
    for line in text.splitlines():
        if _AVF_VIDEO_HEADER.search(line):
            section = "v"
            continue
        if _AVF_AUDIO_HEADER.search(line):
            section = "a"
            continue
        m = _AVF_ITEM.search(line)
        if not m or section is None:
            continue
        idx, name = int(m.group(1)), m.group(2).strip()
        (video if section == "v" else audio).append((idx, name))
    return video, audio


def mac_pick_screen_index(video: list[tuple[int, str]]) -> Optional[int]:
    for idx, name in video:
        if "capture screen" in name.lower() or "screen" in name.lower():
            return idx
    return video[-1][0] if video else None


def mac_pick_default_audio(audio: list[tuple[int, str]]) -> Optional[int]:
    if not audio:
        return None
    # Prefer built-in mic-sounding names, else first.
    for idx, name in audio:
        low = name.lower()
        if "microphone" in low or "built-in" in low or "macbook" in low:
            return idx
    return audio[0][0]


def mac_find_audio_by_name(audio: list[tuple[int, str]], needle: str) -> Optional[int]:
    needle_l = needle.lower()
    for idx, name in audio:
        if needle_l in name.lower():
            return idx
    return None


def mac_find_video_by_name(video: list[tuple[int, str]], needle: str) -> Optional[int]:
    needle_l = needle.lower()
    for idx, name in video:
        if needle_l in name.lower():
            return idx
    return None


# ---------- crop parsing ----------

_CROP_RE = re.compile(r"^(\d+)x(\d+)\+(\d+)\+(\d+)$")


def parse_crop(spec: str) -> tuple[int, int, int, int]:
    m = _CROP_RE.match(spec)
    if not m:
        print(f"Error: --crop must be WxH+X+Y (got {spec!r})", file=sys.stderr)
        sys.exit(2)
    w, h, x, y = map(int, m.groups())
    return w, h, x, y


_SIZE_RE = re.compile(r"^(\d+)x(\d+)$")


def validate_size(spec: str) -> str:
    if not _SIZE_RE.match(spec):
        print(f"Error: --size must be WxH (got {spec!r})", file=sys.stderr)
        sys.exit(2)
    return spec


# ---------- command builders ----------


def build_screen_mac(args: argparse.Namespace) -> list[str]:
    text = list_devices_mac()
    video, audio = parse_avfoundation(text)
    v_idx = mac_pick_screen_index(video)
    if v_idx is None:
        print("Error: no avfoundation video device found.", file=sys.stderr)
        sys.exit(3)

    # Audio routing
    a_spec = ""
    if args.audio == "none":
        a_spec = ""
    elif args.audio == "auto":
        a = mac_pick_default_audio(audio)
        a_spec = f":{a}" if a is not None else ""
    else:
        a = mac_find_audio_by_name(audio, args.audio)
        if a is None:
            print(
                f"Error: audio device {args.audio!r} not found. Available:",
                file=sys.stderr,
            )
            for idx, name in audio:
                print(f"  [{idx}] {name}", file=sys.stderr)
            sys.exit(3)
        a_spec = f":{a}"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "avfoundation",
        "-framerate",
        str(args.fps),
        "-capture_cursor",
        "1",
        "-i",
        f"{v_idx}{a_spec}",
    ]

    if args.crop:
        w, h, x, y = parse_crop(args.crop)
        cmd += ["-vf", f"crop={w}:{h}:{x}:{y}"]

    if args.duration:
        cmd += ["-t", str(args.duration)]

    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if a_spec:
        cmd += ["-c:a", "aac", "-b:a", "160k"]
    cmd += [args.output]
    return cmd


def build_screen_win(args: argparse.Namespace) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-f", "gdigrab", "-framerate", str(args.fps)]
    if args.crop:
        w, h, x, y = parse_crop(args.crop)
        cmd += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}"]
    cmd += ["-i", "desktop"]

    if args.audio not in ("none",):
        dev = "virtual-audio-capturer" if args.audio == "auto" else args.audio
        cmd += ["-f", "dshow", "-i", f"audio={dev}"]

    if args.duration:
        cmd += ["-t", str(args.duration)]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if args.audio != "none":
        cmd += ["-c:a", "aac", "-b:a", "160k"]
    cmd += [args.output]
    return cmd


def build_screen_linux(args: argparse.Namespace) -> list[str]:
    import os

    display = os.environ.get("DISPLAY", ":0.0")

    cmd = ["ffmpeg", "-hide_banner", "-f", "x11grab", "-framerate", str(args.fps)]
    if args.crop:
        w, h, x, y = parse_crop(args.crop)
        cmd += ["-video_size", f"{w}x{h}", "-i", f"{display}+{x},{y}"]
    else:
        cmd += ["-i", display]

    if args.audio != "none":
        src = "default" if args.audio == "auto" else args.audio
        cmd += ["-f", "pulse", "-i", src]

    if args.duration:
        cmd += ["-t", str(args.duration)]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if args.audio != "none":
        cmd += ["-c:a", "aac", "-b:a", "160k"]
    cmd += [args.output]
    return cmd


def build_screen(args: argparse.Namespace, plat: str) -> list[str]:
    if plat == "mac":
        return build_screen_mac(args)
    if plat == "win":
        return build_screen_win(args)
    return build_screen_linux(args)


def build_webcam_mac(args: argparse.Namespace) -> list[str]:
    text = list_devices_mac()
    video, audio = parse_avfoundation(text)
    v_idx = mac_find_video_by_name(video, args.device)
    if v_idx is None:
        print(f"Error: camera {args.device!r} not found. Available:", file=sys.stderr)
        for idx, name in video:
            print(f"  [{idx}] {name}", file=sys.stderr)
        sys.exit(3)
    a_idx = mac_pick_default_audio(audio)
    a_spec = f":{a_idx}" if a_idx is not None else ""
    size = validate_size(args.size)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "avfoundation",
        "-framerate",
        str(args.fps),
        "-video_size",
        size,
        "-i",
        f"{v_idx}{a_spec}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
    ]
    if a_spec:
        cmd += ["-c:a", "aac"]
    cmd += [args.output]
    return cmd


def build_webcam_win(args: argparse.Namespace) -> list[str]:
    size = validate_size(args.size)
    return [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "dshow",
        "-framerate",
        str(args.fps),
        "-video_size",
        size,
        "-i",
        f"video={args.device}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        args.output,
    ]


def build_webcam_linux(args: argparse.Namespace) -> list[str]:
    size = validate_size(args.size)
    dev = args.device if args.device.startswith("/dev/") else f"/dev/{args.device}"
    return [
        "ffmpeg",
        "-hide_banner",
        "-f",
        "v4l2",
        "-input_format",
        "mjpeg",
        "-video_size",
        size,
        "-framerate",
        str(args.fps),
        "-i",
        dev,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        args.output,
    ]


def build_webcam(args: argparse.Namespace, plat: str) -> list[str]:
    if plat == "mac":
        return build_webcam_mac(args)
    if plat == "win":
        return build_webcam_win(args)
    return build_webcam_linux(args)


def build_audio_only(args: argparse.Namespace, plat: str) -> list[str]:
    if plat == "mac":
        text = list_devices_mac()
        _, audio = parse_avfoundation(text)
        a = mac_find_audio_by_name(audio, args.device)
        if a is None:
            print(f"Error: audio device {args.device!r} not found.", file=sys.stderr)
            for idx, name in audio:
                print(f"  [{idx}] {name}", file=sys.stderr)
            sys.exit(3)
        return [
            "ffmpeg",
            "-hide_banner",
            "-f",
            "avfoundation",
            "-i",
            f":{a}",
            args.output,
        ]
    if plat == "win":
        return [
            "ffmpeg",
            "-hide_banner",
            "-f",
            "dshow",
            "-i",
            f"audio={args.device}",
            args.output,
        ]
    # linux: pulse by default
    return ["ffmpeg", "-hide_banner", "-f", "pulse", "-i", args.device, args.output]


# ---------- runner ----------


def run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    if verbose or dry_run:
        print("+ " + " ".join(_shell_quote(c) for c in cmd), file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(cmd)


def _shell_quote(s: str) -> str:
    if not s or re.search(r"[\s\"'`$\\|&;<>()]", s):
        return '"' + s.replace('"', '\\"') + '"'
    return s


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cross-platform ffmpeg capture wrapper (screen/webcam/audio).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--dry-run", action="store_true", help="Print command, don't run.")
    p.add_argument("--verbose", action="store_true", help="Echo command to stderr.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list-devices", help="List capture devices for this platform.")
    pl.add_argument(
        "--platform", choices=["auto", "mac", "win", "linux"], default="auto"
    )

    ps = sub.add_parser("screen", help="Record the screen.")
    ps.add_argument("--output", required=True)
    ps.add_argument("--fps", type=int, default=30)
    ps.add_argument("--crop", default=None, help="WxH+X+Y region.")
    ps.add_argument(
        "--audio", default="auto", help="auto | none | <device name/substring>"
    )
    ps.add_argument(
        "--duration", type=int, default=None, help="Seconds; omit for manual stop."
    )
    ps.add_argument(
        "--platform", choices=["auto", "mac", "win", "linux"], default="auto"
    )

    pw = sub.add_parser("webcam", help="Record a webcam.")
    pw.add_argument("--output", required=True)
    pw.add_argument(
        "--device", required=True, help="Camera name (mac/win) or /dev/videoN (linux)."
    )
    pw.add_argument("--fps", type=int, default=30)
    pw.add_argument("--size", default="1280x720")
    pw.add_argument(
        "--platform", choices=["auto", "mac", "win", "linux"], default="auto"
    )

    pa = sub.add_parser("audio-only", help="Record audio only.")
    pa.add_argument("--output", required=True)
    pa.add_argument("--device", required=True)
    pa.add_argument(
        "--platform", choices=["auto", "mac", "win", "linux"], default="auto"
    )

    return p


def main() -> int:
    args = build_parser().parse_args()
    require_ffmpeg()

    if args.cmd == "list-devices":
        return cmd_list_devices(args)

    plat = detect_platform(getattr(args, "platform", "auto"))

    if args.cmd == "screen":
        cmd = build_screen(args, plat)
    elif args.cmd == "webcam":
        cmd = build_webcam(args, plat)
    elif args.cmd == "audio-only":
        cmd = build_audio_only(args, plat)
    else:
        print(f"Unknown subcommand: {args.cmd}", file=sys.stderr)
        return 2

    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
