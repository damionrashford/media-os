# ffmpeg-normalize reference

High-level wrapper around ffmpeg's `loudnorm` filter that automates proper 2-pass EBU R128 normalization, batch-folders, and stream preservation.

## Platform loudness targets

| Destination | Target IL (LUFS) | True Peak (dBFS) | LRA (LU) | Notes |
|---|---|---|---|---|
| **EBU R128** (broadcast, EU TV / radio) | **-23.0** | -1.0 | 7 | EBU Tech 3341 / 3342. Default of ffmpeg-normalize. |
| **ATSC A/85** (US broadcast TV) | **-24.0** | -2.0 | 7 | ATSC CALM Act compliance. |
| **ARIB TR-B32** (Japan broadcast) | -24.0 | -1.0 | — | |
| **AES Streaming** | -16.0 to -20.0 | -1.0 | — | AES Technical Document. |
| **Apple Podcasts** | **-16.0** | -1.0 | 11 | Spec since 2017. |
| **Spotify** | **-14.0** | -1.0 | — | Loudness-matched if your master is louder. |
| **YouTube** | **-14.0** | -1.0 | — | Normalized playback, louder masters are attenuated. |
| **Tidal** | -14.0 | -1.0 | — | |
| **Amazon Music** | -14.0 | -2.0 | — | |
| **Deezer** | -15.0 | -1.0 | — | |
| **Netflix (stream delivery, stereo)** | -27.0 | -2.0 | — | LKFS. |
| **Netflix (theatrical)** | -24.0 | -2.0 | — | Dialnorm. |
| **Cinema DCP** | -27.0 (dialogue) | -2.0 | — | Not integrated LUFS — dialogue-anchored. |
| **Dolby Atmos stream** | -18.0 | -1.0 | — | |
| **Audiobooks (ACX)** | -18.0 to -23.0 | -3.0 | — | ACX has dual peak + RMS rules. |
| **Game audio (masters)** | -18.0 to -23.0 | -1.0 | — | Varies wildly by engine/platform. |

## Concepts

- **LUFS** (Loudness Units relative to Full Scale): perceptual, K-weighted loudness measurement per ITU-R BS.1770 / EBU R128. 1 LU = 1 dB perceptually, but LUFS integrates across time with a gate.
- **LKFS**: same as LUFS (ATSC / US term).
- **dBFS**: absolute digital sample level. True peak is measured in dBFS.
- **True Peak (dBTP)**: estimated inter-sample peak after 4× oversampling; always higher than sample peak; prevents DAC clipping on playback.
- **LRA** (Loudness Range): difference between the 10th and 95th percentile of short-term loudness, in LU. High LRA = dynamic (movies), low LRA = compressed (pop music).
- **IL** / **I**: Integrated Loudness over the whole file.
- **M** / **S**: Momentary (400 ms) and Short-term (3 s) loudness.

## ffmpeg-normalize vs raw loudnorm

| Aspect | Raw `-af loudnorm` | `ffmpeg-normalize` |
|---|---|---|
| Default pass count | 1 (dynamic — approximate) | **2 (measured + applied — accurate)** |
| Setup | Hand-wire `print_format=json` → parse → second pass | Automatic |
| Batch directory | Shell loop | Built-in (`-of outdir/`) |
| Stream preservation | You write `-map` flags | Default keeps all streams, copies video |
| Per-file independence | Yes | Yes (each file normalized separately) |
| Cross-file consistency | Possible with shared measurement | **Not supported** — use raw for this |
| Codec selection | `-c:a` yourself | `-c:a` + `-b:a` pass-through |
| Progress bar | No | `--progress` (tqdm) |
| Easy to reach inside a pipeline graph | Yes | No (process-level) |

**Use raw `loudnorm` when:** you need cross-file consistency (album-gain), or you're chaining inside a larger `filter_complex` graph.
**Use `ffmpeg-normalize` when:** you're batch-processing independent files to a platform target, or you just want a correct 2-pass without wiring it by hand.

## Batch workflow patterns

### Pattern 1: Podcast library → Apple Podcasts

```bash
ffmpeg-normalize \
  raw-episodes/*.wav \
  -of delivered/ \
  -t -16 -tp -1.5 -lrt 11 \
  -c:a libmp3lame -b:a 192k \
  --progress --print-stats
```

### Pattern 2: YouTube upload from video masters

```bash
ffmpeg-normalize \
  masters/*.mp4 \
  -of uploads/ \
  -t -14 -tp -1.0 \
  -c:a aac -b:a 192k \
  --progress
# Video stream is -c:v copy by default — no quality loss.
```

### Pattern 3: Archive to EBU broadcast spec

```bash
ffmpeg-normalize archive/*.wav \
  -of ebu-compliant/ \
  -t -23 -tp -2.0 -lrt 7 \
  -c:a pcm_s24le -ar 48000
```

### Pattern 4: Game dialogue (lower-only, avoid boosting noise)

```bash
ffmpeg-normalize vo/*.wav \
  -of vo-normalized/ \
  -t -19 -tp -1.0 \
  --lower-only
```

### Pattern 5: Audiobook (ACX-style, -18 to -23 window)

ACX requires **-18 to -23 dB RMS, peak ≤ -3 dBFS, noise ≤ -60 dB**. RMS != LUFS so treat this as approximate:

```bash
ffmpeg-normalize chapters/*.wav \
  -of acx/ \
  -t -20 -tp -3.0 \
  -c:a libmp3lame -b:a 192k
# Then verify with a separate RMS/peak/noise check.
```

### Pattern 6: Dry-run an entire library first

```bash
ffmpeg-normalize library/**/*.flac \
  -of normalized/ \
  -t -14 --dry-run --print-stats \
  > plan.txt
# Review plan.txt, then re-run without --dry-run.
```

## Key flags reference

| Flag | What it does |
|---|---|
| `-t -23` | Integrated loudness target in LUFS. |
| `-tp -1.5` | True peak ceiling in dBFS. |
| `-lrt 11` | Loudness range target (compresses dynamics if source LRA > this). |
| `-o out.ext` | Single-file output. |
| `-of outdir/` | Output folder (created if missing); names mirror input filenames. |
| `-c:a aac` | Audio codec. Required for MP4/MOV/MKV. |
| `-b:a 192k` | Audio bitrate. |
| `-ar 44100` | Sample rate override (via `--extra-output-options`). |
| `-nt ebu` / `rms` / `peak` | Normalization method. `ebu` = EBU R128 (default), `rms` = classic RMS normalization, `peak` = peak-only (no perceptual weighting). |
| `-pr` / `--pre-filter` | Run a pre-filter before loudness analysis. |
| `-prf` / `--post-filter` | Filter after normalization (careful — defeats it). |
| `--audio-stream-filter "a:0"` | Process only this audio stream. |
| `--keep-loudness-range-target` | Preserve source LRA (don't compress). |
| `--keep-lra-above-loudness-range-target` | Force 2-pass on video when LRA > target. |
| `--dual-mono` | Detect dual-mono, apply -3 dB compensation. |
| `--lower-only` | Only attenuate; never boost. |
| `--dry-run` | Print plan, don't run. |
| `--print-stats` | Emit loudnorm JSON summary per file. |
| `--debug` | Full debug + JSON stats. |
| `--progress` | tqdm progress bar. |
| `--extra-input-options` | Pass-through ffmpeg input options. |
| `--extra-output-options` | Pass-through ffmpeg output options. |
| `-f` / `--force` | Overwrite existing outputs. |

## Recipe book

### Verify a result hit its target

```bash
ffmpeg -i out.mp3 -af ebur128=peak=true -f null - 2>&1 | awk '/Integrated|Range|True peak/'
# Expect:  I = -16.0 LUFS (within ±0.5)
#          LRA = 11 LU (or close)
#          True peak = -1.5 dBTP (or below)
```

### Generate a loudness report for a folder

```bash
for f in episodes/*.mp3; do
  ffmpeg-normalize "$f" -o /dev/null --dry-run --print-stats 2>&1 | \
    awk -v f="$f" '/input_i|input_tp|input_lra/ {print f, $0}'
done
```

### Chain: normalize → package HLS

```bash
ffmpeg-normalize in.mp4 -t -16 -c:a aac -b:a 192k -o norm.mp4
ffmpeg -i norm.mp4 -c copy -f hls -hls_time 6 out.m3u8
```

### Podcast with ID3 tags preserved

```bash
ffmpeg-normalize in.mp3 -o out.mp3 -t -16 -c:a libmp3lame -b:a 192k \
  --extra-output-options="[-id3v2_version,3,-write_id3v1,1,-map_metadata,0]"
```

### Batch that writes a per-file JSON stats log

```bash
mkdir -p normalized logs
for f in in/*.wav; do
  base=$(basename "$f" .wav)
  ffmpeg-normalize "$f" -o "normalized/${base}.wav" -t -23 --print-stats \
    2> "logs/${base}.json"
done
```

### When you actually need cross-file consistency (don't use this tool)

Use the `ffmpeg-audio-filter` skill: measure once across a concatenated stream, then re-use the same `measured_*` values for the second pass on each file. `ffmpeg-normalize` intentionally treats every file as independent.
