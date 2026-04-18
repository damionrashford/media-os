# Live Production Workflow

**What:** Run a live show end-to-end — OBS as the mixer, MIDI controllers triggering scenes, DMX lighting synced, PTZ cameras moving on cue, system audio routed correctly, and MediaMTX fanning out the signal to every protocol an audience might be on.

**Who:** Streamers, broadcasters, church AV teams, corporate webinar producers, venue operators, esports shoutcasters.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| Scene authoring | `obs-config` | Build the OBS profile / scene collection / source tree |
| Remote control | `obs-websocket` | Auto-discovers URL+password from local OBS config; RPC all scene/source/record/stream ops |
| Scripting inside OBS | `obs-scripting` | Python/Lua scripts for hotkeys, timers, property dialogs |
| Plugin authoring | `obs-plugins` | Native C++ sources/outputs/encoders/filters |
| Doc lookup | `obs-docs` | Verify every OBS API call before using |
| MIDI control surface | `media-midi` | Map MIDI notes/CCs to OBS Requests |
| OSC integration | `media-osc` | TouchOSC / Reaper / Max/MSP bridge |
| Stage lighting | `media-dmx` | DMX512 / Art-Net / sACN via OLA |
| PTZ cameras | `ptz-visca`, `ptz-onvif` | Pan/tilt/zoom + presets over IP |
| System audio routing | `audio-coreaudio` (macOS) / `audio-wasapi` (Windows) / `audio-pipewire` (Linux) / `audio-jack` | Route app audio into OBS without hardware loopback |
| Multi-protocol egress | `mediamtx-server` | One YAML, all protocols: HLS + RTSP + SRT + WebRTC + WHIP + WHEP |
| Low-latency WebRTC | `ffmpeg-whip` | Sub-second contribution path |
| Capture | `ffmpeg-capture` | Screen + webcam + mic fallback |
| Hardware encode | `ffmpeg-hwaccel` | NVENC / QSV / VAAPI / VideoToolbox / AMF |
| NDI | `ndi-tools`, `ndi-docs` | Sources from NDI network fabric |
| SDI | `decklink-tools` | Blackmagic capture / playout |

---

## The pipeline

### 1. Build the scene collection (`obs-config`)

Author the scene tree as JSON under the active OBS profile:

```bash
uv run .claude/skills/obs-config/scripts/obscfg.py scene-collection create \
  --name "LiveShow2026" \
  --scenes "Starting Soon,Main,BRB,Interview,Outro"
```

Every downstream skill references scenes by exact name — lock these early.

### 2. Route system audio *before* OBS launches

OBS captures whatever audio devices exist at startup. Create virtual sinks first so OBS sees them as inputs.

**macOS:**
```bash
uv run .claude/skills/audio-coreaudio/scripts/coreaudiolist.py create-aggregate \
  --name "OBS-Mix" --devices "BlackHole 2ch,Built-in Microphone"
```

**Linux (PipeWire):**
```bash
uv run .claude/skills/audio-pipewire/scripts/pwctl.py create-sink --name obs-app
uv run .claude/skills/audio-pipewire/scripts/pwctl.py link --from chrome --to obs-app
```

**Windows (WASAPI):**
Install VB-Cable / VoiceMeeter, then:
```bash
uv run .claude/skills/audio-wasapi/scripts/wasapilist.py list-devices
```

### 3. Start OBS and verify websocket

Launch OBS → obs-websocket auto-enabled (OBS 28+ bundles v5). The `wsctl.py` helper auto-discovers password + port from `plugin_config/obs-websocket/config.json` — no flags needed.

```bash
uv run .claude/skills/obs-websocket/scripts/wsctl.py check
uv run .claude/skills/obs-websocket/scripts/wsctl.py ping
```

### 4. Wire up MIDI / OSC triggers

Map MIDI note 36 (lowest C on a 25-key) to scene "Main":

```bash
uv run .claude/skills/media-midi/scripts/midictl.py monitor --channel 1 --json | \
  jq --unbuffered -r 'select(.type=="noteon" and .note==36) | "Main"' | \
  while read scene; do
    uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene "$scene"
  done
```

For OSC (TouchOSC / Reaper):
```bash
uv run .claude/skills/media-osc/scripts/oscctl.py listen --port 8000 --json | \
  while read -r msg; do
    addr=$(echo "$msg" | jq -r .address)
    case "$addr" in
      /scene/main) uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene Main ;;
      /scene/brb)  uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene BRB ;;
    esac
  done
```

### 5. Lighting cue on scene change (DMX)

OBS fires `CurrentProgramSceneChanged` event. Subscribe and drive DMX:

```bash
uv run .claude/skills/obs-websocket/scripts/wsctl.py events --subscribe scenes | \
  jq --unbuffered -r 'select(.d.eventType=="CurrentProgramSceneChanged") | .d.eventData.sceneName' | \
  while read scene; do
    case "$scene" in
      Main)  uv run .claude/skills/media-dmx/scripts/dmxctl.py send --universe 1 --channel 1 --value 255 ;;
      BRB)   uv run .claude/skills/media-dmx/scripts/dmxctl.py send --universe 1 --channel 1 --value 20 ;;
      Outro) uv run .claude/skills/media-dmx/scripts/dmxctl.py fade --universe 1 --channel 1 --from 255 --to 0 --ms 3000 ;;
    esac
  done
```

### 6. PTZ preset recall on scene change

```bash
# Same subscription stream — split to PTZ
uv run .claude/skills/ptz-visca/scripts/viscactl.py preset-recall \
  --host 192.168.1.50 --preset 3  # "interview close-up"
```

For ONVIF-compatible cameras:
```bash
uv run .claude/skills/ptz-onvif/scripts/onvifctl.py discover
uv run .claude/skills/ptz-onvif/scripts/onvifctl.py ptz-goto \
  --host 192.168.1.50 --user admin --token Profile_1 --preset wide
```

### 7. NDI source pickup (optional)

If a remote operator is contributing NDI:
```bash
uv run .claude/skills/ndi-tools/scripts/nditools.py find --timeout 5
```

Add the discovered NDI source via OBS-NDI plugin (requires `obs-ndi` plugin + NDI SDK runtime).

### 8. Multi-protocol egress via MediaMTX

Configure MediaMTX once — it republishes to every protocol an audience might want:

```yaml
# mediamtx.yml
paths:
  live:
    source: publisher          # accept incoming stream
    sourceProtocol: automatic
    runOnReady: ffmpeg -i rtsp://localhost:8554/live -c copy -f flv rtmp://a.rtmp.youtube.com/live2/$KEY
```

Start the server:
```bash
uv run .claude/skills/mediamtx-server/scripts/mtxctl.py start --config mediamtx.yml
```

OBS "Custom RTMP Server" → `rtmp://localhost/live` → MediaMTX fans out to HLS (`http://host:8888/live/index.m3u8`), RTSP (`rtsp://host:8554/live`), SRT (`srt://host:8890?streamid=read:live`), WebRTC (`http://host:8889/live`), plus forwards to YouTube.

### 9. WebRTC low-latency contribution (alternative)

Skip OBS's RTMP output and go straight to WHIP:

```bash
uv run .claude/skills/ffmpeg-whip/scripts/whip.py publish \
  --input screen \
  --whip-url https://mediamtx.example.com/whip/live
```

---

## Variants

### Pure-software setup (no hardware)

Skip DeckLink, PTZ, DMX. Use only OBS + virtual audio sinks + MIDI (software MIDI from Keyboard Maestro / OSC from TouchOSC iOS). Everything else unchanged.

### Broadcast-grade SDI workflow

Swap screen capture for DeckLink input:

```bash
uv run .claude/skills/decklink-tools/scripts/decklinkctl.py list-devices
ffmpeg -f decklink -i "DeckLink Duo 2 (1)" \
  -c:v h264_nvenc -preset p5 -b:v 8M \
  -f flv rtmp://localhost/live
```

And playout back to SDI:
```bash
ffmpeg -i http://localhost:8888/live/index.m3u8 \
  -f decklink "DeckLink Duo 2 (2)"
```

### NDI-first facility

If the whole venue is on NDI, replace RTMP ingest with NDI ingest (via `obs-ndi`) and push NDI output on the egress side. OBS handles both — MediaMTX is still the protocol bridge for external distribution.

### Remote producer mode

Producer runs OBS on a laptop upstage, operator drives another OBS over obs-websocket from FOH:

```bash
# From operator laptop — auto-discover is local-only; for remote use env override
export OBS_WEBSOCKET_URL=ws://producer-laptop.local:4455
export OBS_WEBSOCKET_PASSWORD=<copied from producer's OBS>
uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene Main
```

---

## Gotchas

- **obs-websocket auto-discovery is local-only.** For a remote OBS, export `OBS_WEBSOCKET_URL` + `OBS_WEBSOCKET_PASSWORD`. The helper script will prefer env vars when the local config doesn't resolve.
- **OBS 28+ bundles obs-websocket v5. v4 is EOL.** Make sure clients target v5. Close code 4010 = version mismatch.
- **OBS caches audio devices at launch.** Create virtual sinks *before* starting OBS. Otherwise they won't appear in the source list.
- **Never subscribe to HighVolume events by default.** `InputVolumeMeters` fires every 50ms. Only enable when you're rendering a meter UI. `All` = 4095 (deliberately excludes bits 16-19). Use `eventSubscriptions` bitmask.
- **PTZ presets are camera-stored.** The camera remembers them, not the app. Call `preset-set` once, then `preset-recall` forever.
- **VISCA-over-IP is UDP:52381.** No handshake, no TCP. Firewalls between the camera and the controller silently drop it. Verify with `nc -u -z $HOST 52381` or by watching `viscactl.py ping`.
- **ONVIF is SOAP.** WS-Discovery is multicast on 239.255.255.250:3702 — doesn't cross VLAN boundaries without an IGMP-aware switch.
- **DMX via OLA requires the `olad` daemon running.** Start with `olad -l 3` for logs. Art-Net controllers also need their IP on a dedicated subnet (often 2.0.0.0/8 per the Art-Net spec).
- **Art-Net universe numbering is 0-indexed, but DMX channels are 1-indexed.** `--universe 0 --channel 1` = first channel of universe 0. Off-by-one errors here = wrong fixture on cue.
- **MediaMTX uses port 8888 (HLS), 8889 (WebRTC), 8554 (RTSP), 8890 (SRT), 1935 (RTMP), 9997 (API).** Overlapping with other services is the #1 boot failure.
- **MediaMTX `runOnReady` commands inherit stdin from the daemon.** Always pass `-nostdin` to ffmpeg inside those commands or the encoder will block.
- **NDI runtime is platform-specific** (NewTek/Vizrt) — not bundled with the NDI SDK distribution. Install separately via the official installer before `obs-ndi` can find it.
- **DeckLink device numbering is zero-based in ffmpeg but one-based in `bmdcapture`.** The `-f decklink -i "DeckLink Duo 2 (1)"` syntax uses the name, which avoids the ambiguity.
- **BlackHole / Loopback on macOS appear as both input AND output.** Route the app to the *output* side, then pick it as an *input* in OBS. Wrong direction = silence.
- **Scene names are case-sensitive in the obs-websocket protocol.** `Starting Soon` ≠ `starting soon`. Use `GetSceneList` to enumerate the canonical spelling.
- **MIDI 1.0 vs 2.0 UMP are different wire formats.** `rtpmidi` / `amidi` / CoreMIDI handle 1.0 by default. For 2.0 UMP, use explicitly UMP-aware tools.
- **OSC bundles vs single messages.** TouchOSC sends bundles by default. Parse `{"type":"bundle"}` branches before reaching into `.elements`.

---

## Example — "switch to Main on MIDI note 36, fade lights up, recall PTZ preset 3"

```bash
#!/usr/bin/env bash
# live-cue-main.sh — MIDI-triggered full-stack scene change

uv run .claude/skills/media-midi/scripts/midictl.py monitor --json | while read -r msg; do
  type=$(echo "$msg" | jq -r .type)
  note=$(echo "$msg" | jq -r .note)
  if [[ "$type" == "noteon" && "$note" == "36" ]]; then
    uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene Main &
    uv run .claude/skills/media-dmx/scripts/dmxctl.py fade --universe 1 --channel 1 --from 20 --to 255 --ms 500 &
    uv run .claude/skills/ptz-visca/scripts/viscactl.py preset-recall --host 192.168.1.50 --preset 3 &
    wait
  fi
done
```

Three skills firing in parallel on one MIDI trigger. This is the core of the live-production value: one event, coordinated multi-device response.

---

## Further reading

- [`streaming-distribution.md`](streaming-distribution.md) — what to do with the stream once OBS emits it
- [`audio-production.md`](audio-production.md) — deeper system audio routing recipes
- [`broadcast-delivery.md`](broadcast-delivery.md) — SDI + HDR dynamic metadata upstream
- [`analysis-quality.md`](analysis-quality.md) — monitoring the live stream for drift
