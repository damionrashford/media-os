# Mode: acquisition-archive

**Subagent**: `probe`
**Trigger phrases**: "ingest these", "probe this folder", "archive", "preserve metadata", "verify hash", "checksum tree", "batch probe", "tether DSLR", "gphoto2", "ingest from card", "camera ingest"
**Output**: `${MEDIA_WORK_DIR}/modes/acquisition-archive/{date}_{slug}/`

## Inputs

- **Required**:
  - `task` — `probe-batch`, `ingest-card`, `tether-capture`, `archive-verify`.
  - `source` — directory path (for `probe-batch` / `archive-verify`) OR card mount point (for `ingest-card`) OR camera device (for `tether-capture`).
- **Optional**:
  - `destination` — archive root (default: `${MEDIA_WORK_DIR}/archive/`).
  - `hash_algo` — `xxh3` (default, fast) / `sha256` (default for long-term archive).
  - `skip_existing` — boolean (default: `true`).
  - `tether_settings` — for `tether-capture`: ISO, aperture, shutter, format (RAW+JPEG).

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-acquisition-archive/SKILL.md`. Read tool skills: `ffmpeg-probe`, `media-mediainfo`, `media-exiftool`, `gphoto2-tether` (for tether), `decklink-tools` (for SDI capture), `media-batch` (for parallel probe).
2. Branch by `task`:
   - **`probe-batch`**: For each media file in `source` (recursive), run `moprobe --json <file>` and `exiftool -j <file>`. Store both in a flat NDJSON at `<destination>/manifest.ndjson` keyed by path. Compute hash per `hash_algo`.
   - **`ingest-card`**: Validate card mount point. Walk DCIM/MISC/CLIP directories per common camera layouts (Sony XAVC, Canon CR3, RED R3D, ARRI MXF, GoPro MP4). Copy with verify-after-copy (read back, hash-check). Append to manifest.
   - **`tether-capture`**: For DSLR (Canon EOS / Nikon Z / Sony α): use `gphoto2 --capture-image-and-download --config iso=<n>` etc. For broadcast SDI: use `BMDStreamingServer` with DeckLink.
   - **`archive-verify`**: Walk archive root; for each file in `manifest.ndjson`, recompute hash and compare. Report mismatches as corruption candidates.
3. For media files (video / image / audio): always include in manifest:
   - File path (relative to archive root).
   - File size + mtime.
   - Hash (`xxh3` for fast, `sha256` for long-term).
   - Full `ffprobe -show_streams -show_format` JSON.
   - Full `exiftool -j` JSON (covers EXIF, IPTC, XMP, MakerNotes).
   - For video: SMPTE timecode if present, GOP count, color metadata.
4. **STOP** for `ingest-card` if card removed mid-copy (file not readable) — never silently truncate.
5. Run `media-batch` for parallel probe if file count > 100 (use GNU parallel; `parallel -j 4 moprobe ::: *.mxf`).
6. For `archive-verify`: surface ANY hash mismatch as a critical finding — could be silent disk corruption (bit rot).
7. Write `summary.md` with file count, total bytes, hash algo, manifest path, any failures or anomalies.

## Output schema

```markdown
# Acquisition + archive — {slug} — {date}

## Task
**{probe-batch / ingest-card / tether-capture / archive-verify}**

## Source
- **Path / device**: {source}
- **File count**: {N}
- **Total size**: {bytes / GB}

## Destination
- **Archive root**: {destination}
- **Manifest**: {destination}/manifest.ndjson

## Processing
- **Hash algorithm**: {xxh3 / sha256}
- **Skip existing**: {true / false}
- **Parallel jobs**: {N}
- **Started / completed**: {timestamps}
- **Duration**: {hh:mm:ss}

## Results
| Status | Count | Notes |
|---|---|---|
| Ingested | {N} | Fresh copies, hash verified |
| Skipped | {N} | Existing with matching hash |
| Updated | {N} | Existing with different hash — kept old, copied new with `.dup` suffix |
| Failed | {N} | See `failures.log` |

## Manifest sample
```ndjson
{"path":"...","size":...,"hash":"...","mtime":"...","ffprobe":{...},"exiftool":{...}}
```

## Anomalies
- {file path} — {what was wrong: hash mismatch, missing timecode, EXIF date in future, ...}

## Archive integrity (task=archive-verify)
- **Files checked**: {N}
- **Hash mismatches**: {N} — {list of paths}
- **Verdict**: {clean / N corruption candidates / archive root unreachable}
```

## Quality bar

- Every file has hash in manifest — no entries with `null` or missing hash.
- For `ingest-card`: copy is verify-after-copy (read back + hash compare); files that fail verify are surfaced, not silently kept.
- For `archive-verify`: ANY hash mismatch surfaces as a critical finding.
- For `tether-capture`: gphoto2 errors (camera lost, card full, write error) surface immediately, not buried in a log.
- Manifest is line-delimited JSON (one record per line) for streaming-friendly downstream tools.
- Re-running `probe-batch` with `skip_existing=true` is idempotent — only new/changed files are re-probed.
