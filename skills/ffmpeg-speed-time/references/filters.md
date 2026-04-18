# Speed / Time-remapping Filter Reference

Complete options, expression vocabulary, quality-vs-cost trade-offs, and a
recipe gallery for the filters covered by `ffmpeg-speed-time`.

Upstream docs:

- [setpts / asetpts](https://ffmpeg.org/ffmpeg-filters.html#setpts_002c-asetpts)
- [minterpolate](https://ffmpeg.org/ffmpeg-filters.html#minterpolate)
- [reverse](https://ffmpeg.org/ffmpeg-filters.html#reverse)
- [areverse](https://ffmpeg.org/ffmpeg-filters.html#areverse)
- [tblend](https://ffmpeg.org/ffmpeg-filters.html#tblend)
- [tpad](https://ffmpeg.org/ffmpeg-filters.html#tpad)
- [loop](https://ffmpeg.org/ffmpeg-filters.html#loop-1)
- [atempo](https://ffmpeg.org/ffmpeg-filters.html#atempo)
- [Expression evaluation](https://ffmpeg.org/ffmpeg-utils.html#Expression-Evaluation)

---

## 1. `setpts` — rewrite video PTS

Input: a video stream. Output: same frames, new timestamps.

```
setpts=EXPR
```

| Constant name | Meaning |
|---|---|
| `PTS` | Input frame's presentation timestamp (in TB units) |
| `N`   | Frame count, starting at 0 |
| `TB`  | Output time base (inverse of tbr) |
| `STARTPTS` | PTS of first frame of the input |
| `STARTT` | `STARTPTS * TB` — first frame's time (seconds) |
| `T`   | `PTS * TB` — this frame's time (seconds) |
| `FRAME_RATE`, `FR` | Input frame rate |
| `RTCTIME`, `RTCSTART` | Wall-clock microseconds since epoch / start |
| `PREV_INPTS`, `PREV_OUTPTS`, `PREV_INT`, `PREV_OUTT` | Previous frame's pts/t |
| `INTERLACED`, `TOP_FIELD_FIRST` | 1 if applicable, else 0 |
| `S` | Sample rate (asetpts only) |
| `SR` | Sample rate (asetpts only) |

Common forms:

```
setpts=0.5*PTS        # 2x faster (halve timestamps)
setpts=2.0*PTS        # 0.5x (double timestamps)
setpts=PTS-STARTPTS   # reset first frame to t=0
setpts=PTS/10         # 10x speedup (timelapse-style)
setpts=N/FRAME_RATE/TB  # rebuild PTS from a zero-based frame counter
                         # (pair with select=... to drop frames)
setpts='if(lt(T,10), PTS, if(lt(T,12), PTS + (4-1)*PTS*(T-10)/2, 4*PTS))'
```

`setpts` CANNOT change frame count. It only changes display timestamps.
To drop frames use `select`/`fps`. To add frames use `minterpolate` or `fps`.

## 2. `asetpts` — audio analogue

```
asetpts=N/SR/TB
```

Rarely needed directly. Prefer `atempo` for tempo / `aresample` for sample-rate.
Use `asetpts` after `aselect` to renumber timestamps when dropping audio
samples/packets.

## 3. `atempo` — pitch-preserving audio speed

```
atempo=K     # K in [0.5, 100.0]
```

Out-of-range factors require chaining. Chain rules:

| Target | Chain |
|---|---|
| 0.1x | `atempo=0.5,atempo=0.5,atempo=0.4` |
| 0.25x | `atempo=0.5,atempo=0.5` |
| 0.5x | `atempo=0.5` |
| 2x | `atempo=2.0` |
| 4x | `atempo=2.0,atempo=2.0` |
| 8x | `atempo=2.0,atempo=2.0,atempo=2.0` |

Quality is acceptable up to ~4x; beyond that, use `rubberband` (external
library) or accept artifacts.

## 4. Speed vs pitch — which audio filter?

| Effect wanted | Filter | Notes |
|---|---|---|
| Speed change, preserve pitch | `atempo=K` | Chain for extremes |
| Speed change AND pitch change (chipmunk) | `asetrate=SR*K,aresample=SR` | Like vinyl speed-up |
| Pitch change, keep length | `rubberband=pitch=2^(semitones/12)` | External library |
| Sample-rate conversion only | `aresample=48000` | No speed change |
| Lower sample rate + speed up | `asetrate=SR/2` alone | Half speed + octave down |

`asetrate` directly sets the stream's sample rate metadata without resampling,
which is what shifts pitch. Follow it with `aresample` to restore the
container's expected SR.

## 5. `minterpolate` — motion-compensated frame interpolation

```
minterpolate=mi_mode=MODE:mc_mode=MC:me_mode=ME:me=ALG:
             search_param=N:vsbmc=0|1:fps=X:scd=none|fdiff:scd_threshold=F
```

| Option | Values | Description |
|---|---|---|
| `mi_mode` | `dup` / `blend` / `mci` | dup = repeat; blend = crossfade; mci = motion-compensated (best) |
| `mc_mode` | `obmc` / `aobmc` | overlapped / adaptive overlapped block MC (aobmc is smoother) |
| `me_mode` | `bidir` / `bilat` | bidirectional (default, 2-ref) or bilateral |
| `me` | `esa` / `tss` / `tdls` / `ntss` / `fss` / `ds` / `hexbs` / `epzs` / `umh` | motion estimation algorithm |
| `search_param` | int, default 32 | larger = slower + more accurate |
| `vsbmc` | 0/1 | variable-size block MC (improves moving edges) |
| `fps` | output fps | the rate minterpolate synthesizes AT |
| `scd` | `none` / `fdiff` | scene-change detection |
| `scd_threshold` | float | threshold for fdiff detector |

Quality vs cost table:

| `mi_mode` | Speed | Visual | Notes |
|---|---|---|---|
| `dup` | fastest | repeats — juddery | Not slow-mo, just retimed |
| `blend` | fast | crossfade "ghost" look | Good for soft slow-mo / motion blur |
| `mci` | slowest | smoothest | Real slow-motion; can produce warping artifacts on fast motion / occlusion |

Practical preset for "good enough" slow-mo:

```
minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=120'
```

Apply `setpts` AFTER `minterpolate` in the chain to time-scale. `fps=` is the
synthesis rate (frames generated per second of input) and is not itself a
slow-down.

## 6. `reverse` / `areverse`

```
reverse          # video
areverse         # audio
```

Buffers entire stream in RAM. For a 1080p30 video you need roughly
`W*H*3 bytes * fps * duration` = ~186 MB/s of uncompressed storage.
Long clips OOM.

Mitigation:

1. Split into N-second chunks with the segment muxer.
2. Reverse each chunk with `reverse,areverse`.
3. Concat in **reverse order** of segments.

## 7. `tblend` — temporal blend

```
tblend=all_mode=MODE:all_opacity=O
```

Modes (selected): `addition`, `and`, `average`, `burn`, `darken`, `difference`,
`divide`, `dodge`, `exclusion`, `extremity`, `glow`, `hardlight`, `linearlight`,
`lighten`, `multiply`, `negation`, `or`, `overlay`, `phoenix`, `pinlight`,
`reflect`, `screen`, `softlight`, `subtract`, `vividlight`, `xor`.

Recipes:

- Fake motion-blur slow-mo (no minterpolate cost):
  `tblend=all_mode=average,framerate=60,setpts=2.0*PTS`
- Ghost trail effect: `tblend=all_mode=lighten`
- Difference clip for motion detection: `tblend=all_mode=difference`

## 8. `tpad` — temporal padding

```
tpad=start=N                          # pad N frames at start (default black)
tpad=stop=N                           # pad N frames at end
tpad=start_duration=S:stop_duration=S # pad in seconds instead of frames
tpad=start_mode=add|clone             # add black frames, or clone first
tpad=stop_mode=add|clone              # ditto, at end
tpad=color=COLOR                      # pad color when mode=add
```

Audio analogue: `apad=pad_dur=S` / `apad=whole_dur=S`.

`tpad` cannot trim; if you need a freeze on the FIRST frame, combine
`tpad=start_mode=clone:start_duration=N` with an audio `adelay` or prefix
silence source.

## 9. `loop` / `aloop`

Video:
```
loop=loop=N:size=F:start=S
```

| Option | Meaning |
|---|---|
| `loop` | number of loops (0 = forever, -1 = until EOF) |
| `size` | max number of frames buffered to replay |
| `start` | frame index where the loop anchor starts |

Set `size` greater than your total frame count (`9999` is fine for short
clips). For freeze-frame-in-middle, set `size=1` and `start=FRAME_INDEX`.

Audio:
```
aloop=loop=N:size=SAMPLES:start=SAMPLE_OFFSET
```

`size` counts SAMPLES, not seconds. Cap at ~`2e9` to stay within INT32.

For simple whole-clip repeats prefer `-stream_loop N` at the ffmpeg input
level — no re-encode needed.

## 10. `select` / `aselect` — drop frames/samples

```
select='not(mod(n,10))',setpts=N/FRAME_RATE/TB    # keep every 10th frame
aselect='not(mod(n,2))',asetpts=N/SR/TB           # keep every 2nd sample packet
```

The `setpts=N/FRAME_RATE/TB` (and `asetpts=N/SR/TB`) is mandatory —
without it the surviving frames keep their original PTS values and playback
is wrong.

## 11. `fps`

```
fps=30
fps=fps=60:round=near
```

Used for simple resampling (duplicate or drop frames to hit target fps) — no
motion interpolation. Pair with `setpts` when building a timelapse or a
constant-fps output from a VFR source.

---

## 12. Expression language quick reference

Functions available inside setpts/asetpts expressions:

| Category | Functions |
|---|---|
| Arithmetic | `+ - * / ^ %` |
| Comparison | `lt(x,y)`, `lte`, `gt`, `gte`, `eq`, `ne` |
| Logical | `not(x)`, `and(x,y)`, `or(x,y)`, `if(c,t,e)`, `ifnot` |
| Trig | `sin, cos, tan, asin, acos, atan, atan2(y,x), sinh, cosh, tanh` |
| Rounding | `floor, ceil, round, trunc` |
| Min/max | `min(a,b), max(a,b), clip(x,lo,hi)` |
| Misc | `abs, exp, log, sqrt, hypot(a,b), mod(a,b), pow(a,b)` |
| Piecewise | `between(x,lo,hi)`, `lerp(a,b,t)`, `smoothstep(x,lo,hi)` |

---

## 13. Recipe gallery

### 13.1 Timelapse (keep every 10th frame, render at 30 fps)

```bash
ffmpeg -i src.mp4 -vf "setpts=PTS/10,fps=30" -an timelapse.mp4
```

Or explicit dropping:

```bash
ffmpeg -i src.mp4 -vf "select='not(mod(n,10))',setpts=N/FRAME_RATE/TB" -an timelapse.mp4
```

### 13.2 Bullet-time 0.25x smooth slow-mo

```bash
ffmpeg -i hit.mp4 -filter_complex \
  "[0:v]minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:fps=120',setpts=4.0*PTS,format=yuv420p[v];\
   [0:a]atempo=0.5,atempo=0.5[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset slow out.mp4
```

### 13.3 Reverse flip

```bash
ffmpeg -i in.mp4 -vf reverse -af areverse out_rev.mp4
```

For long clips, chunked approach:

```bash
# Split to 10s chunks, reverse each, concat in reverse order
ffmpeg -i in.mp4 -c copy -f segment -segment_time 10 part_%03d.mp4
for f in $(ls -r part_*.mp4); do
  ffmpeg -i "$f" -vf reverse -af areverse "rev_$f"
done
printf "file 'rev_%s'\n" $(ls rev_part_*.mp4) > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy out_rev.mp4
```

### 13.4 Seamless loop — palindrome boomerang

```bash
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]split=2[v1][v2];[v2]reverse[v2r];[v1][v2r]concat=n=2:v=1:a=0[v];\
   [0:a]asplit=2[a1][a2];[a2]areverse[a2r];[a1][a2r]concat=n=2:v=0:a=1[a]" \
  -map "[v]" -map "[a]" boomerang.mp4
```

### 13.5 Ken-Burns still + freeze + zoompan

```bash
ffmpeg -loop 1 -i photo.jpg -t 6 \
  -vf "zoompan=z='min(zoom+0.0015,1.3)':d=150:s=1920x1080,format=yuv420p" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p out.mp4
```

### 13.6 Freeze LAST frame 3s (V+A)

```bash
ffmpeg -i in.mp4 \
  -vf "tpad=stop_mode=clone:stop_duration=3" \
  -af "apad=pad_dur=3" \
  -shortest out.mp4
```

### 13.7 Freeze FIRST frame 2s (V+A)

```bash
ffmpeg -i in.mp4 \
  -vf "tpad=start_mode=clone:start_duration=2" \
  -af "adelay=2000:all=1" \
  out.mp4
```

### 13.8 Mid-clip freeze (hold at 5s for 2s, 30 fps source)

```bash
ffmpeg -i in.mp4 -vf "loop=loop=60:size=1:start=150" -c:a copy out.mp4
```

### 13.9 Frame-blended fake slow-mo (no minterpolate cost)

```bash
ffmpeg -i in.mp4 -vf "tblend=all_mode=average,setpts=2.0*PTS" out.mp4
```

### 13.10 Chipmunk voice (speed + pitch up)

```bash
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]setpts=(2/3)*PTS[v];[0:a]asetrate=48000*1.5,aresample=48000[a]" \
  -map "[v]" -map "[a]" chipmunk.mp4
```

### 13.11 Demonic slow voice (speed + pitch down)

```bash
ffmpeg -i in.mp4 \
  -filter_complex "[0:v]setpts=2*PTS[v];[0:a]asetrate=48000*0.5,aresample=48000[a]" \
  -map "[v]" -map "[a]" demon.mp4
```

---

## 14. Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| Audio ends early | Only `setpts` applied, not `atempo` | Add matching `atempo=1/K` |
| `atempo out of range` | Factor < 0.5 or > 100 | Chain `atempo=0.5,atempo=0.5` etc |
| Reverse OOMs | Whole-stream buffer | Chunk + per-chunk reverse + reverse-concat |
| minterpolate too slow | Expensive by design | Trim, downscale first, or switch to `tblend` |
| Mid-freeze hits wrong frame | Frame index math wrong | `frame = time_sec * fps_numerator / fps_denominator` |
| Timelapse timestamps garbled | Missing `setpts=N/FRAME_RATE/TB` after `select` | Add it |
| Output fps not constant | VFR source | Add `fps=30` early in chain or use `-vsync cfr` |
| Output silent | `-map` dropped the filtered audio | Explicit `-map "[a]"` |
| Playback stutter after minterpolate | Non-standard pixel format | Append `,format=yuv420p` |
| `-stream_loop` doesn't loop | Muxer can't rewind (pipe input) | Use `loop` filter instead |
