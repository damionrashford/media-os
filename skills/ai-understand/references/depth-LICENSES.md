# Licenses — media-depth

Every model in this skill is picked for **open source + commercial-safe** use. This file is the compliance cheat sheet — keep it current.

## Inference code / scripts

- `depth.py` (this repo) — MIT, same as the parent skills suite. Stdlib-only plus PyPI deps below.

## Runtime deps

| Package              | License              | Notes                                              |
|----------------------|----------------------|----------------------------------------------------|
| transformers (HF)    | Apache 2.0           | huggingface/transformers                           |
| torch                | BSD-3-Clause         | pytorch/pytorch                                    |
| opencv-python        | Apache 2.0           | opencv/opencv (build scripts; the lib itself is Apache 2.0) |
| numpy                | BSD-3-Clause         |                                                    |
| Pillow               | MIT-CMU (HPND)       | Effectively permissive; commercial-safe            |

## Model weights

### Depth-Anything v2 (all public variants)

- **License:** Apache 2.0
- **Covers:** `depth-anything/Depth-Anything-V2-Small-hf`, `-Base-hf`, `-Large-hf`, and the `-Metric-Indoor-*` / `-Metric-Outdoor-*` fine-tunes.
- **Commercial use:** yes.
- **Model card repos:** `https://huggingface.co/depth-anything`

**Nuance for metric fine-tunes**: The metric variants were fine-tuned on Hypersim (CC-BY-NC-SA for the dataset) and Virtual KITTI (CC-BY-NC-SA). **Model weights remain Apache 2.0** — Apache covers the final weights file the lab publishes. The NC restriction applies to redistributing *the training images* themselves, not to the output of the model or the model file. This is the consensus interpretation as of April 2026; track the Depth-Anything v2 model card for any clarifying statements.

### MiDaS v3.1

- **License:** MIT
- **Covers:** `Intel/dpt-swinv2-tiny-256`, `Intel/dpt-large-384`, `Intel/dpt-beit-large-512`.
- **Commercial use:** yes.
- **Upstream:** `https://github.com/isl-org/MiDaS`

## Explicitly DROPPED

These were considered and rejected for the commercial-safe bar of this skill:

- **ZoeDepth** — the canonical upstream repo is MIT, but some fine-tuned variants are research-licensed. To keep this skill unambiguous, we do not include it. Reconsider if and when the fine-tunes get reclassified.
- **Metric3D v2** — research license. Not distributable for commercial use.
- **Marigold** — CreativeML OpenRAIL-M (Stable Diffusion style). Usage restrictions on certain use cases; NOT a permissive license.
- **Proprietary cloud APIs** (Google Cloud Vision depth, Apple ARKit, Niantic Scaniverse) — paid, closed, out of scope.

## Derivative output (depth maps / parallax video / stereo pairs)

Output of an Apache 2.0 or MIT model is **not** encumbered by the upstream license unless the license explicitly extends to outputs (Apache and MIT do not). You may:

- Ship the depth PNG/EXR as a product asset.
- Publish the parallax MP4 on a commercial channel.
- Resell the stereo pair as part of a paid 3D download.

You must:

- Keep the NOTICE / LICENSE files if redistributing the **model weights** themselves (Apache 2.0 § 4).
- Preserve the MIT / Apache copyright notice if redistributing the **inference code** from the upstream repo (not this skill's `depth.py`, which is MIT).

## Reporting a license change

If any of the HuggingFace model cards above flips to a restricted license (CreativeML OpenRAIL-M, CC-BY-NC, RAIL, etc.), remove the model from `MODEL_REGISTRY` in `scripts/depth.py` and update this file. Do not silently keep shipping a model whose license slipped.
