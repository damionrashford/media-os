---
name: ffmpeg-frames-images
description: >
  Extract frames, make thumbnails, build sprite/contact sheets, import/export image sequences, and create high-quality GIFs (palettegen+paletteuse) with ffmpeg. Use when the user asks to grab a thumbnail, extract frames, take a screenshot at a timestamp, create a contact sheet or sprite sheet, convert video to images/PNGs/JPGs, convert an image sequence to video, or make a GIF from a video.
argument-hint: "[action] [input]"
---

# Ffmpeg Frames Images

**Context:** $ARGUMENTS

Frame extraction and image I/O with ffmpeg: single stills, periodic frame dumps, contact sheets, sprite sheets for scrubbers, high-quality GIFs, and building video back from an image sequence.

## Quick start

- **Single screenshot at a timestamp** → Step 1 (screenshot) + Step 2
- **Dump N frames per second to PNG/JPG** → Step 1 (sequence) + Step 2
- **Contact sheet / thumbnail grid** → Step 1 (sheet) + Step 2
- **Sprite sheet for HLS scrubber** → Step 1 (sprite) + Step 2
- **High-quality GIF from video** → Step 1 (gif) + Step 2 (two-pass)
- **Build video from PNG/JPG sequence** → Step 1 (images-to-video) + Step 2

## When to use

- Grab a poster/thumbnail frame at a specific time.
- Produce preview grids (contact sheet) for a long video.
- Generate scrubber sprites for a web player (HLS/DASH image tracks).
- Export frames for ML, computer vision, or VFX pipelines.
- Make a looping GIF for docs/social without visible banding.
- Re-encode a rendered image sequence (e.g. Blender/Nuke output) into MP4.

## Step 1 — Pick your output

Choose exactly one shape; each has its own command pattern.

1. **`screenshot`** — one still image at a timestamp.
2. **`sequence`** — many images at regular intervals (`fps=1` = 1/sec, `fps=1/10` = every 10s).
3. **`sheet`** — one image that is a grid (`tile=MxN`) of stamps across the video.
4. **`sprite`** — same as sheet but sized for a web player's scrubber.
5. **`gif`** — animated GIF (two-command palette workflow).
6. **`images-to-video`** — reverse direction: image sequence → MP4.
7. **`thumbnail-smart`** — let ffmpeg pick a "representative" frame.
8. **`keyframes-only`** — export only frames marked as keyframes.

## Step 2 — Build the command

### 2a. Single screenshot at 1:30
```bash
# Input-side seek is FAST (keyframe-snapped, may be a few ms off).
ffmpeg -ss 00:01:30 -i in.mp4 -vframes 1 -q:v 2 out.jpg

# Frame-accurate (SLOW, decodes from 0):
ffmpeg -i in.mp4 -ss 00:01:30 -vframes 1 -q:v 2 out.jpg

# Lossless PNG instead of JPG:
ffmpeg -ss 90 -i in.mp4 -vframes 1 -c:v png out.png
```

### 2b. One frame per second (or every N seconds)
```bash
# 1 frame / second:
ffmpeg -i in.mp4 -vf fps=1 frame_%04d.jpg

# 1 frame / 10 seconds:
ffmpeg -i in.mp4 -vf fps=1/10 frame_%04d.jpg

# Higher JPG quality (2 = best, 31 = worst):
ffmpeg -i in.mp4 -vf fps=1 -q:v 2 frame_%04d.jpg
```

### 2c. Contact sheet 4x4 at 5-second intervals
```bash
ffmpeg -i in.mp4 \
  -vf "fps=1/5,scale=320:-1,tile=4x4" \
  -frames:v 1 sheet.jpg
```

### 2d. Sprite sheet for HLS scrubber (10x10 grid, 10s interval, 160px wide)
```bash
ffmpeg -i in.mp4 \
  -vf "fps=1/10,scale=160:-1,tile=10x10" \
  -frames:v 1 sprites.jpg
```

Each sprite cell is 160 x (160/aspect). For a 16:9 video that's 160x90. With 100 cells and a 10s interval you cover 1000 seconds of runtime per sheet. See [`references/recipes.md`](references/recipes.md) for HLS `EXT-X-IMAGE-STREAM-INF` math.

### 2e. Smart thumbnail (auto-pick representative frame)
```bash
ffmpeg -i in.mp4 -vf "thumbnail=100,scale=640:-1" -frames:v 1 thumb.jpg
```
`thumbnail=100` scans 100 consecutive frames and picks the most "typical" one (lowest histogram distance to the group average). Good for avoiding black/blurred frames.

### 2f. Keyframes only
```bash
ffmpeg -i in.mp4 -vf "select='eq(pict_type,I)'" -vsync vfr key_%04d.jpg
```

### 2g. High-quality GIF (TWO commands — palettegen, then paletteuse)
```bash
# 1) Generate an optimized palette
ffmpeg -i in.mp4 \
  -vf "fps=15,scale=480:-1:flags=lanczos,palettegen=max_colors=256" \
  -y palette.png

# 2) Apply the palette with dithering
ffmpeg -i in.mp4 -i palette.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  -y out.gif
```
There is no reliable one-shot GIF command that gives this quality. The two-pass `palettegen` → `paletteuse` flow is the standard.

### 2h. Video from image sequence
```bash
# Note: -framerate goes BEFORE -i (it's an input option for image2).
ffmpeg -framerate 30 -i img_%04d.png \
  -c:v libx264 -pix_fmt yuv420p out.mp4

# Glob instead of numeric pattern:
ffmpeg -framerate 30 -pattern_type glob -i 'img_*.png' \
  -c:v libx264 -pix_fmt yuv420p out.mp4

# Start numbering at a non-zero index:
ffmpeg -framerate 24 -start_number 100 -i img_%04d.png out.mp4
```

## Step 3 — Verify frame count

Before shipping, confirm you got what you expected.

```bash
# How many images landed on disk:
ls frame_*.jpg | wc -l

# Expected count for fps=1/N on a duration T:
#   floor(T / N) + 1
# (ffmpeg rounds to the nearest frame; off-by-one is normal.)

# Re-check a produced sheet's dimensions:
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -of csv=p=0 sheet.jpg
```

## Available scripts

- **`scripts/frames.py`** — wrapper around all of the above. Subcommands:
  `screenshot`, `every`, `sheet`, `sprite`, `gif`, `images-to-video`.
  Supports `--dry-run` and `--verbose`. Stdlib-only Python; no prompts.

## Workflow

```bash
# Screenshot at 1m30s:
uv run ${CLAUDE_SKILL_DIR}/scripts/frames.py screenshot \
  --input in.mp4 --time 00:01:30 --output thumb.jpg

# 4x4 contact sheet at 5s intervals:
uv run ${CLAUDE_SKILL_DIR}/scripts/frames.py sheet \
  --input in.mp4 --cols 4 --rows 4 --interval 5 --width 320 --output sheet.jpg

# Two-pass GIF:
uv run ${CLAUDE_SKILL_DIR}/scripts/frames.py gif \
  --input in.mp4 --fps 15 --width 480 --output out.gif

# Rebuild video from PNGs:
uv run ${CLAUDE_SKILL_DIR}/scripts/frames.py images-to-video \
  --pattern 'img_%04d.png' --fps 30 --output out.mp4
```

## Reference docs

Read [`references/recipes.md`](references/recipes.md) when:
- You need more than 8 recipes (there are 30+ in there).
- You need the JPEG quality scale, PNG compression flags, or image2 demuxer options (`pattern_type`, `start_number`, `loop`, `framerate`).
- You're tuning GIF size vs quality (dither tables, fps trade-offs).
- You're computing sprite sheet geometry for `EXT-X-IMAGE-STREAM-INF` playlists.

## Gotchas

- **`-ss` before `-i` is FAST but keyframe-snapped** — the chosen time snaps to the nearest preceding keyframe. Off by up to the GOP length (often ~2s). Great for thumbnails.
- **`-ss` after `-i` is FRAME-ACCURATE but slow** — ffmpeg decodes from frame 0 to the target. Use only when exact frame matters.
- **`-q:v 2` is best-JPEG-quality.** Scale is 2–31, LOWER is better. `2` is visually lossless-ish, `5` is web-quality, `31` is unusable.
- **`-frames:v 1` vs `-vframes 1`** — both work. Prefer `-frames:v` (stream-specific, modern form).
- **`image2` numeric pattern zero-padding must match the `%0Nd` width.** `img_%04d.png` means files must be `img_0001.png`, not `img_1.png`, or you'll get "could not find codec parameters" errors.
- **Glob only works if you add `-pattern_type glob`.** Otherwise ffmpeg treats `img_*.png` as a literal filename.
- **GIF quality REQUIRES the two-pass palette workflow.** There is no acceptable single-command alternative; a naked `ffmpeg -i in.mp4 out.gif` produces banded, washed-out garbage.
- **`paletteuse=dither=bayer:bayer_scale=5`** is the quality/size sweet spot. `dither=none` bands heavily; `dither=floyd_steinberg` is prettiest but noticeably larger.
- **`-framerate` vs `-r`.** `-framerate` is an INPUT option for the image2 demuxer (rate at which images are READ). `-r` is an OUTPUT option (rate STAMPED on the output). For `image sequence → video`, set `-framerate BEFORE -i`.
- **JPG kills alpha.** If the source has transparency (captures, overlays), use PNG or WebP.
- **`tile` must match what you feed it.** A 4x4 tile expects exactly 16 frames — use `-frames:v 1` to stop after the first tiled output and trim the `fps` to produce at least 16 frames' worth.
- **`thumbnail=N` needs N frames in the window.** If the source is shorter than N frames, the filter still works but samples what it has. Default `N` is 100.
- **On macOS, `ffmpeg` may not be on PATH in non-interactive shells.** If your script fails with `command not found`, invoke with an absolute path (e.g. `/opt/homebrew/bin/ffmpeg`).

## Examples

### Example 1: YouTube-style poster frame at 1:30
```bash
ffmpeg -ss 00:01:30 -i lecture.mp4 -vframes 1 -q:v 2 -vf "scale=1280:-1" poster.jpg
```
Result: 1280-wide JPEG, keyframe-snapped (fast).

### Example 2: Scrubber sprite sheet for a 1h video
For a 3600s video, sampling every 10s = 360 thumbs. A 19x19 grid (361 cells) covers it:
```bash
ffmpeg -i movie.mp4 \
  -vf "fps=1/10,scale=160:-1,tile=19x19" \
  -frames:v 1 sprites.jpg
```
Result: one JPG, ~3040x1710 pixels at 16:9, ready to slice on the client.

### Example 3: Animated GIF of a 10s clip
```bash
# 1) palette
ffmpeg -ss 10 -t 10 -i clip.mp4 \
  -vf "fps=15,scale=480:-1:flags=lanczos,palettegen" -y palette.png
# 2) use palette
ffmpeg -ss 10 -t 10 -i clip.mp4 -i palette.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  -y demo.gif
```
Result: ~2–3 MB GIF, no visible banding.

### Example 4: Blender render → MP4
Blender wrote `render_0001.png` … `render_0240.png` at 24 fps:
```bash
ffmpeg -framerate 24 -i render_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 18 render.mp4
```
Result: 10-second MP4, high quality, broadly compatible.

## Troubleshooting

### Error: `Could not find codec parameters for stream 0 (Video: none): unknown codec`
Cause: image pattern's zero-padding doesn't match the actual filenames.
Solution: rename files, or change `%04d` to match the real padding, or switch to `-pattern_type glob -i 'img_*.png'`.

### Error: `Output file #0 does not contain any stream`
Cause: `-ss` placed after `-i` with an offset past the end of the video, OR `thumbnail`/`select` filtered everything out.
Solution: verify the timestamp with `ffprobe -show_entries format=duration`; for select filters, loosen the predicate or pair with `-vsync vfr`.

### Error: GIF looks washed out / banded / has dithering noise halo
Cause: skipped the palette step, or used `dither=none`.
Solution: run the two-pass `palettegen` + `paletteuse=dither=bayer:bayer_scale=5` workflow in section 2g.

### Error: Image sequence imports at wrong speed / too fast / too slow
Cause: you used `-r` (output rate) when you needed `-framerate` (input rate). ffmpeg defaults to 25 fps on the image2 demuxer if neither is set.
Solution: put `-framerate N` BEFORE `-i img_%04d.png`.

### Error: `tile` filter complains about missing frames / produces a partial grid
Cause: `fps` didn't produce enough frames to fill `MxN`.
Solution: either lower the interval (more frames), reduce the grid (`2x2`), or accept a partial tile.

### Error: JPG is huge / low-quality
Cause: missing `-q:v`.
Solution: add `-q:v 2` (best) through `-q:v 7` (web). Remember: lower = better.
