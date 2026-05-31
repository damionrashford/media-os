# ffplay command reference

Quick-access reference for `ffplay`. Source docs:
- https://ffmpeg.org/ffplay.html
- https://ffmpeg.org/ffplay-all.html
- https://ffmpeg.org/ffmpeg-filters.html

## Keyboard shortcuts (full table)

| Key | Action |
|---|---|
| `q`, `Esc` | Quit. |
| `f` | Toggle fullscreen. |
| `p`, `Space` | Toggle pause. |
| `m` | Toggle mute. |
| `9` / `0` | Volume down / up. |
| `/` / `*` | Same as `9` / `0` on some keymaps. |
| `a` | Cycle audio stream. |
| `v` | Cycle video stream. |
| `t` | Cycle subtitle stream. |
| `c` | Cycle program / chapter. |
| `w` | Cycle video filters (and "all off" state). Useful A/B. |
| `s` | Step to the next video frame (with pause). |
| `Left` / `Right` | Seek backward / forward 10 seconds. |
| `Down` / `Up` | Seek backward / forward 1 minute. |
| `Page Down` / `Page Up` | Seek to previous / next chapter, or ±10 min. |
| Mouse left-click | Seek to horizontal position (% of duration). |
| Mouse right-drag | Seek by percentage of drag across window. |
| Double-click | Toggle fullscreen. |

Note: keyboard focus must be on the ffplay SDL window (not the terminal).

## Flag reference

### Input / timing

| Flag | Purpose |
|---|---|
| `-i URL` | Explicit input (usually implicit positional arg). `-i -` for stdin. |
| `-ss POS` | Start offset. Accepts `SS`, `HH:MM:SS`, or `HH:MM:SS.mmm`. |
| `-t DUR` | Duration to play. Combine with `-autoexit` for scripts. |
| `-autoexit` | Quit after EOF instead of freezing on the last frame. |
| `-loop N` | Loop N times. `-loop 0` = infinite. |

### Window / display

| Flag | Purpose |
|---|---|
| `-x WIDTH` | Force window width (logical pixels). |
| `-y HEIGHT` | Force window height. |
| `-left X` / `-top Y` | Initial window position. |
| `-fs` | Start fullscreen. |
| `-window_title "..."` | Custom window title. |
| `-nodisp` | Don't open a video window. Video decoded but not shown. Audio plays. |
| `-noborder` | Borderless window. |
| `-alwaysontop` | Keep window above others. |

### Stream selection / filters

| Flag | Purpose |
|---|---|
| `-an` | Disable audio. |
| `-vn` | Disable video. |
| `-sn` | Disable subtitles. |
| `-ast N` / `-vst N` / `-sst N` | Pick audio/video/subtitle stream index. |
| `-vf "chain"` | Video filter graph. |
| `-af "chain"` | Audio filter graph. |
| `-f lavfi` | Use lavfi as the input format (graphs via `movie=`/`amovie=`). |
| `-pix_fmt FMT` | Request a specific display pixel format. |

### Sync / timing

| Flag | Purpose |
|---|---|
| `-sync audio` | Default. Video resyncs to audio clock. |
| `-sync video` | Audio resyncs to video clock. |
| `-sync ext` | Both resync to external (wall) clock. |
| `-framedrop` | Drop late video frames. On by default when not sync'd to video. |
| `-noframedrop` | Don't drop frames (expect audible skips instead). |
| `-infbuf` | Unlimited demux buffer. For live/RTSP/slow network sources. |

### Logging / diagnostics

| Flag | Purpose |
|---|---|
| `-stats` | In-window HUD (frame #, fps, dropped, VQ size). On by default now. |
| `-nostats` | Disable the HUD. |
| `-loglevel LEVEL` | `quiet` / `panic` / `fatal` / `error` / `warning` / `info` / `verbose` / `debug`. |
| `-v LEVEL` | Alias for `-loglevel`. |
| `-hide_banner` | Skip the build banner. |
| `-showmode MODE` | `0` video, `1` waves, `2` rdft (audio spectrum when no video). |

## Lavfi visualization filters

Use inside `-vf` for video-source material, or inside an `-f lavfi` graph with `amovie=` / `movie=` for file-sourced analysis.

| Filter | Shows | Common options |
|---|---|---|
| `showwaves` | Audio waveform as video. | `s=WxH`, `mode=point|line|p2p|cline`, `rate=30` |
| `showspectrum` | Scrolling spectrogram. | `s=WxH`, `mode=combined|separate`, `slide=scroll|replace`, `color=intensity|channel|rainbow` |
| `showspectrumpic` | One-shot spectrogram image. | `s=WxH`, `legend=1` |
| `showvolume` | Per-channel volume bars. | `r=30`, `b=4`, `f=0.95` |
| `showcqt` | Constant-Q transform (musical pitch view). | `s=WxH`, `bar_g=2` |
| `ebur128` | EBU R128 loudness meter + live I/S/M/LRA. | `video=1`, `meter=9|18`, `size=WxH`, `target=-23` |
| `vectorscope` | Chrominance scatter (broadcast QC). | `mode=gray|color|color3|color4|color5`, `graticule=green` |
| `histogram` | Per-channel luma/chroma histogram. | `display_mode=stack|parade|overlay`, `levels_mode=linear|logarithmic` |
| `waveform` | Broadcast waveform monitor (luma by column). | `mode=row|column`, `intensity=0.04`, `mirror=1`, `display=parade|stack|overlay` |
| `signalstats` | Numeric stats overlay (YAVG, YMIN, SATMAX, etc.). | `stat=tout+vrep+brng`, `out=brng` |
| `oscilloscope` | Pixel-trace along a line (probe a scanline). | `x=0.5:y=0.5:s=0.8:t=0.5` |
| `astats` | Numeric audio stats (terminal, use with `-af`). | — |

### Common ffplay lavfi recipes

Waveform under a video:
```
ffplay -f lavfi "movie=in.mp4,split[a][b];
  [b]scale=1280:-1[top];
  amovie=in.mp4,showwaves=s=1280x120:mode=cline[wav];
  [top][wav]vstack[out]"
```

Two-up comparison (before/after a filter):
```
ffplay -vf "split[a][b];[b]eq=contrast=1.2[c];[a][c]hstack" in.mp4
```

Vectorscope + histogram + video (3-panel QC):
```
ffplay -vf "split=3[a][b][c];
  [b]vectorscope=mode=color3[vs];
  [c]histogram=display_mode=parade[hi];
  [vs][hi]hstack[probes];
  [a][probes]vstack" in.mp4
```

Live loudness with waveform:
```
ffplay -f lavfi "amovie=in.wav,
  asplit=3[a][w][l];
  [w]showwaves=s=1280x120:mode=cline[wv];
  [l]ebur128=video=1:meter=18:size=1280x600[ev][al];
  [wv][ev]vstack[vid];
  [a]anullsink;
  [al]anullsink;
  movie=color=c=black:s=1x1[blk];
  [vid]copy[out0];
  [al]anullsink" 
```
(Simpler: `ffplay -f lavfi "amovie=in.wav,ebur128=video=1:meter=18[out0][out1]"`.)

## SDL environment variables

ffplay uses SDL2 for rendering and audio. Control via env vars, not CLI flags.

### Audio

| Var | Values | Notes |
|---|---|---|
| `SDL_AUDIODRIVER` | `coreaudio` (mac), `pulse`, `alsa`, `pipewire`, `dsp`, `dummy` | Picks backend. `dummy` = silence. |
| `AUDIODEV` | Device path (OSS/ALSA) | e.g. `/dev/dsp1`. |
| `ALSA_PCM_CARD` / `ALSA_PCM_DEVICE` | Card / device index | Route to specific ALSA device. |
| `PULSE_SINK` | Sink name (`pactl list sinks short`) | Route PulseAudio output. |

### Video

| Var | Values | Notes |
|---|---|---|
| `SDL_VIDEODRIVER` | `cocoa`, `x11`, `wayland`, `windows`, `dummy`, `kmsdrm`, `offscreen` | `dummy` / `offscreen` start without a window (equivalent to `-nodisp`). |
| `SDL_RENDER_DRIVER` | `opengl`, `opengles2`, `direct3d`, `metal`, `software` | Force renderer. |
| `SDL_VIDEO_ALLOW_SCREENSAVER` | `0` / `1` | Inhibit OS screensaver. |

## Piped playback recipes

```bash
# Remux on the fly
ffmpeg -i in.mkv -c copy -f matroska - | ffplay -i -

# Generate synthetic test source
ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=30 -f mpegts - | ffplay -i -

# Preview a filter output without writing a file
ffmpeg -i in.mov -vf "zoompan=z='min(zoom+0.0015,1.5)':d=300" \
       -c:v libx264 -preset ultrafast -f matroska - | ffplay -i -

# Network preview (low-latency UDP)
ffmpeg -re -i live.ts -c copy -f mpegts udp://127.0.0.1:1234 &
ffplay -fflags nobuffer -flags low_delay -framedrop udp://127.0.0.1:1234

# Preview encoded segments from HLS
ffplay -protocol_whitelist file,http,https,tcp,tls,crypto https://host/playlist.m3u8
```

## Headless troubleshooting

Symptom → cause → fix:

- `Could not initialize SDL - No available video device` — no GUI session. Fix: `-nodisp`, or X-forward (`ssh -Y host`), or run under `xvfb-run -a ffplay ...`, or use VNC. `SDL_VIDEODRIVER=dummy` lets ffplay start but you will not see video; prefer `-nodisp`.
- `ALSA lib ... cannot open audio device` — PulseAudio is the default on most desktops. Fix: `SDL_AUDIODRIVER=pulse` or start a user PulseAudio instance in the SSH session.
- ffplay spawns on the WRONG monitor — set `SDL_VIDEO_WINDOW_POS=X,Y` before launch, or use `-left` / `-top`.
- Wayland tearing / scaling wrong — try `SDL_VIDEODRIVER=x11` to fall back to XWayland.
- Containers (Docker): mount `/tmp/.X11-unix`, set `DISPLAY=$DISPLAY`, `--device /dev/dri` for hw acceleration. Or run with `xvfb-run` and forgo display.
- macOS: if the window doesn't appear, check Mission Control / another Space. ffplay may also be minimized on first open.
- CI: never expect ffplay to exit cleanly without `-autoexit`. For scripted validation, prefer `ffmpeg -i IN -f null -` (runs the decode + filter chain without a player).

## Quick exit-status cheat sheet

- `0` — normal quit (q, EOF with `-autoexit`).
- `1` — setup error (bad input, unknown codec).
- `130` — SIGINT (Ctrl-C).
- Other — SDL init or decoder failure; re-run with `-loglevel verbose` to see the real reason.

## See also

- `ffmpeg-probe` skill — for metadata-only inspection (JSON/CSV).
- `ffmpeg-video-filter` / `ffmpeg-audio-filter` — for committing a filter chain to a file once you've tuned it here.
- `ffmpeg-transcode` — once playback looks right, encode.
