# mediasoup Signaling Patterns

mediasoup ships **no signaling layer**. You must pick/build one. This is a feature — lets you fit signaling into your existing auth/session stack.

## protoo (reference)

`https://github.com/versatica/protoo` — small request/response + notification WebSocket library used by `mediasoup-demo`.

Server side:

```js
const protoo = require('protoo-server');
const room = new protoo.Room();
wss.on('connection', (ws, req) => {
  const id = extractPeerId(req); // your auth
  const transport = new protoo.WebSocketTransport(ws);
  const peer = room.createPeer(id, null, transport);
  peer.on('request', (req, accept, reject) => {
    switch (req.method) {
      case 'getRouterRtpCapabilities':
        return accept(router.rtpCapabilities);
      case 'createWebRtcTransport':
        return createTransport(peer).then(accept, reject);
      case 'produce':
        return onProduce(peer, req.data).then(accept, reject);
      case 'consume':
        return onConsume(peer, req.data).then(accept, reject);
      // ...
    }
  });
});
```

Client side uses `protoo-client` with the symmetric API.

## Canonical request set

Regardless of transport, the minimum signaling surface is:

| Method                      | Direction     | Payload                                                 |
|-----------------------------|---------------|---------------------------------------------------------|
| `getRouterRtpCapabilities`  | C→S request   | —                                                       |
| `createWebRtcTransport`     | C→S request   | `{ producing, consuming, sctpCapabilities? }`           |
| `connectWebRtcTransport`    | C→S request   | `{ transportId, dtlsParameters }`                       |
| `produce`                   | C→S request   | `{ transportId, kind, rtpParameters, appData }`         |
| `consume`                   | C→S request   | `{ producerId, transportId, rtpCapabilities }`          |
| `pauseProducer` / `resume`  | C→S request   | `{ producerId }`                                        |
| `closeProducer` / `close`   | C→S request   | `{ producerId }`                                        |
| `newPeer` / `peerClosed`    | S→C notify    | `{ id, displayName }`                                   |
| `newProducer`               | S→C notify    | `{ peerId, producerId, kind, rtpParameters }`           |
| `activeSpeaker`             | S→C notify    | `{ peerId, volume }`                                    |

Call `consume` with `paused:true` by default and resume after the client confirms it's ready to render — avoids dropped frames on slow devices.

## Alternative transports

- **Socket.IO** — popular; acknowledgements map neatly to request/response.
- **Raw WebSocket (ws)** — lightest, hand-roll the request id / ack protocol.
- **HTTP long-polling** — for restricted networks that block WS; adds latency.
- **gRPC** — internal service-to-service; clients usually can't speak gRPC-Web reliably for signaling.

## Multi-room sharding

Signaling typically decides **which router** a peer lands on. Strategies:

1. **Round-robin across workers on one host** — default. Each room picks one `router` from a pool.
2. **Consistent hashing by room ID** — same room → same worker.
3. **Across hosts** — signaling routes peer → specific host; use `PipeTransport` to stitch if a room spans hosts.

## Security

- Every signaling request should carry the authenticated peer id — never trust client-supplied ids for `produce`/`consume`.
- Validate that `produce` targets a transport owned by the same peer.
- Validate that `consume` is permitted (e.g., presenter role, private rooms).
- Rate-limit `createWebRtcTransport` and `produce` — they spawn OS resources.

## Related docs

- `https://mediasoup.org/documentation/v3/tricks/#using-raw-rtp-transports-with-ffmpeg` — ffmpeg/GStreamer bridge examples.
- `https://mediasoup.org/documentation/v3/communication-between-client-and-server/` — canonical signaling narrative.
