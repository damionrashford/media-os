# Show HN: Media OS — a 96-skill media production plugin for Claude Code

<!--
Submission packet for Hacker News "Show HN".

HN rules summary (from https://news.ycombinator.com/showhn.html):
- Title MUST start with "Show HN:".
- Must be something people can actually try / see working — not a landing page,
  waitlist, announcement, or press release.
- Link to the project, not to a blog post about the project.
- First comment should explain the story behind it (motivation, how you built it,
  what's interesting under the hood).
- No rants, no ads, no hiring posts, no "beta soon" promises.

Use the draft below verbatim (or close to it).
-->

## Submission fields

**Title (80 char max):**

```
Show HN: Media OS – 96-skill media production plugin for Claude Code
```

**URL:**

```
https://github.com/damionrashford/media-os
```

**Text (leave empty — HN Show HN posts either have URL or text, not both. Put the story below as the first comment.)**

---

## First comment (post immediately after submitting)

Hi HN — I built media-os, a Claude Code plugin that turns Claude into a
working media-production engineer: FFmpeg, HDR / Dolby Vision, OBS Studio,
GStreamer, MediaMTX, NDI, WebRTC, Whisper, Demucs, MoviePy, ExifTool, OTIO,
and a bunch of the 2026 open AI media models (RIFE, Real-ESRGAN, RobustVideoMatting,
Stable Diffusion, Piper, Coqui TTS with proper license filtering).

It's 96 skills, 7 orchestrator agents (probe / qc / hdr / encoder / live / delivery / architect),
13 end-to-end workflow guides, 4 lifecycle hooks, a background monitor for the
incoming folder, and three PATH-level CLIs (`moprobe`, `moqc`, `mosafe`) that
get auto-installed on plugin activation.

### Why I built it

I got tired of Claude confidently hallucinating FFmpeg flags that don't exist.
`-sc_threshold 0` is real, `-keyint_min` is real, `-bframes` is real — but the
models would happily invent combinations that either no-op or silently corrupt
output. Even worse on HDR and Dolby Vision: the `zscale=t=linear →
format=gbrpf32le → tonemap → zscale` sandwich is mandatory for PQ↔HLG
and every single LLM I tried skipped at least one link in the chain.

So every skill that touches a CLI has a companion `*-docs` skill
(`ffmpeg-docs`, `obs-docs`, `gstreamer-docs`, `mediamtx-docs`, `ptz-docs`,
`ndi-docs`, `otio-docs`, `decklink-docs`, `hdr-dynmeta-docs`,
`audio-routing-docs`) that fetches the current upstream reference and searches
it locally. The Claude instance hitting FFmpeg MUST ground flags against
`ffmpeg-docs` before recommending them. This is the anti-hallucination
guardrail — and it's the single most important decision in the repo.

### What's in it

The skills are organized in 9 layers:

1. FFmpeg core + visual/color + audio + streaming + analysis + immersive/broadcast
2. Companion tools: yt-dlp, Whisper, Demucs, MKVToolNix, GPAC, Shaka, HandBrake, MoviePy, loudness, MediaInfo, PySceneDetect, subsync, ImageMagick, ExifTool, SoX, batch, cloud upload
3. OBS Studio: websocket, plugins, scripting, config
4. Frameworks: GStreamer, MediaMTX
5. Broadcast IP + editorial: NDI, OTIO, Dolby Vision (dovi_tool), HDR10+, DeckLink, gPhoto2
6. Control: MIDI, OSC, DMX, PTZ (VISCA, ONVIF) + system audio (PipeWire, JACK, CoreAudio, WASAPI)
7. VFX: USD, OpenEXR, OIIO
8. CV + WebRTC: OpenCV, MediaPipe, spec, Pion, mediasoup, LiveKit
9. Open-source AI media: upscaling (Real-ESRGAN), interpolation (RIFE), matting (RVM),
   depth (MiDaS/Depth-Pro), AI denoise, TTS (Piper/Coqui non-XTTS), image gen (Flux-schnell),
   video gen (AnimateDiff), music gen (MusicGen via Audiocraft), lipsync (Wav2Lip replacements),
   AI OCR (PaddleOCR), auto-tag

Every AI-model skill enforces a strict OSI-open + commercial-safe license filter.
XTTS-v2 (CPML-NC), F5-TTS (research), FLUX-dev (non-commercial), SDXL/SD3 base
(restrictive), SVD (NC research), Wav2Lip (research), SadTalker (NC),
Meta MusicGen (CC-BY-NC), Surya OCR (commercial restriction), CodeFormer (NC),
DAIN (research) are **always dropped**, even when users ask for them by name.
Each AI skill ships a `references/LICENSES.md` explaining why. If you care about
commercial deployment this is the difference between shippable output and a
cease-and-desist.

### What's unusual / maybe interesting

- **Sealed skill folders.** Scripts must not import across skills. Copy any skill
  folder to any other plugin and it keeps working. Makes the surface very
  refactorable.
- **Stdlib-only Python + PEP 723 inline deps.** No requirements.txt. Every
  helper script is runnable via `uv run path/to/script.py` with deps
  declared in the file header. The whole plugin has zero build step.
- **`--dry-run` / `--verbose` required on every helper.** Print the exact shell
  command to stderr before executing. Observability by default.
- **Orchestrator agents, not giant system prompts.** Each agent (probe, qc,
  hdr, encoder, live, delivery, architect) preloads the 4–8 skills it needs and
  delegates the rest. The router agent doesn't know *how* to transcode — it
  knows which specialist to call.
- **Hooks enforce safety, not style.** SessionStart checks deps, UserPromptSubmit
  gates destructive ops, PreToolUse sanity-checks FFmpeg commands, PostToolUse
  sniffs for HDR-metadata loss.
- **Validator is strict.** `validate.py` flags `input()` calls anywhere
  (including docstrings — agents can't respond to stdin), absolute `/Users/…`
  paths in any reference doc, and SKILL.md bodies > 500 lines.

### Install

```
/plugin marketplace add damionrashford/media-os
/plugin install media-os@media-os
```

That's it. Skills become available namespaced as `/media-os:<skill>`.

### What I'd love feedback on

- **Skill granularity.** 96 is a lot. Is this the right cut, or should some
  layers collapse? The trade-off is Claude picks the right skill faster when
  they're narrow, but the menu gets long.
- **Gotchas quality.** Each SKILL.md has a "Gotchas" section — the
  highest-signal part of the whole plugin IMO (`-sc_threshold 0` for HLS GOPs,
  `aac_adtstoasc` for TS→MP4, `&HAABBGGRR` ASS color order, `hwdownload,format=nv12`
  for GPU→CPU, `fieldmatch → decimate` IVTC ordering, etc). If you have FFmpeg
  landmines I'm missing, please send them.
- **The AI license wall.** I'm open to counterarguments on specific models I
  dropped — but my bar is "can a small studio ship a commercial product using
  output from this model without lawyering up" and the answer for XTTS / FLUX-dev
  / SVD is still no.

Repo: https://github.com/damionrashford/media-os
License: MIT (the plugin itself; individual upstream tools retain their own).

Happy to answer anything.

---

## Posting checklist

- [ ] Repo is public and the README renders cleanly on GitHub web.
- [ ] Release tag `v2.0.0` is cut with binaries / release notes.
- [ ] Social preview image uploaded (Settings → Options → Social preview).
- [ ] `about` / description is ≤350 chars and mentions "Claude Code plugin".
- [ ] Topics are set (≤20).
- [ ] Post on a weekday, US morning (9–11am ET is typical HN-front-page window).
- [ ] Do NOT ask people to upvote. HN will deboost / penalize.
- [ ] Respond to every comment in the first 2 hours — that's when the ranking
      algorithm is most sensitive.
- [ ] Cross-post to /r/MediaTools, /r/FFMPEG, /r/ClaudeAI about an hour after
      HN — with a different, self-contained post body (don't just link HN).

## Reference

- https://news.ycombinator.com/showhn.html (rules)
- https://www.ycombinator.com/blog/how-to-do-a-show-hn
