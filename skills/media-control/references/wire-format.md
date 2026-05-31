# DMX / Art-Net / sACN / RDM wire formats

## DMX512-A (ANSI E1.11)

Physical layer: RS-485 differential pair, 250 kbps, 8-N-2.

```
| BREAK (≥88 µs low) | MAB (≥8 µs high) | Start Code (8 bits) | Slot 1..N (8 bits + stop bits each) |
```

- Start code `0x00` = dimmer data (the usual case).
- Start code `0xCC` = RDM (E1.20 bidirectional).
- Up to 512 slots per universe. Max refresh ~44 Hz.
- Max 32 devices per segment before repeater (per spec).

## Art-Net 4 (UDP port 6454)

ASCII header + little-endian OpCode:

```
0: "Art-Net\0"  (8 B)
8: OpCode       (2 B LE)
10: ProtVerHi   (1 B, usually 0)
11: ProtVerLo   (1 B, currently 14)
12+: op-specific
```

OpCodes:

| Name | Hex | Purpose |
|---|---|---|
| OpPoll | 0x2000 | Discovery probe |
| OpPollReply | 0x2100 | Discovery reply |
| OpDmx | 0x5000 | DMX data |
| OpSync | 0x5200 | Frame-synchronous trigger |
| OpAddress | 0x6000 | Reprogramming (name, universe) |
| OpInput | 0x7000 | Input port config |
| OpTodRequest | 0x8000 | RDM discovery request |
| OpTodData | 0x8100 | RDM discovery reply |
| OpTodControl | 0x8200 | RDM discovery control |
| OpRdm | 0x8300 | RDM data |

### OpDmx (0x5000) layout

```
Header (10 B) + Sequence (1 B) + Physical (1 B)
+ SubUni (1 B) + Net (1 B)
+ Length (2 B BE, 0..512)
+ DMX data (Length bytes)
```

Port-Address = `Net(7 bits) + SubNet(4) + Universe(4)` → up to 32768 universes.

### OpPoll (0x2000)

```
Header (10 B) + TalkToMe (1 B) + Priority (1 B)
```

TalkToMe bits: `0x02` = send ArtPollReply on change, `0x04` = diagnostics.

### OpPollReply (0x2100)

Lots of fields; the ones you actually need:

```
14: IP address (4 B)
18: Port (2 B LE, usually 6454)
26: ShortName (18 B, null-term ASCII)
44: LongName (64 B, null-term ASCII)
```

## sACN / E1.31 (UDP multicast, port 5568)

Multicast group for universe U: `239.255.(U>>8).(U&0xFF)`. Universe 1 → `239.255.0.1`.

Packet has three layers — Root + Framing + DMP — all PDU-style:

```
Root Layer (ACN):
  0-1:  Preamble Size = 0x0010
  2-3:  Postamble Size = 0x0000
  4-15: ACN Packet ID = "ASC-E1.17\0\0\0"
  16-17: Flags (0x7 << 12) + Root PDU length
  18-21: Vector = 0x00000004 (E1.31 Data)
  22-37: CID (16-byte UUID)

Framing Layer:
  38-39: Flags + Length
  40-43: Vector = 0x00000002 (E1.31 Data Packet)
  44-107: Source Name (64 B, null-padded)
  108: Priority (1 B, 0-200, default 100)
  109-110: Sync Universe (2 B BE, 0 = no sync)
  111: Sequence Number (1 B, per-universe)
  112: Options (1 B; bit 6 = preview, bit 7 = stream terminated)
  113-114: Universe (2 B BE)

DMP Layer:
  115-116: Flags + Length
  117: Vector = 0x02 (Set Property)
  118: Address & Data Type = 0xA1
  119-120: First Property Address = 0x0000
  121-122: Address Increment = 0x0001
  123-124: Property Value Count = 1 + N (start code + N slots)
  125: Start Code (0x00)
  126..: DMX data (N bytes, typically 512)
```

Priority 0 is reserved (ignore). Multiple sources on the same universe → highest priority wins; tied → merge (HTP or LTP depending on receiver).

## RDM (ANSI E1.20) over DMX

- Uses start code `0xCC`.
- Unique ID = 6 bytes: 2-byte manufacturer ID + 4-byte device ID.
- Discovery uses a binary-search "DUB" (Discovery Unique Branch) protocol.
- PIDs (Parameter IDs) identify settings: `0x0080` DEVICE_INFO, `0x00E0` SOFTWARE_VERSION_LABEL, `0x00F0` DMX_START_ADDRESS, etc.

## Canonical sources

- ANSI E1.11 (DMX512-A): https://tsp.esta.org/tsp/documents/published_docs.php
- ANSI E1.20 (RDM): same index
- ANSI E1.31 (sACN): same index
- Art-Net 4 spec PDF: https://art-net.org.uk/resources/ (captcha-gated direct URL)
- OLA: https://www.openlighting.org/ola/
- OLA man pages: http://docs.openlighting.org/ola/man/
