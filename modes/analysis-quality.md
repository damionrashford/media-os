# Mode: analysis-quality

**Subagent**: `qc`
**Trigger phrases**: "QC this", "VMAF check", "quality gate", "freeze detect", "black frame detect", "loudness check", "EBU R128", "audio loudness", "automated QC", "broadcast QC", "AS-11 QC", "compare encoded"
**Output**: `${MEDIA_WORK_DIR}/modes/analysis-quality/{date}_{slug}/`

## Inputs

- **Required**: one of:
  - `pair` — `source=<ref> encoded=<out>` for VMAF/SSIM/PSNR comparison.
  - `single` — `<file>` for single-file QC (loudness, freeze/black/silence detect, GOP analysis, captions, timecode).
- **Optional**:
  - `vmaf_min` — gate threshold (default from `DEFAULT_VMAF_TARGET`, fallback 93).
  - `loudness_target` — `-16` (Apple), `-23` (EBU R128), `-24` (ATSC A85). Default `-23`.
  - `freeze_threshold_seconds` — duration before flagging a freeze (default: `0.5s`).
  - `black_threshold_seconds` — duration before flagging a black frame run (default: `1.0s`).
  - `silence_threshold_seconds` — duration before flagging silence (default: `2.0s`).

## Steps

1. Read tool skills: `ffmpeg-quality`, `ffmpeg-detect`, `media-ffmpeg-normalize`, `ffmpeg-probe`, `media-mediainfo`.
2. `moprobe --color --json` on each input file.
3. **STOP** if `pair` provided but files differ in resolution AND `--scale-source` not flagged — VMAF requires matching dimensions or explicit scaling.
4. Run analysis battery in parallel where possible:
   - **VMAF/SSIM/PSNR** (pair only): `moqc --ref <source> --out <encoded> --vmaf-min <vmaf_min> --format json`. Per-frame stats stored.
   - **Loudness**: `ffmpeg -i <file> -af loudnorm=print_format=json -f null -` to get integrated LUFS, true peak, LRA, threshold.
   - **Freeze detection**: `ffmpeg -i <file> -vf freezedetect=duration=<freeze_threshold_seconds>:noise=0.001 -f null -`.
   - **Black detection**: `ffmpeg -i <file> -vf blackdetect=d=<black_threshold_seconds>:pic_th=0.98 -f null -`.
   - **Silence detection**: `ffmpeg -i <file> -af silencedetect=duration=<silence_threshold_seconds>:noise=-50dB -f null -`.
   - **GOP analysis** (encoded only): `ffprobe -select_streams v:0 -show_frames -read_intervals "%+#600" -of json` for keyframe distribution.
   - **Caption check**: `ffprobe -select_streams s:0` — list subtitle streams; if WebVTT/SRT/TTML, parse for line-count + timing.
   - **Timecode check**: `mediainfo --Inform="Video;%Delay/String3%"` for SMPTE timecode track presence.
5. Aggregate results into a pass/fail matrix per the configured thresholds.
6. **Do NOT modify the input file.** This mode reports only.
7. Write `summary.md` with full matrix + per-event timestamps for freezes/blacks/silences.

## Output schema

```markdown
# Analysis + QC — {slug} — {date}

## Files
- **Reference**: {path or N/A (single-file mode)}
- **Encoded**: {path}

## Pass/fail matrix

| Check | Threshold | Result | Pass |
|---|---|---|---|
| VMAF | ≥ {vmaf_min} | {N} | ✓ / ✗ |
| Integrated LUFS | within ±0.5 LU of {loudness_target} | {N} LUFS | ✓ / ✗ |
| True peak | ≤ -1.0 dBTP | {N} dBTP | ✓ / ✗ |
| Freezes | none > {freeze_threshold_seconds}s | {N} events | ✓ / ✗ |
| Black runs | none > {black_threshold_seconds}s | {N} events | ✓ / ✗ |
| Silences | none > {silence_threshold_seconds}s | {N} events | ✓ / ✗ |
| GOP regular | I-frames every ≤ 4s | {actual avg} | ✓ / ✗ |
| Captions present | {required or optional} | {Y/N + format} | ✓ / ✗ |
| SMPTE timecode | {required or optional} | {start TC or N/A} | ✓ / ✗ |

## VMAF detail (pair mode)
- **Mean**: {N}
- **Min**: {N} at frame {N} ({timestamp})
- **Standard deviation**: {N}
- **Harmonic mean**: {N}
- **Per-tier scores** (if multi-bitrate): table

## Loudness detail
- **Integrated LUFS**: {N}
- **Max momentary**: {N}
- **Loudness range (LRA)**: {N LU}
- **True peak**: {N dBTP}

## Event log (freeze / black / silence)
| Type | Start | End | Duration |
|---|---|---|---|
| freeze | hh:mm:ss.ms | hh:mm:ss.ms | s |
| black | hh:mm:ss.ms | hh:mm:ss.ms | s |
| silence | hh:mm:ss.ms | hh:mm:ss.ms | s |
```

## Quality bar

- Pass/fail matrix is binary per row — no "mostly passed" rows.
- Per-event timestamps preserved to the millisecond — operators need them to seek directly.
- If GOP analysis shows irregular keyframes (gap > 4s), report as fail — HLS segmenting will break.
- Single-file mode: VMAF row marked `N/A`, not silently dropped.
- This mode never modifies the input — report-only.
- Re-runs produce identical output (deterministic seed for stats).

## Playbook reference (folded from workflow-analysis-quality)

**What:** Inspect every byte and assess every rendition. The gate between "encoded" and "shipped".

### Pipeline

#### Step 1 — Probe everything

`moprobe` + `ffmpeg-probe` — full format + streams + specific stream detail + packet-level bitstream dump when needed. `moprobe --color` for HDR side data.

#### Step 2 — MediaInfo deep diagnostics

`media-mediainfo` (`--Output=JSON|XML|HTML`). Shows encoded-library, CABAC/trellis/B-pyramid, source framerate variance, recording-device metadata, re-encode history. Use when ffprobe alone is insufficient.

#### Step 3 — Quality metrics (VMAF / PSNR / SSIM)

`ffmpeg-quality` or `moqc`:

| Model | Use for |
|---|---|
| `vmaf_v0.6.1` | PC monitor (1920×1080 default) |
| `vmaf_v0.6.1neg` | No-enhancement (catches sharpening cheats) |
| `vmaf_4k_v0.6.1` | 4K TVs |
| `vmaf_b_v0.6.3` | Mobile / phone |

Interpretation: ≥ 95 transparent, ≥ 80 excellent, ≥ 70 good, ≥ 60 acceptable, < 60 visible loss.

#### Step 4 — Scene detection

`media-scenedetect` (content method, default threshold 27). Lower (15–20) for gradual transitions; higher (35–40) for abrupt cuts only. Inline `scdet` filter in ffmpeg if you don't need PySceneDetect's graph output.

#### Step 5 — Crop / silence / black / interlacing

`ffmpeg-detect`:
- `cropdetect` — auto-detect letterbox/pillarbox, emits `crop` filter args.
- `silencedetect` — `-35 dB` default for dialogue, `-50 dB` for music.
- `blackdetect` — `pic_th` 0–1 luma threshold (0.98 = near-pure-black).
- `idet` — counts fields: high TFF/BFF = interlaced, high Progressive = progressive, mixed ~60/40 = telecined (use the ai-enhancement mode or `ffmpeg-ivtc` to recover).

#### Step 6 — ffplay scopes

`ffmpeg-playback` — waveform, vectorscope, histogram live.

#### Step 7 — Bitstream forensics

`ffmpeg-bitstream`:
- NAL dump (HEVC SPS=33, H.264 SPS=7).
- SEI dump for HDR metadata / captions / DoVi / HDR10+.

#### Step 8 — Metadata audit

`media-exiftool` (image / video EXIF, XMP, IPTC). `ffmpeg-metadata` for chapter + MKV tags.

#### Step 9 — Content verification with CV/AI

`media-ocr-ai` for burned text; `cv-mediapipe` for face presence; `media-tag` CLIP/SigLIP for zero-shot content tags.

#### Step 10 — Loudness compliance

`media-ffmpeg-normalize --measure-only` (non-destructive). Compare to spec:

| Spec | Integrated | True peak |
|---|---|---|
| Spotify Master | −14 LUFS ± 2 | −2 dBTP |
| Apple Podcasts | −16 LUFS ± 1 | −1 dBTP |
| ATSC A/85 | −24 LUFS ± 2 | − |
| EBU R128 | −23 LUFS ± 0.5 | −1 dBTP |

#### Step 11 — Automated CI QC gates

`moqc --ref source --out encoded --format json --vmaf-min 93` exits non-zero on failure. Wire into CI to fail builds that would ship broken encodes.

### Variants

- **Regression suite** — new encoder vs golden corpus, VMAF per source.
- **Streaming monitor** — every 60 s, capture 10 s, VMAF against golden.
- **Bulk spec validation** — `media-batch` parallel validate.
- **Interactive debugging** — ffplay with PTS overlay, vectorscope + waveform side-by-side.
- **ABR ladder compare** — VMAF per rung to tune quality.
- **Broadcast spec QC** — color legality (`signalstats`), interlacing (`idet`), timecode continuity, caption presence, ATSC A/85 loudness.

### Gotchas

- **VMAF reference and distorted MUST match duration and frame rate.** Mismatch = silent aligner failure → meaningless score.
- **VMAF prefers matching resolution.** If distorted is lower-res, it upscales silently. Downscale reference explicitly for HD-vs-4K comparison.
- **VMAF default model (`vmaf_v0.6.1`) is for PC monitors.** Pick `_4k`, `_mobile`, `_neg` per target.
- **PSNR-YUV vs PSNR-Y-only.** ffmpeg reports overall; Y-only via `psnr=...y`.
- **Frame drops or duplications break VMAF sync.** Need 1:1 correspondence.
- **Different YUV ranges (limited vs full)** change perceptual VMAF. Clamp to same range before compare.
- **Scene-detect threshold 27 default:** gradual transitions need 15–20, abrupt cuts tolerate 35–40.
- **`cropdetect` samples every N seconds.** Variable content = inconsistent reads. Longer duration = reliable.
- **`silencedetect -35 dB` is dialogue.** Music is −50 dB; noise floor is −60 dB.
- **`idet` gives counts, not decisions.** TFF ≈ 2.5× Progressive = telecined (5 fields per 4 frames).
- **`blackdetect pic_th` is 0–1 picture-luma, NOT dB.** 0.98 = near-pure-black only.
- **MediaInfo "Encoded Library" is a heuristic.** Re-encoded files may show wrong encoder.
- **`ffprobe duration_ts` is in stream timebase; `duration` is in seconds.** Don't conflate.
- **`nb_frames=0` means unknown** (stream not fully parsed). Use `-count_frames` for accurate.
- **ExifTool writes in place by default.** `-overwrite_original` strips backups.
- **NAL types differ between H.264 and HEVC.** Don't swap: H.264 SPS = 7, HEVC SPS = 33.
- **SEI messages in HEVC use type+size+payload** with UUID-prefixed T.35 for DoVi / HDR10+ / captions.
- **Bitstream analysis on encrypted content fails.** Widevine / FairPlay encrypt the essence below the container.
- **`ffplay` blocks.** Use `-autoexit` to exit after duration or background with `&`.
- **`ffprobe -show_streams` is INI-style by default.** Use `-of json` or `-of csv=p=0` for scripting.
- **`jq -r` drops quotes.** Omit `-r` if downstream needs JSON.
- **MediaInfo CLI `--Output=JSON` is version-gated.** v21+ produces much better JSON than v20.
- **VMAF motion metric is I/O-bound** on large sources. Use SSDs.
- **Non-deterministic encoders (x265 with threads) produce slightly different output per run.** Expect ± 0.5 VMAF variance between runs of the same command.

### Example — CI gate on an encoded asset

`moprobe --color source.mov` → sanity-check tags. `moqc --ref source.mov --out encoded.mp4 --vmaf-min 93 --format json` → fail build non-zero. `ffmpeg-detect silencedetect` confirms no > 2 s dead air. `media-ffmpeg-normalize --measure-only` confirms −16 LUFS ± 1.
