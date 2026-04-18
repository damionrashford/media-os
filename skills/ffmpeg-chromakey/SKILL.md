---
name: ffmpeg-chromakey
description: >
  Chromakey, greenscreen, and compositing with ffmpeg: chromakey, colorkey, hsvkey, lumakey, chromakey_cuda, despill, backgroundkey, overlay with alpha. Use when the user asks to do a greenscreen, remove a green/blue background, chroma key, key out a color, composite a subject onto a new background, fix spill from a greenscreen, layer transparent video, or replace a solid background with another video.
argument-hint: "[key-color] [input]"
---

# Ffmpeg Chromakey

**Context:** $ARGUMENTS

## Quick start

- **Green screen over new bg:** → Step 1 (pick filter) → Step 2 (tune) → Step 3 (despill) → Step 4 (overlay)
- **Export transparent mezzanine (ProRes 4444 / VP9-alpha / PNG seq):** → Step 3, then encode with alpha-capable codec
- **GPU path (NVIDIA):** → Step 1 variant using `chromakey_cuda`

## When to use

- Subject shot on green/blue screen needs a new background
- Keyed subject needs to be delivered with alpha for downstream compositing (After Effects, Resolve, web)
- Uneven green (fluorescent falloff, wrinkles): HSV key instead of chromakey
- Subject has a static plate-background (e.g. locked-off camera): `backgroundkey` beats chroma
- Bright-on-dark or dark-on-bright with no color cue: `lumakey`

## Step 1 — Pick the key filter

| Situation | Filter |
|---|---|
| Clean green/blue screen, even lighting | `chromakey` (YUV/UV) |
| Need RGB-based pick or `chromakey` struggles | `colorkey` (RGB) |
| Uneven lighting, muddy green, hair detail | `hsvkey` |
| No color — separate on brightness only | `lumakey` |
| Locked camera, have a clean plate | `backgroundkey` (subtracts plate) |
| NVIDIA GPU available, must be fast | `chromakey_cuda` |

Always sample the ACTUAL green from your footage (screenshot a flat patch, eyedrop in Preview / ffplay with `-vf format=rgb24`). `0x00FF00` is pure green and almost never matches real screens (typical: `0x20B040` – `0x3EB34C`).

## Step 2 — Tune similarity + blend

- `similarity` — how wide the color tolerance is. 0 = exact match only, 1 = everything. Typical `0.05`–`0.20`. Start `0.10`.
- `blend` — edge softness (feather). 0 = hard binary edge (aliased, bad), >0 = graded alpha. Typical `0.02`–`0.10`. Start `0.05`.

Loop: bump `similarity` until the screen is gone and the subject's edges start chewing → back off one notch → then raise `blend` until edges look natural.

```bash
# Basic chromakey (YUV), preserves alpha on yuva420p
ffmpeg -i fg.mp4 -vf "chromakey=0x20B040:0.12:0.05,format=yuva420p" -c:v qtrle keyed.mov
```

## Step 3 — Despill

Even after a clean key, green light reflected onto the subject's skin / hair / white shirt will show as a sickly fringe. Always run `despill` after the key, before compositing.

```bash
# Key then despill (green). Chain inside the same filter graph.
[0:v]chromakey=0x20B040:0.12:0.04,despill=type=green:mix=0.5:expand=0.1[keyed]
```

- `type=green` or `type=blue`
- `mix` = strength of spill removal (0.2 subtle, 0.6 aggressive)
- `expand` = how far from detected pixels to push correction (`0.0`–`0.3`)

## Step 4 — Composite with `overlay`

```bash
# Simple green key + composite onto bg.mp4
ffmpeg -i fg.mp4 -i bg.mp4 \
  -filter_complex "[0:v]chromakey=0x00FF00:0.10:0.05[keyed];[1:v][keyed]overlay=shortest=1[out]" \
  -map "[out]" -map 0:a? -c:v libx264 -crf 18 -pix_fmt yuv420p out.mp4
```

Order: background first (`[1:v]`), keyed subject on top (`[keyed]`). `shortest=1` ends at the shorter input; drop it to run until the longer input finishes.

## Available scripts

- **`scripts/key.py`** — key / composite / identity-transparent subcommands; picks an alpha-capable codec based on output extension.

## Workflow

Key and write a transparent ProRes 4444 mezzanine:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/key.py identity-transparent \
  --input fg.mp4 --output keyed.mov --color 0x20B040 --similarity 0.12 --blend 0.05
```

Full composite in one shot:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/key.py composite \
  --fg fg.mp4 --bg bg.mp4 --output out.mp4 --color 0x20B040 --despill green
```

## Reference docs

Read [`references/filters.md`](references/filters.md) when tuning per-filter options, picking an alpha-capable codec/container, comparing chromakey vs colorkey vs hsvkey, or looking up real-world green/blue hex samples.

## Gotchas

- `chromakey` and `colorkey` differ in color space. `chromakey` operates on YUV chroma (hue + chroma, ignores luma) — robust to brightness variation. `colorkey` operates on RGB distance — simpler but fails under uneven lighting.
- Pure-green `0x00FF00` is almost NEVER the actual screen color. Sample the source (screenshot + eyedrop) or use `colorkey=0x00FF00:0.30:0.20` with a huge similarity to find the range.
- `similarity` typical 0.01–0.30; `blend` typical 0.00–0.20. `blend=0` produces hard aliased binary edges — always raise it slightly.
- ffmpeg has NO alpha-aware color management. Prefer `format=yuva444p` over `yuva420p` for clean edges; `yuva420p` subsamples chroma + alpha and fringes on hair.
- Output container MUST support alpha to preserve the key: MP4 + libx264 does NOT support alpha. Use MOV + `qtrle`, MOV + ProRes 4444 (`prores_ks -profile:v 4444 -pix_fmt yuva444p10le`), WebM + `libvpx-vp9 -pix_fmt yuva420p`, or a PNG image sequence.
- `overlay=shortest=1` ends output at the shorter input — omit when the bg is shorter than the subject and you want it held.
- If a green fringe remains after keying, ALWAYS run `despill=type=green` (or `type=blue`). Do NOT try to hide it by cranking `similarity`.
- `chromakey_cuda` requires NVIDIA hwaccel and MUST be bracketed: `hwupload_cuda,chromakey_cuda=...,hwdownload,format=yuva420p`.
- HSV key is easier to tune on uneven screens — use when chromakey's `similarity` is fighting you.
- Pipeline order: KEY → DESPILL → COMPOSITE. Never composite first.
- Audio: `-map 0:a?` keeps the subject's audio (the `?` makes it optional so the command doesn't fail if input has no audio).
- For transparent delivery to prosumer tools, PNG image sequence is the most portable. For pro finishing, ProRes 4444 is standard.

## Examples

### Example 1: Clean green screen → composite over new bg

```bash
ffmpeg -i subject.mp4 -i newbg.mp4 \
  -filter_complex "[0:v]chromakey=0x20B040:0.12:0.05,despill=type=green:mix=0.4[k];[1:v][k]overlay=shortest=1[out]" \
  -map "[out]" -map 0:a? -c:v libx264 -crf 18 -pix_fmt yuv420p out.mp4
```

### Example 2: Uneven lighting → HSV key

```bash
ffmpeg -i subject.mp4 -i newbg.mp4 \
  -filter_complex "[0:v]hsvkey=h=120:s=0.7:v=0.3:similarity=0.05:blend=0.02,despill=type=green[k];[1:v][k]overlay[out]" \
  -map "[out]" -c:v libx264 -crf 18 out.mp4
```

### Example 3: Transparent ProRes 4444 mezzanine

```bash
ffmpeg -i subject.mp4 -vf "chromakey=0x20B040:0.12:0.05,despill=type=green,format=yuva444p10le" \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -c:a copy keyed.mov
```

### Example 4: Transparent WebM (VP9 with alpha)

```bash
ffmpeg -i subject.mp4 -vf "chromakey=0x20B040:0.12:0.05,despill=type=green,format=yuva420p" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 4M -auto-alt-ref 0 keyed.webm
```

### Example 5: PNG image sequence (fully portable alpha)

```bash
ffmpeg -i subject.mp4 -vf "chromakey=0x20B040:0.12:0.05,despill=type=green,format=rgba" \
  -c:v png frames/keyed_%05d.png
```

### Example 6: GPU (NVIDIA)

```bash
ffmpeg -hwaccel cuda -i subject.mp4 -i newbg.mp4 \
  -filter_complex "[0:v]hwupload_cuda,chromakey_cuda=0x00FF00:0.1:0.05,hwdownload,format=yuva420p[k];[1:v][k]overlay[out]" \
  -map "[out]" -c:v h264_nvenc -cq 20 out.mp4
```

### Example 7: Background subtraction (locked camera + clean plate)

```bash
ffmpeg -i subject.mp4 -i plate.mp4 \
  -filter_complex "[0:v][1:v]backgroundkey=threshold=0.08:similarity=0.1:blend=0.05[k];[0:v][k]alphamerge,format=yuva420p[out]" \
  -map "[out]" -c:v qtrle keyed.mov
```

### Example 8: colorkey variant (RGB-based)

```bash
ffmpeg -i subject.mp4 -vf "colorkey=0x00FF00:0.30:0.20,format=yuva420p" -c:v qtrle keyed.mov
```

## Troubleshooting

### Error: output has black background where the key should be transparent

Cause: container/codec does not support alpha (e.g. MP4+libx264).
Solution: switch to MOV+qtrle, MOV+ProRes 4444, WebM+libvpx-vp9 (yuva420p), or PNG sequence.

### Error: green fringe / halo around subject

Cause: reflected green spill; key cannot remove reflected light.
Solution: chain `despill=type=green:mix=0.5:expand=0.1` after the key filter, BEFORE the overlay.

### Error: jagged / aliased edges

Cause: `blend=0` or too-low blend.
Solution: raise `blend` to `0.02`–`0.08`. If still bad, switch output to `format=yuva444p` (no chroma subsampling on alpha).

### Error: hair / fine detail vanishes

Cause: `similarity` too high.
Solution: lower `similarity`, then switch to `hsvkey` (better tonal separation), and/or downstream roto for hard edges.

### Error: `chromakey_cuda` fails with "No device available"

Cause: NVIDIA drivers / CUDA not available, or missing hwupload bracket.
Solution: confirm `ffmpeg -hwaccels` lists `cuda`. Always bracket: `hwupload_cuda,chromakey_cuda=...,hwdownload,format=yuva420p`.

### Error: `overlay` output ends early

Cause: `shortest=1` set, and the keyed clip is shorter than bg.
Solution: remove `shortest=1`, or swap input order.
