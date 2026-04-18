---
name: media-musicgen
description: >
  Open-source AI music generation with permissive-license models: Riffusion (MIT, spectrogram-to-audio music from text), YuE (Apache 2.0, Chinese Academy 2025 full-song generation with vocals), Stable Audio Open (Stability community license, commercial up to 1M ARR). Text-to-music, genre-conditioned generation, full song with structure, continuation from existing audio, stem splits via media-demucs. Use when the user asks to generate music from text, create AI songs, make background music for video, generate a jingle, produce royalty-free music with open-source models, make a full song with vocals, or continue an existing musical idea.
argument-hint: "[prompt] [output]"
---

# Media MusicGen

**Context:** $ARGUMENTS

## Quick start

- **Quick background music (MIT, fully free):** `scripts/musicgen.py generate --model riffusion --prompt "lo-fi hip-hop beat" --duration 10 --out out.wav` → Step 3
- **Full song with vocals:** `scripts/musicgen.py generate --model yue --prompt "emotional indie rock, male vocalist, 80 bpm" --duration 90 --out song.wav` → Step 3
- **Higher-quality 44.1kHz stereo:** `scripts/musicgen.py generate --model stable-audio-open --prompt "ambient cinematic strings" --duration 47 --out out.wav` → Step 3 (read LICENSES.md first)
- **Continue an existing idea:** `scripts/musicgen.py continue --in sketch.wav --prompt "build into chorus" --duration 20 --out extended.wav` → Step 4
- **Split generated music into stems:** `scripts/musicgen.py stems --in out.wav --out-dir stems/` → Step 5 (hands off to `media-demucs`)

## When to use

- Generate royalty-free background music for video, podcasts, games
- Prototype song ideas or jingles from a text description
- Produce a full song with AI-generated vocals (YuE only)
- Extend an existing musical idea by feeding it as continuation prompt
- Build AI-music pipelines that stay commercial-safe

**Do NOT use this skill for:**
- MusicGen / AudioCraft — **EXCLUDED**, CC-BY-NC weights despite MIT code
- Suno / Udio — commercial paid APIs, not open-source
- Lyria / MusicLM — Google proprietary, not open-weights
- Research-only models (Jukebox, MuseNet, etc.)

## Step 1 — Pick a model

| Task                                       | Recommended       | License                                         | Commercial use?              | Vocals? |
| ------------------------------------------ | ----------------- | ----------------------------------------------- | ---------------------------- | ------- |
| Any, lowest friction, fully permissive     | **Riffusion**     | MIT                                             | Yes, unconditionally         | No      |
| Full song with vocals, best 2025 quality   | **YuE**           | Apache 2.0                                      | Yes, unconditionally         | Yes     |
| Highest audio quality, instrumental        | **Stable Audio Open** | Stability AI Community License              | Yes, up to $1M annual revenue | No      |

Full license audit (including excluded models and Stable Audio's $1M ARR cap) in [`references/LICENSES.md`](references/LICENSES.md).

## Step 2 — Install

```bash
# Riffusion (MIT, diffusers-based)
pip install diffusers transformers torch accelerate soundfile

# YuE (Apache 2.0) — HuggingFace transformers based
pip install transformers torch soundfile
# YuE models: m-a-p/YuE-s1-7B-anneal-en-cot (English, chain-of-thought)
#             m-a-p/YuE-s1-7B-anneal-zh-cot (Mandarin)

# Stable Audio Open (Stability Community License)
pip install stable-audio-tools soundfile
# (HuggingFace: stabilityai/stable-audio-open-1.0)
```

Or let the script help:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py install riffusion
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py install yue
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py install stable-audio-open
```

Check what's available:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py check
```

## Step 3 — Generate

```bash
# Riffusion — fast, MIT, spectrogram diffusion
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model riffusion \
    --prompt "dreamy lo-fi hip-hop beat with mellow piano" \
    --duration 10 \
    --out beat.wav

# YuE — full song with vocals
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model yue \
    --prompt "emotional indie rock, male vocalist, 80 bpm, acoustic guitar, simple drums" \
    --duration 90 \
    --out song.wav

# Stable Audio Open — 44.1 kHz stereo, instrumental
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model stable-audio-open \
    --prompt "ambient cinematic strings, slow rise, film score" \
    --duration 47 \
    --out cue.wav
```

**Per-model limits:**
- Riffusion native window is 5-second spectrograms. Longer durations (>5s) are produced by repeated inference + crossfade; the script handles this automatically.
- YuE accepts "chain-of-thought" prompts with sections (Verse 1 / Chorus / Bridge). Prompt engineering matters more than other models.
- Stable Audio Open caps individual generations at ~47 seconds.

## Step 4 — Continue an existing audio idea

Feed an existing clip as seed; the model continues in style.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py continue \
    --in sketch.wav \
    --model stable-audio-open \
    --prompt "add energy, build into chorus" \
    --duration 20 \
    --out extended.wav
```

Only Stable Audio Open and Riffusion support continuation reliably; YuE's continuation API is less stable.

## Step 5 — Split output into stems (vocals / drums / bass / other)

Delegates to the `media-demucs` skill.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py stems \
    --in song.wav \
    --out-dir stems/
# -> stems/vocals.wav, stems/drums.wav, stems/bass.wav, stems/other.wav
```

## Step 6 — Post-process / mux

- **Loudness normalization for streaming:** hand off to `media-ffmpeg-normalize` (Spotify -14 LUFS, YouTube -14 LUFS, broadcast -23 LUFS).
- **Export MP3 / Opus / FLAC:** `ffmpeg -i song.wav -c:a libmp3lame -b:a 320k song.mp3`
- **Use as video background:** `ffmpeg -i video.mp4 -i music.wav -map 0:v -map 1:a -c:v copy -shortest out.mp4`
- **Loop seamlessly:** see `ffmpeg-audio-filter` skill (afade + concat demuxer).

## Gotchas

- **License boundary with Stable Audio Open:** the Stability AI Community License permits commercial use **only up to $1M in cumulative revenue**. Above that you need a commercial agreement with Stability. Riffusion and YuE have no such cap. Flag this early to the user. See [`references/LICENSES.md`](references/LICENSES.md).
- **MusicGen / AudioCraft / Suno / Udio are EXCLUDED** from this skill. MusicGen's code is MIT but weights are CC-BY-NC. Do not recommend or install them here.
- **Prompt engineering dominates output quality.** Bad results are almost always prompt problems. Try: genre + instrumentation + tempo + mood + production style (e.g. "80 bpm lo-fi hip-hop beat with mellow rhodes piano and vinyl crackle, chill sunset vibe").
- **Riffusion generates via spectrograms.** Under the hood it's Stable Diffusion v1.5 fine-tuned to produce mel-spectrograms, then Griffin-Lim or WaveNet-style decoder. This is why 5 s is the native window.
- **YuE produces vocals but expects structured prompts.** Its best results are with section labels: `"[Verse 1]\n...lyrics...\n[Chorus]\n...lyrics..."`. See the YuE HuggingFace model card.
- **Stable Audio Open output is 44.1 kHz stereo FP32.** Save directly; no resampling needed for most mastering workflows.
- **GPU is practically required for YuE** (7B params). Riffusion runs on CPU slowly (~2 min for 5 s); Stable Audio Open needs GPU for any reasonable speed.
- **Durations are approximate.** All three models generate fixed-length latents; actual output length can be ±10% of the requested duration.
- **Seeds:** pass `--seed N` for reproducibility. Default is a random seed each run.
- **Model downloads are 2-15 GB each.** First run caches into `~/.cache/huggingface/`.
- **Stereo vs mono:** Riffusion is mono-only. YuE is mono. Stable Audio Open is stereo. Upmix to stereo in ffmpeg if needed: `-ac 2`.
- **No copyright laundering:** the user is responsible for confirming generated music doesn't accidentally reproduce a copyrighted melody. Highly specific artist-imitation prompts raise the risk — use genre/mood descriptors instead of artist names.
- **Avoid `--chain-of-thought` in prompts for non-YuE models.** Prompts that reference "Verse 1 / Chorus" etc. confuse Riffusion and Stable Audio Open.

## Examples

### Example 1: 10-second background music for a video intro

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model riffusion \
    --prompt "upbeat corporate bright synth pad, inspirational" \
    --duration 10 \
    --out intro_music.wav

ffmpeg -i intro.mp4 -i intro_music.wav \
    -map 0:v -map 1:a -c:v copy -shortest intro_scored.mp4
```

### Example 2: Full 90-second indie rock song with vocals via YuE

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model yue \
    --prompt "[Verse 1] acoustic guitar picking, soft male vocals about a road trip. [Chorus] full band, big drums, uplifting harmonies, 80 bpm. [Verse 2] same as verse 1 with harmony vocal." \
    --duration 90 \
    --seed 42 \
    --out indie_song.wav
```

### Example 3: Stable Audio Open cinematic cue + stem split for DAW mix

```bash
# Generate
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py generate \
    --model stable-audio-open \
    --prompt "ambient cinematic strings, slow build, film score, Johann Johannsson style" \
    --duration 45 \
    --out cue.wav

# Split stems for further work
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py stems --in cue.wav --out-dir cue_stems/
# -> cue_stems/{vocals,drums,bass,other}.wav (other will dominate for instrumental)
```

### Example 4: Extend a sketch idea

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/musicgen.py continue \
    --in sketch_8bars.wav \
    --model stable-audio-open \
    --prompt "build into a climax, more energy, bigger drums" \
    --duration 15 \
    --out sketch_extended.wav
```

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'diffusers'`

Cause: Riffusion backend isn't installed.
Solution: `pip install diffusers transformers torch accelerate soundfile` or `scripts/musicgen.py install riffusion`.

### Error: `CUDA out of memory` on YuE

Cause: YuE 7B needs ~16 GB VRAM in fp16.
Solution: load in int4 / bnb-4bit (`--load-in-4bit` flag; requires `bitsandbytes`), shorten duration, or generate on CPU (slow — 30+ min).

### Output clips at 5 s for longer prompts

Cause: Riffusion's native window is 5 s; longer requires the crossfade-loop which the script normally handles automatically.
Solution: confirm `--duration` exceeds 5 and that the script version is up to date. Try `--model stable-audio-open` for native long-form.

### YuE produces melody but no vocals

Cause: prompt lacks section markers or vocal cues.
Solution: use `[Verse 1]` / `[Chorus]` tags and mention vocals explicitly ("male vocalist", "female vocalist", "harmonies").

### Generated music sounds like a specific copyrighted song

Cause: overly specific artist / song reference in the prompt.
Solution: describe the **style** instead of the source (e.g. "melancholic 90s grunge with distorted guitars" rather than "a Nirvana song").

### Stable Audio Open refuses to run locally

Cause: Stability CC access-gated on HuggingFace.
Solution: accept the model license on https://huggingface.co/stabilityai/stable-audio-open-1.0 and `huggingface-cli login`.

## Reference docs

- [`references/LICENSES.md`](references/LICENSES.md) — strict confirmation of commercial-safety, including Stable Audio Open's $1M ARR cap and explicit exclusions of MusicGen / Suno / Udio / Jukebox.
