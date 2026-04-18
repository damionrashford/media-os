---
name: media-tag
description: >
  AI image and video tagging, captioning, zero-shot classification, and semantic search with open-source + commercial-safe vision-language models: CLIP (MIT, OpenAI, zero-shot classification + text-image similarity, ViT-B/32 to ViT-L/14), SigLIP (Apache 2.0, Google, sigmoid loss, outperforms CLIP on most benchmarks), BLIP-2 (BSD-3-Clause, Salesforce, strong image captioning), LLaVA / LLaVA-NeXT / LLaVA-OneVision (Apache 2.0, open vision-language model for detailed description + VQA + video). Use when the user asks to auto-tag photos, generate alt text, caption an image, describe a video scene-by-scene, build a CLIP semantic-search index, classify images by free-form text labels ("cat vs dog vs car"), bulk-label a folder, generate WCAG alt text, do zero-shot classification, ask a VLM to describe what is happening in a video, or pick between CLIP/SigLIP/BLIP-2/LLaVA.
argument-hint: "[input] [action]"
---

# Media Tag

**Context:** $ARGUMENTS

Four open-source vision-language families, four different jobs:

- **CLIP / SigLIP** — "is this image closer to prompt A or prompt B?" Zero-shot classification, similarity scoring, semantic search index.
- **BLIP-2** — pure image captioning. One image in, one sentence out.
- **LLaVA** — full vision-language model. Captioning, VQA, dense description, video-frame narration.

All commercial-safe.

## Quick start

- **Caption a single image (sentence):** → Step 3 (`tag.py caption --model blip2`)
- **Describe in detail or ask a question (VLM):** → Step 4 (`tag.py describe --model llava`)
- **Zero-shot classify against your own label list:** → Step 5 (`tag.py classify --model clip`)
- **Build and query a CLIP search index over a folder:** → Step 6 (`tag.py search`)
- **Bulk-tag a folder to CSV:** → Step 7 (`tag.py tag-batch`)
- **Per-scene description of a video:** → Step 8 (`tag.py video-describe`)
- **Pre-download weights:** → Step 2 (`tag.py install <model>`)

## When to use

- Auto-alt-text for a photo library or CMS.
- Content moderation / safety (classify against a forbidden-label list).
- Semantic search over a local image folder ("find the red car in the rain").
- Cataloguing / DAM metadata enrichment (auto-tag with a controlled vocabulary).
- Quick video content summary — one description per second or per scene cut.
- Caption → search index → retrieval pipelines for RAG over images.
- Do NOT use for facial recognition of named individuals (these models weren't trained for that; accuracy and ethics both terrible).
- Do NOT use for OCR — use `media-ocr-ai`. Do NOT use for object-detection bboxes — use `cv-opencv` (YOLO) or `cv-mediapipe`.

## Step 1 — Pick a model

| Family    | License       | Strength                                                | VRAM (base) | When to pick                               |
|-----------|---------------|---------------------------------------------------------|-------------|--------------------------------------------|
| **CLIP**  | MIT           | Zero-shot classification + embedding-based search       | 1–4 GB      | "Does this match this label?"              |
| **SigLIP**| Apache 2.0    | Drop-in CLIP replacement; higher zero-shot accuracy     | 1–4 GB      | Same as CLIP, prefer when quality matters  |
| **BLIP-2**| BSD-3-Clause  | Clean image captions, compact output                    | 6–12 GB     | One-line alt text / captions               |
| **LLaVA** | Apache 2.0    | Free-form dense description, VQA, video-frame narration | 8–24 GB     | "Describe this video scene in detail"      |

Full per-model matrix (benchmark accuracy, caption quality, context length, speed) in `references/models.md`.

## Step 2 — Install / pre-download

PEP 723 header in `scripts/tag.py` declares all dependencies. `uv run` manages an ephemeral venv.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py install clip
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py install siglip
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py install blip2
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py install llava
```

Per-model notes:

- **CLIP** — via `open_clip` (preferred for variety) or `transformers` (`openai/clip-vit-large-patch14`). `open_clip` exposes a huge zoo (`ViT-B-32`, `ViT-L-14`, `ViT-H-14`, `ViT-bigG-14`, with OpenAI / LAION / DataComp pretrain tags).
- **SigLIP** — `google/siglip-base-patch16-384`, `-large-patch16-384`, `-so400m-patch14-384`. All Apache 2.0. Use `transformers`.
- **BLIP-2** — `Salesforce/blip2-opt-2.7b` (BSD-3), `-opt-6.7b`, `-flan-t5-xl`. Use `transformers`.
- **LLaVA** — `llava-hf/llava-1.5-7b-hf`, `llava-hf/llava-v1.6-mistral-7b-hf` (LLaVA-NeXT), `llava-hf/llava-onevision-qwen2-7b-ov-hf` (includes video support, recommended). All Apache 2.0 as repackaged by `llava-hf`. Use `transformers`.

## Step 3 — Single-image caption (BLIP-2 or LLaVA)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py caption \
  --model blip2 --in photo.jpg --out-text caption.txt
```

Output: one sentence, WCAG-alt-text-style. Good for cataloguing.

For richer captions:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py caption \
  --model llava --in photo.jpg --out-text caption.txt
```

LLaVA tends to produce 2–4 sentences describing scene, subject, mood. Pass `--prompt` to steer:

```bash
--prompt "Describe this image in one short sentence suitable for alt text."
```

## Step 4 — VLM description + VQA (LLaVA)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py describe \
  --model llava --in photo.jpg \
  --prompt "What objects are in this image and what is their color?" \
  --out answer.txt
```

Arbitrary VQA via `--prompt`. Useful prompts are cached in `references/prompts.md` — read it when drafting prompts for object detection, scene analysis, or video narration.

## Step 5 — Zero-shot classification (CLIP or SigLIP)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py classify \
  --model clip --in photo.jpg \
  --labels "a photo of a cat,a photo of a dog,a photo of a car,a photo of a bicycle" \
  --top-k 2
```

Output (JSON on stdout):

```json
{"top": [
  {"label": "a photo of a cat", "score": 0.87},
  {"label": "a photo of a dog", "score": 0.09}
]}
```

Pro tip — **use full-sentence prompts** ("a photo of X"), not bare words ("X"). CLIP / SigLIP are heavily biased by phrasing; `"a photo of a cat"` outperforms `"cat"` by 5–10 points on ImageNet-class prompts.

For SigLIP:

```bash
--model siglip
```

Same interface; different pretrain + sigmoid head. Higher-quality scores without softmax competition between labels — each score is independent probability.

## Step 6 — CLIP semantic search index

```bash
# 1. build embedding index of a folder
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py search \
  --model clip --index photos/ --index-out photos_clip.npz

# 2. query
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py search \
  --model clip --index photos_clip.npz \
  --query "a red car in the rain" --top-k 10
```

Index is a `.npz` with `files` (list of paths) + `embeddings` (float32 L2-normalized array). Query is a text embedding dot-producted against the index.

For scale beyond ~50 k images, swap the brute-force dot-product for FAISS or Qdrant — the reference doc `references/models.md` has a short recipe, or integrate into your own pipeline.

## Step 7 — Bulk-tag a folder to CSV

```bash
# tags.txt contains one candidate label per line
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py tag-batch \
  --model clip --in-dir photos/ --tags-file tags.txt \
  --out-csv tags.csv --threshold 0.25 --top-k 5
```

Writes `filename,label,score` rows for every image × top-k labels above threshold. Good for automated catalog metadata.

## Step 8 — Video scene description

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py video-describe \
  --model llava --in clip.mp4 \
  --sample-fps 1 --prompt "Describe this frame in one sentence." \
  --out clip_scenes.jsonl
```

Samples the video at N fps, runs LLaVA on each frame, writes one JSONL row per sample: `{"t": 3.0, "text": "..."}`. Downstream, merge adjacent identical descriptions for scene-level summary, or pair with `media-scenedetect` for true scene-boundary sampling.

Gotcha: per-frame LLaVA is expensive. For a 5-minute video at `--sample-fps 1` on a 3090 that's ~5 minutes of inference. Use `--sample-fps 0.2` (one frame per 5s) or pre-segment with `media-scenedetect` and run once per scene.

## Available scripts

- **`scripts/tag.py`** — subcommands: `caption`, `classify`, `describe`, `search`, `tag-batch`, `video-describe`, `install`. Each supports `--dry-run`, `--verbose`, `--device {auto,cpu,cuda,mps}`.

## Reference docs

- Read [`references/models.md`](references/models.md) when picking a specific CLIP / SigLIP / BLIP-2 / LLaVA variant or tuning for VRAM, latency, or benchmark score.
- Read [`references/prompts.md`](references/prompts.md) when crafting LLaVA prompts for object detection, scene analysis, caption style, or video narration.
- Read [`references/LICENSES.md`](references/LICENSES.md) before shipping model output commercially or redistributing weights — includes a DROPPED-models list (Florence-2, CogVLM, Gemini, GPT-4V, Claude Vision) and why.

## Gotchas

- **"a photo of X" beats "X".** CLIP / SigLIP classification accuracy jumps 5–10 points when you use full-sentence prompts. The codebase of OpenAI CLIP's eval harness ships 80 prompt templates ("a photo of a small X", "a photo of a large X", etc.) that average to a further 1–3 point gain. See `references/prompts.md`.
- **Normalize embeddings before dot-product search.** `open_clip` returns unnormalized features; you must L2-normalize before cosine similarity. The script handles this; if you build your own index, call `features /= features.norm(dim=-1, keepdim=True)`.
- **SigLIP scores are independent probabilities**, not softmax-normalized. Two labels can both score 0.9; that's expected. Interpret as "likelihood this is X" per label, not "pick one of the labels".
- **BLIP-2 can hallucinate.** If the image is abstract / text-heavy / low-quality, the caption will confidently invent details. Cross-check with a second model (LLaVA) for anything user-facing.
- **LLaVA OneVision (`llava-onevision`) handles video natively** via frame-grid input — the older `llava-1.5` and `llava-1.6-mistral` are image-only. Use OneVision if you're processing a video directly; otherwise sample frames and process individually.
- **Float16 on CUDA is usually fine.** On CPU or MPS, fall back to float32 for stability. Script auto-picks.
- **Florence-2 is INTENTIONALLY SKIPPED.** Microsoft dual-licensed it — code is MIT, but the CC-BY-4.0 on the published weights has ambiguity around fine-tuned derivatives. See `references/LICENSES.md` for the details. If/when a clean Apache variant ships, add it back.
- **CLIP "a photo of a person" is still not face recognition.** You cannot get named-individual recognition from CLIP/SigLIP/BLIP-2/LLaVA reliably, and you should not try — use a purpose-built recognizer (cv-opencv FaceRecognizerSF) and only with consent.
- **No prompts, no interactive input.** Scripts are fully non-interactive. All parameters via flags.

## Examples

### Example 1 — Alt text for an image

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py caption \
  --model blip2 --in hero.jpg \
  --prompt "Describe this image in one short sentence for alt text."
```

### Example 2 — Classify photo against custom labels

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py classify \
  --model siglip --in street.jpg \
  --labels "a photo of a pedestrian,a photo of a cyclist,a photo of a car,a photo of a bus,a photo of a truck" \
  --top-k 3
```

### Example 3 — Semantic search the last-year's camera roll

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py search \
  --model clip --index ~/Pictures/2025/ --index-out 2025.npz

uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py search \
  --index 2025.npz --query "sunset at the beach" --top-k 20
```

### Example 4 — Bulk-tag a folder with a controlled vocabulary

`tags.txt`:

```
a photo of a person
a photo of food
a photo of a landscape
a photo of architecture
a photo of an animal
a photo of a vehicle
```

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py tag-batch \
  --model clip --in-dir photos/ --tags-file tags.txt \
  --out-csv photos_tags.csv --top-k 2 --threshold 0.20
```

### Example 5 — Describe a video clip scene-by-scene

```bash
# optional: first find scene boundaries via media-scenedetect
scenedetect -i clip.mp4 detect-adaptive list-scenes

# then describe each scene's mid-frame
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py video-describe \
  --model llava --in clip.mp4 --sample-fps 0.5 \
  --prompt "Describe this scene in 1-2 sentences." \
  --out scenes.jsonl
```

### Example 6 — Detailed visual QA

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tag.py describe \
  --model llava --in kitchen.jpg \
  --prompt "List all appliances you can see and estimate their color."
```

## Troubleshooting

### `OSError: google/siglip-base-patch16-384 is not a local folder`

Cause: No network on first run, or HF Hub outage.
Solution: Pre-download with `tag.py install siglip` when online; weights cache to `~/.cache/huggingface/hub/`.

### Search returns nonsense for perfectly reasonable queries

Cause: Embeddings not L2-normalized before cosine similarity.
Solution: The script normalizes by default. If building your own index, `features /= features.norm(dim=-1, keepdim=True)` before any dot-product or FAISS index insert.

### LLaVA OOM on a 24 GB GPU

Cause: Default torch.float16 + full attention is still tight for 7 B on large inputs.
Solution: Use `--device cpu` (slow but works), or pick a smaller variant (`llava-1.5-7b` is smaller than `-13b`), or enable 4-bit via `bitsandbytes` (see `references/models.md`).

### CLIP classification scores all look the same

Cause: Label prompts are too similar (cosine similarity saturates) or too dissimilar from ImageNet training distribution.
Solution: Rewrite prompts as "a photo of X" / "an image showing X". For domain-specific labels, an ensemble of 5-10 prompt templates per class averaged is the standard trick.

### Video-describe runs for hours

Cause: `--sample-fps 1` is one LLaVA inference per second. For a 30-min video that's 1 800 inferences.
Solution: Reduce to `--sample-fps 0.2` (one per 5 s), or pre-segment with `media-scenedetect` and run once per scene midpoint.

### BLIP-2 captions are boring / repetitive

Cause: Default greedy decoding.
Solution: The script uses `num_beams=5` by default. Crank to 10 or enable `do_sample=True` with temperature 0.7 via `--beams 10 --temperature 0.7` (if wired in). Or switch to LLaVA for more varied language.

### SigLIP scores don't sum to 1

Cause: SigLIP uses sigmoid, not softmax. Each label probability is independent.
Solution: Treat as independent yes/no probabilities. Sum > 1 or < 1 is expected.
