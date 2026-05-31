# PySceneDetect Reference

Companion deep-dive for the `media-scenedetect` skill. Everything here is secondary to the live `scenedetect --help` output but captures stable patterns, tuning heuristics, and recipes.

## 1. Detector comparison

| Detector | Metric | What it measures | Good for | Pitfall |
|---|---|---|---|---|
| **`detect-content`** (ContentDetector) | Weighted sum of per-frame HSV deltas (+ luma + edge). Default `-t 27`. | Sharp cuts, scene changes with color or luma shift. | General-purpose. Almost always the right first try. | Fires on camera-flash frames, fast whip-pans. Mitigate with `-m 1.5`. |
| **`detect-adaptive`** (AdaptiveDetector) | Rolling ratio of the content metric vs. its local moving average. Default `-t 3.0`, `-w 2` (window). | Mixed pacing: slow dialogue + sudden cuts. | Long-form, camera motion is common. | Misses sequences of similar-intensity cuts; noisy on very short scenes. |
| **`detect-threshold`** (ThresholdDetector) | Absolute average pixel intensity vs. threshold. Default `-t 12`, uses fade-in/out modeling. | Fade-to-black transitions, commercial break detection in TV recordings. | Won't catch hard cuts that stay at the same luma. |
| **`detect-hash`** (HashDetector) | Perceptual hash (pHash) Hamming distance between frames. Default `-t 0.395`. | Detecting duplicate/near-duplicate frames across content; good on stylized / animated. | Less tuned than content detector for a generic scene list. |

All detectors accept `-m DURATION` (minimum scene seconds) to suppress chatter.

### When to prefer each

- **Live-action film / TV:** `detect-content -t 27 -m 1.5`.
- **Anime / stylized 2D:** `detect-content -t 30 -m 2.0` OR `detect-hash -t 0.3`.
- **Dark / low-contrast footage:** `detect-content -t 15 -l` (luma-only can be *more* sensitive here).
- **Static talking heads with occasional cuts:** `detect-adaptive -t 3.0 -m 3.0`.
- **TV-with-commercial detection:** `detect-threshold -t 8 -m 10.0` (fade breaks must be ≥10s).
- **Near-duplicate filtering / loop detection:** `detect-hash`.

## 2. Threshold tuning guide

**Universal procedure:**

1. Generate a stats CSV first: `scenedetect -i IN -s stats.csv detect-content`.
2. Open the CSV; the `content_val` column is the per-frame metric.
3. Look at the distribution: baseline "quiet" frames sit in a band; real cuts are 3-10× higher spikes.
4. Set threshold just above the baseline noise band.

**Content-type starting points for `detect-content -t`:**

| Content | Suggested `-t` | Notes |
|---|---|---|
| Modern live-action (30fps+) | 27 (default) | Good out of the box. |
| Cinematic film (24fps, graded) | 25–28 | Lower threshold picks up soft grade transitions. |
| Anime / 2D animation | 30–35 | Stylized colors, avoid false positives from keyframe holds. |
| Dark / noir | 15–20 | Reduced delta magnitude; must lower. |
| Bright stock / outdoor | 30–35 | Motion noise inflates metric. |
| Sports broadcast | 22–27 with `-m 2.0` | Camera cuts are frequent, want to drop micro-cuts. |
| Security / surveillance | `detect-adaptive` | Long static, rare events. |
| Concert / music video | 30–40 + `-m 1.0` | Very frequent cuts, want only macro boundaries. |

Rule of thumb: if you're getting 5× more scenes than expected, *raise* threshold by 5. If you're missing obvious cuts, *lower* by 5.

## 3. Output formats

### CSV (`list-scenes -o scenes.csv`)

Two sections:

```
Timecode List:
00:00:12.345,00:00:45.678,00:01:03.123

Scene Number, Start Frame, Start Time (seconds), Start Timecode, End Frame, End Time (seconds), End Timecode, Length (frames), Length (seconds), Length (timecode)
1,0,0.000,00:00:00.000,295,12.345,00:00:12.345,295,12.345,00:00:12.345
...
```

The first line (timecode list) is comma-joined cut points; the rest is a standard CSV with the header shown.

### JSON

PySceneDetect doesn't emit JSON natively. Either:

- Pipe `list-scenes -o -` to stdout and parse, or
- Use the helper script: `uv run scripts/scenedetect.py detect ...` which emits structured JSON built from the CSV.

### HTML (`export-html -o report.html`)

Self-contained HTML with embedded JPG thumbnails. Best for editorial sharing. Requires `save-images` in the same chain (thumbnails are the image source).

### ffmetadata chapters

Not a first-class exporter. Conversion pattern (CSV → ffmetadata) is encapsulated in the helper script's `chapters` subcommand. Then:

```bash
ffmpeg -i in.mp4 -i chapters.txt -map_metadata 1 -c copy out.mp4
```

MP4 containers accept chapter metadata via this route; MKV likewise.

## 4. `scenedetect` vs `ffmpeg scdet`

| Dimension | PySceneDetect | ffmpeg `scdet` filter |
|---|---|---|
| Accuracy | Excellent on all content types. Tunable per-detector. | Decent on live-action, poor on anime / stylized / low-contrast. |
| Output | CSV, thumbnails, split video, HTML report — first-class. | Prints probabilities to log; no native cut-list format. |
| Thumbnail generation | Built-in (`save-images`). | Manual per-timestamp `ffmpeg` calls. |
| Video splitting | Built-in, mkvmerge stream-copy option. | Must parse scdet log then chain into `-ss`/`-to`. |
| Runtime (1h @ 1080p) | ~2-6 min depending on detector. | ~1-2 min (filter runs inline with decode). |
| Install cost | `pip install scenedetect[opencv]`. | Bundled with ffmpeg. |
| Programmatic use | Python API, CLI, stats CSV. | Log parsing only. |

**Rule:** use `scdet` when you already have an ffmpeg pipeline and content is generic live-action. Use PySceneDetect when you need reliability, anime/stylized content, or a proper cut list.

## 5. Chaining commands

`scenedetect -i FILE <GLOBAL> <DETECTOR> <CMD1> <CMD2> ...` runs the detector *once* and feeds its scene list to every command. Common chains:

```bash
# Detect + list + thumbnails + split (one decode pass for analysis)
scenedetect -i in.mp4 \
  detect-content -t 27 -m 2.0 \
  list-scenes -o scenes.csv \
  save-images -n 3 -o thumbs \
  split-video -m -o parts

# Detect + stats dump (tuning)
scenedetect -i in.mp4 -s stats.csv detect-content list-scenes

# Analysis range (skip intro + outro)
scenedetect -i in.mp4 --start 00:01:30 --end 00:58:00 \
  detect-content list-scenes -o scenes.csv

# 4K fast pass
scenedetect --downscale 4 -i in.mp4 detect-content -l list-scenes
```

Global flags (before the detector) — `-i`, `-o`, `-s`, `-v`, `--downscale`, `--start`, `--end`, `--duration`, `--framerate`.

Command flags (after each command) are command-scoped. Re-order commands freely.

## 6. Recipe book

### 6.1 Auto-chapter a DVD rip

```bash
# Detect with adaptive (DVD extras + features mix pacing), min 5s scenes
scenedetect -i movie.mkv detect-adaptive -m 5.0 list-scenes -o scenes.csv

# Convert to ffmetadata
uv run scripts/scenedetect.py chapters --input movie.mkv --output chapters.txt

# Mux chapters into MKV (stream-copy)
ffmpeg -i movie.mkv -i chapters.txt -map_metadata 1 -map 0 -c copy movie_chap.mkv
```

### 6.2 TV commercial detection

Commercial breaks on US broadcast TV fade to black for ~0.5s between ads.

```bash
# Fade-to-black threshold detection, minimum 10s between fades (real ad breaks)
scenedetect -i recording.ts detect-threshold -t 8 -m 10.0 list-scenes -o breaks.csv

# Feed breaks into an ffmpeg concat list to re-mux only program content
```

### 6.3 Documentary shot list

```bash
# Detect + thumbnail first / mid / last of each scene, HTML report
scenedetect -i doc.mp4 \
  detect-content -t 27 -m 3.0 \
  list-scenes -o shotlist.csv \
  save-images -n 3 -o shots \
  export-html -o shotlist.html
```

Shotlist.csv becomes the timeline for the edit; shotlist.html goes to the director for review.

### 6.4 Video summary thumbnail grid

```bash
# One thumbnail per scene, 3s minimum
scenedetect -i vlog.mp4 detect-content -t 30 -m 3.0 save-images -n 1 -o frames

# ImageMagick grid
magick montage frames/*.jpg -tile 6x -geometry 320x180+4+4 summary.jpg
```

### 6.5 Split without re-encode (stream-copy via mkvmerge)

```bash
scenedetect -i show.mkv detect-content split-video -m -o parts/
```

Cuts align to keyframes (not frame-exact) but runs ~10× faster than re-encode.

### 6.6 Anime / stylized content

```bash
# Higher threshold + min-duration because keyframe holds cause false positives
scenedetect -i anime.mkv detect-content -t 32 -m 2.0 list-scenes save-images -n 1
# Or try perceptual hash:
scenedetect -i anime.mkv detect-hash -t 0.35 list-scenes
```

### 6.7 Concat list for stream-copy re-mux

After `list-scenes -o scenes.csv`:

```bash
# Build ffmpeg concat file from CSV start timecodes (rough pseudo)
awk -F, 'NR>2 {printf("file %s\ninpoint %s\noutpoint %s\n", source, $4, $7)}' \
  scenes.csv > concat.txt

ffmpeg -f concat -safe 0 -i concat.txt -c copy out.mp4
```

Cuts align to the nearest keyframe on stream-copy regardless of what PySceneDetect detected — accept that or re-encode.

### 6.8 Skip the intro for analysis

```bash
scenedetect -i series_s01e01.mkv --start 00:01:30 detect-content list-scenes
```

`--start` / `--end` / `--duration` gate the *analysis range*, not the output of other commands. Combine with `-m` for practical filtering.

## 7. Performance notes

- **`--downscale 4`** processes every 4th pixel in both dimensions → 16× fewer pixels → massive speed-up on 4K. Accuracy loss is negligible for scene detection.
- **`detect-content -l`** (luma-only) skips HSV computation. Use on grayscale or when CPU-bound.
- **Seeking vs decode** — PySceneDetect decodes every frame regardless; it doesn't seek. For 4h+ files, pre-trim with ffmpeg (`-ss` + `-to` + `-c copy`) to a working copy.
- **No GPU acceleration** — scenedetect is CPU-only. For GPU-scale work, write a custom OpenCV+CUDA pipeline or rely on ffmpeg `scdet` + NVDEC.

## 8. Python API (brief)

For deep programmatic use, import directly:

```python
from scenedetect import detect, ContentDetector, split_video_ffmpeg

scenes = detect("in.mp4", ContentDetector(threshold=27.0))
for start, end in scenes:
    print(start.get_timecode(), end.get_timecode())

split_video_ffmpeg("in.mp4", scenes, output_dir="parts")
```

The CLI is sufficient for nearly all workflows; drop to the API only when you need custom detectors or embedded logic.

## 9. Version caveats

- PySceneDetect 0.6+ introduced `detect-adaptive` and `detect-hash` as first-class CLI verbs; earlier versions had a different flag grammar (`--detector` global). Always check `scenedetect version`.
- Behavior of `split-video -m` depends on `mkvmerge` version — older versions cut only on I-frames, newer versions handle open GOPs.
- OpenCV 4.x vs. 3.x: the `[opencv]` extra pins a known-good version; don't mix with a system OpenCV install unless you know what you're doing.
