---
name: media-sox
description: >
  Audio processing with SoX (Swiss Army Knife of audio): format conversion, trim/cut, pad, reverse, speed/pitch change, fade, silence detection and removal, noise profile + reduction, synth tones, channel ops, dither. Use when the user asks to process audio with SoX, trim silence, remove noise with sox noise-profile/noisered (better than ffmpeg afftdn for some cases), generate synth audio, apply a sox effects chain, or convert audio formats with precise dither control.
argument-hint: "[operation] [input]"
---

# Media Sox

**Context:** $ARGUMENTS

## Quick start

- **Convert/resample/rebit:** `sox in.wav -r 48000 -b 16 -c 2 out.flac` → Step 3
- **Trim silence:** `sox in.wav out.wav silence 1 0.1 1% -1 0.5 1%` → Step 3
- **Denoise (2-pass):** profile then reduce → Step 3 (Denoise recipe)
- **Peak normalize:** `sox --norm in.wav out.wav` → Step 3
- **Synth test tone:** `sox -n out.wav synth 3 sine 440` → Step 3
- **Probe/stats:** `sox --i in.wav` or `sox in.wav -n stats` → Step 3

## When to use

- Surgical audio work where precise chain order and dither control matters more than ffmpeg's convenience.
- Denoise via two-pass noise-profile + spectral subtraction (often cleaner than `ffmpeg afftdn` for stationary noise).
- Batch audio conversion / resample / bit-depth / channel ops with a simple, fast CLI.
- Synthesizing test tones, pink/white/brown noise, or sweep signals for calibration.
- Detecting + stripping silence between segments (podcast polish, voicemail trim).
- Quick signal stats (peak dBFS, RMS, DC offset, bit depth) without opening a DAW.

Use **ffmpeg loudnorm** for EBU R128 / broadcast loudness, **demucs/spleeter** for stem separation, **whisper** for transcripts — SoX does none of those.

## Step 1 — Install

```bash
brew install sox           # macOS
sudo apt-get install sox   # Debian/Ubuntu
sox --version              # confirm
sox -h | grep 'AUDIO FILE FORMATS'   # see compiled-in formats
```

MP3 read/write is often **not** compiled in on Homebrew builds. The old `brew install sox --with-lame` flag was removed from Homebrew years ago. If you need MP3, either convert via `ffmpeg` / `lame` externally, or `sox in.wav -t wav - | lame - out.mp3`. WAV / AIFF / FLAC / OGG Vorbis / raw / au are virtually always present.

## Step 2 — Pick the operation

Map the user's request to the matching SoX form:

| Goal | Shape |
|---|---|
| Convert container | `sox in.EXT out.EXT` |
| Resample | `sox in -r 48000 out` (file option, pre-filename) |
| Bit depth | `sox in -b 16 out` (file option) |
| Channels | `sox in -c 1 out` (file option) |
| Trim | `sox in out trim START [DUR]` (effect) |
| Pad | `sox in out pad HEAD TAIL` (effect) |
| Reverse | `sox in out reverse` |
| Tempo (keep pitch) | `sox in out tempo 1.5` |
| Pitch (keep tempo) | `sox in out pitch 200` (cents) |
| Speed (both) | `sox in out speed 1.5` |
| Fade | `sox in out fade IN STOP OUT` |
| Silence trim | `sox in out silence 1 0.1 1% -1 0.5 1%` |
| Peak normalize | `sox --norm in out` |
| Gain (pre) | `sox -v 0.5 in out` (file opt) |
| Gain (effect) | `sox in out gain -3` |
| Reverb | `sox in out reverb 50 50 100` |
| Compand | `sox in out compand 0.3,1 6:-70,-60,-20 -5 -90 0.2` |
| Noise profile | `sox in -n trim 0 1 noiseprof noise.prof` |
| Noise reduce | `sox in out noisered noise.prof 0.21` |
| Synth tone | `sox -n out synth 3 sine 440` |
| Synth noise | `sox -n out synth 5 pinknoise` |
| Concat | `sox a.wav b.wav out.wav` |
| Mix (sum) | `sox -m a.wav b.wav out.wav` |
| Probe | `sox --i in` |
| Stats | `sox in -n stats` |

**Rule:** file options (`-r`, `-b`, `-c`, `-v`, `-e`, `-t`, `--norm`) go **before the file they modify**. Effects (`trim`, `pad`, `gain`, `fade`, `tempo`, `pitch`, `reverb`, `compand`, `silence`, `noiseprof`, `noisered`, `synth`, `reverse`) go **after the output filename**, and are applied **left-to-right**.

## Step 3 — Run the effect chain

### Convert + resample + rebit + mono

```bash
sox in.wav -r 48000 -b 16 -c 1 out.flac
```

### Trim first 30s / extract 20s from 0:10

```bash
sox in.wav out.wav trim 0 30
sox in.wav out.wav trim 10 20
```

### Pad 1s head / 2s tail

```bash
sox in.wav out.wav pad 1 2
```

### Tempo up 50% (keep pitch) / pitch up 2 semitones (keep tempo) / both

```bash
sox in.wav out.wav tempo 1.5
sox in.wav out.wav pitch 200   # cents: 100 cents = 1 semitone
sox in.wav out.wav speed 1.5
```

### Fade 1s in, 1s out, no trim

```bash
sox in.wav out.wav fade 1 -0 1
```

### Silence trim (remove ALL silences > 0.5s below 1% amplitude)

```bash
sox in.wav out.wav silence 1 0.1 1% -1 0.5 1%
```

### Peak normalize to 0 dBFS

```bash
sox --norm in.wav out.wav
```

### Reverb (reverberance 50, HF-damping 50, room-scale 100)

```bash
sox in.wav out.wav reverb 50 50 100
```

### Dynamic-range compression (voice podcast starter)

```bash
sox in.wav out.wav compand 0.3,1 6:-70,-60,-20 -5 -90 0.2
```

### Denoise (TWO-pass — pure-noise sample required)

```bash
# 1) profile from 1s of noise-only at the start
sox in.wav -n trim 0 1 noiseprof noise.prof
# 2) subtract profile (0.21 is conservative; 0.30 aggressive; max 1.0)
sox in.wav out.wav noisered noise.prof 0.21
```

### Generate tone / pink noise

```bash
sox -n out.wav synth 3 sine 440
sox -n out.wav synth 5 pinknoise
```

### Concat / mix / probe / stats

```bash
sox a.wav b.wav out.wav
sox -m a.wav b.wav out.wav
sox --i in.wav
sox in.wav -n stats
```

## Available scripts

- **`scripts/sox.py`** — argparse wrapper for check / info / convert / trim / tempo / pitch / fade / silence-trim / denoise / normalize / synth / concat / mix / stats. Supports `--dry-run` and `--verbose`. Stdlib-only.

## Workflow

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/sox.py check
uv run ${CLAUDE_SKILL_DIR}/scripts/sox.py convert --input in.wav --output out.flac --rate 48000 --bits 16
uv run ${CLAUDE_SKILL_DIR}/scripts/sox.py denoise --input in.wav --output clean.wav --noise-sample "0 1"
```

## Reference docs

- Read [`references/sox.md`](references/sox.md) for the full effect catalog, file-option vs effect distinction, dither controls, noise-reduction best practices, synth waveforms, and recipe book (vinyl rip, podcast polish, per-episode silence trim, dynamic-range compression).

## Gotchas

- **Compiled-in formats limit you.** Check `sox -h`. MP3 is frequently absent; WAV/AIFF/FLAC/OGG are virtually always present. Route MP3 through `ffmpeg` or `lame`.
- **Chain order matters — left to right.** `sox in out gain -6 norm` ≠ `sox in out norm gain -6`.
- **`-v` is a FILE option, not an effect.** Place it *before* the filename it scales. `sox -v 0.5 in.wav out.wav` halves the input; `sox in.wav -v 0.5 out.wav` would apply 0.5 to the output gain handling.
- **`gain` (effect) goes after the output filename**, like all other effects. Don't confuse it with `-v`.
- **Headerless files need explicit format.** `sox -r 48000 -b 16 -c 1 -e signed-integer raw.pcm out.wav`.
- **`tempo 1.5` = 50% faster, same pitch** (WSOLA-style). **`pitch 200` = up 2 semitones** (100 cents per semitone). **`speed 1.5` changes BOTH** — equivalent to playing the file back faster (varispeed).
- **Dither is ON by default when reducing bit depth.** Disable with `-D` *before* the output filename if you don't want it.
- **`silence` syntax is cryptic.** `silence 1 0.1 1% -1 0.5 1%`: first `1` = trim leading silence; `0.1` = min silence duration (s); `1%` = amplitude threshold; `-1` = also remove ALL internal/trailing silences; `0.5` = min internal-silence duration; `1%` = same threshold.
- **`noisered` second arg is sensitivity 0.0–1.0.** Start at 0.21. Higher values destroy transients and introduce "underwater" artifacts. If profile was short or impure, drop to 0.15.
- **`noiseprof` profile is plain text** — you can inspect / diff it. It's tied to sample rate of the profiling source.
- **Sample-rate conversion uses a high-quality polyphase filter by default.** No flag needed for broadcast-grade resampling.
- **SoX does NOT do EBU R128 loudness normalization.** For broadcast `-14/-16/-23 LUFS`, use `ffmpeg loudnorm` or `ffmpeg-normalize`. `sox --norm` is peak-only.
- **Piping across processes works via `-t` format flag:** `sox in.wav -t wav - | sox -t wav - out.wav effect`.
- **Stats output** (`-n stats`) reports DC offset, peak dBFS, RMS, bit-depth, crest factor — ideal for QC.

## Examples

### Example 1: podcast episode polish

Input: `raw.wav` (48 kHz 24-bit, interview with handling noise).
Steps:
```bash
# 1) profile 1s of room tone at the very start (trim it off later)
sox raw.wav -n trim 0 1 noiseprof noise.prof
# 2) denoise, trim, compress, peak-normalize, fade
sox raw.wav episode.wav \
  noisered noise.prof 0.21 \
  silence 1 0.1 1% -1 0.5 1% \
  compand 0.3,1 6:-70,-60,-20 -5 -90 0.2 \
  gain -n -1 \
  fade 0.05 -0 0.2
```
Result: cleaned, silence-trimmed, compressed, -1 dBFS peak, gentle fades.

### Example 2: generate a 440 Hz test tone and mix with a spoken track

```bash
sox -n tone.wav synth 3 sine 440 vol -20dB
sox -m voice.wav tone.wav mixed.wav
```

### Example 3: batch resample folder to 48 kHz / 16-bit WAV

```bash
for f in *.wav; do sox "$f" -r 48000 -b 16 "out/$f"; done
```

## Troubleshooting

### Error: `sox FAIL formats: no handler for file extension 'mp3'`

Cause: MP3 not compiled in.
Solution: Use `ffmpeg -i in.mp3 in.wav` first, or pipe: `ffmpeg -i in.mp3 -f wav - | sox - out.wav <effects>`.

### Error: `sox FAIL sox: Input files must have the same sample-rate`

Cause: concat/mix with mismatched sample rates.
Solution: Resample first: `sox a.wav -r 48000 a_48k.wav`, then concat.

### Output is clipped / distorted after chain

Cause: stacked gain or effects pushed peaks > 0 dBFS.
Solution: Append `gain -n -1` at the end of the chain (normalize to -1 dBFS).

### Denoise sounds "underwater" or metallic

Cause: `noisered` sensitivity too high, or profile taken from non-stationary noise.
Solution: Drop the second arg to 0.15; re-profile from a purer, longer noise-only sample; confirm noise is stationary (HVAC, hiss) — transient clicks need `adeclick`-style tools (ffmpeg/LADSPA).

### "sox: effect `silence' does not accept arguments..."

Cause: effect args on wrong side of filename, or missing one of the six arguments.
Solution: Full form is `silence ABOVE-PERIODS DURATION THRESHOLD BELOW-PERIODS DURATION THRESHOLD` — all six required for full trim.
