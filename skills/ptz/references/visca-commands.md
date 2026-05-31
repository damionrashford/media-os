# VISCA command byte table (curated)

The full Sony VISCA Command List is in the paywalled PDFs at `pro.sony`. This
file is a curated excerpt of the commands most commonly needed to drive
Sony BRC/SRG/FR7, PTZOptics, AVer, Panasonic AW-UE, Canon CR-N and compatible
PTZ cameras. Byte sequences here are the serial form; VISCA-over-IP prepends
the 8-byte payload header.

Legend:

- `8x` = address byte `0x80 | camera_addr` (camera addr 1–7).
- `88` = broadcast (all cameras).
- `y0` = reply address `0x80 | (cam_addr << 4)` → `0x90` for cam 1.
- `FF` = terminator.

Every message ends with `FF`. Replies: ACK `y0 4z FF`, Completion `y0 5z FF`
(z = socket), Error `y0 6z ee FF`.

## Command categories

### Camera control (`CAM_`)

```
Power On         8x 01 04 00 02 FF
Power Off        8x 01 04 00 03 FF
Zoom Stop        8x 01 04 07 00 FF
Zoom Tele        8x 01 04 07 02 FF
Zoom Wide        8x 01 04 07 03 FF
Zoom Tele Var    8x 01 04 07 2p FF     (p = speed 0–7)
Zoom Wide Var    8x 01 04 07 3p FF
Zoom Direct      8x 01 04 47 0p 0q 0r 0s FF   (pqrs = position)
Focus Stop       8x 01 04 08 00 FF
Focus Far        8x 01 04 08 02 FF
Focus Near       8x 01 04 08 03 FF
Focus Far Var    8x 01 04 08 2p FF
Focus Near Var   8x 01 04 08 3p FF
Focus Auto       8x 01 04 38 02 FF
Focus Manual     8x 01 04 38 03 FF
Focus One-push   8x 01 04 18 01 FF
WB Auto          8x 01 04 35 00 FF
WB Indoor        8x 01 04 35 01 FF
WB Outdoor       8x 01 04 35 02 FF
WB One-push      8x 01 04 35 03 FF
WB Manual        8x 01 04 35 05 FF
Exposure Full Auto   8x 01 04 39 00 FF
Exposure Manual      8x 01 04 39 03 FF
Exposure Shutter Priority  8x 01 04 39 0A FF
Exposure Iris Priority     8x 01 04 39 0B FF
Exposure Bright            8x 01 04 39 0D FF
IR Cut Filter On     8x 01 04 01 02 FF
IR Cut Filter Off    8x 01 04 01 03 FF
Backlight On         8x 01 04 33 02 FF
Backlight Off        8x 01 04 33 03 FF
Memory Reset (preset)    8x 01 04 3F 00 0p FF    (p = 0–127 or 0–255)
Memory Set (preset)      8x 01 04 3F 01 0p FF
Memory Recall (preset)   8x 01 04 3F 02 0p FF
```

### Pan-Tilt control (`Pan_tiltDrive`)

```
PanTilt Drive    8x 01 06 01 VV WW YY YY ZZ ZZ FF
  VV = pan speed 01–18      WW = tilt speed 01–17
  YY YY = direction pan  (03 = stop, 01 = left,  02 = right)
  ZZ ZZ = direction tilt (03 = stop, 01 = up,    02 = down)
  e.g. Up     = 8x 01 06 01 VV WW 03 01 FF
       Down   = 8x 01 06 01 VV WW 03 02 FF
       Left   = 8x 01 06 01 VV WW 01 03 FF
       Right  = 8x 01 06 01 VV WW 02 03 FF
       UpLeft = 8x 01 06 01 VV WW 01 01 FF
       Stop   = 8x 01 06 01 VV WW 03 03 FF

PanTilt Absolute   8x 01 06 02 VV WW 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF
PanTilt Relative   8x 01 06 03 VV WW 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF
PanTilt Home       8x 01 06 04 FF
PanTilt Reset      8x 01 06 05 FF
PanTilt Limit Set  8x 01 06 07 00 0W 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF
```

### Inquiry (`CAM_*Inq`)

```
Power Inq          8x 09 04 00 FF  -> y0 50 02/03 FF
Zoom Pos Inq       8x 09 04 47 FF  -> y0 50 0p 0q 0r 0s FF
Focus Pos Inq      8x 09 04 48 FF
PanTilt Pos Inq    8x 09 06 12 FF  -> y0 50 0p 0p 0p 0p 0t 0t 0t 0t FF
Version Inq        8x 09 00 02 FF  -> y0 50 GG GG HH HH JJ JJ KK FF
Block Inq Lens     8x 09 7E 7E 00 FF
Block Inq Camera   8x 09 7E 7E 01 FF
```

### VISCA-over-IP payload wrapper

All commands above are wrapped in an 8-byte header:

```
Offset  Field                 Size  Notes
0-1     Payload type          2 B   0x01 0x00 = VISCA command,
                                    0x01 0x10 = VISCA inquiry,
                                    0x01 0x11 = VISCA reply,
                                    0x02 0x00 = VISCA control command,
                                    0x02 0x01 = VISCA control reply
2-3     Payload length        2 B   big-endian, bytes following header
4-7     Sequence number       4 B   big-endian, monotonic
8+      Payload               N B   serial VISCA bytes
```

UDP port **52381**. Sony, PTZOptics, AVer, Bolin, Avonic, Marshall, Lumens,
Canon CR-N all use this exact wrapper.

## Vendor-specific extras

- **PTZOptics** adds `8x 01 04 00 00 FF` for tally control and a set of OSD
  menu navigation commands — see PTZOptics VISCA-over-IP PDF.
- **AVer Pro-AV** extends preset IDs to 0–255 (Sony spec: 0–127).
- **Sony FR7** adds `NDI|HX` network audio commands under mfg code.
- **Panasonic AW-UE** cameras speak AWProtocol HTTP-CGI by default; many
  models accept limited VISCA on UDP:52381 as a secondary interface.

## Sources

- Sony VISCA Command List v2.00 — https://pro.sony/s3/2022/09/14131603/VISCA-Command-List-Version-2.00.pdf
- Sony BRC-H900 ref — https://pro.sony/s3/cms-static-content/uploadfile/59/1237493025759.pdf
- Sony SRG-300H / VISCA-over-IP (AES6 manual) — https://pro.sony/support/res/manuals/AES6/fe573c4d3e5d01ec8d5172b500b32ac1/AES61001M.pdf
- PTZOptics VISCA-over-IP Rev 1.2 — https://ptzoptics.com/wp-content/uploads/2020/11/PTZOptics-VISCA-over-IP-Rev-1_2-8-20.pdf
