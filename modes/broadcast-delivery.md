# Mode: broadcast-delivery

**Subagent**: `delivery`
**Trigger phrases**: "broadcast deliver", "MXF master", "IMF package", "ProRes master", "DPP deliver", "AS-11 deliver", "Netflix deliver", "broadcast spec deliver", "deliver for air", "create IMF"
**Output**: `${MEDIA_WORK_DIR}/modes/broadcast-delivery/{date}_{slug}/`
**Approval gate**: required — delivery files are immutable once handed off; operator confirms target spec before encode.

## Inputs

- **Required**:
  - `source` — input master (high-bit-depth, ideally ProRes 4444 / DNxHR HQX / DPX sequence / EXR sequence).
  - `target` — delivery spec: `dpp-as11`, `netflix-imf`, `apple-prores`, `broadcast-imx50`, `xdcam-hd422`, `mxf-op1a`, `imf-application2e`.
- **Optional**:
  - `frame_rate` — explicit override (default: preserve source).
  - `audio_layout` — `5.1`, `5.1+stereo`, `stereo`, `discrete-8-mono`, `dolby-atmos-9.1.6`.
  - `captions` — STL / SCC / SRT / TTML file for muxing.
  - `loudness_target` — `r128` (default), `atsc-a85`, `arib-tr-b32`, `ebu-r128-tv`.

## Steps

1. Read `ffmpeg-broadcast` and `media-inspect`. For loudness: `media-audio-cli`.
2. `moprobe --color --json <source>` plus `mediainfo --Output=JSON <source>` for full metadata extraction.
3. **STOP** if source bit depth or chroma is below target spec (e.g. delivering Netflix IMF requires 10-bit 4:2:2 minimum; 8-bit 4:2:0 source must be re-mastered, not just transcoded). Surface to operator.
4. Look up target spec table (in mode reference below) for exact codec + container + flags:
   - `dpp-as11` → MXF OP1a, AVC-Intra 100, 1080i50, BWF audio, DPP shim metadata.
   - `netflix-imf` → IMF Application 2E, JPEG 2000 IMF, OPL/CPL/PKL XML, IAB/Atmos audio.
   - `apple-prores` → ProRes 422 HQ / 4444 / 4444 XQ in QuickTime MOV.
   - `broadcast-imx50` → MPEG-2 422P@HL, 50 Mbps CBR, MXF OP1a.
   - `xdcam-hd422` → MPEG-2 4:2:2, 50 Mbps CBR, 1080i, MXF OP1a.
5. **Approval gate**: present the resolved target spec to the operator (codec, profile, bitrate, GOP structure, audio config, container, metadata sidecars). Wait for explicit approval before encoding.
6. Compose the ffmpeg command (or J2K + MXF wrap chain for IMF; ProRes single-pass for ProRes targets).
7. **`mosafe`-wrap** the command.
8. Encode. Run `mediainfo` on the output to verify codec/profile/level matches target spec exactly.
9. Run loudness measurement: `ffmpeg-normalize -nt <target> -o <normalized> --print-stats <output>`. Confirm within ±0.5 LU of target.
10. Mux captions if provided (`ffmpeg-subtitle` or MXF-aware tools).
11. Run `moqc` against the source for VMAF baseline (not gate — broadcast specs are about conformance, not perceptual quality).
12. Write `summary.md` with delivery checklist matrix (every spec field: pass/fail).

## Output schema

```markdown
# Broadcast delivery — {slug} — {date}

## Target spec
- **Profile**: {dpp-as11 / netflix-imf / apple-prores / ...}
- **Container**: {MXF OP1a / IMF / QuickTime / ...}
- **Video codec + bitrate**: {AVC-Intra 100 / JPEG 2000 IMF / ProRes 422 HQ / ...}
- **Audio**: {layout, codec, bitrate}
- **Frame rate**: {fps}
- **Captions**: {format or N/A}

## Conformance matrix
| Spec field | Required | Actual | Pass |
|---|---|---|---|
| Video codec | ... | ... | ✓ / ✗ |
| Bitrate | ... | ... | ✓ / ✗ |
| Chroma | ... | ... | ✓ / ✗ |
| Bit depth | ... | ... | ✓ / ✗ |
| Frame rate | ... | ... | ✓ / ✗ |
| Audio layout | ... | ... | ✓ / ✗ |
| Loudness | {target ±0.5 LU} | ... | ✓ / ✗ |
| Captions | ... | ... | ✓ / ✗ |

## VMAF vs source
- **Score**: {N}
- **Note**: broadcast conformance is the gate, not VMAF.

## Files
- **Delivery master**: {path}
- **Sidecars** (IMF only): CPL, PKL, OPL, AssetMap — {paths}
```

## Quality bar

- Every spec field passes the conformance matrix.
- Loudness within ±0.5 LU of target.
- `mediainfo` confirms exact codec/profile/level (not just "MPEG-2 video" — must be `MPEG-2 422P@HL`).
- Captions mux verified by re-probing (subtitle stream present, correct format).
- For IMF: CPL / PKL / OPL / AssetMap XML files all present and validated against IMF schema.
- For MXF: OP1a file structure verified by `mediainfo --Inform="General;%Format_Profile%"`.

## Playbook reference (folded from workflow-broadcast-delivery)

## Pipeline

### Step 1 — SDI ingest (if tape source)

Use `broadcast-io` with `-f decklink`, explicit format code (`Hp50`, `Hi59`, `2k24`), `-pixel_format uyvy422` (or `yuv422p10le` on 10-bit-capable devices). Encode to ProRes 422 HQ + PCM 24-bit 48 kHz working master.

### Step 2 — Probe the source

Use `ffmpeg-analyze` and `media-inspect`. Capture: exact frame rate (numerator/denominator), interlace/progressive, pix_fmt, bit depth, chroma subsampling, color primaries/transfer/matrix/range, audio channel layout, caption track(s), starting timecode, drop-frame flag.

### Step 3 — Inverse telecine if needed

If 29.97i is telecined film, use `ffmpeg-restore` — `fieldmatch → decimate` in that exact order — to recover 23.976p.

### Step 4 — HDR dynamic metadata

- **Dolby Vision** — `hdr-meta`. Extract RPU (`extract-rpu`), convert profile 7 → 8.1 for OTT (`convert --mode 2`), re-inject into the final encode (`inject-rpu`).
- **HDR10+** — `hdr-meta`. Extract JSON (`extract`), optionally edit scene metadata, inject back (`inject`).

Never transcode while trying to preserve DoVi/HDR10+ inline — the SEI NAL units get stripped. Extract → encode fresh → re-inject.

### Step 5 — Color-managed ACES pass (optional)

Use `ffmpeg-color` for OCIO-config-driven ACES transforms. For EXR sources, conform through `vfx` → `vfx` first.

### Step 6 — Preserve CEA-608/708 captions

Use `ffmpeg-subtitle`. Extract with `-c:s copy` or `copy-cc`. Re-inject through the transcode. Naive `-c copy` often drops captions.

### Step 7 — Author MXF OP1a (broadcast)

Use `ffmpeg-broadcast`. Spec: `mpeg2video` or XAVC / DNxHR / ProRes depending on house spec, `yuv422p`, 50 M bitrate typical, PCM audio, starting timecode `01:00:00:00` (broadcast convention).

### Step 8 — Author Netflix IMF (OTT master)

Use `ffmpeg-broadcast` with J2K encoding, PCM 24-bit 48 kHz 8-ch, emit CPL XML + PKL + ASSETMAP. Validate with Photon (Netflix's open-source IMF validator).

### Step 9 — QC

Run `ffmpeg-analyze` (VMAF vs source) and a deep `media-inspect` report. Compare to the delivery spec sheet.

### Step 10 — Deliver

Aspera for Netflix, S3 / rclone for general broadcast, both via `media-cloud-upload`.

## Variants

- **Dolby Vision single-layer (profile 8.1)** — OTT streaming. Convert profile 7 → 8.1 via `hdr-meta`.
- **HDR10+ parallel DoVi** — some delivery specs want both tracks. Extract + inject independently.
- **Archival MXF OP-Atom** — some Avid workflows; each essence track is a separate file (`-f mxf_opatom`).
- **EXR → IMF conform** — VFX-origin sources go through `vfx` → OIIO → J2K encode.

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

`broadcast-io` captures the tape to ProRes 422 HQ master. `ffmpeg-analyze` confirms Rec.2020 PQ. `hdr-meta` extracts RPU profile 7 and converts to 8.1. `ffmpeg-broadcast` encodes J2K IMF with captions and PCM audio. `hdr-meta inject-rpu` adds the 8.1 track. Photon validates. `media-cloud-upload` Asperas to Netflix.
