---
name: webrtc-pion
description: >
  Build Go WebRTC applications with Pion (pion/webrtc/v4 — pkg.go.dev): primitives including PeerConnection, MediaEngine, SettingEngine, RTPSender, RTPReceiver, RTPTransceiver, DataChannel, TrackLocalStaticRTP, TrackLocalStaticSample, TrackRemote, ICEAgent, DTLSTransport, SCTPTransport, SRTPSession, Interceptor pipeline, StatsReport. Runnable examples: broadcast (minimal 1-to-N SFU), sfu-ws (WebSocket-signaled SFU), simulcast, play-from-disk, save-to-disk, save-to-webm, data-channels, whip-whep, ice-tcp, ice-single-port, insertable-streams, rtp-forwarder, rtp-to-webrtc. Sibling libs: pion/rtp, pion/rtcp, pion/sdp/v3, pion/ice/v3, pion/dtls/v3, pion/srtp/v3, pion/turn/v4, pion/mediadevices. SFUs built on Pion: ion-sfu, LiveKit, Galene. Use when the user asks to write a WebRTC server in Go, build an SFU from scratch, implement WHIP/WHEP endpoints, save WebRTC tracks to disk, or prototype a Pion pipeline.
argument-hint: "[example]"
---

# webrtc-pion

**Context:** $ARGUMENTS

Pion is the canonical Go WebRTC stack. It is a library, not a server — you embed it in your own binary. The helper script in this skill wraps the **examples repo** for fast prototyping: it fetches one example via `git sparse-checkout`, builds it, and runs it.

## Quick start

- **Browse canonical examples:** → Step 2 (`pion.py list-examples`)
- **Fetch + build + run one example:** → Step 3
- **Quick WHIP/WHEP round-trip:** → Step 5
- **Stand up a TURN server:** → Step 6

## When to use

- User wants a WebRTC server in Go (SFU, WHIP ingest, RTP bridge).
- Need to save WebRTC media to disk, or play a file into a PeerConnection.
- Need to insert low-level hooks (insertable streams, custom RTCP feedback, encoded transforms) that the browser API doesn't expose.
- Pair with `webrtc-spec` when you need to verify protocol details as you build.

Use **`webrtc-mediasoup`** or **`webrtc-livekit`** instead if the user wants a full product out of the box — Pion is one layer down from both.

## Step 1 — Prerequisites

- Go >= 1.22 (`go version`). Install via `brew install go` / `apt install golang-go` / golang.org.
- `git` on PATH.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py check
```

Prints Go version + git presence + current GOPATH.

## Step 2 — Browse canonical examples

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py list-examples
```

Canonical set (mirrors `https://github.com/pion/webrtc/tree/master/examples`):

| Example                 | What it demonstrates                                    |
|-------------------------|---------------------------------------------------------|
| `broadcast`             | Minimal 1-to-N SFU                                      |
| `sfu-ws`                | WebSocket-signaled SFU                                  |
| `simulcast`             | Simulcast ingest + forwarding                           |
| `play-from-disk`        | Send a local IVF/Ogg file as a WebRTC track             |
| `save-to-disk`          | Persist incoming RTP to IVF/Ogg                         |
| `save-to-webm`          | Mux received tracks to a WebM file                      |
| `data-channels`         | Basic SCTP data channel round-trip                      |
| `data-channels-detach`  | Detach a data channel for raw io.ReadWriter usage       |
| `data-channels-close`   | Clean DC shutdown handshake                             |
| `ice-tcp`               | ICE over TCP fallback                                   |
| `ice-single-port`       | Multiplex all UDP flows on one port (SFU-style)         |
| `ice-restart`           | Trigger ICE restart mid-session                         |
| `insertable-streams`    | Encoded-transform hooks (E2EE, watermarks)              |
| `rtp-forwarder`         | Receive over WebRTC, forward RTP to a UDP socket        |
| `rtp-to-webrtc`         | Ingest raw RTP, expose as a WebRTC track                |
| `whip-whep`             | WHIP ingestion + WHEP egress                            |
| `stats`                 | `StatsReport` snapshot dump                             |
| `custom-logger`         | Pluggable logging                                       |
| `swap-tracks`           | Hot-swap a TrackLocal at runtime                        |
| `trickle-ice`           | Explicit trickle-ICE signaling                          |

Full descriptions in [`references/examples.md`](references/examples.md).

## Step 3 — Fetch + build + run

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py fetch-example broadcast --dest ~/pion-broadcast
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py build ~/pion-broadcast
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py run   ~/pion-broadcast
```

`fetch-example` does `git clone --depth 1 --filter=blob:none --sparse https://github.com/pion/webrtc` then `git sparse-checkout set examples/<name>`. No `go.mod` rewrites — the example already declares a replace directive against the local repo root.

## Step 4 — Primitives

Read [`references/primitives.md`](references/primitives.md) for the full list. Core objects:

- `webrtc.API` — factory holding a `MediaEngine`, `SettingEngine`, `InterceptorRegistry`.
- `webrtc.PeerConnection` — SDP + DTLS + SCTP wrapper.
- `MediaEngine` — registered codecs + header extensions.
- `SettingEngine` — transport tuning (ICE lite, candidate filters, single-port mux, custom loggers).
- `InterceptorRegistry` — RTCP generator stack (NACK, TWCC, report).
- `TrackLocalStaticRTP` / `TrackLocalStaticSample` — write outgoing media.
- `TrackRemote` — incoming media; `.ReadRTP()` returns `*rtp.Packet`.
- `RTPSender` / `RTPReceiver` / `RTPTransceiver` — track-flow control.
- `DataChannel` — SCTP data channel; use `.Detach()` for byte-stream mode.
- `ICEAgent` / `DTLSTransport` / `SCTPTransport` / `SRTPSession` — exposed for debugging / advanced graph work.

Sibling modules: `pion/rtp`, `pion/rtcp`, `pion/sdp/v3`, `pion/ice/v3`, `pion/dtls/v3`, `pion/srtp/v3`, `pion/turn/v4`, `pion/mediadevices`.

## Step 5 — WHIP / WHEP quick test

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py whip http://localhost:8080/whip --dest ~/pion-whip
# Publish from ffmpeg (see `ffmpeg-whip` skill for the muxer flags)
# ffmpeg -re -i input.mp4 -c:v libx264 -bf 0 -c:a libopus -f whip http://localhost:8080/whip

uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py whep http://localhost:8080/whep --dest ~/pion-whep
```

Both subcommands are thin wrappers: `fetch-example whip-whep` → `build` → `run`.

## Step 6 — TURN server skeleton

pion/turn has a minimal ready-to-run server:

```go
package main

import (
    "net"
    "github.com/pion/turn/v4"
)

func main() {
    udpListener, _ := net.ListenPacket("udp4", "0.0.0.0:3478")
    server, _ := turn.NewServer(turn.ServerConfig{
        Realm: "example.org",
        AuthHandler: func(username, realm string, srcAddr net.Addr) (key []byte, ok bool) {
            return turn.GenerateAuthKey("alice", "example.org", "secret"), true
        },
        PacketConnConfigs: []turn.PacketConnConfig{
            {PacketConn: udpListener, RelayAddressGenerator: &turn.RelayAddressGeneratorStatic{RelayAddress: net.ParseIP("1.2.3.4"), Address: "0.0.0.0"}},
        },
    })
    defer server.Close()
    select {}
}
```

For an integrated STUN+TURN deployment most teams use `coturn` (C, battle-tested). Use pion/turn when you want to embed TURN in the same Go binary.

## Gotchas

- **Pion has a library per major — `github.com/pion/webrtc/v4` (current), `v3` (old), `v2` (abandoned).** Always use `v4` for new code.
- **`MediaEngine` is NOT reusable across `API` instances** — register codecs once per API.
- **`webrtc.API{}` zero value is invalid.** Construct via `webrtc.NewAPI(...)`.
- **`TrackLocalStaticRTP.WriteRTP` needs a payload type matching the `MediaEngine` registration.** Mismatch drops negotiation.
- **`Sample.Duration` is critical** — set to `time.Second/fps`, otherwise RTP timestamps will be wrong.
- **`PeerConnection.OnTrack` fires once per track.** Put the `ReadRTP` loop inside the callback in its own goroutine; don't spawn one per packet.
- **`OnICEConnectionStateChange` vs `OnConnectionStateChange`** — the second is what you want for "is the PC usable right now".
- **Simulcast on the publisher side requires `SendEncodings` with explicit `Rid`s** in `RTPTransceiverInit` — missing any drops simulcast to single-layer.
- **`Interceptor` order matters** — NACK generator must register before the RTCP sender. Default registry does it right.
- **DTLS fingerprint comparison is case-insensitive and uses ":" separators.** If your signaling rewrites SDP, preserve the colons.
- **`TrackRemote.SSRC()` vs SDP `a=ssrc:`** — with RTX you get primary + RTX as separate `TrackRemote` events.
- **`go.mod replace` in examples points at the repo root.** When copying an example outside the repo, drop the replace and use `go get github.com/pion/webrtc/v4@latest`.

## Examples

### Example 1 — Minimal 1-to-N SFU

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py fetch-example broadcast --dest ~/pion-broadcast
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py run ~/pion-broadcast
```

### Example 2 — Save a WebRTC track to disk

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py fetch-example save-to-disk --dest ~/pion-save
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py run ~/pion-save
```

### Example 3 — WHIP + WHEP round-trip

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py whip http://0.0.0.0:8080/whip --dest ~/pion-whip
```

### Example 4 — Insertable streams

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py fetch-example insertable-streams --dest ~/pion-is
uv run ${CLAUDE_SKILL_DIR}/scripts/pion.py run ~/pion-is
```

### Example 5 — Local TURN

Copy Step-6 skeleton into `main.go`, `go mod init local-turn && go get github.com/pion/turn/v4 && go run .`.

## Troubleshooting

### `go: module github.com/pion/webrtc/v4 ...: unexpected EOF`

Cause: network hiccup during module resolution.
Solution: `go clean -modcache` then retry. Verify `GOPROXY` via `go env GOPROXY`.

### `failed to negotiate: cannot satisfy media section`

Cause: offered codec isn't registered on the answerer's `MediaEngine`.
Solution: call `MediaEngine.RegisterDefaultCodecs()` or `RegisterCodec` per codec.

### Browser sees the track but no video renders

Cause: `TrackLocalStaticSample.WriteSample` called with `Duration: 0` or wrong PT.
Solution: set `Sample{Duration: time.Second/30}` for 30 fps; confirm PT matches engine registration.

### `ICE connection state: failed` on deploy

Cause: no TURN, publisher behind symmetric NAT, or TURN unreachable from subscriber.
Solution: add TURN via `RTCConfiguration.ICEServers`. Test with trickle-ice probe.

### `examples/<name>/main.go: no such file or directory`

Cause: example renamed upstream.
Solution: re-run `list-examples`.

## Reference docs

- Read [`references/primitives.md`](references/primitives.md) when you need the full Pion object + sibling-lib catalog with pkg.go.dev URLs.
- Read [`references/examples.md`](references/examples.md) when you need one-paragraph descriptions of every canonical example.
