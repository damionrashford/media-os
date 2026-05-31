---
name: ffmpeg-edit
description: >
  Use when the user asks to trim a video, cut a clip, extract a segment by timestamps, remove a section, split into parts, join or merge videos, concatenate files, build a segmented HLS-style playlist, grab a thumbnail, extract frames, take a screenshot at a timestamp, create a contact sheet or sprite sheet, convert video to images or PNGs or JPGs, convert an image sequence to video, make a GIF from a video, slow down video, speed up, time-lapse, ramp speed up or down, do a speed ramp, reverse a clip, freeze the last frame, hold on a frame, loop a video, do frame-blending slow-motion, record the screen, capture desktop, record webcam, record microphone, screencast, grab a region of the screen, capture system audio, or list input devices.
argument-hint: "[action] [input]"
---

# Ffmpeg Edit

Consolidated FFmpeg editing skill covering cut/concat, frames/images, speed/time, and capture. Always invoke `ffmpeg-docs` first to confirm any flag or filter before recommending it.

## When to use

- Trim, cut, split, segment, or concatenate clips by timestamp or codec.
- Extract frames, screenshots, contact sheets, sprite sheets, or build a video from an image sequence; make high-quality GIFs.
- Change playback speed, slow-mo (PTS or motion-interpolated), reverse, freeze a frame, loop, time-lapse, or ramp speed.
- Record screen, webcam, microphone, or system audio; list capture devices.

## Techniques

- Read `references/cut-concat.md` when the user wants to trim a clip, extract a segment by timestamps, remove a section, split into N pieces or HLS segments, or join/merge/concatenate files (stream copy vs re-encode, concat demuxer vs concat filter).
- Read `references/frames-images.md` when the user wants a thumbnail or screenshot at a timestamp, periodic frame dumps, a contact sheet or scrubber sprite sheet, image-sequence ⇄ video conversion, or a high-quality GIF (palettegen/paletteuse).
- Read `references/speed-time.md` when the user wants to speed up or slow down, smooth motion-interpolated slow-mo, reverse, freeze first/last/mid frame, loop, time-lapse, or a variable speed ramp (setpts/atempo/minterpolate/tpad).
- Read `references/capture.md` when the user wants to record the screen, desktop, webcam, mic, or system audio, grab a region, or list input devices (avfoundation/gdigrab/dshow/x11grab/kmsgrab/v4l2).
- Read `references/patterns.md` for concat `list.txt` escaping, two-pass `-ss`, `-copyts` muxing-accurate cuts, and keyframe inspection.
- Read `references/recipes.md` for the 30+ frame/GIF recipe gallery, JPEG/PNG quality scales, image2 demuxer options, and HLS sprite geometry.
- Read `references/filters.md` for full setpts expressions, minterpolate modes, atempo vs asetrate, and the speed recipe gallery.
- Read `references/devices.md` for per-platform capture option tables, virtual-audio devices, TCC/permission reset, crash-safe recording, and bitrate/FPS guidance.

## Gotchas

- **Concat demuxer is silent about mismatches.** Inputs MUST share codec, resolution, SAR, pixel format, fps, sample rate, and channel layout, or playback breaks (frozen video, desync audio) with zero warnings. Probe and diff first; otherwise use the concat filter with re-encode. `-safe 0` is required for absolute paths or `..`.
- **`-to` is absolute, `-t` is duration.** `-ss 60 -to 90` = 30s clip; `-ss 60 -t 90` = 90s clip. With `-c copy`, cuts snap to the nearest prior keyframe — add `-avoid_negative_ts make_zero` or re-encode for frame-accuracy.
- **`-ss` before `-i` is fast but keyframe-snapped; after `-i` is frame-accurate but slow.** Use input seek for thumbnails, output seek only when the exact frame matters.
- **GIF quality REQUIRES the two-pass palette workflow** (`palettegen` → `paletteuse=dither=bayer:bayer_scale=5`). A naked `ffmpeg -i in.mp4 out.gif` produces banded garbage. For image sequence → video, set `-framerate` BEFORE `-i` (input rate), not `-r` (output rate); zero-padding must match `%0Nd`.
- **Speed changes must touch BOTH streams or A/V drifts:** `setpts=K*PTS` pairs with `atempo=1/K`. `atempo` range is 0.5–100.0 per instance — chain stages (`atempo=0.5,atempo=0.5` for 0.25x). Use `asetrate` only when you WANT a pitch shift.
- **`reverse`/`areverse` and `minterpolate` are expensive.** Reverse buffers the whole stream in RAM (split long clips, reverse each, concat in reverse order); minterpolate runs ~1 fps at 1080p (trim/downscale first, append `,format=yuv420p`).
- **macOS capture needs Screen Recording AND Microphone permission** granted to the parent terminal/IDE (per binary path). avfoundation indices are independent per list (`"1:0"` = video 1, audio 0) and there is no native system-audio input — install BlackHole and `amix`.
- **Stop captures with `q`, never Ctrl+C on MP4** (no MOOV = unreadable file). Record MKV for anything over a minute, then remux with `-c copy`. `-pix_fmt yuv420p` is required for libx264 output to play in QuickTime/Safari/iOS.

## Scripts

- `scripts/cut.py` — `trim | segment | concat-copy | concat-filter`. Stream copy or `--accurate` re-encode.
- `scripts/frames.py` — `screenshot | every | sheet | sprite | gif | images-to-video`.
- `scripts/time.py` — `speed | reverse | freeze | loop | timelapse | ramp` (supports `--smooth minterpolate`).
- `scripts/capture.py` — `list-devices | screen | webcam | audio-only` (auto-detects platform).

All scripts are stdlib-only Python, non-interactive, and support `--dry-run` and `--verbose`. Invoke as `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py <subcommand> ...`.
