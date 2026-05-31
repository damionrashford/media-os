# OBS Scripting API Reference

Comprehensive `obspython` / `obslua` surface: lifecycle, properties, settings, events, signals, hotkeys, timers, enumeration, cleanup.

Authoritative source: `obs-docs` skill → `uv run obsdocs.py search --query <name> --page scripting`. When a symbol is missing from `scripting`, retry without `--page`; the C API header `obs.h` exposes many more symbols than are wrapped by the scripting SWIG bindings.

## obspython vs obslua

Both modules expose the same symbols. Invocation differs:

| | Python | Lua |
| --- | --- | --- |
| Import | `import obspython as obs` | `obs = obslua` (already global) |
| Boolean | `True` / `False` | `true` / `false` |
| Nil | `None` | `nil` |
| List iteration | `for s in sources:` | `for i, s in ipairs(sources) do` |
| String encoding | sometimes UTF-8 bytes required for `calldata_string` | always string |
| Format literal | `f"x={x}"` | `string.format("x=%s", x)` |
| Globals | `global x` inside function | directly assign |

The rest of this doc uses Python names. For Lua, swap `.` for `.` (same) and dict literals for Lua tables.

## Script lifecycle

All are optional. OBS looks them up by name on the script module.

| Function | Called | Notes |
| --- | --- | --- |
| `script_description() -> str` | once, when OBS loads the script UI | return plain text or very limited HTML |
| `script_load(settings)` | once, after properties are available | register callbacks, timers, hotkeys |
| `script_unload()` | once, when the script is removed or OBS shuts down | unregister everything, release sources |
| `script_defaults(settings)` | before `script_update` on first load | call `obs_data_set_default_*` |
| `script_properties() -> obs_properties_t` | MANY times (every property pane repaint) | cheap; do not enumerate sources here if avoidable |
| `script_update(settings)` | on first load AND on every property change | keep idempotent |
| `script_save(settings)` | when OBS saves scene collection / exits | persist hotkeys, custom state |
| `script_tick(seconds)` | every frame on the graphics thread | use only for per-frame work; prefer `timer_add` |

## Properties API (`obs_properties_*`)

Each returns an `obs_property_t *` on the passed-in `obs_properties_t`.

| Function | Purpose |
| --- | --- |
| `obs_properties_create()` | Make a root properties container. Return from `script_properties`. |
| `obs_properties_add_bool(p, name, desc)` | Checkbox. |
| `obs_properties_add_int(p, name, desc, min, max, step)` | Integer spinbox. |
| `obs_properties_add_int_slider(p, ...)` | Integer slider. |
| `obs_properties_add_float(p, name, desc, min, max, step)` | Float spinbox. |
| `obs_properties_add_float_slider(p, ...)` | Float slider. |
| `obs_properties_add_text(p, name, desc, OBS_TEXT_*)` | Single-line / multi-line / password / info. |
| `obs_properties_add_path(p, name, desc, OBS_PATH_*, filter, default_path)` | File / file-save / directory picker. |
| `obs_properties_add_list(p, name, desc, OBS_COMBO_TYPE_*, OBS_COMBO_FORMAT_*)` | Combo / editable list. Populate with `obs_property_list_add_string\|int\|float`. |
| `obs_properties_add_color(p, name, desc)` | RGB picker. |
| `obs_properties_add_color_alpha(p, name, desc)` | RGBA picker. |
| `obs_properties_add_font(p, name, desc)` | Font chooser. |
| `obs_properties_add_button(p, name, text, callback)` | Button. Callback `(props, prop) -> bool` — return `True` to refresh UI. |
| `obs_properties_add_editable_list(p, name, desc, OBS_EDITABLE_LIST_TYPE_*, filter, default_path)` | List the user can add / remove entries from. |
| `obs_properties_add_frame_rate(p, name, desc)` | FPS dropdown + fractional entry. |
| `obs_properties_add_group(p, name, desc, OBS_GROUP_*, sub_props)` | Collapsible section. `OBS_GROUP_NORMAL` or `OBS_GROUP_CHECKABLE`. |

Modify properties after creation:
- `obs_property_set_visible(prop, bool)`, `obs_property_set_enabled(prop, bool)`
- `obs_property_set_description(prop, str)`, `obs_property_set_long_description(prop, str)`
- `obs_property_set_modified_callback(prop, cb)` — `(props, prop, settings) -> bool`. Return `True` to redraw.

## Settings API (`obs_data_*`)

`settings` is an `obs_data_t`. Every type has `get` / `set` / `set_default` / `get_default`:

| Type | Getter | Setter | Default setter |
| --- | --- | --- | --- |
| string | `obs_data_get_string` | `obs_data_set_string` | `obs_data_set_default_string` |
| int | `obs_data_get_int` | `obs_data_set_int` | `obs_data_set_default_int` |
| double / float | `obs_data_get_double` | `obs_data_set_double` | `obs_data_set_default_double` |
| bool | `obs_data_get_bool` | `obs_data_set_bool` | `obs_data_set_default_bool` |
| obj (`obs_data_t`) | `obs_data_get_obj` | `obs_data_set_obj` | `obs_data_set_default_obj` |
| array (`obs_data_array_t`) | `obs_data_get_array` | `obs_data_set_array` | — |

Release: `obs_data_release(d)` for any data fetched as `obj`; `obs_data_array_release(arr)` for arrays.

JSON helpers: `obs_data_create()`, `obs_data_create_from_json(json_str)`, `obs_data_get_json(data)`.

## Frontend events

Register: `obs_frontend_add_event_callback(callback)`. Callback signature: `(event: int) -> None`.

Full enum (`OBS_FRONTEND_EVENT_*`):

| Event | When |
| --- | --- |
| `STREAMING_STARTING` | Stream start has been requested. |
| `STREAMING_STARTED` | Stream is now live. |
| `STREAMING_STOPPING` | Stream stop requested. |
| `STREAMING_STOPPED` | Stream fully stopped. |
| `RECORDING_STARTING` / `RECORDING_STARTED` / `RECORDING_STOPPING` / `RECORDING_STOPPED` | Recording lifecycle. |
| `RECORDING_PAUSED` / `RECORDING_UNPAUSED` | Pause toggle. |
| `SCENE_CHANGED` | Program scene changed. |
| `SCENE_LIST_CHANGED` | A scene was added / removed / renamed. |
| `TRANSITION_CHANGED` / `TRANSITION_STOPPED` / `TRANSITION_LIST_CHANGED` / `TRANSITION_DURATION_CHANGED` | Transition state. |
| `SCENE_COLLECTION_CHANGED` / `SCENE_COLLECTION_LIST_CHANGED` / `SCENE_COLLECTION_CLEANUP` | Scene collection lifecycle. |
| `PROFILE_CHANGED` / `PROFILE_LIST_CHANGED` | Profile lifecycle. |
| `EXIT` | OBS is about to quit. |
| `REPLAY_BUFFER_STARTING` / `REPLAY_BUFFER_STARTED` / `REPLAY_BUFFER_STOPPING` / `REPLAY_BUFFER_STOPPED` / `REPLAY_BUFFER_SAVED` | Replay buffer lifecycle + save trigger. |
| `STUDIO_MODE_ENABLED` / `STUDIO_MODE_DISABLED` | Studio mode toggle. |
| `PREVIEW_SCENE_CHANGED` | Studio mode preview scene changed. |
| `FINISHED_LOADING` | OBS finished loading scene collection (good time to enumerate sources). |
| `VIRTUALCAM_STARTED` / `VIRTUALCAM_STOPPED` | Virtual camera lifecycle. |
| `TBAR_VALUE_CHANGED` | Studio mode T-bar moved. |

Frontend API accessors (return reference-incremented values — release!):

- `obs_frontend_get_current_scene()` → `obs_source_t *` (release with `obs_source_release`)
- `obs_frontend_set_current_scene(source)`
- `obs_frontend_get_current_preview_scene()` (Studio mode only)
- `obs_frontend_set_current_preview_scene(source)`
- `obs_frontend_get_scenes()` → list (release with `source_list_release`)
- `obs_frontend_get_scene_collections()` / `obs_frontend_set_current_scene_collection(name)`
- `obs_frontend_get_profiles()` / `obs_frontend_set_current_profile(name)`
- `obs_frontend_streaming_active()` / `_recording_active()` / `_replay_buffer_active()` / `_virtualcam_active()` → bool
- `obs_frontend_streaming_start()` / `_stop()`, same for `recording`, `replay_buffer`, `virtualcam`, plus `obs_frontend_save_replay_buffer()`
- `obs_frontend_get_current_transition()` / `obs_frontend_set_current_transition(src)`

## Enums used in properties

| Enum | Values |
| --- | --- |
| `OBS_TEXT_*` | `OBS_TEXT_DEFAULT`, `OBS_TEXT_PASSWORD`, `OBS_TEXT_MULTILINE`, `OBS_TEXT_INFO` |
| `OBS_PATH_*` | `OBS_PATH_FILE`, `OBS_PATH_FILE_SAVE`, `OBS_PATH_DIRECTORY` |
| `OBS_COMBO_TYPE_*` | `OBS_COMBO_TYPE_LIST` (strict), `OBS_COMBO_TYPE_EDITABLE` (user can type) |
| `OBS_COMBO_FORMAT_*` | `OBS_COMBO_FORMAT_STRING`, `OBS_COMBO_FORMAT_INT`, `OBS_COMBO_FORMAT_FLOAT` |
| `OBS_NUMBER_*` | `OBS_NUMBER_SCROLLER`, `OBS_NUMBER_SLIDER` |
| `OBS_GROUP_*` | `OBS_GROUP_NORMAL`, `OBS_GROUP_CHECKABLE` |
| `OBS_EDITABLE_LIST_TYPE_*` | `OBS_EDITABLE_LIST_TYPE_STRINGS`, `OBS_EDITABLE_LIST_TYPE_FILES`, `OBS_EDITABLE_LIST_TYPE_FILES_AND_URLS` |

## Source / scene enumeration

`obs_enum_sources()` — returns a Python list of `obs_source_t` for every registered source (inputs, scenes, filters live elsewhere). MUST call `source_list_release(lst)`.

```python
sources = obs.obs_enum_sources()
if sources is not None:
    for s in sources:
        print(obs.obs_source_get_name(s), obs.obs_source_get_id(s))
    obs.source_list_release(sources)
```

`obs_frontend_get_scenes()` — same pattern, but only scene sources.

`obs_get_source_by_name(name)` — single lookup, returns new reference. Release with `obs_source_release`.

Scene items inside a scene:
```python
scene_src = obs.obs_get_source_by_name("My Scene")
scene = obs.obs_scene_from_source(scene_src)  # no reference change
items = obs.obs_scene_enum_items(scene)       # list of sceneitems, release with sceneitem_list_release
for item in items:
    src = obs.obs_sceneitem_get_source(item)  # no reference change
    print(obs.obs_source_get_name(src))
obs.sceneitem_list_release(items)
obs.obs_source_release(scene_src)
```

## Hotkeys

Register in `script_load`, save in `script_save`, remove in `script_unload`.

```python
HK = obs.OBS_INVALID_HOTKEY_ID

def script_load(settings):
    global HK
    HK = obs.obs_hotkey_register_frontend("myscript.action", "My action", on_hk)
    arr = obs.obs_data_get_array(settings, "hotkey_myscript.action")
    obs.obs_hotkey_load(HK, arr)
    obs.obs_data_array_release(arr)

def script_save(settings):
    arr = obs.obs_hotkey_save(HK)
    obs.obs_data_set_array(settings, "hotkey_myscript.action", arr)
    obs.obs_data_array_release(arr)

def on_hk(pressed):
    if pressed:
        ...
```

`obs_hotkey_unregister(HK)` in `script_unload` if you want a clean exit. The key string used for `obs_data_get_array` / `obs_data_set_array` is arbitrary — just be consistent.

## Signals

Per-object signal handlers. Pattern:

```python
def hook(src_name):
    src = obs.obs_get_source_by_name(src_name)
    if src:
        sh = obs.obs_source_get_signal_handler(src)
        obs.signal_handler_connect(sh, "mute", on_mute)
        obs.obs_source_release(src)

def on_mute(calldata):
    muted = obs.calldata_bool(calldata, "muted")
```

`calldata_*` accessors by type: `calldata_int`, `calldata_float`, `calldata_bool`, `calldata_string`, `calldata_ptr`. Signal names vary per source. Common ones on scenes: `item_add`, `item_remove`, `item_visible`, `item_transform`, `reorder`. On all sources: `destroy`, `rename`, `update`, `mute`, `volume`, `enable`, `activate`, `deactivate`, `show`, `hide`.

`obs_output_get_signal_handler(output)` for streaming / recording outputs — signals `start`, `stop`, `starting`, `stopping`, `reconnect`, `reconnect_success`.

Global signals: `obs_get_signal_handler()` — fires source lifecycle (`source_create`, `source_destroy`, etc.).

Disconnect: `signal_handler_disconnect(handler, signal, cb)`.

## Timers

`obs.timer_add(callback, interval_ms)` — add; callback runs on UI thread every N ms.
`obs.timer_remove(callback)` — remove; call with the same callable.

Idiom for one-shot:

```python
def once():
    obs.timer_remove(once)
    do_the_thing()

obs.timer_add(once, 500)
```

Changing interval: `timer_remove` then `timer_add`. You cannot modify an existing timer in place.

## Script logging

`obs.script_log(level, msg)`. Levels: `obs.LOG_DEBUG`, `obs.LOG_INFO`, `obs.LOG_WARNING`, `obs.LOG_ERROR`. Output appears in Tools → Scripts → Script Log, NOT in the main OBS log file.

## Memory / reference-counting rules

| Got reference via | Release with |
| --- | --- |
| `obs_get_source_by_name` | `obs_source_release` |
| `obs_frontend_get_current_scene` / `_current_preview_scene` / `_current_transition` | `obs_source_release` |
| `obs_enum_sources` / `obs_frontend_get_scenes` | `source_list_release` |
| `obs_scene_enum_items` | `sceneitem_list_release` |
| `obs_sceneitem_addref` | `obs_sceneitem_release` |
| `obs_source_get_settings` | `obs_data_release` |
| `obs_data_create` | `obs_data_release` |
| `obs_data_get_array` / `obs_hotkey_save` | `obs_data_array_release` |
| `obs_data_get_obj` | `obs_data_release` |

`obs_scene_from_source`, `obs_sceneitem_get_source`, `obs_source_get_signal_handler`, `obs_source_get_name`, `obs_source_get_id` do NOT change reference count — do not release what you get from them (except the wrapping source you fetched separately).

Python GC does NOT run OBS reference counting. Leaks accumulate until OBS crashes; with long streams, a leak of one source per minute is enough to OOM a 4 GB box in a few hours.

## Common pitfalls

1. **Python version mismatch.** OBS 30 wants CPython 3.11 exactly. Different minor version = script never appears in the list, sometimes with no error.
2. **Blocking in UI-thread callbacks.** `script_tick`, `on_event`, `on_hotkey`, `timer_add` callbacks, button callbacks, signal callbacks all run on the OBS UI or graphics thread. `requests.get()` with a 30s timeout will freeze OBS visibly for 30 seconds.
3. **Forgetting to release in loops.** `for _ in range(10): obs.obs_get_source_by_name(name)` without release = 10 leaked sources.
4. **`script_properties` doing expensive work.** It runs every time the pane repaints — including on scroll. Cache and reuse.
5. **Hotkey key mismatch.** The string passed to `obs_data_get_array` in `script_load` MUST equal the one in `obs_data_set_array` in `script_save`. Otherwise the binding vanishes each run.
6. **No hot reload.** Save the file on disk, then click the refresh (↻) button in Tools → Scripts. Alternatively, uncheck and re-check the script.
7. **`obs_frontend_set_current_scene` requires a source, not a scene_t.** Use `obs_get_source_by_name` to get the source wrapper.
8. **Threading.** You can spawn a `threading.Thread` from a script, but any OBS API call from that thread must be wrapped so it runs on the UI thread — simplest pattern: set a flag, have a `timer_add` check it and do the API calls.
9. **`obs_properties_add_list` populating.** Call `obs_property_list_add_string(prop, label, value)` on the return value of `add_list`, not on the properties container.
10. **No Qt from scripts.** Menu items, QDialog, QDockWidget need a compiled plugin.

## Related references

- `obs-docs` skill — live search of docs.obsproject.com (backend-design, plugins, frontends, graphics, scripting, reference-core, reference-modules, reference-core-objects, reference-libobs-util, reference-libobs-callback, reference-libobs-graphics, reference-libobs-media-io, reference-frontend-api).
- `obs-plugins` skill — for anything requiring compiled C++ (Qt UI, new source types, custom encoders).
- `obs-websocket` skill — for out-of-process control instead of in-process scripts.
- `obs-config` skill — for managing profile / scene-collection / `global.ini` files from outside OBS.
