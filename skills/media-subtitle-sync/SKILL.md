---
name: media-subtitle-sync
description: >
  Automatic subtitle synchronization with alass and ffsubsync: align SRT/ASS/VTT timings to video audio, fix out-of-sync captions, shift by fixed offset, handle variable drift, framerate mismatch correction. Use when the user asks to sync subtitles, fix out-of-sync SRT, auto-align captions to audio, correct subtitle drift, match translated subs to original video timing, or batch-align a season of subtitle files.
argument-hint: "[subs] [video]"
---

# Media Subtitle Sync

**Context:** $ARGUMENTS

## Quick start

- **Out-of-sync SRT, clean webrip:** → Step 3 (ffsubsync, fast VAD+FFT)
- **TV recording with commercial breaks:** → Step 3 (alass, scene-split aware)
- **Foreign-language sub to aligned reference sub:** → Step 3 (`sync-reference`)
- **Simple constant offset (e.g. "shift +3.5s"):** → Step 3 (`shift`)
- **Season folder of mismatched subs:** → Step 3 (`batch-sync`)

## When to use

- Subtitle file is progressively drifting from audio (framerate mismatch)
- Subtitle has a constant shift (intro/ad removed, shifted start)
- Commercial-break splits broke timing (TV caps on streaming source)
- You have a known-good sub in another language — use it as reference timing
- Need to auto-align an entire season with one command

## Step 1 — Install tools

```bash
brew install alass                 # macOS
# or: download static binary from https://github.com/kaegi/alass/releases

pip install ffsubsync              # Python; needs ffmpeg on PATH
# or: pipx install ffsubsync
```

Verify:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py check
```

Both tools shell out to ffmpeg to extract the reference audio track. alass needs ffmpeg 4+.

## Step 2 — Pick the right tool

| Symptom | Pick |
|---|---|
| Clean webrip, small linear shift | **ffsubsync** — fast, simple VAD+FFT |
| TV rip with commercial breaks, scene cuts | **alass** — splits + linear segment alignment |
| Framerate mismatch (25 ↔ 23.976 ↔ 29.97) | either — both auto-detect |
| Known-good ref sub exists in any language | either with `sync-reference` |
| Video has little/no dialogue (music, animation) | use ref-sub mode; VAD fails on silence |
| You only need a constant offset | `shift` subcommand (no tool needed) |
| Both tools disagree wildly | try ref-sub mode, or manual `shift` |

Unsure → let `--tool auto` try alass first, fall back to ffsubsync.

## Step 3 — Run

### Auto sync (video → subs)

```bash
# Via wrapper (handles tool pick, fallback, dry-run)
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync \
    --video movie.mkv --subs movie.en.srt --output movie.en.synced.srt --tool auto

# Raw alass
alass movie.mkv movie.en.srt movie.en.synced.srt

# alass fast mode (no scene-split analysis, linear only)
alass --no-split movie.mkv movie.en.srt movie.en.synced.srt

# alass with split-penalty tuning (higher = fewer splits)
alass --split-penalty 10 movie.mkv movie.en.srt movie.en.synced.srt

# Raw ffsubsync
ffsubsync movie.mkv -i movie.en.srt -o movie.en.synced.srt

# ffsubsync, disable framerate adjustment (when FR is known-correct)
ffsubsync movie.mkv -i movie.en.srt -o movie.en.synced.srt --no-fix-framerate

# ffsubsync, widen search (default ±60s)
ffsubsync movie.mkv -i movie.en.srt -o movie.en.synced.srt --max-offset-seconds 180
```

### Reference-sub sync (no video audio needed)

Use when the video's audio language differs from the sub language, or when the
video has poor dialogue. The reference sub should be known-good, ideally in the
video's audio language.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync-reference \
    --reference-subs movie.ja.synced.srt --subs movie.en.srt --output movie.en.synced.srt

# Raw alass: swap video for reference srt
alass movie.ja.synced.srt movie.en.srt movie.en.synced.srt
# Raw ffsubsync: same pattern
ffsubsync movie.ja.synced.srt -i movie.en.srt -o movie.en.synced.srt
```

### Fixed constant offset (no tool, pure shift)

Use for "everything is 3.5s late" — no drift, just translation.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift \
    --subs movie.srt --output movie.shifted.srt --seconds 3.5

# Negative shift (subs are ahead)
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift \
    --subs movie.srt --output movie.shifted.srt --seconds -2.1

# Raw ffmpeg equivalent (LINEAR only)
ffmpeg -itsoffset 3.5 -i movie.srt -c copy movie.shifted.srt
```

### Batch (season folder)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py batch-sync \
    --video-dir ./S01 --subs-dir ./S01 --output-dir ./S01/synced --tool alass

# Raw shell loop
for v in *.mkv; do
    base="${v%.mkv}"
    alass "$v" "${base}.srt" "synced/${base}.synced.srt"
done
```

## Step 4 — Verify

1. **Spot-check first and last dialogue.** Open synced SRT, note timestamps of cue #1 and the last cue. Scrub video at those times; dialogue should start ±200 ms of cue.
2. **Check midpoint.** Commercial-break drift only shows mid-file — scrub ~50% through.
3. **Framerate sanity.** If alass reports `framerate ratio 25/23.976` in logs, the source was PAL-speedup. Confirm the synced file sounds in-sync, not just at endpoints.
4. **ffsubsync score.** ffsubsync prints `Score: 0.xx` — below 0.5 means alignment was weak; retry with alass or reference sub.

## Gotchas

- **alass vs ffsubsync differ fundamentally.** ffsubsync = VAD + FFT cross-correlation; fast, great for linear drift. alass = VAD + optional scene-split detection; handles commercial breaks and piecewise-linear drift. TV rip → alass. Webrip → ffsubsync. Both need ffmpeg.
- **Both tools do NOT re-encode video.** Only the subtitle text file is written.
- **Format support differs.** ffsubsync reads `.srt`, `.ass`, `.ssa`, `.vtt`, `.sub`; alass is primarily SRT (convert first via ffmpeg-subtitles skill if needed).
- **Framerate mismatch (25 ↔ 23.976 ↔ 29.97)** is auto-detected by both. Disable with ffsubsync `--no-fix-framerate` when you know FR is correct and only offset is wrong.
- **alass is faster** but requires ffmpeg 4+. On ffmpeg 3.x, force ffsubsync.
- **Reference subtitle must match the video's AUDIO language** for VAD-based alignment. Using an English ref sub against Japanese audio works only in the ref-to-ref mode (no video input).
- **VAD fails on silent video.** Animated content, music videos, opening title cards — ffsubsync will produce low scores and wrong offsets. Use ref-sub mode, or trim the silent prefix first.
- **`--max-offset-seconds`** default is 60. For subs pulled from the wrong release group, widen to 180–300.
- **alass `--split-penalty`** tunes split sensitivity. Raise (≥10) if alass over-splits and adds phantom breaks; lower (≤3) if it misses commercial cuts.
- **When both tools fail,** try manual `shift` — if that works, the problem was constant offset all along (tools over-fit). If it doesn't, the sub is from a different edit/cut of the video; re-download.
- **Encoding / BOM preservation.** ffsubsync preserves input encoding + BOM + line endings. alass always writes UTF-8 LF. If you need Windows-1252 + CRLF out, re-encode after.
- **Silent music/narration mismatch between language tracks** skews VAD alignment. If video has music-only sections that differ between dubs, prefer ref-sub mode over video input.
- **Large files are slow.** Both tools decode full audio. For a 3-hour film, expect 30–90 s. Trim a representative 10-minute section first to dial in settings, then apply full-file.
- **Animated content with minimal dialogue** is a known weak spot for both tools. Expect to fall back to manual `shift` or ref-sub mode.

## Examples

### Example 1: webrip, subs 2s late throughout

```bash
ffsubsync wedding.mkv -i wedding.en.srt -o wedding.en.synced.srt
# or
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync \
    --video wedding.mkv --subs wedding.en.srt --output wedding.en.synced.srt --tool ffsubsync
```

### Example 2: TV broadcast with ad splits

```bash
alass broadcast.ts broadcast.srt broadcast.synced.srt
# If over-splitting:
alass --split-penalty 10 broadcast.ts broadcast.srt broadcast.synced.srt
```

### Example 3: foreign film, only ES subs — align EN subs to them

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync-reference \
    --reference-subs film.es.synced.srt --subs film.en.srt --output film.en.synced.srt
```

### Example 4: constant +4.8 s shift

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift \
    --subs episode.srt --output episode.shifted.srt --seconds 4.8
```

### Example 5: batch season

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py batch-sync \
    --video-dir ./S02 --subs-dir ./S02-subs --output-dir ./S02-synced --tool auto --verbose
```

## Troubleshooting

### Error: `ffmpeg: command not found` (from alass or ffsubsync)

Cause: Both tools shell out to ffmpeg for audio extraction.
Solution: `brew install ffmpeg` (or your platform equivalent); ensure on PATH.

### Error: `alass: unknown format` / alass hangs on `.ass`

Cause: alass is SRT-first. ASS/SSA often fails or is lossy through it.
Solution: Convert to SRT first using the ffmpeg-subtitles skill: `ffmpeg -i in.ass out.srt`. Sync. Convert back if ASS styling is needed.

### ffsubsync score near 0 / alignment obviously wrong

Cause: Silent section in video, wrong release cut, or music-only intro mismatch.
Solution: Try alass. If alass also fails, use ref-sub mode with a known-good sub. Last resort: manual `shift`.

### alass produces garbled timings / mid-file skew

Cause: Over-splitting on false scene cuts.
Solution: Raise `--split-penalty` to 10–20, or use `--no-split` if it's really linear drift.

### Sub is 3-6% consistently drifting

Cause: Framerate mismatch (23.976 ↔ 25). Both tools auto-detect, but can miss.
Solution: Force framerate scaling via ffsubsync (default on). If disabled via `--no-fix-framerate`, remove that flag.

### Output subtitle has wrong encoding

Cause: alass always writes UTF-8 LF; some players want CRLF / Windows-1252.
Solution: Post-process: `iconv -f UTF-8 -t WINDOWS-1252 in.srt > out.srt && unix2dos out.srt`.

### `sync-reference` still produces drift

Cause: Reference sub is itself out of sync, or from a different edit.
Solution: Pick a different reference, or sync the reference to the video first, then use it as ref for the target language.

## Reference docs

- Read [`references/subsync.md`](references/subsync.md) for tool-comparison table, framerate-detection notes, recipe book, and handoff to ffmpeg-subtitles for format conversion.
