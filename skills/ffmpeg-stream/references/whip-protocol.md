# WHIP Reference — ffmpeg WebRTC Egress

## 1. Protocol handshake (what the `whip` muxer actually does)

WHIP (WebRTC-HTTP Ingestion Protocol, IETF `draft-ietf-wish-whip`) is a thin HTTP signaling shell around a WebRTC PeerConnection.

```
Client (ffmpeg)                              Server (WHIP endpoint)
       |                                              |
       | HTTP POST <endpoint>                         |
       | Content-Type: application/sdp                |
       | Authorization: Bearer <token>                |
       | <SDP offer>                                  |
       |--------------------------------------------->|
       |                                              |
       |       201 Created                            |
       |       Location: <resource-url>               |
       |       Content-Type: application/sdp          |
       |       <SDP answer>                           |
       |<---------------------------------------------|
       |                                              |
       | ICE / DTLS / SRTP media (UDP)                |
       |<============================================>|
       |                                              |
       | HTTP DELETE <resource-url>  (on shutdown)    |
       |--------------------------------------------->|
```

- **Offer** is built by ffmpeg from the encoder output (codecs, RTP payload types, ICE ufrag/pwd, DTLS fingerprint).
- **Answer** tells ffmpeg which candidate(s) to hit and the server's DTLS fingerprint.
- Media flows over SRTP (encrypted RTP). DTLS-SRTP derives the keys.
- Graceful shutdown = `DELETE` the resource URL; ungraceful = ICE timeout on server side (~30s).

## 2. Required encoder constraints

WebRTC is stricter than RTMP/HLS because browsers (the ultimate receivers) are picky.

| Dimension      | Allowed                            | Not allowed                    |
|----------------|------------------------------------|--------------------------------|
| Video codec    | H.264 (AVC)                        | HEVC, VP9, AV1 (most impls)    |
| H.264 profile  | `baseline`, `main`                 | `high` (often rejected)        |
| B-frames       | None                               | Any B-frames                   |
| GOP            | Fixed 1–2s (`-g 60` @ 30fps)       | Variable, `-sc_threshold > 0`  |
| Pixel format   | `yuv420p`                          | yuv422p, yuv444p, NV12         |
| Audio codec    | Opus (`libopus`)                   | AAC, MP3, AC3                  |
| Opus rate      | 48000 Hz                           | 44100 Hz (silently resampled)  |
| Channels       | 1 or 2                             | 5.1, 7.1                       |
| Bitrate ceiling| ~6 Mbps practical                  | Higher — congestion control throttles |

`-tune zerolatency` disables x264's lookahead and B-frames; combined with `-profile:v baseline` and fixed GOP it produces a WebRTC-safe bitstream.

## 3. Platform URL patterns

### Cloudflare Stream (WHIP)
```
POST https://customer-<account-hash>.cloudflarestream.com/<SRT-key>/webRTC/publish
```
Auth: the URL itself is the secret (it embeds the stream key). No extra header required. Playback via Cloudflare's WHEP URL or HLS/DASH mirror.

### Mux Live (WHIP)
```
POST https://global-live.mux.com/api/whip/<stream-key>
```
Auth: stream key in URL. Optional `Authorization: Bearer <token>` depending on account config.

### Millicast / Dolby.io
```
POST https://director.millicast.com/api/whip/<stream-name>
Authorization: Bearer <publish-token>
```
Two-step: call Director API first to resolve the regional WHIP URL, then POST SDP.

### MediaMTX (self-hosted, recommended for dev)
```
POST http://localhost:8889/<path>/whip
```
Config in `mediamtx.yml`:
```yaml
paths:
  live:
    source: publisher
```
Playback at `http://localhost:8889/live` in a browser (built-in WHEP player).

### Pion BroadcastBox
```
POST http://localhost:8080/api/whip?streamKey=<key>
```
Open-source Go reference server. Useful for end-to-end testing.

### Janus WebRTC Server
Requires the `janus-pp-whip` plugin; URL shape varies by deployment.

## 4. Authentication patterns

| Pattern              | How to pass with ffmpeg                                         |
|----------------------|-----------------------------------------------------------------|
| Bearer token         | `-headers "Authorization: Bearer $TOK"$'\r\n'`                  |
| Query-param token    | Append `?token=...` to endpoint URL                             |
| URL path secret      | Endpoint URL itself carries the stream key (Cloudflare, Mux)    |
| Custom header        | `-headers "X-API-Key: $KEY"$'\r\n'`                             |
| Multiple headers     | Concatenate with `\r\n` between each; trailing `\r\n` on last   |

CRLF termination is not optional — ffmpeg passes the string through raw to the HTTP layer.

## 5. Latency expectations

| Transport      | Glass-to-glass latency | Reliability under loss |
|----------------|------------------------|------------------------|
| WHIP / WebRTC  | 100–500 ms             | RTX, NACK, adaptive br.|
| SRT            | 200 ms – 2 s           | ARQ, good              |
| RTMP           | 2 – 5 s                | TCP, good              |
| LL-HLS         | 2 – 6 s                | HTTP, excellent        |
| HLS / DASH     | 6 – 30 s               | HTTP, excellent        |

Achieving sub-500ms requires: good network path, regional endpoint, ≤2s GOP, hardware encoder or fast CPU, no extra re-muxing hops.

## 6. WHIP vs RTMP — when to switch

Use **WHIP** when:
- Viewers are in a browser with a WHEP player.
- Latency budget is <1s (auctions, betting, interactive Q&A, sports telestrator).
- Bitrate ≤ ~6 Mbps.

Stay on **RTMP** when:
- Target is YouTube Live, Twitch, Facebook (these still prefer RTMP).
- Bitrate is 8–20 Mbps (4K live, high-motion sport).
- Encoder is legacy and only speaks RTMP.
- You need HLS/DASH output (which the CDN derives from RTMP).

Often both are useful: push RTMP to a CDN for mass audience + WHIP to a realtime side-channel for host interaction.

## 7. Debugging

### On the publisher side (ffmpeg)
```bash
ffmpeg -loglevel debug [...] -f whip '<url>' 2>&1 \
  | grep -Ei 'http|sdp|ice|candidate|dtls|stun|turn'
```
Look for:
- `HTTP/1.1 201 Created` and a `Location:` header = signaling OK.
- `a=candidate:` lines in the SDP answer = the server's ICE endpoints.
- `ICE connection state change` → `connected` = NAT traversal succeeded.
- `DTLS handshake completed` = media path encrypted and ready.

### On the receiver side (browser)
- Open `chrome://webrtc-internals` (Edge: `edge://webrtc-internals`).
- Watch the inbound-rtp graphs: `framesReceived`, `packetsLost`, `jitter`, `keyFramesDecoded`.
- If `framesDecoded == 0` but packets arrive → codec/profile mismatch. Force `baseline`.
- If packet loss > 1% → congestion; lower `-b:v`.

### Wireshark
Filter: `stun || dtls || (udp && not ssdp)`. Capture on the publisher NIC. Useful to confirm ICE pairs and spot where UDP is being dropped (firewall/NAT).

### Quick MediaMTX loopback test
```bash
docker run --rm -it --network=host bluenviron/mediamtx:latest
uv run scripts/whip.py check-build
uv run scripts/whip.py publish --input clip.mp4 \
  --endpoint http://localhost:8889/live/whip
# Open http://localhost:8889/live in the browser.
```

## 8. When NOT to use WHIP

- **Archival / VOD** — use HLS/DASH; WHIP has no concept of segments or rewind.
- **4K high-bitrate live** — WebRTC's congestion control caps you; RTMP/SRT are better.
- **Very lossy networks (mobile uplink < 1 Mbps)** — still feasible but expect heavy quality reductions.
- **Receivers without a WHEP player** — WHIP publish is useless without a matching egress.
- **FFmpeg < 7.0** — muxer simply doesn't exist; upgrade or pick RTMP/SRT.

## 9. Further reading

- FFmpeg whip muxer docs: <https://ffmpeg.org/ffmpeg-formats.html#whip>
- WHIP IETF draft: <https://datatracker.ietf.org/doc/draft-ietf-wish-whip/>
- WHEP (playback counterpart): <https://datatracker.ietf.org/doc/draft-murillo-whep/>
- MediaMTX WHIP/WHEP guide: <https://github.com/bluenviron/mediamtx#webrtc>
- Cloudflare Stream WHIP: <https://developers.cloudflare.com/stream/webrtc-beta/>
- Millicast WHIP: <https://docs.dolby.io/streaming-apis/docs/webrtc-https-ingest-whip>
