---
name: media-exiftool
description: >
  Read and write EXIF, IPTC, XMP, GPS, and maker-note metadata for photos and videos with ExifTool (exiftool -g -json -P -overwrite_original). Use when the user asks to read EXIF tags, edit photo metadata, strip GPS data from images, write IPTC keywords, set camera model, shift timestamps across a folder, copy metadata between files, write XMP sidecar files, or batch-rewrite metadata.
argument-hint: "[operation] [file]"
---

# Media Exiftool

**Context:** $ARGUMENTS

ExifTool (by Phil Harvey) is the de facto standard for reading and writing metadata in images, RAW files, video, PDFs, and audio. It handles EXIF, IPTC, XMP, GPS, MakerNotes, QuickTime atoms, ID3, and hundreds of vendor-specific tags.

## Quick start

- **Dump everything grouped:** `exiftool -g1 in.jpg` → Step 2, read
- **Machine-readable JSON:** `exiftool -j in.jpg` → Step 2, read
- **Write a tag safely:** `exiftool -P -overwrite_original -Artist="Alice" in.jpg` → Step 2, write
- **Nuke all metadata:** `exiftool -all= -overwrite_original in.jpg` → Step 2, strip
- **Copy metadata src → dst:** `exiftool -TagsFromFile src.jpg dst.jpg` → Step 2, copy
- **Shift dates +1h:** `exiftool "-AllDates+=0:0:0 1:0:0" *.jpg` → Step 2, shift

## When to use

- Auditing or editing EXIF/IPTC/XMP on JPEG, TIFF, HEIC, RAW, PNG, PDF
- Scrubbing GPS or all metadata before publishing photos
- Copying tags between a RAW and its JPEG sibling, or writing XMP sidecars
- Rewriting capture timestamps after a camera clock mishap
- Batch-renaming a folder by `DateTimeOriginal`
- Tagging IPTC keywords / XMP ratings for a DAM workflow
- Inspecting or editing QuickTime metadata in MOV/MP4 (including GoPro maker-notes)

## Step 1 — Install

Pick one:

```bash
# macOS (Homebrew)
brew install exiftool

# Debian / Ubuntu
sudo apt install libimage-exiftool-perl

# Verify
exiftool -ver    # expect 12.x or 13.x
```

ExifTool is a Perl script — `perl` must be present (it is on macOS and most Linux).

## Step 2 — Pick an operation

| Op         | When                                               | Core command                                                    |
| ---------- | -------------------------------------------------- | --------------------------------------------------------------- |
| read       | You need to see tags                               | `exiftool -g1 in.jpg` or `exiftool -j in.jpg`                   |
| write      | You need to set or change one or more tags         | `exiftool -P -overwrite_original -Tag=Value in.jpg`             |
| strip      | You need to remove metadata (e.g., before posting) | `exiftool -all= -overwrite_original in.jpg`                     |
| copy       | You need to transfer tags from one file to another | `exiftool -TagsFromFile src.jpg dst.jpg`                        |
| shift      | You need to correct camera clock drift             | `exiftool "-AllDates+=0:0:0 1:0:0" *.jpg`                       |
| gps        | You need to add/remove location                    | `exiftool -GPSLatitude=... -GPSLongitude=... in.jpg`            |
| extract    | You need the embedded thumbnail or preview         | `exiftool -b -ThumbnailImage in.jpg > thumb.jpg`                |
| sidecar    | You need metadata beside (not inside) the file     | `exiftool -o dst.xmp -tagsFromFile src.jpg`                     |
| rename     | You need filenames derived from capture date       | `exiftool '-FileName<DateTimeOriginal' -d '%Y%m%d_%H%M%S.%%le'` |

## Step 3 — Run

### Read

```bash
exiftool -g1 in.jpg                       # grouped by family-1 tag group
exiftool -j in.jpg                        # JSON (always a single-element array)
exiftool -s -s -s -CreateDate in.jpg      # ultra-short: value only
exiftool -CreateDate -ImageWidth -ImageHeight in.jpg
exiftool -n in.jpg                        # numeric/raw values (no pretty formatting)
exiftool -t in.jpg                        # tab-separated
exiftool -r photos/                       # recurse a directory
```

### Write

```bash
# Single tag
exiftool -P -overwrite_original -Artist="Alice" in.jpg

# Multiple tags in one invocation (one pass is always faster)
exiftool -P -overwrite_original \
  -Artist="Alice" \
  -Copyright="(c) 2026 Alice" \
  -XMP:Rating=5 \
  in.jpg

# Append vs replace on list tags (IPTC keywords)
exiftool -P -overwrite_original -Keywords+="sunset" -Keywords+="beach" in.jpg   # append
exiftool -P -overwrite_original -Keywords="sunset"                      in.jpg   # replace
exiftool -P -overwrite_original -Keywords-="badtag"                     in.jpg   # remove one

# Set group explicitly (tags with the same short name exist in EXIF, XMP, IPTC)
exiftool -P -overwrite_original -XMP:Creator="Alice" -IPTC:By-line="Alice" -EXIF:Artist="Alice" in.jpg
```

`-P` preserves the filesystem mtime (otherwise ExifTool updates it to "now"). `-overwrite_original` skips the default `in.jpg_original` backup — only use after you have verified the command works on a copy.

### Strip

```bash
exiftool -all= -overwrite_original in.jpg                 # everything (DESTRUCTIVE)
exiftool -gps:all= -overwrite_original in.jpg             # GPS group only
exiftool -exif:all= -overwrite_original in.jpg            # EXIF only, keep XMP/IPTC
exiftool -all= -tagsfromfile @ -orientation in.jpg        # strip all, restore orientation
```

### Copy

```bash
exiftool -TagsFromFile src.jpg dst.jpg                                  # all writable tags
exiftool -TagsFromFile src.jpg "-DateTimeOriginal" "-Make" "-Model" dst.jpg
exiftool -TagsFromFile src.jpg -all:all dst.jpg                         # every group
```

### Shift dates

```bash
exiftool "-AllDates+=0:0:0 1:0:0"  *.jpg          # +1 hour
exiftool "-AllDates-=0:0:1 0:0:0"  *.jpg          # -1 day
exiftool "-AllDates+=0:0:0 0:30:0" -if '$make eq "Apple"' *.jpg
```

`AllDates` is a convenience shortcut for `DateTimeOriginal + CreateDate + ModifyDate`. Date format is `YYYY:MM:DD HH:MM:SS` (colons, not dashes).

### GPS

```bash
exiftool -GPSLatitude=37.7749 -GPSLongitude=-122.4194 \
         -GPSLatitudeRef=N    -GPSLongitudeRef=W     \
         in.jpg
```

Write decimal latitude/longitude; the Ref tags (N/S for latitude, E/W for longitude) must be set too. ExifTool returns DMS on read unless you pass `-n`.

### Extract thumbnail / preview

```bash
exiftool -b -ThumbnailImage in.jpg  > thumb.jpg
exiftool -b -PreviewImage   in.cr2  > preview.jpg
exiftool -b -JpgFromRaw     in.nef  > full.jpg
```

### XMP sidecar

```bash
exiftool -o dst.xmp -tagsFromFile src.jpg         # create sidecar from image
exiftool -tagsfromfile src.xmp dst.jpg            # apply sidecar to image
```

### Batch rename by capture date

```bash
exiftool '-FileName<DateTimeOriginal' -d '%Y%m%d_%H%M%S.%%le' *.jpg
# %%le = lowercase file extension; ExifTool interprets the outer %-codes, so double them.
```

## Step 4 — Verify

Always read back after a write:

```bash
exiftool -G1 -a -s -Artist -Copyright -XMP:Rating in.jpg
```

For full roundtrip integrity: `exiftool -validate -warning -a in.jpg`.

## Available scripts

- **`scripts/exif.py`** — argparse wrapper over exiftool for `read`, `write`, `strip`, `copy`, `shift-dates`, `gps`, `extract-thumbnail`, `batch-rename`, `sidecar`. Supports `--dry-run` and `--verbose`. Stdlib only.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/exif.py read  --input in.jpg --json
uv run ${CLAUDE_SKILL_DIR}/scripts/exif.py write --input in.jpg --set "Artist=Alice" --set "Copyright=(c) 2026" --preserve-mtime
uv run ${CLAUDE_SKILL_DIR}/scripts/exif.py strip --input in.jpg --gps-only --preserve-mtime
uv run ${CLAUDE_SKILL_DIR}/scripts/exif.py shift-dates --input ./trip --delta "0:0:0 1:0:0"
uv run ${CLAUDE_SKILL_DIR}/scripts/exif.py batch-rename --dir ./trip --pattern DateTimeOriginal --format "%Y%m%d_%H%M%S.%%le"
```

## Reference docs

- Read [`references/exiftool.md`](references/exiftool.md) for tag groups, format support matrix, date/GPS conventions, and the recipe book.

## Gotchas

- **Perl dependency:** ExifTool is a Perl script. `perl` must be on `$PATH` (default on macOS and Linux; on Windows use the Strawberry build).
- **Backup file by default:** every write creates `file.jpg_original` unless you pass `-overwrite_original`. That flag is fast but DANGEROUS — always verify on one file first, or keep your own backup tree.
- **`-P` preserves file mtime.** Without it, ExifTool sets the file's mtime to "now" on every write, which ruins date-based sorting.
- **Tag groups are distinct.** `-XMP:Creator`, `-IPTC:By-line`, and `-EXIF:Artist` are three separate fields on the same image. Write all three when you care about cross-tool interop (Lightroom, Bridge, Finder all look at different ones).
- **XMP is writable on almost everything** — JPEG, TIFF, PDF, MP4, MOV, PSD, HEIC. EXIF is more restricted (largely JPEG/TIFF/HEIC/RAW).
- **Date format is colons.** `YYYY:MM:DD HH:MM:SS` — dashes will fail silently on some tags.
- **`AllDates` is a shortcut** for `DateTimeOriginal + CreateDate + ModifyDate`. `-FileModifyDate` is the filesystem mtime and is separate.
- **GPS needs Ref tags.** Writing `GPSLatitude=37.7749` without `GPSLatitudeRef=N` is ambiguous; some readers will treat it as unsigned.
- **`-n` for numeric output** when piping to another tool — ExifTool's default formatting is human-friendly, not machine-friendly.
- **`-s -s -s`** gives tag value only, no tag name or group. Useful for `$(exiftool -s3 -CreateDate in.jpg)`.
- **`-@ args.txt`** reads arguments from a file — use for long arg lists or to avoid shell quoting hell. `-TagsFromFile` with `-@` reads JSON.
- **MakerNotes are vendor-specific.** Editing Canon/Nikon/Sony/GoPro maker-notes can break vendor tools that re-read them. ExifTool preserves structure better than most, but still: back up.
- **HEIC is supported** (read and write, metadata only — not image data).
- **MKV metadata support is limited** — use `mkvpropedit` for MKV. QuickTime atoms (MP4/MOV) are fully writable.
- **Filter batches with `-if`:** `exiftool -if '$make eq "Apple"' -TagsFromFile ... -r folder/`. Faster than xargs piping.
- **Lightroom/PhotoMechanic/FastStone can collide.** Close them before batch writes — they cache sidecars and may overwrite your changes.
- **Sidecars vs embedded:** when a `.xmp` sidecar exists next to a file, some tools prefer it over the embedded XMP. Decide which is authoritative and stick with it.

## Examples

### Example 1: strip GPS before posting a photo online

```bash
exiftool -P -overwrite_original -gps:all= -xmp:geotag= vacation.jpg
exiftool -g1 -a -s vacation.jpg | grep -i gps    # verify empty
```

### Example 2: copy RAW tags onto the exported JPEG

```bash
exiftool -TagsFromFile IMG_0001.CR2 -all:all --orientation --thumbnailimage IMG_0001.jpg
# --orientation and --thumbnailimage mean "except these" (don't overwrite orientation/thumb on dst).
```

### Example 3: batch-fix a 1-hour camera-clock offset across a trip folder

```bash
exiftool -P -overwrite_original -r "-AllDates+=0:0:0 1:0:0" ./trip_photos/
```

### Example 4: rename files to `YYYYMMDD_HHMMSS.ext` based on capture time

```bash
exiftool '-FileName<DateTimeOriginal' -d '%Y%m%d_%H%M%S%%-c.%%le' -r ./imports/
# %%-c appends -1, -2, etc. on collisions.
```

### Example 5: write a full copyright block

```bash
exiftool -P -overwrite_original \
  -EXIF:Artist="Alice Example" \
  -XMP:Creator="Alice Example" \
  -IPTC:By-line="Alice Example" \
  -XMP:Rights="(c) 2026 Alice Example. All rights reserved." \
  -IPTC:CopyrightNotice="(c) 2026 Alice Example" \
  -EXIF:Copyright="(c) 2026 Alice Example" \
  portfolio/*.jpg
```

### Example 6: audit what's inside a HEIC

```bash
exiftool -g1 -a IMG_1234.HEIC
exiftool -j -struct IMG_1234.HEIC | jq .
```

## Troubleshooting

### Error: `Error: Not a valid TAG=VALUE pair`

Cause: stray shell glob, unquoted special character, or using `=` inside the value without quoting.
Solution: quote the whole assignment: `-Comment="Shot at f/2.8"`.

### Error: `Warning: Sorry, ... is not writable`

Cause: the tag group doesn't exist in that file type (e.g., writing EXIF to a PNG).
Solution: write to XMP instead: `-XMP:Artist="Alice"`.

### File has `_original` suffix everywhere after a batch

Cause: forgot `-overwrite_original`.
Solution: either delete the originals after verifying (`find . -name '*_original' -delete`) or rerun with `-overwrite_original` next time. Keep your own backup first.

### Dates written but Finder/Lightroom still shows old value

Cause: tool reads `FileModifyDate` or a sidecar, not embedded EXIF.
Solution: also set `-FileModifyDate`, or delete the stale `.xmp` sidecar.

### GPS writes succeed but map tools show (0, 0)

Cause: missing `GPSLatitudeRef` / `GPSLongitudeRef`.
Solution: always write both Ref tags alongside the coordinate values.

### `exiftool: command not found`

Cause: not installed, or installed for a different Perl.
Solution: `brew install exiftool` (macOS) / `apt install libimage-exiftool-perl` (Debian). Verify `perl -v` works.
