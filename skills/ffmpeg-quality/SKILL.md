---
name: ffmpeg-quality
description: >
  Measure encode quality with ffmpeg reference-vs-distorted filters: libvmaf (Netflix VMAF), psnr, ssim, vmafmotion, identity, msad, blockdetect, blurdetect. Use when the user asks to measure VMAF, run VMAF scoring, compute PSNR, compute SSIM, compare encoded vs source quality, benchmark a codec, find the best CRF for a target VMAF, verify encoder output, or QA a transcoded file against the original.
argument-hint: "[reference] [distorted]"
---

# Ffmpeg Quality

**Context:** $ARGUMENTS

Reference-vs-distorted (full-reference) objective quality metrics with ffmpeg filters. VMAF is the gold standard for perceptual quality; PSNR and SSIM are older but universally understood. All full-reference filters require the two inputs to be **pixel-aligned**: same resolution, same frame rate, same pixel format, same length.

## Quick start

- **Score a transcode vs its source (VMAF):** → Step 2 (VMAF recipe)
- **Quick PSNR/SSIM number:** → Step 2 (PSNR or SSIM recipe)
- **Find best CRF for a target VMAF:** → Step 3 (rate-distortion sweep)
- **Single-file QC (no reference):** → Step 2 (blockdetect / blurdetect)
- **Parse per-frame results:** → Step 3 (JSON/log parsing)

## When to use

- QA a transcoded / streamed / compressed file against the original.
- Benchmark encoders (x264 vs x265 vs svt-av1 vs vp9) on the same source.
- Pick an optimal CRF / bitrate for a target VMAF (e.g. 93 for near-transparent, 80 for "good enough" mobile).
- Validate a live encoder ladder rung-by-rung.
- Single-input block/blur QC when no reference exists (encoder output spot-check).

## Step 1 — Ensure alignment (prerequisite)

Full-reference metrics (VMAF, PSNR, SSIM) **require both inputs to match exactly** on:

1. **Resolution** — scale both to a target res with `scale=W:H:flags=bicubic`.
2. **Frame rate** — resample with `fps=R` (or `minterpolate` for fractional conversions).
3. **Pixel format** — convert with `format=yuv420p` (or `yuv422p10le`, matching the model bit-depth).
4. **Length** — pad the shorter with `tpad`, or truncate with `-t`.
5. **Pixel offset** — if cropped, pre-crop or the metric will collapse (esp. PSNR, 1-pixel shift wrecks it).

**Canonical prefilter** (both upscaled to 1080p, 24 fps, yuv420p):

```
[0:v]scale=1920:1080:flags=bicubic,fps=24,format=yuv420p[dist];
[1:v]scale=1920:1080:flags=bicubic,fps=24,format=yuv420p[ref];
```

Check alignment first: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,pix_fmt,nb_frames <file>`.

## Step 2 — Pick a metric and run

### VMAF (preferred; perceptual, 0–100)

Default model (`vmaf_v0.6.1`) — 1080p desktop viewing:

```bash
ffmpeg -i distorted.mp4 -i reference.mp4 -lavfi \
  "[0:v]scale=1920:1080:flags=bicubic[dist];[1:v]scale=1920:1080:flags=bicubic[ref];[dist][ref]libvmaf=model=version=vmaf_v0.6.1:log_path=vmaf.json:log_fmt=json:n_threads=8" \
  -f null -
```

**Order matters:** `[distorted][reference]` — distorted first.

Model selection:
- `vmaf_v0.6.1` — default, 1080p desktop.
- `vmaf_v0.6.1neg` — "no enhancement gain"; penalizes over-sharpening. Use when encoder might cheat with unsharp masks.
- `vmaf_4k_v0.6.1` — 4K displays, larger viewing distance assumed.
- `vmaf_float_v0.6.1` — higher-precision float model.
- Phone model: `libvmaf=model=version=vmaf_v0.6.1:phone_model=1` (legacy flag; newer builds use `model=path=/path/to/vmaf_v0.6.1.json`).

### PSNR (simple dB; sensitive to any pixel shift)

```bash
ffmpeg -i distorted.mp4 -i reference.mp4 -lavfi "[0:v][1:v]psnr=stats_file=psnr.log" -f null -
```

Stats file per-frame: `n:X mse_avg:Y mse_y:A mse_u:B mse_v:C psnr_avg:Z psnr_y:... psnr_u:... psnr_v:...`.

### SSIM (structural similarity, 0–1)

```bash
ffmpeg -i distorted.mp4 -i reference.mp4 -lavfi "[0:v][1:v]ssim=stats_file=ssim.log" -f null -
```

Stats file per-frame: `n:X Y:a U:b V:c All:d (dB)`.

### Single-input QC (no reference)

```bash
ffmpeg -i in.mp4 -vf "blockdetect=period_min=3:period_max=24:planes=7" -f null -
ffmpeg -i in.mp4 -vf "blurdetect" -f null -
```

Both emit per-frame metadata; higher `lavfi.block` / `lavfi.blur` means more artifacts.

### Other full-reference filters

- `vmafmotion` — motion-complexity only (one of VMAF's sub-features, isolated).
- `identity` — detects whether two streams are byte-identical.
- `msad` — Mean Sum of Absolute Differences (cheap proxy for PSNR).

## Step 3 — Parse and aggregate

**VMAF JSON summary** (pooled mean):

```bash
jq '.pooled_metrics.vmaf.mean' vmaf.json
jq '.pooled_metrics.vmaf | {min, max, mean, harmonic_mean}' vmaf.json
jq '.frames[] | {n: .frameNum, vmaf: .metrics.vmaf}' vmaf.json | head
```

**PSNR / SSIM averages** print to stderr at the end:
```
[Parsed_psnr_0 @ ...] PSNR y:42.13 u:45.22 v:45.88 average:43.21
[Parsed_ssim_0 @ ...] SSIM Y:0.973 U:0.988 V:0.989 All:0.978 (16.54dB)
```

**Rate-distortion sweep** (use `scripts/quality.py sweep`, Step 4):
- Encode source at CRF 18, 22, 26, 30, 34.
- Compute VMAF of each encode vs source.
- Build a CRF → VMAF → filesize table; pick the knee.

## Step 4 — Interpret

**VMAF (0–100):**
- `< 70` — visibly degraded.
- `70–80` — watchable, noticeable compression.
- `80–90` — good; streaming ladder "main" tiers.
- `90–95` — excellent.
- `95+` — near-transparent; reserved for archive/mastering.
- `~100` — identical (within float noise).

**PSNR (dB):** content-dependent ceiling. Rough bands:
- `< 30` — poor.
- `30–35` — low.
- `35–40` — moderate.
- `40–45` — high.
- `45+` — excellent / near-lossless.

**SSIM (0–1):**
- `< 0.90` — visible degradation.
- `0.90–0.95` — acceptable.
- `0.95–0.98` — good.
- `0.98+` — excellent.

Per-frame dips matter more than the mean — sort frames ascending and look at the 1st percentile for worst-case scenes.

## Available scripts

- **`scripts/quality.py`** — subcommands `vmaf`, `psnr`, `ssim`, `sweep`. Stdlib-only, `--dry-run`, `--verbose`.

Examples:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/quality.py vmaf --reference ref.mp4 --distorted enc.mp4 --model vmaf_v0.6.1 --threads 8 --log-path vmaf.json
uv run ${CLAUDE_SKILL_DIR}/scripts/quality.py psnr --reference ref.mp4 --distorted enc.mp4 --stats-file psnr.log
uv run ${CLAUDE_SKILL_DIR}/scripts/quality.py ssim --reference ref.mp4 --distorted enc.mp4 --stats-file ssim.log
uv run ${CLAUDE_SKILL_DIR}/scripts/quality.py sweep --reference ref.mp4 --crfs 18,22,26,30 --encoder libx264 --preset medium
```

## Reference docs

- Read [`references/metrics.md`](references/metrics.md) for the full option tables, model catalog, scoring bands, scaling recipes, and rate-distortion methodology.

## Gotchas

- **Inputs must match.** ffmpeg does NOT auto-align — mismatched resolution or framerate silently produces garbage scores. Always prefilter both streams with `scale` + `fps` + `format`.
- **Input order for VMAF is `[distorted][reference]`** (distorted first). Swapping does not crash but the result is meaningless.
- **PSNR and SSIM** take both inputs but the meaning of "first" vs "second" is symmetric for the scalar score; the stats_file labels which is which via `[0:v]` vs `[1:v]`.
- **`libvmaf` requires ffmpeg built with `--enable-libvmaf`.** Check with `ffmpeg -filters | grep vmaf`. Homebrew ffmpeg generally includes it; minimal static builds often do not.
- **VMAF model files** are distributed separately for ffmpeg < 4.4. Newer builds (>= 4.4) bundle the default model. If you see "unable to load model," download the `.json` model file and use `model=path=/absolute/path.json`.
- **`n_threads` defaults to 1** — VMAF is CPU-bound; set it to `nproc` or at least 4 or it crawls.
- **VMAF requires >= 13 frames** to compute motion sub-features; very short clips return NaN.
- **PSNR is brittle to 1-pixel shifts.** If the distorted has been cropped/padded vs reference, PSNR collapses while SSIM / VMAF degrade more gracefully. Always align pre-crop.
- **SSIM is less sensitive to brightness / contrast changes** than PSNR — good for luma-graded comparisons.
- **`vmaf_v0.6.1neg`** is the right choice when you suspect the encoder is doing enhancement (sharpening / detail synthesis). Default model rewards sharpening, `neg` does not.
- **Bit depth:** if your source is 10-bit (yuv420p10le), use a float model and match pix_fmt; downconverting to 8-bit before scoring loses precision.
- **No libvmaf available?** Fall back to SSIM; SSIM correlates better with VMAF than PSNR does.
- **Don't trust the mean alone.** Look at 1st-percentile (harmonic mean is a reasonable proxy, and `.pooled_metrics.vmaf.harmonic_mean` is in the JSON).

## Examples

### Example 1: VMAF a 4K encode

```bash
ffmpeg -i encoded_4k.mp4 -i source_4k.mov -lavfi \
  "[0:v]scale=3840:2160:flags=bicubic,format=yuv420p[d];[1:v]scale=3840:2160:flags=bicubic,format=yuv420p[r];[d][r]libvmaf=model=version=vmaf_4k_v0.6.1:log_path=vmaf_4k.json:log_fmt=json:n_threads=16" \
  -f null -
jq '.pooled_metrics.vmaf.mean' vmaf_4k.json
```

### Example 2: Find best CRF for VMAF >= 93

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/quality.py sweep --reference source.mov --crfs 18,20,22,24,26 --encoder libx264 --preset slow
# Review the printed table; pick the highest CRF whose VMAF mean still >= 93.
```

### Example 3: Per-frame PSNR to spot worst frames

```bash
ffmpeg -i enc.mp4 -i ref.mov -lavfi "[0:v][1:v]psnr=stats_file=psnr.log" -f null -
sort -t: -k7 -n psnr.log | head -20   # 20 worst frames by psnr_avg
```

## Troubleshooting

### Error: `No such filter: 'libvmaf'`

Cause: ffmpeg not built with libvmaf support.
Solution: reinstall a full build (`brew reinstall ffmpeg` on macOS, or build with `--enable-libvmaf`). Verify with `ffmpeg -filters | grep vmaf`.

### Error: `Could not parse framerate` / scores look absurd

Cause: resolution or framerate mismatch between inputs.
Solution: add explicit `scale=W:H,fps=R,format=yuv420p` to both inputs before the metric filter.

### Error: VMAF value is NaN

Cause: clip too short (< 13 frames) or all-black frames confusing motion features.
Solution: score a longer range; trim out leading/trailing black with `select='gt(scene\,0.001)'` or preroll.

### Error: `unable to load model`

Cause: older ffmpeg build expecting an external `.json` model.
Solution: download the model from the Netflix/vmaf repo and pass `model=path=/abs/path/vmaf_v0.6.1.json`.

### PSNR is 20 dB lower than expected

Cause: sub-pixel or 1-pixel spatial offset between inputs.
Solution: verify `ffprobe` dimensions on both files; ensure no `crop` applied to one side; rerun with matched `scale`.
