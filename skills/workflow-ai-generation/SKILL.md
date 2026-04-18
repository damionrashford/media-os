---
name: workflow-ai-generation
description: Generate media from scratch with 2026 open-source AI — TTS voiceover (Kokoro / OpenVoice / Piper), image gen (FLUX-schnell / Kolors / Sana / ComfyUI), video gen (LTX-Video / CogVideoX / Mochi / Wan), music (Riffusion / YuE), lipsync talking heads (LivePortrait / LatentSync), OCR (PaddleOCR / Tesseract 5 / TrOCR), zero-shot tagging (CLIP / SigLIP / BLIP-2 / LLaVA). Strict commercial-safe license filter. Use when the user says "generate a video", "TTS voiceover", "AI explainer video", "clone my voice", "generate music", "AI image", "digital human", or anything about from-scratch AI media.
argument-hint: [prompt]
---

# Workflow — AI Generation

**What:** Synthesize new media with open-source, commercial-safe AI models. Strict license filter: Apache-2 / MIT / BSD / GPL. NC / research-only models are always-dropped.

## Skills used

`media-tts-ai`, `media-whisper`, `media-sd`, `media-svd`, `media-musicgen`, `media-lipsync`, `media-depth`, `media-ocr-ai`, `media-tag`, `media-demucs`, `media-denoise-ai`.

## Tool matrix

### TTS (`media-tts-ai`)

| Model | License | Best for |
|---|---|---|
| Kokoro | Apache-2 | general default |
| OpenVoice | MIT | voice cloning |
| CosyVoice | Apache-2 | Chinese |
| Chatterbox | MIT | expressive |
| Piper | MIT | embedded / offline |
| StyleTTS2 | MIT | single-voice quality |
| Parler | Apache-2 | style prompting |
| Bark | MIT | creative / SFX |
| Orpheus | Apache-2 | modern expressive |

DROPPED: XTTS-v2 (CPML NC), F5-TTS (research).

### Image (`media-sd`)

| Model | License | Best for |
|---|---|---|
| FLUX-schnell | Apache-2 | default (4-step distilled) |
| Kolors | Apache-2 | bilingual EN/ZH |
| Sana | Apache-2 | fast 4K |
| ComfyUI | GPL-3 | node-graph workflows |

DROPPED: FLUX-dev (NC), SDXL / SD3 base (restrictive).

### Video (`media-svd`)

| Model | License | Best for |
|---|---|---|
| LTX-Video | Apache-2 | fastest |
| CogVideoX | Apache-2 | high quality (slower) |
| Mochi | Apache-2 | cinematic |
| Wan | Apache-2 | versatile |

DROPPED: Stable Video Diffusion (NC research).

### Music / SFX (`media-musicgen`)

| Model | License | Best for |
|---|---|---|
| Riffusion | Apache-2 | spectrogram-diffusion |
| YuE | Apache-2 | long-form structured |

DROPPED: Meta MusicGen (CC-BY-NC).

### Lipsync (`media-lipsync`)

| Model | License |
|---|---|
| LivePortrait | MIT |
| LatentSync | Apache-2 |

DROPPED: Wav2Lip (research), SadTalker (NC).

### OCR (`media-ocr-ai`)

| Model | License | Best for |
|---|---|---|
| PaddleOCR | Apache-2 | Latin + Chinese default |
| Tesseract 5 | Apache-2 | fastest classical |
| TrOCR | MIT | handwriting |
| EasyOCR | Apache-2 | multilingual |

DROPPED: Surya (commercial restriction).

### Tagging / captioning (`media-tag`)

CLIP (MIT), SigLIP (Apache-2), BLIP-2 (BSD), LLaVA (Apache-2 but needs Llama-2 backbone — check license).

### Stem separation (`media-demucs`)

`htdemucs` 4-stem, `htdemucs_6s` 6-stem (adds guitar + piano).

### Speech-to-text (`media-whisper`)

whisper.cpp (MIT fastest CPU), faster-whisper (MIT CUDA-accelerated).

## Example composite workflows

### Explainer video from script

script → TTS voiceover (`media-tts-ai` Kokoro) → slide images (`media-sd` FLUX-schnell) → B-roll clips (`media-svd` LTX-Video) → host animation (`media-lipsync` LivePortrait) → background music (`media-musicgen` Riffusion) → assemble (`ffmpeg-cut-concat`) → mix (`ffmpeg-audio-filter` + sidechain ducking) → loudness normalize (`media-ffmpeg-normalize`) → auto-burn subtitles (`media-whisper` + `ffmpeg-subtitles`) → transcode H.264 → YouTube upload (`media-cloud-upload`).

### Multilingual voice clone

30 s clean reference → DeepFilterNet denoise → OpenVoice clone to EN/ES/FR/JP → per-track denoise → mux with localized subs.

### Book cover + trailer

FLUX-schnell cover variations → LLaVA auto-describe for alt-text → Mochi cinematic trailer → StyleTTS2 narrator → YuE cinematic score → assemble.

### Automated podcast chapter thumbnails

scenedetect chapter boundaries → extract frame per chapter → BLIP-2 caption → Kolors generate thumbnail from caption → embed chapter metadata.

### Digital human with cloned voice

OpenVoice clone → LivePortrait drives portrait → FLUX-schnell branded background → chromakey + RVM matte composite → Riffusion audio bed → transcode + upload.

## Gotchas

- **License discipline.** Always check the skill's `references/LICENSES.md` BEFORE adopting a new model. HuggingFace license field is NOT authoritative. Pin model weights to specific commit hashes.
- **GPL-3 in ComfyUI / RVM** — requires source distribution if modified/redistributed. Use dynamically / in pipeline, not bundled into proprietary product.
- **All Layer 9 skills need GPU** for reasonable throughput (10–50× slower on CPU).
- **TTS sample rates vary:** Kokoro 24 kHz, Piper 22.05 kHz, StyleTTS2 24 kHz, OpenVoice 24 kHz. Resample ALL to 48 kHz before mixing.
- **Voice cloning needs CLEAN reference.** Noisy sample → noisy clone. DeepFilterNet the reference first.
- **FLUX-schnell is 4-step distilled.** Do NOT push `--steps` above 4–8 — wastes compute, no quality gain.
- **ComfyUI workflow JSONs pin specific node versions.** Use ComfyUI Manager to install matching nodes.
- **LTX-Video prompt adherence is phrasing-sensitive.** "cat running" ≠ "running cat".
- **CogVideoX-5b needs ~20 GB VRAM.** 2b variant runs on 8 GB at lower quality.
- **Riffusion produces 5.11-second clips natively.** Chain with crossfade for longer, or use YuE for structured long-form.
- **LivePortrait expects clean frontal portrait.** Angled faces, glasses, occluded mouths degrade output.
- **LivePortrait outputs 512×512 by default.** Upscale with `media-upscale` for larger.
- **Whisper `large-v3` is 3 GB.** Test with `base.en` (140 MB) first — quality gap to `medium` (1.5 GB) is small for clean audio.
- **Whisper hallucinates on silence.** Trim leading/trailing with `silenceremove`.
- **Whisper word-level timestamps require `--word_timestamps True`** (faster-whisper) or `--max-len 1 --split-on-word` (whisper.cpp).
- **Whisper `--language auto` is fragile on accented speech.** Specify language explicitly.
- **Diarization is external to Whisper.** Use pyannote.audio (MIT) or simple-diarizer.
- **OCR selection:** PaddleOCR for Latin+Chinese, TrOCR for handwriting, Tesseract for speed on clean docs.
- **CLIP / SigLIP / BLIP-2 need fixed-resolution inputs** (224/336/384/448). The `tagctl.py` script resizes internally.
- **LLaVA needs an LLM backbone** (Vicuna / Llama-2 7B+). Llama-2 community license has revenue caps.

## Related

- `workflow-ai-enhancement` — for enhancing EXISTING footage (not generating new).
- `workflow-podcast-pipeline` — for podcast-specific AI workflows.
- `workflow-analysis-quality` — VMAF + QC on AI-generated output.
