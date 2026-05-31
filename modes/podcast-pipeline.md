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

1. Read tool skills: `ai-generate`, `ffmpeg-filter`, `media-audio-cli`, `ffmpeg-subtitle`, `media-whisper`, `media-demucs` (for record-to-master if needs de-noise/source-separation).
2. Branch by `mode`:
   - **`script-to-podcast`**: invoke `ai-generate` with chosen voice + script chunks. Concatenate chunks with `ffmpeg -f concat`. Skip to step 4.
   - **`record-to-master`**: `moprobe <source>` → if multi-track, route through `media-demucs` for vocal isolation; otherwise straight to step 3.
   - **`existing-to-master`**: `moprobe <source>` → straight to step 3.
3. De-noise: `DeepFilterNet` (MIT) for voice. NOT Wave-U-Net (research-only).
4. EQ + compression: high-pass at 80Hz, gentle compression (3:1 ratio, -12dB threshold) via `ffmpeg-filter` `acompressor` + `highpass=f=80`.
5. If `music_bed`: ffmpeg `-filter_complex amix` with -18dB music bed under the voice (or sidechain compression for ducking).
6. Loudness normalization: `media-audio-cli` to `target_lufs` (default -16 LUFS, -1.0 dBTP true peak).
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

## Playbook reference (folded from workflow-podcast-pipeline)

**What:** Take a raw multi-mic recording and ship a broadcast-clean, caption-complete, chapter-tagged, loudness-compliant episode to every podcast platform.

## Pipeline

### Step 1 — Capture + concat multi-source

Join separate mic files into aligned tracks via `amix` / `amerge`. Auto time-align against a clap or common audio marker.

### Step 2 — Denoise per stem BEFORE mixing

`ffmpeg-filter`:
- **`afftdn`** per mic (FFT broadband denoise; tune `nr`/`nf`).
- **`arnndn=m=<model>.rnnn`** (RNNoise model) for steady-state hum/hiss.
- **`anlmdn`** (non-local-means) for low-SNR voice.

### Step 3 — Classical audio polish

SoX or `ffmpeg-filter`: `highpass=f=80`, parametric EQ boost at ~3 kHz, compand for consistent level.

### Step 4 — Music bed + ducking

Sidechain compression (`sidechaincompress`) ducks music under voice. **Order matters:** key input (voice) FIRST, compressed signal (music) SECOND.

### Step 5 — Transcription

`media-whisper`:
- `large-v3` (3 GB) for best quality.
- `base.en` (140 MB) CPU-friendly; gap to `medium` (1.5 GB) is small on clean studio audio.

Use `--word_timestamps True` (faster-whisper) or `--max-len 1 --split-on-word` (whisper.cpp) for word-accurate subs.

### Step 6 — Auto-sync drifted subs (optional)

`ffmpeg-subtitle`: `alass` first, `ffsubsync` as fallback.

### Step 7 — Auto-chapter

- **Silence-based** — `ffmpeg-analyze` silencedetect at `-35 dB` min-duration `5 s`.
- **Diarization-based** — pyannote.audio or simple-diarizer (external to Whisper).

### Step 8 — Loudness normalize

`media-audio-cli` EBU R128 two-pass:

| Target | LUFS |
|---|---|
| Spotify Master | −14 |
| Apple Podcasts | −16 |
| ACX audiobooks | −19 |
| General podcast | −16 to −19 |

### Step 9 — Package deliverables

- **MP3** — `id3v2_version 3`, UTF-16 text, cover 1400–3000 px square ≤ 500 KB.
- **M4A / AAC** — Apple Podcasts. Chapters via `@chpl` atom (ffmpeg writes automatically).
- **Video podcast** — `showwaves` static waveform or pre-mix video track.

### Step 10 — Batch + publish

`media-batch` (GNU parallel) for N-episode throughput. `media-cloud-upload` to host + YouTube.

## Variants

- **Interview podcast** — pyannote diarization, SRT with speaker labels.
- **Music podcast / DJ set** — `media-demucs` stem isolation for promo clips.
- **Binaural / ASMR** — `ffmpeg-filter` sofalizer HRTF, azimuth/elevation per track.
- **Video podcast with scene detection** — multi-camera auto-cut at detected scenes.
- **Transcript → blog post** — Whisper + external LLM formatting.
- **Multi-language release** — transcribe original, translate externally, mux multiple sub tracks with language metadata.
- **AI-generated intro** — TTS branded intro + Riffusion bed + mix. See the `ai-generation` mode.

## Gotchas

- **Whisper wants 16 kHz mono** — resamples internally, but explicit `-ar 16000 -ac 1` is cleaner.
- **Demucs wants 44.1 or 48 kHz STEREO.** Mono input → degraded stems.
- **DeepFilterNet: 16 kHz or 48 kHz MONO only.** Mix inputs at 48 kHz mono.
- **RNNoise: 48 kHz mono 16-bit, strict.** Resample first or it fails silently.
- **`loudnorm -target -14` is Spotify Master, NOT podcasts.** Podcasts want −16 (Apple) or −19 (ACX).
- **Single-pass `loudnorm` uses guardrails** — two-pass measures then applies. For compliance, use `media-audio-cli` (two-pass).
- **`loudnorm` applies a limiter** — over-loudnormed audio sounds compressed. Tune `lra` to preserve dynamics.
- **Sidechain compression order: key input FIRST, compressed signal SECOND.** Wrong order = wrong ducking.
- **Whisper hallucinates on silence.** `silenceremove` leading/trailing before transcription.
- **Whisper timestamps end-of-chunk by default.** Word-level requires `--word_timestamps`.
- **Whisper `--language auto` is fragile on accents.** Specify explicitly.
- **MP3 ID3v2.4 vs v2.3:** Apple Podcasts requires v2.3 + UTF-16 text. `-id3v2_version 3`.
- **Cover art: 1400–3000 px square, < 500 KB JPEG/PNG.** Apple rejects larger.
- **MP3 chapter metadata** uses CTOC + CHAP frames. ffmpeg writes from `-metadata chapters` but older players ignore.
- **M4A chapter metadata** uses `@chpl` atoms — ffmpeg writes automatically.
- **RSS enclosures need exact file size + MIME type.** Post-publish file change = hash mismatch → listeners re-download.
- **Serialize loudness normalization if sharing GPU** with other jobs — two parallel `loudnorm` = memory contention.
- **`alass` fails on already-synced audio** (returns input unchanged). `--force` won't help.
- **`ffsubsync` pattern-matches audio to existing subtitle anchors.** Naive use on very-drifted subs = drift amplification.
- **`showwaves` locks to one audio stream.** For multi-stream, use `showwavespic` (static) or pre-mix.

## Example — 60-minute interview → deliverables

Multi-mic input → DeepFilterNet per mic → amix → EQ + compand → music bed with sidechain duck → Whisper large-v3 word-timestamps → alass subtitle sync → silencedetect auto-chapter → loudnorm −16 LUFS two-pass → MP3 + M4A with chapter atoms + cover art → upload.
