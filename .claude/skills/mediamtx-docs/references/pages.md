# MediaMTX Documentation Page Catalog

`scripts/mtxdocs.py` fetches from a fixed list of pages on mediamtx.org plus a
handful of raw-upstream GitHub files. This file documents what each page is,
when to pick it, and the operational knob it governs.

URLs are the full `https://mediamtx.org/docs/<page>` form, except for the
`github-*` entries which point at raw content in `bluenviron/mediamtx`.

---

## Kickoff — install & upgrade

| Page | Covers |
|---|---|
| `kickoff/introduction` | What MediaMTX is. All-protocol real-time media server, remux-only, single static Go binary. |
| `kickoff/install` | Download binary / Docker `bluenviron/mediamtx` / build from source. |
| `kickoff/upgrade` | Semver notes + migration tips between releases. |

---

## Features — core flows

| Page | Covers |
|---|---|
| `features/architecture` | Paths, sources, readers, publishers. Diagrams for every protocol. |
| `features/publish` | Concept of "publish" — a source-side producer writes RTP packets into a path. |
| `features/read` | Concept of "read" — a reader-side consumer pulls packets out. |
| `features/record` | Segment-to-disk recording (fmp4 default; mpegts option). Path-level `record`, `recordPath`, `recordFormat`, `recordSegmentDuration`, `recordDeleteAfter`. |
| `features/playback` | Playback API (`/playback`) for seeking over previously-recorded fMP4 segments via HTTP. |
| `features/authentication` | Three auth backends: internal users (`authInternalUsers`), external HTTP, JWT (JWK URL / shared secret). Per-action permissions (publish/read/playback/api/metrics/pprof). |
| `features/hooks` | `runOnInit`, `runOnDemand`, `runOnConnect`, `runOnDisconnect`, `runOnReady`, `runOnRead`, `runOnUnread`. |
| `features/metrics` | Prometheus scrape endpoint on port 9998. Stream / session / path counters. |
| `features/forward` | Forward a path to another mediamtx / RTSP / RTMP / SRT destination. |
| `features/proxy` | Proxy an external source into a local path (opposite of forward). |
| `features/performance` | Tuning: UDP buffers, RTSP read/write buffer sizes, ulimit, GOGC. |

## Features — per-protocol

| Page | Covers |
|---|---|
| `features/rtsp-specific-features` | RTSP 1.0 + RTSPS, `protocols: [udp, multicast, tcp]`, authentication methods, port overrides. |
| `features/rtmp-specific-features` | RTMP + RTMPS (1935 + 1936). Flash-era tweaks, encrypted variants, app+stream-key scheme. |
| `features/webrtc-specific-features` | WHIP/WHEP endpoints, ICE server config, TURN, port ranges for unbundled RTP. |
| `features/srt-specific-features` | SRT 8890, streamid routing, passphrase, latency param. |

## Features — operational

| Page | Covers |
|---|---|
| `features/absolute-timestamps` | Align stream timestamps to wall clock so mux tools can correlate across paths. |
| `features/always-available` | Keep a source alive indefinitely. |
| `features/on-demand-publishing` | Fire a publisher process (`runOnDemand`) only when readers appear. |
| `features/decrease-packet-loss` | Tunables to survive lossy UDP networks. |
| `features/extract-snapshots` | Grab a JPEG from a live path without disturbing readers. |
| `features/remuxing-reencoding-compression` | IMPORTANT: MediaMTX does not transcode. Chain an ffmpeg publisher for transcode. |
| `features/start-on-boot` | systemd / launchd / Windows service recipes. |
| `features/embed-streams-in-a-website` | Example HTML for HLS.js / video tag / webrtc WHEP + the required CORS headers. |
| `features/expose-the-server-in-a-subfolder` | Reverse-proxy behind `/mediamtx/*` via nginx / caddy. |
| `features/logging` | Log destinations (stdout / file / syslog), log levels. |
| `features/configuration` | YAML schema overview; how to load alternate config files. |
| `features/control-api` | `/v3/*` on port 9997. GET/POST/DELETE endpoints. |

## References (authoritative)

| Page | Covers |
|---|---|
| `references/configuration-file` | The `mediamtx.yml` schema — every top-level key, every path key, every default. Start here for any config question. |
| `references/control-api` | Every `/v3/*` endpoint with request + response JSON shape. Start here for any API question. |

---

## Publish howtos

All at `publish/<client>`. How to push a stream into MediaMTX from the named client:

- `publish/ffmpeg` — RTSP / RTMP / SRT / WebRTC-WHIP via `ffmpeg ... -f <fmt>`.
- `publish/gstreamer` — `rtspclientsink`, `rtmp2sink`, `srtsink`, `whipclientsink`.
- `publish/obs-studio` — Custom Service URL + stream key.
- `publish/python-opencv` — `cv2.VideoWriter` with `GStreamer` / FFmpeg backend.
- `publish/golang` — `gortsplib` SDK (BluEnviron).
- `publish/unity` — WebRTC publisher from the Unity WebRTC package.
- `publish/raspberry-pi-cameras` — libcamera-vid piped through ffmpeg.
- `publish/web-browsers` — WHIP in the browser with the Signed-Exchange API.
- `publish/webrtc-clients` — WHIP from any WHIP-compliant client.
- `publish/webrtc-servers` — Bridge from an external SFU (Janus, LiveKit, mediasoup).
- `publish/rtsp-cameras-and-servers` — Pull from an IP camera and republish.
- `publish/rtmp-cameras-and-servers` — Pull from RTMP source.
- `publish/hls-cameras-and-servers` — Pull from HLS URL and republish.
- `publish/srt-cameras-and-servers` — Pull from SRT source.
- `publish/generic-webcams` — USB webcam via ffmpeg or gstreamer.
- `publish/rtsp-clients` — RTSP `ANNOUNCE+RECORD` flow.
- `publish/rtmp-clients` — Standard RTMP publish.
- `publish/srt-clients` — SRT caller publish.
- `publish/rtp` — Raw RTP push with SDP.
- `publish/mpeg-ts` — MPEG-TS over HTTP POST or UDP.

---

## Read howtos

All at `read/<client>`. How to pull a stream out of MediaMTX:

- `read/ffmpeg` — Play / record with `ffmpeg -i <rtsp|rtmp|srt|hls|whep-url>`.
- `read/gstreamer` — `rtspsrc`, `hlsdemux`, `srtclientsrc`, `whep*` elements.
- `read/vlc` — Open `rtsp://`, `rtmp://`, `http://.../hls/index.m3u8`, `srt://...`.
- `read/obs-studio` — Media Source for HLS; custom RTSP via Browser Source; WebRTC via browser.
- `read/python-opencv` — `cv2.VideoCapture` with GStreamer / FFmpeg backend.
- `read/golang` — `gortsplib` reader.
- `read/unity` — WebRTC reader.
- `read/web-browsers` — HLS.js for standard HLS; video element for LL-HLS + WHEP; MSE for custom.
- `read/rtsp` — Plain RTSP client.
- `read/rtmp` — Plain RTMP client.
- `read/hls` — HLS URL structure (`/<path>/index.m3u8`).
- `read/srt` — SRT caller read.
- `read/webrtc` — WHEP from any client (web, native, embedded).

---

## GitHub fallbacks (raw upstream)

When the site lags or you need exact current behaviour:

- `github-readme` — `main` branch README.md.
- `github-mediamtx.yml` — The shipped `mediamtx.yml` with every default inline.
- `github-apidocs` — The OpenAPI spec for `/v3/*` (`apidocs/openapi.yaml`).

---

## Default ports (memorise these)

| Port | Service |
|---|---|
| 8554 | RTSP |
| 8322 | RTSPS |
| 1935 | RTMP |
| 1936 | RTMPS |
| 8888 | HLS |
| 8889 | WebRTC (WHIP/WHEP) |
| 8890 | SRT |
| 9997 | Control API |
| 9998 | Metrics (Prometheus) |
| 9999 | pprof |
| 9996 | Playback API |

Disable any you don't expose.

---

## Quick decision table

| Question | Page |
|---|---|
| "How do I add a new path with recording?" | `features/record` + `references/configuration-file` |
| "How do I authenticate publishers with JWT?" | `features/authentication` |
| "What's the API to list live sessions?" | `references/control-api` (look for `/v3/rtspsessions/list` etc.) |
| "How do I detect when a viewer connects?" | `features/hooks` (`runOnRead`) |
| "Why does my HEVC stream fail in browsers?" | `features/remuxing-reencoding-compression` |
| "How do I push from ffmpeg?" | `publish/ffmpeg` |
| "How do I play in VLC?" | `read/vlc` |
| "What Prometheus metrics are exposed?" | `features/metrics` |
| "How do I set up TLS?" | `features/rtsp-specific-features` (for RTSPS), plus TLS keys referenced in `references/configuration-file` |

---

## Cache

- Cache path: `~/.cache/mediamtx-docs/` (override via `MEDIAMTX_DOCS_CACHE`).
- One text file per page.
- `index` fetches all ~70 pages with a 0.3s delay between each.
- After a MediaMTX release, `clear-cache` + `index` to refresh.
