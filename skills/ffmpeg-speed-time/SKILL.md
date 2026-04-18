---
name: ffmpeg-speed-time
description: >
  Speed ramps, time remapping, and temporal effects with ffmpeg: setpts (variable PTS expressions), asetpts, minterpolate for motion-compensated slow-motion, reverse and areverse, tblend for frame blending, freezeframe, loop, tpad (temporal pad), setrate+atempo combos. Use when the user asks to slow down video, speed up, time-lapse, ramp speed up/down, do a speed ramp, reverse a clip, freeze the last frame, hold on a frame, loop a video, or do frame-blending slow-motion.
argument-hint: "[operation] [input]"
---

# Ffmpeg Speed Time

**Context:** $ARGUMENTS

## Quick start

- **Constant 2x speed (V+A):** → Step 1 → `speed` mode with factor 2.0
- **Smooth 0.25x slow-motion (motion-interpolated):** → Step 1 → `speed --smooth minterpolate --fps 120`
- **Reverse entire clip:** → Step 1 → `reverse` mode
- **Freeze last frame for 3s:** → Step 1 → `freeze --end 3`
- **Loop clip 5x:** → Step 1 → `loop --count 5`
- **Timelapse (keep every Nth frame):** → Step 1 → `timelapse --every 10`
- **Speed ramp 1x → 0.25x:** → Step 1 → `ramp` (splits + concats)

## When to use

- Slow a clip to 0.5x / 0.25x with either simple PTS scaling or smooth motion interpolation.
- Speed up a lecture/recording 2x–4x without pitching the voice up.
- Play a clip in reverse (visually and/or audio).
- Hold on the first or last frame for N seconds (title cards, outros).
- Ramp speed mid-clip (cinematic slow-down into a highlight).
- Loop a short clip, build a time-lapse, or freeze a mid-clip frame.

## Step 1 — Pick an operation

| Goal | Operation | Key filters |
|---|---|---|
| Constant speed, both V+A | `speed` | `setpts=K*PTS` + `atempo=1/K` |
| Smooth slow-motion | `speed --smooth minterpolate` | `minterpolate,setpts=...` |
| Play backwards | `reverse` | `reverse`, `areverse` |
| Hold first / last / mid frame | `freeze` | `tpad`, `apad`, `loop` |
| Repeat N times | `loop` | `loop`, `aloop` or concat demuxer |
| Timelapse (drop frames) | `timelapse` | `setpts=PTS/N,fps=X` |
| Variable-speed ramp | `ramp` | split → speed each → concat |

Decision shortcuts:

- **Pitch-preserving speed change** → always pair `setpts` with `atempo` (never `asetrate`).
- **Pitch-shift for effect (chipmunk / deep voice)** → `asetrate=48000*K,aresample=48000` (changes speed AND pitch).
- **Slow-mo below 0.5x and smooth motion matters** → `minterpolate` (slow render, but no juddery frame repeats).
- **Slow-mo below 0.5x and render speed matters** → plain `setpts` (frames simply held longer).
- **Reverse > ~60s clip** → split into chunks, reverse each, concat in reverse order (otherwise RAM explodes).

## Step 2 — Build the V+A filter graph

Speed change must apply to BOTH streams or video and audio drift. Core identity:

```
video: setpts = K * PTS    (K < 1 → faster, K > 1 → slower)
audio: atempo = 1 / K      (must be inverse of K)
```

`atempo` per-instance range is **0.5 – 100.0**. For factors outside that range, chain:

```
0.25x  (K=4)   →  atempo=0.5,atempo=0.5
0.1x   (K=10)  →  atempo=0.5,atempo=0.5,atempo=0.4
4x     (K=0.25)→  atempo=2.0,atempo=2.0
8x     (K=0.125)→ atempo=2.0,atempo=2.0,atempo=2.0
```

### 2a. Constant speed (2x, pitch preserved)

```bash
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" \
  -map "[v]" -map "[a]" out.mp4
```

### 2b. Constant speed (0.5x, pitch preserved)

```bash
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" \
  -map "[v]" -map "[a]" out.mp4
```

### 2c. Smooth slow-motion 0.25x at 120 fps output

```bash
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=120',setpts=4.0*PTS[v];\
   [0:a]atempo=0.5,atempo=0.5[a]" \
  -map "[v]" -map "[a]" out.mp4
```

`minterpolate fps=` is the **OUTPUT fps** the filter generates synthesized frames at — independent of the `setpts` time-scaling that follows. Apply `setpts` AFTER `minterpolate`.

### 2d. Reverse (short clips only — buffers whole stream in RAM)

```bash
ffmpeg -i in.mp4 -vf reverse -af areverse out.mp4
```

### 2e. Freeze LAST frame 3s (V+A)

```bash
ffmpeg -i in.mp4 \
  -vf "tpad=stop_mode=clone:stop_duration=3" \
  -af "apad=pad_dur=3" \
  -shortest out.mp4
```

### 2f. Freeze FIRST frame 2s

```bash
ffmpeg -i in.mp4 \
  -vf "tpad=start_mode=clone:start_duration=2" \
  -af "adelay=2s:all=1" \
  out.mp4
```

### 2g. Mid-clip freeze (hold frame at t=5s for 2s, source is 30 fps)

Frame index = `5s * 30fps = 150`. Hold 2s = `2 * 30 = 60` extra frames:

```bash
ffmpeg -i in.mp4 -vf "loop=loop=60:size=1:start=150" -c:a copy out.mp4
```

### 2h. Loop entire clip 5x

```bash
ffmpeg -stream_loop 4 -i in.mp4 -c copy out.mp4
```

`-stream_loop 4` = play input 5 times total (0-based). Faster than `loop` filter when stream-copy works. Otherwise:

```bash
ffmpeg -i in.mp4 -filter_complex "[0:v]loop=loop=4:size=9999:start=0[v];[0:a]aloop=loop=4:size=2e9:start=0[a]" \
  -map "[v]" -map "[a]" out.mp4
```

### 2i. Timelapse — keep every 10th frame, output 30 fps

```bash
ffmpeg -i in.mp4 -vf "setpts=PTS/10,fps=30" -an out.mp4
```

or explicit frame selection:

```bash
ffmpeg -i in.mp4 -vf "select='not(mod(n,10))',setpts=N/FRAME_RATE/TB" -an out.mp4
```

### 2j. Pitch-shifted speed (chipmunk effect)

```bash
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]setpts=(2/3)*PTS[v];[0:a]asetrate=48000*1.5,aresample=48000[a]" \
  -map "[v]" -map "[a]" out.mp4
```

`asetrate` multiplies both playback rate and pitch (like tape speedup). Follow with `aresample` to restore the container's expected sample rate.

## Step 3 — Run and verify duration

Expected output duration:

```
new_duration = source_duration * K            (K from setpts=K*PTS)
```

Verify:

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 out.mp4
```

For speed 2x on a 60s source you should see `~30`. For 0.5x, `~120`. If the number disagrees, you probably forgot to match `setpts` with `atempo` or one of the audio chains exceeded per-instance range.

## Available scripts

- **`scripts/time.py`** — subcommand-based wrapper around the recipes above. Stdlib only. `--dry-run` prints the exact ffmpeg command.

```bash
# 2x speed
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py speed --input in.mp4 --output out.mp4 --factor 2.0

# 0.25x smooth slow-mo at 120 fps
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py speed --input in.mp4 --output out.mp4 --factor 0.25 --smooth minterpolate --fps 120

# Reverse
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py reverse --input in.mp4 --output out.mp4

# Freeze last 3s
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py freeze --input in.mp4 --output out.mp4 --end 3

# Freeze mid-clip at t=5s for 2s
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py freeze --input in.mp4 --output out.mp4 --at 5 --duration 2

# Loop 5x
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py loop --input in.mp4 --output out.mp4 --count 5

# Timelapse
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py timelapse --input in.mp4 --output out.mp4 --every 10 --fps 30

# Ramp 1.0x → 0.25x starting at t=10s over 2s
uv run ${CLAUDE_SKILL_DIR}/scripts/time.py ramp --input in.mp4 --output out.mp4 --from 1.0 --to 0.25 --start-time 10 --duration 2
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for full option tables (setpts expressions, minterpolate modes, atempo vs asetrate, recipe gallery).

## Gotchas

- **`setpts` and `atempo` are independent.** Change video PTS without changing audio tempo and the two streams drift — 0.5x video over a 60s clip + untouched audio = 60s of video playing at half speed with only 60s of audio, so audio ends at the 50% mark (or the mux silently truncates one stream).
- **`atempo` range is 0.5–100.0 per instance.** For 0.25x chain `atempo=0.5,atempo=0.5`. For 4x chain `atempo=2.0,atempo=2.0`.
- **`setpts` scales ALL timestamps uniformly.** It cannot express "fast then slow" on its own. For variable speed, split the source into segments, speed-change each, then concat.
- **`reverse` and `areverse` buffer the entire stream in RAM.** A 10-minute 4K clip will OOM. Split first, reverse each chunk, concat chunks in reverse order.
- **`minterpolate` is expensive.** 1 fps render throughput is common at 1080p. Use on short clips (<30s) or pre-trim.
- **`minterpolate fps=X`** is the OUTPUT fps of the synthesis stage and is independent of the subsequent `setpts` time scaling. Setting `fps=120` does not itself slow the video — `setpts=4.0*PTS` after it does.
- **`tpad` can only pad, never trim.** To freeze the FIRST frame, `tpad=start_mode=clone:start_duration=N` on video PLUS matching audio delay (`adelay=Ns:all=1`) or silence pad (`apad=pad_dur=N` combined with a pre-rolled silent source).
- **Freezing the LAST frame needs matching audio pad.** Use `apad=pad_dur=N` alongside the video `tpad`. Without it, audio ends early and `-shortest` truncates the frozen video back.
- **`loop` filter is VIDEO only.** Use `aloop` for audio, or prefer `-stream_loop N` at the input level when stream copy is viable.
- **`select` + `setpts=N/FRAME_RATE/TB`** is the portable idiom for dropping frames. The `N/FRAME_RATE/TB` rewrites the N-th surviving frame's PTS to the correct integer tick; without it, output timestamps will be garbage.
- **`asetpts=N/SR/TB`** is the audio equivalent (SR = sample rate), used after `aselect`.
- **`asetrate` changes pitch AND speed.** Use `atempo` for pitch-preserving speed. Use `asetrate` only when you WANT the pitch shift (chipmunk, demonic slowdown).
- **Dropping frames via `fps=10`** is lossy — you throw away the intervening frames entirely. For smooth slow-down from existing frames, use `minterpolate` instead.
- **Pixel format after `minterpolate` may need forcing.** Append `,format=yuv420p` before encoding for broad MP4 compatibility.
- **`loop=size=` is a MAX frame count to buffer for the loop.** Set it to a value larger than your clip's frame count (`9999` for short clips; use `2e9` cap on `aloop` since it counts samples).
- **Output duration can drift with variable-frame-rate sources.** Force `-vsync cfr` or a `fps=` filter early if downstream tools require constant frame rate.

## Examples

### Example 1: 2x lecture speed with natural-sounding audio

```bash
ffmpeg -i lecture.mp4 \
  -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 20 -c:a aac -b:a 128k \
  lecture_2x.mp4
```

Duration of a 60-minute lecture → ~30 minutes. Audio remains at original pitch because `atempo` preserves it.

### Example 2: Cinematic 0.25x slow-mo of a 5-second action shot

```bash
ffmpeg -i hit.mp4 -filter_complex \
  "[0:v]minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=120',setpts=4.0*PTS,format=yuv420p[v];\
   [0:a]atempo=0.5,atempo=0.5[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset slow hit_slowmo.mp4
```

5s input → 20s output at 120 fps with synthesized intermediate frames.

### Example 3: Freeze last frame 3s for an outro

```bash
ffmpeg -i clip.mp4 \
  -vf "tpad=stop_mode=clone:stop_duration=3" \
  -af "apad=pad_dur=3" \
  -shortest -c:v libx264 -crf 20 -c:a aac \
  clip_outro.mp4
```

### Example 4: Speed ramp 1x → 0.25x

```bash
# Split at t=10 and t=12, speed-change middle chunk, concat
ffmpeg -i in.mp4 -t 10 -c copy seg1.mp4
ffmpeg -i in.mp4 -ss 10 -to 12 -filter_complex \
  "[0:v]setpts=4.0*PTS[v];[0:a]atempo=0.5,atempo=0.5[a]" \
  -map "[v]" -map "[a]" seg2.mp4
ffmpeg -i in.mp4 -ss 12 -c copy seg3.mp4
printf "file 'seg1.mp4'\nfile 'seg2.mp4'\nfile 'seg3.mp4'\n" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy ramped.mp4
```

(Concat-copy requires same codec params in all three; re-encode the concat step if needed. `scripts/time.py ramp` automates this.)

### Example 5: Timelapse, 1 frame every 10 → 30 fps output

```bash
ffmpeg -i timelapse_src.mp4 -vf "setpts=PTS/10,fps=30" -an timelapse.mp4
```

## Troubleshooting

### Error: `Value X for parameter 'tempo' out of range [0.5 - 100]`

Cause: `atempo` instance fed a factor outside its single-stage range.
Solution: Chain stages: `atempo=0.5,atempo=0.5` for 0.25x; `atempo=2.0,atempo=2.0` for 4x.

### Output has audio but no video after `setpts` change

Cause: You forgot to `-map "[v]"` — ffmpeg picked a default video stream from the input, not the filtered one.
Solution: Explicit `-map "[v]" -map "[a]"` when using `-filter_complex` with named outputs.

### `minterpolate` runs at 0.5 fps and never finishes

Cause: Expected — minterpolate is CPU-heavy at high resolutions.
Solution: Downscale first (`scale=1280:-2`) or trim the clip before interpolating. No GPU path for minterpolate; only CPU.

### Reverse command killed / OOM

Cause: `reverse`/`areverse` buffer the entire stream in RAM (uncompressed frames).
Solution: Split into 5–10 second segments, reverse each, concat in reverse order of segments.

### Freeze-frame on last frame produces a frozen video with early-cutting audio

Cause: `tpad` extends video but `-shortest` or missing `apad` caps duration at the audio end.
Solution: Add `-af "apad=pad_dur=N"` matching the `stop_duration`, and keep `-shortest` (or drop it).

### Audio and video drift after speed change

Cause: Only one of `setpts`/`atempo` was applied, or `atempo` factor is not `1/K`.
Solution: Verify: `setpts=K*PTS` pairs with `atempo=1/K`. Check `ffprobe` duration of output vs `source_duration * K`.

### Loop filter output is only one iteration

Cause: `loop=size=` was smaller than the clip's frame count, so only the first `size` frames got looped.
Solution: Set `size` greater than total frame count (`9999` for short clips), or prefer `-stream_loop N` at the input level.
