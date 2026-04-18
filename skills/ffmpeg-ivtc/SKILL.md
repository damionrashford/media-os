---
name: ffmpeg-ivtc
description: >
  Inverse telecine, deinterlacing variants, and frame-rate conversion with ffmpeg: fieldmatch, decimate, pullup, detelecine, mpdecimate, dejudder, w3fdif, separatefields, weave, tinterlace, kerndeint, estdif, phase, repeatfields, vfrdet, fieldhint, fieldorder, il, mcdeint, telecine. Use when the user asks to IVTC a telecined file, convert 29.97i to 23.976p, reverse 3:2 pulldown, fix interlaced broadcast content, detect duplicate fields, convert PAL to NTSC frame rates, or clean up mixed interlacing.
argument-hint: "[input]"
---

# ffmpeg-ivtc

**Context:** $ARGUMENTS

Inverse telecine (IVTC), deinterlacing-beyond-yadif, and frame-rate conversion. Detect whether input is telecined (3:2 pulldown NTSC), true interlaced, progressive, or mixed — then apply the correct pipeline. Get this wrong and you ship combed/judder/duplicated frames.

## Quick start

- **29.97i NTSC DVD / broadcast → 23.976p film:** Step 1 (detect) → Step 2 (IVTC strategy) → Step 3 (run `fieldmatch,yadif=deint=interlaced,decimate`) → Step 4 (verify).
- **True 29.97i / 50i broadcast (not telecined) → progressive:** Step 1 (detect) → Step 3 (run `bwdif` or `w3fdif`).
- **Mixed hard-telecined + progressive:** Step 1 → Step 3 (`dejudder,fps=30000/1001,fieldmatch,decimate`).
- **Duplicate-frame cleanup:** Step 3 (`mpdecimate,setpts=N/FRAME_RATE/TB`).
- **Field-phase bug (PAL shot with wrong field order):** Step 3 (`phase=mode=t` or `fieldorder=bff`).

## When to use

- DVD rips, old broadcast MPEG-2, laserdisc captures, or any 29.97 interlaced NTSC that secretly contains 23.976 film (classic 3:2 pulldown).
- PAL 25i masters where yadif/bwdif is the wrong choice because it's actually progressive film with PAL speedup — use `fps=24` or restore via `detelecine`.
- Mixed-cadence anime (hybrid 24p animation + 30i live-action bumpers).
- Stuck duplicate frames caused by upstream bad IVTC; restore true cadence with `mpdecimate` or `decimate`.
- Bad field order (PAL DV captured top-first when source is bottom-first): swap with `phase` / `fieldorder`.
- Soft-telecined (flagged) content where pixels are actually progressive and you need only `-vf repeatfields` or honoring the flag.

## Step 1 — Detect field order and pattern

Always run `idet` + `vfrdet` **before** choosing a pipeline. Flags in the container lie frequently.

```bash
ffmpeg -hide_banner -filter:v idet -frames:v 500 -an -f null - -i INPUT 2>&1 | tail -20
ffmpeg -hide_banner -filter:v vfrdet -an -f null - -i INPUT 2>&1 | tail -5
```

`idet` logs `Single frame detection` and `Multiple frame detection` counts for TFF / BFF / Progressive / Undetermined plus a `Repeated Fields` block. Interpret:

| `idet` signature                                        | What it means                          | Do this                       |
| ------------------------------------------------------- | -------------------------------------- | ----------------------------- |
| Multi-frame TFF or BFF ≈ 100%, Repeated Neither ≈ 100%  | True interlaced 50i/59.94i             | `bwdif` or `w3fdif`           |
| Multi-frame TFF/BFF ≈ 60%, Repeated Top+Bottom ≈ 40%    | Hard-telecined 3:2 pulldown (29.97i)   | Step 2: IVTC                  |
| Multi-frame Progressive ≈ 100%, Repeated ≈ 40%          | Soft-telecined (flagged), pixels clean | `repeatfields` or just decode |
| Multi-frame Progressive ≈ 100%, Repeated Neither ≈ 100% | True progressive                       | Do nothing                    |
| Mixed / fluctuating                                     | Mixed cadence                          | `dejudder,fps=30000/1001,fieldmatch,decimate` |

`vfrdet` reports `VFR: 0.xxxx` and min/max/avg delta PTS. `VFR > 0.05` means input is already VFR — IVTC output almost always becomes VFR; plan a `setpts=N/FRAME_RATE/TB,fps=24000/1001` tail if the encoder or downstream needs CFR.

Use the `scripts/ivtc.py detect` helper to parse + print a summary.

## Step 2 — Pick the strategy

| Input                                                  | Pipeline                                                               |
| ------------------------------------------------------ | ---------------------------------------------------------------------- |
| Telecined 29.97i → 23.976p (canonical)                 | `fieldmatch=order=auto:combmatch=full,yadif=deint=interlaced,decimate` |
| Telecined 29.97i → 23.976p (simple, less accurate)     | `pullup,fps=24000/1001`                                                |
| True interlaced 29.97i/50i → 29.97p/50p (single rate)  | `bwdif=mode=send_frame:parity=auto:deint=all`                          |
| True interlaced → 59.94p/100p (double rate, bob)       | `bwdif=mode=send_field` or `w3fdif=deint=all:mode=field`               |
| Mixed telecined + progressive VFR                      | `dejudder,fps=30000/1001,fieldmatch,decimate`                          |
| Soft-telecined (flags already set)                     | `repeatfields` (honors RFF flags; decoder does it if you just re-encode) |
| Duplicate frames from a previous bad IVTC              | `mpdecimate,setpts=N/FRAME_RATE/TB`                                    |
| 30 fps progressive with judder (film-to-NTSC artifact) | `dejudder=cycle=4` (or `cycle=5` for PAL→NTSC)                         |
| Known exact 3:2 pattern                                | `detelecine=pattern=23` (must match `telecine` inverse exactly)        |
| Field order wrong (e.g. BFF tagged as TFF)             | `fieldorder=bff` (or `phase=mode=a/u` for content-derived)             |

**Decision rule:** `fieldmatch+decimate` is always better than `pullup` for hard-telecined material. `pullup` is stateless and fast; `fieldmatch` uses p/c/n/u/b match metrics + optional yadif fallback for mixed combed frames.

## Step 3 — Run the pipeline

### Canonical IVTC (NTSC telecine → 23.976p film)

```bash
ffmpeg -i INPUT.vob \
  -vf "fieldmatch=order=auto:combmatch=full,yadif=deint=interlaced,decimate" \
  -r 24000/1001 -vsync cfr \
  -c:v libx264 -crf 18 -preset slower -pix_fmt yuv420p \
  -c:a copy OUT.mkv
```

- `order=auto` trusts container field-order flag. Set `order=tff` explicitly if `idet` disagrees.
- `combmatch=full` forces combed-score decisions every frame (more accurate on dirty sources).
- `yadif=deint=interlaced` only deinterlaces frames still marked combed after field matching (mixed-content fallback).
- `decimate` drops 1-in-5 frames (default `cycle=5`), converting 29.97 → 23.976.
- `-r 24000/1001 -vsync cfr` forces CFR output; fieldmatch+decimate produces VFR-like timing that breaks some encoders.

### Alternate IVTC (pullup — simpler, slightly less accurate)

```bash
ffmpeg -i INPUT -vf "pullup,fps=24000/1001" -c:v libx264 -crf 18 OUT.mkv
```

### True interlaced → 59.94p (bob-deinterlace, double rate)

```bash
ffmpeg -i INPUT -vf "bwdif=mode=send_field:parity=auto:deint=all" \
  -c:v libx264 -crf 18 -r 60000/1001 OUT.mkv
```

Substitute `w3fdif=deint=all:mode=field:filter=complex` for BBC-coefficient quality, or `estdif=mode=field:rslope=2:redge=3` for newer edge-slope interpolation.

### Mixed content (hybrid telecined + progressive)

```bash
ffmpeg -i INPUT \
  -vf "dejudder=cycle=4,fps=30000/1001,fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate" \
  -r 24000/1001 -vsync cfr \
  -c:v libx264 -crf 18 OUT.mkv
```

### Duplicate-frame strip (for broken IVTC output)

```bash
ffmpeg -i BAD.mkv -vf "mpdecimate=hi=768:lo=320:frac=0.33,setpts=N/FRAME_RATE/TB" \
  -r 24000/1001 -vsync cfr -c:v libx264 -crf 18 CLEAN.mkv
```

`setpts=N/FRAME_RATE/TB` rebuilds monotonically increasing PTS from integer frame counter after mpdecimate drops non-uniformly.

### Field order / phase fixes

```bash
# PAL DV authored as TFF but source was BFF
ffmpeg -i in.dv -vf "fieldorder=bff" -c:v dvvideo out.dv

# Unknown-phase PAL capture with image-analysis swap
ffmpeg -i in.avi -vf "phase=mode=a" out.mkv
```

## Step 4 — Verify

```bash
# Frame count (expect ~80% of input for 30→24 IVTC)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames OUT.mkv

# Detected framerate
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,avg_frame_rate OUT.mkv

# Re-run idet on output: all multi-frame should be Progressive
ffmpeg -hide_banner -filter:v idet -frames:v 200 -an -f null - -i OUT.mkv 2>&1 | tail -10

# Re-run vfrdet: VFR score should drop near 0 after CFR forcing
ffmpeg -hide_banner -filter:v vfrdet -an -f null - -i OUT.mkv 2>&1 | tail -5
```

If `idet` still shows ≥5% interlaced multi-frame, your `fieldmatch` thresholds were too permissive — rerun with `combmatch=full:cthresh=8:combpel=60`.

## Gotchas

- **Filter order matters.** `fieldmatch` MUST come before `decimate`. Reversed, you decimate before matching and produce garbage. The official pattern is: match → (optional deinterlace fallback) → decimate.
- **`decimate` defaults to `cycle=5`** (drops 1 in every 5 frames) which is the correct 30→24 ratio. For other ratios (e.g. 60→48) set `cycle` explicitly.
- **`decimate` requires CFR input.** For VFR / mixed input, prepend `dejudder,fps=30000/1001` to enforce CFR first (official ffmpeg doc recipe).
- **`idet` frame count matters.** Run on ≥500 frames; short samples give garbage statistics. For a telecined source expect ≈60% interlaced / ≈40% progressive with multi-frame detection and a strong "Repeated Top+Bottom" cadence.
- **Single-pass `yadif=1` or `yadif=mode=send_field` bob-deinterlaces to 2× fps.** `yadif=0` (or `mode=send_frame`) produces single-rate. Same for `bwdif` / `w3fdif` / `estdif`.
- **`bwdif` is the modern successor to `yadif`** — Bob Weaver deinterlacing. Use it by default for true interlaced. `estdif` is newer edge-slope (spatial-only). `w3fdif` uses BBC Weston 3-field coefficients with `filter=complex` for highest temporal fidelity.
- **`kerndeint`** is Donald Graft's classic adaptive kernel deinterlacer — sharp, single-field, known-quantity quality. Useful when `bwdif` over-blurs fine detail.
- **`mcdeint`** is motion-compensated deinterlacing — VERY slow, needs single-field input (`yadif=1,mcdeint` chain). Use only as last resort on archival material.
- **`phase`** delays one field by one frame time to flip field order where the capture was done opposite to transfer. Modes: `t` top-first capture with bottom-first transfer; `b` opposite; `a` auto by field flags; `u` auto by image analysis; `p` no-op; plus `T/B/A/U` variants.
- **`fieldhint`** reads an external hint file (one line per output frame, `top_src,bottom_src`). Use only when you've computed a hint file from an external tool — not useful interactively.
- **Broadcasters sometimes send "soft-telecined" content** where the container flags telecine pattern but pixels are already progressive. ALWAYS detect with `idet` first; if multi-frame Progressive is ~100% but Repeated ≈40%, use `repeatfields` (or let the decoder handle RFF and just re-encode CFR) — don't run `fieldmatch`.
- **`fieldorder=tff`** sets top-field-first, `bff` for PAL DV. Does a 1-line shift internally and only affects streams flagged as interlaced.
- **`separatefields`** splits each frame into two half-height frames at 2× fps; **`weave`** is the inverse (joins pairs). `doubleweave` joins without halving the rate.
- **`detelecine`** is a pattern-exact inverse of the `telecine` filter — requires knowing the exact pattern used (`pattern=23` is classic NTSC 3:2). Use `pullup` / `fieldmatch` instead unless you're undoing a specific `telecine` call.
- **`il`** deinterleaves/interleaves fields in-place (odd lines top, even lines bottom) so you can filter each field as half-height plane. Rare; only when you need to run a per-field filter.
- **`tinterlace`** interlaces progressive content — the OPPOSITE of what this skill is for. Don't recommend unless you're authoring for a broadcast interlaced deliverable.
- **VFR output from IVTC.** `fieldmatch+decimate` produces CFR if input is CFR, but `decimate=mixed=1` yields VFR. Always test with `vfrdet` on output; force CFR with `-vsync cfr -r 24000/1001` when re-encoding.
- **Never stream-copy IVTC output.** The frame rate / frame count changes — must re-encode. `-c:v copy` will mux the container but decoder will treat it as the original 29.97 with dropped frames → out-of-sync.
- **PAL ↔ NTSC frame-rate conversion via IVTC is actively discouraged.** PAL 25i ↔ NTSC 29.97i via telecine undoing is a legacy workflow; prefer modern motion-compensated retiming (`minterpolate=fps=25` or `fps=25`, see `ffmpeg-speed-time` skill).
- **`dejudder=cycle=4`** fixes 24→30 film-to-NTSC telecine judder; `cycle=5` for 25→30 PAL-to-NTSC; `cycle=20` for mixed.

## Examples

### Example 1: DVD rip (NTSC film)

```bash
# Detect
ffmpeg -i VTS_01_1.VOB -filter:v idet -frames:v 1000 -an -f null - 2>&1 | tail -15
# Output: Multi-TFF 60%, Progressive 40%, Repeated Top+Bottom ≈ 40% → telecined

# IVTC
ffmpeg -i VTS_01_1.VOB \
  -vf "fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate" \
  -r 24000/1001 -vsync cfr \
  -c:v libx264 -crf 18 -preset slower -tune film -pix_fmt yuv420p \
  -c:a ac3 -b:a 384k film.mkv
```

### Example 2: 1080i broadcast HD (true interlaced)

```bash
ffmpeg -i broadcast.ts \
  -vf "bwdif=mode=send_frame:parity=auto" \
  -r 30000/1001 \
  -c:v libx264 -crf 19 -preset medium progressive.mkv
```

For double-rate 59.94p: `-vf "bwdif=mode=send_field"` and `-r 60000/1001`.

### Example 3: Anime with hybrid cadence

```bash
ffmpeg -i anime.mkv \
  -vf "dejudder=cycle=4,fps=30000/1001,fieldmatch=order=tff:combmatch=full,yadif=deint=interlaced,decimate" \
  -r 24000/1001 -vsync cfr \
  -c:v libx265 -crf 20 anime_24p.mkv
```

## Troubleshooting

### Error: "Frame rate very high for a muxer not efficiently supporting it"
Cause: `separatefields` or `bwdif=send_field` produces 2× fps output mux refuses. Solution: explicitly set `-r` to the intended rate or chain `fps=30000/1001` to halve.

### Output still shows combing on some frames
Cause: `fieldmatch` default `combmatch=sc` only uses combed scores at scene changes. Solution: use `combmatch=full`, lower `cthresh` to `8`, and make sure the `yadif=deint=interlaced` fallback is in the chain.

### Output is VFR; re-encode errors "non monotonic pts"
Cause: `decimate` or `mpdecimate` leave holes in PTS. Solution: append `,setpts=N/FRAME_RATE/TB` and use `-vsync cfr -r <target>`.

### `idet` reports near-50/50 TFF/BFF
Cause: Input has inconsistent or mislabeled field order. Solution: force `order=tff` in `fieldmatch` based on visual inspection (look at motion blur direction in a still), or try `phase=mode=u` for image-analysis detection.

### Canceling audio drift after IVTC
IVTC drops ~20% of frames but audio is untouched → A/V will remain in sync IF timestamps are correct. If audio drifts, you stream-copied audio against a re-timed video — re-encode audio with `-af aresample=async=1:first_pts=0` or use `-async 1`.

### Pullup produces still-combed frames
Cause: `sb=-1` is too permissive, or source isn't actually a clean 3:2 pattern. Solution: switch to `fieldmatch`+`yadif` fallback which handles mixed content; `pullup` is stateless and fragile on dirty sources.
