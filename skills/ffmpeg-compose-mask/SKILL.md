---
name: ffmpeg-compose-mask
description: >
  Advanced compositing, masking, and channel operations with ffmpeg: maskedclamp, maskedmax, maskedmin, maskedmerge, maskedthreshold, maskfun, alphamerge, alphaextract, premultiply, unpremultiply, displace, hysteresis, floodfill, remap, mergeplanes, shuffleplanes, extractplanes, shuffleframes, shufflepixels, rgbashift, blend (spatial). Use when the user asks to composite with masks, extract or merge alpha, manipulate individual YUV/RGB/alpha planes, do roto-style compositing, displacement map one video by another, remap pixels, or split and recombine channels.
argument-hint: "[input]"
---

# Ffmpeg Compose Mask

**Context:** $ARGUMENTS

Advanced compositing and channel surgery. If you are keying green-screens, see `ffmpeg-chromakey`. If you are grading color, see `ffmpeg-lut-grade`. This skill is for pixel-exact compositing math, alpha plumbing, and plane-level operations.

## Quick start

- **Composite A and B through a mask (white→A, black→B):** → Step 1, 2 (`maskedmerge`)
- **Add an alpha channel from a separate mask video:** → Step 2 (`alphamerge`)
- **Pull mask out of an RGBA/yuva file:** → Step 2 (`alphaextract`)
- **Warp one video using another as a displacement map:** → Step 2 (`displace`)
- **Grab a single plane (Y, U, V, R, G, B, A):** → Step 2 (`extractplanes`)
- **Rebuild image from separated planes:** → Step 2 (`mergeplanes`)
- **Chromatic aberration / per-channel pixel shift:** → Step 2 (`rgbashift`)
- **Apply a Photoshop blend mode (screen, multiply, overlay...):** → Step 2 (`blend`)
- **Fill connected pixel region (Photoshop paint bucket):** → Step 2 (`floodfill`)

## When to use

- Roto-style compositing where you already have (or can compute) a per-pixel matte.
- Alpha plumbing: moving masks between files, reconstructing RGBA from split streams.
- Plane surgery: YUV/RGB channel isolation, swapping, rebuilding across pixel formats.
- Procedural effects: displacement warps, chromatic aberration, blend-mode layers.
- Edge-linking (`hysteresis` paired with `edgedetect`), mask refinement (`maskfun`, `maskedthreshold`, `maskedclamp`).
- Pixel remapping (`remap`), connected-region filling (`floodfill`).

## Step 1 — Identify sources and the mask

Count your inputs. `maskedmerge` and `displace` need **three**; `alphamerge` and `blend` need **two**; `alphaextract`, `extractplanes`, `rgbashift`, `maskfun`, `floodfill` need **one**.

Verify each input with `ffprobe` before building the filter graph:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,pix_fmt,r_frame_rate -of default=nw=1 INPUT
```

All inputs to multi-input filters must share **width, height, and pixel format**. If they don't, scale/convert first (`scale=W:H`, `format=yuva420p`, `fps=FPS`).

## Step 2 — Pick the compositing operation

### Masked merge (3 inputs: source0, source1, mask)

Mask pixel value drives the blend: white = take from source0, black = from source1, gray = weighted mix.

```bash
ffmpeg -i A.mp4 -i B.mp4 -i MASK.mp4 \
  -filter_complex "[2:v]format=gray[m];[0:v][1:v][m]maskedmerge[out]" \
  -map "[out]" -c:v libx264 -crf 18 out.mp4
```

Options: `planes` (bitmask of planes to process; default `0xF` = all).

### Alpha merge (2 inputs: video + grayscale mask)

Bolts a grayscale matte onto the primary input as alpha. Output is yuva-format.

```bash
ffmpeg -i video.mp4 -i mask.mp4 \
  -filter_complex "[0:v][1:v]alphamerge[out]" \
  -map "[out]" -c:v prores_ks -profile:v 4444 out.mov
```

### Alpha extract (1 RGBA/yuva input → grayscale mask)

```bash
ffmpeg -i rgba.mov -vf "alphaextract" -c:v ffv1 mask.mkv
```

### Pre-/un-premultiply around compositing

Straight alpha inputs must NOT be premultiplied into RGB before compositing; premultiplied inputs must be un-multiplied before filters that expect straight, then remultiplied after.

```bash
# Composite with correct alpha math:
ffmpeg -i premul.mov -i bg.mov \
  -filter_complex "[0:v]unpremultiply=inplace=1[a];\
                   [1:v][a]overlay=format=auto[composed];\
                   [composed]premultiply=inplace=1[out]" \
  -map "[out]" -c:v prores_ks -profile:v 4444 out.mov
```

Both `premultiply` and `unpremultiply` accept `inplace=1` to use the input's own alpha plane (no 2nd stream needed).

### Displacement warp (3 inputs: base, xmap, ymap)

xmap and ymap are grayscale; mid-gray (128) means no shift, white = +scale, black = -scale. One map can supply both if you `split`.

```bash
ffmpeg -i base.mp4 -i xmap.mp4 -i ymap.mp4 \
  -filter_complex "[0:v][1:v][2:v]displace=edge=smear[out]" \
  -map "[out]" -c:v libx264 -crf 18 out.mp4
```

Options: `edge ∈ {blank, smear, wrap, mirror}` (default `smear`).

### Plane surgery

Extract a single plane (always output is grayscale):

```bash
# Luma only:
ffmpeg -i in.mp4 -vf "format=yuv420p,extractplanes=y" -c:v ffv1 y.mkv
# All three at once:
ffmpeg -i in.mp4 -filter_complex "extractplanes=y+u+v[y][u][v]" \
  -map "[y]" y.mkv -map "[u]" u.mkv -map "[v]" v.mkv
```

Rebuild planes from multiple inputs via `mergeplanes` with a hex selector:

```bash
# 3 gray streams → single yuv444p:
ffmpeg -i y.mkv -i u.mkv -i v.mkv \
  -filter_complex "[0:v][1:v][2:v]mergeplanes=0x001020:yuv444p[out]" \
  -map "[out]" out.mov

# Add a gray stream as alpha onto a yuv444p stream → yuva444p:
# [yuv][mask]mergeplanes=0x00010210:yuva444p
```

Swap planes within a single stream with `shuffleplanes` (per-plane index into input 0):

```bash
# Y=plane 0, swap U and V:
ffmpeg -i in.mp4 -vf "shuffleplanes=0:2:1:3" out.mp4
```

### Per-channel pixel shift / chromatic aberration

```bash
ffmpeg -i in.mp4 -vf "format=gbrp,rgbashift=rh=2:bh=-2" out.mp4
```

Options: `rh, rv, gh, gv, bh, bv, ah, av` (horizontal/vertical shift in pixels per channel; default 0). `edge ∈ {smear, wrap}`.

### Spatial blend (2 inputs)

Photoshop-style blend modes applied pixelwise between two aligned streams:

```bash
ffmpeg -i base.mp4 -i overlay.mp4 \
  -filter_complex "[0:v][1:v]blend=all_mode=screen:all_opacity=0.5[out]" \
  -map "[out]" out.mp4
```

Modes: `addition, and, average, burn, darken, difference, divide, dodge, exclusion, freeze, glow, grainextract, grainmerge, hardlight, hardmix, heat, lighten, linearlight, multiply, negation, normal, or, overlay, phoenix, pinlight, reflect, screen, softdifference, softlight, subtract, vividlight, xor`. Per-plane variants: `c0_mode`, `c1_mode`, `c2_mode`, `c3_mode` plus matching `c0_opacity`, etc. `all_expr` accepts arbitrary expressions on `A`, `B`, `X`, `Y`, `W`, `H`, `SW`, `SH`, `T`, `N`.

### Floodfill (paint-bucket fill)

```bash
# Replace pixels at (100, 100) and all connected same-color ones with red:
ffmpeg -i in.mp4 -vf "floodfill=x=100:y=100:s0=10:s1=10:s2=10:d0=255:d1=0:d2=0" out.mp4
```

`x, y` are the seed pixel (integer). `s0,s1,s2,s3` match the source pixel (must equal them exactly to flood); `d0,d1,d2,d3` are the destination values. Single component = single plane match/replace.

### Hysteresis (edge-linking)

Pair with `edgedetect`. First input = strong edges (high threshold), second = weak edges (low threshold). Weak edges connected to strong edges are kept.

```bash
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]split[s][w];[s]edgedetect=high=0.3:low=0.3,format=gray[strong];\
   [w]edgedetect=high=0.1:low=0.1,format=gray[weak];\
   [strong][weak]hysteresis=threshold=0:planes=1[out]" \
  -map "[out]" out.mp4
```

### Mask generation helpers

`maskfun=low=N:high=M:fill=F:sum=S` — turn input into a mask (low/high thresholds, fill color for masked pixels, sum window).
`maskedthreshold=threshold=N:mode=abs|diff` — two-input: output 1st where |a-b| ≤ threshold, else 2nd.
`maskedclamp=undershoot=U:overshoot=O:planes=P` — three-input: clamp input0 to the band defined by input1 (lower) and input2 (upper).
`maskedmax`, `maskedmin` — three-input: pick whichever of input1/input2 is farther/closer to input0 per pixel.

## Step 3 — Build the filter graph (labels + `-map`)

Always name every intermediate with `[label]` when you have more than one branch. Every label that leaves `-filter_complex` must be consumed by `-map "[label]"` on an output.

```bash
ffmpeg \
  -i source0.mp4 \
  -i source1.mp4 \
  -i mask.mp4 \
  -filter_complex "\
    [0:v]format=yuva420p[a];\
    [1:v]format=yuva420p[b];\
    [2:v]format=gray[m];\
    [a][b][m]maskedmerge[composed];\
    [composed]format=yuv420p[out_v];\
    [0:a][1:a]amix=inputs=2[out_a]\
  " \
  -map "[out_v]" -map "[out_a]" \
  -c:v libx264 -crf 18 -c:a aac -b:a 192k out.mp4
```

## Step 4 — Verify alpha and channels

After the render, confirm pixel format and plane counts:

```bash
ffprobe -v error -show_entries stream=pix_fmt,width,height -of default=nw=1 out.mov
```

Expected: `yuva420p`, `yuva444p`, `rgba`, or `argb` if alpha was intended. If you see `yuv420p`, alpha was lost (either the container doesn't support it or a later filter/encoder dropped it; see Gotchas).

Preview the mask-only pass before committing:

```bash
ffplay -f lavfi "movie=out.mov,alphaextract"
```

## Available scripts

- **`scripts/compose.py`** — argparse-driven wrapper that builds and (optionally) runs the correct filter graph for each operation: `mask-merge`, `alpha-merge`, `alpha-extract`, `displace`, `planes`, `blend`, `rgbashift`. Stdlib only; supports `--dry-run` and `--verbose`.

```bash
# Preview the command:
python3 ${CLAUDE_SKILL_DIR}/scripts/compose.py mask-merge \
  --source0 A.mp4 --source1 B.mp4 --mask M.mp4 --output out.mp4 --dry-run

# Run it:
python3 ${CLAUDE_SKILL_DIR}/scripts/compose.py blend \
  --source0 a.mp4 --source1 b.mp4 --mode screen --output out.mp4
```

## Reference docs

- [`references/filters.md`](references/filters.md) — per-filter option tables, masking mental model, pre/un-premultiply decision tree, plane-selector hex notation, recipe book (rotoscope, sky replacement, chromatic aberration, displacement warp).

## Gotchas

- `maskedmerge` takes **three inputs in exact order**: source0, source1, mask. Reordering silently produces garbage because each role is positional.
- Masks must be single-plane grayscale. Insert `format=gray` on the mask branch before handing it to `maskedmerge`, `alphamerge`, `displace` (x/y maps), or `hysteresis`. Skipping this is the #1 cause of "why is my composite tinted?"
- `alphamerge` expects `[video][mask]` in that order; swapped → inverted matte.
- Alpha operations require `yuva420p` / `yuva444p` / `rgba` / `gbrap` pixel formats. Insert `format=yuva420p` before any filter that expects alpha; `libx264` by default uses `yuv420p` and will silently drop alpha — use `libx264rgb`, `prores_ks -profile:v 4444`, `qtrle`, `png`, `ffv1`, `vp9` (yuva420p), or PNG sequences for alpha-carrying output.
- Output container must support alpha. MP4 doesn't for most codecs; use MOV (ProRes 4444, QTRLE), MKV (FFV1, VP9 yuva420p), WebM (VP9 yuva420p), or PNG sequence.
- Premultiply vs straight alpha: if your composite has dark halos or incorrect edge colors, insert `unpremultiply=inplace=1` before compositing and `premultiply=inplace=1` after.
- `extractplanes` requires planar pixel formats. Force with `format=yuv420p` or `format=gbrp` first if unsure. The option syntax is `extractplanes=y+u+v` (plus-separated names), not a bitmask.
- `mergeplanes` uses a packed hex selector: `0xAABBCC` for 3 planes, `0xAABBCCDD` for 4. Each byte is `(plane_idx << 4) | input_idx`. Read right-to-left for output plane 0, 1, 2... Example: `0x001020` → out plane 0 = input 0 plane 0, out plane 1 = input 1 plane 0, out plane 2 = input 2 plane 0.
- `shuffleplanes=a:b:c:d` — each number is which **plane of input 0** becomes output planes 0, 1, 2, 3 respectively. It is NOT per-input addressing (use `mergeplanes` for that). `shuffleplanes=0:2:1:3` → Y stays, U and V swap.
- `rgbashift` shifts by **pixels, not subsampled positions**; on chroma-subsampled formats convert to `gbrp` first for pixel-accurate results.
- `displace` x/y maps must be grayscale where mid-gray (~128) = zero shift. White shifts positively, black negatively; amplitude scales with the plane bit-depth range.
- `blend=all_mode=screen` and similar modes operate on whatever range the pixel format uses — in YUV the math is technically correct but differs visually from RGB-space reference blends. Convert to `gbrp` first (`format=gbrp`) to match Photoshop output.
- `maskedclamp` is three-input (source, lower-bound, upper-bound) — lower/upper must bracket `source` pixel-for-pixel.
- `floodfill` coordinates are integer pixels measured from top-left. The filter floods only pixels whose plane values exactly match `s0..s3`; it's not a soft-threshold match.
- `hysteresis` requires two single-plane inputs of identical dimensions. Run `edgedetect` with different thresholds into each branch.
- Every label produced inside `-filter_complex` must be consumed by `-map "[label]"` when you have multiple outputs; unmapped labels are silently dropped.

## Examples

### Example 1 — Replace sky via luminance mask

```bash
ffmpeg -i footage.mp4 -i sky.mp4 \
  -filter_complex "\
    [0:v]split[src][lum];\
    [lum]hue=s=0,curves=master='0/0 0.7/0 0.75/1 1/1',format=gray[m];\
    [1:v]scale=iw:ih[sky];\
    [src][sky][m]maskedmerge[out]\
  " -map "[out]" -c:v libx264 -crf 18 sky_replaced.mp4
```

### Example 2 — Extract alpha, transmit YUV + mask separately, reconstruct

```bash
# Sender:
ffmpeg -i rgba.mov -vf "alphaextract" -c:v ffv1 mask.mkv
ffmpeg -i rgba.mov -vf "format=yuv420p" -c:v libx264 -crf 12 color.mp4
# Receiver:
ffmpeg -i color.mp4 -i mask.mkv \
  -filter_complex "[0:v][1:v]alphamerge" \
  -c:v prores_ks -profile:v 4444 reconstructed.mov
```

### Example 3 — Chromatic aberration look

```bash
ffmpeg -i in.mp4 -vf "format=gbrp,rgbashift=rh=3:bh=-3,format=yuv420p" \
  -c:v libx264 -crf 18 aberrated.mp4
```

### Example 4 — Displacement warp from noise

```bash
ffmpeg -i base.mp4 -f lavfi -i "nullsrc=s=1920x1080:d=10,\
geq='128+40*sin(2*PI*X/100+T):128:128'" \
  -filter_complex "[1:v]split[x][y];[0:v][x][y]displace=edge=smear[out]" \
  -map "[out]" warp.mp4
```

## Troubleshooting

### Error: "Input link parameters do not match"

Cause: mismatched width, height, or pixel format between filter inputs.
Solution: scale and format-convert each branch before the multi-input filter. Insert `scale=W:H,format=yuva420p` on every input.

### Output has no alpha even though I merged one

Cause: encoder or container silently dropped alpha.
Solution: confirm pix_fmt with ffprobe. Switch to `prores_ks -profile:v 4444` in `.mov`, `qtrle` in `.mov`, `ffv1` in `.mkv`, or `libvpx-vp9 -pix_fmt yuva420p` in `.webm`.

### Composite has dark halos around soft edges

Cause: premultiplied alpha treated as straight (or vice versa).
Solution: wrap the compositing chain with `unpremultiply=inplace=1` before, `premultiply=inplace=1` after.

### `extractplanes` errors with "does not support this format"

Cause: non-planar input (e.g., NV12, packed YUYV).
Solution: insert `format=yuv420p` (or `format=gbrp` for RGB work) before `extractplanes`.

### `mergeplanes` produces weird colors

Cause: wrong hex selector. The byte order is little-endian-ish per-plane; read each byte as `(plane_idx << 4) | input_idx`.
Solution: walk through the selector on paper. For 3 gray inputs → yuv444p you want `0x001020` (out0=in0.0, out1=in1.0, out2=in2.0).

### `blend` result looks wrong in YUV

Cause: blend modes are defined mathematically over the sample range; YUV samples aren't linear RGB.
Solution: `format=gbrp` before `blend`, then convert back to `yuv420p` for the encoder.
