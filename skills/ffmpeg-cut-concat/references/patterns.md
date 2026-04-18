# Cut / Concat patterns

Deeper reference material. The main `SKILL.md` covers the common cases; reach
for this file when the basic recipes are not enough.

## Scenario -> mode -> command template

| Scenario | Mode | Command template |
|---|---|---|
| Fast trim, don't care if start is ~1s early | trim (copy) | `ffmpeg -ss T1 -i in -to T2 -c copy -avoid_negative_ts make_zero out` |
| Frame-accurate trim | trim (re-encode) | `ffmpeg -ss T1 -i in -to T2 -c:v libx264 -crf 18 -c:a aac out` |
| Frame-accurate + long file (fast seek, exact cut) | two-pass `-ss` | see "Frame-accurate via double -ss" below |
| Remove last N seconds | trim (copy) | `ffmpeg -i in -t $(DURATION-N) -c copy out` |
| Split into N-second pieces | segment | `ffmpeg -i in -c copy -f segment -segment_time N -reset_timestamps 1 out_%03d.mp4` |
| Split on exact seconds (re-encode) | segment + force_key_frames | `ffmpeg -i in -force_key_frames "expr:gte(t,n_forced*N)" -c:v libx264 -c:a aac -f segment -segment_time N out_%03d.mp4` |
| Join same-codec files | concat-copy | `ffmpeg -f concat -safe 0 -i list.txt -c copy out` |
| Join mismatched files | concat-filter | `-filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]"` |
| Join and keep as many streams as possible | concat-copy + pre-normalize | transcode inputs to same codec first, then concat-copy |
| Extract slice from network URL | concat demuxer inpoint/outpoint | see "Concat demuxer with inpoint/outpoint" below |

## Concat demuxer list.txt — exact syntax

Minimum viable form (files in CWD):

```
file 'clip1.mp4'
file 'clip2.mp4'
```

With absolute paths or paths containing spaces — still single-quoted:

```
file '/Users/me/Movies/part one.mp4'
file '/Users/me/Movies/part two.mp4'
```

Escaping a literal `'` in a filename. Close the quote, backslash-escape, reopen:

```
# Filename:  it's-a-test.mp4
file 'it'\''s-a-test.mp4'
```

Optional header for auto-detection (lets `ffmpeg -i list.txt` work without `-f concat`):

```
ffconcat version 1.0
file 'a.mp4'
file 'b.mp4'
```

Per-entry directives (after a `file` line they apply to that file):

```
file 'a.mp4'
inpoint 5.0          # start demuxing this file at 5.0s
outpoint 15.0        # stop at 15.0s
duration 10.0        # hint for efficient seeking / blank inputs
```

Always pass `-safe 0` when using absolute paths or anything with `..`:

```
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4
```

For HTTP/HTTPS inputs, also whitelist the protocols:

```
ffmpeg -protocol_whitelist file,http,https,tcp,tls -f concat -safe 0 -i list.txt -c copy out.mp4
```

## Concat demuxer with inpoint/outpoint

Useful for slicing clips from larger files without remuxing each one first:

```
ffconcat version 1.0
file 'big1.mp4'
inpoint 60
outpoint 90
file 'big2.mp4'
inpoint 0
outpoint 30
```

Then:

```bash
ffmpeg -f concat -safe 0 -i list.txt -c copy highlights.mp4
```

Caveat: still keyframe-aligned with `-c copy`. For exact times, re-encode.

## Frame-accurate via double `-ss`

Classic recipe: coarse input seek (fast) to near the cut point, then fine
output seek (accurate). Rarely needed on modern ffmpeg (accurate_seek is on by
default) but the technique remains useful when a format's index is unreliable:

```bash
# Cut 00:05:30 -> 00:05:40, decode starts 5s early for safety
ffmpeg -ss 00:05:25 -i input.mp4 -ss 5 -t 10 \
  -c:v libx264 -crf 18 -c:a aac out.mp4
```

The first `-ss` (before `-i`) lands on the keyframe at or before 5:25; the
second `-ss` (after `-i`) discards decoded frames until t=5s relative to the
first seek, giving a cut that starts at 5:30 exactly.

## Muxing-accurate cuts (preserve original timestamps)

When another tool downstream needs timestamps from the source file (e.g. DASH
packaging, subtitle sync, splicing back in), cut with:

```bash
ffmpeg -ss 60 -to 90 -i input.mp4 \
  -c copy \
  -copyts -start_at_zero \
  -muxpreload 0 -muxdelay 0 \
  out.mp4
```

- `-copyts` keeps source timestamps instead of rebasing to zero.
- `-start_at_zero` shifts the first output packet to t=0 while preserving
  relative offsets between streams (prevents leading silence when audio
  and video keyframes don't align).
- `-muxpreload 0 -muxdelay 0` strips the small pre-roll the MP4 muxer
  adds by default.

## Lossless GOP-aligned cut detection

Find the closest preceding keyframe for a target timestamp before cutting,
so you know if `-c copy` will land on the right spot:

```bash
# List all video keyframes as pkt_pts_time
ffprobe -v error -select_streams v:0 \
  -skip_frame nokey -show_frames \
  -show_entries frame=pkt_pts_time \
  -of csv=p=0 input.mp4
```

Pick the largest value <= your desired start; that is what `-c copy` will
actually produce. If the gap is unacceptable, re-encode or re-encode only
the leading GOP (smart-cut; not supported natively by ffmpeg).

## Segment muxer options worth knowing

| Option | Meaning |
|---|---|
| `-segment_time 10` | target segment length in seconds (fractional OK) |
| `-segment_time_delta 1` | allow +/- delta around boundary (keyframe-friendly) |
| `-segment_format mp4` | force container for segments |
| `-segment_list out.m3u8` | write a manifest listing every segment |
| `-segment_list_type m3u8` | manifest flavor (`flat`, `m3u8`, `csv`, `ffconcat`) |
| `-reset_timestamps 1` | reset each segment's PTS/DTS to 0 (standalone playback) |
| `-segment_start_number 100` | offset numbering |
| `-segment_times 30,60,90` | explicit cut points instead of even intervals |

Example — cut at exact known timestamps, not regular intervals:

```bash
ffmpeg -i input.mp4 -c copy -map 0 \
  -f segment -segment_times 30,60,90,120 \
  -reset_timestamps 1 \
  piece_%03d.mp4
```

## Concat filter — more than 2 inputs, extra streams

Three inputs, 1 video + 2 audio tracks each:

```bash
ffmpeg -i a.mp4 -i b.mp4 -i c.mp4 \
  -filter_complex "[0:v][0:a:0][0:a:1][1:v][1:a:0][1:a:1][2:v][2:a:0][2:a:1]concat=n=3:v=1:a=2[v][a0][a1]" \
  -map "[v]" -map "[a0]" -map "[a1]" \
  -c:v libx264 -crf 18 -c:a aac out.mp4
```

If one input has no audio, pad with `anullsrc`:

```bash
ffmpeg -i silent.mp4 -i loud.mp4 -f lavfi -t 1 -i anullsrc=cl=stereo:r=48000 \
  -filter_complex "[0:v][2:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" out.mp4
```

## Removing a middle section (A-B cut)

Cut `[0..T1]` and `[T2..end]`, then concat:

```bash
ffmpeg -i in.mp4 -to T1 -c copy part1.mp4
ffmpeg -ss T2 -i in.mp4 -c copy part2.mp4
printf "file 'part1.mp4'\nfile 'part2.mp4'\n" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy joined.mp4
```

Expect a glitch at the join if codec params drift across the source (rare
with a single source file). If so, use the concat filter instead.

## Common verifications

```bash
# Duration of output
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 out.mp4

# Keyframe times in a source (to pick safe stream-copy cuts)
ffprobe -v error -select_streams v:0 -skip_frame nokey \
  -show_entries frame=pkt_pts_time -of csv=p=0 in.mp4

# Confirm all concat inputs have identical codec params
for f in *.mp4; do
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,width,height,r_frame_rate,sample_aspect_ratio,pix_fmt \
    -of default=nw=1 "$f"
  echo "--- $f"
done
```
