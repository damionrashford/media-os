# Mode: editorial-interchange

**Subagent**: `architect`
**Trigger phrases**: "Premiere to Resolve", "round-trip", "OTIO export", "editorial conform", "XML round-trip", "FCPXML", "EDL export", "AAF export", "convert timeline", "Avid to Premiere", "Resolve to Premiere"
**Output**: `${MEDIA_WORK_DIR}/modes/editorial-interchange/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input editorial file (FCPXML, AAF, EDL, OTIO, Premiere XML, Resolve XML, Avid OMF).
  - `target` — target format(s): `fcpxml` (Premiere/FCP), `aaf` (Avid/ProTools), `edl` (CMX 3600), `otio`, `resolve-xml`.
- **Optional**:
  - `media_root` — directory containing referenced media (for path remapping).
  - `frame_rate` — explicit conversion (e.g. 23.976 → 24 for film conform).
  - `relink_strategy` — `exact-path` (default), `filename-match`, `metadata-match`.

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/otio/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-analyze/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/media-inspect/SKILL.md`.
2. Identify source format from file extension + magic bytes (`file <source>`). Don't trust extension alone — `.xml` could be FCPXML, Premiere XML, or Resolve XML, each with different schemas.
3. Run `otio --inspect <source>` to enumerate clips, transitions, audio/video tracks, gaps, effects, color metadata.
4. **STOP** if source contains effects/transitions that don't translate to target (e.g. Resolve color correction nodes don't survive to Premiere XML; flag and ask whether to drop or render).
5. For each referenced media clip, verify file exists at the path the timeline references. If not, apply `relink_strategy`:
   - `exact-path` → fail with list of missing files.
   - `filename-match` → search `media_root` recursively for matching filenames.
   - `metadata-match` → use ExifTool/MediaInfo timecode + duration matching.
6. If `frame_rate` differs from source: insert pull-down or speed-ramp per OTIO transforms (NOT trivial; flag if motion-effect interpretation differs across target NLEs).
7. Run `otio -i <source> -o <target>` for the conversion. For multi-target export, run once per target.
8. Validate target file: for FCPXML, schema-validate against Apple's DTD; for AAF, run `aaf-info` to confirm clip/track count matches source; for EDL, verify cut count matches.
9. Generate a translation report: clips that perfectly converted, clips that lost data (which effects/markers/colors didn't translate), unresolved media references.
10. Write `summary.md` with translation report + path to each target file.

## Output schema

```markdown
# Editorial interchange — {slug} — {date}

## Conversion
- **Source format**: {FCPXML / AAF / EDL / OTIO / ...}
- **Source NLE**: {Premiere / Resolve / Avid / FCP / inferred}
- **Target format(s)**: {list}
- **Source clip count**: {N video / N audio}
- **Source duration**: {hh:mm:ss}

## Media relink
- **Strategy used**: {exact-path / filename-match / metadata-match}
- **Resolved**: {N / total}
- **Unresolved**: {list with last-known paths}

## Translation report
| Element | Source | Target | Status |
|---|---|---|---|
| Video tracks | {N} | {N} | ✓ |
| Audio tracks | {N} | {N} | ✓ |
| Transitions | {N} | {N} | ✓ / partial / lost |
| Color corrections | {Y/N} | {Y/N} | ✓ / partial / lost |
| Effects | {N} | {N} | ✓ / partial / lost |
| Markers | {N} | {N} | ✓ |

## Output files
- {target-1}: {path}
- {target-2}: {path}

## Notes for the editor
- {gotchas the receiving NLE will hit}
```

## Quality bar

- Clip count and track structure preserve through conversion (1:1 unless explicitly noted lost).
- Timecode is preserved (drop-frame ↔ non-drop-frame handled explicitly, not silently coerced).
- Unresolved media files are surfaced — never silently dropped.
- Effects/colors that don't translate are listed in the translation report, not pretended to convert.
- Frame rate conversions explicitly named (pull-down vs speed-ramp vs frame-blend) so the receiving editor knows what to expect.

## Playbook reference (folded from workflow-editorial-interchange)

**What:** Translate a cut from one NLE to another without losing edits, media references, timecode, or rate-conformed proxies.

### Pipeline

#### Step 1 — Identify source + target NLE formats

| NLE | Export format(s) |
|---|---|
| Premiere | FCP7 XML, AAF |
| Final Cut Pro X | FCPXML |
| DaVinci Resolve | DRP (binary), FCPXML, AAF, EDL |
| Avid | AAF (OP-Atom MXF) |
| Lightworks | AAF, EDL (CMX3600) |

FCP7 XML and FCPXML are DIFFERENT schemas (use `fcp_xml` vs `fcpx_xml` OTIO adapters).

#### Step 2 — Convert through OTIO pivot

Use `otio`. OTIO is the lossless-enough pivot format. `otio` has the adapter matrix.

#### Step 3 — Extract media dependencies

Use OTIO's `list-media` to get the source-clip manifest with in/out points. Cross-check with `ffmpeg-analyze` for actual stream specs per source.

#### Step 4 — Verify + conform rates

Mixed-rate timelines are the #1 interchange break. Use `media-inspect` for deep diagnostics. If conform is needed, batch-transcode with `ffmpeg-encode` + `ffmpeg-encode` to a single mezzanine codec (ProRes 422 HQ or DNxHR HQ).

#### Step 5 — Remap media paths in OTIO

If conformed media moves, use `otio`'s remap-media operation so the target NLE resolves the new paths.

#### Step 6 — Generate proxies (optional, for offline edit)

Hardware-accelerated H.264 proxies with `-r` matching source exactly. Link via proxy-suffix convention (`<original>-proxy.mov` or NLE-specific naming).

#### Step 7 — Package for target NLE

- **Avid** — AAF + DNxHR MXF OP-Atom (one file per essence track).
- **Resolve** — FCPXML or DRP (DRP is opaque; use FCPXML if round-tripping).
- **Premiere** — FCP7 XML or FCPXML.
- **Final Cut Pro X** — FCPXML only.

#### Step 8 — Validate on target

Import, verify: clip count, total duration, transitions, audio track count, levels. Spot-check 3–5 cut points at known timecodes.

### Variants

- **EDL-only (CMX3600)** — legacy/archival. Cuts + basic transitions only. No effects, no subclip data.
- **Round-trip sanity check** — A → B → A, diff to reveal lossy steps.
- **Mixed-rate conform** — 29.97 → 23.976 via `ffmpeg-restore` or frame-rate conversion.
- **Preserve timecode through conform** — `ffprobe` extract start timecode, pass to encode via `-timecode`.
- **MKV chaptered master** — `media-package` for chapter split, `ffmpeg-subtitle` extract, package per NLE.
- **Fragmented MP4 for CMAF** — `media-package` with 4000 ms fragments for ABR downstream.

### Gotchas

- **FCP7 XML ≠ FCPXML.** Legacy vs X/10.x schema. Different OTIO adapters (`fcp_xml` vs `fcpx_xml`). Mixing loses structure.
- **AAF is a container, not a codec.** It may wrap MXF essence. Always inspect with `media-inspect` to see what's actually inside.
- **Avid MXF is OP-Atom, not OP1a.** Each essence track is a separate file. Use `-f mxf_opatom`.
- **OTIO preserves timeline structure, not media.** If media moves, `remap-media` or every clip goes offline.
- **Effects don't round-trip.** Vendor-specific effects collapse to "unknown". Budget manual re-creation.
- **Frame rate determines timecode.** 23.976p with 29.97 DF reel numbering is ambiguous — verify via `media-inspect`.
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

### Example — Premiere cut → Resolve for finishing

`otio --input premiere.xml --output-format fcpx_xml > resolve.fcpxml`. Verify media resolves, batch-transcode mixed-rate clips to ProRes 422 HQ proxies with `ffmpeg-encode` + `ffmpeg-encode`. Re-open in Resolve; spot-check timecode-critical cuts.
