---
name: ffmpeg-transcode
description: >
  Transcode video/audio between codecs and containers with ffmpeg (H.264, HEVC, AV1, VP9, ProRes, AAC, Opus; MP4, MKV, WebM, MOV). Use when the user asks to convert a video, change codec, re-encode, reduce file size with CRF, target a bitrate, do 2-pass encoding, change container, or make a file web/mobile/social-media compatible.
argument-hint: "[input] [target-format]"
---

# Ffmpeg Transcode

**Context:** $ARGUMENTS

## Quick start

- **Web MP4 (H.264 + AAC, most compatible):** → Step 3, recipe A
- **Change container only, keep codecs:** → Step 1 (remux path)
- **Smaller file at same quality (HEVC/AV1):** → Step 3, recipes B / C

## When to use

- User says "convert", "re-encode", "transcode", "change format", "make smaller".
- Target codec differs from source, OR target container doesn't support source codec.
- CRF / bitrate / 2-pass / preset tuning for size vs quality.
- For GPU encoding use `ffmpeg-hwaccel`; for trimming/joining use `ffmpeg-cut-concat`;
  for filters/scaling use `ffmpeg-video-filter`; for raw inspection use `ffmpeg-probe`.

## Step 1 — Pick container + codecs (and decide remux vs re-encode)

First probe the input:

```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name,pix_fmt,profile,channels,sample_rate -of json "$IN"
```

**Decision tree:**

1. If the user only wants a different container AND the source codecs are supported
   by the target container (see matrix below), **remux** — no quality loss, fast:
   ```bash
   ffmpeg -i in.mkv -c copy -map 0 out.mp4
   ```
   Caveats: H.264/HEVC in raw `.ts` vs `.mp4` need a bitstream filter — see
   `ffmpeg-bitstream`. AAC from `.ts` → `.mp4` needs `aac_adtstoasc`.
2. If codecs are incompatible with the target container (e.g. Opus → MP4 is
   technically allowed but fragile; FLAC → MP4 not allowed), re-encode that stream only.
3. Otherwise full re-encode — continue to Step 2.

**Container → codec compatibility matrix:**

| Container | Video codecs (common)              | Audio codecs (common)            | Subtitles        |
|-----------|------------------------------------|----------------------------------|------------------|
| MP4 / M4V | H.264, HEVC, AV1, MPEG-4           | AAC, ALAC, AC3, MP3 (avoid Opus) | mov_text only    |
| MOV       | H.264, HEVC, ProRes, DNxHD         | AAC, PCM, ALAC                   | mov_text         |
| MKV       | anything                           | anything                         | SRT/ASS/PGS/...  |
| WebM      | VP8, VP9, AV1 only                 | Vorbis, Opus only                | WebVTT           |

If unsure which codec to pick, default to **H.264 + AAC in MP4** — works on every
browser, every phone, every social platform.

## Step 2 — Choose rate control

Three modes, pick exactly one per video encode:

- **CRF (constant quality)** — best default. Pick a target quality; filesize varies
  with content. Use when output size doesn't have to be exact.
- **Bitrate target** — `-b:v 5M`. Single pass is fine for live/streaming targets;
  otherwise 2-pass is higher quality at the same size.
- **2-pass** — use when you must hit a specific size (e.g. Twitter 512MB, Discord 25MB).
  Two ffmpeg invocations; first pass writes stats to `ffmpeg2pass-*.log`.

**CRF typical ranges (NOT comparable across codecs):**

| Encoder      | Sane CRF range | Visually-lossless-ish | Notes                                     |
|--------------|----------------|-----------------------|-------------------------------------------|
| libx264      | 18–28 (default 23) | 17–18             | `-crf 0` = mathematically lossless        |
| libx265      | 20–28 (default 28) | 18–20             | `-crf 0` = lossless                        |
| libsvtav1    | 25–40 (default 35) | 20–25             | Higher numbers than x264 for same quality |
| libaom-av1   | 25–40 (set `-b:v 0 -crf N` for CRF) | 20–25 | Slow; prefer libsvtav1 |
| libvpx-vp9   | 24–37 (set `-b:v 0 -crf N`)          | 15–23 | Must pass `-b:v 0` to enable constant-quality |

**2-pass recipe (size-targeted):**

```bash
# Pass 1: analyse only, no audio, discard output
ffmpeg -y -i "$IN" -c:v libx264 -b:v 5M -preset medium \
       -pass 1 -an -f null /dev/null

# Pass 2: real encode, reuse stats
ffmpeg -i "$IN" -c:v libx264 -b:v 5M -preset medium \
       -pass 2 -c:a aac -b:a 128k \
       -movflags +faststart "$OUT"
```

Compute `-b:v` from a size budget: `bitrate_bps = target_size_bits / duration_seconds − audio_bps`.

## Step 3 — Build the command

**Recipe A — Web MP4 (default go-to):**

```bash
ffmpeg -i "$IN" \
  -c:v libx264 -preset medium -crf 20 \
  -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ac 2 \
  -movflags +faststart \
  "$OUT.mp4"
```

**Recipe B — HEVC in MKV (archive / smaller size):**

```bash
ffmpeg -i "$IN" \
  -c:v libx265 -preset medium -crf 22 \
  -pix_fmt yuv420p10le \
  -c:a libopus -b:a 128k \
  "$OUT.mkv"
```

Put HEVC in MP4 instead by adding `-tag:v hvc1` (Apple/QuickTime requires it).

**Recipe C — AV1 in MP4 (modern web / YouTube-style):**

```bash
ffmpeg -i "$IN" \
  -c:v libsvtav1 -preset 6 -crf 30 \
  -pix_fmt yuv420p10le \
  -c:a libopus -b:a 96k \
  -movflags +faststart \
  "$OUT.mp4"
```

(Use `-preset 4` for better quality / slower, `-preset 8` for faster / larger.)

**Recipe D — WebM (VP9 + Opus):**

```bash
ffmpeg -i "$IN" \
  -c:v libvpx-vp9 -b:v 0 -crf 32 -row-mt 1 -cpu-used 2 \
  -pix_fmt yuv420p \
  -c:a libopus -b:a 96k \
  "$OUT.webm"
```

**Recipe E — ProRes for editing (MOV):**

```bash
ffmpeg -i "$IN" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -c:a pcm_s16le \
  "$OUT.mov"
```

Profiles: 0=proxy, 1=lt, 2=standard, 3=hq, 4=4444, 5=4444xq.

**Stream selection (`-map`):**

```bash
# Keep video 0 + audio 1 only, drop all subs:
ffmpeg -i "$IN" -map 0:v:0 -map 0:a:1 -c:v libx264 -crf 20 -c:a aac "$OUT"
# Preserve all streams + copy metadata + copy chapters:
ffmpeg -i "$IN" -map 0 -map_metadata 0 -map_chapters 0 -c copy "$OUT"
```

**Preset runner:**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/transcode.py \
  --input "$IN" --output "$OUT" --preset web-mp4
```

Presets: `web-mp4` (H.264/AAC MP4), `hevc-mkv`, `web-webm`, `av1-mp4`, `prores`, `archive`.

## Step 4 — Verify output

```bash
ffprobe -v error -show_format -show_streams -of json "$OUT" | jq '.format.duration, .streams[].codec_name'
```

Check:
- Duration roughly matches input (within ~0.1s, short container padding is normal).
- Video `codec_name` + audio `codec_name` are what you asked for.
- `pix_fmt` is `yuv420p` if you need browser/phone playback.
- For MP4: `ffprobe -v trace ... 2>&1 | head | grep moov` should show moov atom early
  (or simply: the file starts playing instantly in a browser = faststart worked).

## Gotchas

- **`yuv420p` is required** for broad playback (browsers, iOS, most TVs). ProRes captures
  and RGB sources often land on `yuv444p`/`yuv422p` — always add `-pix_fmt yuv420p`
  for web output, or `yuv420p10le` for 10-bit HDR-ish HEVC/AV1.
- **`-movflags +faststart` is MP4/MOV only.** Does nothing for MKV/WebM. Without it,
  web players have to download the whole file before playback starts.
- **Stream copy across containers may need a bitstream filter** (e.g. H.264 MP4 → TS,
  AAC TS → MP4). See the `ffmpeg-bitstream` skill.
- **CRF values are NOT comparable across codecs.** x264 crf 23 ≠ x265 crf 23 ≠ av1 crf 23.
  Use the table in Step 2.
- **`-crf 0` is lossless only for libx264 / libx265.** For AV1 / VP9 it's the best-quality
  CRF value but still lossy. For true lossless VP9 use `-lossless 1`.
- **`-b:v` is ignored when `-crf` is set** on libx264/libx265 unless you also pass
  `-maxrate`/`-bufsize` (then CRF becomes a capped-CRF ceiling). Pick one mode.
- **Audio must be re-encoded when container doesn't support source codec** — e.g. Opus
  in MP4 is shaky, FLAC in MP4 is unsupported, AAC in WebM is unsupported.
  Re-encode the audio even if you're copying video: `-c:v copy -c:a aac -b:a 128k`.
- **HEVC in MP4 needs `-tag:v hvc1`** to play on Apple QuickTime / Safari / iOS.
- **2-pass requires matching `-b:v` and `-preset` between the two passes.** Stats log
  is per-working-directory — run both passes from the same cwd.
- **libfdk_aac is non-free** and absent from most ffmpeg builds. Use the native `aac`
  encoder unless you know your build has fdk.

## Examples

### Example 1: "Make this MOV playable in browsers"

```bash
ffmpeg -i in.mov -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
       -c:a aac -b:a 128k -movflags +faststart out.mp4
```

### Example 2: "Shrink a 4GB recording for Discord (25MB cap)"

Duration 10 min = 600s. Budget: 25 MB × 8 / 600s ≈ 333 kbps total. Reserve 64k audio,
leave 260k video. 2-pass mandatory at that ratio:

```bash
ffmpeg -y -i in.mp4 -c:v libx264 -b:v 260k -preset slow -pass 1 -an -f null /dev/null
ffmpeg    -i in.mp4 -c:v libx264 -b:v 260k -preset slow -pass 2 \
          -c:a aac -b:a 64k -ac 1 -movflags +faststart out.mp4
```

### Example 3: "Change MKV container to MP4 without re-encoding"

```bash
ffprobe in.mkv            # confirm codecs are H.264/HEVC + AAC/AC3
ffmpeg -i in.mkv -c copy -map 0 -movflags +faststart out.mp4
```

If subtitle streams are SRT/ASS, add `-map 0:v -map 0:a` to drop them (MP4 only takes
mov_text) or add `-c:s mov_text` to convert.

### Example 4: "Archive master to HEVC 10-bit"

```bash
ffmpeg -i master.mov -c:v libx265 -preset slow -crf 18 -pix_fmt yuv420p10le \
       -x265-params "profile=main10" \
       -c:a flac -compression_level 8 archive.mkv
```

## Troubleshooting

### Error: `Could not find tag for codec opus in stream #1, codec not currently supported in container`

Cause: Opus audio in MP4 isn't universally supported by ffmpeg's MP4 muxer.
Solution: Use MKV/WebM, or re-encode audio to AAC: `-c:a aac -b:a 128k`.

### Error: `[libx264 @ ...] height not divisible by 2`

Cause: libx264 with yuv420p requires even dimensions.
Solution: Add `-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"` or an explicit even target.

### Output plays but browsers won't start until fully downloaded

Cause: moov atom at end of MP4.
Solution: Add `-movflags +faststart`. (MP4/MOV only.)

### Output has green / purple tint on iOS

Cause: `yuv444p` or `yuv422p` pixel format.
Solution: Add `-pix_fmt yuv420p`.

### HEVC MP4 won't play on Apple devices

Cause: tag is `hev1` instead of `hvc1`.
Solution: Re-mux with `ffmpeg -i in.mp4 -c copy -tag:v hvc1 out.mp4`.

### "Unknown encoder 'libfdk_aac'"

Cause: build doesn't include non-free fdk.
Solution: Swap `libfdk_aac` → `aac` (native encoder is fine for ≥128 kbps stereo).

## Reference docs

- Deep per-encoder options (presets, tunes, profiles, levels, AV1/VP9 tile options,
  Opus application modes, pixel-format & color cheat sheet) → `references/codecs.md`.
