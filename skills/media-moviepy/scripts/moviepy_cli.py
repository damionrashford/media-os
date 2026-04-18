#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
moviepy_cli.py — a thin stdlib-only driver that generates a small MoviePy
program for each subcommand and runs it via `python -c`.

The caller's Python environment must have moviepy installed:
    pip install moviepy

Subcommands:
    check                          version + ImageMagick availability
    concat    --inputs A B ...     --output O.mp4
    subclip   --input I  --start S --end E --output O
    resize    --input I  --output O --width N
    text-overlay --input I --output O --text "X" [--position center|top|bottom]
                                                 [--font Arial] [--size 70]
    speed     --input I  --output O --factor 2.0
    fade      --input I  --output O [--fade-in SEC] [--fade-out SEC]
    image-to-video --image I --duration SEC --output O.mp4
    template  --config CONFIG.json

Global flags: --dry-run, --verbose

Example:
    python moviepy_cli.py concat --inputs a.mp4 b.mp4 --output out.mp4
    python moviepy_cli.py text-overlay --input in.mp4 --output out.mp4 \\
        --text "Hello" --position bottom --size 64
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Sequence


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _log(args: argparse.Namespace, msg: str) -> None:
    if getattr(args, "verbose", False):
        print(msg, file=sys.stderr)


def _run_python(source: str, args: argparse.Namespace) -> int:
    """Run generated Python source with the current interpreter."""
    if args.dry_run:
        print("# --- dry-run: would run this Python ---", file=sys.stderr)
        print(source, file=sys.stderr)
        return 0
    _log(args, f"Invoking: {sys.executable} -c <generated {len(source)} bytes>")
    proc = subprocess.run([sys.executable, "-c", source])
    return proc.returncode


def _require_exists(path: str) -> None:
    if not Path(path).exists():
        print(f"error: input does not exist: {path}", file=sys.stderr)
        sys.exit(2)


def _py_repr(value) -> str:
    """Safe repr for embedding Python literals in generated source."""
    return repr(value)


# --------------------------------------------------------------------------- #
# subcommand: check
# --------------------------------------------------------------------------- #


def cmd_check(args: argparse.Namespace) -> int:
    source = textwrap.dedent(
        """
        import sys, shutil
        try:
            import moviepy
        except ImportError:
            print("moviepy: NOT INSTALLED  (run: pip install moviepy)")
            sys.exit(1)
        print(f"moviepy: {moviepy.__version__}")
        try:
            import numpy
            print(f"numpy:   {numpy.__version__}")
        except ImportError:
            print("numpy:   MISSING")
        try:
            import PIL
            print(f"pillow:  {PIL.__version__}")
        except ImportError:
            print("pillow:  MISSING")
        im = shutil.which("magick") or shutil.which("convert")
        print(f"imagemagick: {im or 'NOT FOUND (TextClip will fail)'}")
        ff = shutil.which("ffmpeg")
        print(f"ffmpeg:  {ff or 'system ffmpeg not found (imageio-ffmpeg shim will be used)'}")
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: concat
# --------------------------------------------------------------------------- #


def cmd_concat(args: argparse.Namespace) -> int:
    for p in args.inputs:
        _require_exists(p)
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip, concatenate_videoclips
        inputs = {_py_repr(list(args.inputs))}
        clips = [VideoFileClip(p) for p in inputs]
        out = concatenate_videoclips(clips, method="compose")
        out.write_videofile({_py_repr(args.output)}, codec="libx264",
                            audio_codec="aac", fps=30, threads=4)
        for c in clips:
            c.close()
        out.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: subclip
# --------------------------------------------------------------------------- #


def cmd_subclip(args: argparse.Namespace) -> int:
    _require_exists(args.input)
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip
        c = VideoFileClip({_py_repr(args.input)}).subclipped({args.start!r}, {args.end!r})
        c.write_videofile({_py_repr(args.output)}, codec="libx264",
                          audio_codec="aac", fps=30, threads=4)
        c.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: resize
# --------------------------------------------------------------------------- #


def cmd_resize(args: argparse.Namespace) -> int:
    _require_exists(args.input)
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip
        c = VideoFileClip({_py_repr(args.input)}).resized(width={args.width!r})
        c.write_videofile({_py_repr(args.output)}, codec="libx264",
                          audio_codec="aac", fps=30, threads=4)
        c.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: text-overlay
# --------------------------------------------------------------------------- #


def cmd_text_overlay(args: argparse.Namespace) -> int:
    _require_exists(args.input)
    position_map = {
        "center": ("center", "center"),
        "top": ("center", "top"),
        "bottom": ("center", "bottom"),
    }
    pos = position_map.get(args.position, ("center", "bottom"))
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip, TextClip, CompositeVideoClip
        base = VideoFileClip({_py_repr(args.input)})
        txt = (TextClip(text={_py_repr(args.text)},
                        font_size={args.size!r},
                        color="white",
                        font={_py_repr(args.font)},
                        stroke_color="black",
                        stroke_width=2,
                        duration=base.duration)
               .with_position({_py_repr(pos)}))
        out = CompositeVideoClip([base, txt])
        out.write_videofile({_py_repr(args.output)}, codec="libx264",
                            audio_codec="aac", fps=30, threads=4)
        base.close(); out.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: speed
# --------------------------------------------------------------------------- #


def cmd_speed(args: argparse.Namespace) -> int:
    _require_exists(args.input)
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip
        c = VideoFileClip({_py_repr(args.input)}).with_speed_scaled(factor={args.factor!r})
        c.write_videofile({_py_repr(args.output)}, codec="libx264",
                          audio_codec="aac", fps=30, threads=4)
        c.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: fade
# --------------------------------------------------------------------------- #


def cmd_fade(args: argparse.Namespace) -> int:
    _require_exists(args.input)
    chain = "VideoFileClip(" + _py_repr(args.input) + ")"
    if args.fade_in and args.fade_in > 0:
        chain += f".with_fadein({args.fade_in!r})"
    if args.fade_out and args.fade_out > 0:
        chain += f".with_fadeout({args.fade_out!r})"
    source = textwrap.dedent(
        f"""
        from moviepy import VideoFileClip
        c = {chain}
        c.write_videofile({_py_repr(args.output)}, codec="libx264",
                          audio_codec="aac", fps=30, threads=4)
        c.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: image-to-video
# --------------------------------------------------------------------------- #


def cmd_image_to_video(args: argparse.Namespace) -> int:
    _require_exists(args.image)
    source = textwrap.dedent(
        f"""
        from moviepy import ImageClip
        c = ImageClip({_py_repr(args.image)}, duration={args.duration!r})
        c = c.with_fps(30)
        c.write_videofile({_py_repr(args.output)}, codec="libx264", fps=30, threads=4)
        c.close()
        """
    ).strip()
    return _run_python(source, args)


# --------------------------------------------------------------------------- #
# subcommand: template
# --------------------------------------------------------------------------- #

_TEMPLATE_DOC = """\
Declarative JSON template format:

{
  "output": "out.mp4",
  "fps": 30,
  "codec": "libx264",
  "audio_codec": "aac",
  "bitrate": "5000k",
  "size": [1920, 1080],
  "audio": "bg.mp3",            // optional
  "audio_fadein": 1.0,          // optional
  "audio_fadeout": 2.0,         // optional
  "clips": [
    {"type": "video", "path": "intro.mp4"},
    {"type": "video", "path": "body.mp4",
     "subclip": [0, 20], "resize_width": 1920,
     "fadein": 0.5, "fadeout": 0.5},
    {"type": "image", "path": "logo.png", "duration": 3,
     "resize_width": 1280},
    {"type": "color", "size": [1920, 1080], "color": [0, 0, 0], "duration": 2}
  ],
  "overlays": [                 // optional; composited on the whole timeline
    {"type": "text", "text": "Hello", "font_size": 64,
     "color": "white", "font": "Arial",
     "start": 2.0, "duration": 5.0,
     "position": ["center", "bottom"]}
  ]
}
"""


def _template_source(cfg: dict) -> str:
    """Generate a self-contained Python program from a template dict."""
    return textwrap.dedent(
        f"""
        import json
        from moviepy import (VideoFileClip, ImageClip, ColorClip, AudioFileClip,
                             TextClip, CompositeVideoClip, concatenate_videoclips)

        cfg = json.loads({_py_repr(json.dumps(cfg))})

        def _build_clip(c):
            t = c.get("type", "video")
            if t == "video":
                v = VideoFileClip(c["path"])
                if "subclip" in c:
                    v = v.subclipped(*c["subclip"])
                if "resize_width" in c:
                    v = v.resized(width=c["resize_width"])
                if "fadein" in c:
                    v = v.with_fadein(c["fadein"])
                if "fadeout" in c:
                    v = v.with_fadeout(c["fadeout"])
                return v
            if t == "image":
                i = ImageClip(c["path"], duration=c.get("duration", 3))
                if "resize_width" in c:
                    i = i.resized(width=c["resize_width"])
                return i
            if t == "color":
                return ColorClip(size=tuple(c["size"]),
                                 color=tuple(c["color"]),
                                 duration=c["duration"])
            raise ValueError(f"unknown clip type: {{t!r}}")

        clips = [_build_clip(c) for c in cfg["clips"]]
        timeline = concatenate_videoclips(clips, method="compose")

        if "audio" in cfg:
            a = AudioFileClip(cfg["audio"])
            if cfg.get("audio_fadein"):
                a = a.with_audio_fadein(cfg["audio_fadein"])
            if cfg.get("audio_fadeout"):
                a = a.with_audio_fadeout(cfg["audio_fadeout"])
            timeline = timeline.with_audio(a)

        overlays = cfg.get("overlays") or []
        if overlays:
            layers = [timeline]
            for o in overlays:
                if o["type"] == "text":
                    t = TextClip(text=o["text"],
                                 font_size=o.get("font_size", 48),
                                 color=o.get("color", "white"),
                                 font=o.get("font", "Arial"),
                                 stroke_color=o.get("stroke_color", "black"),
                                 stroke_width=o.get("stroke_width", 2),
                                 duration=o.get("duration", timeline.duration))
                    if "position" in o:
                        t = t.with_position(tuple(o["position"]))
                    if "start" in o:
                        t = t.with_start(o["start"])
                    layers.append(t)
            timeline = CompositeVideoClip(layers)

        timeline.write_videofile(
            cfg["output"],
            codec=cfg.get("codec", "libx264"),
            audio_codec=cfg.get("audio_codec", "aac"),
            fps=cfg.get("fps", 30),
            bitrate=cfg.get("bitrate"),
            threads=cfg.get("threads", 4),
        )
        """
    ).strip()


def cmd_template(args: argparse.Namespace) -> int:
    _require_exists(args.config)
    try:
        cfg = json.loads(Path(args.config).read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {args.config}: {e}", file=sys.stderr)
        return 2
    if "output" not in cfg or "clips" not in cfg:
        print("error: template config requires 'output' and 'clips'", file=sys.stderr)
        return 2
    return _run_python(_template_source(cfg), args)


# --------------------------------------------------------------------------- #
# argument parser
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="moviepy_cli",
        description="Stdlib-only driver that generates and runs MoviePy programs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_TEMPLATE_DOC,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the generated Python instead of executing it",
    )
    p.add_argument("--verbose", action="store_true", help="print progress to stderr")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="verify moviepy + ImageMagick availability")

    c = sub.add_parser("concat", help="concatenate N videos to one output")
    c.add_argument("--inputs", nargs="+", required=True, metavar="VIDEO")
    c.add_argument("--output", required=True)

    c = sub.add_parser("subclip", help="extract a time range from a video")
    c.add_argument("--input", required=True)
    c.add_argument("--start", required=True, type=float)
    c.add_argument("--end", required=True, type=float)
    c.add_argument("--output", required=True)

    c = sub.add_parser("resize", help="resize a video to a fixed width")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--width", required=True, type=int)

    c = sub.add_parser("text-overlay", help="burn a text caption into a video")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--text", required=True)
    c.add_argument("--position", choices=("center", "top", "bottom"), default="bottom")
    c.add_argument("--font", default="Arial")
    c.add_argument("--size", type=int, default=70, dest="size")

    c = sub.add_parser("speed", help="change playback speed")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--factor", required=True, type=float)

    c = sub.add_parser("fade", help="apply fade-in / fade-out to a video")
    c.add_argument("--input", required=True)
    c.add_argument("--output", required=True)
    c.add_argument("--fade-in", type=float, default=0.0, dest="fade_in")
    c.add_argument("--fade-out", type=float, default=0.0, dest="fade_out")

    c = sub.add_parser(
        "image-to-video", help="render a still image as a fixed-duration video"
    )
    c.add_argument("--image", required=True)
    c.add_argument("--duration", required=True, type=float)
    c.add_argument("--output", required=True)

    c = sub.add_parser("template", help="run a declarative JSON template")
    c.add_argument(
        "--config", required=True, help="path to a JSON file (see --help for schema)"
    )

    return p


_DISPATCH = {
    "check": cmd_check,
    "concat": cmd_concat,
    "subclip": cmd_subclip,
    "resize": cmd_resize,
    "text-overlay": cmd_text_overlay,
    "speed": cmd_speed,
    "fade": cmd_fade,
    "image-to-video": cmd_image_to_video,
    "template": cmd_template,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = _DISPATCH[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
