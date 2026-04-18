---
name: media-moviepy
description: >
  Programmatic video editing in Python with MoviePy: build videos from clips, text overlays, transitions, compositing, audio manipulation, frame-by-frame custom effects via numpy, concatenate / subclip / fx / resize / rotate. Use when the user asks to build a video programmatically, use MoviePy, make a video from Python code, do numpy frame manipulation, build a template video pipeline in Python, or generate videos dynamically from data.
argument-hint: "[script.py]"
---

# Media MoviePy

Programmatic, Python-first non-linear video editing. MoviePy wraps ffmpeg for I/O but operates on frames in numpy, so it wins on readability and data-driven pipelines — not on throughput. Reach for it when you need *logic*, not a faster transcode.

## Quick start

- **Concatenate clips:** pip install moviepy → `VideoFileClip` → `concatenate_videoclips` → `write_videofile` (Step 2, 3).
- **Burn caption text:** `TextClip` on top of video via `CompositeVideoClip` (Step 3, needs ImageMagick).
- **Per-frame numpy filter:** `clip.image_transform(lambda img: ...)` (Step 3).
- **Trim clip:** `clip.subclipped(10, 20)` (Step 2).
- **Resize / crop / speed:** `clip.resized(width=1280)`, `clip.cropped(...)`, `clip.with_speed_scaled(2.0)`.

## When to use

- You need to generate N videos from a CSV / JSON / database (per-customer, per-product, per-event).
- You want to stitch a template: intro → dynamic middle → outro, with overlays computed from data.
- You need custom per-pixel logic expressible as numpy (ffmpeg `geq` would be painful).
- You are prototyping an effect in a Jupyter notebook.
- **Do NOT use** for plain transcode / cut / concat of large files — `ffmpeg` direct is 10–50× faster.
- **Do NOT use** for real-time streaming; MoviePy is batch-only.
- For production web-first template pipelines, Remotion (JS/React) is usually faster and has a better dev loop.

## Step 1 — Install

```bash
pip install moviepy                 # MoviePy 2.x (2024+); this is the current API
# pip install moviepy==1.0.3        # pin to 1.x ONLY if you have legacy code using set_*/subclip/resize
python -c "import moviepy; print(moviepy.__version__)"
```

Dependencies pulled in: `numpy`, `decorator`, `proglog`, `Pillow`, `imageio`, `imageio-ffmpeg` (ships an ffmpeg binary). Not pulled in: `ImageMagick` — you must install it yourself if you want `TextClip`.

```bash
# macOS
brew install imagemagick
# Debian/Ubuntu
sudo apt-get install imagemagick
# Then UNBLOCK pango/text reads in the ImageMagick policy:
#   sudo sed -i 's/<policy domain="path" rights="none" pattern="@\*"/<!--&-->/' /etc/ImageMagick-6/policy.xml
#   (or /etc/ImageMagick-7/policy.xml — remove the PATTERN / TEXT deny rules)
```

Quick sanity check — use the bundled script:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py check
```

## Step 2 — Build from clips

Load, trim, and combine source clips. MoviePy 2.x uses **`with_*` setters** (functional, return a new clip) and **past-tense transforms** (`resized`, `cropped`, `subclipped`, `rotated`).

```python
from moviepy import VideoFileClip, AudioFileClip, ImageClip, ColorClip, concatenate_videoclips

a = VideoFileClip("intro.mp4")
b = VideoFileClip("body.mp4").subclipped(0, 30)          # first 30 s
c = VideoFileClip("outro.mp4").resized(width=1280)       # keep aspect ratio
bg = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=3)
logo = ImageClip("logo.png", duration=5).with_position(("right", "top"))

timeline = concatenate_videoclips([a, b, c], method="compose")  # "compose" allows different sizes
timeline = timeline.with_audio(AudioFileClip("music.mp3")
                                 .with_audio_fadein(2)
                                 .with_audio_fadeout(2))
```

Core per-clip operations:

| Op | MoviePy 2.x |
|---|---|
| Trim | `clip.subclipped(start, end)` |
| Resize | `clip.resized(width=1280)` / `clip.resized(0.5)` |
| Crop | `clip.cropped(x1=100, y1=100, x2=1820, y2=980)` |
| Rotate | `clip.rotated(90)` |
| Speed | `clip.with_speed_scaled(factor=2.0)` |
| Reverse | `clip.reversed()` |
| Video fade | `clip.with_fadein(1).with_fadeout(1)` |
| Set audio | `clip.with_audio(audio_clip)` |
| Position (for compositing) | `clip.with_position("center")` / `("right", 50)` |
| Start/end on timeline | `clip.with_start(4).with_end(9)` |
| Duration | `clip.with_duration(5)` |

## Step 3 — Compose, overlay, filter, render

**Text overlays** — requires ImageMagick (see Step 1):

```python
from moviepy import TextClip, CompositeVideoClip

caption = (TextClip(text="Breaking News", font_size=70, color="white",
                    font="Arial", stroke_color="black", stroke_width=2,
                    duration=5)
           .with_position(("center", "bottom"))
           .with_start(2))
final = CompositeVideoClip([timeline, caption])
```

**Per-frame numpy filter** — raw image math, RGB uint8 `(H, W, 3)`:

```python
import numpy as np
mirrored = clip.image_transform(lambda img: img[:, ::-1])
brighter = clip.image_transform(lambda img: np.clip(img * 1.2, 0, 255).astype("uint8"))
```

**Crossfade transition** (A ends at 5s, B starts at 4s, 1s overlap):

```python
a_fade = a.with_end(5).with_audio_fadeout(1)
b_fade = b.with_start(4).with_audio_fadein(1).crossfadein(1)
final = CompositeVideoClip([a_fade, b_fade])
```

**Render:**

```python
final.write_videofile(
    "out.mp4",
    codec="libx264", audio_codec="aac",
    fps=30, bitrate="5000k",
    preset="medium",                    # ultrafast|fast|medium|slow
    threads=4,
    ffmpeg_params=["-crf", "18"],       # precision knob; overrides bitrate
    audio_fps=48000,
    remove_temp=True,
)
# audio-only
AudioFileClip("music.mp3").write_audiofile("out.mp3")
# image sequence
final.write_images_sequence("frames/frame_%04d.png", fps=30)
```

## Step 4 — Verify

```bash
ffprobe -v error -show_streams -of json out.mp4 | head
ffplay out.mp4                                            # if available
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py check    # sanity check install
```

Confirm duration, resolution, and presence of audio. If `write_videofile` finished but the file is 0 bytes or lacks audio, check the `temp_audiofile` cleanup and the `audio_codec` argument.

## Gotchas

- **MoviePy 2.x broke 1.x method names.** `subclip()` → `subclipped()`, `set_position` → `with_position`, `set_duration` → `with_duration`, `set_start` → `with_start`, `resize` → `resized`, `crop` → `cropped`, `rotate` → `rotated`, `fx(vfx.speedx, 2)` → `with_speed_scaled(2)`. If code uses the old names, either upgrade the code or `pip install moviepy==1.0.3`. Always: `python -c "import moviepy; print(moviepy.__version__)"`.
- **Imports moved in 2.x.** Everything is on the top-level `moviepy` package now: `from moviepy import VideoFileClip, TextClip, CompositeVideoClip`. In 1.x it was `from moviepy.editor import ...`.
- **TextClip requires ImageMagick.** No ImageMagick → `OSError: MoviePy Error: creation of None failed`. Install it, and on Debian/Ubuntu/Docker you must edit `/etc/ImageMagick-6/policy.xml` (or `-7/`) to remove or comment out the `domain="path" rights="none" pattern="@*"` and the TEXT/PATTERN deny rules, or rendering from strings will fail.
- **Alternative to ImageMagick:** render text with Pillow into a numpy array, wrap in `ImageClip`, composite. Slower to code but zero system-dependency headache.
- **Speed vs ffmpeg.** MoviePy decodes to numpy, processes in Python, re-encodes. Expect 5–50× slower than an equivalent pure-ffmpeg command. Use MoviePy for logic/templates, not for "just convert this file".
- **Memory balloons on long videos.** MoviePy buffers frames per clip; a 2-hour 4K render can OOM. Chunk the timeline, render parts, concat with ffmpeg.
- **Temp audio file.** `write_videofile` writes a temp WAV in `$TEMP`. Pass `remove_temp=True` (default True in 2.x) and a specific `temp_audiofile="/tmp/foo.m4a"` if you hit disk-space issues.
- **Default threads = 1.** Bump via `write_videofile(threads=4)`. Doesn't parallelize frame math, only x264.
- **Audio sample-rate mismatch** between source and music → clicks / desync. Force: `write_videofile(audio_fps=48000)`.
- **BGR vs RGB.** MoviePy frames are RGB uint8. If you feed a clip from OpenCV (BGR), `image_transform` gets BGR — convert or expect wrong colors.
- **`clip.mask` is slow.** Avoid using mask clips unless you actually need transparency; prefer compositing opaque layers.
- **`concatenate_videoclips(method="chain")`** only works when all clips share size / fps / audio layout. Use `method="compose"` to be safe (pads to largest size).

## Examples

### 1. Three-clip concat with music and fades

```python
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
clips = [VideoFileClip(p).with_fadein(0.5).with_fadeout(0.5) for p in ["a.mp4", "b.mp4", "c.mp4"]]
final = concatenate_videoclips(clips, method="compose")
final = final.with_audio(AudioFileClip("bg.mp3").with_audio_fadein(1).with_audio_fadeout(2))
final.write_videofile("story.mp4", codec="libx264", fps=30, threads=4)
```

### 2. News-clip template (intro + body + lower-third caption + outro)

```python
from moviepy import VideoFileClip, TextClip, ImageClip, CompositeVideoClip, concatenate_videoclips
intro, outro = VideoFileClip("intro.mp4"), VideoFileClip("outro.mp4")
body = VideoFileClip("footage.mp4").subclipped(0, 20).resized(width=1920)
lt = (TextClip(text="DATELINE — APRIL 17", font_size=48, color="white",
               font="Arial", bg_color="red", duration=body.duration)
      .with_position(("left", 950)))
composited = CompositeVideoClip([body, lt])
concatenate_videoclips([intro, composited, outro], method="compose") \
    .write_videofile("news.mp4", codec="libx264", fps=30, bitrate="8000k")
```

### 3. Data-driven slideshow from a folder of photos

```python
from moviepy import ImageClip, concatenate_videoclips
from pathlib import Path
clips = [ImageClip(str(p), duration=3).resized(height=1080).with_fadein(0.5).with_fadeout(0.5)
         for p in sorted(Path("photos").glob("*.jpg"))]
concatenate_videoclips(clips, method="compose").write_videofile(
    "slideshow.mp4", codec="libx264", fps=30)
```

### 4. Per-frame numpy filter (sepia)

```python
import numpy as np
from moviepy import VideoFileClip
def sepia(img):
    m = np.array([[0.393,0.769,0.189],[0.349,0.686,0.168],[0.272,0.534,0.131]])
    return np.clip(img @ m.T, 0, 255).astype("uint8")
VideoFileClip("in.mp4").image_transform(sepia).write_videofile("sepia.mp4", codec="libx264")
```

### 5. Use the bundled CLI

```bash
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py concat --inputs a.mp4 b.mp4 c.mp4 --output out.mp4
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py subclip --input in.mp4 --start 10 --end 20 --output cut.mp4
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py text-overlay --input in.mp4 --output captioned.mp4 --text "Hello" --position bottom
python ${CLAUDE_SKILL_DIR}/scripts/moviepy_cli.py template --config news.json
```

## Troubleshooting

### `AttributeError: 'VideoFileClip' object has no attribute 'subclip'` (or `set_position`, `resize`, ...)

Cause: MoviePy 2.x renamed methods. You are on 2.x but the code uses 1.x names.
Solution: Rename (`subclip` → `subclipped`, `set_position` → `with_position`, `resize` → `resized`, etc.) or `pip install moviepy==1.0.3`.

### `ModuleNotFoundError: No module named 'moviepy.editor'`

Cause: 2.x dropped `moviepy.editor`.
Solution: `from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips` — import from top-level.

### `OSError: MoviePy Error: creation of None failed` when using `TextClip`

Cause: ImageMagick missing, or its `policy.xml` disallows reading from strings.
Solution: Install ImageMagick; edit `/etc/ImageMagick-{6,7}/policy.xml` to comment out the `rights="none" pattern="@*"` and TEXT/PATTERN deny rules. On macOS `brew install imagemagick` generally works out of the box.

### Render is painfully slow

Cause: Single-threaded x264, heavy per-frame Python.
Solution: Bump `threads=4`, use `preset="fast"` or `"ultrafast"` for drafts, move heavy logic to numpy (vectorize out of Python loops), or render → re-encode with pure ffmpeg. If you are doing plain concat/trim, switch to ffmpeg `-c copy`.

### Output has no audio / desynced audio

Cause: Missing `audio_codec`, sample-rate mismatch, or muted source.
Solution: `write_videofile("out.mp4", codec="libx264", audio_codec="aac", audio_fps=48000)`. Verify the source clip actually has audio: `VideoFileClip("in.mp4").audio is None`.

### `MemoryError` on a long render

Cause: Whole pipeline held in RAM.
Solution: Split the timeline into segments, render each to disk, ffmpeg-concat the results.
