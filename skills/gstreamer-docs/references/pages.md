# GStreamer Documentation Page Catalog

`scripts/gstdocs.py` fetches from a fixed list of pages at
`https://gstreamer.freedesktop.org/documentation/`. This file documents what
each page is, when to pick it, and how the element-resolver handles the two
distinct URL shapes.

---

## URL shapes

GStreamer's Hotdoc-generated site uses two URL shapes for element pages:

1. **Multi-element plugin** — plugin dir holds many elements, each at its own
   `.html` file.
   ```
   /coreelements/filesrc.html
   /coreelements/queue.html
   /playback/playbin3.html
   /playback/decodebin3.html
   /rtsp/rtspsrc.html
   /hls/hlssink2.html
   /srt/srtsrc.html
   /rswebrtc/webrtcsink.html
   /webrtc/webrtcbin.html
   ```

2. **Singleton plugin** — plugin dir holds exactly one element, and the
   element's docs live at `/<plugin>/index.html`.
   ```
   /videotestsrc/index.html
   /audiotestsrc/index.html
   /audiomixer/index.html
   /compositor/index.html
   /videoconvert/index.html
   /audioconvert/index.html
   /x264/index.html
   /x265/index.html
   ```

**Never** construct `/<element>.html` directly — bare-element URLs are
universally 404. The script's `resolve --element <name>` command tells you
which shape is in effect for a given element.

---

## Anchor syntax

Three flavours of anchor ID appear on element pages. Hotdoc emits them as
`#<id>` fragments; our text extractor surfaces them as `[§<id>]`.

| Anchor form | Example | Meaning |
|---|---|---|
| `<element>` | `#videotestsrc` | The element's top-level landing block |
| `<element>:<property>` | `#videotestsrc:animation-mode` | A property (note the colon) |
| `Gst<CamelCase>!<pad>` | `#GstVideoTestSrc!src` | A pad template |
| `<element>::<signal>` | `#webrtcbin::on-negotiation-needed` | A GObject signal |

When passing anchors to `section --id`, use the raw form without brackets, and
quote it if it contains shell-meaningful characters:

```bash
gstdocs.py section --page videotestsrc --id "videotestsrc:animation-mode"
gstdocs.py section --element webrtcbin  --id "webrtcbin::on-negotiation-needed"
```

---

## Page catalog — top-level guides

| Page | When to use |
|---|---|
| `index` | Site index — rarely useful directly; prefer a topic page. |
| `application-development` | Writing an app that embeds GStreamer via `GstElement` / `GstBus`. Covers Pipeline/Bin/Element/Pad/Caps/Bus/Clock concepts. |
| `tutorials` | Step-by-step tutorials (basic playback, bus messages, dynamic pipelines, etc.) with full C source. |
| `plugin-development` | Writing your own element (inheriting GstBaseSrc / GstBaseTransform / GstBaseSink), registering types, caps negotiation. |
| `deploying` | Shipping GStreamer apps (Linux / macOS / Windows / iOS / Android). |
| `installing` | Installing GStreamer dev packages per OS. |
| `frequently-asked-questions` | Common gotchas from the official FAQ. |
| `contribute` | Upstream contribution guide. |
| `additional` | Misc. reference docs. |

## CLI tools

| Page | When to use |
|---|---|
| `tools` | Index of every CLI shipped with GStreamer. |
| `gst-launch` | Full grammar for `gst-launch-1.0`: the `!` operator, caps filters, named elements + `.` refs, property syntax, queue insertion, signals. |
| `gst-inspect` | `gst-inspect-1.0` output fields (factory rank, author, description, pad templates, properties, signals). |

Other CLIs (not on their own pages, but documented within `tools/` and the core GstBin runtime):

- `gst-device-monitor-1.0` — list video/audio capture + output devices.
- `gst-discoverer-1.0` — probe a URI for streams, caps, duration, tags.
- `gst-play-1.0` — tiny CLI media player using playbin3.
- `gst-typefind-1.0` — typefind a file's MIME / caps.

## Core library indexes

| Page | When to use |
|---|---|
| `gstreamer` | Core GObject API: `GstElement`, `GstPad`, `GstCaps`, `GstBin`, `GstPipeline`, `GstBus`, `GstClock`, `GstBuffer`, `GstEvent`, `GstQuery`. |
| `base` | Base classes for writing elements: `GstBaseSrc`, `GstBaseSink`, `GstBaseTransform`, `GstBaseParse`, `GstAggregator`, `GstCollectPads`, `GstTypeFindHelper`. |
| `video` | `GstVideoInfo`, `GstVideoFormat`, `GstVideoOverlay`, video caps helpers. |
| `audio` | `GstAudioInfo`, `GstAudioFormat`, audio caps helpers, clock-slaving. |
| `rtp` | `GstRTPBuffer`, `GstRTCPBuffer`, `GstRTPBasePayload`, `GstRTPBaseDepayload`. |
| `webrtc` | The C WebRTC library plus `webrtcbin` element + `GstWebRTCRTPTransceiver`, `GstWebRTCICE`, `GstWebRTCDTLSTransport`. |
| `sdp` | SDP (Session Description Protocol) helpers used by webrtcbin + rtspsrc. |
| `pbutils` | Pb-utils: `GstDiscoverer`, `GstEncodingProfile`, codec / pixel-format string helpers. |
| `app` | `appsrc` / `appsink` — feed/drain a pipeline from/to application memory. |
| `coreelements` | The mandatory-always-present elements: `filesrc`, `filesink`, `fakesrc`, `fakesink`, `queue`, `queue2`, `tee`, `identity`, `capsfilter`, `multiqueue`, `valve`, `input-selector`, `output-selector`. |
| `coretracers` | Built-in tracers for GST_DEBUG `gst-top`, `leaks`, `stats`. |
| `libav` | ffmpeg/libav-backed decode/encode elements (`avdec_*`, `avenc_*`). |

## Plugin indexes commonly asked for

| Page | Elements (not exhaustive) |
|---|---|
| `playback` | `playbin`, `playbin3`, `decodebin`, `decodebin3`, `uridecodebin`, `uridecodebin3`, `urisourcebin`, `playsink` |
| `rtsp` | `rtspsrc` |
| `rtspserver` | `rtspclientsink`, `gst-rtsp-server` library objects |
| `hls` | `hlssink`, `hlssink2`, `hlsdemux`, `hlsdemux2` |
| `dash` | `dashdemux`, `dashsink`, `dashdemux2` |
| `srt` | `srtsrc`, `srtsink`, `srtclientsrc`, `srtclientsink`, `srtserversrc`, `srtserversink` |
| `rswebrtc` | `webrtcsink`, `webrtcsrc`, `whipclientsink`, `whepsrc` (Rust, high-level, auto-negotiation) |
| `webrtc` | `webrtcbin` (C, low-level, manual SDP+ICE) |
| `x264` / `x265` / `vpx` | `x264enc`, `x265enc`, `vp8enc`, `vp9enc`, `vp8dec`, `vp9dec` |
| `nvcodec` | `nvh264enc`, `nvh265enc`, `nvh264dec`, `nvh265dec`, CUDA upload/download |
| `isomp4` | `mp4mux`, `qtmux`, `qtdemux`, `fragmentedmp4mux` |
| `matroska` | `matroskamux`, `matroskademux`, `webmmux` |
| `v4l2` | `v4l2src`, `v4l2sink`, plus M2M codec elements on Linux |
| `opengl` | `glimagesink`, `glupload`, `gldownload`, `gleffects`, GPU shaders |
| `vulkan` | Vulkan-backed upload/download/sink |
| `videotestsrc` | Pattern generator — property reference |
| `audiotestsrc` | Tone/noise generator — property reference |

---

## CLI quick reference

CLI tools shipped with GStreamer (all `*-1.0` — the `1.0` suffix is the major
API version; don't drop it):

| CLI | What it does |
|---|---|
| `gst-launch-1.0` | Run a pipeline described in shell syntax. Debug-only in principle; production code should use the library APIs. |
| `gst-inspect-1.0` | Introspect an element (or list all). Shows factory info, pad templates, properties (with types + ranges + defaults), signals. |
| `gst-device-monitor-1.0` | List connected capture + output devices (V4L2, AVF, PipeWire, PulseAudio, ALSA, DShow, WASAPI). |
| `gst-discoverer-1.0` | Probe a URI: streams, caps, duration, tags, seekability. |
| `gst-play-1.0` | Minimal playbin3-based player; handy for quick sanity checks. |
| `gst-typefind-1.0` | Typefind a file — returns the MIME / caps string. |

See the `gstreamer-pipeline` skill for wrappers around all of these.

---

## Key concepts (one line each)

- **Pipeline** — a top-level Bin that owns a clock and bus; what you actually run.
- **Bin** — a container of elements that appears as a single element to its parent.
- **Element** — the atomic processing unit (source, filter, sink).
- **Pad** — a named input/output on an element. Pads carry `GstCaps`.
- **Caps** — media-type + parameters (`video/x-raw, format=I420, width=1280, height=720, framerate=30/1`).
- **Bus** — async message channel for pipeline -> application events (errors, EOS, tags, state changes).
- **Clock** — selected by the pipeline; used for PTS/DTS synchronization across elements.

---

## Cache

- Cache path: `~/.cache/gstreamer-docs/` (override via `GSTREAMER_DOCS_CACHE`).
- One text file per page (plus per-element files for `element` fetches).
- Cache never expires automatically — use `clear-cache` + `index` after a GStreamer release drops doc updates.
- `index` fetches all top-level pages; per-element pages are lazily cached on first access.

## Offline readiness

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gstdocs.py index
```

That's it. `search` / `section` / `fetch --page ...` now work without network for every landing-page-scoped query. Per-element fetches still require network on first access.
