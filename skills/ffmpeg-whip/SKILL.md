---
name: ffmpeg-whip
description: >
  WebRTC egress with ffmpeg whip muxer (FFmpeg 7.0+): publish live AV to a WHIP (WebRTC-HTTP Ingestion Protocol) endpoint, low-latency sub-second delivery, encoder constraints (H.264 baseline/main, Opus audio), ICE/STUN handling. Use when the user asks to push to WHIP, stream via WebRTC, publish to a WebRTC ingest endpoint, send sub-second live to Cloudflare/Mux/Millicast, output to a WHIP URL, or do browser-playable live streaming without HLS/DASH.
argument-hint: "[whip-endpoint]"
---

# Ffmpeg WHIP

**Context:** $ARGUMENTS

WebRTC publish via ffmpeg's `whip` muxer (FFmpeg 7.0+). Sub-second glass-to-glass live delivery to any WHIP-compatible ingest (Cloudflare Stream, Mux, Millicast/Dolby.io, MediaMTX, self-hosted Pion/Janus).

## Quick start

- **Verify build supports whip:** → Step 1
- **Encoder flags for WebRTC:** → Step 2
- **Publish a file as live:** → Step 3, Example 1
- **Publish live screen + mic capture:** → Step 3, Example 2
- **Debug connection / ICE failure:** → Step 4, Troubleshooting

## When to use

- You need sub-second (<500ms) live latency.
- Your platform exposes a WHIP ingest URL (Cloudflare Stream WHIP, Mux, Millicast, MediaMTX, OBS-compatible servers).
- The viewer side is a browser using WebRTC (WHEP playback).
- You explicitly want to avoid RTMP's 2-5s latency or HLS/DASH's 5-30s.

**Do NOT use** for archival VOD (use HLS/DASH), 4K/high-bitrate (RTMP is more robust), or when the target only accepts RTMP.

## Step 1 — Verify ffmpeg 7.0+ with whip muxer

WHIP landed in **FFmpeg 7.0** (April 2024). Older builds do not have it at all — no flag or patch makes it work. Homebrew sometimes lags; check explicitly.

```bash
ffmpeg -version | head -1                    # need "ffmpeg version 7.0" or higher
ffmpeg -muxers 2>/dev/null | grep -i whip    # must print: E whip WHIP ...
ffmpeg -h muxer=whip                          # see all whip-specific options
```

If `whip` is absent: upgrade (`brew upgrade ffmpeg`, or build from source / grab a static build from `johnvansickle.com` / BtbN/FFmpeg-Builds).

Helper: `uv run ${CLAUDE_SKILL_DIR}/scripts/whip.py check-build`.

## Step 2 — Encoder constraints for WebRTC

WebRTC codec support is **much stricter** than RTMP/HLS. Required:

| What            | Required value                                    |
|-----------------|---------------------------------------------------|
| Video codec     | `libx264` (H.264). No HEVC, no VP9, no AV1.       |
| H.264 profile   | `baseline` (safest) or `main`. **No B-frames.**   |
| GOP             | `-g 60 -keyint_min 60 -sc_threshold 0` (2s @ 30fps)|
| Tune            | `-tune zerolatency`                               |
| Preset          | `veryfast` or `ultrafast` (real-time CPU budget)  |
| Pixel format    | `-pix_fmt yuv420p` (mandatory)                    |
| Audio codec     | `libopus`. No AAC.                                |
| Sample rate     | `-ar 48000` (Opus standard)                       |
| Channels        | `-ac 2` (stereo) or `-ac 1` (mono)                |
| Audio bitrate   | `-b:a 128k` (96k–128k typical)                    |
| Video bitrate   | 2500k @ 720p30, 4500k @ 1080p30, 6000k @ 1080p60  |

Constant bitrate is strongly recommended for WebRTC congestion control: `-b:v X -maxrate X -bufsize 2X`.

## Step 3 — Build and run the publish command

### Example 1: Publish a file as live

```bash
ffmpeg -re -i source.mp4 \
  -c:v libx264 -profile:v baseline -preset veryfast -tune zerolatency \
  -g 60 -keyint_min 60 -sc_threshold 0 \
  -b:v 2500k -maxrate 2500k -bufsize 5000k -pix_fmt yuv420p \
  -c:a libopus -b:a 128k -ar 48000 -ac 2 \
  -f whip 'https://whip.example.com/endpoint?token=XYZ'
```

`-re` reads at real-time wall-clock rate — required when the input is a file and you want it to behave like a live feed. **Omit `-re` for actual live capture** (camera/screen/mic already arrive in real time).

### Example 2: Publish live screen + mic (macOS avfoundation)

```bash
ffmpeg -f avfoundation -framerate 30 -i "1:0" \
  -c:v libx264 -profile:v baseline -preset veryfast -tune zerolatency \
  -g 60 -keyint_min 60 -sc_threshold 0 \
  -b:v 3000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p \
  -c:a libopus -b:a 128k -ar 48000 -ac 2 \
  -headers "Authorization: Bearer $TOKEN"$'\r\n' \
  -f whip 'https://whip.example.com/endpoint'
```

Linux: swap `-f avfoundation -i "1:0"` for `-f x11grab -i :0.0 -f pulse -i default`.
Windows: swap for `-f gdigrab -i desktop -f dshow -i audio="Mic"`.

See the `ffmpeg-capture` skill for platform-specific device indexes.

### Bearer auth

Most WHIP endpoints require `Authorization: Bearer <token>`. Pass via `-headers`:

```bash
-headers "Authorization: Bearer ${TOKEN}"$'\r\n'
```

The trailing `\r\n` matters — HTTP headers must be CRLF-terminated. Use ANSI-C `$'\r\n'` in bash/zsh.

### Platform URL patterns

| Platform            | URL shape                                                                 |
|---------------------|----------------------------------------------------------------------------|
| Cloudflare Stream   | `https://customer-<id>.cloudflarestream.com/<SRTKey>/webRTC/publish`       |
| Mux                 | `https://global-live.mux.com/api/whip/<stream-key>`                        |
| Millicast / Dolby   | `https://director.millicast.com/api/whip/<stream-name>` + Bearer header    |
| MediaMTX (self)     | `http://localhost:8889/<path>/whip`                                        |
| Pion/Broadcast Box  | `http://localhost:8080/api/whip?streamKey=<key>`                           |

See `references/whip.md` for per-platform auth details.

### Hardware encoder swap (1080p60 on modest CPU)

Replace `-c:v libx264 -preset veryfast -tune zerolatency` with:

- macOS: `-c:v h264_videotoolbox -realtime 1`
- NVIDIA: `-c:v h264_nvenc -preset p1 -tune ll -zerolatency 1`
- Intel QSV: `-c:v h264_qsv -preset veryfast -low_power 1`

Still keep `-profile:v baseline`, `-g 60 -keyint_min 60`, `-pix_fmt yuv420p`.

## Step 4 — Verify the connection

Run with `-loglevel debug` to see the SDP offer/answer exchange:

```bash
ffmpeg -loglevel debug [...full command...] 2>&1 | grep -Ei 'whip|sdp|ice|stun|http'
```

Success looks like:
1. `HTTP/1.1 201 Created` with a `Location:` header (the WHIP resource URL).
2. SDP answer logged containing `a=candidate:` lines.
3. ICE connectivity check completes, then packets flow.

Play back on the **same platform's WHEP endpoint** from a browser — `ffplay` cannot consume WHIP/WHEP. For Cloudflare, open the dashboard; for MediaMTX open `http://localhost:8889/<path>`; for Pion/BroadcastBox use their web player.

To stop the publish cleanly, `Ctrl-C` — ffmpeg will `DELETE` the resource URL.

## Available scripts

- **`scripts/whip.py check-build`** — reports ffmpeg version and whether the `whip` muxer is present.
- **`scripts/whip.py publish`** — builds the full publish command for a file input with sensible WebRTC encoder defaults. `--dry-run` prints the command without executing.
- **`scripts/whip.py publish-screen`** — same for platform screen + mic capture (picks avfoundation / x11grab / gdigrab by OS).

Both publish subcommands accept `--bitrate`, `--resolution`, `--fps`, `--token`, `--verbose`, `--dry-run`.

## Reference docs

- Read [`references/whip.md`](references/whip.md) for the WHIP handshake, per-platform URL patterns, auth schemes, and RTMP/HLS comparison.

## Gotchas

- **FFmpeg 7.0+ only.** No backport. `ffmpeg -muxers | grep whip` is the gate.
- **Codec allow-list is tiny:** H.264 baseline/main + Opus. No AAC, no HEVC, no VP9, no AV1.
- **No B-frames.** `-profile:v baseline` guarantees this; `main` also works for most receivers.
- **GOP must be low and fixed:** `-g 60 -keyint_min 60 -sc_threshold 0` (or 30 for 15fps). Variable-GOP breaks WebRTC jitter buffer.
- **`-pix_fmt yuv420p` is mandatory.** Not yuv422p, not yuv444p, not NV12.
- **Opus only at 48 kHz, mono or stereo.** 44.1 kHz will get resampled or rejected.
- **TURN relay may be missing.** FFmpeg's WHIP muxer does STUN/ICE but TURN support depends on build. Symmetric NAT without TURN = no connection.
- **`-re` for file inputs, NOT for live capture.** Using `-re` on a live camera double-rate-limits and desyncs.
- **CRLF on `-headers`:** end with `$'\r\n'`, not `\n`, or the server rejects the header.
- **Endpoint URL vs resource URL.** You POST to the endpoint; the server returns a resource URL via `Location:`. ffmpeg sends `DELETE` to the resource URL on shutdown.
- **WHIP is publish-only.** To view, use a WHEP player on the same platform. `ffplay <whip-url>` does not work.
- **Region matters.** Pick the geographically closest regional endpoint or latency balloons.
- **Preset must be `veryfast`/`ultrafast`** on CPU, or you drop frames under real-time.
- **Bitrate ceiling:** WebRTC congestion control throttles at ~6 Mbps. For 4K/high-bitrate, use RTMP/SRT instead.

## Troubleshooting

### Error: `Unknown output format: whip`

**Cause:** ffmpeg version < 7.0 or built without WHIP.
**Fix:** Upgrade (`brew upgrade ffmpeg`) or install a 7.0+ static build.

### Error: `HTTP error 401 Unauthorized`

**Cause:** Missing or malformed Bearer token.
**Fix:** Add `-headers "Authorization: Bearer $TOKEN"$'\r\n'` with the correct CRLF terminator. Verify the token with `curl -v -X POST -H "Authorization: Bearer $TOKEN" <whip-url>`.

### Error: `ICE connection failed` / no video arrives

**Cause:** NAT traversal failed. STUN alone is not enough behind symmetric NAT.
**Fix:** Use a WHIP provider that proxies media (Cloudflare, Mux) or deploy a TURN server and use a ffmpeg build that supports the muxer's TURN options. Test from a different network.

### Error: `non-monotonic DTS`, stream stalls after a few seconds

**Cause:** B-frames or variable GOP slipped in.
**Fix:** Force `-profile:v baseline -bf 0 -g 60 -keyint_min 60 -sc_threshold 0`.

### Error: `Could not find codec parameters for stream`

**Cause:** Wrong audio codec (AAC) or wrong pixel format.
**Fix:** `-c:a libopus -ar 48000` and `-pix_fmt yuv420p`.

### Publish starts, viewer sees black / no audio

**Cause:** Profile mismatch — receiver can't decode. Usually `high` profile sent.
**Fix:** Explicitly `-profile:v baseline` (or `main`) and `-level 4.1`.

### Debugging the handshake

```bash
ffmpeg -loglevel trace -re -i test.mp4 [encoder flags] -f whip '<url>' 2>&1 \
  | grep -Ei 'http|sdp|ice|candidate|dtls|offer|answer'
```

On the **receiving** side, open `chrome://webrtc-internals` in the browser playing the WHEP stream to see inbound RTP stats, packet loss, jitter, and the negotiated codecs.
