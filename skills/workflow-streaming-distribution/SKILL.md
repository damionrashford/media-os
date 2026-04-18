---
name: workflow-streaming-distribution
description: Deliver live or VOD content over HLS / DASH / RTMP / SRT / WHIP / RIST with adaptive bitrate ladders, DRM (Widevine / PlayReady / FairPlay cbcs), multi-protocol fanout via MediaMTX, and CDN upload (Cloudflare Stream / Mux / Bunny / S3). Use when the user says "stream to HLS", "build an ABR ladder", "add Widevine", "multi-bitrate DASH", "WHIP ingest", "low-latency HLS", "SRT contribution", "stream to multiple platforms", "SFU for WebRTC", or anything involving large-scale distribution.
argument-hint: [source]
---

# Workflow — Streaming Distribution

**What:** Ship live or VOD content out to every playback surface. Package once, protect optionally, deliver everywhere.

## Skills used

`ffmpeg-streaming`, `ffmpeg-whip`, `ffmpeg-rist-zmq`, `ffmpeg-hwaccel`, `ffmpeg-drm`, `media-shaka`, `media-gpac`, `mediamtx-server`, `gstreamer-pipeline`, `media-cloud-upload`, `media-batch`, `ffmpeg-quality`, `webrtc-spec`, `webrtc-pion`, `webrtc-mediasoup`, `webrtc-livekit`, `ffmpeg-docs`.

## Pipeline

### Step 1 — Pick contribution protocol

Latency vs. reliability vs. tooling:

| Protocol | Latency | Pros | Cons |
|---|---|---|---|
| WHIP (WebRTC) | sub-second | lowest latency; browser-native | needs HTTPS in prod; ffmpeg 7+ |
| SRT | 120 ms default (tunable) | reliable UDP, forward error recovery | needs port forwarding |
| RTMP | 2–5 s | ubiquitous ingest | TCP, no FEC, aging |
| RIST | low | FEC + ARQ pro contribution | fewer CDN endpoints |

### Step 2 — Build the ABR ladder

Use `ffmpeg-streaming` with the split-scale-encode pattern — one decode, N rate/size variants emitted in parallel. Netflix-style default: 4 video renditions (240p, 480p, 720p, 1080p) + 2 audio tracks (stereo + 5.1). Force keyframe alignment with `-g <fps*seg_len>`, `-keyint_min <fps*seg_len>`, `-sc_threshold 0`.

### Step 3 — Package

Canonical target is CMAF (unified fMP4 segments serving both HLS and DASH manifests). Use `media-shaka` (Shaka Packager) for one-command HLS+DASH output from the same segment set. For pure HLS classic, `ffmpeg-streaming`'s `hls` muxer works directly.

### Step 4 — Optional DRM

- **HLS AES-128** — simplest; encrypts segment payload only.
- **Widevine / PlayReady / FairPlay unified** — CMAF with `cbcs` scheme. `media-shaka` handles the three simultaneously; key server URL in `${user_config.SHAKA_KEY_SERVER_URL}`.
- **DASH CENC** — `ffmpeg-drm` or Shaka for ClearKey / Widevine.

### Step 5 — Fanout via MediaMTX

The `mediamtx-server` skill ingests RTMP/SRT/WebRTC and republishes to every other protocol. One YAML → every playback client served.

### Step 6 — CDN upload

Use `media-cloud-upload`: Cloudflare Stream (tus resumable), Mux (token id + secret), Bunny (PUT to storage zone), S3 (aws CLI / rclone). Tokens live in plugin userConfig.

### Step 7 — Scale — SFU for large interactive audiences

For bidirectional many-to-many (> ~50 peers), deploy an SFU instead of MediaMTX: `webrtc-livekit` (Go + JWT minter), `webrtc-mediasoup` (Node), or `webrtc-pion` (Go, lower-level).

## Variants

- **Low-latency HLS** (LL-HLS) — `-hls_segment_type fmp4`, short `-hls_time` (1–2 s), `-hls_flags +independent_segments+omit_endlist`.
- **DASH with SegmentTemplate** — manifest-side list generation, no explicit segment enum.
- **RIST + ZMQ live control** — dynamic filter parameter changes at runtime via `ffmpeg-rist-zmq`.
- **SRT listener mode** — receiver listens on a port, sender `?mode=caller`.
- **Multicast MPEG-TS** — LAN distribution, no CDN needed.

## Gotchas

- **MP4 output needs `-movflags +faststart`** — second-pass rewrite to move moov atom to front. Required for progressive web playback.
- **`-hls_time` is a target, not a guarantee.** Keyframe cadence determines actual segment length. Force alignment: `-g <fps*seg_len> -keyint_min <fps*seg_len> -sc_threshold 0`.
- **`independent_segments` flag required for CMAF/LL-HLS.** ABR switching breaks without it.
- **HLS AES-128 encrypts segment PAYLOAD only**, not the playlist. Protect the key URI via server-side auth.
- **`-hls_key_info_file` needs a trailing newline on the IV line.** Many editors strip it silently, then decryption fails.
- **Widevine L1 requires hardware CDM** (ChromeOS, Android TEE). Test locally with L3 in Chrome.
- **FairPlay uses `cbcs` scheme; Widevine/PlayReady default to `cenc`.** For unified CMAF DRM, ALL three use `cbcs`.
- **CMAF audio must be fMP4, not TS.** Mixed TS-video + fMP4-audio HLS breaks Safari.
- **WHIP in production needs HTTPS.** Chrome blocks `getUserMedia` over http except on `localhost`.
- **ffmpeg WHIP requires FFmpeg 7+.** Older builds silently fail.
- **MediaMTX default ports: 1935 RTMP, 8554 RTSP, 8888 HLS, 8889 WebRTC, 8890 SRT, 9997 API.** Open all the ones you use.
- **MediaMTX `/v3/*` Control API needs `api: yes` in config** (off by default).
- **`-re` flag reads input at native framerate** — essential for live from file; without it ffmpeg reads as fast as possible.
- **`-f flv` explicit for RTMP** — ffmpeg can pick the wrong muxer from the URL alone.
- **RTMP chunk size default is 128 bytes** — for 4K/HEVC ingest use `-rtmp_chunk_size 4096`.
- **AAC LC floor** — 64 k mono, 96 k stereo. Below that, use HE-AAC.
- **LiveKit JWT tokens expire** (default 6 h). Mint fresh tokens client-side on refresh.
- **Pion SFU needs STUN/TURN** for NAT traversal. Set `ICEServers` in config.
- **mediasoup needs Node 18+ and a platform-specific native `mediasoupworker` build.**

## Example — 4-variant CMAF HLS + DASH with unified DRM

Invoke `media-shaka` to take a single master ProRes/MOV through Shaka Packager with 4 video renditions + AAC stereo + `cbcs` key rotation, emitting both `master.m3u8` and `manifest.mpd` pointing at the same `*.m4s` segments. Upload with `media-cloud-upload`. QC the result with `workflow-analysis-quality`.

## Related

- `workflow-live-production` — where the contribution stream originates.
- `workflow-broadcast-delivery` — for broadcast-spec contribution paths.
- `workflow-analysis-quality` — VMAF + manifest validation on the encoded output.
