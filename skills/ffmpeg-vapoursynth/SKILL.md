---
name: ffmpeg-vapoursynth
description: >
  VapourSynth integration with ffmpeg: vapoursynth demuxer reads VapourSynth script (.vpy) output as a video source for ffmpeg, enabling Python-based frame-server filtering with plugins like QTGMC (deinterlace), KNLMeansCL (denoise), dfttest, BM3DCUDA, MVTools, SVPflow, AviSynth+ compat. Use when the user asks to use VapourSynth scripts in an ffmpeg pipeline, run QTGMC deinterlacing, chain VapourSynth frame-server filters to ffmpeg, do Python-based filter graphs, or leverage VapourSynth plugins ffmpeg lacks natively.
argument-hint: "[script.vpy]"
---

# Ffmpeg VapourSynth

**Context:** $ARGUMENTS

VapourSynth (VS) is a Python-based frame server. A `.vpy` file is a real Python script that builds a filter graph by calling C++ plugins through `vs.core`. `vspipe` streams the resulting video as Y4M to stdout, which ffmpeg consumes as an input — or ffmpeg reads `.vpy` directly via its `vapoursynth` demuxer when built with `--enable-vapoursynth`.

## Quick start

- **Deinterlace with QTGMC:** → Step 2 (write `.vpy`) → Step 3 (pipe)
- **Denoise with KNLMeansCL / BM3DCUDA / dfttest:** → Step 2 → Step 3
- **24 → 60 fps motion interpolation (SVPflow / MVTools):** → Step 2 → Step 3
- **Reuse an AviSynth+ script:** Source with `avisource` inside a `.vpy` → Step 3
- **Direct ffmpeg input without vspipe:** → Step 3 "demuxer" variant

## When to use

- ffmpeg's built-in filters (`yadif`, `bwdif`, `nlmeans`, `hqdn3d`) are not good enough — you need **QTGMC** deinterlacing, **BM3D**/**KNLMeansCL** denoising, or **SVPflow** motion interpolation.
- You want a reproducible, file-based filter graph in Python rather than a one-liner `-vf`.
- You need to share a chain with AviSynth+ users via `avisource`.
- You want to decouple decode/filter (VS) from encode (ffmpeg) and keep encoding flags stable across projects.

## Step 1 — Install VapourSynth and plugins

```bash
# macOS
brew install vapoursynth

# Debian/Ubuntu
sudo apt install vapoursynth vapoursynth-editor

# Python helper libraries (always useful)
pip install vsutil
```

Common plugins (install via package manager or build from source):

- **Source:** `ffms2`, `lsmas` (L-SMASH), `d2vsource`, `dgsource`
- **Deinterlace:** `nnedi3`, `EEDI3`, `mvtools` (needed by QTGMC)
- **Denoise:** `knlm` (KNLMeansCL, OpenCL), `bm3dcuda`, `dfttest`, `fft3dfilter`
- **Interpolation:** `mvtools`, `svpflow`
- **Format:** `fmtc` (fmtconv), built-in `resize`

Python helper modules used by QTGMC and friends:

```bash
pip install havsfunc mvsfunc adjust
```

Verify install:

```bash
vspipe --version
python -c "import vapoursynth as vs; print(vs.core.version())"
```

## Step 2 — Write a `.vpy` script

Minimal scaffold:

```python
import vapoursynth as vs
core = vs.core

clip = core.ffms2.Source("in.mkv")
clip = core.std.Crop(clip, left=10, right=10)
clip.set_output()
```

**QTGMC high-quality deinterlace** (top-field-first source):

```python
import vapoursynth as vs
import havsfunc as haf
core = vs.core

clip = core.ffms2.Source("interlaced.mkv")
clip = haf.QTGMC(clip, Preset="Slower", TFF=True)
clip.set_output()
```

**KNLMeansCL (GPU / OpenCL) denoise:**

```python
clip = core.knlm.KNLMeansCL(clip, d=2, a=2, s=4, h=1.5)
```

**BM3DCUDA denoise (NVIDIA):**

```python
clip = core.bm3dcuda.BM3D(clip, sigma=[1, 1, 1])
```

**dfttest (FFT frequency-domain denoise):**

```python
clip = core.dfttest.DFTTest(clip, sigma=1.0)
```

**SVPflow 24 → 60 fps interpolation** (simplified — see `references/vapoursynth.md` for the full recipe):

```python
import vapoursynth as vs
core = vs.core
clip = core.lsmas.LWLibavSource("movie24.mkv")
# Build motion vectors with mvtools, then Smooth / BlockFPS to 60 fps.
# Full SVPflow pipeline: analyse → smooth → interpolate.
clip.set_output()
```

Always end with `clip.set_output()`. For multiple outputs use `clip.set_output(0)`, `clip2.set_output(1)` and select via `vspipe -o N`.

## Step 3 — Pipe into ffmpeg

**Standard pipe (works everywhere):**

```bash
vspipe --y4m script.vpy - | ffmpeg -i - -c:v libx264 -crf 18 -preset slow out.mp4
```

`--y4m` is mandatory — the Y4M header carries width, height, fps, and pixel format, which ffmpeg needs to interpret the raw stream.

**Direct demuxer (only when ffmpeg was built with `--enable-vapoursynth`):**

```bash
ffmpeg -f vapoursynth -i script.vpy -c:v libx264 -crf 18 out.mp4
```

Most distro builds of ffmpeg do **not** ship this. If `ffmpeg -demuxers | grep vapoursynth` is empty, fall back to the `vspipe | ffmpeg` form.

**Adding audio from the original source:**

```bash
vspipe --y4m script.vpy - | \
  ffmpeg -i - -i original.mkv -map 0:v -map 1:a \
    -c:v libx264 -crf 18 -c:a copy out.mkv
```

## Step 4 — Encode

Encoder choice is independent of VS. Typical targets:

- **Archival:** `libx264 -crf 16 -preset veryslow` or `libx265 -crf 18 -preset slow -tag:v hvc1`
- **High-bit-depth (10-bit) preserving:** emit `vs.YUV420P10` from VS, encode with `-pix_fmt yuv420p10le`
- **Lossless intermediate:** `-c:v ffv1 -level 3 -g 1 -coder 1 -context 1`

Keep bit depth consistent end-to-end: if VS outputs 10-bit, ffmpeg must accept 10-bit (`-pix_fmt yuv420p10le`). Y4M signals this automatically.

## Available scripts

- **`scripts/vspipe.py`** — wrapper around `vspipe` + `ffmpeg` with subcommands:
  - `check` — detect VapourSynth, vspipe, and loaded plugins.
  - `run --vpy script.vpy --output out.mp4 [--codec libx264] [--crf 18]` — pipe `.vpy` through ffmpeg.
  - `qtgmc-deinterlace --input i.mkv --output o.mkv --tff [--preset Slower]` — generate a QTGMC `.vpy` in a tempdir and encode.
  - `knl-denoise --input i.mkv --output o.mkv [--sigma 1.5]`
  - `bm3d-denoise --input i.mkv --output o.mkv [--sigma 1.0]`
  - `gen-vpy --source-plugin ffms2 --input i.mkv --output-vpy out.vpy` — scaffold a minimal `.vpy`.
  - Flags: `--dry-run`, `--verbose`. Stdlib only, non-interactive.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/vspipe.py check
uv run ${CLAUDE_SKILL_DIR}/scripts/vspipe.py qtgmc-deinterlace \
  --input interlaced.mkv --output clean.mkv --tff --preset Slower
```

## Reference docs

- Read [`references/vapoursynth.md`](references/vapoursynth.md) for the plugin catalog, QTGMC preset comparison, havsfunc / mvsfunc / adjust function list, format/bit-depth constants, vspipe CLI flags, ffmpeg integration patterns, AviSynth+ migration notes, and recipe book (anime fansub pipeline, archive restore, 24→60 interpolation).

## Gotchas

- `.vpy` files **are Python code** — they execute arbitrary Python. Don't run untrusted scripts.
- `vspipe` is the canonical way to stream VS output. `--y4m` is **mandatory** for ffmpeg consumption (raw `--y4m`-less output has no header).
- The direct `ffmpeg -f vapoursynth -i script.vpy` demuxer requires ffmpeg to be compiled with `--enable-vapoursynth`. Most distro packages (Debian, Ubuntu, macOS Homebrew bottles) do **not** enable it — fall back to `vspipe | ffmpeg`.
- VS plugins are C++ extensions exposed as `core.NAMESPACE.FUNC`. Common namespaces: `ffms2` / `lsmas` / `d2v` / `dgsource` (sources), `std` (built-in), `resize`, `fmtc`, `nnedi3`, `EEDI3`, `dfttest`, `knlm`, `bm3dcuda`, `mvtools`, `svp1` / `svp2`.
- Python helper modules are different: `havsfunc`, `mvsfunc`, `adjust`, `vsutil` are imported like `import havsfunc as haf` and called as Python functions, **not** via `core.*`.
- **QTGMC** is the gold-standard deinterlacer — far superior to `yadif` / `bwdif`. Presets (quality-vs-speed): `Draft`, `Ultra Fast`, `Super Fast`, `Very Fast`, `Faster`, `Fast`, `Medium`, `Slow`, `Slower`, `Very Slow`, `Placebo`. QTGMC needs `mvtools` + `nnedi3` + `havsfunc` + `mvsfunc` + `adjust` all installed.
- Source-filter choice matters: `ffms2` is general-purpose; `lsmas` (L-SMASH) gives frame-accurate MP4 seeking; `d2vsource` for MPEG-2 DVD with a `.d2v` index; `dgsource` for DGDecNV hardware decode.
- **Every script must end with `clip.set_output()`.** Multi-output: `clip.set_output(0)`, `clip2.set_output(1)`, then `vspipe -o 1 …`.
- Color families are constants: `vs.YUV`, `vs.RGB`, `vs.GRAY`. Bit depths: 8, 10, 16, 32-float. Format IDs combine them: `vs.YUV420P10`, `vs.YUV444P16`, `vs.RGBS` (32-bit float), etc.
- Format conversion: `clip = clip.resize.Bicubic(format=vs.YUV420P8)` or `clip = core.fmtc.bitdepth(clip, bits=10)`.
- Keep high-bit-depth (10/16/32-float) through the whole chain for quality — dithering down only at final output.
- GPU plugins (`knlm`, `bm3dcuda`) need OpenCL / CUDA runtime present. `knlm` also accepts `device_type="cpu"` for fallback.
- Y4M framerate must be correct — VS infers it from the source filter. If your source reports wrong fps, set it explicitly with `core.std.AssumeFPS(clip, fpsnum=24000, fpsden=1001)`.
- VapourSynth Editor (**VSE**) provides real-time `.vpy` preview — great for tuning filter params before a long encode.
- "Plugin not found" usually means the `.so` / `.dylib` / `.dll` isn't in VS's autoload path. Check with `core.version()` for registered plugins, or inspect `vsrepo` output.
- For Python 3.9 compatibility with newer syntax, add `from __future__ import annotations` at the top of `.vpy` files.
- `__file__` works inside `.vpy` — useful for loading sidecar configs relative to the script.

## Examples

### Example 1 — Deinterlace interlaced DV footage with QTGMC

```bash
# Option A: let the helper script write the .vpy
uv run ${CLAUDE_SKILL_DIR}/scripts/vspipe.py qtgmc-deinterlace \
  --input dv.dv --output dv_progressive.mkv --tff --preset Slower

# Option B: hand-written .vpy
cat > dv.vpy <<'PY'
import vapoursynth as vs, havsfunc as haf
core = vs.core
clip = core.ffms2.Source("dv.dv")
clip = haf.QTGMC(clip, Preset="Slower", TFF=True)
clip.set_output()
PY
vspipe --y4m dv.vpy - | ffmpeg -i - -c:v libx264 -crf 17 -preset slow dv_progressive.mkv
```

### Example 2 — Grain-preserving denoise for anime

```python
# anime.vpy
import vapoursynth as vs
core = vs.core
src = core.lsmas.LWLibavSource("raw.mkv")
src = core.knlm.KNLMeansCL(src, d=2, a=2, s=4, h=0.6, channels="Y")
src = core.knlm.KNLMeansCL(src, d=2, a=2, s=4, h=0.4, channels="UV")
src.set_output()
```

```bash
vspipe --y4m anime.vpy - | \
  ffmpeg -i - -c:v libx265 -crf 18 -preset slow -pix_fmt yuv420p10le anime_clean.mkv
```

### Example 3 — 24 → 60 fps with MVTools

```python
# interp.vpy (short form)
import vapoursynth as vs
core = vs.core
src = core.lsmas.LWLibavSource("movie24.mkv")
sup = core.mv.Super(src, pel=2)
bv  = core.mv.Analyse(sup, isb=True,  blksize=16)
fv  = core.mv.Analyse(sup, isb=False, blksize=16)
out = core.mv.BlockFPS(src, sup, bv, fv, num=60, den=1)
out.set_output()
```

```bash
vspipe --y4m interp.vpy - | ffmpeg -i - -c:v libx264 -crf 18 movie60.mp4
```

## Troubleshooting

### Error: `vspipe: command not found`

Cause: VapourSynth not installed or not on `PATH`.
Solution: `brew install vapoursynth` (macOS) / `apt install vapoursynth` (Linux). Confirm with `vspipe --version`.

### Error: `Python exception: No attribute with the name ffms2 exists.`

Cause: The `ffms2` (or other) plugin is not loaded by VapourSynth.
Solution: Install the plugin (package manager, `vsrepo install ffms2`, or build from source), then confirm with `python -c "import vapoursynth as vs; print([p.namespace for p in vs.core.plugins()])"`.

### Error: `ffmpeg: Unknown input format: 'vapoursynth'`

Cause: ffmpeg was not built with `--enable-vapoursynth`.
Solution: Use the `vspipe --y4m … | ffmpeg -i -` fallback, or build ffmpeg from source with `--enable-vapoursynth`.

### Error: `QTGMC: MVTools not found` / `havsfunc` import fails

Cause: Missing dependency — QTGMC needs `mvtools` plugin plus `havsfunc`, `mvsfunc`, `adjust` Python modules.
Solution: `pip install havsfunc mvsfunc adjust` and install the `mvtools` plugin (`vsrepo install mvtools` or package manager).

### Pipe works but ffmpeg reports wrong fps

Cause: Source filter reported incorrect frame rate, or the Y4M header was stripped.
Solution: Always pass `--y4m`. Force fps in VS with `core.std.AssumeFPS(clip, fpsnum=24000, fpsden=1001)`.

### Output looks washed out / too contrasty

Cause: Color-range mismatch (limited vs full) between VS output and the encoder.
Solution: In VS, set range explicitly on the `resize` call (`range_in_s="limited"`, `range_s="limited"`) and tell ffmpeg with `-color_range tv`.
