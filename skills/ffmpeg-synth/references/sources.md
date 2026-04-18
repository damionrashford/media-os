# lavfi synthetic sources — reference

Comprehensive per-source option tables for every video and audio source available via
`-f lavfi -i <expression>`, plus color names, `aevalsrc` grammar, and a recipe gallery.

Upstream docs:

- Video sources: https://ffmpeg.org/ffmpeg-filters.html#Video-Sources
- Audio sources: https://ffmpeg.org/ffmpeg-filters.html#Audio-Sources

Quick sanity check against your local ffmpeg build:

```bash
ffmpeg -hide_banner -filters | grep "Video source"
ffmpeg -hide_banner -filters | grep "Audio source"
ffmpeg -hide_banner -h filter=smptehdbars    # dump options for one source
```

Notation: `s`/`size`, `r`/`rate` and `sr`/`sample_rate` are interchangeable aliases in most
sources. Options marked *(required)* have no usable default.

---

## Video sources

### `testsrc` — colored test pattern

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `320x240` | WxH |
| `rate` / `r` | `25` | fps |
| `duration` / `d` | unset (infinite) | seconds or `HH:MM:SS` |
| `sar` | `1` | sample aspect ratio |
| `decimals` / `n` | `0` | frame-counter digits |

Produces colored rectangles + frame counter + cue tone marker. Good for plain encoder input.

### `testsrc2` — test pattern with counter + movement

Same options as `testsrc`, plus:

| Option | Default | Notes |
| --- | --- | --- |
| `alpha` | `255` | for RGBA output |

Draws a moving element and burns in a timecode-style counter. Preferred over `testsrc`
when you want to *see* frame loss / re-ordering.

### `smptebars` — pre-HD SMPTE 75 % bars

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `320x240` | WxH, SMPTE ECR 1-1978 layout only makes sense at 4:3 |
| `rate` / `r` | `25` | fps |
| `duration` / `d` | infinite | |
| `sar` | `1` | |

### `smptehdbars` — HD 100 % SMPTE ARIB STD-B28 bars

Same options as `smptebars`. Use for HD deliverables; `smptebars` is 4:3 legacy.

### `pal75bars` / `pal100bars` — PAL legacy bars

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `720x576` | set explicitly for HD scaling |
| `rate` / `r` | `25` | PAL-native fps |
| `duration` / `d` | infinite | |

### `rgbtestsrc` / `yuvtestsrc` — pure primary swatches

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `320x240` | |
| `rate` / `r` | `25` | |
| `duration` / `d` | infinite | |
| `complement` | `0` | YUV only — draw negatives |

Use `rgbtestsrc` to exercise full-range RGB path; `yuvtestsrc` for YUV primaries.

### `allyuv` / `allrgb` — exhaustive color sweep

| Source | Fixed size | Notes |
| --- | --- | --- |
| `allyuv` | `256x256` per Y plane | cycles every Y×Cb×Cr triplet |
| `allrgb` | `4096x4096` | one frame covers every R×G×B triplet |

No `size=` parameter — dimensions are fixed by the algorithm. Use `scale` after if needed.

### `colorchecker` — 24-patch Macbeth/X-Rite chart

| Option | Default | Notes |
| --- | --- | --- |
| `rate` / `r` | `25` | fps; irrelevant for static PNG output |
| `duration` / `d` | `0` | `0` = still image |
| `patch_size` | `64x64` | px per color patch (recent ffmpeg only) |
| `preset` | `reference` | `reference` or `skintones` (some builds) |

Often exported with `-frames:v 1` into a PNG. Older builds ignore `size=` — scale after.

### `color` — solid fill

| Option | Default | Notes |
| --- | --- | --- |
| `c` / `color` | `black` | named color, hex, `random`, `red@0.5` |
| `size` / `s` | `320x240` | WxH |
| `rate` / `r` | `25` | fps |
| `duration` / `d` | infinite | seconds |
| `sar` | `1` | |

### `gradients` — animated multi-color gradient

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `640x480` | |
| `rate` / `r` | `25` | |
| `duration` / `d` | infinite | |
| `c0..c7` | varied | up to 8 color stops; `c0=red:c1=blue` |
| `x0 y0 x1 y1` | `0 0 640 480` | gradient vector |
| `nb_colors` | `2` | stops used |
| `seed` | random | deterministic animation seed |
| `speed` | `0.01` | animation speed |
| `type` | `linear` | `linear`/`radial`/`circular`/`spiral`/`square` |

### `mandelbrot` — zooming fractal

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `640x480` | |
| `rate` / `r` | `25` | |
| `maxiter` | `7189` | iteration cap |
| `start_x` | `-0.743643887037158704752191506114774` | seed Re |
| `start_y` | `-0.131825904205311970493132056385139` | seed Im |
| `start_scale` | `3.0` | initial zoom |
| `end_scale` | `0.3` | final zoom |
| `end_pts` | `400` | zoom duration in pts |
| `bailout` | `10` | escape radius |
| `morphxf` `morphyf` `morphamp` | — | morphing deformation |
| `outer` / `inner` | `normalized_iteration_count` / `mincol` | coloring rules |

### `cellauto` — 1-D cellular automaton (Wolfram rules)

| Option | Default | Notes |
| --- | --- | --- |
| `filename` / `f` | — | seed row from file |
| `pattern` / `p` | — | seed row as `0` and `1` string |
| `rate` / `r` | `25` | |
| `size` / `s` | `320x240` | |
| `rule` | `110` | Wolfram rule number |
| `random_fill_ratio` | `1/PHI` | random seed density |
| `random_seed` | `-1` | RNG seed |
| `scroll` | `1` | advance each frame |
| `start_full` | `1` | start with image full |
| `stitch` | `1` | wrap edges |

### `life` — Conway's Game of Life

| Option | Default | Notes |
| --- | --- | --- |
| `filename` / `f` | — | seed from file |
| `size` / `s` | `320x240` | |
| `rate` / `r` | `25` | |
| `rule` | `B3/S23` | Survival/birth rule |
| `random_seed` | `-1` | RNG seed |
| `random_fill_ratio` | `1/PHI` | random seed density |
| `stitch` | `1` | wrap edges |
| `mold` | `0` | decaying trail intensity 0-255 |
| `life_color` / `death_color` / `mold_color` | | RGB strings |

### `zoneplate` — radial zone plate

Drives encoders and sharpeners into aliasing. Options:

| Option | Default | Notes |
| --- | --- | --- |
| `size` / `s` | `320x240` | |
| `rate` / `r` | `25` | |
| `duration` / `d` | infinite | |
| `k0..k22` | various | radial / temporal frequency terms |
| `precision` | `10` | |

### `haldclutsrc` — identity Hald CLUT

| Option | Default | Notes |
| --- | --- | --- |
| `level` | `6` | produces an `N³ × N³` image (lvl 6 → 216², lvl 8 → 512², lvl 12 → 1728²) |

Always emit a single frame with `-frames:v 1`. The PNG is the identity LUT — grade it in
your color tool and apply back with the `haldclut` filter (see `ffmpeg-lut-grade`).

### `nullsrc` / `rgbtestsrc` (placeholder)

`nullsrc` produces uninitialised frames — useful only as a placeholder fed into another
filter that overwrites it (e.g. a multi-input `filter_complex` graph). Don't encode it.

---

## Audio sources

### `sine` — single sine

| Option | Default | Notes |
| --- | --- | --- |
| `frequency` / `f` | `440` | Hz |
| `beep_factor` / `b` | `0` | if non-zero, play a higher tone every N periods |
| `sample_rate` / `r` | `44100` | Hz |
| `duration` / `d` | infinite | seconds |
| `samples_per_frame` | `1024` | frame granularity |

### `anullsrc` — digital silence

| Option | Default | Notes |
| --- | --- | --- |
| `channel_layout` / `cl` | `stereo` | mono / stereo / 5.1 / 7.1 / etc |
| `sample_rate` / `r` | `44100` | Hz |
| `nb_samples` / `n` | `1024` | samples per frame |
| `duration` / `d` | infinite | cap with `-t` instead |

### `anoisesrc` — colored noise

| Option | Default | Notes |
| --- | --- | --- |
| `sample_rate` / `r` | `48000` | Hz |
| `amplitude` / `a` | `1.0` | 0.0-1.0 |
| `duration` / `d` | infinite | |
| `color` / `colour` | `white` | `white`, `pink`, `brown`/`brownian`, `blue`, `violet`, `velvet` |
| `seed` | `-1` | RNG seed |
| `nb_samples` | `1024` | |

### `aevalsrc` — expression-driven audio

| Option | Default | Notes |
| --- | --- | --- |
| `exprs` | — (required) | `\|`-separated per-channel expressions |
| `duration` / `d` | infinite | |
| `nb_samples` / `n` | `1024` | |
| `sample_rate` / `s` | `44100` | |
| `channel_layout` / `c` | `stereo` if 2 exprs, `mono` if 1 | override with `cl=` |

Expression variables/constants available inside `exprs`:

| Symbol | Meaning |
| --- | --- |
| `t` | current sample time (seconds) |
| `n` | number of samples since start |
| `TB` | timebase |
| `s` | sample rate |
| `PI`, `E`, `PHI` | constants |

Operators/functions: `+ - * /`, `abs`, `sin`, `cos`, `tan`, `exp`, `log`, `floor`,
`sqrt`, `hypot`, `mod`, `if(cond,a,b)`, `eq/gte/lte(a,b)`, `random(seed)`.

Examples:

- 440 Hz left, 880 Hz right: `aevalsrc="sin(440*2*PI*t)|sin(880*2*PI*t)"`
- Amplitude ramp: `aevalsrc="0.5*(t/10)*sin(1000*2*PI*t):d=10"`
- Linear chirp 100 → 2000 Hz over 5 s: `aevalsrc="sin(2*PI*(100+(2000-100)*(t/5))*t):d=5"`

### `flite` — Festival-lite TTS

| Option | Default | Notes |
| --- | --- | --- |
| `text` | — | text to speak |
| `textfile` | — | read text from file |
| `voice` / `v` | `kal` | `kal`, `slt`, `awb`, `rms`, `kal16` etc |
| `nb_samples` / `n` | `512` | |

Only present if ffmpeg was compiled with `--enable-libflite`. Verify:
`ffmpeg -filters | grep flite`.

---

## Color name table (accepted wherever a filter takes a color)

FFmpeg accepts CSS-level color keywords plus `random`, hex (`0xRRGGBB`), and
`#RRGGBB` / `#RRGGBBAA`. Alpha is appended with `@0.5` (0.0-1.0).

Common palette (full set is HTML + CSS3):

```
AliceBlue, AntiqueWhite, Aqua, Aquamarine, Azure, Beige, Bisque, Black,
BlanchedAlmond, Blue, BlueViolet, Brown, BurlyWood, CadetBlue, Chartreuse,
Chocolate, Coral, CornflowerBlue, Cornsilk, Crimson, Cyan, DarkBlue, DarkCyan,
DarkGoldenRod, DarkGray, DarkGreen, DarkKhaki, DarkMagenta, DarkOliveGreen,
DarkOrange, DarkOrchid, DarkRed, DarkSalmon, DarkSeaGreen, DarkSlateBlue,
DarkSlateGray, DarkTurquoise, DarkViolet, DeepPink, DeepSkyBlue, DimGray,
DodgerBlue, FireBrick, FloralWhite, ForestGreen, Fuchsia, Gainsboro, GhostWhite,
Gold, GoldenRod, Gray, Green, GreenYellow, HoneyDew, HotPink, IndianRed, Indigo,
Ivory, Khaki, Lavender, LavenderBlush, LawnGreen, LemonChiffon, LightBlue,
LightCoral, LightCyan, LightGoldenRodYellow, LightGray, LightGreen, LightPink,
LightSalmon, LightSeaGreen, LightSkyBlue, LightSlateGray, LightSteelBlue,
LightYellow, Lime, LimeGreen, Linen, Magenta, Maroon, MediumAquamarine,
MediumBlue, MediumOrchid, MediumPurple, MediumSeaGreen, MediumSlateBlue,
MediumSpringGreen, MediumTurquoise, MediumVioletRed, MidnightBlue, MintCream,
MistyRose, Moccasin, NavajoWhite, Navy, OldLace, Olive, OliveDrab, Orange,
OrangeRed, Orchid, PaleGoldenRod, PaleGreen, PaleTurquoise, PaleVioletRed,
PapayaWhip, PeachPuff, Peru, Pink, Plum, PowderBlue, Purple, RebeccaPurple, Red,
RosyBrown, RoyalBlue, SaddleBrown, Salmon, SandyBrown, SeaGreen, SeaShell,
Sienna, Silver, SkyBlue, SlateBlue, SlateGray, Snow, SpringGreen, SteelBlue,
Tan, Teal, Thistle, Tomato, Turquoise, Violet, Wheat, White, WhiteSmoke, Yellow,
YellowGreen
```

Plus: `random` (single random pick per invocation), `black@0.5` (alpha), and
the bare-fallback names `r`, `g`, `b`, `y`, `c`, `m` in some filters.

---

## Recipe gallery

### Broadcast cal — SMPTE HD bars + 1 kHz at -20 dBFS, 1 minute MXF

```bash
ffmpeg -f lavfi -i smptehdbars=size=1920x1080:rate=30 \
       -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
       -af "volume=-20dB" \
       -t 60 -c:v libx264 -pix_fmt yuv420p -crf 16 \
       -c:a pcm_s24le lineup.mxf
```

### ABX pink-noise reference, 30 s FLAC

```bash
ffmpeg -f lavfi -i "anoisesrc=color=pink:sample_rate=96000:amplitude=0.5:duration=30" \
       -c:a flac pink_30s.flac
```

### Gradient overlay plate for lower-third titles

```bash
ffmpeg -f lavfi -i "gradients=s=1920x200:c0=#0a1f44:c1=#113a7a:type=linear:speed=0.002:duration=10" \
       -c:v libx264 -pix_fmt yuv420p lower_third.mp4
```

### 4K 60 fps encoder stress-test, 30 s

```bash
ffmpeg -f lavfi -i testsrc2=size=3840x2160:rate=60 \
       -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
       -t 30 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac stress.mp4
```

### Identity Hald CLUT — round-trip for LUT authoring

```bash
ffmpeg -f lavfi -i haldclutsrc=level=8 -frames:v 1 identity.png
# Grade identity.png in Photoshop/DaVinci/Affinity. Save as graded.png.
# Apply back via lut-grade:
ffmpeg -i source.mov -i graded.png \
       -filter_complex "[0:v][1:v]haldclut" -c:a copy graded.mov
```

### Synthetic image sequence for a `concat` test

```bash
for i in 01 02 03 04 05; do
  ffmpeg -f lavfi -i "color=c=red:size=640x360:duration=1:rate=30, \
                       drawtext=text='clip ${i}':fontsize=72:x=60:y=140:fontcolor=white" \
         -c:v libx264 -pix_fmt yuv420p "clip_${i}.mp4" -y
done
```

### Stereo channel-identification tone

Left = 500 Hz, Right = 1000 Hz for 10 s:

```bash
ffmpeg -f lavfi -i "aevalsrc=exprs=0.5*sin(500*2*PI*t)|0.5*sin(1000*2*PI*t):d=10:s=48000" \
       -c:a pcm_s16le stereo_id.wav
```

### Silence marry-in for a video-only capture

```bash
ffmpeg -i cam.mov \
       -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
       -map 0:v -map 1:a -c:v copy -c:a aac -shortest withaudio.mp4
```
