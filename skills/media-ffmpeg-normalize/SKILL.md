---
name: media-ffmpeg-normalize
description: >
  Higher-level EBU R128 loudness normalization with ffmpeg-normalize: 2-pass loudnorm batch wrapper, target loudness/TP/LRA, preserves streams, works across directories, output format selection, dry-run plan. Use when the user asks to batch-normalize audio loudness, apply EBU R128 across many files, use ffmpeg-normalize (not raw loudnorm), set-and-forget loudness processing for a podcast library, or do broadcast-compliant loudness normalization at scale.
argument-hint: "[input]"
---

# Media Ffmpeg Normalize

**Context:** $ARGUMENTS

`ffmpeg-normalize` is a Python wrapper around ffmpeg's `loudnorm` filter that automates proper **2-pass EBU R128** normalization, batch directories, and preserves non-audio streams. Raw `loudnorm` is 1-pass by default (dynamic, inaccurate); this tool does the measure-then-apply pass automatically.

## Quick start

- **Normalize one file (EBU R128 -23 LUFS default):** `ffmpeg-normalize in.mp3 -o out.mp3` → Step 3
- **Streaming target (-14 LUFS YouTube/Spotify):** `ffmpeg-normalize in.wav -t -14 -o out.wav` → Step 2
- **Batch a podcast folder:** `ffmpeg-normalize episodes/*.mp3 -of out/ -t -16 -tp -1.5 -lrt 11` → Step 3
- **Video (keep video stream, re-encode audio only):** `ffmpeg-normalize in.mp4 -c:a aac -b:a 192k -o out.mp4` → Step 3

## When to use

- Batch-normalizing many files to one target loudness (podcast archive, music library, course videos).
- You want proper 2-pass EBU R128 without wiring the `loudnorm` JSON round-trip yourself (see `ffmpeg-audio-filter` skill if you need manual control).
- Delivering to broadcast, streaming platforms, or archives with an LUFS spec.
- **Don't use** for cross-file consistency (e.g., album-gain style). Each file is normalized independently. For consistent relative levels across a set, use a single manual 2-pass `loudnorm` with a shared measurement, per the `ffmpeg-audio-filter` skill.

## Step 1 — Install

```bash
pip install ffmpeg-normalize
# or with uv
uv tool install ffmpeg-normalize
```

Requires `ffmpeg` on `PATH`. Verify:
```bash
ffmpeg-normalize --version
ffmpeg -hide_banner -filters | grep loudnorm
```

## Step 2 — Pick a target

Decide the **three EBU R128 parameters**:

| Flag | Meaning | Typical value |
|------|---------|---------------|
| `-t` | Integrated loudness (LUFS) | `-23` broadcast EBU R128, `-24` ATSC A/85, `-16` Apple Podcasts, `-14` YouTube/Spotify |
| `-tp` | True peak ceiling (dBFS) | `-1.0` to `-2.0` (use `-1.5` as default) |
| `-lrt` | Loudness range target (LU) | `11` broadcast / podcast, omit for streaming (no clamp) |

Rule of thumb: **broadcast = -23 LUFS, podcast = -16 LUFS, streaming = -14 LUFS**. See `references/normalize.md` for the full platform table.

## Step 3 — Batch

Single file:
```bash
ffmpeg-normalize input.mp3 -o output.mp3 -t -16 -tp -1.5 -lrt 11
```

Folder (glob expanded by shell):
```bash
ffmpeg-normalize in/*.mp3 -of out/ -t -16 -tp -1.5 -lrt 11 --progress
```

Video (copy video, re-encode audio — REQUIRED since raw can't be muxed back):
```bash
ffmpeg-normalize in.mp4 -c:a aac -b:a 192k -o out.mp4
```

The helper script:
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/normalize.py preset --input in.mp3 --output out.mp3 --platform apple-podcasts
uv run ${CLAUDE_SKILL_DIR}/scripts/normalize.py batch --indir episodes/ --outdir normalized/ --platform spotify
```

Dry-run first:
```bash
ffmpeg-normalize in.mp3 -o out.mp3 --dry-run
```

## Step 4 — Verify

Measure the output to confirm it hit the target:
```bash
ffmpeg -i out.mp3 -af ebur128=peak=true -f null - 2>&1 | tail -20
# Look for: I: (integrated LUFS), LRA, True peak
```

Or use `--print-stats` / `--debug` during the normalize run to emit per-file loudnorm JSON.

## Available scripts

- **`scripts/normalize.py`** — `check` / `normalize` / `preset` / `batch` subcommands wrapping `ffmpeg-normalize`; stdlib only.

## Reference docs

- Read [`references/normalize.md`](references/normalize.md) for the platform target table, LUFS/dBFS/LRA concepts, raw-loudnorm vs wrapper comparison, and recipe book.

## Gotchas

- **2-pass is automatic**, no JSON round-trip needed (unlike raw `loudnorm`).
- **Default target is EBU R128 -23 LUFS (broadcast)** — too quiet for streaming. Use `-t -14` for YouTube/Spotify or `-t -16` for Apple Podcasts.
- `-t` = integrated loudness (LUFS); `-tp` = true peak (dBFS, typically `-1` to `-2`); `-lrt` = loudness range target (LU).
- **Batch mode normalizes each file INDEPENDENTLY.** There is no cross-file awareness. To keep relative levels across an album or episode set, do a single manual 2-pass `loudnorm` with a shared measurement (see `ffmpeg-audio-filter`).
- **`-c:a aac` is REQUIRED for MP4 output** (or `pcm_s16le` for WAV). Default encoder is `pcm_s16le` which only works in raw/WAV containers.
- **Re-encodes audio by default** — lossy for MP3/AAC inputs (transcode penalty). For FLAC/WAV output, no additional loss.
- **`-c:v copy` is the default for video** — the video stream is never re-encoded.
- `-of output/` (output folder) creates the dir if missing. Naming convention: `output/<original-filename>.<ext>`.
- `--keep-loudness-range-target` preserves source LRA (don't compress dynamics).
- `--dual-mono` auto-detects dual-mono and compensates (-3 dB, per EBU spec).
- `--lower-only` only **reduces** level, never boosts — useful when you don't want to amplify quiet source noise.
- `--extra-input-options` / `--extra-output-options` pass arbitrary flags through to ffmpeg (e.g., `-ar 44100`).
- `--progress` shows a tqdm progress bar.
- Single-pass (dynamic) is the default for video audio to save time; force 2-pass with `--keep-lra-above-loudness-range-target` when source LRA exceeds target.
- **Never chain a `volume=` filter after normalization** — it defeats the normalization.
- **LUFS** = Loudness Units relative to Full Scale (perceptual loudness, K-weighted).
- **dBFS** = decibels Full Scale (absolute sample level).
- **True Peak** prevents inter-sample clipping on consumer DACs that upsample.
- **LRA** (Loudness Range) = statistical dynamic range in LU.

## Examples

### Example 1: Podcast library to Apple Podcasts spec

```bash
ffmpeg-normalize podcast/*.mp3 \
  -of podcast-normalized/ \
  -t -16 -tp -1.5 -lrt 11 \
  -c:a libmp3lame -b:a 192k \
  --progress
```

### Example 2: Video for YouTube (keep video, AAC audio)

```bash
ffmpeg-normalize talk.mp4 \
  -t -14 -tp -1.0 \
  -c:a aac -b:a 192k \
  -o talk-yt.mp4
```

### Example 3: Dry-run across a directory (plan only)

```bash
ffmpeg-normalize *.wav -of out/ -t -23 --dry-run --print-stats
```

### Example 4: Only lower (never boost) for a noisy archive

```bash
ffmpeg-normalize noisy/*.wav -of safe/ -t -23 --lower-only
```

### Example 5: Specific audio stream (e.g., second language track only)

```bash
ffmpeg-normalize in.mkv -o out.mkv --audio-stream-filter "a:1" -c:a aac
```

## Troubleshooting

### Error: `Output file does not contain any stream` or missing audio in MP4

**Cause:** Default codec `pcm_s16le` can't be muxed into MP4.
**Fix:** Add `-c:a aac -b:a 192k` (or `-c:a libmp3lame` for MP3 output).

### Output is quieter than expected

**Cause:** Default target is `-23` LUFS (broadcast). Streaming targets are louder.
**Fix:** Use `-t -14` (YouTube/Spotify) or `-t -16` (Apple Podcasts).

### All files in a batch sound different relative to each other

**Cause:** Expected — each file is normalized to the target independently. Quiet originals get boosted to target; loud originals get cut.
**Fix:** Use manual 2-pass `loudnorm` with a single concatenated measurement, or process all files together via the `ffmpeg-audio-filter` skill.

### True peak still clips on consumer device

**Cause:** `-tp` default is `-2` but inter-sample peaks can still exceed on some chains.
**Fix:** Tighten to `-tp -1.5` or `-tp -2.0`; do not go above `-1.0`.

### `RuntimeError: Could not find ffmpeg`

**Cause:** ffmpeg not on `PATH`.
**Fix:** Install ffmpeg (`brew install ffmpeg` on macOS) or set `FFMPEG_PATH=/path/to/ffmpeg`.
