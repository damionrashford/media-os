# Media OS Workflows — Master Index

**What the 107-skill suite can actually do, end to end.**

This directory documents every production-grade workflow the Media OS supports. Each entry below links to a dedicated workflow document with the exact skill chain, the commands each step runs, the variants, and the gotchas that break real pipelines.

The structure mirrors how professional media teams are actually organized: **acquire → analyze → edit → color → deliver → distribute → monitor**, plus the specialist verticals (live production, broadcast IP, AI, VFX, interactive control).

---

## Quick navigation

| Domain | Workflow doc |
|---|---|
| 🔴 Live production | [`live-production.md`](live-production.md) — OBS + NDI + MediaMTX + MIDI + DMX + PTZ + audio routing |
| 📡 Streaming distribution | [`streaming-distribution.md`](streaming-distribution.md) — HLS / DASH / RTMP / SRT / WHIP / RIST + DRM + CDN |
| 📺 Broadcast delivery | [`broadcast-delivery.md`](broadcast-delivery.md) — MXF / IMF + HDR dynamic metadata + DeckLink SDI |
| 🎬 Editorial interchange | [`editorial-interchange.md`](editorial-interchange.md) — OTIO + FCP / Premiere / Resolve / AAF + MKVToolNix + GPAC |
| 🤖 AI enhancement | [`ai-enhancement.md`](ai-enhancement.md) — upscale + interpolate + denoise + matte + depth (open-source only) |
| 🎨 AI generation | [`ai-generation.md`](ai-generation.md) — TTS + image gen + video gen + music gen + lipsync + OCR + tagging |
| 🎙️ Podcast pipeline | [`podcast-pipeline.md`](podcast-pipeline.md) — Whisper + Demucs + loudness normalize + captions |
| 🎭 VFX pipeline | [`vfx-pipeline.md`](vfx-pipeline.md) — USD + OpenEXR + OIIO + OCIO ACES |
| 🌈 HDR workflows | [`hdr-workflows.md`](hdr-workflows.md) — HDR10 / HDR10+ / Dolby Vision / HLG authoring + tone-mapping |
| 🎞️ VOD post-production | [`vod-post-production.md`](vod-post-production.md) — transcode + color + stabilize + denoise + captions |
| 🔍 Analysis + QC | [`analysis-quality.md`](analysis-quality.md) — probe + MediaInfo + VMAF + scenedetect + cropdetect + silencedetect |
| 🔊 Audio production | [`audio-production.md`](audio-production.md) — SoX + Demucs + DeepFilterNet + audio routing + MIDI + OSC |
| 📥 Acquisition + archive | [`acquisition-archive.md`](acquisition-archive.md) — yt-dlp + DeckLink + gphoto2 + ExifTool + MediaInfo |

---

## What the full stack can do

### Acquire media from anywhere

- **Any web video site** (1,000+ sites) → `media-ytdlp`
- **Screen / webcam / mic** → `ffmpeg-capture`
- **SDI broadcast input** → `decklink-tools`
- **DSLR tethered capture** → `gphoto2-tether`
- **NDI network source** → `ndi-tools`
- **RTSP camera** → `ffmpeg-streaming`, `mediamtx-server`
- **PTZ camera** → `ptz-visca` / `ptz-onvif`

### Transcode anything to anything

- **Every major codec**: H.264, HEVC, AV1, VP9, VP8, ProRes, DNxHD/HR, FFV1, CineForm, XAVC, JPEG2000, H.266/VVC
- **Every major container**: MP4, MKV, MOV, WebM, TS, MXF, IMF, HLS, DASH, CMAF, FLV, GXF, AVI
- **GPU-accelerated**: NVENC, QSV, VAAPI, VideoToolbox, AMF, Vulkan → `ffmpeg-hwaccel`
- **Codec deep-dives**: `ffmpeg-transcode` + `ffmpeg-docs` verification

### Edit video programmatically

- **Cut / trim / concat**: `ffmpeg-cut-concat`
- **Speed ramps / reverse / slow-mo**: `ffmpeg-speed-time`
- **Frame interpolation (AI)**: `media-interpolate` (RIFE / FILM)
- **Scene detection**: `media-scenedetect`
- **Programmatic Python editing**: `media-moviepy`
- **MKV surgery**: `media-mkvtoolnix`
- **MP4/CMAF surgery**: `media-gpac`
- **Editorial round-trip**: `otio-convert` (Premiere/FCP/Resolve/Avid)

### Apply every major video filter

- **All 293 FFmpeg filters** covered in `ffmpeg-video-filter`, `ffmpeg-audio-filter`, `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`
- **Procedural expressions**: `ffmpeg-geq-expr`
- **VapourSynth frame-server filtering**: `ffmpeg-vapoursynth`

### Color — from LUT to ACES

- **`.cube` / `.3dl` / Hald CLUT LUTs**: `ffmpeg-lut-grade`
- **OpenColorIO + ACES**: `ffmpeg-ocio-colorpro`
- **HDR10 / HDR10+ / Dolby Vision / HLG**: `ffmpeg-hdr-color`
- **HDR dynamic metadata authoring**: `hdr-dovi-tool`, `hdr-hdr10plus-tool`

### Audio — from loudness to binaural

- **EBU R128 loudness**: `ffmpeg-audio-filter` (single), `media-ffmpeg-normalize` (batch)
- **Binaural / HRTF / surround**: `ffmpeg-audio-spatial`
- **Stem separation**: `media-demucs`
- **AI denoise**: `media-denoise-ai` (DeepFilterNet / RNNoise / Resemble Enhance)
- **Classic audio ops**: `media-sox`
- **MIDI / OSC control**: `media-midi`, `media-osc`
- **System audio routing**: `audio-pipewire` (Linux), `audio-jack` (cross-platform), `audio-coreaudio` (macOS), `audio-wasapi` (Windows)

### Subtitles + captions

- **Soft-mux / burn-in / extract / convert**: `ffmpeg-subtitles`
- **CEA-608 / 708 broadcast captions**: `ffmpeg-captions`
- **AI transcription** (Whisper): `media-whisper`
- **Auto-sync**: `media-subtitle-sync` (alass / ffsubsync)

### VFX + 3D

- **Pixar USD composition**: `vfx-usd`
- **OpenEXR deep / multi-part / multi-view**: `vfx-openexr`
- **OpenImageIO 100+ format I/O**: `vfx-oiio`
- **OCIO color managed read/write**: `ffmpeg-ocio-colorpro`, `vfx-oiio`
- **360° VR / stereoscopic 3D**: `ffmpeg-360-3d`

### AI — every major open-source model

**Strict license filter: OSI-approved open source + commercial-safe only.** See each skill's `references/LICENSES.md` for the explicit NC/research-only exclusions.

- **Super-resolution**: `media-upscale` — Real-ESRGAN, SwinIR, HAT
- **Frame interpolation**: `media-interpolate` — RIFE, FILM
- **Background matting**: `media-matte` — rembg, BiRefNet, RMBG-2.0, RobustVideoMatting
- **Depth estimation**: `media-depth` — Depth-Anything v2, MiDaS
- **TTS + voice cloning**: `media-tts-ai` — Kokoro, OpenVoice, CosyVoice, Chatterbox, Bark, Orpheus, Piper, StyleTTS2, Parler
- **Music + SFX generation**: `media-musicgen` — Riffusion, YuE
- **Image generation**: `media-sd` — ComfyUI, FLUX-schnell, Kolors, Sana
- **Video generation**: `media-svd` — LTX-Video, CogVideoX, Mochi, Wan
- **Talking head / lipsync**: `media-lipsync` — LivePortrait, LatentSync
- **Audio denoise**: `media-denoise-ai` — DeepFilterNet, RNNoise, Resemble Enhance
- **OCR**: `media-ocr-ai` — PaddleOCR, EasyOCR, Tesseract 5, TrOCR
- **Zero-shot tagging + captioning**: `media-tag` — CLIP, SigLIP, BLIP-2, LLaVA
- **Speech-to-text**: `media-whisper` — whisper.cpp, faster-whisper
- **Stem separation**: `media-demucs`

### Broadcast IP + hardware

- **NDI over IP** (Vizrt): `ndi-docs`, `ndi-tools`
- **Blackmagic DeckLink SDI**: `decklink-docs`, `decklink-tools`
- **DSLR tether**: `gphoto2-tether`
- **HDR dynamic metadata authoring**: `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `hdr-dynmeta-docs`
- **MXF OP1a / IMF delivery**: `ffmpeg-mxf-imf`

### Live production — every control surface

- **OBS remote control**: `obs-websocket` (auto-discovers URL/password)
- **OBS config authoring**: `obs-config`
- **OBS native plugins**: `obs-plugins`
- **OBS Python/Lua scripts**: `obs-scripting`
- **MIDI 1.0 + 2.0 UMP**: `media-midi`
- **OSC wire protocol**: `media-osc`
- **DMX512 / Art-Net / sACN** (stage lighting): `media-dmx` via OLA
- **PTZ cameras**: `ptz-visca` (UDP:52381), `ptz-onvif` (SOAP + WS-Discovery)

### Real-time streaming frameworks

- **GStreamer pipelines**: `gstreamer-pipeline`, `gstreamer-docs`
- **MediaMTX all-protocol server**: `mediamtx-server` (RTSP/RTMP/HLS/SRT/WebRTC/WHIP/WHEP from one YAML)
- **WebRTC spec + SFUs**: `webrtc-spec`, `webrtc-pion` (Go), `webrtc-mediasoup` (Node), `webrtc-livekit` (Go + JWT minter)

### Computer vision pipelines

- **OpenCV Mat / dnn / tracking / calib3d**: `cv-opencv`
- **MediaPipe Tasks** (face / hand / pose / gesture / segmentation / LLM): `cv-mediapipe`

### Package + DRM + deliver

- **HLS AES-128 / DASH CENC / ClearKey**: `ffmpeg-drm`
- **Widevine / PlayReady / FairPlay**: `media-shaka`
- **MP4Box / CMAF surgery**: `media-gpac`
- **MKV authoring**: `media-mkvtoolnix`
- **Smart presets**: `media-handbrake`
- **Cloud upload**: `media-cloud-upload` (Cloudflare Stream, Mux, Bunny, YouTube, S3)
- **Batch scale**: `media-batch` (GNU parallel)

### Analyze + QC + debug

- **ffprobe deep analysis**: `ffmpeg-probe`
- **MediaInfo pro diagnostics**: `media-mediainfo`
- **VMAF / PSNR / SSIM**: `ffmpeg-quality`
- **Scene detect / crop detect / silence detect**: `ffmpeg-detect`, `media-scenedetect`
- **ffplay debugging + scopes**: `ffmpeg-playback`
- **Bitstream repair / analysis**: `ffmpeg-bitstream`
- **EXIF / IPTC / XMP / GPS metadata**: `media-exiftool`
- **Image manipulation / introspection**: `media-imagemagick`

---

## Cross-layer workflow stacks

Real pipelines combine skills from every layer. Representative chains:

### Podcast → polished deliverable
```
media-whisper  →  ffmpeg-subtitles  →  media-demucs  →
media-ffmpeg-normalize  →  media-cloud-upload
```

### Live show with MIDI + lighting + PTZ
```
obs-config (scene setup)  →  obs-websocket (auto-discover)  →
media-midi (controller input)  →  media-dmx (stage lights) +
ptz-visca (camera moves)  →  mediamtx-server (multi-protocol egress)
```

### Broadcast IMF delivery with Dolby Vision
```
decklink-tools (SDI ingest)  →  ffmpeg-probe (HDR check)  →
hdr-dovi-tool (RPU profile 7 to 8.1)  →  ffmpeg-hdr-color  →
ffmpeg-ocio-colorpro (ACES pass)  →  ffmpeg-captions  →
ffmpeg-mxf-imf (IMF CPL)  →  media-shaka (optional DRM)  →
media-cloud-upload (delivery platform)
```

### Full AI restoration of archive footage
```
media-ytdlp (acquire)  →  ffmpeg-detect (cropdetect) →
media-denoise-ai (DeepFilterNet audio)  →
media-upscale (Real-ESRGAN video)  →
media-interpolate (RIFE 24→60fps)  →
media-matte (rembg background removal, optional) →
ffmpeg-hdr-color (SDR tone map)  →
ffmpeg-transcode (modern delivery)
```

### Editorial round-trip with conform
```
otio-docs (pick adapter)  →  otio-convert (Premiere XML → Resolve DRP)  →
ffmpeg-probe (verify conformed media)  →
media-mediainfo (deep stream diagnostics)  →
ffmpeg-transcode (flatten to masters)
```

### VFX-aware color pass
```
vfx-oiio (iinfo on source EXR sequence)  →
vfx-openexr (verify multi-part / deep channels)  →
ffmpeg-ocio-colorpro (ACES config)  →
ffmpeg-transcode (ProRes master)
```

### AI-generated explainer video
```
media-tts-ai (Kokoro voiceover)  →  media-sd (FLUX-schnell slides)  →
media-svd (LTX-Video B-roll)  →  media-lipsync (LivePortrait talking head)  →
media-musicgen (Riffusion background)  →  ffmpeg-cut-concat (assemble)  →
media-ffmpeg-normalize (loudness)  →  media-cloud-upload
```

### Multi-protocol live fanout
```
ffmpeg-capture (screen + mic)  →  ffmpeg-hwaccel (NVENC)  →
ffmpeg-whip (WebRTC sub-second path)  +
mediamtx-server (ingest + fanout to HLS + RTSP + SRT)  →
media-cloud-upload (CDN distribution)
```

---

## How to use this documentation

- **Plan**: skim the domain table, pick the workflow matching what you're doing, read the workflow doc end-to-end.
- **Execute**: each workflow doc lists the exact commands and skills; invoke them in order. Helper scripts use `--dry-run` and `--verbose` — use them to inspect commands before running.
- **Debug**: every workflow doc has a Gotchas section front-loading the mistakes a production pipeline hits. Read it *before* the problem appears, not after.
- **Compose**: workflows chain. The "Cross-layer workflow stacks" above are starting points; most real pipelines are hybrids.

---

## Conventions across workflow docs

- **Skill references** use the `skill-name` format and link to the folder.
- **Commands** are copy-pasteable, dependency-checked, and use the helper scripts bundled with each skill whenever available.
- **Variants** note alternative paths for common constraints (e.g. "no GPU? use x264 instead of NVENC").
- **Gotchas** are the production landmines: exact flag orders, pixel format traps, build flag requirements, license pitfalls.
- **License notes** on AI workflows list the dropped-commercial-use models so you don't accidentally ship a non-compliant dependency.
