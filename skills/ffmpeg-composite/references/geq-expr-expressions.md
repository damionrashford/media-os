# FFmpeg Expression Reference (for geq / aeval / lut2 / drawgraph)

The ffmpeg "expression evaluator" is a tiny AST-based math mini-language used by `geq`, `aeval`, `lut2`, `drawgraph`, `setpts`, `select`, `crop`, and many other filters. The grammar is shared; only the **variables** differ per filter. Authoritative source: `ffmpeg-utils(1)` "Expression Evaluation". Always verify live with:

```
python3 .claude/skills/ffmpeg-docs/scripts/ffdocs.py search --query <filter> --page ffmpeg-filters
```

---

## 1. Grammar

### Constants

| Name | Value |
|---|---|
| `PI` | π (3.14159...) |
| `E` | Euler's e |
| `PHI` | golden ratio |
| `TAU` | 2π |

### Unary / binary operators

`+`, `-`, `*`, `/`, `%` (mod), `^` (power — same as `pow(a,b)`), `&&`, `||`, `!`.

There is **no** C-style `? :` ternary. Use `if(c,then,else)`.

### Functions

```
abs(x)        floor(x)      ceil(x)        round(x)     trunc(x)
sqrt(x)       exp(x)        log(x)          pow(a,b)     hypot(a,b)
sin(x)        cos(x)        tan(x)          asin(x)      acos(x)
atan(x)       atan2(y,x)    sinh(x)         cosh(x)      tanh(x)
mod(a,b)      clip(v,lo,hi) between(v,lo,hi)
gt(a,b)       lt(a,b)        gte(a,b)       lte(a,b)     eq(a,b)
if(c,t,e)     ifnot(c,e)     not(x)         isnan(x)     isinf(x)
min(a,b)      max(a,b)
random(seed)  — uniform [0,1), seeded by N for determinism when needed
print(v)      — writes v to stderr, returns v; use for expression debug
st(N,v)       — store v into slot N (N ∈ 0..25); returns v
ld(N)         — read slot N
sd(N)         — swap halves / store-default; rarely needed
```

`st/ld` has **26 slots** (`0..25`) per expression instance. Use them to avoid re-computing an expensive sub-expression inside the same pixel pass.

### Number literals

Decimal (`3.14`), integer (`255`), hex (`0xff`). Time-like literals (`1K`, `1M`) are honoured in some filters but not inside expressions — use plain numbers.

---

## 2. Per-filter variables

### 2.1 `geq` (video, per-pixel)

| Name | Meaning |
|---|---|
| `X`, `Y` | 0-based pixel coords in the current plane |
| `W`, `H` | plane width / height in pixels |
| `SW`, `SH` | sub-sampling factor: `chroma_W / luma_W` (0.5 on 4:2:0 chroma planes, 1.0 on luma) |
| `T` | timestamp of current frame in seconds (float) |
| `N` | frame index (integer) |
| `p(x,y)` | current-plane value at (x,y). In a `lum=` expression this is luma; in a `cb=` expression it's Cb; etc. |
| `lum(x,y)` | luma value at (x,y) regardless of current plane |
| `cb(x,y)`, `cr(x,y)` | chroma values at (x,y) |
| `alpha(x,y)` | alpha value at (x,y) if input has alpha |
| `r(x,y)`, `g(x,y)`, `b(x,y)` | R, G, B values (RGB inputs only; pre-format with `format=gbrp`) |
| `interlaced` | 1 if frame is interlaced, else 0 |

**Per-plane expressions** map to filter option names: `lum`/`cb`/`cr`/`alpha` for YUV, `r`/`g`/`b`/`a` for RGB. Missing planes default to a passthrough of the source.

### 2.2 `aeval` / `aevalsrc` (audio, per-sample)

| Name | Meaning |
|---|---|
| `ch` | 0-based output channel index |
| `val(i)` | current-sample value of input channel `i` (only in `aeval`) |
| `nb_in_channels` | input channel count (only in `aeval`) |
| `nb_out_channels` | output channel count |
| `s` | sample rate (Hz) |
| `t` | time of current sample in seconds (float) |
| `n` | sample index |

Per-channel expressions are separated with `|`, e.g. `aeval=val(0)*0.5|val(1)*0.5`.

### 2.3 `lut2` (two video inputs)

| Name | Meaning |
|---|---|
| `x` | sample from input 0 |
| `y` | sample from input 1 |
| `bdx`, `bdy` | bit depth of input 0, input 1 |
| `N` | frame number |

Same expression can be given per-component via `c0`, `c1`, `c2`, `c3`. Both inputs **must share dimensions and pixel format**.

### 2.4 `drawgraph` (video metadata → chart)

Values come from **upstream filter metadata** (not variables in an expression). You pick up to 4 metric keys with `m1`, `m2`, `m3`, `m4`. Colors via `fg1..fg4` (hex 0xRRGGBB or 0xAARRGGBB). Range with `min`/`max`. Output size with `size=WxH`. Modes: `bar`, `dot`, `line`. Background defaults transparent — set `bg=black` for a standalone panel.

### 2.5 `drawvg` (SVG/VGS rendering)

Uses the VGS (Vector Graphics Script) mini-language, not the main expression evaluator. Inputs come from `source=` (inline SVG/VGS string) or `sourcefile=` (path). New filter — check availability with `ffmpeg -filters | grep drawvg`.

### 2.6 `random` (frame shuffle)

Options: `frames` (window size), `seed`. No expressions.

### 2.7 `feedback` (recursive PiP)

Required: `x`, `y`, `w`, `h`. Missing any one makes it a no-op.

### 2.8 `lagfun` (dark decay)

Option: `decay` (0..1). Applied per-plane; defaults to all planes — set `planes=` bitmask to limit.

---

## 3. Store/Load usage

When an expression recomputes the same thing multiple times, cache with `st()`/`ld()`:

```
# Vignette with cached radius²
geq=lum='st(0, pow((X-W/2)/(W/2),2) + pow((Y-H/2)/(H/2),2)); lum(X,Y) * clip(1-ld(0), 0, 1)'
```

Expressions are evaluated left-to-right; `;` separates statements within one expression string; the final expression value is returned.

---

## 4. Worked geq recipes

Prepend `format=gbrp,` when a recipe uses `r/g/b`. All are tested on a short clip — adjust `W`/`H` refs as needed.

### Gradients
```
# Horizontal grayscale ramp
geq=lum='255*X/W':cb=128:cr=128

# Diagonal RGB
format=gbrp,geq=r='255*X/W':g='255*Y/H':b='255*(X+Y)/(W+H)'

# Radial gradient (white → black from center)
geq=lum='255*(1-hypot((X-W/2)/(W/2),(Y-H/2)/(H/2)))':cb=128:cr=128
```

### Channel ops
```
# BGR swap
format=gbrp,geq=r='b(X,Y)':g='g(X,Y)':b='r(X,Y)'

# Red only
format=gbrp,geq=r='r(X,Y)':g=0:b=0

# Invert
geq=lum='255-lum(X,Y)':cb='255-cb(X,Y)':cr='255-cr(X,Y)'

# Grayscale (broadcast Y)
geq=lum='lum(X,Y)':cb=128:cr=128
```

### Geometric
```
# Horizontal flip
geq=p(W-X\,Y)

# Vertical flip
geq=p(X\,H-Y)

# 2× zoom from center
geq=p(W/4+X/2\,H/4+Y/2)

# Pinwheel / twirl
geq=p(W/2 + hypot(X-W/2,Y-H/2)*cos(atan2(Y-H/2,X-W/2)+T) \, H/2 + hypot(X-W/2,Y-H/2)*sin(atan2(Y-H/2,X-W/2)+T))
```

### Lighting / vignette
```
# Soft vignette (luma only)
geq=lum='lum(X,Y) * clip(1 - pow((X-W/2)/(W/2),2) - pow((Y-H/2)/(H/2),2), 0, 1)'

# RGB vignette
format=gbrp,geq=r='r(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)':g='g(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)':b='b(X,Y)*clip(1-pow((X-W/2)/(W/2),2)-pow((Y-H/2)/(H/2),2),0,1)'

# Moving spotlight
geq=lum='lum(X,Y) * clip(1 - hypot(X-W/2-100*sin(T), Y-H/2-100*cos(T))/300, 0, 1)':cb='cb(X,Y)':cr='cr(X,Y)'
```

### Creative patterns
```
# Plasma
format=gbrp,geq=r='128+127*sin(X/20+T)':g='128+127*sin(Y/20+T*1.3)':b='128+127*sin((X+Y)/20+T*0.7)'

# Checkerboard
geq=lum='if(eq(mod(floor(X/32)+floor(Y/32),2),0),255,0)':cb=128:cr=128

# Static white noise
geq=lum='random(0)*255':cb=128:cr=128

# Film-grain add (adds noise to luma)
geq=lum='clip(lum(X,Y)+random(0)*20-10,0,255)':cb='cb(X,Y)':cr='cr(X,Y)'

# Moving sine stripes
geq=lum='128+127*sin(2*PI*X/40 + T*4)':cb=128:cr=128

# Rings
geq=lum='128+127*sin(hypot(X-W/2,Y-H/2)/10 - T*4)':cb=128:cr=128

# Plasma with store/load cache
format=gbrp,geq=r='st(0,sin(X/20+T)); 128+127*ld(0)':g='128+127*sin(Y/20+T*1.3)':b='128+127*sin((X+Y)/20+T*0.7)'

# Mandelbrot-ish (slow)
geq=lum='st(0,(X-W/2)/(W/4)); st(1,(Y-H/2)/(H/4)); st(2,0); st(3,0); st(4,0); while(lt(ld(4),32) * lt(ld(2)*ld(2)+ld(3)*ld(3),4), st(5,ld(2)*ld(2)-ld(3)*ld(3)+ld(0)); st(3,2*ld(2)*ld(3)+ld(1)); st(2,ld(5)); st(4,ld(4)+1)); ld(4)*8':cb=128:cr=128
```
(Note: `while()` isn't in all FFmpeg builds — most ship without it. The above is illustrative; prefer pre-built `mandelbrot` lavfi source.)

### Chromatic / color effects
```
# Chromatic aberration (RGB needs format=gbrp)
format=gbrp,geq=r='r(X+2,Y)':g='g(X,Y)':b='b(X-2,Y)'

# Hue rotate (approx, YUV)
geq=lum='lum(X,Y)':cb='128 + (cb(X,Y)-128)*cos(T) - (cr(X,Y)-128)*sin(T)':cr='128 + (cb(X,Y)-128)*sin(T) + (cr(X,Y)-128)*cos(T)'

# Posterize (4 levels)
geq=lum='floor(lum(X,Y)/64)*64':cb='cb(X,Y)':cr='cr(X,Y)'

# Solarize
geq=lum='if(gt(lum(X,Y),128),255-lum(X,Y),lum(X,Y))':cb='cb(X,Y)':cr='cr(X,Y)'
```

### Displacement / warp
```
# Ripple
geq=p(X + 4*sin(Y/12+T*4) \, Y)

# Barrel pinch
geq=p(W/2 + (X-W/2)*(1 + 0.2*hypot((X-W/2)/(W/2),(Y-H/2)/(H/2))^2) \, H/2 + (Y-H/2)*(1 + 0.2*hypot((X-W/2)/(W/2),(Y-H/2)/(H/2))^2))

# Sinusoidal wobble
geq=p(X + 8*sin(Y/20+T) \, Y + 8*cos(X/20+T))
```

### Edge / blur / convolution via geq
```
# Tiny box blur (3×3 average)
geq=lum='(p(X-1,Y-1)+p(X,Y-1)+p(X+1,Y-1)+p(X-1,Y)+p(X,Y)+p(X+1,Y)+p(X-1,Y+1)+p(X,Y+1)+p(X+1,Y+1))/9':cb='cb(X,Y)':cr='cr(X,Y)'

# Emboss (from FFmpeg docs)
format=gray,geq=lum='(p(X,Y)+(256-p(X-4,Y-4)))/2'

# Sobel-X (edge detect, approx)
format=gray,geq=lum='clip(p(X+1,Y-1) + 2*p(X+1,Y) + p(X+1,Y+1) - p(X-1,Y-1) - 2*p(X-1,Y) - p(X-1,Y+1) + 128, 0, 255)'
```

### Temporal
```
# Time-based luma pulse
geq=lum='lum(X,Y) * (0.5 + 0.5*sin(T*2*PI))':cb='cb(X,Y)':cr='cr(X,Y)'

# Moving scanline
geq=lum='if(lt(abs(Y-mod(T*100,H)),4), 255, lum(X,Y))':cb='cb(X,Y)':cr='cr(X,Y)'
```

---

## 5. `drawgraph` metadata catalog

`drawgraph` reads **metadata keys** set by upstream filters. Common producers:

### `signalstats` (must be upstream)
- `lavfi.signalstats.YAVG` — luma average
- `lavfi.signalstats.YMIN` / `YMAX`
- `lavfi.signalstats.UAVG` / `VAVG`
- `lavfi.signalstats.YDIF` — per-frame luma diff
- `lavfi.signalstats.SATAVG` / `SATMIN` / `SATMAX`
- `lavfi.signalstats.HUEAVG` / `HUEMED`
- `lavfi.signalstats.TOUT`, `VREP`, `BRNG` — QC flags (out-of-range, vertical repetition, broadcast-range)

### `ebur128` (audio loudness, use `adrawgraph`)
- `lavfi.r128.M` — momentary LUFS
- `lavfi.r128.S` — short-term LUFS
- `lavfi.r128.I` — integrated LUFS
- `lavfi.r128.LRA` — loudness range
- `lavfi.r128.LRA.low` / `.high`
- `lavfi.r128.sample_peaks_ch0` etc.

### `blockdetect`
- `lavfi.block` — blocking score (0..1)

### `blurdetect`
- `lavfi.blur` — blur score (0..1)

### `freezedetect`
- `lavfi.freezedetect.freeze_start`
- `lavfi.freezedetect.freeze_duration`
- `lavfi.freezedetect.freeze_end`

### `psnr`, `ssim`, `libvmaf`
- `lavfi.psnr.psnr_avg` etc.
- `lavfi.ssim.All`
- `lavfi.vmaf.VMAF_score`

Usage:
```
signalstats,drawgraph=m1=lavfi.signalstats.YAVG:fg1=0xffff00:m2=lavfi.signalstats.SATAVG:fg2=0x00ffff:min=0:max=255:size=1920x120:bg=black
```
Multi-stream example (loudness + video brightness side-by-side) requires two `drawgraph` instances, one on each stream, then `vstack`.

---

## 6. Debug workflow

1. **Start tiny.** Always test with a 2-second clip: `-t 2` or `-frames:v 1` for a single frame.
2. **Turn up logging.** `-loglevel debug` prints expression tokens as they parse. Search stderr for `Error when evaluating`.
3. **Use `print()`** inside any expression to dump values:
   ```
   geq=lum='print(T); 255*X/W':cb=128:cr=128
   ```
   `print()` returns its argument, so it drops into any subexpression without changing output.
4. **Simplify.** Strip the expression to a constant (e.g. `lum=128`) and confirm the pipeline runs. Add terms back one at a time.
5. **Escape commas.** Inside a function call you must backslash-escape `,` (e.g. `p(W-X\,Y)`), OR wrap the whole filter argument in single quotes on the shell.
6. **RGB problems → add `format=gbrp`.** Easily 80% of geq-RGB bugs.
7. **Silent black output** → expression parse error. Step 2.
8. **0.3 fps** → expression is too expensive, cache with `st/ld`, or switch to a native filter.
9. **Two-input filter "dimensions differ"** → normalize with `scale=W:H,format=yuv420p` on both inputs first.
10. **Verify live docs:** `python3 .claude/skills/ffmpeg-docs/scripts/ffdocs.py search --query <filter> --page ffmpeg-filters` catches syntax drift between FFmpeg versions.

---

## 7. Quick reference card

```
CONSTANTS:  PI  E  PHI  TAU
UNARY:      +  -  !
BINARY:     +  -  *  /  %  ^  &&  ||
COMPARE:    gt  lt  gte  lte  eq  (functions, not operators)
CONTROL:    if(c,t,e)  ifnot(c,e)  between(v,a,b)  clip(v,lo,hi)
MATH:       sin cos tan asin acos atan atan2
            sinh cosh tanh exp log sqrt pow hypot
            abs floor ceil round trunc mod min max
STATE:      st(N,v)  ld(N)  [N in 0..25]
DEBUG:      print(v)
RANDOM:     random(seed)
```
