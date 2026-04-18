# Stem Separation Reference

Deep reference for `media-demucs`. Cross-link: see `SKILL.md` for quick-start workflow.

## 1. Model comparison

### Demucs (Meta, PyTorch)

| Model | Architecture | Stems | Notes |
|-------|--------------|-------|-------|
| `htdemucs` | Hybrid Transformer Demucs v4 | 4 (vocals / drums / bass / other) | Default. Fast, solid quality. |
| `htdemucs_ft` | Fine-tuned ensemble of 4 HT Demucs | 4 | Best overall quality. ~4× slower. |
| `htdemucs_6s` | HT Demucs, 6-stem variant | 6 (+ guitar + piano) | Guitar/piano are weaker — expect bleed. |
| `hdemucs_mmi` | Hybrid Demucs, MUSDB + extra | 4 | Legacy; superseded by `htdemucs`. |
| `mdx` | MDX-Net (frequency domain) | 4 | Older MDX-Net. |
| `mdx_extra` | MDX-Net with extra data | 4 | Higher quality; ~4 GB VRAM; slow. |
| `mdx_q` | Quantized MDX-Net | 4 | Small, CPU-friendly; quality trade-off. |
| `mdx_extra_q` | Quantized mdx_extra | 4 | Middle ground. |

### Spleeter (Deezer, TensorFlow)

| Preset | Stems |
|--------|-------|
| `spleeter:2stems` | vocals / accompaniment |
| `spleeter:4stems` | vocals / drums / bass / other |
| `spleeter:5stems` | + piano (vocals / drums / bass / piano / other) |

## 2. Quality vs speed vs VRAM

Rough relative numbers for a 3–4 min song at 44.1 kHz stereo.

| Model | Quality (SDR proxy) | Speed (GPU) | CPU speed | VRAM peak | Disk size |
|-------|----------------------|-------------|-----------|-----------|-----------|
| `htdemucs_ft` | 5/5 | slow (4× htdemucs) | very slow | ~3 GB | ~300 MB × 4 |
| `mdx_extra` | 5/5 | slow | very slow | ~4 GB | ~700 MB |
| `htdemucs` | 4/5 | fast | slow | ~2 GB | ~80 MB |
| `htdemucs_6s` | 4/5 | fast | slow | ~2 GB | ~80 MB |
| `mdx_extra_q` | 4/5 | fast | medium | ~2 GB | smaller |
| `mdx_q` | 3/5 | very fast | medium (best CPU) | ~1 GB | small |
| `spleeter:2stems` | 3/5 | very fast | fast | CPU ok | ~75 MB |
| `spleeter:4stems` | 3/5 | very fast | fast | CPU ok | ~75 MB |
| `spleeter:5stems` | 3/5 | very fast | fast | CPU ok | ~75 MB |

CPU estimates: `htdemucs` ~10 min/song, `htdemucs_ft` ~30 min, `mdx_q` ~4 min, Spleeter ~30 s.

## 3. Stem layouts per model

- **2-stem (demucs `--two-stems vocals`)**: `vocals.wav`, `no_vocals.wav`.
- **2-stem (spleeter `2stems`)**: `vocals.wav`, `accompaniment.wav`.
- **4-stem (demucs / spleeter `4stems`)**: `vocals`, `drums`, `bass`, `other`.
- **5-stem (spleeter `5stems`)**: `vocals`, `drums`, `bass`, `piano`, `other`.
- **6-stem (demucs `htdemucs_6s`)**: `vocals`, `drums`, `bass`, `guitar`, `piano`, `other`.

Demucs writes to: `<outdir>/<model>/<input-stem>/<stem>.<ext>`
Spleeter writes to: `<outdir>/<input-stem>/<stem>.wav`

## 4. Model download locations

Demucs downloads weights on first use into `~/.cache/torch/hub/checkpoints/` (torch hub).
Official repo: `facebookresearch/demucs` on HuggingFace Hub.

Spleeter downloads pretrained models into `pretrained_models/` next to the working dir (or `MODEL_PATH` env var).
Source: Deezer's `spleeter` GitHub repo.

Pin model cache with env vars:

```bash
export TORCH_HOME=/path/to/cache
export MODEL_PATH=/path/to/spleeter/models
```

## 5. Demucs CLI flag reference

| Flag | Purpose |
|------|---------|
| `-n NAME` | Select model (default `htdemucs`). |
| `--two-stems STEM` | Output STEM + `no_STEM` only. |
| `-o DIR` | Output directory. |
| `--device {cuda,cpu,mps}` | Force device (auto by default). |
| `--shifts N` | Average N random time shifts (2× cost each). 10 is a common max. |
| `--overlap F` | Overlap-add fraction between chunks (default 0.25). |
| `--segment S` | Max segment length in seconds; reduces VRAM. |
| `--jobs J` | Parallel jobs on CPU (effective only for non-GPU runs). |
| `--flac` | Write FLAC instead of WAV. |
| `--mp3` | Write MP3 (use `--mp3-bitrate K`). |
| `--int24` | 24-bit WAV output. |
| `--float32` | 32-bit float WAV. |
| `--clip-mode {rescale,clamp}` | Avoid overflow on reconstruction. |
| `--filename PATTERN` | Output filename template. |

Under VRAM pressure: first try `--segment 7`, then switch model, then `--device cpu`.

## 6. Recipe book

### Karaoke production (pop track)

```bash
demucs -n htdemucs_ft --two-stems vocals --shifts 10 --overlap 0.25 \
    --flac -o karaoke song.wav
# backing = karaoke/htdemucs_ft/song/no_vocals.flac
```

Post-process the backing track:

```bash
ffmpeg -i no_vocals.flac -af "highpass=f=35,loudnorm=I=-14:TP=-1:LRA=7" \
    karaoke_ready.flac
```

### Vocal isolation for ML / ASR training

```bash
demucs -n htdemucs_ft --two-stems vocals --shifts 5 -o vox_ds \
    --int24 *.wav
# keep only vocals.wav, feed into whisper/VAD.
```

Consider `media-whisper` next for transcription, or `media-sox` / `ffmpeg-denoise-restore` for a light denoise pass.

### Bass-only for DJ edit

```bash
demucs -n htdemucs --flac song.wav
cp separated/htdemucs/song/bass.flac dj/bass.flac
```

Optional: sidechain or layer under a new beat in the DAW.

### Drums for sampling

```bash
demucs -n htdemucs_ft --shifts 10 --flac drumheavy.wav
# separated/htdemucs_ft/drumheavy/drums.flac → slice in your sampler
```

Slice + retrigger in a sampler; Demucs drums are generally the cleanest stem.

### Remix prep (6-stem)

```bash
demucs -n htdemucs_6s --flac --int24 -o remix song.wav
# Import vocals/drums/bass/guitar/piano/other into DAW tracks.
```

Expect guitar/piano bleed; treat them as starting points, not finished stems.

### Fast CPU batch (Spleeter)

```bash
for f in *.mp3; do
    spleeter separate -p spleeter:2stems -o out "$f"
done
```

Good for quick-and-dirty batch karaoke where Demucs quality isn't required.

### Low-VRAM GPU (6 GB)

```bash
demucs -n htdemucs --segment 7 --overlap 0.25 song.wav
```

Drop to `mdx_q` or CPU if OOM persists.

## 7. Related skills

- `media-sox` / `ffmpeg-audio-filter` — post-process stems (denoise, EQ, loudness).
- `media-ffmpeg-normalize` — EBU R128 on finished stems.
- `media-whisper` — transcribe isolated vocals.
- `ffmpeg-audio-spatial` — spatial/binaural mixes from stems.
- `media-moviepy` / `ffmpeg-cut-concat` — reassemble stems with video.
