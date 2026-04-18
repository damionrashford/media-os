#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "transformers>=4.40",
#   "torch>=2.2",
#   "open_clip_torch>=2.24",
#   "sentence-transformers>=2.7",
#   "opencv-python>=4.9",
#   "numpy>=1.24",
#   "pillow>=10.0",
# ]
# ///
"""
tag.py - AI image/video tagging + captioning + zero-shot classification.

Subcommands:
  caption         - single-image caption (blip2 or llava)
  classify        - zero-shot classification against custom labels (clip or siglip)
  describe        - visual QA / dense description (llava)
  search          - build CLIP embedding index, and query it by text
  tag-batch       - bulk-tag a folder into CSV (clip or siglip)
  video-describe  - per-frame LLaVA on a video at --sample-fps
  install         - pre-download model weights

Non-interactive. No prompts. All params via flags. Each supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    import cv2
except ImportError:
    print("error: opencv-python not importable. run via `uv run`.", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("error: Pillow not importable. run via `uv run`.", file=sys.stderr)
    sys.exit(1)


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[tag] {msg}", file=sys.stderr)


def _emit_plan(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[tag.plan] {msg}", file=sys.stderr)


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


def _dtype_for(device: str):
    import torch  # noqa: WPS433

    if device == "cuda":
        return torch.float16
    return torch.float32


# ---------------------------------------------------------------------------
# Model loaders - lazy
# ---------------------------------------------------------------------------


def _load_clip(model_name: str, device: str):
    import open_clip  # noqa: WPS433

    # default: ViT-B-32 / openai
    name, pretrained = (model_name.split(",", 1) + [None])[:2]
    model, _, preprocess = open_clip.create_model_and_transforms(
        name or "ViT-B-32", pretrained=pretrained or "openai"
    )
    tokenizer = open_clip.get_tokenizer(name or "ViT-B-32")
    model = model.to(device).eval()
    return {
        "kind": "clip",
        "model": model,
        "preprocess": preprocess,
        "tokenizer": tokenizer,
        "device": device,
    }


def _load_siglip(model_name: str, device: str):
    from transformers import AutoModel, AutoProcessor  # noqa: WPS433

    hf_id = model_name or "google/siglip-base-patch16-384"
    processor = AutoProcessor.from_pretrained(hf_id)
    model = AutoModel.from_pretrained(hf_id).to(device).eval()
    return {"kind": "siglip", "model": model, "processor": processor, "device": device}


def _load_blip2(model_name: str, device: str):
    from transformers import (
        Blip2ForConditionalGeneration,
        Blip2Processor,
    )  # noqa: WPS433

    hf_id = model_name or "Salesforce/blip2-opt-2.7b"
    processor = Blip2Processor.from_pretrained(hf_id)
    model = (
        Blip2ForConditionalGeneration.from_pretrained(
            hf_id, torch_dtype=_dtype_for(device)
        )
        .to(device)
        .eval()
    )
    return {"kind": "blip2", "model": model, "processor": processor, "device": device}


def _load_llava(model_name: str, device: str):
    from transformers import (
        AutoProcessor,
        LlavaForConditionalGeneration,
    )  # noqa: WPS433

    hf_id = model_name or "llava-hf/llava-1.5-7b-hf"
    processor = AutoProcessor.from_pretrained(hf_id)
    model = (
        LlavaForConditionalGeneration.from_pretrained(
            hf_id, torch_dtype=_dtype_for(device)
        )
        .to(device)
        .eval()
    )
    return {"kind": "llava", "model": model, "processor": processor, "device": device}


MODEL_LOADERS = {
    "clip": _load_clip,
    "siglip": _load_siglip,
    "blip2": _load_blip2,
    "llava": _load_llava,
}


def _load(kind: str, model_name: str | None, device: str):
    if kind not in MODEL_LOADERS:
        raise ValueError(f"unknown model: {kind}")
    return MODEL_LOADERS[kind](model_name or "", device)


# ---------------------------------------------------------------------------
# CLIP embedding helpers
# ---------------------------------------------------------------------------


def _clip_encode_image(handle: dict, pil_img: Image.Image) -> np.ndarray:
    import torch  # noqa: WPS433

    img_tensor = handle["preprocess"](pil_img).unsqueeze(0).to(handle["device"])
    with torch.no_grad():
        feats = handle["model"].encode_image(img_tensor)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.detach().cpu().float().numpy()[0]


def _clip_encode_text(handle: dict, texts: list[str]) -> np.ndarray:
    import torch  # noqa: WPS433

    tokens = handle["tokenizer"](texts).to(handle["device"])
    with torch.no_grad():
        feats = handle["model"].encode_text(tokens)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.detach().cpu().float().numpy()


def _siglip_scores(handle: dict, pil_img: Image.Image, labels: list[str]) -> np.ndarray:
    import torch  # noqa: WPS433

    processor = handle["processor"]
    inputs = processor(
        text=labels, images=pil_img, return_tensors="pt", padding="max_length"
    ).to(handle["device"])
    with torch.no_grad():
        out = handle["model"](**inputs)
    # sigmoid(logits_per_image) - independent per-label probabilities
    probs = torch.sigmoid(out.logits_per_image).detach().cpu().float().numpy()[0]
    return probs


# ---------------------------------------------------------------------------
# Subcommand: install
# ---------------------------------------------------------------------------


def cmd_install(args: argparse.Namespace) -> int:
    _emit_plan(f"install target={args.target} name={args.name}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] install {args.target}")
        return 0
    device = _pick_device(args.device, args.verbose)
    handle = _load(args.target, args.name, device)
    print(f"ok: {args.target} loaded ({handle['kind']})")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: caption
# ---------------------------------------------------------------------------


def _blip2_caption(
    handle: dict, pil: Image.Image, prompt: str | None, beams: int
) -> str:
    import torch  # noqa: WPS433

    processor = handle["processor"]
    text = prompt if prompt else ""
    inputs = processor(images=pil, text=text, return_tensors="pt").to(handle["device"])
    with torch.no_grad():
        ids = handle["model"].generate(**inputs, max_new_tokens=80, num_beams=beams)
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip()


def _llava_caption(handle: dict, pil: Image.Image, prompt: str, max_new: int) -> str:
    import torch  # noqa: WPS433

    processor = handle["processor"]
    conv = prompt
    if "<image>" not in conv:
        conv = f"USER: <image>\n{conv}\nASSISTANT:"
    inputs = processor(images=pil, text=conv, return_tensors="pt").to(handle["device"])
    with torch.no_grad():
        ids = handle["model"].generate(
            **inputs, max_new_tokens=max_new, do_sample=False
        )
    out = processor.batch_decode(ids, skip_special_tokens=True)[0]
    # trim to the part after "ASSISTANT:"
    if "ASSISTANT:" in out:
        out = out.split("ASSISTANT:", 1)[1].strip()
    return out.strip()


def cmd_caption(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    _emit_plan(f"caption model={args.model} in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] caption {args.model} {path}")
        return 0

    device = _pick_device(args.device, args.verbose)
    handle = _load(args.model, args.name, device)
    pil = Image.open(path).convert("RGB")

    if args.model == "blip2":
        text = _blip2_caption(handle, pil, args.prompt, args.beams)
    elif args.model == "llava":
        prompt = args.prompt or "Describe this image in one short sentence."
        text = _llava_caption(handle, pil, prompt, args.max_new_tokens)
    else:
        raise ValueError(f"caption unsupported for model {args.model!r}")

    if args.out_text:
        Path(args.out_text).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_text).write_text(text + "\n", encoding="utf-8")
        print(f"ok: wrote {args.out_text}")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: classify
# ---------------------------------------------------------------------------


def cmd_classify(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    if not labels:
        print("error: --labels must be non-empty comma-separated", file=sys.stderr)
        return 2
    _emit_plan(f"classify model={args.model} labels={labels} in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] classify {args.model} {len(labels)} labels")
        return 0

    device = _pick_device(args.device, args.verbose)
    handle = _load(args.model, args.name, device)
    pil = Image.open(path).convert("RGB")

    if args.model == "clip":
        img_feat = _clip_encode_image(handle, pil)
        txt_feat = _clip_encode_text(handle, labels)
        scores = (txt_feat @ img_feat).tolist()
    elif args.model == "siglip":
        scores = _siglip_scores(handle, pil, labels).tolist()
    else:
        raise ValueError(f"classify unsupported for model {args.model!r}")

    ranked = sorted(
        [{"label": lbl, "score": float(s)} for lbl, s in zip(labels, scores)],
        key=lambda x: -x["score"],
    )
    top = ranked[: args.top_k]
    print(json.dumps({"top": top}, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: describe (LLaVA VQA)
# ---------------------------------------------------------------------------


def cmd_describe(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    if args.model != "llava":
        print("error: --model must be 'llava'", file=sys.stderr)
        return 2
    _emit_plan(f"describe llava in={path}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] describe llava {path}")
        return 0

    device = _pick_device(args.device, args.verbose)
    handle = _load("llava", args.name, device)
    pil = Image.open(path).convert("RGB")
    prompt = args.prompt or "Describe this image in detail."
    text = _llava_caption(handle, pil, prompt, args.max_new_tokens)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"ok: wrote {args.out}")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: search
# ---------------------------------------------------------------------------


def _list_images(root: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts
    )


def cmd_search(args: argparse.Namespace) -> int:
    if args.model not in ("clip", "siglip"):
        print("error: --model must be 'clip' or 'siglip'", file=sys.stderr)
        return 2
    if args.query and not args.index:
        print("error: --query requires --index (an existing .npz)", file=sys.stderr)
        return 2

    device = _pick_device(args.device, args.verbose)
    handle = _load(args.model, args.name, device)

    # Build mode
    if args.index and Path(args.index).is_dir():
        index_dir = Path(args.index)
        out_path = Path(args.index_out or (index_dir.name + "_index.npz"))
        _emit_plan(
            f"search build {args.model} dir={index_dir} out={out_path}", args.verbose
        )
        if args.dry_run:
            print(f"[dry-run] would build index from {index_dir}")
            return 0

        files = _list_images(index_dir)
        if not files:
            print(f"warn: no images found in {index_dir}", file=sys.stderr)
            return 0

        feats: list[np.ndarray] = []
        for i, p in enumerate(files):
            pil = Image.open(p).convert("RGB")
            if args.model == "clip":
                feat = _clip_encode_image(handle, pil)
            else:
                # SigLIP image embedding
                import torch  # noqa: WPS433

                inputs = handle["processor"](images=pil, return_tensors="pt").to(device)
                with torch.no_grad():
                    img_feat = handle["model"].get_image_features(**inputs)
                img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
                feat = img_feat.detach().cpu().float().numpy()[0]
            feats.append(feat)
            if args.verbose and i % 50 == 0:
                _trace(f"embed {i}/{len(files)}", args.verbose)

        embeddings = np.stack(feats, axis=0).astype(np.float32)
        np.savez(
            str(out_path),
            files=np.array([str(p) for p in files]),
            embeddings=embeddings,
        )
        print(f"ok: wrote {out_path} ({len(files)} images)")
        return 0

    # Query mode
    if not args.index or not Path(args.index).is_file():
        print(
            "error: --index must be a folder (to build) or a .npz (to query)",
            file=sys.stderr,
        )
        return 2

    data = np.load(str(args.index), allow_pickle=True)
    files = data["files"].tolist()
    embs = data["embeddings"]

    if args.model == "clip":
        q = _clip_encode_text(handle, [args.query])[0]
    else:
        import torch  # noqa: WPS433

        inputs = handle["processor"](
            text=[args.query], return_tensors="pt", padding=True
        ).to(device)
        with torch.no_grad():
            q_feat = handle["model"].get_text_features(**inputs)
        q_feat = q_feat / q_feat.norm(dim=-1, keepdim=True)
        q = q_feat.detach().cpu().float().numpy()[0]

    sims = embs @ q
    idx = np.argsort(-sims)[: args.top_k]
    results = [{"file": files[i], "score": float(sims[i])} for i in idx]
    print(
        json.dumps(
            {"query": args.query, "results": results}, ensure_ascii=False, indent=2
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: tag-batch
# ---------------------------------------------------------------------------


def cmd_tag_batch(args: argparse.Namespace) -> int:
    if args.model not in ("clip", "siglip"):
        print("error: --model must be 'clip' or 'siglip'", file=sys.stderr)
        return 2
    in_dir = Path(args.in_dir)
    if not in_dir.is_dir():
        print(f"error: --in-dir must be a directory: {in_dir}", file=sys.stderr)
        return 2
    tags_file = Path(args.tags_file)
    if not tags_file.is_file():
        print(f"error: --tags-file not found: {tags_file}", file=sys.stderr)
        return 2
    labels = [
        line.strip() for line in tags_file.read_text().splitlines() if line.strip()
    ]

    _emit_plan(
        f"tag-batch model={args.model} dir={in_dir} labels={len(labels)}", args.verbose
    )
    if args.dry_run:
        print(f"[dry-run] would tag {in_dir} with {len(labels)} labels")
        return 0

    device = _pick_device(args.device, args.verbose)
    handle = _load(args.model, args.name, device)

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if args.model == "clip":
        txt_feat = _clip_encode_text(handle, labels)

    files = _list_images(in_dir)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["file", "label", "score"])
        for i, p in enumerate(files):
            pil = Image.open(p).convert("RGB")
            if args.model == "clip":
                img_feat = _clip_encode_image(handle, pil)
                sc = (txt_feat @ img_feat).tolist()
            else:
                sc = _siglip_scores(handle, pil, labels).tolist()
            ranked = sorted(
                [(lbl, float(s)) for lbl, s in zip(labels, sc)], key=lambda x: -x[1]
            )
            written = 0
            for lbl, s in ranked:
                if written >= args.top_k:
                    break
                if s < args.threshold:
                    break
                writer.writerow([str(p), lbl, f"{s:.4f}"])
                written += 1
            if args.verbose and i % 50 == 0:
                _trace(f"tagged {i}/{len(files)}", args.verbose)
    print(f"ok: wrote {out_csv}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: video-describe
# ---------------------------------------------------------------------------


def _iter_video_frames(
    path: str, sample_fps: float
) -> Iterable[tuple[float, np.ndarray]]:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video: {path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    stride = max(1, int(round(src_fps / max(sample_fps, 1e-6))))
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                t = idx / src_fps
                yield t, frame
            idx += 1
    finally:
        cap.release()


def cmd_video_describe(args: argparse.Namespace) -> int:
    path = Path(args.inp)
    if not path.exists():
        print(f"error: input not found: {path}", file=sys.stderr)
        return 2
    if args.model != "llava":
        print("error: --model must be 'llava'", file=sys.stderr)
        return 2
    _emit_plan(f"video-describe llava in={path} fps={args.sample_fps}", args.verbose)
    if args.dry_run:
        print(f"[dry-run] video-describe {path} at {args.sample_fps} fps")
        return 0

    device = _pick_device(args.device, args.verbose)
    handle = _load("llava", args.name, device)
    prompt = args.prompt or "Describe this frame in one short sentence."

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for t, frame in _iter_video_frames(str(path), args.sample_fps):
        pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        text = _llava_caption(handle, pil, prompt, args.max_new_tokens)
        row = {"t": round(t, 3), "text": text}
        rows.append(row)
        if args.verbose:
            _trace(f"t={t:.2f} text={text[:80]}", args.verbose)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"ok: wrote {out_path} ({len(rows)} rows)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    p.add_argument(
        "--name", default=None, help="override HuggingFace model id / clip name"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tag.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("caption", help="single-image caption")
    pc.add_argument("--model", default="blip2", choices=["blip2", "llava"])
    pc.add_argument("--in", dest="inp", required=True)
    pc.add_argument("--out-text", default=None)
    pc.add_argument("--prompt", default=None)
    pc.add_argument("--beams", type=int, default=5)
    pc.add_argument("--max-new-tokens", type=int, default=128)
    _add_common(pc)
    pc.set_defaults(func=cmd_caption)

    pcl = sub.add_parser("classify", help="zero-shot classification")
    pcl.add_argument("--model", default="clip", choices=["clip", "siglip"])
    pcl.add_argument("--in", dest="inp", required=True)
    pcl.add_argument("--labels", required=True, help="comma-separated")
    pcl.add_argument("--top-k", type=int, default=5)
    _add_common(pcl)
    pcl.set_defaults(func=cmd_classify)

    pd = sub.add_parser("describe", help="LLaVA VQA / dense description")
    pd.add_argument("--model", default="llava", choices=["llava"])
    pd.add_argument("--in", dest="inp", required=True)
    pd.add_argument("--prompt", default=None)
    pd.add_argument("--out", default=None)
    pd.add_argument("--max-new-tokens", type=int, default=256)
    _add_common(pd)
    pd.set_defaults(func=cmd_describe)

    ps = sub.add_parser("search", help="build / query CLIP embedding index")
    ps.add_argument("--model", default="clip", choices=["clip", "siglip"])
    ps.add_argument(
        "--index", required=True, help="folder (to build) or .npz (to query)"
    )
    ps.add_argument("--index-out", default=None, help="output .npz path when building")
    ps.add_argument("--query", default=None)
    ps.add_argument("--top-k", type=int, default=10)
    _add_common(ps)
    ps.set_defaults(func=cmd_search)

    pt = sub.add_parser("tag-batch", help="bulk-tag a folder to CSV")
    pt.add_argument("--model", default="clip", choices=["clip", "siglip"])
    pt.add_argument("--in-dir", required=True)
    pt.add_argument("--tags-file", required=True)
    pt.add_argument("--out-csv", required=True)
    pt.add_argument("--top-k", type=int, default=5)
    pt.add_argument("--threshold", type=float, default=0.20)
    _add_common(pt)
    pt.set_defaults(func=cmd_tag_batch)

    pv = sub.add_parser("video-describe", help="per-frame LLaVA on a video")
    pv.add_argument("--model", default="llava", choices=["llava"])
    pv.add_argument("--in", dest="inp", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument("--sample-fps", type=float, default=1.0)
    pv.add_argument("--prompt", default=None)
    pv.add_argument("--max-new-tokens", type=int, default=96)
    _add_common(pv)
    pv.set_defaults(func=cmd_video_describe)

    pi = sub.add_parser("install", help="pre-download weights")
    pi.add_argument("target", choices=list(MODEL_LOADERS))
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
