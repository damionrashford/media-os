---
name: ffmpeg-ocr-logo
description: >
  OCR, logo detection, and rectangle operations with ffmpeg: ocr (Tesseract inside ffmpeg), find_rect (find a reference rectangle), cover_rect (hide it), delogo and removelogo (station logo removal), qrencode (generate QR), quirc (decode QR from frames). Use when the user asks to read text from video frames, detect a recurring logo, hide or blur a TV station watermark, find repeated rectangles, extract visible text with OCR, or embed and decode a QR code inside video.
argument-hint: "[input]"
---

# Ffmpeg Ocr Logo

**Context:** $ARGUMENTS

OCR, logo removal, and QR operations inside ffmpeg are **filter-graph** operations. They run on the decoded frame, emit results as frame metadata under `lavfi.<filter>.*`, and/or modify pixels in place. All are **re-encode only** — you cannot stream-copy through any of these filters.

Several of the filters in this skill are **build-flag gated** — `ocr` needs `--enable-libtesseract`, `quirc` needs `--enable-libquirc`, and `qrencode` needs `--enable-libqrencode`. Many static / minimal ffmpeg builds ship without these. **Always check the build first** (Step 1) before writing a pipeline.

## Quick start

- **Read text from video:** → Step 1 (check `ocr`) → Step 2 (pick "OCR") → Step 3
- **Hide a known rectangle (e.g. bug/logo at fixed coords):** → Step 2 (pick "delogo") → Step 3
- **Remove a logo with an alpha mask PNG:** → Step 2 (pick "removelogo") → Step 3
- **Find and hide a recurring graphic (reference image):** → Step 2 (pick "find-rect + cover-rect") → Step 3
- **Decode QR codes from frames:** → Step 1 (check `quirc`) → Step 2 (pick "QR decode") → Step 3
- **Burn a QR code overlay into video:** → Step 1 (check `qrencode`) → Step 2 (pick "QR encode") → Step 3

## When to use

- Extracting burned-in text (lower-thirds, scoreboard tickers, timestamps) live from a stream.
- Removing a broadcaster bug / channel logo from a captured feed.
- Blurring license plates or faces at a consistent screen location.
- Embedding / reading QR watermarks for pipeline tracing or ad-insertion cues.

**Not this skill:** Pre-recorded high-accuracy OCR — extract frames with `ffmpeg-frames-images` then run `tesseract` directly for better accuracy. True object detection / face detection — use an external ML model. Arbitrary watermark removal without a known shape — ffmpeg has no generic inpainting.

## Step 1 — Check your ffmpeg build

Run once before building any pipeline:

```bash
ffmpeg -hide_banner -filters 2>/dev/null | grep -E "ocr|find_rect|cover_rect|delogo|removelogo|qrencode|quirc"
```

Or use the helper:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocrlogo.py check-build
```

Expected results:

| Filter | Build flag required | Usually present? |
|---|---|---|
| `ocr` | `--enable-libtesseract` | Homebrew yes; static builds often no |
| `find_rect` | *(core)* | Yes |
| `cover_rect` | *(core)* | Yes |
| `delogo` | *(core, GPL — `--enable-gpl`)* | Yes on GPL builds |
| `removelogo` | *(core)* | Yes |
| `qrencode` | `--enable-libqrencode` | **Rare**, FFmpeg 7.1+ only |
| `quirc` | `--enable-libquirc` | **Rare**, FFmpeg 7.1+ only |

If a filter is missing, either rebuild ffmpeg with the flag or fall back to the OS tool (`tesseract`, `zbarimg`, `qrencode` CLI) on extracted frames.

## Step 2 — Pick the operation

### A. OCR — read text from frames

```bash
ffmpeg -i in.mp4 \
  -vf "ocr=datapath=/usr/local/share/tessdata/:language=eng,metadata=mode=print:file=ocr.txt" \
  -an -f null -
```

- `datapath` is the **Tesseract tessdata directory** (contains `eng.traineddata` etc.). If omitted, ffmpeg uses Tesseract's compile-time default.
- `metadata=mode=print:file=ocr.txt` dumps `lavfi.ocr.text` for every frame. Without it, results stay in memory and are lost.
- Add `-an` to skip audio, `-f null -` to discard video output.
- Whitelist / blacklist characters via `whitelist=0123456789:` (useful for clocks) and `blacklist=...`.

**OCR a single frame at 10s:**

```bash
ffmpeg -ss 10 -i in.mp4 -vframes 1 \
  -vf "ocr=datapath=/usr/local/share/tessdata/,metadata=mode=print" \
  -f null - 2>&1 | grep "lavfi.ocr.text"
```

### B. delogo — erase a known rectangle

```bash
ffmpeg -i in.mp4 \
  -vf "delogo=x=10:y=10:w=200:h=80:show=0" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

- `x,y` is the **top-left** of the rectangle; `w,h` its size.
- `show=1` draws a green outline — use when tuning coordinates, then set back to `0`.
- The rectangle is filled by interpolating the 1-pixel ring just outside it. Works well on solid colors, **poorly on textured** or semi-transparent logos.
- If edges bleed, extend the clearing zone via `band=2` (default 1).

### C. removelogo — erase via alpha-mask PNG

```bash
ffmpeg -i in.mp4 \
  -vf "removelogo=logo_mask.png" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

- The mask must be the **same resolution as the video**.
- **White (255) = logo pixel to remove; Black (0) = keep untouched.** This is opposite of the typical alpha convention.
- Build the mask by screen-grabbing a black frame showing the logo, thresholding in GIMP/ImageMagick, then eroding once or twice.

### D. find-rect + cover-rect — find a reference image and hide it

```bash
# ref.pgm must be gray8 (convert via ImageMagick: magick ref.png -colorspace gray ref.pgm)
ffmpeg -i in.mp4 \
  -vf "find_rect=object=ref.pgm:threshold=0.3,cover_rect=cover=blank.jpg:mode=cover" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

- `find_rect` scans each frame for the reference sub-image via cross-correlation. The matched rectangle's position is written to `lavfi.rect.{x,y,w,h,score}`.
- `cover_rect` reads those metadata entries from its upstream filter — **they must be in the same filter chain**.
- `cover=` image must be **yuv420** (e.g. a plain `.jpg`). Use `mode=blur` for a soft blur instead of an image patch:

```bash
find_rect=object=ref.pgm:threshold=0.3,cover_rect=mode=blur
```

- Tune `threshold` (0.01 = exact match, 0.99 = almost anything). Start at 0.3–0.5.
- Restrict search area with `xmin/ymin/xmax/ymax` for speed.
- `discard=1` drops frames where no match was found (useful when you only want the detection hits).

### E. QR decode (`quirc`)

```bash
ffmpeg -i in.mp4 \
  -vf "quirc,metadata=mode=print" \
  -an -f null - 2>&1 | grep "lavfi.quirc"
```

Emitted metadata per frame with a detected QR:

- `lavfi.quirc.count=N` (only set if ≥ 1 found)
- `lavfi.quirc.0.payload=<decoded text>`
- `lavfi.quirc.0.corner.0.x` … `lavfi.quirc.0.corner.3.y` (four corner coords)

### F. QR encode (`qrencode`) — overlay QR on video

```bash
ffmpeg -i in.mp4 \
  -vf "qrencode=text='https://example.com':q=w*0.25:x=w-q-20:y=20:level=H" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

- `text` or `textfile` supplies the payload.
- `qrcode_width` / `q` is the rendered size (accepts expressions referencing `w`, `h`).
- `x`, `y` position the top-left corner — same expression DSL as `overlay`/`drawtext`.
- `level` is L/M/Q/H (H = most redundancy, larger code).
- `foreground_color` / `background_color` take any ffmpeg color name.

## Step 3 — Run the command and parse the metadata

When you use `metadata=mode=print`, ffmpeg emits a block per frame to stdout (or the file set by `file=`):

```
frame:42   pts:42000    pts_time:1.68
lavfi.ocr.text=Hello World
lavfi.ocr.confidence=87 91 93
```

Parse with regex:

```python
import re
OCR_RE  = re.compile(r"^lavfi\.ocr\.text=(.*)$", re.M)
QR_RE   = re.compile(r"^lavfi\.quirc\.(\d+)\.payload=(.*)$", re.M)
RECT_RE = re.compile(r"^lavfi\.rect\.(x|y|w|h|score)=([\d.]+)$", re.M)
```

Or use the helper script:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocrlogo.py ocr --input in.mp4 --output ocr.txt
uv run ${CLAUDE_SKILL_DIR}/scripts/ocrlogo.py qr-decode --input in.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/ocrlogo.py find-cover --input in.mp4 --output o.mp4 \
     --reference logo.pgm --cover blur
```

## Available scripts

- **`scripts/ocrlogo.py`** — subcommands: `check-build`, `ocr`, `delogo`, `removelogo`, `find-cover`, `qr-decode`, `qr-encode`. Stdlib only. Supports `--dry-run` and `--verbose`.

## Reference docs

- Read [`references/filters.md`](references/filters.md) for full option tables, per-OS tessdata paths, regex parsing patterns, a logo-removal decision tree, and recipe book (plate blur, live-TV logo removal, QR watermark).

## Gotchas

- **`ocr` needs `--enable-libtesseract`.** Static / minimal ffmpeg builds (including several Homebrew bottles and the official `ffmpeg.org` static releases) **don't have it**. Check with `ffmpeg -filters | grep ocr` first. On macOS use `brew install ffmpeg` (full, not `ffmpeg@...`-slim); on Linux check your distro package or build from source.
- **`datapath` is the tessdata directory, not a file.** It points at a folder that contains `<lang>.traineddata`. Defaults:
  - Linux (apt): `/usr/share/tessdata/` or `/usr/share/tesseract-ocr/<ver>/tessdata/`
  - macOS Homebrew: `/usr/local/share/tessdata/` (Intel) or `/opt/homebrew/share/tessdata/` (Apple Silicon)
  - Windows: `C:/Program Files/Tesseract-OCR/tessdata/`
- **Language files must match the `language` option.** `language=deu` requires `deu.traineddata` in the datapath. Install extras via `brew install tesseract-lang` / `apt install tesseract-ocr-deu`.
- **OCR accuracy drops hard on compressed video.** Sample at high bitrate, pre-upscale (`scale=iw*2:ih*2`), or pre-threshold (`eq=contrast=1.5,curves=preset=increase_contrast`). For production OCR on a library, extract frames (`ffmpeg-frames-images`) and run `tesseract` directly — **far more accurate** than ffmpeg's in-graph ocr filter.
- **`ocr` is best for LIVE or streaming** use cases where you want text as frame metadata in a single pass (cropdetect-style). Don't use it for one-off transcription.
- **`metadata=mode=print` format** prints a `frame:N pts:M pts_time:T` header then `lavfi.ocr.text="..."` lines. Multi-line OCR output gets escaped with `\n`. Parse with a state machine or the regex pattern in Step 3.
- **`delogo` works best on solid-color bugs** (station logos, simple graphics). Struggles on textured, semi-transparent, or animated logos — the interpolation visibly smears.
- **`removelogo` mask convention is inverted from intuition** — white pixels mean "this is the logo, remove it," black means "keep." The mask must be the **exact resolution** of the video.
- **`find_rect` needs a gray8 reference** (`.pgm` or 8-bit grayscale `.png`). Convert with `magick ref.png -colorspace gray ref.pgm` or `ffmpeg -i ref.png -pix_fmt gray -y ref.pgm`.
- **`cover_rect`'s cover image must be yuv420.** Use `.jpg` or convert via `ffmpeg -i cover.png -pix_fmt yuv420p cover.jpg`.
- **`find_rect` + `cover_rect` must share a filter chain.** They communicate via frame metadata (`lavfi.rect.*`); a `-filter_complex` with separate branches breaks the hand-off. Chain them with a comma.
- **`find_rect` finds at most ONE instance per frame.** Multiple logos of the same shape on one frame need multiple passes or a different approach.
- **`threshold` semantics are inverted from what you'd guess** — `0.01` means "only exact matches" (strict), `0.99` means "almost anything matches" (loose). Start at 0.3.
- **`quirc` / `qrencode` are rare** — both require explicit build flags (`--enable-libquirc`, `--enable-libqrencode`) and only landed in FFmpeg 7.1. On older or slimmer builds, decode with `zbarimg` and encode with the `qrencode` CLI on extracted frames.
- **QR metadata key misspelling:** the official docs show `lavfi.quirc.N.coreer.M.y` (sic — this is actually `corner` in the source). Match both spellings defensively if parsing.
- **`qrencode` defaults to black-on-white** and top-left placement. For watermarking a bright scene, swap to `foreground_color=white:background_color=black` and scale down to 10–15% frame width.
- **All filters in this skill require a re-encode** — you cannot `-c copy` through them. Pair with a reasonable `-crf` / `-preset` in the encoder call.

## Examples

### Example 1 — OCR a news ticker every second

```bash
ffmpeg -i news.mp4 \
  -vf "fps=1,ocr=datapath=/usr/local/share/tessdata/:language=eng,metadata=mode=print:file=ticker.txt" \
  -an -f null -
grep "^lavfi.ocr.text=" ticker.txt
```

`fps=1` samples 1 frame per second before OCR to cut cost by 24–30x.

### Example 2 — Remove a broadcaster bug in the top-right

First locate the bug coordinates with `show=1`:

```bash
ffplay -vf "delogo=x=1720:y=40:w=180:h=80:show=1" live.mp4
```

Then render the cleaned file:

```bash
ffmpeg -i live.mp4 \
  -vf "delogo=x=1720:y=40:w=180:h=80" \
  -c:v libx264 -crf 20 -c:a copy clean.mp4
```

### Example 3 — Auto-blur a recurring reference object

Wherever the reference image appears, blur it.

```bash
# Prepare gray8 reference
magick ref.png -colorspace gray ref.pgm

# Auto-blur
ffmpeg -i surveil.mp4 \
  -vf "find_rect=object=ref.pgm:threshold=0.4,cover_rect=mode=blur" \
  -c:v libx264 -crf 20 -c:a copy blurred.mp4
```

### Example 4 — Decode QR codes once per second

```bash
ffmpeg -i tracer.mp4 -vf "fps=1,quirc,metadata=mode=print:file=qr.log" -an -f null -
grep "payload=" qr.log
```

### Example 5 — Embed a tracking QR code bottom-right

```bash
ffmpeg -i in.mp4 \
  -vf "qrencode=text='job-id=12345':q=128:x=w-q-20:y=h-q-20:level=Q:\
foreground_color=black:background_color=white@0.85" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

## Troubleshooting

### Error: `No such filter: 'ocr'`

**Cause:** Your ffmpeg build doesn't include libtesseract.
**Solution:** Check with `ffmpeg -filters | grep ocr`. Reinstall (`brew reinstall ffmpeg` — Homebrew's default is full-featured) or build from source with `--enable-libtesseract`. Alternatively, extract frames with `ffmpeg-frames-images` and run `tesseract` directly.

### Error: `Failed to init ocr (Failed loading language 'eng')`

**Cause:** Tessdata missing or `datapath` wrong.
**Solution:** Verify the folder exists and contains `eng.traineddata`: `ls /usr/local/share/tessdata/`. On macOS also install `brew install tesseract`. Pass the correct path via `datapath=`.

### OCR output is gibberish / empty

**Cause:** Source video too compressed, text too small, or font antialiased too aggressively.
**Solution:** Sample at higher resolution, pre-scale (`scale=iw*2:ih*2:flags=lanczos`), pre-contrast (`eq=contrast=1.4`), or crop to the text region first (`crop=W:H:X:Y`). For best accuracy, extract frames and run `tesseract` standalone.

### `delogo` leaves a visible smear

**Cause:** Logo extends beyond the specified rectangle, or is textured.
**Solution:** Widen `w`/`h` by 4–8 pixels, then set `band=2`. For textured logos try `removelogo` with a mask PNG instead.

### `removelogo: Mask file does not match video size`

**Cause:** Mask PNG resolution differs from the video stream resolution.
**Solution:** Resize the mask to match: `magick mask.png -resize 1920x1080! mask_fixed.png`. Must be an exact match.

### `find_rect` never matches

**Cause:** Reference image not in gray8, or threshold too strict.
**Solution:** Confirm gray8: `ffprobe -show_streams ref.pgm | grep pix_fmt` should say `gray`. Relax threshold (0.5 → 0.7). Reduce the reference to a tight crop of the logo — extra border content kills correlation score.

### `No such filter: 'quirc'` / `'qrencode'`

**Cause:** ffmpeg built without libquirc / libqrencode.
**Solution:** Confirm with `ffmpeg -filters | grep -E 'quirc|qrencode'`. Either rebuild with `--enable-libquirc --enable-libqrencode` (FFmpeg 7.1+ only), or fall back to `zbarimg` (decode) / `qrencode` CLI (encode) on extracted frames.
