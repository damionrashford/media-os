---
name: broadcast-io
description: >
  Blackmagic DeckLink SDI/HDMI capture and playout plus NDI send/receive/record/bridge and gphoto2 DSLR/mirrorless tether. DeckLink via ffmpeg -f decklink (list_devices, list_formats, capture, play out SDI, SignalGenerator test patterns, four-CC modes Hp60/4k60, uyvy422/v210 pixel formats, Desktop Video driver, DeckLink SDK install). NDI via NewTek/Vizrt SDK tools (ndi-send, ndi-find, ndi-record, NDI Bridge, Studio Monitor, DistroAV OBS plugin, mDNS 5353, SpeedHQ, NDI 6 HDR/HX3). gphoto2 tether (auto-detect, capture-image-and-download, capture-preview live-view, capture-movie, get-all-files, list/get/set-config for shutter/aperture/ISO, timelapse, PTP/IP over Wi-Fi; Canon/Nikon/Sony). Use when the user asks to capture from DeckLink, output SDI/HDMI, list DeckLink devices/formats, send/receive/find/record/bridge NDI, use DistroAV in OBS, tether a DSLR, remote-control camera aperture/ISO/shutter, drive live-view, or build a photobooth/timelapse rig.
argument-hint: "[device-or-source] [target]"
---

# Broadcast I/O

**Context:** $ARGUMENTS

Hardware and network signal I/O for live production: Blackmagic DeckLink SDI/HDMI, NewTek/Vizrt NDI over LAN, and gphoto2 camera tether over USB / PTP-IP.

## When to use

- Capture or play out SDI/HDMI through Blackmagic DeckLink hardware (Mini Recorder, Mini Monitor, 4K/8K Pro, UltraStudio).
- Send, receive, find, record, or bridge NDI sources on the network; integrate NDI into OBS via DistroAV.
- Tether a DSLR / mirrorless (Canon, Nikon, Sony, Fujifilm, etc.) over USB or Wi-Fi for remote capture, config, live-view, or timelapse.
- Verify an SDK call, enum, port number, or display mode before recommending code or config.

## Techniques

- Read `references/decklink.md` when capturing or playing SDI/HDMI via DeckLink, listing devices/formats, generating test patterns, or installing the DeckLink SDK. Driver wrapper: `scripts/decklink.py`.
- Read `references/ndi.md` when sending, receiving, finding, recording, bridging, or benchmarking NDI, or installing NDI Tools / DistroAV. CLI wrapper: `scripts/ndictl.py`.
- Read `references/gphoto2.md` when tethering a camera — capture, download, live-view, movie, config, timelapse, PTP/IP. Wrapper: `scripts/tether.py`.
- Read `references/cards-and-modes.md` when you need the DeckLink card matrix and full display-mode/four-CC table.
- Read `references/tools.md` when you need full CLI option tables for `ndi-send`, `ndi-find`, `ndi-record`, `ndi-benchmark`, and NDI env vars.
- Read `references/config-keys.md` when mapping gphoto2 config-key paths across Canon / Nikon / Sony bodies.

## Docs lookup

Before naming any SDK interface, enum, method, port number, or display mode, verify it against the cached vendor docs — do NOT recall it from training memory (anti-hallucination):

- Read `references/docs-search-decklink.md` and run `scripts/decklinkdocs.py search --query "..."` for DeckLink C++/COM API (IDeckLinkInput/Output, BMDPixelFormat, BMDDisplayMode) and the ffmpeg decklink demuxer/muxer options. Page catalog in `references/catalog.md`.
- Read `references/docs-search-ndi.md` and run `scripts/ndidocs.py search --query "..."` for NDI ports, HDR (PQ/HLG), SpeedHQ vs HX, NDI 6 features, SDK-vs-Advanced matrix, and DistroAV. Page catalog in `references/pages.md`.

## Gotchas

- **DeckLink device names are case-sensitive and contain spaces.** Always quote: `-i "DeckLink Mini Recorder 4K"`. Run `decklink.py list-devices` and copy the exact string.
- **`bmdcapture` / `BMDPlaybackSample` are NOT official SDK samples.** They ship with third-party `bmdtools` (github.com/lu-zero/bmdtools). Official samples are `CapturePreview`, `LoopThroughPreview`, `SignalGenerator`, `StatusMonitor`, `DeviceList`, `TestPattern`, etc. Correct the user.
- **DeckLink playback requires `-re`** and v210 (10-bit YUV) requires width divisible by 48. ffmpeg needs `--enable-decklink` AND the Desktop Video runtime driver installed, or you get `Unknown input format: 'decklink'`.
- **NDI cannot be bundled in ffmpeg** (non-redistributable SDK) — mainline removed it. Use the ndi-* CLIs or DistroAV in OBS. **obs-ndi is dead; DistroAV is the successor**, and it needs the NDI runtime installed separately.
- **NDI uses three port families:** mDNS UDP 5353, messaging TCP 5960, per-source streams TCP/UDP 5961+. mDNS often blocked across VLANs — symptom is `ndi-find` finding zero sources; fix with NDI Discovery Server or Bridge. `ndi-record` and multicast need the Advanced SDK.
- **macOS hijacks tethered cameras via PTPCamera.** Run `killall PTPCamera` before gphoto2. Linux needs udev rules for non-root USB access.
- **gphoto2 config-key paths are per-camera, not a universal schema.** Canon aperture is `/main/capturesettings/aperture`; Nikon is `f-number`. Always run `tether.py config-list` first on an unknown body.
- **`gphoto2-config` / `gphoto2-cam-conf` do not exist** — config is a subcommand family of the single `gphoto2` binary (`--list-config`, `--get-config`, `--set-config`). And `gphoto.org` is HTTP-only (invalid HTTPS cert).

## Scripts

All stdlib-only Python 3.9+, `--dry-run` / `--verbose` supported, run via `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>`:

- `scripts/decklink.py` — DeckLink capture/play/signal-gen/list (wraps ffmpeg `-f decklink`).
- `scripts/ndictl.py` — NDI find/send/record/studio-monitor/bridge/benchmark/install-sdk.
- `scripts/tether.py` — gphoto2 detect/shoot/preview/movie/bulk-download/config-*/timelapse/ptpip.
- `scripts/decklinkdocs.py` — search/section/fetch Blackmagic + ffmpeg decklink docs.
- `scripts/ndidocs.py` — search/section/fetch docs.ndi.video + DistroAV docs.
