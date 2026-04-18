---
name: audio-coreaudio
description: >
  Manipulate macOS audio at the Core Audio HAL layer: afinfo (audio file metadata), afplay (play), afconvert (convert format/rate/bit-depth/channel layout), say (TTS), SwitchAudioSource (change default input/output/system device — brew install switchaudio-osx), audiodevice CLIs (npm/Go variants), AppleScript via osascript to drive System Preferences Sound. HAL plugins at /Library/Audio/Plug-Ins/HAL/ load virtual drivers (BlackHole 2ch/16ch/64ch, Loopback, Background Music). Aggregate Device (drift-corrected multi-in) and Multi-Output Device via Audio MIDI Setup.app or AudioHardwareCreateAggregateDevice. Use when the user asks to change default macOS audio device, route audio between apps on Mac, install BlackHole, build an Aggregate Device, convert audio files with afconvert, or script Mac audio from the terminal.
argument-hint: "[action]"
---

# Audio CoreAudio

**Context:** $ARGUMENTS

## Quick start

- **List input/output devices:** → Step 1 (`macaudio.py list-devices`)
- **Change default output:** → Step 2 (`macaudio.py set-default`)
- **Inspect an audio file:** → Step 3 (`macaudio.py info`)
- **Play a file:** → Step 3 (`macaudio.py play`)
- **Convert format/rate/bits:** → Step 4 (`macaudio.py convert`)
- **Text-to-speech:** → Step 5 (`macaudio.py tts`)
- **Build an Aggregate Device:** → Step 6 (`macaudio.py aggregate-create`)
- **List HAL virtual drivers:** → Step 7 (`macaudio.py hal-plugins`)
- **Install BlackHole virtual cable:** → Step 8 (`macaudio.py blackhole-install`)

## When to use

- User is on macOS and needs terminal-driven audio control.
- Wants to change the default input/output/system device without clicking through
  System Settings → Sound.
- Wants to convert audio files with Apple's built-in `afconvert` (more format
  coverage than SoX for Apple formats; handles CAF, M4A, ALAC natively).
- Wants to build an Aggregate Device (multi-input) or Multi-Output Device
  (mirror output to several devices).
- Wants to install / evaluate virtual audio drivers (BlackHole, Loopback,
  Background Music).

Not for: Linux (use `audio-pipewire`), Windows (use `audio-wasapi`).

The script exits 2 with a helpful message if run on non-macOS.

---

## Step 1 — List devices

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py list-devices
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py list-devices --format json
```

`SwitchAudioSource -a` underneath. Each line is `<name> (<type>)` where type is
`input` / `output`. If `SwitchAudioSource` isn't installed the script tells you
to run `brew install switchaudio-osx`.

---

## Step 2 — Set default input/output/system device

macOS distinguishes three defaults: **output** (music/TV audio), **input** (mic),
**system** (alert sounds, which can be a different device).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py set-default "MacBook Pro Speakers"
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py set-default "Scarlett Solo" --type input
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py set-default "MacBook Pro Speakers" --type system
```

Device name must match exactly (spaces matter, quoting required). Use
`list-devices` first.

---

## Step 3 — Inspect and play files (afinfo / afplay)

`afinfo` + `afplay` ship with macOS. No install needed.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py info track.caf
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py play track.caf
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py play track.caf --volume 128   # 0-255
```

`afinfo` reads every Apple format (CAF, M4A/AAC/ALAC, AIFF, WAV, MP3) plus
anything the system's registered AudioToolbox components understand.

---

## Step 4 — Convert with afconvert

`afconvert` is Apple's native format converter. Preferred over SoX for
Apple-specific flows (CAF, ALAC, AAC for M4A/M4R, lossless 32-bit float).

```bash
# WAV -> Apple Lossless in an M4A
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py convert \
  --input in.wav --output out.m4a --format m4af

# 24-bit 96k WAV -> 16-bit 48k WAV
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py convert \
  --input hi.wav --output lo.wav --format WAVE \
  --rate 48000 --bit-depth 16

# Stereo -> 5.1 upmix (container must support it — CAF does)
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py convert \
  --input stereo.wav --output surround.caf --format caff \
  --channel-layout 5.1
```

FourCC codes the `--format` flag accepts: `caff` (CAF), `m4af` (MPEG-4 audio),
`WAVE`, `AIFF`, `AIFC`. Full list: `afconvert -hf`.

---

## Step 5 — say + afplay TTS

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py tts "Build complete"
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py tts "hola" --voice Monica
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py tts "saved" --output voicemail.aiff
```

`say -v '?'` lists installed voices. Voices beyond the defaults (Alex, Samantha,
Daniel) require a one-time download via System Settings → Accessibility →
Spoken Content → System Voice → Customize.

---

## Step 6 — Aggregate Device / Multi-Output Device

macOS lets you combine physical devices two ways:

- **Aggregate Device** — sum inputs *and* outputs of several devices into one
  logical interface. DAWs see it as a single multi-channel device. Needs drift
  correction when the member devices don't share a word clock.
- **Multi-Output Device** — mirror playback to several outputs (e.g. speakers +
  BlackHole + AirPods). Output-only.

This wrapper opens Audio MIDI Setup and prints the clickable steps, because
programmatic creation needs `AudioHardwareCreateAggregateDevice` from
`CoreAudio/AudioHardware.h` (Swift / Objective-C). Use when wiring for
automation:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py aggregate-create \
  --name "Studio Aggregate" \
  --devices "AppleHDAEngineOutput:1B,0,0,1:0" "BlackHole2ch_UID" \
  --drift-correct "BlackHole2ch_UID"
```

Member device UIDs come from `list-devices` (pass `--format json` for the full
UID strings).

For a truly automatable path, write the Swift snippet that calls
`AudioHardwareCreateAggregateDevice` — see `references/virtual-drivers.md`.

---

## Step 7 — List HAL plug-ins

HAL plug-ins are `.driver` bundles that register virtual audio devices:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py hal-plugins
```

Typical output includes `BlackHole2ch.driver`, `BackgroundMusic.driver`,
`Loopback.driver`, Aggregate/Multi-Output synthesizer drivers from Apple.

Global path: `/Library/Audio/Plug-Ins/HAL/*.driver`.
User path: `~/Library/Audio/Plug-Ins/HAL/*.driver` (rare; per-user installs).

After installing or removing a HAL plug-in, `coreaudiod` has to rescan:

```bash
sudo pkill coreaudiod     # wrapper intentionally does NOT run this
```

---

## Step 8 — BlackHole (virtual cable)

BlackHole is the go-to free open-source virtual driver — works on Apple Silicon
(DriverKit / AudioDriverKit) and Intel, 2ch / 16ch / 64ch variants.

The wrapper *prints* install instructions rather than installing automatically:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py blackhole-install --variant 2ch
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py blackhole-install --variant 16ch
```

Runs the install only if the user copies the printed `brew install --cask` line.
See [`references/virtual-drivers.md`](references/virtual-drivers.md) for the
full BlackHole vs Loopback vs Background Music comparison.

---

## Gotchas

- **Soundflower is abandoned.** It does not load on macOS 11+ / Apple Silicon.
  Never recommend it. Use BlackHole instead.
- **`SwitchAudioSource` device names must match exactly.** Trailing spaces,
  capitalization, and the full name (including brand prefix) all matter.
  Quote-wrap everything. `list-devices --format json` gives you a copy-pasteable
  UID.
- **There are two "audiodevice" CLIs in the wild.** An npm package
  (`node-audiodevice`) and a Go binary. Both predate SwitchAudioSource and have
  different flags. Always specify the package/binary when pointing at them;
  default to `SwitchAudioSource` in docs.
- **BlackHole, Loopback, and Background Music all use DriverKit/AudioDriverKit
  on Apple Silicon.** Legacy kext audio drivers (Soundflower, old Loopback
  versions) won't load. If a driver supposedly installs but `list-devices`
  doesn't show it, SIP or kernel-extension approval is likely blocking it
  (System Settings → Privacy & Security → Allow).
- **Aggregate Device needs drift correction when members don't share a clock.**
  Without drift correction, multi-USB-device aggregates will desync by seconds
  over a long session.
- **Multi-Output Device cannot be a system alert device.** macOS rejects it —
  system sounds require a real output endpoint.
- **`afconvert` fourCC codes are case-sensitive.** `WAVE` with `-f`, not `wave`.
  Likewise `AIFF`/`AIFC`/`caff`/`m4af`.
- **After installing a HAL plug-in, new processes pick it up; existing ones don't.**
  Apps that cached `AudioDeviceID` values will miss it until restart. System
  Settings → Sound usually re-enumerates immediately.
- **`say` runs through the system output by default**, not whatever
  `set-default --type input` was last set to. If you need say → file, pipe
  through `--output` (AIFF) or `afconvert` afterward for M4A/MP3.
- **AppleScript via osascript can hit Sound preferences via UI automation**, but
  it's fragile across macOS versions and requires accessibility permissions.
  Prefer `SwitchAudioSource` for scripted default changes.
- **CoreAudio HAL IDs are not stable across reboots.** Use the device
  **UID** (string) instead of the numeric `AudioDeviceID` when persisting
  references in scripts / plist / DAW configs.
- **BlackHole per-channel variants are not upgradeable in place.** Uninstall
  `blackhole-2ch` before installing `blackhole-16ch`, or both drivers show up
  simultaneously (which is fine — they are different devices, separately named).

---

## Examples

### Example 1 — "Swap default output to my headphones"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py list-devices     # find exact name
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py set-default "Sony WH-1000XM5"
```

### Example 2 — "Capture system audio into OBS"

1. Install BlackHole 2ch:

   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py blackhole-install --variant 2ch
   # copy the printed brew command and run it
   ```

2. In Audio MIDI Setup build a Multi-Output Device combining your speakers +
   BlackHole; set it as system output.
3. Point OBS's "Audio Input Capture" at BlackHole.

### Example 3 — "Convert a WAV archive to Apple Lossless"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py convert \
  --input master.wav --output master.m4a --format m4af
```

### Example 4 — "Read EXIF from an AIFF"

`afinfo` covers it:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py info recording.aiff
```

### Example 5 — "Speak build results to me"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/macaudio.py tts "Tests passed, zero failures" --voice Samantha
```

---

## Troubleshooting

### `SwitchAudioSource: command not found`

**Cause:** Not installed.
**Fix:** `brew install switchaudio-osx`. The wrapper points at this in its error
output.

### Default device "silently" reverts after plugging in USB interface

**Cause:** macOS default-reassign behavior when "When playing sound through" is
set to "whatever device is connected". Overrides your scripted default.
**Fix:** System Settings → Sound → Output → uncheck "Automatically switch to
newly connected devices" (macOS 14+), or persist the default in a LaunchAgent
that re-runs `set-default` on device change.

### `afconvert: Error -50` (invalid parameter)

**Cause:** Requested an output format/rate/bit-depth combo that the codec
rejects (e.g. ALAC in WAV container, 32-bit float into M4A).
**Fix:** Drop mismatched flags. ALAC belongs in `m4af` only; bit-depth is
AAC-ignored.

### BlackHole doesn't appear after install

**Cause:** System Extension blocked by macOS.
**Fix:** System Settings → Privacy & Security → scroll to the "System software
was blocked" banner → Allow. Reboot. Retry.

### `afplay` works but no sound

**Cause:** afplay uses the current system default output. If you set a weird
output recently (aggregate without speakers as a member), nothing audible is
reached.
**Fix:** Re-run `set-default` with a known-good physical output and retry.

### Aggregate Device session drifts

**Cause:** No drift correction, or drift master isn't the most-stable clock.
**Fix:** In Audio MIDI Setup, check "Drift Correction" on every non-master
member. Put the interface with the best clock (Thunderbolt → PCIe card → USB 2)
as master.

---

## Reference docs

- BlackHole vs Loopback vs Background Music comparison, plus the Swift snippet
  for programmatic Aggregate Device creation →
  [`references/virtual-drivers.md`](references/virtual-drivers.md).
