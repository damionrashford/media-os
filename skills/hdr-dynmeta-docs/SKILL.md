---
name: hdr-dynmeta-docs
description: >
  Search and fetch docs for HDR dynamic-metadata CLIs: dovi_tool (Dolby Vision RPU authoring — profiles 4, 5, 7, 8.1, 8.4 — github.com/quietvoid/dovi_tool) and hdr10plus_tool (HDR10+ SEI authoring — github.com/quietvoid/hdr10plus_tool). Canonical subcommand lists (info, generate, editor, export, plot, convert, demux, mux, extract-rpu, inject-rpu for dovi_tool; extract, inject, remove, plot, editor for hdr10plus_tool), HEVC Annex-B + Matroska I/O, integration with ffmpeg bitstream filters + mkvmerge + MP4Box. Use when the user asks to look up a dovi_tool or hdr10plus_tool subcommand, check Dolby Vision profile support, verify HDR dynamic-metadata tool usage, or read the canonical GitHub README.
argument-hint: "[query]"
---

# HDR DynMeta Docs

**Context:** $ARGUMENTS

## Quick start

- **Find a dovi_tool / hdr10plus_tool subcommand or flag:** → Step 2 (`search`)
- **Read the full README section:** → Step 3 (`section`)
- **Grab a whole README / release-notes page:** → Step 4 (`fetch`)
- **Prime cache for offline use:** → Step 5 (`index`)

## When to use

- User asks "which Dolby Vision profiles does dovi_tool support?" (answer: 4, 5, 7, 8.1, 8.4 — 8.2 unknown).
- User asks about hdr10plus_tool subcommands (extract / inject / remove / plot / editor).
- User is about to chain `ffmpeg bsf=hevc_mp4toannexb | dovi_tool extract-rpu | …` and needs to verify flag names.
- Need latest release version and Rust MSRV before recommending install method.
- For the execution side (actually running these tools), see `hdr-dovi-tool` + `hdr-hdr10plus-tool` skills.

---

## Step 1 — Page catalog

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py list-pages
```

| Page | URL |
|---|---|
| `dovi-readme` | `github.com/quietvoid/dovi_tool/blob/main/README.md` (raw) |
| `dovi-releases` | `api.github.com/repos/quietvoid/dovi_tool/releases/latest` |
| `hdr10plus-readme` | `github.com/quietvoid/hdr10plus_tool/blob/main/README.md` (raw) |
| `hdr10plus-releases` | `api.github.com/repos/quietvoid/hdr10plus_tool/releases/latest` |

Read [`references/subcommands.md`](references/subcommands.md) for the verified subcommand + flag catalog.

---

## Step 2 — Search first

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "extract-rpu" --page dovi-readme
```

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "editor" --page hdr10plus-readme
```

Use `--format json` for machine-parseable output.

---

## Step 3 — Read a section

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py section --page dovi-readme --id Usage
```

---

## Step 4 — Fetch a page

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py fetch --page dovi-readme
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py fetch --page hdr10plus-releases
```

---

## Step 5 — Prime the cache

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py index
```

Cache dir: `~/.cache/hdr-dynmeta-docs/`. Override with `HDR_DYNMETA_DOCS_CACHE=/path`.

---

## Gotchas

- **Both tools are by `quietvoid`, written in Rust.** Install via `cargo install` (from source) or pre-built binaries from each repo's Releases. hdr10plus_tool 1.7.2 (Dec 2025) requires Rust ≥ 1.85.0. dovi_tool tracks similar recent MSRVs.
- **dovi_tool supported DV profiles: 4, 5, 7, 8.1, 8.4.** Profile 8.2 is NOT documented as supported — if a user asks, do not assume it works. Profile 7 is BL+EL (dual-layer) and can be `convert`-ed to 8.1 (single-layer with RPU).
- **Canonical dovi_tool subcommands (verified):** `info`, `generate`, `editor`, `export`, `plot`, `convert`, `demux`, `mux`, `extract-rpu`, `inject-rpu`, `remove`.
- **Canonical hdr10plus_tool subcommands (verified):** `extract`, `inject`, `remove`, `plot`, `editor`. No `convert` / `demux` / `mux` — those are dovi_tool only.
- **Input to `extract-rpu` and `extract` must be HEVC Annex-B bytestream**, NOT MP4/MKV-muxed HEVC. Extract it first: `ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | dovi_tool extract-rpu -`.
- **After `inject-rpu` / `inject`, you get Annex-B HEVC again** — you have to re-mux into MKV via `mkvmerge` or MP4 via `MP4Box`. ffmpeg's MP4 muxer for HEVC+RPU is flaky; MP4Box is recommended.
- **GitHub API rate limit:** unauthenticated requests are capped at 60/hour. The release-info pages use `api.github.com`. Set `GITHUB_TOKEN=…` env var for 5000/hour if you hit the limit.
- **Release-note pages are JSON from the GitHub API** — text-extracted to show tag name, published date, and body.
- **Docs are Markdown from `raw.githubusercontent.com`** — preserved as-is by the script (no HTML→text conversion). Headings with `##` map cleanly to `section --id Heading`.
- **Neither tool writes HDR10+ or Dolby Vision from scratch.** They operate on existing RPU/SEI data. "Generate" in dovi_tool produces profile-compliant RPU from input like L1 analysis + Dolby XML — it's authoring, not AI. No tool "adds Dolby Vision to an SDR video" on its own.
- **The script is stdlib-only.** No cargo, no Rust needed to read docs — only to run the actual tools.

---

## Examples

### Example 1 — "What Dolby Vision profiles does dovi_tool support?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "profile" --page dovi-readme --limit 10
```

### Example 2 — "How does `dovi_tool editor` work?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "editor" --page dovi-readme
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py section --page dovi-readme --id editor
```

### Example 3 — "What's the latest hdr10plus_tool version?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py fetch --page hdr10plus-releases
```

### Example 4 — "How do I extract RPU from a Blu-ray remux?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "extract-rpu" --page dovi-readme
```

### Example 5 — "Does hdr10plus_tool have a `convert` command?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrdocs.py search --query "convert" --page hdr10plus-readme
# (expected: no hits — hdr10plus_tool has extract/inject/remove/plot/editor only)
```

---

## Troubleshooting

### Error: `urlopen error 403` from GitHub API

**Cause:** Rate-limited (60 unauth requests/hour).
**Solution:** Set `GITHUB_TOKEN=...` env var (a public-repo-read token is enough).

### Search returns no hits for a subcommand you think exists

**Cause:** Wrong tool or wrong page. `convert` is dovi_tool only; `editor` is in both; `x265-encode` isn't a real subcommand (that's a convenience preset in `hdr-hdr10plus-tool` wrapper).
**Solution:** Drop `--page` to search both READMEs. Consult `references/subcommands.md`.

### Cache is stale after upstream release

**Solution:** `clear-cache` then `index`.

---

## Reference docs

- Full subcommand + flag catalog (verified against current READMEs) → `references/subcommands.md`.
