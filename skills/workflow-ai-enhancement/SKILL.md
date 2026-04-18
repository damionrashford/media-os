---
name: workflow-ai-enhancement
description: Restore, upscale, and enhance existing footage using 2026 open-source AI models — Real-ESRGAN/SwinIR/HAT super-resolution, RIFE/FILM interpolation, DeepFilterNet/RNNoise audio denoise, rembg/BiRefNet/RVM matting, Depth-Anything v2 depth — with strict OSI-open commercial-safe license filter. Use when the user says "upscale old footage", "remaster", "enhance quality", "30 to 60fps", "AI denoise", "restore VHS", "remove background from video", or anything about AI-driven footage restoration.
argument-hint: [source]
---

# Workflow — AI Enhancement

**What:** Take existing footage and make it visually/sonically better using open-source AI. Strict license discipline: Apache-2 / MIT / BSD / GPL only. NC / research-only models are documented-and-dropped.

## Skills used

`media-upscale`, `media-interpolate`, `media-matte`, `media-depth`, `media-denoise-ai`, `media-demucs`, `ffmpeg-denoise-restore`, `ffmpeg-stabilize`, `ffmpeg-ivtc`, `ffmpeg-hdr-color`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro`, `ffmpeg-transcode`, `ffmpeg-hwaccel`, `ffmpeg-quality`.

## Pipeline

### Step 1 — Probe source

`ffmpeg-probe`. Capture resolution, frame rate, codec artifacts, audio noise floor, color space (BT.601 / BT.709 / SDR), bit depth, chroma.

### Step 2 — Undo legacy artifacts BEFORE AI

- **Telecined 29.97i → 23.976p** — `ffmpeg-ivtc` (`fieldmatch → decimate`).
- **True interlaced** — `yadif` via `ffmpeg-video-filter`.
- **Compression noise** — `ffmpeg-denoise-restore` (`nlmeans`, `hqdn3d`).
- **Unstable handheld** — `ffmpeg-stabilize` two-pass (`vidstabdetect` → `vidstabtransform`).

### Step 3 — AI super-resolution

Use `media-upscale`:
- **Real-ESRGAN x4plus** — live-action default.
- **Real-ESRGAN anime6b** — animation.
- **SwinIR** — graphics / text.
- **HAT** — best-quality slowest.
- **Face-enhance** — for close-ups; never use CodeFormer (NC).

### Step 4 — Frame interpolation

`media-interpolate`:
- **RIFE v4.6** (MIT) — handles scene cuts.
- **FILM** (Apache-2) — slightly smoother, drops on scene cuts.

Target integer multiples for clean math (23.976 → 47.952 exact 2×). 23.976 → 60 is 2.504× — quality suffers on fractional positions.

### Step 5 — AI audio denoise

`media-denoise-ai`:
- **DeepFilterNet** — general, 16 kHz or 48 kHz MONO only.
- **RNNoise** — lightweight, hardcoded 48 kHz mono 16-bit.
- **Resemble Enhance** — speech super-res.

Isolate stems first with `media-demucs` if source is mixed.

### Step 6 — Background removal (optional)

`media-matte`:
- **rembg** (MIT) — fastest.
- **BiRefNet / RMBG-2.0** — stills only; per-frame for video produces temporal flicker.
- **RVM (RobustVideoMatting)** — temporally coherent, GPL-3 (propagates if shipped embedded; commercial OK via dynamic linking).

### Step 7 — Depth estimation (optional)

`media-depth`:
- **Depth-Anything v2** (Apache-2) — fastest, relative depth.
- **MiDaS** — for relighting / 3D reprojection.

### Step 8 — Color + HDR finish

LUT (`ffmpeg-lut-grade`), OCIO ACES (`ffmpeg-ocio-colorpro`), or SDR→HLG tone-map (`ffmpeg-hdr-color`).

### Step 9 — QC + final encode

`ffmpeg-quality` VMAF vs source (80–95 expected). `ffmpeg-transcode` to delivery: H.264 10-bit `yuv420p10le` for broad compat, AV1 for bandwidth-constrained.

## Variants

- **Animation** — Real-ESRGAN anime variant + RIFE with smooth motion.
- **Face-focused** — GFPGAN (MIT) for talking heads. NEVER CodeFormer (NC).
- **VHS → 4K archive** — detect cadence → `yadif` → heavy `hqdn3d` → upscale 480p → 1440p → color correct.
- **Game capture 30 → 120 fps** — RIFE with higher factors.
- **Handheld + upscale** — stabilize FIRST (crop introduced), THEN upscale.

## Gotchas

- **License landmines — always-drop list:** CodeFormer (NC), DAIN (research), XTTS-v2 / F5-TTS (CPML NC), Stable Video Diffusion (NC), Wav2Lip / SadTalker (research), MusicGen Meta (CC-BY-NC), Surya (commercial restriction). Each AI skill's `references/LICENSES.md` pins the allow-list.
- **Upscaling amplifies noise.** ALWAYS denoise first — upscaler + noisy source = HD noise.
- **RIFE handles scene cuts; FILM doesn't.** Watch for ghost frames on FILM output.
- **Real-ESRGAN default tile size 400** — drop to 200 if VRAM-bound. Model doesn't "see" the whole frame; artifacts at tile borders on wild tile sizes.
- **After AI upscale, force `-pix_fmt yuv420p`** (or `yuv420p10le` for 10-bit deliver). AI models often output RGB or YUV 4:4:4; consumer players need 4:2:0.
- **10-bit upscale into 8-bit codec = banding.** If upscale to 10-bit, deliver in 10-bit: `libx264 -pix_fmt yuv420p10le` or equivalent HEVC.
- **DeepFilterNet expects 16 kHz or 48 kHz MONO.** Feed right format or it downsamples badly.
- **RNNoise hardcoded 48 kHz mono 16-bit.** Resample first or it fails silently.
- **Demucs expects 44.1 kHz or 48 kHz STEREO.** Mono input → degraded stems.
- **RVM is GPL-3.** If shipped embedded in proprietary code, GPL-3 propagates. Commercial OK via dynamic linking.
- **rembg default `u2net`** is fine; `isnet-general-use` is better but heavier.
- **BiRefNet is image-only.** Per-frame video = temporal flicker. Use RVM for temporal coherence.
- **Depth-Anything v2 outputs RELATIVE depth.** Good for VFX; NOT for measurement.
- **Hugging Face model licenses can change without notice.** Pin exact commit hash in `references/LICENSES.md`.
- **AI inference benefits 10× from GPU.** On CPU, Real-ESRGAN 1080p30s = hours.
- **`ffmpeg -hwaccel` is decode-only.** AI models run on their own CUDA / Metal / ROCm paths.
- **Apple Silicon (M1–M4) MPS:** set `PYTORCH_ENABLE_MPS_FALLBACK=1` for unported ops.

## Example — Upscale + interpolate old 720p30 → 4K60

Probe source → denoise with `hqdn3d` → Real-ESRGAN x4plus to 2880×? tile=400 → RIFE v4.6 ×2 → LUT grade → ffmpeg-transcode to HEVC 10-bit HDR-ready `yuv420p10le`. VMAF check against source at 720p (upscale reference). Deliver.

## Related

- `workflow-ai-generation` — pure AI-generated media (not enhancement of existing).
- `workflow-vod-post-production` — traditional color/stabilize/denoise path without AI.
- `workflow-hdr` — if AI output needs HDR mastering.
