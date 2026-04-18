---
name: ffmpeg-synth
description: >
  Generate synthetic test media with ffmpeg lavfi sources: testsrc, testsrc2, smptebars, smptehdbars, rgbtestsrc, yuvtestsrc, allyuv, allrgb, colorchecker, color (solid), mandelbrot, cellauto, life, gradients, zoneplate, sine tone, anullsrc, anoisesrc. Use when the user asks to generate test bars and tone, create a calibration clip, make SMPTE color bars, generate a sine tone, output silence, create a test video, produce a solid-color background, generate 1 kHz reference tone, or build synthetic assets for pipeline testing.
argument-hint: "[source-type] [duration]"
---

# Ffmpeg Synth

**Context:** $ARGUMENTS

## Quick start

- **SMPTE HD bars + 1 kHz tone (10 s 1080p30):** `-f lavfi -i smptehdbars=... -f lavfi -i sine=...` → Step 3, recipe A
- **testsrc2 moving pattern + counter:** `-f lavfi -i testsrc2=size=1280x720:rate=30` → Step 3, recipe B
- **Solid color fill:** `-f lavfi -i color=c=red:size=1280x720:rate=30:duration=5` → Step 3, recipe C
- **Gradient background:** `-f lavfi -i "gradients=s=1920x1080:c0=red:c1=blue:speed=0.01"` → Step 3, recipe D
- **Mandelbrot zoom:** `-f lavfi -i mandelbrot=size=1920x1080:rate=30 -t 10` → Step 3, recipe E
- **Legacy PAL 75 % bars:** `-f lavfi -i pal75bars=size=720x576:rate=25 -t 10` → Step 3, recipe F
- **Silent stereo audio track:** `-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -t 10` → Step 3, recipe G
- **White / pink / brown noise:** `-f lavfi -i anoisesrc=color=pink:duration=10:amplitude=0.3` → Step 3, recipe H
- **Sine sweep tone:** `-f lavfi -i "sine=frequency=440:beep_factor=4:duration=10"` → Step 3, recipe I
- **Identity Hald CLUT PNG (for LUT authoring):** `-f lavfi -i haldclutsrc=level=8 -frames:v 1 hald.png` → Step 3, recipe J
- **colorchecker 24-patch PNG:** `-f lavfi -i colorchecker -frames:v 1 colorchecker.png` → Step 3, recipe K

## When to use

- Pipeline integration tests that must not depend on external media files.
- Broadcast calibration — SMPTE bars + -20 dBFS 1 kHz tone for line-up.
- ABX audio listening tests (white / pink / brown noise as reference).
- Encoder stress testing — high-entropy `rgbtestsrc` / `mandelbrot` / `testsrc2`.
- Overlay backgrounds — solid `color` or `gradients` as a plate for `drawtext`/`overlay`.
- LUT authoring — identity `haldclutsrc` round-tripped through a grading tool.
- Placeholder silence track to marry onto a video-only source.
- Monitor calibration / gamut checks — `pal100bars`, `smptehdbars`, `rgbtestsrc`.
- Not a playback preview tool — for interactive filter tweaks use `ffmpeg-playback`.
- For writing the synthetic video through a filter chain (drawtext overlay, LUT), see `ffmpeg-video-filter` and `ffmpeg-lut-grade`.

## Step 1 — Pick a source

All synthetic sources live inside `libavfilter` and are addressed via the `lavfi` input format. Choose by category:

| Category | Source | What it gives you |
| --- | --- | --- |
| Engineering test pattern | `testsrc` | Colored rects + frame number + test tone cue |
| Engineering test pattern | `testsrc2` | Like `testsrc`, plus a moving element and timecode |
| Broadcast bars | `smptebars` | SMPTE 75 % bars, pre-HD aspect (4:3-ish, 320×240 default) |
| Broadcast bars | `smptehdbars` | SMPTE HD 100 % bars (ARIB STD-B28 style) |
| Broadcast bars | `pal75bars` / `pal100bars` | PAL legacy 75 %/100 % bars |
| Gamut / primaries | `rgbtestsrc` | Pure RGB color field (tests full-range RGB path) |
| Gamut / primaries | `yuvtestsrc` | Pure YUV color field |
| Exhaustive color sweep | `allyuv` | Every Y×Cb×Cr triplet (256×256 per Y plane) |
| Exhaustive color sweep | `allrgb` | Every R×G×B triplet (4096×4096 image) |
| Reference swatches | `colorchecker` | 24-patch X-Rite / Macbeth chart |
| Solid fill | `color` | One color, parametric size/rate/duration |
| Math-art | `mandelbrot` | Zoomable Mandelbrot fractal |
| Math-art | `cellauto` | 1-D cellular automaton (Wolfram rules) |
| Math-art | `life` | Conway's Game of Life |
| Gradient | `gradients` | 2-color+ animated gradient |
| Engineering | `zoneplate` | Radial zone plate (aliasing / sharpening stress) |
| LUT authoring | `haldclutsrc` | Identity Hald CLUT at `level=N` → N³×N³ image |
| Audio tone | `sine` | Single sine (optionally beeping) |
| Audio silence | `anullsrc` | True digital silence |
| Audio noise | `anoisesrc` | White / pink / brown / blue / velvet noise |
| Audio expression | `aevalsrc` | Arbitrary sample expression (chirps, custom) |
| Audio TTS | `flite` | Synthetic speech (requires ffmpeg built with `--enable-libflite`) |

Probe whether your ffmpeg supports a given source before committing to it:

```bash
ffmpeg -hide_banner -sources lavfi 2>/dev/null   # list lavfi devices (sometimes empty)
ffmpeg -hide_banner -h filter=smptehdbars        # dump the options for one source
ffmpeg -hide_banner -filters | grep -E "smpte|testsrc|colorchecker"
```

## Step 2 — Build the lavfi input

Every lavfi source is an `-f lavfi -i <expression>` pair. The expression is **filter syntax, not a file path**:

```
-f lavfi -i "SOURCE=key1=val1:key2=val2:..."
```

Always quote the expression (colons and commas need protection in most shells). Key knobs:

- `size=WxH` (or `s=WxH`) — output frame size. Some sources have defaults (`smptebars`→`320x240`), some don't — set it explicitly for anything HD or above.
- `rate=N` (or `r=N`) — **video** framerate, fps.
- `duration=N` — source-level duration, seconds (or `HH:MM:SS.ms`). Leave it off → source runs forever until `-t` or EOF.
- `sample_rate=N` (or `sr=N`) — **audio** sample rate, Hz.
- `channel_layout=mono|stereo|5.1` — audio layout (not `channels=2` for most sources; see gotchas).
- `pixel_format=yuv420p|yuv422p|rgb24|…` — some sources accept it; use `format=` filter otherwise.
- `c=<colorname>` / `color=<…>` — solid-color sources accept CSS/HTML names, `0xRRGGBB`, `#RRGGBB`, `random`.

Compose video + audio by stacking two `-f lavfi -i` inputs:

```
-f lavfi -i smptehdbars=size=1920x1080:rate=30 \
-f lavfi -i "sine=frequency=1000:sample_rate=48000"
```

ffmpeg auto-maps one video + one audio from those inputs — no `-map` usually needed for a single V+A pair.

## Step 3 — Encode, duration, and container

Synthetic sources are infinite by default. **Always** bound the output with *one* of:

- `duration=N` inside the source expression, or
- `-t N` on the output (before the output filename).

Mixing both works but is easy to get wrong — prefer `-t` on the command line so the same flag caps both streams.

### Recipe A — SMPTE HD bars + 1 kHz tone, 10 s, 1080p30, MP4

```bash
ffmpeg -f lavfi -i smptehdbars=size=1920x1080:rate=30 \
       -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
       -t 10 \
       -c:v libx264 -pix_fmt yuv420p -crf 18 \
       -c:a aac -b:a 192k -ar 48000 \
       out.mp4
```

### Recipe B — testsrc2 moving pattern + counter, 5 s, 720p30

```bash
ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=30 -t 5 \
       -c:v libx264 -pix_fmt yuv420p -crf 20 out.mp4
```

### Recipe C — Solid red fill, 5 s, 720p

```bash
ffmpeg -f lavfi -i "color=c=red:size=1280x720:rate=30:duration=5" \
       -c:v libx264 -pix_fmt yuv420p out.mp4
```

### Recipe D — Animated red→blue gradient, 10 s 1080p

```bash
ffmpeg -f lavfi -i "gradients=s=1920x1080:duration=10:speed=0.01:c0=red:c1=blue" \
       -c:v libx264 -pix_fmt yuv420p out.mp4
```

### Recipe E — Mandelbrot zoom, 10 s 1080p30

```bash
ffmpeg -f lavfi -i mandelbrot=size=1920x1080:rate=30 -t 10 \
       -c:v libx264 -pix_fmt yuv420p out.mp4
```

### Recipe F — PAL 75 % bars, 10 s 576i

```bash
ffmpeg -f lavfi -i pal75bars=size=720x576:rate=25 -t 10 \
       -c:v libx264 -pix_fmt yuv420p out.mp4
```

### Recipe G — Silent stereo track attached to a video-only source

```bash
ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=30 \
       -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
       -t 10 -c:v libx264 -pix_fmt yuv420p -c:a aac out.mp4
```

### Recipe H — White / pink noise (audio only)

```bash
ffmpeg -f lavfi -i "anoisesrc=color=white:duration=5:sample_rate=48000:amplitude=0.3" \
       -c:a pcm_s16le noise.wav
```

### Recipe I — Beep-style sine (0.25 s beep every 1 s)

```bash
ffmpeg -f lavfi -i "sine=frequency=440:beep_factor=4:duration=10:sample_rate=48000" \
       -c:a pcm_s16le beep.wav
```

### Recipe J — Identity Hald CLUT (level 8 → 512×512 PNG)

```bash
ffmpeg -f lavfi -i haldclutsrc=level=8 -frames:v 1 hald.png
```

### Recipe K — ColorChecker 24-patch PNG

```bash
ffmpeg -f lavfi -i colorchecker -frames:v 1 colorchecker.png
# Some builds accept size=:  -f lavfi -i colorchecker=patch_size=128x128:preset=reference
```

### Recipe L — Broadcast line-up: SMPTE HD bars + 1 kHz tone at -20 dBFS

```bash
ffmpeg -f lavfi -i smptehdbars=size=1920x1080:rate=30 \
       -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
       -af "volume=-20dB" \
       -t 60 -c:v libx264 -pix_fmt yuv420p -crf 16 \
       -c:a pcm_s24le lineup.mxf
```

### Recipe M — Overlay a running timecode on SMPTE bars

Chain with `drawtext` (see `ffmpeg-video-filter`):

```bash
ffmpeg -f lavfi -i smptehdbars=size=1920x1080:rate=30 \
       -vf "drawtext=fontfile=/System/Library/Fonts/Menlo.ttc:text='%{pts\\:hms}':x=40:y=40:fontsize=64:fontcolor=white:box=1:boxcolor=black@0.6" \
       -t 10 -c:v libx264 -pix_fmt yuv420p bars_tc.mp4
```

## Gotchas

- **Every lavfi source uses `-f lavfi -i <expression>`.** `<expression>` is filter-source syntax. It is NOT a filename; do not quote it as a path.
- **Duration is not implicit.** Without `duration=` on the source OR `-t` on the output, ffmpeg generates frames forever. Always bound one of them.
- **Use `-t` *or* `duration=`, not both casually.** They interact: `-t` caps the output, `duration=` caps the source. If they disagree the shorter one wins; prefer `-t` for consistency across V+A inputs.
- **`sine` duration lives on the SOURCE.** `-f lavfi -i "sine=frequency=1000:duration=10"` — the filter owns its own length. `-t 10` also works and is clearer when you have two inputs.
- **`smptebars` vs `smptehdbars`.** `smptebars` = pre-HD 75 % bars at `320x240` default. `smptehdbars` = HD 100 % bars, aspect-correct. `pal75bars` / `pal100bars` are the PAL variants. Don't default to `smptebars` for HD deliverables.
- **`size=` is often required.** `colorchecker`, `rgbtestsrc`, `yuvtestsrc`, `smptebars` have small/fixed defaults in older ffmpeg builds. Pass `size=WxH` explicitly for HD.
- **`rate` is VIDEO fps; `sample_rate` is AUDIO Hz.** They're different knobs. Don't set `rate=48000` on `sine`.
- **Channel layout, not channel count.** Most audio sources want `channel_layout=stereo` (or `mono`, `5.1`). A raw `channels=2` is accepted by some but not all — prefer the named layout.
- **Combining V+A = two `-f lavfi -i` flags.** Each input needs its own `-f lavfi` before its `-i`. One `-f lavfi` does not cover the next `-i`.
- **Container must accept both streams.** MP4 + libx264 + aac is the safe default. Don't write a video source into a `.wav`. Don't stuff `pcm_s24le` into plain MP4 (use MOV/MXF/MKV).
- **Color names.** `c=red` / `c=0xff0000` / `c=#ff0000` / `c=random` all work. Alpha via `c=red@0.5`.
- **`testsrc2`** already burns in a frame counter and moving element — if you want it clean, use `testsrc`.
- **`haldclutsrc=level=N`** produces an `N³ × N³` PNG (level 6 → 216×216, level 8 → 512×512, level 12 → 1728×1728). Level 8 is the common LUT-authoring default.
- **`anullsrc` is identical regardless of `duration`.** It's literal zeros. Use `-t` to cap length.
- **Images need `-frames:v 1`.** Otherwise ffmpeg keeps writing frames into `out.png` indefinitely (or errors on single-image muxers).
- **Seek does not apply to generators.** `-ss 5 -f lavfi -i testsrc` will NOT start the source at `t=5`. Generators start at zero; use `-itsoffset` or `tpad` if you need a cold start.
- **Broadcast line-up level.** SMPTE-compliant line-up = 1 kHz sine at -20 dBFS (EBU R68 = -18 dBFS). Apply with `-af "volume=-20dB"` — the `sine` source emits full-scale by default.
- **`flite` TTS requires a custom build.** `ffmpeg -filters | grep flite` — if empty, your build is stock; use external TTS and import the WAV.

## Available scripts

- **`scripts/synth.py`** — argparse wrapper with subcommands for the common synthetic assets: `bars`, `test-pattern`, `color`, `tone`, `noise`, `silence`, `hald-identity`. Prints the exact ffmpeg command, supports `--dry-run` and `--verbose`. Stdlib only, non-interactive.

## Workflow

1. Run the script for a standard recipe:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/synth.py bars --output out.mp4 --duration 10 --resolution 1920x1080 --fps 30 --tone-hz 1000 --hd
   uv run ${CLAUDE_SKILL_DIR}/scripts/synth.py test-pattern --output out.mp4 --kind testsrc2 --duration 5
   uv run ${CLAUDE_SKILL_DIR}/scripts/synth.py tone --output tone.wav --hz 1000 --duration 10
   uv run ${CLAUDE_SKILL_DIR}/scripts/synth.py noise --output noise.wav --color pink --duration 10
   uv run ${CLAUDE_SKILL_DIR}/scripts/synth.py hald-identity --output hald.png --level 8
   ```
2. For anything off the menu (custom gradient, aevalsrc expression, zoneplate, cellauto) build the `-f lavfi -i` chain by hand using Step 2.

## Reference docs

- Read [`references/sources.md`](references/sources.md) for full per-source option tables, color name list, `aevalsrc` grammar, and a recipe gallery (broadcast cal, ABX noise, 4K 60 fps stress, identity Hald, synthetic overlays).

## Examples

### Example 1: Broadcast cal leader, 1 minute, MXF

```bash
ffmpeg -f lavfi -i smptehdbars=size=1920x1080:rate=30 \
       -f lavfi -i "sine=frequency=1000:sample_rate=48000" \
       -af "volume=-20dB" \
       -t 60 -c:v libx264 -pix_fmt yuv420p -crf 16 -c:a pcm_s24le \
       leader.mxf
```

### Example 2: 4 K 60 fps encoder stress-test, 30 s

```bash
ffmpeg -f lavfi -i testsrc2=size=3840x2160:rate=60 \
       -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
       -t 30 -c:v libx264 -preset ultrafast -pix_fmt yuv420p stress.mp4
```

### Example 3: Identity Hald CLUT round-trip

```bash
ffmpeg -f lavfi -i haldclutsrc=level=8 -frames:v 1 identity.png
# Grade identity.png in your DaVinci/Photoshop/LUT tool, save back as graded.png
# Apply the graded CLUT to any footage via ffmpeg-lut-grade:
#   ffmpeg -i source.mov -i graded.png -filter_complex "haldclut" out.mov
```

### Example 4: Solid-color plate for lower-third compositing

```bash
ffmpeg -f lavfi -i "color=c=0x0a1f44:size=1920x200:rate=30:duration=10" \
       -c:v libx264 -pix_fmt yuv420p lower_third_bg.mp4
```

## Troubleshooting

### Error: `No such filter: 'lavfi'`

Cause: you passed `-i lavfi:...` instead of `-f lavfi -i "..."`.
Solution: `-f lavfi` is a format flag; it must precede `-i`, and the expression goes in `-i`.

### Error: `Option size not found`

Cause: the specific source does not accept `size=` in your ffmpeg version (older builds of `colorchecker`, `rgbtestsrc`).
Solution: pipe through a `scale` filter, e.g. `-vf "scale=1920:1080"`, or upgrade ffmpeg.

### Output file is empty / 0 bytes

Cause: no duration bound — ffmpeg was producing frames with no EOF signal and you killed it early.
Solution: add `-t N` or `duration=N` inside the source expression.

### `sine` audio is silent / file is tiny

Cause: forgot `sample_rate=48000` and the default (44100) is being resampled to 0 by a bad `-ar`.
Solution: set `sample_rate=` on the source AND `-ar 48000` on the output if you want a specific rate.

### `Invalid duration specification` for `color`

Cause: quoting ate the colons. `color=c=red:size=1280x720:rate=30:duration=5` must be a single token to ffmpeg.
Solution: wrap the whole expression in double quotes: `-i "color=c=red:size=1280x720:rate=30:duration=5"`.

### `anoisesrc` complains about `color=pink`

Cause: older ffmpeg builds only shipped `white` and `pink`; `blue`/`brown`/`velvet` came later.
Solution: upgrade ffmpeg to 4.4+ for the full palette, or fall back to `color=white` and shape with `-af "highpass=..."`.

### Seeking into a synthetic source does nothing

Cause: `-ss` on a lavfi input is a no-op (no seekable timeline).
Solution: offset via `-itsoffset`, or prepend blank frames with `tpad=start_duration=…`.
