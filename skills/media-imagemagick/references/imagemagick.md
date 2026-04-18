# ImageMagick Reference

Deep dive for topics that don't fit in `SKILL.md`. Conventions:

- All commands assume ImageMagick 7 (`magick` unified binary). On v6, replace `magick <sub>` with the matching `<sub>` binary: `magick convert …` → `convert …`, etc.
- "Geometry" is IM's shared language for sizes, offsets, and crops. See the cheat sheet below.

---

## 1. Geometry cheat sheet

IM accepts a single string format for nearly every size/offset argument:

```
<width>x<height>{%,!,<,>,^,@}{+-}<x>{+-}<y>
```

### Size suffixes (applied to `-resize`, `-thumbnail`, `-extent`, `-crop`, `-geometry`)

| Suffix | Meaning | Example | Result on a 4000×3000 image |
| ------ | ------- | ------- | -------------------------- |
| *(none)* | Fit INSIDE box, preserve aspect (default). | `1920x1080` | 1440×1080 |
| `!` | FORCE exact W×H, ignore aspect. Distorts. | `1920x1080!` | 1920×1080 stretched |
| `^` | FILL the box; one side ≥ target. Use with `-extent` to crop. | `1920x1080^` | 1920x1440 |
| `>` | Shrink only if larger than box. | `1920x1080>` on a 500×500 image | 500×500 unchanged |
| `<` | Enlarge only if smaller. | `1920x1080<` on a 500×500 image | 1920×1080 |
| `%` | Scale by percent. | `50%` | 2000×1500 |
| `@` | Cap total pixel count to W×H. | `2073600@` | ≤ 2073600 px (1920×1080 area) |

### Offset / crop geometry

```
<W>x<H>+<X>+<Y>       # crop rectangle, from top-left
+<X>+<Y>              # offset-only (for -geometry on composite)
-<X>-<Y>              # negative offsets are legal (off-canvas)
```

`-crop WxH+X+Y` leaves a "virtual canvas" reference — ALWAYS append `+repage` to clear it unless you need the original coords preserved.

### Tiling

```
-tile COLS x ROWS     # used by montage, and by patterned fill
```

---

## 2. Gravity reference

`-gravity` sets the anchor point used by `-annotate`, `-draw`, `-composite`, `-extent`, `-crop` (for relative cropping), `-append`. Default: `NorthWest` (top-left).

```
NorthWest   North    NorthEast
West        Center   East
SouthWest   South    SouthEast
```

Positional offsets (`+X+Y`) measure FROM the chosen gravity corner. Example: `-gravity SouthEast -geometry +20+20` places something 20 px in from the bottom-right corner.

---

## 3. Format table

| Format | Ext | Read | Write | Notes |
| ------ | --- | ---- | ----- | ----- |
| JPEG | `.jpg .jpeg` | Always | Always | 8-bit only, lossy, no alpha. `-quality 1–100`, `-interlace Plane` for progressive. |
| PNG | `.png` | Always | Always | Lossless, alpha supported. `-quality` maps to zlib level × 10 + filter. `-define png:compression-level=9`. |
| WebP | `.webp` | Usually | Usually | `-quality` 0-100; `-define webp:lossless=true`, `-define webp:method=6` (slower, smaller). |
| HEIC/HEIF | `.heic .heif` | Optional (libheif) | Optional | `magick -list format \| grep HEIC` to check. `-define heic:speed=0` (best) … `8` (fastest). |
| AVIF | `.avif` | Optional (libavif) | Optional | `-define heic:speed=…` reused for AVIF on some builds; also `-define avif:encoder-speed=…`. |
| JXL | `.jxl` | Optional (libjxl) | Optional | `-define jxl:effort=3–9`; `-quality 100 -define jxl:distance=0` for lossless. |
| TIFF | `.tif .tiff` | Always | Always | `-compress zip`, `-compress lzw`, `-compress none`. Supports 16-bit if Q16 build. |
| GIF | `.gif` | Always | Always | 256-color palette. `-layers Optimize` for animated. `-coalesce` to get full frames. |
| BMP | `.bmp` | Always | Always | Uncompressed by default. |
| ICO | `.ico` | Always | Always | Multi-size favicons: `magick in.png -define icon:auto-resize=16,32,48,64,128,256 favicon.ico`. |
| PDF | `.pdf` | Optional (ghostscript) | Optional | `-density 300` before input for vector rasterization. Often blocked by policy.xml. |
| PSD | `.psd` | Yes | Yes | Layered: `magick in.psd[0]` reads composed, `[1]` reads first layer. |
| SVG | `.svg` | Yes | Yes (via MSVG/RSVG) | Rasterized via `MSVG` (built-in) or `RSVG` (librsvg, better). |
| RAW (CR2/NEF/ARW) | *various* | Via dcraw/ufraw | No | IM shells out to dcraw. Quality is limited; prefer `darktable-cli` / `rawtherapee-cli` for serious work. |

Check what your build supports:

```bash
magick -list format                        # everything
magick -list format | grep -E '^ *WEBP'    # specific format line (note leading spaces)
magick -list delegate                      # shows external helpers (ghostscript, dcraw, rsvg)
```

---

## 4. Color operations

### Quick knobs

| Filter | Example | What it does |
| ------ | ------- | ------------ |
| `-modulate B,S,H` | `-modulate 110,120,100` | Brightness, Saturation, Hue (100 = unchanged). |
| `-level lo,hi` | `-level 10%,90%` | Stretch/compress tonal range. Add gamma: `10%,90%,1.2`. |
| `-brightness-contrast BxC` | `-brightness-contrast 10x20` | Photoshop-style sliders, -100 to +100. |
| `-gamma g` | `-gamma 1.2` | Gamma-only adjustment. |
| `-auto-level` | `-auto-level` | Stretch histogram to full range. |
| `-auto-gamma` | `-auto-gamma` | Heuristic gamma correction. |
| `-contrast-stretch a%,b%` | `-contrast-stretch 1%,1%` | Like Photoshop auto-levels. |
| `-normalize` | `-normalize` | Rough histogram normalization. |
| `-equalize` | `-equalize` | Histogram equalization. |
| `-sigmoidal-contrast Cxβ` | `-sigmoidal-contrast 5x50%` | Photographic S-curve contrast. |

### Colorspace transforms

```bash
magick in.jpg -colorspace Gray out.jpg           # desaturate
magick in.png -colorspace sRGB out.png           # tag as sRGB
magick in.jpg -colorspace LAB -channel L -level 10%,90% +channel -colorspace sRGB out.jpg
```

Valid `-colorspace` values include: `sRGB`, `RGB`, `Gray`, `Rec709Luma`, `Rec601Luma`, `HSL`, `HSV`, `HSB`, `HCL`, `LAB`, `LUV`, `XYZ`, `CMY`, `CMYK`, `YCbCr`, `YIQ`.

### ICC profiles

```bash
magick in.jpg -profile sRGB.icc out.jpg                    # embed/convert to sRGB
magick in.jpg -profile /path/AdobeRGB1998.icc \
             -profile sRGB2014.icc out.jpg                  # convert AdobeRGB → sRGB
magick in.jpg +profile "*" out.jpg                          # strip all profiles
```

Profile order matters: the first `-profile` becomes the source profile (or validates an embedded one); subsequent `-profile` calls convert to that space.

### LUT / curves

```bash
magick in.jpg lut.png -clut out.jpg                         # apply a 1D Colour Look-Up Table
magick in.jpg hald.png -hald-clut out.jpg                   # 3D Hald CLUT (use Hald identity images to bake LUTs)
magick -size 256x1 gradient: -rotate 90 lut.png             # make a grayscale 1D LUT
```

For 3D `.cube` / `.3dl` / OCIO LUTs: use ffmpeg's `lut3d` filter or `ocio` filter (see `ffmpeg-lut-grade` / `ffmpeg-ocio-colorpro`).

---

## 5. Font rendering

### Find fonts

```bash
magick -list font                   # all fonts known to IM's fontconfig cache
magick -list font | awk '/Font:/{print $2}'
```

### Specifying a font

```bash
-font DejaVu-Sans                   # by logical name (printed by -list font)
-font /path/to/FreeSans.ttf         # by absolute path to a .ttf/.otf/.ttc
-family "DejaVu Sans"               # by family + style/weight
-weight Bold                        # 400 = normal, 700 = bold (or words: Thin/Normal/Bold)
-stretch Condensed                  # Condensed/Expanded/etc.
```

### Linux gotcha

ImageMagick on Linux uses fontconfig. If your font isn't listed:

1. Drop it into `~/.local/share/fonts/` or `/usr/share/fonts/`.
2. Run `fc-cache -fv`.
3. Re-run `magick -list font`.

### Alpine / Docker

Base Alpine has no fonts. Install:

```bash
apk add --no-cache fontconfig ttf-dejavu ttf-liberation
```

### macOS

All system fonts (`/Library/Fonts`, `/System/Library/Fonts`, `~/Library/Fonts`) are picked up automatically.

### Unicode coverage

- CJK: `Noto-Sans-CJK-SC-Regular`, `Noto-Sans-CJK-JP-Regular`, `Noto-Sans-CJK-KR-Regular`.
- Emoji: `Apple-Color-Emoji` (macOS), `Noto-Color-Emoji` (Linux). Note: IM's rasterizer may fall back to glyph tofu on color-emoji fonts — v7.1+ handles them better.
- Arabic/Hebrew RTL: needs HarfBuzz-enabled build (`magick -version | grep Features`).

---

## 6. Security policy (`policy.xml`)

Path: `/etc/ImageMagick-7/policy.xml` (Debian/Ubuntu), `$(brew --prefix)/etc/ImageMagick-7/policy.xml` (macOS Homebrew), `C:\Program Files\ImageMagick-*\policy.xml` (Windows).

### Common blocks

After the 2016 "ImageTragick" (CVE-2016-3714) and follow-on CVEs, many distros ship a policy like:

```xml
<policy domain="coder" rights="none" pattern="PS" />
<policy domain="coder" rights="none" pattern="EPI" />
<policy domain="coder" rights="none" pattern="PDF" />
<policy domain="coder" rights="none" pattern="XPS" />
<policy domain="coder" rights="none" pattern="MVG" />
<policy domain="coder" rights="none" pattern="MSL" />
<policy domain="coder" rights="none" pattern="HTTPS" />
<policy domain="coder" rights="none" pattern="LABEL" />
<policy domain="path"  rights="none" pattern="@*" />
```

Symptoms: `attempt to perform an operation not allowed by the security policy 'PDF'`.

### Resource caps

```xml
<policy domain="resource" name="memory" value="256MiB"/>
<policy domain="resource" name="map"    value="512MiB"/>
<policy domain="resource" name="width"  value="16KP"/>
<policy domain="resource" name="height" value="16KP"/>
<policy domain="resource" name="area"   value="128MP"/>
<policy domain="resource" name="disk"   value="1GiB"/>
<policy domain="resource" name="time"   value="120"/>    <!-- seconds -->
```

Hitting a cap produces `cache resources exhausted` or `width/height exceeds limit`.

### Unblocking safely

Preferred: copy policy.xml to a local file, edit, point at it:

```bash
cp /etc/ImageMagick-7/policy.xml /tmp/im-loose.xml
# edit /tmp/im-loose.xml
MAGICK_CONFIGURE_PATH=/tmp magick -verbose in.pdf out.png
```

Or override resource caps via env:

```bash
export MAGICK_MEMORY_LIMIT=8GiB
export MAGICK_MAP_LIMIT=16GiB
export MAGICK_DISK_LIMIT=32GiB
export MAGICK_AREA_LIMIT=2GP
export MAGICK_WIDTH_LIMIT=64KP
export MAGICK_HEIGHT_LIMIT=64KP
```

Never relax `HTTPS`, `URL`, or path `@*` policies on a server that accepts user input — that's how ImageTragick-class RCE happens.

---

## 7. Recipe book

### 7a. Batch thumbnails (fast, parallel)

```bash
mkdir -p thumbs
find photos -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) -print0 |
  parallel -0 -j "$(nproc)" \
    'magick {} -thumbnail 400x400^ -gravity center -extent 400x400 \
              -quality 82 -strip -interlace Plane thumbs/{/}'
```

`parallel` (GNU parallel, `brew install parallel` / `apt install parallel`) gives big throughput wins since IM is single-threaded per image.

### 7b. Signed watermark (bottom-right)

```bash
magick in.jpg \
  \( -size 600x -background none -fill '#ffffffa0' -font DejaVu-Sans-Bold \
     -pointsize 48 label:'© 2026 Damion' \
     -trim +repage \) \
  -gravity SouthEast -geometry +32+32 -composite \
  out.jpg
```

### 7c. Favicon + Apple touch icons

```bash
magick logo.png -resize 256x256 -background none \
       -define icon:auto-resize=16,32,48,64,128,256 favicon.ico

for sz in 32 57 72 96 114 120 144 152 180 192 512; do
  magick logo.png -resize ${sz}x${sz} \
         -background none -gravity center -extent ${sz}x${sz} \
         apple-touch-icon-${sz}x${sz}.png
done
```

### 7d. Social bundle from one hero

```bash
hero=hero.jpg
for size in 1080x1080 1080x1350 1920x1080 1200x630; do
  magick "$hero" -resize "${size}^" -gravity center -extent "$size" \
         -quality 88 -strip "${hero%.*}_${size}.jpg"
done
```

- `1080x1080` — Instagram feed square.
- `1080x1350` — Instagram / TikTok portrait (4:5).
- `1920x1080` — YouTube thumbnail / Twitter landscape.
- `1200x630` — Open Graph / LinkedIn.

### 7e. PDF page rendering (flatten transparent pages)

```bash
magick -density 200 report.pdf \
       -background white -alpha remove -alpha off \
       -quality 90 report_%03d.jpg
```

`-alpha remove -alpha off` prevents pages that include transparency from rendering black.

### 7f. Bake a 3D LUT (Hald CLUT)

```bash
# Generate a neutral Hald identity, import into your grading tool, export the graded Hald,
# then apply with -hald-clut.
magick hald:12 hald_identity.png                # 12³ = 1728 → 12 cubed = 144x144... actually 12x12x12x12 tiles
magick photo.jpg graded_hald.png -hald-clut out.jpg
```

### 7g. Compare two images numerically

```bash
magick compare -metric RMSE a.png b.png diff.png ; echo       # RMSE: 1234.56 (0)
magick compare -metric PSNR a.png b.png null: 2>&1             # higher = more similar
magick compare -metric AE   -fuzz 5% a.png b.png null:         # # of differing pixels w/ 5% fuzz
```

Available metrics: `AE`, `DSSIM`, `FUZZ`, `MAE`, `MEPP`, `MSE`, `NCC`, `PAE`, `PHASH`, `PSNR`, `RMSE`, `SSIM`.

### 7h. Fix orientation from EXIF and strip metadata

```bash
mogrify -path fixed/ -auto-orient -strip *.jpg
```

Do this before any other processing — otherwise `-rotate`, `-crop`, and manual geometry operations will be off by 90° for phone photos.

### 7i. Extract layers / pages from PSD or TIFF

```bash
magick in.psd[0]                      # flattened composite (layer 0)
magick in.psd[1] layer1.png           # first real layer
magick -compress none in.psd layers_%d.png       # dump every layer
magick in.tif[0-4] -append stack.png             # first 5 pages stacked vertically
```

### 7j. Montage with labels

```bash
magick montage \
  -label '%t\n%wx%h' \
  *.jpg \
  -geometry 240x240+6+6 -tile 5x \
  -background '#111' -fill '#ddd' -font DejaVu-Sans -pointsize 14 \
  contact_sheet.jpg
```

`-tile 5x` = 5 columns, unlimited rows. `%t` = basename, `%wx%h` = dimensions — see `magick -list format` for the full format-string vocabulary.

---

## 8. Build info check

```bash
magick -version
# Copyright: …
# Features: Cipher DPC HDRI Modules OpenMP(5.0)
# Delegates (built-in): bzlib fontconfig freetype gslib heic jng jp2 jpeg jxl lcms ltdl lzma openexr pangocairo png ps raw tiff webp x xml zlib
```

What to check:
- **Q8 vs Q16.** `magick -version | head -1` says `Q16` (default Homebrew) or `Q8`. Q16 = 16-bit-per-channel internals; needed for 16-bit PNG/TIFF and HDRI.
- **HDRI flag** in Features = supports negative / >1.0 pixel values for floating-point math. On by default in Homebrew.
- **Delegates** = optional format support. If `heic` is missing, you can't read HEIC. If `jxl` is missing, no JPEG-XL. Rebuild with `--with-heic --with-libjxl --with-libavif`.
- **OpenMP** = parallel pixel operations inside one image. Control threads with `-limit thread 4` or env `MAGICK_THREAD_LIMIT=4`.
