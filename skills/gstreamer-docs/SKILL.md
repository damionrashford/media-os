---
name: gstreamer-docs
description: >
  Search and fetch official GStreamer documentation from gstreamer.freedesktop.org: application-development, tutorials, plugin-development, tools (gst-launch-1.0, gst-inspect-1.0, gst-device-monitor-1.0, gst-discoverer-1.0, gst-play-1.0, gst-typefind-1.0), libraries (core gstreamer, base, video, audio, rtp, webrtc, sdp, pbutils, app, coreelements, coretracers, libav). Use when the user asks to look up a GStreamer element, find an element's properties or pads, check caps negotiation rules, search GStreamer docs, verify a gst-launch pipeline, look up the gstreamer webrtcbin or hlssink API, or verify a GStreamer call against the real docs.
argument-hint: "[query]"
---

# GStreamer Docs

**Context:** $ARGUMENTS

## Quick start

- **Find an element / property / signal:** -> Step 2 (`search --query <term>`)
- **Read the full docs for one element:** -> Step 3 (`element --name <name>`)
- **Read one section by anchor:** -> Step 4 (`section --page <page> --id <anchor>`)
- **Grab a whole page:** -> Step 5 (`fetch --page <name>`)
- **Prime cache for offline use:** -> Step 6 (`index`)

## When to use

- User asks "what does element `X` do?" or "what properties does `webrtcbin` expose?"
- Need to verify an element name, property, pad, or signal exists before recommending it.
- Need the canonical gstreamer.freedesktop.org URL to cite in a response.
- Before writing any non-trivial gst-launch-1.0 pipeline, verify the element and its caps/properties.
- Need to know which plugin package an element ships in.

---

## Step 1 — Know the page catalog

The script targets a fixed list of plugin-index pages + top-level guides. Get the list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py list-pages
```

Common picks:

| Question | Page |
|---|---|
| "What does filesrc / queue / tee / capsfilter do?" | `coreelements` |
| "How do I use playbin3 / decodebin3 / uridecodebin3?" | `playback` |
| "RTSP client / server elements?" | `rtsp`, `rtspserver` |
| "HLS / DASH muxing / sinks?" | `hls`, `dash` |
| "WebRTC — webrtcbin (C) vs webrtcsink (Rust)?" | `webrtc`, `rswebrtc` |
| "SRT source / sink?" | `srt` |
| "x264enc / x265enc / VP9 options?" | `x264`, `x265`, `vpx` |
| "NVENC / NVDEC in GStreamer?" | `nvcodec` |
| "MP4 / QuickTime mux / demux?" | `isomp4` |
| "Matroska / WebM mux?" | `matroska` |
| "V4L2 webcam?" | `v4l2` |
| "OpenGL elements?" | `opengl` |
| "gst-launch-1.0 syntax rules?" | `gst-launch` |
| "gst-inspect-1.0 output fields?" | `gst-inspect` |
| "Core GObject API / GstElement / GstPad / GstCaps?" | `gstreamer` |
| "Base classes for writing elements (GstBaseSrc etc.)?" | `base` |

Read [`references/pages.md`](references/pages.md) for the full catalog.

---

## Step 2 — Search first (this is the default)

When the user names an element, property, pad, or signal, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "webrtcbin" --limit 5
```

Scope to a page when you know it (faster, less noise):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "animation-mode" --page videotestsrc
```

Output per hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with anchor>
<snippet with ±3 lines of context>
```

`--format json` for machine-parseable output; `--regex` for anchored patterns.

---

## Step 3 — Read one element's docs

When you know the element name (e.g. `filesrc`, `playbin3`, `webrtcbin`):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py element --name filesrc
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py element --name webrtcbin --format json
```

The script resolves element pages automatically across the two URL shapes GStreamer uses:

- **Multi-element plugin**: `/<plugin>/<element>.html` (e.g. `/coreelements/filesrc.html`, `/playback/playbin3.html`, `/rtsp/rtspsrc.html`, `/hls/hlssink2.html`, `/srt/srtsrc.html`, `/rswebrtc/webrtcsink.html`).
- **Singleton plugin**: `/<element>/index.html` (e.g. `/videotestsrc/index.html`, `/audiotestsrc/index.html`, `/webrtclib/index.html`, `/x264/index.html`).

You can also debug which shape was picked:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py resolve --element webrtcbin
```

---

## Step 4 — Read one section

When a search hit shows an anchor like `[§videotestsrc:animation-mode]` and you want the whole block:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py section --page videotestsrc --id "videotestsrc:animation-mode"
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py section --element webrtcbin --id ice-agent
```

`--id` accepts a raw anchor id or a heading keyword (case-insensitive substring match on the first matching heading).

---

## Step 5 — Fetch a whole page

Rare — usually overkill. When you need it:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py fetch --page coreelements
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py fetch --element playbin3 --format json
```

---

## Step 6 — Prime cache (optional)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py index
```

Downloads every known landing page into `~/.cache/gstreamer-docs/` with a 0.3s delay.

Override the cache directory with `export GSTREAMER_DOCS_CACHE=/path/to/dir`.
Clear: `gstdocs.py clear-cache`.

---

## Gotchas

- **Bare `/<element>.html` is universally 404.** Elements live under a plugin dir — `/coreelements/filesrc.html`, not `/filesrc.html`. The `element` subcommand handles this for you; never construct the URL yourself.
- **Two element-page shapes exist.** Multi-element plugin: `/<plugin>/<element>.html`. Singleton plugin: `/<element>/index.html`. `resolve --element` tells you which shape was picked.
- **Anchor syntax is Hotdoc-specific.** You'll see three flavours inside page text: `#<element>` (the element landing block), `#<element>:<property>` with a literal colon (e.g. `#videotestsrc:animation-mode`), and `#Gst<CamelCase>!<pad>` (e.g. `#GstVideoTestSrc!src` for the `src` pad). Pass the form you see in search output verbatim to `section --id`.
- **webrtcbin vs webrtcsink are distinct.** `webrtcbin` is the low-level C element in plugin `webrtc` — you handle SDP + ICE yourself. `webrtcsink` / `webrtcsrc` are the high-level Rust elements in plugin `rswebrtc` that speak WHIP/WHEP and negotiate automatically. Don't mix their properties.
- **playbin vs playbin3.** `playbin` is the legacy high-level player. `playbin3` is the current one — different signals, different bus messages, different stream-selection API. Check which one you're actually using.
- **decodebin3 / urisourcebin stream-selection is different from decodebin/uridecodebin.** Events are `GST_EVENT_SELECT_STREAMS` + `GST_MESSAGE_STREAM_COLLECTION` rather than the old `autoplug-*` signals. Don't port old code verbatim.
- **`gst-inspect-1.0 <element>` is authoritative for local builds.** If the online docs don't match what your installed GStreamer exposes, the CLI is right — some plugins are rolled from different upstreams (gst-plugins-good vs bad vs ugly vs rs) and versions diverge.
- **Docs are Hotdoc-generated, NOT Sphinx.** Don't assume Sphinx conventions like `:py:class:` or `_CPPv4N...` — GStreamer anchors are flatter (`element`, `element:property`, `GstType!pad`).
- **Plugin packages: good/bad/ugly/base/rs.** "bad" means "not yet up to par", NOT "buggy". Many widely-used elements (`webrtcbin`, `hlssink2`, `srtsink`) live in `gst-plugins-bad` or `gst-plugins-rs`. If `gst-inspect-1.0 foo` comes up empty, you probably haven't installed the plugin-set it ships in.
- **Rust plugins (`gst-plugins-rs`) ship separately.** `webrtcsink`, `awstranscriber`, `fallbackswitch`, etc. are Rust — check `rswebrtc` and related index pages, not the C plugin pages.
- **Search may miss content in complex tables.** The text extractor flattens multi-column property tables. If a search hit looks incomplete, open the canonical URL printed in the hit header.
- **Cache never expires automatically.** After a GStreamer release reshuffles plugins, run `clear-cache` + `index`.
- **The script is stdlib-only** — no pip install. Works anywhere Python 3.9+ runs.

---

## Examples

### Example 1 — "What properties does webrtcbin expose?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py element --name webrtcbin
```

Or search + jump:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "webrtcbin" --page webrtc --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py section --element webrtcbin --id "webrtcbin:stun-server"
```

### Example 2 — "Does hlssink2 support fMP4 / CMAF?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "hlssink2" --page hls
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py element --name hlssink2
```

### Example 3 — "What's the gst-launch-1.0 syntax for named elements and caps filters?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "pipeline description" --page gst-launch
```

### Example 4 — "What does `videotestsrc animation-mode=frames` actually do?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py section --page videotestsrc --id "videotestsrc:animation-mode"
```

### Example 5 — "Which plugin provides rtspclientsink?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py resolve --element rtspclientsink
```

(Prints URL + shape. URL's first path segment is the plugin.)

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** The name isn't in the catalog.
**Solution:** Run `list-pages`. Common mistakes: using `elements` instead of `coreelements`; `rtspsrc` (an element) instead of `rtsp` (the plugin).

### Error: `could not resolve element <name>`

**Cause:** The element isn't in `ELEMENT_HINTS`, the singleton-plugin guess failed, and no known plugin landing page linked to it.
**Solution:** Run `gst-inspect-1.0 <name>` to confirm the element exists and see its plugin. Then `search --query "<name>"` across the whole catalog to find the right plugin page. If it's a Rust plugin not in our list yet, the element lives at `/<plugin>/<name>.html` under `gst-plugins-rs` — fetch the URL directly with `urllib` until the catalog is updated.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** System certificate store is out of date (usually macOS Python).
**Solution:** Run `/Applications/Python\ 3.x/Install\ Certificates.command`, or set `SSL_CERT_FILE` to a valid CA bundle. Do NOT disable SSL verification.

### Search returns zero hits

**Cause:** The term isn't on the pages you queried.
**Solution:** Drop `--page` to search everything; try a broader query. Some APIs are in the base-class pages (`base`, `gstreamer`) rather than the element page.

### Anchor not found with `section --id`

**Cause:** Hotdoc anchors include colons and `!` which copy-paste fine but may confuse shells. Quote them.
**Solution:** `--id "videotestsrc:animation-mode"` with quotes, or fall back to a heading keyword: `--id animation-mode`.

### Cache is stale after GStreamer upstream release

**Solution:** `gstdocs.py clear-cache` then `gstdocs.py index`.

---

## Reference docs

- Full page catalog with element-to-plugin hints and anchor-syntax details -> [`references/pages.md`](references/pages.md)
