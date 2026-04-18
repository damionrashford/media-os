---
name: media-whisper
description: >
  Speech-to-text transcription and subtitle generation with whisper.cpp and faster-whisper: extract spoken text from audio/video, generate SRT/VTT subtitles, translate speech to English, word-level timestamps, multilingual support, speaker diarization optional. Use when the user asks to transcribe a video, auto-generate subtitles from speech, create captions, translate a foreign-language clip to English, extract dialogue as text, build an ASR pipeline, or process podcast audio into a transcript.
argument-hint: "[input]"
---

# Media Whisper

**Context:** $ARGUMENTS

## Quick start

- **Transcribe video → SRT:** extract 16 kHz mono WAV (Step 2) → run ASR (Step 3) → SRT is written next to the input.
- **Translate foreign speech → English SRT:** Step 2, then `whisper-cpp -tr ...` or faster-whisper `task="translate"` (Step 3).
- **Burn-in captions:** generate SRT here, then hand off to the `ffmpeg-subtitles` skill.
- **Soft-mux SRT into MP4:** `scripts/whisper.py srt-mux --video in.mp4 --srt out.srt --output tagged.mp4`.

## When to use

- Auto-generate captions (SRT/VTT) from audio or video.
- Translate non-English audio to an English transcript.
- Produce a searchable text transcript or word-level JSON for a podcast/interview.
- Build an ASR stage in a larger pipeline (precedes diarization, search indexing, summarization).
- Do NOT use for speaker identification — whisper doesn't do diarization reliably. Hand off to `pyannote-audio` (see `references/whisper.md`).

## Step 1 — Pick a backend

Two mature local backends. Pick one:

| Backend         | Install                                                                      | Strength                                                   | Use when                                                                 |
| --------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------ |
| whisper.cpp     | `brew install whisper-cpp` (macOS) or build from source on Linux             | Zero Python deps, Metal on Apple Silicon, SRT/VTT built in | Shell-only pipelines, Apple Silicon, want a static binary                |
| faster-whisper  | `pip install faster-whisper` (or `uv pip install faster-whisper`)            | ~4× faster on CPU (CTranslate2), word timestamps, VAD      | Python pipeline, need word-level timing, GPU CUDA, long files with VAD   |
| OpenAI API      | n/a (HTTP)                                                                   | Best-quality large-v3, no local compute                    | Network available, ok paying per minute, confidentiality is not an issue |

Check what's present:

```bash
uv run .claude/skills/media-whisper/scripts/whisper.py check
```

Download a GGML model for whisper.cpp (one-time):

```bash
# Installed with brew: models land in /opt/homebrew/share/whisper.cpp/models
bash /opt/homebrew/share/whisper.cpp/models/download-ggml-model.sh base.en
# Options: tiny / tiny.en / base / base.en / small / small.en / medium / medium.en / large-v3 / large-v3-q5_0
```

faster-whisper downloads models automatically on first use into `~/.cache/huggingface/`.

## Step 2 — Extract 16 kHz mono WAV

whisper.cpp **requires** 16 kHz mono PCM-s16le WAV. faster-whisper accepts almost any format but benefits from the same normalization. Always do this first:

```bash
ffmpeg -y -i in.mp4 -vn -ar 16000 -ac 1 -c:a pcm_s16le audio.wav
```

`scripts/whisper.py transcribe` runs this step automatically if the input is not already a WAV.

**Pre-processing for better accuracy** (optional, for podcast / phone audio): loudnorm + denoise before ASR. See `ffmpeg-audio-filter` skill — `loudnorm` two-pass to hit -16 LUFS, then `afftdn=nr=12` for broadband noise. Whisper hallucinates less on normalized input.

## Step 3 — Run ASR

### Option A: whisper.cpp

```bash
# Basic: English, write SRT + VTT + plain text
whisper-cpp \
  -m /opt/homebrew/share/whisper.cpp/models/ggml-base.en.bin \
  -f audio.wav \
  -l en \
  -osrt -ovtt -otxt \
  -of out            # output basename → out.srt / out.vtt / out.txt

# Auto language detection (first 30s used for detection)
whisper-cpp -m ggml-large-v3.bin -f audio.wav -l auto -osrt -of out

# Translate any language → English SRT
whisper-cpp -m ggml-large-v3.bin -f audio.wav -tr -osrt -of out

# Word-level timestamps (TSV)
whisper-cpp -m ggml-large-v3.bin -f audio.wav -owts -of out

# Diarized-ish timestamps (tinydiarize — only works with ggml-small.en-tdrz.bin model)
whisper-cpp -m ggml-small.en-tdrz.bin -f audio.wav -tdrz -osrt -of out
```

Useful flags: `-t N` threads, `-p N` processors, `-ml N` max segment length (chars), `-sow` split on word, `-pp` print progress, `-nt` no timestamps (plain text mode), `-et` entropy threshold for hallucination guard.

### Option B: faster-whisper (Python)

```python
from faster_whisper import WhisperModel

# compute_type: int8 (fast CPU), int8_float16 (GPU balance), float16 (GPU best)
model = WhisperModel("large-v3", device="cpu", compute_type="int8")

segments, info = model.transcribe(
    "audio.wav",
    language="en",              # or None for auto-detect
    task="transcribe",          # or "translate" → English
    word_timestamps=True,
    vad_filter=True,            # removes silence, reduces hallucinations
    vad_parameters={"min_silence_duration_ms": 500},
)
print(f"Detected language: {info.language} (prob {info.language_probability:.2f})")
for seg in segments:
    print(f"[{seg.start:.2f} -> {seg.end:.2f}] {seg.text}")
```

`segments` is a generator — iterate once, write SRT as you go. `scripts/whisper.py transcribe --backend faster` handles this.

### Option C: Driver script (recommended)

```bash
# Auto picks whisper.cpp if binary is on PATH, else faster-whisper
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
    --input podcast.mp3 --output-srt podcast.srt --model base.en --lang en

# Force backend
uv run .../whisper.py transcribe --backend cpp  --input in.mp4 --output-srt out.srt
uv run .../whisper.py transcribe --backend faster --input in.mp4 --output-srt out.srt \
    --word-timestamps

# Translate
uv run .../whisper.py translate --input spanish.mp4 --output english.srt --model large-v3
```

## Step 4 — Post-process and mux

**Soft-mux SRT into MP4** (no re-encode):

```bash
ffmpeg -i in.mp4 -i out.srt -c copy -c:s mov_text out.mp4
# or through the script
uv run .../whisper.py srt-mux --video in.mp4 --srt out.srt --output tagged.mp4
```

**Burn-in (hard-coded) subtitles:** hand off to `ffmpeg-subtitles` skill. Or quick form:

```bash
ffmpeg -i in.mp4 -vf "subtitles=out.srt" -c:a copy burned.mp4
# or
uv run .../whisper.py srt-burn --video in.mp4 --srt out.srt --output burned.mp4
```

**Trim end-of-file hallucinations:** whisper commonly emits a phantom "Thank you for watching" / "Subtitles by..." at EOF. Check the last cue; drop it if it appears after the audio ended.

## Gotchas

- whisper.cpp **requires** 16 kHz mono PCM-s16le WAV. Other formats sometimes work via internal conversion but are unreliable — always normalize with ffmpeg first.
- Model sizes (FP16 GGML): **tiny 39M · base 74M · small 244M · medium 769M · large-v3 1.5GB**. RAM need ~= model size + 1GB working set.
- **English-only models (`.en` suffix) are faster AND more accurate for English** than the multilingual equivalents. Never use multilingual if you know the content is English.
- Multilingual models can **translate to English** (`-tr` / `task="translate"`) but cannot translate between two non-English languages.
- **Auto language detection uses only the first 30 s** of audio. Unreliable for code-switching / mixed-language content. Pass `-l <iso>` explicitly when you know the language.
- Use **quantized models** (`large-v3-q5_0` ~1.1GB vs 1.5GB FP16) when RAM-constrained. Accuracy loss is minimal; inference ~same speed or faster on CPU.
- **faster-whisper is ~4× faster than whisper.cpp on CPU** (CTranslate2 int8). Use it for long files. whisper.cpp wins on Apple Silicon with Metal for short files due to faster warm-up.
- **compute_type** tradeoff: `int8` fast CPU, `int8_float16` good on GPU, `float16` best quality but GPU-only, `float32` reference.
- **Smaller models drop punctuation** on complex sentences. Use `large-v3` or a post-processing punctuation restorer (e.g., `deepmultilingualpunctuation`).
- **End-of-file hallucinations** are common — whisper trained on YouTube often appends "Thanks for watching", "Subtitles by ..." after real speech ends. Check final cue and drop if it extends past audio duration.
- **Hallucinations on silence** are the #1 quality issue. Mitigate: enable VAD (`vad_filter=True` in faster-whisper), pre-trim silence with `ffmpeg-audio-filter` `silenceremove`, or bump `-et` entropy threshold in whisper.cpp.
- `chunk_length` default is 30 s — audio longer than that is processed in overlapping windows. Usually fine; long silences between chunks can cause boundary glitches.
- **Diarization (who spoke when) is NOT whisper.** `-tdrz` (tinydiarize) is a token hint, not real diarization. For speaker labels, run `pyannote-audio` separately and merge on timestamps. See `references/whisper.md`.
- **GPU support:** whisper.cpp has Metal (Apple) + CUDA. faster-whisper has CUDA only (no Metal). On Apple Silicon, whisper.cpp is usually faster.
- `-owts` in whisper.cpp writes a **.wts** karaoke-style script, not JSON. For word-level JSON, use faster-whisper `word_timestamps=True`.
- SRT timing granularity is ms — don't expect sample-accurate boundaries. Word timestamps can drift ±200 ms from true onsets.

## Examples

### Example 1: English podcast → SRT

```bash
uv run .../whisper.py transcribe \
    --input episode42.mp3 \
    --output-srt episode42.srt \
    --model small.en \
    --lang en \
    --verbose
```

Uses whisper.cpp if available (via `small.en` GGML); falls back to faster-whisper. `small.en` is the sweet-spot for English podcasts on CPU.

### Example 2: Spanish film clip → English captions burned into video

```bash
# 1. Translate
uv run .../whisper.py translate --input scene.mov --output scene.srt --model large-v3

# 2. Burn into video (720p output)
uv run .../whisper.py srt-burn --video scene.mov --srt scene.srt --output scene.dubbed.mp4
```

### Example 3: Interview → word-level JSON for search index

```bash
uv run .../whisper.py transcribe \
    --input interview.wav \
    --output-srt interview.srt \
    --backend faster \
    --model large-v3 \
    --word-timestamps
# Script also writes interview.words.json when --word-timestamps is set.
```

### Example 4: Long lecture with lots of silence

```bash
# Enable VAD to skip silent stretches; dramatic speedup + fewer hallucinations.
uv run .../whisper.py transcribe \
    --input lecture.m4a --output-srt lecture.srt \
    --backend faster --model medium.en
# Script enables vad_filter=True by default for faster-whisper.
```

## Troubleshooting

### Error: `whisper-cpp: command not found`

Cause: whisper.cpp binary not installed.
Solution: `brew install whisper-cpp` (macOS) or build from https://github.com/ggerganov/whisper.cpp. Or force faster-whisper: `--backend faster`.

### Error: `ModuleNotFoundError: No module named 'faster_whisper'`

Cause: package not installed in active Python.
Solution: `pip install faster-whisper` (or `uv pip install faster-whisper`). Alternatively use `--backend cpp`.

### Error: `failed to load model: ggml-base.en.bin`

Cause: model file missing.
Solution: `bash /opt/homebrew/share/whisper.cpp/models/download-ggml-model.sh base.en`. Pass the full path via `-m` if it's stored elsewhere.

### Transcript contains "Thanks for watching, don't forget to subscribe"

Cause: EOF hallucination — model trained on YouTube.
Solution: drop the last cue if its start time is past the audio duration. Or pre-trim the trailing silence with `ffmpeg -af silenceremove=stop_periods=1:stop_duration=2:stop_threshold=-40dB`.

### Subtitles drift vs. audio on long file

Cause: boundary glitches between 30 s chunks, or variable frame rate source.
Solution: remux to CFR first (`ffmpeg -i in.mp4 -vsync cfr out.mp4`), or run the `media-subtitle-sync` skill (alass / ffsubsync) on the generated SRT to re-align.

### Punctuation missing from transcript

Cause: small / tiny models produce unpunctuated output.
Solution: use `medium` or `large-v3`, or post-process with `deepmultilingualpunctuation` / `punctuators`. faster-whisper's `large-v3` is generally best.

### faster-whisper is slow on my Mac

Cause: faster-whisper uses CTranslate2 CPU path on Apple Silicon (no Metal).
Solution: switch to whisper.cpp (`--backend cpp`) which has Metal acceleration. Or run faster-whisper on a CUDA box.

### Auto-detected language is wrong

Cause: first 30 s of file is music / silence / wrong language.
Solution: force `--lang <iso>`. See language codes in `references/whisper.md`.
