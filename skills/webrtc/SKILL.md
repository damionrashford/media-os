---
name: webrtc
description: >
  Build and ship WebRTC: W3C WebRTC 1.0 + IETF RFCs (RTCPeerConnection, SDP RFC 8866, ICE RFC 8445, JSEP RFC 9429, DTLS-SRTP, WHIP RFC 9725, WHEP, simulcast, getUserMedia, WebCodecs), Pion (Go library — PeerConnection, MediaEngine, tracks, DataChannel, interceptors, TURN, runnable examples: broadcast, sfu-ws, save-to-disk, whip-whep, insertable-streams), mediasoup (Node.js SFU — Worker/Router/Transport/Producer/Consumer, PlainTransport ffmpeg bridge, simulcast, BYO signaling), LiveKit (Apache-2.0 Go SFU binary — JWT grant tokens, livekit-cli, egress record/stream-out, ingress RTMP/WHIP/SRT, SDK matrix, Agents). Use when the user asks to look up an SDP attribute or RFC, verify an ICE/DTLS behavior, write a WebRTC server in Go, build an SFU from scratch, implement WHIP/WHEP, save WebRTC tracks to disk, spin up a Node.js video-conferencing SFU, bridge mediasoup to ffmpeg, run a LiveKit server, mint room tokens, record or ingest a LiveKit room, or build a meeting-room backend.
argument-hint: "[query]"
---

# WebRTC

Build, debug, and ship WebRTC — from the wire protocol (W3C + IETF specs) up through three production SFU stacks (Pion, mediasoup, LiveKit). Pick the layer the task needs: spec lookup for correctness, Pion to build from scratch in Go, mediasoup for a Node.js SFU you control, LiveKit for a batteries-included Go binary.

## When to use

- Look up an SDP attribute, RFC number, ICE/DTLS/JSEP/WHIP behavior, or browser-API signature — read `references/spec.md`.
- Write a WebRTC server in Go, build an SFU from scratch, implement WHIP/WHEP, save tracks to disk, insertable streams — read `references/pion.md`.
- Stand up a Node.js video-conferencing SFU you fully control, bridge RTP to ffmpeg/GStreamer — read `references/mediasoup.md`.
- Deploy a single-binary SFU with broad SDK coverage, token minting, recording, ingest, or AI agents — read `references/livekit.md`.

## Techniques

- Read `references/spec.md` when verifying an SDP attribute, RFC number, ICE/DTLS/JSEP behavior, WHIP/WHEP details, or a W3C WebRTC 1.0 / getUserMedia / WebCodecs API. This is the anti-hallucination guardrail — verify protocol claims here first.
- Read `references/pion.md` when building a WebRTC server in Go with `pion/webrtc/v4`, fetching/building the canonical examples, or embedding a TURN server.
- Read `references/mediasoup.md` when hosting a Node.js SFU with Worker/Router/Transport/Producer/Consumer or bridging plain RTP via PlainTransport.
- Read `references/livekit.md` when running `livekit-server`, minting JWT grant tokens, using `lk` CLI, or wiring egress/ingress sidecars.

## Gotchas

- **SDP is RFC 8866, not 4566** (4566 is obsoleted, 2020). JSEP prefers RFC 9429 over 8829. WHIP is final (RFC 9725); WHEP is still a draft.
- **Pion: always use `github.com/pion/webrtc/v4`.** `Sample.Duration` must be `time.Second/fps` or RTP timestamps break; construct via `webrtc.NewAPI(...)`, never the zero value.
- **mediasoup `announcedIp` is critical in NAT deployments** — it populates `a=candidate` lines and must be the public address. One Worker per physical core; the `on('died')` handler is mandatory.
- **LiveKit tokens are HS256 JWTs with a mandatory `exp`** — RS256 or missing `exp` → 401 at room join. The dev key `devkey:secret` is insecure for anything internet-reachable.
- **Simulcast needs explicit per-encoding `rid`s** everywhere — Pion `SendEncodings`, mediasoup `encodings:[{rid:...}]`, LiveKit browser publishers (on by default). Forgetting drops upper layers.
- **`ICE failed` after deploy** almost always means no/unreachable TURN, a private `listenIp`/`announcedIp`, or a blocked UDP port range plus no TCP fallback.
- **DTLS fingerprint comparison is case-insensitive and colon-separated** — if signaling rewrites SDP, preserve the colons.
- **`use_external_ip:true` (LiveKit) reads cloud metadata endpoints** on AWS/GCP/Azure; set `node_ip` manually on-prem.

## Scripts

- `scripts/webrtcdocs.py` — search/fetch W3C + IETF WebRTC specs (`search`, `section`, `fetch`, `list-rfcs`, `list-pages`, `index`).
- `scripts/pion.py` — fetch/build/run Pion examples (`check`, `list-examples`, `fetch-example`, `build`, `run`, `whip`, `whep`).
- `scripts/mediasoup.py` — scaffold + introspect a Node.js SFU (`install`, `quickstart`, `demo`, `rtp-bridge`, `workers`).
- `scripts/livekit.py` — install/run LiveKit + mint tokens (`install-server`, `install-cli`, `start`, `mint-token`, `room-list`, `room-join`, `load-test`, `egress-start`, `ingress-start`).

All scripts support `--dry-run` and `--verbose`.
