---
name: ffmpeg-audio-spatial
description: >
  Spatial and binaural audio with ffmpeg: headphone (HRTF binaural from multichannel), sofalizer (custom HRTF via SOFA files), surround (mono/stereo → 5.1/7.1 upmix), extrastereo, stereotools, stereowiden, earwax, crossfeed, channelsplit, channelmap, join. Use when the user asks to create binaural headphone audio, apply HRTF, convert stereo to 5.1, upmix mono to surround, widen stereo image, split channels to separate tracks, route channels, or fix mobile-device listening fatigue.
argument-hint: "[operation] [input]"
---

# Ffmpeg Audio Spatial

**Context:** $ARGUMENTS

## Quick start

- **5.1/7.1 → binaural headphones:** Step 1 (probe layout) → Step 2 (pick `headphone` or `sofalizer`) → Step 3 (build filter, ClockWise channel order)
- **Stereo → 5.1 upmix:** Step 1 (probe) → Step 2 (pick `surround`) → Step 3 (`chl_out=5.1`)
- **Stereo widen / crossfeed / earwax:** Step 2 (pick stereo FX) → Step 3 (one-liner `-af`)
- **Split / remap / join channels:** Step 2 (pick `channelsplit` / `pan` / `amerge`) → Step 3 (build graph)

## When to use

- You need a binaural headphone downmix from a 5.1/7.1 film or game mix.
- You are given a stereo master and asked to "make it wider," "add space," "reduce ping-pong fatigue on earbuds," or "trick a stereo file into 5.1."
- You need to split a multichannel master into one-mono-per-channel files (stem prep).
- You need to remap, reroute, or merge separate mono tracks into a laid-out multichannel bus.

## Step 1 — Identify the channel layout

Every spatial op depends on the input layout. Probe first:

```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=channels,channel_layout,sample_rate \
  -of default=nw=1 INPUT
```

Interpret:

- `channels=2 channel_layout=stereo` → stereo-only operations (widen, earwax, crossfeed, upmix).
- `channels=6 channel_layout=5.1` (or `5.1(side)`) → binaural, downmix, or split.
- `channels=8 channel_layout=7.1` → binaural (extend channel map) or split.
- `channels=1 channel_layout=mono` → duplicate to stereo first, or upmix.
- Layout missing? Use `scripts/spatial.py detect` — it falls back to FFmpeg's layout table and warns when the layout is unset so you can force it with `-channel_layout` on input.

## Step 2 — Pick the operation

| Goal | Filter | Notes |
| --- | --- | --- |
| 5.1/7.1 → binaural (built-in HRTF) | `headphone` | Channels must be listed in ClockWise order (see Gotchas). |
| 5.1/7.1 → binaural (custom HRTF) | `sofalizer` | Needs `--enable-libmysofa` build flag + a `.sofa` file. |
| Stereo → 5.1/7.1 upmix | `surround` | Invents center/surrounds — sounds plausible, not true 5.1. |
| Stereo widen | `stereowiden` | Delay+feedback — physical widening. |
| Boost stereo difference | `extrastereo` | Amplifies L-R, can exaggerate artifacts. |
| M/S stereo tools | `stereotools` | Mid/Side level, phase, mute-L/mute-R. |
| Headphone listening fatigue | `crossfeed` | Blends L/R back — opposite of `extrastereo`. |
| 2-ch CD → headphone cues | `earwax` | Fixed 44.1 kHz stereo only. |
| Split channels to streams | `channelsplit` | Produces N mono pads. |
| Remap channel layout | `channelmap` or `pan` | `pan` is expression-based. |
| Join N monos into a layout | `amerge` + `pan` | `amerge` interleaves; `pan` assigns names. |

## Step 3 — Build the filter

### 5.1 → binaural stereo (built-in HRTF)

```bash
ffmpeg -i in.mkv -af "headphone=FL|FR|FC|LFE|BL|BR" -c:a libmp3lame -q:a 2 out.mp3
```

### 7.1 → binaural (ClockWise: FL FR FC LFE BL BR SL SR)

```bash
ffmpeg -i in.mkv -af "headphone=FL|FR|FC|LFE|BL|BR|SL|SR" -c:a aac -b:a 192k out.m4a
```

### 5.1 → binaural with custom SOFA

```bash
ffmpeg -i in.mkv -af "sofalizer=sofa=mit_kemar.sofa:type=freq:radius=1" out.flac
```

### Stereo → 5.1 upmix

```bash
ffmpeg -i stereo.wav -af "surround=chl_out=5.1" -c:a ac3 -b:a 448k surround.ac3
```

### Stereo widen

```bash
ffmpeg -i in.wav -af "stereowiden=delay=20:feedback=0.3:crossfeed=0.3:drymix=0.8" out.wav
```

### Extra-stereo (L-R amplification)

```bash
ffmpeg -i in.wav -af "extrastereo=m=2.5" out.wav
```

### Crossfeed (headphone fatigue reducer)

```bash
ffmpeg -i in.wav -af "crossfeed=strength=0.5:range=0.5" out.wav
```

### Earwax (CD-stereo → headphone cues)

```bash
ffmpeg -i in.wav -af "earwax" out.wav
```

### Stereotools M/S matrix

```bash
ffmpeg -i in.wav -af "stereotools=mlev=0.8:slev=1.2" out.wav
```

### Split 5.1 into six mono WAVs

```bash
ffmpeg -i in.mkv -filter_complex \
  "[0:a]channelsplit=channel_layout=5.1[FL][FR][FC][LFE][BL][BR]" \
  -map "[FL]" FL.wav -map "[FR]" FR.wav -map "[FC]" FC.wav \
  -map "[LFE]" LFE.wav -map "[BL]" BL.wav -map "[BR]" BR.wav
```

### Remap — stereo → mono (left only)

```bash
ffmpeg -i in.wav -af "pan=mono|c0=c0" left.wav
# equivalent via channelmap:
ffmpeg -i in.wav -af "channelmap=channel_layout=mono:map=FL-FC" left.wav
```

### Remap — mono → stereo (duplicate)

```bash
ffmpeg -i in.wav -af "pan=stereo|c0=c0|c1=c0" stereo.wav
# equivalent via channelmap:
ffmpeg -i in.wav -af "channelmap=channel_layout=stereo:map=0-FL|0-FR" stereo.wav
```

### Join two mono files into stereo

```bash
ffmpeg -i L.wav -i R.wav -filter_complex \
  "[0:a][1:a]amerge=inputs=2,pan=stereo|c0=c0|c1=c1[a]" \
  -map "[a]" stereo.wav
```

## Step 4 — Verify the output layout

Always re-probe the result:

```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=channels,channel_layout -of default=nw=1 OUT
```

- Binaural should report `channels=2 channel_layout=stereo`.
- Upmix should report `channels=6 channel_layout=5.1`.
- If `channel_layout=unknown`, add `-channel_layout` on input or use `aformat=channel_layouts=...` before encoding.

## Available scripts

- **`scripts/spatial.py`** — Stdlib-only helper with `detect`, `binaural`, `upmix`, `widen`, `split`, `remap`, `join` subcommands. Prints the exact ffmpeg command, supports `--dry-run` and `--verbose`.

Examples:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py detect --input movie.mkv
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py binaural --input movie.mkv --output bin.m4a
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py binaural --input movie.mkv --output bin.flac --sofa mit_kemar.sofa
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py upmix --input stereo.wav --output surround.ac3 --layout 5.1
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py widen --input in.wav --output wide.wav --strength 0.5
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py split --input in.mkv --output-pattern "ch_%d.wav"
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py remap --input in.wav --output out.wav --map "mono:c0=0.5*c0+0.5*c1"
uv run ${CLAUDE_SKILL_DIR}/scripts/spatial.py join --inputs L.wav R.wav --output stereo.wav --layout stereo
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for per-filter option tables, channel-layout names/codes, ClockWise diagrams, SOFA sources, `pan` grammar, and a recipe book.

## Gotchas

- **`headphone` ClockWise order is mandatory.** 5.1 = `FL|FR|FC|LFE|BL|BR`; 7.1 = `FL|FR|FC|LFE|BL|BR|SL|SR`. Wrong order produces a spatially scrambled binaural mix that still "sounds like audio" — easy to miss on a casual listen.
- **`headphone` uses a generic built-in HRTF.** Acceptable for previews; for delivery use `sofalizer` with a measured SOFA file.
- **`sofalizer` needs `--enable-libmysofa`.** Verify with `ffmpeg -filters | grep sofalizer`. If absent, rebuild FFmpeg or fall back to `headphone`.
- **SOFA file sources:** SADIE II (University of York), MIT KEMAR, CIPIC HRTF database, ARI HRTF. Free for research. Per-subject impulse responses — pick one close to your listener population or use the "generic" subject.
- **`surround` upmix invents channels.** It is NOT Dolby Pro Logic / Pro Logic II decoding. For delivery masters, upmix stereo → 5.1 is generally discouraged unless the source was originally multichannel and got downmixed somewhere.
- **Channel names (FFmpeg):** `FL, FR, FC, LFE, BL, BR, SL, SR, BC, FLC, FRC, TC, TFL, TFC, TFR, TBL, TBC, TBR, DL, DR, WL, WR`. Some older builds use `SL/SR` where newer builds use `BL/BR` for 5.1 — check `ffmpeg -layouts`.
- **`channel_layout` strings:** `mono, stereo, 2.1, 3.0, 3.0(back), 4.0, quad, quad(side), 3.1, 5.0, 5.0(side), 4.1, 5.1, 5.1(side), 6.0, 6.0(front), hexagonal, 6.1, 6.1(back), 6.1(front), 7.0, 7.0(front), 7.1, 7.1(wide), 7.1(wide-side), octagonal, hexadecagonal, downmix`.
- **`pan` syntax:** `pan=LAYOUT|CHAN=EXPR|CHAN=EXPR`. `EXPR` uses `c0..cN` for the input channels, or named channels like `FL`, `FR`. Weights are linear (not dB).
- **`amerge` interleaves, `amix` sums.** Use `amerge` to combine separate monos into one multichannel stream; follow it with `pan` to assign a layout. Use `amix` to sum multiple stereo buses into one.
- **After `amerge=inputs=N`:** the layout is unset. Always chain `,pan=stereo|c0=c0|c1=c1` (or whatever layout you want) so downstream encoders know what to do.
- **Binaural output is stereo.** Always deliver binaural as stereo AAC/Opus/FLAC — not mono, not 5.1.
- **Crossfeed is for hard-panned masters.** Old stereo records (pre-1970s pop, some jazz) sound exhausting on earbuds because they hard-pan instruments. `crossfeed=strength=0.4:range=0.6` is a good default.
- **Sample rate matters for HRTF.** `sofalizer` supports multiple rates but resampling during HRTF adds artifacts. If your source varies, insert `aresample=48000` before the binaural filter and keep downstream consistent.
- **Container capacity:** MP4+AAC up to 7.1 is fine. For exotic layouts (hexadecagonal, 22.2) use MKV/MOV + FLAC or PCM. Some MP4 players silently downmix anything >5.1.

## Examples

### Example 1: Theater 5.1 → binaural preview for editor review

```bash
ffmpeg -i reel.mov -vn \
  -af "aresample=48000,headphone=FL|FR|FC|LFE|BL|BR" \
  -c:a libopus -b:a 160k reel_binaural.opus
```

Result: stereo Opus file that carries spatial cues on headphones.

### Example 2: Podcast — tighten host-guest stereo and reduce earbud fatigue

```bash
ffmpeg -i podcast.wav \
  -af "crossfeed=strength=0.4:range=0.5,stereotools=mlev=1.0:slev=0.9" \
  -c:a libopus -b:a 96k podcast_cf.opus
```

### Example 3: Extract center-channel dialogue from a 5.1 film

```bash
ffmpeg -i film.mkv -filter_complex \
  "[0:a]channelsplit=channel_layout=5.1:channels=FC[dlg]" \
  -map "[dlg]" -c:a flac dialogue.flac
```

### Example 4: Build a 5.1 master from six mono stems

```bash
ffmpeg -i FL.wav -i FR.wav -i FC.wav -i LFE.wav -i BL.wav -i BR.wav \
  -filter_complex "[0][1][2][3][4][5]amerge=inputs=6,pan=5.1|c0=c0|c1=c1|c2=c2|c3=c3|c4=c4|c5=c5[a]" \
  -map "[a]" -c:a flac master_5_1.flac
```

### Example 5: Stereo widen a boom-mic narration for a VR piece

```bash
ffmpeg -i vo.wav \
  -af "stereowiden=delay=18:feedback=0.2:crossfeed=0.2:drymix=0.9" \
  -c:a flac vo_wide.flac
```

## Troubleshooting

### Error: `Option 'map' not found` or channel names look wrong in `channelmap`

Cause: using `map=0-FL|0-FR` on an input whose layout is `unknown`.
Solution: force the input layout with `-channel_layout stereo` (on the input) or use `pan` with `c0/c1` indices instead of names.

### Error: `Unknown filter 'sofalizer'`

Cause: FFmpeg not built with `--enable-libmysofa`.
Solution: rebuild FFmpeg, `brew install ffmpeg` with the `--with-libmysofa` formula option if available, or fall back to `headphone`.

### Binaural sounds "inside your head" / lifeless

Cause: input wasn't a true multichannel mix (stereo fed into `headphone` does nothing useful); or channel order was wrong.
Solution: confirm source channel count with `ffprobe`; re-order the map to strict ClockWise `FL|FR|FC|LFE|BL|BR`.

### `surround` upmix has no center / no surrounds

Cause: input was already mono or the `chl_out` layout wasn't set.
Solution: ensure input is stereo, then set `chl_out=5.1` explicitly: `-af "surround=chl_out=5.1"`. For mono sources duplicate to stereo first with `pan=stereo|c0=c0|c1=c0`.

### Output reports `channel_layout=unknown`

Cause: `amerge` produced an unlabeled multichannel stream; encoder refuses to tag it.
Solution: chain `,pan=LAYOUT|...` or `,aformat=channel_layouts=5.1` before the encoder.

### Encoder rejects 7.1 output

Cause: codec/container mismatch (MP3 max 2ch, some AAC profiles max 5.1, older MP4 mux).
Solution: switch to FLAC/Opus/AC-3/E-AC-3 and MKV/MOV; verify with `ffprobe` that `channel_layout=7.1` survived the mux.

### `extrastereo` makes vocals disappear

Cause: `m` too high — vocals often sit in the M (mono) component and get cancelled.
Solution: lower `m` (try 1.5–2.0 max); or use `stereotools` with a small `slev` boost instead.
