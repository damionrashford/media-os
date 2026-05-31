# GStreamer Pipeline Recipes

Copy-paste-ready `gst-launch-1.0` pipelines covering the most common flows.
Every pipeline has been sanity-checked against current GStreamer 1.24+ plugin
names. When an element lives in a non-default plugin set (`gst-plugins-bad`,
`gst-plugins-ugly`, `gst-plugins-rs`) the recipe notes it.

**Conventions:**
- Run via the gst.py wrapper: `uv run ${CLAUDE_SKILL_DIR}/scripts/gst.py launch -e -v -- <pipeline>`
- Or directly: `gst-launch-1.0 -e -v <pipeline>`
- `-e` sends EOS on SIGINT so muxers finalise their output.
- `-v` prints caps negotiation + property changes (debug-noisy; drop in production).

---

## 1. File playback

Plain playback with auto-sinks:

```
filesrc location=in.mp4 ! decodebin3 ! videoconvert ! autovideosink
```

With explicit sinks:

```
filesrc location=in.mp4 ! decodebin3 name=d \
  d. ! queue ! videoconvert ! glimagesink \
  d. ! queue ! audioconvert ! audioresample ! pulsesink
```

Use `playbin3 uri=file:///abs/path/in.mp4` for the lazy one-liner.

---

## 2. Transcode: input -> H.264 + AAC in MP4

```
filesrc location=in.mov \
  ! decodebin3 name=d \
  d.video_0 ! queue ! videoconvert ! videoscale \
     ! video/x-raw,width=1920,height=1080,format=I420 \
     ! x264enc tune=zerolatency speed-preset=medium bitrate=5000 \
     ! h264parse ! queue ! mux. \
  d.audio_0 ! queue ! audioconvert ! audioresample \
     ! avenc_aac bitrate=128000 ! aacparse ! queue ! mux. \
  mp4mux name=mux faststart=true ! filesink location=out.mp4
```

Notes: `x264enc` ships in `gst-plugins-ugly`. `avenc_aac` comes from
`gst-libav`. Add `movflags=+faststart` via `mp4mux faststart=true` so web
players start before full download.

---

## 3. Webcam + mic -> MP4 (macOS)

```
avfvideosrc device-index=0 \
  ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=3000 \
  ! h264parse ! queue ! mux. \
avfaudiosrc ! audioconvert ! audioresample \
  ! avenc_aac bitrate=128000 ! aacparse ! queue ! mux. \
qtmux name=mux faststart=true ! filesink location=out.mp4
```

Linux equivalent: replace `avfvideosrc` with `v4l2src device=/dev/video0` and
`avfaudiosrc` with `pulsesrc` / `pipewiresrc`.

Windows: `ksvideosrc` (DirectShow legacy) or `mfvideosrc` (Media Foundation)
for video; `wasapisrc` for audio.

---

## 4. Screen capture

**macOS** (Apple Silicon + Intel):

```
avfvideosrc capture-screen=true capture-screen-cursor=true \
  ! video/x-raw,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=8000 \
  ! h264parse ! mp4mux faststart=true ! filesink location=screen.mp4
```

**Linux (X11)**:

```
ximagesrc use-damage=0 show-pointer=true \
  ! video/x-raw,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=8000 \
  ! h264parse ! mp4mux faststart=true ! filesink location=screen.mp4
```

**Linux (Wayland / PipeWire)**:

```
pipewiresrc path=<node-id> \
  ! videoconvert ! x264enc tune=zerolatency bitrate=8000 \
  ! h264parse ! mp4mux ! filesink location=screen.mp4
```

(Use `pw-dump | jq` to find the screen's PipeWire node id.)

**Windows**:

```
d3d11screencapturesrc show-cursor=true ! d3d11convert \
  ! d3d11h264enc ! h264parse ! mp4mux ! filesink location=screen.mp4
```

---

## 5. RTP send (H.264, UDP)

Sender:

```
videotestsrc is-live=true \
  ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! videoconvert \
  ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2500 \
    key-int-max=60 bframes=0 \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=127.0.0.1 port=5000
```

Receiver:

```
udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer \
  ! rtph264depay \
  ! h264parse \
  ! avdec_h264 \
  ! videoconvert \
  ! autovideosink
```

Opus audio variant: replace video chain with `audiotestsrc ! audioconvert !
opusenc ! rtpopuspay ! udpsink` and receiver with `rtpopusdepay ! opusdec !
autoaudiosink`.

---

## 6. MPEG-TS over UDP with FEC (broadcast contribution)

```
videotestsrc is-live=true ! videoconvert \
  ! x264enc tune=zerolatency bitrate=6000 key-int-max=30 \
  ! mpegtsmux ! rtpmp2tpay ! udpsink host=224.0.0.1 port=5004 auto-multicast=true
```

For SMPTE 2022-1 FEC add `rtpulpfecenc` + `rtpstorage` before the `udpsink`.

---

## 7. RTSP source (consume)

```
rtspsrc location=rtsp://admin:pw@10.0.0.42/stream latency=100 \
  ! rtph264depay ! h264parse ! avdec_h264 \
  ! videoconvert ! autovideosink
```

Force TCP transport: `rtspsrc ... protocols=tcp`.

Split audio+video with named element:

```
rtspsrc location=rtsp://... name=src \
  src. ! queue ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink \
  src. ! queue ! rtpmp4gdepay ! aacparse ! avdec_aac ! audioconvert ! autoaudiosink
```

---

## 8. RTSP publish (client side -> server)

```
videotestsrc is-live=true ! videoconvert \
  ! x264enc tune=zerolatency bitrate=3000 key-int-max=30 \
  ! h264parse ! rtspclientsink location=rtsp://127.0.0.1:8554/mystream
```

`rtspclientsink` ships in `gst-rtsp-server`. For an in-process server, write
Python/C using `gst_rtsp_server_new()` — there is no stand-alone server
element.

---

## 9. HLS segmenting (live)

```
videotestsrc is-live=true ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! videoconvert \
  ! x264enc tune=zerolatency bitrate=3000 key-int-max=60 \
  ! h264parse ! hlssink2 \
      location=/srv/hls/seg_%05d.ts \
      playlist-location=/srv/hls/live.m3u8 \
      max-files=5 target-duration=2
```

Requires `gst-plugins-bad`. Serve `/srv/hls/` over HTTP (nginx, caddy,
python -m http.server). For fMP4/CMAF use `hlssink3` (Rust,
`gst-plugins-rs`).

---

## 10. MPEG-DASH segmenting

```
videotestsrc is-live=true ! videoconvert \
  ! x264enc tune=zerolatency bitrate=3000 key-int-max=60 \
  ! h264parse ! dashsink \
      mpd-filename=manifest.mpd \
      target-duration=2 \
      muxer=cmaf
```

`dashsink` is `gst-plugins-rs`. For older setups use `dashmp4mux` +
`hlssink`-style file rotation manually.

---

## 11. WebRTC publish (Rust, high-level)

`webrtcsink` auto-handles SDP + ICE + signalling. Requires `gst-plugins-rs`.

```
videotestsrc is-live=true \
  ! video/x-raw,width=1280,height=720,framerate=30/1 \
  ! videoconvert ! queue \
  ! webrtcsink name=ws \
      signaller::uri=ws://127.0.0.1:8443 \
      meta="meta,name=room1"
```

WHIP direct-publish (simpler; no signaller server):

```
videotestsrc is-live=true ! videoconvert ! queue \
  ! whipclientsink name=ws \
    signaller::whip-endpoint=http://mediamtx.local:8889/live/whip
```

---

## 12. WebRTC receive/publish low-level (`webrtcbin`)

Manual SDP + ICE handling via signals — best to script in Python or Rust, but
a gst-launch one-liner for quick peer-to-peer tests:

```
webrtcbin name=wb bundle-policy=max-bundle stun-server=stun://stun.l.google.com:19302 \
  videotestsrc is-live=true ! videoconvert ! queue \
  ! vp8enc deadline=1 ! rtpvp8pay pt=96 \
  ! 'application/x-rtp,media=video,encoding-name=VP8,payload=96' \
  ! wb.
```

You must connect the `on-negotiation-needed`, `on-ice-candidate`,
`create-offer`, `set-local-description`, `set-remote-description` signals from
code. Read the `gstreamer-docs` skill's `webrtc` page for the full signal
list.

---

## 13. SRT send / receive

Send:

```
videotestsrc is-live=true ! videoconvert \
  ! x264enc tune=zerolatency bitrate=3000 key-int-max=30 \
  ! h264parse ! mpegtsmux \
  ! srtserversink uri=srt://:8888 latency=200
```

Receive:

```
srtclientsrc uri=srt://sender.local:8888 latency=200 ! tsdemux \
  ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

`srt` plugin ships in `gst-plugins-bad`; requires libsrt.

---

## 14. appsrc / appsink bridges

**appsrc** — push frames from your code into a pipeline:

```
appsrc name=src is-live=true format=time \
    caps=video/x-raw,format=BGRA,width=640,height=480,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=2000 \
  ! h264parse ! mp4mux ! filesink location=out.mp4
```

From Python, feed with `appsrc.emit("push-buffer", buf)`.

**appsink** — pull frames out:

```
videotestsrc ! videoconvert ! video/x-raw,format=BGRA,width=640,height=480 \
  ! appsink name=out emit-signals=true max-buffers=1 drop=true
```

Python side: `sink.connect("new-sample", on_new_sample)` and
`sink.emit("pull-sample")`.

---

## 15. FFmpeg -> GStreamer pipe bridge

Use ffmpeg as the source, GStreamer for the rest of the chain (rare but
handy when ffmpeg has a decoder / protocol GStreamer lacks):

```
ffmpeg -i input.srt -c:v copy -f mpegts -      | \
  gst-launch-1.0 fdsrc fd=0 ! tsdemux          \
    ! h264parse ! avdec_h264 ! videoconvert    \
    ! autovideosink
```

Reverse direction — GStreamer -> ffmpeg — via `fdsink fd=1`.

---

## 16. NDI send / receive (requires ndi plugin)

Send:

```
videotestsrc is-live=true ! videoconvert ! ndisink ndi-name="GstTestSender"
```

Receive:

```
ndisrc ndi-name="GstTestSender" ! ndisrcdemux name=d \
  d.video ! queue ! videoconvert ! autovideosink \
  d.audio ! queue ! audioconvert ! autoaudiosink
```

Plugin: `gst-plugins-rs` (Rust `ndi` crate binding).

---

## 17. DeckLink SDI capture (Blackmagic)

Requires Desktop Video SDK and the `decklink` plugin from `gst-plugins-bad`.

```
decklinkvideosrc device-number=0 mode=1080p30 \
  ! videoconvert ! x264enc tune=zerolatency bitrate=10000 \
  ! h264parse ! mp4mux ! filesink location=sdi.mp4
```

List modes: `gst-inspect-1.0 decklinkvideosrc | grep -A 50 mode`.

---

## 18. Tee fan-out (preview + record simultaneously)

```
videotestsrc is-live=true ! videoconvert ! tee name=t \
  t. ! queue ! autovideosink \
  t. ! queue ! x264enc tune=zerolatency bitrate=3000 \
       ! h264parse ! mp4mux ! filesink location=rec.mp4
```

`queue` on each branch is mandatory; without it the pipeline blocks.

---

## Common caps templates

- `video/x-raw,format=I420,width=1280,height=720,framerate=30/1`
- `video/x-raw,format=BGRA,width=640,height=480,framerate=60/1`
- `audio/x-raw,format=S16LE,channels=2,rate=48000,layout=interleaved`
- `application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000`
- `application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000`
- `image/jpeg,width=1280,height=720,framerate=30/1`

---

## Debug cheatsheet

- `GST_DEBUG=3 gst-launch-1.0 ...` — info-level log.
- `GST_DEBUG="*:3,webrtcbin:6"` — everything at 3, webrtcbin at 6.
- `GST_DEBUG_FILE=/tmp/gst.log` — redirect debug output.
- `GST_DEBUG_DUMP_DOT_DIR=/tmp` — dump pipeline graph as `.dot` on each state change. Convert with Graphviz `dot`.
- Run with `-v` for caps negotiation prints.
- Run with `-m` for bus messages.
- Run with `-e` when writing to a muxer so Ctrl-C finalises.

---

## Companion skills

- Look up an element's properties / signals / pads -> `gstreamer-docs`.
- When you need a server that accepts any of RTSP/RTMP/HLS/WebRTC/SRT, use `mediamtx-server` rather than hand-rolling a GStreamer rtsp-server.
- For browser-targeted WebRTC ingest, `ffmpeg-whip` is often simpler than `webrtcsink` / `webrtcbin`.
