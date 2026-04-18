---
name: obs-config
description: >
  Install and configure OBS Studio programmatically: install via brew cask / winget / Flatpak / apt, author profiles (basic.ini, streamEncoder.json, recordEncoder.json), author scene collections (scenes JSON), manage global.ini, set defaults for encoder / output / audio / hotkeys, cross-platform config paths. Use when the user asks to install OBS, set up an OBS profile, create a scene collection from code, configure OBS defaults without the GUI, edit basic.ini, manage multiple OBS profiles, or script a fresh OBS install with known-good settings.
argument-hint: "[operation]"
---

# obs-config

**Context:** $ARGUMENTS

Install OBS Studio and author its on-disk configuration (profiles, scene collections, encoder JSON, `global.ini`, `service.json`) without touching the GUI. Everything lives in a single per-user config directory whose location differs per OS — get that wrong and OBS will silently create a blank second install.

## Quick start

- **Install OBS on macOS:** → Step 1 (`brew install --cask obs`)
- **Install OBS on Windows/Linux:** → Step 1
- **Find where OBS stores config:** → Step 2
- **Create a streaming profile from code:** → Step 3
- **Create a scene collection from code:** → Step 4
- **Verify the config before launching OBS:** → Step 5

## When to use

- Scripting a fresh OBS install with known-good defaults (CI box, new streamer, classroom lab).
- Provisioning N identical OBS machines (bitrate, encoder, keyframe interval, hotkeys, service/key all baked in).
- Migrating a profile/collection between machines without the GUI's "Import" dialog.
- Pre-seeding scene collections from a template before handing the machine to a non-technical user.

Do NOT use this skill to remote-control a running OBS — that is `obs-websocket`. Do NOT use it to write a Python/Lua script that runs inside OBS — that is `obs-scripting`. Do NOT use it to build a compiled C++ plugin — that is `obs-plugins`.

## Step 1 — Install OBS per platform

Run the right installer for your OS. `scripts/obsconfig.py install --platform auto` will pick and print the command (use `--dry-run` first).

- **macOS:** `brew install --cask obs` — signed + notarized, handles Gatekeeper. A manual `.dmg` install requires `sudo xattr -rd com.apple.quarantine /Applications/OBS.app`.
- **Windows:** `winget install -e --id OBSProject.OBSStudio` or `choco install obs-studio`.
- **Ubuntu / Debian:** `sudo add-apt-repository ppa:obsproject/obs-studio && sudo apt update && sudo apt install obs-studio`.
- **Any Linux with Flatpak:** `flatpak install flathub com.obsproject.Studio`. Note: Flatpak stores config under `~/.var/app/com.obsproject.Studio/config/obs-studio/`, NOT `~/.config/obs-studio/`.
- **AppImage:** download from `github.com/obsproject/obs-studio/releases`, `chmod +x`, run. Portable-ish — config still goes to `~/.config/obs-studio/`.

## Step 2 — Locate the config dir

OBS uses ONE per-user config root. Everything else is relative to it.

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/obs-studio/` |
| Linux (native) | `~/.config/obs-studio/` |
| Linux (Flatpak) | `~/.var/app/com.obsproject.Studio/config/obs-studio/` |
| Windows | `%APPDATA%\obs-studio\` (i.e. `C:\Users\<you>\AppData\Roaming\obs-studio\`) |

Layout inside it:

```
<CONFIG_DIR>/
  global.ini                        # last-used profile, collection, version
  basic/
    profiles/
      <ProfileName>/
        basic.ini                   # video/output/audio settings
        streamEncoder.json          # encoder-specific JSON for streaming
        recordEncoder.json          # encoder-specific JSON for recording
        service.json                # streaming service (Twitch/YouTube/custom)
    scenes/
      <SceneCollection>.json        # scene graph, sources, transitions
  plugin_config/<plugin_id>/...     # per-plugin JSON/INI
  logs/                             # rolling logs (last ~10 sessions)
  crashes/                          # crash dumps
```

`<ProfileName>` is a directory; `<SceneCollection>.json` is a single file whose basename equals the collection's display name. DO NOT hardcode `~/.config/obs-studio` on macOS — that path does not exist there and OBS will not read from it.

## Step 3 — Create/edit a profile

A profile is a directory under `basic/profiles/`. At minimum it needs `basic.ini`.

```ini
[General]
Name=Streaming

[Video]
BaseCX=1920
BaseCY=1080
OutputCX=1920
OutputCY=1080
FPSType=0
FPSCommon=60

[Output]
Mode=Advanced
RecFilePath=/Users/you/Videos
RecFormat2=mkv
RecEncoder=obs_x264
StreamEncoder=obs_x264

[SimpleOutput]
VBitrate=6000
ABitrate=160
RecQuality=Stream

[AdvOut]
TrackIndex=1
RecType=Standard
RecTracks=1

[Audio]
SampleRate=48000
ChannelSetup=Stereo
```

Encoder-specific settings live as JSON siblings (NOT inside basic.ini):

```json
// streamEncoder.json — for obs_x264
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

NVENC / QSV / VideoToolbox use different keys — see `references/config.md`.

Service (streaming destination) lives in `service.json` alongside `basic.ini`:

```json
{
  "type": "rtmp_custom",
  "settings": {
    "server": "rtmp://live.example.com/app",
    "key": "STREAM-KEY-HERE",
    "use_auth": false
  }
}
```

For built-in services use `"type": "rtmp_common"` with `{"service":"Twitch","server":"auto","key":"live_..."}`.

## Step 4 — Create/edit a scene collection

A scene collection is ONE JSON file at `basic/scenes/<Name>.json`. Filename basename = collection display name. Minimum viable file:

```json
{
  "current_scene": "Main",
  "current_transition": "Fade",
  "transition_duration": 300,
  "transitions": [
    {"id": "fade_transition", "name": "Fade"}
  ],
  "scene_order": [{"name": "Main"}],
  "sources": [
    {
      "id": "scene",
      "name": "Main",
      "uuid": "11111111-1111-4111-8111-111111111111",
      "settings": {
        "items": [
          {
            "source_uuid": "22222222-2222-4222-8222-222222222222",
            "visible": true,
            "locked": false,
            "pos": {"x": 0, "y": 0},
            "scale": {"x": 1.0, "y": 1.0},
            "bounds_type": 0,
            "align": 5
          }
        ]
      }
    },
    {
      "id": "browser_source",
      "name": "Overlay",
      "uuid": "22222222-2222-4222-8222-222222222222",
      "settings": {
        "url": "https://example.com/overlay",
        "width": 1920,
        "height": 1080,
        "fps_custom": false,
        "reroute_audio": false
      },
      "filters": [],
      "flags": 0,
      "volume": 1.0,
      "balance": 0.5,
      "hotkeys": {}
    }
  ],
  "groups": [],
  "quick_transitions": [],
  "modules": {}
}
```

Source kinds accepted by top-level `id` (platform-specific noted):
`scene`, `group`, `image_source`, `color_source_v3`, `text_gdiplus_v3` (Windows), `text_ft2_source_v2`, `browser_source`, `ffmpeg_source`, `vlc_source`,
`dshow_input` / `wasapi_input_capture` / `monitor_capture` / `window_capture` / `game_capture` (Windows),
`av_capture_input_v2` / `coreaudio_input_capture` / `display_capture` / `window_capture` / `macos_game_capture` (macOS),
`v4l2_input` / `pulse_input_capture` / `xshm_input` / `pipewire-screen-capture-source` (Linux).

See `references/config.md` for the full catalog and platform availability.

## Step 5 — Verify and point OBS at the new config

Close OBS FIRST — if OBS is running while you edit, it will overwrite your changes on quit.

Set the default profile + collection so OBS picks them up on next launch. Edit `global.ini`:

```ini
[Basic]
Profile=Streaming
ProfileDir=Streaming
SceneCollection=Main
SceneCollectionFile=Main
```

Or launch with CLI flags (equivalent, one-off):

```
obs --profile "Streaming" --collection "Main"
# Other useful flags:
# --studio-mode            launch with Studio Mode on
# --startstreaming         begin streaming immediately
# --startrecording         begin recording immediately
# --startreplaybuffer      begin replay buffer immediately
# --startvirtualcam        begin virtual cam immediately
# --minimize-to-tray       hide window on launch
# --portable               force portable mode (looks for config next to the binary)
# --multi                  allow multiple OBS instances (single-instance lock override)
# --safe-mode / --disable-shutdown-check
```

Then from the checker:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py check --verbose
```

## Available scripts

- **`scripts/obsconfig.py`** — stdlib-only CLI: detect platform, install OBS, list/create/delete profiles and scene collections, set encoder + service, export/import a profile+collection bundle as zip.

## Workflow

1. See what's already there:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py check
   ```
2. Install OBS if missing:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py install --platform auto --dry-run
   ```
3. Create profile + collection from templates:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py profile create --name Streaming --template 1080p60_stream
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py collection create --name Main --template browser-overlay
   ```
4. Wire streaming destination:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py service set --profile Streaming \
     --type rtmp_custom --server rtmp://live.example.com/app --key KEY
   ```
5. Make them default:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py profile set-default --name Streaming
   uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py collection set-default --name Main
   ```
6. Launch OBS and verify.

## Reference docs

- Read [`references/config.md`](references/config.md) for the full `basic.ini` key list, every source-kind ID per platform, encoder JSON shape per codec, `global.ini` keys, `service.json` variants, CLI flags, and portable mode per OS.

## Gotchas

- **Config path differs per platform.** macOS = `~/Library/Application Support/obs-studio/`, NOT `~/.config/obs-studio/`. Flatpak on Linux uses `~/.var/app/com.obsproject.Studio/config/obs-studio/`.
- **OBS must not be running when you edit.** OBS reads config at launch and overwrites on quit — concurrent edits get stomped. Quit OBS, then edit.
- **Scene collection UUIDs must match.** A scene's `items[].source_uuid` MUST equal the target source's top-level `uuid`, and all UUIDs must be valid v4. Mismatch = the source silently doesn't render in that scene.
- **Filename = collection name.** The collection displayed as "My Stream" lives at `basic/scenes/My Stream.json`. Spaces and unicode are allowed; case matters on Linux/macOS.
- **Profile is a directory, not a file.** `basic/profiles/Streaming/` — not `Streaming.ini`.
- **Switching profile needs a hint.** Either pass `--profile "Name"` on launch, or edit `global.ini` `[Basic] Profile=Name` + `ProfileDir=Name` before launch.
- **Encoder IDs vary by platform.** `obs_x264` (everywhere), `obs_qsv11` (Intel), `jim_nvenc` / `ffmpeg_nvenc` (NVIDIA), `com.apple.videotoolbox.videoencoder.ave.avc` (macOS HW H.264), `obs_svt_av1`, `obs_aom_av1`, `amd_amf_h264` (Windows AMD). An unknown ID = OBS silently falls back to x264.
- **RecFormat2, not RecFormat.** OBS 28+ uses `RecFormat2=mkv`; old `RecFormat=mkv` is ignored in newer builds. Write both if you need to support mixed versions.
- **Hotkeys.** In `basic.ini` under `[Hotkeys]`, each value is a JSON-escaped list like `"OBSBasic.StartStreaming": "[{\"key\":\"OBS_KEY_F1\"}]"`. Key names changed subtly between Qt5 (OBS 27.x) and Qt6 (OBS 28+).
- **macOS system audio needs a virtual driver.** Native system-audio capture is unsupported; install BlackHole or Loopback and reference the device by name.
- **Linux Wayland capture is limited.** `monitor_capture` may not work — use `pipewire-screen-capture-source` (OBS 28+) or fall back to XWayland.
- **Portable mode on Windows.** Drop an empty `portable_mode.txt` next to `obs64.exe`; OBS then writes config to `config/` under the install dir.
- **First launch creates "Untitled" profile + collection.** These are safe to delete/rename once your real ones exist and are set as default in `global.ini`.
- **Back up `basic/` first.** `cp -r <config>/basic <config>/basic.bak` before any scripted edits.

## Examples

### Example 1: Provision a 1080p60 Twitch streamer on macOS

```bash
brew install --cask obs
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py profile create \
  --name Twitch1080p60 --template 1080p60_stream
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py encoder set \
  --profile Twitch1080p60 --codec x264 --bitrate 6000 --preset veryfast
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py service set \
  --profile Twitch1080p60 --type rtmp_common --server auto --key live_XXX
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py collection create \
  --name Main --template webcam
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py profile set-default --name Twitch1080p60
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py collection set-default --name Main
open -a OBS
```

### Example 2: Clone a working setup to a second machine

```bash
# On machine A
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py export \
  --profile Twitch1080p60 --output twitch.zip

# Copy twitch.zip to machine B, then:
uv run ${CLAUDE_SKILL_DIR}/scripts/obsconfig.py import --archive twitch.zip
```

### Example 3: One scene with a browser overlay on top of a display capture (macOS)

Write `basic/scenes/Main.json` with two sources (`display_capture` + `browser_source`) inside a `scene` whose `items[]` references both by UUID. See Step 4 for the shape — add a second `items[]` entry and a second top-level source with matching UUIDs.

## Troubleshooting

### Error: OBS launches but shows "Untitled" profile, ignores my new one

Cause: `global.ini` still points at the default, OR the profile directory name doesn't match `[Basic] ProfileDir=`.
Solution: Open `global.ini`, set both `Profile=Name` AND `ProfileDir=Name` to your profile's directory name (case-sensitive on macOS/Linux). Close OBS fully before editing.

### Error: Scene collection loads but a source is missing or shows "Source not found"

Cause: UUID mismatch between `sources[].uuid` and the referencing `items[].source_uuid`, or an invalid (non-v4) UUID.
Solution: Regenerate UUIDs with `python -c "import uuid; print(uuid.uuid4())"` and make sure every `items[].source_uuid` appears exactly once as a top-level `sources[].uuid`.

### Error: Encoder falls back to x264 on a machine with an NVIDIA GPU

Cause: Wrong encoder ID in `basic.ini` (`StreamEncoder`/`RecEncoder`) or `streamEncoder.json` keys don't match the NVENC encoder.
Solution: Use `jim_nvenc` (modern) or `ffmpeg_nvenc` (legacy). The JSON keys for NVENC are different from x264 — see `references/config.md`.

### Error: Recording file path is wrong / recordings go to Desktop

Cause: `RecFilePath` under `[Output]` (Advanced) or `[SimpleOutput]` (Simple) is empty or points somewhere else.
Solution: Set `Mode=Advanced` plus `RecFilePath=/absolute/path`, AND `RecFormat2=mkv`. Restart OBS.

### Error: "Cannot launch, another instance is already running" on CI

Cause: Single-instance lock from a stale session.
Solution: Pass `--multi` to the CLI, OR delete the lock file (`~/.config/obs-studio/safe_mode.txt` / macOS equivalent) before launch.
