#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
pion.py — scaffold runners for pion/webrtc examples.

Wraps the canonical examples repo at github.com/pion/webrtc. Does NOT
implement Pion itself — you need a Go toolchain on PATH. Stdlib-only.

Usage:
    pion.py check
    pion.py list-examples
    pion.py fetch-example NAME --dest DIR
    pion.py build DIR
    pion.py run DIR
    pion.py whip URL --dest DIR      # fetch-example whip-whep then run
    pion.py whep URL --dest DIR      # fetch-example whip-whep then run (same binary)

Each subcommand supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PION_REPO = "https://github.com/pion/webrtc"

EXAMPLES = [
    "broadcast",
    "custom-logger",
    "data-channels",
    "data-channels-close",
    "data-channels-detach",
    "ice-restart",
    "ice-single-port",
    "ice-tcp",
    "insertable-streams",
    "pion-to-pion",
    "play-from-disk",
    "play-from-disk-h264",
    "reflect",
    "rtp-forwarder",
    "rtp-to-webrtc",
    "save-to-disk",
    "save-to-webm",
    "sfu-ws",
    "simulcast",
    "stats",
    "swap-tracks",
    "trickle-ice",
    "whip-whep",
]


def _emit(cmd: list[str], verbose: bool) -> None:
    if verbose:
        print("[pion] " + " ".join(cmd), file=sys.stderr)


def _run(
    cmd: list[str], cwd: Path | None = None, verbose: bool = False, dry: bool = False
) -> int:
    _emit(cmd, verbose)
    if dry:
        return 0
    return subprocess.run(cmd, cwd=cwd).returncode


def cmd_check(args):
    def which(n):
        p = shutil.which(n)
        return p or "not found"

    print(f"go:  {which('go')}")
    print(f"git: {which('git')}")
    go = shutil.which("go")
    if go:
        subprocess.run([go, "version"])
        subprocess.run([go, "env", "GOPATH"])
    return 0


def cmd_list_examples(args):
    for name in sorted(EXAMPLES):
        print(name)
    print(
        f"\n[{len(EXAMPLES)} examples; canonical list at {PION_REPO}/tree/master/examples]",
        file=sys.stderr,
    )
    return 0


def cmd_fetch_example(args):
    if args.name not in EXAMPLES:
        print(
            f"error: unknown example {args.name!r}. Run `list-examples`.",
            file=sys.stderr,
        )
        return 2
    dest = Path(args.dest).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} already exists and is non-empty", file=sys.stderr)
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    if shutil.which("git") is None:
        print("error: git not found on PATH", file=sys.stderr)
        return 2
    # Sparse-checkout the single example + top-level go.mod/go.sum
    rc = _run(
        [
            "git",
            "clone",
            "--depth=1",
            "--filter=blob:none",
            "--sparse",
            PION_REPO,
            str(dest),
        ],
        verbose=args.verbose,
        dry=args.dry_run,
    )
    if rc != 0:
        return rc
    rc = _run(
        ["git", "sparse-checkout", "set", f"examples/{args.name}", "go.mod", "go.sum"],
        cwd=dest,
        verbose=args.verbose,
        dry=args.dry_run,
    )
    if rc != 0:
        return rc
    print(f"[pion] example ready at {dest / 'examples' / args.name}")
    return 0


def _resolve_example_dir(root: Path) -> Path:
    # If user pointed at the repo root, descend into examples/<only-one>.
    ex = root / "examples"
    if ex.exists():
        subs = [p for p in ex.iterdir() if p.is_dir()]
        if len(subs) == 1:
            return subs[0]
    return root


def cmd_build(args):
    d = _resolve_example_dir(Path(args.dir).expanduser().resolve())
    if shutil.which("go") is None:
        print("error: go not found on PATH", file=sys.stderr)
        return 2
    return _run(["go", "build", "./..."], cwd=d, verbose=args.verbose, dry=args.dry_run)


def cmd_run(args):
    d = _resolve_example_dir(Path(args.dir).expanduser().resolve())
    if shutil.which("go") is None:
        print("error: go not found on PATH", file=sys.stderr)
        return 2
    env = os.environ.copy()
    return _run(["go", "run", "./..."], cwd=d, verbose=args.verbose, dry=args.dry_run)


def _whip_whep_common(args, print_env_hint: str):
    args.name = "whip-whep"
    rc = cmd_fetch_example(args)
    if rc not in (0,):
        # Allow "already exists and non-empty" to still build/run.
        pass
    rc = cmd_build(
        argparse.Namespace(dir=args.dest, verbose=args.verbose, dry_run=args.dry_run)
    )
    if rc != 0:
        return rc
    print(f"[pion] {print_env_hint} -> URL: {args.url}", file=sys.stderr)
    return cmd_run(
        argparse.Namespace(dir=args.dest, verbose=args.verbose, dry_run=args.dry_run)
    )


def cmd_whip(args):
    return _whip_whep_common(args, "WHIP ingest")


def cmd_whep(args):
    return _whip_whep_common(args, "WHEP egress")


def build_parser():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--dry-run", action="store_true", help="print the commands, do not execute"
    )
    parent.add_argument(
        "--verbose", action="store_true", help="trace commands to stderr"
    )

    p = argparse.ArgumentParser(
        description="Scaffold runners for pion/webrtc canonical examples.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[parent],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("check", help="report Go + git + GOPATH", parents=[parent])
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser(
        "list-examples", help="list canonical Pion examples", parents=[parent]
    )
    s.set_defaults(fn=cmd_list_examples)

    s = sub.add_parser(
        "fetch-example", help="sparse-clone one example", parents=[parent]
    )
    s.add_argument("name")
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_fetch_example)

    s = sub.add_parser(
        "build", help="go build ./... in the example dir", parents=[parent]
    )
    s.add_argument("dir")
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser("run", help="go run ./... in the example dir", parents=[parent])
    s.add_argument("dir")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser(
        "whip",
        help="build + run the whip-whep example; URL is informational",
        parents=[parent],
    )
    s.add_argument("url")
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_whip)

    s = sub.add_parser(
        "whep",
        help="build + run the whip-whep example for WHEP playback",
        parents=[parent],
    )
    s.add_argument("url")
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_whep)

    return p


def main():
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
