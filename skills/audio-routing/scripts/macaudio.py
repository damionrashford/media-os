#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""macaudio.py — drive macOS Core Audio HAL from the terminal.

Wraps the built-in tools (afinfo, afplay, afconvert, say) plus the de-facto
standard third-party CLI SwitchAudioSource (brew install switchaudio-osx).
Can also enumerate HAL plug-ins and print BlackHole install instructions.

Stdlib only. No interactive prompts. Prints every shell-out to stderr.

Usage:
    macaudio.py list-devices
    macaudio.py set-default NAME [--type input|output|system]
    macaudio.py info FILE
    macaudio.py play FILE [--volume 0-255]
    macaudio.py convert --input IN --output OUT [--format caff|m4af|WAVE|...]
                        [--rate 48000] [--bit-depth 24]
                        [--channel-layout stereo|mono|5.1|...]
    macaudio.py tts "text" [--voice Samantha]
    macaudio.py aggregate-create NAME --devices UID1 UID2 [--drift-correct UID]
    macaudio.py hal-plugins
    macaudio.py blackhole-install [--variant 2ch|16ch|64ch]

Every subcommand supports --dry-run and --verbose. On non-macOS hosts the
script prints a helpful message pointing at audio-pipewire / audio-wasapi and
exits 2.
"""

from __future__ import annotations

import argparse
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


# ── platform guard ─────────────────────────────────────────────────────────


def require_macos() -> None:
    if platform.system() != "Darwin":
        sys.stderr.write(
            "error: audio-coreaudio is macOS-only.\n"
            "  For Linux use the audio-pipewire skill.\n"
            "  For Windows use the audio-wasapi skill.\n"
        )
        sys.exit(2)


# ── helpers ────────────────────────────────────────────────────────────────


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry: bool, verbose: bool) -> int:
    if verbose or dry:
        echo(cmd)
    if dry:
        return 0
    if shutil.which(cmd[0]) is None:
        print(f"error: '{cmd[0]}' not on PATH", file=sys.stderr)
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


# ── subcommand handlers ────────────────────────────────────────────────────


def cmd_list_devices(args: argparse.Namespace) -> int:
    tool = shutil.which("SwitchAudioSource")
    if not tool:
        print(
            "error: SwitchAudioSource not installed. Install with:\n"
            "  brew install switchaudio-osx",
            file=sys.stderr,
        )
        return 127
    cli = ["SwitchAudioSource", "-a"]
    if args.format == "json":
        cli += ["-f", "json"]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_set_default(args: argparse.Namespace) -> int:
    if not shutil.which("SwitchAudioSource"):
        print(
            "error: SwitchAudioSource not installed (brew install switchaudio-osx)",
            file=sys.stderr,
        )
        return 127
    cli = ["SwitchAudioSource", "-s", args.name]
    cli += ["-t", args.type]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_info(args: argparse.Namespace) -> int:
    return run(["afinfo", str(args.file)], dry=args.dry_run, verbose=args.verbose)


def cmd_play(args: argparse.Namespace) -> int:
    cli = ["afplay", str(args.file)]
    if args.volume is not None:
        cli += ["-v", str(args.volume)]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_convert(args: argparse.Namespace) -> int:
    cli = ["afconvert", str(args.input), str(args.output)]
    if args.format:
        cli += ["-f", args.format]
    if args.rate:
        cli += ["-r", str(args.rate)]
    if args.bit_depth:
        cli += ["-d", f"LEI{args.bit_depth}"]
    if args.channel_layout:
        cli += ["-l", args.channel_layout]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_tts(args: argparse.Namespace) -> int:
    cli = ["say", args.text]
    if args.voice:
        cli = ["say", "-v", args.voice, args.text]
    if args.output:
        cli += ["-o", str(args.output)]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_aggregate_create(args: argparse.Namespace) -> int:
    """Build an AppleScript that creates an Aggregate Device via Audio MIDI Setup.

    AppleScript is the simplest no-build-step path. For programmatic use from
    Swift/ObjC, call AudioHardwareCreateAggregateDevice directly.
    """
    members = ",".join(f'"{d}"' for d in args.devices)
    drift = args.drift_correct or ""
    # Build an osascript snippet that drives Audio MIDI Setup.
    script = f"""
tell application "Audio MIDI Setup"
    activate
end tell
-- NOTE: programmatic aggregate creation on modern macOS requires
-- the private API AudioHardwareCreateAggregateDevice (Swift/ObjC).
-- The AppleScript UI path in Audio MIDI Setup.app is the user-level option:
--   1. Click '+' -> Create Aggregate Device
--   2. Check boxes for: {members}
{"--   3. Pick drift-correct master: " + drift if drift else ""}
--   4. Rename to: {args.name}
"""
    if args.verbose or args.dry_run:
        print("+ osascript -e <<EOF", file=sys.stderr)
        print(script, file=sys.stderr)
        print("EOF", file=sys.stderr)
    if args.dry_run:
        return 0
    if shutil.which("osascript") is None:
        print("error: osascript not on PATH (macOS only)", file=sys.stderr)
        return 127
    try:
        return subprocess.run(["osascript", "-e", script], check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_hal_plugins(args: argparse.Namespace) -> int:
    """List HAL plug-ins installed on this Mac."""
    roots = [
        Path("/Library/Audio/Plug-Ins/HAL"),
        Path.home() / "Library/Audio/Plug-Ins/HAL",
    ]
    if args.dry_run:
        for r in roots:
            print(f"+ ls {r}", file=sys.stderr)
        return 0
    found = False
    for r in roots:
        if not r.exists():
            continue
        for p in sorted(r.iterdir()):
            if p.suffix == ".driver":
                print(f"{p}")
                found = True
    if not found:
        print("(no HAL plug-ins found)", file=sys.stderr)
    return 0


def cmd_blackhole_install(args: argparse.Namespace) -> int:
    """Print BlackHole install instructions. Does not auto-install."""
    variant = args.variant or "2ch"
    cask = f"blackhole-{variant}"
    print(
        "BlackHole install instructions (do not auto-install):\n"
        f"  brew install --cask {cask}\n"
        "\n"
        "Variants:\n"
        "  blackhole-2ch   # 2-channel, fits most desktop loopback needs\n"
        "  blackhole-16ch  # 16-channel, for multi-stream routing (OBS, Zoom, etc.)\n"
        "  blackhole-64ch  # 64-channel, for pro-audio DAW sessions\n"
        "\n"
        "After install:\n"
        "  1. Open Audio MIDI Setup.app\n"
        "  2. Build a Multi-Output Device: BlackHole + your speakers\n"
        "  3. Set the Multi-Output Device as system output\n"
        "  4. Point your recorder (OBS / QuickTime screen record) at BlackHole\n"
        "\n"
        "Source / alternatives:\n"
        "  - BlackHole:        https://github.com/ExistentialAudio/BlackHole\n"
        "  - Loopback (paid):  https://rogueamoeba.com/loopback/\n"
        "  - Background Music: https://github.com/kyleneideck/BackgroundMusic\n"
        "\n"
        "Soundflower is ABANDONED — do not install on modern macOS.\n",
        file=sys.stderr,
    )
    return 0


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="macOS Core Audio wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--verbose", action="store_true")

    s = sub.add_parser("list-devices", help="SwitchAudioSource -a")
    s.add_argument("--format", choices=["cli", "json"], default="cli")
    add_common(s)
    s.set_defaults(fn=cmd_list_devices)

    s = sub.add_parser(
        "set-default", help="Change the default input/output/system device"
    )
    s.add_argument("name", help="Device name (match exactly from list-devices)")
    s.add_argument(
        "--type",
        choices=["input", "output", "system"],
        default="output",
        help="Which role to change (default: output)",
    )
    add_common(s)
    s.set_defaults(fn=cmd_set_default)

    s = sub.add_parser("info", help="afinfo — dump file metadata")
    s.add_argument("file", type=Path)
    add_common(s)
    s.set_defaults(fn=cmd_info)

    s = sub.add_parser("play", help="afplay — play a file")
    s.add_argument("file", type=Path)
    s.add_argument("--volume", type=int, help="0-255 (afplay -v)")
    add_common(s)
    s.set_defaults(fn=cmd_play)

    s = sub.add_parser("convert", help="afconvert — change format/rate/bit-depth")
    s.add_argument("--input", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)
    s.add_argument(
        "--format", help="Output format fourCC (caff, m4af, WAVE, AIFF, ...)"
    )
    s.add_argument("--rate", type=int, help="Output sample rate (Hz)")
    s.add_argument("--bit-depth", type=int, help="Output bit depth (16 / 24 / 32 int)")
    s.add_argument(
        "--channel-layout", help="Channel layout tag (mono, stereo, 5.1, 7.1, ...)"
    )
    add_common(s)
    s.set_defaults(fn=cmd_convert)

    s = sub.add_parser("tts", help="say — text-to-speech")
    s.add_argument("text")
    s.add_argument("--voice", help="Voice name (say -v ?) to list available")
    s.add_argument("--output", type=Path, help="Write AIFF to file instead of speaker")
    add_common(s)
    s.set_defaults(fn=cmd_tts)

    s = sub.add_parser(
        "aggregate-create",
        help="Print/run AppleScript that opens Audio MIDI Setup to build an Aggregate Device",
    )
    s.add_argument("--name", required=True, help="Display name for the aggregate")
    s.add_argument(
        "--devices",
        nargs="+",
        required=True,
        help="Member device UIDs (from list-devices)",
    )
    s.add_argument(
        "--drift-correct", help="UID of the device that should drift-correct the others"
    )
    add_common(s)
    s.set_defaults(fn=cmd_aggregate_create)

    s = sub.add_parser(
        "hal-plugins", help="List .driver bundles under /Library/Audio/Plug-Ins/HAL"
    )
    add_common(s)
    s.set_defaults(fn=cmd_hal_plugins)

    s = sub.add_parser(
        "blackhole-install", help="Print (do NOT run) brew cask install instructions"
    )
    s.add_argument("--variant", choices=["2ch", "16ch", "64ch"], default="2ch")
    add_common(s)
    s.set_defaults(fn=cmd_blackhole_install)

    return p


def main() -> int:
    require_macos()
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
