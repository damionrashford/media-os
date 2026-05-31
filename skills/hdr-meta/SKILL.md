---
name: hdr-meta
description: >
  Author and edit HDR dynamic metadata with dovi_tool (Dolby Vision RPU) and hdr10plus_tool (HDR10+ SEI). Use when the user asks to extract or inject a Dolby Vision RPU, convert DV profile 7 to 8.1, edit a DV RPU JSON, repackage HEVC with Dolby Vision, strip Dolby Vision, plot DV L1 brightness, demux or mux a dual-layer BL+EL stream, extract HDR10+ metadata to Samsung-compatible JSON, inject HDR10+ SEI into an HEVC encode, bake HDR10+ into x265 via dhdr10-info, remove or verify HDR10+, plot an HDR10+ brightness curve, edit an HDR10+ JSON, look up a dovi_tool or hdr10plus_tool subcommand or flag, or check which Dolby Vision profiles (4, 5, 7, 8.1, 8.4) are supported.
argument-hint: "[task] [args...]"
---

# HDR dynamic metadata

**Context:** $ARGUMENTS

Author and edit HDR dynamic metadata for HEVC: Dolby Vision RPU (`dovi_tool`) and HDR10+ SEI (`hdr10plus_tool`). Both tools operate on raw HEVC Annex-B bytestreams, not muxed MP4/MKV.

## When to use

- Extract, inject, edit, convert, or strip Dolby Vision RPU metadata. → `dovi-tool.md`
- Convert a profile-7 dual-layer (BL+EL) source to single-layer 8.1, or demux/mux BL+EL. → `dovi-tool.md`
- Extract, inject, edit, remove, or verify HDR10+ dynamic metadata; bake HDR10+ into an x265 encode. → `hdr10plus-tool.md`
- Plot per-frame brightness curves for either format.
- Look up a subcommand or flag, or check DV profile support, before naming tool options. → `docs-search.md`

## Techniques

- Read `references/dovi-tool.md` when the task is Dolby Vision: extract-rpu, inject-rpu, convert 7→8.1, editor, export, plot, demux, mux, remove, or the end-to-end pipeline (ffmpeg bsf → extract → edit → inject → mkvmerge/MP4Box).
- Read `references/hdr10plus-tool.md` when the task is HDR10+: extract to Samsung JSON, inject SEI, remove, editor, plot, or the x265 `--dhdr10-info` encode preset.
- Read `references/edit-schema.md` when authoring a `dovi_tool` editor JSON (active_area/L5 crop, remove_scenes, duplicate_scenes, scene_cuts, L1/L6 offsets) — also covers the HDR10+ editor JSON shape.
- Read `references/x265-options.md` when building an x265 HDR10+ encode command (colorprim/transfer/colormatrix, --hdr10, --master-display, --max-cll, --dhdr10-info).
- Read `references/subcommands.md` for the verified subcommand catalog and Annex-B I/O pipeline shape for both tools.

## Docs lookup

Before naming any `dovi_tool` / `hdr10plus_tool` subcommand, flag, or DV profile, use `references/docs-search.md` to search/fetch the canonical upstream READMEs and release notes via `scripts/hdrdocs.py`. This is the anti-hallucination guardrail — `convert`/`demux`/`mux` are dovi_tool-only; `extract`/`inject`/`remove`/`plot`/`editor` exist in both with different I/O. Profile 8.2 is NOT documented as supported.

## Gotchas

- **Input to extract/extract-rpu/inject/remove must be HEVC Annex-B, not muxed MP4/MKV.** Unpack first: `ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc out.hevc`. dovi_tool's `pipeline` wrapper handles this; standalone subcommands do not.
- **DV uses RPU NAL units; HDR10+ uses SMPTE 2094-40 SEI NAL units.** They can coexist in one stream — one tool per format. Don't confuse the two or feed a Samsung HDR10+ JSON to dovi_tool (or vice versa).
- **RPU NAL ordering is strict** — inject-rpu places RPU NALs immediately before slice-layer NALs; hand-spliced streams silently drop DV. Always use the tool.
- **DV profiles supported: 4, 5, 7, 8.1, 8.4. Profile 8.2 is NOT documented** — don't promise it. Profile 7 is BL+EL dual-layer; convert mode 2 → 8.1 for broad compatibility.
- **After inject you have raw Annex-B HEVC — you MUST remux.** Prefer `mkvmerge -o out.mkv injected.hevc` (MKV) or `MP4Box -add injected.hevc:dvhe=hvcC out.mp4` (MP4). ffmpeg's MP4 muxer for HEVC+RPU/HDR10+ is flaky.
- **HDR10+ `remove` strips only the dynamic SEI**, not HDR10 static metadata (MaxCLL/MaxFALL/MDCV) — those are separate VUI/SEI fields from the encoder.
- **Prefer x265 `--dhdr10-info` over inject-after-encode** for HDR10+ — single pass, correct SEI placement. inject is for fixing encodes you can't redo. Requires a 10-bit x265 build with HDR10+ support (`x265 --help 2>&1 | grep dhdr10`).
- **Editor JSON schema changes between tool versions.** Pin the tool version alongside the JSON in VCS. Apple TV/iOS prefer DV profile 5; older Apple devices may reject 8.1.

## Scripts

- `scripts/dovi.py` — Dolby Vision RPU: `info`, `extract-rpu`, `inject-rpu`, `convert`, `editor`, `export`, `plot`, `demux`, `mux`, `remove`, plus `pipeline` (end-to-end ffmpeg + extract + edit + inject + remux).
- `scripts/hdr10plus.py` — HDR10+: `extract`, `inject`, `remove`, `editor`, `plot`, `x265-encode` (prints an x265 `--dhdr10-info` command).
- `scripts/hdrdocs.py` — docs lookup: `list-pages`, `search`, `section`, `fetch`, `index` against the upstream READMEs/releases.

All scripts are stdlib-only Python 3, non-interactive, print the exact shell command to stderr before running, and support `--dry-run`. Run via `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py`.
