# WebRTC RFC + W3C TR Index

Grouped by topic. All URLs verified HTTP 200 at authoring time.

## W3C (Browser API)

| Page name                  | Title                                         | URL                                                 |
|----------------------------|-----------------------------------------------|-----------------------------------------------------|
| `w3c-webrtc`               | WebRTC 1.0 (REC) — RTCPeerConnection etc.     | `https://www.w3.org/TR/webrtc/`                     |
| `w3c-webrtc-extensions`    | Extensions (simulcast, encoded transforms)    | `https://www.w3.org/TR/webrtc-extensions/`          |
| `w3c-webrtc-stats`         | Statistics API identifiers                    | `https://www.w3.org/TR/webrtc-stats/`               |
| `w3c-mediacapture-streams` | getUserMedia / MediaStream                    | `https://www.w3.org/TR/mediacapture-streams/`       |
| `w3c-screen-capture`       | getDisplayMedia                               | `https://www.w3.org/TR/screen-capture/`             |
| `w3c-webcodecs`            | WebCodecs — low-level encoder/decoder         | `https://www.w3.org/TR/webcodecs/`                  |
| `w3c-webtransport`         | WebTransport                                  | `https://www.w3.org/TR/webtransport/`               |

## IETF — Overview / Security / Framework

| RFC   | Title                                               | URL                                                        |
|-------|-----------------------------------------------------|------------------------------------------------------------|
| 8825  | Overview: Real-Time Protocols for Browser-Based Apps| `https://datatracker.ietf.org/doc/html/rfc8825`            |
| 8826  | Security Considerations for WebRTC                  | `https://datatracker.ietf.org/doc/html/rfc8826`            |
| 8827  | WebRTC Security Architecture                        | `https://datatracker.ietf.org/doc/html/rfc8827`            |
| 8828  | WebRTC IP Address Handling Requirements             | `https://datatracker.ietf.org/doc/html/rfc8828`            |

## IETF — Signaling / JSEP / SDP

| RFC   | Title                                               | URL                                                        |
|-------|-----------------------------------------------------|------------------------------------------------------------|
| 8829  | JSEP (original)                                     | `https://datatracker.ietf.org/doc/html/rfc8829`            |
| 9429  | JSEP (bis, obsoletes 8829)                          | `https://datatracker.ietf.org/doc/html/rfc9429`            |
| 8866  | **SDP** (obsoletes 4566)                            | `https://datatracker.ietf.org/doc/html/rfc8866`            |
| 8843  | ICE/DTLS multiplexing in SDP                        | `https://datatracker.ietf.org/doc/html/rfc8843`            |
| 9143  | BUNDLE                                              | `https://datatracker.ietf.org/doc/html/rfc9143`            |
| 8853  | Simulcast in SDP/RTP                                | `https://datatracker.ietf.org/doc/html/rfc8853`            |
| 8851  | rid — RTP Stream Identifier                         | `https://datatracker.ietf.org/doc/html/rfc8851`            |

## IETF — ICE / STUN / TURN

| RFC   | Title                                               | URL                                                        |
|-------|-----------------------------------------------------|------------------------------------------------------------|
| 8445  | ICE — Interactive Connectivity Establishment        | `https://datatracker.ietf.org/doc/html/rfc8445`            |
| 8489  | STUN                                                | `https://datatracker.ietf.org/doc/html/rfc8489`            |
| 8656  | TURN                                                | `https://datatracker.ietf.org/doc/html/rfc8656`            |
| 7064  | stun: URI scheme                                    | `https://datatracker.ietf.org/doc/html/rfc7064`            |
| 7065  | turn: URI scheme                                    | `https://datatracker.ietf.org/doc/html/rfc7065`            |
| 8838  | Trickle ICE                                         | `https://datatracker.ietf.org/doc/html/rfc8838`            |

## IETF — Media Transport

| RFC   | Title                                               | URL                                                        |
|-------|-----------------------------------------------------|------------------------------------------------------------|
| 3550  | RTP                                                 | `https://datatracker.ietf.org/doc/html/rfc3550`            |
| 3711  | SRTP                                                | `https://datatracker.ietf.org/doc/html/rfc3711`            |
| 5764  | DTLS-SRTP                                           | `https://datatracker.ietf.org/doc/html/rfc5764`            |
| 8834  | RTP usage in WebRTC                                 | `https://datatracker.ietf.org/doc/html/rfc8834`            |
| 8835  | WebRTC Transports                                   | `https://datatracker.ietf.org/doc/html/rfc8835`            |
| 8836  | Congestion Control Requirements                     | `https://datatracker.ietf.org/doc/html/rfc8836`            |
| 8837  | DSCP Packet Markings                                | `https://datatracker.ietf.org/doc/html/rfc8837`            |

## IETF — Data Channels

| RFC   | Title                                               | URL                                                        |
|-------|-----------------------------------------------------|------------------------------------------------------------|
| 8831  | WebRTC Data Channels                                | `https://datatracker.ietf.org/doc/html/rfc8831`            |
| 8832  | DCEP — Data Channel Establishment Protocol          | `https://datatracker.ietf.org/doc/html/rfc8832`            |

## IETF — Codec RTP Payload Formats

| RFC   | Codec   | URL                                                         |
|-------|---------|-------------------------------------------------------------|
| 6184  | H.264   | `https://datatracker.ietf.org/doc/html/rfc6184`             |
| 7798  | HEVC    | `https://datatracker.ietf.org/doc/html/rfc7798`             |
| 7741  | VP8     | `https://datatracker.ietf.org/doc/html/rfc7741`             |
| 7587  | Opus    | `https://datatracker.ietf.org/doc/html/rfc7587`             |

## IETF — WHIP / WHEP (ingest / egress HTTP signaling)

| Doc                         | Title                            | URL                                                              |
|-----------------------------|----------------------------------|------------------------------------------------------------------|
| RFC 9725                    | WHIP (WebRTC-HTTP Ingestion)     | `https://datatracker.ietf.org/doc/html/rfc9725`                  |
| `draft-ietf-wish-whep`      | WHEP (Egress) — still a draft    | `https://datatracker.ietf.org/doc/draft-ietf-wish-whep/`         |

## Reference implementations (not in the spec catalog but referenced)

- **coturn** — `https://github.com/coturn/coturn` — canonical STUN/TURN server.
- **pion/turn** — `https://github.com/pion/turn` — Go STUN/TURN library.
- **aiortc** — `https://github.com/aiortc/aiortc` — Python WebRTC client (async).

## Common misattributions — be careful

- "RFC 4566 is SDP" — **obsolete** since 2020. 8866 is the current SDP.
- "RFC 8854 is SDP" — **wrong**. 8854 = FEC Requirements for Real-Time Text. SDP = 8866.
- "JSEP = RFC 8829" — partially correct. 9429 is the newer bis and is authoritative.
- "WHEP is an RFC" — **no**. Still a draft. Cite `draft-ietf-wish-whep-NN`.
- "ICE = 5245" — 5245 is obsoleted by 8445.
