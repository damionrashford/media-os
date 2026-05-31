# MKVToolNix reference

A senior engineer's reference for `mkvmerge`, `mkvextract`, `mkvpropedit`,
`mkvinfo`. Nothing here re-encodes; MKVToolNix is a pure Matroska authoring
suite.

## Tool comparison

| Tool          | Purpose                                    | Output                    | Re-mux required? |
|---------------|--------------------------------------------|---------------------------|------------------|
| `mkvmerge`    | Combine tracks, split, append, convert     | New `.mkv` / `.webm`      | Yes (rewrites)   |
| `mkvextract`  | Pull tracks/chapters/tags/attachments out  | Raw essences / XML / text | No (reads only)  |
| `mkvpropedit` | Edit metadata, flags, attachments, chapters| Modifies input in place   | No (header-only) |
| `mkvinfo`     | Inspect EBML structure of a MKV            | Text to stdout            | No               |

Decision tree:

- Need to change container contents (add/remove tracks, cut, append) → `mkvmerge`.
- Need raw essence outside MKV (e.g. `.h264`, `.ac3`, `.srt`) → `mkvextract`.
- Need to flip a flag, rename a track, add a font, correct language tag → `mkvpropedit`.
- Debugging structure / verifying a change → `mkvinfo` or `mkvmerge -J`.

---

## `mkvmerge` — split syntax

`--split MODE:ARGS` where MODE is one of:

### `size:N[K|M|G]`
Split when each output reaches size N.
```
mkvmerge -o part.mkv --split size:700M in.mkv    # CD-sized chunks
mkvmerge -o part.mkv --split size:4G   in.mkv    # FAT32 safe
```

### `timestamps:T1,T2,...`
Split at each absolute timestamp. Format: `HH:MM:SS[.nnn]` or `NNs`.
```
mkvmerge -o p.mkv --split timestamps:00:10:00,00:20:00,00:30:00 in.mkv
```
Produces 4 parts: 0–10, 10–20, 20–30, 30–end.

### `parts:RANGE[,+RANGE...]`
Keep only these absolute ranges. A leading `+` on a subsequent range **glues** it
into the previous output; no `+` starts a **new** output file.
```
# One output, two ranges glued together:
mkvmerge -o out.mkv --split parts:00:00:00-00:10:00,+00:15:00-00:25:00 in.mkv

# Two outputs, one per range:
mkvmerge -o out.mkv --split parts:00:00:00-00:10:00,00:15:00-00:25:00 in.mkv
```

### `parts-frames:FR1-FR2[,+FR3-FR4...]`
Same as `parts:` but in video frame indices.

### `frames:N[,M,...]`
Split every N frames (single value) or at each listed frame index.
```
mkvmerge -o p.mkv --split frames:2500 in.mkv
```

### `chapters:all` | `chapters:N[,M,...]`
Split at every chapter, or at selected chapter indices (1-based).
```
mkvmerge -o ep.mkv --split chapters:all in.mkv
```

### Output pattern
mkvmerge auto-numbers: `part.mkv` → `part-001.mkv`, `part-002.mkv`, ...
Override numeric format with `%Nd` in the name: `chunk-%03d.mkv`.

---

## Track ID and selector conventions

Two distinct numbering systems:

1. **Track ID (0-based, global)** — used by `mkvmerge` for per-input flags and by
   `mkvextract tracks`. Get via `mkvmerge --identify in.mkv` or `-J`:
   ```
   Track ID 0: video (V_MPEG4/ISO/AVC)
   Track ID 1: audio (A_AC3)
   Track ID 2: subtitles (S_TEXT/UTF8)
   ```
2. **Track selector (type + 1-based index)** — used by `mkvpropedit --edit`:
   - `track:v1` = first video track
   - `track:a2` = second audio track
   - `track:s1` = first subtitle track
   - `track:@N` = track whose MKV track-number header equals N
   - `track:=UID` = track whose 128-bit UID equals the hex value

Special selectors for `mkvpropedit`:
- `info` — the segment info element (title, muxing app, writing app).
- `track:1` (no type prefix) also works, but `track:v1` etc. is clearer.

---

## Flag reference (MKV track flags)

Set via `mkvpropedit` `--set KEY=VALUE` or by mkvmerge at merge time.

| Flag                    | Meaning                                                      | Default |
|-------------------------|--------------------------------------------------------------|---------|
| `flag-default`          | "Play this by default if multiple of this type"              | 1       |
| `flag-forced`           | "Player MUST render" (forced subtitles — burn-in translation)| 0       |
| `flag-enabled`          | "Track is available for playback" (0 = hidden)               | 1       |
| `flag-hearing-impaired` | SDH / CC — visual cues for hearing-impaired viewers          | 0       |
| `flag-visual-impaired`  | Audio description / narration for visually-impaired          | 0       |
| `flag-text-descriptions`| Text descriptions (accessibility)                            | 0       |
| `flag-original`         | Content is in the original production language               | 0       |
| `flag-commentary`       | Commentary track                                             | 0       |

Values are `0` or `1`.

```
# Mark a track as SDH closed captions:
mkvpropedit in.mkv --edit track:s1 --set "flag-hearing-impaired=1"

# Mark an audio track as commentary (not default):
mkvpropedit in.mkv --edit track:a3 \
  --set "flag-commentary=1" --set "flag-default=0" --set "name=Director Commentary"
```

At merge time (mkvmerge), the equivalents are `--default-track 0:yes/no`,
`--forced-track 0:yes/no`, `--hearing-impaired-flag 0:yes/no`, etc. (ID `:flag`).

---

## Language codes

MKV stores **two** language fields per track:

- `language` — legacy ISO 639-2/B (three-letter). Always present.
- `language-ietf` — modern BCP-47 (e.g. `en`, `ja`, `pt-BR`, `zh-Hans`). Preferred
  in MKVToolNix 60+.

When set via mkvtoolnix, recent versions populate both. Use BCP-47 in new work.

| Language  | ISO 639-2/B | BCP-47    |
|-----------|-------------|-----------|
| English   | `eng`       | `en`      |
| Japanese  | `jpn`       | `ja`      |
| Chinese (Simplified) | `chi` | `zh-Hans` |
| Chinese (Traditional)| `chi` | `zh-Hant` |
| Spanish (Latin Am.)  | `spa` | `es-419`  |
| Portuguese (Brazil)  | `por` | `pt-BR`   |
| German    | `ger`       | `de`      |
| French    | `fre`       | `fr`      |
| Russian   | `rus`       | `ru`      |
| Korean    | `kor`       | `ko`      |
| Arabic    | `ara`       | `ar`      |
| Undetermined | `und`    | `und`     |

Force-set both:
```
mkvpropedit in.mkv --edit track:a1 \
  --set "language=jpn" --set "language-ietf=ja"
```

---

## Chapter XML schema (abbreviated)

Chapters come in two flavors:

### OGM / simple (legacy)
```
CHAPTER01=00:00:00.000
CHAPTER01NAME=Intro
CHAPTER02=00:01:30.000
CHAPTER02NAME=Act 1
```
Extract: `mkvextract chapters --simple in.mkv > chapters.txt`.

### Matroska XML (richer)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Chapters SYSTEM "matroskachapters.dtd">
<Chapters>
  <EditionEntry>
    <EditionFlagDefault>1</EditionFlagDefault>
    <EditionUID>1234567890</EditionUID>
    <ChapterAtom>
      <ChapterUID>111</ChapterUID>
      <ChapterTimeStart>00:00:00.000000000</ChapterTimeStart>
      <ChapterTimeEnd>00:01:29.999999999</ChapterTimeEnd>
      <ChapterDisplay>
        <ChapterString>Intro</ChapterString>
        <ChapterLanguage>eng</ChapterLanguage>
        <ChapLanguageIETF>en</ChapLanguageIETF>
      </ChapterDisplay>
    </ChapterAtom>
    <ChapterAtom>
      <ChapterUID>112</ChapterUID>
      <ChapterTimeStart>00:01:30.000000000</ChapterTimeStart>
      <ChapterDisplay>
        <ChapterString>Act 1</ChapterString>
        <ChapterLanguage>eng</ChapterLanguage>
      </ChapterDisplay>
    </ChapterAtom>
  </EditionEntry>
</Chapters>
```

Workflow: `mkvextract chapters in.mkv > template.xml`, edit, then
`mkvpropedit in.mkv --chapters template.xml`.

---

## Attachment MIME types

Common types accepted by Matroska attachments:

| Extension   | MIME type                               |
|-------------|-----------------------------------------|
| `.ttf`      | `application/x-truetype-font`           |
| `.otf`      | `application/x-opentype-font` (or `application/vnd.ms-opentype`) |
| `.jpg`/`.jpeg` | `image/jpeg`                         |
| `.png`      | `image/png`                             |
| `.webp`     | `image/webp`                            |
| `.pdf`      | `application/pdf`                       |
| `.txt`      | `text/plain`                            |
| `.xml`      | `application/xml`                       |
| `.zip`      | `application/zip`                       |

Add:
```
mkvpropedit in.mkv \
  --attachment-mime-type application/x-truetype-font \
  --attachment-name "MainFont" \
  --attachment-description "Dialogue font for ASS subs" \
  --add-attachment dialogue.ttf
```

Note MIME flags go **before** `--add-attachment`.

---

## Recipe book

### Anime fansub release (video + dual audio + dual subs + fonts)

```bash
mkvmerge -o "Show S01E01 [1080p BD].mkv" \
  --title "Show - S01E01 - The Beginning" \
  --language 0:jpn --track-name 0:"Video" video.h264 \
  --language 0:jpn --track-name 0:"Japanese FLAC 2.0" --default-track 0:yes audio_jpn.flac \
  --language 0:eng --track-name 0:"English AC3 5.1" --default-track 0:no audio_eng.ac3 \
  --language 0:eng --track-name 0:"English Dialogue" --default-track 0:yes subs_en.ass \
  --language 0:eng --track-name 0:"Signs & Songs" --forced-track 0:yes --default-track 0:no subs_sns.ass \
  --attachment-mime-type application/x-truetype-font --attach-file fonts/DialogueRegular.ttf \
  --attachment-mime-type application/x-truetype-font --attach-file fonts/DialogueBold.ttf \
  --attachment-mime-type application/x-opentype-font --attach-file fonts/Titles.otf
```

### Archive a full season into CD-sized chunks

```bash
for ep in S01E*.mkv; do
  mkvmerge -o "archive/${ep%.mkv}-part-%03d.mkv" --split size:700M "$ep"
done
```

### Correct a wrong language tag (no re-mux)

```bash
# Inspect
mkvmerge -J wrong.mkv | jq '.tracks[] | {id, type: .type,
  codec: .codec, lang: .properties.language,
  ietf: .properties.language_ietf, name: .properties.track_name}'

# Fix audio track 1 from "und" to Japanese (both fields)
mkvpropedit wrong.mkv --edit track:a1 \
  --set "language=jpn" --set "language-ietf=ja" \
  --set "name=Japanese 2.0"
```

### Font-attach for ASS subs (post-mux)

```bash
for f in fonts/*.ttf; do
  mkvpropedit episode.mkv \
    --attachment-mime-type application/x-truetype-font \
    --add-attachment "$f"
done
for f in fonts/*.otf; do
  mkvpropedit episode.mkv \
    --attachment-mime-type application/x-opentype-font \
    --add-attachment "$f"
done
```

### Flip default subtitle track

```bash
mkvpropedit show.mkv --edit track:s1 --set "flag-default=0"
mkvpropedit show.mkv --edit track:s2 --set "flag-default=1"
```

### Extract all subs from a season

```bash
for f in S01E*.mkv; do
  # get subtitle track IDs
  ids=$(mkvmerge -J "$f" | jq -r '.tracks[] | select(.type == "subtitles") | .id')
  args=()
  for id in $ids; do
    args+=("$id:${f%.mkv}.sub${id}.srt")
  done
  mkvextract tracks "$f" "${args[@]}"
done
```

### Strip metadata bloat (tags + chapters + attachments)

```bash
mkvmerge -o clean.mkv --no-global-tags --no-track-tags --no-chapters --no-attachments dirty.mkv
```

### Concatenate split episodes

```bash
# Requires identical codecs/resolution/timebase
mkvmerge -o full.mkv part1.mkv + part2.mkv + part3.mkv
```

### Batch re-mux (defragment + refresh headers)

```bash
for f in *.mkv; do
  mkvmerge -o "remuxed/$f" "$f"
done
```

### Extract a cover-art JPEG from attachments

```bash
id=$(mkvmerge -J movie.mkv | jq -r '.attachments[] | select(.content_type == "image/jpeg") | .id' | head -1)
mkvextract attachments movie.mkv "${id}:cover.jpg"
```

---

## JSON output for pipelines

`mkvmerge -J in.mkv` returns a stable JSON schema with:
- `attachments[]` — `{id, file_name, content_type, size, description}`
- `chapters[]` — `{num_entries}`
- `container` — `{type, recognized, supported, properties}`
- `file_name`
- `global_tags[]`, `track_tags[]`
- `tracks[]` — per track: `{id, type, codec, properties: {language, language_ietf, default_track, forced_track, enabled_track, track_name, display_dimensions, pixel_dimensions, audio_channels, audio_sampling_frequency, number, uid, codec_id, codec_private_length, ...}}`

Example filter:
```bash
mkvmerge -J in.mkv | jq '.tracks[] | {id, type, codec, default: .properties.default_track, lang: .properties.language_ietf // .properties.language}'
```

---

## Cross-reference

- Re-encoding or MKV → MP4 → see `ffmpeg-transcode`.
- Cutting with re-encode across GOP boundaries → see `ffmpeg-cut-concat`.
- Subtitle format conversion (SRT ↔ ASS ↔ VTT) → see `ffmpeg-subtitles`.
- Deep container probe beyond `mkvinfo` → see `media-mediainfo` / `ffmpeg-probe`.
- Multi-DRM CMAF/DASH/HLS packaging → see `media-shaka`.
