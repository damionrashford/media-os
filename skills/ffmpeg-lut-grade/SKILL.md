---
name: ffmpeg-lut-grade
description: >
  Color grading and LUT application with ffmpeg: lut3d (.cube/.3dl), lut1d, haldclut, colorbalance, selectivecolor, colormatrix, colorlevels, colorchannelmixer, hue. Use when the user asks to apply a LUT, apply a .cube file, color grade, do a cinematic look, apply a film emulation, adjust shadows/midtones/highlights independently, apply a Hald CLUT, fix color cast, or match color between clips.
argument-hint: "[lut-file] [input]"
---

# Ffmpeg Lut Grade

**Context:** $ARGUMENTS

## Quick start

- **Apply a .cube LUT:** → Step 1 (LUT file path) → Step 2 (`lut3d` with `interp=tetrahedral`)
- **Apply a Hald CLUT PNG:** → Step 1 (pick `haldclut`) → Step 2 (`-filter_complex [0][1]haldclut`)
- **Grade without a LUT (balance/curves):** → Step 1 (pick filter-based) → Step 3 (stack correctly)
- **Match two clips:** → Step 3 (per-clip LUT + manual colorbalance trim)
- **Fix legacy BT.601 → BT.709:** → Step 1 (`colormatrix`)

## When to use

- You have a `.cube`, `.3dl`, or Hald CLUT PNG and need to bake the look into a render.
- You need non-destructive primary/secondary color correction (balance, selective color, levels).
- You need to normalize legacy broadcast footage (BT.601 ↔ BT.709 matrix).
- You want to match shot-to-shot color after editing.

Do **not** use this skill for HDR → SDR tone-mapping (see `ffmpeg-hdr-color`), denoise
(`ffmpeg-denoise-restore`), or generic video filters like scale/crop
(`ffmpeg-video-filter`).

## Step 1 — Pick the grading tool

Decide by asset, not vibe:

| You have                                | Use                                                     |
| --------------------------------------- | ------------------------------------------------------- |
| `.cube` or `.3dl` file                  | `lut3d=file='look.cube':interp=tetrahedral`             |
| 1D LUT (`.cube` with `LUT_1D_SIZE`)     | `lut1d=file='look.cube'`                                |
| Hald CLUT PNG (graded identity image)   | `[0][1]haldclut=interp=tetrahedral` (filter_complex)    |
| Need R/G/B tint per zone                | `colorbalance` (shadows/mids/highlights)                |
| Want only reds/skin/sky shifted         | `selectivecolor`                                        |
| Legacy BT.601 tagged as BT.709 (or v.v.)| `colormatrix=bt601:bt709` (legacy, non-ICtCp)           |
| Crush shadows / recover highlights      | `colorlevels`                                           |
| Channel-mix R/G/B                       | `colorchannelmixer`                                     |
| Hue rotate / desaturate                 | `hue=h=15:s=0.9`                                        |
| Brightness/contrast/gamma/saturation    | `eq` (see `ffmpeg-video-filter` for full table)         |
| False-color exposure analysis           | `pseudocolor=preset=heat`                               |

Validate the LUT file exists and has the expected header (see `references/filters.md`
"`.cube` spec"). If the LUT is a Hald identity that hasn't been graded yet, applying it
is a no-op — confirm it's the graded version.

## Step 2 — Apply it and verify

### Apply .cube (most common)

```bash
ffmpeg -i in.mp4 -vf "lut3d=file='look.cube':interp=tetrahedral" \
  -c:v libx264 -crf 18 -c:a copy out.mp4
```

### Apply Hald CLUT

```bash
ffmpeg -i in.mp4 -i clut.png \
  -filter_complex "[0:v][1:v]haldclut=interp=tetrahedral" \
  -c:v libx264 -crf 18 -c:a copy out.mp4
```

### Filter-based grade (no LUT file)

```bash
# Warm shadows, cool highlights
ffmpeg -i in.mp4 -vf "colorbalance=rs=.15:gs=.05:bs=-.1:rh=-.1:gh=.0:bh=.1" \
  -c:v libx264 -crf 18 out.mp4

# Reduce red saturation (skin safety or red-dominant scenes)
ffmpeg -i in.mp4 -vf "selectivecolor=reds=0 0 -0.5 0" \
  -c:v libx264 -crf 18 out.mp4

# Shadow crush + highlight roll-off
ffmpeg -i in.mp4 -vf "colorlevels=rimin=0.05:gimin=0.05:bimin=0.05:romax=0.95:gomax=0.95:bomax=0.95" \
  -c:v libx264 -crf 18 out.mp4
```

### Legacy matrix conversion

```bash
# SD footage tagged 709 that actually carries 601 primaries
ffmpeg -i sd.mxf -vf "colormatrix=bt601:bt709" -c:v libx264 -crf 18 out.mp4
```

### Verify with vectorscope / waveform (ffplay)

```bash
ffplay -i out.mp4 -vf "split=2[a][b];[b]vectorscope=mode=color3[c];[a][c]hstack"
ffplay -i out.mp4 -vf "waveform=intensity=0.1:mode=column:display=overlay:components=7"
```

Skin tones should land on the flesh-line at ~10-11 o'clock on the vectorscope; clipped
channels park on the outer ring.

## Step 3 — Stack grading ops correctly

Grading is **non-commutative**. Recommended chain order (coarsest → finest):

1. `format=rgb24` (or `zscale` to linear) — ensure LUT sees RGB if the LUT is RGB-domain.
2. `eq` (exposure / contrast baseline) — optional; many colorists skip and use levels.
3. `colorbalance` or `colorchannelmixer` — primary white balance / cast fix.
4. `lut3d` / `haldclut` — the creative look.
5. `selectivecolor` — secondary corrections (skin, sky) on top of the look.
6. `colorlevels` — final output range shaping.
7. Output: `format=yuv420p` for H.264/H.265 compatibility.

Full chain example (teal-and-orange):

```bash
ffmpeg -i in.mov -vf \
  "format=rgb24,\
   colorbalance=rs=.05:bs=-.05:rh=-.05:bh=.08,\
   lut3d=file='teal_orange.cube':interp=tetrahedral,\
   selectivecolor=reds=0 0 0.2 0:yellows=-0.1 0 0.1 0,\
   colorlevels=rimin=0.02:gimin=0.02:bimin=0.02,\
   format=yuv420p" \
  -c:v libx264 -crf 18 -c:a copy out.mp4
```

Match two clips A and B (different cameras, same scene):

```bash
# Clip A: apply camera-A LUT + subtle cool
ffmpeg -i A.mov -vf "lut3d=file='camA_to_rec709.cube',colorbalance=bh=.03" -c:v prores -profile:v 3 A_match.mov
# Clip B: apply camera-B LUT + subtle warm
ffmpeg -i B.mov -vf "lut3d=file='camB_to_rec709.cube',colorbalance=rh=.03" -c:v prores -profile:v 3 B_match.mov
```

## Available scripts

- **`scripts/grade.py`** — thin wrapper around the filters above. Subcommands:
  `lut`, `haldclut`, `balance`, `selective`, `match-bt601-to-bt709`.
  Validates `.cube` path, supports `--dry-run` and `--verbose`, stdlib only.

Usage examples:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py lut \
  --input in.mp4 --lut look.cube --output out.mp4 --interp tetrahedral

uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py haldclut \
  --input in.mp4 --clut clut.png --output out.mp4

uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py balance \
  --input in.mp4 --output out.mp4 \
  --shadows 0.15,0.05,-0.1 --mids 0,0,0 --highlights -0.1,0,0.1

uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py selective \
  --input in.mp4 --output out.mp4 --color reds --adjust 0,0,-0.5,0

uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py match-bt601-to-bt709 \
  --input in.mxf --output out.mp4
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for full option tables
  (lut3d, lut1d, haldclut, colorbalance, selectivecolor, colormatrix, colorlevels,
  colorchannelmixer, hue, pseudocolor), `.cube` spec, Hald identity generator, the
  recommended chain order, and a recipe book (teal-and-orange, bleach bypass,
  cross-process, sepia, B&W with tinted shadows, skin-tone protection).

## Gotchas

- **`interp=tetrahedral` beats `trilinear`** for nearly all .cube LUTs — smoother
  gradients, no visible banding at hue transitions. Prefer it unless you need
  bit-exact match with another NLE that used trilinear.
- **`.cube` supports LUT_3D_SIZE 17, 33, 64, 128** in ffmpeg. Comments start with `#`.
  `DOMAIN_MIN` / `DOMAIN_MAX` outside `0.0 1.0` means the LUT expects extended range
  (log footage) — converting to Rec.709 first will clip it.
- **Hald CLUT requires a *graded* identity PNG**, not the raw identity. Someone runs
  the identity through Photoshop/Affinity/DaVinci, saves, and hands you the result.
  Applying the raw identity is a no-op.
- **Order matters.** `eq` → `lut3d` → `colorbalance` bakes contrast into the LUT input;
  `lut3d` → `colorbalance` lets you push tint without affecting the LUT shape.
  Document intent; don't swap silently.
- **LUTs baked in Rec.709 assume Rec.709 input.** Feeding sRGB, log, or HDR to a
  Rec.709 LUT produces wrong colors. Convert first with `colorspace` / `zscale`, or
  use a matching log-to-Rec709 LUT (e.g. Slog3, LogC, VLog).
- **`selectivecolor` values are space-separated 4-tuples `C M Y K`, not commas.**
  `selectivecolor=reds=0 0 -0.5 0` is correct; `reds=0,0,-0.5,0` is an error.
- **`colorbalance` range is roughly -1..1** but anything over `0.2` on any axis is
  usually too strong and crushes the channel. Start at `0.05`.
- **GPU LUT?** `lut3d` runs on CPU. For hardware-accelerated grading, use
  `libplacebo` with `custom_lut='look.cube'` (Vulkan) or VAAPI's `lut3d` variant on
  Linux Intel.
- **Hald CLUT level 8 = 512×512** is the common size. Level 6 = 216×216 is faster but
  loses precision. Always verify with an identity round-trip.
- **Two LUTs back-to-back compound interpolation error.** Bake one accurate LUT in
  a grading app instead of stacking.
- **Most `.cube` LUTs are RGB-domain.** If input is YUV, insert `format=rgb24` before
  `lut3d` — otherwise ffmpeg auto-converts but may pick a narrower pixel format.
- **Verify with `vectorscope`.** Skin tones should sit on the flesh-line at ~10-11
  o'clock. Clipped channels appear as bright spots on the outer ring.
- **Never apply a LUT *after* HDR→SDR tone-mapping** unless the LUT was specifically
  designed for the mapped output. Tone-map → 709 → LUT is almost always wrong;
  LUT-at-log → tone-map is correct for log sources.

## Examples

### Example 1: Apply a film emulation .cube to a MOV

Input: `raw.mov` (ProRes, Rec.709, 1080p), LUT `kodak2383.cube` (17^3).
Steps: `lut3d=file='kodak2383.cube':interp=tetrahedral` → x264 CRF 18.
Result: `graded.mp4` with film print look baked in; source untouched.

### Example 2: Match camera-A to camera-B on a two-camera interview

Input: `A.mov` (FX3, Slog3), `B.mov` (A7S3, Rec709).
Steps: Apply `slog3_to_rec709.cube` to A; apply mild `colorbalance=bh=.02` to B.
Result: Both clips on the same Rec.709 baseline; fine-tune with `selectivecolor`
on skin if needed.

### Example 3: Hald CLUT from a Photoshop action

Input: `trip.mp4`, `hald_level8_graded.png` (someone ran an LR preset over the
identity and exported).
Steps: `[0:v][1:v]haldclut=interp=tetrahedral` in `-filter_complex`.
Result: Photoshop-preset look on video, deterministic and repeatable.

## Troubleshooting

### Error: `Unable to parse option value "..." for 'file'`

Cause: Path has a space or special char and isn't single-quoted inside the filter.
Solution: Quote the path inside the filter graph: `lut3d=file='My LUTs/look.cube'`.

### Output looks washed out / low-contrast

Cause: LUT expects log input but you fed it Rec.709; LUT is designed to *expand*
log to 709, so a Rec.709-in → Rec.709 LUT produces flat results.
Solution: Confirm the LUT's intended input space. Use a matching LUT or skip it.

### Output has visible banding in gradients

Cause: `interp=nearest` or `trilinear`, or 8-bit pipeline with an aggressive LUT.
Solution: `interp=tetrahedral`. For stronger grades, encode output at 10-bit
(`-pix_fmt yuv420p10le -c:v libx265` or ProRes).

### `haldclut` fails with "Invalid frame dimensions"

Cause: CLUT PNG isn't a valid Hald size (`level^3 × level^3` pixels, so level 8 =
512×512, level 6 = 216×216).
Solution: Regenerate the identity via
`ffmpeg -f lavfi -i haldclutsrc=level=8 -frames:v 1 hald_identity.png`, regrade it,
and retry.

### `selectivecolor` throws "Option not found" / zero effect

Cause: Commas used instead of spaces inside the 4-tuple.
Solution: `selectivecolor=reds=0 0 -0.5 0` (spaces, not commas). Quote the whole
filter arg in shell: `-vf "selectivecolor=reds=0 0 -0.5 0"`.

### Colors look right on your monitor but wrong on web / phones

Cause: Output tagged with non-standard primaries/transfer, or pipeline stripped tags.
Solution: End the chain with `format=yuv420p` and re-tag:
`-colorspace bt709 -color_primaries bt709 -color_trc bt709`.
