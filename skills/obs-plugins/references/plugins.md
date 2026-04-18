# OBS Plugin API Reference

Source of truth: https://docs.obsproject.com/plugins, https://docs.obsproject.com/reference-modules, https://docs.obsproject.com/reference-core-objects, https://github.com/obsproject/obs-plugintemplate. Verify before quoting via `obs-docs` search.

---

## 1. Module macros + exports (reference-modules)

| Symbol | Signature | Notes |
|---|---|---|
| `OBS_DECLARE_MODULE()` | macro | Required. Exactly once per plugin binary. Defines `obs_module_pointer` and other required symbol exports. |
| `OBS_MODULE_USE_DEFAULT_LOCALE(id, default_locale)` | macro | Opt-in. Wires up `obs_module_text()` against `data/locale/<locale>.ini`. |
| `obs_module_load` | `bool obs_module_load(void)` | Required. Register sources/outputs/encoders/services. Return `false` to refuse loading. |
| `obs_module_unload` | `void obs_module_unload(void)` | Optional. Called at shutdown. |
| `obs_module_post_load` | `void obs_module_post_load(void)` | Optional. Called after all modules have loaded (useful for cross-module dependencies). |
| `obs_module_set_locale` | `void obs_module_set_locale(const char *locale)` | Automatic when using `OBS_MODULE_USE_DEFAULT_LOCALE`. |
| `obs_module_text` | `const char *obs_module_text(const char *key)` | Locale lookup. |

Registration functions:

| Fn | Registers |
|---|---|
| `obs_register_source(&info)` | `obs_source_info` |
| `obs_register_output(&info)` | `obs_output_info` |
| `obs_register_encoder(&info)` | `obs_encoder_info` |
| `obs_register_service(&info)` | `obs_service_info` |

The pointer passed to `obs_register_*` must outlive the plugin (static or heap).

---

## 2. `obs_source_info` fields

Verified via obs-docs (plugins and reference-sources pages).

| Field | Type | Purpose |
|---|---|---|
| `id` | `const char *` | Unique source id (e.g. "my_src"). |
| `type` | `enum obs_source_type` | INPUT / FILTER / TRANSITION / SCENE. |
| `output_flags` | `uint32_t` | Capability bitmask (see §3). |
| `get_name` | `const char *(*)(void *type_data)` | Localized name. |
| `create` | `void *(*)(obs_data_t *settings, obs_source_t *source)` | Allocate user data. |
| `destroy` | `void (*)(void *data)` | Free user data. |
| `update` | `void (*)(void *data, obs_data_t *settings)` | Settings changed. |
| `get_defaults` | `void (*)(obs_data_t *settings)` | Populate default settings. |
| `get_properties` | `obs_properties_t *(*)(void *data)` | Build UI. |
| `get_width` | `uint32_t (*)(void *data)` | Required for VIDEO sources. |
| `get_height` | `uint32_t (*)(void *data)` | Required for VIDEO sources. |
| `video_render` | `void (*)(void *data, gs_effect_t *effect)` | Sync video draw. |
| `video_tick` | `void (*)(void *data, float seconds)` | Per-frame tick. |
| `audio_render` | `bool (*)(void *data, uint64_t *ts_out, struct obs_source_audio_mix *audio_output, uint32_t mixers, size_t channels, size_t sample_rate)` | Sync audio mix (for transitions/scenes). |
| `filter_video` | `struct obs_source_frame *(*)(void *data, struct obs_source_frame *frame)` | Filter variant. |
| `filter_audio` | `struct obs_audio_data *(*)(void *data, struct obs_audio_data *audio)` | Filter variant. |
| `mouse_click` / `mouse_move` / `mouse_wheel` | interaction callbacks | Needs `OBS_SOURCE_INTERACTION`. |
| `key_click` / `focus` | interaction callbacks | Needs `OBS_SOURCE_INTERACTION`. |
| `icon_type` | `enum obs_icon_type` | GUI icon hint. |
| `media_play_pause`, `media_restart`, `media_stop`, `media_next`, `media_previous`, `media_get_duration`, `media_get_time`, `media_set_time`, `media_get_state` | media control | Needs `OBS_SOURCE_CONTROLLABLE_MEDIA`. |
| `activate` / `deactivate` / `show` / `hide` | lifecycle hooks | Visibility notifications. |
| `save` / `load` | callbacks | Persist non-settings state. |
| `enum_active_sources` / `enum_all_sources` | iteration | For composite/group-style sources. |
| `type_data` / `free_type_data` | shared | Per-type user data. |

For async input sources, feed video with `obs_source_output_video(source, &frame)` where `obs_source_frame` has: `video_format`, `width`, `height`, `linesize[8]`, `full_range`, `color_matrix`, `color_range_min`, `color_range_max`, `data[8]` planes, `timestamp`.

---

## 3. `OBS_SOURCE_TYPE` + `output_flags`

```
enum obs_source_type {
  OBS_SOURCE_TYPE_INPUT      = 0,
  OBS_SOURCE_TYPE_FILTER     = 1,
  OBS_SOURCE_TYPE_TRANSITION = 2,
  OBS_SOURCE_TYPE_SCENE      = 3,
};
```

Flags (bitwise OR):

| Flag | Meaning |
|---|---|
| `OBS_SOURCE_VIDEO` | Source outputs video. |
| `OBS_SOURCE_AUDIO` | Source outputs audio. |
| `OBS_SOURCE_ASYNC` | Async video (frames delivered off the graphics thread). |
| `OBS_SOURCE_ASYNC_VIDEO` | Shorthand: `OBS_SOURCE_VIDEO | OBS_SOURCE_ASYNC`. |
| `OBS_SOURCE_CUSTOM_DRAW` | Source handles its own draw calls in `video_render`. |
| `OBS_SOURCE_INTERACTION` | Wants mouse / key input. |
| `OBS_SOURCE_COMPOSITE` | Mixes children (e.g. scene/transition). |
| `OBS_SOURCE_DO_NOT_DUPLICATE` | Hide from duplicate menus. |
| `OBS_SOURCE_DEPRECATED` | Mark deprecated. |
| `OBS_SOURCE_DO_NOT_SELF_MONITOR` | Skip self-audio monitor feedback. |
| `OBS_SOURCE_CAP_DISABLED` | Not user-selectable. |
| `OBS_SOURCE_CAP_OBSOLETE` | Obsolete legacy id. |
| `OBS_SOURCE_CONTROLLABLE_MEDIA` | Implements media_* callbacks. |
| `OBS_SOURCE_CEA_708` | Exposes CEA-708 captions. |
| `OBS_SOURCE_SRGB` | Sampling/output is linear sRGB. |
| `OBS_SOURCE_CAP_DONT_SHOW_PROPERTIES` | Hide properties dialog. |

---

## 4. `obs_output_info` fields

| Field | Type | Purpose |
|---|---|---|
| `id` | `const char *` | Unique output id. |
| `flags` | `uint32_t` | `OBS_OUTPUT_VIDEO`, `OBS_OUTPUT_AUDIO`, `OBS_OUTPUT_AV`, `OBS_OUTPUT_ENCODED`, `OBS_OUTPUT_SERVICE`, `OBS_OUTPUT_MULTI_TRACK`, `OBS_OUTPUT_CAN_PAUSE`. |
| `get_name` | callback | Localized name. |
| `create` / `destroy` | callbacks | Lifecycle. |
| `start` / `stop` | callbacks | Start/stop the output. |
| `raw_video` | `void (*)(void *data, struct video_data *frame)` | Raw (unencoded) video in. |
| `raw_audio` | `void (*)(void *data, struct audio_data *audio)` | Raw audio in. |
| `encoded_packet` | `void (*)(void *data, struct encoder_packet *packet)` | Encoded packet in. |
| `update` | callback | Settings changed. |
| `get_defaults` / `get_properties` | callbacks | Defaults + UI. |
| `get_total_bytes` | `uint64_t (*)(void *data)` | Stats hook. |
| `get_dropped_frames` | `int (*)(void *data)` | Stats hook. |
| `get_congestion` | `float (*)(void *data)` | Network congestion for services. |
| `get_connect_time_ms` | `int (*)(void *data)` | Network telemetry. |
| `encoded_video_codecs` / `encoded_audio_codecs` | `const char *` | Comma-separated codecs supported by the output (e.g. "h264,hevc"). |
| `protocols` | `const char *` | For service-typed outputs. |

---

## 5. `obs_encoder_info` fields

| Field | Type | Purpose |
|---|---|---|
| `id` | `const char *` | Unique id. |
| `type` | `enum obs_encoder_type` | `OBS_ENCODER_VIDEO` or `OBS_ENCODER_AUDIO`. |
| `codec` | `const char *` | e.g. "h264", "hevc", "av1", "aac", "opus". |
| `get_name` / `create` / `destroy` | callbacks | Lifecycle. |
| `encode` | `bool (*)(void *data, struct encoder_frame *frame, struct encoder_packet *packet, bool *received_packet)` | CPU encode path. |
| `encode_texture` | `bool (*)(void *data, uint32_t handle, int64_t pts, uint64_t lock_key, uint64_t *next_key, struct encoder_packet *packet, bool *received_packet)` | GPU texture encode path (Windows D3D11 shared handle). |
| `get_defaults` / `get_properties` | callbacks | Defaults + UI. |
| `update` | callback | Settings changed. |
| `get_extra_data` | `bool (*)(void *data, uint8_t **extra_data, size_t *size)` | e.g. SPS/PPS. |
| `get_sei_data` | `bool (*)(void *data, uint8_t **sei, size_t *size)` | H.264 SEI. |
| `get_video_info` | `void (*)(void *data, struct video_scale_info *info)` | Preferred input pixel format. |
| `get_audio_info` | `void (*)(void *data, struct audio_convert_info *info)` | Preferred input sample format. |
| `get_frame_size` | `size_t (*)(void *data)` | Samples per audio frame. |
| `caps` | `uint32_t` | `OBS_ENCODER_CAP_DEPRECATED`, `OBS_ENCODER_CAP_PASS_TEXTURE`, `OBS_ENCODER_CAP_DYN_BITRATE`, `OBS_ENCODER_CAP_INTERNAL`. |

---

## 6. `obs_service_info` fields

(Author's note from the OBS docs: the service API is incomplete.)

| Field | Type | Purpose |
|---|---|---|
| `id` | `const char *` | Unique id. |
| `get_name` / `create` / `destroy` | callbacks | Lifecycle. |
| `update` | callback | Settings changed. |
| `get_defaults` / `get_properties` | callbacks | Defaults + UI. |
| `get_url` | `const char *(*)(void *data)` | Ingest URL. |
| `get_key` | `const char *(*)(void *data)` | Stream key. |
| `get_username` / `get_password` | callbacks | Credentials. |
| `get_output_type` | `const char *(*)(void *data)` | The output `id` this service uses (e.g. "rtmp_output"). |
| `apply_encoder_settings` | `void (*)(void *data, obs_data_t *video_settings, obs_data_t *audio_settings)` | Force caps (e.g. max bitrate). |

---

## 7. Properties API catalog (reference-properties)

Container: `obs_properties_create()` returns `obs_properties_t *`. Attach items:

| Function | Kind |
|---|---|
| `obs_properties_add_text(p, name, desc, OBS_TEXT_DEFAULT|OBS_TEXT_PASSWORD|OBS_TEXT_MULTILINE|OBS_TEXT_INFO)` | Text input / info label. |
| `obs_properties_add_int(p, name, desc, min, max, step)` | Integer. |
| `obs_properties_add_int_slider(...)` | Integer slider. |
| `obs_properties_add_float(...)` / `obs_properties_add_float_slider(...)` | Float. |
| `obs_properties_add_bool(p, name, desc)` | Checkbox. |
| `obs_properties_add_list(p, name, desc, OBS_COMBO_TYPE_LIST|EDITABLE, OBS_COMBO_FORMAT_INT|FLOAT|STRING)` | Combo box. Populate with `obs_property_list_add_int/_float/_string`. |
| `obs_properties_add_path(p, name, desc, OBS_PATH_FILE|FILE_SAVE|DIRECTORY, filter, default)` | File/dir picker. |
| `obs_properties_add_color(p, name, desc)` / `obs_properties_add_color_alpha(...)` | Color picker (opaque / with alpha). |
| `obs_properties_add_font(p, name, desc)` | Font chooser. |
| `obs_properties_add_button(p, name, desc, cb)` / `_button2(...)` | Action button. |
| `obs_properties_add_editable_list(p, name, desc, type, filter, default)` | Editable string list. |
| `obs_properties_add_frame_rate(p, name, desc)` | Numerator/denominator. |
| `obs_properties_add_group(p, name, desc, type, group)` | Nested group. |

Per-item tweaks: `obs_property_set_long_description`, `obs_property_set_modified_callback`, `obs_property_set_visible`, `obs_property_set_enabled`.

---

## 8. Settings API (`obs_data_t`)

| Getter | Setter | Default |
|---|---|---|
| `obs_data_get_string` | `obs_data_set_string` | `obs_data_set_default_string` |
| `obs_data_get_int` | `obs_data_set_int` | `obs_data_set_default_int` |
| `obs_data_get_double` | `obs_data_set_double` | `obs_data_set_default_double` |
| `obs_data_get_bool` | `obs_data_set_bool` | `obs_data_set_default_bool` |
| `obs_data_get_obj` | `obs_data_set_obj` | `obs_data_set_default_obj` |
| `obs_data_get_array` | `obs_data_set_array` | — |

Create/release: `obs_data_create()`, `obs_data_release()`. JSON: `obs_data_create_from_json(str)`, `obs_data_get_json(data)`.

Array variant: `obs_data_array_t *` with `obs_data_array_count`, `obs_data_array_item`, `obs_data_array_push_back`.

Allocation helpers (libobs-util): use `bmalloc`, `bzalloc`, `brealloc`, `bstrdup`, `bfree`. Never mix with `malloc`/`free`.

---

## 9. Graphics (gs_*) — callbacks run on the graphics thread

Key helpers: `obs_enter_graphics()` / `obs_leave_graphics()` bracket any off-thread GPU work. `gs_effect_t` compiled from `.effect` files, load with `gs_effect_create_from_file` or bundled-resource helpers. Draw state: `gs_draw_sprite`, `gs_matrix_push`/`_translate`/`_scale`/`_pop`, `gs_blend_state_push` / `_pop`, `gs_set_linear_srgb`, `gs_texture_create`, `gs_render_save`. See `reference-libobs-graphics`.

---

## 10. Signals (reference-libobs-callback)

Global: `signal_handler_connect(obs_get_signal_handler(), "source_create", cb, data)`. Common global signals: `source_create`, `source_destroy`, `source_rename`, `source_update`, `source_save`, `source_load`, `source_activate`, `source_deactivate`, `source_show`, `source_hide`.

Per-source: `signal_handler_connect(obs_source_get_signal_handler(src), "mute", cb, data)`. Per-source signals include `mute`, `volume`, `enable`, `filter_add`, `filter_remove`, `reorder`, `transition_start`, `transition_stop`, `transition_video_stop`, `media_play`, `media_pause`, `media_restart`, `media_stopped`, `media_started`, `media_ended`, `media_next`, `media_previous`.

---

## 11. obs-plugintemplate `buildspec.json` schema

Fields it consumes:

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Plugin short id (no spaces). Drives binary name + install dir. |
| `version` | string | Semver. |
| `author` | string | For packaging metadata + macOS bundle. |
| `website` | string | README + bundle metadata. |
| `email` | string | Contact. |
| `description` | string | Long description. |
| `id` / `bundleId` | string | Reverse-DNS bundle id (macOS). |
| `dependencies` | object | Pinned OBS + prebuilt dependency versions (OBS, Qt, plugin-deps). Set OBS major here to control ABI target. |
| `platformConfig` | object | Per-OS overrides (deployment target, architectures). |

Run `./.github/scripts/bootstrap.sh` AFTER editing `buildspec.json`. It rewrites `CMakePresets.json` and CI workflows with the final name/id.

---

## 12. CMake + CI layout produced by obs-plugintemplate

- `CMakeLists.txt` — sets `PROJECT` to the plugin name, calls `find_package(libobs REQUIRED)` + optional `frontend-api`/`Qt6`, declares target, and installs.
- `CMakePresets.json` — presets: `macos`, `windows-x64`, `ubuntu-x86_64`, `macos-ci`, etc. Build with `cmake --preset X && cmake --build --preset X --config RelWithDebInfo`.
- `.github/workflows/build-project.yaml` — matrix build on macOS / Windows / Ubuntu.
- `cmake/common/`, `cmake/macos/`, `cmake/windows/`, `cmake/linux/` — helper modules.

---

## 13. Install layouts (per user)

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/obs-studio/plugins/<name>.plugin/` (macOS bundle: `Contents/MacOS/<name>`, `Contents/Resources/` for data). |
| Windows | `%APPDATA%\obs-studio\plugins\<name>\bin\64bit\<name>.dll` + `%APPDATA%\obs-studio\plugins\<name>\data\`. |
| Linux | `~/.config/obs-studio/plugins/<name>/bin/64bit/<name>.so` + `~/.config/obs-studio/plugins/<name>/data/`. |
| Linux (Flatpak) | `~/.var/app/com.obsproject.Studio/config/obs-studio/plugins/<name>/…` |

System-wide paths also exist (`/Library/Application Support/obs-studio/plugins`, `C:\Program Files\obs-studio\obs-plugins\64bit`, `/usr/lib/obs-plugins` / `/usr/lib/x86_64-linux-gnu/obs-plugins`) but per-user is preferred during development.

---

## 14. OBS version ↔ plugin ABI matrix

| OBS major | ABI | Notes |
|---|---|---|
| 27 | old | Last 32-bit Windows. Plugins built for 27 often work on 28 but not vice versa. |
| 28 | new | Qt6, libobs API reset, bundled obs-websocket 5.x. Most community plugins target 28+ now. |
| 29 | compatible-ish | Minor ABI changes; rebuild recommended. |
| 30 | breaking | Several struct expansions; rebuild required for video/encoder plugins. |
| 31+ | breaking | Ongoing; always rebuild on major bumps. |

Pin in `buildspec.json` → `dependencies.obs-studio.version`. Rebuild when OBS bumps major.

---

## 15. Community plugin directory

| Plugin | GitHub | One-liner |
|---|---|---|
| obs-websocket | obsproject/obs-websocket | WebSocket remote-control API (bundled in OBS 28+). |
| StreamFX | Xaymar/obs-StreamFX (archived) | Advanced filters, shaders, blending. Community forks exist. |
| Advanced Scene Switcher | WarmUpTill/SceneSwitcher | Macro-based scene automation. |
| Move (Exeldro) | exeldro/obs-move-transition | Animated filter value transitions. |
| NDI | obs-ndi/obs-ndi | NewTek NDI send/receive. Requires NDI Runtime separately. |
| Source Record | exeldro/obs-source-record | Per-source recording. |
| Backtrack | exeldro/obs-backtrack | Instant-replay time-shift buffer. |
| Shaderfilter | exeldro/obs-shaderfilter | Custom HLSL/GLSL shaders as filters. |
| Downstream Keyer | exeldro/obs-downstream-keyer | Graphics layer above the program. |
| Composite Blur | FiniteSingularity/obs-composite-blur | Gaussian/box/kawase blur. |
| Background Removal | royshil/obs-backgroundremoval | ML background matte (uses ONNX). |
| Multi RTMP | sorayuki/obs-multi-rtmp | Publish to many RTMP destinations. |
| DistroAV (Team NDI) | DistroAV/DistroAV | Maintained fork of NDI plugin. |

---

## 16. Signing / notarization

### macOS

- CI presets in `obs-plugintemplate` expect `MACOS_NOTARIZATION_UUID`, `MACOS_NOTARIZATION_USERNAME`, `MACOS_NOTARIZATION_PASSWORD`, `MACOS_SIGNING_IDENTITY` secrets.
- For unsigned local builds: `sudo xattr -rd com.apple.quarantine ~/Library/Application\ Support/obs-studio/plugins/<name>.plugin`.
- Sign manually: `codesign --force --sign "Developer ID Application: NAME" --timestamp --deep <bundle>`.
- Notarize: `xcrun notarytool submit <zip> --apple-id … --team-id … --password … --wait` then `xcrun stapler staple <bundle>`.

### Windows

- Sign DLL + installer with `signtool sign /f cert.pfx /p pw /tr http://timestamp.digicert.com /td sha256 /fd sha256 <file>`.
- Unsigned plugins load but may trip SmartScreen when the installer is downloaded.

### Linux

- No system-wide signing. Debian packages can be `debsign`'d; AppImage plugins are rare.

---

## 17. Debugging tips

- **OBS log file.** Help → Log Files → View Current Log. Search for the plugin `id` and for "[<name>]" tags.
- **Run OBS with verbose logging:** `obs --verbose --log_level debug` (Linux/macOS CLI) or launch the debug binary on Windows.
- **`blog(level, fmt, ...)`** from your plugin — levels: `LOG_DEBUG`, `LOG_INFO`, `LOG_WARNING`, `LOG_ERROR`. Prefix messages with `[<plugin-name>]` for grep-ability.
- **Leak checks.** `bmalloc_debug_output()` in libobs-util tracks outstanding allocations at shutdown (dev builds).
- **Attach a debugger.**
  - macOS: `lldb /Applications/OBS.app/Contents/MacOS/OBS`.
  - Linux: `gdb --args obs --multi`.
  - Windows: attach Visual Studio to `obs64.exe`.
- **Reload without restart.** Not supported officially — plugins load once at startup. Use OBS scripting for hot-reload iteration on UI-only bits.
- **Plugin did not load.** Check log for `LoadLibrary`/`dlopen` errors (missing transitive dependency) and ABI-version mismatch warnings.
- **Graphics glitches.** Verify `OBS_SOURCE_CUSTOM_DRAW` is set if you issue `gs_draw_sprite`, and that you entered/left graphics context off the render thread.
