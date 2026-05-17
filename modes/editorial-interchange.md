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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-editorial-interchange/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/otio-convert/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-probe/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/media-mediainfo/SKILL.md`.
2. Identify source format from file extension + magic bytes (`file <source>`). Don't trust extension alone — `.xml` could be FCPXML, Premiere XML, or Resolve XML, each with different schemas.
3. Run `otio-convert --inspect <source>` to enumerate clips, transitions, audio/video tracks, gaps, effects, color metadata.
4. **STOP** if source contains effects/transitions that don't translate to target (e.g. Resolve color correction nodes don't survive to Premiere XML; flag and ask whether to drop or render).
5. For each referenced media clip, verify file exists at the path the timeline references. If not, apply `relink_strategy`:
   - `exact-path` → fail with list of missing files.
   - `filename-match` → search `media_root` recursively for matching filenames.
   - `metadata-match` → use ExifTool/MediaInfo timecode + duration matching.
6. If `frame_rate` differs from source: insert pull-down or speed-ramp per OTIO transforms (NOT trivial; flag if motion-effect interpretation differs across target NLEs).
7. Run `otio-convert -i <source> -o <target>` for the conversion. For multi-target export, run once per target.
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
