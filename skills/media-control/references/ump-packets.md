# MIDI 2.0 Universal MIDI Packet (UMP) — type/status summary

UMP packets are 32/64/96/128 bits. The first 4 bits of the first word encode **Message Type (MT)**; bits 4-7 encode **Group** (0-15). Each group carries 16 MIDI channels, so UMP supports 256 logical channels.

## Message types (MT nibble)

| MT | Size | Category | Notes |
|---|---|---|---|
| 0x0 | 32-bit | Utility | NOOP, JR Clock, JR Timestamp |
| 0x1 | 32-bit | System Real-Time and Common | F8 timing clock, F0/F7 NOT here (use 0x3) |
| 0x2 | 32-bit | MIDI 1.0 Channel Voice | Legacy-compatible CV in UMP form |
| 0x3 | 64-bit | Data Message (64-bit) | SysEx 7-bit (F0..F7-equivalent split across UMP payloads) |
| 0x4 | 64-bit | MIDI 2.0 Channel Voice | Higher-resolution note/cc/etc. — 32-bit data, 16-bit attributes |
| 0x5 | 128-bit | Data Message (128-bit) | SysEx 8-bit, Mixed Data Set |
| 0x6-0xC | — | Reserved | |
| 0xD | 128-bit | Flex Data | Song position metadata, tempo, metadata strings |
| 0xE | — | Reserved | |
| 0xF | 128-bit | UMP Stream | Endpoint Discovery, Function Block Info, Stream Configuration |

## MIDI 2.0 Channel Voice (MT=0x4)

| Status | Name | Data fields |
|---|---|---|
| 0x0 | Registered Per-Note Controller | note, index, 32-bit data |
| 0x1 | Assignable Per-Note Controller | note, index, 32-bit data |
| 0x2 | Registered Controller (RPN) | bank, index, 32-bit data |
| 0x3 | Assignable Controller (NRPN) | bank, index, 32-bit data |
| 0x4 | Relative Registered Controller | bank, index, signed 32-bit delta |
| 0x5 | Relative Assignable Controller | bank, index, signed 32-bit delta |
| 0x6 | Per-Note Pitch Bend | note, 32-bit unsigned |
| 0x8 | Note Off | note, attribute type, 16-bit velocity, 16-bit attribute data |
| 0x9 | Note On | note, attribute type, 16-bit velocity, 16-bit attribute data |
| 0xA | Poly Pressure | note, 32-bit pressure |
| 0xB | Control Change (CC) | index, 32-bit value |
| 0xC | Program Change | 16-bit options, program# + bank MSB/LSB |
| 0xD | Channel Pressure | 32-bit pressure |
| 0xE | Pitch Bend | 32-bit signed |
| 0xF | Per-Note Management | note, flags |

Velocity in 2.0 is **16-bit (0..65535)** not 7-bit. A 0 Note On is still "note off" by convention if the transmitter chooses, but 2.0 introduces **explicit** note-off with velocity.

## Utility / Jitter Reduction (MT=0x0)

| Status | Name |
|---|---|
| 0x0 | NOOP |
| 0x1 | JR Clock (14-bit sender tick) |
| 0x2 | JR Timestamp |
| 0x3 | Delta Clockstamp Ticks Per Quarter Note |
| 0x4 | Delta Clockstamp |

## MIDI-CI (runs over MIDI 1.0 sysex, not UMP)

Universal Non-Real-Time SysEx `F0 7E <dest> 0D <subID2> ...`:

| subID2 | Purpose |
|---|---|
| 0x70 | Discovery Inquiry |
| 0x71 | Discovery Reply |
| 0x10 | Protocol Negotiation Initiate |
| 0x11 | Protocol Negotiation Reply |
| 0x12 | Set New Protocol |
| 0x20 | Profile Configuration Inquiry / Reply |
| 0x21-0x2F | Profile-on / Profile-off / Profile-specific |
| 0x30-0x3F | Property Exchange (Get, Reply, Set, Subscribe) |
| 0x7F | CI NAK |

MIDI-CI MUIDs are 28-bit random endpoint IDs.

## Sources

- midi.org/specs (public index)
- midi.org/midi-2-0 (public overview)
- Full MIDI 2.0 protocol specs (UMP + MIDI-CI + CA-033 bitstream) are login-gated at **midi.org/join-now** — register for a free membership to download the PDFs.
