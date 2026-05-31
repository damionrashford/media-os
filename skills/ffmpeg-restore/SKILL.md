---
name: ffmpeg-restore
description: >
  Use when the user asks to restore old footage, denoise video, clean up grain, remove noise, fix a noisy webcam, remove film grain, upscale with AI super-resolution, run RNNoise audio denoise, stabilize shaky footage, smooth handheld video, fix camera shake, de-wobble a GoPro clip, fix rolling shutter, run vid.stab detect/transform, IVTC a telecined file, convert 29.97i to 23.976p, reverse 3:2 pulldown, deinterlace broadcast content, detect duplicate fields, fix interlaced or mixed-cadence content, fix barrel or fisheye distortion, remove lens distortion, correct keystone or perspective, add or remove a vignette, un-shear tilted footage, rotate with expanded canvas, or run VapourSynth scripts (QTGMC, KNLMeansCL, BM3DCUDA, MVTools, SVPflow) in an ffmpeg pipeline.
argument-hint: "[operation] [input]"
---

# ffmpeg-restore

Footage restoration and geometric repair with ffmpeg (plus VapourSynth): denoising, super-resolution, stabilization, inverse telecine / deinterlacing, lens-distortion and perspective correction, and Python frame-server filtering. This skill is a consolidation — each technique's full playbook (recipes, option tables, gotchas, examples, troubleshooting) lives verbatim in a dedicated reference file. Read the matching reference before acting; it is the authoritative source.

Always invoke the `ffmpeg-docs` skill first to confirm any filter/flag before recommending it — it is the anti-hallucination guardrail.

## When to use

- Clean up noisy webcams, low-light/high-ISO footage, VHS/DVD rips, film scans; remove or preserve grain; AI super-resolution; broadband audio hiss/hum (RNNoise) → denoising.
- Smooth shaky handheld, GoPro/action-cam jitter, drone buffet; fake a locked-off tripod; pre-stabilize before VFX or grading → stabilization.
- IVTC telecined NTSC (29.97i → 23.976p), reverse 3:2 pulldown, deinterlace true-interlaced or mixed-cadence content, strip duplicate frames, fix field order → inverse telecine.
- Undistort barrel/fisheye or pincushion, fix keystone/perspective, add/remove vignette, arbitrary-angle rotate, un-shear → lens & perspective.
- Need QTGMC, KNLMeansCL, BM3DCUDA, MVTools, or SVPflow that ffmpeg lacks natively → VapourSynth.

## Techniques

- Read `references/denoise-restore.md` when the task is denoising, grain removal, restoration, AI super-resolution (ESPCN/EDSR/SRCNN), or audio denoise (afftdn/anlmdn/arnndn). Deep option tables in `references/denoise-restore-filters.md`.
- Read `references/stabilize.md` when the task is stabilizing shaky footage with vid.stab (2-pass detect/transform), deshake, or deshake_opencl. Deep option tables in `references/vidstab.md`.
- Read `references/ivtc.md` when the task is inverse telecine, deinterlacing variants, frame-rate / cadence conversion, field-order fixes, or duplicate-frame cleanup. Deep option tables in `references/ivtc-filters.md`.
- Read `references/lens-perspective.md` when the task is lens-distortion correction, keystone/perspective warp, vignette add/remove, arbitrary rotation, or shear. Deep option tables in `references/lens-perspective-filters.md`.
- Read `references/vapoursynth.md` when the task needs a `.vpy` frame-server chain (QTGMC, KNLMeansCL, BM3DCUDA, MVTools, SVPflow, AviSynth+ compat) piped into ffmpeg. Deep reference in `references/vapoursynth-reference.md`.

## Gotchas

- **IVTC filter order is critical:** `fieldmatch` MUST come before `decimate` — `fieldmatch,yadif=deint=interlaced,decimate`. Reversed, you decimate before matching and ship garbage. `decimate` needs CFR input; prepend `dejudder,fps=30000/1001` for VFR/mixed sources, and force CFR out with `-vsync cfr -r 24000/1001`. Never stream-copy IVTC output.
- **Every denoise filter trades detail for noise** — start mild and tune up; you cannot un-denoise. Denoise BEFORE encoding (post-compression noise is mostly irrecoverable). Keep 10-bit chains 10-bit (`format=yuv420p10le`).
- **vid.stab is 2-pass and re-encode-only:** pass 1 (`vidstabdetect`) writes `transforms.trf`, pass 2 (`vidstabtransform`) consumes it; stream copy is impossible. `smoothing` is in frames (30 ≈ 1s at 30fps). Apply `unsharp` AFTER the transform, never before. vid.stab cannot fix rolling shutter — pre-correct in Gyroflow/GoPro Player.
- **`lenscorrection` k1 sign:** NEGATIVE undistorts barrel, POSITIVE undistorts pincushion. `rotate` angle is RADIANS — use `N*PI/180`, and `ow=rotw(A):oh=roth(A)` to avoid clipped corners. `vignette mode=backward` removes a vignette. After any warp, add `crop`/`scale` and `-pix_fmt yuv420p` (filters can emit `yuva420p`).
- **Always run `idet` + `vfrdet` on ≥500 frames before choosing an IVTC/deinterlace pipeline** — container field-order flags lie. `bwdif` is the modern default deinterlacer; `qtgmc` (VapourSynth) is reference-quality.
- **Build flags gate several filters:** `dnn_processing` (TensorFlow/OpenVINO), `lensfun` (`--enable-liblensfun`), vid.stab (`--enable-libvidstab`), and the `vapoursynth` demuxer (`--enable-vapoursynth`) are absent from most distro/Homebrew builds. Verify with `ffmpeg -filters`/`-demuxers`/`-buildconf` and fall back accordingly.
- **`.vpy` scripts are arbitrary Python** — never run untrusted ones. `vspipe --y4m` is mandatory for ffmpeg piping (the Y4M header carries dimensions/fps/pixfmt). QTGMC needs `mvtools` + `nnedi3` + `havsfunc` + `mvsfunc` + `adjust` all installed.
- **Model/sidecar files are not shipped:** SR `.pb`/`.onnx`, `arnndn` `.rnnn` (from `xiph/rnnoise`), and lensfun DB strings (`lensfun-list`) must be obtained separately and matched exactly.

## Scripts

All under `scripts/`, stdlib-only, non-interactive, with `--dry-run` and `--verbose`. Invoke with `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py`.

- `denoise.py` — subcommands `video`, `grain`, `audio`, `sr`. See `references/denoise-restore.md`.
- `stabilize.py` — subcommands `stabilize` (2-pass), `deshake`, `check-build`. See `references/stabilize.md`.
- `ivtc.py` — `detect` plus IVTC pipelines. See `references/ivtc.md`.
- `lens.py` — subcommands `undistort-barrel`, `undistort-pincushion`, `lensfun`, `perspective`, `vignette`, `rotate`, `shear`. See `references/lens-perspective.md`.
- `vspipe.py` — subcommands `check`, `run`, `qtgmc-deinterlace`, `knl-denoise`, `bm3d-denoise`, `gen-vpy`. See `references/vapoursynth.md`.
