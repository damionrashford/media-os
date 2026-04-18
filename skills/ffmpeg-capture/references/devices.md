# Capture Devices Reference

Full per-platform grabber tables, virtual-audio routing, permission/TCC troubleshooting, crash-safe recording patterns, and recommended encoding settings.

## Overview

Load this reference when:
- The quick recipes in `SKILL.md` don't cover the exact grabber option you need.
- You need to route system audio via a virtual device (BlackHole, VB-Cable, pulse loopback).
- macOS permissions are blocking capture and you need to reset TCC.
- You're recording a long session and need crash-safe segmenting + remux.
- You're choosing a hardware encoder / bitrate for a target FPS + resolution.

---

## macOS — avfoundation

List: `ffmpeg -f avfoundation -list_devices true -i ""`

Input syntax: `-i "V:A"` or `-i "V"` (video only) or `-i ":A"` (audio only). Indices are from the two independent lists in `-list_devices` output.

| Option | Values | Notes |
|---|---|---|
| `-framerate` | 15, 30, 60 | Before `-i`. Some screens cap at 60. |
| `-video_size` | `1280x720` etc. | Mostly for cameras; ignored by screen capture. |
| `-pixel_format` | `uyvy422`, `yuyv422`, `nv12` | Before `-i`. Camera-dependent. |
| `-capture_cursor` | `0` / `1` | Draws mouse on screen captures. |
| `-capture_mouse_clicks` | `0` / `1` | Ripples click animation. |
| `-capture_raw_data` | `0` / `1` | Disable HW decoding in driver. |
| `-pixel_format list` | — | Run with `-list_devices` to enumerate supported formats per device. |

Device index notes:
- Video list typically ends with `[N] Capture screen 0` (and `[N+1] Capture screen 1` on multi-monitor).
- Audio list starts with the OS default mic at index 0.
- iPhone plugged into Mac shows as a video device if Continuity Camera is on.

---

## Windows — gdigrab (desktop)

Input name is literal: `-i desktop` (full primary monitor), `-i title="Window Title"` (single window by title), or `-i hdc` for a device context.

| Option | Purpose |
|---|---|
| `-framerate N` | FPS. Before `-i`. |
| `-offset_x N -offset_y N` | Top-left corner of region. |
| `-video_size WxH` | Region size. Combine with offsets. |
| `-draw_mouse 0/1` | Cursor overlay (default 1). |
| `-show_region 1` | Draw a box around the captured region (debug). |
| `-framerate ntsc` | Shortcut for 30000/1001. |

Gotchas: gdigrab is GDI-based and slower than dxgi. For high-fps capture install a modern build with `ddagrab` (DXGI desktop duplication) and `-f lavfi -i ddagrab`.

## Windows — dshow (cameras, mics, stereo mix)

List: `ffmpeg -list_devices true -f dshow -i dummy`
List formats: `ffmpeg -list_options true -f dshow -i video="HD Webcam"`

Input: `-i video="Name":audio="Name"` — quotes required, exact case, no trailing space.

| Option | Purpose |
|---|---|
| `-video_size WxH` | Must match a mode from `-list_options`. |
| `-framerate N` | Must match a mode. |
| `-pixel_format fmt` | `yuyv422`, `nv12`, `mjpeg`. |
| `-rtbufsize 256M` | Raise real-time input buffer to prevent drops. |
| `-audio_buffer_size N` | Lower = less latency (ms). |
| `-sample_rate N` | Audio sample rate. |
| `-channels N` | 1 mono, 2 stereo. |

## Windows — ddagrab (modern DXGI, high fps)

`ffmpeg -f lavfi -i ddagrab=output_idx=0:framerate=60 -c:v h264_nvenc out.mp4` — lives on GPU, zero-copy to NVENC.

---

## Linux — x11grab

`-f x11grab -framerate N -video_size WxH -i DISPLAY[+X,Y]`

| Option | Purpose |
|---|---|
| `-video_size` | Region size (or full display size). |
| `-framerate` | FPS. |
| `-draw_mouse 0/1` | Cursor overlay. |
| `-follow_mouse centered` | Track mouse with capture region. |
| `-show_region 1` | Debug rectangle. |
| `-i :D.S+X,Y` | Display D, screen S, origin X,Y. |

## Linux — kmsgrab (Wayland / headless)

`sudo ffmpeg -device /dev/dri/card0 -f kmsgrab -i - -vf 'hwdownload,format=bgr0' ...`

| Option | Purpose |
|---|---|
| `-device /dev/dri/cardN` | Which DRM node. |
| `-format bgr0` (hwdownload) | Required pixel conversion. |
| `-framerate N` | Cap FPS. |

Requires CAP_SYS_ADMIN. Captures whatever the running compositor is showing (works under Wayland). Output is DRM prime frames — you MUST chain `hwdownload,format=bgr0` (or keep on GPU with `vaapi_scale` etc.) before a CPU encoder.

## Linux — v4l2 (webcams)

`ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i /dev/video0`

| Option | Purpose |
|---|---|
| `-input_format` | `mjpeg`, `yuyv422`, `h264`. MJPEG required for most UVC at 720p+. |
| `-video_size` / `-framerate` | Must match a mode from `ffmpeg -f v4l2 -list_formats all -i /dev/video0`. |
| `-ts abs` | Timestamp mode. |
| `-use_libv4l2 1` | Use libv4l2 for format conversions. |

## Linux — ALSA

`ffmpeg -f alsa -i hw:0` or `plughw:0,0`. Use `arecord -L` to enumerate names.

| Option | Purpose |
|---|---|
| `-sample_rate` | 44100, 48000. |
| `-channels` | 1 or 2. |
| `-i default` | ALSA default device (or `hw:CARD=PCH`). |

## Linux — PulseAudio

`ffmpeg -f pulse -i default` or `-i <source.name>` from `pactl list sources short`.

To capture system audio, use the `.monitor` source of your output sink:
```
pactl list sources short | grep monitor
# alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
ffmpeg -f pulse -i alsa_output.pci-0000_00_1f.3.analog-stereo.monitor out.wav
```

## Decklink (Blackmagic SDI/HDMI capture)

`ffmpeg -f decklink -list_devices 1 -i dummy`
`ffmpeg -f decklink -format_code Hp30 -i "UltraStudio Mini"`

Requires Blackmagic Desktop Video drivers and ffmpeg built with `--enable-decklink`. Format codes like `Hp30` (1080p30), `hp60` (720p60), `Hi60` (1080i60).

---

## Virtual audio devices

### macOS — BlackHole (free) / Loopback (paid)
1. Install BlackHole 2ch from GitHub.
2. In Audio MIDI Setup, create a **Multi-Output Device** combining Speakers + BlackHole — set system output to this so you can still hear audio.
3. BlackHole appears in `-list_devices true` as an audio device.
4. Capture: `-f avfoundation -i ":<blackhole_idx>"`, optionally combined with mic via `-filter_complex amix`.

### Windows — VB-Cable (free) or VoiceMeeter
1. Install VB-Cable. "CABLE Input" is a playback device; "CABLE Output" is a recording device.
2. Set app/system output to CABLE Input.
3. Capture: `-f dshow -i audio="CABLE Output (VB-Audio Virtual Cable)"`.
4. "Stereo Mix" works on some Realtek-equipped Windows boxes — enable it in Sound Control Panel → Recording → Show Disabled Devices.

### Linux — PulseAudio loopback / module-null-sink
```bash
# Create a null sink and loop the real output into it
pactl load-module module-null-sink sink_name=record
pactl load-module module-loopback source=<real_source> sink=record
# Now record the null sink's monitor
ffmpeg -f pulse -i record.monitor out.wav
```
Or on PipeWire: use `qpwgraph` / `pw-link` to wire app outputs into a dedicated capture node.

---

## macOS permissions troubleshooting (TCC)

Symptoms: ffmpeg exits immediately, output is 0 bytes, stderr shows `Input/output error` or `Cannot Open`. The first run also often reports `... nothing captured`.

Fix:
1. System Settings → **Privacy & Security** → **Screen Recording** → enable the parent app (Terminal / iTerm2 / VS Code / Warp). Not ffmpeg itself — ffmpeg inherits from the terminal.
2. Same for **Microphone** and **Camera**.
3. **Fully quit** the terminal app (Cmd-Q, not just close window) and relaunch. TCC permissions apply on process launch.
4. If the toggle is on but capture still fails: reset and re-prompt:
   ```bash
   tccutil reset ScreenCapture
   tccutil reset Microphone
   tccutil reset Camera
   ```
5. Per-binary: if you moved ffmpeg (`/opt/homebrew/bin/ffmpeg` vs `/usr/local/bin/ffmpeg`) TCC treats them as different and re-prompts. Reinstalls also re-prompt.

---

## Crash-safe recording

MP4 finalizes the MOOV atom only on clean shutdown. If ffmpeg is killed (crash, kernel panic, out-of-disk), the file is typically unplayable. Two patterns avoid this:

### Pattern A — MKV first, remux to MP4 after
```bash
ffmpeg ... -c:v libx264 -c:a aac out.mkv
# later, when you pressed q:
ffmpeg -i out.mkv -c copy out.mp4
```
MKV uses a streaming muxer — every frame is written with a complete header. Truncated MKVs remain playable up to the last written frame.

### Pattern B — segmented MKV
```bash
ffmpeg ... -f segment -segment_time 600 -reset_timestamps 1 out_%03d.mkv
# after stopping:
printf "file '%s'\n" out_*.mkv > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy combined.mp4
```
Crash costs at most one 10-minute segment.

### Pattern C — `-movflags +faststart` alone doesn't help
`faststart` moves MOOV to front AT END of encode. It doesn't write MOOV incrementally. Use `-movflags frag_keyframe+empty_moov+default_base_moof` for fragmented MP4, which is crash-safe but has slightly larger files and worse compatibility.

---

## Cursor / FPS / bitrate recommendations

| Use case | FPS | Encoder | Bitrate / CRF | Notes |
|---|---|---|---|---|
| Talking-head screencast | 30 | `libx264 -preset ultrafast` | CRF 23 | `-pix_fmt yuv420p`. |
| Fast action / gameplay | 60 | HW (NVENC / VideoToolbox / QSV) | 8–12 Mbps CBR | CPU encoders drop frames. |
| Archival / editing source | 30 | `libx264 -preset veryfast` | CRF 18 | Larger but edits cleanly. |
| Webcam interview | 30 | `libx264 -preset ultrafast` | CRF 23 | MJPEG input on v4l2/dshow. |
| Voice-only podcast | — | PCM or Opus | 96–128k Opus | `-c:a libopus -b:a 96k`. |
| 4K screen capture | 30 | HW | 20–30 Mbps | Enable HW or drop to 1080p. |
| Low-latency local | 30 | `libx264 -tune zerolatency` | CRF 28 | Smaller GOP via `-g 30`. |

Cursor visibility:
- avfoundation: `-capture_cursor 1` (+ `-capture_mouse_clicks 1` for ripples).
- gdigrab: `-draw_mouse 1` (default).
- x11grab: `-draw_mouse 1` (default).
- kmsgrab: cursor rendered by compositor — usually present automatically.

---

## DirectShow vs Media Foundation

ffmpeg on Windows ships two capture APIs:

- **`-f dshow`** — DirectShow, older but supports almost every webcam/mic. Device names from `-list_devices true -f dshow`. Use this by default.
- **`-f mf`** — Media Foundation, newer Win7+. `ffmpeg -f mf -list_devices 1 -i dummy`. Better with modern UVC devices but support is inconsistent across ffmpeg builds.

Prefer dshow unless a specific device requires MF (some ARM64 Windows tablets).

---

## Gotchas

- avfoundation video and audio index spaces are independent — don't assume `2:2` means one device.
- On macOS, `-list_devices true` exits non-zero; that's expected (there's no real input).
- `-capture_cursor 1` must come BEFORE `-i`, not after — it's an input option.
- dshow names must match byte-for-byte including double spaces; copy from `-list_devices` output.
- v4l2 webcams often expose `/dev/video0` (capture) and `/dev/video1` (metadata stream). If `video0` errors with "no such capability", try `video1`.
- kmsgrab output is 10-bit on some Intel GPUs — chain `format=nv12` explicitly to avoid encoder errors.
- Audio sample rates between input and encoder: always add `-ar 48000` on the output if mixing sources; otherwise drift.
- On Apple Silicon, `h264_videotoolbox` needs `-allow_sw 1` if the GPU encoder is busy; otherwise ffmpeg refuses.
- Recording while sleeping: macOS pauses capture on sleep. Use `caffeinate -dims ffmpeg ...` to keep the machine awake.
