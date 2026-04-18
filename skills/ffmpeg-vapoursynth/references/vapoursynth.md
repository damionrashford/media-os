# VapourSynth reference

## 1. Plugin catalog (by category)

### Source filters

| Plugin | Namespace | Call | Notes |
|---|---|---|---|
| FFmpegSource 2 | `ffms2` | `core.ffms2.Source("in.mkv")` | General-purpose; indexes first run (`in.mkv.ffindex`). |
| L-SMASH Works | `lsmas` | `core.lsmas.LWLibavSource("in.mp4")` / `LSMASHSource` | Frame-accurate seeking on MP4. |
| d2vsource | `d2v` | `core.d2v.Source("in.d2v")` | MPEG-2 DVD; use DGIndex to make the `.d2v`. |
| DGDecNV | `dgdecodenv` | `core.dgdecodenv.DGSource("in.dgi")` | NVIDIA hardware decode. |
| AviSource (AVS+) | `avisource` | `core.avisource.AVISource("in.avs")` | Run an AviSynth+ script from inside VS. |
| ImageMagick | `imwri` | `core.imwri.Read("frame%04d.png")` | Image sequences. |
| BestSource | `bs` | `core.bs.VideoSource("in.mkv")` | Exact seeking, slower. |

### Deinterlace / interpolate

- `nnedi3` — neural-net edge interpolation (needed by QTGMC).
- `EEDI3` / `eedi3m` — edge-directed interpolation.
- `mvtools` — motion-compensated vectors; foundation for QTGMC and custom FPS.
- `havsfunc.QTGMC(clip, Preset=..., TFF=...)` — gold-standard deinterlacer.
- `svpflow` (`svp1`, `svp2`) — SmoothVideo motion interpolation (24 → 60).

### Denoise

- `knlm` — KNLMeansCL (OpenCL non-local means).
- `bm3dcuda` / `bm3dcpu` — BM3D (3-D collaborative filtering), CUDA or CPU.
- `dfttest` — FFT frequency-domain denoise.
- `fft3dfilter` — 3-D FFT denoise.
- `neo_fft3d` — modernized fft3dfilter.
- `vs-miscfilters-obsolete` — `TemporalSoften`, etc.
- `removegrain` / `rgvs` — RemoveGrain ports.
- `havsfunc.SMDegrain(clip, tr=3, thSAD=300)` — motion-compensated temporal denoise.

### Resize / format conversion

- `std` — built-in (`core.std.Crop`, `Expr`, `Merge`, `AssumeFPS`, …).
- `resize` — built-in (`clip.resize.Bicubic(format=vs.YUV420P10)`).
- `fmtc` (fmtconv) — higher-quality bit-depth and color conversions.
- `zimg` — used under the hood by `resize`.

### Color / grading

- `adjust` — Python module (`adjust.Tweak(clip, hue=..., sat=..., bright=..., cont=...)`).
- `havsfunc.FineDehalo` / `DeHalo_alpha` — halo removal.
- `havsfunc.EdgeCleaner`, `havsfunc.FastLineDarkenMOD`.

### Subtitles / overlay

- `assrender` / `sub` — ASS/SSA burn-in.
- `std.MaskedMerge` — composite with alpha.

## 2. QTGMC preset comparison

| Preset | Quality | Relative speed | Typical use |
|---|---|---|---|
| `Draft` | Very low | 10× fastest | Scrubbing previews only |
| `Ultra Fast` | Low | ~8× | Rough proxy |
| `Super Fast` | Low-mid | ~5× | Editorial proxy |
| `Very Fast` | Mid | ~3× | Quick rough cut |
| `Faster` | Mid | ~2× | Fast good-enough TV work |
| `Fast` | Mid-high | ~1.5× | Balanced |
| `Medium` | High | 1× (reference) | Default web release |
| `Slow` | High | ~0.7× | Archive-grade |
| `Slower` | Very high | ~0.4× | Recommended archival preset |
| `Very Slow` | Near-max | ~0.2× | Master deliverables |
| `Placebo` | Marginal gain | ~0.1× | Diminishing returns |

Key QTGMC params:

| Param | Meaning | Typical |
|---|---|---|
| `Preset` | Quality/speed tradeoff | `"Slower"` |
| `TFF` | Top Field First | `True` for NTSC DV/DVB, check `idet` if unsure |
| `InputType` | 0 = interlaced; 1 = progressive w/ combing; 2 = static noise | `0` |
| `SourceMatch` | 0–3, higher = more detail retention | `3` for archival |
| `Lossless` | 0 (off), 1, 2 | `2` for near-lossless detail |
| `FPSDivisor` | 1 = double-rate (60p from 30i), 2 = same-rate (30p from 30i) | `1` for smooth motion |
| `EZDenoise` | Enables light built-in denoise | `0` (prefer external) |
| `Sharpness` | Post-sharpening | `0.2` |
| `NoiseProcess` | 0 off, 1 denoise, 2 restore grain | `0` |

## 3. `havsfunc` / `mvsfunc` / `adjust` — commonly used functions

### havsfunc
`QTGMC`, `SMDegrain`, `FineDehalo`, `DeHalo_alpha`, `EdgeCleaner`, `FastLineDarkenMOD`, `LSFmod`, `Deblock_QED`, `Stab`, `STPresso`, `SigmoidInverse` / `SigmoidDirect`, `Bob`, `daa`, `santiag`.

### mvsfunc
`ToYUV`, `ToRGB`, `BM3D`, `Depth` (bit-depth convert with dithering), `GetPlane`, `LimitFilter`, `PlaneStatistics`.

### adjust
`Tweak(clip, hue=..., sat=..., bright=..., cont=..., coring=True)`.

### vsutil
`get_y`, `join`, `depth`, `get_depth`, `get_w`, `get_h`, `iterate`, `scale_value`, `plane`.

## 4. Format family and bit-depth constants

```python
vs.GRAY, vs.YUV, vs.RGB                       # color families
vs.GRAY8,  vs.GRAY16, vs.GRAYS                # S = 32-bit float
vs.YUV420P8, vs.YUV420P10, vs.YUV420P16
vs.YUV422P8, vs.YUV422P10, vs.YUV422P16
vs.YUV444P8, vs.YUV444P10, vs.YUV444P16, vs.YUV444PS
vs.RGB24, vs.RGB30, vs.RGB48, vs.RGBS
```

Bit-depth conversion:

```python
clip = clip.resize.Bicubic(format=vs.YUV420P10)
# or higher-quality dither:
from mvsfunc import Depth
clip = Depth(clip, 10, dither="error_diffusion")
```

## 5. vspipe CLI flags

```
vspipe [options] script.vpy output

Options
  --y4m,   -y           Emit Y4M (required for piping to ffmpeg video)
  --outputindex N, -o N Select output node N (default 0)
  --start N, -s N       Start frame
  --end N,   -e N       End frame (inclusive)
  --requests N, -r N    Concurrent frame requests
  --arg KEY=VAL, -a     Pass arg to script as VS "arg" var
  --container y4m|wav   Force container
  --progress, -p        Show progress
  --info,     -i        Print clip info, no output
  --version, -v         Print version
```

Multi-output pick:

```bash
vspipe --y4m -o 1 script.vpy -  # pick output #1
```

Argument passing:

```python
# script.vpy
import vapoursynth as vs
core = vs.core
src_path = globals().get("src", "default.mkv")
clip = core.ffms2.Source(src_path)
clip.set_output()
```

```bash
vspipe --arg src=movie.mkv --y4m script.vpy - | ffmpeg -i - ...
```

## 6. ffmpeg integration patterns

### Pipe (universal)

```bash
vspipe --y4m script.vpy - | ffmpeg -i - -c:v libx264 -crf 18 out.mp4
```

### Direct demuxer (ffmpeg built with `--enable-vapoursynth`)

```bash
ffmpeg -f vapoursynth -i script.vpy -c:v libx264 -crf 18 out.mp4
```

Verify support:

```bash
ffmpeg -hide_banner -demuxers | grep vapoursynth
```

### Preserve original audio

```bash
vspipe --y4m script.vpy - | \
  ffmpeg -i - -i original.mkv \
    -map 0:v -map 1:a -c:v libx264 -crf 18 -c:a copy out.mkv
```

### 10-bit pipeline

```python
clip = clip.resize.Bicubic(format=vs.YUV420P10)  # in .vpy
```

```bash
vspipe --y4m script.vpy - | \
  ffmpeg -i - -c:v libx265 -pix_fmt yuv420p10le -crf 18 out.mkv
```

### Preview with ffplay

```bash
vspipe --y4m script.vpy - | ffplay -
```

## 7. AviSynth+ migration notes

- Most AVS+ filters exist as VS equivalents: `Trim` → `core.std.Trim`; `Crop` → `core.std.Crop`; `ConvertToYUV420` → `clip.resize.Bicubic(format=vs.YUV420P8)`.
- `FFT3DFilter` (AVS+) → `neo_fft3d` or `fft3dfilter` plugin in VS.
- `QTGMC.avsi` → `havsfunc.QTGMC`.
- Fall back to `core.avisource.AVISource("in.avs")` to just reuse a legacy `.avs` script unchanged.
- AVS+ uses `last` as implicit clip variable; VS requires explicit variable names.
- AVS+ is single-threaded per filter graph by default; VS is natively multithreaded.

## 8. Recipe book

### Anime fansub pipeline (1080p source, 10-bit HEVC out)

```python
import vapoursynth as vs
import havsfunc as haf
core = vs.core
src = core.lsmas.LWLibavSource("raw.mkv")
src = haf.FineDehalo(src)
src = core.knlm.KNLMeansCL(src, d=2, a=2, s=4, h=0.6, channels="Y")
src = core.knlm.KNLMeansCL(src, d=2, a=2, s=4, h=0.4, channels="UV")
src = haf.LSFmod(src, strength=50)
src = src.resize.Bicubic(format=vs.YUV420P10)
src.set_output()
```

```bash
vspipe --y4m fansub.vpy - | \
  ffmpeg -i - -c:v libx265 -preset slow -crf 18 -pix_fmt yuv420p10le out.mkv
```

### Archive deinterlace + denoise (old DV → progressive archival)

```python
import vapoursynth as vs
import havsfunc as haf
core = vs.core
src = core.ffms2.Source("dv.dv")
src = haf.QTGMC(src, Preset="Slower", TFF=True, SourceMatch=3, Lossless=2)
src = haf.SMDegrain(src, tr=3, thSAD=300)
src = src.resize.Bicubic(format=vs.YUV422P10)
src.set_output()
```

```bash
vspipe --y4m archive.vpy - | \
  ffmpeg -i - -c:v ffv1 -level 3 -g 1 -coder 1 -context 1 \
    -pix_fmt yuv422p10le archive.mkv
```

### Motion interpolation 24 → 60 fps (MVTools)

```python
import vapoursynth as vs
core = vs.core
src = core.lsmas.LWLibavSource("movie24.mkv")
sup = core.mv.Super(src, pel=2, sharp=2, rfilter=4)
bv  = core.mv.Analyse(sup, isb=True,  blksize=16, overlap=8, search=3)
fv  = core.mv.Analyse(sup, isb=False, blksize=16, overlap=8, search=3)
out = core.mv.BlockFPS(src, sup, bv, fv, num=60000, den=1001, mode=3)
out.set_output()
```

```bash
vspipe --y4m interp.vpy - | \
  ffmpeg -i - -c:v libx264 -crf 18 -preset slow movie60.mp4
```

### SVPflow alternative (simpler, often higher quality)

```python
import vapoursynth as vs
core = vs.core
src = core.lsmas.LWLibavSource("movie24.mkv")
sup  = core.svp1.Super(src, "{pel:2}")
vec  = core.svp1.Analyse(sup["clip"], sup["data"], src, "{}")
out  = core.svp2.SmoothFps(src, sup["clip"], sup["data"],
                           vec["clip"], vec["data"],
                           "{rate:{num:60,den:1}}")
out.set_output()
```

### Dry sanity check

```bash
vspipe --info script.vpy -     # prints format, width, height, fps, frames
```
