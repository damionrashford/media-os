# Podcast Pipeline Workflow

**What:** Take raw podcast recordings → polished, loudness-compliant, caption-accurate, chapter-tagged, multi-platform deliverables.

**Who:** Podcast producers, indie hosts, media networks, corporate training teams, church/conference recording teams.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| Transcription | `media-whisper` | whisper.cpp / faster-whisper → SRT/VTT |
| Stem separation | `media-demucs` | Isolate voice from music/ambience |
| AI denoise | `media-denoise-ai` | DeepFilterNet / RNNoise / Resemble Enhance |
| Subtitle sync | `media-subtitle-sync` | alass / ffsubsync auto-align |
| Classical audio | `media-sox` | EQ, compression, classical DSP |
| FFmpeg audio | `ffmpeg-audio-filter` | loudnorm, EQ, compander, asetpts |
| FFmpeg audio FX | `ffmpeg-audio-fx` | Chorus, flanger, reverb |
| Audio spatial | `ffmpeg-audio-spatial` | Binaural for headphone mixes |
| Batch loudness | `media-ffmpeg-normalize` | EBU R128 / -16 LUFS / ATSC A/85 |
| Silence detect | `ffmpeg-detect` | Auto-trim / chapter from silence |
| Metadata | `ffmpeg-metadata`, `media-exiftool` | Chapters, cover art, ID3, RSS-compat |
| Subtitles | `ffmpeg-subtitles` | Burn-in / soft-mux |
| Captions | `ffmpeg-captions` | CEA-608 if going to broadcast too |
| Batch scale | `media-batch` | Parallel processing of many episodes |
| Cloud upload | `media-cloud-upload` | RSS host / YouTube / S3 |
| Image cover art | `media-imagemagick` | Resize / compose cover art variations |

---

## The pipeline

### 1. Capture → concatenate multi-source

Most podcasts: multiple mics on individual tracks. Double-ender (Riverside, SquadCast, Zencastr) gives you local-quality stems. Remote-recorded calls give you single mixed tracks.

```bash
# Join two-host WAV recording (separate mic files) with automatic time alignment
ffmpeg -i host1.wav -i guest1.wav \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0[out]" \
  -map "[out]" -c:a pcm_s24le raw-mixed.wav
```

### 2. AI denoise each stem (BEFORE mixing)

Denoising individual mics preserves more signal than post-mix.

```bash
for track in host1 guest1; do
  uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
    --input ${track}.wav --output ${track}-clean.wav
done
```

For extreme cases (wind, HVAC hum, dog bark):
```bash
# RNNoise for steady-state background
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py rnnoise \
  --input host1-clean.wav --output host1-cleaner.wav

# Resemble Enhance for speech clarity / super-res speech
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py resemble \
  --input host1-cleaner.wav --output host1-enhanced.wav
```

### 3. Classical audio polish (SoX or ffmpeg-audio-filter)

```bash
# SoX: parametric EQ + compression
uv run .claude/skills/media-sox/scripts/soxrun.py process \
  --input host1-enhanced.wav --output host1-polished.wav \
  --effects "highpass 80 equalizer 3000 1 3 compand 0.3,1 6:-70,-60,-20 -5 -90 0.2"
```

Or ffmpeg equivalent:
```bash
ffmpeg -i host1-enhanced.wav \
  -af "highpass=f=80, \
       equalizer=f=3000:w=1:g=3, \
       acompressor=threshold=-20dB:ratio=3:attack=200:release=1000" \
  host1-polished.wav
```

### 4. Mix with music + SFX

```bash
# Duck music under voice
ffmpeg -i host1-polished.wav -i guest1-polished.wav -i music.wav \
  -filter_complex "\
    [0][1]amix=inputs=2:duration=longest[voice]; \
    [voice]asplit[vckey][vcmain]; \
    [2][vckey]sidechaincompress=threshold=0.04:ratio=8:attack=10:release=300[ducked_music]; \
    [vcmain][ducked_music]amix=inputs=2:normalize=0[out]" \
  -map "[out]" mixed.wav
```

### 5. Transcribe (Whisper)

```bash
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input mixed.wav \
  --output transcript.srt \
  --model large-v3 \
  --format srt \
  --word-timestamps \
  --language en
```

Faster CPU path:
```bash
uv run .claude/skills/media-whisper/scripts/whisper.py whispercpp \
  --input mixed.wav --output transcript.srt --model base.en
```

### 6. Auto-sync subtitles to audio

If subs drift (e.g., you edited the mix after transcription):
```bash
uv run .claude/skills/media-subtitle-sync/scripts/subsync.py alass \
  --subs transcript.srt --audio mixed.wav --output transcript-synced.srt
```

### 7. Auto-chapter from silence or topic shifts

**Silence-based:**
```bash
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input mixed.wav \
  --threshold -35dB \
  --min-duration 5s \
  --output chapters.json
```

**Topic shift (via embeddings):**
Use `media-whisper` + diarization. Chapter at every new speaker topic.

Convert to FFmpeg chapter metadata:
```bash
uv run .claude/skills/ffmpeg-metadata/scripts/metadata.py chapters-from-json \
  --input mixed.wav \
  --json chapters.json \
  --output mixed-chapters.wav
```

### 8. Loudness normalize (EBU R128 / Spotify / podcast standard)

Podcasts: Spotify wants -14 LUFS integrated, Apple Podcasts is -16 LUFS, broadcast is -23 LUFS.

```bash
# Target -16 LUFS (Apple Podcasts / typical podcast)
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input mixed-chapters.wav \
  --output mixed-final.wav \
  --target -16 \
  --true-peak -1 \
  --lra 11
```

### 9. Package deliverables

**MP3 for broad compatibility:**
```bash
ffmpeg -i mixed-final.wav \
  -c:a libmp3lame -b:a 128k -ac 2 \
  -i cover-3000.jpg -map 0:a -map 1:v \
  -metadata title="Episode 42: The Podcast" \
  -metadata artist="Show Name" \
  -metadata album="Show Name" \
  -metadata date="2026-04-17" \
  -metadata genre="Podcast" \
  -disposition:v:0 attached_pic \
  episode-42.mp3
```

**M4A/AAC for Apple Podcasts:**
```bash
ffmpeg -i mixed-final.wav \
  -c:a aac -b:a 128k \
  -i cover-3000.jpg -map 0:a -map 1:v \
  -disposition:v:0 attached_pic \
  episode-42.m4a
```

**Video podcast version:**
```bash
# Static waveform / speaker photos via ffmpeg
ffmpeg -loop 1 -i cover-vertical.jpg -i mixed-final.wav \
  -vf "showwaves=s=1920x200:mode=line:colors=white" \
  -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
  -shortest -pix_fmt yuv420p \
  episode-42.mp4
```

### 10. Batch scale

For a show with many episodes:

```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob 'raw/episode-*.wav' \
  --output-dir published/ \
  --jobs 4 \
  --command 'bash process-episode.sh {in} {out}'
```

### 11. Publish

```bash
# Cloud host
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --bucket podcast-cdn --prefix episodes/ --file episode-42.mp3

# YouTube (video podcast)
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py stream \
  --provider youtube --file episode-42.mp4 --title "Episode 42"
```

---

## Variants

### Interview podcast (multi-speaker diarization)

```bash
# 1. Transcribe with speaker labels
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input mixed.wav --output transcript.json --diarize

# 2. Emit SRT with speaker prefixes
jq -r '.segments[] | "\(.start) \(.end) [\(.speaker)]: \(.text)"' transcript.json
```

### Music podcast / DJ set

Stem separation lets you promote tracks without full license:

```bash
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input set.wav --output-dir stems/ --model htdemucs

# stems/vocals.wav, drums.wav, bass.wav, other.wav
# Use vocals + drums only for Instagram Reels preview
ffmpeg -i stems/vocals.wav -i stems/drums.wav \
  -filter_complex "[0][1]amix=inputs=2" preview.wav
```

### Binaural podcast (ASMR / narrative)

```bash
uv run .claude/skills/ffmpeg-audio-spatial/scripts/spatial.py hrtf \
  --input mono.wav --output binaural.wav \
  --azimuth 45 --elevation 0 \
  --sofa-file cipic-subject-021.sofa
```

### Video podcast with scene detection

```bash
# 1. Video of multi-camera recording
uv run .claude/skills/media-scenedetect/scripts/scenedetect.py detect \
  --input multicam.mp4 --output scenes.csv --threshold 27

# 2. Cut at detected scenes
# (Or use these as automatic camera-angle chapter points)
```

### Transcription to blog post

```bash
# Whisper + formatting pipeline
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input mixed.wav --output transcript.txt --format txt

# Post-process with LLM externally for blog formatting
```

### Multi-language release

```bash
# Transcribe original, translate subs externally, re-mux
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input mixed.wav --output en.srt --language en

# (translate en.srt → es.srt externally — Whisper's --task translate only goes TO English)

# Mux multiple sub tracks
ffmpeg -i episode.m4a -i en.srt -i es.srt -i fr.srt \
  -map 0 -map 1 -map 2 -map 3 \
  -metadata:s:s:0 language=eng \
  -metadata:s:s:1 language=spa \
  -metadata:s:s:2 language=fre \
  -c copy -c:s mov_text \
  episode-multilang.m4a
```

### AI intro generation

```bash
# 1. TTS a branded intro
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py kokoro \
  --text "Welcome to Episode 42 of the Show." \
  --voice af --output intro-vo.wav

# 2. Generate branded music bed
uv run .claude/skills/media-musicgen/scripts/musicctl.py riffusion \
  --prompt "Upbeat tech podcast intro, 10 seconds" \
  --duration 10 --output intro-music.wav

# 3. Mix
ffmpeg -i intro-vo.wav -i intro-music.wav \
  -filter_complex "[0][1]amix=inputs=2" intro.wav

# 4. Concatenate before episode
ffmpeg -f concat -safe 0 -i <(printf "file '%s'\nfile '%s'\n" intro.wav mixed-final.wav) \
  -c copy episode-with-intro.wav
```

---

## Gotchas

### Audio technical

- **Whisper expects 16kHz mono.** It resamples internally but upstream noise in stereo → mono conversion can be lost. Downsample explicitly with `ffmpeg -ar 16000 -ac 1` first for best results.
- **Demucs expects 44.1 or 48 kHz stereo.** Mono input silently produces degraded stems.
- **DeepFilterNet processes 16kHz or 48kHz mono.** Mix inputs at 48kHz mono for best quality.
- **RNNoise is strictly 48kHz mono 16-bit.** Resample first.
- **loudnorm at `-target -14` is Spotify Master for music, not podcasts.** Podcasts target -16 (Apple) or -19 (ACX audiobooks). Know your distribution requirement.
- **`loudnorm` with `-target` alone ≠ two-pass loudnorm.** Single-pass uses guardrails; two-pass measures first, applies corrections. For accurate loudness certification, use two-pass (which `media-ffmpeg-normalize` does).
- **`loudnorm` applies a limiter as part of true-peak management.** Over-loudnormed sources sound compressed. Use `lra` (loudness range) parameter to preserve dynamics.
- **Sidechain compression (`sidechaincompress`)** needs the key input first, compressed signal second. Wrong order = wrong ducking.

### Transcription

- **Whisper hallucinates on silence.** Always trim leading silence with `silenceremove` before transcription.
- **Whisper timestamps are end-of-chunk, not word-accurate** without `--word_timestamps`. For caption alignment, always enable word timestamps.
- **`large-v3` is 3GB of weights.** The quality gap to `medium` (1.5GB) is small for clean studio audio. Test both.
- **Whisper `--language auto` is fragile** on accented speech. Specify the language explicitly for production runs.
- **Diarization is external to Whisper.** Use `pyannote.audio` (MIT) or `simple-diarizer`. Neither is bundled in the skill; we only provide the transcription wrapper.

### Metadata / distribution

- **MP3 ID3v2.4 vs v2.3** — Apple Podcasts wants v2.3 + UTF-16 text encoding. `ffmpeg -id3v2_version 3` enforces.
- **Cover art must be ≤ 3000×3000 px, ≥ 1400×1400, under 500KB JPEG or PNG.** Apple rejects larger. Use ImageMagick:
  ```bash
  uv run .claude/skills/media-imagemagick/scripts/imagemagick.py resize \
    --input big-cover.png --output cover-3000.jpg --size 3000x3000 --quality 85
  ```
- **Chapter metadata in MP3** uses CTOC + CHAP frames — ffmpeg writes these from `-metadata chapters` but some older players ignore them.
- **M4A chapter metadata** uses `@chpl` atoms. `ffmpeg` writes these automatically.
- **RSS feed enclosures need `<enclosure>` + exact file size + MIME type.** If you change the file after publishing, the hash mismatch can cause re-downloads. Rev the URL too.

### Pipeline

- **Batch-process episodes in parallel, but SERIALIZE loudness normalization** if you share a single GPU — two parallel ffmpeg loudnorm passes contend for memory.
- **Subtitle sync (`alass`) can silently fail on clean audio.** If the input is already synced, it returns the input unchanged — `--force` won't help. Test with known-bad inputs.
- **`ffsubsync` requires a reference timestamp.** It pattern-matches audio to existing subtitle anchors; naive use can introduce drift.
- **Video-podcast waveform generators (`showwaves`) lock to one audio stream.** For multi-stream mixes, use `showwavespic` (static image) or pre-mix first.

---

## Example — "Full-polish 2-host podcast episode"

```bash
#!/usr/bin/env bash
set -e

HOST1_RAW="raw/host1.wav"
HOST2_RAW="raw/guest1.wav"
MUSIC="assets/music.wav"
COVER="assets/cover-3000.jpg"
EPISODE_NUM="42"
EPISODE_TITLE="The Podcast, Episode 42"
OUT_DIR="published/ep${EPISODE_NUM}"
mkdir -p "$OUT_DIR"

# 1. AI denoise each track
for t in host1 guest1; do
  uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
    --input raw/${t}.wav --output tmp-${t}-clean.wav
done

# 2. Polish with EQ + compression
for t in host1 guest1; do
  ffmpeg -y -i tmp-${t}-clean.wav \
    -af "highpass=f=80, \
         equalizer=f=200:w=1:g=-3, \
         equalizer=f=3000:w=1:g=3, \
         acompressor=threshold=-20dB:ratio=3:attack=200:release=1000" \
    tmp-${t}-polished.wav
done

# 3. Mix hosts + ducked music
ffmpeg -y -i tmp-host1-polished.wav -i tmp-guest1-polished.wav -i "$MUSIC" \
  -filter_complex "\
    [0][1]amix=inputs=2:duration=longest[voice]; \
    [voice]asplit[vckey][vcmain]; \
    [2][vckey]sidechaincompress=threshold=0.04:ratio=8[ducked]; \
    [vcmain][ducked]amix=inputs=2:normalize=0[out]" \
  -map "[out]" -c:a pcm_s24le tmp-mixed.wav

# 4. Transcribe
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input tmp-mixed.wav --output "$OUT_DIR/transcript.srt" \
  --model large-v3 --format srt --word-timestamps --language en

# 5. Auto-chapter from silence
uv run .claude/skills/ffmpeg-detect/scripts/detect.py silence \
  --input tmp-mixed.wav --threshold -35dB --min-duration 5s \
  --output "$OUT_DIR/chapters.json"

# 6. Loudness-normalize to -16 LUFS
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input tmp-mixed.wav --output tmp-loudnormed.wav \
  --target -16 --true-peak -1 --lra 11

# 7. Resize cover
uv run .claude/skills/media-imagemagick/scripts/imagemagick.py resize \
  --input "$COVER" --output tmp-cover.jpg --size 3000x3000 --quality 85

# 8. Package MP3 (RSS-compatible)
ffmpeg -y -i tmp-loudnormed.wav -i tmp-cover.jpg \
  -map 0:a -map 1:v \
  -c:a libmp3lame -b:a 128k -ac 2 \
  -id3v2_version 3 \
  -metadata title="$EPISODE_TITLE" \
  -metadata artist="Show Name" \
  -metadata album="Show Name" \
  -metadata date="$(date +%Y-%m-%d)" \
  -metadata genre="Podcast" \
  -metadata track="$EPISODE_NUM" \
  -disposition:v:0 attached_pic \
  "$OUT_DIR/ep${EPISODE_NUM}.mp3"

# 9. Package M4A (Apple Podcasts with chapters)
ffmpeg -y -i tmp-loudnormed.wav -i tmp-cover.jpg \
  -map 0:a -map 1:v \
  -c:a aac -b:a 128k \
  -metadata title="$EPISODE_TITLE" \
  -metadata artist="Show Name" \
  -metadata album="Show Name" \
  -disposition:v:0 attached_pic \
  "$OUT_DIR/ep${EPISODE_NUM}.m4a"

# 10. Upload to CDN
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --bucket podcast-cdn \
  --prefix episodes/ \
  --file "$OUT_DIR/ep${EPISODE_NUM}.mp3"

# Cleanup temp
rm tmp-*.wav tmp-*.jpg

echo "Published: ep${EPISODE_NUM}"
```

---

## Further reading

- [`ai-generation.md`](ai-generation.md) — TTS intros, music beds, voice cloning
- [`audio-production.md`](audio-production.md) — deeper audio routing + MIDI/OSC
- [`ai-enhancement.md`](ai-enhancement.md) — deeper denoise / Resemble Enhance for terrible source audio
- [`analysis-quality.md`](analysis-quality.md) — loudness certification and QC
