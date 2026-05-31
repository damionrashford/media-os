---
name: ffmpeg-color
description: >
  Color and HDR work with ffmpeg: tone-map HDR to SDR, convert HDR10/HDR10+/HLG/Dolby Vision to Rec.709, change color primaries or transfer function, BT.2020 to BT.709, PQ and HLG linear sandwich, apply a LUT or .cube or .3dl or Hald CLUT, color grade, cinematic or teal-and-orange or film-emulation look, colorbalance, selectivecolor, colorlevels, colorchannelmixer, hue, fix color cast, match color between clips, legacy BT.601 to BT.709, ACES color management, OCIO config, ACEScc or ACEScg or ACES2065-1, DCI-P3, embed or detect ICC profiles, match a DaVinci Resolve pipeline. Use when the user wants to tone-map HDR, downconvert HDR to SDR, make HDR phone-playable, apply a LUT or .cube, color grade a clip, do a film look, fix a color cast, match shots, convert between color spaces, do ACES or OCIO color management, or embed ICC profiles.
argument-hint: "[operation] [input]"
---

# FFmpeg Color

**Context:** $ARGUMENTS

Consolidated color pipeline: HDR tone-mapping, LUT/creative grading, and professional OCIO/ACES color management. Always invoke `ffmpeg-docs` before recommending a flag or filter — it is the anti-hallucination guardrail.

## When to use

- Source is HDR10, HDR10+, HLG, or Dolby Vision and you need an SDR deliverable, or colors look washed/neon/dark after transcoding an HDR file.
- You need a primaries/transfer/matrix change (BT.2020 → BT.709, PQ → gamma) without full tone-mapping.
- You have a `.cube`/`.3dl`/Hald CLUT to bake in, or you want filter-based grading (balance, selective color, levels, channel mixer, hue).
- You need to match shot-to-shot color, fix a cast, or normalize legacy BT.601 ↔ BT.709 footage.
- You want ACES/OCIO-managed fidelity (ACEScc/ACEScg/ACES2065-1 ↔ Rec.709/sRGB/DCI-P3/Rec.2020 PQ), film-emulation LMTs, or ICC embedding/detection to match a DaVinci Resolve pipeline.

## Techniques

- Read `references/hdr-color.md` when tone-mapping HDR to SDR, handling HDR10/HDR10+/HLG/Dolby Vision, changing primaries or transfer functions, or tagging output color. It carries the detect → tone-map → tag workflow and the `tonemap` vs `libplacebo` decision.
- Read `references/lut-grade.md` when applying a LUT (`.cube`/`.3dl`/Hald CLUT) or doing filter-based grading (`colorbalance`, `selectivecolor`, `colorlevels`, `colorchannelmixer`, `hue`), matching clips, or converting legacy BT.601 ↔ BT.709 matrices.
- Read `references/ocio-colorpro.md` when doing ACES/OCIO color management, converting between ACES spaces and a display space, applying film-emulation LMTs, or embedding/detecting ICC profiles to match a Resolve pipeline.
- Read `references/colorspace.md` for tone-map operator trade-offs, full `zscale`/`libplacebo`/`colorspace` option catalogs, HDR metadata/DV profile tables, and primaries/transfer/matrix lookup.
- Read `references/filters.md` for full grading-filter option tables, the `.cube` spec, Hald identity generation, chain ordering, and the grading recipe book.
- Read `references/ocio.md` for the ACES config version matrix, OCIO role names, colorspace catalog, `ociobake` usage, and vendor camera-log spaces.

## Gotchas

- `tonemap` operates on **linear-light, floating-point** frames only. Sandwich it: `zscale=t=linear:npl=100,format=gbrpf32le` **before**, `zscale=t=bt709:m=bt709:r=tv,format=yuv420p` **after**. Skip the sandwich and you get black or banded output. HLG input also needs `zscale=tin=arib-std-b67`, or HLG code values are misread as PQ and the picture goes dark.
- Always set explicit output tags `-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv`. Omit them and QuickTime/Chrome guess BT.709 over still-HDR or already-mapped pixels and render neon garbage or washed-out frames. `tv` vs `pc` range mismatch crushes blacks / blows highlights.
- Tone-mapping **cannot** be done with stream copy — re-encode video (audio may still `-c:a copy`). `libplacebo` needs `-init_hw_device vulkan` before `-i` plus `hwupload`/`hwdownload,format=yuv420p`; most Apple Silicon Homebrew builds have no Vulkan, so fall back to `tonemap`. Dolby Vision p5 tone-maps as HDR10 (RPU dropped); p7/8 enhancement layers need `dovi_tool` first.
- For HDR out of OCIO, the x265 `master-display` master string is critical: `master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,50)` with `repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc` — and you must still set the matching container `-color_*` tags.
- `interp=tetrahedral` beats `trilinear` for nearly all `.cube` LUTs (smoother gradients, no hue-transition banding). `selectivecolor` values are **space-separated** `C M Y K` 4-tuples (`reds=0 0 -0.5 0`), not commas. Most `.cube` LUTs are RGB-domain — insert `format=rgb24` before `lut3d` on YUV input.
- LUTs baked in Rec.709 assume Rec.709 input — feeding sRGB/log/HDR produces wrong color. Never apply a creative LUT *after* HDR→SDR tone-mapping unless built for the mapped output; LUT-at-log → tone-map is the correct order for log sources.
- The `ocio` filter requires `--enable-libocio` (rare in stock builds — check `ffmpeg -filters | grep ocio`); if absent, `ociobake` a `.cube` and apply via `lut3d`. OCIO needs `$OCIO` set and float bracketing (`format=gbrpf32le`). ACES config versions 1.x vs 2.0 are NOT drop-in — names drift; `Rec.709 ≠ sRGB` (same primaries, different TRC). ICC embeds reliably only in MKV/MOV, not MP4.

## Scripts

- `scripts/hdrcolor.py` — HDR/color tone-mapping. Subcommands: `detect`, `hdr-to-sdr`, `hlg-to-sdr`, `bt2020-to-bt709`. Flags `--method {tonemap,libplacebo}`, `--crf`, `--dry-run`, `--verbose`.
- `scripts/grade.py` — LUT/filter grading. Subcommands: `lut`, `haldclut`, `balance`, `selective`, `match-bt601-to-bt709`. `--dry-run`, `--verbose`.
- `scripts/colorpro.py` — OCIO/ACES + ICC. Subcommands: `check`, `aces-to-rec709`, `transform`, `bake-lut`, `attach-icc`. `--dry-run`, `--verbose`.

Invoke via `uv run ${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-color/scripts/<script>.py <subcommand> ...`. Full usage in the matching reference file.
