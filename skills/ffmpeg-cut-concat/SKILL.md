---
name: ffmpeg-cut-concat
description: >
  Trim, cut, split, segment, and concatenate media with ffmpeg (stream copy when possible, re-encode across cut boundaries). Use when the user asks to trim a video, cut a clip, extract a segment by timestamps, remove a section, split into parts, join/merge videos, concatenate files, or build a segmented HLS-style playlist.
argument-hint: "[action] [input]"
---

# Ffmpeg Cut Concat

**Context:** $ARGUMENTS

## Quick start

- **Fast trim (keyframe-aligned):** → Step 1 → trim mode with `-c copy`
- **Frame-accurate trim:** → Step 1 → trim mode, re-encode (`--accurate`)
- **Split one file into N pieces:** → Step 1 → segment mode
- **Join same-codec files:** → Step 1 → concat-copy mode
- **Join different-codec files:** → Step 1 → concat-filter mode

## When to use

- Extracting a clip between two timestamps (e.g. `00:01:30` to `00:02:00`).
- Splitting a long file into N-second chunks (podcast, HLS prep).
- Joining multiple recordings end-to-end.
- Removing the first/last N seconds of a video.
- Building a highlight reel from several source files.

## Step 1 — Pick a strategy

| Goal | Mode | Command skeleton |
|---|---|---|
| Trim one clip from one file | `trim` | `ffmpeg -ss T1 -i in -to T2 -c copy out` |
| Split one file into equal pieces | `segment` | `ffmpeg -i in -f segment -segment_time N out_%03d.mp4` |
| Join files with identical codecs | `concat-copy` | `ffmpeg -f concat -safe 0 -i list.txt -c copy out` |
| Join files with mismatched codecs | `concat-filter` | `-filter_complex "concat=n=N:v=1:a=1"` |

Do not use concat demuxer for files that differ in codec, resolution, SAR, fps, or sample rate — it will mux them but playback breaks silently. Use the concat filter instead.

## Step 2 — Decide stream copy vs re-encode

- **Stream copy (`-c copy`)** is ~100x faster and lossless, but cuts land on the nearest keyframe before the requested timestamp. A clip asked for at `00:01:30.000` may actually start at `00:01:28.5`.
- **Re-encode** (drop `-c copy`, add `-c:v libx264 -c:a aac`) is frame-accurate but slow and lossy.
- **Default rule:** start with `-c copy`; switch to re-encode only when the user says "frame-accurate," "exact," or the first frame looks wrong after a test.

Input-side vs output-side seek:

- `-ss T -i in.mp4` (before `-i`) — input seek. Fast; ffmpeg seeks in the container to the keyframe at or before T, then starts decoding. With `-c copy`, output begins at that keyframe.
- `-i in.mp4 -ss T` (after `-i`) — output seek. Decodes from the start, discards frames until T. Slow but accurate. Rarely needed since modern ffmpeg does accurate input seek by default with `-accurate_seek`.

For accurate cut with re-encode, use input seek too — it is fast AND accurate once decoding is on.

## Step 3 — Run the command

### 3a. Trim (stream copy, keyframe-aligned)

```bash
ffmpeg -ss 00:01:30 -i input.mp4 -to 00:02:00 -c copy -avoid_negative_ts make_zero out.mp4
```

`-to` is absolute input-time. If you wrote `-ss 00:01:30 -to 00:02:00`, you get 30 seconds out.

Use `-t 30` instead of `-to` to specify duration directly (`-t` wins if both set).

### 3b. Trim (frame-accurate, re-encode)

```bash
ffmpeg -ss 00:01:30 -i input.mp4 -to 00:02:00 \
  -c:v libx264 -crf 18 -preset veryfast \
  -c:a aac -b:a 192k \
  out.mp4
```

### 3c. Segment (split into N-second pieces)

```bash
ffmpeg -i input.mp4 -c copy -map 0 \
  -f segment -segment_time 60 -reset_timestamps 1 \
  out_%03d.mp4
```

Segments still break on keyframes. If you need exact 60.000s pieces, re-encode with forced keyframes: `-force_key_frames "expr:gte(t,n_forced*60)"`.

### 3d. Concat demuxer (same codec params)

Create `list.txt`:

```
file 'clip1.mp4'
file 'clip2.mp4'
file 'clip3.mp4'
```

Run:

```bash
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4
```

`-safe 0` allows absolute paths and `..` — needed for anything except plain filenames in CWD.

### 3e. Concat filter (different codecs / resolutions)

```bash
ffmpeg -i a.mp4 -i b.mp4 -i c.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -c:a aac -b:a 192k \
  out.mp4
```

Each input contributes `v` video streams and `a` audio streams — reference them in order `[i:v][i:a]` for `i=0..n-1`.

## Step 4 — Verify duration

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 out.mp4
```

For stream copy, the reported duration may be a bit shorter or longer than requested due to keyframe alignment. If the discrepancy is more than ~2s, your GOP size is large — re-encode.

## Available scripts

- **`scripts/cut.py`** — single entrypoint for all four modes (`trim`, `segment`, `concat-copy`, `concat-filter`) with `--dry-run` and `--verbose`.

## Workflow

```bash
# Fast trim
uv run ${CLAUDE_SKILL_DIR}/scripts/cut.py trim \
  --input in.mp4 --start 00:01:30 --end 00:02:00 --output clip.mp4

# Frame-accurate
uv run ${CLAUDE_SKILL_DIR}/scripts/cut.py trim \
  --input in.mp4 --start 00:01:30 --end 00:02:00 --accurate --output clip.mp4

# Split into 60s chunks
uv run ${CLAUDE_SKILL_DIR}/scripts/cut.py segment \
  --input in.mp4 --seconds 60 --pattern out_%03d.mp4

# Concat same-codec files
uv run ${CLAUDE_SKILL_DIR}/scripts/cut.py concat-copy \
  --inputs a.mp4 b.mp4 c.mp4 --output joined.mp4

# Concat mixed-codec files (re-encodes)
uv run ${CLAUDE_SKILL_DIR}/scripts/cut.py concat-filter \
  --inputs a.mp4 b.webm --output joined.mp4
```

## Reference docs

- Read [`references/patterns.md`](references/patterns.md) for exact `list.txt` escaping rules, the two-pass `-ss` recipe, `-copyts` muxing-accurate cuts, and keyframe inspection via ffprobe.

## Gotchas

- **Concat demuxer is silent about mismatches.** Files MUST have identical codec, resolution, SAR, pixel format, fps, sample rate, and channel layout. Otherwise the output plays wrong (frozen video, desync audio) with zero warnings. Probe first: `ffprobe -v error -show_streams a.mp4 b.mp4` and diff the codec/fps/sar fields.
- **`-safe 0` is required** for concat list entries with absolute paths or `..`. Without it you get `Unsafe file name`.
- **Single-quote escaping in list.txt.** Each path is wrapped in `'...'`. To include a literal `'`, close the quote, backslash-escape, reopen: `file 'it'\''s.mp4'`.
- **Input seek + `-c copy` can produce negative timestamps.** The first packet's PTS may be earlier than the cut point. Add `-avoid_negative_ts make_zero` or players may show a blank first second.
- **Stream-copy trim starts on a keyframe.** If you asked for `00:01:30` but the nearest prior keyframe is at `00:01:28.5`, the output starts at `00:01:28.5`. To snap exactly, re-encode.
- **`-to` is absolute, `-t` is duration.** `-ss 60 -to 90` = 30s clip. `-ss 60 -t 90` = 90s clip. Mixing them confuses people who memorized one form.
- **Concat filter requires matching stream counts per input.** `concat=n=3:v=1:a=1` expects `[0:v][0:a][1:v][1:a][2:v][2:a]`. A silent input needs a dummy `anullsrc` or a=0.
- **Lossless cuts only work at keyframes.** Run `ffprobe -select_streams v -show_frames -skip_frame nokey -show_entries frame=pkt_pts_time` to find them.
- **`-ss` position before `-i` on some formats (especially raw/TS)** seeks inaccurately. If the clip starts in the wrong place, move `-ss` after `-i` to force decode-based seek.

## Examples

### Example 1: cut a 30s clip, fast

```bash
ffmpeg -ss 00:01:30 -i lecture.mp4 -to 00:02:00 \
  -c copy -avoid_negative_ts make_zero \
  highlight.mp4
```

### Example 2: remove first 10 seconds, frame-accurate

```bash
ffmpeg -ss 10 -i raw.mov \
  -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 192k \
  trimmed.mp4
```

### Example 3: split a podcast into 10-minute chunks

```bash
ffmpeg -i podcast.m4a -c copy -f segment -segment_time 600 \
  -reset_timestamps 1 part_%02d.m4a
```

### Example 4: join three identical-format clips

```bash
cat > list.txt <<'EOF'
file 'intro.mp4'
file 'main.mp4'
file 'outro.mp4'
EOF
ffmpeg -f concat -safe 0 -i list.txt -c copy final.mp4
```

### Example 5: merge a 1080p mp4 and a 720p webm

```bash
ffmpeg -i a.mp4 -i b.webm \
  -filter_complex "[0:v]scale=1280:720,setsar=1[v0];[1:v]setsar=1[v1];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 20 -c:a aac mix.mp4
```

## Troubleshooting

### Error: `Unsafe file name`

**Cause:** concat demuxer refusing a path outside CWD without `-safe 0`.
**Solution:** add `-safe 0` before `-i list.txt`, or use filenames relative to CWD.

### Output starts before the requested `-ss`, or has a black first frame

**Cause:** keyframe alignment with `-c copy` + negative initial PTS.
**Solution:** add `-avoid_negative_ts make_zero`. For exact start, drop `-c copy` and re-encode.

### Concat demuxer output has frozen video or audio desync

**Cause:** input files differ in codec/resolution/fps/sar/sample rate.
**Solution:** probe them (`ffprobe -show_streams`), confirm mismatch, switch to concat filter with re-encode, or normalize inputs first with `-c:v libx264 -vf "scale=W:H,fps=F,setsar=1" -ar 48000 -ac 2`.

### `Stream specifier ':a' matches no streams`

**Cause:** one input has no audio track, but your concat filter expects `a=1`.
**Solution:** either generate silence (`-f lavfi -i anullsrc=cl=stereo:r=48000`) for that input, or set `a=0` and handle audio separately.

### Segments are uneven lengths despite `-segment_time 60`

**Cause:** segmenter only breaks at keyframes; your GOP is longer than 60s or irregular.
**Solution:** re-encode with `-force_key_frames "expr:gte(t,n_forced*60)"` before segmenting (or in the same pass).

### `[concat @ ...] DTS ... < ... out of order`

**Cause:** overlapping or decreasing timestamps when concatenating.
**Solution:** add `-fflags +genpts` before `-i list.txt`, or re-mux each input through `-c copy` first to normalize timestamps.
