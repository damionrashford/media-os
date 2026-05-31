---
name: using-media-os
description: Use at the start of any session and BEFORE acting on ANY media-production request (encode, stream, color/HDR, package, deliver, QC, capture, AI media, audio routing). Establishes that media intent routes through media-pipeline-router and that every media op is probe-first, mosafe-wrapped, and quality-gated. Read before hand-rolling any ffmpeg or media command.
---

# Using Media OS

Media OS is a routed multi-agent system: a router skill dispatches each media-production intent to a specialist subagent running a per-task playbook (`modes/`), under shared cross-cutting rules (`modes/_shared.md`). This skill is the gateway — it makes that routing non-optional.

<EXTREMELY-IMPORTANT>
If the user expresses ANY media-production intent — even a 1% chance one applies — you route it through the `media-pipeline-router` skill. You do NOT hand-roll an ffmpeg command in the main thread, and you do NOT answer media-production questions from training memory. This is not negotiable.
</EXTREMELY-IMPORTANT>

## The one rule

**Media intent → invoke `media-pipeline-router`.** The router reads `modes/_shared.md` + the matched `modes/<mode>.md`, composes the dispatch prompt, and spawns the right specialist (architect / probe / qc / hdr / encoder / live / delivery). It carries the cross-cutting guarantees — probe-first, `mosafe`-wrap, quality gate, AI license filter, deterministic output paths — that the main thread forgets every few turns.

## When this fires

Any of: encode / transcode / VOD master; go live / stream / OBS / NDI / DeckLink / PTZ; HLS / DASH / CMAF / DRM package; MXF / IMF / ProRes / AS-11 / DPP / Netflix deliver; OTIO / FCPXML / EDL / AAF conform; Dolby Vision / HDR10+ / tone-map / PQ↔HLG; AI upscale / interpolate / denoise / matte / depth / generate image-video-TTS-music / lipsync; QC / VMAF / loudness / freeze / black; audio routing / mix; ingest / probe / archive / hash-verify / DSLR tether.

## Iron Laws (carried by every dispatch)

> **Probe before you operate** (`moprobe`). **Wrap every ffmpeg call** (`mosafe`). **Gate before you claim done** (`moqc` or the mode's quality bar). **Never use a NC / research / commercial-restricted AI model.**

## Red flags — these thoughts mean STOP

| Thought | Reality |
|---|---|
| "This is a quick ffmpeg one-liner, I'll just write it." | Quick one-liners drop `+faststart` / `-sc_threshold 0` / `aac_adtstoasc`. Route it; let `mosafe` lint it. |
| "I know this transcode, no need to probe." | You don't know color / bit-depth / streams until you probe. Probe first. |
| "I'll answer the HDR question directly." | Main-thread answers skip the dispatch contract and the anti-hallucination doc skills. Route it. |
| "It ran, so it's done." | Exit 0 ≠ correct output. Re-probe + gate before claiming success. |
| "The operator named FLUX-dev / SVD / XTTS-v2, so it's allowed." | License filter is absolute. Offer the OSI-safe alternative; proceed only on approval. |
| "I remember this skill's flags." | Skills consolidated in v3. Invoke `ffmpeg-docs` (and the domain skill's `references/`) before quoting flags. |

## Dispatch flow

```
media-production intent?
  ├─ yes → invoke media-pipeline-router → it reads _shared.md + mode → spawns specialist
  └─ editing the system itself (skills / agents / modes / hooks / manifests)
           or a one-off single-ffprobe lookup → handle directly
```

When in doubt, route. The router is cheap; an unprobed, unwrapped, ungated media op is not.
