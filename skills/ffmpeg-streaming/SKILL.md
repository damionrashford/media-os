---
name: ffmpeg-streaming
description: >
  Package and stream media with ffmpeg: HLS (hls muxer), MPEG-DASH (dash muxer), RTMP push (to YouTube/Twitch/custom ingest), SRT, RTSP, RTP, UDP, plus tee muxer for multi-output. Use when the user asks to stream to YouTube/Twitch/Facebook Live, push RTMP, generate HLS segments, build a DASH manifest, go live, set up low-latency streaming with SRT, or output to multiple destinations at once.
argument-hint: "[protocol] [input]"
---

# Ffmpeg Streaming

**Context:** $ARGUMENTS

## Quick start

- **Push to YouTube/Twitch (RTMP):** → Step 1 (RTMP) + Step 2 (live encoder)
- **Generate HLS VOD (.m3u8 + TS):** → Step 1 (HLS) + Step 3 (muxer)
- **HLS live with sliding window:** → Step 1 (HLS live) + Step 3
- **HLS ABR ladder (multi-rendition master):** → Step 1 (HLS ABR)
- **MPEG-DASH manifest:** → Step 1 (DASH)
- **Low-latency SRT transport:** → Step 1 (SRT)
- **Multi-output (HLS + RTMP + file):** → Step 1 (Tee)

## When to use

- Pushing a live encoder to an ingest (YouTube, Twitch, Facebook, Mux, Wowza, nginx-rtmp).
- Packaging a file or live source into HLS / DASH for browser/mobile playback.
- Building an ABR ladder with multiple renditions and a master playlist.
- Contribution links with very low latency (SRT, RTP, UDP, RTSP).
- Distributing a single encode to many destinations without encoding N times (tee muxer).

## Step 1 — Pick a delivery protocol

| Protocol | Muxer / `-f` | Typical use | Latency |
| --- | --- | --- | --- |
| RTMP   | `-f flv` to `rtmp://…`         | Ingest to YouTube/Twitch/FB    | 2–5 s |
| HLS    | `-f hls` → `.m3u8` + segments  | Browser / iOS VOD + Live       | 6–20 s (std), 3–7 s (LL) |
| DASH   | `-f dash` → `.mpd`             | Browser / Android              | 6–20 s (std), 3–7 s (LL) |
| SRT    | `-f mpegts` over `srt://…`     | Contribution / IP backhaul     | 120–400 ms |
| RTSP   | `-f rtsp` to `rtsp://…`        | IP cameras / private nets      | ~200 ms |
| RTP    | `-f rtp` to `rtp://host:port`  | Low-level unicast/multicast    | ~100 ms |
| UDP    | `-f mpegts` to `udp://…`       | Broadcast contribution         | ~100 ms |
| Tee    | `-f tee '[f=…]out1|[f=…]out2'` | One encode → many destinations | per-sink |

Decide **one** primary protocol first. Pick tee only *after* the single-sink command works.

## Step 2 — Encoder settings for low-latency live

Live ingests demand a strict GOP and fast encoder. These flags are mandatory for RTMP/HLS/DASH live.

```
-c:v libx264 -preset veryfast -tune zerolatency \
-b:v 6000k -maxrate 6000k -bufsize 12000k \
-pix_fmt yuv420p \
-g 60 -keyint_min 60 -sc_threshold 0 \
-c:a aac -b:a 160k -ar 44100 -ac 2
```

Rules of thumb:

- **GOP size `-g` = fps × segment_time** (30 fps × 2 s = `-g 60`). Force with `-keyint_min` equal to `-g`.
- `-sc_threshold 0` disables scene-cut keyframes → consistent GOP boundaries required for clean HLS/DASH segmentation.
- `-tune zerolatency` only valid for `libx264`/`libx265`; drops B-frames and look-ahead.
- YouTube/Twitch/Facebook want **2-second keyframe interval**, AAC LC, 44.1 or 48 kHz.
- For files played in real-time (simulated live), prepend `-re` on the **input**. Do NOT use `-re` with a real live camera.

## Step 3 — Muxer options

### RTMP (push to platform ingest)

```
ffmpeg -i in.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -b:v 6000k -maxrate 6000k -bufsize 12000k \
  -g 60 -keyint_min 60 -sc_threshold 0 -pix_fmt yuv420p \
  -c:a aac -b:a 160k -ar 44100 \
  -f flv rtmp://a.rtmp.youtube.com/live2/STREAM-KEY
```

Ingests: YouTube `rtmp://a.rtmp.youtube.com/live2/KEY`, Twitch `rtmp://live.twitch.tv/app/KEY`, Facebook `rtmps://live-api-s.facebook.com:443/rtmp/KEY`. `rtmps://` needs an ffmpeg built with OpenSSL/GnuTLS.

### HLS — VOD (fixed playlist)

```
ffmpeg -i in.mp4 \
  -c:v libx264 -b:v 2500k -c:a aac -b:a 128k \
  -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_segment_filename 'seg_%03d.ts' out.m3u8
```

### HLS — live (sliding window)

```
ffmpeg -i rtmp://localhost/live/stream \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -b:v 3000k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 128k \
  -f hls -hls_time 4 -hls_list_size 6 \
  -hls_flags delete_segments+append_list \
  out.m3u8
```

Use `-hls_playlist_type event` when you want the playlist to grow but never drop segments. Leave `-hls_playlist_type` unset (or `event`) to allow `delete_segments`.

### HLS — fMP4 (CMAF-style)

```
-hls_segment_type fmp4 \
-hls_fmp4_init_filename init.mp4 \
-hls_segment_filename 'seg_%05d.m4s'
```

### HLS — ABR (3 renditions, master playlist)

```
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]split=3[v1][v2][v3];
    [v1]scale=w=1920:h=1080[v1out];
    [v2]scale=w=1280:h=720[v2out];
    [v3]scale=w=854:h=480[v3out]" \
  -map "[v1out]" -c:v:0 libx264 -b:v:0 5000k -maxrate:v:0 5350k -bufsize:v:0 7500k \
  -map "[v2out]" -c:v:1 libx264 -b:v:1 2800k -maxrate:v:1 3000k -bufsize:v:1 4200k \
  -map "[v3out]" -c:v:2 libx264 -b:v:2 1400k -maxrate:v:2 1500k -bufsize:v:2 2100k \
  -map a:0 -map a:0 -map a:0 \
  -c:a aac -b:a 128k -ac 2 \
  -preset veryfast -g 60 -keyint_min 60 -sc_threshold 0 \
  -f hls -hls_time 4 -hls_playlist_type vod \
  -hls_segment_filename 'stream_%v/seg_%03d.ts' \
  -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" \
  'stream_%v/index.m3u8'
```

`-var_stream_map` groups are space-separated; each group lists comma-separated stream indexes for that rendition (`v:N,a:N`). `%v` in filenames expands to the variant index.

### MPEG-DASH

```
ffmpeg -i in.mp4 \
  -c:v libx264 -b:v 2500k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 128k \
  -f dash -seg_duration 4 -use_template 1 -use_timeline 1 \
  -init_seg_name 'init-$RepresentationID$.m4s' \
  -media_seg_name 'chunk-$RepresentationID$-$Number%05d$.m4s' \
  manifest.mpd
```

### SRT — listener (pull) and caller (push)

```
# Listener (server) — wait for a caller to connect
ffmpeg -re -i in.mp4 -c copy \
  -f mpegts 'srt://0.0.0.0:9000?mode=listener&latency=120000'

# Caller (push) with passphrase (AES-128)
ffmpeg -re -i in.mp4 -c copy \
  -f mpegts 'srt://receiver.example.com:9000?mode=caller&passphrase=secretpass123&pbkeylen=16&latency=120000'
```

`latency` is in **microseconds** (`120000` = 120 ms). `pbkeylen` = 16/24/32 for AES-128/192/256. Passphrase must be 10–79 chars.

### Tee muxer — one encode, many outputs

```
ffmpeg -i in.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -b:v 4500k -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 128k \
  -map 0:v -map 0:a \
  -f tee '[f=flv]rtmp://a.rtmp.youtube.com/live2/KEY|[f=hls:hls_time=4:hls_list_size=6:hls_flags=delete_segments]out.m3u8|[f=mpegts]archive.ts'
```

Escape `|` inside shell strings by quoting the whole tee spec. Per-sink options go inside `[f=…:opt=val:opt=val]`.

## Step 4 — Run + verify

1. Print the ffmpeg command (the script prints before executing).
2. Start the command; check stderr for `frame=`, `fps=`, `bitrate=`, `speed=`. `speed` must be ≥ 1× for live.
3. For HLS/DASH outputs: verify segments land on disk, open `.m3u8`/`.mpd` in a player (ffplay, hls.js, dash.js, Safari).
4. For RTMP: the platform dashboard should show "live" within 10–30 s.
5. For SRT: watch the stats printed by ffmpeg (RTT, lost pkts). If `lost` grows, raise `latency`.

## Available scripts

- **`scripts/stream.py`** — subcommands: `rtmp`, `hls-vod`, `hls-live`, `hls-abr`, `dash`, `srt-listener`, `srt-caller`, `tee`. Stdlib only; prints the ffmpeg command, supports `--dry-run` and `--verbose`.

## Workflow

1. Pick the subcommand, then run:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/stream.py <subcommand> --input INPUT [flags]
   ```
2. Add `--dry-run` first to print the command; run again without it to execute.

## Reference docs

- Read [`references/muxers.md`](references/muxers.md) for full option tables (hls, dash, tee, rtmp, srt, rtsp, udp, rtp), latency ladder, platform ingest URLs, keyframe math, and LL-HLS notes.

## Gotchas

- `-re` is required when streaming a **file** in real-time (live simulation); NEVER use it on a true live camera/encoder input.
- **GOP = fps × segment_time** is mandatory. 30 fps × 2 s → `-g 60 -keyint_min 60`. Set both; `-g` alone allows variable GOP.
- `-sc_threshold 0` is REQUIRED on libx264 for HLS/DASH — otherwise a scene cut inserts an extra keyframe and segments misalign.
- `-tune zerolatency` is libx264/libx265 only. It disables B-frames + look-ahead; do not use for VOD.
- YouTube requires a **2-second keyframe interval** (at 30 fps that is `-g 60`). Twitch and Facebook are the same.
- RTMP output container MUST be `-f flv`. AAC-LC only; sample rate 44.1 or 48 kHz; stereo.
- HLS `-hls_flags delete_segments` only works when `-hls_playlist_type` is **unset** or `event`, never `vod`.
- HLS ABR requires **stream-specific flags**: `-c:v:0`, `-b:v:0`, `-maxrate:v:0`, `-bufsize:v:0`, etc., one set per rendition.
- `-var_stream_map` takes **space-separated** groups, each `v:N,a:N` referencing the **output** map indexes, not input.
- DASH best-practice: `-use_template 1 -use_timeline 1`. Leave both off only for static MPDs you hand-edit.
- SRT `latency` is **microseconds** (120000 = 120 ms). Minimum useful value ≈ 2 × RTT.
- Tee: the `|` separator must be inside quotes to avoid being parsed as a shell pipe.
- `-flush_packets 1` (default) is fine for RTMP; set `-flush_packets 0` only if a specific CDN asks for it — increases latency.
- `-movflags +faststart` is for MP4 VOD only. It is **irrelevant** for live HLS/DASH/RTMP/SRT.
- LL-HLS partial segments (`EXT-X-PART`) are NOT produced by upstream ffmpeg. ffmpeg emits standard HLS with short `-hls_time` (e.g. 2 s) — true LL-HLS requires an external packager.

## Examples

### Example 1: go live on YouTube from a local file

Input: `intro.mp4`, stream key `abcd-1234-efgh-5678`.
```
uv run scripts/stream.py rtmp --input intro.mp4 \
  --url rtmp://a.rtmp.youtube.com/live2/abcd-1234-efgh-5678 \
  --bitrate 6000k --preset veryfast
```
Result: YouTube Studio shows "Live" within ~20 s.

### Example 2: HLS VOD with 6-second segments

```
uv run scripts/stream.py hls-vod --input movie.mp4 --outdir out/ --segments 6
```
Result: `out/index.m3u8` + `out/seg_000.ts`, `seg_001.ts`, …

### Example 3: HLS ABR ladder (1080p/720p/480p)

```
uv run scripts/stream.py hls-abr --input master.mov --outdir abr/ \
  --ladder "1080p=5000k 720p=2800k 480p=1400k"
```
Result: `abr/master.m3u8` master + `abr/stream_0/index.m3u8`, `stream_1/…`, `stream_2/…`.

### Example 4: SRT caller with AES-128

```
uv run scripts/stream.py srt-caller --input live.ts \
  --url 'srt://receiver.example.com:9000?mode=caller&passphrase=secretpass123&pbkeylen=16&latency=120000'
```

### Example 5: Tee — simultaneous YouTube + local HLS + archive

```
uv run scripts/stream.py tee --input cam.mp4 \
  --outputs '[f=flv]rtmp://a.rtmp.youtube.com/live2/KEY|[f=hls:hls_time=4:hls_list_size=6:hls_flags=delete_segments]out.m3u8|[f=mpegts]archive.ts'
```

## Troubleshooting

### Error: `Output #0, flv, to 'rtmp://...': could not find tag for codec ... in stream #0`

Cause: container/codec mismatch. RTMP/FLV only carries H.264 + AAC.
Solution: add `-c:v libx264 -c:a aac`. Never pass `-c copy` to an RTMP target unless the input is already H.264/AAC.

### Error: `Non-monotonous DTS` flood

Cause: re-muxing a live source with `-c copy` when input has bad timestamps.
Solution: re-encode (`-c:v libx264 -c:a aac`) or add `-fflags +genpts`.

### Error: HLS playlist `#EXT-X-DISCONTINUITY` on every segment

Cause: GOP not aligned to segment duration. Scene-cut keyframes or `-g` != fps × hls_time.
Solution: set `-g $((fps * hls_time)) -keyint_min $((fps * hls_time)) -sc_threshold 0`.

### Error: SRT `Connection setup failure: connection time out`

Cause: listener not reachable, wrong mode, or latency too low for the link RTT.
Solution: verify `mode=listener` vs `mode=caller`, open UDP port 9000, raise `latency=400000` for sat links.

### Error: Tee output — one sink kills the whole ffmpeg on network drop

Cause: by default tee propagates sink errors.
Solution: add `onfail=ignore` per sink: `[f=flv:onfail=ignore]rtmp://…`.

### Error: YouTube says "no data received"

Cause: wrong ingest URL, missing `-f flv`, or GOP > 4 s.
Solution: confirm `rtmp://a.rtmp.youtube.com/live2/KEY`, use `-f flv`, ensure keyframes every 2 s (`-g 60` at 30 fps).
