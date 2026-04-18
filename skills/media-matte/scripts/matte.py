#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-matte driver: AI background removal / matting for images + video.

Non-interactive (no prompts). Prints every command to stderr before running it.

Subcommands:
    check          Report installed backends.
    install        Print install command for a model (no auto-install).
    image          Matte a still image (rembg / birefnet / rmbg2).
    video          Matte a video with RVM (GPL-3.0, invoked as subprocess — CLI boundary).
    refine         Alpha-matting refine with an externally-provided trimap.
    composite      Composite a transparent PNG over a background.

Global flags:
    --dry-run      Print commands only; do not execute.
    --verbose      Extra progress to stderr.

Stdlib only in this file. Python wrappers for BiRefNet / RMBG-2.0 are executed
as small inline scripts via `python -c` so they run under whatever Python the
user's shell resolves — keeping this driver dependency-free.

Models (all commercial-safe except RVM which is GPL-3.0):
    rembg      MIT  (weights: Apache 2.0 for u2net / isnet)
    birefnet   MIT
    rmbg2      Apache 2.0   (Brinet briaai/RMBG-2.0 — NOT v1.4 which is NC)
    rvm        GPL-3.0      (subprocess boundary REQUIRED for closed-source products)

NOT supported (non-commercial or proprietary):
    RMBG v1.4 (CC-BY-NC)
    Adobe Sensei / backgroundremover.app (proprietary SaaS)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def run(
    cmd: list[str], *, dry_run: bool, verbose: bool, cwd: Optional[str] = None
) -> int:
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {pretty}" + (f"   (cwd: {cwd})" if cwd else ""), file=sys.stderr)
    if dry_run:
        return 0
    out = subprocess.run(cmd, check=False, cwd=cwd)
    return out.returncode


def ensure(path: Path, kind: str = "file") -> None:
    if not path.exists():
        die(f"{kind} not found: {path}")


# --------------------------------------------------------------------------- #
# Backend metadata
# --------------------------------------------------------------------------- #


MODELS = {
    "rembg": {
        "binary": "rembg",
        "license": "MIT (code) + Apache-2.0 (u2net/isnet weights)",
        "repo": "https://github.com/danielgatis/rembg",
        "kinds": {"image", "refine"},
    },
    "birefnet": {
        "binary": None,
        "license": "MIT",
        "repo": "https://github.com/ZhengPeng7/BiRefNet",
        "hf": "ZhengPeng7/BiRefNet",
        "kinds": {"image"},
    },
    "rmbg2": {
        "binary": None,
        "license": "Apache-2.0",
        "repo": "https://huggingface.co/briaai/RMBG-2.0",
        "hf": "briaai/RMBG-2.0",
        "kinds": {"image"},
    },
    "rvm": {
        "binary": None,
        "license": "GPL-3.0",
        "repo": "https://github.com/PeterL1n/RobustVideoMatting",
        "kinds": {"video"},
        "note": "GPL-3.0 — invoke only as a subprocess from a closed-source product.",
    },
}


INSTALL_HINTS = {
    "rembg": {
        "darwin": "uv pip install 'rembg[cli]'",
        "linux": "uv pip install 'rembg[cli]'",
        "windows": "uv pip install 'rembg[cli]'",
    },
    "birefnet": {
        "darwin": "uv pip install torch torchvision transformers pillow",
        "linux": "uv pip install torch torchvision transformers pillow",
        "windows": "uv pip install torch torchvision transformers pillow",
    },
    "rmbg2": {
        "darwin": "uv pip install torch torchvision transformers pillow",
        "linux": "uv pip install torch torchvision transformers pillow",
        "windows": "uv pip install torch torchvision transformers pillow",
    },
    "rvm": {
        "darwin": "git clone https://github.com/PeterL1n/RobustVideoMatting && uv pip install torch torchvision av tqdm pims",
        "linux": "git clone https://github.com/PeterL1n/RobustVideoMatting && uv pip install torch torchvision av tqdm pims",
        "windows": "git clone https://github.com/PeterL1n/RobustVideoMatting && uv pip install torch torchvision av tqdm pims",
    },
}


# --------------------------------------------------------------------------- #
# check / install
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    result = {
        "models": {
            k: {
                "license": v["license"],
                "repo": v["repo"],
                "binary": v["binary"],
                "on_path": bool(v["binary"] and which(v["binary"])),
            }
            for k, v in MODELS.items()
        },
        "python": sys.executable,
        "ffmpeg": {"on_path": bool(which("ffmpeg"))},
        "ffprobe": {"on_path": bool(which("ffprobe"))},
    }
    # Try importing python packages non-destructively.
    for pkg in ("transformers", "torch", "rembg"):
        try:
            __import__(pkg)
            result.setdefault("python_imports", {})[pkg] = True
        except Exception:
            result.setdefault("python_imports", {})[pkg] = False
    print(json.dumps(result, indent=2))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    model = args.model
    if model not in INSTALL_HINTS:
        die(f"unknown model: {model}; choose from {sorted(INSTALL_HINTS)}")
    sysname = platform.system().lower()
    key = sysname if sysname in ("darwin", "linux", "windows") else "linux"
    print(f"# Install {model} ({MODELS[model]['license']}) on {sysname or 'unknown'}:")
    print(INSTALL_HINTS[model][key])
    print(f"# Repo: {MODELS[model]['repo']}")
    if MODELS[model].get("note"):
        print(f"# NOTE: {MODELS[model]['note']}")
    return 0


# --------------------------------------------------------------------------- #
# image
# --------------------------------------------------------------------------- #


BIREFNET_INLINE = r"""
import sys, torch, os
from PIL import Image
import torchvision.transforms as T
from transformers import AutoModelForImageSegmentation

hf_id, in_path, out_path, size = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForImageSegmentation.from_pretrained(hf_id, trust_remote_code=True).eval().to(device)

img = Image.open(in_path).convert("RGB")
tx = T.Compose([T.Resize((size, size)), T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with torch.no_grad():
    out = model(tx(img).unsqueeze(0).to(device))
mask = (out[-1] if isinstance(out, (list, tuple)) else out).sigmoid().cpu()[0, 0]
mask_img = T.Resize(img.size[::-1])(mask.unsqueeze(0))[0].numpy()
import numpy as np
alpha = (mask_img * 255).clip(0, 255).astype("uint8")
rgba = Image.merge("RGBA", (*img.split(), Image.fromarray(alpha, mode="L")))
rgba.save(out_path)
print(f"wrote {out_path}", file=sys.stderr)
"""


def cmd_image(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input image")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.model == "rembg":
        binary = which("rembg") or die(
            "rembg not on PATH — run: matte.py install rembg"
        )
        cmd = [binary, "i"]
        if args.model_name:
            cmd += ["-m", args.model_name]
        if args.alpha_matting:
            cmd += ["-a"]
        cmd += [str(inp), str(out)]
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    if args.model in ("birefnet", "rmbg2"):
        hf_id = MODELS[args.model]["hf"]
        size = args.resize if args.resize else 1024
        cmd = [
            sys.executable,
            "-c",
            BIREFNET_INLINE,
            hf_id,
            str(inp),
            str(out),
            str(size),
        ]
        return run(cmd, dry_run=args.dry_run, verbose=args.verbose)

    die(f"image mode does not support --model {args.model}")


# --------------------------------------------------------------------------- #
# video (RVM subprocess — GPL-3.0 boundary)
# --------------------------------------------------------------------------- #


def cmd_video(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    out = Path(args.out)
    ensure(inp, "input video")
    if args.model != "rvm":
        die("video mode supports --model rvm only (RVM is the temporal video matter).")
    if not which("ffmpeg"):
        die("ffmpeg not on PATH")

    rvm_dir = Path(args.rvm_dir).expanduser().resolve() if args.rvm_dir else None
    if rvm_dir is None or not (rvm_dir / "inference.py").exists():
        die(
            "pass --rvm-dir <path/to/RobustVideoMatting> — clone: "
            "git clone https://github.com/PeterL1n/RobustVideoMatting"
        )

    checkpoint = (
        Path(args.checkpoint).expanduser().resolve() if args.checkpoint else None
    )
    if checkpoint is None or not checkpoint.exists():
        die(
            "pass --checkpoint <path>.pth  (download rvm_mobilenetv3.pth or rvm_resnet50.pth from RVM releases)"
        )

    out.parent.mkdir(parents=True, exist_ok=True)

    device = args.device
    cmd = [
        sys.executable,
        "inference.py",
        "--variant",
        args.variant,
        "--checkpoint",
        str(checkpoint),
        "--device",
        device,
        "--input-source",
        str(inp.resolve()),
        "--output-type",
        "video",
        "--output-composition",
        str(out.resolve()),
    ]
    if args.alpha:
        cmd += ["--output-alpha", str(Path(args.alpha).resolve())]
    if args.foreground:
        cmd += ["--output-foreground", str(Path(args.foreground).resolve())]
    if args.bg:
        # RVM's --output-composition alone composites onto a solid green unless you supply --bg-source.
        # RVM supports --bg-source for a background image or video.
        cmd += ["--bg-source", str(Path(args.bg).resolve())]
    if args.output_mbps is not None:
        cmd += ["--output-video-mbps", str(args.output_mbps)]

    # Run inside the RVM checkout as cwd — `inference.py` uses relative imports.
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose, cwd=str(rvm_dir))


# --------------------------------------------------------------------------- #
# refine (trimap alpha-matting)
# --------------------------------------------------------------------------- #


REFINE_INLINE = r"""
import sys
from PIL import Image
import numpy as np
try:
    from pymatting import estimate_alpha_cf, load_image, save_image
except Exception as e:
    print(f"pymatting not installed: {e}", file=sys.stderr); sys.exit(2)

img_path, trimap_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
image = load_image(img_path, "RGB")
trimap = load_image(trimap_path, "GRAY")
alpha = estimate_alpha_cf(image, trimap)
# Build RGBA
rgba = np.dstack([image, alpha])
Image.fromarray((rgba * 255).astype("uint8"), mode="RGBA").save(out_path)
print(f"wrote {out_path}", file=sys.stderr)
"""


def cmd_refine(args: argparse.Namespace) -> int:
    inp = Path(args.inp)
    mask = Path(args.mask)
    out = Path(args.out)
    ensure(inp, "input image")
    ensure(mask, "trimap")
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-c", REFINE_INLINE, str(inp), str(mask), str(out)]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# --------------------------------------------------------------------------- #
# composite
# --------------------------------------------------------------------------- #


COMPOSITE_INLINE = r"""
import sys
from PIL import Image
fg_path, bg_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
fg = Image.open(fg_path).convert("RGBA")
bg = Image.open(bg_path).convert("RGB").resize(fg.size, Image.LANCZOS)
out = Image.new("RGB", fg.size)
out.paste(bg, (0, 0))
out.paste(fg, (0, 0), fg.split()[-1])
out.save(out_path)
print(f"wrote {out_path}", file=sys.stderr)
"""


def cmd_composite(args: argparse.Namespace) -> int:
    fg = Path(args.fg)
    bg = Path(args.bg)
    out = Path(args.out)
    ensure(fg, "foreground RGBA")
    ensure(bg, "background")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-c", COMPOSITE_INLINE, str(fg), str(bg), str(out)]
    return run(cmd, dry_run=args.dry_run, verbose=args.verbose)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="matte.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )
    p.add_argument("--verbose", action="store_true", help="Extra progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    # check / install
    pc = sub.add_parser("check", help="Report installed backends")
    pc.set_defaults(func=cmd_check)

    pi = sub.add_parser(
        "install", help="Print install command for a model (no auto-install)"
    )
    pi.add_argument("model", choices=list(INSTALL_HINTS.keys()))
    pi.set_defaults(func=cmd_install)

    # image
    pim = sub.add_parser("image", help="Matte a still image")
    pim.add_argument("--model", required=True, choices=["rembg", "birefnet", "rmbg2"])
    pim.add_argument("--in", dest="inp", required=True)
    pim.add_argument("--out", required=True)
    pim.add_argument(
        "--model-name",
        default=None,
        help="rembg -m (e.g. u2net, isnet-general-use, isnet-anime, sam)",
    )
    pim.add_argument(
        "--alpha-matting", action="store_true", help="rembg -a (pymatting refine, slow)"
    )
    pim.add_argument(
        "--resize",
        type=int,
        default=None,
        help="BiRefNet / RMBG-2.0 inference resize (default 1024)",
    )
    pim.set_defaults(func=cmd_image)

    # video (RVM, GPL-3.0 subprocess)
    pv = sub.add_parser("video", help="Matte a video with RVM (subprocess)")
    pv.add_argument("--model", default="rvm", choices=["rvm"])
    pv.add_argument("--in", dest="inp", required=True)
    pv.add_argument("--out", required=True, help="--output-composition target")
    pv.add_argument("--alpha", default=None, help="Also write alpha mask video here")
    pv.add_argument(
        "--foreground", default=None, help="Also write foreground video here"
    )
    pv.add_argument(
        "--bg",
        default=None,
        help="Background image or video for the composite (RVM --bg-source)",
    )
    pv.add_argument(
        "--variant", default="mobilenetv3", choices=["mobilenetv3", "resnet50"]
    )
    pv.add_argument(
        "--rvm-dir", default=None, help="Path to your RobustVideoMatting checkout"
    )
    pv.add_argument(
        "--checkpoint",
        default=None,
        help="Path to rvm_mobilenetv3.pth or rvm_resnet50.pth",
    )
    pv.add_argument("--device", default="cuda")
    pv.add_argument("--output-mbps", type=float, default=None)
    pv.set_defaults(func=cmd_video)

    # refine
    pr = sub.add_parser("refine", help="Alpha-matting refine with a trimap")
    pr.add_argument("--in", dest="inp", required=True)
    pr.add_argument(
        "--mask", required=True, help="trimap.png (0=bg, 255=fg, 128=unknown)"
    )
    pr.add_argument("--out", required=True)
    pr.set_defaults(func=cmd_refine)

    # composite
    pco = sub.add_parser("composite", help="Composite RGBA foreground over background")
    pco.add_argument("--fg", required=True, help="RGBA PNG")
    pco.add_argument("--bg", required=True, help="RGB background (PNG/JPG)")
    pco.add_argument("--out", required=True)
    pco.set_defaults(func=cmd_composite)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
