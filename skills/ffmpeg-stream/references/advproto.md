# Advanced streaming protocols reference (RIST / ZMQ / prompeg / Icecast / multicast)

This file is a look-up reference loaded from `SKILL.md`. Keep it open when
tuning RIST buffers, authoring ZMQ commands, sizing prompeg FEC, choosing an
Icecast content-type, or comparing latencies.

## 1. RIST Simple vs Main profile

| Feature | Simple (profile=0) | Main (profile=1) |
|---|---|---|
| Spec | VSF TR-06-1 | VSF TR-06-2 |
| Authentication | none | CNAME + shared secret |
| Encryption | none | DTLS (AES-128 / AES-256) |
| FEC / ARQ | yes (ARQ + optional FEC) | yes |
| Multipath | yes (via peers) | yes (via peers) |
| Tunneling | GRE-over-UDP | GRE-over-UDP inside DTLS |
| Compatibility | any Simple endpoint | Main-only endpoints |
| Internet-safe | LAN/VPN only | yes |
| Negotiation | manual | automatic DTLS handshake |
| librist default | profile=1 (main) in recent builds — verify with `?profile=0/1` |

**Rule:** both peers must pick the same profile. Mismatched profiles fail at connect time with a "no session" error.

## 2. RIST URL option catalog

Form: `rist://[host][:port][?key=value&key=value...]`

Prefix `@` to bind as a listener: `rist://@:1234`.

Key options (confirmed against `ffmpeg-protocols` §3.22):

| Option | Values | Meaning |
|---|---|---|
| `rist_profile` / `profile` | 0 = simple, 1 = main, 2 = advanced | Protocol profile |
| `buffer_size` | 0-30000 (ms) | ARQ retransmit window. 0 = librist default (1000 ms) |
| `fifo_size` | power of 2, default 8192 | Receive FIFO packets |
| `overrun_nonfatal` | 0 / 1 | Keep running after FIFO overrun |
| `pkt_size` | multiple of 188 | MPEG-TS packet size, default 1316 |
| `log_level` | int | librist log verbosity |
| `secret` | string | Shared secret (main profile) |
| `encryption_type` | 0/1/2 | none / AES-128 / AES-256 |
| `username` | string | Main profile auth |
| `password` | string | Main profile auth |
| `cname` | string | Session identifier — send different cnames for bonded peers |
| `peers` | `weight@host:port[,...]` | Add secondary paths (bonded / seamless) |
| `min_retries` | int | Minimum ARQ retries |
| `max_retries` | int | Max ARQ retries |
| `reorder_buffer_size` | ms | Receiver reorder window |

**Buffer sizing rule of thumb:** `buffer_size ≈ 2 × RTT`. LAN: 100-500 ms. Transcontinental: 2000-3000 ms. Satellite/cellular: 5000+ ms.

**Multi-path example:**
```
rist://primary.host:1234?peers=1000@secondary.host:2345,500@tertiary.host:3456
```
Weights are relative; higher = preferred path. librist round-robins + recovers across paths.

## 3. ZMQ filter runtime API

The `zmq` filter ships with FFmpeg (not the `zmq://` URL protocol). Embed it in any filter chain to turn other filters' runtime commands into a remote-control channel.

### Server syntax

```
[in]<filter>,zmq=bind_address=tcp\\://*\\:5555[out]
```
Note: inside `-filter_complex`, `:` and `/` in option values must be backslash-escaped. Some shells need double-backslash (`\\\\:`).

### Client wire format

REQ/REP socket. Each request is a single UTF-8 string:
```
<FILTER_INSTANCE> <COMMAND> <VALUE>
```
- `FILTER_INSTANCE`: ffmpeg auto-names filters as `Parsed_<name>_<index>`. First `drawtext` = `Parsed_drawtext_0`.
- `COMMAND`: the filter's registered command name (usually matches the option name).
- `VALUE`: the new value. Whitespace-separated; use quotes on the client side if the value contains spaces. Example: `Parsed_drawtext_0 text Hello\ World`.

### Response format

- `0 Success` — command accepted.
- `<nonzero> <error message>` — rejected (bad command, bad value, unknown instance).

### Filters with common runtime commands

| Filter | Commands |
|---|---|
| `drawtext` | `reinit`, `text`, `fontsize`, `x`, `y`, `fontcolor` (partial) |
| `drawbox` | `x`, `y`, `w`, `h`, `c` (via reinit-style) |
| `volume` | `volume` |
| `crop` | `x`, `y`, `w`, `h` |
| `setpts` / `asetpts` | `expr` |
| `eq` | `contrast`, `brightness`, `saturation`, `gamma` |
| `hue` | `h`, `s`, `H`, `b` |
| `scale` | `w`, `h` (limited) |

Check `ffmpeg -h filter=<name>` — if "This filter supports the following commands:" appears, those names are the ZMQ commands.

### Python client stub

```python
import zmq
ctx = zmq.Context()
s = ctx.socket(zmq.REQ)
s.connect("tcp://localhost:5555")
s.send_string("Parsed_drawtext_0 text LIVE NOW")
print(s.recv_string())  # expect "0 Success"
```

### zmqshell.py

Ships in FFmpeg source under `tools/zmqshell.py`. Interactive REPL: launch with the bind address, type command lines, see responses. Useful for ops / on-air board.

## 4. prompeg FEC sizing

Pro-MPEG Code of Practice #3 Release 2 is a row+column Reed-Solomon code over RTP-MPEGTS payloads.

- **Matrix:** L columns × D rows of source packets.
- **Parity:** L "column" packets + D "row" packets per L×D source group.
- **Overhead:** `(L + D) / (L × D)`.
- **Constraints (per spec):** `1 ≤ L ≤ 20`, `4 ≤ D ≤ 20`, `L × D ≤ 100`.

### Sizing table

| L | D | Group | Parity | Overhead | Typical use |
|---|---|---|---|---|---|
| 4 | 4 | 16 | 8 | 50% | Very lossy, low latency tolerated |
| 5 | 5 | 25 | 10 | 40% | Default "safe" |
| 6 | 6 | 36 | 12 | 33% | |
| 8 | 4 | 32 | 12 | 37.5% | Broadcast norm, row-dominant |
| 10 | 5 | 50 | 15 | 30% | Moderate loss |
| 10 | 10 | 100 | 20 | 20% | High-efficiency, higher latency |

**Rule:** bigger L×D = better recovery of bursty loss but higher recovery latency (decoder waits for a full group). Keep `L × D ≤ 100`.

### Caveats

- prompeg requires the `rtp_mpegts` muxer (not plain `rtp`).
- FEC is feed-forward only; there's no retransmit. Combine with RIST/SRT for mission-critical links.
- Receiver-side recovery is automatic in ffmpeg when it reads `rtp_mpegts` with prompeg-tagged streams.

## 5. Icecast / Shoutcast URL schemes

### Icecast2 (ffmpeg's native)

```
icecast://<source-user>:<source-password>@<host>:<port>/<mount>
```

Server defaults:
- Port 8000
- Source user = `source`
- Mount names start with `/`: `/live`, `/stream.mp3`, etc.

Options:
- `-content_type <mime>` — MUST match payload for non-MP3. `audio/mpeg`, `audio/ogg`, `audio/aac`.
- `-ice_name`, `-ice_description`, `-ice_genre`, `-ice_url` — metadata.
- `-ice_public 1` — list in public directory (default 0).
- `-user_agent` — override libshout default.
- `-legacy_icecast 1` — old server < 2.4.0 compat.

### Shoutcast v1

ffmpeg talks the Icecast source protocol; some Shoutcast servers accept it on the DJ port (`port + 1`). Mount is `/`. Password only (no user). Set `-legacy_icecast 1`.

### Content-type matrix

| Codec | `-c:a` | `-f` | `-content_type` |
|---|---|---|---|
| MP3 | libmp3lame | mp3 | audio/mpeg |
| Vorbis | libvorbis | ogg | audio/ogg |
| Opus | libopus | ogg | audio/ogg |
| AAC | aac | adts | audio/aac |
| FLAC | flac | ogg | audio/ogg |

## 6. MPEG-TS packet size and MTU

MPEG-TS stream packets are **always 188 bytes**. The `pkt_size` UDP/RIST/SRT option controls how many TS packets are batched per IP datagram.

- Must be a multiple of 188.
- Default: 1316 bytes = 7 × 188. Fits in a 1500-byte Ethernet MTU after IP(20) + UDP(8) headers.
- Jumbo frames: `pkt_size=7520` (40 × 188) if the entire path has MTU ≥ 9000.

Wrong sizes silently fragment or mis-align TS sync bytes on the receiver.

## 7. Latency comparison

End-to-end glass-to-glass (encoder input → decoder output), typical:

| Transport | Latency | Reliability | Notes |
|---|---|---|---|
| RIST (simple) | 100-500 ms | ARQ + FEC | LAN/VPN |
| RIST (main) | 100-500 ms | ARQ + FEC + DTLS | Internet contribution |
| SRT | 120-500 ms | ARQ | Similar to RIST, single path |
| RTP + prompeg | 30-100 ms | FEC only | No retransmit |
| RTP (raw) | 20-80 ms | none | LAN or UDP tunnel |
| UDP multicast | 10-50 ms | none | LAN one-to-many |
| RTMP | 2-5 s | TCP (in-order) | Legacy ingest |
| HLS | 6-30 s | segmented HTTP | Scales infinitely |
| DASH | 6-30 s | segmented HTTP | Same class as HLS |
| LL-HLS / LL-DASH | 2-6 s | chunked HTTP | Lower-latency variants |
| WebRTC / WHIP | 150-500 ms | ICE + SRTP | Sub-second, browser-playable |
| Icecast | 5-15 s | TCP | Buffered radio |

## 8. Recipe book

### R1. Studio-to-studio RIST main profile with bonded links

**Sender:**
```
ffmpeg -re -i cam.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency -b:v 10M -maxrate 10M -bufsize 10M \
  -x264-params "nal-hrd=cbr:force-cfr=1" -g 60 \
  -c:a aac -b:a 192k \
  -f mpegts \
  "rist://studio-a.example.com:2000?profile=main&secret=hunter2&cname=cam1&encryption_type=1&peers=1000@studio-a-b.example.com:2001"
```

**Receiver:**
```
ffmpeg -i "rist://@:2000?profile=main&secret=hunter2&buffer_size=2000" \
  -c copy master.ts
```

### R2. Remote filter bypass / re-tune via ZMQ

Launch once, mutate forever:
```
ffmpeg -re -i in.mp4 \
  -filter_complex "[0:v]drawtext=text='OFF AIR':fontsize=72:x=(w-tw)/2:y=(h-th)/2:fontcolor=red,zmq=bind_address=tcp\\://127.0.0.1\\:5555[v]" \
  -map "[v]" -map 0:a -c:v libx264 -c:a aac out.mp4
```
Flip to on-air:
```
python3 -c "import zmq; s=zmq.Context().socket(zmq.REQ); s.connect('tcp://127.0.0.1:5555'); s.send_string('Parsed_drawtext_0 text ON AIR'); print(s.recv_string())"
```

### R3. Internet radio via Icecast

```
ffmpeg -re -stream_loop -1 -i playlist.m3u \
  -c:a libmp3lame -b:a 192k -ar 44100 \
  -content_type audio/mpeg \
  -ice_name "Deep Focus" \
  -ice_description "ambient + piano, 24/7" \
  -ice_genre "Ambient" -ice_public 1 \
  -f mp3 "icecast://source:secret@stream.example.com:8000/live"
```

### R4. Lossy 4G uplink with prompeg

```
ffmpeg -f avfoundation -framerate 30 -i "0:0" \
  -c:v libx264 -preset veryfast -tune zerolatency -b:v 3M \
  -c:a aac -b:a 96k \
  -f rtp_mpegts -fec prompeg=l=8:d=4 \
  "rtp://cloud-ingest.example.com:5000"
```
Heavier L=8, D=4 to absorb bursty cellular loss.

### R5. One-to-many UDP multicast to every screen in the building

```
ffmpeg -re -i lecture.mp4 -c copy \
  -f mpegts "udp://239.10.20.30:5000?pkt_size=1316&ttl=3"
```
Receivers: `ffplay "udp://@239.10.20.30:5000?fifo_size=2000000&overrun_nonfatal=1"`.

## 9. Gotchas

- RIST buffer too small = dropped frames on bad links. Buffer too big = latency balloons.
- ZMQ filter cannot add/remove filters — only tune existing params. Re-structure requires restart.
- prompeg only works with `rtp_mpegts` muxer, and `L×D ≤ 100`.
- Icecast mounts are single-use; duplicate source connections are rejected with HTTP 403.
- Multicast TTL=1 (default) never leaves the local link. Raise TTL *and* ensure router supports multicast routing.
- ffmpeg builds without `--enable-librist` / `libzmq` / `libshout` silently fail to find the protocol — always `ffmpeg -buildconf` first.
