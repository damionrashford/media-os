# HW Encoder Reference (ffmpeg)

Encoder option tables, cross-encoder quality ladder, format-bridging rules,
per-platform driver install notes, multi-GPU selection, and session limits.
Values are what shipping FFmpeg 6.x / 7.x accept — check `ffmpeg -h encoder=<name>`
on your build for exact option names.

## 1. Encoder options

### `h264_nvenc` / `hevc_nvenc` / `av1_nvenc`

| Option             | Values                                       | Purpose                                               |
|--------------------|----------------------------------------------|-------------------------------------------------------|
| `-preset`          | `p1`..`p7`  (p1 fastest, p7 best)            | Speed / quality tradeoff. Legacy: `slow`/`medium`…    |
| `-tune`            | `hq` / `ll` / `ull` / `lossless`             | hq=quality, ll=low-latency, ull=ultra-low-latency     |
| `-rc`              | `vbr` / `cbr` / `constqp`                    | Rate control.                                         |
| `-cq`              | 0–51                                         | Quality target for vbr (lower = better).              |
| `-qp`              | 0–51                                         | Constant QP for `-rc constqp`.                        |
| `-b:v` / `-maxrate`| `0` + `-maxrate`                             | `-b:v 0 -maxrate X` = pure VBR with cap.              |
| `-bf`              | 0–5                                          | B-frames. Turing+ only.                               |
| `-b_ref_mode`      | `disabled` / `each` / `middle`               | Use B-frames as references (Turing+).                 |
| `-spatial_aq`      | 0/1                                          | Spatial adaptive quantization.                        |
| `-temporal_aq`     | 0/1                                          | Temporal AQ (Turing+).                                |
| `-aq-strength`     | 1–15                                         | AQ strength.                                          |
| `-rc-lookahead`    | frames                                       | Lookahead. Costs VRAM.                                |
| `-pix_fmt`         | `yuv420p` / `p010le` (10-bit) / `yuv444p`    | 10-bit HEVC/AV1 requires `p010le`.                    |
| `-gpu`             | device index                                 | Multi-GPU: select encoder device.                     |

### `h264_qsv` / `hevc_qsv` / `av1_qsv`

| Option               | Values                                  | Purpose                                |
|----------------------|-----------------------------------------|----------------------------------------|
| `-preset`            | `veryfast`..`veryslow` (or 1–7)         | Speed/quality.                         |
| `-global_quality`    | 1–51                                    | ICQ quality (lower = better).          |
| `-look_ahead`        | 0/1                                     | Enable LA-ICQ (higher quality).        |
| `-look_ahead_depth`  | frames                                  | Lookahead depth.                       |
| `-b:v` / `-maxrate`  | bitrate                                 | CBR/VBR mode.                          |
| `-bf`                | 0–16                                    | B-frames.                              |
| `-async_depth`       | 1–64                                    | Pipeline depth — higher = higher fps.  |
| `-extbrc`            | 0/1                                     | Extended bitrate control.              |
| `-profile:v`         | `main` / `main10` / `high`              |                                        |

### `h264_vaapi` / `hevc_vaapi` / `av1_vaapi`

| Option        | Values                                   | Purpose                             |
|---------------|------------------------------------------|-------------------------------------|
| `-rc_mode`    | `CQP` / `CBR` / `VBR` / `ICQ` / `QVBR`   | Rate control.                       |
| `-qp`         | 0–52                                     | For CQP.                            |
| `-global_quality` | 1–52                                 | For ICQ/QVBR.                       |
| `-b:v`        | bitrate                                  | For CBR/VBR.                        |
| `-profile:v`  | `main` / `main10` / `high`               |                                     |
| `-quality`    | 0–8 (lower = better, 0 = default)        | Encoder speed preset.               |
| `-bf`         | 0–7                                      | B-frames (HW must support).         |
| `-low_power`  | 0/1                                      | Use fixed-function LP encoder.      |

### `h264_videotoolbox` / `hevc_videotoolbox` / `prores_videotoolbox`

| Option             | Values                          | Purpose                                            |
|--------------------|---------------------------------|----------------------------------------------------|
| `-b:v`             | bitrate                         | H.264 rate target.                                 |
| `-q:v`             | 0–100 (higher = better)         | HEVC quality mode (Apple Silicon).                 |
| `-allow_sw`        | 0/1                             | Allow SW fallback (odd res, 4:4:4).                |
| `-require_sw`      | 0/1                             | Force SW (debug).                                  |
| `-realtime`        | 0/1                             | Real-time encoding hint.                           |
| `-tag:v`           | `hvc1` / `hev1`                 | `hvc1` required for Safari/QuickTime HEVC.         |
| `-profile:v`       | `main` / `main10` / `high` etc  |                                                    |
| `-prio_speed`      | 0/1                             | Prioritize speed over quality.                     |
| `-profile:v` (ProRes) | `0`..`5`                     | 0=proxy,1=LT,2=standard,3=HQ,4=4444,5=4444XQ       |

### `h264_amf` / `hevc_amf` / `av1_amf`

| Option          | Values                                        | Purpose                        |
|-----------------|-----------------------------------------------|--------------------------------|
| `-quality`      | `speed` / `balanced` / `quality`              | Speed/quality preset.          |
| `-rc`           | `cqp` / `cbr` / `vbr_latency` / `vbr_peak`    | Rate control (names vary).     |
| `-qp_i`/`qp_p`  | 0–51                                          | CQP per-frame-type.            |
| `-b:v`          | bitrate                                       | CBR/VBR.                       |
| `-usage`        | `transcoding` / `ultralowlatency` / `lowlatency` / `webcam` |                |
| `-profile:v`    | `main` / `high` / `constrained_baseline`      |                                |
| `-preanalysis`  | 0/1                                           | Pre-analysis for quality.      |

## 2. Cross-encoder quality ladder (approximate)

Rough equivalence when all are configured sensibly; real mileage varies with content.

| Perceptual target | libx264 -crf | libx265 -crf | h264_nvenc -cq | hevc_nvenc -cq | h264_qsv -global_quality | hevc_qsv -global_quality | h264_vaapi -qp | h264_videotoolbox | hevc_videotoolbox -q:v |
|-------------------|-------------:|-------------:|---------------:|---------------:|-------------------------:|-------------------------:|---------------:|-------------------|-----------------------:|
| Visually lossless | 16           | 18           | 17             | 19             | 16                       | 18                       | 18             | 15 Mbps           | 75                     |
| High quality      | 18           | 20           | 19             | 21             | 19                       | 21                       | 21             | 8 Mbps            | 65                     |
| Standard web      | 22           | 24           | 23             | 25             | 23                       | 25                       | 24             | 5 Mbps            | 55                     |
| Small file        | 26           | 28           | 28             | 30             | 28                       | 30                       | 28             | 2 Mbps            | 45                     |

Hardware encoders generally need **+15–30% bitrate** vs libx264/libx265 to match perceptual quality at the same CRF-equivalent level.

## 3. Format bridges

Hardware surfaces (`cuda`, `qsv`, `vaapi`, `videotoolbox`) are opaque to CPU filters. Bridging rules:

| Chain                                  | Filter string                                                        |
|----------------------------------------|----------------------------------------------------------------------|
| GPU → CPU (NVIDIA)                     | `hwdownload,format=nv12`                                             |
| GPU → CPU (VAAPI)                      | `hwdownload,format=nv12`                                             |
| CPU → GPU (NVIDIA, for scale_cuda)     | `hwupload_cuda`                                                      |
| CPU → GPU (VAAPI)                      | `format=nv12,hwupload`                                               |
| CPU → GPU (QSV)                        | `format=nv12,hwupload=extra_hw_frames=64`                            |
| Round-trip (CPU filter in GPU chain)   | `hwdownload,format=nv12,<cpu_filter>,hwupload`                       |
| 10-bit VAAPI                           | `format=p010,hwupload` with encoder `-pix_fmt p010le -profile main10`|

**Key error signatures:**

- `Impossible to convert between the formats` → missing `format=<sw_fmt>` before `hwupload`.
- `Filter hwupload_cuda has an unconnected output` → you forgot an encoder downstream, or the filter produced GPU frames but the next filter expects SW.
- `No such filter: 'scale_cuda'` → FFmpeg wasn't built with `--enable-nvdec`/`--enable-cuda-nvcc`. Use `scale_npp` on older builds, or fall back to `hwdownload,scale,hwupload_cuda`.

## 4. Driver install notes

### NVIDIA (NVENC / NVDEC / CUDA)
- Linux: install proprietary NVIDIA driver **≥ 520** for modern NVENC features (AV1 needs 530+, Ada Lovelace card).
- Also install **CUDA toolkit** OR `nvidia-cuda-toolkit` package for `nvcc`/`scale_cuda`. For `scale_npp` you need the NPP library.
- Verify: `nvidia-smi`, then `ffmpeg -init_hw_device cuda=cu -f lavfi -i nullsrc -f null -`.
- Windows: GeForce/Studio driver includes NVENC/NVDEC; nothing extra needed.

### Intel Quick Sync (QSV)
- Linux: `intel-media-va-driver-non-free` (Ubuntu/Debian) or `intel-media-driver` (Fedora). The old `i965-va-driver` is insufficient for Gen9+ features.
- Set `LIBVA_DRIVER_NAME=iHD` (newer) or `i965` (legacy).
- Verify: `vainfo` — look for `VAProfileH264Main : VAEntrypointEncSlice` etc.
- Windows: Intel Graphics driver (Arc Control / latest Intel DSA).

### VA-API (Linux general)
- Mesa `mesa-va-drivers` for AMD. NVIDIA users can install `nvidia-vaapi-driver` (RADV/VDPAU translation).
- Render node: `/dev/dri/renderD128` (first GPU). User must be in `video` or `render` group.
- Verify: `vainfo --display drm --device /dev/dri/renderD128`.

### VideoToolbox (macOS)
- Built into macOS. Nothing to install.
- Available encoders depend on chip: M1/M2/M3/M4 have HW ProRes encode; Intel Macs don't.
- Verify: `ffmpeg -h encoder=h264_videotoolbox`.

### AMD AMF (Windows)
- Install latest Adrenalin driver.
- FFmpeg must be built with `--enable-amf` (gyan.dev and BtbN builds both ship it).
- Linux AMF exists via the Pro driver but is fragile — prefer VAAPI on Linux AMD.

### Vulkan (emerging)
- FFmpeg 7.0+ with `--enable-vulkan` and `--enable-libshaderc`.
- Linux: Mesa 24+ with `VK_KHR_video_decode_queue`.
- Windows: Vulkan SDK + recent driver.

## 5. Multi-GPU selection

| API          | Selection flag                                                             |
|--------------|----------------------------------------------------------------------------|
| NVIDIA CUDA  | `-hwaccel_device 1` (hwaccel init) + `-gpu 1` (nvenc encoder option)       |
|              | Also honors `CUDA_VISIBLE_DEVICES=1`                                       |
| QSV          | `-qsv_device /dev/dri/renderD128` (Linux) or device index via `MFX`        |
| VAAPI        | `-vaapi_device /dev/dri/renderD129` (second GPU's render node)             |
| VideoToolbox | Not selectable — uses the system default GPU                               |
| AMF          | `-init_hw_device d3d11va=dx11,adapter=1` then `-filter_hw_device dx11`     |

## 6. Session / capability limits

- **NVENC consumer GPUs**: 3 concurrent sessions on older GeForce; 5–8 on RTX 30/40/50 series. Quadro/Tesla/Data Center cards have no artificial cap.
  - Linux: `nvidia-patch` (keylase/nvidia-patch) removes the cap.
  - Windows: firmware-locked.
- **NVENC codec support by generation**:
  - Pascal: H.264, HEVC 8-bit
  - Turing: + HEVC 10-bit, B-frames as references
  - Ampere: improved HEVC quality
  - Ada (RTX 40): + AV1 encode
  - Blackwell (RTX 50): improved AV1, 4:2:2 support
- **Intel QSV codec support by gen**:
  - Gen9 (Skylake) – H.264, HEVC 8-bit
  - Gen11 (Ice Lake) – + HEVC 10-bit, VP9 decode
  - Xe (Tiger Lake / Arc) – + AV1 decode
  - Arc A-series / Alchemist – + AV1 encode
- **Apple Silicon**: M1/M2/M3/M4 — H.264, HEVC (8/10-bit, 4:2:0/4:2:2), ProRes encode; AV1 decode on M3+; no AV1 encode yet.
- **AMD AMF**:
  - Polaris+ – H.264, HEVC
  - RDNA2+ – + AV1 decode
  - RDNA3+ (RX 7000) – + AV1 encode
- **Max resolution**: NVENC RTX 40 up to 8192×8192 H.264 / 8192×8192 HEVC; QSV typically 8K on Arc/12th gen; VT 8K on M2+.

## 7. Sanity-check one-liners

```bash
# NVENC works?
ffmpeg -hide_banner -f lavfi -i testsrc=duration=1:size=1280x720:rate=30 \
  -c:v h264_nvenc -f null -

# QSV works?
ffmpeg -hide_banner -init_hw_device qsv=hw -f lavfi -i testsrc=duration=1:size=1280x720 \
  -vf "format=nv12,hwupload=extra_hw_frames=16" -c:v h264_qsv -f null -

# VAAPI works?
ffmpeg -hide_banner -vaapi_device /dev/dri/renderD128 \
  -f lavfi -i testsrc=duration=1:size=1280x720 \
  -vf "format=nv12,hwupload" -c:v h264_vaapi -f null -

# VideoToolbox works?
ffmpeg -hide_banner -f lavfi -i testsrc=duration=1:size=1280x720 \
  -c:v h264_videotoolbox -b:v 5M -f null -

# AMF works?
ffmpeg -hide_banner -f lavfi -i testsrc=duration=1:size=1280x720 \
  -c:v h264_amf -f null -
```

If any of the above segfaults or errors, the corresponding encoder is NOT usable on this build/driver combo — do not pick that `--accel`.
