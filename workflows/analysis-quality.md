# Analysis + Quality Control Workflow

**What:** Deep inspection of media, automated QC against reference, quality metrics (VMAF/PSNR/SSIM), scene/crop/silence detection, regression checks. The "does this file meet spec?" layer that catches problems before delivery.

**Who:** QC engineers, broadcast operators, streaming ingest teams, release supervisors, automated CI/CD for media pipelines.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| ffprobe JSON | `ffmpeg-probe` | Streams, format, packet/frame level, HDR detection |
| MediaInfo | `media-mediainfo` | Deep container/stream diagnostics beyond ffprobe |
| VMAF / PSNR / SSIM | `ffmpeg-quality` | Reference-based perceptual quality metrics |
| Scene detection | `media-scenedetect`, `ffmpeg-detect` (scdet) | Cut-list extraction |
| Crop detection | `ffmpeg-detect` (cropdetect) | Auto-detect letterbox/pillarbox |
| Silence detection | `ffmpeg-detect` (silencedetect) | Trim points / chapter boundaries |
| Interlacing detection | `ffmpeg-detect` (idet) | Progressive vs interlaced vs telecined |
| Black detection | `ffmpeg-detect` (blackdetect, blackframe) | Slate / inter-program gaps |
| ffplay debug | `ffmpeg-playback` | Scopes, waveform, vectorscope |
| Bitstream analysis | `ffmpeg-bitstream` | NAL unit inspection, SEI decoding |
| Metadata | `media-exiftool`, `ffmpeg-metadata` | EXIF / IPTC / XMP / ID3 / MKV tags |
| MediaInfo variants | `media-mediainfo` | XML / JSON / HTML reports |
| OCR verification | `media-ocr-ai`, `ffmpeg-ocr-logo` | Verify burned-in text / ID / logos |
| CV detection | `cv-opencv`, `cv-mediapipe` | Automated face/logo/feature detection |
| Quality tagging | `media-tag` | Zero-shot content classification |

---

## The pipeline

### 1. Probe everything

```bash
# Full probe: format + all streams
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full input.mp4

# Specific stream details
uv run .claude/skills/ffmpeg-probe/scripts/probe.py streams input.mp4

# HDR-specific metadata check
uv run .claude/skills/ffmpeg-probe/scripts/probe.py hdr-check input.mp4

# Packet-level (for bitstream issues)
uv run .claude/skills/ffmpeg-probe/scripts/probe.py packets input.mp4
```

### 2. MediaInfo deep diagnostics

When ffprobe isn't enough:

```bash
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file input.mp4 --format json > mediainfo.json

# XML (XSD-schema-valid)
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file input.mp4 --format xml > mediainfo.xml

# Just one field
uv run .claude/skills/media-mediainfo/scripts/miinfo.py field \
  --file input.mp4 --field "Video;%Encoded_Library%"
```

MediaInfo knows things ffprobe doesn't:
- Exact encoder build (`x264 core 164 r3095`)
- Cabac / Trellis / B-Pyramid settings
- Source framerate variance
- Actual recording device metadata
- Encoding history (if present)

### 3. VMAF quality metrics

Primary use: comparing encoded output vs source, or comparing two encoders.

```bash
# Full VMAF (default model, 1920x1080 viewing distance)
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference original.mov --distorted encoded.mp4 --json > vmaf.json

# VMAF NEG (no-enhancement, catches over-sharpening)
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference original.mov --distorted encoded.mp4 \
  --model vmaf_v0.6.1neg --json

# 4K model
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference uhd-original.mov --distorted uhd-encoded.mp4 \
  --model vmaf_4k_v0.6.1 --json

# Phone-sized (mobile)
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference original.mov --distorted mobile-encoded.mp4 \
  --model vmaf_b_v0.6.3 --json
```

VMAF score interpretation:
- **>= 95** — Transparent (viewer can't tell from source)
- **>= 80** — Excellent (typical streaming delivery target)
- **>= 70** — Good (mobile delivery)
- **>= 60** — Acceptable (low-bitrate fallback)
- **< 60** — Visible quality loss

### 4. PSNR / SSIM (when VMAF isn't appropriate)

```bash
# PSNR (classic, legacy reference)
uv run .claude/skills/ffmpeg-quality/scripts/quality.py psnr \
  --reference ref.mov --distorted encoded.mp4 --json

# SSIM (structural similarity)
uv run .claude/skills/ffmpeg-quality/scripts/quality.py ssim \
  --reference ref.mov --distorted encoded.mp4 --json

# Multiscale SSIM
ffmpeg -i encoded.mp4 -i ref.mov -lavfi "[0:v][1:v]msssim" -f null -
```

PSNR is dB-based, viewer-agnostic. Don't ship on PSNR alone — it doesn't correlate well with perception. VMAF is the standard.

### 5. Scene detection

**PySceneDetect (standalone, most robust):**
```bash
uv run .claude/skills/media-scenedetect/scripts/scenedetect.py detect \
  --input long.mp4 --output scenes.csv \
  --method content --threshold 27

# Also split at scenes
uv run .claude/skills/media-scenedetect/scripts/scenedetect.py split \
  --input long.mp4 --output-dir scenes/ --threshold 27
```

**FFmpeg scdet (inline):**
```bash
ffmpeg -i long.mp4 -vf "scdet=threshold=10" -f null - 2>&1 | grep "scdet"
```

### 6. Crop detection (auto-remove letterbox)

```bash
uv run .claude/skills/ffmpeg-detect/scripts/detect.py crop \
  --input letterboxed.mov --duration 30

# Output: crop=1920:816:0:132
# Use in your ffmpeg command:
ffmpeg -i letterboxed.mov -vf "crop=1920:816:0:132" unboxed.mov
```

### 7. Silence detection

```bash
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input audio.wav \
  --threshold -35dB \
  --min-duration 2s \
  --output silences.json

# Auto-trim leading / trailing silence
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input audio.wav \
  --output trimmed.wav \
  --action trim-ends --threshold -35dB
```

### 8. Interlacing detection

```bash
ffmpeg -i input.mov -vf "idet" -f null - 2>&1 | grep "Multi frame detection"
# → [Parsed_idet_0 @ 0x...] Multi frame detection: TFF: 1234 BFF: 0 Progressive: 5 Undetermined: 0
```

Interpretation:
- High TFF or BFF count → interlaced (TFF = top field first, BFF = bottom field first)
- High "Progressive" count → progressive
- Mixed ~60/40 split → telecined (29.97i from 23.976p film)

Use `ffmpeg-ivtc` skill if telecined.

### 9. Black-frame / slate detection

```bash
# Detect black gaps (for commercial-break insertion points)
ffmpeg -i program.mov -vf "blackdetect=d=1:pic_th=0.98" -f null - 2>&1 | grep black

# Detect leader slate at file head
uv run .claude/skills/ffmpeg-detect/scripts/detect.py black \
  --input master.mov --min-duration 0.5 --output black-ranges.json
```

### 10. ffplay scopes (live inspection)

```bash
# Play with waveform scope
uv run .claude/skills/ffmpeg-playback/scripts/play.py scope \
  --input source.mp4 --scope waveform

# Vectorscope + histogram
uv run .claude/skills/ffmpeg-playback/scripts/play.py scope \
  --input source.mp4 --scope vectorscope+histogram
```

### 11. Bitstream forensics

Low-level HEVC / H.264 inspection:

```bash
uv run .claude/skills/ffmpeg-bitstream/scripts/bsf.py nal-dump \
  --input video.hevc --max-nals 100 | head -50

# Trace SEI messages (HDR metadata)
uv run .claude/skills/ffmpeg-bitstream/scripts/bsf.py sei-dump \
  --input video.hevc
```

### 12. Metadata audit

```bash
# Image/video metadata
uv run .claude/skills/media-exiftool/scripts/exif.py read \
  --input photo.jpg --format json

# Video chapter metadata
uv run .claude/skills/ffmpeg-metadata/scripts/metadata.py read \
  --input video.mp4

# MKV tags
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py info \
  --input file.mkv
```

### 13. Content verification with AI

**Burned-in text check:**
```bash
# Extract frame every 10s, OCR each
ffmpeg -i video.mp4 -vf "fps=0.1" -qscale:v 2 frames/%04d.jpg

uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py paddle \
  --input frames/ --output ocr-results.json --batch
```

**Face presence check:**
```bash
uv run .claude/skills/cv-mediapipe/scripts/cvmp.py face-detect \
  --input video.mp4 --output faces-per-frame.json
```

**Content tagging:**
```bash
uv run .claude/skills/media-tag/scripts/tagctl.py siglip \
  --input frame.jpg \
  --labels "nudity,violence,weapons,logo,watermark" \
  --output tags.json
```

### 14. Loudness compliance

```bash
# Measure without modifying
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py measure \
  --input audio.mov
```

Example output:
```json
{
  "integrated_loudness": -17.2,
  "loudness_range": 8.5,
  "true_peak": -1.1,
  "threshold": -27.2
}
```

Compare to spec (Spotify: -14 ±2 LUFS, Apple Podcasts: -16 ±1, ATSC A/85: -24 ±2, EBU R128: -23 ±0.5).

### 15. Automated CI QC pipeline

```bash
#!/usr/bin/env bash
# qc-check.sh — returns non-zero on failure

FILE=$1
TARGET_VMAF=85

# Spec check
PROBE=$(uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$FILE" --json)
WIDTH=$(echo "$PROBE" | jq -r '.streams[0].width')
HEIGHT=$(echo "$PROBE" | jq -r '.streams[0].height')
CODEC=$(echo "$PROBE" | jq -r '.streams[0].codec_name')
FPS=$(echo "$PROBE" | jq -r '.streams[0].r_frame_rate')

# Spec assertions
if [[ "$CODEC" != "h264" ]]; then echo "FAIL: codec=$CODEC, expected h264"; exit 1; fi
if [[ "$WIDTH" != "1920" || "$HEIGHT" != "1080" ]]; then echo "FAIL: resolution=${WIDTH}x${HEIGHT}"; exit 1; fi
if [[ "$FPS" != "24000/1001" ]]; then echo "FAIL: fps=$FPS"; exit 1; fi

# VMAF vs reference
VMAF=$(uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference reference.mov --distorted "$FILE" --json | jq -r .vmaf_mean)

if (( $(echo "$VMAF < $TARGET_VMAF" | bc -l) )); then
  echo "FAIL: VMAF=$VMAF, target $TARGET_VMAF"; exit 1
fi

# Loudness check (CI uses tighter spec)
LUFS=$(uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py measure \
  --input "$FILE" | jq -r .integrated_loudness)

if (( $(echo "$LUFS > -13 || $LUFS < -19" | bc -l) )); then
  echo "FAIL: loudness=$LUFS LUFS, expected -16±3"; exit 1
fi

echo "PASS: $FILE"
```

---

## Variants

### Automated regression suite

Compare a new encoder version's output to a golden reference across a corpus:

```bash
for SOURCE in corpus/*.mov; do
  ENCODED=$(basename "$SOURCE" .mov).mp4
  ffmpeg -i "$SOURCE" -c:v libx264 -crf 20 "encoded/$ENCODED"

  VMAF=$(uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
    --reference "$SOURCE" --distorted "encoded/$ENCODED" --json | jq -r .vmaf_mean)

  echo "$SOURCE,$VMAF" >> results.csv
done
```

Diff against previous regression:
```bash
diff baseline.csv results.csv
```

### Continuous streaming monitor

Monitor a live stream for quality drift:

```bash
# Every 60 seconds, capture 10s, measure VMAF against a golden segment
while true; do
  ffmpeg -i https://live.example.com/stream.m3u8 -t 10 -c copy sample.ts
  uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
    --reference golden.ts --distorted sample.ts --json > measurement.json
  sleep 50
done
```

### Bulk spec validation

```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob 'masters/*.mp4' \
  --jobs 4 \
  --command 'bash qc-check.sh {in}'
```

### Interactive ffplay debugging

```bash
# Play with pts overlay
ffplay -vf "drawtext=text='%{pts\\:hms}':fontsize=24:fontcolor=white:x=10:y=10" input.mp4

# Vectorscope + waveform side-by-side
ffplay -vf "split=3[a][b][c];[a]vectorscope=m=color4[v1];[b]waveform=m=0[v2];[c]null[v3];[v1][v2][v3]hstack=inputs=3" input.mov
```

### Compare ABR ladder rungs

```bash
for RUNG in 1080p 720p 480p 360p; do
  VMAF=$(uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
    --reference source.mov --distorted "abr/${RUNG}.mp4" --json | jq -r .vmaf_mean)
  echo "$RUNG: VMAF $VMAF"
done
```

### Automated broadcast spec QC

Check for: broadcast-safe color (legal range), interlacing, drop-frame timecode consistency, caption presence, loudness, silence:

```bash
# 1. Color legality
ffmpeg -i program.mov -vf "signalstats" -f null - 2>&1 | grep -E "YMIN|YMAX|UMIN|UMAX|VMIN|VMAX"

# 2. Interlacing
ffmpeg -i program.mov -vf "idet" -f null - 2>&1 | tail -5

# 3. Timecode continuity
uv run .claude/skills/ffmpeg-probe/scripts/probe.py timecode --input program.mov

# 4. Caption presence
ffprobe -select_streams s -show_streams program.mov | grep codec_type

# 5. Loudness (ATSC A/85 spec: -24 ±2 LUFS)
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py measure \
  --input program.mov
```

---

## Gotchas

### Measurement integrity

- **VMAF reference and distorted MUST be identical duration + frame rate.** Otherwise aligner fails silently; result is meaningless.
- **VMAF prefers same resolution for ref + distorted.** If distorted is lower-res, VMAF upscales distorted by default. For HD-vs-4K comparisons, explicitly downscale the reference.
- **VMAF `vmaf_v0.6.1` is the default PC-monitor model.** `vmaf_v0.6.1neg` catches enhancement artifacts. `vmaf_4k_v0.6.1` for 4K. `vmaf_b_v0.6.3` for mobile. Using the wrong model = wrong score.
- **PSNR-YUV vs PSNR-Y-only** — `ffmpeg -psnr` reports overall. For Y-only (luma), use `psnr=...y`.
- **Frame-drop / duplication breaks sync.** VMAF wants 1:1 frame correspondence. Variable-frame-rate inputs → non-sensical scores.
- **Clamping to different ranges (limited vs full) changes perceptual scores.** Convert both to the same range before measuring.

### Detection thresholds

- **Scene-detect `threshold=27` is the PySceneDetect default.** Content with gradual transitions / fades may need lower (15-20). Content with many abrupt cuts (trailers) tolerates higher (35-40).
- **`cropdetect` samples every N seconds** — default works for most, but variable-content (e.g., action movies with black at cuts) gives inconsistent reads. Longer `--duration` = more reliable.
- **`silencedetect` threshold `-35dB` is good for dialogue.** For music content, try `-50dB`. Below `-60dB`, you're in noise-floor territory.
- **`idet` gives counts, not decisions.** Interpret: if TFF count ≈ 2.5x Progressive, it's telecined (5 fields per 4 frames pattern).
- **`blackdetect pic_th` is picture-luma threshold 0-1, not dB.** 0.98 = only near-pure-black frames count.

### Metadata

- **MediaInfo "Encoded Library" is heuristic.** Re-encoded content may show an encoder that no longer matches the actual bitstream.
- **ffprobe `duration_ts` is in stream timebase, `duration` is seconds.** Don't conflate.
- **`nb_frames=0` means "unknown count" (stream wasn't fully parsed).** Use `count_frames` for accurate count.
- **ExifTool can read AND WRITE** — be careful with `-tagsfromfile` and `-overwrite_original` (strips backups).

### Bitstream

- **NAL unit types differ between H.264 and HEVC.** Don't swap: H.264 SPS = type 7, HEVC SPS = type 33.
- **SEI messages inside HEVC** use a type byte + size + payload. UUID-prefixed T.35 user-data is where DoVi/HDR10+/closed-captions live. Use `hdr-dovi-tool` / `hdr-hdr10plus-tool` to decode, not raw byte parsing.
- **Bitstream analysis on encrypted content (Widevine / FairPlay) fails** — the essence is encrypted below the container layer.

### Operational

- **ffplay is blocking** — use `-autoexit` to return control after duration, or background it with `&` and track PID.
- **`ffprobe -show_streams -show_format` outputs INI-style by default.** Use `-of json` or `-of csv=p=0` for scripting.
- **`jq -r` drops quotes on string fields; use `jq` (no `-r`) when downstream parsers need JSON.**
- **MediaInfo CLI's `--Output=JSON` flag is version-gated.** MediaInfo 21+ has better JSON output than 20.x.
- **VMAF motion computation is I/O-bound on large sources.** Use SSDs for reference + distorted.
- **Reference encoder settings matter for VMAF.** Non-deterministic encoders (multi-threaded x264/x265 without `--deterministic`) give slightly different output per run.

---

## Example — "Deep QC report for a deliverable"

```bash
#!/usr/bin/env bash
set -e

INPUT="deliverable.mp4"
REFERENCE="source.mov"
REPORT_DIR="qc/$(basename $INPUT .mp4)"
mkdir -p "$REPORT_DIR"

echo "=== QC Report: $INPUT ==="

# 1. Spec
echo "--- Probe ---"
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$INPUT" > "$REPORT_DIR/probe.json"
jq -r '.streams[] | "\(.codec_type): \(.codec_name) \(.width // "")x\(.height // "") \(.r_frame_rate // "")"' "$REPORT_DIR/probe.json"

# 2. MediaInfo
echo "--- MediaInfo ---"
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report --file "$INPUT" --format json > "$REPORT_DIR/mediainfo.json"

# 3. HDR
echo "--- HDR check ---"
uv run .claude/skills/ffmpeg-probe/scripts/probe.py hdr-check "$INPUT" | tee "$REPORT_DIR/hdr.txt"

# 4. VMAF
echo "--- VMAF ---"
uv run .claude/skills/ffmpeg-quality/scripts/quality.py vmaf \
  --reference "$REFERENCE" --distorted "$INPUT" --json > "$REPORT_DIR/vmaf.json"
VMAF_MEAN=$(jq -r .vmaf_mean "$REPORT_DIR/vmaf.json")
echo "VMAF mean: $VMAF_MEAN"

# 5. Loudness
echo "--- Loudness ---"
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py measure \
  --input "$INPUT" > "$REPORT_DIR/loudness.json"
jq -r '"LUFS: \(.integrated_loudness), LRA: \(.loudness_range), TP: \(.true_peak)"' "$REPORT_DIR/loudness.json"

# 6. Black / silence detection
echo "--- Black frames ---"
ffmpeg -i "$INPUT" -vf "blackdetect=d=1:pic_th=0.98" -f null - 2>&1 | grep black | tee "$REPORT_DIR/blacks.txt"

echo "--- Silences ---"
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input "$INPUT" --threshold -45dB --min-duration 1 --output "$REPORT_DIR/silences.json"

# 7. Interlacing
echo "--- Interlacing ---"
ffmpeg -i "$INPUT" -vf "idet" -f null - 2>&1 | grep "Multi frame detection" | tee "$REPORT_DIR/idet.txt"

# 8. Scene count (for sanity)
echo "--- Scenes ---"
uv run .claude/skills/media-scenedetect/scripts/scenedetect.py detect \
  --input "$INPUT" --output "$REPORT_DIR/scenes.csv" --method content --threshold 27
echo "Scene count: $(wc -l < $REPORT_DIR/scenes.csv)"

# 9. Verdict
echo ""
echo "=== VERDICT ==="
if (( $(echo "$VMAF_MEAN >= 85" | bc -l) )); then
  echo "✓ VMAF passes ($VMAF_MEAN ≥ 85)"
else
  echo "✗ VMAF fails ($VMAF_MEAN < 85)"
  exit 1
fi

echo "Full report: $REPORT_DIR/"
```

---

## Further reading

- [`broadcast-delivery.md`](broadcast-delivery.md) — QC gates in the broadcast pipeline
- [`streaming-distribution.md`](streaming-distribution.md) — ABR ladder tuning via VMAF
- [`hdr-workflows.md`](hdr-workflows.md) — HDR metadata validation
- [`vod-post-production.md`](vod-post-production.md) — QC during finishing
