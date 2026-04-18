---
name: otio-docs
description: >
  Search and fetch official OpenTimelineIO (OTIO) docs from opentimelineio.readthedocs.io and github.com/AcademySoftwareFoundation/OpenTimelineIO: timeline primitives (RationalTime, TimeRange, TimeTransform), containers (Timeline/Stack/Track), content (Clip/Gap/Transition), MediaReferences, tutorials (quickstart, timeline-structure, time-ranges, write-a-schemadef-plugin, adapters), Python API (schema/core/opentime/algorithms/media_linker/hooks), adapter catalog (otio_json, otiod, otioz native; cmx_3600 EDL, fcp_xml, fcpx_xml, aaf_adapter, ale, burnins, maya_sequencer, xges, svg via OpenTimelineIO-Plugins). Use when the user asks to look up an OTIO class, find an adapter for a NLE format, verify Python bindings, or read OpenTimelineIO docs.
argument-hint: "[query]"
---

# OTIO Docs

**Context:** $ARGUMENTS

## Quick start

- **Find an OTIO class / function / adapter:** → Step 2 (`search --query <term>`)
- **Read the full API section:** → Step 3 (`section --page <page> --id <anchor>`)
- **Grab a whole tutorial / API page:** → Step 4 (`fetch --page <name>`)
- **Prime cache for offline use:** → Step 5 (`index`)

## When to use

- User asks "what does `otio.schema.Clip` take?" or "how do I subclass Track?"
- Need to confirm an adapter exists (EDL, FCP7-XML, FCPXML, AAF, ALE, XGES, SVG) before recommending.
- Need the `otioconvert` / `otiotool` / `otiostat` CLI surface (CLIs are documented via `--help`, not readthedocs — this skill pulls the tutorials + Python-API pages instead).
- Need to cite the canonical readthedocs URL or GitHub source of truth.
- Before writing OTIO Python code: verify API surface (classes, methods, serialization fields).

---

## Step 1 — Know the page catalog

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py list-pages
```

Common picks:

| Question | Page |
|---|---|
| "How do I read/write OTIO from Python?" | `tut-quickstart` |
| "What's Stack vs Track vs Timeline?" | `tut-timeline-structure` |
| "How do RationalTime and TimeRange work?" | `tut-time-ranges` |
| "Which adapters ship natively vs via OpenTimelineIO-Plugins?" | `tut-adapters` |
| "How do I author a custom schema?" | `tut-schemadef` |
| "Python API reference root" | `api-py-root` |
| "opentime module (RationalTime/TimeRange)" | `api-opentime` |
| "core module (SerializableObject, SerializableCollection)" | `api-core` |
| "schema module (Timeline/Clip/Gap/Track/Stack)" | `api-schema` |
| "algorithms module (stack_algo, track_algo, timeline_postprocess)" | `api-algorithms` |
| "media_linker module" | `api-media-linker` |
| "hooks module" | `api-hooks` |
| "README / repo root" | `github-readme` |
| "OpenTimelineIO-Plugins meta-package (community adapters)" | `plugins-readme` |

Read [`references/adapters.md`](references/adapters.md) for the full adapter matrix + [`references/pages.md`](references/pages.md) for the URL catalog.

---

## Step 2 — Search first

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py search --query "RationalTime" --limit 5
```

Scoped to one page:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py search --query "fcpx_xml" --page tut-adapters
```

Use `--format json` for machine-parseable output.

First run downloads; subsequent hit `~/.cache/otio-docs/`.

---

## Step 3 — Read one section in full

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py section --page api-schema --id opentimelineio.schema.Clip
```

`--id` accepts a Sphinx anchor id OR a heading keyword fallback.

---

## Step 4 — Fetch a whole page

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py fetch --page tut-adapters
```

Pair with `--format json` for structured output.

---

## Step 5 — Prime the cache

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py index
```

Fetches every known page into `~/.cache/otio-docs/`. Override with `OTIO_DOCS_CACHE=/path`.

Clear: `uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py clear-cache`.

---

## Gotchas

- **Canonical repo moved from PixarAnimationStudios to AcademySoftwareFoundation.** The GitHub URL `github.com/AcademySoftwareFoundation/OpenTimelineIO` is the source of truth — OTIO is now an ASWF project. Old `PixarAnimationStudios/OpenTimelineIO` URLs redirect but are stale; don't cache/cite them.
- **CLIs do NOT have readthedocs pages.** `otioconvert --help`, `otiocat --help`, `otiostat --help`, `otiotool --help`, and `otiopluginfo --help` are the authoritative CLI reference. This skill pulls the Python tutorials + API docs that ground the CLI behavior; for CLI flags run the tools with `--help`.
- **Native vs community adapters:**
  - **Native (shipped with `opentimelineio` core pip package):** `otio_json` (.otio), `otiod` (directory form), `otioz` (zipped form with media).
  - **Community (installed via `pip install OpenTimelineIO-Plugins` meta-package):** `cmx_3600` (EDL), `fcp_xml` (FCP7/Premiere XML), `fcpx_xml` (FCPXML), `aaf_adapter` (Avid), `ale` (Avid Log Exchange), `burnins` (render timecode burn-in), `maya_sequencer`, `xges` (GStreamer Editing Services), `svg` (render timeline to SVG).
  - Installing `OpenTimelineIO-Plugins` auto-installs `opentimelineio` core. Don't pip-install `opentimelineio` and then expect AAF/EDL/FCPXML to work — you need the meta-package.
- **`RationalTime` is rate-aware, not just a float.** `RationalTime(value=24, rate=24.0)` = 1 second. Do NOT convert to seconds prematurely — do all arithmetic in the native rate to avoid rounding drift. Use `rescaled_to(new_rate)` when changing.
- **`TimeRange` uses start + duration, NOT start + end.** `end_time_exclusive()` and `end_time_inclusive()` compute end on demand. Mixing these up off-by-ones every timeline.
- **Track kind is case-sensitive: `"Video"` or `"Audio"`.** Not `"video"` / `"audio"`. Lowercase is a common source of "no clips found" bugs.
- **`Clip.media_reference` can be `MissingReference` — not `None`.** Check `isinstance(clip.media_reference, opentimelineio.schema.MissingReference)` before treating as loaded.
- **Sphinx anchors for Python API use `moduleName.ClassName` form** (dotted path). Not the mangled C++ form you'd see in C++ Doxygen.
- **AAF adapter requires `pyaaf2`** (a non-PyPI-resolved dep on some systems). If `pip install OpenTimelineIO-Plugins` fails on AAF only, install `pyaaf2` first.
- **Round-trips lose data.** FCP7-XML → OTIO → FCPXML preserves structure, NOT every effect/generator. Adapter docs enumerate exactly what round-trips cleanly.
- **`.otio` is the canonical lossless format.** When in doubt, convert to `.otio` first; all other adapters lose detail.
- **Cache is per-page only, not per-OTIO-version.** After a new OTIO release, `clear-cache` then `index`.
- **The script is stdlib-only.** No pip dependencies.

---

## Examples

### Example 1 — "What does `opentimelineio.schema.Clip` take?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py search --query "class Clip" --page api-schema --limit 3
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py section --page api-schema --id opentimelineio.schema.Clip
```

### Example 2 — "Is there an AAF adapter?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py search --query "AAF" --page tut-adapters --limit 5
```

### Example 3 — "How do RationalTime arithmetic and rate conversion work?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py fetch --page tut-time-ranges
```

### Example 4 — "How do I write a custom schema plugin?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py fetch --page tut-schemadef
```

### Example 5 — "Where do OTIO algorithms like `track_trimmed_to_range` live?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otiodocs.py search --query "track_trimmed" --page api-algorithms
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** Not in the catalog.
**Solution:** Run `list-pages` — common mistakes: `schema` instead of `api-schema`; `adapters` instead of `tut-adapters`.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** macOS Python without certs.
**Solution:** `/Applications/Python\ 3.x/Install\ Certificates.command` or set `SSL_CERT_FILE`.

### Search returns zero hits for a class name

**Cause:** Class is in a different module than expected — e.g. `Clip` is in `schema`, `RationalTime` is in `opentime`, `track_trimmed_to_range` is in `algorithms`.
**Solution:** Drop `--page` to search all pages.

### Cache stale after OTIO release

**Solution:** `clear-cache` then `index`.

---

## Reference docs

- Adapter matrix (native vs community, round-trip fidelity, install steps) → `references/adapters.md`
- URL catalog + page descriptions → `references/pages.md`
