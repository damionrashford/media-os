---
name: ffmpeg-subtitle
description: >
  Subtitles and captions end-to-end with ffmpeg and friends. Burn-in (hardcode via subtitles/ass filter), soft-mux (mov_text for MP4, ASS/SRT for MKV, WebVTT for WebM), extract embedded tracks, convert formats (SRT, ASS/SSA, VTT, SUB), style captions. CEA-608/708 closed captions: -a53cc 1 passthrough, ccextractor extraction, SCC/MCC/STL import-export, 608 to SRT, preserve captions in MPEG-TS/MP4/MOV. Auto-sync timing with alass and ffsubsync, fix out-of-sync subs, constant shift, framerate-drift correction, reference-sub alignment, batch a whole season. Use when the user asks to burn subtitles into video, hardcode captions, add soft subtitles, embed or extract SRT/VTT/ASS, convert subtitle format, style captions, extract CEA-608/708 closed captions, preserve broadcast captions during transcode, convert SCC to SRT, sync subtitles, fix out-of-sync SRT, auto-align captions to audio, shift subtitle timing, or batch-align subtitles.
argument-hint: "[action] [video] [subs]"
---

# Ffmpeg Subtitle

**Context:** $ARGUMENTS

Unified skill for everything subtitle- and caption-related: text subtitle files (SRT/ASS/VTT), broadcast closed captions (CEA-608/708, SCC/MCC/STL), and automatic timing sync. Each domain has a full reference doc — load the one matching the task.

## When to use

- Merge an external subtitle file (`.srt`, `.ass`, `.vtt`, `.sub`) into a video, burned-in or soft.
- Extract a subtitle track from MKV/MP4, or convert between subtitle formats.
- Restyle captions (font, size, color, outline, margin) before burning in.
- Preserve, extract, or convert broadcast CEA-608/708 closed captions (MPEG-TS, MP4, MOV, MXF, SCC, MCC, STL).
- Re-encode H.264 broadcast source without losing SEI caption data.
- Fix out-of-sync subtitles: constant offset, framerate drift, commercial-break skew, or align to a reference sub.
- Batch-align a season of subtitle files in one command.

## Techniques

- Read `references/subtitles.md` when the task is text subtitle files: burn-in vs soft-mux vs extract vs convert, the container × `-c:s` codec matrix, `force_style` styling, charset/mojibake fixes. Pair with `references/subtitles-formats.md` for the full option catalog (codec matrix, force_style parameters, ASS color hex, fontfile paths, filter-path escaping).
- Read `references/captions.md` when the task is broadcast closed captions CEA-608/708: detecting embedded SEI, `-a53cc 1` passthrough, ccextractor extraction, SCC/MCC/STL import-export, burning broadcast captions. Pair with `references/captions-formats.md` for 608-vs-708 protocol detail, carriage matrix, file layouts, ccextractor flags, SEI A53 NAL details.
- Read `references/subsync.md` when the task is timing: auto-sync with alass or ffsubsync, constant shift, framerate-drift correction, reference-sub alignment, batch season sync, and the tool-comparison/recipe catalog.

Always invoke the `ffmpeg-docs` skill before recommending an FFmpeg flag or filter — it's the anti-hallucination guardrail.

## Gotchas

- **`force_style` uses ASS colors in `&HAABBGGRR` order — alpha + BGR, not RGB.** Pure red is `&H000000FF`. Half-transparent black outline is `&H80000000`. Omit the `&H` at your peril. (See `references/subtitles.md`.)
- **MP4 only supports `mov_text` for subs; WebM only WebVTT.** `-c:s copy` from SRT/ASS into MP4 fails with "Subtitle codec not supported" — always transcode (`-c:s mov_text` / `-c:s webvtt`). MKV is the friendliest container.
- **Burn-in always re-encodes video** — `-c:v copy` is impossible with `-vf subtitles=...`. Filter-path escaping is three-level (shell → filter graph → libavfilter); wrap POSIX paths containing colons/commas in single quotes.
- **`-a53cc 1` does NOT create captions — it only preserves** existing SEI CC during libx264 re-encode. Re-encoding H.264 broadcast source without it silently drops captions, no warning. `-c:v copy` preserves SEI NAL units automatically.
- **Embedded 608/708 are invisible to `ffprobe -show_streams`** — they live as SEI NAL units inside the video bitstream, not as a subtitle track. ccextractor is a separate tool (`brew install ccextractor`), not bundled with ffmpeg. `readeia608` only reads open captions drawn on NTSC line 21, not SEI.
- **alass vs ffsubsync differ fundamentally.** ffsubsync = VAD + FFT cross-correlation (fast, linear drift, webrips). alass = VAD + scene-split detection (commercial breaks, piecewise-linear drift, TV rips). Both shell out to ffmpeg; alass needs ffmpeg 4+ and writes UTF-8 LF only.
- **VAD-based sync fails on silent/low-dialogue video** (animation, music). Use reference-sub mode (no video audio), and note the ref sub must match the video's AUDIO language. When both tools fail, try manual `shift` — if it works, the issue was constant offset all along.
- **`-itsoffset` does not shift the `subtitles=` burn-in filter** — it shifts an input, but the filter re-reads the file from scratch. To shift burned-in subs, rewrite the SRT timestamps or use the `subsync.py shift` subcommand.

## Scripts

- **`scripts/subs.py`** — stdlib wrapper over the four text-subtitle modes (`burn`, `mux`, `extract`, `convert`). Picks `-c:s` from the output extension, escapes filter paths, `--dry-run`/`--verbose`.
- **`scripts/cc.py`** — closed-caption helper around ffmpeg + ccextractor (`detect`, `preserve`, `extract`, `passthrough`). `--dry-run`/`--verbose`.
- **`scripts/subsync.py`** — timing sync over alass/ffsubsync (`check`, `sync`, `sync-reference`, `shift`, `batch-sync`). Handles tool pick + fallback, `--dry-run`/`--verbose`.

```bash
# Burn SRT into MP4 with styling
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py burn --video in.mp4 --subs subs.srt --output out.mp4 --font Arial --size 28 --color white
# Soft-mux English SRT into MP4
python3 ${CLAUDE_SKILL_DIR}/scripts/subs.py mux --video in.mp4 --subs subs.srt --output out.mp4 --lang eng
# Detect / preserve / extract broadcast captions
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py detect --input in.ts
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py preserve --input in.ts --output out.ts --crf 20
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py extract --input in.ts --output captions.srt
# Auto-sync, reference-sync, constant shift, batch season
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync --video movie.mkv --subs movie.en.srt --output movie.en.synced.srt --tool auto
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py sync-reference --reference-subs movie.ja.synced.srt --subs movie.en.srt --output movie.en.synced.srt
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py shift --subs movie.srt --output movie.shifted.srt --seconds 3.5
uv run ${CLAUDE_SKILL_DIR}/scripts/subsync.py batch-sync --video-dir ./S01 --subs-dir ./S01 --output-dir ./S01/synced --tool alass
```
