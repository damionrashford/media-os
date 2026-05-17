<div align="center">

# Media OS for Claude Code

**Routed multi-agent media production for Claude Code.** Say what you want — _encode this for HLS, master Dolby Vision profile 8.4, set up an NDI feed with a PTZ camera_ — the router spawns the right specialist with the right tools and the right flags.

**96 skills · 13 routed modes · 7 specialist agents · 5 lifecycle hooks · 3 PATH CLIs.** MIT licensed. v2.1.0.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?style=for-the-badge)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?logo=ffmpeg&logoColor=white&style=for-the-badge)](https://ffmpeg.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/damionrashford/media-os/validate.yml?style=for-the-badge&label=ci)](https://github.com/damionrashford/media-os/actions/workflows/validate.yml)

[![Stars](https://img.shields.io/github/stars/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/stargazers)
[![Forks](https://img.shields.io/github/forks/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/network/members)
[![Last commit](https://img.shields.io/github/last-commit/damionrashford/media-os?style=social)](https://github.com/damionrashford/media-os/commits/main)

🌐 **[damionrashford.github.io/media-os](https://damionrashford.github.io/media-os/)** — marketing site & docs

</div>

<table align="center">
<tr>
<td><a href="#install"><b>Install</b></a></td>
<td><a href="#quick-examples">Quick examples</a></td>
<td><a href="#routed-modes">Routed modes</a></td>
<td><a href="#specialists">Specialists</a></td>
<td><a href="#safety-hooks">Hooks</a></td>
<td><a href="#cli-toolbelt">CLIs</a></td>
<td><a href="#skills-catalog">Skills</a></td>
<td><a href="#configuration">Config</a></td>
<td><a href="#faq">FAQ</a></td>
</tr>
</table>

---

## Why use Media OS

Built for **broadcast engineers, video automation developers, live producers, and AI media pipeline engineers** who want Claude's natural-language interface over the real toolchain — not yet another wrapper that fails on the third edge case.

- **FFmpeg is unforgiving.** One missing flag — `-movflags +faststart`, `-sc_threshold 0`, `aac_adtstoasc`, `hvc1` vs `hev1` — ships a broken file. Every skill front-loads the gotchas LLMs get wrong from training data alone, and `mosafe` lints commands before they run.
- **Broadcast tools aren't scriptable.** NDI, DeckLink, Dolby Vision, HDR10+, OpenTimelineIO — production-grade but not designed for natural-language interfaces. Media OS provides scripted entry points for all of them, with the right metadata sidecar mux handled.
- **AI media is a license minefield.** Every Layer 9 AI skill ships a hard filter: only Apache-2 / MIT / BSD / GPL models. NC, research-only, and commercial-restricted models are explicitly documented-and-dropped.
- **Routed dispatch is deterministic.** The router skill auto-loads on any production intent and forces the four-step contract (read `_shared.md`, read mode file, compose, spawn). No opportunistic skill selection; no forgotten cross-cutting rules.

---

## Install

### Option A — Install the full plugin (recommended)

```text
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

All **109 skills** (96 tool + 13 workflow) plus the routing layer load under `/media-os:`. The router auto-triggers on intent. The `bin/` CLIs (`moprobe`, `moqc`, `mosafe`) are added to your `PATH`. Hooks register on session start.

### Option B — Copy a single skill

Every skill at [`skills/<name>/`](skills/) is a **sealed self-contained folder** — `SKILL.md` + optional `scripts/` + `references/`, no cross-skill imports.

```bash
git clone https://github.com/damionrashford/media-os.git /tmp/media-os
cp -r /tmp/media-os/skills/ffmpeg-hdr-color   ~/.claude/skills/
cp -r /tmp/media-os/skills/obs-websocket      ~/.claude/skills/
cp -r /tmp/media-os/skills/hdr-dovi-tool      ~/.claude/skills/
```

Standalone skills load under `/ffmpeg-hdr-color`, `/obs-websocket`, etc. No plugin namespace, no marketplace dependency.

### Requirements

| Requirement | Version | Notes |
|---|---|---|
| Claude Code | ≥ 2.1.60 | Plugin system support |
| Python | ≥ 3.10 | All helper scripts are stdlib-only, run via `uv run` |
| FFmpeg | Recent full build | `brew install ffmpeg` · `apt install ffmpeg` · `winget install Gyan.FFmpeg` |
| Per-skill CLIs | varies | See [Configuration](#configuration) — install only what you use |

---

## Quick examples

The most-requested production tasks and the skill chain Media OS routes them to:

| You say... | Mode dispatched | Skills invoked |
|---|---|---|
| "encode this for HLS, VMAF ≥ 95" | `streaming-distribution` | `ffmpeg-streaming` → `ffmpeg-quality` → `media-shaka` → `ffmpeg-captions` |
| "master Dolby Vision profile 8.4 for HLS" | `hdr-mastering` → `streaming-distribution` | `ffmpeg-hdr-color` → `hdr-dovi-tool` → `hdr-hdr10plus-tool` → `ffmpeg-mxf-imf` |
| "upscale + interpolate + denoise" | `ai-enhancement` | `media-upscale` → `media-interpolate` → `media-denoise-ai` → `ffmpeg-transcode` |
| "set up NDI feed from OBS with PTZ on cam-2" | `live-production` | `obs-websocket` → `ndi-tools` → `ptz-onvif` → `media-midi` → `media-dmx` |
| "podcast: TTS → mix → normalize → captions" | `podcast-pipeline` | `media-tts-ai` → `ffmpeg-audio-filter` → `media-ffmpeg-normalize` → `ffmpeg-captions` |
| "VFX ACES conform (EXR → master)" | `vfx-pipeline` | `vfx-oiio` → `vfx-openexr` → `ffmpeg-ocio-colorpro` → `ffmpeg-transcode` |
| "Premiere ↔ Resolve round-trip" | `editorial-interchange` | `otio-convert` → `ffmpeg-probe` → `media-mediainfo` → `ffmpeg-transcode` |
| "QC + deliver IMF for Netflix" | `analysis-quality` → `broadcast-delivery` | `moqc` → `ffmpeg-mxf-imf` → `media-shaka` |
| "lipsync + face animation" | `ai-enhancement` | `media-lipsync` → `media-tts-ai` → `ffmpeg-transcode` |

---

## Routed modes

**Media OS implements the [modes pattern](https://github.com/damionrashford/modes) — a routed multi-agent dispatch system.** The router skill auto-loads on any media production intent and forces a deterministic four-step contract.

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
  4. Agent(subagent_type="delivery", prompt=composed, description="streaming-distribution")
        ↓
delivery specialist runs in isolated context:
  - probes input, derives bitrate ladder
  - mosafe-wraps every ffmpeg invocation
  - encodes tiers, runs moqc per tier
  - packages HLS / DASH, applies cbcs DRM
  - writes artifact to deterministic path
        ↓
${MEDIA_WORK_DIR}/modes/streaming-distribution/{date}_{slug}/
```

Mode files are read **fresh from disk on every dispatch** — never cached, never paraphrased. Cross-cutting rules (`mosafe`-wrap every ffmpeg call, license filter on AI models, deterministic output paths, idempotent re-runs) live in `modes/_shared.md` and apply to every specialist.

### The 13 modes

Each mode declares its specialist, trigger phrases, required + optional inputs, output schema, and quality bar. Modes are the **configurable surface** — adding a task type is one new mode file plus one routing-table row.

| Mode | Specialist | Domain |
|---|---|---|
| [`live-production`](modes/live-production.md) | `live` | OBS + NDI + DeckLink + PTZ + RTMP/SRT/RIST/WHIP |
| [`streaming-distribution`](modes/streaming-distribution.md) | `delivery` | HLS / DASH / CMAF / LL-HLS + cbcs DRM + CDN upload |
| [`broadcast-delivery`](modes/broadcast-delivery.md) ⚠️ | `delivery` | DPP AS-11 · Netflix IMF · ProRes · MXF OP1a (approval-gated) |
| [`editorial-interchange`](modes/editorial-interchange.md) | `architect` | Premiere ↔ Resolve ↔ Avid ↔ FCP via FCPXML / AAF / EDL / OTIO |
| [`ai-enhancement`](modes/ai-enhancement.md) | `architect` | Upscale, interpolate, denoise, matte, depth, lipsync |
| [`ai-generation`](modes/ai-generation.md) | `architect` | Image / video / TTS / music gen (license-filtered) |
| [`podcast-pipeline`](modes/podcast-pipeline.md) | `architect` | Record / script / re-master → EBU R128 + captions |
| [`vfx-pipeline`](modes/vfx-pipeline.md) | `architect` | EXR / DPX / USD through ACES + OCIO to ProRes 4444 / J2K IMF |
| [`hdr-mastering`](modes/hdr-mastering.md) | `hdr` | HDR10, HDR10+, Dolby Vision profiles 5 / 7 / 8.4, HLG, SDR tone-map |
| [`vod-post-production`](modes/vod-post-production.md) | `encoder` | H.264 / H.265 / AV1 / ProRes / DNxHR with VMAF gate |
| [`analysis-quality`](modes/analysis-quality.md) | `qc` | VMAF + SSIM + PSNR + loudness + freeze / black / silence |
| [`audio-production`](modes/audio-production.md) | `architect` | PipeWire / JACK / Core Audio / WASAPI routing, mix, repair, MIDI/OSC |
| [`acquisition-archive`](modes/acquisition-archive.md) | `probe` | Probe-batch, ingest-card, tether-capture, archive-verify |

⚠️ = approval-gated (operator confirms target spec before dispatch).

The 13 modes are 1:1 with the 13 portable `workflow-*` skills in [`skills/`](skills/) — same domain coverage, two delivery surfaces. The modes layer is the orchestrated path (auto-route, dispatch contract, deterministic output paths); the `workflow-*` skills are the copy-a-folder portable path.

### Chained dispatch

Multi-step intents run sequentially with artifact paths passed forward. The router knows about:

| You say... | Chain |
|---|---|
| "encode + deliver this master for HLS" | `vod-post-production` → `streaming-distribution` |
| "upscale + interpolate + deliver" | `ai-enhancement` → `vod-post-production` → `streaming-distribution` |
| "HDR master + broadcast deliver" | `hdr-mastering` → `broadcast-delivery` |
| "QC + deliver" | `analysis-quality` → (if pass) → `broadcast-delivery` |
| "VFX → HDR master" | `vfx-pipeline` → `hdr-mastering` |

### Observability

Every dispatch logs one JSON line to `${MEDIA_WORK_DIR}/modes/dispatch.log` via the `SubagentStop` audit hook — timestamp, mode, specialist, duration, exit status, transcript path.

```bash
tail -F ${MEDIA_WORK_DIR}/modes/dispatch.log | jq
```

---

## Specialists

7 domain agents with pre-loaded skill sets and tool restrictions. Spawn from any Claude conversation, or let the router dispatch them.

| Agent | Color | Specialization |
|---|---|---|
| [`architect`](agents/architect.md) | 🔵 blue | Plans end-to-end pipelines before any command runs |
| [`probe`](agents/probe.md) | 🟢 green | Forensic file inspection — color, HDR side-data, GOP, captions, timecode |
| [`qc`](agents/qc.md) | 🟦 teal | Automated quality gate — VMAF + SSIM + PSNR + loudness + freeze/black/silence |
| [`hdr`](agents/hdr.md) | 🟣 purple | HDR10, HDR10+, Dolby Vision, PQ ↔ HLG, ACES, OpenColorIO |
| [`encoder`](agents/encoder.md) | 🟠 orange | Rate control, pixel format, container flags, hardware acceleration |
| [`live`](agents/live.md) | 🔴 red | OBS + RTMP/SRT/RIST/WHIP + NDI + DeckLink + PTZ |
| [`delivery`](agents/delivery.md) | 🟡 yellow | HLS/DASH packaging + cbcs DRM + CDN upload + IMF/MXF |

---

## Safety hooks

5 lifecycle hooks fire automatically. Four catch the FFmpeg mistakes that take a pipeline down; one audits every dispatch.

| Event | What it does |
|---|---|
| `SessionStart` | Probes installed CLIs + FFmpeg build flags (`libvmaf`, `libzimg`, `libvidstab`, `librist`, `libplacebo`, hwaccel) and surfaces gaps before Claude recommends anything it can't run |
| `UserPromptSubmit` | When you name a media path, auto-probes it and drops the summary (codec, color, HDR side-data, duration, GOP) into context |
| `PreToolUse(Bash)` | Flags in-place overwrites · missing `-movflags +faststart` · missing `-sc_threshold 0` on HLS · missing `aac_adtstoasc` on TS→MP4 · conflicting `-crf` + `-b:v` |
| `PostToolUse(Bash)` | Re-`ffprobe`s every FFmpeg output; catches zero-duration / truncated files before they ship |
| `SubagentStop` | Logs every routed dispatch (mode, specialist, duration, exit status) to `${MEDIA_WORK_DIR}/modes/dispatch.log` |

---

## CLI toolbelt

Three commands added to your `PATH` on install. Use them from any shell, Makefile, or CI job.

```bash
# Compact media inspection
moprobe source.mov                                # one-line summary
moprobe --color source.mov                        # HDR / color pipeline summary
moprobe --json source.mov                         # full ffprobe JSON

# Quality gate (VMAF + SSIM + PSNR + loudness + freeze/black/silence)
moqc --ref source.mov --out encoded.mp4 --vmaf-min 95 --format json

# FFmpeg pre-flight lint (wrap every ffmpeg call in CI)
mosafe ffmpeg -i in.mov -c:v libx264 -crf 23 -b:v 5M out.mp4 || exit 1
```

All three exit non-zero on failure — drop them in CI directly. The plugin also runs an `incoming-watch` background monitor that polls `INCOMING_MEDIA_DIR` for new stable files and surfaces them to Claude with a suggested probe.

---

## Skills catalog

**96 tool-and-technique skills across 9 layers**, plus **13 workflow-* recipe skills** (the portable counterparts of the 13 routed modes).

| # | Layer | Count | Coverage |
|---|---|---|---|
| **1** | FFmpeg complete | **37** | transcode, streaming, filters, HDR, codecs, protocols, broadcast MXF/IMF, DRM, 360°, VapourSynth |
| **2** | Professional companion tools | **17** | yt-dlp, MKVToolNix, Shaka Packager, GPAC, MediaInfo, ImageMagick, ExifTool, SoX, HandBrake, whisper.cpp, Demucs, PySceneDetect, ffmpeg-normalize, MoviePy, alass, cloud upload, GNU parallel |
| **3** | OBS Studio | **4** | obs-websocket v5, profile authoring, C++ plugin SDK, Python/Lua scripting |
| **4** | Streaming frameworks | **2** | GStreamer pipelines, MediaMTX all-protocol server |
| **5** | Broadcast IP + editorial + HDR dynamic | **6** | NDI, OpenTimelineIO, dovi_tool, hdr10plus_tool, Blackmagic DeckLink SDI, gphoto2 DSLR tether |
| **6** | Control protocols + system audio | **9** | MIDI 1.0 + 2.0 UMP, OSC, DMX512/Art-Net/sACN via OLA, VISCA + ONVIF PTZ, PipeWire/JACK/Core Audio/WASAPI |
| **7** | VFX stack | **3** | Pixar USD, OpenEXR, OpenImageIO |
| **8** | Computer vision + WebRTC | **6** | OpenCV, MediaPipe Tasks, W3C WebRTC spec, Pion (Go), mediasoup (Node SFU), LiveKit (Go SFU) |
| **9** | 2026 open-source AI media | **12** | Real-ESRGAN · SwinIR · HAT · RIFE · FILM · BiRefNet · rembg · RVM · Kokoro · OpenVoice · Piper · StyleTTS2 · Riffusion · ComfyUI · FLUX-schnell · Kolors · LTX-Video · CogVideoX · LivePortrait · LatentSync · Depth-Anything · MiDaS · PaddleOCR · DeepFilterNet · CLIP · SigLIP |
| **W** | Workflow recipe skills | **13** | Portable counterparts of the 13 [routed modes](#routed-modes) |

Every skill is a sealed folder. Browse the full catalog at [`skills/`](skills/).

### License filter on AI skills

Every model shipped in a Layer 9 skill is **Apache-2 / MIT / BSD / GPL**. Restricted models — **XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base** — are explicitly documented-and-dropped in each AI skill's [`references/LICENSES.md`](skills/). You don't accidentally ship something you can't monetize.

---

## Configuration

### `userConfig` fields (set at `/plugin install` time)

| Field | Purpose | Default |
|---|---|---|
| `MEDIA_WORK_DIR` | Scratch directory for intermediate renders | `/tmp/media-os` |
| `DEFAULT_ENCODE_PRESET` | x264 / x265 default preset | `medium` |
| `DEFAULT_VMAF_TARGET` | QC gate threshold | `93` |
| `OBS_WEBSOCKET_URL` / `_PASSWORD` | OBS control endpoint + auth | `ws://localhost:4455` |
| `HUGGINGFACE_TOKEN` | AI skill model access | _empty_ |
| `SHAKA_KEY_SERVER_URL` | DRM key server for Shaka Packager | _empty_ |
| `CLOUDFLARE_STREAM_TOKEN` · `MUX_TOKEN_ID/SECRET` · `BUNNY_CDN_TOKEN` | CDN upload credentials | _empty_ |
| `INCOMING_MEDIA_DIR` | Watcher target | _empty (disabled)_ |
| `LIVE_STREAM_URL` | Stream-health monitor target | _empty (disabled)_ |
| `RENDER_QUEUE_URL` / `_DIR` | Render farm monitor | _empty (disabled)_ |
| `SAFETY_REQUIRE_CONFIRM_OVERWRITE` | Toggle pre-FFmpeg overwrite guard | `true` |

### External tool requirements (per skill)

Install only what your workflows actually need. Every helper script is stdlib-only Python 3 (runs via `uv run`) and shells out to the real CLI.

<details>
<summary><strong>FFmpeg + companion tools</strong> (Layers 1 + 2)</summary>

| Skill family | External tool | Required build flags |
|---|---|---|
| `ffmpeg-*` (most) | `ffmpeg`, `ffprobe`, `ffplay` | A full-featured build |
| `ffmpeg-stabilize` | ffmpeg | `--enable-libvidstab` |
| `ffmpeg-quality` | ffmpeg | `--enable-libvmaf` |
| `ffmpeg-hdr-color` | ffmpeg | `--enable-libzimg` |
| `ffmpeg-rist-zmq` | ffmpeg | `--enable-librist` |
| `ffmpeg-ocio-colorpro` | ffmpeg + OpenColorIO | OCIO link |
| `ffmpeg-*` (GPU tonemap) | ffmpeg + libplacebo | `--enable-libplacebo` |
| `media-ytdlp` | `yt-dlp` | — |
| `media-whisper` | `whisper.cpp` / `faster-whisper` | — |
| `media-demucs` | `demucs` | — |
| `media-mkvtoolnix` | `mkvmerge` / `mkvextract` / `mkvpropedit` | — |
| `media-gpac` | `MP4Box` | — |
| `media-shaka` | `packager` (Shaka) | — |
| `media-handbrake` | `HandBrakeCLI` | — |
| `media-imagemagick` | `magick` (ImageMagick 7+) | — |
| `media-exiftool` | `exiftool` | — |
| `media-mediainfo` | `mediainfo` | — |
| `media-sox` | `sox` | — |
| `media-scenedetect` | `scenedetect` | — |
| `media-subtitle-sync` | `alass` / `ffsubsync` | — |
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
| `ndi-tools` | NDI Tools runtime (Vizrt / NewTek) |
| `decklink-tools` | Blackmagic Desktop Video driver |
| `gphoto2-tether` | `gphoto2` (libgphoto2) |
| `media-dmx` | `ola` / `olad` daemon |
| `otio-convert` | `opentimelineio` |
| `ptz-onvif` / `ptz-visca` | `onvif-zeep` / VISCA over serial-or-IP |
| `media-midi` | `python-rtmidi` |
| `media-osc` | `python-osc` |

</details>

<details>
<summary><strong>VFX + AI media</strong> (Layers 7 + 9)</summary>

| Skill | External tool |
|---|---|
| `vfx-usd` | `usdpython` + `usdview` |
| `vfx-oiio` | `oiiotool`, `iinfo`, `iconvert` |
| `vfx-openexr` | OpenEXR CLI + libOpenEXR |

Layer 9 AI skills require Python + a model runtime (PyTorch or similar). Each AI skill's [`references/`](skills/) documents exact model install paths and GPU requirements. Most benefit significantly from a CUDA / Metal / ROCm-capable GPU. **All models are Apache-2 / MIT / BSD / GPL.**

</details>

---

## Architecture

- **Skills are sealed.** One folder, one `SKILL.md`, optional `scripts/` and `references/`. No cross-skill imports — copy a folder, get a working skill.
- **SKILL.md bodies ≤ 500 lines.** Deep reference material lives in `references/<topic>.md` and loads on demand via progressive disclosure.
- **Helper scripts are stdlib Python 3.** PEP 723 inline deps (`uv run` ready), `--dry-run`, `--verbose`, exact shell command printed to stderr before executing.
- **Gotchas front-loaded.** Every `SKILL.md` lists production traps LLMs get wrong from training data alone — wrong pixel format, missing `-movflags +faststart`, `-sc_threshold 0` for HLS, `aac_adtstoasc` for TS→MP4, ASS `&HAABBGGRR` color order, `zscale=t=linear→format=gbrpf32le` sandwich for PQ ↔ HLG, `fieldmatch → decimate` IVTC order, `repeat-headers=1` for streaming HEVC, `hvc1` vs `hev1` tags, `cbcs` for unified DRM.
- **Modes are deterministic.** Mode files are loaded fresh from disk on every dispatch. The router skill auto-loads on intent and forces the four-step contract (read `_shared.md`, read mode file, compose, spawn). No opportunistic skill selection.

→ Full contributor reference: [`CLAUDE.md`](CLAUDE.md). Modes pattern reference: [github.com/damionrashford/modes](https://github.com/damionrashford/modes).

---

## Contributing & releases

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

- 🐛 [Report a broken skill / hook / CLI](https://github.com/damionrashford/media-os/issues/new?template=bug.yml)
- 💡 [Propose a new skill](https://github.com/damionrashford/media-os/issues/new?template=skill_request.yml)
- 🛤️ [Propose a new workflow / mode](https://github.com/damionrashford/media-os/issues/new?template=workflow_request.yml)
- 💬 [Discussions](https://github.com/damionrashford/media-os/discussions)

**Author a new skill locally:**

```bash
# Scaffold
uv run .claude/skills/skill-creator/scripts/scaffold.py \
  --name <new-skill> \
  --output skills \
  --with-scripts --with-references \
  --description "What it does. Use when the user asks to X, Y, or Z."

# Validate (matches CI)
uv run .claude/skills/skill-creator/scripts/validate.py skills/<new-skill>
```

Exit codes: `0` clean · `2` warnings only (acceptable) · `1` spec violation (must fix). CI at [`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs the same checks plus modes-layer validation.

**Releases:** see [CHANGELOG.md](CHANGELOG.md) and [GitHub releases](https://github.com/damionrashford/media-os/releases). Current: **v2.1.0**. Third-party marketplaces do not auto-update — pull new versions with `/plugin marketplace update media-os`.

---

## FAQ

<details>
<summary><strong>Does Media OS cost money to run?</strong></summary>

No. Media OS is MIT-licensed. You pay for the Claude model you use (Anthropic billing) and any paid external tools — most are free (FFmpeg, OBS, GStreamer, MediaMTX); some are paid (Blackmagic DeckLink hardware, NDI HX2 licensing, DRM key servers for Shaka). Each skill's [`references/`](skills/) lists licensing.
</details>

<details>
<summary><strong>Do I need all 109 skills?</strong></summary>

No. Claude auto-loads only what each task needs, and every skill folder is sealed. Copy a single folder into `~/.claude/skills/` to use one standalone, or install the full plugin for batteries-included mode.
</details>

<details>
<summary><strong>What's the safety story for live encodes?</strong></summary>

Five hooks run automatically. `SessionStart` probes installed CLIs and FFmpeg build flags. `UserPromptSubmit` auto-probes any media path you mention. `PreToolUse` blocks common FFmpeg foot-guns (in-place overwrites, missing `-movflags +faststart`, missing `-sc_threshold 0` on HLS, missing `aac_adtstoasc` on TS→MP4 remux, conflicting `-crf` + bitrate). `PostToolUse` re-`ffprobe`s every output for zero-duration / truncation. `SubagentStop` logs every routed dispatch to `dispatch.log`.
</details>

<details>
<summary><strong>What's the difference between the 13 modes and the 13 workflow-* skills?</strong></summary>

Same domain coverage, two delivery surfaces. **Modes** are the orchestrated path — the router skill auto-loads on intent, reads `modes/_shared.md` + the matched mode file, composes a prompt, spawns the specialist, and the artifact lands at a deterministic path. **`workflow-*` skills** are the copy-a-folder portable path — sealed self-contained capability declarations you can `cp -r` into another project without the router. Use modes when you want orchestrated dispatch; use the `workflow-*` skills when you want one folder you can move.
</details>

<details>
<summary><strong>What about AI models with restrictive licenses?</strong></summary>

Every Layer 9 AI skill passes a strict OSI-open and commercial-safe filter (Apache-2, MIT, BSD, GPL only). Restrictive models — XTTS-v2, F5-TTS, CodeFormer, DAIN, SVD, Wav2Lip, SadTalker, Surya, FLUX-dev, Meta MusicGen, SDXL/SD3 base — are explicitly documented-and-dropped in each AI skill's `references/LICENSES.md`.
</details>

<details>
<summary><strong>How does Media OS compare to running FFmpeg manually?</strong></summary>

Media OS does not replace FFmpeg — it gives Claude the right vocabulary, flag combinations, and pre-flight checks for FFmpeg, OBS, GStreamer, MediaMTX, NDI, DeckLink, Dolby Vision, and 50+ other media tools. You still run the real tools; Media OS makes sure the agent calls them with the right arguments, validates the output, and catches the gotchas LLMs get wrong from training alone.
</details>

<details>
<summary><strong>Does Media OS work without an internet connection?</strong></summary>

Yes for most skills — FFmpeg, OBS, GStreamer, NDI, DeckLink, MIDI, OSC, DMX all run locally. Internet is required for AI model downloads (first run only, cached after), cloud upload skills, DRM key server skills, and `yt-dlp`.
</details>

<details>
<summary><strong>Which platforms are supported?</strong></summary>

macOS (Apple Silicon + Intel), Linux (x86_64 + ARM), Windows (x86_64). Some skills are platform-conditional — `audio-coreaudio` is macOS-only, `audio-wasapi` is Windows-only, `audio-pipewire` and `audio-jack` are Linux-primary. Each `SKILL.md` documents platform support.
</details>

<details>
<summary><strong>Can I add my own skill?</strong></summary>

Yes. Scaffold via the vendored [`.claude/skills/skill-creator`](.claude/skills/), validate with `validate.py`, ship a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md). Every skill is a sealed folder — copy a folder, get a working skill.
</details>

---

## License & related

**[MIT](LICENSE).** FFmpeg itself is LGPL 2.1+ / GPL 2+ depending on build ([ffmpeg.org/legal.html](https://ffmpeg.org/legal.html)). Each companion tool and AI model carries its own license — see each skill's [`references/`](skills/).

- [**Media OS project site**](https://damionrashford.github.io/media-os/) — marketing site, full docs, llms.txt for AI agents
- [**Claude Code documentation**](https://docs.claude.com/en/docs/claude-code/overview) — the runtime
- [**Claude Code plugins spec**](https://docs.claude.com/en/docs/claude-code/plugins)
- [**Agent Skills specification**](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- [**Modes pattern**](https://github.com/damionrashford/modes) — the dispatch architecture this plugin implements

---

<div align="center">

### ⭐ If Media OS ships you a working pipeline, leave a star.

[![Star](https://img.shields.io/github/stars/damionrashford/media-os?style=for-the-badge&logo=github&label=Star%20on%20GitHub)](https://github.com/damionrashford/media-os/stargazers)

Built by [**Damion Rashford**](https://github.com/damionrashford) · [LinkedIn](https://www.linkedin.com/in/damion-rashford)

</div>
