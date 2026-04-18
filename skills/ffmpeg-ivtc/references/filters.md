# IVTC / Deinterlace / Frame-Rate Filter Reference

Exhaustive options for every filter in this skill's scope, verified against the ffmpeg 7.x docs (ffmpeg.org/ffmpeg-filters.html). Use this when you need to tune beyond the canonical recipes in SKILL.md.

---

## 3:2 pulldown (telecine) in 30 seconds

Film shoots at 24 fps. NTSC broadcasts at ~30 fps (actually 30000/1001 = 29.97). The frame-rate gap is bridged by **3:2 pulldown**: every 4 film frames A B C D become 5 video frames laid out as fields:

```
Film:     A     B     C     D
Fields:  At Ab Bt Bb Bt Ct Cd Dt Db  (9 fields)
  ->    AA   BB   BC   CD   DD       (5 video frames, 2 of which are combed)
```

Top-field-first with pattern `23` means: 2 progressive frames, then 3 progressive frames, alternating. Inverse telecine (IVTC) reverses this: it rebuilds ABCD from fields while dropping the two combed "dup" frames → 23.976p.

```
video frames: A  A  B  B  B  C  C  D  D  (after field-match)
              ↓ decimate 1-in-5 ↓
film frames:  A     B     C     D
```

Three filters handle this: `fieldmatch` (match fields to rebuild clean frames), `yadif=deint=interlaced` (fallback for genuinely combed ones), `decimate` (drop the duplicates).

---

## Pattern detection with `idet`

`idet` analyses up to N frames and reports field characteristics. Run with `-frames:v 500` minimum; 1000–2000 is safer on varied sources. Output buckets:

| Bucket           | Meaning                                                        |
| ---------------- | -------------------------------------------------------------- |
| Single frame     | Per-frame verdict (less reliable; only looks at 1 frame).      |
| Multiple frame   | Uses classification history — trust this.                      |
| Repeated Fields  | Count of fields that match adjacent frame's field (= telecine) |

Classification map:

| `multiple` distribution                       | Repeated                        | Verdict                          |
| --------------------------------------------- | ------------------------------- | -------------------------------- |
| Progressive ~100%, TFF/BFF <5%                | Neither ~100%                   | **Progressive**, do nothing.     |
| TFF or BFF >95%, Progressive <5%              | Neither ~100%                   | **True interlaced** → deinterlace. |
| TFF/BFF ~60%, Progressive ~40%                | Top+Bottom ~40%                 | **Hard-telecined 3:2** → IVTC.   |
| Progressive ~100%, non-trivial Repeated       | Top+Bottom ~40%                 | **Soft-telecined** → `repeatfields` or decode & re-encode. |
| Mixed, Undetermined >10%                      | —                               | **Mixed / dirty** → dejudder+fieldmatch+yadif fallback. |

---

## Per-filter option tables

### 11.93 `fieldmatch` (IVTC field matcher)

| Option      | Values                                                | Default | Notes                                                                 |
| ----------- | ----------------------------------------------------- | ------- | --------------------------------------------------------------------- |
| `order`     | `auto`, `bff`, `tff`                                  | `auto`  | Trust the container only if `idet` agrees. Set explicitly on dirty sources. |
| `mode`      | `pc`, `pc_n`, `pc_u`, `pc_n_ub`, `pcn`, `pcn_ub`      | `pc_n`  | `pc_n_ub` = slowest/safest; `pc` = fastest. Trade jerkiness vs. combing. |
| `ppsrc`     | `0`, `1`                                              | `0`     | `1` marks input 1 as a pre-processed filter source (for noise reduction); use a 2nd input as the clean source. |
| `field`     | `auto`, `bottom`, `top`                               | `auto`  | Which field to match FROM. Keep same as `order` unless matching fails. |
| `mchroma`   | `0`, `1`                                              | `1`     | Disable to speed up, or if chroma is rainbow-y.                        |
| `y0`, `y1`  | int line numbers                                      | `0`,`0` | Exclusion band — ignore lines between these for matching decision (mask out logos/subs). |
| `scthresh`  | float 0.0–100.0                                       | `12.0`  | Scene-change threshold (% max luma change). Relevant for `combmatch=sc`. |
| `combmatch` | `none`, `sc`, `full`                                  | `sc`    | `full` = always use combed scores in deciding matches. Most robust.    |
| `combdbg`   | `none`, `pcn`, `pcnub`                                | `none`  | Force calculation of combed metrics for listed matches and log them.   |
| `cthresh`   | int −1 to 255                                         | `9`     | Combing detection sensitivity (per-pixel). `[8, 12]` is typical.       |
| `chroma`    | `0`, `1`                                              | `0`     | Include chroma in combed-frame detection. Disable on rainbowy chroma.  |
| `blockx`    | power-of-2, 4–512                                     | `16`    | X-axis block size for combed detection.                                |
| `blocky`    | power-of-2, 4–512                                     | `16`    | Y-axis block size.                                                     |
| `combpel`   | int 0 to `blockx*blocky`                              | `80`    | Combed-pixel threshold per block. Known as MI in TFM/VFM.              |

**Must be followed by `decimate` for a full IVTC.** Optional fallback deinterlacer `yadif=deint=interlaced` between them handles frames fieldmatch couldn't reconstruct.

### 11.56 `decimate` (drop duplicated frames at regular intervals)

| Option      | Type     | Default | Notes                                                                |
| ----------- | -------- | ------- | -------------------------------------------------------------------- |
| `cycle`     | int      | `5`     | Drop 1 of every N. `5` is the 30→24 ratio. `2` halves fps.            |
| `dupthresh` | float    | `1.1`   | Diff-metric below which a frame is "duplicate".                      |
| `scthresh`  | float    | `15`    | Scene-change threshold.                                              |
| `blockx`    | pow2     | `32`    | Metric block size.                                                   |
| `blocky`    | pow2     | `32`    | Metric block size.                                                   |
| `ppsrc`     | `0`/`1`  | `0`     | Mark main input as pre-processed, use 2nd input as clean source.     |
| `chroma`    | `0`/`1`  | `1`     | Include chroma in metrics.                                           |
| `mixed`     | bool     | `false` | Enable for partial-decimation sources; **forces VFR output**.        |

Requires CFR input; see the fieldmatch doc note about `dejudder,fps=30000/1001,fieldmatch,decimate` for VFR → CFR pre-conditioning.

### 11.202 `pullup` (stateless pulldown reversal)

| Option             | Values              | Default | Notes                                                                  |
| ------------------ | ------------------- | ------- | ---------------------------------------------------------------------- |
| `jl`, `jr`         | int × 8 pixels      | `8`     | Junk to ignore on left/right (pixels).                                 |
| `jt`, `jb`         | int × 2 lines       | `8`     | Junk to ignore on top/bottom (lines).                                  |
| `sb`               | `-1`, `0`, `1`      | `0`     | Strict breaks. `1` = fewer bad matches but more drops; `-1` = looser. |
| `mp`               | `l`, `u`, `v`       | `l`     | Metric plane: luma / chroma-U / chroma-V. Chroma is faster but less accurate. |

Follow with `fps=24000/1001` (NTSC film) or `fps=24` (rare 30p-telecined source) to get CFR output.

### 11.67 `detelecine` (exact inverse of `telecine`)

| Option        | Values                     | Default | Notes                                                    |
| ------------- | -------------------------- | ------- | -------------------------------------------------------- |
| `first_field` | `top`/`t`, `bottom`/`b`    | `top`   | Must match whatever `telecine` was called with.          |
| `pattern`     | string of digits (e.g. 23) | `23`    | Pulldown pattern. Classic NTSC 3:2 = `23`.               |
| `start_frame` | int                        | `0`     | Pattern phase offset (if source was cut mid-pattern).    |

Use only when you know the exact forward `telecine` pattern that was applied (e.g. reversing a filter-chain test). Prefer `fieldmatch` / `pullup` for unknown sources.

### 11.171 `mpdecimate` (drop near-identical frames)

| Option | Type  | Default  | Notes                                                               |
| ------ | ----- | -------- | ------------------------------------------------------------------- |
| `max`  | int   | `0`      | Max consecutive drops (pos) or min interval between drops (neg).    |
| `keep` | int   | `0`      | Max consecutive similar-frames-ignored before dropping starts.      |
| `hi`   | int   | `64*12`  | 8×8 block diff threshold for "no block exceeds this".               |
| `lo`   | int   | `64*5`   | 8×8 block diff threshold paired with `frac`.                        |
| `frac` | float | `0.33`   | Fraction of blocks required to differ by `lo`. Lower = more aggressive dropping. |

Produces VFR; always chain `setpts=N/FRAME_RATE/TB,fps=<target>` downstream and force `-vsync cfr`.

### 11.62 `dejudder`

| Option  | Type | Default | Notes                                                                          |
| ------- | ---- | ------- | ------------------------------------------------------------------------------ |
| `cycle` | int  | `4`     | `4` film→NTSC (24→30); `5` PAL→NTSC (25→30); `20` mixture; any int >1 OK.      |

Used upstream of IVTC or after pullup to settle fractional timing.

### 11.281 `w3fdif` (Weston 3-field deinterlacer)

| Option   | Values                     | Default   | Notes                                                                 |
| -------- | -------------------------- | --------- | --------------------------------------------------------------------- |
| `filter` | `simple`, `complex`        | `complex` | Coefficient set. `complex` = better but slower.                       |
| `mode`   | `frame`, `field`           | `field`   | Single-rate or double-rate (bob) output.                              |
| `parity` | `tff`, `bff`, `auto`       | `auto`    | Source field order. `auto` = decoder-reported, defaults to TFF if unknown. |
| `deint`  | `all`, `interlaced`        | `all`     | Process all frames, or only those flagged interlaced.                 |

### 11.84 `estdif` (edge-slope tracing deinterlacer)

| Option         | Values                               | Default | Notes                                           |
| -------------- | ------------------------------------ | ------- | ----------------------------------------------- |
| `mode`         | `frame`, `field`                     | `field` | Single/double rate.                             |
| `parity`       | `tff`, `bff`, `auto`                 | `auto`  | Field order.                                    |
| `deint`        | `all`, `interlaced`                  | `all`   | Scope.                                          |
| `rslope`       | int 1–15                             | `1`     | Edge-slope search radius.                       |
| `redge`        | int 0–15                             | `2`     | Edge-matching search radius.                    |
| `ecost`        | float                                | (depends on version) | Edge cost weight. Check `ffmpeg -h filter=estdif`. |
| `mcost`        | float                                | —       | Mid cost weight.                                |
| `dcost`        | float                                | —       | Distance cost weight.                           |
| `interp`       | `2p`, `4p`, `6p`                     | `4p`    | Interpolation tap count.                        |

### 11.138 `kerndeint` (Donald Graft's adaptive kernel deinterlacer)

| Option   | Type  | Range   | Default | Notes                                                  |
| -------- | ----- | ------- | ------- | ------------------------------------------------------ |
| `thresh` | int   | 0–255   | `10`    | Pixel-line processing tolerance. `0` = process everywhere. |
| `map`    | 0/1   | —       | `0`     | `1` paints processed pixels white (debug).             |
| `order`  | 0/1   | —       | `0`     | `1` swaps fields.                                      |
| `sharp`  | 0/1   | —       | `0`     | Extra sharpening.                                      |
| `twoway` | 0/1   | —       | `0`     | Twoway sharpening.                                     |

### 11.161 `mcdeint` (motion-compensation deinterlacer)

| Option   | Values                                        | Default | Notes                                                |
| -------- | --------------------------------------------- | ------- | ---------------------------------------------------- |
| `mode`   | `fast`, `medium`, `slow`, `extra_slow`        | `fast`  | Quality/speed. `extra_slow` uses multiple refs.      |
| `parity` | `0/tff`, `1/bff`                              | `bff`   | Field order.                                         |
| `qp`     | int                                           | `1`     | QP for internal encoder. Higher → smoother MVs.      |

**Requires 1-field-per-frame input.** Canonical chain: `yadif=mode=1,mcdeint`.

### 11.191 `phase` (delay one field by one frame time)

| Option | Values                                              | Default | Notes                                                                                                |
| ------ | --------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| `mode` | `t`, `b`, `p`, `a`, `u`, `T`, `B`, `A`, `U`         | —       | Lowercase: capture fixed, transfer fixed. Uppercase: capture fixed, transfer unknown (image analysis). |

- `t`: capture TFF, transfer BFF (delays bottom field).
- `b`: capture BFF, transfer TFF (delays top field).
- `p`: pass-through (documentation reference).
- `a`: capture by flag, transfer opposite.
- `u`: capture unknown, transfer opposite (image analysis).
- `T`, `B`: capture fixed, transfer unknown.
- `A`, `U`: full auto.

### 11.94 `fieldorder`

| Option  | Values        | Default | Notes                                                  |
| ------- | ------------- | ------- | ------------------------------------------------------ |
| `order` | `tff`, `bff`  | `tff`   | Only acts if stream is flagged interlaced.             |

Used to convert TFF ↔ BFF for PAL DV authoring (`bff`) or cleanup after capture.

### 11.92 `fieldhint`

| Option | Values                              | Default    | Notes                                                                  |
| ------ | ----------------------------------- | ---------- | ---------------------------------------------------------------------- |
| `hint` | file path                           | —          | One line per output frame: `top_src,bottom_src` (± interlaced/progressive tag). |
| `mode` | `absolute`, `relative`, `pattern`   | `absolute` | `pattern` loops the hint file when exhausted.                          |

External-driven field picking. Produce the hint file from an external analyzer (e.g. TIVTC in AviSynth).

### 11.212 `repeatfields`

No options. Honors the RFF (repeat-first-field) flag from the decoded video's ES headers and hard-repeats fields. Use on soft-telecined content to materialize the signaled pattern into actual frames.

### 11.274 `vfrdet`

No options. Analyzes PTS deltas and logs at end-of-stream: `VFR: <frac>` and `min/max/average` delta PTS. `<frac>` is the fraction of frames with non-standard delta PTS. `> 0.05` suggests real VFR.

### 11.135 `il` (deinterleave / interleave fields)

| Option                                    | Values                                              | Default | Notes                                                  |
| ----------------------------------------- | --------------------------------------------------- | ------- | ------------------------------------------------------ |
| `luma_mode`, `chroma_mode`, `alpha_mode`  | `none`, `deinterleave`/`d`, `interleave`/`i`        | `none`  | Per-plane action.                                      |
| `luma_swap`, `chroma_swap`, `alpha_swap`  | `0`, `1`                                            | `0`     | Swap field order.                                      |

### 11.223 `separatefields`

No options. Splits each frame into two half-height frames at 2× fps. Inverse: `weave`.

### 11.283 `weave`, `doubleweave`

| Option        | Values                  | Default | Notes                                                              |
| ------------- | ----------------------- | ------- | ------------------------------------------------------------------ |
| `first_field` | `top`/`t`, `bottom`/`b` | —       | Which input frame becomes the top-field of the output pair.         |

`weave` joins pairs of fields into frames (halves fps). `doubleweave` joins without halving rate.

### 11.255 `tinterlace` (progressive → interlaced)

| Option | Values                                                                                   | Default | Notes |
| ------ | ---------------------------------------------------------------------------------------- | ------- | ----- |
| `mode` | `merge`/`0`, `drop_even`/`1`, `drop_odd`/`2`, `pad`/`3`, `interleave_top`/`4`, `interleave_bottom`/`5`, `interlacex2`/`6`, `mergex2`/`7` | `merge` | See ffmpeg-filters docs for diagrams. |
| `flags`| `low_pass_filter`, `bypass_il`, `cvlpf`, `vlpf`                                          | (none)  | Vertical low-pass to reduce twitter.   |

**Direction is opposite of this skill's main purpose** — use only when authoring for an interlaced broadcast deliverable.

### 11.249 `telecine` (progressive → telecined)

| Option        | Values                     | Default | Notes                                                  |
| ------------- | -------------------------- | ------- | ------------------------------------------------------ |
| `first_field` | `top`/`t`, `bottom`/`b`    | `top`   | —                                                      |
| `pattern`     | digit string               | `23`    | 3:2 pulldown = `23`; Euro = `222222222223`; etc.       |

Included here because `detelecine` is its exact inverse — if you telecined with this, undo with `detelecine` using the same pattern.

### 11.134 `idet` (detect field type)

No options. Logs to stderr these counters:

- `Single frame detection: TFF / BFF / Progressive / Undetermined` counts.
- `Multi frame detection: TFF / BFF / Progressive / Undetermined` counts (USE THIS).
- Per-frame metadata: `lavfi.idet.single.current_frame`, `lavfi.idet.multiple.current_frame`, `lavfi.idet.repeated.current_frame`.
- End-of-stream `Repeated Fields: Neither / Top / Bottom`.

Run ≥500 frames. Not a filter you keep in production chains — it's analysis only.

### yadif / bwdif (covered in ffmpeg-video-filter skill)

Brief cross-reference:

- `yadif=mode=0:parity=-1:deint=0` — single-rate, auto parity, all frames.
- `yadif=mode=1` — bob (double-rate).
- `yadif=mode=0:deint=1` — only frames marked interlaced.
- `bwdif=mode=send_frame:parity=auto:deint=all` — higher-quality successor to yadif. `mode=send_field` for bob.

---

## IVTC recipe gallery

### Clean telecined NTSC DVD (most common case)

```text
fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate
```

End with `-r 24000/1001 -vsync cfr` to force CFR output.

### Dirty / mixed telecined broadcast capture

```text
dejudder=cycle=4,fps=30000/1001,fieldmatch=order=tff:combmatch=full:cthresh=8:combpel=60,yadif=deint=interlaced,decimate
```

`fps=30000/1001` forces CFR before decimation (required). Tightening `cthresh`/`combpel` catches more combed frames for yadif fallback.

### Soft telecine (flags say 3:2, pixels are progressive)

```text
# detect first — confirm multiple.progressive ~100%, repeated ~40%
# then either just re-encode (decoder honors RFF):
ffmpeg -i IN -c:v libx264 -crf 18 -r 24000/1001 OUT.mkv
# ... or explicitly materialize:
-vf "repeatfields"
```

### Known-pattern reversal (e.g. test file made with `telecine=pattern=23`)

```text
detelecine=pattern=23:first_field=top:start_frame=0
```

### Fast but fragile (no fallback)

```text
pullup,fps=24000/1001
```

### Duplicate-frame stripper for borked IVTC output

```text
mpdecimate=hi=768:lo=320:frac=0.33,setpts=N/FRAME_RATE/TB
```

### Hybrid anime (24p animation + 30i live-action bumpers)

```text
dejudder=cycle=4,fps=30000/1001,fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate=mixed=1
```

`decimate=mixed=1` allows partial decimation — output will be VFR unless you clamp with `-vsync cfr -r 24000/1001`.

### Field-order repair

```text
# PAL DV captured wrong way
fieldorder=bff

# PAL film with phase-inverted capture (content-derived)
phase=mode=u

# Known-BFF capture transferred as TFF
phase=mode=b
```

---

## Deinterlacer comparison

| Filter      | Type                    | Speed      | Quality            | Double-rate? | Notes                                                           |
| ----------- | ----------------------- | ---------- | ------------------ | ------------ | --------------------------------------------------------------- |
| `yadif`     | temporal/spatial hybrid | Fast       | Good baseline      | `mode=1`     | Standard. `yadif=0` single, `yadif=1` bob.                      |
| `bwdif`     | Yadif + w3fdif + cubic  | Fast       | Very good          | `send_field` | Modern default. Smoother motion than yadif.                     |
| `w3fdif`    | BBC Weston 3-field      | Medium     | Excellent (temporal) | `mode=field` | Use `filter=complex` coefficients.                              |
| `estdif`    | Edge-slope interpolation (spatial only) | Medium | Excellent detail | `mode=field` | Newest. No temporal — safe on scene cuts but no motion smoothing. |
| `kerndeint` | Donald Graft adaptive kernel | Fast  | Sharp              | No           | Single-field only. Crunchy but detailed.                        |
| `mcdeint`   | Motion-compensated      | VERY slow  | Best (archival)    | Inherent (needs yadif=1 feed) | Use only for restoration. Encodes internally to estimate MVs.   |
| `nnedi`     | Neural-net edge interp  | Slow       | Excellent          | via `field_rate=all` | Lives in `ffmpeg-denoise-restore` scope.                        |
| `qtgmc`     | VapourSynth only        | Slow       | Reference-quality  | Yes          | Use via VapourSynth demuxer (`ffmpeg-vapoursynth`).             |

**Default picks:**
- Real-time / throughput: `bwdif`.
- Static-detail priority: `estdif`.
- Archival / restoration: `qtgmc` (VapourSynth) or `mcdeint` (pure ffmpeg).
- Classic NTSC home video: `w3fdif=filter=complex`.

---

## VFR / CFR notes post-IVTC

- `fieldmatch,decimate` leaves output PTS following the original 29.97 timebase with holes where drops occurred. Muxers may see this as VFR.
- `setpts=N/FRAME_RATE/TB` rewrites PTS as `frame_index / frame_rate`, producing monotonic CFR timing.
- Force CFR at encode: `-vsync cfr -r 24000/1001` (or the new equivalent `-fps_mode cfr`).
- Streaming copy after IVTC is **never safe** — frame count and rate differ from source. Always re-encode.

---

## Common pitfalls

- **Running `decimate` before `fieldmatch`** — destroys reconstruction; the correct order is match → (optional yadif fallback) → decimate.
- **Forgetting `-vsync cfr`** — downstream encoders may complain about non-monotonic PTS.
- **Trusting the container field-order flag** — always cross-check with `idet` first.
- **Using `pullup` on mixed-cadence sources** — it's stateless and can't adapt to breaks; use `fieldmatch` with `combmatch=full` + `yadif=deint=interlaced` fallback.
- **Bobbing telecined content** — never useful. Bob is for true 50i/59.94i. IVTC telecined sources to 23.976p instead.
- **Deinterlacing progressive sources** — adds blur, ruins detail. Run `idet` first.
- **Mixing `-r` before `-i`** — that sets input rate (changes duration), not output. Use `-r` after `-i` or `fps=` in the filter chain.
