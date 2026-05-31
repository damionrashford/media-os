# mediasoup Transport Types

All create-from-Router. Full API docs: `https://mediasoup.org/documentation/v3/mediasoup/api/`.

## WebRtcTransport

The browser-facing transport. Does ICE + DTLS + SRTP. Used for every end-user peer.

```js
const t = await router.createWebRtcTransport({
  listenIps: [{ ip: '0.0.0.0', announcedIp: 'PUBLIC_IP' }],
  enableUdp: true, enableTcp: true, preferUdp: true,
  initialAvailableOutgoingBitrate: 1_000_000,
});
```

Key options:

- `listenIps` — interfaces to bind (one per NIC). `announcedIp` overrides `ip` in `a=candidate`.
- `enableUdp` / `enableTcp` — UDP always preferred if available.
- `preferUdp` — if both enabled, prefer UDP over TCP.
- `initialAvailableOutgoingBitrate` — starting BWE guess (bps).
- `enableSctp`, `numSctpStreams`, `maxSctpMessageSize`, `sctpSendBufferSize` — data channels.

Flow:

1. Server creates transport → replies with `{iceParameters, iceCandidates, dtlsParameters, sctpParameters}`.
2. Client `transport.connect({ dtlsParameters })` via signaling.
3. Server applies DTLS params via `transport.connect({ dtlsParameters })`.
4. Client then `transport.produce({ kind, rtpParameters })` per publish, or `transport.consume({ producerId, rtpCapabilities })` per subscribe.

## PlainTransport

Plain RTP over UDP. The bridge to ffmpeg / GStreamer / third-party MCUs. NO DTLS, NO ICE, NO SRTP (unless `srtpParameters` is explicitly set).

```js
const t = await router.createPlainTransport({
  listenIp: { ip: '127.0.0.1' },
  rtcpMux: true,
  comedia: true,    // learn remote tuple from first packet
});
```

- `comedia:true` — mediasoup discovers the remote address+port from the first inbound packet. Use when the sender (ffmpeg) doesn't know mediasoup's ephemeral port.
- `rtcpMux:true` — RTP and RTCP share one port.
- For the producer, you must supply complete `rtpParameters` (codec, payloadType, clockRate, channels, SSRC).
- SRTP: pass `enableSrtp:true` + `srtpCryptoSuite` to enable encrypted RTP (rare).

Example ingest: `ffmpeg -re -i in.wav -c:a libopus -ssrc 11111111 -payload_type 100 -f rtp rtp://<mediasoup-ip>:5004`.

Example egress: server opens outbound PlainTransport with `comedia:false` + `connect({ip, port})`, then `consume` the producer; ffmpeg reads via an SDP file.

## PipeTransport

Router-to-router inside the same mediasoup cluster. Uses UDP over the internal network. No ICE/DTLS (relies on the cluster network being trusted).

```js
const t = await router.createPipeTransport({ listenIp: { ip: '10.0.0.5' } });
await t.connect({ ip: '10.0.0.6', port: 44444, srtpParameters: null });
await router.pipeToRouter({ producerId: prod.id, router: routerB });
```

Use to shard a conference across multiple mediasoup hosts or multiple workers on one host.

## DirectTransport

In-process Node ↔ Worker data channel. No network stack. Used for control-plane messages (e.g., generating synthetic audio, custom RTP routing from Node).

```js
const t = await router.createDirectTransport();
const dp = await t.produceData({ label: 'control' });
const dc = await t.consumeData({ dataProducerId: dp.id });
dc.on('message', (msg) => { /* ... */ });
```

Rare in practice; useful for server-generated data channels or custom analytics streams.

## Transport cheat-sheet

| Transport          | ICE | DTLS | SRTP | Typical peer               |
|--------------------|-----|------|------|----------------------------|
| WebRtcTransport    | ✅  | ✅   | ✅   | Browser, mobile WebRTC     |
| PlainTransport     | ❌  | ❌   | opt  | ffmpeg, GStreamer, legacy  |
| PipeTransport      | ❌  | ❌   | opt  | Another mediasoup router   |
| DirectTransport    | ❌  | ❌   | ❌   | Node process itself        |
