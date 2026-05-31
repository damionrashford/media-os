#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""winaudio.py — drive Windows audio endpoints from the terminal.

Wraps PowerShell's AudioDeviceCmdlets module (github.com/frgnca/AudioDeviceCmdlets)
and NirSoft's svcl.exe / SoundVolumeView. Has best-effort exclusive-mode probe
and prints install URLs for VB-Cable / VoiceMeeter (does NOT auto-download).

Stdlib only. No interactive prompts. Prints every shell-out to stderr.

Usage:
    winaudio.py list-devices [--kind playback|recording|all]
    winaudio.py get-default [--kind playback|recording|communications]
    winaudio.py set-default NAME [--kind playback|recording|communications]
    winaudio.py mute NAME
    winaudio.py unmute NAME
    winaudio.py volume NAME --level 0-100
    winaudio.py exclusive-test NAME
    winaudio.py vbcable-install
    winaudio.py voicemeeter-config

Every subcommand supports --dry-run and --verbose. On non-Windows hosts the
script prints a helpful message and exits 2.
"""

from __future__ import annotations

import argparse
import platform
import shlex
import shutil
import subprocess
import sys


# ── platform guard ─────────────────────────────────────────────────────────


def require_windows() -> None:
    if platform.system() != "Windows":
        sys.stderr.write(
            "error: audio-wasapi is Windows-only.\n"
            "  For Linux use the audio-pipewire skill.\n"
            "  For macOS use the audio-coreaudio skill.\n"
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


def pwsh_exec() -> str:
    """Pick pwsh (Core) if available, else fall back to powershell.exe."""
    return shutil.which("pwsh") or shutil.which("powershell") or "powershell"


def run_pwsh(script: str, *, dry: bool, verbose: bool) -> int:
    exe = pwsh_exec()
    cmd = [exe, "-NoProfile", "-NonInteractive", "-Command", script]
    if verbose or dry:
        echo(cmd)
    if dry:
        return 0
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


# ── subcommand handlers ────────────────────────────────────────────────────


def cmd_list_devices(args: argparse.Namespace) -> int:
    if args.kind == "all":
        script = (
            "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
            "Get-AudioDevice -List | Format-Table -AutoSize"
        )
    else:
        script = (
            "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
            f"Get-AudioDevice -List | Where-Object {{ $_.Type -eq '{args.kind}' }} "
            "| Format-Table -AutoSize"
        )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_get_default(args: argparse.Namespace) -> int:
    flag = {
        "playback": "-Playback",
        "recording": "-Recording",
        "communications": "-PlaybackCommunication",
    }[args.kind]
    script = (
        "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
        f"Get-AudioDevice {flag} | Format-List"
    )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_set_default(args: argparse.Namespace) -> int:
    # AudioDeviceCmdlets only takes the device's numeric Index or its Id.
    # Use Set-AudioDevice + Get-AudioDevice -List + match by Name.
    kind_filter = {
        "playback": "Playback",
        "recording": "Recording",
    }.get(args.kind, "Playback")
    script = (
        "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
        f"$d = Get-AudioDevice -List | Where-Object {{ $_.Type -eq '{kind_filter}' "
        f"-and $_.Name -eq '{args.name}' }}; "
        "if (-not $d) { Write-Error ('Device not found: ' + '"
        + args.name
        + "'); exit 1 }; "
        "Set-AudioDevice -Index $d.Index"
    )
    if args.kind == "communications":
        script += "; Set-AudioDevice -Index $d.Index -CommunicationDefault"
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_mute(args: argparse.Namespace) -> int:
    script = (
        "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
        f"$d = Get-AudioDevice -List | Where-Object {{ $_.Name -eq '{args.name}' }}; "
        "if (-not $d) { Write-Error 'Device not found'; exit 1 }; "
        "Set-AudioDevice -Index $d.Index; "
        "Set-AudioDevice -PlaybackMute $true"
    )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_unmute(args: argparse.Namespace) -> int:
    script = (
        "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
        f"$d = Get-AudioDevice -List | Where-Object {{ $_.Name -eq '{args.name}' }}; "
        "if (-not $d) { Write-Error 'Device not found'; exit 1 }; "
        "Set-AudioDevice -Index $d.Index; "
        "Set-AudioDevice -PlaybackMute $false"
    )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_volume(args: argparse.Namespace) -> int:
    if not 0 <= args.level <= 100:
        print("error: --level must be 0-100", file=sys.stderr)
        return 2
    script = (
        "Import-Module AudioDeviceCmdlets -ErrorAction Stop; "
        f"$d = Get-AudioDevice -List | Where-Object {{ $_.Name -eq '{args.name}' }}; "
        "if (-not $d) { Write-Error 'Device not found'; exit 1 }; "
        "Set-AudioDevice -Index $d.Index; "
        f"Set-AudioDevice -PlaybackVolume {args.level}"
    )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_exclusive_test(args: argparse.Namespace) -> int:
    """Best-effort probe: read the endpoint's 'AllowExclusiveMode' toggle from
    the registry and report. Setting it requires elevation + UI.
    """
    # AudioEndpointBuilder stores per-endpoint properties under
    # HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\
    # <guid>\Properties\
    # Property {b3f8fa53-0004-438e-9003-51a46e139bfc},2 = "Allow applications to
    # take exclusive control of this device" (REG_DWORD: 1 allow, 0 deny).
    script = (
        "$endpoints = Get-ChildItem "
        "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\MMDevices\\Audio\\Render'; "
        "foreach ($ep in $endpoints) { "
        "  $props = Join-Path $ep.PSPath 'Properties'; "
        "  if (-not (Test-Path $props)) { continue }; "
        "  $name = (Get-ItemProperty $props -ErrorAction SilentlyContinue)."
        "'{a45c254e-df1c-4efd-8020-67d146a850e0},2'; "
        f"  if ($name -ne '{args.name}') {{ continue }}; "
        "  $val = (Get-ItemProperty $props -ErrorAction SilentlyContinue)."
        "'{b3f8fa53-0004-438e-9003-51a46e139bfc},2'; "
        "  $state = switch ($val) { 1 { 'allowed' } 0 { 'blocked' } default { 'unknown' } }; "
        "  Write-Output ('{0} -> exclusive mode: {1}' -f $name, $state); "
        "}"
    )
    return run_pwsh(script, dry=args.dry_run, verbose=args.verbose)


def cmd_vbcable_install(args: argparse.Namespace) -> int:
    print(
        "VB-Audio Virtual Cable — install instructions (do not auto-download):\n"
        "\n"
        "  1. Download: https://vb-audio.com/Cable/\n"
        "  2. Unzip, right-click VBCABLE_Setup_x64.exe, Run as administrator\n"
        "  3. Reboot\n"
        "  4. Two new devices appear: 'CABLE Input' (playback) and 'CABLE Output'\n"
        "     (recording). They are internally wired — anything you play to\n"
        "     CABLE Input is captured from CABLE Output.\n"
        "\n"
        "Tiers (multiple cables):\n"
        "  - VB-Cable (free, donationware) — A+B cable pair\n"
        "  - VB-Cable A+B (paid) — 2 extra named cables\n"
        "  - VB-Cable C+D (paid) — 2 more named cables\n"
        "  - VoiceMeeter / Banana / Potato — full virtual mixer + ASIO bridge\n"
        "\n"
        "See voicemeeter-config for the full VoiceMeeter pointer.\n",
        file=sys.stderr,
    )
    return 0


def cmd_voicemeeter_config(args: argparse.Namespace) -> int:
    print(
        "VoiceMeeter install + basics (do not auto-download):\n"
        "\n"
        "  Download: https://voicemeeter.com/\n"
        "  Editions:\n"
        "    - VoiceMeeter         — 2 physical ins + 1 virtual in -> 1 physical out + 1 virtual out\n"
        "    - VoiceMeeter Banana  — 3 physical + 2 virtual -> 3 physical + 2 virtual\n"
        "    - VoiceMeeter Potato  — 5 physical + 3 virtual -> 5 physical + 3 virtual\n"
        "\n"
        "Install flow:\n"
        "  1. Download, run installer as admin, reboot.\n"
        "  2. Open VoiceMeeter — each 'VoiceMeeter Aux Output' / 'VAIO' is a\n"
        "     virtual WDM audio device visible to every app on the machine.\n"
        "  3. Set Windows default output to 'VoiceMeeter Input' to route system\n"
        "     audio into the mixer, then mix back to the physical output of choice.\n"
        "  4. Apps that want tighter latency can talk ASIO directly to VoiceMeeter\n"
        "     (which is an ASIO host).\n"
        "\n"
        "Config files live under %APPDATA%\\VB\\Voicemeeter as *.xml named\n"
        "by edition. They are GUI-edited; also loadable via -l <path>.\n"
        "\n"
        "Remote control: VoiceMeeter exposes a C API + MIDI / OSC integration;\n"
        "unofficial Python bindings: pip install voicemeeter-api.\n",
        file=sys.stderr,
    )
    return 0


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Windows WASAPI endpoint wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--verbose", action="store_true")

    s = sub.add_parser(
        "list-devices", help="List audio endpoints (Get-AudioDevice -List)"
    )
    s.add_argument("--kind", choices=["playback", "recording", "all"], default="all")
    add_common(s)
    s.set_defaults(fn=cmd_list_devices)

    s = sub.add_parser("get-default", help="Show the current default device")
    s.add_argument(
        "--kind",
        choices=["playback", "recording", "communications"],
        default="playback",
    )
    add_common(s)
    s.set_defaults(fn=cmd_get_default)

    s = sub.add_parser("set-default", help="Change the default device by Name")
    s.add_argument("name", help="Device name (match Get-AudioDevice -List output)")
    s.add_argument(
        "--kind",
        choices=["playback", "recording", "communications"],
        default="playback",
    )
    add_common(s)
    s.set_defaults(fn=cmd_set_default)

    s = sub.add_parser("mute", help="Mute a device")
    s.add_argument("name")
    add_common(s)
    s.set_defaults(fn=cmd_mute)

    s = sub.add_parser("unmute", help="Unmute a device")
    s.add_argument("name")
    add_common(s)
    s.set_defaults(fn=cmd_unmute)

    s = sub.add_parser("volume", help="Set playback volume 0-100")
    s.add_argument("name")
    s.add_argument("--level", type=int, required=True)
    add_common(s)
    s.set_defaults(fn=cmd_volume)

    s = sub.add_parser(
        "exclusive-test",
        help="Probe whether exclusive-mode is allowed for a device",
    )
    s.add_argument("name")
    add_common(s)
    s.set_defaults(fn=cmd_exclusive_test)

    s = sub.add_parser(
        "vbcable-install", help="Print (do NOT run) VB-Cable install instructions"
    )
    add_common(s)
    s.set_defaults(fn=cmd_vbcable_install)

    s = sub.add_parser(
        "voicemeeter-config", help="Print VoiceMeeter install + config pointer"
    )
    add_common(s)
    s.set_defaults(fn=cmd_voicemeeter_config)

    return p


def main() -> int:
    require_windows()
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
