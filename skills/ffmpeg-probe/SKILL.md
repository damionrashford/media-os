---
name: ffmpeg-probe
description: >
  Inspect media files with ffprobe: format, streams, codecs, duration, bitrate, resolution, fps, color space, channel layout, metadata, chapters, and per-frame/packet analysis, output as JSON/CSV/INI/XML. Use when the user asks to inspect a video, check codec, get resolution/bitrate/fps/duration, detect HDR, list streams/tracks, dump metadata, count frames, find keyframes, get container info, or pipe media info into a pipeline.
argument-hint: "[input] [fields]"
---

# Ffmpeg Probe

**Context:** $ARGUMENTS

## Quick start

- **Everything, JSON:** `ffprobe -v error -show_format -show_streams -of json in.mp4` → Step 1
- **Single field (duration / fps / resolution / codec):** → Step 3, one-liners
- **Keyframes / chapters / metadata:** → Step 1 (pick section)
- **HDR detection:** → Step 3, HDR recipe
- **Python helper w/ subcommands:** `uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py summary --input in.mp4`

## When to use

- User says "inspect", "what codec is this", "how long", "what resolution",
  "is it HDR", "get the bitrate", "dump metadata", "list tracks".
- You need **machine-readable** media info for a downstream step
  (e.g. before transcoding, cutting, or streaming).
- For playback/preview use `ffmpeg-playback`; for transcoding use `ffmpeg-transcode`;
  for raw extradata/bitstream inspection use `ffmpeg-bitstream`.

## Step 1 — Pick what to dump

ffprobe organises output into sections. Combine as many `-show_*` flags as needed:

| Flag                  | Contents                                                  | Size   |
|-----------------------|-----------------------------------------------------------|--------|
| `-show_format`        | Container: filename, duration, size, bit_rate, tags       | small  |
| `-show_streams`       | Per-stream: codec, resolution, fps, channels, color, tags | small  |
| `-show_chapters`      | Chapter list with start/end times and titles              | small  |
| `-show_programs`      | MPEG-TS programs (broadcast / multi-program streams)      | small  |
| `-show_frames`        | Every decoded frame (`pict_type`, `pts`, `key_frame`, …)  | HUGE   |
| `-show_packets`       | Every packet (`pts`, `dts`, `size`, `flags`)              | HUGE   |
| `-show_entries K=V,…` | Whitelist specific sections/fields (see `references/queries.md`) | small  |
| `-show_error`         | Structured error if demuxing fails                        | tiny   |

For `-show_frames` / `-show_packets`, **always** combine with either
`-select_streams` and/or `-read_intervals` to bound the output:

```bash
ffprobe -v error -select_streams v:0 -read_intervals "%+#20" -show_frames -of json in.mp4
# reads the first 20 packets of v:0 (the `%+#N` form = first N packets)
```

## Step 2 — Pick output format

| `-of` value                            | Use case                                         |
|----------------------------------------|--------------------------------------------------|
| `default`                              | Human-ish, `section.key=value` lines             |
| `default=noprint_wrappers=1:nokey=1`   | Bare value(s), one per line — great for shell    |
| `json`                                 | Scripts / `jq` / the bundled `probe.py`          |
| `csv=p=0`                              | Spreadsheet; `p=0` strips the section name       |
| `csv=s=x:p=0`                          | Use `x` as separator (e.g. `1920x1080`)          |
| `flat`                                 | `streams.stream.0.width=1920` — easy to `grep`   |
| `ini`                                  | INI sections per stream                          |
| `xml`                                  | XML (pair with `-x` pretty-print)                |

**Rule of thumb:** `json` for automation, `default=…nokey=1` for shell
one-liners, `csv` when you want to paste into a sheet.

## Step 3 — Run it (recipes)

**Full dump, JSON (the default starting point):**
```bash
ffprobe -v error -show_format -show_streams -of json in.mp4
```

**Duration in seconds (float):**
```bash
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 in.mp4
```

**Resolution as `1920x1080`:**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height -of csv=s=x:p=0 in.mp4
```

**FPS as a fraction (`30000/1001`, `25/1`, …):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
```
Parse the fraction yourself — it is *not* a float. See Gotchas.

**Codec name (video / audio):**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
```

**Bitrate (stream level first, then container fallback):**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
# fallback if "N/A":
ffprobe -v error -show_entries format=bit_rate \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
```

**Audio channel layout / channel count / sample rate:**
```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=channel_layout,channels,sample_rate \
  -of default=noprint_wrappers=1 in.mp4
```

**Color info (for HDR / BT.2020 / BT.709 classification):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_space,color_primaries,color_transfer,color_range,pix_fmt \
  -of json in.mp4
```

**HDR detection (full recipe):**
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_transfer,color_primaries,color_space:stream_side_data_list \
  -of json in.mp4
```
Classify:
- `color_transfer=smpte2084` + `color_primaries=bt2020` → **HDR10** (also check
  `mastering_display_metadata` / `content_light_level` in `side_data_list` for HDR10).
- `color_transfer=arib-std-b67` → **HLG**.
- `side_data_type="DOVI configuration record"` → **Dolby Vision**.
- Otherwise → **SDR** (usually `bt709`).

**Frame count (exact — SLOW, decodes whole stream):**
```bash
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames -of csv=p=0 in.mp4
```
Prefer the fast path first:
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames \
  -of default=nokey=1:noprint_wrappers=1 in.mp4
# "N/A" → fall back to -count_frames, or compute duration * fps.
```

**Keyframe timestamps:**
```bash
ffprobe -v error -select_streams v:0 -show_frames \
  -show_entries frame=pkt_pts_time,pict_type \
  -of csv=p=0 in.mp4 | awk -F, '$2=="I" {print $1}'
```

**All packets (use intervals — raw `-show_packets` is huge):**
```bash
ffprobe -v error -select_streams v:0 -read_intervals "10%+30" \
  -show_packets -of json in.mp4
# reads 30 seconds starting 10% into the file
```

**Chapters:**
```bash
ffprobe -v error -show_chapters -of json in.mkv
```

**Metadata tags (format + per-stream):**
```bash
ffprobe -v error -show_entries format_tags:stream_tags -of json in.mp4
```

## Available scripts

- **`scripts/probe.py`** — stdlib-only wrapper. Subcommands:
  - `summary --input I` — human-readable container / V / A summary.
  - `json --input I` — full `-show_format -show_streams` JSON to stdout.
  - `field --input I --query KEY` — dotted path: `format.duration`,
    `stream.v.width`, `stream.v.fps`, `stream.a.channels`, …
  - `keyframes --input I` — keyframe PTS times, one per line.
  - `hdr --input I` — prints one of `SDR`, `HDR10`, `HLG`, `DolbyVision`.
  - `compare --inputs A.mp4 B.mp4` — side-by-side field diff.
  - Every subcommand supports `--verbose` and `--dry-run` (prints the underlying
    `ffprobe` command instead of executing).

## Workflow

```bash
# Quick human summary:
uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py summary --input in.mp4

# One field for a shell variable:
FPS=$(uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py field --input in.mp4 --query stream.v.fps)

# HDR class:
uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py hdr --input in.mp4
```

## Reference docs

- Read [`references/queries.md`](references/queries.md) for the full
  `-show_entries` field table, stream-specifier syntax, output-format cheat
  sheet, an HDR detection flowchart, timebase math, and a 30+ one-liner library.

## Gotchas

- **`r_frame_rate` is a FRACTION** (`30000/1001`, `24000/1001`, `25/1`), not a
  float. Always parse `num/den`. `probe.py` does this; raw shell consumers must too.
- **`avg_frame_rate` ≠ `r_frame_rate` on VFR content.** `r_frame_rate` is the
  lowest framerate that exactly describes every timestamp (effectively "base"
  rate); `avg_frame_rate` = total frames / duration. For CFR they match; for
  VFR use `avg_frame_rate` for "how many FPS on average", `r_frame_rate` for
  "what does each timestamp snap to".
- **`-count_frames` decodes the whole stream.** Slow on long videos. Prefer
  `stream=nb_frames` first; most MP4/MOV muxers write it. MKV usually does not.
- **`bit_rate` at stream level is often `N/A`** for streams inside MKV/WebM and
  some fragmented MP4s. Fall back to `format.bit_rate`, or compute
  `file_size * 8 / duration`.
- **Use `-v error`** to silence stderr noise when piping (otherwise ffprobe
  prints banner + build info to stderr and callers assume it failed).
- **Stream specifier `v:0` picks the first video stream** — after
  `-select_streams`, the remaining stream's original `index` is still in its
  JSON, but counting positions in the filtered output is different. Always
  identify streams by `index`, not by position.
- **Packet/frame timestamps are in timebase units.** Seconds =
  `pts * time_base.num / time_base.den`. ffprobe exposes `*_time` convenience
  fields (`pkt_pts_time`, `best_effort_timestamp_time`) already in seconds —
  prefer those.
- **`-read_intervals "10%+30"`** = start at 10% of duration, read 30 seconds.
  `"%+#20"` = from start, 20 packets. Great for sampling huge files without
  dumping gigabytes of JSON.
- **`side_data_list`** (a.k.a. `-show_entries stream_side_data_list`) is where
  HDR10 mastering display, content light level, Dolby Vision config, and
  stereoscopic 3D layout live. Not in the main stream dict.
- **Raw files** (headerless YUV/PCM) need explicit demuxer hints:
  `ffprobe -f rawvideo -video_size 1920x1080 -pix_fmt yuv420p -framerate 24 in.yuv`.
- **`-show_entries` section syntax uses `:` between sections, `,` between
  fields:** `-show_entries format=duration:stream=codec_name,bit_rate`.
- **`-of json` is nested**: `{"streams":[{...}], "format":{...}}`. Flatten with
  `jq` or `-of flat` if you need grep-friendly output.
- **"N/A"** is a literal string, not null — parsers must coerce.
- **`-hide_banner` is implied** when `-v error` is set, but set both to be safe
  across ffmpeg versions.

## Examples

### Example 1: "What's the resolution and fps of this mp4?"

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -of csv=p=0 in.mp4
# -> 1920,1080,30000/1001
```

### Example 2: "Is this file HDR?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py hdr --input in.mp4
# -> HDR10
```

### Example 3: "Get duration in seconds into a shell variable"

```bash
DUR=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 in.mp4)
echo "$DUR"    # 128.458667
```

### Example 4: "Dump all keyframe timestamps to a file"

```bash
ffprobe -v error -select_streams v:0 -show_frames \
  -show_entries frame=pkt_pts_time,pict_type \
  -of csv=p=0 in.mp4 | awk -F, '$2=="I"{print $1}' > keyframes.txt
```

### Example 5: "Compare two encodes"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/probe.py compare --inputs orig.mp4 encoded.mp4
```

## Troubleshooting

### Error: `Invalid data found when processing input`

Cause: file is truncated, or container is wrong (e.g. `.mp4` is actually a `.ts`).
Solution: try `ffprobe -v error -show_format file` (no `-show_streams`) to see
the detected `format_name`. If it's `mpegts`, treat as `.ts`. If ffprobe still
fails, the file is likely corrupt — try `ffmpeg -err_detect ignore_err -i …`.

### `bit_rate=N/A` on every stream

Cause: muxer didn't write per-stream bitrate (common in MKV, WebM, fragmented MP4).
Solution: use `format.bit_rate`, or compute `size_bytes * 8 / duration_seconds`
from `-show_entries format=size,duration`.

### `r_frame_rate=0/0`

Cause: codec/container has no concept of a frame rate (image, some audio-only
containers probed for a non-existent video stream).
Solution: guard against `num==0 || den==0` in parsers; skip fps reporting.

### `nb_frames=N/A` but I need an exact count

Cause: muxer doesn't store it. Solution: either compute
`duration * avg_frame_rate` (approximate, fine for CFR) or use `-count_frames`
(slow, exact).

### Output is truncated / stops mid-JSON

Cause: you hit a pipe or buffer limit dumping `-show_frames` / `-show_packets`
on a long file.
Solution: always scope with `-select_streams` + `-read_intervals`; stream JSON
to a file with `>` rather than piping through an aggressive consumer.

### `Option not found` for `-show_entries`

Cause: very old ffprobe (< 1.0). Solution: upgrade; on macOS
`brew install ffmpeg`.
