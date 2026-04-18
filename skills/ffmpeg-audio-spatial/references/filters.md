# Spatial / binaural audio filter reference

## `headphone` — HRTF binaural from multichannel

Binauralizes a multichannel signal using FFmpeg's built-in HRTF (or, when
combined with `map=` pointing at SOFA-formatted WAVs, per-ear impulse
responses). Output is always stereo.

| Option | Type | Default | Notes |
| --- | --- | --- | --- |
| `map` | string | (required) | Pipe-separated ClockWise channel order, e.g. `FL\|FR\|FC\|LFE\|BL\|BR`. Each token is an FFmpeg channel name. |
| `gain` | float (dB) | 0 | Post-gain applied to the binaural output. |
| `type` | enum `time`\|`freq` | `freq` | `freq` uses FFT convolution (fast, recommended for long clips). |
| `lfe` | float (dB) | 0 | Gain applied to LFE before summing (LFE has no spatial position). |
| `size` | int (samples) | 1024 | FFT block size (freq mode only). Larger = more latency, less overlap cost. |
| `hrir` | enum `stereo`\|`multich` | `stereo` | How paired HRIR samples are laid out when supplied as extra inputs. |

**Channel-order rule:** ClockWise starting from Front-Left.

## `sofalizer` — custom HRTF via SOFA file

Needs `--enable-libmysofa` at build time. Reads a `.sofa` file from the SOFA
project (http://www.sofacoustics.org/) to place up to 9 virtual loudspeakers
around a listener.

| Option | Type | Default | Notes |
| --- | --- | --- | --- |
| `sofa` | path | (required) | Path to `.sofa` file. |
| `gain` | float (dB) | 0 | Post gain. |
| `rotation` | float (deg) | 0 | Rotate the virtual soundfield around the listener. |
| `elevation` | float (deg) | 0 | Raise/lower the virtual speaker arc. |
| `radius` | float (m) | 1 | Listener radius; affects proximity cues for near-field SOFA sets. |
| `type` | enum `time`\|`freq` | `freq` | Convolution mode. |
| `speakers` | string | auto | Custom speaker positions, e.g. `"0 FL -30 0\|0 FR 30 0"` (name, az, el). |
| `lfegain` | float (dB) | 0 | LFE level. |
| `framesize` | int | 1024 | Convolution frame size. |
| `normalize` | bool | 1 | Normalize HRIR energy. |
| `interpolate` | bool | 0 | Bilinear HRIR interpolation between SOFA grid points. |
| `minphase` | bool | 0 | Use minimum-phase HRIR (lower group delay, flatter response). |

## `surround` — upmix stereo → N.M

| Option | Type | Default | Notes |
| --- | --- | --- | --- |
| `chl_out` | layout | `5.1` | Target layout (e.g. `5.1`, `7.1`, `5.1(side)`). |
| `chl_in` | layout | `stereo` | Source layout (usually `stereo`). |
| `level_in` | float | 1 | Pre-gain. |
| `level_out` | float | 1 | Post-gain. |
| `lfe` | bool | 1 | Emit an LFE channel (low-pass of the center). |
| `lfe_low` / `lfe_high` | Hz | 128 / 256 | LFE bandpass bounds. |
| `lfe_mode` | enum `add`\|`sub` | `add` | Whether to subtract LFE from mains. |
| `smooth` | float | 0 | Temporal smoothing of the matrix (0 disabled). |
| `angle` | float | 90 | Front image angle. |
| `fc_in` / `fc_out` | float | 1 | Center channel in/out gains. |
| `focus` | float | 0 | Widens/narrows front focus. |

## `extrastereo`

| Option | Default | Notes |
| --- | --- | --- |
| `m` | 2.5 | Multiplier of the L-R difference. >1 widens, <1 narrows. |
| `c` | 1 | Bool clip guard. |

## `stereotools`

M/S stereo matrix + utility toolkit.

| Option | Default | Notes |
| --- | --- | --- |
| `level_in` / `level_out` | 1 | In/out gain. |
| `balance_in` / `balance_out` | 0 | -1..+1. |
| `softclip` | 0 | Soft clip the output. |
| `mutel` / `muter` | 0 | Mute L or R. |
| `phasel` / `phaser` | 0 | Invert L or R. |
| `mode` | `lr>lr` | Matrix mode. Values: `lr>lr`, `lr>ms`, `ms>lr`, `lr>ll`, `lr>rr`, `lr>l+r`, `lr>rl`, `ms>ll`, `ms>rr`, `ms>rl`, `lr>l-r`. |
| `slev` / `sbal` | 1 / 0 | Side level & balance. |
| `mlev` / `mpan` | 1 / 0 | Mid level & pan. |
| `base` | 0 | Widening via bass/treble offset. |
| `delay` | 0 | L/R delay (ms). |
| `sclevel` | 1 | Side-channel compressor threshold. |

## `stereowiden`

Physical widening by delay + cross-feedback.

| Option | Default | Notes |
| --- | --- | --- |
| `delay` | 20 | ms of cross-delay. |
| `feedback` | 0.3 | 0..0.9, loops delayed opposite channel. |
| `crossfeed` | 0.3 | Blend of delayed signal. |
| `drymix` | 0.8 | Dry/wet. |

## `crossfeed`

Bauer-style cross-feed for headphone listening.

| Option | Default | Notes |
| --- | --- | --- |
| `strength` | 0.2 | 0..1 amount of L↔R blend. |
| `range` | 0.5 | Frequency range (low-shelf width). |
| `slope` | 0.5 | Shelf slope. |
| `level_in` / `level_out` | 0.9 / 1 | Gains. |
| `block_size` | 0 | FFT block size (0 = IIR mode). |

## `earwax`

No options. 44.1 kHz stereo only. Ported from SoX; adds cues that shift the
stereo image from "inside the head" to "in front" on headphones.

## `channelsplit`

| Option | Default | Notes |
| --- | --- | --- |
| `channel_layout` | `stereo` | Source layout name. |
| `channels` | `all` | Subset to keep (e.g. `FC\|LFE`). |

## `channelmap`

| Option | Default | Notes |
| --- | --- | --- |
| `map` | (required) | `SRC-DST\|SRC-DST` pairs, either `IDX-NAME`, `NAME-NAME`, or `IDX-IDX`. |
| `channel_layout` | — | Output layout label. |

Example: `channelmap=channel_layout=stereo:map=0-FL\|0-FR` duplicates a mono
input into both stereo channels.

## `join`

Combine parallel streams into one multichannel stream.

| Option | Default | Notes |
| --- | --- | --- |
| `inputs` | 2 | Number of input streams. |
| `channel_layout` | `stereo` | Output layout. |
| `map` | auto | Per-channel mapping `inputId.channelName-outChan`. |

## `amerge` + `pan`

`amerge=inputs=N` interleaves N input audio streams into one with N×channels,
but leaves the layout unset. Always chain `pan=LAYOUT|...` to name channels.

## `pan` expression grammar

```
pan=LAYOUT|OUTCHAN=EXPR|OUTCHAN=EXPR[|...]
```

- `LAYOUT`: a layout name (`stereo`, `5.1`, `mono`, ...) or channel count (`c6`).
- `OUTCHAN`: an output channel name (`FL`, `FC`, ...) or index (`c0`, `c1`, ...).
- `EXPR`: a linear combination of input channels using `c0..cN`, `+`, `-`, `*`, numeric constants. Weights are LINEAR (not dB).

Shortcuts:

- `c0=c0` is copy.
- `c0<c0+c1` (the `<` instead of `=`) auto-normalizes weights so sum = 1.

Examples:

```
pan=mono|c0=0.5*c0+0.5*c1          # stereo → mono, equal sum
pan=stereo|c0=c0|c1=c0             # mono → stereo (L/R both = source)
pan=stereo|FL<FL+0.707*FC+0.707*BL|FR<FR+0.707*FC+0.707*BR   # 5.1 → Lt/Rt matrix
pan=5.1|FL=c0|FR=c1|FC=c2|LFE=c3|BL=c4|BR=c5                 # identity remap
```

## Channel layout names and 4-char codes

| Layout | Count | FFmpeg tag | Channels (order) |
| --- | --- | --- | --- |
| mono | 1 | `mono` | FC |
| stereo | 2 | `stereo` | FL FR |
| 2.1 | 3 | `2.1` | FL FR LFE |
| 3.0 | 3 | `3.0` | FL FR FC |
| 3.0(back) | 3 | `3.0(back)` | FL FR BC |
| 4.0 | 4 | `4.0` | FL FR FC BC |
| quad | 4 | `quad` | FL FR BL BR |
| quad(side) | 4 | `quad(side)` | FL FR SL SR |
| 3.1 | 4 | `3.1` | FL FR FC LFE |
| 5.0 | 5 | `5.0` | FL FR FC BL BR |
| 5.0(side) | 5 | `5.0(side)` | FL FR FC SL SR |
| 4.1 | 5 | `4.1` | FL FR FC LFE BC |
| 5.1 | 6 | `5.1` | FL FR FC LFE BL BR |
| 5.1(side) | 6 | `5.1(side)` | FL FR FC LFE SL SR |
| 6.0 | 6 | `6.0` | FL FR FC BC SL SR |
| 6.0(front) | 6 | `6.0(front)` | FL FR FLC FRC SL SR |
| hexagonal | 6 | `hexagonal` | FL FR FC BL BR BC |
| 6.1 | 7 | `6.1` | FL FR FC LFE BC SL SR |
| 6.1(back) | 7 | `6.1(back)` | FL FR FC LFE BL BR BC |
| 6.1(front) | 7 | `6.1(front)` | FL FR LFE FLC FRC SL SR |
| 7.0 | 7 | `7.0` | FL FR FC BL BR SL SR |
| 7.0(front) | 7 | `7.0(front)` | FL FR FC FLC FRC SL SR |
| 7.1 | 8 | `7.1` | FL FR FC LFE BL BR SL SR |
| 7.1(wide) | 8 | `7.1(wide)` | FL FR FC LFE BL BR FLC FRC |
| 7.1(wide-side) | 8 | `7.1(wide-side)` | FL FR FC LFE FLC FRC SL SR |
| octagonal | 8 | `octagonal` | FL FR FC BL BR BC SL SR |
| hexadecagonal | 16 | `hexadecagonal` | + wide & top speakers |
| downmix | 2 | `downmix` | DL DR (matrix Lt/Rt) |

Full channel-name glossary (FFmpeg):

```
FL FR FC LFE BL BR BC SL SR FLC FRC TC
TFL TFC TFR TBL TBC TBR DL DR WL WR
LFE2 SDL SDR BFC BFL BFR
```

Produce the authoritative list with `ffmpeg -layouts`.

## ClockWise channel order diagram

**5.1 ClockWise** (what `headphone=` wants, FL → FR → FC → LFE → BL → BR):

```
             FC
      FL ───────── FR
       ●    ▲       ●
            │
            │
       ●    LFE     ●
      BL ──────── BR
```

**7.1 ClockWise** (FL → FR → FC → LFE → BL → BR → SL → SR):

```
             FC
      FL ───────── FR
       ●    ▲       ●
  SL ●      │      ● SR
            │
            │
       ●    LFE     ●
      BL ──────── BR
```

Mnemonic: "Front pair → Center → Sub → Back pair → Side pair". Listing
anything out of order (e.g. putting BL before FC) will cause the binauralizer
to place sounds at the wrong virtual angle.

## SOFA file sources (no links)

| Source | Notes |
| --- | --- |
| MIT KEMAR | Classic 1994 dataset, manikin head, 710 positions. Good generic fallback. |
| CIPIC HRTF Database | 45 subjects; anthropometric data included; good for subject-matching. |
| SADIE II | University of York; includes KU100 and KEMAR measurements; free academic use. |
| ARI HRTF (Austrian Academy) | Large database, multiple subject ages. |
| Bernschütz (TH Köln) | High-resolution; fewer subjects. |
| Club Fritz / Aachen | Used in research comparisons. |

Downloaded files are `.sofa`. Keep them alongside your project and reference
with `sofalizer=sofa=path/to/file.sofa`.

## Recipe book

### Theater 5.1 → headphone binaural (archival)

```bash
ffmpeg -i film.mov -vn \
  -af "aresample=48000,headphone=FL|FR|FC|LFE|BL|BR:lfe=0:type=freq:size=1024" \
  -c:a flac film_binaural.flac
```

Use `flac` for archive; transcode to Opus 128–160k for delivery.

### Theater 5.1 → binaural with measured HRTF

```bash
ffmpeg -i film.mov -vn \
  -af "aresample=48000,sofalizer=sofa=sadie_subject3.sofa:type=freq:radius=1:interpolate=1:minphase=1" \
  -c:a libopus -b:a 160k film_binaural.opus
```

### Podcast stereo widen (mild, safe for mono folddown)

```bash
ffmpeg -i ep.wav -af \
  "stereowiden=delay=15:feedback=0.2:crossfeed=0.2:drymix=0.9,crossfeed=strength=0.35:range=0.5" \
  -c:a libopus -b:a 96k ep.opus
```

Why not `extrastereo`: it can make vocals vanish on mono phone speakers.
`stereowiden` + `crossfeed` keeps the mid intact.

### Voice-over / dialogue extraction from 5.1

```bash
# Get FC only
ffmpeg -i film.mkv -filter_complex \
  "[0:a]channelsplit=channel_layout=5.1:channels=FC[dlg]" \
  -map "[dlg]" -c:a flac dialogue.flac
```

Not a perfect source separator — center still has some score bleed — but a
strong starting point before de-noise / dialogue-enhance.

### Stereo → 5.1 upmix for a YouTube spatial preview

```bash
ffmpeg -i music.wav -af "surround=chl_out=5.1" -c:a ac3 -b:a 448k music_5_1.ac3
```

Note: `surround` upmix is synthetic. Do not ship upmixed audio as an original
5.1 master — re-mix properly in a DAW instead.

### Dolby Atmos downmix — limits

FFmpeg has no Atmos object renderer. You can only operate on the **bed channels**
(typically 7.1.2 in an ADM BWF) after decoding with a third-party renderer
(Nugen Halo, Dolby Reference Player) to a channel-based master. Once you have
a 7.1 or 5.1 WAV you can run `headphone` / `sofalizer` for binaural preview.
Do not pretend `headphone` is an Atmos renderer — it is not object-aware.

### Build a 5.1 master from six mono stems

```bash
ffmpeg -i FL.wav -i FR.wav -i FC.wav -i LFE.wav -i BL.wav -i BR.wav \
  -filter_complex "[0][1][2][3][4][5]amerge=inputs=6,pan=5.1|c0=c0|c1=c1|c2=c2|c3=c3|c4=c4|c5=c5[a]" \
  -map "[a]" -c:a flac master_5_1.flac
```

### Sanity-check output layout

```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=channels,channel_layout,sample_rate -of default=nw=1 OUT
```
