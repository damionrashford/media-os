---
name: media-dmx
description: >
  Stage lighting protocols: DMX512-A (ANSI E1.11 serial, 250 kbps RS-485, 512 slots per universe, RDM E1.20 bidirectional config), Art-Net 4 (UDP port 6454, ASCII Art-Net header + 15-bit universe addressing from Artistic Licence), sACN / E1.31 (UDP multicast 239.255.X.Y port 5568 with universe sync + priority), Open Lighting Architecture (OLA — olad daemon, ola_streaming_client, ola_recorder, ola_dmxconsole, ola_patch, ola_rdm_get/set, ola_artnet, ola_e131, ola_usbpro for Enttec USB Pro), Enttec Open DMX + USB Pro serial framing. Use when the user asks to control stage lights, send DMX, drive an Art-Net node, stream sACN, discover RDM devices, patch a lighting rig from code, send a show cue, record/playback a DMX show, or bridge OSC/MIDI to lighting.
argument-hint: "[action]"
---

# Media DMX

**Context:** $ARGUMENTS

Control stage lighting: DMX512 over serial, Art-Net over UDP/6454, sACN/E1.31 over UDP multicast/5568, plus Enttec USB Pro framing. Ships a pure-Python sACN sender (no OLA needed), plus wrappers around the OLA CLIs when available.

## Quick start

- **List connected devices:** → Step 2 (`list-devices`)
- **Send a single DMX frame on one universe:** → Step 3 (`send-dmx --universe 1 --slots 255,0,128,64`)
- **Raw-Python sACN sender (no OLA):** → Step 4 (`sacn-send --universe 1 --slots 255,0,...`)
- **Art-Net poll (discovery):** → Step 5 (`artnet-poll`)
- **Record / stream a show:** → Step 6 (`record` / `stream`)
- **RDM discovery / get / set:** → Step 7 (`rdm-scan`)

## When to use

- Drive LED PARs / movers / dimmers / hazers from a show-control script.
- Bridge OSC/MIDI → lighting (pair with `media-osc` / `media-midi`).
- Build a cue stack without a console (pair with `ola_recorder`).
- Discover and configure RDM-capable fixtures (E1.20).
- Send sACN priority-aware streams to a grandMA / MagicQ / Avolites / Chamsys node.

## Step 1 — Protocol cheat sheet

- **DMX512-A / E1.11:** RS-485 differential pair, 250 kbps, 8-N-2. Each frame = BREAK (≥88 µs low) + MAB (Mark After Break, ≥8 µs high) + start code (0x00 = dimmer data) + 1..512 slots of 8-bit data. ~44 Hz max refresh.
- **RDM / E1.20:** Bidirectional config over the same DMX bus using start code **0xCC**. Discovery uses unique IDs (6 bytes: 2-byte mfr + 4-byte device).
- **Art-Net 4:** UDP port **6454**. ASCII header `Art-Net\0` + 16-bit OpCode (little-endian). OpCodes include `OpPoll=0x2000`, `OpPollReply=0x2100`, `OpDmx=0x5000`, `OpSync=0x5200`, `OpAddress=0x6000`. Universe = Net(7 bits) + SubNet(4) + Universe(4) = up to 32768 universes. Broadcasts default to `2.255.255.255` (Artistic Licence "primary") or subnet broadcast on consumer networks.
- **sACN / E1.31:** UDP multicast `239.255.X.Y` where X = (universe >> 8), Y = (universe & 0xFF); port **5568**. Packet = ACN Root Layer + E1.31 Framing Layer (priority 0-200, default 100, sync address) + DMP Layer (start code + slot data). Universe Sync via a "null-universe" sync packet.

## Step 2 — List devices

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py list-devices
```

Requires OLA's `olad` running. Wraps `ola_dev_info` and `ola_uni_info`. Without OLA the command falls back to listing `/dev/tty*` serial ports on macOS/Linux so you can at least see Enttec USB Pro adapters.

## Step 3 — Send a DMX frame (OLA path)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py send-dmx \
    --universe 1 --slots 255,0,128,64,200,10,5
```

Wraps `ola_streaming_client`. The OLA daemon handles the chosen output (USB Pro, Art-Net, sACN, serial) based on the patch.

## Step 4 — Pure-Python sACN (no OLA needed)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py sacn-send \
    --universe 1 --slots 255,0,128,64 \
    --priority 100 --source-name "Claude"
```

Builds the ACN + E1.31 + DMP packet in stdlib and multicasts to `239.255.0.1` (for universe 1). Uses a small built-in sequence-number counter per universe.

```bash
# Continuous 44 Hz stream of the same frame until Ctrl-C
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py sacn-send \
    --universe 1 --slots 255,0,0,0 --repeat --rate 44
```

## Step 5 — Art-Net poll (discovery)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py artnet-poll --timeout 2
```

Broadcasts `OpPoll=0x2000` to 255.255.255.255 on UDP 6454 and collects `OpPollReply=0x2100` responses. Reports node IP, short/long name, firmware, and published universes.

## Step 6 — Record / stream shows

```bash
# Stream from stdin (one frame per line, comma-separated slots)
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py stream --universe 1

# Record an OLA show
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py record --universe 1 --out show.ola
```

## Step 7 — RDM

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py rdm-scan --universe 1
```

Wraps `ola_rdm_discover`. Returns the list of UIDs on the universe. `ola_rdm_get` / `ola_rdm_set` are available via `--get PID` / `--set PID=VALUE`.

## Gotchas

- **RS-485 termination matters.** Missing 120 Ω terminator at the far end of a DMX run causes reflections → flicker, stuck channels. First fault to check when output looks garbage.
- **DMX universe is 1-indexed in UIs but 0-indexed in Art-Net.** Port-Address = `Net(7)+SubNet(4)+Universe(4)` — universe 1 on wire is Port-Address 0. sACN and OLA vary: sACN uses 1..63999 directly; OLA universe IDs are user-assigned integers.
- **Start code 0x00 for dimmer data; 0xCC for RDM.** Mixing them breaks receivers that don't track start code.
- **Max ~32 devices per DMX segment** before repeater needed (per E1.11). People get away with 48 on short runs but it's out of spec.
- **Art-Net broadcast on 255.255.255.255 may be dropped** by managed switches. Artistic Licence primary is `2.x.x.x/8`; most networks use the subnet broadcast instead. Node responds unicast anyway.
- **sACN multicast address = `239.255.<uni_hi>.<uni_lo>`.** Universe 1 → `239.255.0.1`, universe 256 → `239.255.1.0`. Get the byte order wrong and your console sends to a ghost.
- **sACN priority 0 is a reserved "ignore"**. Use 1–200; 100 is default. Universe sync requires all transmitters on the same sync-address and at least one "null-start-code 0xdd" sync packet.
- **Enttec USB Pro framing:** SOM `0x7E` + label (1 B) + length LE (2 B) + data + EOM `0xE7`. Common labels: 6 = send DMX, 5 = receive DMX, 3 = set widget params. Open DMX (non-Pro) has NO framing — just raw UART at 250k.
- **On macOS, USB Pro adapters appear as `/dev/tty.usbserial-...`.** On Linux they're `/dev/ttyUSB0`. Permissions: add the user to `dialout` (Linux) or grant full-disk access to terminal (macOS).
- **`artnetify`, `artnet-ctl`, `ArtNetomatic` do NOT exist as real tools.** Don't reference them. The real CLIs for Art-Net are via OLA (`ola_artnet`) or proprietary node firmware.
- **`sacn` (PyPI) is pure Python and real.** For non-OLA users this is the easiest sACN library; our helper mirrors its packet layout.
- **OLA's `olad` must be running** (`brew services start ola` or `systemctl start olad`) for any `ola_*` CLI to work. Without it, OLA commands fail with "unable to connect to olad".
- **ESTA specs (E1.11, E1.20, E1.31) are free but gated** behind a EULA click-through at `https://tsp.esta.org/tsp/documents/published_docs.php`.
- **Art-Net spec PDF has a captcha** on the direct URL — go through `https://art-net.org.uk/resources/` to download.

## Examples

### Example 1 — Fade a single channel from OSC

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py sacn-send \
    --universe 1 --slots 255,0,0,0 --priority 100 --source-name fade
```

### Example 2 — Blackout everything on universe 1

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py sacn-send \
    --universe 1 --slots $(python -c 'print(",".join(["0"]*512))')
```

### Example 3 — Discover Art-Net nodes on the LAN

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py artnet-poll --timeout 3 --format json
```

### Example 4 — Dry-run see the sACN packet bytes

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dmxctl.py sacn-send \
    --universe 1 --slots 255,128,0 --dry-run --verbose
```

## Reference docs

- [`references/wire-format.md`](references/wire-format.md) — DMX512, Art-Net, sACN, RDM packet layouts with byte-exact diagrams.
- [`references/enttec-labels.md`](references/enttec-labels.md) — Enttec USB Pro label table.

## CLI alternatives

- **OLA (Open Lighting Architecture):** `olad` + the `ola_*` family — the universal Linux/macOS backend. Full list: `ola_dev_info`, `ola_uni_info`, `ola_patch`, `ola_dmxconsole`, `ola_dmxmonitor`, `ola_streaming_client`, `ola_recorder`, `ola_artnet`, `ola_e131`, `ola_usbpro`, `ola_rdm_discover`, `ola_rdm_get`, `ola_rdm_set`.
- **`sacn` (Python, PyPI):** easy pure-Python sACN.
- **QLC+, Chamsys MagicQ, grandMA3 onPC:** GUI apps for cue stacks — complement this skill.

## Troubleshooting

### OLA command "unable to connect to olad"

**Cause:** olad daemon not running.
**Solution:** `brew services start ola` (macOS) or `sudo systemctl start olad` (Linux).

### sACN packets sent but receiver sees nothing

**Cause:** Multicast blocked by router/firewall, or wrong universe → wrong multicast group.
**Solution:** Check `sudo tcpdump -i any -nn udp port 5568` for outgoing packets. Verify universe 1 = `239.255.0.1`, not `239.255.1.0`.

### Art-Net node unresponsive to ArtPoll

**Cause:** Node bound to different IP range (Artistic Licence primary `2.x.x.x`) vs your LAN.
**Solution:** Unicast an OpPoll to the node's known IP, or set the node's IP to match your subnet via its web UI.

### DMX output garbled / flickering

**Cause:** Missing termination, too many fixtures on one segment, or wrong baud.
**Solution:** Add 120 Ω terminator. Limit segment to 32 fixtures. Confirm 250 kbps 8-N-2.

### Enttec USB Pro doesn't enumerate

**Cause:** No FTDI driver (macOS older), or permissions.
**Solution:** Install FTDI VCP driver (macOS pre-Catalina only; post-Catalina uses Apple's built-in). On Linux `sudo usermod -aG dialout $USER` and re-login.
