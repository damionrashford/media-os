---
name: media-inspect
description: >
  Inspect and edit media metadata. Use when the user asks to get detailed media info, check codec profile or level, inspect HDR10 or HDR10+ or Dolby Vision metadata, analyze bitrate distribution, see GOP structure, diagnose a container, run a Netflix delivery pre-flight, get broadcast media diagnostics, read EXIF tags, edit photo metadata, strip GPS data from images, write IPTC keywords, set camera model, shift timestamps across a folder, copy metadata between files, write XMP sidecar files, batch-rename by capture date, or audit EXIF, IPTC, XMP, or maker-note metadata on photos and videos.
argument-hint: "[file]"
---

# Media Inspect

**Context:** $ARGUMENTS

Two inspection engines under one roof: MediaInfo for deep container/stream analysis (codec profiles, HDR, GOP, broadcast QC) and ExifTool for reading/writing EXIF/IPTC/XMP/GPS/maker-note metadata on photos and videos.

## When to use

- Container-level detail ffprobe omits: MP4 atoms, MKV clusters, MXF operational patterns, CMAF moof/mdat structure, GOP structure, codec profile/level strings.
- HDR static/dynamic metadata verification and Dolby Vision profile disambiguation (DV5 / DV7 / DV8.1 / DV8.4).
- Broadcast QC and multi-file delivery audits (e.g. Netflix 4K HDR pre-flight).
- Reading or editing EXIF / IPTC / XMP / GPS metadata on JPEG, TIFF, HEIC, RAW, PNG, PDF, MOV, MP4.
- Scrubbing GPS or all metadata before publishing; copying tags between files; writing XMP sidecars.
- Fixing capture timestamps (camera clock drift) or batch-renaming a folder by `DateTimeOriginal`.

## Techniques

- Read `references/mediainfo.md` when inspecting containers, codec profiles/levels, GOP structure, HDR10/HDR10+/HLG/Dolby Vision metadata, audio channel layouts, or running broadcast/Netflix delivery checks.
- Read `references/mediainfo-tags.md` when you need the MediaInfo vs ffprobe `%Field%` name crosswalk.
- Read `references/exiftool.md` when reading or writing EXIF/IPTC/XMP/GPS/maker-note tags, stripping metadata, copying tags, shifting dates, writing sidecars, or batch-renaming by capture date.
- Read `references/exiftool-tags.md` when you need the ExifTool tag-group list, format support matrix, date/GPS conventions, or recipe book.

## Gotchas

- **MediaInfo beats ffprobe for container-level info.** MP4 atom types, MKV clusters, fragmented-MP4 moof/mdat, MXF operational pattern — visible in MediaInfo, omitted by ffprobe.
- **HDR10 static metadata lives in MediaInfo `--Full`** (`MasteringDisplay_ColorPrimaries`, `MaxCLL`, `MaxFALL`); ffprobe only surfaces it via expensive `-show_frames` decode. Dolby Vision profile (5/7/8.1/8.4) reporting is reliable in MediaInfo.
- **MediaInfo JSON schema is stable across versions; human output is not.** Use JSON for automation. `%Field%` names are MediaInfo's, not ffprobe's — `%Width%` not `width`.
- **ExifTool `-overwrite_original` skips the `_original` backup but is DANGEROUS** — verify on a copy first. `-P` preserves file mtime; without it every write stamps mtime to "now".
- **ExifTool tag groups are distinct fields.** `-XMP:Creator`, `-IPTC:By-line`, `-EXIF:Artist` are three separate tags on one image — write all three for Lightroom/Bridge/Finder interop.
- **ExifTool date format is colons** (`YYYY:MM:DD HH:MM:SS`); dashes fail silently. `AllDates` = `DateTimeOriginal + CreateDate + ModifyDate`.
- **GPS writes need Ref tags.** `GPSLatitude` without `GPSLatitudeRef=N` is ambiguous; map tools show (0,0). XMP is writable almost everywhere; EXIF is restricted to JPEG/TIFF/HEIC/RAW.
- **Some MediaInfo fields need bitstream metadata** (SPS/PPS/VPS). If muxed without them, re-run with `--Full` or fall back to ffprobe for bitstream-derived values.

## Scripts

- `scripts/mediainfo.py` — subcommands `check`, `summary`, `json`, `field`, `hdr`, `codec-profile`, `compare`, `netflix-check`. `hdr` returns SDR/HDR10/HDR10+/HLG/DolbyVision verdict. Supports `--dry-run`/`--verbose`.
- `scripts/exif.py` — subcommands `read`, `write`, `strip`, `copy`, `shift-dates`, `gps`, `extract-thumbnail`, `batch-rename`, `sidecar`. Supports `--dry-run`/`--verbose`. Stdlib only.

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/media-inspect/scripts/mediainfo.py hdr --input in.mkv
uv run ${CLAUDE_PLUGIN_ROOT}/skills/media-inspect/scripts/mediainfo.py netflix-check --input master.mxf
uv run ${CLAUDE_PLUGIN_ROOT}/skills/media-inspect/scripts/exif.py read --input in.jpg --json
uv run ${CLAUDE_PLUGIN_ROOT}/skills/media-inspect/scripts/exif.py strip --input in.jpg --gps-only --preserve-mtime
```
