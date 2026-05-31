#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "paddlepaddle>=2.6",
#   "paddleocr>=2.7",
#   "easyocr>=1.7",
#   "pytesseract>=0.3.10",
#   "transformers>=4.40",
#   "torch>=2.2",
#   "opencv-python>=4.9",
#   "numpy>=1.24",
#   "pillow>=10.0",
# ]
# ///
"""
ocr.py - multi-backend OCR CLI for media-ocr-ai skill.

Subcommands:
  extract       - plain text extraction (any backend)
  layout        - PP-StructureV2 layout analysis (paddle only)
  handwriting   - TrOCR line-level recognition, paddle pre-segment
  multi-lang    - multilingual extraction (paddle / easy / tesseract)
  table         - PaddleOCR table-structure-recognition -> CSV
  install       - pre-download / pre-install backend models

Non-interactive. All params via flags. Each supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    print("error: opencv-python not importable. run via `uv run`.", file=sys.stderr)
    sys.exit(1)


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[ocr] {msg}", file=sys.stderr)


def _emit_plan(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[ocr.plan] {msg}", file=sys.stderr)


def _read_image(path: str | Path) -> np.ndarray:
    arr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if arr is None:
        arr = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    return arr


# ---------------------------------------------------------------------------
# Backends - lazy-imported
# ---------------------------------------------------------------------------


def _paddle(lang: str = "en", use_angle_cls: bool = True):
    from paddleocr import PaddleOCR  # noqa: WPS433

    return PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, show_log=False)


def _paddle_struct(lang: str = "en"):
    from paddleocr import PPStructure  # noqa: WPS433

    return PPStructure(table=True, ocr=True, lang=lang, show_log=False)


def _easy(langs: list[str]):
    import easyocr  # noqa: WPS433

    return easyocr.Reader(langs)


def _tess_langs(codes: list[str]) -> str:
    # PaddleOCR "en" -> Tesseract "eng". Minimal mapping.
    m = {
        "en": "eng",
        "ja": "jpn",
        "zh": "chi_sim",
        "ch": "chi_sim",
        "ko": "kor",
        "ar": "ara",
        "ru": "rus",
        "fr": "fra",
        "de": "deu",
        "es": "spa",
        "it": "ita",
        "pt": "por",
        "he": "heb",
        "hi": "hin",
        "th": "tha",
    }
    return "+".join(m.get(c, c) for c in codes)


def _trocr(variant: str, device: str):
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # noqa: WPS433

    model_id = f"microsoft/trocr-{variant}"
    processor = TrOCRProcessor.from_pretrained(model_id)
    model = VisionEncoderDecoderModel.from_pretrained(model_id).to(device)
    model.eval()
    return processor, model


def _pick_device(requested: str, verbose: bool) -> str:
    import torch  # noqa: WPS433

    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    _trace("auto device: cpu", verbose)
    return "cpu"


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def _blocks_to_text(blocks: list[dict]) -> str:
    return "\n".join(b["text"] for b in blocks)


def _blocks_to_json(blocks: list[dict]) -> str:
    return json.dumps({"blocks": blocks}, ensure_ascii=False, indent=2)


def _blocks_to_tsv(blocks: list[dict]) -> str:
    lines = ["x\ty\tw\th\tconf\ttext"]
    for b in blocks:
        x, y, w, h = b["bbox"]
        lines.append(f"{x}\t{y}\t{w}\t{h}\t{b.get('confidence', ''):.4f}\t{b['text']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand: install
# ---------------------------------------------------------------------------


def cmd_install(args: argparse.Namespace) -> int:
    target = args.target
    _emit_plan(f"install target={target}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] would install: {target}")
        return 0

    if target == "paddle":
        _trace("triggering paddleocr first-use model download", args.verbose)
        p = _paddle(lang=args.lang or "en")
        _ = p  # noqa: WPS122
        print("ok: paddleocr ready")
    elif target == "easy":
        langs = (args.lang or "en").split(",")
        _trace(f"triggering easyocr model download for {langs}", args.verbose)
        r = _easy(langs)
        _ = r
        print("ok: easyocr ready")
    elif target == "tesseract":
        # binary must be system-installed. verify.
        import pytesseract  # noqa: WPS433

        try:
            version = pytesseract.get_tesseract_version()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "tesseract binary not on PATH. "
                "brew install tesseract tesseract-lang (macOS) / apt install tesseract-ocr (Debian)."
            ) from exc
        print(f"ok: tesseract {version}")
    elif target == "trocr":
        device = _pick_device(args.device, args.verbose)
        variant = args.variant or "base-handwritten"
        _trace(f"downloading trocr-{variant} on {device}", args.verbose)
        _ = _trocr(variant, device)
        print(f"ok: trocr-{variant} cached")
    else:
        raise ValueError(f"unknown install target: {target!r}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: extract
# ---------------------------------------------------------------------------


def _extract_paddle(image_path: Path, lang: str) -> list[dict]:
    p = _paddle(lang=lang)
    result = p.ocr(str(image_path), cls=True)
    # result is list of pages; single-page lists[0] is a list of [box, (text, conf)]
    blocks: list[dict] = []
    if not result:
        return blocks
    page = result[0] if result else []
    if page is None:
        return blocks
    for item in page:
        box = item[0]
        text, conf = item[1]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = int(min(xs)), int(min(ys))
        w = int(max(xs) - min(xs))
        h = int(max(ys) - min(ys))
        blocks.append({"bbox": [x, y, w, h], "text": text, "confidence": float(conf)})
    return blocks


def _extract_easy(image_path: Path, langs: list[str]) -> list[dict]:
    r = _easy(langs)
    out = r.readtext(str(image_path))
    blocks: list[dict] = []
    for box, text, conf in out:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = int(min(xs)), int(min(ys))
        w = int(max(xs) - min(xs))
        h = int(max(ys) - min(ys))
        blocks.append({"bbox": [x, y, w, h], "text": text, "confidence": float(conf)})
    return blocks


def _extract_tesseract(image_path: Path, lang_codes: list[str]) -> list[dict]:
    import pytesseract  # noqa: WPS433

    lang = _tess_langs(lang_codes)
    img = _read_image(image_path)
    data = pytesseract.image_to_data(
        img, lang=lang, output_type=pytesseract.Output.DICT
    )
    blocks: list[dict] = []
    for i, text in enumerate(data["text"]):
        if not text or not text.strip():
            continue
        conf = (
            float(data["conf"][i])
            if str(data["conf"][i]).lstrip("-").isdigit()
            else -1.0
        )
        if conf < 0:
            continue
        blocks.append(
            {
                "bbox": [
                    int(data["left"][i]),
                    int(data["top"][i]),
                    int(data["width"][i]),
                    int(data["height"][i]),
                ],
                "text": text,
                "confidence": conf / 100.0,
            }
        )
    return blocks


def cmd_extract(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    lang = args.lang or "en"
    _emit_plan(
        f"extract model={args.model} lang={lang} in={path} out-format={args.out_format}",
        args.verbose,
    )
    if args.dry_run:
        print(f"[dry-run] extract {args.model} {path}")
        return 0

    if args.model == "paddle":
        blocks = _extract_paddle(path, lang)
    elif args.model == "easy":
        blocks = _extract_easy(path, lang.split(","))
    elif args.model == "tesseract":
        blocks = _extract_tesseract(path, lang.split(","))
    elif args.model == "trocr":
        raise SystemExit(
            "trocr is line-level; use the 'handwriting' subcommand with --detect paddle."
        )
    else:
        raise ValueError(f"unknown --model {args.model!r}")

    if args.out_format == "text":
        out_str = _blocks_to_text(blocks)
    elif args.out_format == "json":
        out_str = _blocks_to_json(blocks)
    elif args.out_format == "tsv":
        out_str = _blocks_to_tsv(blocks)
    else:
        raise ValueError(f"unknown out-format: {args.out_format!r}")

    print(out_str)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: layout (paddle only)
# ---------------------------------------------------------------------------


def cmd_layout(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    if args.model != "paddle":
        print("error: --model must be 'paddle' for layout analysis", file=sys.stderr)
        return 2
    out_json = Path(args.out_json)
    lang = args.lang or "en"
    _emit_plan(f"layout paddle lang={lang} in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] layout paddle {path}")
        return 0

    engine = _paddle_struct(lang=lang)
    img = _read_image(path)
    result = engine(img)

    regions = []
    for r in result:
        region = {"type": r.get("type"), "bbox": r.get("bbox")}
        res = r.get("res") or {}
        if region["type"] == "table":
            region["html"] = res.get("html") if isinstance(res, dict) else None
        else:
            if isinstance(res, list):
                region["text"] = "\n".join(
                    x.get("text", "") for x in res if isinstance(x, dict)
                )
            elif isinstance(res, dict):
                region["text"] = res.get("text", "")
            else:
                region["text"] = ""
        regions.append(region)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"regions": regions}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"ok: wrote {out_json}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: handwriting (trocr, optional paddle detect)
# ---------------------------------------------------------------------------


def _detect_lines_paddle(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    from paddleocr import PaddleOCR  # noqa: WPS433

    det = PaddleOCR(det=True, rec=False, use_angle_cls=False, lang="en", show_log=False)
    out = det.ocr(image, rec=False, cls=False)
    if not out or not out[0]:
        return []
    boxes = out[0]
    out_boxes: list[tuple[int, int, int, int]] = []
    for box in boxes:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = int(min(xs)), int(min(ys))
        w = int(max(xs) - min(xs))
        h = int(max(ys) - min(ys))
        out_boxes.append((x, y, w, h))
    # sort top-to-bottom, left-to-right
    out_boxes.sort(key=lambda b: (b[1], b[0]))
    return out_boxes


def cmd_handwriting(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    if args.model != "trocr":
        print("error: --model must be 'trocr'", file=sys.stderr)
        return 2

    device = _pick_device(args.device, args.verbose)
    variant = args.variant or "base-handwritten"
    _emit_plan(f"handwriting trocr variant={variant} device={device}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] trocr {variant} on {path}")
        return 0

    processor, model = _trocr(variant, device)

    img = _read_image(path)
    if args.detect == "paddle":
        boxes = _detect_lines_paddle(img)
        if not boxes:
            boxes = [(0, 0, img.shape[1], img.shape[0])]
    else:
        boxes = [(0, 0, img.shape[1], img.shape[0])]

    from PIL import Image  # noqa: WPS433
    import torch  # noqa: WPS433

    lines: list[str] = []
    with torch.no_grad():
        for x, y, w, h in boxes:
            crop = img[max(0, y) : y + h, max(0, x) : x + w]
            if crop.size == 0:
                continue
            pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            pixel_values = processor(images=pil, return_tensors="pt").pixel_values.to(
                device
            )
            out_ids = model.generate(pixel_values, max_new_tokens=128)
            text = processor.batch_decode(out_ids, skip_special_tokens=True)[0]
            lines.append(text)

    text_out = "\n".join(lines)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text_out, encoding="utf-8")
    print(f"ok: wrote {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: multi-lang
# ---------------------------------------------------------------------------


def cmd_multi_lang(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    if not langs:
        print(
            "error: --langs must be a non-empty comma-separated list", file=sys.stderr
        )
        return 2
    _emit_plan(f"multi-lang model={args.model} langs={langs} in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] multi-lang {args.model} langs={langs}")
        return 0

    if args.model == "paddle":
        # paddle: pick first lang as primary; paddle runs best single-lang per call
        primary = langs[0]
        blocks = _extract_paddle(path, primary)
    elif args.model == "easy":
        blocks = _extract_easy(path, langs)
    elif args.model == "tesseract":
        blocks = _extract_tesseract(path, langs)
    else:
        raise ValueError(f"multi-lang not supported for model {args.model!r}")

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"langs": langs, "blocks": blocks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"ok: wrote {out_json}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: table
# ---------------------------------------------------------------------------


def _html_table_to_csv(html: str) -> list[list[str]]:
    """Minimal HTML-table parser. Handles <table><tr><td>...</td></tr></table>."""
    rows: list[list[str]] = []
    # Split rows
    for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S):
        row_html = row_match.group(1)
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.I | re.S)
        cleaned = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        rows.append(cleaned)
    return rows


def cmd_table(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    if args.model != "paddle":
        print("error: --model must be 'paddle' for table extraction", file=sys.stderr)
        return 2
    out_csv = Path(args.out_csv)
    _emit_plan(f"table paddle in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] table paddle {path}")
        return 0

    engine = _paddle_struct(lang=args.lang or "en")
    img = _read_image(path)
    result = engine(img)
    tables = [r for r in result if r.get("type") == "table"]
    if not tables:
        print("warn: no table regions detected", file=sys.stderr)
        return 0

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    for idx, t in enumerate(tables):
        html = (
            (t.get("res") or {}).get("html") if isinstance(t.get("res"), dict) else None
        )
        rows = _html_table_to_csv(html or "")
        dest = (
            out_csv if idx == 0 else out_csv.with_name(f"{out_csv.stem}_table{idx}.csv")
        )
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)
        print(f"ok: wrote {dest}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="runtime device for neural backends",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ocr.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="plain text extraction")
    pe.add_argument(
        "--model", required=True, choices=["paddle", "easy", "tesseract", "trocr"]
    )
    pe.add_argument("--in", dest="inp", required=True)
    pe.add_argument("--lang", default=None)
    pe.add_argument("--out-format", default="text", choices=["text", "json", "tsv"])
    _add_common(pe)
    pe.set_defaults(func=cmd_extract)

    pl = sub.add_parser("layout", help="structured layout (paddle only)")
    pl.add_argument("--model", default="paddle", choices=["paddle"])
    pl.add_argument("--in", dest="inp", required=True)
    pl.add_argument("--out-json", required=True)
    pl.add_argument("--lang", default="en")
    _add_common(pl)
    pl.set_defaults(func=cmd_layout)

    ph = sub.add_parser("handwriting", help="line-level handwriting via trocr")
    ph.add_argument("--model", default="trocr", choices=["trocr"])
    ph.add_argument("--in", dest="inp", required=True)
    ph.add_argument("--out", required=True)
    ph.add_argument(
        "--variant",
        default="base-handwritten",
        choices=[
            "small-handwritten",
            "base-handwritten",
            "large-handwritten",
            "small-printed",
            "base-printed",
            "large-printed",
        ],
    )
    ph.add_argument("--detect", default="none", choices=["none", "paddle"])
    _add_common(ph)
    ph.set_defaults(func=cmd_handwriting)

    pm = sub.add_parser("multi-lang", help="multilingual extraction")
    pm.add_argument("--model", required=True, choices=["paddle", "easy", "tesseract"])
    pm.add_argument("--in", dest="inp", required=True)
    pm.add_argument("--langs", required=True, help="comma-separated language codes")
    pm.add_argument("--out-json", required=True)
    _add_common(pm)
    pm.set_defaults(func=cmd_multi_lang)

    pt = sub.add_parser("table", help="paddle table-structure -> CSV")
    pt.add_argument("--model", default="paddle", choices=["paddle"])
    pt.add_argument("--in", dest="inp", required=True)
    pt.add_argument("--out-csv", required=True)
    pt.add_argument("--lang", default="en")
    _add_common(pt)
    pt.set_defaults(func=cmd_table)

    pi = sub.add_parser("install", help="pre-install / pre-download a backend")
    pi.add_argument("target", choices=["paddle", "easy", "tesseract", "trocr"])
    pi.add_argument("--lang", default=None)
    pi.add_argument("--variant", default=None)
    _add_common(pi)
    pi.set_defaults(func=cmd_install)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
