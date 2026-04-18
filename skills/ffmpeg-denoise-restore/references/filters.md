# Denoise & restoration filter reference

Exhaustive option tables for video/audio denoise filters, noise-type diagnosis, a speed/quality matrix, DNN backend build notes, model sources, and an end-to-end recipe book.

---

## Noise type diagnosis cheat-sheet

| What you see | Diagnosis | Root cause | Best filter |
|---|---|---|---|
| Uniform fine speckle (random luma + chroma) | Gaussian / thermal sensor noise | Sensor read noise at high ISO | `hqdn3d`, `nlmeans`, `bm3d`, `fftdnoiz` |
| Color blotches on flat areas | Chroma noise | CFA reconstruction in low light | `hqdn3d` with strong chroma terms; `nlmeans` (works on chroma too) |
| 8×8 / 16×16 block patterns visible on smooth gradients | Compression block noise | DCT block artifacts | `deblock`, `owdenoise` (cannot fully restore) |
| Horizontal steps on smooth color gradients | Bit-depth banding | 8-bit quantization on subtle gradient | `gradfun`, `format=yuv420p10le` + dither |
| Stuck pixels, never move, spread uniform | Fixed-pattern / sensor defect | Hot/dead sensor pixels | `removegrain=mode=11`, `atadenoise` |
| Textured grain that moves each frame | Film grain (or Alexa grain emulation) | Analog film / intentional grain | `bm3d` low sigma + re-add `noise=alls=6:allf=t`, OR preserve |
| Horizontal rain streaks | Weather | Rain on lens | `derain` |
| Colored fringes on high-contrast edges | Chromatic aberration | Cheap lens | `chromaber_vulkan` |
| "Ringing" halos around edges | Over-sharpening or JPEG quality | Over-processed source | `dctdnoiz`, `owdenoise` |
| Waterfall / rolling-shutter wave on vertical lines | Rolling shutter | CMOS scan | use `ffmpeg-stabilize` skill instead |
| Mosquito noise around captions | DCT ringing at quant boundaries | Low-bitrate encode | `dctdnoiz` |

---

## Strength / speed / quality matrix

Measured loose on a 2.5 GHz x86 CPU, 1080p H.264 source:

| Filter | Typical speed (fps) | Quality ceiling | Best use |
|---|---|---|---|
| `hqdn3d` | 200–400 | Fair | Real-time cleanup, dailies |
| `removegrain` | 300–600 | Fair (single-frame only) | Fast grain / stuck pixel |
| `fftdnoiz` | 30–60 | Good | DCT / compression noise |
| `atadenoise` | 60–120 | Good for static footage | Security cams, fixed shots |
| `dctdnoiz` | 5–20 | Good | Ringing / mosquito |
| `owdenoise` | 10–30 | Good | Moderate |
| `nlmeans` | 5–30 | Very good | General purpose |
| `bm3d` | 0.5–5 | Excellent (SOTA) | Archival, film scans |
| `dnn_processing (SR)` | 1–20 (CPU) / 30–100 (GPU) | Depends on model | Upscaling |

---

## Video denoise filter tables

### `hqdn3d` — high-quality 3D denoiser
`hqdn3d=luma_spatial:chroma_spatial:luma_tmp:chroma_tmp`

| Option | Default | Notes |
|---|---|---|
| `luma_spatial` | 4 | 0–ish; higher = smoother luma |
| `chroma_spatial` | 3 | usually ~0.75× luma |
| `luma_tmp` | 6 | temporal luma; higher = smearier motion |
| `chroma_tmp` | ~4.5 | usually ~0.75× luma_tmp |

Mild default: `hqdn3d` (no args). Typical explicit: `hqdn3d=4:3:6:4.5`. Heavy archival: `hqdn3d=8:6:12:9`.

### `nlmeans` — non-local means
| Option | Default | Range | Notes |
|---|---|---|---|
| `s` | 1.0 | 1.0–30.0 | strength; high = smoother |
| `p` | 7 | odd 3–99 | patch size (px) |
| `pc` | = p | | chroma patch size |
| `r` | 15 | odd 3–99 | research window |
| `rc` | = r | | chroma research window |

Tradeoff: quality scales with `r` squared; speed falls as `r^2`. `p=7, r=15` is the standard sweet spot.

### `bm3d` — block-matching 3D
| Option | Default | Notes |
|---|---|---|
| `sigma` | 1.0 | noise strength estimate |
| `block` | 16 | block size (power of 2) |
| `bstep` | 4 | block step |
| `group` | 1 | temporal group (needs even frame count when >1) |
| `range` | 9 | search range |
| `mstep` | 1 | match step |
| `thmse` | 0.0 | MSE threshold for matching |
| `hdthr` | 2.7 | hard threshold |
| `estim` | basic | `basic` or `final` |
| `ref` | 0 | use reference block |
| `planes` | 7 | plane bitmask |

Can run at <1 fps. Use `bm3d=sigma=10:block=4:bstep=2:group=1` for medium. Heavy archival: `sigma=20:block=8:bstep=4:group=8`.

### `atadenoise` — adaptive temporal averaging
| Option | Default | Notes |
|---|---|---|
| `0a`/`0b` | 0.02/0.04 | Y plane threshold a/b |
| `1a`/`1b` | 0.02/0.04 | U plane threshold a/b |
| `2a`/`2b` | 0.02/0.04 | V plane threshold a/b |
| `s` | 9 | frame radius (odd) |
| `p` | 7 | planes bitmask |
| `a` | p | algorithm: `p` parallel, `s` serial |

Excellent for static shots; smears motion. Raise `s` to 15 for heavy cleanup.

### `fftdnoiz` — FFT-domain denoiser
| Option | Default | Notes |
|---|---|---|
| `sigma` | 1 | noise strength |
| `amount` | 1.0 | filter strength (0–1) |
| `block` | 32 | block size (power of 2) |
| `overlap` | 0.5 | block overlap |
| `prev` | 0 | previous frames |
| `next` | 0 | next frames |
| `planes` | 7 | plane bitmask |

Good all-rounder for DCT / compression noise. `fftdnoiz=sigma=8:amount=0.9` medium.

### `dctdnoiz` — DCT-domain denoiser
| Option | Default | Notes |
|---|---|---|
| `sigma` | 0 | noise sigma |
| `overlap` | -1 (=n/2) | DCT block overlap |
| `expr` | - | custom DCT expression |
| `n` | 3 | block size log2 (8×8) |

Good for mosquito/ringing noise. `dctdnoiz=3` is typical.

### `owdenoise` — overcomplete wavelet
| Option | Default | Notes |
|---|---|---|
| `depth` | 8 | wavelet depth |
| `luma_strength` | 1.0 | luma strength |
| `chroma_strength` | 1.0 | chroma strength |

Slower than hqdn3d; better edge preservation.

### `removegrain` — single-frame modes
Takes `mode=<0–24>`. Modes:
- `0` leave unchanged
- `1` min/max neighbour
- `2..4` progressively stronger clipping
- `11/12` 3×3 smooth (mode 11 is the most common "mild")
- `17` increase similarity
- `19..24` strong median variants

Per-plane: `removegrain=m0=11:m1=2:m2=2`.

### `nnedi` — neural-network edge-directed interpolation
Primarily a deinterlacer/upscaler. Requires `nnedi3_weights.bin`.
| Option | Default | Notes |
|---|---|---|
| `weights` | nnedi3_weights.bin | NNEDI3 weights file |
| `deint` | all | `all`, `interlaced` |
| `field` | a | `a` auto, `t` top, `b` bottom, `tf`/`bf` top/bottom force |
| `planes` | 7 | plane bitmask |
| `nsize` | s32x4 | neurons/patch size |
| `nns` | n32 | number of neurons |
| `qual` | fast | `fast` or `slow` |
| `etype` | a | prediction `a` absolute or `s` squared |
| `pscrn` | new | prescreener version |

### `derain` — DNN rain-removal filter
Uses `dnn_processing` under the hood with a rain-removal model.
- requires: `dnn_backend=tensorflow` or `openvino` build
- model sources: FFmpeg lab DNN models repo

### `dnn_processing` — generic DNN filter
| Option | Default | Notes |
|---|---|---|
| `dnn_backend` | native | `native`, `tensorflow`, `openvino` |
| `model` | - | path to .pb/.xml/.model |
| `input` | - | input tensor name (often `x` or `input`) |
| `output` | - | output tensor name (often `y`, `output`) |
| `options` | - | backend-specific opts |
| `async` | 1 | async exec |
| `nireq` | 0 | inference requests |

Use for super-resolution (ESPCN, EDSR, SRCNN) and derain. Build requirement: `--enable-libtensorflow` OR `--enable-libopenvino` OR the native (limited) backend.

---

## Audio denoise tables

### `afftdn` — FFT-based audio denoise
| Option | Default | Notes |
|---|---|---|
| `nr` | 12 | reduction amount dB |
| `nf` | -50 | noise floor dB (-80..-20) |
| `nt` | w | noise type: `w` white, `v` vinyl, `s` shellac, `c` custom |
| `bn` | - | custom band noise (pairs of freq:noise) |
| `rf` | -1 | residual floor dB |
| `tn` | 0 | track noise updates (0/1) |
| `tr` | 0 | track residual (0/1) |
| `om` | o | output mode: `i` input, `o` output, `n` noise |
| `ab` | 0.05 | adaptability |
| `gs` | 1.0 | gain smoothing |

Common: `afftdn=nf=-25` (moderate), `nf=-20` (aggressive), `nf=-40` (gentle).

### `anlmdn` — audio non-local means
| Option | Default | Notes |
|---|---|---|
| `s` | 0.00001 | noise strength |
| `p` | 0.002 | patch duration sec |
| `r` | 0.006 | research duration sec |
| `o` | 0.75 | output overlap |
| `m` | 15 | smooth factor |

Preserves voice transients. `anlmdn=s=7:p=0.002:r=0.002` is reference-quality.

### `arnndn` — RNN audio denoise (RNNoise)
| Option | Default | Notes |
|---|---|---|
| `m` | - | **required** path to .rnnn model |
| `mix` | 1.0 | mix 0..1 (dry/wet) |

Does not ship a model. Grab from `xiph/rnnoise` repo (look for `bd.rnnn`, `std.rnnn`, `cb.rnnn`, `mp.rnnn`).

---

## TF / OpenVINO build note

macOS Homebrew `ffmpeg` and most Ubuntu/Debian packages do NOT include `--enable-libtensorflow` or `--enable-libopenvino`. Check:

```bash
ffmpeg -hide_banner -buildconf | grep -E 'tensorflow|openvino'
ffmpeg -hide_banner -filters | grep dnn_processing
```

If missing:
- **macOS**: build from source with `brew install tensorflow` (or use static TF C API from TF releases), then `./configure --enable-libtensorflow`.
- **Linux**: same; or `apt install libtensorflow-dev` on Ubuntu 22.04+. OpenVINO via Intel's installer and `./configure --enable-libopenvino`.
- **Windows**: pre-built binaries at BtbN/FFmpeg-Builds include TF in full / gpl-shared variants.
- **Docker**: `jrottenberg/ffmpeg` full variant; or `jellyfin-ffmpeg` for OpenVINO.

Native backend: limited ops, mostly for SRCNN-style small nets, model format `.model` (internal).

---

## Known model sources

Not direct links — these are the repos to grep/browse (update as ecosystem shifts):

| Model family | Purpose | Where to find |
|---|---|---|
| ESPCN | 2x / 3x / 4x super-resolution (fast) | FFmpeg lab DNN models repo (github `guoyejun/dnn_processing` or `FFmpeg/FFmpeg` `tools/python` utilities) |
| EDSR | 2x / 3x / 4x SR (higher quality, slower) | same as ESPCN |
| SRCNN | 2x / 3x SR (original SR paper) | same |
| derain (DNN) | rain streak removal | FFmpeg lab DNN models repo |
| RNNoise `bd.rnnn` | broadcast/broadband denoise | `github.com/xiph/rnnoise` |
| RNNoise `std.rnnn` | standard voice denoise | same repo |
| RNNoise `cb.rnnn` | conf-bridge tuned | third-party (search `richardpl/rnnoise-models` or similar) |
| RNNoise `mp.rnnn` | music+podcast tuned | third-party |

For TF models: convert `.pb` from Keras/TensorFlow saved-model via `tf.saved_model` → frozen graph. Watch input tensor name (`input`, `x`, `input_1`) — must match `input=` arg.
For OpenVINO: `model optimizer` converts to `.xml`+`.bin`. Both files must sit side-by-side; point `model=` at the `.xml`.

Model input/output sizes (height × width × channels) are baked in — you cannot change them at runtime.

---

## Recipe book

### VHS / DVD rip restoration
```bash
ffmpeg -i vhs_rip.vob \
  -vf "bwdif=1,hqdn3d=6:4:8:6,removegrain=mode=17,eq=saturation=1.1,format=yuv420p" \
  -af "highpass=f=80,lowpass=f=14000,afftdn=nf=-25,loudnorm" \
  -c:v libx264 -crf 18 -preset slow -c:a aac -b:a 192k \
  vhs_restored.mp4
```

### Low-light webcam, real-time
```bash
ffmpeg -i webcam.mp4 \
  -vf "hqdn3d=4:3:6:4.5" \
  -c:v libx264 -crf 20 -preset veryfast \
  webcam_clean.mp4
```

### DSLR high-ISO night shot (4K 10-bit)
```bash
ffmpeg -i dslr_iso6400.mov \
  -vf "nlmeans=s=1.2:p=7:r=15,format=yuv420p10le" \
  -c:v libx265 -crf 20 -preset medium -tag:v hvc1 \
  dslr_denoised.mp4
```

### Film grain — preserve tastefully (light denoise + re-add grain)
```bash
ffmpeg -i film_scan.mov \
  -vf "bm3d=sigma=3:block=4:bstep=2:group=1,noise=alls=6:allf=t+u" \
  -c:v libx264 -crf 17 -preset slow \
  film_preserved.mp4
```

### Film grain — fully remove
```bash
ffmpeg -i film_scan.mov \
  -vf "bm3d=sigma=15:block=4:bstep=2:group=1" \
  -c:v libx264 -crf 18 -preset slow \
  film_clean.mp4
```

### 2x ESPCN super-resolution (TensorFlow)
```bash
ffmpeg -i small.mp4 \
  -vf "dnn_processing=dnn_backend=tensorflow:model=espcn_2x.pb:input=x:output=y,format=yuv420p" \
  -c:v libx264 -crf 18 -preset slow \
  big.mp4
```

### Lavalier mic with HVAC hum + hiss
```bash
ffmpeg -i mic.wav \
  -af "highpass=f=80,afftdn=nf=-25,anlmdn=s=7:p=0.002:r=0.002,loudnorm" \
  mic_clean.wav
```

### Conference recording with RNNoise + normalize
```bash
ffmpeg -i conf.wav \
  -af "arnndn=m=bd.rnnn,loudnorm=I=-16:TP=-1.5:LRA=11" \
  conf_clean.wav
```

### Static surveillance camera (temporal denoise)
```bash
ffmpeg -i cam.mp4 \
  -vf "atadenoise=0a=0.02:0b=0.04:1a=0.02:1b=0.04:2a=0.02:2b=0.04:s=15" \
  -c:v libx264 -crf 20 \
  cam_clean.mp4
```

### Chain: denoise → deband → grade (use ffmpeg-lut-grade skill after)
```bash
ffmpeg -i src.mov \
  -vf "nlmeans=s=1.0:p=7:r=15,gradfun=3.5:8,format=yuv420p10le" \
  -c:v libx265 -crf 18 -preset slow -tag:v hvc1 \
  out.mp4
```
