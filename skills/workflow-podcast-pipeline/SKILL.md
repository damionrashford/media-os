---
name: workflow-podcast-pipeline
description: Raw podcast recordings → polished, loudness-compliant (EBU R128 / Spotify / Apple Podcasts / ACX), caption-accurate (Whisper), chapter-tagged deliverables across MP3 / M4A / video-podcast. Covers multi-mic capture, AI denoise, sidechain ducking, auto-chaptering, multi-language subtitles, ID3/MP4 metadata, and batch release. Use when the user says "publish a podcast episode", "normalize loudness to −16 LUFS", "auto-chapter", "podcast subtitles", "batch process episodes", "interview diarization", or anything podcast-production-related.
argument-hint: [episode]
---

# Workflow — Podcast Pipeline

**What:** Take a raw multi-mic recording and ship a broadcast-clean, caption-complete, chapter-tagged, loudness-compliant episode to every podcast platform.

## Skills used

`media-whisper`, `media-demucs`, `media-denoise-ai`, `media-subtitle-sync`, `media-sox`, `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `media-ffmpeg-normalize`, `ffmpeg-detect`, `ffmpeg-metadata`, `ffmpeg-subtitles`, `ffmpeg-captions`, `media-batch`, `media-cloud-upload`, `media-imagemagick`.

## Pipeline

### Step 1 — Capture + concat multi-source

Join separate mic files into aligned tracks via `amix` / `amerge`. Auto time-align against a clap or common audio marker.

### Step 2 — AI denoise per stem BEFORE mixing

`media-denoise-ai`:
- **DeepFilterNet** per mic (general use, 48 kHz mono).
- **RNNoise** for steady-state hum.
- **Resemble Enhance** for speech clarity.

### Step 3 — Classical audio polish

SoX or `ffmpeg-audio-filter`: `highpass=f=80`, parametric EQ boost at ~3 kHz, compand for consistent level.

### Step 4 — Music bed + ducking

Sidechain compression (`sidechaincompress`) ducks music under voice. **Order matters:** key input (voice) FIRST, compressed signal (music) SECOND.

### Step 5 — Transcription

`media-whisper`:
- `large-v3` (3 GB) for best quality.
- `base.en` (140 MB) CPU-friendly; gap to `medium` (1.5 GB) is small on clean studio audio.

Use `--word_timestamps True` (faster-whisper) or `--max-len 1 --split-on-word` (whisper.cpp) for word-accurate subs.

### Step 6 — Auto-sync drifted subs (optional)

`media-subtitle-sync`: `alass` first, `ffsubsync` as fallback.

### Step 7 — Auto-chapter

- **Silence-based** — `ffmpeg-detect` silencedetect at `-35 dB` min-duration `5 s`.
- **Diarization-based** — pyannote.audio or simple-diarizer (external to Whisper).

### Step 8 — Loudness normalize

`media-ffmpeg-normalize` EBU R128 two-pass:

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
- **Binaural / ASMR** — `ffmpeg-audio-spatial` sofalizer HRTF, azimuth/elevation per track.
- **Video podcast with scene detection** — multi-camera auto-cut at detected scenes.
- **Transcript → blog post** — Whisper + external LLM formatting.
- **Multi-language release** — transcribe original, translate externally, mux multiple sub tracks with language metadata.
- **AI-generated intro** — TTS branded intro + Riffusion bed + mix. See `workflow-ai-generation`.

## Gotchas

- **Whisper wants 16 kHz mono** — resamples internally, but explicit `-ar 16000 -ac 1` is cleaner.
- **Demucs wants 44.1 or 48 kHz STEREO.** Mono input → degraded stems.
- **DeepFilterNet: 16 kHz or 48 kHz MONO only.** Mix inputs at 48 kHz mono.
- **RNNoise: 48 kHz mono 16-bit, strict.** Resample first or it fails silently.
- **`loudnorm -target -14` is Spotify Master, NOT podcasts.** Podcasts want −16 (Apple) or −19 (ACX).
- **Single-pass `loudnorm` uses guardrails** — two-pass measures then applies. For compliance, use `media-ffmpeg-normalize` (two-pass).
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

## Related

- `workflow-audio-production` — deeper audio-chain recipes.
- `workflow-ai-generation` — AI intro / voice clone / thumbnails.
- `workflow-analysis-quality` — loudness compliance verification.
