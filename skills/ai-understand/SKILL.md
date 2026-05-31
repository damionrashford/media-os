---
name: ai-understand
description: >
  AI image and video understanding with open-source, commercial-safe models: background removal and matting (rembg, BiRefNet, RMBG-2.0, RobustVideoMatting/RVM), monocular depth estimation (Depth-Anything v2, MiDaS), OCR and document layout (PaddleOCR, EasyOCR, Tesseract 5, TrOCR), and tagging, captioning, and zero-shot classification (CLIP, SigLIP, BLIP-2, LLaVA). Use when the user asks to remove a background, cut out a subject, make a transparent PNG, matte a person, replace a video background, generate an alpha channel, estimate depth, build a depth map, run Depth Anything or MiDaS, create a 2.5D parallax or Ken Burns shot, convert 2D to stereo 3D, extract a Z-depth pass, OCR an image, read text from a photo or scanned PDF, parse a receipt or invoice, detect table structure, transcribe handwriting, auto-tag photos, generate alt text, caption an image, describe a video scene-by-scene, build a CLIP search index, or do zero-shot classification.
argument-hint: "[task] [input] [output]"
---

# AI Understand

**Context:** $ARGUMENTS

AI models that read and interpret visual media: matting, depth, OCR, tagging. All open-source and commercial-safe. Pick a technique, then read its reference for full recipes.

## When to use

- Remove a background, cut out a subject, make a transparent PNG, matte a person, or replace a video background without a green screen.
- Estimate depth, build a depth map, convert 2D to stereo 3D, animate a 2.5D parallax / Ken Burns shot, or extract a Z-depth pass for compositing.
- OCR an image or scanned PDF, read multilingual text, parse a receipt or invoice, detect table structure, or transcribe handwriting.
- Auto-tag photos, generate alt text, caption images, describe video scene-by-scene, build a CLIP semantic-search index, or do zero-shot classification.
- Do NOT use for chroma-key on real greenscreen footage (use `ffmpeg-chromakey`), in-ffmpeg live OCR (use `ffmpeg-ocr-logo`), object-detection bboxes (use `cv-opencv` / `cv-mediapipe`), or named-individual face recognition.

## Techniques

- Read `references/matte.md` when removing backgrounds, cutting out subjects, making transparent PNGs, or matting video. Models: rembg, BiRefNet, RMBG-2.0, RVM.
- Read `references/depth.md` when estimating depth, building depth maps, converting 2D to stereo 3D, animating parallax, or extracting Z-depth. Models: Depth-Anything v2, MiDaS.
- Read `references/ocr-ai.md` when reading text from images or scanned PDFs, parsing structured documents, extracting tables, or transcribing handwriting. Models: PaddleOCR, EasyOCR, Tesseract 5, TrOCR.
- Read `references/tag.md` when captioning, tagging, generating alt text, zero-shot classifying, building a search index, or describing video. Models: CLIP, SigLIP, BLIP-2, LLaVA.

## Licenses

Every model here passes a strict OSI-open + commercial-safe filter. Per-technique LICENSES files carry the full compliance detail and the dropped-model reasoning — read the relevant one before shipping output or redistributing weights:

- `references/matte-LICENSES.md` — note RMBG v1.4 is CC-BY-NC (dropped; only v2.0 Apache used) and RVM is GPL-3.0 (subprocess-boundary only).
- `references/depth-LICENSES.md` — relative-depth output is commercial-safe even where metric fine-tunes trained on NC datasets.
- `references/ocr-ai-LICENSES.md` — all four backends Apache 2.0 / MIT.
- `references/tag-LICENSES.md` — dropped models include Florence-2, CogVLM, and closed cloud VLMs (Gemini, GPT-4V, Claude Vision) with reasoning.

## Gotchas

- **RVM is GPL-3.0** — run it as a subprocess (CLI boundary), never import its modules into closed-source code, or copyleft propagates. RMBG **v1.4 is CC-BY-NC**; only the Apache-2.0 v2.0 is used here.
- **rembg is frame-by-frame** and flickers on video; use RVM for temporal coherence. MP4 + H.264 can't carry alpha — use ProRes 4444 `.mov` or VP9 `.webm` for transparent video.
- **Depth is inverse-relative, not metric.** HuggingFace returns higher = closer; Blender / Nuke want the opposite, so pass `--invert`. Per-frame video depth flickers — smooth temporally.
- **"Tesseract is the default" is wrong** — EasyOCR / PaddleOCR beat it on modern documents. Tesseract needs per-language `.traineddata` or it silently falls back to English garbage. TrOCR is line-level: segment lines first.
- **"a photo of X" beats "X"** for CLIP/SigLIP zero-shot by 5–10 points. L2-normalize embeddings before cosine search. SigLIP scores are independent sigmoid probabilities, not softmax — they need not sum to 1.
- **LLaVA OneVision handles video natively**; older llava-1.5 / 1.6 are image-only. Per-frame LLaVA is expensive — sample at low fps or pre-segment with `media-scenedetect`.
- **Non-interactive only.** All scripts take parameters via flags, support `--dry-run` and `--verbose`, and print the shell command to stderr before running.

## Scripts

- `scripts/matte.py` — `image | video | refine | composite | check`. Background removal and matting.
- `scripts/depth.py` — `image | video | stereo | parallax | install`. Monocular depth, stereo, parallax.
- `scripts/ocr.py` — `extract | layout | handwriting | multi-lang | table | install`. OCR and document layout.
- `scripts/tag.py` — `caption | classify | describe | search | tag-batch | video-describe | install`. Tagging, captioning, classification.

Invoke any with `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py <subcommand> ...`. Each subcommand supports `--dry-run` and `--verbose`.
