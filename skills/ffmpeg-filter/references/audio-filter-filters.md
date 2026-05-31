# Audio Filters — Reference

Full option tables, channel-layout names, platform loudness targets, and
recipes. Load this when the SKILL.md quickstart is not enough — e.g.
tuning compressor knee, choosing resampler quality, building a ducking
or de-ess chain.

Authoritative sources:
- https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters
- https://ffmpeg.org/ffmpeg-resampler.html
- https://ffmpeg.org/ffmpeg-utils.html  (channel layouts)
- https://trac.ffmpeg.org/wiki/AudioVolume
- https://k.ylo.ph/2016/04/04/loudnorm.html  (2-pass loudnorm)

---

## Loudness background (EBU R128 / ITU-R BS.1770-4)

- **LUFS / LKFS** — Loudness Units Full Scale; perceptual integrated
  loudness averaged over the whole program using K-weighting + gating
  at -70 LUFS absolute and -10 LU relative.
- **LRA** — Loudness Range, in LU; the statistical spread of loudness
  over time (10th-95th percentile of gated short-term values).
- **TP / dBTP** — True Peak in dB relative to full scale, measured with
  4x oversampling. Stricter than sample peak.
- **I (Integrated)** — the single-number loudness target (e.g. -16 LUFS).

---

## loudnorm

EBU R128 single-pass or two-pass normalizer.

| Option           | Default | Notes                                          |
|------------------|---------|------------------------------------------------|
| `I`              | -24     | Integrated loudness target (LUFS). Range -70..-5. |
| `LRA`            | 7       | Loudness range target (LU). Range 1..50.       |
| `TP`             | -2      | True peak target (dBTP). Range -9..0.          |
| `measured_I`     | —       | Pass-1 measured integrated loudness.           |
| `measured_LRA`   | —       | Pass-1 measured loudness range.                |
| `measured_TP`    | —       | Pass-1 measured true peak.                     |
| `measured_thresh`| —       | Pass-1 measured threshold (gate).              |
| `offset`         | 0       | Pass-1 target offset gain.                     |
| `linear`         | true    | With all measured_*, apply linear gain (no dyn).|
| `dual_mono`      | false   | Treat mono as dual-mono for loudness calc.     |
| `print_format`   | none    | `json` (pass 1) or `summary` (pass 2).         |

**2-pass is mandatory for masters.** Single-pass applies dynamic gain
that can pump transients.

---

## dynaudnorm

Dynamic audio normalizer (per-window). Fast one-pass, OK for rough cuts.

| Option | Default | Notes                                           |
|--------|---------|-------------------------------------------------|
| `f`    | 500     | Frame length (ms). Smaller = more responsive.   |
| `g`    | 31      | Gaussian window size (odd). Smaller = less smoothing. |
| `p`    | 0.95    | Peak value (0..1). How close to clip it aims.   |
| `m`    | 10      | Max gain factor.                                |
| `r`    | 0       | Target RMS (0 = disabled).                      |
| `n`    | 1       | Coupled channels (0 = per-channel).             |
| `c`    | 0       | Compress factor. 0 disables internal compress.  |

---

## volume

Static linear or dB gain.

| Option       | Default | Notes                                      |
|--------------|---------|--------------------------------------------|
| `volume`     | 1.0     | `0.5`, `-6dB`, expressions like `2*PI`.    |
| `precision`  | float   | `fixed`, `float`, `double`.                |
| `replaygain` | drop    | `drop`, `ignore`, `track`, `album`.        |
| `eval`       | once    | `once` or `frame` (per-frame eval).        |

---

## acompressor

Feed-forward compressor.

| Option       | Default | Notes                                      |
|--------------|---------|--------------------------------------------|
| `threshold`  | 0.125   | Linear (≈ -18 dBFS). Or `-18dB`.           |
| `ratio`      | 2       | 1..20.                                     |
| `attack`     | 20      | ms. 0.01..2000.                            |
| `release`    | 250     | ms. 0.01..9000.                            |
| `knee`       | 2.828   | dB (linear 2.828 ≈ 9 dB knee).             |
| `makeup`     | 1       | Makeup gain (linear).                      |
| `mix`        | 1       | Dry/wet 0..1.                              |
| `detection`  | rms     | `peak` or `rms`.                           |
| `link`       | average | `average` or `maximum` (stereo linking).   |

---

## compand

Multi-band compressor/expander via attack/decay/transfer points.

Canonical "voice compand":
```
compand=attacks=0.3:decays=0.8:points=-80/-80|-40/-40|-30/-20|-20/-10|0/-3
```
`attacks`/`decays`: seconds (per-channel if `:`-separated).
`points`: piecewise transfer function `in_dB/out_dB|...`.

---

## equalizer / bass / treble / highpass / lowpass

`equalizer=f=<Hz>:t=<q|s|o|h|k>:w=<width>:g=<dB>`
- `t=q` → width in Q; `t=s` → slope; `t=o` → octaves; `t=h` → Hz.

`bass=g=<dB>:f=<Hz>:w=<width>:t=<q|s|o|h>`  (low-shelf, default f=100)
`treble=g=<dB>:f=<Hz>:w=<width>:t=<q|s|o|h>` (high-shelf, default f=3000)

`highpass=f=<Hz>:t=<q|s|o|h>:w=<width>:p=<poles>` (p=1 or 2)
`lowpass` — same options as highpass.

---

## aresample

Sample-rate conversion + async handling.

| Option         | Default | Notes                                          |
|----------------|---------|------------------------------------------------|
| `<rate>`       | —       | Positional — `aresample=48000`.                |
| `async`        | 0       | Samples/second correction for drift (e.g. 1000).|
| `min_hard_comp`| 0.1     | Seconds — threshold to hard-stretch/pad.       |
| `first_pts`    | -1      | Align first PTS to value (0 for t=0).          |
| `resampler`    | swr     | `swr` or `soxr`.                               |
| `dither_method`| triangular_hp | `rectangular`, `triangular`, `gaussian`, etc. |
| `filter_type`  | kaiser  | `cubic`, `blackman_nuttall`, `kaiser`.         |
| `kaiser_beta`  | 9       | 2..16. Higher = steeper rolloff.               |
| `precision`    | 20      | Bits. Higher = better quality / slower.        |

Use `aresample=async=1000:first_pts=0` to correct A/V drift on capture.

---

## atempo

Time-stretch without pitch shift.

- Range per instance: **0.5..100.0** (modern ffmpeg). Older <5.1 capped at 2.0.
- Chain: `atempo=0.5,atempo=0.5` → 0.25x; `atempo=2,atempo=2,atempo=2` → 8x.
- Keep pitch = atempo. Change pitch too = `asetrate`.

---

## amix

Sum N inputs.

| Option                | Default  | Notes                                      |
|-----------------------|----------|--------------------------------------------|
| `inputs`              | 2        | Number of inputs.                          |
| `duration`            | longest  | `longest`, `shortest`, `first`.            |
| `dropout_transition`  | 2        | Seconds to fade when a stream ends.        |
| `normalize`           | 1        | **Set to 0** unless you want 1/N gain.     |
| `weights`             | "1 1 ... 1" | Per-input gain weights (space-separated).|

---

## amerge

Interleave channels of N inputs into one stream.

```
amerge=inputs=<N>
```
Each input keeps its own channel count; total channels = sum. Use `pan`
afterwards to relabel the resulting layout.

---

## pan

Remap / recombine channels with an explicit expression.

```
pan=<out_layout>|c0=<expr>|c1=<expr>|...
```
Identifiers inside `<expr>`:
- `c0`, `c1`, … — input channel index.
- Named: `FL`, `FR`, `FC`, `LFE`, `BL`, `BR`, `SL`, `SR`, `BC`, `FLC`, `FRC`.
- Coefficients are linear; `0.707` ≈ -3 dB.

Common:
```
pan=mono|c0=0.5*c0+0.5*c1                             # stereo → mono
pan=stereo|c0=c0|c1=c1                                # passthrough
pan=stereo|c0=0.5*FL+0.707*FC+0.5*BL+0.5*SL|          # 5.1 → stereo
          c1=0.5*FR+0.707*FC+0.5*BR+0.5*SR
pan=stereo|c0=c1|c1=c0                                # swap L/R
```

---

## silenceremove

Trim silence at start/end/middle.

| Option            | Default | Notes                                          |
|-------------------|---------|------------------------------------------------|
| `start_periods`   | 0       | How many leading silent regions to strip.      |
| `start_duration`  | 0       | Seconds of continuous silence to count.        |
| `start_threshold` | 0       | Below this level = silence. `0` or `-50dB`.    |
| `stop_periods`    | 0       | Trailing silent regions. **`-1` = all** tail.  |
| `stop_duration`   | 0       | Seconds.                                       |
| `stop_threshold`  | 0       | Level.                                         |
| `detection`       | rms     | `peak` or `rms`.                               |
| `window`          | 0.02    | RMS averaging window (s).                      |

---

## Channel-layout names (FFmpeg)

Canonical single-channel identifiers:

| ID    | Meaning                     |
|-------|-----------------------------|
| FL    | Front Left                  |
| FR    | Front Right                 |
| FC    | Front Center                |
| LFE   | Low Frequency Effects (sub) |
| BL    | Back Left                   |
| BR    | Back Right                  |
| FLC   | Front Left of Center        |
| FRC   | Front Right of Center       |
| BC    | Back Center                 |
| SL    | Side Left                   |
| SR    | Side Right                  |
| TC    | Top Center                  |
| TFL   | Top Front Left              |
| TFC   | Top Front Center            |
| TFR   | Top Front Right             |
| TBL   | Top Back Left               |
| TBC   | Top Back Center             |
| TBR   | Top Back Right              |
| DL    | Downmix Left                |
| DR    | Downmix Right               |
| WL    | Wide Left                   |
| WR    | Wide Right                  |
| SDL   | Surround Direct Left        |
| SDR   | Surround Direct Right       |
| LFE2  | Second LFE                  |

Named layouts: `mono`, `stereo`, `2.1`, `3.0`, `3.0(back)`, `4.0`,
`quad`, `quad(side)`, `5.0`, `5.0(side)`, `5.1`, `5.1(side)`, `6.0`,
`6.0(front)`, `hexagonal`, `6.1`, `6.1(back)`, `6.1(front)`, `7.0`,
`7.0(front)`, `7.1`, `7.1(wide)`, `7.1(wide-side)`, `octagonal`,
`hexadecagonal`, `downmix`.

Custom layouts: `FL+FR+FC+LFE+BL+BR` (any `+`-joined list of IDs).

---

## Platform loudness targets

| Platform                      | Integrated (LUFS) | True Peak (dBTP) | LRA (LU) |
|-------------------------------|-------------------|------------------|----------|
| YouTube                       | -14               | -1.0             | —        |
| Spotify (normal)              | -14               | -1.0             | —        |
| Spotify (loud)                | -11               | -2.0             | —        |
| Apple Music (Sound Check on)  | -16               | -1.0             | —        |
| Apple Podcasts                | -16               | -1.0             | —        |
| Tidal                         | -14               | -1.0             | —        |
| Amazon Music                  | -14               | -2.0             | —        |
| Netflix (stream / mobile)     | -27               | -2.0             | —        |
| AMAZON AIV / delivery         | -24               | -2.0             | —        |
| EBU R128 (TV, EU)             | -23               | -1.0             | ≤ ~7..10 |
| ATSC A/85 (US TV)             | -24               | -2.0             | —        |
| AES streaming                 | -18 to -16        | -1.0             | —        |

Broadcast masters: run 2-pass loudnorm; verify with a separate `ebur128`
measurement pass — do not trust the summary from the applying pass.

---

## Recipes

### Duck music under voice (sidechain)

Voice is the key; music is the target:
```bash
ffmpeg -i voice.wav -i music.wav -filter_complex \
"[0:a]asplit=2[vox][key]; \
 [1:a][key]sidechaincompress=threshold=-24dB:ratio=8:attack=5:release=250:makeup=0[ducked]; \
 [vox][ducked]amix=inputs=2:duration=longest:normalize=0[aout]" \
-map "[aout]" out.wav
```
- `threshold` controls how quiet voice must be before ducking stops.
- `attack=5 ms` catches consonants; `release=250 ms` lets music breathe.

### De-esser (dynamic EQ via sidechain on hi-band)

```bash
-af "asplit=2[full][ess]; \
     [ess]bandpass=f=6500:w=4000[esskey]; \
     [full][esskey]sidechaincompress=threshold=-28dB:ratio=6:attack=1:release=60[out]"
```
Tweak `f=6500` toward 4–10 kHz depending on the voice.

### Click / pop removal

```bash
-af "adeclick=w=55:o=2:a=2:threshold=2,adeclip=w=55:o=2:a=2:threshold=10"
```
`adeclick` targets short impulses (vinyl clicks); `adeclip` repairs
clipped samples. Both are CPU-light and can stack.

### Broadband denoise

```bash
-af "afftdn=nr=12:nf=-25:nt=w"
```
`nr` = noise reduction in dB; `nf` = noise floor estimate in dBFS;
`nt=w` = wideband mode. For stationary hum add `arnndn=m=<model>.rnnn`
if an RNNoise model file is available.

### Mastering chain (voice podcast)

```
highpass=f=80,
lowpass=f=16000,
equalizer=f=200:t=q:w=1.2:g=-2,
equalizer=f=3000:t=q:w=1.5:g=2,
acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=1.5,
loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=...:measured_LRA=...:measured_TP=...:measured_thresh=...:offset=...:linear=true
```
High-pass rumble → gentle mid-scoop → presence lift → light comp →
loudnorm as the final stage (not before comp — loudnorm must see the
final dynamics).

### A/V sync drift from live capture

```
-af "aresample=async=1000:first_pts=0,aresample=48000"
```
`async=1000` stretches/squeezes up to 1000 samples/sec to track PTS.
