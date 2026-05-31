#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""pwctl.py — wrap PipeWire CLIs with argparse subcommands.

Drives the native PipeWire tooling (pw-cli, pw-dump, pw-link, pw-cat, pw-top,
pw-loopback, pw-metadata) through a single subcommand-oriented entry point.
Stdlib only (subprocess + json). No interactive prompts.

Usage:
    pwctl.py list [--kind Node|Port|Link|Device|Module|Metadata]
    pwctl.py dump [--monitor] [--filter <substring>]
    pwctl.py graph [--kind audio|video|midi]
    pwctl.py link <src> <dst>
    pwctl.py unlink <src> <dst>
    pwctl.py links
    pwctl.py play <file> [--target <sink-name>]
    pwctl.py record <file> [--target <source-name>] [--duration N]
    pwctl.py loopback [--name N] [--channels 2] [--capture <src>] [--playback <dst>]
    pwctl.py top [--batch-mode] [--iterations N]
    pwctl.py metadata-get [--id N] [--key K]
    pwctl.py metadata-set --id N --key K --value V [--type T]
    pwctl.py wireplumber-config

Every subcommand supports --dry-run (print the exact command and exit 0) and
--verbose (print to stderr as we go). Shells out, exits with the child's code.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def echo(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(a) for a in cmd), file=sys.stderr)


def run(cmd: list[str], *, dry: bool, verbose: bool) -> int:
    if verbose or dry:
        echo(cmd)
    if dry:
        return 0
    tool = cmd[0]
    if shutil.which(tool) is None:
        print(
            f"error: '{tool}' not on PATH. Install PipeWire or run on a host with PipeWire available.",
            file=sys.stderr,
        )
        return 127
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 130


def run_capture(cmd: list[str], *, verbose: bool) -> tuple[int, str, str]:
    if verbose:
        echo(cmd)
    if shutil.which(cmd[0]) is None:
        return 127, "", f"'{cmd[0]}' not on PATH"
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except KeyboardInterrupt:
        return 130, "", "interrupted"
    return p.returncode, p.stdout, p.stderr


# ── subcommand handlers ────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> int:
    cli = ["pw-cli", "list-objects"]
    if args.kind:
        cli.append(args.kind)
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_dump(args: argparse.Namespace) -> int:
    cli = ["pw-dump"]
    if args.monitor:
        cli.append("--monitor")
    if args.dry_run or not args.filter:
        return run(cli, dry=args.dry_run, verbose=args.verbose)
    # With a filter, capture and filter JSON locally.
    rc, out, err = run_capture(cli, verbose=args.verbose)
    if rc != 0:
        sys.stderr.write(err)
        return rc
    try:
        objs = json.loads(out)
    except json.JSONDecodeError as e:
        print(f"error: pw-dump output not JSON: {e}", file=sys.stderr)
        return 2
    needle = args.filter.lower()

    def matches(o: dict) -> bool:
        return needle in json.dumps(o).lower()

    kept = [o for o in objs if matches(o)]
    json.dump(kept, sys.stdout, indent=2)
    print()
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Render a compact ASCII graph (Nodes with their direction-sorted links)."""
    cli = ["pw-dump"]
    if args.dry_run:
        echo(cli)
        print("[dry-run] would render ASCII graph from pw-dump JSON", file=sys.stderr)
        return 0
    rc, out, err = run_capture(cli, verbose=args.verbose)
    if rc != 0:
        sys.stderr.write(err)
        return rc
    try:
        objs = json.loads(out)
    except json.JSONDecodeError as e:
        print(f"error: pw-dump output not JSON: {e}", file=sys.stderr)
        return 2

    nodes = {}
    ports = {}
    links = []
    for o in objs:
        t = o.get("type", "")
        info = o.get("info", {}) or {}
        props = info.get("props", {}) or {}
        if t.endswith(":Node"):
            nodes[o["id"]] = (
                props.get("node.name") or props.get("node.description") or str(o["id"])
            )
        elif t.endswith(":Port"):
            ports[o["id"]] = {
                "node": props.get("node.id"),
                "name": props.get("port.name", str(o["id"])),
                "dir": props.get("port.direction", "?"),
                "kind": props.get("format.dsp") or props.get("media.type") or "",
            }
        elif t.endswith(":Link"):
            links.append(
                {
                    "out_port": info.get("output-port-id"),
                    "in_port": info.get("input-port-id"),
                    "out_node": info.get("output-node-id"),
                    "in_node": info.get("input-node-id"),
                }
            )

    if args.kind:
        wanted = args.kind.lower()

        def port_kind(p: dict) -> str:
            k = (p.get("kind") or "").lower()
            if "audio" in k:
                return "audio"
            if "video" in k:
                return "video"
            if "midi" in k:
                return "midi"
            return "other"

        links = [
            lk
            for lk in links
            if port_kind(ports.get(lk["out_port"], {})) == wanted
            or port_kind(ports.get(lk["in_port"], {})) == wanted
        ]

    # Print Nodes with their outgoing links
    print("# PipeWire graph (nodes → links)")
    for nid, nname in sorted(nodes.items(), key=lambda x: x[1]):
        outs = [lk for lk in links if lk["out_node"] == nid]
        if not outs:
            continue
        print(f"\n[{nid}] {nname}")
        for lk in outs:
            dst = nodes.get(lk["in_node"], f"?{lk['in_node']}")
            srcp = ports.get(lk["out_port"], {}).get("name", "?")
            dstp = ports.get(lk["in_port"], {}).get("name", "?")
            print(f"    {srcp}  ──►  [{lk['in_node']}] {dst} : {dstp}")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    return run(["pw-link", args.src, args.dst], dry=args.dry_run, verbose=args.verbose)


def cmd_unlink(args: argparse.Namespace) -> int:
    return run(
        ["pw-link", "-d", args.src, args.dst], dry=args.dry_run, verbose=args.verbose
    )


def cmd_links(args: argparse.Namespace) -> int:
    return run(["pw-link", "-l"], dry=args.dry_run, verbose=args.verbose)


def cmd_play(args: argparse.Namespace) -> int:
    cli = ["pw-cat", "--playback", str(args.file)]
    if args.target:
        cli += ["--target", args.target]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_record(args: argparse.Namespace) -> int:
    cli = ["pw-cat", "--record", str(args.file)]
    if args.target:
        cli += ["--target", args.target]
    # pw-cat does not have a --duration; let the user ^C or use `timeout`.
    if args.duration is not None:
        cli = ["timeout", str(args.duration)] + cli
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_loopback(args: argparse.Namespace) -> int:
    cli = ["pw-loopback"]
    if args.name:
        cli += ["--name", args.name]
    if args.channels:
        cli += ["--channels", str(args.channels)]
    if args.capture:
        cli += ["--capture", args.capture]
    if args.playback:
        cli += ["--playback", args.playback]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_top(args: argparse.Namespace) -> int:
    cli = ["pw-top"]
    if args.batch_mode:
        cli.append("--batch-mode")
    if args.iterations is not None:
        cli += ["--iterations", str(args.iterations)]
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_metadata_get(args: argparse.Namespace) -> int:
    cli = ["pw-metadata"]
    if args.id is not None:
        cli.append(str(args.id))
    if args.key:
        if args.id is None:
            cli.append("0")
        cli.append(args.key)
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_metadata_set(args: argparse.Namespace) -> int:
    cli = ["pw-metadata", str(args.id), args.key, args.value]
    if args.type:
        cli.append(args.type)
    return run(cli, dry=args.dry_run, verbose=args.verbose)


def cmd_wireplumber_config(args: argparse.Namespace) -> int:
    """Print WirePlumber config search paths. Does not edit anything."""
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    paths = [
        Path(xdg) / "wireplumber",
        Path("/etc/wireplumber"),
        Path("/usr/share/wireplumber"),
    ]
    print("# WirePlumber config search order (first wins on conflict):")
    for p in paths:
        exists = "exists" if p.exists() else "(absent)"
        print(f"  {p}  {exists}")
    print()
    print("Drop `.lua` / `.conf` fragments in the user config dir to override")
    print("defaults from /usr/share/wireplumber.")
    if args.verbose:
        print(
            "Tip: `wpctl status` (from the wireplumber package) shows the live graph.",
            file=sys.stderr,
        )
    return 0


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PipeWire routing + introspection wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the underlying command and exit 0",
        )
        sp.add_argument(
            "--verbose", action="store_true", help="Echo commands to stderr as they run"
        )

    s = sub.add_parser("list", help="pw-cli list-objects")
    s.add_argument(
        "--kind", help="Filter by type (Node, Port, Link, Device, Module, Metadata)"
    )
    add_common(s)
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("dump", help="pw-dump (full graph as JSON)")
    s.add_argument(
        "--monitor",
        action="store_true",
        help="Stream updates instead of a one-shot snapshot",
    )
    s.add_argument("--filter", help="Client-side substring filter on the JSON")
    add_common(s)
    s.set_defaults(fn=cmd_dump)

    s = sub.add_parser("graph", help="Render an ASCII node→link graph from pw-dump")
    s.add_argument(
        "--kind",
        choices=["audio", "video", "midi"],
        help="Keep only links where either end matches this media type",
    )
    add_common(s)
    s.set_defaults(fn=cmd_graph)

    s = sub.add_parser("link", help="pw-link <src> <dst>")
    s.add_argument("src", help="Source port (e.g. 'Firefox:output_FL')")
    s.add_argument(
        "dst", help="Destination port (e.g. 'alsa_output.pci-...:playback_FL')"
    )
    add_common(s)
    s.set_defaults(fn=cmd_link)

    s = sub.add_parser("unlink", help="pw-link -d <src> <dst>")
    s.add_argument("src")
    s.add_argument("dst")
    add_common(s)
    s.set_defaults(fn=cmd_unlink)

    s = sub.add_parser("links", help="pw-link -l (list existing links)")
    add_common(s)
    s.set_defaults(fn=cmd_links)

    s = sub.add_parser("play", help="pw-cat --playback <file>")
    s.add_argument("file", type=Path)
    s.add_argument("--target", help="Target sink name or id")
    add_common(s)
    s.set_defaults(fn=cmd_play)

    s = sub.add_parser("record", help="pw-cat --record <file>")
    s.add_argument("file", type=Path)
    s.add_argument("--target", help="Target source name or id")
    s.add_argument(
        "--duration", type=float, help="Stop after N seconds (wraps with `timeout`)"
    )
    add_common(s)
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser("loopback", help="pw-loopback (virtual source↔sink bridge)")
    s.add_argument("--name", help="Node/module name for the loopback")
    s.add_argument("--channels", type=int, help="Channel count (default: 2)")
    s.add_argument("--capture", help="Target capture node name")
    s.add_argument("--playback", help="Target playback node name")
    add_common(s)
    s.set_defaults(fn=cmd_loopback)

    s = sub.add_parser("top", help="pw-top (DSP load / xrun viewer)")
    s.add_argument(
        "--batch-mode",
        action="store_true",
        help="Non-curses batch output suitable for logs",
    )
    s.add_argument("--iterations", type=int, help="Iteration cap in batch mode")
    add_common(s)
    s.set_defaults(fn=cmd_top)

    s = sub.add_parser("metadata-get", help="pw-metadata [id] [key]")
    s.add_argument("--id", type=int, help="Metadata object id (default: 0 = default)")
    s.add_argument("--key", help="Key name (e.g. default.audio.sink)")
    add_common(s)
    s.set_defaults(fn=cmd_metadata_get)

    s = sub.add_parser("metadata-set", help="pw-metadata <id> <key> <value> [type]")
    s.add_argument("--id", type=int, required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--value", required=True)
    s.add_argument("--type", help="Value type hint (e.g. Spa:String:JSON)")
    add_common(s)
    s.set_defaults(fn=cmd_metadata_set)

    s = sub.add_parser(
        "wireplumber-config", help="Print WirePlumber config search paths"
    )
    add_common(s)
    s.set_defaults(fn=cmd_wireplumber_config)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
