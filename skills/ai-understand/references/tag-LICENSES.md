# Licenses — media-tag

Every model is MIT, Apache 2.0, or BSD-3-Clause. Safe for commercial output. Read this before you ship.

## Runtime deps

| Package                | License       | Notes                                       |
|------------------------|---------------|---------------------------------------------|
| transformers           | Apache 2.0    | HuggingFace                                 |
| torch                  | BSD-3-Clause  |                                             |
| open_clip_torch        | MIT           | LAION re-implementation of OpenAI CLIP      |
| sentence-transformers  | Apache 2.0    | (optional; used for some text-only utils)   |
| opencv-python          | Apache 2.0    |                                             |
| numpy                  | BSD-3-Clause  |                                             |
| Pillow                 | MIT-CMU (HPND)|                                             |

## Model weights

### CLIP (OpenAI + LAION + DataComp)

- **OpenAI CLIP** (`openai/clip-vit-*`, open_clip "openai" pretrain) — **MIT**
- **LAION OpenCLIP** (`laion2b_s32b_b82k`, etc.) — **MIT**
- **DataComp** pretraining — **MIT**
- **Commercial:** yes

### SigLIP (Google)

- All public checkpoints (`google/siglip-*`, `google/siglip2-*`) — **Apache 2.0**
- **Commercial:** yes

### BLIP-2 (Salesforce)

- **BLIP-2 code and Q-Former + vision tower weights** — **BSD-3-Clause**
- **Frozen LLMs** inside:
  - OPT family (`-opt-2.7b`, `-opt-6.7b`) — **Meta OPT license, non-commercial**. Shipping a product that calls `blip2-opt-*` on customer data likely crosses the commercial line. *Use the Flan-T5 variants instead for unambiguous commercial use.*
  - Flan-T5 (`-flan-t5-xl`, `-flan-t5-xxl`) — **Apache 2.0**. Fully commercial.
- **Recommendation:** for commercial pipelines, pin `Salesforce/blip2-flan-t5-xl`. For research or internal use only, `-opt-2.7b` is fine.

### LLaVA (llava-hf repackagings)

- **LLaVA code** — **Apache 2.0**
- **llava-hf/llava-1.5-7b-hf** — packaging of LLaVA visual-projection weights + Vicuna-7B. Vicuna was originally trained from LLaMA (research license), but the `llava-hf` redistribution has been cleared to Apache 2.0 per the repo's model card. Still, some practitioners prefer to avoid Vicuna-based checkpoints for enterprise-grade commercial use.
- **llava-hf/llava-v1.6-mistral-7b-hf** — Mistral-7B base is **Apache 2.0**. Clean.
- **llava-hf/llava-onevision-qwen2-*-ov-hf** — Qwen2 base is **Apache 2.0**. SigLIP vision tower is **Apache 2.0**. All-Apache stack, recommended.
- **Commercial:** yes for the OneVision Qwen2 variants; recommended over 1.5 for clean licensing.

## Explicitly DROPPED

- **Florence-2** (Microsoft) — **DROPPED**. Microsoft dual-licensed: the code is MIT, but the published weights on HF are under **CC-BY-4.0 with a "research-friendly" interpretation**. The exact boundary for commercial fine-tunes + derivatives is ambiguous enough that we skip it. Flagged — track `microsoft/Florence-2-*` on HF; if/when it gets cleanly re-licensed to MIT + weights, add back.
- **CogVLM / CogVLM2** — custom non-commercial research license on the base model. Fine-tunes are sometimes Apache but the graph of derivatives is murky. Skip.
- **InternVL** — bundles InternLM weights; some variants are non-commercial research only. Too easy to pick a bad checkpoint. Skip unless a specific variant is verified.
- **Gemma Vision** (Google Gemma-based VLMs) — Gemma license has "acceptable use terms" — not a pure Apache/MIT permissive license. Google explicitly reserves restriction rights. **Flagged** — if the user needs Gemma-Vision specifically, review the Gemma Terms (ai.google.dev/gemma/terms) before shipping.
- **GPT-4V / GPT-4o vision** — proprietary, paid, closed. Out of scope.
- **Claude Vision / Anthropic** — proprietary, paid, closed. Out of scope.
- **Gemini** — proprietary, paid, closed. Out of scope.

## Derivative output (captions, tags, embedding indices, video descriptions)

Apache 2.0 and MIT and BSD-3 **do not** encumber model output. You may:

- Ship BLIP-2 / LLaVA captions as product copy, alt text, search indices.
- Store CLIP / SigLIP embeddings in a commercial vector database.
- Publish the descriptions on a content site.
- Resell a curated dataset of images + generated captions.

You must:

- Preserve copyright notices if you redistribute the **source code** you copied from upstream repos.
- Preserve NOTICE files when redistributing **model weights** (Apache 2.0 § 4).
- Not pretend the output is human-authored when it's material for a context that requires disclosure (EU AI Act art 50, certain client contracts).

## Training-data provenance

The models were trained on large web-scraped corpora (LAION-2B, CommonCrawl text, ImageNet, VQA, etc.). There is active litigation about whether training on copyrighted images constitutes fair use. **Model weights are redistributable under their stated licenses regardless of this legal question**; that's the current industry consensus. If your jurisdiction or risk profile requires provenance-clean training data, check projects like `OpenDataArtifact` or your cloud provider's "commercial-ready" model lists.

## Reporting a license change

Each HF model card is the canonical source of truth. If any changes (new version with new license, or upstream flips from MIT to RAIL), remove the model from `tag.py` and update this file immediately. Never keep shipping a model whose license slipped.

Last reviewed: 2026-04.
