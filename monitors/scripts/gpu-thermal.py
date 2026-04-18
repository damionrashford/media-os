#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""gpu-thermal — warn when the GPU is about to throttle.

Polls `nvidia-smi` (CUDA) every GPU_POLL_SEC (default 30 s). If temperature
exceeds GPU_TEMP_WARN_C (default 80 °C) or utilization stays above
GPU_UTIL_HEAVY_PCT (default 95 %) for more than GPU_HEAVY_SUSTAIN_SEC
(default 300 s), emits a one-line notification.

Silent when the GPU is healthy. Silent on non-Nvidia systems (macOS Metal,
AMD ROCm) — the monitor exits 0 without spamming.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def poll_nvidia() -> list[dict]:
    r = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True, text=True, timeout=10,
    )
    out: list[dict] = []
    if r.returncode != 0:
        return out
    for line in r.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 8:
            continue
        out.append(
            {
                "idx": int(parts[0]),
                "name": parts[1],
                "temp_c": int(parts[2]),
                "util_pct": int(parts[3]),
                "mem_used_mb": int(parts[4]),
                "mem_total_mb": int(parts[5]),
                "power_w": float(parts[6]),
                "power_limit_w": float(parts[7]),
            }
        )
    return out


def main() -> int:
    if not shutil.which("nvidia-smi"):
        return 0
    poll = int(os.environ.get("GPU_POLL_SEC", "30"))
    temp_warn = int(os.environ.get("GPU_TEMP_WARN_C", "80"))
    util_heavy = int(os.environ.get("GPU_UTIL_HEAVY_PCT", "95"))
    heavy_sustain = int(os.environ.get("GPU_HEAVY_SUSTAIN_SEC", "300"))

    heavy_since: dict[int, float] = {}
    warned_temp: set[int] = set()
    warned_sustain: set[int] = set()

    while True:
        try:
            gpus = poll_nvidia()
            now = time.time()
            for g in gpus:
                idx = g["idx"]
                if g["temp_c"] >= temp_warn:
                    if idx not in warned_temp:
                        emit(
                            f"gpu-thermal: GPU {idx} {g['name']} at {g['temp_c']}°C "
                            f"(warn threshold {temp_warn}°C). Throttling may begin soon."
                        )
                        warned_temp.add(idx)
                else:
                    warned_temp.discard(idx)

                if g["util_pct"] >= util_heavy:
                    since = heavy_since.setdefault(idx, now)
                    if now - since > heavy_sustain and idx not in warned_sustain:
                        emit(
                            f"gpu-thermal: GPU {idx} {g['name']} sustained "
                            f"{g['util_pct']}% util for {int(now - since)}s "
                            f"({g['power_w']:.0f}W / {g['power_limit_w']:.0f}W)."
                        )
                        warned_sustain.add(idx)
                else:
                    heavy_since.pop(idx, None)
                    warned_sustain.discard(idx)
            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"gpu-thermal error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
