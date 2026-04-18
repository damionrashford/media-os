---
name: workflow-editorial-interchange
description: Move timelines between NLEs (Premiere, Final Cut Pro X, DaVinci Resolve, Avid, Lightworks) using OTIO as the pivot format, with cuts, transitions, media links, and timecode preserved. Use when the user says "move my Premiere timeline to Resolve", "export from FCP to Avid", "round-trip AAF", "conform multi-rate edit", "generate proxies and relink", "FCPXML to AAF", or anything about editorial round-trip between pro NLEs.
argument-hint: [source-timeline]
---

# Workflow — Editorial Interchange

**What:** Translate a cut from one NLE to another without losing edits, media references, timecode, or rate-conformed proxies.

## Skills used

`otio-docs`, `otio-convert`, `media-mkvtoolnix`, `media-gpac`, `ffmpeg-probe`, `media-mediainfo`, `ffmpeg-transcode`, `ffmpeg-hwaccel`, `ffmpeg-subtitles`, `ffmpeg-captions`, `media-exiftool`, `ffmpeg-metadata`, `media-batch`.

## Pipeline

### Step 1 — Identify source + target NLE formats

| NLE | Export format(s) |
|---|---|
| Premiere | FCP7 XML, AAF |
| Final Cut Pro X | FCPXML |
| DaVinci Resolve | DRP (binary), FCPXML, AAF, EDL |
| Avid | AAF (OP-Atom MXF) |
| Lightworks | AAF, EDL (CMX3600) |

FCP7 XML and FCPXML are DIFFERENT schemas (use `fcp_xml` vs `fcpx_xml` OTIO adapters).

### Step 2 — Convert through OTIO pivot

Use `otio-convert`. OTIO is the lossless-enough pivot format. `otio-docs` has the adapter matrix.

### Step 3 — Extract media dependencies

Use OTIO's `list-media` to get the source-clip manifest with in/out points. Cross-check with `ffmpeg-probe` for actual stream specs per source.

### Step 4 — Verify + conform rates

Mixed-rate timelines are the #1 interchange break. Use `media-mediainfo` for deep diagnostics. If conform is needed, batch-transcode with `ffmpeg-transcode` + `ffmpeg-hwaccel` to a single mezzanine codec (ProRes 422 HQ or DNxHR HQ).

### Step 5 — Remap media paths in OTIO

If conformed media moves, use `otio-convert`'s remap-media operation so the target NLE resolves the new paths.

### Step 6 — Generate proxies (optional, for offline edit)

Hardware-accelerated H.264 proxies with `-r` matching source exactly. Link via proxy-suffix convention (`<original>-proxy.mov` or NLE-specific naming).

### Step 7 — Package for target NLE

- **Avid** — AAF + DNxHR MXF OP-Atom (one file per essence track).
- **Resolve** — FCPXML or DRP (DRP is opaque; use FCPXML if round-tripping).
- **Premiere** — FCP7 XML or FCPXML.
- **Final Cut Pro X** — FCPXML only.

### Step 8 — Validate on target

Import, verify: clip count, total duration, transitions, audio track count, levels. Spot-check 3–5 cut points at known timecodes.

## Variants

- **EDL-only (CMX3600)** — legacy/archival. Cuts + basic transitions only. No effects, no subclip data.
- **Round-trip sanity check** — A → B → A, diff to reveal lossy steps.
- **Mixed-rate conform** — 29.97 → 23.976 via `ffmpeg-ivtc` or frame-rate conversion.
- **Preserve timecode through conform** — `ffprobe` extract start timecode, pass to encode via `-timecode`.
- **MKV chaptered master** — `media-mkvtoolnix` for chapter split, `ffmpeg-captions` extract, package per NLE.
- **Fragmented MP4 for CMAF** — `media-gpac` with 4000 ms fragments for ABR downstream.

## Gotchas

- **FCP7 XML ≠ FCPXML.** Legacy vs X/10.x schema. Different OTIO adapters (`fcp_xml` vs `fcpx_xml`). Mixing loses structure.
- **AAF is a container, not a codec.** It may wrap MXF essence. Always inspect with `media-mediainfo` to see what's actually inside.
- **Avid MXF is OP-Atom, not OP1a.** Each essence track is a separate file. Use `-f mxf_opatom`.
- **OTIO preserves timeline structure, not media.** If media moves, `remap-media` or every clip goes offline.
- **Effects don't round-trip.** Vendor-specific effects collapse to "unknown". Budget manual re-creation.
- **Frame rate determines timecode.** 23.976p with 29.97 DF reel numbering is ambiguous — verify via `media-mediainfo`.
- **Drop-frame vs non-drop-frame** — 29.97 DF drops 2 frames every minute (except every 10th). 23.976 is non-drop. Conforming across these = offset drift.
- **Proxies must be frame-accurate to masters.** Wrong proxy rate = editorial cuts land at wrong source timecode. `-r <exact-num>/<exact-den>` not a rounded decimal.
- **Channel layout variations** — 2-ch stereo, dual-mono, 5.1 — NLEs merge-down on import inconsistently. Verify with `ffprobe`.
- **FCPXML `<media-rep>` uses `file://` URLs.** Bare paths won't link. Every `<asset>` src must be `file:///`-prefixed.
- **Premiere XML versions 4 and 5 migrated** — specify `--version` explicitly in OTIO adapter.
- **Resolve DRP is opaque binary.** Round-tripping OTIO → DRP → OTIO loses info. Prefer FCPXML.
- **AAF timecode rate must match essence rate.** Mismatch = silent clip-offset errors.
- **MXF `-timecode` must be 8-digit HH:MM:SS:FF** (`01:00:00:00`, not `3600`).
- **Consolidation can break subclip dependencies.** `/path/cam1/A001_C001.mov#0.5s-3.2s` must preserve in/out on conform or edit re-slips.
- **Prerendered effects bake in.** An editor's color-corrected render IS the source from OTIO's perspective.
- **MKVToolNix `--split` modes** — `timestamps`, `parts`, `chapters`, `size`. Wrong mode = wrong splits.
- **GPAC `MP4Box` exits 0 on some recoverable errors.** Check stderr, not just exit code.
- **ExifTool overwrites in place by default.** Use `-o output.jpg` or `-overwrite_original` to confirm intent.

## Example — Premiere cut → Resolve for finishing

`otio-convert --input premiere.xml --output-format fcpx_xml > resolve.fcpxml`. Verify media resolves, batch-transcode mixed-rate clips to ProRes 422 HQ proxies with `ffmpeg-transcode` + `ffmpeg-hwaccel`. Re-open in Resolve; spot-check timecode-critical cuts.

## Related

- `workflow-vod-post-production` — for the finishing pass after conform.
- `workflow-broadcast-delivery` — MXF/IMF delivery from the conformed master.
- `workflow-analysis-quality` — verify clips conform correctly.
