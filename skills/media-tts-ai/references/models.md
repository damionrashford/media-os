# TTS Model Comparison Matrix

All models below are **commercial-safe** (permissive open-source license). Non-commercial models (XTTS-v2, F5-TTS, paid Bark v2, MusicGen) are explicitly excluded.

## Speech synthesis (no cloning)

| Model       | License     | Params | Speed on CPU            | GPU req    | Languages                                 | Emotion         | Best for                                     |
| ----------- | ----------- | ------ | ----------------------- | ---------- | ----------------------------------------- | --------------- | -------------------------------------------- |
| Kokoro      | Apache 2.0  | 82M    | realtime (ONNX int8)    | optional   | en-us/en-gb/fr/ja/ko/zh/hi/it/pt-br       | neutral         | Default — best quality-for-size              |
| Piper       | MIT         | 3-30M  | 5-10x realtime          | none       | 70+ via voice packs                       | neutral         | Embedded / Raspberry Pi / latency-critical   |
| StyleTTS2   | MIT         | 200M   | ~realtime               | helpful    | en                                        | style transfer  | Kokoro-like with direct access to arch       |
| Bark        | MIT         | 1.2B   | 0.1x realtime           | required   | en + 12 others (speaker_0..9 per lang)    | strong (cues)   | [laughs] [sighs] [music] expressive output   |
| Orpheus     | Apache 2.0  | 3B     | 0.2x realtime           | required   | en                                        | strong          | Emotional Llama-3-based TTS, 2025 SOTA       |
| Parler-TTS  | Apache 2.0  | 880M   | 0.3x realtime           | required   | en                                        | prompt-controlled | Describe voice style in natural language   |

## Voice cloning

| Model       | License     | Params | Speed (GPU)       | CPU-capable? | Reference length | Emotion controls | Best for                                 |
| ----------- | ----------- | ------ | ----------------- | ------------ | ---------------- | ---------------- | ---------------------------------------- |
| OpenVoice v2 | MIT        | ~200M  | realtime          | yes (slow)   | 5-30s            | no (tone only)   | Cross-lingual tone-color transfer        |
| CosyVoice 2 | Apache 2.0  | 500M   | ~realtime         | yes (slow)   | 3-10s            | yes              | 2025 SOTA zero-shot cloning, multilingual |
| Chatterbox  | MIT         | ~500M  | ~realtime         | yes (slow)   | 5-15s            | yes (0.0-1.0)    | Zero-shot + emotion intensity knob       |

## Sample rate output

- Kokoro: 24 kHz
- Piper: 16 or 22.05 kHz (voice-dependent — `-low`/`-medium`/`-high` suffix)
- Bark: 24 kHz
- CosyVoice 2: 22.05 kHz
- OpenVoice v2: 24 kHz
- Chatterbox: 24 kHz
- Orpheus: 24 kHz
- Parler-TTS: 44.1 kHz

Always resample to 48 kHz in ffmpeg if mixing stems in a DAW.

## Memory footprint

| Model       | RAM (CPU inference) | VRAM (GPU inference) |
| ----------- | ------------------- | --------------------- |
| Kokoro      | ~500 MB             | ~1 GB                 |
| Piper       | ~100-300 MB         | n/a                   |
| StyleTTS2   | ~2 GB               | ~3 GB                 |
| Bark        | ~8 GB (default)     | ~12 GB; 8 GB with SUNO_USE_SMALL_MODELS=1 |
| Orpheus     | ~16 GB              | ~24 GB                |
| Parler-TTS  | ~8 GB               | ~6 GB                 |
| OpenVoice v2 | ~4 GB              | ~4 GB                 |
| CosyVoice 2 | ~8 GB               | ~8 GB                 |
| Chatterbox  | ~6 GB               | ~6 GB                 |

## Decision tree

1. **No cloning, best default local quality, CPU-only?** Kokoro
2. **No cloning, lowest-latency embedded?** Piper
3. **No cloning, need [laughs]/[sighs]/non-verbals?** Bark
4. **Cloning, best 2025 quality?** CosyVoice 2
5. **Cloning, cross-lingual (source lang != target lang)?** OpenVoice v2
6. **Cloning, want emotion intensity knob?** Chatterbox
7. **Want to describe the voice in natural language?** Parler-TTS
