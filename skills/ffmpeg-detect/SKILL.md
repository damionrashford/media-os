---
name: ffmpeg-detect
description: >
  Detect-and-act workflows with ffmpeg analysis filters: cropdetect (autocrop black bars), silencedetect, blackdetect, freezedetect, blurdetect, blockdetect, scdet (scene-change detection), idet (interlace detection), signalstats broadcast QC, readeia608 (CEA-608 caption read), readvitc (VITC timecode read). Use when the user asks to autocrop black bars, detect silences, find black frames, detect scene cuts, check if video is interlaced, find freeze frames, auto-split on scene changes, read embedded timecode, or parse detection output into cut points.
argument-hint: "[detector] [input]"
---

# Ffmpeg Detect

**Context:** $ARGUMENTS

Detect-and-act filters in ffmpeg are read-only analysis passes. They write findings to **stderr** (and/or frame metadata under `lavfi.*`), never modify the file, and are designed to be parsed by a script that then issues a second ffmpeg call with real parameters.

## Quick start

- **Autocrop black bars:** → Step 1 (`cropdetect`) → Step 3 (apply `crop=W:H:X:Y`)
- **Trim silences:** → Step 1 (`silencedetect`) → Step 3 (cut with `-ss`/`-to` pairs)
- **Find black frames / scene cuts:** → Step 1 (`blackdetect` / `scdet`) → Step 3 (split with concat demuxer)
- **Check if interlaced:** → Step 1 (`idet`) → Step 3 (decide on `yadif`/`bwdif`)
- **Broadcast QC:** → Step 1 (`signalstats`) → Step 3 (flag out-of-range YMIN/YMAX/SATMAX)
- **Read embedded captions / timecode:** → `readeia608`, `readvitc`
- **Pre-loudnorm audio stats:** → `volumedetect`, `astats` (use `loudnorm` from ffmpeg-audio-filter for true LUFS)

## When to use

- You need to compute parameters (crop rect, cut list, LUT threshold) from a media file before doing a real encode.
- You're doing QC on broadcast or archival content and need per-frame statistics.
- You're auto-splitting a long capture on scene changes or silences.
- You're deciding whether to deinterlace before a delivery encode.

Use **ffmpeg-quality** for reference-vs-distorted measurement (VMAF/PSNR/SSIM). Use **ffmpeg-probe** for container/codec structure — `detect` filters are for *content* analysis.

## Step 1 — Pick the detector

| Goal | Filter | Typical command tail |
|---|---|---|
| Autocrop | `cropdetect` | `-vf cropdetect=limit=24:round=2 -f null -` |
| Silences in audio | `silencedetect` | `-af silencedetect=noise=-30dB:d=0.5 -f null -` |
| Black segments | `blackdetect` | `-vf blackdetect=d=1:pix_th=0.1 -f null -` |
| Freeze frames | `freezedetect` | `-vf freezedetect=n=0.001:d=0.5 -f null -` |
| Blur QC | `blurdetect` | `-vf blurdetect -f null -` |
| Blocking QC | `blockdetect` | `-vf blockdetect -f null -` |
| Scene cuts | `scdet` | `-vf "scdet=s=1:t=10" -f null -` |
| Interlace | `idet` | `-vf idet -f null -` |
| Broadcast QC | `signalstats` | `-vf signalstats -f null -` |
| CEA-608 captions | `readeia608` | `-vf readeia608 -f null -` |
| VITC timecode | `readvitc` | `-vf readvitc -f null -` |
| Volume (peak/mean dB) | `volumedetect` | `-af volumedetect -f null -` |

All of these pair with `-f null -` (video) or route to `-f null -` (audio) so no file is written. The filter's output lives in stderr. Add `-hide_banner` to reduce noise. Seek first (`-ss`) and limit (`-t`) for fast sampling on long files.

## Step 2 — Run and parse stderr / metadata

ffmpeg writes detector lines to stderr. Standard pattern:

```bash
ffmpeg -hide_banner -i IN -vf FILTER -f null - 2>&1 | grep PATTERN
```

Per-detector regexes (see `references/detectors.md` for full catalog):

- `cropdetect` → `crop=\d+:\d+:\d+:\d+` (take last match — stabilizes over time).
- `silencedetect` → `silence_start: ([\d.]+)` and `silence_end: ([\d.]+) \| silence_duration: ([\d.]+)` — pair consecutive start/end lines.
- `blackdetect` → `black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)` (all on one line).
- `freezedetect` → `freeze_start: ([\d.]+)`, `freeze_duration: ([\d.]+)`, `freeze_end: ([\d.]+)`.
- `scdet` → `lavfi.scd.score` / `lavfi.scd.time` in metadata (with `-f null -` and `scdet=s=1` prints to stderr).
- `idet` → three summary lines at end: `Single frame detection`, `Multi frame detection`, `Repeated Fields`. Use **Multi frame** for decision.
- `signalstats` → per-frame metadata keys `lavfi.signalstats.{YAVG,YMIN,YMAX,UMIN,UMAX,VMIN,VMAX,SATMIN,SATMAX,HUEMED,HUEAVG,YDIF,UDIF,VDIF,SATDIF,TOUT,VREP}`. Extract with `-show_frames` on a second ffprobe pass, or with `metadata=mode=print`.
- `readeia608` → `lavfi.readeia608.X.cc` bytes — pipe to `-f srt` or parse manually for proper caption extraction.
- `readvitc` → `lavfi.readvitc.tc_str=HH:MM:SS:FF` per frame.
- `volumedetect` → `mean_volume: X dB`, `max_volume: Y dB` at end of run.

For metadata keys, the idiomatic pattern is:

```bash
ffmpeg -i IN -vf "signalstats,metadata=mode=print:file=-" -f null - 2>/dev/null
```

## Step 3 — Turn parsed output into actionable parameters

**Autocrop (two commands):**
```bash
# Sample from 10s in, 120s long — skip opening credits / fades
ffmpeg -hide_banner -ss 10 -i in.mp4 -t 120 -vf cropdetect=limit=24:round=2 \
  -f null - 2>&1 | grep -o 'crop=[0-9:]*' | tail -1
# → crop=1920:816:0:132
ffmpeg -i in.mp4 -vf crop=1920:816:0:132 -c:a copy out.mp4
```

**Silence trim:** parse silencedetect lines, invert to "keep" segments, pass to concat demuxer or `-ss`/`-to` pairs. See `scripts/detect.py silences` for JSON output.

**Scene-split chapters:** feed `scdet` timestamps to `ffmpeg-cut-concat` skill to segment on cuts.

**Interlace decision:** if `Multi frame detection` shows `TFF > 100 && progressive < 10` → `-vf yadif=1:0` (TFF). If `BFF > progressive` → `-vf yadif=1:1` (BFF). If progressive dominates → skip deinterlace.

**Broadcast QC:** flag any frame where `YMIN < 16` or `YMAX > 235` (limited-range violation), `SATMAX > 118.2` (NTSC 75% bars), or `TOUT > 0.005` (temporal outlier / dropout).

## Available scripts

- **`scripts/detect.py`** — argparse dispatcher with subcommands `crop`, `silences`, `blacks`, `freezes`, `scenes`, `interlace`, `stats`, `volume`. All return JSON (or a ready-to-use crop string for `crop`). Stdlib only, non-interactive.

## Workflow

```bash
# Autocrop
uv run ${CLAUDE_SKILL_DIR}/scripts/detect.py crop --input in.mp4
# Silences → JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/detect.py silences --input in.mp3 --noise-db -30 --min-duration 0.5
# Scene cuts
uv run ${CLAUDE_SKILL_DIR}/scripts/detect.py scenes --input in.mp4 --threshold 10
# Interlace decision
uv run ${CLAUDE_SKILL_DIR}/scripts/detect.py interlace --input broadcast.ts
```

## Reference docs

- Read [`references/detectors.md`](references/detectors.md) for per-filter option tables, example stderr, regex patterns, signalstats metadata keys, idet interpretation, and recipes (auto-chapter, silence-trim, broadcast QC pass).

## Gotchas

- **Detector output is stderr, not stdout.** Pipe with `2>&1` before `grep`/`awk`. `-progress` gives machine-readable progress but NOT filter output.
- **`cropdetect` needs 100–200 frames of content.** Run with `-ss 10` past fades/credits and `-t 60–120` to keep it fast. It updates over time; take the *last* `crop=` line.
- **`cropdetect limit=24`** = black threshold on 0–255 scale (8-bit). Raise to 32–40 for lighter grey letterbox bars. `round=2` keeps even dims (required by most codecs); `round=16` for strict macroblock alignment.
- **`silencedetect noise=-30dB:d=0.5`** — duration in seconds. Below `-60dB` is near-digital silence; `-30dB` is room tone. Each silence emits TWO lines (`silence_start`, then `silence_end` with `silence_duration`) — pair them.
- **`blackdetect`** outputs `black_start`, `black_end`, `black_duration` all on one line. `pix_th=0.1` = pixel blackness threshold (normalized 0–1).
- **`freezedetect n=0.001:d=0.5`** — `n` is noise tolerance (normalized 0–1), `d` is minimum freeze duration in seconds.
- **`scdet t=THRESH`** — threshold on 0–100 score scale. Typical 10 (lots of cuts) to 30 (only hard cuts). Use `s=1` to emit one line per detected cut with score + time.
- **`idet` prints THREE summary blocks at end:** *single-frame detection*, *multi-frame detection*, and *repeated fields*. Use **multi-frame** for the decision (it uses more temporal context). Run on at least ~1000 frames (~40s at 24fps) for confidence. One run is often noisy — re-run with a different segment if counts are ambiguous.
- **`signalstats` per-frame metadata lives in `lavfi.signalstats.*`.** Extract via `ffprobe -show_frames` OR the `metadata=mode=print` filter. Filter alone writes nothing to stderr by default.
- **`readeia608` only works on SD broadcast content** with CEA-608 bytes on VBI lines 0–1 (or via captions sidecar). It does NOT read CEA-708, teletext, or burned-in subs. See the **ffmpeg-captions** skill for a full pipeline.
- **All detect filters are READ-ONLY.** `-f null -` sinks output. Nothing is written to disk unless you explicitly add `-y output.ext` *without* `-f null`.
- **`volumedetect` gives peak + mean dBFS, NOT LUFS.** For loudness compliance (EBU R128 / ITU-R BS.1770) use `loudnorm=print_format=summary` from the **ffmpeg-audio-filter** skill.
- **Scene-cut list → split:** feed scdet timestamps to the **ffmpeg-cut-concat** skill (concat demuxer or segment muxer). Do not try to encode concatenated output in a single ffmpeg call — use stream copy on pre-split clips.

## Examples

### Example 1: Autocrop letterboxed film

```bash
ffmpeg -hide_banner -ss 30 -i movie.mkv -t 180 \
  -vf cropdetect=limit=24:round=2 -f null - 2>&1 \
  | grep -o 'crop=[0-9:]*' | tail -1
# → crop=1920:800:0:140
ffmpeg -i movie.mkv -vf crop=1920:800:0:140 -c:v libx264 -crf 18 -c:a copy cropped.mkv
```

### Example 2: Generate a silence-trim cut list

```bash
ffmpeg -hide_banner -i podcast.wav -af silencedetect=noise=-35dB:d=0.8 \
  -f null - 2>&1 | grep silence_
# silence_start: 12.3
# silence_end: 14.8 | silence_duration: 2.5
# silence_start: 120.4
# silence_end: 121.2 | silence_duration: 0.8
```

Invert to "keep" ranges `0–12.3`, `14.8–120.4`, `121.2–END`, then use ffmpeg-cut-concat.

### Example 3: Interlace detection on broadcast capture

```bash
ffmpeg -hide_banner -i capture.ts -vf idet -f null - 2>&1 | grep "frame detection"
# [Parsed_idet_0 @ ...] Multi frame detection: TFF:  982 BFF:   3 Progressive:  15 Undetermined: 0
```

Decision: TFF dominates → `-vf yadif=1:0` in the delivery encode.

### Example 4: Broadcast QC gate

```bash
ffmpeg -hide_banner -i master.mov \
  -vf "signalstats,metadata=mode=print:key=lavfi.signalstats.YMAX:file=ymax.log" \
  -f null -
awk -F= '$2+0 > 235 {print}' ymax.log   # any frame over legal range
```

## Troubleshooting

### Error: `cropdetect` returns no `crop=` line
Cause: input segment is all-black or too short (<100 frames).
Solution: seek further in with `-ss 30`, extend duration with `-t 120`, lower `limit` (e.g. `limit=16`) for very dark content.

### Error: `silencedetect` emits `silence_start` but no matching `silence_end`
Cause: file ends during a silence segment.
Solution: treat the final `silence_start` as silence until duration end; ffprobe the duration and synthesize the end timestamp.

### Error: `idet` counts look random / change between runs
Cause: too few frames sampled, or the clip has mixed progressive + interlaced sections.
Solution: sample at least 1000 frames, run on multiple segments (`-ss 0`, `-ss 60`, `-ss 300`) and compare. Mixed content needs frame-by-frame idet metadata rather than summary.

### Error: `readeia608` returns empty / no metadata
Cause: content is HD (CEA-708, not 608), or captions are in a sidecar/subtitle track rather than in VBI.
Solution: use the **ffmpeg-captions** skill for CEA-708 / SCC / MCC extraction. `readeia608` only sees SD VBI line bytes.

### Error: `signalstats` gives no output
Cause: the filter populates frame metadata, not stderr.
Solution: add `,metadata=mode=print:file=-` to the filter chain, or use `ffprobe -show_frames -of json` on a re-encoded null output.

### Error: `volumedetect` output shows only `n_samples`, no `mean_volume`
Cause: ffmpeg didn't finish processing (piped output was broken, or input stream had zero audio frames).
Solution: ensure `-f null -` is the sink and stderr is captured; verify input has audio with `ffprobe -show_streams -select_streams a`.
