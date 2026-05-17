# Mode: podcast-pipeline

**Subagent**: `architect`
**Trigger phrases**: "podcast edit", "TTS podcast", "loudness normalize", "audio mix podcast", "podcast master", "AI voiceover", "podcast post", "EBU R128", "podcast captions", "transcribe podcast"
**Output**: `${MEDIA_WORK_DIR}/modes/podcast-pipeline/{date}_{slug}/`

## Inputs

- **Required**:
  - `mode` — `record-to-master` (raw recording → final), `script-to-podcast` (TTS-driven), `existing-to-master` (re-master existing audio).
  - One of: `script` (for `script-to-podcast`) OR `source` (for `record-to-master` / `existing-to-master`).
- **Optional**:
  - `voice` — TTS voice (for script-to-podcast). Default: Kokoro `af_heart`.
  - `target_lufs` — `-16` (Apple Podcasts / Spotify default), `-19` (older standard), or explicit value.
  - `target_true_peak` — `-1.0` dBTP (default).
  - `music_bed` — optional intro/outro music file.
  - `captions` — `true` (default) to generate WebVTT + SRT via whisper.cpp.

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-podcast-pipeline/SKILL.md`. Read tool skills: `media-tts-ai`, `ffmpeg-audio-filter`, `media-ffmpeg-normalize`, `ffmpeg-captions`, `media-whisper`, `media-demucs` (for record-to-master if needs de-noise/source-separation).
2. Branch by `mode`:
   - **`script-to-podcast`**: invoke `media-tts-ai` with chosen voice + script chunks. Concatenate chunks with `ffmpeg -f concat`. Skip to step 4.
   - **`record-to-master`**: `moprobe <source>` → if multi-track, route through `media-demucs` for vocal isolation; otherwise straight to step 3.
   - **`existing-to-master`**: `moprobe <source>` → straight to step 3.
3. De-noise: `DeepFilterNet` (MIT) for voice. NOT Wave-U-Net (research-only).
4. EQ + compression: high-pass at 80Hz, gentle compression (3:1 ratio, -12dB threshold) via `ffmpeg-audio-filter` `acompressor` + `highpass=f=80`.
5. If `music_bed`: ffmpeg `-filter_complex amix` with -18dB music bed under the voice (or sidechain compression for ducking).
6. Loudness normalization: `media-ffmpeg-normalize` to `target_lufs` (default -16 LUFS, -1.0 dBTP true peak).
7. **`mosafe`-wrap** the final ffmpeg invocations.
8. If `captions`: run `whisper.cpp` (or `faster-whisper`) on the normalized audio. Produce both `.srt` (for video embedding) and `.vtt` (for podcast platforms supporting it).
9. Final output: MP3 192kbps CBR (Apple Podcasts spec) OR M4A AAC 128kbps (modern). Embed ID3 tags (title, artist, year, cover art if provided).
10. Run `moqc --ref <pre-normalization> --out <final>` for sanity (not a gate; podcast audio doesn't fail VMAF).
11. Write `summary.md` with LUFS reading, true peak, file size, duration, caption stats.

## Output schema

```markdown
# Podcast pipeline — {slug} — {date}

## Pipeline
- **Mode**: {record-to-master / script-to-podcast / existing-to-master}
- **De-noise**: {DeepFilterNet / none}
- **EQ + compression**: {applied / passthrough}
- **Music bed**: {path or none}
- **Loudness target**: {N LUFS} / {N dBTP}

## Final audio
- **Duration**: {hh:mm:ss}
- **LUFS (integrated)**: {N}
- **LUFS (max momentary)**: {N}
- **True peak**: {N dBTP}
- **Loudness range (LRA)**: {N LU}
- **Codec / bitrate**: {MP3 192kbps / M4A AAC 128kbps}
- **File size**: {bytes}

## Captions
- **SRT**: {path or N/A}
- **VTT**: {path or N/A}
- **Word count**: {N}
- **WER estimate (whisper confidence avg)**: {N%}

## Files
- **Master audio**: {path}
- **Cover art** (if embedded): {path}
```

## Quality bar

- Integrated LUFS within ±0.5 LU of `target_lufs`.
- True peak ≤ `target_true_peak` (default -1.0 dBTP).
- Codec/bitrate matches target spec (MP3 192kbps CBR for Apple Podcasts; modern alternatives explicitly named).
- Captions cover ≥ 95% of speech (sanity check via whisper confidence average).
- No silent gaps > 3 seconds in TTS output (model-stitching gotcha).
- ID3 tags present and well-formed (verified via `exiftool` or `ffprobe`).
