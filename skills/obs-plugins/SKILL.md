---
name: obs-plugins
description: >
  OBS plugin authoring and ecosystem: scaffold a new C++ plugin from obs-plugintemplate (CMake, cross-platform GitHub Actions CI), register obs_source_info / obs_output_info / obs_encoder_info / obs_service_info, implement obs_module_load / obs_module_unload with OBS_DECLARE_MODULE, plus install / configure common community plugins (StreamFX, Advanced Scene Switcher, Move, NDI, Source Record, Backtrack, obs-websocket). Use when the user asks to write an OBS plugin, build a custom source / output / encoder, use obs-plugintemplate, install a specific OBS plugin, or set up the OBS plugin build environment.
argument-hint: "[action]"
---

# OBS Plugins

**Context:** $ARGUMENTS

## Quick start

- **Scaffold a new plugin** → Step 1
- **Implement a source / output / encoder / service** → Step 2
- **Build the plugin** → Step 3
- **Install the built plugin locally** → Step 4
- **Install a community plugin (StreamFX, NDI, Move, etc.)** → Step 5

## When to use

- Writing a native C/C++ OBS plugin (custom source, filter, transition, output, encoder, or service).
- Bootstrapping a cross-platform OBS plugin repo with working GitHub Actions CI.
- Installing and configuring community plugins such as StreamFX, Advanced Scene Switcher, Move (Exeldro), NDI, Source Record, Backtrack, or obs-websocket.
- Diagnosing plugin load failures (ABI mismatch, missing `OBS_DECLARE_MODULE`, wrong install path, macOS quarantine).

**Not this skill:** writing Python/Lua scripts that run inside OBS → use `obs-scripting`. Programmatically editing profile/scene-collection files → use `obs-config`. Controlling a running OBS via WebSocket → use `obs-websocket`.

## MANDATORY — verify APIs before quoting them

Before claiming any function signature, struct field, or macro exists, run:

```bash
# If you have the obs-docs skill installed separately, use its search command search --query "<name>" --limit 5
```

## Step 1 — Scaffold from obs-plugintemplate

`obs-plugintemplate` is the only officially recommended starting point. It ships cross-platform CMake presets (macOS / Windows / Linux) and GitHub Actions CI that builds, signs (optional), and packages the plugin for each OS.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py scaffold \
  --name my-plugin \
  --author "Your Name" \
  --bundle-id com.yourname.my-plugin \
  --description "My custom OBS source" \
  --outdir ~/src
```

Or manually:

```bash
git clone https://github.com/obsproject/obs-plugintemplate.git my-plugin
cd my-plugin
# Edit buildspec.json: name, version, author, website, description, id (bundle id)
# Edit CMakePresets.json if you want to pin a different OBS version
./.github/scripts/bootstrap.sh    # MUST run AFTER you edit buildspec.json
```

**Critical:** run `bootstrap.sh` after — not before — editing `buildspec.json`. Running it first generates paths tied to the literal string `obs-plugintemplate`.

## Step 2 — Implement a source / output / encoder / service

Minimal video input source (`src/plugin-main.c`):

```c
#include <obs-module.h>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE("my-plugin", "en-US")

static const char *src_get_name(void *unused) {
    (void)unused;
    return obs_module_text("MySourceName");
}

static void *src_create(obs_data_t *settings, obs_source_t *source) {
    (void)settings; (void)source;
    return bzalloc(sizeof(struct { int unused; }));
}

static void src_destroy(void *data)          { bfree(data); }
static uint32_t src_width(void *data)        { (void)data; return 1920; }
static uint32_t src_height(void *data)       { (void)data; return 1080; }
static void src_render(void *data, gs_effect_t *eff) {
    (void)data; (void)eff;
    /* gs_* graphics-thread calls only */
}

static struct obs_source_info my_src = {
    .id             = "my_src",
    .type           = OBS_SOURCE_TYPE_INPUT,
    .output_flags   = OBS_SOURCE_VIDEO | OBS_SOURCE_CUSTOM_DRAW | OBS_SOURCE_SRGB,
    .get_name       = src_get_name,
    .create         = src_create,
    .destroy        = src_destroy,
    .get_width      = src_width,
    .get_height     = src_height,
    .video_render   = src_render,
};

bool obs_module_load(void) {
    obs_register_source(&my_src);
    return true;      /* return false to refuse loading (e.g. missing dep) */
}

void obs_module_unload(void) { /* global cleanup */ }
```

For output / encoder / service, fill `obs_output_info` / `obs_encoder_info` / `obs_service_info` and call `obs_register_output` / `obs_register_encoder` / `obs_register_service` respectively. Full field list in `references/plugins.md`.

**Properties** (settings dialog UI) — build in a `get_properties` callback:

```c
static obs_properties_t *src_properties(void *data) {
    obs_properties_t *p = obs_properties_create();
    obs_properties_add_int(p, "width",  obs_module_text("Width"),  16, 4096, 1);
    obs_properties_add_text(p, "label", obs_module_text("Label"), OBS_TEXT_DEFAULT);
    obs_property_t *list = obs_properties_add_list(p, "mode",
        obs_module_text("Mode"), OBS_COMBO_TYPE_LIST, OBS_COMBO_FORMAT_INT);
    obs_property_list_add_int(list, obs_module_text("Fast"), 0);
    obs_property_list_add_int(list, obs_module_text("HQ"),   1);
    return p;
}
```

**Locale** — put strings in `data/locale/en-US.ini` as `MySourceName=My Source` and reference with `obs_module_text("MySourceName")`. The locale file must match the locale string in `OBS_MODULE_USE_DEFAULT_LOCALE`.

## Step 3 — Build

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py build --path ~/src/my-plugin
```

Or raw CMake:

| Platform | Configure | Build |
|---|---|---|
| macOS | `cmake --preset macos` | `cmake --build --preset macos --config RelWithDebInfo` |
| Windows | `cmake --preset windows-x64` | `cmake --build --preset windows-x64 --config RelWithDebInfo` |
| Linux | `cmake --preset ubuntu-x86_64` | `cmake --build --preset ubuntu-x86_64 --config RelWithDebInfo` |

## Step 4 — Install locally

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-local --path ~/src/my-plugin
```

Per-user install paths:

- macOS: `~/Library/Application Support/obs-studio/plugins/<name>.plugin/Contents/MacOS/<name>` (bundle layout).
- Windows: `%APPDATA%\obs-studio\plugins\<name>\bin\64bit\<name>.dll` + `%APPDATA%\obs-studio\plugins\<name>\data\`.
- Linux: `~/.config/obs-studio/plugins/<name>/bin/64bit/<name>.so` + `~/.config/obs-studio/plugins/<name>/data/`.

Verify in OBS: **Help -> Log Files -> View Current Log** and search for your plugin name.

## Step 5 — Install a community plugin

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin streamfx
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin asc
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin move
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin ndi
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin source-record
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin backtrack
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin obs-websocket
```

| Plugin | Repo | Purpose |
|---|---|---|
| obs-websocket | bundled in OBS 28+; else https://github.com/obsproject/obs-websocket | Remote-control API on :4455 |
| StreamFX | https://github.com/Xaymar/obs-StreamFX (archived; community forks exist) | Advanced filters, blending, shaders |
| Advanced Scene Switcher | https://github.com/WarmUpTill/SceneSwitcher | Macro-based scene automation |
| Move (Exeldro) | https://github.com/exeldro/obs-move-transition | Animated filter transitions |
| NDI | https://github.com/obs-ndi/obs-ndi | NewTek NDI in/out (requires NDI Runtime) |
| Source Record | https://github.com/exeldro/obs-source-record | Per-source recording |
| Backtrack | https://github.com/exeldro/obs-backtrack | Instant-replay time-shift buffer |

## Available scripts

- **`scripts/plugins.py`** — stdlib-only CLI: `check`, `scaffold`, `build`, `install-local`, `list-installed`, `install-community`. Supports `--dry-run` and `--verbose`. Non-interactive.

## Reference docs

- **`references/plugins.md`** — full field references for `obs_source_info`, `obs_output_info`, `obs_encoder_info`, `obs_service_info`; `OBS_SOURCE_TYPE` / `output_flags` enums; properties + settings API catalog; buildspec.json schema; OBS-version ↔ ABI matrix; signing/notarization notes; debug tips.

## Gotchas

- **obs-plugintemplate is the ONLY officially-recommended starting point** — do not copy an older sample. Its GitHub Actions CI works cross-platform out of the box.
- **`bootstrap.sh` must run AFTER editing `buildspec.json`**, not before — otherwise it generates paths tied to the literal `obs-plugintemplate` name.
- **`OBS_DECLARE_MODULE()` MUST appear exactly once per plugin binary.** Multiple occurrences (e.g. from merging two example files) cause linker errors.
- **`obs_module_load` returns `bool`** — return `false` to refuse loading (for example, a missing runtime dependency). Do not abort or crash.
- **`bfree()` everything you `bmalloc` / `bzalloc` / `bstrdup` allocated.** Mixing with `malloc`/`free` is undefined.
- **`obs_register_source` takes a pointer to a `obs_source_info`** that must outlive unload — make it `static` or heap-allocate. Stack-allocated structs are a use-after-free.
- **Settings / properties pointers are libobs-owned** — do NOT free them.
- **Sources declaring `OBS_SOURCE_VIDEO` must implement `get_width` + `get_height`.**
- **Async sources** feed frames via `obs_source_output_video` using `obs_source_frame` (fields: `video_format`, `width`, `height`, `linesize`, `full_range`, `color_matrix`, `color_range_min`, `color_range_max`, `data[8]` planes). Synchronous video sources use `video_render`.
- **Graphics (`gs_*`) calls run on the graphics thread only.** Wrap off-thread GPU work with `obs_enter_graphics()` / `obs_leave_graphics()`.
- **Plugin binaries are unsigned** by default — macOS users may need `sudo xattr -rd com.apple.quarantine ~/Library/Application\ Support/obs-studio/plugins/<name>.plugin`.
- **OBS major-version ABI:** a plugin built against OBS 28 may break in 29/30. Pin the target OBS version in `buildspec.json` and rebuild when OBS bumps majors.
- **64-bit only** — 32-bit builds have not been supported since OBS 27.
- **Locale file must match** the locale string in `OBS_MODULE_USE_DEFAULT_LOCALE("my-plugin", "en-US")` — i.e. `data/locale/en-US.ini`.
- **Plugin icon** → `data/icon.svg` (SVG only).
- **Global signals** (`source_create`, `source_destroy`, `source_rename`) via `signal_handler_connect(obs_get_signal_handler(), "<signal>", cb, data)`.
- **Dock widgets** require the frontend-api (`obs_frontend_add_dock_by_id`) and Qt linkage — that's what makes a C++ "frontend plugin" vs. a plain C source plugin.
- **StreamFX is archived**; community forks exist but are not drop-in replacements. Advanced Scene Switcher + Move (Exeldro) are the two most-requested extensions beyond bundled features.
- **NDI plugin requires NDI Runtime** installed separately (https://ndi.video/sdk/).

## Examples

### Example 1: Scaffold + build + install a new source plugin on macOS

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py scaffold \
  --name obs-my-src --author "Alice" --bundle-id com.alice.obs-my-src \
  --description "Experimental source" --outdir ~/src
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py build --path ~/src/obs-my-src
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-local --path ~/src/obs-my-src
# Launch OBS, check Help -> Log Files -> View Current Log for the plugin's name.
```

### Example 2: Install Move + Advanced Scene Switcher on an existing OBS install

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin move
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py install-community --plugin asc
uv run ${CLAUDE_SKILL_DIR}/scripts/plugins.py list-installed
```

### Example 3: Minimal filter skeleton

Change `type` to `OBS_SOURCE_TYPE_FILTER` and implement `filter_video` (sync) or `filter_audio`. Drop `get_width` / `get_height` — filters inherit from their parent.

## Troubleshooting

### "Module not found" / plugin silently missing from OBS

Cause: install path wrong, or ABI mismatch (plugin built against a different OBS major).
Solution: `list-installed` to confirm path. Rebuild against the installed OBS version; match `OBS_STUDIO_VERSION` in `buildspec.json`.

### macOS: "<plugin> is damaged and can't be opened"

Cause: quarantine xattr on an unsigned plugin bundle.
Solution: `sudo xattr -rd com.apple.quarantine ~/Library/Application\ Support/obs-studio/plugins/<name>.plugin`.

### Linker error: multiple definition of `obs_module_*`

Cause: two translation units each invoked `OBS_DECLARE_MODULE()`.
Solution: keep it in one `.c` only.

### OBS logs: "Required OBS plugin version mismatch"

Cause: the plugin declared a minimum OBS version higher than the host.
Solution: rebuild with a lower target in `buildspec.json`, or upgrade OBS.

### NDI plugin loads but no NDI sources appear

Cause: NDI Runtime (separate install) missing or outdated.
Solution: install the NDI Runtime from https://ndi.video/sdk/ and restart OBS.
