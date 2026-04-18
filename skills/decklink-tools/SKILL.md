---
name: decklink-tools
description: >
  Capture and play back SDI/HDMI video via Blackmagic DeckLink hardware: ffmpeg decklink indev/outdev (-f decklink -list_devices 1, -f decklink -list_formats 1, -f decklink -i 'DeckLink Mini Recorder 4K', -f decklink 'DeckLink Mini Monitor'), SDK Samples (CapturePreview, LoopThroughPreview, SignalGenerator test-pattern output, StatusMonitor, DeviceList, TestPattern, 3DVideoFrames, StreamOperations, FrameServer, AudioMixer). Pixel formats (uyvy422 = bmdFormat8BitYUV, v210 = bmdFormat10BitYUV), four-CC display modes (Hp60 = 1080p60, 4k60 = UHD60). Requires Desktop Video driver + ffmpeg built --enable-decklink. Use when the user asks to capture from DeckLink, output to SDI, ingest HDMI via Blackmagic, list DeckLink devices/formats, generate test patterns out SDI, or install the DeckLink SDK.
argument-hint: "[device-or-file] [target]"
---

# Decklink Tools

**Context:** $ARGUMENTS

## Quick start

- **List DeckLink devices:** → Step 1 (`decklink.py list-devices`)
- **List supported formats for a device:** → Step 2 (`decklink.py list-formats`)
- **Capture SDI/HDMI to a file:** → Step 3 (`decklink.py capture`)
- **Play a file out SDI/HDMI:** → Step 4 (`decklink.py play`)
- **Generate a test pattern out SDI/HDMI:** → Step 5 (`decklink.py signal-gen`)
- **Need the SDK headers for your own code?** → Step 6 (`decklink.py sdk-install`)

## When to use

- User has Blackmagic hardware (Mini Recorder, Mini Monitor, DeckLink 4K Pro, UltraStudio, etc.) plugged in and wants to capture or play SDI/HDMI.
- Need the exact device name ffmpeg expects (case-sensitive, quoted).
- Need to pick an SDI/HDMI mode by four-CC (`Hp60`, `4k60`) or name.
- Generating continuous test bars on an SDI output for calibration.
- Use the companion `decklink-docs` skill to verify API / enum / option names.

## Step 1 — List devices

DeckLink hardware is enumerated at the OS level by the Desktop Video driver. ffmpeg talks to it via the decklink indev/outdev.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py list-devices
```

Under the hood this runs:

```bash
ffmpeg -hide_banner -f decklink -list_devices 1 -i dummy
```

Output lines look like `[decklink @ ...] 'DeckLink Mini Recorder 4K'`. The quoted string is the exact name to pass to `-i` or as output URL. Names are case-sensitive; spaces are significant.

## Step 2 — List formats for one device

Display modes supported by a device depend on the hardware (HD-only vs 12G-SDI).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py list-formats --device "DeckLink Mini Recorder 4K"
```

Under the hood:

```bash
ffmpeg -hide_banner -f decklink -list_formats 1 -i "DeckLink Mini Recorder 4K"
```

Output columns: mode index, four-CC, mode name, FPS. Use either the index (`-format_code 23`) or the four-CC (`-format_code Hp60`) — four-CCs are clearer and more portable.

## Step 3 — Capture

Stream copy the DeckLink signal to a file without re-encoding (fastest path):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py capture \
  --device "DeckLink Mini Recorder 4K" \
  --format Hp60 \
  --pixel uyvy422 \
  --out capture.mov
```

Expands to:

```bash
ffmpeg -f decklink -format_code Hp60 -raw_format uyvy422 \
       -i "DeckLink Mini Recorder 4K" \
       -c:v copy -c:a copy capture.mov
```

For 10-bit YUV (Rec.2020 HDR, film), pass `--pixel v210`. Width must be divisible by 48 for v210.

Re-encode during capture (useful when disk bandwidth is limited):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py capture \
  --device "DeckLink Mini Recorder 4K" --format Hp60 \
  --encode prores_hq --out capture.mov
```

Encode presets: `prores_proxy`, `prores_lt`, `prores_hq`, `h264_crf20`, `hevc_crf20`, `dnxhr_hq`.

## Step 4 — Playback

Play an existing file out SDI/HDMI via a DeckLink output card:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py play \
  --device "DeckLink Mini Monitor" \
  --in clip.mov \
  --format Hp60
```

Expands to:

```bash
ffmpeg -re -i clip.mov \
       -pix_fmt uyvy422 -vf scale=1920:1080,setsar=1 \
       -f decklink -format_code Hp60 "DeckLink Mini Monitor"
```

`-re` (read at native frame rate) is mandatory — without it ffmpeg feeds the DeckLink faster than the output clock and the card drops frames.

## Step 5 — Signal generator (test pattern)

Generate continuous SMPTE bars + 1 kHz tone out SDI/HDMI:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py signal-gen \
  --device "DeckLink Mini Monitor" \
  --mode Hp60 \
  --pattern smptebars
```

Expands to:

```bash
ffmpeg -re \
  -f lavfi -i "smptebars=size=1920x1080:rate=60" \
  -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
  -pix_fmt uyvy422 \
  -f decklink -format_code Hp60 "DeckLink Mini Monitor"
```

Patterns: `smptebars`, `smptehdbars`, `testsrc`, `testsrc2`, `rgbtestsrc`, `color=black`, `color=gray`.

## Step 6 — SDK install (instructions only)

Writing your own C++ code against the DeckLink API needs the SDK headers, which live in a login-gated ZIP.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py sdk-install
```

This prints — it does not download — the two links:

1. **Desktop Video driver + runtime** (no login):
   `https://www.blackmagicdesign.com/support/family/capture-and-playback`
2. **Desktop Video SDK** (free Blackmagic developer account required):
   `https://www.blackmagicdesign.com/developer/product/capture-and-playback`

Plus the standard install order: install the driver first, reboot, then unzip the SDK somewhere and point your build at `<SDK>/Mac` / `Linux` / `Win`. `ffmpeg --enable-decklink --extra-cflags=-I/path/to/SDK/Linux/include` on Linux.

---

## Gotchas

- **`bmdcapture`, `BMDPlaybackSample`, `bmd_capture_tool` are NOT official SDK sample names.** `bmdcapture` / `bmdplay` come from the third-party `github.com/lu-zero/bmdtools` repo. Official sample directories are `CapturePreview`, `LoopThroughPreview`, `SignalGenerator`, `StatusMonitor`, `DeviceList`, `TestPattern`, `3DVideoFrames`, `StreamOperations`, `FrameServer`, `AudioMixer`. Correct this if the user mentions those non-existent names.
- **Device names are case-sensitive and contain spaces.** Always quote: `-i "DeckLink Mini Recorder 4K"`, never `-i DeckLink-Mini-Recorder-4K`.
- **The decklink indev/outdev only exists if ffmpeg was built `--enable-decklink`.** Homebrew `ffmpeg` does not enable it by default; you need a third-party tap or a source build with SDK headers present. Missing: `Unknown input format: 'decklink'`.
- **The Desktop Video driver must be installed at runtime** even when ffmpeg was built with the SDK. No `libDeckLinkAPI.{so,dll,dylib}` → ffmpeg errors at startup.
- **v210 (bmdFormat10BitYUV) requires width divisible by 48.** 1920 / 48 = 40, OK. Custom widths like 1936 will fail to open.
- **`-raw_format` takes ffmpeg pix_fmt names, not SDK enum names.** `uyvy422` = `bmdFormat8BitYUV`, `v210` = `bmdFormat10BitYUV`, `argb` = `bmdFormat8BitARGB`, `bgra` = `bmdFormat8BitBGRA`, `r210` = `bmdFormat10BitRGB`.
- **`-format_code` accepts four-CCs OR mode indexes.** Four-CCs are 4 ASCII bytes; some are space-padded (`'pal '`). Trailing-space four-CCs are not shell-safe — use the index instead.
- **Playback requires `-re`.** Without native-rate read, the DeckLink card fills its hardware queue, underruns on switch-over, and emits visible glitches.
- **Audio channels:** DeckLink cards ship 2, 8, or 16 channels of embedded SDI audio. If you ask for 8-channel output but only have 2 tracks, ffmpeg pads silence; if you ask for 2 but receive 8, ffmpeg drops the extras silently. Match `-channels` to the source.
- **`-duplex_mode` (full vs half).** On cards with one connector that can do both input and output (DeckLink Studio 4K), you must set `-duplex_mode full` before using both directions simultaneously. Half duplex is default.
- **Macs:** Desktop Video installs `libDeckLinkAPI.dylib` into `/Library/Frameworks/DeckLinkAPI.framework/`. Ad-hoc ffmpeg builds need the framework on the rpath.
- **Linux `libgcc` ABI mismatch:** SDK samples compiled on one distro may fail on another with `undefined reference to __cxa_*`. Rebuild the samples on the target machine with the matching g++.

---

## Examples

### Example 1: "What DeckLink cards are plugged in?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py list-devices
```

### Example 2: "Record 1080p60 uncompressed from the Mini Recorder 4K"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py capture \
  --device "DeckLink Mini Recorder 4K" --format Hp60 --pixel uyvy422 \
  --out /tmp/grab.mov
```

### Example 3: "Record 4K 60 HDR 10-bit from SDI to ProRes HQ"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py capture \
  --device "DeckLink 8K Pro" --format 4k60 --pixel v210 \
  --encode prores_hq --out hdr_grab.mov
```

### Example 4: "Send SMPTE bars out my Mini Monitor for calibration"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py signal-gen \
  --device "DeckLink Mini Monitor" --mode Hp60 --pattern smptehdbars
```

### Example 5: "Play back a ProRes master file out SDI at 29.97"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklink.py play \
  --device "DeckLink Mini Monitor" --in master.mov --format Hp29
```

---

## Troubleshooting

### Error: `Unknown input format: 'decklink'`

**Cause:** ffmpeg was not built `--enable-decklink`.
**Solution:** Build from source with the SDK headers present, or install a decklink-enabled ffmpeg binary.

### Error: `Cannot find DeckLink device called 'DeckLink ...'`

**Cause:** Exact name mismatch (extra space, wrong case) or driver not running.
**Solution:** Run `list-devices`, copy-paste the exact string. Verify Desktop Video is installed and the card is lit.

### Error: `DeckLinkCaptureDelegate::VideoInputFrameArrived: DeckLink frame bad: 0x80000000`

**Cause:** No incoming signal (unplugged cable, camera off, wrong format on sender).
**Solution:** Use the `StatusMonitor` SDK sample, or run `ffmpeg -f decklink -i "..."` with `-hide_banner` and watch the first log line — it reports detected input format. Match `-format_code` to that.

### Error: `v210: width is not divisible by 48`

**Cause:** Packed 10-bit YUV pixel layout requirement.
**Solution:** Use `-raw_format uyvy422` (8-bit) or scale first: `-vf scale=1920:1080`.

### Frames drop during playback

**Cause:** Missing `-re`, or disk can't sustain raw-rate read.
**Solution:** Add `-re`. If it's already there, pre-transcode the source to a codec decodable in real time (ProRes, DNxHR).

### Error: `Could not find any DeckLink card`

**Cause:** Driver installed but kernel hasn't claimed the device, or Thunderbolt hub not powered.
**Solution:** Reboot. Check `Blackmagic Desktop Video Setup` enumerates the card.

---

## Reference docs

- For SDK interface names, enum values, and the full BMDDisplayMode table, invoke the `decklink-docs` skill (companion search + catalog).
- For ffmpeg decklink option reference: `decklink-docs` → `search --query "..." --page ffmpeg-devices-decklink`.
