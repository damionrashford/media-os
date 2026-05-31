# Mode: vfx-pipeline

**Subagent**: `architect`
**Trigger phrases**: "VFX conform", "EXR to master", "ACES pipeline", "USD scene", "OCIO conform", "OpenColorIO", "color management", "EXR sequence", "dailies turnaround", "VFX deliver"
**Output**: `${MEDIA_WORK_DIR}/modes/vfx-pipeline/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — EXR sequence (file pattern `frame_%06d.exr`), DPX sequence, or USD stage.
  - `target_space` — final color space: `rec709-display`, `rec2020-pq`, `aces-rec709`, `aces-rec2020-pq`, `dcdm-p3`.
- **Optional**:
  - `working_space` — `acescg` (default), `aceslog`, `linear-rec709`.
  - `ocio_config` — path to OCIO config (default: ACES Studio Config 1.3).
  - `frame_range` — `1-1000` (default: all frames in sequence).
  - `lut` — additional creative LUT to apply after working-to-target conform.

## Steps

1. Read tool skills: `vfx-oiio`, `vfx-openexr`, `vfx-usd`, `ffmpeg-ocio-colorpro`, `ffmpeg-lut-grade`, `ffmpeg-hdr-color`.
2. Use `oiiotool --info <source-frame>` to capture per-channel bit depth, compression (PIZ/ZIPS/DWA/none), color space metadata (if `acesImage` chroma tag present), display window vs data window.
3. For EXR sequences: verify all frames in `frame_range` exist (`ls <pattern>` count vs expected). Surface missing frames as a STOP condition.
4. For USD stages: `usdview --no-window` headless render via Hydra (Storm/RTX) to produce an EXR sequence.
5. Validate `working_space` and `target_space` exist in the OCIO config (`ociocheck --inputconfig <ocio_config>` plus enum lookup).
6. Build the conform graph per `ffmpeg-ocio-colorpro` SKILL.md:
   - For ACES → Rec.709: `OCIOColorSpace inputspace=ACEScg outputspace="Output - Rec.709"`.
   - For Rec.2020 PQ delivery: `OCIOColorSpace inputspace=ACEScg outputspace="Utility - Linear - Rec.2020"` → then `zscale=t=linear:p=2020:m=2020nc → format=gbrpf32le → zscale=p=bt2020:t=smpte2084` for PQ encode.
   - Apply `lut` after the working-to-target conform (creative grade goes last).
7. **`mosafe`-wrap** the ffmpeg invocation (especially the zscale sandwich for HDR conform).
8. Encode out to ProRes 4444 (mezzanine) OR JPEG 2000 IMF (for IMF delivery) OR per-frame target sequence.
9. If target is HDR, write SEI/static metadata (`-metadata:s:v:0 mastering_display_metadata=...`).
10. Run `oiiotool --colorconvert <working> <target>` on a representative frame as a numerical sanity check (compare pixel values to a known reference).
11. Write `summary.md` with frame count, color path graph, codec/bit depth choices, runtime.

## Output schema

```markdown
# VFX pipeline — {slug} — {date}

## Source
- **Type**: {EXR sequence / DPX sequence / USD stage}
- **Frame range**: {start-end} ({total} frames)
- **Source space**: {ACEScg / linear-Rec.709 / scene-linear}
- **Bit depth**: {16-bit half / 32-bit float}
- **EXR compression** (if EXR): {PIZ / ZIPS / DWA / none}

## Color path
- **OCIO config**: {path}
- **Working space**: {acescg / aceslog / linear-rec709}
- **Target space**: {rec709-display / rec2020-pq / aces-rec709 / aces-rec2020-pq / dcdm-p3}
- **Creative LUT applied**: {path or none}

## Output
- **Codec**: {ProRes 4444 / JPEG 2000 / EXR sequence / DPX sequence}
- **Container**: {QuickTime MOV / MXF IMF / sequence}
- **Frame count out**: {N}
- **HDR metadata**: {present / N/A}
- **File / sequence path**: {path}

## Reference frame check
- Test frame: {frame N}
- Pre-conform pixel sample at (x,y): {R,G,B}
- Post-conform pixel sample at same (x,y): {R,G,B}
- Match against expected target value (if reference provided): {pass / fail / N/A}
```

## Quality bar

- Every frame in `frame_range` exists at start; missing frames surfaced (don't silently fill black).
- Color space conform passes the reference-frame pixel check (within ±1% tolerance for float conversions).
- Bit depth preserved through working space (never collapse to 8-bit mid-pipeline).
- For HDR target: SEI/static metadata present in output; mosafe confirmed zscale sandwich correct.
- For IMF target: hand-off to `broadcast-delivery` mode for OPL/CPL/PKL generation.
- LUT application is the LAST step (creative grade after technical conform).

## Playbook reference (folded from workflow-vfx-pipeline)

**What:** Handle VFX-grade media interchange. Color-managed ACES throughout, EXR as the float-linear format, USD for scene descriptions, clean handoffs to compositors and back to editorial.

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
