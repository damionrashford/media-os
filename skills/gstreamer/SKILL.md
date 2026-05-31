---
name: gstreamer
description: >
  Use when the user asks to build or run a GStreamer pipeline, construct a gst-launch-1.0 command, do real-time video processing with GStreamer, pipe ffmpeg output into GStreamer, build an embedded or Linux media pipeline, use webrtcbin or webrtcsink, stream RTSP or HLS or DASH or SRT via GStreamer, segment HLS with hlssink2, author a plugin-graph pipeline, introspect an element with gst-inspect-1.0, discover media with gst-discoverer-1.0, enumerate cameras or mics with gst-device-monitor-1.0, play a file with gst-play-1.0, or detect type with gst-typefind-1.0. Also use to look up GStreamer docs from gstreamer.freedesktop.org, search for an element or its properties, pads, signals, or caps, check caps negotiation rules, find which plugin package an element ships in (good, bad, ugly, base, rs), or verify a GStreamer element, call, or pipeline against the real docs before recommending it.
argument-hint: "[pipeline-or-query]"
---

# GStreamer

**Context:** $ARGUMENTS

Build/run GStreamer pipelines AND verify elements against the official docs. Two helpers live under `scripts/`: `gst.py` (run the local toolchain) and `gstdocs.py` (search gstreamer.freedesktop.org).

## When to use

- User wants a running pipeline: "play this", "transcode", "publish RTSP/WHIP", "receive WebRTC".
- User wants a `gst-launch-1.0` one-liner before coding the C / Rust / Python client.
- User wants to introspect an element, probe a file, or enumerate cameras/mics/screens.
- User asks what an element does, what properties/pads/signals it has, or which plugin ships it.
- Before recommending ANY element, property, or caps — verify it exists in the docs.

## Docs lookup (do this FIRST)

Anti-hallucination guardrail. Before you name an element, property, pad, signal, or caps in a pipeline or answer, verify it against the real docs:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py search --query "webrtcbin" --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py element --name hlssink2
```

Read `references/docs-search.md` for the full lookup workflow (search, element, section, fetch, index subcommands; anchor syntax; element-page resolution). The page catalog with element-to-plugin hints is in `references/pages.md`.

## Techniques

Read `references/pipeline.md` when the user needs to run a pipeline, introspect locally with `gst.py`, probe devices/media, or grab a recipe. It documents every `gst.py` subcommand (`launch`, `inspect`, `discover`, `devices`, `typefind`, `play`, `list-elements`) with examples.

The copy-paste recipe book (15+ production pipelines: playback, transcode, RTP, MPEG-TS+FEC, RTSP, HLS, DASH, WebRTC, SRT, appsrc/appsink, NDI/DeckLink) is in `references/pipelines.md`. The element-resolver / page catalog for docs is in `references/pages.md`.

## Gotchas

- **All CLI tools carry the `-1.0` suffix.** `gst-inspect-1.0`, `gst-launch-1.0` — bare names usually don't exist (0.10 was EOL'd in 2012).
- **`!` is the link operator, NOT logical-NOT.** Quote the pipeline or pass it after `--` so the shell leaves it alone.
- **`queue` is mandatory between threads.** After any `tee` fan-out or subsystem crossing (audio↔video, CPU↔GPU), put a `queue` on each branch or the second branch starves.
- **`-e` / `--eos-on-shutdown` when writing to a muxer.** Without it, Ctrl-C kills the pipeline mid-write and `qtmux`/`mp4mux` never write the moov atom — output is 0 bytes / unseekable.
- **`webrtcbin` (C, plugin `webrtc`) vs `webrtcsink` (Rust, plugin `rswebrtc`).** `webrtcbin` is low-level — you drive SDP+ICE via signals. `webrtcsink` auto-negotiates and speaks WHIP/WHEP. Don't mix their properties.
- **"bad" means "not yet up to par", NOT buggy.** Many staples (`webrtcbin`, `hlssink2`, `srtsink`) live in `-bad`; Rust elements (`webrtcsink`, `whipclientsink`) need `gst-plugins-rs`. Empty `gst-inspect-1.0 foo` = missing plugin-set, not a typo.
- **Bare `/<element>.html` is universally 404 in the docs.** Elements live under a plugin dir (`/coreelements/filesrc.html`). Use the `element` subcommand — never hand-build the URL.
- **`gst-inspect-1.0 <element>` is authoritative for local builds.** If online docs disagree with the installed GStreamer, the CLI wins — plugins roll from different upstreams and versions diverge.

## Scripts

- `scripts/gst.py` — run the local toolchain: `launch | inspect | discover | devices | typefind | play | list-elements`. Each supports `--dry-run` / `--verbose`. See `references/pipeline.md`.
- `scripts/gstdocs.py` — search/fetch official docs: `search | element | section | fetch | resolve | list-pages | index | clear-cache`. See `references/docs-search.md`.
