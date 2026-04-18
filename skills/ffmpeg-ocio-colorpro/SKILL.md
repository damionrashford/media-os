---
name: ffmpeg-ocio-colorpro
description: >
  Professional color management with ffmpeg + OpenColorIO: ocio filter (OCIO config / LUT / colorspace transforms), ACES workflows (ACEScc / ACEScg / ACES2065-1), Resolve-compatible LUTs, film-emulation via OCIO, iccdetect, iccgen, ICC profile handling. Use when the user asks for ACES color management, apply an OCIO config, use a studio/film LUT, embed ICC profiles, convert between ACEScc/ACEScg/sRGB/Rec709/DCI-P3, do Resolve-grade post color workflows, or match DaVinci Resolve's color pipeline in ffmpeg.
argument-hint: "[config] [input]"
---

# FFmpeg OCIO ColorPro

**Context:** $ARGUMENTS

## Quick start

- **Check OCIO support:** → Step 1
- **Apply ACES → Rec.709:** → Step 2 + Step 3
- **Bake OCIO transform to .cube (fallback when filter missing):** → Gotchas + `bake-lut`
- **Embed ICC profile:** → Step 3 (`attach-icc`)

## When to use

- You want Resolve-grade color fidelity through ffmpeg (ACES, LMTs, film emulation).
- You need to convert between ACES spaces (ACES2065-1, ACEScg, ACEScc, ACEScct) and a display space (Rec.709, sRGB, DCI-P3 D65, Rec.2020 PQ).
- You must embed/detect ICC profiles for downstream compositing/web delivery.
- You want to match a Resolve .cube/OCIO pipeline exactly, without re-grading.

## Step 1 — Set OCIO config & check support

```bash
ffmpeg -hide_banner -filters | grep -i ocio   # expect "ocio" line if built with libOpenColorIO
export OCIO=/path/to/aces_1.3/config.ocio     # or ACES 2.0 studio-config
```

If `ocio` is **missing** from the filter list, jump to Gotchas → bake a `.cube` with `ociobake` and apply via the `lut3d` filter (see `ffmpeg-lut-grade`).

## Step 2 — Pick the transform (pinput → poutput)

- `pinput` = source color space. Typical: `ACES2065-1` (linear scene-referred, the ACES interchange), `ACEScc` / `ACEScct` (log grading spaces), `ACEScg` (rendering-linear for CGI), camera logs (`Input - ARRI - V3 LogC (EI800)`, `Input - Sony - S-Log3`, `Input - RED - Log3G10`).
- `poutput` = target display/encoding. Typical: `Output - Rec.709`, `Output - sRGB`, `Output - DCI-P3 D65`, `Output - Rec.2020 ST2084` (HDR10 PQ), `Output - Rec.2100 HLG`.

Names are **config-dependent** — run `ociocheck --iconfig $OCIO` or `pyociotools` to list exact strings.

## Step 3 — Run

```bash
# ACES2065-1 → Rec.709 (SDR)
ffmpeg -i in.exr -vf "format=gbrpf32le,ocio=pinput=ACES2065-1:poutput=Output - Rec.709,format=yuv420p" \
  -c:v libx264 -crf 16 out.mp4

# ACEScc (log grading) → DCI-P3 D65 (DCDM proxy)
ffmpeg -i graded.mov -vf "format=gbrpf32le,ocio=pinput=ACEScc:poutput=Output - DCI-P3 D65" \
  -c:v prores_ks -profile:v 3 out_dcip3.mov

# Apply a CDL / Look (LMT) from config
ffmpeg -i in.mov -vf "ocio=pinput=ACEScc:poutput=Output - Rec.709:look=LMT_Analog_Exposure" out.mov

# Attach ICC profile (bt709 primaries + sRGB TRC) on output
ffmpeg -i in.mov -vf "iccgen=primaries=bt709:trc=iec61966-2-1" -c copy out_icc.mkv

# Detect ICC in source
ffmpeg -i src.mkv -vf "iccdetect=force=1" -f null -
```

Use `scripts/colorpro.py` for a guarded wrapper:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/colorpro.py check
uv run ${CLAUDE_SKILL_DIR}/scripts/colorpro.py aces-to-rec709 --input in.exr --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/colorpro.py transform --input in.mov --output out.mov \
  --pinput "ACEScc" --poutput "Output - Rec.709"
uv run ${CLAUDE_SKILL_DIR}/scripts/colorpro.py bake-lut --config $OCIO \
  --pinput "ACES2065-1" --poutput "Output - Rec.709" --output aces_to_709.cube
uv run ${CLAUDE_SKILL_DIR}/scripts/colorpro.py attach-icc --input in.mov --output out.mkv \
  --primaries bt709 --trc iec61966-2-1
```

## Step 4 — Verify

- Visual QC with vectorscope/waveform via `ffmpeg-playback`:
  ```bash
  ffplay -vf "split=2[a][b];[a]vectorscope=m=color3[v];[b]waveform=m=1[w];[v][w]vstack" out.mp4
  ```
- Confirm container tags match the transform: primaries, transfer, matrix, range. Use `ffmpeg-probe` → `-show_streams`.
- For HDR/PQ delivery, cross-check with `ffmpeg-hdr-color` (MaxCLL/MaxFALL, mastering display metadata).
- For Netflix/studio IMF, audit with `ffmpeg-mxf-imf`.

## Gotchas

- **`ocio` filter requires ffmpeg built with `--enable-libocio`.** Most Homebrew/apt/chocolatey builds DO NOT include it — `ffmpeg -filters | grep ocio` tells the truth. If missing: (a) recompile ffmpeg against libOpenColorIO; (b) use `ociobake --inputspace X --outputspace Y --format cinespace --lutsize 33` to emit a `.cube`, then apply with `lut3d` (see `ffmpeg-lut-grade`).
- `$OCIO` environment variable **must** point at a config.ocio file — ffmpeg reads it via `getenv("OCIO")` unless you pass `config=/path`.
- ACES config versions differ: **1.0.3 / 1.1 / 1.2 / 1.3 / 2.0** use different role names and transform catalogs. An ACES 1.x pipeline is NOT drop-in compatible with ACES 2.0 (new Output Transforms, different naming). Pin your config version in the project.
- ACES color-space glossary: `ACES2065-1` = AP0 linear, interchange; `ACEScg` = AP1 linear, rendering/CGI; `ACEScc` = AP1 log, grading (pure log, no toe); `ACEScct` = AP1 log with a toe (closer to Cineon feel); `ACESproxy` = integer-quantized log for 10/12-bit transmission.
- Common ACES roles: `scene_linear`, `compositing_linear`, `rendering`, `aces_interchange`, `cie_xyz_d65_interchange`, `color_timing`, `texture_paint`, `data`, `matte_paint`.
- poutput spellings are literal & case-sensitive. Examples in ACES 1.3 studio-config: `Output - sRGB`, `Output - Rec.709`, `Output - Rec.2020 ST2084`, `Output - DCI-P3 D65`, `Output - Rec.2100 HLG`.
- ffmpeg's OCIO binding is **more limited than Nuke/Resolve/Blender** — some LMTs, display-referred looks, and GPU-only transforms may silently fall back or apply incorrectly. For deliveries, verify against a Resolve render.
- OCIO math is **floating-point**. Always bracket the filter with `format=gbrpf32le` on the input side and a target pixel format (e.g. `format=yuv420p10le`) on the output side to avoid quantization shocks.
- ICC profile embedding in **MP4 is limited** (iTunes-only `colr` atom semantics). Prefer **MKV or MOV** for ICC-tagged intermediates. `iccgen` builds an ICC from ffmpeg color tags (`primaries`, `trc`); `iccdetect` reads one from the input stream.
- **Rec.709 ≠ sRGB.** Same primaries, different transfer functions (Rec.709 is ~gamma 2.4 display; sRGB is piecewise linear + ~2.2). Don't swap them in web delivery.
- For **HDR out of OCIO** (e.g. ACES → HDR10 PQ BT.2020), set both the transform (`poutput="Output - Rec.2020 ST2084"`) AND the container color tags (`-colorspace bt2020nc -color_primaries bt2020 -color_trc smpte2084`) via `ffmpeg-hdr-color`.
- `DaVinci Resolve` exports .cube LUTs at 17/33/65 cube sizes; reuse via `lut3d` filter. OCIO `look` sections map 1:1 to Resolve Color Space Transforms only in v2.0+.

## Examples

### Example 1: ARRI LogC EXR plates → Rec.709 proxy (VFX review)

```bash
ffmpeg -start_number 1001 -i plate_%04d.exr \
  -vf "format=gbrpf32le,ocio=pinput=Input - ARRI - V3 LogC (EI800):poutput=Output - Rec.709,format=yuv420p" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  review_proxy.mp4
```

### Example 2: Graded ACEScc master → HDR10 deliverable

```bash
ffmpeg -i master_ACEScc.mov \
  -vf "format=gbrpf32le,ocio=pinput=ACEScc:poutput=Output - Rec.2020 ST2084,format=yuv420p10le" \
  -c:v libx265 -x265-params "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,50):max-cll=1000,400" \
  -pix_fmt yuv420p10le hdr10.mp4
```

### Example 3: Film look via OCIO LMT

```bash
ffmpeg -i in.mov -vf "ocio=pinput=ACEScct:poutput=Output - Rec.709:look=Kodak_2383_D65" out_kodak2383.mov
```

### Example 4: Fallback — bake .cube, apply with lut3d (no libocio build)

```bash
ociobake --iconfig $OCIO --inputspace "ACES2065-1" --outputspace "Output - Rec.709" \
  --format cinespace --lutsize 33 > aces_to_709.cube
ffmpeg -i in.exr -vf "format=gbrpf32le,lut3d=aces_to_709.cube,format=yuv420p" out.mp4
```

## Troubleshooting

### Error: `No such filter: 'ocio'`

Cause: ffmpeg built without libOpenColorIO.
Solution: Rebuild with `--enable-libocio`, or bake the transform with `ociobake` and apply via `lut3d`.

### Error: `Could not find colorspace 'Output - Rec.709'`

Cause: The active `$OCIO` config uses a different name (e.g. ACES 2.0 calls it `Rec.709 - Display`).
Solution: `ociocheck --iconfig $OCIO` and list colorspaces; use the exact string.

### Output looks washed out / over-saturated

Cause: Double display transform (e.g. applying ACES OutputTransform then also re-tagging as sRGB), or missing `format=gbrpf32le` stage causing int8 clipping before the transform.
Solution: Ensure a single display transform; always bracket with float format; verify container tags are untouched.

### ICC profile not honored in browser

Cause: MP4 container strips/ignores embedded ICC in most players.
Solution: Deliver as MKV/MOV for ICC; for web, rely on `colr` primaries/trc tags and assume sRGB/Rec.709 rendering intent.

## Reference docs

- [`references/ocio.md`](references/ocio.md) — ACES config version matrix, role names, colorspace catalog, ociobake usage, vendor log spaces, recipe book.

## Related skills

- `ffmpeg-lut-grade` — lut3d/haldclut application, ideal fallback when libocio is absent.
- `ffmpeg-hdr-color` — HDR primaries/TRC tagging, tone-mapping.
- `ffmpeg-playback` — vectorscope/waveform QC.
- `ffmpeg-probe` — verify color tags on output.
- `ffmpeg-mxf-imf` — studio IMF deliverables.
