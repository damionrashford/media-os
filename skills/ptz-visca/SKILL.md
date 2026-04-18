---
name: ptz-visca
description: >
  Control PTZ cameras with Sony VISCA protocol (RS-232/485 serial 9600/38400 8N1, or UDP:52381 with 8-byte payload header): pan/tilt/zoom/focus/exposure/WB commands, libvisca + libvisca-ip, python-visca, pyvisca, pysca, visca-over-ip. Supported cameras: Sony (BRC/SRG/FR7/FCB modules), PTZOptics, AVer Pro-AV, Panasonic AW-series partial, Bolin, Avonic, Lumens, Marshall, Canon CR-N subset. Use when the user asks to drive a PTZ camera, move a PTZOptics/Sony cam, send pan-tilt over IP, control a camera preset, zoom/focus from a script, build a VISCA packet, or integrate a PTZ rig into OBS/vMix.
argument-hint: "[action]"
---

# PTZ VISCA

**Context:** $ARGUMENTS

Send Sony VISCA commands to a PTZ camera over serial (RS-232C/422/485) or IP (UDP:52381). For spec lookup / command byte tables see `ptz-docs`. For IP cameras without VISCA (ONVIF Profile S/T) use `ptz-onvif`.

## Quick start

- **Pan/tilt the camera:** → Step 3 (`pan-tilt --x 8 --y 0 --duration 1`)
- **Recall a preset:** → Step 3 (`preset recall --number 2`)
- **Zoom tele/wide:** → Step 3 (`zoom --direction tele --speed 4`)
- **Focus:** → Step 3 (`focus --mode auto` / `--mode near`)
- **Send a raw packet:** → Step 3 (`raw --hex '81 01 04 00 02 FF'`)

## When to use

- Drive a broadcast / streaming PTZ (Sony BRC/SRG/FR7, PTZOptics, AVer Pro-AV, Panasonic AW, Bolin, Avonic, Lumens, Marshall, Canon CR-N) from a script.
- Remote-control a camera over LAN from a producer laptop without Sony CGI software.
- Build an OBS/vMix/Companion integration.
- Dry-run a packet before sending (see exact bytes, skip network).

## Step 1 — Pick the transport

- **Serial (RS-232C / RS-422 / RS-485):** 9600 or 38400 baud, 8N1. Multi-camera daisy-chain via address 1–7 in the first byte. Requires `pyserial` for the Python helper (optional — detected at runtime; otherwise fall back to IP).
- **IP (UDP:52381):** 8-byte payload header wraps the serial VISCA message. No retransmit at protocol level — add your own at the app layer if you need reliability. Sony, PTZOptics, AVer, Bolin, Marshall, Lumens, Canon CR-N all use the same wrapper.

Pass `--transport serial|udp-ip` to `viscactl.py`. Default is `udp-ip`.

## Step 2 — Identify the camera

Address 1–7 (broadcast 8). First byte = `0x80 | addr` on wire.

| Camera | Default port | Default addr |
|---|---|---|
| Sony BRC-H900 | 52381 | 1 |
| Sony SRG-300H | 52381 | 1 |
| Sony FR7 | 52381 | 1 |
| PTZOptics (G2/G3/Move SE/Move 4K) | 1259 (legacy) / 52381 (modern) | 1 |
| AVer Pro-AV (PTZ310 etc.) | 52381 | 1 |
| Panasonic AW-UE | 52381 | 1 |

PTZOptics legacy firmware uses port **1259**; newer units standardized on 52381. Check the camera's OSD/web UI if in doubt. Use `--port` to override.

## Step 3 — Drive the camera

```bash
# IP (default)
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py pan-tilt \
    --host 192.168.1.100 --address 1 \
    --x 8 --y 0 --duration 1.5

uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py zoom \
    --host 192.168.1.100 --direction tele --speed 4 --duration 1

uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py preset \
    --host 192.168.1.100 --action recall --number 2

uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py focus \
    --host 192.168.1.100 --mode auto

uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py power \
    --host 192.168.1.100 --action on

uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py home --host 192.168.1.100
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py reset --host 192.168.1.100

# Serial
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py pan-tilt \
    --transport serial --serial-port /dev/tty.usbserial-AB0J8W5C --baud 9600 \
    --x 0 --y 6 --duration 1

# Raw escape hatch
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py raw \
    --host 192.168.1.100 --hex '81 01 04 3F 02 01 FF'
```

Every command supports `--dry-run` (print packet, skip send) and `--verbose` (trace bytes on stderr).

## Step 4 — Read the reply

After a Command, expect ACK (`y0 4z FF`) then Completion (`y0 5z FF`). After an Inquiry, expect Completion carrying the data. Errors return `y0 6z ee FF` where ee is:

| ee | Meaning |
|---|---|
| 01 | Message length error |
| 02 | Syntax error |
| 03 | Command buffer full |
| 04 | Command canceled |
| 05 | No socket (to cancel) |
| 41 | Command not executable |

For IP transport, the 8-byte payload header on replies uses payload type `0x0111` (VISCA reply).

## Gotchas

- **First byte is `0x80 | address`, not a literal `0x81`.** `0x81` means address=1; `0x82`=address 2, etc. Broadcast is `0x88`.
- **Every VISCA packet ends with `0xFF`.** It's the terminator, not a length field.
- **VISCA-over-IP wraps the serial VISCA in an 8-byte header** (payload type + length + seq#). Do NOT just TCP-tunnel the serial form — you'll get silent drops because IP cameras reject unwrapped VISCA.
- **PTZOptics legacy firmware listens on UDP:1259.** Modern firmware uses 52381. If `52381` times out, retry on `1259`.
- **PanTilt speed is 1–24 for pan, 1–20 for tilt on Sony BRC.** Older cams use 1–18 / 1–17. Exceeding the range triggers `Syntax error (ee=02)`.
- **Preset IDs are 0–127 on Sony spec** but AVer extends to 0–255. PTZOptics respects 0–255 too. Passing >127 to a strict Sony unit returns `Command not executable (41)`.
- **Commands must not stack too fast on serial** — wait for Completion before sending the next. IP is more forgiving but still commits to FIFO inside the camera; sending 200 commands/sec will overflow the 2-socket queue and you'll get `Command buffer full (03)`.
- **There is no built-in retransmit on UDP-IP.** Packet loss → camera never moved. For production, resend after N ms if no Completion arrives.
- **Zoom direct position is 4 nibbles** (`0p 0q 0r 0s`) — NOT 4 hex bytes. Each nibble carries 4 bits of the position. Same for absolute pan/tilt (`0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z`, 16-bit position split across 4 nibbles each).
- **pyserial is optional.** The helper runs IP without it. If you need serial, `pip install pyserial` — script auto-detects. No pyserial → `--transport serial` exits with a hint.
- **Sequence number is monotonic per session.** Reset to 1 after reconnect.
- **Home position is a separate command from preset 0.** `PanTilt Home` (`8x 01 06 04 FF`) is the factory-set center; preset 0 is user-defined.

## Examples

### Example 1 — Nudge left 1 second

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py pan-tilt \
    --host 192.168.1.100 --x -6 --y 0 --duration 1
```

### Example 2 — Save preset 3 at current position

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py preset \
    --host 192.168.1.100 --action save --number 3
```

### Example 3 — Manual focus, push near

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py focus \
    --host 192.168.1.100 --mode manual
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py focus \
    --host 192.168.1.100 --mode near --speed 3 --duration 1
```

### Example 4 — Broadcast "Home" to every camera on the bus

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py home \
    --host 192.168.1.100 --address 8
```

### Example 5 — Dry-run the bytes before sending

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/viscactl.py zoom \
    --host 192.168.1.100 --direction tele --speed 4 --duration 1 --dry-run
```

## Reference docs

- [`references/commands.md`](references/commands.md) — VISCA command table (Pan/Tilt, Zoom, Focus, Exposure, WB, Preset, Inquiries) with exact byte sequences.

## Python library alternatives

- `visca-over-ip` (PyPI) — async, straightforward IP transport.
- `pyvisca` / `python-visca` — older, serial-focused.
- `pysca` — reactive-style.
- `libvisca` (C) — `github.com/norihiro/libvisca-ip` adds TCP+UDP support on top of upstream libvisca.

## Troubleshooting

### Timeout, no reply

**Cause:** Wrong port (1259 vs 52381), wrong address, or camera VISCA disabled in OSD.
**Solution:** Ping the camera, check VISCA-over-IP enabled in camera web UI, try `--port 1259` for older PTZOptics.

### Reply carries `ee=02` Syntax error

**Cause:** Invalid byte sequence — wrong speed range, wrong nibble packing.
**Solution:** Check `references/commands.md` for the exact shape. Use `--dry-run --verbose` to inspect bytes before sending.

### Reply carries `ee=03` Command buffer full

**Cause:** Sent commands faster than the camera could complete them.
**Solution:** Wait for Completion before sending the next, or throttle to ~10 Hz.

### Reply carries `ee=41` Command not executable

**Cause:** Valid syntax but the camera can't run it now (e.g. focus direct when in AF, preset >127 on strict Sony).
**Solution:** Change state first (e.g. `focus --mode manual`) then retry.

### pyserial not installed

**Cause:** `--transport serial` without the optional pyserial dep.
**Solution:** `pip install pyserial` — or switch to `--transport udp-ip`.

### Packets arrive but camera doesn't move

**Cause:** Pan/tilt speed = 0 (stop), or direction bytes wrong (`03 03` = stop).
**Solution:** Use non-zero `--x`/`--y` magnitude; see the direction matrix in `references/commands.md`.
