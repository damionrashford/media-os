# Phase 2 — consolidation name-map (97 → ~36)

Proposed old→new groupings. Each NEW skill = lean SKILL.md (router over techniques)
+ one `references/<technique>.md` per absorbed skill (full body, verbatim) + merged
`scripts/`. `description` = union of absorbed triggers, CSO-style, front-loaded.

Breaking change: every mode/_shared/router reference to an OLD name must update to the
NEW name in a final sweep.

## FFmpeg (38 → 10)
| New skill | Absorbs |
|---|---|
| `ffmpeg-encode` | ffmpeg-transcode, ffmpeg-hwaccel, ffmpeg-bitstream, ffmpeg-playback |
| `ffmpeg-edit` | ffmpeg-cut-concat, ffmpeg-frames-images, ffmpeg-speed-time, ffmpeg-capture |
| `ffmpeg-filter` | ffmpeg-video-filter, ffmpeg-audio-filter, ffmpeg-audio-fx, ffmpeg-audio-spatial |
| `ffmpeg-color` | ffmpeg-hdr-color, ffmpeg-lut-grade, ffmpeg-ocio-colorpro |
| `ffmpeg-restore` | ffmpeg-denoise-restore, ffmpeg-stabilize, ffmpeg-ivtc, ffmpeg-lens-perspective, ffmpeg-vapoursynth |
| `ffmpeg-composite` | ffmpeg-chromakey, ffmpeg-compose-mask, ffmpeg-360-3d, ffmpeg-geq-expr, ffmpeg-synth |
| `ffmpeg-analyze` | ffmpeg-probe, ffmpeg-detect, ffmpeg-quality, ffmpeg-metadata, ffmpeg-ocr-logo, media-scenedetect |
| `ffmpeg-subtitle` | ffmpeg-subtitles, ffmpeg-captions, media-subtitle-sync |
| `ffmpeg-stream` | ffmpeg-streaming, ffmpeg-whip, ffmpeg-rist-zmq |
| `ffmpeg-broadcast` | ffmpeg-mxf-imf, ffmpeg-drm |

## Companion CLIs (17 → 9)
| New skill | Absorbs |
|---|---|
| `media-download` | media-ytdlp |
| `media-whisper` | media-whisper (kept) |
| `media-demucs` | media-demucs (kept) |
| `media-package` | media-mkvtoolnix, media-gpac, media-shaka |
| `media-handbrake` | media-handbrake (kept) |
| `media-moviepy` | media-moviepy (kept) |
| `media-audio-cli` | media-sox, media-ffmpeg-normalize |
| `media-inspect` | media-mediainfo, media-exiftool |
| `media-imagemagick` | media-imagemagick (kept) |
| `media-batch` | media-batch (kept) |
| `media-cloud-upload` | media-cloud-upload (kept) |

(11 — `media-scenedetect` → ffmpeg-analyze, `media-subtitle-sync` → ffmpeg-subtitle already counted above.)

## OBS (5 → 1) · Frameworks (2 → 2)
| New skill | Absorbs |
|---|---|
| `obs` | obs-websocket, obs-config, obs-scripting, obs-plugins |
| `gstreamer` | gstreamer-pipeline |
| `mediamtx` | mediamtx-server |

## Broadcast IP + editorial (6 → 3)
| New skill | Absorbs |
|---|---|
| `broadcast-io` | decklink-tools, ndi-tools, gphoto2-tether |
| `otio` | otio-convert |
| `hdr-meta` | hdr-dovi-tool, hdr-hdr10plus-tool |

## Control (5 → 2) · System audio (4 → 1)
| New skill | Absorbs |
|---|---|
| `media-control` | media-midi, media-osc, media-dmx |
| `ptz` | ptz-onvif, ptz-visca |
| `audio-routing` | audio-coreaudio, audio-jack, audio-pipewire, audio-wasapi |

## VFX (3 → 1) · CV (2 → 1) · WebRTC (4 → 1)
| New skill | Absorbs |
|---|---|
| `vfx` | vfx-oiio, vfx-openexr, vfx-usd |
| `cv` | cv-opencv, cv-mediapipe |
| `webrtc` | webrtc-spec, webrtc-pion, webrtc-mediasoup, webrtc-livekit |

## AI media (12 → 4)
| New skill | Absorbs |
|---|---|
| `ai-enhance` | media-upscale, media-interpolate, media-denoise-ai |
| `ai-generate` | media-sd, media-svd, media-tts-ai, media-musicgen |
| `ai-understand` | media-matte, media-depth, media-ocr-ai, media-tag |
| `ai-lipsync` | media-lipsync |

## Kept as-is
- `media-pipeline-router` (router; description gets CSO trim in Phase 3)
- NEW `using-media-os` (gateway; Phase 3)

## Tally
10 ffmpeg + 11 companion + 3 obs/frameworks + 3 broadcast + 3 control/audio + 3 vfx/cv/webrtc + 4 ai + router = **38**, +1 gateway = **39 dirs**.
(Trim toward ~34 by merging `media-handbrake`→`ffmpeg-encode` and `ai-lipsync`→`ai-generate` if tighter is wanted.)

## Open: the `-docs` skills
10 `*-docs` skills (ffmpeg-docs, obs-docs, gstreamer-docs, mediamtx-docs, ndi-docs,
otio-docs, ptz-docs, decklink-docs, hdr-dynmeta-docs, audio-routing-docs) live in
`.claude/skills/` (dev-only). The distributed modes + skill bodies tell users to
"invoke ffmpeg-docs first" — but users never receive these skills. Must resolve before
Phase 2 (see question).
