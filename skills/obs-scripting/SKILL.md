---
name: obs-scripting
description: >
  Write Python / Lua scripts that run inside OBS Studio: script lifecycle (script_load, script_unload, script_description, script_properties, script_defaults, script_update, script_save, script_tick), registering frontend event callbacks, hooking signals, accessing sources + scenes + filters from a script, using obspython / obslua bindings, building script UIs with obs_properties_t. Use when the user asks to write an OBS Python script, write an OBS Lua script, automate something inside OBS without a compiled plugin, add a script-side hotkey, build a tools-menu script, or hook OBS signals from Python.
argument-hint: "[action]"
---

# OBS Scripting

Write Python or Lua scripts that run INSIDE OBS Studio. Loaded via Tools → Scripts. The `obspython` / `obslua` modules expose a pragmatic subset of libobs: lifecycle callbacks, property UIs, frontend events, signals, hotkeys, timers. There is NO Qt access, NO top-level menu injection, NO compiled binary — for those, use `obs-plugins`.

## Quick start

- **Brand-new script:** → Step 1 (locate dir + enable Python) → Step 2 (skeleton)
- **Add a config UI:** → Step 3 (properties + settings)
- **React to stream/record/scene events:** → Step 4 (frontend events + signals)
- **Hotkey or periodic task:** → Step 5 (hotkeys + timers)
- **Verify an API exists:** `obs-docs` skill, `obsdocs.py search --query <name> --page scripting`

## When to use

- Automate something inside OBS without compiling a C++ plugin.
- Add a per-install tool with a small UI (scene switcher, auto-record on signal, hotkey macro).
- Integrate with external services from inside OBS (HTTP poll, write file on scene change).
- Prototype behavior that would later become a real plugin.

## Step 1 — Locate the scripts dir and enable Python

Scripts can live ANYWHERE on disk. You add them via OBS: **Tools → Scripts → `+`**. OBS remembers the path across launches (stored in `global.ini`).

**Lua needs no setup.** Python requires pointing OBS at a matching interpreter.

**OBS 30+ on macOS / Windows / Linux wants Python 3.11 specifically.** Using 3.10 or 3.12 silently fails to load — the script does not appear in the list. Install python.org 3.11 (or Homebrew `python@3.11`), then:

- **macOS:** Tools → Scripts → **Python Settings** tab → path = `/Library/Frameworks/Python.framework/Versions/3.11`. Homebrew path: `/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11` (Apple Silicon) or `/usr/local/opt/python@3.11/Frameworks/Python.framework/Versions/3.11` (Intel).
- **Linux:** path = `/usr/lib/python3.11` (or your distro's equivalent, e.g. `/usr/lib64/python3.11`).
- **Windows:** path = `C:\Users\<you>\AppData\Local\Programs\Python\Python311\`.

Check which version OBS wants in its Help → Log Files → View Current Log (grep for "Python").

Run `uv run ${CLAUDE_SKILL_DIR}/scripts/scaffold-script.py check` to auto-detect.

## Step 2 — Minimal Python skeleton

Every script exports lifecycle functions OBS calls by name. All are optional.

```python
import obspython as obs

greeting = "Hello"
count = 5

def script_description():
    return "Example OBS Python script."

def script_properties():
    p = obs.obs_properties_create()
    obs.obs_properties_add_text(p, "greeting", "Greeting", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(p, "count", "Count", 1, 100, 1)
    obs.obs_properties_add_button(p, "do_it", "Do It", on_click)
    return p

def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "greeting", "Hello")
    obs.obs_data_set_default_int(settings, "count", 5)

def script_update(settings):
    global greeting, count
    greeting = obs.obs_data_get_string(settings, "greeting")
    count = obs.obs_data_get_int(settings, "count")

def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)

def script_unload():
    pass

def on_click(props, prop):
    obs.script_log(obs.LOG_INFO, f"Clicked; greeting={greeting}, count={count}")
    return False  # True to force a property-UI refresh

def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
        scene = obs.obs_frontend_get_current_scene()
        name = obs.obs_source_get_name(scene)
        obs.obs_source_release(scene)
        obs.script_log(obs.LOG_INFO, f"Scene: {name}")
```

Lua equivalent uses `obs = obslua` and `function script_load(settings)` syntax — see `scripts/scaffold-script.py new-lua`.

## Step 3 — Properties UI and settings

`script_properties()` is called often (every time the property pane repaints). Do not do expensive work there. Property types:

- `obs_properties_add_text(p, name, desc, OBS_TEXT_DEFAULT | OBS_TEXT_PASSWORD | OBS_TEXT_MULTILINE | OBS_TEXT_INFO)`
- `obs_properties_add_int(p, name, desc, min, max, step)` / `obs_properties_add_int_slider` / `..._float` / `..._float_slider`
- `obs_properties_add_bool(p, name, desc)`
- `obs_properties_add_list(p, name, desc, OBS_COMBO_TYPE_LIST|EDITABLE, OBS_COMBO_FORMAT_STRING|INT|FLOAT)` then `obs_property_list_add_string|int|float(prop, label, value)`
- `obs_properties_add_path(p, name, desc, OBS_PATH_FILE | OBS_PATH_FILE_SAVE | OBS_PATH_DIRECTORY, filter, default_path)`
- `obs_properties_add_color(p, name, desc)` / `obs_properties_add_color_alpha` / `obs_properties_add_font`
- `obs_properties_add_button(p, name, text, callback)` — callback returns `True` to refresh UI
- `obs_properties_add_editable_list(p, name, desc, OBS_EDITABLE_LIST_TYPE_STRINGS|FILES|FILES_AND_URLS, filter, default_path)`
- `obs_properties_add_group(p, name, desc, OBS_GROUP_NORMAL|CHECKABLE, sub_props)`

Settings get/set by type: `obs_data_get_int|string|bool|double`, `obs_data_set_default_int|string|bool|double`. `script_update(settings)` fires on every property change AND on first load — make it idempotent.

Populate a list of scenes dynamically:

```python
def script_properties():
    p = obs.obs_properties_create()
    lst = obs.obs_properties_add_list(p, "target_scene", "Target scene",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    scenes = obs.obs_frontend_get_scenes()
    if scenes is not None:
        for s in scenes:
            name = obs.obs_source_get_name(s)
            obs.obs_property_list_add_string(lst, name, name)
        obs.source_list_release(scenes)
    return p
```

## Step 4 — Frontend events and signals

Register once in `script_load`. Callback takes one int `event` arg:

```python
def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)

def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED:
        ...
    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        ...
```

Full enum: `STREAMING_STARTING`, `STREAMING_STARTED`, `STREAMING_STOPPING`, `STREAMING_STOPPED`, `RECORDING_STARTING`, `RECORDING_STARTED`, `RECORDING_STOPPING`, `RECORDING_STOPPED`, `SCENE_CHANGED`, `SCENE_LIST_CHANGED`, `TRANSITION_CHANGED`, `TRANSITION_STOPPED`, `TRANSITION_LIST_CHANGED`, `SCENE_COLLECTION_CHANGED`, `SCENE_COLLECTION_LIST_CHANGED`, `PROFILE_CHANGED`, `PROFILE_LIST_CHANGED`, `EXIT`, `REPLAY_BUFFER_STARTING`, `REPLAY_BUFFER_STARTED`, `REPLAY_BUFFER_STOPPING`, `REPLAY_BUFFER_STOPPED`, `REPLAY_BUFFER_SAVED`, `STUDIO_MODE_ENABLED`, `STUDIO_MODE_DISABLED`, `PREVIEW_SCENE_CHANGED`, `SCENE_COLLECTION_CLEANUP`, `FINISHED_LOADING`, `RECORDING_PAUSED`, `RECORDING_UNPAUSED`, `TRANSITION_DURATION_CHANGED`, `VIRTUALCAM_STARTED`, `VIRTUALCAM_STOPPED`, `TBAR_VALUE_CHANGED`.

Per-source signals — hook fine-grained events (item shown/hidden, audio muted, etc.):

```python
def hook_source(name):
    src = obs.obs_get_source_by_name(name)
    if src:
        sh = obs.obs_source_get_signal_handler(src)
        obs.signal_handler_connect(sh, "item_visible", on_visible)
        obs.obs_source_release(src)

def on_visible(calldata):
    item_visible = obs.calldata_bool(calldata, "visible")
    obs.script_log(obs.LOG_INFO, f"visible={item_visible}")
```

## Step 5 — Hotkeys and timers

Hotkeys survive across launches ONLY if you pair save/load:

```python
hotkey_id = obs.OBS_INVALID_HOTKEY_ID

def script_load(settings):
    global hotkey_id
    hotkey_id = obs.obs_hotkey_register_frontend(
        "my_script.fire", "Fire my script action", on_hotkey)
    hk_arr = obs.obs_data_get_array(settings, "hotkey_my_script.fire")
    obs.obs_hotkey_load(hotkey_id, hk_arr)
    obs.obs_data_array_release(hk_arr)

def script_save(settings):
    hk_arr = obs.obs_hotkey_save(hotkey_id)
    obs.obs_data_set_array(settings, "hotkey_my_script.fire", hk_arr)
    obs.obs_data_array_release(hk_arr)

def on_hotkey(pressed):
    if pressed:
        obs.script_log(obs.LOG_INFO, "Fired")
```

Timers run on the OBS UI thread. `timer_add(callback, millis)` and `timer_remove(callback)`. One-shot idiom: call `timer_remove(self)` from inside the callback.

```python
def every_second():
    obs.script_log(obs.LOG_INFO, "tick")

def script_load(settings):
    obs.timer_add(every_second, 1000)

def script_unload():
    obs.timer_remove(every_second)
```

## Available scripts

- **`scripts/scaffold-script.py`** — stdlib-only scaffolder. Subcommands:
  - `check` — detect OBS install, scripts dir, Python version.
  - `new-python --name NAME --outdir DIR` — canonical Python lifecycle stub.
  - `new-lua --name NAME --outdir DIR` — Lua equivalent.
  - `new-scene-switcher --outdir DIR` — hotkey + frontend-event template.
  - `new-hotkey --outdir DIR` — hotkey with save/load pattern.
  - `new-timer --outdir DIR` — periodic-task template.
  - `install --script FILE [--auto-load]` — copy into OBS scripts dir, optionally edit `global.ini` to autoload.
  - Global flags: `--dry-run`, `--verbose`.

## Workflow

```bash
# 1. Detect environment
uv run ${CLAUDE_SKILL_DIR}/scripts/scaffold-script.py check

# 2. Create a new script from template
uv run ${CLAUDE_SKILL_DIR}/scripts/scaffold-script.py new-python \
    --name my_scene_switcher --outdir ~/OBS-scripts

# 3. Open OBS → Tools → Scripts → + → select the file
# 4. Iterate: edit file, hit Refresh button in Scripts dialog (scripts do NOT hot-reload)
```

## Reference docs

- Read [`references/api.md`](references/api.md) for the full lifecycle / properties / settings / hotkey / signal / timer reference with every enum value.
- Authoritative upstream: `obs-docs` skill → `obsdocs.py search --query <name> --page scripting`.

## Gotchas

- **Python version is a hard ABI match.** OBS 30 ships against CPython 3.11 — 3.10 or 3.12 silently fail to load. On macOS, Homebrew's default `python3` may be newer than 3.11; install `python@3.11` explicitly or use the python.org installer.
- **Scripts run on the OBS UI thread.** Never call blocking I/O or `time.sleep` in `script_tick`, a property callback, or an event callback — OBS will freeze. Offload to a thread or use `timer_add`.
- **Reference counting is manual.** OBS source/scene/data objects returned from `obs_get_source_by_name`, `obs_frontend_get_current_scene`, `obs_frontend_get_scenes`, `obs_enum_sources`, `obs_source_get_settings` are reference-incremented. You MUST release:
  - Single source / scene → `obs_source_release(src)` / `obs_scene_release(scene)`
  - List from `obs_enum_sources` or `obs_frontend_get_scenes` → `source_list_release(lst)`
  - `obs_data_t` → `obs_data_release(d)`
  - `obs_data_array_t` → `obs_data_array_release(arr)`
  - Python GC does NOT do this. Leaks grow silently until OBS crashes.
- **`script_properties()` is called many times.** Don't enumerate sources or hit the network inside it. Cache.
- **`script_update(settings)` fires on first load AND on every property change.** Make it idempotent.
- **Hotkey save/load must pair.** Omit `script_save` and the user's keybinding is erased every launch.
- **No hot reload.** Editing a `.py` on disk does nothing — hit the refresh (↻) button in Tools → Scripts, or toggle the checkbox.
- **No Qt.** You cannot create `QDialog`, `QDockWidget`, menu items, etc. from a script. For that you need a compiled C++ plugin (see `obs-plugins`).
- **`obs_properties_add_button` callback return value:** `True` tells OBS to refresh the property pane; `False` leaves it. Returning nothing = `None` = falsy = fine.
- **Lua vs Python string handling:** Python API calls that take strings just take `str`. Some lower-level calldata accessors may need bytes. Lua has no such ambiguity.
- **Module name is lowercase.** Python: `import obspython as obs`. Lua: `obs = obslua` (it's already a global).
- **Logging:** `obs.script_log(obs.LOG_INFO, "msg")`. Levels: `LOG_DEBUG`, `LOG_INFO`, `LOG_WARNING`, `LOG_ERROR`. Visible in Tools → Scripts → Script Log.

## Examples

### Auto-switch to a scene on streaming-stopped

```python
import obspython as obs

target_scene_name = ""

def script_description():
    return "Switch to a chosen scene when streaming stops."

def script_properties():
    p = obs.obs_properties_create()
    lst = obs.obs_properties_add_list(p, "target", "Target scene",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    scenes = obs.obs_frontend_get_scenes()
    if scenes is not None:
        for s in scenes:
            n = obs.obs_source_get_name(s)
            obs.obs_property_list_add_string(lst, n, n)
        obs.source_list_release(scenes)
    return p

def script_update(settings):
    global target_scene_name
    target_scene_name = obs.obs_data_get_string(settings, "target")

def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)

def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and target_scene_name:
        src = obs.obs_get_source_by_name(target_scene_name)
        if src:
            obs.obs_frontend_set_current_scene(src)
            obs.obs_source_release(src)
```

### Periodic stats log

```python
import obspython as obs

def tick():
    scene = obs.obs_frontend_get_current_scene()
    if scene:
        obs.script_log(obs.LOG_INFO, f"now on: {obs.obs_source_get_name(scene)}")
        obs.obs_source_release(scene)

def script_load(settings):
    obs.timer_add(tick, 5000)

def script_unload():
    obs.timer_remove(tick)
```

## Troubleshooting

### Script does not appear in the list / "Failed to load Python"

Cause: Python version mismatch or path points at the wrong install.
Solution: Help → Log Files → View Current Log. Look for the line that says which Python ABI OBS wants (e.g. `Python version: 3.11.x`). Install exactly that minor version from python.org (or Homebrew `python@3.11`), then set Tools → Scripts → Python Settings to that install's `Frameworks/Python.framework/Versions/3.11` (macOS) / install root (Win/Linux). Restart OBS.

### "module 'obspython' has no attribute 'X'"

Cause: The binding wasn't exposed to scripting (C API only), or a typo.
Solution: check the obs-docs skill (if installed separately) or consult docs.obsproject.com directly. If zero hits on `scripting`, retry without `--page` — if it only exists in reference-core, you need a compiled plugin.

### OBS freezes when I click my button

Cause: Blocking I/O in the callback, which runs on the UI thread.
Solution: Move the work into a `threading.Thread` or schedule via `timer_add` with a short interval and a done flag.

### Hotkey resets every time I restart OBS

Cause: Missing or mismatched `script_save`. The key used in `obs_data_set_array` must exactly match the key in `obs_data_get_array` in `script_load`.
Solution: Use the pattern in Step 5 literally — same string both sides.

### Memory grows during a long stream

Cause: Leaked source / data / array references. Each `obs_get_source_by_name`, `obs_frontend_get_current_scene`, `obs_frontend_get_scenes`, `obs_enum_sources`, `obs_source_get_settings`, `obs_data_get_array` needs a paired release.
Solution: Audit the script — every function call listed above must have a matching `_release` before the variable goes out of scope.
