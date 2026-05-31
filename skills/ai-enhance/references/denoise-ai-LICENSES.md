# License Audit — media-denoise-ai

Every model shipped by this skill has been verified **commercial-safe** (no restrictions on commercial use).

## Allowed — all three fully commercial-safe

| Model            | Code License | Weights License | Commercial use?     | Source                                                   |
| ---------------- | ------------ | --------------- | ------------------- | -------------------------------------------------------- |
| DeepFilterNet    | MIT          | MIT             | Yes, unconditionally | https://github.com/Rikorose/DeepFilterNet                |
| RNNoise          | BSD-3-Clause | BSD-3-Clause    | Yes, unconditionally | https://gitlab.xiph.org/xiph/rnnoise                     |
| Resemble Enhance | Apache 2.0   | Apache 2.0      | Yes, unconditionally | https://github.com/resemble-ai/resemble-enhance          |

## ffmpeg arnndn clarification

The `arnndn` audio filter in ffmpeg is an in-tree re-implementation of RNNoise licensed under LGPL 2.1+ / GPL 2+ (same as the rest of ffmpeg). The downloadable `.rnnn` model files from https://github.com/GregorR/rnnoise-models are under the BSD-3 license of the original RNNoise project. No commercial restrictions on either.

## Excluded (not used by this skill)

Nothing relevant. All leading open-source speech-denoise models are commercial-safe. The only AI-denoise tools that carry NC restrictions are:

- **Nvidia NVIDIA Broadcast / RTX Voice** — proprietary Nvidia SDK, closed-source.
- **Krisp** — proprietary SaaS, closed-source.
- **Adobe Enhance Speech** — proprietary SaaS, closed-source.

This skill does not integrate any proprietary / closed-source denoiser.

## Output copyright

Denoised output is a derivative of your input. The model license only governs the model itself; the audio you feed in is yours and the cleaned output inherits your ownership. No license attribution is required when you ship denoised audio commercially.

## Attribution recommendations (optional but good practice)

- DeepFilterNet: cite Schröter et al. "DeepFilterNet" (Interspeech 2022) if using in academic work.
- RNNoise: cite Valin "A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement" (2018).
- Resemble Enhance: no citation requirement per Apache 2.0; repo link courtesy.
