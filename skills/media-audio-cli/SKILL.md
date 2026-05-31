---
name: media-audio-cli
description: >
  Use when the user asks to normalize audio loudness, apply EBU R128 / LUFS, batch-normalize a podcast or music library to a platform target (-23 broadcast, -16 Apple Podcasts, -14 YouTube/Spotify), use ffmpeg-normalize, set true peak or loudness range, do broadcast-compliant loudness at scale, or process audio with SoX: convert formats, resample, change bit depth or channels, trim, pad, fade, reverse, change speed/tempo/pitch, detect and remove silence, denoise with noise-profile + noise reduction, apply a SoX effects chain, compand or compress dynamics, generate synth tones or pink/white/brown noise, peak-normalize, or report signal stats (peak dBFS, RMS, DC offset, bit depth).
argument-hint: "[operation] [input]"
---

# Media Audio CLI

**Context:** $ARGUMENTS

Command-line audio processing for two complementary tools: **SoX** (surgical edit/convert/denoise/synth with precise chain + dither control) and **ffmpeg-normalize** (2-pass EBU R128 loudness normalization at scale).

## When to use

- Convert / resample / re-bit / re-channel audio, or run a precise SoX effects chain where order and dither matter.
- Trim, pad, fade, reverse; change tempo (keep pitch), pitch (keep tempo), or speed (both).
- Detect and strip silence; two-pass denoise via noise-profile + spectral subtraction.
- Compress dynamics (compand), peak-normalize, or report signal stats (peak/RMS/DC/bit-depth).
- Synthesize test tones, sweeps, or pink/white/brown noise for calibration.
- Batch EBU R128 / LUFS loudness normalization to a broadcast or streaming target, preserving non-audio streams.

## Techniques

- Read `references/sox.md` when the task is any SoX operation: format conversion, trim/pad/fade, speed/tempo/pitch, silence removal, denoise, compand, synth, peak-normalize, channel ops, or signal stats.
- Read `references/sox-catalog.md` when you need the full SoX effect catalog, file-option-vs-effect distinction, dither controls, noise-reduction best practices, synth waveforms, or the recipe book.
- Read `references/ffmpeg-normalize.md` when the task is EBU R128 / LUFS loudness normalization, picking a platform target, batch-normalizing a directory, or set-and-forget broadcast-compliant loudness.
- Read `references/normalize-catalog.md` when you need the full platform loudness target table, LUFS/dBFS/LRA concepts, raw-loudnorm-vs-wrapper comparison, or the normalization recipe book.

## Gotchas

- **SoX does NOT do EBU R128 loudness.** `sox --norm` is peak-only. For `-14/-16/-23 LUFS`, use ffmpeg-normalize.
- **SoX chain order is left-to-right** and matters: `gain -6 norm` ≠ `norm gain -6`. `-v` is a FILE option (pre-filename); `gain` is an effect (post-output-filename).
- **SoX `tempo 1.5` keeps pitch; `pitch 200` (cents) keeps tempo; `speed 1.5` changes BOTH** (varispeed).
- **SoX `noisered` amount is 0.0–1.0** — start at 0.21; above ~0.35 voice goes "underwater". Profile from pure noise at the same sample rate.
- **SoX dither is ON by default when reducing bit depth.** Disable with global `-D` before the output filename for intermediate files.
- **ffmpeg-normalize is 2-pass automatically** (no JSON round-trip); default target is **-23 LUFS broadcast** — too quiet for streaming, use `-t -14` or `-t -16`.
- **`-c:a aac` (or `pcm_s16le` for WAV) is REQUIRED for MP4 output** — the default `pcm_s16le` can't mux into MP4; video is `-c:v copy` by default.
- **ffmpeg-normalize batch normalizes each file INDEPENDENTLY** — no cross-file/album-gain awareness; for shared relative levels use a single manual 2-pass `loudnorm`. Never chain `volume=` after normalization.

## Scripts

- **`scripts/sox.py`** — argparse wrapper: check / info / convert / trim / tempo / pitch / fade / silence-trim / denoise / normalize / synth / concat / mix / stats. `--dry-run`, `--verbose`, stdlib-only.
- **`scripts/normalize.py`** — `check` / `normalize` / `preset` / `batch` subcommands wrapping `ffmpeg-normalize`. `--dry-run`, `--verbose`, stdlib-only.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/sox.py convert --input in.wav --output out.flac --rate 48000 --bits 16
uv run ${CLAUDE_SKILL_DIR}/scripts/normalize.py preset --input in.mp3 --output out.mp3 --platform apple-podcasts
```
