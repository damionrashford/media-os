#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""SessionStart hook: detect installed media tools and surface build flags.

Prints an additionalContext block so Claude knows which CLIs + ffmpeg build
flags are available BEFORE it recommends a pipeline. Prevents recommending
--enable-libvmaf filters when the user's ffmpeg wasn't built with libvmaf.

Runs in <1 s: shells out to each detector with a 2 s timeout, caches result
in $CLAUDE_PLUGIN_DATA/capabilities.json for 24 h to avoid re-probing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


CLIS = [
    "ffmpeg", "ffprobe", "ffplay",
    "yt-dlp", "mediainfo", "exiftool", "sox", "magick",
    "mkvmerge", "MP4Box", "packager", "HandBrakeCLI",
    "scenedetect", "ffmpeg-normalize", "whisper-cpp", "demucs",
    "dovi_tool", "hdr10plus_tool",
    "olad", "gphoto2", "ndi-record",
    "parallel", "rclone", "aws",
]


FFMPEG_BUILD_FLAGS = [
    "--enable-libx264", "--enable-libx265", "--enable-libvpx",
    "--enable-libaom", "--enable-libsvtav1",
    "--enable-libvmaf", "--enable-libvidstab", "--enable-libzimg",
    "--enable-librist", "--enable-libsrt", "--enable-libwebrtc",
    "--enable-libplacebo", "--enable-libfdk-aac", "--enable-libopus",
    "--enable-libopencore-amrnb", "--enable-libmp3lame",
    "--enable-libass", "--enable-libfreetype",
    "--enable-libopencolorio",
    "--enable-videotoolbox", "--enable-vaapi", "--enable-nvenc", "--enable-cuda",
]


def detect() -> dict:
    data: dict = {"generated_at": int(time.time()), "clis": {}, "ffmpeg_flags": {}}
    for cli in CLIS:
        data["clis"][cli] = bool(shutil.which(cli))
    if data["clis"].get("ffmpeg"):
        try:
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-version"],
                capture_output=True, text=True, timeout=3,
            )
            blob = (r.stdout or "") + (r.stderr or "")
            for flag in FFMPEG_BUILD_FLAGS:
                data["ffmpeg_flags"][flag] = flag in blob
        except Exception:
            pass
    return data


def format_context(data: dict) -> str:
    clis = data.get("clis", {})
    flags = data.get("ffmpeg_flags", {})
    have = [k for k, v in clis.items() if v]
    miss = [k for k, v in clis.items() if not v]
    ff_have = [k.replace("--enable-", "") for k, v in flags.items() if v]
    ff_miss = [k.replace("--enable-", "") for k, v in flags.items() if not v]
    lines = [
        "## Media OS — detected environment",
        "",
        f"**Installed CLIs:** {', '.join(have) if have else 'none'}",
    ]
    if miss:
        lines.append(
            f"**Missing CLIs** (skill scripts that need these will fail): {', '.join(miss)}"
        )
    if ff_have:
        lines.append(f"**ffmpeg build flags present:** {', '.join(ff_have)}")
    if ff_miss:
        lines.append(
            f"**ffmpeg build flags MISSING — do not recommend filters that need them:** {', '.join(ff_miss)}"
        )
    lines.append("")
    lines.append(
        "When a required tool or build flag is missing, surface the gap to the user "
        "BEFORE generating the command — do not silently produce a pipeline that will fail."
    )
    return "\n".join(lines)


def main() -> int:
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    cache_path: Path | None = None
    data: dict | None = None
    if data_dir:
        cache_path = Path(data_dir) / "capabilities.json"
        try:
            if cache_path.exists():
                cached = json.loads(cache_path.read_text())
                if int(time.time()) - cached.get("generated_at", 0) < 86400:
                    data = cached
        except Exception:
            data = None
    if data is None:
        data = detect()
        if cache_path is not None:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": format_context(data),
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
