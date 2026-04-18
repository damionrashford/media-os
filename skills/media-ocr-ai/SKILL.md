---
name: media-ocr-ai
description: >
  Modern AI OCR with open-source + commercial-safe models: PaddleOCR (Apache 2.0, Baidu, 80+ languages, layout analysis, tables), EasyOCR (Apache 2.0, JaidedAI, 80+ languages, easiest install), Tesseract 5 (Apache 2.0, mature LSTM backend, 100+ languages), TrOCR (MIT, Microsoft transformer, the only one that really handles cursive handwriting). Extract text from images and PDFs, structured layout (headers/paragraphs/tables), multilingual documents, handwriting, receipts, invoices, screenshots, scanned forms, signage, whiteboards. Use when the user asks to OCR an image, read text from a picture, extract text from a scanned PDF, parse a receipt or invoice, detect table structure, transcribe handwriting, process a multilingual document (English/Japanese/Chinese/Arabic/etc.), handle CJK or RTL scripts, or pick between PaddleOCR vs EasyOCR vs Tesseract vs TrOCR.
argument-hint: "[input] [output]"
---

# Media OCR AI

**Context:** $ARGUMENTS

Modern open-source OCR. Goes far beyond plain Tesseract by giving four models for four different jobs: PaddleOCR for layout + tables, EasyOCR for "just read the text", Tesseract for the widest language set, TrOCR for handwriting.

For the **in-ffmpeg** `ocr=` filter (Tesseract inside a filtergraph, good for logo detection / rough live text), use `ffmpeg-ocr-logo`. This skill is for **offline, high-accuracy, structured** OCR — document processing, not video frame grabs.

## Quick start

- **Read text from a photo (any language):** → Step 3 (`ocr.py extract --model easy`)
- **Structured layout of a PDF page (headers, paragraphs, tables):** → Step 4 (`ocr.py layout --model paddle`)
- **Cursive handwriting:** → Step 5 (`ocr.py handwriting --model trocr`)
- **Multilingual doc (e.g. English + Japanese):** → Step 6 (`ocr.py multi-lang --langs en,ja`)
- **Extract a table as CSV:** → Step 7 (`ocr.py table --model paddle`)
- **Pre-install a backend:** → Step 2 (`ocr.py install <model>`)

## When to use

- Read text from photos, screenshots, scans, or video frames (single-frame OCR).
- Parse receipts, invoices, business cards, signage — structured documents where layout matters.
- Transcribe handwritten notes, filled forms, or cursive.
- Multilingual content (English mixed with CJK, Arabic, Cyrillic, Thai, etc.).
- PDF text extraction when the PDF is *scanned images* (use PaddleOCR). For text-native PDFs with embedded font glyphs, reach for `pdftotext` / `pdfplumber` first — they're faster and exact.
- Do NOT use for video real-time OCR — go to `ffmpeg-ocr-logo` for that. Do NOT use for barcode / QR — see `ffmpeg-ocr-logo` (quirc).

## Step 1 — Pick a backend

| Model         | License    | Strengths                                                       | Install difficulty | When to pick                                      |
|---------------|------------|-----------------------------------------------------------------|--------------------|---------------------------------------------------|
| **PaddleOCR** | Apache 2.0 | Best layout analysis + table extraction, 80+ languages          | medium (paddlepaddle) | Structured documents, receipts, invoices, tables |
| **EasyOCR**   | Apache 2.0 | Easiest install, good general quality, 80+ languages            | easy               | "Just read this image"                            |
| **Tesseract 5** | Apache 2.0 | Widest language support (100+), battle-tested, pure CLI        | easiest (system pkg) | Legacy, CPU-only, obscure scripts                 |
| **TrOCR**     | MIT        | Transformer trained on IAM handwriting; best cursive by far     | medium (transformers) | Handwritten notes, cursive, stylized fonts       |

Pairing advice:

- PaddleOCR has the best layout analysis + table structure. EasyOCR is the easiest to install. Tesseract has the widest language support but worse accuracy on modern content. TrOCR is the only one that really handles cursive handwriting.

Full per-model strengths, install quirks, and language-matrix in `references/languages.md`.

## Step 2 — Install the backend(s)

PEP 723 header in `scripts/ocr.py` lists all dependencies. Run via `uv run` once to populate the ephemeral venv. The one-shot installer:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py install paddle
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py install easy
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py install tesseract
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py install trocr
```

Per-backend notes:

- **PaddleOCR** — pulls `paddlepaddle` (CPU) or `paddlepaddle-gpu` (CUDA) via pip. First-use downloads detection + recognition + layout models to `~/.paddleocr/`.
- **EasyOCR** — pulls `easyocr` + downloads craft-detection + language-specific recognition models to `~/.EasyOCR/` on first use.
- **Tesseract 5** — needs the system binary: `brew install tesseract tesseract-lang` (macOS) / `apt install tesseract-ocr tesseract-ocr-all` (Debian). `pytesseract` is just the Python wrapper.
- **TrOCR** — pulls HuggingFace `microsoft/trocr-base-handwritten` (or `-large-printed`) via `transformers`. Weights cache to `~/.cache/huggingface/hub/`.

## Step 3 — Extract text (any language, any backend)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py extract \
  --model easy --in photo.jpg --out-format text > photo.txt
```

Output formats:

- `--out-format text` — raw text, one line per detected region (reading order)
- `--out-format json` — `{"blocks": [{"bbox": [x,y,w,h], "text": ..., "confidence": ...}, ...]}`
- `--out-format tsv` — Tesseract-style TSV (bbox columns + text + conf), good for spreadsheets

`--lang` sets the detection / recognition language hint (e.g. `--lang en` or `--lang ja`). Without it, backends fall back to their default (usually English).

## Step 4 — Layout analysis (PaddleOCR only)

Structured layout — headers, paragraphs, lists, tables, figures — is PaddleOCR's flagship capability via **PP-StructureV2**:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py layout \
  --model paddle --in scanned_page.png --out-json layout.json
```

Output JSON has `regions`, each with `type` in `{"title", "text", "list", "table", "figure", "figure_caption", "table_caption", "header", "footer", "reference", "equation"}`, plus `bbox` and either `text` (text regions) or `html` (table regions, full cell structure).

For a multi-page scanned PDF, loop per page:

```bash
# split pages via ImageMagick (media-imagemagick skill)
magick in.pdf page_%03d.png
for p in page_*.png; do
  uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py layout --model paddle --in "$p" --out-json "${p%.png}.json"
done
```

## Step 5 — Handwriting (TrOCR)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py handwriting \
  --model trocr --in handwritten.jpg --out note.txt
```

TrOCR is a **line-level** recognizer. If the image has multiple lines, pre-segment with PaddleOCR's detection head and then run TrOCR on each line crop (the script's `handwriting` subcommand does this automatically when `--detect paddle` is passed).

Variants:

- `microsoft/trocr-small-handwritten` — fastest
- `microsoft/trocr-base-handwritten` — default
- `microsoft/trocr-large-handwritten` — best quality, slower
- `microsoft/trocr-*-printed` — for printed text (worse on handwriting, so pick only when you know the input is printed)

Select with `--variant base-handwritten` (or similar).

## Step 6 — Multilingual documents

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py multi-lang \
  --model paddle --langs en,ja,zh --in doc.png --out-json ocr.json
```

PaddleOCR supports concurrent mixed languages by loading a multilingual recognizer. EasyOCR accepts multiple `--languages` as a list on init. Tesseract takes `-l eng+jpn+chi_sim`.

See `references/languages.md` for the supported-language matrix per backend. Some languages are paddle-only (e.g. Sanskrit, Thai), some are tesseract-only (older scripts, a long tail).

## Step 7 — Table extraction as CSV

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py table \
  --model paddle --in invoice.png --out-csv invoice.csv
```

Uses PaddleOCR's PP-Structure table engine. Each detected table becomes a `<table>`-parsed CSV. Multi-table pages produce one CSV per detected table: `invoice.csv`, `invoice_table1.csv`, etc.

For complex bordered / borderless tables, PaddleOCR beats the other three backends by a wide margin — only it ships a trained table-structure-recognition model (SLANet).

## Available scripts

- **`scripts/ocr.py`** — subcommands: `extract`, `layout`, `handwriting`, `multi-lang`, `table`, `install`. Each supports `--dry-run`, `--verbose`.

## Reference docs

- Read [`references/languages.md`](references/languages.md) when picking between backends for a specific language, script, or multilingual mix (English + Japanese, CJK, Arabic/Farsi, Thai, Cyrillic).
- Read [`references/LICENSES.md`](references/LICENSES.md) before shipping OCR output commercially or redistributing the model weights.

## Gotchas

- **"Tesseract 5 is the default" is wrong.** For modern documents (receipts, phone photos, stylized fonts), EasyOCR and PaddleOCR consistently outperform Tesseract. Tesseract wins only on (a) language breadth and (b) CPU-only footprint.
- **PaddleOCR install on Apple Silicon needs `paddlepaddle` (not `-gpu`)**, and a specific version. Pin to `paddlepaddle>=2.6` in the PEP 723 deps — older 2.4 wheels have M1/M2 build issues.
- **EasyOCR downloads ~500 MB per language set** on first use. No way around it. Cache persists in `~/.EasyOCR/` — ship the cache with container images to avoid re-downloading.
- **TrOCR is line-level, not page-level.** Feeding a full page to TrOCR directly produces garbage; you must first segment lines (the `handwriting --detect paddle` flow does this).
- **Tesseract needs per-language .traineddata files.** On macOS, `brew install tesseract-lang` grabs them all; on Linux, `apt install tesseract-ocr-<lang>` is per-language. Without them, Tesseract silently recognizes in English only and produces garbage for CJK / RTL.
- **Right-to-left scripts.** Arabic / Hebrew / Farsi reading order is RTL. PaddleOCR and EasyOCR handle it correctly when you pass `--lang ar` / `--lang he`. Tesseract often outputs text in visual LTR order — post-process with `python-bidi` if needed.
- **Layout analysis != document OCR.** `ocr.py layout` returns bounding boxes + region types; the text inside each region is still produced by the rec head. If you only want "read the text", skip layout.
- **Non-Latin scripts in PaddleOCR need a different rec model.** The default `en`-only model won't recognize Chinese or Japanese. Pass `--lang ch` / `--lang japan` (PaddleOCR's codes — see `references/languages.md` for the full list; they don't all match ISO codes).
- **No prompts, no interactive choices.** Scripts are non-interactive. All parameters via flags.

## Examples

### Example 1 — Plain text extraction (EasyOCR, easiest path)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py extract \
  --model easy --in receipt.jpg --lang en --out-format text > receipt.txt
```

### Example 2 — Structured receipt parsing with layout + table detection

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py layout \
  --model paddle --in receipt.jpg --out-json receipt.json
# receipt.json has regions with types {"title","text","table","figure"}
# for the table region, html field contains the cell-accurate markup
```

### Example 3 — Transcribe handwritten notes

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py handwriting \
  --model trocr --variant base-handwritten \
  --detect paddle --in notebook_page.jpg --out notebook.txt
```

### Example 4 — Japanese menu photo

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py extract \
  --model paddle --lang japan --in menu.jpg --out-format json > menu.json
```

### Example 5 — Invoice table to CSV

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py table \
  --model paddle --in invoice.png --out-csv invoice.csv
```

### Example 6 — Batch folder with GNU parallel

Hand off to `media-batch`:

```bash
ls scans/*.png | parallel --jobs 4 \
  uv run ${CLAUDE_SKILL_DIR}/scripts/ocr.py extract \
    --model easy --in {} --out-format text > out/{/.}.txt
```

## Troubleshooting

### `ImportError: No module named 'paddle'` (or `paddlepaddle`)

Cause: PaddleOCR imported without the backend installed.
Solution: `pip install paddlepaddle>=2.6 paddleocr` (CPU). For CUDA, `pip install paddlepaddle-gpu`. Or run via `uv run` which handles the PEP 723 deps automatically.

### EasyOCR hangs on first run

Cause: Downloading the craft detector + recognizer models. Can take minutes over slow links.
Solution: Wait, or pre-warm with `uv run ocr.py install easy --lang en`. Once cached in `~/.EasyOCR/`, subsequent runs are instant.

### Tesseract returns gibberish for Chinese / Japanese / Arabic

Cause: Missing `.traineddata`. Tesseract defaults to English and silently mis-recognizes.
Solution: `brew install tesseract-lang` (macOS) or `apt install tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-ara` (Debian). Verify: `tesseract --list-langs`.

### TrOCR output is "?????" or random

Cause: Fed a full page to a line-level model, or mismatched variant (printed model on handwriting).
Solution: Run with `--detect paddle` to auto-segment lines, or use a correct variant (`-handwritten` vs `-printed`).

### `cv2.error` opening a PDF

Cause: OpenCV doesn't read PDFs directly.
Solution: Rasterize first: `magick in.pdf -density 300 page_%03d.png` (see `media-imagemagick`), then OCR each PNG.

### RTL (Arabic/Hebrew) output is visually reversed

Cause: Some backends output text in visual order (as it appears left-to-right on screen) rather than logical order.
Solution: `pip install python-bidi && python -c "from bidi.algorithm import get_display; print(get_display(open('out.txt').read()))"`.
