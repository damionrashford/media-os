#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""gst.py -- Build and run GStreamer pipelines from the CLI.

Wraps the six official GStreamer command-line tools into a single argparse
interface with --dry-run + --verbose + stderr-echo of the exact tool command.

Subcommands:
    list-elements     gst-inspect-1.0  (no args -> every factory)
    inspect           gst-inspect-1.0 <element>
    discover          gst-discoverer-1.0 [URI]
    devices           gst-device-monitor-1.0 [classes]
    launch            gst-launch-1.0 <pipeline-desc>
    typefind          gst-typefind-1.0 <file>
    play              gst-play-1.0 <URI>

Every subcommand prints the effective shell invocation to stderr before
running, honours --dry-run, and propagates the tool's exit code.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from typing import Sequence

DEFAULT_VERSION_SUFFIX = "-1.0"  # GStreamer 1.x ships tools as foo-1.0


def which_tool(name: str) -> str:
    """Return the full path of a gstreamer CLI or raise with a helpful hint."""
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(
        f"error: {name} not found on PATH. "
        f"Install GStreamer (see gstreamer.freedesktop.org/documentation/installing/). "
        f"On macOS: brew install gstreamer. "
        f"On Debian/Ubuntu: apt install gstreamer1.0-tools."
    )


def echo_and_run(
    cmd: Sequence[str],
    *,
    dry_run: bool,
    verbose: bool,
    extra_env: dict[str, str] | None = None,
) -> int:
    display = "+ " + " ".join(shlex.quote(a) for a in cmd)
    print(display, file=sys.stderr)
    if verbose and extra_env:
        for k, v in extra_env.items():
            print(f"[env] {k}={v}", file=sys.stderr)
    if dry_run:
        return 0
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run(cmd, env=env, check=False).returncode
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


# ── Subcommand implementations ──────────────────────────────────────────────


def cmd_list_elements(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-inspect{DEFAULT_VERSION_SUFFIX}")
    cmd: list[str] = [tool]
    if args.plugin:
        cmd.append(args.plugin)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_inspect(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-inspect{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    if args.all:
        cmd.append("-a")
    if args.uri_handlers:
        cmd.append("--uri-handlers")
    if args.types:
        cmd.append("--types")
        cmd.append(args.types)
    if args.element:
        cmd.append(args.element)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_discover(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-discoverer{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    if args.verbose_tool:
        cmd.append("-v")
    if args.timeout:
        cmd += ["-t", str(args.timeout)]
    if args.uri:
        cmd.append(args.uri)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_devices(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-device-monitor{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    if args.follow:
        cmd.append("-f")
    if args.include_hidden:
        cmd.append("-i")
    if args.classes:
        cmd.extend(args.classes)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_launch(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-launch{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    if args.verbose_tool:
        cmd.append("-v")
    if args.no_fault:
        cmd.append("--no-fault")
    if args.eos_on_shutdown:
        cmd.append("-e")
    if args.messages:
        cmd.append("-m")
    if args.tags:
        cmd.append("-t")
    if args.quiet:
        cmd.append("-q")
    # Pipeline tokens come through as a positional list so gst-launch can
    # parse element ! element with its own grammar.
    cmd.extend(args.pipeline)
    env: dict[str, str] = {}
    if args.debug_level:
        env["GST_DEBUG"] = args.debug_level
    if args.debug_file:
        env["GST_DEBUG_FILE"] = args.debug_file
    return echo_and_run(
        cmd, dry_run=args.dry_run, verbose=args.verbose, extra_env=env or None
    )


def cmd_typefind(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-typefind{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    cmd.extend(args.files)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_play(args: argparse.Namespace) -> int:
    tool = which_tool(f"gst-play{DEFAULT_VERSION_SUFFIX}")
    cmd = [tool]
    if args.audio_only:
        cmd.append("--audio")
    if args.video_sink:
        cmd += ["--videosink", args.video_sink]
    if args.audio_sink:
        cmd += ["--audiosink", args.audio_sink]
    if args.flags:
        cmd += ["--flags", args.flags]
    if args.volume is not None:
        cmd += ["--volume", str(args.volume)]
    if args.no_interactive:
        cmd.append("--interactive=false")
    cmd.extend(args.uris)
    return echo_and_run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# ── Parser ──────────────────────────────────────────────────────────────────


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact tool command to stderr and exit 0 without running it",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Also print env-var overrides and tool metadata to stderr",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build and run GStreamer pipelines with the standard CLI tools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # list-elements
    p1 = sub.add_parser(
        "list-elements",
        help="list every registered element factory (optionally filter to one plugin)",
    )
    p1.add_argument("--plugin", help="limit output to elements provided by this plugin")
    add_common(p1)
    p1.set_defaults(fn=cmd_list_elements)

    # inspect
    p2 = sub.add_parser("inspect", help="introspect an element factory")
    p2.add_argument(
        "--element",
        help="element factory name (e.g. filesrc, webrtcbin, hlssink2). "
        "Omit to list every factory.",
    )
    p2.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="print all (plugins + elements + types)",
    )
    p2.add_argument(
        "--uri-handlers",
        action="store_true",
        help="print which elements handle what URI schemes",
    )
    p2.add_argument(
        "--types",
        help="filter element factories by type (source/sink/encoder/decoder/muxer/demuxer/...)",
    )
    add_common(p2)
    p2.set_defaults(fn=cmd_inspect)

    # discover
    p3 = sub.add_parser(
        "discover",
        help="probe a URI with gst-discoverer (streams, caps, tags, duration)",
    )
    p3.add_argument("--uri", help="URI to probe (file:///, http://, rtsp://, etc.)")
    p3.add_argument(
        "-v", "--verbose-tool", action="store_true", help="verbose discoverer output"
    )
    p3.add_argument("-t", "--timeout", type=int, help="timeout in seconds")
    add_common(p3)
    p3.set_defaults(fn=cmd_discover)

    # devices
    p4 = sub.add_parser(
        "devices", help="enumerate capture/output devices via gst-device-monitor"
    )
    p4.add_argument(
        "--classes",
        nargs="*",
        default=[],
        help="device classes to include (Video/Source Audio/Sink etc.); "
        "leave empty to list all",
    )
    p4.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="stay attached and print device-added/removed events",
    )
    p4.add_argument(
        "-i",
        "--include-hidden",
        action="store_true",
        help="include hidden devices (monitors, loopbacks, etc.)",
    )
    add_common(p4)
    p4.set_defaults(fn=cmd_devices)

    # launch
    p5 = sub.add_parser("launch", help="run a gst-launch-1.0 pipeline description")
    p5.add_argument(
        "pipeline",
        nargs=argparse.REMAINDER,
        help="pipeline description (element ! element ...). "
        "Pass `--` first to separate from gst.py flags if needed.",
    )
    p5.add_argument(
        "-v",
        "--verbose-tool",
        action="store_true",
        help="gst-launch -v (print property changes + caps negotiation)",
    )
    p5.add_argument(
        "-e",
        "--eos-on-shutdown",
        action="store_true",
        help="send EOS on SIGINT so recorders finalise properly",
    )
    p5.add_argument(
        "-m",
        "--messages",
        action="store_true",
        help="print pipeline messages (tags, QoS, buffering)",
    )
    p5.add_argument(
        "-t", "--tags", action="store_true", help="print tag messages as they arrive"
    )
    p5.add_argument(
        "-q", "--quiet", action="store_true", help="suppress progress output"
    )
    p5.add_argument(
        "--no-fault", action="store_true", help="don't install segfault handler"
    )
    p5.add_argument(
        "--debug-level",
        help="GST_DEBUG value (e.g. 3, *:4, GST_PADS:5). Exported as env var.",
    )
    p5.add_argument(
        "--debug-file",
        help="GST_DEBUG_FILE path; when set gstreamer writes debug lines there",
    )
    add_common(p5)
    p5.set_defaults(fn=cmd_launch)

    # typefind
    p6 = sub.add_parser("typefind", help="typefind one or more files")
    p6.add_argument(
        "files", nargs="+", help="file paths (or '-' for stdin not supported by tool)"
    )
    add_common(p6)
    p6.set_defaults(fn=cmd_typefind)

    # play
    p7 = sub.add_parser("play", help="play one or more URIs with gst-play-1.0")
    p7.add_argument(
        "uris",
        nargs="+",
        help="URIs or file paths (gst-play auto-resolves to file://)",
    )
    p7.add_argument("--audio-only", action="store_true", help="audio-only playback")
    p7.add_argument("--video-sink", help="override video sink (e.g. glimagesink)")
    p7.add_argument("--audio-sink", help="override audio sink (e.g. pulsesink)")
    p7.add_argument(
        "--flags",
        help="playbin-flags (e.g. 'video+audio+native-video')",
    )
    p7.add_argument("--volume", type=float, help="initial volume (0.0-10.0)")
    p7.add_argument(
        "--no-interactive",
        action="store_true",
        help="disable the keyboard controls (non-interactive mode — safe for agent runs)",
    )
    add_common(p7)
    p7.set_defaults(fn=cmd_play)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
