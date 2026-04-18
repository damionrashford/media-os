# MediaMTX `mediamtx.yml` — Annotated Reference

Every knob in `mediamtx.yml`, grouped by function, with defaults.

Authoritative source: the shipped `mediamtx.yml` in the release tarball,
or upstream at
`https://raw.githubusercontent.com/bluenviron/mediamtx/main/mediamtx.yml`.

The `mtxctl.py init-config` subcommand writes a production-leaning subset
of this; this page is the full menu.

---

## Top-level sections

```yaml
# Logging
logLevel: info            # debug | info | warn | error
logDestinations: [stdout] # combo of: stdout, file, syslog
logFile: mediamtx.log     # path when `file` is in logDestinations

# Read / write buffer sizes -- tune under heavy UDP load
readTimeout: 10s
writeTimeout: 10s
writeQueueSize: 512       # power of 2
udpMaxPayloadSize: 1472   # RTP UDP MTU

# Runtime
runOnConnect: ''
runOnConnectRestart: no
runOnDisconnect: ''
```

---

## API / metrics / pprof / playback listeners

```yaml
api: yes
apiAddress: :9997
apiEncryption: no         # wrap /v3/* in TLS
apiServerKey: server.key
apiServerCert: server.crt
apiAllowOrigin: '*'
apiTrustedProxies: []

metrics: yes
metricsAddress: :9998
metricsEncryption: no
metricsServerKey: server.key
metricsServerCert: server.crt
metricsAllowOrigin: '*'
metricsTrustedProxies: []

pprof: no
pprofAddress: :9999
pprofEncryption: no
pprofServerKey: server.key
pprofServerCert: server.crt
pprofAllowOrigin: '*'
pprofTrustedProxies: []

playback: yes
playbackAddress: :9996
playbackEncryption: no
playbackServerKey: server.key
playbackServerCert: server.crt
playbackAllowOrigin: '*'
playbackTrustedProxies: []
```

---

## RTSP

```yaml
rtsp: yes
rtspTransports: [udp, multicast, tcp]   # order of preference
rtspEncryption: 'no'                    # 'no' | 'strict' | 'optional'
rtspAddress: :8554
rtspsAddress: :8322
rtpAddress: :8000
rtcpAddress: :8001
multicastIPRange: 224.1.0.0/16
multicastRTPPort: 8002
multicastRTCPPort: 8003
rtspServerKey: server.key
rtspServerCert: server.crt
rtspAuthMethods: [basic]                # basic | digest (digest deprecated by most clients)
```

---

## RTMP

```yaml
rtmp: yes
rtmpAddress: :1935
rtmpEncryption: 'no'                    # 'no' | 'strict' | 'optional'
rtmpsAddress: :1936
rtmpServerKey: server.key
rtmpServerCert: server.crt
```

---

## HLS

```yaml
hls: yes
hlsAddress: :8888
hlsEncryption: no
hlsServerKey: server.key
hlsServerCert: server.crt
hlsAllowOrigin: '*'
hlsTrustedProxies: []
hlsAlwaysRemux: no
hlsVariant: lowLatency      # mpegts | fmp4 | lowLatency
hlsSegmentCount: 7          # number of segments in the playlist
hlsSegmentDuration: 1s      # (LL-HLS: 1-2s; standard: 6s+)
hlsPartDuration: 200ms      # LL-HLS only
hlsSegmentMaxSize: 50M
hlsDirectory: ''            # persist segments to disk (default: memory only)
hlsMuxerCloseAfter: 60s     # keep muxer alive this long after last viewer
```

---

## WebRTC (WHIP/WHEP)

```yaml
webrtc: yes
webrtcAddress: :8889
webrtcEncryption: no
webrtcServerKey: server.key
webrtcServerCert: server.crt
webrtcAllowOrigin: '*'
webrtcTrustedProxies: []
webrtcLocalUDPAddress: :8189       # ICE host candidate UDP
webrtcLocalTCPAddress: ''          # optional TCP ICE fallback
webrtcIPsFromInterfaces: yes
webrtcIPsFromInterfacesList: []    # e.g. [eth0, wlan0]
webrtcAdditionalHosts: []          # announce these as host candidates
webrtcICEServers2:                 # STUN + TURN for NAT traversal
  - url: stun:stun.l.google.com:19302
  # - url: turn:turn.example.com:3478
  #   username: me
  #   password: pw
  #   clientOnly: yes
webrtcHandshakeTimeout: 10s
webrtcTrackGatherTimeout: 2s
webrtcSTUNGatherTimeout: 5s
```

---

## SRT

```yaml
srt: yes
srtAddress: :8890
```

---

## Authentication

```yaml
# 'internal' | 'http' | 'jwt'
authMethod: internal

# ── internal ─────────────────────────────────────────────────────────────
authInternalUsers:
  - user: any                 # 'any' means no authentication for this user
    pass: ''
    ips: []                   # CIDRs: restrict by source IP
    permissions:
      - action: publish       # publish | read | playback | api | metrics | pprof
        path: ''              # optional: regex on path (empty = all)
      - action: read
        path: ''
  - user: admin
    pass: CHANGE_ME
    ips: [127.0.0.1/32]
    permissions:
      - action: api
      - action: metrics
      - action: pprof

# ── http ─────────────────────────────────────────────────────────────────
# MediaMTX POSTs the request details to this URL; you return 200 or 401.
authHTTPAddress: http://localhost:8000/auth
authHTTPExclude:
  - action: api
  - action: metrics
  - action: pprof

# ── jwt ──────────────────────────────────────────────────────────────────
# Either jwtJWKSURL (RSA keys) OR provide a static HMAC secret in auth code.
authJWTJWKS: ''
authJWTJWKSFingerprint: ''
authJWTClaimKey: mediamtx_permissions
authJWTExclude:
  - action: api
  - action: metrics
```

---

## Path defaults + per-path config

```yaml
pathDefaults:
  # Source selection — how this path gets its media
  source: publisher           # publisher | rtsp:// | rtmp:// | hls:// | srt:// | udp://...
  sourceFingerprint: ''
  sourceOnDemand: no
  sourceOnDemandStartTimeout: 10s
  sourceOnDemandCloseAfter: 10s
  maxReaders: 0
  srtReadPassphrase: ''

  # RTSP source tweaks
  rtspTransport: automatic    # automatic | udp | multicast | tcp
  rtspAnyPort: no
  rtspRangeType: ''           # clock | npt | smpte
  rtspRangeStart: ''

  # Redirect
  sourceRedirect: ''

  # Recording
  record: no
  recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S-%f
  recordFormat: fmp4          # fmp4 | mpegts
  recordPartDuration: 1s
  recordSegmentDuration: 1h
  recordDeleteAfter: 24h

  # Publisher / reader hooks (shell commands)
  overridePublisher: yes
  fallback: ''

  runOnInit: ''
  runOnInitRestart: no
  runOnDemand: ''             # spawn a publisher when first reader connects
  runOnDemandRestart: no
  runOnDemandStartTimeout: 10s
  runOnDemandCloseAfter: 10s
  runOnUnDemand: ''
  runOnReady: ''              # fires when source becomes ready
  runOnReadyRestart: no
  runOnNotReady: ''
  runOnRead: ''               # fires when a reader connects
  runOnReadRestart: no
  runOnUnread: ''
  runOnRecordSegmentCreate: ''
  runOnRecordSegmentComplete: ''

paths:
  # Static path: publisher pushes, readers subscribe
  live:

  # Path that proxies a remote RTSP camera on-demand
  camera1:
    source: rtsp://user:pw@10.0.0.42:554/Streaming/Channels/101
    sourceOnDemand: yes
    sourceOnDemandCloseAfter: 30s
    record: yes
    recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S

  # Regex path: 'live/<anything>'
  'live/~^.+$':
    record: yes

  # Catch-all
  all_others:
```

Path-name special forms:

- Literal: `myname`
- Regex: prefix with `~` then the Go regex (`'~^live/.+$'`).
- Catch-all: `all_others`.

---

## Hook variables

Every hook command has these environment variables available:

| Var | Meaning |
|---|---|
| `$MTX_PATH` | Path name |
| `$MTX_QUERY` | URL query string from the client |
| `$MTX_CONN_TYPE` | rtspsConn / rtmpConn / webrtcSession / srtConn |
| `$MTX_CONN_ID` | Connection id |
| `$MTX_SOURCE_TYPE` | publisher / rtspSource / etc. |
| `$MTX_SOURCE_ID` | Source id |
| `$RTSP_USER`, `$RTSP_PASS` | When relevant |
| `$RTSP_PORT`, `$MTX_SEGMENT_PATH` | Per-hook extras |

---

## Time / size unit suffixes

- Durations: `s`, `m`, `h`, `d` (`1h`, `500ms`, `2d`).
- Sizes: `B`, `K`, `M`, `G` (`50M`).

---

## Common patterns

### On-demand RTSP camera proxy

```yaml
paths:
  cam1:
    source: rtsp://admin:pw@10.0.0.42/stream
    sourceOnDemand: yes
    sourceOnDemandCloseAfter: 60s
```

### Record every path

```yaml
pathDefaults:
  record: yes
  recordPath: ./recordings/%path/%Y/%m/%d/%H-%M-%S-%f
  recordFormat: fmp4
  recordSegmentDuration: 15m
  recordDeleteAfter: 168h   # 7 days
```

### On-demand ffmpeg publisher (spawns when reader connects)

```yaml
paths:
  synthetic:
    runOnDemand: ffmpeg -re -i /path/to/loop.mp4 -c copy -f rtsp rtsp://localhost:8554/$MTX_PATH
    runOnDemandRestart: yes
    runOnDemandCloseAfter: 10s
```

### Webhook-style hook on reader connect

```yaml
pathDefaults:
  runOnRead: curl -s -X POST http://hooks.local/joined -d "path=$MTX_PATH&id=$MTX_CONN_ID"
```

### Forward one path to another server

```yaml
paths:
  live/cam1:
    source: publisher
    # Not a built-in — author via runOnReady to launch an ffmpeg bridge, or
    # use the `features/forward` page for the dedicated "forward" config key
    # in the server-global section (see mediamtx-docs).
```

---

## Keys that require full restart (no SIGHUP hot-reload)

- Any `*Address` listener (rtspAddress, rtmpAddress, etc.).
- TLS cert + key paths.
- `api`, `metrics`, `pprof`, `playback` enable flags.
- `multicastIPRange`, `webrtcLocalUDPAddress`, etc.

Everything else hot-reloads. `mtxctl.py reload` sends SIGHUP.
