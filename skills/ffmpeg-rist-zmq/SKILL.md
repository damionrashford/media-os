---
name: ffmpeg-rist-zmq
description: >
  Advanced streaming protocols with ffmpeg: RIST (rist://, Reliable Internet Streaming Transport for contribution), ZMQ (zmq:// for real-time filter-graph control via ZeroMQ), prompeg (SMPTE 2022-1 forward-error-correction), icecast (radio / shoutcast streaming), RTP-MPEGTS with FEC. Use when the user asks to stream RIST contribution, control an ffmpeg filter graph live via ZMQ, add forward-error-correction to RTP, push to an icecast radio station, or do pro-grade low-latency IP transport with FEC and reliability.
argument-hint: "[protocol]"
---

# Ffmpeg Rist Zmq

**Context:** $ARGUMENTS

## Quick start

- **Send RIST contribution (caller):** → Step 3, `advproto.py rist-send`
- **Receive RIST as a listener:** → Step 3, `advproto.py rist-listen`
- **Control a running filter graph via ZMQ:** → Step 3, `advproto.py zmq-serve` + `zmq-send`
- **Protect RTP with prompeg FEC:** → Step 3, `advproto.py rtp-fec`
- **Push to an icecast radio:** → Step 3, `advproto.py icecast`
- **UDP multicast MPEG-TS:** → Step 3, `advproto.py multicast`
- **Check build support (librist / libzmq / libshout):** `advproto.py check`

## When to use

- Studio-to-studio or camera-to-cloud contribution that needs ARQ retransmission, bonded paths, and sub-second latency (RIST).
- You want to re-tune a `drawtext`, `volume`, `crop`, or any filter **while ffmpeg is live** without re-launching — ZMQ filter control.
- Legacy MPEG-TS over RTP links where packet loss is normal — add prompeg Reed-Solomon FEC.
- Streaming MP3/Opus/Vorbis to an Icecast/Shoutcast radio source.
- One-to-many LAN distribution via IP multicast.

If you just need HLS, DASH, RTMP, SRT, or RTSP — use `ffmpeg-streaming`. If you need WebRTC (WHIP) — use `ffmpeg-whip`.

## Step 1 — Pick the protocol

| Need | Protocol | URL scheme |
|---|---|---|
| Reliable contribution over lossy WAN, ARQ | RIST | `rist://host:port` |
| Multi-path bonded contribution | RIST main-profile | `rist://host:port?peers=...` |
| Re-tune filter params at runtime | ZMQ filter | filter `zmq=bind_address=tcp://*:5555` |
| Raw video/audio with FEC over RTP | prompeg + rtp_mpegts | `rtp://host:port` + `-fec prompeg=l=5:d=5` |
| Radio source to Icecast2 | icecast | `icecast://user:pass@host:port/mount` |
| LAN one-to-many | UDP multicast | `udp://239.0.0.1:1234?pkt_size=1316` |

RIST has two profiles:
- **Simple profile (0)** — GRE over UDP, basic ARQ, no auth/encryption. Works with any Simple receiver.
- **Main profile (1)** — tunnels over GRE with DTLS encryption, CNAME identification, auth. Use for Internet-exposed links.

Verify ffmpeg has the right libs:
```
ffmpeg -hide_banner -buildconf | grep -E "librist|libzmq|libshout"
```
If a lib is missing, recompile or use a build that enables it (`--enable-librist`, `--enable-libzmq`, `--enable-libshout`). Or run `advproto.py check`.

## Step 2 — Configure caller vs listener

RIST and UDP both support **caller** (initiates) and **listener** (waits) roles.

**RIST caller (sender)** — most common, sends to a known receiver:
```
ffmpeg -re -i in.mp4 -c:v libx264 -tune zerolatency -b:v 5M \
       -c:a aac -b:a 128k -f mpegts \
       "rist://receiver.ip:1234?buffer_size=1000&cname=studio-a"
```

**RIST listener (receiver bind)** — pass `@` to bind, no host:
```
ffplay "rist://@:1234?buffer_size=500"
```
or capture to file:
```
ffmpeg -i "rist://@:1234?buffer_size=500" -c copy out.ts
```

**RIST main-profile with auth/encryption**:
```
"rist://host:1234?profile=main&secret=hunter2&encryption_type=1&cname=session1"
```
`encryption_type=1` = AES-128, `=2` = AES-256 (librist-dependent).

**RIST multi-path (bonded)** — add secondary peers:
```
"rist://receiver1.ip:1234?peers=1000@receiver2.ip:2345"
```
Both paths carry the same stream; losses on one path are recovered from the other.

**ZMQ** — always **listener** on the ffmpeg side (server waits for control). Pick a `bind_address`:
- `tcp://*:5555` = bind all interfaces (fine on localhost, firewall it otherwise).
- `tcp://127.0.0.1:5555` = localhost only (safest).
- `tcp://10.0.0.5:5555` = specific NIC.

**Icecast** is always caller. URL carries source user + password:
```
icecast://source:password@icecast.example.com:8000/stream
```

**UDP multicast** — sender sets group address; all receivers join the group:
```
"udp://239.0.0.1:1234?pkt_size=1316"
```

## Step 3 — Encode + send

### RIST contribution (H.264 + AAC, 5 Mb/s)
```
ffmpeg -re -i in.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency -b:v 5M -maxrate 5M -bufsize 5M \
  -x264-params "nal-hrd=cbr:force-cfr=1" -g 60 -keyint_min 60 \
  -c:a aac -b:a 128k -ar 48000 \
  -f mpegts "rist://receiver.ip:1234?buffer_size=1000&cname=session1"
```
Use `-tune zerolatency` + CBR for stable bitrate over the RIST pipe.

### RIST listener → file
```
ffmpeg -i "rist://@:1234?buffer_size=500" -c copy archive.ts
```

### ZMQ runtime filter control (server side)
Attach `zmq` to whichever filter you want to retune. The `zmq` filter itself doesn't touch pixels — it just opens a control port:
```
ffmpeg -re -i in.mp4 \
  -filter_complex "[0:v]drawtext=text='hello':x=10:y=10:fontcolor=white,zmq=bind_address=tcp\\\\://*\\\\:5555[out]" \
  -map "[out]" -map 0:a -c:v libx264 -c:a aac out.mp4
```
Note the escaped colon/slash inside `-filter_complex`. If you prefer, put zmq at the end of the chain without its own label.

### ZMQ runtime filter control (client side)
Send commands with `python -m zmq` or the `tools/zmqshell.py` that ships with the ffmpeg source tree. Command format is whitespace-separated: `<filter_instance> <param> <value>`:
```
python3 -c "import zmq, sys; s=zmq.Context().socket(zmq.REQ); s.connect('tcp://localhost:5555'); s.send_string('Parsed_drawtext_0 text world'); print(s.recv())"
```
Or use `advproto.py zmq-send --addr tcp://localhost:5555 --command "Parsed_drawtext_0 text world"`.

Find the instance name by reading ffmpeg's stderr — the first `drawtext` in a graph is `Parsed_drawtext_0`, the second is `Parsed_drawtext_1`, etc.

### prompeg FEC on RTP-MPEGTS
```
ffmpeg -re -i in.mp4 -c:v libx264 -c:a aac \
  -f rtp_mpegts -fec prompeg=l=5:d=5 "rtp://dst.ip:5000"
```
`l` = FEC columns, `d` = FEC rows. Group = L×D packets + (L + D) parity. Higher L/D → more recoverable loss, more overhead. Typical: `l=5:d=5` (~40% overhead), `l=8:d=4` (broadcast default).

### Icecast audio push
```
ffmpeg -re -i music.mp3 -c:a libmp3lame -b:a 128k \
  -content_type audio/mpeg \
  -ice_name "My Radio" -ice_description "24/7 lofi" \
  -ice_genre "Electronic" -ice_public 1 \
  -f mp3 "icecast://source:hunter2@icecast.example.com:8000/stream"
```
For Ogg Vorbis: `-c:a libvorbis -content_type audio/ogg -f ogg`.

### UDP multicast MPEG-TS
Sender:
```
ffmpeg -re -i in.mp4 -c copy -f mpegts "udp://239.0.0.1:1234?pkt_size=1316&ttl=2"
```
Receiver:
```
ffplay "udp://@239.0.0.1:1234?fifo_size=1000000&overrun_nonfatal=1"
```

### Multi-output RTP (separate video + audio) with SDP
RTP carries one elementary stream per port, so you must emit an SDP:
```
ffmpeg -re -i in.mp4 \
  -map 0:v -c:v libx264 -an -f rtp "rtp://dst.ip:5004" \
  -map 0:a -c:a aac -vn -f rtp "rtp://dst.ip:5006" \
  -sdp_file stream.sdp
```
Then on the receiver: `ffplay -protocol_whitelist file,udp,rtp stream.sdp`.

## Step 4 — Verify + debug

- **Build check:** `ffmpeg -buildconf | grep -E "librist|libzmq|libshout"` or `advproto.py check`.
- **Protocol list:** `ffmpeg -protocols | grep -E "rist|zmq|icecast|rtp"`.
- **RIST stats:** add `-stats_period 1` and watch `fps=/bitrate=/drop=` in ffmpeg's stderr. A healthy RIST link has zero dropped packets after warmup.
- **ZMQ control round-trip:** the server replies `0 Success` on good commands, non-zero with an error string on bad ones. If you see `Bad Message`, check whitespace separation (not `=`).
- **prompeg RTT sanity:** prompeg is purely transmit-side FEC; there's no ACK. Confirm the receiver reports fewer continuity errors with it than without.
- **Icecast verify:** open `http://icecast.example.com:8000/status.xsl` — your mount should appear with current listeners.
- **Multicast reachability:** `ffplay udp://@239.0.0.1:1234` on the same LAN. If nothing — router/switch IGMP snooping is blocking.

## Available scripts

- **`scripts/advproto.py`** — subcommands: `check`, `rist-send`, `rist-listen`, `zmq-serve`, `zmq-send`, `rtp-fec`, `icecast`, `multicast`. `--dry-run` prints the exact ffmpeg command without running. Stdlib only.

## Workflow

```bash
# Check ffmpeg was built with the needed libraries:
uv run ${CLAUDE_SKILL_DIR}/scripts/advproto.py check

# RIST send:
uv run ${CLAUDE_SKILL_DIR}/scripts/advproto.py rist-send \
  --input in.mp4 --url "rist://receiver.ip:1234?buffer_size=1000&cname=s1" \
  --bitrate 5M

# ZMQ serve (run in background) + send command:
uv run ${CLAUDE_SKILL_DIR}/scripts/advproto.py zmq-serve \
  --input in.mp4 --output out.mp4 \
  --filter-expr "drawtext=text='hello':x=10:y=10:fontcolor=white" \
  --bind-addr "tcp://*:5555" &
uv run ${CLAUDE_SKILL_DIR}/scripts/advproto.py zmq-send \
  --addr tcp://localhost:5555 --command "Parsed_drawtext_0 text world"
```

## Reference docs

- Read [`references/advproto.md`](references/advproto.md) for RIST profile comparison, URL option catalog, ZMQ command API, prompeg FEC math, latency comparison, and recipe book.

## Gotchas

- **Two RIST profiles:** Simple (no auth, basic FEC/ARQ) and Main (DTLS encryption, CNAME-based auth). Both peers **must** agree — a Simple caller cannot talk to a Main listener.
- **ffmpeg build required:** `--enable-librist`, `--enable-libzmq`, `--enable-libshout` at configure time. Check `ffmpeg -buildconf`. `brew install ffmpeg` on macOS enables all three by default; distro packages often miss librist.
- **RIST `buffer_size` is milliseconds**, not bytes. It's the retransmit window — too small and losses escape; too large and latency goes up. Valid range is 0..30000 ms (0 = librist default 1000 ms).
- **Multi-path RIST:** use `?peers=...` to add secondary paths for resilience: `rist://r1.ip:1234?peers=1000@r2.ip:2345`. Both paths carry the same data; losses on one are recovered via the other.
- **ZMQ filter is runtime-only:** it mutates already-instantiated filter options without re-encoding. You cannot add or remove filters, only change their params.
- **ZMQ command syntax:** `FILTER_INSTANCE COMMAND VALUE`, whitespace-separated. Do NOT use `=`. Example: `Parsed_volume_0 volume 0.5`. Response is `0 Success` or a non-zero error code.
- **ZMQ requires pyzmq on the client** (`pip install pyzmq`) or ffmpeg's own `tools/zmqshell.py` from source. The server side in ffmpeg only needs `--enable-libzmq`.
- **`bind_address` exposure:** `tcp://*:5555` binds ALL interfaces. For anything Internet-facing, use `tcp://127.0.0.1:5555` + SSH tunnel or a specific private IP.
- **prompeg works only with `rtp_mpegts`** muxer, not plain `rtp`. Syntax: `-f rtp_mpegts -fec prompeg=l=5:d=5 rtp://...`.
- **prompeg overhead math:** L columns × D rows of source packets → (L + D) parity packets per group. Overhead ≈ `(L+D) / (L*D)`. `l=5:d=5` = 40%, `l=8:d=4` = 37.5%, `l=10:d=10` = 20% (but bigger groups = higher recovery latency).
- **Icecast URL is `icecast://user:pass@host:port/mountpoint`.** `libshout` under the hood. Set `-content_type` explicitly if not MP3 (`audio/ogg` for Vorbis, `audio/aac` for AAC — some servers reject AAC).
- **Icecast auth failures** usually mean wrong mount password or mount already in use — check `icecast.log`.
- **MPEG-TS `pkt_size` MUST be a multiple of 188 bytes.** IP MTU-friendly default is `?pkt_size=1316` (7 × 188 = 1316, fits 1500-byte MTU after headers). Values that aren't multiples of 188 silently mis-align TS packets and break receivers.
- **UDP multicast requires network support** — unmanaged switches + home routers often drop multicast. Set `?ttl=N` for routed multicast (default 1 = link-local only).
- **Multi-stream RTP needs an SDP file** for playback. ffmpeg writes SDP to stderr by default; use `-sdp_file out.sdp` to capture it cleanly.
- **Zero-latency encoding:** `-tune zerolatency -x264-params "nal-hrd=cbr:force-cfr=1"` for consistent bitrate. Without this, VBR spikes will overflow the RIST / prompeg buffers.
- **Contribution protocol ranking:** RIST ≈ SRT > RTMP for reliability; RIST adds multi-path bonding that SRT lacks. Typical end-to-end latency: RIST 100-500 ms, SRT 120-500 ms, RTMP 2-5 s, RTP+FEC 30-100 ms, WHIP <500 ms.
- **For mission-critical broadcast contribution** consider commercial overlays (Zixi, LiveU, Haivision) rather than raw ffmpeg — they add recovery on top of RIST/SRT.

## Examples

### Example 1: camera to studio over the open Internet (RIST main profile)
```
ffmpeg -f avfoundation -i "0:0" \
  -c:v libx264 -preset veryfast -tune zerolatency -b:v 6M \
  -x264-params "nal-hrd=cbr" -g 60 -c:a aac -b:a 128k -ar 48000 \
  -f mpegts "rist://studio.example.com:2000?profile=main&secret=hunter2&cname=field-cam"
```
On the studio side:
```
ffmpeg -i "rist://@:2000?profile=main&secret=hunter2" -c copy tape.ts
```

### Example 2: live drawtext retune over ZMQ
```
# Terminal A (server):
ffmpeg -re -i in.mp4 \
  -filter_complex "[0:v]drawtext=text='Pre-show':fontsize=48:x=(w-tw)/2:y=h-100:fontcolor=yellow,zmq=bind_address=tcp\\\\://127.0.0.1\\\\:5555[v]" \
  -map "[v]" -map 0:a -c:v libx264 -c:a aac out.mp4

# Terminal B (client), later:
python3 -m pip install pyzmq
python3 - <<'PY'
import zmq
s = zmq.Context().socket(zmq.REQ); s.connect("tcp://127.0.0.1:5555")
s.send_string("Parsed_drawtext_0 text LIVE"); print(s.recv_string())
PY
```

### Example 3: lossy link + prompeg FEC
```
ffmpeg -re -i in.mp4 -c:v libx264 -preset veryfast -tune zerolatency -b:v 4M \
  -c:a aac -b:a 128k \
  -f rtp_mpegts -fec prompeg=l=5:d=5 "rtp://192.168.10.20:5000"
```
Receiver: `ffplay rtp://@:5000` (or supply SDP).

### Example 4: MP3 radio to Icecast
```
ffmpeg -re -stream_loop -1 -i playlist.m3u -c:a libmp3lame -b:a 192k \
  -content_type audio/mpeg \
  -ice_name "Deep Focus" -ice_description "ambient + piano" \
  -f mp3 "icecast://source:secret@stream.example.com:8000/live"
```

### Example 5: LAN multicast
```
# Sender
ffmpeg -re -i in.mp4 -c copy -f mpegts "udp://239.1.2.3:5000?pkt_size=1316&ttl=2"

# Receiver (any host on the LAN)
ffplay "udp://@239.1.2.3:5000?fifo_size=2000000&overrun_nonfatal=1"
```

## Troubleshooting

### Error: `Protocol not found: rist` / `zmq` / `icecast`
Cause: ffmpeg was built without the corresponding library.
Solution: `ffmpeg -buildconf | grep <libname>`. On macOS `brew reinstall ffmpeg` — it ships with librist/libzmq/libshout by default. On Linux, use a build that was configured with `--enable-librist --enable-libzmq --enable-libshout`, or compile from source.

### Error: `rist: Invalid argument`
Cause: wrong URL options for the chosen profile, or mismatched profiles on the two ends.
Solution: check both endpoints use the same `profile=` (simple or main) and the same `secret`/`encryption_type` if set. Remove all options to isolate: `rist://host:port`.

### Error: ZMQ client gets `Bad Message` or no response
Cause: command not whitespace-separated, wrong filter instance name, or filter doesn't implement that command.
Solution: format is `FILTER_INSTANCE COMMAND VALUE` (spaces, not `=`). Read ffmpeg stderr to confirm the actual instance name (`Parsed_drawtext_0` etc). Only filters that declare a runtime command accept updates — `drawtext text`, `volume volume`, `crop x/y/w/h`, `setpts expr` are common.

### prompeg group has `l * d > 100` warning
Cause: total group size > 100 is off-spec for the Pro-MPEG Code of Practice.
Solution: keep `l * d <= 100`. Typical values: 5×5, 8×4, 10×5.

### Icecast connects but no audio
Cause: wrong `-content_type` or mount point already in use.
Solution: set `-content_type audio/mpeg` for MP3 or `audio/ogg` for Vorbis. Check Icecast admin UI for the live mount. Set `-ice_public 1` to appear in the directory.

### UDP multicast works locally but not across subnets
Cause: TTL=1 by default (link-local); routers ignore it.
Solution: `?ttl=16` or similar; ensure the router is configured for multicast routing (PIM-SM/DM) and IGMP snooping is not over-filtering.

### RIST link has high loss recovery rate but still drops
Cause: `buffer_size` too small for the round-trip time — retransmits arrive after playout.
Solution: raise `buffer_size` toward 2× RTT. For transcontinental paths start at 2000-3000 ms; for LAN, 100-500 ms is plenty.
