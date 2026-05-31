---
name: obs
description: >
  OBS Studio control, configuration, scripting, and plugin authoring. Use when the user asks to remote-control OBS, switch OBS scenes from a script, start or stop recording or streaming programmatically, send an obs-websocket v5 request, subscribe to CurrentProgramSceneChanged or RecordStateChanged events, connect to ws localhost 4455, authenticate with the SHA-256 challenge handshake, toggle sources filters or audio mixer, fire a RequestBatch, install OBS via brew winget flatpak or apt, author a profile basic.ini streamEncoder.json or service.json, create a scene collection from JSON, set defaults without the GUI, write an OBS Python or Lua script, register script_load script_properties or frontend event callbacks, hook OBS signals, add a script hotkey or timer, scaffold a C++ plugin from obs-plugintemplate, register obs_source_info obs_output_info or obs_encoder_info, install StreamFX Advanced Scene Switcher Move NDI or other community plugins, or look up an OBS API signature.
argument-hint: "[task]"
---

# OBS

Control OBS Studio end to end: remote-control a running instance over obs-websocket v5, author its on-disk config (profiles, scene collections, encoders, services), write Python/Lua scripts that run inside OBS, build native C++ plugins, and look up the real OBS / obs-websocket API surface.

## When to use

- Remote-control a running OBS from a CLI, bot, or web UI — scene switches, record/stream toggles, mixer, RequestBatch, live events.
- Install OBS and author profiles / scene collections / encoder JSON / `service.json` without the GUI.
- Write Python or Lua scripts that run inside OBS (lifecycle callbacks, property UIs, frontend events, signals, hotkeys, timers).
- Author a native C/C++ plugin (source / filter / output / encoder / service) or install a community plugin.
- Verify any OBS or obs-websocket API name before quoting it.

## Techniques

- Read `references/websocket.md` when remote-controlling a running OBS over obs-websocket v5 (auth handshake, Requests, Events, RequestBatch, `scripts/wsctl.py`).
- Read `references/config.md` when installing OBS or authoring profiles, scene collections, encoders, or services on disk (`scripts/obsconfig.py`). Deep catalog in `references/config-catalog.md`.
- Read `references/scripting.md` when writing Python/Lua scripts that run inside OBS (`scripts/scaffold-script.py`). Full API in `references/api.md`.
- Read `references/plugins.md` when authoring a C++ plugin or installing a community plugin (`scripts/plugins.py`). Full field catalog in `references/plugins-catalog.md`.

## Docs lookup

ALWAYS use `references/docs-search.md` and its `scripts/obsdocs.py` BEFORE recommending an obs-websocket Request/Event name, an `obs_*` C function, a scripting binding, or a plugin struct field. It is the anti-hallucination guardrail — if `search --query "<name>"` returns zero hits, the API does not exist. `SetCurrentScene` (v4) vs `SetCurrentProgramScene` (v5) is the classic trap.

## Gotchas

- **obs-websocket v5 ≠ v4.** v4 is EOL and incompatible. Target `rpcVersion: 1`. Auth = double SHA-256 with STANDARD base64: `secret = b64(sha256(pw+salt))`, `auth = b64(sha256(secret+challenge))`.
- **Event `All` mask is 4095, not 2047** (includes Vendors 512 + Canvases 2048). High-volume bits 16–19 (`InputVolumeMeters` etc.) are excluded — OR them in explicitly, and only if you'll consume them (they flood the socket).
- **Config path is per-OS.** macOS = `~/Library/Application Support/obs-studio/`, NOT `~/.config/obs-studio/`. Flatpak = `~/.var/app/com.obsproject.Studio/config/obs-studio/`. Quit OBS before editing — it overwrites config on quit.
- **Scene-collection UUIDs must match.** Every `items[].source_uuid` must equal a top-level `sources[].uuid` (valid v4). Mismatch = the source silently doesn't render. Use `RecFormat2`, not `RecFormat`, on OBS 28+.
- **OBS scripting wants Python 3.11 exactly** (OBS 30). 3.10/3.12 silently fail to load. Reference counting is manual — every `obs_get_source_by_name` / `obs_frontend_get_scenes` needs a paired `_release`, or OBS leaks until it crashes. No Qt, no hot reload (hit Refresh).
- **`OBS_DECLARE_MODULE()` appears exactly once** per plugin binary. `obs_register_source` needs a `static` (outlives unload) `obs_source_info`. `bfree()` anything `bmalloc`/`bzalloc`/`bstrdup` allocated. `gs_*` graphics calls run on the graphics thread only.
- **Encoder/source/input-kind IDs are platform-specific.** `coreaudio_input_capture` (macOS) vs `wasapi_input_capture` (Windows) vs `pulse_input_capture` (Linux); `jim_nvenc` vs `obs_x264`. An unknown encoder ID silently falls back to x264. Call `GetInputKindList` before creating an input over websocket.
- **macOS unsigned plugins** need `sudo xattr -rd com.apple.quarantine ...plugins/<name>.plugin`. Plugins are 64-bit only and pinned to an OBS major ABI.

## Scripts

All stdlib-only, `uv run`, support `--dry-run` / `--verbose`, non-interactive.

- `scripts/wsctl.py` — obs-websocket v5 client (ping, scene-switch, record, mute, replay-buffer, events, request, batch). Auto-discovers URL/password from OBS config; override via `OBS_WEBSOCKET_URL` / `OBS_WEBSOCKET_PASSWORD`.
- `scripts/obsconfig.py` — install OBS, manage profiles + scene collections, set encoder + service, export/import bundles.
- `scripts/scaffold-script.py` — scaffold Python/Lua scripts (lifecycle, scene-switcher, hotkey, timer), detect env, install into OBS.
- `scripts/plugins.py` — scaffold/build/install a C++ plugin, install community plugins.
- `scripts/obsdocs.py` — search/section/fetch/index official OBS + obs-websocket docs (anti-hallucination).
