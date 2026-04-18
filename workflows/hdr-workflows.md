# HDR Workflows

**What:** Author, transcode, tone-map, and deliver HDR content across every major HDR standard — HDR10, HDR10+, Dolby Vision (profiles 5 / 7 / 8.1), HLG — including dynamic-metadata pipelines that traditional tooling can't touch.

**Who:** Colorists, OTT platform engineers, broadcast delivery teams, streaming platform ingest ops, content owners preparing HDR masters for Netflix / Disney+ / Apple TV+ / Amazon / YouTube.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| HDR color transforms | `ffmpeg-hdr-color` | zscale, tonemap, libplacebo; HDR10/HLG/DoVi → SDR |
| Dolby Vision RPU | `hdr-dovi-tool` | Extract/inject RPU, profile 7 → 8.1, RPU editing |
| HDR10+ metadata | `hdr-hdr10plus-tool` | Extract/inject HDR10+ SEI metadata, JSON authoring |
| HDR spec reference | `hdr-dynmeta-docs` | SMPTE 2094 series, ITU-R BT.2100 |
| OCIO / ACES | `ffmpeg-ocio-colorpro`, `vfx-oiio` | Color-managed tone-map via OCIO |
| Probe / verification | `ffmpeg-probe`, `media-mediainfo` | Verify HDR metadata in output |
| Transcode engine | `ffmpeg-transcode`, `ffmpeg-hwaccel` | libx265 / libaom-av1 with HDR encoder params |
| IMF delivery | `ffmpeg-mxf-imf` | HDR IMF CPL / MXF wrap |
| DRM | `media-shaka` | HDR-aware packaging for OTT |
| VFX | `vfx-openexr` | EXR HDR data for DIT / color |
| Lookup verification | `ffmpeg-docs` | Never hallucinate an HDR flag |

---

## The HDR landscape

| Format | Transfer | Peak (nits) | Gamut | Metadata | Notes |
|---|---|---|---|---|---|
| HDR10 | ST 2084 (PQ) | 1000+ nominal | BT.2020 | Static (MDC, MaxCLL, MaxFALL) | Universal. Bare minimum HDR. |
| HDR10+ | ST 2084 (PQ) | 1000+ | BT.2020 | Dynamic (per-scene ST 2094-40) | Royalty-free, Samsung/Amazon-led |
| Dolby Vision P5 | ST 2084 (PQ) | up to 10k | BT.2020 | Single-layer + RPU (dynamic) | Mobile encoding |
| Dolby Vision P7 | ST 2084 (PQ) | up to 10k | BT.2020 | Dual-layer (BL+EL+RPU) | Blu-ray |
| Dolby Vision P8 / 8.1 | ST 2084 (PQ) | up to 10k | BT.2020 | Single-layer + RPU | Streaming OTT |
| HLG | ARIB STD-B67 (HLG) | 1000 | BT.2020 | Static | Broadcast-compatible (backward-compat SDR) |
| SDR (BT.1886) | BT.1886 / sRGB | 100 | BT.709 | None | Baseline |

---

## The pipeline — by operation

### 1. Probe a source: HDR or not?

```bash
uv run .claude/skills/ffmpeg-probe/scripts/probe.py hdr-check \
  --input source.mp4
```

This reports:
- **Color primaries**: bt709 / bt2020
- **Color transfer**: bt709 / smpte2084 (PQ) / arib-std-b67 (HLG)
- **Color matrix**: bt709 / bt2020nc / bt2020c
- **Color range**: tv (limited) / pc (full)
- **Mastering Display Color Volume (MDC)**: present for HDR10
- **MaxCLL / MaxFALL**: present for HDR10
- **Dolby Vision RPU** (SEI NAL 0x4 + T.35 with Dolby UUID)
- **HDR10+ metadata** (SEI NAL 0x4 + T.35 with Samsung UUID)

### 2. SDR → HDR tone map up (creative / archival)

```bash
# SDR → HLG (simplest)
uv run .claude/skills/ffmpeg-hdr-color/scripts/hdrcolor.py sdr-to-hdr \
  --input sdr.mov --output hlg.mov --target hlg

# SDR → HDR10 with synthetic MDC
uv run .claude/skills/ffmpeg-hdr-color/scripts/hdrcolor.py sdr-to-hdr \
  --input sdr.mov --output hdr10.mov --target hdr10 \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,50)" \
  --maxcll 1000,400
```

**Warning**: inverse tone mapping is creative interpretation. SDR lacks the information HDR represents. Use sparingly; for archive content it's usually acceptable.

### 3. HDR → SDR tone map down (delivery)

```bash
# HDR10 → SDR Rec.709
uv run .claude/skills/ffmpeg-hdr-color/scripts/hdrcolor.py hdr-to-sdr \
  --input hdr10.mov --output sdr.mov \
  --tonemap hable --peak 400 --gamut-mode "warn"
```

Tonemapping algorithms:
- **hable** (Uncharted 2) — mildly saturated, cinematic
- **mobius** — gentle knee, preserves mid-tones
- **reinhard** — simple, tends to wash out highlights
- **bt2390** — ITU-R recommended for broadcast
- **bt2446a** / **bt2446c** — BBC-developed, preserves creative intent
- **aces** (via OCIO) — film-look ACES RRT+ODT

Recommended: **bt2446a** for broadcast, **hable** for cinema/OTT, **aces** for VFX pipelines.

### 4. Convert between HDR formats

**HDR10 → HLG (BBC workflow):**
```bash
ffmpeg -i hdr10.mov \
  -vf "zscale=t=linear:npl=1000,format=gbrpf32le,zscale=p=bt2020:t=arib-std-b67:m=bt2020nc:r=tv,format=yuv420p10le" \
  -c:v libx265 -preset slow -crf 18 \
  -x265-params "colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:master-display=:max-cll=" \
  hlg.mov
```

**HLG → HDR10:**
```bash
ffmpeg -i hlg.mov \
  -vf "zscale=t=linear:npl=1000,format=gbrpf32le,zscale=p=bt2020:t=smpte2084:m=bt2020nc:r=tv,format=yuv420p10le" \
  -c:v libx265 -preset slow -crf 18 \
  -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,50):max-cll=1000,400" \
  hdr10.mov
```

**Key pattern**: the `zscale=t=linear` → `format=gbrpf32le` → `zscale` sandwich is mandatory for PQ↔HLG conversions. Skipping it = wrong luminance.

### 5. Dolby Vision RPU operations

**Extract RPU from HEVC:**
```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py extract \
  --input source-p7.hevc --output rpu-p7.bin
```

**Convert profile 7 → 8.1 (dual-layer → single-layer for streaming):**
```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py convert \
  --input rpu-p7.bin --output rpu-p8.bin --target-profile 8.1
```

**Edit RPU parameters (L1 / L2 / L8 metadata — brightness/contrast/tint per-frame):**
```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py edit \
  --input rpu-p8.bin --output rpu-edited.bin \
  --edit-config edits.json
```

Example `edits.json`:
```json
{
  "crop": { "top": 132, "bottom": 132, "left": 0, "right": 0 },
  "active_area": null,
  "level5": { "presets": [ { "id": 0, "top": 132, "bottom": 132, "left": 0, "right": 0 } ] }
}
```

**Inject RPU into re-encoded HEVC:**
```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video encoded.hevc --rpu rpu-p8.bin --output with-dovi.hevc
```

**Generate RPU from HDR10 (synthetic trim pass):**
```bash
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py generate \
  --input hdr10.hevc --output synth-rpu.bin \
  --mode hdr10-to-dovi
```

### 6. HDR10+ metadata operations

**Extract HDR10+ JSON from HEVC:**
```bash
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py extract \
  --input hdr10plus.hevc --output metadata.json
```

**Author HDR10+ JSON from scratch** (per-scene brightness):
```json
[
  {
    "frame": 0,
    "targeted_system_display_maximum_luminance": 4000,
    "maxscl": [12000, 11500, 10000],
    "average_maxrgb": 2000,
    "tone_mapping_flag": true,
    "knee_point_x": 300,
    "knee_point_y": 500,
    "num_bezier_curve_anchors": 9,
    "bezier_curve_anchors": [50, 100, 200, 300, 400, 600, 800, 850, 900]
  }
]
```

**Inject HDR10+ into HEVC:**
```bash
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py inject \
  --video hdr10.hevc --json metadata.json --output hdr10plus.hevc
```

### 7. Author the final HDR HEVC

**HDR10 with libx265:**
```bash
ffmpeg -i source.mov \
  -c:v libx265 -preset slow -crf 18 -pix_fmt yuv420p10le \
  -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -color_range tv \
  -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,50):max-cll=1000,400:hdr-opt=1:repeat-headers=1:aud=1" \
  hdr10.hevc
```

**Important flags**:
- `hdr-opt=1` — enables HDR encoding optimizations
- `repeat-headers=1` — ensures VPS/SPS/PPS in every IDR (streaming requirement)
- `master-display` — exact MDC in x265 units (divide chromaticities by 50000, luminance by 10000)

**HDR10+ (dynamic metadata inline at encode):**
```bash
ffmpeg -i source.mov \
  -c:v libx265 -preset slow -crf 18 -pix_fmt yuv420p10le \
  -x265-params "dhdr10-info=metadata.json:hdr-opt=1:repeat-headers=1" \
  hdr10plus.hevc
```

**AV1 for Dolby Vision (profile 10):**
```bash
ffmpeg -i source.mov \
  -c:v libsvtav1 -crf 28 -preset 6 -pix_fmt yuv420p10le \
  -svtav1-params "enable-hdr=1:color-primaries=bt2020:transfer-characteristics=smpte2084:matrix-coefficients=bt2020nc" \
  hdr10.av1
```

### 8. Delivery / wrapping

**MP4 (OTT):**
```bash
ffmpeg -i hdr10plus.hevc -i audio.ac3 -c copy \
  -tag:v hvc1 \
  -movflags +faststart \
  deliverable.mp4
```

**MKV (archive/enthusiast):**
```bash
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py mux \
  --video hdr10plus.hevc --audio audio.ac3 --output archival.mkv
```

**IMF (Netflix-grade):**
```bash
uv run .claude/skills/ffmpeg-mxf-imf/scripts/mxfimf.py imf \
  --video deliverable.mp4 --output-dir IMF/ \
  --cpl-title "Show_HDR10plus" --image-codec j2k
```

---

## Variants

### Dolby Vision-only-when-sensible workflow

Profile 8.1 is the only DoVi flavor most OTT accepts:

```bash
# From a P7 Blu-ray source:
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py extract \
  --input bluray.hevc --output rpu-p7.bin

uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py convert \
  --input rpu-p7.bin --output rpu-p8.bin --target-profile 8.1

# Re-encode the video portion (stripping old RPU)
ffmpeg -i bluray.hevc -c:v copy -bsf:v hevc_metadata=<params> stripped.hevc

# Inject new RPU
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video stripped.hevc --rpu rpu-p8.bin --output streaming-p8.hevc
```

### Dual-delivery (HDR10 + HDR10+ + DoVi + HLG + SDR)

Professional OTT platforms need every flavor:

```bash
# Start from a linear EXR sequence or a ProRes 4444 XQ master
MASTER=master-acescg.mov

# 1. HDR10 main
ffmpeg -i $MASTER -vf "ocio=colorspace_in=ACES - ACEScg:colorspace_out=Output - Rec.2020 ST2084" \
  -c:v libx265 -x265-params "..." hdr10.hevc

# 2. HDR10+ (same video, inject JSON)
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py inject \
  --video hdr10.hevc --json dynamic.json --output hdr10plus.hevc

# 3. DoVi P8.1 (same video, inject RPU)
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video hdr10.hevc --rpu rpu-p8.bin --output dovi-p8.hevc

# 4. HLG (broadcast)
ffmpeg -i $MASTER -vf "ocio=colorspace_in=ACES - ACEScg:colorspace_out=Output - Rec.2020 HLG" \
  -c:v libx265 -x265-params "..." hlg.hevc

# 5. SDR Rec.709
ffmpeg -i $MASTER -vf "ocio=colorspace_in=ACES - ACEScg:colorspace_out=Output - Rec.709" \
  -c:v libx264 -crf 18 sdr.mov
```

### HDR YouTube upload

YouTube accepts HDR10, HDR10+, HLG, and Dolby Vision. Best results from VP9 or AV1:

```bash
ffmpeg -i master.mov \
  -c:v libaom-av1 -crf 30 -b:v 0 -pix_fmt yuv420p10le \
  -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc \
  -movflags +faststart \
  youtube-hdr.mp4
```

### Apple HLS with HDR

Apple requires HEVC in fMP4 with specific tags:

```bash
ffmpeg -i hdr10.hevc \
  -c:v copy -tag:v hvc1 \
  -c:a aac -b:a 192k \
  -f hls -hls_segment_type fmp4 -hls_time 4 \
  -hls_flags independent_segments \
  -hls_fmp4_init_filename "init.mp4" \
  master.m3u8
```

### HLG live broadcast

HLG is the only HDR format that's backward-compatible with SDR displays (limited-range 100 nits window):

```bash
# Live ingest SDI → HLG stream
ffmpeg -f decklink -i "DeckLink 8K Pro (1)" \
  -c:v libx265 -preset ultrafast -x265-params "..." \
  -f mpegts "srt://broadcaster:9000"
```

---

## Gotchas

### Metadata integrity

- **HDR metadata lives in NAL units inside HEVC** — transcoding strips it unless you explicitly preserve. Use `-c:v copy` when possible. If re-encoding, extract + re-inject.
- **Dolby Vision RPU is in SEI NAL type 62** (prefix) / **63** (suffix) with Dolby-specific ITU-T T.35 UUID.
- **HDR10+ is in SEI NAL type 4** with Samsung T.35 UUID.
- **Stripping NALs is easy, injecting correctly is hard** — use `dovi_tool` / `hdr10plus_tool` rather than hand-crafting SEI.
- **Profile 7 dual-layer DoVi has TWO video layers** (BL + EL). Most extractors handle this, but some choke — `dovi_tool` is the canonical reference.

### Encoder params

- **`master-display` unit confusion**: x265 wants chromaticities in 0.00002 units (so 0.6 = 30000), luminance in 0.0001 units (so 1000 nits = 10000000). Getting unit wrong = invalid SEI, some players reject.
- **`max-cll` is `MaxCLL,MaxFALL`**: single pair, not array. `max-cll=1000,400` means peak 1000 nit, average-frame 400 nit.
- **`repeat-headers=1` is mandatory for streaming** — without it, the first segment has headers but subsequent segments don't, breaking mid-stream joiners.
- **x265 `hdr-opt=1` enables HDR-specific optimizations** but doesn't set anything automatically — you still need explicit colorprim/transfer/colormatrix.
- **aom-av1 uses different flag names**: `--color-primaries`, `--transfer-characteristics`, `--matrix-coefficients` (hyphen-prefixed when passed via -svtav1-params).

### Display / tonemap

- **BT.2100 specifies two transfer curves**: PQ (ST 2084) and HLG (ARIB STD-B67). They are NOT compatible — HLG playback of PQ content looks washed, PQ playback of HLG content looks dim.
- **PQ is absolute luminance**: 100 nits = 100 nits on screen. HLG is relative: 100% HLG = displayed at the display's peak (1000 nits typically).
- **HLG has an OOTF (optical-optical transfer function)** that shifts gamma based on display peak. Tonemapping HLG to SDR must respect this.
- **`tonemap_opencl` + `libplacebo` are GPU-accelerated tonemap filters** — much faster than CPU `tonemap` for 4K. Require libplacebo-enabled ffmpeg build.

### Delivery

- **`.mp4` container tag for HEVC must be `hvc1`** for iOS/Apple TV. `hev1` works elsewhere but Apple rejects.
- **Netflix IMF requires J2K video** — HEVC HDR10+ / DoVi goes into the elementary stream of the J2K-wrapped MXF, not as HEVC. The dynamic metadata is also delivered as a sidecar XML.
- **Dolby Vision MEL (Minimum Enhancement Layer) profile 8.4** uses HLG as the base — different workflow from 8.1 (PQ base).
- **YouTube re-encodes HDR uploads** — don't expect bit-for-bit preservation. Deliver a clean master; YouTube handles the HDR math.
- **FFmpeg's `libx265` defaults to `yuv420p`** — MUST explicitly set `-pix_fmt yuv420p10le` for HDR. Without 10-bit, banding everywhere.

### VFX handoff

- **EXR linear-light working space → PQ/HLG**: the `zscale=t=linear` is critical between the ACEScg space and the display-ref PQ space. Without linear-intermediate, gamma compression doubles.
- **ACES RRT+ODT (reference rendering transform + output device transform) is not the same as naive tonemap** — use OCIO to apply the canonical ACES RRT for grade-accurate results.

---

## Example — "ARRI LogC source → HDR10+ OTT deliverable with DoVi P8.1"

```bash
#!/usr/bin/env bash
set -e

export OCIO=/opt/aces/config.ocio

SOURCE="raw/A001_C001.mxf"
RPU_P8="work/rpu-p8.bin"
HDR10P_JSON="work/dynamic.json"
ENCODED="work/main.hevc"
DELIVERABLE="deliver/show.mp4"

# 1. Transcode to ACEScg HDR10 base
ffmpeg -i "$SOURCE" \
  -vf "ocio=colorspace_in=Input - ARRI - LogC (v3-EI800) - Wide Gamut:colorspace_out=Output - Rec.2020 ST2084" \
  -c:v libx265 -preset slow -crf 18 -pix_fmt yuv420p10le \
  -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:hdr-opt=1:repeat-headers=1:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,50):max-cll=1000,400" \
  "$ENCODED"

# 2. Generate synthetic DoVi P8.1 from HDR10
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py generate \
  --input "$ENCODED" --output "$RPU_P8" \
  --mode hdr10-to-dovi --target-profile 8.1

# 3. Author HDR10+ per-scene metadata (from LUFS-analyzed highlights)
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py auto \
  --input "$ENCODED" --output "$HDR10P_JSON"

# 4. Inject HDR10+ first
uv run .claude/skills/hdr-hdr10plus-tool/scripts/hdr10pctl.py inject \
  --video "$ENCODED" --json "$HDR10P_JSON" --output work/with-hdr10p.hevc

# 5. Then inject DoVi P8.1 (compatible with HDR10+ — the two metadata formats coexist in separate SEI)
uv run .claude/skills/hdr-dovi-tool/scripts/dovictl.py inject \
  --video work/with-hdr10p.hevc --rpu "$RPU_P8" --output work/all-hdr.hevc

# 6. Mux with audio
ffmpeg -i work/all-hdr.hevc -i audio.ac3 \
  -c copy -tag:v hvc1 -movflags +faststart \
  "$DELIVERABLE"

# 7. Verify
uv run .claude/skills/ffmpeg-probe/scripts/probe.py hdr-check --input "$DELIVERABLE"

echo "Deliverable: $DELIVERABLE (HDR10 + HDR10+ + DoVi P8.1)"
```

---

## Further reading

- [`broadcast-delivery.md`](broadcast-delivery.md) — IMF + MXF packaging for HDR
- [`vfx-pipeline.md`](vfx-pipeline.md) — ACES pipeline supplying the master
- [`streaming-distribution.md`](streaming-distribution.md) — HDR HLS/DASH packaging
- [`vod-post-production.md`](vod-post-production.md) — color grading workflow ahead of the HDR pass
