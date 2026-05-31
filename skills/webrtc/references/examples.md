# Pion Canonical Examples

All under `https://github.com/pion/webrtc/tree/master/examples`. Fetch any one with `pion.py fetch-example <name> --dest DIR`.

## Media flows

- **broadcast** — Minimal 1-to-N SFU. Publisher POSTs offer → server; subscribers do the same and receive the forwarded track. Smallest working SFU in the repo.
- **sfu-ws** — WebSocket-signaled SFU. Adds mid-session track join/leave.
- **simulcast** — Shows how to ingest a simulcasted publisher and forward selected layers.
- **play-from-disk** — Read a VP8 IVF and Opus Ogg file from disk, send over WebRTC.
- **play-from-disk-h264** — Same but with H.264 Annex-B; uses `NewTrackLocalStaticSample`.
- **save-to-disk** — Receive tracks, persist VP8 to `.ivf` and Opus to `.ogg`.
- **save-to-webm** — Mux to a WebM container instead of separate files.
- **reflect** — Receive a track, send it straight back (useful for echo testing).
- **pion-to-pion** — Two Pion instances connecting over the loopback; good for library familiarity.

## Data channels

- **data-channels** — Basic SCTP open + message echo.
- **data-channels-detach** — `dc.Detach()` to get an `io.ReadWriter` for bulk streams.
- **data-channels-close** — Clean four-way close handshake.

## ICE + signaling

- **ice-tcp** — ICE over TCP (firewall-hostile networks).
- **ice-single-port** — Multiplex every PeerConnection's candidate onto one UDP port. Standard SFU deployment pattern.
- **ice-restart** — Trigger ICE restart mid-session after an interface change.
- **trickle-ice** — Explicit trickle-ICE signaling with `OnICECandidate` round-trip.

## WHIP / WHEP

- **whip-whep** — Self-contained HTTP server. POST `/whip` with an SDP offer → 201 + Location header + answer body. GET `/whep` receives the forwarded stream. Works with `ffmpeg -f whip`.

## Observability / advanced

- **insertable-streams** — Encoded-frame transform hooks (E2EE, watermarks, custom codec post-processing).
- **rtp-forwarder** — Receive over WebRTC, forward RTP to a plain UDP socket (bridge to GStreamer / ffmpeg).
- **rtp-to-webrtc** — Inverse: ingest raw RTP, wrap as a WebRTC track.
- **stats** — Dump `RTCStatsReport` periodically. Good template for dashboards.
- **custom-logger** — Plug a custom logger.
- **swap-tracks** — Replace an outgoing track without renegotiation using `RTPSender.ReplaceTrack`.

## Running checklist

1. `pion.py fetch-example <name> --dest DIR`.
2. `cd DIR/examples/<name>`.
3. `go build ./...` — should pull modules automatically.
4. `go run ./...` — example-specific flags via `-h`.

The upstream repo's example READMEs are authoritative — open `github.com/pion/webrtc/tree/master/examples/<name>` in a browser for the current instructions.
