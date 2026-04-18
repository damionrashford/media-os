---
name: ffmpeg-subtitles
description: >
  Work with subtitles in ffmpeg: burn-in (hardcode via subtitles/ass filter), soft-mux (mov_text for MP4, ASS/SRT for MKV, WebVTT for WebM), extract embedded subs, convert formats (SRT, ASS/SSA, VTT, SUB). Use when the user asks to burn subtitles into video, hardcode captions, add soft subtitles, embed SRT/VTT/ASS, extract subs from a file, convert subtitle format, style captions, or sync subtitle timing.
argument-hint: "[action] [video] [subs]"
---

# Ffmpeg Subtitles

**Context:** $ARGUMENTS

## Quick start

- **Burn (hardcode) SRT into MP4:** → Step 1 (mode = burn-in), Step 3 example A
- **Soft-embed SRT into MP4:** → Step 1 (mode = soft-mux), Step 3 example B
- **Extract embedded track from MKV:** → Step 1 (mode = extract), Step 3 example C
- **Convert SRT → ASS or VTT:** → Step 1 (mode = convert), Step 3 example D
- **Style caption fonts / colors:** → Step 3 example A + `references/formats.md` force_style section
- **Fix garbled accented characters:** → Gotchas (charset) + Troubleshooting

## When to use

- You have a video and an external subtitle file (`.srt`, `.ass`, `.vtt`, `.sub`) and need them merged or displayed.
- You need to extract a subtitle track from an MKV/MP4 to edit or re-use.
- You need to convert between subtitle formats while preserving timing.
- You need to sync / shift subtitle timing to match a re-cut video.
- You need to restyle captions (font, size, color, outline, margin) before burning in.

## Step 1 — Pick mode

Decide one of the four modes. Every decision downstream depends on this:

| Mode | Use when | Re-encodes video? |
| --- | --- | --- |
| `burn-in` | Player won't support soft subs (social media upload, VP9/AV1 on some devices), or you want captions baked in permanently. | **Yes** (must re-encode video) |
| `soft-mux` | You want a toggleable subtitle track the player can turn off. | No (video can be `-c:v copy`) |
| `extract` | Pull an embedded sub track out to a standalone file. | No (no video path at all) |
| `convert` | Change subtitle format only (SRT ↔ ASS ↔ VTT ↔ SUB). | No (no video path at all) |

## Step 2 — Match container to subtitle codec

Containers only accept certain subtitle codecs. Pick the right `-c:s` for the output extension:

| Output container | Valid `-c:s` values | Notes |
| --- | --- | --- |
| `.mp4` / `.mov` / `.m4v` | `mov_text` **only** | `-c:s copy` from SRT/ASS into MP4 **fails** — always transcode to `mov_text`. |
| `.mkv` | `copy`, `srt` / `subrip`, `ass`, `ssa`, `webvtt`, `dvdsub`, `dvbsub` | MKV is the friendliest container. |
| `.webm` | `webvtt` **only** | Must convert SRT/ASS → WebVTT first (or let ffmpeg do it via `-c:s webvtt`). |
| `.ts` / `.m2ts` | `dvbsub`, `dvdsub`, `hdmv_pgs_subtitle` | Bitmap subs only in transport streams. |

See `references/formats.md` for the full matrix.

## Step 3 — Run the command

All examples produce output you can verify with `ffprobe -v error -show_streams -select_streams s <file>`.

### A) Burn-in SRT with styling

```bash
ffmpeg -i in.mp4 \
  -vf "subtitles=subs.srt:force_style='Fontname=Arial,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,MarginV=60'" \
  -c:v libx264 -crf 20 -preset medium -c:a copy out.mp4
```

Burn-in **always re-encodes video** — `-c:v copy` is not possible. Use the `ass` filter instead when the subtitle file is ASS/SSA (it respects the file's own styling):

```bash
ffmpeg -i in.mp4 -vf "ass=subs.ass" -c:v libx264 -crf 20 -c:a copy out.mp4
```

### B) Soft-mux

MP4 (SRT source → `mov_text`):

```bash
ffmpeg -i in.mp4 -i subs.srt -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng -disposition:s:0 default out.mp4
```

MKV (keep original sub format):

```bash
ffmpeg -i in.mkv -i subs.srt -c copy -c:s srt -metadata:s:s:0 language=eng out.mkv
```

WebM:

```bash
ffmpeg -i in.webm -i subs.srt -c:v copy -c:a copy -c:s webvtt out.webm
```

Multiple tracks at once:

```bash
ffmpeg -i in.mp4 -i en.srt -i fr.srt \
  -map 0 -map 1 -map 2 -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng -metadata:s:s:1 language=fra out.mp4
```

### C) Extract embedded subtitle track

```bash
ffmpeg -i in.mkv -map 0:s:0 -c:s copy subs.srt          # copy if already SRT
ffmpeg -i in.mkv -map 0:s:0 -c:s srt subs.srt            # transcode ASS → SRT
ffmpeg -i in.mkv -map 0:s:0 -c:s webvtt subs.vtt         # transcode → VTT
```

### D) Convert format

```bash
ffmpeg -i subs.srt subs.ass                              # SRT → ASS
ffmpeg -i subs.ass subs.vtt                              # ASS → VTT
ffmpeg -sub_charenc CP1252 -i subs.srt -c:s srt out.srt  # re-save non-UTF-8 as UTF-8
```

## Step 4 — Verify

```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name:stream_tags=language \
  -of csv=p=0 out.mp4
```

For burn-in, visually spot-check one segment:

```bash
ffmpeg -ss 00:00:30 -i out.mp4 -frames:v 1 frame.png
```

## Available scripts

- **`scripts/subs.py`** — stdlib-only wrapper over the four modes (`burn`, `mux`, `extract`, `convert`). Picks the correct `-c:s` from the output extension, escapes filter paths for burn-in, supports `--dry-run` and `--verbose`.

## Workflow

```bash
# Burn SRT into MP4 with styling
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py burn \
  --video in.mp4 --subs subs.srt --output out.mp4 \
  --font Arial --size 28 --color white

# Soft-mux an English SRT into MP4
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py mux \
  --video in.mp4 --subs subs.srt --output out.mp4 --lang eng

# Extract first embedded subtitle stream
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py extract \
  --input movie.mkv --stream 0 --output movie.srt

# Convert SRT → ASS (extension-driven)
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py convert \
  --input subs.srt --output subs.ass
```

## Reference docs

- Read [`references/formats.md`](references/formats.md) for the container × codec matrix, the full `force_style` parameter list, ASS color hex format, per-format feature comparison, common fontfile paths, and filter-path escaping rules.

## Gotchas

- **MP4 only supports `mov_text` for subs.** `-c:s copy` from SRT/ASS to MP4 fails with `Subtitle codec X not supported by output format`. Always use `-c:s mov_text`.
- **WebM only supports WebVTT.** Same class of error — use `-c:s webvtt`.
- **Burn-in always re-encodes video.** You cannot use `-c:v copy` with `-vf subtitles=...`.
- **Filter path escaping is three-level** (shell → filter graph → libavfilter). A Windows path like `C:\subs\foo.srt` must become `subtitles='C\\:\\\\subs\\\\foo.srt'`. On POSIX, wrap paths with colons or commas in single quotes: `-vf "subtitles='my:file.srt'"`. The included `subs.py` does this for you.
- **`force_style` uses ASS colors in `&HAABBGGRR` order — alpha + BGR, not RGB.** Pure red is `&H000000FF`. Half-transparent black outline is `&H80000000`. Omit the `&H` at your peril.
- **Styling inside an SRT file is ignored.** SRT tags like `<font>` / `{\b1}` are not reliably rendered; convert to ASS first (`ffmpeg -i x.srt x.ass`) and edit there, then `-vf ass=x.ass`.
- **Non-UTF-8 SRTs render as mojibake.** Western European files are often CP1252 or ISO-8859-1. Prepend input with `-sub_charenc CP1252` (only works on `-i file.srt`, not on the `-vf subtitles=` filter). For burn-in with a legacy charset, first re-save the SRT as UTF-8.
- **`fontconfig` must be available at runtime.** Without it, `Fontname=Arial` silently falls back to a bundled default and Unicode glyphs may drop. Either install fontconfig or use `fontfile=` with an absolute path.
- **`stream_index` selects a track when the subtitle file itself has multiple streams:** `subtitles=movie.mkv:stream_index=2` burns in the third embedded track.
- **Default subtitle disposition:** players auto-enable the track with `disposition default`. Set explicitly with `-disposition:s:0 default` (or `-disposition:s:0 0` to clear).
- **`-itsoffset` does not shift the `subtitles=` filter.** `-itsoffset` shifts an *input*; the `subtitles` filter re-reads the file from scratch and ignores demuxer offsets. To shift a burn-in SRT, either (a) rewrite the SRT timestamps, or (b) soft-mux with `-itsoffset 2 -i subs.srt` and re-extract.
- **`subrip` and `srt` are the same codec** — ffmpeg accepts either name for `-c:s`.
- **MKV auto-selects on first matching language tag.** If you mux two English tracks, the second one won't be picked by default — use `-disposition:s:N default` and clear the other.

## Examples

### Example 1: YouTube upload with burned-in captions

```bash
ffmpeg -i raw.mp4 \
  -vf "subtitles=captions.srt:force_style='Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=80,Alignment=2'" \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k out.mp4
```

Result: YouTube-safe H.264/AAC MP4 with always-visible bottom-center captions (Alignment=2 = bottom-center).

### Example 2: Archival MKV with three soft subtitle tracks

```bash
ffmpeg -i film.mkv -i en.srt -i es.srt -i fr.srt \
  -map 0:v -map 0:a -map 1 -map 2 -map 3 \
  -c:v copy -c:a copy -c:s srt \
  -metadata:s:s:0 language=eng -metadata:s:s:0 title="English" \
  -metadata:s:s:1 language=spa -metadata:s:s:1 title="Español" \
  -metadata:s:s:2 language=fra -metadata:s:s:2 title="Français" \
  -disposition:s:0 default out.mkv
```

### Example 3: Extract, shift by +2 s, re-mux

```bash
ffmpeg -i in.mkv -map 0:s:0 -c:s srt orig.srt
# shift SRT timestamps with any tool, then:
ffmpeg -i in.mkv -i shifted.srt -map 0:v -map 0:a -map 1 \
  -c copy -c:s srt out.mkv
```

## Troubleshooting

### Error: `Subtitle codec 94213 [0][0][0][0] / 0x17F05 is not supported by this version of FFmpeg`

**Cause:** you tried `-c:s copy` into an MP4 with a non-`mov_text` subtitle.
**Solution:** use `-c:s mov_text`.

### Error: `Unable to parse option value "&H00FFFFFF" as image size`

**Cause:** missing quotes around `force_style` — the comma inside it is being parsed as a filter separator.
**Solution:** wrap the whole `force_style` block in single quotes: `force_style='Fontname=Arial,Fontsize=24'`.

### Error: `No such filter: 'subtitles'`

**Cause:** ffmpeg built without `--enable-libass`.
**Solution:** install a full build (`brew install ffmpeg`, `apt install ffmpeg`) — the "minimal" / `ffmpeg-lite` builds omit libass.

### Symptom: accented characters display as `Ã©`, `Ã¨`, etc.

**Cause:** SRT is CP1252/Latin-1 but ffmpeg is reading it as UTF-8.
**Solution:** add `-sub_charenc CP1252` before the `-i subs.srt`. For the `subtitles=` filter (burn-in), convert the file to UTF-8 first: `iconv -f CP1252 -t UTF-8 in.srt > out.srt`.

### Symptom: subtitles render in the wrong font or drop Unicode glyphs

**Cause:** fontconfig missing, or the named font not installed.
**Solution:** either install the font / fontconfig, or switch to `fontfile=`: `subtitles=subs.srt:fontsdir=/System/Library/Fonts:force_style='Fontname=Helvetica'`.

### Symptom: soft-muxed subs don't show up in QuickTime / iOS

**Cause:** only `mov_text` works in MP4 on Apple players, and the track needs a language tag + default disposition.
**Solution:** `-c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 default`.
