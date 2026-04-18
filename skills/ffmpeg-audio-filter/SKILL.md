---
name: ffmpeg-audio-filter
description: >
  Apply audio filters with ffmpeg -af / -filter_complex: loudnorm (EBU R128), volume, dynaudnorm, compand, equalizer, bass/treble, aresample (sample rate), atempo (speed), apad/atrim, amix, amerge, pan (channel layout), silenceremove, afade, asetrate. Use when the user asks to normalize loudness, boost/reduce volume, EQ audio, resample, change speed/tempo, trim silence, mix audio tracks, merge channels, swap/remap channels, convert mono/stereo/5.1, or fade in/out.
argument-hint: "[operation] [input]"
---

# Ffmpeg Audio Filter

**Context:** $ARGUMENTS

## Quick start

- **Loudness normalize (YouTube, podcast, broadcast):** 2-pass loudnorm → Step 1
- **Quick volume bump/cut:** `volume` filter → Step 2
- **Change speed without pitch shift:** `atempo` (chain if outside 0.5–2.0) → Step 2
- **Mix two tracks (voice over music):** `amix` with `aresample` + `aformat` guards → Step 2
- **Stereo → mono / 5.1 → stereo:** `pan` with explicit channel map → Step 2
- **Trim leading/trailing silence:** `silenceremove` → Step 2
- **Verify result:** `ebur128` or `astats` → Step 3

## When to use

- Delivering audio to a loudness spec (YT -14, Spotify -14, Apple Pod -16, EBU R128 -23, ATSC A/85 -24 LKFS).
- Fixing level mismatch across multiple source clips.
- Changing playback speed, pitch, or sample rate without manual re-encode math.
- Mixing/merging/splitting channels or remapping surround layouts.
- Cleaning up: de-ess, denoise, compress, EQ, silence trim.

## Step 1 — Pick your target

Loudness mastering (perceptual) → 2-pass `loudnorm`. Single-pass is dynamic
and can pump; 2-pass uses measured stats for a clean linear gain.

Peak normalize (simple, not perceptual) → measure peak with `astats` or
`volumedetect`, then apply `volume=<gain>dB`.

Speed/tempo change → `atempo` (keeps pitch; range 0.5–100 per instance,
chain two `atempo=0.5` for 0.25x). Pitch shift → `asetrate`+`aresample`
or `rubberband` (rare build).

Mix/merge → `amix` (sums signals, ideal for music+voice); `amerge`
(interleaves channels, e.g. L+R mono files → stereo).

Channel remap → `pan` with an explicit layout expression.

Verify → `ebur128` filter (loudness meter) or `astats` (peak/RMS/DC).

## Step 2 — Build the filter graph

Use `-af` when there is a single audio input. Use `-filter_complex`
whenever more than one input feeds the graph (`amix`, `amerge`,
`sidechaincompress`).

### Loudnorm 2-pass (canonical, required for masters)

Pass 1 — measure (writes JSON to stderr):
```bash
ffmpeg -hide_banner -i in.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json \
  -f null -
```

Parse `input_i`, `input_lra`, `input_tp`, `input_thresh`, `target_offset`
from the JSON block at the end of stderr.

Pass 2 — apply (linear gain, clean):
```bash
ffmpeg -i in.wav -af \
  loudnorm=I=-16:LRA=11:TP=-1.5:\
measured_I=<input_i>:measured_LRA=<input_lra>:\
measured_TP=<input_tp>:measured_thresh=<input_thresh>:\
offset=<target_offset>:linear=true:print_format=summary \
  -ar 48000 out.wav
```

`scripts/afilter.py --two-pass` handles both passes and JSON parsing.

### Single-pass dynaudnorm (fast, OK for rough jobs)

```bash
ffmpeg -i in.wav -af dynaudnorm=f=150:g=15:p=0.95 out.wav
```

### Volume

```bash
-af volume=0.5           # linear (half amplitude)
-af volume=-6dB          # decibel
-af volume=0.8:precision=float
```

### atempo (speed, pitch-preserving)

```bash
-af atempo=1.5                      # 1.5x
-af atempo=0.5,atempo=0.5           # 0.25x (chain; single-instance limit 0.5–100)
```

### asetrate + aresample (speed AND pitch, like a tape)

```bash
-af asetrate=48000*1.06,aresample=48000,atempo=1/1.06
# pitch up ~1 semitone, keep duration
```

### amix (two sources summed)

```bash
ffmpeg -i voice.wav -i music.wav -filter_complex \
  "[0]aresample=48000,aformat=channel_layouts=stereo[a0]; \
   [1]aresample=48000,aformat=channel_layouts=stereo,volume=0.25[a1]; \
   [a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]" \
  -map "[aout]" out.wav
```

`normalize=0` is critical — default 1 scales by 1/N which is almost
never what you want.

### amerge (L+R mono → stereo)

```bash
ffmpeg -i L.wav -i R.wav -filter_complex \
  "[0][1]amerge=inputs=2,pan=stereo|c0=c0|c1=c1[aout]" \
  -map "[aout]" stereo.wav
```

### pan (channel remap)

```bash
-af pan=mono|c0=0.5*c0+0.5*c1                     # stereo → mono
-af "pan=stereo|c0=c0|c1=c1"                      # passthrough stereo
-af "pan=stereo|c0=0.5*FL+0.707*FC+0.5*BL+0.5*SL| \
               c1=0.5*FR+0.707*FC+0.5*BR+0.5*SR"  # 5.1 → stereo downmix
```

### silenceremove

```bash
-af silenceremove=start_periods=1:start_duration=0.5:start_threshold=-50dB: \
                  stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB
```

### Fade

```bash
-af "afade=t=in:st=0:d=1,afade=t=out:st=58:d=2"
```

### EQ chain

```bash
-af "highpass=f=80,lowpass=f=16000,equalizer=f=3000:t=q:w=1.5:g=3,bass=g=2,treble=g=1"
```

## Step 3 — Run + verify

After any loudness operation, re-measure:
```bash
ffmpeg -hide_banner -nostats -i out.wav -af ebur128=peak=true -f null - 2>&1 | tail -20
```

Look at `I:` (integrated LUFS), `LRA:` (loudness range), `Peak:` (dBTP).
They should match the target within ~0.5 LU.

For peak/RMS/DC offset:
```bash
ffmpeg -i out.wav -af astats=metadata=1:reset=1 -f null - 2>&1 | grep -E "RMS|Peak|DC"
```

Channel layout / codec sanity:
```bash
ffprobe -v error -select_streams a -show_entries stream=codec_name,sample_rate,channels,channel_layout -of json out.wav
```

## Available scripts

- **`scripts/afilter.py`** — presets for loudnorm (yt/podcast/ebu), peak normalize, 2-input mix, speed, mono downmix, simple denoise. Implements the 2-pass loudnorm measure→apply flow (`--two-pass`).

## Workflow

```bash
# 2-pass loudnorm to YouTube target
uv run ${CLAUDE_SKILL_DIR}/scripts/afilter.py loudnorm-yt \
  --input in.wav --output out.wav --two-pass --verbose

# mix voice over music
uv run ${CLAUDE_SKILL_DIR}/scripts/afilter.py mix-two \
  --inputs voice.wav music.wav --output mix.wav

# speed up 2x (chain-safe)
uv run ${CLAUDE_SKILL_DIR}/scripts/afilter.py speed \
  --input in.wav --output out.wav --factor 2.0

# preview command without running
uv run ${CLAUDE_SKILL_DIR}/scripts/afilter.py loudnorm-podcast \
  --input in.wav --output out.wav --two-pass --dry-run
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for full option tables (loudnorm, dynaudnorm, acompressor, compand, equalizer, aresample, amix, pan, silenceremove), channel-layout names, platform loudness targets, and recipes (ducking, de-ess, click removal).

## Gotchas

- **`loudnorm` single-pass is dynamic**, not linear. It can pump and distort transients. Always run 2-pass for masters — measure first, then apply with `measured_*` + `linear=true`.
- **`linear=true` only works when every `measured_*` value is supplied.** Miss one → falls back to dynamic silently.
- **`-af` is single-input.** Any graph with `amix`, `amerge`, or `sidechaincompress` must use `-filter_complex` and `-map "[aout]"`.
- **`amix` vs `amerge`:** `amix` sums samples (music + voice mix). `amerge` interleaves channels (two mono files → one stereo stream). Mixing these up produces silent outputs or wrong channel counts.
- **Sample-rate mismatch silently corrupts `amix`.** Insert `aresample=48000` on every input before mixing.
- **Channel-layout mismatch silently breaks `amix`.** Insert `aformat=channel_layouts=stereo` (or `mono`) per input.
- **`amix` default `normalize=1` scales output by 1/N.** Almost always wrong — set `normalize=0` and handle gain yourself.
- **`volume` is NOT loudness.** Linear/dB gain only — perceptual targets need `loudnorm`.
- **`atempo` is capped 0.5–100.0 per instance.** For 0.25x chain `atempo=0.5,atempo=0.5`; for 200x chain `atempo=10,atempo=10,atempo=2`.
- **`asetrate` alone changes pitch.** If you want speed without pitch, use `atempo`. `asetrate`+`aresample` resets SR but pitch is still shifted — combine with `atempo` to compensate.
- **`rubberband` filter requires a custom ffmpeg build.** Check `ffmpeg -filters | grep -i rubberband`. Most distro/Homebrew builds do not include it.
- **`-ar` on output ≠ `aresample` filter.** `-ar` is a global output option; filter-graph resampling must use `aresample` explicitly inside the graph.
- **`silenceremove` uses `stop_periods=-1`** (negative) to remove every silent region, not just the first.
- **`loudnorm` writes JSON to stderr**, mixed with progress lines. Parse the last `{...}` block, not the whole stream.
- **Loudness targets differ across platforms** — check `references/filters.md` before delivery.

## Examples

### Example 1: Normalize a podcast episode to -16 LUFS

```bash
# Pass 1 — measure
ffmpeg -hide_banner -i ep01.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json -f null - 2>measure.txt

# Pass 2 — apply (values plugged in from measure.txt JSON block)
ffmpeg -i ep01.wav -af \
"loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=-21.3:measured_LRA=8.2:\
measured_TP=-4.1:measured_thresh=-31.5:offset=-0.7:linear=true:print_format=summary" \
  -ar 48000 -c:a pcm_s24le ep01_norm.wav

# Verify
ffmpeg -i ep01_norm.wav -af ebur128=peak=true -f null - 2>&1 | tail -10
```

### Example 2: Sidechain-duck music under a voiceover

```bash
ffmpeg -i voice.wav -i music.wav -filter_complex \
"[0:a]asplit=2[vox][sc]; \
 [1:a][sc]sidechaincompress=threshold=-24dB:ratio=8:attack=5:release=250[ducked]; \
 [vox][ducked]amix=inputs=2:duration=longest:normalize=0[aout]" \
-map "[aout]" out.wav
```

### Example 3: 5.1 Dolby → stereo downmix

```bash
ffmpeg -i surround.wav -af \
"pan=stereo|c0=0.5*FL+0.707*FC+0.5*BL+0.5*SL|\
c1=0.5*FR+0.707*FC+0.5*BR+0.5*SR" -c:a pcm_s16le stereo.wav
```

### Example 4: Trim leading + trailing silence below -50 dB

```bash
ffmpeg -i raw.wav -af \
"silenceremove=start_periods=1:start_duration=0.3:start_threshold=-50dB:\
stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB" trimmed.wav
```

### Example 5: Speed to 0.25x (chain atempo)

```bash
ffmpeg -i in.wav -af atempo=0.5,atempo=0.5 slow.wav
```

## Troubleshooting

### Error: "Filter amix has an unconnected output" / "Impossible to convert between the formats"

Cause: inputs have different sample rates or channel layouts.
Solution: pre-normalize each input:
```
[0]aresample=48000,aformat=channel_layouts=stereo[a0];
[1]aresample=48000,aformat=channel_layouts=stereo[a1];
[a0][a1]amix=inputs=2:normalize=0[aout]
```

### Error: "Value 4.000000 for parameter 'tempo' out of range [0.500000 - 2.000000]"

Older ffmpeg (<5.1) capped atempo at 2.0. Chain multiple instances:
`atempo=2.0,atempo=2.0` for 4x. Modern builds go to 100.

### Error: loudnorm output still sounds pumpy

Cause: single-pass mode (dynamic). Either you did not supply all
`measured_*` values, or `linear=true` was omitted. Double-check every
field from pass 1 JSON is present in pass 2.

### Error: "No such filter: 'rubberband'"

Cause: ffmpeg built without librubberband. Use `atempo` (keeps pitch)
or `asetrate` (changes pitch) instead, or install a build with
rubberband (e.g. `brew install ffmpeg` usually does NOT include it;
build from source with `--enable-librubberband`).

### Error: output file has 0 channels / silent

Cause: `pan` expression referenced a channel that does not exist in
the layout (e.g. `BL` on a stereo source). Use `ffprobe` to confirm
input channel_layout before writing the pan map.

### Error: amix output is half as loud as expected

Cause: default `normalize=1` scales by 1/N. Add `:normalize=0`.
