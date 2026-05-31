# Mode: live-production

**Subagent**: `live`
**Trigger phrases**: "go live", "start streaming", "OBS broadcast", "wire up live rig", "NDI to stream", "set up multi-bitrate stream", "broadcast from OBS", "live encoder setup", "PTZ camera setup", "DeckLink capture stream"
**Output**: `${MEDIA_WORK_DIR}/modes/live-production/{date}_{slug}/`

## Inputs

- **Required**:
  - `target` — destination URL(s) (RTMP / SRT / RIST / WHIP / HLS push). Multiple targets allowed (multi-CDN fan-out).
  - `source` — input chain (OBS scene name OR NDI source name OR DeckLink device index OR ffmpeg input URI).
- **Optional**:
  - `bitrate_ladder` — comma-separated kbps tiers (default: `8000,5000,3000,1500` for 1080p; `4000,2500,1200` for 720p; `2000,1000,500` for 480p).
  - `latency_mode` — `low` (≤2s, WHIP/RIST), `standard` (~6s, RTMP/SRT), `chunked` (~3s, LL-HLS). Default: `standard`.
  - `ptz_camera` — VISCA-over-IP or ONVIF endpoint for camera control.
  - `obs_websocket_url` — defaults to `OBS_WEBSOCKET_URL` userConfig.

## Steps

1. Read tool skills `obs-websocket`, `ndi-tools`, `decklink-tools`, `ffmpeg-whip`, `ffmpeg-rist-zmq`, `mediamtx-server`, `ptz-onvif`/`ptz-visca` as needed.
2. Run `moprobe --json <source>` if source is a file or URL. For OBS scenes, query `obs-websocket` for the current scene's video/audio settings. For NDI, run `ndi-tools` discovery first.
3. **STOP** if the source isn't reachable (NDI source not advertising, DeckLink device unplugged, OBS WebSocket auth fail). Surface the failure with the exact diagnostic command (`ndi-record-cli -list`, `BMDStreamingServer -list`, etc.).
4. Validate `target` URLs: RTMP must include stream key; SRT must include `?streamid=` if using stream-ID auth; WHIP target must be HTTPS.
5. Compose the ffmpeg invocation (or OBS WebSocket call) per the chosen `latency_mode`:
   - `low` → WHIP (`ffmpeg -f whip -bsf:v dump_extra <target>`) or RIST (`-f rist <target>?bandwidth=<kbps>`).
   - `standard` → RTMP (`-f flv rtmp://...`) or SRT (`-f mpegts srt://...?mode=caller`).
   - `chunked` → LL-HLS (`hls_segment_type=fmp4`, `hls_part_target=0.5`, `lhls=1`).
6. **`mosafe`-wrap the full ffmpeg command** before invocation.
7. For PTZ: send VISCA `home` + `recall preset 1` (or ONVIF `GotoPreset`) on stream start.
8. Start the stream. Tail the encoder log for `frame=`, `bitrate=`, `dup=`, `drop=` — pin these in a status line.
9. Health-monitor: if `dup > 0` for 30s or `drop > 5/sec` for 10s, surface to operator (likely network saturation or source desync). Do NOT auto-recover — live ops require human-in-loop.
10. On stream stop, save `summary.md` with start/stop times, target URLs, total dropped frames, peak bitrate.

## Output schema

```markdown
# Live production — {slug} — {date}

## Configuration
- **Source**: {source}
- **Targets**: {target list}
- **Bitrate ladder**: {ladder}
- **Latency mode**: {low|standard|chunked}
- **PTZ**: {endpoint or N/A}

## Stream session
- **Started**: {ISO timestamp}
- **Stopped**: {ISO timestamp}
- **Duration**: {hh:mm:ss}
- **Total frames encoded**: {N}
- **Dropped frames**: {N} ({pct}%)
- **Duplicate frames**: {N}
- **Peak bitrate**: {kbps}

## Issues observed
- {timestamp} — {observation}

## Replay assets
- Local DVR: {path or N/A}
- Multi-bitrate VOD: {path or N/A — see streaming-distribution mode}
```

## Quality bar

- `mosafe` exited zero before stream start.
- All `target` URLs were validated (curl reachable for HLS targets; RTMP/SRT/RIST/WHIP went through one test packet).
- Dropped-frame rate < 1% over the session (flag in `## Issues observed` if exceeded).
- PTZ preset recalls completed without ONVIF/VISCA error.
- No silent stream death — surface a clear error if encoder process exited non-zero.

## Playbook reference (folded from workflow-live-production)

**What:** Run a live show end-to-end. OBS is the mixer; MIDI controllers trigger scenes; DMX lighting and PTZ cameras follow scene changes; system audio is correctly routed; MediaMTX fans the output to HLS + RTSP + SRT + WebRTC + RTMP.

**Who:** Streamers, broadcasters, church/corporate AV, venue operators, esports shoutcasters.

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
