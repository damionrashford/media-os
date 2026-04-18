---
name: mediamtx-docs
description: >
  Search and fetch official MediaMTX documentation from mediamtx.org: kickoff (introduction, install, upgrade), features (architecture, publish, read, record, playback, authentication, hooks, metrics, forward, proxy, performance, rtsp-specific-features, rtmp-specific-features, webrtc-specific-features, srt-specific-features, absolute-timestamps, always-available, on-demand-publishing, decrease-packet-loss, extract-snapshots, remuxing-reencoding-compression, start-on-boot, embed-streams-in-a-website, expose-the-server-in-a-subfolder, logging, configuration), publish + read howtos (ffmpeg, gstreamer, obs-studio, python-opencv, golang, unity, raspberry-pi-cameras, rtsp, rtmp, hls, srt, webrtc, rtp, mpeg-ts), references (configuration-file, control-api). Use when the user asks to look up a MediaMTX config option, find a control-api endpoint, verify supported protocols, check auth modes (internal/HTTP/JWT), or read mediamtx howtos.
argument-hint: "[query]"
---

# MediaMTX Docs

**Context:** $ARGUMENTS

## Quick start

- **Find a config key / API endpoint / feature:** -> Step 2 (`search --query <term>`)
- **Read a how-to in full:** -> Step 4 (`fetch --page <publish/X or read/X>`)
- **Read one section:** -> Step 3 (`section --page <page> --id <anchor>`)
- **Prime cache for offline:** -> Step 5 (`index`)

## When to use

- User asks "how do I push RTSP to MediaMTX?" or "how do I configure JWT auth?" or "what control-api endpoints exist?"
- Need to verify a MediaMTX config key or CLI flag before recommending it.
- Need the canonical mediamtx.org URL to cite.
- Before wiring up a publisher/reader, confirm the protocol endpoint and default port (RTSP 8554, RTMP 1935, HLS 8888, WebRTC 8889, SRT 8890, API 9997, Metrics 9998, pprof 9999).
- For the running-server wrapper + API calls, see the `mediamtx-server` skill.

---

## Step 1 — Know the page catalog

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py list-pages
```

Top-level families:

| Family | When to pick |
|---|---|
| `kickoff/*` | Install, upgrade, first-run. |
| `features/*` | Core concepts (publish, read, record, playback, auth, hooks, metrics). |
| `features/<proto>-specific-features` | Per-protocol options (`rtsp-specific-features`, `rtmp-specific-features`, `webrtc-specific-features`, `srt-specific-features`). |
| `features/configuration` + `features/control-api` + `features/logging` + `features/metrics` | Operational — the knobs you actually turn in production. |
| `references/configuration-file` | Authoritative list of every YAML option. Start here for config questions. |
| `references/control-api` | Authoritative list of every `/v3/*` endpoint. |
| `publish/<client>` | How to SEND a stream in via ffmpeg / gstreamer / OBS / Python / Go / Unity / etc. |
| `read/<client>` | How to PLAY a stream out via ffmpeg / gstreamer / VLC / OBS / browsers / etc. |
| `github-readme`, `github-mediamtx.yml`, `github-apidocs` | Raw upstream files — the ground truth when mediamtx.org is behind. |

Read [`references/pages.md`](references/pages.md) for the full catalog.

---

## Step 2 — Search first

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "recordFormat" --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "jwt" --page features/authentication
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "/v3/paths" --page references/control-api
```

Use `--regex` for anchored patterns. Each hit prints page:line, nearest heading, canonical URL, and ±3 lines of context.

---

## Step 3 — Read one section

When a hit surfaces `[§anchor]`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py section --page features/authentication --id internal-users
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py section --page references/configuration-file --id paths
```

`--id` also accepts a heading keyword as fallback.

---

## Step 4 — Fetch a whole page

Use sparingly — howto pages are compact enough to fetch whole when you actually need the full recipe:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page publish/ffmpeg
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page read/web-browsers
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page github-mediamtx.yml   # raw upstream YAML
```

`--format json` for structured handoff.

---

## Step 5 — Prime cache

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py index
```

Fetches every known page (~70 URLs) at 0.3s each. Override cache dir via `MEDIAMTX_DOCS_CACHE`. Clear with `clear-cache`.

---

## Gotchas

- **MediaMTX does NOT transcode — it remuxes only.** If a publisher pushes HEVC into a path and a reader asks for WebRTC in the browser, the reader will FAIL (browsers don't universally support HEVC in WebRTC). The docs page `features/remuxing-reencoding-compression` is explicit: for transcoding, chain an external `ffmpeg` publisher. When in doubt, publish as H.264 + Opus.
- **The binary is now `mediamtx` (was `rtsp-simple-server`).** Repo moved from `aler9/rtsp-simple-server` -> `bluenviron/mediamtx`. Old Docker tags and install scripts still float around the internet; ignore them.
- **Default ports you'll see quoted in docs:** RTSP 8554, RTSPS 8322, RTMP 1935, RTMPS 1936, HLS 8888, WebRTC 8889, SRT 8890, Control API 9997, Metrics 9998, pprof 9999, Playback 9996. Each is a separate listener; disable any you don't need in `mediamtx.yml`.
- **Three auth backends, exclusive.** `internal` (users in YAML under `authInternalUsers`), `http` (POST to an external endpoint), `jwt` (verify a bearer token via JWK URL or static secret). You can't mix them globally — but per-path `permissions` still apply. See `features/authentication`.
- **Auth actions**: `publish`, `read`, `playback`, `api`, `metrics`, `pprof`. Default allowed users have `all` which is shorthand for the union. Lock down production before exposing port 9997.
- **Hooks fire on path events**, not on connection events. `runOnInit` runs when the path is first registered, not when a client connects. `runOnDemand` is what you want for lazy pipelines. Read `features/hooks`.
- **`always-available` vs `on-demand-publishing`.** Set `sourceOnDemand: true` to start `source:` only when readers appear (saves bandwidth). `sourceOnDemandStartTimeout` + `sourceOnDemandCloseAfter` control how long MediaMTX waits / keeps source alive after the last reader.
- **Control API lives at `/v3/*`**, NOT `/v2/*` or `/v1/*`. Older tutorials reference v2; the v3 namespace is the current stable. Full endpoint list is on `references/control-api`.
- **HLS has two variants**: "HLS" (standard, `.ts` segments, ~6s latency) and "Low-Latency HLS" (LL-HLS, fMP4 partial segments, ~2s latency). Configurable per path via `hlsVariant`.
- **WebRTC signalling is WHIP/WHEP** over HTTP at `http://<host>:8889/<path>/whip` (publish) and `.../whep` (read). Default ICE servers + STUN config live at the global level; per-path overrides are NOT supported.
- **SRT uses the "stream ID" trick for path routing.** `srt://host:8890?streamid=publish:<path>:<user>:<pass>` to publish; `srt://host:8890?streamid=read:<path>:<user>:<pass>` to read. Quotes required in most shells.
- **`recordFormat: fmp4` is the default and what you want.** MPEG-TS recording is deprecated for most cases because it can't seek.
- **Config file hot-reloads on SIGHUP**, but some settings (listening ports, TLS certs) require a full restart. If a change "doesn't seem to take", restart the process.
- **Docs site pagination is Next.js SSR**; anchors are Markdown-slugified headings (`#internal-users`, `#authentication-methods`). The `section --id` command accepts either the raw slug or a heading keyword.
- **Raw upstream YAML is the final authority.** `github-mediamtx.yml` page returns the exact `mediamtx.yml` shipped in `main` with every default documented inline. When mediamtx.org lags a release, this is the ground truth.

---

## Examples

### Example 1 — "What do I put in mediamtx.yml to enable JWT auth?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "jwt" --page features/authentication --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py section --page features/authentication --id jwt
```

### Example 2 — "How do I publish with ffmpeg?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page publish/ffmpeg
```

### Example 3 — "What's the full list of control-api endpoints?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page references/control-api
```

### Example 4 — "What does `runOnDemandCloseAfter` default to?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "runOnDemandCloseAfter" --page github-mediamtx.yml --limit 3
```

(Upstream YAML has inline defaults — faster than the HTML docs here.)

### Example 5 — "Record to disk, rotate every 15 min, keep 4 hours"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "recordSegmentDuration" --page features/record
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py search --query "recordDeleteAfter" --page features/record
```

### Example 6 — "WebRTC publish from a browser — what's the WHIP URL?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mtxdocs.py fetch --page publish/web-browsers
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** The name isn't in the catalog.
**Solution:** Run `list-pages`. Common mistakes: using `record` instead of `features/record`; `api` instead of `references/control-api`.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** System certificate store is out of date (usually macOS Python).
**Solution:** Run `/Applications/Python\ 3.x/Install\ Certificates.command` or set `SSL_CERT_FILE`. Don't patch SSL verification off.

### Search returns zero hits for a config key

**Cause:** Key might be new in `main` but not yet in the published docs.
**Solution:** Search against the upstream YAML — `search --query "<key>" --page github-mediamtx.yml`. The upstream file is the source of truth.

### Results look like broken-up tables

**Cause:** The HTML extractor flattens cell borders into pipes but can't reconstruct multi-line cells.
**Solution:** The search-hit header prints the canonical URL. Open it directly in a browser for the authoritative view.

### Cache stale after MediaMTX release

**Solution:** `clear-cache` then `index`. The GitHub fallback pages already track `main` — if you want a specific release tag, edit the `github-*` URLs in the script's `PAGES` dict (or fetch directly with `urllib`).

---

## Reference docs

- Full page catalog with protocol-to-page cross reference -> [`references/pages.md`](references/pages.md)
