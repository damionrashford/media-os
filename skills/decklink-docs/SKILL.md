---
name: decklink-docs
description: >
  Look up Blackmagic DeckLink SDK docs at blackmagicdesign.com/developer: DeckLink C++ / COM-style API (DeckLinkAPI.h, DeckLinkAPI.idl), Desktop Video SDK (driver + runtime), DeckLink Arduino SDK. Core interfaces: IDeckLink, IDeckLinkInput, IDeckLinkOutput, IDeckLinkDisplayMode, IDeckLinkConfiguration, IDeckLinkNotification, IDeckLinkProfileAttributes. BMDPixelFormat (8BitYUV/10BitYUV/ARGB/BGRA/10BitRGB/r210/v210), BMDDisplayMode (SD/HD/2K/UHD/4K/8K). Relationship to ffmpeg decklink demuxer/muxer. Use when the user asks to look up a DeckLink API, check supported pixel formats or display modes, verify an IDeckLinkInput or IDeckLinkOutput method, or find Blackmagic SDK documentation.
argument-hint: "[query]"
---

# Decklink Docs

**Context:** $ARGUMENTS

## Quick start

- **Find an API / interface / BMD enum:** → Step 2 (`search --query <term>`)
- **Read one full section:** → Step 3 (`section --page <name> --id <anchor>`)
- **Grab the whole page:** → Step 4 (`fetch --page <name>`)
- **Prime the cache offline:** → Step 5 (`index`)
- **Verify the ffmpeg `decklink` device options:** → search on page `ffmpeg-devices`

## When to use

- User asks "what does `IDeckLinkInput::StartStreams` return?" or "what pixel formats does a Mini Recorder accept?"
- Need to verify an interface / method / enum exists before recommending C++ / COM code.
- Need the exact ffmpeg `-f decklink` option list (the ffmpeg decklink demuxer / muxer docs).
- Need to cite the canonical Blackmagic SDK URL in a response.
- Before writing any non-trivial DeckLink integration, check the current doc for the interface you're using.

---

## Step 1 — Know the page catalog

The script only works against a fixed list of known Blackmagic / related doc pages. Get the list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py list-pages
```

The catalog groups into four areas:

| Page family | What's covered |
|---|---|
| `blackmagic-developer` / `blackmagic-capture-playback` | Landing pages. The SDK ZIP is login-gated; URLs are catalog stubs. |
| `ffmpeg-devices-decklink` / `ffmpeg-devices` | The ffmpeg decklink demuxer + muxer (options, examples). |
| `decklink-sdk-readme-*` | Third-party mirrors of SDK sample names + API index (informational only). |
| `bmdtools-github` | Third-party `bmdtools` (the tool that ships `bmdcapture` / `bmdplay`). |

Read [`references/catalog.md`](references/catalog.md) for the full page list with descriptions and login-gated notes.

---

## Step 2 — Search first (default workflow)

When the user names an interface, enum, method, or option, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py search --query "IDeckLinkInput" --limit 5
```

Scope to a page for less noise:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py search --query "list_formats" --page ffmpeg-devices-decklink
```

Output format per hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with anchor>
<snippet with ±3 lines of context>
```

First run downloads the page (~1–2s). Subsequent runs hit the local cache (`~/.cache/decklink-docs/`) — instant.

Use `--format json` for machine-parseable output when chaining.

---

## Step 3 — Read one section in full

When a search hit lands on an interface / option and you want the whole block:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py section --page ffmpeg-devices-decklink --id decklink
```

`--id` accepts either the anchor id printed in search results as `[§xxxx]` or a heading keyword.

---

## Step 4 — Fetch a whole page

Rarely needed — usually overkill. Use when you need the entire page text:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py fetch --page ffmpeg-devices-decklink
```

Pair with `--format json` for structured handoff.

---

## Step 5 — Prime the cache (optional)

For reliable offline lookups or before a burst of queries:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py index
```

Fetches every known page, stores text-extracted versions in `~/.cache/decklink-docs/`. Some Blackmagic developer pages may fail with 403 when unauthenticated — the script keeps going and reports failures.

Override cache location: `export DECKLINK_DOCS_CACHE=/path/to/dir`.
Clear: `uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py clear-cache`.

---

## Gotchas

- **The Blackmagic SDK download itself is login-gated.** `https://www.blackmagicdesign.com/developer/product/capture-and-playback` renders a product page only; the SDK ZIP with `DeckLinkAPI.h` / `DeckLinkAPI.idl` + `Samples/` tree requires free account + terms acceptance. The script catalogs these URLs but cannot fetch the SDK contents directly. Tell the user to register once.
- **`bmdcapture` / `BMDPlaybackSample` are NOT official SDK sample names.** `bmdcapture` ships with third-party `bmdtools` (github.com/lu-zero/bmdtools). The actual official SDK `Samples/` are: `CapturePreview`, `LoopThroughPreview`, `SignalGenerator`, `StatusMonitor`, `DeviceList`, `TestPattern`, `3DVideoFrames`, `StreamOperations`, `FrameServer`, `AudioMixer`.
- **The DeckLink API is COM-style on all platforms**, not just Windows. Use `CreateDeckLinkIteratorInstance()` on macOS/Linux — the SDK includes a cross-platform shim so `QueryInterface` / `AddRef` / `Release` work the same way.
- **Release order matters.** COM-style reference counting: every interface obtained via `QueryInterface` must be `Release()`-d. Leaking an `IDeckLinkDisplayMode` across frames crashes the driver.
- **ffmpeg must be built `--enable-decklink`** and the runtime driver (`libDeckLinkAPI.so` / `DeckLinkAPI.dll` / `DeckLinkAPI.dylib` in `/Library/Frameworks`) must be installed. Missing either produces `Unknown input format: 'decklink'`.
- **Pixel format mapping from SDK → ffmpeg:** `bmdFormat8BitYUV` = `uyvy422`, `bmdFormat10BitYUV` = `v210`, `bmdFormat10BitRGB` = `r210`, `bmdFormat8BitARGB` = `argb`, `bmdFormat8BitBGRA` = `bgra`. Never mix SDK enum names with ffmpeg pixel-format names.
- **Display-mode selection is a BMDDisplayMode four-CC** (e.g. `'Hp60'` = 1080p60, `'2k24'` = 2K 24p). The ffmpeg `-format_code` decklink option accepts these same four-CCs as strings. See `ffmpeg-devices-decklink` page.
- **10-bit YUV (`v210`) requires width divisible by 48** because of its packed 3-pixel/4-word layout. Not 16, not 32 — 48. Any other width needs scaling before the DeckLink output.
- **Search is case-insensitive; C++ identifiers are case-sensitive.** The query will match regardless, but when you cite an interface in your answer use the exact case (`IDeckLinkInput`, not `idecklinkinput`).
- **The script is stdlib-only.** No pip install.
- **One-shot queries can skip `index`.** The script fetches lazily on first use.

---

## Examples

### Example 1 — "What options does ffmpeg's decklink demuxer take?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py section --page ffmpeg-devices-decklink --id decklink
```

### Example 2 — "Which BMDPixelFormat values exist?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py search --query "BMDPixelFormat" --limit 5
```

### Example 3 — "What's the official SDK sample for a preview window?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py search --query "CapturePreview" --limit 5
```

(Correct answer: `Samples/CapturePreview/` — not `bmdcapture`. See Gotchas.)

### Example 4 — "How do I list DeckLink devices from ffmpeg?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/decklinkdocs.py search --query "list_devices" --page ffmpeg-devices-decklink
```

Cite the command: `ffmpeg -f decklink -list_devices 1 -i dummy`.

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** Name isn't in the catalog.
**Solution:** `list-pages` to see valid names.

### Error: `HTTPError: 403` when fetching a Blackmagic dev URL

**Cause:** That page is behind the developer login wall.
**Solution:** Use the general landing / ffmpeg-side pages; register a free Blackmagic developer account to download the actual SDK ZIP.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** System cert store out of date.
**Solution:** Update certifi or run Python's `Install Certificates.command`. Do NOT disable SSL verification.

### Search returns zero hits

**Cause:** Term doesn't exist on the catalog's pages (most SDK internals are inside the login-gated ZIP, not on the web).
**Solution:** Drop `--page` to search all; if still empty, the term lives in the SDK header files and requires downloading the SDK.

### Results look truncated

**Cause:** HTML → text extraction flattens tables.
**Solution:** Open the canonical URL printed in the hit header for the authoritative view.
