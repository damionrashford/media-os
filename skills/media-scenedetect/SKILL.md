---
name: media-scenedetect
description: >
  Reliable scene-change detection with PySceneDetect (scenedetect CLI): content-aware detection (ContentDetector), threshold detection (ThresholdDetector), adaptive detection (AdaptiveDetector), scene list to CSV/JSON, split videos at scene cuts, save scene thumbnails, HSV/edge-based metrics. Use when the user asks to split a video at scene changes, build a chapter list from scene cuts, generate thumbnails per scene, detect shot boundaries reliably, or do content-aware auto-chapter markers (better than ffmpeg scdet).
argument-hint: "[input]"
---

# Media Scenedetect

**Context:** $ARGUMENTS

PySceneDetect is the go-to tool for reliable scene-change detection. It is superior to ffmpeg's built-in `scdet` filter, especially on anime, stylized, and low-contrast content. The `scenedetect` CLI chains a *detector* (`detect-content`, `detect-adaptive`, `detect-threshold`) with one or more *commands* (`list-scenes`, `save-images`, `split-video`, `export-html`) in a single invocation.

## Quick start

- **Detect scenes + dump a CSV:** → Step 3 (`scenedetect -i in.mp4 detect-content list-scenes`)
- **Split video at every cut:** → Step 4a (`split-video -m` for stream-copy via mkvmerge)
- **Generate thumbnails per scene:** → Step 4b (`save-images -n 3 -o thumbs`)
- **Auto-chapter a long file:** → Step 4c (use helper script `chapters` subcommand)

## When to use

- You want reliable shot boundaries for cut sheets, editorial, or auto-chapters.
- ffmpeg `scdet` is returning noisy / missed cuts on stylized, anime, or dark content.
- You need thumbnails per scene for a dashboard, chapter art, or video summary.
- You're building a pipeline that re-muxes segments into concat lists.

## Step 1 — Install

```bash
pip install scenedetect[opencv]            # recommended (bundled OpenCV wheel)
pip install scenedetect[opencv-headless]   # headless servers, no GUI deps
pip install scenedetect                     # core only — OpenCV already present
```

Verify: `scenedetect version`. Splitting requires `ffmpeg` (default) or `mkvmerge` on PATH.

## Step 2 — Pick detector + threshold

Detectors are mutually exclusive positional commands:

| Detector | When | Typical threshold |
|---|---|---|
| `detect-content` | Default. Content-aware via HSV deltas. Best general choice. | `-t 27` (default). Range 15–40. |
| `detect-adaptive` | Mixed pacing, slow fades, camera motion. Rolling average of content metric. | `-t 3.0` (default adaptive ratio). |
| `detect-threshold` | Fade-to-black detection or hard-cut-only content. | `-t 12` (default, 0–255 luma). |
| `detect-hash` | Perceptual hash; good for detecting duplicate/near-duplicate frames. | `-t 0.395`. |

**Threshold intuition:** higher threshold ⇒ fewer scenes (more tolerant of change). Lower for dark or low-contrast content; raise for noisy / shaky handheld.

**Minimum scene length:** pass `-m 2.0` (seconds) to the detector to drop micro-cuts under 2s.

**Luma-only fast mode:** `detect-content -l` skips HSV, uses only luma — cheap on CPU.

## Step 3 — Run

Single-detector + list:

```bash
scenedetect -i in.mp4 detect-content list-scenes -o scenes.csv
```

Chain multiple outputs in one pass (detector runs once):

```bash
scenedetect -i in.mp4 \
  detect-content -t 27 -m 2.0 \
  list-scenes -o scenes.csv \
  save-images -n 3 -o thumbs \
  split-video -o parts -m
```

Global options worth knowing:

- `-o DIR` — global output directory (applies to all commands unless overridden).
- `-s STATS.csv` — write per-frame metric CSV (very useful for threshold tuning).
- `--downscale N` — process every Nth pixel (N=4 for 4K); massive speed-up.
- `--start T`, `--end T`, `--duration T` — limit analysis range (skip intros).
- `-v quiet|error|warning|info|debug` — verbosity.

## Step 4 — Use the scenes

### 4a. Split the video

```bash
# Re-encode via ffmpeg — exact cuts, slow
scenedetect -i in.mp4 detect-content split-video -o parts

# Stream-copy via mkvmerge — fast, cuts only at keyframes (not frame-exact)
scenedetect -i in.mp4 detect-content split-video -m -o parts
```

`split-video` requires `ffmpeg` unless `-m` is passed (then needs `mkvmerge`). Output filenames default to `$VIDEO_NAME-Scene-001.mp4` etc.

### 4b. Thumbnails per scene

```bash
scenedetect -i in.mp4 detect-content save-images -n 3 -o thumbs
```

`-n N` = images per scene (default 3: first / middle / last). JPG by default; add `--jpeg-quality 95` or switch with `--png`. Useful for chapter art or contact sheet.

### 4c. Chapters

No first-class chapter exporter — convert `list-scenes` CSV to ffmetadata format (the helper script's `chapters` subcommand does this). Then:

```bash
ffmpeg -i in.mp4 -i chapters.txt -map_metadata 1 -codec copy out.mp4
```

### 4d. HTML report

```bash
scenedetect -i in.mp4 detect-content list-scenes save-images export-html -o report.html
```

Self-contained HTML with thumbnails + timecodes. Great for editorial review.

## Available scripts

- **`scripts/scenedetect.py`** — stdlib wrapper with `check`, `detect`, `split`, `thumbnails`, `html-report`, `chapters` subcommands. All support `--dry-run` and `--verbose`.

## Workflow

```bash
# Verify install
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py check

# Detect, get scene list as JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py detect \
  --input in.mp4 --method content --threshold 27 --min-duration 2.0

# Split with stream-copy
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py split \
  --input in.mp4 --outdir parts --stream-copy

# Per-scene thumbnails
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py thumbnails \
  --input in.mp4 --outdir thumbs --per-scene 3

# HTML report
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py html-report \
  --input in.mp4 --output report.html

# Build ffmetadata chapter file
uv run ${CLAUDE_SKILL_DIR}/scripts/scenedetect.py chapters \
  --input in.mp4 --output chapters.txt
```

## Reference docs

- Read [`references/scenedetect.md`](references/scenedetect.md) for detector comparison, threshold tuning per content type, CSV/JSON/HTML formats, `scdet` vs PySceneDetect, and recipe book (auto-chapter DVD, commercial detection, video summaries).

## Gotchas

- **Detector then command chain.** `scenedetect -i FILE <detect-X> <cmd1> <cmd2> ...` — `detect-X` runs first; every command after re-uses its output. ALL can run in one invocation.
- **Threshold scale is content-dependent.** 15–40 typical for `detect-content`; default 27. Higher = fewer scenes. Lower for dark / low-contrast; raise for noisy / shaky.
- **`split-video` defaults to re-encoding via ffmpeg** — slow. Pass `-m` to stream-copy with mkvmerge — fast, but cuts fall on keyframes only (not frame-exact).
- **`save-images` default is 3 per scene** (first / middle / last). `-n N` overrides.
- **`-m` on the *detector*** sets minimum scene duration (seconds). `-m` on `split-video` means "use mkvmerge". Same flag letter, different meaning per command.
- **HSV color space** used internally for `detect-content`; on grayscale content use `-l` (luma-only) for speed.
- **Default detects every transition, including fades.** For mixed pacing use `detect-adaptive`.
- **Large files: add `--downscale 4`** (process every 4th pixel). Cuts runtime massively with negligible accuracy loss.
- **Always test threshold on a short clip first** (`--start 60 --duration 120`) — threshold varies per content type.
- **PySceneDetect is superior to ffmpeg `scdet`** on anime / stylized / low-contrast content. Use `scdet` only when you already have ffmpeg in the pipeline and content is live-action.
- **CSV header:** `Scene Number, Start Frame, Start Time (seconds), Start Timecode, End Frame, End Time (seconds), End Timecode, Length (frames), Length (seconds), Length (timecode)`.
- **For frame-exact stream-copy cuts,** convert the CSV to an ffmpeg concat list and re-mux with `-c copy` — but accept that cuts align to the nearest keyframe anyway.
- **No `ffmpeg` required unless splitting.** Analysis itself only needs OpenCV / PySceneDetect.
- **`--start` + `--duration`** skip intros / limit range; applies globally.

## Examples

### Example 1: Auto-chapter a DVD rip

```bash
scenedetect -i movie.mkv \
  detect-adaptive -m 5.0 \
  list-scenes -o scenes.csv save-images -n 1 -o chapter_art
# then convert scenes.csv → chapters.txt via helper script
uv run scripts/scenedetect.py chapters --input movie.mkv --output chapters.txt
ffmpeg -i movie.mkv -i chapters.txt -map_metadata 1 -c copy movie_chap.mkv
```

### Example 2: Detect commercials in a TV recording

```bash
# Fades to black are the commercial breaks — use threshold detector
scenedetect -i recording.ts detect-threshold -t 8 list-scenes -o breaks.csv
```

### Example 3: Video summary grid

```bash
scenedetect -i vlog.mp4 detect-content -t 30 -m 3.0 save-images -n 1 -o frames
# then montage via ImageMagick
magick montage frames/*.jpg -tile 6x -geometry 320x180+4+4 summary.jpg
```

### Example 4: Fast first pass on a 4K file

```bash
scenedetect --downscale 4 -i 4k.mp4 detect-content -l -m 2.0 list-scenes -o scenes.csv
```

## Troubleshooting

### Error: `scenedetect: command not found`

Cause: not installed or not on PATH.
Solution: `pip install scenedetect[opencv]`. If installed in a venv, activate it or use `python -m scenedetect ...`.

### Error: `Failed to open video: <file>` / `cv2.error`

Cause: OpenCV can't decode the container (some MKVs with odd codecs).
Solution: re-mux to mp4 first (`ffmpeg -i in.mkv -c copy in.mp4`) or install full `scenedetect[opencv]` wheel.

### Too many / too few scenes

Cause: threshold off for your content.
Solution: generate a stats file (`-s stats.csv`) to see per-frame metric, then pick threshold above typical baseline but below scene-cut spikes.

### `split-video` produced weird-length segments

Cause: `-m` (mkvmerge) only cuts on keyframes — GOP-aligned, not frame-exact.
Solution: drop `-m` to re-encode (frame-exact) or raise GOP density at encode time.

### Adaptive detector misses obvious cuts

Cause: rolling window smoothing threshold too high for slow-paced content.
Solution: lower `-t` (e.g. `-t 2.0`), or fall back to `detect-content` with a high min-duration.
