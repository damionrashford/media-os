# media-lipsync model catalog

Only MIT / Apache 2.0 weights with clear commercial terms.

## LivePortrait — Kuaishou 2024

- License: **MIT** (code AND weights).
- GitHub: https://github.com/KwaiVGI/LivePortrait
- HuggingFace: https://huggingface.co/KwaiVGI/LivePortrait
- Architecture: implicit keypoint-based portrait animation (descends from Face Vid2Vid / First-Order Motion family), retrained with audio conditioning in the 2024 release.
- VRAM: ~4-8 GB FP16.
- Inputs: ONE still image (source) + ONE driving (audio WAV, or video MP4 of a real face).
- Output: mp4 at driving's fps (typically 24/25/30).
- Best at: short clips (10-20 s), single visible face.
- Limitations:
  - Weak phoneme-level lip sync in audio-driven mode (plausible talking but not tight).
  - Identity drift past 30 s.
  - Profile views (>45° off-axis) degrade.
  - The "animals" variant is separate weights — use only if animal support is needed.

## LatentSync — ByteDance 2025

- License: **Apache 2.0** (code) + weights under same terms per HF model card.
- GitHub: https://github.com/bytedance/LatentSync
- HuggingFace: https://huggingface.co/ByteDance/LatentSync
- Architecture: latent diffusion on the lip region, conditioned on Whisper audio embeddings + surrounding frame context.
- VRAM: ~24 GB FP16 for 512x512 output at 25 fps.
- Inputs: ONE video (face visible) + ONE audio.
- Output: same video, lips re-synced to new audio.
- Best at: dubbing, ADR, language swap, TTS-lip-alignment.
- Limitations:
  - Requires CUDA (xformers / flash-attn).
  - OOMs on long videos; split into chunks.
  - Occlusions over the mouth (hand, mic) cause artifacts.
  - Profile views degrade.

## Model selection flowchart

```
Input is a still image?
  -> LivePortrait (animate)
Input is a video?
  Need to change what the subject SAYS?
    -> LatentSync (sync / dub)
  Need to retarget a different person's EXPRESSIONS onto the subject?
    -> LivePortrait (animate --driving actor.mp4) — note: source is still a single frame
```

## Combining models

For best-in-class audio-driven talking-head from a still:

1. `media-sd` or your own still of a face.
2. LivePortrait audio-driven -> preliminary talking-head with plausible head motion.
3. LatentSync over LivePortrait's output -> tight lip sync on top.

This two-stage pipeline is noticeably better than LivePortrait's audio-driven output
alone, at the cost of 2x processing.

## Benchmarks (rough, H100)

| Task                                   | Time per 5 s clip |
|----------------------------------------|-------------------|
| LivePortrait audio-driven              | ~8 s              |
| LivePortrait video-driven              | ~5 s              |
| LatentSync 25 steps @ 512x512          | ~50 s             |
| LivePortrait -> LatentSync cascade     | ~60 s             |

On a 4090: roughly 2x the above. On M3 Max (LivePortrait only): 5-10x.
