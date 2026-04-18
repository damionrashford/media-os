---
name: ffmpeg-playback
description: >
  Preview and debug media with ffplay: quick A/V preview, filter-graph testing (-vf/-af), loudness meter (ebur128), AV-sync debug, seek/loop, show waveform/spectrum/vectorscope, pixel format overlay. Use when the user asks to preview a video, play back a file quickly, test a filter with live output, debug audio/video sync, inspect loudness visually, loop a clip, or scrub through frame-by-frame for QA.
argument-hint: "[input]"
---

# Ffmpeg Playback

**Context:** $ARGUMENTS

## Quick start

- **Preview a file:** Step 1 — `ffplay in.mp4`
- **Test a `-vf` filter live without transcoding:** Step 2
- **Debug pixel format / SAR / frame info:** Step 3
- **Visualize audio (waveform / spectrum / loudness meter):** Step 4
- **Fix AV-sync drift:** Step 3 (`-sync ext`) + `-vf setpts=PTS-STARTPTS`
- **Headless preview (no GUI):** add `-nodisp -autoexit` (audio only)

## When to use

- User wants to eyeball a clip after a cut, filter, or encode (QA pass).
- User is iterating on a `-vf` or `-af` chain and wants live feedback before running a full transcode.
- User needs visual AV diagnostics: waveform, spectrum, vectorscope, ebur128 loudness meter, or verbose logs to see pixel format / color range / SAR.
- User is debugging A/V drift, out-of-order PTS, or choppy playback.

Do NOT use for: long-term rendering (use `ffmpeg-transcode`), authoring filter chains to a file (use `ffmpeg-video-filter` / `ffmpeg-audio-filter`), inspecting metadata only (use `ffmpeg-probe`). ffplay is an interactive debug player — not a production media player.

## Step 1 — Simple preview

```bash
ffplay in.mp4                          # play, loop off, window auto-sized
ffplay -ss 60 -t 10 in.mp4             # start at 60s, play 10s then quit (with -autoexit)
ffplay -autoexit in.mp4                # quit at EOF instead of hanging on last frame
ffplay -loop 0 in.mp4                  # infinite loop
ffplay -x 1280 -y 720 in.mp4           # force window size
ffplay -an in.mp4                      # mute / disable audio decoder
ffplay -vn in.mp4                      # audio only
ffplay -nodisp -autoexit in.mp4        # no window (audio plays; video decoded but not shown)
```

`-ss` is ffplay's **start-offset seek** — it only accepts a single timestamp and goes before the input file on the command line. There is no "output-side" seek in ffplay.

## Step 2 — Filter-graph test (live, no transcode)

Use ffplay to preview a filter you'll later apply with ffmpeg. No file is written.

```bash
# Test a video filter chain
ffplay -vf "scale=1280:-2,eq=brightness=0.1,unsharp=5:5:1.0" in.mp4

# Test an audio filter chain
ffplay -af "loudnorm=I=-16:LRA=11:TP=-1.5" in.mp4

# Both at once
ffplay -vf "hqdn3d" -af "highpass=f=80" in.mp4
```

Press **`w`** during playback to cycle through / disable the video filter chain — useful for A/B comparison.

For complex graphs with multiple inputs, use `-f lavfi` with a source filter (`movie=`, `amovie=`) in a filtergraph:

```bash
ffplay -f lavfi "movie=in.mp4,split[a][b];[b]vflip[c];[a][c]hstack[out]"
```

When `-f lavfi` is used, the graph MUST terminate with labeled outputs. For combined audio+video use two sinks named `[out0]` (video) and `[out1]` (audio).

## Step 3 — Debug mode: stats, pixel format, AV-sync

```bash
# In-window HUD: frame #, fps, VQ size, dropped frames (on by default in newer builds)
ffplay -stats in.mp4

# Verbose terminal log: shows pix_fmt, color_range, SAR/DAR, timebase, decoder
ffplay -loglevel verbose in.mp4

# Cycle stream with keyboard: a (audio), v (video), t (subtitle), c (chapter)
```

**AV-sync debugging.** ffplay picks audio as the master clock by default. Swap masters to narrow down drift:

```bash
ffplay -sync audio in.mp4    # default — video resyncs to audio
ffplay -sync video in.mp4    # audio resyncs to video (exposes dropped video frames as audio drift)
ffplay -sync ext   in.mp4    # both sync to an external wall clock — exposes stream-level drift
```

If you see monotonic drift, the fix is usually in a filter: prepend `setpts=PTS-STARTPTS` (video) and `asetpts=PTS-STARTPTS` (audio) to reset timestamps, or `aresample=async=1` to soft-fix audio gaps.

**Useful debug flags:**

- `-framedrop` — drop video frames if CPU can't keep up (on by default when sync source is not video).
- `-infbuf` — unlimited demux buffer (for live/RTSP/slow sources).
- `-vf "showinfo"` — log per-frame metadata (pts, pkt_pos, mean).

## Step 4 — Visualize audio

ffplay can render audio as video via lavfi source filters (`amovie=`). The graph must end in `[out0]` (video) + `[out1]` (audio).

```bash
# Waveform (overlay mode "cline") next to audio
ffplay -f lavfi "amovie=in.mp3,asplit[a][w];[w]showwaves=s=1280x120:mode=cline[v];[a][v]concat=n=1:v=1:a=1[out0][out1]"

# Spectrum
ffplay -f lavfi "amovie=in.mp3,showspectrum=s=1024x512:mode=combined:slide=scroll"

# Live loudness meter (EBU R128, 18 LU scale)
ffplay -f lavfi "amovie=in.mp3,ebur128=video=1:meter=18[out0][out1]"

# Vectorscope overlay on a video (live)
ffplay -vf "split[a][b];[b]vectorscope=mode=color3[c];[a][c]overlay=W-w" in.mp4

# Histogram + waveform monitor on a live video
ffplay -vf "split[a][b];[b]histogram[c];[a][c]hstack" in.mp4
```

## Piped playback

ffplay reads stdin when the input is `-`:

```bash
ffmpeg -i in.mkv -c copy -f matroska - | ffplay -i -
ffmpeg -f lavfi -i testsrc=size=640x360:rate=30 -f mpegts - | ffplay -i -
```

## Gotchas

- **ffplay is a DEBUG player.** There is no playlist, no UI for codec selection, no per-device audio routing. Do not ship it to end users.
- **SDL2 is required.** In headless SSH you get `Could not initialize SDL - No available video device`. Fix: X-forward (`ssh -Y`), VNC, or add `-nodisp` for audio only. `SDL_VIDEODRIVER=dummy` lets ffplay start without a window but you also won't see any video — use `-nodisp` instead.
- **macOS opens its own window** (Cocoa). No menu bar — keyboard shortcuts only work when the ffplay window has **focus**. Click it first.
- **Audio device isn't selectable via ffplay flags.** Use SDL env vars: `SDL_AUDIODRIVER=coreaudio` (mac) / `alsa` / `pulse` / `dsp`. To pick a specific device set `AUDIODEV` (OSS/ALSA) or configure PulseAudio default sink.
- **`-f lavfi` graphs MUST end in labeled outputs.** For video+audio that's `[out0]` and `[out1]` — BOTH are required when using `ebur128=video=1` or `showwaves` + concat with audio. Drop one label and you'll see `Output pad "out1" ... not connected`.
- **`amovie` / `movie` are lavfi source filters**, not input flags. Use them INSIDE the `-f lavfi` graph string, not as `-i`.
- **`-ss` is a start offset, not an output-side seek.** You cannot put `-ss` after an input or combine it with `-to`; use `-t` for duration.
- **Exit status is not useful for automation.** ffplay is interactive. Use `-autoexit` to quit at EOF; use `-nodisp` to avoid needing a display. For CI/QA scripts, prefer `ffmpeg` with `-f null -` for filter validation.
- **`-stats` is on by default in newer builds** — disable with `-nostats` if it clutters your log.
- **High-DPI displays:** `-x` / `-y` are logical pixels on macOS/Wayland — the actual backing store is 2× on Retina.
- **Keyboard focus is per-window.** Tmux / screen multiplexers don't forward keys to ffplay; you must focus the SDL window.
- **`-loop 0` means loop forever**; `-loop 1` plays once (default); `-loop N` plays N times. Mirrors ffmpeg's output-side `-loop` semantics but confusingly named.

## Examples

### Example 1 — Iterate on a color filter before a final encode

```bash
# Live preview while tuning
ffplay -vf "eq=contrast=1.1:brightness=0.05:saturation=1.1,unsharp=5:5:0.8" in.mp4
# Press w mid-playback to A/B toggle. When happy, commit with ffmpeg:
ffmpeg -i in.mp4 -vf "eq=contrast=1.1:brightness=0.05:saturation=1.1,unsharp=5:5:0.8" -c:a copy out.mp4
```

### Example 2 — Is the audio too loud?

```bash
ffplay -f lavfi "amovie=mix.wav,ebur128=video=1:meter=18[out0][out1]"
# Read integrated LUFS bottom-left, short-term/momentary bars right side.
# If I > -14 LUFS, normalize with: ffmpeg -af loudnorm=I=-16:LRA=11:TP=-1.5 ...
```

### Example 3 — AV is drifting after a concat

```bash
ffplay -sync ext concat_out.mp4
# If drift accumulates linearly, the concat inputs had different timebases.
# Re-do the concat with: -vf setpts=PTS-STARTPTS -af asetpts=PTS-STARTPTS,aresample=async=1
```

### Example 4 — Preview an ffmpeg pipe without writing a file

```bash
ffmpeg -i in.mov -vf scale=640:-2 -c:v libx264 -preset ultrafast -f matroska - | ffplay -i -
```

## Keyboard shortcuts (full table in `references/commands.md`)

- `Space` / `p` — pause/play
- `s` — step one frame forward
- `Left` / `Right` — seek ±10s
- `Down` / `Up` — seek ±1min
- `PgDown` / `PgUp` — seek to previous/next chapter (or ±10min)
- `f` — toggle fullscreen
- `w` — cycle video filters (ffplay-only, for A/B)
- `a` / `v` / `t` / `c` — cycle audio / video / subtitle / program stream
- `m` — mute
- `9` / `0` — volume down / up
- `q` / `Esc` — quit
- Left-click on video — seek to that horizontal position (% of duration)
- Right-click / drag — seek by percent

## Available scripts

- **`scripts/play.py`** — stdlib-only argparse wrapper around ffplay with subcommands: `preview`, `filter-test`, `waveform`, `spectrum`, `vectorscope`, `loudness-meter`, `sync`. Flags: `--dry-run`, `--verbose`. Prints the command before running, and downgrades to `-nodisp` when no DISPLAY is detected.

## Workflow

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/play.py preview --input in.mp4 --start 60 --duration 10
python3 ${CLAUDE_SKILL_DIR}/scripts/play.py filter-test --input in.mp4 --vf "scale=1280:-2,eq=brightness=0.1"
python3 ${CLAUDE_SKILL_DIR}/scripts/play.py loudness-meter --input in.mp3
python3 ${CLAUDE_SKILL_DIR}/scripts/play.py sync --input in.mp4 --mode ext
```

## Reference docs

- Read [`references/commands.md`](references/commands.md) for the full keyboard shortcut table, every ffplay flag, the lavfi visualization catalog, SDL audio env vars, pipe recipes, and headless troubleshooting.

## Troubleshooting

### Error: `Could not initialize SDL - No available video device`

Cause: no DISPLAY / Wayland / Quartz session (headless SSH, container, CI).
Solution: add `-nodisp` for audio-only; or X-forward with `ssh -Y`; or run under VNC/xvfb. `SDL_VIDEODRIVER=dummy` starts SDL but shows nothing — equivalent to `-nodisp` with extra steps.

### Error: `Output pad "out1" with type audio of the filtergraph is not connected to any destination`

Cause: `-f lavfi` graph has only a video sink but the source (e.g. `amovie`) also produces audio, or you used `ebur128=video=1` which emits both pads.
Solution: terminate with `[out0][out1]` and keep both audio + video, e.g. `...ebur128=video=1[out0][out1]`.

### Error: `Option 'ss' cannot be applied to output url`

Cause: `-ss` placed after a `-i` or alongside `-to`. In ffplay, `-ss` is a global/input-side start offset only, given once.
Solution: `ffplay -ss 60 -t 10 in.mp4` — `-ss` first, `-i` is implicit.

### Video plays but audio is silent

Causes (in order): SDL audio driver mismatch, default output device muted, decoder can't produce planar format SDL wants.
Solution: set `SDL_AUDIODRIVER=coreaudio` (mac) / `pulse` / `alsa`; check system volume; re-run with `-loglevel verbose` and look for `SDL_OpenAudioDevice` errors.

### AV out of sync on a file that plays fine in VLC

Cause: ffplay's default master clock is audio; if audio has gaps or VFR video has long frames, drift is visible.
Solution: `-sync ext` to use wall clock; or preprocess with `setpts=PTS-STARTPTS` + `aresample=async=1`.

### Keyboard shortcuts do nothing

Cause: SDL window doesn't have focus, or terminal is capturing keys.
Solution: click the video window. On macOS, make sure a Terminal.app shortcut isn't swallowing the key.
