# Color-Space and HDR Reference

Detailed reference material for the `ffmpeg-hdr-color` skill. Read this when
you need to pick a tone-map operator, look up a `zscale` option, understand
the difference between DV profiles, or decode the meaning of a color-tag.

---

## Tone-mapping operators (`tonemap=tonemap=...`)

All operators expect linear-light, floating-point input (`gbrpf32le`). All
accept optional `param=` to tune aggressiveness and `desat=` (0 = preserve
saturation, higher = desaturate highlights).

| Operator   | Curve type                         | Pros                                       | Cons / Notes                                                  | Typical `param` |
| ---------- | ---------------------------------- | ------------------------------------------ | ------------------------------------------------------------- | --------------- |
| `hable`    | Filmic curve (Uncharted 2)         | Safe default, good highlight roll-off, preserves midtones | Slightly dark midtones at extreme peaks                      | — (no param)    |
| `mobius`   | Mobius transformation, smooth knee | Softer roll-off than hable, gentle on faces | Can slightly flatten contrast                                 | `0.3`–`0.6`     |
| `reinhard` | Classic Reinhard `x / (x + c)`     | Simple, fast                                | Flat midtones, can crush blacks                               | `0.5`           |
| `gamma`    | Power curve                         | Predictable tone behaviour                   | Ignores peak; highlights still clip                           | `1.8`–`2.4`     |
| `clip`     | Hard clip                           | Fastest, preserves lows perfectly            | Severe banding/clipping in highlights                         | —               |
| `linear`   | Straight scale by `param`           | Useful for SDR→HDR inverse work              | Not a real tone map for HDR→SDR                                | `1.5`–`4.0`     |

Default recommendation: `tonemap=hable:desat=0`.

---

## `zscale` parameters

`zscale` is the ffmpeg wrapper around zimg. It handles color-space,
transfer, primaries, matrix, range, and resize.

| Key      | Meaning                              | Common values                                                                 |
| -------- | ------------------------------------ | ----------------------------------------------------------------------------- |
| `w` / `h`| Output width/height                  | numeric, or `-1` to preserve                                                   |
| `p`      | Output primaries                     | `bt709`, `bt2020`, `smpte170m`, `bt470bg`                                     |
| `t`      | Output transfer                      | `bt709`, `smpte2084`, `arib-std-b67`, `linear`, `iec61966-2-1` (sRGB)          |
| `m`      | Output matrix                        | `bt709`, `bt2020nc`, `bt2020c`, `smpte170m`                                    |
| `r`      | Output range                         | `tv` (limited), `pc` (full)                                                     |
| `pin`    | Input primaries (override)           | same values as `p`                                                              |
| `tin`    | Input transfer (override)            | same values as `t` — needed for HLG input (`arib-std-b67`)                      |
| `min`    | Input matrix (override)              |                                                                                 |
| `rin`    | Input range (override)               |                                                                                 |
| `npl`    | Nominal peak luminance (cd/m²)       | `100` (SDR), `203` (broadcast HDR ref), `1000` (PQ ref)                         |
| `d`      | Dither method                        | `none`, `ordered`, `random`, `error_diffusion`                                  |
| `f`      | Filter for resize                    | `bilinear`, `bicubic`, `lanczos`, `spline36`                                    |

Typical patterns:

- Linearize PQ: `zscale=t=linear:npl=100,format=gbrpf32le`
- Linearize HLG: `zscale=t=linear:npl=100:tin=arib-std-b67,format=gbrpf32le`
- Back to SDR: `zscale=t=bt709:m=bt709:r=tv,format=yuv420p`
- BT.2020 → BT.709 (SDR): `zscale=primaries=709:transfer=709:matrix=709`

---

## `libplacebo` options

Requires `-init_hw_device vulkan` and ffmpeg built with `--enable-libplacebo --enable-vulkan`.

| Option                | Values                                                                                 | Notes                                                               |
| --------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `tonemapping`         | `auto`, `clip`, `st2094-40`, `st2094-10`, `bt.2390`, `bt.2446a`, `spline`, `reinhard`, `mobius`, `hable`, `gamma`, `linear` | `bt.2390` is the current recommended SMPTE standard curve.          |
| `colorspace`          | `bt709`, `bt2020nc`, `bt2020c`                                                         | Output YUV matrix.                                                  |
| `color_primaries`     | `bt709`, `bt2020`, `smpte170m`, `bt470bg`                                              | Output primaries tag.                                               |
| `color_trc`           | `bt709`, `smpte2084`, `arib-std-b67`, `linear`                                          | Output transfer tag.                                                |
| `format`              | `yuv420p`, `yuv420p10le`, `p010le`, `nv12`                                             | Output pixel format.                                                |
| `gamut_mode`          | `clip`, `warn`, `darken`, `desaturate`                                                  | What to do when input gamut exceeds output.                         |
| `dither`              | `none`, `blue`, `ordered`, `ordered_fixed`, `white`                                     | `blue` noise is highest quality.                                    |
| `deband`              | `0` / `1`                                                                              | Enable debanding (very effective on PQ sources).                    |
| `deband_iterations`   | integer                                                                                | More iterations = stronger debanding, slower.                       |
| `peak_detect`         | `0` / `1`                                                                              | Dynamic peak detection; enable for variable source mastering.       |
| `smoothing_period`    | float                                                                                  | Frame-to-frame smoothing of detected peak.                          |

Example: `libplacebo=tonemapping=bt.2390:colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p:gamut_mode=desaturate:deband=1:peak_detect=1`

---

## `colorspace` filter

CPU-only, no linearization/tone-map. Use for SDR-to-SDR matrix/primaries/trc
conversion when `zscale` is unavailable.

```
colorspace=all=bt709:iall=bt2020ncl:fast=1
```

Keys: `all` (output), `iall` (input), `ispace`, `irange`, `iprimaries`, `itrc`,
`space`, `range`, `primaries`, `trc`, `format`, `fast` (0/1), `dither` (none/fsb).

Does **not** handle PQ → gamma; use `tonemap` or `libplacebo` for HDR sources.

---

## HDR metadata profiles

| Format        | Transfer       | Peak metadata                         | Dynamic metadata                   | ffmpeg tone-map path                             |
| ------------- | -------------- | ------------------------------------- | ---------------------------------- | ------------------------------------------------ |
| **HDR10**     | PQ (`smpte2084`) | Static `MaxCLL` / `MaxFALL` + mastering display | None                               | Straightforward                                  |
| **HDR10+**    | PQ             | Static + per-scene                     | SMPTE ST 2094-40 JSON              | Dynamic metadata is dropped (SDR ignores it)    |
| **HLG**       | `arib-std-b67` | Implicit (system gamma)                 | None                               | Use `tin=arib-std-b67`                           |
| **Dolby Vision profile 4** | PQ   | Static + RPU                           | Dolby RPU                          | Legacy, rare                                     |
| **DV profile 5** | PQ (IPTPQc2) | RPU only (no HDR10 fallback)           | Dolby RPU                          | Single-layer; tone-map like HDR10 (colors off without DV decoder) |
| **DV profile 7** | PQ           | BL + EL + RPU (dual layer)              | Dolby RPU                          | ffmpeg cannot combine BL+EL; use `dovi_tool`    |
| **DV profile 8.1** | PQ         | HDR10-compatible BL + RPU              | Dolby RPU                          | Tone-map BL as HDR10 (works); RPU ignored       |
| **DV profile 8.4** | HLG        | HLG-compatible BL + RPU                | Dolby RPU                          | Tone-map BL as HLG; RPU ignored                  |

Workflow for DV p7 → SDR: `dovi_tool remove -m 2 input.hevc -o bl.hevc` then
tone-map `bl.hevc` as regular HDR10.

---

## Color tag reference tables

### Primaries (`color_primaries`)

| Value        | Aliases                 | Meaning                            |
| ------------ | ----------------------- | ---------------------------------- |
| `bt709`      | `709`                   | Rec.709 / sRGB                     |
| `bt2020`     | `2020`                  | Rec.2020 / UHD                     |
| `bt470bg`    | `470bg`                 | PAL/SECAM                          |
| `smpte170m`  | `170m`                  | NTSC, Rec.601                      |
| `smpte240m`  |                         | SMPTE 240M                         |
| `film`       |                         | Generic cinema film                 |
| `smpte428`   | `xyz`                   | DCI-XYZ                            |
| `smpte431`   | `dci-p3`                | DCI P3                             |
| `smpte432`   | `p3-d65`                | Display P3                          |

### Transfer (`color_trc`)

| Value           | Aliases        | Meaning                                     |
| --------------- | -------------- | ------------------------------------------- |
| `bt709`         | `709`          | Rec.709 gamma (~2.0 encode)                 |
| `smpte170m`     |                | Rec.601 / NTSC                              |
| `smpte2084`     | `pq`           | Perceptual Quantizer (HDR10)                |
| `arib-std-b67`  | `hlg`          | Hybrid Log-Gamma (BBC/NHK)                   |
| `linear`        |                | Linear light                                 |
| `gamma22`       |                | Pure gamma 2.2                               |
| `gamma28`       |                | Pure gamma 2.8                               |
| `iec61966-2-1`  | `sRGB`         | sRGB piece-wise                              |
| `log`           |                | Log100                                       |
| `log_sqrt`      |                | Log316                                       |
| `bt2020-10`     |                | BT.2020 10-bit                               |
| `bt2020-12`     |                | BT.2020 12-bit                               |

### Matrix (`colorspace`)

| Value          | Meaning                                    |
| -------------- | ------------------------------------------ |
| `bt709`        | Rec.709 YCbCr                              |
| `bt2020nc`     | Rec.2020 non-constant luminance            |
| `bt2020c`      | Rec.2020 constant luminance                |
| `smpte170m`    | Rec.601 YCbCr                              |
| `rgb`          | Identity (GBR)                             |
| `ycgco`        | YCgCo                                      |
| `fcc`          | FCC 73.682                                 |

### Range (`color_range`)

- `tv` / `mpeg` / `limited`: 16–235 (8-bit) — broadcast, streaming default.
- `pc` / `jpeg` / `full`: 0–255 — computer graphics, JPEG, some RAW.

---

## Verification recipe

After any HDR → SDR or primaries change, always re-probe the output to confirm
tags actually wrote through. Containers sometimes silently drop them.

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=pix_fmt,color_space,color_transfer,color_primaries,color_range \
  -of default=nw=1 out.mp4
```

Expected after HDR → SDR:

```
pix_fmt=yuv420p
color_range=tv
color_space=bt709
color_transfer=bt709
color_primaries=bt709
```

If any field shows `unknown` or `reserved`, the output `-color_*` flags were
not passed and players will guess — often wrong. Re-run the encode with the
explicit flags (see SKILL.md Step 4).

Also confirm side-data is gone:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream_side_data=+ \
  -of json out.mp4
```

An SDR deliverable should have **no** `Mastering display metadata`, **no**
`Content light level metadata`, **no** `HDR Dynamic Metadata SMPTE2094-40`,
**no** `DOVI configuration record`.
