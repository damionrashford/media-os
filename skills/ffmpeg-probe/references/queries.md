# ffprobe queries — reference

Companion to `SKILL.md`. Everything here is copy-pasteable.

---

## 1. `-show_entries` field table

`-show_entries` takes a colon-separated list of section filters. Each filter is
either `SECTION` (dump all known keys) or `SECTION=k1,k2,…` (whitelist).

### Format section (`format=…`)

The container. Single object per file.

| Key                    | Meaning                                          |
|------------------------|--------------------------------------------------|
| `filename`             | Path as demuxer sees it.                         |
| `nb_streams`           | Total stream count.                              |
| `nb_programs`          | Program count (MPEG-TS).                         |
| `format_name`          | Short demuxer name (`mov,mp4,m4a,3gp,…`).        |
| `format_long_name`     | Human name.                                      |
| `start_time`           | Seconds (float, may be negative).                |
| `duration`             | Seconds (float).                                 |
| `size`                 | Bytes.                                           |
| `bit_rate`             | Container-level bitrate, b/s.                    |
| `probe_score`          | 0–100, demuxer's confidence.                     |
| `tags`                 | Dict of arbitrary metadata (title, artist, …).   |

### Stream section (`stream=…`)

One object per stream. Common keys:

| Key                      | Applies to | Meaning                                       |
|--------------------------|------------|-----------------------------------------------|
| `index`                  | all        | 0-based index inside container.               |
| `codec_name`             | all        | `h264`, `hevc`, `aac`, `opus`, `subrip`, …    |
| `codec_long_name`        | all        | Human name.                                   |
| `codec_type`             | all        | `video` / `audio` / `subtitle` / `data`.      |
| `codec_tag_string`       | all        | FourCC (`avc1`, `hev1`, `mp4a`, …).           |
| `profile`                | v / a      | `High`, `Main 10`, `LC`, …                    |
| `width` / `height`       | v          | Coded size, pixels.                           |
| `coded_width` / `coded_height` | v    | Post-crop size, usually same as width/height. |
| `sample_aspect_ratio`    | v          | Pixel shape (`1:1`, `40:33`, …).              |
| `display_aspect_ratio`   | v          | Picture shape (`16:9`, …).                    |
| `pix_fmt`                | v          | `yuv420p`, `yuv420p10le`, `nv12`, …           |
| `field_order`            | v          | `progressive` / `tt` / `bb` / `tb` / `bt`.    |
| `level`                  | v          | Codec level (H.264 `41` = 4.1).               |
| `color_range`            | v          | `tv` (limited) / `pc` (full).                 |
| `color_space`            | v          | Matrix: `bt709`, `bt2020nc`, …                |
| `color_transfer`         | v          | `bt709`, `smpte2084` (HDR10), `arib-std-b67` (HLG). |
| `color_primaries`        | v          | `bt709`, `bt2020`, …                          |
| `chroma_location`        | v          | `left`, `center`, …                           |
| `r_frame_rate`           | v          | Base rate as fraction — parse `num/den`.      |
| `avg_frame_rate`         | v          | Average fps fraction.                         |
| `time_base`              | all        | Fraction; multiply pts by this for seconds.   |
| `start_pts` / `start_time`| all       | First PTS / seconds.                          |
| `duration_ts` / `duration`| all       | Timebase units / seconds.                     |
| `bit_rate`               | all        | b/s. Often N/A for MKV/WebM.                  |
| `max_bit_rate`           | all        | b/s.                                          |
| `nb_frames`              | v / a      | Frame count if muxer stored it.               |
| `nb_read_frames`         | v / a      | Counted by `-count_frames` (decodes; slow).   |
| `nb_read_packets`        | all        | Counted by `-count_packets`.                  |
| `sample_rate`            | a          | Hz.                                           |
| `channels`               | a          | Integer channel count.                        |
| `channel_layout`         | a          | `mono`, `stereo`, `5.1`, `7.1`, …             |
| `sample_fmt`             | a          | `fltp`, `s16p`, …                             |
| `bits_per_sample`        | a          | 0 for compressed formats.                     |
| `bits_per_raw_sample`    | v / a      | True bit depth.                               |
| `disposition`            | all        | Dict of flags: `default`, `forced`, …         |
| `tags`                   | all        | `language`, `title`, `handler_name`, …        |

### Frame section (`frame=…`) — huge, always bound

| Key                         | Meaning                                      |
|-----------------------------|----------------------------------------------|
| `media_type`                | `video` / `audio`.                           |
| `stream_index`              | Owning stream.                               |
| `key_frame`                 | 1 = key frame.                               |
| `pict_type`                 | `I` / `P` / `B` (video).                     |
| `pkt_pts` / `pkt_pts_time`  | Packet PTS / seconds.                        |
| `pkt_dts` / `pkt_dts_time`  | Packet DTS / seconds.                        |
| `best_effort_timestamp`     | Best guess PTS (prefer this for seeking).    |
| `best_effort_timestamp_time`| Same, in seconds.                            |
| `pkt_duration_time`         | Frame duration, seconds.                     |
| `width` / `height`          | Decoded frame size.                          |
| `interlaced_frame`          | 1/0.                                         |
| `top_field_first`           | 1/0.                                         |
| `repeat_pict`               | 1/0.                                         |
| `side_data_list`            | Per-frame HDR / closed captions / A53.       |

### Packet section (`packet=…`) — huge, always bound

| Key                | Meaning                                         |
|--------------------|-------------------------------------------------|
| `codec_type`       | video / audio / …                               |
| `stream_index`     | Owning stream.                                  |
| `pts` / `pts_time` | In time_base units / seconds.                   |
| `dts` / `dts_time` | Decode timestamp.                               |
| `duration` / `duration_time` | Packet duration.                      |
| `size`             | Bytes.                                          |
| `pos`              | Byte offset in file.                            |
| `flags`            | `K` = keyframe, `_` = not.                      |

### Other sections

- `chapter=…` — `id`, `time_base`, `start`, `start_time`, `end`, `end_time`, `tags`.
- `program=…` — MPEG-TS programs; has nested `streams`.
- `stream_side_data_list=…` — HDR metadata container (see HDR section below).
- `stream_disposition=…` — break `disposition` out as its own section.
- `format_tags=…` / `stream_tags=…` — metadata only.

Combined example:
```bash
ffprobe -v error -show_entries \
  'format=duration,bit_rate:stream=index,codec_name,width,height,r_frame_rate' \
  -of json in.mp4
```

---

## 2. Output-format cheat sheet (`-of` / `-print_format`)

| Form                                    | Example output                          |
|-----------------------------------------|-----------------------------------------|
| `default`                               | `width=1920` / `[STREAM] … [/STREAM]`   |
| `default=nw=1`                          | Suppress section wrappers.              |
| `default=nk=1`                          | Values only, no keys.                   |
| `default=nw=1:nk=1`                     | Pure bare values.                       |
| `json`                                  | Full nested JSON object.                |
| `json=c=1`                              | Compact (no indentation).               |
| `csv`                                   | `stream,0,1920,1080`                    |
| `csv=p=0`                               | Strip leading section name.             |
| `csv=s=x`                               | Use `x` as separator (`1920x1080`).     |
| `csv=s=x:p=0`                           | Combine: `1920x1080`.                   |
| `flat`                                  | `streams.stream.0.width=1920`           |
| `flat=s=_:h=1`                          | `_` separator, include header.          |
| `ini`                                   | Windows INI sections.                   |
| `xml`                                   | XML (add `-x` for pretty).              |
| `xml=x=1`                               | XSD-compliant XML.                      |

Short aliases: `-of` == `-print_format`. Settings after `=` are comma-sep key=value.

---

## 3. Stream specifier syntax

Used with `-select_streams`. Copy of ffmpeg stream specifiers:

| Form                 | Meaning                                                 |
|----------------------|---------------------------------------------------------|
| `v` / `a` / `s` / `d` / `t` | All video / audio / subtitle / data / attachment. |
| `v:0`                | First video stream (0-indexed within type).             |
| `a:1`                | Second audio stream.                                    |
| `0:5`                | Stream index 5 in input 0 (raw index).                  |
| `v:m:language:eng`   | First video whose `language` tag is `eng`.              |
| `a:m:language:eng`   | First English audio.                                    |
| `a:m:title:Director` | First audio whose title contains `Director`.            |
| `p:1:v`              | Video in program id 1 (MPEG-TS).                        |
| `#`+tag              | By stream `id` (container-assigned).                    |

Examples:
```bash
# First English audio
ffprobe -v error -select_streams a:m:language:eng \
  -show_entries stream=index,codec_name,channels -of json in.mkv

# Stream with the specific index 5
ffprobe -v error -select_streams 0:5 \
  -show_entries stream=codec_type,codec_name -of json in.mkv
```

---

## 4. HDR detection flowchart

```
                  +-------------------------------+
                  | side_data_list contains       |
                  | "DOVI configuration record"?  |
                  +-------------------------------+
                         |yes               |no
                   Dolby Vision              v
                                 +-------------------------------+
                                 | color_transfer == arib-std-b67|
                                 +-------------------------------+
                                         |yes               |no
                                        HLG                   v
                                              +-------------------------------+
                                              | color_transfer == smpte2084   |
                                              | OR color_primaries == bt2020  |
                                              +-------------------------------+
                                                    |yes               |no
                                                  HDR10                SDR
```

Extra HDR10 evidence (not required, but confirming):
- `side_data_type = "Mastering display metadata"` in `stream_side_data_list`
- `side_data_type = "Content light level metadata"` in `stream_side_data_list`
- `pix_fmt = yuv420p10le` / `yuv422p10le` / `yuv420p12le` (10-bit+ required for HDR)

HDR10+ adds dynamic metadata inside bitstream SEI — ffprobe exposes it as
`side_data_type = "HDR Dynamic Metadata SMPTE2094-40 (HDR10+)"` in frame
side_data when present.

Detection one-liner:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_transfer,color_primaries:stream_side_data=side_data_type \
  -of json in.mp4
```

---

## 5. Timebase math

ffprobe reports timestamps in **time_base units** (a fraction like `1/90000`
or `1/15360`).

Seconds = `pts * time_base.num / time_base.den`.

ffprobe usually already exposes the computed seconds as a parallel field:

| Raw (units)               | Computed (seconds)              |
|---------------------------|---------------------------------|
| `start_pts`               | `start_time`                    |
| `duration_ts`             | `duration`                      |
| `pts`                     | `pts_time`                      |
| `dts`                     | `dts_time`                      |
| `pkt_pts`                 | `pkt_pts_time`                  |
| `pkt_dts`                 | `pkt_dts_time`                  |
| `best_effort_timestamp`   | `best_effort_timestamp_time`    |

Prefer `*_time` fields unless you're doing frame-accurate seeking/muxing math,
in which case you want the integer `pts` + `time_base` so you avoid float
rounding.

---

## 6. `-read_intervals` syntax

Limits which bytes ffprobe reads. Crucial for `-show_frames`/`-show_packets`.

```
intervals  := interval [, interval …]
interval   := [start]%[+end | +#nframes]
start / end:
  absolute seconds ........  "30"
  percentage .............. "25%"
  duration from start of prev "+15"
  N packets from start ....  "+#100"
```

Examples:

| Input                  | Meaning                                               |
|------------------------|-------------------------------------------------------|
| `30%+20`               | Start at 30% of duration, read 20 seconds.            |
| `10%20%`               | Read from 10% to 20% of duration.                     |
| `0%+#50`               | First 50 packets.                                     |
| `60%+#100`             | 100 packets starting at 60%.                          |
| `5,10,20%+30`          | Multiple intervals: 5s point, 10s point, 20% + 30s.   |

---

## 7. One-liner library (copy & adapt)

**Container basics**
```bash
# Duration (float seconds)
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 in.mp4

# File size (bytes)
ffprobe -v error -show_entries format=size -of default=nw=1:nk=1 in.mp4

# Container format name
ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 in.mp4

# Container bitrate (b/s)
ffprobe -v error -show_entries format=bit_rate -of default=nw=1:nk=1 in.mp4
```

**Video stream**
```bash
# Resolution as 1920x1080
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 in.mp4

# Codec (h264, hevc, …)
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nw=1:nk=1 in.mp4

# FPS (fraction — parse it)
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=nw=1:nk=1 in.mp4

# Average FPS (float-friendly via awk)
ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=nw=1:nk=1 in.mp4 \
  | awk -F/ '$2==0 {print "N/A"; exit} {printf "%.3f\n", $1/$2}'

# Pixel format / bit depth
ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt,bits_per_raw_sample -of json in.mp4

# Aspect ratio (DAR)
ffprobe -v error -select_streams v:0 -show_entries stream=display_aspect_ratio -of default=nw=1:nk=1 in.mp4

# Color tags (for HDR / BT.709 classification)
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_space,color_transfer,color_primaries,color_range -of json in.mp4

# Nominal frame count
ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nw=1:nk=1 in.mp4

# Exact frame count (decodes — slow)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 in.mp4

# GOP / keyframe interval (list keyframe times)
ffprobe -v error -select_streams v:0 -show_frames \
  -show_entries frame=pkt_pts_time,pict_type -of csv=p=0 in.mp4 \
  | awk -F, '$2=="I"{print $1}'
```

**Audio stream**
```bash
# Audio codec
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1:nk=1 in.mp4

# Channel count + layout
ffprobe -v error -select_streams a:0 -show_entries stream=channels,channel_layout -of default=nw=1 in.mp4

# Sample rate
ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nw=1:nk=1 in.mp4

# Audio bitrate
ffprobe -v error -select_streams a:0 -show_entries stream=bit_rate -of default=nw=1:nk=1 in.mp4

# Language of every audio track
ffprobe -v error -select_streams a -show_entries stream=index:stream_tags=language -of csv=p=0 in.mkv
```

**Subtitles & chapters**
```bash
# List subtitle tracks with language
ffprobe -v error -select_streams s -show_entries stream=index,codec_name:stream_tags=language,title -of json in.mkv

# All chapters
ffprobe -v error -show_chapters -of json in.mkv

# Chapter titles as a list
ffprobe -v error -show_chapters -show_entries chapter=start_time,end_time:chapter_tags=title -of json in.mkv
```

**Metadata**
```bash
# Format-level tags (title, artist, comment, …)
ffprobe -v error -show_entries format_tags -of json in.mp4

# All per-stream tags
ffprobe -v error -show_entries stream_tags -of json in.mkv

# Just the encoder tag
ffprobe -v error -show_entries format_tags=encoder -of default=nw=1:nk=1 in.mp4
```

**Sampling / debugging**
```bash
# First 50 packets only (video)
ffprobe -v error -select_streams v:0 -read_intervals "%+#50" -show_packets -of json in.mp4

# 30 seconds starting 2 minutes in
ffprobe -v error -select_streams v:0 -read_intervals "120%+30" -show_frames -of json in.mp4

# Probe a raw YUV file
ffprobe -v error -f rawvideo -video_size 1920x1080 -pix_fmt yuv420p -framerate 24 \
  -show_streams -of json in.yuv

# Detect corruption at the demuxer level
ffprobe -v error -show_error -of json in.mp4

# Probe via a lavfi source (generated test pattern)
ffprobe -v error -f lavfi -i "testsrc=size=1280x720:rate=30" \
  -show_streams -of json
```

**Quick classifiers (shell)**
```bash
# HDR yes/no
t=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer \
      -of default=nw=1:nk=1 in.mp4)
case "$t" in smpte2084|arib-std-b67) echo HDR ;; *) echo SDR ;; esac

# Is audio stereo?
c=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels \
      -of default=nw=1:nk=1 in.mp4)
[ "$c" = "2" ] && echo stereo || echo "$c channels"

# Does the file have a video stream?
ffprobe -v error -select_streams v -show_entries stream=index -of csv=p=0 in.mp4 \
  | grep -q . && echo video || echo no-video
```
