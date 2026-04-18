---
name: workflow-vod-post-production
description: Traditional VOD finishing — transcode to mezzanine + proxies, cut/trim/concat, color grade (LUT / OCIO / manual), stabilize handheld, denoise, retime (slow-mo / reverse / speed ramps), chromakey, lower thirds, burn subtitles, loudness normalize, thumbnails/sprite sheets, chapter metadata, and final delivery H.264/AV1 for YouTube/social/archive. Use when the user says "finish my YouTube video", "post-production", "color grade and stabilize", "convert to vertical TikTok", "batch wedding videos", "sprite sheet for scrubbing", or standard VOD finishing.
argument-hint: [source]
---

# Workflow — VOD Post-Production

**What:** Finish a video between editorial and distribution. Transcode, color, retime, caption, audio, package. Not live. Not broadcast master. Not AI-restoration. Just classic VOD finishing.

## Skills used

`ffmpeg-transcode`, `ffmpeg-hwaccel`, `ffmpeg-cut-concat`, `ffmpeg-speed-time`, `ffmpeg-video-filter`, `ffmpeg-stabilize`, `ffmpeg-denoise-restore`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro`, `ffmpeg-hdr-color`, `ffmpeg-chromakey`, `ffmpeg-compose-mask`, `ffmpeg-lens-perspective`, `ffmpeg-subtitles`, `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `media-ffmpeg-normalize`, `ffmpeg-frames-images`, `ffmpeg-metadata`, `media-moviepy`, `media-handbrake`, `media-batch`, `media-cloud-upload`, `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-quality`.

## Pipeline

### Step 1 — Transcode to mezzanine

ProRes 422 HQ (Apple) or DNxHR HQ (Avid / cross-platform). Never cut from camera original.

### Step 2 — Proxies for offline edit

Hardware-accelerated H.264 (NVENC / QSV / VideoToolbox). Real-time or faster on modern chips.

### Step 3 — Cut / trim / concat

`ffmpeg-cut-concat`:
- `trim --mode stream-copy` — FAST, keyframe-snapped.
- `trim --mode reencode` — frame-accurate.
- `concat --mode copy` — same codec.
- `concat --mode filter` — different codecs.

### Step 4 — Color grade

`ffmpeg-lut-grade` for `.cube`/`.3dl`/Hald CLUT. `ffmpeg-ocio-colorpro` for OCIO/ACES. Manual `eq`, `curves`, `colorbalance` filters via `ffmpeg-video-filter`.

### Step 5 — Stabilize

`ffmpeg-stabilize` two-pass (`vidstabdetect` → `vidstabtransform`) for best quality; `deshake` single-pass for speed.

### Step 6 — Denoise

`ffmpeg-denoise-restore`: `nlmeans` for film grain, `bm3d` heavier preserves detail, `hqdn3d` general fast.

### Step 7 — Scale / crop / reframe

`scale`, `cropdetect` auto letterbox, `16:9 → 9:16` vertical via `crop`+`scale`.

### Step 8 — Speed / time manipulation

`ffmpeg-speed-time`: `setpts`, `atempo`, `minterpolate` for smooth slow-mo, freeze frame, reverse.

### Step 9 — Chromakey / greenscreen

`ffmpeg-chromakey`: `chromakey` + `despill` filters.

### Step 10 — Text / lower thirds

`drawtext` or ASS sidecar subtitles.

### Step 11 — Subtitles

`ffmpeg-subtitles`: soft-mux, burn-in, extract, format convert.

### Step 12 — Audio finishing

EQ + compression via `ffmpeg-audio-filter`, loudness via `media-ffmpeg-normalize`.

### Step 13 — Thumbnails / sprite sheets

`ffmpeg-frames-images`: extract every N seconds, sprite sheet for scrubber UI, animated GIF preview.

### Step 14 — Chapters + metadata

`ffmpeg-metadata`: chapter markers + cover art.

### Step 15 — Final delivery

HandBrake preset for prosumer; ffmpeg direct for fine-grained; AV1 for archival/bandwidth.

### Step 16 — QC

`workflow-analysis-quality` — VMAF vs reference, spec assertions.

### Step 17 — Upload

`media-cloud-upload` (YouTube, Vimeo, S3, etc.).

## Variants

- **Batch** — `media-batch` runs `finish-xxx.sh` across N files in parallel.
- **Programmatic (MoviePy)** — when ffmpeg filtergraph gets unwieldy, drop to Python.
- **Vertical social** — face-tracking auto-crop 16:9 → 9:16.
- **360° VR edit** — equirect → stereographic "little planet" via `ffmpeg-360-3d`.

## Gotchas

- **`-movflags +faststart` is a SECOND pass.** Encoder runs; ffmpeg rewinds; rewrites moov atom to front. Adds time — necessary for progressive MP4.
- **`concat` demuxer requires identical codecs.** Different rates / codecs = silent failure. Use `concat` FILTER instead.
- **Slow-motion `setpts=N*PTS` needs matching `-r` input.** Without, frame drop/duplicate is odd.
- **`atempo` range is 0.5–2.0 per filter.** Chain for extreme tempo shifts.
- **`yadif` modes:** 0=single-rate, 1=double-rate, 2=spatial-only, 3=double-rate spatial.
- **`scale=-2:1080`** keeps aspect ratio with even width (required for yuv420p).
- **`libx264 -pix_fmt yuv420p` required for broadcast playback.** Many decoders don't handle `yuv422p` / `yuv444p`.
- **NVENC preset is `p1`–`p7`** (higher = better quality, slower). NOT `ultrafast`–`placebo`.
- **`h264_videotoolbox` is quality-preset only.** `-b:v` and `-q:v` are hints; quality varies.
- **`libsvtav1 -preset` is 0–13** (0 slowest). NOT 1–10 like libaom-av1.
- **`libvpx-vp9` needs `-row-mt 1 -threads 4`** to multi-thread. Single-threaded default.
- **`-shortest` stops at shortest input.** Without it, looping `-loop 1` inputs = infinite.
- **`drawtext` needs font FILE PATH, not font name.** macOS `/System/Library/Fonts/Helvetica.ttc`.
- **ASS subtitles use `&HAABBGGRR`** (ARGB). AA=alpha, BGR byte order. Wrong byte order = wrong color.
- **`chromakey` works in RGB.** YUV sources auto-convert, but precise keying wants `format=yuva420p` first.
- **`vidstab` requires `--enable-libvidstab`** ffmpeg build. Some Ubuntu stock builds lack it.
- **`atempo` preserves pitch; `asetrate` shifts pitch.** Combine carefully.
- **`-ss` before `-i`** = fast seek, non-frame-accurate. **`-ss` after `-i`** = frame-accurate, sequential. Use after for accuracy.
- **Two-pass loudnorm via `media-ffmpeg-normalize`.** Single-pass applies runtime auto limits.
- **`-map 0:v:0 -map 0:a:0`** selects first video+audio. Default `-map 0` grabs ALL streams.
- **HandBrake presets are opinionated.** "Fast 1080p30" = H.264 CRF 22 + AAC 160. Sometimes wrong for source.
- **Alpha preservation needs `-pix_fmt yuva420p`** (or yuva444p) AND `-c:v qtrle` or `-c:v prores_ks -profile:v 4` (ProRes 4444). H.264 has NO alpha.

## Example — 4K camera raw → 1080p YouTube master

Probe → ProRes 422 HQ mezzanine → cut + concat → LUT color grade → `hqdn3d` → `scale=-2:1080` → `loudnorm` two-pass → `drawtext` lower third → `mov_text` subtitles → H.264 CRF 18 `yuv420p` `-movflags +faststart` → VMAF QC → YouTube upload.

## Related

- `workflow-editorial-interchange` — round-tripping the edit into/out of NLEs.
- `workflow-ai-enhancement` — AI upscale/interpolate/denoise path.
- `workflow-analysis-quality` — QC gating before shipping.
