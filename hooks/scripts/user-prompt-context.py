#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""UserPromptSubmit hook: inject task-specific context from the prompt.

When the user's prompt names a file that's already on disk, prepend a tiny
ffprobe summary so Claude doesn't have to spend a turn probing it. Low
noise: only triggers when the prompt literally names a path we can stat.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


MEDIA_EXTS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".ts", ".m2ts", ".mxf",
    ".wav", ".flac", ".mp3", ".aac", ".m4a", ".opus", ".ogg",
    ".exr", ".dpx", ".tiff", ".png", ".jpg", ".jpeg",
    ".mpd", ".m3u8", ".vtt", ".srt", ".ass",
}


def find_paths(prompt: str) -> list[Path]:
    hits: list[Path] = []
    for m in re.findall(r"(?:/|\./|~/)[\w\-./ ]+", prompt):
        p = Path(os.path.expanduser(m.strip())).resolve()
        if p.exists() and p.is_file() and p.suffix.lower() in MEDIA_EXTS:
            hits.append(p)
    return hits[:3]


def probe(p: Path) -> str:
    if not shutil.which("ffprobe"):
        return ""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-hide_banner", "-v", "error",
                "-print_format", "json",
                "-show_format", "-show_streams", str(p),
            ],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return ""
        info = json.loads(r.stdout)
    except Exception:
        return ""
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    lines = [f"### {p.name}"]
    dur = fmt.get("duration")
    size = fmt.get("size")
    fname = fmt.get("format_name")
    if dur or size or fname:
        lines.append(
            f"- container: `{fname}`  duration: `{dur}s`  size: `{size}B`"
        )
    for s in streams:
        t = s.get("codec_type")
        codec = s.get("codec_name")
        if t == "video":
            lines.append(
                f"- video: `{codec}` {s.get('width')}x{s.get('height')} "
                f"pix_fmt=`{s.get('pix_fmt')}` "
                f"color_primaries=`{s.get('color_primaries','-')}` "
                f"transfer=`{s.get('color_transfer','-')}` "
                f"fps=`{s.get('r_frame_rate','-')}`"
            )
        elif t == "audio":
            lines.append(
                f"- audio: `{codec}` ch=`{s.get('channels')}` "
                f"rate=`{s.get('sample_rate')}` layout=`{s.get('channel_layout','-')}`"
            )
        elif t == "subtitle":
            lines.append(f"- subtitle: `{codec}`")
    return "\n".join(lines)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = payload.get("prompt", "")
    if not prompt:
        return 0
    hits = find_paths(prompt)
    if not hits:
        return 0
    blocks = [probe(p) for p in hits]
    blocks = [b for b in blocks if b]
    if not blocks:
        return 0
    ctx = "## Media OS — auto-probed inputs\n\n" + "\n\n".join(blocks)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ctx,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
