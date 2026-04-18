#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
AI stem separation helper for Demucs and Spleeter.

Subcommands:
    check                   Report demucs + spleeter availability and GPU status.
    split                   Full stem separation (2/4/6 stems).
    karaoke                 2-stem split, write vocals and backing to explicit paths.
    vocals-only             Write only the vocals stem.
    backing-only            Write only the no-vocals (instrumental) stem.

Global flags:
    --dry-run               Print the command(s) that would run, do nothing.
    --verbose               Echo commands as they run (to stderr).

Examples:
    stems.py check
    stems.py split --input song.mp3 --outdir out --stems 4 --model htdemucs_ft
    stems.py split --input song.mp3 --outdir out --tool spleeter --stems 2
    stems.py karaoke --input song.mp3 --output-vocals vox.wav --output-backing inst.wav
    stems.py vocals-only --input song.mp3 --output vox.wav --device cpu
    stems.py backing-only --input song.mp3 --output inst.wav --model htdemucs_ft

Stdlib only. Non-interactive.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[stems] {msg}", file=sys.stderr)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    printable = " ".join(_quote(a) for a in cmd)
    if dry_run or verbose:
        print(f"$ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def _quote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _detect_gpu() -> dict:
    """Best-effort GPU detection without importing torch."""
    info = {"cuda": False, "mps": False, "nvidia_smi": False, "details": ""}
    if _which("nvidia-smi"):
        info["nvidia_smi"] = True
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            ).strip()
            if out:
                info["cuda"] = True
                info["details"] = out
        except Exception:
            pass
    if sys.platform == "darwin":
        # Apple Silicon -> MPS likely available if torch is installed.
        try:
            uname = subprocess.check_output(
                ["uname", "-m"], text=True, timeout=2
            ).strip()
            if uname in ("arm64", "aarch64"):
                info["mps"] = True
        except Exception:
            pass
    return info


def _module_available(mod: str) -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def _cli_available(name: str) -> bool:
    return _which(name) is not None


# ---------------------------------------------------------------------------
# Demucs command builders
# ---------------------------------------------------------------------------


def _demucs_base(
    input_path: Path,
    outdir: Path,
    model: str | None,
    device: str | None,
    two_stems: str | None,
    extra: list[str] | None = None,
) -> list[str]:
    cmd: list[str] = ["demucs"]
    if model:
        cmd += ["-n", model]
    if device:
        cmd += ["--device", device]
    if two_stems:
        cmd += ["--two-stems", two_stems]
    cmd += ["-o", str(outdir)]
    if extra:
        cmd += extra
    cmd.append(str(input_path))
    return cmd


def _demucs_output_dir(outdir: Path, model: str, input_path: Path) -> Path:
    """Demucs writes to <outdir>/<model>/<stem_of_input>/."""
    return outdir / model / input_path.stem


def _default_demucs_model(stems: int) -> str:
    if stems == 6:
        return "htdemucs_6s"
    return "htdemucs"


# ---------------------------------------------------------------------------
# Spleeter command builders
# ---------------------------------------------------------------------------


def _spleeter_cmd(
    input_path: Path,
    outdir: Path,
    stems: int,
) -> list[str]:
    preset = {2: "spleeter:2stems", 4: "spleeter:4stems", 5: "spleeter:5stems"}.get(
        stems
    )
    if preset is None:
        raise SystemExit(f"spleeter supports --stems 2/4/5, got {stems}")
    return ["spleeter", "separate", "-p", preset, "-o", str(outdir), str(input_path)]


# ---------------------------------------------------------------------------
# Subcommand: check
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    info: dict = {}
    info["demucs_cli"] = _cli_available("demucs")
    info["demucs_module"] = _module_available("demucs")
    info["spleeter_cli"] = _cli_available("spleeter")
    info["spleeter_module"] = _module_available("spleeter")
    info["ffmpeg"] = _cli_available("ffmpeg")
    info["python"] = sys.version.split()[0]
    info["platform"] = sys.platform
    info["gpu"] = _detect_gpu()

    demucs_ok = info["demucs_cli"] or info["demucs_module"]
    spleeter_ok = info["spleeter_cli"] or info["spleeter_module"]
    info["any_tool_available"] = demucs_ok or spleeter_ok
    info["recommended"] = (
        "demucs" if demucs_ok else ("spleeter" if spleeter_ok else "none")
    )

    print(json.dumps(info, indent=2))
    return 0 if info["any_tool_available"] else 1


# ---------------------------------------------------------------------------
# Subcommand: split
# ---------------------------------------------------------------------------


def cmd_split(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    tool = args.tool
    if tool == "demucs":
        if not (_cli_available("demucs") or _module_available("demucs")):
            print("error: demucs not installed. `pip install demucs`", file=sys.stderr)
            return 3

        stems = int(args.stems)
        model = args.model or _default_demucs_model(stems)
        two_stems = "vocals" if stems == 2 else None

        extra: list[str] = []
        if args.flac:
            extra.append("--flac")
        if args.mp3:
            extra.append("--mp3")
        if args.int24:
            extra.append("--int24")
        if args.shifts:
            extra += ["--shifts", str(args.shifts)]
        if args.overlap is not None:
            extra += ["--overlap", str(args.overlap)]
        if args.segment is not None:
            extra += ["--segment", str(args.segment)]
        if args.jobs is not None:
            extra += ["--jobs", str(args.jobs)]

        cmd = _demucs_base(input_path, outdir, model, args.device, two_stems, extra)
        rc = _run(cmd, args.dry_run, args.verbose)
        if rc == 0 and not args.dry_run:
            out = _demucs_output_dir(outdir, model, input_path)
            _log(f"stems written under: {out}", True)
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "tool": "demucs",
                        "model": model,
                        "stems": stems,
                        "output_dir": str(out),
                    },
                    indent=2,
                )
            )
        return rc

    if tool == "spleeter":
        if not (_cli_available("spleeter") or _module_available("spleeter")):
            print(
                "error: spleeter not installed. `pip install spleeter`", file=sys.stderr
            )
            return 3
        cmd = _spleeter_cmd(input_path, outdir, int(args.stems))
        rc = _run(cmd, args.dry_run, args.verbose)
        if rc == 0 and not args.dry_run:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "tool": "spleeter",
                        "stems": int(args.stems),
                        "output_dir": str(outdir / input_path.stem),
                    },
                    indent=2,
                )
            )
        return rc

    print(f"error: unknown tool: {tool}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Subcommand: karaoke / vocals-only / backing-only
# ---------------------------------------------------------------------------


def _run_two_stems(
    input_path: Path,
    model: str,
    device: str | None,
    shifts: int | None,
    dry_run: bool,
    verbose: bool,
) -> tuple[int, Path | None]:
    """Run demucs --two-stems vocals into a tmp dir. Return (rc, stem_dir)."""
    if not (_cli_available("demucs") or _module_available("demucs")):
        print("error: demucs not installed. `pip install demucs`", file=sys.stderr)
        return 3, None

    tmp = Path(tempfile.mkdtemp(prefix="demucs_"))
    extra: list[str] = []
    if shifts:
        extra += ["--shifts", str(shifts)]
    cmd = _demucs_base(input_path, tmp, model, device, "vocals", extra)
    rc = _run(cmd, dry_run, verbose)
    if rc != 0:
        return rc, None
    if dry_run:
        return 0, None
    stem_dir = _demucs_output_dir(tmp, model, input_path)
    return rc, stem_dir


def _copy_stem(stem_dir: Path, stem_name: str, dest: Path, verbose: bool) -> int:
    # demucs writes .wav by default; tolerate .flac/.mp3 too.
    for ext in (".wav", ".flac", ".mp3"):
        candidate = stem_dir / f"{stem_name}{ext}"
        if candidate.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, dest)
            _log(f"{candidate} -> {dest}", verbose)
            return 0
    print(
        f"error: expected stem {stem_name} not found under {stem_dir}", file=sys.stderr
    )
    return 4


def cmd_karaoke(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2
    model = args.model or "htdemucs"
    rc, stem_dir = _run_two_stems(
        input_path, model, args.device, args.shifts, args.dry_run, args.verbose
    )
    if rc != 0 or args.dry_run:
        return rc
    assert stem_dir is not None
    rc1 = _copy_stem(
        stem_dir,
        "vocals",
        Path(args.output_vocals).expanduser().resolve(),
        args.verbose,
    )
    rc2 = _copy_stem(
        stem_dir,
        "no_vocals",
        Path(args.output_backing).expanduser().resolve(),
        args.verbose,
    )
    shutil.rmtree(stem_dir.parent.parent, ignore_errors=True)
    rc = rc1 or rc2
    if rc == 0:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "vocals": args.output_vocals,
                    "backing": args.output_backing,
                    "model": model,
                },
                indent=2,
            )
        )
    return rc


def _single_stem(args: argparse.Namespace, which: str) -> int:
    """which = 'vocals' or 'no_vocals'."""
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2
    model = args.model or "htdemucs"
    rc, stem_dir = _run_two_stems(
        input_path, model, args.device, args.shifts, args.dry_run, args.verbose
    )
    if rc != 0 or args.dry_run:
        return rc
    assert stem_dir is not None
    rc = _copy_stem(
        stem_dir, which, Path(args.output).expanduser().resolve(), args.verbose
    )
    shutil.rmtree(stem_dir.parent.parent, ignore_errors=True)
    if rc == 0:
        print(
            json.dumps(
                {"status": "ok", "stem": which, "output": args.output, "model": model},
                indent=2,
            )
        )
    return rc


def cmd_vocals_only(args: argparse.Namespace) -> int:
    return _single_stem(args, "vocals")


def cmd_backing_only(args: argparse.Namespace) -> int:
    return _single_stem(args, "no_vocals")


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run", action="store_true", help="Print commands without running them"
    )
    p.add_argument(
        "--verbose", action="store_true", help="Echo progress / commands to stderr"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stems.py",
        description="Demucs / Spleeter stem separation helper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    pc = sub.add_parser("check", help="Report tool availability and GPU state.")
    _add_common(pc)
    pc.set_defaults(func=cmd_check)

    # split
    ps = sub.add_parser("split", help="Full stem separation (2/4/6 stems).")
    ps.add_argument("--input", required=True)
    ps.add_argument("--outdir", required=True)
    ps.add_argument("--tool", choices=["demucs", "spleeter"], default="demucs")
    ps.add_argument(
        "--model",
        default=None,
        help="Demucs model name (htdemucs / htdemucs_ft / "
        "htdemucs_6s / mdx_extra / mdx_q). Ignored for "
        "spleeter.",
    )
    ps.add_argument("--stems", type=int, choices=[2, 4, 5, 6], default=4)
    ps.add_argument("--device", choices=["cuda", "cpu", "mps"], default=None)
    ps.add_argument("--flac", action="store_true")
    ps.add_argument("--mp3", action="store_true")
    ps.add_argument("--int24", action="store_true")
    ps.add_argument("--shifts", type=int, default=None)
    ps.add_argument("--overlap", type=float, default=None)
    ps.add_argument("--segment", type=int, default=None)
    ps.add_argument("--jobs", type=int, default=None)
    _add_common(ps)
    ps.set_defaults(func=cmd_split)

    # karaoke
    pk = sub.add_parser("karaoke", help="2-stem karaoke split with explicit outputs.")
    pk.add_argument("--input", required=True)
    pk.add_argument("--output-vocals", required=True)
    pk.add_argument("--output-backing", required=True)
    pk.add_argument("--model", default=None)
    pk.add_argument("--device", choices=["cuda", "cpu", "mps"], default=None)
    pk.add_argument("--shifts", type=int, default=None)
    _add_common(pk)
    pk.set_defaults(func=cmd_karaoke)

    # vocals-only
    pv = sub.add_parser("vocals-only", help="Write only the vocals stem.")
    pv.add_argument("--input", required=True)
    pv.add_argument("--output", required=True)
    pv.add_argument("--model", default=None)
    pv.add_argument("--device", choices=["cuda", "cpu", "mps"], default=None)
    pv.add_argument("--shifts", type=int, default=None)
    _add_common(pv)
    pv.set_defaults(func=cmd_vocals_only)

    # backing-only
    pb = sub.add_parser(
        "backing-only", help="Write only the no-vocals (instrumental) stem."
    )
    pb.add_argument("--input", required=True)
    pb.add_argument("--output", required=True)
    pb.add_argument("--model", default=None)
    pb.add_argument("--device", choices=["cuda", "cpu", "mps"], default=None)
    pb.add_argument("--shifts", type=int, default=None)
    _add_common(pb)
    pb.set_defaults(func=cmd_backing_only)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
