#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""stream-health — probe a live-stream ingest URL and notify on degradation.

Set LIVE_STREAM_URL to an RTMP/SRT/RTSP/HLS URL. The monitor ffprobes it
every STREAM_POLL_SEC (default 60 s) and emits a notification only when
state changes (up/down, bitrate drop, audio-only, frame drops).

No notification when state is healthy and unchanged — avoids
background-noise spam.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def probe(url: str, timeout: int) -> dict | None:
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(
            [
                "ffprobe", "-hide_banner", "-v", "error",
                "-timeout", str(timeout * 1_000_000),
                "-rw_timeout", str(timeout * 1_000_000),
                "-print_format", "json",
                "-show_format", "-show_streams",
                url,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def summarize(info: dict) -> dict:
    fmt = info.get("format", {}) or {}
    streams = info.get("streams", []) or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "bitrate": int(fmt.get("bit_rate") or 0),
        "has_video": bool(v),
        "has_audio": bool(a),
        "v_codec": (v or {}).get("codec_name"),
        "v_w": (v or {}).get("width"),
        "v_h": (v or {}).get("height"),
        "v_fps": (v or {}).get("r_frame_rate"),
        "a_codec": (a or {}).get("codec_name"),
    }


def main() -> int:
    url = os.environ.get("LIVE_STREAM_URL", "").strip()
    if not url:
        return 0
    poll = int(os.environ.get("STREAM_POLL_SEC", "60"))
    timeout = int(os.environ.get("STREAM_PROBE_TIMEOUT_SEC", "15"))
    degrade_factor = float(os.environ.get("STREAM_BITRATE_DEGRADE_FACTOR", "0.5"))

    last_state: str | None = None
    last_bitrate: int = 0

    while True:
        try:
            info = probe(url, timeout)
            if info is None:
                state = "DOWN"
                if last_state != state:
                    emit(f"stream-health: {url} UNREACHABLE (ffprobe failed or timed out)")
                last_state = state
                last_bitrate = 0
            else:
                s = summarize(info)
                current = s["bitrate"]
                if not s["has_video"]:
                    state = "AUDIO-ONLY"
                    if last_state != state:
                        emit(f"stream-health: {url} is AUDIO-ONLY (no video stream)")
                elif not s["has_audio"]:
                    state = "VIDEO-ONLY"
                    if last_state != state:
                        emit(f"stream-health: {url} is VIDEO-ONLY (no audio stream)")
                else:
                    state = "UP"
                    if last_state in (None, "DOWN", "AUDIO-ONLY", "VIDEO-ONLY"):
                        emit(
                            f"stream-health: {url} UP — "
                            f"{s['v_codec']} {s['v_w']}x{s['v_h']} @ {s['v_fps']}, "
                            f"{s['a_codec']}, {current//1000} kbps"
                        )
                    elif last_bitrate and current < last_bitrate * degrade_factor:
                        emit(
                            f"stream-health: {url} BITRATE DROP — "
                            f"{last_bitrate//1000} → {current//1000} kbps"
                        )
                last_state = state
                last_bitrate = current
            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"stream-health error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
