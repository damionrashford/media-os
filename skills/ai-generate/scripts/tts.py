#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
AI text-to-speech + voice-cloning helper.

Models supported (all open-source + commercial-safe):
    speak-only:   kokoro, piper, bark, orpheus, parler, styletts2
    cloning:      openvoice, cosyvoice, chatterbox

Subcommands:
    check                        Report which TTS backends are installed.
    install <model>              Print or run the pip install line for a model.
    list-voices --model <m>      Enumerate preset voices for a model.
    speak                        Synthesize speech (no cloning).
    clone                        Synthesize in the voice of a reference clip.
    batch                        One utterance per line / per SRT cue to a folder.
    audiobook                    Split on `# heading` markdown, narrate chapters.

Global flags (on every subcommand):
    --dry-run                    Print the command(s) that would run, do nothing.
    --verbose                    Echo commands / progress to stderr.

Examples:
    tts.py check
    tts.py install kokoro
    tts.py list-voices --model kokoro
    tts.py speak --model kokoro --text "Hello" --voice af_bella --out out.wav
    tts.py clone --model openvoice --reference ref.wav --text "Hi" --out out.wav
    tts.py batch --script lines.txt --model kokoro --voice af_bella --out-dir dub/
    tts.py audiobook --text-file book.md --model kokoro --voice af_bella \\
                     --chapter-split --out-dir chapters/

Stdlib only. Non-interactive. No interactive prompts anywhere.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUPPORTED_MODELS = [
    "kokoro",
    "piper",
    "bark",
    "orpheus",
    "parler",
    "styletts2",
    "openvoice",
    "cosyvoice",
    "chatterbox",
]

CLONE_MODELS = {"openvoice", "cosyvoice", "chatterbox"}

PIP_LINES = {
    "kokoro": "pip install kokoro-onnx onnxruntime soundfile",
    "piper": "pip install piper-tts",
    "bark": "pip install suno-bark soundfile",
    "orpheus": "pip install orpheus-speech soundfile",
    "parler": "pip install parler-tts soundfile",
    "styletts2": "pip install styletts2 soundfile",
    "openvoice": "pip install openvoice-cli melo-tts soundfile",
    "cosyvoice": "pip install 'funasr[llm]' modelscope soundfile",
    "chatterbox": "pip install chatterbox-tts soundfile",
}

MODULE_NAMES = {
    "kokoro": "kokoro_onnx",
    "piper": "piper",
    "bark": "bark",
    "orpheus": "orpheus_tts",
    "parler": "parler_tts",
    "styletts2": "styletts2",
    "openvoice": "openvoice",
    "cosyvoice": "cosyvoice",
    "chatterbox": "chatterbox",
}

KOKORO_PRESET_VOICES = [
    # American female
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_jessica",
    "af_kore",
    "af_nova",
    "af_river",
    # American male
    "am_adam",
    "am_michael",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_onyx",
    "am_puck",
    "am_santa",
    # British female
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    # British male
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    # Japanese
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    # Mandarin Chinese
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
    # French / Italian / Portuguese / Hindi
    "ff_siwis",
    "if_sara",
    "im_nicola",
    "pf_dora",
    "pm_alex",
    "pm_santa",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
]


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[tts] {msg}", file=sys.stderr)


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


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries without NLTK. Keeps abbreviations mostly intact."""
    text = text.strip()
    if not text:
        return []
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text)
    return [p.strip() for p in pieces if p.strip()]


# ---------------------------------------------------------------------------
# check / install / list-voices
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    info: dict = {"python": sys.version.split()[0], "platform": sys.platform}
    for m in SUPPORTED_MODELS:
        info[m] = _module_available(MODULE_NAMES[m])
    info["piper_cli"] = _which("piper") is not None
    info["ffmpeg"] = _which("ffmpeg") is not None
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
        parts = pip_line.split()
        return _run(parts, args.dry_run, args.verbose)
    return 0


def cmd_list_voices(args: argparse.Namespace) -> int:
    model = args.model.lower()
    if model == "kokoro":
        print(json.dumps({"model": "kokoro", "voices": KOKORO_PRESET_VOICES}, indent=2))
        return 0
    if model == "piper":
        print(
            json.dumps(
                {
                    "model": "piper",
                    "note": "Piper voices are external .onnx + .onnx.json files.",
                    "source": "https://huggingface.co/rhasspy/piper-voices",
                    "examples": [
                        "en_US-amy-medium",
                        "en_US-amy-low",
                        "en_US-lessac-high",
                        "en_US-libritts_r-medium",
                        "en_GB-alan-medium",
                        "en_GB-jenny_dioco-medium",
                        "de_DE-thorsten-high",
                        "fr_FR-siwis-medium",
                        "es_ES-davefx-medium",
                        "it_IT-riccardo-x_low",
                        "nl_NL-mls-medium",
                    ],
                },
                indent=2,
            )
        )
        return 0
    if model == "bark":
        print(
            json.dumps(
                {
                    "model": "bark",
                    "note": "Bark uses speaker prompts like v2/en_speaker_0 through v2/en_speaker_9.",
                    "examples": [f"v2/en_speaker_{i}" for i in range(10)]
                    + [
                        f"v2/{lang}_speaker_{i}"
                        for lang in (
                            "de",
                            "es",
                            "fr",
                            "hi",
                            "it",
                            "ja",
                            "ko",
                            "pl",
                            "pt",
                            "ru",
                            "tr",
                            "zh",
                        )
                        for i in range(3)
                    ],
                },
                indent=2,
            )
        )
        return 0
    if model == "cosyvoice":
        print(
            json.dumps(
                {
                    "model": "cosyvoice",
                    "note": "CosyVoice 2 uses reference clips for zero-shot cloning. "
                    "Built-in voices via ModelScope tags:",
                    "examples": [
                        "中文女",
                        "中文男",
                        "日语女",
                        "英文女",
                        "英文男",
                        "韩语女",
                    ],
                },
                indent=2,
            )
        )
        return 0
    if model in ("openvoice", "chatterbox", "orpheus", "parler", "styletts2"):
        print(
            json.dumps(
                {
                    "model": model,
                    "note": f"{model} is reference-driven or prompt-driven; no preset voice list. "
                    "For cloning models pass --reference. For prompt-driven models pass "
                    "--style or a description in the text.",
                },
                indent=2,
            )
        )
        return 0
    print(f"error: unknown model '{model}'", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Synthesis backends
# ---------------------------------------------------------------------------


def _synth_kokoro(text: str, voice: str, lang: str, out: Path, verbose: bool) -> int:
    try:
        from kokoro_onnx import Kokoro  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['kokoro']}", file=sys.stderr)
        return 3
    _log(f"kokoro synth voice={voice} lang={lang}", verbose)
    # Kokoro-onnx discovers models via HF hub / local cache
    model = Kokoro.from_pretrained()
    samples, sr = model.create(text, voice=voice, speed=1.0, lang=lang)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), samples, sr)
    return 0


def _synth_piper(text: str, voice: str, out: Path, verbose: bool) -> int:
    piper_bin = _which("piper")
    if piper_bin is None:
        print(f"error: piper CLI not found. Run: {PIP_LINES['piper']}", file=sys.stderr)
        return 3
    # voice is path to .onnx (companion .onnx.json must sit next to it)
    cmd = [piper_bin, "--model", voice, "--output_file", str(out)]
    _log(f"$ {' '.join(_quote(c) for c in cmd)} (stdin=text)", verbose)
    proc = subprocess.run(cmd, input=text, text=True)
    return proc.returncode


def _synth_bark(text: str, voice: str, out: Path, verbose: bool) -> int:
    try:
        from bark import generate_audio, preload_models, SAMPLE_RATE  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['bark']}", file=sys.stderr)
        return 3
    _log(f"bark synth voice={voice}", verbose)
    preload_models()
    audio = generate_audio(text, history_prompt=voice or None)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, SAMPLE_RATE)
    return 0


def _synth_orpheus(text: str, voice: str, out: Path, verbose: bool) -> int:
    try:
        from orpheus_tts import OrpheusModel  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['orpheus']}", file=sys.stderr)
        return 3
    _log(f"orpheus synth voice={voice}", verbose)
    model = OrpheusModel()
    audio, sr = model.generate(text, voice=voice or "tara")
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, sr)
    return 0


def _synth_parler(text: str, voice: str, out: Path, verbose: bool) -> int:
    try:
        from parler_tts import ParlerTTSForConditionalGeneration  # type: ignore
        from transformers import AutoTokenizer  # type: ignore
        import soundfile as sf  # type: ignore
        import torch  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['parler']}", file=sys.stderr)
        return 3
    _log(f"parler synth style={voice}", verbose)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        "parler-tts/parler-tts-mini-v1"
    ).to(device)
    tok = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")
    style = voice or "A calm female voice with clear articulation."
    input_ids = tok(style, return_tensors="pt").input_ids.to(device)
    prompt_ids = tok(text, return_tensors="pt").input_ids.to(device)
    generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_ids)
    audio = generation.cpu().numpy().squeeze()
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, model.config.sampling_rate)
    return 0


def _synth_styletts2(text: str, voice: str, out: Path, verbose: bool) -> int:
    try:
        from styletts2 import tts as st2_tts  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['styletts2']}", file=sys.stderr)
        return 3
    _log("styletts2 synth", verbose)
    model = st2_tts.StyleTTS2()
    audio = model.inference(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, 24000)
    return 0


def _synth_openvoice(
    reference: Path, text: str, lang: str, out: Path, verbose: bool
) -> int:
    try:
        from openvoice import se_extractor, ToneColorConverter  # type: ignore
        from melo.api import TTS as MeloTTS  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['openvoice']}", file=sys.stderr)
        return 3
    _log(f"openvoice clone reference={reference}", verbose)
    base = MeloTTS(language=lang.upper() if lang else "EN")
    tmp_wav = out.with_suffix(".base.wav")
    base.tts_to_file(
        text,
        base.hps.data.spk2id[list(base.hps.data.spk2id)[0]],
        str(tmp_wav),
        speed=1.0,
    )
    converter = ToneColorConverter()
    target_se, _ = se_extractor.get_se(str(reference), converter, vad=True)
    source_se, _ = se_extractor.get_se(str(tmp_wav), converter, vad=True)
    converter.convert(
        audio_src_path=str(tmp_wav),
        src_se=source_se,
        tgt_se=target_se,
        output_path=str(out),
    )
    tmp_wav.unlink(missing_ok=True)
    return 0


def _synth_cosyvoice(reference: Path, text: str, out: Path, verbose: bool) -> int:
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['cosyvoice']}", file=sys.stderr)
        return 3
    _log(f"cosyvoice clone reference={reference}", verbose)
    cv = CosyVoice("iic/CosyVoice2-0.5B")
    for i, item in enumerate(cv.inference_zero_shot(text, "", str(reference))):
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), item["tts_speech"].numpy().squeeze(), cv.sample_rate)
        break
    return 0


def _synth_chatterbox(
    reference: Path, text: str, emotion: float, out: Path, verbose: bool
) -> int:
    try:
        from chatterbox.tts import ChatterboxTTS  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        print(f"error: {e}. Run: {PIP_LINES['chatterbox']}", file=sys.stderr)
        return 3
    _log(f"chatterbox clone reference={reference} emotion={emotion}", verbose)
    model = ChatterboxTTS.from_pretrained()
    wav = model.generate(text, audio_prompt_path=str(reference), exaggeration=emotion)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), wav.squeeze(), model.sr)
    return 0


# ---------------------------------------------------------------------------
# speak / clone / batch / audiobook
# ---------------------------------------------------------------------------


def cmd_speak(args: argparse.Namespace) -> int:
    model = args.model.lower()
    if model in CLONE_MODELS:
        print(
            f"error: '{model}' requires --reference (use `clone` subcommand)",
            file=sys.stderr,
        )
        return 2
    text = args.text
    voice = args.voice or ""
    lang = args.lang or "en-us"
    out = Path(args.out).expanduser().resolve()
    _log(f"speak model={model} out={out}", args.verbose or args.dry_run)
    if args.dry_run:
        print(f"# would synthesize {len(text)} chars with {model}", file=sys.stderr)
        return 0
    if model == "kokoro":
        return _synth_kokoro(text, voice or "af_bella", lang, out, args.verbose)
    if model == "piper":
        if not voice:
            print("error: piper needs --voice <path-to-.onnx>", file=sys.stderr)
            return 2
        return _synth_piper(text, voice, out, args.verbose)
    if model == "bark":
        return _synth_bark(text, voice, out, args.verbose)
    if model == "orpheus":
        return _synth_orpheus(text, voice, out, args.verbose)
    if model == "parler":
        return _synth_parler(text, voice, out, args.verbose)
    if model == "styletts2":
        return _synth_styletts2(text, voice, out, args.verbose)
    print(f"error: unknown model '{model}'", file=sys.stderr)
    return 2


def cmd_clone(args: argparse.Namespace) -> int:
    model = args.model.lower()
    if model not in CLONE_MODELS:
        print(
            f"error: '{model}' does not support cloning. Use speak subcommand.",
            file=sys.stderr,
        )
        return 2
    reference = Path(args.reference).expanduser().resolve()
    if not reference.exists():
        print(f"error: reference clip not found: {reference}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser().resolve()
    lang = args.lang or "en"
    emotion = float(args.emotion) if args.emotion is not None else 0.5
    _log(f"clone model={model} ref={reference} out={out}", args.verbose or args.dry_run)
    if args.dry_run:
        print(f"# would clone {reference.name} -> {out.name}", file=sys.stderr)
        return 0
    if model == "openvoice":
        return _synth_openvoice(reference, args.text, lang, out, args.verbose)
    if model == "cosyvoice":
        return _synth_cosyvoice(reference, args.text, out, args.verbose)
    if model == "chatterbox":
        return _synth_chatterbox(reference, args.text, emotion, out, args.verbose)
    return 2


def _parse_srt(path: Path) -> list[dict]:
    """Parse an SRT file into [{index, start, end, text}, ...] dicts."""
    entries: list[dict] = []
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    ts_re = re.compile(r"(\d\d:\d\d:\d\d[,.]\d+)\s*-->\s*(\d\d:\d\d:\d\d[,.]\d+)")
    for blk in blocks:
        lines = [ln for ln in blk.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        idx = lines[0].strip()
        m = ts_re.search(lines[1])
        if not m:
            continue
        text = " ".join(lines[2:]).strip()
        if text:
            entries.append(
                {"index": idx, "start": m.group(1), "end": m.group(2), "text": text}
            )
    return entries


def cmd_batch(args: argparse.Namespace) -> int:
    script = Path(args.script).expanduser().resolve()
    if not script.exists():
        print(f"error: script not found: {script}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    _ensure_dir(out_dir)
    model = args.model.lower()

    if script.suffix.lower() == ".srt":
        cues = _parse_srt(script)
    else:
        lines = [
            ln.strip()
            for ln in script.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        cues = [
            {"index": str(i + 1), "start": None, "end": None, "text": t}
            for i, t in enumerate(lines)
        ]

    manifest: list[dict] = []
    for cue in cues:
        stem = (
            f"{int(cue['index']):04d}"
            if cue["index"].isdigit()
            else re.sub(r"\W+", "_", cue["index"])
        )
        out = out_dir / f"{stem}.wav"
        _log(f"batch: {stem} -> {out}", args.verbose or args.dry_run)
        if args.dry_run:
            manifest.append({**cue, "out": str(out), "status": "dry-run"})
            continue
        rc = _dispatch_speak(
            model,
            cue["text"],
            args.voice or "af_bella",
            args.lang or "en-us",
            out,
            args.verbose,
        )
        manifest.append(
            {**cue, "out": str(out), "status": "ok" if rc == 0 else f"err:{rc}"}
        )

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {"status": "ok", "count": len(manifest), "out_dir": str(out_dir)}, indent=2
        )
    )
    return 0


def cmd_audiobook(args: argparse.Namespace) -> int:
    text_file = Path(args.text_file).expanduser().resolve()
    if not text_file.exists():
        print(f"error: text file not found: {text_file}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    _ensure_dir(out_dir)
    model = args.model.lower()
    content = text_file.read_text(encoding="utf-8")

    if args.chapter_split:
        chunks = _split_chapters(content)
    else:
        chunks = [("full", content)]

    manifest: list[dict] = []
    for i, (title, body) in enumerate(chunks, start=1):
        stem = f"{i:02d}-{_slug(title)}"
        out = out_dir / f"{stem}.wav"
        _log(f"audiobook: chapter={title} -> {out}", args.verbose or args.dry_run)
        if args.dry_run:
            manifest.append({"chapter": title, "out": str(out), "status": "dry-run"})
            continue
        # Split body into sentences to avoid hitting per-model hard-cuts (e.g. Bark 13s).
        sentences = _split_sentences(body)
        tmp_files: list[Path] = []
        for j, sent in enumerate(sentences, start=1):
            tmp = out_dir / f".{stem}.p{j:04d}.wav"
            rc = _dispatch_speak(
                model,
                sent,
                args.voice or "af_bella",
                args.lang or "en-us",
                tmp,
                args.verbose,
            )
            if rc != 0:
                print(f"error: chapter {title} sentence {j} failed", file=sys.stderr)
                return rc
            tmp_files.append(tmp)
        _concat_wavs(tmp_files, out, args.verbose)
        for t in tmp_files:
            t.unlink(missing_ok=True)
        manifest.append({"chapter": title, "out": str(out), "status": "ok"})

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {"status": "ok", "chapters": len(manifest), "out_dir": str(out_dir)},
            indent=2,
        )
    )
    return 0


def _dispatch_speak(
    model: str, text: str, voice: str, lang: str, out: Path, verbose: bool
) -> int:
    if model == "kokoro":
        return _synth_kokoro(text, voice or "af_bella", lang, out, verbose)
    if model == "piper":
        if not voice:
            print("error: piper needs --voice <path-to-.onnx>", file=sys.stderr)
            return 2
        return _synth_piper(text, voice, out, verbose)
    if model == "bark":
        return _synth_bark(text, voice, out, verbose)
    if model == "orpheus":
        return _synth_orpheus(text, voice, out, verbose)
    if model == "parler":
        return _synth_parler(text, voice, out, verbose)
    if model == "styletts2":
        return _synth_styletts2(text, voice, out, verbose)
    print(
        f"error: batch/audiobook does not support cloning model '{model}'",
        file=sys.stderr,
    )
    return 2


def _split_chapters(md: str) -> list[tuple[str, str]]:
    """Split on `# heading` lines. Content before first heading becomes `preface`."""
    parts: list[tuple[str, str]] = []
    current_title = "preface"
    buf: list[str] = []
    for line in md.splitlines():
        if line.startswith("# "):
            if buf and "".join(buf).strip():
                parts.append((current_title, "\n".join(buf).strip()))
            current_title = line.lstrip("# ").strip() or f"chapter-{len(parts) + 1}"
            buf = []
        else:
            buf.append(line)
    if buf and "".join(buf).strip():
        parts.append((current_title, "\n".join(buf).strip()))
    return parts or [("full", md)]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "chapter"


def _concat_wavs(parts: list[Path], out: Path, verbose: bool) -> None:
    """Concatenate WAV files using ffmpeg concat demuxer. Requires ffmpeg on PATH."""
    if not parts:
        return
    ffmpeg = _which("ffmpeg")
    if ffmpeg is None:
        # Pure Python fallback using wave + struct.
        import wave

        data = b""
        params = None
        for p in parts:
            with wave.open(str(p), "rb") as w:
                if params is None:
                    params = w.getparams()
                data += w.readframes(w.getnframes())
        with wave.open(str(out), "wb") as w:
            assert params is not None
            w.setparams(params)
            w.writeframes(data)
        return
    listfile = out.with_suffix(".list.txt")
    listfile.write_text("".join(f"file '{p}'\n" for p in parts))
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listfile),
        "-c",
        "copy",
        str(out),
    ]
    _log(f"$ {' '.join(_quote(c) for c in cmd)}", verbose)
    subprocess.run(cmd, check=False)
    listfile.unlink(missing_ok=True)


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
        prog="tts.py",
        description="AI text-to-speech + voice cloning (commercial-safe models only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("check", help="Report TTS backend availability.")
    _add_common(pc)
    pc.set_defaults(func=cmd_check)

    pi = sub.add_parser("install", help="Print / run pip install line for a model.")
    pi.add_argument("model", help=f"One of: {', '.join(SUPPORTED_MODELS)}")
    pi.add_argument(
        "--run",
        action="store_true",
        help="Actually execute the pip install (otherwise just print).",
    )
    _add_common(pi)
    pi.set_defaults(func=cmd_install)

    pl = sub.add_parser("list-voices", help="Enumerate preset voices for a model.")
    pl.add_argument("--model", required=True, choices=SUPPORTED_MODELS)
    _add_common(pl)
    pl.set_defaults(func=cmd_list_voices)

    ps = sub.add_parser("speak", help="Synthesize speech (no cloning).")
    ps.add_argument(
        "--model",
        required=True,
        choices=[m for m in SUPPORTED_MODELS if m not in CLONE_MODELS],
    )
    ps.add_argument("--text", required=True)
    ps.add_argument(
        "--voice",
        default=None,
        help="Voice name / path (Piper) / speaker prompt (Bark).",
    )
    ps.add_argument(
        "--lang", default="en-us", help="Language code (Kokoro). Default en-us."
    )
    ps.add_argument("--out", required=True)
    _add_common(ps)
    ps.set_defaults(func=cmd_speak)

    pcl = sub.add_parser("clone", help="Synthesize in the voice of a reference clip.")
    pcl.add_argument("--model", required=True, choices=sorted(CLONE_MODELS))
    pcl.add_argument(
        "--reference", required=True, help="Path to a 5-10s reference audio clip."
    )
    pcl.add_argument("--text", required=True)
    pcl.add_argument("--lang", default="en")
    pcl.add_argument(
        "--emotion",
        type=float,
        default=None,
        help="Chatterbox only: 0.0-1.0 expressiveness (default 0.5).",
    )
    pcl.add_argument("--out", required=True)
    _add_common(pcl)
    pcl.set_defaults(func=cmd_clone)

    pb = sub.add_parser(
        "batch", help="One utterance per SRT cue / per line -> a folder."
    )
    pb.add_argument(
        "--script",
        required=True,
        help="SRT file OR plain-text file (one utterance per line).",
    )
    pb.add_argument(
        "--model",
        required=True,
        choices=[m for m in SUPPORTED_MODELS if m not in CLONE_MODELS],
    )
    pb.add_argument("--voice", default=None)
    pb.add_argument("--lang", default="en-us")
    pb.add_argument("--out-dir", required=True)
    _add_common(pb)
    pb.set_defaults(func=cmd_batch)

    pa = sub.add_parser("audiobook", help="Split on `# heading`, narrate chapters.")
    pa.add_argument(
        "--text-file",
        required=True,
        help="Markdown or plain text; with --chapter-split uses `# heading`.",
    )
    pa.add_argument(
        "--model",
        required=True,
        choices=[m for m in SUPPORTED_MODELS if m not in CLONE_MODELS],
    )
    pa.add_argument("--voice", default=None)
    pa.add_argument("--lang", default="en-us")
    pa.add_argument(
        "--chapter-split",
        action="store_true",
        help="Split on `# heading` lines into per-chapter WAV files.",
    )
    pa.add_argument("--out-dir", required=True)
    _add_common(pa)
    pa.set_defaults(func=cmd_audiobook)

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
