---
name: ffmpeg-filter
description: >
  Apply any ffmpeg video or audio filter via -vf/-af/-filter_complex. Use when the user asks to resize, crop, rotate, flip, pad, scale, deinterlace, overlay a watermark or logo, stack videos side-by-side, picture-in-picture, add text/captions/drawtext/timecode, change fps, color correct (curves, eq, hue), sharpen, blur, denoise, fade, zoompan; normalize loudness (EBU R128, loudnorm), boost/reduce volume, EQ, resample, change speed/tempo (atempo), trim silence, mix or merge audio tracks, remap channels, downmix 5.1 to stereo, sidechain duck; add echo, chorus, flanger, phaser, tremolo, vibrato, crystalizer, de-click vinyl, de-clip, soft-clip, true-peak limit, enhance dialogue, host LADSPA/LV2 plugins, frequency-shift; create binaural HRTF headphone audio, sofalizer, upmix mono/stereo to 5.1/7.1, widen stereo, crossfeed, earwax, split or join channels.
argument-hint: "[operation] [input]"
---

# Ffmpeg Filter

**Context:** $ARGUMENTS

Unified front door for all ffmpeg filtering — video transforms, audio mastering, creative/restoration FX, and spatial/binaural audio. Each technique below has a self-contained reference with full recipes, gotchas, examples, and troubleshooting. Always invoke the `ffmpeg-docs` skill before recommending an unfamiliar filter or flag — it is the anti-hallucination guardrail.

## When to use

- **Video filtering** — resize, crop, pad, rotate/flip, deinterlace, overlay/watermark, stack, picture-in-picture, drawtext/timecode, fps change, color correction, sharpen, blur, fade, zoompan.
- **Audio filtering (core)** — loudness normalize (EBU R128 / loudnorm 2-pass), volume, EQ, resample, speed/tempo (atempo), trim silence, mix (amix) / merge (amerge), channel remap (pan), 5.1→stereo downmix, sidechain ducking.
- **Audio FX (creative + restoration)** — echo, chorus, flanger, phaser, tremolo, vibrato, crystalizer, de-click/de-clip vinyl, soft-clip, psychoacoustic true-peak limit, dialogue enhance, dynamic EQ, frequency shift, spectral (afftfilt), LADSPA/LV2 plugin hosting.
- **Spatial audio** — binaural HRTF headphone downmix (headphone / sofalizer), stereo→5.1/7.1 upmix, stereo widen, crossfeed, earwax, channel split/join/remap.

## Techniques

- Read `references/video-filter.md` when the task is any **video** filter operation: scale/crop/pad/rotate, overlay/watermark, hstack/vstack, drawtext, deinterlace, color/eq, fps, `-vf` vs `-filter_complex`.
- Read `references/audio-filter.md` when the task is **core audio**: loudness normalization, volume, EQ, sample-rate/tempo change, silence trim, amix/amerge, pan/channel remap, downmix, or sidechain ducking.
- Read `references/audio-fx.md` when the task is **creative or restoration audio FX**: modulation (chorus/flanger/phaser/tremolo/vibrato), echo, speechnorm/dialoguenhance, dynamic EQ, crystalizer, soft-clip, apsyclip true-peak limit, de-click/de-clip, frequency shift, spectral, or LADSPA/LV2 plugins.
- Read `references/audio-spatial.md` when the task is **spatial / binaural** audio: HRTF headphone downmix, sofalizer + SOFA, surround upmix, stereowiden/extrastereo/stereotools, crossfeed/earwax, channelsplit/channelmap/join.

Each technique reference also links to a deep option-table file:
`references/video-filter-filters.md`, `references/audio-filter-filters.md`, `references/audio-fx-filters.md`, `references/audio-spatial-filters.md`.

## Gotchas

- **Even dimensions for video.** Most encoders demand even width *and* height. Use `scale=-2:720`, not `scale=-1:720`; `-2` preserves aspect AND snaps to a multiple of 2. `libx264` with YUV 4:2:0 hard-fails on odd sizes.
- **`-filter_complex` disables default stream selection.** You *must* `-map` every output label you want muxed (`-map "[v]" -map 0:a?`). The moment you need `[1:v]` or a second input, switch from `-vf`/`-af` to `-filter_complex`.
- **overlay silently drops alpha.** Precede `overlay` with `format=yuva420p` on the overlay input or transparency disappears: `[1:v]format=yuva420p,scale=...[wm]`.
- **`loudnorm` single-pass is dynamic, not linear** — it pumps. For masters run 2-pass: measure (`print_format=json`), then apply with all `measured_*` values + `linear=true`. Miss one `measured_*` and it falls back to dynamic silently.
- **`amix` defaults bite twice.** `normalize=1` scales output by 1/N (almost always wrong → set `normalize=0`), and mismatched sample rate or channel layout silently corrupts the mix → insert `aresample=48000` and `aformat=channel_layouts=stereo` per input. `amix` sums; `amerge` interleaves — never confuse them.
- **`atempo` is capped 0.5–100 per instance** and preserves pitch; chain `atempo=0.5,atempo=0.5` for 0.25x. `asetrate` alone changes pitch (tape effect).
- **`headphone` ClockWise channel order is mandatory** and `apsyclip` is the recommended broadcast true-peak limiter. 5.1 = `FL|FR|FC|LFE|BL|BR`, 7.1 = `FL|FR|FC|LFE|BL|BR|SL|SR`; wrong order scrambles the binaural image while still "sounding like audio."
- **Build-flag-gated filters fail with "No such filter."** `sofalizer` needs `--enable-libmysofa`; `ladspa`/`lv2` need `--enable-ladspa`/`--enable-lv2`; `rubberband` needs `--enable-librubberband` (most Homebrew/distro builds lack it). Verify with `ffmpeg -filters | grep <name>` before promising the recipe.

## Scripts

- **`scripts/vfilter.py`** — video filter preset runner (scale-720p, letterbox, watermark, deinterlace, drawtext-timecode, hstack, vstack, 2x-speed) plus `--custom --filter-string`. `--dry-run`/`--verbose`.
- **`scripts/afilter.py`** — core audio presets (loudnorm yt/podcast/ebu with `--two-pass` measure→apply, peak normalize, 2-input mix, speed, mono downmix, denoise).
- **`scripts/afx.py`** — creative/restoration FX subcommands (echo, declick, limit, modulation, etc.).
- **`scripts/spatial.py`** — spatial subcommands (detect, binaural, upmix, widen, split, remap, join).

All scripts are stdlib-only, print the exact ffmpeg command, and support `--dry-run` and `--verbose`. Invoke via `uv run ${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-filter/scripts/<file>.py ...`.
