---
name: workflow-live-production
description: End-to-end live production — OBS as the mixer with obs-websocket control, MIDI/OSC cue triggers, DMX lighting sync, PTZ camera moves, system audio routing, NDI/SDI I/O, and multi-protocol egress via MediaMTX. Use when the user says "go live", "run a live show", "live stream", "wire up OBS", "scene switch on MIDI", "OBS + lighting + PTZ", "broadcast webinar", or anything involving real-time production with multiple control surfaces firing together.
argument-hint: [show-name]
---

# Workflow — Live Production

**What:** Run a live show end-to-end. OBS is the mixer; MIDI controllers trigger scenes; DMX lighting and PTZ cameras follow scene changes; system audio is correctly routed; MediaMTX fans the output to HLS + RTSP + SRT + WebRTC + RTMP.

**Who:** Streamers, broadcasters, church/corporate AV, venue operators, esports shoutcasters.

## Skills used

| Role | Skill |
|---|---|
| Scene authoring | `obs-config` |
| Remote control | `obs-websocket` (auto-discovers URL+password from local OBS) |
| In-OBS scripting | `obs-scripting` |
| Native plugin authoring | `obs-plugins` |
| Doc lookup guardrail | `obs-docs` |
| MIDI surface | `media-midi` |
| OSC surface | `media-osc` |
| Stage lighting | `media-dmx` (via OLA daemon) |
| PTZ cameras | `ptz-visca`, `ptz-onvif` |
| System audio | `audio-coreaudio` / `audio-wasapi` / `audio-pipewire` / `audio-jack` |
| Multi-protocol egress | `mediamtx-server` |
| WebRTC contribution | `ffmpeg-whip` |
| Capture | `ffmpeg-capture` |
| Hardware encode | `ffmpeg-hwaccel` |
| NDI ingest | `ndi-tools` |
| SDI ingest | `decklink-tools` |

## Pipeline

### Step 1 — Build the scene collection

Author the scene tree as JSON under the active OBS profile via the `obs-config` skill. Lock scene names early — downstream skills reference them by exact spelling (case-sensitive in the websocket protocol).

### Step 2 — Route system audio BEFORE launching OBS

OBS caches audio devices at startup. Create virtual sinks first so OBS sees them as inputs.

- **macOS:** create an aggregate device combining BlackHole + mic (`audio-coreaudio` skill).
- **Linux (PipeWire):** create a sink and link source apps into it (`audio-pipewire` skill).
- **Windows:** install VB-Cable / VoiceMeeter, enumerate devices (`audio-wasapi` skill).

### Step 3 — Start OBS and verify obs-websocket

OBS 28+ bundles obs-websocket v5. Use the `obs-websocket` skill's `wsctl.py check` + `ping` — it auto-discovers the password from the local OBS config. For remote OBS, export `OBS_WEBSOCKET_URL` and `OBS_WEBSOCKET_PASSWORD`.

### Step 4 — Wire MIDI / OSC triggers to scene switches

Use `media-midi` (`midictl.py monitor --json`) piped to `obs-websocket` (`wsctl.py scene-switch`). For TouchOSC / Reaper, use `media-osc` (`oscctl.py listen --port 8000 --json`) with the same fan-out pattern.

### Step 5 — Lighting cue on scene change (DMX)

Subscribe to OBS's `CurrentProgramSceneChanged` event via `wsctl.py events --subscribe scenes`, then drive DMX through `media-dmx` (`dmxctl.py send/fade --universe N --channel M`).

### Step 6 — PTZ preset recall on scene change

Same subscription stream. For VISCA cameras (UDP port 52381), use `ptz-visca` (`viscactl.py preset-recall --host <ip> --preset N`). For ONVIF, use `ptz-onvif` after discovery (`onvifctl.py discover`).

### Step 7 — Multi-protocol egress via MediaMTX

Configure the `mediamtx-server` skill once: RTMP ingest from OBS, auto-republish to HLS (8888), RTSP (8554), SRT (8890), WebRTC/WHEP (8889). Optional `runOnReady` spawns an ffmpeg forwarder to YouTube/Twitch/Facebook.

### Step 8 — WebRTC low-latency path (alternative to RTMP)

Skip OBS's RTMP output and go straight to WHIP via `ffmpeg-whip` — sub-second latency for contribution.

## Variants

- **Pure-software** — skip DMX/PTZ/DeckLink; software MIDI (Keyboard Maestro) + virtual audio + OBS only.
- **Broadcast SDI** — swap screen capture for DeckLink input via `decklink-tools`; playout back to SDI with ffmpeg's `-f decklink` output.
- **NDI-first facility** — replace RTMP ingest with NDI via `obs-ndi` plugin; MediaMTX still bridges to external delivery.
- **Remote producer + FOH operator** — both run OBS; operator drives producer's OBS over obs-websocket by setting `OBS_WEBSOCKET_URL` to the producer's LAN address.

## Gotchas

- **obs-websocket auto-discovery is local-only.** For a remote OBS, export `OBS_WEBSOCKET_URL` + `OBS_WEBSOCKET_PASSWORD`.
- **obs-websocket v5 only.** v4 is EOL. Close code `4010` = client/server version mismatch.
- **OBS caches audio devices at launch.** Create virtual sinks before starting OBS.
- **HighVolume events (bits 16–19) are deliberately excluded from `All` (=4095).** `InputVolumeMeters` fires every 50 ms. Only subscribe if you're rendering a meter UI.
- **PTZ presets are camera-stored.** `preset-set` once, `preset-recall` forever.
- **VISCA-over-IP is UDP:52381.** No handshake. Firewalls between camera and controller silently drop.
- **ONVIF WS-Discovery is multicast on 239.255.255.250:3702.** Does NOT cross VLAN boundaries without an IGMP-aware switch.
- **DMX via OLA requires `olad` running.** Art-Net controllers often want a dedicated 2.0.0.0/8 subnet per spec.
- **Art-Net universe is 0-indexed; DMX channel is 1-indexed.** `--universe 0 --channel 1` = first channel of universe 0.
- **MediaMTX ports: 8888 (HLS), 8889 (WebRTC), 8554 (RTSP), 8890 (SRT), 1935 (RTMP), 9997 (API).** Overlap with another service = silent boot failure.
- **MediaMTX `runOnReady` inherits stdin from the daemon.** Always pass `-nostdin` to ffmpeg inside those commands or the encoder blocks.
- **NDI runtime (NewTek/Vizrt) is a separate install** from the NDI SDK.
- **BlackHole / Loopback on macOS appear as both input and output.** App routes to output side, OBS picks it up from input side. Wrong direction = silence.
- **OBS scene names are case-sensitive** in the websocket protocol. Enumerate with `GetSceneList` for canonical spelling.
- **MIDI 1.0 vs 2.0 UMP are different wire formats.** Most tools speak 1.0 by default.
- **OSC bundles vs single messages.** TouchOSC sends bundles by default — parse `{"type":"bundle"}` before reaching into `.elements`.

## Example — MIDI note 36 triggers full-stack cue

On MIDI note 36: switch OBS to scene "Main", fade DMX channel 1 up to full, recall PTZ preset 3. Use `media-midi` monitor piped through `jq` to fan out three parallel actions (obs-websocket scene-switch, media-dmx fade, ptz-visca preset-recall). Core live-production value: one event → coordinated multi-device response.

## Related

- `workflow-streaming-distribution` — what to do with the stream once OBS emits it.
- `workflow-audio-production` — deeper system-audio recipes.
- `workflow-broadcast-delivery` — SDI + HDR dynamic metadata upstream.
- `workflow-analysis-quality` — monitor the live stream for drift.
