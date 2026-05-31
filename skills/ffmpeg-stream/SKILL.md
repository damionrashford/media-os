---
name: ffmpeg-stream
description: >
  Package and stream live or file media with ffmpeg across every delivery and contribution protocol. Use when the user asks to stream to YouTube, Twitch, or Facebook Live, push RTMP or RTMPS, go live, generate HLS segments or an m3u8, build a DASH mpd manifest, make an ABR ladder, set up low-latency SRT, publish to a WHIP WebRTC endpoint for sub-second delivery to Cloudflare or Mux or Millicast, send RIST contribution with ARQ and bonded paths, control a live filter graph over ZMQ, add prompeg FEC to RTP, push to an Icecast radio, send UDP multicast or RTSP or RTP, or output one encode to many destinations with the tee muxer.
argument-hint: "[protocol] [input]"
---

# Ffmpeg Stream

Package and deliver media over every ffmpeg streaming + contribution protocol: HLS, DASH, RTMP/RTMPS, SRT, RTSP, RTP, UDP, tee multi-output, WHIP (WebRTC), RIST, ZMQ filter control, prompeg FEC, and Icecast.

**When invoking any ffmpeg flag or filter, consult the `ffmpeg-docs` skill first — it is the anti-hallucination guardrail.**

## When to use

- Push a live encoder to a platform ingest (YouTube, Twitch, Facebook, Mux, Wowza, nginx-rtmp) over RTMP/RTMPS.
- Package a file or live source into HLS / DASH for browser/mobile playback, including ABR ladders with a master playlist.
- Sub-second WebRTC delivery to a WHIP ingest (Cloudflare Stream, Mux, Millicast, MediaMTX) with WHEP playback.
- Low-latency contribution: SRT, RIST (ARQ + bonded multipath), RTP+prompeg FEC.
- Re-tune a running filter graph live (drawtext, volume, crop) over ZMQ without restarting ffmpeg.
- Internet radio to Icecast, LAN one-to-many UDP multicast, or RTSP/RTP private-network links.
- Fan one encode out to many destinations at once with the tee muxer.

## Techniques

- Read `references/streaming.md` when the target is HLS, DASH, RTMP/RTMPS, SRT, RTSP, RTP, UDP, or the tee muxer — covers VOD vs live playlists, fMP4/CMAF, ABR ladders, platform ingest URLs, and `stream.py`.
- Read `references/muxers.md` when you need the full option catalog for hls/dash/tee/rtmp/srt/rtsp/udp/rtp, the keyframe-interval math table, the latency ladder, or LL-HLS notes.
- Read `references/whip.md` when publishing to a WHIP WebRTC endpoint (FFmpeg 7.0+) — WebRTC encoder constraints, Bearer/CRLF auth, platform URLs, screen+mic capture, and `whip.py`.
- Read `references/whip-protocol.md` when you need the WHIP handshake detail, per-platform auth schemes, or the WHIP-vs-RTMP decision matrix.
- Read `references/rist-zmq.md` when the target is RIST contribution, ZMQ runtime filter control, prompeg FEC over RTP, Icecast radio, or UDP multicast — caller/listener roles and `advproto.py`.
- Read `references/advproto.md` when you need the RIST profile comparison, RIST/ZMQ/Icecast option catalogs, prompeg FEC sizing math, or the recipe book.

## Gotchas

- **GOP = fps × segment_time, forced both ways.** 30 fps × 2 s → `-g 60 -keyint_min 60`. `-g` alone permits variable GOPs. This applies to HLS, DASH, RTMP, SRT, RIST, and WHIP alike.
- **`-sc_threshold 0` is REQUIRED on libx264** for HLS/DASH/WebRTC — a scene-cut keyframe otherwise inserts an extra IDR and segments misalign (`EXT-X-DISCONTINUITY`, broken ABR switching, WebRTC jitter-buffer breakage).
- **TS→MP4 needs `aac_adtstoasc`.** When remuxing an MPEG-TS capture (SRT/RIST/UDP) into MP4 with `-c copy`, apply `-bsf:a aac_adtstoasc` or playback fails on the AAC track.
- **`-re` for file inputs, NEVER for true live capture.** It real-time-paces a file so it behaves like a feed; on a live camera it double-rate-limits and desyncs.
- **RTMP must be `-f flv`, H.264 + AAC-LC only**, 44.1/48 kHz stereo. WHIP is even stricter: H.264 baseline/main + Opus at 48 kHz, no B-frames, `-pix_fmt yuv420p` mandatory, FFmpeg 7.0+ only.
- **HLS `-hls_flags delete_segments` only works when `-hls_playlist_type` is unset or `event`**, never `vod`. ABR needs stream-specific flags (`-c:v:0`, `-b:v:0`, …) and `-var_stream_map` with space-separated `v:N,a:N` groups referencing output indexes.
- **SRT `latency` is microseconds** (120000 = 120 ms, min ≈ 2×RTT); **RIST `buffer_size` is milliseconds** (0–30000, ≈ 2×RTT). Don't confuse the units.
- **MPEG-TS `pkt_size` must be a multiple of 188** — default `1316` (7×188) fits a 1500-MTU frame. prompeg works only with `rtp_mpegts` and `L×D ≤ 100`; UDP multicast TTL defaults to 1 (link-local). Tee's `|` separator must be quoted, and `onfail=ignore` keeps one dead sink from killing the run.

## Scripts

- **`scripts/stream.py`** — subcommands `rtmp`, `hls-vod`, `hls-live`, `hls-abr`, `dash`, `srt-listener`, `srt-caller`, `tee`. Prints the ffmpeg command; `--dry-run` / `--verbose`.
- **`scripts/whip.py`** — subcommands `check-build`, `publish`, `publish-screen` for WHIP WebRTC egress with WebRTC-safe encoder defaults. `--dry-run` / `--verbose`.
- **`scripts/advproto.py`** — subcommands `check`, `rist-send`, `rist-listen`, `zmq-serve`, `zmq-send`, `rtp-fec`, `icecast`, `multicast`. `--dry-run` / `--verbose`.

All three are stdlib-only and print the exact ffmpeg command to stderr before executing. Run with `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py <subcommand> [flags]`.
