# Denoise & Restoration (formerly ffmpeg-denoise-restore)

**Context:** $ARGUMENTS

## Quick start

- **Fast/mild video denoise (real-time):** `hqdn3d` → Step 2
- **Good quality / medium speed:** `nlmeans` → Step 2
- **Archival/highest quality (slow):** `bm3d` → Step 2
- **Temporally-adaptive (static backgrounds):** `atadenoise` → Step 2
- **Film grain removal (single-frame):** `removegrain=mode=11` → Step 2
- **AI super-resolution (2x/4x):** `dnn_processing` → Step 2
- **Audio broadband hiss:** `afftdn` → Step 4
- **Audio non-local means (preserves speech):** `anlmdn` → Step 4
- **Audio RNN-based (RNNoise model):** `arnndn` → Step 4

## When to use

- Cleaning up noisy webcams, low-light or high-ISO footage, old VHS/DVD rips, 8-mm film scans.
- Preparing noisy sources for encoding (denoise BEFORE encoding — post-compression noise is mostly irrecoverable).
- Upscaling small sources with DNN super-resolution (ESPCN / EDSR / SRCNN).
- Broadband hiss / fan noise / hum on lavalier, conference, or field audio recordings.
- Restoring rain streaks or chromatic aberration with `derain`, `chromaber_vulkan`.

## Step 1 — Identify the noise type

Before picking a filter, decide what kind of noise you have — the right filter changes drastically.

| Symptom | Likely type | Best filter |
|---|---|---|
| Random luma speckle, uniform distribution | Gaussian / thermal | `hqdn3d`, `nlmeans`, `bm3d` |
| Color blotches on flat areas | Chroma noise | `hqdn3d` with strong chroma params; `nlmeans` |
| 8×8 / 16×16 blocks on flats | Compression block noise | `deblock`, `owdenoise` (cannot fully recover) |
| Horizontal/vertical banding on gradients | Banding (bit-depth) | `gradfun`, dither to 10-bit (`format=yuv420p10le`) |
| Static speckle that never moves | Fixed-pattern / sensor | `removegrain=mode=11`, `atadenoise` |
| Visible film grain to preserve | Organic grain | Do not denoise; or `bm3d` with low sigma + add-grain back |
| Rain streaks | Weather artifact | `derain` |
| Rolling colored fringes on edges | Chromatic aberration | `chromaber_vulkan` |

Use the `ffmpeg-probe` skill (`ffprobe -show_frames`) to confirm bit depth and pixel format before denoising.

## Step 2 — Pick filter + strength

All recipes produce MP4 / H.264 CRF 18. Replace encoder / container as needed.

```bash
# LIGHT — fast, real-time-ish on CPU. hqdn3d=luma_spatial:chroma_spatial:luma_tmp:chroma_tmp
ffmpeg -i in.mp4 -vf "hqdn3d=4:3:6:4.5" -c:v libx264 -crf 18 out.mp4

# MEDIUM — better quality, non-local means (s=strength, p=patch, r=research window)
ffmpeg -i in.mp4 -vf "nlmeans=s=1.0:p=7:r=15" -c:v libx264 -crf 18 out.mp4

# HEAVY — archival; BM3D, can run at ~1 fps
ffmpeg -i in.mp4 -vf "bm3d=sigma=10:block=4:bstep=2:group=1" -c:v libx264 -crf 18 out.mp4

# TEMPORAL ADAPTIVE — only changes static pixels, preserves motion
ffmpeg -i in.mp4 -vf "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=9" -c:v libx264 -crf 18 out.mp4

# GRAIN REMOVAL — single-frame mode 11 (smooth 3x3)
ffmpeg -i in.mp4 -vf "removegrain=mode=11" -c:v libx264 -crf 18 out.mp4

# FFT-BASED — good on DCT / compression noise
ffmpeg -i in.mp4 -vf "fftdnoiz=sigma=8:amount=0.9" -c:v libx264 -crf 18 out.mp4

# DNN SUPER-RESOLUTION (2x ESPCN, TensorFlow backend)
ffmpeg -i in.mp4 -vf "dnn_processing=dnn_backend=tensorflow:model=espcn.pb:input=x:output=y" -c:v libx264 -crf 18 out.mp4
```

Strength guidance: start at the mildest setting; every denoise trades detail for noise. Bump sigma/strength one step at a time and A/B compare.

## Step 3 — Apply + verify

1. Render a 5–10 second sample first (`-ss 0 -t 10`) — faster iteration.
2. Compare to source with showspectrum / side-by-side (`ffmpeg-playback` skill).
3. Check for smearing on motion, loss of texture on skin/fabric, halos around edges.
4. If detail loss is unacceptable, lower sigma or switch to a preserving filter (`nlmeans` with p=5, r=11).

## Step 4 — Audio (parallel workflow)

Audio denoise is generally SAFE to do FIRST, before any other cleanup.

```bash
# Broadband (hiss, fan, tape) — nf is noise floor in dB, -20 to -40 typical
ffmpeg -i in.wav -af "afftdn=nf=-25" out.wav

# Non-local means (preserves speech transients)
ffmpeg -i in.wav -af "anlmdn=s=7:p=0.002:r=0.002" out.wav

# RNNoise — needs an .rnnn model file (download from xiph/rnnoise repo)
ffmpeg -i in.wav -af "arnndn=m=bd.rnnn" out.wav

# Band-limit to voice range before other processing
ffmpeg -i in.wav -af "highpass=f=80,lowpass=f=12000" out.wav
```

## Available scripts

- **`scripts/denoise.py`** — opinionated wrapper, subcommands: `video`, `grain`, `audio`, `sr` (super-resolution). Supports `--dry-run`, `--verbose`.

## Workflow

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py video --input in.mp4 --output out.mp4 --strength medium
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py grain --input in.mp4 --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py audio --input in.wav --output out.wav --method afftdn
uv run ${CLAUDE_SKILL_DIR}/scripts/denoise.py sr --input in.mp4 --output out.mp4 --scale 2 --model espcn.pb
```

## Reference docs

- Read [`references/denoise-restore-filters.md`](denoise-restore-filters.md) for full option tables, noise-type diagnosis, strength/speed/quality matrix, DNN model sources, and end-to-end recipe book (VHS, webcam, DSLR, film grain).

## Gotchas

- **Every denoise filter TRADES DETAIL FOR NOISE.** Start mild and tune up — you cannot un-denoise.
- **hqdn3d full form** is `hqdn3d=luma_spatial:chroma_spatial:luma_tmp:chroma_tmp`. With no args it uses mild defaults (4:3:6:4.5).
- **nlmeans params:** `s=strength, p=patch_size, r=research_window`. p=7, r=15 is a good default; p=3 r=9 is faster; p=9 r=21 is heavy.
- **bm3d is extremely slow** — can be ~1 fps. Only for archival work. Also requires an even number of frames when `group>1`.
- **atadenoise is temporal** — preserves static detail beautifully but smears motion trails; bad for fast action.
- **`dnn_processing` requires ffmpeg built with TensorFlow OR OpenVINO OR NativeDN** support. Most distro packages DO NOT include it. Check `ffmpeg -filters | grep dnn_processing`.
- **SR model files (.pb / .onnx) must be downloaded separately.** FFmpeg does not ship them. See `references/denoise-restore-filters.md`.
- **`sr` filter is deprecated** — use `dnn_processing` instead.
- **Super-resolution output width/height are BAKED INTO THE MODEL** — you cannot pass an arbitrary scale factor at runtime; pick the model that matches your target.
- **`arnndn` needs an `.rnnn` model file** — ffmpeg doesn't ship one. Grab `bd.rnnn` or `std.rnnn` from the `xiph/rnnoise` repo.
- **`afftdn nf` is in dB.** -25 is moderate; -20 is aggressive; -40 is gentle.
- **Always verify with A/B spectrograms** (use ffmpeg-playback skill's `showspectrum`).
- **Denoise BEFORE encoding, not after** — post-compression noise is entangled with block artifacts and is mostly irrecoverable.
- **10-bit sources stay 10-bit through the chain.** Add `format=yuv420p10le` or `yuv422p10le` after the denoise; most denoise filters support high bit depths but will downconvert silently if the encoder is 8-bit.

## Examples

### Example 1: Noisy webcam, real-time
Input: 1080p30 webcam capture, uniform luma/chroma noise.
Steps: `hqdn3d=4:3:6:4.5` → H.264 CRF 20. Done in one pass, CPU only.

### Example 2: High-ISO DSLR at night
Input: 4K H.265, heavy chroma noise, some luma grain.
Steps: `nlmeans=s=1.2:p=7:r=15,format=yuv420p10le` → HEVC CRF 20 10-bit.

### Example 3: VHS-rip restoration
Input: 480i interlaced, dot-crawl, tape hiss, color bleed.
Steps: deinterlace (`bwdif`) → `hqdn3d=6:4:8:6` → `removegrain=mode=17` → audio `arnndn=m=bd.rnnn` → H.264 CRF 18.

### Example 4: 2x AI upscale of small archival clip
Input: 480p20 archival interview.
Steps: download ESPCN .pb → `dnn_processing=dnn_backend=tensorflow:model=espcn.pb:input=x:output=y` → H.264 CRF 18.

## Troubleshooting

### Error: `Filter 'dnn_processing' not found`
Cause: ffmpeg built without TF/OpenVINO support.
Solution: rebuild from source with `--enable-libtensorflow` or `--enable-libopenvino`, or install a build that includes it (e.g., BtbN's Windows builds, `jellyfin-ffmpeg`). macOS Homebrew `ffmpeg` does NOT include DNN backends by default.

### Error: `Invalid model file` / `Cannot load model`
Cause: wrong backend vs. file format (TF expects `.pb`, OpenVINO expects `.xml`+`.bin`, NativeDN has its own format).
Solution: set `dnn_backend=` to match the model; verify the file by loading it in the originating framework.

### Result: Video looks plasticky / skin lost texture
Cause: denoise too aggressive; detail thrown out.
Solution: lower sigma / strength; switch `bm3d` → `nlmeans`; or `nlmeans s=1.5` → `s=0.8`; re-add a tiny `noise=alls=3:allf=t` grain.

### Result: Motion smearing / ghost trails
Cause: temporal filter too aggressive (`hqdn3d` last two params, `atadenoise` over-wide).
Solution: reduce temporal terms (`hqdn3d=4:3:2:1.5`) or drop temporal entirely with single-frame filters (`removegrain`, `fftdnoiz`).

### Error: `arnndn: model file required`
Cause: missing `.rnnn` model.
Solution: download `bd.rnnn` or `std.rnnn` from the `xiph/rnnoise` GitHub repo and pass with `arnndn=m=/path/to/bd.rnnn`.

### Result: Audio sounds "underwater" after afftdn
Cause: noise floor too aggressive.
Solution: raise `nf` toward -40 (less aggressive), or switch to `anlmdn` which preserves transients better.
