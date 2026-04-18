# AI Generation Workflow

**What:** Generate media from scratch — TTS voiceovers, image generation, video generation, music generation, talking-head animation, OCR, automated tagging — using 2026-caliber open-source models with a strict commercial-safe license filter.

**Who:** Content creators, explainer-video producers, indie game devs, marketing teams, podcasters who want custom intros/SFX, anyone building AI-assisted media pipelines that must be commercially shippable.

**License constraint:** Apache-2 / MIT / BSD / GPL only. NC / research-only / ambiguous-commercial licenses are explicitly dropped per skill in `references/LICENSES.md`.

---

## Skills used

| Role | Skill | Open-source models |
|---|---|---|
| Text-to-speech + voice cloning | `media-tts-ai` | Kokoro, OpenVoice, CosyVoice, Chatterbox, Bark, Orpheus, Piper, StyleTTS2, Parler (all Apache/MIT) |
| Speech-to-text | `media-whisper` | whisper.cpp, faster-whisper (MIT) |
| Image generation | `media-sd` | ComfyUI (GPL-3), FLUX-schnell (Apache-2), Kolors (Apache-2), Sana (Apache-2) |
| Video generation | `media-svd` | LTX-Video, CogVideoX, Mochi, Wan (all Apache-2 class) |
| Music / SFX generation | `media-musicgen` | Riffusion (Apache-2), YuE (Apache-2) |
| Lip-sync / talking head | `media-lipsync` | LivePortrait (MIT), LatentSync (Apache-2) |
| Depth estimation | `media-depth` | Depth-Anything v2, MiDaS |
| OCR | `media-ocr-ai` | PaddleOCR, EasyOCR, Tesseract 5, TrOCR |
| Zero-shot tagging + captioning | `media-tag` | CLIP, SigLIP, BLIP-2, LLaVA |
| Stem separation | `media-demucs` | Demucs (MIT) |
| Audio denoise | `media-denoise-ai` | DeepFilterNet, RNNoise, Resemble Enhance |

### Dropped per open-source filter

| Skill | Dropped model | License reason |
|---|---|---|
| `media-tts-ai` | XTTS-v2 | Coqui Public Model License (NC) |
| `media-tts-ai` | F5-TTS | Research license, NC |
| `media-musicgen` | Meta MusicGen | CC-BY-NC |
| `media-sd` | FLUX-dev | Non-commercial |
| `media-sd` | SDXL / SD3 base | Restrictive research license on base weights |
| `media-svd` | Stable Video Diffusion | NC research |
| `media-lipsync` | Wav2Lip | Research-only |
| `media-lipsync` | SadTalker | Non-commercial |
| `media-ocr-ai` | Surya | Commercial restriction |
| `media-upscale` | CodeFormer | NC-research |
| `media-interpolate` | DAIN | Research-only |

---

## The pipeline

### 1. Text-to-speech voiceover

Pick a model based on requirement:

| Need | Model | Notes |
|---|---|---|
| Fast, zero-shot, natural voice | Kokoro | Apache-2, best general quality, 82M params |
| Voice cloning (multilingual) | OpenVoice | MIT, clones from 15s sample |
| Chinese-native voice cloning | CosyVoice | Apache-2 |
| Expressive, emotional | Chatterbox | Apache-2 |
| Simple, lightweight, embedded | Piper | MIT, runs on Raspberry Pi |
| High quality single-voice | StyleTTS2 | MIT |
| Text+style control | Parler | Apache-2 |
| Creative / music-like | Bark | MIT |
| Modern expressive | Orpheus | Apache-2 |

```bash
# Kokoro (recommended default)
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py kokoro \
  --text "Welcome to our tutorial. Today we'll be exploring AI video generation." \
  --voice af \
  --output voiceover.wav

# OpenVoice for cloning
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py openvoice \
  --text "This is a cloned voice." \
  --reference-audio my-voice-sample.wav \
  --output cloned.wav

# Piper (embedded / fast)
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py piper \
  --text "Quick announcement" \
  --voice en_US-amy-medium \
  --output announcement.wav
```

**Never use XTTS-v2 or F5-TTS** — both excluded for commercial-restrictive licenses.

### 2. Image generation

```bash
# FLUX-schnell (Apache-2) — recommended default
uv run .claude/skills/media-sd/scripts/sdctl.py flux-schnell \
  --prompt "A cinematic shot of a mountain lake at golden hour, 8k, sharp focus" \
  --output image.png \
  --width 1024 --height 1024 --steps 4

# Kolors (Apache-2) — strong on Chinese + English
uv run .claude/skills/media-sd/scripts/sdctl.py kolors \
  --prompt "..." --output image.png

# Sana (Apache-2) — blazing fast 4K generation
uv run .claude/skills/media-sd/scripts/sdctl.py sana \
  --prompt "..." --output image.png --width 4096 --height 4096

# ComfyUI (GPL-3) — node-graph workflow engine
uv run .claude/skills/media-sd/scripts/sdctl.py comfyui-run \
  --workflow my-workflow.json
```

**FLUX-dev is dropped** (non-commercial). FLUX-schnell is the Apache-2 variant.

### 3. Video generation

2026-class open-source video models:

| Model | License | Best for |
|---|---|---|
| LTX-Video | Apache-2 class | Real-time fast generation |
| CogVideoX | Apache-2 | High quality, longer clips |
| Mochi | Apache-2 | Cinematic quality |
| Wan | Apache-2 | Versatile, good motion |

```bash
# LTX-Video (fastest)
uv run .claude/skills/media-svd/scripts/svdctl.py ltxvideo \
  --prompt "A cat walking through a garden, cinematic, 4k" \
  --output clip.mp4 \
  --duration 5 --fps 24

# CogVideoX (slower, higher quality)
uv run .claude/skills/media-svd/scripts/svdctl.py cogvideox \
  --prompt "..." --output clip.mp4 --model cogvideox-5b
```

**Stable Video Diffusion is dropped** (NC research).

### 4. Music / SFX generation

```bash
# Riffusion — spectrogram-diffusion music
uv run .claude/skills/media-musicgen/scripts/musicctl.py riffusion \
  --prompt "Upbeat electronic with piano, 120bpm" \
  --duration 30 --output music.wav

# YuE — longer-form, structured music
uv run .claude/skills/media-musicgen/scripts/musicctl.py yue \
  --prompt "Ambient cinematic pad with subtle percussion" \
  --duration 60 --output cinematic.wav
```

**Meta MusicGen is dropped** (CC-BY-NC).

### 5. Lip-sync / talking head animation

Drive a still photo with audio:

```bash
# LivePortrait (MIT) — best open-source face animator
uv run .claude/skills/media-lipsync/scripts/lipsyncctl.py liveportrait \
  --image portrait.jpg \
  --audio voiceover.wav \
  --output talking.mp4

# LatentSync (Apache-2) — latent-space lip-sync
uv run .claude/skills/media-lipsync/scripts/lipsyncctl.py latentsync \
  --video face-video.mp4 \
  --audio new-audio.wav \
  --output relipsynced.mp4
```

**Wav2Lip and SadTalker are dropped** (research / non-commercial).

### 6. OCR — extract text from images / video

```bash
# PaddleOCR (Apache-2) — best general purpose
uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py paddle \
  --input document.png --output extracted.json --lang en

# Tesseract 5 (Apache-2) — fastest, classical
uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py tesseract \
  --input document.png --output extracted.txt --lang eng

# TrOCR (MIT) — transformer-based, handwriting
uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py trocr \
  --input handwritten.jpg --output text.txt

# EasyOCR — multilingual, good on scenes
uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py easy \
  --input scene.jpg --output text.txt --langs en,zh,ja
```

**Surya is dropped** (commercial restriction).

### 7. Zero-shot tagging + captioning

```bash
# CLIP (MIT) — zero-shot classification
uv run .claude/skills/media-tag/scripts/tagctl.py clip \
  --input image.jpg \
  --labels "dog,cat,bird,car,person" \
  --output tags.json

# SigLIP (Apache-2) — improved CLIP
uv run .claude/skills/media-tag/scripts/tagctl.py siglip \
  --input image.jpg \
  --labels "..." --output tags.json

# BLIP-2 (BSD) — generate captions
uv run .claude/skills/media-tag/scripts/tagctl.py blip2 \
  --input image.jpg \
  --output "caption.txt"

# LLaVA (Apache-2) — conversational image understanding
uv run .claude/skills/media-tag/scripts/tagctl.py llava \
  --input image.jpg \
  --prompt "Describe the image in detail." \
  --output description.txt
```

### 8. Speech-to-text (Whisper)

```bash
# whisper.cpp (fastest local)
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input audio.wav \
  --output transcript.srt \
  --model base.en \
  --format srt

# faster-whisper (Python, CUDA-accelerated)
uv run .claude/skills/media-whisper/scripts/whisper.py faster \
  --input audio.wav \
  --output transcript.vtt \
  --model large-v3
```

### 9. Stem separation

```bash
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input song.wav \
  --output-dir stems/ \
  --model htdemucs
# Outputs stems/vocals.wav, drums.wav, bass.wav, other.wav
```

---

## Composite workflows

### Explainer video from scratch

1. Write script (human).
2. `media-tts-ai` → voiceover (Kokoro).
3. `media-sd` → slide images (FLUX-schnell, 16:9).
4. `media-svd` → B-roll clips (LTX-Video).
5. `media-lipsync` → animate a host photo (LivePortrait).
6. `media-musicgen` → background music (Riffusion, ambient).
7. `ffmpeg-cut-concat` → assemble to timeline.
8. `ffmpeg-audio-filter` → mix voiceover + music + SFX.
9. `media-ffmpeg-normalize` → -16 LUFS loudness.
10. `ffmpeg-subtitles` → auto-burn (from the TTS source text).
11. `ffmpeg-transcode` → H.264 deliverable.
12. `media-cloud-upload` → push to YouTube.

### Multilingual voice cloning

1. Record 30s voice sample.
2. `media-tts-ai` (OpenVoice) → clone to English + Spanish + French + Japanese.
3. Generate localized voiceovers per target market.
4. Run each through `media-denoise-ai` (DeepFilterNet) for polish.
5. Mux with localized subtitles (`ffmpeg-subtitles`).

### Book cover + trailer

1. `media-sd` (FLUX-schnell) → cover art variations (3-5 prompts).
2. `media-tag` (LLaVA) → auto-describe for alt-text.
3. `media-svd` (Mochi) → 10s cinematic trailer clip.
4. `media-tts-ai` (StyleTTS2) → narrator voiceover.
5. `media-musicgen` (YuE) → cinematic score.
6. Assemble in `media-moviepy` or `ffmpeg-cut-concat`.

### Automated podcast chapter thumbnails

1. `media-scenedetect` → find chapter boundaries.
2. `ffmpeg-frames-images` → extract one frame per chapter.
3. `media-tag` (BLIP-2) → generate caption per frame.
4. `media-sd` (Kolors) → generate stylized thumbnail from each caption.
5. `media-exiftool` → embed chapter metadata.

### Digital human with cloned voice

1. `media-tts-ai` (OpenVoice) → voice clone.
2. `media-lipsync` (LivePortrait) → drive a portrait photo with the cloned voice.
3. `media-sd` (FLUX-schnell) → generate branded background.
4. `ffmpeg-chromakey` + `media-matte` (RobustVideoMatting) → composite cleanly.
5. `media-musicgen` → brand audio bed.
6. Final via `ffmpeg-transcode` + `media-cloud-upload`.

---

## Gotchas

### License discipline

- **Always verify via `references/LICENSES.md` before adding a new model.** Upstream repos can add non-commercial riders in later commits.
- **GPL-3 (e.g., ComfyUI, RobustVideoMatting) requires source distribution** if you modify and redistribute. Use dynamically or in a pipeline, not bundled into proprietary binaries.
- **Hugging Face License field is not authoritative** — always read the actual LICENSE file in the repo.
- **Pin model weights to specific commits** when publishing a pipeline. Weights-only forks sometimes add NC clauses without the PR noting it.

### Technical landmines

- **All Layer 9 skills require GPU for reasonable throughput.** CPU-only runs are 10-50x slower. Apple Silicon MPS works for most but has edge cases.
- **TTS models have different sample rates.** Kokoro=24kHz, Piper=22.05kHz, StyleTTS2=24kHz, OpenVoice=24kHz. Resample to 48kHz before mixing with other audio.
- **Voice cloning needs CLEAN reference audio.** Noisy samples produce noisy clones. Run `media-denoise-ai` (DeepFilterNet) on the reference first.
- **FLUX-schnell is 4-step distilled.** Don't increase `--steps` above 4-8; it doesn't improve quality and wastes compute.
- **ComfyUI workflow JSONs pin specific node versions.** A workflow from someone else's ComfyUI may not load without matching node packages — use ComfyUI Manager to install missing nodes.
- **LTX-Video prompt adherence is sensitive to phrasing.** "A cat running" ≠ "A running cat." Prompt engineering matters more than with image models.
- **CogVideoX-5b needs ~20GB VRAM.** CogVideoX-2b runs on 8GB but quality is notably lower.
- **Riffusion produces 5.11-second clips natively.** For longer music, chain clips with crossfade, or use YuE for structured long-form.
- **LivePortrait expects a clean frontal portrait.** Angled faces, glasses, and occluded mouths degrade results.
- **LivePortrait output is 512×512 by default.** Upscale with `media-upscale` if you need larger.
- **Whisper `large-v3` is 3GB of weights.** Test with `base.en` (140MB) first. Quality gap closes with `medium` (1.5GB).
- **Whisper hallucinates on silence.** Trim leading/trailing silence with `ffmpeg-audio-filter` (`silenceremove`) before transcription.
- **Whisper word-level timestamps require `--word_timestamps True`** in faster-whisper; whisper.cpp has `--max-len 1 --split-on-word`.
- **Demucs 4-stem model is `htdemucs`. 6-stem (adds guitar+piano) is `htdemucs_6s`.** Different default.
- **OCR model selection by script**: PaddleOCR is best for Latin + Chinese. TrOCR is best for handwritten. Tesseract is fastest but weakest on complex layouts.
- **CLIP / SigLIP / BLIP-2 need fixed-resolution inputs (typically 224/336/384/448).** `tagctl.py` resizes internally; don't feed arbitrary sizes manually.
- **LLaVA needs a LLM backbone** (usually Vicuna/Llama-2 7B+). That LLM has its own license — Llama-2 is "community license" with revenue cap clauses.

---

## Example — "Open-source explainer video with cloned voice"

```bash
#!/usr/bin/env bash
set -e

# Artifacts
VOICE_REF="host-sample.wav"         # 30s of the host's voice
SCRIPT="script.txt"                  # The narration text
OUT="explainer-final.mp4"

# 1. Clone voice + render narration
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py openvoice \
  --text "$(cat $SCRIPT)" \
  --reference-audio "$VOICE_REF" \
  --output tmp-voice.wav

# 2. Denoise the voiceover
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
  --input tmp-voice.wav --output voice-clean.wav

# 3. Generate 5 slide images
for i in 1 2 3 4 5; do
  uv run .claude/skills/media-sd/scripts/sdctl.py flux-schnell \
    --prompt "$(sed -n "${i}p" prompts.txt)" \
    --width 1920 --height 1080 \
    --output "slide-$i.png"
done

# 4. Generate 3 B-roll video clips
for i in 1 2 3; do
  uv run .claude/skills/media-svd/scripts/svdctl.py ltxvideo \
    --prompt "$(sed -n "${i}p" broll-prompts.txt)" \
    --duration 5 --fps 24 \
    --output "broll-$i.mp4"
done

# 5. Animate a host portrait
uv run .claude/skills/media-lipsync/scripts/lipsyncctl.py liveportrait \
  --image host-portrait.jpg \
  --audio voice-clean.wav \
  --output talking-host.mp4

# 6. Background music
uv run .claude/skills/media-musicgen/scripts/musicctl.py riffusion \
  --prompt "Upbeat tech background music" \
  --duration 90 --output music.wav

# 7. Auto-subtitles
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input voice-clean.wav --output subs.srt --model small.en --format srt

# 8. Assemble (simplified — replace with actual timeline build)
ffmpeg -i talking-host.mp4 \
  -f concat -safe 0 -i <(printf "file '%s'\n" broll-*.mp4 slide-*.png) \
  -i music.wav \
  -filter_complex "[1]concat=n=5[v]; [0:a][2]amix=inputs=2:duration=first[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -vf "subtitles=subs.srt" \
  -movflags +faststart \
  "$OUT"

# 9. Normalize loudness
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input "$OUT" --output explainer-final-normalized.mp4 --target -16

# 10. Publish
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider youtube --file explainer-final-normalized.mp4

# Cleanup
rm tmp-* slide-* broll-* music.wav subs.srt voice-clean.wav talking-host.mp4
```

**Every model in this pipeline is Apache-2 / MIT / BSD** — fully commercial.

---

## Further reading

- [`ai-enhancement.md`](ai-enhancement.md) — restoration models (upscale, interpolate, denoise, matte, depth)
- [`podcast-pipeline.md`](podcast-pipeline.md) — audio-focused AI pipeline
- [`vod-post-production.md`](vod-post-production.md) — traditional finishing on AI-generated media
- Each skill's `references/LICENSES.md` — canonical license audit per model
