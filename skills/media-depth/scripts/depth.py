#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "transformers>=4.40",
#   "torch>=2.2",
#   "opencv-python>=4.9",
#   "numpy>=1.24",
#   "pillow>=10.0",
# ]
# ///
"""
depth.py - monocular depth estimation CLI for media-depth skill.

Subcommands:
  image    - per-image depth map (PNG 16-bit / NPY / EXR)
  video    - per-frame depth for a video (MP4 grayscale / PNG seq / EXR seq)
  stereo   - depth-driven 2D-to-stereo pair (left / right PNG)
  parallax - 2.5D parallax animation (MP4) from image + depth
  install  - pre-download model weights into HuggingFace cache

Every subcommand is non-interactive. No prompts. All params via flags.
Each supports --dry-run and --verbose. The equivalent runtime config is
logged to stderr before model load.

Models: depthanything-v2 (sizes: small/base/large), midas (DPT-SwinV2-Tiny / DPT-BEiT-Large).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    print("error: opencv-python not importable. Run via `uv run`.", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("error: Pillow not importable. Run via `uv run`.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

MODEL_REGISTRY = {
    "depthanything-v2": {
        "small": "depth-anything/Depth-Anything-V2-Small-hf",
        "base": "depth-anything/Depth-Anything-V2-Base-hf",
        "large": "depth-anything/Depth-Anything-V2-Large-hf",
    },
    "midas": {
        "tiny": "Intel/dpt-swinv2-tiny-256",
        "large": "Intel/dpt-beit-large-512",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[depth] {msg}", file=sys.stderr)


def _emit_plan(cmd_like: str, verbose: bool) -> None:
    if verbose:
        print(f"[depth.plan] {cmd_like}", file=sys.stderr)


def _pick_device(requested: str, verbose: bool) -> str:
    import torch  # noqa: WPS433 - late import is fine

    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        _trace("auto device: cuda", verbose)
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        _trace("auto device: mps", verbose)
        return "mps"
    _trace("auto device: cpu", verbose)
    return "cpu"


def _resolve_model(model: str, size: str | None) -> str:
    if model not in MODEL_REGISTRY:
        raise ValueError(
            f"unknown --model {model!r}. expected one of: " f"{sorted(MODEL_REGISTRY)}"
        )
    table = MODEL_REGISTRY[model]
    if size is None:
        size = next(iter(table))
    if size not in table:
        raise ValueError(
            f"unknown --size {size!r} for model {model!r}. expected one of: "
            f"{sorted(table)}"
        )
    return table[size]


def _load_pipeline(hf_id: str, device: str, verbose: bool):
    _trace(f"loading transformers pipeline: {hf_id} on {device}", verbose)
    from transformers import pipeline  # noqa: WPS433

    kwargs = {}
    # Use torch_dtype=float16 on cuda for speed. float32 elsewhere for stability.
    import torch  # noqa: WPS433

    if device == "cuda":
        kwargs["torch_dtype"] = torch.float16
    return pipeline(task="depth-estimation", model=hf_id, device=device, **kwargs)


def _infer_depth_pil(pipe, pil_img: Image.Image) -> np.ndarray:
    """Return float32 HxW inverse-depth array, arbitrary scale."""
    out = pipe(pil_img)
    depth = out["predicted_depth"] if "predicted_depth" in out else out["depth"]
    # pipeline returns either a torch Tensor or a PIL Image. Normalize to ndarray.
    if hasattr(depth, "cpu"):
        depth_np = depth.squeeze().detach().cpu().float().numpy()
    elif isinstance(depth, Image.Image):
        depth_np = np.asarray(depth, dtype=np.float32)
    else:
        depth_np = np.asarray(depth, dtype=np.float32)
    return depth_np


def _normalize_to_u16(depth: np.ndarray, invert: bool) -> np.ndarray:
    lo, hi = float(depth.min()), float(depth.max())
    if hi - lo < 1e-6:
        return np.zeros_like(depth, dtype=np.uint16)
    n = (depth - lo) / (hi - lo)
    if invert:
        n = 1.0 - n
    return (n * 65535.0).clip(0, 65535).astype(np.uint16)


def _normalize_to_u8(depth: np.ndarray, invert: bool) -> np.ndarray:
    u16 = _normalize_to_u16(depth, invert)
    return (u16 >> 8).astype(np.uint8)


def _resize_like(depth: np.ndarray, h: int, w: int) -> np.ndarray:
    if depth.shape[0] == h and depth.shape[1] == w:
        return depth
    return cv2.resize(depth.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _write_image_depth(
    depth: np.ndarray, out_path: Path, out_format: str, invert: bool, preview: bool
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_format == "png":
        img = _normalize_to_u16(depth, invert)
        cv2.imwrite(str(out_path), img)
    elif out_format == "npy":
        arr = depth.astype(np.float32)
        if invert:
            lo, hi = float(arr.min()), float(arr.max())
            if hi - lo > 1e-6:
                arr = (hi - arr) + lo
        np.save(str(out_path), arr)
    elif out_format == "exr":
        # requires OPENCV_IO_ENABLE_OPENEXR
        os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
        arr = depth.astype(np.float32)
        if invert:
            lo, hi = float(arr.min()), float(arr.max())
            if hi - lo > 1e-6:
                arr = (hi - arr) + lo
        ok = cv2.imwrite(str(out_path), arr)
        if not ok:
            raise RuntimeError(
                "cv2.imwrite failed for EXR; rebuild OpenCV with OpenEXR or use --out-format npy"
            )
    else:
        raise ValueError(f"unknown out_format: {out_format!r}")
    if preview:
        u8 = _normalize_to_u8(depth, invert)
        vis = cv2.applyColorMap(u8, cv2.COLORMAP_TURBO)
        preview_path = out_path.with_name(out_path.stem + "_preview.png")
        cv2.imwrite(str(preview_path), vis)


# ---------------------------------------------------------------------------
# Subcommand: install
# ---------------------------------------------------------------------------


def cmd_install(args: argparse.Namespace) -> int:
    hf_id = _resolve_model(args.model, args.size)
    _emit_plan(
        f"transformers.pipeline('depth-estimation', model='{hf_id}')", args.verbose
    )
    if args.dry_run:
        print(f"[dry-run] would download: {hf_id}")
        return 0
    device = _pick_device(args.device, args.verbose)
    pipe = _load_pipeline(hf_id, device, args.verbose)
    _trace(f"pipeline loaded: type={type(pipe).__name__}", args.verbose)
    print(f"ok: {hf_id} cached")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: image
# ---------------------------------------------------------------------------


def cmd_image(args: argparse.Namespace) -> int:
    in_path = Path(args.inp)
    out_path = Path(args.out)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    hf_id = _resolve_model(args.model, args.size)
    _emit_plan(
        f"depth.image model={hf_id} in={in_path} out={out_path} "
        f"format={args.out_format} invert={args.invert}",
        args.verbose,
    )
    if args.dry_run:
        print(f"[dry-run] model={hf_id} in={in_path} out={out_path}")
        return 0

    device = _pick_device(args.device, args.verbose)
    pipe = _load_pipeline(hf_id, device, args.verbose)

    pil = Image.open(in_path).convert("RGB")
    w, h = pil.size
    depth = _infer_depth_pil(pipe, pil)
    depth = _resize_like(depth, h, w)
    _write_image_depth(
        depth, out_path, args.out_format, args.invert, preview=not args.no_preview
    )
    print(f"ok: wrote {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: video
# ---------------------------------------------------------------------------


def _open_video(src: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video: {src}")
    return cap


def cmd_video(args: argparse.Namespace) -> int:
    in_path = Path(args.inp)
    out_path = Path(args.out)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    hf_id = _resolve_model(args.model, args.size)
    _emit_plan(
        f"depth.video model={hf_id} in={in_path} out={out_path} "
        f"format={args.out_format} smooth={args.smooth}",
        args.verbose,
    )
    if args.dry_run:
        print(f"[dry-run] model={hf_id} in={in_path} out={out_path}")
        return 0

    device = _pick_device(args.device, args.verbose)
    pipe = _load_pipeline(hf_id, device, args.verbose)

    cap = _open_video(str(in_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    _trace(f"video: {w}x{h}@{fps:.2f} frames={n_frames}", args.verbose)

    smooth_buf: list[np.ndarray] = []

    if args.out_format == "mp4":
        # Use ffmpeg via a PNG pipe for lossless greyscale frames.
        if shutil.which("ffmpeg") is None:
            print(
                "error: ffmpeg not on PATH (needed for --out-format mp4)",
                file=sys.stderr,
            )
            return 3
        tmpdir = Path(tempfile.mkdtemp(prefix="depth_"))
        idx = 0
        try:
            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                depth = _infer_depth_pil(pipe, pil)
                depth = _resize_like(depth, h, w)
                if args.smooth == "temporal":
                    smooth_buf.append(depth)
                    if len(smooth_buf) > 3:
                        smooth_buf.pop(0)
                    depth = np.mean(np.stack(smooth_buf, axis=0), axis=0)
                u8 = _normalize_to_u8(depth, args.invert)
                cv2.imwrite(str(tmpdir / f"f_{idx:06d}.png"), u8)
                idx += 1
                if args.verbose and idx % 30 == 0:
                    _trace(f"frame {idx}/{n_frames}", args.verbose)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            ff_cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                f"{fps}",
                "-i",
                str(tmpdir / "f_%06d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "18",
                str(out_path),
            ]
            _emit_plan(" ".join(ff_cmd), args.verbose)
            subprocess.run(ff_cmd, check=True)
        finally:
            cap.release()
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        out_path.mkdir(parents=True, exist_ok=True)
        idx = 0
        suffix = "png" if args.out_format == "png-seq" else "exr"
        try:
            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                depth = _infer_depth_pil(pipe, pil)
                depth = _resize_like(depth, h, w)
                if args.smooth == "temporal":
                    smooth_buf.append(depth)
                    if len(smooth_buf) > 3:
                        smooth_buf.pop(0)
                    depth = np.mean(np.stack(smooth_buf, axis=0), axis=0)
                frame_path = out_path / f"frame_{idx:06d}.{suffix}"
                if suffix == "png":
                    cv2.imwrite(str(frame_path), _normalize_to_u16(depth, args.invert))
                else:
                    os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
                    arr = depth.astype(np.float32)
                    if args.invert:
                        lo, hi = float(arr.min()), float(arr.max())
                        if hi - lo > 1e-6:
                            arr = (hi - arr) + lo
                    cv2.imwrite(str(frame_path), arr)
                idx += 1
                if args.verbose and idx % 30 == 0:
                    _trace(f"frame {idx}/{n_frames}", args.verbose)
        finally:
            cap.release()
    print(f"ok: wrote {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: stereo
# ---------------------------------------------------------------------------


def _forward_warp(image: np.ndarray, depth_u16: np.ndarray, shift: float) -> np.ndarray:
    """Depth-sorted forward warp with Z-buffer, then TELEA inpaint on holes."""
    h, w = image.shape[:2]
    # depth_u16: 65535 = nearest. normalize to 0..1
    d = depth_u16.astype(np.float32) / 65535.0
    # per-pixel horizontal shift in px. near = more shift.
    shifts = (d * shift).astype(np.float32)

    # Build destination image + hole mask via z-buffered forward scatter.
    dst = np.zeros_like(image)
    zbuf = np.full((h, w), -1.0, dtype=np.float32)
    mask = np.ones((h, w), dtype=np.uint8)

    xs = np.arange(w, dtype=np.float32)[None, :].repeat(h, axis=0)
    ys = np.arange(h, dtype=np.float32)[:, None].repeat(w, axis=1)
    new_x = xs + shifts
    new_x_int = np.clip(np.rint(new_x), 0, w - 1).astype(np.int32)
    ys_int = ys.astype(np.int32)

    # Scatter, preferring larger d (closer) at each dst pixel.
    flat_idx = ys_int * w + new_x_int
    order = np.argsort(d, axis=None)  # small first, large overwrites
    flat_idx_o = flat_idx.ravel()[order]
    src_flat = image.reshape(-1, image.shape[-1] if image.ndim == 3 else 1)[order]
    d_o = d.ravel()[order]

    dst_flat = dst.reshape(-1, dst.shape[-1] if dst.ndim == 3 else 1)
    zbuf_flat = zbuf.ravel()
    mask_flat = mask.ravel()
    for k in range(flat_idx_o.shape[0]):
        di = flat_idx_o[k]
        if d_o[k] >= zbuf_flat[di]:
            dst_flat[di] = src_flat[k]
            zbuf_flat[di] = d_o[k]
            mask_flat[di] = 0
    return cv2.inpaint(dst, mask, 3, cv2.INPAINT_TELEA)


def cmd_stereo(args: argparse.Namespace) -> int:
    in_path = Path(args.inp)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2
    out_L = Path(args.out_left)
    out_R = Path(args.out_right)

    _emit_plan(
        f"depth.stereo in={in_path} depth={args.depth} baseline={args.baseline}",
        args.verbose,
    )
    if args.dry_run:
        print(f"[dry-run] stereo from {in_path} with baseline={args.baseline}")
        return 0

    image = cv2.imread(str(in_path), cv2.IMREAD_COLOR)
    if image is None:
        print(f"error: cannot read image: {in_path}", file=sys.stderr)
        return 2

    if args.depth:
        depth_u16 = cv2.imread(str(args.depth), cv2.IMREAD_UNCHANGED)
        if depth_u16 is None:
            print(f"error: cannot read depth: {args.depth}", file=sys.stderr)
            return 2
        if depth_u16.dtype != np.uint16:
            depth_u16 = (depth_u16.astype(np.float32) * (65535.0 / 255.0)).astype(
                np.uint16
            )
    else:
        hf_id = _resolve_model(args.model, args.size)
        device = _pick_device(args.device, args.verbose)
        pipe = _load_pipeline(hf_id, device, args.verbose)
        pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        depth = _infer_depth_pil(pipe, pil)
        depth = _resize_like(depth, image.shape[0], image.shape[1])
        depth_u16 = _normalize_to_u16(depth, invert=False)

    left = _forward_warp(image, depth_u16, shift=+args.baseline / 2.0)
    right = _forward_warp(image, depth_u16, shift=-args.baseline / 2.0)
    out_L.parent.mkdir(parents=True, exist_ok=True)
    out_R.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_L), left)
    cv2.imwrite(str(out_R), right)
    print(f"ok: {out_L} {out_R}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: parallax
# ---------------------------------------------------------------------------


def _motion_offsets(
    motion: str, frames: int, amplitude: float
) -> list[tuple[float, float]]:
    """Return per-frame (dx, dy) offsets in px."""
    import math

    out: list[tuple[float, float]] = []
    for i in range(frames):
        t = i / max(1, frames - 1)
        if motion == "orbit":
            ang = 2.0 * math.pi * t
            out.append((amplitude * math.sin(ang), 0.4 * amplitude * math.cos(ang)))
        elif motion == "zoom":
            out.append((0.0, 0.0))  # zoom handled separately if desired
        elif motion == "pan-left":
            out.append((-amplitude * t, 0.0))
        elif motion == "pan-right":
            out.append((+amplitude * t, 0.0))
        elif motion == "ken-burns":
            out.append((amplitude * 0.3 * math.sin(math.pi * t), 0.0))
        else:
            out.append((0.0, 0.0))
    return out


def cmd_parallax(args: argparse.Namespace) -> int:
    in_img = Path(args.image)
    in_d = Path(args.depth)
    out = Path(args.out)
    if not in_img.exists():
        print(f"error: image not found: {in_img}", file=sys.stderr)
        return 2
    if not in_d.exists():
        print(f"error: depth not found: {in_d}", file=sys.stderr)
        return 2

    _emit_plan(
        f"depth.parallax image={in_img} depth={in_d} out={out} "
        f"motion={args.motion} frames={args.frames} fps={args.fps} amp={args.amplitude}",
        args.verbose,
    )
    if args.dry_run:
        print(f"[dry-run] would render {args.frames} frames at {args.fps} fps")
        return 0

    image = cv2.imread(str(in_img), cv2.IMREAD_COLOR)
    depth = cv2.imread(str(in_d), cv2.IMREAD_UNCHANGED)
    if image is None or depth is None:
        print("error: could not load image or depth", file=sys.stderr)
        return 2
    if depth.dtype != np.uint16:
        depth = (depth.astype(np.float32) * (65535.0 / 255.0)).astype(np.uint16)

    offsets = _motion_offsets(args.motion, args.frames, args.amplitude)
    tmpdir = Path(tempfile.mkdtemp(prefix="parallax_"))
    try:
        for i, (dx, _dy) in enumerate(offsets):
            frame = _forward_warp(image, depth, shift=dx)
            cv2.imwrite(str(tmpdir / f"f_{i:06d}.png"), frame)
            if args.verbose and i % 20 == 0:
                _trace(f"frame {i}/{args.frames}", args.verbose)
        if shutil.which("ffmpeg") is None:
            print(
                "error: ffmpeg not on PATH (needed to encode parallax MP4)",
                file=sys.stderr,
            )
            return 3
        out.parent.mkdir(parents=True, exist_ok=True)
        ff_cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            f"{args.fps}",
            "-i",
            str(tmpdir / "f_%06d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            str(out),
        ]
        _emit_plan(" ".join(ff_cmd), args.verbose)
        subprocess.run(ff_cmd, check=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"ok: wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true", help="plan only; no inference")
    p.add_argument("--verbose", action="store_true", help="log steps to stderr")
    p.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="runtime device selection (default: auto)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="depth.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("install", help="pre-download model weights")
    pi.add_argument("model", choices=list(MODEL_REGISTRY))
    pi.add_argument("--size", default=None)
    _add_common(pi)
    pi.set_defaults(func=cmd_install)

    pim = sub.add_parser("image", help="depth map from a single image")
    pim.add_argument(
        "--model", default="depthanything-v2", choices=list(MODEL_REGISTRY)
    )
    pim.add_argument("--size", default="small")
    pim.add_argument("--in", dest="inp", required=True)
    pim.add_argument("--out", required=True)
    pim.add_argument("--out-format", default="png", choices=["png", "npy", "exr"])
    pim.add_argument(
        "--invert", action="store_true", help="flip so far=bright (Blender)"
    )
    pim.add_argument(
        "--no-preview", action="store_true", help="skip the turbo-colormap preview"
    )
    _add_common(pim)
    pim.set_defaults(func=cmd_image)

    pv = sub.add_parser("video", help="per-frame depth for video")
    pv.add_argument("--model", default="depthanything-v2", choices=list(MODEL_REGISTRY))
    pv.add_argument("--size", default="small")
    pv.add_argument("--in", dest="inp", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument(
        "--out-format", default="mp4", choices=["mp4", "png-seq", "exr-seq"]
    )
    pv.add_argument("--invert", action="store_true")
    pv.add_argument("--smooth", default="none", choices=["none", "temporal"])
    _add_common(pv)
    pv.set_defaults(func=cmd_video)

    ps = sub.add_parser("stereo", help="2D to stereo pair via depth-driven parallax")
    ps.add_argument("--model", default="depthanything-v2", choices=list(MODEL_REGISTRY))
    ps.add_argument("--size", default="small")
    ps.add_argument("--in", dest="inp", required=True)
    ps.add_argument(
        "--depth",
        default=None,
        help="optional pre-computed depth PNG; if omitted, inferred",
    )
    ps.add_argument("--out-left", required=True)
    ps.add_argument("--out-right", required=True)
    ps.add_argument(
        "--baseline", type=float, default=6.5, help="max parallax shift in px"
    )
    _add_common(ps)
    ps.set_defaults(func=cmd_stereo)

    pp = sub.add_parser("parallax", help="2.5D parallax animation from image + depth")
    pp.add_argument("--image", required=True)
    pp.add_argument("--depth", required=True)
    pp.add_argument("--out", required=True)
    pp.add_argument("--frames", type=int, default=120)
    pp.add_argument("--fps", type=float, default=30.0)
    pp.add_argument(
        "--motion",
        default="orbit",
        choices=["orbit", "zoom", "pan-left", "pan-right", "ken-burns"],
    )
    pp.add_argument("--amplitude", type=float, default=30.0, help="max shift in px")
    _add_common(pp)
    pp.set_defaults(func=cmd_parallax)

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
