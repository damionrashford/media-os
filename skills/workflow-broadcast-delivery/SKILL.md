---
name: workflow-broadcast-delivery
description: Produce broadcast-grade MXF OP1a or Netflix IMF masters with HDR dynamic metadata (Dolby Vision / HDR10+), SDI capture/playout, ACES color management, CEA-608/708 captions, and timecode-accurate delivery. Use when the user says "deliver to broadcast", "make an IMF for Netflix", "MXF OP1a", "SDI ingest", "Dolby Vision profile 8.1", "convert DV profile 7 to 8.1", "broadcast master", or anything about professional broadcast/OTT mastering.
argument-hint: [source]
---

# Workflow — Broadcast Delivery

**What:** Turn a source master into a broadcast-spec or OTT-spec deliverable — MXF OP1a for traditional broadcast, IMF (J2K + XML CPL/PKL/ASSETMAP) for Netflix/Amazon, with HDR dynamic metadata preserved and captions intact.

## Skills used

`decklink-tools`, `decklink-docs`, `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-ivtc`, `ffmpeg-hdr-color`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `hdr-dynmeta-docs`, `ffmpeg-ocio-colorpro`, `vfx-oiio`, `vfx-openexr`, `ffmpeg-captions`, `ffmpeg-mxf-imf`, `ffmpeg-quality`, `media-cloud-upload`.

## Pipeline

### Step 1 — SDI ingest (if tape source)

Use `decklink-tools` with `-f decklink`, explicit format code (`Hp50`, `Hi59`, `2k24`), `-pixel_format uyvy422` (or `yuv422p10le` on 10-bit-capable devices). Encode to ProRes 422 HQ + PCM 24-bit 48 kHz working master.

### Step 2 — Probe the source

Use `ffmpeg-probe` and `media-mediainfo`. Capture: exact frame rate (numerator/denominator), interlace/progressive, pix_fmt, bit depth, chroma subsampling, color primaries/transfer/matrix/range, audio channel layout, caption track(s), starting timecode, drop-frame flag.

### Step 3 — Inverse telecine if needed

If 29.97i is telecined film, use `ffmpeg-ivtc` — `fieldmatch → decimate` in that exact order — to recover 23.976p.

### Step 4 — HDR dynamic metadata

- **Dolby Vision** — `hdr-dovi-tool`. Extract RPU (`extract-rpu`), convert profile 7 → 8.1 for OTT (`convert --mode 2`), re-inject into the final encode (`inject-rpu`).
- **HDR10+** — `hdr-hdr10plus-tool`. Extract JSON (`extract`), optionally edit scene metadata, inject back (`inject`).

Never transcode while trying to preserve DoVi/HDR10+ inline — the SEI NAL units get stripped. Extract → encode fresh → re-inject.

### Step 5 — Color-managed ACES pass (optional)

Use `ffmpeg-ocio-colorpro` for OCIO-config-driven ACES transforms. For EXR sources, conform through `vfx-oiio` → `vfx-openexr` first.

### Step 6 — Preserve CEA-608/708 captions

Use `ffmpeg-captions`. Extract with `-c:s copy` or `copy-cc`. Re-inject through the transcode. Naive `-c copy` often drops captions.

### Step 7 — Author MXF OP1a (broadcast)

Use `ffmpeg-mxf-imf`. Spec: `mpeg2video` or XAVC / DNxHR / ProRes depending on house spec, `yuv422p`, 50 M bitrate typical, PCM audio, starting timecode `01:00:00:00` (broadcast convention).

### Step 8 — Author Netflix IMF (OTT master)

Use `ffmpeg-mxf-imf` with J2K encoding, PCM 24-bit 48 kHz 8-ch, emit CPL XML + PKL + ASSETMAP. Validate with Photon (Netflix's open-source IMF validator).

### Step 9 — QC

Run `ffmpeg-quality` (VMAF vs source) and a deep `media-mediainfo` report. Compare to the delivery spec sheet.

### Step 10 — Deliver

Aspera for Netflix, S3 / rclone for general broadcast, both via `media-cloud-upload`.

## Variants

- **Dolby Vision single-layer (profile 8.1)** — OTT streaming. Convert profile 7 → 8.1 via `hdr-dovi-tool`.
- **HDR10+ parallel DoVi** — some delivery specs want both tracks. Extract + inject independently.
- **Archival MXF OP-Atom** — some Avid workflows; each essence track is a separate file (`-f mxf_opatom`).
- **EXR → IMF conform** — VFX-origin sources go through `vfx-openexr` → OIIO → J2K encode.

## Gotchas

- **MXF OP1a vs OP-Atom are different.** OP1a = interleaved single file (broadcast). OP-Atom = one file per essence track (some Avid). Wrong target rejected on ingest.
- **IMF requires JPEG 2000, not H.264.** Netflix spec: lossless or near-lossless J2K.
- **IMF audio must be PCM 24-bit 48 kHz**, 8-track interleaved (or 5.1+2.0+2.0 config). No AAC.
- **IMF CPL is signed XML. UUIDs must be deterministic.** Validate with Photon.
- **Dolby Vision profile matters.** 5 = mobile, 7 = BD dual-layer, 8.1 = OTT single-layer. OTT rejects profile 7.
- **Dolby Vision RPU lives in HEVC SEI NAL units.** Any re-encode without explicit re-injection strips it. Use `-c:v copy` where possible; otherwise extract → encode → inject.
- **HDR10+ in SEI 0x4 (ITU-T T.35)** — same preservation constraint as DoVi.
- **HEVC `-x265-params master-display` unit is 0.00002 for chromaticity and 0.0001 for luminance.** Wrong units = invalid SEI.
- **PQ (`smpte2084`) and HLG (`arib-std-b67`) are incompatible transfer curves.** Do not mix without the `zscale=t=linear→format=gbrpf32le` sandwich.
- **BT.2020 Non-Constant Luminance (`bt2020nc`) is the default.** `bt2020c` (Constant Luminance) is rarely correct.
- **Interlaced flags: `-flags +ilme+ildct` plus `-top 1` (TFF) or `-top 0` (BFF).** Wrong field order produces a zipper pattern every frame.
- **Broadcast timecode convention: starting `01:00:00:00` (1 h pre-roll).** Archives often use `00:00:00:00`.
- **MXF timecode base is independent of video frame rate.** 23.976p uses 24 fps timecode DF=0; 29.97p uses DF=1.
- **CEA-608 survives TS → MP4 only with `-c:s mov_text` or an explicit SCC sidecar.** Naive `-c copy` drops captions.
- **SCC timing is frame-accurate at 29.97 DF.** Converting 29.97 → 23.976 invalidates SCC timing — regenerate.
- **ProRes profiles are 0-indexed:** 0=Proxy, 1=LT, 2=422, 3=HQ, 4=4444, 5=4444 XQ.
- **J2K encoding is CPU-heavy** (1–2 frames/sec/core). Budget hours for 4K IMF.
- **Netflix IMF DV delivery uses an XML sidecar**, not inline RPU.
- **DeckLink format codes are 4-letter** (`Hp50` = 1920×1080p50, `Hi59` = 1080i59.94, `2k24` = 2K 24p).

## Example — SDI ingest → Dolby Vision profile 8.1 IMF

`decklink-tools` captures the tape to ProRes 422 HQ master. `ffmpeg-probe` confirms Rec.2020 PQ. `hdr-dovi-tool` extracts RPU profile 7 and converts to 8.1. `ffmpeg-mxf-imf` encodes J2K IMF with captions and PCM audio. `hdr-dovi-tool inject-rpu` adds the 8.1 track. Photon validates. `media-cloud-upload` Asperas to Netflix.

## Related

- `workflow-hdr` — HDR color-pipeline details (PQ↔HLG, ACES, tone mapping).
- `workflow-vfx-pipeline` — EXR / OIIO feeding the delivery master.
- `workflow-analysis-quality` — VMAF + MediaInfo QC gate.
