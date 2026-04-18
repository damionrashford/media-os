# Codec deep reference

Per-encoder options, container compatibility, codec selection guide,
pixel-format / color cheat sheet. Consult from `SKILL.md` when tuning
beyond the default presets.

---

## 1. libx264 (H.264 / AVC)

The baseline "safe" video encoder. Plays everywhere. Mature, fast, good quality.

**Key options (as `-<flag>`):**

| Flag         | Typical values                                                        | Notes |
|--------------|-----------------------------------------------------------------------|-------|
| `-preset`    | `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium` (default), `slow`, `slower`, `veryslow`, `placebo` | Speed vs compression tradeoff. `medium` is the sweet spot; `slow` for archive. Avoid `placebo`. |
| `-tune`      | `film`, `animation`, `grain`, `stillimage`, `fastdecode`, `zerolatency` | `animation` for cartoons/anime; `grain` preserves film grain; `zerolatency` for live / capture. Omit if unsure. |
| `-profile:v` | `baseline`, `main`, `high` (default), `high10`, `high422`, `high444`  | `baseline` = ancient devices; `high` = normal; `high10` for 10-bit. |
| `-level:v`   | e.g. `3.0`, `3.1`, `4.0`, `4.1`, `4.2`, `5.1`                         | Caps resolution/bitrate/ref frames. Set when targeting hardware decoders (Blu-ray = 4.1, most phones ≤ 4.2). |
| `-crf`       | `0`–`51` (default `23`)                                               | Lower = higher quality. `0` = mathematically lossless. Sane range `18–28`. |
| `-b:v`       | e.g. `5M`                                                             | Target bitrate. Ignored when `-crf` is set unless also using `-maxrate`. |
| `-maxrate` + `-bufsize` | e.g. `-maxrate 6M -bufsize 12M`                             | Caps peak bitrate; required for streaming targets. `bufsize` ≈ 2× `maxrate`. |
| `-g`         | e.g. `120` (2s @ 60fps)                                               | GOP size. Shorter = better seeking + streaming; longer = better compression. |
| `-keyint_min`| same as `-g` usually                                                  | Minimum keyframe interval. |
| `-bf`        | `0`–`16` (default `3`)                                                | B-frames. |
| `-refs`      | `1`–`16`                                                              | Reference frames. |
| `-x264-params` | `key=val:key=val`                                                   | Raw libx264 params (e.g. `aq-mode=3:psy-rd=1.0,0.15`). |

**CRF rules of thumb:**

| Use case                     | CRF | Preset    |
|------------------------------|-----|-----------|
| Visually lossless archive    | 17–18 | `slow`    |
| High-quality web             | 20–22 | `medium`  |
| General web                  | 23 | `medium`  |
| Small files, OK quality      | 25–28 | `medium`  |
| Live/streaming (single-pass bitrate) | — | `veryfast` |

---

## 2. libx265 (HEVC / H.265)

Higher compression than H.264 (~30–50% smaller at same quality). Slower to encode.
Requires newer devices; needs `-tag:v hvc1` for Apple MP4.

**Key options:**

| Flag          | Typical values                                                       | Notes |
|---------------|----------------------------------------------------------------------|-------|
| `-preset`     | `ultrafast` … `placebo` (default `medium`)                           | Same scale as x264. |
| `-tune`       | `grain`, `animation`, `psnr`, `ssim`, `fastdecode`, `zerolatency`    | Fewer tunes than x264. |
| `-profile:v`  | `main`, `main10`, `main12`, `main444-10`                             | `main10` for 10-bit HDR. |
| `-crf`        | `0`–`51` (default `28`)                                              | Sane range `20–28`. `0` = lossless. |
| `-x265-params`| e.g. `profile=main10:aq-mode=3:bframes=8`                            | Raw params. |
| `-tag:v`      | `hvc1` (required for Apple MP4) or default `hev1`                    | — |

---

## 3. libsvtav1 (AV1 via SVT-AV1)

Modern AV1 encoder. Much faster than `libaom-av1`. Usually the right AV1 choice.

**Key options:**

| Flag       | Values      | Notes |
|------------|-------------|-------|
| `-preset`  | `0`–`13` (default `10` ffmpeg / `8` upstream) | Lower = slower + higher quality. `4–6` archive, `8–10` practical, `12+` realtime. |
| `-crf`     | `0`–`63` (default `35`)                       | Sane range `25–40`. Lower is higher quality. |
| `-b:v`     | bitrate target                                | Pick CRF OR bitrate. |
| `-svtav1-params` | `tune=0:film-grain=8:enable-overlays=1`  | Raw SVT params. `tune=0` favors PSNR, `tune=1` subjective (default recent). |
| `-g`       | e.g. `120`                                    | Keyframe interval. |
| `-pix_fmt` | `yuv420p10le` preferred                        | 10-bit is free quality boost in AV1. |

---

## 4. libaom-av1 (AV1 via libaom)

Reference encoder. Highest quality per bit but painfully slow. Only use for archive.

**Key options:**

| Flag        | Values      | Notes |
|-------------|-------------|-------|
| `-crf`      | `0`–`63` (default `32`)                       | Requires `-b:v 0` to activate constant-quality. |
| `-b:v`      | `0` for CRF mode; else target bitrate         | — |
| `-cpu-used` | `0`–`8` (default `1`)                         | Higher = faster + lower quality. `4–6` is practical. |
| `-aq-mode`  | `0` off, `1` variance (default), `2` complexity, `3` cyclic | — |
| `-row-mt`   | `1` enable                                    | Row-based threading; required for multicore. |
| `-tiles`    | e.g. `2x2`                                    | Columns × rows; enables parallel decode. |
| `-lag-in-frames` | up to `35`                                | Lookahead; quality boost. |

---

## 5. libvpx-vp9 (VP9)

Google's pre-AV1. Required for WebM on older browsers. Slower than AV1 SVT for similar quality.

**Key options:**

| Flag            | Values    | Notes |
|-----------------|-----------|-------|
| `-crf`          | `0`–`63`                                    | Needs `-b:v 0` for CRF mode. Sane range `24–37`. |
| `-b:v`          | `0` for CRF; else bitrate                    | — |
| `-cpu-used`     | `-8` … `8` (default `1`)                     | Higher = faster. `2` good default; `0–1` for archive. |
| `-row-mt`       | `1`                                          | Row threading; always set. |
| `-tile-columns` | `0`–`6`                                       | Parallelism; `2` for 1080p, `3–4` for 4K. Must be ≤ log2(width/64). |
| `-frame-parallel` | `1`                                        | — |
| `-lossless`     | `1`                                          | True lossless VP9 (not CRF 0). |
| `-deadline`     | `good` (default), `best`, `realtime`         | `good` + cpu-used controls speed. |

---

## 6. libopus (Opus audio)

Best modern general-purpose audio codec. Great for web (WebM) and MKV.
Native AAC / fdk-AAC are still better for MP4 targets.

**Key options:**

| Flag              | Values                                    | Notes |
|-------------------|-------------------------------------------|-------|
| `-b:a`            | `32k` voice → `160k` transparent stereo   | `96k` fine for most web video; `128k` hi-fi. |
| `-vbr`            | `on` (default), `off`, `constrained`      | Keep `on`. |
| `-application`    | `voip`, `audio` (default), `lowdelay`     | `voip` for speech, `audio` for music, `lowdelay` for live. |
| `-frame_duration` | `2.5`, `5`, `10`, `20` (default), `40`, `60` (ms) | Longer = better compression but more latency. |
| `-compression_level` | `0`–`10` (default `10`)                | Encoder effort; no bitstream cost. |

---

## 7. libfdk_aac (Fraunhofer AAC)

Highest-quality AAC encoder but non-free — most distributed ffmpeg binaries
lack it. Check `ffmpeg -encoders | grep fdk`.

**Key options:**

| Flag         | Values                                               | Notes |
|--------------|------------------------------------------------------|-------|
| `-b:a`       | e.g. `128k`                                           | Use CBR with fdk. |
| `-vbr`       | `1`–`5`                                               | Alternative VBR mode (mutually exclusive with `-b:a`). 4 ≈ 128k, 5 ≈ 192k. |
| `-profile:a` | `aac_low` (default), `aac_he`, `aac_he_v2`, `aac_ld`, `aac_eld` | Use `aac_he` (HE-AAC v1) for ≤ 64 kbps; `aac_he_v2` for ≤ 32 kbps stereo (parametric stereo). |
| `-afterburner` | `1` (default)                                       | Extra quality; leave on. |

---

## 8. aac (native FFmpeg AAC)

Shipped with every ffmpeg build. Quality is fine at ≥ 128 kbps stereo. Use this
by default unless you've verified libfdk_aac is available.

| Flag         | Values                       | Notes |
|--------------|------------------------------|-------|
| `-b:a`       | `128k` default, up to `320k` | CBR. |
| `-q:a`       | `0.1`–`2` roughly            | VBR quality. Uses `global_quality`; less predictable than `-b:a`. |
| `-aac_coder` | `twoloop` (default), `fast`  | `twoloop` = better; `fast` = faster. |
| `-profile:a` | `aac_low` (default), `mpeg2_aac_low` | Leave default. |

---

## 9. libvorbis (Vorbis in WebM/Ogg)

Legacy WebM audio. Prefer Opus.

| Flag    | Values                          | Notes |
|---------|---------------------------------|-------|
| `-q:a`  | `-1`–`10` (typical `3`–`7`)     | VBR quality. `4` ≈ 128 kbps. |
| `-b:a`  | e.g. `128k`                     | CBR-ish. |

---

## 10. flac

Lossless audio. Use for archival masters. Large files.

| Flag                    | Values        | Notes |
|-------------------------|---------------|-------|
| `-compression_level`    | `0`–`12` (default `5`) | Size only; lossless regardless. `8` is a good tradeoff. |

---

## 11. prores_ks (Apple ProRes)

Professional intermediate codec. Huge files, fast to decode, edit-friendly.

| Flag              | Values                                   | Notes |
|-------------------|------------------------------------------|-------|
| `-profile:v`      | `0` proxy, `1` lt, `2` standard, `3` hq, `4` 4444, `5` 4444xq | Bitrate increases with profile. |
| `-pix_fmt`        | `yuv422p10le` (0-3), `yuva444p10le` (4444 w/ alpha) | ProRes requires 10-bit. |
| `-vendor`         | `apl0`                                   | Identify as Apple encoder (some NLEs require this). |
| `-bits_per_mb`    | e.g. `8000`                               | Override automatic rate. Rarely needed. |

---

## Container → codec support matrix

| Container | Video                                    | Audio                                              | Subtitles         |
|-----------|------------------------------------------|----------------------------------------------------|-------------------|
| **MP4**   | H.264, HEVC (tag hvc1), AV1, MPEG-4, ProRes (some players) | AAC, ALAC, AC3, E-AC3, MP3, Opus (ffmpeg will warn) | mov_text only     |
| **MOV**   | H.264, HEVC, ProRes, DNxHD, MJPEG         | AAC, ALAC, PCM (any), AC3                          | mov_text          |
| **MKV**   | Any                                       | Any                                                 | SRT, ASS, PGS, VobSub, WebVTT |
| **WebM**  | VP8, VP9, AV1                             | Vorbis, Opus                                        | WebVTT             |
| **TS**    | H.264, HEVC, MPEG-2                       | AAC (ADTS), AC3, MP2                               | DVB, teletext     |
| **FLV**   | H.264, VP6, Sorenson                      | AAC, MP3                                            | —                  |

Flac in MP4 is "supported" (ISO/IEC 14496-12 via `fLaC` atom) but has poor
ecosystem support — use MKV. Opus in MP4 works but older Safari chokes.

---

## Codec choice guide

| Situation                              | Video       | Audio   | Container |
|----------------------------------------|-------------|---------|-----------|
| Default / web / social / mobile        | H.264       | AAC     | MP4       |
| Modern web with broad support          | H.264       | AAC     | MP4       |
| Smaller archive, Apple-compatible      | HEVC (`hvc1`) | AAC   | MP4       |
| Archive master / HDR                   | HEVC 10-bit or AV1 10-bit | FLAC | MKV |
| YouTube-class modern encode            | AV1 (SVT)   | Opus    | MP4 / MKV |
| Web with Chrome/Firefox/Android only   | VP9 or AV1  | Opus    | WebM      |
| Editing / NLE intermediate             | ProRes      | PCM     | MOV       |
| Live streaming RTMP                    | H.264 (zerolatency preset) | AAC | FLV→RTMP |
| HDR10 delivery                         | HEVC `main10`, `bt2020nc`, `smpte2084` | — | MP4 / MKV |
| Old phones, legacy hardware            | H.264 baseline profile | AAC-LC | MP4 |

---

## Pixel format + color cheat sheet

Set with `-pix_fmt` (input side may need `-color_primaries / -color_trc /
-colorspace / -color_range` tags).

| pix_fmt         | Bits | Chroma  | Typical use                         |
|-----------------|------|---------|-------------------------------------|
| `yuv420p`       | 8    | 4:2:0   | SDR web video, broadest support     |
| `yuvj420p`      | 8    | 4:2:0 full-range | JPEG-derived stills; convert to `yuv420p` for video |
| `yuv420p10le`   | 10   | 4:2:0   | HDR / banding-prone content (HEVC/AV1/VP9) |
| `yuv422p`       | 8    | 4:2:2   | Broadcast / ProRes proxy            |
| `yuv422p10le`   | 10   | 4:2:2   | ProRes 0–3                          |
| `yuva444p10le`  | 10   | 4:4:4 + alpha | ProRes 4444                   |
| `rgb24` / `gbrp`| 8    | 4:4:4   | Screen capture, RGB masters         |

**Color tag examples:**

| Space            | `-color_primaries` | `-color_trc` | `-colorspace` |
|------------------|--------------------|--------------|---------------|
| SDR Rec.709 (HD) | `bt709`            | `bt709`      | `bt709`       |
| SDR Rec.601 (SD PAL) | `bt470bg`      | `smpte170m`  | `smpte170m`   |
| SDR Rec.601 (SD NTSC)| `smpte170m`    | `smpte170m`  | `smpte170m`   |
| HDR10 PQ         | `bt2020`           | `smpte2084`  | `bt2020nc`    |
| HLG              | `bt2020`           | `arib-std-b67` | `bt2020nc`  |

Also set `-color_range tv` (limited, normal video) or `pc` (full, computer
graphics) when converting between JPEG-ish sources and video targets.

---

## Bitrate ballparks (H.264 @ CRF-equivalent quality)

| Resolution / fps | Low  | Medium | High |
|------------------|------|--------|------|
| 480p30           | 0.5M | 1.0M   | 2.0M |
| 720p30           | 1.5M | 3.0M   | 5.0M |
| 1080p30          | 3.0M | 6.0M   | 10M  |
| 1080p60          | 4.5M | 9.0M   | 15M  |
| 2160p30          | 12M  | 25M    | 50M  |
| 2160p60          | 18M  | 40M    | 80M  |

HEVC/AV1: roughly 0.5–0.7× these numbers at equivalent quality.
