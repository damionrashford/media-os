---
name: media-depth
description: >
  Monocular depth estimation with open-source + commercial-safe models: Depth-Anything v2 (Apache 2.0, TikTok/ByteDance 2024, current SOTA small/base/large) via HuggingFace transformers, MiDaS v3.1 (MIT, Intel ISL classic with DPT/BEiT/Swin backbones). Extract depth maps from a single image or video, enable 2.5D parallax / Ken Burns effects, drive Blender/Unreal Z-depth passes, replace LiDAR capture, convert 2D → stereo 3D via depth-driven parallax. Use when the user asks to estimate depth, compute a depth map, run Depth Anything, run MiDaS, get a disparity map, animate a 2.5D parallax shot from a still, build a stereo pair from a 2D photo, extract Z-depth for compositing, drive a VFX pipeline with monocular depth, convert 2D video to side-by-side 3D, or produce a depth video for the Looking Glass / Blender camera tracker.
argument-hint: "[input] [output]"
---

# Media Depth

**Context:** $ARGUMENTS

Monocular depth estimation — estimate a per-pixel depth map from a single RGB image or video, no stereo rig or LiDAR required. Two actively maintained open-source model families with commercial-safe licenses: **Depth-Anything v2** (Apache 2.0, current SOTA, 2024) and **MiDaS v3.1** (MIT, Intel ISL, long-standing baseline).

## Quick start

- **Depth map from a photo (PNG):** → Step 3 (`depth.py image --model depthanything-v2`)
- **Depth sequence from a video:** → Step 4 (`depth.py video`)
- **2D photo → side-by-side stereo 3D pair:** → Step 5 (`depth.py stereo --baseline 6.5`)
- **Animate a 2.5D parallax / Ken Burns shot from a still:** → Step 6 (`depth.py parallax --frames 30`)
- **Pre-download model weights:** → Step 2 (`depth.py install <model>`)

## When to use

- Need a **Z-depth pass** to hand to Blender, Nuke, Fusion, After Effects, or Unreal (compositing, DoF, fog).
- Converting flat 2D footage to **side-by-side / over-under stereo 3D** without reshooting.
- Producing **parallax / 2.5D / "Ken Burns" motion** from stills for social reels or lyric videos.
- Building a **pseudo-LiDAR point cloud** for photogrammetry, volumetric capture prep, or robotics dev.
- Any workflow where "metric depth in meters" is *not* required — both default models here return **relative / inverse depth** normalized 0–1. For metric depth, read `references/models.md` on Depth-Anything v2 metric fine-tunes.
- Not for real-time (<10 ms) embedded use — pick MiDaS-small for the fastest CPU path but even that is ~50 ms on a modern laptop at 384 px.

## Step 1 — Install PyTorch + transformers

Depth-Anything v2 is distributed via HuggingFace `transformers` using the `pipeline("depth-estimation", ...)` API — no custom model code required. MiDaS also works through `transformers` (using the `DPTForDepthEstimation` class).

PEP 723 header in `scripts/depth.py` declares the full dependency set. Running via `uv run` handles an ephemeral venv. Manual install:

```bash
pip install torch transformers opencv-python numpy pillow
```

On Apple Silicon, PyTorch picks MPS automatically when you set `device="mps"`. On NVIDIA, `device="cuda"`. The helper auto-selects.

Verify the runtime:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py install depthanything-v2 --size small
```

Downloads the `depth-anything/Depth-Anything-V2-Small-hf` weights (~100 MB) into `~/.cache/huggingface/hub/`.

## Step 2 — Pick a model

| Model                       | License       | Variants                          | Relative/Metric | Notes                                            |
|-----------------------------|---------------|-----------------------------------|-----------------|--------------------------------------------------|
| `depthanything-v2` (default)| Apache 2.0    | `small` / `base` / `large`        | Relative (inverse depth) | SOTA 2024, crisper edges than v1; metric fine-tunes exist for indoor/outdoor |
| `midas`                     | MIT           | `dpt-swinv2-tiny-256` / `dpt-beit-large-512` | Relative | Intel ISL v3.1, older, still robust             |

Pick by size vs accuracy:

- `depthanything-v2 --size small` — ~25 M params, ~40 fps 1080p on a 3090
- `depthanything-v2 --size base`  — ~97 M params, ~20 fps
- `depthanything-v2 --size large` — ~335 M params, ~8 fps, sharpest edges

Full per-model speed, VRAM, and license matrix in `references/models.md`. Read it when picking a model for batch video or embedded deployment.

## Step 3 — Depth map from a single image

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py image \
  --model depthanything-v2 --size small \
  --in photo.jpg --out depth.png
```

Outputs a 16-bit single-channel PNG where `0` = far, `65535` = near (the HuggingFace pipeline yields "inverse depth", higher = closer). Also writes `depth_preview.png` — a turbo-colormap 8-bit visualization for human inspection.

Useful flags:

- `--out-format npy` — raw `float32` numpy `.npy` (best fidelity for VFX tools)
- `--out-format exr` — 32-bit EXR (requires `opencv-python` built with OpenEXR; otherwise install `pip install OpenEXR imath` or use the `.npy` path and convert with `vfx-oiio` / `ffmpeg-ocio-colorpro`)
- `--invert` — flip so that `0` = near, `65535` = far (Blender / most DCCs expect this)

## Step 4 — Per-frame depth for video

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py video \
  --model depthanything-v2 --size small \
  --in input.mp4 --out depth.mp4
```

Writes a grayscale H.264 MP4 at the source fps where each pixel encodes depth (8-bit). For compositing fidelity prefer:

```bash
--out-format png-seq --out depth_frames/   # 16-bit PNG sequence, frame_%06d.png
--out-format exr-seq --out depth_exr/      # 32-bit EXR sequence (best for Nuke)
```

Gotcha: per-frame monocular depth is **temporally unstable** — the depth of a static object can flicker frame-to-frame. Use `--smooth temporal` for a light 3-tap EMA across frames, or hand the output to `ffmpeg-denoise-restore` (`hqdn3d` on the grayscale depth track) before consuming it downstream.

## Step 5 — 2D → stereo 3D (depth-driven parallax)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py stereo \
  --model depthanything-v2 --size base \
  --in photo.jpg \
  --out-left left.png --out-right right.png \
  --baseline 6.5
```

`--baseline` is the interpupillary-distance shift in **pixels** (or millimeters at 96 dpi — it's an opinionated single scalar). Typical values:

- `3.0` — subtle parallax for phone viewing
- `6.5` — the physical human IPD in mm; gives a natural "window" look
- `12.0` — exaggerated for VR / anaglyph

The occlusion-aware parallax math (forward-warp with depth-sorted Z-buffer, then inpaint revealed background) is documented in `references/parallax-math.md` — read it when you need to tune the quality / hole-filling trade-off.

Pack side-by-side for a 3D TV / Meta Quest:

```bash
ffmpeg -i left.png -i right.png -filter_complex hstack sbs.png
```

## Step 6 — Animate a 2.5D parallax shot (Ken Burns style)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py parallax \
  --image photo.jpg --depth depth.png \
  --out parallax.mp4 \
  --frames 120 --fps 30 \
  --motion orbit --amplitude 40
```

`--motion` presets:

- `orbit` — smooth circular camera orbit (best default)
- `zoom` — dolly in toward the nearest plane
- `pan-left` / `pan-right` — horizontal slide with depth-correct parallax
- `ken-burns` — slow zoom + slight pan

`--amplitude` is the max pixel shift of the nearest foreground. Values 20–80 work well for 1080p stills. Hole-fill is done via OpenCV `INPAINT_TELEA` on the revealed background — the reference doc covers why TELEA beats NS for this specific use case.

If you have both the `--image` and `--depth` already, parallax is a pure post-process (no model inference). Chain it after Step 3.

## Available scripts

- **`scripts/depth.py`** — subcommands: `image`, `video`, `stereo`, `parallax`, `install`. Each supports `--dry-run`, `--verbose`, `--device {auto,cpu,cuda,mps}`.

## Reference docs

- Read [`references/models.md`](references/models.md) when picking between Depth-Anything v2 variants, switching to MiDaS, or needing metric (in-meters) depth rather than relative.
- Read [`references/parallax-math.md`](references/parallax-math.md) when tuning the occlusion-aware warp, debugging hole-fill artifacts, or implementing a custom stereo baseline model.
- Read [`references/LICENSES.md`](references/LICENSES.md) before shipping commercial output — all models listed here are Apache 2.0 or MIT, but the commercial-safety boundary for **derivative depth maps** vs **the model weights themselves** has nuances worth knowing.

## Gotchas

- **Relative vs metric depth.** Both default models return **inverse relative depth**, normalized per image. Values are **not** in meters. Comparing two frames of the same scene means their absolute depth scale drifts. For metric-in-meters depth you need Depth-Anything v2's *metric fine-tunes* (`Depth-Anything-V2-Metric-Indoor-*` / `-Outdoor-*`), which are Apache 2.0 but trained on NC-licensed datasets (Hypersim, KITTI) — the **output** is commercial-safe; the **training data license** does not transfer. See `references/LICENSES.md`.
- **Inverse-depth convention.** HuggingFace pipelines return "depth" where **higher = closer** (inverse depth). Blender / Nuke / most DCCs expect **higher = farther**. Pass `--invert` in that case.
- **16-bit PNG vs 8-bit video.** MP4 video output is 8-bit — good enough for parallax, too coarse for compositing. Use `--out-format png-seq` or `exr-seq` for any downstream Z-depth workflow.
- **Temporal flicker on video.** Per-frame monocular depth is not temporally stable. Always smooth (`--smooth temporal`) or denoise the depth track before using it as a camera-tracking signal.
- **Input resolution matters.** Both models internally resize to their native input size (518×518 for Depth-Anything v2, 384 or 512 for MiDaS). Output is upscaled back to source resolution — don't feed 8K and expect 8K-quality edges; the model saw a 518×518 version.
- **MPS on Apple Silicon occasionally drops precision** for very large images. If output looks noisy, force `--device cpu` (slower but accurate) or downscale first.
- **`--baseline` for stereo is pixels, not cm.** Despite the hint "6.5 mm IPD," the scalar is in image pixels at the source resolution. Scale proportionally if you resize.
- **Skill-specific hole-filling.** `INPAINT_TELEA` on the revealed background beats NS for single-image parallax because it preserves edge continuity where the foreground pulled away — see `references/parallax-math.md`.
- **No prompts, no interactive choices.** Scripts are non-interactive. Pass all parameters on the command line.

## Examples

### Example 1 — Depth PNG from a JPEG

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py image \
  --model depthanything-v2 --size small \
  --in portrait.jpg --out portrait_depth.png --invert
```

Produces a 16-bit grayscale PNG where near objects are dark, far is bright (Blender convention).

### Example 2 — EXR depth sequence for Nuke

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py video \
  --model depthanything-v2 --size base \
  --in plate.mov --out depth_exr/ --out-format exr-seq \
  --smooth temporal
```

Writes `depth_exr/frame_000001.exr …` — 32-bit float Z-depth per frame with light temporal smoothing.

### Example 3 — Side-by-side stereo from a landscape photo

```bash
# 1. depth
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py image \
  --model depthanything-v2 --size base \
  --in lake.jpg --out lake_depth.png

# 2. stereo pair
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py stereo \
  --in lake.jpg --depth lake_depth.png \
  --out-left L.png --out-right R.png --baseline 8.0

# 3. pack as SBS
ffmpeg -y -i L.png -i R.png -filter_complex hstack lake_sbs.png
```

### Example 4 — 2.5D parallax reel from a single still

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py image \
  --model depthanything-v2 --size small \
  --in hero.jpg --out hero_depth.png

uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py parallax \
  --image hero.jpg --depth hero_depth.png \
  --out hero_parallax.mp4 \
  --motion orbit --frames 150 --fps 30 --amplitude 35
```

### Example 5 — Batch depth on a folder (GNU parallel)

Hand off to `media-batch`:

```bash
ls in/*.jpg | parallel --jobs 4 \
  uv run ${CLAUDE_SKILL_DIR}/scripts/depth.py image \
    --model depthanything-v2 --size small \
    --in {} --out out/{/.}_depth.png
```

## Troubleshooting

### `OSError: Can't load tokenizer/image processor for 'depth-anything/Depth-Anything-V2-Small-hf'`

Cause: No network on first run, or HF Hub outage.
Solution: Pre-download with `depth.py install depthanything-v2 --size small` when the network is up; weights cache to `~/.cache/huggingface/hub/` and work offline after.

### Depth looks inverted (near=bright, I expected near=dark)

Cause: HuggingFace convention is inverse-depth (near=bright); most DCCs want the opposite.
Solution: Re-run with `--invert`. Or post-process: `python -c "import cv2,numpy as np; d=cv2.imread('d.png',-1); cv2.imwrite('d_inv.png', 65535 - d)"`.

### Video output flickers frame-to-frame

Cause: Monocular per-frame depth is temporally unstable.
Solution: Add `--smooth temporal`. For stronger stability, hand off the depth video to `ffmpeg-denoise-restore` with `hqdn3d=4:3:6:4.5`, or upgrade to a video-aware model (none of those are Apache/MIT as of April 2026 — track updates in `references/models.md`).

### Stereo pair has obvious tearing / black slivers

Cause: Parallax baseline too large for the depth range; hole-fill can't invent enough background.
Solution: Reduce `--baseline` (try 3.0–5.0), or supply a higher-quality depth map (`--size large`).

### `RuntimeError: MPS backend out of memory`

Cause: Apple Silicon MPS allocator fragments on large images.
Solution: `--device cpu` (slower), or downscale the input (`ffmpeg -i in.jpg -vf scale=1280:-1 small.jpg`) before running depth.

### `ffmpeg` not found when writing video output

Cause: The video subcommand shells out to ffmpeg for encoding.
Solution: `brew install ffmpeg` (macOS) or your distro equivalent — the `ffmpeg-transcode` skill has install details.
