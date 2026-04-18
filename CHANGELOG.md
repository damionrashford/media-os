# Changelog

All notable changes to the Media OS plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-04-17

### Changed

- **Reverted to single-plugin architecture.** The 96 individual single-skill plugin entries added in v1.1.0 are removed. The marketplace now has ONE plugin (`media-os`) containing all 96 skills — the canonical Claude Code plugin pattern (1 plugin = 1 installable unit).
- `.claude-plugin/marketplace.json` shrunk from 97 entries to 1 (48 lines total).
- Removed `metadata.pluginRoot` (only relevant when individual entries existed).

### Added

- **Single-skill copy-install documented.** Every skill folder at `skills/<name>/` is self-contained (sealed, stdlib-only, no cross-skill imports). Users can grab individual skills without the plugin: `cp -r media-os/skills/ffmpeg-hdr-color ~/.claude/skills/`. This is the way to use "just one skill" — it's a skill-level operation, not a plugin-level one.

### Rationale

Claude Code plugins bundle skills; skills themselves are the installable unit within a plugin. Shipping 96 plugins each containing 1 skill created doubled invocations (`/ffmpeg-hdr-color:ffmpeg-hdr-color`) and bloated the marketplace. The standard pattern is: one plugin wraps all related skills, and anyone who wants to lift out a single skill copies the folder.

## [1.1.0] — 2026-04-17

### Added

- **Single-skill install support.** Every one of the 96 skills is now independently installable as its own standalone plugin from the same marketplace. Users can install the full bundle (`/plugin install media-os@media-os`) OR cherry-pick individual skills (`/plugin install ffmpeg-hdr-color@media-os`, `/plugin install obs-websocket@media-os`, etc.).
- **`.claude-plugin/marketplace.json`** expanded from 1 entry to 97 entries: the bundle + 96 individual single-skill plugins. Each individual entry uses `strict: false` with `"source": "./skills/<name>"` and `"skills": ["./"]`, so skill folders stay sealed and require no per-skill `plugin.json`.
- **README documentation** for both install modes with a comparison table.

### Changed

- Marketplace metadata + plugin manifest bumped to v1.1.0.

## [1.0.0] — 2026-04-17

### Added — initial release

96 production skills across 9 layers, distributed as a Claude Code plugin + self-hosted marketplace.

**Layer 1 — FFmpeg complete (38 skills)**
- Core editing + conversion: `ffmpeg-transcode`, `ffmpeg-cut-concat`, `ffmpeg-video-filter`, `ffmpeg-audio-filter`, `ffmpeg-subtitles`, `ffmpeg-frames-images`, `ffmpeg-streaming`, `ffmpeg-capture`, `ffmpeg-hwaccel`, `ffmpeg-probe`, `ffmpeg-bitstream`, `ffmpeg-playback`
- Visual + color: `ffmpeg-hdr-color`, `ffmpeg-lut-grade`, `ffmpeg-ocio-colorpro`, `ffmpeg-chromakey`, `ffmpeg-compose-mask`, `ffmpeg-lens-perspective`, `ffmpeg-stabilize`, `ffmpeg-denoise-restore`, `ffmpeg-ivtc`, `ffmpeg-speed-time`
- Audio specialized: `ffmpeg-audio-fx`, `ffmpeg-audio-spatial`, `ffmpeg-captions`
- Streaming specialized: `ffmpeg-whip`, `ffmpeg-rist-zmq`
- Analysis + authoring: `ffmpeg-detect`, `ffmpeg-quality`, `ffmpeg-metadata`, `ffmpeg-synth`, `ffmpeg-geq-expr`, `ffmpeg-ocr-logo`
- Immersive + broadcast: `ffmpeg-360-3d`, `ffmpeg-mxf-imf`, `ffmpeg-drm`
- Infrastructure: `ffmpeg-docs`, `ffmpeg-vapoursynth`

**Layer 2 — Professional companion tools (17 skills)**
- `media-ytdlp`, `media-whisper`, `media-demucs`, `media-mkvtoolnix`, `media-gpac`, `media-shaka`, `media-handbrake`, `media-moviepy`, `media-ffmpeg-normalize`, `media-mediainfo`, `media-scenedetect`, `media-subtitle-sync`, `media-imagemagick`, `media-exiftool`, `media-sox`, `media-batch`, `media-cloud-upload`

**Layer 3 — OBS Studio full stack (5 skills)**
- `obs-docs`, `obs-websocket`, `obs-config`, `obs-plugins`, `obs-scripting`

**Layer 4 — Frameworks + servers (4 skills)**
- `gstreamer-docs`, `gstreamer-pipeline`, `mediamtx-docs`, `mediamtx-server`

**Layer 5 — Broadcast IP + editorial (10 skills)**
- `ndi-docs`, `ndi-tools`, `otio-docs`, `otio-convert`, `hdr-dynmeta-docs`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `decklink-docs`, `decklink-tools`, `gphoto2-tether`

**Layer 6 — Low-level control protocols + system audio (11 skills)**
- Control: `media-midi`, `media-osc`, `media-dmx`, `ptz-docs`, `ptz-visca`, `ptz-onvif`
- System audio: `audio-routing-docs`, `audio-pipewire`, `audio-jack`, `audio-coreaudio`, `audio-wasapi`

**Layer 7 — VFX stack (3 skills)**
- `vfx-usd`, `vfx-openexr`, `vfx-oiio`

**Layer 8 — Computer vision + WebRTC (6 skills)**
- `cv-opencv`, `cv-mediapipe`, `webrtc-spec`, `webrtc-pion`, `webrtc-mediasoup`, `webrtc-livekit`

**Layer 9 — 2026 open-source AI era (12 skills)**
- Restoration: `media-upscale`, `media-interpolate`, `media-matte`, `media-depth`, `media-denoise-ai`
- Generation: `media-tts-ai`, `media-sd`, `media-svd`, `media-musicgen`, `media-lipsync`
- Analysis: `media-ocr-ai`, `media-tag`

All Layer 9 skills pass a strict OSI-open + commercial-safe license filter. Models with NC / research-only / ambiguous licenses (XTTS-v2, F5-TTS, FLUX-dev, SVD, Wav2Lip, SadTalker, Meta MusicGen, Surya, CodeFormer, DAIN) are explicitly documented and dropped in each skill's `references/LICENSES.md`.

### Documentation
- 13 domain workflow guides under `workflows/` covering live production, streaming distribution, broadcast delivery, editorial interchange, AI enhancement, AI generation, podcast pipeline, VFX pipeline, HDR workflows, VOD post-production, analysis + QC, audio production, and acquisition + archive.
- Master workflow index at `workflows/index.md`.
- `CLAUDE.md` — development instructions for contributors authoring new skills.
- `README.md` — user-facing overview + install flow.

### Architecture
- Distributed as a single `media-os` plugin via a self-hosted marketplace.
- Every helper script is stdlib-only Python 3 with PEP 723 inline deps (runs via `uv run`).
- Every script supports `--dry-run` and `--verbose`.
- Skill folders are sealed: no cross-skill imports.
- SKILL.md bodies kept under 500 lines; deep reference material lives in `references/<topic>.md` loaded on demand.
