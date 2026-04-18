---
name: media-upscale
description: >
  AI super-resolution for images and video beyond ffmpeg's outdated built-in DNN models (SRCNN 2014 / ESPCN 2016 / EDSR 2017). Open-source + commercial-safe only: Real-ESRGAN (BSD-3-Clause, the current default for photos/video), Real-CUGAN (MIT, anime-optimized), SwinIR (Apache 2.0, transformer-based), HAT (Apache 2.0, 2023 SOTA), GFPGAN (Apache 2.0, face restoration), waifu2x-ncnn-vulkan (MIT, classic anime), Upscayl (AGPL-3.0, GUI wrapper around Real-ESRGAN), chaiNNer (GPL-3.0, node pipeline for arbitrary models). Realistic 2x / 4x / 8x SR for photos, film scans, low-res archives, anime, screenshots, game textures. Use when the user asks to upscale an image, super-resolution a video, enhance an old photo, restore a face, upscale anime, rescale game textures, do AI upscaling, or when ffmpeg's built-in SRCNN/ESPCN/EDSR isn't good enough.
argument-hint: "[model] [input] [output]"
---

# Media Upscale

**Context:** $ARGUMENTS

## Quick start

- **Photo 2x/4x → upscaled PNG:** Real-ESRGAN → Step 2 recipe A.
- **Anime / cel-shaded art:** Real-CUGAN → Step 2 recipe B.
- **Restore a face in a blurry photo:** GFPGAN → Step 2 recipe E.
- **Upscale a whole video:** Real-ESRGAN frame pipeline → Step 3.
- **Batch a folder of images:** `scripts/upscale.py batch` → Step 4.

## When to use

- User says "upscale", "super-res", "enhance", "4K-ify", "make it sharper", "AI upscale".
- Source is lower resolution than the target medium (SD → HD, HD → 4K, 480p anime → 1080p).
- ffmpeg's `dnn_processing` (SRCNN/ESPCN/EDSR) or a plain `scale=...:flags=lanczos` looks soft / blurry on real content.
- Face-only restoration of a scanned photo or low-res portrait.
- Do NOT use this skill for mere resizing without quality gain — use `ffmpeg-video-filter` (`scale`) instead.
- Do NOT use for temporal frame interpolation — that is `media-interpolate`.

## Step 1 — Pick a model

| Model                 | License         | Best for                          | GPU needed? | Notes                                       |
|-----------------------|-----------------|-----------------------------------|-------------|---------------------------------------------|
| Real-ESRGAN           | BSD-3-Clause    | Photos, video frames, real-world  | Optional    | `realesrgan-ncnn-vulkan` — default. 2x/4x.  |
| Real-CUGAN            | MIT             | Anime, illustration, cel-art      | Optional    | `realcugan-ncnn-vulkan` — 2x/3x/4x, denoise  |
| SwinIR                | Apache 2.0      | Fine-texture photo SR             | Yes (CUDA)  | Transformer, Python inference, slower       |
| HAT                   | Apache 2.0      | SOTA photo SR (2023)              | Yes (CUDA)  | Hybrid Attention Transformer, Python        |
| GFPGAN                | Apache 2.0      | Face restoration in photos        | Yes (CUDA)  | Face-only; combines with Real-ESRGAN bg     |
| waifu2x-ncnn-vulkan   | MIT             | Classic anime, small images       | Optional    | Original 2015-era anime upscaler            |
| Upscayl               | AGPL-3.0        | GUI for Real-ESRGAN               | Optional    | Desktop app; script skill stays CLI         |
| chaiNNer              | GPL-3.0         | Node-graph pipeline, ANY SR model | Optional    | Run arbitrary PyTorch/ONNX/NCNN SR models   |

**Decision rules:**

1. Real photos / video frames → **Real-ESRGAN** (`realesr-animevideov3` for cartoons, `realesrgan-x4plus` for photos, `realesrgan-x4plus-anime` for anime stills).
2. Anime or illustration → **Real-CUGAN** (sharper cel edges than Real-ESRGAN), fall back to **waifu2x-ncnn-vulkan** for very small sources.
3. Faces are the focal point (portrait, ID card, old family photo) → **GFPGAN** (then blend with a Real-ESRGAN-upscaled background).
4. Need academic SOTA quality, don't mind Python/CUDA → **HAT** or **SwinIR**.
5. Multi-model pipeline (segment → upscale → denoise → sharpen chain) → **chaiNNer**.

**Do NOT use:** CodeFormer (S-Lab License, research-only — not commercial-safe), Topaz Video AI (commercial, paid). This skill covers open-source + commercial-safe only.

## Step 2 — Install the chosen binary / package

`scripts/upscale.py install <model>` prints the exact package-manager command for your platform. It does **not** auto-install. Examples:

```bash
# Real-ESRGAN (ncnn-vulkan prebuilt — fastest install, zero Python)
# macOS:
brew install realesrgan-ncnn-vulkan          # if tap available, else download release
# or grab a release zip from: https://github.com/xinntao/Real-ESRGAN/releases

# Real-CUGAN (ncnn-vulkan)
# Download: https://github.com/nihui/realcugan-ncnn-vulkan/releases

# waifu2x-ncnn-vulkan
brew install waifu2x                           # macOS; tap: nihui/waifu2x-ncnn-vulkan

# GFPGAN (Python)
uv pip install gfpgan basicsr realesrgan facexlib

# SwinIR / HAT (Python + CUDA)
uv pip install torch opencv-python numpy basicsr
git clone https://github.com/JingyunLiang/SwinIR      # weights via model zoo
git clone https://github.com/XPixelGroup/HAT         # weights via releases page

# chaiNNer
# Download from: https://chainner.app/
```

### Recipe A — Real-ESRGAN 4x on a photo

```bash
realesrgan-ncnn-vulkan \
  -i photo.jpg -o photo_4x.png \
  -n realesrgan-x4plus -s 4 -f png
# Available -n models: realesrgan-x4plus, realesrnet-x4plus, realesr-animevideov3,
#                      realesrgan-x4plus-anime
# -s scale: 2, 3, 4
# -t tile: 0 auto, or e.g. 256 to limit VRAM. Set -g <GPU_ID> for multi-GPU.
# -f format: png | jpg | webp
```

Through the driver script:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py image \
  --model realesr --scale 4 --in photo.jpg --out photo_4x.png
```

### Recipe B — Real-CUGAN on anime

```bash
realcugan-ncnn-vulkan \
  -i anime.png -o anime_4x.png \
  -n 0 -s 4 -f png
# -n 0 default, -n 3 for heavy denoise, -n -1 conservative; -s 2|3|4.
```

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py image \
  --model realcugan --scale 4 --in anime.png --out anime_4x.png
```

### Recipe C — SwinIR (Python)

```bash
python SwinIR/main_test_swinir.py \
  --task real_sr --scale 4 --large_model \
  --model_path SwinIR/model_zoo/swinir/003_realSR_BSRGAN_DFO_s64w8_SwinIR-L_x4_GAN.pth \
  --folder_lq /path/to/input_dir --tile 400
```

### Recipe D — HAT (Python)

```bash
python HAT/hat/test.py -opt HAT/options/test/HAT_SRx4.yml
```

### Recipe E — GFPGAN face restoration + Real-ESRGAN background

```bash
python GFPGAN/inference_gfpgan.py \
  -i inputs/ -o results/ \
  -v 1.4 -s 2 --bg_upsampler realesrgan
# -v model version: 1.2, 1.3, 1.4; -s output scale factor.
# --bg_upsampler realesrgan re-uses Real-ESRGAN for non-face pixels.
```

Driver:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py face-restore \
  --model gfpgan --in portrait.jpg --out portrait_restored.png --scale 2
```

## Step 3 — Upscale a video (frame pipeline)

AI SR models are frame-based. Video workflow:

1. **Extract frames** with ffmpeg (lossless PNGs).
2. **Upscale each frame** with Real-ESRGAN / Real-CUGAN.
3. **Remux** the upscaled frame sequence with the original audio.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py video \
  --model realesr --scale 4 --in clip.mp4 --out clip_4x.mp4 \
  --model-name realesr-animevideov3
```

What the script does:

```bash
# (1) frames out
ffmpeg -i clip.mp4 -qscale:v 1 -qmin 1 -qmax 1 -vsync 0 frames/%08d.png
# (2) upscale frames
realesrgan-ncnn-vulkan -i frames -o frames_4x -n realesr-animevideov3 -s 4 -f png
# (3) remux with original audio, pick an FPS matching the source
ffmpeg -framerate <src_fps> -i frames_4x/%08d.png -i clip.mp4 \
       -map 0:v -map 1:a? -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
       -c:a copy -movflags +faststart clip_4x.mp4
```

**VRAM control:** add `-t 256` (tile size) to the Real-ESRGAN step if GPU VRAM is tight; 0 = auto.

**Native video model choice:** `realesr-animevideov3` is tuned for video and runs faster than the still-image models on frame sequences.

## Step 4 — Batch a folder

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py batch \
  --model realesr --scale 4 --in-dir photos/ --out-dir photos_4x/
```

Real-ESRGAN ncnn-vulkan natively accepts `-i <dir> -o <dir>` and processes every file in parallel. The wrapper adds logging, dry-run, and skips already-processed outputs.

## Gotchas

- **ffmpeg built-in SR is outdated.** `dnn_processing=model=espcn.pb` / EDSR / SRCNN are 2014–2017 research models. On real content they are not competitive with Real-ESRGAN (2021+). Recommend ffmpeg built-ins only as a tiny fallback.
- **`-n` model name, not path.** `realesrgan-ncnn-vulkan -n realesrgan-x4plus` expects the model file to live under the binary's `models/` directory (shipped in the release zip). If you get `failed to load model`, pass `-m <dir>` to point at your models.
- **Scale factor must match the chosen model.** `realesrgan-x4plus` is 4x-only. Don't pass `-s 2` to a 4x model and expect 2x output — you'll get a downsample of 4x output.
- **yuv420p even dimensions.** After a 3x upscale of an odd-width video, libx264 will complain. Add `-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"` on the remux.
- **VRAM.** Real-ESRGAN on a 4K frame wants ~6GB at 4x. Use `-t 256` (tile size) to process 256×256 tiles and stitch — slower but fits in 2GB.
- **Face restoration bakes in features** that weren't in the original. GFPGAN will hallucinate plausible detail; don't use it on ID photos you need legally faithful. For cinema/commercial work, only use it when the client has signed off on "AI reconstruction."
- **CodeFormer is NOT in this skill.** CodeFormer is S-Lab License research-only. Do not recommend it even though many tutorials online still do.
- **Topaz Video AI is NOT in this skill.** It is commercial paid software; outside the open-source + commercial-safe scope.
- **RMBG v1.4 is NOT in this skill.** Different project (background removal) — see `media-matte`. Also: v1.4 was NC; only v2.0 (Apache 2.0) is commercial-safe.
- **Upscayl is AGPL-3.0.** If you ship code derived from Upscayl's source in a commercial closed product you must release source. Running the bundled app to produce outputs is fine.
- **chaiNNer is GPL-3.0.** Same caveat as Upscayl: running it to produce outputs is fine, linking its code into a closed product is not.
- **Video frame remux needs the source FPS exactly.** Pull it from `ffprobe` first — don't assume 23.976 / 25 / 29.97.
- **8-bit → 10-bit matters.** Upscaling an 8-bit source doesn't add dynamic range. If the source is 10-bit HDR, keep the frame dumps in a 16-bit PNG pipeline or use EXR to preserve the bit depth.

## Examples

### Example 1: 4x an old family photo

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py image \
  --model realesr --scale 4 --in grandma_1970.jpg --out grandma_4x.png
```

### Example 2: Upscale a 480p anime clip to 1080p

```bash
# 480 * 2.25 ≈ 1080 → use Real-CUGAN 2x, then pad to 1080p if needed.
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py video \
  --model realcugan --scale 2 --in ep01_480p.mp4 --out ep01_960p.mp4
ffmpeg -i ep01_960p.mp4 -vf "scale=-2:1080:flags=lanczos" -c:v libx264 -crf 18 ep01_1080p.mp4
```

### Example 3: Restore a face in a scan, keep background

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py face-restore \
  --model gfpgan --in scan.jpg --out scan_restored.png --scale 2
```

### Example 4: Batch 4x a folder of 1000 thumbnails

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py batch \
  --model realesr --scale 4 --in-dir thumbs/ --out-dir thumbs_4x/
```

### Example 5: Check which upscale binaries are on PATH

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/upscale.py check
```

## Troubleshooting

### Error: `realesrgan-ncnn-vulkan: command not found`

Cause: binary not installed.
Solution: Download from https://github.com/xinntao/Real-ESRGAN/releases and unzip. Or `brew install realesrgan-ncnn-vulkan`. Or run `uv run .../upscale.py install realesr`.

### Error: `failed to load model: realesrgan-x4plus`

Cause: model `.param` / `.bin` files not next to the binary (expected at `<binary>/models/`).
Solution: The release zip bundles them — always use the full zip. Or pass `-m /path/to/models`.

### Output is blocky / has tile seams

Cause: `-t` tile size too small relative to content.
Solution: Increase tile (`-t 512` or `-t 0` for auto). Or run without tiling on a GPU with more VRAM.

### HAT / SwinIR inference: `CUDA out of memory`

Cause: tile size too large.
Solution: Reduce `--tile 400` → `--tile 200`. HAT's test.py reads `tile` from the YML.

### Upscaled video stutters / is desynced

Cause: reassembled at wrong FPS, or VFR source.
Solution: `ffprobe -select_streams v -show_entries stream=r_frame_rate,avg_frame_rate clip.mp4` — pass that exact rational to `-framerate`. For VFR sources, first normalize with `ffmpeg -vsync cfr`.

### GFPGAN "RuntimeError: CUDA error" on CPU machine

Cause: GFPGAN needs a GPU by default.
Solution: `python inference_gfpgan.py --device cpu ...` (slow but works).

## Reference docs

- Per-model URLs, input res ranges, GPU/CPU support, download commands → `references/models.md`.
- Full license table for every model bundled → `references/LICENSES.md`.
