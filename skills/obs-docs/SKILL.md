---
name: obs-docs
description: >
  Search and fetch official OBS Studio documentation: docs.obsproject.com (backend-design, plugins, frontends, graphics, scripting, reference-core, reference-modules, reference-core-objects, reference-libobs-util, reference-libobs-callback, reference-libobs-graphics, reference-libobs-media-io, reference-frontend-api), install wiki, obs-plugintemplate README, obs-websocket protocol reference. Use when the user asks to look up an OBS API, find an obs_ function signature, check libobs callback signatures, read OBS scripting API, search obs-websocket request/event/opcode details, learn OBS plugin authoring, look up frontend API calls, or verify an OBS SDK call against the real documentation.
argument-hint: "[query]"
---

# OBS Docs

**Context:** $ARGUMENTS

## Quick start

- **Find an `obs_` function / callback / event:** → Step 2 (`search --query <term>`)
- **Read the full section for an API:** → Step 3 (`section --page <page> --id <anchor>`)
- **Grab a doc page:** → Step 4 (`fetch --page <name>`)
- **Prime cache for offline use:** → Step 5 (`index`)

## When to use

- User asks "what does `obs_source_create` take?" or "what's the signature of `obs_hotkey_register_frontend`?"
- Need to verify an API name exists before recommending it (prevents hallucinated OBS calls).
- Need to look up an obs-websocket Request / Event / OpCode field.
- Before writing an OBS plugin, script, or obs-websocket client: confirm the real API surface.
- Need the canonical URL to cite an OBS doc.

---

## Step 1 — Know the page catalog

Only the pages below are covered. Get the list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py list-pages
```

Pick the right page for the question:

| Question | Page |
|---|---|
| How does OBS's architecture work? | `backend-design` |
| Plugin authoring / source / output / encoder / service module | `plugins` |
| Qt frontend integration (menus, docks) | `frontends` |
| Graphics API (effects, shaders, textures) | `graphics` |
| Python/Lua scripting inside OBS | `scripting` |
| Core lifecycle + global funcs (`obs_startup`, `obs_shutdown`) | `reference-core` |
| Module loader / `obs_module_*` macros | `reference-modules` |
| `obs_source`, `obs_output`, `obs_encoder`, `obs_service`, `obs_scene`, `obs_data`, `obs_hotkey` | `reference-core-objects` |
| `bmalloc`, `bstrdup`, `dstr`, lists, config, threading, darrays | `reference-libobs-util` |
| `signal_handler`, `calldata`, procedural callbacks | `reference-libobs-callback` |
| `gs_*` graphics (textures, effects, vertex buffers, shaders) | `reference-libobs-graphics` |
| `obs_source_frame`, `obs_source_audio`, media IO, video frames | `reference-libobs-media-io` |
| `obs_frontend_*` (Qt dock, scene switching, recording control, events) | `reference-frontend-api` |
| Install OBS on macOS / Windows / Linux | `wiki-install` |
| Build a plugin from scratch (CMake, GitHub template) | `plugintemplate-readme` |
| obs-websocket Requests / Events / OpCodes / Identify handshake | `obs-websocket-protocol` |

Read [`references/pages.md`](references/pages.md) for the full catalog with use-cases.

---

## Step 2 — Search first

When the user names an API, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "obs_source_create" --limit 5
```

When you know the page, scope to it (faster, less noise):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "hotkey_register" --page reference-core-objects
```

Output format per hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with anchor>
<±3 lines of context>
```

Use `--format json` for machine-parseable output.

First run downloads the page; subsequent runs hit the local cache at `~/.cache/obs-docs/`.

---

## Step 3 — Read one section in full

When the hit points to a specific API and you want the full declaration + description, use `section`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py section --page reference-core-objects --id obs_source_create
```

`--id` accepts:

- An anchor id printed in search results as `[§xxxx]`.
- A heading keyword — the script falls back to the first heading that contains it.

Output is the section from its heading down to the next same-or-higher-level heading.

---

## Step 4 — Fetch a whole page

Rarely needed; search/section are almost always better. When you do:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py fetch --page reference-frontend-api
```

Pair with `--format json` for structured output.

---

## Step 5 — Prime the cache (optional)

For reliable offline lookups:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py index
```

Fetches every known page, stores text-extracted versions in `~/.cache/obs-docs/`. Re-run when a new OBS Studio / obs-websocket release drops docs.

Override cache dir: `export OBS_DOCS_CACHE=/path/to/dir`.
Clear: `uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py clear-cache`.

---

## Gotchas

- **Never recommend an OBS API call without searching first.** If `search --query "<name>"` returns zero hits, the function/callback/event doesn't exist — don't claim it does.
- **libobs vs obs-websocket are distinct surfaces.** A `SetCurrentProgramScene` Request lives in `obs-websocket-protocol`. An `obs_frontend_set_current_scene()` C function lives in `reference-frontend-api`. Search the right page.
- **obs-websocket uses OpCodes for the wire protocol** (0 Hello, 1 Identify, 2 Identified, 3 Reidentify, 5 Event, 6 Request, 7 RequestResponse, 8 RequestBatch, 9 RequestBatchResponse). Requests and Events are NOT the same thing — a single user-facing operation may have both (e.g. `SetCurrentProgramScene` Request and `CurrentProgramSceneChanged` Event).
- **The obs-websocket page is a single LARGE Markdown file** from GitHub; search it with `--page obs-websocket-protocol --limit 3`. It's the wire protocol only, not the C API.
- **docs.obsproject.com is Sphinx-generated HTML.** Anchor IDs follow the Sphinx-C-domain pattern like `_CPPv4N10obs_source9is_activeEv` (mangled) or simpler like `obs_source_create`. Use `search` first to discover the real anchor; `section --id` accepts the raw id OR a heading keyword fallback.
- **The plugin template README is the entry point for new plugin projects** — don't confuse it with the `plugins` docs page (which is the developer guide for the plugin API).
- **Scripting (Python/Lua) has a SEPARATE, smaller API surface** than the full libobs C API. Scripting exposes `obs_*` via bindings with some limits. Search `scripting` page for what's actually exposed.
- **Frontend API requires building a Qt plugin** — it is NOT available to scripts. Check `reference-frontend-api` for what's usable.
- **Scene vs Scene-collection vs Source.** A Scene is a specific `obs_source` type (`scene`). A Scene-collection is a file-level concept. A Source is the base abstraction. Don't mix them up — `reference-core-objects` is authoritative.
- **Graphics calls MUST be made from the graphics thread.** If you see a `gs_*` function, it can only run inside `obs_enter_graphics()` / `obs_leave_graphics()` brackets or inside a video-render callback. `reference-libobs-graphics` is explicit about this.
- **Signals are via `signal_handler_connect`** — register BEFORE the event fires. Calldata is read/written with `calldata_get_*` / `calldata_set_*` (see `reference-libobs-callback`).
- **Use `bfree()` for anything libobs allocated**, not `free()`. Same for `bmalloc`/`bstrdup` vs `malloc`/`strdup`.
- **Module entry points are `obs_module_load()` + `obs_module_unload()`**, and the macros `OBS_DECLARE_MODULE()` + `OBS_MODULE_USE_DEFAULT_LOCALE()` must appear in your plugin source.
- **URL pattern on docs.obsproject.com is `/<page>`** (no file extension, not `.html`). The script handles this.
- **Cache is per-page only, not per-OBS-version.** After a new OBS release shifts the API, `clear-cache` + `index`.

---

## Examples

### Example 1 — "What does `obs_source_create` take?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "obs_source_create" --page reference-core-objects --limit 3
```

Pick the hit, then read the full definition:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py section --page reference-core-objects --id obs_source_create
```

Cite the URL printed in the hit header.

### Example 2 — "How do I change the current scene over obs-websocket?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "SetCurrentProgramScene" --page obs-websocket-protocol --limit 3
```

### Example 3 — "What Frontend API functions exist for recording control?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "recording" --page reference-frontend-api --limit 10
```

### Example 4 — "Plugin CMake setup?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py fetch --page plugintemplate-readme
```

### Example 5 — "What scripting callbacks can a Python script register?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/obsdocs.py search --query "callback" --page scripting --limit 10
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** The name isn't in the catalog.
**Solution:** Run `list-pages` for valid names. Common mistakes: `core` instead of `reference-core`; `frontend` instead of `reference-frontend-api`; `websocket` instead of `obs-websocket-protocol`.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** macOS Python without up-to-date certs.
**Solution:** Run `/Applications/Python\ 3.x/Install\ Certificates.command` or set `SSL_CERT_FILE`. Don't patch the script to disable SSL verification.

### Search returns zero hits

**Cause:** Term doesn't exist on that page, or is only in a different reference surface.
**Solution:** Drop `--page` to search all pages. Try broader query. Some APIs live in `reference-libobs-*` utility pages (dstr, calldata, gs_) rather than the obvious place.

### Results look truncated

**Cause:** Text extraction flattens complex Sphinx tables.
**Solution:** The search-hit header prints the canonical URL. Open it directly for the authoritative view.

### Cache stale after OBS upstream release

**Solution:** `clear-cache` then `index` (or `fetch --no-cache --page <name>` for one page).
