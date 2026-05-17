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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-live-production/SKILL.md` for the full chain; read tool skills `obs-websocket`, `ndi-tools`, `decklink-tools`, `ffmpeg-whip`, `ffmpeg-rist-zmq`, `mediamtx-server`, `ptz-onvif`/`ptz-visca` as needed.
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
