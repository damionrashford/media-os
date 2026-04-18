# Model Comparison — AI Audio Denoisers

All three models shipped here are **commercial-safe** (see `LICENSES.md`).

## Summary matrix

| Model            | License | Params  | Speed (CPU)   | GPU req? | Native SR | Dereverb? | BWE? | Strength                                | Weakness                                      |
| ---------------- | ------- | ------- | ------------- | -------- | --------- | --------- | ---- | --------------------------------------- | --------------------------------------------- |
| DeepFilterNet    | MIT     | ~2M     | ~1x realtime  | No       | 48 kHz    | Partial   | No   | Realtime, full-band, single binary      | Aggressive on music / ambience                |
| RNNoise (arnndn) | BSD-3   | ~90k    | Several x RT  | No       | 48 kHz    | No        | No   | Already in ffmpeg, zero-install         | Lower quality than DeepFilterNet; needs `.rnnn` file |
| Resemble Enhance | Apache 2.0 | ~100M+ | 0.2-0.5x RT  | Helpful  | 44.1 kHz  | Yes       | Yes  | Full restoration in one pass            | Slow on CPU, forces 44.1 kHz output           |

## DeepFilterNet — the default

- Author: Hendrik Schröter (Rikorose)
- Paper: "DeepFilterNet: A Low Complexity Speech Enhancement Framework for Full-Band Audio based on Deep Filtering" (Interspeech 2022)
- V2/V3 variants: DeepFilterNet2 (2023) and DeepFilterNet3 (2024) are the current defaults.
- Runs on CPU in real time. Prebuilt Rust binary (`deep-filter`) available via `cargo install deep-filter` or release tarball.
- Python wrapper `pip install deepfilternet` or `pip install deep_filter`.

**Recipes:**

```bash
# Best quality (uses DeepFilterNet3 by default in recent releases)
deep-filter -o out_dir input.wav

# Force a specific model
deep-filter -m /path/to/DeepFilterNet3 -o out_dir input.wav

# Control post-filter beta (stronger suppression)
deep-filter --post-filter-beta 0.02 -o out_dir input.wav
```

## RNNoise — the zero-install baseline

- Author: Xiph.Org / Mozilla (Jean-Marc Valin, 2017)
- Paper: "A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement" (2018)
- Shipped as `arnndn` filter inside ffmpeg since FFmpeg 4.1.
- Requires a `.rnnn` model file; ffmpeg does not bundle one.

Download models from `https://github.com/GregorR/rnnoise-models`:
- `cb.rnnn` (conjoined-burgers) — general speech (most common)
- `bd.rnnn` (beguiling-drafter) — slightly different voice
- `lq.rnnn` (leavened-quisling) — aggressive suppression
- `mp.rnnn` (marathon-prescription) — less aggressive

Usage:

```bash
ffmpeg -i noisy.wav -af arnndn=m=cb.rnnn clean.wav
```

Strengths: very low CPU cost (can run real-time on a Raspberry Pi). Good for live streams.
Weaknesses: noticeably worse than DeepFilterNet on complex backgrounds (café, keyboard clicks, music bleed).

## Resemble Enhance — the restoration workhorse

- Author: Resemble AI
- Two stages under the hood: **denoiser** (mel-conditional diffusion) + **enhancer** (CFM-based generative upscaler).
- Runs denoise-only via `denoise(wav, sr)`; runs the full pipeline via `enhance(wav, sr)`.
- Always outputs 44.1 kHz (bandwidth extension target).
- Supports GPU (CUDA) and MPS (Apple Silicon) with CPU fallback.

Flags that matter:
- `nfe` (number of function evaluations): 64 default; 128 slightly better but 2x slower.
- `solver`: `midpoint` (default, best), `euler` (fast), `rk4` (debug only).
- `lambd` (lambda strength): 0.0 very light, 1.0 full. 0.5 default is a good balance.
- `tau`: noise schedule parameter; leave at 0.5.

**Recipes:**

```python
from resemble_enhance.enhancer.inference import denoise, enhance
import soundfile as sf, torch
wav, sr = sf.read("noisy.wav")
wav_t = torch.from_numpy(wav).float()
# Denoise only
clean, out_sr = denoise(wav_t, sr, device="cuda")
sf.write("clean.wav", clean.cpu().numpy(), out_sr)
# Full enhance (denoise + dereverb + BWE)
enhanced, out_sr = enhance(wav_t, sr, device="cuda", nfe=64, solver="midpoint", lambd=0.5, tau=0.5)
sf.write("enhanced.wav", enhanced.cpu().numpy(), out_sr)
```

## Decision tree

1. **Need real-time CPU speech denoise, commercial license?** DeepFilterNet (MIT).
2. **Need fastest possible, already in ffmpeg?** RNNoise via `arnndn` (BSD-3).
3. **Old / muffled / reverberant recording, need full restoration?** Resemble Enhance (Apache 2.0).
4. **Music source — isolate vocals from instrumental?** Not this skill; use `media-demucs`.
5. **Voice recording pre-ASR?** DeepFilterNet (best quality / speed tradeoff).
6. **Live podcast / streaming?** DeepFilterNet (Rust binary, low latency) or RNNoise (lowest latency).

## Known failure modes

- **All three:** trained on speech. Input containing music loses the music as "noise".
- **DeepFilterNet:** occasional consonant smearing on very soft speech. Try `--post-filter-beta 0.02` if output sounds muffled.
- **RNNoise:** obvious "musical noise" artifacts on broadband backgrounds. Upgrade to DeepFilterNet.
- **Resemble Enhance:** can hallucinate breath sounds at sentence boundaries on very low-SNR input. Try `--strength 0.3` for lighter processing.

## When to chain with other skills

- `media-whisper` (ASR) — denoise **before** transcription; dramatic hallucination reduction.
- `media-demucs` (source separation) — separate voice/music first, denoise voice stem, re-mix. Do not denoise the full mix.
- `ffmpeg-audio-filter` — apply `loudnorm` AFTER denoise, not before. Post-denoise output has different headroom.
- `ffmpeg-audio-fx` — deess AFTER denoise to tame sibilance that the model may leave intact.
- `media-ffmpeg-normalize` — batch EBU R128 loudness on a folder of already-denoised files.
