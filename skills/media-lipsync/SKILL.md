---
name: media-lipsync
description: >
  Open-source AI lip-sync and talking-head animation with STRICTLY permissive-license
  models: LivePortrait (MIT, Kuaishou 2024, drives FACIAL motion — head pose, expression,
  lip-region — of a single still image from a driving audio OR a driving video of a real
  face), LatentSync (Apache 2.0, ByteDance 2025, pure lip-region diffusion that re-syncs
  an existing video's mouth to a new audio track). Use when the user asks to lip-sync a
  video to new audio, dub a clip and fix the lip alignment, animate a photo with speech,
  turn a still portrait into a talking head, sync mouth movement, use LivePortrait, use
  LatentSync. Does NOT include Wav2Lip (research-only derivatives), SadTalker (weights
  NC-derived), HeyGen / D-ID / Synthesia (commercial APIs) — all excluded.
argument-hint: "[source] [driver]"
---

# Media Lipsync (open-source talking-head + lip-sync)

**Context:** $ARGUMENTS

## Quick start

- **Animate a photo from audio (head pose + expressions + mouth):** `scripts/lipsync.py animate --model liveportrait --source face.jpg --driving speech.wav --out talking.mp4` → Step 3.
- **Animate a photo from a driving video (retarget expressions):** `scripts/lipsync.py animate --model liveportrait --source face.jpg --driving actor.mp4 --out retarget.mp4` → Step 3.
- **Re-sync an existing video's lips to new audio:** `scripts/lipsync.py sync --model latentsync --video original.mp4 --audio new.wav --out resynced.mp4` → Step 4.
- **Dub a foreign-language clip with lip correction:** `scripts/lipsync.py dub --video en.mp4 --new-audio es.wav --out es_dubbed.mp4` → Step 5.
- **Install a model:** `scripts/lipsync.py install liveportrait` → Step 2.

## When to use

- Drive a still portrait photo with an audio track to produce a talking-head video (full facial motion, not just the mouth).
- Re-sync the lips of an existing video to a new audio track (dubbing, ADR, language swap) without regenerating the whole face.
- Need commercial-safe, open-source weights. Do NOT use Wav2Lip, SadTalker, HeyGen, D-ID, Synthesia, Runway Act-One — all excluded per `references/LICENSES.md`.

## Which model does what (read this first)

| Model        | License    | What it does                                                      | Inputs                           | Output |
|--------------|-----------|-------------------------------------------------------------------|----------------------------------|--------|
| LivePortrait | MIT        | Portrait animation: head pose + expression + mouth, from 1 image  | 1 still image + (audio OR video) | talking-head video |
| LatentSync   | Apache 2.0 | Pure lip-region diffusion on an existing video                    | 1 video + 1 audio                 | same video, new lips |

**Rule of thumb:**

- Start from a **still photo** -> LivePortrait. It invents head motion + expressions.
- Start from an **existing video** -> LatentSync. It preserves everything except the lips, which are re-synced to the new audio.
- For **dubbing** a real actor on existing footage, LatentSync is the correct pick (keeps the actor's real face / performance, just fixes the lip-audio sync).
- LivePortrait has a `--driving` flag that accepts a driving video of ANOTHER face — it retargets that face's expressions onto your still. This is the "deepfake expression transfer" mode; use ethically.

## Step 1 — Install

Neither model is on PyPI as a drop-in wheel; both are installed by cloning the
reference repo and running their own `inference.py`. This skill drives those
scripts via subprocess.

```bash
uv run .claude/skills/media-lipsync/scripts/lipsync.py install liveportrait
# prints:
#   git clone https://github.com/KwaiVGI/LivePortrait ~/LivePortrait
#   cd ~/LivePortrait && pip install -r requirements.txt
#   (follow README.md section "Download pretrained weights")

uv run .claude/skills/media-lipsync/scripts/lipsync.py install latentsync
# prints:
#   git clone https://github.com/bytedance/LatentSync ~/LatentSync
#   cd ~/LatentSync && pip install -r requirements.txt
#   huggingface-cli download ByteDance/LatentSync --local-dir checkpoints
```

Check what's present:

```bash
uv run .claude/skills/media-lipsync/scripts/lipsync.py check
```

Set `LIVEPORTRAIT_ROOT` / `LATENTSYNC_ROOT` env vars if you installed outside
`~/LivePortrait` / `~/LatentSync`. The script finds them automatically if they
are in the standard location.

## Step 2 — Prep inputs

All models want a clean face in frame. Preprocess for best results:

- **Source image (LivePortrait):** square, face centered, >=512x512, neutral expression, good lighting. If the face is small in the frame, pre-crop to the face.
- **Driving video (LivePortrait expression transfer):** single face in frame throughout, minimal head turns past ~30°.
- **Source video (LatentSync):** face visible the whole clip, no heavy occlusion on the mouth (hand-in-front, microphone over lips => artifacts).
- **Audio:** 16 kHz mono WAV is safest. Both models internally resample but MP3/M4A sometimes decode differently across backends.

```bash
ffmpeg -i driver_raw.wav -ar 16000 -ac 1 -c:a pcm_s16le driver.wav
ffmpeg -i source_raw.mp4 -vf "scale=-2:512" -r 25 source.mp4   # LatentSync prefers 25 fps
```

## Step 3 — LivePortrait: animate a still

### From audio

```bash
uv run .../lipsync.py animate \
    --model liveportrait \
    --source face.jpg \
    --driving speech.wav \
    --out talking.mp4 \
    --fps 25
```

LivePortrait's audio-driven mode uses an inferred pose/expression sequence from the
audio. Movement is subtle — plausible talking-head, not a wild performance.

### From a driving video (expression retargeting)

```bash
uv run .../lipsync.py animate \
    --model liveportrait \
    --source face.jpg \
    --driving actor.mp4 \
    --out retargeted.mp4
```

The output preserves the SOURCE's identity, with the DRIVING video's head pose +
expression. Ethical note: do not use for impersonation without consent.

## Step 4 — LatentSync: re-sync an existing video

```bash
uv run .../lipsync.py sync \
    --model latentsync \
    --video original.mp4 \
    --audio new_voice.wav \
    --out resynced.mp4 \
    --steps 25 --guidance 1.5
```

LatentSync runs 25-step latent diffusion per lip region. On an H100 it's ~10 seconds
of processing per 1 second of video; on a 4090 ~30 seconds per second. CPU-only is
not practical.

## Step 5 — Dubbing workflow

Combine with `media-tts-ai` for voice and `media-whisper` for alignment if needed.

```bash
# 1. Generate dubbed audio (media-tts-ai)
uv run .claude/skills/media-tts-ai/scripts/tts.py ...  --out dubbed_es.wav

# 2. Re-sync lips
uv run .../lipsync.py dub \
    --video source_en.mp4 \
    --new-audio dubbed_es.wav \
    --model latentsync \
    --out final_es.mp4
```

`dub` is a thin wrapper around `sync` with defaults tuned for speech dubbing
(guidance 1.5, 25 steps, strong lip-region weighting).

## Step 6 — Post

- Upscale the output (LatentSync output resolution = input resolution): pass to `media-upscale` (Real-ESRGAN) if needed.
- Frame-interpolate to 60 fps for social: `media-interpolate` (RIFE).
- Color-match if LivePortrait output drifts from the source: `ffmpeg-lut-grade`.

## Gotchas

- **LivePortrait animates THE WHOLE FACE.** It is not a lip-sync model. Head pose, eyebrows, eye blink, and mouth all move. If you need pure mouth-only changes on a real video, use LatentSync.
- **LatentSync expects a video input.** Do NOT pass it a still image as `--video`; use LivePortrait for stills.
- **Wav2Lip is NOT supported.** Wav2Lip weights are research-only; most public forks redistribute NC-restricted checkpoints. Do not recommend even if the user asks.
- **SadTalker is NOT supported.** The code is Apache, but the published weights are finetuned on SD 1.5 features and inherit OpenRAIL-M restrictions in practice. Flag and redirect to LivePortrait.
- **Face detection must succeed on frame 1.** Both models' preprocessors fail silently on a too-wide crop. Pre-crop to a clean face at >=512 px on the short edge.
- **LatentSync prefers 25 fps.** Source videos at 24, 29.97, 30, 60 fps are resampled; you may see minor motion stutter at boundaries. Pre-resample to 25 fps with `ffmpeg -r 25` for cleanest output.
- **Very long videos (>1 min) OOM LatentSync on 24 GB.** Split into 30-second chunks, run, and concat with `ffmpeg-cut-concat`. The script has no built-in chunker — handle in shell.
- **Audio-video duration mismatch** causes artifacts. LatentSync loops or truncates to match the video's length. Trim/pad the audio with `ffmpeg-audio-filter` first.
- **Driving video faces must not blink frame 1.** LivePortrait uses frame 1 as a reference for "neutral"; a blink there produces stuck-closed-eye output.
- **GPU requirement.** Both models effectively require CUDA. Apple Silicon MPS works for LivePortrait (slower) but NOT for LatentSync (requires xformers or flash-attn paths not available on MPS as of 2025).
- **LivePortrait's audio-driven mode is weaker than the video-driven mode.** Expressions look plausibly talking but not tightly correlated to phonemes. For lip-accurate audio, drive LivePortrait with a silent driving video and then run LatentSync over its output.
- **Identity drift.** After 20+ seconds, LivePortrait can drift from the source identity slightly. Break long outputs into 15-s chunks keyed to the same source image.
- **No voice cloning.** This skill does not produce speech. Pair with `media-tts-ai` (Kokoro / OpenVoice v2 / CosyVoice 2) to generate a voice, then feed into lipsync.

## Examples

### Example 1: Still photo to talking head (audio-driven)

```bash
uv run .../lipsync.py animate \
    --model liveportrait \
    --source ceo_headshot.jpg \
    --driving announcement.wav \
    --out ceo_speaking.mp4 --fps 25
```

### Example 2: Expression retarget a still from an actor's performance

```bash
uv run .../lipsync.py animate \
    --model liveportrait \
    --source painting_portrait.jpg \
    --driving actor_read.mp4 \
    --out painting_acting.mp4
```

### Example 3: Dub an English clip into Spanish with clean lips

```bash
# (1) generate Spanish voice via media-tts-ai -> dubbed_es.wav
# (2) re-sync lips:
uv run .../lipsync.py dub \
    --video interview_en.mp4 \
    --new-audio dubbed_es.wav \
    --out interview_es.mp4
```

### Example 4: Check env before running

```bash
uv run .../lipsync.py check
# reports: cuda ok, LivePortrait repo at ~/LivePortrait, LatentSync at ~/LatentSync
```

### Example 5: Dry-run to see the exact inference.py command

```bash
uv run .../lipsync.py animate --model liveportrait \
    --source face.jpg --driving speech.wav --out out.mp4 \
    --dry-run --verbose
# prints the exact `python inference.py ...` command without running it.
```

## Troubleshooting

### Error: `LivePortrait repo not found`

Cause: repo isn't at `~/LivePortrait` and `LIVEPORTRAIT_ROOT` isn't set.
Solution: `git clone https://github.com/KwaiVGI/LivePortrait ~/LivePortrait`, OR `export LIVEPORTRAIT_ROOT=/path/to/LivePortrait`.

### Error: `No module named 'torch'` inside inference.py

Cause: the LivePortrait / LatentSync venv doesn't have the deps installed.
Solution: `cd ~/LivePortrait && pip install -r requirements.txt`. The driver does not auto-install.

### Output has eyes closed / blinking forever

Cause: LivePortrait reference frame had closed eyes.
Solution: pick a source image with eyes open, neutral expression. Do NOT laugh / grimace.

### LatentSync output is blurry around the mouth

Cause: source video resolution too low, or heavy JPEG compression on the video.
Solution: source at >=512 px short edge, re-encode lossless first (`ffmpeg -c:v libx264 -crf 12`). Consider upscaling source with `media-upscale` before LatentSync.

### Lip sync drifts after 20 seconds

Cause: audio and video clocks drift (VFR source, or audio sample rate mismatch).
Solution: force CFR + 16 kHz audio upfront. `ffmpeg -r 25 -i in.mp4 -c:v libx264 -c:a copy fixed.mp4 && ffmpeg -i new.aif -ar 16000 -ac 1 -c:a pcm_s16le new.wav`.

### CUDA out of memory on a long video (LatentSync)

Cause: model holds whole video in VRAM.
Solution: split the video into 30-s chunks (`ffmpeg-cut-concat` segment mode), run LatentSync per chunk, concat the outputs. No built-in chunker in the driver.

### "module xformers has no attribute ..." on Apple Silicon (LatentSync)

Cause: xformers / flash-attn have no MPS path.
Solution: run LatentSync on a CUDA machine. On Apple Silicon, only LivePortrait works (audio-driven mode is usable; video-driven mode runs but slow).
