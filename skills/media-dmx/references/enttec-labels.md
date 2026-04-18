# Enttec USB Pro serial framing

All communication with an Enttec DMX USB Pro (and Pro Mk2) uses a framed packet:

```
+-----+-------+-------------------+---------+-----+
| SOM | Label | Length LE (2 B)   | Data... | EOM |
| 7E  | (1 B) | 0..600            | N B     | E7  |
+-----+-------+-------------------+---------+-----+
```

- `SOM` = `0x7E`, `EOM` = `0xE7`.
- `Length` is little-endian (LSB, MSB).
- `Label` determines the message semantics (see table).
- Non-Pro "Open DMX" USB widgets have NO framing — they are raw UART at 250 kbps.

## Labels

| Label (dec) | Label (hex) | Direction | Name | Notes |
|---|---|---|---|---|
| 1 | 0x01 | in | Reprogram Firmware Request | firmware loader |
| 2 | 0x02 | in | Program Flash Page Request | |
| 3 | 0x03 | out (reply) | Get Widget Parameters Reply | returns struct |
| 3 | 0x03 | in | Set Widget Parameters Request | break time, etc. |
| 4 | 0x04 | in | Received DMX Packet | widget → host |
| 5 | 0x05 | in | Received DMX Changed | widget → host, change-only |
| 6 | 0x06 | out | Output Only Send DMX | host → widget; data starts with start code (0x00) |
| 7 | 0x07 | out | Send DMX RDM | for RDM |
| 8 | 0x08 | out | Receive DMX on Change | request |
| 9 | 0x09 | in | Received DMX Change Of State | |
| 10 | 0x0A | out | Get Widget Serial Number Request | |
| 10 | 0x0A | in | Get Widget Serial Number Reply | 4 bytes LE |
| 11 | 0x0B | out | Send RDM Discovery Request | |
| 12 | 0x0C | in | RDM Timeout | |

## Example: send a DMX frame with 3 slots (R=255, G=128, B=0)

```
7E   06   04 00   00  FF 80 00   E7
SOM  lbl  len-LE  SC  slots      EOM
```

Notes:

- The first byte of data is the **start code** (0x00 for dimmer).
- Length covers everything between length field and EOM: `1 (start code) + N (slots)`.
- For empty DMX (break-test) send one byte: start code only.

## Get widget params reply layout (Label 0x03 in)

```
0: Firmware Version LSB
1: Firmware Version MSB
2: Break Time (microseconds / 10.67)
3: MAB Time (microseconds / 10.67)
4: Output Rate (packets per second)
5..N: User-config bytes
```

## Sources

- Enttec DMX USB Pro API: https://dol2kh495zr52.cloudfront.net/pdf/misc/dmx_usb_pro_api_spec.pdf
- OLA driver source (authoritative): https://github.com/OpenLightingProject/ola/tree/master/plugins/usbdmx
