---
name: webrtc-spec
description: >
  Search and fetch WebRTC specs from W3C and IETF: W3C WebRTC 1.0 (RTCPeerConnection, RTCRtpSender/Receiver/Transceiver, RTCDataChannel, RTCDtlsTransport, RTCIceTransport, RTCSctpTransport, RTCStatsReport), WebRTC-Extensions (simulcast, encoded transforms), WebRTC Stats, Media Capture and Streams (getUserMedia), Screen Capture, WebCodecs, WebTransport. IETF RFCs: 8825 (overview), 8826/8827/8828 (security), 8829+9429 (JSEP), 8831/8832 (data channels), 8834 (RTP in WebRTC), 8835 (transports), 8836 (congestion), 8837 (DSCP), 8866 (SDP, obsoletes 4566), 8445 (ICE), 8489 (STUN), 8656 (TURN), 5764 (DTLS-SRTP), 3711 (SRTP), 3550 (RTP), 6184 (H.264), 7798 (HEVC), 7741 (VP8), 7587 (Opus), 9725 (WHIP), draft-ietf-wish-whep (WHEP). Use when the user asks to look up an SDP attribute, verify an ICE behavior, check an RFC number for WebRTC, or find the canonical spec for a WebRTC feature.
argument-hint: "[query]"
---

# webrtc-spec

**Context:** $ARGUMENTS

Search and fetch W3C + IETF WebRTC specifications. A companion to `webrtc-pion`, `webrtc-mediasoup`, `webrtc-livekit` — this skill is your source-of-truth for what the wire protocol and browser API actually require.

## Quick start

- **Find an SDP attribute / RFC number:** → Step 2 (`search --query <term>`)
- **Read a full section:** → Step 3 (`section --page <page> --id <anchor>`)
- **Dump a whole doc:** → Step 4 (`fetch --page <page>`)
- **Print the RFC table:** → Step 5 (`list-rfcs`)
- **Prime the cache offline:** → Step 6 (`index`)

## When to use

- Before telling the user what an SDP attribute means, verify it against RFC 8866 (NOT RFC 4566, which is obsoleted).
- Before mentioning a WebRTC JS API method, verify it against the current W3C WebRTC 1.0 (REC).
- Need to cite the canonical URL for an RFC / TR (`https://datatracker.ietf.org/doc/html/rfcN` or `https://www.w3.org/TR/<name>/`).
- Choosing between two RFCs (e.g. SDP: 4566 vs 8866 — 8866 wins; JSEP: 8829 vs 9429 — 9429 is the newest update).

## Step 1 — Page catalog

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py list-pages
```

Top picks:

| Question                                       | Page                               |
|------------------------------------------------|------------------------------------|
| "What's the signature of `addTransceiver`?"    | `w3c-webrtc`                        |
| "What does `a=msid` mean?"                     | `rfc-8866`                          |
| "How does ICE gather candidates?"              | `rfc-8445`                          |
| "What's in JSEP?"                              | `rfc-9429` (obsoletes 8829)         |
| "How is DTLS-SRTP negotiated?"                 | `rfc-5764`                          |
| "What's the WHIP protocol?"                    | `rfc-9725`                          |
| "How does simulcast work in SDP?"              | `rfc-8853`                          |
| "What's a `rid`?"                              | `rfc-8851`                          |
| "getUserMedia constraints?"                    | `w3c-mediacapture-streams`          |
| "Screen-capture permission model?"             | `w3c-screen-capture`                |
| "WebCodecs frame formats?"                     | `w3c-webcodecs`                     |

Full catalog in [`references/rfc-index.md`](references/rfc-index.md).

## Step 2 — Search

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "rtcp-fb" --limit 5
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "a=candidate" --page rfc-8866
```

Hits print `page:line — heading`, the canonical URL, and ±3 lines of context. First run fetches + caches; subsequent runs are instant.

## Step 3 — Read one section

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py section --page rfc-8866 --id 5
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py section --page w3c-webrtc --id dom-rtcpeerconnection
```

`--id` accepts either a heading keyword or a numeric section like `5.13`.

## Step 4 — Fetch a whole page

Rarely needed — `search` + `section` is usually enough. Use for offline copies:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py fetch --page rfc-9725 --format text
```

## Step 5 — Print the RFC table

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py list-rfcs
```

Prints each RFC in the catalog with its number, short title, and canonical URL. Same data also in `references/rfc-index.md` for inline reading.

## Step 6 — Prime the cache

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py index
```

Fetches every known page to `~/.cache/webrtc-spec/`. Override with `WEBRTC_DOCS_CACHE=/path env`.

## Gotchas

- **SDP is RFC 8866, not RFC 4566.** 8866 obsoletes 4566 (2020). If Claude has trained on older material, it will likely cite 4566 — don't.
- **"RFC 8854" is NOT SDP.** 8854 is "FEC Requirements for Real-Time Text". Easy confusion because of proximity to 8866. Always verify via `list-rfcs`.
- **JSEP has two RFCs.** The original 8829 + the update 9429. For new work prefer 9429. Old blog posts cite 8829.
- **WHIP is RFC 9725.** It is final, not a draft. WHEP is still `draft-ietf-wish-whep-NN` — use the Datatracker "latest draft" URL.
- **Trickle ICE is RFC 8838**, separate from the base ICE RFC 8445.
- **BUNDLE = RFC 9143.** Older blog posts reference `draft-ietf-mmusic-sdp-bundle-negotiation` — cite 9143 instead.
- **ICE + DTLS carriage in SDP is RFC 8843.** Separate from ICE itself (8445) and from DTLS-SRTP (5764).
- **Simulcast = RFC 8853; rid = RFC 8851**; `mid` is a core SDP attribute living in RFC 8843 / 5888 depending on context.
- **H.264 RTP = RFC 6184**, HEVC = RFC 7798, VP8 = RFC 7741, VP9 payload is still in IETF draft land. Opus = RFC 7587 (+ draft updates).
- **W3C URLs vs IETF URLs.** W3C TRs live at `https://www.w3.org/TR/<name>/` (published) or `<name>/drafts/`. IETF RFCs live at `https://datatracker.ietf.org/doc/html/rfcN`. Don't mix them.
- **`mediacapture-streams` is the getUserMedia spec.** Not "WebRTC Media" — that's colloquial.

## Examples

### Example 1 — "What does `a=setup` mean?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "a=setup" --page rfc-8843
```

Cite RFC 8843 §5 ("Role-less" ICE handling) — `a=setup:actpass|active|passive|holdconn`.

### Example 2 — "Is trickle ICE standardized?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "trickle" --limit 5
```

Points at RFC 8838.

### Example 3 — "What are valid RTCP feedback types?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "rtcp-fb" --limit 10
```

Scope to `rfc-8866` (syntax) and `rfc-5104` (AVPF — referenced but not in our catalog).

### Example 4 — "What's WHIP's authentication model?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py section --page rfc-9725 --id 4
```

Section 4 — Bearer tokens, one-time POST to ingestion URL, 201 + Location header.

### Example 5 — "Where is `createOffer` defined?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/webrtcdocs.py search --query "createOffer" --page w3c-webrtc
```

## Troubleshooting

### `unknown page: foo`

Cause: typo'd name.
Solution: `list-pages` to see valid names. Common mistake: `sdp` — use `rfc-8866`.

### `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

Cause: out-of-date system CAs.
Solution: install/update certifi or run the macOS `Install Certificates.command`. Don't disable SSL verification.

### Search returns nothing

Cause: wrong page or term is in a sibling RFC not in our catalog.
Solution: drop `--page`, try broader term, or check `list-rfcs` for adjacent RFCs.

### Results look truncated

Cause: text extraction flattens complex IETF tables.
Solution: open the canonical URL printed in the hit — that's the authoritative view.

## Reference docs

- Read [`references/rfc-index.md`](references/rfc-index.md) when you need the full RFC table grouped by topic (ICE/STUN/TURN, media transport, SDP, DTLS/SRTP, codecs, signaling, WHIP/WHEP, data channels, congestion, security).
- Read [`references/sdp-grammar.md`](references/sdp-grammar.md) when debugging an SDP offer/answer — covers `a=rtpmap`, `a=fmtp`, `a=rtcp-fb`, `a=extmap`, `a=msid`, `a=ssrc`, `a=ice-ufrag`/`ice-pwd`, `a=candidate`, `a=fingerprint`, `a=setup`, `a=mid`, `a=rid`, `a=simulcast`, `a=sctp-port`.
