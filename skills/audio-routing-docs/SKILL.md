---
name: audio-routing-docs
description: >
  Search and fetch docs for system-level audio routing subsystems (lives BELOW ffmpeg): PipeWire (docs.pipewire.org — pw-cli, pw-dump, pw-link, pw-cat, pw-top, pw-loopback, WirePlumber session manager, PA+JACK compat), JACK Audio Connection Kit (jackaudio.org, jackd/jack_lsp/jack_connect, JACK1 vs JACK2, JackTrip for network audio), Apple Core Audio (developer.apple.com archive — HAL plugins, Aggregate/Multi-Output devices, BlackHole virtual driver), Windows WASAPI (learn.microsoft.com — exclusive vs shared mode, MMDevice, Audio Engine, WDM/KS stack, VB-Cable, VoiceMeeter). Use when the user asks to look up a PipeWire/JACK/CoreAudio/WASAPI API, verify a system audio routing command, check virtual audio driver setup, or find subsystem docs.
argument-hint: "[query]"
---

# Audio Routing Docs

**Context:** $ARGUMENTS

## Quick start

- **Find a command / API:** → Step 2 (`search --query <term>`)
- **Read the full section for one command:** → Step 3 (`section --page <name> --id <anchor>`)
- **Grab an entire doc page:** → Step 4 (`fetch --page <name>`)
- **Prime the cache for offline use:** → Step 5 (`index`)
- **List all known pages grouped by host:** → Step 1 (`list-pages`)

## When to use

- User asks "what does `pw-link` / `jack_connect` / `SwitchAudioSource` / `svcl.exe` do?"
- Need to verify a subsystem CLI flag before recommending it (anti-hallucination guard).
- Need the canonical URL for a PipeWire man page, JACK API doc, Apple Core Audio archive
  page, or Microsoft WASAPI concept page.
- About to write instructions involving virtual drivers (BlackHole, VB-Cable, VoiceMeeter)
  and want the real install/config page, not a guess.

This skill is **docs only**. For actual capability (running `pw-link`, installing
BlackHole, flipping Windows default output), use the sibling skills:
`audio-pipewire`, `audio-jack`, `audio-coreaudio`, `audio-wasapi`.

---

## Step 1 — Know the page catalog

The script works only against a curated list of pages across four hosts:
`docs.pipewire.org`, `jackaudio.org`, `developer.apple.com`, `learn.microsoft.com`.
Get the current list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py list-pages
```

Common picks by question:

| Question | Page |
|---|---|
| "What does `pw-link` accept?" | `pipewire-man-pw-link` |
| "How do I dump the PipeWire graph?" | `pipewire-man-pw-dump` |
| "Where are PipeWire CLIs listed?" | `pipewire-programs` |
| "WirePlumber session manager?" | `wireplumber-home` |
| "What is `jack_lsp`?" | `jack-api` or `jack-stanford` |
| "JackTrip over the internet?" | `jacktrip-docs`, `jacktrip-github` |
| "What is Core Audio / the HAL?" | `coreaudio-overview`, `coreaudio-essentials` |
| "SwitchAudioSource flags?" | `switchaudio-osx` |
| "BlackHole install?" | `blackhole-github` |
| "WASAPI exclusive vs shared?" | `wasapi-exclusive`, `wasapi-overview` |
| "NirSoft svcl.exe flags?" | `wasapi-svcl` |
| "AudioDeviceCmdlets PowerShell?" | `wasapi-audiodevicecmdlets` |
| "VB-Cable / VoiceMeeter install?" | `wasapi-vbcable`, `wasapi-voicemeeter` |

Read [`references/pages.md`](references/pages.md) when you need the full catalog
with one-line descriptions per page.

---

## Step 2 — Search first (default)

When the user names a command, API, or concept, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search --query "pw-link" --limit 5
```

Scope to one subsystem when you know where it lives (faster, less noise):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search \
  --query "exclusive mode" --page wasapi-exclusive
```

Output for each hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with #anchor if available>
<snippet with ±3 lines of context>
```

Pass `--format json` for machine-parseable output when chaining.

First run downloads the page (~1–2s). Subsequent runs hit the local cache
(`~/.cache/audio-routing-docs/`) instantly.

---

## Step 3 — Read one section in full

When a search hit points to a specific command/API and you want the full block
(option list + description), use `section`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py section \
  --page pipewire-man-pw-link --id SYNOPSIS
```

`--id` accepts either:

- An anchor id printed in search results as `[§xxxx]`.
- A heading keyword — the script falls back to the first heading matching the string
  (case-insensitive).

Output runs from the matching heading down to the next same-or-higher-level heading.

---

## Step 4 — Fetch a whole page

Only when you need to dump the whole page (rare — `search` + `section` are almost
always better):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py fetch --page pipewire-programs
```

Pair with `--format json` for structured handoff.

---

## Step 5 — Prime the cache (optional)

For reliable offline lookups or before a burst of queries:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py index
```

Fetches every known page and stores text-extracted versions in
`~/.cache/audio-routing-docs/`. Override the cache directory with
`AUDIO_ROUTING_DOCS_CACHE=/path/to/dir`.

Clear the cache when upstream docs change:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py clear-cache
```

---

## Gotchas

- **Never recommend a PipeWire/JACK/CoreAudio/WASAPI flag without searching first.**
  This skill exists precisely to prevent hallucinated flags. Zero search hits means
  the flag is not in that subsystem's official docs — do not claim it works.
- **PipeWire replaced `pipewire-media-session` with WirePlumber.** Old docs and blog
  posts still mention `pipewire-media-session`; it is deprecated. Route session-manager
  questions to `wireplumber-home`, not the legacy config files.
- **JACK1 vs JACK2 are both "jackd" but behave differently.** JACK1 is C, single-core,
  maintenance mode. JACK2 is C++, multicore, adds `jack_control` via D-Bus. On modern
  Linux desktops the binary that answers `jackd` is usually PipeWire's libjack shim,
  not a real jackd — period size and backends come from PipeWire/WirePlumber, not JACK.
- **Apple's Core Audio docs live at `developer.apple.com/library/archive/...`** —
  those are the canonical conceptual docs. The modern path `developer.apple.com/documentation/coreaudio`
  covers Swift/Objective-C API references but the archive covers concepts (HAL, Aggregate
  Device, AU graph) more fully. Link to the archive for concept questions.
- **BlackHole and Loopback are Apple-Silicon-compatible DriverKit / AudioDriverKit drivers.**
  Soundflower is abandoned and won't load on modern macOS — do not recommend it. Route to
  `blackhole-github` for installs.
- **WASAPI has no first-party Microsoft CLI.** Everything CLI-shaped (SoundVolumeView,
  svcl.exe, AudioDeviceCmdlets, nircmd) is third-party. The Microsoft docs (`wasapi-*`
  pages) describe the C/C++ API surface; they do not document the NirSoft/GitHub CLIs.
  Cross-check each by searching its own page.
- **Exclusive mode in WASAPI is the bit-perfect path.** Sub-3ms latency needs
  `AUDCLNT_STREAMFLAGS_EVENTCALLBACK` + `IAudioClient3::InitializeSharedAudioStream`.
  Search on `wasapi-exclusive` and `wasapi-device-formats` for the trade-offs.
- **`audiodevice` is ambiguous on macOS** — at least two tools share the name (npm
  package and a Go binary). Always cite the exact upstream repo when recommending it,
  or prefer `SwitchAudioSource` (brew install `switchaudio-osx`) which is unambiguous.
- **Cache is keyed by page name only.** Upstream doc edits (new PipeWire release,
  new Microsoft revision) are not detected automatically. `clear-cache` + `index`
  when you suspect staleness.
- **Anchors in search results use the `[§anchor-id]` sentinel.** Drop the `[§` / `]`
  brackets when passing to `section --id`.
- **Text extraction is lossy for complex tables.** If a hit looks truncated, open the
  URL printed in the hit header directly for the authoritative view.
- **`learn.microsoft.com` pages include large chrome (nav, breadcrumbs) that the script
  strips.** If a search hit has no obvious snippet, the term was in the boilerplate;
  try a more specific query or `fetch` the whole page.

---

## Examples

### Example 1 — "What does `pw-link` actually let me do?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search --query "pw-link" --limit 3
```

Pick the hit on `pipewire-man-pw-link`, then read the synopsis:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py section \
  --page pipewire-man-pw-link --id SYNOPSIS
```

### Example 2 — "What's the difference between JACK exclusive & shared audio on Windows?"

Wrong subsystem — WASAPI has exclusive/shared; JACK does not. Fetch the canonical
doc:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py fetch --page wasapi-exclusive
```

### Example 3 — "What are the CLI flags for `svcl.exe`?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search \
  --query "SetDefault" --page wasapi-svcl --limit 5
```

(NirSoft's command-line reference lives on `wasapi-svcl`.)

### Example 4 — "Does macOS still support Soundflower?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search \
  --query "Soundflower" --limit 3
```

Expected result: nothing authoritative — Soundflower is abandoned. Recommend
BlackHole instead; fetch `blackhole-github`.

### Example 5 — "Find the JackTrip server flags."

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/audiodocs.py search \
  --query "server" --page jacktrip-docs --limit 5
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** The page name isn't in the catalog.
**Fix:** Run `list-pages` to see valid names. Common mistakes: `pipewire` instead of
`pipewire-home`; `jack` instead of `jack-home`; `coreaudio` instead of `coreaudio-overview`.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** System certificate store is out of date (typically macOS with older Python).
**Fix:** Install/update certifi, or run `/Applications/Python\ 3.x/Install\ Certificates.command`.
Do NOT patch the script to disable SSL verification.

### Search returns zero hits

**Cause:** Term isn't on that page, or wrong subsystem.
**Fix:** Drop `--page` to search everywhere; try the sibling subsystem (`wasapi-*`
for Windows, `pipewire-*` for Linux, etc.); try a broader query.

### Results look truncated / tables mangled

**Cause:** Lossy HTML→text extraction on complex tables.
**Fix:** Open the canonical URL printed in the hit header (WebFetch or browser).

### Cache is stale after a subsystem upstream update

**Fix:** `clear-cache` then `index` (or just `fetch --no-cache --page <name>` for one).

---

## Reference docs

- Full annotated page catalog (host-by-host, with what each page covers) →
  [`references/pages.md`](references/pages.md).
