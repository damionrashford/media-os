---
name: ai-enhance
description: >
  Use when the user asks to upscale an image or video, super-resolution, AI upscale, 4K-ify, enhance an old photo, restore a face, sharpen, upscale anime, rescale game textures (Real-ESRGAN, Real-CUGAN, SwinIR, HAT, GFPGAN, waifu2x); interpolate frames, AI slow-motion, boost framerate, smooth 24 to 60fps or 30 to 60fps, frame-double, motion-compensated tweens, in-between two images (RIFE, FILM, PractCL); or remove audio noise, denoise voice, clean up a podcast, restore old or lo-fi audio, suppress hum/hiss/clicks, dereverb, fix muffled speech (DeepFilterNet, RNNoise, Resemble Enhance). Open-source, commercial-safe models that beat ffmpeg's built-in SRCNN/ESPCN/EDSR upscalers, minterpolate, and afftdn/arnndn denoisers.
argument-hint: "[technique] [input] [output]"
---

# AI Enhance

**Context:** $ARGUMENTS

Three AI media-enhancement techniques behind one skill: super-resolution upscaling, frame interpolation, and audio denoising. Every recommended model is OSI-open and commercial-safe.

## When to use

- Upscale / super-resolve a photo, video, anime, or texture beyond a plain `scale` resize, or restore a face.
- Interpolate frames for smoother framerate (24→60), AI slow-motion, or tween between two stills.
- Denoise speech audio, clean a podcast, restore lo-fi/muffled recordings, or dereverb.
- The user is dissatisfied with ffmpeg built-ins (SRCNN/ESPCN/EDSR, `minterpolate`, `afftdn`/`arnndn`).
- Do NOT use for plain resizing (`ffmpeg-video-filter`), speed change at constant fps (`ffmpeg-speed-time`), or music source separation (`media-demucs`).

## Techniques

- Read `references/upscale.md` when upscaling, super-resolving, sharpening, 4K-ifying, restoring an old photo or face, or rescaling anime/game textures.
- Read `references/interpolate.md` when interpolating frames, boosting framerate, creating AI slow-motion, frame-doubling, or tweening between two images.
- Read `references/denoise-ai.md` when removing audio noise, cleaning a podcast, restoring lo-fi audio, suppressing hum/hiss/clicks, dereverbing, or fixing muffled speech.

## Licenses

Every model in this skill is OSI-open and commercial-safe (BSD-3 / MIT / Apache-2.0, plus AGPL/GPL GUI wrappers usable as apps). Research-only and proprietary tools (CodeFormer, Topaz, DAIN, Krisp, NVIDIA Broadcast, Adobe Enhance) are explicitly excluded. See the per-technique audits: `references/upscale-LICENSES.md`, `references/interpolate-LICENSES.md`, `references/denoise-ai-LICENSES.md`. Per-model detail tables: `references/upscale-models.md`, `references/interpolate-models.md`, `references/denoise-ai-models.md`.

## Gotchas

- **ffmpeg built-ins are outdated.** `dnn_processing` SRCNN/ESPCN/EDSR (2014–2017), `minterpolate` (2015 block-matching), and `afftdn`/`arnndn` all lose to the AI models here on real content. Recommend the built-ins only as a no-GPU fallback.
- **All three pipelines are frame/segment-based.** Upscale and interpolate extract PNGs, process, then remux — pull the **exact** source FPS from `ffprobe` before reassembly; never assume 23.976/25/29.97.
- **Scale factor must match the model.** `realesrgan-x4plus` is 4x-only — passing `-s 2` downsamples a 4x output. After odd-dimension upscales, add `scale=trunc(iw/2)*2:trunc(ih/2)*2` so libx264 accepts yuv420p.
- **Interpolation across a scene cut smears.** RIFE/FILM blend unrelated frames; run `media-scenedetect` and process each scene independently.
- **Slow-motion drops audio by default.** Stretching the video timeline while keeping audio at native rate desyncs A/V — re-apply `atempo=1/factor` afterwards (chain `atempo=0.5,atempo=0.5` for 0.25x).
- **Speech denoisers eat music.** DeepFilterNet and Resemble Enhance treat music/ambience as noise — process voice-only segments, or split stems with `media-demucs` first. Never chain two AI denoisers in series.
- **Normalize VFR sources first.** Variable-framerate captures break the frame-pair pipelines: `ffmpeg -i in.mp4 -vsync cfr -r <src_fps> cfr.mp4`. De-interlace (`ffmpeg-ivtc`/`yadif`) before interpolating.
- **Face restoration hallucinates.** GFPGAN invents plausible detail — never use it on ID photos, evidence, or fidelity-critical work without sign-off.

## Scripts

- `scripts/upscale.py` — subcommands `image | video | batch | face-restore | install | check` (Real-ESRGAN / Real-CUGAN / SwinIR / HAT / GFPGAN / waifu2x).
- `scripts/interp.py` — subcommands `video | slow-mo | images | install | check` (RIFE / FILM / PractCL).
- `scripts/denoise.py` — subcommands `denoise | enhance | batch | install | check` (DeepFilterNet / RNNoise / Resemble Enhance).

All support `--dry-run` and `--verbose`. Run with `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py <subcommand>`.
