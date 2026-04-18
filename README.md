# media-os

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-D97757?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=for-the-badge)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?logo=ffmpeg&logoColor=white&style=for-the-badge)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin&style=for-the-badge)](https://www.linkedin.com/in/damion-rashford)

![GitHub Stars](https://img.shields.io/github/stars/damionrashford/media-os?style=social)
![GitHub Forks](https://img.shields.io/github/forks/damionrashford/media-os?style=social)
![GitHub Issues](https://img.shields.io/github/issues/damionrashford/media-os?style=social)
![Last Commit](https://img.shields.io/github/last-commit/damionrashford/media-os?style=social)

**The Media OS for Claude Code.** 96 production skills + 13 workflow skills + 7 orchestrator agents + 4 safety hooks + 3 PATH-level CLIs + an incoming-media watcher. Covers FFmpeg end-to-end, OBS Studio, GStreamer, MediaMTX, broadcast IP (NDI, OpenTimelineIO, HDR dynamic metadata, DeckLink, gphoto2), control protocols (MIDI, OSC, DMX, PTZ), system audio routing, VFX (USD, OpenEXR, OpenImageIO), computer vision, WebRTC, and 2026 open-source AI media. One plugin, the full Claude Code feature surface. Or copy a single skill folder on its own.

> 🆓 **Open source under MIT.** No hosted layer, no API key to media-os itself. Bring your own ffmpeg/OBS/CDP creds.

## Why

FFmpeg is powerful but error-prone — one missing flag breaks the pipeline. Broadcast tools (NDI, DeckLink, Dolby Vision, HDR10+) aren't scriptable out of the box. AI media (upscale, interpolate, TTS, gen) is a zoo of incompatible models. **media-os** puts 96 sealed, copy-and-run skills + 7 specialist agents + pre-flight safety hooks behind Claude's natural-language interface, so a broadcast engineer / video-automation dev / live producer / AI-pipeline engineer can say what they want and Claude runs the right toolchain — with `mosafe` lint catching ffmpeg foot-guns before the command fires.

## Common workflows

Task → the skills that execute it:

| Task | Skill chain |
|---|---|
| Broadcast HLS / DASH delivery | `ffmpeg-streaming` · `ffmpeg-quality` · `media-shaka` · `ffmpeg-captions` |
| Dolby Vision / HDR10+ authoring | `ffmpeg-hdr-color` · `hdr-dovi-tool` · `hdr-hdr10plus-tool` · `ffmpeg-mxf-imf` |
| AI upscale + interpolate + denoise | `media-upscale` · `media-interpolate` · `media-denoise-ai` · `ffmpeg-transcode` |
| Live OBS + NDI + PTZ production | `obs-websocket` · `ndi-tools` · `ptz-onvif` · `media-midi` · `media-dmx` |
| Podcast: TTS → mix → normalize | `media-tts-ai` · `ffmpeg-audio-filter` · `media-ffmpeg-normalize` · `ffmpeg-captions` |
| VFX ACES conform (EXR → master) | `vfx-oiio` · `vfx-openexr` · `ffmpeg-ocio-colorpro` · `ffmpeg-transcode` |
| Editorial round-trip (Premiere ↔ Resolve ↔ Avid) | `otio-convert` · `ffmpeg-probe` · `media-mediainfo` · `ffmpeg-transcode` |

## Install

### Option 1 — Install the plugin (recommended)

```
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

All 96 skills load under the `/media-os:` namespace (e.g. `/media-os:ffmpeg-hdr-color`, `/media-os:obs-websocket`, `/media-os:media-tts-ai`). Claude auto-triggers the right skill when you describe a task.

### Option 2 — Use a single skill standalone

Every skill at `skills/<name>/` is a sealed, self-contained folder (`SKILL.md` + optional `scripts/` + `references/`). Copy just the one you want:

```bash
# Grab one skill — no plugin install needed
git clone https://github.com/damionrashford/media-os.git /tmp/media-os
cp -r /tmp/media-os/skills/ffmpeg-hdr-color ~/.claude/skills/
cp -r /tmp/media-os/skills/obs-websocket ~/.claude/skills/
```

Those skills then load directly under `/ffmpeg-hdr-color`, `/obs-websocket`, etc. — no plugin namespace, no marketplace dependency, copy-and-go.

Skill folders are sealed by design: no cross-skill imports, every script is stdlib-only Python 3 via `uv run`. Copy one folder, get a working skill.

## What's in it

96 tool-and-technique skills across 9 layers, plus 13 workflow skills that orchestrate across them:

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

## Orchestrator agents

7 domain specialists that preload the right skill set and arrive with tool restrictions. Spawn them from any Claude conversation:

| Agent | Role |
|---|---|
| `architect` | Plans end-to-end pipelines before a command runs |
| `probe` | Forensic file inspection (color, HDR side-data, GOP, captions, timecode) |
| `qc` | Automated quality gate — VMAF + SSIM + PSNR + loudness + freeze/black/silence |
| `hdr` | HDR10 / HDR10+ / Dolby Vision / PQ↔HLG / ACES/OCIO |
| `encoder` | Rate control, pixel format, container flags, hwaccel |
| `live` | OBS + RTMP/SRT/RIST/WHIP + NDI + DeckLink + PTZ |
| `delivery` | HLS/DASH packaging + DRM (cbcs) + CDN upload + IMF/MXF |

## Safety hooks

4 lifecycle hooks wired on install, catching the ffmpeg mistakes that take a pipeline down:

- **`SessionStart`** — detects installed CLIs + ffmpeg build flags (libvmaf, libzimg, libvidstab, librist, libplacebo, hwaccel backends) and surfaces gaps before the agent recommends anything.
- **`UserPromptSubmit`** — if you name a media path in your prompt, it's auto-probed and the summary is dropped into context.
- **`PreToolUse(Bash)`** — flags in-place overwrites, missing `-movflags +faststart`, missing `-sc_threshold 0` on HLS, missing `aac_adtstoasc` on TS→MP4, conflicting CRF + bitrate.
- **`PostToolUse(Bash)`** — ffprobes the output after any ffmpeg command; catches zero-duration / truncated files before you ship them.

## CLI toolbelt (on PATH after install)

The plugin's `bin/` is added to your PATH. Three tools you can call from any shell, Makefile, or CI job:

```bash
moprobe source.mov                    # compact probe
moprobe --color source.mov            # HDR/color pipeline summary
moprobe --json source.mov             # full ffprobe JSON

moqc --ref source.mov --out encoded.mp4                    # VMAF + SSIM + PSNR gate
moqc --ref source.mov --out encoded.mp4 --vmaf-min 95 --format json

mosafe ffmpeg -i in.mov -c:v libx264 -crf 23 -b:v 5M out.mp4   # preflight footguns
```

`mosafe` exits non-zero on issues — drop it in a CI step to fail builds that would have shipped broken ffmpeg commands.

## Incoming-media watcher

Set `INCOMING_MEDIA_DIR` in the plugin's userConfig and the `incoming-watch` monitor polls it for new media files. Each new, stable (mtime-quiesced) file is surfaced to Claude with a suggested probe prompt so you can triage dropped assets without asking.

## userConfig

13 fields, set at `/plugin install` time:

| Field | Purpose |
|---|---|
| `MEDIA_WORK_DIR` | Scratch dir for intermediate renders |
| `DEFAULT_ENCODE_PRESET` | x264/x265 default preset |
| `DEFAULT_VMAF_TARGET` | QC gate threshold |
| `OBS_WEBSOCKET_URL` / `OBS_WEBSOCKET_PASSWORD` | OBS control |
| `HUGGINGFACE_TOKEN` | AI skill model access |
| `SHAKA_KEY_SERVER_URL` | DRM key server |
| `CLOUDFLARE_STREAM_TOKEN` / `MUX_TOKEN_ID` / `MUX_TOKEN_SECRET` / `BUNNY_CDN_TOKEN` | CDN uploads |
| `INCOMING_MEDIA_DIR` | Directory the watcher polls |
| `SAFETY_REQUIRE_CONFIRM_OVERWRITE` | Toggle the pre-ffmpeg overwrite guard |

## Workflow skills

13 end-to-end production workflows are first-class skills you invoke by name. Both you AND Claude can trigger them — say "I need to deliver to broadcast" and Claude auto-loads `workflow-broadcast-delivery`, or type `/media-os:workflow-broadcast-delivery` directly.

| Domain | Skill |
|---|---|
| 🔴 Live production | `/media-os:workflow-live-production` |
| 📡 Streaming distribution | `/media-os:workflow-streaming-distribution` |
| 📺 Broadcast delivery | `/media-os:workflow-broadcast-delivery` |
| 🎬 Editorial interchange | `/media-os:workflow-editorial-interchange` |
| 🤖 AI enhancement | `/media-os:workflow-ai-enhancement` |
| 🎨 AI generation | `/media-os:workflow-ai-generation` |
| 🎙️ Podcast pipeline | `/media-os:workflow-podcast-pipeline` |
| 🎭 VFX pipeline | `/media-os:workflow-vfx-pipeline` |
| 🌈 HDR | `/media-os:workflow-hdr` |
| 🎞️ VOD post-production | `/media-os:workflow-vod-post-production` |
| 🔍 Analysis + QC | `/media-os:workflow-analysis-quality` |
| 🔊 Audio production | `/media-os:workflow-audio-production` |
| 📥 Acquisition + archive | `/media-os:workflow-acquisition-archive` |

Each workflow skill lists the skill chain, step-by-step pipeline, variants, and the production gotchas that break real pipelines.

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

Current: [v2.0.0](https://github.com/damionrashford/media-os/releases/tag/v2.0.0). See [`CHANGELOG.md`](CHANGELOG.md).

Third-party marketplaces do not auto-update. Pull new versions with:

```
/plugin marketplace update media-os
```

## FAQ

<details>
<summary><strong>Does media-os cost money to run?</strong></summary>

No. media-os is MIT-licensed. What costs money: the model you use with Claude Code (Anthropic billing), the external tools the skills call (most free: ffmpeg, OBS, GStreamer, MediaMTX — some paid: Blackmagic DeckLink hardware, NDI HX2 licensing, DRM key servers for Shaka). Each skill's `references/` lists licensing.
</details>

<details>
<summary><strong>Do I need all 96 skills?</strong></summary>

No — Claude auto-loads only what a given task needs, and each skill folder is sealed. If you just want Dolby Vision authoring, `cp -r skills/ffmpeg-hdr-color ~/.claude/skills/` works standalone. The plugin is the batteries-included mode; the copy-a-folder mode is the minimalist mode.
</details>

<details>
<summary><strong>What's the safety story for live encodes?</strong></summary>

Four hooks run automatically. `SessionStart` probes which ffmpeg build flags + CLIs you have installed (libvmaf, libzimg, libvidstab, librist, libplacebo, hwaccel backends) and surfaces gaps before Claude recommends anything it can't run. `PreToolUse` intercepts Bash calls and blocks common foot-guns — in-place overwrites, missing `-movflags +faststart`, missing `-sc_threshold 0` on HLS, missing `-bsf:a aac_adtstoasc` on TS→MP4 remux, conflicting `-crf` + bitrate. `PostToolUse` ffprobes every ffmpeg output to catch zero-duration / truncated files. `UserPromptSubmit` auto-probes any media path you mention.
</details>

<details>
<summary><strong>What's the difference between the 96 skills and the 13 workflow skills?</strong></summary>

The 96 skills are tool-and-technique — `ffmpeg-transcode`, `obs-websocket`, `hdr-dovi-tool`, one skill per bounded capability. The 13 workflow skills orchestrate across them — `workflow-broadcast-delivery`, `workflow-ai-enhancement`, `workflow-podcast-pipeline` — each encoding the full recipe for a domain with the right skill chain, the gotchas, and the variants.
</details>

<details>
<summary><strong>What about AI models with restrictive licenses?</strong></summary>

Every Layer-9 AI skill passes a strict OSI-open + commercial-safe filter (Apache-2 / MIT / BSD / GPL). NC / research-only / commercial-restricted models (XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base) are explicitly documented-and-dropped in each AI skill's `references/LICENSES.md` so you don't accidentally ship something you can't monetize.
</details>

<details>
<summary><strong>Can I add my own skill?</strong></summary>

Yes. Scaffold via the vendored `.claude/skills/skill-creator`, validate against its `validate.py`. See [CLAUDE.md](CLAUDE.md) for the full contributor pipeline. Every skill is a sealed folder — copy a folder, get a working skill.
</details>

## License

[MIT](LICENSE). FFmpeg itself is LGPL 2.1+ / GPL 2+ depending on build ([ffmpeg.org/legal.html](https://ffmpeg.org/legal.html)). Each companion tool and AI model carries its own license — see each skill's `references/`.

## Related

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) — the runtime
- [Claude Code plugins](https://docs.claude.com/en/docs/claude-code/plugins) — plugin spec
- [Agent Skills spec](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — the standard skills conform to

## ⭐ Star this repo

If media-os helps you ship, a star makes it easier for other engineers to find.

[![Star this repo](https://img.shields.io/github/stars/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os)

---

<!--
Machine-readable metadata for LLM + search indexers (Perplexity / ChatGPT / Claude / Google AI Overviews).
-->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "media-os",
  "description": "Production media plugin for Claude Code. 96 skills + 7 orchestrator agents + 13 workflow skills + safety hooks + CLI toolbelt covering FFmpeg, OBS Studio, GStreamer, MediaMTX, NDI, OpenTimelineIO, HDR dynamic metadata (Dolby Vision, HDR10+), Blackmagic DeckLink, MIDI/OSC/DMX/PTZ, system audio routing, VFX (USD/OpenEXR/OIIO), computer vision, WebRTC, and 2026 open-source AI media.",
  "applicationCategory": "MultimediaApplication",
  "applicationSubCategory": "VideoProduction",
  "operatingSystem": "macOS, Linux, Windows",
  "license": "https://opensource.org/licenses/MIT",
  "url": "https://github.com/damionrashford/media-os",
  "codeRepository": "https://github.com/damionrashford/media-os",
  "author": { "@type": "Person", "name": "Damion Rashford", "url": "https://github.com/damionrashford" },
  "keywords": "ffmpeg, obs-studio, gstreamer, mediamtx, broadcast, hdr, dolby-vision, hdr10-plus, video-production, video-generation, image-generation, claude-code, claude-plugin, multi-agent, audio-routing, ndi, opentimelineio, webrtc, open-source-ai, media-production",
  "softwareRequirements": "Claude Code 2.1.60+, Python 3.10+, uv, ffmpeg",
  "programmingLanguage": ["Python"],
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
</script>
