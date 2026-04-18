# HandBrake CLI — reference

Deep reference for `HandBrakeCLI`. The SKILL.md has the "how to use it" narrative. This file is the "why / which knob" catalog — preset catalog, per-encoder options, filters, audio/sub rules, JSON spec, decision matrix, and the recipe book.

Tested against HandBrake 1.6 / 1.7 / 1.8.

---

## 1. Built-in preset catalog

`HandBrakeCLI --preset-list` prints exactly what your build ships. The groupings below are stable across 1.6–1.8:

### General

| Preset | Resolution cap | Video | Audio | Use for |
|--------|----------------|-------|-------|---------|
| `Very Fast 480p30` / `720p30` / `1080p30` | as named | x264, CRF 22, preset `veryfast` | AAC 128 kbps | quick-and-dirty |
| `Fast 480p30` / `720p30` / `1080p30` | as named | x264, CRF 22, preset `fast` | AAC 160 kbps | everyday conversion |
| `HQ 480p30 Surround` / `720p30 Surround` / `1080p30 Surround` | as named | x264, CRF 20, preset `slow` | AAC+AC3 surround | high quality |
| `Super HQ 480p30 Surround` / `720p30 Surround` / `1080p30 Surround` | as named | x264, CRF 18, preset `slower` | AAC+AC3 surround | near-lossless |

### Web

- `Creator 1080p60` / `720p60` — x264, optimized for content creators uploading to platforms.
- `Discord Nitro Small 480p30` / `540p30` — low-bitrate presets sized for Discord's 8 MB / 50 MB limits.
- `Gmail Large 3 Minutes 720p30` / `Gmail Medium 5 Minutes 480p30` / `Gmail Small 5 Minutes 288p30` — Gmail 25 MB attachment limits.
- `Social 25 MB 5 Minutes 720p30` / `10 Minutes 540p30` / `2 Minutes 1080p30` — generic social-media size targets.
- `Vimeo YouTube HQ 1080p60` / `720p60` / `4K 60` / `4K 50`.
- `YouTube 4K 60` / `1080p60` / `720p60` — YouTube upload-friendly.

### Devices

- `iPhone and iPod touch`, `iPad` — H.264, max 1080p30, broad Apple compatibility.
- `Apple 240p30` through `Apple 2160p60 4K HEVC Surround` — HEVC on Apple Silicon / Apple TV 4K; uses VideoToolbox on macOS.
- `Android`, `Android Tablet` — H.264 baseline/main.
- `Chromecast 1080p60 Surround`.
- `Amazon Fire 720p30` / `1080p30`.
- `Playstation 1080p30 Surround` / `720p30`, `Xbox Legacy 1080p30`, `Roku 1080p30 Surround` / `2160p60 4K HEVC Surround`.

### Matroska (MKV)

- `H.264 MKV 480p30` / `720p30` / `1080p30` / `2160p60 4K`.
- `H.265 MKV 480p30` / `720p30` / `1080p30` / `2160p60 4K`.
- `VP9 MKV 480p30` / `720p30` / `1080p30` / `2160p60 4K`.
- `AV1 MKV 480p30` / `720p30` / `1080p30` / `2160p60 4K` (1.7+, SVT-AV1).

### Production

- `Production Standard`, `Production Max`, `Production Proxy` — intended for post pipelines, high quality, constrained CRF.

### Hardware (Apple Silicon / Windows NVIDIA / Intel QSV)

Newer builds add `QuickSync H.265 2160p60 4K`, `NVENC H.265 2160p60 4K`, `VideoToolbox H.265 2160p60 4K`, etc. Verify with `--preset-list` — availability depends on your platform.

---

## 2. Encoder options by backend

### x264 / x264_10bit (`-e x264`)

| Flag | Values | Notes |
|------|--------|-------|
| `-q N` | 0–51 (float OK) | CRF; lower = higher quality. Typical 18–28, default 22. |
| `-b N` | kbps | Average bitrate (use with `-2` for 2-pass). |
| `--encoder-preset` | ultrafast … placebo | Speed/compression tradeoff. Default `veryfast`. |
| `--encoder-tune` | film, grain, animation, psnr, ssim, fastdecode, zerolatency, stillimage | `film` = live-action, `grain` = preserve noise. |
| `--encoder-profile` | baseline, main, high, high10, high422, high444 | Compatibility vs features. |
| `--encoder-level` | 1.0 … 6.2 | Decoder level constraint. |
| `--encopts "key=val:key=val"` | raw x264 opts | e.g. `ref=5:bframes=8:me=umh`. |

### x265 / x265_10bit / x265_12bit (`-e x265`)

Same as x264 plus:

- `--encoder-profile main / main10 / main12 / mainstillpicture`.
- `--encoder-tune psnr / ssim / grain / fastdecode / zerolatency / animation`.
- Higher CPU cost; 10-bit is smaller at equal VMAF for most content.

### SVT-AV1 (`-e svt_av1`, 1.7+)

- `-q` 0–63, lower = better.
- `--encoder-preset` 0 (slow, best) … 13 (fast, worst). 8 is default.
- Requires a compatible HandBrake build.

### VP9 (`-e vp9`)

- `-q` 0–63, default 32.
- `--encoder-preset good / best / realtime`.
- Container: WebM or MKV.

### VideoToolbox (macOS, `-e vt_h264` / `vt_h265` / `vt_h265_10bit`)

- `-q` 0–100, **higher = better** (opposite of x264/x265).
- Much faster, slightly lower quality at same size.
- `--encopts "keyint=N:bframes=N:profile=main"`.

### NVENC (`-e nvenc_h264` / `nvenc_h265` / `nvenc_av1`)

- `-q` 0–51 (CRF-ish). Typical 18–24.
- `--encoder-preset` `fastest … slowest` (NVENC naming).
- `--encoder-tune hq / ll / ull / lossless`.

### QSV (`-e qsv_h264` / `qsv_h265` / `qsv_av1`)

- `-q` 1–51.
- `--encoder-preset veryfast … veryslow`.
- Platform: Intel iGPU / Arc.

### VCE / AMF (`-e vce_h264` / `vce_h265`)

- Windows + AMD.
- `-q` 1–51.

---

## 3. Filter options

### Deinterlace

- `-d default` — single-rate deinterlace via Decomb (safe default).
- `-d bob` — doubles frame rate (29.97i → 59.94p).
- `--comb-detect[=default]` — detect combing; if used together with `--deinterlace`, only deinterlaces when needed.
- `--detelecine[=default]` — reverse 3:2 pulldown (telecine → progressive).

### Denoise

- `--nlmeans=[preset]` with `ultralight / light / medium / strong`. `--nlmeans-tune film / grain / animation / tape / sprite`.
- `--hqdn3d=[preset]` with `ultralight / light / medium / strong`. Faster, less accurate.
- `--chroma-smooth=[preset]` — color-only denoise.

### Sharpen

- `--sharpen=[preset]=[tune]` — options `unsharp` or `lapsharp`; tunes `ultralight / light / medium / strong`.

### Color

- `--colorspace bt709 / bt2020 / smpte170m` — tag output color.
- `--comb-detect` has no color effect.
- HandBrake does **not** tone-map HDR→SDR well. For HDR use ffmpeg or libplacebo.

### Crop / resize

- `--crop-mode auto / none / custom` (1.7+; older uses `--no-loose-anamorphic` style).
- `--crop T:B:L:R` — manual crop (when `--crop-mode custom`).
- `-X W` max width, `-Y H` max height, `--width W`, `--height H`.
- `--auto-anamorphic` / `--non-anamorphic` / `--loose-anamorphic` / `--custom-anamorphic`.
- `--modulus 2|4|8|16` — force pixel alignment.
- `--rotate=angle=0|90|180|270:hflip=0|1`.

### Framerate

- `-r FPS` — target framerate.
- `--cfr` constant, `--pfr` peak (cap), `--vfr` variable.

---

## 4. Audio handling

Flag forms:

- `-a 1,2,3` — track indices to include (from `--scan` output).
- `-E av_aac,copy:ac3,copy:dts` — per-track encoders, positional.
- `-B 128,192,192` — per-track bitrate (kbps).
- `-6 stereo,5point1,5point1` — per-track mixdown.
- `-D 0,0,0` — per-track DRC value.
- `--gain 0,0,0` — per-track gain in dB.

### Passthrough rules

- `copy:ac3` / `copy:eac3` / `copy:dts` / `copy:dtshd` / `copy:truehd` / `copy:aac` / `copy:mp3` / `copy:flac` — requires source to already be that codec. Otherwise HandBrake falls through to `--audio-fallback` (default `av_aac`).
- `--audio-copy-mask aac,ac3,eac3,dts,dtshd,mp3,truehd,flac` — what codecs are allowed to pass through when `copy` is requested.
- `--audio-fallback av_aac | ac3` — what to encode to when passthrough isn't possible.

### Track selection shortcuts

- `--all-audio` — include every audio track.
- `--first-audio` — first track only.
- `--audio-lang-list en,es` — pick by language.

---

## 5. Subtitles

- `--all-subtitles` — pass every subtitle track through.
- `--first-subtitle` — first only.
- `--subtitle 1,2` — specific tracks.
- `--subtitle-lang-list en,es` — filter by language.
- `--subtitle-burned=N | none | scan` — burn track N in (pixels, destroys soft-sub); `scan` burns only if a "forced" track is found.
- `--subtitle-default=N | none` — mark track N as default on playback.
- `--subtitle-forced=N` — include only forced (foreign-language) segments from track N.
- `--srt-file a.srt,b.srt --srt-codeset UTF-8 --srt-offset 0 --srt-lang eng --srt-default 1 --srt-burn 0` — import external SRT.
- `--ssa-file a.ass ...` — import SSA/ASS (1.7+).
- Chapters: preserved by default; `--markers` enables; `--markers=chapters.csv` imports names.

---

## 6. JSON job spec

`--json` on input prints a scan JSON. To export a reproducible job, use the GUI to build it and export, or write your own. Structure (abridged):

```json
{
  "Version": { "Major": 14, "Minor": 0, "Micro": 0 },
  "Source": { "Path": "in.mkv", "Title": 1, "Range": { "Type": "chapter", "Start": 1, "End": 0 } },
  "Destination": {
    "File": "out.mp4",
    "Mux": "av_mp4",
    "Options": { "Optimize": true, "IpodAtom": false }
  },
  "Video": {
    "Encoder": "x264",
    "Quality": 20,
    "Preset": "slow",
    "Tune": "film",
    "Profile": "high",
    "Level": "4.1",
    "TwoPass": false
  },
  "Audio": {
    "AudioList": [
      { "Track": 1, "Encoder": "av_aac", "Bitrate": 128, "Mixdown": "stereo" }
    ]
  },
  "Subtitle": { "Search": { "Enable": false }, "SubtitleList": [] },
  "Filters": {
    "FilterList": [
      { "ID": 3, "Settings": { "mode": 0 } },
      { "ID": 12, "Settings": { "preset": "fast" } }
    ]
  }
}
```

Import with `--preset-import-file my_job.json`. Export an existing preset with `--preset-export=Name`.

---

## 7. HandBrake vs ffmpeg vs other wrappers — decision matrix

| Job | Use | Why |
|-----|-----|-----|
| Quick consumer transcode | HandBrake | Presets > flags. `-Z "Fast 1080p30"` done. |
| Apple device target | HandBrake | Apple preset family uses VideoToolbox, proven. |
| DVD / Blu-ray rip | HandBrake | `--title N`, `--main-feature`, chapter/sub handling. |
| 4K HDR → SDR for mobile | ffmpeg (`ffmpeg-hdr-color` skill) | HandBrake lacks good tone mapping. |
| MXF / IMF broadcast delivery | ffmpeg (`ffmpeg-mxf-imf` skill) | HandBrake can't write MXF. |
| HLS / DASH packaging | ffmpeg or Shaka | HandBrake outputs single files only. |
| DRM-encrypted packaging | Shaka Packager (`media-shaka`) | Widevine / FairPlay / PlayReady. |
| Complex filter graphs | ffmpeg | HandBrake's filter set is limited. |
| Live streaming / WHIP / RTMP | ffmpeg (`ffmpeg-streaming`, `ffmpeg-whip`) | HandBrake is VOD only. |
| Stream copy (no re-encode) | ffmpeg / mkvmerge | HandBrake always re-encodes video. |
| Batch re-encode a folder | HandBrake CLI or `media-batch` + HandBrake | Presets keep results consistent. |
| Chapter edit without re-encode | `media-mkvtoolnix` or `ffmpeg-metadata` | HandBrake re-encodes. |

---

## 8. Recipe book

### 8.1 Rip DVD to MKV, preserve title structure

```bash
# Scan titles first
HandBrakeCLI -i /Volumes/DVD --scan -t 0 2>&1 | grep -E "title|duration"

# Rip main feature
HandBrakeCLI -i /Volumes/DVD --main-feature \
  -o movie.mkv -Z "H.264 MKV 1080p30" \
  --all-audio -E copy:ac3,av_aac --audio-copy-mask ac3,dts,eac3,aac,mp3 \
  --all-subtitles --subtitle-default=1 --markers
```

### 8.2 4K HDR → 1080p SDR for phones (hand off HDR → ffmpeg)

HandBrake can't tonemap well. Do the tone-map in ffmpeg first, then feed to HandBrake.

```bash
# Pass 1: HDR → SDR intermediate (ffmpeg, see ffmpeg-hdr-color skill)
ffmpeg -i hdr.mkv -vf "zscale=t=linear:npl=100,format=gbrpf32le,\
tonemap=tonemap=hable:desat=0,\
zscale=p=bt709:t=bt709:m=bt709:r=tv,format=yuv420p" \
  -c:v prores_ks -profile:v 3 -c:a copy sdr_intermediate.mov

# Pass 2: HandBrake finishes the encode with its preset system
HandBrakeCLI -i sdr_intermediate.mov -o out.mp4 \
  -Z "Fast 1080p30" --optimize
```

### 8.3 Anime that MUST preserve grain / line-art

```bash
HandBrakeCLI -i episode.mkv -o episode.mp4 \
  -e x265_10bit -q 19 \
  --encoder-preset slow --encoder-tune animation \
  --encopts "aq-mode=3:aq-strength=0.8:psy-rd=1.0:psy-rdoq=1.0" \
  --all-subtitles --subtitle-default=1 \
  --optimize
```

`animation` tune protects flat regions; `aq-mode=3` is better for anime's flat colors.

### 8.4 Archival MKV (keep everything, re-encode video to HEVC 10-bit)

```bash
HandBrakeCLI -i master.mkv -o archive.mkv \
  -e x265_10bit -q 18 --encoder-preset slower --encoder-tune film \
  --all-audio -E copy:ac3,copy:dts,copy:truehd,av_aac \
  --audio-copy-mask ac3,eac3,dts,dtshd,truehd,aac,mp3,flac \
  --all-subtitles --markers \
  --colorspace bt709
```

### 8.5 Broadcast camera footage with mixed interlacing (detect + deinterlace only when needed)

```bash
HandBrakeCLI -i broadcast.mxf -o out.mp4 \
  --comb-detect --deinterlace default \
  --detelecine default \
  -Z "HQ 1080p30 Surround"
```

### 8.6 Auto-crop letterbox, keep original aspect, maximum compatibility

```bash
HandBrakeCLI -i letterboxed.mkv -o cropped.mp4 \
  --crop-mode auto --auto-anamorphic \
  -Z "Fast 1080p30" --optimize
```

### 8.7 Force specific resolution without aspect distortion

```bash
HandBrakeCLI -i source.mkv -o 720p.mp4 \
  -Z "Fast 1080p30" -X 1280 -Y 720 --non-anamorphic --modulus 2
```

### 8.8 Web-distribution preset (Discord 50 MB in < 5 min)

```bash
HandBrakeCLI -i clip.mp4 -o discord.mp4 \
  -Z "Discord Nitro Small 540p30" --optimize
```

### 8.9 Reproducible encode via exported JSON

```bash
# Build a preset once in the GUI, export, then:
HandBrakeCLI --preset-import-file my_preset.json \
  -Z "My Custom Preset" -i in.mkv -o out.mp4
```

### 8.10 Batch a folder with the Python helper

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py batch \
  --indir ~/Videos/raw --outdir ~/Videos/out \
  -Z "Fast 1080p30" --optimize --2pass
```

---

## 9. Cheatsheet

```text
-i IN          input file / device
-o OUT         output file
-Z "Name"      built-in preset
-e CODEC       video encoder (x264, x265, vt_h264, nvenc_h265, svt_av1, …)
-q N           CRF / quality (encoder-specific scale)
-b N           bitrate kbps (with -2 for 2-pass)
-2             2-pass
--optimize     web-friendly MP4 (moov first)
-X W / -Y H    max width / height
--crop-mode auto|none|custom [--crop T:B:L:R]
-d default     deinterlace   --comb-detect  conditional
--nlmeans med  high-quality denoise
-a 1,2 -E av_aac,copy:ac3 -B 128,192
--all-subtitles --subtitle-burned=none --subtitle-default=1
--markers      chapters
--json         export scan info as JSON
--preset-list  list all presets
--preset-import-file  load a custom preset JSON
```
