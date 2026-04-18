---
name: media-sd
description: >
  Open-source AI image generation via ComfyUI (GPL-3.0, node-based runner) with
  STRICTLY permissive-license models: FLUX.1 [schnell] (Apache 2.0, Black Forest Labs
  fastest high-quality 4-step distilled model), Kolors (Apache 2.0, Kuaishou
  photorealistic diffusion), Sana (Apache 2.0, NVIDIA efficient DiT that runs on ~12GB
  VRAM), Lumina-Next (Apache 2.0, Shanghai AI Lab high-resolution), HunyuanDiT
  (Tencent License 2.0, commercial-permissive with a 100M-MAU cap), PixArt-Sigma.
  Text-to-image, image-to-image, ControlNet conditioning, LoRA adapters, ComfyUI
  node-graph workflows, HuggingFace diffusers pipeline. Use when the user asks to
  generate AI images, do text-to-image, create AI art, build or run a ComfyUI
  workflow, apply ControlNet, stack LoRAs, run a local diffusion server, use
  FLUX-schnell, use Kolors, use Sana, use Lumina, use HunyuanDiT, use PixArt, or
  specifically asks for OSI-open / Apache-licensed / commercial-safe image models.
argument-hint: "[prompt] [output]"
---

# Media SD (open-source image generation)

**Context:** $ARGUMENTS

## Quick start

- **Fast quality text-to-image:** `scripts/sd.py generate --model flux-schnell --prompt "..." --out out.png --steps 4` → Step 3.
- **Run a ComfyUI workflow JSON:** `scripts/sd.py comfy-workflow --workflow my.json --out out.png` → Step 4.
- **Install ComfyUI:** `scripts/sd.py comfy-install` prints the exact clone + pip steps → Step 2.
- **img2img edit from a seed image:** `scripts/sd.py img2img --model flux-schnell --init-image in.png --prompt "..." --strength 0.6 --out out.png` → Step 3.
- **Download weights (confirm required):** `scripts/sd.py download --model flux-schnell --yes` → Step 2.

## When to use

- Generate images from a text prompt using ONLY permissively licensed open-source weights (Apache 2.0 / MIT / BSD / OSI-open).
- Need a license that clears commercial product use without usage restrictions (no CreativeML OpenRAIL-M, no FLUX.1 [dev] NC, no SD3 research-only terms).
- Run a ComfyUI node-graph workflow exported from the ComfyUI web UI or Manager.
- Build img2img / inpaint pipelines on permissive backbones.
- Do NOT use for SDXL / SD 1.5 / SD 2.1 / SD3 base, FLUX.1 [dev], DALL-E, Midjourney. These are either commercial APIs or have license restrictions. See `references/LICENSES.md`.

## Step 1 — Pick a model

| Model | License | VRAM (FP16) | Strength | Use when |
|-------|---------|-------------|----------|----------|
| **FLUX.1 [schnell]** | Apache 2.0 | 24GB (or 12GB NF4) | Highest quality at 4 steps | Default for most users; fastest quality per second |
| **Kolors** | Apache 2.0 | 16GB | Photorealism, Chinese prompts strong | Photoreal faces/products; multilingual |
| **Sana** | Apache 2.0 | 12GB (runs on consumer cards) | Efficient DiT, up to 4096px | Tight VRAM budget, high resolution |
| **Lumina-Next** | Apache 2.0 | 24GB | Strong prompt adherence at high-res | Complex multi-subject prompts |
| **HunyuanDiT** | Tencent License 2.0 | 16GB | Bilingual EN/CN | Commercial use under >100M MAU cap (see Gotchas) |
| **PixArt-Sigma** | Per-checkpoint (check) | 12–20GB | Efficient transformer | Research / specific checkpoints — verify license per variant |

Read `references/models.md` for resolution ranges, speed benchmarks, recommended samplers, and per-model prompt quirks.

Check what's installed locally:

```bash
uv run .claude/skills/media-sd/scripts/sd.py check
```

## Step 2 — Install ComfyUI and pull weights

ComfyUI is the canonical runtime for these models. It's GPL-3.0 and self-hosted.

```bash
uv run .claude/skills/media-sd/scripts/sd.py comfy-install
# prints: git clone https://github.com/comfyanonymous/ComfyUI
#         cd ComfyUI && python -m venv .venv && source .venv/bin/activate
#         pip install -r requirements.txt
#         python main.py --listen 127.0.0.1 --port 8188
```

Pull weights (downloads are big — 5–24 GB — so the script requires `--yes` to confirm):

```bash
uv run .../sd.py download --model flux-schnell --yes
# → downloads into ./ComfyUI/models/unet|vae|clip by default
# override with --comfy-root /path/to/ComfyUI
```

Or use HuggingFace diffusers directly (pure Python, no ComfyUI needed):

```bash
uv run .../sd.py install flux-schnell
# pip install diffusers transformers accelerate torch
```

Read `references/comfyui.md` for node-graph basics, the standard FLUX-schnell workflow JSON, ControlNet + LoRA wiring, and common node names.

## Step 3 — Generate

### Option A: Diffusers pipeline (recommended for one-shot)

```bash
uv run .../sd.py generate \
    --model flux-schnell \
    --prompt "a photo of a capybara wearing a tiny wizard hat, studio lighting" \
    --out out.png \
    --width 1024 --height 1024 \
    --steps 4 --guidance 0.0 --seed 42
```

FLUX-schnell is distilled — `--steps 4` + `--guidance 0.0` is the correct setting; more steps or guidance >1 will DEGRADE output. Kolors / Sana / Lumina want 20–30 steps and `--guidance 4–7`.

### Option B: img2img (seed from an existing image)

```bash
uv run .../sd.py img2img \
    --model flux-schnell \
    --init-image input.png \
    --prompt "convert to oil painting" \
    --strength 0.6 \
    --out out.png
```

`--strength 0.0` keeps the input unchanged; `1.0` ignores it. Useful range: 0.3–0.75.

### Option C: ComfyUI workflow JSON

```bash
# Start ComfyUI in the background (one-time)
cd ~/ComfyUI && python main.py --listen 127.0.0.1 --port 8188 &

# Run a saved workflow (exported from ComfyUI UI via "Save (API Format)")
uv run .../sd.py comfy-workflow \
    --workflow flux_schnell_default.json \
    --out out.png \
    --server http://127.0.0.1:8188
```

The script POSTs to `/prompt`, polls `/history/<prompt_id>`, then pulls the resulting PNG from `/view`.

## Step 4 — Integrate with ffmpeg

After generating stills, typical hand-offs:

- Build an image sequence into a video: pass to `ffmpeg-frames-images` skill (`ffmpeg -framerate 24 -i "frame_%04d.png" -c:v libx264 ...`).
- Upscale an output: pass to `media-upscale` (Real-ESRGAN / SwinIR).
- Animate a still with AI motion: pass to `media-svd` for i2v.
- Drive a face photo: pass to `media-lipsync`.

## Gotchas

- **FLUX.1 [schnell] is Apache 2.0 and commercially safe. FLUX.1 [dev] is NON-COMMERCIAL.** Never default to `flux-dev` — this skill intentionally does not list it. See `references/LICENSES.md`.
- **Never use SDXL / SD 1.5 / SD 2.1 / SD3 base from this skill.** Their CreativeML OpenRAIL-M license contains use-case restrictions and is not OSI-open. Call `media-upscale` or other non-generative skills if the user wants SD-era tooling.
- **HunyuanDiT has a company-size cap**: Tencent License 2.0 permits commercial use unless the licensee's products exceed ~100M monthly active users — flag this before recommending it for a large-scale product.
- **Stable Video Diffusion (SVD) is NOT included** despite the skill's legacy name `media-svd` in the sibling skill. SVD's OpenRAIL-M NC terms forbid commercial use. That sibling skill uses LTX-Video / CogVideoX / Mochi instead.
- **FLUX-schnell hates high guidance.** It was distilled to run guidance-free (`guidance_scale=0.0`). Setting `--guidance 7` will produce blurry/saturated garbage.
- **FLUX-schnell needs exactly 4 steps.** More steps do not help and can degrade. Other models (Kolors, Sana) do want 20–30 steps at guidance 4–7.
- **VRAM vs. quantization.** FLUX FP16 needs 24 GB; NF4 / GGUF quantized forks run on 12 GB but may slightly reduce quality. `scripts/sd.py` picks quantization based on `--dtype` (default `bfloat16` → auto-fallback to `float16` → `nf4`).
- **ComfyUI workflow JSON comes in two flavors.** The "Save" button saves a UI-format JSON (with positions, colors, etc.) that the API will NOT accept. Use "Save (API Format)" in the UI, or the script autodetects and converts via the `/object_info` endpoint.
- **CUDA is the fast path.** Apple Silicon runs on MPS via PyTorch but FLUX is notably slow (~2 minutes / image on M3 Max). Sana is the best Apple-Silicon pick (~25 s).
- **`diffusers` tracks model-specific pipelines.** `FluxPipeline`, `KolorsPipeline`, `SanaPipeline`, `Lumina2Text2ImgPipeline`, `HunyuanDiTPipeline`. Using `AutoPipelineForText2Image` usually works but sometimes falls back to the wrong class — the script dispatches explicitly.
- **Never auto-download weights without `--yes`.** Weights are 5–24 GB per model and come from HuggingFace which may require a token (`HF_TOKEN` env var) for gated models. The helper always confirms first.
- **Gated HF repos**: even permissive models sometimes sit behind a click-through at HuggingFace (required acceptance ≠ restrictive license). Set `HF_TOKEN` in the environment before `download`.

## Examples

### Example 1: 4-step FLUX-schnell portrait

```bash
uv run .../sd.py generate \
    --model flux-schnell \
    --prompt "cinematic portrait of an astronaut, 35mm film, shallow DOF" \
    --out astronaut.png --width 1024 --height 1024 --steps 4 --seed 7
```

### Example 2: Photoreal product shot with Kolors

```bash
uv run .../sd.py generate \
    --model kolors \
    --prompt "a red leather messenger bag on a marble table, softbox lighting" \
    --out bag.png --steps 25 --guidance 5.0
```

### Example 3: High-res landscape on a 12GB card (Sana)

```bash
uv run .../sd.py generate \
    --model sana --prompt "snow-capped mountain valley at sunrise" \
    --out valley.png --width 2048 --height 2048 --steps 20 --dtype float16
```

### Example 4: Run an exported ComfyUI FLUX workflow

```bash
# ComfyUI running on 8188
uv run .../sd.py comfy-workflow \
    --workflow flux_schnell_api.json \
    --out render.png \
    --timeout 300
```

### Example 5: img2img style transfer

```bash
uv run .../sd.py img2img \
    --model flux-schnell --init-image photo.jpg \
    --prompt "anime illustration, pastel palette" \
    --strength 0.55 --steps 4 --out stylized.png
```

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'diffusers'`

Cause: the diffusers stack isn't installed in the active Python.
Solution: `pip install diffusers transformers accelerate torch` or run `uv run .../sd.py install flux-schnell` which pins the right versions.

### Error: `CUDA out of memory`

Cause: model + latent doesn't fit in VRAM.
Solution: add `--dtype float16`, lower `--width`/`--height` to 768, enable `--cpu-offload`, or switch to Sana which is designed for 12 GB cards.

### Error: `ConnectionRefusedError: 127.0.0.1:8188`

Cause: ComfyUI server isn't running.
Solution: `cd ~/ComfyUI && python main.py --listen 127.0.0.1 --port 8188`. Or run `scripts/sd.py comfy-install` for the exact setup commands.

### Error: `Repository not found` / `401 Unauthorized` from HuggingFace

Cause: the model's HF repo is gated and requires authentication.
Solution: accept the terms on the HF page, then `export HF_TOKEN=<your_hf_token>` before re-running `download`. Even Apache-licensed weights sometimes require click-through acceptance.

### FLUX output is blurry / over-saturated

Cause: used `--guidance > 0` or `--steps != 4` with flux-schnell.
Solution: FLUX-schnell is a distilled model. Use exactly `--steps 4 --guidance 0.0`. For CFG-style guidance, switch to `flux-dev` (but that is NON-COMMERCIAL — we don't ship a preset for it).

### ComfyUI workflow import fails: "cannot execute node KSampler"

Cause: the JSON is the UI-format export, not API-format.
Solution: in ComfyUI UI, Settings → "Enable Dev mode Options", then "Save (API Format)". Or load the UI JSON into ComfyUI then re-export via the API button.
