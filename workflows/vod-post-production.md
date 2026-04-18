# VOD Post-Production Workflow

**What:** Traditional video-on-demand finishing — transcode, color, stabilize, denoise, caption, retime, deliver — for all the work between editorial and distribution that isn't live, broadcast, VFX, or AI-specific.

**Who:** YouTubers, small post houses, corporate video teams, wedding/event videographers, documentarians, anyone producing polished pre-recorded video at scale.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| Source transcode | `ffmpeg-transcode` | H.264 / HEVC / AV1 / VP9 / ProRes / DNxHR |
| HW encode | `ffmpeg-hwaccel` | NVENC / QSV / VAAPI / VideoToolbox / AMF / Vulkan |
| Edit / cut / concat | `ffmpeg-cut-concat` | Trim / split / segment / concat |
| Speed / time | `ffmpeg-speed-time` | Ramps, slow-mo, reverse, freeze-frame |
| Scale / crop / overlay | `ffmpeg-video-filter` | All 293 video filters |
| Stabilization | `ffmpeg-stabilize` | vid.stab 2-pass |
| Denoise | `ffmpeg-denoise-restore` | nlmeans, bm3d, hqdn3d |
| Color grading | `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro` | LUTs + OCIO |
| HDR | `ffmpeg-hdr-color` | HDR10 / HLG / DoVi / tone-map |
| Chromakey | `ffmpeg-chromakey` | Green/bluescreen keying + despill |
| Composite / mask | `ffmpeg-compose-mask` | Advanced masking + channel ops |
| Lens correction | `ffmpeg-lens-perspective` | Distortion, perspective, vignette |
| Subtitles | `ffmpeg-subtitles` | Soft-mux, burn-in, convert |
| Audio | `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial` | All audio ops |
| Loudness | `media-ffmpeg-normalize` | EBU R128 |
| Frame extraction | `ffmpeg-frames-images` | Stills / thumbs / sprite sheets / GIFs |
| Metadata | `ffmpeg-metadata` | Chapters / cover art / dispositions |
| Programmatic editing | `media-moviepy` | Python-driven video composition |
| Smart presets | `media-handbrake` | HandBrake CLI for "just encode this" |
| Batch | `media-batch` | Parallel |
| Cloud | `media-cloud-upload` | YouTube / Mux / Cloudflare / S3 |
| Probe / QC | `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-quality` | Verify |

---

## The pipeline

### 1. Transcode source to mezzanine (proxies + online)

Never cut from camera original — it's codec-hostile (H.264 long-GOP from drones, HEVC 10-bit from iPhone, ProRes compressed LT from cameras). Transcode to editorial mezzanine.

**ProRes 422 HQ** for Apple ecosystem:
```bash
uv run .claude/skills/ffmpeg-transcode/scripts/transcode.py to-prores \
  --input camera.mp4 --output mezz.mov --profile 3
```

**DNxHR HQ** for Avid / cross-platform:
```bash
ffmpeg -i camera.mp4 -c:v dnxhd -profile:v dnxhr_hq \
  -pix_fmt yuv422p -c:a pcm_s24le mezz.mxf
```

### 2. Proxies for offline edit

```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob 'raw/*.mp4' --output-dir proxies/ \
  --jobs 8 \
  --command 'ffmpeg -i {in} -vf scale=960:-2 -c:v h264_videotoolbox -b:v 3M -c:a aac {out}'
```

Hardware-accelerated = real-time or faster on modern chips.

### 3. Cut / trim / concat (frame accurate)

**Stream-copy trim (FAST, but cuts to keyframes only):**
```bash
uv run .claude/skills/ffmpeg-cut-concat/scripts/cut.py trim \
  --input source.mov --output cut.mov --start 00:01:30 --end 00:02:45 \
  --copy
```

**Re-encode trim (frame-accurate):**
```bash
uv run .claude/skills/ffmpeg-cut-concat/scripts/cut.py trim \
  --input source.mov --output cut.mov --start 00:01:30.5 --end 00:02:45.25
```

**Concat multiple clips:**
```bash
# Same codec + container: use concat demuxer (no re-encode)
uv run .claude/skills/ffmpeg-cut-concat/scripts/cut.py concat-copy \
  --inputs "clip1.mov,clip2.mov,clip3.mov" --output joined.mov

# Different codecs: use concat filter (re-encode)
uv run .claude/skills/ffmpeg-cut-concat/scripts/cut.py concat-filter \
  --inputs "clip1.mp4,clip2.mov,clip3.mkv" --output joined.mp4
```

### 4. Color grade

**LUT-based (camera LUT + creative LUT):**
```bash
uv run .claude/skills/ffmpeg-lut-grade/scripts/lut.py apply \
  --input log-footage.mov --lut "Alexa_LogC_to_Rec709.cube" --output rec709.mov
```

**OCIO / ACES:**
```bash
export OCIO=/opt/aces/config.ocio
uv run .claude/skills/ffmpeg-ocio-colorpro/scripts/ociogo.py transform \
  --input source.mov --output graded.mov \
  --from "Input - ARRI - LogC (v3-EI800) - Wide Gamut" \
  --to "Output - Rec.709"
```

**Manual color adjustments (curves/saturation/etc.):**
```bash
ffmpeg -i ungraded.mov \
  -vf "eq=contrast=1.05:brightness=-0.01:saturation=1.1:gamma=0.95, \
       curves=preset=increase_contrast, \
       colorbalance=rs=.1:gs=0:bs=-.05" \
  graded.mov
```

### 5. Stabilize shaky handheld shots

**2-pass vid.stab (best quality):**
```bash
uv run .claude/skills/ffmpeg-stabilize/scripts/stabilize.py 2pass \
  --input shaky.mov --output stable.mov \
  --shakiness 5 --accuracy 15 --stepsize 6 --mincontrast 0.3
```

**Single-pass deshake (faster, lesser quality):**
```bash
ffmpeg -i shaky.mov -vf "deshake=edge=3:rx=32:ry=32" deshaken.mov
```

### 6. Denoise

**Classical nlmeans (best for film grain / low-ISO):**
```bash
ffmpeg -i noisy.mov -vf "nlmeans=s=4:p=7:r=15" denoised.mov
```

**bm3d (heavier, preserves detail):**
```bash
ffmpeg -i noisy.mov -vf "bm3d=sigma=3:block=4:bstep=2" denoised.mov
```

**hqdn3d (fast, general):**
```bash
ffmpeg -i noisy.mov -vf "hqdn3d=4:3:6:4.5" denoised.mov
```

For heavier AI denoise, use `media-denoise-ai` from the AI-enhancement workflow.

### 7. Scale / crop / aspect changes

**Scale to 1080p maintaining aspect:**
```bash
ffmpeg -i 4k.mov -vf "scale=-2:1080" 1080p.mov
```

**Crop letterbox (auto-detect):**
```bash
# Detect black bars
uv run .claude/skills/ffmpeg-detect/scripts/detect.py crop \
  --input widescreen.mov --duration 30s
# → Returns crop=1920:816:0:132

ffmpeg -i widescreen.mov -vf "crop=1920:816:0:132" cropped.mov
```

**16:9 → 9:16 vertical (TikTok / Shorts):**
```bash
uv run .claude/skills/ffmpeg-video-filter/scripts/vfilter.py vertical-crop \
  --input landscape.mov --output vertical.mov \
  --mode subject-center
```

### 8. Speed + time manipulation

```bash
# Slow down 2x
ffmpeg -i source.mov -vf "setpts=2.0*PTS" -af "atempo=0.5" slow.mov

# Speed up 2x
ffmpeg -i source.mov -vf "setpts=0.5*PTS" -af "atempo=2.0" fast.mov

# Motion-interpolated slow-mo (smooth)
uv run .claude/skills/ffmpeg-speed-time/scripts/timefx.py minterpolate \
  --input 30fps.mov --output 60fps-smooth.mov --target-fps 60

# Freeze on a specific frame
uv run .claude/skills/ffmpeg-speed-time/scripts/timefx.py freeze \
  --input source.mov --output with-freeze.mov \
  --timestamp 00:00:15 --duration 3

# Reverse
ffmpeg -i source.mov -vf reverse -af areverse reversed.mov
```

### 9. Chromakey / greenscreen

```bash
uv run .claude/skills/ffmpeg-chromakey/scripts/chromakey.py key \
  --foreground green-screen.mov --background backdrop.mov \
  --output composited.mov \
  --color 00FF00 --similarity 0.2 --blend 0.1
```

For hairy edges, spill suppression:
```bash
ffmpeg -i fg.mov -i bg.mov -filter_complex "\
  [0]chromakey=0x00FF00:0.2:0.1[keyed]; \
  [keyed]despill=type=green:mix=0.5[despilled]; \
  [1][despilled]overlay" composited.mov
```

### 10. Text overlays / lower thirds

```bash
ffmpeg -i source.mov \
  -vf "drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc: \
       text='Live from Tokyo':x=40:y=h-80:fontsize=36:fontcolor=white: \
       box=1:boxcolor=black@0.6:boxborderw=10" \
  with-text.mov
```

Or as a sidecar ASS subtitle (more styling control):
```bash
ffmpeg -i source.mov -vf "ass=lower-thirds.ass" with-text.mov
```

### 11. Subtitles

```bash
# Soft-mux
uv run .claude/skills/ffmpeg-subtitles/scripts/subs.py mux \
  --video source.mp4 --subs eng.srt --language eng --output captioned.mp4

# Burn-in
uv run .claude/skills/ffmpeg-subtitles/scripts/subs.py burnin \
  --video source.mp4 --subs eng.srt --output burnt.mp4

# Extract
uv run .claude/skills/ffmpeg-subtitles/scripts/subs.py extract \
  --input captioned.mp4 --output eng.srt --stream 0:s:0
```

### 12. Audio finishing

```bash
# EQ + compression
ffmpeg -i source.mov \
  -af "highpass=f=80, \
       equalizer=f=3000:w=1:g=3, \
       acompressor=threshold=-20dB:ratio=3:attack=200:release=1000" \
  -c:v copy finished-audio.mov

# Loudness normalize
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input finished-audio.mov --output final.mov --target -14
```

### 13. Thumbnails + sprite sheets

```bash
# Every 10 seconds → thumbnail
uv run .claude/skills/ffmpeg-frames-images/scripts/frames.py extract \
  --input source.mov --output "thumbs/%03d.jpg" --interval 10

# Sprite sheet for video scrubbing UI
uv run .claude/skills/ffmpeg-frames-images/scripts/frames.py sprite-sheet \
  --input source.mov --output sprite.jpg --cols 10 --rows 10 --width 160

# Animated GIF preview
uv run .claude/skills/ffmpeg-frames-images/scripts/frames.py gif \
  --input source.mov --output preview.gif --start 5 --duration 3 --width 640
```

### 14. Chapters + metadata

```bash
uv run .claude/skills/ffmpeg-metadata/scripts/metadata.py add-chapters \
  --input source.mov --output chaptered.mov \
  --chapters-file chapters.txt

# Cover art
uv run .claude/skills/ffmpeg-metadata/scripts/metadata.py cover-art \
  --input chaptered.mov --output final.mov --image cover.jpg
```

### 15. Final delivery transcode

**YouTube / social:**
```bash
uv run .claude/skills/media-handbrake/scripts/hb.py preset \
  --input master.mov --output youtube.mp4 --preset "General/Fast 1080p30"
```

**Direct ffmpeg with modern settings:**
```bash
ffmpeg -i master.mov \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ac 2 \
  -movflags +faststart \
  deliverable.mp4
```

**AV1 for archival / bandwidth-conscious:**
```bash
ffmpeg -i master.mov \
  -c:v libsvtav1 -crf 28 -preset 6 -pix_fmt yuv420p10le \
  -c:a libopus -b:a 128k \
  deliverable.webm
```

### 16. QC before shipping

```bash
# Spec check
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full deliverable.mp4
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report --file deliverable.mp4

# Quality vs reference
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference master.mov --distorted deliverable.mp4 --json
```

### 17. Upload

```bash
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider youtube --file deliverable.mp4 --title "Episode 42"
```

---

## Variants

### Batch-process all wedding videos

```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob 'raw/wedding-*.mov' \
  --output-dir published/ \
  --jobs 4 \
  --command 'bash finish-wedding.sh {in} {out}'
```

### Programmatic assembly with MoviePy

```bash
# When ffmpeg's filtergraph gets too unwieldy, drop to Python
uv run .claude/skills/media-moviepy/scripts/mvp.py compose \
  --script assembly.py
```

Example `assembly.py`:
```python
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip

intro = VideoFileClip("intro.mov")
main = VideoFileClip("main.mov").subclip(10, 120)
outro = VideoFileClip("outro.mov")
title = TextClip("Episode 42", fontsize=60, color='white').set_duration(3)
final = concatenate_videoclips([intro, CompositeVideoClip([main, title.set_pos('bottom')]), outro])
final.write_videofile("output.mp4", codec="libx264")
```

### Vertical-format social cuts from landscape master

```bash
# Auto-crop with face tracking
uv run .claude/skills/ffmpeg-video-filter/scripts/vfilter.py vertical-crop \
  --input master.mov --output vertical.mov \
  --mode auto-track --aspect 9:16
```

### 360° VR edit

```bash
# 360 equirect → stereographic "little planet"
uv run .claude/skills/ffmpeg-360-3d/scripts/s3d.py v360 \
  --input 360.mov --output planet.mov \
  --from equirect --to stereographic
```

---

## Gotchas

- **`-movflags +faststart` is a SECOND pass.** The encoder runs, then ffmpeg rewinds and rewrites moov atom at file start. Adds time but necessary for progressive MP4.
- **`concat` demuxer requires identical codecs across inputs.** Different audio sample rates / video codecs / pixel formats → silent failure or subtle artifacts. Use `concat filter` if codecs differ.
- **`setpts=N*PTS` for slow-motion requires `-r` on input to match target.** Without `-r`, ffmpeg may drop/duplicate frames oddly.
- **`atempo` filter range is 0.5-2.0 per filter.** Chain them for more extreme speeds: `atempo=0.5,atempo=0.5` = 0.25x.
- **`yadif` has modes 0-3**: 0=single-rate (one field → one frame), 1=double-rate (two fields → two frames), 2=spatial-only (no temporal), 3=double-rate spatial. Most want mode=1.
- **`scale=-2:1080`** uses `-2` to keep aspect-ratio-preserving width divisible by 2 (required for yuv420p). `-1` does divisible by 1 (may fail encode).
- **`libx264 -pix_fmt yuv420p` is required for broadcast playback.** Many H.264 decoders don't do `yuv422p` / `yuv444p`.
- **`h264_nvenc` preset names differ from libx264**: `p1`-`p7` (not `ultrafast`-`placebo`). Higher number = higher quality, slower.
- **`h264_videotoolbox` is quality-preset only**: `-b:v` and `-q:v` are hints. Quality varies wildly — check with VMAF after.
- **`libsvtav1` `-preset` is 0-13 where 0 is slowest.** NOT 1-10 like libaom-av1.
- **`libvpx-vp9 -row-mt 1 -threads 4`** is required for multithreading — otherwise single-threaded by default.
- **`-shortest` stops encoding when shortest input ends.** Without it, looping `-loop 1 -i` inputs = infinite encode.
- **`-vf` and `-filter:v` are equivalent; `-vf` is shorter but the spelled-out form is clearer in scripts.**
- **Drawtext needs the exact font file path**, not a font name. On macOS: `/System/Library/Fonts/Helvetica.ttc`. On Linux: `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`.
- **ASS subtitles use `&HAABBGGRR`** (ARGB with AA=alpha, BGR order). Getting the byte order wrong = wrong color. See `ffmpeg-subtitles` gotchas.
- **`chromakey` works in RGB space.** For YUV sources, FFmpeg auto-converts, but precise keying wants `format=yuva420p` first for alpha.
- **vid.stab requires `--enable-libvidstab` in FFmpeg build.** Some Ubuntu stock builds lack it. Check: `ffmpeg -filters | grep vidstab`.
- **`atempo` alters audio pitch ONLY if you also use `asetrate`.** Pure `atempo` = speed change, no pitch change. Pure `asetrate` = pitch + speed together.
- **`-itsoffset` offsets input (pre-cut); `-ss` before `-i` seeks fast but may not be frame-accurate; `-ss` after `-i` seeks precisely but reads sequentially.** For frame-accurate cutting, `-ss` after `-i`.
- **`loudnorm` single-pass applies automatic limits; two-pass measures + applies precisely.** Use `media-ffmpeg-normalize` for guaranteed two-pass.
- **`-map 0:v:0 -map 0:a:0` selects only first video + first audio stream.** Default `-map 0` includes ALL streams.
- **HandBrake presets are opinionated.** "Fast 1080p30" means H.264 CRF 22 + AAC 160. Sometimes this is fine; sometimes it's wrong for your source.
- **Alpha channel preservation needs `-pix_fmt yuva420p` (or yuva444p) AND `-c:v qtrle` or `-c:v prores_ks -profile:v 4` (4444)**. H.264 doesn't support alpha.

---

## Example — "Raw 4K footage → finished 1080p YouTube video with LUT + captions + chapters"

```bash
#!/usr/bin/env bash
set -e

RAW_GLOB='raw/*.MP4'
EPISODE_NUM=42
OUT="published/episode-$EPISODE_NUM.mp4"

# 1. Transcode all raw clips to ProRes mezz
mkdir -p mezz
for f in $RAW_GLOB; do
  BASE=$(basename "$f" .MP4)
  ffmpeg -i "$f" -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -c:a pcm_s24le \
    "mezz/${BASE}.mov"
done

# 2. Concat mezz clips (same codec, safe)
printf "file '%s'\n" mezz/*.mov > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy joined.mov

# 3. Detect + apply crop (landscape letterbox)
CROP=$(uv run .claude/skills/ffmpeg-detect/scripts/detect.py crop \
  --input joined.mov --duration 60 | jq -r .crop)

# 4. Apply LUT + crop + scale
ffmpeg -i joined.mov \
  -vf "$CROP, lut3d=creative.cube, scale=-2:1080" \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
  -c:a copy graded.mov

# 5. Stabilize (if needed)
uv run .claude/skills/ffmpeg-stabilize/scripts/stabilize.py 2pass \
  --input graded.mov --output stable.mov --shakiness 5

# 6. Auto-transcribe
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input stable.mov --output captions.srt --model small.en --format srt

# 7. Soft-mux captions + loudness-normalize
ffmpeg -i stable.mov -i captions.srt \
  -map 0 -map 1 \
  -c copy -c:s mov_text \
  -af "loudnorm=I=-14:TP=-1:LRA=11" \
  tmp-with-captions.mp4

# 8. Chapter metadata from silence
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input tmp-with-captions.mp4 --threshold -30dB --min-duration 3 \
  --output chapters.txt --format ffmpeg-metadata

ffmpeg -i tmp-with-captions.mp4 -i chapters.txt \
  -map_metadata 1 -map_chapters 1 -c copy \
  tmp-with-chapters.mp4

# 9. Final H.264 + faststart
ffmpeg -i tmp-with-chapters.mp4 \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ac 2 \
  -c:s mov_text \
  -movflags +faststart \
  "$OUT"

# 10. QC
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference joined.mov --distorted "$OUT" --json

# 11. Upload
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider youtube --file "$OUT"

# Cleanup
rm -rf mezz joined.mov graded.mov stable.mov tmp-*.mp4 concat.txt captions.srt chapters.txt

echo "Published: $OUT"
```

---

## Further reading

- [`editorial-interchange.md`](editorial-interchange.md) — bringing the edit in from an NLE
- [`podcast-pipeline.md`](podcast-pipeline.md) — audio-specific polish
- [`ai-enhancement.md`](ai-enhancement.md) — AI-assisted restoration
- [`analysis-quality.md`](analysis-quality.md) — QC and metric validation
- [`streaming-distribution.md`](streaming-distribution.md) — delivery protocols for VOD
