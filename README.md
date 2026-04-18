# Media OS — Claude Code Plugin + Marketplace

**The most complete media-workflow skill suite ever built for an AI agent, distributed as a Claude Code plugin.** 96 self-contained [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) inside one [Claude Code plugin](https://docs.claude.com/en/docs/claude-code/plugins), shipped via a self-hosted [Claude Code marketplace](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces). Install with `/plugin marketplace add damionrashford/media-os` → `/plugin install media-os@media-os`.

**Layer 1 — FFmpeg complete (38 skills):** every major FFmpeg capability, 293 filters, all container + codec + protocol surfaces.

**Layer 2 — Professional companion tools (17 skills):** yt-dlp, MKVToolNix, Shaka Packager, MP4Box/GPAC, MediaInfo, ImageMagick, ExifTool, SoX, HandBrake, whisper.cpp, Demucs, PySceneDetect, ffmpeg-normalize, MoviePy, ccextractor, alass, cloud upload (Cloudflare Stream, Mux, Bunny, YouTube, S3), GNU parallel batch.

**Layer 3 — OBS Studio full stack (5 skills):** docs, websocket remote-control, profile + scene-collection authoring, C++ plugin SDK, Python/Lua scripting.

**Layer 4 — Frameworks + servers (4 skills):** GStreamer (the other major media framework), MediaMTX (all-protocol media server — HLS/RTSP/RTMP/SRT/WebRTC from one daemon).

**Layer 5 — Broadcast IP + editorial (9 skills):** NDI SDK (Vizrt), OpenTimelineIO (Premiere/FCP/Resolve/Avid round-trip), HDR dynamic metadata (dovi_tool + hdr10plus_tool), Blackmagic DeckLink SDI, gphoto2 DSLR tethering.

**Layer 6 — Low-level control protocols (9 skills):** MIDI 1.0+2.0/UMP, OSC wire protocol, DMX512/Art-Net/sACN stage lighting (via OLA), VISCA + ONVIF PTZ camera control. Plus 5 system-audio routing skills: PipeWire (Linux), JACK (cross-platform), Core Audio (macOS), WASAPI (Windows), unified docs.

**Layer 7 — VFX stack (3 skills):** Pixar USD, OpenEXR, OpenImageIO — where ffmpeg stops and film-VFX pipelines start.

**Layer 8 — Computer vision + WebRTC (6 skills):** OpenCV (Mat/dnn/tracking/calib3d), MediaPipe Tasks (face/hand/pose/gesture/segmentation/LLM), W3C+IETF WebRTC specs, Pion (Go), mediasoup (Node SFU), LiveKit (Go SFU with full SDK stack + pure-stdlib JWT minter).

**Layer 9 — 2026 AI era (12 skills, strict open-source + commercial-safe filter):** Real-ESRGAN/SwinIR/HAT super-resolution, RIFE/FILM frame interpolation, rembg/BiRefNet/RMBG-2.0/RobustVideoMatting matting, Kokoro+OpenVoice+CosyVoice+Chatterbox+Bark+Orpheus+Piper+StyleTTS2+Parler TTS & voice cloning, Riffusion/YuE music gen, ComfyUI + FLUX-schnell + Kolors + Sana image gen, LTX-Video + CogVideoX + Mochi + Wan video gen, LivePortrait + LatentSync lip-sync, Depth-Anything v2 + MiDaS depth, PaddleOCR + EasyOCR + Tesseract 5 + TrOCR modern OCR, DeepFilterNet + RNNoise + Resemble Enhance audio denoise, CLIP + SigLIP + BLIP-2 + LLaVA tagging. **Every NC / research-only / commercial-restricted model (XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, MusicGen, SDXL/SD3 base) explicitly documented-and-dropped** with reasoning in each skill's `references/LICENSES.md`.

Transcoding, streaming (HLS / DASH / RTMP / SRT / WHIP / RIST), video + audio filters (all 293 filters in `ffmpeg-filters`), HDR tone-mapping, LUT color grading, inverse telecine, chromakey / greenscreen, video stabilization, AI denoise + super-resolution, scene detection, metadata + chapters + cover art, closed captions (CEA-608/708), DRM (AES-128, CENC, Widevine, PlayReady, FairPlay), 360° VR + stereoscopic 3D, VMAF / PSNR / SSIM quality metrics, broadcast MXF + IMF delivery, OpenColorIO ACES workflows, OCR + logo removal, binaural audio, speech-to-text transcription, stem separation, synthetic test sources, frame extraction, GPU acceleration (NVENC / QSV / VAAPI / VideoToolbox / AMF / Vulkan), bitstream repair, ffprobe + MediaInfo deep analysis, ffplay debugging — every doc section on ffmpeg.org mapped to an owning skill, every major complementary CLI tool wrapped with production-grade recipes.

> **Scope:** 96 workflow skills (plus `skill-creator` dev harness in `.claude/skills/`). **Dependencies:** `ffmpeg`, `ffprobe`, `ffplay` required for the FFmpeg layer; other tools per-skill and optional for their respective layers. **Zero** Python package requirements for helper scripts (stdlib only). **Zero** cross-folder imports — each skill is a sealed directory. Every AI skill in Layer 9 passes a strict OSI-open + commercial-safe license filter; NC / research-only / ambiguously-licensed models are explicitly documented-and-dropped in each skill's `references/LICENSES.md`.

---

## Table of Contents

- [Why this exists](#why-this-exists)
- [Install](#install)
- [Workflow documentation](#workflow-documentation)
- [The 96 skills](#the-96-skills)
- [Coverage matrix](#coverage-matrix)
- [How triggering works](#how-triggering-works)
- [Example workflows](#example-workflows)
- [Requirements](#requirements)
- [Design notes](#design-notes)
- [Validation](#validation)
- [Contributing](#contributing)
- [License](#license)

---

## Why this exists

FFmpeg is the engine of digital media, but it is also one of the most unforgiving CLI tools on earth. A missing `-movflags +faststart`, a wrong pixel format, an ASS color in RGB instead of BGR, a dropped `-sc_threshold 0`, and your pipeline silently produces garbage. LLMs hallucinate FFmpeg flags constantly.

Beyond FFmpeg, a real media pipeline needs a dozen more tools — yt-dlp to acquire, MKVToolNix to edit MKV precisely, Shaka Packager for Widevine DRM, MediaInfo for pro diagnostics, whisper.cpp for subtitles, Demucs for stem separation, ExifTool for metadata, HandBrake for smart encoding presets, OCIO for color science, ffmpeg-normalize for batch loudness, MoviePy for programmatic editing. None of these are ffmpeg. All of them are essential.

This suite solves both. Every skill:

- **Encodes verified recipes** from the canonical source (ffmpeg.org docs live-verified via the bundled `ffmpeg-docs` skill, plus each companion tool's authoritative documentation).
- **Front-loads the gotchas** — the exact traps that break real pipelines: `yuv420p` for playback, `-sc_threshold 0` for HLS GOPs, `aac_adtstoasc` for TS→MP4, `hwdownload,format=nv12` for GPU↔CPU, ASS `&HAABBGGRR` color ordering, `zscale=t=linear→format=gbrpf32le` tonemap sandwich, `-nostdin` for ffmpeg in batch, `cbcs` scheme for FairPlay+Widevine unified DRM, `fieldmatch→decimate` IVTC order, OCIO libocio build requirement, vid.stab `--enable-libvidstab` build flag, whisper 16 kHz mono WAV requirement, Shaka Packager KID uniqueness rule, HandBrake preset family choice, MoviePy 2.x API change.
- **Ships a runnable helper script** — stdlib-only Python with PEP 723 inline deps, `--dry-run`, `--verbose`, the exact command printed before executing.
- **Is fully self-contained** — one folder, one `SKILL.md`, one helper script, one reference doc, no imports. Copy the folder, get the whole skill.

Built for [Anthropic Claude Code](https://docs.claude.com/en/docs/claude-code/overview), the [Claude Agent SDK](https://docs.claude.com/en/docs/agents-and-tools/agent-sdk/overview), and any agent runtime that understands the [Agent Skills spec](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/getting-started).

---

## Install

This repo ships as a Claude Code **plugin + marketplace**. One plugin, 96 skills, one install command.

### Option 1 — As a Claude Code plugin (recommended)

Inside any Claude Code session:

```
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

That's it. Claude Code fetches the marketplace catalog from this repo (via `.claude-plugin/marketplace.json`), installs the `media-os` plugin (`.claude-plugin/plugin.json`), and all 96 skills become available project-wide.

To scope to a single project:

```
/plugin install media-os@media-os --scope project
```

To enable/disable:

```
/plugin list
/plugin disable media-os
/plugin enable media-os
```

To pull updates:

```
/plugin marketplace update media-os
```

### Option 2 — Local-path install (for development)

From a clone of this repo:

```
/plugin marketplace add /absolute/path/to/FFMPEG
/plugin install media-os@media-os
```

Claude Code reads the local marketplace.json, installs from the same path. Edits to `skills/<skill>/SKILL.md` show up live on `/plugin reload`.

### Option 3 — Raw-copy install (no plugin system)

If you prefer to bypass the plugin system and copy skills directly (legacy behavior):

```bash
git clone https://github.com/damionrashford/media-os.git
cp -r FFMPEG/skills/* /path/to/your/project/skills/
```

### Verify

After install, type `/` in Claude Code. You should see 96 entries across every prefix (`ffmpeg-`, `media-`, `obs-`, `gstreamer-`, `mediamtx-`, `ndi-`, `otio-`, `hdr-`, `decklink-`, `gphoto2-`, `ptz-`, `audio-`, `vfx-`, `cv-`, `webrtc-`). Or ask Claude: *"Which media skills are available?"*

### Marketplace + plugin manifests

- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) — marketplace metadata (name: `media-os`, one plugin entry)
- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) — plugin manifest (name: `media-os`, points `skills` field at `./skills/`)

---

## Workflow documentation

Cross-layer workflow guides live in [`workflows/index.md`](workflows/index.md) — a master index linking to 13 domain-specific walkthroughs (each 350-530 lines), covering every major media pipeline the suite supports:

| Domain | Doc |
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

Each doc has the same structure: skills involved, step-by-step pipeline with real commands, variants, gotchas (the production landmines), an end-to-end example script, cross-references.

---

## The 96 skills

> 9 layers. Each layer is self-contained — use the ones you need. The FFmpeg + companions core (Layers 1-2) is the historical suite; Layers 3-9 extend it into OBS, other media frameworks, broadcast IP, control protocols, VFX, CV, WebRTC, and the 2026 open-source AI era.

## Layer 1 — FFmpeg complete (38 skills)

### 🎬 Core editing & conversion (12 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 1 | [`ffmpeg-transcode`](skills/ffmpeg-transcode) | Codecs + containers (H.264 / HEVC / AV1 / VP9 / ProRes / AAC / Opus) |
| 2 | [`ffmpeg-cut-concat`](skills/ffmpeg-cut-concat) | Trim / split / segment / concatenate |
| 3 | [`ffmpeg-video-filter`](skills/ffmpeg-video-filter) | Common `-vf`: scale, crop, overlay, drawtext, deinterlace |
| 4 | [`ffmpeg-audio-filter`](skills/ffmpeg-audio-filter) | loudnorm, EQ, resample, mix, channels |
| 5 | [`ffmpeg-subtitles`](skills/ffmpeg-subtitles) | Burn-in, soft-mux, extract, convert |
| 6 | [`ffmpeg-frames-images`](skills/ffmpeg-frames-images) | Frames, thumbnails, sprite sheets, GIFs |
| 7 | [`ffmpeg-streaming`](skills/ffmpeg-streaming) | HLS / DASH / RTMP / SRT / tee |
| 8 | [`ffmpeg-capture`](skills/ffmpeg-capture) | Screen / webcam / mic recording |
| 9 | [`ffmpeg-hwaccel`](skills/ffmpeg-hwaccel) | NVENC / QSV / VAAPI / VideoToolbox / AMF / Vulkan |
| 10 | [`ffmpeg-probe`](skills/ffmpeg-probe) | ffprobe JSON analysis + HDR detection |
| 11 | [`ffmpeg-bitstream`](skills/ffmpeg-bitstream) | `-bsf` filters without re-encode |
| 12 | [`ffmpeg-playback`](skills/ffmpeg-playback) | `ffplay` preview + scopes |

### 🎨 Visual effects & color (10 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 13 | [`ffmpeg-hdr-color`](skills/ffmpeg-hdr-color) | HDR10 / HDR10+ / HLG / DoVi → SDR; zscale, tonemap, libplacebo |
| 14 | [`ffmpeg-lut-grade`](skills/ffmpeg-lut-grade) | `.cube` / `.3dl` LUTs, Hald CLUT, selectivecolor |
| 15 | [`ffmpeg-ocio-colorpro`](skills/ffmpeg-ocio-colorpro) | OpenColorIO + ACES pipeline |
| 16 | [`ffmpeg-chromakey`](skills/ffmpeg-chromakey) | Greenscreen / chromakey / despill |
| 17 | [`ffmpeg-compose-mask`](skills/ffmpeg-compose-mask) | Advanced masking + channel ops |
| 18 | [`ffmpeg-lens-perspective`](skills/ffmpeg-lens-perspective) | Lens correction, perspective, vignette |
| 19 | [`ffmpeg-stabilize`](skills/ffmpeg-stabilize) | vid.stab 2-pass, deshake |
| 20 | [`ffmpeg-denoise-restore`](skills/ffmpeg-denoise-restore) | nlmeans, bm3d, DNN super-resolution |
| 21 | [`ffmpeg-ivtc`](skills/ffmpeg-ivtc) | Inverse telecine, deinterlace variants |
| 22 | [`ffmpeg-speed-time`](skills/ffmpeg-speed-time) | Speed ramps, minterpolate slow-mo, reverse |

### 🔊 Audio specialized (3 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 23 | [`ffmpeg-audio-fx`](skills/ffmpeg-audio-fx) | Chorus, flanger, echo, LADSPA/LV2 plugins |
| 24 | [`ffmpeg-audio-spatial`](skills/ffmpeg-audio-spatial) | HRTF binaural, sofalizer, surround upmix |
| 25 | [`ffmpeg-captions`](skills/ffmpeg-captions) | CEA-608/708 broadcast captions |

### 📡 Streaming specialized (2 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 26 | [`ffmpeg-whip`](skills/ffmpeg-whip) | WebRTC sub-second live (ffmpeg 7+) |
| 27 | [`ffmpeg-rist-zmq`](skills/ffmpeg-rist-zmq) | RIST contribution + ZMQ live filter-graph control |

### 🧪 Analysis + authoring (6 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 28 | [`ffmpeg-detect`](skills/ffmpeg-detect) | cropdetect / silencedetect / scdet / idet → parse → act |
| 29 | [`ffmpeg-quality`](skills/ffmpeg-quality) | libvmaf / PSNR / SSIM measurement |
| 30 | [`ffmpeg-metadata`](skills/ffmpeg-metadata) | Tags, chapters, cover art, dispositions |
| 31 | [`ffmpeg-synth`](skills/ffmpeg-synth) | SMPTE bars, testsrc, sine tone, silence |
| 32 | [`ffmpeg-geq-expr`](skills/ffmpeg-geq-expr) | Procedural expression filters (geq, aeval, lut2) |
| 33 | [`ffmpeg-ocr-logo`](skills/ffmpeg-ocr-logo) | OCR, logo detection, QR encode/decode |

### 🎥 Immersive + broadcast (3 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 34 | [`ffmpeg-360-3d`](skills/ffmpeg-360-3d) | 360° VR projections + stereoscopic 3D |
| 35 | [`ffmpeg-mxf-imf`](skills/ffmpeg-mxf-imf) | Broadcast MXF + IMF Netflix delivery |
| 36 | [`ffmpeg-drm`](skills/ffmpeg-drm) | HLS AES-128 + DASH CENC + ClearKey |

### 🔧 Infrastructure (2 FFmpeg-native)

| # | Skill | Purpose |
|---|---|---|
| 37 | [`ffmpeg-docs`](skills/ffmpeg-docs) | **Live-search ffmpeg.org documentation** (prevents hallucinated flags) |
| 38 | [`ffmpeg-vapoursynth`](skills/ffmpeg-vapoursynth) | VapourSynth Python-based frame-server filtering |

## Layer 2 — Professional companion tools (17 skills)

### 🌐 Media acquisition + AI (3 companion)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 39 | [`media-ytdlp`](skills/media-ytdlp) | Download from 1,000+ sites | yt-dlp |
| 40 | [`media-whisper`](skills/media-whisper) | Speech-to-text → SRT/VTT subtitles | whisper.cpp / faster-whisper |
| 41 | [`media-demucs`](skills/media-demucs) | AI stem separation (vocals/drums/bass) | Demucs / Spleeter |

### 🎞️ Authoring / packaging companions (6)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 42 | [`media-mkvtoolnix`](skills/media-mkvtoolnix) | MKV authoring (split / merge / edit metadata) | MKVToolNix |
| 43 | [`media-gpac`](skills/media-gpac) | Advanced MP4/CMAF surgery | MP4Box / GPAC |
| 44 | [`media-shaka`](skills/media-shaka) | Commercial DRM (Widevine / PlayReady / FairPlay) | Shaka Packager |
| 45 | [`media-handbrake`](skills/media-handbrake) | Smart transcode presets | HandBrake CLI |
| 46 | [`media-moviepy`](skills/media-moviepy) | Programmatic Python video editing | MoviePy |
| 47 | [`media-ffmpeg-normalize`](skills/media-ffmpeg-normalize) | Batch EBU R128 loudness | ffmpeg-normalize |

### 🔍 Analysis + sync companions (3)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 48 | [`media-mediainfo`](skills/media-mediainfo) | Deep container/stream diagnostics | MediaInfo |
| 49 | [`media-scenedetect`](skills/media-scenedetect) | Reliable scene-change detection | PySceneDetect |
| 50 | [`media-subtitle-sync`](skills/media-subtitle-sync) | Auto-sync SRT to video audio | alass / ffsubsync |

### 🖼️ Image + metadata companions (2)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 51 | [`media-imagemagick`](skills/media-imagemagick) | Image manipulation (200+ formats) | ImageMagick |
| 52 | [`media-exiftool`](skills/media-exiftool) | EXIF / IPTC / XMP / GPS metadata | ExifTool |

### 🎚️ Audio companions (1)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 53 | [`media-sox`](skills/media-sox) | Audio effects + format ops | SoX |

### 🚀 Scale + delivery companions (2)

| # | Skill | Purpose | Tool |
|---|---|---|---|
| 54 | [`media-batch`](skills/media-batch) | Parallel ffmpeg at scale | GNU parallel |
| 55 | [`media-cloud-upload`](skills/media-cloud-upload) | Upload to CDN / streaming platforms | Cloudflare Stream / Mux / Bunny / YouTube / S3 |

## Layer 3 — OBS Studio full stack (5 skills)

Live-production software control: remote RPC, profile/scene authoring, native plugin SDK, Python/Lua scripting, canonical docs.

| # | Skill | Purpose |
|---|---|---|
| 56 | [`obs-docs`](skills/obs-docs) | Live-search docs.obsproject.com + wiki + obs-websocket protocol reference |
| 57 | [`obs-websocket`](skills/obs-websocket) | obs-websocket v5 RPC — auto-discovers URL/password from local OBS config |
| 58 | [`obs-config`](skills/obs-config) | Profile, scene-collection, source, scene, filter authoring via config files |
| 59 | [`obs-plugins`](skills/obs-plugins) | C++ plugin SDK — sources / outputs / encoders / services / filters |
| 60 | [`obs-scripting`](skills/obs-scripting) | Python / Lua scripting inside OBS (scene automation, hotkeys, properties) |

## Layer 4 — Frameworks + servers (4 skills)

The other media frameworks FFmpeg doesn't replace: GStreamer pipelines, MediaMTX all-protocol server.

| # | Skill | Purpose |
|---|---|---|
| 61 | [`gstreamer-docs`](skills/gstreamer-docs) | Live-search gstreamer.freedesktop.org — plugins, elements, pads, caps |
| 62 | [`gstreamer-pipeline`](skills/gstreamer-pipeline) | gst-launch-1.0 + gst-inspect pipelines: WebRTCBin, hlssink, decodebin |
| 63 | [`mediamtx-docs`](skills/mediamtx-docs) | Live-search MediaMTX docs — YAML config, all-protocol server |
| 64 | [`mediamtx-server`](skills/mediamtx-server) | RTSP/RTMP/HLS/SRT/WebRTC/WHIP/WHEP ingest+egress from one YAML config + /v3/* control API |

## Layer 5 — Broadcast IP + editorial + HDR dynamic metadata (10 skills)

The professional-delivery slice FFmpeg alone doesn't cover: NDI over IP, editorial round-trip, HDR10+/Dolby Vision NAL authoring, Blackmagic SDI, DSLR tether.

### 📡 NDI (Network Device Interface — Vizrt)

| # | Skill | Purpose |
|---|---|---|
| 65 | [`ndi-docs`](skills/ndi-docs) | Official NDI SDK docs lookup (Advanced SDK, Tools, Streams) |
| 66 | [`ndi-tools`](skills/ndi-tools) | `ndi-record` / `ndi-find` / NDI Test Patterns / Studio Monitor / FFmpeg libndi_newtek |

### 🎬 OpenTimelineIO (editorial interchange)

| # | Skill | Purpose |
|---|---|---|
| 67 | [`otio-docs`](skills/otio-docs) | OpenTimelineIO docs — schema, adapters, media linker |
| 68 | [`otio-convert`](skills/otio-convert) | `otioconvert` round-trip between Premiere XML / FCP XML / Resolve / AAF / EDL / CMX3600 |

### 🌈 HDR dynamic metadata

| # | Skill | Purpose |
|---|---|---|
| 69 | [`hdr-dynmeta-docs`](skills/hdr-dynmeta-docs) | HDR10+ + Dolby Vision metadata spec docs (SMPTE 2094) |
| 70 | [`hdr-dovi-tool`](skills/hdr-dovi-tool) | Dolby Vision RPU extract/inject/convert (profile 7 to 8.1), NAL surgery |
| 71 | [`hdr-hdr10plus-tool`](skills/hdr-hdr10plus-tool) | HDR10+ dynamic-metadata extract/inject, JSON generation |

### 🎥 Hardware I/O

| # | Skill | Purpose |
|---|---|---|
| 72 | [`decklink-docs`](skills/decklink-docs) | Blackmagic DeckLink SDK docs (IDeckLinkInput/IDeckLinkOutput) |
| 73 | [`decklink-tools`](skills/decklink-tools) | `bmdcapture` / `bmdplayback` + FFmpeg decklink_input/output devices |
| 74 | [`gphoto2-tether`](skills/gphoto2-tether) | DSLR tethered capture — Canon/Nikon/Sony/Fuji remote shutter via libgphoto2 |

## Layer 6 — Low-level control protocols + system audio routing (11 skills)

The control plane professional studios run on: MIDI 1.0/2.0, OSC, DMX512/Art-Net/sACN, PTZ (VISCA + ONVIF), plus every major platform's system audio graph.

### 🎛️ Control protocols

| # | Skill | Purpose |
|---|---|---|
| 75 | [`media-midi`](skills/media-midi) | MIDI 1.0 + MIDI 2.0 UMP — CoreMIDI / ALSA / WinMM / `amidi` / `sendmidi` / `rtpmidid` |
| 76 | [`media-osc`](skills/media-osc) | OSC 1.0/1.1 wire protocol — `oscsend`/`oscdump`, TouchOSC, Reaper, Max/MSP |
| 77 | [`media-dmx`](skills/media-dmx) | DMX512 / Art-Net / sACN via Open Lighting Architecture (`ola_dev_info`, `ola_streaming_client`) |
| 78 | [`ptz-docs`](skills/ptz-docs) | PTZ camera protocol docs — Sony VISCA, VISCA-over-IP (UDP:52381), ONVIF |
| 79 | [`ptz-visca`](skills/ptz-visca) | VISCA-over-IP — pan/tilt/zoom/preset control of PTZ cameras |
| 80 | [`ptz-onvif`](skills/ptz-onvif) | ONVIF Profile-S/T — WS-Discovery + PTZ + media profile + RTSP URL retrieval |

### 🔊 System audio routing

| # | Skill | Purpose |
|---|---|---|
| 81 | [`audio-routing-docs`](skills/audio-routing-docs) | Unified cross-platform audio-graph routing reference |
| 82 | [`audio-pipewire`](skills/audio-pipewire) | Linux — `pw-cli`, `pw-link`, `wpctl`, virtual sinks, PulseAudio compat |
| 83 | [`audio-jack`](skills/audio-jack) | JACK cross-platform low-latency audio graph — `jack_lsp`, `jack_connect` |
| 84 | [`audio-coreaudio`](skills/audio-coreaudio) | macOS — AUHAL, aggregate devices, BlackHole/Loopback virtual cables |
| 85 | [`audio-wasapi`](skills/audio-wasapi) | Windows — WASAPI loopback, VB-Cable, VoiceMeeter, exclusive-mode capture |

## Layer 7 — VFX stack (3 skills)

Where FFmpeg stops and film-VFX pipelines start: USD scene description, OpenEXR deep/multi-part imagery, OpenImageIO ingest.

| # | Skill | Purpose |
|---|---|---|
| 86 | [`vfx-usd`](skills/vfx-usd) | Pixar USD — composition (LIVRPS), `usdcat` / `usdview` / `usdedit` |
| 87 | [`vfx-openexr`](skills/vfx-openexr) | OpenEXR — deep images, multi-part, multi-view, `exrheader` / `exrinfo` / `exrenvmap` |
| 88 | [`vfx-oiio`](skills/vfx-oiio) | OpenImageIO — `oiiotool` / `iconvert` / `iinfo`; 100+ formats, color-managed read/write |

## Layer 8 — Computer vision + WebRTC (6 skills)

The CV plumbing real-time AI pipelines need, plus the full WebRTC stack (spec + SFU + client).

### 👁️ Computer vision

| # | Skill | Purpose |
|---|---|---|
| 89 | [`cv-opencv`](skills/cv-opencv) | OpenCV — Mat / cv.dnn / tracking / calib3d / optical flow |
| 90 | [`cv-mediapipe`](skills/cv-mediapipe) | MediaPipe Tasks — face / hand / pose / gesture / segmentation / LLM-inference |

### 🌐 WebRTC

| # | Skill | Purpose |
|---|---|---|
| 91 | [`webrtc-spec`](skills/webrtc-spec) | W3C WebRTC + IETF RFCs (RFC 8866 SDP, RFC 9725 WHIP), ICE / DTLS / SRTP / SCTP |
| 92 | [`webrtc-pion`](skills/webrtc-pion) | Pion (Go) — pure-Go WebRTC stack for custom SFU/MCU servers |
| 93 | [`webrtc-mediasoup`](skills/webrtc-mediasoup) | mediasoup (Node SFU) — server-side media router, simulcast/SVC |
| 94 | [`webrtc-livekit`](skills/webrtc-livekit) | LiveKit (Go SFU) — room API, server SDK, pure-stdlib HS256 JWT minter |

## Layer 9 — 2026 open-source AI era (12 skills)

Everything an AI pipeline needs, 2026-caliber — with a **strict OSI-open + commercial-safe license filter**. Every skill's `references/LICENSES.md` enumerates the NC / research-only / ambiguously-licensed models explicitly dropped.

### 🔬 Super-resolution + temporal

| # | Skill | Purpose | Open-source models |
|---|---|---|---|
| 95 | [`media-upscale`](skills/media-upscale) | 2x/4x AI upscaling | Real-ESRGAN (BSD-3), SwinIR (Apache-2), HAT (Apache-2) |
| 96 | [`media-interpolate`](skills/media-interpolate) | Frame interpolation / slow-mo | RIFE (MIT), FILM (Apache-2). **DAIN dropped** (research-only) |

### ✂️ Matting + depth

| # | Skill | Purpose | Open-source models |
|---|---|---|---|
| 97 | [`media-matte`](skills/media-matte) | AI background removal | rembg (MIT), BiRefNet (MIT), RMBG-2.0 (Apache-2), RobustVideoMatting (GPL-3) |
| 98 | [`media-depth`](skills/media-depth) | Monocular depth estimation | Depth-Anything v2 (Apache-2), MiDaS (MIT) |

### 🎙️ Voice + audio

| # | Skill | Purpose | Open-source models |
|---|---|---|---|
| 99 | [`media-tts-ai`](skills/media-tts-ai) | TTS + zero-shot voice cloning | Kokoro (Apache-2), OpenVoice (MIT), CosyVoice (Apache-2), Chatterbox (Apache-2), Bark (MIT), Orpheus (Apache-2), Piper (MIT), StyleTTS2 (MIT), Parler (Apache-2). **XTTS-v2 + F5-TTS dropped** (CPML / NC) |
| 100 | [`media-musicgen`](skills/media-musicgen) | Music + SFX generation | Riffusion (Apache-2), YuE (Apache-2). **Meta MusicGen dropped** (CC-BY-NC) |
| 101 | [`media-denoise-ai`](skills/media-denoise-ai) | AI audio denoise + enhance | DeepFilterNet (MIT/Apache-2), RNNoise (BSD), Resemble Enhance (MIT) |

### 🖼️ Image + video generation

| # | Skill | Purpose | Open-source models |
|---|---|---|---|
| 102 | [`media-sd`](skills/media-sd) | AI image generation | ComfyUI (GPL-3), FLUX-schnell (Apache-2), Kolors (Apache-2), Sana (Apache-2). **FLUX-dev + SDXL/SD3 base dropped** (NC) |
| 103 | [`media-svd`](skills/media-svd) | AI video generation | LTX-Video (Apache-2 class), CogVideoX (Apache-2), Mochi (Apache-2), Wan (Apache-2). **Stable Video Diffusion dropped** (NC research) |

### 👄 Talking head + OCR + tagging

| # | Skill | Purpose | Open-source models |
|---|---|---|---|
| 104 | [`media-lipsync`](skills/media-lipsync) | Audio-driven face animation | LivePortrait (MIT), LatentSync (Apache-2). **Wav2Lip + SadTalker dropped** (research / non-commercial) |
| 105 | [`media-ocr-ai`](skills/media-ocr-ai) | Modern OCR | PaddleOCR (Apache-2), EasyOCR (Apache-2), Tesseract 5 (Apache-2), TrOCR (MIT). **Surya dropped** (commercial restriction) |
| 106 | [`media-tag`](skills/media-tag) | Zero-shot tagging + captioning | CLIP (MIT), SigLIP (Apache-2), BLIP-2 (BSD), LLaVA (Apache-2) |

---

## Coverage matrix

Every section of the official FFmpeg documentation maps to one or more owning skills. Gaps are auditable at a glance.

| FFmpeg doc page | Owning skill(s) |
|---|---|
| [`ffmpeg`](https://ffmpeg.org/ffmpeg.html) / [`ffmpeg-all`](https://ffmpeg.org/ffmpeg-all.html) | All ffmpeg-* skills |
| [`ffplay`](https://ffmpeg.org/ffplay.html) / [`ffplay-all`](https://ffmpeg.org/ffplay-all.html) | `ffmpeg-playback` |
| [`ffprobe`](https://ffmpeg.org/ffprobe.html) / [`ffprobe-all`](https://ffmpeg.org/ffprobe-all.html) | `ffmpeg-probe` + `media-mediainfo` |
| [`ffmpeg-codecs`](https://ffmpeg.org/ffmpeg-codecs.html) | `ffmpeg-transcode`, `ffmpeg-hwaccel`, `ffmpeg-captions` |
| [`ffmpeg-bitstream-filters`](https://ffmpeg.org/ffmpeg-bitstream-filters.html) | `ffmpeg-bitstream` |
| [`ffmpeg-formats`](https://ffmpeg.org/ffmpeg-formats.html) | `ffmpeg-transcode`, `ffmpeg-cut-concat`, `ffmpeg-streaming`, `ffmpeg-drm`, `ffmpeg-metadata`, `ffmpeg-mxf-imf`, `media-gpac`, `media-mkvtoolnix` |
| [`ffmpeg-protocols`](https://ffmpeg.org/ffmpeg-protocols.html) | `ffmpeg-streaming`, `ffmpeg-whip`, `ffmpeg-rist-zmq`, `ffmpeg-drm` |
| [`ffmpeg-devices`](https://ffmpeg.org/ffmpeg-devices.html) | `ffmpeg-capture` |
| [`ffmpeg-filters`](https://ffmpeg.org/ffmpeg-filters.html) — video | `ffmpeg-video-filter`, `ffmpeg-hdr-color`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro`, `ffmpeg-chromakey`, `ffmpeg-compose-mask`, `ffmpeg-stabilize`, `ffmpeg-denoise-restore`, `ffmpeg-ivtc`, `ffmpeg-detect`, `ffmpeg-speed-time`, `ffmpeg-synth`, `ffmpeg-360-3d`, `ffmpeg-frames-images`, `ffmpeg-subtitles`, `ffmpeg-lens-perspective`, `ffmpeg-geq-expr`, `ffmpeg-ocr-logo` |
| [`ffmpeg-filters`](https://ffmpeg.org/ffmpeg-filters.html) — audio | `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `ffmpeg-detect`, `ffmpeg-denoise-restore` |
| [`ffmpeg-filters`](https://ffmpeg.org/ffmpeg-filters.html) — quality metrics | `ffmpeg-quality` |
| [`ffmpeg-utils`](https://ffmpeg.org/ffmpeg-utils.html) | Distributed; expression language in `ffmpeg-geq-expr` |
| [`ffmpeg-scaler`](https://ffmpeg.org/ffmpeg-scaler.html) | `ffmpeg-video-filter` references |
| [`ffmpeg-resampler`](https://ffmpeg.org/ffmpeg-resampler.html) | `ffmpeg-audio-filter` references |
| [`libav*`](https://ffmpeg.org/libavfilter.html) | *Out of scope — C API for app developers, not CLI. Use [PyAV](https://github.com/PyAV-Org/PyAV) for Python bindings.* |
| [`faq`](https://ffmpeg.org/faq.html) | Distributed across skill troubleshooting sections |
| [`general`](https://ffmpeg.org/general.html) | Each skill references the relevant subset |
| [`platform`](https://ffmpeg.org/platform.html) / [`developer`](https://ffmpeg.org/developer.html) | *Out of scope — contributor docs for building ffmpeg itself.* |
| **Beyond FFmpeg** — acquisition, DRM packaging, MKV authoring, image processing, metadata, ASR, stem separation, scene detection, subtitle sync, batch, cloud delivery | All `media-*` skills |

**No gaps.** If a CLI workflow Claude needs isn't covered, it's a bug — open an issue.

---

## How triggering works

Three-tier progressive disclosure:

1. **Tier 1 (always loaded):** Each skill's `name` + `description` (~100 tokens). Claude reads all 96 at session start.
2. **Tier 2 (on activation):** Full `SKILL.md` body with workflow instructions, gotchas, examples, troubleshooting (< 5,000 tokens each).
3. **Tier 3 (on demand):** `references/*.md` — deep option catalogs loaded only when the SKILL.md explicitly says *"Read `references/X.md` when [condition]"*.

Users can also invoke manually via `/<skill-name>`.

### Real-world trigger examples

| User says | Skills activated |
|---|---|
| "Convert this HDR clip to SDR for Twitter" | `ffmpeg-hdr-color` |
| "Download this YouTube video" | `media-ytdlp` |
| "Auto-generate subtitles for my podcast" | `media-whisper` → `ffmpeg-subtitles` |
| "Package this VOD with Widevine DRM" | `media-shaka` |
| "Stabilize my GoPro footage" | `ffmpeg-stabilize` |
| "Make a karaoke track" | `media-demucs` |
| "Batch normalize 500 podcast episodes to -16 LUFS" | `media-ffmpeg-normalize` + `media-batch` |
| "Push live to YouTube" | `ffmpeg-streaming` |
| "Push live to WebRTC" | `ffmpeg-whip` |
| "IVTC this telecined DVD rip" | `ffmpeg-ivtc` |
| "VMAF score my AV1 encode" | `ffmpeg-quality` |
| "Remove the station logo from the top-right" | `ffmpeg-ocr-logo` |
| "Strip GPS from all these photos" | `media-exiftool` |
| "Split this MKV at the chapter marks" | `media-mkvtoolnix` |
| "Make me SMPTE color bars with a 1 kHz tone" | `ffmpeg-synth` |
| "Apply this ACES OCIO config" | `ffmpeg-ocio-colorpro` |
| "Upload to Cloudflare Stream" | `media-cloud-upload` |
| "Switch my OBS scene from chat" | `obs-websocket` |
| "Build a GStreamer WebRTC pipeline" | `gstreamer-pipeline` |
| "Spin up MediaMTX to ingest RTMP and egress HLS+WebRTC" | `mediamtx-server` |
| "Send this Premiere XML to DaVinci Resolve" | `otio-convert` |
| "Extract the Dolby Vision RPU from this HEVC" | `hdr-dovi-tool` |
| "Convert HDR10+ metadata from JSON to inject into HEVC" | `hdr-hdr10plus-tool` |
| "Capture from my DeckLink Duo 2" | `decklink-tools` |
| "Tether shoot from my Canon EOS" | `gphoto2-tether` |
| "Map MIDI note 36 to switch OBS scene" | `media-midi` + `obs-websocket` |
| "Drive stage lights from an Art-Net universe" | `media-dmx` |
| "Pan+zoom this PTZ camera over the network" | `ptz-visca` / `ptz-onvif` |
| "Route Chrome audio into OBS on macOS" | `audio-coreaudio` |
| "Read a USD scene and dump the stage" | `vfx-usd` |
| "Inspect this multi-part OpenEXR" | `vfx-openexr` |
| "Build a custom SFU in Go" | `webrtc-pion` |
| "Mint a LiveKit access token" | `webrtc-livekit` |
| "Upscale this 1080p clip to 4K with open-source AI" | `media-upscale` |
| "Interpolate 24→60fps without DAIN" | `media-interpolate` |
| "Remove the background from this video with RobustVideoMatting" | `media-matte` |
| "Generate a voiceover with open-source TTS" | `media-tts-ai` |
| "Generate an image with FLUX-schnell (Apache-2 only)" | `media-sd` |
| "Generate 5s of video with LTX-Video" | `media-svd` |
| "Lip-sync this audio to a photo with LivePortrait" | `media-lipsync` |
| "Generate a depth map with Depth-Anything v2" | `media-depth` |
| "OCR this PDF with PaddleOCR" | `media-ocr-ai` |
| "Clean this podcast with DeepFilterNet" | `media-denoise-ai` |
| "Auto-tag this image with CLIP" | `media-tag` |

---

## Example workflows

Full pipelines chaining multiple skills:

### Podcast → auto-captions → loudness-normalized → uploaded

```
media-whisper (transcribe → SRT) →
ffmpeg-subtitles (burn-in) →
media-ffmpeg-normalize (EBU R128 -16 LUFS) →
media-cloud-upload (push to S3)
```

### YouTube rip → scene-split → thumbnails → karaoke

```
media-ytdlp (download best quality) →
media-scenedetect (split at scene cuts) →
ffmpeg-frames-images (per-scene thumbs) →
media-demucs (vocals out) →
ffmpeg-subtitles (soft-mux vocals as track)
```

### Broadcast delivery

```
ffmpeg-probe (verify source specs) →
ffmpeg-ivtc (if telecined) →
ffmpeg-hdr-color (if HDR → SDR needed) →
ffmpeg-ocio-colorpro (ACES color pass) →
ffmpeg-captions (preserve CEA-608) →
ffmpeg-mxf-imf (deliver as MXF OP1a)
```

### Live-streaming CDN pipeline

```
ffmpeg-capture (screen + mic) →
ffmpeg-hwaccel (NVENC) →
ffmpeg-streaming (HLS ABR ladder) →
ffmpeg-drm (AES-128 encrypt) →
media-cloud-upload (deploy to Bunny CDN)
```

### AI post-production (fully open-source)

```
media-upscale (Real-ESRGAN 2x) →
media-interpolate (RIFE 24→60fps) →
media-denoise-ai (DeepFilterNet on audio) →
media-tts-ai (Kokoro voiceover) →
media-lipsync (LivePortrait to still image) →
ffmpeg-transcode (final H.264 for delivery)
```

### OBS-driven live show

```
obs-config (author scenes + profiles) →
obs-websocket (auto-discover + RPC) →
media-midi (MIDI controller triggers) →
ptz-visca (PTZ presets on scene change) →
audio-coreaudio (route app audio into OBS) →
mediamtx-server (fanout WHIP ingest to HLS+WebRTC)
```

### Broadcast IP delivery

```
decklink-tools (SDI ingest) →
ffmpeg-probe (verify HDR metadata) →
hdr-dovi-tool (extract + convert Dolby Vision profile 7 to 8.1) →
hdr-hdr10plus-tool (inject HDR10+ JSON into HEVC) →
ffmpeg-mxf-imf (deliver as IMF CPL)
```

### Editorial round-trip

```
otio-docs (pick the right adapter) →
otio-convert (Premiere XML → OTIO → Resolve DRP) →
ffmpeg-probe (verify conformed media) →
ffmpeg-transcode (flatten to deliverable)
```

### VFX-aware color pass

```
vfx-oiio (iinfo on source EXR sequence) →
vfx-openexr (verify multi-part / deep channels) →
ffmpeg-ocio-colorpro (ACES pass through OCIO config) →
ffmpeg-transcode (final ProRes master)
```

---

## Requirements

| Tool | Purpose | Required by |
|---|---|---|
| `ffmpeg` 5.0+ (7.0+ recommended) | Core engine | All `ffmpeg-*` skills |
| `ffprobe` / `ffplay` | Bundled with ffmpeg | `ffmpeg-probe`, `ffmpeg-playback` |
| `python3` 3.9+ | Helper scripts | All |
| `uv` | Optional runner for PEP 723 scripts | All |
| `yt-dlp` | Download | `media-ytdlp` |
| `whisper-cpp` or `faster-whisper` (pip) | ASR | `media-whisper` |
| `demucs` (pip) | Stem separation | `media-demucs` |
| `magick` (ImageMagick 7+) | Image ops | `media-imagemagick` |
| `exiftool` | Metadata | `media-exiftool` |
| `mediainfo` | Inspection | `media-mediainfo` |
| `mkvmerge` / `mkvextract` / `mkvpropedit` | MKV ops | `media-mkvtoolnix` |
| `sox` | Audio ops | `media-sox` |
| `HandBrakeCLI` | Smart encode | `media-handbrake` |
| `packager` (Shaka) | DRM | `media-shaka` |
| `MP4Box` (GPAC) | MP4 surgery | `media-gpac` |
| `scenedetect` (pip) | Scene cuts | `media-scenedetect` |
| `alass` / `ffsubsync` | Subtitle sync | `media-subtitle-sync` |
| `ffmpeg-normalize` (pip) | Batch loudness | `media-ffmpeg-normalize` |
| `moviepy` (pip) | Python editing | `media-moviepy` |
| `parallel` (GNU parallel) | Batch scale | `media-batch` |
| `curl` / `rclone` / `aws` | Cloud upload | `media-cloud-upload` |
| `ccextractor` | CEA-608 extraction | `ffmpeg-captions` |
| VapourSynth + plugins | Frame-server | `ffmpeg-vapoursynth` |
| libOpenColorIO in ffmpeg | OCIO filter | `ffmpeg-ocio-colorpro` |
| vid.stab in ffmpeg (`--enable-libvidstab`) | Stabilization | `ffmpeg-stabilize` |
| libvmaf in ffmpeg (`--enable-libvmaf`) | VMAF | `ffmpeg-quality` |
| libzimg in ffmpeg (`--enable-libzimg`) | zscale | `ffmpeg-hdr-color` |
| librist in ffmpeg (`--enable-librist`) | RIST | `ffmpeg-rist-zmq` |
| Claude Code | Runtime | All |

Install FFmpeg with max features:
```bash
brew install ffmpeg                      # macOS (includes most build flags)
sudo apt install ffmpeg                  # Ubuntu/Debian (stock; rebuild for niche filters)
winget install Gyan.FFmpeg               # Windows (full build)
```

---

## Design notes

### One skill per workflow

Each skill is a single workflow — not a catch-all tool. Basketball-player analogy: Claude is the player, skills are shooting / dribbling / passing. We didn't build one giant `ffmpeg` skill — we built 96 focused ones across 9 layers of the media stack.

### Sealed folders

```
<skill-name>/
├── SKILL.md              # Agent instructions (< 500 lines)
├── scripts/
│   └── <name>.py         # stdlib-only helper, PEP 723 deps
└── references/
    └── <topic>.md        # Deep reference, loaded on demand
```

No cross-folder imports. Copy one folder, get a working skill.

### Progressive disclosure

`SKILL.md` bodies stay under 500 lines. Encyclopedic content (option catalogs, recipe books) lives in `references/*.md` loaded only when the body says to.

### Stdlib-only scripts

Helper scripts use zero third-party Python packages. They shell out to the real tool (`ffmpeg`, `yt-dlp`, `magick`, etc.), parse stdout/stderr, and print the exact command before executing. Every helper has `--dry-run` + `--verbose`.

### Gotchas front-loaded

Every `SKILL.md` has a `Gotchas` section with the production-breaking traps an LLM makes from training alone: the exact flag orders, build flags, escaping rules, and silent-failure modes that matter in practice.

---

## Validation

```bash
for s in skills/*/; do
  uv run skills/skill-creator/scripts/validate.py "$s"
done
```

Current: **0 errors, 0 non-cosmetic warnings across all 96 skills**. Only remaining warning is cosmetic `description-display-truncation` (descriptions >250 chars for trigger-phrase breadth; Claude reads the full text, only the `/` menu preview is shorter).

---

## Contributing

Pattern for new skills:

```bash
uv run skills/skill-creator/scripts/scaffold.py \
  --name <kebab-name> \
  --output .claude/skills \
  --with-scripts --with-references \
  --description "What it does. Use when the user asks to X, Y, or Z."
# Fill SKILL.md + scripts/<name>.py + references/<topic>.md
uv run skills/skill-creator/scripts/validate.py skills/<name>
```

---

## License

See [LICENSE](LICENSE). FFmpeg itself is LGPL 2.1+ / GPL 2+ depending on build — see [ffmpeg.org/legal.html](https://ffmpeg.org/legal.html). Companion tools carry their own licenses.

---

## Related

- **[FFmpeg documentation](https://ffmpeg.org/documentation.html)** — canonical source.
- **[Claude Code](https://docs.claude.com/en/docs/claude-code/overview)** — the runtime.
- **[Agent Skills spec](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)** — the standard the suite conforms to.
- **[Claude Agent SDK](https://docs.claude.com/en/docs/agents-and-tools/agent-sdk/overview)** — building custom agents.

---

**Keywords:** ffmpeg, ffprobe, ffplay, gstreamer, mediamtx, obs studio, obs-websocket, obs scripting, ndi, opentimelineio, otio, dolby vision, hdr10+, dovi_tool, hdr10plus_tool, blackmagic decklink, gphoto2, tethered capture, midi, midi 2.0, ump, osc, open sound control, dmx512, art-net, sacn, ola, open lighting architecture, ptz, visca, visca over ip, onvif, ws-discovery, pipewire, jack audio, coreaudio, wasapi, virtual audio cable, pixar usd, openusd, openexr, deep exr, multi-part exr, openimageio, oiio, opencv, opencv dnn, mediapipe, mediapipe tasks, webrtc, webrtc spec, rfc 8866, rfc 9725, whip, whep, pion, mediasoup, livekit, sfu, real-esrgan, swinir, hat, rife, film frame interpolation, rembg, birefnet, rmbg-2.0, robustvideomatting, depth-anything v2, midas, kokoro tts, openvoice, cosyvoice, chatterbox, bark, orpheus, piper, styletts2, parler tts, riffusion, yue, comfyui, flux-schnell, kolors, sana, ltx-video, cogvideox, mochi, wan, liveportrait, latentsync, paddleocr, easyocr, tesseract 5, trocr, deepfilternet, rnnoise, resemble enhance, clip, siglip, blip-2, llava, open source ai, apache 2.0, mit, bsd, commercial-safe ai models, claude code, claude agent skills, anthropic, ai video editing, ai media operating system, yt-dlp, mkvtoolnix, shaka packager, mp4box, gpac, mediainfo, imagemagick, exiftool, sox, handbrake, whisper.cpp, faster-whisper, demucs, spleeter, pyscenedetect, ffsubsync, alass, ffmpeg-normalize, moviepy, ccextractor, vapoursynth, opencolorio, aces color, hdr tone-mapping, hdr10, hlg, dolby vision, lut3d, .cube lut, haldclut, chromakey, greenscreen, vid.stab, video stabilization, nlmeans, bm3d, dnn super-resolution, ai upscaling, scene detection, cropdetect, autocrop, silencedetect, blackdetect, idet, inverse telecine, nvenc, qsv, vaapi, videotoolbox, amf, vulkan, cuda, hls streaming, dash streaming, rtmp, srt, whip webrtc, rist, zmq, icecast, hls aes-128, dash cenc, clearkey, widevine, playready, fairplay, mxf, imf, smpte 2067, broadcast delivery, cea-608, cea-708, scc, mcc, subtitle sync, subtitle burn-in, ebu r128, loudnorm, vmaf, psnr, ssim, video quality metrics, 360 video, v360, vr180, stereoscopic 3d, smpte bars, testsrc, synthetic test media, speed ramp, minterpolate, reverse video, freezeframe, metadata, chapters, cover art, exif, iptc, xmp, gps metadata, mp4 chapters, mkv authoring, cmaf, fragmented mp4, hls cmaf, speech to text, auto subtitles, srt generation, karaoke, stem separation, vocals isolation, batch encoding, gnu parallel, cloud upload, cloudflare stream, mux video, bunny stream, youtube data api, aws s3, rclone, media operating system, media pipeline, ai video operating system, claude media os.
