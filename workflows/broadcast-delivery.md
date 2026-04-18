# Broadcast Delivery Workflow

**What:** Produce broadcast-grade masters with HDR dynamic metadata, broadcast captions, professional SDI I/O, and deliver as MXF OP1a or Netflix IMF.

**Who:** Post houses, sports broadcasters, streaming platforms requiring IMF, theatrical distribution, Netflix/Disney+/Apple TV+ deliverables.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| SDI I/O | `decklink-tools`, `decklink-docs` | Blackmagic Duo 2 / Quad / 8K Pro capture + playout |
| Source analysis | `ffmpeg-probe`, `media-mediainfo` | Verify source specs, HDR metadata, cadence |
| Inverse telecine | `ffmpeg-ivtc` | 29.97i telecined → 23.976p film |
| HDR tone-mapping | `ffmpeg-hdr-color` | HDR10 / HDR10+ / HLG / Dolby Vision → SDR |
| HDR dynamic metadata | `hdr-dovi-tool`, `hdr-hdr10plus-tool` | RPU extract/inject, profile 7 → 8.1, HDR10+ JSON |
| HDR spec reference | `hdr-dynmeta-docs` | SMPTE 2094 |
| Color-managed pipeline | `ffmpeg-ocio-colorpro`, `vfx-oiio` | ACES + OCIO |
| Broadcast captions | `ffmpeg-captions` | CEA-608 / 708 / SCC / MCC preservation |
| MXF / IMF authoring | `ffmpeg-mxf-imf` | OP1a, IMF CPL |
| Quality QC | `ffmpeg-quality` | VMAF / PSNR / SSIM for master QC |
| Delivery platforms | `media-cloud-upload` | Aspera, Signiant, S3 |
| Deep EXR / OIIO | `vfx-openexr`, `vfx-oiio` | VFX conform |

---

## The pipeline

### 1. Ingest from SDI (live or tape)

```bash
# List DeckLink devices
uv run .claude/skills/decklink-tools/scripts/decklinkctl.py list-devices

# Capture from DeckLink Duo 2 input 1
ffmpeg -f decklink -video_input sdi -audio_input embedded \
  -format_code "Hp50" \
  -i "DeckLink Duo 2 (1)" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -c:a pcm_s24le \
  -timecode 00:00:00:00 \
  master.mov
```

Where `Hp50` = 1920x1080p50. List codes:
```bash
ffmpeg -f decklink -list_formats 1 -i "DeckLink Duo 2 (1)"
```

### 2. Probe source specs

```bash
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full master.mov
uv run .claude/skills/media-mediainfo/scripts/miinfo.py deep master.mov
```

Verify: resolution, frame rate (exact: 23.976 / 24 / 25 / 29.97 / 50 / 59.94), scan type (interlaced vs progressive), codec, bit depth, chroma subsampling (4:2:0 / 4:2:2 / 4:4:4), color primaries, transfer characteristics (BT.709 / BT.2020 / PQ / HLG), matrix, color range (limited vs full), audio channel layout (PCM 24-bit 48kHz for broadcast), embedded captions, timecode.

### 3. Inverse telecine (if needed)

If source is 29.97i telecined film, reverse to 23.976p:

```bash
uv run .claude/skills/ffmpeg-ivtc/scripts/ivtc.py detect master.mov
uv run .claude/skills/ffmpeg-ivtc/scripts/ivtc.py apply \
  --input master.mov --output master-film.mov \
  --method fieldmatch-decimate
```

Under the hood: `fieldmatch,decimate` — *never* swap the order. `decimate` without `fieldmatch` first produces motion juddering.

### 4. HDR dynamic metadata handling

**Dolby Vision profile 7 to 8.1 (streaming-friendly):**

```bash
# Extract RPU
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py extract \
  --input master-dovi-p7.hevc --output rpu-p7.bin

# Convert profile 7 → 8.1 (enhancement layer → single-layer)
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py convert \
  --input rpu-p7.bin --output rpu-p8.bin --target-profile 8.1

# Inject into HEVC
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video master.hevc --rpu rpu-p8.bin --output master-p8.hevc
```

**HDR10+ metadata:**

```bash
# Extract from source (if already has HDR10+)
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py extract \
  --input master.hevc --output hdr10plus.json

# Edit JSON to taste (per-scene brightness, etc.)
# Then reinject:
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py inject \
  --video master.hevc --json hdr10plus.json --output master-hdr10p.hevc
```

Consult the spec reference:
```bash
uv run .claude/skills/hdr-dynmeta-docs/scripts/hdrmetadocs.py search \
  --query "ST2094-40" --page smpte
```

### 5. Color-managed ACES pass

For ACES-centric post houses, run the OCIO pipeline:

```bash
export OCIO=/path/to/aces/config.ocio
ffmpeg -i master.mov \
  -vf "ocio=colorspace_in=ACES - ACEScg:colorspace_out=Output - Rec.709" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  master-rec709.mov
```

Helper:
```bash
uv run .claude/skills/ffmpeg-ocio-colorpro/scripts/ociogo.py transform \
  --input master.mov --output master-rec709.mov \
  --config /path/to/aces/config.ocio \
  --from "ACES - ACEScg" --to "Output - Rec.709"
```

For VFX conform from EXR:
```bash
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "frames/%04d.exr" --output master.mov \
  --colorspace-in "ACES - ACEScg" --colorspace-out "Output - Rec.709" \
  --compression prores --quality 422HQ
```

### 6. Preserve broadcast captions

CEA-608/708 must survive every transcode. Use `copy-cc` or the `-c:s copy` path:

```bash
uv run .claude/skills/ffmpeg-captions/scripts/captions.py extract \
  --input master.mov --output captions.scc --type 608

# And preserve through transcode:
ffmpeg -i master.mov -c copy -c:s copy master-preserved.mov
```

Or convert between SCC / MCC / SRT:
```bash
uv run .claude/skills/ffmpeg-captions/scripts/captions.py convert \
  --input captions.scc --output captions.mcc
```

### 7. Author MXF OP1a

Broadcast delivery standard:

```bash
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py mxf-op1a \
  --input master.mov \
  --output master.mxf \
  --video-codec xdcam_hd422 \
  --audio-pcm-tracks 4 \
  --timecode 01:00:00:00
```

Under the hood:
```bash
ffmpeg -i master.mov \
  -c:v mpeg2video -pix_fmt yuv422p -b:v 50M -flags +ilme+ildct \
  -c:a pcm_s24le -f mxf_opatom master.mxf
```

### 8. Author Netflix IMF delivery

IMF = Interoperable Master Format (SMPTE 2067). Files are MXF, assembly is CPL XML.

```bash
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py imf \
  --video master.mov \
  --output-dir IMF/ \
  --cpl-title "ShowName_S01E01" \
  --image-codec j2k \
  --audio-pcm-tracks 8 \
  --dolby-e-passthrough
```

Creates:
- `VIDEO.mxf` — J2K (JPEG 2000) video essence
- `AUDIO.mxf` — PCM 24-bit 48kHz
- `CPL_*.xml` — Composition Playlist
- `PKL_*.xml` — Packaging List
- `ASSETMAP.xml` / `VOLINDEX.xml`

Verify with Netflix's Photon validator (external — not bundled):
```
java -jar photon.jar IMF/
```

### 9. QC the master

```bash
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference source.mov --distorted master.mxf --json
```

Full QC report via MediaInfo:
```bash
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file master.mxf --format json
```

### 10. Deliver

```bash
# Aspera
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py aspera \
  --target faspex.netflix.com --file master.mxf

# S3 for general broadcast
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --bucket broadcast-masters --prefix show/episode/ --file master.mxf
```

---

## Variants

### Dolby Vision single-layer (Profile 8.1) delivery

Most OTT platforms require profile 8.1, not 7. If source is profile 7:

```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py convert \
  --input rpu-p7.bin --output rpu-p8.bin --target-profile 8.1
```

Re-mux with the new RPU into HEVC, then into MXF.

### HDR10 static metadata only

When distributor doesn't support HDR10+ or DoVi:

```bash
ffmpeg -i master-hdr10p.mov \
  -c:v copy \
  -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc \
  -x265-params "hdr-opt=1:repeat-headers=1:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400" \
  master-hdr10.mov
```

### Full archival master (TIFF / DPX sequence)

For long-term archive, convert to DPX:

```bash
ffmpeg -i master.mov frames/%07d.dpx
```

Or preserve as ProRes 4444 XQ:

```bash
ffmpeg -i master.mov -c:v prores_ks -profile:v 5 -pix_fmt yuv444p12le master-xq.mov
```

### Playout to SDI monitor for QC

```bash
ffmpeg -i master.mov -f decklink \
  -pix_fmt uyvy422 -s 1920x1080 -r 29.97 \
  "DeckLink Duo 2 (2)"
```

### Multi-territory localization

Drop in localized audio + sub tracks before MXF:

```bash
ffmpeg -i video.mov -i audio-eng.wav -i audio-spa.wav \
  -i subs-eng.srt -i subs-spa.srt \
  -map 0:v -map 1:a -map 2:a -map 3:s -map 4:s \
  -metadata:s:a:0 language=eng \
  -metadata:s:a:1 language=spa \
  -metadata:s:s:0 language=eng \
  -metadata:s:s:1 language=spa \
  -c copy master-mx.mov
```

---

## Gotchas

- **MXF OP1a vs OP-Atom.** OP1a = interleaved single file (most broadcast). OP-Atom = separate essence files with single-frame wrapping (some Avid workflows). Wrong one = rejected delivery.
- **IMF requires J2K, not H.264.** Netflix spec: lossless or near-lossless JPEG 2000 (XYZ color space for theatrical, Rec.709 or Rec.2020 for OTT).
- **IMF audio must be PCM 24-bit 48kHz, 8-track interleaved (or 5.1+2.0+2.0 configurations).** Dolby E can be passed through as PCM. No AAC.
- **IMF CPL is XML and signed** — timecode addresses are hh:mm:ss:ff format, and UUIDs must be deterministic. Use Photon for validation.
- **Dolby Vision profile 5 is for mobile encoding, profile 7 is dual-layer for Blu-ray, profile 8.1 is single-layer for streaming.** OTT platforms reject profile 7.
- **Dolby Vision RPU is carried in SEI NAL units inside HEVC.** Stripping NALs during transcode removes DoVi. Use `-c:v copy` when possible; if re-encoding, inject the RPU afterward.
- **HDR10+ metadata is in SEI 0x4 (ITU-T T.35).** Same preservation constraint as DoVi.
- **HEVC `-x265-params master-display` takes units of 0.00002 for chromaticity, 0.0001 for luminance.** Getting this wrong silently writes invalid SEI.
- **Color transfer `smpte2084` (PQ) vs `arib-std-b67` (HLG)** — different flags, different tone curves. Do not mix.
- **BT.2020 Non-Constant Luminance (`bt2020nc`) vs Constant Luminance (`bt2020c`)** — almost all content is NCL. CL is a BT.2020 feature rarely used.
- **Interlaced flags: `-flags +ilme+ildct` plus `-top 1` (TFF) or `-top 0` (BFF)** — getting field order wrong causes zipper-patterned playback.
- **`-timecode 01:00:00:00` start at 1h is the broadcast convention** (first hour is bars/slate/countdown). `00:00:00:00` is for archives.
- **DeckLink format codes are 4-letter.** `Hp50` = 1920x1080p50. `Hi59` = 1080i59.94. `2k24` = 2K 24p. See the ffmpeg-devices docs.
- **ffmpeg DeckLink capture supports 10-bit** via `-pix_fmt yuv422p10le` — but only for v210-capable devices. Duo 2 supports it; older Mini Monitor doesn't.
- **MXF timecode base is separate from video frame rate.** 23.976p content uses 24fps timecode with DF=0 (non-drop-frame). 29.97p uses DF=1 (drop-frame). Mismatches cause sync drift.
- **CEA-608 survives TS → MP4 only if you use `-c:s mov_text` or explicit SCC sidecar.** Naive `-c copy` drops captions when changing container.
- **SCC captions are frame-accurate at 29.97 drop-frame** by definition. Converting 29.97 → 23.976 invalidates SCC timing. Convert to 23.976-native format (MCC v2) or re-time.
- **`prores_ks` vs `prores_aw` vs `prores_videotoolbox`.** `_ks` (Kostya's) is cross-platform and most feature-complete. `_videotoolbox` is macOS-only hardware. `_aw` is legacy.
- **ProRes profiles: 0=Proxy, 1=LT, 2=422, 3=HQ, 4=4444, 5=4444 XQ.** Not 1-indexed.
- **J2K (JPEG 2000) encoding is CPU-heavy.** Budget 1-2 frames/sec/core. Use `-threads 0` and expect long wall-clock times for 4K IMF.
- **Netflix IMF delivery requires Dolby Vision XML sidecar** for DV tracks, not inline RPU. Different workflow than streaming.

---

## Example — "SDI tape → ACES color → IMF delivery with HDR10+ and DoVi"

```bash
#!/usr/bin/env bash
set -e

SOURCE_MOV="master.mov"
RPU_P7="rpu-p7.bin"
RPU_P8="rpu-p8.bin"
HDR10P_JSON="hdr10plus.json"
IMF_DIR="IMF_delivery"

# 1. Probe
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$SOURCE_MOV"

# 2. Extract + convert DoVi RPU
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py extract \
  --input "$SOURCE_MOV" --output "$RPU_P7"
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py convert \
  --input "$RPU_P7" --output "$RPU_P8" --target-profile 8.1

# 3. Extract HDR10+
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py extract \
  --input "$SOURCE_MOV" --output "$HDR10P_JSON"

# 4. ACES color pass through OCIO
export OCIO="$HOME/ACES/config.ocio"
uv run .claude/skills/ffmpeg-ocio-colorpro/scripts/ociogo.py transform \
  --input "$SOURCE_MOV" --output master-rec2020.mov \
  --from "ACES - ACEScg" --to "Output - Rec.2020 ST2084"

# 5. Re-inject HDR metadata
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video master-rec2020.mov --rpu "$RPU_P8" --output master-with-dovi.mov
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py inject \
  --video master-with-dovi.mov --json "$HDR10P_JSON" --output master-all-hdr.mov

# 6. Author IMF
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py imf \
  --video master-all-hdr.mov \
  --output-dir "$IMF_DIR" \
  --cpl-title "ShowName_S01E01_HDR" \
  --image-codec j2k \
  --audio-pcm-tracks 8

# 7. Validate (external)
java -jar ~/tools/photon.jar "$IMF_DIR"

# 8. Deliver
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py aspera \
  --target faspex.netflix.com --dir "$IMF_DIR"
```

---

## Further reading

- [`hdr-workflows.md`](hdr-workflows.md) — HDR deep-dive: PQ / HLG / DoVi / HDR10+
- [`editorial-interchange.md`](editorial-interchange.md) — bringing the master back from NLEs
- [`vfx-pipeline.md`](vfx-pipeline.md) — VFX conform into the broadcast master
- [`analysis-quality.md`](analysis-quality.md) — QC and metric validation
