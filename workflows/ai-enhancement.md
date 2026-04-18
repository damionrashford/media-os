# AI Enhancement Workflow

**What:** Restore, upscale, and enhance existing footage using the 2026 state-of-the-art in open-source AI models — strictly filtered for commercial-safe licenses.

**Who:** Archival teams, remasterers, content owners preparing old libraries for modern platforms, YouTubers wanting 4K/60fps from HD/30fps sources, anyone who can't send media to commercial APIs.

**License constraint:** Every model in every Layer 9 skill passes an OSI-open + commercial-safe filter. **No XTTS-v2, no F5-TTS, no DAIN, no Stable Video Diffusion, no Wav2Lip, no SadTalker, no FLUX-dev, no MusicGen (Meta), no Surya, no CodeFormer.** These are enumerated-and-dropped in each skill's `references/LICENSES.md`.

---

## Skills used

| Role | Skill | Open-source models |
|---|---|---|
| Super-resolution | `media-upscale` | Real-ESRGAN (BSD-3), SwinIR (Apache-2), HAT (Apache-2) |
| Frame interpolation | `media-interpolate` | RIFE (MIT), FILM (Apache-2). *DAIN dropped (research-only)* |
| Background matting | `media-matte` | rembg (MIT), BiRefNet (MIT), RMBG-2.0 (Apache-2), RobustVideoMatting (GPL-3) |
| Depth estimation | `media-depth` | Depth-Anything v2 (Apache-2), MiDaS (MIT) |
| AI audio denoise | `media-denoise-ai` | DeepFilterNet (MIT/Apache-2), RNNoise (BSD), Resemble Enhance (MIT) |
| Stem separation | `media-demucs` | Demucs (MIT) |
| Classical denoise | `ffmpeg-denoise-restore` | nlmeans, bm3d, hqdn3d (built-in) |
| Stabilization | `ffmpeg-stabilize` | vid.stab (2-pass) |
| Inverse telecine | `ffmpeg-ivtc` | fieldmatch + decimate |
| Color + HDR | `ffmpeg-hdr-color`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro` | Tone map + LUT + OCIO |
| Final transcode | `ffmpeg-transcode`, `ffmpeg-hwaccel` | Modern codec delivery |
| Quality QC | `ffmpeg-quality` | VMAF/PSNR/SSIM vs reference |

---

## The pipeline

### 1. Probe the source — know what you're starting with

```bash
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full old.mp4
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report --file old.mp4
```

Identify: original resolution, frame rate (telecined? drop-frame?), codec artifacts (blocking? ringing? DCT? macroblocks?), audio noise floor, color space (BT.601? BT.709? SDR?), bit depth.

### 2. Reverse legacy artifacts BEFORE upscaling

Upscalers amplify artifacts. Clean first.

**Interlaced source:**
```bash
# Telecined 29.97i film → 23.976p
uv run .claude/skills/ffmpeg-ivtc/scripts/ivtc.py apply \
  --input old.mp4 --output old-progressive.mp4 --method fieldmatch-decimate

# True interlaced video → progressive (no cadence)
ffmpeg -i old.mp4 -vf "yadif=mode=1:parity=auto:deint=all" old-progressive.mp4
```

**Classical denoise (before AI upscale):**
```bash
uv run .claude/skills/ffmpeg-denoise-restore/scripts/denoise.py nlmeans \
  --input old-progressive.mp4 --output old-denoised.mp4 \
  --strength 4 --patch 7 --research 15
```

Classical denoise is cheap and preserves detail better than letting the upscaler infer through noise.

### 3. AI super-resolution

Pick the model based on content:

| Content | Best model | Reason |
|---|---|---|
| Anime / illustration | Real-ESRGAN (anime6b variant) | Trained on animation |
| Live-action | Real-ESRGAN (x4plus) or SwinIR | General purpose |
| Faces | Real-ESRGAN + GFPGAN (pip add-on, MIT) | Face-specific details. *CodeFormer is NC-restricted, dropped* |
| Text / UI / graphics | SwinIR | Preserves sharp edges |
| High-quality content needing sharper results | HAT | Heaviest / slowest / best |

```bash
# Real-ESRGAN 4x upscale
uv run .claude/skills/media-upscale/scripts/upscale.py realesrgan \
  --input old-denoised.mp4 \
  --output upscaled-4x.mp4 \
  --model RealESRGAN_x4plus \
  --tile 400 \
  --face-enhance
```

For frame-sequence processing (more control):
```bash
# Extract frames
ffmpeg -i old-denoised.mp4 frames/%06d.png

# Batch upscale (Real-ESRGAN CLI)
realesrgan-ncnn-vulkan -i frames/ -o upscaled/ -n realesrgan-x4plus -s 4

# Reassemble with original audio
ffmpeg -framerate 23.976 -i upscaled/%06d.png \
  -i old-denoised.mp4 -map 0:v -map 1:a \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
  -c:a copy upscaled-4x.mp4
```

### 4. Frame interpolation (30→60 / 24→60fps)

Use RIFE (recommended — MIT, open weights, fastest) or FILM (Apache-2, higher quality, slower):

```bash
# RIFE: 23.976 → 47.952fps (2x)
uv run .claude/skills/media-interpolate/scripts/interp.py rife \
  --input upscaled-4x.mp4 \
  --output smooth.mp4 \
  --target-fps 47.952 \
  --model rife-v4.6

# FILM: 30 → 60fps
uv run .claude/skills/media-interpolate/scripts/interp.py film \
  --input source.mp4 \
  --output smooth.mp4 \
  --target-fps 60
```

**Do not use DAIN** — research-only license, disallowed in this skill.

### 5. AI audio denoise / enhance

```bash
# DeepFilterNet — best general quality, permissive license
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
  --input noisy.wav \
  --output clean.wav

# RNNoise — ultra-light, BSD, embeddable
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py rnnoise \
  --input noisy.wav \
  --output clean.wav

# Resemble Enhance — speech-specific, MIT
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py resemble \
  --input speech.wav \
  --output enhanced.wav
```

For music (not speech), use Demucs stem separation first, then recombine cleanly:
```bash
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input song.wav --output-dir stems/
# Produces stems/vocals.wav, drums.wav, bass.wav, other.wav
```

### 6. Background removal (for green-screen-less subjects)

```bash
# Fastest: rembg (MIT)
uv run .claude/skills/media-matte/scripts/matte.py rembg \
  --input video.mp4 --output matted.mp4 --model u2net

# Best quality: RobustVideoMatting (GPL-3)
uv run .claude/skills/media-matte/scripts/matte.py rvm \
  --input video.mp4 --output matted.mp4 --model mobilenetv3

# BiRefNet or RMBG-2.0 for still images
uv run .claude/skills/media-matte/scripts/matte.py birefnet \
  --input image.jpg --output matted.png
```

### 7. Depth estimation (for 3D effect, relighting)

```bash
# Depth-Anything v2 (Apache-2, fastest best-quality)
uv run .claude/skills/media-depth/scripts/depth.py depthanything \
  --input video.mp4 --output depth.mp4 --model depth-anything-v2-small

# MiDaS (older but well-understood)
uv run .claude/skills/media-depth/scripts/depth.py midas \
  --input video.mp4 --output depth.mp4 --model dpt_large
```

Use depth for: fake 3D parallax, relighting, occlusion-aware VFX.

### 8. Color + HDR finish

Upscaled + interpolated content often has crushed shadows from YouTube-era compression. Restore dynamic range:

```bash
# LUT-based (if you have a matching LUT)
uv run .claude/skills/ffmpeg-lut-grade/scripts/lut.py apply \
  --input smooth.mp4 --lut warm-cinematic.cube --output graded.mp4

# OCIO ACES pass (for professional finish)
export OCIO=/path/to/aces/config.ocio
uv run .claude/skills/ffmpeg-ocio-colorpro/scripts/ociogo.py transform \
  --input smooth.mp4 --output graded.mp4 \
  --from "Output - Rec.709" --to "Output - Rec.2020 ST2084"

# Tone-map expand to HDR (experimental, works well on cinematic content)
uv run .claude/skills/ffmpeg-hdr-color/scripts/hdrcolor.py sdr-to-hdr \
  --input smooth.mp4 --output hdr.mp4 --target hlg
```

### 9. Quality QC vs source

```bash
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference old.mp4 --distorted enhanced.mp4 --json > vmaf.json
```

Expect VMAF in the 80-95 range. Lower = you lost content; higher = faithful enhancement.

### 10. Final transcode

```bash
# Modern delivery (H.264 10-bit for broad compat)
ffmpeg -i enhanced.mp4 \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p10le \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  deliverable.mp4

# Or AV1 for bandwidth-constrained delivery
ffmpeg -i enhanced.mp4 \
  -c:v libsvtav1 -crf 28 -preset 6 -pix_fmt yuv420p10le \
  -c:a libopus -b:a 128k \
  deliverable.webm
```

---

## Variants

### Animation-specific pipeline

Anime and Western animation benefit from specialty models:

```bash
# Real-ESRGAN anime variant
uv run .claude/skills/media-upscale/scripts/upscale.py realesrgan \
  --input anime.mp4 --output upscaled.mp4 \
  --model realesr-animevideov3

# Interpolation on anime wants smooth, NOT per-frame detection
uv run .claude/skills/media-interpolate/scripts/interp.py rife \
  --input upscaled.mp4 --output interp.mp4 --model rife-v4.6 --uhd
```

### Face-focused restoration

For talking-head content, run face-specific restoration after upscale:

```bash
# GFPGAN (MIT) — good, use this
# CodeFormer (NC-research) — DO NOT USE
uv run .claude/skills/media-upscale/scripts/upscale.py gfpgan \
  --input head.mp4 --output fixed-faces.mp4 --upscale 2
```

### Archive-to-4K path (old DVD/VHS)

```bash
# VHS path:
# 1. Detect cadence
ffmpeg -i vhs.mkv -vf "idet" -f null - 2>&1 | grep "Multi frame detection"

# 2. De-interlace (likely true-interlaced, not telecined)
ffmpeg -i vhs.mkv -vf "yadif=mode=1" vhs-progressive.mkv

# 3. Classical denoise (heavy — VHS has lots of noise)
ffmpeg -i vhs-progressive.mkv -vf "hqdn3d=4:3:6:4.5" vhs-denoised.mkv

# 4. Upscale 480p → 1440p (NOT 4K — SD source doesn't have the detail)
uv run .claude/skills/media-upscale/scripts/upscale.py realesrgan \
  --input vhs-denoised.mkv --output vhs-1440.mp4 \
  --model RealESRGAN_x4plus --scale 3

# 5. Final color correction
# ...
```

### Game capture 30 → 120fps

```bash
# RIFE can push higher factors
uv run .claude/skills/media-interpolate/scripts/interp.py rife \
  --input game.mp4 --output game-120.mp4 \
  --target-fps 120 --model rife-v4.6
```

### Stabilize handheld footage before upscale

```bash
# 2-pass vid.stab
uv run .claude/skills/ffmpeg-stabilize/scripts/stabilize.py 2pass \
  --input shaky.mp4 --output stable.mp4 --shakiness 5

# Then upscale the stabilized result (stabilization introduces crop; upscale handles it)
```

---

## Gotchas

### License landmines

- **CodeFormer (NC-restricted)**: dropped from `media-upscale`. Use GFPGAN instead for face restoration.
- **DAIN (research-only)**: dropped from `media-interpolate`. Use RIFE or FILM.
- **XTTS-v2 (CPML NC)**: dropped from `media-tts-ai`. Multiple alternatives listed.
- **Stable Video Diffusion (NC research)**: dropped from `media-svd`. Use LTX-Video / CogVideoX / Mochi / Wan.
- **Wav2Lip / SadTalker (research-only)**: dropped from `media-lipsync`. Use LivePortrait / LatentSync.
- **MusicGen from Meta (CC-BY-NC)**: dropped from `media-musicgen`. Use Riffusion or YuE.
- **Surya OCR (commercial restriction)**: dropped from `media-ocr-ai`. Use PaddleOCR / EasyOCR / Tesseract / TrOCR.
- Always check `references/LICENSES.md` in each Layer 9 skill before adopting a new model.

### Technical landmines

- **Upscaling amplifies noise.** Always denoise first. Upscaler + noisy source = HD noise.
- **RIFE / FILM interpolation fails on scene cuts.** Watch for ghost frames at cut points. Use scene-aware wrappers (RIFE handles this, FILM doesn't).
- **Real-ESRGAN default tile size of 400 is fine for most GPUs.** Drop to 200 if VRAM-bound; the model doesn't "see" the whole frame, it runs on tiles with overlap and blends.
- **`-pix_fmt yuv420p` after AI upscale** — many AI models output RGB or YUV 4:4:4. Consumer players need 4:2:0; convert explicitly or get color banding.
- **10-bit upscale output, 8-bit codec = banding.** If you upscale to 10-bit, deliver in 10-bit (`libx264` with `-pix_fmt yuv420p10le` plus a compatible profile).
- **Frame rate target must be divisible for clean integer math.** 23.976 → 47.952 (exact 2x). 23.976 → 60 (2.504x) = model has to interpolate fractional positions; quality suffers. Round to clean ratios when possible.
- **DeepFilterNet processes 16kHz or 48kHz mono only.** Feed it the right format or it downsamples badly.
- **RNNoise is 48kHz mono 16-bit** — hardcoded. Resample first or it fails.
- **Demucs expects 44.1kHz or 48kHz stereo.** Mono → wrong stems.
- **RobustVideoMatting is GPL-3.** If you ship the skill's output embedded in a proprietary product, GPL-3 terms propagate. Commercial OK if linking dynamically; static linking or SaaS with modifications = full GPL exposure. Read the license.
- **rembg default `u2net` is fine; `isnet-general-use` is better quality** but heavier.
- **BiRefNet is image-only.** For video matting, iterate per-frame; expect temporal flicker (use temporal-coherence models like RVM for video).
- **Depth-Anything v2 outputs relative depth, not absolute metric depth.** Good for visual effects; not for measurement. For metric, use `depth-anything-v2-metric` with explicit dataset prior.
- **Models on Hugging Face can change license without notice.** `references/LICENSES.md` pins the exact commit hash that was OSI-clean at audit time.
- **AI inference benefits 10x+ from GPU.** On CPU, Real-ESRGAN at 1080p30s takes hours. Feed GPU-bound jobs through `--tile` + batching.
- **`ffmpeg -hwaccel` is decode-only; AI models run on their own CUDA/Metal/ROCm paths.** Don't expect ffmpeg's hwaccel to speed up PyTorch inference.
- **Apple Silicon (M1-M4) runs most models via Metal Performance Shaders (MPS).** Set `PYTORCH_ENABLE_MPS_FALLBACK=1` for models that haven't been fully ported.

---

## Example — "Restore old 720p 30fps clip to modern 4K 60fps HDR"

```bash
#!/usr/bin/env bash
set -e

SOURCE="old-720p30.mp4"
DENOISED="tmp-denoised.mp4"
UPSCALED="tmp-upscaled.mp4"
INTERP="tmp-60fps.mp4"
FINAL="restored-4k60-hdr.mp4"

# 1. Probe
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$SOURCE"

# 2. Denoise (classical, preserves detail)
ffmpeg -i "$SOURCE" -vf "nlmeans=s=4:p=7:r=15" \
  -c:v libx264 -crf 15 -preset slow -c:a copy "$DENOISED"

# 3. AI upscale 720p → 2880p (3x, approximating 4K)
uv run .claude/skills/media-upscale/scripts/upscale.py realesrgan \
  --input "$DENOISED" --output "$UPSCALED" \
  --model RealESRGAN_x4plus --scale 3 --tile 400 --face-enhance

# 4. AI frame interpolation 30 → 60fps
uv run .claude/skills/media-interpolate/scripts/interp.py rife \
  --input "$UPSCALED" --output "$INTERP" \
  --target-fps 60 --model rife-v4.6

# 5. SDR → HLG HDR
uv run .claude/skills/ffmpeg-hdr-color/scripts/hdrcolor.py sdr-to-hdr \
  --input "$INTERP" --output tmp-hlg.mp4 --target hlg

# 6. AI audio denoise
ffmpeg -i tmp-hlg.mp4 -vn -c:a pcm_s16le -ar 48000 -ac 1 tmp-noisy.wav
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
  --input tmp-noisy.wav --output tmp-clean.wav

# 7. Mux final (4K HLG HEVC + clean audio)
ffmpeg -i tmp-hlg.mp4 -i tmp-clean.wav \
  -map 0:v -map 1:a \
  -c:v libx265 -crf 22 -preset slow -pix_fmt yuv420p10le \
  -x265-params "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc" \
  -c:a aac -b:a 256k \
  -movflags +faststart \
  "$FINAL"

# 8. QC
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference "$SOURCE" --distorted "$FINAL" --json

# 9. Cleanup
rm tmp-*.mp4 tmp-*.wav
```

---

## Further reading

- [`ai-generation.md`](ai-generation.md) — generation models (TTS, image, video, music)
- [`podcast-pipeline.md`](podcast-pipeline.md) — audio-focused enhancement
- [`hdr-workflows.md`](hdr-workflows.md) — HDR targeting / tone-map decisions
- [`analysis-quality.md`](analysis-quality.md) — VMAF / PSNR / SSIM QC
- Each skill's `references/LICENSES.md` for the canonical open-source audit
