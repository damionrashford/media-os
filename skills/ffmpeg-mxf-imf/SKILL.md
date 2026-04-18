---
name: ffmpeg-mxf-imf
description: >
  Professional broadcast and film delivery with ffmpeg: MXF (SMPTE 377M OP1a/OP-Atom) mux/demux, IMF (Interoperable Master Format SMPTE 2067) for Netflix/studio delivery, GXF, broadcast timecode (drop-frame / non-drop-frame), SMPTE 2022 / SMPTE 2110 IP essences, XDCAM profiles. Use when the user asks to work with MXF files, author IMF packages, handle broadcast-exchange containers, deal with SMPTE timecode, read MXF operational patterns, do IMP delivery to Netflix, or do professional post-production mastering.
argument-hint: "[operation]"
---

# ffmpeg-mxf-imf

**Context:** $ARGUMENTS

## Quick start

- **Make an OP1a broadcast MXF (DNxHD/DNxHR):** → Step 3 recipe A.
- **Make an OP-Atom Avid-style MXF (one essence per file):** → Step 3 recipe B.
- **ProRes .mov mezzanine:** → Step 3 recipe C.
- **XDCAM HD422 50 Mbps MXF:** → Step 3 recipe D.
- **Author an IMF package:** cannot be done with ffmpeg alone → Step 3 recipe E.
- **Stamp SMPTE timecode (DF vs NDF):** → Step 3 recipe F.

## When to use

- Broadcast exchange delivery (MXF OP1a to a TV network QC dept).
- Avid ingest / export (MXF OP-Atom).
- Studio / streamer mastering (ProRes mezzanine, IMF delivery).
- Any time the user says "MXF", "IMF", "IMP", "XDCAM", "DNxHD", "ProRes", "SMPTE", "broadcast deliverable", or "Netflix spec".
- Embedding or restamping SMPTE timecode on a mastering track.
- Reading SMPTE 2022 / 2110 IP essences (niche, build-dependent).

## Step 1 — Identify the target spec

Ask / infer:

1. **Container**: MXF OP1a? MXF OP-Atom? MOV (ProRes)? IMF? GXF?
2. **Codec**: DNxHD, DNxHR, XDCAM HD422, ProRes 422 HQ / 4444, JPEG 2000, etc.
3. **Timecode**: drop-frame or non-drop-frame? Starting at `01:00:00:00`?
4. **Audio**: PCM 24-bit 48 kHz is the broadcast default. How many tracks / channels?
5. **Interlacing**: `setfield=tff` for broadcast TFF output?
6. **IMF CPL**: if IMF, ffmpeg alone is not enough — plan for `asdcplib` / `photon`.

## Step 2 — Pick encoder + muxer

| Target                  | Codec                       | Muxer        |
|-------------------------|------------------------------|--------------|
| MXF OP1a broadcast      | `dnxhd` / `dnxhr`            | `-f mxf`     |
| MXF OP-Atom (Avid/IMF)  | `dnxhd` / `dnxhr` / `prores` | `-f mxf_opatom` |
| MXF D-10 IMX            | `mpeg2video` D-10            | `-f mxf_d10` |
| XDCAM HD422             | `mpeg2video` 50 Mb CBR       | `-f mxf`     |
| ProRes mezzanine        | `prores_ks`                  | `-f mov`     |
| GXF (Grass Valley)      | `mpeg2video` / others        | `-f gxf`     |

See `references/formats.md` for full codec profile tables.

## Step 3 — Run

### A. MXF OP1a, DNxHD 120 Mbps, PCM 24-bit (broadcast default)

```bash
ffmpeg -i in.mov \
  -c:v dnxhd -b:v 120M -pix_fmt yuv422p \
  -vf "setfield=tff" \
  -c:a pcm_s24le -ar 48000 \
  -timecode "01:00:00:00" \
  -f mxf out_op1a.mxf
```

For DNxHR (raster-independent successor): `-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p`.

### B. MXF OP-Atom (one essence per file, Avid/IMF style)

```bash
ffmpeg -i in.mov \
  -map 0:v -c:v dnxhd -b:v 120M -pix_fmt yuv422p \
  -f mxf_opatom video.mxf
ffmpeg -i in.mov \
  -map 0:a:0 -c:a pcm_s24le -ar 48000 -f mxf_opatom audio_1.mxf
```

One file per video essence + one file per audio channel. Script `mxf-opatom` does the fan-out.

### C. ProRes 422 HQ mezzanine (most common intermediate)

```bash
ffmpeg -i in.mov \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -vendor apl0 \
  -c:a pcm_s24le \
  out_prores.mov
```

Profile map: 0 Proxy, 1 LT, 2 Standard 422, 3 HQ 422, 4 4444, 5 4444 XQ.

### D. XDCAM HD422 50 Mbps CBR MXF

```bash
ffmpeg -i in.mov \
  -c:v mpeg2video -pix_fmt yuv422p \
  -b:v 50M -maxrate 50M -minrate 50M -bufsize 17M \
  -flags +ildct+ilme -top 1 \
  -c:a pcm_s24le -ar 48000 \
  -f mxf out_xdcam.mxf
```

### E. IMF package (read carefully)

ffmpeg **cannot author an IMF package**. IMF = MXF essence files + **XML CPL (Composition Playlist), PKL, ASSETMAP, OPL, VOLINDEX**. ffmpeg writes the MXF essence (J2K SMPTE ST 2067-20 or ProRes ST 2067-21); CPL authoring requires external tooling:

- **Netflix Photon** (`https://github.com/Netflix/photon`) — validates IMF packages.
- **asdcplib / asdcp-wrap** — creates the J2K MXF essence for IMF.
- **IMF Conversion Utility** (Netflix) — converts ProRes/etc. into IMF.
- **OpenTimelineIO + Tractor** — can stitch CPLs.

Document this limitation; do **not** pretend ffmpeg alone produces an IMP.

### F. Stamp SMPTE timecode

```bash
# Non-drop-frame (24, 25, 30, 50, 60 fps) — use COLON
ffmpeg -i in.mov -c copy -timecode "01:00:00:00" -f mxf out.mxf

# Drop-frame (29.97, 59.94) — use SEMICOLON before frames field
ffmpeg -i in.mov -c copy -timecode "01:00:00;00" -f mxf out.mxf
```

The semicolon vs. colon is load-bearing — it is how ffmpeg selects DF.

## Step 4 — Verify

```bash
ffprobe -v error -show_streams -show_format out.mxf
ffprobe -v error -show_entries format_tags:stream_tags=timecode out.mxf
mediainfo --Output=JSON --Full out.mxf        # deeper: GOP, profile, level
```

Look for: `codec_name`, `pix_fmt`, `r_frame_rate`, `tags.timecode`, MXF Operational Pattern in `mediainfo`. IMF essence should show `JPEG 2000` or `ProRes` with 10-bit 4:2:2+ and a UL identifying SMPTE ST 2067.

## Available scripts

- **`scripts/mxfimf.py`** — subcommands: `mxf-op1a`, `mxf-opatom`, `prores-mov`, `xdcam-hd422`, `set-timecode`, `identify-imf`.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py mxf-op1a \
  --input in.mov --output out.mxf --codec dnxhd --timecode "01:00:00:00"
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py set-timecode \
  --input in.mov --output out.mov --tc "01:00:00;00" --drop-frame
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py identify-imf --input suspect.mxf
```

All subcommands accept `--dry-run` and `--verbose`.

## Reference docs

- Read [`references/formats.md`](references/formats.md) for MXF operational patterns, DNxHD/DNxHR profiles, ProRes profiles, XDCAM variants, timecode syntax, IMF spec refs, Netflix/Disney/Apple delivery notes, external IMF tooling, SMPTE 2022/2110 overview, and DeckLink SDI capture.

## Gotchas

- **MXF Operational Patterns differ.** `-f mxf` = OP1a (single file, broadcast default). `-f mxf_opatom` = OP-Atom (one essence per file, Avid + IMF). `-f mxf_d10` = D-10 / IMX. Confirm which the downstream system requires — mixing them up causes silent ingest rejection.
- **Drop-frame timecode syntax uses SEMICOLON.** `01:00:00;00` = drop-frame. `01:00:00:00` = non-drop-frame. 29.97 fps NDF is **not** the same as 29.97 DF — NDF never skips, DF skips 2 frames every minute except every 10th minute.
- **Interlacing flags**: broadcast TFF needs `-vf setfield=tff` on output, plus `-flags +ildct+ilme -top 1` for MPEG-2. Missing these produces ingest-rejecting files.
- **PCM is standard for MXF audio.** Use `pcm_s24le` at 48 kHz. Don't use AAC in broadcast MXF.
- **OP-Atom = one channel per file.** Each logical audio channel typically becomes its own MXF file. The `mxf-opatom` subcommand fans out automatically.
- **`-mpegts_flags system_b`** for broadcast MPEG-TS compliance.
- **IMF delivery to Netflix** requires specific codec profiles: JPEG 2000 (SMPTE ST 2067-20) or ProRes IMF (SMPTE ST 2067-21). See Netflix Partner Help Center for the current delivery spec; ffmpeg alone cannot author the XML CPL — use Netflix Photon or asdcplib.
- **HDR metadata in MXF** (Dolby Vision RPU, HDR10 static) needs specific handling: mux-time metadata via `-metadata` rarely suffices; Dolby Vision usually requires MP4Box or `dovi_tool` after encode.
- **Timecode source**: input side use `-metadata timecode=HH:MM:SS:FF`, output side use `-timecode` — they are different flags.
- **SMPTE 2110** needs a build with 2110 SDP support plus **PTP / IEEE 1588 network time sync** in production. Most stock ffmpeg builds do not include it.
- **SDI capture** via Blackmagic DeckLink: `-f decklink -i "DeckLink Mini Recorder"`. Requires the Blackmagic Desktop Video driver.
- **MPEG-2 broadcast grade**: add `-mbd rd -trellis 2 -cmp 2 -subcmp 2` for better RD.
- **Never use H.264 Baseline for broadcast** — use Main or High. Baseline lacks B-frames / CABAC and fails most broadcast conformance suites.
- **`_original` suffix on output** means ffmpeg refused to overwrite — pass `-y` to force overwrite.
- **XDCAM EX** has specific GOP and quality ceilings (35 Mbps) different from HD422 (50 Mbps). Do not use HD422 params to target XDCAM EX.

## Examples

### Example 1: OP1a broadcast deliverable with timecode

Input: `master.mov` (ProRes 422 HQ, 29.97 fps, needs DF timecode).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py mxf-op1a \
  --input master.mov --output deliverable.mxf \
  --codec dnxhd --timecode "10:00:00;00"
ffprobe -show_entries stream_tags=timecode deliverable.mxf
```

Result: OP1a MXF with DNxHD 120 Mbps video + PCM 24-bit audio + drop-frame SMPTE timecode starting at 10:00:00;00.

### Example 2: Avid OP-Atom fan-out

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py mxf-opatom \
  --input master.mov --outdir /tmp/opatom --codec dnxhr
```

Produces `video.mxf`, `audio_0.mxf`, `audio_1.mxf`, … one essence per file.

### Example 3: IMF identification

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py identify-imf --input unknown.mxf
```

Reports whether the MXF uses SMPTE ST 2067 descriptors and whether ffmpeg can round-trip it. If IMF, instructs user to fetch the CPL and use Netflix Photon.

## Troubleshooting

### Error: `Could not find tag for codec ... in stream #0, codec not currently supported in container`

Cause: codec/muxer mismatch (e.g., H.264 in `mxf_opatom`, or AAC in MXF).
Solution: MXF wants DNxHD/DNxHR/MPEG-2/JPEG 2000 for video and PCM for audio. Re-encode with a supported codec.

### Error: OP-Atom output has multiple streams

Cause: `mxf_opatom` supports exactly one video or one audio essence per file.
Solution: split with `-map` and produce one MXF per essence. Use the `mxf-opatom` subcommand.

### Timecode shows `00:00:00:00` after mux

Cause: `-timecode` must be on the output side, not input; or input was `-c copy` without the output flag.
Solution: put `-timecode "HH:MM:SS:FF"` as an output option, after `-i`. For DF, use semicolon.

### Broadcaster rejects the file for interlace non-compliance

Cause: missing `setfield=tff` and/or `-top 1`, or wrong field order.
Solution: add `-vf setfield=tff -flags +ildct+ilme -top 1` for TFF broadcast.

### Output MXF has `_original` suffix

Cause: a file with that name already existed and ffmpeg refused to overwrite.
Solution: add `-y` to the ffmpeg command, or delete the existing output first.

### IMF package validation fails in Netflix Photon

Cause: ffmpeg does not author CPLs. You produced the essence but not the XML package.
Solution: use `asdcp-wrap` or the Netflix IMF Conversion Utility to wrap the essence and generate CPL/PKL/ASSETMAP. ffmpeg is only step 1.
