#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
AI music generation helper (commercial-safe, open-source only).

Models supported:
    riffusion            Riffusion v1 (MIT) - spectrogram-diffusion
    yue                  YuE (Apache 2.0) - full song with vocals
    stable-audio-open    Stable Audio Open 1.0 (Stability Community License,
                         commercial use capped at $1M ARR)

Explicitly EXCLUDED (NOT commercial-safe):
    MusicGen / AudioCraft (CC-BY-NC weights)
    Suno / Udio (proprietary paid)
    Jukebox / MuseNet (research only)

Subcommands:
    check                    Report installed backends.
    install <model>          Print / run pip install line for a model.
    generate                 Generate music from a text prompt.
    continue                 Continue an existing audio clip.
    stems                    Split output into stems (handoff to media-demucs).

Global flags (every subcommand):
    --dry-run                Print the command(s) that would run, do nothing.
    --verbose                Echo commands / progress to stderr.

Examples:
    musicgen.py check
    musicgen.py install riffusion
    musicgen.py generate --model riffusion --prompt "lo-fi beat" \\
                         --duration 10 --out out.wav
    musicgen.py generate --model yue --prompt "indie rock with vocals" \\
                         --duration 90 --out song.wav
    musicgen.py continue --in sketch.wav --model stable-audio-open \\
                         --prompt "build up" --duration 15 --out extended.wav
    musicgen.py stems --in song.wav --out-dir stems/

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

SUPPORTED_MODELS = ["riffusion", "yue", "stable-audio-open"]

PIP_LINES = {
    "riffusion": "pip install diffusers transformers torch accelerate soundfile",
    "yue": "pip install transformers torch accelerate soundfile",
    "stable-audio-open": "pip install stable-audio-tools soundfile",
}

MODULE_CHECKS = {
    "riffusion": ["diffusers", "transformers"],
    "yue": ["transformers"],
    "stable-audio-open": ["stable_audio_tools"],
}

HF_REPOS = {
    "riffusion": "riffusion/riffusion-model-v1",
    "yue-en": "m-a-p/YuE-s1-7B-anneal-en-cot",
    "yue-zh": "m-a-p/YuE-s1-7B-anneal-zh-cot",
    "stable-audio-open": "stabilityai/stable-audio-open-1.0",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[musicgen] {msg}", file=sys.stderr)


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


# ---------------------------------------------------------------------------
# check / install
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    info: dict = {"python": sys.version.split()[0], "platform": sys.platform}
    for m, mods in MODULE_CHECKS.items():
        info[m] = all(_module_available(mod) for mod in mods)
    info["ffmpeg"] = _which("ffmpeg") is not None
    info["demucs"] = _which("demucs") is not None or _module_available("demucs")
    print(json.dumps(info, indent=2))
    return 0 if any(info[m] for m in SUPPORTED_MODELS) else 1


def cmd_install(args: argparse.Namespace) -> int:
    model = args.model.lower()
    if model not in PIP_LINES:
        print(
            f"error: unknown model '{model}'. Options: {', '.join(SUPPORTED_MODELS)}",
            file=sys.stderr,
        )
        return 2
    pip_line = PIP_LINES[model]
    print(f"# Install line for {model}:")
    print(pip_line)
    if args.run:
        return _run(pip_line.split(), args.dry_run, args.verbose)
    return 0


# ---------------------------------------------------------------------------
# Generation backends
# ---------------------------------------------------------------------------


def _generate_riffusion(
    prompt: str, duration: float, seed: int | None, out: Path, verbose: bool
) -> int:
    try:
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore
        import torch  # type: ignore
        from diffusers import DiffusionPipeline  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['riffusion']}", file=sys.stderr)
        return 3

    _log(f"riffusion prompt='{prompt[:60]}...' duration={duration}s", verbose)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = DiffusionPipeline.from_pretrained(
        HF_REPOS["riffusion"], custom_pipeline="riffusion/riffusion-model-v1"
    ).to(device)
    if seed is not None:
        generator = torch.Generator(device=device).manual_seed(seed)
    else:
        generator = None

    # Riffusion native window is ~5s at 512 pixel width.
    # For longer outputs, run iteratively and crossfade.
    chunk_dur = 5.0
    n_chunks = max(1, int(duration / chunk_dur + 0.999))
    chunks = []
    sr = 44100
    for i in range(n_chunks):
        out_spec = pipe(prompt=prompt, generator=generator).images[0]
        # Delegate spectrogram -> audio via pipe's built-in vocoder if present.
        # Most riffusion pipelines expose .audio output; fall back to manual.
        if hasattr(pipe, "spectrogram_image_to_audio"):
            audio = pipe.spectrogram_image_to_audio(out_spec)
        else:
            # Minimal fallback: treat the image as mel, Griffin-Lim reconstruct.
            from diffusers.pipelines.riffusion import spectrogram_to_audio  # type: ignore

            audio = spectrogram_to_audio(out_spec)
        chunks.append(np.asarray(audio, dtype=np.float32))
        _log(f"riffusion chunk {i+1}/{n_chunks} done", verbose)

    # Concatenate with ~50 ms crossfade between chunks.
    fade_samples = int(0.05 * sr)
    if len(chunks) == 1:
        combined = chunks[0]
    else:
        combined = chunks[0]
        for c in chunks[1:]:
            fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
            fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
            tail = combined[-fade_samples:] * fade_out
            head = c[:fade_samples] * fade_in
            combined = np.concatenate(
                [combined[:-fade_samples], tail + head, c[fade_samples:]]
            )

    # Trim to requested duration.
    combined = combined[: int(duration * sr)]
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), combined, sr)
    return 0


def _generate_yue(
    prompt: str,
    duration: float,
    seed: int | None,
    out: Path,
    load_in_4bit: bool,
    verbose: bool,
) -> int:
    try:
        import soundfile as sf  # type: ignore
        import torch  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['yue']}", file=sys.stderr)
        return 3

    repo = (
        HF_REPOS["yue-zh"]
        if any("\u4e00" <= ch <= "\u9fff" for ch in prompt)
        else HF_REPOS["yue-en"]
    )
    _log(f"yue repo={repo} prompt='{prompt[:60]}...'", verbose)

    kwargs = {"torch_dtype": torch.float16}
    if load_in_4bit:
        try:
            from transformers import BitsAndBytesConfig  # type: ignore

            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
        except ImportError:
            print(
                "warn: bitsandbytes not installed, falling back to fp16",
                file=sys.stderr,
            )

    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, **kwargs)
    if not load_in_4bit:
        model = model.to("cuda" if torch.cuda.is_available() else "cpu")

    if seed is not None:
        torch.manual_seed(seed)
    # YuE prompt structure: assumes caller embeds section markers as needed.
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    # Token budget for ~N seconds of audio (model-specific).
    max_tokens = min(int(duration * 50), 4000)
    gen = model.generate(
        **inputs, max_new_tokens=max_tokens, do_sample=True, temperature=0.9, top_p=0.95
    )
    # YuE decodes audio via its codec head — library-specific; abstract here.
    if hasattr(model, "decode_audio"):
        audio, sr = model.decode_audio(gen)
    else:
        print(
            "error: YuE model missing decode_audio method. Check model card "
            "at huggingface.co/m-a-p/YuE-s1-7B-anneal-en-cot for decode API.",
            file=sys.stderr,
        )
        return 4
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, sr)
    return 0


def _generate_stable_audio_open(
    prompt: str,
    duration: float,
    seed: int | None,
    out: Path,
    seed_audio: Path | None,
    verbose: bool,
) -> int:
    try:
        import soundfile as sf  # type: ignore
        import torch  # type: ignore
        from stable_audio_tools import get_pretrained_model  # type: ignore
        from stable_audio_tools.inference.generation import (
            generate_diffusion_cond,
        )  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['stable-audio-open']}", file=sys.stderr)
        return 3

    _log(f"stable-audio-open prompt='{prompt[:60]}...' duration={duration}s", verbose)
    model, model_config = get_pretrained_model(HF_REPOS["stable-audio-open"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    sample_rate = model_config["sample_rate"]
    if duration > 47:
        print("warn: stable-audio-open caps at ~47s; clamping.", file=sys.stderr)
        duration = 47
    sample_size = int(duration * sample_rate)

    conditioning = [
        {"prompt": prompt, "seconds_start": 0, "seconds_total": int(duration)}
    ]

    init_audio = None
    if seed_audio is not None and seed_audio.exists():
        import numpy as np  # type: ignore

        seed_wav, seed_sr = sf.read(str(seed_audio))
        if seed_sr != sample_rate:
            # Leave resampling to ffmpeg caller; warn for now.
            print(
                f"warn: seed audio sr={seed_sr} != model sr={sample_rate}",
                file=sys.stderr,
            )
        seed_tensor = torch.as_tensor(seed_wav.T, dtype=torch.float32, device=device)
        if seed_tensor.ndim == 1:
            seed_tensor = seed_tensor.unsqueeze(0)
        init_audio = (sample_rate, seed_tensor.unsqueeze(0))

    audio = generate_diffusion_cond(
        model,
        steps=100,
        cfg_scale=7,
        conditioning=conditioning,
        sample_size=sample_size,
        sigma_min=0.3,
        sigma_max=500,
        sampler_type="dpmpp-3m-sde",
        device=device,
        seed=seed or -1,
        init_audio=init_audio,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    # audio is [1, ch, samples] typically
    audio_np = audio.squeeze(0).cpu().numpy().T  # (samples, ch)
    sf.write(str(out), audio_np, sample_rate)
    return 0


# ---------------------------------------------------------------------------
# generate / continue / stems
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    model = args.model.lower()
    out = Path(args.out).expanduser().resolve()
    duration = float(args.duration)
    seed = int(args.seed) if args.seed is not None else None
    prompt = args.prompt

    _log(f"generate model={model} out={out}", args.verbose or args.dry_run)
    if args.dry_run:
        print(f"# would generate {duration}s with {model}", file=sys.stderr)
        return 0

    if model == "riffusion":
        return _generate_riffusion(prompt, duration, seed, out, args.verbose)
    if model == "yue":
        return _generate_yue(
            prompt, duration, seed, out, args.load_in_4bit, args.verbose
        )
    if model == "stable-audio-open":
        return _generate_stable_audio_open(
            prompt, duration, seed, out, None, args.verbose
        )
    print(f"error: unknown model '{model}'", file=sys.stderr)
    return 2


def cmd_continue(args: argparse.Namespace) -> int:
    model = args.model.lower()
    seed_audio = Path(args.in_path).expanduser().resolve()
    if not seed_audio.exists():
        print(f"error: seed audio not found: {seed_audio}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser().resolve()
    duration = float(args.duration)
    seed = int(args.seed) if args.seed is not None else None

    _log(
        f"continue model={model} seed={seed_audio} out={out}",
        args.verbose or args.dry_run,
    )
    if args.dry_run:
        print(
            f"# would continue {seed_audio.name} by {duration}s with {model}",
            file=sys.stderr,
        )
        return 0

    if model == "stable-audio-open":
        return _generate_stable_audio_open(
            args.prompt, duration, seed, out, seed_audio, args.verbose
        )
    if model == "riffusion":
        # Riffusion "continuation" = prompt re-use; no true conditioning on audio.
        print(
            "warn: riffusion does not condition on input audio; "
            "generating fresh clip with same prompt.",
            file=sys.stderr,
        )
        return _generate_riffusion(args.prompt, duration, seed, out, args.verbose)
    if model == "yue":
        print(
            "error: YuE continuation API is unstable. Use --model "
            "stable-audio-open for reliable continuation.",
            file=sys.stderr,
        )
        return 4
    print(f"error: unknown model '{model}'", file=sys.stderr)
    return 2


def cmd_stems(args: argparse.Namespace) -> int:
    in_path = Path(args.in_path).expanduser().resolve()
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Delegate to demucs CLI. The media-demucs skill provides the full wrapper.
    demucs = _which("demucs")
    if demucs is None and not _module_available("demucs"):
        print(
            "error: demucs not installed. `pip install demucs` "
            "or use media-demucs skill.",
            file=sys.stderr,
        )
        return 3

    cmd = [demucs or sys.executable, "-m", "demucs"] if demucs is None else [demucs]
    cmd += ["-o", str(out_dir), str(in_path)]
    return _run(cmd, args.dry_run, args.verbose)


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
        prog="musicgen.py",
        description="AI music generation (commercial-safe, open-source only).",
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

    pg = sub.add_parser("generate", help="Generate music from a text prompt.")
    pg.add_argument("--model", required=True, choices=SUPPORTED_MODELS)
    pg.add_argument("--prompt", required=True)
    pg.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Target duration in seconds (default 10)",
    )
    pg.add_argument("--seed", type=int, default=None)
    pg.add_argument(
        "--load-in-4bit",
        action="store_true",
        help="YuE only: load model in 4-bit (requires bitsandbytes)",
    )
    pg.add_argument("--out", required=True)
    _add_common(pg)
    pg.set_defaults(func=cmd_generate)

    pn = sub.add_parser("continue", help="Continue an existing audio clip.")
    pn.add_argument(
        "--in", dest="in_path", required=True, help="Seed audio file to continue"
    )
    pn.add_argument("--model", required=True, choices=SUPPORTED_MODELS)
    pn.add_argument("--prompt", required=True)
    pn.add_argument("--duration", type=float, default=10.0)
    pn.add_argument("--seed", type=int, default=None)
    pn.add_argument("--out", required=True)
    _add_common(pn)
    pn.set_defaults(func=cmd_continue)

    pst = sub.add_parser(
        "stems", help="Split a clip into stems " "(handoff to media-demucs)."
    )
    pst.add_argument("--in", dest="in_path", required=True)
    pst.add_argument("--out-dir", required=True)
    _add_common(pst)
    pst.set_defaults(func=cmd_stems)

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
