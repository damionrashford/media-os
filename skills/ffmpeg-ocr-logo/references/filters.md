# ffmpeg-ocr-logo — filter reference

Deep reference for every filter surfaced by this skill. Verified against the
FFmpeg 7.x filter manual.

## 1. Build-flag requirements

| Filter       | configure flag                 | FFmpeg since | Common availability                           |
|--------------|--------------------------------|--------------|-----------------------------------------------|
| `ocr`        | `--enable-libtesseract`        | 2.8          | Homebrew default yes; static releases **no**  |
| `find_rect`  | (core)                         | 3.4          | Always                                        |
| `cover_rect` | (core)                         | 3.4          | Always                                        |
| `delogo`     | `--enable-gpl`                 | 0.9          | GPL builds only (almost all of them)          |
| `removelogo` | (core)                         | 1.0          | Always                                        |
| `qrencode`   | `--enable-libqrencode`         | 7.1          | **Rare** — almost no distro ships this        |
| `quirc`      | `--enable-libquirc`            | 7.1          | **Rare**                                      |

Verify with:

```bash
ffmpeg -hide_banner -filters | grep -E "ocr|find_rect|cover_rect|delogo|removelogo|qrencode|quirc"
```

or `uv run scripts/ocrlogo.py check-build`.

## 2. Tesseract tessdata paths per OS

The `datapath=` option on `ocr` points to a **directory** (not a file) that
contains language files named `<lang>.traineddata`.

| OS / installer                          | Default tessdata path                          |
|-----------------------------------------|------------------------------------------------|
| Debian / Ubuntu (`apt install tesseract-ocr`) | `/usr/share/tesseract-ocr/<ver>/tessdata/` or `/usr/share/tessdata/` |
| Fedora / RHEL (`dnf install tesseract`) | `/usr/share/tesseract/tessdata/`               |
| Arch (`pacman -S tesseract`)            | `/usr/share/tessdata/`                         |
| macOS Homebrew, Intel                   | `/usr/local/share/tessdata/`                   |
| macOS Homebrew, Apple Silicon           | `/opt/homebrew/share/tessdata/`                |
| Windows (UB-Mannheim installer)         | `C:\Program Files\Tesseract-OCR\tessdata\`     |
| Docker `tesseractshadow/tesseract4re`   | `/usr/share/tesseract-ocr/4.00/tessdata/`      |

Common language codes: `eng`, `deu`, `fra`, `spa`, `ita`, `nld`, `por`, `rus`,
`jpn`, `kor`, `chi_sim`, `chi_tra`, `ara`, `hin`. Install extras:

- Homebrew: `brew install tesseract-lang`
- Debian: `apt install tesseract-ocr-<lang>`
- Download direct: https://github.com/tesseract-ocr/tessdata_best

`ocr` also respects the env var `TESSDATA_PREFIX` if `datapath=` is unset.

## 3. `ocr` — option table

| Option       | Type   | Default   | Notes                                                        |
|--------------|--------|-----------|--------------------------------------------------------------|
| `datapath`   | string | build-set | Tessdata directory. Must end in `/`.                         |
| `language`   | string | `eng`     | Must match a `<lang>.traineddata` file in `datapath`.        |
| `whitelist`  | string | (none)    | Only these characters will be recognized. Example: `0123456789:` |
| `blacklist`  | string | (none)    | These characters are never returned.                         |

Emits per-frame metadata:

- `lavfi.ocr.text` — the recognized string (may contain `\n`-escaped newlines)
- `lavfi.ocr.confidence` — space-separated per-word confidence values (0–100)

## 4. `delogo` — option table

| Option | Type | Default | Notes                                       |
|--------|------|---------|---------------------------------------------|
| `x`    | int  | —       | Top-left X of logo rect. Required.          |
| `y`    | int  | —       | Top-left Y of logo rect. Required.          |
| `w`    | int  | —       | Width. Required, >0.                        |
| `h`    | int  | —       | Height. Required, >0.                       |
| `band` | int  | 1       | How many pixels outside the rect to blend.  |
| `show` | 0/1  | 0       | 1 draws a green outline for tuning.         |

Interpolation is a simple gradient from the 1-pixel ring outside the rect.
No metadata emitted.

## 5. `removelogo` — option table

| Option         | Type   | Notes                                                      |
|----------------|--------|------------------------------------------------------------|
| `filename`, `f`| path   | Alpha-mask PNG. Same resolution as video. Required.        |

**Mask convention:** white (255) = this pixel is part of the logo, remove it;
black (0) = keep as-is. Inverted from typical alpha usage.

Build the mask:

```bash
# 1. Capture a black frame showing the logo:
ffmpeg -i in.mp4 -ss 5 -vframes 1 sample.png
# 2. Threshold + erode with ImageMagick:
magick sample.png -threshold 50% -morphology Erode Diamond:1 mask.png
```

## 6. `find_rect` — option table

| Option       | Type  | Default | Notes                                                                  |
|--------------|-------|---------|------------------------------------------------------------------------|
| `object`     | path  | —       | Reference image. Must be **gray8** (`.pgm` or 8-bit gray PNG). Required. |
| `threshold`  | float | 0.5     | 0-1. 0.01 = exact match only (strict). 0.99 = almost anything.         |
| `mipmaps`    | int   | 3       | Gaussian pyramid depth. Higher = faster, coarser.                      |
| `xmin, ymin` | int   | 0       | Top-left of search rectangle.                                          |
| `xmax, ymax` | int   | full    | Bottom-right of search rectangle.                                      |
| `discard`    | 0/1   | 0       | 1 = drop frames with no match.                                         |

Emits per-frame metadata **when a match is found**:

- `lavfi.rect.x`, `lavfi.rect.y` — top-left of the found rectangle
- `lavfi.rect.w`, `lavfi.rect.h` — dimensions
- `lavfi.rect.score` — match confidence

Convert a reference image to gray8:

```bash
magick ref.png -colorspace gray ref.pgm
# or
ffmpeg -i ref.png -pix_fmt gray -y ref.pgm
```

## 7. `cover_rect` — option table

| Option  | Type   | Default | Notes                                                       |
|---------|--------|---------|-------------------------------------------------------------|
| `cover` | path   | (none)  | Image to patch over the rect. Must be **yuv420** (`.jpg`).  |
| `mode`  | enum   | `blur`  | `cover` = use the image, `blur` = interpolate surrounding.  |

`cover_rect` reads `lavfi.rect.*` from upstream. **Must be in the same
comma-chained filter chain as `find_rect`.**

## 8. `qrencode` — option table (abridged)

| Option                       | Default | Notes                                                 |
|------------------------------|---------|-------------------------------------------------------|
| `text`                       | (none)  | Payload. If empty/unset, no QR is drawn.              |
| `textfile`                   | (none)  | Read payload from file.                               |
| `qrcode_width`, `q`          | auto    | Expression. Can reference `w`, `h`, `dar`, `sar`, `t`. |
| `padded_qrcode_width`, `Q`   | = `q`   | With quiet-zone border.                               |
| `x`, `y`                     | 0, 0    | Position expressions (same DSL as `overlay`).          |
| `case_sensitive`, `cs`       | 1       | 0 to allow lowercase encoding optimizations.          |
| `level`, `l`                 | `L`     | Error correction: `L`<`M`<`Q`<`H`.                    |
| `expansion`                  | `normal`| `none` disables template expansion in `text`.          |
| `background_color`, `bc`     | white   | Any ffmpeg color name or `#RRGGBB@A`.                  |
| `foreground_color`, `fc`     | black   | Same syntax.                                           |

## 9. `quirc` — emitted metadata

Per frame, only set when ≥1 QR code is found:

- `lavfi.quirc.count` — number of QR codes
- `lavfi.quirc.<N>.payload` — decoded text
- `lavfi.quirc.<N>.corner.<M>.x`, `.y` — corners, `M` ∈ {0,1,2,3}
  - **Note:** the official docs (and some builds) spell the `y` version
    `coreer.M.y` (sic). Match both spellings when parsing.

## 10. Metadata parsing regexes

`metadata=mode=print` emits:

```
frame:N        pts:P       pts_time:T
lavfi.<filter>.<key>=<value>
lavfi.<filter>.<key>=<value>
...
```

Python patterns:

```python
import re

FRAME_RE = re.compile(r"^frame:(\d+)\s+pts:(\d+)\s+pts_time:([\d.]+)$", re.M)
OCR_TEXT_RE = re.compile(r"^lavfi\.ocr\.text=(.*)$", re.M)
OCR_CONF_RE = re.compile(r"^lavfi\.ocr\.confidence=(.*)$", re.M)
RECT_RE = re.compile(r"^lavfi\.rect\.(x|y|w|h|score)=([\d.]+)$", re.M)
QR_COUNT_RE = re.compile(r"^lavfi\.quirc\.count=(\d+)$", re.M)
QR_PAYLOAD_RE = re.compile(r"^lavfi\.quirc\.(\d+)\.payload=(.*)$", re.M)
```

Multi-line OCR output is escaped as `\n` inside the value; unescape with
`value.encode().decode("unicode_escape")`.

## 11. Logo-removal decision tree

```
Do you know the exact rectangle coordinates? ─────────► delogo
        │ no
        ▼
Do you have a binary mask PNG the same size as the video? ─► removelogo
        │ no
        ▼
Do you have a reference image of the object? ─► find_rect + cover_rect
        │ no
        ▼
Fall back to: scenedetect-style analysis + manual crop+blur, or an external
ML detector (not supported by this skill).
```

Quality vs. effort:

| Approach          | Effort     | Quality on solid logo | Quality on textured logo |
|-------------------|------------|------------------------|---------------------------|
| `delogo`          | trivial    | good                   | poor                      |
| `removelogo`      | medium     | excellent              | fair                      |
| `find_rect+cover` | medium     | good (+ covers motion) | good                      |
| ML detector       | high       | excellent              | excellent                 |

## 12. Recipe book

### 12.1 Auto-blur license plates at a consistent location

If the plate is at a known rect:

```bash
ffmpeg -i dashcam.mp4 \
  -vf "boxblur=luma_radius=20:luma_power=1:enable='between(t,0,9999)':x=600:y=400:w=200:h=60" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

If the plate has a consistent rectangular shape moving around, use a reference
image of the plate outline (gray8) and blur on find-cover:

```bash
magick plate_ref.png -colorspace gray plate_ref.pgm
ffmpeg -i dashcam.mp4 \
  -vf "find_rect=object=plate_ref.pgm:threshold=0.5,cover_rect=mode=blur" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

### 12.2 Live-TV station bug removal

Preview the rectangle coordinates with `show=1`, then run final:

```bash
# Preview in ffplay
ffplay -vf "delogo=x=1720:y=40:w=180:h=80:show=1" live.mp4

# Render final with band=2 for clean edges
ffmpeg -i live.mp4 \
  -vf "delogo=x=1720:y=40:w=180:h=80:band=2" \
  -c:v libx264 -crf 20 -c:a copy clean.mp4
```

### 12.3 Read a burned-in sports scoreboard every second

```bash
ffmpeg -i game.mp4 \
  -vf "crop=400:80:1500:980,fps=1,eq=contrast=1.4,scale=iw*2:ih*2:flags=lanczos,\
ocr=datapath=/usr/local/share/tessdata/:language=eng:whitelist='0123456789 :-',\
metadata=mode=print:file=scores.txt" \
  -an -f null -
```

Crop first (scoreboard region), sample 1fps, contrast-boost, 2× upscale, then
OCR with a digit+separator whitelist. Parse `scores.txt` with the OCR regex
above.

### 12.4 QR-watermark every encode with a job id

```bash
JOB="job-$(date +%s)"
ffmpeg -i master.mov \
  -vf "qrencode=text='$JOB':q=w*0.12:x=w-q-16:y=h-q-16:level=Q:\
foreground_color=black@0.9:background_color=white@0.9" \
  -c:v libx264 -crf 20 -c:a copy "out_${JOB}.mp4"
```

Then verify by decoding:

```bash
ffmpeg -i "out_${JOB}.mp4" -vf "fps=1,quirc,metadata=mode=print" -an -f null - \
  2>&1 | grep payload
```

### 12.5 Detect when a logo appears / disappears (for ad-break detection)

```bash
ffmpeg -i broadcast.ts \
  -vf "find_rect=object=network_bug.pgm:threshold=0.4,metadata=mode=print:file=presence.log" \
  -an -f null -
```

Each line `lavfi.rect.score=0.xxx` marks a match. Gaps in the log correspond
to commercial breaks (bug missing). Post-process the timestamps to derive
ad-break boundaries.

### 12.6 Extract all visible timestamps from a surveillance camera

Many cams overlay `YYYY-MM-DD HH:MM:SS`. Crop + OCR with a tight whitelist:

```bash
ffmpeg -i cam.mp4 \
  -vf "crop=480:36:1440:0,fps=1,ocr=language=eng:whitelist='0123456789- :',\
metadata=mode=print:file=timestamps.txt" \
  -an -f null -
awk -F= '/^lavfi.ocr.text=/ {print $2}' timestamps.txt
```

## 13. Fallbacks when a build flag is missing

| Missing filter | Fallback                                                          |
|----------------|-------------------------------------------------------------------|
| `ocr`          | Extract frames (see `ffmpeg-frames-images`), run `tesseract` CLI. |
| `quirc`        | Extract frames, run `zbarimg <file>.png`.                         |
| `qrencode`     | `qrencode -o qr.png '<payload>'`, then overlay with `overlay` filter. |
| `delogo`       | `drawbox` + `boxblur` with `enable='between(t,...)'`.              |
| `removelogo`   | `maskedmerge` from `ffmpeg-compose-mask` skill.                    |

## 14. Interop notes

- All filters in this skill are **re-encode only** — `-c copy` will not work.
- `ocr` and `quirc` produce metadata per decoded frame; pair with `fps=N` to
  throttle cost. One full-res 4K frame per `ocr` invocation can take 100–500ms
  depending on Tesseract language model.
- `find_rect` scales O(W·H · mipmaps²) — reduce search area with
  `xmin/ymin/xmax/ymax` on HD/4K video.
- `qrencode` renders in RGB; if your pipeline is `yuv420p`, ffmpeg will insert
  an auto-convert. For hardware-accelerated pipelines, insert an explicit
  `format=yuv420p` after `qrencode`.
- `delogo` edges can shimmer frame-to-frame. For cleaner results on static
  logos, pre-convert to a reference mask and use `removelogo` instead.
