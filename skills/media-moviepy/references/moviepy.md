# MoviePy 2.x Reference

Load this when you need API detail beyond the SKILL.md quick-start: full method catalog, `write_videofile` parameter semantics, ImageMagick setup, pipeline patterns, comparison with alternatives, and a recipe book.

## Version

MoviePy has two incompatible generations:

| | 1.x (`1.0.3`) | 2.x (2024+) |
|---|---|---|
| Install | `pip install moviepy==1.0.3` | `pip install moviepy` |
| Import root | `from moviepy.editor import ...` | `from moviepy import ...` |
| Setters | `set_position`, `set_duration`, `set_start`, `set_end`, `set_audio` | `with_position`, `with_duration`, `with_start`, `with_end`, `with_audio` |
| Transforms | `subclip`, `resize`, `crop`, `rotate`, `fl_image` | `subclipped`, `resized`, `cropped`, `rotated`, `image_transform` |
| Speed | `clip.fx(vfx.speedx, 2)` | `clip.with_speed_scaled(factor=2.0)` |
| Reverse | `clip.fx(vfx.time_mirror)` | `clip.reversed()` |
| Fade | `clip.fadein(1).fadeout(1)` | `clip.with_fadein(1).with_fadeout(1)` |
| Audio fade | `clip.audio_fadein(1)` | `clip.with_audio_fadein(1)` |

Always confirm: `python -c "import moviepy; print(moviepy.__version__)"`. Everything below is MoviePy 2.x.

## Clip classes

All clip classes inherit from `Clip` → `VideoClip` / `AudioClip`. Methods with the `with_*` prefix are immutable: they return a new clip, they do not mutate in-place.

### `VideoFileClip(filename, audio=True, has_mask=False, decode_file=False, fps_source="fps")`
Read a video file (any format ffmpeg can decode). `has_mask=True` if the file has an alpha channel (ProRes 4444, WebM with alpha). `fps_source="tbr"` can help with VFR sources.

### `AudioFileClip(filename, decode_file=False, buffersize=200000, nbytes=2, fps=44100)`
Read an audio file. Returns an `AudioClip`.

### `ImageClip(img, duration=None, is_mask=False, transparent=True, fromalpha=False, ismask=False)`
Create a still-video clip from an image file path or a numpy `(H, W, 3)` / `(H, W, 4)` array. Must set `duration` (or `with_duration`) before compositing.

### `ColorClip(size, color=None, duration=None, is_mask=False)`
Solid-color clip. `size=(w, h)`, `color=(r, g, b)` in 0–255.

### `TextClip(text=None, filename=None, font=None, font_size=None, size=(None, None), margin=(0, 0), color="black", bg_color=None, stroke_color=None, stroke_width=0, method="label", text_align="left", horizontal_align="center", vertical_align="center", interline=4, transparent=True, duration=None)`
Renders text via ImageMagick. `method="caption"` auto-wraps within `size`; `method="label"` sizes to fit the text. `font` accepts either a font family name ImageMagick knows about or a path to a `.ttf`/`.otf` file (path is more reliable).

### `CompositeVideoClip(clips, size=None, bg_color=None, use_bgclip=False)`
Stack clips in the order given; each clip is placed per `with_position`, `with_start`, `with_end`. Size defaults to the size of the first clip.

### `concatenate_videoclips(clips, method="chain", transition=None, bg_color=None, padding=0)`
Serially join clips. `method="chain"` needs identical size/fps/audio; `method="compose"` pads to the largest size (safer, slower).

## Method catalog (VideoClip)

| Category | Method | Notes |
|---|---|---|
| Timeline | `with_start(t)`, `with_end(t)`, `with_duration(d)` | For compositing |
| Trim | `subclipped(start_time, end_time=None)` | Replaces 1.x `subclip` |
| Layout | `with_position(pos, relative=False)` | pos: `"center"`, `(x,y)`, `("center","bottom")`, lambda t |
| Size | `resized(new_size=None, height=None, width=None)` | new_size: scale float or `(w,h)` |
| Crop | `cropped(x1,y1,x2,y2,width,height,x_center,y_center)` | Any subset of args |
| Rotate | `rotated(angle, unit="deg", resample="bicubic", expand=True)` | Angle can be a function of `t` |
| Mirror | `image_transform(lambda f: f[:,::-1])` | No dedicated flip |
| Speed | `with_speed_scaled(factor=2.0)` | Affects audio too |
| Reverse | `reversed()` | |
| Fades | `with_fadein(d)`, `with_fadeout(d)`, `crossfadein(d)`, `crossfadeout(d)` | |
| Audio ops | `with_audio(aclip)`, `without_audio()`, `with_volume_scaled(factor)` | |
| Audio fades | `with_audio_fadein(d)`, `with_audio_fadeout(d)` | |
| Frame math | `image_transform(fn, apply_to=[])` | `fn(img) -> img`, RGB uint8 |
| Time math | `time_transform(fn)` | `fn(t) -> t'` for time remapping |
| Effects | `with_effects([vfx.MultiplyColor(1.2), ...])` | 2.x effects-class API |
| FPS | `with_fps(fps)` | |
| Mask | `with_mask(mask_clip)`, `without_mask()` | Mask is a gray-scale VideoClip in 0–1 |
| Export | `write_videofile(...)`, `write_gif(...)`, `write_images_sequence(...)`, `save_frame(path, t=0)` | See below |

## Method catalog (AudioClip)

| Method | Notes |
|---|---|
| `subclipped(t1, t2)` | Trim |
| `with_duration(d)` | |
| `with_start(t)`, `with_end(t)` | For placement in CompositeVideo |
| `with_volume_scaled(factor)` | Linear gain |
| `with_audio_fadein(d)`, `with_audio_fadeout(d)` | |
| `with_fps(fps)` | Resample |
| `write_audiofile(path, fps=44100, nbytes=2, buffersize=2000, codec=None, bitrate=None)` | |

## `write_videofile` parameters

```python
clip.write_videofile(
    filename,                # path, extension determines container
    fps=None,                # inherit from clip if None
    codec=None,              # default: libx264 for .mp4/.mov; libvpx for .webm
    bitrate=None,            # e.g. "5000k"
    audio=True,
    audio_fps=44100,
    preset="medium",         # x264: ultrafast, superfast, veryfast, faster, fast,
                             # medium, slow, slower, veryslow, placebo
    audio_nbytes=4,
    audio_codec=None,        # default: aac for .mp4/.mov; libvorbis for .ogv
    audio_bitrate=None,
    audio_bufsize=2000,
    temp_audiofile=None,     # path for intermediate audio; auto if None
    temp_audiofile_path="",
    remove_temp=True,
    write_logfile=False,
    threads=None,            # x264 threads; default 1, bump to 4+
    ffmpeg_params=None,      # list of extra args, e.g. ["-crf", "18"]
    logger="bar",            # proglog TQDM progress; pass None to silence
    pixel_format=None,       # e.g. "yuv420p" for maximum compatibility
)
```

**CRF vs bitrate.** For libx264, quality-based encoding is `ffmpeg_params=["-crf", "18"]` (lower = higher quality; 18 is visually lossless, 23 default, 28 is "small file"). This overrides `bitrate=`.

**yuv420p.** Add `ffmpeg_params=["-pix_fmt", "yuv420p"]` (or `pixel_format="yuv420p"`) for phone / web / Quicktime compatibility — without it x264 may write `yuv444p` which Safari refuses to play.

## ImageMagick dependency

`TextClip` shells out to ImageMagick (`magick` on IM7, `convert` on IM6). Installation and policy gotchas:

```bash
# macOS
brew install imagemagick

# Debian / Ubuntu / Docker
apt-get install -y imagemagick ghostscript
```

MoviePy locates the binary via:

```python
from moviepy.config import check, IMAGEMAGICK_BINARY
print(IMAGEMAGICK_BINARY)   # e.g. '/usr/bin/convert' or 'unset'
check()
```

If wrong or unset:

```python
import os
os.environ["IMAGEMAGICK_BINARY"] = "/opt/homebrew/bin/magick"
```

**Policy.xml surgery (Linux Docker base images).** `/etc/ImageMagick-{6,7}/policy.xml` ships with rules that forbid reading `@*` (string-based input that `TextClip` uses) and may forbid PDF / LABEL / TEXT / PATTERN. Comment or delete:

```xml
<policy domain="path" rights="none" pattern="@*" />
<policy domain="coder" rights="none" pattern="TEXT" />
<policy domain="coder" rights="none" pattern="LABEL" />
```

After editing, test: `magick -background none -fill white -font Arial label:"hi" hi.png`.

**Alternative that avoids ImageMagick entirely:** render text with Pillow into a numpy array, then wrap in `ImageClip`:

```python
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import ImageClip

def pillow_text(msg, size=(1280, 120), font_path="/Library/Fonts/Arial.ttf",
                font_size=64, color=(255, 255, 255, 255)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)
    w, h = draw.textbbox((0, 0), msg, font=font)[2:]
    draw.text(((size[0]-w)//2, (size[1]-h)//2), msg, font=font, fill=color)
    return np.array(img)

caption = ImageClip(pillow_text("Hello"), duration=5, transparent=True) \
            .with_position(("center", "bottom"))
```

## Pipeline patterns

### Template: intro → dynamic body → outro

```python
from moviepy import VideoFileClip, concatenate_videoclips

def build(intro, body_clip, outro, out):
    timeline = concatenate_videoclips(
        [VideoFileClip(intro), body_clip, VideoFileClip(outro)],
        method="compose")
    timeline.write_videofile(out, codec="libx264", fps=30, threads=4)
```

Call `build()` in a loop over rows of a DataFrame for N personalized videos.

### Dynamic subtitle overlay from SRT

```python
import pysrt
from moviepy import VideoFileClip, TextClip, CompositeVideoClip

def burn_srt(video_path, srt_path, out_path):
    video = VideoFileClip(video_path)
    subs = pysrt.open(srt_path)
    overlays = []
    for s in subs:
        start = s.start.ordinal / 1000
        end   = s.end.ordinal   / 1000
        t = (TextClip(text=s.text, font_size=42, color="white",
                      font="Arial", stroke_color="black", stroke_width=2,
                      duration=end - start)
             .with_position(("center", 850))
             .with_start(start))
        overlays.append(t)
    CompositeVideoClip([video, *overlays]).write_videofile(
        out_path, codec="libx264", fps=30, threads=4)
```

### Per-frame filter (numpy)

```python
import numpy as np
from moviepy import VideoFileClip

def vignette(img, strength=0.5):
    h, w = img.shape[:2]
    y, x = np.ogrid[:h, :w]
    cx, cy = w/2, h/2
    d = np.sqrt((x-cx)**2 + (y-cy)**2) / np.sqrt(cx**2 + cy**2)
    mask = (1 - strength*d)[..., None]
    return np.clip(img * mask, 0, 255).astype("uint8")

VideoFileClip("in.mp4").image_transform(vignette) \
    .write_videofile("vignette.mp4", codec="libx264", fps=30)
```

### Chunked render for long videos

```python
from moviepy import VideoFileClip, concatenate_videoclips
import subprocess, os

src = VideoFileClip("long.mp4")
CHUNK = 60  # seconds
parts = []
t = 0
while t < src.duration:
    end = min(t + CHUNK, src.duration)
    sub = src.subclipped(t, end).image_transform(...)  # expensive op
    p = f"part_{int(t):06d}.mp4"
    sub.write_videofile(p, codec="libx264", fps=30, threads=4, logger=None)
    parts.append(p)
    t = end
# Use ffmpeg concat demuxer (fast, no re-encode) to stitch
with open("parts.txt", "w") as f:
    for p in parts: f.write(f"file '{p}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", "parts.txt", "-c", "copy", "final.mp4"], check=True)
```

## MoviePy vs ffmpeg vs Remotion

| Dimension | MoviePy | ffmpeg (direct) | Remotion |
|---|---|---|---|
| Language | Python | shell / `filter_complex` | React / TypeScript |
| Speed | Slow (Python per frame) | Fast (C) | Medium (headless Chromium) |
| Readability | High | Low for complex graphs | High |
| Data-driven templates | Natural (pandas → clips) | Painful (shell loops) | Natural (JSX props) |
| Effects | numpy, any-code | Built-in filter set | CSS / Canvas / WebGL |
| Text layout | Via ImageMagick (fragile) | `drawtext` (limited) | Full web typography |
| Audio | Basic mixing, fades | Full toolbox | Basic |
| Best for | Programmatic batch, prototyping, per-frame numpy | High-volume transcode, production pipelines | Polished template videos with rich typography / motion graphics |
| Worst at | Long-form, high-volume | Logic-heavy templates | Custom numpy frame math |

**Rule of thumb:** if your task is expressible as one `ffmpeg` command, use ffmpeg; if it requires `if/for/pandas`, use MoviePy; if it requires nice typography and CSS-style layout, use Remotion.

## Recipe book

### 1. News clip with ticker, lower-third, and logo

```python
from moviepy import (VideoFileClip, TextClip, ImageClip, ColorClip,
                     CompositeVideoClip, concatenate_videoclips)

body = VideoFileClip("footage.mp4").subclipped(0, 25).resized(width=1920)

logo = ImageClip("logo.png", duration=body.duration) \
    .resized(height=100) \
    .with_position(("right", 30))

lower = (ColorClip(size=(1920, 140), color=(200, 0, 0),
                   duration=body.duration).with_opacity(0.85)
         .with_position((0, 900)))

title = (TextClip(text="BREAKING — Market close, April 17",
                  font_size=56, color="white", font="Arial-Bold",
                  duration=body.duration)
         .with_position((40, 920)))

ticker = (TextClip(text="AAPL +1.2%   TSLA -0.8%   BTC $71,200",
                   font_size=36, color="yellow", font="Arial",
                   duration=body.duration)
          .with_position(lambda t: (1920 - int(t*120), 1040)))

CompositeVideoClip([body, lower, title, logo, ticker]) \
    .write_videofile("news.mp4", codec="libx264", fps=30, bitrate="8000k")
```

### 2. Karaoke bouncing-ball text

```python
from moviepy import AudioFileClip, ColorClip, TextClip, ImageClip, CompositeVideoClip
import numpy as np

WORDS = [("Hello",   0.0, 1.0),
         ("moviepy", 1.0, 2.5),
         ("world",   2.5, 4.0)]

audio = AudioFileClip("song.mp3").subclipped(0, 4)
bg = ColorClip((1280, 720), (10, 10, 40), duration=4).with_audio(audio)

def ball(t):
    # bounce with a 0.25s period
    return 640 - 40, 360 + int(30 * abs(np.sin(t * np.pi * 4)))
ball_clip = (ColorClip((80, 80), (255, 200, 0), duration=4)
             .with_position(ball))

words = [
    TextClip(text=w, font_size=90, color="white", font="Arial",
             duration=end - start).with_start(start).with_position(("center", 250))
    for w, start, end in WORDS
]

CompositeVideoClip([bg, ball_clip, *words]) \
    .write_videofile("karaoke.mp4", codec="libx264", fps=30)
```

### 3. Data-viz animated chart from CSV

```python
import numpy as np, pandas as pd
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip, AudioFileClip

df = pd.read_csv("timeseries.csv")          # columns: t, value
T = float(df["t"].max())
values = df.set_index("t")["value"].to_dict()

def make_frame(t):
    img = Image.new("RGB", (1280, 720), "white")
    d = ImageDraw.Draw(img)
    mask = df["t"] <= t
    pts = [(int(40 + 1200 * (x / T)),
            int(680 - 600 * (v / df["value"].max())))
           for x, v in zip(df["t"][mask], df["value"][mask])]
    if len(pts) >= 2:
        d.line(pts, fill=(0, 120, 200), width=4)
    d.text((40, 20), f"t = {t:0.2f}", fill="black")
    return np.array(img)

VideoClip(make_frame, duration=T).with_fps(30) \
    .write_videofile("chart.mp4", codec="libx264", fps=30)
```

### 4. Slideshow from photos with Ken Burns pan/zoom

```python
from moviepy import ImageClip, concatenate_videoclips
from pathlib import Path

def ken_burns(path, duration=4, zoom_from=1.0, zoom_to=1.1):
    clip = ImageClip(str(path), duration=duration).resized(height=1080)
    return clip.resized(lambda t: zoom_from + (zoom_to - zoom_from) * (t / duration)) \
               .with_position("center")

clips = [ken_burns(p) for p in sorted(Path("photos").glob("*.jpg"))]
concatenate_videoclips(
    [c.with_fadein(0.5).with_fadeout(0.5) for c in clips],
    method="compose"
).write_videofile("slideshow.mp4", codec="libx264", fps=30)
```

## Gotchas (reference level)

- `write_videofile` silently falls back to the `imageio-ffmpeg` bundled binary if `ffmpeg` is not on PATH. To force a specific ffmpeg, set `IMAGEIO_FFMPEG_EXE=/path/to/ffmpeg` before importing MoviePy.
- `CompositeVideoClip(size=...)` is required if no clip in the list has a definite size (e.g. all TextClips).
- `concatenate_videoclips(method="chain")` silently drops audio if one clip has no audio track — use `method="compose"` or normalize audio beforehand.
- Mask clips must be grayscale in `[0, 1]` float; passing uint8 produces black output.
- `image_transform` is called on every frame. Keep it numpy-vectorized; a Python `for y in range(h): for x in range(w): ...` loop will halve your FPS.
- `with_position(lambda t: (x(t), y(t)))` is the recommended API for animated positions — don't mutate `clip.pos` directly.
- `clip.close()` is important for `VideoFileClip` — the underlying ffmpeg subprocess leaks file descriptors if you don't close. Use `with VideoFileClip(...) as c:` in production code.
- Releasing in 2.x, the `moviepy.editor` module no longer exists. Monkey-patches like `moviepy.editor.VideoFileClip = ...` will `ImportError`.
