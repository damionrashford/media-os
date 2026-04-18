---
name: media-demucs
description: >
  AI audio source separation with Demucs and Spleeter: isolate vocals / drums / bass / other stems from mixed audio, karaoke track extraction, music remixing prep, Hybrid Transformer Demucs (htdemucs), 2-stem and 4-stem and 6-stem models, GPU-accelerated. Use when the user asks to separate vocals from a song, extract drums/bass/other stems, make a karaoke track, isolate stems with AI, remove music from speech, prep stems for remixing, or use Demucs.
argument-hint: "[input]"
---

# Media Demucs

**Context:** $ARGUMENTS

## Quick start

- **Karaoke (vocals out):** `demucs --two-stems vocals song.mp3` → Step 3
- **Full stems (vocals/drums/bass/other):** `demucs song.mp3` → Step 3
- **6-stem (+ guitar + piano):** `demucs -n htdemucs_6s song.mp3` → Step 3
- **Scripted one-shot:** `uv run scripts/stems.py split --input song.mp3 --outdir out` → Step 3

## When to use

- Producing a karaoke / instrumental track from a finished song
- Pulling vocals out for speech ML, dubbing, or sample-pack prep
- Isolating drums or bass stems for sampling / DJ re-edits
- Preparing stems for remixing in a DAW (Ableton, Logic, Reaper)
- Cleaning music out of a voice recording (e.g. interviews shot in a noisy venue)

## Step 1 — Install

Demucs (recommended, modern transformer):

```bash
pip install demucs
# or: pipx install demucs
```

Spleeter (older, faster on CPU, legacy):

```bash
pip install spleeter
```

Check what is available on this machine:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/stems.py check
```

First-time use downloads model weights (~200 MB–2 GB each) into `~/.cache/torch/hub/checkpoints/`.

## Step 2 — Pick a model

| Task | Model |
|------|-------|
| Best overall quality | `htdemucs_ft` (fine-tuned Hybrid Transformer) |
| Default good quality | `htdemucs` |
| Higher quality, slower, more VRAM | `mdx_extra` |
| CPU / low-VRAM fallback | `mdx_q` (quantized) |
| 6 stems (vocals/drums/bass/guitar/piano/other) | `htdemucs_6s` |
| Fast batch karaoke on CPU | Spleeter `2stems` |

See [`references/stems.md`](references/stems.md) for a full quality/speed/VRAM table.

## Step 3 — Separate

### Demucs — default 4-stem

```bash
demucs song.mp3
# → separated/htdemucs/song/{vocals,drums,bass,other}.wav
```

### Demucs — karaoke (2-stem)

```bash
demucs --two-stems vocals song.mp3
# → vocals.wav + no_vocals.wav
```

### Demucs — 6-stem

```bash
demucs -n htdemucs_6s song.mp3
# → vocals, drums, bass, guitar, piano, other
```

### Demucs — quality knobs

```bash
demucs -n htdemucs_ft --shifts 10 --overlap 0.25 song.mp3
```

- `--shifts N` averages N random time shifts (2× cost per shift, higher quality).
- `--overlap 0.25` controls overlap-add blending between chunks.
- `--segment S` shrinks chunk size for low-VRAM GPUs.

### Device / output

```bash
demucs --device cuda -o OUTDIR --flac song.mp3     # GPU + FLAC
demucs --device cpu song.mp3                       # force CPU
demucs --mp3 song.mp3                              # MP3 output
demucs --int24 song.mp3                            # 24-bit WAV
demucs *.mp3                                       # batch
```

### Spleeter

```bash
spleeter separate -p spleeter:2stems -o output in.mp3   # vocals / accompaniment
spleeter separate -p spleeter:4stems -o output in.mp3   # vocals / drums / bass / other
spleeter separate -p spleeter:5stems -o output in.mp3   # + piano
```

### Scripted helper

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/stems.py karaoke \
    --input song.mp3 --output-vocals vox.wav --output-backing inst.wav
```

Subcommands: `check`, `split`, `karaoke`, `vocals-only`, `backing-only`. All support `--dry-run` and `--verbose`.

## Step 4 — Post-process

- Light denoise on stems if a smaller model was used (aliasing is common). Try `sox stem.wav clean.wav noisered prof 0.2` or ffmpeg `afftdn`.
- Match LUFS across stems before DAW import (use `media-ffmpeg-normalize` or `loudnorm`).
- For karaoke delivery, lightly high-pass the backing at ~40 Hz to clean rumble after subtraction.
- Convert to FLAC or 24-bit for archival: `demucs --flac --int24 ...`.

## Gotchas

- Demucs is **more accurate** than Spleeter (modern transformer); prefer it unless you need batch speed on CPU.
- Models download on first use; cached in `~/.cache/torch/hub/checkpoints/`. Individual models are 200 MB–2 GB.
- `htdemucs_ft` is usually top quality but ~4× slower than `htdemucs` (it runs 4 fine-tuned sub-models and averages).
- `mdx_extra` needs ~4 GB VRAM. On OOM: switch to smaller model or add `--segment 7`.
- CPU inference works but is slow (10–30 min per 3–4 min song). `mdx_q` is the best CPU option.
- Spleeter only works under Python <3.9 in some versions; its GPU path needs `tensorflow-gpu`.
- Demucs was trained at 44.1 kHz. Different sample rates work but quality drops — **pre-resample** with ffmpeg/sox if the source isn't 44.1k.
- Stems are written as individual files matching input sample rate; default is 16-bit WAV. Use `--int24` or `--flac` for more bit depth.
- `--shifts 10` roughly 20× runtime vs default — reserve for final deliverables, not iteration.
- `--two-stems vocals` yields `vocals.wav` and `no_vocals.wav` (not `accompaniment.wav` — that's Spleeter naming).
- 6-stem (`htdemucs_6s`) guitar/piano separation is weaker than the 4-stem base; bleed is common.
- For **karaoke**: 2-stem + `--shifts 10` is the best quality/time trade.
- For **remixing**: 4- or 6-stem, then import into a DAW on separate tracks.
- Watch RAM: Demucs processes in chunks but still holds large tensors; close other GPU jobs first.

## Examples

### Karaoke track from a pop song

```bash
demucs --two-stems vocals --shifts 10 -n htdemucs_ft -o karaoke song.mp3
# use: karaoke/htdemucs_ft/song/no_vocals.wav
```

### All four stems for DAW remix

```bash
demucs -n htdemucs_ft --flac -o stems song.wav
# stems/htdemucs_ft/song/{vocals,drums,bass,other}.flac
```

### Batch a folder

```bash
demucs -n htdemucs --device cuda -o out input/*.mp3
```

### Bass-only for a DJ edit

```bash
demucs -n htdemucs song.mp3
# keep only separated/htdemucs/song/bass.wav
```

## Troubleshooting

### Error: `CUDA out of memory`

Cause: Model/chunk too large for GPU VRAM.
Solution: Add `--segment 7` (or lower), switch to `htdemucs` instead of `mdx_extra`, or `--device cpu`.

### Error: `No module named 'demucs'`

Cause: Not installed in the active env.
Solution: `pip install demucs` (or `pipx install demucs`). Confirm with `scripts/stems.py check`.

### Vocals bleed into instrumental (or vice versa)

Cause: Default model, low `--shifts`, or non-44.1 kHz input.
Solution: Use `-n htdemucs_ft --shifts 10`; pre-resample source to 44.1 kHz.

### Spleeter fails on Python 3.11+

Cause: Spleeter pins old TensorFlow.
Solution: Use Demucs, or create a Python 3.8/3.9 venv just for Spleeter.

### Model download stalls

Cause: Huggingface Hub / torch.hub mirror issue.
Solution: Retry; or pre-download weights and place them under `~/.cache/torch/hub/checkpoints/`.

## Reference docs

- Read [`references/stems.md`](references/stems.md) for model comparison, VRAM/quality/speed table, stem layouts per model, CLI flag reference, and a recipe book (karaoke, vocal isolation for ML, bass-only for DJ, drums-for-sampling).
