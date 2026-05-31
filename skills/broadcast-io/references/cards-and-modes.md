# DeckLink cards, display modes, and pixel-format cheat sheet

Loaded on demand when a user asks "which card should I buy?" or "what
modes does my card support?" or needs a four-CC table.

## Common DeckLink cards and their ceiling

| Card | Interface | Max video | Notes |
|---|---|---|---|
| DeckLink Mini Recorder 4K | TB3 | UHD 4K 30p / 1080p60 | Capture only (SDI+HDMI inputs) |
| DeckLink Mini Monitor 4K | TB3 | UHD 4K 30p | Playback only |
| DeckLink Studio 4K | PCIe | UHD 4K 30p | Half/full duplex, 4x SDI |
| DeckLink 4K Pro | PCIe | UHD 4K 60p (12G) | 4x SDI, reference input |
| DeckLink 8K Pro | PCIe | 8K 60p | 4x 12G-SDI, quad-link 8K |
| DeckLink Quad HDMI Recorder | PCIe | 4x 1080p60 HDMI | Multi-camera capture |
| UltraStudio Mini Recorder/Monitor | TB2/TB3 | HD only | Mobile capture/playback |
| UltraStudio 4K Mini | TB3 | UHD 4K 30p | Portable 4K |
| UltraStudio 4K Extreme | TB3 | UHD 4K 60p | Fastest TB3 |

## Display-mode four-CC table (BMDDisplayMode)

These strings double as ffmpeg `-format_code` arguments.

| Four-CC | Mode | Width x Height | Rate |
|---|---|---|---|
| `ntsc` | NTSC SD interlaced | 720 x 486 | 29.97i |
| `nt23`| NTSC 23.98 PsF | 720 x 486 | 23.98 |
| `pal ` | PAL SD interlaced | 720 x 576 | 25i |
| `hp59` | HD 720p 59.94 | 1280 x 720 | 59.94 |
| `hp60` | HD 720p 60 | 1280 x 720 | 60 |
| `hp50` | HD 720p 50 | 1280 x 720 | 50 |
| `Hp23` | HD 1080p 23.98 | 1920 x 1080 | 23.98 |
| `Hp24` | HD 1080p 24 | 1920 x 1080 | 24 |
| `Hp25` | HD 1080p 25 | 1920 x 1080 | 25 |
| `Hp29` | HD 1080p 29.97 | 1920 x 1080 | 29.97 |
| `Hp30` | HD 1080p 30 | 1920 x 1080 | 30 |
| `Hp50` | HD 1080p 50 | 1920 x 1080 | 50 |
| `Hp59` | HD 1080p 59.94 | 1920 x 1080 | 59.94 |
| `Hp60` | HD 1080p 60 | 1920 x 1080 | 60 |
| `Hi50` | HD 1080i 50 | 1920 x 1080 | 25i |
| `Hi59` | HD 1080i 59.94 | 1920 x 1080 | 29.97i |
| `Hi60` | HD 1080i 60 | 1920 x 1080 | 30i |
| `2k23` | 2K DCI 23.98p | 2048 x 1080 | 23.98 |
| `2k24` | 2K DCI 24p | 2048 x 1080 | 24 |
| `2k25` | 2K DCI 25p | 2048 x 1080 | 25 |
| `4k23` | UHD 4K 23.98p | 3840 x 2160 | 23.98 |
| `4k24` | UHD 4K 24p | 3840 x 2160 | 24 |
| `4k25` | UHD 4K 25p | 3840 x 2160 | 25 |
| `4k29` | UHD 4K 29.97p | 3840 x 2160 | 29.97 |
| `4k30` | UHD 4K 30p | 3840 x 2160 | 30 |
| `4k50` | UHD 4K 50p | 3840 x 2160 | 50 |
| `4k59` | UHD 4K 59.94p | 3840 x 2160 | 59.94 |
| `4k60` | UHD 4K 60p | 3840 x 2160 | 60 |
| `4d23` | 4K DCI 23.98p | 4096 x 2160 | 23.98 |
| `8k23` | 8K UHD 23.98p | 7680 x 4320 | 23.98 |
| `8k60` | 8K UHD 60p | 7680 x 4320 | 60 |

## Pixel formats (BMDPixelFormat -> ffmpeg pix_fmt)

| SDK enum | ffmpeg | Bit depth | Chroma | Notes |
|---|---|---|---|---|
| `bmdFormat8BitYUV` | `uyvy422` | 8 | 4:2:2 | UYVY, most common |
| `bmdFormat10BitYUV` | `v210` | 10 | 4:2:2 | Width must be divisible by 48 |
| `bmdFormat8BitARGB` | `argb` | 8 | 4:4:4 | With alpha |
| `bmdFormat8BitBGRA` | `bgra` | 8 | 4:4:4 | With alpha, Windows order |
| `bmdFormat10BitRGB` | `r210` | 10 | 4:4:4 | Packed 10-bit RGB |
| `bmdFormat12BitRGB` | (no pix_fmt) | 12 | 4:4:4 | Needs custom handling |
| `bmdFormat12BitRGBLE` | (no pix_fmt) | 12 | 4:4:4 | Little-endian |
| `bmdFormat10BitRGBXLE` | (no pix_fmt) | 10 | 4:4:4 | Padded |
| `bmdFormat10BitRGBX` | (no pix_fmt) | 10 | 4:4:4 | Padded |

## Audio capabilities

- **Embedded SDI audio:** 2, 8, or 16 channels depending on card
- **Bit depths:** 16-bit (default), 24-bit, 32-bit
- **Sample rate:** 48 kHz fixed (SDI spec requirement)
- **HDMI audio:** 2 channels PCM; some cards support 8-ch LPCM on HDMI 2.0

## Recommended encode presets by use case

| Use case | Preset | Rationale |
|---|---|---|
| Broadcast-quality ingest | `prores_hq` | 10-bit, edit-ready, ~220 Mbps 1080p |
| Proxy for editing | `prores_proxy` | ~45 Mbps 1080p, very editable |
| Long-duration record | `h264_crf20` | Storage-efficient, decode-only |
| HDR master | `hevc_crf20` with `v210` source + 10-bit color | Preserves 10-bit |
| Network archive | `dnxhr_hq` | Avid-compatible, 440 Mbps 1080p |
| Diagnostic raw | `copy` (uyvy422 or v210) | No re-encode, biggest files |
