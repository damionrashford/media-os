# MXF, IMF, ProRes, XDCAM, SMPTE Timecode — Reference

Load when authoring broadcast or film deliverables, or when the user needs specific codec profiles, operational patterns, or timecode syntax clarified.

## MXF Operational Patterns (SMPTE 377M)

| OP      | ffmpeg muxer    | Typical use                                  |
|---------|-----------------|----------------------------------------------|
| OP1a    | `-f mxf`        | Single-file broadcast exchange (default)     |
| OP-Atom | `-f mxf_opatom` | Avid ingest; IMF essence wrap; 1 essence/file|
| OP1b    | (not native)    | Multiple essences, multiple packages         |
| D-10 / IMX | `-f mxf_d10` | Sony IMX 30/40/50 Mbps I-frame MPEG-2 (SD)  |

Rules of thumb:

- Broadcaster says "MXF" without more context -> OP1a.
- Avid / Media Composer wants OP-Atom (one MXF per video, one per audio channel).
- IMF essence files are OP-Atom; the IMP around them is XML.

## DNxHD / DNxHR Profiles

DNxHD is 1920x1080 only (fixed raster). DNxHR is raster-independent.

| Profile     | ffmpeg `-profile:v` | Bit depth | Chroma | Target bitrate @1080p |
|-------------|---------------------|-----------|--------|-----------------------|
| DNxHR LB    | `dnxhr_lb`          | 8-bit     | 4:2:2  | ~45 Mbps              |
| DNxHR SQ    | `dnxhr_sq`          | 8-bit     | 4:2:2  | ~115 Mbps             |
| DNxHR HQ    | `dnxhr_hq`          | 8-bit     | 4:2:2  | ~175 Mbps             |
| DNxHR HQX   | `dnxhr_hqx`         | 10/12-bit | 4:2:2  | ~175 Mbps             |
| DNxHR 444   | `dnxhr_444`         | 10/12-bit | 4:4:4  | ~350 Mbps             |
| DNxHD 120   | (use `-b:v 120M`)   | 8-bit     | 4:2:2  | 120 Mbps (1080i29.97) |
| DNxHD 185   | (use `-b:v 185M`)   | 8/10-bit  | 4:2:2  | 185 Mbps              |
| DNxHD 440x  | (use `-b:v 440M`)   | 10-bit    | 4:2:2  | 440 Mbps              |

Pick DNxHR for modern 4K workflows; DNxHD for legacy 1080i29.97 broadcast.

## ProRes Profiles (`prores_ks`)

| `-profile:v` | Name          | Chroma  | Bit depth | Approx bitrate 1080p29 |
|--------------|---------------|---------|-----------|------------------------|
| 0            | Proxy         | 4:2:2   | 10-bit    | ~45 Mbps               |
| 1            | LT            | 4:2:2   | 10-bit    | ~100 Mbps              |
| 2            | 422 (Standard)| 4:2:2   | 10-bit    | ~147 Mbps              |
| 3            | 422 HQ        | 4:2:2   | 10-bit    | ~220 Mbps              |
| 4            | 4444          | 4:4:4:4 | 10/12-bit | ~330 Mbps              |
| 5            | 4444 XQ       | 4:4:4:4 | 10/12-bit | ~500 Mbps              |

Vendor tag `-vendor apl0` marks as Apple-authored (some tools check this).

## XDCAM Variants

| Variant       | Codec      | Bitrate          | Chroma | Notes                         |
|---------------|------------|------------------|--------|-------------------------------|
| XDCAM HD      | MPEG-2 LGOP| 18/25/35 Mbps VBR| 4:2:0  | HDV-era                       |
| XDCAM EX      | MPEG-2 LGOP| 35 Mbps VBR      | 4:2:0  | SxS card format               |
| XDCAM HD422   | MPEG-2 LGOP| 50 Mbps CBR      | 4:2:2  | Broadcast delivery standard   |
| XDCAM IMX (D-10)| MPEG-2 I | 30/40/50 Mbps    | 4:2:2  | SD; use `-f mxf_d10`          |

HD422 requires: `-b:v 50M -maxrate 50M -minrate 50M -bufsize 17M`, `yuv422p`, interlace flags for TFF.

## SMPTE Timecode Syntax

| Format           | Separator for frames | When used                       |
|------------------|----------------------|---------------------------------|
| `HH:MM:SS:FF`    | `:` (colon)          | Non-drop-frame (NDF): 23.976, 24, 25, 29.97 NDF, 30, 50, 59.94 NDF, 60 |
| `HH:MM:SS;FF`    | `;` (semicolon)      | Drop-frame (DF): 29.97 DF, 59.94 DF |

- ffmpeg: `-timecode "01:00:00:00"` (NDF) vs `-timecode "01:00:00;00"` (DF).
- Drop-frame **skips** frame numbers 0 and 1 at the start of each minute **except** every 10th minute. Actual duration is identical; only the label changes to keep wall-clock alignment.
- 29.97 NDF is **not** the same as 29.97 DF. A one-hour 29.97 NDF sequence is labeled `00:59:56;12` when measured as DF.
- Embed with `-timecode` on the **output** side; read input TC with `-metadata timecode=...` or probe `stream_tags.timecode`.
- Programs often use `drawtext=timecode=...:timecode_rate=29.97:rate=30000/1001` to burn-in.

## IMF (Interoperable Master Format) — SMPTE ST 2067 Series

IMF is a **package**: MXF essence + XML metadata. ffmpeg writes the essence; it does **not** author the XML.

Key SMPTE ST 2067 parts:

- **ST 2067-2** Core Constraints.
- **ST 2067-3** Composition Playlist (CPL) — XML describing timeline.
- **ST 2067-8** Generic Stream for opaque data.
- **ST 2067-20** Application 2 — JPEG 2000 broadcast profile.
- **ST 2067-21** Application 2E — extended JPEG 2000 (higher bit depth / HDR).
- **ST 2067-40** Application 4 Cinema Mezzanine — ProRes (aka **ProRes IMF**).
- **ST 2067-50** Application 5 ACES.

IMF package files:

- `ASSETMAP.xml` — maps UUIDs to file paths.
- `VOLINDEX.xml` — volume metadata.
- `PKL_*.xml` — Packing List (hashes).
- `CPL_*.xml` — Composition Playlist (timeline).
- `OPL_*.xml` — Output Profile List (optional).
- `*.mxf` — essences (video, audio, subtitles, data).

### Delivery Requirements (public info; always verify current spec)

- **Netflix**: IMF (JPEG 2000 ST 2067-20/21 or ProRes ST 2067-40), timed-text via IMSC1, audio PCM 24-bit 48 kHz. Validate with [Netflix Photon](https://github.com/Netflix/photon).
- **Disney / Apple / Amazon**: each has its own IMF profile variant. Always fetch their current partner spec.
- **Broadcasters** (BBC, NHK, ZDF): often MXF OP1a AS-11 / AS-10 constrained profiles rather than IMF.

### External Tooling (needed for IMF)

| Tool                        | Role                                              |
|-----------------------------|---------------------------------------------------|
| Netflix Photon              | IMF validator (Java). Run before delivery.        |
| asdcplib / asdcp-wrap       | Wraps J2K / PCM into IMF-shaped MXF essence.      |
| asdcp-test                  | Inspects MXF essence.                             |
| IMF Conversion Utility (Netflix) | ProRes/etc. → IMF package.                  |
| Photon-backed CPL builders (OpenCube, IMF Studio, EasyDCP) | Commercial; author CPLs. |
| OpenTimelineIO              | Programmatic CPL read/write (partial).            |

## SMPTE 2022 / 2110 IP Essences (Overview)

- **SMPTE 2022-1/-2**: FEC for MPEG-TS over RTP/UDP (contribution links).
- **SMPTE 2022-6**: Uncompressed HD-SDI over IP (3 Gbps+). Requires patched ffmpeg.
- **SMPTE 2022-7**: Seamless dual-path redundancy.
- **SMPTE 2110-10**: System time / PTP (IEEE 1588) — mandatory for studio sync.
- **SMPTE 2110-20**: Uncompressed video essence (RTP).
- **SMPTE 2110-21**: Traffic-shaping rules.
- **SMPTE 2110-30/-31**: Audio (PCM AES67) / AES3 transparent.
- **SMPTE 2110-40**: Ancillary data (SCTE-104, CEA-608/708 over RTP).

ffmpeg: `-f sdp` to consume a 2110 SDP; requires custom build + a PTP-synced clock on the host. Stock Homebrew ffmpeg typically does **not** support 2110-20 without rebuild.

## DeckLink SDI Capture (Blackmagic)

Requires Blackmagic Desktop Video driver + matching ffmpeg DeckLink build.

```bash
ffmpeg -f decklink -list_devices 1 -i dummy
ffmpeg -f decklink -format_code Hi50 -i "DeckLink Mini Recorder" \
  -c:v dnxhd -b:v 120M -pix_fmt yuv422p \
  -c:a pcm_s24le -ar 48000 \
  -f mxf out.mxf
```

`-format_code` picks the input raster (e.g., `Hi50`, `hp59`, `Hi60`).

## Quick-Reference Gotchas

- OP1a vs OP-Atom: wrong one = silent ingest rejection.
- DF uses `;`; NDF uses `:`. Mixing them breaks editorial conform.
- `setfield=tff` + `-top 1` + `-flags +ildct+ilme` = broadcast TFF output.
- PCM s24le @ 48 kHz is the broadcast audio default.
- HDR in MXF: Dolby Vision RPUs typically need `dovi_tool` post-mux.
- IMF CPL authoring is **not** an ffmpeg capability — use Photon / asdcplib.
- 2110 requires PTP. No PTP = no 2110.
- XDCAM HD422 is CBR 50 Mbps; XDCAM EX is VBR 35 Mbps. Different bitrate rules.
