#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""PostToolUse hook on Bash: verify ffmpeg outputs after they're written.

When a Bash ffmpeg command writes an output file, ffprobe it and surface a
one-line sanity summary (container, streams, duration). Catches silent
failures where ffmpeg exits 0 but produces a zero-duration or corrupt file.

Does NOT block. Writes to additionalContext so Claude sees the result.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


MEDIA_EXTS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".ts", ".m2ts", ".mxf",
    ".wav", ".flac", ".mp3", ".aac", ".m4a", ".opus", ".ogg",
    ".m3u8", ".mpd",
}


def extract_output(cmd: str) -> Path | None:
    if "ffmpeg" not in cmd:
        return None
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        return None
    try:
        ff_idx = next(i for i, t in enumerate(tokens) if Path(t).name == "ffmpeg")
    except StopIteration:
        return None
    args = tokens[ff_idx + 1:]
    if not args:
        return None
    last = args[-1]
    if last.startswith("-"):
        return None
    p = Path(os.path.expanduser(last))
    if p.suffix.lower() not in MEDIA_EXTS:
        return None
    return p if p.exists() else None


def probe_summary(p: Path) -> str:
    if not shutil.which("ffprobe"):
        return ""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-hide_banner", "-v", "error",
                "-print_format", "json",
                "-show_format", "-show_streams", str(p),
            ],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return f"ffprobe failed on {p.name}: {r.stderr.strip()}"
        info = json.loads(r.stdout)
    except Exception as e:
        return f"ffprobe error on {p.name}: {e}"
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    dur = float(fmt.get("duration", 0) or 0)
    size = int(fmt.get("size", 0) or 0)
    warnings: list[str] = []
    if dur < 0.1:
        warnings.append("duration is ~0s \u2014 output is likely empty")
    if size < 1024:
        warnings.append(f"file size is {size} B \u2014 output is likely truncated")
    v = [s for s in streams if s.get("codec_type") == "video"]
    a = [s for s in streams if s.get("codec_type") == "audio"]
    parts = [
        f"container `{fmt.get('format_name','?')}`",
        f"{len(v)}v+{len(a)}a streams",
        f"{dur:.2f}s",
        f"{size} B",
    ]
    if v:
        vs = v[0]
        parts.append(
            f"video `{vs.get('codec_name')}` {vs.get('width')}x{vs.get('height')} "
            f"pix_fmt=`{vs.get('pix_fmt')}`"
        )
    msg = f"PostToolUse verify: {p.name} \u2014 " + ", ".join(parts)
    if warnings:
        msg += " | \u26a0\ufe0f " + " | ".join(warnings)
    return msg


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = payload.get("tool_input", {}).get("command", "")
    out_path = extract_output(cmd)
    if out_path is None:
        return 0
    summary = probe_summary(out_path)
    if not summary:
        return 0
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": summary,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
