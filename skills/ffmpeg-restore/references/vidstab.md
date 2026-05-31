# vid.stab / deshake reference

Full option tables for ffmpeg stabilization filters, transforms.trf file format, tripod mode, a recipe gallery, the full stabilize pipeline (pre-crop → stabilize → post-crop), and a build-from-source note for users missing vid.stab.

Primary sources:
- https://ffmpeg.org/ffmpeg-filters.html#vidstabdetect
- https://ffmpeg.org/ffmpeg-filters.html#vidstabtransform
- https://ffmpeg.org/ffmpeg-filters.html#deshake
- https://ffmpeg.org/ffmpeg-filters.html#deshake_005fopencl
- https://trac.ffmpeg.org/wiki/FilteringGuide

---

## vidstabdetect (pass 1)

Analyzes the video and writes a plain-text `transforms.trf` sidecar describing per-frame motion.

| Option        | Range / Default        | Meaning |
|---------------|------------------------|---------|
| `result`      | path (`transforms.trf`)| Output sidecar path. Use absolute path if not running pass 2 from same cwd. |
| `shakiness`   | 1–10 (default 5)       | Expected shake level. 1 = mild / 10 = extreme. Higher values sample more motion candidates. |
| `accuracy`    | 1–15 (default 15)      | Detection accuracy; 15 = slowest + best. Almost always leave at 15. |
| `stepsize`    | 1–32 (default 6)       | Pixel step when searching for matching blocks. Lower = slower + more accurate. |
| `mincontrast` | 0.0–1.0 (default 0.25) | Contrast threshold for measurement fields. Lower captures more of low-contrast frames; higher ignores weak fields. |
| `tripod`      | frame # (default 0 = off) | Reference frame to lock to for tripod mode (pass 1 side). |
| `show`        | 0/1/2 (default 0)      | 0 = no overlay; 1 = draw fields on output; 2 = draw fields + numbers. Useful to preview motion. |

Tips:
- `show=1` plus a visible encode (not `-f null -`) lets you see what the detector is tracking.
- Run once with `accuracy=9` for a quick iteration, then with `accuracy=15` for the final pass.
- The command **must** decode frames; do not use `-c:v copy`.

---

## vidstabtransform (pass 2)

Applies the motion data from `transforms.trf` to produce a stabilized output.

| Option       | Range / Default            | Meaning |
|--------------|----------------------------|---------|
| `input`      | path (`transforms.trf`)    | Sidecar from pass 1. |
| `smoothing`  | frames ≥ 0 (default 10)    | Length of smoothing window. 30 ≈ 1s at 30fps. Higher → smoother but floaty. |
| `optalgo`    | `gauss` / `avg` (default `gauss`) | Camera-path smoothing algorithm. `avg` is faster but less graceful. |
| `maxshift`   | pixels (default -1 = no limit) | Max allowed translational shift. Clamp to avoid extreme repositioning. |
| `maxangle`   | rad (default -1 = no limit) | Max allowed rotation. |
| `crop`       | `keep` / `black` (default `keep`) | Border fill. `black` shows exposed background; `keep` repeats previous pixels. |
| `invert`     | 0/1 (default 0)            | 1 inverts transforms (useful for debugging). |
| `relative`   | 0/1 (default 0)            | 1 = transforms are relative to previous frame; 0 = absolute (default since vid.stab 1.1). |
| `zoom`       | percent (default 0)        | Fixed zoom to hide borders. Negative zooms out. |
| `optzoom`    | 0 / 1 / 2 (default 1)      | 0 = no auto zoom; 1 = optimal static zoom for whole clip; 2 = adaptive per-frame zoom. |
| `zoomspeed`  | float ≥ 0 (default 0.25)   | Max percent zoom per frame, only when `optzoom=2`. |
| `interpol`   | `no`/`linear`/`bilinear`/`bicubic` (default `bilinear`) | Interpolation used for warping. `bicubic` is sharpest / slowest. |
| `tripod`     | 0/1 (default 0)            | Virtual tripod mode (pass 2 side). Set `smoothing=0` and pair with detect-side `tripod=N`. |
| `debug`      | 0/1 (default 0)            | Print transform values per frame. |

Notes:
- Pair `optzoom=2` with `zoomspeed` to prevent the zoom from "breathing".
- `crop=black` with no zoom is useful if you plan to post-crop manually; you can see exactly where the cut lives.
- Always re-encode video — stream copy is impossible.

---

## deshake (builtin, single-pass)

Cheaper heuristic motion estimator, no sidecar.

| Option    | Range / Default           | Meaning |
|-----------|---------------------------|---------|
| `x`,`y`,`w`,`h` | -1 / frame region   | ROI to estimate motion in (-1 = whole frame). |
| `rx`,`ry` | 0–64 (default 16)         | Max horizontal/vertical shift searched. |
| `edge`    | `blank`/`original`/`clamp`/`mirror` (default `mirror`) | Edge fill behavior after shift. |
| `blocksize` | 4–128 (default 8)        | Block size for motion estimate. |
| `contrast`  | 1–255 (default 125)      | Contrast threshold for blocks to include. |
| `search`    | `exhaustive`/`less` (default `exhaustive`) | Search strategy. |
| `filename`  | path                     | Optional file for motion-log dump. |

Quality floor is well below vid.stab; use only when you can't run two passes.

---

## deshake_opencl (GPU)

OpenCL-accelerated variant of `deshake`. Requires `-init_hw_device opencl`.

| Option        | Default | Meaning |
|---------------|---------|---------|
| `tripod`      | 0       | Enable tripod mode (static shots). |
| `debug`       | 0       | Print debug info. |
| `adaptive_crop` | 1     | Crop to hide unstable borders. |
| `refine_features` | 1   | Subpixel feature refinement. |
| `smooth_strength` | 0.0 | Manual smoothing; 0 = automatic. |
| `smooth_window_multiplier` | 2.0 | Smoothing window in seconds. |

Launch boilerplate:
```bash
ffmpeg -init_hw_device opencl=ocl:0.0 -filter_hw_device ocl \
  -i in.mp4 \
  -vf "format=nv12,hwupload,deshake_opencl,hwdownload,format=yuv420p" \
  -c:v libx264 -crf 18 out.mp4
```

---

## transforms.trf file format

Plain text. Header lines begin with `#`. Each frame block looks like:

```
Frame 1 (List 3 [
  (LM x 12 y -5 uval 0.91 contrast 0.35)
  ...
])
#transforms
1 0 0.03 1.02 1
```

The `#transforms` block (below the measurement fields) is the one `vidstabtransform` actually consumes: `frame dx dy rot zoom ok`. You can safely inspect, diff, or archive this file; a corrupt or zero-length `.trf` means pass 1 failed.

---

## Tripod mode (virtual lock-off)

Use when the shot should be **completely still** (interview, product shot).

```bash
# Pass 1: lock every frame to the pose at frame 1.
ffmpeg -i in.mp4 \
  -vf vidstabdetect=shakiness=3:accuracy=15:tripod=1:result=tripod.trf \
  -f null -

# Pass 2: smoothing=0, crop=keep so no border is exposed.
ffmpeg -i in.mp4 \
  -vf "vidstabtransform=input=tripod.trf:smoothing=0:crop=keep:optzoom=1,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -c:a copy locked.mp4
```

Choose a `tripod=N` frame that is in-focus and pose-representative; every later frame is warped back to that pose.

---

## Recipe gallery

### Light handheld (talking head, slow pan)

```
vidstabdetect=shakiness=3:accuracy=15:result=a.trf
vidstabtransform=input=a.trf:smoothing=15:zoom=0:crop=keep,unsharp=5:5:0.8:3:3:0.4
```

### Heavy handheld (walking, running)

```
vidstabdetect=shakiness=8:accuracy=15:result=a.trf
vidstabtransform=input=a.trf:smoothing=60:optzoom=2:zoomspeed=0.3:crop=black,unsharp=5:5:0.8:3:3:0.4
```

### Mounted-car / GoPro (moderate vibration)

```
vidstabdetect=shakiness=5:accuracy=15:result=a.trf
vidstabtransform=input=a.trf:smoothing=30:optzoom=1:crop=black,unsharp=5:5:0.8:3:3:0.4
```

### Fake tripod (see above)

```
vidstabdetect=shakiness=3:tripod=1:result=a.trf
vidstabtransform=input=a.trf:tripod=1:smoothing=0:crop=keep,unsharp=5:5:0.8:3:3:0.4
```

### Drone (mild buffet, avoid warping horizon)

```
vidstabdetect=shakiness=4:accuracy=15:result=a.trf
vidstabtransform=input=a.trf:smoothing=45:maxangle=0.05:optzoom=1:crop=black
```

(`maxangle` clamps rotation so horizon doesn't wobble.)

---

## Full pipeline: pre-crop → stabilize → post-crop

Shaky edges (tape, dust, vignette) confuse the motion estimator. Consider cropping *before* detect:

```bash
# 1. Crop away junk edges before analysis.
ffmpeg -i raw.mov -vf "crop=iw-40:ih-40" -c:v libx264 -crf 15 clean.mp4

# 2. Detect.
ffmpeg -i clean.mp4 -vf vidstabdetect=shakiness=5:accuracy=15:result=a.trf -f null -

# 3. Transform with optzoom to hide residual borders.
ffmpeg -i clean.mp4 \
  -vf "vidstabtransform=input=a.trf:smoothing=30:optzoom=1:crop=black,unsharp=5:5:0.8:3:3:0.4" \
  -c:v libx264 -crf 18 -c:a copy stab.mp4

# 4. Optional: final crop + re-aspect to hide anything still wiggling at edges.
ffmpeg -i stab.mp4 -vf "crop=iw*0.95:ih*0.95,scale=1920:1080" -c:v libx264 -crf 18 final.mp4
```

For long clips, prepend `-fflags +genpts` to the pass-2 input to avoid timebase drift in the output mux.

---

## Building ffmpeg with vid.stab (missing-filter case)

If `ffmpeg -filters | grep vidstab` returns nothing:

**macOS (Homebrew):**
```bash
brew install ffmpeg          # includes libvidstab since 2019
```

**From source (Linux/other):**
```bash
# 1. vid.stab library
git clone https://github.com/georgmartius/vid.stab.git
cd vid.stab && cmake . && make && sudo make install

# 2. ffmpeg, configured with libvidstab
./configure --enable-gpl --enable-libvidstab \
            --enable-libx264 --enable-libfreetype
make -j$(nproc)
sudo make install
```

Verify:
```bash
ffmpeg -filters | grep vidstab
# vidstabdetect
# vidstabtransform
```

If building is not an option, fall back to `deshake` — lower quality, but always available.
