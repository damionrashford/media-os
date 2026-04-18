---
name: media-midi
description: >
  MIDI 1.0 and 2.0 wire protocol, control surfaces, and SMF file authoring: sendmidi/receivemidi (macOS/Linux/Windows), ALSA amidi/aconnect/aplaymidi/arecordmidi/aseqdump (Linux), mido and python-rtmidi (cross-platform Python), SMF chunks (MThd/MTrk with VLQ delta times), Universal MIDI Packet (UMP) groups for MIDI 2.0, MIDI-CI negotiation, standard CC numbers, General MIDI program tables, sysex framing. Use when the user asks to send MIDI messages, trigger notes from a script, route a control surface, parse or write a .mid file, bridge MIDI over USB/BT, work with UMP packets, run MIDI-CI property exchange, or speak MIDI to a synth/DAW from the CLI.
argument-hint: "[action]"
---

# Media MIDI

**Context:** $ARGUMENTS

Wire-level MIDI 1.0 + 2.0, Standard MIDI Files (SMF), and control-surface plumbing. Not a DAW — for sequencing use a DAW; this skill is the CLI layer under it.

## Quick start

- **List MIDI ports:** → Step 1 (`list-ports`)
- **Send a note-on to port X:** → Step 2 (`send note-on --port "IAC" --channel 1 --note 60 --velocity 100`)
- **Monitor incoming MIDI:** → Step 3 (`dump`)
- **Parse a .mid file:** → Step 4 (`smf-dump file.mid`)
- **Author a .mid programmatically:** → Step 4 (`smf-write --json events.json --out song.mid`)

## When to use

- Trigger notes / CCs / program changes from a shell script (automation, QA, live show cues).
- Build a control surface that speaks to Ableton / Logic / Pro Tools / Reaper / MainStage / Bitwig.
- Round-trip parse and author `.mid` files programmatically (Standard MIDI File format 0/1/2).
- Sniff a hardware controller's output for reverse-engineering.
- Work with MIDI 2.0 UMP packets (32/64/96/128-bit) when the target supports it.

## Step 1 — Detect ports

`midictl.py list-ports` probes the platform and shells out to the appropriate tool:

- **macOS:** `sendmidi list` (if installed) or uses Core MIDI directly via `mido`/`rtmidi` if present.
- **Linux:** `amidi -l` + `aconnect -l` (ALSA).
- **Windows:** `sendmidi list`.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py list-ports
```

Install tools (macOS/Linux/Windows cross-platform): `brew install gbevin/tools/sendmidi` (also installs `receivemidi`).

## Step 2 — Send messages

```bash
# Note on/off at channel 1 (1-indexed in CLI, 0x90/0x80 on wire)
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send note-on \
    --port "IAC Driver Bus 1" --channel 1 --note 60 --velocity 100
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send note-off \
    --port "IAC Driver Bus 1" --channel 1 --note 60

# Continuous controller
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send cc \
    --port "IAC Driver Bus 1" --channel 1 --cc 74 --value 64

# Program change
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send program \
    --port "IAC Driver Bus 1" --channel 1 --program 42

# System Exclusive
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send sysex \
    --port "IAC Driver Bus 1" --hex 'F0 7E 7F 06 01 F7'  # Identity request
```

## Step 3 — Monitor

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py dump --port "MyController"
# or on Linux specifically via aseqdump
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py monitor --port 24:0
```

## Step 4 — SMF files

```bash
# Parse .mid to human-readable events + JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py smf-dump song.mid --format json

# Author .mid from a JSON event list
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py smf-write \
    --json events.json --out song.mid --ppq 480 --format 1
```

Input JSON schema (each entry = {delta_ticks, type, channel, data1, data2, [meta: name, tempo, time_sig, ...]}).

## Gotchas

- **MIDI 1.0 serial is 31,250 bps 8-N-1.** USB-MIDI and BLE-MIDI wrap the same status+data bytes in USB-MIDI Class (CIN codes) or BLE-MIDI (timestamp headers). The message semantics are identical.
- **Status byte high bit is set (0x80-0xFF).** Data bytes are 7-bit (MSB clear). If a data byte has its MSB set, your stream is broken.
- **Running status is legal and common.** Subsequent Channel Voice messages of the same status may omit the status byte. Parsers that don't track running status will lose data.
- **Sysex is `F0 <manufacturer> ... F7`.** Never truncate before `F7` — dropped `F7` hangs the device. Universal Real-Time / Non-Real-Time sysex use mfr IDs `7E`/`7F`.
- **MIDI 2.0 UMP ≠ MIDI 1.0.** UMP is 32/64/96/128-bit packets; 16 "groups" × 16 channels. Messages Type 0x2 (MIDI 1.0 CV in UMP) ≠ Type 0x4 (MIDI 2.0 CV). **MIDI-CI discovery/negotiation runs over MIDI 1.0 sysex**, not over UMP.
- **SMF = `MThd` (6 B: format, ntracks, division) + `MTrk`** chunks. Each MTrk event is `VLQ delta-time` + event stream. Format 0 = one track, Format 1 = multiple tracks sharing tempo map, Format 2 = independent tracks (rare).
- **VLQ (variable-length quantity) is big-endian base-128.** Each byte's high bit signals continuation (1 = more bytes, 0 = last). `0x40` = 64, `0x81 0x00` = 128, `0x82 0x80 0x00` = 32768. Get this wrong and your whole SMF is misaligned.
- **Tempo meta-event is microseconds per quarter note** (500000 = 120 BPM), not BPM directly.
- **Channels are 1-indexed in UIs but 0-indexed on the wire.** Ch 1 = status nibble 0. The helper takes 1-indexed `--channel` values.
- **`rtmidi-cli` does NOT exist as a packaged binary.** Don't reference it. The Python `python-rtmidi` library is real; `sendmidi`/`receivemidi` by gbevin are the real cross-platform CLIs.
- **Full MIDI 2.0 spec PDFs are login-gated at `https://midi.org/join-now`.** Public overviews live at `https://midi.org/specs`. Link both; note the gate.
- **BLE-MIDI timestamp overflow at 13 bits = 8192 ms.** Long sysex must be split into multiple BLE packets with timestamp continuation bytes.
- **ALSA sequencer addresses look like `client:port` (e.g. `128:0`)**, not device paths. Use `aconnect -l` to enumerate.
- **On macOS, the IAC Driver is off by default.** Enable it in Audio MIDI Setup → MIDI Studio → IAC Driver → check "Device is online" — otherwise there are no virtual ports to send to.

## Examples

### Example 1 — Trigger a C-major chord

```bash
for n in 60 64 67; do
    uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send note-on \
        --port "IAC Driver Bus 1" --channel 1 --note $n --velocity 100
done
sleep 1
for n in 60 64 67; do
    uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send note-off \
        --port "IAC Driver Bus 1" --channel 1 --note $n
done
```

### Example 2 — Identity request (universal sysex)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py send sysex \
    --port "MyController" --hex 'F0 7E 7F 06 01 F7'
```

### Example 3 — Dump events from a .mid

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py smf-dump song.mid
```

### Example 4 — Build a tiny SMF

```bash
cat > events.json <<'JSON'
[
  {"delta": 0, "type": "tempo", "bpm": 120},
  {"delta": 0, "type": "note-on", "channel": 1, "note": 60, "velocity": 100},
  {"delta": 480, "type": "note-off", "channel": 1, "note": 60}
]
JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/midictl.py smf-write --json events.json --out c.mid
```

## Reference docs

- [`references/cc-table.md`](references/cc-table.md) — complete MIDI 1.0 CC number table (0-127) with official names.
- [`references/ump-packets.md`](references/ump-packets.md) — MIDI 2.0 UMP type/status codes.

## Troubleshooting

### `port "X" not found`

**Cause:** Port name typo, IAC disabled (macOS), or ALSA sequencer subsystem not loaded.
**Solution:** Run `list-ports` to see the canonical names. On macOS enable IAC in Audio MIDI Setup. On Linux ensure `snd-seq` module is loaded.

### Notes hang (never stop)

**Cause:** Missed note-off. Happens with aborted scripts.
**Solution:** Send `CC 123 (All Notes Off)` to the channel or power-cycle the synth.

### `sendmidi` not found

**Cause:** Not installed.
**Solution:** `brew install gbevin/tools/sendmidi`. Helper falls back to ALSA `amidi` / Python `mido`/`rtmidi` if any is available.

### Parser errors on SMF

**Cause:** Malformed VLQ or missing `F7` terminator in an embedded sysex.
**Solution:** Inspect the file with `od -c` or `xxd`; compare against spec in `references/`.
