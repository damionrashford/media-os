# ffmpeg metadata reference

Deep reference for the ffmetadata file format, per-container tag catalogs,
ISO 639-2 language codes, disposition flag list, cover-art compatibility
matrix, MKV edition entries, and ffprobe verification recipes.

---

## 1. ffmetadata format spec

The ffmetadata1 format is ffmpeg's portable "dump-and-reapply" file for
container-level tags and chapters. `-f ffmetadata` reads and writes it.

### Rules

1. **First line MUST be exactly `;FFMETADATA1`** — no BOM, no leading
   whitespace, no blank line before it.
2. Comments begin with `;` or `#`.
3. Top-level `KEY=VALUE` lines before any section are **container (global)
   tags**.
4. Sections start with `[SECTION]` on its own line. Known sections:
   - `[STREAM]` — tags attached to the next stream in file order (rarely
     round-trips perfectly across containers; prefer `-metadata:s:...`
     on the command line).
   - `[CHAPTER]` — one chapter marker.
5. Multi-line values: escape `\n` with a literal `\n`, or continue lines
   by ending with a single `\`.
6. Special chars `; # = \` must be escaped with backslash in values.
7. Unknown keys are preserved (container permitting).

### Minimal example

```
;FFMETADATA1
title=My Video
artist=Alice
date=2026
comment=Exported 2026-04-17
```

### With chapters

```
;FFMETADATA1
title=Podcast Ep 42
artist=The Pod
date=2026

[CHAPTER]
TIMEBASE=1/1000
START=0
END=30000
title=Cold open

[CHAPTER]
TIMEBASE=1/1000
START=30000
END=1230000
title=Interview

[CHAPTER]
TIMEBASE=1/1000
START=1230000
END=1380000
title=Outro
```

### TIMEBASE notes

| TIMEBASE | Meaning          | START=60 means |
|----------|------------------|----------------|
| `1/1`    | seconds          | 60 s           |
| `1/1000` | milliseconds     | 60 ms          |
| `1/90000`| MPEG-TS ticks    | 60/90000 s     |
| `1/48000`| audio-sample units | 60/48000 s   |

`START` and `END` MUST be integers. Fractional seconds go through
TIMEBASE, e.g. `TIMEBASE=1/1000` + `START=500` = 0.5 s.

### With per-stream tags (limited portability)

```
;FFMETADATA1
title=Movie

[STREAM]
language=eng
title=English 5.1

[STREAM]
language=fra
title=Français 5.1
```

### Extracting + editing round-trip

```bash
ffmpeg -i in.mp4 -f ffmetadata meta.txt     # dump
$EDITOR meta.txt                             # edit
ffmpeg -i in.mp4 -i meta.txt \
  -map_metadata 1 -map_chapters 1 -c copy out.mp4
```

---

## 2. Container-specific tag catalogs

### MP4 / M4A / MOV (iTunes-style atoms)

ffmpeg maps these keys to iTunes atoms. Arbitrary keys are silently
dropped by the MP4 muxer.

| ffmpeg key       | iTunes atom | Notes                               |
|------------------|-------------|-------------------------------------|
| `title`          | `©nam`      | Track title                         |
| `artist`         | `©ART`      | Artist                              |
| `album_artist`   | `aART`      | Album artist                        |
| `album`          | `©alb`      | Album                               |
| `date` / `year`  | `©day`      | Release year                        |
| `comment`        | `©cmt`      |                                     |
| `description`    | `desc`      | Short description                   |
| `synopsis`       | `ldes`      | Long description                    |
| `show`           | `tvsh`      | TV show name                        |
| `episode_id`     | `tven`      |                                     |
| `season_number`  | `tvsn`      |                                     |
| `episode_sort`   | `tves`      |                                     |
| `network`        | `tvnn`      |                                     |
| `genre`          | `©gen`      |                                     |
| `track`          | `trkn`      | "3/10" form OK                      |
| `disc`           | `disk`      | "1/2" form OK                       |
| `composer`       | `©wrt`      |                                     |
| `copyright`      | `cprt`      |                                     |
| `lyrics`         | `©lyr`      |                                     |
| `performer`      | `perf`      |                                     |
| `encoder`        | `©too`      | Auto-set by ffmpeg                  |
| `encoded_by`     | `©enc`      |                                     |
| `media_type`     | `stik`      | 0 movie, 1 normal, 9 TV, 10 music   |
| `compilation`    | `cpil`      | `1` = true                          |
| `gapless_playback`| `pgap`     |                                     |
| `hd_video`       | `hdvd`      |                                     |

Cover art is stored in the `covr` atom. ffmpeg writes it automatically
when you mark an image stream `-disposition:v:N attached_pic`.

### MKV / WebM (Matroska)

Matroska is free-form — any key is stored in `SimpleTag` elements.
Common conventions:

| Key            | Meaning                          |
|----------------|----------------------------------|
| `title`        | Segment title                    |
| `artist`       | Primary artist/director          |
| `date` / `year`| Release date                     |
| `genre`        |                                  |
| `comment`      |                                  |
| `description`  |                                  |
| `copyright`    |                                  |
| `encoder`      | Auto-set by ffmpeg               |
| `language`     | Per-stream, ISO 639-2            |
| `title` (s:a:N)| Audio track display name         |
| `title` (s:s:N)| Subtitle track display name      |

MKV also supports:
- **Attachments** (fonts, images, subs): `-attach FILE` + `-metadata:s:t:N mimetype=...`
- **Chapters**: full ffmetadata chapter support, portable across ffmpeg
- **Edition entries**: see section 7

### MP3 (ID3v2)

ffmpeg auto-maps friendly keys to ID3v2 frames. Use
`-id3v2_version 3` for maximum player compatibility (v4 is newer but
some devices/cars only read v3).

| ffmpeg key     | ID3v2 frame | Meaning                |
|----------------|-------------|------------------------|
| `title`        | TIT2        | Title                  |
| `artist`       | TPE1        | Lead performer         |
| `album_artist` | TPE2        | Band / album artist    |
| `album`        | TALB        | Album                  |
| `date`         | TDRC        | Recording time         |
| `year`         | TYER        | (v2.3 only)            |
| `track`        | TRCK        | "3/10" OK              |
| `disc`         | TPOS        | Disc number            |
| `genre`        | TCON        |                        |
| `composer`     | TCOM        |                        |
| `performer`    | TPE3        | Conductor/performer    |
| `copyright`    | TCOP        |                        |
| `comment`      | COMM        |                        |
| `lyrics`       | USLT        |                        |
| `publisher`    | TPUB        |                        |
| `encoder`      | TSSE        | Auto-set               |
| `language`     | TLAN        |                        |
| `isrc`         | TSRC        |                        |
| `bpm`          | TBPM        |                        |

Cover art (front cover): add an image input, `-map 1:v`,
`-disposition:v:0 attached_pic`. ffmpeg writes it as an `APIC` frame
with picture type 3 (Cover front).

### FLAC (Vorbis comments)

Vorbis comment blocks are case-insensitive, free-form key=value.
ffmpeg writes all `-metadata` keys verbatim.

Common keys: `TITLE`, `ARTIST`, `ALBUM`, `DATE`, `GENRE`,
`TRACKNUMBER`, `TRACKTOTAL`, `DISCNUMBER`, `DISCTOTAL`,
`ALBUMARTIST`, `COMPOSER`, `COMMENT`, `LYRICS`, `PERFORMER`,
`COPYRIGHT`, `LICENSE`, `ORGANIZATION`, `DESCRIPTION`, `LOCATION`,
`CONTACT`, `ISRC`.

ReplayGain: `REPLAYGAIN_TRACK_GAIN`, `REPLAYGAIN_TRACK_PEAK`,
`REPLAYGAIN_ALBUM_GAIN`, `REPLAYGAIN_ALBUM_PEAK`.

Cover art: FLAC has a native `PICTURE` block. ffmpeg writes it from an
attached_pic image stream.

### OGG / Opus / Vorbis

Same Vorbis comment convention as FLAC. Key differences:
- Opus uses `OpusTags`; ffmpeg handles transparently.
- Cover art embedding via `METADATA_BLOCK_PICTURE` (base64-encoded FLAC
  picture block). ffmpeg handles when image stream has `attached_pic`.

### WAV (BWF + INFO + optional ID3)

WAV supports the `INFO` chunk and, optionally, an `id3 ` chunk.
Broadcast Wave (BWF) adds a `bext` chunk with production metadata.

INFO chunk keys (subset):

| ffmpeg key  | INFO ID | Meaning       |
|-------------|---------|---------------|
| `title`     | INAM    | Title         |
| `artist`    | IART    | Artist        |
| `album`     | IPRD    | Product       |
| `date`      | ICRD    | Creation date |
| `genre`     | IGNR    | Genre         |
| `comment`   | ICMT    | Comments      |
| `copyright` | ICOP    | Copyright     |
| `encoder`   | ISFT    | Software      |
| `track`     | ITRK    | Track number  |

BWF `bext` keys (auto-mapped by ffmpeg):
- `description`, `originator`, `originator_reference`, `origination_date`,
  `origination_time`, `time_reference`, `coding_history`, `umid`.

### AIFF

Similar to WAV but uses `ID3` chunk; ffmpeg accepts friendly keys and
writes as ID3 when supported.

---

## 3. ISO 639-2 language codes (common)

Use three-letter codes for `language=XXX` stream tags. Two-letter codes
often fail to match in players.

| Code | Language             |
|------|----------------------|
| eng  | English              |
| spa  | Spanish              |
| fra  | French               |
| deu  | German               |
| ita  | Italian              |
| por  | Portuguese           |
| rus  | Russian              |
| ara  | Arabic               |
| hin  | Hindi                |
| jpn  | Japanese             |
| kor  | Korean               |
| zho  | Chinese              |
| vie  | Vietnamese           |
| tha  | Thai                 |
| tur  | Turkish              |
| nld  | Dutch                |
| swe  | Swedish              |
| nor  | Norwegian            |
| dan  | Danish               |
| fin  | Finnish              |
| pol  | Polish               |
| ces  | Czech                |
| ell  | Greek                |
| heb  | Hebrew               |
| ind  | Indonesian           |
| ben  | Bengali              |
| ukr  | Ukrainian            |
| ron  | Romanian             |
| hun  | Hungarian            |
| und  | Undetermined         |
| mul  | Multiple languages   |

Some containers also accept BCP-47 tags (`en-US`, `pt-BR`). MKV's
`language_ietf` accepts BCP-47 alongside the legacy ISO 639-2 `language`
field.

---

## 4. Disposition flags

Set via `-disposition:<specifier> FLAGS`:

- `+name` — ADD flag (keeps others)
- `-name` — REMOVE flag
- `name` — REPLACE all flags with this one
- `0` — CLEAR all flags

Known flags:

| Flag              | Meaning                                                            |
|-------------------|--------------------------------------------------------------------|
| `default`         | Default stream (auto-selected by player)                           |
| `dub`             | Dubbed audio                                                       |
| `original`        | Original-language audio                                            |
| `comment`         | Commentary track                                                   |
| `lyrics`          | Lyrics track                                                       |
| `karaoke`         | Karaoke track                                                      |
| `forced`          | Subtitles forced (e.g. foreign dialogue translations)              |
| `hearing_impaired`| For hearing-impaired viewers (SDH/HoH)                             |
| `visual_impaired` | Audio description for visually impaired                            |
| `clean_effects`   | Effects-only audio                                                 |
| `attached_pic`    | Stream is a still image (cover art)                                |
| `timed_thumbnails`| Trickplay / scrubbing thumbnails                                   |
| `captions`        | Stream carries captions                                            |
| `descriptions`    | Text descriptions                                                  |
| `metadata`        | Stream contains metadata                                           |
| `dependent`       | Dependent stream (e.g. supplementary eSBR/SHVC layer)              |
| `still_image`     | Stream is a still image                                            |
| `thumbnail`       | Single thumbnail image                                             |

Common recipes:

```bash
# Forced English subtitles, also default
-disposition:s:0 +default+forced

# Swap default audio from track 0 to track 1
-disposition:a:0 -default -disposition:a:1 +default

# Mark audio track 2 as commentary
-disposition:a:2 +comment

# Make an image stream act as cover art
-disposition:v:1 attached_pic
```

---

## 5. Cover-art embedding — compatibility matrix

| Container | Method                                                   | Typical result             |
|-----------|----------------------------------------------------------|----------------------------|
| MP3       | image stream + `-disposition:v:0 attached_pic` + `-id3v2_version 3` | APIC frame, type 3 (Front)|
| MP4/M4A   | image stream + `-disposition:v:N attached_pic`           | `covr` atom                |
| MOV       | same as MP4                                              | `covr` atom                |
| MKV       | `-attach cover.jpg` + mimetype tag OR attached_pic stream| Attachment OR secondary video stream |
| WebM      | Only as Matroska attachment — no attached_pic support    | Attachment                 |
| FLAC      | image stream + attached_pic                              | native PICTURE block       |
| OGG/Opus  | image stream + attached_pic                              | METADATA_BLOCK_PICTURE     |
| WAV       | Limited — requires ID3 chunk + attached_pic              | ID3 APIC frame             |
| AIFF      | image stream + attached_pic (ID3 APIC)                   | APIC frame                 |

Recommendations:
- JPEG for cover art (universal); PNG for crisp logos/transparency.
- Square (1:1), 1400×1400 to 3000×3000 is safe for podcast directories.
- Under 1 MB keeps metadata parse fast in media libraries.

---

## 6. ffprobe verification recipes

### Container tags only

```bash
ffprobe -v error -show_entries format_tags -of json out.mp4
```

### All stream tags

```bash
ffprobe -v error -show_entries stream=index,codec_type:stream_tags \
  -of json out.mkv
```

### Language tag per audio/subtitle stream

```bash
ffprobe -v error \
  -select_streams a \
  -show_entries stream=index:stream_tags=language,title \
  -of compact=p=0 out.mkv

ffprobe -v error \
  -select_streams s \
  -show_entries stream=index:stream_tags=language,title \
  -of compact=p=0 out.mkv
```

### Disposition flags

```bash
ffprobe -v error \
  -show_entries stream=index,codec_type:stream_disposition \
  -of json out.mkv
```

### Chapters

```bash
ffprobe -v error -show_chapters -of json out.mp4
# Pretty per-chapter with title:
ffprobe -v error -show_chapters \
  -of compact=nk=1:p=0:s=, out.mp4
```

### Attachments (MKV)

```bash
ffprobe -v error -select_streams t \
  -show_entries stream=index,codec_name:stream_tags=filename,mimetype \
  -of compact=p=0 out.mkv
```

### One-shot summary

```bash
ffprobe -v error -show_format -show_streams -show_chapters \
  -of json out.mkv | jq '{
    format_tags: .format.tags,
    streams: [.streams[] | {
      index, codec_type,
      title: .tags.title, language: .tags.language,
      default: .disposition.default,
      forced: .disposition.forced,
      attached_pic: .disposition.attached_pic
    }],
    chapters: .chapters
  }'
```

---

## 7. MKV edition entries

Matroska supports multiple "editions" (e.g. Theatrical, Director's
Cut, Extended). ffmpeg's support is **limited** — reading works
better than authoring. For authoring you usually reach for `mkvmerge`
(from mkvtoolnix).

What ffmpeg can do:

```bash
# Tag an edition title (limited; mkvmerge is more reliable)
ffmpeg -i in.mkv -c copy \
  -metadata:s:edition:0 title="Director's Cut" \
  out.mkv
```

For full edition authoring (ordered chapters, hidden editions), prefer:

```bash
mkvmerge -o out.mkv --chapters edition.xml in.mkv
```

where `edition.xml` is a Matroska XML chapter file with
`<EditionFlagOrdered>`, `<EditionFlagDefault>`, etc.

---

## 8. Stripping metadata cleanly

`-map_metadata -1` and `-map_chapters -1` remove source metadata, but
ffmpeg still writes its own `encoder=Lavf...` tag. To fully silence it:

```bash
ffmpeg -i in.mp4 -map 0 \
  -map_metadata -1 -map_chapters -1 \
  -c copy \
  -fflags +bitexact \
  -flags:v +bitexact -flags:a +bitexact \
  clean.mp4
```

Verify nothing leaked:

```bash
ffprobe -v error -show_format -show_streams clean.mp4 | grep -iE 'tag|TAG'
```

---

## 9. Handy one-liners

```bash
# Quick title edit, in-place via temp
ffmpeg -i in.mp4 -c copy -metadata title="New title" tmp.mp4 && mv tmp.mp4 in.mp4

# Clear track-0 default flag (useful before setting another as default)
ffmpeg -i in.mkv -c copy -disposition:a:0 0 out.mkv

# Copy all tags AND chapters from A to B
ffmpeg -i B.mkv -i A.mkv \
  -map 0 -map_metadata 1 -map_chapters 1 \
  -c copy B_tagged.mkv

# Dump every tag to a readable file
ffmpeg -i in.mkv -f ffmetadata meta_dump.txt

# Batch-set language on all audio streams (shell loop)
for i in 0 1 2; do
  set -- "$@" -metadata:s:a:$i language=eng
done
ffmpeg -i in.mkv -c copy "$@" out.mkv
```
