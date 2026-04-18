---
name: ffmpeg-bitstream
description: >
  Apply bitstream filters (-bsf) with ffmpeg to rewrite packet metadata without re-encoding: h264_mp4toannexb, hevc_mp4toannexb, aac_adtstoasc, extract_extradata, dump_extra, setts, noise, remove_extra, filter_units, mjpeg2jpeg, mpeg4_unpack_bframes. Use when the user asks to fix MP4-to-TS mux errors, convert H.264/HEVC between MP4 and Annex-B, fix AAC ADTS to ASC for MP4, repair a broken container, change PTS/DTS without re-encode, or extract raw codec extradata/SPS-PPS.
argument-hint: "[filter] [input]"
---

# Ffmpeg Bitstream

**Context:** $ARGUMENTS

## Quick start

- **MP4 H.264 → TS/HLS:** `-bsf:v h264_mp4toannexb` → Step 3, recipe A
- **MP4 HEVC → TS:** `-bsf:v hevc_mp4toannexb` → Step 3, recipe A
- **TS AAC → MP4:** `-bsf:a aac_adtstoasc` → Step 3, recipe B
- **Old DivX/XviD packed B-frames:** `-bsf:v mpeg4_unpack_bframes` → Step 3, recipe D
- **Rewrite H.264 level / VUI:** `-bsf:v h264_metadata=...` → Step 3, recipe E
- **Strip SEI / AUD / filler NALs:** `-bsf:v filter_units=remove_types=6` → Step 3, recipe F
- **Dump extradata into every keyframe (streaming recovery):** `-bsf:v dump_extra=freq=k`
- **Zero-base timestamps without re-encoding:** `-bsf:v setts=ts=PTS-STARTPTS`
- **Debug NAL/SPS/PPS structure:** `-bsf:v trace_headers`

## When to use

- Container mux fails with `Malformed AAC bitstream detected` / `H.264 bitstream not in Annex-B format`.
- Need to remux MP4 ↔ TS / HLS / MKV with `-c copy` (no re-encode, no quality loss).
- Change H.264/HEVC level, profile, color primaries, or VUI flags without touching pixels.
- Split a stream into segments that need keyframe-carried SPS/PPS for mid-stream joins.
- Strip SEI/AUD NAL units a downstream decoder chokes on.
- Rewrite PTS/DTS on the packet level (e.g. zero-base timestamps, offset by N).
- Pull SPS/PPS out of a file for a hardware pipeline.
- Fix broken old MP4s with packed B-frames (DivX/XviD era).
- For re-encode workflows use `ffmpeg-transcode`; for trimming use `ffmpeg-cut-concat`;
  for pure container inspection use `ffmpeg-probe`.

## Step 1 — Identify the mux / codec mismatch

Probe first — bsf choice depends on codec + source container + target container:

```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name,profile -of json "$IN"
```

What to look at:

- **Video `codec_name`** = `h264` → pick `h264_mp4toannexb` or `h264_metadata`.
- **Video `codec_name`** = `hevc` / `h265` → pick `hevc_mp4toannexb` or `hevc_metadata`.
- **Audio `codec_name`** = `aac` coming from `mpegts` → need `aac_adtstoasc` for MP4.
- **Source container** = `.mp4` / `.mov` (AVCC / length-prefixed NAL) vs `.ts` / `.flv`
  (Annex-B / start-code NAL) — this is the framing that bsf rewrites.

**Container ↔ framing cheat-sheet (H.264 / HEVC):**

| Source container | Framing      | Target container | Required `-bsf:v`                    |
|------------------|--------------|------------------|--------------------------------------|
| `.mp4` / `.mov`  | AVCC         | `.ts` / HLS / `.flv` | `h264_mp4toannexb` / `hevc_mp4toannexb` |
| `.ts` / `.flv`   | Annex-B      | `.mp4` / `.mov`  | none (ffmpeg converts back automatically) |
| `.mkv`           | either       | `.mp4` / `.ts`   | usually none (mkv stores extradata out-of-band) |

**Audio (AAC):**

| Source container  | Framing | Target container | Required `-bsf:a`   |
|-------------------|---------|------------------|---------------------|
| `.ts` / `.aac`    | ADTS    | `.mp4` / `.mov`  | `aac_adtstoasc`     |
| `.mp4` / `.mkv`   | ASC     | `.ts` / `.flv`   | none (auto)         |

## Step 2 — Pick the right bsf

**Conversion filters (change framing / headers):**

- `h264_mp4toannexb` — MP4 AVCC → Annex-B. Required for MP4 → TS/HLS/FLV with `-c copy`.
  No options needed.
- `hevc_mp4toannexb` — same, for H.265/HEVC.
- `aac_adtstoasc` — ADTS → MP4 AudioSpecificConfig. Required for TS AAC → MP4 `-c copy`.
- `mpeg4_unpack_bframes` — fix old DivX/XviD MP4s that packed a B-frame inside the
  preceding P-frame. Transparent no-op on normal MP4.
- `mjpeg2jpeg` — split an MJPEG video stream into individual JPEG packets (use with
  `-c copy -f image2` to write `frame_%04d.jpg`).

**Metadata rewriters (change header fields only):**

- `h264_metadata`, `hevc_metadata`, `av1_metadata` — edit SPS/VPS/PPS/OBU fields:
  `level`, `profile`, `tier`, `aud`, `sample_aspect_ratio`, `video_format`,
  `colour_primaries`, `transfer_characteristics`, `matrix_coefficients`, `chroma_sample_loc_type`,
  `tick_rate`, `crop_{left,right,top,bottom}`, `fixed_frame_rate_flag`, `overscan_appropriate_flag`.

**Extradata manipulation:**

- `extract_extradata` — emit codec extradata (SPS/PPS) as side-data packets.
- `dump_extra=freq=k` — repeat extradata before every keyframe (makes segments
  independently decodable; costs a few bytes per IDR).
- `remove_extra=freq=k` — inverse — strip extradata from keyframes.

**NAL-unit surgery:**

- `filter_units=remove_types=6` — drop NAL units by type (see Step 3 recipe F and
  `references/filters.md` for the type table).
- `filter_units=pass_types=...` — whitelist mode.
- `filter_units=discard_flags=...` — drop packets with a given flag.

**Timing / debugging / fuzz:**

- `setts=ts=...` / `pts=...` / `dts=...` — expression-based PTS/DTS rewrite.
  Expression vocab: `PTS`, `DTS`, `STARTPTS`, `STARTDTS`, `PREV_INPTS`, `PREV_OUTPTS`,
  `PREV_INDTS`, `PREV_OUTDTS`, `N` (packet index), `TB` (timebase).
- `trace_headers` — pretty-print SPS/PPS/slice headers to stderr. Read-only.
- `noise` — random byte fuzzing for robustness testing. `amount`, `drop`, `dropamount`.

## Step 3 — Apply with `-c copy`

`-bsf:v` and `-bsf:a` only fire when the stream is copied. Any `-c:v libx264` /
`-c:a aac` re-encode rewrites extradata itself — the bsf is silently ignored.

**Recipe A — MP4 H.264/HEVC → TS / HLS:**

```bash
# H.264
ffmpeg -i in.mp4 -c copy -bsf:v h264_mp4toannexb out.ts

# HEVC
ffmpeg -i in.mp4 -c copy -bsf:v hevc_mp4toannexb out.ts
```

Modern ffmpeg auto-inserts these when muxing mpegts from mp4 — but passing the flag
explicitly is always safe and portable across older builds.

**Recipe B — TS (AAC) → MP4:**

```bash
ffmpeg -i in.ts -c copy -bsf:a aac_adtstoasc out.mp4
```

**Unlike the video bsf, ffmpeg does NOT always auto-insert `aac_adtstoasc`.** Always
pass it when targeting MP4 from a TS/FLV/raw-AAC source.

**Recipe C — HLS segment with keyframe-carried extradata (mid-segment joinable):**

```bash
ffmpeg -i in.mp4 -c copy \
  -bsf:v "h264_mp4toannexb,dump_extra=freq=k" \
  -f mpegts segment.ts
```

Chain multiple bsf with a **comma** inside the same `-bsf:v` argument.

**Recipe D — Fix packed B-frames in old DivX/XviD MP4s:**

```bash
ffmpeg -i old.avi -c copy -bsf:v mpeg4_unpack_bframes -f mp4 fixed.mp4
```

Symptom you're fixing: player shows "warning: Invalid and inefficient vfw-avi packed
B-frames detected" or every other frame is black.

**Recipe E — Rewrite H.264 metadata (level, VUI, SAR) in place:**

```bash
# Claim Level 4.1 so a hardware decoder that refuses 4.2 will accept it:
ffmpeg -i in.mp4 -c copy -bsf:v "h264_metadata=level=4.1" out.mp4

# Tag BT.709 color primaries + transfer + matrix (HD):
ffmpeg -i in.mp4 -c copy \
  -bsf:v "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1" \
  tagged.mp4

# Fix square-pixel signalling (SAR 1:1):
ffmpeg -i in.mp4 -c copy -bsf:v "h264_metadata=sample_aspect_ratio=1/1" out.mp4
```

HEVC/AV1 equivalents: `hevc_metadata=...`, `av1_metadata=...`. Same field names.

**Recipe F — Strip NAL unit types (SEI, AUD, filler):**

```bash
# H.264: strip SEI (type 6) — fixes some broadcast players that choke on timecode SEI:
ffmpeg -i in.mp4 -c copy -bsf:v "filter_units=remove_types=6" out.mp4

# Strip SEI + AUD + filler:
ffmpeg -i in.mp4 -c copy -bsf:v "filter_units=remove_types=6|9|12" out.mp4
```

H.264 NAL types you care about: `5`=IDR, `6`=SEI, `7`=SPS, `8`=PPS, `9`=AUD, `12`=filler.
HEVC types live in a different range — see `references/filters.md`.

**Recipe G — Zero-base timestamps:**

```bash
# Reset PTS/DTS so the file starts at 0, preserving spacing:
ffmpeg -i in.mp4 -c copy \
  -bsf:v "setts=ts=PTS-STARTPTS" \
  -bsf:a "setts=ts=PTS-STARTPTS" \
  zeroed.mp4

# Offset video by +2s (shift audio-video sync):
ffmpeg -i in.mp4 -c copy -bsf:v "setts=ts=PTS+2/TB" out.mp4
```

Remember: `setts` expressions run in the **packet timebase** — multiply seconds by
`1/TB` (or equivalently, divide by `TB`).

**Recipe H — Extract SPS/PPS (extradata) as side-data:**

```bash
ffmpeg -i in.mp4 -c:v copy -bsf:v extract_extradata -f null -
# Combined with ffprobe -show_packets -show_data to read the side-data bytes.
```

For most practical needs use `ffprobe` directly — `extract_extradata` is mostly a
building block for piping to another tool.

**Recipe I — MJPEG video stream → individual JPEG files:**

```bash
ffmpeg -i in.avi -c:v copy -bsf:v mjpeg2jpeg frame_%04d.jpg
```

**Recipe J — Debug / inspect headers:**

```bash
ffmpeg -i in.mp4 -c:v copy -bsf:v trace_headers -f null - 2>&1 | less
```

Dumps every SPS / PPS / slice header field in human-readable form. Needs a build with
CBS (coded-bitstream) support — almost every modern ffmpeg has it.

## Step 4 — Verify

```bash
# Container + streams sane:
ffprobe -v error -show_streams -show_format -of json "$OUT"

# For MP4-from-TS: confirm moov atom is present and AAC audio decodes:
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels "$OUT"

# For TS-from-MP4: confirm packets are Annex-B — first video packet should start 0x00 0x00 0x00 0x01:
ffmpeg -i "$OUT" -map 0:v:0 -c copy -f h264 - 2>/dev/null | xxd | head -1
#                                       ^^^ raw Annex-B H.264
```

Playback test: open in VLC or `ffplay`. A bad bsf → corrupt / garbled video but valid
container structure (ffprobe will say "OK", playback will say "no").

## Available scripts

- **`scripts/bsf.py`** — subcommand-driven runner for the common bsf tasks
  (mp4-to-ts, ts-to-mp4, fix-packed-bframes, level, strip-sei, trace, zero-ts). Auto-detects
  H.264 vs HEVC via `ffprobe` and picks the matching `*_mp4toannexb` filter.

## Workflow

```bash
# Convert MP4 to TS (auto-detects codec):
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py mp4-to-ts --input in.mp4 --output out.ts

# Convert TS to MP4 with aac_adtstoasc:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py ts-to-mp4 --input in.ts --output out.mp4

# Fix packed B-frames:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py fix-packed-bframes --input old.avi --output fixed.mp4

# Rewrite H.264 level to 4.1:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py level --input in.mp4 --output out.mp4 --level 4.1

# Strip SEI:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py strip-sei --input in.mp4 --output out.mp4

# Zero-base PTS/DTS on both streams:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py zero-ts --input in.mp4 --output out.mp4

# Dump headers:
uv run ${CLAUDE_SKILL_DIR}/scripts/bsf.py trace --input in.mp4 --stream v:0
```

All subcommands accept `--dry-run` (print the command, do not run) and `--verbose`
(pass `-loglevel info` to ffmpeg).

## Reference docs

- Read [`references/filters.md`](references/filters.md) for: the full bsf reference
  table, codec ↔ bsf matrix, container-conversion cheat-sheet, H.264 / HEVC NAL-unit
  type numbers, `setts` expression grammar, and the full option catalog for
  `h264_metadata` / `hevc_metadata` / `av1_metadata` / `filter_units`.

## Gotchas

- **bsf only works with `-c copy`.** Any re-encode path rewrites extradata itself and
  silently ignores the bsf. If your level-rewrite doesn't "stick", check you didn't
  accidentally pass `-c:v libx264`.
- **Applying `h264_mp4toannexb` to an already-Annex-B stream** used to corrupt output;
  ffmpeg 4.x+ auto-detects framing and becomes a no-op, but explicitly doing so on
  older builds is a footgun. When in doubt, probe source container first.
- **MP4 → TS/HLS may be auto-handled.** Modern ffmpeg inserts `h264_mp4toannexb` /
  `hevc_mp4toannexb` automatically when the mpegts muxer sees AVCC input. Explicit is
  still safer for older builds and scripting reproducibility.
- **TS AAC → MP4 is NOT auto-handled.** `aac_adtstoasc` must be passed explicitly in
  most builds — otherwise you get `Malformed AAC bitstream detected` or silent
  unplayable audio in the MP4.
- **`dump_extra=freq=k` slightly inflates bitrate** (SPS+PPS are tens of bytes per IDR),
  but it's what makes HLS / live segments joinable mid-stream.
- **`filter_units=remove_types=` takes NAL unit type NUMBERS, not names.** See
  `references/filters.md` for the table. Multiple types are `|`-separated.
- **`h264_metadata` only works on H.264 streams** — not HEVC, not AV1. Use the matching
  `hevc_metadata` / `av1_metadata` filter.
- **Chain multiple bsf with comma** inside the same `-bsf:v` flag:
  `-bsf:v "h264_mp4toannexb,dump_extra=freq=k"`. Order matters — framing conversion first,
  then extradata manipulation, then metadata rewrite.
- **bsf argument syntax** uses `=` to separate the filter name from options, and `:`
  between options — always quote: `-bsf:v "h264_metadata=level=4.1:aud=insert"`.
- **Stream specifiers matter:** `-bsf:v` targets video streams, `-bsf:a` audio,
  `-bsf:s` subtitles. Use `-bsf:v:0` to target only the first video stream in a
  multi-stream file.
- **`setts` expressions run in packet timebase, NOT seconds.** To add 2 seconds use
  `ts=PTS+2/TB`, not `ts=PTS+2`. Use `ffprobe -show_streams | grep time_base` if unsure.
- **`trace_headers` requires CBS support** compiled into your ffmpeg build. Homebrew,
  Debian, and static builds from johnvansickle all ship it; some minimal stripped
  builds don't.
- **`noise` is destructive** — intended for robustness testing of decoders, not for
  production use.
- **`mpeg4_unpack_bframes` is safe on non-packed MP4s.** It detects the absence of
  packed B-frames and passes through untouched, so it's cheap to apply prophylactically
  when batch-normalising old video libraries.

## Examples

### Example 1: Recorded `.ts` won't mux to `.mp4` ("Malformed AAC bitstream")

```bash
ffmpeg -i recording.ts -c copy -bsf:a aac_adtstoasc recording.mp4
```

### Example 2: Convert MP4 to HLS segments joinable mid-stream

```bash
ffmpeg -i movie.mp4 -c copy \
  -bsf:v "h264_mp4toannexb,dump_extra=freq=k" \
  -f hls -hls_time 6 -hls_segment_type mpegts out.m3u8
```

### Example 3: Old DivX AVI has packed B-frames, fix without re-encoding

```bash
ffmpeg -i old_divx.avi -c copy -bsf:v mpeg4_unpack_bframes -f mp4 fixed.mp4
```

### Example 4: Claim lower H.264 Level for a picky hardware decoder

```bash
ffmpeg -i in.mp4 -c copy -bsf:v "h264_metadata=level=4.0" decoderfriendly.mp4
```

### Example 5: Strip all SEI (timecode / closed-captions metadata) NAL units

```bash
ffmpeg -i in.mp4 -c copy -bsf:v "filter_units=remove_types=6" stripped.mp4
```

### Example 6: Zero-base PTS/DTS on a trimmed clip

```bash
ffmpeg -ss 00:01:30 -i src.mp4 -c copy -t 30 \
  -bsf:v "setts=ts=PTS-STARTPTS" -bsf:a "setts=ts=PTS-STARTPTS" \
  clip.mp4
```

## Troubleshooting

### Error: `Malformed AAC bitstream detected: use the audio bitstream filter 'aac_adtstoasc'`

Cause: muxing ADTS AAC (TS/FLV source) into MP4 without the bsf.
Solution: `-bsf:a aac_adtstoasc`.

### Error: `H.264 bitstream malformed, no startcode found, use the video bitstream filter 'h264_mp4toannexb'`

Cause: copying AVCC-framed H.264 from MP4 into TS/FLV without converting framing.
Solution: `-bsf:v h264_mp4toannexb`.

### Error: `Bitstream filter 'h264_metadata' not found`

Cause: your ffmpeg build was compiled without CBS support (rare — check `ffmpeg -bsfs`).
Solution: install a standard build (Homebrew / static `johnvansickle` / Debian `ffmpeg`).

### Output has visual glitches after applying `h264_mp4toannexb`

Cause: source was already Annex-B (e.g. `.ts`), filter applied to already-converted stream.
Solution: probe source container first. On modern ffmpeg the filter no-ops safely, but
you may be on an older build — remove the flag when source is `.ts` / `.flv`.

### `-bsf:v` appears to do nothing (e.g. level stays the same)

Cause: an `-c:v ...` re-encoder is active and overriding extradata.
Solution: use `-c copy` (or `-c:v copy`). bsf only runs on copied streams.

### `filter_units=remove_types=` drops too much / too little

Cause: passing a type name instead of the numeric type, or using H.264 numbers against
HEVC (type spaces are different).
Solution: check `references/filters.md` for the type tables.

### `setts` produces out-of-order DTS

Cause: expression doesn't preserve the DTS ≤ PTS invariant.
Solution: rewrite both — `setts=pts=PTS-STARTPTS:dts=DTS-STARTDTS` — and avoid
expressions that can push DTS past PTS on B-frame streams.
