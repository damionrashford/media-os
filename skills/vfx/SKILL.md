---
name: vfx
description: >
  Use when working with VFX imagery and 3D scene description across three toolchains. OpenImageIO/oiiotool: convert 30+ image formats (EXR, DPX, Cineon, TIFF, HDR, JPEG XL, PSD, OpenVDB), OCIO color management (colorconvert/ociodisplay/ociolook), build MIP-map tiled textures (maketx .tx), deep compositing, perceptual diff (idiff), iinfo/igrep/iconvert. OpenEXR: exrheader/exrinfo, scanline-to-tiled (exrmaketiled), multi-part EXR 2 (exrmultipart), stereo multi-view, deep images (deepscanline/deeptile), latlong/cube env maps (exrenvmap), standard attributes, validate (exrcheck), ACES 2065-1 (exr2aces), compression types (PIZ/DWAA/DWAB/PXR24/HTJ2K). OpenUSD/USD: usdcat convert .usda/.usdc/.usdz, usdview, usdrecord Hydra render, usdchecker validate for Apple ARKit Quick Look, usdzip AR packages, composition arcs and LIVRPS strength ordering, UsdGeom/UsdLux/UsdShade schemas. Use when asked to inspect/convert EXR, manage color, build renderer textures, or author USD scenes.
argument-hint: "[action]"
---

# VFX

Image processing and 3D scene description for VFX pipelines: OpenImageIO (oiiotool), OpenEXR, and OpenUSD. Each toolchain has a wrapper script plus a deep reference.

## When to use

- Convert or inspect VFX imagery (EXR, DPX, Cineon, TIFF, HDR, JPEG XL, PSD, OpenVDB) — `references/oiio.md`.
- OCIO color management, ACES transforms, or baking MIP-map `.tx` textures for Arnold/RenderMan/V-Ray/Cycles — `references/oiio.md`.
- Author, validate, or render USD scenes; deliver `.usdz` for Apple AR Quick Look — `references/usd.md`.
- Manipulate EXR layout: scanline↔tiled, single↔multi-part, deep images, stereo views, env maps, chromaticities — `references/openexr.md`.

## Techniques

- Read `references/oiio.md` when the task is OpenImageIO / oiiotool: format conversion, OCIO color, maketx textures, deep compositing, idiff, iinfo/igrep.
- Read `references/openexr.md` when the task is OpenEXR-specific: header/attributes, tiled or multi-part or deep or multi-view EXR, env maps, compression choice, ACES 2065-1 tagging, exrcheck.
- Read `references/usd.md` when the task is OpenUSD: convert between .usda/.usdc/.usdz, usdview/usdrecord, usdchecker (incl. ARKit), usdzip, composition arcs, schemas.
- For oiiotool recipes (alpha ops, compositing, color, deep, resize): read `references/oiiotool-cheatsheet.md`.
- For EXR compression trade-offs and standard attributes: read `references/compression.md` and `references/standard-attributes.md`.
- For USD core concepts and schemas: read `references/concepts.md` and `references/schemas.md`.

## Gotchas

- **oiiotool is a stack machine**, not a linear pipeline. Inputs push images; operators consume the top N. `a.exr b.exr --over` works; `a.exr --over b.exr` does not.
- **`--over` needs premultiplied alpha.** Straight alpha → wrap with `--unpremult`/`--premult` or use `--Aover`, else dark halos.
- **PIZ is lossless; DWAA/DWAB are not.** DWA preserves float precision but is still lossy. DWAB compresses harder than DWAA. Pick compression deliberately (see `references/compression.md`).
- **EXR `displayWindow` vs `dataWindow`**, and `chromaticities` define primaries — missing chromaticities means assume Rec.709. `exr2aces` only rewrites the header, it does NOT transform pixels.
- **Deep EXR has two flavors:** `deepscanline` and `deeptile`, different APIs; most renderers write scanline.
- **USD composition obeys LIVRPS strength order** (Local > Inherits > VariantSets > References > Payloads > Specializes). "My edit isn't showing up" almost always means a stronger opinion wins elsewhere.
- **`.usdz` is a zero-compression aligned ZIP** — build it with `usdzip`, never plain `zip`, or Apple Quick Look rejects it. Re-validate with `usdchecker --arkit` before Apple submission.
- **References are always loaded; Payloads load on demand** (`stage.Load()`/`Unload()`). Use Payloads for heavy environments.

## Scripts

- `scripts/oiio.py` — OpenImageIO wrapper: `info`, `convert`, `diff`, `grep`, `maketx`, `color`, `resize`, `crop`, `rotate`, `tool` (raw oiiotool passthrough).
- `scripts/exr.py` — OpenEXR wrapper: `header`, `info`, `tiled`, `envmap`, `preview`, `multipart`, `multiview`, `stdattr`, `check`, `to-aces`, `manifest`, `metrics`.
- `scripts/usd.py` — OpenUSD wrapper: `cat`, `info`, `validate`, `record`, `zip`/`unzip`, `diff`, `resolve`, `view`, `stitch-clips`.

All scripts support `--dry-run` and `--verbose`. Run via `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py`.
