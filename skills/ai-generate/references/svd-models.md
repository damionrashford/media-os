# media-svd model catalog

Only OSI-open / commercial-safe weights.

## LTX-Video — Lightricks

- License: Apache 2.0.
- HF repo: `Lightricks/LTX-Video` (and `Lightricks/LTX-Video-0.9.5` etc.).
- Architecture: DiT on top of a custom 32x spatial-temporal VAE.
- VRAM: ~24 GB FP16; 12 GB with NF4 / GGUF.
- Resolution: width x height each must be a multiple of 32. Common: 768x512, 1216x704.
- Native fps: 24. Supports up to ~17 s.
- Near-realtime on H100. Minutes on a 4090. 2-3x a clip's duration on M-series Macs.
- Diffusers pipelines: `LTXPipeline` (t2v), `LTXImageToVideoPipeline` (i2v).
- No negative prompt support in LTXPipeline (ignored).

## CogVideoX — Tsinghua + Zhipu

- License: Apache 2.0.
- Variants:
  - `THUDM/CogVideoX-2b`  (t2v, 12 GB).
  - `THUDM/CogVideoX-5b`  (t2v, 24 GB).
  - `THUDM/CogVideoX-5b-I2V` (i2v, 24 GB).
- Resolution: fixed 720x480 (t2v) / 480x720 (i2v 5B). Do not override.
- Native fps: 8. Use `media-interpolate` to reach 24/60.
- Duration: 6 seconds (49 frames at 8 fps).
- Prompt encoder: T5-XXL, 226 tokens.
- Strong negative prompt support.
- `diffusers.CogVideoXPipeline` / `diffusers.CogVideoXImageToVideoPipeline`.

## Mochi-1 — Genmo

- License: Apache 2.0.
- HF repo: `genmo/mochi-1-preview` (and `genmoai/mochi-1-preview` 8-bit community quant).
- 10B DiT + VAE.
- VRAM: 60+ GB FP16 (multi-GPU tensor parallel). `bitsandbytes` 8-bit fits in ~40 GB.
- Resolution: 848x480 native.
- Native fps: 30.
- Duration: 5.4 s (163 frames).
- SOTA quality among open models; heavy. Not default.

## Wan-Video 2.1 — Alibaba

- License: Apache 2.0.
- HF repo: `Wan-AI/Wan2.1-T2V-1.3B-Diffusers`, `Wan-AI/Wan2.1-T2V-14B-Diffusers`, `Wan-AI/Wan2.1-I2V-14B-Diffusers`.
- DiT with VAE. 1.3B runs on 24 GB; 14B needs multi-GPU.
- Resolution: multiple of 16; default 832x480.
- Native fps: 16.
- `diffusers.WanPipeline` / `diffusers.WanImageToVideoPipeline` (diffusers >= 0.32).

## AnimateDiff

- License: Apache 2.0 (code + motion module weights).
- Works ONLY via ComfyUI (no stable diffusers API for animate-through-a-sampler).
- Repo: Kosinkadink/ComfyUI-AnimateDiff-Evolved custom node.
- Attaches to an image-model UNet (SD 1.5 historically; SDXL and SD3 variants exist but less mature).
- In this skill we wire AnimateDiff onto permissive image backbones from `media-sd`:
  Sana, PixArt-Sigma, HunyuanDiT. SD 1.5 is NOT exposed because its license is OpenRAIL-M.

## Excluded (for reference — do NOT default to)

- **Stable Video Diffusion (SVD)** — OpenRAIL-M NC for most tiers. Not commercial-safe.
- **HunyuanVideo** — Tencent License with MAU cap, same caveats as HunyuanDiT.
- **Sora (OpenAI), Runway Gen-3, Kling, Luma Dream Machine** — proprietary APIs.
- **ModelScope t2v, Zeroscope** — OpenRAIL-M.

## Speed reference (H100, 24 steps, 5 s clip)

| Model          | Time to clip |
|----------------|--------------|
| LTX-Video      | ~4 s         |
| CogVideoX-2B   | ~25 s        |
| CogVideoX-5B   | ~60 s        |
| Wan 2.1 1.3B   | ~15 s        |
| Mochi (multi)  | ~90 s        |

Apple Silicon M3 Max (MPS): expect 5-10x the above. Sana-powered AnimateDiff is the
practical pick for MPS.
