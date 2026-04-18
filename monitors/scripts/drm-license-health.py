#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""drm-license-health — probe a Widevine / PlayReady / FairPlay key-server
health endpoint and notify on auth failures or extended downtime.

Set SHAKA_KEY_SERVER_URL (typically via plugin userConfig). The monitor
HEADs or GETs the URL every DRM_POLL_SEC (default 300 s). Two-state
transition reporter: healthy ↔ degraded.

Silent when the server is healthy and the state hasn't changed. Silent
when the URL isn't configured.
"""
from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request


def emit(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def check(url: str, timeout: int) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "media-os-drm-health/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
            return (200 <= code < 400, f"HTTP {code}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return (False, f"HTTP {e.code} AUTH")
        if e.code == 404:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "media-os-drm-health/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    code = r.getcode()
                    return (200 <= code < 400, f"HTTP {code}")
            except Exception as e2:
                return (False, f"HTTP {getattr(e2, 'code', '?')}")
        return (False, f"HTTP {e.code}")
    except Exception as e:
        return (False, f"UNREACHABLE ({type(e).__name__})")


def main() -> int:
    url = os.environ.get("SHAKA_KEY_SERVER_URL", "").strip()
    if not url:
        return 0
    poll = int(os.environ.get("DRM_POLL_SEC", "300"))
    timeout = int(os.environ.get("DRM_TIMEOUT_SEC", "15"))
    fail_streak_warn = int(os.environ.get("DRM_FAIL_STREAK_WARN", "2"))

    last_ok: bool | None = None
    fail_streak = 0

    while True:
        try:
            ok, detail = check(url, timeout)
            if ok:
                if last_ok is False:
                    emit(f"drm-license-health: {url} RECOVERED ({detail}).")
                fail_streak = 0
            else:
                fail_streak += 1
                if fail_streak == fail_streak_warn or (last_ok is not False and fail_streak >= 1):
                    emit(
                        f"drm-license-health: {url} DEGRADED — {detail} "
                        f"(streak={fail_streak}). Encodes that need DRM will fail."
                    )
            last_ok = ok
            time.sleep(poll)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            emit(f"drm-license-health error: {e}")
            time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
