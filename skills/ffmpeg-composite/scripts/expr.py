#!/usr/bin/env python3
"""
expr.py — run ffmpeg expression-based filters with common defaults.

Subcommands:
  geq        per-pixel YUV or RGB expressions
  aeval      per-sample audio expression
  lut2       two-input pixel math
  drawgraph  burn a metadata chart into the video
  feedback   feedback picture-in-picture loop
  lagfun     dark-decay afterimage

Stdlib only. Non-interactive. Prints the ffmpeg command it plans to run,
supports --dry-run and --verbose. Fails fast on bad inputs.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    kwargs = {}
    if not verbose:
        kwargs["stderr"] = subprocess.DEVNULL
    try:
        proc = subprocess.run(cmd, **kwargs)
        return proc.returncode
    except FileNotFoundError:
        print("error: ffmpeg not found in PATH", file=sys.stderr)
        return 127


def _require_input(path: str) -> None:
    if not Path(path).exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        sys.exit(2)


def cmd_geq(args: argparse.Namespace) -> int:
    _require_input(args.input)
    rgb = any(x is not None for x in (args.r, args.g, args.b))
    yuv = any(x is not None for x in (args.lum, args.cb, args.cr))
    if rgb and yuv:
        print(
            "error: pass either --r/--g/--b (RGB) OR --lum/--cb/--cr (YUV), not both",
            file=sys.stderr,
        )
        return 2
    if not rgb and not yuv:
        print(
            "error: must pass at least one of --lum --cb --cr --r --g --b",
            file=sys.stderr,
        )
        return 2

    parts: list[str] = []
    if rgb:
        parts.append("format=gbrp")
        geq_fields: list[str] = []
        if args.r is not None:
            geq_fields.append(f"r='{args.r}'")
        if args.g is not None:
            geq_fields.append(f"g='{args.g}'")
        if args.b is not None:
            geq_fields.append(f"b='{args.b}'")
        parts.append("geq=" + ":".join(geq_fields))
    else:
        geq_fields = []
        if args.lum is not None:
            geq_fields.append(f"lum='{args.lum}'")
        if args.cb is not None:
            geq_fields.append(f"cb='{args.cb}'")
        if args.cr is not None:
            geq_fields.append(f"cr='{args.cr}'")
        parts.append("geq=" + ":".join(geq_fields))
    vf = ",".join(parts)

    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", args.input, "-vf", vf]
    if args.duration:
        cmd += ["-t", str(args.duration)]
    cmd.append(args.output)
    return _run(cmd, args.dry_run, args.verbose)


def cmd_aeval(args: argparse.Namespace) -> int:
    _require_input(args.input)
    af = f"aeval={args.expr}:c=same"
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", args.input, "-af", af]
    if args.duration:
        cmd += ["-t", str(args.duration)]
    cmd.append(args.output)
    return _run(cmd, args.dry_run, args.verbose)


def cmd_lut2(args: argparse.Namespace) -> int:
    _require_input(args.source0)
    _require_input(args.source1)
    fc = (
        f"[0:v]format=yuv420p[a];[1:v]format=yuv420p[b];"
        f"[a][b]lut2=c0='{args.expr}':c1='{args.expr}':c2='{args.expr}'"
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        args.source0,
        "-i",
        args.source1,
        "-filter_complex",
        fc,
        args.output,
    ]
    return _run(cmd, args.dry_run, args.verbose)


def cmd_drawgraph(args: argparse.Namespace) -> int:
    _require_input(args.input)
    # The drawgraph filter expects the metric producer upstream.
    # signalstats is the common case; other producers (ebur128, blockdetect,
    # blurdetect) can be added manually by wrapping the vf.
    producer = args.producer or "signalstats"
    vf = (
        f"{producer},drawgraph="
        f"m1={args.metric}:fg1=0x{args.color}:"
        f"min={args.min}:max={args.max}:size={args.size}"
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        args.input,
        "-vf",
        vf,
        "-pix_fmt",
        "yuv420p",
        args.output,
    ]
    return _run(cmd, args.dry_run, args.verbose)


def cmd_feedback(args: argparse.Namespace) -> int:
    _require_input(args.input)
    vf = f"feedback=x={args.x}:y={args.y}:w={args.w}:h={args.h}"
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", args.input, "-vf", vf, args.output]
    return _run(cmd, args.dry_run, args.verbose)


def cmd_lagfun(args: argparse.Namespace) -> int:
    _require_input(args.input)
    vf = f"lagfun=decay={args.decay}"
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", args.input, "-vf", vf, args.output]
    return _run(cmd, args.dry_run, args.verbose)


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run", action="store_true", help="print command, do not execute"
    )
    p.add_argument("--verbose", action="store_true", help="show ffmpeg stderr")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="expr.py",
        description="Run ffmpeg expression-based filters (geq, aeval, lut2, drawgraph, feedback, lagfun).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("geq", help="per-pixel expression filter")
    g.add_argument("--input", required=True)
    g.add_argument("--output", required=True)
    g.add_argument("--lum", help="YUV luma expression")
    g.add_argument("--cb", help="YUV Cb expression")
    g.add_argument("--cr", help="YUV Cr expression")
    g.add_argument("--r", help="RGB R expression (auto-inserts format=gbrp)")
    g.add_argument("--g", help="RGB G expression")
    g.add_argument("--b", help="RGB B expression")
    g.add_argument(
        "-t", "--duration", help="limit output duration (e.g. 2 or 00:00:02)"
    )
    _common(g)
    g.set_defaults(func=cmd_geq)

    a = sub.add_parser("aeval", help="per-sample audio expression")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    a.add_argument(
        "--expr",
        required=True,
        help="e.g. 'val(0)*0.5|val(1)*0.5' (separate channel exprs with |)",
    )
    a.add_argument("-t", "--duration")
    _common(a)
    a.set_defaults(func=cmd_aeval)

    l = sub.add_parser("lut2", help="two-input pixel math")
    l.add_argument(
        "--source0", required=True, help="first input, referenced as x in --expr"
    )
    l.add_argument(
        "--source1", required=True, help="second input, referenced as y in --expr"
    )
    l.add_argument("--output", required=True)
    l.add_argument("--expr", required=True, help="e.g. '(x+y)/2'")
    _common(l)
    l.set_defaults(func=cmd_lut2)

    d = sub.add_parser("drawgraph", help="burn a metadata chart into video")
    d.add_argument("--input", required=True)
    d.add_argument("--output", required=True)
    d.add_argument(
        "--metric",
        default="lavfi.signalstats.YAVG",
        help="metadata key (default: lavfi.signalstats.YAVG)",
    )
    d.add_argument(
        "--producer",
        help="upstream filter that emits the metric (default: signalstats)",
    )
    d.add_argument("--min", default="0")
    d.add_argument("--max", default="255")
    d.add_argument("--size", default="1280x200")
    d.add_argument(
        "--color", default="ffff00", help="hex RRGGBB for the trace (default: ffff00)"
    )
    _common(d)
    d.set_defaults(func=cmd_drawgraph)

    f = sub.add_parser("feedback", help="feedback picture-in-picture loop")
    f.add_argument("--input", required=True)
    f.add_argument("--output", required=True)
    f.add_argument("--x", required=True)
    f.add_argument("--y", required=True)
    f.add_argument("--w", required=True)
    f.add_argument("--h", required=True)
    _common(f)
    f.set_defaults(func=cmd_feedback)

    lf = sub.add_parser("lagfun", help="dark-decay afterimage")
    lf.add_argument("--input", required=True)
    lf.add_argument("--output", required=True)
    lf.add_argument("--decay", default="0.9")
    _common(lf)
    lf.set_defaults(func=cmd_lagfun)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
