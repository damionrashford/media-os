#!/usr/bin/env python3
"""
quality.py - ffmpeg reference-vs-distorted quality metric runner.

Subcommands:
  vmaf   - compute VMAF of distorted vs reference, output JSON summary.
  psnr   - compute PSNR with per-frame stats file.
  ssim   - compute SSIM with per-frame stats file.
  sweep  - encode a source at multiple CRFs and compute VMAF for each,
           producing a rate-distortion table.

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# --------------------------------------------------------------------------- #
# Utility
# --------------------------------------------------------------------------- #


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[quality] {msg}", file=sys.stderr)


def run_cmd(
    cmd: list[str], *, dry_run: bool, verbose: bool
) -> subprocess.CompletedProcess:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    log(f"exec: {pretty}", verbose)
    if dry_run:
        print(pretty)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("error: ffmpeg not found on PATH")


def require_file(path: str, label: str) -> None:
    if not Path(path).is_file():
        sys.exit(f"error: {label} not found: {path}")


def get_filesize(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


# --------------------------------------------------------------------------- #
# Filter graph builders
# --------------------------------------------------------------------------- #


def align_prefilter(scale_to: str | None, fps: str | None, pix_fmt: str) -> str:
    """Build the per-stream alignment filter chain, joined by commas."""
    parts: list[str] = []
    if scale_to:
        parts.append(f"scale={scale_to}:flags=bicubic")
    if fps:
        parts.append(f"fps={fps}")
    parts.append(f"format={pix_fmt}")
    return ",".join(parts)


def build_vmaf_graph(
    model: str,
    log_path: str,
    log_fmt: str,
    threads: int,
    scale_to: str | None,
    fps: str | None,
    pix_fmt: str,
) -> str:
    pre = align_prefilter(scale_to, fps, pix_fmt)
    vmaf_opts = [
        f"model=version={model}",
        f"log_path={log_path}",
        f"log_fmt={log_fmt}",
        f"n_threads={threads}",
    ]
    vmaf = "libvmaf=" + ":".join(vmaf_opts)
    return f"[0:v]{pre}[dist];" f"[1:v]{pre}[ref];" f"[dist][ref]{vmaf}"


def build_psnr_graph(
    stats_file: str, scale_to: str | None, fps: str | None, pix_fmt: str
) -> str:
    pre = align_prefilter(scale_to, fps, pix_fmt)
    return (
        f"[0:v]{pre}[dist];"
        f"[1:v]{pre}[ref];"
        f"[dist][ref]psnr=stats_file={stats_file}"
    )


def build_ssim_graph(
    stats_file: str, scale_to: str | None, fps: str | None, pix_fmt: str
) -> str:
    pre = align_prefilter(scale_to, fps, pix_fmt)
    return (
        f"[0:v]{pre}[dist];"
        f"[1:v]{pre}[ref];"
        f"[dist][ref]ssim=stats_file={stats_file}"
    )


# --------------------------------------------------------------------------- #
# Parsers
# --------------------------------------------------------------------------- #

PSNR_AVG_RE = re.compile(
    r"PSNR\s+y:([\d.]+)\s+u:([\d.]+)\s+v:([\d.]+)\s+average:([\d.]+)"
)
SSIM_AVG_RE = re.compile(
    r"SSIM\s+Y:([\d.]+)\s+U:([\d.]+)\s+V:([\d.]+)\s+All:([\d.]+)\s+\(([\-\d.]+)dB\)"
)


def parse_psnr_average(stderr: str) -> dict | None:
    m = PSNR_AVG_RE.search(stderr)
    if not m:
        return None
    return {
        "psnr_y": float(m.group(1)),
        "psnr_u": float(m.group(2)),
        "psnr_v": float(m.group(3)),
        "psnr_average": float(m.group(4)),
    }


def parse_ssim_average(stderr: str) -> dict | None:
    m = SSIM_AVG_RE.search(stderr)
    if not m:
        return None
    return {
        "ssim_y": float(m.group(1)),
        "ssim_u": float(m.group(2)),
        "ssim_v": float(m.group(3)),
        "ssim_all": float(m.group(4)),
        "ssim_all_db": float(m.group(5)),
    }


def parse_vmaf_json(path: str) -> dict | None:
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    pooled = data.get("pooled_metrics", {}).get("vmaf", {})
    return {
        "mean": pooled.get("mean"),
        "min": pooled.get("min"),
        "max": pooled.get("max"),
        "harmonic_mean": pooled.get("harmonic_mean"),
    }


# --------------------------------------------------------------------------- #
# Subcommand: vmaf
# --------------------------------------------------------------------------- #


def cmd_vmaf(args: argparse.Namespace) -> int:
    require_ffmpeg()
    if not args.dry_run:
        require_file(args.reference, "reference")
        require_file(args.distorted, "distorted")

    graph = build_vmaf_graph(
        model=args.model,
        log_path=args.log_path,
        log_fmt=args.log_fmt,
        threads=args.threads,
        scale_to=args.scale,
        fps=args.fps,
        pix_fmt=args.pix_fmt,
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        args.distorted,
        "-i",
        args.reference,
        "-lavfi",
        graph,
        "-f",
        "null",
        "-",
    ]
    result = run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    summary = parse_vmaf_json(args.log_path) or {}
    summary["log_path"] = args.log_path
    summary["model"] = args.model
    print(json.dumps(summary, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: psnr
# --------------------------------------------------------------------------- #


def cmd_psnr(args: argparse.Namespace) -> int:
    require_ffmpeg()
    if not args.dry_run:
        require_file(args.reference, "reference")
        require_file(args.distorted, "distorted")

    graph = build_psnr_graph(args.stats_file, args.scale, args.fps, args.pix_fmt)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        args.distorted,
        "-i",
        args.reference,
        "-lavfi",
        graph,
        "-f",
        "null",
        "-",
    ]
    result = run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    summary = parse_psnr_average(result.stderr) or {}
    summary["stats_file"] = args.stats_file
    print(json.dumps(summary, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: ssim
# --------------------------------------------------------------------------- #


def cmd_ssim(args: argparse.Namespace) -> int:
    require_ffmpeg()
    if not args.dry_run:
        require_file(args.reference, "reference")
        require_file(args.distorted, "distorted")

    graph = build_ssim_graph(args.stats_file, args.scale, args.fps, args.pix_fmt)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        args.distorted,
        "-i",
        args.reference,
        "-lavfi",
        graph,
        "-f",
        "null",
        "-",
    ]
    result = run_cmd(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    summary = parse_ssim_average(result.stderr) or {}
    summary["stats_file"] = args.stats_file
    print(json.dumps(summary, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: sweep
# --------------------------------------------------------------------------- #


def encode_at_crf(
    reference: str,
    crf: int,
    encoder: str,
    preset: str,
    out_path: str,
    dry_run: bool,
    verbose: bool,
) -> int:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        reference,
        "-c:v",
        encoder,
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-an",
        out_path,
    ]
    result = run_cmd(cmd, dry_run=dry_run, verbose=verbose)
    if dry_run:
        return 0
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def vmaf_score(
    reference: str,
    distorted: str,
    log_path: str,
    model: str,
    threads: int,
    dry_run: bool,
    verbose: bool,
) -> dict | None:
    graph = build_vmaf_graph(
        model=model,
        log_path=log_path,
        log_fmt="json",
        threads=threads,
        scale_to=None,
        fps=None,
        pix_fmt="yuv420p",
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        distorted,
        "-i",
        reference,
        "-lavfi",
        graph,
        "-f",
        "null",
        "-",
    ]
    result = run_cmd(cmd, dry_run=dry_run, verbose=verbose)
    if dry_run:
        return None
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return None
    return parse_vmaf_json(log_path)


def cmd_sweep(args: argparse.Namespace) -> int:
    require_ffmpeg()
    if not args.dry_run:
        require_file(args.reference, "reference")

    crfs = [int(x.strip()) for x in args.crfs.split(",") if x.strip()]
    if not crfs:
        sys.exit("error: --crfs must be a comma-separated list of integers")

    workdir_ctx = (
        tempfile.TemporaryDirectory(prefix="quality-sweep-")
        if not args.keep_temp
        else None
    )
    workdir = (
        workdir_ctx.name
        if workdir_ctx
        else (args.workdir or tempfile.mkdtemp(prefix="quality-sweep-"))
    )
    log(f"workdir: {workdir}", args.verbose)

    rows: list[dict] = []
    try:
        for crf in crfs:
            enc_path = os.path.join(workdir, f"enc_crf{crf}.mp4")
            log(f"encoding CRF {crf} -> {enc_path}", args.verbose)
            rc = encode_at_crf(
                reference=args.reference,
                crf=crf,
                encoder=args.encoder,
                preset=args.preset,
                out_path=enc_path,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            if rc != 0 and not args.dry_run:
                sys.stderr.write(f"warn: encode failed at CRF {crf}, skipping\n")
                continue

            vmaf_json = os.path.join(workdir, f"vmaf_crf{crf}.json")
            vmaf = vmaf_score(
                reference=args.reference,
                distorted=enc_path,
                log_path=vmaf_json,
                model=args.model,
                threads=args.threads,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            size_bytes = 0 if args.dry_run else get_filesize(enc_path)
            row = {
                "crf": crf,
                "vmaf_mean": vmaf.get("mean") if vmaf else None,
                "vmaf_min": vmaf.get("min") if vmaf else None,
                "vmaf_harmonic_mean": vmaf.get("harmonic_mean") if vmaf else None,
                "filesize_bytes": size_bytes,
                "filesize_mb": (
                    round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0
                ),
                "encode_path": enc_path,
            }
            rows.append(row)
    finally:
        if workdir_ctx is not None:
            workdir_ctx.cleanup()

    if args.dry_run:
        return 0

    # Print a fixed-width table to stdout.
    header = f"{'CRF':>4}  {'VMAF mean':>10}  {'VMAF min':>9}  {'VMAF hmean':>11}  {'Size (MB)':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        vm = f"{r['vmaf_mean']:.3f}" if r["vmaf_mean"] is not None else "n/a"
        vmin = f"{r['vmaf_min']:.3f}" if r["vmaf_min"] is not None else "n/a"
        vhm = (
            f"{r['vmaf_harmonic_mean']:.3f}"
            if r["vmaf_harmonic_mean"] is not None
            else "n/a"
        )
        print(f"{r['crf']:>4}  {vm:>10}  {vmin:>9}  {vhm:>11}  {r['filesize_mb']:>10}")

    # Also emit JSON for machine consumption.
    print()
    print(
        json.dumps(
            {
                "encoder": args.encoder,
                "preset": args.preset,
                "model": args.model,
                "rows": rows,
            },
            indent=2,
        )
    )
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quality.py",
        description="ffmpeg reference-vs-distorted quality metric runner",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print commands without running"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="log executed commands to stderr"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Shared alignment args.
    def add_alignment(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--scale",
            default=None,
            help="force both inputs to W:H before metric (e.g. 1920:1080). Default: no scale.",
        )
        p.add_argument(
            "--fps",
            default=None,
            help="force both inputs to this fps before metric (e.g. 24). Default: no change.",
        )
        p.add_argument(
            "--pix-fmt",
            default="yuv420p",
            help="pixel format to convert both inputs to before metric (default: yuv420p)",
        )

    # vmaf
    p_vmaf = sub.add_parser("vmaf", help="compute VMAF")
    p_vmaf.add_argument(
        "--reference", "-r", required=True, help="path to reference (original) video"
    )
    p_vmaf.add_argument(
        "--distorted", "-d", required=True, help="path to distorted (encoded) video"
    )
    p_vmaf.add_argument(
        "--model",
        default="vmaf_v0.6.1",
        help="VMAF model version (vmaf_v0.6.1, vmaf_v0.6.1neg, vmaf_4k_v0.6.1, vmaf_float_v0.6.1)",
    )
    p_vmaf.add_argument(
        "--threads",
        type=int,
        default=max(1, (os.cpu_count() or 1)),
        help="n_threads for libvmaf (default: number of CPUs)",
    )
    p_vmaf.add_argument(
        "--log-path", default="vmaf.json", help="output path for VMAF log"
    )
    p_vmaf.add_argument(
        "--log-fmt",
        default="json",
        choices=["json", "xml", "csv"],
        help="VMAF log format (default: json)",
    )
    add_alignment(p_vmaf)
    p_vmaf.set_defaults(func=cmd_vmaf)

    # psnr
    p_psnr = sub.add_parser("psnr", help="compute PSNR")
    p_psnr.add_argument(
        "--reference", "-r", required=True, help="path to reference video"
    )
    p_psnr.add_argument(
        "--distorted", "-d", required=True, help="path to distorted video"
    )
    p_psnr.add_argument(
        "--stats-file",
        default="psnr.log",
        help="per-frame stats file (default: psnr.log)",
    )
    add_alignment(p_psnr)
    p_psnr.set_defaults(func=cmd_psnr)

    # ssim
    p_ssim = sub.add_parser("ssim", help="compute SSIM")
    p_ssim.add_argument(
        "--reference", "-r", required=True, help="path to reference video"
    )
    p_ssim.add_argument(
        "--distorted", "-d", required=True, help="path to distorted video"
    )
    p_ssim.add_argument(
        "--stats-file",
        default="ssim.log",
        help="per-frame stats file (default: ssim.log)",
    )
    add_alignment(p_ssim)
    p_ssim.set_defaults(func=cmd_ssim)

    # sweep
    p_sweep = sub.add_parser(
        "sweep", help="encode at multiple CRFs and compute VMAF for each"
    )
    p_sweep.add_argument(
        "--reference", "-r", required=True, help="path to reference/source video"
    )
    p_sweep.add_argument(
        "--crfs",
        default="18,22,26,30",
        help="comma-separated CRF values (default: 18,22,26,30)",
    )
    p_sweep.add_argument(
        "--encoder",
        default="libx264",
        help="video encoder (libx264, libx265, libsvtav1, libvpx-vp9)",
    )
    p_sweep.add_argument(
        "--preset", default="medium", help="encoder preset (default: medium)"
    )
    p_sweep.add_argument(
        "--model", default="vmaf_v0.6.1", help="VMAF model (default: vmaf_v0.6.1)"
    )
    p_sweep.add_argument(
        "--threads",
        type=int,
        default=max(1, (os.cpu_count() or 1)),
        help="n_threads for libvmaf",
    )
    p_sweep.add_argument(
        "--workdir", default=None, help="explicit workdir (default: a temp dir)"
    )
    p_sweep.add_argument(
        "--keep-temp",
        action="store_true",
        help="do not delete the encode temp dir on exit",
    )
    p_sweep.set_defaults(func=cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
