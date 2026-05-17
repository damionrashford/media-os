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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-audio-production/SKILL.md`. Read tool skills per `task`:
   - `route` → `audio-pipewire` (Linux primary), `audio-jack` (Linux/macOS), `audio-coreaudio` (macOS), `audio-wasapi` (Windows).
   - `mix` → `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `media-ffmpeg-normalize`, `media-sox`.
   - `repair` → `media-demucs` (source-separation), `media-sox` (de-click), `media-denoise-ai` (DeepFilterNet for voice).
   - `control-bridge` → `media-midi`, `media-osc`.
2. **Platform detection**: detect host OS via `uname -s` and route to the right audio skill (don't suggest PipeWire on macOS).
3. Branch by `task`:
   - **`route`**: Compose the routing graph (PipeWire `pw-link`, JACK `jack_connect`, Core Audio aggregate device, WASAPI exclusive-mode device). Apply via the underlying tool's API. Verify with `pw-dump`/`jack_lsp`/`SystemAudioConfig` query.
   - **`mix`**: For multitrack stems, compose `ffmpeg -filter_complex amix=inputs=N:weights=...` OR for parametric mix, build the filter graph (HPF + EQ + compression + bus group + master limiter). For Atmos: invoke ADM BWF tooling (out-of-scope for ffmpeg alone; surface).
   - **`repair`**: De-noise via DeepFilterNet (MIT). De-click via SoX `noisered`. Source-separate via Demucs (`htdemucs` model, MIT). Apply in order: de-click → de-noise → source-separate.
   - **`control-bridge`**: Map MIDI CC or OSC messages to audio params (ffmpeg filter parameters, OBS source filters, etc.). Use `media-midi` for CC parsing, `media-osc` for OSC parsing.
4. For `mix` and `repair`: **`mosafe`-wrap** every ffmpeg invocation.
5. Output to the chosen sample rate / bit depth / channel layout. Verify with `soxi` or `ffprobe`.
6. Run loudness check via `media-ffmpeg-normalize --print-stats` even on non-broadcast targets (catches clipping / extreme LRA).
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
