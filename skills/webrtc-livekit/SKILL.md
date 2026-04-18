---
name: webrtc-livekit
description: >
  Deploy LiveKit WebRTC SFU (docs.livekit.io — Apache-2.0 Go binary): livekit-server (SFU binary, YAML + env config), livekit-cli (admin + load-testing — create-token, load-test, room list, room join), livekit-egress (record/stream-out to HLS/MP4/RTMP), livekit-ingress (RTMP/WHIP/SRT/URL ingest), livekit-agents (realtime AI voice/video agents). Data model: Room, Participant, Track, TrackPublication. JWT access tokens with grants (room, roomJoin, canPublish, canSubscribe, canPublishData, hidden, recorder). SDKs: JS/TS, Python, Go, Rust, Swift, Kotlin, Flutter, Unity, React/React Native, Node.js, Ruby, PHP. Redis for multi-node. TURN via bundled Pion or external coturn. Cloud vs self-hosted options. Use when the user asks to run a LiveKit server, mint room tokens, record a LiveKit room, build a conferencing app, integrate LiveKit Agents, or deploy a WebRTC SFU with full SDK coverage.
argument-hint: "[action]"
---

# webrtc-livekit

**Context:** $ARGUMENTS

LiveKit is an Apache-2.0 WebRTC SFU written in Go — a single-binary deployment with a vast SDK matrix. Docs home: `https://docs.livekit.io/home/`. Repo: `https://github.com/livekit/livekit`.

## Quick start

- **Install server binary for your platform:** → Step 1 (`livekit.py install-server`)
- **Install the CLI (`lk` / `livekit-cli`):** → Step 1 (`livekit.py install-cli`)
- **Start a dev server:** → Step 2 (`livekit.py start`)
- **Mint a JWT access token:** → Step 3 (`livekit.py mint-token`)
- **Record or stream-out a room:** → Step 5 (`livekit.py egress-start`)
- **Ingest RTMP/WHIP/SRT into a room:** → Step 6 (`livekit.py ingress-start`)

## Data model

```
Room (per-meeting)
  ├── Participant (per-user)
  │     ├── TrackPublication (the publisher's declaration)
  │     │     └── Track (camera / mic / screen-share / data)
  │     └── Permissions  (from JWT grants)
  └── Metadata           (free-form, room-wide or per-participant)
```

Tokens are **JWT** (HS256). Each token carries a `video` grant describing which room and which permissions.

## Step 1 — Install the binaries

```bash
# Server
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py install-server --dest ~/bin
# CLI ("lk", formerly "livekit-cli")
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py install-cli --dest ~/bin
```

The script downloads the correct release from `github.com/livekit/livekit/releases` (server) and `github.com/livekit/livekit-cli/releases` (CLI) for your `uname -sm`, extracts it, and places the binary in `--dest`. No sudo required if `--dest` is writable. Homebrew and the official install.sh exist upstream — pick whichever fits your OS.

## Step 2 — Start a dev server

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py start --dev
```

`--dev` launches with a built-in dev API key / secret (`devkey` / `secret`) and enabled self-signed TURN on 443. For production, write a YAML config:

```yaml
# livekit.yaml (abridged — see references/deployment.md for the full set)
port: 7880
bind_addresses: ['']
rtc:
  port_range_start: 50000
  port_range_end: 60000
  tcp_port: 7881
  use_external_ip: true
keys:
  devkey: secret
redis:
  address: redis:6379
```

Run: `livekit-server --config livekit.yaml`.

## Step 3 — Mint access tokens (JWT HS256, pure Python)

LiveKit tokens are JWTs with an `iss` = API key, `sub` = participant identity, `video` grant, and standard `iat` / `exp`. The helper mints them with stdlib only (hmac + hashlib + base64 + json):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py mint-token \
  --api-key devkey --api-secret secret \
  --room my-room --identity alice \
  --name 'Alice' --ttl 3600 \
  --grants roomJoin=true,canPublish=true,canSubscribe=true,canPublishData=true
```

Token schema (see [`references/grants.md`](references/grants.md) for every flag):

```json
{
  "iss": "devkey",
  "sub": "alice",
  "name": "Alice",
  "iat": 1710000000,
  "exp": 1710003600,
  "nbf": 1710000000,
  "video": {
    "room": "my-room",
    "roomJoin": true,
    "canPublish": true,
    "canSubscribe": true,
    "canPublishData": true,
    "hidden": false,
    "recorder": false
  }
}
```

## Step 4 — Use the CLI

```bash
lk room list --api-key KEY --api-secret SECRET --url ws://localhost:7880
lk room join --url ws://localhost:7880 --api-key KEY --api-secret SECRET --identity alice my-room
lk load-test --url ws://localhost:7880 --api-key KEY --api-secret SECRET --room test --publishers 5 --subscribers 20
```

The helper wraps these (passes through to `lk`):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py room-list
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py room-join --room my-room --identity alice
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py load-test --config load-test.yaml
```

## Step 5 — Egress (record / stream out)

`livekit-egress` is a separate binary (`github.com/livekit/egress`) that connects to a Room and records or re-streams it. Outputs: MP4 file, HLS manifest, or RTMP push.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py egress-start \
  --url ws://localhost:7880 --api-key KEY --api-secret SECRET \
  --room my-room --type room-composite --layout grid \
  --output mp4 --dest ./recording.mp4
```

Egress types:

- `room-composite` — lay out all participants into one MP4/HLS stream.
- `track-composite` — specific set of tracks (audio + screen share, etc.).
- `track` — single track, no composite (raw stream).
- `web` — load an arbitrary URL (like a Grafana dashboard) and record it.
- `participant` — one participant's outgoing tracks.

Egress runs best as a separate service in its own container (uses headless Chromium); docs: `https://docs.livekit.io/home/egress/overview/`.

## Step 6 — Ingress (RTMP / WHIP / SRT / URL into a Room)

`livekit-ingress` (`github.com/livekit/ingress`) accepts RTMP / WHIP / SRT / URL pulls and injects them as Participants.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py ingress-start \
  --url ws://localhost:7880 --api-key KEY --api-secret SECRET \
  --room my-room --type rtmp --name 'OBS Feed' --identity obs-1
```

Returns an ingest URL and stream key. Ingress must run as a sidecar too.

## SDK matrix

Official SDKs (all link from `https://docs.livekit.io/home/client/`):

- **JS/TS** — `livekit-client` (browser + Node)
- **Python** — `livekit` on PyPI
- **Go** — `github.com/livekit/server-sdk-go`
- **Rust** — `livekit` on crates.io
- **Swift** — `LiveKit` for iOS/macOS
- **Kotlin** — Android
- **Flutter** — `livekit_client`
- **Unity** — WebRTC-based
- **React / React Native** — `@livekit/components-react` / `livekit-react-native`
- **Node.js server SDK** — `livekit-server-sdk` (for minting tokens + webhooks)
- **Ruby**, **PHP** — community + first-party server SDKs

## LiveKit Agents (realtime AI)

`https://docs.livekit.io/agents/` — framework for realtime voice/video agents that join Rooms. Pair with OpenAI Realtime, Deepgram, ElevenLabs etc. Python + Node.js.

## Gotchas

- **JWT algorithm is HS256.** Do NOT use RS256 or the server rejects it. The helper enforces HS256.
- **`exp` is mandatory.** Missing `exp` → 401 at room join.
- **Identity must be unique per room.** Re-joining with the same identity kicks the previous participant.
- **`canPublish:false` tokens still count against room-size limits** — hidden observers need `hidden:true` to not appear in participant lists.
- **`recorder:true` grant** is what `livekit-egress` uses — mark your egress participant with it so the server doesn't include it in room composites.
- **TCP fallback port (`rtc.tcp_port`)** must be reachable on your public IP; otherwise peers behind strict firewalls fail to connect.
- **Use a shared Redis for multi-node** — without it, participants on different nodes cannot see each other.
- **CLI was renamed** from `livekit-cli` to `lk` in late 2024. The long name still works via symlink in most builds.
- **The dev key `devkey:secret` is insecure.** For any deployment that's reachable from the internet, generate fresh keys — `lk create-api-key`.
- **Egress containers want 2+ vCPU and 2 GB RAM each** — composite recording drives headless Chromium + ffmpeg. Underprovisioning causes frame drops.
- **Ingress RTMP stream keys leak the room name** if you're not careful — use per-stream keys and rotate.
- **`use_external_ip:true` reads cloud metadata endpoints** on AWS/GCP/Azure. On-prem: set `node_ip` manually.
- **Simulcast is ON by default** for browser publishers. Turn it off via `VideoPresets` on the client for single-layer encoders.

## Examples

### Example 1 — Dev server + token + join

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py install-server --dest ~/bin
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py start --dev        # in one terminal

# in another
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py mint-token \
  --api-key devkey --api-secret secret \
  --room test --identity alice --ttl 3600 \
  --grants roomJoin=true,canPublish=true,canSubscribe=true

# Paste the token into the Meet demo at https://meet.livekit.io
```

### Example 2 — Record a room to MP4

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py egress-start \
  --url ws://localhost:7880 --api-key devkey --api-secret secret \
  --room test --type room-composite --output mp4 --dest ./out.mp4
```

### Example 3 — RTMP ingress from OBS

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py ingress-start \
  --url ws://localhost:7880 --api-key devkey --api-secret secret \
  --room test --type rtmp --identity obs-cam
```

Response contains `url` + `streamKey` — paste into OBS Stream settings.

### Example 4 — 50-participant load test

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py load-test \
  --url ws://localhost:7880 --api-key devkey --api-secret secret \
  --room bench --publishers 10 --subscribers 40 --duration 60s
```

### Example 5 — Short-lived recorder token (no publish)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/livekit.py mint-token \
  --api-key devkey --api-secret secret \
  --room test --identity rec-bot --ttl 600 \
  --grants roomJoin=true,canSubscribe=true,hidden=true,recorder=true
```

## Troubleshooting

### Client gets 401 at `room.connect`

Cause: token signature invalid, expired, wrong API key, or missing `roomJoin` grant.
Solution: re-mint with `mint-token`, verify API secret matches server config.

### ICE succeeds but no media arrives

Cause: `rtc.port_range_start..end` UDP range blocked at firewall; no TCP fallback port.
Solution: open the UDP range publicly (50000-60000 by default), plus `rtc.tcp_port`.

### "No room service available"

Cause: talking to the wrong port (`7880` is HTTP + WS), or Redis is required but unreachable.
Solution: check `docker logs` / server stdout for Redis errors.

### Egress produces 0-byte MP4

Cause: Chromium failed to launch (missing `libatk`, `libxss`, `libgbm` on slim containers).
Solution: use the official egress image `livekit/egress:latest` which bundles deps.

### Participant appears twice after reconnect

Cause: old session not cleaned up; client using same identity.
Solution: server will auto-kick the older session; ensure the client uses a fresh identity or reuse the existing token.

## Reference docs

- Read [`references/grants.md`](references/grants.md) for the full VideoGrant / RoomAdmin grant catalog with per-flag permissions.
- Read [`references/deployment.md`](references/deployment.md) for the self-hosted stack (livekit-server, Redis, TURN via bundled Pion or coturn, egress + ingress sidecars, sample YAML).
