# Streaming Distribution Workflow

**What:** Take a live or VOD source and deliver it to end users over every major streaming protocol — HLS, DASH, RTMP, SRT, WHIP/WebRTC, RIST — with DRM, ABR ladders, and CDN distribution.

**Who:** OTT platforms, live streamers, news organizations, sports broadcasters, enterprise video teams.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| Core streaming | `ffmpeg-streaming` | HLS / DASH / RTMP / SRT / tee output |
| WebRTC contribution | `ffmpeg-whip` | FFmpeg 7+ WHIP publisher |
| RIST + ZMQ | `ffmpeg-rist-zmq` | Broadcast-grade RIST + live filter-graph control via ZMQ |
| Multi-protocol server | `mediamtx-server` | One YAML → all protocols, with Control API |
| Protocol framework | `gstreamer-pipeline` | Alternative to FFmpeg for GStreamer-native shops |
| Hardware encode | `ffmpeg-hwaccel` | NVENC / QSV / VAAPI / VideoToolbox / AMF |
| Protocol docs | `ffmpeg-docs` | Verify every flag before committing |
| HLS AES-128 + DASH CENC | `ffmpeg-drm` | Native FFmpeg encryption |
| Commercial DRM | `media-shaka` | Widevine / PlayReady / FairPlay packaging |
| MP4/CMAF surgery | `media-gpac` | fragment / repair / remux |
| Cloud CDN upload | `media-cloud-upload` | Cloudflare Stream / Mux / Bunny / YouTube / S3 |
| Batch scale | `media-batch` | GNU parallel for many simultaneous renditions |
| WebRTC spec | `webrtc-spec` | SDP / ICE / DTLS / SRTP internals |
| WebRTC SFUs | `webrtc-pion`, `webrtc-mediasoup`, `webrtc-livekit` | Build or operate an SFU |
| Quality | `ffmpeg-quality` | VMAF ABR rung tuning |

---

## The pipeline

### 1. Pick the contribution protocol

| Source latency needed | Protocol | Skill |
|---|---|---|
| Sub-second interactive | WHIP (WebRTC) | `ffmpeg-whip`, `mediamtx-server` WHIP endpoint |
| < 2s broadcast contribution | SRT | `ffmpeg-streaming` (`srt://`) |
| Legacy broadcaster | RTMP | `ffmpeg-streaming` (`rtmp://`) |
| Nat-traversal / packet loss | RIST | `ffmpeg-rist-zmq` |
| UDP multicast (venue) | MPEG-TS over UDP | `ffmpeg-streaming` (`udp://`) |

### 2. Build the ABR ladder

Netflix-style ABR ladder with four renditions:

```bash
ffmpeg -i input.mp4 \
  -filter_complex "\
    [0:v]split=4[v1][v2][v3][v4]; \
    [v1]scale=w=1920:h=1080[v1out]; \
    [v2]scale=w=1280:h=720[v2out]; \
    [v3]scale=w=854:h=480[v3out]; \
    [v4]scale=w=640:h=360[v4out]" \
  -map "[v1out]" -c:v:0 libx264 -b:v:0 5M -maxrate:0 5.35M -bufsize:0 7.5M \
  -map "[v2out]" -c:v:1 libx264 -b:v:1 3M -maxrate:1 3.2M -bufsize:1 4.5M \
  -map "[v3out]" -c:v:2 libx264 -b:v:2 1.5M -maxrate:2 1.6M -bufsize:2 2.25M \
  -map "[v4out]" -c:v:3 libx264 -b:v:3 800k -maxrate:3 856k -bufsize:3 1.2M \
  -map a:0 -c:a aac -b:a 128k -ac 2 \
  -map a:0 -c:a aac -b:a 128k -ac 2 \
  -map a:0 -c:a aac -b:a 96k -ac 2 \
  -map a:0 -c:a aac -b:a 64k -ac 2 \
  -f hls -hls_time 4 -hls_list_size 0 -hls_segment_type mpegts \
  -hls_flags independent_segments -master_pl_name master.m3u8 \
  -hls_segment_filename "v%v/segment_%03d.ts" \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2 v:3,a:3" \
  "v%v/playlist.m3u8"
```

**Critical flags** (see `ffmpeg-streaming`):
- `-hls_time 4` — segment duration (2-6s typical)
- `-hls_flags independent_segments` — each segment is independently decodable (required for CMAF)
- `-sc_threshold 0` (when using `-g`) — prevents GOP mid-segment (breaks ABR switching)
- `-hls_segment_type mpegts` — legacy TS; use `fmp4` for CMAF/DASH co-packaging

Use `ffmpeg-docs` to verify every flag:
```bash
uv run .claude/skills/ffmpeg-docs/scripts/ffdocs.py search --query "hls_flags" --page ffmpeg-formats
```

### 3. Apply DRM (if needed)

**HLS AES-128 (cheap, broad compat, no CDM required):**
```bash
ffmpeg -i input.mp4 \
  -c copy -hls_time 4 \
  -hls_key_info_file key.info \
  -f hls index.m3u8
```

Where `key.info` is three lines: key URI, local key path, IV.

**DASH CENC / ClearKey:**
```bash
ffmpeg -i input.mp4 \
  -c copy -f dash \
  -encryption_scheme cenc-aes-ctr \
  -encryption_key <hex> -encryption_kid <hex> \
  manifest.mpd
```

**Widevine + PlayReady + FairPlay (production):**
Hand off to Shaka Packager:

```bash
uv run .claude/skills/media-shaka/scripts/shakactl.py package \
  --input input.mp4 \
  --output-dir cmaf/ \
  --drm widevine,playready,fairplay \
  --widevine-key-server https://license.uat.widevine.com/cenc/getcontentkey/... \
  --fairplay-scheme cbcs
```

Shaka produces CMAF + HLS playlists + DASH MPD signed for all three DRM ecosystems.

### 4. Package containers

**CMAF (unified HLS + DASH):**
```bash
uv run .claude/skills/media-shaka/scripts/shakactl.py package --format cmaf ...
```

**MP4 `faststart` for progressive:**
```bash
ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4
```

Fragment MP4 manually:
```bash
uv run .claude/skills/media-gpac/scripts/gpacctl.py fragment --input input.mp4 --output fragmented.mp4
```

### 5. Multi-protocol fanout via MediaMTX

Point MediaMTX at a single RTMP ingest; it publishes HLS + WebRTC + RTSP + SRT simultaneously.

```yaml
# mediamtx.yml
paths:
  live:
    source: publisher
```

Start:
```bash
uv run .claude/skills/mediamtx-server/scripts/mtxctl.py start --config mediamtx.yml
```

Ingest (from anywhere):
```bash
ffmpeg -re -i input.mp4 -c copy -f flv rtmp://mediamtx-host:1935/live
```

Playback URLs:
- HLS: `http://host:8888/live/index.m3u8`
- WebRTC: `http://host:8889/live`
- RTSP: `rtsp://host:8554/live`
- SRT: `srt://host:8890?streamid=read:live`
- WHEP: `http://host:8889/live/whep`

### 6. Cloud CDN upload

```bash
# Cloudflare Stream
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider cloudflare --file master.m3u8

# Mux
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider mux --file input.mp4

# S3 static HLS
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --bucket my-vod --prefix live/ --dir hls/
```

### 7. WebRTC SFU mode (large audience interactive)

For large interactive audiences, MediaMTX won't scale — you need an SFU.

**LiveKit (easiest):**
```bash
# Mint a room token (pure-stdlib helper, no pip)
uv run .claude/skills/webrtc-livekit/scripts/lkctl.py mint-token \
  --api-key APIkey --api-secret secret \
  --room live --identity viewer-42 --grants subscribe
```

**mediasoup (most flexible):**
```bash
uv run .claude/skills/webrtc-mediasoup/scripts/msctl.py create-router
```

**Pion (Go, custom logic):**
```bash
uv run .claude/skills/webrtc-pion/scripts/pionctl.py scaffold --name my-sfu
```

---

## Variants

### Low-latency HLS (LL-HLS)

```
ffmpeg ... \
  -hls_time 1 -hls_list_size 10 \
  -hls_flags independent_segments+program_date_time+append_list \
  -hls_playlist_type event \
  -hls_segment_type fmp4 \
  -method PUT -http_persistent 1 \
  -hls_fmp4_init_filename "init.mp4"
```

Pair with a CDN that supports LL-HLS (Cloudflare, AWS CloudFront via custom behaviors).

### DASH with SegmentTemplate

```bash
ffmpeg -i input.mp4 -c:v libx264 -c:a aac \
  -f dash -seg_duration 4 -use_timeline 1 -use_template 1 \
  -init_seg_name 'init-$RepresentationID$.m4s' \
  -media_seg_name 'chunk-$RepresentationID$-$Number%05d$.m4s' \
  manifest.mpd
```

### RIST contribution with ZMQ live-control

```bash
ffmpeg -i input.mp4 \
  -f mpegts "rist://receiver:1968?buffer=800&bandwidth=10000"
```

Dynamically change a filter param during the stream:
```bash
uv run .claude/skills/ffmpeg-rist-zmq/scripts/ristzmq.py send \
  --addr tcp://127.0.0.1:5555 \
  --target "Parsed_overlay_0" --command "x 100"
```

### SRT in listener mode

```bash
# Receiver listens
ffmpeg -i "srt://:9000?mode=listener&latency=120000" -c copy out.ts

# Sender caller
ffmpeg -i input.mp4 -c copy -f mpegts "srt://receiver:9000?mode=caller&latency=120000"
```

### Multicast MPEG-TS (LAN distribution)

```bash
ffmpeg -re -i input.mp4 -c copy \
  -f mpegts "udp://239.0.0.1:1234?pkt_size=1316&ttl=1"
```

Receiver:
```bash
ffplay "udp://239.0.0.1:1234"
```

---

## Gotchas

- **`-movflags +faststart` runs a *second pass* to move moov atom to the front.** If you don't include it, progressive playback stalls until the full file downloads. For fragmented MP4 this flag is irrelevant — fMP4 is already progressive.
- **`-hls_time` is a *target* — keyframe alignment determines actual segment duration.** If `-g` isn't set, ffmpeg picks keyframes where it wants. Force with `-g <fps * hls_time>` and `-keyint_min` to match, plus `-sc_threshold 0` to disable scene-change cuts.
- **`independent_segments` flag is required for CMAF/LL-HLS.** Without it, a segment may depend on a prior segment's reference frames — breaks ABR switching mid-segment.
- **HLS AES-128 encrypts the segment payload only, not the playlist.** The key URI in the M3U8 is plaintext. Protect it with server-side auth (signed URLs, origin auth).
- **`-hls_key_info_file` must have the trailing newline** on the IV line. Some editors strip it silently.
- **Widevine L1 requires a CDM** (ChromeOS, Android hardware TEE). You cannot "test Widevine L1 locally." Test with L3 (software) in Chrome Stable.
- **FairPlay uses `cbcs` scheme (AES-CBC sample encryption).** Widevine/PlayReady default to `cenc` (AES-CTR). If you ship one unified CMAF + CENC for all three, you must use `cbcs` and have encoder keys that work with all three DRMs. Shaka Packager's `--protection_scheme cbcs` handles this.
- **CMAF audio must be fMP4, not TS.** Mixed TS-video + fMP4-audio HLS playlists break on most players. Stay consistent.
- **WHIP endpoint must be HTTPS in production.** Chrome refuses `getUserMedia` + WebRTC over http (except localhost). FFmpeg's WHIP client allows http, but the receiver (browser) won't.
- **FFmpeg WHIP requires FFmpeg 7+.** The `ffmpeg-whip` skill explicitly checks. Older builds silently fail.
- **MediaMTX listens on many ports.** Default 1935 (RTMP), 8554 (RTSP), 8888 (HLS), 8889 (WebRTC), 8890 (SRT), 9997 (API). Open all you plan to use in the firewall.
- **MediaMTX /v3/* Control API requires `api: yes` in config.** Off by default.
- **`-re` flag reads input at native framerate** — essential for live streaming from a file. Without it, ffmpeg reads as fast as possible and saturates the ingest.
- **`-f flv` is required for RTMP**. Without it, ffmpeg picks the wrong muxer.
- **RTMP chunk size defaults to 128 bytes.** For 4K/HEVC you want `-rtmp_chunk_size 4096`. Below that, overhead kills throughput.
- **`-g` (GOP) must match `-hls_time * fps`** for clean segment boundaries. At 30fps with 4s segments: `-g 120 -keyint_min 120 -sc_threshold 0`.
- **AAC LC + mono is 64k minimum, AAC LC stereo is 96k minimum** for transparent quality. Below those thresholds, use HE-AAC (`-profile:a aac_he`) instead.
- **`aac_adtstoasc` bitstream filter is required when muxing TS to MP4** — otherwise, AAC stream is wrong format. `ffmpeg-bitstream` covers this.
- **LiveKit JWT tokens expire.** Default 6 hours. For long-lived rooms, mint new tokens client-side on refresh.
- **Pion SFU needs turn/stun for NAT traversal.** Set `ICEServers` in the config, or remote peers never connect.
- **mediasoup requires Node 18+** and `libmediasoupworker` native build. The worker binary is platform-specific.

---

## Example — "live HLS ABR with AES-128 to Cloudflare"

```bash
#!/usr/bin/env bash
# abr-aes-cloudflare.sh

INPUT="input.mp4"
OUT_DIR="./hls"
KEY_URI="https://stream.example.com/key"
KEY_FILE="./key.bin"
IV=$(openssl rand -hex 16)

# 1. Generate encryption key
openssl rand 16 > "$KEY_FILE"
cat > key.info <<EOF
$KEY_URI
$KEY_FILE
$IV
EOF

# 2. Encode + encrypt
mkdir -p "$OUT_DIR"
ffmpeg -i "$INPUT" \
  -filter_complex "[0:v]split=3[v1][v2][v3]; \
    [v1]scale=1920:1080[v1out]; \
    [v2]scale=1280:720[v2out]; \
    [v3]scale=854:480[v3out]" \
  -map "[v1out]" -c:v:0 libx264 -b:v:0 5M \
  -map "[v2out]" -c:v:1 libx264 -b:v:1 3M \
  -map "[v3out]" -c:v:2 libx264 -b:v:2 1.5M \
  -map a:0 -c:a aac -b:a 128k \
  -map a:0 -c:a aac -b:a 128k \
  -map a:0 -c:a aac -b:a 96k \
  -g 120 -keyint_min 120 -sc_threshold 0 \
  -f hls -hls_time 4 \
  -hls_flags independent_segments \
  -hls_key_info_file key.info \
  -master_pl_name master.m3u8 \
  -hls_segment_filename "$OUT_DIR/v%v/seg_%03d.ts" \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" \
  "$OUT_DIR/v%v/playlist.m3u8"

# 3. Upload to Cloudflare R2 / Stream
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --provider cloudflare-r2 \
  --bucket vod-streams --prefix live/$(date +%s)/ \
  --dir "$OUT_DIR"
```

---

## Further reading

- [`live-production.md`](live-production.md) — the OBS/contribution side of the stream
- [`broadcast-delivery.md`](broadcast-delivery.md) — broadcast-grade MXF/IMF origination
- [`analysis-quality.md`](analysis-quality.md) — VMAF-driven ABR ladder tuning
- [`hdr-workflows.md`](hdr-workflows.md) — HDR streaming (HLG / HDR10 / Dolby Vision)
