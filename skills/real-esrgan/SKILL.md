---
name: real-esrgan
description: >
  Use when the user asks to upscale or super-resolve an image or video with Real-ESRGAN — AI upscale, 4K-ify, super-resolution, enhance a low-res or blurry photo, sharpen, 2x/3x/4x upscale, restore an old photo, upscale anime or illustration, rescale game textures, or upscale video frames beyond a plain lanczos scale. Covers the realesrgan-ncnn-vulkan portable binary (no Python/CUDA) and the Python realesrgan package (inference_realesrgan.py, inference_realesrgan_video.py, RealESRGANer); models realesrgan-x4plus, realesr-animevideov3, realesrgan-x4plus-anime, realesrnet-x4plus; optional GFPGAN --face_enhance; and the extract → upscale → remux video pipeline. BSD-3-Clause, commercial-safe. Do NOT use for plain resizing (ffmpeg-filter), frame-rate interpolation, or audio denoise.
argument-hint: "[image|video|batch] [input] [output]"
---

# Real-ESRGAN

**Context:** $ARGUMENTS

Real-ESRGAN ([xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN), BSD-3-Clause) is a practical super-resolution model trained on pure synthetic degradations. It beats ffmpeg's built-in `dnn_processing` SRCNN/ESPCN/EDSR (2014–2017) and a plain `scale=...:flags=lanczos` on real-world photos, video frames, and anime. Two ways to run it: the **ncnn-vulkan portable binary** (zero Python, any GPU via Vulkan, the default) and the **Python `realesrgan` package** (CUDA, scriptable, `--face_enhance`).

## When to use

- Upscale / super-resolve a photo, video, anime, or game texture by 2x / 3x / 4x.
- A `scale` resize or ffmpeg's `dnn_processing` looks soft or blurry on real content.
- Restore a low-res or blurry portrait (add `--face_enhance` → GFPGAN on faces).
- Do NOT use for: plain resizing without quality gain (`ffmpeg-filter` `scale`), frame-rate interpolation / slow-motion, audio denoise, or background removal (`ai-understand` matte).

## Models

Pick with `-n` (ncnn) or `--model_name` (Python):

| Model | Scale | Best for |
|---|---|---|
| `realesrgan-x4plus` | 4x | General real-world photos (default for stills) |
| `realesr-animevideov3` | 2/3/4x | Video frames + cartoons; fastest, tuned for motion (ncnn default) |
| `realesrgan-x4plus-anime` | 4x | Anime / illustration stills (smaller, sharper cel edges) |
| `realesrnet-x4plus` | 4x | Less aggressive denoise, more faithful to source |

Read `references/models.md` for weights URLs, the Python `RealESRGANer` API, VRAM/tile guidance, and the full ncnn-vs-Python comparison. Read `references/licenses.md` before shipping outputs in a product.

## Install (the script prints the command; it does NOT auto-install)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py install      # prints platform install command
uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py check        # what's on PATH
```

- **ncnn-vulkan (recommended):** download the release zip (binary + bundled `models/`) from <https://github.com/xinntao/Real-ESRGAN/releases>, or `brew install realesrgan-ncnn-vulkan` where the tap exists.
- **Python:** `uv pip install realesrgan basicsr` (CUDA for speed; `--fp32` on CPU/old GPUs).

## Recipe — image (ncnn-vulkan)

```bash
realesrgan-ncnn-vulkan -i photo.jpg -o photo_4x.png -n realesrgan-x4plus -s 4 -f png
```

Flags: `-s` 2/3/4 · `-t` tile (0=auto, `256` to cap VRAM) · `-m` models dir · `-g` gpu-id · `-x` TTA (slower, higher quality) · `-f` jpg/png/webp. Driver:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py image --in photo.jpg --out photo_4x.png --model realesrgan-x4plus --scale 4
```

## Recipe — video (frame pipeline)

Real-ESRGAN is frame-based: extract lossless PNGs → upscale each → remux with original audio at the **exact source FPS**.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py video --in clip.mp4 --out clip_4x.mp4 --model realesr-animevideov3 --scale 4
```

What it runs:

```bash
ffmpeg -i clip.mp4 -qscale:v 1 -qmin 1 -qmax 1 -vsync 0 frames/%08d.png
realesrgan-ncnn-vulkan -i frames -o frames_4x -n realesr-animevideov3 -s 4 -f png
ffmpeg -framerate <src_fps> -i frames_4x/%08d.png -i clip.mp4 \
       -map 0:v -map 1:a? -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
       -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:a copy -movflags +faststart clip_4x.mp4
```

Python alternative (CUDA, single pass): `inference_realesrgan_video.py -i clip.mp4 -n realesr-animevideov3 -s 2 --num_process_per_gpu 2` — see `references/models.md`.

## Recipe — batch a folder

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py batch --in-dir photos/ --out-dir photos_4x/ --model realesrgan-x4plus --scale 4
```

ncnn-vulkan natively accepts `-i <dir> -o <dir>`; the wrapper adds logging, `--dry-run`, and skips already-done outputs.

## Gotchas

- **`-n` is a model NAME, not a path.** The `.param`/`.bin` files must sit under the binary's `models/` dir (shipped in the release zip). On `failed to load model`, pass `-m /path/to/models`.
- **Scale must match the model.** `realesrgan-x4plus` is 4x-only — passing `-s 2` downsamples a 4x result. Use `realesr-animevideov3` for true 2x/3x.
- **`realesr-animevideov3` is the ncnn default `-n`** and is the right pick for video frames — faster than the still models on sequences.
- **Even dimensions for yuv420p.** After an odd-dimension upscale, `libx264` rejects the frames; keep `scale=trunc(iw/2)*2:trunc(ih/2)*2` on the remux.
- **VRAM.** A 4K frame at 4x wants ~6 GB. Use `-t 256` to tile (slower, fits ~2 GB). Tile seams → raise `-t 512` or `-t 0`.
- **Pull source FPS from `ffprobe`** before remux — never assume 23.976/25/29.97. Normalize VFR first: `ffmpeg -i in.mp4 -vsync cfr -r <fps> cfr.mp4`.
- **`--face_enhance` hallucinates.** It routes faces through GFPGAN, which invents plausible detail — never on ID photos, evidence, or fidelity-critical work without sign-off.
- **Upscaling doesn't add dynamic range.** An 8-bit source stays 8-bit-worth of information; for 10-bit HDR keep a 16-bit PNG (or EXR) frame pipeline to avoid banding.
- **ffmpeg built-in SR is a fallback only.** `dnn_processing=model=espcn.pb`/EDSR/SRCNN lose to Real-ESRGAN on real content; recommend them only when no GPU/Vulkan is available.

## Scripts

- `scripts/realesrgan.py` — subcommands `image | video | batch | install | check`. ncnn-vulkan primary, Python `realesrgan` fallback. All support `--dry-run` and `--verbose`; the exact shell command prints to stderr before running. Run via `uv run ${CLAUDE_SKILL_DIR}/scripts/realesrgan.py <subcommand>`.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `realesrgan-ncnn-vulkan: command not found` | binary not installed | unzip the release; or `realesrgan.py install` |
| `failed to load model: realesrgan-x4plus` | model files not next to binary | use the full release zip, or `-m <models-dir>` |
| blocky / tile seams | tile too small | raise `-t 512` or `-t 0` |
| `CUDA out of memory` (Python) | tile too large | `--tile 200`; or `--fp32` on small GPUs |
| upscaled video stutters / desyncs | wrong remux FPS or VFR source | pass exact `ffprobe` `r_frame_rate` to `-framerate`; normalize VFR with `-vsync cfr` |
