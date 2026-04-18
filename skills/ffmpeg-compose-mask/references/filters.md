# ffmpeg compose / mask filter reference

Per-filter option tables, mental models, and recipe book for compositing and plane work. Authoritative source: `ffmpeg.org/ffmpeg-filters.html`. Re-verify with `ffdocs.py search --query <filter> --page ffmpeg-filters` before shipping production pipelines.

## Masking mental model

A mask is always a **single-plane grayscale image**:

- **White (255)** = "pass through" or "pick from the primary input".
- **Black (0)** = "block" or "pick from the secondary input".
- **Mid-gray (128)** = half-and-half (for merge filters that interpolate).

For `displace`, mid-gray means "no shift"; pixel values above 128 shift positively, below shift negatively.

For `alphamerge` / `alphaextract`, a mask is indistinguishable from an alpha plane — they're the same grayscale data, just stored differently.

Always force the mask branch with `format=gray` (or `format=gray16` for 16-bit content) before handing it to a compositing filter. FFmpeg will often auto-insert a format converter, but occasionally picks the wrong one and you get a tinted composite.

## Pre- vs. un-premultiply decision tree

```
Does your input have alpha?
├── No  → no premultiply work needed; use overlay/blend directly
└── Yes → Is it straight alpha or premultiplied?
    ├── Straight (most hand-authored masks, PNG exports)
    │   → Composite directly; use overlay=format=auto or maskedmerge.
    ├── Premultiplied (some After Effects MOVs, modern 3D renders)
    │   → unpremultiply=inplace=1 before filters that expect straight;
    │     then premultiply=inplace=1 before encoding if target expects it.
    └── Unknown
        → Inspect: does the black background of a subject look correct?
          Halos / color fringing on soft edges ⇒ wrong assumption; flip.
```

Rule of thumb: `overlay=format=auto` handles both correctly. Manual `maskedmerge` does not — assumes straight.

## Plane selector hex notation

`mergeplanes=0xAABBCC:yuv444p` reads right-to-left for output planes 0, 1, 2:

| Byte position | Output plane | Nibble layout             |
| ------------- | ------------ | ------------------------- |
| `0xAA` (hi)   | plane 2      | `(plane_idx << 4) | input_idx` |
| `0xBB`        | plane 1      | same                      |
| `0xCC` (lo)   | plane 0      | same                      |

High nibble of each byte = which plane of the source input to take. Low nibble = which input (0-based).

Examples:

- `0x001020` → out0 = in0.plane0, out1 = in1.plane0, out2 = in2.plane0. (Three gray streams combined into yuv444p.)
- `0x00010210` → four planes, so the selector is 4 bytes. out0 = in0.plane0, out1 = in0.plane1, out2 = in0.plane2, out3 = in1.plane0. (Attach gray as alpha.)
- `0x03010200` → out0 = in0.p0, out1 = in0.p2, out2 = in0.p1, out3 = in0.p3. (Swap U↔V within one yuv444p input.)

`shuffleplanes=a:b:c:d` is different — it only reorders planes within a single input. Each argument is the source-plane index for output planes 0–3.

## Filter option tables

### maskedmerge

3 inputs: source0, source1, mask. Output = source0 where mask is white, source1 where black.

| Option  | Default | Meaning                                                     |
| ------- | ------- | ----------------------------------------------------------- |
| planes  | `0xF`   | Bitmask of which planes to merge (bit n = plane n).         |

### maskedclamp

3 inputs: source, lower-bound, upper-bound. Clamps source[i] to [lower[i], upper[i]].

| Option     | Default | Meaning                                  |
| ---------- | ------- | ---------------------------------------- |
| undershoot | 0       | Extra slack below the lower bound.       |
| overshoot  | 0       | Extra slack above the upper bound.       |
| planes     | `0xF`   | Bitmask of planes.                       |

### maskedmin / maskedmax

3 inputs. `maskedmin`: pick the input (1 or 2) closer to source. `maskedmax`: pick farther. Planes bitmask as above.

### maskedthreshold

2 inputs. Output source0 where |source0 - source1| ≤ threshold, else source1.

| Option    | Default | Meaning                                      |
| --------- | ------- | -------------------------------------------- |
| threshold | 1       | Threshold for difference test.               |
| planes    | `0xF`   | Bitmask of planes.                           |
| mode      | `abs`   | `abs` or `diff` (use signed difference).     |

### maskfun

1 input. Creates a mask by thresholding.

| Option | Default | Meaning                                          |
| ------ | ------- | ------------------------------------------------ |
| low    | 10      | Lower threshold.                                 |
| high   | 10      | Upper threshold.                                 |
| planes | `0xF`   | Planes bitmask.                                  |
| fill   | 0       | Value to fill "in-mask" pixels with.             |
| sum    | 10      | Window size for summed thresholding.             |

### alphamerge

2 inputs: video, grayscale. Output pixel format becomes yuva* / rgba depending on input. No options.

### alphaextract

1 input (must have alpha). Output is grayscale of the alpha plane. No options.

### premultiply / unpremultiply

1 or 2 inputs. With `inplace=1`: use input's own alpha plane (1 input). Without: second stream is the alpha source.

| Option  | Default | Meaning                                  |
| ------- | ------- | ---------------------------------------- |
| planes  | `0xF`   | Which planes to (un)premultiply.         |
| inplace | 0       | Use input's alpha, skip 2nd input.       |

### displace

3 inputs: base, xmap, ymap.

| Option | Default | Meaning                                                         |
| ------ | ------- | --------------------------------------------------------------- |
| edge   | `smear` | `blank` (black), `smear` (clamp), `wrap`, `mirror` for OOB pix. |

### extractplanes

1 input → N grayscale outputs (one per requested plane).

| Option | Default | Meaning                                                |
| ------ | ------- | ------------------------------------------------------ |
| planes | `r`     | `+`-joined list: y, u, v, r, g, b, a (combinations).   |

### mergeplanes

2–4 inputs. See hex-notation section above.

| Option  | Default   | Meaning                                                    |
| ------- | --------- | ---------------------------------------------------------- |
| mapping | 0         | Hex selector; byte per output plane.                       |
| format  | `yuva444p`| Output pixel format.                                       |

### shuffleplanes

1 input, reorders its planes.

| Option | Default | Meaning                                      |
| ------ | ------- | -------------------------------------------- |
| map0   | 0       | Which source plane → output plane 0.         |
| map1   | 1       | Which source plane → output plane 1.         |
| map2   | 2       | Which source plane → output plane 2.         |
| map3   | 3       | Which source plane → output plane 3.         |

Shorthand: `shuffleplanes=0:2:1:3`.

### shufflepixels

1 input. Reversibly scrambles pixel positions within fixed-size blocks (useful for visual hashing / reversible masking). Options: `direction ∈ {forward, inverse}`, `mode ∈ {horizontal, vertical, block}`, `width`, `height`, `seed`.

### shuffleframes

1 input. Reorders frames within a configurable window (e.g. `shuffleframes=0 2 1` swaps frame 1 and 2 in each 3-frame window).

### rgbashift

1 input. Per-channel pixel shift.

| Option | Default   | Meaning                                  |
| ------ | --------- | ---------------------------------------- |
| rh, rv | 0         | Red horizontal/vertical shift (px).      |
| gh, gv | 0         | Green H/V shift.                         |
| bh, bv | 0         | Blue H/V shift.                          |
| ah, av | 0         | Alpha H/V shift.                         |
| edge   | `smear`   | `smear` or `wrap` for OOB pixels.        |

### blend (spatial, 2 inputs)

| Option                     | Default  | Meaning                                              |
| -------------------------- | -------- | ---------------------------------------------------- |
| all_mode                   | `normal` | Blend mode applied to every plane.                   |
| all_opacity                | 1.0      | Mix weight with the first input.                     |
| all_expr                   | (unset)  | Custom expression (A, B, X, Y, W, H, T, N vars).     |
| c0_mode … c3_mode          | `normal` | Per-plane blend modes.                               |
| c0_opacity … c3_opacity    | 1.0      | Per-plane opacity.                                   |
| c0_expr … c3_expr          | (unset)  | Per-plane expressions.                               |

Modes: `addition, and, average, burn, darken, difference, divide, dodge, exclusion, extremity, freeze, geometric, glow, grainextract, grainmerge, hardlight, hardmix, hardoverlay, harmonic, heat, interpolate, lighten, linearlight, multiply, multiply128, negation, normal, or, overlay, phoenix, pinlight, reflect, screen, softdifference, softlight, subtract, vividlight, xor`.

### floodfill

1 input. Paint-bucket fill from a seed.

| Option        | Default | Meaning                                               |
| ------------- | ------- | ----------------------------------------------------- |
| x, y          | 0       | Seed pixel.                                           |
| s0, s1, s2, s3| 0       | Source component values to match at seed.             |
| d0, d1, d2, d3| 0       | Destination component values.                         |

### hysteresis

2 inputs (strong + weak edge masks). Output is weak-edge pixels connected to strong-edge pixels.

| Option    | Default | Meaning                                       |
| --------- | ------- | --------------------------------------------- |
| planes    | `0xF`   | Planes to process.                            |
| threshold | 0       | Value above which pixels are "present".       |

### remap

3 inputs (source, xmap, ymap). xmap/ymap are single-plane 16-bit images with absolute pixel coordinates (not deltas, unlike `displace`).

| Option | Default  | Meaning                                             |
| ------ | -------- | --------------------------------------------------- |
| format | `color`  | `color` or `gray` output.                           |
| fill   | `black`  | Fill color for out-of-range samples.                |

## Recipe book

### Rotoscope workflow (hand-painted mask → composite)

```bash
# 1. Extract frames you will paint:
ffmpeg -i source.mp4 -vf fps=24 frames/%04d.png

# 2. Paint masks in external tool (Photoshop, Krita, etc.), save as masks/%04d.png.

# 3. Rebuild mask video:
ffmpeg -framerate 24 -i masks/%04d.png -vf format=gray -c:v ffv1 mask.mkv

# 4. Composite onto a new background:
ffmpeg -i source.mp4 -i bg.mp4 -i mask.mkv \
  -filter_complex "[2:v]format=gray[m];[0:v][1:v][m]maskedmerge[out]" \
  -map "[out]" -c:v libx264 -crf 18 composite.mp4
```

### Sky replacement via luminance mask

Use the source's own luma as the mask (curves lift the sky, crush everything else).

```bash
ffmpeg -i footage.mp4 -i new_sky.mp4 \
  -filter_complex "\
    [0:v]split[src][lum];\
    [lum]format=yuv420p,extractplanes=y,\
         curves=master='0/0 0.7/0 0.75/1 1/1'[m];\
    [src][1:v][m]maskedmerge[out]" \
  -map "[out]" sky_replaced.mp4
```

### Chromatic aberration

```bash
ffmpeg -i in.mp4 \
  -vf "format=gbrp,rgbashift=rh=3:rv=0:bh=-3:bv=0,format=yuv420p" \
  out.mp4
```

Amplify further with `geq`:

```bash
ffmpeg -i in.mp4 \
  -vf "format=gbrp,rgbashift=rh=5:bh=-5,gblur=sigma=0.5,format=yuv420p" \
  out.mp4
```

### Displacement warp (procedural water ripple)

```bash
ffmpeg -i base.mp4 -f lavfi -i "\
color=c=gray:s=1920x1080:d=10,\
geq='128+40*sin(2*PI*(X+T*60)/160):128:128',format=gray" \
  -filter_complex "[1:v]split[x][y];[0:v][x][y]displace=edge=smear[out]" \
  -map "[out]" ripple.mp4
```

### Alpha round-trip (YUV + mask → reconstruct RGBA)

```bash
# Split:
ffmpeg -i rgba.mov -vf "alphaextract" -c:v ffv1 mask.mkv
ffmpeg -i rgba.mov -vf "format=yuv420p" -c:v libx264 -crf 12 color.mp4

# Reassemble:
ffmpeg -i color.mp4 -i mask.mkv \
  -filter_complex "[0:v][1:v]alphamerge" \
  -c:v prores_ks -profile:v 4444 out.mov
```

### Green-screen refinement (chromakey → maskfun → maskedmerge)

```bash
ffmpeg -i green.mov -i bg.mp4 \
  -filter_complex "\
    [0:v]chromakey=0x00FF00:0.1:0.2,format=yuva420p[keyed];\
    [keyed]alphaextract,maskfun=low=20:high=220,format=gray[m];\
    [bg_resized]…; [0:v][bg][m]maskedmerge[out]" \
  -map "[out]" composite.mp4
```

For dedicated green-screen workflows see the `ffmpeg-chromakey` skill; this combo is for when you need pixel-exact edge control the keyer can't give you.

### Plane-swap psychedelic effect

```bash
ffmpeg -i in.mp4 -vf "format=yuv444p,shuffleplanes=0:2:1:3" out.mp4
# Y stays, U↔V swap. Purples become oranges etc.
```

### Build yuva444p from three gray mattes + one RGB source

```bash
# Suppose a.mkv, b.mkv, c.mkv are gray Y/U/V, and m.mkv is a gray alpha.
ffmpeg -i a.mkv -i b.mkv -i c.mkv -i m.mkv \
  -filter_complex "[0:v][1:v][2:v][3:v]mergeplanes=0x00102030:yuva444p[out]" \
  -map "[out]" -c:v prores_ks -profile:v 4444 merged.mov
```

### Connected-region paint (floodfill)

Replace a solid colored region with another color. The seed pixel's current values must match `s0..s2` exactly.

```bash
ffmpeg -i in.mp4 -vf "format=yuv444p,floodfill=x=100:y=100:s0=76:s1=84:s2=255:d0=235:d1=128:d2=128" out.mp4
```

### Edge refinement via hysteresis

```bash
ffmpeg -i in.mp4 -filter_complex "\
  [0:v]split[hi][lo];\
  [hi]edgedetect=mode=canny:high=0.3:low=0.1,format=gray[strong];\
  [lo]edgedetect=mode=canny:high=0.1:low=0.05,format=gray[weak];\
  [strong][weak]hysteresis=threshold=0:planes=1[out]" \
  -map "[out]" edges.mp4
```
