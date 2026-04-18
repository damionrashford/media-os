---
name: ffmpeg-video-filter
description: >
  Apply video filters with ffmpeg -vf / -filter_complex: scale, crop, pad, rotate/transpose, fps, setsar, deinterlace (yadif/bwdif), overlay, hstack/vstack, drawtext, drawbox, color (curves, eq, colorchannelmixer), denoise, sharpen, blur, fade, zoompan. Use when the user asks to resize, crop, rotate, flip, pad, overlay a watermark/logo, stack videos side-by-side, add text/captions on top, change fps, deinterlace, color correct, sharpen, blur, or apply any video effect.
argument-hint: "[operation] [input]"
---

# Ffmpeg Video Filter

**Context:** $ARGUMENTS

## Quick start

- **Resize to 720p (keep aspect):** `-vf "scale=-2:720"` → Step 2
- **Letterbox to 1080p:** `-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"` → Example 2
- **Watermark (PNG corner):** `-filter_complex "[1:v]scale=200:-1[wm];[0:v][wm]overlay=W-w-10:H-h-10"` → Example 1
- **Deinterlace:** `-vf "yadif=1"` → Example 5
- **Stack two videos:** `-filter_complex "[0:v][1:v]hstack=inputs=2"` → Example 3

## When to use

- Single-input transformation on one video stream (scale/crop/pad/fps/color) → use `-vf`.
- Combining two or more inputs (overlay, hstack, picture-in-picture) → use `-filter_complex`.
- Anything with `split`, multiple outputs, or named labels → `-filter_complex` + `-map`.

## Step 1 — Pick `-vf` vs `-filter_complex`

`-vf` (and `-af` for audio) is shorthand for a single-input, single-output chain. Every filter is comma-separated. Example: `-vf "scale=1280:720,eq=saturation=1.1,fps=30"`.

`-filter_complex` is the general graph. It accepts multiple inputs and outputs, uses `[in][out]` labels, and chains are separated by **semicolons** (filters within a chain are still comma-separated). When you use it you **must** `-map` every output stream you want in the container — default stream selection is disabled.

Rules of thumb:
- One input file, one video track, linear transform → `-vf`.
- Any time you write `[0:v]` or `[1:v]` → `-filter_complex`.
- You need the same source twice (split) → `-filter_complex`.

## Step 2 — Build the filter chain

Canonical filter order: **deinterlace → crop → scale → pad → color/eq → overlay → drawtext → fps → format**. Deviating has real cost: cropping after scaling wastes pixels; scaling before cropping blurs detail you were going to throw away.

Scale recipes (`scale` is the workhorse):

```text
scale=1280:720                    # exact
scale=-2:720                      # keep aspect, height 720, width rounded to even
scale=1920:-2                     # keep aspect, width 1920
scale=iw/2:ih/2                   # half size
scale=1920:1080:force_original_aspect_ratio=decrease   # fit inside box (letterbox prep)
scale=1920:1080:force_original_aspect_ratio=increase   # fill box (crop prep)
scale=1920:1080:flags=lanczos     # high-quality downscale
```

Use `-2` (not `-1`) for the auto dimension: most codecs (H.264/HEVC/AV1 with YUV 4:2:0) require even width and height. `-1` preserves aspect but can give odd numbers; `-2` preserves aspect AND snaps to a multiple of 2.

Color / eq quick picks:

```text
eq=brightness=0.05:saturation=1.2:contrast=1.1:gamma=1.0
curves=preset=increase_contrast
curves=preset=cross_process
hue=h=10:s=1.2                    # shift hue by 10 degrees, saturate
colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3   # luma-weighted grayscale
```

Overlay with alpha (PNG logo): pre-format the alpha plane so overlay doesn't silently drop it: `format=yuva420p`.

## Step 3 — Run + verify

```bash
ffmpeg -i in.mp4 -vf "scale=-2:720" -c:v libx264 -crf 20 -preset medium -c:a copy out.mp4
```

For `-filter_complex`, map outputs explicitly:

```bash
ffmpeg -i main.mp4 -i logo.png \
  -filter_complex "[1:v]scale=200:-1[wm];[0:v][wm]overlay=W-w-10:H-h-10[v]" \
  -map "[v]" -map 0:a? -c:a copy out.mp4
```

Verify the output dimensions/fps with ffprobe:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,pix_fmt out.mp4
```

## Available scripts

- **`scripts/vfilter.py`** — preset runner (`scale-720p`, `scale-1080p-letterbox`, `watermark`, `deinterlace`, `drawtext-timecode`, `hstack`, `vstack`, `2x-speed`) plus `--custom --filter-string "..."` for arbitrary `-vf` expressions. Use `--dry-run` to print the command without running.

## Workflow

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/vfilter.py --preset scale-720p --input in.mp4 --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/vfilter.py --preset watermark --input in.mp4 --watermark logo.png --output out.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/vfilter.py --preset hstack --inputs a.mp4,b.mp4 --output side.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/vfilter.py --custom --filter-string "crop=iw-200:ih:100:0,scale=-2:720" --input in.mp4 --output out.mp4
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for exhaustive option tables, expression variables, `-filter_complex` label/map rules, drawtext escaping, and 50+ recipe snippets.

## Gotchas

- **Even dimensions.** Most encoders demand even width *and* height. Use `scale=-2:720`, not `scale=-1:720`. `libx264` with YUV 4:2:0 will hard-fail on odd sizes.
- **drawtext needs a fontfile on many builds.** If fontconfig is missing, omitting `fontfile=` throws "Fontconfig not found". Always specify a real path. macOS: `/System/Library/Fonts/Supplemental/Arial.ttf`. Linux: `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`. Windows: `C\:/Windows/Fonts/arial.ttf` (note the escaped colon).
- **drawtext has three escape levels.** `:` separates filter params → escape inside text as `\:`. `,` separates filters → escape as `\,`. `'` quotes the text → escape as `\\\''` or wrap the whole arg in double quotes at the shell level. For % signs use `\%`.
- **`-vf` cannot take multiple inputs.** The moment you need `[1:v]`, switch to `-filter_complex`.
- **`-filter_complex` disables default stream selection.** You *must* `-map` every output label you want muxed (`-map "[v]" -map 0:a?`), or ffmpeg will not pick them up.
- **Filter order changes results.** Crop before scale to reduce compute and keep detail where it matters. Color ops go after scaling to avoid quantizing twice. drawtext/overlay go last so they render on the final pixel grid.
- **overlay silently drops alpha.** If your PNG has transparency, precede overlay with `format=yuva420p` on the overlay input: `[1:v]format=yuva420p,scale=...[wm]`.
- **`setsar=1` fixes aspect metadata.** Some sources (DV, DVD) have non-square pixels. After any scale you should append `setsar=1` to force square-pixel output.
- **`scale=flags=lanczos` matters when downscaling.** Default is bicubic; lanczos is sharper for 1080p→720p. Upscaling: bicubic/lanczos similar; gauss for blur-friendly upscale.
- **`hstack`/`vstack` require equal dimensions.** Both inputs must match the stacking axis (same height for hstack, same width for vstack). Scale first.
- **`fps` vs `minterpolate`.** `fps=30` drops/duplicates frames — cheap, no visual smoothing. `minterpolate=fps=60` motion-interpolates new frames — expensive, but smooth.
- **Deinterlace field order.** Check with `ffprobe -show_streams | grep field_order`. `yadif=1` sends one field per frame (keeps fps); `yadif=0` merges fields (halves fps, often what you want for 29.97i → 29.97p).

## Examples

### Example 1 — Watermark a logo in the bottom-right

Input: `main.mp4`, `logo.png` (with alpha).
Steps: scale logo to 200px wide, overlay with 10px margin.

```bash
ffmpeg -i main.mp4 -i logo.png \
  -filter_complex "[1:v]format=yuva420p,scale=200:-1[wm];[0:v][wm]overlay=W-w-10:H-h-10[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 20 -c:a copy out.mp4
```

### Example 2 — Scale + letterbox to exact 1920x1080

Input: any aspect ratio.
Steps: fit inside 1920x1080, pad with black to center.

```bash
ffmpeg -i in.mp4 -vf \
  "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,\
pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1" \
  -c:v libx264 -crf 18 -c:a copy out.mp4
```

### Example 3 — 2-up side-by-side (hstack)

Both inputs must share height. Normalize first.

```bash
ffmpeg -i a.mp4 -i b.mp4 -filter_complex \
  "[0:v]scale=-2:720[a];[1:v]scale=-2:720[b];[a][b]hstack=inputs=2[v]" \
  -map "[v]" -c:v libx264 -crf 20 out.mp4
```

### Example 4 — Timecode with drawtext

Burns running timecode at top-left with semi-transparent box.

```bash
ffmpeg -i in.mp4 -vf \
  "drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:\
timecode='00\:00\:00\:00':rate=25:fontsize=32:fontcolor=white:\
box=1:boxcolor=black@0.5:boxborderw=8:x=20:y=20" \
  -c:v libx264 -crf 20 -c:a copy out.mp4
```

Note the `\:` inside the `timecode=` value — the colons are escaped so ffmpeg doesn't interpret them as parameter separators.

### Example 5 — Deinterlace 1080i to 1080p

```bash
ffmpeg -i interlaced.mxf -vf "yadif=1,setsar=1" \
  -c:v libx264 -crf 18 -preset slow -c:a copy progressive.mp4
```

Use `yadif=0` if you actually want half the output framerate (merge fields, 50i → 25p).

## Troubleshooting

### Error: "width not divisible by 2"

Cause: `scale=-1:720` produced an odd width, or you used a codec that demands even dimensions.
Solution: replace `-1` with `-2`. Example: `scale=-2:720`.

### Error: "No such filter" / "Fontconfig not found"

Cause: your ffmpeg build lacks the filter or font system.
Solution: check `ffmpeg -filters | grep drawtext`. If present, pass `fontfile=/absolute/path/to/font.ttf` explicitly — do not rely on `font=Arial`.

### Error: "Output with label 'v' does not exist"

Cause: `-filter_complex` defined `[v]` but you forgot `-map "[v]"`, or you misspelled the label.
Solution: every bracketed label on the right side of the last filter must appear in a `-map` directive.

### Error: filtering produces frozen/black overlay

Cause: overlay input has alpha but no explicit pixel format, so it was negotiated to a format without alpha.
Solution: add `format=yuva420p` before `overlay` on the overlay chain: `[1:v]format=yuva420p,scale=200:-1[wm]`.

### Error: "Filter hstack:0 has an unconnected output" or size mismatch

Cause: inputs to hstack/vstack have different heights/widths.
Solution: scale both to a common dimension first. `[0:v]scale=-2:720[a];[1:v]scale=-2:720[b];[a][b]hstack`.

### drawtext text displays literally with backslashes visible

Cause: over-escaping. You only escape once at the filter-argument level.
Solution: for static text, use `text='Hello\, World'` (single-quoted, `\,` for commas). For timecodes, use the `timecode=` option instead of `text=`.
