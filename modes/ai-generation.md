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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-ai-generation/SKILL.md`. Read modality-specific skill:
   - image → `media-sd` (and `references/LICENSES.md`).
   - video → `media-svd` (and `references/LICENSES.md`).
   - tts → `media-tts-ai` (and `references/LICENSES.md`).
   - music → `media-musicgen` (and `references/LICENSES.md`).
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
9. For audio (TTS / music): normalize via `media-ffmpeg-normalize` if `loudness_target` specified.
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
