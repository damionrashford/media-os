# OBS Doc Page Catalog

The `scripts/obsdocs.py` helper fetches from a fixed list of OBS documentation sources. This file documents what each page contains, when to pick it, and what lives where.

Pages live across three hosts:

1. **`docs.obsproject.com`** — Sphinx-generated developer documentation for libobs (the C API), plugins, scripting, graphics, and frontend integration.
2. **`obsproject.com/wiki`** — user-facing install instructions and troubleshooting.
3. **`raw.githubusercontent.com`** — Markdown files pulled straight from the upstream repositories (`obs-plugintemplate` README, `obs-websocket` generated protocol reference).

---

## `docs.obsproject.com` — developer documentation

### Top-level guides

| Page | Contents |
|---|---|
| `index` | Landing page with links to all other sections. Useful when you don't know which reference page has what. |
| `backend-design` | High-level libobs architecture: sources, outputs, encoders, services, scenes, filters, data flow between threads. Read first when learning the model. |
| `plugins` | Plugin authoring guide — sources (`obs_source_info`), outputs (`obs_output_info`), encoders (`obs_encoder_info`), services (`obs_service_info`), filter chains, property UIs, settings dialogs. |
| `frontends` | Writing a Qt frontend integration (dock widgets, menus, hotkeys, dialogs) against `obs-frontend-api`. |
| `graphics` | OBS graphics subsystem — effects (`.effect` HLSL/GLSL files), vertex buffers, textures, render targets, shaders. |
| `scripting` | Python / Lua scripting interface. Covers the subset of `obs_*` available to scripts plus the scripting lifecycle hooks. |

### Reference — core lifecycle + loader

| Page | Contents |
|---|---|
| `reference-core` | Core lifecycle (`obs_startup`, `obs_shutdown`, `obs_initialized`), reset audio/video, log level, data paths, locale. |
| `reference-modules` | Module loader and plugin entry points — `OBS_DECLARE_MODULE()`, `OBS_MODULE_USE_DEFAULT_LOCALE()`, `obs_module_load()`, `obs_module_unload()`, `obs_register_*_s`. |
| `reference-core-objects` | The big one — every core object type: `obs_source`, `obs_output`, `obs_encoder`, `obs_service`, `obs_scene`, `obs_sceneitem`, `obs_data`, `obs_data_array`, `obs_properties`, `obs_property`, `obs_hotkey`, `obs_display`, `obs_view`. |

### Reference — libobs utilities

| Page | Contents |
|---|---|
| `reference-libobs-util` | Utility layer — `bmalloc`/`bzalloc`/`brealloc`/`bstrdup`/`bfree`, `dstr` (dynamic string), dynamic arrays (`DARRAY`, `darray_*`), config files, threading primitives, lookup (list), platform abstractions, base logger. |
| `reference-libobs-callback` | Signal system (`signal_handler_t`, `signal_handler_connect`, `signal_handler_disconnect`, `signal_handler_signal`), procedural handler (`proc_handler_t`, `proc_handler_call`), `calldata_t` for argument passing between callbacks. |
| `reference-libobs-graphics` | Graphics API (`gs_*` functions): texture creation/sampling, effects (HLSL-like shaders), vertex/index buffers, render targets, viewport/projection, blend/depth/cull state. **Must run on graphics thread.** |
| `reference-libobs-media-io` | Media frame types — `obs_source_frame`, `obs_source_audio`, video format enums (`video_format`, `video_colorspace`, `video_range_type`), audio format enums, frame-rate structs. |

### Reference — frontend API

| Page | Contents |
|---|---|
| `reference-frontend-api` | `obs_frontend_*` functions — only available when loaded as a C++ plugin into the OBS Studio process. Covers: scene switching, recording/streaming control, replay buffer, virtualcam, event callbacks (`obs_frontend_add_event_callback`, `OBS_FRONTEND_EVENT_*`), Qt main window access, dock widgets, transitions, profiles, scene collections. |

---

## `obsproject.com/wiki`

| Page | Contents |
|---|---|
| `wiki-install` | Install OBS Studio on Windows / macOS / Linux — official builds, dependencies, Apple Silicon note, self-built Linux options, Flatpak vs Snap. Consumer-facing, not API. |

---

## GitHub raw Markdown

| Page | Contents |
|---|---|
| `plugintemplate-readme` | `obs-plugintemplate` README — CMake-based cross-platform plugin scaffold (Windows / macOS / Ubuntu via GitHub Actions), preset targets, build config, signing, packaging. The official starting point for writing a new plugin. |
| `obs-websocket-protocol` | Full wire protocol for the `obs-websocket` plugin — OpCodes (Hello, Identify, Identified, Reidentify, Event, Request, RequestResponse, RequestBatch, RequestBatchResponse), authentication via SHA-256 challenge + salt, all Requests and Events generated from the server source. This is what you search when building a remote-control client. |

---

## Which page for which question?

Pick FIRST, then search.

| User asks... | Page |
|---|---|
| "What does `obs_source_create` do?" | `reference-core-objects` |
| "How do I start OBS?" (build, author) | `reference-core` |
| "How do I write a source plugin?" | `plugins` |
| "How do I add a menu item to OBS?" | `frontends` + `reference-frontend-api` |
| "How do I write a Python script for OBS?" | `scripting` |
| "How do I draw something on the graphics thread?" | `graphics` + `reference-libobs-graphics` |
| "What's `bfree()` for?" | `reference-libobs-util` |
| "How do I listen for scene changes?" (C) | `reference-libobs-callback` + `reference-core-objects` |
| "How do I listen for scene changes over obs-websocket?" | `obs-websocket-protocol` (search for `CurrentProgramSceneChanged`) |
| "How do I trigger start recording remotely?" | `obs-websocket-protocol` (search for `StartRecord`) |
| "How do I trigger start recording from a plugin?" | `reference-frontend-api` (search for `obs_frontend_recording_start`) |
| "What video formats does `obs_source_output_video` accept?" | `reference-libobs-media-io` |
| "How do I install OBS on Apple Silicon?" | `wiki-install` |
| "How do I start a new plugin project?" | `plugintemplate-readme` |
| "What macros go in `obs_module_load()`?" | `reference-modules` |

---

## Anchor ID conventions

Anchors vary by source:

- **docs.obsproject.com** (Sphinx): uses either plain-text anchors (`obs_source_create`) or the Sphinx C-domain mangled form (`_CPPv4N10obs_source9is_activeEv`). Prefer `search` to discover the actual id before passing to `section --id`.
- **obs-websocket-protocol** (Markdown): anchors are generated from heading text, lowercased and hyphenated (e.g. `## SetCurrentProgramScene` → `#setcurrentprogramscene`). The `section --id` command with a keyword fallback handles this gracefully.
- **Install wiki** (obsproject.com/wiki HTML): usually doesn't have deep anchors — use `search --page wiki-install` and read the hit context.

If an anchor lookup fails, the script falls back to a heading keyword match. So `section --id "StartRecord"` works even if the actual anchor is `#startrecord`.

---

## Cache behavior

- Cache path: `~/.cache/obs-docs/` (override with `OBS_DOCS_CACHE` env var).
- One text file per page: `~/.cache/obs-docs/<page>.txt`.
- Cache never expires automatically. `clear-cache` or delete the dir manually.
- `index` pre-fetches every page with a 0.5-second delay between requests.

---

## Offline readiness

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py index
```

All 17 pages cached to disk. `search` / `section` / `fetch` then work without network.

---

## Cross-skill handoffs

- **Building a plugin?** Start with `plugintemplate-readme`, then read `plugins` + `reference-modules` + `reference-core-objects`. Specific domains: `reference-libobs-graphics` if you render, `reference-libobs-callback` if you handle signals, `reference-frontend-api` if you integrate with the OBS Studio UI.
- **Writing an obs-websocket client?** Read `obs-websocket-protocol` in full once (understand the OpCode handshake + auth), then search per-request as needed. Pair with a language-specific client library (`obsws-python`, `obs-websocket-js`, `obswebsocket` Go).
- **Writing a Python script inside OBS?** Read `scripting` first — it tells you which `obs_*` functions are actually bound. Don't copy C API code directly; wrapper semantics differ.
