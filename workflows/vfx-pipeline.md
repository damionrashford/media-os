# VFX Pipeline Workflow

**What:** Where FFmpeg stops and film-grade VFX pipelines begin. Read/write USD scene description, process deep and multi-part OpenEXR, use OpenImageIO for 100+ format color-managed I/O, integrate ACES via OCIO, and hand off clean deliverables back to traditional transcoding.

**Who:** VFX supervisors, compositors, DITs, color scientists, studios integrating Maya / Houdini / Nuke / Blender / Resolve with a programmatic pipeline.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| USD scene description | `vfx-usd` | `usdcat` / `usdview` / `usdedit`, LIVRPS composition |
| OpenEXR I/O | `vfx-openexr` | Deep / multi-part / multi-view, `exrheader` / `exrinfo` / `exrenvmap` |
| OpenImageIO | `vfx-oiio` | `oiiotool` / `iconvert` / `iinfo`, color-managed read/write |
| OCIO color | `ffmpeg-ocio-colorpro` | ACES config, transforms during ffmpeg |
| CLUT / LUTs | `ffmpeg-lut-grade` | 1D/3D LUTs, Hald CLUT |
| Probe / QC | `ffmpeg-probe`, `media-mediainfo` | Verify deliverable specs |
| HDR / color space | `ffmpeg-hdr-color` | PQ / HLG / BT.2020 / BT.709 conversions |
| Sequence I/O | `ffmpeg-frames-images` | DPX / EXR / TIFF sequence → video |
| Deliverable | `ffmpeg-transcode`, `ffmpeg-mxf-imf` | ProRes / DNxHR / IMF J2K |
| Editorial hand-back | `otio-convert` | Send VFX plates out / conform comps back |

---

## The pipeline

### 1. Inspect an OpenEXR sequence

```bash
# Deep info on a single frame
uv run .claude/skills/vfx-openexr/scripts/exrctl.py header \
  --input frames/0001.exr

# Summary of all channels, compression, chromaticities
uv run .claude/skills/vfx-openexr/scripts/exrctl.py info \
  --input frames/0001.exr --verbose
```

Look for:
- **Channel set**: RGB / RGBA / Y / BY / RY / Z / custom AOVs (beauty, diffuse, specular, id, uv, p_world, normal)
- **Compression**: ZIP / ZIPS / PIZ / B44 / B44A / PXR24 / DWAA / DWAB
- **Chromaticities**: tells you the color space — check if ACES (wg ACEScg) vs Rec.709 vs sRGB
- **Multi-part**: deep-comp / cryptomatte / layer-separated passes
- **Multi-view**: stereo (`left` / `right`) for 3D

### 2. Inspect a USD stage

```bash
uv run .claude/skills/vfx-usd/scripts/usdctl.py info \
  --input shot.usda

uv run .claude/skills/vfx-usd/scripts/usdctl.py flatten \
  --input shot.usda --output shot-flat.usda
```

USD's LIVRPS composition order: **L**ocal, **I**nherits, **V**ariantSets, **R**eferences, **P**ayloads, **S**pecializes. Every override you see in `usdview` is resolved through that stack. To debug "why is this attribute this value?":

```bash
uv run .claude/skills/vfx-usd/scripts/usdctl.py resolve-info \
  --input shot.usda --prim /World/Camera --attribute focalLength
```

### 3. Color pipeline setup

ACES + OCIO is the VFX standard. Set up once, use everywhere:

```bash
# Typical studio config
export OCIO=/opt/aces/config-aces-v1.3_studio-config-v3.0.0/config.ocio

# Check what transforms are available
uv run .claude/skills/ffmpeg-ocio-colorpro/scripts/ociogo.py list-transforms
```

ACES working space decisions:
- **Linear ACEScg** (AP1) for compositing — the default working space
- **Linear ACES2065-1** (AP0) for interchange / archival
- **Output - Rec.709** for SDR review
- **Output - Rec.2020 ST2084** for HDR10 delivery
- **Output - Rec.2020 HLG** for HDR HLG delivery

### 4. Convert an EXR sequence to ProRes for dailies

```bash
# Using oiiotool for color managed conversion
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "frames/%04d.exr" \
  --output dailies.mov \
  --colorspace-in "ACES - ACEScg" \
  --colorspace-out "Output - Rec.709" \
  --codec prores \
  --quality 422HQ \
  --framerate 23.976
```

Alternative with ffmpeg + OCIO filter:
```bash
ffmpeg -framerate 23.976 -i "frames/%04d.exr" \
  -vf "ocio=config=$OCIO:colorspace_in=ACES - ACEScg:colorspace_out=Output - Rec.709" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -c:a copy dailies.mov
```

### 5. Generate plates for VFX vendors

**LIN-LIN ACEScg EXR plates (working space):**
```bash
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input camera-original.mov \
  --output "plates/shot_001/%04d.exr" \
  --colorspace-in "Input - ARRI - LogC3" \
  --colorspace-out "ACES - ACEScg" \
  --compression zip \
  --bit-depth 16
```

**Proxy plates for review (Rec.709):**
```bash
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input camera-original.mov \
  --output "proxies/shot_001/%04d.jpg" \
  --colorspace-in "Input - ARRI - LogC3" \
  --colorspace-out "Output - Rec.709" \
  --quality 90
```

### 6. Ingest comps back from vendor

VFX vendor returns an EXR sequence. Verify:

```bash
# 1. Check color space matches (ACEScg?)
uv run .claude/skills/vfx-openexr/scripts/exrctl.py header \
  --input "comps/shot_001/0001.exr" | grep -i chromaticities

# 2. Check resolution + duration matches plate
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py info \
  --input "comps/shot_001/%04d.exr"

# 3. Round-trip to Rec.709 review
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "comps/shot_001/%04d.exr" \
  --output review.mov \
  --colorspace-in "ACES - ACEScg" \
  --colorspace-out "Output - Rec.709" \
  --codec prores --quality 422HQ
```

### 7. Cryptomatte extraction

Cryptomattes are multi-part EXR with hashed IDs enabling ID-level mattes without pre-baking:

```bash
uv run .claude/skills/vfx-openexr/scripts/exrctl.py list-parts \
  --input comp.exr
# Parts: main, crypto00, crypto01, crypto02

uv run .claude/skills/vfx-openexr/scripts/exrctl.py extract-part \
  --input comp.exr --part crypto00 --output cryptomatte.exr
```

Then use an external cryptomatte extractor (Nuke node, or `cryptomatte` Python library) to isolate specific IDs.

### 8. USD-driven render submission

USD is Pixar's DCC-neutral scene format. Compose shots without opening Maya/Houdini:

```bash
# Reference a layout into a shot
uv run .claude/skills/vfx-usd/scripts/usdctl.py reference \
  --stage shot.usda \
  --prim /World/Set \
  --reference /library/sets/warehouse.usda
```

### 9. Handoff to editorial

Compositor delivers final shot as an EXR sequence or a ProRes master. Editorial needs the ProRes conform:

```bash
# Final master at ACEScg → Rec.2020 HDR
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "finals/shot_001/%04d.exr" \
  --output shot_001_hdr.mov \
  --colorspace-in "ACES - ACEScg" \
  --colorspace-out "Output - Rec.2020 ST2084" \
  --codec prores --quality 4444XQ

# Or send to IMF for streaming
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py imf \
  --video shot_001_hdr.mov \
  --output-dir IMF/shot_001 \
  --image-codec j2k
```

### 10. Send back to OTIO / NLE

```bash
# Emit FCPXML for the editor to re-link
uv run .claude/skills/otio-convert/scripts/otioctl.py emit \
  --from shot_manifest.json --output show.fcpxml --adapter fcpx_xml
```

---

## Variants

### Stereo 3D (left/right eye) workflow

OpenEXR supports multi-view natively. Each view is a separate set of channels or a separate "part":

```bash
# Inspect multi-view
uv run .claude/skills/vfx-openexr/scripts/exrctl.py header \
  --input stereo-frame.exr | grep multiView

# Extract left eye as separate sequence
uv run .claude/skills/vfx-openexr/scripts/exrctl.py extract-view \
  --input "frames/%04d.exr" \
  --view left \
  --output "left/%04d.exr"
```

Or go direct to ffmpeg-360-3d for side-by-side stereo delivery:
```bash
uv run .claude/skills/ffmpeg-360-3d/scripts/s3d.py compose \
  --left left.mov --right right.mov --layout sbs --output stereo.mov
```

### Deep compositing

Deep EXR has Z-layers per pixel (front-to-back samples) — enables true volumetric compositing:

```bash
uv run .claude/skills/vfx-openexr/scripts/exrctl.py deep-info \
  --input deep.exr

# Flatten deep → flat (for ffmpeg compatibility)
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py deep-to-flat \
  --input deep.exr --output flat.exr
```

### Environment maps / HDRI

```bash
# Create a latlong (2:1) environment map
uv run .claude/skills/vfx-openexr/scripts/exrctl.py envmap \
  --input cubemap.exr \
  --output latlong.exr \
  --type latlong
```

### ARRI LogC / Sony SLog / RED Log → ACEScg

Common DIT path — camera log → linear ACES → working space:

| Source | OCIO transform |
|---|---|
| ARRI Alexa LogC3 (EI 800) | `Input - ARRI - LogC (v3-EI800) - Wide Gamut` |
| Sony SLog3 SGamut3 | `Input - Sony - SLog3 - S-Gamut3` |
| RED RWG Log3G10 | `Input - RED - REDlogFilm - REDWideGamutRGB` |
| Canon CLog3 Cinema Gamut | `Input - Canon - CLog3 - Cinema Gamut` |
| BMD Film Gen 4/5 | `Input - Blackmagic - Blackmagic Film Generation 5` |

```bash
# ARRI → ACEScg
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "arri/%04d.ari" \
  --output "acescg/%04d.exr" \
  --colorspace-in "Input - ARRI - LogC (v3-EI800) - Wide Gamut" \
  --colorspace-out "ACES - ACEScg" \
  --compression zips --bit-depth 16
```

### USD-driven batch render

Use USD to parameterize shots:

```bash
# Override camera focal length per shot
for shot in A B C; do
  uv run .claude/skills/vfx-usd/scripts/usdctl.py override \
    --stage base.usda \
    --prim /World/Camera \
    --attribute focalLength \
    --value 35 \
    --output "shot-${shot}.usda"
  # Submit shot-${shot}.usda to your renderer
done
```

---

## Gotchas

### Color management

- **ACEScg (AP1) vs ACES2065-1 (AP0)**. ACEScg is the working space for compositing (smaller gamut, fits BT.2020). ACES2065-1 is the wide-gamut archival format. Don't composite in AP0 — it's for interchange only.
- **OCIO config must match everything else.** A config mismatch between oiiotool + ffmpeg + Nuke renders differently. Always export `OCIO` env var from the same path.
- **EXR chromaticities field is the source of truth.** If absent, tools assume Rec.709/sRGB — which is wrong for ACES data. Always write chromaticities when producing EXR.
- **`ocio` ffmpeg filter requires libOpenColorIO-enabled build.** `brew install ffmpeg` includes it on recent versions; `ffmpeg -filters | grep ocio` to confirm.
- **Rec.709 display output assumes sRGB gamma on most monitors, but broadcast uses BT.1886 gamma (~2.4 pure power).** Confirm what the target is. OCIO has `Output - sRGB` vs `Output - Rec.709` as distinct transforms.

### EXR specifics

- **Compression choice matters**: ZIP = lossless, slow. ZIPS = scanline ZIP (faster reads). PIZ = lossless with good compression for natural imagery. B44 = lossy half-float-optimized. DWAA/DWAB = very high-quality lossy, disk-cheap. For archival: ZIP or PIZ. For dailies turnaround: DWAA.
- **Scanline EXR vs tiled EXR.** Scanline is the default; tiled enables random access but needs tile-aware renderers (Nuke handles both).
- **Multi-part vs multi-channel.** Multi-part = discrete OpenEXR "parts" inside one file, each with independent channels/compression/chromaticities (better for deep/crypto). Multi-channel = all AOVs in one part (simpler, Nuke preference). Compositor expectations vary — confirm before delivery.
- **Half-float (16-bit) has limited range** — around 65504 max value. HDR scenes with very bright values may clip. Use 32-bit float for HDRI environment maps.
- **Deep EXR `deep-samples-per-pixel` is variable.** Memory footprint can balloon; processing tools must be deep-aware or they'll flatten silently.

### USD specifics

- **LIVRPS composition order is CRITICAL.** An override in a stronger layer always wins. If you set an attribute and it doesn't stick, something stronger is overriding it — use `resolve-info` to find the culprit.
- **USD references vs payloads**. References always load. Payloads lazy-load (unload by default in a session — reduces initial open time). Use payloads for large sets; references for small overrides.
- **USD variants are authoring-time, not runtime.** A variantSet "lookStyle" with variants {blue, red, green} switches at authoring — downstream tools see the resolved variant only.
- **`.usda` is ASCII (readable). `.usdc` is binary (fast). `.usdz` is a zipped bundle (for shipping).** Never edit .usdc by hand — always open, modify, save via usdedit or a Python API.
- **USD unit system defaults to centimeters.** Many DCCs default to meters. Get this wrong = 100x-scale objects.
- **UsdSkel for skinning**: requires a specific prim hierarchy (skeleton + animation + bindings). Check with `usdchecker`.

### OIIO / tooling

- **`oiiotool` `--colorconvert` requires a valid OCIO config** in OCIO env. Without one, it fails silently (no conversion applied).
- **Sequence reading `%04d.exr` in oiiotool/ffmpeg uses 0-padded integers.** `frame_1.exr` ≠ `frame_0001.exr`. Rename first if mixed.
- **OIIO TextureSystem caches heavily.** Clear if weird results: `oiiotool --invalidate`.
- **`iinfo -v` on a 4K EXR is fast; on a 16K EXR it reads the whole file.** Use `--stats` for summary-only.
- **`prores_ks --profile:v 4` (4444) is 12-bit RGBA, suitable for ingesting EXR→ProRes without clipping.** 422HQ is 10-bit YCbCr — color information loss for EXR input.

### Deliverable

- **IMF from VFX**: J2K encoding of float EXR → int12/int16 J2K loses dynamic range. Author EXR → RGB int16 → J2K. Check `j2kenc_openjpeg` supports your precision.
- **Nuke's "DPX" ≠ SMPTE DPX**. Nuke writes a specific DPX variant; downstream tools may reject. Use oiiotool to convert to SMPTE-standard DPX if issues.

---

## Example — "Camera log footage → ACES → VFX plates → comp back → IMF delivery"

```bash
#!/usr/bin/env bash
set -e

export OCIO=/opt/aces/config-aces-v1.3_studio-config-v3.0.0/config.ocio

CAMERA_MOV="camera/A001_C001.mov"
PLATE_DIR="plates/shot_001"
COMP_DIR="comps/shot_001"
FINAL_MOV="final/shot_001.mov"
IMF_DIR="IMF"

# 1. Camera → ACEScg plates (for VFX vendor)
mkdir -p "$PLATE_DIR"
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "$CAMERA_MOV" \
  --output "$PLATE_DIR/%04d.exr" \
  --colorspace-in "Input - ARRI - LogC (v3-EI800) - Wide Gamut" \
  --colorspace-out "ACES - ACEScg" \
  --compression zips \
  --bit-depth 16

# 2. Vendor delivers comps back into COMP_DIR. Verify.
uv run .claude/skills/vfx-openexr/scripts/exrctl.py header \
  --input "$COMP_DIR/0001.exr" > /dev/null  # fails if bad

FRAMES=$(ls "$PLATE_DIR" | wc -l)
COMPS=$(ls "$COMP_DIR" | wc -l)
if [ "$FRAMES" != "$COMPS" ]; then
  echo "Frame count mismatch: plate=$FRAMES comp=$COMPS"; exit 1
fi

# 3. Comp → HDR Rec.2020 ST2084 master
mkdir -p "$(dirname $FINAL_MOV)"
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "$COMP_DIR/%04d.exr" \
  --output "$FINAL_MOV" \
  --colorspace-in "ACES - ACEScg" \
  --colorspace-out "Output - Rec.2020 ST2084" \
  --codec prores --quality 4444XQ \
  --framerate 23.976

# 4. QC
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$FINAL_MOV"

# 5. IMF delivery
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py imf \
  --video "$FINAL_MOV" \
  --output-dir "$IMF_DIR/shot_001" \
  --cpl-title "Show_Shot001_HDR" \
  --image-codec j2k

echo "Done. IMF at $IMF_DIR/shot_001"
```

---

## Further reading

- [`broadcast-delivery.md`](broadcast-delivery.md) — IMF authoring from VFX masters
- [`hdr-workflows.md`](hdr-workflows.md) — HDR color pipeline details
- [`editorial-interchange.md`](editorial-interchange.md) — getting OTIO plates out, comps back in
- [`analysis-quality.md`](analysis-quality.md) — QC on VFX deliverables
