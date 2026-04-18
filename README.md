# Media OS — Claude Code Plugin

**96 production media skills for Claude Code.** FFmpeg complete, OBS Studio, GStreamer, MediaMTX, broadcast IP (NDI, OpenTimelineIO, HDR dynamic metadata, DeckLink, gphoto2), control protocols (MIDI, OSC, DMX, PTZ), system audio routing, VFX (USD, OpenEXR, OpenImageIO), computer vision, WebRTC, and 2026 open-source AI media. Install the whole bundle OR cherry-pick individual skills.

## Install

First, add the marketplace:

```
/plugin marketplace add damionrashford/media-os
```

Then pick your install mode:

### Install ALL 96 skills (the bundle)

```
/plugin install media-os@media-os
```

All 96 skills load under the `/media-os:` namespace (e.g. `/media-os:ffmpeg-hdr-color`).

### Install ONE skill (standalone)

Each skill is also its own plugin. Install just the ones you need:

```
/plugin install ffmpeg-hdr-color@media-os
/plugin install obs-websocket@media-os
/plugin install media-tts-ai@media-os
```

Individual plugins are named exactly after the skill (`ffmpeg-transcode`, `hdr-dovi-tool`, `webrtc-livekit`, etc.). Install only what your workflow actually needs.

### What's the difference?

| | Bundle (`media-os`) | Single skill |
|---|---|---|
| Contents | All 96 skills | 1 skill + its scripts + references |
| Invocation | `/media-os:skill-name` | `/skill-name:skill-name` |
| When to use | You want the full media toolkit | You only need one specific capability |
| Size | ~10 MB | ~100 KB per skill |
| Updates | Bumping the bundle updates all 96 | Each single-skill plugin versioned independently |

You can install the bundle AND individual plugins side-by-side; they'll coexist under different namespaces but show the skill twice in `/` menu. Pick one mode and stick with it unless you have a reason to mix.

Type `/` to browse what's available, or ask Claude to do something media-related ("convert this HDR clip to SDR", "build a HLS ABR ladder", "restore this VHS rip with open-source AI") — Claude auto-triggers the right skill.

## What's in it

96 skills across 9 layers:

| # | Layer | Count | Focus |
|---|---|---|---|
| 1 | FFmpeg complete | 37 | transcode, streaming, filters, HDR, codecs, protocols, broadcast MXF/IMF, DRM, 360°, VapourSynth |
| 2 | Professional companion tools | 17 | yt-dlp, MKVToolNix, Shaka, GPAC, MediaInfo, ImageMagick, ExifTool, SoX, HandBrake, whisper.cpp, Demucs, PySceneDetect, ffmpeg-normalize, MoviePy, alass, cloud upload, batch |
| 3 | OBS Studio | 4 | obs-websocket remote control, profile authoring, C++ plugin SDK, Python/Lua scripting |
| 4 | Streaming frameworks | 2 | GStreamer pipelines, MediaMTX all-protocol server |
| 5 | Broadcast IP + editorial + HDR dynamic | 6 | NDI, OTIO convert, dovi_tool, hdr10plus_tool, Blackmagic DeckLink SDI, gphoto2 DSLR tether |
| 6 | Control protocols + system audio | 9 | MIDI 1.0+2.0 UMP, OSC, DMX512/Art-Net/sACN via OLA, VISCA + ONVIF PTZ, PipeWire/JACK/Core Audio/WASAPI |
| 7 | VFX stack | 3 | Pixar USD, OpenEXR, OpenImageIO |
| 8 | Computer vision + WebRTC | 6 | OpenCV, MediaPipe Tasks, W3C WebRTC spec, Pion (Go), mediasoup (Node SFU), LiveKit (Go SFU) |
| 9 | 2026 open-source AI | 12 | Real-ESRGAN/SwinIR/HAT upscale, RIFE/FILM interpolation, rembg/BiRefNet/RMBG/RVM matting, Kokoro/OpenVoice/CosyVoice/Chatterbox/Bark/Orpheus/Piper/StyleTTS2/Parler TTS, Riffusion/YuE music gen, ComfyUI/FLUX-schnell/Kolors/Sana image gen, LTX-Video/CogVideoX/Mochi/Wan video gen, LivePortrait/LatentSync lipsync, Depth-Anything/MiDaS depth, PaddleOCR/EasyOCR/Tesseract 5/TrOCR, DeepFilterNet/RNNoise/Resemble Enhance denoise, CLIP/SigLIP/BLIP-2/LLaVA tagging |

Full skill catalog: [`skills/`](skills/).

**License filter on AI skills (Layer 9):** every model is Apache-2 / MIT / BSD / GPL. NC / research-only / commercial-restricted models (XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base) are explicitly documented-and-dropped in each AI skill's `references/LICENSES.md`.

## Workflows

13 end-to-end production guides in [`workflows/`](workflows/):

| Domain | Guide |
|---|---|
| 🔴 Live production | [`live-production.md`](workflows/live-production.md) |
| 📡 Streaming distribution | [`streaming-distribution.md`](workflows/streaming-distribution.md) |
| 📺 Broadcast delivery | [`broadcast-delivery.md`](workflows/broadcast-delivery.md) |
| 🎬 Editorial interchange | [`editorial-interchange.md`](workflows/editorial-interchange.md) |
| 🤖 AI enhancement | [`ai-enhancement.md`](workflows/ai-enhancement.md) |
| 🎨 AI generation | [`ai-generation.md`](workflows/ai-generation.md) |
| 🎙️ Podcast pipeline | [`podcast-pipeline.md`](workflows/podcast-pipeline.md) |
| 🎭 VFX pipeline | [`vfx-pipeline.md`](workflows/vfx-pipeline.md) |
| 🌈 HDR workflows | [`hdr-workflows.md`](workflows/hdr-workflows.md) |
| 🎞️ VOD post-production | [`vod-post-production.md`](workflows/vod-post-production.md) |
| 🔍 Analysis + QC | [`analysis-quality.md`](workflows/analysis-quality.md) |
| 🔊 Audio production | [`audio-production.md`](workflows/audio-production.md) |
| 📥 Acquisition + archive | [`acquisition-archive.md`](workflows/acquisition-archive.md) |

Master index: [`workflows/index.md`](workflows/index.md).

## Requirements

Every helper script is stdlib-only Python 3 (runs via `uv run`) and shells out to the real CLI. Install only what your workflows actually need:

| Skill family | External tool |
|---|---|
| `ffmpeg-*` | `ffmpeg`, `ffprobe`, `ffplay` — use a full-featured build (`brew install ffmpeg`, `apt install ffmpeg`, `winget install Gyan.FFmpeg`). Some skills require specific build flags: `--enable-libvidstab` (`ffmpeg-stabilize`), `--enable-libvmaf` (`ffmpeg-quality`), `--enable-libzimg` (`ffmpeg-hdr-color`), `--enable-librist` (`ffmpeg-rist-zmq`), OpenColorIO (`ffmpeg-ocio-colorpro`), libplacebo (for GPU tonemap). |
| `media-ytdlp` | `yt-dlp` |
| `media-whisper` | `whisper.cpp` or `faster-whisper` |
| `media-demucs` | `demucs` |
| `media-mkvtoolnix` | `mkvmerge`, `mkvextract`, `mkvpropedit` |
| `media-gpac` | `MP4Box` |
| `media-shaka` | `packager` (Shaka) |
| `media-handbrake` | `HandBrakeCLI` |
| `media-imagemagick` | `magick` (ImageMagick 7+) |
| `media-exiftool` | `exiftool` |
| `media-mediainfo` | `mediainfo` |
| `media-sox` | `sox` |
| `media-scenedetect` | `scenedetect` |
| `media-subtitle-sync` | `alass` or `ffsubsync` |
| `media-ffmpeg-normalize` | `ffmpeg-normalize` |
| `media-moviepy` | `moviepy` |
| `media-batch` | `parallel` (GNU parallel) |
| `media-cloud-upload` | `curl` / `aws` / `rclone` per provider |
| `hdr-dovi-tool` | `dovi_tool` |
| `hdr-hdr10plus-tool` | `hdr10plus_tool` |
| `media-dmx` | `ola` / `olad` daemon |
| `gphoto2-tether` | `gphoto2` (libgphoto2) |
| `decklink-tools` | Blackmagic Desktop Video driver |
| `ndi-tools` | NDI Tools runtime (Vizrt/NewTek) |
| `vfx-usd` | `usdpython` + `usdview` |
| `vfx-oiio` | `oiiotool`, `iinfo`, `iconvert` |
| `vfx-openexr` | OpenEXR CLI + libOpenEXR |

**Layer 9 AI skills** require Python + a model runtime (PyTorch or similar). Each AI skill's `references/` documents exact model install paths and GPU requirements. Most benefit significantly from a CUDA / Metal / ROCm-capable GPU.

Claude Code ≥ 2.1.60 required for the plugin system.

## Architecture

- **Skills are sealed** — one folder, one `SKILL.md`, optional `scripts/` and `references/`. No cross-skill imports. Copy a folder, get a working skill.
- **SKILL.md bodies ≤ 500 lines** — deep reference material lives in `references/<topic>.md` and loads on demand.
- **Helper scripts are stdlib Python 3** — PEP 723 inline deps, `--dry-run`, `--verbose`, exact command printed to stderr before executing.
- **Gotchas front-loaded** — every SKILL.md has a Gotchas section with the exact production traps LLMs get wrong from training data alone (wrong pixel format, missing `-movflags +faststart`, `-sc_threshold 0` for HLS, `aac_adtstoasc` for TS→MP4, ASS `&HAABBGGRR` color order, `zscale=t=linear→format=gbrpf32le` sandwich for PQ↔HLG, `fieldmatch→decimate` IVTC order, `repeat-headers=1` for streaming HEVC, `hvc1` vs `hev1` tags, `cbcs` scheme for unified Widevine+PlayReady+FairPlay DRM).

See [`CLAUDE.md`](CLAUDE.md) for contributor development instructions.

## Contributing

Scaffold + validate new skills via the authoring harness in `.claude/skills/skill-creator`:

```bash
# Scaffold
uv run .claude/skills/skill-creator/scripts/scaffold.py \
  --name <new-skill> \
  --output skills \
  --with-scripts \
  --with-references \
  --description "What it does. Use when the user asks to X, Y, or Z."

# Validate
uv run .claude/skills/skill-creator/scripts/validate.py skills/<new-skill>
```

Exit codes: `0` clean, `2` warnings only (acceptable), `1` spec violation (must fix).

Full contributor guide: [`CLAUDE.md`](CLAUDE.md).

## Release

Current: [v1.0.0](https://github.com/damionrashford/media-os/releases/tag/v1.0.0). See [`CHANGELOG.md`](CHANGELOG.md).

Third-party marketplaces do not auto-update. Pull new versions with:

```
/plugin marketplace update media-os
```

## License

[MIT](LICENSE). FFmpeg itself is LGPL 2.1+ / GPL 2+ depending on build ([ffmpeg.org/legal.html](https://ffmpeg.org/legal.html)). Each companion tool and AI model carries its own license — see each skill's `references/`.

## Related

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) — the runtime
- [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugins) — plugin spec
- [Agent Skills spec](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — the standard skills conform to
