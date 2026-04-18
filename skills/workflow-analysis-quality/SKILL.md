---
name: workflow-analysis-quality
description: Deep media inspection + automated QC — ffprobe stream details, MediaInfo diagnostics, VMAF/PSNR/SSIM quality metrics, PySceneDetect scene cuts, crop/silence/black-frame/interlacing detection, ffplay scope debugging, NAL/SEI bitstream forensics, metadata audits, loudness compliance against Spotify/Apple/ATSC/EBU specs, and automated CI QC gates. Use when the user says "QC this file", "run VMAF", "compare encoders", "detect scene cuts", "check loudness compliance", "validate delivery spec", "automated QC pipeline", or any deep inspection / quality gating.
argument-hint: [ref] [out]
---

# Workflow — Analysis + Quality

**What:** Inspect every byte and assess every rendition. The gate between "encoded" and "shipped".

## Skills used

`ffmpeg-probe`, `media-mediainfo`, `ffmpeg-quality`, `media-scenedetect`, `ffmpeg-detect`, `ffmpeg-playback`, `ffmpeg-bitstream`, `media-exiftool`, `ffmpeg-metadata`, `media-ocr-ai`, `cv-opencv`, `cv-mediapipe`, `media-tag`.

## Pipeline

### Step 1 — Probe everything

`moprobe` + `ffmpeg-probe` — full format + streams + specific stream detail + packet-level bitstream dump when needed. `moprobe --color` for HDR side data.

### Step 2 — MediaInfo deep diagnostics

`media-mediainfo` (`--Output=JSON|XML|HTML`). Shows encoded-library, CABAC/trellis/B-pyramid, source framerate variance, recording-device metadata, re-encode history. Use when ffprobe alone is insufficient.

### Step 3 — Quality metrics (VMAF / PSNR / SSIM)

`ffmpeg-quality` or `moqc`:

| Model | Use for |
|---|---|
| `vmaf_v0.6.1` | PC monitor (1920×1080 default) |
| `vmaf_v0.6.1neg` | No-enhancement (catches sharpening cheats) |
| `vmaf_4k_v0.6.1` | 4K TVs |
| `vmaf_b_v0.6.3` | Mobile / phone |

Interpretation: ≥ 95 transparent, ≥ 80 excellent, ≥ 70 good, ≥ 60 acceptable, < 60 visible loss.

### Step 4 — Scene detection

`media-scenedetect` (content method, default threshold 27). Lower (15–20) for gradual transitions; higher (35–40) for abrupt cuts only. Inline `scdet` filter in ffmpeg if you don't need PySceneDetect's graph output.

### Step 5 — Crop / silence / black / interlacing

`ffmpeg-detect`:
- `cropdetect` — auto-detect letterbox/pillarbox, emits `crop` filter args.
- `silencedetect` — `-35 dB` default for dialogue, `-50 dB` for music.
- `blackdetect` — `pic_th` 0–1 luma threshold (0.98 = near-pure-black).
- `idet` — counts fields: high TFF/BFF = interlaced, high Progressive = progressive, mixed ~60/40 = telecined (use `workflow-ai-enhancement` or `ffmpeg-ivtc` to recover).

### Step 6 — ffplay scopes

`ffmpeg-playback` — waveform, vectorscope, histogram live.

### Step 7 — Bitstream forensics

`ffmpeg-bitstream`:
- NAL dump (HEVC SPS=33, H.264 SPS=7).
- SEI dump for HDR metadata / captions / DoVi / HDR10+.

### Step 8 — Metadata audit

`media-exiftool` (image / video EXIF, XMP, IPTC). `ffmpeg-metadata` for chapter + MKV tags.

### Step 9 — Content verification with CV/AI

`media-ocr-ai` for burned text; `cv-mediapipe` for face presence; `media-tag` CLIP/SigLIP for zero-shot content tags.

### Step 10 — Loudness compliance

`media-ffmpeg-normalize --measure-only` (non-destructive). Compare to spec:

| Spec | Integrated | True peak |
|---|---|---|
| Spotify Master | −14 LUFS ± 2 | −2 dBTP |
| Apple Podcasts | −16 LUFS ± 1 | −1 dBTP |
| ATSC A/85 | −24 LUFS ± 2 | − |
| EBU R128 | −23 LUFS ± 0.5 | −1 dBTP |

### Step 11 — Automated CI QC gates

`moqc --ref source --out encoded --format json --vmaf-min 93` exits non-zero on failure. Wire into CI to fail builds that would ship broken encodes.

## Variants

- **Regression suite** — new encoder vs golden corpus, VMAF per source.
- **Streaming monitor** — every 60 s, capture 10 s, VMAF against golden.
- **Bulk spec validation** — `media-batch` parallel validate.
- **Interactive debugging** — ffplay with PTS overlay, vectorscope + waveform side-by-side.
- **ABR ladder compare** — VMAF per rung to tune quality.
- **Broadcast spec QC** — color legality (`signalstats`), interlacing (`idet`), timecode continuity, caption presence, ATSC A/85 loudness.

## Gotchas

- **VMAF reference and distorted MUST match duration and frame rate.** Mismatch = silent aligner failure → meaningless score.
- **VMAF prefers matching resolution.** If distorted is lower-res, it upscales silently. Downscale reference explicitly for HD-vs-4K comparison.
- **VMAF default model (`vmaf_v0.6.1`) is for PC monitors.** Pick `_4k`, `_mobile`, `_neg` per target.
- **PSNR-YUV vs PSNR-Y-only.** ffmpeg reports overall; Y-only via `psnr=...y`.
- **Frame drops or duplications break VMAF sync.** Need 1:1 correspondence.
- **Different YUV ranges (limited vs full)** change perceptual VMAF. Clamp to same range before compare.
- **Scene-detect threshold 27 default:** gradual transitions need 15–20, abrupt cuts tolerate 35–40.
- **`cropdetect` samples every N seconds.** Variable content = inconsistent reads. Longer duration = reliable.
- **`silencedetect -35 dB` is dialogue.** Music is −50 dB; noise floor is −60 dB.
- **`idet` gives counts, not decisions.** TFF ≈ 2.5× Progressive = telecined (5 fields per 4 frames).
- **`blackdetect pic_th` is 0–1 picture-luma, NOT dB.** 0.98 = near-pure-black only.
- **MediaInfo "Encoded Library" is a heuristic.** Re-encoded files may show wrong encoder.
- **`ffprobe duration_ts` is in stream timebase; `duration` is in seconds.** Don't conflate.
- **`nb_frames=0` means unknown** (stream not fully parsed). Use `-count_frames` for accurate.
- **ExifTool writes in place by default.** `-overwrite_original` strips backups.
- **NAL types differ between H.264 and HEVC.** Don't swap: H.264 SPS = 7, HEVC SPS = 33.
- **SEI messages in HEVC use type+size+payload** with UUID-prefixed T.35 for DoVi / HDR10+ / captions.
- **Bitstream analysis on encrypted content fails.** Widevine / FairPlay encrypt the essence below the container.
- **`ffplay` blocks.** Use `-autoexit` to exit after duration or background with `&`.
- **`ffprobe -show_streams` is INI-style by default.** Use `-of json` or `-of csv=p=0` for scripting.
- **`jq -r` drops quotes.** Omit `-r` if downstream needs JSON.
- **MediaInfo CLI `--Output=JSON` is version-gated.** v21+ produces much better JSON than v20.
- **VMAF motion metric is I/O-bound** on large sources. Use SSDs.
- **Non-deterministic encoders (x265 with threads) produce slightly different output per run.** Expect ± 0.5 VMAF variance between runs of the same command.

## Example — CI gate on an encoded asset

`moprobe --color source.mov` → sanity-check tags. `moqc --ref source.mov --out encoded.mp4 --vmaf-min 93 --format json` → fail build non-zero. `ffmpeg-detect silencedetect` confirms no > 2 s dead air. `media-ffmpeg-normalize --measure-only` confirms −16 LUFS ± 1.

## Related

- Every other workflow — this is the gate.
- `workflow-broadcast-delivery` — broadcast-spec QC subset.
- `workflow-streaming-distribution` — ABR rung comparison.
