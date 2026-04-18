# Subtitle Sync Reference

Deep reference for `media-subtitle-sync`. Read when the SKILL.md quick path
fails — tool internals, framerate detection, manual fixes, recipes.

## Tool comparison

| Aspect | alass | ffsubsync |
|---|---|---|
| Alignment method | VAD on audio track + piecewise-linear + optional scene-split | VAD + FFT cross-correlation (single linear shift + FR scaling) |
| Handles commercial breaks | Yes (splits) | No (single shift per file) |
| Framerate mismatch | Auto-detects 23.976/24/25/29.97/30 | Auto-detects; `--no-fix-framerate` to disable |
| Speed | Faster (native Rust) | Slower (Python + scipy) |
| ffmpeg requirement | ffmpeg 4+ | any modern ffmpeg |
| Formats in | SRT (primary); other formats often fail | SRT, ASS, SSA, VTT, SUB |
| Formats out | SRT (UTF-8 LF) | Same as input; preserves BOM + line endings |
| Reference-sub mode | Yes — swap video for ref SRT | Yes — same positional trick |
| Tuning knobs | `--split-penalty`, `--no-split`, `--disable-fps-guessing` | `--max-offset-seconds`, `--no-fix-framerate`, `--vad` |
| Best for | TV caps with commercials; piecewise drift | Clean webrips; known-correct FR |

## When to pick which

- **Single-number drift across whole file** → ffsubsync (it was designed for this)
- **Drift changes partway** (commercial cut, re-edit, ad pod) → alass
- **Non-dialogue heavy source** (music, animation) → avoid VAD; use reference-sub mode (alass or ffsubsync both work)
- **Multiple subs, same video** (season) → same tool for all; start with alass, fall back to ffsubsync per-file if a score is suspect
- **Wrong release / wrong cut** → neither helps; redownload subs matching the release group

## Framerate detection

PAL speedup (23.976 fps film → 25 fps broadcast) accelerates audio by ~4.27%.
Subs authored for one rate against video at the other drift 4%:

- 2 min in: 5 s off
- 45 min in: ~2 min off

Detection:

```bash
ffprobe -v 0 -select_streams v:0 -show_entries stream=r_frame_rate,avg_frame_rate movie.mkv
```

`24000/1001` = 23.976, `25/1` = PAL, `30000/1001` = NTSC.

Both alass and ffsubsync auto-compute the FR ratio and scale timestamps.
`ffsubsync --no-fix-framerate` forces a pure offset search — useful when you
*know* FR is correct and suspect the tool is mis-detecting.

## When tools fail — manual fixes

### 1. Constant offset only

```bash
# via this skill's shift subcommand
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift \
    --subs in.srt --output out.srt --seconds 3.5

# raw ffmpeg (SRT → SRT with offset; linear only)
ffmpeg -itsoffset 3.5 -i in.srt -c copy out.srt
```

### 2. Two-point timestamp fit (manual rate + offset)

You observed: cue #1 should be at 00:00:12 but file says 00:00:15.2 (−3.2 s),
and cue #N should be at 01:42:07 but file says 01:46:51 (+4.67 s). Compute
rate and offset:

```
rate = (target_end - target_start) / (observed_end - observed_start)
offset = target_start - rate * observed_start
new_t = rate * observed_t + offset
```

Use a spreadsheet or `awk` on the SRT timestamps, or the ref-sub mode — which
computes this automatically when given a known-good ref.

### 3. Commercial-break aware (3+ points)

alass handles this natively. If alass is unavailable, split the SRT at the
break boundary, shift each half independently, concatenate.

### 4. Tools keep picking the wrong alignment

Force a window:

```bash
ffsubsync video.mkv -i subs.srt -o synced.srt --max-offset-seconds 10
```

Narrow `--max-offset-seconds` when you *know* the error is small — prevents
the cross-correlator from locking onto a spurious peak far away.

## Subtitle format conversion handoff

alass is SRT-first. If input is ASS/SSA/VTT/SUB, convert first via the
**ffmpeg-subtitles** skill:

```bash
ffmpeg -i in.ass in.srt         # ASS → SRT (loses styling)
ffmpeg -i in.vtt in.srt         # WebVTT → SRT
ffmpeg -i in.sub -i in.idx in.srt   # VobSub → SRT (needs OCR; use subtile-ocr)
```

Then sync. Then convert back if ASS styling is required — but styling info is
already lost at the first conversion.

ffsubsync preserves input format when the parser supports it — prefer it when
you need to keep ASS styling.

## Recipe book

### Recipe A — Single mis-synced webrip episode

```bash
ffsubsync episode.mkv -i episode.srt -o episode.synced.srt
# verify first/mid/last cue
```

### Recipe B — TV recording with commercial breaks

```bash
alass recording.ts recording.srt recording.synced.srt
# if over-splits:
alass --split-penalty 15 recording.ts recording.srt recording.synced.srt
# if misses breaks:
alass --split-penalty 3 recording.ts recording.srt recording.synced.srt
```

### Recipe C — Foreign-language sync via reference

Video is Korean. You have synced Korean subs and unsynced English subs.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync-reference \
    --reference-subs show.ko.synced.srt \
    --subs show.en.srt \
    --output show.en.synced.srt
```

(VAD against Korean audio using English subs usually fails because dialogue
cadence differs; ref-sub mode sidesteps that entirely.)

### Recipe D — Entire season, single command

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py batch-sync \
    --video-dir "./Show S02" \
    --subs-dir  "./Show S02 subs" \
    --output-dir "./Show S02 synced" \
    --tool auto --fallback --verbose
```

Pairs are matched by filename stem. If your subs are named
`show.S02E05.eng.srt` and videos are `show.S02E05.mkv`, the matcher uses
prefix matching — works as long as the sub stem starts with the video stem.

### Recipe E — Constant shift (known offset)

"Subs are exactly 4.8 seconds early":

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift \
    --subs movie.srt --output movie.srt.shifted --seconds 4.8
mv movie.srt.shifted movie.srt
```

### Recipe F — PAL-speedup correction (23.976 ↔ 25)

When you know the subs were authored against 25fps but video is 23.976:

```bash
ffsubsync movie.mkv -i pal.srt -o fixed.srt
# ffsubsync will auto-compute 23.976/25 ratio; verify midpoint drift is gone
```

### Recipe G — Animated film, both tools fail

Minimal dialogue breaks VAD. Options, in order:

1. Find a ref sub in any language that *is* synced to this release; use `sync-reference`.
2. Manually note two cue-timestamps that should match known events; use two-point fit.
3. If drift is linear only, try `shift` with average of the two residuals.

### Recipe H — Verify with playback

```bash
# Mux synced sub into a quick MKV copy, play
ffmpeg -i movie.mkv -i movie.synced.srt -c copy -c:s srt movie.preview.mkv
ffplay movie.preview.mkv
```

Or use the **ffmpeg-playback** skill's ffplay recipes.

## ffsubsync tuning notes

- `--vad auditok` — alternative VAD (default is `webrtc`); try if default fails
- `--start-seconds N` — skip first N s of video (useful if intro logo confuses VAD)
- `--frame-rate N` — override detected FR
- Low score (<0.5) in stdout = weak alignment; retry with alass or ref sub

## alass tuning notes

- `--split-penalty 10` — raise to suppress spurious splits; lower to allow more splits
- `--no-split` — force linear, no scene detection; fast path
- `--disable-fps-guessing` — skip framerate fit; pure offset
- `--encoding UTF-8` — force input decode encoding
- Output is always UTF-8 LF; re-encode downstream if needed

## Cross-skill handoffs

- Need to convert sub format: **ffmpeg-subtitles**
- Need to burn synced subs into video: **ffmpeg-subtitles** (burn-in)
- Need to generate subs from scratch (ASR): **media-whisper**, then sync
- Need closed-caption (608/708) extraction before sync: **ffmpeg-captions**
- Batch at scale (100s of files with GNU parallel): **media-batch**
- Preview synced output: **ffmpeg-playback**
