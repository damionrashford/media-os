---
name: media-package
description: >
  Use when the user asks to package DRM, build encrypted DASH or HLS, do multi-DRM CMAF, integrate a Widevine, PlayReady, or FairPlay license server, ship studio-grade DRM-protected content, package CENC with PSSH boxes, do key rotation, or use Shaka Packager; or to use MP4Box or gpac, fragment an MP4, build fragmented fMP4, extract a track by ID, dump MP4 box structure, inject sidx indexing, CMAF-package for DASH, ClearKey CENC encrypt, repair an MP4 ffmpeg cannot, or do advanced ISO-BMFF box surgery; or to use MKVToolNix, mkvmerge, mkvextract, mkvpropedit, or mkvinfo, split or merge MKV without re-encode, extract a track (audio, subs, attachment), edit MKV chapter names, change default or forced track flags, fix MKV metadata without re-encoding, add fonts or cover art, or demux MKV.
argument-hint: "[operation] [input]"
---

# Media Package

**Context:** $ARGUMENTS

Container authoring, fragmentation, and DRM packaging for delivery. Three tools, one
skill: **MKVToolNix** (lossless Matroska editing), **GPAC/MP4Box** (ISO-BMFF surgery +
DASH/CMAF + CENC), and **Shaka Packager** (commercial multi-DRM). None of these
re-encode — encode first with ffmpeg, then package here.

## When to use

- Lossless MKV editing: split/merge without re-encode, extract tracks, edit chapters,
  flip default/forced flags, add font/cover attachments, fix metadata in place.
- ISO-BMFF surgery ffmpeg can't express: box-level edits, precise track IDs, edit-list
  fixes, sidx injection, repairing broken moov/moof.
- Fragmented MP4 + DASH/CMAF packaging where fragment timing must be accurate.
- ClearKey CENC encryption for pipeline testing.
- Commercial DRM: Widevine / PlayReady / FairPlay, multi-DRM CMAF, key rotation,
  license-server integration, PSSH boxes, SCTE-35/EMSG passthrough.
- Skip if: you need to re-encode, filter, or stabilize — do that in ffmpeg first.

Tool picker:

| Need | Tool | Read |
|------|------|------|
| MKV split/merge/extract/metadata (no re-encode) | mkvmerge/mkvextract/mkvpropedit | `references/mkvtoolnix.md` |
| MP4/ISO-BMFF surgery, fragment, DASH, CENC | MP4Box/gpac | `references/gpac.md` |
| Commercial Widevine/PlayReady/FairPlay multi-DRM | Shaka Packager | `references/shaka.md` |

## Techniques

- Read `references/mkvtoolnix.md` when the task is lossless Matroska work — splitting,
  merging, appending, extracting raw tracks, editing chapters/tags, changing
  default/forced flags, or managing font/cover attachments without re-muxing.
- Read `references/gpac.md` when doing ISO-BMFF box surgery, fragmenting an MP4,
  packaging DASH/CMAF, injecting sidx, repairing a stream ffmpeg can't, or authoring
  ClearKey CENC content.
- Read `references/shaka.md` when packaging commercial DRM — Widevine, PlayReady,
  FairPlay, multi-DRM CMAF DASH+HLS, key rotation, or license-server integration.
- Read `references/mkvtoolnix-reference.md` for the full MKVToolNix option catalog
  (split syntax, track selector grammar, flag/language/MIME tables, chapter XML schema).
- Read `references/gpac-reference.md` for the GPAC option catalog (DASH profiles,
  ISO-BMFF box reference, CENC XML schema, MP4Box→gpac filter-graph translation).
- Read `references/shaka-reference.md` for the Shaka option catalog (protection-scheme
  matrix, DRM UUIDs, stream descriptor syntax, manifest options, vendor list, PSSH).

## Gotchas

- **None of these tools re-encode.** MKVToolNix and Shaka are stream-copy only; MP4Box
  does box surgery. If the source bitrate/resolution is wrong, fix it in ffmpeg first.
- **MKVToolNix writes only Matroska/WebM.** MKV → MP4 is NOT supported — use ffmpeg
  (`ffmpeg -i in.mkv -c copy out.mp4`). mkvmerge splits are key-frame-aligned, so cuts
  land 1–2 frames off; frame-exact cuts require re-encoding.
- **MP4Box edits in place unless you pass `-out`.** Always back up or pass `-out`.
  Track IDs are 1-based (`MP4Box -info` lists them); `-raw TID` gives the raw ES.
- **DASH packaging needs `-rap`** so each segment starts on an IDR — omit it and DASH is
  unseekable. `-dash 4000` is segment ms; `sidx` is required for `onDemand` byte-range
  DASH but not for `live`.
- **`cbcs` is the modern DRM default**, not `cenc`. Widevine 14.0+, PlayReady, and
  FairPlay all support `cbcs`, so one set of `.m4s` plays everywhere. `cenc` blocks
  FairPlay — using it is the #1 cause of "iOS fails, Android works".
- **KIDs and keys are 32 hex chars (16 bytes).** Any other length silently breaks. KID
  must be unique per content — a reused KID means one revocation kills your whole catalog.
- **Shaka does CENC/commercial DRM; MP4Box does CENC but NOT license-server signaling.**
  Package box-level with MP4Box, hand commercial DRM to Shaka. Don't mix CENC auxiliary
  boxes (`senc`/`saio`/`saiz`) between tools mid-pipeline.
- **`--clear_lead N`** leaves N unencrypted seconds so playback starts before the
  license arrives (typical 10 for VOD). `drm_label` (HD/SD/UHD) must match the license
  server's content-type policy or HD playback is refused on L3 devices.

## Scripts

All stdlib-only, non-interactive, support `--dry-run` and `--verbose`.

- **`scripts/mkv.py`** — wraps mkvmerge/mkvextract/mkvpropedit/mkvinfo. Subcommands:
  `identify`, `merge`, `split-time`, `split-size`, `extract-tracks`, `extract-chapters`,
  `extract-attachments`, `edit`, `default-flag`, `add-attachment`, `replace-chapters`.
- **`scripts/gpac.py`** — wraps MP4Box. Subcommands: `check`, `info`, `diso`,
  `extract-track`, `fragment`, `dash`, `encrypt`, `decrypt`, `remove-track`, `set-lang`,
  `split-time`. Generates CENC DRM XML in a temp file.
- **`scripts/shaka.py`** — wraps `packager`. Subcommands: `check`, `gen-clearkey-keys`,
  `clearkey`, `widevine`, `multi-drm`, `fairplay-hls`.

Invoke via `${CLAUDE_PLUGIN_ROOT}/skills/media-package/scripts/<file>.py`. See the
matching `references/<tool>.md` for full command examples.
