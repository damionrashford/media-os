---
name: ptz
description: >
  Control PTZ cameras over Sony VISCA (RS-232/422/485 serial 9600/38400 8N1 or UDP:52381 payload-wrapped) and ONVIF (SOAP 1.2/XML, WS-Security UsernameToken digest, WS-Discovery multicast 239.255.255.250:3702). Drive pan, tilt, zoom, focus, exposure, white balance; recall and save presets; send raw VISCA bytes; discover ONVIF cameras; pull RTSP stream URIs; grab snapshots; query device capabilities; ContinuousMove, AbsoluteMove, RelativeMove, GotoPreset. Cameras: Sony BRC/SRG/FR7/FCB, PTZOptics, AVer, Panasonic AW, Bolin, Lumens, Marshall, Canon CR-N, Hikvision, Dahua, Axis, Bosch, Amcrest, Reolink. Use when the user asks to drive a PTZ camera, move a PTZOptics or Sony cam, send pan-tilt over IP or serial, zoom or focus from a script, recall a camera preset, build a VISCA packet, integrate PTZ into OBS or vMix, discover ONVIF cameras, get an RTSP URL, grab a snapshot, authenticate with UsernameToken digest, or look up a VISCA command or ONVIF service.
argument-hint: "[action]"
---

# PTZ

**Context:** $ARGUMENTS

Drive PTZ cameras two ways: low-level Sony VISCA (serial or UDP-IP wire protocol) and ONVIF (SOAP/WS-Security for IP cameras — discovery, RTSP URIs, PTZ, snapshots). Always confirm wire bytes or SOAP operations against the docs lookup before naming them.

## When to use

- Drive a broadcast/streaming PTZ (Sony BRC/SRG/FR7, PTZOptics, AVer, Panasonic AW, Bolin, Marshall, Canon CR-N) from a script — VISCA.
- Discover ONVIF cameras on a subnet, pull RTSP URIs for ffmpeg ingest, grab snapshots, or drive PTZ across heterogeneous brands (Hikvision, Dahua, Axis, Bosch, Amcrest, Reolink) — ONVIF.
- Recall/save presets, zoom, focus, build raw VISCA packets, or integrate a PTZ rig into OBS/vMix/Companion.
- Authenticate with WS-Security UsernameToken digest or dry-run a packet/SOAP envelope before sending.

## Techniques

- Read `references/visca.md` when the user wants Sony VISCA control over serial or UDP-IP: pan/tilt/zoom/focus/exposure/WB, presets, raw packets, reply parsing. Helper: `scripts/viscactl.py`.
- Read `references/onvif.md` when the user wants ONVIF IP-camera control: WS-Discovery, device info, RTSP stream URIs, snapshots, ContinuousMove/AbsoluteMove/GotoPreset. Helper: `scripts/onvifctl.py`.

## Docs lookup

BEFORE naming any VISCA command byte sequence or ONVIF service/operation, verify it against the canonical specs — this is the anti-hallucination guardrail.

- Read `references/docs-search.md` for how to search/fetch Sony VISCA PDFs and onvif.org profile pages with `scripts/ptzdocs.py` (`search`, `section`, `fetch`, `list-pages`, `index`).
- Curated byte/service tables live in `references/visca-commands.md`, `references/commands.md` (VISCA), and `references/onvif-services.md`, `references/services.md` (ONVIF) — use these for exact byte sequences the PDF search cannot return.

## Gotchas

- **First VISCA byte is `0x80 | address`, not literal `0x81`.** `0x81`=addr 1, `0x82`=addr 2; broadcast is `0x88`. Every packet ends with `0xFF` (terminator, not a length field).
- **VISCA-over-IP wraps the serial message in an 8-byte payload header** (type + length + seq#) on UDP:52381. Do NOT TCP-tunnel raw serial VISCA — IP cameras silently drop unwrapped packets. PTZOptics legacy firmware listens on UDP:1259; modern uses 52381.
- **VISCA error codes:** `ee=02` syntax (bad speed range / nibble packing), `ee=03` buffer full (sent too fast — wait for Completion or throttle ~10 Hz), `ee=41` not executable (e.g. preset >127 on strict Sony, focus-direct while in AF).
- **WS-Discovery does NOT cross subnets** — link-local multicast at `239.255.255.250:3702` only. For remote ONVIF cameras, hit the Device service URL / `GetCapabilities` directly.
- **ONVIF WS-Security digest = `BASE64(SHA1(raw_nonce + created + password))`.** The nonce goes in as raw bytes for the SHA1 but base64 into the `wsse:Nonce` XML element — mixing these up yields silent 401s. Always send PasswordDigest (not PasswordText); clock skew > 5 min also breaks auth.
- **ONVIF Profile S is deprecated 2027-03-31** (Profile Q already deprecated). Prefer Profile T (H.264/H.265 + metadata) and its Media2 `GetStreamUri`.
- **`AbsoluteMove` fails on cameras lacking `AbsolutePanTiltPositionSpace`** — fall back to `RelativeMove` or `ContinuousMove` with a short timeout.
- **RTSP often needs a separate credential from the ONVIF/SOAP user.** If the returned RTSP URI 401s, inject the user:pass into the URL or check the camera's RTSP user table.

## Scripts

- `scripts/viscactl.py` — VISCA over serial/UDP-IP: `pan-tilt`, `zoom`, `focus`, `preset`, `power`, `home`, `reset`, `raw`. Supports `--transport serial|udp-ip`, `--dry-run`, `--verbose`.
- `scripts/onvifctl.py` — ONVIF SOAP client: `discover`, `info`, `streams`, `snapshot`, `ptz {continuous|absolute|preset-goto|preset-set|stop}`. Pure-stdlib WS-Security; `--dry-run` prints the SOAP envelope + digest.
- `scripts/ptzdocs.py` — spec search/fetch: `list-pages`, `search`, `section`, `fetch`, `index`, `clear-cache`. Anti-hallucination lookup for VISCA/ONVIF.
