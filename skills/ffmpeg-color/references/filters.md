# Color Grading & LUT Filters — Reference

Exhaustive option tables, `.cube` file format, Hald identity generator, chain
ordering, and a recipe book. Paired with the parent skill
[`../SKILL.md`](../SKILL.md).

## Filter option tables

### `lut3d`

Apply a 3D LUT. Accepts `.cube` (Adobe/Iridas) and `.3dl` (Lustre/Autodesk).

| Option   | Values                                                       | Default       | Notes |
| -------- | ------------------------------------------------------------ | ------------- | ----- |
| `file`   | path                                                         | —             | Quote inside filter: `lut3d=file='path.cube'` |
| `interp` | `nearest`, `trilinear`, `tetrahedral`, `pyramid`, `prism`    | `tetrahedral` | `tetrahedral` is smoothest; `trilinear` is faster, may band |
| `clut`   | `first`, `all`                                               | `all`         | Only relevant when LUT is a second input (usage discouraged) |

Pixel formats: planar RGB (`rgb24`, `gbrp`, etc.). Insert `format=rgb24` before
`lut3d` if your input is YUV and the LUT expects RGB domain.

### `lut1d`

Apply a 1D LUT (tone curve). Accepts `.cube` with `LUT_1D_SIZE`.

| Option   | Values                           | Default       |
| -------- | -------------------------------- | ------------- |
| `file`   | path                             | —             |
| `interp` | `linear`, `cosine`, `cubic`, `spline` | `linear` |

Common for gamma curves, log-to-linear lifts. Not for creative grading.

### `haldclut`

Apply a Hald CLUT image (a graded identity PNG).

| Option   | Values                                                       | Default       |
| -------- | ------------------------------------------------------------ | ------------- |
| `interp` | `nearest`, `trilinear`, `tetrahedral`, `pyramid`, `prism`    | `tetrahedral` |
| `clut`   | `first`, `all`                                               | `all`         |

Usage requires two inputs and `-filter_complex`:

```
[0:v][1:v]haldclut=interp=tetrahedral
```

### `colorbalance`

Independent R/G/B shift per tonal zone. Each option ranges roughly `[-1.0, 1.0]`.
Values above `0.2` usually too strong.

| Option | Effect                    |
| ------ | ------------------------- |
| `rs`   | Red in shadows            |
| `gs`   | Green in shadows          |
| `bs`   | Blue in shadows           |
| `rm`   | Red in midtones           |
| `gm`   | Green in midtones         |
| `bm`   | Blue in midtones          |
| `rh`   | Red in highlights         |
| `gh`   | Green in highlights       |
| `bh`   | Blue in highlights        |
| `pl`   | Preserve lightness (`0` or `1`) |

### `selectivecolor`

Per-color cast adjustment. Values are **space-separated 4-tuples** `C M Y K`
(cyan, magenta, yellow, black) each in `[-1.0, 1.0]`. NOT comma-separated.

| Color option | Target                         |
| ------------ | ------------------------------ |
| `reds`       | Red-dominant pixels            |
| `yellows`    | Yellow-dominant pixels         |
| `greens`     | Green-dominant pixels          |
| `cyans`      | Cyan-dominant pixels           |
| `blues`      | Blue-dominant pixels           |
| `magentas`   | Magenta-dominant pixels        |
| `whites`     | Near-white pixels              |
| `neutrals`   | Mid-luma desaturated pixels    |
| `blacks`     | Near-black pixels              |
| `correction_method` | `absolute` or `relative`. Default `absolute` |

Example: `selectivecolor=reds=0 0 -0.5 0:yellows=-0.1 0 0.1 0`

### `colormatrix` (legacy)

Conversion between YUV matrix conventions. Does **not** resample primaries —
only the YUV↔RGB matrix. For full colorspace conversion, use `colorspace` or
`zscale` (see `ffmpeg-hdr-color`).

| Option | Values                                                |
| ------ | ----------------------------------------------------- |
| `src`  | `bt601`, `bt709`, `smpte240m`, `fcc`, `bt2020`        |
| `dst`  | same set                                              |

Example: `colormatrix=bt601:bt709`

### `colorlevels`

Per-channel input/output min/max remap. All values in `[0.0, 1.0]`.

| Option  | Effect                   | Default |
| ------- | ------------------------ | ------- |
| `rimin` | Red input min            | 0.0     |
| `gimin` | Green input min          | 0.0     |
| `bimin` | Blue input min           | 0.0     |
| `aimin` | Alpha input min          | 0.0     |
| `rimax` | Red input max            | 1.0     |
| `gimax` | Green input max          | 1.0     |
| `bimax` | Blue input max           | 1.0     |
| `aimax` | Alpha input max          | 1.0     |
| `romin` | Red output min           | 0.0     |
| `gomin` | Green output min         | 0.0     |
| `bomin` | Blue output min          | 0.0     |
| `aomin` | Alpha output min         | 0.0     |
| `romax` | Red output max           | 1.0     |
| `gomax` | Green output max         | 1.0     |
| `bomax` | Blue output max          | 1.0     |
| `aomax` | Alpha output max         | 1.0     |

Stretch contrast: raise `rimin/gimin/bimin` and lower `rimax/gimax/bimax`.
Compress range (broadcast-safe): raise `romin/gomin/bomin` and lower
`romax/gomax/bomax`.

### `colorchannelmixer`

3×3 RGB(A) mixer. Each option is a coefficient in `[-2.0, 2.0]`.

| Option | Effect                       | Default |
| ------ | ---------------------------- | ------- |
| `rr`   | Red from red                 | 1.0     |
| `rg`   | Red from green               | 0.0     |
| `rb`   | Red from blue                | 0.0     |
| `ra`   | Red from alpha               | 0.0     |
| `gr`   | Green from red               | 0.0     |
| `gg`   | Green from green             | 1.0     |
| `gb`   | Green from blue              | 0.0     |
| `ga`   | Green from alpha             | 0.0     |
| `br`   | Blue from red                | 0.0     |
| `bg`   | Blue from green              | 0.0     |
| `bb`   | Blue from blue               | 1.0     |
| `ba`   | Blue from alpha              | 0.0     |
| `ar..aa` | Alpha row (if present)     | …       |
| `pc`   | Preservation color mode. `none`, `lum`, `max`, `avg`, `sum`, `nrm`, `pwr` | `none` |
| `pa`   | Preservation amount          | 0.0     |

Sepia example: `colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131`

### `hue`

| Option | Values / units                     | Default |
| ------ | ---------------------------------- | ------- |
| `h`    | Hue shift in degrees (expression)  | 0       |
| `s`    | Saturation multiplier              | 1       |
| `H`    | Hue shift in radians (alt)         | —       |
| `b`    | Brightness multiplier              | 0       |

### `pseudocolor`

False color mapping (exposure analysis / heat map).

| Option   | Values                                                              | Default |
| -------- | ------------------------------------------------------------------- | ------- |
| `preset` | `none`, `magma`, `inferno`, `plasma`, `viridis`, `turbo`, `cividis`, `hot`, `solar`, `cool`, `spectral`, `heat` | `none`  |
| `opacity`| `[0.0, 1.0]`                                                       | 1.0     |
| `c0`..`c3` | Expressions for custom mapping                                  | —       |

## `.cube` file format spec

Plain text. Comments begin with `#`. Key lines:

```
# optional comment
TITLE "My Look"
LUT_3D_SIZE 33
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0
0.000000 0.000000 0.000000
0.031250 0.000000 0.000000
...
```

Rules:

- `LUT_3D_SIZE N` — cubic grid edge length. ffmpeg accepts 2, 17, 32, 33, 64, 128.
- `LUT_1D_SIZE N` — 1D table length. ffmpeg's `lut1d` reads this.
- `DOMAIN_MIN` / `DOMAIN_MAX` — input range. Defaults `0.0`/`1.0`. Log LUTs may
  use wider ranges; extended-range values will clip unless you match them.
- Data row order: `B` varies slowest, then `G`, then `R` (innermost fastest).
  So for size 33 you have 33^3 = 35,937 rows after the header.
- Whitespace between the three floats in each row; newline ends the row.
- No trailing commas.

### Quick-validate a `.cube`

```bash
head -20 look.cube       # header should show TITLE / LUT_3D_SIZE
wc -l look.cube          # should be ~ LUT_3D_SIZE^3 + header lines
```

## Hald CLUT identity generator

Generate an identity CLUT PNG you can grade in Photoshop / Affinity / DaVinci
and re-apply via `haldclut`.

```bash
# Level 8 (512x512, most common, 8^3 = 512 px per side)
ffmpeg -f lavfi -i haldclutsrc=level=8 -frames:v 1 hald_identity.png

# Level 6 (216x216, smaller, lower precision)
ffmpeg -f lavfi -i haldclutsrc=level=6 -frames:v 1 hald_identity_l6.png

# Level 12 (1728x1728, overkill precision)
ffmpeg -f lavfi -i haldclutsrc=level=12 -frames:v 1 hald_identity_l12.png
```

After grading the PNG in your image editor (do **not** crop, rotate, or resize
it), apply with:

```bash
ffmpeg -i in.mp4 -i hald_identity_graded.png \
  -filter_complex "[0:v][1:v]haldclut=interp=tetrahedral" \
  -c:v libx264 -crf 18 out.mp4
```

## Recommended chain order

Coarsest → finest. Skip any step you don't need, but keep the order.

1. **`format=rgb24`** — ensure LUT sees RGB if it's RGB-domain.
2. **White balance / cast fix** — `colorbalance` (small values, `rm/gm/bm` or
   `rs/gs/bs`) or `colorchannelmixer` for camera-level corrections.
3. **Primary correction** — exposure (`eq=brightness`), contrast (`eq=contrast`
   or `colorlevels`), raw saturation (`eq=saturation`).
4. **The LUT** — `lut3d` / `haldclut`. This is where creative look lives.
5. **Secondary corrections** — `selectivecolor` for skin, sky, reds.
6. **Final output shaping** — `colorlevels` (broadcast-safe range), `hue` micro
   adjustments, `eq=gamma` if the output still feels off.
7. **`format=yuv420p`** — for H.264/HEVC playback compatibility.

Rule of thumb: if you find yourself fighting the LUT with heavy
`colorbalance`/`selectivecolor` *after* it, the LUT is wrong for the source.
Pre-correct the input (step 2/3) or switch LUTs rather than stacking bandaids.

## Recipe book

Copy-paste filter graphs. Wrap in `-vf "..."` for single-input, or put inside
`-filter_complex` if chained with other inputs.

### Teal-and-orange (Hollywood blockbuster)

```
format=rgb24,
colorbalance=rs=.1:bs=-.05:rh=-.05:bh=.1,
curves=preset=medium_contrast,
selectivecolor=reds=0 0 0.25 0:yellows=-0.1 0 0.15 0:blues=0.2 0 0 0,
colorlevels=rimin=0.03:gimin=0.03:bimin=0.03,
format=yuv420p
```

### Bleach bypass (film look, desaturated highlights)

```
format=rgb24,
eq=contrast=1.15:saturation=0.6,
colorchannelmixer=pc=lum:pa=0.5,
colorlevels=rimin=0.05:gimin=0.05:bimin=0.05:romax=0.92:gomax=0.92:bomax=0.92,
format=yuv420p
```

### Cross-process (shifted shadows / crushed blacks)

```
format=rgb24,
colorbalance=rs=-.15:gs=.05:bs=.2:rh=.1:gh=-.05:bh=-.15,
eq=contrast=1.25:saturation=1.2,
colorlevels=rimin=0.04:gimin=0.04:bimin=0.04,
format=yuv420p
```

### Sepia

```
colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131
```

### B&W with tinted shadows (blue toe)

```
format=rgb24,
hue=s=0,
colorbalance=rs=-.08:gs=-.05:bs=.12,
format=yuv420p
```

### Skin-tone protection (reduce red/yellow saturation, keep rest)

```
selectivecolor=reds=0 0 -0.35 0:yellows=0 0 -0.25 0
```

### Warm film (Kodak 2383 approximation)

```
format=rgb24,
colorbalance=rs=.08:rh=.04:bh=-.05,
curves=preset=medium_contrast,
selectivecolor=yellows=-0.05 0 0.1 0:reds=-0.05 0 0.1 0,
colorlevels=romax=0.96:gomax=0.96:bomax=0.96,
format=yuv420p
```

### Night-scene cool (moonlight)

```
format=rgb24,
colorbalance=rs=-.1:bs=.15:rh=-.08:bh=.1,
eq=brightness=-0.05:contrast=1.1:saturation=0.85,
format=yuv420p
```

### Log-to-Rec709 (no creative look, just normalize)

Prefer a camera-specific `.cube` (Sony Slog3, ARRI LogC, Panasonic VLog). If you
only have `colormatrix`/`eq`, you are guessing — get the correct LUT.

```
lut3d=file='slog3_to_rec709.cube':interp=tetrahedral
```

### Broadcast-safe (clip to legal 16-235 range)

```
colorlevels=rimin=0.0:rimax=1.0:romin=16/255:romax=235/255:gimin=0.0:gimax=1.0:gomin=16/255:gomax=235/255:bimin=0.0:bimax=1.0:bomin=16/255:bomax=235/255
```

### Exposure analysis overlay (false color)

```
pseudocolor=preset=heat
```

Use in `ffplay` while grading to spot clipped highlights and crushed shadows.
