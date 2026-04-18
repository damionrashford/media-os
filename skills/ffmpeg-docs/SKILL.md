---
name: ffmpeg-docs
description: >
  Search and fetch official FFmpeg documentation from ffmpeg.org: ffmpeg, ffmpeg-all, ffmpeg-filters, ffmpeg-codecs, ffmpeg-formats, ffmpeg-protocols, ffmpeg-devices, ffmpeg-bitstream-filters, ffmpeg-utils, ffmpeg-scaler, ffmpeg-resampler, ffprobe-all, ffplay-all, general, faq, platform, developer. Use when the user asks to look up an ffmpeg option, find filter parameters, check a muxer or demuxer option, search ffmpeg docs, get the official description of a codec flag, find out what an ffmpeg flag does, or verify ffmpeg syntax against the real documentation.
argument-hint: "[query]"
---

# FFmpeg Docs

**Context:** $ARGUMENTS

## Quick start

- **Find a filter / option:** → Step 2 (`search --query <term>`)
- **Read the full section for a filter:** → Step 3 (`section --page ffmpeg-filters --id <anchor>`)
- **Grab an entire doc page:** → Step 4 (`fetch --page <name>`)
- **Prime cache for offline use:** → Step 5 (`index`)

## When to use

- User asks "what does `-X` do in ffmpeg?" or "what are the parameters for filter Y?"
- Need to verify a flag name exists before recommending it (prevents hallucinated options).
- Need the exact option table for a muxer / demuxer / protocol / device.
- Need to cite the canonical ffmpeg.org URL in a response.
- Before writing any non-trivial ffmpeg command, check the current doc for the filter/option you're about to use.

---

## Step 1 — Know the page catalog

The script only works against a fixed list of known ffmpeg.org doc pages. Get the list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py list-pages
```

Common picks:

| Question | Page |
|---|---|
| "What does filter X do?" | `ffmpeg-filters` |
| "What are the options for `-c:v libx264`?" | `ffmpeg-codecs` |
| "What HLS muxer options exist?" | `ffmpeg-formats` |
| "What does `srt://` accept?" | `ffmpeg-protocols` |
| "How do I capture with avfoundation?" | `ffmpeg-devices` |
| "What bitstream filters are there?" | `ffmpeg-bitstream-filters` |
| "ffprobe output fields?" | `ffprobe-all` |
| "Expression syntax (`eval`, `if`, `gt`)?" | `ffmpeg-utils` |
| "Scaler flags?" | `ffmpeg-scaler` |
| "Resampler options?" | `ffmpeg-resampler` |

Read [`references/pages.md`](references/pages.md) for the full catalog with descriptions.

---

## Step 2 — Search first (this is the default)

When the user names a filter, option, muxer, or codec, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "tonemap" --limit 5
```

When you already know which page, scope the search to it (faster, less noise):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "hls_time" --page ffmpeg-formats
```

Output format for each hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with anchor>
<snippet with ±3 lines of context>
```

Use `--format json` for machine-parseable output when chaining into another tool.

First run downloads the page (~1–2s). Subsequent runs hit the local cache (`~/.cache/ffmpeg-docs/`) — instant.

---

## Step 3 — Read one section in full

When the search hit points to a specific filter/option and you want the whole block (option list + description), use `section`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py section --page ffmpeg-filters --id tonemap-1
```

`--id` accepts either:

- An anchor id printed in search results as `[§xxxx]` (e.g. `tonemap-1`, `Muxer-Options`).
- A heading keyword — the script falls back to the first heading matching the string.

Output is the section from its heading down to the next same-or-higher-level heading.

---

## Step 4 — Fetch a whole page

Only when you need to dump the entire page (rare — usually overkill):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py fetch --page ffmpeg-filters
```

Pair with `--format json` for structured handoff.

---

## Step 5 — Prime the cache (optional)

For reliable offline lookups or before a burst of queries:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py index
```

Fetches every known page, stores text-extracted versions in `~/.cache/ffmpeg-docs/`. Run once; re-run only when you need fresh docs (new ffmpeg release, upstream doc edits).

To override the cache location: `export FFMPEG_DOCS_CACHE=/path/to/dir`.

To clear: `uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py clear-cache`.

---

## Gotchas

- **Never recommend an ffmpeg flag without searching first.** Half the problem this skill solves is preventing hallucinated options. If `search --query "<flag>"` returns zero hits, the flag doesn't exist on that page — don't claim it does.
- **Cache is keyed by page name only, not by ffmpeg version.** If the user is on a specific ffmpeg version and the latest docs don't match, re-fetch with `--no-cache` or clear the cache.
- **The text extraction is lossy for complex tables.** The script converts ffmpeg.org HTML → text (headings, `dt`/`dd` option pairs, code blocks preserved; complex multi-column tables flattened). If a search hit looks incomplete, open the URL printed in the hit header and read the original page.
- **Anchors inside search results have the form `[§anchor-id]`** (a literal `§` sentinel). When passing to `section --id`, drop the `[§` / `]` brackets — just use the raw id.
- **Some ffmpeg.org pages are MASSIVE** (`ffmpeg-filters` is ~2 MB of HTML). Searching the full page is fast because it hits the cache; re-fetching with `--no-cache` takes a few seconds. Don't `fetch` the whole page into the conversation — `search` with `--limit` or `section` are almost always better.
- **Filter names are case-sensitive in ffmpeg but search is case-insensitive.** The search will match regardless; the CLI invocation you recommend must use the exact case.
- **`ffmpeg-all` / `ffprobe-all` / `ffplay-all` are single-file concatenations** of the per-topic pages. They're slower to search (big files) and duplicate content. Prefer the topic-specific page (`ffmpeg-filters`, `ffmpeg-formats`) unless you explicitly want everything.
- **Libav\* pages (`libavutil`, `libswscale`, `libswresample`, `libavcodec`, `libavformat`, `libavdevice`, `libavfilter`) are C API docs**, not CLI docs. Skip them for command-line questions — they rarely contain flag/option info.
- **This skill does not read doxygen** (`/doxygen/trunk/…`). It's scoped to the curated manual pages only.
- **The script is stdlib-only** — no pip install. Works anywhere Python 3.9+ runs.
- **One-shot queries can skip `index`.** The script fetches lazily on first use. `index` is for when you plan to run many queries or want offline.

---

## Examples

### Example 1 — "What are the options for the tonemap filter?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "tonemap" --page ffmpeg-filters --limit 5
```

Pick the hit with heading `## [§tonemap-1] …`, then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py section --page ffmpeg-filters --id tonemap-1
```

Cite the URL printed in the hit header when responding.

### Example 2 — "What are the valid `hls_segment_type` values?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "hls_segment_type" --page ffmpeg-formats
```

### Example 3 — "What does `-movflags +faststart` actually do?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "faststart" --page ffmpeg-formats
```

### Example 4 — "Does the `sr` filter still exist or is it deprecated?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py search --query "sr" --page ffmpeg-filters --regex --limit 3
```

Use `--regex` with anchored patterns (`^sr\b`) when a short term has many false positives.

### Example 5 — "What color expressions does `drawtext` accept?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py section --page ffmpeg-utils --id Color
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** The name isn't in the catalog.
**Solution:** Run `list-pages` to see valid names. Common mistakes: using `filters` instead of `ffmpeg-filters`; using `protocols` instead of `ffmpeg-protocols`.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** System certificate store is out of date (mostly macOS with older Python installs).
**Solution:** Install/update certifi, or run `/Applications/Python\ 3.x/Install\ Certificates.command`. As a last resort, set `SSL_CERT_FILE` env var to a valid CA bundle path. Do NOT patch the script to disable SSL verification.

### Search returns zero hits

**Cause:** Term doesn't exist on that page, or you're searching a page the term isn't documented on.
**Solution:** Drop `--page` to search all pages, or try a broader query. Some options live in `ffmpeg-utils` (expressions, colors) rather than the obvious page.

### Results look truncated / tables broken

**Cause:** Text extraction flattens complex HTML tables.
**Solution:** The search-hit header prints the canonical URL with anchor. Open it directly (WebFetch or browser) for the authoritative view.

### Cache is stale after ffmpeg upstream update

**Solution:** `clear-cache` then `index` (or just `fetch --no-cache --page <name>` for a single page).
