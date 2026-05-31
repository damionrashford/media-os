# Mode: audio-production

**Subagent**: `architect`
**Trigger phrases**: "mix audio", "audio routing", "PipeWire route", "JACK route", "Core Audio route", "WASAPI route", "stems mix", "MIDI route", "OSC route", "system audio setup", "DAW routing", "live audio mix"
**Output**: `${MEDIA_WORK_DIR}/modes/audio-production/{date}_{slug}/`

## Inputs

- **Required**:
  - `task` — `route` (set up system audio routing), `mix` (combine stems → master), `repair` (de-noise / de-click), `control-bridge` (MIDI/OSC → audio params).
- **Optional**:
  - `sources` — list of input files / stems (for `mix`) or device names (for `route`).
  - `output_layout` — `mono`, `stereo`, `5.1`, `7.1`, `atmos-9.1.6`. Default: `stereo`.
  - `sample_rate` — `44100` (default for music), `48000` (default for video/broadcast), `96000`.
  - `bit_depth` — `16` (default), `24`, `32-float`.
  - `routing_graph` — JSON description of node connections (for `route` task).

## Steps

1. Read tool skills per `task`:
   - `route` → `audio-routing` (Linux primary), `audio-routing` (Linux/macOS), `audio-routing` (macOS), `audio-routing` (Windows).
   - `mix` → `ffmpeg-filter`, `ffmpeg-filter`, `media-audio-cli`, `media-audio-cli`.
   - `repair` → `media-demucs` (source-separation), `media-audio-cli` (de-click), `ffmpeg-filter` (afftdn / arnndn voice denoise).
   - `control-bridge` → `media-control`, `media-control`.
2. **Platform detection**: detect host OS via `uname -s` and route to the right audio skill (don't suggest PipeWire on macOS).
3. Branch by `task`:
   - **`route`**: Compose the routing graph (PipeWire `pw-link`, JACK `jack_connect`, Core Audio aggregate device, WASAPI exclusive-mode device). Apply via the underlying tool's API. Verify with `pw-dump`/`jack_lsp`/`SystemAudioConfig` query.
   - **`mix`**: For multitrack stems, compose `ffmpeg -filter_complex amix=inputs=N:weights=...` OR for parametric mix, build the filter graph (HPF + EQ + compression + bus group + master limiter). For Atmos: invoke ADM BWF tooling (out-of-scope for ffmpeg alone; surface).
   - **`repair`**: De-noise via DeepFilterNet (MIT). De-click via SoX `noisered`. Source-separate via Demucs (`htdemucs` model, MIT). Apply in order: de-click → de-noise → source-separate.
   - **`control-bridge`**: Map MIDI CC or OSC messages to audio params (ffmpeg filter parameters, OBS source filters, etc.). Use `media-control` for CC parsing, `media-control` for OSC parsing.
4. For `mix` and `repair`: **`mosafe`-wrap** every ffmpeg invocation.
5. Output to the chosen sample rate / bit depth / channel layout. Verify with `soxi` or `ffprobe`.
6. Run loudness check via `media-audio-cli --print-stats` even on non-broadcast targets (catches clipping / extreme LRA).
7. Write `summary.md` with routing diagram (for `route`), mix matrix (for `mix`), source-separation stems list (for `repair`), or MIDI/OSC mapping table (for `control-bridge`).

## Output schema

```markdown
# Audio production — {slug} — {date}

## Task
**{route / mix / repair / control-bridge}**

## Platform
- **OS**: {macOS / Linux / Windows}
- **Audio subsystem**: {Core Audio / PipeWire / JACK / WASAPI}

## Configuration
- **Sample rate / bit depth / channels**: {N Hz} / {N bit} / {layout}

{Per-task section:}

### Routing (task=route)
- Graph applied: {description or JSON}
- Verification: {pw-dump excerpt / jack_lsp output / Core Audio config}

### Mix matrix (task=mix)
| Input | Channels | Weight | Bus | Notes |
|---|---|---|---|---|

### Repair (task=repair)
- Tools applied: {DeepFilterNet / SoX noisered / Demucs}
- Source separation stems: {drums / bass / vocals / other paths}

### Control bridge (task=control-bridge)
| MIDI CC / OSC path | Target param | Range | Curve |
|---|---|---|---|

## Output
- **File / device**: {path or device name}
- **Loudness check**: {integrated LUFS, true peak, LRA}
- **Verification**: {soxi or ffprobe excerpt}
```

## Quality bar

- Platform detection happened — no PipeWire suggestions on macOS, no Core Audio config on Linux.
- Sample rate / bit depth / channel layout match request exactly (verified post-process).
- For `mix`: no clipping (true peak ≤ -1.0 dBTP unless explicitly requested).
- For `repair`: source files preserved; repair output goes to new path.
- For Atmos: explicit notice if request exceeds ffmpeg capability (ADM BWF requires dedicated tooling).
- For `control-bridge`: MIDI CC mappings and OSC paths documented in summary (operator needs them to undo).

## Playbook reference (folded from workflow-audio-production)

## Pipeline

### Step 1 — Platform audio routing

| OS | Skill | What to do |
|---|---|---|
| Linux | `audio-routing` | `pw-cli list`, create virtual sink, `pw-link` source → target |
| macOS | `audio-routing` | aggregate devices (multi-mic sum), BlackHole / Loopback virtual cables |
| Windows | `audio-routing` | VB-Cable / VoiceMeeter virtual routing |
| Cross-platform | `audio-routing` | `jackd` start, `jack_lsp` list-ports, `jack_connect` DAW → destination |

### Step 2 — Control surfaces

- **MIDI** — `media-control`: list-ports, monitor JSON, send-note, map to OBS/OSC/anything.
- **OSC** — `media-control`: send/listen.

### Step 3 — DSP chain

- **SoX / FFmpeg filters** — `highpass=f=80`, `equalizer=f=3000:t=q:w=1:g=3`, `acompressor`, `alimiter`, `loudnorm`.
- **LADSPA / LV2 plugins** — via ffmpeg's `ladspa` / `lv2` filters.

### Step 4 — Spatial audio

`ffmpeg-filter`:
- **Binaural HRTF** — `sofalizer` with a SOFA file, per-track azimuth / elevation.
- **Surround 5.1 upmix / downmix** — `pan` filter with channel matrix.

### Step 5 — AI processing

`ffmpeg-filter` (afftdn / arnndn / anlmdn denoise), `media-demucs` (stem separation), `ai-generate` (Kokoro / OpenVoice / Piper), `ai-generate` (Riffusion / YuE), `media-whisper` (transcription).

### Step 6 — Loudness certification

`media-audio-cli` two-pass EBU R128:

| Target | Integrated | True peak |
|---|---|---|
| Spotify Master | −14 LUFS | −2 dBTP |
| Apple Podcasts | −16 LUFS | −1 dBTP |
| ATSC A/85 | −24 LUFS | varies |
| EBU R128 broadcast | −23 LUFS | −1 dBTP |
| ACX audiobooks | −19 LUFS | −3 dBTP |

## Variants

- **Live DAW recording** — start JACK, connect DAW I/O, MIDI controller, OSC tablet.
- **Podcast cleanup** — see the podcast-pipeline mode.
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
- **Single-pass `loudnorm` uses guardrails (±1 LUFS).** Two-pass measures then applies exactly. Use `media-audio-cli` for certification.
- **True peak measures inter-sample peaks, 4× oversampled.** Standard sample peak misses these.
- **LUFS = LKFS = same thing (different standards' names for integrated loudness).**

## Example — Podcast-style live monitor with MIDI transport

`jackd` start → connect DAW ↔ system audio → `media-control monitor` Stream Deck → MIDI CC maps to DAW transport (play/stop/record) AND to OBS scene switch in parallel.
