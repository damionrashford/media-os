---
name: gstreamer-pipeline
description: >
  Build and run GStreamer pipelines with gst-launch-1.0, introspect elements with gst-inspect-1.0, discover media with gst-discoverer-1.0, enumerate devices with gst-device-monitor-1.0, play files with gst-play-1.0, detect type with gst-typefind-1.0. Pipeline syntax (element ! element, named elements, caps filter), common flows (file playback, transcoding, RTP send/receive, HLS/DASH segmenting, WebRTC via webrtcbin, RTSP server via rtspclientsink/rtsp-server library, screen capture, webcam, appsrc/appsink integration). Use when the user asks to build a GStreamer pipeline, construct a gst-launch command, do real-time video processing with GStreamer, pipe ffmpeg output into GStreamer, build an embedded/Linux media pipeline, use webrtcbin, stream RTSP via GStreamer, or author a plugin-graph pipeline.
argument-hint: "[pipeline]"
---

# GStreamer Pipeline

**Context:** $ARGUMENTS

## Quick start

- **Run a pipeline:** -> Step 4 (`launch -- <pipeline-desc>`)
- **Look up an element's properties:** -> Step 2 (`inspect --element <name>`)
- **Probe a file or URL:** -> Step 3 (`discover --uri <uri>`)
- **List cameras / mics / screens:** -> Step 3 (`devices`)
- **Copy-paste a ready-made recipe:** -> Read [`references/pipelines.md`](references/pipelines.md)

## When to use

- User wants a running pipeline: "play this", "transcode", "publish RTSP", "receive WebRTC".
- User wants to verify an element exists locally AND is linkable with a given caps.
- User wants to enumerate cameras/mics with `gst-device-monitor-1.0`.
- User wants to probe a file's streams/caps/duration via `gst-discoverer-1.0`.
- User wants a `gst-launch-1.0` one-liner for bench-testing before coding the C / Rust / Python client.

For documentation lookup (which properties does `hlssink2` expose? what does `webrtcbin` support?), use the `gstreamer-docs` skill first.

---

## Step 1 — Check GStreamer is installed

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --element filesrc --dry-run
```

If this errors with "gst-inspect-1.0 not found", install:

- macOS: `brew install gstreamer`
- Debian/Ubuntu: `apt install gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad,ugly} gstreamer1.0-libav`
- Fedora: `dnf install gstreamer1 gstreamer1-plugins-{base,good,bad-free,ugly-free} gstreamer1-libav`
- Windows: MSI installer at gstreamer.freedesktop.org/download/

Verify plugin sets are present; many elements (e.g. `webrtcbin`, `hlssink2`, `srtsink`, `x264enc`) ship in `-bad` or `-ugly` or Rust plugins (`gst-plugins-rs`).

---

## Step 2 — Introspect an element before using it

Never hand-assemble an element's properties from memory. Use:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --element webrtcbin
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --element hlssink2
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --element x264enc
```

List every factory:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py list-elements
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py list-elements --plugin coreelements
```

Find which elements handle a URI scheme (e.g. rtsp://):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --uri-handlers
```

Filter by factory type:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --types "Codec/Encoder/Video"
```

Pair with the `gstreamer-docs` skill for the canonical URL and full property table if the CLI output is terse.

---

## Step 3 — Probe devices and media

Discover streams, caps, duration, tags of a file or URL:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py discover --uri file:///path/to/file.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py discover --uri rtsp://camera.local/stream -v -t 10
```

List capture + output devices:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py devices
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py devices --classes "Video/Source" "Audio/Source"
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py devices --follow   # watch add/remove events
```

Typefind (MIME / caps) on a blob:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py typefind /tmp/unknown.bin
```

---

## Step 4 — Run a pipeline with `launch`

Use `--` to separate pipeline tokens from gst.py flags, then write the pipeline in GStreamer shell syntax:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -- \
  videotestsrc num-buffers=300 \
  ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! timeoverlay \
  ! autovideosink
```

Enable verbose caps negotiation:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -v -- videotestsrc ! fakesink
```

Set `GST_DEBUG` without manual env export:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch \
  --debug-level "3,webrtcbin:6" \
  --debug-file /tmp/gst.log \
  --verbose-tool -e -- \
  videotestsrc ! x264enc ! rtph264pay ! udpsink host=127.0.0.1 port=5000
```

Add `--eos-on-shutdown` when writing to a muxer so Ctrl-C finalises the file cleanly (otherwise `matroskamux` / `mp4mux` leave a truncated output).

Dry-run echoes the exact `gst-launch-1.0` invocation and exits:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch --dry-run -- filesrc location=in.mp4 ! decodebin ! autovideosink
```

---

## Step 5 — Quick playback with `play`

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py play video.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py play rtsp://cam/stream --audio-only
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py play video.mp4 --no-interactive
```

`--no-interactive` disables keyboard controls — use this in any non-interactive agent run.

---

## Step 6 — Grab a recipe

[`references/pipelines.md`](references/pipelines.md) has 15+ production-ready pipelines:

- File playback / transcoding (H.264 + AAC in MP4)
- Webcam + mic -> MP4
- Screen capture -> MP4 (macOS / Linux / Windows)
- RTP send + receive (H.264, Opus)
- MPEG-TS over UDP with FEC
- RTSP client consumption and RTSP server publish
- HLS segmenting (`hlssink2`)
- DASH segmenting (`dashsink`)
- WebRTC publish with `webrtcsink` (Rust, auto-negotiation)
- Low-level WebRTC with `webrtcbin`
- SRT send / receive
- appsrc / appsink bridges for custom code
- NDI / DeckLink if available

Read `references/pipelines.md` when the user needs a starting pipeline for any of the above.

---

## Gotchas

- **All CLI tools have the `-1.0` suffix.** `gst-inspect-1.0` not `gst-inspect`, `gst-launch-1.0` not `gst-launch`. The `1.0` is the major API version; GStreamer 0.10 was EOL'd in 2012 and tools without `-1.0` usually don't exist.
- **`!` is NOT a logical-NOT in gst-launch.** It's the link operator. Quote your pipeline or use `--` so the shell passes it through: `gst.py launch -- videotestsrc ! fakesink`.
- **Caps filters are `video/x-raw,width=1280,...` with NO space after the commas.** Some shells swallow the parens / commas — single-quote the caps string when in doubt.
- **`queue` is mandatory between threads.** Whenever you have a `tee` fan-out, or sink/source crossing subsystems (audio<->video, CPU<->GPU), insert a `queue` on each branch. Without it the pipeline serialises on one thread and the second branch starves.
- **`videoconvert` + `audioconvert` are cheap insurance.** When two elements disagree on caps, drop `videoconvert ! videoscale` or `audioconvert ! audioresample` in between. GStreamer will no-op if the caps already match.
- **`decodebin3` / `uridecodebin3` use `GST_MESSAGE_STREAM_COLLECTION` + `GST_EVENT_SELECT_STREAMS`**, NOT the old `autoplug-*` signals. Port old `decodebin` code carefully.
- **`playbin3` has different bus messages from `playbin`.** Don't copy-paste signal handlers between them.
- **Rust plugins (gst-plugins-rs) ship separately.** `webrtcsink`, `awstranscriber`, `whipclientsink` aren't in `-good/-bad/-ugly` — they need `gst-plugins-rs` (available from gstreamer.freedesktop.org or your distro). If `gst-inspect-1.0 webrtcsink` comes up empty, install `gst-plugins-rs`.
- **`webrtcbin` vs `webrtcsink`**: `webrtcbin` is the low-level C element where you drive SDP + ICE manually via signals (`create-offer`, `set-local-description`, etc.). `webrtcsink` is the Rust high-level element that auto-negotiates and speaks WHIP/WHEP. Pick one.
- **`hlssink` is deprecated; use `hlssink2` or `hlssink3`.** Same for RTSP server: `rtspclientsink` is the client side; the server side is the `gst-rtsp-server` library (no stand-alone element).
- **`-e` / `--eos-on-shutdown`** — always pass this when writing to a muxer. Without it, Ctrl-C kills the pipeline mid-write and the output file has no moov atom / is unseekable.
- **`GST_DEBUG=3` is the sweet spot** for pipeline tracing. `*:4` is too noisy. Scope to one element: `GST_DEBUG="*:3,webrtcbin:6"`.
- **macOS `avfvideosrc` needs `device-index=<N>`** — discover via `gst-device-monitor-1.0 Video/Source`. Permission prompts happen on first run; grant them in System Settings -> Privacy.
- **Windows + `ksvideosrc` / `wasapisrc`** may be flaky on some Dell/Realtek combos — fall back to `mfvideosrc` / `directsoundsrc` when they are.
- **`autovideosink` / `autoaudiosink` pick the best-available sink**; fine for ad-hoc testing but in production always name the sink (`glimagesink`, `d3d11videosink`, `osxvideosink`, `pulsesink`, `pipewiresink`) so behaviour is deterministic.
- **Pipeline descriptions that work in `gst-launch-1.0` may need slight tweaks in `gst_parse_launch()`.** The latter is a superset in most GStreamer versions but bracket+escaping differs. When porting from CLI to code, test both.
- **`gst-launch-1.0` is debug-only per the official docs** — production code should use the library API. The pipelines in `references/pipelines.md` are optimised for prototyping and Claude-to-user hand-off.

---

## Examples

### Example 1: "Play an MP4 with verbose caps"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -v -- \
  filesrc location=in.mp4 ! decodebin3 ! videoconvert ! autovideosink
```

### Example 2: "Record my webcam + mic to MP4 for 30 seconds (macOS)"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -e -- \
  avfvideosrc device-index=0 ! video/x-raw,width=1280,height=720 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=3000 ! h264parse \
  ! qtmux name=mux ! filesink location=out.mp4 \
  avfaudiosrc ! audioconvert ! audioresample ! avenc_aac bitrate=128000 \
  ! mux. \
  --eos-on-shutdown
```

(Kill with Ctrl-C after 30s; `-e` ensures `qtmux` finalises.)

### Example 3: "Probe an RTSP camera for its streams"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py discover \
  --uri rtsp://admin:pw@10.0.0.42/stream -v -t 10
```

### Example 4: "What video inputs can I record from?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py devices --classes "Video/Source"
```

### Example 5: "Dump the full property list for webrtcbin"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py inspect --element webrtcbin
```

### Example 6: "Publish a test pattern to MediaMTX via WHIP"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -v -e -- \
  videotestsrc is-live=true \
  ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! videoconvert \
  ! 'whipclientsink name=ws signaller::whip-endpoint=http://127.0.0.1:8889/live/whip'
```

(Requires `gst-plugins-rs`; fall back to a `webrtcsink + signaller` setup if absent.)

---

## Troubleshooting

### `WARNING: erroneous pipeline: no element "webrtcbin"`

**Cause:** Plugin not installed.
**Solution:** `webrtcbin` lives in `gst-plugins-bad`. Install it: macOS `brew install gst-plugins-bad`; Debian/Ubuntu `apt install gstreamer1.0-plugins-bad libnice-dev`. Verify with `gst-inspect-1.0 webrtcbin`.

### `could not link filesrc0 to decodebin0`

**Cause:** `filesrc` produces `ANY` caps, but some decoders want a typefind step.
**Solution:** Insert `decodebin3` which handles typefind internally: `filesrc location=in.mp4 ! decodebin3 ! ...`. Or use `uridecodebin3 uri=file:///...`.

### `gst-launch-1.0: command not found`

**Cause:** Tools not on PATH, or only `gst-launch` installed without the `-1.0` suffix (very old GStreamer).
**Solution:** Reinstall GStreamer 1.x. On macOS homebrew: `brew install gstreamer`.

### Output MP4 from the recording pipeline is 0 bytes or unplayable

**Cause:** Process killed without EOS -> `qtmux` / `mp4mux` never wrote the moov atom.
**Solution:** Re-run with `-e` / `--eos-on-shutdown`, use Ctrl-C only once, then wait 1-2s for finalisation.

### `avfvideosrc` opens but produces no frames on macOS

**Cause:** Privacy permission not granted to the terminal / IDE running gst-launch.
**Solution:** macOS System Settings -> Privacy & Security -> Camera -> add your terminal. Restart the terminal after granting.

### Pipeline runs but no audio in output

**Cause:** Missing `queue` on the audio branch of a muxer fan-in, or wrong sample rate.
**Solution:** Insert `queue ! audioconvert ! audioresample` before the muxer pad. Ensure `mux.` syntax attaches to the named `mux` element.

### "Delayed linking failed for: webrtcbin.sink"

**Cause:** `webrtcbin` refuses RTP caps that don't specify `payload-type` / `encoding-name`.
**Solution:** Add a `capsfilter`: `rtph264pay config-interval=-1 pt=96 ! application/x-rtp,media=video,encoding-name=H264,payload=96 ! webrtcbin.`

---

## Reference docs

- Full set of copy-paste pipeline recipes -> [`references/pipelines.md`](references/pipelines.md)
