# SoX Reference

Deep-dive companion to `SKILL.md`. Load when you need effect parameters, sample-format minutiae, dither behavior, or a battle-tested recipe.

## 1. File options vs effects — the core mental model

SoX has two distinct argument categories that are constantly confused:

| Kind | Where it goes | Scope | Examples |
|---|---|---|---|
| **Global option** | Before any filename | Whole command | `--norm`, `-D` (no dither), `-S` (show progress), `-q` (quiet), `-V` (verbose level) |
| **File option** | Immediately before the filename it modifies | That one file only | `-r RATE`, `-b BITS`, `-c CHAN`, `-e ENCODING`, `-t TYPE`, `-v VOL`, `-L`/`-B` (endian), `--endian`, `-U`/`-A`/`-s`/`-u` (encoding shortcuts) |
| **Effect** | After the output filename | Applied left-to-right in the chain | `trim`, `pad`, `gain`, `norm` (effect form), `fade`, `tempo`, `pitch`, `speed`, `reverse`, `reverb`, `echo`, `echos`, `chorus`, `flanger`, `phaser`, `tremolo`, `compand`, `mcompand`, `silence`, `noiseprof`, `noisered`, `synth`, `remix`, `channels`, `rate`, `dither`, `stats`, `stat` |

**Canonical form:** `sox [global] [file-opts] infile [file-opts] outfile [effect [args] ...]`

Multi-input: `sox [fopts] in1 [fopts] in2 [fopts] out [effects]` — inputs are concatenated by default; `-m` sums them.

## 2. Effect catalog

### 2.1 Time / length

- `trim START [DURATION]` — START and DURATION accept `S` seconds, `S.sss` fractional, `HH:MM:SS`, or samples suffixed with `s`. Negative START trims from end.
- `pad HEAD TAIL` — insert silence head / tail in seconds.
- `reverse` — reverse samples in time (loads whole file — big files need memory).
- `repeat N` — repeat N times.
- `splice POSITION [EXCESS [LEEWAY]]` — crossfade-join at position; used with multi-input.

### 2.2 Rate / pitch / speed

- `tempo [-q|-m|-s|-l] FACTOR [SEGMENT [SEARCH [OVERLAP]]]` — WSOLA-style tempo change, pitch preserved. Flags: `-q` quick, `-m` music default, `-s` speech, `-l` linear (best for drums).
- `pitch [-q] CENTS [SEGMENT [SEARCH [OVERLAP]]]` — pitch shift in cents (100 cents = 1 semitone); tempo preserved.
- `speed FACTOR[c]` — varispeed: pitch AND tempo scale together. Append `c` to interpret FACTOR as cents.
- `rate [-q|-l|-m|-h|-v] [-s|-i|-I|-L] [-a] [-b 0-99.7] [-p PHASE] RATE` — explicit sample-rate conversion with filter-quality control. `-v` (very high) is default for SoX ≥ 14.3.

### 2.3 Level

- `gain [-e|-B|-b|-r|-n] [-l|-h] [dB]` — flexible gain: `-n` normalize to 0 dBFS, `-B` balance gain, `-e` equalize channels.
- `norm [dBFS]` — effect-form normalize (equivalent to `gain -n`).
- `vol GAIN [TYPE [LIMITERGAIN]]` — volume with optional limiter. TYPE = `amplitude` (default) / `power` / `dB`.
- `dcshift SHIFT [LIMITERGAIN]` — DC offset correction.
- `loudness [GAIN [REFERENCE]]` — ISO 226 equal-loudness compensation (NOT EBU R128 — see §7).

### 2.4 Dynamics

- `compand ATTACK,DECAY SOFT-KNEE:IN-DB1,OUT-DB1,IN-DB2,OUT-DB2,... [GAIN [INITIAL-VOLUME [DELAY]]]`
  - Voice-podcast starter: `compand 0.3,1 6:-70,-60,-20 -5 -90 0.2`.
  - Hard limiter: `compand 0.0,0.1 -90,-90,-20,-15 0 0 0.1`.
- `mcompand '"ATTACK,DECAY SOFT-KNEE:...," FREQ'` — multi-band compand (quoted band strings separated by frequency Hz crossovers).

### 2.5 Frequency shaping (use `ffmpeg` or LADSPA for surgical EQ; SoX has the basics)

- `bass GAIN [FREQ [WIDTH[w|h|k|o|q]]]` — shelf bass.
- `treble GAIN [FREQ [WIDTH]]` — shelf treble.
- `equalizer FREQ WIDTH[q|o|h|k] GAIN` — peaking EQ.
- `bandpass [-c] FREQ WIDTH` — bandpass.
- `bandreject FREQ WIDTH` — notch.
- `highpass|lowpass [-1|-2] FREQ [WIDTH]` — Butterworth.
- `allpass FREQ WIDTH` — phase filter.
- `sinc [-a ATT] [-n TAPS] [-b BETA] [-p PHASE] [-M|-I|-L] [-t TB] [FREQ1][-FREQ2]` — arbitrary-cutoff FIR.

### 2.6 Reverb / modulation

- `reverb [-w] [REVERBERANCE [HF-DAMPING [ROOM-SCALE [STEREO-DEPTH [PRE-DELAY [WET-GAIN]]]]]]` — all defaults 50 except pre-delay 0, wet-gain 0.
- `echo GAIN-IN GAIN-OUT DELAY DECAY ...` — simple echo with delay/decay pairs.
- `echos` — sequential echoes.
- `chorus GAIN-IN GAIN-OUT DELAY DECAY SPEED DEPTH -s|-t` — chorus (one or more voices).
- `flanger [DELAY [DEPTH [REGEN [WIDTH [SPEED [SHAPE [PHASE [INTERP]]]]]]]]`.
- `phaser GAIN-IN GAIN-OUT DELAY DECAY SPEED -s|-t`.
- `tremolo SPEED [DEPTH]` — amplitude modulation.

### 2.7 Silence / noise

- `silence [-l] ABOVE-PERIODS DURATION THRESHOLD[d|%] [BELOW-PERIODS DURATION THRESHOLD[d|%]]`
  - ABOVE-PERIODS > 0 trims leading silence.
  - BELOW-PERIODS = -1 trims ALL silence (including internal).
  - Typical podcast trim: `silence 1 0.1 1% -1 0.5 1%`.
  - Threshold can be percent (`1%`) or dBFS (`-40d`).
- `noiseprof [PROFILE-FILE]` — writes text profile (stdout if omitted). Run against a noise-only segment (use `trim` before it in the chain).
- `noisered [PROFILE-FILE [AMOUNT]]` — spectral subtraction. AMOUNT 0.0–1.0, default 0.5. Start at 0.21; raise cautiously.

### 2.8 Channels / mix

- `channels N` — simple mono / stereo converter (averaging / duplicating).
- `remix [-m|-a] OUT1 OUT2 ...` — arbitrary channel routing with `1,2` = sum ch1+ch2.
- `mixer` (deprecated — use `remix`).
- `swapchannels` — swap L/R (2-ch only).
- `oops` — out-of-phase stereo (vocal suppression trick).

### 2.9 Synthesis

- `synth [LENGTH] TYPE [MIX] [FREQ[-FREQ2]] [OFF] [PHASE] [p1 [p2 [p3]]]`
  - TYPE: `sine`, `square`, `triangle`, `sawtooth`, `trapezium`, `exp`, `[white|pink|brown|tpdf]noise`, `pluck`.
  - LENGTH omitted = infinite (use with `trim` to bound).
  - MIX: `create` (default), `mix`, `amod`, `fmod` — compose against prior stream.
  - Frequency range `A-B` = linear sweep.

Examples:
- 1 kHz reference tone, 5 s, -20 dBFS: `sox -n ref.wav synth 5 sine 1000 vol -20dB`
- Pink noise 10 s: `sox -n pink.wav synth 10 pinknoise`
- 20 Hz–20 kHz log sweep: `sox -n sweep.wav synth 30 sine 20-20000 vol -6dB`

### 2.10 Analysis

- `stats` — prints DC offset, Min/Max level, Pk lev dB, RMS lev dB, RMS Pk dB, RMS Tr dB, Crest factor, Flat factor, Pk count, Bit-depth. Use with `-n` null-output: `sox in.wav -n stats`.
- `stat` — older SoX stat block; more verbose but less structured. `sox in.wav -n stat`.
- `spectrogram [-x WIDTH -y HEIGHT -z RANGE -o FILE.png]` — dumps PNG.

## 3. Sample format & encoding

### 3.1 Encoding flags (`-e`)

- `signed-integer` / `s` — default for 16/24/32-bit PCM.
- `unsigned-integer` / `u` — rare (8-bit WAV).
- `floating-point` / `f` — 32/64-bit float WAV.
- `mu-law` / `u-law`, `a-law` — telephony.
- `ima-adpcm`, `ms-adpcm`, `gsm-full-rate` — compressed PCM variants.

### 3.2 Bit depth (`-b`)

Common: 8, 16, 24, 32. 32 with `-e floating-point` = 32-bit float. Reducing bit depth invokes dither by default.

### 3.3 Headerless / raw files

You must specify **everything** SoX cannot infer:
```bash
sox -t raw -r 48000 -b 16 -c 1 -e signed-integer --endian little input.pcm out.wav
```

### 3.4 Container / codec types (`-t`)

`wav`, `aiff`, `au`, `flac`, `ogg`, `raw`, `sph`, `voc`, `caf`, `w64`. MP3 requires `libmad`/`libmp3lame` at compile time — usually absent on Homebrew.

## 4. Dither

Bit-depth reduction triggers TPDF (triangular probability density function) dither by default. Controls:

- **`-D` (global)** — disable dither entirely. Place before any filename: `sox -D in.wav -b 16 out.wav`.
- **`dither` effect** — explicit. Syntax: `dither [-S|-s|-f FILTER] [-a] [-p PRECISION]`. FILTER: `lipshitz`, `f-weighted`, `modified-e-weighted`, `improved-e-weighted`, `gesemann`, `shibata`, `low-shibata`, `high-shibata`. `-a` auto — only dither if reducing bits.

Best practice:
- For 24 → 16 conversion destined for consumer playback: keep default TPDF or use `dither -s` (noise-shaped).
- For intermediate files in a chain where further processing will happen: `-D` to avoid stacking dither noise.

## 5. Noise-reduction best practices

Two-pass `noiseprof` / `noisered` is SoX's killer feature for stationary noise.

1. **Profile from pure noise only.** At least 0.5–1.0 s. Use `trim` to point at a silence gap before the noise reducer runs — or profile from a separate "room tone" file recorded deliberately.
2. **Same sample rate and channel count** for profile file and target file. Re-profile if resampled.
3. **Amount tuning:** start at 0.21, ear-test. Go up by 0.05 increments. Above 0.35 you will hear "underwater" / metallic artifacts on voice.
4. **Don't double-denoise.** Running noisered twice compounds artifacts.
5. **Non-stationary noise** (clicks, pops, traffic bursts) — use `ffmpeg adeclick` / `adeclip` / `arnndn`, or LADSPA `noise_suppressor_for_voice`, not SoX.
6. **Preserve transients** by lowering sensitivity (0.15) even if some hiss remains — subsequent downstream compression/limiting will re-expose less noise if sensitivity was conservative.
7. **Edit profile manually:** it's plain text. Each line = one frequency bin amplitude. You can trim HF bins if you want to preserve air.

## 6. Synth waveform reference

| Kind | Use |
|---|---|
| `sine` | Test tones, reference 440 / 1 kHz |
| `square` | Harsh FM carriers, 8-bit game audio |
| `triangle` | Softer carrier, harmonic content |
| `sawtooth` | Synth bass / lead emulation |
| `trapezium` | Between square & triangle |
| `exp` | Exponential decay envelope source |
| `pinknoise` | Room-response measurement, masking |
| `whitenoise` | ADC calibration, dither source |
| `brownnoise` | Rumble simulation, sleep-aid |
| `tpdfnoise` | Dither-compatible noise |
| `pluck` | Karplus-Strong string emulation |

Bounded-duration tonal clip: `sox -n out.wav synth 2 sine 440 vol -12dB fade 0.01 2 0.01`.

## 7. What SoX does NOT do well — reach for other tools

- **EBU R128 / LUFS loudness normalization** — use `ffmpeg -af loudnorm` or `ffmpeg-normalize`. `sox --norm` is peak-only.
- **Stem separation** — use Demucs / Spleeter.
- **Speech-to-text** — use Whisper.
- **MP3 / AAC encoding** — usually route through `ffmpeg` or `lame`.
- **Complex multi-channel routing & panning** — `ffmpeg pan` filter syntax is easier.
- **Real-time audio graphs** — SoX is batch-only; use JACK / PipeWire / `ffmpeg -re`.
- **Spectral repair (clicks, hum removal at specific freqs)** — iZotope RX, or `ffmpeg afftfilt`.
- **Convolution reverb / IR loading** — LADSPA/LV2 (`zita-convolver`), or `ffmpeg afir`.

## 8. Recipe book

### 8.1 Vinyl rip cleanup

```bash
# 1) profile the lead-in groove (assume first 0.8s = quiet surface noise)
sox rip.wav -n trim 0 0.8 noiseprof surface.prof
# 2) full chain: denoise, declick-via-soft-limit, EQ air, normalize, dither to 16-bit
sox rip.wav -D rip_clean.wav \
  noisered surface.prof 0.18 \
  highpass 30 \
  equalizer 10000 0.7q 2 \
  compand 0.01,0.2 -50,-50,-20,-15 -2 -90 0.02 \
  gain -n -1
# 3) optional: dither explicitly to 16-bit target
sox rip_clean.wav -b 16 rip_master.wav dither -s
```

### 8.2 Podcast episode polish (single-mic interview)

```bash
sox raw.wav -n trim 0 1 noiseprof noise.prof
sox raw.wav episode.wav \
  noisered noise.prof 0.21 \
  highpass 80 \
  equalizer 200 0.6q -2 \
  equalizer 3500 0.8q 2 \
  compand 0.3,1 6:-70,-60,-20 -5 -90 0.2 \
  gain -n -1 \
  silence 1 0.1 1% -1 0.5 1% \
  fade 0.05 -0 0.2
```

### 8.3 Per-episode silence trim (batch)

```bash
for f in ep*.wav; do
  sox "$f" "out/${f}" silence 1 0.1 1% -1 0.5 1%
done
```

### 8.4 Dynamic-range compression starter presets

```bash
# Gentle podcast voice
compand 0.3,1 6:-70,-60,-20 -5 -90 0.2

# Aggressive broadcast voice
compand 0.01,0.20 -90,-90,-70,-70,-45,-15,-10,-10,0,-5 -3 -90 0.1

# Transparent music bus
compand 0.1,0.3 -80,-80,-40,-30,-15,-10 -2 -90 0.05
```

### 8.5 Measurement: peak / RMS / DC offset report

```bash
sox in.wav -n stats 2>&1 | tee in.stats.txt
```

Fields:
- `DC offset` — should be < 0.003; larger = microphone/ADC bias.
- `Pk lev dB` — peak. Target ≤ -1.0 for broadcast.
- `RMS lev dB` — average energy. -20 for music, -18 for speech.
- `Crest factor` — peak/RMS ratio; < 10 = heavily compressed.
- `Bit-depth` — effective resolution; 16/16 = fully-used 16-bit.

### 8.6 A/B match sample rates before mixing

```bash
sox a.wav -r 48000 a_48.wav rate -v
sox b.wav -r 48000 b_48.wav rate -v
sox -m a_48.wav b_48.wav mixed.wav gain -n -1
```

### 8.7 Build a 1 kHz / -20 dBFS line-up tone (broadcast slate)

```bash
sox -n -r 48000 -b 24 lineup.wav synth 30 sine 1000 vol -20dB
```

### 8.8 Concatenate with crossfade via splice

```bash
# length of a.wav
SOX_A_DUR=$(sox --i -D a.wav)
sox a.wav b.wav joined.wav splice ${SOX_A_DUR},0.5,0.5
```

## 9. Troubleshooting quick table

| Symptom | Likely cause | Fix |
|---|---|---|
| `no handler for file extension` | Format not compiled in (usually MP3) | Transcode via ffmpeg/lame |
| `Input files must have the same sample-rate` | Multi-input mismatch | Resample each with `-r RATE` before mixing |
| Clicks at chain boundary | Abrupt transition; no fade | Append `fade 0.005 -0 0.005` |
| Clipping after chain | Stacked gain | Append `gain -n -1` |
| "Underwater" voice after denoise | Sensitivity too high | Drop to 0.15 |
| Wrong pitch after `speed` | `speed` is varispeed | Use `tempo` instead for pitch-preserved timing |
| Trim returns empty file | START past EOF or `trim 0 0` | Check `sox --i -D in.wav` for duration |
