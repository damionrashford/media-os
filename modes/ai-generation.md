# Mode: ai-generation

**Subagent**: `architect`
**Trigger phrases**: "generate video", "text to video", "TTS", "text to speech", "AI music", "image gen", "FLUX", "LTX-Video", "CogVideoX", "ComfyUI", "Kokoro TTS", "Riffusion", "generate an image", "generate audio"
**Output**: `${MEDIA_WORK_DIR}/modes/ai-generation/{date}_{slug}/`

## Inputs

- **Required**:
  - `modality` — `image`, `video`, `tts`, `music`.
  - `prompt` — text prompt (or script for TTS, or musical description for music).
- **Optional**:
  - `model` — explicit model override (must pass license filter).
  - `resolution` — image / video: WxH (default: 1024×1024 for image; 720×480 for video).
  - `duration` — video / audio length in seconds (default: 5s video, prompt-length TTS, 30s music).
  - `voice` — TTS only: voice ID per model's voice list.
  - `seed` — reproducibility (default: random).
  - `negative_prompt` — image / video only (default: empty).

## Steps

1. Read modality-specific skill:
   - image → `ai-generate` (and `references/LICENSES.md`).
   - video → `ai-generate` (and `references/LICENSES.md`).
   - tts → `ai-generate` (and `references/LICENSES.md`).
   - music → `ai-generate` (and `references/LICENSES.md`).
2. Default model per modality (Apache-2 / MIT / BSD / GPL only):
   - image → **FLUX-schnell** (Apache-2) > Kolors (Apache-2) > Sana (Apache-2). NOT FLUX-dev (research-only), NOT SDXL/SD3 base (research-only).
   - video → **LTX-Video** (Apache-2) > CogVideoX (Apache-2) > Mochi (Apache-2) > Wan (Apache-2). NOT SVD (research-only).
   - tts → **Kokoro** (Apache-2) > OpenVoice (MIT) > Piper (MIT) > StyleTTS2 (MIT) > Bark (MIT) > Orpheus (Apache-2) > Parler (Apache-2). NOT XTTS-v2 / F5-TTS (research-only).
   - music → **Riffusion** (MIT) > YuE (Apache-2). NOT Meta MusicGen (NC).
3. **STOP** if `model` override names a restricted model — surface the licensed alternative.
4. For image/video: compose ComfyUI workflow JSON OR direct model invocation per skill helper.
5. For TTS: validate `voice` exists in the model's voice list (Kokoro: `af_*`, `am_*`, `bf_*`; OpenVoice: cloned voices; Piper: per-language `<lang>_<voice>`).
6. For music: pass `duration` (Riffusion: 5–30s chunks; YuE: up to 5min).
7. Run the model with `seed`, `prompt`, `negative_prompt`, `resolution`, `duration` as applicable.
8. For video: post-process (interpolate to higher fps if requested; tone-map if HDR target).
9. For audio (TTS / music): normalize via `media-audio-cli` if `loudness_target` specified.
10. Optionally compose multi-modal output (e.g. TTS over generated image as a video) by chaining into `vfx-pipeline` or `podcast-pipeline`.
11. **`mosafe`-wrap** any ffmpeg post-processing.
12. Write `summary.md` with model, license, seed (for reproducibility), full prompt, runtime, output path.

## Output schema

```markdown
# AI generation — {slug} — {date}

## Configuration
- **Modality**: {image / video / tts / music}
- **Model**: {model name}
- **License**: {Apache-2 / MIT / BSD / GPL}
- **Resolution / duration**: {WxH} / {seconds}
- **Seed**: {N — for reproducibility}

## Prompt
```
{full prompt verbatim}
```

{negative_prompt block if image/video}

## Generation
- **Started**: {ISO timestamp}
- **Runtime**: {hh:mm:ss}
- **GPU**: {CUDA / Metal / ROCm / CPU} — {device name}

## Output
- **File**: {path}
- **Size**: {bytes}
- **Format**: {png / mp4 / wav / ...}
- **Post-processing applied**: {none / interpolated to N fps / loudness-normalized to N LUFS / ...}
```

## Quality bar

- Model is Apache-2 / MIT / BSD / GPL — verified against `references/LICENSES.md`.
- Seed recorded for reproducibility.
- Full prompt (including system tokens, if model uses them) preserved verbatim in summary.
- Output re-probed: image dimensions match; video has expected duration/fps; audio has expected sample rate / bit depth.
- For video gen: model's actual generated resolution may be smaller than requested (LTX-Video tops at 768×512 stock); flag if upscale was applied to reach target.

## Playbook reference (folded from workflow-ai-generation)

# Workflow — AI Generation

**What:** Synthesize new media with open-source, commercial-safe AI models. Strict license filter: Apache-2 / MIT / BSD / GPL. NC / research-only models are always-dropped.

## Tool matrix

### TTS (`ai-generate`)

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

### Image (`ai-generate`)

| Model | License | Best for |
|---|---|---|
| FLUX-schnell | Apache-2 | default (4-step distilled) |
| Kolors | Apache-2 | bilingual EN/ZH |
| Sana | Apache-2 | fast 4K |
| ComfyUI | GPL-3 | node-graph workflows |

DROPPED: FLUX-dev (NC), SDXL / SD3 base (restrictive).

### Video (`ai-generate`)

| Model | License | Best for |
|---|---|---|
| LTX-Video | Apache-2 | fastest |
| CogVideoX | Apache-2 | high quality (slower) |
| Mochi | Apache-2 | cinematic |
| Wan | Apache-2 | versatile |

DROPPED: Stable Video Diffusion (NC research).

### Music / SFX (`ai-generate`)

| Model | License | Best for |
|---|---|---|
| Riffusion | Apache-2 | spectrogram-diffusion |
| YuE | Apache-2 | long-form structured |

DROPPED: Meta MusicGen (CC-BY-NC).

### Lipsync (`ai-lipsync`)

| Model | License |
|---|---|
| LivePortrait | MIT |
| LatentSync | Apache-2 |

DROPPED: Wav2Lip (research), SadTalker (NC).

### OCR (`ai-understand`)

| Model | License | Best for |
|---|---|---|
| PaddleOCR | Apache-2 | Latin + Chinese default |
| Tesseract 5 | Apache-2 | fastest classical |
| TrOCR | MIT | handwriting |
| EasyOCR | Apache-2 | multilingual |

DROPPED: Surya (commercial restriction).

### Tagging / captioning (`ai-understand`)

CLIP (MIT), SigLIP (Apache-2), BLIP-2 (BSD), LLaVA (Apache-2 but needs Llama-2 backbone — check license).

### Stem separation (`media-demucs`)

`htdemucs` 4-stem, `htdemucs_6s` 6-stem (adds guitar + piano).

### Speech-to-text (`media-whisper`)

whisper.cpp (MIT fastest CPU), faster-whisper (MIT CUDA-accelerated).

## Example composite workflows

### Explainer video from script

script → TTS voiceover (`ai-generate` Kokoro) → slide images (`ai-generate` FLUX-schnell) → B-roll clips (`ai-generate` LTX-Video) → host animation (`ai-lipsync` LivePortrait) → background music (`ai-generate` Riffusion) → assemble (`ffmpeg-edit`) → mix (`ffmpeg-filter` + sidechain ducking) → loudness normalize (`media-audio-cli`) → auto-burn subtitles (`media-whisper` + `ffmpeg-subtitle`) → transcode H.264 → YouTube upload (`media-cloud-upload`).

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
- **LivePortrait outputs 512×512 by default.** Upscale with `ai-enhance` for larger.
- **Whisper `large-v3` is 3 GB.** Test with `base.en` (140 MB) first — quality gap to `medium` (1.5 GB) is small for clean audio.
- **Whisper hallucinates on silence.** Trim leading/trailing with `silenceremove`.
- **Whisper word-level timestamps require `--word_timestamps True`** (faster-whisper) or `--max-len 1 --split-on-word` (whisper.cpp).
- **Whisper `--language auto` is fragile on accented speech.** Specify language explicitly.
- **Diarization is external to Whisper.** Use pyannote.audio (MIT) or simple-diarizer.
- **OCR selection:** PaddleOCR for Latin+Chinese, TrOCR for handwriting, Tesseract for speed on clean docs.
- **CLIP / SigLIP / BLIP-2 need fixed-resolution inputs** (224/336/384/448). The `tagctl.py` script resizes internally.
- **LLaVA needs an LLM backbone** (Vicuna / Llama-2 7B+). Llama-2 community license has revenue caps.
