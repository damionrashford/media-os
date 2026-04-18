#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""ndictl.py — Wrapper around NDI SDK / Tools CLIs.

Non-interactive driver for ndi-send, ndi-find, ndi-record, ndi-benchmark,
plus pointers for NDI Bridge, Studio Monitor, and DistroAV install.

This script does NOT download the SDK automatically (licence acceptance
is required). `install-sdk` prints the URL + platform-specific install steps.

Usage:
    ndictl.py install-sdk --platform <mac|win|linux>
    ndictl.py find [--timeout 5] [--groups PUBLIC,PROD]
    ndictl.py send --input FILE [--name NAME] [--loop] [--groups G]
    ndictl.py record --source "NAME" --output FILE [--duration SEC]
    ndictl.py studio-monitor
    ndictl.py bridge --mode host --listen 0.0.0.0:5990
    ndictl.py bridge --mode join --remote HOST:PORT
    ndictl.py benchmark --resolution 1920x1080 --fps 60 --duration 30

Global flags: --dry-run, --verbose. Every run prints the real command to stderr.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

INSTALL_URLS = {
    "sdk": "https://ndi.video/for-developers/ndi-sdk/",
    "advanced": "https://ndi.video/for-developers/ndi-advanced-sdk/",
    "tools": "https://ndi.video/tools/",
    "distroav": "https://github.com/DistroAV/DistroAV/releases",
}

# Common search paths for NDI bundled CLIs (varies by installer version).
NDI_SEARCH_PATHS = [
    "/Library/NDI SDK for Apple/examples/bin",
    "/Library/NDI Advanced SDK for Apple/examples/bin",
    "/usr/local/bin",
    "/opt/ndi/bin",
    "C:\\Program Files\\NDI\\NDI 6 SDK\\Bin\\x64",
    "C:\\Program Files\\NDI\\NDI 6 Advanced SDK\\Bin\\x64",
]


def resolve_ndi_cli(name: str) -> str | None:
    """Search PATH and known NDI install dirs for an ndi-* executable."""
    hit = shutil.which(name)
    if hit:
        return hit
    for base in NDI_SEARCH_PATHS:
        p = Path(base) / name
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
        # Windows .exe
        p_exe = Path(base) / f"{name}.exe"
        if p_exe.exists():
            return str(p_exe)
    return None


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry_run: bool) -> int:
    echo(cmd)
    if dry_run:
        return 0
    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        print(f"error: {cmd[0]} not found on PATH", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        return 130


def cmd_install_sdk(args: argparse.Namespace) -> int:
    plat = args.platform
    print(f"NDI SDK landing: {INSTALL_URLS['sdk']}")
    print(f"NDI Advanced SDK: {INSTALL_URLS['advanced']}")
    print(f"NDI Tools (end-user apps + runtime): {INSTALL_URLS['tools']}")
    print(f"DistroAV (OBS plugin): {INSTALL_URLS['distroav']}")
    print()
    if plat == "mac":
        print("macOS install steps:")
        print(" 1. Download 'NDI SDK for Apple' .pkg from the SDK URL.")
        print(" 2. Accept licence, install — drops libs in /usr/local/lib and")
        print("    examples under /Library/NDI SDK for Apple/.")
        print(
            " 3. For end-user tools (Studio Monitor, Bridge): install 'NDI Tools' dmg."
        )
        print(" 4. For OBS integration: install DistroAV .pkg.")
    elif plat == "win":
        print("Windows install steps:")
        print(
            " 1. Download 'NDI SDK' .exe from the SDK URL, run as admin, accept licence."
        )
        print(
            " 2. Optional: 'NDI Tools' installer (Studio Monitor, Test Patterns, Scan Converter)."
        )
        print(" 3. For OBS: install DistroAV .exe from GitHub Releases.")
        print(
            " 4. Runtime DLLs go to C:\\Program Files\\NDI\\NDI 6 Runtime\\ — add to PATH if needed."
        )
    elif plat == "linux":
        print("Linux install steps:")
        print(" 1. Download 'NDI SDK for Linux' tarball (x86_64 / aarch64).")
        print(
            " 2. Extract; run the bundled 'Install_NDI_SDK_v6_Linux.sh' — accept licence."
        )
        print(" 3. Copy libndi.so to /usr/local/lib; run ldconfig.")
        print(" 4. Add /usr/local/bin to PATH (for ndi-send, ndi-find, ndi-record).")
        print(" 5. For OBS: install DistroAV .deb / .rpm / Flatpak per distro.")
    else:
        print(f"error: unknown platform {plat!r}", file=sys.stderr)
        return 2
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    cli = resolve_ndi_cli("ndi-find")
    if not cli:
        print(
            "error: ndi-find not found. Install the NDI SDK — see `ndictl.py install-sdk`.",
            file=sys.stderr,
        )
        return 127
    env_note = []
    if args.groups:
        env_note.append(f"NDI_GROUPS={args.groups}")
    env_line = " ".join(env_note)
    cmd = [cli]
    if args.timeout is not None:
        cmd += ["--timeout", str(args.timeout)]
    full = ([env_line] + cmd) if env_line else cmd
    echo(full)
    if args.dry_run:
        return 0
    env = os.environ.copy()
    if args.groups:
        env["NDI_GROUPS"] = args.groups
    try:
        return subprocess.run(cmd, env=env, check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_send(args: argparse.Namespace) -> int:
    cli = resolve_ndi_cli("ndi-send")
    if not cli:
        print(
            "error: ndi-send not found. Install the NDI SDK — see `ndictl.py install-sdk`.",
            file=sys.stderr,
        )
        return 127
    cmd = [cli, "--input", str(args.input)]
    if args.name:
        cmd += ["--name", args.name]
    if args.loop:
        cmd += ["--loop"]
    if args.fps:
        cmd += ["--fps", str(args.fps)]
    env = os.environ.copy()
    if args.groups:
        env["NDI_GROUPS"] = args.groups
    echo(cmd)
    if args.dry_run:
        return 0
    if not Path(args.input).exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2
    try:
        return subprocess.run(cmd, env=env, check=False).returncode
    except KeyboardInterrupt:
        return 130


def cmd_record(args: argparse.Namespace) -> int:
    cli = resolve_ndi_cli("ndi-record")
    if not cli:
        print(
            "error: ndi-record not found. This tool ships with the NDI Advanced SDK only.",
            file=sys.stderr,
        )
        print(
            "       Get it at https://ndi.video/for-developers/ndi-advanced-sdk/ (commercial licence).",
            file=sys.stderr,
        )
        return 127
    cmd = [cli, "--source", args.source, "--output", str(args.output)]
    if args.duration is not None:
        cmd += ["--duration", str(args.duration)]
    return run(cmd, dry_run=args.dry_run)


def cmd_studio_monitor(args: argparse.Namespace) -> int:
    # macOS app path; Windows has start-menu shortcut; Linux has no official GUI.
    mac_app = Path("/Applications/NDI Studio Monitor.app")
    if mac_app.exists():
        cmd = ["open", str(mac_app)]
        return run(cmd, dry_run=args.dry_run)
    windows_hint = Path("C:\\Program Files\\NDI\\NDI 6 Tools\\Studio Monitor")
    if windows_hint.exists():
        exe = windows_hint / "Studio Monitor.exe"
        cmd = [str(exe)]
        return run(cmd, dry_run=args.dry_run)
    print(
        "error: NDI Studio Monitor is not installed on this platform.",
        file=sys.stderr,
    )
    print(
        "       Linux has no official Studio Monitor — use DistroAV inside OBS instead.",
        file=sys.stderr,
    )
    print(f"       Download: {INSTALL_URLS['tools']}", file=sys.stderr)
    return 127


def cmd_bridge(args: argparse.Namespace) -> int:
    # NDI Bridge is a GUI app; no official CLI. Print launch instructions.
    mac_app = Path("/Applications/NDI Bridge.app")
    if args.mode == "host":
        target = f"listen {args.listen}"
    else:
        target = f"join {args.remote}"
    print(f"NDI Bridge — {target}")
    if mac_app.exists():
        cmd = ["open", str(mac_app)]
        print(
            "Launching NDI Bridge GUI on macOS; configure the mode in-app.",
            file=sys.stderr,
        )
        return run(cmd, dry_run=args.dry_run)
    print(
        "error: NDI Bridge not found. It is a GUI-only app and ships with NDI Tools.",
        file=sys.stderr,
    )
    print(f"       Download: {INSTALL_URLS['tools']}", file=sys.stderr)
    return 127


def cmd_benchmark(args: argparse.Namespace) -> int:
    cli = resolve_ndi_cli("ndi-benchmark")
    if not cli:
        print(
            "error: ndi-benchmark not found. Ships with the NDI SDK examples.",
            file=sys.stderr,
        )
        return 127
    cmd = [cli]
    if args.resolution:
        cmd += ["--resolution", args.resolution]
    if args.fps:
        cmd += ["--fps", str(args.fps)]
    if args.duration:
        cmd += ["--duration", str(args.duration)]
    return run(cmd, dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Wrapper around NDI SDK/Tools CLIs. Non-interactive; prints every "
            "real command to stderr before executing."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Global flags on parent parser (so they work before OR after the subcommand).
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command without running it",
    )
    parent.add_argument("--verbose", action="store_true", help="Extra log detail")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("install-sdk", parents=[parent], help="Show SDK install URLs")
    s.add_argument("--platform", required=True, choices=["mac", "win", "linux"])
    s.set_defaults(fn=cmd_install_sdk)

    s = sub.add_parser("find", parents=[parent], help="Discover NDI sources via mDNS")
    s.add_argument("--timeout", type=int, default=None)
    s.add_argument("--groups", help="comma list for NDI_GROUPS env")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("send", parents=[parent], help="Send a file as an NDI source")
    s.add_argument("--input", required=True, help="source media file")
    s.add_argument("--name", help="NDI source name (shows as 'host (name)')")
    s.add_argument("--loop", action="store_true", help="loop the input")
    s.add_argument("--fps", type=int, default=None, help="frame rate override")
    s.add_argument("--groups", help="comma list for NDI_GROUPS env")
    s.set_defaults(fn=cmd_send)

    s = sub.add_parser(
        "record", parents=[parent], help="Record an NDI source (Advanced SDK only)"
    )
    s.add_argument("--source", required=True, help="source name (as ndi-find prints)")
    s.add_argument("--output", required=True, type=Path)
    s.add_argument("--duration", type=int, default=None, help="seconds")
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser(
        "studio-monitor", parents=[parent], help="Launch NDI Studio Monitor GUI"
    )
    s.set_defaults(fn=cmd_studio_monitor)

    s = sub.add_parser(
        "bridge", parents=[parent], help="Launch NDI Bridge GUI (host or join mode)"
    )
    s.add_argument("--mode", required=True, choices=["host", "join"])
    s.add_argument("--listen", help="for host mode, ip:port to listen on")
    s.add_argument("--remote", help="for join mode, host:port of remote bridge")
    s.set_defaults(fn=cmd_bridge)

    s = sub.add_parser(
        "benchmark",
        parents=[parent],
        help="Measure encode/decode throughput via ndi-benchmark",
    )
    s.add_argument("--resolution", default="1920x1080")
    s.add_argument("--fps", type=int, default=60)
    s.add_argument("--duration", type=int, default=30, help="seconds")
    s.set_defaults(fn=cmd_benchmark)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
