---
name: mediamtx
description: >
  Use when the user asks to host or run a self-hosted media server, stand up MediaMTX (bluenviron/mediamtx, formerly rtsp-simple-server), accept or ingest RTSP, RTSPS, RTMP, RTMPS, HLS, LL-HLS, WebRTC (WHIP/WHEP), SRT, MPEG-TS, or RTP on one binary that auto-transmuxes between them, build a WHIP receiver, stream to a browser via LL-HLS or WebRTC, record streams to disk, relay/forward/proxy between servers, author mediamtx.yml (paths, record, hooks, auth internal/HTTP/JWT), drive the Control API at /v3/*, scrape Prometheus metrics, set up on-demand publishing, deploy in Docker, or look up a MediaMTX config key, control-api endpoint, default port, auth mode, or publish/read howto from the official mediamtx.org docs.
argument-hint: "[action]"
---

# MediaMTX

Consolidated MediaMTX skill: run the all-protocol media server AND look up its
official docs. Detailed playbooks live in `references/`; load them on demand.

## When to use

- Host a self-hosted server that accepts any of RTSP, RTMP, HLS, WebRTC (WHIP/WHEP), SRT, MPEG-TS and transmuxes between them without transcoding.
- Author `mediamtx.yml`: paths, recording, hooks, auth (internal/HTTP/JWT), on-demand publishing, forward/proxy.
- Drive the Control API at `/v3/*` — list paths, sessions, connections, recordings; patch/delete paths; kick sessions.
- Scrape Prometheus metrics or relay/forward/proxy between servers.
- Deploy in Docker, mint test JWTs, or look up any config key, endpoint, port, or publish/read howto.

## Techniques

- Read `references/server.md` when installing the binary, writing a starter config, running/reloading/stopping the server, driving the Control API, minting JWTs, recording to disk, locking down the API, or deploying in Docker. Drive it with `scripts/mtxctl.py`.
- Read `references/api.md` when you need the full `/v3/*` Control API endpoint catalog with request/response shapes.
- Read `references/config.md` when you need the annotated `mediamtx.yml` with every knob and its default.

## Docs lookup

ALWAYS confirm a MediaMTX config key, `/v3/*` endpoint, default port, auth mode,
or howto against the official docs BEFORE naming it — this is the
anti-hallucination guardrail. Read `references/docs-search.md` for the workflow
and run `scripts/mtxdocs.py` (`list-pages` / `search` / `section` / `fetch` /
`index`). `references/pages.md` is the full page catalog. When mediamtx.org lags
a release, search `github-mediamtx.yml` (the raw upstream YAML) — it carries
every default inline and is the ground truth.

## Gotchas

- **MediaMTX does NOT transcode — it remuxes only.** If a publisher pushes HEVC and a reader wants WebRTC in the browser, playback FAILS (browsers don't support HEVC in WebRTC). Fix: chain an external ffmpeg that re-encodes into a second path. Publish H.264 + Opus when in doubt.
- **Repo is now `bluenviron/mediamtx`** (was `aler9/rtsp-simple-server`). Old install scripts, Docker tags (`aler9/rtsp-simple-server:latest`), and StackOverflow answers reference the dead name — ignore them. Current image: `bluenviron/mediamtx:latest`.
- **Control API lives at `/v3/*`**, NOT `/v2/*` or `/v1/*`. Any tutorial referencing `/v2` is obsolete.
- **API 9997 is UNAUTHENTICATED by default.** Exposing it beyond `127.0.0.1` lets anyone add paths, rewrite config, or kick sessions. Require the `api` action via `authInternalUsers` and firewall the port.
- **`authMethod` is global, not per-path.** You can't use `internal` for RTSP but `jwt` for WebRTC. Per-path granularity comes from the `permissions` list inside each user entry.
- **Default ports are independent listeners.** RTSP 8554, RTSPS 8322, RTMP 1935, RTMPS 1936, HLS 8888, WebRTC 8889 (WHIP/WHEP over HTTP), SRT 8890, API 9997, Metrics 9998, Playback 9996, pprof 9999. Disable unused ones (`rtsp: no`, etc.) — exposing them all is needless attack surface.
- **SRT routing is via streamId**: `srt://host:8890?streamid=publish:<path>:<user>:<pass>` to publish, `read:...` to read. Most clients default to `streamid=live` — you must set it.
- **`mediamtx.yml` hot-reloads on SIGHUP** for almost every key. Exceptions needing a full restart: listening addresses, TLS certs, API address.

## Scripts

- `scripts/mtxctl.py` — server lifecycle + Control API wrapper. Subcommands: `install`, `init-config`, `start`, `reload`, `stop`, `paths-list`, `sessions-list`, `recordings-list`, `api`, `mint-jwt`. Honors `MEDIAMTX_BIN`, `MEDIAMTX_PID`, `MEDIAMTX_API`.
- `scripts/mtxdocs.py` — docs search/fetch. Subcommands: `list-pages`, `search`, `section`, `fetch`, `index`, `clear-cache`. Cache dir via `MEDIAMTX_DOCS_CACHE`.

Both support `--dry-run` and `--verbose`. Reference via
`${CLAUDE_PLUGIN_ROOT}/skills/mediamtx/scripts/<file>.py` from other skills.

Companion skills: `ffmpeg-streaming` / `ffmpeg-whip` to publish via ffmpeg,
`gstreamer-pipeline` to publish via GStreamer.
