---
name: media-mkvtoolnix
description: >
  Matroska (MKV) authoring with MKVToolNix (mkvmerge, mkvextract, mkvpropedit, mkvinfo): split or merge MKV without re-encode, extract tracks, edit chapter titles, add attachments, change track metadata in-place, fix header compression, adjust default/forced flags. Use when the user asks to split an MKV at timestamps, merge MKVs, extract a track (audio/subs/attachment), edit MKV chapter names, change default track flags, fix MKV metadata without re-encoding, or demux a MKV with mkvextract.
argument-hint: "[operation] [input]"
---

# Media Mkvtoolnix

**Context:** $ARGUMENTS

MKVToolNix authors Matroska natively. Four tools: `mkvmerge` (mux/split), `mkvextract`
(demux), `mkvpropedit` (in-place metadata edit), `mkvinfo` (inspect). **Never re-encodes**
— stream-copy only. For re-encoding use ffmpeg; for MKV → MP4 use ffmpeg (MKVToolNix
cannot write MP4).

## Quick start

- **Merge tracks into one MKV:** → Step 3 (merge recipe)
- **Split by time / size:** → Step 3 (split recipe)
- **Extract a track (audio/subs/attachment):** → Step 3 (extract recipe)
- **Edit language / default flag in place:** → Step 3 (propedit recipe)
- **Inspect / verify:** → Step 4

## When to use

- You need lossless MKV editing (splitting, merging, metadata).
- You want to change track language, name, default/forced flag **without re-muxing**.
- You need to extract raw tracks (h264/ac3/srt) for re-authoring.
- You need to add/replace fonts or cover art attachments.
- Skip if: re-encoding required, or output container must be MP4/MOV/WebM-not-Matroska.

## Step 1 — Install

```bash
# macOS
brew install mkvtoolnix

# Debian/Ubuntu
sudo apt install mkvtoolnix

# Verify
mkvmerge --version && mkvextract --version && mkvpropedit --version && mkvinfo --version
```

## Step 2 — Pick the right tool

| Task | Tool |
|------|------|
| Combine tracks / split / remux | `mkvmerge` |
| Pull tracks/chapters/tags/attachments out | `mkvextract` |
| Edit metadata in place (fast, no remux) | `mkvpropedit` |
| Inspect structure | `mkvinfo` |

Get track IDs first: `mkvmerge --identify in.mkv` (or `-J in.mkv` for JSON).

## Step 3 — Run

### Merge (mkvmerge)

```bash
# Combine raw essences into an MKV
mkvmerge -o out.mkv video.h264 audio.ac3 subs.srt

# Merge with language + title metadata
mkvmerge -o out.mkv \
  --language 0:eng --track-name 0:"Main Video" video.h264 \
  --language 0:jpn audio.ac3 \
  --language 0:eng subs.srt \
  --title "My Movie"

# Append (concatenate) MKVs: use `+` between files
mkvmerge -o out.mkv a.mkv + b.mkv + c.mkv

# Re-mux / defragment / strip oddities
mkvmerge -o clean.mkv messy.mkv

# Convert MP4 -> MKV
mkvmerge -o out.mkv in.mp4
```

### Split (mkvmerge --split)

```bash
# Split at absolute timestamps
mkvmerge -o part.mkv --split timestamps:00:10:00,00:20:00 in.mkv

# Split by size
mkvmerge -o part.mkv --split size:500M in.mkv

# Keep only selected ranges (parts: absolute)
mkvmerge -o out.mkv --split parts:00:00:00-00:10:00,+00:15:00-00:25:00 in.mkv

# Split every N frames
mkvmerge -o part.mkv --split frames:2500 in.mkv

# Split at chapter boundaries
mkvmerge -o part.mkv --split chapters:all in.mkv
```

Output name template: `--split` writes `part-001.mkv`, `part-002.mkv`, ...

### Extract (mkvextract)

```bash
# Extract raw tracks (track_id:output_file)
mkvextract tracks in.mkv 0:video.h264 1:audio.ac3 2:subs.srt

# Extract chapters (XML by default, --simple = OGM)
mkvextract chapters in.mkv > chapters.xml
mkvextract chapters --simple in.mkv > chapters.txt

# Extract global tags
mkvextract tags in.mkv > tags.xml

# Extract attachments (attachment_id:output_file — IDs from mkvmerge -J)
mkvextract attachments in.mkv 1:font.ttf 2:cover.jpg

# Extract cues, timestamps, CUE sheet (advanced)
mkvextract timestamps_v2 in.mkv 0:video_ts.txt
```

### Edit metadata in place (mkvpropedit)

```bash
# Set track language + name
mkvpropedit in.mkv --edit track:v1 --set "language=eng" --set "name=Main Video"

# Set default flag on audio track 2 (a2 = second audio track)
mkvpropedit in.mkv --edit track:a2 --set "flag-default=1"

# Unset default flag on audio track 1
mkvpropedit in.mkv --edit track:a1 --set "flag-default=0"

# Set forced flag on a subtitle track
mkvpropedit in.mkv --edit track:s1 --set "flag-forced=1"

# Replace chapters from XML
mkvpropedit in.mkv --chapters chapters.xml

# Delete all chapters
mkvpropedit in.mkv --chapters ""

# Delete all tags
mkvpropedit in.mkv --tags all:""

# Add / replace / delete attachments
mkvpropedit in.mkv --add-attachment font.ttf --attachment-mime-type application/x-truetype-font
mkvpropedit in.mkv --replace-attachment 1:new.ttf
mkvpropedit in.mkv --delete-attachment 1

# Set container title
mkvpropedit in.mkv --edit info --set "title=My Movie"
```

Track selector syntax: `track:v1` (first video), `track:a2` (second audio),
`track:s1` (first subtitle), `track:@N` (track with MKV track number N),
`track:=UID` (track UID).

## Step 4 — Verify with mkvinfo

```bash
# Human-readable
mkvinfo in.mkv

# With size info + UTF-8
mkvinfo --output-charset UTF-8 -p in.mkv

# Programmatic: use mkvmerge JSON
mkvmerge -J in.mkv | jq '.tracks[] | {id, type: .type, codec: .codec, lang: .properties.language, default: .properties.default_track, forced: .properties.forced_track}'
```

## Gotchas

- **MKVToolNix is not ffmpeg.** It reads/writes Matroska natively, preserves metadata
  exactly, and is often faster for MKV-in/MKV-out work. But it cannot re-encode and
  cannot write non-Matroska containers.
- **Never re-encodes.** Every mkvmerge operation is stream-copy. If source codecs
  can't live in MKV, mkvmerge errors — don't expect implicit conversion.
- **Splits are key-frame-aligned.** The actual cut may be 1–2 frames off the requested
  timestamp. For frame-exact cuts you must re-encode via ffmpeg.
- **`--split` value format is strict:**
  - `size:500M` (K/M/G suffixes)
  - `timestamps:HH:MM:SS.nnn,HH:MM:SS.nnn` (absolute)
  - `parts:START-END[,+START-END...]` (`+` glues into one file, no `+` = new file)
  - `frames:N` / `chapters:all` / `chapters:N,M`
- **`mkvpropedit` edits in place without re-muxing** — extremely fast, no temp file.
- **Default / forced flags are MKV conventions:**
  - `flag-default=1` → "play this one if multiple in same type."
  - `flag-forced=1` → "player MUST render this" (forced subs, burn-in translation).
  - Use `0` to unset. Only one track per type should be default.
- **Language tags:** MKVToolNix accepts BCP-47 (`en`, `ja`, `pt-BR`) **and** ISO 639-2
  three-letter (`eng`, `jpn`, `por`). New versions prefer BCP-47. Use three-letter for
  max compatibility with older players.
- **`+` in mkvmerge appends files** (concatenates). Codecs/resolutions/timebases must
  match or the append fails — normalize with ffmpeg first if mismatched.
- **Track IDs** come from `mkvmerge --identify in.mkv` (or `-J` for JSON). They are
  0-indexed and distinct from the `v1/a1/s1` selector used by `--edit`.
- **Attachments are preserved** across `mkvmerge -o out in.mkv`. Strip them with
  `--no-attachments`. Common MIME types: `application/x-truetype-font`,
  `application/x-opentype-font`, `image/jpeg`, `image/png`.
- **MP4 → MKV** works (`mkvmerge -o out.mkv in.mp4`) but strips some MP4-specific
  atoms. **MKV → MP4 is NOT supported** — use ffmpeg.
- **Chapter XML schema is specific.** Generate via `mkvextract chapters in.mkv > template.xml`
  and edit, rather than writing from scratch.
- **`--title "Name"`** sets the container-level title (seen in players).
  **`--chapter-language eng`** sets chapter language metadata.
- **WebM is a Matroska subset.** mkvmerge handles WebM; to produce WebM use
  `--webm` or output to `.webm`.
- **Segment linking (`--link` / `--segment-linking`)** creates chained MKVs referring
  to each other by UID. Advanced; most players don't follow the links.

## Examples

### Example 1: anime fansub — merge video, two audio, two subtitle tracks + fonts

```bash
mkvmerge -o episode.mkv \
  --language 0:jpn --track-name 0:"Video" video.h264 \
  --language 0:jpn --track-name 0:"Japanese" --default-track 0:yes audio_jpn.flac \
  --language 0:eng --track-name 0:"English Dub" --default-track 0:no audio_eng.ac3 \
  --language 0:eng --track-name 0:"English Subs" --default-track 0:yes subs_eng.ass \
  --language 0:eng --track-name 0:"Signs & Songs" --forced-track 0:yes --default-track 0:no subs_signs.ass \
  --attachment-mime-type application/x-truetype-font --attach-file font1.ttf \
  --attachment-mime-type application/x-truetype-font --attach-file font2.otf \
  --title "Show Name - Ep 01"
```

### Example 2: split a season archive into 4 GB chunks

```bash
mkvmerge -o season01-%03d.mkv --split size:4000M season01-full.mkv
```

### Example 3: correct a wrong language tag without re-muxing

```bash
mkvmerge -J wrong.mkv | jq '.tracks[] | {id, type: .type, lang: .properties.language}'
# Say audio track (a1) is labeled "und" but should be "jpn":
mkvpropedit wrong.mkv --edit track:a1 --set "language=jpn"
```

### Example 4: replace attached fonts in an ASS-subtitled MKV

```bash
# Inspect existing attachments
mkvmerge -J in.mkv | jq '.attachments[] | {id, name: .file_name, mime: .content_type}'

# Replace attachment ID 1, delete ID 2, add a third
mkvpropedit in.mkv \
  --replace-attachment 1:new-regular.ttf \
  --delete-attachment 2 \
  --add-attachment new-italic.ttf --attachment-mime-type application/x-truetype-font
```

### Example 5: keep only chapters 2 and 5 of a movie

```bash
mkvmerge -o keep.mkv --split parts:00:12:30-00:24:10,+00:58:00-01:12:00 movie.mkv
```

### Example 6: strip all chapters and tags from a release

```bash
mkvpropedit release.mkv --chapters "" --tags all:""
```

## Available scripts

- **`scripts/mkv.py`** — argparse wrapper around `mkvmerge`, `mkvextract`,
  `mkvpropedit`, `mkvinfo`. Subcommands: `identify`, `merge`, `split-time`,
  `split-size`, `extract-tracks`, `extract-chapters`, `extract-attachments`,
  `edit`, `default-flag`, `add-attachment`, `replace-chapters`.
  Flags: `--dry-run`, `--verbose`. Stdlib only.

```bash
# Identify tracks (JSON)
python3 ${CLAUDE_SKILL_DIR}/scripts/mkv.py identify --input in.mkv

# Merge
python3 ${CLAUDE_SKILL_DIR}/scripts/mkv.py merge \
  --output out.mkv --inputs v.h264 a.ac3 s.srt \
  --title "My Movie" --languages eng,jpn,eng

# Split by time
python3 ${CLAUDE_SKILL_DIR}/scripts/mkv.py split-time \
  --input in.mkv --output-pattern part.mkv --times 00:10:00,00:20:00

# Flip default flag
python3 ${CLAUDE_SKILL_DIR}/scripts/mkv.py default-flag \
  --input in.mkv --track a2 --value 1
```

## Reference docs

- Read [`references/mkvtoolnix.md`](references/mkvtoolnix.md) for full split syntax,
  track selector grammar, flag reference (default/forced/hearing-impaired/commentary),
  language code tables, chapter XML schema, MIME types, and recipe book
  (fansub workflow, season archival, font embedding, language correction).

## Troubleshooting

### Error: `The file could not be opened for reading: Wrong Matroska version`
Cause: File isn't Matroska, or is corrupt.
Solution: `ffprobe file.mkv` to confirm. If MP4 mis-named, rename. If corrupt,
try `mkvmerge -o recovered.mkv --engage keep_bitstream_av1 damaged.mkv`.

### Error: `The track parameters do not match`
Cause: Appending (`+`) two files whose codecs/resolution/timebase differ.
Solution: Normalize with ffmpeg first: `ffmpeg -i a.mkv -c copy a-norm.mkv` won't
help — you must re-encode to matching params: `ffmpeg -i a.mkv -c:v libx264 -c:a aac a-norm.mp4`.

### `mkvpropedit` says `Nothing to do` but I specified `--set`
Cause: Track selector didn't match. Selectors are `track:v1`, `track:a1`, `track:s1`
(type+index), not 0-indexed track IDs.
Solution: Verify with `mkvmerge -J in.mkv` and use the right selector form.

### Splits land a frame or two off the requested timestamp
Cause: Splits are key-frame aligned; mkvmerge never re-encodes.
Solution: For frame-exact cuts, re-encode with ffmpeg seeking, or add a keyframe at
the target timestamp via `ffmpeg -force_key_frames` before splitting.

### Fonts in attached MKV don't render in players
Cause: Wrong MIME type or player doesn't auto-load MKV attachments.
Solution: Use `application/x-truetype-font` for .ttf and
`application/x-opentype-font` for .otf. VLC / mpv autoload; some hardware players
do not — burn subs in via ffmpeg `subtitles=` filter instead.

### `mkvmerge -o out.mp4 in.mkv` fails
Cause: MKVToolNix writes only Matroska/WebM. It cannot produce MP4.
Solution: `ffmpeg -i in.mkv -c copy out.mp4`.
