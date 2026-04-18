#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-whisper driver: ASR via whisper.cpp or faster-whisper, plus ffmpeg SRT mux/burn.

Subcommands:
    check          Report backend + GPU availability.
    transcribe     Audio/video -> SRT (+ optional word-level JSON).
    translate      Any language -> English SRT.
    srt-mux        Soft-mux SRT into MP4 (stream copy, mov_text).
    srt-burn       Hard-burn SRT into video (ffmpeg subtitles filter).

Global flags:
    --dry-run      Print commands / plan; do not execute.
    --verbose      Stream tool stdout/stderr and progress info.

Stdlib only. Non-interactive. Prepares a 16 kHz mono PCM-s16le WAV automatically
via ffmpeg if the input is not already that format.

Examples:
    uv run scripts/whisper.py check
    uv run scripts/whisper.py transcribe --input in.mp4 --output-srt out.srt \\
        --model base.en --lang en
    uv run scripts/whisper.py transcribe --input in.mp4 --output-srt out.srt \\
        --backend faster --model large-v3 --word-timestamps
    uv run scripts/whisper.py translate --input spanish.mp4 --output english.srt \\
        --model large-v3
    uv run scripts/whisper.py srt-mux  --video in.mp4 --srt out.srt --output tagged.mp4
    uv run scripts/whisper.py srt-burn --video in.mp4 --srt out.srt --output burned.mp4
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #

WAV_EXTS = {".wav"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".ts", ".m4v"}

WHISPER_CPP_MODEL_DIRS = [
    Path("/opt/homebrew/share/whisper.cpp/models"),
    Path("/usr/local/share/whisper.cpp/models"),
    Path.home() / ".cache/whisper.cpp/models",
    Path.home() / "whisper.cpp/models",
]


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def run(cmd: list[str], *, dry_run: bool, verbose: bool) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    if dry_run:
        print(f"[dry-run] {pretty}")
        return 0
    log(f"+ {pretty}", verbose)
    out = subprocess.run(cmd, check=False)
    return out.returncode


def ensure(path: Path, kind: str = "file") -> None:
    if not path.exists():
        die(f"{kind} not found: {path}")


# --------------------------------------------------------------------------- #
# Backend discovery
# --------------------------------------------------------------------------- #


@dataclass
class BackendInfo:
    whisper_cpp_bin: Optional[str]
    whisper_cpp_models_dir: Optional[Path]
    faster_whisper: bool
    faster_whisper_cuda: bool
    metal: bool  # whisper.cpp Metal (Apple Silicon)
    ffmpeg: Optional[str]
    ffprobe: Optional[str]


def find_whisper_cpp() -> Optional[str]:
    for name in ("whisper-cpp", "whisper-cli", "main"):
        p = which(name)
        if p:
            return p
    return None


def find_whisper_cpp_models() -> Optional[Path]:
    for d in WHISPER_CPP_MODEL_DIRS:
        if d.is_dir():
            return d
    return None


def check_faster_whisper() -> tuple[bool, bool]:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return (False, False)
    cuda = False
    try:
        import ctranslate2  # type: ignore

        cuda = bool(getattr(ctranslate2, "get_cuda_device_count", lambda: 0)())
    except Exception:
        cuda = False
    return (True, cuda)


def detect() -> BackendInfo:
    bin_path = find_whisper_cpp()
    metal = bool(bin_path) and sys.platform == "darwin"
    fw, fw_cuda = check_faster_whisper()
    return BackendInfo(
        whisper_cpp_bin=bin_path,
        whisper_cpp_models_dir=find_whisper_cpp_models(),
        faster_whisper=fw,
        faster_whisper_cuda=fw_cuda,
        metal=metal,
        ffmpeg=which("ffmpeg"),
        ffprobe=which("ffprobe"),
    )


# --------------------------------------------------------------------------- #
# WAV prep (16 kHz mono PCM-s16le via ffmpeg)
# --------------------------------------------------------------------------- #


def needs_wav_prep(path: Path) -> bool:
    # Always re-mux to guarantee 16 kHz mono; users may hand us wrong-SR wav.
    if path.suffix.lower() not in WAV_EXTS:
        return True
    # If it is already .wav, still re-mux unless probe confirms format.
    # Keep it simple: trust .wav only if ffprobe confirms.
    return True


def prepare_wav(input_path: Path, *, dry_run: bool, verbose: bool) -> Path:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        die("ffmpeg not found on PATH (needed to prepare 16 kHz mono WAV)")
    tmpdir = Path(tempfile.mkdtemp(prefix="mw-"))
    wav = tmpdir / (input_path.stem + ".16k.wav")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(wav),
    ]
    rc = run(cmd, dry_run=dry_run, verbose=verbose)
    if rc != 0 and not dry_run:
        die(f"ffmpeg failed to prepare 16 kHz mono WAV (rc={rc})")
    if dry_run:
        # Fabricate the path so downstream commands can still be printed.
        return wav
    if not wav.exists():
        die(f"expected WAV not produced: {wav}")
    return wav


# --------------------------------------------------------------------------- #
# whisper.cpp model resolution
# --------------------------------------------------------------------------- #


def resolve_cpp_model(model: str, info: BackendInfo) -> Path:
    # Accept absolute paths, names like "base.en", or "ggml-base.en.bin".
    p = Path(model)
    if p.is_absolute() and p.exists():
        return p
    candidates: list[Path] = []
    if info.whisper_cpp_models_dir:
        candidates.append(info.whisper_cpp_models_dir / model)
        if not model.startswith("ggml-"):
            candidates.append(info.whisper_cpp_models_dir / f"ggml-{model}.bin")
        if not model.endswith(".bin"):
            candidates.append(info.whisper_cpp_models_dir / f"{model}.bin")
    for c in candidates:
        if c.exists():
            return c
    searched = ", ".join(str(c) for c in candidates) or "(no model dir found)"
    die(
        f"whisper.cpp model not found for '{model}'. Searched: {searched}. "
        "Download with: bash /opt/homebrew/share/whisper.cpp/models/"
        f"download-ggml-model.sh {model}"
    )
    raise AssertionError("unreachable")  # for type-checkers


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    info = detect()
    out = {
        "ffmpeg": info.ffmpeg,
        "ffprobe": info.ffprobe,
        "whisper_cpp_bin": info.whisper_cpp_bin,
        "whisper_cpp_models_dir": (
            str(info.whisper_cpp_models_dir) if info.whisper_cpp_models_dir else None
        ),
        "whisper_cpp_metal": info.metal,
        "faster_whisper_installed": info.faster_whisper,
        "faster_whisper_cuda": info.faster_whisper_cuda,
        "platform": sys.platform,
    }
    print(json.dumps(out, indent=2))
    missing = []
    if not info.ffmpeg:
        missing.append("ffmpeg")
    if not info.whisper_cpp_bin and not info.faster_whisper:
        missing.append("whisper-cpp or faster-whisper")
    if missing:
        print(f"warning: missing: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


def _pick_backend(requested: str, info: BackendInfo) -> str:
    if requested == "cpp":
        if not info.whisper_cpp_bin:
            die("--backend cpp requested but whisper-cpp not on PATH")
        return "cpp"
    if requested == "faster":
        if not info.faster_whisper:
            die("--backend faster requested but faster_whisper not importable")
        return "faster"
    # auto
    if info.whisper_cpp_bin:
        return "cpp"
    if info.faster_whisper:
        return "faster"
    die("no backend available: install whisper-cpp or faster-whisper")
    raise AssertionError("unreachable")


def _transcribe_cpp(
    *,
    wav: Path,
    output_srt: Path,
    model: str,
    lang: str,
    task: str,
    word_timestamps: bool,
    info: BackendInfo,
    dry_run: bool,
    verbose: bool,
) -> int:
    model_path = resolve_cpp_model(model, info) if not dry_run else Path(f"<{model}>")
    out_base = output_srt.with_suffix("")  # whisper.cpp appends .srt itself
    cmd = [
        info.whisper_cpp_bin or "whisper-cpp",
        "-m",
        str(model_path),
        "-f",
        str(wav),
        "-l",
        lang,
        "-osrt",
        "-of",
        str(out_base),
    ]
    if task == "translate":
        cmd.append("-tr")
    if word_timestamps:
        cmd.append("-owts")
    if verbose:
        cmd.append("-pp")
    return run(cmd, dry_run=dry_run, verbose=verbose)


def _srt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _transcribe_faster(
    *,
    wav: Path,
    output_srt: Path,
    model: str,
    lang: str,
    task: str,
    word_timestamps: bool,
    info: BackendInfo,
    dry_run: bool,
    verbose: bool,
) -> int:
    if dry_run:
        print(
            f"[dry-run] faster_whisper.WhisperModel({model!r}).transcribe("
            f"{str(wav)!r}, language={lang!r}, task={task!r}, "
            f"word_timestamps={word_timestamps}, vad_filter=True) -> {output_srt}"
        )
        return 0
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:  # pragma: no cover
        die(f"failed to import faster_whisper: {e}")

    # Pick compute_type sensibly: GPU fp16 if CUDA, else int8 on CPU.
    device = "cuda" if info.faster_whisper_cuda else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    log(
        f"faster-whisper: model={model} device={device} compute={compute_type}", verbose
    )

    wmodel = WhisperModel(model, device=device, compute_type=compute_type)
    language = None if lang == "auto" else lang
    segments, info_obj = wmodel.transcribe(
        str(wav),
        language=language,
        task=task,
        word_timestamps=word_timestamps,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    log(
        f"detected language: {info_obj.language} "
        f"(prob {info_obj.language_probability:.2f})",
        verbose,
    )

    words_path: Optional[Path] = None
    words_f = None
    if word_timestamps:
        words_path = output_srt.with_suffix(".words.json")
        words_f = open(words_path, "w", encoding="utf-8")
        words_f.write("[\n")
        first = True

    with open(output_srt, "w", encoding="utf-8") as srt_f:
        idx = 0
        for seg in segments:
            idx += 1
            text = (seg.text or "").strip()
            srt_f.write(
                f"{idx}\n{_srt_ts(seg.start)} --> {_srt_ts(seg.end)}\n{text}\n\n"
            )
            if word_timestamps and words_f is not None and seg.words:
                for w in seg.words:
                    if not first:
                        words_f.write(",\n")
                    first = False
                    words_f.write(
                        json.dumps(
                            {
                                "start": w.start,
                                "end": w.end,
                                "word": w.word,
                                "probability": getattr(w, "probability", None),
                            }
                        )
                    )
            if verbose:
                log(f"  [{seg.start:7.2f} -> {seg.end:7.2f}] {text[:80]}", verbose)
    if words_f is not None:
        words_f.write("\n]\n")
        words_f.close()
        log(f"wrote word-level JSON: {words_path}", verbose)
    return 0


def cmd_transcribe(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    ensure(input_path)
    output_srt = Path(args.output_srt)
    output_srt.parent.mkdir(parents=True, exist_ok=True)

    info = detect()
    backend = _pick_backend(args.backend, info)
    log(f"backend: {backend}", args.verbose)

    wav = prepare_wav(input_path, dry_run=args.dry_run, verbose=args.verbose)

    task = "translate" if getattr(args, "_translate", False) else "transcribe"

    if backend == "cpp":
        rc = _transcribe_cpp(
            wav=wav,
            output_srt=output_srt,
            model=args.model,
            lang=args.lang,
            task=task,
            word_timestamps=args.word_timestamps,
            info=info,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    else:
        rc = _transcribe_faster(
            wav=wav,
            output_srt=output_srt,
            model=args.model,
            lang=args.lang,
            task=task,
            word_timestamps=args.word_timestamps,
            info=info,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    if rc == 0 and not args.dry_run:
        log(f"wrote SRT: {output_srt}", args.verbose)
    return rc


def cmd_translate(args: argparse.Namespace) -> int:
    # Same path as transcribe with task="translate" (any lang -> English).
    args.output_srt = args.output
    args.lang = getattr(args, "lang", "auto")
    args._translate = True
    return cmd_transcribe(args)


def cmd_srt_mux(args: argparse.Namespace) -> int:
    ensure(Path(args.video))
    ensure(Path(args.srt))
    ffmpeg = which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        args.video,
        "-i",
        args.srt,
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        args.output,
    ]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_srt_burn(args: argparse.Namespace) -> int:
    ensure(Path(args.video))
    ensure(Path(args.srt))
    ffmpeg = which("ffmpeg") or "ffmpeg"
    # Escape the SRT path for the filtergraph (single-quote any colons/commas).
    srt_arg = args.srt.replace("\\", "/").replace(":", r"\:").replace("'", r"\\\'")
    vf = f"subtitles='{srt_arg}'"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        args.video,
        "-vf",
        vf,
        "-c:a",
        "copy",
        args.output,
    ]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="whisper.py",
        description="media-whisper driver (whisper.cpp / faster-whisper + ffmpeg mux).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--dry-run", action="store_true", help="Print commands; do nothing.")
    p.add_argument("--verbose", action="store_true", help="Print progress to stderr.")

    sub = p.add_subparsers(dest="cmd", required=True)

    # check
    sp = sub.add_parser("check", help="Report backend + GPU availability.")
    sp.set_defaults(func=cmd_check)

    # transcribe
    sp = sub.add_parser("transcribe", help="Transcribe audio/video to SRT.")
    sp.add_argument("--input", required=True, help="Input audio or video.")
    sp.add_argument("--output-srt", required=True, help="Output .srt path.")
    sp.add_argument(
        "--model",
        default="base.en",
        help="Model name (e.g. tiny.en, base.en, small, medium, large-v3).",
    )
    sp.add_argument(
        "--lang", default="en", help="Language code (en, es, fr, ...) or 'auto'."
    )
    sp.add_argument("--backend", default="auto", choices=["auto", "cpp", "faster"])
    sp.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Emit word-level timings (faster-whisper: .words.json).",
    )
    sp.set_defaults(func=cmd_transcribe, _translate=False)

    # translate
    sp = sub.add_parser(
        "translate", help="Translate any-language audio to English SRT."
    )
    sp.add_argument("--input", required=True)
    sp.add_argument("--output", required=True, help="Output English .srt path.")
    sp.add_argument(
        "--model",
        default="large-v3",
        help="Multilingual model (translate is multilingual-only).",
    )
    sp.add_argument("--lang", default="auto", help="Source language or 'auto'.")
    sp.add_argument("--backend", default="auto", choices=["auto", "cpp", "faster"])
    sp.add_argument("--word-timestamps", action="store_true")
    sp.set_defaults(func=cmd_translate)

    # srt-mux
    sp = sub.add_parser(
        "srt-mux", help="Soft-mux SRT into MP4 (mov_text, no re-encode)."
    )
    sp.add_argument("--video", required=True)
    sp.add_argument("--srt", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_srt_mux)

    # srt-burn
    sp = sub.add_parser("srt-burn", help="Hard-burn SRT into video (ffmpeg subtitles).")
    sp.add_argument("--video", required=True)
    sp.add_argument("--srt", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_srt_burn)

    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    # Non-interactive: never prompt, never read stdin.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
