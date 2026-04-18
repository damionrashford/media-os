---
name: ffmpeg-audio-fx
description: >
  Creative and restoration audio effects with ffmpeg: chorus, flanger, aphaser, tremolo, vibrato, aecho, crystalizer, adecorrelate, adeclick, adeclip, apsyclip, asoftclip, speechnorm, dialoguenhance, adynamicequalizer, adynamicsmooth, afreqshift, aphaseshift, asupercut, asuperpass, asuperstop, atilt, afftfilt, bandpass, bandreject, biquad, allpass, ladspa, lv2. Use when the user asks to add echo/chorus/flanger, create psychedelic audio effects, enhance dialogue, de-click vinyl rips, soft-clip audio, apply LADSPA or LV2 plugins, or shift frequency.
argument-hint: "[effect] [input]"
---

# ffmpeg Audio FX

**Context:** $ARGUMENTS

Creative and restoration audio effects. `-af` chain syntax. Every recipe below is verified against the FFmpeg filters doc. For basic gain / EQ / loudnorm / tempo see the sibling `ffmpeg-audio-filter` skill — this one is modulation, delay, restoration, true-peak limiting, dynamic EQ, spectral domain, and plugin hosts.

## Quick start

- **Add echo** — Step 2 (Delay group), recipe `aecho`.
- **Chorus / flanger / phaser / tremolo / vibrato** — Step 2 (Modulation group).
- **Normalize speech for a podcast** — Step 2 (Dynamics group), recipe `speechnorm`.
- **Rescue vinyl rip** — Step 2 (Restoration group), chain `adeclick` → `adeclip`.
- **Broadcast-safe true-peak limit** — `apsyclip` (Dynamics group).
- **Host a LADSPA or LV2 plugin** — Step 2 (Plugin group).
- **Shift frequencies (not pitch)** — `afreqshift` (Filter-curve group).

## When to use

- Music production: add modulation (chorus/flanger/phaser), widen a mono source, add shimmer (crystalizer), analog-warm limiting (asoftclip).
- Post / dialogue: enhance voice in a 5.1 mix (dialoguenhance), level an uneven interview (speechnorm), duck resonant frequencies (adynamicequalizer).
- Restoration: vinyl / shellac / cassette rips (adeclick + adeclip + asupercut rumble filter), decorrelate stereo (adecorrelate).
- Broadcast / streaming: psychoacoustic true-peak limiter (apsyclip) as the final stage before dithering to s16.
- DSP / research: arbitrary biquads, spectral-domain manipulation (afftfilt), host third-party plugins via LADSPA / LV2.

## Step 1 — Classify the effect

Group the request into one of five buckets before picking a filter:

| Group | Filters | Use when |
|---|---|---|
| **Modulation** | `chorus`, `flanger`, `aphaser`, `tremolo`, `vibrato` | Add movement / wobble / thickness. |
| **Delay** | `aecho` | Echo / slap-back / doubler. |
| **Dynamics** | `speechnorm`, `dialoguenhance`, `adynamicequalizer`, `adynamicsmooth`, `asoftclip`, `apsyclip`, `crystalizer` | Level, duck, saturate, limit, sharpen transients. |
| **Restoration** | `adeclick`, `adeclip`, `adecorrelate`, `asupercut` | Vinyl pops, clipped peaks, stereo smear, subsonic rumble. |
| **Filter-curve / spectral** | `bandpass`, `bandreject`, `biquad`, `allpass`, `asuperpass`, `asuperstop`, `atilt`, `afreqshift`, `aphaseshift`, `afftfilt` | Surgical EQ, high-order filters, frequency shifting (not pitch), arbitrary spectral math. |
| **Plugin host** | `ladspa`, `lv2` | Load an external DSP plugin. Requires build flags. |

## Step 2 — Build the filter chain

Copy the exact recipe. Parameters that look arbitrary (e.g. `0.8:0.9:1000:0.3`) are positional and mismatched counts produce cryptic errors.

### Modulation

```bash
# Echo (doubler / slap-back) — delays are MILLISECONDS
ffmpeg -i in.wav -af "aecho=0.8:0.9:1000:0.3" out.wav
# Chorus (6 positional args: in-gain:out-gain:delays-ms:decays:speeds:depths)
ffmpeg -i in.wav -af "chorus=0.7:0.9:55:0.4:0.25:2" out.wav
# Flanger (jet-swoosh; depth is ms range of the LFO)
ffmpeg -i in.wav -af "flanger=delay=5:depth=2:speed=0.5" out.wav
# Phaser (type=t triangle, s sine, n analog noise)
ffmpeg -i in.wav -af "aphaser=type=t:speed=2" out.wav
# Tremolo (volume modulation)
ffmpeg -i in.wav -af "tremolo=f=5:d=0.5" out.wav
# Vibrato (pitch modulation via delay)
ffmpeg -i in.wav -af "vibrato=f=7:d=0.5" out.wav
```

### Dynamics

```bash
# Intelligent speech leveler — better than dynaudnorm for voice-only
ffmpeg -i podcast.wav -af "speechnorm=e=12.5:r=0.0001:l=1" out.wav
# Dialogue enhance (boosts the center channel voice band, REQUIRES 5.1+)
ffmpeg -i film.wav -af "dialoguenhance" out.wav
# Dynamic EQ — duck resonant 1 kHz band by 5 dB when it gets loud
ffmpeg -i in.wav -af "adynamicequalizer=bandwidth=300:dfrequency=1000:direction=below:mode=cut:makeup=5" out.wav
# Crystalizer (add harmonics / transient sharpening) — intensity > 3 = artificial
ffmpeg -i in.wav -af "crystalizer=i=2" out.wav
# Soft-clip (warm limiter; type= hard / tanh / atan / cubic / exp / alg / quintic / sin / erf)
ffmpeg -i in.wav -af "asoftclip=type=tanh" out.wav
# Psychoacoustic true-peak limiter (THE recommended broadcast limiter)
ffmpeg -i in.wav -af "apsyclip=level_in=1:level_out=1:clip=0.9" out.wav
```

### Restoration

```bash
# Vinyl de-click (arorder 6-8 for vinyl; method a=autoregressive)
ffmpeg -i vinyl.wav -af "adeclick=window=55:overlap=75:arorder=8:threshold=2:burst=2" out.wav
# De-clip (threshold 10+ for obvious clipping; hsize=1000 history size)
ffmpeg -i clipped.wav -af "adeclip=window=55:overlap=75:arorder=8:threshold=10:hsize=1000:method=a" out.wav
# Subsonic rumble kill (sharp 20 Hz high-pass, 20th order Butterworth)
ffmpeg -i in.wav -af "asupercut=cutoff=20:order=20" out.wav
# Stereo decorrelation (adds a tiny inter-channel delay)
ffmpeg -i mono_ish.wav -af "adecorrelate" out.wav
```

### Filter-curve / spectral

```bash
# Band-pass for voice intelligibility (Q=2 around 1 kHz)
ffmpeg -i in.wav -af "bandpass=f=1000:width_type=q:w=2" out.wav
# Frequency shift 50 Hz (NOT pitch shift — inharmonic, metallic)
ffmpeg -i in.wav -af "afreqshift=shift=50" out.wav
# Spectral tilt (lean EQ, +/- dB per octave)
ffmpeg -i in.wav -af "atilt=freq=1000:slope=-3" out.wav
# Arbitrary biquad IIR (coefficients b0,b1,b2,a0,a1,a2)
ffmpeg -i in.wav -af "biquad=b0=0.5:b1=0:b2=0.5:a0=1:a1=0:a2=0" out.wav
# FFT filter — real/imag expressions in spectral domain (null example)
ffmpeg -i in.wav -af "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)'" out.wav
```

### Plugin host

```bash
# LADSPA: file=libname (no .so), plugin=label, c=key=val,...
ffmpeg -i in.wav -af "ladspa=file=cmt:plugin=amp_stereo:c=gain=10" out.wav
# LV2: p=plugin URI, c=key=val,...
ffmpeg -i in.wav -af "lv2=p=http://calf.sourceforge.net/plugins/Reverb" out.wav
```

## Step 3 — Run

Encode to the target codec in the same invocation:

```bash
ffmpeg -i in.wav -af "speechnorm=e=12.5:r=0.0001:l=1,apsyclip=clip=0.95" \
       -c:a libopus -b:a 96k out.opus
```

For video input, pass the video through untouched with `-c:v copy`:

```bash
ffmpeg -i in.mp4 -af "dialoguenhance,speechnorm=e=6.25" \
       -c:v copy -c:a aac -b:a 192k out.mp4
```

## Step 4 — A/B verify

Always listen to the result against the source. Use the `ffmpeg-playback` skill's `ffplay` recipes or diff loudness:

```bash
ffmpeg -i in.wav -af "ebur128=peak=true" -f null - 2>&1 | tail -20
ffmpeg -i out.wav -af "ebur128=peak=true" -f null - 2>&1 | tail -20
```

Target: integrated loudness inside spec (podcast -16 LUFS, streaming -14 LUFS, broadcast -23 LUFS), true peak ≤ -1 dBTP.

## Available scripts

- **`scripts/afx.py`** — stdlib argparse front-end with subcommands for every recipe above. `--dry-run` prints the ffmpeg command without running it. `--verbose` shows the full argv.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/afx.py echo --input in.wav --output out.wav --delay-ms 600 --decay 0.4
uv run ${CLAUDE_SKILL_DIR}/scripts/afx.py deckick --input vinyl.wav --output clean.wav
uv run ${CLAUDE_SKILL_DIR}/scripts/afx.py limit --input master.wav --output final.wav --method psy
```

## Reference docs

Read [`references/filters.md`](references/filters.md) for per-filter option tables, effect-type taxonomy, LADSPA/LV2 plugin discovery, and production recipe book (vinyl chain, voice chain, radio master chain).

## Gotchas

- `aecho` delays are **milliseconds** in a pipe-separated string: `"1000|1500|2000"` means three echoes at 1 s / 1.5 s / 2 s. Decays list must match the delay count.
- `chorus` positional args are `in-gain:out-gain:delays-ms:decays:speeds:depths`. Mismatched list counts produce a silent error / empty output.
- `flanger` `depth` is the LFO oscillation range in **milliseconds** — typical 0.5–10. Higher sounds like pitch-bend seasickness.
- `aphaser` `type=t` triangle LFO, `s` sine, `n` analog noise — noise sounds vintage / broken.
- `tremolo` modulates **volume**, `vibrato` modulates **pitch** (via delay). They are easy to confuse; pick the one that matches what "tremolo" means on your instrument.
- `adeclick` `arorder` should be 6–8 for vinyl; higher = more CPU and diminishing returns. `threshold` 2 is a good starting point.
- `adeclip` needs `threshold=10` or more for obviously clipped material. Lower thresholds miss hard clips entirely.
- `crystalizer` intensity > 3 gets fatiguing fast. Most mastering uses `i=1` to `i=2`.
- `apsyclip` is **the** recommended true-peak limiter for broadcast — psychoacoustic masking hides artifacts better than plain `alimiter`. Set `clip=0.9` (about -0.9 dBTP) to stay under -1 dBTP.
- `speechnorm` is better than `dynaudnorm` for voice-only material (podcasts, audiobooks). For music or mixed content use `loudnorm` instead.
- `dialoguenhance` operates on stereo per current docs, but the real-world gain is on 5.1/7.1 where it targets the center channel. On stereo it will run but the effect is subtle.
- `adynamicequalizer` supports both `mode=cut` (duck a resonance) and `mode=boost` (lift under a threshold). `direction=below` or `above` chooses whether it acts on quiet or loud material.
- `biquad` is the generic bottom-level IIR. Prefer `highpass`, `lowpass`, `bandpass`, `allpass`, `equalizer`, `treble`, `bass` unless you genuinely need raw coefficients.
- `afftfilt` takes two expressions (`real` and `imag`) — advanced spectral domain. `re`, `im`, `bin_h`, `mag`, `pha` are available symbols.
- `afreqshift` is frequency shift (single-sideband), not pitch shift. It destroys harmonic relationships. For pitch shift use `rubberband` or `asetrate+atempo`.
- `asupercut` / `asuperpass` / `asuperstop` are high-order Butterworth (up to 20th order) — use when a regular `highpass`/`bandpass` rolloff isn't steep enough.
- `atilt` is linear-slope spectral tilt in dB/octave. Useful for pink-noise-style mastering adjustments.
- LADSPA requires ffmpeg built with `--enable-ladspa`. Plugin `.so` files live in `/usr/lib/ladspa` (or set `LADSPA_PATH`). Invoke with `file=cmt` (not `file=cmt.so`) and `plugin=<label>`.
- LV2 requires ffmpeg built with `--enable-lv2` (lilv). Plugins live in `/usr/lib/lv2` (or set `LV2_PATH`). Invoke with `p=<plugin URI>`. Calf's massive library is discoverable with `lv2ls | grep -i calf`.
- After heavy processing always re-dither if going back to integer PCM: `-af "...,aformat=sample_fmts=s16,aresample=44100:dither_method=triangular"`.
- Never chain two strong limiters back-to-back — the second pumps against the first's reduction and creates distortion artifacts.

## Examples

### Example 1: Podcast voice chain

Input: noisy lavalier recording, `interview.wav`, needs to land at -16 LUFS for podcast.

```bash
ffmpeg -i interview.wav \
  -af "asupercut=cutoff=80:order=10,\
speechnorm=e=12.5:r=0.0001:l=1,\
adynamicequalizer=dfrequency=5000:mode=cut:bandwidth=800:makeup=4,\
apsyclip=level_out=0.9" \
  -c:a libopus -b:a 96k episode.opus
```

High-pass kills rumble → speech leveler brings quiet/loud to parity → dynamic EQ tames sibilant 5 kHz resonance → psyclip catches stray peaks.

### Example 2: Vinyl restoration

Input: `lp_side_a.flac` from a USB turntable, clicks and a couple clipped peaks.

```bash
ffmpeg -i lp_side_a.flac \
  -af "adeclick=arorder=8:threshold=2,\
adeclip=threshold=10:method=a,\
asupercut=cutoff=30:order=12,\
aformat=sample_fmts=s16,aresample=44100:dither_method=triangular" \
  restored.flac
```

### Example 3: Shimmer guitar

Chorus + crystalizer for a clean arpeggio:

```bash
ffmpeg -i guitar.wav -af "chorus=0.6:0.9:40|60:0.3|0.4:0.2|0.25:1.5|2.0,crystalizer=i=1" shimmer.wav
```

### Example 4: Host a Calf LV2 reverb

```bash
ffmpeg -i dry.wav -af "lv2=p=http://calf.sourceforge.net/plugins/Reverb:c=room_size=5|decay_time=3" wet.wav
```

## Troubleshooting

### Error: `Option chorus not found`

Cause: ffmpeg build missing the filter — rare, but Alpine / minimal builds sometimes strip creative filters.
Solution: `ffmpeg -filters | grep chorus`. If absent, install the full `ffmpeg` package (Debian/Ubuntu) or rebuild with `--enable-filter=chorus`.

### Error: `Error while parsing the string for 'aecho'`

Cause: mismatched delay/decay counts — e.g. two delays `1000|1500` with only one decay `0.3`.
Solution: counts must match. `aecho=0.8:0.9:1000|1500:0.3|0.4`.

### Error: LADSPA/LV2 `No such filter`

Cause: ffmpeg was built without `--enable-ladspa` / `--enable-lv2`.
Solution: `ffmpeg -buildconf | grep -E 'ladspa|lv2'`. On macOS via Homebrew: `brew install ffmpeg` ships with ladspa/lv2 when available; on minimal Docker images you usually must rebuild.

### Error: plugin loads but parameters silently ignored

Cause: wrong parameter name for the plugin (LADSPA/LV2 parameter names are plugin-specific).
Solution: `listplugins` for LADSPA, `lv2ls` + `lv2info <URI>` for LV2 — copy the exact control-port name.

### Symptom: `dialoguenhance` has no audible effect

Cause: running on mono or stereo source. The algorithm targets a dialogue-band extraction that is most effective on multichannel content with real separation.
Solution: for stereo, try `bandpass=f=2500:w=1200` + a light boost (+2 dB) instead, or upmix first with `surround`.

### Symptom: distortion after limiter

Cause: chaining two strong dynamics stages (e.g. `speechnorm l=1` into `apsyclip level_in=2`) pumps against itself.
Solution: drop limiter input gain to 1.0, or remove one stage. Rule: one make-up-gain stage, one peak-catching stage — never both loud.
