---
name: vfx-openexr
description: >
  Work with OpenEXR VFX image format: exrheader (dump header attributes), exrinfo (concise info), exrmaketiled (scanline to tiled for MIP-map access), exrenvmap (latlong / cube environment-map conversion), exrmakepreview (embed thumbnail), exrmultipart (split/combine multi-part), exrmultiview (split/combine stereo multi-view), exrstdattr (read/write standard attributes), exrcheck (validate), exr2aces (convert to ACES-compliant EXR), exrmanifest (deep ID manifest), exrmetrics. Scanline vs tiled, multi-part (EXR 2+), deep images (deepscanline/deeptile), chromaticities, compression types (NONE/RLE/ZIPS/ZIP/PIZ/PXR24/B44/B44A/DWAA/DWAB/HTJ2K). EXR 2.x multi-part + deep data + DWAA/DWAB; EXR 3.x rewritten OpenEXRCore C API (thread-safe), Imath split out. Docs at openexr.com. Use when the user asks to inspect an EXR, convert EXR to tiled or multi-part, handle deep compositing data, embed thumbnails, or validate a VFX EXR pipeline.
argument-hint: "[action]"
---

# Vfx Openexr

**Context:** $ARGUMENTS

## Quick start

- **Dump header attributes:** -> Step 1 (`exr.py header`)
- **Quick info summary:** -> Step 2 (`exr.py info`)
- **Convert scanline -> tiled (for MIP-map access):** -> Step 3 (`exr.py tiled`)
- **Latlong -> cubemap or cube -> latlong:** -> Step 4 (`exr.py envmap`)
- **Embed a small preview thumbnail:** -> Step 5 (`exr.py preview`)
- **Multi-part (EXR 2) pack/unpack:** -> Step 6 (`exr.py multipart`)
- **Stereo multi-view pack/unpack:** -> Step 7 (`exr.py multiview`)
- **Standard attributes read/write:** -> Step 8 (`exr.py stdattr`)
- **Validate:** -> Step 9 (`exr.py check`)
- **Convert to ACES 2065-1:** -> Step 10 (`exr.py to-aces`)
- **Deep-ID manifest / metrics:** -> Step 11 (`exr.py manifest` / `metrics`)

## When to use

- User asks about EXR files in a VFX / compositing / lookdev context.
- Need to change EXR layout (scanline vs tiled, single-part vs multi-part).
- Deep compositing workflow (deepscanline / deeptile images).
- Preparing HDR source for a renderer's texture cache (`exrmaketiled`).
- ACES-ODT / ACES 2065-1 deliverables.

---

## Step 1 — Header dump

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py header image.exr
```

Expands to `exrheader image.exr`. Shows every header attribute: dataWindow, displayWindow, chromaticities, channels, compression, pixelAspectRatio, screenWindowCenter, screenWindowWidth.

---

## Step 2 — Concise info

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py info image.exr
```

Expands to `exrinfo image.exr`. Shorter than header; single-line-per-part summary.

---

## Step 3 — Make tiled (for MIP-mapped texture cache)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py tiled --in env.exr --out env_tiled.exr
```

Expands to `exrmaketiled env.exr env_tiled.exr`. Default tile size 64x64. Renderers like RenderMan/Arnold/V-Ray read tiled .exr far faster than scanline. Pair with `maketx` from OIIO for `.tx` output.

Options: `--tilesize 128`, `--rip` (RIP-map instead of MIP-map), `--plevel N` (levels).

---

## Step 4 — Environment maps

Convert latlong equirectangular to a cube (6 images stacked vertically):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py envmap --in latlong.exr --out cube.exr --type cube
```

Expands to `exrenvmap -latlong latlong.exr -cube cube.exr`.

Convert cube -> latlong:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py envmap --in cube.exr --out latlong.exr --type latlong
```

Requires input already in cube layout (6 stacked squares).

---

## Step 5 — Embed a preview

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py preview --in big.exr --out with_preview.exr --size 200
```

Expands to `exrmakepreview -w 200 big.exr with_preview.exr`. The small preview is embedded in the header so file browsers can thumbnail without decoding the full float pixels.

---

## Step 6 — Multi-part (EXR 2+)

Combine N single-part EXRs into one multi-part file:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py multipart pack \
  --out combined.exr beauty.exr normal.exr position.exr
```

Expands to `exrmultipart -combine -i beauty.exr normal.exr position.exr -o combined.exr`.

Split a multi-part back into per-part files:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py multipart unpack --in combined.exr --dest ./parts/
```

Expands to `exrmultipart -separate -i combined.exr -o ./parts/`. Per-part prefix defaults to the part name.

---

## Step 7 — Multi-view (stereo)

Combine left+right eye renders into one multi-view EXR:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py multiview pack \
  --out stereo.exr --left L.exr --right R.exr
```

Expands to `exrmultiview -combine -i L.exr R.exr -v left right -o stereo.exr`.

Split:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py multiview unpack --in stereo.exr --dest ./eyes/
```

---

## Step 8 — Standard attributes

Read every standard attribute:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py stdattr get image.exr
```

Expands to `exrstdattr image.exr`.

Write an attribute (example: set the owner):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py stdattr set --in image.exr --out tagged.exr \
  --attr owner --value "Lookdev Dept"
```

Expands to `exrstdattr -owner "Lookdev Dept" image.exr tagged.exr`. Standard attributes include: `owner`, `comments`, `capDate`, `utcOffset`, `longitude`, `latitude`, `altitude`, `focus`, `expTime`, `aperture`, `isoSpeed`, `envmap`, `chromaticities`, `whiteLuminance`, `adoptedNeutral`, `renderingTransform`, `lookModTransform`, `xDensity`, `wrapModes`, `keyCode`, `timeCode`, `framesPerSecond`. Full reference in `references/standard-attributes.md`.

---

## Step 9 — Validate

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py check image.exr
```

Expands to `exrcheck image.exr`. Structural validation: header integrity, chunk table, pixel-data presence. Non-zero exit on any corruption.

---

## Step 10 — Convert to ACES

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py to-aces image.exr aces.exr
```

Expands to `exr2aces image.exr aces.exr`. Sets chromaticities to AP0 (ACES 2065-1) and adds SMPTE ST 2065-4 ACES-compliant attributes.

---

## Step 11 — Deep ID manifest + metrics

Read the deep-ID manifest (cryptomatte-adjacent feature):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py manifest deep.exr
```

Expands to `exrmanifest deep.exr`.

Compression size/speed stats:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py metrics image.exr
```

Expands to `exrmetrics image.exr`.

---

## Gotchas

- **11 compression types, pick right:** `NONE`, `RLE`, `ZIPS` (per-scanline zip), `ZIP` (16-scanline block zip), `PIZ` (wavelet, best lossless for grainy film), `PXR24` (lossy 24-bit float to 24-bit), `B44` / `B44A` (fixed-size lossy, fast random access), `DWAA` / `DWAB` (DCT-based lossy, best size/quality), `HTJ2K` (EXR 3.2+ JPEG-2000-like). Read `references/compression.md` for the full tradeoff table.
- **EXR 2.x adds multi-part + deep data.** EXR 3.x reimplements the library (OpenEXRCore C API, thread-safe) and split Imath out as a separate lib. Pin your IO lib version if you need bit-exact compat.
- **Deep images have two flavors:** `deepscanline` (unordered samples) and `deeptile` (tiled). They require different APIs and most renderers write the scanline flavor.
- **PIZ is lossless; DWAA/DWAB are not.** Users sometimes assume DWA is lossless because it preserves floating-point precision — it doesn't. DWAB compresses harder than DWAA.
- **`chromaticities` attribute is where "what primaries does this EXR use?" is stored.** Missing chromaticities = assume Rec.709. ACEScg primaries look like `red=0.713,0.293; green=0.165,0.830; blue=0.128,0.044; white=0.3127,0.329`. ACES 2065-1 (AP0) is different.
- **`screenWindowCenter` / `screenWindowWidth` are for CG origin**, not for cropping. Don't set these to change the display window.
- **`displayWindow` vs `dataWindow`:** `displayWindow` is the intended canvas; `dataWindow` is the rendered area (may extend beyond displayWindow for overscan, or be smaller for partial renders). Comp apps crop to `dataWindow` on read.
- **Tiled EXR random-access != random-access guaranteed.** Tile size matters for how many tiles a renderer reads per sample. 64x64 is a good default; 128x128 for large-area sampling.
- **Environment maps (`exrenvmap`) expect specific layouts.** Latlong: full 2:1 equirect with rows = latitude. Cube: 6 faces stacked vertically as +X,-X,+Y,-Y,+Z,-Z (1:6 aspect), sized 6*N rows x N cols.
- **`exrcheck` does NOT verify perceptual quality.** It confirms the file is well-formed; it can't tell you the pixels are correct.
- **`exr2aces` only rewrites the header chromaticities.** It does NOT re-transform pixels. If pixels are already ACEScg but you mark as ACES2065-1, you've mislabelled color — use OIIO / OCIO to actually transform pixel values.
- **Canonical tools list verified from `openexr.com/en/latest/tools.html`:** `exrheader`, `exrinfo`, `exrmaketiled`, `exrenvmap`, `exrmakepreview`, `exrmultipart`, `exrmultiview`, `exrstdattr`, `exrcheck`, `exr2aces`, `exrmanifest`, `exrmetrics`. No `exrconv`, `exrconvert`, or `exr2png` — those are NOT real tools.

---

## Examples

### Example 1: "Tile a big latlong IBL for Arnold texture cache"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py tiled --in studio.exr --out studio_tiled.exr --tilesize 128
```

### Example 2: "Combine my AOV passes into one multi-part EXR"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py multipart pack --out shot.exr \
  beauty.exr diffuse.exr specular.exr normal.exr position.exr
```

### Example 3: "Check this deep render didn't get corrupted"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py check deep.exr
```

### Example 4: "Convert this latlong HDRI to a cubemap"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py envmap --in sky.exr --out sky_cube.exr --type cube
```

### Example 5: "Flag this file as ACES 2065-1 for studio ingest"

Only after confirming pixels are actually in AP0:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py to-aces render.exr render_aces.exr
```

### Example 6: "List all the standard attributes on this plate"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exr.py stdattr get plate.exr
```

---

## Troubleshooting

### Error: `exrheader: command not found`

**Cause:** OpenEXR CLIs not installed.
**Solution:** `brew install openexr`, `apt install openexr`, or build from source (github.com/AcademySoftwareFoundation/openexr).

### Error: `Invalid image data: cannot read chunk table`

**Cause:** Truncated file (upload/download interrupted), or EXR 2/3 version mismatch.
**Solution:** Re-copy the file. Confirm reader lib version: `exrheader image.exr | grep version`.

### Renderer says "tiled EXR required"

**Cause:** Scanline file passed to a renderer that wants tiled for MIP pyramid.
**Solution:** `exr.py tiled`. Some renderers (RenderMan) also want `.tx` — use `maketx` from OIIO (see `vfx-oiio` skill).

### Deep file loads in Nuke but not in RenderMan

**Cause:** Deep file is `deeptile` but one tool only expects `deepscanline`.
**Solution:** Check `exrheader` for `type: deeptile` vs `type: deepscanline`. Rewrite via OIIO if a converter is needed (no built-in converter ships with OpenEXR CLI suite).

### Preview embedding fails on very large images

**Cause:** Some `exrmakepreview` builds can't allocate huge intermediate buffers.
**Solution:** Pre-downscale the source with OIIO, then embed.

---

## Reference docs

- **Compression trade-offs table** (all 11 types, lossy/lossless, speed) -> [`references/compression.md`]
- **Standard attributes full list** (fields + expected types + meaning) -> [`references/standard-attributes.md`]
