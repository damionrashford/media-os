#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""work-dir-space — warn before MEDIA_WORK_DIR fills up.

Media renders are bulk — a 4K ProRes master can be hundreds of GB. Filling
the scratch dir mid-encode corrupts output. This monitor checks free space
every DISK_POLL_SEC (default 120 s) and notifies when free space drops
below DISK_WARN_GB (default 20 GB) or DISK_CRITICAL_GB (default 5 GB).

Also notifies at the transitions out of those states so Claude knows the
pressure cleared.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def main() -> int:
    work_dir = os.environ.get("MEDIA_WORK_DIR", "/tmp/media-os")
    root = Path(os.path.expanduser(work_dir))
    root.mkdir(parents=True, exist_ok=True)

    poll = int(os.environ.get("DISK_POLL_SEC", "120"))
    warn_gb = float(os.environ.get("DISK_WARN_GB", "20"))
    crit_gb = float(os.environ.get("DISK_CRITICAL_GB", "5"))

    last_state: str | None = None

    while True:
        try:
            usage = shutil.disk_usage(root)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            pct_free = 100 * usage.free / usage.total if usage.total else 0

            if free_gb < crit_gb:
                state = "CRITICAL"
            elif free_gb < warn_gb:
                state = "WARN"
            else:
                state = "OK"

            if state != last_state:
                if state == "CRITICAL":
                    emit(
                        f"work-dir-space CRITICAL: {root} has {free_gb:.1f} GB free "
                        f"of {total_gb:.0f} GB ({pct_free:.1f}%). Encodes WILL fail."
                    )
                elif state == "WARN":
                    emit(
                        f"work-dir-space WARN: {root} at {free_gb:.1f} GB free "
                        f"({pct_free:.1f}%). Clean intermediates before the next render."
                    )
                elif last_state in ("WARN", "CRITICAL"):
                    emit(
                        f"work-dir-space OK: {root} now at {free_gb:.1f} GB free "
                        f"({pct_free:.1f}%)."
                    )
                last_state = state

            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"work-dir-space error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
