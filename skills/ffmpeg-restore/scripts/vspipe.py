#!/usr/bin/env python3
"""vspipe.py — glue between VapourSynth (.vpy) scripts and ffmpeg.

Subcommands:
    check                  Report VapourSynth / vspipe / plugin availability.
    run                    Pipe an existing .vpy through ffmpeg for encoding.
    qtgmc-deinterlace      Generate a QTGMC .vpy and encode (deinterlace).
    knl-denoise            Generate a KNLMeansCL denoise .vpy and encode.
    bm3d-denoise           Generate a BM3DCUDA denoise .vpy and encode.
    gen-vpy                Scaffold a minimal .vpy for a given source plugin.

Flags:
    --dry-run              Print commands/scripts without executing.
    --verbose / -v         Verbose stderr logging.

Stdlib only. Non-interactive. Exit code 0 on success, non-zero on error.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# utilities
# ---------------------------------------------------------------------------


def log(msg: str, *, verbose: bool) -> None:
    if verbose:
        print(f"[vspipe.py] {msg}", file=sys.stderr)


def which_or_die(binary: str, *, dry_run: bool = False) -> str:
    path = shutil.which(binary)
    if not path:
        if dry_run:
            return binary  # fine — dry-run won't actually exec
        print(f"error: required binary not found on PATH: {binary}", file=sys.stderr)
        sys.exit(2)
    return path


def run_cmd(cmd: Sequence[str], *, dry_run: bool, verbose: bool) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if dry_run or verbose:
        print(f"$ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(list(cmd))


def run_pipe(
    producer: Sequence[str],
    consumer: Sequence[str],
    *,
    dry_run: bool,
    verbose: bool,
) -> int:
    prod_str = " ".join(shlex.quote(c) for c in producer)
    cons_str = " ".join(shlex.quote(c) for c in consumer)
    if dry_run or verbose:
        print(f"$ {prod_str} | {cons_str}", file=sys.stderr)
    if dry_run:
        return 0
    p = subprocess.Popen(list(producer), stdout=subprocess.PIPE)
    try:
        c = subprocess.Popen(list(consumer), stdin=p.stdout)
    except FileNotFoundError as exc:
        p.kill()
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if p.stdout is not None:
        p.stdout.close()
    c.wait()
    p.wait()
    return c.returncode or p.returncode


def write_vpy(contents: str, *, dest: Optional[Path], verbose: bool) -> Path:
    if dest is None:
        tmp = tempfile.NamedTemporaryFile(
            prefix="vs_", suffix=".vpy", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(contents)
        tmp.close()
        path = Path(tmp.name)
    else:
        path = dest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    log(f"wrote .vpy -> {path}", verbose=verbose)
    return path


def source_snippet(input_path: str, plugin: str) -> str:
    plugin = plugin.lower()
    if plugin == "ffms2":
        return f'clip = core.ffms2.Source(r"{input_path}")'
    if plugin in {"lsmas", "l-smash", "lwlibav"}:
        return f'clip = core.lsmas.LWLibavSource(r"{input_path}")'
    if plugin == "d2v":
        return f'clip = core.d2v.Source(r"{input_path}")'
    if plugin == "dgsource":
        return f'clip = core.dgdecodenv.DGSource(r"{input_path}")'
    if plugin == "avisource":
        return f'clip = core.avisource.AVISource(r"{input_path}")'
    raise ValueError(f"unknown source plugin: {plugin}")


def build_encode_cmd(
    output: str,
    codec: str,
    crf: Optional[int],
    extra: Sequence[str],
) -> List[str]:
    cmd = ["ffmpeg", "-y", "-i", "-", "-c:v", codec]
    if crf is not None:
        cmd += ["-crf", str(crf)]
    cmd += list(extra)
    cmd += [output]
    return cmd


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    vspipe = shutil.which("vspipe")
    ffmpeg = shutil.which("ffmpeg")
    print(f"vspipe: {vspipe or 'NOT FOUND'}")
    print(f"ffmpeg: {ffmpeg or 'NOT FOUND'}")
    if vspipe:
        try:
            out = subprocess.check_output(
                [vspipe, "--version"], stderr=subprocess.STDOUT
            )
            print(out.decode("utf-8", errors="replace").strip())
        except subprocess.CalledProcessError as exc:
            print(f"vspipe --version failed: {exc}")
    # Plugin probe (best-effort)
    try:
        import vapoursynth  # type: ignore

        core = vapoursynth.core
        print(f"VapourSynth API: {core.version().strip().splitlines()[0]}")
        plugins = sorted({p.namespace for p in core.plugins()})
        print(f"Plugins ({len(plugins)}): {', '.join(plugins)}")
    except Exception as exc:  # pragma: no cover - env dependent
        print(f"vapoursynth python module: NOT IMPORTABLE ({exc})")
    # ffmpeg demuxer check
    if ffmpeg:
        try:
            out = subprocess.check_output([ffmpeg, "-hide_banner", "-demuxers"])
            has_demuxer = b"vapoursynth" in out.lower()
            print(
                f"ffmpeg vapoursynth demuxer: {'yes' if has_demuxer else 'no (use vspipe | ffmpeg fallback)'}"
            )
        except subprocess.CalledProcessError:
            pass
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    vspipe = which_or_die("vspipe", dry_run=args.dry_run)
    which_or_die("ffmpeg", dry_run=args.dry_run)
    vpy = Path(args.vpy)
    if not vpy.exists():
        print(f"error: .vpy not found: {vpy}", file=sys.stderr)
        return 2
    producer = [vspipe, "--y4m", str(vpy), "-"]
    consumer = build_encode_cmd(
        args.output, args.codec, args.crf, args.ffmpeg_extra or []
    )
    return run_pipe(producer, consumer, dry_run=args.dry_run, verbose=args.verbose)


def cmd_qtgmc(args: argparse.Namespace) -> int:
    vspipe = which_or_die("vspipe", dry_run=args.dry_run)
    which_or_die("ffmpeg", dry_run=args.dry_run)
    tff = "True" if args.tff else "False"
    src = source_snippet(args.input, args.source_plugin)
    script = (
        "import vapoursynth as vs\n"
        "import havsfunc as haf\n"
        "core = vs.core\n"
        f"{src}\n"
        f'clip = haf.QTGMC(clip, Preset="{args.preset}", TFF={tff})\n'
        "clip.set_output()\n"
    )
    vpy = write_vpy(
        script,
        dest=Path(args.save_vpy) if args.save_vpy else None,
        verbose=args.verbose,
    )
    producer = [vspipe, "--y4m", str(vpy), "-"]
    consumer = build_encode_cmd(
        args.output, args.codec, args.crf, args.ffmpeg_extra or []
    )
    return run_pipe(producer, consumer, dry_run=args.dry_run, verbose=args.verbose)


def cmd_knl(args: argparse.Namespace) -> int:
    vspipe = which_or_die("vspipe", dry_run=args.dry_run)
    which_or_die("ffmpeg", dry_run=args.dry_run)
    src = source_snippet(args.input, args.source_plugin)
    script = (
        "import vapoursynth as vs\n"
        "core = vs.core\n"
        f"{src}\n"
        f'clip = core.knlm.KNLMeansCL(clip, d=2, a=2, s=4, h={args.sigma}, channels="YUV")\n'
        "clip.set_output()\n"
    )
    vpy = write_vpy(
        script,
        dest=Path(args.save_vpy) if args.save_vpy else None,
        verbose=args.verbose,
    )
    producer = [vspipe, "--y4m", str(vpy), "-"]
    consumer = build_encode_cmd(
        args.output, args.codec, args.crf, args.ffmpeg_extra or []
    )
    return run_pipe(producer, consumer, dry_run=args.dry_run, verbose=args.verbose)


def cmd_bm3d(args: argparse.Namespace) -> int:
    vspipe = which_or_die("vspipe", dry_run=args.dry_run)
    which_or_die("ffmpeg", dry_run=args.dry_run)
    src = source_snippet(args.input, args.source_plugin)
    s = float(args.sigma)
    script = (
        "import vapoursynth as vs\n"
        "core = vs.core\n"
        f"{src}\n"
        f"clip = core.bm3dcuda.BM3D(clip, sigma=[{s}, {s}, {s}])\n"
        "clip.set_output()\n"
    )
    vpy = write_vpy(
        script,
        dest=Path(args.save_vpy) if args.save_vpy else None,
        verbose=args.verbose,
    )
    producer = [vspipe, "--y4m", str(vpy), "-"]
    consumer = build_encode_cmd(
        args.output, args.codec, args.crf, args.ffmpeg_extra or []
    )
    return run_pipe(producer, consumer, dry_run=args.dry_run, verbose=args.verbose)


def cmd_gen_vpy(args: argparse.Namespace) -> int:
    src = source_snippet(args.input, args.source_plugin)
    script = (
        "import vapoursynth as vs\n"
        "core = vs.core\n"
        f"{src}\n"
        "# add filters here, e.g.:\n"
        "# clip = core.std.Crop(clip, left=0, right=0, top=0, bottom=0)\n"
        "clip.set_output()\n"
    )
    out = Path(args.output_vpy)
    if args.dry_run:
        print(f"# would write -> {out}\n{script}")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(script, encoding="utf-8")
    log(f"wrote {out}", verbose=args.verbose)
    print(str(out))
    return 0


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def add_common_encode_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--codec", default="libx264", help="ffmpeg -c:v codec (default: libx264)"
    )
    p.add_argument("--crf", type=int, default=18, help="CRF (default: 18)")
    p.add_argument(
        "--ffmpeg-extra",
        nargs=argparse.REMAINDER,
        help="Extra ffmpeg args after --, passed verbatim",
    )


def add_source_flag(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--source-plugin",
        default="ffms2",
        choices=["ffms2", "lsmas", "d2v", "dgsource", "avisource"],
        help="VapourSynth source plugin (default: ffms2)",
    )


def add_common_io(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", required=True, help="Input media file")
    p.add_argument("--output", required=True, help="Output media file (ffmpeg target)")
    p.add_argument(
        "--save-vpy", help="Persist generated .vpy to this path instead of a tempdir"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vspipe.py",
        description="VapourSynth + ffmpeg glue. Wraps `vspipe --y4m | ffmpeg`.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging to stderr"
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    sp = sub.add_parser(
        "check", help="Report vapoursynth + vspipe + plugin availability"
    )
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("run", help="Pipe a .vpy script through ffmpeg")
    sp.add_argument("--vpy", required=True, help="VapourSynth script (.vpy)")
    sp.add_argument("--output", required=True, help="Output media file")
    add_common_encode_flags(sp)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser(
        "qtgmc-deinterlace", help="QTGMC deinterlace via generated .vpy"
    )
    add_common_io(sp)
    add_source_flag(sp)
    field = sp.add_mutually_exclusive_group(required=True)
    field.add_argument("--tff", dest="tff", action="store_true", help="Top field first")
    field.add_argument(
        "--bff", dest="tff", action="store_false", help="Bottom field first"
    )
    sp.add_argument(
        "--preset",
        default="Slower",
        choices=[
            "Draft",
            "Ultra Fast",
            "Super Fast",
            "Very Fast",
            "Faster",
            "Fast",
            "Medium",
            "Slow",
            "Slower",
            "Very Slow",
            "Placebo",
        ],
        help="QTGMC preset (default: Slower)",
    )
    add_common_encode_flags(sp)
    sp.set_defaults(func=cmd_qtgmc)

    sp = sub.add_parser("knl-denoise", help="KNLMeansCL denoise via generated .vpy")
    add_common_io(sp)
    add_source_flag(sp)
    sp.add_argument(
        "--sigma", type=float, default=1.5, help="KNLMeansCL h (strength, default 1.5)"
    )
    add_common_encode_flags(sp)
    sp.set_defaults(func=cmd_knl)

    sp = sub.add_parser("bm3d-denoise", help="BM3DCUDA denoise via generated .vpy")
    add_common_io(sp)
    add_source_flag(sp)
    sp.add_argument("--sigma", type=float, default=1.0, help="BM3D sigma (default 1.0)")
    add_common_encode_flags(sp)
    sp.set_defaults(func=cmd_bm3d)

    sp = sub.add_parser(
        "gen-vpy", help="Scaffold a minimal .vpy for a given source plugin"
    )
    sp.add_argument("--input", required=True, help="Input media file")
    sp.add_argument("--output-vpy", required=True, help="Destination .vpy path")
    add_source_flag(sp)
    sp.set_defaults(func=cmd_gen_vpy)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
