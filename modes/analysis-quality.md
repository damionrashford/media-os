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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-analysis-quality/SKILL.md`. Read tool skills: `ffmpeg-quality`, `ffmpeg-detect`, `media-ffmpeg-normalize`, `ffmpeg-probe`, `media-mediainfo`.
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
