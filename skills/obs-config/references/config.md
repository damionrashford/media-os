# OBS on-disk configuration reference

This file is the full map of what lives on disk for OBS Studio, organized so a script can author it without launching the GUI. OBS reads this tree at launch and rewrites on quit — concurrent edits lose. Always quit OBS before programmatic edits, and back up `basic/` first.

## 1. Per-platform config root

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/obs-studio/` |
| Linux (native deb/AppImage) | `~/.config/obs-studio/` |
| Linux (Flatpak) | `~/.var/app/com.obsproject.Studio/config/obs-studio/` |
| Linux (Snap) | `~/snap/obs-studio/current/.config/obs-studio/` (sandbox path) |
| Windows | `%APPDATA%\obs-studio\` (`C:\Users\<you>\AppData\Roaming\obs-studio\`) |
| Portable (any OS) | `<install_dir>/config/obs-studio/` when `portable_mode.txt` / `--portable` is used |

Layout inside the root:

```
global.ini
basic/
  profiles/
    <ProfileName>/
      basic.ini
      streamEncoder.json
      recordEncoder.json
      service.json
      recordEncoder_recent.json       # auto-generated MRU; safe to ignore
  scenes/
    <SceneCollection>.json
    <SceneCollection>.json.bak        # backup OBS writes automatically
plugin_config/<plugin_id>/...
logs/
crashes/
safe_mode.txt                         # single-instance lock (delete if stale)
```

## 2. `global.ini`

Top-level INI. Keys that matter:

```ini
[General]
Pre19Defaults=false
FirstRun=true
LastVersion=503316480        ; packed version number
ConfirmOnExit=true

[Basic]
Profile=Streaming            ; display name of current profile
ProfileDir=Streaming         ; directory under basic/profiles/
SceneCollection=Main         ; display name
SceneCollectionFile=Main     ; filename stem under basic/scenes/

[Audio]
MonitoringDeviceId=default
MonitoringDeviceName=Default

[Video]
Renderer=Metal               ; OpenGL on Linux; Direct3D 11 on Windows; Metal on macOS

[Accessibility]
OverrideColors=false
```

Only `[Basic] Profile`, `ProfileDir`, `SceneCollection`, `SceneCollectionFile` are routinely scripted. Write BOTH keys in each pair — name alone is insufficient.

## 3. `basic/profiles/<Profile>/basic.ini`

The profile's settings file. Recognized sections and keys:

### `[General]`
- `Name=<display name>` — shown in profile picker.

### `[Video]`
- `BaseCX`, `BaseCY` — canvas resolution (int).
- `OutputCX`, `OutputCY` — output (scaled) resolution.
- `FPSType=0|1|2` — 0 = common preset, 1 = integer, 2 = fraction.
- `FPSCommon=60|59.94|50|48|30|29.97|25|24 NTSC|24|...` (string).
- `FPSInt=<int>`, `FPSNum`, `FPSDen` — when `FPSType=1` or `2`.
- `ScaleType=bicubic|lanczos|area|bilinear`.
- `ColorFormat=NV12|I420|I444|P010|P216|P416|RGB` — pre-encode color format.
- `ColorSpace=601|709|2100PQ|2100HLG|sRGB`.
- `ColorRange=Partial|Full`.
- `SdrWhiteLevel=300`, `HdrNominalPeakLevel=1000`.

### `[Output]` (Advanced mode master keys)
- `Mode=Simple|Advanced`.
- `RecFilePath=<abs path>` — recordings directory.
- `RecFormat2=mkv|mp4|mov|flv|ts|m3u8|fragmented_mp4|fragmented_mov|hybrid_mp4`.
- `RecFormat=<legacy>` — OBS <28 only; newer builds ignore.
- `RecEncoder=<encoder_id>` — see Section 6.
- `StreamEncoder=<encoder_id>`.
- `FilenameFormatting=%CCYY-%MM-%DD %hh-%mm-%ss` — macros: `%CCYY`, `%YY`, `%MM`, `%DD`, `%hh`, `%mm`, `%ss`, `%a`, `%A`, `%b`, `%B`, `%d`, `%H`, `%I`, `%m`, `%p`, `%S`, `%y`, `%Y`, `%z`, `%Z`, `%FPS`, `%CRES`, `%ORES`, `%VF`.
- `OverwriteIfExists=false`, `RecRBPrefix=Replay`, `RecRBSuffix=`.
- `DelayEnable=false`, `DelaySec=20`, `DelayPreserve=true`.
- `Reconnect=true`, `RetryDelay=10`, `MaxRetries=25`.
- `BindIP=default`, `NewSocketLoopEnable=false`, `LowLatencyEnable=false`.

### `[SimpleOutput]`
- `FilePath=<abs path>`, `FileNameWithoutSpace=false`.
- `VBitrate=<kbps>`, `ABitrate=<kbps>`.
- `UseAdvanced=false`.
- `Preset=veryfast` (x264 preset when simple + x264).
- `NVENCPreset2=p5`, `QSVPreset=balanced`, `AMDPreset=balanced`.
- `RecQuality=Stream|Small|HQ|Lossless|Stream2`.
- `RecFormat2=mkv|...`.
- `RecEncoder=x264|nvenc|qsv|amd|apple|svt_av1|aom_av1`.
- `RecAEncoder=aac|opus`.
- `StreamAudioEncoder=aac|opus`.

### `[AdvOut]`
- `TrackIndex=1..6` — which audio track streams.
- `VodTrackIndex=2` (Twitch VOD track).
- `VodTrackEnabled=false`.
- `RecType=Standard|FFmpeg` — `FFmpeg` uses the `[AdvOut]` ffmpeg_* keys below.
- `RecTracks=1` — bitmask of audio tracks to record (bit 0 = track 1).
- `RecFormat2=mkv|...`.
- `RecRB=false`, `RecRBTime=20`, `RecRBSize=512`.
- `Encoder=obs_x264` (stream encoder ID override).
- `RecEncoder=none|<encoder_id>` — `none` means "use stream encoder".
- `FFFilePath=<abs>`, `FFFormat=flv|mkv|mp4|...`, `FFVEncoderId`, `FFVBitrate`, `FFAEncoderId`, `FFABitrate`, `FFExtension`, `FFCustom`, `FFMCustom`.

### `[Audio]`
- `SampleRate=44100|48000`.
- `ChannelSetup=Mono|Stereo|2.1|4.0|4.1|5.1|7.1`.
- `MeterDecayRate=23.53|11.76|8.82`.
- `PeakMeterType=0|1|2` — 0=sample peak, 2=true peak.
- `MonitoringDeviceId`, `MonitoringDeviceName`.

### `[AudioDevice<N>]`
One section per legacy mic/aux device slot. Generally leave to OBS.

### `[Hotkeys]`
One KEY per OBS action; value is a JSON-escaped array of key bindings:

```ini
[Hotkeys]
OBSBasic.StartStreaming={"bindings":[{"key":"OBS_KEY_F1","modifiers":0}]}
OBSBasic.StopStreaming={"bindings":[{"key":"OBS_KEY_F2","modifiers":0}]}
OBSBasic.StartRecording={"bindings":[{"key":"OBS_KEY_F3","modifiers":0}]}
OBSBasic.StopRecording={"bindings":[{"key":"OBS_KEY_F4","modifiers":0}]}
OBSBasic.StartReplayBuffer={"bindings":[{"key":"OBS_KEY_F5","modifiers":0}]}
OBSBasic.SaveReplayBuffer={"bindings":[{"key":"OBS_KEY_F6","modifiers":0}]}
OBSBasic.EnablePreview={"bindings":[{"key":"OBS_KEY_F7","modifiers":0}]}
```

`modifiers` bitmask: 1=Shift, 2=Ctrl, 4=Alt, 8=Cmd/Win. Key names come from libobs' key table (`OBS_KEY_A`..`OBS_KEY_Z`, `OBS_KEY_0`..`OBS_KEY_9`, `OBS_KEY_F1`..`OBS_KEY_F24`, `OBS_KEY_NUM0`..`OBS_KEY_NUM9`, `OBS_KEY_RETURN`, `OBS_KEY_ESCAPE`, `OBS_KEY_TAB`, `OBS_KEY_SPACE`, arrow keys, etc.). Qt5 (OBS 27.x) vs Qt6 (OBS 28+) differ on a handful — re-record in the GUI if porting.

## 4. `basic/profiles/<Profile>/streamEncoder.json` + `recordEncoder.json`

Pure JSON, per-encoder. Keys vary by encoder ID. Same JSON shape for both files.

### x264 (`obs_x264`) — universal fallback
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "preset": "veryfast",
  "profile": "high",
  "rate_control": "CBR",
  "tune": "zerolatency",
  "x264opts": ""
}
```
`preset`: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo.
`rate_control`: CBR, ABR, VBR, CRF.
`tune`: film, animation, grain, stillimage, psnr, ssim, fastdecode, zerolatency.

### NVENC H.264 (`jim_nvenc` modern, `ffmpeg_nvenc` legacy)
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "preset": "p5",
  "profile": "high",
  "rate_control": "CBR",
  "tune": "hq",
  "multipass": "qres",
  "lookahead": false,
  "psycho_aq": true,
  "gpu": 0,
  "max_bitrate": 0
}
```
`preset`: p1..p7 (modern), or `default`, `hq`, `hp`, `bd`, `ll`, `llhq`, `llhp`, `lossless`, `losslesshp` (legacy).
`tune`: hq, ll (low-latency), ull (ultra-low-latency), lossless.
`multipass`: disabled, qres, fullres.

### NVENC HEVC (`jim_hevc_nvenc`) / AV1 (`jim_av1_nvenc`) — same keys as above.

### QuickSync H.264 (`obs_qsv11`), HEVC (`obs_qsv11_hevc`), AV1 (`obs_qsv11_av1`)
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "target_usage": "balanced",
  "profile": "high",
  "rate_control": "CBR",
  "async_depth": 4,
  "la_depth": 0
}
```
`target_usage`: veryslow, slower, slow, balanced, fast, faster, veryfast.

### AMD AMF (`amd_amf_h264`, `h265_texture_amf`, `av1_texture_amf`)
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "preset": "quality",
  "profile": "high",
  "rate_control": "CBR"
}
```
`preset`: speed, balanced, quality.

### Apple VideoToolbox H.264 (`com.apple.videotoolbox.videoencoder.ave.avc`), HEVC (`com.apple.videotoolbox.videoencoder.ave.hevc`)
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "profile": "high",
  "rate_control": "CBR",
  "allow_frame_reordering": true,
  "require_hw_encoder": true
}
```

### SVT-AV1 (`obs_svt_av1`) / AOM AV1 (`obs_aom_av1`)
```json
{
  "bitrate": 6000,
  "keyint_sec": 2,
  "preset": 10,
  "rate_control": "CBR",
  "cpu_used": 6
}
```
SVT-AV1 `preset`: 0..13 (higher = faster).

### Lossless / FFmpeg raw output
For `RecType=FFmpeg` the keys live in `basic.ini` `[AdvOut]`, not in a JSON file.

## 5. `basic/profiles/<Profile>/service.json`

### Custom RTMP / RTMPS / SRT / HLS
```json
{
  "type": "rtmp_custom",
  "settings": {
    "server": "rtmp://live.example.com/app",
    "key": "STREAM-KEY",
    "use_auth": false,
    "username": "",
    "password": "",
    "bframes": 2
  }
}
```
`server` accepts `rtmp://`, `rtmps://`, `srt://`, `rist://`, `http(s)://` (HLS push), `whip+https://` (OBS 30+).

### Built-in service (Twitch, YouTube, Facebook, ...)
```json
{
  "type": "rtmp_common",
  "settings": {
    "service": "Twitch",
    "server": "auto",
    "key": "live_XXXXXXXX",
    "bwtest": false,
    "protocol": "RTMPS"
  }
}
```
Common `service` values: `Twitch`, `YouTube - HLS`, `YouTube - RTMPS`, `Facebook Live`, `Facebook Gaming`, `Kick`, `Trovo`, `TikTok`, `DLive`, `Restream.io - RTMP`, `Restream.io - FTL`, `Amazon IVS`.

### YouTube (OAuth — OBS-managed token)
OBS stores the OAuth connection in a separate `basic/profiles/<Profile>/youtube_connected.json`; DO NOT author this by hand. Use the GUI for first-time auth, then script everything else.

## 6. Encoder IDs cheat sheet

| Codec | Encoder ID | Platforms |
|-------|------------|-----------|
| H.264 (SW) | `obs_x264` | all |
| H.264 (NVIDIA) | `jim_nvenc` (modern), `ffmpeg_nvenc` (legacy) | Win + Linux |
| HEVC (NVIDIA) | `jim_hevc_nvenc` | Win + Linux |
| AV1 (NVIDIA) | `jim_av1_nvenc` | Win + Linux (RTX 40+) |
| H.264 (Intel QSV) | `obs_qsv11` | Win + Linux (with iHD driver) |
| HEVC (Intel QSV) | `obs_qsv11_hevc` | Win + Linux |
| AV1 (Intel QSV) | `obs_qsv11_av1` | Win + Linux (Arc) |
| H.264 (AMD AMF) | `amd_amf_h264` | Win |
| HEVC (AMD AMF) | `h265_texture_amf` | Win |
| AV1 (AMD AMF) | `av1_texture_amf` | Win |
| H.264 (Apple VT) | `com.apple.videotoolbox.videoencoder.ave.avc` | macOS |
| HEVC (Apple VT) | `com.apple.videotoolbox.videoencoder.ave.hevc` | macOS |
| AV1 SVT | `obs_svt_av1` | all |
| AV1 AOM | `obs_aom_av1` | all |

If OBS doesn't recognize the ID (missing plugin / wrong platform), it silently falls back to `obs_x264`. Verify with `check` after launch.

## 7. Scene collection JSON (`basic/scenes/<Name>.json`)

Top-level shape:

```jsonc
{
  "current_scene": "Main",
  "current_transition": "Fade",
  "transition_duration": 300,
  "name": "Main",                        // optional, usually matches filename
  "transitions": [
    {"id": "fade_transition", "name": "Fade"},
    {"id": "cut_transition",  "name": "Cut"},
    {"id": "swipe_transition","name": "Swipe",
     "settings": {"direction":"left","smoothness":0}}
  ],
  "scene_order": [{"name": "Main"}, {"name": "BRB"}],
  "sources": [ /* one entry per scene, group, and input source */ ],
  "groups":  [ /* legacy; on OBS 28+ groups are just scenes with a flag */ ],
  "quick_transitions": [
    {"fade_to_black": false, "id": 1, "name": "Cut", "duration": 300, "hotkeys":[]}
  ],
  "modules": {
    "auto-scene-switcher": {...},
    "output-timer": {...},
    "scripts-tool": []
  },
  "saved_projectors": []
}
```

Every scene, group, and input source is an entry in `sources`:

```jsonc
{
  "id": "<source_kind_id>",             // see Section 8
  "name": "Human-readable name",
  "uuid": "v4-uuid",                    // MUST match source_uuid in any items[]
  "settings": { /* kind-specific */ },
  "filters": [ { "id": "<filter_id>", "name": "...", "settings": {...} } ],
  "flags": 0,
  "volume": 1.0,
  "balance": 0.5,
  "mixers": 255,                        // bitmask: which of 6 tracks the source feeds
  "monitoring_type": 0,                 // 0=none, 1=monitor-only, 2=monitor+output
  "sync": 0,                            // audio offset in ms
  "hotkeys": {},
  "muted": false,
  "push-to-mute": false,
  "push-to-mute-delay": 0,
  "push-to-talk": false,
  "push-to-talk-delay": 0,
  "private_settings": {}
}
```

A scene's `settings.items[]` is the scene graph:

```jsonc
{
  "source_uuid": "<must equal a source uuid above>",
  "visible": true,
  "locked": false,
  "pos": {"x": 0, "y": 0},
  "scale": {"x": 1.0, "y": 1.0},
  "scale_filter": "disable",            // disable|point|bilinear|bicubic|lanczos|area
  "blend_method": "default",            // default|srgb_off
  "blend_type": "normal",               // normal|additive|subtract|screen|multiply|lighten|darken
  "rot": 0.0,
  "bounds_type": 0,                     // 0..5, see below
  "bounds_align": 0,
  "bounds": {"x": 0, "y": 0},
  "align": 5,                           // 1=left,2=right,4=top,8=bottom; 5=top-left
  "crop_left": 0, "crop_top": 0, "crop_right": 0, "crop_bottom": 0,
  "show_transition":  {"duration": 0},
  "hide_transition":  {"duration": 0}
}
```

`bounds_type`: 0=no bounds, 1=stretch to bounds, 2=scale to inner, 3=scale to outer, 4=scale to width, 5=scale to height, 6=max only.

## 8. Source kind IDs

All cross-platform unless noted. Verify per-install via `obs-docs` `reference-core-objects` or by inspecting an existing collection.

### Built-in (all platforms)
- `scene` — a scene.
- `group` — a group (acts like a scene).
- `image_source` — `{"file":"/abs/path.png","unload":false,"linear_alpha":false}`.
- `color_source_v3` — `{"color":4294967295,"width":1920,"height":1080}` (color is 0xAABBGGRR uint32).
- `text_ft2_source_v2` — `{"text":"hi","font":{"face":"Arial","size":72,"flags":0},"color1":4294967295,"color2":4294967295,"outline":false}`.
- `browser_source` — `{"url":"https://...","width":1920,"height":1080,"fps_custom":false,"fps":30,"reroute_audio":false,"css":"","shutdown":false,"restart_when_active":false}`.
- `ffmpeg_source` — `{"input":"/abs/or/url","is_local_file":true,"looping":false,"restart_on_activate":true,"clear_on_media_end":true,"hw_decode":true}`.
- `vlc_source` — `{"playlist":[{"hidden":false,"selected":false,"value":"/abs/path"}],"loop":true,"shuffle":false}`.

### Windows
- `dshow_input` — DirectShow webcam/capture card.
- `wasapi_input_capture` — mic (input).
- `wasapi_output_capture` — system audio (output monitor).
- `wasapi_process_output_capture` — per-application audio capture (Win 10 2004+).
- `monitor_capture` — WGC display capture.
- `window_capture` — WGC window capture.
- `game_capture` — DirectX/Vulkan/OpenGL game capture.
- `text_gdiplus_v3` — GDI+ text (richer than FT2).

### macOS
- `av_capture_input_v2` — webcam / capture card.
- `coreaudio_input_capture` — mic.
- `coreaudio_output_capture` — system audio (OBS 28.1+, requires a virtual driver like BlackHole).
- `screen_capture` — ScreenCaptureKit display+window+app picker (macOS 12.3+, OBS 29+).
- `display_capture` — legacy CGDisplay capture.
- `window_capture` — legacy CGWindow capture.
- `macos_game_capture` — SCK-based game capture (OBS 30+).

### Linux
- `v4l2_input` — V4L2 webcam.
- `pulse_input_capture` — PulseAudio input.
- `pulse_output_capture` — PulseAudio monitor.
- `jack_output_capture` — JACK input.
- `xshm_input` — X11 screen capture.
- `xcomposite_input` — X11 window capture.
- `pipewire-screen-capture-source` — PipeWire desktop/window/region capture (OBS 27.2+).
- `pipewire-camera-source` — PipeWire camera (OBS 29+).

## 9. CLI flags reference

Invoke OBS with flags on launch to override `global.ini` or start in a specific state:

```
obs --profile "<Profile>"                 # pick profile
obs --collection "<SceneCollection>"      # pick collection
obs --scene "<SceneName>"                 # pre-select scene at launch
obs --studio-mode                         # start with Studio Mode on
obs --startstreaming                      # begin streaming immediately
obs --startrecording                      # begin recording immediately
obs --startreplaybuffer                   # begin replay buffer
obs --startvirtualcam                     # begin virtual camera
obs --minimize-to-tray                    # minimize on launch
obs --portable                            # portable mode (config next to binary)
obs --multi                               # allow multiple instances
obs --disable-updater                     # skip update check
obs --disable-shutdown-check              # skip "was the last session clean?" prompt
obs --safe-mode                           # launch with all plugins/scripts disabled
obs --allow-opengl                        # Windows: allow OpenGL renderer
obs --unfiltered_log                      # verbose libobs log
obs --verbose                             # verbose log
obs --always-on-top
```

Binary names by platform: `obs` on macOS/Linux, `obs64.exe` on Windows (inside the install dir, e.g. `C:\Program Files\obs-studio\bin\64bit\`).

## 10. Portable mode

- **Windows:** place an empty file `portable_mode.txt` next to `obs64.exe`. Config root becomes `<install>/config/obs-studio/`.
- **Linux (AppImage):** create `portable_config/` next to the AppImage OR pass `--portable`.
- **macOS:** not officially supported — use a fresh user account or a sandboxed launcher shim to get per-run config. `brew install --cask obs` always uses `~/Library/Application Support/obs-studio/`.

## 11. Plugin config

`plugin_config/<plugin_id>/...` holds per-plugin settings. Examples:
- `plugin_config/obs-websocket/config.json` — server port (default 4455), password hash, auth enabled.
- `plugin_config/advanced-scene-switcher/` — config.json.
- `plugin_config/obs-studio-srt/` — SRT protocol options.

Most plugins JSON-dump their config here. Authoring by hand is plugin-specific; check the plugin's README.

## 12. Logs + crashes

- `logs/<YYYY-MM-DD HH-MM-SS>.txt` — one per launch, last ~10 kept.
- `crashes/<YYYY-MM-DD HH-MM-SS>.txt` — crash dumps (stack trace + plugin list).

Useful for verifying your config parsed correctly — first 200 lines of a fresh log list every profile/collection/plugin loaded and any parse errors.
