---
name: media-tts-ai
description: >
  Modern AI text-to-speech + voice cloning with open-source + commercial-safe models: Kokoro (Apache 2.0, 82M params, realtime on CPU, top TTS Arena ranking, 8+ languages), OpenVoice v2 (MIT, voice cloning), CosyVoice 2 (Apache 2.0, 2025 SOTA cloning from Alibaba), Chatterbox (MIT, Resemble AI zero-shot cloning + emotion control), Bark (MIT, expressive + non-verbal sounds like laughs/sighs), Orpheus (Apache 2.0, Canopy AI Llama-3-based expressive), Piper (MIT, fastest embedded TTS), StyleTTS2 (MIT, Kokoro's architecture base), Parler-TTS (Apache 2.0, prompt-controlled voice). Use when the user asks to synthesize speech, clone a voice, read text aloud, generate audiobook narration, add TTS to an app, replace Core Audio say with better quality, or create AI voiceovers.
argument-hint: "[text] [output]"
---

# Media TTS AI

**Context:** $ARGUMENTS

## Quick start

- **Default TTS (no cloning), best quality-for-size:** `scripts/tts.py speak --model kokoro --text "Hello" --voice af_bella --out out.wav` → Step 3
- **Voice clone from a 5-10s sample:** `scripts/tts.py clone --model openvoice --reference ref.wav --text "..." --out out.wav` → Step 4
- **Audiobook from a text/markdown file:** `scripts/tts.py audiobook --text-file book.md --model kokoro --voice af_bella --chapter-split --out-dir chapters/` → Step 5
- **Realtime embedded (lowest latency, local):** `scripts/tts.py speak --model piper --text "Hi" --voice en_US-amy-medium --out out.wav`
- **Expressive + non-verbal ([laughs], [sighs]):** `scripts/tts.py speak --model bark --text "Nice. [laughs]" --out out.wav`

## When to use

- Generate narration, voiceover, or podcast intros from text
- Clone a specific voice from a short reference clip (OpenVoice / CosyVoice / Chatterbox)
- Build audiobooks with chapter splits from markdown / plain text
- Replace Apple's `say` or eSpeak with neural-quality TTS
- Batch-dub SRT lines (time-aligned per cue) for localization
- Do NOT use for: lip-sync to a face video — that's `media-lipsync`. Transcription (opposite direction) is `media-whisper`.

## Step 1 — Pick a model

All nine models below are **open-source + commercial-safe**. Pick by task:

| Task                                       | Recommended        | License      | Notes                                          |
| ------------------------------------------ | ------------------ | ------------ | ---------------------------------------------- |
| Default high-quality TTS, no cloning       | **Kokoro**         | Apache 2.0   | 82M params, realtime on CPU, ~50 preset voices |
| Lowest-latency embedded TTS                | **Piper**          | MIT          | ONNX runtime, Raspberry Pi friendly            |
| Voice cloning from short reference         | **OpenVoice v2**   | MIT          | Tone-color transfer, cross-lingual             |
| SOTA 2025 cloning / multilingual           | **CosyVoice 2**    | Apache 2.0   | Alibaba FunAudioLLM                            |
| Zero-shot cloning + emotion intensity      | **Chatterbox**     | MIT          | Resemble AI                                    |
| Expressive speech + [laughs] [sighs]       | **Bark**           | MIT          | Suno AI original weights (not v2/Suno paid)    |
| Emotional Llama-3-based TTS                | **Orpheus**        | Apache 2.0   | Canopy AI 2025                                 |
| Prompt-controlled voice style              | **Parler-TTS**     | Apache 2.0   | HuggingFace                                    |
| Base architecture of Kokoro                | **StyleTTS2**      | MIT          | Direct access to the model under Kokoro        |

Full comparison matrix (quality / speed / GPU req / clone-support / emotion-support) in [`references/models.md`](references/models.md). License proofs in [`references/LICENSES.md`](references/LICENSES.md).

**DO NOT** use: XTTS-v2 (Coqui CPML — non-commercial), F5-TTS (CC-BY-NC weights), MusicGen (CC-BY-NC weights), Suno-proprietary Bark v2 derivatives. This skill explicitly refuses those.

## Step 2 — Install

```bash
# Default path (Kokoro ONNX — CPU-friendly, no torch required)
pip install kokoro-onnx onnxruntime soundfile

# Or the PyTorch variant (bigger, supports more voices)
pip install kokoro soundfile

# Piper (ONNX, <50 MB for a voice)
pip install piper-tts

# Voice cloning (pick one)
pip install openvoice-cli                     # OpenVoice v2 CLI wrapper
pip install "funasr[llm]" modelscope          # CosyVoice 2 via ModelScope
pip install chatterbox-tts                    # Chatterbox
pip install suno-bark                         # Bark (Apache 2.0 weights only)
pip install orpheus-speech                    # Orpheus
pip install parler-tts                        # Parler-TTS

# StyleTTS2 (builds from source)
pip install styletts2
```

Or let the script bootstrap for you:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py install kokoro
```

Check what's available:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py check
```

## Step 3 — Synthesize speech (no cloning)

```bash
# Kokoro (default)
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py speak \
    --model kokoro \
    --text "Hello world, this is a test." \
    --voice af_bella \
    --lang en-us \
    --out out.wav

# Piper (fastest)
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py speak \
    --model piper \
    --text "Hello" \
    --voice en_US-amy-medium \
    --out out.wav

# Bark (expressive)
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py speak \
    --model bark \
    --text "Hmm, interesting. [laughs] That's wild." \
    --voice v2/en_speaker_6 \
    --out out.wav
```

List available voices per model:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py list-voices --model kokoro
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py list-voices --model piper
```

See [`references/voices.md`](references/voices.md) for the ~50 Kokoro voice names and language codes.

## Step 4 — Voice cloning

A clean 5-10 s reference clip of the target voice works best. Mono, 16-24 kHz, minimal background noise.

```bash
# OpenVoice v2
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py clone \
    --model openvoice \
    --reference speaker_ref.wav \
    --text "Text to say in the cloned voice." \
    --lang en \
    --out out.wav

# CosyVoice 2 (SOTA 2025)
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py clone \
    --model cosyvoice \
    --reference ref.wav \
    --text "Hello in the cloned voice." \
    --out out.wav

# Chatterbox with emotion intensity
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py clone \
    --model chatterbox \
    --reference ref.wav \
    --text "I'm actually pretty excited about this!" \
    --emotion 0.8 \
    --out out.wav
```

**Ethical note:** only clone voices you have explicit consent to clone. Logging the reference path is recommended for provenance.

## Step 5 — Batch / audiobook / SRT dub

```bash
# Audiobook: split on `# heading` into chapter files
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py audiobook \
    --text-file book.md \
    --model kokoro \
    --voice af_bella \
    --chapter-split \
    --out-dir chapters/

# Batch: each SRT cue → aligned WAV inside out-dir/
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py batch \
    --script script.srt \
    --model kokoro \
    --voice af_bella \
    --out-dir dub/

# Or a plain text file, one line = one utterance
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py batch \
    --script lines.txt \
    --model piper \
    --voice en_US-amy-medium \
    --out-dir lines/
```

## Step 6 — Post-process and mux

- **Loudness normalization:** hand off to `media-ffmpeg-normalize` (EBU R128, -16 LUFS for podcasts, -23 LUFS for broadcast).
- **Format conversion:** `ffmpeg -i out.wav -c:a libopus -b:a 64k out.opus`
- **Replace audio track in a video:** `ffmpeg -i video.mp4 -i out.wav -map 0:v -map 1:a -c:v copy -shortest dubbed.mp4`
- **Lip-sync to an existing face video:** hand off to `media-lipsync` (LivePortrait / LatentSync).

## Gotchas

- **License boundaries matter.** XTTS-v2, F5-TTS, Suno's paid Bark v2, and MusicGen weights are NOT commercial-safe. This skill intentionally excludes them. See [`references/LICENSES.md`](references/LICENSES.md).
- **Kokoro ONNX vs PyTorch:** `kokoro-onnx` runs CPU-only without torch; the PyTorch `kokoro` package adds more voices but requires torch + CUDA for speed. The script auto-picks ONNX first.
- **Piper voice files are per-voice** — download from huggingface.co/rhasspy/piper-voices. Each voice is two files: `.onnx` + `.onnx.json`. Path to `.onnx` is the voice argument.
- **Bark hard-cuts at ~13s** per generation. Longer text needs sentence-level chunking; the `audiobook` and `batch` subcommands do this automatically.
- **OpenVoice v2 needs a base TTS** (it does tone-color transfer, not end-to-end synthesis). The wrapper handles this by using a MeloTTS base model under the hood.
- **CosyVoice 2 models are 1-3GB.** First run downloads; subsequent runs are cached in `~/.cache/modelscope/`.
- **Chatterbox emotion intensity** range is 0.0 to 1.0 (higher = more expressive). Default 0.5 feels natural; 0.8+ can sound cartoonish.
- **Bark prompts:** non-verbal cues are bracketed: `[laughs]`, `[sighs]`, `[music]`, `[gasps]`, `[clears throat]`. Music notes like `♪ la la la ♪` trigger sung output (unreliable).
- **Sample rate:** Kokoro outputs 24 kHz, Piper 16-22 kHz (voice-dependent), Bark 24 kHz, CosyVoice 22.05 kHz. If mixing voices in a DAW, resample all to 48 kHz first.
- **No interactive prompts anywhere.** All models run non-interactive via the script.
- **Hallucinated words on long sentences:** split text at sentence boundaries; the batch/audiobook paths do this with NLTK-free regex (`.!?` splits).
- **GPU vs CPU:** Kokoro / Piper / StyleTTS2 run realtime on CPU. Bark / CosyVoice / Orpheus / Parler-TTS need a GPU for near-realtime; on CPU they run at 0.1-0.3x realtime.
- **Apple Silicon MPS:** most of these libraries have partial MPS support. If you hit errors, force CPU: `--device cpu`.
- **Licensing of generated audio:** you own the output under the model's license — but if you cloned a voice, make sure you have rights to that speaker's voice. Written consent for any voice clone used commercially.
- **Language coverage:** Kokoro ships en-us / en-gb / fr / ja / ko / zh / hi / it / pt-br. Other models vary — see [`references/models.md`](references/models.md).

## Examples

### Example 1: English podcast intro from a single line

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py speak \
    --model kokoro \
    --text "Welcome to the show. Today we're talking about open-source AI." \
    --voice af_bella \
    --out intro.wav
ffmpeg -i intro.wav -c:a libopus -b:a 64k intro.opus
```

### Example 2: Clone a speaker for an accessibility narration

```bash
# Record a 10s clean reference clip of the speaker
ffmpeg -f avfoundation -i ":0" -t 10 -ac 1 -ar 24000 ref.wav

# Clone with CosyVoice 2
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py clone \
    --model cosyvoice \
    --reference ref.wav \
    --text "This is the accessibility narration in the cloned voice." \
    --out narration.wav
```

### Example 3: Audiobook from a Markdown book, split on `# Chapter`

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py audiobook \
    --text-file manuscript.md \
    --model kokoro \
    --voice af_bella \
    --chapter-split \
    --out-dir book/
# -> book/01-introduction.wav, book/02-chapter-one.wav, ...
```

### Example 4: Dub an SRT into aligned WAV cues

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tts.py batch \
    --script subs.srt \
    --model kokoro \
    --voice am_michael \
    --out-dir dub/
# -> dub/0001-00-00-00-00-000.wav, dub/0002-...wav, with timing in dub/manifest.json
```

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'kokoro_onnx'`

Cause: Default path isn't installed.
Solution: `pip install kokoro-onnx onnxruntime soundfile` or run `scripts/tts.py install kokoro`.

### Error: `Voice not found: af_bella`

Cause: Kokoro voice pack wasn't downloaded or the name is misspelled.
Solution: `scripts/tts.py list-voices --model kokoro` to see the exact names; `kokoro-onnx` fetches voices on first use from HuggingFace (network required once).

### Output sounds robotic / metallic

Cause: Using a smaller Piper voice (`-low` / `-x_low`) or CPU-quantized Kokoro.
Solution: switch to a `-medium` or `-high` Piper voice; for Kokoro use the full PyTorch package instead of ONNX-int8.

### Voice clone sounds nothing like the reference

Cause: reference clip is noisy, too short, or has music under it.
Solution: pre-process with `media-denoise-ai enhance ref.wav clean_ref.wav`, then re-clone. Also try CosyVoice 2 which is SOTA 2025 for zero-shot cloning.

### Bark cuts off mid-sentence

Cause: Bark's 13s hard limit per generation.
Solution: use `audiobook` or `batch` subcommand — splits on sentence boundaries and concatenates.

### `CUDA out of memory` on Bark / CosyVoice / Orpheus

Cause: VRAM pressure.
Solution: `--device cpu` (slower), or free other GPU processes; Bark has a `SUNO_USE_SMALL_MODELS=1` env var for an 8GB-VRAM mode.

### Output file is silent

Cause: text was empty after preprocessing (e.g. only emoji), or model errored silently.
Solution: rerun with `--verbose` to see the exact command and the model's stderr; confirm `soundfile.info(out.wav)` shows a nonzero duration.

## Reference docs

- [`references/models.md`](references/models.md) — full comparison: license, clone support, emotion control, speed, GPU need, languages.
- [`references/voices.md`](references/voices.md) — ~50 Kokoro voice names, Piper naming convention, Bark prompts, language codes.
- [`references/LICENSES.md`](references/LICENSES.md) — strict table confirming every model shipped here is commercial-safe. XTTS-v2 / F5-TTS / MusicGen are explicitly excluded.
