# Matting Model Reference

All models here are open-source. Three are fully commercial-safe; RVM is
GPL-3.0 and MUST be used behind a subprocess boundary in closed-source
products (see LICENSES.md).

## rembg — the default for stills

- **Repo:** https://github.com/danielgatis/rembg
- **License (code):** MIT
- **License (bundled weights):**
  - `u2net` — Apache-2.0 (U-2-Net paper weights, distributed in Apache form by rembg)
  - `u2netp` — licensed per u2netp release; re-check if you depend on it
  - `isnet-general-use` — Apache-2.0
  - `isnet-anime` — Apache-2.0
  - `silueta` — MIT
  - `sam` — Apache-2.0 (Meta Segment Anything)
- **Install:** `uv pip install "rembg[cli]"`
- **CLI:** `rembg i <in> <out>`; flags: `-m <model>`, `-a` (alpha matting)
- **Strength:** ubiquitous, fastest install, bundled weights covers ~90% of casual cutout jobs.
- **Weakness:** frame-by-frame only (flickers on video), chunky hair edges without `-a`.

## BiRefNet — 2024 SOTA bilateral

- **Repo:** https://github.com/ZhengPeng7/BiRefNet
- **HF:** https://huggingface.co/ZhengPeng7/BiRefNet
- **License:** MIT
- **Engine:** PyTorch + transformers.AutoModelForImageSegmentation
- **Strength:** best open-source hair / fur / semi-transparent edge detail as of 2024.
- **Default input size:** 1024×1024. For very large photos, loss of detail from the resize dominates; consider a tile-based wrapper.
- **GPU:** CUDA strongly recommended; CPU works but slow.

## RMBG-2.0 — briaai 2025

- **HF:** https://huggingface.co/briaai/RMBG-2.0
- **License:** Apache-2.0
- **Engine:** transformers.AutoModelForImageSegmentation (`trust_remote_code=True`)
- **Strength:** tuned for e-commerce / product photography (clean white/neutral backgrounds). Extremely clean on studio shots.
- **Note:** RMBG v1.4 is distinct and is **CC-BY-NC** (non-commercial). This skill does NOT use v1.4.

## RobustVideoMatting (RVM) — video

- **Repo:** https://github.com/PeterL1n/RobustVideoMatting
- **License:** GPL-3.0
- **Paper:** Robust High-Resolution Video Matting with Temporal Guidance (WACV 2022)
- **Engine:** PyTorch; ships TorchScript + ONNX exports too
- **Variants:**
  - `mobilenetv3` — ~4K real-time on an RTX 3060; the default
  - `resnet50` — higher quality, slower
- **Input:** any ffmpeg-readable video (internally uses PyAV / PIMS)
- **Outputs:** composition (subject over bg), alpha video, premultiplied foreground, PNG sequence — pick with `--output-type`.
- **License caveat (GPL-3.0):** linking RVM code into your product makes it GPL. For commercial closed-source, invoke `inference.py` as a subprocess. This skill's driver does exactly that.

## Comparison

| Model      | Still quality      | Hair / fur edges  | Product (white bg) | Video         | License for closed commercial |
|------------|--------------------|-------------------|--------------------|---------------|-------------------------------|
| rembg      | Good               | Medium (w/ `-a`)  | Good               | Frame-by-frame, flicker | Yes (MIT)         |
| BiRefNet   | Excellent          | Best              | Excellent          | Frame-by-frame | Yes (MIT)                    |
| RMBG-2.0   | Excellent          | Good              | Best               | Frame-by-frame | Yes (Apache-2.0)             |
| RVM        | N/A (video model)  | Good              | N/A                | Best          | Yes (via subprocess boundary) |

## Explicitly excluded

| Tool                        | Reason                                              |
|-----------------------------|-----------------------------------------------------|
| RMBG v1.4                   | CC-BY-NC — non-commercial only (v2.0 is safe)       |
| Adobe Sensei                | Proprietary SaaS                                    |
| backgroundremover.app       | Proprietary freemium SaaS                           |
| PhotoRoom / remove.bg API   | Proprietary SaaS                                    |

## Recipes for pathological cases

- **Wispy hair on a low-res portrait:** BiRefNet + pymatting refine with a manual trimap.
- **Glass or liquid:** no open-source model is reliable; keyframe it in DaVinci/Nuke.
- **Subject partially outside frame:** models tend to cut at the image edge; pad canvas with 50 px before matting and re-crop after.
- **Motion blur on a fast subject (video):** RVM `resnet50` variant; mobilenetv3 blurs motion-blurred edges.
- **Black subject on dark background:** any model may fail; provide a trimap and use `refine`.
