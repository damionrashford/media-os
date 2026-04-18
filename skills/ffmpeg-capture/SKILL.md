---
name: ffmpeg-capture
description: >
  Record from capture devices with ffmpeg: screen/desktop (avfoundation on macOS, gdigrab/dshow on Windows, x11grab/kmsgrab on Linux), webcam (avfoundation/dshow/v4l2), microphone, system audio, and list available devices. Use when the user asks to record the screen, capture desktop, record webcam, record microphone, screencast, grab a region of the screen, capture system audio, or list input devices.
argument-hint: "[source] [output]"
---

# Ffmpeg Capture

**Context:** $ARGUMENTS

## Quick start

- **Record the screen:** → Step 1 (list devices) → Step 2 (pick source) → Step 3 (run)
- **Record webcam + mic:** → Step 1 → Step 3 with `webcam` subcommand
- **Record a region:** → Step 3 with `--crop` (mac/linux) or `-offset_x/-offset_y/-video_size` (Windows gdigrab)
- **Record system audio (mac):** install BlackHole first → Step 2 (route via virtual device)
- **Just list devices:** `python3 scripts/capture.py list-devices`

## When to use

- User wants a screencast, demo recording, or desktop capture to a file.
- User wants to record webcam/microphone/system audio to disk.
- User wants to enumerate which cameras/mics/screens ffmpeg can see.
- User wants low-latency or crash-safe recording (MKV-first, remux to MP4 after).

Do NOT use for: streaming to RTMP/HLS (use `ffmpeg-streaming`), applying filters/effects (use `ffmpeg-video-filter`), or converting an existing file (use `ffmpeg-transcode`).

## Step 1 — Detect platform + list devices

Always list devices first. Names and indices are shown in the format ffmpeg expects them.

**macOS (avfoundation):**
```bash
ffmpeg -f avfoundation -list_devices true -i ""
```
Output has two sections: `AVFoundation video devices:` (cameras + screens, screen is usually the last one with `Capture screen 0`) and `AVFoundation audio devices:`. Indices reset between the two lists — video `1` and audio `0` are unrelated.

**Windows (dshow for camera/mic, gdigrab for desktop):**
```bash
ffmpeg -list_devices true -f dshow -i dummy
ffmpeg -list_options true -f dshow -i video="HD Webcam"
```
`gdigrab` needs no enumeration — input name is always `desktop` (or `title=Window Name`).

**Linux:**
```bash
# Cameras
v4l2-ctl --list-devices
ffmpeg -f v4l2 -list_formats all -i /dev/video0
# Audio (Pulse)
pactl list sources short
# Audio (ALSA)
arecord -L
# Display (X11)
echo "$DISPLAY"   # usually :0.0 or :1.0
```

Or run the helper: `python3 scripts/capture.py list-devices` (auto-detects platform).

## Step 2 — Pick source + audio route

Decide:

1. **Video source:** screen? camera? region? window?
2. **Audio route:** mic? system audio? both? none?
3. **Container:** MKV for long/crash-safe sessions, MP4 for quick clips.
4. **Encoder:** `libx264 -preset ultrafast -pix_fmt yuv420p` for CPU; platform HW encoder for 60fps+ (see [`references/devices.md`](references/devices.md)).

System audio notes:
- **macOS** has no native loopback — install [BlackHole](https://github.com/ExistentialAudio/BlackHole) (or use Loopback / Rogue Amoeba). Route system output to BlackHole, then use `-i ":<blackhole_index>"`. To hear it too, build a Multi-Output Device in Audio MIDI Setup.
- **Windows**: use `-f dshow -i audio="Stereo Mix"` (if enabled) or VB-Cable.
- **Linux**: `pactl list sources short` shows a `*.monitor` source for each sink — that's system audio.

## Step 3 — Run capture with proper encoder

### macOS — screen + default mic (most common)
```bash
ffmpeg -f avfoundation -framerate 30 -capture_cursor 1 -i "1:0" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -b:a 160k out.mp4
```
`"1:0"` = video device index 1 (screen), audio device index 0 (default mic). Replace with your actual indices from Step 1.

### macOS — screen only, no audio, 60fps, HW-encoded
```bash
ffmpeg -f avfoundation -framerate 60 -capture_cursor 1 -i "1" \
  -c:v h264_videotoolbox -b:v 8M -pix_fmt yuv420p out.mp4
```

### macOS — crop a region from full-screen capture
```bash
ffmpeg -f avfoundation -framerate 30 -i "1" \
  -vf "crop=1280:720:100:100" -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```
avfoundation has no native region mode; always full-screen then crop via `-vf crop=W:H:X:Y`.

### macOS — built-in camera + mic
```bash
ffmpeg -f avfoundation -framerate 30 -video_size 1280x720 -i "0:0" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac out.mp4
```

### macOS — screen + mic + system audio (BlackHole)
Assume BlackHole is audio index 2, mic is index 0:
```bash
ffmpeg -f avfoundation -framerate 30 -capture_cursor 1 -i "1:0" \
       -f avfoundation -i ":2" \
       -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest[a]" \
       -map 0:v -map "[a]" -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac out.mp4
```

### Windows — full desktop
```bash
ffmpeg -f gdigrab -framerate 30 -i desktop \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```

### Windows — region of desktop
```bash
ffmpeg -f gdigrab -framerate 30 -offset_x 100 -offset_y 100 \
  -video_size 1280x720 -i desktop -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```

### Windows — specific window
```bash
ffmpeg -f gdigrab -framerate 30 -i title="Mozilla Firefox" -c:v libx264 out.mp4
```

### Windows — webcam + mic (dshow)
```bash
ffmpeg -f dshow -framerate 30 -video_size 1280x720 \
  -i video="HD Pro Webcam C920":audio="Microphone (Realtek)" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac out.mp4
```

### Linux — X11 full display
```bash
ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0 \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```

### Linux — X11 region
```bash
ffmpeg -f x11grab -framerate 30 -video_size 1280x720 -i :0.0+100,100 out.mp4
```

### Linux — webcam (v4l2)
```bash
ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 \
  -i /dev/video0 -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```

### Linux — audio (Pulse or ALSA)
```bash
ffmpeg -f pulse -i default out.wav           # Pulse default mic
ffmpeg -f pulse -i alsa_output.monitor out.wav  # system audio (monitor)
ffmpeg -f alsa -i hw:0 out.wav
```

### Linux — DRM/KMS (Wayland / no X11)
```bash
sudo ffmpeg -device /dev/dri/card0 -f kmsgrab -i - \
  -vf 'hwdownload,format=bgr0' -c:v libx264 -preset ultrafast -pix_fmt yuv420p out.mp4
```
Requires root or `sudo setcap cap_sys_admin+ep $(which ffmpeg)`.

## Step 4 — Stop cleanly

- **Press `q`** in the ffmpeg terminal. ffmpeg flushes the mux and finalizes the MOOV atom for MP4.
- **Do NOT Ctrl+C** unless recording MKV. Ctrl+C on MP4 often leaves an unreadable file (no MOOV). MKV is crash-safe and can be remuxed later: `ffmpeg -i recording.mkv -c copy recording.mp4`.
- For unattended timed captures use `-t 60` (stop after 60s) rather than killing the process.
- For long sessions use `-f segment -segment_time 600 -reset_timestamps 1 out_%03d.mkv` so crashes cost at most one segment.

## Available scripts

- **`scripts/capture.py`** — cross-platform wrapper: `list-devices`, `screen`, `webcam`, `audio-only`. Auto-detects the platform and builds the right ffmpeg command. `--dry-run` prints the command without running it.

## Workflow

```bash
# 1. What devices exist?
python3 ${CLAUDE_SKILL_DIR}/scripts/capture.py list-devices

# 2. Dry-run to confirm the command
python3 ${CLAUDE_SKILL_DIR}/scripts/capture.py screen --output out.mp4 --fps 30 --dry-run

# 3. Record
python3 ${CLAUDE_SKILL_DIR}/scripts/capture.py screen --output out.mp4 --fps 30 --audio auto
```

## Reference docs

- Read [`references/devices.md`](references/devices.md) for the full per-platform option tables (avfoundation, gdigrab, dshow, x11grab, kmsgrab, v4l2, alsa, pulse, decklink), virtual-audio devices, TCC/permission reset, crash-safe recording, and bitrate/FPS recommendations.

## Gotchas

- **macOS permissions:** ffmpeg needs Screen Recording AND Microphone permission in System Settings → Privacy & Security. First run prompts the dialog and ffmpeg exits immediately with empty/`EAGAIN` capture — grant permission to the parent terminal/IDE (Terminal.app, iTerm, VS Code) and re-run. Permission is per-binary-path: reinstalling ffmpeg to a new location re-prompts.
- **avfoundation indices are not arbitrary.** `"1:0"` means "video device 1, audio device 0" exactly as listed by `-list_devices true`. Video and audio lists are numbered independently.
- **avfoundation has no system-audio input.** Install BlackHole / Loopback and chain it as a second `-f avfoundation -i ":N"` input, then `-filter_complex amix` or `-map` to combine.
- **dshow device names need exact case and quoting** on Windows. `video="HD Webcam"` (curly-quote will break). Audio and video are separate arguments in the same `-i`: `video="X":audio="Y"`.
- **`-pix_fmt yuv420p`** is required for libx264 output that plays in QuickTime/Safari/iOS. Leave it off and you get yuv444p, which many players refuse.
- **60fps screen capture** saturates libx264-ultrafast on most CPUs. Use `h264_videotoolbox` (mac), `h264_nvenc` (NVIDIA), `h264_qsv` (Intel), `h264_amf` (AMD) — see `ffmpeg-hwaccel`.
- **gdigrab cursor:** `-draw_mouse 1` (default on). Some builds ignore it; cursor overlay is unreliable in virtual display setups (RDP).
- **x11grab `:0.0`** must match the running `$DISPLAY`. On multi-monitor X, use `:0.0+X,Y` to pick the origin.
- **v4l2 `-input_format mjpeg`** is required for most UVC webcams at 720p/1080p 30fps. Raw YUYV falls back to 5–10fps at full res.
- **kmsgrab** requires root or `setcap cap_sys_admin+ep`. Outputs DRM prime frames — always chain `hwdownload,format=bgr0` before encoding on CPU.
- **Pulse source names** change between reboots on some systems — `pactl list sources short` each session.
- **Stopping:** `q` in terminal = clean shutdown. Ctrl+C on MP4 = corrupted file. Record MKV for anything over a minute, remux after.
- **Audio drift:** on long sessions audio can drift several hundred ms. Use `-async 1` or record audio to a separate file and mux after.

## Examples

### Example 1: quick 30-second screen recording on macOS

```bash
# List devices
ffmpeg -f avfoundation -list_devices true -i ""
# → video index 1 = "Capture screen 0", audio index 0 = "MacBook Pro Microphone"

ffmpeg -f avfoundation -framerate 30 -capture_cursor 1 -i "1:0" \
  -t 30 -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac demo.mp4
```

### Example 2: crash-safe 2-hour tutorial recording on Windows

```bash
ffmpeg -f gdigrab -framerate 30 -i desktop \
       -f dshow -i audio="Microphone (USB Audio)" \
       -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -c:a aac \
       -f segment -segment_time 600 -reset_timestamps 1 tutorial_%03d.mkv
# Press q to stop. Then remux:
ffmpeg -f concat -safe 0 -i <(for f in tutorial_*.mkv; do echo "file '$PWD/$f'"; done) -c copy tutorial.mp4
```

### Example 3: webcam-only on Linux for a video call recording

```bash
ffmpeg -f v4l2 -input_format mjpeg -video_size 1920x1080 -framerate 30 -i /dev/video0 \
       -f pulse -i default \
       -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac call.mp4
```

## Troubleshooting

### Error: `Input/output error` or zero bytes (macOS)
**Cause:** Screen Recording permission not granted to the parent terminal.
**Solution:** System Settings → Privacy & Security → Screen Recording → enable Terminal/iTerm/VS Code. Fully quit and relaunch the terminal (not just re-run). If still failing, reset TCC: `tccutil reset ScreenCapture`.

### Error: `Could not find video device with name [...]` (Windows dshow)
**Cause:** Device name mismatch (case, trailing spaces, truncated).
**Solution:** Run `ffmpeg -list_devices true -f dshow -i dummy` and copy the name verbatim, including spaces. Wrap in double quotes.

### Error: `x11grab ... BadMatch` or black frame
**Cause:** `$DISPLAY` doesn't match, or running over SSH without `-Y`.
**Solution:** `export DISPLAY=:0.0` locally, or use `ssh -Y` and target the remote display.

### Error: `kmsgrab: Permission denied`
**Cause:** kmsgrab requires CAP_SYS_ADMIN.
**Solution:** `sudo ffmpeg ...` or `sudo setcap cap_sys_admin+ep $(which ffmpeg)`.

### Output MP4 won't open / "moov atom not found"
**Cause:** ffmpeg was killed with SIGKILL / Ctrl+C mid-recording; MOOV never written.
**Solution:** Always press `q` to stop. For future recordings use MKV, then `ffmpeg -i in.mkv -c copy out.mp4`. Try recovery: `untrunc` or `ffmpeg -err_detect ignore_err -i broken.mp4 -c copy fixed.mp4`.

### Webcam stuck at 5fps (Linux)
**Cause:** v4l2 defaulted to raw YUYV; USB 2.0 bandwidth cap.
**Solution:** Add `-input_format mjpeg` before `-i /dev/video0`.

### Audio and video out of sync after a long recording
**Cause:** Clock drift between capture devices.
**Solution:** Add `-use_wallclock_as_timestamps 1` on each input, or record audio separately and mux after with `-itsoffset` to align.
