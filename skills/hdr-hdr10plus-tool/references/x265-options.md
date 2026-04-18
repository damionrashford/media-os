# x265 HDR10+ encode flags

When baking HDR10+ at encode time with x265, the `--dhdr10-info` flag accepts a Samsung-format HDR10+ JSON (as produced by `hdr10plus_tool extract`).

## Essential HDR10 flags (needed alongside --dhdr10-info)

| Flag | Value | Purpose |
|---|---|---|
| `--colorprim` | `bt2020` | Color primaries |
| `--transfer` | `smpte2084` | PQ transfer function (HDR10) |
| `--colormatrix` | `bt2020nc` | Non-constant luminance YCbCr |
| `--hdr10` | (flag) | Enable HDR10 metadata output |
| `--hdr10-opt` | (flag) | Enable HDR10-specific rate-control optimisations |
| `--repeat-headers` | (flag) | Repeat VPS/SPS/PPS on each IDR (needed for some muxers) |

## HDR10+ dynamic-metadata flag

| Flag | Value | Purpose |
|---|---|---|
| `--dhdr10-info` | path to JSON | Embed HDR10+ SEI per-frame at encode time |
| `--dhdr10-opt` | (flag, rare) | Optimisations specific to dynamic HDR10+ |

## Static HDR10 metadata flags

| Flag | Value | Purpose |
|---|---|---|
| `--max-cll` | `MaxCLL,MaxFALL` in cd/m² | Static MaxCLL/MaxFALL SEI |
| `--master-display` | `G(…)B(…)R(…)WP(…)L(max,min)` | Master-display colour volume SEI |

Example `--master-display` string for DCI-P3 mastered to 1000 nits:

```
G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)
```

(x265 expects values scaled by 50000 for chromaticities and by 10000 for luminance per the x265 docs.)

## Full template command

```
x265 --y4m --input source.y4m \
     --crf 18 --preset slow \
     --colorprim bt2020 --transfer smpte2084 --colormatrix bt2020nc \
     --hdr10 --hdr10-opt --repeat-headers \
     --dhdr10-info metadata.json \
     --master-display 'G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)' \
     --max-cll '1000,400' \
     --output out.hevc
```

## Verifying HDR10+ in the output

```bash
hdr10plus_tool extract -i out.hevc -o verify.json
# if verify.json has per-frame data, SEI survived
```

Or with MediaInfo:

```bash
mediainfo --Inform='Video;%HDR_Format%' out.mkv
# should mention HDR10+ if present
```

## Why x265 > inject

- Single pass (no extract-encode-inject-remux dance).
- SEI placement is guaranteed correct relative to slices.
- Easier to reproduce builds — the full encode is one command.

Use `hdr10plus_tool inject` only when re-encoding isn't possible (licence restrictions, encode-time unavailability, etc.).

## Common gotchas

- `--dhdr10-info` requires x265 built with HDR10+ support. Check `x265 --help 2>&1 | grep dhdr10`.
- Use 10-bit x265 builds for HDR content. 8-bit x265 can tag output HDR but playback devices often reject it.
- Samsung HDR10+ JSON format is specific — don't feed a dovi_tool RPU or a generic metadata dump.
- Keep the encode's frame count matching the JSON's frame count. Mismatches cause HDR10+ to drop silently on some TVs.
