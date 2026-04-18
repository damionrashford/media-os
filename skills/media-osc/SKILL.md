---
name: media-osc
description: >
  Open Sound Control (OSC) wire protocol: OSC 1.0 and 1.1 spec, packet layout (address pattern + comma-prefixed type tag + 4-byte-aligned args), OSC bundles with NTP timetags, address-pattern matching (?/*/[]/{}), OSC over UDP/TCP/SLIP, liblo CLIs (oscsend, oscdump), python-osc library, Stanford CCRMA spec home. Use when the user asks to send an OSC message, dump incoming OSC packets, write a Python OSC client or server, bridge OSC to MIDI or DMX, control a visualizer/DAW/livecoding environment (SuperCollider/TouchDesigner/Max/Resolume) over OSC, build a show-control system, or parse the OSC wire format.
argument-hint: "[action]"
---

# Media OSC

**Context:** $ARGUMENTS

Hand-roll OSC 1.0/1.1 packets over UDP from the CLI. No dependencies. For real-time control of SuperCollider, TouchDesigner, Max/MSP, Resolume, QLab, Ableton Link, ReaCoder, or any OSC-speaking app.

## Quick start

- **Send a message:** → Step 2 (`send --host 127.0.0.1 --port 7000 /fader/1 --float 0.75`)
- **Dump incoming packets:** → Step 3 (`dump --port 7000`)
- **Ping (send then wait briefly):** → Step 4 (`ping --host 127.0.0.1 --port 7000 /ping`)
- **Send a bundle with a timetag:** → Step 5 (`bundle --host ... --json cues.json`)

## When to use

- Trigger a DAW/visualizer cue from a shell script or CI job.
- Bridge MIDI/DMX → OSC (pair with `media-midi` / `media-dmx`).
- Prototype a show-control protocol.
- Sniff OSC traffic to reverse-engineer an undocumented app.
- Ship a tiny cross-platform OSC client without Python or liblo deps.

## Step 1 — Wire format refresher

An OSC packet is either a **Message** or a **Bundle**:

```
Message := <address:OSC-string> <type-tag:OSC-string> <arg0> <arg1> ...
Bundle  := "#bundle\0" <timetag:u64 NTP> <size:i32> <packet> <size:i32> <packet> ...
```

- **OSC-string:** null-terminated ASCII padded to 4-byte multiple.
- **Type tag:** starts with `,` then one char per arg (`i`=int32 `f`=float32 `s`=string `b`=blob, OSC 1.1 adds `T`=true `F`=false `N`=nil `I`=impulse/infinitum `h`=int64 `d`=double `t`=timetag).
- **Every arg is 4-byte aligned.** blobs are `<size:i32><bytes><pad>`.
- **Int/Float are big-endian.**
- **NTP timetag:** 32-bit seconds since 1900-01-01 + 32-bit fractional. Special value `0x00000000_00000001` = "execute immediately".

Address-pattern matching (1.0):

- `?` → single non-`/` char
- `*` → any run of non-`/` chars
- `[abc]` / `[a-z]` / `[!abc]` → char set
- `{alt1,alt2}` → alternatives
- OSC 1.1 adds `//` → zero or more path segments.

## Step 2 — Send

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 7000 \
    /fader/1 --float 0.75

uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 7000 \
    /trigger --int 1 --string "cue-3"
```

Mix `--int`, `--float`, `--string`, `--true`, `--false`, `--nil`, `--blob-hex`. The script builds the type tag from the order of flags.

TCP with SLIP framing (OSC 1.1):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send --tcp \
    --host 127.0.0.1 --port 7000 /volume --float 0.5
```

## Step 3 — Dump (listen)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py dump --port 7000
```

Pretty-prints each received packet. Recurses into bundles. Ctrl-C to stop.

## Step 4 — Ping reachability

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py ping --host 192.168.1.50 --port 7000 /ping
```

Sends, waits 500 ms, reports whether any reply was received on the same socket (for apps that mirror).

## Step 5 — Send a bundle

```bash
cat > cues.json <<'JSON'
{
  "timetag": "+0.5",
  "messages": [
    {"address": "/fader/1", "args": [{"type": "f", "value": 0.25}]},
    {"address": "/cue/go",  "args": [{"type": "i", "value": 3}]}
  ]
}
JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py bundle \
    --host 127.0.0.1 --port 7000 --json cues.json
```

`timetag`:

- `"now"` or `"immediate"` → special 0x00000000_00000001.
- `"+0.5"` → 500 ms from now.
- `1234567890.25` → absolute Unix float timestamp (will be converted to NTP).

## Gotchas

- **Do NOT reference `opensoundcontrol.org` — that domain is dead.** Use `opensoundcontrol.stanford.edu/spec-1_0.html` and `spec-1_1.html` (hosted by CCRMA, Stanford).
- **Every OSC string is null-terminated AND padded to 4-byte multiple.** `/foo` becomes `2f 66 6f 6f 00 00 00 00` (5 bytes of content, pad to 8). Parsers that forget the pad misalign all subsequent args.
- **Type tag starts with `,`, not `,,` or nothing.** An empty-arg message is `,` + 3 zero pad = 4 bytes total type-tag chunk.
- **NTP epoch is 1900-01-01**, not 1970. `ntp = unix + 2208988800`.
- **UDP can drop or reorder. OSC has no retransmit.** For guaranteed delivery use TCP with SLIP framing (OSC 1.1) — but most apps default to UDP.
- **OSC over TCP needs framing.** Either 4-byte length prefix (easy) or SLIP (OSC 1.1 — END `0xC0`, ESC `0xDB`, escape `END`→`DB DC`, `ESC`→`DB DD`). Apps disagree; check docs. Our helper defaults to length-prefix for TCP.
- **Address patterns are case-sensitive.** `/Fader/1` ≠ `/fader/1`.
- **`oscchief` is dormant** and many distros don't package it. Use `oscsend`/`oscdump` from liblo (`brew install liblo`, `apt install liblo-tools`).
- **python-osc is the current lingua franca** (`from pythonosc.udp_client import SimpleUDPClient`). `pyOSC` is abandoned — don't use it.
- **`,i` means ONE int arg**, `,ii` means two ints, `,if` means int-then-float. Get the order wrong and everything after drifts.
- **Blob size (i32) is the actual blob size, not including the padding.** But the blob in the packet IS padded. Readers that skip based on the i32 without adding the pad hit the wrong offset.

## Examples

### Example 1 — Ableton Live via LiveOSC / AbletonOSC

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 11000 /live/play
```

### Example 2 — SuperCollider scsynth

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 57110 /s_new --string "default" --int -1 --int 0 --int 0
```

### Example 3 — TouchDesigner OSC In CHOP

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 192.168.1.20 --port 10000 /ch1/vol --float 0.6
```

### Example 4 — Resolume composition trigger

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 7000 /composition/layers/1/clips/1/connect --int 1
```

### Example 5 — Dry-run a packet (see the hex bytes)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/oscctl.py send \
    --host 127.0.0.1 --port 7000 /fader/1 --float 0.75 --dry-run
```

## Reference docs

- [`references/osc-types.md`](references/osc-types.md) — full type-tag table, address-pattern grammar, SLIP escaping, NTP timetag math.

## CLI alternatives

- `oscsend` / `oscdump` from liblo — `brew install liblo` or `apt install liblo-tools`.
- `sendosc` (Go) — single binary, no deps.
- `oscli` (Python) — pip installable.
- PyPI `python-osc` for programmatic use.

## Troubleshooting

### Receiving app sees nothing

**Cause:** Wrong port, firewall, or sending to 127.0.0.1 instead of 0.0.0.0/LAN IP.
**Solution:** `tcpdump -i any -nn udp port 7000` to confirm packets on the wire. Fix firewall or bind address.

### Args arrive as garbage (wrong types)

**Cause:** Type tag order doesn't match arg order, or missing leading `,`.
**Solution:** Use `--dry-run --verbose` to print the exact bytes. Rebuild with args in declared order.

### Bundle ignored

**Cause:** Some apps reject bundles with past timetags.
**Solution:** Use `"now"` for immediate, or `"+0.1"` for a tiny future delay.

### TCP framing mismatch

**Cause:** Receiver expects SLIP but we send length-prefix (or vice versa).
**Solution:** Most apps accept either; check docs. `--tcp-framing slip` forces SLIP.

### Stanford URL 404

**Cause:** Path changed.
**Solution:** Canonical pages are `https://opensoundcontrol.stanford.edu/spec-1_0.html` and `spec-1_1.html`. If those 404, try `https://ccrma.stanford.edu/groups/osc/`.
