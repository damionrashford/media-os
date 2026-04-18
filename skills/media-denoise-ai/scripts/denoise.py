#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
AI audio denoiser / restorer helper (commercial-safe, open-source only).

Models supported:
    deepfilternet   DeepFilterNet (MIT) - real-time full-band speech denoise
    rnnoise         RNNoise via ffmpeg arnndn (BSD-3) - already in ffmpeg
    resemble        Resemble Enhance (Apache 2.0) - denoise + dereverb + BWE

Subcommands:
    check                    Report installed backends.
    install <model>          Print / run pip install line for a model.
    denoise                  Single-file denoise with a chosen model.
    enhance                  Full restoration via Resemble Enhance (denoise + dereverb + BWE).
    batch                    Walk an input directory, denoise each file, mirror tree.

Global flags (every subcommand):
    --dry-run                Print the command(s) that would run, do nothing.
    --verbose                Echo commands / progress to stderr.

Examples:
    denoise.py check
    denoise.py install deepfilternet
    denoise.py denoise --model deepfilternet --in noisy.wav --out clean.wav
    denoise.py denoise --model rnnoise --in noisy.wav --out clean.wav \\
                       --rnn-model cb.rnnn
    denoise.py enhance --in muffled.wav --out clean.wav
    denoise.py batch --model deepfilternet --in-dir raw/ --out-dir clean/

Stdlib only. Non-interactive. No interactive prompts anywhere.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_MODELS = ["deepfilternet", "rnnoise", "resemble"]

PIP_LINES = {
    "deepfilternet": "pip install deepfilternet soundfile",
    "resemble": "pip install resemble-enhance soundfile",
    "rnnoise": "# ffmpeg arnndn ships with ffmpeg. Download a model:\n"
    "curl -Lo cb.rnnn https://raw.githubusercontent.com/"
    "GregorR/rnnoise-models/master/conjoined-burgers-2018-08-28/"
    "cb.rnnn",
}

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[denoise] {msg}", file=sys.stderr)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _module_available(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def _quote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    printable = " ".join(_quote(a) for a in cmd)
    if dry_run or verbose:
        print(f"$ {printable}", file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# check / install
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    info: dict = {"python": sys.version.split()[0], "platform": sys.platform}
    info["deepfilternet_module"] = _module_available(
        "deepfilternet"
    ) or _module_available("df")
    info["deepfilternet_cli"] = _which("deep-filter") is not None
    info["resemble_module"] = _module_available("resemble_enhance")
    info["ffmpeg"] = _which("ffmpeg") is not None
    # arnndn is built into ffmpeg; presence is implicit if ffmpeg has it.
    info["ffmpeg_arnndn"] = False
    if info["ffmpeg"]:
        try:
            out = subprocess.check_output(
                [_which("ffmpeg"), "-hide_banner", "-filters"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
            )
            info["ffmpeg_arnndn"] = " arnndn " in out
        except Exception:
            pass
    print(json.dumps(info, indent=2))
    any_ok = (
        info["deepfilternet_module"]
        or info["deepfilternet_cli"]
        or info["resemble_module"]
        or info["ffmpeg_arnndn"]
    )
    return 0 if any_ok else 1


def cmd_install(args: argparse.Namespace) -> int:
    model = args.model.lower()
    if model not in PIP_LINES:
        print(
            f"error: unknown model '{model}'. "
            f"Options: {', '.join(SUPPORTED_MODELS)}",
            file=sys.stderr,
        )
        return 2
    pip_line = PIP_LINES[model]
    print(f"# Install line for {model}:")
    print(pip_line)
    if args.run and not pip_line.startswith("#"):
        return _run(pip_line.split(), args.dry_run, args.verbose)
    return 0


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


def _denoise_deepfilternet(
    in_path: Path, out_path: Path, verbose: bool, dry_run: bool
) -> int:
    """Prefer the Rust binary (deep-filter) when present; otherwise Python."""
    binary = _which("deep-filter")
    _ensure_parent(out_path)
    if binary:
        # The Rust CLI writes to a directory with matching file name.
        tmp_dir = out_path.parent / ".dfn_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        cmd = [binary, "-o", str(tmp_dir), str(in_path)]
        rc = _run(cmd, dry_run, verbose)
        if rc != 0 or dry_run:
            return rc
        produced = tmp_dir / in_path.name
        if produced.exists():
            shutil.move(str(produced), str(out_path))
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return 0

    # Python wrapper fallback.
    try:
        from df.enhance import enhance, init_df, load_audio, save_audio  # type: ignore
    except ImportError:
        try:
            from deepfilternet import enhance, init_df, load_audio, save_audio  # type: ignore
        except ImportError as e:
            print(f"error: {e}. Run: {PIP_LINES['deepfilternet']}", file=sys.stderr)
            return 3

    _log(f"deepfilternet (python) in={in_path} out={out_path}", verbose)
    if dry_run:
        return 0
    model, df_state, _ = init_df()
    audio, _ = load_audio(str(in_path), sr=df_state.sr())
    enhanced = enhance(model, df_state, audio)
    save_audio(str(out_path), enhanced, df_state.sr())
    return 0


def _denoise_rnnoise_ffmpeg(
    in_path: Path, out_path: Path, rnn_model: str | None, verbose: bool, dry_run: bool
) -> int:
    ffmpeg = _which("ffmpeg")
    if ffmpeg is None:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        return 3
    af = "arnndn"
    if rnn_model:
        af = f"arnndn=m={rnn_model}"
    _ensure_parent(out_path)
    cmd = [ffmpeg, "-y", "-i", str(in_path), "-af", af, str(out_path)]
    return _run(cmd, dry_run, verbose)


def _denoise_resemble(
    in_path: Path,
    out_path: Path,
    enhance_mode: bool,
    nfe_steps: int,
    solver: str,
    strength: float,
    verbose: bool,
    dry_run: bool,
) -> int:
    try:
        import soundfile as sf  # type: ignore
        import torch  # type: ignore
        from resemble_enhance.enhancer.inference import denoise, enhance  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['resemble']}", file=sys.stderr)
        return 3

    _log(
        f"resemble-enhance mode={'enhance' if enhance_mode else 'denoise'} "
        f"nfe={nfe_steps} solver={solver} strength={strength}",
        verbose,
    )
    if dry_run:
        return 0

    device = (
        "cuda"
        if torch.cuda.is_available()
        else (
            "mps"
            if getattr(torch.backends, "mps", None)
            and torch.backends.mps.is_available()
            else "cpu"
        )
    )
    wav, sr = sf.read(str(in_path))
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    wav_t = torch.as_tensor(wav, dtype=torch.float32).to(device)

    if enhance_mode:
        out_wav, out_sr = enhance(
            wav_t,
            sr,
            device=device,
            nfe=nfe_steps,
            solver=solver,
            lambd=strength,
            tau=0.5,
        )
    else:
        out_wav, out_sr = denoise(wav_t, sr, device=device)

    _ensure_parent(out_path)
    sf.write(str(out_path), out_wav.cpu().numpy(), out_sr)
    return 0


# ---------------------------------------------------------------------------
# denoise / enhance / batch
# ---------------------------------------------------------------------------


def cmd_denoise(args: argparse.Namespace) -> int:
    in_path = Path(args.in_path).expanduser().resolve()
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2
    out_path = Path(args.out).expanduser().resolve()
    model = args.model.lower()

    if model == "deepfilternet":
        return _denoise_deepfilternet(in_path, out_path, args.verbose, args.dry_run)
    if model == "rnnoise":
        return _denoise_rnnoise_ffmpeg(
            in_path, out_path, args.rnn_model, args.verbose, args.dry_run
        )
    if model == "resemble":
        return _denoise_resemble(
            in_path,
            out_path,
            enhance_mode=False,
            nfe_steps=64,
            solver="midpoint",
            strength=0.5,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
    print(f"error: unknown model '{model}'", file=sys.stderr)
    return 2


def cmd_enhance(args: argparse.Namespace) -> int:
    in_path = Path(args.in_path).expanduser().resolve()
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2
    out_path = Path(args.out).expanduser().resolve()
    return _denoise_resemble(
        in_path,
        out_path,
        enhance_mode=True,
        nfe_steps=int(args.nfe_steps),
        solver=args.solver,
        strength=float(args.strength),
        verbose=args.verbose,
        dry_run=args.dry_run,
    )


def cmd_batch(args: argparse.Namespace) -> int:
    in_dir = Path(args.in_dir).expanduser().resolve()
    if not in_dir.is_dir():
        print(f"error: input dir not found: {in_dir}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    model = args.model.lower()

    count = 0
    errors = 0
    for src in sorted(in_dir.rglob("*")):
        if not src.is_file() or src.suffix.lower() not in AUDIO_EXTS:
            continue
        rel = src.relative_to(in_dir)
        dst = out_dir / rel
        if dst.exists() and not args.overwrite:
            _log(f"skip existing {dst}", args.verbose)
            continue
        _log(f"batch {rel}", args.verbose or args.dry_run)

        if model == "deepfilternet":
            rc = _denoise_deepfilternet(src, dst, args.verbose, args.dry_run)
        elif model == "rnnoise":
            rc = _denoise_rnnoise_ffmpeg(
                src, dst, args.rnn_model, args.verbose, args.dry_run
            )
        elif model == "resemble":
            rc = _denoise_resemble(
                src,
                dst,
                enhance_mode=False,
                nfe_steps=64,
                solver="midpoint",
                strength=0.5,
                verbose=args.verbose,
                dry_run=args.dry_run,
            )
        else:
            print(f"error: unknown model '{model}'", file=sys.stderr)
            return 2
        if rc != 0:
            errors += 1
            print(f"error processing {rel}: rc={rc}", file=sys.stderr)
        else:
            count += 1

    print(
        json.dumps(
            {
                "status": "ok" if errors == 0 else "partial",
                "processed": count,
                "errors": errors,
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    return 0 if errors == 0 else 4


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
        prog="denoise.py",
        description="AI audio denoise + restore (commercial-safe, open-source only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("check", help="Report backend availability.")
    _add_common(pc)
    pc.set_defaults(func=cmd_check)

    pi = sub.add_parser("install", help="Print / run pip install line for a model.")
    pi.add_argument("model", help=f"One of: {', '.join(SUPPORTED_MODELS)}")
    pi.add_argument(
        "--run", action="store_true", help="Actually execute the pip install"
    )
    _add_common(pi)
    pi.set_defaults(func=cmd_install)

    pd = sub.add_parser("denoise", help="Single-file denoise.")
    pd.add_argument("--model", required=True, choices=SUPPORTED_MODELS)
    pd.add_argument("--in", dest="in_path", required=True)
    pd.add_argument("--out", required=True)
    pd.add_argument(
        "--rnn-model",
        default=None,
        help="rnnoise: path to .rnnn model file for ffmpeg arnndn.",
    )
    _add_common(pd)
    pd.set_defaults(func=cmd_denoise)

    pe = sub.add_parser(
        "enhance",
        help="Full restoration (denoise + dereverb + bandwidth extension) "
        "via Resemble Enhance.",
    )
    pe.add_argument("--in", dest="in_path", required=True)
    pe.add_argument("--out", required=True)
    pe.add_argument(
        "--nfe-steps",
        type=int,
        default=64,
        help="Resemble Enhance sampler steps (default 64).",
    )
    pe.add_argument(
        "--solver", default="midpoint", choices=["midpoint", "euler", "rk4"]
    )
    pe.add_argument(
        "--strength",
        type=float,
        default=0.5,
        help="Enhancement strength lambda 0.0-1.0 (default 0.5).",
    )
    _add_common(pe)
    pe.set_defaults(func=cmd_enhance)

    pb = sub.add_parser("batch", help="Walk a dir, denoise each file.")
    pb.add_argument("--model", required=True, choices=SUPPORTED_MODELS)
    pb.add_argument("--in-dir", required=True)
    pb.add_argument("--out-dir", required=True)
    pb.add_argument("--rnn-model", default=None)
    pb.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-process files whose output already exists.",
    )
    _add_common(pb)
    pb.set_defaults(func=cmd_batch)

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
