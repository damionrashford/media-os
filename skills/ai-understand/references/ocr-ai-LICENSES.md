# Licenses — media-ocr-ai

Every backend is Apache 2.0 or MIT. Safe to ship OCR output commercially. This file is the compliance cheat sheet — keep it current.

## Runtime deps

| Package          | License       | Notes                                     |
|------------------|---------------|-------------------------------------------|
| paddlepaddle     | Apache 2.0    | Baidu's DL framework; binary wheels       |
| paddleocr        | Apache 2.0    | PaddleOCR Python wrapper                  |
| easyocr          | Apache 2.0    | JaidedAI's EasyOCR                        |
| pytesseract      | Apache 2.0    | Python wrapper for the tesseract CLI      |
| tesseract (CLI)  | Apache 2.0    | HP → Google → community, Apache since 3.x |
| transformers     | Apache 2.0    | HuggingFace                               |
| torch            | BSD-3-Clause  |                                           |
| opencv-python    | Apache 2.0    |                                           |
| numpy            | BSD-3-Clause  |                                           |
| Pillow           | MIT-CMU (HPND)|                                           |

## Model weights

### PaddleOCR

- **License:** Apache 2.0 (both code and weights). The repo ships separate per-language recognition + detection + table + layout checkpoints — all Apache.
- **Upstream:** `https://github.com/PaddlePaddle/PaddleOCR`
- **Commercial use:** yes.

### EasyOCR

- **License:** Apache 2.0 (both code and weights). Each language-specific recognizer ships under the same license.
- **Upstream:** `https://github.com/JaidedAI/EasyOCR`
- **Commercial use:** yes.

### Tesseract 5

- **License:** Apache 2.0.
- **Upstream:** `https://github.com/tesseract-ocr/tesseract`
- **`.traineddata`** packages on `tessdata_best` / `tessdata_fast` / `tessdata` are also Apache 2.0.
- **Commercial use:** yes.

### TrOCR (Microsoft)

- **License:** MIT (model code + weights). The HuggingFace model card says MIT; Microsoft published the weights under MIT via the repo.
- **Upstream:** `https://github.com/microsoft/unilm/tree/master/trocr`, `https://huggingface.co/microsoft/trocr-base-handwritten`
- **Commercial use:** yes.

## Explicitly DROPPED

- **Surya** (github.com/VikParuchuri/surya) — **DROPPED**. Weights are CC-BY-NC (non-commercial). No matter how good it is (and it is good), it cannot be used here.
- **DocTR** (Mindee) — mostly Apache 2.0 but bundles optional models with research-only licenses; use only Apache-subset recipes if you include it. We pass, to keep this skill bright-line.
- **Google Cloud Vision** — paid, closed. Out of scope.
- **Azure Document Intelligence (formerly Form Recognizer)** — paid, closed. Out of scope.
- **AWS Textract** — paid, closed. Out of scope.
- **Gemini OCR / GPT-4V / Claude Vision** — proprietary, paid; not open source. Out of scope.

## Derivative output (OCR text, layout JSON, table CSV)

Apache 2.0 and MIT do **not** encumber model output. You may:

- Ship the OCR'd text as part of a product (e.g. a searchable PDF, a receipt-scan app).
- Store OCR output in a commercial database.
- Publish the text on the web.

You must:

- Preserve Apache 2.0 NOTICE files if you **redistribute the model weights** as part of your artifact (rare — most pipelines download on first use from HF Hub, which is fine).
- Keep copyright headers in any **source code** you copy from the upstream repos (e.g. if you vendor part of PaddleOCR's inference code).

## Training-data provenance caveats

The **training data** that produced each model is a separate matter from the **weights** license.

- **PaddleOCR** trained on Baidu proprietary datasets + open sets (ICDAR, LSVT, RCTW). The *output of the trained model* is Apache-licensed. The training images themselves are not redistributable.
- **EasyOCR** trained on open academic benchmarks (ICDAR, CTW1500, MSRA-TD500) + internal scraping.
- **Tesseract** trained on mixed public-domain corpora; `.traineddata` files are Apache.
- **TrOCR** trained on IAM Handwriting DB (research license on the dataset; weights are MIT-licensed by Microsoft, separately).

In practice: **use the output freely**. Don't claim rights on the training data.

## Reporting a license change

If an upstream flips license (a fork, a fine-tune, a new release with different terms), remove the model from `MODEL_REGISTRY` /  `scripts/ocr.py` and update this file. Never silently keep shipping a model whose license slipped.
