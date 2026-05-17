#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""SubagentStop hook: log every Media OS modes dispatch.

Writes one JSON line per dispatch to ${MEDIA_WORK_DIR:-/tmp/media-os}/modes/dispatch.log.

Each line: timestamp, mode (description field), specialist (subagent_type),
duration_ms, exit status, transcript path.

Non-blocking: any error here must NOT fail the dispatch. Print to stderr and exit 0.
"""

import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        # stdin wasn't JSON — nothing to audit, exit clean
        return 0

    # Resolve audit log path
    work_dir = os.environ.get("MEDIA_WORK_DIR", "/tmp/media-os")
    log_dir = Path(work_dir) / "modes"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"dispatch-audit: cannot create {log_dir}: {e}", file=sys.stderr)
        return 0

    log_path = log_dir / "dispatch.log"

    # Extract fields. SubagentStop payload shape per Claude Code spec:
    #   { "hook_event_name": "SubagentStop",
    #     "session_id": "...",
    #     "transcript_path": "...",
    #     "stop_hook_active": bool,
    #     "subagent_type": "...",      # the specialist
    #     "description": "...",        # the mode name (what we passed on Agent())
    #     "duration_ms": int,
    #     "exit_status": "success"|"failure"|... }
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": payload.get("description", "<unknown-mode>"),
        "specialist": payload.get("subagent_type", "<unknown-agent>"),
        "duration_ms": payload.get("duration_ms"),
        "exit_status": payload.get("exit_status"),
        "session_id": payload.get("session_id"),
        "transcript_path": payload.get("transcript_path"),
    }

    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError as e:
        print(f"dispatch-audit: cannot write {log_path}: {e}", file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
