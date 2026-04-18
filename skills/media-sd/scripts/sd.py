#!/usr/bin/env python3
# /// script
# dependencies = [
#   "diffusers",
#   "torch",
#   "transformers",
#   "accelerate",
# ]
# ///
"""
media-sd driver: open-source, commercial-safe AI image generation via diffusers +
ComfyUI. STRICT license policy: only Apache 2.0 / MIT / BSD / OSI-open weights.

Subcommands:
    check              Report diffusers/torch/ComfyUI availability and GPU status.
    generate           Text-to-image with a named permissive model.
    img2img            Image-to-image edit from an initial image + prompt.
    comfy-workflow     POST a ComfyUI API-format workflow JSON and fetch PNG.
    comfy-install      Print exact ComfyUI install commands (does not run them).
    download           Fetch model weights from HuggingFace (requires --yes).
    install            Print the pip install line for a model's diffusers deps.

Global flags:
    --dry-run          Print commands / plan; do not execute.
    --verbose          Stream tool stdout/stderr and progress info.

Stdlib only for dispatch. Diffusers is imported lazily inside `generate` /
`img2img`. Non-interactive: no prompts. Weight downloads always require --yes.

Supported models (all OSI-open / commercial-safe except HunyuanDiT which has a
>100M MAU cap — flagged at runtime):
    flux-schnell   FLUX.1 [schnell]     Apache 2.0   (default)
    kolors         Kolors               Apache 2.0
    sana           Sana 1.6B            Apache 2.0
    lumina         Lumina-Next          Apache 2.0
    hunyuan-dit    HunyuanDiT           Tencent L.2.0 (commercial cap)
    pixart-sigma   PixArt-Sigma         per-checkpoint (check LICENSES.md)

Examples:
    uv run scripts/sd.py check
    uv run scripts/sd.py generate --model flux-schnell \\
        --prompt "a capybara in a wizard hat" --out out.png --steps 4
    uv run scripts/sd.py img2img --model flux-schnell --init-image in.png \\
        --prompt "oil painting" --strength 0.6 --out out.png
    uv run scripts/sd.py comfy-install
    uv run scripts/sd.py comfy-workflow --workflow flow.json --out out.png
    uv run scripts/sd.py download --model flux-schnell --yes
    uv run scripts/sd.py install flux-schnell
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
# Model registry (OSI-open / commercial-safe only)
# --------------------------------------------------------------------------- #

MODELS = {
    "flux-schnell": {
        "repo": "black-forest-labs/FLUX.1-schnell",
        "license": "Apache 2.0",
        "pipeline": "FluxPipeline",
        "vram_gb": 24,
        "default_steps": 4,
        "default_guidance": 0.0,
        "default_size": (1024, 1024),
        "notes": "Distilled 4-step model; do NOT raise guidance above 0.",
    },
    "kolors": {
        "repo": "Kwai-Kolors/Kolors-diffusers",
        "license": "Apache 2.0",
        "pipeline": "KolorsPipeline",
        "vram_gb": 16,
        "default_steps": 25,
        "default_guidance": 5.0,
        "default_size": (1024, 1024),
        "notes": "Photoreal; strong Chinese + English prompts.",
    },
    "sana": {
        "repo": "Efficient-Large-Model/Sana_1600M_1024px_diffusers",
        "license": "Apache 2.0",
        "pipeline": "SanaPipeline",
        "vram_gb": 12,
        "default_steps": 20,
        "default_guidance": 4.5,
        "default_size": (1024, 1024),
        "notes": "NVIDIA DiT; best pick for Apple Silicon and <= 12GB cards.",
    },
    "lumina": {
        "repo": "Alpha-VLLM/Lumina-Next-SFT-diffusers",
        "license": "Apache 2.0",
        "pipeline": "LuminaText2ImgPipeline",
        "vram_gb": 24,
        "default_steps": 30,
        "default_guidance": 4.0,
        "default_size": (1024, 1024),
        "notes": "Strong prompt adherence, high resolution.",
    },
    "hunyuan-dit": {
        "repo": "Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers",
        "license": "Tencent License 2.0 (commercial cap ~100M MAU)",
        "pipeline": "HunyuanDiTPipeline",
        "vram_gb": 16,
        "default_steps": 25,
        "default_guidance": 5.0,
        "default_size": (1024, 1024),
        "notes": "Bilingual EN/CN. Cap on monthly active users for commercial use.",
    },
    "pixart-sigma": {
        "repo": "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS",
        "license": "Per-checkpoint (see references/LICENSES.md)",
        "pipeline": "PixArtSigmaPipeline",
        "vram_gb": 12,
        "default_steps": 20,
        "default_guidance": 4.5,
        "default_size": (1024, 1024),
        "notes": "Efficient DiT; verify checkpoint license before commercial use.",
    },
}

# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[sd] {msg}", file=sys.stderr)


def _die(msg: str, code: int = 2) -> "int":
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


def _run(cmd: list[str], dry_run: bool, verbose: bool) -> int:
    if dry_run or verbose:
        _echo_cmd(cmd)
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


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


def _resolve_model(name: str) -> dict:
    if name not in MODELS:
        _die(
            f"unknown model '{name}'. Valid: {', '.join(MODELS.keys())}",
            3,
        )
        raise SystemExit(3)
    return MODELS[name]


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
        "gpu": _detect_gpu(),
        "models_supported": list(MODELS.keys()),
    }
    print(json.dumps(info, indent=2))
    return 0 if info["diffusers"] and info["torch"] else 1


# --------------------------------------------------------------------------- #
# install (print pip line)
# --------------------------------------------------------------------------- #


def cmd_install(args: argparse.Namespace) -> int:
    model = _resolve_model(args.model)
    lines = [
        f"# {args.model} ({model['license']})",
        f"# repo: {model['repo']}",
        "pip install --upgrade diffusers transformers accelerate torch",
    ]
    for line in lines:
        print(line)
    return 0


# --------------------------------------------------------------------------- #
# download (HF snapshot — confirmation required)
# --------------------------------------------------------------------------- #


def cmd_download(args: argparse.Namespace) -> int:
    if not args.yes:
        return _die(
            "download refuses to run without --yes (weights are large, 5-24 GB). "
            f"Re-run with --yes to confirm pulling '{args.model}' from HuggingFace.",
            4,
        )
    model = _resolve_model(args.model)
    cmd = [
        sys.executable,
        "-c",
        (
            "from huggingface_hub import snapshot_download; "
            f"snapshot_download(repo_id={model['repo']!r}, "
            f"local_dir={args.dest!r} if {args.dest!r} != 'None' else None, "
            "local_dir_use_symlinks=False)"
        ),
    ]
    # Clean None sentinel
    if args.dest is None:
        cmd[2] = (
            "from huggingface_hub import snapshot_download; "
            f"snapshot_download(repo_id={model['repo']!r})"
        )
    if args.dry_run or args.verbose:
        _echo_cmd(cmd)
    if args.dry_run:
        return 0
    if not _module_available("huggingface_hub"):
        return _die("huggingface_hub not installed. `pip install huggingface_hub`.", 5)
    return subprocess.run(cmd).returncode


# --------------------------------------------------------------------------- #
# generate (diffusers text-to-image)
# --------------------------------------------------------------------------- #


def _load_pipeline(model_key: str, dtype_name: str, device: str, cpu_offload: bool):
    """Lazy import diffusers and build the right pipeline class."""
    model = _resolve_model(model_key)
    import torch  # type: ignore
    import diffusers  # type: ignore

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    torch_dtype = dtype_map.get(dtype_name, torch.bfloat16)

    pipeline_cls = getattr(diffusers, model["pipeline"], None)
    if pipeline_cls is None:
        # Fall back to AutoPipeline if specific class not present in this diffusers version
        pipeline_cls = diffusers.AutoPipelineForText2Image

    pipe = pipeline_cls.from_pretrained(model["repo"], torch_dtype=torch_dtype)
    if cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    return pipe, model


def cmd_generate(args: argparse.Namespace) -> int:
    model_key = args.model
    model = _resolve_model(model_key)
    width, height = (
        args.width or model["default_size"][0],
        args.height or model["default_size"][1],
    )
    steps = args.steps if args.steps is not None else model["default_steps"]
    guidance = args.guidance if args.guidance is not None else model["default_guidance"]
    seed = args.seed
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plan = {
        "model": model_key,
        "repo": model["repo"],
        "license": model["license"],
        "prompt": args.prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance,
        "seed": seed,
        "output": str(out_path),
        "dtype": args.dtype,
        "device": args.device or _detect_gpu()["device"],
    }
    if args.dry_run or args.verbose:
        print("$ diffusers.generate " + json.dumps(plan), file=sys.stderr)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "plan": plan}, indent=2))
        return 0

    if not (_module_available("diffusers") and _module_available("torch")):
        return _die(
            "diffusers + torch not installed. Run `sd.py install "
            f"{model_key}` for the pip line, or `pip install diffusers torch "
            "transformers accelerate`.",
            5,
        )

    import torch  # type: ignore

    device = args.device or _detect_gpu()["device"]
    _log(f"loading {model['repo']} on {device} (dtype={args.dtype})", True)
    pipe, _m = _load_pipeline(model_key, args.dtype, device, args.cpu_offload)

    generator = None
    if seed is not None:
        generator = torch.Generator(device=device).manual_seed(int(seed))

    kwargs = {
        "prompt": args.prompt,
        "width": width,
        "height": height,
        "num_inference_steps": int(steps),
        "guidance_scale": float(guidance),
    }
    if generator is not None:
        kwargs["generator"] = generator
    if args.negative_prompt:
        kwargs["negative_prompt"] = args.negative_prompt

    _log(f"generating -> {out_path}", True)
    result = pipe(**kwargs)
    image = result.images[0]
    image.save(out_path)
    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# img2img
# --------------------------------------------------------------------------- #


def cmd_img2img(args: argparse.Namespace) -> int:
    model_key = args.model
    model = _resolve_model(model_key)
    init_path = Path(args.init_image).expanduser().resolve()
    if not init_path.exists():
        return _die(f"init image not found: {init_path}", 2)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    steps = args.steps if args.steps is not None else model["default_steps"]
    guidance = args.guidance if args.guidance is not None else model["default_guidance"]

    plan = {
        "mode": "img2img",
        "model": model_key,
        "repo": model["repo"],
        "init_image": str(init_path),
        "prompt": args.prompt,
        "strength": args.strength,
        "steps": steps,
        "guidance_scale": guidance,
        "output": str(out_path),
        "device": args.device or _detect_gpu()["device"],
    }
    if args.dry_run or args.verbose:
        print("$ diffusers.img2img " + json.dumps(plan), file=sys.stderr)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "plan": plan}, indent=2))
        return 0

    if not (_module_available("diffusers") and _module_available("torch")):
        return _die("diffusers + torch not installed.", 5)

    import torch  # type: ignore
    import diffusers  # type: ignore
    from PIL import Image  # type: ignore

    device = args.device or _detect_gpu()["device"]

    # Map text-to-image pipeline class -> img2img class best-effort
    img2img_map = {
        "FluxPipeline": "FluxImg2ImgPipeline",
        "KolorsPipeline": "KolorsImg2ImgPipeline",
        "SanaPipeline": "SanaImg2ImgPipeline",
        "LuminaText2ImgPipeline": "LuminaText2ImgPipeline",  # no dedicated img2img yet
        "HunyuanDiTPipeline": "HunyuanDiTImg2ImgPipeline",
        "PixArtSigmaPipeline": "PixArtSigmaPipeline",
    }
    cls_name = img2img_map.get(model["pipeline"], "AutoPipelineForImage2Image")
    pipeline_cls = (
        getattr(diffusers, cls_name, None) or diffusers.AutoPipelineForImage2Image
    )

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    torch_dtype = dtype_map.get(args.dtype, torch.bfloat16)
    pipe = pipeline_cls.from_pretrained(model["repo"], torch_dtype=torch_dtype)
    if args.cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    init = Image.open(init_path).convert("RGB")
    generator = None
    if args.seed is not None:
        generator = torch.Generator(device=device).manual_seed(int(args.seed))

    kwargs = {
        "prompt": args.prompt,
        "image": init,
        "strength": float(args.strength),
        "num_inference_steps": int(steps),
        "guidance_scale": float(guidance),
    }
    if generator is not None:
        kwargs["generator"] = generator
    if args.negative_prompt:
        kwargs["negative_prompt"] = args.negative_prompt

    result = pipe(**kwargs)
    result.images[0].save(out_path)
    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# comfy-install (print instructions)
# --------------------------------------------------------------------------- #


def cmd_comfy_install(args: argparse.Namespace) -> int:
    target = args.target or "~/ComfyUI"
    lines = [
        f"# ComfyUI install (GPL-3.0) into {target}",
        f"git clone https://github.com/comfyanonymous/ComfyUI {target}",
        f"cd {target}",
        "python -m venv .venv",
        "source .venv/bin/activate    # Windows: .venv\\Scripts\\activate",
        "# PyTorch — pick ONE:",
        "#   CUDA 12.1:  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121",
        "#   CPU only :  pip install torch torchvision",
        "#   Apple MPS:  pip install torch torchvision  # universal2 wheel",
        "pip install -r requirements.txt",
        "# Optional: ComfyUI-Manager (node/model installer):",
        "git clone https://github.com/ltdrdata/ComfyUI-Manager custom_nodes/ComfyUI-Manager",
        "# Start:",
        "python main.py --listen 127.0.0.1 --port 8188",
    ]
    for line in lines:
        print(line)
    return 0


# --------------------------------------------------------------------------- #
# comfy-workflow (POST API-format JSON, poll, fetch PNG)
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


def cmd_comfy_workflow(args: argparse.Namespace) -> int:
    workflow_path = Path(args.workflow).expanduser().resolve()
    if not workflow_path.exists():
        return _die(f"workflow not found: {workflow_path}", 2)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with workflow_path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    # Detect UI-format (has "nodes" top-level list) vs API-format (flat dict of node_id -> node)
    if (
        isinstance(workflow, dict)
        and "nodes" in workflow
        and isinstance(workflow["nodes"], list)
    ):
        return _die(
            "workflow appears to be UI-format (contains top-level 'nodes' list). "
            "Re-export from ComfyUI with 'Save (API Format)' after enabling "
            "Settings -> 'Enable Dev mode Options'.",
            6,
        )

    server = args.server.rstrip("/")
    client_id = f"media-sd-{int(time.time())}"
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
        return _die(f"failed to POST workflow to ComfyUI: {e}", 7)
    prompt_id = submit.get("prompt_id")
    if not prompt_id:
        return _die(f"no prompt_id in response: {submit}", 7)

    _log(f"prompt_id={prompt_id}; polling /history...", True)
    deadline = time.time() + args.timeout
    history_url = f"{server}/history/{prompt_id}"
    images_meta: list[dict] = []
    while time.time() < deadline:
        try:
            hist = _http_get_json(history_url, 10)
        except Exception:
            time.sleep(1.0)
            continue
        entry = hist.get(prompt_id)
        if entry and entry.get("outputs"):
            for _node_id, node_out in entry["outputs"].items():
                for img in node_out.get("images", []) or []:
                    images_meta.append(img)
            if images_meta:
                break
        time.sleep(1.0)

    if not images_meta:
        return _die(f"timeout waiting for ComfyUI result (prompt_id={prompt_id})", 8)

    first = images_meta[0]
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
                "image_count": len(images_meta),
            },
            indent=2,
        )
    )
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def _add_global(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true", help="print plan; do not execute")
    p.add_argument("--verbose", action="store_true", help="stream progress / commands")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sd.py",
        description="Open-source AI image generation (OSI-open / commercial-safe only).",
    )
    _add_global(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="report env + GPU status")
    _add_global(c)
    c.set_defaults(func=cmd_check)

    c = sub.add_parser("install", help="print pip install line for a model")
    _add_global(c)
    c.add_argument("model", choices=list(MODELS.keys()))
    c.set_defaults(func=cmd_install)

    c = sub.add_parser("download", help="fetch weights from HuggingFace")
    _add_global(c)
    c.add_argument("--model", required=True, choices=list(MODELS.keys()))
    c.add_argument("--dest", default=None, help="local_dir for snapshot_download")
    c.add_argument("--yes", action="store_true", help="confirm large download")
    c.set_defaults(func=cmd_download)

    c = sub.add_parser("generate", help="text-to-image")
    _add_global(c)
    c.add_argument("--model", default="flux-schnell", choices=list(MODELS.keys()))
    c.add_argument("--prompt", required=True)
    c.add_argument("--negative-prompt", default=None)
    c.add_argument("--out", required=True)
    c.add_argument("--width", type=int, default=None)
    c.add_argument("--height", type=int, default=None)
    c.add_argument("--steps", type=int, default=None)
    c.add_argument("--guidance", type=float, default=None)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument(
        "--dtype", choices=["float32", "float16", "bfloat16"], default="bfloat16"
    )
    c.add_argument(
        "--device", default=None, help="cuda|mps|cpu (autodetect if omitted)"
    )
    c.add_argument(
        "--cpu-offload",
        action="store_true",
        help="enable_model_cpu_offload() for low VRAM",
    )
    c.set_defaults(func=cmd_generate)

    c = sub.add_parser("img2img", help="image-to-image edit")
    _add_global(c)
    c.add_argument("--model", default="flux-schnell", choices=list(MODELS.keys()))
    c.add_argument("--init-image", required=True)
    c.add_argument("--prompt", required=True)
    c.add_argument("--negative-prompt", default=None)
    c.add_argument("--strength", type=float, default=0.6)
    c.add_argument("--out", required=True)
    c.add_argument("--steps", type=int, default=None)
    c.add_argument("--guidance", type=float, default=None)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument(
        "--dtype", choices=["float32", "float16", "bfloat16"], default="bfloat16"
    )
    c.add_argument("--device", default=None)
    c.add_argument("--cpu-offload", action="store_true")
    c.set_defaults(func=cmd_img2img)

    c = sub.add_parser("comfy-install", help="print ComfyUI install commands")
    _add_global(c)
    c.add_argument(
        "--target", default=None, help="clone target dir (default ~/ComfyUI)"
    )
    c.set_defaults(func=cmd_comfy_install)

    c = sub.add_parser("comfy-workflow", help="run an API-format ComfyUI workflow")
    _add_global(c)
    c.add_argument("--workflow", required=True, help="path to API-format JSON")
    c.add_argument("--out", required=True, help="PNG output path")
    c.add_argument("--server", default="http://127.0.0.1:8188")
    c.add_argument("--timeout", type=int, default=300)
    c.set_defaults(func=cmd_comfy_workflow)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
