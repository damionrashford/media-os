# Changelog

All notable changes to the Media OS plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] — 2026-05-17

### Added — routed modes dispatch (the modes pattern overlay)

Media OS now ships with a router-and-modes dispatch layer on top of the existing skills + agents + hooks. The orchestrator (main-thread Claude) no longer picks skills opportunistically — every media production intent is routed deterministically to the right specialist via a per-task playbook.

- **`skills/media-pipeline-router/SKILL.md`** — auto-loads on any media production intent (~140 trigger phrases packed into the description). Reads `_shared.md` + the matched mode file from disk on every dispatch, composes the prompt, and spawns the right specialist via `Agent()`. The deterministic dispatcher.
- **`modes/_shared.md`** — cross-cutting prefix prepended to every dispatch. Carries: operator scope, plugin layout source-of-truth, full tool inventory (moprobe / moqc / mosafe + every Bash CLI), output-root template (`${MEDIA_WORK_DIR}/modes/<mode>/{date}_{slug}/`), the FFmpeg-flag hard rules LLMs get wrong from training data alone (movflags, sc_threshold, aac_adtstoasc, hvc1/hev1, zscale sandwich for PQ↔HLG, cbcs vs cenc), the AI license filter (Apache-2 / MIT / BSD / GPL only), and idempotent re-run rules.
- **`modes/<mode>.md`** — 13 routed playbooks, one per production domain. Each declares its specialist (architect / probe / qc / hdr / encoder / live / delivery), trigger phrases, required + optional inputs, output path template, the per-step pipeline, the literal output schema, and the per-mode quality bar. Modes shipped:
  - `live-production` (live) — OBS + NDI + DeckLink + PTZ + RTMP/SRT/RIST/WHIP
  - `streaming-distribution` (delivery) — HLS / DASH / CMAF / LL-HLS + Widevine/PlayReady/FairPlay cbcs DRM + CDN upload
  - `broadcast-delivery` (delivery, approval-gated) — DPP AS-11 / Netflix IMF / ProRes / IMX50 / XDCAM HD422 / MXF OP1a
  - `editorial-interchange` (architect) — Premiere ↔ Resolve ↔ Avid ↔ FCP via FCPXML / AAF / EDL / OTIO
  - `ai-enhancement` (architect) — upscale (Real-ESRGAN / SwinIR / HAT), interpolate (RIFE / FILM), denoise, matte (BiRefNet / rembg / RVM), depth (Depth-Anything), lipsync (LivePortrait / LatentSync)
  - `ai-generation` (architect) — image (FLUX-schnell / Kolors / Sana), video (LTX-Video / CogVideoX / Mochi / Wan), TTS (Kokoro / OpenVoice / Piper), music (Riffusion / YuE)
  - `podcast-pipeline` (architect) — record-to-master, script-to-podcast (TTS), or existing-to-master with EBU R128 loudness + captions
  - `vfx-pipeline` (architect) — EXR / DPX / USD conform through ACES + OCIO to ProRes 4444 / J2K IMF
  - `hdr-mastering` (hdr) — HDR10 static, HDR10+ dynamic (JSON sidecar mux), Dolby Vision profiles 5 / 7 / 8.4, HLG, SDR tone-map
  - `vod-post-production` (encoder) — H.264 / H.265 / AV1 / ProRes / DNxHR with VMAF gate + 2-pass support
  - `analysis-quality` (qc) — VMAF + SSIM + PSNR + loudness + freeze / black / silence detection with per-event timestamps
  - `audio-production` (architect) — PipeWire / JACK / Core Audio / WASAPI routing, multitrack mix, repair (DeepFilterNet / Demucs), MIDI/OSC control bridge
  - `acquisition-archive` (probe) — probe-batch, ingest-card, tether-capture (gphoto2), archive-verify (hash-tree)
- **`hooks/scripts/dispatch-audit.py` + SubagentStop registration** — every dispatch logs one JSON line to `${MEDIA_WORK_DIR}/modes/dispatch.log` (timestamp, mode, specialist, duration, exit status, transcript path). Observability for the dispatch trace.
- **CI checks for the modes layer** — validates `_shared.md` exists, asserts 13 mode files, verifies every mode's `**Subagent**` line points at a real `agents/<name>.md`, confirms the dispatch-audit hook is executable.

### Changed

- Plugin + marketplace manifests bumped to v2.1.0.
- Marketplace tags now include `modes`, `routed-multi-agent`, `dispatch` for discoverability.

### Rationale

v2.0 made the plugin active (hooks, agents, CLIs). v2.1 makes it **deterministic** — the router auto-loads on media production intent and forces the dispatch contract (read `_shared.md`, read mode file, compose, spawn) every turn. Without the router, the orchestrator picks skills opportunistically and forgets cross-cutting rules (`mosafe`-wrap, license filter, deterministic output paths) every few turns. With the router, every dispatch goes through the same four-step contract and lands its artifact at a deterministic, overwrite-safe path. Modes are the configurable surface (add a task type = one new mode file + one routing-table row); specialists are fixed identities (almost never change); `_shared.md` is the cross-cutting prefix (edit once, every mode inherits). Pattern sourced from [github.com/damionrashford/modes](https://github.com/damionrashford/modes).

---

## [2.0.0] — 2026-04-17

### Added — orchestrator agents, safety hooks, CLI toolbelt, media watcher

Major release. The plugin is no longer "just a bag of skills" — it's the full Claude Code plugin feature surface wired around the media stack.

- **7 orchestrator agents** (`agents/`) that preload the right skills for a domain and arrive with tool restrictions:
  - `architect` — designs end-to-end pipelines before any command runs
  - `probe` — forensic file inspection (color, HDR side-data, GOP, captions, timecode)
  - `qc` — VMAF + SSIM + PSNR + loudness + freeze/black/silence gating
  - `hdr` — HDR10 / HDR10+ / Dolby Vision / PQ↔HLG / ACES/OCIO
  - `encoder` — rate-control math, pixel format, container flags, hwaccel
  - `live` — obs-websocket, RTMP/SRT/RIST/WHIP, NDI, DeckLink, PTZ
  - `delivery` — HLS/DASH packaging, DRM (cbcs), CDN upload, IMF/MXF
- **4 lifecycle hooks** (`hooks/`) that catch classic FFmpeg footguns:
  - `SessionStart` — detects installed CLIs + ffmpeg build flags (libvmaf, libzimg, libvidstab, librist, etc.), caches for 24 h
  - `UserPromptSubmit` — auto-probes media files named in the prompt
  - `PreToolUse(Bash)` — blocks in-place overwrites, flags missing `-movflags +faststart`, missing `-sc_threshold 0` on HLS, missing `aac_adtstoasc` on TS→MP4, conflicting CRF + bitrate
  - `PostToolUse(Bash)` — probes ffmpeg outputs and flags zero-duration / truncated files
- **3 PATH-level CLI tools** (`bin/`) installed on plugin activation:
  - `moprobe` — one-shot probe (compact / color / streams / JSON modes)
  - `moqc` — automated QC gate (VMAF/SSIM/PSNR) with configurable thresholds and `--format json`
  - `mosafe` — standalone version of the pre-ffmpeg validator, usable in any shell or CI
- **1 background monitor** (`monitors/incoming-watch`) that polls `INCOMING_MEDIA_DIR` for new media files and surfaces them to Claude with an auto-probe suggestion.
- **13 userConfig fields** in `plugin.json` covering encode defaults, VMAF target, OBS connection, Hugging Face/Shaka/Cloudflare/Mux/Bunny tokens, incoming-media directory, and safety toggles.

### Changed

- Marketplace + plugin manifest bumped to v2.0.0.
- README rewritten to document agents, hooks, bin/, monitors, and userConfig alongside skills.

### Rationale

v1.x shipped 96 skills as passive capabilities Claude would auto-load. v2.0 makes the plugin active: it inspects the environment at session start, injects probe context on prompts, catches destructive ffmpeg commands before they run, verifies outputs after they write, and offers domain-specialized agents that preload the right skills instead of making Claude page them in mid-task. The CLI toolbelt (moprobe/moqc/mosafe) gives users a shell-callable surface that works OUTSIDE the agent too — usable in CI, Makefiles, cron jobs, or terminal one-liners.

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
