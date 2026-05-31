---
name: media-control
description: >
  Use when controlling MIDI, OSC, or DMX stage lighting from the CLI: send MIDI notes/CCs/program-changes/sysex, route a control surface to a DAW (Ableton/Logic/Reaper/MainStage), parse or author .mid SMF files, work with MIDI 2.0 UMP packets or MIDI-CI; send or dump OSC messages and bundles with NTP timetags over UDP/TCP-SLIP, bridge to SuperCollider/TouchDesigner/Max/Resolume/QLab; drive stage lights via DMX512-A, Art-Net 4 (UDP 6454), or sACN/E1.31 (multicast 5568), discover RDM devices, stream/record a show, run OLA (olad/ola_streaming_client) or a pure-Python sACN sender, frame Enttec USB Pro. Also use to bridge MIDI/OSC/DMX for show-control and live-event automation.
argument-hint: "[action]"
---

# Media Control

Wire-level real-time control protocols for live shows and media automation: MIDI 1.0/2.0, OSC, and DMX512 lighting. CLI layer — not a DAW or lighting console. The three protocols bridge cleanly into each other for show-control rigs.

## When to use

- Trigger MIDI notes/CCs/program changes/sysex from a script; route a control surface to a DAW; parse or author `.mid` SMF files; work with MIDI 2.0 UMP or MIDI-CI.
- Send or dump OSC messages and bundles over UDP/TCP; control SuperCollider, TouchDesigner, Max, Resolume, QLab.
- Drive stage lights over DMX512-A, Art-Net 4, or sACN/E1.31; discover RDM fixtures; stream or record a show via OLA or a pure-Python sACN sender.
- Bridge MIDI ↔ OSC ↔ DMX for show-control and live-event automation.

## Techniques

- Read `references/midi.md` when sending MIDI, routing a control surface, parsing/authoring SMF, or working with UMP/MIDI-CI. Helper: `scripts/midictl.py`.
- Read `references/osc.md` when sending/dumping OSC, building bundles with timetags, or controlling an OSC app over UDP/TCP-SLIP. Helper: `scripts/oscctl.py`.
- Read `references/dmx.md` when driving DMX512/Art-Net/sACN lighting, discovering RDM, or streaming/recording a show. Helper: `scripts/dmxctl.py`.
- Read `references/cc-table.md` for the full MIDI 1.0 CC number table; `references/ump-packets.md` for MIDI 2.0 UMP type/status codes.
- Read `references/osc-types.md` for the OSC type-tag table, address-pattern grammar, SLIP escaping, NTP math.
- Read `references/wire-format.md` for byte-exact DMX/Art-Net/sACN/RDM packet diagrams; `references/enttec-labels.md` for the USB Pro label table.

## Gotchas

- **MIDI 2.0 UMP ≠ MIDI 1.0.** UMP is 32/64/96/128-bit packets, 16 groups × 16 channels; Type 0x2 (MIDI 1.0 CV in UMP) ≠ Type 0x4 (MIDI 2.0 CV). MIDI-CI discovery/negotiation runs over MIDI 1.0 sysex, not UMP. Channels are 1-indexed in UIs, 0-indexed on the wire.
- **SMF VLQ delta-times are big-endian base-128**, high bit = continuation. Tempo meta-event is microseconds per quarter note (500000 = 120 BPM), not BPM. Never truncate sysex before `F7`.
- **Every OSC string is null-terminated AND padded to a 4-byte multiple**; type tag starts with `,`. NTP epoch is 1900-01-01 (`ntp = unix + 2208988800`). UDP has no retransmit — use TCP+SLIP (OSC 1.1) for guaranteed delivery. Don't reference dead `opensoundcontrol.org`; use `opensoundcontrol.stanford.edu`.
- **sACN multicast address = `239.255.<uni_hi>.<uni_lo>`** (universe 1 → `239.255.0.1`); port 5568. Priority 0 is reserved "ignore" — use 1–200, default 100.
- **Art-Net (UDP 6454) universe is 0-indexed on the wire** (universe 1 = Port-Address 0); start code 0x00 = dimmer data, 0xCC = RDM. Broadcast on 255.255.255.255 may be dropped by managed switches.
- **DMX512 needs a 120 Ω terminator** at the far end (missing → flicker/stuck channels); 250 kbps 8-N-2, ~32 fixtures max per segment. Enttec USB Pro framing: SOM `0x7E` + label + LE length + data + EOM `0xE7`; Open DMX has no framing.
- **`rtmidi-cli`, `artnetify`, `artnet-ctl`, `ArtNetomatic`, `pyOSC`, `oscchief` are not real/current tools** — don't reference them. Real: `sendmidi`/`receivemidi`, `python-rtmidi`, `python-osc`, liblo `oscsend`/`oscdump`, OLA `ola_*` family, PyPI `sacn`.
- **OLA's `olad` daemon must be running** (`brew services start ola` / `systemctl start olad`) for any `ola_*` CLI; the sACN helper needs no OLA.

## Scripts

- `scripts/midictl.py` — list-ports / send / dump / monitor / smf-dump / smf-write. MIDI 1.0+2.0 + SMF.
- `scripts/oscctl.py` — send / dump / ping / bundle. OSC 1.0/1.1 over UDP/TCP.
- `scripts/dmxctl.py` — list-devices / send-dmx / sacn-send / artnet-poll / stream / record / rdm-scan. DMX512/Art-Net/sACN.

All helpers support `--dry-run` and `--verbose`.
