---
name: workflow-audio-production
description: Full-stack audio routing across macOS / Linux / Windows, MIDI + OSC control surfaces, DAW integration over JACK, DSP (EQ / compression / loudness / spatial / binaural HRTF), AI denoise (DeepFilterNet / RNNoise / Resemble Enhance), stem separation (Demucs), TTS, Whisper transcription, and EBU R128 / Spotify / Apple / ATSC loudness certification. Use when the user says "set up DAW", "route audio through OBS", "MIDI control surface", "binaural ASMR", "stem separation", "loudness to −16 LUFS", "JACK transport", or anything audio-stack-related.
argument-hint: [source]
---

# Workflow — Audio Production

**What:** Route, process, and finish audio end-to-end across every OS and every control surface.

## Skills used

`audio-routing-docs`, `audio-pipewire`, `audio-jack`, `audio-coreaudio`, `audio-wasapi`, `media-midi`, `media-osc`, `media-sox`, `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `media-denoise-ai`, `media-demucs`, `media-musicgen`, `media-tts-ai`, `media-whisper`, `media-ffmpeg-normalize`, `ffmpeg-captions`, `ffmpeg-subtitles`.

## Pipeline

### Step 1 — Platform audio routing

| OS | Skill | What to do |
|---|---|---|
| Linux | `audio-pipewire` | `pw-cli list`, create virtual sink, `pw-link` source → target |
| macOS | `audio-coreaudio` | aggregate devices (multi-mic sum), BlackHole / Loopback virtual cables |
| Windows | `audio-wasapi` | VB-Cable / VoiceMeeter virtual routing |
| Cross-platform | `audio-jack` | `jackd` start, `jack_lsp` list-ports, `jack_connect` DAW → destination |

### Step 2 — Control surfaces

- **MIDI** — `media-midi`: list-ports, monitor JSON, send-note, map to OBS/OSC/anything.
- **OSC** — `media-osc`: send/listen.

### Step 3 — DSP chain

- **SoX / FFmpeg filters** — `highpass=f=80`, `equalizer=f=3000:t=q:w=1:g=3`, `acompressor`, `alimiter`, `loudnorm`.
- **LADSPA / LV2 plugins** — via ffmpeg's `ladspa` / `lv2` filters.

### Step 4 — Spatial audio

`ffmpeg-audio-spatial`:
- **Binaural HRTF** — `sofalizer` with a SOFA file, per-track azimuth / elevation.
- **Surround 5.1 upmix / downmix** — `pan` filter with channel matrix.

### Step 5 — AI processing

`media-denoise-ai` (DeepFilterNet / RNNoise / Resemble Enhance), `media-demucs` (stem separation), `media-tts-ai` (Kokoro / OpenVoice / Piper), `media-musicgen` (Riffusion / YuE), `media-whisper` (transcription).

### Step 6 — Loudness certification

`media-ffmpeg-normalize` two-pass EBU R128:

| Target | Integrated | True peak |
|---|---|---|
| Spotify Master | −14 LUFS | −2 dBTP |
| Apple Podcasts | −16 LUFS | −1 dBTP |
| ATSC A/85 | −24 LUFS | varies |
| EBU R128 broadcast | −23 LUFS | −1 dBTP |
| ACX audiobooks | −19 LUFS | −3 dBTP |

## Variants

- **Live DAW recording** — start JACK, connect DAW I/O, MIDI controller, OSC tablet.
- **Podcast cleanup** — see `workflow-podcast-pipeline`.
- **Binaural audiodrama** — split stereo, per-track HRTF positioning, sum.
- **DAW → OBS system-audio routing** — aggregate device, DAW out → BlackHole, OBS source → aggregate.
- **Control-surface-driven automation** — Stream Deck MIDI → OBS scene + DMX cue + OSC transport in parallel.

## Gotchas

- **BlackHole / Loopback appear as BOTH input AND output on macOS.** Route the app to OUTPUT; pick input in DAW/OBS.
- **PipeWire aliases `default` to the current Pulse sink.** Script with the real sink name from `pw-cli ls Node`.
- **JACK buffer = latency frames ÷ sample rate** (128 @ 48 kHz = 2.67 ms). Too low = xruns; too high = sluggish.
- **WASAPI loopback captures the render endpoint, not the source app.** Use a virtual cable for per-app capture.
- **macOS aggregate devices clock to the FIRST device in the list.** Others drift. Pick the clock master first.
- **Windows MME is legacy shared; WASAPI is exclusive/professional.** For low latency, use WASAPI.
- **MIDI 1.0 = 3 bytes; MIDI 2.0 UMP = 4–16 bytes.** Wrong protocol = silent ignore.
- **MIDI channels: 0–15 on the wire, 1–16 in UI.** Off-by-one is the #1 bug.
- **MIDI running status** compresses repeated types — old hardware uses it; modern mostly doesn't.
- **OSC bundles contain timed sub-messages.** Parse `type:bundle` → `.elements` branch.
- **OSC address patterns support wildcards** (`/track/*/volume`). Server-side wildcards fire multiple handlers.
- **OSC TCP 1.1 vs UDP 1.0.** Pick one per endpoint; they're not interchangeable.
- **`loudnorm` is NOT a limiter.** It normalizes. If peaks exceed target, it applies downward gain, not transient shaving. Add explicit `alimiter`.
- **`aresample filter_size` trades quality for speed.** 512 = audiophile, 128 = streaming.
- **`atempo` range is 0.5–2.0 per instance.** Chain for extremes.
- **`asetrate` changes pitch AND tempo together.** Combine with `atempo` for pitch-preserving speed.
- **`sidechaincompress`** — key input FIRST, signal SECOND. Wrong order = wrong ducking.
- **DeepFilterNet: 48 kHz MONO or 16 kHz MONO.** Resample before.
- **RNNoise: 48 kHz mono 16-bit, hardcoded.** Anything else fails silently.
- **Demucs: 44.1 / 48 kHz STEREO.** Mono → degraded stems.
- **Whisper: 16 kHz mono best.** Resamples internally; explicit is cleaner.
- **Voice cloning needs a CLEAN reference.** DeepFilterNet the reference sample first.
- **Kokoro TTS outputs 24 kHz.** Resample to 48 kHz before mixing.
- **Single-pass `loudnorm` uses guardrails (±1 LUFS).** Two-pass measures then applies exactly. Use `media-ffmpeg-normalize` for certification.
- **True peak measures inter-sample peaks, 4× oversampled.** Standard sample peak misses these.
- **LUFS = LKFS = same thing (different standards' names for integrated loudness).**

## Example — Podcast-style live monitor with MIDI transport

`jackd` start → connect DAW ↔ system audio → `media-midi monitor` Stream Deck → MIDI CC maps to DAW transport (play/stop/record) AND to OBS scene switch in parallel.

## Related

- `workflow-podcast-pipeline` — applied podcast recipe using this stack.
- `workflow-live-production` — MIDI/OSC surfaces driving OBS + DMX + PTZ.
- `workflow-analysis-quality` — loudness compliance verification.
