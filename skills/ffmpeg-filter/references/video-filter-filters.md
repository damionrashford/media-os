# ffmpeg Video Filters — Reference

Exhaustive options, expression variables, escaping rules, and 50+ compiled recipes for the filters covered by this skill. All self-contained; no external links required to use.

## Contents

1. Filter option tables (scale, crop, pad, overlay, drawtext, eq, curves, yadif, fps, colorspace, and others)
2. Expression evaluation cheat-sheet
3. `-filter_complex` label & map rules
4. Escaping rules (three levels for drawtext)
5. Compiled recipes (50+)

---

## 1. Filter option tables

### `scale`

| Option | Values | Notes |
|---|---|---|
| `w` / `width` | integer, expression, `-1`, `-2` | `-1` keeps aspect; `-2` keeps aspect AND ensures divisibility by 2. |
| `h` / `height` | integer, expression, `-1`, `-2` | same as `w`. |
| `force_original_aspect_ratio` | `disable` (default), `decrease`, `increase` | `decrease` = fit inside box (letterbox); `increase` = fill box (crop). |
| `force_divisible_by` | integer (default 1) | Round final dims to a multiple. Useful with `-1`. |
| `flags` | `fast_bilinear`, `bilinear`, `bicubic` (default), `experimental`, `neighbor`, `area`, `bicublin`, `gauss`, `sinc`, `lanczos`, `spline` | See scaler algorithm notes below. |
| `sws_dither` | `none`, `auto`, `bayer`, `ed`, `a_dither`, `x_dither` | Dithering for 10-bit → 8-bit downscales. |
| `in_color_matrix` / `out_color_matrix` | `auto`, `bt601`, `bt709`, `smpte170m`, `bt2020` | Override color matrix during resample. |
| `in_range` / `out_range` | `auto`, `full`/`pc`/`jpeg`, `limited`/`tv`/`mpeg` | Fix full-vs-limited range mismatches. |

Scaler algorithms (when to pick):
- `bicubic` — default, good all-rounder.
- `lanczos` — sharpest downscale; best choice for 1080→720 or 4K→1080.
- `bilinear` / `fast_bilinear` — fast, soft.
- `neighbor` — pixel art, zero interpolation.
- `area` — clean downscale without ringing.
- `spline` — smoother than lanczos, slightly less sharp.
- `gauss` — upscale without ringing.

### `crop`

| Option | Values | Notes |
|---|---|---|
| `w` | expression | Output width. Default `iw`. |
| `h` | expression | Output height. Default `ih`. |
| `x` | expression | Horizontal offset of top-left. Default `(iw-ow)/2` (centered). |
| `y` | expression | Vertical offset. Default `(ih-oh)/2`. |
| `keep_aspect` | 0/1 | If 1, output SAR is adjusted so DAR matches input. |
| `exact` | 0/1 | If 0, output dims rounded to chroma subsampling grid. |

### `pad`

| Option | Values | Notes |
|---|---|---|
| `w` / `h` | expression | Output dims. |
| `x` / `y` | expression | Where to place input in padded canvas. Centered = `(ow-iw)/2 : (oh-ih)/2`. |
| `color` | color name/hex | Default `black`. Named colors or `0xRRGGBB` or `0xRRGGBBAA`. |
| `aspect` | rational | Alternative to w/h: pad to match a target aspect. |

### `overlay`

| Option | Values | Notes |
|---|---|---|
| `x` / `y` | expression | Position of overlay top-left on main. |
| `eof_action` | `repeat`, `endall`, `pass` | What happens when overlay ends. |
| `format` | `yuv420`, `yuv420p10`, `yuv422`, `yuv444`, `rgb`, `gbrp`, `auto` | Output pixel format; pick `auto` unless you know. |
| `shortest` | 0/1 | End output when shortest input ends. |

Common x/y expressions: `10:10` top-left, `(W-w)/2:(H-h)/2` center, `W-w-10:H-h-10` bottom-right, `W-w-10:10` top-right.

### `drawtext`

| Option | Values | Notes |
|---|---|---|
| `fontfile` | absolute path | **Required on most builds.** See platform paths below. |
| `text` | string | Literal text to draw. Escape `:` as `\:`, `,` as `\,`, `%` as `\%`. |
| `textfile` | path | Read text from file instead of `text=`. |
| `timecode` | `'HH\:MM\:SS\:FF'` | Auto-advances by `rate`. Overrides `text`. |
| `rate` / `r` | fps | Required with `timecode`. |
| `fontsize` | int | Pixels. |
| `fontcolor` | color | `white`, `black`, `#RRGGBB`, `red@0.5`. |
| `x` / `y` | expression | Supports `W`, `H`, `w` (text w), `h` (text h), `t` (time), `n` (frame). |
| `box` | 0/1 | Draw background box. |
| `boxcolor` | color | Box fill color. |
| `boxborderw` | int | Box padding in px. |
| `borderw` | int | Text outline width. |
| `bordercolor` | color | Outline color. |
| `shadowx` / `shadowy` | int | Drop-shadow offset. |
| `shadowcolor` | color | |
| `line_spacing` | int | Extra px between lines. |
| `alpha` | 0.0–1.0 or expr | Per-glyph alpha. |
| `enable` | expression | Gate the draw. E.g. `enable='between(t,10,20)'`. |
| `expansion` | `none`, `strftime`, `normal` (default) | `normal` allows `%{...}` sequences like `%{pts}`, `%{localtime}`, `%{n}`. |

Platform font paths:
- macOS: `/System/Library/Fonts/Supplemental/Arial.ttf` or `/Library/Fonts/Arial.ttf`.
- Linux: `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`.
- Windows: `C\:/Windows/Fonts/arial.ttf` (note escaped colon).

### `eq`

| Option | Range | Notes |
|---|---|---|
| `brightness` | -1.0 to 1.0 | 0 = unchanged. |
| `contrast` | -1000 to 1000 | 1 = unchanged. |
| `saturation` | 0 to 3 | 1 = unchanged. 0 = grayscale. |
| `gamma` | 0.1 to 10 | 1 = unchanged. |
| `gamma_r`, `gamma_g`, `gamma_b` | 0.1 to 10 | Per-channel gamma. |
| `gamma_weight` | 0 to 1 | Reduces gamma effect on bright areas. |

### `curves`

| Option | Values |
|---|---|
| `preset` | `none`, `color_negative`, `cross_process`, `darker`, `increase_contrast`, `lighter`, `linear_contrast`, `medium_contrast`, `negative`, `strong_contrast`, `vintage` |
| `master` / `m` | `"0/0 0.5/0.6 1/1"` (control points) |
| `red` / `r`, `green` / `g`, `blue` / `b` | per-channel curve control points |
| `psfile` | `.acv` Photoshop curves file | |

### `yadif` / `bwdif`

| Option | Values | Notes |
|---|---|---|
| `mode` | `0` (send_frame, one output per frame, halves fps), `1` (send_field, two output frames per input frame, keeps fps), `2` (send_frame_nospatial), `3` (send_field_nospatial) | |
| `parity` | `0` (tff), `1` (bff), `-1` (auto) | Field order. |
| `deint` | `0` (all), `1` (interlaced only) | |

`bwdif` same options; generally higher quality than `yadif`.

### `fps` / `minterpolate`

`fps=fps=30[:round=near|up|down|zero]` — cheap drop/dup frame rate conversion.

`minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1` — motion-compensated interpolation. Expensive. Use for slow-motion or smooth 24→60 pulldown.

### `colorspace`

Convert between color spaces. Common args: `colorspace=all=bt709:iall=bt601-6-625:fast=1`. Parameters: `all`, `space`, `trc`, `primaries`, `range`, `format`, `iall`, `ispace`, `itrc`, `iprimaries`, `irange`, `iformat`.

### Other quick-reference

| Filter | Canonical form |
|---|---|
| `setsar` | `setsar=1` — force square pixels. |
| `setdar` | `setdar=16/9` — force display aspect. |
| `rotate` | `rotate=PI/4:ow=hypot(iw,ih):oh=ow:c=black` |
| `transpose` | `transpose=0` (90° CCW + vflip), `1` (90° CW), `2` (90° CCW), `3` (90° CW + vflip) |
| `hflip`, `vflip` | no args |
| `hue` | `hue=h=90:s=1.2` (h in degrees, s multiplier) |
| `colorchannelmixer` | 12 floats: `rr:rg:rb:ra:gr:gg:gb:ga:br:bg:bb:ba` |
| `colorlevels` | `rimin=.058:gimin=.058:bimin=.058` (per-channel levels) |
| `noise` | `noise=alls=20:allf=t+u` (strength + flags t=temporal, u=uniform, a=avg, p=pattern) |
| `unsharp` | `unsharp=5:5:1.0:5:5:0.0` (lx:ly:la:cx:cy:ca) |
| `boxblur` | `boxblur=2:1` (radius:steps) |
| `gblur` | `gblur=sigma=2:steps=1` |
| `fade` | `fade=t=in:st=0:d=1` or `fade=t=out:st=10:d=1:alpha=1` |
| `zoompan` | `zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1280x720` |
| `trim` | `trim=start=5:end=15,setpts=PTS-STARTPTS` |
| `setpts` | `setpts=0.5*PTS` (2x speed), `setpts=2*PTS` (half speed) |
| `split` | `split=2[a][b]` (fan out to 2 copies) |
| `format` | `format=yuv420p` or `format=yuva420p` |
| `null` | pass-through |
| `drawbox` | `drawbox=x=10:y=10:w=100:h=50:color=red@0.5:t=fill` |

---

## 2. Expression evaluation cheat-sheet

Filter arguments (most of them, anywhere the docs say "expression") accept these variables and functions.

**Input/frame variables:**
- `iw`, `ih` — input width, height.
- `ow`, `oh` — output width, height (where meaningful — in pad, scale, crop).
- `W`, `H` — main video dims (in overlay/drawtext, refers to background).
- `w`, `h` — overlay/drawtext element dims (in overlay: the overlay; in drawtext: rendered text).
- `x`, `y` — previous x/y (for recurring expressions).
- `t` — timestamp in seconds (float).
- `n` — frame number (0-indexed).
- `pos` — byte position of current packet.
- `sar` — sample aspect ratio.
- `dar` — display aspect ratio.
- `hsub`, `vsub` — chroma subsampling factors.
- `pts` — presentation timestamp in time_base units.

**Functions:**
- Arithmetic: `+ - * / ^` and parentheses.
- `abs(x)`, `min(a,b)`, `max(a,b)`, `mod(a,b)`, `hypot(a,b)`, `sqrt(x)`.
- Comparison: `eq(a,b)`, `gt(a,b)`, `gte(a,b)`, `lt(a,b)`, `lte(a,b)`.
- Conditional: `if(cond, then)`, `if(cond, then, else)`, `ifnot(...)`.
- Range: `between(val, min, max)` → 1 if inside, 0 otherwise.
- Trig: `sin(x)`, `cos(x)`, `tan(x)`, `atan2(y,x)`. Angles in radians. `PI` constant available.
- Random: `random(seed)` uniform 0..1.

**Examples:**
- Center overlay: `x=(W-w)/2:y=(H-h)/2`
- Bounce overlay: `x=if(lt(mod(t,8),4), (W-w)*mod(t,4)/4, (W-w)*(1-mod(t,4)/4))`
- Only show text for seconds 5–10: `enable='between(t,5,10)'`
- Scroll text right-to-left: `x=W-tw*0.1*t:y=H-lh-10` (where `tw`/`th` are drawtext's text dims)

---

## 3. `-filter_complex` label & map rules

**Syntax.** A filter graph is a sequence of chains separated by `;`. Inside a chain, filters are separated by `,`. Each filter can name inputs and outputs with `[label]`. Unnamed output of one filter flows into unnamed input of the next filter in the same chain.

```text
[0:v]scale=1280:720[a];                                     -- chain 1
[1:v]scale=200:-1[wm];                                      -- chain 2
[a][wm]overlay=W-w-10:H-h-10[v]                             -- chain 3
```

**Input labels.** `[0:v]` = first input file, video. `[0:a]` = first input, audio. `[1:v:0]` = second input, video stream 0.

**Output labels.** Any `[name]` on the right side of a filter is a named pipe. Must be unique within the graph.

**-map rules.**
- Without `-filter_complex`, ffmpeg auto-selects 1 video + 1 audio + 1 subtitle stream.
- With `-filter_complex`, auto-selection is disabled. You must map what you want: `-map "[v]" -map "[a]" -map 0:s?`.
- Trailing `?` on a map (e.g. `-map 0:a?`) means "ignore if not present" — essential for passthrough audio when input may or may not have audio.
- Every named output `[xxx]` in the graph that you want in the output file needs a matching `-map "[xxx]"`.
- You can mix mapped filter outputs with mapped original streams: `-map "[v]" -map 0:a?` keeps processed video but copies audio.

---

## 4. Escaping rules (the three levels)

drawtext's `text=` is the worst offender because three layers of escaping can all apply.

**Level 1 — Shell.** Your shell (bash/zsh) parses the command. Wrap the whole `-vf` or `-filter_complex` value in double or single quotes. Inside double quotes, `$`, `` ` ``, `\`, `"` need escaping. Inside single quotes, nothing does — but you can't include a literal single quote.

**Level 2 — Filter graph.** ffmpeg's filter parser uses `:` to separate options, `,` to separate filters in a chain, `;` to separate chains, `[` `]` for labels, and `\` to escape. So inside a filter argument:
- `:` → `\:`
- `,` → `\,`
- `;` → `\;`
- `[` `]` → `\[` `\]`
- `\` → `\\`
- `'` → `\'`

**Level 3 — drawtext `text=` value.** The text is parsed again for `%{...}` expansion. If you want a literal `%`, write `\%`.

**Practical rule.** The safest way to include punctuation in drawtext is:

```text
drawtext=fontfile=/path/to/font.ttf:text='Hello\, World\: hi':x=10:y=10
```

Notes: single quotes around text so the shell passes it literally; `\,` and `\:` so the filter parser passes them literally.

For complex strings, use `textfile=path.txt` instead of `text=`.

---

## 5. Compiled recipes

### Resize

1. `-vf "scale=1280:720"` — exact.
2. `-vf "scale=-2:720"` — 720p height, aspect preserved.
3. `-vf "scale=1920:-2"` — 1080p width, aspect preserved.
4. `-vf "scale=iw/2:ih/2"` — half.
5. `-vf "scale=iw*2:ih*2:flags=neighbor"` — pixel-art 2x.
6. `-vf "scale=1920:1080:flags=lanczos"` — high-quality 1080p.
7. `-vf "scale=w=min(1920\,iw):h=-2"` — cap at 1920 wide, never upscale.

### Letterbox / pillarbox

8. `-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"` — fit in 1080p.
9. `-vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"` — landscape → 9:16 portrait with bars.
10. `-vf "crop=ih*16/9:ih,scale=1920:1080"` — crop 4:3 to 16:9 then resize.

### Crop

11. `-vf "crop=1280:720"` — center 720p.
12. `-vf "crop=iw-200:ih:100:0"` — shave 100px from left+right.
13. `-vf "crop=w=ih*9/16:h=ih"` — pillarbox a 16:9 source to 9:16.

### Rotate / flip

14. `-vf "transpose=1"` — rotate 90° CW.
15. `-vf "transpose=2"` — rotate 90° CCW.
16. `-vf "transpose=2,transpose=2"` — rotate 180°.
17. `-vf "hflip"` — mirror.
18. `-vf "vflip"` — flip vertical.
19. `-vf "rotate=PI/6:c=black"` — arbitrary 30° rotation.

### Aspect fixes

20. `-vf "setsar=1"` — square pixels.
21. `-vf "setdar=16/9"` — claim 16:9 DAR.

### Deinterlace

22. `-vf "yadif=1"` — keep fps.
23. `-vf "yadif=0"` — halve fps (50i → 25p).
24. `-vf "bwdif=1:-1:1"` — higher-quality, auto parity, skip progressive.

### Frame rate

25. `-vf "fps=30"` — drop/dup to 30fps.
26. `-vf "fps=60,setpts=N/60/TB"` — force 60fps with new timestamps.
27. `-vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"` — motion-compensated 60fps.

### Color / eq

28. `-vf "eq=brightness=0.05:saturation=1.2"` — slight boost.
29. `-vf "eq=contrast=1.3:gamma=0.9"` — punchier, darker.
30. `-vf "curves=preset=increase_contrast"` — preset contrast curve.
31. `-vf "curves=preset=vintage"` — stylized vintage look.
32. `-vf "hue=h=180:s=1"` — invert hue.
33. `-vf "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3"` — luma-weighted grayscale.
34. `-vf "colorlevels=rimin=0.058:gimin=0.058:bimin=0.058"` — crush blacks.
35. `-vf "colorspace=all=bt709:iall=bt601-6-625"` — SD → HD color space.
36. `-vf "lutyuv=y=negval:u=negval:v=negval"` — color-negative.

### Sharpen / blur / denoise

37. `-vf "unsharp=5:5:1.0:5:5:0.0"` — sharpen luma only.
38. `-vf "unsharp=5:5:-1.0:5:5:0.0"` — negative amount = blur.
39. `-vf "gblur=sigma=2"` — gaussian blur.
40. `-vf "boxblur=2:1"` — cheap box blur.
41. `-vf "noise=alls=20:allf=t+u"` — add film-grain noise.
42. `-vf "hqdn3d=4:3:6:4.5"` — denoise (slower, better).

### Overlay / watermark

43. `-filter_complex "[1:v]format=yuva420p,scale=200:-1[wm];[0:v][wm]overlay=W-w-20:H-h-20"` — PNG watermark.
44. `-filter_complex "[1:v]scale=320:-1[pip];[0:v][pip]overlay=W-w-20:20"` — picture-in-picture top-right.
45. `-filter_complex "[1:v]setpts=PTS-STARTPTS[fg];[0:v]setpts=PTS-STARTPTS[bg];[bg][fg]overlay=enable='between(t,2,8)'"` — overlay only 2-8s.

### Stacks

46. `-filter_complex "[0:v][1:v]hstack=inputs=2"` — side by side (equal height required).
47. `-filter_complex "[0:v][1:v][2:v]hstack=inputs=3"` — 3-up.
48. `-filter_complex "[0:v][1:v]vstack"` — over/under.
49. `-filter_complex "[0:v][1:v][2:v][3:v]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0"` — 2x2 grid.

### Text

50. `-vf "drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:text='Hello':x=20:y=20:fontsize=48:fontcolor=white"` — static text.
51. `-vf "drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:timecode='00\:00\:00\:00':rate=25:fontsize=32:fontcolor=white:box=1:boxcolor=black@0.5:x=20:y=20"` — running timecode.
52. `-vf "drawtext=fontfile=/path/font.ttf:textfile=caption.txt:x=(w-tw)/2:y=h-lh-20:fontcolor=white:box=1:boxcolor=black@0.6"` — bottom-center caption from file.
53. `-vf "drawtext=fontfile=/path/font.ttf:text='%{localtime\:%T}':x=10:y=10"` — wall-clock time.
54. `-vf "drawbox=x=10:y=10:w=200:h=50:color=red@0.5:t=fill"` — filled red box.

### Fades & transitions

55. `-vf "fade=t=in:st=0:d=1"` — 1-sec fade-in.
56. `-vf "fade=t=out:st=10:d=1"` — fade-out starting at 10s.
57. `-filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=4"` — crossfade between clips at 4s.

### Trim & speed

58. `-vf "trim=start=5:end=15,setpts=PTS-STARTPTS"` — keep 5–15s.
59. `-vf "setpts=0.5*PTS"` — 2x speed (drop frames).
60. `-vf "minterpolate=fps=60,setpts=0.25*PTS"` — 4x speed with smooth motion.

### Zoom / pan (Ken Burns)

61. `-vf "zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1280x720:fps=25"` — slow zoom-in.
62. `-vf "zoompan=z=1.5:x='iw/2-(iw/zoom/2)':y=0:d=125:s=1280x720"` — pan from top.

### Split / fan-out

63. `-filter_complex "[0:v]split=2[main][blur];[blur]gblur=sigma=20,scale=1920:1080[bg];[bg][main]overlay=(W-w)/2:(H-h)/2"` — blurred background behind small main video.

### Format / pipeline glue

64. `-vf "format=yuv420p"` — force 8-bit 4:2:0 (web compat).
65. `-vf "format=yuv420p10le"` — force 10-bit for HDR/HEVC.
66. `-vf "null"` — explicit no-op.

---

## Gotchas (compiled)

- `scale=-1:720` can produce odd widths; use `scale=-2:720` with most codecs.
- `overlay` defaults to first-frame's pixel format — add `format=yuva420p` before overlay when the overlay has alpha.
- `drawtext` without `fontfile=` requires fontconfig; many static ffmpeg builds ship without it.
- Three-level escaping (shell, filter, drawtext text) is the most common source of bizarre syntax errors.
- `-filter_complex` disables automatic stream selection — always `-map`.
- `setpts=PTS-STARTPTS` is mandatory after `trim` if you want the output to start at t=0.
- `hstack`/`vstack` require matching dimensions — scale first.
- `fps` drops/dupes frames; `minterpolate` generates new ones (costly).
- `setsar=1` after any scale prevents downstream aspect-ratio confusion.
- `yadif=0` vs `yadif=1`: mode 0 halves fps, mode 1 keeps fps — pick consciously.
