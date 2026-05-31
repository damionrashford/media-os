# Upscale Model Reference

All models listed here are open-source AND commercial-safe. CodeFormer (S-Lab
research-only) and Topaz Video AI (commercial) are intentionally excluded from
this skill.

## Real-ESRGAN — the default

- **Repo:** https://github.com/xinntao/Real-ESRGAN
- **License:** BSD-3-Clause
- **CLI:** `realesrgan-ncnn-vulkan` (cross-platform prebuilt binary)
- **Releases:** https://github.com/xinntao/Real-ESRGAN/releases
- **Bundled model names (`-n`):**
  - `realesrgan-x4plus` — general photos, 4x only
  - `realesrnet-x4plus` — less aggressive; preserves more source detail
  - `realesrgan-x4plus-anime` — anime stills
  - `realesr-animevideov3` — optimized for video frames (faster, temporally stable)
- **Scale factors:** 2, 3, 4 (pass `-s`)
- **GPU:** Vulkan — works on NVIDIA, AMD, Intel, Apple Silicon (MoltenVK). No CUDA needed.
- **Typical use:** 1080p photo → 4K, 720p archive video → 1440p, social-media upscales.
- **Input resolution range:** no hard lower bound; outputs >~12 000 px on a side need tiling (`-t`).

## Real-CUGAN — anime-optimized

- **Repo:** https://github.com/nihui/realcugan-ncnn-vulkan (NCNN build of bilibili/ailab/Real-CUGAN)
- **Upstream:** https://github.com/bilibili/ailab/tree/main/Real-CUGAN
- **License:** MIT
- **CLI:** `realcugan-ncnn-vulkan`
- **Releases:** https://github.com/nihui/realcugan-ncnn-vulkan/releases
- **Denoise levels (`-n`):** -1 conservative, 0 default, 1 light, 2 medium, 3 heavy
- **Scale factors:** 2, 3, 4
- **Typical use:** anime / cartoon / cel-shaded art. Sharper edges than Real-ESRGAN on flat color regions.
- **Caveat:** can over-sharpen real photos; for live action use Real-ESRGAN.

## SwinIR — transformer photo SR

- **Repo:** https://github.com/JingyunLiang/SwinIR
- **License:** Apache-2.0
- **CLI:** `python SwinIR/main_test_swinir.py` (no standalone binary)
- **Weights:** https://github.com/JingyunLiang/SwinIR/releases
- **Tasks:** `classical_sr`, `lightweight_sr`, `real_sr`, `gray_dn`, `color_dn`, `jpeg_car`
- **Scale factors:** 2, 3, 4
- **GPU:** CUDA-only via PyTorch (CPU works but very slow)
- **Typical use:** fine-texture photo SR; excels on natural images.

## HAT — 2023 SOTA photo SR

- **Repo:** https://github.com/XPixelGroup/HAT
- **License:** Apache-2.0
- **CLI:** `python HAT/hat/test.py -opt <yml>`
- **Weights:** https://github.com/XPixelGroup/HAT/releases
- **Scale factors:** 2, 3, 4
- **GPU:** CUDA (via PyTorch + BasicSR)
- **Typical use:** when benchmark PSNR matters; currently leads classic SR benchmarks.
- **Tip:** tile size controlled via `tile` key in the YML config.

## GFPGAN — face restoration

- **Repo:** https://github.com/TencentARC/GFPGAN
- **License:** Apache-2.0
- **CLI:** `python -m gfpgan.inference_gfpgan` or `python inference_gfpgan.py`
- **Weights:** auto-downloaded on first run into `gfpgan/weights/`
- **Versions (`-v`):** 1.2, 1.3, 1.4 (1.4 is the most recent; also supports `RestoreFormer`)
- **Background:** pass `--bg_upsampler realesrgan` to pair with Real-ESRGAN on non-face pixels.
- **Typical use:** scanned portraits, old family photos, low-res headshots.
- **Caveat:** hallucinates plausible features — unsafe for ID photos, evidence, or fidelity-critical work.

## waifu2x-ncnn-vulkan — classic anime

- **Repo:** https://github.com/nihui/waifu2x-ncnn-vulkan
- **License:** MIT
- **CLI:** `waifu2x-ncnn-vulkan`
- **Scale factors:** 1, 2, 4, 8, 16, 32
- **Noise levels (`-n`):** -1..3
- **Typical use:** very small anime sources (<512 px), pre-2020 cartoon art.
- **Note:** Real-CUGAN generally supersedes waifu2x quality — use waifu2x for small/legacy sources.

## Upscayl — desktop GUI

- **Repo:** https://github.com/upscayl/upscayl
- **License:** AGPL-3.0
- **Form:** Electron app; wraps Real-ESRGAN binaries. Not used by this skill's scripts.
- **Caveat:** AGPL imposes source-release obligations on derived code. Running it to produce outputs is fine.

## chaiNNer — node pipeline

- **Repo:** https://github.com/chaiNNer-org/chaiNNer
- **Website:** https://chainner.app/
- **License:** GPL-3.0
- **Form:** Electron node-graph UI. Can run PyTorch, ONNX, NCNN SR models arbitrarily (including Real-ESRGAN, SwinIR, HAT, DAT, RGT, SPAN, ATD, and others).
- **Use when:** you want a visual pipeline with segment → upscale → denoise → sharpen stages, or to try models this skill doesn't ship a recipe for.
- **Caveat:** GPL — same source-release caveats as AGPL tools if you link its code.

## Not in this skill (and why)

| Tool              | License            | Reason                                     |
|-------------------|--------------------|--------------------------------------------|
| CodeFormer        | S-Lab License 1.0  | Non-commercial / research-only             |
| Topaz Video AI    | Commercial (paid)  | Proprietary paid software                  |
| Remini / Fotor    | SaaS               | Proprietary cloud, not locally runnable    |

## Benchmarks (rough guidance, not a substitute for testing your own content)

| Content               | Best open-source model     |
|-----------------------|----------------------------|
| Modern photo (HD)     | Real-ESRGAN x4plus         |
| Modern photo, PSNR    | HAT x4                     |
| Portrait / face       | GFPGAN 1.4 + Real-ESRGAN bg |
| Live-action video     | Real-ESRGAN animevideov3 (despite name — tuned for video) |
| Anime video           | Real-ESRGAN animevideov3 or Real-CUGAN |
| Anime still art       | Real-CUGAN                 |
| Tiny (<256 px) anime  | waifu2x                    |
| Academic benchmarks   | HAT, then SwinIR           |

## Model download hosts (mirror-friendly)

- Real-ESRGAN weights: GitHub Releases (`xinntao/Real-ESRGAN`) — bundled in the NCNN release zip.
- Real-CUGAN: GitHub Releases (`nihui/realcugan-ncnn-vulkan`) — bundled in release zip.
- SwinIR: GitHub Releases + Google Drive (see README model zoo section).
- HAT: GitHub Releases + Baidu Netdisk + Google Drive (README).
- GFPGAN: auto-downloads to `gfpgan/weights/` on first run.
