# LiveKit Self-Hosted Deployment

Full canonical guide: `https://docs.livekit.io/home/self-hosting/deployment/`.

## Stack overview

```
                            ┌──────────────────┐
   Browser / mobile SDK ────►  livekit-server  │◄──── Redis (multi-node sharding)
                            │   (Go binary)    │
                            └────────┬─────────┘
                                     │ gRPC
                                     ▼
                    ┌──────── egress ────────── ingress ────────┐
                    │  (record/stream out)   (RTMP/WHIP/SRT in) │
                    └────────────────────────────────────────────┘
                                     │
                                     ▼
                         coturn (TURN) — optional but recommended
```

Components:

- `livekit-server` — the SFU.
- `livekit-egress` — composite/record rooms.
- `livekit-ingress` — RTMP/WHIP/SRT/URL → Room.
- `livekit-cli` (`lk`) — admin + load-test.
- `livekit-agents` — realtime AI.
- Redis — state store for multi-node + job queue.
- TURN — bundled Pion (enabled via config) or external `coturn`.

## Single-node YAML (`livekit.yaml`)

```yaml
port: 7880
bind_addresses: ['']
logging:
  level: info
  pion_level: warn
rtc:
  port_range_start: 50000
  port_range_end: 60000
  tcp_port: 7881
  use_external_ip: true
keys:
  APIxxxxxxxxxxxx: "secretxxxxxxxxxxxxxxxxxxxxxx"
room:
  auto_create: true
  empty_timeout: 300s
webhook:
  api_key: APIxxxxxxxxxxxx
  urls: ['https://my-app/livekit/webhook']
turn:
  enabled: true
  domain: turn.example.com
  tls_port: 5349
  udp_port: 3478
  external_tls: true   # terminate TLS at load balancer
```

Start: `livekit-server --config livekit.yaml`. Dev mode: `livekit-server --dev`.

## Multi-node config

Add Redis + cluster settings:

```yaml
redis:
  address: redis.my-cluster:6379
  username: default
  password: REDIS_PW
  db: 0
node_ip: 10.0.0.5           # this node's public IP (or detect via use_external_ip)
region: us-east
```

Every node points at the same Redis. Clients still hit any node via a single DNS record (or a round-robin LB).

## Ports to open

| Port                  | Protocol | Who   | Purpose                          |
|-----------------------|----------|-------|----------------------------------|
| `7880`                | TCP      | LB    | HTTPS + WebSocket signaling      |
| `7881`                | TCP      | Peers | WebRTC over TCP fallback         |
| `50000-60000`         | UDP      | Peers | WebRTC media (configurable range)|
| `3478`                | UDP      | Peers | TURN UDP                         |
| `5349`                | TCP      | Peers | TURN over TLS                    |
| `6379`                | TCP      | nodes | Redis (private network only)     |

## TURN options

1. **Bundled Pion TURN** — enable via `turn.enabled:true` above. Same IP as server. Simplest for small deployments.
2. **External coturn** — point clients at `turn:turn.example.com:3478?transport=udp` in `RTCConfiguration.iceServers`. Standard in production — more reliable under load than the bundled TURN.

## Container deployment

Official images (all tagged):

- `livekit/livekit-server:latest`
- `livekit/egress:latest`
- `livekit/ingress:latest`
- `livekit/livekit-cli:latest`

Minimal `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ['6379:6379']
  livekit:
    image: livekit/livekit-server:latest
    ports: ['7880:7880', '7881:7881', '50000-60000:50000-60000/udp']
    environment:
      - LIVEKIT_CONFIG_FILE=/livekit.yaml
    volumes: ['./livekit.yaml:/livekit.yaml']
    depends_on: [redis]
  egress:
    image: livekit/egress:latest
    environment:
      - EGRESS_CONFIG_FILE=/egress.yaml
    volumes: ['./egress.yaml:/egress.yaml']
    depends_on: [livekit, redis]
  ingress:
    image: livekit/ingress:latest
    ports: ['1935:1935']   # RTMP
    environment:
      - INGRESS_CONFIG_FILE=/ingress.yaml
    volumes: ['./ingress.yaml:/ingress.yaml']
    depends_on: [livekit, redis]
```

## Kubernetes

LiveKit ships a Helm chart: `https://github.com/livekit/livekit-helm`. Covers the server + egress + ingress + redis + ingress-controller hooks.

Rough shape:

```
helm repo add livekit https://helm.livekit.io
helm install livekit livekit/livekit-server \
    --set config.keys[0].key=API... \
    --set config.keys[0].secret=SECRET... \
    --set 'loadBalancerAnnotations.service\.beta\.kubernetes\.io/aws-load-balancer-type'=nlb
```

## Observability

- Prometheus metrics: `http://livekit:6789/metrics` (off by default; enable via `monitoring:` config).
- Logs: stdout — `level: debug | info | warn | error`.
- Webhook events: set `webhook.urls` → server posts JSON on `room_started`, `room_finished`, `participant_joined`, etc. Use for billing + integrations.

## LiveKit Cloud

`https://cloud.livekit.io` is the managed offering (same server, different deployment). If the user wants to avoid managing the stack, point them there. The helper's tooling is all self-hosted-first but works against cloud URLs too (just pass `--url wss://your-project.livekit.cloud`).
