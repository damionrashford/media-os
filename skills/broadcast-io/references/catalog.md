# DeckLink docs page catalog

Full list of URLs in the catalog and what each covers. Cache each with
`decklinkdocs.py fetch --page <name>` or prime everything with `index`.

## Blackmagic developer hub (login-gated for SDK download)

| Page | URL | Purpose |
|---|---|---|
| `blackmagic-developer` | https://www.blackmagicdesign.com/developer | Landing page — developer SDKs index |
| `blackmagic-capture-playback` | https://www.blackmagicdesign.com/developer/product/capture-and-playback | DeckLink Desktop Video SDK product page. The SDK ZIP download requires a free Blackmagic developer account + terms acceptance. |
| `blackmagic-support` | https://www.blackmagicdesign.com/support/family/capture-and-playback | Driver + Desktop Video runtime downloads (no login required) |

## ffmpeg decklink device docs

| Page | URL | Purpose |
|---|---|---|
| `ffmpeg-devices` | https://ffmpeg.org/ffmpeg-devices.html | All ffmpeg devices (decklink + others) |
| `ffmpeg-devices-decklink` | https://ffmpeg.org/ffmpeg-devices.html#decklink | decklink indev (capture) + outdev (play) options |

The decklink section documents: `-list_devices`, `-list_formats`, `-format_code`, `-bm_v210`, `-video_input`, `-audio_input`, `-duplex_mode`, `-timecode_format`, `-raw_format`, `-teletext_lines`, `-draw_bars`, `-audio_depth`, plus the muxer (output) options: `-pix_fmt`, `-field_order`, `-vsync`, `-audio_depth`, `-timing_offset`.

## SDK sample catalog (reference-only)

The actual samples ship in the SDK ZIP. Official sample directory names (to cite correctly):

- `CapturePreview` — preview-window capture app
- `LoopThroughPreview` — real-time loop-through with monitor window
- `SignalGenerator` — test-pattern generator to SDI/HDMI
- `StatusMonitor` — signal status + format probing
- `DeviceList` — enumerate all DeckLink devices on the system
- `TestPattern` — lower-level output test
- `3DVideoFrames` — stereoscopic video frame handling
- `StreamOperations` — capture-with-encode (H.264) pipelines
- `FrameServer` — multi-client frame distribution
- `AudioMixer` — multi-channel audio mixing

**Not official samples:** `bmdcapture`, `BMDPlaybackSample`, `bmd_capture_tool`. `bmdcapture`/`bmdplay` come from github.com/lu-zero/bmdtools — a third-party ffmpeg-backed CLI wrapping the SDK.

## DeckLink API core interfaces (ship in `DeckLinkAPI.h` / `DeckLinkAPI.idl`)

Cite these by exact case when recommending C++ code:

- **Discovery:** `IDeckLinkIterator`, `IDeckLink`, `IDeckLinkProfileAttributes`, `IDeckLinkStatus`, `IDeckLinkNotification`
- **Capture:** `IDeckLinkInput`, `IDeckLinkInputCallback`, `IDeckLinkVideoInputFrame`, `IDeckLinkAudioInputPacket`
- **Playback:** `IDeckLinkOutput`, `IDeckLinkVideoOutputCallback`, `IDeckLinkMutableVideoFrame`
- **Format:** `IDeckLinkDisplayMode`, `IDeckLinkDisplayModeIterator`, `IDeckLinkConfiguration`
- **Stereo / 3D:** `IDeckLinkVideoFrame3DExtensions`
- **HDR:** `IDeckLinkVideoFrameMetadataExtensions` (EOTF, mastering metadata L1/L6)
- **Profile mgmt:** `IDeckLinkProfile`, `IDeckLinkProfileManager`, `IDeckLinkProfileCallback`

## BMDPixelFormat enum (canonical values)

| SDK enum | 4CC | ffmpeg `pix_fmt` equivalent |
|---|---|---|
| `bmdFormat8BitYUV` | `2vuy` | `uyvy422` |
| `bmdFormat10BitYUV` | `v210` | `v210` |
| `bmdFormat8BitARGB` | (none) | `argb` |
| `bmdFormat8BitBGRA` | `BGRA` | `bgra` |
| `bmdFormat10BitRGB` | `r210` | `r210` |
| `bmdFormat12BitRGB` | `R12B` | — |
| `bmdFormat12BitRGBLE` | `R12L` | — |
| `bmdFormat10BitRGBXLE` | `R10l` | — |
| `bmdFormat10BitRGBX` | `R10b` | — |

## BMDDisplayMode examples (four-CC codes)

These four-CCs double as ffmpeg `-format_code` arguments:

| Four-CC | Mode |
|---|---|
| `ntsc` | NTSC SD 525/59.94i |
| `pal ` | PAL SD 625/50i |
| `Hp60` | HD 1080p60 |
| `Hp59` | HD 1080p59.94 |
| `Hp50` | HD 1080p50 |
| `Hi60` | HD 1080i60 |
| `Hi59` | HD 1080i59.94 |
| `Hi50` | HD 1080i50 |
| `hp60` | HD 720p60 |
| `hp59` | HD 720p59.94 |
| `hp50` | HD 720p50 |
| `2k24` | 2K DCI 24p |
| `4k24` | UHD 4K 24p |
| `4k30` | UHD 4K 29.97p |
| `4k60` | UHD 4K 59.94p |

Full list enumerated at runtime via `IDeckLinkDisplayModeIterator`.

## Gotchas

- **SDK ZIP vs runtime driver are separate downloads.** SDK = headers + samples (login). Driver = `Desktop Video` installer (no login). Both required for ffmpeg `--enable-decklink` + runtime.
- **Four-CCs are 4 ASCII bytes with spaces padding** (`'pal '` = PAL). Strip the quote marks when passing to `-format_code`.
- **Blackmagic URLs rate-limit scrapers.** Catalog them, don't spam them; the `index` command sleeps between requests.
