---
name: media-svd
description: >
  Open-source AI video generation with STRICTLY permissive-license models: LTX-Video
  (Apache 2.0, Lightricks realtime-ish text-to-video), CogVideoX-2B / -5B (Apache 2.0,
  Tsinghua + Zhipu, 2024), Mochi-1 (Apache 2.0, Genmo), AnimateDiff (Apache 2.0, motion
  module that animates any diffusion image model), Wan-Video (Apache 2.0, Alibaba 2025
  high quality). Text-to-video (t2v), image-to-video (i2v), motion-controlled animation
  via AnimateDiff, ComfyUI workflow integration. Use when the user asks to generate a
  video from a text prompt, animate a still image, make a short AI clip, run CogVideoX,
  use LTX-Video, use Mochi, use Wan-Video, use AnimateDiff, or specifically asks for
  Apache-licensed / OSI-open / commercial-safe video generation models. Does NOT include
  Stable Video Diffusion (SVD OpenRAIL-M NC), Sora, Runway, Kling — all proprietary or
  non-commercial. HunyuanVideo is mentioned but flagged for its commercial cap.
argument-hint: "[prompt] [output]"
---

# Media SVD (open-source video generation)

**Context:** $ARGUMENTS

## Quick start

- **Text-to-video:** `scripts/svd.py t2v --model ltx --prompt "..." --duration 5 --fps 24 --out out.mp4` → Step 3.
- **Image-to-video:** `scripts/svd.py i2v --model cogvideox --init-image in.png --prompt "..." --duration 5 --out out.mp4` → Step 3.
- **AnimateDiff image-model motion:** `scripts/svd.py animate --workflow animatediff.json --out out.mp4` → Step 4.
- **Install a model's pip deps:** `scripts/svd.py install ltx` → Step 2.
- **Fetch weights (confirm required):** `scripts/svd.py download --model ltx --yes` → Step 2.

## When to use

- Generate a short video clip from a text prompt using permissively licensed open-source models only.
- Animate an existing still image into motion via image-to-video (i2v).
- Use AnimateDiff to add motion to any `media-sd` image model workflow.
- Need commercial clearance: all default models are Apache 2.0.
- Do NOT use for Stable Video Diffusion (SVD), Sora, Runway Gen-3, Kling — they are either non-commercial or proprietary APIs. HunyuanVideo has a commercial user-size cap (Tencent License) — mention but do not default to.

## Step 1 — Pick a model

| Model              | License    | Type         | Typical duration | VRAM (FP16)      | Notes |
|--------------------|------------|--------------|------------------|------------------|-------|
| **LTX-Video**      | Apache 2.0 | t2v + i2v    | 5 s (up to ~17 s)| 24 GB (12 GB nf4)| Near-realtime on H100; fastest Apache model |
| **CogVideoX-5B**   | Apache 2.0 | t2v + i2v    | 6 s @ 8 fps     | 24 GB            | Best quality in the 5B class; 2B variant fits 12 GB |
| **CogVideoX-2B**   | Apache 2.0 | t2v          | 6 s              | 12 GB            | Smaller; good for consumer cards |
| **Mochi-1**        | Apache 2.0 | t2v          | 5.4 s @ 30 fps   | 60 GB+ (multi-GPU)| SOTA quality, heavy. Use 8-bit / tensor parallel |
| **AnimateDiff**    | Apache 2.0 | motion module| 2–4 s            | same as image model | Plugs into a `media-sd` image pipeline |
| **Wan-Video 2.1**  | Apache 2.0 | t2v + i2v    | 5 s              | 24 GB            | Alibaba 2025; strong prompt adherence |
| HunyuanVideo       | Tencent L. | t2v          | 5 s              | 60 GB+           | Commercial cap — flag before use; NOT default |

Read `references/models.md` for per-model prompt style, sampler/scheduler pairs, and published VBench / human-eval scores.

Check environment:

```bash
uv run .claude/skills/media-svd/scripts/svd.py check
```

## Step 2 — Install and download

### Diffusers pipeline (pure Python, no ComfyUI)

```bash
uv run .../svd.py install ltx
# → pip install diffusers transformers accelerate torch imageio imageio-ffmpeg

uv run .../svd.py download --model ltx --yes
# → huggingface_hub snapshot_download into HF cache
```

### ComfyUI (for workflows with AnimateDiff / LoRAs)

See the `media-sd` skill for ComfyUI install. Then download video-model nodes via ComfyUI-Manager:

- `ComfyUI-LTXVideo`
- `ComfyUI-CogVideoXWrapper`
- `ComfyUI-MochiWrapper`
- `ComfyUI-AnimateDiff-Evolved`
- `ComfyUI-WanVideoWrapper`

## Step 3 — Generate

### Text-to-video (t2v)

```bash
uv run .../svd.py t2v \
    --model ltx \
    --prompt "a cat jumping off a sofa, cinematic, 35mm film grain" \
    --duration 5 --fps 24 \
    --width 768 --height 512 \
    --out cat.mp4 --seed 42
```

LTX-Video wants resolution as a multiple of 32. CogVideoX is fixed to 720x480. The
script rounds/validates per-model.

### Image-to-video (i2v)

```bash
uv run .../svd.py i2v \
    --model cogvideox \
    --init-image first_frame.png \
    --prompt "the wind blows and the flag starts waving" \
    --duration 6 --fps 8 \
    --out waving.mp4
```

The init-image becomes the first frame. Keep the prompt consistent with the image —
conflicting prompts ("dog" when the image is a cat) produce artifacted morphs.

### AnimateDiff via ComfyUI

```bash
# ComfyUI running on 8188, workflow loaded with AnimateDiff nodes
uv run .../svd.py animate \
    --workflow animatediff_sana.json \
    --out anim.mp4 --server http://127.0.0.1:8188
```

AnimateDiff adds temporal attention to a frozen image UNet. Inside the ComfyUI
workflow, wire `AnimateDiffLoaderGen1` between `ModelLoader` and `KSampler`. Use
Apache 2.0 image backbones only (Sana, PixArt-Sigma — see `media-sd`).

## Step 4 — Post-process and mux

Typical follow-ups:

- Upscale 512p → 1080p: pass to `media-upscale` (Real-ESRGAN).
- Interpolate 8 fps → 24/60 fps: pass to `media-interpolate` (RIFE / FILM).
- Add audio: `ffmpeg -i video.mp4 -i music.mp3 -c:v copy -c:a aac -shortest final.mp4` (or use `ffmpeg-transcode`).
- Concat multiple clips: `ffmpeg-cut-concat`.

## Gotchas

- **Stable Video Diffusion (SVD) is NOT in this skill.** Its OpenRAIL-M license is non-commercial for most tiers. If a user says "SVD" they probably mean that model — tell them to use LTX-Video or CogVideoX instead.
- **Apache 2.0 is not a free pass on content.** Most Apache models still include an acceptable-use / ethics statement in the model card. These are not license terms (because Apache 2.0 doesn't allow them) but are practical guidelines. Read the HF model card.
- **HunyuanVideo has a commercial cap** (same Tencent License 2.0 as HunyuanDiT). Not our default; mention only when the user explicitly asks.
- **CogVideoX resolution is fixed**: 720x480 for 2B/5B t2v, 480x720 for 5B i2v. Passing other sizes errors or silently resizes.
- **LTX-Video resolution must be a multiple of 32**, duration rounded to multiples of 1/24 s.
- **Mochi-1 is 60+ GB VRAM** — effectively multi-GPU only. There's an 8-bit community quant (`genmoai/mochi-1-preview` with `bitsandbytes`) that fits in 40 GB.
- **fps control is trickier than it looks.** CogVideoX outputs 8 fps native; upsample later with `media-interpolate`. LTX-Video does 24 fps native. AnimateDiff defaults to 8 fps.
- **Diffusers video pipelines return lists of PIL frames**, not an ffmpeg-friendly file. The script writes frames → ffmpeg -i "frame_%04d.png" internally using `imageio_ffmpeg`.
- **Prompt length**: CogVideoX uses T5 (up to 226 tokens), LTX uses T5 (120 tokens), Mochi uses T5 (256 tokens). Longer prompts get truncated silently.
- **Negative prompts** are not always supported (LTX-Video ignores them). For Mochi and CogVideoX, negative prompts HELP avoid blur/chroma-smearing.
- **VRAM paging via `enable_sequential_cpu_offload()`** halves speed but halves VRAM. Use when OOM.
- **Seeds drift across diffusers versions** — pin `diffusers>=0.32` for reproducibility.
- **AnimateDiff 1.5 vs SDXL** — AnimateDiff-SDXL weights exist but are experimental; the original is trained on SD 1.5 frames and needs an SD-1.5-compatible backbone. We don't expose SD 1.5 in media-sd (CreativeML OpenRAIL-M excluded). Use AnimateDiff-Lightning on a Sana or PixArt backbone, or skip AnimateDiff entirely.

## Examples

### Example 1: LTX-Video cat clip, 5 s @ 24 fps

```bash
uv run .../svd.py t2v --model ltx \
    --prompt "a ginger cat leaps from a sofa to a bookshelf, slow motion" \
    --duration 5 --fps 24 --width 768 --height 512 \
    --out cat.mp4 --seed 7
```

### Example 2: CogVideoX-5B i2v from a still

```bash
uv run .../svd.py i2v --model cogvideox-5b \
    --init-image portrait.png \
    --prompt "she smiles and turns her head slightly" \
    --duration 6 --fps 8 --out smile.mp4
```

### Example 3: Low-VRAM CogVideoX-2B on a 12 GB card

```bash
uv run .../svd.py t2v --model cogvideox-2b \
    --prompt "neon Tokyo street at night, rain, reflections" \
    --duration 6 --fps 8 --cpu-offload \
    --out tokyo.mp4
```

### Example 4: AnimateDiff on a Sana image backbone

```bash
# 1. Pre-author the ComfyUI workflow with AnimateDiffLoaderGen1 + Sana backbone
# 2. Run it:
uv run .../svd.py animate \
    --workflow sana_animatediff.json --out anim.mp4 \
    --server http://127.0.0.1:8188
```

### Example 5: Wan-Video high quality

```bash
uv run .../svd.py t2v --model wan \
    --prompt "a hot-air balloon drifts over snow-capped mountains at sunrise" \
    --duration 5 --fps 24 --width 832 --height 480 \
    --out balloon.mp4
```

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'diffusers'`

Cause: diffusers stack not installed.
Solution: `uv run .../svd.py install <model>` or `pip install diffusers transformers accelerate torch imageio imageio-ffmpeg`.

### Error: `CUDA out of memory` on Mochi-1

Cause: 60+ GB model doesn't fit.
Solution: switch to LTX-Video or CogVideoX-2B, or run Mochi under `bitsandbytes` 8-bit quant with `--cpu-offload` (~40 GB). True FP16 Mochi needs multi-GPU tensor parallel.

### Output is a static image / no motion

Cause: i2v with `--strength 0.0` or mismatched prompt, or forgot `--duration`.
Solution: set `--duration >= 2`, ensure prompt describes motion ("she walks", "camera pans"), raise strength if using i2v.

### CogVideoX output is blurry

Cause: T5 prompt too short, or negative prompt missing.
Solution: write a 30–60 word prompt describing subject + motion + camera + style. Add `--negative-prompt "blurry, low quality, distorted"`.

### Frames appear doubled / juddery at 24 fps

Cause: native model fps is 8; `--fps 24` upsampled by frame repeat.
Solution: do not oversell native fps. Render at native, then pass to `media-interpolate` (RIFE / FILM) for smooth 24/60 fps.

### ComfyUI workflow fails: "AnimateDiffLoaderGen1 missing"

Cause: ComfyUI-AnimateDiff-Evolved custom node not installed.
Solution: in ComfyUI-Manager, install "AnimateDiff Evolved" by Kosinkadink. Or `git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved custom_nodes/ComfyUI-AnimateDiff-Evolved`.
