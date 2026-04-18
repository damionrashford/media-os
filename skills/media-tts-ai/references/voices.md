# TTS Voice Catalog

## Kokoro preset voices (~50 voices)

Naming convention: `<lang><gender>_<name>`:
- Lang: `a` (American English), `b` (British English), `j` (Japanese), `z` (Mandarin), `f` (French), `i` (Italian), `p` (Portuguese), `h` (Hindi)
- Gender: `f` (female), `m` (male)

### American English — female (`af_*`)
af_bella, af_nicole, af_sarah, af_sky, af_heart, af_alloy, af_aoede, af_jessica, af_kore, af_nova, af_river

### American English — male (`am_*`)
am_adam, am_michael, am_echo, am_eric, am_fenrir, am_liam, am_onyx, am_puck, am_santa

### British English — female (`bf_*`) / male (`bm_*`)
bf_alice, bf_emma, bf_isabella, bf_lily, bm_daniel, bm_fable, bm_george, bm_lewis

### Japanese (`jf_*` / `jm_*`)
jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro, jm_kumo

### Mandarin Chinese (`zf_*` / `zm_*`)
zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi, zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang

### French / Italian / Portuguese / Hindi
ff_siwis, if_sara, im_nicola, pf_dora, pm_alex, pm_santa, hf_alpha, hf_beta, hm_omega, hm_psi

### Language codes for the `--lang` flag
- `en-us` — American English (default)
- `en-gb` — British English
- `fr-fr` — French
- `ja` — Japanese
- `ko` — Korean
- `zh` — Mandarin Chinese
- `hi` — Hindi
- `it` — Italian
- `pt-br` — Brazilian Portuguese

## Piper voices

Piper uses ONNX files, one per voice. Download from https://huggingface.co/rhasspy/piper-voices.

Naming: `<locale>-<name>-<quality>.onnx`
- Quality suffixes: `x_low`, `low`, `medium`, `high` (higher = bigger + slower + better)

Examples:
- `en_US-amy-low.onnx` (tiny, 6 MB)
- `en_US-amy-medium.onnx` (30 MB, good default)
- `en_US-lessac-high.onnx` (high quality)
- `en_US-libritts_r-medium.onnx` (multi-speaker)
- `en_GB-alan-medium.onnx`
- `en_GB-jenny_dioco-medium.onnx`
- `de_DE-thorsten-high.onnx`
- `fr_FR-siwis-medium.onnx`
- `es_ES-davefx-medium.onnx`
- `it_IT-riccardo-x_low.onnx`
- `nl_NL-mls-medium.onnx`

## Bark speaker prompts

Bark accepts a `history_prompt` string referring to a built-in speaker bank.

### English
`v2/en_speaker_0` through `v2/en_speaker_9`

### Other languages (3 speakers each)
`v2/de_speaker_{0..2}` (German)
`v2/es_speaker_{0..2}` (Spanish)
`v2/fr_speaker_{0..2}` (French)
`v2/hi_speaker_{0..2}` (Hindi)
`v2/it_speaker_{0..2}` (Italian)
`v2/ja_speaker_{0..2}` (Japanese)
`v2/ko_speaker_{0..2}` (Korean)
`v2/pl_speaker_{0..2}` (Polish)
`v2/pt_speaker_{0..2}` (Portuguese)
`v2/ru_speaker_{0..2}` (Russian)
`v2/tr_speaker_{0..2}` (Turkish)
`v2/zh_speaker_{0..2}` (Mandarin)

### Non-verbal cues (bracketed tokens in text)
- `[laughs]`, `[laughter]`
- `[sighs]`, `[sigh]`
- `[gasps]`, `[gasp]`
- `[music]`
- `[clears throat]`
- `[singing]`
- `♪ la la la ♪` (attempt at sung output — unreliable)
- `—` (em-dash causes short pause)
- `...` (ellipsis causes hesitation)

## CosyVoice 2 built-in voices

CosyVoice 2 is primarily zero-shot (pass `--reference`), but has these named Chinese voices:
`中文女` (Chinese female), `中文男` (Chinese male), `日语女` (Japanese female), `英文女` (English female), `英文男` (English male), `韩语女` (Korean female)

## Parler-TTS prompt examples

Parler takes a natural-language style description:
- "A calm female voice with clear articulation at a steady pace."
- "An energetic male narrator with a deep voice and enthusiastic delivery."
- "A whispered confidential tone, very close-mic, intimate."
- "A British middle-aged man reading children's stories with warmth."
