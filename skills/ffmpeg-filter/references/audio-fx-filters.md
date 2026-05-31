# ffmpeg-audio-fx — filter reference

Per-filter option tables, effect taxonomy, plugin host discovery, and production recipe book. Every option table below is transcribed from the official ffmpeg-filters documentation.

## Effect taxonomy

| Group | Filters | Mental model |
|---|---|---|
| Modulation | `chorus`, `flanger`, `aphaser`, `tremolo`, `vibrato`, `apulsator` | LFO drives gain/delay/pitch to add movement. |
| Delay (single-tap / feedback) | `aecho`, `adelay`, `afwtdn` | Echoes of the signal at fixed offsets. |
| Dynamics | `speechnorm`, `dialoguenhance`, `adynamicequalizer`, `adynamicsmooth`, `crystalizer`, `asoftclip`, `apsyclip`, `aexciter` | Volume / harmonic / transient reshaping. |
| Restoration | `adeclick`, `adeclip`, `adecorrelate`, `asupercut` (rumble), `afftdn`, `anlmdn`, `arnndn` | Remove artifacts, noise, clipping. |
| Filter-curve / spectral | `bandpass`, `bandreject`, `biquad`, `allpass`, `highpass`, `lowpass`, `asupercut`, `asuperpass`, `asuperstop`, `atilt`, `afreqshift`, `aphaseshift`, `afftfilt` | Frequency-selective filtering, spectral math. |
| Plugin host | `ladspa`, `lv2` | Load external DSP. |

---

## Modulation

### chorus — `chorus=in-gain:out-gain:delays:decays:speeds:depths`

All six positional args required. `delays` and later lists are pipe-separated; counts must match across all four oscillator lists.

| Option | Type | Typical | Notes |
|---|---|---|---|
| `in_gain` | float 0–1 | 0.4–0.7 | Pre-gain into chorus. |
| `out_gain` | float 0–1 | 0.7–0.9 | Post-gain. |
| `delays` | list of ms | 40–90 | Base delay per voice. |
| `decays` | list 0–1 | 0.3–0.5 | Per-voice feedback. |
| `speeds` | list Hz | 0.15–0.3 | Per-voice LFO rate. |
| `depths` | list ms | 1–3 | Per-voice LFO swing. |

### flanger — `flanger=delay=5:depth=2:speed=0.5:...`

| Option | Range | Default | Notes |
|---|---|---|---|
| `delay` | 0–30 ms | 0 | Base delay. |
| `depth` | 0–10 ms | 2 | LFO swing. |
| `regen` | -95–95 % | 0 | Feedback — higher = more whoosh. |
| `width` | 0–100 % | 71 | Dry/wet. |
| `speed` | 0.1–10 Hz | 0.5 | LFO rate. |
| `shape` | `sinusoidal` / `triangular` | sinusoidal | LFO wave. |
| `phase` | 0–100 % | 25 | Stereo phase offset. |
| `interp` | `linear` / `quadratic` | linear | Interpolation. |

### aphaser — `aphaser=type=t:speed=2:...`

| Option | Range | Default | Notes |
|---|---|---|---|
| `in_gain` | 0–1 | 0.4 | Input gain. |
| `out_gain` | 0–1e9 | 0.74 | Output gain. |
| `delay` | 0–5 ms | 3 | Base delay. |
| `decay` | 0–0.99 | 0.4 | Feedback. |
| `speed` | 0.1–2 Hz | 0.5 | LFO rate. |
| `type` | `t` / `s` | t | Triangle / sine LFO. |

(Docs also reference an analog-noise-sounding variant; `t` and `s` are always safe.)

### tremolo — `tremolo=f=5:d=0.5`

| Option | Range | Default | Notes |
|---|---|---|---|
| `f` | 0.1–20000 Hz | 5 | Modulation Hz (keep under 20 for audibility). |
| `d` | 0–1 | 0.5 | Depth — fraction of volume modulated. |

### vibrato — `vibrato=f=7:d=0.5`

Same options as tremolo, but modulates **pitch** (via microsecond-level delay modulation) rather than amplitude.

### apulsator — autopanner / pulsator

| Option | Default | Notes |
|---|---|---|
| `level_in`, `level_out` | 1 | I/O gain. |
| `mode` | sine | `sine`, `triangle`, `square`, `sawup`, `sawdown`. |
| `amount` | 1 | Intensity 0–1. |
| `offset_l`, `offset_r` | 0, 0.5 | Left / right LFO phase offset (0.5 = autopanner). |
| `width` | 1 | Pulse width 0–2. |
| `timing` | hz | `bpm`, `ms`, or `hz`. |
| `bpm` / `ms` / `hz` | — | Rate depending on `timing`. |

---

## Delay

### aecho — `aecho=in-gain:out-gain:delays:decays`

Positional. `delays` and `decays` are **pipe-separated lists of equal length**. Units: delays in ms, decays as 0–1 scalars.

```
aecho=0.8:0.9:1000|1500|2000:0.3|0.2|0.1
```

| Arg | Range | Typical | Notes |
|---|---|---|---|
| in-gain | 0–1 | 0.8 | Input level into delay line. |
| out-gain | 0–1 | 0.88–0.95 | Dry+wet mix. |
| delays | 0–90000 ms | 60–2000 | Per-tap. |
| decays | 0–1 | 0.2–0.4 | Per-tap. |

---

## Dynamics

### speechnorm — intelligent speech leveler

| Option | Default | Notes |
|---|---|---|
| `peak, p` | 0.95 | Target peak 0–1. |
| `expansion, e` | 2 | Max expansion factor (>1 = expansion). Voice: 6–16. |
| `compression, c` | 2 | Max compression factor. |
| `threshold, t` | 0 | Below this level nothing happens. |
| `raise, r` | 0.001 | Speed of upward expansion. Podcast: 0.0001. |
| `fall, f` | 0.001 | Speed of downward compression. |
| `channels, h` | "all" | Channel selector. |
| `invert, i` | 0 | Invert raise/fall direction. |
| `link, l` | 0 | 1 = channels linked. |

### dialoguenhance

Enhances the dialogue component in stereo / multichannel audio. Documented options (current):

| Option | Default | Notes |
|---|---|---|
| `original` | 1 | Dry amount 0–1. |
| `enhance` | 1 | Dialogue emphasis 0–3. |
| `voice` | 2 | Voice band weighting 2–32. |

Most effective on 5.1/7.1 where there's a real center channel to boost.

### adynamicequalizer

| Option | Default | Notes |
|---|---|---|
| `threshold` | 0 | Trigger dB. |
| `dfrequency` | 1000 | Detection frequency Hz. |
| `dqfactor` | 1 | Detection Q. |
| `tfrequency` | 1000 | Target frequency Hz. |
| `tqfactor` | 1 | Target Q. |
| `attack` | 20 | ms. |
| `release` | 200 | ms. |
| `ratio` | 1 | Compression ratio. |
| `makeup` | 0 | dB. |
| `range` | 0 | Max dB movement. |
| `mode` | `cut` | `cut` (ducking) or `boost`. |
| `dftype` | `bandpass` | Detection filter. |
| `tftype` | `bell` | Target filter shape. |
| `direction` | `downward` | `downward` acts on loud; `upward` acts on quiet. |
| `auto` | `disabled` | Auto-makeup. |
| `precision` | `auto` | `float` / `double` / `auto`. |

### adynamicsmooth

Adaptive smoothing (stabilizes noisy control signals or adds subtle envelope following). Options: `sensitivity` (default 2), `basefreq` (default 22050).

### crystalizer — `crystalizer=i=2`

| Option | Default | Notes |
|---|---|---|
| `i` | 2 | Intensity (0–10, but >3 is fatiguing). |
| `c` | `true` | Clip protection. |

### asoftclip — `asoftclip=type=tanh`

| Option | Options | Notes |
|---|---|---|
| `type` | `hard`, `tanh`, `atan`, `cubic`, `exp`, `alg`, `quintic`, `sin`, `erf` | `tanh` = classic soft saturation. |
| `threshold` | default 1 | Soft threshold. |
| `output` | default 1 | Make-up gain. |
| `param` | — | Type-specific shape param. |
| `oversample` | 1 | 1/2/4× oversampling. |

### apsyclip — psychoacoustic true-peak limiter

| Option | Default | Notes |
|---|---|---|
| `level_in` | 1 | Pre-gain. |
| `level_out` | 1 | Post-gain. |
| `clip` | 1 | Clip threshold linear (0.9 ≈ -0.9 dBTP). |
| `diff` | 0 | Amount of diff signal. |
| `adaptive` | 0.5 | Masking strength 0–1. |
| `iterations` | 10 | Sample-iterative refinement. |
| `level` | 0 | 1 = auto-level compensation. |

Use as the final stage before dither.

---

## Restoration

### adeclick

| Option | Default | Notes |
|---|---|---|
| `window, w` | 55 | ms window. |
| `overlap, o` | 75 | % overlap. |
| `arorder, a` | 2 | AR model order — 6–8 for vinyl. |
| `threshold, t` | 2 | Detection threshold. |
| `burst, b` | 2 | Burst fusion ms. |
| `method, m` | `add` | `add` or `save` (passthrough). |

### adeclip

| Option | Default | Notes |
|---|---|---|
| `window, w` | 55 | ms. |
| `overlap, o` | 75 | %. |
| `arorder, a` | 8 | AR order. |
| `threshold, t` | 10 | Clipping detect threshold (keep ≥ 10). |
| `hsize, n` | 1000 | History size. |
| `method, m` | `a` | `a` (autoregressive) or `s` (save). |

### adecorrelate

Stereo decorrelation to add space to near-mono material. Options: `stages` (default 6), `seed` (random seed).

### asupercut / asuperpass / asuperstop

High-order (up to 20) Butterworth high-pass / band-pass / band-stop. Options:

| Option | Notes |
|---|---|
| `cutoff` | Hz (for asupercut). |
| `centerf` | Center Hz (for asuperpass/asuperstop). |
| `qfactor` | Q. |
| `order` | 3–20 (higher = steeper rolloff). |
| `level` | Gain. |

### atilt

Spectral tilt filter.

| Option | Default | Notes |
|---|---|---|
| `freq` | 10000 | Pivot Hz. |
| `slope` | 0 | dB/octave. |
| `width` | 1000 | Transition width. |
| `order` | 5 | Filter order 2–30. |
| `level` | 1 | Gain. |

---

## Filter-curve / spectral

### bandpass / bandreject / allpass / highpass / lowpass / biquad

Common options across these RBJ biquad-family filters:

| Option | Notes |
|---|---|
| `frequency, f` | Center/corner Hz. |
| `width_type, t` | `h` (Hz), `q` (Q factor), `o` (octaves), `s` (slope), `k` (kHz). |
| `width, w` | Width in the chosen unit. |
| `mix, m` | Dry/wet. |
| `channels, c` | Channel selector. |
| `normalize, n` | 1 = normalize magnitude at DC. |
| `transform, a` | `di`, `dii`, `tdi`, `tdii`, `latt`, `svf`, `zdf` — biquad transform. |
| `precision, r` | `s16`/`s32`/`f32`/`f64`/`auto`. |
| `blocksize, b` | 0 = off, else partition blocksize. |

`biquad` additionally accepts raw `b0:b1:b2:a0:a1:a2` coefficients.

### afreqshift / aphaseshift

Single-sideband frequency or phase shift. Options: `shift` (Hz for freq, 0–1 for phase), `level` (gain), `order` (filter order).

### afftfilt — arbitrary spectral expression

| Option | Default | Notes |
|---|---|---|
| `real` | re | Expression for real part. |
| `imag` | im | Expression for imag part. |
| `win_size` | 4096 | FFT size (power of 2). |
| `win_func` | `hann` | Window. |
| `overlap` | 0.75 | Window overlap. |

Symbols available in expressions: `sr` (sample rate), `b` (bin), `nb` (num bins), `ch`, `chs`, `pts`, `re`, `im`, `magnitude`, `phase`.

Example — low-pass at half Nyquist:

```
afftfilt=real='re*(b<nb/4)':imag='im*(b<nb/4)'
```

---

## Plugin hosts

### LADSPA — `ladspa=file=<lib>:plugin=<label>[:c=k=v|k=v]`

Requirements:
- ffmpeg built with `--enable-ladspa`.
- Plugins live in `/usr/lib/ladspa`, `/usr/local/lib/ladspa`, or `$LADSPA_PATH` (colon-separated).

Discovery:

```bash
# What does ffmpeg link?
ffmpeg -buildconf 2>&1 | grep -i ladspa
# List available plugins (from ladspa-sdk)
listplugins
# Describe one
analyseplugin /usr/lib/ladspa/cmt.so
# List control ports for a specific plugin
analyseplugin cmt.so amp_stereo
```

Popular free LADSPA libraries: `cmt` (Computer Music Toolkit), `swh-plugins` (Steve Harris), `tap-plugins` (Tom's Audio Plugins), `caps` (C* Audio Plugin Suite), `blop`.

### LV2 — `lv2=p=<URI>[:c=k=v|k=v]`

Requirements:
- ffmpeg built with `--enable-lv2` (depends on liblilv).
- Plugins live in `/usr/lib/lv2`, `~/.lv2`, or `$LV2_PATH`.

Discovery:

```bash
ffmpeg -buildconf 2>&1 | grep -i lv2
lv2ls                                      # list plugin URIs
lv2ls | grep -i calf                       # find Calf plugins
lv2info http://calf.sourceforge.net/plugins/Reverb   # describe + control ports
```

Popular LV2 libraries: Calf (`calfjackhost --list`), x42 (many broadcast tools), LSP, ZynAddSubFX, Dragonfly Reverb.

---

## Recipe book

### Vinyl restoration chain

```bash
ffmpeg -i lp_rip.flac -af "\
adeclick=window=55:overlap=75:arorder=8:threshold=2,\
adeclip=window=55:overlap=75:arorder=8:threshold=10:hsize=1000:method=a,\
afftdn=nr=12:nf=-35:tn=1,\
asupercut=cutoff=30:order=12,\
aformat=sample_fmts=s16,aresample=44100:dither_method=triangular" restored.flac
```

Stage 1 declick → stage 2 declip → stage 3 broadband afftdn denoise → stage 4 30 Hz rumble — then conform to CD spec with TPDF dither.

### Voice enhancement chain (podcast / audiobook)

```bash
ffmpeg -i raw_voice.wav -af "\
highpass=f=80,\
adynamicequalizer=dfrequency=6200:tfrequency=6200:mode=cut:bandwidth=1200:makeup=5:ratio=4,\
dialoguenhance,\
speechnorm=e=12.5:r=0.0001:l=1,\
apsyclip=level_in=1:level_out=1:clip=0.9" voice_ready.wav
```

High-pass → de-esser-style dynamic EQ at ~6.2 kHz → dialogue enhance → speech leveler → psyclip as the final peak catcher.

### Radio-ready master chain (music)

```bash
ffmpeg -i master_pre.wav -af "\
equalizer=f=60:t=q:w=1.2:g=1,\
adynamicequalizer=dfrequency=3500:tfrequency=3500:mode=cut:bandwidth=800:makeup=3:ratio=2,\
loudnorm=I=-14:TP=-1.5:LRA=7,\
apsyclip=clip=0.89" master_radio.wav
```

Low shelf lift → upper-mid dynamic cut to tame ear fatigue → EBU R128 streaming target (-14 LUFS) → psyclip as true-peak safety.

### Creative: synth pad shimmer

```bash
ffmpeg -i pad.wav -af "chorus=0.5:0.9:40|60|80:0.3|0.3|0.3:0.2|0.25|0.3:1|1.5|2,\
aphaser=type=t:speed=0.3:depth=0.7,\
crystalizer=i=1.5" pad_shimmer.wav
```

### Telephone/radio effect

```bash
ffmpeg -i voice.wav -af "bandpass=f=1700:width_type=q:w=0.5,asoftclip=type=atan" telephone.wav
```

### Host a Calf Compressor (LV2)

```bash
ffmpeg -i in.wav -af "lv2=p=http://calf.sourceforge.net/plugins/Compressor:c=threshold=0.1|ratio=4|attack=20|release=250|makeup=4" out.wav
```
