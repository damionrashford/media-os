---
name: mediamtx-server
description: >
  Host an all-protocol media server with MediaMTX (bluenviron/mediamtx, formerly rtsp-simple-server): single binary speaks RTSP + RTSPS + RTMP + RTMPS + HLS + LL-HLS + WebRTC (WHIP/WHEP) + SRT + MPEG-TS + RTP, auto-transmuxes between them on the fly. Author mediamtx.yml (paths, record, hooks, auth internal/HTTP/JWT), drive the Control API at /v3/* (config, paths, connections, sessions, recordings), Prometheus metrics, on-demand publishing, forward/proxy to other servers, Docker deployment. Use when the user asks to host an RTSP/RTMP/HLS/WebRTC/SRT server, run a self-hosted media server, ingest to an all-protocol endpoint, build a WHIP receiver, stream to a browser via LL-HLS or WebRTC, record streams to disk, or set up a media relay — all without transcoding.
argument-hint: "[action]"
---

# MediaMTX Server

**Context:** $ARGUMENTS

## Quick start

- **Install the binary:** -> Step 1 (`install`)
- **Write a starter config:** -> Step 2 (`init-config`)
- **Launch + reload + stop:** -> Step 3 (`start` / `reload` / `stop`)
- **Query the Control API:** -> Step 4 (`paths-list` / `sessions-list` / `api`)
- **Author auth rules (JWT):** -> Step 5 (`mint-jwt`)

## When to use

- User wants a self-hosted server that accepts any of RTSP, RTMP, HLS, WebRTC (WHIP/WHEP), SRT, MPEG-TS and transmuxes between them.
- User needs on-demand publishing (spawn an ffmpeg publisher only when readers appear), recording to disk, or per-path hooks.
- User wants a Prometheus-scrapeable metrics endpoint for stream health.
- User wants to relay / forward / proxy between servers.

For documentation lookup (what does `recordSegmentDuration` default to? which `/v3/*` endpoint lists webrtc sessions?), use the `mediamtx-docs` skill first.

---

## Step 1 — Install

Download the latest release binary for the current platform (detects
`darwin_{arm64,amd64}`, `linux_{amd64,arm64v8,armv7,armv6}`, `windows_amd64`):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py install --dir ./MediaMTX-bin
```

Then the binary lives at `./MediaMTX-bin/mediamtx` (or `.exe` on Windows).
Export `MEDIAMTX_BIN` once so subsequent commands can find it without `--bin`:

```bash
export MEDIAMTX_BIN=$PWD/MediaMTX-bin/mediamtx
```

Alternative installs (not covered by this script — all documented at `mediamtx-docs`):

- Docker: `docker run --rm -it --network host bluenviron/mediamtx:latest`
- Homebrew: `brew install mediamtx`
- `go install github.com/bluenviron/mediamtx@latest`

---

## Step 2 — Write a starter config

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py init-config --output ./mediamtx.yml
```

The generated `mediamtx.yml` has:

- API on `:9997`, metrics on `:9998`, playback on `:9996`.
- RTSP + RTMP + HLS (LL-HLS variant) + WebRTC + SRT all enabled.
- Internal auth with an `any` user (no-auth publisher/reader) and a locked-down `admin` for API/metrics.
- Commented-out examples for on-demand-only paths, recording, and upstream RTSP camera proxy.

Edit before starting. At minimum:
- Change the admin password.
- Set `webrtcICEServers2` to a real STUN/TURN for NAT traversal.
- Add per-path recording if needed.

Full reference: [`references/config.md`](references/config.md) has the
annotated YAML + every knob.

---

## Step 3 — Run the server

Start (forked, pidfile-tracked):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py start \
  --bin ./MediaMTX-bin/mediamtx \
  --config ./mediamtx.yml \
  --log ./mediamtx.log
```

The pidfile defaults to `/tmp/mediamtx.pid` (override with `--pidfile` or
`MEDIAMTX_PID`). Starting twice fails fast if the pidfile's process is still
alive.

Hot-reload the config (SIGHUP — most keys reload without restart; a few
listener changes need a full restart):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py reload
```

Stop:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py stop            # SIGTERM
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py stop --kill     # SIGKILL if stuck
```

For systemd / launchd / Windows service, point your unit/plist at the
`mediamtx` binary directly — the docs page `features/start-on-boot` has
templates.

---

## Step 4 — Drive the Control API

Default API base: `http://127.0.0.1:9997` (override with `--base` or
`$MEDIAMTX_API`). Tags that pass `--user` / `--password` use HTTP Basic.

List all paths (live + configured):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py paths-list
```

Aggregate every session + connection endpoint into one JSON blob:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py sessions-list
```

(Covers `/v3/rtspconns/list`, `/v3/rtspsessions/list`, `/v3/rtspsconns/list`,
`/v3/rtspssessions/list`, `/v3/rtmpconns/list`, `/v3/rtmpsconns/list`,
`/v3/hlsmuxers/list`, `/v3/webrtcsessions/list`, `/v3/srtconns/list`.)

List recordings:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py recordings-list
```

Generic GET / POST / PATCH / DELETE:

```bash
# Read global config
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api --path /v3/config/global/get

# Patch a path at runtime
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api \
  --path /v3/config/paths/patch/camera1 \
  --method PATCH \
  --json-body '{"record":true,"recordFormat":"fmp4"}'

# Delete a path
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api \
  --path /v3/config/paths/delete/camera1 \
  --method DELETE

# Kick a WebRTC session
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api \
  --path /v3/webrtcsessions/kick/<id> \
  --method POST
```

Full endpoint list: [`references/api.md`](references/api.md) or
`mediamtx-docs` -> `references/control-api`.

---

## Step 5 — Auth + mint a JWT

MediaMTX supports three auth backends, selected by `authMethod`:

- `internal` — users listed under `authInternalUsers` in `mediamtx.yml`.
- `http` — MediaMTX POSTs `{action, path, protocol, user, pass, ip, query}` to
  your external endpoint; your endpoint replies `200` (allow) or anything else
  (deny).
- `jwt` — bearer token verified against a JWK URL (`jwtJWKSURL`) OR a shared
  HMAC secret. The token's `mediamtx_permissions` claim is a list of
  `{action, path}` entries.

For testing the JWT flow, mint a short-lived HS256 token:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py mint-jwt \
  --secret "$MY_SHARED_SECRET" \
  --sub user42 \
  --ttl 900 \
  --permission publish:live/cam1 \
  --permission read:live/cam1
```

Pass the token as either `?jwt=<token>` on the publish URL or the
`Authorization: Bearer <token>` header.

Full auth flow details: `references/api.md` and
`mediamtx-docs` -> `features/authentication`.

---

## Gotchas

- **MediaMTX does NOT transcode.** It's a remuxer. If a publisher pushes HEVC and the reader wants WebRTC in the browser, the reader will fail to play (browsers don't support HEVC in WebRTC). Common fix: chain an external ffmpeg that transcodes into a second path. `features/remuxing-reencoding-compression` has the recipe.
- **Repo name is now `bluenviron/mediamtx`** (was `aler9/rtsp-simple-server`). Old install scripts, Docker image tags (`aler9/rtsp-simple-server:latest`), and StackOverflow answers still reference the old name — ignore them. Current image: `bluenviron/mediamtx:latest`.
- **Default ports — every listener is independent.** RTSP 8554, RTSPS 8322, RTMP 1935, RTMPS 1936, HLS 8888, WebRTC 8889 (WHIP/WHEP over HTTP), SRT 8890, API 9997, Metrics 9998, Playback 9996, pprof 9999. Disable unused ones in `mediamtx.yml` (set `rtsp: no`, `rtmp: no`, etc.) — exposing them all in production is unnecessary attack surface.
- **Control API lives at `/v3/*`**, NOT `/v2/*` or `/v1/*`. Any tutorial referencing `/v2` is obsolete.
- **API 9997 is UNAUTHENTICATED by default.** Exposing it beyond `127.0.0.1` is dangerous — anyone with access can add paths, rewrite config, or kick sessions. Lock it down with `authInternalUsers` that requires the `api` action, and firewall the port.
- **`authMethod` is global, not per-path.** You can't use `internal` for RTSP but `jwt` for WebRTC. Per-path granularity comes from the `permissions` list inside each user entry.
- **`sourceOnDemand: true` fires `runOnDemand` only when a reader connects.** `sourceOnDemandStartTimeout` (default 10s) is the grace period for the publisher to appear; `sourceOnDemandCloseAfter` (default 10s) is how long the source stays alive after the last reader disconnects.
- **Hooks are shell commands, not HTTP calls.** `runOnInit`, `runOnDemand`, `runOnReady`, `runOnRead`, `runOnUnread`, `runOnConnect`, `runOnDisconnect` all `fork/exec` a shell. MediaMTX substitutes `$MTX_PATH`, `$MTX_QUERY`, `$MTX_SOURCE_TYPE`, etc. into the command.
- **HLS has three variants**: `mpegts` (legacy, `.ts` segments, ~6-10s latency, widest compat), `fmp4` (fragmented MP4, ~4-6s), `lowLatency` (LL-HLS with partial segments, ~1-2s, Safari + hls.js >=1.5 only). Default is `lowLatency`.
- **WebRTC = WHIP for publish + WHEP for read**, served at `:8889/<path>/whip` and `.../whep`. Not a signalling-server model — direct HTTP POST of SDP offers. OBS's built-in WebRTC service targets this.
- **SRT routing is via streamId**: `srt://host:8890?streamid=publish:<path>:<user>:<pass>` to publish, `srt://host:8890?streamid=read:<path>:<user>:<pass>` to read. Most SRT clients default to `streamid=live` — you must set it.
- **Recording: `recordFormat: fmp4` default, `recordSegmentDuration: 1h` default.** fMP4 supports seek via the Playback API (`/playback`). MPEG-TS recordings do not.
- **`mediamtx.yml` hot-reloads on SIGHUP** for almost every key. Exceptions: listening addresses, TLS certs, API address. Restart for those.
- **Binaries are static — no external deps.** Good for container slim images. `FROM scratch` works if you also ship the CA bundle your upstreams need.
- **The official release contains the binary AND an embedded reference mediamtx.yml** in its tarball — the upstream YAML at `raw.githubusercontent.com/.../main/mediamtx.yml` is always the ground truth for defaults. `mediamtx-docs` `github-mediamtx.yml` page gives it to you directly.

---

## Examples

### Example 1 — "Stand up a server for my ffmpeg publisher to push RTSP"

```bash
# 1. install + init-config + start
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py install
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py init-config
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py start --config ./mediamtx.yml

# 2. publish via ffmpeg (separate shell)
ffmpeg -re -stream_loop -1 -i sample.mp4 -c copy -f rtsp \
  rtsp://127.0.0.1:8554/live/demo

# 3. read via ffplay / VLC
ffplay rtsp://127.0.0.1:8554/live/demo
```

### Example 2 — "Record every publisher to disk, rotate hourly, keep 24h"

Edit `mediamtx.yml`:

```yaml
pathDefaults:
  record: yes
  recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S-%f
  recordFormat: fmp4
  recordSegmentDuration: 1h
  recordDeleteAfter: 24h
```

Hot-reload:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py reload
```

Later, inspect disk:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py recordings-list
```

### Example 3 — "Publish a WHIP stream from OBS into a LL-HLS viewer"

- In `mediamtx.yml`, ensure `hls: yes` and `hlsVariant: lowLatency`.
- In OBS, Settings -> Stream -> Service "WHIP", Server `http://127.0.0.1:8889/live/obs/whip`, Bearer Token blank (unless auth on).
- The browser player opens `http://127.0.0.1:8888/live/obs/index.m3u8` (LL-HLS) or `http://127.0.0.1:8889/live/obs/` (WHEP viewer page).

### Example 4 — "Lock down the control API to admin-only"

In `mediamtx.yml`:

```yaml
authMethod: internal
authInternalUsers:
  - user: admin
    pass: SECURE_PW
    ips: [127.0.0.1/32]
    permissions:
      - action: api
      - action: metrics
      - action: pprof
  - user: publisher
    pass: PUB_PW
    permissions:
      - action: publish
  - user: any
    pass:
    permissions:
      - action: read
```

Reload. API calls now need `--user admin --password SECURE_PW`.

### Example 5 — "Kick every WebRTC session"

```bash
ids=$(uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api --path /v3/webrtcsessions/list \
  | jq -r '.items[].id')
for id in $ids; do
  uv run ${CLAUDE_SKILL_DIR}/scripts/mtxctl.py api \
    --path "/v3/webrtcsessions/kick/$id" --method POST
done
```

### Example 6 — "Run in Docker instead of the helper binary"

```bash
docker run -d --name mediamtx --network host \
  -v "$PWD/mediamtx.yml:/mediamtx.yml" \
  -v "$PWD/recordings:/recordings" \
  bluenviron/mediamtx:latest
```

The `install` / `start` / `stop` / `reload` script subcommands are not
needed in this mode — Docker manages the process lifecycle. `mtxctl.py
paths-list` / `api` / `mint-jwt` still work against the API at
`http://127.0.0.1:9997`.

---

## Troubleshooting

### `mediamtx binary not found`

**Cause:** `MEDIAMTX_BIN` isn't set and `./MediaMTX-bin/mediamtx` doesn't exist.
**Solution:** Run `mtxctl.py install` first, or export `MEDIAMTX_BIN=$(which mediamtx)`, or pass `--bin /path/to/mediamtx`.

### Start says "already running pid X" but the process is gone

**Cause:** Pidfile is stale (non-graceful shutdown).
**Solution:** Remove the pidfile (`rm /tmp/mediamtx.pid`) and start again.

### HEVC publisher -> WebRTC reader gives "codec not supported"

**Cause:** MediaMTX can't transcode; browsers don't support HEVC in WebRTC.
**Solution:** Re-encode upstream: run an ffmpeg process that reads HEVC from one path and publishes H.264 into a second path, then point the WebRTC reader at the second path.

### API returns 401

**Cause:** `authMethod` is internal and your API user doesn't have the `api` action.
**Solution:** Add `- action: api` to the user's permissions list, reload, and include `--user`/`--password` on every API call.

### API returns 404 for `/v2/paths/list`

**Cause:** The v2 namespace was removed.
**Solution:** Use `/v3/paths/list`.

### WebRTC publish works locally but fails across networks

**Cause:** No public STUN/TURN — browser can't get a reachable ICE candidate.
**Solution:** In `mediamtx.yml` set `webrtcICEServers2` with real STUN + TURN (coturn, Cloudflare Realtime, Twilio STUN).

### Recording fills disk

**Cause:** `recordDeleteAfter` not set.
**Solution:** Set `recordDeleteAfter: 24h` (or similar) in `pathDefaults` so old segments are pruned.

### SIGHUP reload did nothing

**Cause:** The key you changed is in the "requires restart" set (listener addresses, TLS, API address).
**Solution:** Full restart: `mtxctl.py stop && mtxctl.py start ...`.

---

## Reference docs

- Full `/v3/*` API endpoint catalog with request/response shapes -> [`references/api.md`](references/api.md)
- Annotated `mediamtx.yml` with every knob + its default -> [`references/config.md`](references/config.md)

Companion skills:
- `mediamtx-docs` for official doc search / section fetch.
- `ffmpeg-streaming` for publishing via ffmpeg (`-f rtsp`, `-f rtmp`, `-f srt`).
- `ffmpeg-whip` for WHIP publish from ffmpeg.
- `gstreamer-pipeline` for publishing via GStreamer (`rtspclientsink`, `whipclientsink`, `srtsink`).
