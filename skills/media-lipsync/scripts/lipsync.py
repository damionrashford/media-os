#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-lipsync driver: open-source, commercial-safe AI lip-sync + talking-head.

Subcommands:
    check           Report env, GPU, and whether LivePortrait / LatentSync are installed.
    animate         LivePortrait: animate a still image from audio OR a driving video.
    sync            LatentSync: re-sync an existing video's lips to a new audio track.
    dub             Wrapper around `sync` with defaults tuned for speech dubbing.
    install         Print install instructions for a model (does not run them).

Global flags:
    --dry-run       Print the exact `python inference.py` command; do not execute.
    --verbose       Echo commands + progress.

Stdlib only. Non-interactive.

Model sources (clone these; env vars override):
    LivePortrait   https://github.com/KwaiVGI/LivePortrait          default ~/LivePortrait
    LatentSync     https://github.com/bytedance/LatentSync          default ~/LatentSync

Environment overrides:
    LIVEPORTRAIT_ROOT  full path to a LivePortrait checkout
    LATENTSYNC_ROOT    full path to a LatentSync checkout

Examples:
    uv run scripts/lipsync.py check
    uv run scripts/lipsync.py animate --model liveportrait \\
        --source face.jpg --driving speech.wav --out out.mp4
    uv run scripts/lipsync.py animate --model liveportrait \\
        --source face.jpg --driving actor.mp4 --out retarget.mp4
    uv run scripts/lipsync.py sync --model latentsync \\
        --video in.mp4 --audio new.wav --out resynced.mp4 --steps 25
    uv run scripts/lipsync.py dub --video en.mp4 --new-audio es.wav --out es.mp4
    uv run scripts/lipsync.py install liveportrait
    uv run scripts/lipsync.py install latentsync
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Model info
# --------------------------------------------------------------------------- #

MODELS = {
    "liveportrait": {
        "repo_url": "https://github.com/KwaiVGI/LivePortrait",
        "env_var": "LIVEPORTRAIT_ROOT",
        "default_dir": Path.home() / "LivePortrait",
        "license": "MIT",
        "inference_module": "inference.py",
        "notes": "Portrait animation from still + (audio or video). Full facial motion.",
    },
    "latentsync": {
        "repo_url": "https://github.com/bytedance/LatentSync",
        "env_var": "LATENTSYNC_ROOT",
        "default_dir": Path.home() / "LatentSync",
        "license": "Apache 2.0",
        "inference_module": "scripts/inference.py",
        "notes": "Diffusion-based lip-region re-sync on an existing video.",
    },
}

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[lipsync] {msg}", file=sys.stderr)


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


def _run(cmd: list[str], dry_run: bool, verbose: bool, cwd: Path | None = None) -> int:
    if dry_run or verbose:
        _echo_cmd(cmd)
        if cwd:
            print(f"  (cwd={cwd})", file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode


def _model_root(model_key: str) -> Path | None:
    info = MODELS.get(model_key)
    if not info:
        return None
    env = os.environ.get(info["env_var"])
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p
    p = info["default_dir"]
    return p if p.exists() else None


def _detect_gpu() -> dict:
    info = {"cuda": False, "mps": False, "device": "cpu"}
    if _which("nvidia-smi"):
        try:
            subprocess.check_output(
                ["nvidia-smi", "-L"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            info["cuda"] = True
            info["device"] = "cuda"
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


def _classify_driving(path: Path) -> str:
    """Return 'audio' or 'video' based on suffix."""
    s = path.suffix.lower()
    if s in AUDIO_EXTS:
        return "audio"
    if s in VIDEO_EXTS:
        return "video"
    return "unknown"


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    info: dict = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "gpu": _detect_gpu(),
        "ffmpeg": bool(_which("ffmpeg")),
        "models": {},
    }
    for key, meta in MODELS.items():
        root = _model_root(key)
        info["models"][key] = {
            "repo_url": meta["repo_url"],
            "license": meta["license"],
            "root": str(root) if root else None,
            "found": root is not None,
        }
    print(json.dumps(info, indent=2))
    any_found = any(v["found"] for v in info["models"].values())
    return 0 if any_found else 1


# --------------------------------------------------------------------------- #
# install (prints guidance)
# --------------------------------------------------------------------------- #


def cmd_install(args: argparse.Namespace) -> int:
    key = args.model
    if key not in MODELS:
        return _die(f"unknown model '{key}'. Valid: {', '.join(MODELS.keys())}", 3)
    meta = MODELS[key]
    target = Path(os.environ.get(meta["env_var"]) or meta["default_dir"]).expanduser()

    lines = [
        f"# {key} ({meta['license']})",
        f"# upstream: {meta['repo_url']}",
        "",
        f"git clone {meta['repo_url']} {target}",
        f"cd {target}",
        "python -m venv .venv && source .venv/bin/activate",
        "pip install -r requirements.txt",
    ]
    if key == "liveportrait":
        lines += [
            "# Follow upstream README section 'Download pretrained weights':",
            "#   bash scripts/download_pretrained_weights.sh     # if provided",
            "#   OR download from HuggingFace:",
            "huggingface-cli download KwaiVGI/LivePortrait --local-dir pretrained_weights",
            "",
            "# optional: set env var so this driver finds the repo",
            f"export {meta['env_var']}={target}",
        ]
    else:  # latentsync
        lines += [
            "# Weights from ByteDance HuggingFace:",
            "huggingface-cli download ByteDance/LatentSync --local-dir checkpoints",
            "",
            f"export {meta['env_var']}={target}",
        ]
    for line in lines:
        print(line)
    return 0


# --------------------------------------------------------------------------- #
# animate (LivePortrait)
# --------------------------------------------------------------------------- #


def cmd_animate(args: argparse.Namespace) -> int:
    if args.model != "liveportrait":
        return _die(
            f"animate is LivePortrait-only; got --model {args.model}. "
            "For existing-video lip-sync use `sync --model latentsync`.",
            4,
        )
    root = _model_root("liveportrait")
    if not root:
        return _die(
            "LivePortrait repo not found. Run `lipsync.py install liveportrait` "
            "for setup, or set LIVEPORTRAIT_ROOT.",
            5,
        )
    source = Path(args.source).expanduser().resolve()
    driving = Path(args.driving).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    if not source.exists():
        return _die(f"source not found: {source}", 2)
    if not driving.exists():
        return _die(f"driving not found: {driving}", 2)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    kind = _classify_driving(driving)
    inference = root / "inference.py"
    if not inference.exists():
        return _die(f"LivePortrait inference.py missing at {inference}", 6)

    # LivePortrait CLI (as of 2024-2025 releases) accepts:
    #   -s SOURCE_IMAGE
    #   -d DRIVING (video OR audio)
    #   --output-dir OUT_DIR
    # The tool writes an mp4 inside OUT_DIR; we post-move to the requested path.
    out_dir = out_path.parent / f".lp_tmp_{out_path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(inference),
        "-s",
        str(source),
        "-d",
        str(driving),
        "--output-dir",
        str(out_dir),
    ]
    if args.fps:
        cmd += ["--output-fps", str(int(args.fps))]
    if args.flag_cpu:
        cmd += ["--flag-force-cpu"]

    plan = {
        "mode": "animate",
        "model": "liveportrait",
        "driving_kind": kind,
        "source": str(source),
        "driving": str(driving),
        "output": str(out_path),
        "output_tmp_dir": str(out_dir),
        "fps": args.fps,
        "repo": str(root),
    }
    if args.dry_run or args.verbose:
        print(f"[lipsync] plan: {json.dumps(plan)}", file=sys.stderr)
    rc = _run(cmd, args.dry_run, args.verbose, cwd=root)
    if rc != 0 or args.dry_run:
        return rc

    # Find the produced mp4 in out_dir; move to final out_path.
    mp4s = sorted(out_dir.glob("*.mp4"))
    if not mp4s:
        return _die(f"LivePortrait did not produce an mp4 in {out_dir}", 7)
    final_src = mp4s[-1]
    shutil.move(str(final_src), str(out_path))
    # best-effort cleanup
    for f in out_dir.iterdir():
        try:
            f.unlink()
        except Exception:
            pass
    try:
        out_dir.rmdir()
    except Exception:
        pass

    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# sync (LatentSync)
# --------------------------------------------------------------------------- #


def cmd_sync(args: argparse.Namespace) -> int:
    if args.model != "latentsync":
        return _die(
            f"sync is LatentSync-only; got --model {args.model}. "
            "For still-image animation use `animate --model liveportrait`.",
            4,
        )
    root = _model_root("latentsync")
    if not root:
        return _die(
            "LatentSync repo not found. Run `lipsync.py install latentsync` "
            "or set LATENTSYNC_ROOT.",
            5,
        )
    video = Path(args.video).expanduser().resolve()
    audio = Path(args.audio).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    if not video.exists():
        return _die(f"video not found: {video}", 2)
    if not audio.exists():
        return _die(f"audio not found: {audio}", 2)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    inference = root / "scripts" / "inference.py"
    if not inference.exists():
        return _die(f"LatentSync scripts/inference.py missing at {inference}", 6)

    config = args.config or str(root / "configs" / "unet" / "second_stage.yaml")

    cmd = [
        sys.executable,
        str(inference),
        "--unet_config_path",
        config,
        "--inference_ckpt_path",
        args.ckpt or str(root / "checkpoints" / "latentsync_unet.pt"),
        "--video_path",
        str(video),
        "--audio_path",
        str(audio),
        "--video_out_path",
        str(out_path),
        "--inference_steps",
        str(int(args.steps)),
        "--guidance_scale",
        str(float(args.guidance)),
    ]
    if args.seed is not None:
        cmd += ["--seed", str(int(args.seed))]

    plan = {
        "mode": "sync",
        "model": "latentsync",
        "video": str(video),
        "audio": str(audio),
        "output": str(out_path),
        "steps": args.steps,
        "guidance": args.guidance,
        "seed": args.seed,
        "repo": str(root),
    }
    if args.dry_run or args.verbose:
        print(f"[lipsync] plan: {json.dumps(plan)}", file=sys.stderr)
    rc = _run(cmd, args.dry_run, args.verbose, cwd=root)
    if rc != 0 or args.dry_run:
        return rc

    print(json.dumps({"status": "ok", **plan}, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# dub (wrapper around sync)
# --------------------------------------------------------------------------- #


def cmd_dub(args: argparse.Namespace) -> int:
    # Rewrite args into the sync shape.
    class _Args:
        pass

    sync_args = _Args()
    sync_args.model = args.model
    sync_args.video = args.video
    sync_args.audio = args.new_audio
    sync_args.out = args.out
    sync_args.steps = args.steps
    sync_args.guidance = args.guidance
    sync_args.seed = args.seed
    sync_args.config = args.config
    sync_args.ckpt = args.ckpt
    sync_args.dry_run = args.dry_run
    sync_args.verbose = args.verbose
    return cmd_sync(sync_args)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def _add_global(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lipsync.py",
        description="Open-source AI lip-sync + talking-head (MIT / Apache 2.0 only).",
    )
    _add_global(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="report env + installed model roots")
    _add_global(c)
    c.set_defaults(func=cmd_check)

    c = sub.add_parser("install", help="print install instructions for a model")
    _add_global(c)
    c.add_argument("model", choices=list(MODELS.keys()))
    c.set_defaults(func=cmd_install)

    c = sub.add_parser(
        "animate", help="LivePortrait: drive a still from audio or video"
    )
    _add_global(c)
    c.add_argument("--model", default="liveportrait", choices=["liveportrait"])
    c.add_argument("--source", required=True, help="source image (still photo)")
    c.add_argument(
        "--driving", required=True, help="driving audio .wav OR driving video .mp4"
    )
    c.add_argument("--out", required=True, help="output mp4 path")
    c.add_argument(
        "--fps", type=int, default=None, help="output fps (default = driving fps)"
    )
    c.add_argument("--flag-cpu", action="store_true", help="force CPU (very slow)")
    c.set_defaults(func=cmd_animate)

    c = sub.add_parser(
        "sync", help="LatentSync: re-sync existing video's lips to new audio"
    )
    _add_global(c)
    c.add_argument("--model", default="latentsync", choices=["latentsync"])
    c.add_argument("--video", required=True, help="source video (face visible)")
    c.add_argument("--audio", required=True, help="new audio track")
    c.add_argument("--out", required=True, help="output mp4 path")
    c.add_argument("--steps", type=int, default=25, help="diffusion steps (default 25)")
    c.add_argument(
        "--guidance", type=float, default=1.5, help="guidance scale (default 1.5)"
    )
    c.add_argument("--seed", type=int, default=None)
    c.add_argument(
        "--config",
        default=None,
        help="path to unet config yaml (default: configs/unet/second_stage.yaml)",
    )
    c.add_argument("--ckpt", default=None, help="path to inference checkpoint .pt")
    c.set_defaults(func=cmd_sync)

    c = sub.add_parser("dub", help="shortcut for `sync` tuned for speech dubbing")
    _add_global(c)
    c.add_argument("--model", default="latentsync", choices=["latentsync"])
    c.add_argument("--video", required=True)
    c.add_argument("--new-audio", required=True, help="dubbed voice track")
    c.add_argument("--out", required=True)
    c.add_argument("--steps", type=int, default=25)
    c.add_argument("--guidance", type=float, default=1.5)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument("--config", default=None)
    c.add_argument("--ckpt", default=None)
    c.set_defaults(func=cmd_dub)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
