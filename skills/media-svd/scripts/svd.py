#!/usr/bin/env python3
# /// script
# dependencies = [
#   "diffusers",
#   "torch",
#   "transformers",
#   "accelerate",
#   "imageio",
#   "imageio-ffmpeg",
# ]
# ///
"""
media-svd driver: open-source, commercial-safe AI video generation via diffusers
and ComfyUI. STRICT license policy: only Apache 2.0 / MIT / BSD weights.

Subcommands:
    check           Report diffusers/torch availability and GPU status.
    t2v             Text-to-video.
    i2v             Image-to-video (seed from an existing first frame).
    animate         POST a ComfyUI API-format AnimateDiff workflow.
    install         Print the pip install line for a model's deps.
    download        Fetch model weights from HuggingFace (requires --yes).

Global flags:
    --dry-run       Print commands / plan; do not execute.
    --verbose       Stream progress and command lines.

Stdlib-only dispatch. Non-interactive. Weights require --yes to download.

Supported models (all Apache 2.0):
    ltx             LTX-Video (Lightricks)       t2v + i2v
    cogvideox-2b    CogVideoX-2B (Tsinghua)      t2v
    cogvideox-5b    CogVideoX-5B (Tsinghua)      t2v + i2v
    cogvideox       alias -> cogvideox-5b
    mochi           Mochi-1 (Genmo)              t2v (heavy VRAM)
    wan             Wan-Video 2.1 (Alibaba)      t2v + i2v
    animatediff     ComfyUI-only motion module; use `animate` subcommand

Examples:
    uv run scripts/svd.py check
    uv run scripts/svd.py t2v --model ltx --prompt "..." \\
        --duration 5 --fps 24 --out out.mp4
    uv run scripts/svd.py i2v --model cogvideox --init-image in.png \\
        --prompt "..." --duration 6 --out out.mp4
    uv run scripts/svd.py animate --workflow animatediff.json --out anim.mp4
    uv run scripts/svd.py install ltx
    uv run scripts/svd.py download --model ltx --yes
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# Model registry
# --------------------------------------------------------------------------- #

MODELS = {
    "ltx": {
        "repo": "Lightricks/LTX-Video",
        "license": "Apache 2.0",
        "pipeline_t2v": "LTXPipeline",
        "pipeline_i2v": "LTXImageToVideoPipeline",
        "vram_gb": 24,
        "default_fps": 24,
        "default_duration": 5.0,
        "default_size": (768, 512),
        "size_multiple": 32,
        "notes": "Fastest Apache model; near-realtime on H100.",
    },
    "cogvideox-2b": {
        "repo": "THUDM/CogVideoX-2b",
        "license": "Apache 2.0",
        "pipeline_t2v": "CogVideoXPipeline",
        "pipeline_i2v": None,
        "vram_gb": 12,
        "default_fps": 8,
        "default_duration": 6.0,
        "default_size": (720, 480),
        "size_multiple": None,
        "notes": "Smaller CogVideoX; fits 12 GB.",
    },
    "cogvideox-5b": {
        "repo": "THUDM/CogVideoX-5b",
        "license": "Apache 2.0",
        "pipeline_t2v": "CogVideoXPipeline",
        "pipeline_i2v": "CogVideoXImageToVideoPipeline",
        "vram_gb": 24,
        "default_fps": 8,
        "default_duration": 6.0,
        "default_size": (720, 480),
        "size_multiple": None,
        "notes": "Higher-quality CogVideoX.",
    },
    "mochi": {
        "repo": "genmo/mochi-1-preview",
        "license": "Apache 2.0",
        "pipeline_t2v": "MochiPipeline",
        "pipeline_i2v": None,
        "vram_gb": 60,
        "default_fps": 30,
        "default_duration": 5.4,
        "default_size": (848, 480),
        "size_multiple": None,
        "notes": "SOTA quality; effectively multi-GPU.",
    },
    "wan": {
        "repo": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        "license": "Apache 2.0",
        "pipeline_t2v": "WanPipeline",
        "pipeline_i2v": "WanImageToVideoPipeline",
        "vram_gb": 24,
        "default_fps": 16,
        "default_duration": 5.0,
        "default_size": (832, 480),
        "size_multiple": 16,
        "notes": "Alibaba Wan 2.1.",
    },
}

ALIASES = {"cogvideox": "cogvideox-5b"}


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[svd] {msg}", file=sys.stderr)


def _die(msg: str, code: int = 2) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return code


def _which(name: str) -> str | None:
    return shutil.which(name)


def _quote(s: str) -> str:
    if not s or any(c in s for c in " \t\"'"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _echo_cmd(cmd: list[str]) -> None:
    print("$ " + " ".join(_quote(a) for a in cmd), file=sys.stderr)


def _module_available(mod: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(mod) is not None


def _detect_gpu() -> dict:
    info = {"cuda": False, "mps": False, "device": "cpu", "details": ""}
    if _which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            ).strip()
            if out:
                info["cuda"] = True
                info["device"] = "cuda"
                info["details"] = out
        except Exception:
            pass
    if sys.platform == "darwin":
        try:
            arch = subprocess.check_output(
                ["uname", "-m"], text=True, timeout=2
            ).strip()
            if arch in ("arm64", "aarch64"):
                info["mps"] = True
                if info["device"] == "cpu":
                    info["device"] = "mps"
        except Exception:
            pass
    return info


def _resolve_model(name: str) -> tuple[str, dict]:
    canon = ALIASES.get(name, name)
    if canon not in MODELS:
        _die(
            f"unknown model '{name}'. Valid: {', '.join(sorted(MODELS.keys()))} "
            f"(or alias: {', '.join(sorted(ALIASES.keys()))})",
            3,
        )
        raise SystemExit(3)
    return canon, MODELS[canon]


def _round_to(x: int, m: int | None) -> int:
    if not m:
        return x
    return (x // m) * m


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    info = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "diffusers": _module_available("diffusers"),
        "torch": _module_available("torch"),
        "transformers": _module_available("transformers"),
        "accelerate": _module_available("accelerate"),
        "imageio": _module_available("imageio"),
        "imageio_ffmpeg": _module_available("imageio_ffmpeg"),
        "gpu": _detect_gpu(),
        "models_supported": list(MODELS.keys()),
    }
    print(json.dumps(info, indent=2))
    return 0 if info["diffusers"] and info["torch"] else 1


# --------------------------------------------------------------------------- #
# install
# --------------------------------------------------------------------------- #


def cmd_install(args: argparse.Namespace) -> int:
    _canon, model = _resolve_model(args.model)
    lines = [
        f"# {args.model} ({model['license']})",
        f"# repo: {model['repo']}",
        "pip install --upgrade diffusers transformers accelerate torch imageio imageio-ffmpeg",
    ]
    for line in lines:
        print(line)
    return 0


# --------------------------------------------------------------------------- #
# download
# --------------------------------------------------------------------------- #


def cmd_download(args: argparse.Namespace) -> int:
    if not args.yes:
        return _die(
            "download refuses without --yes (video weights are 5-60 GB). "
            f"Re-run with --yes to pull '{args.model}' from HuggingFace.",
            4,
        )
    _canon, model = _resolve_model(args.model)
    py_expr = (
        "from huggingface_hub import snapshot_download; "
        f"snapshot_download(repo_id={model['repo']!r}"
    )
    if args.dest:
        py_expr += f", local_dir={args.dest!r}, local_dir_use_symlinks=False"
    py_expr += ")"

    cmd = [sys.executable, "-c", py_expr]
    if args.dry_run or args.verbose:
        _echo_cmd(cmd)
    if args.dry_run:
        return 0
    if not _module_available("huggingface_hub"):
        return _die("huggingface_hub not installed. `pip install huggingface_hub`.", 5)
    return subprocess.run(cmd).returncode


# --------------------------------------------------------------------------- #
# t2v / i2v helpers
# --------------------------------------------------------------------------- #


def _compute_num_frames(duration: float, fps: int) -> int:
    return max(1, int(round(duration * fps)))


def _save_video(frames, out_path: Path, fps: int) -> None:
    """Write a list of PIL.Image frames to out_path using imageio_ffmpeg."""
    import imageio  # type: ignore
    import numpy as np  # type: ignore

    writer = imageio.get_writer(
        str(out_path),
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=1,
    )
    try:
        for frame in frames:
            writer.append_data(np.asarray(frame.convert("RGB")))
    finally:
        writer.close()


def _load_t2v_pipeline(model_key: str, dtype_name: str, device: str, cpu_offload: bool):
    canon, model = _resolve_model(model_key)
    import torch  # type: ignore
    import diffusers  # type: ignore

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    torch_dtype = dtype_map.get(dtype_name, torch.bfloat16)
    cls_name = model["pipeline_t2v"]
    pipeline_cls = getattr(diffusers, cls_name, None)
    if pipeline_cls is None:
        raise SystemExit(
            f"diffusers version is missing {cls_name}; `pip install --upgrade diffusers` "
            f"to get the latest video pipelines."
        )
    pipe = pipeline_cls.from_pretrained(model["repo"], torch_dtype=torch_dtype)
    if cpu_offload:
        pipe.enable_sequential_cpu_offload()
    else:
        pipe = pipe.to(device)
    return pipe, model


def _load_i2v_pipeline(model_key: str, dtype_name: str, device: str, cpu_offload: bool):
    canon, model = _resolve_model(model_key)
    if not model.get("pipeline_i2v"):
        raise SystemExit(f"{canon} does not support image-to-video.")
    import torch  # type: ignore
    import diffusers  # type: ignore

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    torch_dtype = dtype_map.get(dtype_name, torch.bfloat16)
    pipeline_cls = getattr(diffusers, model["pipeline_i2v"], None)
    if pipeline_cls is None:
        raise SystemExit(
            f"diffusers version is missing {model['pipeline_i2v']}; upgrade diffusers."
        )
    pipe = pipeline_cls.from_pretrained(model["repo"], torch_dtype=torch_dtype)
    if cpu_offload:
        pipe.enable_sequential_cpu_offload()
    else:
        pipe = pipe.to(device)
    return pipe, model


# --------------------------------------------------------------------------- #
# t2v
# --------------------------------------------------------------------------- #


def cmd_t2v(args: argparse.Namespace) -> int:
    canon, model = _resolve_model(args.model)
    fps = args.fps or model["default_fps"]
    duration = args.duration if args.duration is not None else model["default_duration"]
    default_w, default_h = model["default_size"]
    width = args.width or default_w
    height = args.height or default_h
    mult = model.get("size_multiple")
    width = _round_to(width, mult)
    height = _round_to(height, mult)
    num_frames = _compute_num_frames(float(duration), int(fps))
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plan = {
        "mode": "t2v",
        "model": canon,
        "repo": model["repo"],
        "license": model["license"],
        "prompt": args.prompt,
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "num_frames": num_frames,
        "seed": args.seed,
        "output": str(out_path),
        "dtype": args.dtype,
        "device": args.device or _detect_gpu()["device"],
        "cpu_offload": args.cpu_offload,
    }
    if args.dry_run or args.verbose:
        print("$ diffusers.t2v " + json.dumps(plan), file=sys.stderr)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "plan": plan}, indent=2))
        return 0

    if not (_module_available("diffusers") and _module_available("torch")):
        return _die("diffusers + torch not installed. See `svd.py install <model>`.", 5)

    import torch  # type: ignore

    device = args.device or _detect_gpu()["device"]
    _log(f"loading {model['repo']} on {device}", True)
    pipe, _m = _load_t2v_pipeline(canon, args.dtype, device, args.cpu_offload)

    gen = (
        torch.Generator(device=device).manual_seed(int(args.seed))
        if args.seed is not None
        else None
    )
    kwargs = dict(
        prompt=args.prompt,
        width=int(width),
        height=int(height),
        num_frames=int(num_frames),
        num_inference_steps=int(args.steps),
    )
    if args.guidance is not None:
        kwargs["guidance_scale"] = float(args.guidance)
    if gen is not None:
        kwargs["generator"] = gen
    if args.negative_prompt:
        kwargs["negative_prompt"] = args.negative_prompt

    _log(f"generating -> {out_path} ({num_frames} frames)", True)
    result = pipe(**kwargs)
    frames = result.frames[0] if hasattr(result, "frames") else result.videos[0]
    _save_video(frames, out_path, fps)
    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# i2v
# --------------------------------------------------------------------------- #


def cmd_i2v(args: argparse.Namespace) -> int:
    canon, model = _resolve_model(args.model)
    if not model.get("pipeline_i2v"):
        return _die(
            f"{canon} does not support image-to-video. "
            f"Try --model cogvideox-5b, ltx, or wan.",
            6,
        )
    init_path = Path(args.init_image).expanduser().resolve()
    if not init_path.exists():
        return _die(f"init image not found: {init_path}", 2)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fps = args.fps or model["default_fps"]
    duration = args.duration if args.duration is not None else model["default_duration"]
    num_frames = _compute_num_frames(float(duration), int(fps))

    plan = {
        "mode": "i2v",
        "model": canon,
        "repo": model["repo"],
        "init_image": str(init_path),
        "prompt": args.prompt,
        "fps": fps,
        "duration": duration,
        "num_frames": num_frames,
        "output": str(out_path),
        "device": args.device or _detect_gpu()["device"],
    }
    if args.dry_run or args.verbose:
        print("$ diffusers.i2v " + json.dumps(plan), file=sys.stderr)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "plan": plan}, indent=2))
        return 0

    if not (_module_available("diffusers") and _module_available("torch")):
        return _die("diffusers + torch not installed.", 5)

    import torch  # type: ignore
    from PIL import Image  # type: ignore

    device = args.device or _detect_gpu()["device"]
    pipe, _m = _load_i2v_pipeline(canon, args.dtype, device, args.cpu_offload)

    img = Image.open(init_path).convert("RGB")
    gen = (
        torch.Generator(device=device).manual_seed(int(args.seed))
        if args.seed is not None
        else None
    )
    kwargs = dict(
        prompt=args.prompt,
        image=img,
        num_frames=int(num_frames),
        num_inference_steps=int(args.steps),
    )
    if args.guidance is not None:
        kwargs["guidance_scale"] = float(args.guidance)
    if gen is not None:
        kwargs["generator"] = gen
    if args.negative_prompt:
        kwargs["negative_prompt"] = args.negative_prompt

    result = pipe(**kwargs)
    frames = result.frames[0] if hasattr(result, "frames") else result.videos[0]
    _save_video(frames, out_path, fps)
    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# animate (ComfyUI API-format workflow for AnimateDiff)
# --------------------------------------------------------------------------- #


def _http_post_json(url: str, body: dict, timeout: int) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_bytes(url: str, timeout: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def cmd_animate(args: argparse.Namespace) -> int:
    workflow_path = Path(args.workflow).expanduser().resolve()
    if not workflow_path.exists():
        return _die(f"workflow not found: {workflow_path}", 2)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with workflow_path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    if (
        isinstance(workflow, dict)
        and "nodes" in workflow
        and isinstance(workflow["nodes"], list)
    ):
        return _die(
            "workflow is UI-format (has top-level 'nodes' list). Re-export "
            "from ComfyUI with 'Save (API Format)' (enable Dev mode first).",
            7,
        )

    server = args.server.rstrip("/")
    client_id = f"media-svd-{int(time.time())}"
    body = {"prompt": workflow, "client_id": client_id}

    if args.dry_run or args.verbose:
        print(
            f"$ POST {server}/prompt  (workflow={workflow_path.name})", file=sys.stderr
        )
    if args.dry_run:
        return 0

    try:
        submit = _http_post_json(f"{server}/prompt", body, args.timeout)
    except Exception as e:
        return _die(f"failed POST to ComfyUI: {e}", 8)
    prompt_id = submit.get("prompt_id")
    if not prompt_id:
        return _die(f"no prompt_id in response: {submit}", 8)

    _log(f"prompt_id={prompt_id}; polling /history...", True)
    deadline = time.time() + args.timeout
    history_url = f"{server}/history/{prompt_id}"
    media_meta: list[dict] = []
    while time.time() < deadline:
        try:
            hist = _http_get_json(history_url, 10)
        except Exception:
            time.sleep(1.0)
            continue
        entry = hist.get(prompt_id)
        if entry and entry.get("outputs"):
            for _node_id, node_out in entry["outputs"].items():
                # VHS_VideoCombine emits 'gifs' or 'videos'; basic VAE Decode -> SaveImage emits 'images'
                for key in ("videos", "gifs", "images"):
                    for m in node_out.get(key, []) or []:
                        media_meta.append({**m, "_key": key})
            if media_meta:
                break
        time.sleep(1.0)

    if not media_meta:
        return _die(f"timeout waiting for workflow result (prompt_id={prompt_id})", 9)

    first = media_meta[0]
    q = urllib.parse.urlencode(
        {
            "filename": first.get("filename", ""),
            "subfolder": first.get("subfolder", ""),
            "type": first.get("type", "output"),
        }
    )
    view_url = f"{server}/view?{q}"
    data = _http_get_bytes(view_url, args.timeout)
    with out_path.open("wb") as f:
        f.write(data)
    print(
        json.dumps(
            {
                "status": "ok",
                "prompt_id": prompt_id,
                "output": str(out_path),
                "media_count": len(media_meta),
                "first_media_type": first.get("_key"),
            },
            indent=2,
        )
    )
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def _add_global(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="svd.py",
        description="Open-source AI video generation (OSI-open / commercial-safe only).",
    )
    _add_global(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="report env + GPU")
    _add_global(c)
    c.set_defaults(func=cmd_check)

    c = sub.add_parser("install", help="print pip install line")
    _add_global(c)
    c.add_argument("model", choices=list(MODELS.keys()) + list(ALIASES.keys()))
    c.set_defaults(func=cmd_install)

    c = sub.add_parser("download", help="pull weights from HF")
    _add_global(c)
    c.add_argument(
        "--model", required=True, choices=list(MODELS.keys()) + list(ALIASES.keys())
    )
    c.add_argument("--dest", default=None)
    c.add_argument("--yes", action="store_true")
    c.set_defaults(func=cmd_download)

    c = sub.add_parser("t2v", help="text-to-video")
    _add_global(c)
    c.add_argument(
        "--model", default="ltx", choices=list(MODELS.keys()) + list(ALIASES.keys())
    )
    c.add_argument("--prompt", required=True)
    c.add_argument("--negative-prompt", default=None)
    c.add_argument("--out", required=True)
    c.add_argument("--duration", type=float, default=None, help="seconds")
    c.add_argument("--fps", type=int, default=None)
    c.add_argument("--width", type=int, default=None)
    c.add_argument("--height", type=int, default=None)
    c.add_argument("--steps", type=int, default=50)
    c.add_argument("--guidance", type=float, default=None)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument(
        "--dtype", choices=["float32", "float16", "bfloat16"], default="bfloat16"
    )
    c.add_argument("--device", default=None)
    c.add_argument("--cpu-offload", action="store_true")
    c.set_defaults(func=cmd_t2v)

    c = sub.add_parser("i2v", help="image-to-video")
    _add_global(c)
    c.add_argument(
        "--model",
        default="cogvideox-5b",
        choices=list(MODELS.keys()) + list(ALIASES.keys()),
    )
    c.add_argument("--init-image", required=True)
    c.add_argument("--prompt", required=True)
    c.add_argument("--negative-prompt", default=None)
    c.add_argument("--out", required=True)
    c.add_argument("--duration", type=float, default=None)
    c.add_argument("--fps", type=int, default=None)
    c.add_argument("--steps", type=int, default=50)
    c.add_argument("--guidance", type=float, default=None)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument(
        "--dtype", choices=["float32", "float16", "bfloat16"], default="bfloat16"
    )
    c.add_argument("--device", default=None)
    c.add_argument("--cpu-offload", action="store_true")
    c.set_defaults(func=cmd_i2v)

    c = sub.add_parser("animate", help="run a ComfyUI AnimateDiff workflow")
    _add_global(c)
    c.add_argument("--workflow", required=True, help="API-format JSON")
    c.add_argument("--out", required=True)
    c.add_argument("--server", default="http://127.0.0.1:8188")
    c.add_argument("--timeout", type=int, default=600)
    c.set_defaults(func=cmd_animate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
