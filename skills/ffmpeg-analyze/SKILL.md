---
name: ffmpeg-analyze
description: >
  Inspect, measure, and analyze media with ffprobe and ffmpeg analysis filters plus PySceneDetect. Use when the user asks to inspect a video, check codec, get resolution/bitrate/fps/duration, detect HDR, list streams or tracks, count frames, find keyframes, measure VMAF, compute PSNR or SSIM, compare encoded vs source quality, find the best CRF, autocrop black bars, detect silences, find black or freeze frames, detect scene cuts or shot boundaries, check if interlaced, read broadcast QC stats, read embedded captions or timecode, split a video at scene changes, generate per-scene thumbnails, add or edit chapters, edit tags, set title/artist/year, embed cover art, set stream language, mark default/forced subtitle, strip metadata, read text from frames with OCR, detect or remove a logo or watermark, blur a recurring rectangle, or encode/decode a QR code in video.
argument-hint: "[task] [input]"
---

# ffmpeg-analyze

**Context:** $ARGUMENTS

Inspection, measurement, detection, metadata authoring, OCR/logo work, and scene
detection for media files. Every technique is a separate reference doc — read the
one that matches the task. Invoke `ffmpeg-docs` before quoting any non-obvious
ffmpeg flag or filter; it is the anti-hallucination guardrail.

## When to use

- Inspect a file: codec, resolution, fps, duration, bitrate, HDR class, streams,
  keyframes, chapters, container structure → `probe.md`.
- Compute parameters from content before a real encode: autocrop, silence trim,
  black/freeze frames, scene cuts, interlace decision, broadcast QC → `detect.md`.
- Measure encode quality vs a reference: VMAF, PSNR, SSIM, CRF sweep, single-input
  block/blur QC → `quality.md`.
- Author tags, chapters, cover art, stream language, disposition flags, or strip
  metadata → `metadata.md`.
- Read burned-in text, remove a logo/watermark, blur a recurring rectangle, or
  encode/decode QR codes inside video → `ocr-logo.md`.
- Reliable shot-boundary detection (better than ffmpeg `scdet`), scene splitting,
  per-scene thumbnails, content-aware auto-chapters → `scenedetect.md`.

## Techniques

- Read `references/probe.md` when inspecting a file's container, codecs, streams,
  resolution, fps, duration, bitrate, color/HDR, frame count, keyframes, or
  chapters with ffprobe, or when piping machine-readable info downstream.
- Read `references/detect.md` when running ffmpeg analysis filters to autocrop,
  trim silences, find black/freeze frames, detect scene cuts, check interlacing,
  run broadcast `signalstats` QC, or read embedded captions/timecode.
- Read `references/quality.md` when measuring perceptual or objective quality
  (VMAF, PSNR, SSIM), benchmarking encoders, finding the best CRF for a target
  VMAF, or doing single-input block/blur QC.
- Read `references/metadata.md` when adding/editing tags, chapters, cover art,
  stream language, marking default/forced subtitle tracks, attaching fonts, or
  stripping metadata.
- Read `references/ocr-logo.md` when reading text from frames (Tesseract `ocr`),
  removing a logo (`delogo`/`removelogo`), finding/hiding a recurring rectangle
  (`find_rect`/`cover_rect`), or encoding/decoding QR codes (`qrencode`/`quirc`).
- Read `references/scenedetect.md` when reliable scene-change detection is needed
  (PySceneDetect), splitting a video at cuts, generating per-scene thumbnails, or
  building content-aware chapter markers.

Deep option catalogs live alongside: `references/queries.md` (ffprobe field/format
syntax), `references/detectors.md` (per-filter tables + regexes), `references/metrics.md`
(VMAF model catalog + scoring bands), `references/tags.md` (per-container tag
catalogs + ISO 639-2 codes), `references/filters.md` (OCR/logo/QR option tables),
`references/scenedetect-scenedetect.md` (detector comparison + recipes).

## Gotchas

- **`r_frame_rate` is a fraction** (`30000/1001`, `25/1`), not a float. Parse
  `num/den`. On VFR content `avg_frame_rate` ≠ `r_frame_rate`. Use `-v error` so
  ffprobe's banner on stderr is not mistaken for failure.
- **Detect filters write to stderr (and `lavfi.*` frame metadata), not stdout.**
  Pipe with `2>&1`. They are read-only — pair with `-f null -`. `cropdetect`
  updates over time; take the *last* `crop=` line.
- **Full-reference quality metrics require pixel-aligned inputs** — same
  resolution, fps, pixel format, length. ffmpeg does NOT auto-align; mismatch
  silently yields garbage. VMAF input order is `[distorted][reference]` (distorted
  first), needs `--enable-libvmaf` and `n_threads > 1`.
- **Metadata edits use `-c copy`** — never re-encode just to write a tag.
  ffmetadata files MUST start with `;FFMETADATA1` on line 1; language codes are
  three-letter ISO 639-2 (`eng`, not `en`); `+default+forced` ADDS, bare
  `default` REPLACES.
- **OCR/logo/QR filters are re-encode only** (no `-c copy`) and several are
  build-flag gated (`ocr`→libtesseract, `quirc`→libquirc, `qrencode`→libqrencode).
  Check `ffmpeg -filters | grep ...` first. `removelogo` mask is inverted
  (white = remove); `find_rect` threshold is inverted (0.01 = exact).
- **PySceneDetect beats ffmpeg `scdet`** on anime/stylized/low-contrast content.
  `-m` means min-scene-duration on the detector but "use mkvmerge" on
  `split-video`. `split-video -m` stream-copies but cuts only on keyframes.
- **Scene-cut/silence lists → splitting** is a separate step: feed timestamps to
  the `ffmpeg-cut-concat` skill (concat demuxer / segment muxer), stream-copying
  pre-split clips.

## Scripts

All stdlib-only, non-interactive, with `--dry-run` and `--verbose`.

- `scripts/probe.py` — `summary`, `json`, `field`, `keyframes`, `hdr`, `compare`.
- `scripts/detect.py` — `crop`, `silences`, `blacks`, `freezes`, `scenes`,
  `interlace`, `stats`, `volume`.
- `scripts/quality.py` — `vmaf`, `psnr`, `ssim`, `sweep`.
- `scripts/meta.py` — `set`, `chapters`, `extract-chapters`, `cover`, `attach`,
  `strip`, `disposition`.
- `scripts/ocrlogo.py` — `check-build`, `ocr`, `delogo`, `removelogo`,
  `find-cover`, `qr-decode`, `qr-encode`.
- `scripts/scenedetect.py` — `check`, `detect`, `split`, `thumbnails`,
  `html-report`, `chapters`.

Run with `uv run ${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-analyze/scripts/<file>.py <subcommand> ...`.
