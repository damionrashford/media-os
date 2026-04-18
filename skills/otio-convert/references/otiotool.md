# otiotool — Transform Catalog

`otiotool` is OTIO's filter/edit CLI. Input an OTIO, apply transforms, write OTIO.
Authoritative reference: `otiotool --help`.

## Track operations

| Flag | Effect |
|---|---|
| `--flatten video` | Collapse all video tracks into a single track. |
| `--flatten audio` | Collapse all audio tracks into a single track. |
| `--only-tracks-with-kind KIND` | Keep only `Video` or `Audio`. |
| `--only-tracks-with-name NAME` | Regex-match track names. |
| `--only-clips-with-name NAME` | Regex-match clip names (case-sensitive). |

## Trimming

| Flag | Effect |
|---|---|
| `--trim START END` | Crop global timeline to a `TimeRange`. |
| `--keep-drop-frames` | Preserve drop-frame timecode on export. |

## Cleanup

| Flag | Effect |
|---|---|
| `--remove-transitions` | Drop all `Transition` objects. |
| `--remove-markers` | Drop all `Marker` objects. |
| `--redact` | Strip clip names — useful for sharing timelines without leaking file paths. |

## Media references

| Flag | Effect |
|---|---|
| `--copy-media-refs-from FILE.otio` | Import `MediaReference`s from another timeline (by matching clip name). |
| `--media-linker NAME` | Run a media linker plugin to resolve `MissingReference`s. |

## Output control

| Flag | Effect |
|---|---|
| `--output PATH` | Write result to `PATH` (also available as `-o`). |
| `--output-format JSON` | Force output format even if extension doesn't match. |

## Examples

```bash
# Flatten video + strip transitions for a clean EDL-ready cut
otiotool -i edit.otio -o flat.otio --flatten video --remove-transitions

# Trim to a range (first 30 seconds at 24fps)
otiotool -i edit.otio -o trimmed.otio --trim "0@24" "720@24"

# Redact names before sharing
otiotool -i edit.otio -o shared.otio --redact
```

## Via the wrapper

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py tool \
  --input edit.otio --output flat.otio \
  -- --flatten video --remove-transitions
```

Everything after `--` goes straight to `otiotool`.
