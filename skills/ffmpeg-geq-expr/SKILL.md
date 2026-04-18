---
name: ffmpeg-geq-expr
description: >
  Procedural and expression-based ffmpeg filters: geq (per-pixel YUV/RGB expressions), aeval (audio sample expressions), lut2 (two-input LUT expression), drawgraph (real-time metrics graph), drawvg (SVG rendering over video), random, feedback, lagfun. Use when the user asks to build a custom pixel-level filter, apply math directly to video samples, render SVG over video, make a real-time debug graph, simulate feedback delay, or write arbitrary expressions for creative effects.
argument-hint: "[expression]"
---

# ffmpeg-geq-expr — procedural expression filters

**Context:** $ARGUMENTS

Power-user creative filters where you hand-write a math expression and ffmpeg evaluates it per-pixel (`geq`), per-sample (`aeval`), per-pair (`lut2`), or per-metric (`drawgraph`). Grammar is the same everywhere: see `references/expressions.md`.

## Quick start

- **Custom per-pixel effect:** → Step 1 → pick `geq`
- **Custom per-sample audio effect:** → Step 1 → pick `aeval`
- **Blend/combine two videos pixel-by-pixel with math:** → Step 1 → pick `lut2`
- **Real-time metric graph burned into video:** → Step 1 → pick `drawgraph`
- **SVG overlay driven by frame metadata:** → Step 1 → pick `drawvg`
- **Light-on-dark persistence / phosphor trails:** → Step 1 → pick `lagfun`
- **Feedback-loop picture-in-picture:** → Step 1 → pick `feedback`
- **Shuffle frame order:** → Step 1 → pick `random`

## When to use

- You need a per-pixel/per-sample effect that no named filter ships with (gradients, plasma, custom noise, chromatic aberration, vignettes).
- You want to wire filter metadata (`signalstats`, `ebur128`, `blockdetect`) into a visible QC graph.
- You want to combine two aligned inputs with arbitrary math, not `blend`'s fixed modes.
- You want a one-off creative look without writing a C filter.

**Do NOT use for things with a dedicated filter** — `geq` is typically 10–100× slower than a native filter. If `vignette`, `lut3d`, `colorchannelmixer`, `curves`, etc. can do it, use those.

## Step 1 — Pick the right filter

| Need | Filter | Domain |
|---|---|---|
| Per-pixel math on one video | `geq` | spatial (X,Y) + temporal (T,N) |
| Per-sample math on audio | `aeval` | per-sample per-channel |
| Two-video pixel math | `lut2` | pairs of samples (x, y) from inputs |
| Graph metadata values | `drawgraph` | per-frame scalar from metadata keys |
| SVG / VGS vector overlay | `drawvg` | per-frame VGS script |
| Frame-order shuffle | `random` | temporal only |
| Feedback picture-in-picture | `feedback` | spatial box + time |
| Dark-decay afterimage | `lagfun` | per-pixel with decay |

## Step 2 — Write the expression

Grammar highlights (full table in `references/expressions.md`):

- **Built-in constants:** `PI`, `E`, `PHI`, `TAU`.
- **Functions:** `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `log`, `sqrt`, `hypot(a,b)`, `pow(a,b)` or `a^b`, `mod(a,b)`, `abs`, `floor`, `ceil`, `round`, `trunc`, `clip(v,a,b)`, `between(v,a,b)`, `if(c,t,e)`, `ifnot(c,e)`, `gt(a,b)`, `lt(a,b)`, `gte`, `lte`, `eq(a,b)`, `not(x)`, `random(seed)`, `st(N,v)` store, `ld(N)` load (26 slots, N=0..25), `print(v)` to stderr.
- **Operators:** `+ - * / %`, `^` power, `&& || !` logic, `? :` ternary is NOT supported (use `if(c,t,e)`).

**geq per-plane YUV:**
```
geq=lum='X+T*10':cb=128:cr=128            # moving luminance ramp, neutral chroma
geq=lum='255*(X/W)':cb='128+64*sin(T)':cr='128+64*cos(T)'
```
**geq RGB (requires planar RGB pixfmt):**
```
format=gbrp,geq=r='255*X/W':g='255*Y/H':b=0       # diagonal RG gradient
format=gbrp,geq=r='b(X,Y)':g=g:b='r(X,Y)'         # BGR channel swap
```
**Vignette via geq (hand-rolled):**
```
format=gbrp,geq=r='r(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)':g='g(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)':b='b(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)'
```
**aeval (per-sample):**
```
aeval=val(0)*0.5|val(1)*0.5:channel_layout=stereo        # halve volume (note | between exprs)
aeval=val(ch)*sin(2*PI*5*t):c=same                       # 5 Hz tremolo
```
**aevalsrc (synth):**
```
aevalsrc='sin(2*PI*440*t)':channel_layout=mono:sample_rate=48000:duration=2
```
**lut2 (two inputs, same size/pixfmt):**
```
lut2=c0='(x+y)/2':c1='(x+y)/2':c2='(x+y)/2'              # pixel average blend
```
**drawgraph (metadata chart):**
```
signalstats,drawgraph=m1=lavfi.signalstats.YAVG:fg1=0xff00ff:min=0:max=255:size=1280x200
```
**drawvg (SVG/VGS overlay):**
```
drawvg=cfg='<svg><rect x=20 y=20 width=200 height=60 fill="red"/></svg>'
```
**random (frame order):**
```
random=frames=30:seed=42
```
**feedback (recursive PiP):**
```
feedback=x=10:y=10:w=100:h=100
```
**lagfun (dark decay / afterimage):**
```
lagfun=decay=0.9
```

## Step 3 — Run and debug

**Always test on 2 seconds first:**
```
ffmpeg -i in.mp4 -t 2 -vf "<expr-filter>" -y out_test.mp4
```
**See parse errors:** `-loglevel debug` prints tokens as they parse. A silent output or black frames without stderr output almost always means a typo or an operator ffmpeg's parser rejected.

**Drop `print()` into any expression** to dump a value per evaluation to stderr:
```
geq=lum='print(T)':cb=128:cr=128
```

**Use the helper:**
```
uv run ${CLAUDE_SKILL_DIR}/scripts/expr.py geq --input in.mp4 --output out.mp4 --lum 'X+T*10'
```

## Available scripts

- **`scripts/expr.py`** — subcommands: `geq`, `aeval`, `lut2`, `drawgraph`, `feedback`, `lagfun`. All support `--dry-run` and `--verbose`. Autodetects RGB vs YUV for `geq` based on which flags you pass.

## Reference docs

- Read [`references/expressions.md`](references/expressions.md) for the full grammar, geq constant table, store/load slot usage, 50+ worked recipes, and the `drawgraph` metric catalog.

## Gotchas

- `geq` **coordinates**: `X`/`Y` are 0-based pixel coordinates, `W`/`H` are plane dimensions, `SW`/`SH` are the horizontal/vertical subsampling factors (use `SW`/`SH` in chroma expressions on 4:2:0, where chroma planes are half-size). `T` is time in seconds (float). `N` is the frame number.
- `p(x,y)` inside a chroma (`cb`/`cr`) expression returns a **chroma** sample, not luma. If you want luma inside a chroma expression use `lum(X,Y)`. Likewise `lum()`, `cb()`, `cr()`, `alpha()`, `r()`, `g()`, `b()` all exist.
- `clip(v,a,b)` clamps; `st(N,v)` stores in slot `N` (0..25), `ld(N)` reads. Use these when an expression appears multiple times.
- `geq` on RGB input silently operates on **packed** pixels unless you insert `format=gbrp` first. Always prepend `format=gbrp` before a color-channel `geq`.
- Expressions are compiled but **evaluated per pixel, per frame**. Complex expressions can drop processing to sub-1 fps. Cache common sub-expressions with `st()`/`ld()`.
- `aeval` evaluates **per audio sample** and is slow. For synth (not a real-time effect on a real stream), use `aevalsrc` — much faster because there's no input rate.
- `aeval` variables: `val(i)` is input channel `i`'s current sample, `ch` is output channel index, `nb_in_channels`, `nb_out_channels`, `s` sample rate, `t` time, `n` sample number.
- `lut2`: expression uses `x` (input 0 sample) and `y` (input 1 sample). Both inputs **must** have the same dimensions AND pixel format. Insert `scale=` + `format=` before the join.
- `drawgraph`: background defaults to transparent. If you want it on top of video, pipe through `overlay`. To output a standalone graph, add `bg=black` or use the `color` source as a backdrop.
- `drawvg` is **new** (post-FFmpeg 7.x). Check `ffmpeg -filters 2>&1 | grep drawvg` before relying on it.
- `feedback` requires **all four** `x`, `y`, `w`, `h` — without `w`/`h` it silently fails.
- When an expression has a parse error, ffmpeg commonly **silently outputs black frames** or stops without a loud error. Run with `-loglevel debug` and search the output for `Error when evaluating`.
- `PI` / `E` / `PHI` / `TAU` are built-in; don't redeclare them as `st()`.
- Comma `,` separates filter options in ffmpeg syntax. Inside an expression, use `\,` (escaped) or wrap the whole expression in single quotes.
- Semicolon `;` separates filter-graph stages; use `|` to separate per-channel expressions inside `aeval`.
- Always test expressions with `-t 2` on a short clip first, then scale up.

## Examples

### Vertical gradient (RGB)
```
ffmpeg -f lavfi -i color=black:s=640x360:d=2 -vf "format=gbrp,geq=r='255*Y/H':g=0:b='255-255*Y/H'" -y grad.mp4
```

### Moving plasma
```
ffmpeg -f lavfi -i color=black:s=640x360:d=3 \
  -vf "format=gbrp,geq=r='128+127*sin(X/20+T)':g='128+127*sin(Y/20+T*1.3)':b='128+127*sin((X+Y)/20+T*0.7)'" \
  -y plasma.mp4
```

### Chromatic aberration
```
ffmpeg -i in.mp4 -vf "format=gbrp,geq=r='r(X+2,Y)':g='g(X,Y)':b='b(X-2,Y)'" -y ca.mp4
```

### YAVG graph burn-in
```
ffmpeg -i in.mp4 -vf "signalstats,drawgraph=m1=lavfi.signalstats.YAVG:fg1=0xffff00:min=0:max=255:size=1920x120,format=yuv420p" -c:v libx264 -crf 18 -y graph.mp4
```

### Lagfun phosphor trail
```
ffmpeg -i in.mp4 -vf "lagfun=decay=0.92" -y trail.mp4
```

### Two-video lut2 average blend
```
ffmpeg -i a.mp4 -i b.mp4 -filter_complex "[0:v]scale=1280:720,format=yuv420p[a];[1:v]scale=1280:720,format=yuv420p[b];[a][b]lut2=c0='(x+y)/2':c1='(x+y)/2':c2='(x+y)/2'" -y blend.mp4
```

## Troubleshooting

### Black frames, no obvious error

Cause: expression parse error silently produced all-zero output.
Solution: add `-loglevel debug`, search stderr for `Error when evaluating`, check for unescaped commas in expression, or wrong variable name (e.g. `x` inside `geq` should be `X`).

### `geq` on RGB but colors ignored / operating on packed bytes

Cause: input is packed RGB (`rgb24`, `bgr24`), not planar.
Solution: prepend `format=gbrp` before `geq`.

### `lut2` error: inputs dimensions differ

Cause: two inputs have different resolutions or pixel formats.
Solution: prepend `scale=W:H,format=yuv420p` on both inputs before joining.

### `geq` runs at 0.3 fps

Cause: expression is complex, recomputed per-pixel.
Solution: cache repeated sub-expressions with `st(0,...)` then reuse with `ld(0)`. Also: consider if a native filter (vignette, colorchannelmixer, curves) can do the same thing.

### `drawgraph` shows nothing

Cause: metadata keys are wrong, or the producer filter wasn't upstream.
Solution: `signalstats` → `drawgraph=m1=lavfi.signalstats.YAVG`. Run `ffprobe -show_frames` to confirm the metadata keys.

### `aevalsrc` produces clipped audio

Cause: expression output exceeds ±1.0.
Solution: scale the expression: `sin(2*PI*440*t)*0.5`.

### `feedback` silently does nothing

Cause: missing one of `x`, `y`, `w`, `h`.
Solution: supply all four. Also check coords are inside the frame.
