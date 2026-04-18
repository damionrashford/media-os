---
name: ffmpeg-stabilize
description: >
  Video stabilization with ffmpeg: 2-pass vidstabdetect + vidstabtransform (vid.stab library), single-pass deshake, deshake_opencl, and rolling-shutter correction. Use when the user asks to stabilize shaky footage, smooth out handheld video, fix camera shake, de-wobble a GoPro clip, fix rolling shutter, apply optical stabilization in post, or run the vid.stab detect/transform pipeline.
argument-hint: "[input]"
---

# Ffmpeg Stabilize

**Context:** $ARGUMENTS

## Quick start

- **Stabilize shaky handheld (best quality):** 2-pass vid.stab → Steps 1–4
- **Quick fix, don't care about quality:** single-pass `deshake` → Examples
- **GPU single-pass:** `deshake_opencl` → Examples
- **Locked-off tripod look from handheld:** `tripod=N` → `references/vidstab.md`

## When to use

- Handheld phone/camera footage with visible shake
- GoPro / action-cam clips (mounted but still jittery)
- Drone clips with buffeting wobble
- Making interview-style footage look "locked off" without an actual tripod
- Pre-stabilizing before VFX, speed ramps, or any grading that amplifies jitter

## Step 1 — Check build supports vid.stab

```bash
ffmpeg -filters 2>/dev/null | grep -i vidstab
```

Must show both `vidstabdetect` and `vidstabtransform`. If missing, either install a Homebrew build (`brew install ffmpeg` — includes `--enable-libvidstab` since late 2019), or fall back to `deshake` (builtin, always available).

`scripts/stabilize.py check-build` does this check programmatically.

## Step 2 — Pass 1: detect motion → transforms.trf

```bash
ffmpeg -i in.mp4 \
  -vf vidstabdetect=shakiness=5:accuracy=15:result=transforms.trf \
  -f null -
```

- Produces `transforms.trf` (plain-text, one line per frame with dx/dy/rot/zoom).
- `-f null -` discards the video output — we only want the sidecar file.
- `shakiness`: 1 (mild) to 10 (extreme), default 5.
- `accuracy`: 1 (fast) to 15 (max), default 15. Keep at 15 unless iterating.

## Step 3 — Pass 2: transform + sharpen + optional zoom

```bash
ffmpeg -i in.mp4 \
  -vf "vidstabtransform=input=transforms.trf:zoom=0:smoothing=30:crop=black,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -preset slow \
  -c:a copy out.mp4
```

- `smoothing=30` ≈ 1 second at 30 fps — good default.
- `crop=black` leaves black borders where frame was pushed; `crop=keep` repeats prior edge pixels.
- `unsharp=5:5:0.8:3:3:0.4` restores sharpness lost to bilinear interpolation.
- `-c:a copy` passes audio through; re-encode is required for video.

### Hide black borders

Option A — fixed zoom (percent):
```
vidstabtransform=input=transforms.trf:zoom=5:smoothing=30:crop=black
```
Option B — automatic optimal zoom (recommended for heavy shake):
```
vidstabtransform=input=transforms.trf:optzoom=1:smoothing=30:crop=black
```
Option C — adaptive optzoom with zoom speed cap:
```
vidstabtransform=input=transforms.trf:optzoom=2:zoomspeed=0.25:smoothing=30:crop=black
```

## Step 4 — Verify

```bash
ffplay out.mp4                     # visual check
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate out.mp4
```

For A/B compare:
```bash
ffmpeg -i in.mp4 -i out.mp4 -filter_complex hstack -c:v libx264 -crf 20 compare.mp4
```

## Available scripts

- **`scripts/stabilize.py stabilize`** — runs both passes end-to-end, manages `transforms.trf` in a tempdir.
- **`scripts/stabilize.py deshake`** — single-pass fallback.
- **`scripts/stabilize.py check-build`** — reports vid.stab availability.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/stabilize.py stabilize --input in.mp4 --output out.mp4 --sharpen --zoom auto
uv run ${CLAUDE_SKILL_DIR}/scripts/stabilize.py deshake --input in.mp4 --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/stabilize.py check-build
```

## Reference docs

- Read [`references/vidstab.md`](references/vidstab.md) for full option tables, tripod mode, recipe gallery, and the build-from-source note.

## Gotchas

- vid.stab is NOT in every ffmpeg build — must be compiled with `--enable-libvidstab`. Homebrew's `ffmpeg` has included it for years; static Zeranoe-style builds sometimes don't. **Always verify with Step 1 first.**
- 2-pass vid.stab is ALWAYS better than `deshake` for genuinely shaky content. `deshake` is a last resort.
- `transforms.trf` is plain text — safe to inspect, diff, or back up.
- `shakiness` is 1–10 (5 typical). `accuracy` is 1–15 (15 = slowest / best).
- `smoothing` is in **frames**, not seconds. 30 ≈ 1s at 30 fps. Too high → jelly/floaty feel. Too low → residual shake bleeds through.
- `zoom=N` is percent. Use `optzoom=1` for automatic; `optzoom=2:zoomspeed=...` for gentler adaptive.
- `crop=black` produces borders that **wiggle** at clip edges. Compensate with `zoom` / `optzoom`, or post-crop.
- Stream copy (`-c:v copy`) is **not possible** — the filter requires decoded frames. Re-encode is mandatory.
- `unsharp` **after** the transform, not before. Pre-sharpening amplifies noise into the motion estimator.
- Do NOT combine `vidstabtransform` with `deshake` — pick one.
- `deshake_opencl` requires `-init_hw_device opencl` before the `-i`. Missing it → filter not found.
- Pass 1 with `-f null -` writes NOTHING to stdout/stderr (except progress). The `transforms.trf` file IS being written — don't assume it failed.
- Pass 1 with `-vcodec copy` **does not work** — vidstabdetect needs decoded frames.
- Long-clip timebase drift: add `-fflags +genpts` on the input side of pass 2.
- vid.stab is 2D (x+y) only. No axis-lock option; you cannot stabilize only vertical.
- Rolling-shutter + stabilization: stabilization **exposes** wobble. ffmpeg has no true rolling-shutter filter — pre-correct in GoPro Player / DaVinci / Gyroflow before running ffmpeg stabilization.

## Examples

### Example 1 — Standard handheld phone clip

```bash
# Pass 1
ffmpeg -i phone.mp4 -vf vidstabdetect=shakiness=5:accuracy=15:result=phone.trf -f null -
# Pass 2
ffmpeg -i phone.mp4 \
  -vf "vidstabtransform=input=phone.trf:smoothing=30:optzoom=1:crop=black,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -preset slow -c:a copy phone_stable.mp4
```

### Example 2 — Heavy shake (running, mountain biking)

```bash
ffmpeg -i wild.mp4 -vf vidstabdetect=shakiness=10:accuracy=15:result=wild.trf -f null -
ffmpeg -i wild.mp4 \
  -vf "vidstabtransform=input=wild.trf:smoothing=60:optzoom=2:zoomspeed=0.3:crop=black,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -preset slow -c:a copy wild_stable.mp4
```

### Example 3 — Fake tripod lock on frame 0

```bash
ffmpeg -i talk.mp4 -vf vidstabdetect=shakiness=3:result=talk.trf -f null -
ffmpeg -i talk.mp4 \
  -vf "vidstabtransform=input=talk.trf:tripod=1:smoothing=0:crop=keep,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -c:a copy talk_locked.mp4
```

### Example 4 — Quick single-pass deshake

```bash
ffmpeg -i in.mp4 -vf deshake -c:v libx264 -crf 18 out.mp4
```

### Example 5 — GPU deshake_opencl

```bash
ffmpeg -init_hw_device opencl=ocl:0.0 -filter_hw_device ocl \
  -i in.mp4 \
  -vf "format=nv12,hwupload,deshake_opencl,hwdownload,format=yuv420p" \
  -c:v libx264 -crf 18 out.mp4
```

## Troubleshooting

### Error: `No such filter: 'vidstabdetect'`

Cause: ffmpeg built without `--enable-libvidstab`.
Solution: `brew install ffmpeg` (macOS) or rebuild; use `deshake` as a fallback.

### Error: `Unable to open file 'transforms.trf' for reading`

Cause: pass 2 run from a different cwd than pass 1, or pass 1 silently failed.
Solution: pass absolute paths to `result=` and `input=`; verify the file exists and is non-empty.

### Output has thick black borders wobbling at edges

Cause: `crop=black` + `zoom=0`.
Solution: add `optzoom=1` or `zoom=5`; or post-crop with `crop=iw*0.95:ih*0.95`.

### Output looks "floaty" / jelly-like

Cause: `smoothing` too high.
Solution: drop to `smoothing=15` or `smoothing=10`.

### Residual shake still visible

Cause: `smoothing` too low, or `shakiness` in pass 1 underestimated the motion.
Solution: rerun pass 1 with `shakiness=8–10`, rerun pass 2 with `smoothing=60`.

### Stabilized clip has a "rolling" wobble

Cause: rolling shutter skew, not camera shake. vid.stab can't fix the skew itself.
Solution: pre-process with Gyroflow / GoPro Player to correct rolling shutter, then stabilize.

### Pass 1 "hangs" with no output

Not hung — `-f null -` suppresses the output stream. Watch the `frame=` progress line on stderr; `transforms.trf` is being written.
