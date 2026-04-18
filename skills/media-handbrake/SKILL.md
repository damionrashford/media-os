---
name: media-handbrake
description: >
  Video transcoding with HandBrake CLI (HandBrakeCLI): smart presets (Fast / HQ / Super HQ / Apple iPhone / iPad / Apple TV / Discord / YouTube), 2-pass encoding, automatic black-bar auto-crop, built-in denoise/deinterlace, queue batch, chapter preservation. Use when the user asks to transcode with HandBrake, use Apple device presets, do smart auto-crop encoding, build a reliable archival encode, batch convert with HandBrake, or use the official HandBrake presets.
argument-hint: "[preset] [input]"
---

# Media Handbrake

**Context:** $ARGUMENTS

HandBrake is an opinionated wrapper around libx264 / libx265 / libvpx / libaom / ffmpeg libs. Its value is preset quality — names like `"Fast 1080p30"` or `"Apple 2160p60 4K HEVC Surround"` encode thousands of hours of community tuning. Reach for HandBrake when you want a reliable, opinionated encode with minimal flags. Reach for raw ffmpeg when you need MXF, complex filtergraphs, or something HandBrake doesn't speak.

## Quick start

- **Just convert something:** → Step 2 → Step 3, preset `"Fast 1080p30"`.
- **For Apple devices:** → Step 3, preset `"Apple 1080p60 Surround"` or `"Apple 2160p60 4K HEVC Surround"`.
- **For Discord upload:** → Step 3, preset `"Discord Nitro Small 540p30"`.
- **Archival master:** → Step 3, preset `"Super HQ 1080p30 Surround"` with `-2` (2-pass).
- **Batch a folder:** → Examples → Batch.
- **Custom CRF encode:** → Step 3, `custom` subcommand.

## When to use

- You want presets, not flags. HandBrake > ffmpeg for "just transcode this well."
- You're targeting a consumer device (iPhone, iPad, Apple TV, Chromecast, Fire TV).
- You need dependable auto-crop of black bars and built-in deinterlace/denoise.
- You want 2-pass encoding with sane defaults in one flag (`-2`).
- You're ripping DVD/Blu-ray titles (`--title N`) or batch-converting a library.
- **Don't** use HandBrake for: MXF/IMF broadcast delivery, complex ffmpeg filter_complex graphs, HLS/DASH packaging, DRM, live streaming, bitstream filters. Use ffmpeg or the matching specialized skill.

## Step 1 — Install

```bash
# macOS
brew install handbrake           # provides HandBrakeCLI + HandBrake.app

# Linux (Debian/Ubuntu)
sudo apt install handbrake-cli

# Windows / official builds
# https://handbrake.fr/downloads2.php   (CLI tarball)

# Docker
docker run --rm -v "$PWD:/data" jrottenberg/handbrake \
  -i /data/in.mkv -o /data/out.mp4 -Z "Fast 1080p30"

# Verify
HandBrakeCLI --version
```

Python helper:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py check
```

## Step 2 — Pick a preset

List every built-in preset (categorized):

```bash
HandBrakeCLI --preset-list
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py list-presets
```

Categories you will see: **General** (Fast / HQ / Super HQ), **Web** (Creator / Discord / Gmail / Vimeo / YouTube), **Devices** (Apple / Android / Chromecast / Fire TV / Playstation / Roku / Xbox), **Matroska** (H.264/H.265 MKV), **Production** (Standard, Max, Proxy). Preset names include the resolution and frame cap, e.g. `"Fast 1080p30"` caps output at 1080p30 regardless of source.

Common go-tos:

| Goal | Preset |
|------|--------|
| Quick everyday H.264 MP4 | `"Fast 1080p30"` |
| High-quality H.264 MP4 | `"HQ 1080p30 Surround"` |
| Archival H.264 MKV | `"H.264 MKV 1080p30"` |
| Near-lossless master | `"Super HQ 1080p30 Surround"` |
| iPhone / iPad | `"iPhone and iPod touch"` / `"iPad"` |
| Apple TV 4K HDR | `"Apple 2160p60 4K HEVC Surround"` |
| Discord upload | `"Discord Nitro Small 540p30"` |
| YouTube master | `"YouTube 4K 60"` |

## Step 3 — Run

**Use a built-in preset (80% of real work):**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 -Z "Fast 1080p30"
```

**2-pass:**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 -Z "HQ 1080p30 Surround" -2
```

**Web-optimized MP4 (moov atom at head):**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 -Z "Fast 1080p30" --optimize
```

**Custom encode (x264 CRF 20, medium speed, film tune, AAC 128k, auto-crop, anamorphic, all subs, no burn-in):**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 \
  -e x264 -q 20 --encoder-preset medium --encoder-tune film \
  -B 128 -a 1 -E av_aac \
  --all-subtitles --subtitle-burned=none --subtitle-default=1 \
  --auto-anamorphic --crop-mode auto --optimize
```

**Target bitrate instead of CRF (`-b` kbps):**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 -e x264 -b 2500 -2
```

**Hardware encoders:**

```bash
# Apple VideoToolbox (macOS)
HandBrakeCLI -i in.mkv -o out.mp4 -e vt_h264 -q 65
HandBrakeCLI -i in.mkv -o out.mp4 -e vt_h265 -q 65

# NVIDIA
HandBrakeCLI -i in.mkv -o out.mp4 -e nvenc_h264 -q 22
HandBrakeCLI -i in.mkv -o out.mp4 -e nvenc_h265 -q 22

# Intel Quick Sync
HandBrakeCLI -i in.mkv -o out.mp4 -e qsv_h264 -q 22
```

**DVD rip (pick title):**

```bash
HandBrakeCLI -i /Volumes/DVD --title 1 -o movie.mp4 -Z "H.264 MKV 1080p30"
```

**Dry run (export job as JSON):**

```bash
HandBrakeCLI -i in.mkv -o out.mp4 -Z "Fast 1080p30" --json > job.json
```

**Python helper covers all of the above:**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py encode -i in.mkv -o out.mp4 -Z "Fast 1080p30" --2pass --optimize
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py custom -i in.mkv -o out.mp4 --encoder x264 --quality 20 --preset-name medium --tune film --audio-bitrate 128
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py apple -i in.mkv -o out.mp4 --device iphone
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py batch --indir ./mkvs --outdir ./mp4s -Z "Fast 1080p30"
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py inspect -i in.mkv --json
```

## Step 4 — Verify

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,bit_rate \
  -show_entries format=duration,size -of default=nk=0 out.mp4
```

For MP4 distribution, confirm fast-start:

```bash
ffprobe -v trace -i out.mp4 2>&1 | head -20 | grep -i moov
# "moov" should appear before "mdat"
```

Spot-check visually:

```bash
ffplay out.mp4
```

## Reference docs

- [`references/handbrake.md`](references/handbrake.md) — preset catalog, per-encoder flags, filter options, audio passthrough rules, JSON job spec, HandBrake-vs-ffmpeg decision matrix, recipe book (DVD, 4K-HDR→1080p-SDR, anime grain preservation, archival MKV).

## Gotchas

- HandBrake is a **wrapper** around libx264/libx265/libvpx/libaom/ffmpeg libs with opinionated defaults. It is **not** raw ffmpeg — most `-ffmpeg` flags are ignored. Presets encode thousands of hours of community wisdom; `-Z "Preset Name"` handles ~80% of real-world transcoding.
- **Preset names include resolution.** `"Fast 1080p30"` caps output at 1080p30 even if the source is 4K60. For 4K use `"H.265 MKV 2160p60"`, `"Apple 2160p60 4K HEVC Surround"`, or `"YouTube 4K 60"`.
- `-q` (CRF) scale depends on the encoder:
  - x264 / x265: 0–51, typical 18–28 (22 is default, lower = higher quality).
  - VP9 / AV1: 0–63.
  - VideoToolbox (vt_h264 / vt_h265): 0–100 (higher = higher quality, opposite of x264).
- `--encoder-preset` controls speed/compression tradeoff: `ultrafast | superfast | veryfast | faster | fast | medium | slow | slower | veryslow | placebo`. Slower = smaller/better.
- `--encoder-tune` options: `film` (live-action), `grain` (preserve noise/film grain), `animation` (cartoons/anime), `psnr`, `ssim`, `fastdecode`, `zerolatency`.
- `--crop-mode auto` scans black bars and crops — occasionally too aggressive (crops legitimate dark content). Override with `--crop-mode custom --crop T:B:L:R` or `--crop-mode none`.
- `--comb-detect` first runs detection and only deinterlaces if it sees combing. Safer than unconditional `-d default` on progressive sources.
- `--nlmeans medium --nlmeans-tune film` produces higher-quality denoise than ffmpeg's hqdn3d, but is significantly slower. Use `--hqdn3d` for a fast alternative.
- Audio `copy:ac3` only passes through if the **source** is ac3. If it isn't, HandBrake falls back to the configured fallback encoder (default `av_aac`). `--audio-copy-mask aac,ac3,eac3,dts,dtshd,mp3,truehd,flac` controls which formats are allowed to pass through.
- `-a 1,2,3 -E av_aac,copy:ac3,copy:dts` configures per-track codecs positionally.
- DVD/Blu-ray sources: `--title 0` scans all titles; `--title N` selects title N. `--main-feature` picks the longest title.
- `--optimize` is mandatory for Mac / web / streaming distribution — relocates the `moov` atom to the start so the file can play while downloading.
- Subtitles: `--all-subtitles` passes everything through; `--subtitle-burned=1` burns the first (for open captions / hard-subs); `--subtitle-default=1` marks the first as default for soft-sub playback; `--subtitle-forced=1` only includes forced (foreign-language) subs.
- Chapters are preserved by default on MKV/MP4. `--markers=chapters.csv` imports custom chapter names.
- `--json` outputs the full job spec for scripting / reproducibility. Feed a modified JSON back in with `--preset-import-file`.
- HandBrake produces **slightly larger** files at equal VMAF than hand-tuned ffmpeg — the defaults favor safety (broader compatibility, better decode on low-end hardware). That's a feature, not a bug.
- Newer HandBrake (1.7+) has SVT-AV1 presets (`"SVT-AV1 1080p30"`, `"SVT-AV1 10-bit 1080p30"`). Check `HandBrakeCLI --version` first.
- For broadcast/MXF/IMF workflows, **use ffmpeg directly.** HandBrake can't write MXF, do filter_complex graphs, or handle SMPTE 2110/2022.

## Examples

### Example 1: 4K MKV → iPhone-playable MP4

```bash
HandBrakeCLI -i movie.mkv -o movie.mp4 -Z "iPhone and iPod touch" --optimize
```

Result: 1080p H.264, AAC stereo, fast-start MP4, plays on every iPhone since the 6s.

### Example 2: Batch convert a directory of MKVs

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/handbrake.py batch \
  --indir ~/Videos/raw --outdir ~/Videos/encoded -Z "Fast 1080p30"
```

Walks `raw/` recursively, preserves subdirectory structure, skips already-existing outputs.

### Example 3: Anime that must preserve grain

```bash
HandBrakeCLI -i episode.mkv -o episode.mp4 \
  -e x265 -q 19 --encoder-preset slow --encoder-tune animation \
  --all-subtitles --subtitle-default=1 --optimize
```

### Example 4: 2-pass archival with 2500 kbps target

```bash
HandBrakeCLI -i master.mov -o archive.mp4 \
  -e x264 -b 2500 -2 --encoder-preset slow --optimize
```

## Troubleshooting

### Error: `Unknown preset: Fast 1080p30`

Cause: HandBrake too old, or typo in preset name.
Solution: `HandBrakeCLI --preset-list` and copy the exact name. Upgrade with `brew upgrade handbrake`.

### Error: `Failed to open output file`

Cause: Output directory does not exist, or insufficient permissions.
Solution: `mkdir -p $(dirname out.mp4)` before running; check write permissions.

### Output is unexpectedly small / low-quality

Cause: Preset capped resolution or framerate ("Fast 1080p30" is 1080p30, not 4K60).
Solution: Use a preset matching source resolution/fps, or a Production / Super HQ preset.

### Auto-crop removed content I wanted to keep

Cause: `--crop-mode auto` detected dark content as black bars.
Solution: `--crop-mode none` (no crop) or `--crop-mode custom --crop 0:0:0:0`.

### Audio passthrough silently re-encoded to AAC

Cause: Source codec not in `--audio-copy-mask`, or track codec doesn't match your `copy:<codec>` hint.
Solution: `--audio-copy-mask aac,ac3,eac3,dts,dtshd,mp3,truehd,flac` and ensure your `-E` token matches source.

### HDR looks washed out after encoding to SDR

Cause: HandBrake doesn't tone-map HDR→SDR well. That's an ffmpeg job.
Solution: Use the `ffmpeg-hdr-color` skill with zscale/tonemap, or libplacebo.
