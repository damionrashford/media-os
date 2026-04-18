# media-sd model catalog

Only OSI-open / commercial-safe weights. See `LICENSES.md` for the formal status.

## FLUX.1 [schnell] — Black Forest Labs

- License: **Apache 2.0** (the schnell variant only; `flux-dev` is NON-COMMERCIAL and is NOT listed here).
- HF repo: `black-forest-labs/FLUX.1-schnell`
- Parameters: 12B MMDiT rectified flow.
- VRAM: ~24 GB FP16, ~12 GB NF4 quantized, ~8 GB with cpu-offload.
- Resolution: native 1024; works 512–2048 with quality falloff past 1536.
- Distilled — use **exactly 4 steps, guidance 0.0**. Do not raise either.
- Sampler: `FlowMatchEulerDiscreteScheduler` (default in FluxPipeline).
- Speed (A100 FP16): ~0.8 s/image at 1024. M3 Max MPS: ~120 s/image.

## Kolors — Kuaishou

- License: **Apache 2.0**.
- HF repo: `Kwai-Kolors/Kolors-diffusers`.
- SDXL-style UNet + ChatGLM-6B text encoder.
- VRAM: ~16 GB FP16.
- Resolution: 1024 native, up to 2048.
- Steps/guidance: 25 steps, CFG 5.0 typical.
- Strength: photorealism, product/retail imagery, strong Chinese + English prompts.
- Sampler: DPM++ 2M Karras recommended.

## Sana 1.6B — NVIDIA

- License: **Apache 2.0**.
- HF repo: `Efficient-Large-Model/Sana_1600M_1024px_diffusers` (and `_4096px_diffusers` for ultra-HD).
- Linear-attention DiT — 20x faster than same-parameter comparison.
- VRAM: ~12 GB — runs on RTX 3060 / M2 Max.
- Resolution: 1024 base, up to 4096 with the 4K checkpoint.
- Steps: 20, CFG 4.5.
- Speed (M3 Max): ~25 s/image @ 1024. Best Apple Silicon pick.
- Uses Gemma-2 text encoder (weights Apache 2.0).

## Lumina-Next — Shanghai AI Lab

- License: **Apache 2.0**.
- HF repo: `Alpha-VLLM/Lumina-Next-SFT-diffusers`.
- NextDiT-2B with Gemma-2B text encoder.
- VRAM: ~24 GB FP16.
- Resolution: 1024, 1536, 2048 (any aspect, trained on 5M multi-aspect pairs).
- Steps 30, CFG 4.
- Strength: complex multi-subject prompts, typography tolerance.

## HunyuanDiT v1.2 — Tencent

- License: **Tencent License 2.0** — commercial use allowed BUT if your product has
  >=100M MAU (monthly active users) you need a separate commercial license from Tencent.
  Not OSI-open because of the MAU cap. Usable for most commercial products; flag at large scale.
- HF repo: `Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers`.
- 1.5B DiT.
- VRAM: ~16 GB FP16.
- Resolution: 1024 native.
- Bilingual EN/CN prompts.

## PixArt-Sigma — PixArt-alpha

- License: per-checkpoint — the "Sigma" 1024-MS repo is Apache 2.0; older PixArt-alpha checkpoints have research-only terms. Always check `LICENSE` in the specific HF repo.
- HF repo: `PixArt-alpha/PixArt-Sigma-XL-2-1024-MS`.
- 0.6B DiT + T5-XXL text encoder.
- VRAM: ~12 GB FP16.
- Resolution: 256 / 512 / 1024 / 2K variants.

## Comparison table

| Model         | License        | Min VRAM | Native res | Best step/CFG | Speed (A100, 1024) |
|---------------|----------------|----------|------------|---------------|--------------------|
| flux-schnell  | Apache 2.0     | 12 GB NF4| 1024       | 4 / 0.0       | ~0.8 s            |
| kolors        | Apache 2.0     | 16 GB    | 1024       | 25 / 5.0      | ~4 s              |
| sana          | Apache 2.0     | 12 GB    | 1024–4096  | 20 / 4.5      | ~1.5 s            |
| lumina        | Apache 2.0     | 24 GB    | 1024–2048  | 30 / 4.0      | ~3 s              |
| hunyuan-dit   | Tencent 2.0    | 16 GB    | 1024       | 25 / 5.0      | ~4 s              |
| pixart-sigma  | per-checkpoint | 12 GB    | 1024 / 2K  | 20 / 4.5      | ~2 s              |

## Prompt style quirks

- **FLUX-schnell**: natural-language prompts; does not need danbooru-style tags.
- **Kolors**: responds well to Chinese prompts with product descriptors.
- **Sana**: concise prompts work best; verbose ones dilute.
- **Lumina**: enjoys structured prompts with explicit subject/style/lighting segments.
- **HunyuanDiT**: bilingual — mixing EN + CN works ("一只猫 sitting on a chair").
- **PixArt-Sigma**: T5-XXL is long-context; prompts up to 300 tokens work.
