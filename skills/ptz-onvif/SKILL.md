---
name: ptz-onvif
description: >
  Discover and control ONVIF IP cameras via SOAP/XML with WS-Security UsernameToken digest: onvif-util (libonvif github.com/sr99622/libonvif), onvif-cli (github.com/gardere/onvif-cli), python-onvif-zeep (PyPI onvif-zeep), onvif_control (bash + WS-Security), gonvif (Go). WS-Discovery multicast to 239.255.255.250:3702 finds ProbeMatch responses. Services: Device Management, Media (RTSP URIs), PTZ, Imaging, Events, Recording/Search/Replay, Analytics. Profiles: S (deprecated 2027), T (H.264/H.265 + metadata), G (recording), M (analytics), A/C/D (access). Use when the user asks to discover ONVIF cameras, get an RTSP stream URL, move a PTZ via ONVIF (ContinuousMove/AbsoluteMove/GotoPreset), grab a snapshot, authenticate with UsernameToken digest, or query a camera's ONVIF capabilities.
argument-hint: "[command]"
---

# PTZ ONVIF

**Context:** $ARGUMENTS

Speak ONVIF (SOAP 1.2 / XML / WS-Security) to IP cameras — the industry-standard way to discover devices, pull RTSP URIs, and drive PTZ without vendor SDKs. For low-level Sony VISCA (non-ONVIF PTZ) use `ptz-visca`. For spec lookup see `ptz-docs`.

## Quick start

- **Discover all cameras on the LAN:** → Step 1 (`discover`)
- **Fetch basic camera info:** → Step 2 (`info --host 192.168.1.64 --user admin --password x`)
- **Get the RTSP stream URL:** → Step 3 (`streams`)
- **Grab a single snapshot:** → Step 4 (`snapshot`)
- **PTZ continuous pan-right:** → Step 5 (`ptz continuous --pan 0.5 --tilt 0 --timeout 1.5`)
- **PTZ absolute position or preset:** → Step 5 (`ptz absolute` / `ptz preset-goto`)

## When to use

- Turn up a new NVR/VMS deployment; inventory cameras on the subnet.
- Pull RTSP URIs programmatically for ffmpeg ingest without vendor apps.
- Build a control UI that speaks to any ONVIF-compliant camera (Hikvision, Dahua, Axis, Bosch, PTZOptics, Amcrest, Reolink, Uniview, ACTi, Vivotek, etc.).
- Script snapshots / presets / PTZ movement across heterogeneous brands.
- Subscribe to motion-detection events.

## Step 1 — Discover

WS-Discovery is a UDP multicast probe to `239.255.255.250:3702`. The helper sends a SOAP `<Probe>` envelope and parses `ProbeMatch` responses to extract each camera's Device service URL (`XAddrs`).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py discover --timeout 3
```

Output (JSON):

```json
[
  {"xaddr": "http://192.168.1.64:80/onvif/device_service",
   "types": "dn:NetworkVideoTransmitter tds:Device",
   "scopes": ["onvif://www.onvif.org/hardware/DS-2CD2", ...]}
]
```

WS-Discovery is **link-local** — it does NOT cross subnets or VLANs. For a camera you already know, skip to Step 2 with the Device service URL (usually `http://HOST/onvif/device_service`).

## Step 2 — Get device info

Requires WS-Security `UsernameToken` with digest:

```
Digest = BASE64( SHA1( nonce + created + password ) )
```

`nonce` is raw random bytes (NOT base64) used inside the SHA1. The header also carries the base64 of the nonce and the ISO-8601 `Created` timestamp.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py info \
    --host 192.168.1.64 --user admin --password 'S3cret' \
    --format json
```

Returns Manufacturer, Model, FirmwareVersion, SerialNumber, HardwareId.

## Step 3 — Fetch stream URIs (Media service)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py streams \
    --host 192.168.1.64 --user admin --password 'S3cret'
```

Enumerates media profiles and returns RTSP URIs suitable for ffmpeg:

```bash
ffmpeg -rtsp_transport tcp -i rtsp://admin:S3cret@192.168.1.64:554/... out.mp4
```

Pass `--rtsp-transport rtp-unicast` / `rtp-multicast` / `http` to tweak `SetStreamUri` negotiation.

## Step 4 — Snapshot

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py snapshot \
    --host 192.168.1.64 --user admin --password 'S3cret' \
    --output shot.jpg
```

Calls `GetSnapshotUri` then fetches the JPEG via HTTP Digest (most cameras) or Basic auth.

## Step 5 — PTZ

```bash
# Continuous move (ContinuousMove, auto-stop after --timeout)
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz continuous \
    --host 192.168.1.64 --user admin --password 'S3cret' \
    --pan 0.5 --tilt 0 --zoom 0 --timeout 1.5

# Absolute (AbsoluteMove)
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz absolute \
    --host ... --pan-x 0.5 --tilt-y -0.3 --zoom 0.2

# Goto preset
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz preset-goto \
    --host ... --preset-token 2

# Save current position as preset
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz preset-set \
    --host ... --preset-name "Cam1-Wide"

# Stop
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz stop --host ...
```

Pan/tilt velocities are normalized to `[-1.0, 1.0]`. Absolute positions also `[-1.0, 1.0]`; zoom `[0.0, 1.0]`. The helper auto-discovers the first ProfileToken if none is provided.

## Gotchas

- **WS-Discovery does NOT cross subnets.** It's link-local multicast only. For remote cameras, plug in the Device service URL directly or run a proxy on the camera's subnet.
- **WS-Security PasswordText vs PasswordDigest.** Spec requires digest. Some old cameras accept PasswordText, but sending PasswordText to a modern camera fails with `Sender not authorized`. Always compute the digest.
- **Nonce is raw bytes into SHA1, base64 into XML.** The digest is `SHA1(raw_nonce + created_str + password)`; the XML element's `wsse:Nonce` tag carries the BASE64-encoded nonce. Mixing these up produces silent 401 rejections.
- **Clock skew > 5 min breaks auth.** Many cameras reject digests with a `Created` timestamp too far from their own clock. If auth fails on a known-good password, check `ntp` on the camera — or add `--time-offset <sec>` when using the helper.
- **Profile S is deprecated 2027-03-31.** Profile T replaces it. When both exist, prefer T's Media2 service (`GetStreamUri` on Media2 vs Media v1).
- **`onvif-util` != `onvif-cli`.** Both are real (libonvif's `onvif-util` from github.com/sr99622/libonvif, and the PyPI/Go `onvif-cli`). Don't confuse them. **`camobaby` is NOT a real tool** — ignore any hallucinated reference.
- **Vendor-specific paths.** Most cameras expose `/onvif/device_service` but Axis uses `/onvif/services` and some OEM devices use `/onvif-http/snapshot`. Always resolve XAddrs via `GetCapabilities` or `GetServices` rather than assuming the path.
- **RTSP often wants a separate credential.** Cameras can have an "ONVIF user" (for SOAP) and a separate "RTSP user"; if the returned RTSP URL 401s, try injecting the same user/password or check the camera's own user table.
- **Port 80 for SOAP is common but not universal.** Hikvision NVRs often host SOAP on the camera at `:80` but on the NVR at `:8000`. `GetServices` returns authoritative URLs.
- **`AbsoluteMove` fails on cameras that don't report `AbsolutePanTiltPositionSpace`.** Fall back to `RelativeMove` or `ContinuousMove`. The helper raises a clear error.
- **`GetSnapshotUri` returns ONE URI but cameras often rate-limit it.** Don't poll at >1 Hz without testing; some units will refuse connections after burst requests.
- **High-ping cameras can exceed the default timeout.** Use `--timeout N` to override (default 8 s).
- **Python-onvif-zeep (PyPI `onvif-zeep`) is optional.** The helper ships a pure-stdlib SOAP client. If `onvif-zeep` is importable, the helper can fall back to it for complex flows (Events, Analytics) — but everything shown above works without it.

## Examples

### Example 1 — Discover and grab stream URIs in one shot

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py discover | \
    jq -r '.[].xaddr' | while read url; do
        uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py streams \
            --xaddr "$url" --user admin --password 'S3cret'
    done
```

### Example 2 — Point camera at preset 2 with a 1 s pre-move freeze

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz stop --host ... --user admin --password x
sleep 1
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py ptz preset-goto \
    --host ... --user admin --password x --preset-token 2
```

### Example 3 — Pipe the RTSP URI straight to ffmpeg

```bash
URL=$(uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py streams \
    --host ... --user admin --password x --format json \
    | jq -r '.[0].rtsp_uri')
ffmpeg -rtsp_transport tcp -i "$URL" -c copy out.mp4
```

### Example 4 — Dry-run the SOAP envelope

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/onvifctl.py info \
    --host ... --user admin --password x --dry-run --verbose
```

Prints the SOAP envelope and the computed WS-Security digest without hitting the network.

## Reference docs

- [`references/services.md`](references/services.md) — per-profile ONVIF service matrix, XAddr conventions, WS-Security digest recipe, canonical SOAP operation names.

## CLI alternatives

- `onvif-util` — libonvif (`github.com/sr99622/libonvif`), C, `brew install sr99622/libonvif/libonvif` or build from source.
- `onvif-cli` (Python) — `pipx install onvif-cli` (from `github.com/gardere/onvif-cli`).
- `onvif_control` (Bash) — `github.com/camelcamro/onvif_control`, minimal WS-Security + PTZ.
- `gonvif` (Go) — performant alternative for large fleets.
- PyPI `onvif-zeep` for Python dev; pure Python, full coverage incl. Events/Analytics.

## Troubleshooting

### WS-Discovery returns nothing

**Cause:** Not on the same L2 broadcast domain, or firewall drops multicast.
**Solution:** Confirm cameras on same subnet/VLAN. Disable firewall UDP blocks on port 3702. Fall back to unicast `GetCapabilities` with a known IP.

### HTTP 401 from SOAP endpoint

**Cause:** Digest mismatch — typically PasswordText vs PasswordDigest, or clock skew > 5 min.
**Solution:** Use `--verbose` to see the SOAP envelope. Verify the `Created` timestamp is current. Check the camera's NTP.

### `Sender not authorized` or `401` from digest

**Cause:** Wrong hashing order (`nonce + created + password` is required — in that order), or passing the base64-encoded nonce into the SHA1 instead of raw bytes.
**Solution:** Read `references/services.md` WS-Security pseudocode. Let `--dry-run --verbose` print the digest inputs.

### `ActionNotSupported` on `AbsoluteMove`

**Cause:** Camera lacks `AbsolutePanTiltPositionSpace`.
**Solution:** Use `ContinuousMove` with a short `--timeout` or `RelativeMove`.

### RTSP stream URL returns 401

**Cause:** Different user table for RTSP vs SOAP.
**Solution:** Embed user/password in the URL (`rtsp://user:pass@host/...`) or check the RTSP user in the camera UI.

### Snapshot URL 404s

**Cause:** Vendor's snapshot handler lives elsewhere despite what `GetSnapshotUri` returns.
**Solution:** Try the vendor's documented URL (e.g. `http://host/cgi-bin/snapshot.cgi` for Amcrest/Dahua), or use an `ffmpeg -frames:v 1` grab from the RTSP stream.
