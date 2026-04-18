---
name: ffmpeg-metadata
description: >
  Metadata, chapters, and cover art authoring with ffmpeg: -metadata, -metadata:s:a:0, -map_metadata, ffmetadata chapter files, -attach, -disposition attached_pic, MKV edition entries, stream titles, language tags, tag writing for MP4/MKV/MP3/FLAC. Use when the user asks to add chapters, edit tags, set title/artist/year, add cover art, embed thumbnail, set stream language, rename audio tracks, mark default/forced subtitle track, strip metadata, or write an ffmetadata file.
argument-hint: "[operation] [input]"
---

# Ffmpeg Metadata

**Context:** $ARGUMENTS

## Quick start

- **Set title/artist/year:** → Step 1 (pick "set tags") → Step 2
- **Add chapter markers:** → Step 1 (pick "chapters") → Step 2
- **Embed cover art / thumbnail:** → Step 1 (pick "cover") → Step 2
- **Set audio language / stream title:** → Step 1 (per-stream tags) → Step 2
- **Mark subtitle default/forced:** → Step 1 (disposition) → Step 2
- **Strip all metadata:** → Step 1 (strip) → Step 2
- **Attach font to MKV for ASS subs:** → Step 1 (attach) → Step 2
- **Always verify after:** → Step 3

## When to use

- Authoring final deliverables where titles, artists, years, comments must be embedded.
- Adding chapter markers so players (QuickTime, VLC, Plex, iOS) show a chapter list.
- Embedding cover art / poster frames in MP3, MP4/M4A, MKV, FLAC.
- Tagging audio/subtitle streams with correct ISO 639-2 language codes so players auto-select the right track.
- Marking a subtitle track as `default` and/or `forced`.
- Stripping identifying metadata before publishing (privacy).
- Attaching fonts to MKV files so ASS subtitle styling renders correctly on other machines.

## Step 1 — Pick the operation

Decide which category your task falls in. Each maps to a different flag set.

| Operation              | Core flags                                                           |
|------------------------|----------------------------------------------------------------------|
| Set container tags     | `-metadata KEY=VALUE ...`                                            |
| Set per-stream tags    | `-metadata:s:<type>:<index> KEY=VALUE` (e.g. `s:a:0`, `s:v:0`, `s:s:0`) |
| Add chapters           | ffmetadata file + `-map_metadata 1 -map_chapters 1`                  |
| Extract chapters       | `-f ffmetadata chapters.txt`                                         |
| Embed cover art        | Second input (image) + `-map 0 -map 1:v -disposition:v:<i> attached_pic` |
| MKV attachment         | `-attach FILE -metadata:s:t:<i> mimetype=...`                        |
| Strip metadata         | `-map_metadata -1 -map_chapters -1`                                  |
| Disposition flags      | `-disposition:<specifier> +default+forced` (or bare value to replace) |

All of these should use `-c copy` — changing metadata never requires re-encoding.

## Step 2 — Build the command

### Set container tags (MP4)

```bash
ffmpeg -i in.mp4 -c copy \
  -metadata title="My Video" \
  -metadata artist="Alice" \
  -metadata year=2026 \
  -metadata comment="Rendered 2026-04-17" \
  out.mp4
```

### Set per-stream tags (MKV)

```bash
ffmpeg -i in.mkv -c copy \
  -metadata:s:a:0 language=eng -metadata:s:a:0 title="English 5.1" \
  -metadata:s:a:1 language=fra -metadata:s:a:1 title="Français Stereo" \
  -metadata:s:s:0 language=eng -metadata:s:s:0 title="English SDH" \
  out.mkv
```

Stream specifiers: `s:v:0` (first video), `s:a:1` (second audio), `s:s:0` (first subtitle), `s:t:0` (first attachment in MKV).

### Add chapters from an ffmetadata file

Create `chapters.txt` (FIRST line must be `;FFMETADATA1`):

```
;FFMETADATA1
[CHAPTER]
TIMEBASE=1/1000
START=0
END=60000
title=Intro
[CHAPTER]
TIMEBASE=1/1000
START=60000
END=180000
title=Main
[CHAPTER]
TIMEBASE=1/1000
START=180000
END=210000
title=Outro
```

Apply:

```bash
ffmpeg -i in.mp4 -i chapters.txt -map_metadata 1 -map_chapters 1 -c copy out.mp4
```

### Extract existing chapters

```bash
ffmpeg -i in.mp4 -f ffmetadata chapters_out.txt
```

You can edit the resulting file (change titles, times) and re-apply with the command above.

### Embed cover art

MP3:

```bash
ffmpeg -i in.mp3 -i cover.jpg \
  -map 0:a -map 1:v -c copy \
  -id3v2_version 3 \
  -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" \
  -disposition:v:0 attached_pic \
  out.mp3
```

MP4 / M4A:

```bash
ffmpeg -i in.m4a -i cover.jpg \
  -map 0 -map 1 -c copy \
  -disposition:v:1 attached_pic \
  out.m4a
```

MKV (via attachment):

```bash
ffmpeg -i in.mkv -attach cover.jpg \
  -metadata:s:t:0 mimetype=image/jpeg \
  -metadata:s:t:0 filename=cover.jpg \
  -c copy out.mkv
```

### Attach a font to MKV (for ASS subtitles)

```bash
ffmpeg -i in.mkv -attach arial.ttf \
  -metadata:s:t:0 mimetype=application/x-truetype-font \
  -metadata:s:t:0 filename=arial.ttf \
  -c copy out.mkv
```

### Disposition — default / forced subtitle

```bash
# ADD flags (keeps any existing)
ffmpeg -i in.mkv -c copy -disposition:s:0 +default+forced out.mkv

# REPLACE flags (drops everything else)
ffmpeg -i in.mkv -c copy -disposition:s:0 default out.mkv

# CLEAR all flags on a stream
ffmpeg -i in.mkv -c copy -disposition:s:0 0 out.mkv
```

### Strip all metadata + chapters

```bash
ffmpeg -i in.mp4 -map 0 -map_metadata -1 -map_chapters -1 \
  -c copy -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
  out.mp4
```

The `+bitexact` flags also suppress the automatic `encoder=Lavf...` tag ffmpeg adds.

## Step 3 — Verify with ffprobe

After writing metadata, confirm it stuck:

```bash
# All format + stream tags, JSON
ffprobe -v error -show_format -show_streams -show_chapters -of json out.mp4

# Just the title
ffprobe -v error -show_entries format_tags=title -of default=nw=1:nk=1 out.mp4

# Per-stream language tags
ffprobe -v error -show_entries stream=index,codec_type:stream_tags=language,title \
  -of compact out.mkv

# Disposition flags
ffprobe -v error -show_entries stream=index,codec_type:stream_disposition=default,forced,attached_pic \
  -of compact out.mkv

# Chapters only
ffprobe -v error -show_chapters -of json out.mp4
```

If a tag is missing, check: (a) container supports that key, (b) you used `-c copy` (re-encoding sometimes drops unsupported tags), (c) `-map_metadata` wasn't set to `-1`.

## Gotchas

- **`-c copy` is required** for metadata-only edits, otherwise ffmpeg re-encodes (slow, quality loss).
- **MP4 uses a fixed tag vocabulary** — `title, artist, album, album_artist, composer, date/year, comment, genre, track, disc, copyright, description, synopsis, show, episode_id, network, lyrics, performer`. Arbitrary keys silently drop.
- **MKV is permissive** — accepts any free-form key; great for custom tagging.
- **MP3 maps ffmpeg keys to ID3 automatically** (title→TIT2, artist→TPE1, album→TALB, date→TDRC, etc.). Use `-id3v2_version 3` for maximum player compatibility.
- **Cover art in MP3** needs `-disposition:v:0 attached_pic` or players ignore it.
- **Cover art in MP4** is stored in the `covr` atom; ffmpeg handles this automatically when `attached_pic` disposition is set on the image stream.
- **ffmetadata files MUST start with `;FFMETADATA1` on line 1** — no leading whitespace, no BOM.
- **CHAPTER `TIMEBASE` uses fraction form** — `1/1000` = milliseconds, `1/1` = seconds, `1/90000` = MPEG-TS ticks. `START` and `END` are integers in timebase units.
- **Language codes are ISO 639-2 three-letter** (eng, fra, deu, spa, jpn, kor, zho). Two-letter codes (en, fr) often fail to match in players.
- **`encoder=Lavf...` sneaks back in** even after `-map_metadata -1`. Add `-fflags +bitexact -flags:v +bitexact -flags:a +bitexact` to suppress.
- **`-map_chapters -1` is separate from `-map_metadata -1`** — chapters are tracked independently, strip both to fully clean.
- **`-disposition:s:0 +default+forced` ADDS, `-disposition:s:0 default` REPLACES.** `0` clears all flags.
- **MP4 attached_pic stream ordering** — some players (notably QuickTime) want the cover image stream to appear AFTER the main video. Use `-map` to control order.
- **MKV attachments persist through `-c copy`** — that's by design. To remove them, see `-map -0:t` exclusion.
- **`-metadata:g KEY=VALUE`** also works for global tags (equivalent to bare `-metadata`).
- **Per-stream `-metadata:s:a:0` applies to OUTPUT stream 0 of type a**, after `-map` reordering. If you remap, recount.

## Examples

### Example 1: podcast MP3 — title, artist, album, cover

```bash
ffmpeg -i episode42.mp3 -i cover.jpg \
  -map 0:a -map 1:v -c copy -id3v2_version 3 \
  -metadata title="Episode 42: Time Travel" \
  -metadata artist="The Pod" -metadata album="The Pod Season 3" \
  -metadata date=2026 -metadata track=42 -metadata genre=Podcast \
  -disposition:v:0 attached_pic \
  out.mp3
```

### Example 2: movie MKV — chapters + per-language audio tags

1. Write `chapters.txt` (see Step 2).
2. Mux:
   ```bash
   ffmpeg -i movie.mkv -i chapters.txt \
     -map_metadata 1 -map_chapters 1 \
     -metadata:s:a:0 language=eng -metadata:s:a:0 title="English 5.1" \
     -metadata:s:a:1 language=fra -metadata:s:a:1 title="Français 5.1" \
     -metadata:s:s:0 language=eng -disposition:s:0 +default \
     -c copy tagged.mkv
   ```

### Example 3: strip everything for privacy

```bash
ffmpeg -i vacation.mp4 -map 0 -map_metadata -1 -map_chapters -1 \
  -c copy -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
  clean.mp4
ffprobe -v error -show_format -show_streams clean.mp4 | grep -i tag
```

### Example 4: force a subtitle as default + forced

```bash
ffmpeg -i in.mkv -c copy -disposition:s:0 +default+forced out.mkv
ffprobe -show_entries stream=index:stream_disposition=default,forced -of compact out.mkv
```

## Troubleshooting

### Error: `At least one output file must be specified`
Cause: `-f ffmetadata` extraction missing an output path.
Solution: `ffmpeg -i in.mp4 -f ffmetadata chapters.txt` — `chapters.txt` is the output.

### Tag disappears after mux
Cause: Container doesn't support that tag name (common: arbitrary keys on MP4).
Solution: Use MKV for free-form tags, or pick a supported MP4 key from the list in `references/tags.md`.

### Cover art doesn't show in player
Cause: Missing `attached_pic` disposition, OR cover is first video stream when player expects it second.
Solution: Set `-disposition:v:N attached_pic` on the image stream; reorder with `-map` so the primary video is first.

### Chapters silently ignored
Cause: ffmetadata file missing `;FFMETADATA1` header, or wrong TIMEBASE.
Solution: First line must be exactly `;FFMETADATA1`. TIMEBASE must be `N/D` (e.g. `1/1000`).

### Language tag not recognized by player
Cause: Used two-letter code (`en`) instead of three-letter ISO 639-2 (`eng`).
Solution: Always use three-letter: `eng, fra, deu, spa, ita, por, jpn, kor, zho, rus, ara, hin`.

### `encoder=Lavf...` keeps appearing
Cause: ffmpeg writes its own encoder tag.
Solution: Add `-fflags +bitexact -flags:v +bitexact -flags:a +bitexact`.

## Reference docs

- Read [`references/tags.md`](references/tags.md) for the ffmetadata format spec, per-container tag catalogs (MP4/MKV/MP3/FLAC/OGG/WAV), ISO 639-2 language codes, disposition flag list, cover-art compatibility matrix, MKV edition entries, and ffprobe verification recipes.

## Available scripts

- **`scripts/meta.py`** — argparse CLI for all metadata operations (`set`, `chapters`, `extract-chapters`, `cover`, `attach`, `strip`, `disposition`). Prints the ffmpeg command it runs; supports `--dry-run` and `--verbose`. Stdlib only.

Usage examples:

```bash
# Set container + per-stream tags
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py set \
  --input in.mp4 --output out.mp4 \
  --tags title="My Video" artist="Alice" year=2026 \
  --stream-tags a:0:language=eng a:0:title="English 5.1" s:0:language=eng

# Add chapters from inline timestamps
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py chapters \
  --input in.mp4 --output out.mp4 \
  --from-timestamps "0:00 Intro" "1:00 Main" "3:00 Outro"

# Add chapters from a pre-written ffmetadata file
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py chapters \
  --input in.mp4 --output out.mp4 --chapters-file chapters.txt

# Extract chapters
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py extract-chapters \
  --input in.mp4 --output chapters.txt

# Embed cover art
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py cover \
  --input song.mp3 --output tagged.mp3 --image cover.jpg

# Attach font to MKV
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py attach \
  --input in.mkv --output out.mkv --file arial.ttf \
  --mimetype application/x-truetype-font

# Set disposition flags
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py disposition \
  --input in.mkv --output out.mkv --stream s:0 --flags "+default+forced"

# Strip everything
uv run ${CLAUDE_SKILL_DIR}/scripts/meta.py strip \
  --input in.mp4 --output clean.mp4
```
