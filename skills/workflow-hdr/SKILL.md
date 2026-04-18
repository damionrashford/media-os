---
name: workflow-hdr
description: End-to-end HDR authoring — HDR10 (static MDC + MaxCLL/MaxFALL), HDR10+ dynamic metadata JSON, Dolby Vision profiles 5/7/8.1/8.4, HLG, PQ↔HLG conversion, SDR↔HDR tone-mapping (hable/mobius/reinhard/bt2390/aces), dovi_tool + hdr10plus_tool orchestration, and multi-format dual-delivery. Use when the user says "HDR10+", "Dolby Vision", "PQ to HLG", "tone-map to SDR", "ACES RRT", "HLG broadcast", "DV profile 7 to 8.1", "YouTube HDR", or anything HDR-color-pipeline.
argument-hint: [source]
---

# Workflow — HDR

**What:** Author, transcode, tone-map, and deliver HDR content across every major standard without metadata loss.

## Skills used

`ffmpeg-hdr-color`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `hdr-dynmeta-docs`, `ffmpeg-ocio-colorpro`, `vfx-oiio`, `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-transcode`, `ffmpeg-hwaccel`, `ffmpeg-mxf-imf`, `media-shaka`.

## Pipeline

### Step 1 — Probe

`ffmpeg-probe` (`moprobe --color`) captures: color primaries (bt709 / bt2020), transfer (bt709 / smpte2084 / arib-std-b67), matrix, range, MaxCLL / MaxFALL, DoVi RPU SEI, HDR10+ SEI.

### Step 2 — SDR → HDR (up)

`ffmpeg-hdr-color sdr-to-hdr --target hlg|hdr10` with a synthetic MDC. Inverse tone-mapping is creative — use sparingly; real HDR grading is preferable.

### Step 3 — HDR → SDR (down)

`ffmpeg-hdr-color hdr-to-sdr --algo <hable|mobius|reinhard|bt2390|bt2446a|bt2446c|aces>`. Try `bt2446a` first — ITU-standard, predictable.

### Step 4 — Cross-format HDR conversion

Between HDR10 and HLG, ALWAYS via the linear-float sandwich:
```
zscale=t=linear → format=gbrpf32le → zscale=t=<new_transfer>:p=<primaries>:m=<matrix>
```
Missing the float32 step silently clips highlights.

### Step 5 — Dolby Vision RPU ops

`hdr-dovi-tool`:
- `extract-rpu` from HEVC
- `convert --mode 2` (profile 7 → 8.1 for streaming)
- `editor` for L1/L2/L8 metadata edits
- `inject-rpu` into fresh HEVC

For HDR10 → DoVi uplift, `dovi_tool` generates a synthetic RPU.

### Step 6 — HDR10+ metadata ops

`hdr-hdr10plus-tool`:
- `extract` JSON from HEVC
- author / edit per-scene brightness JSON
- `inject` into HEVC

Or inline at encode: `-x265-params "dhdr10-info=metadata.json"`.

### Step 7 — Author final HEVC

`libx265` with:
- `hdr-opt=1`
- `repeat-headers=1` (streaming)
- `master-display=G(...)B(...)R(...)WP(...)L(...)` (in x265 units: 0.00002 for chromaticity, 0.0001 for luminance)
- `max-cll=<MaxCLL>,<MaxFALL>`
- `-pix_fmt yuv420p10le` (mandatory; 8-bit = banding)
- `-tag:v hvc1` for MP4 Apple compat

### Step 8 — AV1 Dolby Vision (alternative)

`libaom-av1` or `libsvtav1` at profile 10.

### Step 9 — Deliver / wrap

MP4 (`hvc1` tag), MKV, or J2K IMF via `ffmpeg-mxf-imf`. DASH/HLS packaging via `media-shaka`.

## Variants

- **DoVi-only sensible** — profile 8.1 single-layer HDR10-base (most OTT accepts). Extract P7 RPU → convert to 8.1 → re-encode stripping old → inject fresh.
- **Dual delivery (HDR10 + HDR10+ + DoVi + HLG + SDR)** — start from linear EXR or ProRes 4444. Encode HDR10 base, inject HDR10+ JSON, inject DoVi RPU, encode HLG separately, SDR via tone-map.
- **YouTube HDR** — accepts HDR10 / HDR10+ / HLG / DoVi. Best results from VP9 or AV1.
- **Apple HLS HDR** — HEVC fMP4, `hvc1` tag, proper color tags.
- **HLG live broadcast** — backward-compat 100-nit SDR window on non-HDR displays.

## Gotchas

- **HDR metadata lives in NAL units inside HEVC.** Any re-encode strips unless explicitly preserved. `-c:v copy` when possible; otherwise extract → encode → re-inject.
- **Dolby Vision RPU = SEI NALs 62/63 with Dolby T.35 UUID.**
- **HDR10+ metadata = SEI 0x4 with Samsung T.35 UUID.**
- **Stripping NALs is easy; re-injecting correctly is hard.** Always use `dovi_tool` / `hdr10plus_tool` — never hand-craft.
- **Profile 7 dual-layer has TWO video layers (BL + EL).** Some extractors choke. `dovi_tool` is canonical.
- **`master-display` x265 unit trap:** chromaticity in 0.00002 units (0.6 = 30000), luminance in 0.0001 units (1000 nits = 10000000). Wrong units = invalid SEI.
- **`max-cll=1000,400`** (MaxCLL, MaxFALL) — single pair, NOT an array.
- **`repeat-headers=1` mandatory for streaming.** Without, first segment has headers, subsequent don't → mid-stream joiners break.
- **`hdr-opt=1` enables HDR optimizations but auto-sets NOTHING.** You still need explicit `colorprim`, `transfer`, `colormatrix`.
- **aom-av1 flags differ** — `--color-primaries` etc. via `-svtav1-params`.
- **BT.2100 PQ (ST 2084) and HLG (ARIB STD-B67) are INCOMPATIBLE transfer curves.** HLG-display of PQ = washed. PQ-display of HLG = dim.
- **PQ = absolute luminance** (100 nits = 100 nits on screen). **HLG = relative** (100% = display peak, typically 1000 nits).
- **HLG has an OOTF** (optical-optical transfer function) that shifts gamma based on display peak. Tone-mapping to SDR must respect it.
- **`tonemap_opencl` + `libplacebo` are GPU-accelerated** — much faster than CPU for 4K. Needs libplacebo-enabled ffmpeg build.
- **MP4 HEVC tag must be `hvc1` for iOS/Apple.** `hev1` works elsewhere; Apple rejects.
- **Netflix IMF wants J2K video** with HDR10+/DoVi metadata as a SIDECAR XML, not inline.
- **Dolby Vision MEL profile 8.4 uses HLG base** (different workflow from 8.1 PQ base).
- **YouTube re-encodes HDR uploads.** Don't expect bit-for-bit preservation.
- **`libx265` defaults to `yuv420p`** (8-bit). MUST explicitly set `-pix_fmt yuv420p10le` for HDR — without it = banding.
- **EXR linear ACEScg → PQ/HLG path:** `zscale=t=linear` is CRITICAL between ACEScg and display-referred. Without it, gamma compression doubles.
- **ACES RRT+ODT is NOT a naive tone-map.** Use OCIO for canonical ACES RRT path.

## Example — HDR10+ with DoVi P8.1 dual delivery

Source HEVC HDR10 base → `hdr-dovi-tool` generate synthetic RPU P8.1 → `hdr-hdr10plus-tool` author per-scene JSON → encode fresh HEVC 10-bit with `hdr-opt=1 repeat-headers=1 master-display=... max-cll=1000,400` → `dovi_tool inject-rpu` → `hdr10plus_tool inject` → MP4 `-tag:v hvc1`.

## Related

- `workflow-broadcast-delivery` — IMF / MXF packaging for OTT delivery.
- `workflow-vfx-pipeline` — ACES EXR sources feeding HDR master.
- `workflow-streaming-distribution` — packaging HDR for HLS/DASH.
