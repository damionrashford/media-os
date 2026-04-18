# WebRTC SDP Attribute Cheat Sheet

All references are to **RFC 8866** (current SDP, obsoletes 4566) unless noted. WebRTC-specific additions live in 8843, 8853, 8851, 9143, etc.

## Session-level lines

```
v=0                                # version, always 0 per 8866
o=- 1234 1 IN IP4 0.0.0.0          # origin: username sess-id sess-version nettype addrtype addr
s=-                                # session name (- if none)
t=0 0                              # timing: start stop (0 0 = unbounded)
a=group:BUNDLE 0 1                 # BUNDLE groups m-sections — RFC 9143
a=msid-semantic: WMS *             # MediaStream semantic tag
```

## Media description (`m=` line)

```
m=audio 9 UDP/TLS/RTP/SAVPF 111 103 104
m=video 9 UDP/TLS/RTP/SAVPF 96 97 98
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
```

- port `9` = "unused" (ICE supplies the real one).
- `UDP/TLS/RTP/SAVPF` = DTLS-SRTP profile (audio/video).
- `UDP/DTLS/SCTP` = data channels.
- Trailing numbers are RTP payload types referenced by `a=rtpmap`/`a=fmtp`.

## Core `a=` attributes

### Codec description

```
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:96 H264/90000
a=fmtp:96 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
a=fmtp:97 apt=96                   # RTX (retransmission) payload for PT 96
a=rtpmap:97 rtx/90000
```

`a=fmtp` syntax is codec-specific. See RFC 6184 (H.264), 7798 (HEVC), 7741 (VP8), 7587 (Opus).

### RTCP feedback

```
a=rtcp-fb:96 nack
a=rtcp-fb:96 nack pli
a=rtcp-fb:96 ccm fir
a=rtcp-fb:96 goog-remb
a=rtcp-fb:96 transport-cc
```

- `nack` — per RFC 4585
- `nack pli` — Picture Loss Indication
- `ccm fir` — Full Intra Request
- `goog-remb` / `transport-cc` — congestion-control feedback

### RTP header extensions (`extmap`)

```
a=extmap:1 urn:ietf:params:rtp-hdrext:sdes:mid
a=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time
a=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id    # rid (RFC 8851)
a=extmap:5 urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id
```

### ICE credentials + candidates

```
a=ice-ufrag:Fg4PNB2JJ1tRWDfQ
a=ice-pwd:BZ/5h...
a=ice-options:trickle
a=candidate:1 1 UDP 2122252543 192.0.2.1 54400 typ host
a=candidate:2 1 UDP 1686052607 198.51.100.2 40000 typ srflx raddr 192.0.2.1 rport 54400
a=candidate:3 1 UDP 41819902 203.0.113.4 3478 typ relay raddr 198.51.100.2 rport 40000
a=end-of-candidates
```

Candidate fields: foundation component transport priority addr port `typ {host|srflx|prflx|relay}`. See RFC 8445.

### DTLS fingerprint + role

```
a=fingerprint:sha-256 AB:CD:...:EF
a=setup:actpass      # actpass | active | passive | holdconn — RFC 8843/5763
```

### Direction

```
a=sendrecv
a=sendonly
a=recvonly
a=inactive
```

### Source identifiers

```
a=mid:0                                # m-section identifier (used by BUNDLE)
a=msid:stream-id track-id              # MediaStream + Track association
a=ssrc:1234567 cname:abc
a=ssrc:1234567 msid:stream-id track-id
a=ssrc-group:FID 1234567 7654321       # RTX feedback identification
a=ssrc-group:FEC 1234567 7654321       # FEC pair
```

### Simulcast + rid (RFC 8851 + 8853)

```
a=rid:low  send max-width=320;max-height=180
a=rid:mid  send max-width=640;max-height=360
a=rid:high send
a=simulcast:send low;mid;high
```

`a=simulcast:send` lists the rid identifiers in descending priority. Receive side mirrors.

### Data channels (RFC 8841/8831)

```
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
a=sctp-port:5000
a=max-message-size:262144
```

### Payload-type reduction

```
a=rtcp-mux
a=rtcp-rsize
```

Both are practically mandatory in modern WebRTC.

## Minimal example offer (audio-only)

```
v=0
o=- 8432 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS -
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:Fg4P
a=ice-pwd:BZ5h
a=fingerprint:sha-256 AB:CD:EF:...
a=setup:actpass
a=mid:0
a=sendrecv
a=rtcp-mux
a=rtcp-rsize
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=extmap:1 urn:ietf:params:rtp-hdrext:sdes:mid
```

## Attribute-to-RFC map

| Attribute                               | Spec                 |
|-----------------------------------------|----------------------|
| `a=rtpmap`, `a=fmtp`, `a=rtcp`, `c=`    | RFC 8866             |
| `a=rtcp-fb`                             | RFC 4585             |
| `a=rtcp-mux`, `a=rtcp-rsize`            | RFC 5761, 5506       |
| `a=group:BUNDLE`                        | RFC 9143             |
| `a=mid`                                 | RFC 5888 / 8843      |
| `a=msid`                                | RFC 8830             |
| `a=ssrc`, `a=ssrc-group`                | RFC 5576             |
| `a=candidate`, `a=ice-ufrag`, `a=ice-pwd` | RFC 8839          |
| `a=end-of-candidates`                   | RFC 8838 (Trickle)   |
| `a=fingerprint`, `a=setup`              | RFC 8122 / 5763      |
| `a=extmap`                              | RFC 8285             |
| `a=rid`                                 | RFC 8851             |
| `a=simulcast`                           | RFC 8853             |
| `a=sctp-port`, `a=max-message-size`     | RFC 8841             |

Use `webrtcdocs.py search --query "<attr>"` to fetch the exact normative text.
