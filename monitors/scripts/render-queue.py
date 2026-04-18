#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""render-queue — watch a render-farm queue for completed / failed jobs.

Generic poller that expects a JSON endpoint or a jobs directory. Two
modes:

1. HTTP mode (RENDER_QUEUE_URL set): GET the URL, expect a JSON list of
   `[{"id": "...", "status": "queued|running|done|failed", "name": "..."}]`.
2. Directory mode (RENDER_QUEUE_DIR set): scan for `*.status` sidecar
   files. Each file's first line is the status token; the filename stem
   is the job id.

Emits a notification only on state transitions (queued → done, running →
failed). Silent otherwise. Skippable — both env vars empty = monitor
exits 0.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def poll_http(url: str, timeout: int) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "media-os-render-queue/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        if isinstance(data, list):
            return [j for j in data if isinstance(j, dict)]
        if isinstance(data, dict) and isinstance(data.get("jobs"), list):
            return [j for j in data["jobs"] if isinstance(j, dict)]
        return []
    except Exception:
        return []


def poll_dir(root: Path) -> list[dict]:
    out: list[dict] = []
    for p in root.glob("*.status"):
        try:
            status = p.read_text().strip().splitlines()[0].strip().lower()
        except Exception:
            continue
        out.append({"id": p.stem, "status": status, "name": p.stem})
    return out


def main() -> int:
    url = os.environ.get("RENDER_QUEUE_URL", "").strip()
    directory = os.environ.get("RENDER_QUEUE_DIR", "").strip()
    if not url and not directory:
        return 0
    poll = int(os.environ.get("RENDER_POLL_SEC", "60"))
    timeout = int(os.environ.get("RENDER_HTTP_TIMEOUT_SEC", "10"))
    last: dict[str, str] = {}

    while True:
        try:
            if url:
                jobs = poll_http(url, timeout)
            else:
                root = Path(os.path.expanduser(directory))
                jobs = poll_dir(root) if root.is_dir() else []
            for j in jobs:
                jid = str(j.get("id") or j.get("name") or "?")
                status = str(j.get("status") or "?").lower()
                name = j.get("name") or jid
                prev = last.get(jid)
                if prev is None:
                    last[jid] = status
                    continue
                if prev != status:
                    last[jid] = status
                    if status == "done":
                        emit(f"render-queue: job {name} ({jid}) DONE.")
                    elif status == "failed":
                        emit(f"render-queue: job {name} ({jid}) FAILED.")
                    elif status in ("queued", "running", "paused"):
                        emit(f"render-queue: job {name} ({jid}) → {status}.")
            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"render-queue error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
