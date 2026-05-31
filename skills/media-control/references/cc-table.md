# MIDI 1.0 Control Change (CC) number table

Status byte: `0xBn` where n = channel (0-15). Followed by CC number (0-127) and value (0-127).

| CC | Name | Notes |
|---|---|---|
| 0 | Bank Select (MSB) | paired with CC 32 LSB |
| 1 | Modulation Wheel (MSB) | LFO depth; LSB at CC 33 |
| 2 | Breath Controller (MSB) | LSB at CC 34 |
| 3 | Undefined | |
| 4 | Foot Controller (MSB) | LSB at CC 36 |
| 5 | Portamento Time (MSB) | LSB at CC 37 |
| 6 | Data Entry (MSB) | for RPN/NRPN; LSB at CC 38 |
| 7 | Channel Volume (MSB) | was "Main Volume"; LSB at CC 39 |
| 8 | Balance (MSB) | LSB at CC 40 |
| 9 | Undefined | |
| 10 | Pan (MSB) | LSB at CC 42 |
| 11 | Expression Controller (MSB) | LSB at CC 43 |
| 12 | Effect Control 1 (MSB) | LSB at CC 44 |
| 13 | Effect Control 2 (MSB) | LSB at CC 45 |
| 14-15 | Undefined | |
| 16 | General Purpose 1 (MSB) | LSB at CC 48 |
| 17 | General Purpose 2 (MSB) | LSB at CC 49 |
| 18 | General Purpose 3 (MSB) | LSB at CC 50 |
| 19 | General Purpose 4 (MSB) | LSB at CC 51 |
| 20-31 | Undefined | |
| 32-63 | LSB of 0-31 | high-resolution pair |
| 64 | Damper Pedal / Sustain | 0-63 off, 64-127 on |
| 65 | Portamento On/Off | |
| 66 | Sostenuto On/Off | |
| 67 | Soft Pedal On/Off | |
| 68 | Legato Footswitch | |
| 69 | Hold 2 | |
| 70 | Sound Controller 1 (Sound Variation) | |
| 71 | Sound Controller 2 (Timbre / Harmonic Intensity / Filter Resonance) | |
| 72 | Sound Controller 3 (Release Time) | |
| 73 | Sound Controller 4 (Attack Time) | |
| 74 | Sound Controller 5 (Brightness / Cutoff) | |
| 75 | Sound Controller 6 (Decay Time) | GM2 |
| 76 | Sound Controller 7 (Vibrato Rate) | GM2 |
| 77 | Sound Controller 8 (Vibrato Depth) | GM2 |
| 78 | Sound Controller 9 (Vibrato Delay) | GM2 |
| 79 | Sound Controller 10 | |
| 80-83 | General Purpose 5-8 | |
| 84 | Portamento Control | |
| 85-87 | Undefined | |
| 88 | High Resolution Velocity Prefix | MIDI 2012 |
| 89-90 | Undefined | |
| 91 | Effects 1 Depth (Reverb) | |
| 92 | Effects 2 Depth (Tremolo) | |
| 93 | Effects 3 Depth (Chorus) | |
| 94 | Effects 4 Depth (Celeste/Detune) | |
| 95 | Effects 5 Depth (Phaser) | |
| 96 | Data Increment | RPN/NRPN |
| 97 | Data Decrement | RPN/NRPN |
| 98 | NRPN LSB | |
| 99 | NRPN MSB | |
| 100 | RPN LSB | |
| 101 | RPN MSB | |
| 102-119 | Undefined | |
| 120 | All Sound Off | value=0 |
| 121 | Reset All Controllers | value=0 |
| 122 | Local Control On/Off | |
| 123 | All Notes Off | value=0 |
| 124 | Omni Mode Off | value=0 |
| 125 | Omni Mode On | value=0 |
| 126 | Mono Mode On | |
| 127 | Poly Mode On | value=0 |

## RPN / NRPN

To write an RPN (Registered Parameter Number):

1. Send CC 101 (RPN MSB) + CC 100 (RPN LSB) to select the parameter.
2. Send CC 6 (Data Entry MSB) [+ optionally CC 38 LSB] with the value.
3. Optionally CC 101=127, CC 100=127 to "deselect" RPN.

Common RPNs:

| MSB LSB | Parameter |
|---|---|
| 00 00 | Pitch Bend Sensitivity (semitones, cents) |
| 00 01 | Channel Fine Tuning |
| 00 02 | Channel Coarse Tuning |
| 00 03 | Tuning Program Select |
| 00 04 | Tuning Bank Select |
| 00 05 | Modulation Depth Range |
| 7F 7F | RPN Null |

NRPN follows the same pattern with CC 99/98.

Spec source: midi.org/midi-1-0 (public summary); full MIDI 2012 spec is login-gated at midi.org.
