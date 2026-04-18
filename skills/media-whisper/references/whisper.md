# Whisper Reference

Load this when you need model-sizing data, a backend comparison, SRT/VTT/JSON
format detail, pre-processing recipes, language codes, or handoff notes for
diarization / real-time streaming. The main SKILL.md stays focused on the
happy path — this file is the look-up table.

## Model size table (OpenAI whisper family)

| Model         | Params | GGML FP16 size | RAM (approx) | Relative speed | WER (English, clean) |
| ------------- | ------ | -------------- | ------------ | -------------- | -------------------- |
| `tiny`        | 39M    | 75 MB          | ~0.4 GB      | 32×            | high                 |
| `tiny.en`     | 39M    | 75 MB          | ~0.4 GB      | 32×            | high                 |
| `base`        | 74M    | 142 MB         | ~0.5 GB      | 16×            | med-high             |
| `base.en`     | 74M    | 142 MB         | ~0.5 GB      | 16×            | med (better than base) |
| `small`       | 244M   | 466 MB         | ~1.0 GB      | 6×             | med                  |
| `small.en`    | 244M   | 466 MB         | ~1.0 GB      | 6×             | low-med (good for EN pods) |
| `medium`      | 769M   | 1.5 GB         | ~2.5 GB      | 2×             | low                  |
| `medium.en`   | 769M   | 1.5 GB         | ~2.5 GB      | 2×             | low (solid EN)       |
| `large-v2`    | 1.5B   | 2.9 GB         | ~4.5 GB      | 1×             | very low             |
| `large-v3`    | 1.5B   | 2.9 GB / 1.5 GB FP16 | ~4.5 GB | 1×        | best available (multi)|
| `large-v3-turbo` | 809M | 1.5 GB         | ~2.5 GB      | 4×             | near large-v3, 4× faster |
| `large-v3-q5_0` | 1.5B | 1.1 GB          | ~2.0 GB      | ~1×            | near large-v3 (quantized) |

"Relative speed" is whisper.cpp on a single CPU core versus `large-v3` = 1×.
`.en` suffix = English-only (fewer tokens, faster, more accurate for English).
Multilingual models can translate (source → English) but cannot go between
two non-English languages.

### Quantization variants (whisper.cpp GGML)

| Suffix  | Bits per weight | Size vs FP16 | Quality loss |
| ------- | --------------- | ------------ | ------------ |
| `f16`   | 16 (default)    | 100%         | baseline     |
| `q8_0`  | 8               | ~53%         | tiny         |
| `q5_1`  | 5.5             | ~40%         | small        |
| `q5_0`  | 5               | ~38%         | small-med    |
| `q4_1`  | 4.5             | ~33%         | medium       |
| `q4_0`  | 4               | ~30%         | medium (not recommended) |

Rule of thumb: `q5_0` of `large-v3` is the best quality/RAM tradeoff on
Apple Silicon. Go `q4_*` only under severe RAM pressure.

## Backend comparison

| Capability                    | whisper.cpp            | faster-whisper          | OpenAI API             |
| ----------------------------- | ---------------------- | ----------------------- | ---------------------- |
| Install                       | `brew install whisper-cpp` / `make` | `pip install faster-whisper` | HTTP, account |
| Runtime                       | C++ binary             | Python (CTranslate2)    | Remote                 |
| Model format                  | GGML (.bin)            | CTranslate2 (downloads auto) | Server-side     |
| CPU speed                     | ok                     | **~4× faster** (int8)   | n/a                    |
| Apple Silicon (Metal)         | **yes**                | no                      | n/a                    |
| NVIDIA CUDA                   | yes                    | yes                     | n/a                    |
| Output: SRT / VTT             | yes (`-osrt -ovtt`)    | build yourself          | yes                    |
| Output: word timestamps       | `.wts` TSV (`-owts`)   | structured `.words`     | `response_format=verbose_json` |
| VAD (silence filter)          | experimental           | **built-in** (`vad_filter=True`) | server-side    |
| Diarization hint              | tinydiarize (`-tdrz`)  | no                      | no                     |
| Privacy (local)               | yes                    | yes                     | no                     |
| Cost                          | free                   | free                    | per minute             |
| Best for                      | shell pipelines, Mac   | Python pipelines, long files, word-level | zero-ops, best model always |

## Compute-type tradeoffs (faster-whisper)

| `compute_type`   | Device   | Speed | Quality | Notes                                     |
| ---------------- | -------- | ----- | ------- | ----------------------------------------- |
| `int8`           | CPU      | fast  | slight loss | Default CPU; ~4× PyTorch, tiny quality dip |
| `int8_float16`   | GPU      | fast  | good    | Weights int8, activations fp16            |
| `int8_float32`   | GPU/CPU  | med   | good    | Activations fp32 if precision matters     |
| `float16`        | GPU only | med   | best    | Needs CUDA; full fp16                     |
| `float32`        | any      | slow  | ref     | Reference precision                       |

## Output formats

### SRT example

```
1
00:00:00,000 --> 00:00:02,480
Welcome to the podcast.

2
00:00:02,480 --> 00:00:05,960
Today we are talking about Rust.
```

Timecode is `HH:MM:SS,mmm` (comma, not dot). One blank line between cues.

### VTT example

```
WEBVTT

00:00:00.000 --> 00:00:02.480
Welcome to the podcast.

00:00:02.480 --> 00:00:05.960
Today we are talking about Rust.
```

Timecode is `HH:MM:SS.mmm` (dot). Starts with literal `WEBVTT` line.

### JSON (faster-whisper `word_timestamps=True`)

```json
[
  {"start": 0.00, "end": 0.42, "word": "Welcome", "probability": 0.98},
  {"start": 0.42, "end": 0.63, "word": " to",      "probability": 0.99},
  {"start": 0.63, "end": 0.95, "word": " the",     "probability": 0.99},
  {"start": 0.95, "end": 1.40, "word": " podcast.","probability": 0.95}
]
```

Leading-space word tokens are intentional — they are the whisper BPE token
boundaries. Join with `"".join(w["word"] for w in words)` to rebuild text.

### whisper.cpp `.wts` (karaoke)

The `-owts` flag emits a bash-playable script of `ffmpeg drawtext` calls for
a karaoke-style burn-in. Not structured data. For JSON, use faster-whisper.

## GGML model downloads

Helper script is bundled with whisper.cpp:

```
bash /opt/homebrew/share/whisper.cpp/models/download-ggml-model.sh <model>
```

Valid `<model>` names: `tiny`, `tiny.en`, `base`, `base.en`, `small`,
`small.en`, `small.en-tdrz`, `medium`, `medium.en`, `large-v1`, `large-v2`,
`large-v3`, `large-v3-turbo`, plus quantized variants like `large-v3-q5_0`.
They are hosted on Hugging Face under the `ggerganov/whisper.cpp` repo.
Downloaded files land in the same `models/` directory as the script.

## Pre-processing recipes (ffmpeg)

Better input audio → better transcript. Run before passing to whisper.

### Loudness normalization (EBU R128)

```
ffmpeg -i in.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 16000 -ac 1 \
  -c:a pcm_s16le pre.wav
```

### Broadband denoise (podcast / phone audio)

```
ffmpeg -i in.mp3 -af "afftdn=nr=12:nf=-30,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -ar 16000 -ac 1 -c:a pcm_s16le pre.wav
```

### Silence trim (reduces hallucinations, speeds up ASR)

```
ffmpeg -i in.mp3 -af \
  "silenceremove=start_periods=1:start_duration=0.5:start_threshold=-40dB:\
detection=peak,aformat=dblp,areverse,\
silenceremove=start_periods=1:start_duration=0.5:start_threshold=-40dB:\
detection=peak,aformat=dblp,areverse" \
  -ar 16000 -ac 1 -c:a pcm_s16le pre.wav
```

(For batch / higher-level control, use `ffmpeg-audio-filter` skill. For
Spleeter-free vocal isolation on music-heavy podcasts, see `media-demucs`.)

## Language codes (ISO 639-1 subset supported by whisper)

Common ones — the full list is ~100 languages.

| Code | Language    | Code | Language      | Code | Language     |
| ---- | ----------- | ---- | ------------- | ---- | ------------ |
| en   | English     | es   | Spanish       | fr   | French       |
| de   | German      | it   | Italian       | pt   | Portuguese   |
| nl   | Dutch       | sv   | Swedish       | no   | Norwegian    |
| da   | Danish      | fi   | Finnish       | pl   | Polish       |
| ru   | Russian     | uk   | Ukrainian     | cs   | Czech        |
| tr   | Turkish     | ar   | Arabic        | he   | Hebrew       |
| hi   | Hindi       | bn   | Bengali       | ta   | Tamil        |
| zh   | Chinese     | ja   | Japanese      | ko   | Korean       |
| id   | Indonesian  | ms   | Malay         | vi   | Vietnamese   |
| th   | Thai        | tl   | Tagalog       | sw   | Swahili      |
| auto | auto-detect (whisper.cpp `-l auto`; faster-whisper `language=None`)  |

Note: whisper ships specific tokenizers per language. Code mismatch ≈ garbage
output. Prefer explicit `--lang` over `auto` on mixed / music-heavy content.

## Diarization handoff (who spoke when)

Whisper alone cannot label speakers. Two options:

### 1. pyannote-audio + whisper merge

```
pip install pyannote.audio
# Requires HF token + accepting the model's EULA on Hugging Face.
```

```python
from pyannote.audio import Pipeline
pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",
                                use_auth_token=HF_TOKEN)
diar = pipe("audio.wav")
# diar: Annotation of (start, end, speaker_label)
```

Then align with your whisper segments: for each whisper segment, pick the
speaker whose diarization interval has max overlap. Prepend `"[SPEAKER_00] "`
to the SRT cue text.

### 2. whisper.cpp tinydiarize

`-tdrz` with the `ggml-small.en-tdrz.bin` model emits `[_SOLM_]`
(speaker-change) markers inline in the transcript. Useful as a quick hint;
not a full speaker-ID solution. Two speakers only, English-only.

## Real-time streaming

### whisper.cpp stream mode

```
whisper-cpp --stream -m ggml-base.en.bin -t 8 --step 500 --length 5000
```

Uses SDL audio capture; prints partial transcripts with rolling window.
Flags:
- `--step N` — partial decode every N ms (500 is balanced).
- `--length N` — total audio window kept (5000 ms default).
- `--keep N` — ms of overlap between windows (default 200).
- `--vad-thold` — voice-activity threshold, 0.6 default.

Latency: ~700 ms end-to-end with `base.en` on M1. Higher models = higher
latency; use `tiny.en` or `base.en` for live.

### Faster alternatives for real-time

- `whisper.cpp server` (HTTP endpoint, WebSocket streaming variants).
- `whisper_streaming` (Python, VAD + local agreement; based on faster-whisper).
- NVIDIA NeMo Canary / Parakeet (non-whisper, best-in-class RTF on GPU).

## Post-processing: punctuation, spelling, speaker labels

- `deepmultilingualpunctuation` (pip): adds `. , ? !` to unpunctuated output
  from tiny/base models.
- `punctuators` (pip): newer transformer-based punctuation + truecasing.
- Custom-vocab biasing: whisper.cpp `--prompt "Acme, kubectl, CTO"` primes
  the decoder toward domain-specific tokens. Keep prompt <224 tokens.
- Spell-fix proper nouns post-hoc with a simple regex list — whisper
  consistently mis-spells the same names, fix them in batch.

## Gotchas

- `initial_prompt` / `--prompt` influences the first window only; re-passing
  context across 30 s chunks requires custom decoding loops.
- faster-whisper's VAD uses Silero VAD internally; tune
  `min_silence_duration_ms` (default 2000) down for fast-cut content.
- Word-level timestamps **cost ~20% more time** to generate — skip them if
  you only need cue-level SRT.
- `large-v3` was trained on more non-English data than `large-v2` and is
  slightly worse than v2 on purely English clean audio in some benchmarks.
  For English podcasts, `medium.en` often ties `large-v3` at a fraction of
  the cost. Benchmark on your own data.
- Numerical content ("one zero zero") is frequently transcribed in words,
  not digits. Post-process with `word2number` or regex if you need digits.
