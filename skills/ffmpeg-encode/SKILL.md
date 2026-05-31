---
name: ffmpeg-encode
description: >
  Use when the user asks to convert a video, change codec, re-encode, transcode, reduce file size with CRF, target a bitrate, do 2-pass encoding, change container, or make a file web/mobile/social-media compatible (H.264, HEVC, AV1, VP9, ProRes, AAC, Opus; MP4, MKV, WebM, MOV). Also when encoding on GPU — NVENC/NVDEC/CUDA, Quick Sync (QSV), VA-API, VideoToolbox on Mac, AMD AMF, Vulkan, hwupload/hwdownload zero-copy pipelines, or to accelerate/speed up transcoding. Also for bitstream filters (-bsf) to fix MP4-to-TS mux errors, convert H.264/HEVC between MP4 and Annex-B, fix AAC ADTS to ASC, repair a container, change PTS/DTS without re-encode, or extract SPS/PPS extradata. Also to preview/play back a file with ffplay, test a -vf/-af filter live, debug A/V sync, view loudness/waveform/spectrum/vectorscope, or scrub frame-by-frame for QA.
argument-hint: "[input] [target]"
---

# Ffmpeg Encode

**Context:** $ARGUMENTS

Encode, accelerate, remux, and preview with ffmpeg/ffplay. Always invoke `ffmpeg-docs` before recommending a flag or filter — it is the anti-hallucination guardrail.

## When to use

- Convert / re-encode / transcode between codecs and containers; shrink to a CRF or size budget; 2-pass; change container; make web/mobile/social-compatible.
- Encode on a GPU (NVENC, QSV, VA-API, VideoToolbox, AMF, Vulkan); zero-copy GPU filter pipelines; speed up bulk or real-time transcodes.
- Remux MP4 ↔ TS/HLS/FLV with `-c copy`; fix `Malformed AAC bitstream` / `not in Annex-B format`; rewrite level/VUI/color tags or PTS/DTS without re-encoding; extract SPS/PPS.
- Preview a clip, test a `-vf`/`-af` chain live, debug A/V sync, inspect loudness/waveform/spectrum/vectorscope, scrub frame-by-frame for QA.

For trimming/joining use `ffmpeg-cut-concat`; for filters/scaling use `ffmpeg-video-filter`/`ffmpeg-audio-filter`; for inspection only use `ffmpeg-probe`.

## Techniques

- Read `references/transcode.md` when choosing codec/container, rate control (CRF vs bitrate vs 2-pass), per-encoder presets/profiles, or building a software encode (libx264/libx265/libsvtav1/libvpx-vp9/ProRes/AAC/Opus). Deep encoder option tables live in `references/codecs.md`.
- Read `references/hwaccel.md` when encoding on a GPU — detecting available accel, picking NVENC/QSV/VA-API/VideoToolbox/AMF, building end-to-end GPU pipelines, and the hwupload/hwdownload bridge rules. Encoder option ladders live in `references/pipelines.md`.
- Read `references/bitstream.md` when applying `-bsf` to remux without re-encode, fix mux errors, rewrite headers/timestamps, or do NAL-unit surgery. Full bsf/NAL/`setts`/`*_metadata` catalog lives in `references/filters.md`.
- Read `references/playback.md` when previewing with ffplay, live-testing a filter graph, debugging A/V sync, or visualizing audio. Full keyboard table, flags, and lavfi catalog live in `references/commands.md`.

## Gotchas

- **`-pix_fmt yuv420p` is required** for broad playback (browsers, iOS, most TVs). ProRes/RGB sources land on 4:4:4/4:2:2 → green/purple tint without it. Use `yuv420p10le` for 10-bit HEVC/AV1.
- **`-movflags +faststart` is MP4/MOV only** — moves the moov atom to the front so web players start instantly. No-op on MKV/WebM.
- **CRF values are NOT comparable across codecs** (x264 23 ≠ x265 23 ≠ av1 23), and **hardware encoders are not comparable to libx264 CRF** — NVENC/QSV produce ~15–30% larger files at equal quality; raise bitrate or lower `-cq`/`-global_quality`.
- **HEVC in MP4 needs `-tag:v hvc1`** (software and VideoToolbox) or Apple QuickTime/Safari/iOS won't play it; default `hev1` is rejected.
- **Mixing CPU filters with GPU frames needs `hwdownload,format=nv12`** (and `,hwupload` back); on VA-API/QSV the `format=` before `hwupload` is NOT optional, else `Impossible to convert between the formats`. 10-bit NVENC HEVC needs `-pix_fmt p010le`, not `yuv420p10le`.
- **`-bsf` only fires with `-c copy`** — any re-encoder rewrites extradata and silently ignores it. **TS AAC → MP4 is NOT auto-handled**: pass `-bsf:a aac_adtstoasc` explicitly. Chain bsf with commas inside one `-bsf:v`; framing first, then extradata, then metadata.
- **`setts` expressions run in packet timebase, not seconds** — add 2s with `ts=PTS+2/TB`. NVENC/QSV often drop source color tags — set `-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709` (or `bt2020nc` for HDR) explicitly.
- **ffplay is a DEBUG player, not for shipping.** SDL2 required — headless SSH fails with `Could not initialize SDL`; use `-nodisp` for audio-only. `-f lavfi` graphs MUST end in labeled outputs (`[out0]` video + `[out1]` audio).

## Scripts

- `scripts/transcode.py` — preset-driven software transcode runner (`web-mp4`, `hevc-mkv`, `web-webm`, `av1-mp4`, `prores`, `archive`).
- `scripts/hwaccel.py` — `detect` available HW accel; `transcode --accel auto` builds a correct end-to-end GPU pipeline.
- `scripts/bsf.py` — subcommand bitstream runner (`mp4-to-ts`, `ts-to-mp4`, `fix-packed-bframes`, `level`, `strip-sei`, `zero-ts`, `trace`); auto-detects H.264 vs HEVC.
- `scripts/play.py` — ffplay wrapper (`preview`, `filter-test`, `waveform`, `spectrum`, `vectorscope`, `loudness-meter`, `sync`); downgrades to `-nodisp` when no display.

All helpers support `--dry-run` and `--verbose`.
