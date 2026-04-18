---
name: ffmpeg-hwaccel
description: >
  Use hardware acceleration with ffmpeg: NVIDIA NVENC/NVDEC/CUDA, Intel Quick Sync (QSV), VA-API (Linux Intel/AMD), VideoToolbox (macOS Apple Silicon/Intel), AMD AMF (Windows), Vulkan, plus hwupload/hwdownload filters for full-GPU pipelines. Use when the user asks to encode with GPU, use NVENC, use QSV, use VideoToolbox on Mac, use VAAPI, accelerate ffmpeg with GPU, speed up transcoding, or do zero-copy GPU-to-GPU filtering.
argument-hint: "[operation] [input]"
---

# Ffmpeg Hwaccel

**Context:** $ARGUMENTS

## Quick start

- **I don't know what my GPU supports:** → Step 1 (detection)
- **Just encode fast on whatever GPU I have:** → `scripts/hwaccel.py transcode --accel auto`
- **Zero-copy NVIDIA pipeline (decode+scale+encode on GPU):** → Step 2, recipe A
- **Intel Quick Sync on Windows/Linux:** → Step 2, recipe B
- **VA-API on Linux desktop:** → Step 2, recipe C
- **macOS (Intel or Apple Silicon):** → Step 2, recipe D
- **AMD on Windows:** → Step 2, recipe E

## When to use

- You need to transcode many/long files and CPU encode is too slow.
- You want real-time or faster-than-realtime encoding (live streaming, bulk archive conversion).
- You explicitly want NVENC, QSV, VAAPI, VideoToolbox, AMF or Vulkan.
- Hardware decoder (NVDEC/QSV-dec/VAAPI-dec) to offload decoding while still using CPU for something else.

If you just want best quality at the smallest size, **prefer `ffmpeg-transcode` with libx264/libx265/libaom-av1** — hardware encoders trade quality for speed. See the gotcha about quality-per-bit below.

## Step 1 — Detect what's available on this machine

```bash
# 1. Which hwaccel APIs does this ffmpeg build expose?
ffmpeg -hide_banner -hwaccels

# 2. Which HW encoders are compiled in?
ffmpeg -hide_banner -encoders | grep -E 'nvenc|qsv|vaapi|videotoolbox|amf|vulkan'

# 3. Which HW decoders / *_cuvid variants?
ffmpeg -hide_banner -decoders | grep -E 'cuvid|qsv|vaapi|videotoolbox'

# 4. Probe the NVENC / QSV / VAAPI backends
ffmpeg -hide_banner -f lavfi -i nullsrc -c:v h264_nvenc -f null -     2>&1 | head -20   # NVENC sanity
ffmpeg -hide_banner -init_hw_device qsv=hw -f lavfi -i nullsrc -c:v h264_qsv -f null - 2>&1 | head -20
vainfo                                                                                 # Linux VAAPI
```

Or just: `uv run ${CLAUDE_SKILL_DIR}/scripts/hwaccel.py detect`.

**Platform cheat sheet (what to pick when `auto`):**

| OS / GPU               | First choice       | Fallback          |
|------------------------|--------------------|-------------------|
| macOS (any Mac)        | `videotoolbox`     | libx264           |
| Linux + NVIDIA         | `nvenc`            | `vaapi`           |
| Linux + Intel iGPU     | `qsv` (iHD driver) | `vaapi`           |
| Linux + AMD            | `vaapi` (Mesa)     | libx264           |
| Windows + NVIDIA       | `nvenc`            | libx264           |
| Windows + Intel iGPU   | `qsv`              | `d3d11va` decode  |
| Windows + AMD          | `amf`              | libx264           |

## Step 2 — Pick a decode + filter + encode pipeline

The general shape is:

```
ffmpeg [hwaccel flags BEFORE -i] -i in.mp4 \
       [-vf "GPU filter chain" OR "hwdownload,format=...,CPU filter chain"] \
       [-c:v <hw encoder>] [rate control + preset flags] \
       out.mp4
```

Key rule: **hwaccel flags come before `-i`**. Encoder flags come after.

### Recipe A — NVIDIA end-to-end GPU (decode, scale, encode all on CUDA)

```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda \
  -i in.mp4 \
  -vf "scale_cuda=1280:720:format=yuv420p" \
  -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 23 -b:v 0 -maxrate 12M -bufsize 24M \
  -c:a copy out.mp4
```

HEVC: `-c:v hevc_nvenc -pix_fmt p010le` for 10-bit. AV1 (Ada/Blackwell): `-c:v av1_nvenc -preset p5 -cq 30`.

**NVENC decode-only, CPU-encode (e.g. you need libx264 quality but want fast decode):**
```bash
ffmpeg -hwaccel cuda -i in.mp4 -c:v libx264 -crf 18 out.mp4
```
(No `-hwaccel_output_format cuda` → ffmpeg downloads frames automatically.)

**Explicit bridge when mixing GPU decode with CPU filters:**
```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i in.mp4 \
  -vf "hwdownload,format=nv12,unsharp=5:5:0.8,hwupload_cuda" \
  -c:v h264_nvenc -preset p5 -cq 23 out.mp4
```

### Recipe B — Intel Quick Sync (QSV)

```bash
ffmpeg -hwaccel qsv -c:v h264_qsv -i in.mp4 \
  -vf "scale_qsv=1280:720" \
  -c:v h264_qsv -preset medium -global_quality 23 -look_ahead 1 \
  -c:a copy out.mp4
```

HEVC: `-c:v hevc_qsv`. AV1 (Arc / 12th gen+): `-c:v av1_qsv`. Rate control: `-global_quality` = ICQ, add `-look_ahead 1` for LA-ICQ, or use `-b:v 5M` for CBR/VBR.

### Recipe C — VA-API (Linux, Intel / AMD / NVIDIA with nvidia-vaapi-driver)

```bash
ffmpeg -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi \
  -i in.mp4 \
  -vf "scale_vaapi=1280:720,format=nv12|vaapi,hwupload" \
  -c:v h264_vaapi -rc_mode CQP -qp 23 \
  -c:a copy out.mp4
```

HEVC: `-c:v hevc_vaapi -profile:v main` (or `main10` for 10-bit with `-pix_fmt p010le`). For CPU-source → VAAPI encode:

```bash
ffmpeg -vaapi_device /dev/dri/renderD128 -i in.mp4 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -qp 23 out.mp4
```

### Recipe D — VideoToolbox (macOS)

```bash
# H.264 — bitrate mode
ffmpeg -hwaccel videotoolbox -i in.mp4 \
  -c:v h264_videotoolbox -b:v 5M -maxrate 6M -bufsize 10M \
  -c:a copy out.mp4

# HEVC — quality mode on Apple Silicon; hvc1 tag for Safari/QuickTime
ffmpeg -hwaccel videotoolbox -i in.mp4 \
  -c:v hevc_videotoolbox -tag:v hvc1 -q:v 50 -allow_sw 1 \
  -c:a copy out.mov

# ProRes (Apple Silicon M1+ has a hardware ProRes encoder)
ffmpeg -i in.mov -c:v prores_videotoolbox -profile:v 3 -c:a copy out.mov
```

`-q:v` on HEVC_VT is 0–100 (higher = better quality). `-allow_sw 1` lets VT fall back to software when hardware rejects the request (odd resolutions, unusual pixel formats).

### Recipe E — AMD AMF (Windows)

```bash
ffmpeg -i in.mp4 \
  -c:v h264_amf -rc vbr_latency -quality speed -b:v 5M -maxrate 8M \
  -c:a copy out.mp4
```

HEVC: `-c:v hevc_amf`. Quality presets: `speed | balanced | quality`. RC modes: `cqp | cbr | vbr_latency | vbr_peak` (names differ between builds — check `ffmpeg -h encoder=h264_amf`).

## Step 3 — Format bridges (hwupload / hwdownload) — the #1 cause of confusion

GPU frames live in opaque hardware surfaces (`cuda`, `qsv`, `vaapi`, `videotoolbox`). CPU filters (`scale`, `crop`, `drawtext`, `unsharp`, `eq`, `pad`) cannot touch them directly. Rules:

| Situation                                        | Bridge you need                              |
|--------------------------------------------------|----------------------------------------------|
| GPU decode → GPU filter (`scale_cuda`) → HW enc  | none — frames stay on GPU                    |
| GPU decode → CPU filter → HW enc                 | `hwdownload,format=nv12, … ,hwupload_cuda`   |
| GPU decode → CPU filter → libx264                | `hwdownload,format=nv12`                     |
| CPU source → VAAPI encoder                       | `format=nv12,hwupload`                       |
| CPU source → NVENC                               | none (NVENC takes CPU frames directly)       |
| CPU source → QSV                                 | `format=nv12,hwupload=extra_hw_frames=64`    |

The `format=` is **not optional** before `hwupload` on VAAPI/QSV — without it you'll see `Impossible to convert between the formats`.

## Step 4 — Verify acceleration actually happened

```bash
ffmpeg -benchmark -v verbose -hwaccel cuda -i in.mp4 -c:v h264_nvenc -f null - 2>&1 | \
  grep -E 'hwaccel|using|nvenc|nvdec|qsv|vaapi|videotoolbox'
```

Look for lines like `Using auto hwaccel type cuda` and `[h264_nvenc @ …] Loaded Nvenc version …`. Also watch `fps=` in the progress line: a 1080p H.264 → H.264 transcode should run hundreds of fps on a modern GPU. If you see 30–60 fps, you're probably still on the CPU.

GPU usage: `nvidia-smi dmon -s u` (NVIDIA), `intel_gpu_top` (Intel Linux), Activity Monitor → GPU History (macOS), Task Manager → Performance (Windows).

## Available scripts

- **`scripts/hwaccel.py`** — detect available HW + build a correct end-to-end GPU pipeline.
  - `detect` → prints `ffmpeg -hwaccels`, encoder inventory, platform guess.
  - `transcode --input I --output O --accel {nvenc,qsv,vaapi,videotoolbox,amf,auto} [--codec {h264,hevc,av1}] [--quality 23] [--resolution 1280x720]`
  - `--dry-run` prints the command, `--verbose` dumps decisions.

## Reference docs

- Read [`references/pipelines.md`](references/pipelines.md) for encoder option tables (NVENC presets p1–p7, QSV `global_quality`, VAAPI `rc_mode`, VT `q:v`), cross-encoder quality ladder, driver install notes, multi-GPU selection, and session limits.

## Gotchas

- **Hwaccel decoder must match the input codec.** `-hwaccel cuda` for generic CUDA decode; for specific control use `-c:v h264_cuvid` / `hevc_cuvid` / `av1_cuvid`. VAAPI and QSV infer the decoder from `-hwaccel`.
- **Mixing CPU filters with GPU frames needs `hwdownload,format=<sw_fmt>`.** The `format=` is NOT optional — without it the chain errors with "Impossible to convert between the formats".
- **NVENC quality is not comparable to libx264 CRF.** `h264_nvenc -cq 23` ≈ libx264 `-crf 22` roughly. Hardware encoders usually produce ~15–30% larger files for the same visual quality vs libx264/libx265 — raise the bitrate (or lower `-cq`) to match.
- **NVENC presets changed.** `-preset slow|medium|fast` are legacy aliases; new names are `p1`..`p7` (p1 fastest, p7 slowest/best). Pair with `-tune hq|ll|ull|lossless`.
- **QSV on Linux requires the iHD driver** (`intel-media-driver` / `libva-intel-media`). Old `i965` driver does not expose modern QSV. QSV uses VAAPI as its backend on Linux.
- **VAAPI render node path** is `/dev/dri/renderD128` by default; with multiple GPUs the second is `renderD129`, etc. Select with `-vaapi_device /dev/dri/renderD129`.
- **`hwupload` without a preceding `format=nv12`** on VAAPI/QSV will fail — software format must match one of the HW surface's supported formats.
- **VideoToolbox HEVC output** must add `-tag:v hvc1` for QuickTime / Safari to play it (default tag is `hev1` which Safari rejects).
- **`-allow_sw 1` on VideoToolbox** permits software fallback when VT rejects the request (odd resolutions like 1079×1920, 4:4:4 pixel formats, >8K).
- **AMF rate control mode names** vary between FFmpeg builds: `vbr_latency`, `vbr_peak`, `cbr`, `cqp`. Check `ffmpeg -h encoder=h264_amf` on the specific build.
- **Vulkan filters (`scale_vulkan`, `chromaber_vulkan`)** need Vulkan decode support — FFmpeg 7+ with `--enable-vulkan`. Still experimental on many distros.
- **Multi-GPU selection:** NVIDIA uses `-hwaccel_device 1` (and set `CUDA_VISIBLE_DEVICES`); VAAPI uses a different `renderD12x` path; QSV uses `-qsv_device /dev/dri/renderD128`.
- **Hardware encoders give lower quality-per-bit than libx264/libx265.** At equal bitrate NVENC and QSV files look noticeably worse at low bitrates; the gap narrows above ~6 Mbps for 1080p.
- **NVENC session limit on consumer NVIDIA GPUs** is typically 3–8 concurrent encodes. On Linux this can be lifted with nvidia-patch; on Windows it's firmware-locked.
- **10-bit NVENC HEVC** requires `-pix_fmt p010le` (not `yuv420p10le`) because the encoder expects semi-planar HW formats.
- **Color range tags (`-color_range tv`, `-colorspace bt709`, `-color_primaries bt709`, `-color_trc bt709`)** — NVENC and QSV often don't propagate source tags correctly and produce shifted blacks/whites on playback. Set them explicitly.
- **NVENC B-frames** are supported on Turing+ (`-bf 3 -b_ref_mode middle`); older Pascal cards ignore `-bf`.
- **Apple Silicon ProRes** via `prores_videotoolbox` is real hardware — much faster than `prores_ks` CPU encoder — but only on M1/M2/M3/M4.

## Examples

### Example 1: NVIDIA — re-encode a 4K file to 1080p H.264 for web, fully on GPU

```bash
ffmpeg -hwaccel cuda -hwaccel_output_format cuda \
  -i movie_4k.mkv \
  -vf "scale_cuda=1920:1080:format=yuv420p" \
  -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 21 -b:v 0 -maxrate 15M -bufsize 30M \
  -c:a aac -b:a 160k -movflags +faststart movie_1080p.mp4
```

### Example 2: macOS — convert an MKV to Apple-friendly HEVC MP4 with VideoToolbox

```bash
ffmpeg -hwaccel videotoolbox -i in.mkv \
  -c:v hevc_videotoolbox -tag:v hvc1 -q:v 55 -allow_sw 1 \
  -c:a aac -b:a 192k out.mp4
```

### Example 3: Linux Intel iGPU — batch convert with QSV

```bash
for f in *.mov; do
  ffmpeg -hwaccel qsv -c:v h264_qsv -i "$f" \
    -vf "scale_qsv=1280:720" \
    -c:v h264_qsv -preset medium -global_quality 25 -look_ahead 1 \
    -c:a copy "${f%.mov}_720p.mp4"
done
```

### Example 4: VAAPI HEVC 10-bit on Linux

```bash
ffmpeg -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi \
  -i in.mov \
  -vf "scale_vaapi=1920:1080:format=p010,hwupload" \
  -c:v hevc_vaapi -profile:v main10 -rc_mode CQP -qp 24 -pix_fmt p010le \
  -c:a copy out.mp4
```

### Example 5: Pick automatically via the helper

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hwaccel.py transcode \
  --input in.mp4 --output out.mp4 --accel auto --codec hevc --quality 24 --resolution 1920x1080
```

## Troubleshooting

### Error: "Impossible to convert between the formats supported by the filter 'Parsed_hwupload_0' and the filter 'auto_scaler_0'"
Cause: missing `format=nv12` (or `p010` for 10-bit) before `hwupload` on VAAPI/QSV.  
Solution: prefix the filter chain with `format=nv12,` before `hwupload`.

### Error: "No NVENC capable devices found" / "Cannot load nvcuda.dll"
Cause: NVIDIA driver missing/too old, or running headless WSL without NVIDIA driver pass-through.  
Solution: install a driver ≥ 520 for modern NVENC features; on WSL install the Windows-side NVIDIA driver, not a Linux one.

### Error: "Device creation failed: -542398533" (VAAPI)
Cause: wrong `renderD12x` path or no permissions.  
Solution: `ls /dev/dri/` to find the right node, add user to `video` group, `vainfo` to verify.

### Error: "Error initializing an internal MFX session" / QSV device init fail
Cause: iHD driver missing, or using old `i965-va-driver`.  
Solution: `apt install intel-media-va-driver-non-free` (Debian/Ubuntu) and `export LIBVA_DRIVER_NAME=iHD`.

### Error: "Error while opening encoder … Generic error in an external library" (h264_videotoolbox)
Cause: VT doesn't support the requested pixel format or odd resolution.  
Solution: add `-allow_sw 1`, or `-vf "format=nv12,scale=trunc(iw/2)*2:trunc(ih/2)*2"` to force even dims.

### Output is noticeably worse than libx264 at the same bitrate
Cause: expected — hardware encoders trade quality for speed.  
Solution: raise bitrate 15–30%, lower `-cq` (NVENC) or `-global_quality` (QSV), enable `-tune hq` / `-look_ahead 1` / `-bf 3 -b_ref_mode middle`. If quality matters more than speed, use `ffmpeg-transcode` with libx264/libx265.

### Encoder prints "OpenEncodeSessionEx failed: out of memory (10)"
Cause: NVENC concurrent-session limit hit on a consumer GPU.  
Solution: reduce concurrent ffmpeg processes, or (Linux) apply nvidia-patch to lift the cap.

### Colors look washed out or shifted after NVENC/QSV encode
Cause: color tags not propagated.  
Solution: add `-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709` (or `bt2020nc` for HDR).
