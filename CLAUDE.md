# CLAUDE.md

Development instructions for Claude Code when working IN this repository (authoring / maintaining skills).

This is NOT documentation for end users of the plugin. End users install via `/plugin install media-os@media-os` and invoke skills. This file is for contributors editing skill source.

## Repository role

This repo IS a Claude Code plugin + marketplace. Users install the `media-os` plugin from the `media-os` marketplace. The plugin surface is the `skills/` directory at repo root (**40 skills**). The `.claude-plugin/` directory holds the plugin manifest and marketplace catalog.

There is no service, no app, no build step. The deliverable is the directory tree itself.

v3 is a **breaking** change (skill names changed wholesale): the previous 110-skill suite was consolidated to 40 lean router-over-techniques skills, the 13 `workflow-*` skills were deleted (their pipelines now live in `modes/`), and the 10 former dev-only `*-docs` skills were promoted into the plugin. Plugin version is `3.0.0`.

## Directory layout

```
.claude-plugin/
  plugin.json            # plugin manifest (userConfig fields live here) — REAL auto-discovered primitive
  marketplace.json       # marketplace catalog (one entry: media-os → ./)
.claude/
  skills/                # dev-only: skill-creator (authoring harness) + studio symlink — NOT distributed
  agents/                # dev-only agents (repo maintenance) — NOT distributed
  settings.json          # contributor-friendly permission defaults
skills/                  # 40 consolidated router-over-techniques skills — distributed (auto-discovered)
agents/                  # 7 orchestrator agents (architect/probe/qc/hdr/encoder/live/delivery) — auto-discovered
modes/                   # CONVENTION dir — routed playbooks; the SINGLE pipeline source, read by the router
  _shared.md             #   cross-cutting prefix: Iron Laws + rationalization table
  <mode>.md              #   one playbook per pipeline (vod-post-production, live-production, ...)
hooks/
  hooks.json             # 5 lifecycle hooks (SessionStart, UserPromptSubmit, Pre/PostToolUse, Stop) — auto-discovered
  scripts/               # hook executables (stdlib Python 3, PEP 723)
bin/                     # CONVENTION dir — moprobe/moqc/mosafe CLIs. NOT auto-added to PATH (see below)
monitors/
  monitors.json          # CONVENTION dir — aspirational config, NO automatic runner (see below)
  scripts/
docs/                    # GitHub Pages site (index.html, llms.txt, sitemap.xml, _config.yml)
CLAUDE.md                # this file (dev instructions)
README.md                # user-facing overview + install flow
CONTRIBUTING.md          # contributor guide
LICENSE                  # MIT
CHANGELOG.md             # release history
```

Invariant: the `skills/` directory is the plugin's entire user-facing surface. Everything else supports authoring, docs, or distribution.

### Real primitives vs. convention directories

Only these are **auto-discovered Claude Code plugin primitives**: `skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `.mcp.json`, and `.claude-plugin/plugin.json`. The rest are project conventions this repo wires up by hand:

- **`modes/` is a convention.** Claude Code does not load it. The `media-pipeline-router` skill reads `modes/_shared.md` + the matched `modes/<mode>.md` itself when composing a dispatch.
- **`bin/` is NOT auto-added to PATH.** There is no manifest `bin` field and Claude Code does not install these CLIs. Invoke them as `${CLAUDE_PLUGIN_ROOT}/bin/<tool>`, or the user adds `bin/` to their own PATH. Do not write SKILL.md/mode text that assumes a bare `moprobe` resolves.
- **`monitors/monitors.json` has NO automatic runner.** No `monitors` hook event exists. It is aspirational config, not wired — nothing executes it.

## Hard rules — do not violate

### Skill structure
- Every skill is `skills/<name>/SKILL.md` + optional `scripts/` + optional `references/` + optional `assets/`.
- A skill folder is sealed. Scripts MUST NOT import from other skills. Copying a skill folder to any other plugin must yield a working skill.
- Skill `name` field is kebab-case, no leading `claude-` or `anthropic-` (reserved).
- SKILL.md body ≤ 500 lines. Deep reference material (option tables, recipe books, grammars) goes in `references/<topic>.md` and loads only when SKILL.md explicitly says "Read `references/X.md` when [condition]".

### Script standards
- Python 3.9+, stdlib only. No pip dependencies.
- PEP 723 inline-dep header at the top of every script (even if empty) so `uv run script.py` works.
- Every helper supports `--dry-run` and `--verbose`.
- Print the exact shell command to stderr before executing it (observability).
- No `input()` calls anywhere. Agents run non-interactive. The validator flags even docstring prose containing `input(` — phrase it as "non-interactive" instead.
- Reference other skills' scripts using `${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/<file>.py`, NOT hardcoded absolute paths.

### Prohibited files
- No `README.md` inside a skill folder (spec forbids).
- No `__pycache__` directories committed (.gitignore handles this).
- No absolute local paths anywhere (`/Users/...`, `/home/...`).

### Authoring harness (`.claude/skills/skill-creator/`)
Dev-only. Not part of the distributed plugin. Use it to scaffold + validate new skills. `.claude/skills/` now holds only `skill-creator` (the dev authoring harness) and a `studio` symlink — the 10 former dev-only `*-docs` skills were promoted into the plugin (see "Skill suite" below).

## Authoring workflow

### Scaffold a new skill
```bash
uv run .claude/skills/skill-creator/scripts/scaffold.py \
  --name <new-skill-name> \
  --output skills \
  --with-scripts \
  --with-references \
  --argument-hint "[input] [output]" \
  --description "What it does. Use when the user asks to X, Y, or Z."
```

The scaffolder emits `skills/<name>/SKILL.md` with correct frontmatter, plus `scripts/process.py` and `references/guide.md` as placeholders. **Delete both placeholders** after replacing with real files named after the skill's function (e.g. `scripts/encode.py`, `references/codecs.md`). The validator **errors** (exit 1) on leftover scaffold placeholder content — stubs cannot ship.

### Validate one skill
```bash
uv run .claude/skills/skill-creator/scripts/validate.py skills/<name>
```

Exit codes: `0` clean, `2` warnings only (acceptable), `1` spec violations (must fix before committing).

The only warning tolerated suite-wide is `description-display-truncation` — skills front-load an exhaustive trigger-phrase list that exceeds the 250-char `/` menu preview. Claude still reads the full description; only the menu preview is truncated.

### Validate the whole suite
```bash
for s in skills/*; do
  uv run .claude/skills/skill-creator/scripts/validate.py "$s"
done
```

### Validate the plugin + marketplace
```bash
uv run .claude/skills/skill-creator/scripts/validate-plugin.py .
```
(Or whatever the equivalent command is — see skill-creator's own SKILL.md.)

## Skill body conventions

Each SKILL.md follows this structure:

```markdown
---
<frontmatter>
---

# Skill Name

**Context:** <brief framing, if needed>

## Quick start
3 bullets pointing to the most common steps.

## When to use
Bullet list of scenarios.

## Step N — <action>
Exact, actionable instructions. Include real commands, field names, expected output.

## Gotchas
The production landmines. Highest-value section — what an LLM gets wrong from training data alone.

## Examples
Input → Commands → Result.

## Troubleshooting
Error → Cause → Solution.
```

The **Gotchas** section is the most valuable — FFmpeg specifics like `-sc_threshold 0` for HLS GOPs, `aac_adtstoasc` for TS→MP4, `&HAABBGGRR` ASS color order, `hwdownload,format=nv12` for GPU→CPU, `-movflags +faststart` second-pass rewrite, `zscale=t=linear → format=gbrpf32le` sandwich for PQ↔HLG, `fieldmatch → decimate` IVTC order, `repeat-headers=1` for streaming HEVC.

Helper scripts use argparse subcommands (not mode flags) when there are 3+ distinct workflows, e.g. `scripts/cut.py trim | segment | concat-copy | concat-filter`. Each subcommand has its own `--dry-run`/`--verbose`. Use the parent-parser pattern so globals work before OR after the subcommand.

Reference docs are option catalogs (tables of encoder flags, protocol options, channel layouts, NAL unit types, expression grammars), not tutorials.

## Skill suite (40 skills in plugin + skill-creator dev-only in `.claude/skills/`)

Each skill is a **lean router-over-techniques** SKILL.md: the CSO `description` is trigger phrases only (under 1024 chars), the body is a thin technique map, and each absorbed technique's full depth lives in `references/<technique>.md` (loaded only when SKILL.md points there). The pre-v3 110-skill suite collapsed into these 40.

Routing (2): `media-pipeline-router` (the router — reads `modes/`), `using-media-os` (behavioral gateway injected at SessionStart).

FFmpeg (11): `ffmpeg-encode`, `ffmpeg-edit`, `ffmpeg-filter`, `ffmpeg-color`, `ffmpeg-restore`, `ffmpeg-composite`, `ffmpeg-analyze`, `ffmpeg-subtitle`, `ffmpeg-stream`, `ffmpeg-broadcast`, `ffmpeg-docs`.

Companion CLIs (11): `media-download`, `media-whisper`, `media-demucs`, `media-package`, `media-handbrake`, `media-moviepy`, `media-audio-cli`, `media-inspect`, `media-imagemagick`, `media-batch`, `media-cloud-upload`.

Frameworks + broadcast IP (6): `obs`, `gstreamer`, `mediamtx`, `broadcast-io`, `otio`, `hdr-meta`.

Control + system audio (3): `media-control`, `ptz`, `audio-routing`.

VFX + CV + WebRTC (3): `vfx`, `cv`, `webrtc`.

AI media (4): `ai-enhance`, `ai-generate`, `ai-understand`, `ai-lipsync`.

### Docs-search anti-hallucination guardrail

The 10 former dev-only `*-docs` skills were **promoted into the plugin**. `ffmpeg-docs` is a standalone skill; the rest folded into their domain skill's `references/docs-search.md` (e.g. `obs/references/docs-search.md`, `mediamtx/references/docs-search.md`, `broadcast-io/references/docs-search-ndi.md` + `docs-search-decklink.md`, `otio/`, `ptz/`, `gstreamer/`, `hdr-meta/`, `audio-routing/`).

When recommending an FFmpeg flag / filter, **always invoke `ffmpeg-docs` first** — it's the anti-hallucination guardrail. For the other domains, read the skill's `references/docs-search.md` before quoting a non-obvious flag, protocol option, or API call.

### Rigor layer (Superpowers-style)

v3 adds a behavioral-rigor layer that makes the dispatch contract non-optional:

- **`skills/using-media-os`** is injected at SessionStart by `hooks/scripts/session-start-capabilities.py`. It establishes that any media-production intent routes through `media-pipeline-router` and that every op is probe-first, `mosafe`-wrapped, and quality-gated — Claude does not hand-roll ffmpeg in the main thread.
- **`modes/_shared.md`** is the cross-cutting prefix prepended to every dispatch. It carries the **Iron Laws** (fresh `moprobe` first; `mosafe`-wrap every ffmpeg call; `moqc` gate before any "done" claim; never use an NC/research/commercial-restricted AI model) plus a **rationalization table** that names the excuses ("it's a simple transcode, I don't need to probe") and rebuts each one.

When editing modes or these two skills, keep the Iron Laws and the rationalization table intact — they are the spine of the system.

## AI skill license discipline

Every AI skill (`ai-enhance`, `ai-generate`, `ai-understand`, `ai-lipsync`) passes a strict OSI-open + commercial-safe filter. Allowed licenses: Apache-2, MIT, BSD, GPL.

Always-dropped — NEVER recommend even if the user asks by name:
- XTTS-v2 (Coqui CPML NC), F5-TTS (research), FLUX-dev (NC), SDXL / SD3 base (restrictive), Stable Video Diffusion (NC research), Wav2Lip (research), SadTalker (NC), Meta MusicGen (CC-BY-NC), Surya OCR (commercial restriction), CodeFormer (NC research), DAIN (research-only).

Each AI skill enumerates its dropped models with explicit reasoning in per-technique license files under `references/` — e.g. `ai-enhance/references/upscale-LICENSES.md`, `ai-generate/references/sd-LICENSES.md`, `ai-understand/references/matte-LICENSES.md`, `ai-lipsync/references/LICENSES.md`. When authoring or modifying an AI technique, update the matching `*-LICENSES.md`.

## Version management

- Plugin version lives in `.claude-plugin/plugin.json`. Bump on every release (semver). Current version is `3.0.0` (v3 renamed skills — a breaking major).
- Marketplace version lives in `.claude-plugin/marketplace.json` metadata. Keep in sync with plugin version.
- Do NOT duplicate the version in both the plugin.json and marketplace entry — plugin.json wins silently if both are set. Set it in plugin.json only (except for relative-path plugins where the marketplace entry must carry it).
- Tag git releases as `v<MAJOR>.<MINOR>.<PATCH>`.

## Git workflow

- `main` is the source-of-truth branch.
- The `.claude/settings.json` in this repo denies `--amend`, `--no-verify`, force-push, hard-reset, clean. Do not try them; fix underlying issues instead.
- Commits reference specific skill(s) touched when possible: `skills/ffmpeg-color: fix zscale sandwich for HLG→PQ`.
- Before committing a new/changed skill, run `validate.py` on that skill.
- Before pushing, validate the whole suite.

## Common pitfalls

- **Leaving `scripts/process.py` and `references/guide.md` placeholders** after scaffolding — delete them once the real files are in place. The validator **errors** (exit 1) on leftover placeholder content.
- **Absolute paths** (`/Users/...`) leaking into SKILL.md or reference docs. Use `${CLAUDE_PLUGIN_ROOT}` when referencing files inside the plugin, relative paths when referencing skill-local files.
- **Hardcoding examples to a specific user's environment** — use placeholders like `/tmp/input.mp4`, `~/Videos/`, `$HOME/work/`.
- **Over-expanding SKILL.md body** — if a skill needs > 500 lines, split reference material into `references/<topic>.md` files and load on demand.
- **Missing `--dry-run`** on a helper — required.
- **Using pip-installed packages** in a helper script — forbidden. Shell out to a CLI tool instead.
- **Referencing one skill from another by absolute path** — use `${CLAUDE_PLUGIN_ROOT}/skills/<name>/scripts/<file>.py`.

## Distribution

Users install the plugin with:
```
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

After install, skills load namespaced as `/media-os:<skill-name>`. Contributors working in this repo access skills locally via the `.claude/skills/skill-creator` dev harness and the `skills/` directory directly.

Releases publish via GitHub Releases tagged `v1.0.0`, `v1.1.0`, etc. Auto-update is enabled by default for the official Anthropic marketplace only; third-party marketplaces (this one) require users to run `/plugin marketplace update media-os` to pull new versions.
