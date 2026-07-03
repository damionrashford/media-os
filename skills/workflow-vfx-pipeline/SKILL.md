---
name: workflow-vfx-pipeline
description: VFX-grade I/O and handoff — read/write USD (Pixar Universal Scene Description), deep and multi-part OpenEXR, color-managed OpenImageIO with ACES/OCIO configs, dailies, cryptomatte extraction, plate generation for compositors, and delivery back to editorial or IMF. Use when the user says "ACES pipeline", "EXR sequence", "USD stage", "VFX plates", "cryptomatte", "ARRI LogC to ACEScg", "deep compositing", or anything VFX-I/O related.
argument-hint: "[source]"
---

# Workflow — VFX Pipeline

**What:** Handle VFX-grade media interchange. Color-managed ACES throughout, EXR as the float-linear format, USD for scene descriptions, clean handoffs to compositors and back to editorial.

## Skills used

`vfx-usd`, `vfx-openexr`, `vfx-oiio`, `ffmpeg-ocio-colorpro`, `ffmpeg-lut-grade`, `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-hdr-color`, `ffmpeg-frames-images`, `ffmpeg-transcode`, `ffmpeg-mxf-imf`, `otio-convert`.

## Pipeline

### Step 1 — Inspect EXR

`vfx-openexr` (`exrctl header` for channels / compression / chromaticities; `exrctl info` for multi-part / multi-view).

### Step 2 — Inspect USD

`vfx-usd` (`usdctl info` for hierarchy; `usdctl flatten` to resolve LIVRPS composition).

### Step 3 — Color config

`export OCIO=/opt/aces/config.ocio`. `ffmpeg-ocio-colorpro list-transforms` to confirm what's available. Core ACES spaces:

| Role | Space |
|---|---|
| Compositing | Linear ACEScg AP1 |
| Archival | ACES2065-1 AP0 |
| SDR output | Output - Rec.709 |
| HDR10 output | Output - Rec.2020 ST2084 |
| HLG output | Output - Rec.2020 HLG |

### Step 4 — EXR → ProRes dailies

`vfx-oiio` (`oiiotool` color-managed ACEScg → Rec.709) OR `ffmpeg-ocio-colorpro` with the OCIO filter. ProRes 4444 XQ 12-bit for no clipping; 422 HQ 10-bit has YCbCr color loss vs EXR.

### Step 5 — Plates for VFX vendors

LIN-LIN ACEScg EXR, ZIP compression, 16-bit half-float. Rec.709 JPEG proxies for review copies.

### Step 6 — Ingest comps back

Verify color space = ACEScg. Check resolution, duration, frame count match. Round-trip to Rec.709 for review.

### Step 7 — Cryptomatte extraction

`exrctl list-parts` → `extract-part` for crypto layers.

### Step 8 — USD-driven render submission

`usdctl reference` to layout shots without opening Maya/Houdini. `usdctl override` attributes per shot.

### Step 9 — Hand off to editorial

EXR ACEScg → Rec.2020 ST2084 ProRes 4444 XQ (HDR10 dailies) or straight to J2K IMF via `ffmpeg-mxf-imf`.

### Step 10 — Back to NLE

Emit FCPXML via `otio-convert` for editor relink.

## Variants

- **Stereo 3D** — `exrctl info` for multi-view, `extract-view` per eye, compose side-by-side via `ffmpeg-360-3d`.
- **Deep compositing** — `exrctl deep-info` on Z-layers, flatten deep → flat for ffmpeg compat.
- **Environment maps** — `exrctl envmap` cubemap ↔ latlong.
- **Camera log → ACEScg** — ARRI LogC / Sony SLog / RED Log mapped via OCIO.
- **USD batch render** — `usdctl override` per-shot, submit to renderer.

## Gotchas

- **ACEScg (AP1) vs ACES2065-1 (AP0).** ACEScg for compositing (smaller gamut fits BT.2020). AP0 for archival wide-gamut only — DO NOT composite in AP0.
- **OCIO config mismatch between tools breaks everything.** oiiotool, ffmpeg, Nuke all consume the SAME config path. Always `export OCIO=...` from one source of truth.
- **EXR `chromaticities` field is source-of-truth for color space.** Absent = tools assume Rec.709/sRGB — WRONG for ACES. Always write chromaticities.
- **`ocio` ffmpeg filter needs libOpenColorIO build.** Verify: `ffmpeg -filters | grep ocio`.
- **Rec.709 display output assumes sRGB gamma on monitors; broadcast uses BT.1886 (~2.4).** Confirm target — OCIO has both `Output - sRGB` and `Output - Rec.709`.
- **EXR compression choice:** ZIP lossless slow (archive), ZIPS scanline ZIP faster, PIZ lossless great for natural, B44 lossy half-float, DWAA/DWAB high-quality lossy disk-cheap (dailies).
- **Scanline vs tiled EXR.** Scanline = default random access. Tiled needs tile-aware readers.
- **Multi-part vs multi-channel.** Multi-part = discrete "parts" with independent channels/compression/chromaticities — best for deep/crypto. Multi-channel = all AOVs in one part — simpler.
- **Half-float 16-bit clips HDR above ~65504.** Use 32-bit float for HDRI environment maps.
- **Deep EXR has variable samples per pixel.** Memory can balloon; all downstream tools must be deep-aware.
- **USD LIVRPS composition order: Local, Inherits, VariantSets, References, Payloads, Specializes.** Stronger layer always wins. `resolve-info` finds override culprits.
- **USD references always load; payloads are lazy.** Use payloads for large sets.
- **USD variantSets are authoring-time**, not runtime. `variantSet lookStyle {blue,red,green}` switches at authoring.
- **USD file flavors:** `.usda` ASCII editable, `.usdc` binary fast — NEVER hand-edit `.usdc`. Use `usdedit` or Python API. `.usdz` is a zipped bundle.
- **USD defaults to centimeters.** Many DCCs default to meters. 100× scale errors result.
- **UsdSkel requires specific prim hierarchy** (skeleton + animation + bindings). Validate with `usdchecker`.
- **`oiiotool --colorconvert` requires `$OCIO` set.** Without, fails silently.
- **Frame sequences use 0-padded numbering** (`frame_0001.exr`). `frame_1.exr` ≠ `frame_0001.exr` in glob matching. Rename first if inconsistent.
- **OIIO TextureSystem caches aggressively.** Weird behaviour → `oiiotool --invalidate`.
- **`iinfo -v` on 4K EXR is fast; on 16K EXR it reads the whole file.** Use `--stats` for summary only.
- **ProRes `--profile:v 4` = 4444 (12-bit RGBA).** 422 HQ 10-bit YCbCr = color loss from EXR source.
- **IMF from VFX: J2K encoding of float EXR → int12/int16 loses dynamic range.** Author EXR → RGB int16 → J2K.
- **Nuke "DPX" ≠ SMPTE DPX.** Nuke adds a variant some downstream tools reject. Use `oiiotool` for standard DPX.

## Example — ARRI LogC plate → ACEScg comp → HDR10 IMF

ARRI footage LogC v3 → OCIO transform to ACEScg EXR (16-bit half ZIP) → handoff to comp → ingest comp EXR sequence → `oiiotool` color-convert ACEScg → Rec.2020 ST2084 ProRes 4444 XQ 12-bit → `ffmpeg-mxf-imf` J2K IMF.

## Related

- `workflow-hdr` — HDR mastering details.
- `workflow-broadcast-delivery` — IMF / MXF OP1a packaging.
- `workflow-editorial-interchange` — OTIO round-trip to the editor.
