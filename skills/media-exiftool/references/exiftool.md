# ExifTool reference

Deep reference for ExifTool (by Phil Harvey). Paired with `SKILL.md`; read this when you need tag groups, full format support, or a recipe.

---

## 1. Tag groups (family 1)

ExifTool partitions tags into groups. The same human name (e.g., `Artist`, `Creator`) can exist in multiple groups and they are treated as independent fields.

| Group          | Scope                                         | Typical containers                          |
| -------------- | --------------------------------------------- | ------------------------------------------- |
| `EXIF`         | JEITA EXIF IFD0/IFD1/ExifIFD/GPS/Interop      | JPEG, TIFF, HEIC, most RAW                  |
| `IPTC`         | IPTC IIM (legacy news-industry metadata)      | JPEG, TIFF                                  |
| `XMP`          | Adobe Extensible Metadata Platform (RDF/XML)  | JPEG, TIFF, PDF, MP4, MOV, PSD, HEIC, DNG   |
| `MakerNotes`   | Vendor maker-note sub-IFD (Canon, Nikon, ...) | JPEG, TIFF, RAW                             |
| `QuickTime`    | ISO BMFF / QuickTime atoms                    | MP4, MOV, M4A, M4V, HEIC (partial)          |
| `ID3`          | ID3v1/v2 audio tags                           | MP3, sometimes WAV (ID3 chunk)              |
| `RIFF`         | RIFF chunks (INFO, ...)                       | WAV, AVI                                    |
| `Matroska`     | EBML element metadata (read, limited write)   | MKV, WEBM (use mkvpropedit for write)       |
| `PNG`          | tEXt/zTXt/iTXt + eXIf chunk                   | PNG, APNG                                   |
| `PDF`          | PDF Info dictionary / XMP metadata stream     | PDF                                         |
| `Photoshop`    | 8BIM resource blocks                          | PSD, TIFF, JPEG                             |
| `Composite`    | virtual tags ExifTool computes (ImageSize, …) | any                                         |
| `File`         | filesystem-level (FileModifyDate, FileSize)   | any                                         |

Address a specific group on read/write with `-GROUP:Tag`, e.g. `-XMP:Creator`, `-IPTC:By-line`, `-EXIF:Artist`.

Show group on output: `exiftool -G1 -a -s in.jpg`.

---

## 2. Common tags by group

### EXIF

| Tag                  | Notes                                    |
| -------------------- | ---------------------------------------- |
| `DateTimeOriginal`   | Capture time. `YYYY:MM:DD HH:MM:SS`.     |
| `CreateDate`         | Digitization time (often same as above). |
| `ModifyDate`         | Last file modification (embedded).       |
| `Make`, `Model`      | Camera manufacturer / model.             |
| `LensModel`          | Lens name (also in MakerNotes).          |
| `ExposureTime`       | Shutter speed (1/250, etc.).             |
| `FNumber`            | Aperture.                                |
| `ISO`                | Sensor gain.                             |
| `FocalLength`        | In mm (pretty-printed); use `-n` raw.    |
| `Orientation`        | 1 = normal, 3 = 180, 6 = 90 CW, 8 = 90 CCW. |
| `Artist`             | Photographer. Separate from XMP:Creator. |
| `Copyright`          | Copyright string.                        |
| `ImageWidth`/`Height`| Pixel dimensions.                        |

### GPS (EXIF sub-group)

| Tag                 | Notes                                        |
| ------------------- | -------------------------------------------- |
| `GPSLatitude`       | Decimal degrees on write, DMS on read.       |
| `GPSLatitudeRef`    | `N` or `S`.                                  |
| `GPSLongitude`      | Decimal degrees on write, DMS on read.       |
| `GPSLongitudeRef`   | `E` or `W`.                                  |
| `GPSAltitude`       | Meters. `GPSAltitudeRef`: 0 above, 1 below.  |
| `GPSDateStamp`      | `YYYY:MM:DD`.                                |
| `GPSTimeStamp`      | `HH:MM:SS` UTC.                              |

### IPTC (legacy, still required by many DAMs)

| Tag                | Notes                                    |
| ------------------ | ---------------------------------------- |
| `By-line`          | Photographer (IPTC's "Artist").          |
| `By-lineTitle`     | Photographer's title/role.               |
| `Caption-Abstract` | Long-form description.                   |
| `Headline`         | Short headline.                          |
| `Keywords`         | LIST tag; append with `+=`, remove with `-=`. |
| `ObjectName`       | Title.                                   |
| `City`, `Province-State`, `Country-PrimaryLocationName` | Location. |
| `CopyrightNotice`  | IPTC's copyright field.                  |

### XMP (Adobe's everywhere-compatible namespace)

| Tag                 | Notes                                      |
| ------------------- | ------------------------------------------ |
| `XMP:Creator`       | Photographer (modern; preferred by Lightroom, Bridge). |
| `XMP:Title`         | Title (maps to IPTC:ObjectName in sync).   |
| `XMP:Description`   | Long description (maps to IPTC:Caption-Abstract). |
| `XMP:Subject`       | List of keywords (maps to IPTC:Keywords).  |
| `XMP:Rating`        | 0-5 stars.                                 |
| `XMP:Label`         | Color label (Red/Yellow/Green/Blue/Purple).|
| `XMP:Rights`        | Copyright string (maps to IPTC:CopyrightNotice / EXIF:Copyright). |
| `XMP:CreateDate`    | Capture date.                              |
| `XMP:MetadataDate`  | Last metadata edit.                        |

### QuickTime (MP4/MOV)

| Tag                            | Notes                            |
| ------------------------------ | -------------------------------- |
| `QuickTime:CreateDate`         | File creation.                   |
| `QuickTime:ModifyDate`         | File modification.               |
| `QuickTime:Title`              | iTunes-style title.              |
| `QuickTime:Artist`             | Artist.                          |
| `QuickTime:Description`        | Description atom.                |
| `QuickTime:GPSCoordinates`     | `+37.7749-122.4194/` ISO 6709.   |
| `QuickTime:Make`/`Model`       | Camera maker/model.              |
| `Keys:Make`, `Keys:Model`, ... | Apple "Keys" atom variants.      |

### ID3 (MP3 audio)

| Tag              | Notes                  |
| ---------------- | ---------------------- |
| `Title`          | Track title.           |
| `Artist`         | Track artist.          |
| `Album`          | Album title.           |
| `Year`           | Release year.          |
| `Track`          | Track number.          |
| `Genre`          | Genre string.          |
| `Picture`        | Embedded cover art.    |

---

## 3. Date/time format

All writable date tags use colon separators:

```
YYYY:MM:DD HH:MM:SS[.subsec][±HH:MM]
```

Examples:
- `2026:04:17 09:30:00`
- `2026:04:17 09:30:00.250`
- `2026:04:17 09:30:00+02:00`

Write a formatted string:

```bash
exiftool -DateTimeOriginal="2026:04:17 09:30:00" in.jpg
```

Read with a custom strftime (`-d`):

```bash
exiftool -DateTimeOriginal -d '%Y-%m-%d %H:%M:%S' -s3 in.jpg
# 2026-04-17 09:30:00
```

Shift by a delta (`Y:M:D h:m:s`):

```bash
exiftool "-AllDates+=0:0:0 1:0:0"   *.jpg   # +1h
exiftool "-AllDates-=0:0:1 0:0:0"   *.jpg   # -1 day
exiftool "-AllDates+=0:1:0 0:0:0"   *.jpg   # +1 month
```

`AllDates` = `DateTimeOriginal + CreateDate + ModifyDate`. It does NOT include `FileModifyDate` (filesystem mtime — use `-FileModifyDate=` explicitly).

---

## 4. GPS conventions

- Write latitude/longitude in DECIMAL degrees. ExifTool converts internally to EXIF's rational-array DMS representation.
- ALWAYS write the matching Ref tag:
  - `GPSLatitudeRef=N` (positive) or `S` (negative)
  - `GPSLongitudeRef=E` (positive) or `W` (negative)
- For negative values either pass the sign in the coordinate (ExifTool flips Ref to match) or set Ref explicitly.
- Altitude: `GPSAltitudeRef=0` above sea level, `1` below.
- Read raw decimal with `-n`: `exiftool -n -GPSLatitude -GPSLongitude in.jpg`.

ISO 6709 (used in QuickTime atoms): `+37.7749-122.4194+0.000/` — ExifTool reads/writes this correctly via `-QuickTime:GPSCoordinates`.

---

## 5. Format support matrix (key highlights)

| Format  | Read          | Write         | Notes                                         |
| ------- | ------------- | ------------- | --------------------------------------------- |
| JPEG    | full          | full          | EXIF, IPTC, XMP all writable.                 |
| TIFF    | full          | full          | Including DNG.                                |
| HEIC    | full          | full (meta)   | Image data untouched.                         |
| PNG     | EXIF/XMP/tEXt | limited       | eXIf chunk (PNG spec 1.5+) supported.         |
| RAW     | vendor-wide   | XMP + some    | Sidecars preferred for non-destructive edits. |
| MP4/MOV | full          | mostly        | QuickTime atoms writable; muxer-dependent.    |
| MKV     | good          | very limited  | Use `mkvpropedit` for reliable write.         |
| PDF     | XMP + Info    | XMP + Info    | PDF Info dictionary + embedded XMP stream.    |
| PSD     | full          | full          | Photoshop 8BIM + XMP.                         |
| MP3     | ID3v1/v2      | ID3v2         | Cover art via `Picture`.                      |
| FLAC    | Vorbis        | Vorbis        |                                               |
| WAV     | INFO/ID3/BWF  | INFO/ID3      |                                               |

For the authoritative list: https://exiftool.org/#supported

---

## 6. XMP sidecars

When embedded metadata can't be written (camera RAW, read-only formats, or to keep originals bit-exact), put it in a sibling `.xmp` file.

Create a sidecar from an image:

```bash
exiftool -o IMG_0001.xmp -tagsFromFile IMG_0001.CR2
```

Apply a sidecar back to an image:

```bash
exiftool -tagsFromFile IMG_0001.xmp IMG_0001.CR2
```

Lightroom, Bridge, Capture One, darktable all understand XMP sidecars. Convention: same basename, `.xmp` extension, next to the file.

---

## 7. Batch processing patterns

### Recursive

```bash
exiftool -r -Artist="Alice" ./imports/
```

### Filter with `-if`

```bash
exiftool -if '$make eq "Apple"' -XMP:Label="Blue" -r ./imports/
exiftool -if '$imagewidth > 4000' -Keywords+="highres" -r ./imports/
```

### Argument files

Put long arg lists in a text file (one per line) and reference with `-@`:

```
# args.txt
-Artist=Alice
-XMP:Rights=(c) 2026 Alice
-P
-overwrite_original
```

```bash
exiftool -@ args.txt *.jpg
```

### JSON import

```bash
exiftool -j -g1 in.jpg > meta.json
# edit meta.json, then:
exiftool -j=meta.json dst.jpg
```

### Parallelism

ExifTool is single-threaded Perl. To saturate cores, shard with xargs or GNU parallel:

```bash
find imports -name '*.jpg' -print0 | xargs -0 -n 50 -P 8 exiftool -P -overwrite_original -Artist=Alice
```

`-n 50` batches 50 files per invocation (reduces Perl startup overhead).

---

## 8. Recipe book

### A) Organize a trip folder

```bash
# 1. Shift camera-clock drift (example: camera was 1 hour behind).
exiftool -P -overwrite_original -r "-AllDates+=0:0:0 1:0:0" ./trip/

# 2. Geotag from a GPX track.
exiftool -geotag=track.gpx -r ./trip/

# 3. Rename deterministically by capture date.
exiftool '-FileName<DateTimeOriginal' -d '%Y%m%d_%H%M%S%%-c.%%le' -r ./trip/
```

### B) Watermark protection / copyright stamping

```bash
exiftool -P -overwrite_original \
  -EXIF:Artist="Alice Example" \
  -XMP:Creator="Alice Example" \
  -IPTC:By-line="Alice Example" \
  -EXIF:Copyright="(c) 2026 Alice Example" \
  -XMP:Rights="(c) 2026 Alice Example. All rights reserved." \
  -IPTC:CopyrightNotice="(c) 2026 Alice Example" \
  -XMP-xmpRights:WebStatement="https://example.com/license" \
  -XMP-xmpRights:Marked=True \
  -r ./portfolio/
```

### C) EXIF-based renaming (preserves uniqueness)

```bash
exiftool '-FileName<DateTimeOriginal' \
         -d '%Y/%m/%Y-%m-%d_%H%M%S%%-c.%%le' \
         -r ./ingest/
# Creates YYYY/MM/YYYY-MM-DD_HHMMSS.jpg, appending -1, -2 on collisions.
```

### D) Strip GPS (and only GPS) before posting

```bash
exiftool -P -overwrite_original -gps:all= -xmp:geotag= for-web.jpg
# Verify
exiftool -G1 -a -s for-web.jpg | grep -i gps  # expect no output
```

### E) Full metadata scrub (OpSec)

```bash
exiftool -all= -tagsfromfile @ -orientation -overwrite_original in.jpg
# Strip everything, then restore orientation so the image doesn't rotate unexpectedly.
```

### F) Transfer metadata from RAW to JPEG export

```bash
exiftool -TagsFromFile IMG_0001.CR2 \
  -all:all --thumbnailimage --previewimage --orientation \
  -P -overwrite_original IMG_0001.jpg
# --tag syntax means "except this tag".
```

### G) Build a contact-sheet CSV

```bash
exiftool -r -csv -filename -createdate -imagewidth -imageheight -make -model ./photos > photos.csv
```

### H) Batch tag with IPTC keywords from a text file

```bash
while IFS= read -r kw; do
  exiftool -P -overwrite_original -Keywords+="$kw" *.jpg
done < keywords.txt
```

### I) Fix "my iPhone video has no date in Windows Explorer"

```bash
exiftool -P -overwrite_original \
  "-QuickTime:CreateDate<CreateDate" \
  "-QuickTime:ModifyDate<ModifyDate" \
  video.mov
```

### J) Remove a single troublesome tag (e.g. broken MakerNotes block)

```bash
exiftool -P -overwrite_original -MakerNotes= in.jpg
```

---

## 9. Quick one-liners

```bash
exiftool -ver                                  # version
exiftool -listx Artist                         # tag details (XML)
exiftool -list                                 # list all readable tags
exiftool -listw                                # list all writable tags
exiftool -listg1                               # list all family-1 group names
exiftool -a -G1 -s in.jpg                      # every tag, with group, short
exiftool -validate -warning -a in.jpg          # integrity check
exiftool -charset utf8 ...                     # force UTF-8 on Windows
```
