---
name: media-denoise-ai
description: >
  AI audio noise reduction with open-source + commercial-safe models that go beyond ffmpeg's built-in afftdn/arnndn: DeepFilterNet (MIT, Rikorose, real-time full-band 48 kHz speech denoise, ships as a prebuilt Rust binary), RNNoise (BSD-3, Xiph/Mozilla reference RNN suppressor, already in ffmpeg as arnndn filter), Resemble Enhance (Apache 2.0, Resemble AI, does denoise + dereverb + bandwidth extension in one pass). Use when the user asks to remove audio noise, enhance voice clarity, clean up a podcast, restore old / lo-fi audio, suppress hum/hiss/keyboard clicks from a video call, fix muffled speech, or get better results than ffmpeg afftdn / arnndn alone.
argument-hint: "[input] [output]"
---

# Media Denoise AI

**Context:** $ARGUMENTS

## Quick start

- **Default, real-time speech denoise (MIT):** `scripts/denoise.py denoise --model deepfilternet --in noisy.wav --out clean.wav` → Step 3
- **Full restoration (denoise + dereverb + bandwidth extension):** `scripts/denoise.py enhance --in muffled.wav --out clean.wav` → Step 4
- **Batch a folder of podcast episodes:** `scripts/denoise.py batch --model deepfilternet --in-dir raw/ --out-dir clean/` → Step 5
- **Use ffmpeg's built-in RNNoise (fastest, no new install):** `scripts/denoise.py denoise --model rnnoise --in noisy.wav --out clean.wav`

## When to use

- Remove steady background noise (HVAC, fan hum, traffic) from voice recordings
- Clean keyboard clicks, mouse clicks, fridge hum out of video-call recordings
- Restore old / cassette / lo-fi audio (Resemble Enhance handles bandwidth extension)
- Pre-process audio before ASR (`media-whisper`) — dramatically reduces hallucinations
- Pre-process audio before TTS voice-cloning reference clips (`media-tts-ai clone`)
- Clean podcast tracks before loudness-normalization

**Why not just use ffmpeg?** ffmpeg ships `afftdn` (spectral subtraction), `anlmdn` (non-local means), and `arnndn` (RNNoise port). All work but are limited:
- `afftdn` is aggressive on breathiness and music, smears consonants
- `anlmdn` is slow and fine-tuned for constant background only
- `arnndn` requires RNN model files, speech-only, 16 kHz biased

AI-based options (DeepFilterNet, Resemble Enhance) give noticeably better SNR, preserve consonants, and handle transient noise (clicks) that ffmpeg filters struggle with.

## Step 1 — Pick a model

| Task                                                | Recommended        | License  | Speed         | GPU req  | Does dereverb? | Does BWE? |
| --------------------------------------------------- | ------------------ | -------- | ------------- | -------- | -------------- | --------- |
| Default realtime speech denoise, full-band 48 kHz   | **DeepFilterNet**  | MIT      | ~real-time on CPU | none   | partial        | no        |
| Ultra-fast, already in ffmpeg, low-quality baseline | **RNNoise**        | BSD-3    | real-time     | none     | no             | no        |
| Full restoration (noise + reverb + bandwidth)       | **Resemble Enhance** | Apache 2.0 | 0.2-0.5x RT on CPU | helpful | yes          | yes       |

See [`references/models.md`](references/models.md) for detailed comparison. Licensing in [`references/LICENSES.md`](references/LICENSES.md).

## Step 2 — Install

```bash
# DeepFilterNet (ships compiled Rust binary + Python wrapper)
pip install deepfilternet
# or prebuilt binary (faster startup):
# cargo install deep-filter
# or download from https://github.com/Rikorose/DeepFilterNet/releases

# Resemble Enhance (PyTorch)
pip install resemble-enhance

# RNNoise is already in ffmpeg as the arnndn filter — no install needed.
# Optional: download RNN model files for arnndn from:
#   https://github.com/GregorR/rnnoise-models
```

Or let the script fetch:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py install deepfilternet
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py install resemble
```

Check what's available:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py check
```

## Step 3 — Denoise

```bash
# DeepFilterNet (default)
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model deepfilternet \
    --in noisy.wav \
    --out clean.wav

# RNNoise via ffmpeg arnndn (fastest, needs RNN model file)
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model rnnoise \
    --in noisy.wav \
    --out clean.wav \
    --rnn-model cb.rnnn        # optional; uses ffmpeg default if omitted

# Resemble Enhance (denoise only, no BWE)
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model resemble \
    --in noisy.wav \
    --out clean.wav
```

## Step 4 — Full enhancement (denoise + dereverb + bandwidth extension)

Resemble Enhance's superpower. Great for old recordings, bad phone calls, muffled interviews.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py enhance \
    --in muffled_phonecall.wav \
    --out clean.wav

# Control denoising strength (0.0 light, 1.0 full)
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py enhance \
    --in muffled.wav \
    --out clean.wav \
    --nfe-steps 64 \
    --solver midpoint \
    --strength 1.0
```

## Step 5 — Batch processing

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py batch \
    --model deepfilternet \
    --in-dir raw_episodes/ \
    --out-dir clean_episodes/
# Mirrors the input folder structure. Skips files already in out-dir by default.
```

## Step 6 — Post-process

- **Match a target loudness (podcast, broadcast):** hand off to `media-ffmpeg-normalize`
  ```bash
  ffmpeg-normalize clean.wav -o final.wav -t -16 -tp -1.5 -lrt 11
  ```
- **Remove inter-phrase silences:** `ffmpeg -af silenceremove=...` — see `ffmpeg-audio-filter` skill
- **Mux cleaned audio back into video:**
  ```bash
  ffmpeg -i video.mp4 -i clean.wav -map 0:v -map 1:a -c:v copy -shortest out.mp4
  ```

## Gotchas

- **DeepFilterNet is speech-optimized.** It will aggressively suppress music and ambience. Don't run it on a podcast with musical intro/outro intact — process voice-only segments, or use Resemble Enhance (more preserving).
- **RNNoise (`arnndn`) requires a `.rnnn` model file.** ffmpeg ships without one. Download a model from `github.com/GregorR/rnnoise-models` (or xiph origin) and pass `--rnn-model path/to/cb.rnnn`.
- **Resemble Enhance upsamples to 44.1 kHz** regardless of input sample rate. This is intentional (part of bandwidth extension); if you need to preserve original SR, resample the output with ffmpeg.
- **Sample-rate friction:** DeepFilterNet runs at 48 kHz natively. Inputs at other rates are resampled internally; the script always writes 48 kHz output. Use `ffmpeg -ar 44100` afterwards if your pipeline requires it.
- **Do not chain AI denoisers in series.** Running DeepFilterNet + Resemble Enhance back-to-back erodes consonants and introduces artifacts. Pick one.
- **For ASR pre-processing, always denoise before Whisper.** whisper.cpp's VAD is sensitive to noise; denoising reduces hallucinations dramatically.
- **DeepFilterNet warm-up:** first run loads the ONNX model (~50 MB). Expect a 1-2s startup delay; subsequent runs in the same process are real-time.
- **Resemble Enhance `--solver` choice:** `midpoint` (default) is best quality. `euler` is faster but slightly worse SNR. Don't use `rk4` unless debugging.
- **GPU on Apple Silicon:** DeepFilterNet is CPU-only (Rust ndarray). Resemble Enhance supports MPS but with some ops falling back to CPU — expect ~0.5x realtime.
- **Mono only for all three models.** Stereo inputs are downmixed before processing. If you need stereo cleanup, run left and right channels separately and merge with ffmpeg `amerge`.
- **Clicks and plosives:** DeepFilterNet handles keyboard clicks well; Resemble Enhance is slightly better at plosives (P/B). Neither removes sibilance (use ffmpeg `deesser` for that — see `ffmpeg-audio-fx`).
- **Music content:** do NOT use DeepFilterNet or Resemble Enhance on music — they are trained on speech. For music source separation see `media-demucs`.
- **Licensing:** all three models are commercial-safe (MIT / BSD-3 / Apache 2.0). No caveats. See [`references/LICENSES.md`](references/LICENSES.md).

## Examples

### Example 1: clean a podcast recording before loudness normalization

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model deepfilternet \
    --in episode_raw.wav \
    --out episode_clean.wav

ffmpeg-normalize episode_clean.wav -o episode_final.wav -t -16 -tp -1.5
```

### Example 2: restore an old phone call

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py enhance \
    --in phonecall_1998.wav \
    --out phonecall_restored.wav
# Resemble Enhance upscales to 44.1 kHz and dereverbs.
```

### Example 3: pre-process for Whisper ASR

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model deepfilternet \
    --in interview.wav \
    --out interview_clean.wav

# Hand off to media-whisper
uv run .../media-whisper/scripts/whisper.py transcribe \
    --input interview_clean.wav \
    --output-srt interview.srt \
    --model medium.en
```

### Example 4: batch-clean an entire folder

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py batch \
    --model deepfilternet \
    --in-dir recordings/ \
    --out-dir cleaned/ \
    --verbose
```

### Example 5: use ffmpeg's built-in arnndn

```bash
# Download an RNN model first (one-time)
curl -Lo cb.rnnn https://raw.githubusercontent.com/GregorR/rnnoise-models/master/conjoined-burgers-2018-08-28/cb.rnnn

uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py denoise \
    --model rnnoise \
    --in noisy.wav \
    --out clean.wav \
    --rnn-model cb.rnnn
```

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'deepfilternet'`

Cause: DeepFilterNet Python wrapper isn't installed.
Solution: `pip install deepfilternet` or install the prebuilt Rust binary via `cargo install deep-filter` and rerun — the script auto-detects the binary.

### Error: `arnndn: could not open '.rnnn' model file`

Cause: no RNN model file specified for ffmpeg's arnndn filter.
Solution: download one from https://github.com/GregorR/rnnoise-models and pass via `--rnn-model`. E.g. `cb.rnnn` (conjoined-burgers 2018 — general speech).

### Output sounds over-processed / consonants smeared

Cause: running DeepFilterNet on music, or chaining two AI denoisers.
Solution: use Resemble Enhance for less aggressive processing, or run `denoise` on voice-only segments and re-mux with music tracks.

### Resemble Enhance CUDA out of memory

Cause: input file too long for VRAM.
Solution: split the input with `ffmpeg-cut-concat` into chunks <60 s, process each, concat with `ffmpeg -f concat`. Or run CPU: `CUDA_VISIBLE_DEVICES= uv run ...`.

### Output file has wrong sample rate (44.1 kHz instead of 48 kHz)

Cause: Resemble Enhance always outputs 44.1 kHz (bandwidth extension reference rate).
Solution: resample: `ffmpeg -i clean.wav -ar 48000 clean_48k.wav`.

### Background music is gone after denoising

Cause: DeepFilterNet and Resemble Enhance are speech models — they suppress music as "noise".
Solution: isolate voice and music tracks with `media-demucs`, denoise voice only, re-mux.

## Reference docs

- [`references/models.md`](references/models.md) — detailed per-model comparison (quality, speed, dereverb, BWE, known failure modes, real-world recipes).
- [`references/LICENSES.md`](references/LICENSES.md) — strict confirmation that all three models are commercial-safe.
