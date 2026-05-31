---
name: audio-routing
description: >
  Use when the user wants to route or control system audio on any OS: change the default output/input/communications device, route audio between apps, build a virtual audio cable, or capture system audio into OBS. Linux PipeWire (pw-link, pw-cat, pw-loopback, pw-dump, pw-top, WirePlumber). macOS Core Audio (SwitchAudioSource, afconvert, afplay, BlackHole, Aggregate and Multi-Output devices, HAL plugins). Windows WASAPI (AudioDeviceCmdlets, SoundVolumeView/svcl, nircmd, VB-Cable, VoiceMeeter, exclusive vs shared mode). JACK low-latency pro-audio routing (jackd, jack_lsp, jack_connect, JackTrip network audio) on Linux and macOS. Also docs lookup to verify any PipeWire, JACK, Core Audio, or WASAPI command or flag before naming it. Triggers: route Linux audio, change Mac default device, install BlackHole or VB-Cable, set up VoiceMeeter, measure JACK roundtrip latency, link two audio apps, virtual audio device, system audio capture.
argument-hint: "[action]"
---

# Audio Routing

**Context:** $ARGUMENTS

System-level audio routing below FFmpeg, across all four host subsystems. Pick
the technique reference for the user's OS / use case, then run its scripts.

## When to use

- Change the default output / input / communications device from the terminal
  on Linux, macOS, or Windows.
- Route audio between apps or to a specific device (port-level links).
- Build a virtual audio cable to capture system audio into OBS / streaming tools.
- Set up Aggregate / Multi-Output devices (macOS) or virtual mixers (VoiceMeeter).
- Run low-latency pro-audio routing with JACK, or bridge audio over the network
  with JackTrip.
- Diagnose xruns, exclusive-vs-shared mode mismatches, or measure round-trip
  latency.
- Verify a PipeWire / JACK / Core Audio / WASAPI command or flag before naming it.

## Techniques

Identify the user's OS first, then load the matching reference. Each reference is
self-contained (its own steps, gotchas, examples, troubleshooting) and drives a
script in `scripts/`.

- Read `references/pipewire.md` when the user is on **Linux** and wants to route
  audio, link apps, list devices, create a loopback, record system audio, or
  debug xruns (drives `scripts/pwctl.py`).
- Read `references/coreaudio.md` when the user is on **macOS** and wants to change
  the default device, install BlackHole, build an Aggregate / Multi-Output device,
  convert with afconvert, or script Mac audio (drives `scripts/macaudio.py`).
- Read `references/wasapi.md` when the user is on **Windows** and wants to change
  the default device, install VB-Cable / VoiceMeeter, or enable exclusive-mode
  low-latency output (drives `scripts/winaudio.py`).
- Read `references/jack.md` when the user wants **low-latency pro-audio routing**
  (Ardour, Reaper, Bitwig), explicit period/sample-rate control, round-trip
  latency measurement, or JackTrip network audio (drives `scripts/jackctl.py`).

Subsystem reference docs loaded on demand by the technique references:

- `references/virtual-drivers.md` — BlackHole vs Loopback vs Background Music
  (macOS); programmatic Aggregate Device creation.
- `references/backends.md` — JACK per-backend flag catalog (ALSA, CoreAudio,
  PortAudio, ASIO).
- `references/jacktrip.md` — JackTrip server/client/hub mode, FEC, port list.
- `references/elements.md` — PipeWire object/type taxonomy and property keys.
- `references/exclusive-vs-shared.md` — WASAPI shared vs exclusive deep dive,
  IAudioClient3.
- `references/virtual-cable.md` — VB-Cable tiers, svcl.exe flags, VoiceMeeter
  routing.

## Docs lookup

Before naming any PipeWire, JACK, Core Audio, or WASAPI command, flag, or API,
**verify it against the official docs** — this is the anti-hallucination guard.
Zero search hits means the flag is not in that subsystem's docs; do not claim it
works.

Read `references/docs-search.md` for the workflow, then run
`scripts/audiodocs.py`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search --query "pw-link" --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py section --page pipewire-man-pw-link --id SYNOPSIS
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py list-pages
```

`references/pages.md` holds the full annotated page catalog across
`docs.pipewire.org`, `jackaudio.org`, `developer.apple.com`, `learn.microsoft.com`.

## Gotchas

- **On modern Linux, `jackd` is almost always PipeWire's libjack shim.** Starting
  a second jackd is a no-op. Use PipeWire (`pw-metadata -n settings 0
  clock.force-quantum <N>`) to change quantum; existing JACK apps already run
  against the shim.
- **Soundflower is abandoned** — won't load on macOS 11+ / Apple Silicon. Never
  recommend it; use BlackHole (DriverKit / AudioDriverKit). After install, if a
  driver doesn't appear, approve it under Privacy & Security → Allow, then reboot.
- **Windows has no first-party CLI to change audio devices.** Everything is
  third-party (AudioDeviceCmdlets, NirSoft svcl, VB-Audio); expect install steps.
- **Three separate "default" roles per OS.** macOS: output / input / system.
  Windows: playback / recording / communications (Zoom/Discord pull from
  communications, not multimedia). Set each explicitly.
- **Device/port names must match exactly and need quoting.** Spaces, colons, and
  dots are common. Prefer immutable IDs/UIDs (CoreAudio UID, Windows endpoint
  GUID, PipeWire node name) over display names in scripts — names drift across
  updates and object IDs change across daemon restarts.
- **Exclusive vs shared (WASAPI).** Shared mode resamples everything to the
  endpoint mix format via `audiodg.exe`; exclusive mode is bit-perfect but the
  app must negotiate a hardware-supported format or `IAudioClient::Initialize`
  returns `AUDCLNT_E_UNSUPPORTED_FORMAT`.
- **JACK direction trips everyone.** `system:capture_*` are output ports;
  `system:playback_*` are input ports (server's POV). Connecting two outputs or
  two inputs fails silently. Latency ≈ `(period × nperiods) / samplerate`.
- **Virtual cables / loopbacks don't persist by default.** `pw-loopback` dies with
  its foreground process; existing apps don't see a freshly installed virtual
  driver until they re-enumerate (usually a restart). Persist PipeWire loopbacks
  via a config fragment or WirePlumber Lua.

## Scripts

All Python 3, stdlib-only, support `--dry-run` and `--verbose`. Each exits with a
helpful message if run on the wrong OS.

| Script | Subsystem | OS |
|---|---|---|
| `scripts/pwctl.py` | PipeWire | Linux |
| `scripts/macaudio.py` | Core Audio | macOS |
| `scripts/winaudio.py` | WASAPI | Windows |
| `scripts/jackctl.py` | JACK / JackTrip | Linux, macOS |
| `scripts/audiodocs.py` | Docs lookup (all four) | any |

Invoke with `uv run ${CLAUDE_SKILL_DIR}/scripts/<script>.py <subcommand>`.
