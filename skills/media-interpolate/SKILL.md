---
name: media-interpolate
description: >
  AI frame interpolation with open-source + commercial-safe models: RIFE (MIT, current best real-time open-source interpolator; ECCV 2022; available as rife-ncnn-vulkan prebuilt CLI on macOS/Linux/Windows), FILM (Apache 2.0, Google 2022, excels on large motion), PractCL (MIT, practical cascaded refinement). Convert 24fps to 60fps, create AI slow-motion, smooth low-framerate footage, anime frame-doubling. Superior to ffmpeg minterpolate (2015 motion-estimation filter) for clean motion without warping or jelly artifacts. Use when the user asks to interpolate frames, do AI slow-motion, boost framerate, smooth 24 to 60fps or 30 to 60fps, create motion-compensated tweens, in-between two images, or when ffmpeg minterpolate produces artifacts.
argument-hint: "[model] [input] [output] [fps|factor]"
---

# Media Interpolate

**Context:** $ARGUMENTS

## Quick start

- **24fps → 60fps:** RIFE `rife-ncnn-vulkan` → Step 2 recipe A.
- **2x slow-motion (keep audio pitch unchanged):** Step 3.
- **Tween between two stills** (generate N frames between A and B): Step 4.
- **Anime frame-doubling:** RIFE with `-m rife-v4.6` → Step 2 recipe A.

## When to use

- User says "interpolate", "smooth framerate", "AI slow-motion", "24 to 60", "frame double", "insert frames".
- Source fps is lower than target display fps and you want motion-compensated tweens (not duplicated frames).
- ffmpeg's `minterpolate=fps=60:mi_mode=mci` looks wobbly, jelly, or artifact-heavy.
- Do NOT use for changing playback speed while keeping framerate constant — that's `ffmpeg-speed-time` (`setpts` + `atempo`).
- Do NOT use for upscaling resolution — that's `media-upscale`.

## Step 1 — Pick a model

| Model    | License    | Best for                                    | Form                          |
|----------|------------|---------------------------------------------|-------------------------------|
| RIFE     | MIT        | General video, anime, real-time, default    | `rife-ncnn-vulkan` prebuilt CLI + PyTorch repo |
| FILM     | Apache-2.0 | Large motion (sports, fast pans), stills    | Python/TensorFlow inference   |
| PractCL  | MIT        | Research, cascaded refinement experiments   | Python/PyTorch                |

**Decision rules:**

1. Default to **RIFE** via `rife-ncnn-vulkan` — Vulkan cross-platform (NVIDIA, AMD, Intel, Apple Silicon via MoltenVK), no Python, fastest install.
2. Scene with large motion (fast pans, sports, explosions, big occlusions) → **FILM**.
3. Tweening two still images with very different content → **FILM** (designed for near-duplicate photos a year apart).
4. Pure anime → **RIFE** models `rife-anime-v4.x` are tuned for it.

**Do NOT use:** DAIN (research-only license). It pre-dates RIFE and is slower; RIFE supersedes it at every benchmark this skill cares about.

## Step 2 — Install the binary / package

`scripts/interp.py install <model>` prints the exact platform-specific command. It does not auto-install.

```bash
# RIFE (ncnn-vulkan prebuilt — recommended)
# Download release zip from: https://github.com/nihui/rife-ncnn-vulkan/releases
# Unzip; add the folder to PATH. Includes models: rife-v2.3 / v2.4 / v3.0 / v3.1 / v4 / v4.6 / anime

# FILM (Python + TensorFlow)
uv pip install tensorflow mediapy
git clone https://github.com/google-research/frame-interpolation

# PractCL
git clone https://github.com/fatheral/PractCL
uv pip install torch opencv-python numpy
```

### Recipe A — RIFE 2x frame-doubling on a video

```bash
# Frame pipeline: extract frames -> RIFE 2x on folder -> remux.
# The script does this end-to-end:
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py video \
  --model rife --in clip_24fps.mp4 --out clip_60fps.mp4 \
  --fps 60 --rife-model rife-v4.6
```

What happens under the hood:

```bash
# (1) extract PNGs at source fps
ffmpeg -i clip_24fps.mp4 -qscale:v 1 -qmin 1 -qmax 1 -vsync 0 in/%08d.png
# (2) RIFE fills the gaps (pick 2x, or directly target -f output-frames)
rife-ncnn-vulkan -i in -o out -m rife-v4.6 -n 0
# -n 0 = auto (2x). For arbitrary target fps, use the script, which computes N.
# (3) remux at target fps + original audio
ffmpeg -framerate 60 -i out/%08d.png -i clip_24fps.mp4 \
       -map 0:v -map 1:a? -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
       -c:a copy -movflags +faststart clip_60fps.mp4
```

### Recipe B — FILM on a video with big motion

```bash
python frame-interpolation/eval/interpolator_cli.py \
  --pattern "frames_in/*.png" \
  --model_path /path/to/film_net/Style/saved_model \
  --times_to_interpolate 1 \
  --output_video
```

`--times_to_interpolate` is log2 of the multiplier: `1` doubles (2x), `2` quadruples (4x), `3` eight-times.

### Recipe C — PractCL

```bash
python PractCL/test.py --input in/ --output out/ --factor 2
```

## Step 3 — Slow-motion (keep audio unmodified)

`interp.py slow-mo` doubles / quadruples / 8x's the number of frames while keeping the output framerate unchanged (so content plays back slower):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py slow-mo \
  --model rife --in action.mp4 --out action_slow2x.mp4 --factor 2
```

Implementation: extract frames at `src_fps`, RIFE by `factor`, remux at `src_fps`. Audio is **dropped** (slowing the video without slowing the audio produces a pitch mismatch). Restore audio afterwards with `ffmpeg-audio-filter` `atempo=1/factor` if desired.

## Step 4 — Tween between two stills

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py images \
  --model rife before.png after.png --out middle.png
# Generate N intermediate frames
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py images \
  --model rife before.png after.png --out-dir sequence/ --count 8
```

Under the hood, RIFE ncnn accepts two-image mode with `-0 first.png -1 second.png -o middle.png`. For N>1 the script repeatedly subdivides (midpoint of midpoint).

## Gotchas

- **AI interpolation vs. `ffmpeg minterpolate`.** `minterpolate=fps=60:mi_mode=mci` is a 2015 block-matching motion estimator. It warps pixels into the gap frame and produces "jelly" on fast motion, edge halos on occlusions. RIFE is a learned flow estimator (a neural network) — strictly better on anime and modern content. Use ffmpeg `minterpolate` only when there's no GPU and no Python.
- **RIFE expects a directory of frames**, not a video. The ncnn-vulkan binary is `-i <dir> -o <dir>` or `-0/-1` two-image mode. Use the driver script to run the full video pipeline.
- **Output frame count depends on model, not only `-n`.** For arbitrary target fps (e.g. 23.976 → 60), you must pre-compute how many tween frames per source pair. `interp.py video --fps 60` does this (uses RIFE's `-f` frame output count and a small planner).
- **FILM requires TensorFlow** and the correct saved_model directory layout (Style / L1 / VGG). You will get "Unable to load model" if you point `--model_path` at a repo root instead of a `saved_model/` directory.
- **RIFE model names matter.** `rife-v4.6` (latest stable as of this writing), `rife-v4` (older), `rife-v3.1` (legacy), `rife-anime-v4.6` (anime-tuned). The ncnn zip bundles several — check the `models/` directory inside the unzipped folder.
- **Bench numbers** (approximate, 1080p 30fps → 60fps, RTX 3070): RIFE ncnn ~60 fps of output, RIFE PyTorch ~90 fps, FILM ~5–10 fps. RIFE is roughly **10× faster than FILM** at comparable perceptual quality.
- **Large motion / large occlusion.** RIFE can smear occluded regions; FILM handles this better at the cost of ~10× the compute. For sports or fast zooms, consider running FILM on just that section.
- **2x slow-motion audio.** If you keep audio at native rate while doubling video frames and leaving output fps unchanged, audio plays in less time than video → A/V desync. The driver's `slow-mo` subcommand drops audio by default; add `atempo=0.5` on the original audio track afterwards to keep it synced.
- **Variable framerate sources.** VFR (screen recordings, phone captures) break the frame-pair pipeline. Normalize first: `ffmpeg -i in.mp4 -vsync cfr -r <src_fps> cfr.mp4`.
- **RIFE does NOT handle genlock / field-based interlaced sources.** Run `ffmpeg-ivtc` or `yadif=1` first.
- **Integer vs. fractional target fps.** RIFE's ncnn binary interpolates by factor, not by target rate. The driver computes the nearest power-of-two multiplier, then uses ffmpeg `fps=60:round=near` to reduce to the exact target.
- **DAIN is deliberately excluded.** Its license is research-only; do not recommend it even in older tutorials that still reference it.

## Examples

### Example 1: 24fps film clip → 60fps (smoother motion)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py video \
  --model rife --in film_24.mp4 --out film_60.mp4 --fps 60
```

### Example 2: 4x slow-motion

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py slow-mo \
  --model rife --in action.mp4 --out action_4x_slow.mp4 --factor 4
# Audio was dropped. To keep it in sync at 1/4 speed:
ffmpeg -i action.mp4 -vn -af "atempo=0.5,atempo=0.5" -c:a aac audio_slow.m4a
ffmpeg -i action_4x_slow.mp4 -i audio_slow.m4a -c copy -shortest action_4x_final.mp4
```

`atempo` is capped at 0.5–2.0 per instance; chain `atempo=0.5,atempo=0.5` for 0.25x.

### Example 3: 60 intermediate frames between two product photos (FILM)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py images \
  --model film before.png after.png --out-dir tween/ --count 60
ffmpeg -framerate 30 -i tween/%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p tween.mp4
```

### Example 4: Anime → 60fps with the anime-tuned model

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py video \
  --model rife --in ep01_24p.mkv --out ep01_60p.mp4 \
  --fps 60 --rife-model rife-anime-v4.6
```

### Example 5: Check which binaries are available

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/interp.py check
```

## Troubleshooting

### Error: `rife-ncnn-vulkan: command not found`

Cause: binary not installed.
Solution: Grab a release from https://github.com/nihui/rife-ncnn-vulkan/releases, unzip, add the folder to PATH. Or `uv run .../interp.py install rife`.

### Error: `failed to load model: rife-v4.6`

Cause: `-m` model name expects a directory named `rife-v4.6` under the binary's `models/` path.
Solution: The ncnn release zip includes several models pre-staged. If you moved the binary without its `models/` folder, re-unzip and keep them together. Or pass `-m /abs/path/to/rife-v4.6`.

### Video has doubled length / slow-motion when you wanted smooth-60

Cause: remuxed the 2x frames at the **source** fps instead of the **target** fps. `ffmpeg -framerate 24 -i out/...` plays 2x frames at 24 fps → 2x duration.
Solution: use `-framerate 60` (or the target you asked for) on the reassembly step. The driver handles this — don't roll your own.

### Output has A/V desync after slow-mo

Cause: the slow-mo path kept the original audio at native rate while the video timeline stretched.
Solution: either drop audio (script default) or run `atempo=1/factor` on audio and remux.

### RIFE looks great on most frames but smears during a fast cut

Cause: the two input frames span a scene change. The model tries to interpolate between unrelated content.
Solution: run `media-scenedetect` to find cuts, then process each scene independently (or skip interpolation across cuts).

### FILM `Unable to load model`

Cause: `--model_path` not pointing at a `saved_model` directory (must contain `saved_model.pb` + `variables/`).
Solution: download from the FILM releases and point at the right style subfolder (e.g. `.../Style/saved_model`).

## Reference docs

- Per-model repo URLs, license, benchmarks, GPU/CPU support → `references/models.md`.
- Full license table → `references/LICENSES.md`.
