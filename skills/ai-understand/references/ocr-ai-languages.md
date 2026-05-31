# Languages — per-backend support matrix

Read this when picking a backend for a specific language, script, or multilingual mix.

## Summary

| Capability                             | PaddleOCR | EasyOCR | Tesseract 5 | TrOCR  |
|----------------------------------------|-----------|---------|-------------|--------|
| Languages supported (approx.)          | 80+       | 80+     | 100+        | 1 (EN) |
| Chinese (Simplified)                   | excellent | good    | ok          | no     |
| Chinese (Traditional)                  | excellent | good    | ok          | no     |
| Japanese                               | excellent | good    | ok          | no     |
| Korean                                 | excellent | good    | ok          | no     |
| Arabic / Hebrew / Farsi (RTL)          | good      | good    | ok-but-LTR  | no     |
| Cyrillic (Russian, Ukrainian, etc.)    | excellent | good    | excellent   | no     |
| Thai                                   | good      | good    | ok          | no     |
| Hindi / Bengali / Tamil (Indic)        | good      | good    | excellent   | no     |
| Handwriting (English)                  | ok        | ok      | poor        | **best**  |
| Structured layout (headers, paragraphs, tables) | **yes — PP-StructureV2** | no | legacy `hOCR` | no |
| Table structure recognition (SLANet)   | **yes**   | no      | no          | no     |

## Language code cheat sheet

Each backend uses a different convention.

### PaddleOCR codes

`en`, `ch` (Chinese Simplified), `chinese_cht` (Traditional), `japan`, `korean`, `french`, `german`, `spanish`, `italian`, `portuguese`, `dutch`, `russian`, `ukrainian`, `polish`, `arabic`, `persian`, `hindi`, `thai`, `vietnamese`, `malay`, `turkish`, `bulgarian`, `greek`, `serbian_latin`, `maori`, `uyghur`, plus ~60 more. Full list: `https://github.com/PaddlePaddle/PaddleOCR/blob/main/ppocr/utils/dict/`.

**Paddle is single-language-per-instance.** To OCR a mixed-language document, run once per language and merge results, or use the special `multilingual` rec model (~30 Latin-based languages in one pass).

### EasyOCR codes

Two-letter ISO: `en`, `ja`, `zh` (Simplified), `zh_tra` (Traditional), `ko`, `ru`, `ar`, `fa`, `hi`, `th`, `vi`, `fr`, `de`, `es`, `it`, `pt`, `nl`, `ru`, `uk`, `tr`, `pl`, `cs`, `el`, `bg`, `mn`, `ta`, `te`, `kn`, `ml`, `ur`, `az`, `kk`, `uz`, `he`, plus ~50 more. Full list: `https://www.jaided.ai/easyocr/`.

**EasyOCR accepts multiple languages per call**: `Reader(['en', 'ja'])`. Combines scripts from the loaded recognizers; useful for mixed English+CJK receipts.

### Tesseract 5 codes

Three-letter: `eng`, `jpn`, `chi_sim`, `chi_tra`, `kor`, `ara`, `heb`, `rus`, `ukr`, `fra`, `deu`, `spa`, `ita`, `por`, `nld`, `tur`, `pol`, `ces`, `hun`, `hin`, `tam`, `tel`, `ben`, `guj`, `mal`, `kan`, `tha`, `vie`, `khm`, `mya`. The legacy 100+ list lives at `https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html`.

**Combine with `+`**: `-l eng+jpn`. Tesseract 5 runs them all simultaneously via the LSTM backend.

### TrOCR variants

TrOCR is English-only. Variants gate *content* (handwritten vs printed) and *size*:

- `microsoft/trocr-small-handwritten`
- `microsoft/trocr-base-handwritten` (default)
- `microsoft/trocr-large-handwritten`
- `microsoft/trocr-small-printed`
- `microsoft/trocr-base-printed`
- `microsoft/trocr-large-printed`

For non-English handwriting in 2026, no open-source + commercial-safe model really works end-to-end. PaddleOCR is the least bad fallback for non-English printed.

## Picking for a task

### "Japanese menu photo"
→ PaddleOCR with `--lang japan`. Or EasyOCR with `['ja']`. Paddle is slightly better on stylized signage; EasyOCR installs faster.

### "English + Japanese on the same page"
→ EasyOCR with `['en', 'ja']`. Paddle can't mix in one call (you'd run twice).

### "Handwritten shopping list"
→ TrOCR `base-handwritten` with `--detect paddle` to pre-segment lines. Expect ~60–80% word accuracy on legible handwriting, much worse on messy cursive.

### "Arabic news scan"
→ PaddleOCR with `--lang arabic`. Tesseract's `ara` works but outputs in visual LTR — reorder with python-bidi.

### "Multi-column academic PDF"
→ Rasterize with `magick in.pdf page_%03d.png`, then `ocr.py layout --model paddle --in page_001.png` to get reading-order + column layout. `regions[*].type == "text"` preserves paragraph structure.

### "100-language support, CPU only, no deps"
→ Tesseract 5. `brew install tesseract tesseract-lang` — one binary, all languages.

## Known language gaps

Even the union of all four backends has blind spots:

- **Ancient scripts** (Cuneiform, Egyptian Hieroglyphs, Phoenician) — no OCR support anywhere. Consider `Transkribus` (proprietary, research-licensed).
- **Low-resource African scripts** (Ge'ez/Amharic, Tifinagh) — PaddleOCR has experimental Amharic; Tifinagh is not supported.
- **Stylized gothic / blackletter** — Tesseract `frk` (Fraktur) works on 19th-century German. Other blackletter variants need custom `.traineddata` fine-tuning.
- **Historical long-s / ligatures** — post-process; no model handles them natively.

## Confidence scoring interpretation

All four backends return a `confidence` in 0..1 (or 0..100 for Tesseract's raw `conf`). Rules of thumb:

- `> 0.9` — trust it.
- `0.5–0.9` — review if downstream is sensitive.
- `< 0.5` — likely garbage; reject or re-OCR with a different backend.

For critical pipelines (invoice processing, ID parsing) **always run two backends** and flag disagreements for human review.
