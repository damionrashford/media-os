---
name: ai-generate
description: >
  Use when generating AI images, video, speech, or music from text with strictly
  open-source, commercial-safe models. Image: text-to-image, AI art, img2img,
  ControlNet, LoRA, ComfyUI workflows, FLUX-schnell, Kolors, Sana, Lumina, HunyuanDiT,
  PixArt. Video: text-to-video, image-to-video, animate a still, short AI clip,
  LTX-Video, CogVideoX, Mochi, Wan-Video, AnimateDiff. Speech: synthesize speech,
  voiceover, narration, audiobook, clone a voice, read text aloud, TTS, Kokoro,
  OpenVoice, Piper, CosyVoice, Chatterbox, Bark, Orpheus, Parler-TTS, StyleTTS2.
  Music: generate music, AI songs, background music, jingle, royalty-free music,
  full song with vocals, Riffusion, YuE, Stable Audio Open. Use when the user asks
  to generate AI art, do text-to-image, build a ComfyUI workflow, make an AI video
  clip, animate an image, create a voiceover, clone a voice, or produce
  open-source / Apache-licensed / OSI-open music.
argument-hint: "[prompt] [output]"
---

# AI Generate

Generate images, video, speech, and music from text using only open-source, commercial-safe models. Pick the technique, load its reference, run the matching script.

## When to use

- Generate images from text (text-to-image, img2img, ControlNet, LoRA, ComfyUI workflows).
- Generate video from text or animate a still (t2v, i2v, AnimateDiff).
- Synthesize speech, narration, audiobooks, or clone a voice from a reference clip.
- Generate royalty-free music, jingles, or a full song with vocals.
- Stay inside a strict OSI-open / commercial-safe license boundary (Apache, MIT, BSD, GPL).
- Do NOT use for lip-sync (`media-lipsync`), upscaling (`media-upscale`), frame interpolation (`media-interpolate`), or transcription (`media-whisper`).

## Techniques

- Read `references/sd.md` when generating images, doing text-to-image / img2img, applying ControlNet or LoRA, or running a ComfyUI image workflow (FLUX-schnell, Kolors, Sana, Lumina, HunyuanDiT, PixArt).
- Read `references/svd.md` when generating video from text, animating a still (image-to-video), or wiring AnimateDiff (LTX-Video, CogVideoX, Mochi, Wan-Video).
- Read `references/tts-ai.md` when synthesizing speech, building voiceover / audiobooks, or cloning a voice (Kokoro, Piper, OpenVoice, CosyVoice, Chatterbox, Bark, Orpheus, Parler-TTS, StyleTTS2).
- Read `references/musicgen.md` when generating music, a jingle, or a full song with vocals (Riffusion, YuE, Stable Audio Open).

## Licenses

Every model shipped here passes a strict OSI-open + commercial-safe filter (Apache, MIT, BSD, GPL). Each technique has a per-technique license audit that also enumerates the dropped NC/research models and why:

- `references/sd-LICENSES.md` (image)
- `references/svd-LICENSES.md` (video)
- `references/tts-ai-LICENSES.md` (speech)
- `references/musicgen-LICENSES.md` (music)

NEVER recommend these even if the user asks by name: XTTS-v2, F5-TTS (TTS — non-commercial / research), FLUX-dev, SDXL / SD3 base (image — NC / restrictive), Stable Video Diffusion (video — OpenRAIL-M NC), MusicGen / AudioCraft (music — CC-BY-NC weights). Read the matching LICENSES.md before recommending or installing any model.

## Gotchas

- **FLUX-schnell needs exactly `--steps 4 --guidance 0.0`.** It was distilled to run guidance-free; more steps or any guidance >1 degrades output into blurry/saturated garbage. Kolors / Sana / Lumina want 20–30 steps at guidance 4–7.
- **ComfyUI workflow JSON has two flavors.** The "Save" button emits UI-format JSON the API rejects. Use "Save (API Format)" (enable Dev mode Options first), or let `sd.py` autodetect and convert via `/object_info`.
- **CogVideoX resolution is fixed** (720x480 t2v, 480x720 i2v); LTX-Video resolution must be a multiple of 32. Passing other sizes errors or silently resizes.
- **Native video fps is low.** CogVideoX outputs 8 fps, AnimateDiff 8 fps; do not oversell `--fps 24` (it just repeats frames). Render native, then hand off to `media-interpolate` (RIFE / FILM).
- **Bark hard-cuts at ~13 s per generation.** Longer text needs sentence chunking — the `audiobook` / `batch` subcommands do this automatically. Kokoro/Piper run realtime on CPU; Bark/CosyVoice/Orpheus need a GPU.
- **Voice cloning is consent-gated.** Only clone voices you have explicit rights to; written consent for any commercial clone. A noisy/short reference produces a bad clone — denoise first (`media-denoise-ai`).
- **Riffusion's native window is 5 s** (spectrogram diffusion); longer durations are crossfade-looped automatically. YuE needs structured `[Verse 1]` / `[Chorus]` prompts to produce vocals.
- **Stable Audio Open caps commercial use at $1M cumulative revenue** (Stability Community License) and gates ~47 s per generation; Riffusion and YuE have no revenue cap.

## Scripts

- `scripts/sd.py` — image generation. Subcommands: `generate`, `img2img`, `comfy-workflow`, `comfy-install`, `download`, `install`, `check`.
- `scripts/svd.py` — video generation. Subcommands: `t2v`, `i2v`, `animate`, `install`, `download`, `check`.
- `scripts/tts.py` — speech / voice cloning. Subcommands: `speak`, `clone`, `audiobook`, `batch`, `list-voices`, `install`, `check`.
- `scripts/musicgen.py` — music generation. Subcommands: `generate`, `continue`, `stems`, `install`, `check`.

All scripts are stdlib-only with PEP 723 headers, support `--dry-run` / `--verbose`, and run non-interactive.
