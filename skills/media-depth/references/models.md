# Depth models — per-model matrix

Consult this file when picking between Depth-Anything v2 variants, switching to MiDaS, or needing metric depth instead of relative.

## Depth-Anything v2 (Apache 2.0, ByteDance/TikTok, 2024)

Upstream: `https://github.com/DepthAnything/Depth-Anything-V2`
HuggingFace org: `depth-anything`

| Variant                                           | Params | 1080p fps (3090, FP16) | Notes                                  |
|---------------------------------------------------|--------|------------------------|----------------------------------------|
| `Depth-Anything-V2-Small-hf`                      | ~25 M  | ~40 fps                | Fastest; default for live / batch      |
| `Depth-Anything-V2-Base-hf`                       | ~97 M  | ~20 fps                | Best speed/quality trade               |
| `Depth-Anything-V2-Large-hf`                      | ~335 M | ~8 fps                 | Sharpest edges; use for hero shots     |

- **Native input size:** 518 × 518.
- **Output:** inverse-relative depth (higher = closer), arbitrary scale.
- **Transformer backbone:** DINOv2 encoder + DPT head.
- **HuggingFace integration:** `pipeline("depth-estimation", model=hf_id)`; returns dict with `"depth"` (PIL.Image) or `"predicted_depth"` (torch.Tensor).
- **Strengths vs v1:** crisper edges, fewer floating-artifact halos, better transparent and reflective surfaces.
- **Metric fine-tunes:**
  - `Depth-Anything-V2-Metric-Indoor-Small/Base/Large-hf` — trained on Hypersim (depth in meters, indoor only, max 20 m range).
  - `Depth-Anything-V2-Metric-Outdoor-Small/Base/Large-hf` — trained on Virtual KITTI (depth in meters, outdoor, max 80 m range).
  - Metric output is still inverse-scale by default through the pipeline; post-process to meters per the model card.

## MiDaS v3.1 (MIT, Intel ISL)

Upstream: `https://github.com/isl-org/MiDaS`
HuggingFace org: `Intel`

| Variant                            | Backbone         | Input | 1080p fps (3090) | Use when                              |
|------------------------------------|------------------|-------|------------------|---------------------------------------|
| `Intel/dpt-swinv2-tiny-256`        | Swin V2 Tiny     | 256   | ~60 fps          | Minimum VRAM / mobile / embedded      |
| `Intel/dpt-large-384` (legacy)     | ViT-Large        | 384   | ~15 fps          | Legacy v3.0 baseline                  |
| `Intel/dpt-beit-large-512`         | BEiT-Large       | 512   | ~6 fps           | Best-quality pre-DepthAnything        |

- **Output:** inverse-relative depth (higher = closer). Same convention as Depth-Anything.
- **DPT (Dense Prediction Transformer)** head across all variants.
- **Still a solid baseline** for lower-VRAM devices and as a speed floor. For quality on CPU, Depth-Anything v2 Small remains the better pick.

## Relative vs metric depth

- **Relative depth** — each output is normalized internally; comparing two separate frames does NOT yield consistent meters. Perfect for visual / VFX uses where the viewer only needs the within-frame ordering.
- **Metric depth** — output is in meters. Required for:
  - Camera solve / photogrammetry seed
  - 3D scene reconstruction at scale
  - Mixed reality anchoring against real IMU data
- Metric monocular depth is fundamentally under-constrained; all "metric" models solve it by training on a fixed domain (indoor vs outdoor, a specific depth range).

## Disparity vs depth

- **Depth** (Z) — distance from camera along optical axis. Units: meters (metric) or unitless (relative).
- **Disparity** — inverse of depth, proportional to `1 / Z`. Stereo matchers produce disparity; most monocular models produce "inverse relative depth" which IS proportional to disparity up to a scale factor.
- The HuggingFace `depth-estimation` pipeline outputs what the model predicts. For Depth-Anything v2 and MiDaS, that's *inverse relative depth* — i.e. brighter = closer.

## How to convert "nearest = bright" to "nearest = dark"

Most 3D tools (Blender, Nuke, Fusion, Unreal) expect **nearest = dark, far = bright**. The `depth.py --invert` flag flips the normalization.

Equivalent math on a 16-bit PNG:

```python
import cv2, numpy as np
d = cv2.imread("depth.png", -1)
cv2.imwrite("depth_inv.png", (65535 - d).astype(np.uint16))
```

## When to pick which

| Goal                                  | Model                            | Size   |
|---------------------------------------|----------------------------------|--------|
| Single hero still, quality matters    | `depthanything-v2`               | large  |
| Batch 10 000 photos, throughput       | `depthanything-v2`               | small  |
| Video 1080p at interactive rate       | `depthanything-v2`               | small  |
| Embedded / CPU-only / <4 GB VRAM      | `midas` (`dpt-swinv2-tiny-256`)  | tiny   |
| Research baseline / reproducing v3.1  | `midas` (`dpt-beit-large-512`)   | large  |
| Metric indoor depth in meters         | Depth-Anything-V2-Metric-Indoor  | small/base/large |
| Metric outdoor depth in meters        | Depth-Anything-V2-Metric-Outdoor | small/base/large |
