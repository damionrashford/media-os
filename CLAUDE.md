# CLAUDE.md

Development instructions for Claude Code when working IN this repository (authoring / maintaining skills).

This is NOT documentation for end users of the plugin. End users install via `/plugin install media-os@media-os` and invoke skills. This file is for contributors editing skill source.

## Repository role

This repo IS a Claude Code plugin + marketplace. Users install the `media-os` plugin from the `media-os` marketplace. The plugin surface is the `skills/` directory at repo root (96 skills). The `.claude-plugin/` directory holds the plugin manifest and marketplace catalog.

There is no service, no app, no build step. The deliverable is the directory tree itself.

## Directory layout

```
.claude-plugin/
  plugin.json            # plugin manifest (authored by hand, keep versions in sync)
  marketplace.json       # marketplace catalog (one entry: media-os → ./)
.claude/
  skills/
    skill-creator/       # authoring harness — NOT distributed, dev-only
  settings.json          # contributor-friendly permission defaults
skills/                  # 96 production skills — THIS is what the plugin ships
workflows/
  index.md               # master workflow catalog
  *.md                   # 13 domain workflow guides
CLAUDE.md                # this file (dev instructions)
README.md                # user-facing overview + install flow
LICENSE                  # MIT
CHANGELOG.md             # release history
```

Invariant: the `skills/` directory is the plugin's entire user-facing surface. Everything else supports authoring, docs, or distribution.

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
Dev-only. Not part of the distributed plugin. Use it to scaffold + validate new skills.

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

The scaffolder emits `skills/<name>/SKILL.md` with correct frontmatter, plus `scripts/process.py` and `references/guide.md` as placeholders. **Delete both placeholders** after replacing with real files named after the skill's function (e.g. `scripts/transcode.py`, `references/codecs.md`).

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

## Skill categories (96 in plugin + 11 dev-only in `.claude/skills/`)

Layer 1 — FFmpeg core editing + conversion (12): `ffmpeg-transcode`, `ffmpeg-cut-concat`, `ffmpeg-video-filter`, `ffmpeg-audio-filter`, `ffmpeg-subtitles`, `ffmpeg-frames-images`, `ffmpeg-streaming`, `ffmpeg-capture`, `ffmpeg-hwaccel`, `ffmpeg-probe`, `ffmpeg-bitstream`, `ffmpeg-playback`.

Layer 1 — Visual + color (10): `ffmpeg-hdr-color`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro`, `ffmpeg-chromakey`, `ffmpeg-compose-mask`, `ffmpeg-lens-perspective`, `ffmpeg-stabilize`, `ffmpeg-denoise-restore`, `ffmpeg-ivtc`, `ffmpeg-speed-time`.

Layer 1 — Audio specialized (3): `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `ffmpeg-captions`.

Layer 1 — Streaming specialized (2): `ffmpeg-whip`, `ffmpeg-rist-zmq`.

Layer 1 — Analysis + authoring (6): `ffmpeg-detect`, `ffmpeg-quality`, `ffmpeg-metadata`, `ffmpeg-synth`, `ffmpeg-geq-expr`, `ffmpeg-ocr-logo`.

Layer 1 — Immersive + broadcast (3): `ffmpeg-360-3d`, `ffmpeg-mxf-imf`, `ffmpeg-drm`.

Layer 1 — Infrastructure (2): `ffmpeg-docs`, `ffmpeg-vapoursynth`.

Layer 2 — Companion tools (15): `media-ytdlp`, `media-whisper`, `media-demucs`, `media-mkvtoolnix`, `media-gpac`, `media-shaka`, `media-handbrake`, `media-moviepy`, `media-ffmpeg-normalize`, `media-mediainfo`, `media-scenedetect`, `media-subtitle-sync`, `media-imagemagick`, `media-exiftool`, `media-sox`, `media-batch`, `media-cloud-upload`.

Layer 3 — OBS Studio (5): `obs-docs`, `obs-websocket`, `obs-config`, `obs-plugins`, `obs-scripting`.

Layer 4 — Frameworks (4): `gstreamer-docs`, `gstreamer-pipeline`, `mediamtx-docs`, `mediamtx-server`.

Layer 5 — Broadcast IP + editorial (10): `ndi-docs`, `ndi-tools`, `otio-docs`, `otio-convert`, `hdr-dynmeta-docs`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `decklink-docs`, `decklink-tools`, `gphoto2-tether`.

Layer 6 — Control protocols (6): `media-midi`, `media-osc`, `media-dmx`, `ptz-docs`, `ptz-visca`, `ptz-onvif`.

Layer 6 — System audio (5): `audio-routing-docs`, `audio-pipewire`, `audio-jack`, `audio-coreaudio`, `audio-wasapi`.

Layer 7 — VFX (3): `vfx-usd`, `vfx-openexr`, `vfx-oiio`.

Layer 8 — CV + WebRTC (6): `cv-opencv`, `cv-mediapipe`, `webrtc-spec`, `webrtc-pion`, `webrtc-mediasoup`, `webrtc-livekit`.

Layer 9 — 2026 AI media (12): `media-upscale`, `media-interpolate`, `media-matte`, `media-depth`, `media-denoise-ai`, `media-tts-ai`, `media-sd`, `media-svd`, `media-musicgen`, `media-lipsync`, `media-ocr-ai`, `media-tag`.

When recommending an FFmpeg flag / filter, **always invoke `ffmpeg-docs` first**. It's the anti-hallucination guardrail. Same for OBS (`obs-docs`), GStreamer (`gstreamer-docs`), MediaMTX (`mediamtx-docs`), NDI (`ndi-docs`), OTIO (`otio-docs`), PTZ (`ptz-docs`), DeckLink (`decklink-docs`), HDR dynamic metadata (`hdr-dynmeta-docs`), system audio (`audio-routing-docs`).

## AI skill license discipline (Layer 9)

Every AI skill passes a strict OSI-open + commercial-safe filter. Allowed licenses: Apache-2, MIT, BSD, GPL.

Always-dropped — NEVER recommend even if the user asks by name:
- XTTS-v2 (Coqui CPML NC), F5-TTS (research), FLUX-dev (NC), SDXL / SD3 base (restrictive), Stable Video Diffusion (NC research), Wav2Lip (research), SadTalker (NC), Meta MusicGen (CC-BY-NC), Surya OCR (commercial restriction), CodeFormer (NC research), DAIN (research-only).

Each Layer 9 skill's `references/LICENSES.md` enumerates the dropped models with explicit reasoning. When authoring or modifying an AI skill, update that file.

## Version management

- Plugin version lives in `.claude-plugin/plugin.json`. Bump on every release (semver).
- Marketplace version lives in `.claude-plugin/marketplace.json` metadata. Keep in sync with plugin version.
- Do NOT duplicate the version in both the plugin.json and marketplace entry — plugin.json wins silently if both are set. Set it in plugin.json only (except for relative-path plugins where the marketplace entry must carry it).
- Tag git releases as `v<MAJOR>.<MINOR>.<PATCH>`.

## Git workflow

- `main` is the source-of-truth branch.
- The `.claude/settings.json` in this repo denies `--amend`, `--no-verify`, force-push, hard-reset, clean. Do not try them; fix underlying issues instead.
- Commits reference specific skill(s) touched when possible: `skills/ffmpeg-hdr-color: fix zscale sandwich for HLG→PQ`.
- Before committing a new/changed skill, run `validate.py` on that skill.
- Before pushing, validate the whole suite.

## Common pitfalls

- **Leaving `scripts/process.py` and `references/guide.md` placeholders** after scaffolding — delete them once the real files are in place. The validator warns.
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
