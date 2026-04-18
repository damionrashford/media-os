---
name: media-imagemagick
description: >
  Image manipulation with ImageMagick (magick / convert / mogrify / composite / identify / montage): resize, crop, rotate, convert between 200+ formats, compose layers with alpha, add text, apply effects, batch process folders, color operations, PDF/PSD/HEIC/AVIF/JXL support. Use when the user asks to process images, resize photos, convert image formats, composite layers, build a photo montage, add text to an image, apply a filter, or batch convert an image folder.
argument-hint: "[operation]"
---

# Media Imagemagick

**Context:** $ARGUMENTS

## Quick start

- **Resize / thumbnail:** → Step 2 `resize`
- **Change format (PNG→JPG/WebP/HEIC):** → Step 2 `convert`
- **Overlay logo / watermark:** → Step 2 `composite`
- **Contact-sheet grid:** → Step 2 `montage`
- **PDF → PNGs, GIF → frames:** → Step 2 format-specific recipes
- **Probe dimensions / metadata:** → Step 4 `identify`
- **Batch a folder:** → Step 2 `mogrify` / `batch-resize`

## When to use

- Resize / compress / re-encode one image or a whole folder.
- Convert between JPEG, PNG, WebP, HEIC, AVIF, JXL, TIFF, GIF, BMP, ICO, PDF, PSD.
- Compose / watermark / annotate / make contact sheets or social-media multi-size bundles.
- Script-level image plumbing where Photoshop-class apps are overkill and plain Python PIL is too limited.

Not for: raster painting (use Krita), RAW development (use darktable/RawTherapee), video (use ffmpeg — see `ffmpeg-*` skills).

## Step 1 — Install + verify

```bash
# macOS
brew install imagemagick

# Debian/Ubuntu
sudo apt install imagemagick

# Verify. On v7 the command is `magick`. v6 uses `convert`/`mogrify`/`composite` as separate binaries.
magick -version
magick -list format | head        # enumerate supported formats on this build
magick -list format | grep -Ei '^ *(HEIC|AVIF|JXL|WEBP) '   # confirm optional formats
```

- v7+ is `magick <subcommand>` (e.g. `magick convert`, `magick identify`, `magick mogrify`, `magick composite`, `magick montage`, `magick compare`). Bare `convert` still works on v7 (aliased), but ALWAYS prefer `magick` — `convert` also collides with a Windows built-in.
- HEIC / AVIF / JXL support depends on the build shipping with libheif / libavif / libjxl. If missing, rebuild from source or use a Homebrew tap / apt backport that bundles them.
- ImageMagick ships with a security policy at `/etc/ImageMagick-7/policy.xml` (or `/opt/homebrew/etc/ImageMagick-7/policy.xml` on macOS) that by default can block `PDF`, `MVG`, `LABEL`, `HTTPS`, and set low memory/disk limits. If you see `not authorized` errors, edit that file or run with `-define registry:temporary-path=...` / `--security-policy` override.

## Step 2 — Pick your operation

All recipes below are v7 `magick` form. Chain multiple ops by listing them in order; ImageMagick applies left-to-right.

### Format conversion

```bash
magick in.png out.jpg                          # format decided by extension
magick in.heic out.webp
magick in.tif -quality 85 out.jpg              # JPEG quality 85
magick in.png -define webp:lossless=true out.webp
magick in.jpg -define heic:speed=2 out.heic    # slower = smaller
magick in.jpg -strip -interlace Plane out.jpg  # strip EXIF + progressive JPEG (web-friendly)
```

### Resize / thumbnail / fit

Geometry suffix decides behavior — see `references/imagemagick.md` for the full matrix.

```bash
magick in.jpg -resize 1920x1080 out.jpg                    # fit inside, keep aspect
magick in.jpg -resize 1920x1080! out.jpg                   # force exact, ignore aspect (distorts)
magick in.jpg -resize 1920x1080^ -gravity center -extent 1920x1080 out.jpg  # fill + center-crop
magick in.jpg -resize '1920x1080>' out.jpg                 # shrink only if larger
magick in.jpg -resize 50%     out.jpg                      # percent
magick in.jpg -thumbnail 200x200 out.jpg                   # -thumbnail = -resize + -strip, much faster
```

### Crop / rotate / orient

```bash
magick in.jpg -crop 800x600+100+50 +repage out.jpg         # WxH+X+Y from top-left; +repage clears virtual canvas
magick in.jpg -rotate 90 out.jpg
magick in.jpg -rotate '90>' out.jpg                        # only if wider than tall (quirk: use sparingly)
magick in.jpg -auto-orient out.jpg                         # apply EXIF Orientation and clear tag
magick in.jpg -flop out.jpg                                # horizontal mirror
magick in.jpg -flip out.jpg                                # vertical mirror
```

### Text / annotate

```bash
magick in.jpg -font DejaVu-Sans -pointsize 72 -fill white \
              -gravity SouthEast -annotate +20+20 '© 2026' out.jpg
magick in.jpg -pointsize 48 -fill 'rgba(255,255,255,0.8)' \
              -draw "text 10,100 'Hello'" out.jpg
magick -list font | head              # discover available fonts (fontconfig on Linux, system on macOS)
```

Unicode glyphs need a font that ships them — Arial often lacks CJK/emoji; prefer `DejaVu-Sans`, `Noto-Sans-CJK`, or `Apple-Color-Emoji` depending on the glyph set.

### Composite / overlay / watermark

```bash
magick base.png logo.png -geometry +10+10 -composite out.png        # top-left @ 10,10
magick base.png logo.png -gravity SouthEast -geometry +20+20 -composite out.png
magick base.png \( logo.png -alpha set -channel A -evaluate set 40% \) \
       -gravity SouthEast -geometry +20+20 -composite out.png        # 40% opacity watermark
```

### Montage / contact sheet

```bash
magick montage *.jpg -geometry 200x200+5+5 -tile 4x4 grid.jpg
magick montage -label '%f' *.jpg -geometry 200x200+5+5 -tile 4x4 \
               -background '#222' -fill white grid.jpg               # labeled
```

### Color / tone

```bash
magick in.jpg -modulate 110,120,100 out.jpg          # brightness, saturation, hue (100 = no change)
magick in.jpg -level 10%,90% out.jpg                 # black point / white point stretch
magick in.jpg -brightness-contrast 10x20 out.jpg     # +10 brightness, +20 contrast
magick in.jpg -colorspace Gray out.jpg               # desaturate
magick in.jpg -profile sRGB.icc out.jpg              # embed / convert ICC profile
```

### Animated GIF ↔ frames

```bash
magick in.gif -coalesce frame_%04d.png                                      # explode (keep full frames)
magick -delay 10 -loop 0 frame_*.png -layers Optimize out.gif               # assemble + optimize
```

### PDF ↔ images

```bash
magick -density 300 in.pdf page_%03d.png                 # ALWAYS put -density BEFORE -input for vector/PDF
magick page_*.png out.pdf                                # images → multi-page PDF
```

If you get `attempt to perform an operation not allowed by the security policy 'PDF'`, edit policy.xml (see Gotchas).

### In-place batch (`mogrify`)

```bash
mogrify -resize 1080 *.jpg                               # OVERWRITES originals
mogrify -path thumbs/ -resize 400x400 -quality 82 *.jpg  # safer: write into thumbs/
```

Or from Python via `scripts/image.py batch-resize`.

## Step 3 — Run

Prefer the Python wrapper for repeatable, scriptable work — it echoes the exact `magick` command and supports `--dry-run`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/image.py check
python3 ${CLAUDE_SKILL_DIR}/scripts/image.py resize --input in.jpg --output out.jpg --width 1920 --fit inside --quality 85
python3 ${CLAUDE_SKILL_DIR}/scripts/image.py batch-resize --indir photos/ --outdir thumbs/ --width 1080 --verbose
python3 ${CLAUDE_SKILL_DIR}/scripts/image.py identify --input in.jpg
```

For one-off exploration, run `magick` directly. For anything you will repeat, put it behind a subcommand in `scripts/image.py`.

## Step 4 — Verify with `identify`

```bash
magick identify in.jpg                                                # brief
magick identify -format "%w x %h  %m  Q=%Q  %[colorspace]\n" in.jpg   # scriptable one-liner
magick identify -verbose in.jpg | less                                # full EXIF / channels / histogram
magick identify -format "%[EXIF:*]" in.jpg                            # just EXIF
magick compare -metric RMSE a.png b.png null:                         # pixel-diff two images (lower = more similar)
```

Always `identify` the output after a transform to confirm dimensions, colorspace, and quality landed where you expected.

## Reference docs

- Read [`references/imagemagick.md`](references/imagemagick.md) for the full geometry / gravity / format / color-op / security-policy cheat-sheet and recipe book.

## Gotchas

- **v7 vs v6 commands.** v7 uses the unified `magick` binary (`magick convert …`, `magick identify …`). v6 exposes `convert`, `mogrify`, `composite`, `identify`, `montage`, `compare` as separate binaries. On v7, bare `convert` still works but is deprecated and collides with a Windows system tool — ALWAYS use `magick`.
- **Security policy blocks formats.** `/etc/ImageMagick-7/policy.xml` (or the Homebrew path) restricts `PDF`, `PS`, `EPS`, `MVG`, `LABEL`, `HTTPS`, and caps memory/disk. `not authorized` errors come from here. Either edit the policy (comment out the offending `<policy domain="coder" rights="none" pattern="PDF" />` line) or pass `--security-policy /path/to/loose.xml`.
- **Geometry suffix matters.** `100x100` (fit inside), `100x100!` (force exact — distorts), `100x100^` (fill, larger of the two), `100x100>` (shrink only if larger), `100x100<` (enlarge only if smaller), `50%` (scale). Mix up `!` and `^` and you either stretch or crop by accident.
- **Coordinate system is top-left origin.** `+X+Y` in `-crop`, `-geometry`, `-annotate`, `-draw` offsets are from top-left. `-gravity` re-anchors which corner offsets are measured from (NorthWest default).
- **`mogrify` overwrites originals in place.** ALWAYS pass `-path outdir/` to redirect, or back up first. This has eaten people's photo libraries.
- **`-density` must come BEFORE the input for vector/PDF.** `magick -density 300 in.pdf out.png` rasterizes at 300 DPI. Put it after and it's a no-op on the input.
- **`-strip` deletes all EXIF/XMP/IPTC.** Great for web (privacy + filesize), terrible if the client needs camera metadata. `-thumbnail` implicitly strips.
- **`-interlace Plane` = progressive JPEG / interlaced PNG.** Smaller perceived-load times on the web; slightly larger file.
- **Fonts need fontconfig on Linux.** `-font Arial` may silently fall back if Arial isn't installed. `magick -list font` shows what's usable. On macOS, system fonts work; on Alpine/Docker, install `fontconfig` + `ttf-dejavu`.
- **Unicode / emoji rendering.** Default font won't render CJK or emoji. Use `-font Noto-Sans-CJK-Regular`, `-font Apple-Color-Emoji`, or a font that covers your glyphs, or text falls back to tofu boxes.
- **HEIC/AVIF/JXL are optional.** Build must include libheif / libavif / libjxl. Check with `magick -list format | grep HEIC`. Homebrew's build includes them; Debian's default `imagemagick` does not always.
- **Q8 vs Q16 build.** Q8 stores 8 bits/channel internally; Q16 stores 16. For HDR, ICC profile-accurate work, or 16-bit TIFF / PNG, install the Q16 build (`brew install imagemagick` ships Q16 HDRI by default; check `magick -version`).
- **Memory limits.** Large images (huge PSDs, giant PDFs) can exhaust policy-defined memory limits and spill to disk. Raise with `export MAGICK_MEMORY_LIMIT=8GiB MAGICK_MAP_LIMIT=16GiB MAGICK_DISK_LIMIT=32GiB` or edit policy.xml.
- **Parallel batch.** ImageMagick itself is mostly single-threaded per image. Use GNU `parallel` or `xargs -P` for folder-level parallelism: `find . -name '*.jpg' | parallel magick {} -resize 1080 out/{/.}.jpg`.
- **`+repage` after crop.** `-crop` leaves a "virtual canvas" so the cropped piece remembers its original offset — multi-page formats or GIFs will act weird. Append `+repage` to clear it.

## Examples

### Example 1 — Web thumbnail batch

Input: `photos/*.jpg` full-res DSLR output.
Run:

```bash
mkdir -p thumbs
mogrify -path thumbs/ -thumbnail 400x400^ -gravity center -extent 400x400 \
        -quality 82 -strip -interlace Plane photos/*.jpg
```

Result: 400×400 center-cropped JPEGs, EXIF stripped, progressive, in `thumbs/`.

### Example 2 — Watermarked social bundle

Input: `hero.jpg`, `logo.png`.
Run:

```bash
for size in 1080x1080 1080x1350 1920x1080 1200x630; do
  magick hero.jpg -resize "${size}^" -gravity center -extent "$size" \
         \( logo.png -resize 10% \) -gravity SouthEast -geometry +24+24 -composite \
         "hero_${size}.jpg"
done
```

Result: one square (IG feed), one portrait (IG/TikTok), one landscape (YouTube thumb), one OG-image (og:image), each watermarked bottom-right.

### Example 3 — Render a PDF for review

```bash
magick -density 200 report.pdf -background white -alpha remove -alpha off report_%03d.png
```

Result: one PNG per page at 200 DPI, flattened over white (prevents transparent pages from looking black).

## Troubleshooting

### Error: `attempt to perform an operation not allowed by the security policy 'PDF'`

Cause: ImageMagick's policy.xml blocks PDF (and PS/EPS) by default.
Solution: Edit `/etc/ImageMagick-7/policy.xml` (or `$(brew --prefix)/etc/ImageMagick-7/policy.xml`), comment out `<policy domain="coder" rights="none" pattern="PDF" />`. Or run with `--security-policy /path/to/loose.xml` pointing at an edited copy.

### Error: `no decode delegate for this image format 'HEIC'`

Cause: Build lacks libheif. Check with `magick -list format | grep HEIC`.
Solution: `brew reinstall imagemagick` on macOS (Homebrew builds with libheif). On Debian, install `imagemagick` from bookworm-backports or build from source with `--with-heic`.

### Error: `convert: unable to read font` or output has wrong font

Cause: Named font not installed / fontconfig cache stale.
Solution: `magick -list font` to see what's available. Install the font (macOS: drop into `~/Library/Fonts`; Linux: `apt install fonts-dejavu` then `fc-cache -fv`). Then reference by the name `magick -list font` prints (e.g. `DejaVu-Sans`, not `DejaVu Sans.ttf`).

### Error: `cache resources exhausted` / `width or height exceeds limit`

Cause: policy.xml memory/disk/area caps too low for your image (common with huge PSDs, scanned TIFFs, multi-page PDFs).
Solution: Edit policy.xml `<policy domain="resource" name="memory" value="…"/>` entries upward, or set env vars `MAGICK_MEMORY_LIMIT`, `MAGICK_DISK_LIMIT`, `MAGICK_AREA_LIMIT`, `MAGICK_WIDTH_LIMIT`, `MAGICK_HEIGHT_LIMIT`.

### Error: output image looks stretched after `-resize`

Cause: Used `!` suffix (force exact) instead of default fit-inside.
Solution: Drop the `!`. If you need exact WxH without distortion, use `-resize WxH^ -gravity center -extent WxH` (fill + crop).

### Error: cropped PNG/GIF has wrong size / stray offset

Cause: `-crop` set a virtual canvas; writer preserved it.
Solution: Add `+repage` after `-crop`.
