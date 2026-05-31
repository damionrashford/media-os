# Pion Primitives + Sibling Libraries

Canonical GoDoc for every type listed here: `https://pkg.go.dev/github.com/pion/<module>`.

## Core package — `github.com/pion/webrtc/v4`

| Type                           | Purpose                                                              |
|--------------------------------|----------------------------------------------------------------------|
| `API`                          | Factory that holds a MediaEngine + SettingEngine + InterceptorRegistry. Construct with `webrtc.NewAPI(opts...)`. |
| `PeerConnection`               | Main WebRTC session object. Wraps DTLS, ICE, SRTP, SCTP.             |
| `MediaEngine`                  | Registered codecs + header extensions. `RegisterDefaultCodecs()` or `RegisterCodec(...)`. |
| `SettingEngine`                | Transport-layer tuning (ICE lite, candidate filters, single-port mux, logger). |
| `InterceptorRegistry`          | RTCP generator stack (NACK, TWCC, Report Sender). `RegisterDefaultInterceptors()` gives the typical set. |
| `RTPSender`                    | Outgoing side of a media flow; exposes `GetParameters`, `ReplaceTrack`. |
| `RTPReceiver`                  | Incoming side; exposes `Read`, `ReadRTCP`.                           |
| `RTPTransceiver`               | Bi-directional track-flow with a `Direction` (sendrecv/sendonly/recvonly/inactive). |
| `TrackLocal` (interface)       | Anything you can push media into.                                    |
| `TrackLocalStaticRTP`          | Write pre-packetized `*rtp.Packet` frames.                           |
| `TrackLocalStaticSample`       | Write codec-agnostic media samples — Pion packetizes for you.        |
| `TrackRemote`                  | Incoming media track; use `.ReadRTP()` or `.Read(buf)`.              |
| `DataChannel`                  | SCTP data channel; call `.Detach()` for `io.ReadWriter` mode.        |
| `DTLSTransport`                | Exposed for fingerprint introspection / rekey.                       |
| `ICETransport`                 | Per-transceiver ICE state.                                           |
| `SCTPTransport`                | SCTP association wrapper.                                            |
| `SRTPSession`                  | Low-level SRTP crypto context (rarely touched).                      |
| `Stats`, `StatsReport`         | RTCStatsReport mirror. Call `PeerConnection.GetStats()`.             |
| `OfferAnswerOptions`           | SDP offer/answer modifiers (ice restart, voice activity detection).  |
| `Configuration`                | ICE servers + transport policy. Pass to `API.NewPeerConnection`.     |

## Sibling libraries

| Module                              | What it does                                                       |
|-------------------------------------|--------------------------------------------------------------------|
| `github.com/pion/rtp`               | RTP packet parsing + marshalling                                   |
| `github.com/pion/rtcp`              | RTCP packet types (SR, RR, RTPFB, PSFB, APP)                        |
| `github.com/pion/sdp/v3`            | SDP parser/writer                                                  |
| `github.com/pion/ice/v3`            | Standalone ICE agent                                               |
| `github.com/pion/dtls/v3`           | DTLS 1.2 client + server                                           |
| `github.com/pion/srtp/v3`           | SRTP session                                                       |
| `github.com/pion/turn/v4`           | STUN + TURN server library                                         |
| `github.com/pion/mediadevices`      | Cross-platform camera + mic capture → TrackLocal                   |
| `github.com/pion/interceptor`       | Modular RTCP generators (NACK, TWCC, REMB)                         |
| `github.com/pion/webrtc-reference-test` | Integration suite Google uses                                   |

## SFU projects built on Pion

- **ion-sfu** (`https://github.com/ionorg/ion-sfu`) — archived reference SFU, still useful reading.
- **ion** (`https://github.com/pion/ion`) — sibling product suite.
- **LiveKit** (`https://github.com/livekit/livekit`) — production SFU + auth + egress/ingress.
- **Galene** (`https://github.com/jech/galene`) — minimal multi-participant SFU.

## Typical lifecycle (pseudo-Go)

```go
m := &webrtc.MediaEngine{}
m.RegisterDefaultCodecs()

r := &interceptor.Registry{}
webrtc.RegisterDefaultInterceptors(m, r)

api := webrtc.NewAPI(webrtc.WithMediaEngine(m), webrtc.WithInterceptorRegistry(r))
pc, _ := api.NewPeerConnection(webrtc.Configuration{
    ICEServers: []webrtc.ICEServer{{URLs: []string{"stun:stun.l.google.com:19302"}}},
})
defer pc.Close()

track, _ := webrtc.NewTrackLocalStaticSample(
    webrtc.RTPCodecCapability{MimeType: webrtc.MimeTypeH264}, "video", "pion",
)
pc.AddTrack(track)

offer, _ := pc.CreateOffer(nil)
pc.SetLocalDescription(offer)
// ... exchange SDP with peer ...
pc.SetRemoteDescription(remoteAnswer)

for {
    track.WriteSample(media.Sample{Data: frame, Duration: time.Second/30})
}
```

## Design rules

- **Register codecs + interceptors BEFORE `NewPeerConnection`** — rebuilds are not supported on an active PC.
- **Use `TrackLocalStaticSample` for unmodified frames** (H.264 Annex-B, Opus frames). Use `TrackLocalStaticRTP` if you already have RTP packets.
- **`WriteSample.Duration` is mandatory** — Pion computes RTP timestamps from it.
- **Goroutine per track, not per packet.** `TrackRemote.ReadRTP` blocks until a packet arrives; a long-lived goroutine per track is the idiom.
- **Interceptor order = registration order.** NACK generator must register before the sending interceptor.
