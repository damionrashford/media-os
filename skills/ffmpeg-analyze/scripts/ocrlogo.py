#!/usr/bin/env python3
"""OCR, logo removal, rectangle and QR operations for ffmpeg.

Subcommands:
  check-build  — report which of {ocr, find_rect, cover_rect, delogo,
                 removelogo, qrencode, quirc} are compiled into the ffmpeg
                 currently on PATH.
  ocr          — run the ocr filter and capture `lavfi.ocr.text` lines.
  delogo       — soft-erase a known rectangle (delogo filter).
  removelogo   — erase logo pixels via an alpha-mask PNG (removelogo filter).
  find-cover   — find a reference image and cover it with an image or blur
                 (find_rect + cover_rect in one chain).
  qr-decode    — identify and decode QR codes via quirc.
  qr-encode    — overlay a generated QR onto video via qrencode.

Every subcommand supports `--dry-run` (print the ffmpeg command without
executing it) and `--verbose` (echo the command to stderr before running).
Stdlib only, non-interactive.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from typing import Iterable, Optional

GATED_FILTERS = {
    "ocr": "--enable-libtesseract",
    "find_rect": "(core)",
    "cover_rect": "(core)",
    "delogo": "(core, GPL)",
    "removelogo": "(core)",
    "qrencode": "--enable-libqrencode",
    "quirc": "--enable-libquirc",
}


# ---- helpers ---------------------------------------------------------------


def _have(bin_: str) -> None:
    if shutil.which(bin_) is None:
        print(f"error: {bin_!r} not found on PATH", file=sys.stderr)
        sys.exit(2)


def _list_filters() -> set[str]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        # Rows look like: " T.. delogo           V->V  ..."
        parts = line.split()
        if len(parts) >= 3 and parts[0].endswith(".."):
            names.add(parts[1])
        elif len(parts) >= 2:
            # Fallback tolerant parse.
            names.add(parts[1] if len(parts[0]) <= 4 else parts[0])
    return names


def _run(
    cmd: list[str], *, dry_run: bool, verbose: bool
) -> subprocess.CompletedProcess:
    if verbose or dry_run:
        pretty = " ".join(shlex.quote(c) for c in cmd)
        prefix = "DRY RUN: " if dry_run else "+ "
        print(prefix + pretty, file=sys.stderr)
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _filter_present(name: str, available: set[str]) -> None:
    if name not in available:
        flag = GATED_FILTERS.get(name, "(unknown)")
        print(
            f"error: filter {name!r} not available in this ffmpeg build "
            f"(requires {flag}).",
            file=sys.stderr,
        )
        print(
            "Run `ocrlogo.py check-build` to see what your build has.",
            file=sys.stderr,
        )
        sys.exit(3)


def _escape_filter_value(v: str) -> str:
    """Escape a string to embed into a filter arg."""
    return v.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


# ---- subcommand: check-build ----------------------------------------------


def cmd_check_build(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    available = _list_filters()
    width = max(len(n) for n in GATED_FILTERS)
    print(f"{'filter'.ljust(width)}  present  build flag")
    print(f"{'-' * width}  -------  ----------")
    missing: list[str] = []
    for name, flag in GATED_FILTERS.items():
        ok = name in available
        mark = "yes" if ok else "NO "
        print(f"{name.ljust(width)}  {mark}      {flag}")
        if not ok:
            missing.append(name)
    if missing:
        print(
            "\nmissing filters: "
            + ", ".join(missing)
            + "\nRebuild ffmpeg with the listed flags or fall back to OS tools "
            "(tesseract, zbarimg, qrencode CLI) on extracted frames.",
            file=sys.stderr,
        )
        return 1
    return 0


# ---- subcommand: ocr -------------------------------------------------------


def cmd_ocr(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    available = _list_filters()
    _filter_present("ocr", available)

    ocr_opts: list[str] = []
    if args.datapath:
        ocr_opts.append(f"datapath={_escape_filter_value(args.datapath)}")
    ocr_opts.append(f"language={args.lang}")
    if args.whitelist:
        ocr_opts.append(f"whitelist={_escape_filter_value(args.whitelist)}")
    if args.blacklist:
        ocr_opts.append(f"blacklist={_escape_filter_value(args.blacklist)}")

    ocr_filter = "ocr=" + ":".join(ocr_opts) if ocr_opts else "ocr"

    if args.output == "-":
        metadata = "metadata=mode=print"
    else:
        metadata = f"metadata=mode=print:file={_escape_filter_value(args.output)}"

    vf_parts: list[str] = []
    if args.fps:
        vf_parts.append(f"fps={args.fps}")
    vf_parts += [ocr_filter, metadata]
    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i",
        args.input,
        "-vf",
        vf,
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    if args.output == "-":
        # Filter 'metadata=mode=print' without file= writes to stdout.
        sys.stdout.write(result.stdout)
    else:
        # File was written by ffmpeg; nothing else to echo.
        if args.verbose:
            print(f"wrote OCR metadata to {args.output}", file=sys.stderr)
    return result.returncode


# ---- subcommand: delogo ----------------------------------------------------


def _parse_rect(s: str) -> tuple[int, int, int, int]:
    parts = s.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("rect must be X,Y,W,H")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError as e:
        raise argparse.ArgumentTypeError("rect values must be integers") from e
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("rect width and height must be > 0")
    return x, y, w, h


def _encoder_flags(args: argparse.Namespace) -> list[str]:
    return [
        "-c:v",
        args.vcodec,
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-c:a",
        "copy",
    ]


def cmd_delogo(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    _filter_present("delogo", _list_filters())
    x, y, w, h = args.rect
    show = 1 if args.show else 0
    vf = f"delogo=x={x}:y={y}:w={w}:h={h}:band={args.band}:show={show}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vf",
        vf,
        *_encoder_flags(args),
        args.output,
    ]
    r = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return r.returncode


# ---- subcommand: removelogo ------------------------------------------------


def cmd_removelogo(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    _filter_present("removelogo", _list_filters())
    vf = f"removelogo={_escape_filter_value(args.mask)}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vf",
        vf,
        *_encoder_flags(args),
        args.output,
    ]
    r = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return r.returncode


# ---- subcommand: find-cover ------------------------------------------------


def cmd_find_cover(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    available = _list_filters()
    _filter_present("find_rect", available)
    _filter_present("cover_rect", available)

    find = f"find_rect=object={_escape_filter_value(args.reference)}:threshold={args.threshold}"
    if args.mipmaps is not None:
        find += f":mipmaps={args.mipmaps}"
    if args.discard:
        find += ":discard=1"

    if args.cover == "blur":
        cover = "cover_rect=mode=blur"
    else:
        if not args.cover_image:
            print("error: --cover image requires --cover-image PATH", file=sys.stderr)
            return 2
        cover = f"cover_rect=cover={_escape_filter_value(args.cover_image)}:mode=cover"

    vf = f"{find},{cover}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vf",
        vf,
        *_encoder_flags(args),
        args.output,
    ]
    r = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return r.returncode


# ---- subcommand: qr-decode -------------------------------------------------


def cmd_qr_decode(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    _filter_present("quirc", _list_filters())
    vf_parts: list[str] = []
    if args.fps:
        vf_parts.append(f"fps={args.fps}")
    vf_parts += ["quirc", "metadata=mode=print"]
    vf = ",".join(vf_parts)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i",
        args.input,
        "-vf",
        vf,
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return 0
    # Forward lines that look like QR payload / count / corner metadata.
    for line in result.stdout.splitlines():
        if "lavfi.quirc" in line:
            print(line)
    return result.returncode


# ---- subcommand: qr-encode -------------------------------------------------


def cmd_qr_encode(args: argparse.Namespace) -> int:
    _have("ffmpeg")
    _filter_present("qrencode", _list_filters())
    size_expr = (
        f"w*{args.size}"
        if "." in str(args.size) or float(args.size) < 1
        else str(args.size)
    )
    text_escaped = args.text.replace("\\", "\\\\").replace("'", "\\'")
    opts = [
        f"text='{text_escaped}'",
        f"q={size_expr}",
        f"x={args.x}",
        f"y={args.y}",
        f"level={args.level}",
    ]
    vf = "qrencode=" + ":".join(opts)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-y" if args.overwrite else "-n",
        "-i",
        args.input,
        "-vf",
        vf,
        *_encoder_flags(args),
        args.output,
    ]
    r = _run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    return r.returncode


# ---- argparse --------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run", action="store_true", help="print the ffmpeg command and exit"
    )
    p.add_argument(
        "--verbose", action="store_true", help="echo the ffmpeg command before running"
    )


def _add_encoder(p: argparse.ArgumentParser) -> None:
    p.add_argument("--vcodec", default="libx264", help="video codec (default libx264)")
    p.add_argument("--crf", type=int, default=20, help="x264/x265 CRF (default 20)")
    p.add_argument("--preset", default="medium", help="encoder preset (default medium)")
    p.add_argument(
        "--overwrite", action="store_true", help="pass -y (overwrite output)"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ocrlogo.py",
        description="OCR, logo removal, rectangle and QR operations for ffmpeg.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser(
        "check-build", help="report which filters are in this ffmpeg build"
    )
    _add_common(pc)
    pc.set_defaults(func=cmd_check_build)

    po = sub.add_parser("ocr", help="run the ocr filter and capture lavfi.ocr.text")
    po.add_argument("--input", "-i", required=True, help="input media file")
    po.add_argument("--lang", default="eng", help="Tesseract language (default eng)")
    po.add_argument(
        "--datapath", default=None, help="tessdata directory (default: build-default)"
    )
    po.add_argument("--whitelist", default=None, help="character whitelist")
    po.add_argument("--blacklist", default=None, help="character blacklist")
    po.add_argument(
        "--fps", default=None, help="pre-decimate to N frames per second before OCR"
    )
    po.add_argument(
        "--output",
        "-o",
        default="-",
        help="metadata file path ('-' for stdout, default)",
    )
    _add_common(po)
    po.set_defaults(func=cmd_ocr)

    pd = sub.add_parser("delogo", help="soft-erase a known rectangle")
    pd.add_argument("--input", "-i", required=True)
    pd.add_argument("--output", "-o", required=True)
    pd.add_argument(
        "--rect", type=_parse_rect, required=True, help="X,Y,W,H (integers)"
    )
    pd.add_argument("--band", type=int, default=1, help="edge extension (default 1)")
    pd.add_argument("--show", action="store_true", help="draw green outline for tuning")
    _add_encoder(pd)
    _add_common(pd)
    pd.set_defaults(func=cmd_delogo)

    pr = sub.add_parser("removelogo", help="erase logo pixels via an alpha-mask PNG")
    pr.add_argument("--input", "-i", required=True)
    pr.add_argument("--output", "-o", required=True)
    pr.add_argument(
        "--mask",
        required=True,
        help="PNG mask, same resolution as video, white=logo, black=keep",
    )
    _add_encoder(pr)
    _add_common(pr)
    pr.set_defaults(func=cmd_removelogo)

    pf = sub.add_parser(
        "find-cover", help="find a reference image, cover it with blur or an image"
    )
    pf.add_argument("--input", "-i", required=True)
    pf.add_argument("--output", "-o", required=True)
    pf.add_argument(
        "--reference",
        required=True,
        help="gray8 reference image (.pgm or 8-bit gray PNG)",
    )
    pf.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="match threshold 0-1, lower=stricter (default 0.3)",
    )
    pf.add_argument(
        "--mipmaps", type=int, default=None, help="pyramid depth (default 3)"
    )
    pf.add_argument(
        "--discard", action="store_true", help="drop frames without a match"
    )
    pf.add_argument(
        "--cover",
        choices=["blur", "image"],
        default="blur",
        help="cover mode (default blur)",
    )
    pf.add_argument(
        "--cover-image",
        default=None,
        help="yuv420 image to patch over the rect (when --cover image)",
    )
    _add_encoder(pf)
    _add_common(pf)
    pf.set_defaults(func=cmd_find_cover)

    pq = sub.add_parser("qr-decode", help="identify and decode QR codes via quirc")
    pq.add_argument("--input", "-i", required=True)
    pq.add_argument("--fps", default=None, help="pre-decimate to N frames per second")
    _add_common(pq)
    pq.set_defaults(func=cmd_qr_decode)

    pe = sub.add_parser("qr-encode", help="overlay a QR code via qrencode")
    pe.add_argument("--input", "-i", required=True)
    pe.add_argument("--output", "-o", required=True)
    pe.add_argument("--text", required=True, help="QR payload text")
    pe.add_argument(
        "--size",
        default="0.25",
        help="QR size: fraction of video width (e.g. 0.25) or pixels (e.g. 128)",
    )
    pe.add_argument("--x", default="20", help="x position expression (default 20)")
    pe.add_argument("--y", default="20", help="y position expression (default 20)")
    pe.add_argument(
        "--level",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="error correction (default M)",
    )
    _add_encoder(pe)
    _add_common(pe)
    pe.set_defaults(func=cmd_qr_encode)

    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
