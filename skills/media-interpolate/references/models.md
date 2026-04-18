# Interpolation Model Reference

All models are open-source AND commercial-safe. DAIN (research-only) is
intentionally excluded from this skill.

## RIFE — the default

- **Repo:** https://github.com/hzwer/Practical-RIFE  (author) and https://github.com/hzwer/ECCV2022-RIFE (paper)
- **NCNN Vulkan build:** https://github.com/nihui/rife-ncnn-vulkan
- **License:** MIT (both code and NCNN port)
- **Paper:** RIFE: Real-Time Intermediate Flow Estimation for Video Frame Interpolation (ECCV 2022)
- **CLI:** `rife-ncnn-vulkan` — Vulkan cross-platform (NVIDIA/AMD/Intel/Apple Silicon via MoltenVK)
- **Bundled models (`-m`):**
  - `rife-v2.3`, `rife-v2.4`, `rife-v3.0`, `rife-v3.1`, `rife-v4` — legacy versions
  - `rife-v4.6` — current stable, best default
  - `rife-anime-v4.6` — anime/cel-art tuned
  - `rife-anime` — older anime weights
- **Output:** 2x by default; call iteratively for 4x / 8x / 16x.
- **Two-image mode:** `rife-ncnn-vulkan -0 a.png -1 b.png -o mid.png -m rife-v4.6`
- **Directory mode:** `rife-ncnn-vulkan -i in_dir -o out_dir -m rife-v4.6`
- **GPU:** Vulkan — no CUDA required. Apple Silicon works via MoltenVK.
- **CPU fallback:** `-g -1` uses CPU; usable but slow.
- **Benchmark (1080p → 60fps double, RTX 3070):** ~60 output fps.

## FILM — Google 2022

- **Repo:** https://github.com/google-research/frame-interpolation
- **Paper:** FILM: Frame Interpolation for Large Motion (Reda et al., ECCV 2022)
- **License:** Apache-2.0
- **CLI:** `python frame-interpolation/eval/interpolator_cli.py --pattern '*.png' --model_path <saved_model> --times_to_interpolate K`
- **Saved models:** `Style`, `L1`, `VGG` under `pretrained_models/film_net/<name>/saved_model/`
- **Engine:** TensorFlow (requires `pip install tensorflow mediapy`)
- **Best for:** large motion (fast pans, explosions, sports), near-duplicate photos (a year apart, same subject).
- **Benchmark:** ~10× slower than RIFE at comparable perceptual quality on typical content. Better on pathological large-motion scenes.

## PractCL

- **Repo:** https://github.com/fatheral/PractCL
- **License:** MIT
- **Engine:** PyTorch
- **Best for:** research experiments, cascaded refinement. Not a day-to-day production tool.

## Comparison grid

| Model     | License     | Speed (rel.) | Quality on normal content | Quality on large motion | Install complexity |
|-----------|-------------|--------------|---------------------------|-------------------------|--------------------|
| RIFE ncnn | MIT         | 1.0×         | Excellent                 | Good                    | Download zip       |
| RIFE torch| MIT         | ~1.5× RIFE ncnn | Excellent               | Good                    | torch + weights    |
| FILM      | Apache-2.0  | ~0.1×        | Excellent                 | Best                    | TF + saved_model   |
| PractCL   | MIT         | ~0.3×        | Good                      | Medium                  | torch              |

## NOT in this skill

| Tool   | License           | Reason                       |
|--------|-------------------|------------------------------|
| DAIN   | Research-only     | Not commercial-safe          |
| XVFI   | Apache-2.0 but the pretrained weights have unclear distribution terms — audit before recommending. |

## Benchmarks note

Frame-rate numbers vary wildly with GPU and frame resolution. RIFE ncnn on
Apple Silicon M-series GPUs is usable but notably slower than a discrete
NVIDIA GPU of similar tier. Always measure on your own hardware before
committing to a workflow.

## Temporal note

All three models are pairwise: they look at frames N and N+1 and synthesize
an in-between. They do NOT reason about longer time context. For scene-cut
handling use `media-scenedetect` to segment first, then process each scene
independently.
