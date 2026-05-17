<div align="center">

# Media OS for Claude Code

**The complete media production toolchain for Claude Code — FFmpeg, OBS, broadcast IP, HDR, AI media. 96 production skills, 13 workflow recipes, 7 orchestrator agents, 4 safety hooks, 3 CLIs. MIT licensed.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?style=for-the-badge)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?logo=ffmpeg&logoColor=white&style=for-the-badge)](https://ffmpeg.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/damionrashford/media-os/validate.yml?style=for-the-badge&label=validate)](https://github.com/damionrashford/media-os/actions/workflows/validate.yml)

[![GitHub Stars](https://img.shields.io/github/stars/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/commits/main)

**[Install](#install) · [Skills catalog](#skills-catalog) · [Routed modes](#routed-modes) · [Workflow recipes](#workflow-recipes) · [Agents](#orchestrator-agents) · [Safety hooks](#safety-hooks) · [CLI toolbelt](#cli-toolbelt) · [FAQ](#faq)**

</div>

---

## What is Media OS?

**Media OS is a Claude Code plugin that turns natural-language requests into production-grade media pipelines.** Tell Claude *"deliver this master to HLS with VMAF ≥ 95 and Widevine DRM"* or *"set up an NDI feed from OBS to MediaMTX with a PTZ camera on cam-2"* — Media OS routes to the right skill chain, runs the right CLI with the right flags, and catches the foot-guns before they ship a broken file.

Built for **broadcast engineers, video automation developers, live producers, and AI media pipeline engineers** who want Claude's natural-language interface over the real toolchain (FFmpeg, OBS, GStreamer, MediaMTX, NDI, DeckLink, Dolby Vision authoring tools, ComfyUI, etc.) — not yet another wrapper that fails on the third edge case.

### Why this exists

- **FFmpeg is powerful but unforgiving** — one missing flag (`-movflags +faststart`, `-sc_threshold 0`, `aac_adtstoasc`) breaks the pipeline. Every skill front-loads the gotchas LLMs get wrong from training data alone.
- **Broadcast tools aren't scriptable out of the box** — NDI, DeckLink, Dolby Vision, HDR10+, OpenTimelineIO. Media OS provides scripted entry points for all of them.
- **AI media is a license minefield** — every Layer 9 AI skill ships a hard filter: only Apache-2 / MIT / BSD / GPL models. NC and research-only models are explicitly documented-and-dropped.
- **Safety hooks catch mistakes pre-flight** — `mosafe` lints FFmpeg commands before they run; `PostToolUse` re-probes every output for zero-duration / truncation.

---

## Install

### Option A — Install the full plugin (recommended)

```text
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

All **109 skills** (96 tool + 13 workflow) load under the `/media-os:` namespace. Claude auto-triggers the right skill for each request. The `bin/` CLIs (`moprobe`, `moqc`, `mosafe`) are added to your `PATH` automatically.

### Option B — Copy a single skill

Every skill at [`skills/<name>/`](skills/) is a **sealed self-contained folder** — `SKILL.md` + optional `scripts/` + `references/`, no cross-skill imports. Copy just the one you need:

```bash
git clone https://github.com/damionrashford/media-os.git /tmp/media-os
cp -r /tmp/media-os/skills/ffmpeg-hdr-color   ~/.claude/skills/
cp -r /tmp/media-os/skills/obs-websocket      ~/.claude/skills/
cp -r /tmp/media-os/skills/hdr-dovi-tool      ~/.claude/skills/
```

Standalone skills load under `/ffmpeg-hdr-color`, `/obs-websocket`, etc. — no plugin namespace, no marketplace dependency.

### Requirements

| Requirement | Version | Notes |
|---|---|---|
| Claude Code | ≥ 2.1.60 | Plugin system support |
| Python | ≥ 3.10 | All helper scripts are stdlib-only, run via `uv run` |
| FFmpeg | Recent full build | `brew install ffmpeg` / `apt install ffmpeg` / `winget install Gyan.FFmpeg` |
| External tools | Per-skill | See [Requirements](#per-skill-requirements) — install only what you use |

---

## Common workflows

The most-requested production tasks and the skill chain Media OS routes them to:

| Production task | Skills invoked (in order) |
|---|---|
| **Broadcast HLS / DASH delivery with DRM** | `ffmpeg-streaming` → `ffmpeg-quality` → `media-shaka` → `ffmpeg-captions` |
| **Dolby Vision / HDR10+ authoring** | `ffmpeg-hdr-color` → `hdr-dovi-tool` → `hdr-hdr10plus-tool` → `ffmpeg-mxf-imf` |
| **AI upscale + interpolate + denoise** | `media-upscale` → `media-interpolate` → `media-denoise-ai` → `ffmpeg-transcode` |
| **Live OBS + NDI + PTZ production** | `obs-websocket` → `ndi-tools` → `ptz-onvif` → `media-midi` → `media-dmx` |
| **Podcast: TTS → mix → normalize → captions** | `media-tts-ai` → `ffmpeg-audio-filter` → `media-ffmpeg-normalize` → `ffmpeg-captions` |
| **VFX ACES conform (EXR → master)** | `vfx-oiio` → `vfx-openexr` → `ffmpeg-ocio-colorpro` → `ffmpeg-transcode` |
| **Editorial round-trip (Premiere ↔ Resolve ↔ Avid)** | `otio-convert` → `ffmpeg-probe` → `media-mediainfo` → `ffmpeg-transcode` |
| **Streaming origin (RTMP/SRT/WHIP/RIST)** | `mediamtx-server` → `ffmpeg-rist-zmq` → `ffmpeg-whip` |
| **Lipsync + face animation** | `media-lipsync` → `media-tts-ai` → `ffmpeg-transcode` |

→ Full set of orchestrated production recipes: [Workflow recipes](#workflow-recipes).

---

## Skills catalog

**109 skills total**: 96 tool-and-technique skills across 9 layers, plus 13 end-to-end workflow recipes.

| # | Layer | Count | Coverage |
|---|---|---|---|
| **1** | [FFmpeg complete](skills/) | **37** | transcode, streaming, filters, HDR, codecs, protocols, broadcast MXF/IMF, DRM, 360°, VapourSynth |
| **2** | [Professional companion tools](skills/) | **17** | yt-dlp, MKVToolNix, Shaka Packager, GPAC, MediaInfo, ImageMagick, ExifTool, SoX, HandBrake, whisper.cpp, Demucs, PySceneDetect, ffmpeg-normalize, MoviePy, alass, cloud upload, GNU parallel |
| **3** | [OBS Studio](skills/) | **4** | obs-websocket v5, profile authoring, C++ plugin SDK, Python/Lua scripting |
| **4** | [Streaming frameworks](skills/) | **2** | GStreamer pipelines, MediaMTX all-protocol server |
| **5** | [Broadcast IP + editorial + HDR dynamic](skills/) | **6** | NDI, OpenTimelineIO, dovi_tool, hdr10plus_tool, Blackmagic DeckLink SDI, gphoto2 DSLR tether |
| **6** | [Control protocols + system audio](skills/) | **9** | MIDI 1.0 + 2.0 UMP, OSC, DMX512/Art-Net/sACN via OLA, VISCA + ONVIF PTZ, PipeWire/JACK/Core Audio/WASAPI |
| **7** | [VFX stack](skills/) | **3** | Pixar USD, OpenEXR, OpenImageIO |
| **8** | [Computer vision + WebRTC](skills/) | **6** | OpenCV, MediaPipe Tasks, W3C WebRTC spec, Pion (Go), mediasoup (Node SFU), LiveKit (Go SFU) |
| **9** | [2026 open-source AI media](skills/) | **12** | Real-ESRGAN / SwinIR / HAT upscale · RIFE / FILM interpolation · rembg / BiRefNet / RVM matting · Kokoro / OpenVoice / Piper / StyleTTS2 TTS · Riffusion music gen · ComfyUI / FLUX-schnell / Kolors image gen · LTX-Video / CogVideoX video gen · LivePortrait / LatentSync lipsync · Depth-Anything / MiDaS depth · PaddleOCR / Tesseract 5 OCR · DeepFilterNet / RNNoise denoise · CLIP / SigLIP / BLIP-2 / LLaVA tagging |
| **W** | [Workflow recipes](#workflow-recipes) | **13** | End-to-end domain orchestrators (live, streaming, broadcast, editorial, AI, podcast, VFX, HDR, VOD, QC, audio, acquisition, archive) |

→ Browse the full catalog at [`skills/`](skills/). Every skill is a sealed folder with a `SKILL.md`, optional `scripts/` (stdlib-only Python 3 via `uv run`), and optional `references/`.

---

## Routed modes

**Media OS implements the [modes pattern](https://github.com/damionrashford/modes) — a routed multi-agent dispatch system.** Say what you want; the router auto-loads on media production intent and spawns the right specialist in an isolated context with a per-task playbook.

### How dispatch works

```
USER: "encode this master for HLS with VMAF ≥ 95"
        ↓
Router skill auto-loads on intent
        ↓
Dispatch contract (4 steps, every dispatch):
  1. Read modes/_shared.md from disk
  2. Read modes/streaming-distribution.md from disk
  3. Compose prompt = _shared + mode + user_ask
  4. Agent(subagent_type="delivery",
          prompt=composed,
          description="streaming-distribution")
        ↓
delivery specialist runs in isolated context:
  - probes input, derives bitrate ladder
  - mosafe-wraps every ffmpeg invocation
  - encodes tiers, runs moqc per tier
  - packages HLS/DASH, applies cbcs DRM
  - writes artifact to deterministic path
        ↓
${MEDIA_WORK_DIR}/modes/streaming-distribution/{date}_{slug}/
```

### The 13 modes (one per production domain)

Each mode declares its specialist, trigger phrases, required + optional inputs, output schema, and quality bar. Modes are the **configurable surface** — adding a task type is one new mode file plus one routing-table row.

| Mode | Specialist | Domain |
|---|---|---|
| [`live-production`](modes/live-production.md) | `live` | OBS + NDI + DeckLink + PTZ + RTMP/SRT/RIST/WHIP |
| [`streaming-distribution`](modes/streaming-distribution.md) | `delivery` | HLS / DASH / CMAF / LL-HLS + cbcs DRM + CDN upload |
| [`broadcast-delivery`](modes/broadcast-delivery.md) | `delivery` | DPP AS-11 / Netflix IMF / ProRes / MXF OP1a (approval-gated) |
| [`editorial-interchange`](modes/editorial-interchange.md) | `architect` | Premiere ↔ Resolve ↔ Avid ↔ FCP via FCPXML / AAF / EDL / OTIO |
| [`ai-enhancement`](modes/ai-enhancement.md) | `architect` | Upscale, interpolate, denoise, matte, depth, lipsync |
| [`ai-generation`](modes/ai-generation.md) | `architect` | Image / video / TTS / music generation (license-filtered) |
| [`podcast-pipeline`](modes/podcast-pipeline.md) | `architect` | Record / script / re-master → EBU R128 + captions |
| [`vfx-pipeline`](modes/vfx-pipeline.md) | `architect` | EXR / DPX / USD through ACES + OCIO to ProRes 4444 / J2K IMF |
| [`hdr-mastering`](modes/hdr-mastering.md) | `hdr` | HDR10, HDR10+, Dolby Vision profiles 5/7/8.4, HLG, SDR tone-map |
| [`vod-post-production`](modes/vod-post-production.md) | `encoder` | H.264 / H.265 / AV1 / ProRes / DNxHR with VMAF gate |
| [`analysis-quality`](modes/analysis-quality.md) | `qc` | VMAF + SSIM + PSNR + loudness + freeze / black / silence |
| [`audio-production`](modes/audio-production.md) | `architect` | PipeWire / JACK / Core Audio / WASAPI routing, mix, repair, MIDI/OSC |
| [`acquisition-archive`](modes/acquisition-archive.md) | `probe` | Probe-batch, ingest-card, tether-capture, archive-verify |

### Chained dispatch

Multi-step intents run sequentially with artifact paths passed forward. Examples the router knows about:

| User says | Chain |
|---|---|
| "encode + deliver this master for HLS" | `vod-post-production` → `streaming-distribution` |
| "upscale + interpolate + deliver" | `ai-enhancement` → `vod-post-production` → `streaming-distribution` |
| "HDR master + broadcast deliver" | `hdr-mastering` → `broadcast-delivery` |
| "QC + deliver" | `analysis-quality` → if pass → `broadcast-delivery` |
| "VFX → HDR master" | `vfx-pipeline` → `hdr-mastering` |

### Observability

Every dispatch logs one JSON line to `${MEDIA_WORK_DIR}/modes/dispatch.log` via the `SubagentStop` audit hook — timestamp, mode, specialist, duration, exit status, transcript path. Tail it to see dispatch rate and failure patterns.

### The dispatch contract is deterministic

The router skill auto-loads on every media production intent and forces the four-step contract. The mode files are loaded fresh from disk on every dispatch — never cached, never paraphrased. Cross-cutting rules (`mosafe`-wrap every ffmpeg call, license filter on AI models, deterministic output paths, idempotent re-runs) live in `modes/_shared.md` and apply to every specialist.

### License filter on AI skills (Layer 9)

Every model shipped in a Layer 9 skill is **Apache-2 / MIT / BSD / GPL**. Models with NC / research-only / commercial-restricted licenses — **XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base** — are explicitly documented-and-dropped in each AI skill's [`references/LICENSES.md`](skills/). You don't accidentally ship something you can't monetize.

---

## Workflow recipes

13 end-to-end production workflows shipped as first-class skills. Say "I need to deliver to broadcast" and Claude auto-loads [`workflow-broadcast-delivery`](skills/workflow-broadcast-delivery), or invoke directly with `/media-os:workflow-broadcast-delivery`.

| Domain | Workflow skill |
|---|---|
| Live production | [`workflow-live-production`](skills/workflow-live-production) |
| Streaming distribution | [`workflow-streaming-distribution`](skills/workflow-streaming-distribution) |
| Broadcast delivery | [`workflow-broadcast-delivery`](skills/workflow-broadcast-delivery) |
| Editorial interchange | [`workflow-editorial-interchange`](skills/workflow-editorial-interchange) |
| AI enhancement | [`workflow-ai-enhancement`](skills/workflow-ai-enhancement) |
| AI generation | [`workflow-ai-generation`](skills/workflow-ai-generation) |
| Podcast pipeline | [`workflow-podcast-pipeline`](skills/workflow-podcast-pipeline) |
| VFX pipeline | [`workflow-vfx-pipeline`](skills/workflow-vfx-pipeline) |
| HDR mastering | [`workflow-hdr`](skills/workflow-hdr) |
| VOD post-production | [`workflow-vod-post-production`](skills/workflow-vod-post-production) |
| Analysis + QC | [`workflow-analysis-quality`](skills/workflow-analysis-quality) |
| Audio production | [`workflow-audio-production`](skills/workflow-audio-production) |
| Acquisition + archive | [`workflow-acquisition-archive`](skills/workflow-acquisition-archive) |

Each workflow skill documents the full skill chain, step-by-step pipeline, variants (e.g. live vs VOD HLS), and the production gotchas that break real pipelines.

---

## Orchestrator agents

7 domain specialists with pre-loaded skill sets and tool restrictions. Spawn from any Claude conversation:

| Agent | Specialization |
|---|---|
| [`architect`](agents/architect.md) | Plans end-to-end pipelines before any command runs |
| [`probe`](agents/probe.md) | Forensic file inspection (color, HDR side-data, GOP, captions, timecode) |
| [`qc`](agents/qc.md) | Automated quality gate — VMAF + SSIM + PSNR + loudness + freeze/black/silence detection |
| [`hdr`](agents/hdr.md) | HDR10, HDR10+, Dolby Vision, PQ↔HLG, ACES, OpenColorIO |
| [`encoder`](agents/encoder.md) | Rate control, pixel format, container flags, hardware acceleration |
| [`live`](agents/live.md) | OBS + RTMP/SRT/RIST/WHIP + NDI + DeckLink + PTZ |
| [`delivery`](agents/delivery.md) | HLS/DASH packaging + DRM (cbcs) + CDN upload + IMF/MXF |

---

## Safety hooks

4 lifecycle hooks fire automatically on install and catch the FFmpeg mistakes that take a pipeline down:

| Event | What it does |
|---|---|
| `SessionStart` | Detects installed CLIs + FFmpeg build flags (`libvmaf`, `libzimg`, `libvidstab`, `librist`, `libplacebo`, hwaccel backends) and surfaces gaps before Claude recommends anything it can't run |
| `UserPromptSubmit` | When you name a media path in your prompt, auto-probes it and drops the summary (codec, color, HDR side-data, duration, GOP) into context |
| `PreToolUse(Bash)` | Flags in-place overwrites · missing `-movflags +faststart` · missing `-sc_threshold 0` on HLS · missing `aac_adtstoasc` on TS→MP4 · conflicting `-crf` + `-b:v` |
| `PostToolUse(Bash)` | Re-`ffprobe`s the output of every FFmpeg call; catches zero-duration / truncated files before they ship |

---

## CLI toolbelt

Three commands added to your `PATH` after install. Use them from any shell, Makefile, or CI job:

### `moprobe` — compact media inspection

```bash
moprobe source.mov                    # one-line summary
moprobe --color source.mov            # HDR / color pipeline summary
moprobe --json source.mov             # full ffprobe JSON
```

### `moqc` — quality gate

```bash
moqc --ref source.mov --out encoded.mp4
moqc --ref source.mov --out encoded.mp4 --vmaf-min 95 --format json
```

Runs VMAF + SSIM + PSNR + loudness analysis. Exits non-zero if quality drops below threshold — drop it in CI.

### `mosafe` — FFmpeg pre-flight lint

```bash
mosafe ffmpeg -i in.mov -c:v libx264 -crf 23 -b:v 5M out.mp4
```

Catches conflicting flags, missing container hints, and risky overwrites **before** the command runs. Exits non-zero on detected issues. Wrap any `ffmpeg` invocation in CI: `mosafe ffmpeg ... || exit 1`.

---

## Incoming-media watcher

Set `INCOMING_MEDIA_DIR` in plugin userConfig and the `incoming-watch` monitor polls the directory for new stable (mtime-quiesced) files. Each new asset is surfaced to Claude with a suggested probe prompt — triage dropped media without asking.

---

## Configuration

16 fields, all set at `/plugin install` time:

| Field | Purpose | Default |
|---|---|---|
| `MEDIA_WORK_DIR` | Scratch directory for intermediate renders | `/tmp/media-os` |
| `DEFAULT_ENCODE_PRESET` | x264/x265 default preset | `medium` |
| `DEFAULT_VMAF_TARGET` | QC gate threshold | `93` |
| `OBS_WEBSOCKET_URL` | OBS control endpoint | `ws://localhost:4455` |
| `OBS_WEBSOCKET_PASSWORD` | OBS auth | _empty_ |
| `HUGGINGFACE_TOKEN` | AI skill model access | _empty_ |
| `SHAKA_KEY_SERVER_URL` | DRM key server for Shaka Packager | _empty_ |
| `CLOUDFLARE_STREAM_TOKEN` | Cloudflare Stream uploads | _empty_ |
| `MUX_TOKEN_ID` / `MUX_TOKEN_SECRET` | Mux uploads | _empty_ |
| `BUNNY_CDN_TOKEN` | Bunny.net Stream uploads | _empty_ |
| `INCOMING_MEDIA_DIR` | Watcher directory | _empty (disabled)_ |
| `LIVE_STREAM_URL` | Stream-health monitor target | _empty (disabled)_ |
| `RENDER_QUEUE_URL` / `RENDER_QUEUE_DIR` | Render farm monitor | _empty (disabled)_ |
| `SAFETY_REQUIRE_CONFIRM_OVERWRITE` | Toggle the pre-FFmpeg overwrite guard | `true` |

---

## Per-skill requirements

Every helper script is stdlib-only Python 3 (runs via `uv run`) and shells out to the real CLI. **Install only what your workflows actually need:**

<details>
<summary><strong>FFmpeg + companion tools</strong> (37 + 17 skills)</summary>

| Skill family | External tool | Required build flags |
|---|---|---|
| `ffmpeg-*` (most) | `ffmpeg`, `ffprobe`, `ffplay` | A full-featured build (`brew install ffmpeg`) |
| `ffmpeg-stabilize` | ffmpeg | `--enable-libvidstab` |
| `ffmpeg-quality` | ffmpeg | `--enable-libvmaf` |
| `ffmpeg-hdr-color` | ffmpeg | `--enable-libzimg` |
| `ffmpeg-rist-zmq` | ffmpeg | `--enable-librist` |
| `ffmpeg-ocio-colorpro` | ffmpeg + OpenColorIO | OCIO link |
| `ffmpeg-*` (GPU tonemap) | ffmpeg + libplacebo | `--enable-libplacebo` |
| `media-ytdlp` | `yt-dlp` | — |
| `media-whisper` | `whisper.cpp` or `faster-whisper` | — |
| `media-demucs` | `demucs` | — |
| `media-mkvtoolnix` | `mkvmerge`, `mkvextract`, `mkvpropedit` | — |
| `media-gpac` | `MP4Box` | — |
| `media-shaka` | `packager` (Shaka) | — |
| `media-handbrake` | `HandBrakeCLI` | — |
| `media-imagemagick` | `magick` (ImageMagick 7+) | — |
| `media-exiftool` | `exiftool` | — |
| `media-mediainfo` | `mediainfo` | — |
| `media-sox` | `sox` | — |
| `media-scenedetect` | `scenedetect` | — |
| `media-subtitle-sync` | `alass` or `ffsubsync` | — |
| `media-ffmpeg-normalize` | `ffmpeg-normalize` | — |
| `media-moviepy` | `moviepy` | — |
| `media-batch` | `parallel` (GNU parallel) | — |
| `media-cloud-upload` | `curl` / `aws` / `rclone` per provider | — |

</details>

<details>
<summary><strong>Broadcast IP + HDR dynamic + protocols</strong> (Layers 5 + 6)</summary>

| Skill | External tool |
|---|---|
| `hdr-dovi-tool` | `dovi_tool` |
| `hdr-hdr10plus-tool` | `hdr10plus_tool` |
| `ndi-tools` | NDI Tools runtime (Vizrt/NewTek) |
| `decklink-tools` | Blackmagic Desktop Video driver |
| `gphoto2-tether` | `gphoto2` (libgphoto2) |
| `media-dmx` | `ola` / `olad` daemon |
| `otio-convert` | `opentimelineio` |
| `ptz-onvif` / `ptz-visca` | `onvif-zeep` / VISCA over serial-or-IP |
| `media-midi` | `python-rtmidi` |
| `media-osc` | `python-osc` |

</details>

<details>
<summary><strong>VFX</strong> (Layer 7)</summary>

| Skill | External tool |
|---|---|
| `vfx-usd` | `usdpython` + `usdview` |
| `vfx-oiio` | `oiiotool`, `iinfo`, `iconvert` |
| `vfx-openexr` | OpenEXR CLI + libOpenEXR |

</details>

<details>
<summary><strong>AI media</strong> (Layer 9)</summary>

Layer 9 skills require Python + a model runtime (PyTorch or similar). Each AI skill's [`references/`](skills/) documents exact model install paths and GPU requirements. Most benefit significantly from a CUDA / Metal / ROCm-capable GPU. **All models are Apache-2 / MIT / BSD / GPL.**

</details>

---

## Architecture

- **Skills are sealed.** One folder, one `SKILL.md`, optional `scripts/` and `references/`. No cross-skill imports. Copy a folder, get a working skill.
- **SKILL.md bodies ≤ 500 lines.** Deep reference material lives in `references/<topic>.md` and loads on demand via progressive disclosure.
- **Helper scripts are stdlib Python 3.** PEP 723 inline deps (`uv run` ready), `--dry-run`, `--verbose`, the exact shell command printed to stderr before executing.
- **Gotchas front-loaded.** Every `SKILL.md` has a Gotchas section with the exact production traps LLMs get wrong from training data alone — wrong pixel format, missing `-movflags +faststart`, `-sc_threshold 0` for HLS, `aac_adtstoasc` for TS→MP4 remux, ASS `&HAABBGGRR` color order, `zscale=t=linear→format=gbrpf32le` sandwich for PQ↔HLG, `fieldmatch→decimate` IVTC order, `repeat-headers=1` for streaming HEVC, `hvc1` vs `hev1` tags, `cbcs` scheme for unified Widevine + PlayReady + FairPlay DRM.

→ Full contributor reference: [`CLAUDE.md`](CLAUDE.md).

---

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

**Quick paths:**

- 🐛 [Report a broken skill / hook / CLI](https://github.com/damionrashford/media-os/issues/new?template=bug.yml)
- 💡 [Propose a new tool-and-technique skill](https://github.com/damionrashford/media-os/issues/new?template=skill_request.yml)
- 🛤️ [Propose a new workflow recipe](https://github.com/damionrashford/media-os/issues/new?template=workflow_request.yml)
- 💬 [Show & tell / ask questions](https://github.com/damionrashford/media-os/discussions)

**Author a new skill locally:**

```bash
# Scaffold
uv run .claude/skills/skill-creator/scripts/scaffold.py \
  --name <new-skill> \
  --output skills \
  --with-scripts \
  --with-references \
  --description "What it does. Use when the user asks to X, Y, or Z."

# Validate (matches CI)
uv run .claude/skills/skill-creator/scripts/validate.py skills/<new-skill>
```

Exit codes: `0` clean · `2` warnings only (acceptable) · `1` spec violation (must fix). CI at [`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs the same checks.

---

## Release & updates

Current: **v2.0.1** — see [CHANGELOG.md](CHANGELOG.md) and [releases](https://github.com/damionrashford/media-os/releases).

Third-party marketplaces do not auto-update. Pull new versions with:

```text
/plugin marketplace update media-os
```

---

## FAQ

### Does Media OS cost money to run?

No. Media OS is MIT-licensed. The costs you incur: the Claude model you use (Anthropic billing) and the external tools the skills call (most free — FFmpeg, OBS, GStreamer, MediaMTX — some paid: Blackmagic DeckLink hardware, NDI HX2 licensing, DRM key servers for Shaka). Each skill's [`references/`](skills/) lists licensing.

### Do I need all 109 skills?

No. Claude auto-loads only what each task needs, and every skill folder is sealed. If you only want Dolby Vision authoring, `cp -r skills/ffmpeg-hdr-color ~/.claude/skills/` works standalone. The plugin install is the batteries-included mode; the copy-a-folder mode is the minimalist mode.

### What's the safety story for live encodes?

Four hooks run automatically. `SessionStart` probes which FFmpeg build flags + CLIs are installed (libvmaf, libzimg, libvidstab, librist, libplacebo, hwaccel backends) and surfaces gaps before Claude recommends anything it can't actually run. `PreToolUse` intercepts Bash calls and blocks common foot-guns — in-place overwrites, missing `-movflags +faststart`, missing `-sc_threshold 0` on HLS, missing `-bsf:a aac_adtstoasc` on TS→MP4 remux, conflicting `-crf` + bitrate. `PostToolUse` re-`ffprobe`s every FFmpeg output to catch zero-duration / truncated files. `UserPromptSubmit` auto-probes any media path you mention.

### What's the difference between the 96 skills and the 13 workflow skills?

The 96 skills are **tool-and-technique** — `ffmpeg-transcode`, `obs-websocket`, `hdr-dovi-tool` — one skill per bounded capability. The 13 workflow skills **orchestrate across them** — `workflow-broadcast-delivery`, `workflow-ai-enhancement`, `workflow-podcast-pipeline` — each encodes the full recipe for a production domain with the skill chain, the gotchas, and the variants.

### What about AI models with restrictive licenses?

Every Layer 9 AI skill passes a strict OSI-open + commercial-safe filter (Apache-2 / MIT / BSD / GPL). Restrictive models — XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base — are explicitly documented-and-dropped in each AI skill's `references/LICENSES.md` so you don't accidentally ship something you can't monetize.

### How does Media OS compare to running FFmpeg manually?

Media OS does not replace FFmpeg — it gives Claude the right vocabulary, flag combinations, and pre-flight checks for FFmpeg, OBS, GStreamer, MediaMTX, NDI, DeckLink, Dolby Vision, and 50+ other media tools. You still run the real tools; Media OS makes sure the agent calls them with the right arguments, validates the output, and catches the gotchas LLMs get wrong from training alone.

### Can I add my own skill?

Yes. Scaffold via the vendored [`.claude/skills/skill-creator`](.claude/skills/), validate with `validate.py`, ship a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md) for the full pipeline. Every skill is a sealed folder — copy a folder, get a working skill.

### Does Media OS work without an internet connection?

Yes for most skills — FFmpeg, OBS, GStreamer, NDI, DeckLink, MIDI, OSC, DMX all run locally. Internet is required for: AI model downloads (first run only, cached after), cloud upload skills (`media-cloud-upload`), DRM key server skills (`media-shaka`), and `media-ytdlp`.

### Which platforms are supported?

macOS (Apple Silicon + Intel), Linux (x86_64 + ARM), Windows (x86_64). Some skills are platform-conditional — `audio-coreaudio` is macOS-only, `audio-wasapi` is Windows-only, `audio-pipewire` and `audio-jack` are Linux-primary. Each skill's `SKILL.md` documents platform support.

---

## License

[MIT](LICENSE). FFmpeg itself is LGPL 2.1+ / GPL 2+ depending on build ([ffmpeg.org/legal.html](https://ffmpeg.org/legal.html)). Each companion tool and AI model carries its own license — see each skill's [`references/`](skills/).

## Related

- [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/overview) — the runtime
- [Claude Code plugins spec](https://docs.claude.com/en/docs/claude-code/plugins) — the plugin standard
- [Agent Skills specification](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — the skills standard
- [Media OS project site](https://damionrashford.github.io/media-os/) — full documentation + searchable skill catalog
- [LLM machine-readable index](https://damionrashford.github.io/media-os/llms.txt) — for AI agent discovery

---

<div align="center">

### ⭐ Star Media OS

If Media OS ships you a working pipeline, a star helps other engineers find it.

[![Star](https://img.shields.io/github/stars/damionrashford/media-os?style=for-the-badge&logo=github&label=Star%20on%20GitHub)](https://github.com/damionrashford/media-os/stargazers)

Built by [Damion Rashford](https://github.com/damionrashford) · [LinkedIn](https://www.linkedin.com/in/damion-rashford)

</div>

<!--
Machine-readable metadata for LLM crawlers (Perplexity, ChatGPT, Claude, Google AI Overviews) and search indexers.
-->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "@id": "https://github.com/damionrashford/media-os#software",
      "name": "Media OS for Claude Code",
      "alternateName": "media-os",
      "description": "Production media plugin for Claude Code. 96 tool-and-technique skills + 13 workflow recipes + 7 orchestrator agents + 4 safety hooks + 3 PATH-level CLIs (moprobe, moqc, mosafe) covering FFmpeg complete, OBS Studio, GStreamer, MediaMTX, NDI, OpenTimelineIO, HDR dynamic metadata (Dolby Vision, HDR10+), Blackmagic DeckLink, gphoto2, MIDI/OSC/DMX/PTZ, system audio routing (PipeWire/JACK/Core Audio/WASAPI), VFX (USD/OpenEXR/OpenImageIO), computer vision (OpenCV/MediaPipe), WebRTC (Pion/mediasoup/LiveKit), and 2026 open-source AI media with strict OSI-open license filter.",
      "applicationCategory": "MultimediaApplication",
      "applicationSubCategory": "VideoProduction",
      "operatingSystem": "macOS, Linux, Windows",
      "license": "https://opensource.org/licenses/MIT",
      "url": "https://github.com/damionrashford/media-os",
      "downloadUrl": "https://github.com/damionrashford/media-os/releases",
      "codeRepository": "https://github.com/damionrashford/media-os",
      "softwareVersion": "2.0.1",
      "softwareRequirements": "Claude Code 2.1.60+, Python 3.10+, uv, ffmpeg",
      "programmingLanguage": ["Python", "Shell"],
      "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
      "author": { "@id": "https://github.com/damionrashford#person" },
      "keywords": "ffmpeg, claude code plugin, claude code, media production, video pipeline, broadcast engineering, HDR, Dolby Vision, HDR10 plus, NDI, DeckLink, OBS Studio, GStreamer, MediaMTX, OpenTimelineIO, WebRTC, Pion, mediasoup, LiveKit, VFX, USD, OpenEXR, OpenImageIO, Real-ESRGAN, RIFE, Kokoro TTS, FLUX schnell, LTX-Video, ComfyUI, PaddleOCR, Whisper, Demucs, MIDI 2.0, OSC, DMX512, Art-Net, sACN, VISCA, ONVIF, PTZ, PipeWire, JACK, Core Audio, WASAPI, Shaka Packager, GPAC, MKVToolNix, yt-dlp, HandBrake, ImageMagick, ExifTool, SoX, open source AI media, commercial safe AI"
    },
    {
      "@type": "Person",
      "@id": "https://github.com/damionrashford#person",
      "name": "Damion Rashford",
      "url": "https://github.com/damionrashford",
      "sameAs": ["https://www.linkedin.com/in/damion-rashford"]
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Does Media OS cost money to run?",
          "acceptedAnswer": { "@type": "Answer", "text": "No. Media OS is MIT-licensed. You pay for the Claude model you use (Anthropic billing) and any paid external tools (most FFmpeg/OBS/GStreamer tooling is free; some paid tools include Blackmagic DeckLink hardware, NDI HX2 licensing, DRM key servers for Shaka)." }
        },
        {
          "@type": "Question",
          "name": "Do I need all 109 skills?",
          "acceptedAnswer": { "@type": "Answer", "text": "No. Claude auto-loads only what each task needs and every skill folder is sealed. Copy a single folder into ~/.claude/skills/ to use one skill standalone, or install the full plugin for the batteries-included experience." }
        },
        {
          "@type": "Question",
          "name": "What is the safety story for live encodes?",
          "acceptedAnswer": { "@type": "Answer", "text": "Four hooks run automatically. SessionStart probes installed CLIs and FFmpeg build flags. UserPromptSubmit auto-probes any media path you mention. PreToolUse blocks common FFmpeg foot-guns (in-place overwrites, missing -movflags +faststart, missing -sc_threshold 0 on HLS, missing aac_adtstoasc on TS-to-MP4 remux, conflicting -crf and bitrate). PostToolUse re-ffprobes every FFmpeg output to catch zero-duration or truncated files." }
        },
        {
          "@type": "Question",
          "name": "What is the difference between the 96 skills and the 13 workflow skills?",
          "acceptedAnswer": { "@type": "Answer", "text": "The 96 skills are tool-and-technique (ffmpeg-transcode, obs-websocket, hdr-dovi-tool) — one skill per bounded capability. The 13 workflow skills orchestrate across them (workflow-broadcast-delivery, workflow-ai-enhancement, workflow-podcast-pipeline) — each encodes the full recipe for a production domain with the skill chain, the gotchas, and the variants." }
        },
        {
          "@type": "Question",
          "name": "What about AI models with restrictive licenses?",
          "acceptedAnswer": { "@type": "Answer", "text": "Every Layer 9 AI skill passes a strict OSI-open and commercial-safe filter (Apache-2, MIT, BSD, GPL only). Restrictive models — XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base — are explicitly documented-and-dropped in each AI skill's references/LICENSES.md." }
        },
        {
          "@type": "Question",
          "name": "How does Media OS compare to running FFmpeg manually?",
          "acceptedAnswer": { "@type": "Answer", "text": "Media OS does not replace FFmpeg — it gives Claude the right vocabulary, flag combinations, and pre-flight checks for FFmpeg, OBS, GStreamer, MediaMTX, NDI, DeckLink, Dolby Vision, and 50+ other media tools. You still run the real tools; Media OS makes sure the agent calls them with the right arguments, validates the output, and catches the gotchas LLMs get wrong from training alone." }
        },
        {
          "@type": "Question",
          "name": "Does Media OS work without an internet connection?",
          "acceptedAnswer": { "@type": "Answer", "text": "Yes for most skills — FFmpeg, OBS, GStreamer, NDI, DeckLink, MIDI, OSC, DMX all run locally. Internet is required for AI model downloads (first run only, cached after), cloud upload skills, DRM key server skills, and yt-dlp." }
        },
        {
          "@type": "Question",
          "name": "Which platforms does Media OS support?",
          "acceptedAnswer": { "@type": "Answer", "text": "macOS (Apple Silicon + Intel), Linux (x86_64 + ARM), Windows (x86_64). Some audio skills are platform-conditional: audio-coreaudio is macOS-only, audio-wasapi is Windows-only, audio-pipewire and audio-jack are Linux-primary." }
        }
      ]
    }
  ]
}
</script>
