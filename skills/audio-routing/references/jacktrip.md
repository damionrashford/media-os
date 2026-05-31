# JackTrip

JackTrip sends uncompressed multichannel PCM over UDP. Designed at Stanford
CCRMA for remote ensemble performance where compression codec latency / FEC
re-buffering would break timing.

Docs: <https://jacktrip.github.io/jacktrip/> — source: <https://github.com/jacktrip/jacktrip>

---

## Modes

### Peer-to-peer server

One side runs as server (listens on a UDP port), the other side connects.
Traffic is bidirectional.

```bash
jacktrip -s -n 2                 # server, 2 channels
jacktrip -c <server-ip> -n 2     # client
```

Server prints its IP and waits. Once the client connects, both sides see JACK
client named `JackTrip` with `send_*` outputs and `receive_*` inputs.

### Hub mode (many-to-many)

A single hub relays audio between N connected clients. Scales past 2 peers.

```bash
jacktrip -S                              # hub server
jacktrip -C <hub-ip>                     # hub client (x N)
```

The hub must have enough uplink to sum + forward all participant streams.

### JackTrip Virtual Studio (JTVS)

Commercial cloud hub at <https://www.jacktrip.com/virtual-studio/>.
Consumes JackTrip clients; web UI replaces ad-hoc IP config.

---

## Ports

Default UDP port: **`4464`**.

Each connected peer/channel pair uses a separate UDP port starting at the base
port. Peer negotiation happens at `4464`; the data streams move to
`base + peer_id + channel`.

Firewall requirements:

- **Server / hub:** inbound UDP on `4464` (negotiation) and a range
  (usually `4464` → `4464 + N_peers * N_channels`).
- **Client:** outbound UDP unrestricted to the negotiated ports, and inbound
  UDP on the return path (most consumer routers pinhole this via symmetric NAT;
  failing that, UPnP or explicit forwarding).

Change the base port:

```bash
jacktrip -s -B 4500
```

---

## Key flags

| Flag | Meaning |
|---|---|
| `-s` / `-c <host>` | Server / client mode (peer-to-peer). |
| `-S` / `-C <host>` | Hub server / hub client. |
| `-n <N>` | Number of audio channels (default 2). |
| `-q <N>` | Receive queue length in packets. Trades latency for dropout tolerance. 4 is tight, 16 is slack. |
| `-r <N>` | Redundant packets (FEC) per audio packet. 1 = none, 2+ adds latency but survives UDP loss. |
| `-B <port>` | Base UDP port (default 4464). |
| `-z` / `--zerounderrun` | Send silence instead of leaving stale audio when a packet is late. |
| `-b 16` / `-b 24` / `-b 32` | Bits per sample. 32 = f32 native JACK float. |
| `--udprt` | Use UDP RT scheduling class. |
| `--remotename <N>` | Override the JACK client name on the remote side. |
| `-y auto` | Auto-select sample rate / buffer size from the JACK server. |

Full CLI reference: `jacktrip --help` or the GitHub README.

---

## Latency budget

```
one_way = network_RTT / 2
        + audio_interface_latency_local
        + audio_interface_latency_remote
        + jack_period_local
        + jack_period_remote
        + receive_queue_length * jack_period_remote
```

Typical campus LAN (sub-ms RTT), 128 frames @ 48k both sides, queue 4:

```
  0.5 ms + 3 ms + 3 ms + 2.7 ms + 2.7 ms + 4 * 2.7 ms ≈ 22.5 ms
```

Going across a 60 ms RTT connection adds 30 ms one-way. Below ~30 ms total is
"ensemble playable"; above 50 ms players instinctively drag.

---

## Quality of service

- No compression at all — raw interleaved PCM. 2 channels × 48 kHz × 32 bits
  ≈ 3.1 Mbit/s before overhead.
- No retransmit. Lost packets are **lost** (or filled with silence / last value
  depending on `-z`).
- Raising `-r` (redundancy) sends each packet N times, which survives bursty
  loss at the cost of N× bandwidth and N-1 periods of additional latency.
- Raising `-q` (queue) absorbs jitter but adds latency monotonically.

---

## Common JACK port wiring

After a JackTrip session is up, both sides have a `JackTrip` client:

```bash
# Route local mic to remote listener (send):
jack_connect system:capture_1 JackTrip:send_1
jack_connect system:capture_2 JackTrip:send_2

# Route incoming remote audio to local headphones (receive):
jack_connect JackTrip:receive_1 system:playback_1
jack_connect JackTrip:receive_2 system:playback_2
```

---

## Troubleshooting

- **Audio one-way:** Server side receives, client side doesn't. Usually
  client-side firewall blocks the inbound UDP. Confirm with `tcpdump -i any -n udp`.
- **Choppy / glitchy:** Too small a `-q` for the link jitter. Try `-q 8`. Or
  raise `-r` if loss rate is observable.
- **Clock drift after a long session:** Each side runs its own clock. JackTrip
  doesn't sync them. After an hour they can drift by a sample period. Restart
  the session, or use the `--timeout-fade` and packet-loss-concealment options
  on recent builds.
- **"Waiting for Peer":** Negotiation blocked. Check UDP 4464 open both ways,
  and that both sides use the same channel count (`-n`).
