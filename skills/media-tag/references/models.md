# Models — per-model matrix

Read when picking a specific CLIP / SigLIP / BLIP-2 / LLaVA variant or tuning for VRAM, latency, or benchmark score.

## CLIP family (MIT, OpenAI + LAION + DataComp)

Via `open_clip_torch`. Pass `--name "ViT-L-14,openai"` (i.e. `architecture,pretrained`). Pretrained tags include `openai`, `laion2b_s32b_b82k`, `datacomp_xl_s13b_b90k`, etc.

| Arch          | Pretrain           | Params  | Image size | ImageNet-1k zero-shot | Notes                                     |
|---------------|--------------------|---------|------------|------------------------|-------------------------------------------|
| ViT-B-32      | openai             | ~150 M  | 224        | 63.4 %                 | Small, fast, the "CLIP default"           |
| ViT-B-16      | openai             | ~150 M  | 224        | 68.3 %                 | Still B-sized, better accuracy            |
| ViT-L-14      | openai             | ~430 M  | 224        | 75.5 %                 | "CLIP large" historical baseline          |
| ViT-L-14-336  | openai             | ~430 M  | 336        | 76.6 %                 | OpenAI's best pre-LAION                   |
| ViT-H-14      | laion2b_s32b_b82k  | ~1.0 B  | 224        | 78.0 %                 | LAION-2B trained; commercially usable     |
| ViT-g-14      | laion2b_s34b_b88k  | ~1.4 B  | 224        | 78.5 %                 |                                           |
| ViT-bigG-14   | laion2b_s39b_b160k | ~2.5 B  | 224        | 80.1 %                 | Best open CLIP; 10 GB VRAM                |
| ViT-L-14      | datacomp_xl_s13b   | ~430 M  | 224        | 79.2 %                 | DataComp XL; better than LAION-2B @ L-14 |

**License:** all MIT (OpenAI) or MIT (LAION / DataComp). Full commercial rights.

## SigLIP family (Apache 2.0, Google)

Via `transformers`. Pass `--name google/siglip-base-patch16-384`.

| Model                                      | Params | Image size | COCO zero-shot T→I R@1 | Notes                           |
|--------------------------------------------|--------|------------|-------------------------|---------------------------------|
| `google/siglip-base-patch16-224`           | ~200 M | 224        | ~52 %                   | Base, fastest                   |
| `google/siglip-base-patch16-384`           | ~200 M | 384        | ~55 %                   | Recommended default             |
| `google/siglip-large-patch16-384`          | ~650 M | 384        | ~60 %                   | Best speed-quality trade        |
| `google/siglip-so400m-patch14-384`         | ~400 M | 384        | ~62 %                   | Shape-optimal 400 M; SOTA open  |
| `google/siglip2-base-patch16-naflex`       | ~200 M | var        | (2025 v2)               | NaFlex variable-res support     |

SigLIP uses **sigmoid** loss rather than softmax, so label scores are **independent probabilities** — each label is "likely yes/no", no forced competition. This is why SigLIP's score distribution looks different from CLIP.

**License:** all Apache 2.0.

## BLIP-2 family (BSD-3-Clause, Salesforce)

Via `transformers`.

| Model                           | Frozen LLM   | Params | VRAM (fp16) | Notes                                      |
|---------------------------------|--------------|--------|-------------|--------------------------------------------|
| `Salesforce/blip2-opt-2.7b`     | OPT-2.7B     | ~3.9 B | ~8 GB       | Default                                    |
| `Salesforce/blip2-opt-6.7b`     | OPT-6.7B     | ~7.9 B | ~18 GB      | Bigger LLM, slightly better captions       |
| `Salesforce/blip2-flan-t5-xl`   | Flan-T5-XL   | ~4 B   | ~10 GB      | Better at instruction-style prompts        |
| `Salesforce/blip2-flan-t5-xxl`  | Flan-T5-XXL  | ~12 B  | ~40 GB      | Best quality; full-rank only               |

BLIP-2 outputs short, factual captions. It can do VQA by passing the question as `text=` into the processor, but LLaVA is much better at that — use BLIP-2 for captioning, LLaVA for VQA.

**License:** code BSD-3-Clause; weights (via Salesforce HF repos) BSD-3-Clause as well. The frozen LLMs inside (OPT, Flan-T5) have their own licenses: OPT is custom non-commercial. Check before shipping — if you use `blip2-opt-*` commercially you're redistributing OPT weights which Meta's OPT license restricts. For bulletproof commercial use, pick the Flan-T5 variants (Apache 2.0 LLM).

## LLaVA family (Apache 2.0 for the `llava-hf` repackagings)

Via `transformers`.

| Model                                             | Base LLM     | Image encoder  | Params | VRAM (fp16) | Video? | Notes                          |
|---------------------------------------------------|--------------|----------------|--------|-------------|--------|--------------------------------|
| `llava-hf/llava-1.5-7b-hf`                        | Vicuna-7B    | CLIP ViT-L/14  | ~7 B   | ~15 GB      | no     | Original LLaVA 1.5             |
| `llava-hf/llava-1.5-13b-hf`                       | Vicuna-13B   | CLIP ViT-L/14  | ~13 B  | ~28 GB      | no     |                                |
| `llava-hf/llava-v1.6-mistral-7b-hf` (NeXT)        | Mistral-7B   | CLIP ViT-L/14  | ~7 B   | ~16 GB      | no     | LLaVA-NeXT, AnyRes resolution  |
| `llava-hf/llava-v1.6-vicuna-13b-hf`               | Vicuna-13B   | CLIP ViT-L/14  | ~13 B  | ~28 GB      | no     |                                |
| `llava-hf/llava-onevision-qwen2-0.5b-ov-hf`       | Qwen2-0.5B   | SigLIP SO400M  | ~0.5 B | ~3 GB       | **yes**| Tiny OneVision                 |
| `llava-hf/llava-onevision-qwen2-7b-ov-hf`         | Qwen2-7B     | SigLIP SO400M  | ~7 B   | ~18 GB      | **yes**| Recommended for video          |
| `llava-hf/llava-onevision-qwen2-72b-ov-hf`        | Qwen2-72B    | SigLIP SO400M  | ~72 B  | ~160 GB     | **yes**| SOTA open VLM; needs 2× H100   |

**License:** all Apache 2.0 as distributed by `llava-hf`. Inner LLMs (Vicuna, Mistral, Qwen2) are also open (Mistral Apache, Qwen2 Apache, Vicuna has some history — original Vicuna was LLaMA-derived with research license; the 1.5 checkpoints have been re-released under more permissive terms via `llava-hf`'s repackaging). For zero-doubt commercial use, prefer `onevision-qwen2-*` — Qwen2 + SigLIP + LLaVA glue is all Apache 2.0 end-to-end.

## Benchmark summary

| Task                                  | Recommended                                           |
|---------------------------------------|-------------------------------------------------------|
| Zero-shot ImageNet-1k classification  | SigLIP SO400M or CLIP ViT-bigG-14                     |
| Image-text retrieval (COCO, Flickr)   | SigLIP SO400M                                         |
| Short one-line captions               | BLIP-2 (flan-t5-xl) or LLaVA-1.5-7B                   |
| Long / detailed descriptions          | LLaVA-NeXT-7B or LLaVA-OneVision-7B                   |
| Visual Question Answering             | LLaVA-OneVision-7B                                    |
| Video frame narration                 | LLaVA-OneVision-7B (native video frame grid)          |
| Low-VRAM (< 8 GB)                     | LLaVA-OneVision-0.5B, or BLIP-2-opt-2.7b int8         |

## VRAM reduction tricks

- `torch_dtype=torch.float16` on CUDA: halves VRAM vs float32 (script default).
- `bitsandbytes` 4-bit quantization: roughly quarter again. `load_in_4bit=True`.
- Batch size 1 is fine for all; VRAM is dominated by model weights, not activations.
- MPS (Apple Silicon) works for CLIP / SigLIP reliably; BLIP-2 / LLaVA sometimes hit unsupported ops — fall back to CPU with `--device cpu`.

## Scaling a CLIP index beyond 50 k images

Brute-force dot-product in `search` is O(N × D). For 50 k × 512-d it's fine (<50 ms). Beyond that:

- **FAISS** (`pip install faiss-cpu` or `faiss-gpu`) — `IndexFlatIP` for exact cosine (embeddings already L2-normalized); `IndexHNSW` for approximate, millions of images in ms.
- **Qdrant / Weaviate / pgvector** — a proper vector database. Hand off once the index exceeds a few million.

Skeleton:

```python
import faiss
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings.astype("float32"))
D, I = index.search(query[None, :], k=10)
```

The script ships the brute-force path only; everything above is a straightforward swap.
