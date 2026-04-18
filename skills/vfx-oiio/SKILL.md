---
name: vfx-oiio
description: >
  VFX-grade image processing with OpenImageIO: oiiotool (stack-based Swiss Army knife - load/save, resize/crop/rotate/blur, metadata, compositing, color management via OCIO, deep images), iconvert (format conversion), iinfo (metadata dump), igrep (search metadata), idiff (perceptual diff), maketx (build tiled MIP-map textures for renderers), iv (GUI viewer). Handles OpenEXR, TIFF, DPX, Cineon, JPEG, JPEG 2000, JPEG XL, HEIC/HEIF/AVIF, PNG, BMP, RAW (LibRaw), FITS, PSD, WebP, PNM, Targa, IFF, SGI, Radiance HDR, GIF, DDS, Field3D, OpenVDB, Ptex. Direct OCIO integration (--colorconvert, --ociolook, --ociodisplay, --ociofiletransform). Docs at openimageio.readthedocs.io. Use when the user asks to convert image formats at VFX scale, apply color management, build MIP-map textures, read DPX/Cineon/EXR/OpenVDB, do deep compositing, or batch-process imagery with oiiotool.
argument-hint: "[action]"
---

# Vfx Oiio

**Context:** $ARGUMENTS

## Quick start

- **Inspect an image:** -> Step 1 (`oiio.py info`)
- **Convert formats:** -> Step 2 (`oiio.py convert`)
- **Perceptual diff:** -> Step 3 (`oiio.py diff`)
- **Search metadata:** -> Step 4 (`oiio.py grep`)
- **Build .tx / .exr tiled texture (maketx):** -> Step 5 (`oiio.py maketx`)
- **Color-space transform:** -> Step 6 (`oiio.py color`)
- **Resize / crop / rotate:** -> Steps 7-9 (`oiio.py resize|crop|rotate`)
- **Arbitrary oiiotool recipe:** -> Step 10 (`oiio.py tool -- args...`)

## When to use

- Converting between 30+ VFX image formats (EXR, DPX, Cineon, TIFF, HDR, JPEG XL, PSD, ...).
- OCIO color management with `--colorconvert`, `--ociodisplay`, `--ociolook`, `--ociofiletransform`.
- Building MIP-mapped tiled textures for Arnold, RenderMan, V-Ray, Cycles.
- Deep compositing (`--deepen`, `--deepmerge`, `--deepholdout`).
- Pixel-level perceptual diff (`idiff`).
- Pair with `vfx-openexr` for EXR-specific authoring; with `vfx-usd` for USD texture paths.

---

## Step 1 — Info

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py info plate.exr
```

Expands to `iinfo -v plate.exr`. Use `--stats` for per-channel pixel stats (min/max/avg/stddev) which is invaluable for "is this actually black?" and "did my tonemap clip?".

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py info --stats plate.exr
```

---

## Step 2 — Convert

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py convert --in in.dpx --out out.exr
```

Expands to `iconvert in.dpx out.exr`. Format inferred from the output extension.

Set compression explicitly (EXR output):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py convert --in in.dpx --out out.exr --compression dwaa
```

---

## Step 3 — Perceptual diff

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py diff a.exr b.exr
```

Expands to `idiff a.exr b.exr`. Exit 0 = identical within default tolerance. Tune tolerance with `--fail 0.01 --warn 0.001`.

Save a difference image:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py diff a.exr b.exr --out diff.exr
# -> idiff -o diff.exr a.exr b.exr
```

---

## Step 4 — Grep metadata

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py grep --pattern "smpte:TimeCode" plate.exr
```

Expands to `igrep smpte:TimeCode plate.exr`. Case-insensitive by default.

---

## Step 5 — maketx (tiled MIP-map texture)

Build a `.tx` texture from a source image:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py maketx --in source.exr --out texture.tx
```

Expands to `maketx -o texture.tx source.exr`.

Common flags:

- `--hdri` — preserve HDR range, use box downsampling for lighting IBLs.
- `--unpremult` — unpremultiply alpha before downscaling (for color maps with alpha).
- `--monochrome-detect` — single out R=G=B files as 1-channel to save memory.
- `--filter lanczos3` — specify downsample filter.
- `--colorconvert sRGB ACEScg` — bake in a color transform during maketx.

---

## Step 6 — Color-space transform

Convert between OCIO-managed color spaces:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py color --in srgb.png --out acescg.exr \
  --from sRGB --to ACEScg
```

Expands to `oiiotool --colorconfig $OCIO srgb.png --colorconvert sRGB ACEScg -o acescg.exr`.

Requires an active OCIO config (set `$OCIO` to a `config.ocio` path, e.g. the ACES 1.3 studio config).

Apply a view transform (display-referred output):

```bash
# View an ACEScg EXR through the Rec.709 ACES ODT:
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py tool -- \
  in_acescg.exr --ociodisplay "sRGB" "Rec.709" -o preview.png
```

---

## Step 7 — Resize

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py resize --in big.exr --out small.exr --size 1920x1080
```

Expands to `oiiotool big.exr --resize 1920x1080 -o small.exr`.

Use `--filter lanczos3` for high quality, `--filter box` for IBL/HDRI. Default is a good general-purpose filter (blackman-harris).

---

## Step 8 — Crop

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py crop --in in.exr --out out.exr --box 100,100,1820,980
```

Expands to `oiiotool in.exr --crop 1720x880+100+100 -o out.exr`.

---

## Step 9 — Rotate

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py rotate --in in.exr --out out.exr --degrees 90
```

Expands to `oiiotool in.exr --rotate 90 -o out.exr`. 90 / 180 / 270 are lossless; other angles resample pixels.

---

## Step 10 — Raw oiiotool wrapper

For anything not wrapped above, pass arbitrary args through. The stack-based grammar is oiiotool's superpower:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py tool -- \
  bg.exr fg.exr --over -o composite.exr
```

Expands to `oiiotool bg.exr fg.exr --over -o composite.exr`.

Read [`references/oiiotool-cheatsheet.md`] for 15 copy-paste recipes covering the common ops.

---

## Gotchas

- **`oiiotool` is a stack machine, not a linear pipeline.** Order matters: every positional input pushes an image on the stack; every operator consumes the top N and pushes a result. `a.exr b.exr --over` works, but `a.exr --over b.exr` does NOT (no second operand for `--over` yet).
- **`--over` requires premultiplied alpha.** If `bg.exr` has straight alpha, add `--unpremult` before and `--premult` after, or use `--Aover` (straight-alpha over).
- **`iinfo` vs `iinfo -v`:** without `-v` you get one-line-per-file summary. With `-v` you get full metadata dump. `--stats` is a third level: actually scans pixels.
- **`maketx` bakes in color transforms if you pass `--colorconvert`.** Once baked in, the renderer cannot reinterpret. Usually you want `--colorconvert` only when producing linear working-space `.tx` from an sRGB texture.
- **OCIO configs are environment-driven.** Most tools honor `$OCIO` pointing at `config.ocio`. If your color-convert complains "colorspace not found", check `echo $OCIO` and `ociocheck $OCIO`.
- **`maketx` default tile size is 64.** Override with `--tile 128` for large-area sampling; for small filters 64 is optimal.
- **`idiff` is PSNR/SSIM-based by default**, not a strict byte-compare. For bit-exact use `cmp` or `openssl dgst`.
- **Format auto-detection uses the extension, not magic bytes.** A `.dpx` written with a wrong header will be mis-read. Use `iinfo` to sanity-check.
- **`--ociodisplay` vs `--colorconvert`:** `--colorconvert` is scene-referred roundtrip; `--ociodisplay` applies a display transform (ACES RRT+ODT, Filmic view, etc.) and produces display-referred output.
- **OIIO's Ptex / OpenVDB / Field3D support is optional** — require build-time linking. Some distributions don't ship those format plugins; check `oiiotool --help` "Supported input formats".
- **Canonical tool list verified from `openimageio.readthedocs.io`:** `oiiotool`, `iconvert`, `iinfo`, `igrep`, `idiff`, `maketx`, `iv`. The `iv` viewer has no dedicated page — it's the GUI counterpart to `iinfo`.

---

## Examples

### Example 1: "Convert a 16-bit TIFF to linear EXR"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py convert --in photo.tif --out photo.exr \
  --compression zip
```

### Example 2: "Make an IBL .tx for Arnold, preserving HDR"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py maketx --in studio.exr --out studio.tx --hdri
```

### Example 3: "Transform sRGB PNG to ACEScg EXR"

```bash
export OCIO=/path/to/studio-config-v1.0.0/config.ocio
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py color --in logo.png --out logo_acescg.exr \
  --from sRGB --to ACEScg
```

### Example 4: "Composite fg over bg and crop"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py tool -- \
  bg.exr fg.exr --over --crop 1920x1080+0+0 -o comp.exr
```

### Example 5: "Diff two renders and save a heat map"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py diff render_v1.exr render_v2.exr --out diff.exr
```

### Example 6: "Find all EXRs with a given AOV name"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oiio.py grep --pattern "specular.R" *.exr
```

---

## Troubleshooting

### Error: `oiiotool: command not found`

**Cause:** OIIO binaries not installed.
**Solution:** `brew install openimageio`, `apt install openimageio-tools`, or build from source (github.com/AcademySoftwareFoundation/OpenImageIO).

### Error: `ColorSpace 'X' not found`

**Cause:** OCIO config doesn't define that color space.
**Solution:** `echo $OCIO` to verify config path; `ociocheck $OCIO` to list defined spaces; use an ACES studio config if unsure.

### `--over` gives dark halos

**Cause:** Straight-alpha input treated as premultiplied.
**Solution:** Add `--unpremult` before `--over`; or use `--Aover`.

### `maketx` produces huge output file

**Cause:** `--monochrome-detect` not set and source is grayscale but stored as RGB.
**Solution:** Add `--monochrome-detect`. Also check compression: `--compression dwaa` or `--compression zip`.

### iinfo crashes on a DPX

**Cause:** Non-standard DPX header (Kodak legacy, early camera logs).
**Solution:** Try `oiiotool --info -v in.dpx`; if it also crashes, the file needs a header fix (use the `dpx` DCC or re-export from source).

---

## Reference docs

- **oiiotool recipe cheat-sheet** (15 most-used pipelines: alpha ops, compositing, color, deep, resize, denoise) -> [`references/oiiotool-cheatsheet.md`]
