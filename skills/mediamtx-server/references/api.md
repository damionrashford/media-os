# MediaMTX Control API (`/v3/*`)

The MediaMTX Control API is a JSON REST surface exposed by the `api` listener
(default `127.0.0.1:9997`). Authoritative reference: `mediamtx-docs` ->
`references/control-api`, or the upstream OpenAPI spec at
`https://raw.githubusercontent.com/bluenviron/mediamtx/main/apidocs/openapi.yaml`.

This page documents every endpoint family with example request/response
shapes. Auth (when enabled) is HTTP Basic using a user that has the `api`
action.

---

## Global config

### `GET /v3/config/global/get`

Returns the fully-effective config as loaded by the server (YAML + defaults
merged).

```json
{
  "logLevel": "info",
  "api": true,
  "apiAddress": ":9997",
  ...
}
```

### `PATCH /v3/config/global/patch`

Partially update the global config. JSON body is the subset of keys to
change. Hot-reloads immediately; keys that need a restart are rejected with
400.

```bash
curl -u admin:pw -X PATCH http://127.0.0.1:9997/v3/config/global/patch \
  -H 'Content-Type: application/json' \
  -d '{"logLevel":"debug"}'
```

---

## Path defaults

### `GET /v3/config/pathdefaults/get`

Returns the `pathDefaults` section of the config (defaults applied to every
path unless overridden).

### `PATCH /v3/config/pathdefaults/patch`

Update the defaults. All paths inherit the new values unless they
override them.

---

## Paths (configured)

### `GET /v3/config/paths/list`

List every configured path (from YAML + runtime-added).

```json
{
  "itemCount": 2,
  "pageCount": 1,
  "items": [
    { "name": "all_others", ...},
    { "name": "camera1", "source": "rtsp://...", ...}
  ]
}
```

### `GET /v3/config/paths/get/{name}`

Fetch a single path's configuration.

### `POST /v3/config/paths/add/{name}`

Add a new path. Body = path config object.

```bash
curl -u admin:pw -X POST \
  http://127.0.0.1:9997/v3/config/paths/add/newcam \
  -H 'Content-Type: application/json' \
  -d '{"source":"rtsp://10.0.0.42:554/live","sourceOnDemand":true}'
```

### `PATCH /v3/config/paths/patch/{name}`

Update specific keys on an existing path.

### `PUT /v3/config/paths/replace/{name}`

Full replacement of a path's config (like PUT idempotent).

### `DELETE /v3/config/paths/delete/{name}`

Remove a path.

---

## Paths (live)

### `GET /v3/paths/list`

Every active path, including automatically-created ones (e.g. ad-hoc RTMP
publishes via `all_others`). Returns source + reader counts, caps.

```json
{
  "itemCount": 1,
  "items": [
    {
      "name": "live/cam1",
      "confName": "all_others",
      "source": {"type": "rtspSession", "id": "abc"},
      "ready": true,
      "readyTime": "2026-04-17T12:00:00Z",
      "tracks": ["H264", "MPEG-4-Audio"],
      "bytesReceived": 12345678,
      "bytesSent": 98765432,
      "readers": [...]
    }
  ]
}
```

### `GET /v3/paths/get/{name}`

One path by name.

---

## RTSP sessions + connections

### `GET /v3/rtspconns/list`

List raw RTSP TCP connections (before they become sessions).

### `GET /v3/rtspsessions/list`

List RTSP sessions (a session = an established SETUP+PLAY/RECORD sequence).

Each item has: `id`, `created`, `remoteAddr`, `state`
(`idle|read|publish`), `path`, `transport`, `bytesReceived`,
`bytesSent`.

### `POST /v3/rtspsessions/kick/{id}`

Forcibly terminate a session.

### `GET /v3/rtspsconns/list` + `GET /v3/rtspssessions/list` + `POST /v3/rtspssessions/kick/{id}`

Same, but for RTSPS (TLS).

---

## RTMP connections

### `GET /v3/rtmpconns/list`

Each item: `id`, `created`, `remoteAddr`, `state` (`idle|read|publish`),
`path`, `bytesReceived`, `bytesSent`.

### `POST /v3/rtmpconns/kick/{id}`

Kick a connection.

### `GET /v3/rtmpsconns/list` + `POST /v3/rtmpsconns/kick/{id}`

Same, but RTMPS.

---

## HLS

### `GET /v3/hlsmuxers/list`

List active HLS muxers (one per path being served over HLS).

Each item: `path`, `created`, `lastRequest`, `bytesSent`.

---

## WebRTC

### `GET /v3/webrtcsessions/list`

List active WebRTC sessions (WHIP publishers + WHEP readers).

Each item: `id`, `created`, `remoteAddr`, `peerConnectionEstablished`,
`localCandidate`, `remoteCandidate`, `state` (`read|publish`), `path`,
`bytesReceived`, `bytesSent`.

### `POST /v3/webrtcsessions/kick/{id}`

Close a WebRTC session.

---

## SRT

### `GET /v3/srtconns/list`

List active SRT connections.

Each item: `id`, `created`, `remoteAddr`, `state` (`read|publish`), `path`,
`bytesReceived`, `bytesSent`, plus SRT stats (RTT, packets lost, retransmitted).

### `POST /v3/srtconns/kick/{id}`

Close an SRT connection.

---

## Recordings

### `GET /v3/recordings/list`

List paths that have recordings on disk.

```json
{
  "items": [
    {
      "name": "live/cam1",
      "segments": [
        { "start": "2026-04-17T10:00:00Z", "duration": "3600s", ...},
        { "start": "2026-04-17T11:00:00Z", "duration": "3600s", ...}
      ]
    }
  ]
}
```

### `GET /v3/recordings/get/{name}`

Recordings for one path.

### `DELETE /v3/recordings/deletesegment?path={p}&start={iso-time}`

Delete a single segment.

---

## Playback (separate listener at :9996)

`/get?path=live/cam1&start=2026-04-17T10:00:00Z&duration=60s` returns an
fMP4 blob that plays in browsers / VLC. Not on the `/v3/*` API surface;
it's on its own `:9996` listener.

---

## Auth modes — endpoint cross-reference

The API itself is protected by whichever `authMethod` the server is
configured with:

### Internal (`authMethod: internal`)

HTTP Basic with a user from `authInternalUsers` that has `action: api`:

```bash
curl -u admin:pw http://127.0.0.1:9997/v3/paths/list
```

### HTTP (`authMethod: http`)

MediaMTX POSTs credentials to the configured external URL
(`authHTTPAddress`). Your endpoint returns 200 OK or 401.

### JWT (`authMethod: jwt`)

Token passed either as `Authorization: Bearer <token>` header or
`?jwt=<token>` query param.

Token payload must include `mediamtx_permissions: [{action, path}, ...]`.
`mtxctl.py mint-jwt` builds one with HMAC HS256.

---

## Error format

Every 4xx/5xx response is:

```json
{
  "error": "human-readable reason"
}
```

Common codes:
- `400` — malformed body / unknown key.
- `401` — auth required / invalid credentials.
- `404` — path/session/recording not found.
- `409` — path name already exists.
- `500` — internal error (check server log).

---

## Pagination

List endpoints return `{itemCount, pageCount, items}`. Paginate with
`?page=N&itemsPerPage=M` query params (default 100 items/page).

---

## Metrics (Prometheus, separate listener :9998)

`GET /metrics` (NOT on `/v3/*`). Returns Prometheus text format with:

- `paths{name, state}` — gauge per active path.
- `rtsp_conns{state}` / `rtsp_sessions{state}` gauges.
- `rtmp_conns{state}`.
- `hls_muxers`.
- `webrtc_sessions{state}`.
- `srt_conns{state}`.
- Bytes in/out counters per category.

Scrape it with Prometheus; alert on stuck states.

---

## pprof (Go runtime profiler, separate listener :9999)

`GET /debug/pprof/*`. Standard `net/http/pprof` surface — goroutines, heap,
CPU profile, mutex contention. Password-protect in production.
