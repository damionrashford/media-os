#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""incoming-watch — poll INCOMING_MEDIA_DIR for new media files.

Emits a newline-delimited JSON event on stdout for each new file so the
Media OS plugin's monitor hook can surface it to Claude as a prompt.

Env:
  INCOMING_MEDIA_DIR   directory to poll (empty \u2192 disabled, monitor exits 0)
  POLL_INTERVAL_SEC    poll every N seconds (default 30)
  STABILITY_SEC        file mtime must be at least N s old to be considered
                       done being written (default 15)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


MEDIA_EXTS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".ts", ".m2ts", ".mxf",
    ".wav", ".flac", ".mp3", ".aac", ".m4a", ".opus", ".ogg",
    ".exr", ".dpx",
}


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def main() -> int:
    watch_dir = os.environ.get("INCOMING_MEDIA_DIR", "").strip()
    if not watch_dir:
        return 0
    root = Path(os.path.expanduser(watch_dir))
    if not root.exists() or not root.is_dir():
        emit(f"incoming-watch: configured directory not found: {root}")
        return 0

    poll = int(os.environ.get("POLL_INTERVAL_SEC", "30"))
    stability = int(os.environ.get("STABILITY_SEC", "15"))
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".claude-plugin-data" / "media-os"))
    state = Path(data_dir) / "incoming-watch.seen.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    try:
        seen = set(json.loads(state.read_text()))
    except Exception:
        seen = set()

    def fmt_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    while True:
        try:
            now = time.time()
            new = []
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in MEDIA_EXTS:
                    continue
                try:
                    mtime = p.stat().st_mtime
                    size = p.stat().st_size
                except OSError:
                    continue
                if now - mtime < stability:
                    continue
                key = f"{p}:{mtime:.0f}:{size}"
                if key in seen:
                    continue
                seen.add(key)
                new.append((p, mtime, size))
            if new:
                for p, _, size in new:
                    emit(
                        f"New media: {p} ({fmt_size(size)}). "
                        f"Run `moprobe {p}` for a summary; flag zero-duration, missing audio, "
                        f"or mismatched color tags."
                    )
                try:
                    state.write_text(json.dumps(sorted(seen)))
                except Exception:
                    pass
            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"incoming-watch error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
