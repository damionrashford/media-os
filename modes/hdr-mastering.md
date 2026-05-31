# Mode: hdr-mastering

**Subagent**: `hdr`
**Trigger phrases**: "Dolby Vision", "HDR10+", "HDR master", "tone map HDR", "PQ to HLG", "HLG to PQ", "DV profile", "static HDR metadata", "dynamic HDR metadata", "MaxCLL", "MaxFALL", "ACES tone map"
**Output**: `${MEDIA_WORK_DIR}/modes/hdr-mastering/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input file (SDR or HDR).
  - `target_format` — `hdr10`, `hdr10-plus`, `dolby-vision-profile-5`, `dolby-vision-profile-7`, `dolby-vision-profile-8.4`, `hlg`, `sdr-tone-map`.
- **Optional**:
  - `mastering_display` — peak nits (default: `1000`), min nits (default: `0.005`), color primaries (default: `bt2020`).
  - `maxcll_maxfall` — `auto` (measure from content, default) or explicit `<MaxCLL>,<MaxFALL>` nits.
  - `tone_map_algo` — for SDR conversion: `reinhard` / `mobius` / `hable` (default for film) / `bt2390` (default for broadcast).

## Steps

1. Read tool skills: `ffmpeg-hdr-color`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `ffmpeg-ocio-colorpro`.
2. `moprobe --color --json <source>` to capture color primaries, transfer, matrix, MaxCLL / MaxFALL (if present), HDR side-data (DV RPU, HDR10+ JSON), bit depth.
3. **STOP** if source is 8-bit and target is HDR (HDR requires 10-bit minimum). Surface that the source must be re-mastered, not just transcoded.
4. Branch by `target_format`:
   - **`hdr10`** (static metadata) → encode with `-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc` + `mastering_display_metadata` + `content_light_level`. Compute MaxCLL/MaxFALL with `ffmpeg -i <src> -vf signalstats -f null -` if `auto`.
   - **`hdr10-plus`** (dynamic metadata) → extract HDR10+ JSON from source via `hdr10plus_tool extract`, encode HEVC with `--repeat-headers --hdr10-plus` flags, inject via `hdr10plus_tool inject`.
   - **`dolby-vision-profile-5`** → DV-only (no HDR10 fallback). Encode HEVC + DV RPU; package as IMF or MXF.
   - **`dolby-vision-profile-7`** → DV + HDR10 fallback (dual-layer). `dovi_tool convert -m 2` for profile 7 mode.
   - **`dolby-vision-profile-8.4`** → DV + HDR10 fallback, single-layer (only DV profile that works in HLS). `dovi_tool convert -m 2 --rpu-out` then mux RPU into HEVC bitstream.
   - **`hlg`** → BBC/NHK broadcast HDR. Convert with `zscale=t=linear→format=gbrpf32le→zscale=p=bt2020:t=arib-std-b67` sandwich. NEVER direct format conversion.
   - **`sdr-tone-map`** → use `zscale=t=linear→tonemap=<algo>:peak=<peak>` chain. Default to `bt2390` for broadcast.
5. Build the ffmpeg command per branch.
6. **`mosafe`-wrap** the command. Reject if it doesn't pass — the zscale sandwich and SEI metadata patterns trip up training-data flags.
7. Encode. For DV profiles requiring RPU mux: use `dovi_tool inject` post-encode.
8. Verify output: `ffprobe -show_streams` confirms `color_primaries=bt2020`, `color_transfer=smpte2084` (or `arib-std-b67` for HLG); for DV: `dovi_tool info` shows correct profile.
9. For HDR10+: `hdr10plus_tool extract` from output and compare frame count to source JSON.
10. Run `moqc --ref <source> --out <output>` for sanity (VMAF is gamma-aware; HDR scores may be lower than SDR — that's expected).
11. Write `summary.md` with target format, mastering display config, before/after color metadata, DV/HDR10+ verification results.

## Output schema

```markdown
# HDR mastering — {slug} — {date}

## Source HDR profile
- **Color primaries / transfer / matrix**: {primaries / transfer / matrix}
- **Bit depth**: {N bits}
- **MaxCLL / MaxFALL**: {N / N nits, or N/A}
- **Dynamic metadata**: {HDR10+ JSON / DV RPU profile X / none}

## Target
- **Format**: {hdr10 / hdr10-plus / dolby-vision-profile-{5,7,8.4} / hlg / sdr-tone-map}
- **Mastering display**: {peak nits, min nits, primaries}
- **MaxCLL / MaxFALL out**: {N / N nits — auto-measured or explicit}
- **Tone-map algo** (SDR only): {reinhard / mobius / hable / bt2390}

## Output metadata verification
- **`ffprobe color_primaries`**: {bt2020 / bt709}
- **`ffprobe color_transfer`**: {smpte2084 / arib-std-b67 / bt709}
- **DV verification** (`dovi_tool info`): {profile X verified / N/A}
- **HDR10+ verification** (`hdr10plus_tool extract`): {N frames match source / N/A}

## VMAF (HDR-aware)
- **Score vs source**: {N}
- **Note**: HDR scores commonly trail SDR for the same perceived quality.

## Files
- **Master**: {path}
- **DV RPU sidecar** (if applicable): {path}
- **HDR10+ JSON sidecar** (if applicable): {path}
```

## Quality bar

- 10-bit minimum throughout pipeline.
- `mosafe` passed on the zscale sandwich (the key foot-gun for HDR conversion).
- For DV profile 8.4 targeting HLS: RPU is in-bitstream (mux verified via `dovi_tool info`).
- For HDR10+: per-frame JSON count matches source (no dropped metadata frames).
- Color metadata explicitly written, not "inherited" (specifying `bt709` defaults is a foot-gun in HDR pipelines).
- For SDR tone-map: peak nits specified explicitly (default to mastering_display peak, fall back to 400 nits if unknown).

## Playbook reference (folded from workflow-hdr)

**What:** Author, transcode, tone-map, and deliver HDR content across every major standard without metadata loss.

### Pipeline

#### Step 1 — Probe

`ffmpeg-probe` (`moprobe --color`) captures: color primaries (bt709 / bt2020), transfer (bt709 / smpte2084 / arib-std-b67), matrix, range, MaxCLL / MaxFALL, DoVi RPU SEI, HDR10+ SEI.

#### Step 2 — SDR → HDR (up)

`ffmpeg-hdr-color sdr-to-hdr --target hlg|hdr10` with a synthetic MDC. Inverse tone-mapping is creative — use sparingly; real HDR grading is preferable.

#### Step 3 — HDR → SDR (down)

`ffmpeg-hdr-color hdr-to-sdr --algo <hable|mobius|reinhard|bt2390|bt2446a|bt2446c|aces>`. Try `bt2446a` first — ITU-standard, predictable.

#### Step 4 — Cross-format HDR conversion

Between HDR10 and HLG, ALWAYS via the linear-float sandwich:
```
zscale=t=linear → format=gbrpf32le → zscale=t=<new_transfer>:p=<primaries>:m=<matrix>
```
Missing the float32 step silently clips highlights.

#### Step 5 — Dolby Vision RPU ops

`hdr-dovi-tool`:
- `extract-rpu` from HEVC
- `convert --mode 2` (profile 7 → 8.1 for streaming)
- `editor` for L1/L2/L8 metadata edits
- `inject-rpu` into fresh HEVC

For HDR10 → DoVi uplift, `dovi_tool` generates a synthetic RPU.

#### Step 6 — HDR10+ metadata ops

`hdr-hdr10plus-tool`:
- `extract` JSON from HEVC
- author / edit per-scene brightness JSON
- `inject` into HEVC

Or inline at encode: `-x265-params "dhdr10-info=metadata.json"`.

#### Step 7 — Author final HEVC

`libx265` with:
- `hdr-opt=1`
- `repeat-headers=1` (streaming)
- `master-display=G(...)B(...)R(...)WP(...)L(...)` (in x265 units: 0.00002 for chromaticity, 0.0001 for luminance)
- `max-cll=<MaxCLL>,<MaxFALL>`
- `-pix_fmt yuv420p10le` (mandatory; 8-bit = banding)
- `-tag:v hvc1` for MP4 Apple compat

#### Step 8 — AV1 Dolby Vision (alternative)

`libaom-av1` or `libsvtav1` at profile 10.

#### Step 9 — Deliver / wrap

MP4 (`hvc1` tag), MKV, or J2K IMF via `ffmpeg-mxf-imf`. DASH/HLS packaging via `media-shaka`.

### Variants

- **DoVi-only sensible** — profile 8.1 single-layer HDR10-base (most OTT accepts). Extract P7 RPU → convert to 8.1 → re-encode stripping old → inject fresh.
- **Dual delivery (HDR10 + HDR10+ + DoVi + HLG + SDR)** — start from linear EXR or ProRes 4444. Encode HDR10 base, inject HDR10+ JSON, inject DoVi RPU, encode HLG separately, SDR via tone-map.
- **YouTube HDR** — accepts HDR10 / HDR10+ / HLG / DoVi. Best results from VP9 or AV1.
- **Apple HLS HDR** — HEVC fMP4, `hvc1` tag, proper color tags.
- **HLG live broadcast** — backward-compat 100-nit SDR window on non-HDR displays.

### Gotchas

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

### Example — HDR10+ with DoVi P8.1 dual delivery

Source HEVC HDR10 base → `hdr-dovi-tool` generate synthetic RPU P8.1 → `hdr-hdr10plus-tool` author per-scene JSON → encode fresh HEVC 10-bit with `hdr-opt=1 repeat-headers=1 master-display=... max-cll=1000,400` → `dovi_tool inject-rpu` → `hdr10plus_tool inject` → MP4 `-tag:v hvc1`.
