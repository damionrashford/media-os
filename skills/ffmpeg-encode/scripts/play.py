#!/usr/bin/env python3
"""
play.py — ffplay wrapper for preview, filter-test, and visualization.

Subcommands:
  preview         Play a file (optional start/duration/size/loop).
  filter-test     Live-preview a -vf / -af chain without transcoding.
  waveform        Show audio as a scrolling waveform (showwaves).
  spectrum        Show audio as a spectrogram (showspectrum).
  vectorscope     Overlay a live vectorscope on a video.
  loudness-meter  Show a live EBU R128 loudness meter (ebur128 video=1).
  sync            Pick an AV master clock (audio / video / ext).

Flags:
  --dry-run    Print the ffplay command and exit.
  --verbose    Set -loglevel verbose so pix_fmt/SAR/etc print to stderr.

Stdlib only. Non-interactive. Works on macOS / Linux / Windows.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from typing import List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_display() -> bool:
    """Return True if a GUI session looks available for SDL."""
    if sys.platform == "darwin":
        # Cocoa/Quartz is usually present when logged in. There is no cheap
        # programmatic check that's reliable; assume yes unless forced off.
        return os.environ.get("CLAUDE_FFPLAY_HEADLESS") != "1"
    if sys.platform.startswith("win"):
        return True
    # Linux / BSD — need DISPLAY (X11) or WAYLAND_DISPLAY.
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _find_ffplay() -> str:
    path = shutil.which("ffplay")
    if not path:
        print(
            "error: ffplay not found in PATH. Install it with the ffmpeg package.",
            file=sys.stderr,
        )
        sys.exit(127)
    return path


def _maybe_nodisp(cmd: List[str], allow: bool) -> List[str]:
    """Inject -nodisp if there's no DISPLAY and the subcommand tolerates it."""
    if allow and not _has_display():
        print(
            "warning: no DISPLAY / WAYLAND_DISPLAY detected; adding -nodisp "
            "(audio only, video decoded but not shown).",
            file=sys.stderr,
        )
        # Insert right after the binary so SDL video init is skipped early.
        return [cmd[0], "-nodisp"] + cmd[1:]
    return cmd


def _run(cmd: List[str], dry_run: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


def _common_flags(args: argparse.Namespace) -> List[str]:
    flags: List[str] = []
    if getattr(args, "verbose", False):
        flags += ["-loglevel", "verbose"]
    else:
        flags += ["-hide_banner"]
    return flags


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_preview(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    cmd: List[str] = [ffplay] + _common_flags(args)
    if args.start is not None:
        cmd += ["-ss", str(args.start)]
    if args.duration is not None:
        cmd += ["-t", str(args.duration)]
    if args.size:
        try:
            w, h = args.size.lower().split("x", 1)
            int(w)
            int(h)
        except (ValueError, AttributeError):
            print("error: --size must be WxH (e.g. 1280x720)", file=sys.stderr)
            return 2
        cmd += ["-x", w, "-y", h]
    if args.loop is not None:
        cmd += ["-loop", str(args.loop)]
    if args.autoexit:
        cmd += ["-autoexit"]
    if args.mute:
        cmd += ["-an"]
    if args.video_only:
        cmd += ["-vn"]
    cmd += [args.input]
    cmd = _maybe_nodisp(cmd, allow=True)
    return _run(cmd, args.dry_run)


def cmd_filter_test(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    cmd: List[str] = [ffplay] + _common_flags(args)
    if args.vf:
        cmd += ["-vf", args.vf]
    if args.af:
        cmd += ["-af", args.af]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd += [args.input]
    cmd = _maybe_nodisp(cmd, allow=True)
    return _run(cmd, args.dry_run)


def _lavfi(graph: str, input_path: str) -> str:
    """
    Inline an input path into a lavfi source filter safely.
    Escapes backslashes, single-quotes, colons, and commas per ffmpeg grammar.
    """
    escaped = (
        input_path.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", r"\\\'")
        .replace(",", "\\,")
    )
    return graph.replace("__INPUT__", escaped)


def cmd_waveform(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    graph = (
        "amovie='__INPUT__',"
        "asplit[a][w];"
        "[w]showwaves=s=1280x160:mode=cline:rate=30[v];"
        "[a][v]concat=n=1:v=1:a=1[out0][out1]"
    )
    cmd = [ffplay] + _common_flags(args) + ["-f", "lavfi", _lavfi(graph, args.input)]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd = _maybe_nodisp(cmd, allow=False)  # requires video output
    return _run(cmd, args.dry_run)


def cmd_spectrum(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    graph = (
        "amovie='__INPUT__',"
        "asplit[a][w];"
        "[w]showspectrum=s=1280x512:mode=combined:slide=scroll:color=intensity[v];"
        "[a][v]concat=n=1:v=1:a=1[out0][out1]"
    )
    cmd = [ffplay] + _common_flags(args) + ["-f", "lavfi", _lavfi(graph, args.input)]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd = _maybe_nodisp(cmd, allow=False)
    return _run(cmd, args.dry_run)


def cmd_vectorscope(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    vf = "split[a][b];[b]vectorscope=mode=color3[c];[a][c]overlay=W-w"
    cmd = [ffplay] + _common_flags(args) + ["-vf", vf, args.input]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd = _maybe_nodisp(cmd, allow=False)
    return _run(cmd, args.dry_run)


def cmd_loudness_meter(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    graph = (
        "amovie='__INPUT__',"
        f"ebur128=video=1:meter={args.meter}:size=1280x720[out0][out1]"
    )
    cmd = [ffplay] + _common_flags(args) + ["-f", "lavfi", _lavfi(graph, args.input)]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd = _maybe_nodisp(cmd, allow=False)
    return _run(cmd, args.dry_run)


def cmd_sync(args: argparse.Namespace) -> int:
    ffplay = _find_ffplay()
    cmd = [ffplay] + _common_flags(args) + ["-sync", args.mode]
    if args.autoexit:
        cmd += ["-autoexit"]
    cmd += [args.input]
    cmd = _maybe_nodisp(cmd, allow=True)
    return _run(cmd, args.dry_run)


# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    # Parent parser so --dry-run / --verbose work both before AND after the
    # subcommand name (e.g. `play.py --dry-run preview ...` and
    # `play.py preview --dry-run ...`).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run", action="store_true", help="Print the ffplay command and exit."
    )
    common.add_argument(
        "--verbose", action="store_true", help="Pass -loglevel verbose to ffplay."
    )

    p = argparse.ArgumentParser(
        prog="play.py",
        description="ffplay wrapper for preview, filter-test, and visualization.",
        parents=[common],
    )

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("preview", help="Play a file.", parents=[common])
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--start", "-s", help="Start offset (seconds or HH:MM:SS).")
    sp.add_argument("--duration", "-t", help="Playback duration.")
    sp.add_argument("--size", help="Window size, e.g. 1280x720.")
    sp.add_argument("--loop", type=int, help="0 = infinite loop; N = N plays.")
    sp.add_argument(
        "--autoexit",
        action="store_true",
        help="Quit at EOF instead of hanging on last frame.",
    )
    sp.add_argument("--mute", action="store_true", help="Disable audio (-an).")
    sp.add_argument(
        "--video-only",
        action="store_true",
        help="Audio off, video only. (Alias of --mute for parity.)",
    )
    sp.set_defaults(func=cmd_preview)

    sp = sub.add_parser("filter-test", help="Live -vf / -af preview.", parents=[common])
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--vf", help="Video filter chain.")
    sp.add_argument("--af", help="Audio filter chain.")
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_filter_test)

    sp = sub.add_parser(
        "waveform", help="Audio waveform via showwaves.", parents=[common]
    )
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_waveform)

    sp = sub.add_parser(
        "spectrum", help="Audio spectrogram via showspectrum.", parents=[common]
    )
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_spectrum)

    sp = sub.add_parser(
        "vectorscope", help="Vectorscope overlay on video.", parents=[common]
    )
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_vectorscope)

    sp = sub.add_parser("loudness-meter", help="Live EBU R128 meter.", parents=[common])
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument(
        "--meter",
        default="18",
        help="Meter scale in LU (default 18; 9 for fine detail).",
    )
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_loudness_meter)

    sp = sub.add_parser("sync", help="Pick AV master clock.", parents=[common])
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument(
        "--mode",
        required=True,
        choices=["audio", "video", "ext"],
        help="Master clock source.",
    )
    sp.add_argument("--autoexit", action="store_true")
    sp.set_defaults(func=cmd_sync)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
