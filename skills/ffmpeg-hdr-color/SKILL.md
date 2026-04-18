---
name: ffmpeg-hdr-color
description: >
  HDR tone-mapping and color-space conversion with ffmpeg: tonemap, zscale, libplacebo tone-mapping, colorspace filter, HDR10/HDR10+/HLG/Dolby Vision → SDR, BT.2020 → BT.709, PQ → gamma 2.4. Use when the user asks to convert HDR to SDR, tone-map HDR10, downconvert HDR10 to Rec.709, handle Dolby Vision, convert HLG to SDR, change color primaries or transfer function, or make HDR content SDR-playable on phones/web.
argument-hint: "[operation] [input]"
---

# FFmpeg HDR / Color

**Context:** $ARGUMENTS

## Quick start

- **HDR10 → SDR (safe, works everywhere):** → Step 2 (tonemap) + Step 3 + Step 4
- **HDR10 → SDR (best quality, Vulkan):** → Step 2 (libplacebo) + Step 3 + Step 4
- **HLG → SDR:** → Step 3 (HLG recipe)
- **BT.2020 → BT.709 (SDR-only primaries fix):** → Step 3 (zscale primaries)
- **Detect what kind of HDR a file is:** → Step 1
- **Make sure the output is tagged correctly:** → Step 4

## When to use

- Source is HDR10, HDR10+, HLG, or Dolby Vision and you need an SDR deliverable.
- Colors look washed out, too dark, or neon after transcoding an HDR file.
- Target player assumes BT.709 and you have BT.2020-tagged content.
- Mobile/web/social targets require SDR + Rec.709.
- You need to burn in correct color tags so downstream tools don't mis-interpret.

## Step 1 — Detect the HDR type via ffprobe

Inspect `color_transfer`, `color_primaries`, `color_space`, and `side_data_list` of the video stream.

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_space,color_transfer,color_primaries,color_range:stream_side_data=+ \
  -of json input.mkv
```

Decision map:

| `color_transfer`              | `color_primaries` | Side data                     | Type       |
| ----------------------------- | ----------------- | ----------------------------- | ---------- |
| `smpte2084`                   | `bt2020`          | `Mastering display metadata`  | HDR10      |
| `smpte2084`                   | `bt2020`          | `HDR Dynamic Metadata SMPTE2094-40` | HDR10+    |
| `arib-std-b67`                | `bt2020`          | (may be absent)               | HLG        |
| `smpte2084` (DoVi profile 5/7/8) | `bt2020`       | `DOVI configuration record`   | Dolby Vision |
| `bt709` / `smpte170m`         | `bt709`           | —                             | SDR        |

Or use the helper: `uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py detect --input input.mkv`.

## Step 2 — Pick the tone-map path

- **`tonemap` filter (CPU, zimg):** safe default, works on any ffmpeg built with `--enable-libzimg`. Requires floating-point linear-light input (the `zscale=t=linear,format=gbrpf32le` sandwich — see Gotchas). Operators: `hable` (default, recommended), `mobius`, `reinhard`, `gamma`, `clip`, `linear`.
- **`libplacebo` filter (Vulkan, higher quality):** better roll-off, built-in debanding, peak detection. Requires `-init_hw_device vulkan` and ffmpeg built with `--enable-libplacebo --enable-vulkan`. On Apple Silicon most Homebrew ffmpeg builds lack Vulkan — fall back to `tonemap`.
- **`colorspace` filter:** does matrix/primaries/trc conversion but **not** real HDR tone-mapping. Use for BT.2020-SDR → BT.709-SDR, not for PQ/HLG → SDR.

Check availability:

```bash
ffmpeg -hide_banner -filters | grep -E "zscale|tonemap|libplacebo|colorspace"
```

## Step 3 — Build the full filter chain

### HDR10 → SDR (tonemap, CPU, works everywhere)

```bash
ffmpeg -i hdr.mkv \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  -c:v libx264 -crf 19 -preset medium \
  -c:a copy \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  out.mp4
```

### HDR10 → SDR (libplacebo, highest quality)

```bash
ffmpeg -init_hw_device vulkan \
  -i hdr.mkv \
  -vf "format=yuv420p10le,hwupload,libplacebo=tonemapping=bt.2390:colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p,hwdownload,format=yuv420p" \
  -c:v libx264 -crf 18 -preset medium \
  -c:a copy \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  out.mp4
```

### HLG → SDR

```bash
ffmpeg -i hlg.mkv \
  -vf "zscale=t=linear:npl=100:tin=arib-std-b67,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  -c:v libx264 -crf 19 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  out.mp4
```

### Dolby Vision profile 5 (single-layer, IPTPQc2)

Profile 5 is PQ-based and can be tone-mapped like HDR10; the DoVi RPU metadata is discarded. Profiles 7 and 8 need a real DV-aware decoder (e.g. `dovi_tool`/`hdr10plus_tool` pre-processing) — ffmpeg alone cannot fully resolve enhancement layers.

```bash
ffmpeg -i dovi_p5.mkv \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  -c:v libx264 -crf 19 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  out.mp4
```

### BT.2020 → BT.709 (SDR-to-SDR primaries only, no tone-mapping)

```bash
ffmpeg -i bt2020_sdr.mkv \
  -vf "zscale=primaries=709:transfer=709:matrix=709" \
  -c:v libx264 -crf 18 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  out.mp4
```

### SDR → faux HDR (inverse tone-map; warning: marketing only)

```bash
ffmpeg -i sdr.mp4 \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt2020,tonemap=tonemap=linear:param=4,zscale=t=smpte2084:m=bt2020nc:r=tv,format=yuv420p10le" \
  -c:v libx265 -crf 18 -x265-params hdr10=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc \
  -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc \
  out.mkv
```

Real HDR requires real dynamic range; "upconverting" SDR rarely produces a better image.

## Step 4 — Set output color tags and verify

Always pass explicit container flags so downstream players don't guess:

```
-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv
```

Verify they stuck:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_space,color_transfer,color_primaries,color_range \
  -of default=nw=1 out.mp4
```

Expected:

```
color_range=tv
color_space=bt709
color_transfer=bt709
color_primaries=bt709
```

## Available scripts

- **`scripts/hdrcolor.py`** — stdlib-only helper. Subcommands: `detect`, `hdr-to-sdr`, `hlg-to-sdr`, `bt2020-to-bt709`. Supports `--dry-run`, `--verbose`, `--method {tonemap,libplacebo}`, `--crf`.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py detect --input in.mkv
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py hdr-to-sdr --input in.mkv --output out.mp4 --method tonemap --crf 19
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py hdr-to-sdr --input in.mkv --output out.mp4 --method libplacebo
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py hlg-to-sdr --input hlg.mkv --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/hdrcolor.py bt2020-to-bt709 --input in.mkv --output out.mp4
```

## Reference docs

- Read [`references/colorspace.md`](references/colorspace.md) for tone-map operator trade-offs, full `zscale` / `libplacebo` / `colorspace` option catalogs, HDR metadata profiles, and primaries/transfer/matrix lookup tables.

## Gotchas

- `tonemap` operates on **linear-light, floating-point** frames only. You MUST sandwich it: `zscale=t=linear:npl=100,format=gbrpf32le` **before**, and `zscale=t=bt709:m=bt709:r=tv,format=yuv420p` **after**. Skip the sandwich and you get a black or banded result.
- `npl=100` is nominal peak luminance (cd/m²) — usual reference for SDR targets. Raise to `200`–`400` for brighter-looking output; lower clips highlights.
- `tonemap=desat=0` preserves saturation. Values `1.0`–`2.0` progressively desaturate highlights; `2.0` mangles skin tones.
- `libplacebo` requires `-init_hw_device vulkan` **before** `-i`. Also needs `hwupload` before and `hwdownload,format=yuv420p` after in the filter chain.
- On Apple Silicon most Homebrew ffmpeg builds have no Vulkan — `libplacebo` will error with "No such filter". Use the `tonemap` recipe instead.
- Dolby Vision profile 5 is single-layer PQ; tone-map as HDR10 and the RPU metadata is silently dropped. Profiles 7/8 have an enhancement layer — ffmpeg can decode the base layer but the EL is discarded, so output is darker/flatter than a true DV-aware pipeline (use `dovi_tool` to strip/convert the RPU first).
- HDR10+ dynamic metadata (SMPTE ST 2094-40) is discarded by both `tonemap` and `libplacebo`. That is expected when the output is SDR.
- Skipping `-color_primaries/-color_trc/-colorspace` on the **output** tags the file with unspecified flags; some players (QuickTime, Chrome on macOS) then assume BT.709 and display your still-HDR pixels as neon garbage, or display your tone-mapped pixels as washed-out.
- `zscale` comes from zimg. Check with `ffmpeg -filters | grep zscale`; if absent, ffmpeg wasn't built with `--enable-libzimg` — rebuild or use Homebrew's `ffmpeg` with `--with-libzimg`, or fall back to `colorspace` + `format` for SDR-only conversions.
- **Tone-mapping cannot be done with stream copy.** You must re-encode video. Audio can still `-c:a copy`.
- Lowercase/uppercase mismatch: output-flag `-colorspace bt709` vs `zscale m=bt709` vs `colorspace=bt709` inside libplacebo — same concept, three syntaxes, easy to cross-wire.
- Tone-map operators: `hable` (default, safe, filmic), `mobius` (softer roll-off), `reinhard` (flatter, often crushed blacks), `clip` (hard cutoff — banding), `linear` (scales only, no roll-off), `gamma` (simple power curve). Default to `hable`.
- HLG input needs `zscale=tin=arib-std-b67` (or `t=arib-std-b67` before linearization). Forgetting it treats HLG code values as PQ and produces a dark, wrong-gamma picture.
- Setting `-color_range tv` vs `pc` matters: most broadcast/streaming is `tv` (limited, 16–235). Tagging `pc` when the pixels are `tv` crushes blacks and blows highlights.

## Examples

### Example 1: 4K HDR10 Blu-ray rip → 1080p SDR MP4 for phones

```bash
ffmpeg -i hdr10_2160p.mkv \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,scale=1920:1080:flags=lanczos" \
  -c:v libx264 -crf 20 -preset slow -profile:v high -level 4.1 \
  -c:a aac -b:a 192k \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -movflags +faststart \
  phone_sdr_1080p.mp4
```

### Example 2: BBC HLG broadcast archive → Rec.709 SDR proxy

```bash
ffmpeg -i bbc_hlg.mxf \
  -vf "zscale=t=linear:npl=200:tin=arib-std-b67,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0.5,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  -c:v libx264 -crf 18 -preset medium \
  -c:a copy \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  proxy.mp4
```

### Example 3: BT.2020 SDR source (no PQ/HLG) → BT.709 SDR

```bash
ffmpeg -i bt2020_sdr.mov \
  -vf "zscale=primaries=709:transfer=709:matrix=709" \
  -c:v libx264 -crf 17 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  rec709.mp4
```

## Troubleshooting

### Error: `No such filter: 'zscale'`

Cause: ffmpeg built without zimg.
Solution: `brew reinstall ffmpeg` (Homebrew includes zimg); or build ffmpeg with `--enable-libzimg`. As a workaround, `colorspace=all=bt709:iall=bt2020ncl:fast=1` can do BT.2020-SDR → BT.709-SDR but cannot tone-map.

### Error: `Impossible to convert between the formats supported by the filter 'Parsed_tonemap_0' and the filter 'auto_scaler_0'`

Cause: `tonemap` received non-float pixels.
Solution: Prepend `zscale=t=linear:npl=100,format=gbrpf32le` and append `zscale=t=bt709:m=bt709:r=tv,format=yuv420p`.

### Error: `No such filter: 'libplacebo'` or `Failed to initialize Vulkan`

Cause: ffmpeg built without libplacebo/Vulkan (common on macOS Homebrew).
Solution: Use the `tonemap` recipe instead. Check with `ffmpeg -filters | grep libplacebo` and `ffmpeg -init_hw_device list`.

### Output looks dark / washed out / banded

Cause: Missing output color tags, wrong `npl`, or `desat` too high.
Solution: Add `-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv`; try `npl=150` or `npl=200`; set `desat=0`.

### Output still looks like HDR on the target player

Cause: Tone-map chain not actually in the graph (e.g. `-c:v copy` used) or output tagged as BT.2020/PQ.
Solution: Confirm re-encode is happening (not `-c copy`); re-verify with `ffprobe` per Step 4.

### Dolby Vision file plays dark/flat even after tone-mapping

Cause: DV profile 7/8 enhancement layer discarded by ffmpeg.
Solution: Pre-process with `dovi_tool` (strip RPU to profile 8.1 single-track, or demux BL only), then run the HDR10 recipe.
