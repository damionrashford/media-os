# FFmpeg Quality Metrics — Reference

Full-reference (distorted vs reference) objective quality metrics and
single-input QC filters available in ffmpeg. All full-reference metrics
require **pixel-aligned inputs**: same width, height, pixel format, frame
rate, and (ideally) length. ffmpeg does not auto-align — you must prefilter.

---

## 1. Filter option tables

### 1.1 `libvmaf`

VMAF (Video Multi-method Assessment Fusion) — Netflix's perceptual metric.
Inputs: `[distorted][reference]` (distorted first).

| Option | Type | Default | Notes |
|---|---|---|---|
| `model` | string | `version=vmaf_v0.6.1` | Key=value; `version=NAME` uses bundled models; `path=/abs/path.json` loads an external model. Multiple models may be stacked via `\|`. |
| `feature` | string | — | Extra features: `name=psnr`, `name=float_ssim`, `name=float_ms_ssim`, `name=ciede`. Stack via `\|`. |
| `log_path` | string | — | Write per-frame + pooled results here. |
| `log_fmt` | enum | `xml` | `xml`, `json`, `csv`. Prefer `json`. |
| `n_threads` | int | `0` (=1) | Worker threads; set to CPU count. |
| `n_subsample` | int | `1` | Skip every Nth frame (e.g. `5` = sample 20%). |
| `pool` | enum | `mean` | `mean`, `harmonic_mean`, `min`. Affects the scalar reported. |
| `ts_sync_mode` | enum | `near` | Timestamp sync: `near` (default), `nearest`. |
| `phone_model` | bool | `0` | Legacy option for phone viewing model (newer: use `model=path=`). |

Models (bundled in ffmpeg >= 4.4):

| Model version | Target viewing | Notes |
|---|---|---|
| `vmaf_v0.6.1` | 1080p desktop, ~1.5H viewing distance | Default. Rewards sharpness. |
| `vmaf_v0.6.1neg` | 1080p desktop, "no enhancement gain" | Harder to game with unsharp masks or detail synthesis. |
| `vmaf_4k_v0.6.1` | 4K display, 1.5H | Use for 2160p scoring. |
| `vmaf_float_v0.6.1` | 1080p desktop | Float (higher precision) variant; slightly slower. |
| `vmaf_float_v0.6.1neg` | 1080p desktop, no-enhance | Float + neg. |
| `vmaf_v0.6.1.json` (phone) | phone viewing | Smaller display assumption. Pass via `model=path=`. |

### 1.2 `psnr`

Peak Signal-to-Noise Ratio. Inputs: two streams (any order).

| Option | Type | Default | Notes |
|---|---|---|---|
| `stats_file` (alias `f`) | string | — | File to write per-frame stats. `-` = stdout. |
| `stats_version` | int | `1` | Set to `2` for additional fields. |
| `output_max` | bool | `0` | Include MAX_PSNR. |

Stats per frame: `n:X mse_avg:Y mse_y:A mse_u:B mse_v:C psnr_avg:Z psnr_y:.. psnr_u:.. psnr_v:..`.

Summary line on stderr: `PSNR y:42.13 u:45.22 v:45.88 average:43.21 min:... max:...`.

### 1.3 `ssim`

Structural Similarity Index. Inputs: two streams.

| Option | Type | Default | Notes |
|---|---|---|---|
| `stats_file` (alias `f`) | string | — | Per-frame stats file. |

Stats per frame: `n:X Y:a U:b V:c All:d (dB)`.
Summary: `SSIM Y:0.973 U:0.988 V:0.989 All:0.978 (16.54dB)`.

### 1.4 `vmafmotion`

Motion score only (one of the VMAF sub-features, isolated).

| Option | Type | Default | Notes |
|---|---|---|---|
| `stats_file` (alias `f`) | string | — | Per-frame motion score file. |

Useful for classifying clip complexity before choosing encoder settings.

### 1.5 `identity`

Pixel-identical check. Outputs max PSNR (effectively infinity) when inputs
are bit-identical.

| Option | Type | Default | Notes |
|---|---|---|---|
| `stats_file` (alias `f`) | string | — | Per-frame identity stats. |

### 1.6 `msad`

Mean Sum of Absolute Differences. Cheap scalar distance proxy.

| Option | Type | Default | Notes |
|---|---|---|---|
| `stats_file` (alias `f`) | string | — | Per-frame MSAD. |

### 1.7 `blockdetect` (single-input QC)

Detect 8x8 blocking artifacts.

| Option | Type | Default | Notes |
|---|---|---|---|
| `period_min` | int | `3` | Minimum block period. |
| `period_max` | int | `24` | Maximum block period. |
| `planes` | int | `1` | Bitmask; `7` = Y+U+V. |

Emits `lavfi.block` frame metadata; higher = more blocky.

### 1.8 `blurdetect` (single-input QC)

Edge-based blurriness estimator.

| Option | Type | Default | Notes |
|---|---|---|---|
| `low` | float | `0.0588` | Canny low threshold. |
| `high` | float | `0.1176` | Canny high threshold. |
| `radius` | int | `50` | Edge search radius. |
| `block_pct` | int | `80` | % of largest-blur blocks to use. |
| `block_width` | int | `-1` | Block size W (auto if -1). |
| `block_height` | int | `-1` | Block size H. |
| `planes` | int | `1` | Which planes to analyse. |

Emits `lavfi.blur` metadata; higher = more blur.

---

## 2. VMAF model catalog — which to use

| Use case | Model | Why |
|---|---|---|
| Streaming ladder QA (1080p/720p) | `vmaf_v0.6.1` | Default, trained on desktop viewing. |
| 4K VOD / UHD streaming | `vmaf_4k_v0.6.1` | Tuned for larger displays + longer viewing distance. |
| Encoder bake-off with enhancement risk | `vmaf_v0.6.1neg` | Ignores benefits of pre-sharpening / detail synthesis. |
| Mobile / phone playback | phone model (legacy `phone_model=1` or `model=path=vmaf_v0.6.1.json` on phone configuration) | Smaller display means worse quality is less visible. |
| High-precision research | `vmaf_float_v0.6.1` | Float pipeline, slightly more accurate. |
| Archival / near-lossless | `vmaf_v0.6.1` with `pool=harmonic_mean` | Focus on worst-frame quality, not average. |

Stack models in one pass: `model=version=vmaf_v0.6.1\|version=vmaf_v0.6.1neg`.

---

## 3. Scoring bands

### 3.1 VMAF (0–100)

| Band | Interpretation |
|---|---|
| 95–100 | Near-transparent; mastering / archive. |
| 90–95 | Excellent; premium OTT top tiers. |
| 80–90 | Good; main streaming tiers, typical CRF 20–23 x264. |
| 70–80 | Watchable; compression visible to attentive viewer. |
| 60–70 | Noticeable artifacts; acceptable only for low-bandwidth fallback. |
| < 60 | Visibly degraded. |

### 3.2 PSNR (dB, luma)

Content-dependent, but rough bands:

| Band | Interpretation |
|---|---|
| ≥ 45 | Near-lossless (ceiling ~50–60 dB for low-noise content). |
| 40–45 | High. |
| 35–40 | Moderate. |
| 30–35 | Low; visible compression. |
| < 30 | Poor. |

### 3.3 SSIM (0–1)

| Band | Interpretation |
|---|---|
| ≥ 0.98 | Excellent. |
| 0.95–0.98 | Good. |
| 0.90–0.95 | Acceptable; compression visible. |
| < 0.90 | Visibly degraded. |

---

## 4. Mathematical definitions (brief)

### 4.1 PSNR

```
MSE   = (1 / (W*H)) * Σ (I_ref(x,y) - I_dist(x,y))^2
PSNR  = 10 * log10 (MAX_I^2 / MSE)
```

where `MAX_I` is the maximum pixel value (255 for 8-bit, 1023 for 10-bit).
PSNR is reported per plane (Y, U, V) and as a weighted average.

### 4.2 SSIM

For two windows `x` and `y`:

```
SSIM(x,y) = (2μ_x μ_y + c1)(2σ_xy + c2) / ((μ_x^2 + μ_y^2 + c1)(σ_x^2 + σ_y^2 + c2))
```

with `c1 = (K1 * L)^2`, `c2 = (K2 * L)^2`, L = dynamic range. ffmpeg uses
the standard 8x8 sliding window and averages across the frame. SSIM is
normalised to [-1, 1], reported in [0, 1] for natural images, and
optionally converted to dB by `-10*log10(1 - SSIM)`.

### 4.3 VMAF

A fused metric combining:

- **VIF** (Visual Information Fidelity) — 4 scales.
- **ADM** (Additive Distortion Measure / Detail Loss Metric).
- **Motion** (temporal motion complexity).

These features feed a Support Vector Regressor (SVR) trained on subjective
(DMOS) scores from the NFLX dataset. Output is 0–100.

---

## 5. Aggregation: pooled vs per-frame vs per-scene

- **Pooled** — single scalar across the whole clip.
  - `mean` (default) — arithmetic mean of per-frame scores.
  - `harmonic_mean` — emphasises worst frames; report this for streaming QA.
  - `min` — absolute worst frame.
- **Per-frame** — the JSON `frames` array; useful for plotting or finding
  dropouts (e.g. 1st-percentile frame analysis).
- **Per-scene** — cut the clip at scene changes (`scdet` or `select='gt(scene,0.4)'`),
  score each scene separately, and report the minimum scene VMAF.
  Hard scenes drag down overall quality even when the mean looks fine.

Extract from VMAF JSON:

```bash
jq '.pooled_metrics.vmaf.mean'              vmaf.json
jq '.pooled_metrics.vmaf.harmonic_mean'     vmaf.json
jq '[.frames[].metrics.vmaf] | sort | .[0:10]' vmaf.json   # 10 worst frames
```

---

## 6. Alignment preprocessing recipes

### 6.1 Scale both to same resolution

```
[0:v]scale=1920:1080:flags=bicubic[dist];
[1:v]scale=1920:1080:flags=bicubic[ref];
```

Use `flags=lanczos` for higher-quality upscaling; `bicubic` is standard.

### 6.2 Resample framerate (decimate or interpolate)

Simple (nearest-neighbour duplication / drop):

```
fps=24
```

Motion-compensated (cleaner for big fps changes):

```
minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me=epzs
```

### 6.3 Match pixel format

```
format=yuv420p        # 8-bit 4:2:0, most common
format=yuv420p10le    # 10-bit (for 10-bit VMAF models)
format=yuv444p        # 4:4:4 (no chroma subsampling)
```

### 6.4 Match length

Pad the shorter stream:

```
[0:v]tpad=stop_mode=clone:stop_duration=5[dist]
```

Or truncate to the shorter length:

```
-t 00:02:30.000
```

### 6.5 Correct a crop offset

If the distorted was cropped (e.g. 1920x1080 vs 1920x1040 letterbox strip):

```
[1:v]crop=1920:1040:0:20[ref_cropped];
[0:v]scale=1920:1040[dist];
[dist][ref_cropped]libvmaf=...
```

### 6.6 Canonical full alignment block (reusable)

```
[0:v]scale=1920:1080:flags=bicubic,fps=24,format=yuv420p[dist];
[1:v]scale=1920:1080:flags=bicubic,fps=24,format=yuv420p[ref];
```

---

## 7. Rate-distortion curve methodology

The standard way to pick an encoder setting for a target quality:

1. **Pick a source clip** representative of your catalog (action / dialogue
   / animation — one of each is ideal).
2. **Sweep encoder settings:**
   - For CRF-based encoders (libx264, libx265, libsvtav1, libvpx-vp9):
     CRF values like 18, 20, 22, 24, 26, 28, 30 (x264/x265) or
     23, 27, 32, 36, 40 (AV1/VP9 — different scale).
   - For bitrate-based: sweep `-b:v` from 500k to 8000k in 500k steps.
3. **Encode each setting** at the same preset (e.g. `medium` or `slow`).
4. **Compute VMAF** for each encode vs source (matched resolution/fps).
5. **Record** (setting, filesize or bitrate, VMAF mean, VMAF harmonic_mean,
   VMAF min).
6. **Plot** bitrate (x) vs VMAF (y). The "knee" is where VMAF gains
   flatten — encode higher than the knee is wasteful.
7. **Pick the operating point:**
   - For streaming ladders: choose bitrate at the knee (BD-rate analysis).
   - For CRF targeting: pick the highest CRF whose VMAF mean >= target
     (e.g. mean >= 93 and harmonic_mean >= 88).

A minimal table (what `scripts/quality.py sweep` emits):

| CRF | VMAF mean | VMAF min | VMAF hmean | Size (MB) |
|---:|---:|---:|---:|---:|
| 18 | 98.1 | 94.2 | 97.8 | 182.3 |
| 22 | 95.6 | 88.4 | 94.9 | 112.7 |
| 26 | 91.2 | 80.1 | 89.5 | 71.4 |
| 30 | 85.4 | 72.6 | 82.8 | 45.9 |

Read the table: CRF 22 is likely the sweet spot for "excellent" (>= 95
mean) — CRF 18 nearly doubles the filesize for 2.5 VMAF points.

### 7.1 BD-rate (optional, advanced)

Bjøntegaard-Delta rate compares two codecs' RD curves, reporting the
average bitrate saving at equal VMAF. Tools: the `bjontegaard` python
package, or `vmaf`'s included scripts. Not built into ffmpeg.

### 7.2 Per-scene RD

For heterogeneous content, compute VMAF per scene and weight by scene
duration. This is the basis of Netflix's per-title and per-shot encoding.

---

## 8. VMAF JSON structure (for parsing)

```json
{
  "version": "...",
  "fps": 23.976,
  "frames": [
    {
      "frameNum": 0,
      "metrics": {
        "integer_motion": 0.0,
        "integer_vif_scale0": 0.95,
        "integer_vif_scale1": 0.97,
        "integer_vif_scale2": 0.98,
        "integer_vif_scale3": 0.98,
        "integer_adm2": 0.99,
        "vmaf": 96.8
      }
    }
  ],
  "pooled_metrics": {
    "vmaf": {
      "min": 72.5,
      "max": 99.2,
      "mean": 94.1,
      "harmonic_mean": 93.6
    }
  }
}
```

---

## 9. References

- https://ffmpeg.org/ffmpeg-filters.html#libvmaf
- https://ffmpeg.org/ffmpeg-filters.html#psnr
- https://ffmpeg.org/ffmpeg-filters.html#ssim
- https://ffmpeg.org/ffmpeg-filters.html#vmafmotion
- https://ffmpeg.org/ffmpeg-filters.html#identity
- https://ffmpeg.org/ffmpeg-filters.html#msad
- https://ffmpeg.org/ffmpeg-filters.html#blockdetect
- https://ffmpeg.org/ffmpeg-filters.html#blurdetect
- https://github.com/Netflix/vmaf — upstream VMAF project, models, and research papers.
