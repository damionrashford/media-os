# FFmpeg Bitstream Filters — Reference

Bitstream filters ("bsf") rewrite packet metadata / framing / NAL-unit structure
**without decoding the compressed payload**. They run between the demuxer and the
muxer and are applied on streams being copied (`-c copy`). Re-encoding rewrites
extradata itself and bypasses the bsf.

Upstream doc: <https://ffmpeg.org/ffmpeg-bitstream-filters.html>

---

## 1. Complete bsf reference table

Codec column: `*` = codec-agnostic (runs on any stream).

| Filter                  | Codec      | Purpose                                                                               | Key options |
|-------------------------|------------|---------------------------------------------------------------------------------------|-------------|
| `aac_adtstoasc`         | AAC        | Convert ADTS-framed AAC → MPEG-4 AudioSpecificConfig (MP4/MOV/MKV audio muxers need this). | — |
| `av1_frame_merge`       | AV1        | Merge OBU streams into single frame packets. | — |
| `av1_frame_split`       | AV1        | Split combined AV1 OBU packets into per-frame packets. | — |
| `av1_metadata`          | AV1        | Rewrite AV1 OBU metadata (color, AFD, tile info, timing). | `color_primaries`, `transfer_characteristics`, `matrix_coefficients`, `color_range`, `chroma_sample_position`, `tick_rate`, `num_ticks_per_picture`, `delete_padding` |
| `chomp`                 | `*`        | Strip trailing zero-byte padding from packets (legacy TS fix). | — |
| `dca_core`              | DTS        | Extract the DTS core substream from DTS-HD packets. | — |
| `dts2pts`               | `*`        | Derive missing PTS from DTS. | — |
| `dump_extra`            | `*`        | Repeat codec extradata before selected packets (commonly every keyframe). | `freq` = `k` (keyframes) / `all` / `e` (extradata-only packets) |
| `eac3_core`             | E-AC-3     | Extract AC-3 core from E-AC-3. | — |
| `extract_extradata`     | `*`        | Pull extradata (SPS/PPS/VPS/etc) out as packet side-data. | `remove` (int, 0/1) |
| `filter_units`          | H.264/HEVC/AV1/MPEG-2/VVC | Drop or whitelist NAL / OBU units by type. | `pass_types`, `remove_types`, `discard_flags` (see §6) |
| `h264_metadata`         | H.264      | Rewrite SPS/PPS fields (level, VUI, SAR, crop, AUD, SEI). | see §5 |
| `h264_mp4toannexb`      | H.264      | AVCC (length-prefixed) → Annex-B (start-code) framing. Required MP4/MOV → TS/FLV/HLS. | — |
| `h264_redundant_pps`    | H.264      | Rewrite redundant PPS to be consistent across packets. | — |
| `hapqa_extract`         | HAP-Q      | Extract HAP-Q packets from HAP streams. | — |
| `hevc_metadata`         | HEVC       | Rewrite VPS/SPS/PPS (level, tier, VUI, color, SAR). | see §5 |
| `hevc_mp4toannexb`      | HEVC       | AVCC → Annex-B framing for HEVC. Required MP4/MOV → TS. | — |
| `imx_dump_header`       | IMX MPEG-2 | Emit IMX header data for broadcast workflows. | — |
| `media100_to_mjpegb`    | Media100   | Convert Media100 → MJPEG-B. | — |
| `mjpeg2jpeg`            | MJPEG      | Split an MJPEG video stream into independent JPEG packets. | — |
| `mjpega_dump_header`    | MJPEG-A    | Emit MJPEG-A header. | — |
| `mov2textsub`           | mov_text   | Extract mov_text into plaintext. | — |
| `mp3decomp`             | MP3        | Decompress MP3 ADU → regular MP3 frames. | — |
| `mpeg2_metadata`        | MPEG-2     | Rewrite MPEG-2 sequence/display headers. | `display_aspect_ratio`, `frame_rate`, `video_format`, `colour_primaries`, `transfer_characteristics`, `matrix_coefficients` |
| `mpeg4_unpack_bframes`  | MPEG-4 ASP | Fix packed B-frames in DivX/XviD-era MP4s. | — |
| `noise`                 | `*`        | Random byte fuzzing (robustness testing). | `amount`, `drop`, `dropamount` |
| `null`                  | `*`        | No-op (debugging placeholder). | — |
| `opus_metadata`         | Opus       | Rewrite Opus header gain / channel-mapping fields. | `gain` |
| `pcm_rechunk`           | PCM        | Repack PCM packets to a fixed duration. | `nb_out_samples`, `pad`, `frame_rate` |
| `prores_metadata`       | ProRes     | Rewrite ProRes color-tag fields. | `color_primaries`, `transfer_characteristics`, `matrix_coefficients` |
| `remove_extra`          | `*`        | Strip extradata already present in packets. | `freq` = `k` / `all` / `e` |
| `setts`                 | `*`        | Expression-driven PTS/DTS rewrite. | `ts`, `pts`, `dts`, `duration` |
| `showinfo`              | `*`        | Print packet info to stderr (debug). | — |
| `text2movsub`           | `*`        | Wrap plaintext subtitle in mov_text. | — |
| `trace_headers`         | H.264/HEVC/MPEG-2/VP9/AV1/VVC | Dump decoded CBS headers to stderr (read-only). | Requires CBS support. |
| `truehd_core`           | TrueHD     | Extract AC-3 core from TrueHD. | — |
| `vp9_metadata`          | VP9        | Rewrite VP9 color / profile fields. | `color_space`, `color_range` |
| `vp9_raw_reorder`       | VP9        | Repack VP9 packets into proper decode order. | — |
| `vp9_superframe`        | VP9        | Repack into VP9 superframes. | — |
| `vp9_superframe_split`  | VP9        | Inverse of `vp9_superframe`. | — |

Enumerate what your local build supports: `ffmpeg -bsfs`.

---

## 2. Codec ↔ bsf matrix

| Codec     | Framing / extradata fixers                                          | Metadata rewriter      | Other                  |
|-----------|---------------------------------------------------------------------|------------------------|------------------------|
| H.264     | `h264_mp4toannexb`, `extract_extradata`, `dump_extra`, `remove_extra` | `h264_metadata`        | `filter_units`, `h264_redundant_pps`, `trace_headers` |
| HEVC      | `hevc_mp4toannexb`, `extract_extradata`, `dump_extra`, `remove_extra` | `hevc_metadata`        | `filter_units`, `trace_headers` |
| AV1       | `av1_frame_merge`, `av1_frame_split`, `extract_extradata`           | `av1_metadata`         | `filter_units`, `trace_headers` |
| MPEG-2    | `extract_extradata`                                                 | `mpeg2_metadata`       | `filter_units`, `trace_headers` |
| MPEG-4 ASP| `mpeg4_unpack_bframes`                                              | —                      | — |
| VP9       | `vp9_superframe`, `vp9_superframe_split`, `vp9_raw_reorder`         | `vp9_metadata`         | `trace_headers` |
| AAC       | `aac_adtstoasc`                                                     | —                      | — |
| AC-3 / E-AC-3 / TrueHD | `eac3_core`, `truehd_core`, `dca_core`                  | —                      | — |
| MP3       | `mp3decomp`                                                         | —                      | — |
| Opus      | —                                                                   | `opus_metadata`        | — |
| ProRes    | —                                                                   | `prores_metadata`      | — |
| MJPEG     | `mjpeg2jpeg`                                                        | —                      | `mjpega_dump_header` |
| PCM       | `pcm_rechunk`                                                       | —                      | — |
| mov_text  | `mov2textsub`, `text2movsub`                                        | —                      | — |

---

## 3. Container conversion cheat-sheet

### H.264 video

| From                          | To                       | `-bsf:v`              |
|-------------------------------|--------------------------|-----------------------|
| MP4 / MOV / 3GP (AVCC)        | MPEG-TS / HLS / FLV      | `h264_mp4toannexb`    |
| MP4                           | Matroska / WebM-style MKV| none                  |
| MPEG-TS / FLV (Annex-B)       | MP4 / MOV                | none (auto)           |
| Matroska (H.264 AVCC or Annex-B) | MP4 / MOV             | none (auto)           |
| Any H.264                     | raw `.h264` / `.264`     | `h264_mp4toannexb`    |

### HEVC video

| From                    | To                    | `-bsf:v`              |
|-------------------------|-----------------------|-----------------------|
| MP4 / MOV               | MPEG-TS / HLS         | `hevc_mp4toannexb`    |
| MPEG-TS                 | MP4 / MOV             | none (auto)           |
| Any HEVC                | raw `.hevc` / `.h265` | `hevc_mp4toannexb`    |

### AAC audio

| From                    | To                | `-bsf:a`              |
|-------------------------|-------------------|-----------------------|
| MPEG-TS (ADTS)          | MP4 / MOV / MKV   | `aac_adtstoasc`       |
| Raw `.aac` (ADTS)       | MP4 / MOV         | `aac_adtstoasc`       |
| MP4 (ASC)               | MPEG-TS           | none (auto wraps to ADTS) |
| FLV (ADTS)              | MP4               | `aac_adtstoasc`       |

### DivX / XviD MPEG-4 ASP

| From / symptom                       | To    | `-bsf:v`                |
|--------------------------------------|-------|-------------------------|
| Old AVI/MP4 with packed B-frames     | MP4   | `mpeg4_unpack_bframes`  |

---

## 4. NAL unit type reference

Pass these numbers to `filter_units=remove_types=N1|N2|...`.

### H.264 (ITU-T H.264 Table 7-1, `nal_unit_type` 5-bit)

| Type | Name                                     | Typical action           |
|------|------------------------------------------|--------------------------|
| 1    | Non-IDR slice                            | never remove             |
| 2    | Slice data partition A                   | never remove             |
| 3    | Slice data partition B                   | never remove             |
| 4    | Slice data partition C                   | never remove             |
| 5    | IDR slice                                | never remove             |
| 6    | SEI (Supplemental Enhancement Info)      | often removed (timecode, CC) |
| 7    | SPS (Sequence Parameter Set)             | never remove             |
| 8    | PPS (Picture Parameter Set)              | never remove             |
| 9    | AUD (Access Unit Delimiter)              | sometimes removed (some muxers reject) |
| 10   | End of sequence                          | safe to remove           |
| 11   | End of stream                            | safe to remove           |
| 12   | Filler data                              | often removed            |
| 13   | SPS extension                            | rarely used              |
| 14   | Prefix NAL (SVC)                         | strip for AVC-only tools |
| 15   | Subset SPS (SVC / MVC)                   | strip for AVC-only tools |
| 19   | Auxiliary slice (alpha channel)          | rarely used              |
| 20   | Slice extension (SVC / MVC)              | strip for AVC-only tools |

### HEVC (ITU-T H.265 Table 7-1, `nal_unit_type` 6-bit)

| Type  | Name                                           | Notes                  |
|-------|------------------------------------------------|------------------------|
| 0-9   | Trailing / leading slices (TRAIL_N ... RASL_R) | never remove           |
| 16-21 | IRAP slices (BLA / IDR / CRA variants)         | never remove           |
| 32    | VPS (Video Parameter Set)                      | never remove           |
| 33    | SPS                                            | never remove           |
| 34    | PPS                                            | never remove           |
| 35    | AUD                                            | sometimes removed      |
| 36    | End of sequence                                | safe to remove         |
| 37    | End of bitstream                               | safe to remove         |
| 38    | Filler data                                    | often removed          |
| 39    | SEI prefix                                     | often removed          |
| 40    | SEI suffix                                     | often removed          |

Example — strip all SEI from HEVC: `-bsf:v "filter_units=remove_types=39|40"`.

---

## 5. `h264_metadata` / `hevc_metadata` / `av1_metadata` option catalog

All three filters accept similar color/VUI fields; only H.264 and HEVC have
level/profile/tier rewriting.

### `h264_metadata`

| Option                        | Type   | Purpose                                         |
|-------------------------------|--------|-------------------------------------------------|
| `aud`                         | enum   | `pass` / `insert` / `remove` AUD NAL units      |
| `sample_aspect_ratio`         | rational | Rewrite SAR in VUI (e.g. `1/1`, `4/3`)         |
| `overscan_appropriate_flag`   | int    | 0 / 1                                            |
| `video_format`                | int    | 0=component, 1=PAL, 2=NTSC, 3=SECAM, 4=MAC, 5=unspec |
| `video_full_range_flag`       | int    | 0 / 1 (studio vs full range)                    |
| `colour_primaries`            | int    | ITU-T H.273 code (1=BT.709, 9=BT.2020, ...)     |
| `transfer_characteristics`    | int    | H.273 code (1=BT.709, 16=PQ / SMPTE2084, 18=HLG) |
| `matrix_coefficients`         | int    | H.273 code (1=BT.709, 9=BT.2020 NCL, ...)       |
| `chroma_sample_loc_type`      | int    | 0-5                                              |
| `tick_rate`                   | rational | VUI time-scale / num-units-in-tick            |
| `fixed_frame_rate_flag`       | int    | 0 / 1                                            |
| `zero_new_constraint_set_flags` | int  | 0 / 1                                            |
| `crop_left` / `crop_right` / `crop_top` / `crop_bottom` | int | Rewrite frame-crop offsets |
| `sei_user_data`               | string | Add UUID+payload SEI per packet (`UUID+hex`)    |
| `delete_filler`               | int    | 0 / 1                                            |
| `display_orientation`         | enum   | `pass` / `insert` / `remove` / `extract`        |
| `rotate`                      | double | Degrees of rotation to signal in SEI             |
| `flip`                        | flags  | `horizontal` / `vertical`                        |
| `level`                       | string | `auto` or level number: `1`, `1b`, `1.1`, `1.2`, `1.3`, `2`, `2.1`, `2.2`, `3`, `3.1`, `3.2`, `4`, `4.1`, `4.2`, `5`, `5.1`, `5.2`, `6`, `6.1`, `6.2` |

### `hevc_metadata`

Mostly the same names as above, plus:

| Option      | Purpose                                                    |
|-------------|------------------------------------------------------------|
| `tier`      | `main` / `high`                                            |
| `level`     | e.g. `3`, `3.1`, `4`, `4.1`, `5`, `5.1`, `5.2`, `6`, `6.1`, `6.2` |
| `aud`       | `pass` / `insert` / `remove`                               |

### `av1_metadata`

| Option                       | Purpose                                             |
|------------------------------|-----------------------------------------------------|
| `color_primaries`            | H.273 code                                           |
| `transfer_characteristics`   | H.273 code                                           |
| `matrix_coefficients`        | H.273 code                                           |
| `color_range`                | `tv` / `pc`                                          |
| `chroma_sample_position`     | `unknown` / `vertical` / `colocated`                 |
| `tick_rate`                  | rational — time-scale / num-ticks-per-pic            |
| `num_ticks_per_picture`      | int                                                  |
| `delete_padding`             | int — drop padding OBUs                              |

---

## 6. `filter_units` options

| Option          | Type          | Purpose                                                                 |
|-----------------|---------------|-------------------------------------------------------------------------|
| `pass_types`    | `|`-separated | Whitelist: keep ONLY these NAL/OBU types, drop everything else          |
| `remove_types`  | `|`-separated | Blacklist: drop these types, keep everything else                       |
| `discard_flags` | flags         | `none`, `nonref`, `nonintra`, `nonkey`, `all` — drop packets by property |

Only one of `pass_types` / `remove_types` may be set per instance.

**Recipes:**

```bash
# H.264 — keep only SPS/PPS/IDR/non-IDR/SEI:
-bsf:v "filter_units=pass_types=1|5|6|7|8"

# HEVC — strip all SEI (prefix + suffix):
-bsf:v "filter_units=remove_types=39|40"

# Drop every non-reference frame (HEVC NAL types 0/2/4/6/8 are _N variants):
-bsf:v "filter_units=discard_flags=nonref"
```

---

## 7. `setts` expression grammar

Syntax: `setts=ts=EXPR[:pts=EXPR][:dts=EXPR][:duration=EXPR]`.
`ts=` is a shortcut that sets BOTH pts and dts to the same expression.

**Variables:**

| Name          | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| `PTS`         | Current packet's input PTS (packet-timebase units)        |
| `DTS`         | Current packet's input DTS                                |
| `STARTPTS`    | PTS of the first packet seen on this stream               |
| `STARTDTS`    | DTS of the first packet seen on this stream               |
| `PREV_INPTS`  | Previous packet's input PTS                               |
| `PREV_OUTPTS` | Previous packet's output PTS                              |
| `PREV_INDTS`  | Previous packet's input DTS                               |
| `PREV_OUTDTS` | Previous packet's output DTS                              |
| `N`           | 0-based index of the current packet                       |
| `POS`         | Byte offset of the packet in the source, or -1 if unknown |
| `DURATION`    | Packet's duration in timebase units                       |
| `TB`          | The packet's timebase (a fraction, e.g. 1/90000 for TS)   |
| `NOPTS`       | AV_NOPTS_VALUE constant (use for "unset")                 |
| `S`           | Sample rate (audio only)                                  |
| `SR`          | Sample rate in Hz (audio)                                 |

Timebase conversion: a duration of `X` seconds = `X / TB` timebase units.

**Common recipes:**

```bash
# Zero-base timestamps (keep spacing):
-bsf:v "setts=ts=PTS-STARTPTS"

# Shift forward by 2.0 seconds:
-bsf:v "setts=ts=PTS+2/TB"

# Monotonically increasing integer timestamps (clobbers timing):
-bsf:v "setts=ts=N"

# Rebase timestamps onto a 90kHz timebase (e.g. for MPEG-TS):
-bsf:v "setts=ts=PTS*90000*TB"

# Clear DTS (let the muxer re-derive it):
-bsf:v "setts=dts=NOPTS"

# Independent rewrites of pts and dts:
-bsf:v "setts=pts=PTS-STARTPTS:dts=DTS-STARTDTS"
```

**Warning:** you must preserve `DTS <= PTS` for B-frame streams, or the muxer will
reject the packets as out-of-order.

---

## 8. bsf argument syntax

- Single bsf: `-bsf:v filter_name`
- With options: `-bsf:v "filter_name=opt1=val1:opt2=val2"`
- Multiple filters chained (comma-separated, left-to-right):
  `-bsf:v "h264_mp4toannexb,dump_extra=freq=k,h264_metadata=level=4.1"`
- Stream-specific: `-bsf:v:0 ...` (only first video stream),
  `-bsf:a:1 aac_adtstoasc` (second audio stream).

Always quote the argument if it contains `=` or `:` to avoid shell splitting.

---

## 9. Introspection

```bash
# List every bsf supported by your build:
ffmpeg -bsfs

# Show options for a specific bsf:
ffmpeg -h bsf=h264_metadata
ffmpeg -h bsf=filter_units
ffmpeg -h bsf=setts
```

These are the only reliable way to discover build-specific additions or missing
filters (CBS-dependent filters won't appear if CBS wasn't compiled in).
