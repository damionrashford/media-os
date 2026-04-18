---
name: webrtc-mediasoup
description: >
  Host a WebRTC SFU with mediasoup (mediasoup.org/documentation/v3/): Worker (C++ subprocess, one per CPU core) to Router (per-room routing surface) to Transport (WebRtcTransport for ICE/DTLS/SRTP, PlainTransport for plain RTP + ffmpeg/GStreamer bridge, PipeTransport for Router-to-Router, DirectTransport for Node-Worker control plane) to Producer (incoming peer track) / Consumer (outgoing peer track) / DataProducer/DataConsumer (SCTP channels). ActiveSpeakerObserver / AudioLevelObserver for server-side detection. Node.js API (createWorker, router.createWebRtcTransport, transport.produce, transport.consume). Clients via mediasoup-client (browser) or libmediasoupclient (C++). Signaling is BYO — protoo is the reference. Use when the user asks to build a video-conferencing server, spin up a Node.js SFU, bridge mediasoup to ffmpeg via PlainTransport, or build a meeting room backend.
argument-hint: "[action]"
---

# webrtc-mediasoup

**Context:** $ARGUMENTS

mediasoup is a C++ SFU core with a Node.js (+ Rust, + Python) control surface. Docs home: `https://mediasoup.org/documentation/v3/`. Repo: `https://github.com/versatica/mediasoup`.

## Quick start

- **See what's installed:** → Step 1 (`mediasoup.py install`)
- **Scaffold a minimal Node.js server:** → Step 2 (`mediasoup.py quickstart DIR`)
- **Clone the reference demo:** → Step 3 (`mediasoup.py demo`)
- **Bridge RTP in/out via PlainTransport:** → Step 4 (`mediasoup.py rtp-bridge ...`)
- **Inspect workers topology:** → Step 5 (`mediasoup.py workers`)

## Architecture

```
App (Node.js)
  └── Worker   (C++ subprocess — one per CPU core)
        └── Router  (per-room; holds the codec + extension set for that room)
              ├── WebRtcTransport   (ICE/DTLS/SRTP; one per peer)
              │     ├── Producer   (peer publishing)
              │     └── Consumer   (peer subscribing)
              ├── PlainTransport   (plain RTP; ffmpeg/GStreamer bridge)
              ├── PipeTransport    (router-to-router; one mediasoup host to another)
              └── DirectTransport  (Node ↔ Worker control plane, no network)
```

Observers attach to Routers:

- `ActiveSpeakerObserver` — emits when a new speaker takes over.
- `AudioLevelObserver` — periodic volume dBov levels for all producers.

## Step 1 — Install

mediasoup is a Node.js package that builds the C++ core natively the first time you install it. The `install` subcommand prints the canonical one-liner; it does NOT auto-install:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py install
```

The user runs (requires Node.js >= 20 and Python 3.7+ for node-gyp):

```bash
npm install mediasoup
# Verify the native build landed:
ls node_modules/mediasoup/worker/out/Release/mediasoup-worker
```

Platform requirements from `mediasoup.org`: Node.js ≥ 20, Python ≥ 3.7, a C++ toolchain (`build-essential` / Xcode command-line tools / MSVC Build Tools), meson, ninja.

## Step 2 — Minimal server quickstart

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py quickstart ~/my-sfu
```

This writes a `server.js` + `package.json` containing a single-room SFU:

```js
// server.js  (written by quickstart)
const mediasoup = require('mediasoup');

async function main() {
  const worker = await mediasoup.createWorker({
    rtcMinPort: 40000, rtcMaxPort: 49999,
  });
  worker.on('died', () => { console.error('worker died'); process.exit(1); });

  const mediaCodecs = [
    { kind: 'audio', mimeType: 'audio/opus', clockRate: 48000, channels: 2 },
    { kind: 'video', mimeType: 'video/VP8',  clockRate: 90000,
      parameters: { 'x-google-start-bitrate': 1000 } },
    { kind: 'video', mimeType: 'video/H264', clockRate: 90000,
      parameters: { 'packetization-mode': 1, 'profile-level-id': '42e01f',
                    'level-asymmetry-allowed': 1 } },
  ];

  const router = await worker.createRouter({ mediaCodecs });

  const listenIps = [{ ip: '0.0.0.0', announcedIp: null }];
  const transport = await router.createWebRtcTransport({
    listenIps, enableUdp: true, enableTcp: true, preferUdp: true,
  });

  // Your BYO signaling layer calls:
  // await transport.connect({ dtlsParameters })
  // const producer = await transport.produce({ kind, rtpParameters })
  // const consumer = await transport.consume({ producerId, rtpCapabilities, paused: true })
  console.log('mediasoup ready; RouterRtpCapabilities:', router.rtpCapabilities);
}
main();
```

Run: `cd ~/my-sfu && npm install && node server.js`.

## Step 3 — The reference demo

`versatica/mediasoup-demo` is the canonical end-to-end example. Large, production-ish, uses protoo for signaling.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py demo ~/mediasoup-demo
# then follow the README: npm start in server/, browser app in app/
```

Repo: `https://github.com/versatica/mediasoup-demo`.

## Step 4 — RTP bridge (PlainTransport + ffmpeg)

PlainTransport is the RTP bridge between mediasoup and ffmpeg/GStreamer — used for recording, ingesting RTMP/RTSP, or mixing.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py rtp-bridge \
  --in-port 5004 --out-port 5006 --codec opus --out ~/bridge-config.json
```

Writes a JSON config describing the two PlainTransports. Wire it in your server:

```js
// Ingress: ffmpeg pushes RTP to mediasoup
const plainTx = await router.createPlainTransport({
  listenIp: { ip: '127.0.0.1' }, rtcpMux: true, comedia: true,
});
await plainTx.connect({ ip: '127.0.0.1', port: 5004 });
const producer = await plainTx.produce({
  kind: 'audio',
  rtpParameters: { codecs: [{ mimeType:'audio/opus', payloadType:100, clockRate:48000, channels:2 }], encodings:[{ssrc:11111111}] },
});
```

The ffmpeg side pushes: `ffmpeg -re -i in.wav -c:a libopus -ssrc 11111111 -payload_type 100 -f rtp rtp://127.0.0.1:5004`.

The inverse (Consumer → ffmpeg) uses an outgoing PlainTransport and an ffmpeg receive: `ffmpeg -protocol_whitelist rtp,udp,file -i out.sdp ...`.

## Step 5 — Inspect workers topology

Once your server has created workers + routers, introspect them:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py workers
```

Prints the conceptual topology (workers, routers, transports, producers/consumers). Because this is out-of-band from your running server, it emits a template you can adapt — for live runtime stats, call `worker.getResourceUsage()` and `router.dump()` inside your server.

## Clients

| Client                         | Module                                 | Platform       |
|--------------------------------|----------------------------------------|----------------|
| mediasoup-client               | `npm i mediasoup-client`               | Browsers       |
| libmediasoupclient             | C++                                    | Native (iOS/Android/desktop) |
| pymediasoup (community)        | `pip install pymediasoup`              | Python         |
| mediasoup-client-kotlin/swift  | community                              | Mobile         |

Signaling is **bring-your-own**. protoo (`https://github.com/versatica/protoo`) is the reference WebSocket pub/sub used in the official demo. Any transport (Socket.IO, raw WS, HTTP polling) works.

## Transport selection cheat sheet

Read [`references/transports.md`](references/transports.md) for full details.

- **WebRtcTransport** — client browser / mobile native WebRTC peer.
- **PlainTransport** — anything that speaks plain RTP (ffmpeg, GStreamer, Jitsi).
- **PipeTransport** — shard across boxes (router-to-router over unicast).
- **DirectTransport** — in-process Node ↔ Worker data channel (rare).

## Gotchas

- **Workers are subprocesses.** `worker.close()` hangs if a subprocess is stuck; use `process.kill(worker.pid, 'SIGKILL')` as a last resort.
- **One Router per room is idiomatic.** Multiple rooms = multiple routers on the same (or different) worker(s).
- **Codec negotiation is strict.** The client must advertise RTP capabilities that the Router accepts. Call `router.rtpCapabilities` → pass to client → client calls `device.load({ routerRtpCapabilities })`.
- **`produce({ rtpParameters })` must include an `ssrc`** for each encoding when going via PlainTransport without a=ssrc in an SDP answer. Missing SSRC = silent failure.
- **Simulcast RTP parameters** need `encodings: [{rid:'r0'}, {rid:'r1'}, {rid:'r2'}]` on producer creation + matching simulcast on the client. Forgetting the rid drops the upper layers.
- **`comedia:true` on PlainTransport** makes mediasoup learn the remote port from the first incoming RTP packet. Set it when the sender can't know the mediasoup port ahead of time (ffmpeg); unset when you explicitly set the tuple.
- **`rtcpMux` defaults to true.** For legacy SDP-answer flows that carry separate RTP / RTCP ports, set `rtcpMux:false` + `comedia:false` and connect explicitly.
- **`announcedIp` is critical in NAT deployments.** It's what appears in `a=candidate` lines — must be your public address, not the internal.
- **`numWorkers` default is `os.cpus().length`.** One Worker per physical core. Do NOT over-subscribe — workers are single-threaded.
- **The `on('died')` handler is mandatory** — a dead worker takes every router under it.
- **Routers do not forward between themselves automatically.** Use PipeTransport to connect Router A to Router B when sharding rooms across workers.
- **libmediasoupclient is not 1:1 with mediasoup-client.** Native clients need the app to manage codec / RTP parameters manually where the browser device does it automatically.

## Examples

### Example 1 — Single-room SFU in ~/my-sfu

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py quickstart ~/my-sfu
cd ~/my-sfu && npm install && node server.js
```

### Example 2 — Clone the demo

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py demo ~/mediasoup-demo
```

### Example 3 — ffmpeg → mediasoup ingest (audio only)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py rtp-bridge \
  --in-port 5004 --codec opus --direction in --out ~/ingest.json
# ffmpeg side:
# ffmpeg -re -i in.wav -c:a libopus -ssrc 11111111 -payload_type 100 -f rtp rtp://127.0.0.1:5004
```

### Example 4 — mediasoup → ffmpeg record (video)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediasoup.py rtp-bridge \
  --out-port 5006 --codec vp8 --direction out --out ~/record.json
# ffmpeg reads via an SDP file describing the outgoing RTP.
```

## Troubleshooting

### `Cannot find module 'mediasoup'`

Cause: npm install failed or wrong cwd.
Solution: `cd <project> && npm install mediasoup`; verify Node ≥ 20.

### `mediasoup-worker binary not found`

Cause: native build failed (missing Python / C++ toolchain / meson).
Solution: install build deps: Linux `apt install build-essential python3 python3-pip meson ninja-build`; macOS `xcode-select --install`.

### Browser sees `a=recvonly` instead of `a=sendrecv`

Cause: `appData` / `paused:true` on the consumer; or wrong `RTCRtpTransceiverDirection` on the client.
Solution: on client `transport.consume({ paused:false })`; check `transceiver.direction`.

### Audio works but video shows `ICE failed`

Cause: `listenIps` on the server is private, `announcedIp` is missing, and the client is off-LAN.
Solution: set `announcedIp` to the server's public IP.

### `TypeError: router.createWebRtcTransport is not a function`

Cause: `worker.createRouter` not awaited, or the object is already closed.
Solution: `await` every async mediasoup call.

## Reference docs

- Read [`references/transports.md`](references/transports.md) for WebRtcTransport vs PlainTransport vs PipeTransport vs DirectTransport with per-option details.
- Read [`references/signaling.md`](references/signaling.md) when choosing a signaling layer — protoo reference plus notes on Socket.IO, raw WebSocket, and HTTP long-polling trade-offs.
