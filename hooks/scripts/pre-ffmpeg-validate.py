#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""PreToolUse hook on Bash: guard against classic ffmpeg footguns.

Matches Bash tool invocations and inspects the command string for common
mistakes. Returns `permissionDecision: ask` (not block) when a foot-gun
is detected, so the user can override. Only blocks on truly destructive
patterns (e.g. overwriting the input).

Checks:
  1. `-y` overwriting an output that already exists (when SAFETY_REQUIRE_CONFIRM_OVERWRITE=true)
  2. Output path equals input path (in-place overwrite, almost always a bug)
  3. MP4 output without `-movflags +faststart` (web playback pessimization)
  4. HLS segmenter without `-sc_threshold 0` (keyframe misalignment)
  5. TS -> MP4 without `-bsf:a aac_adtstoasc`
  6. x264/x265 with CRF AND bitrate (conflicting rate control)
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path


def scan(cmd: str) -> list[str]:
    warnings: list[str] = []
    if "ffmpeg" not in cmd:
        return warnings
    tokens = shlex.split(cmd, posix=True)
    try:
        ff_idx = next(i for i, t in enumerate(tokens) if Path(t).name == "ffmpeg")
    except StopIteration:
        return warnings
    args = tokens[ff_idx + 1:]
    inputs: list[str] = []
    output = None
    i = 0
    while i < len(args):
        t = args[i]
        if t == "-i" and i + 1 < len(args):
            inputs.append(args[i + 1])
            i += 2
            continue
        i += 1
    if args and not args[-1].startswith("-"):
        output = args[-1]
    if output:
        for inp in inputs:
            if inp == output:
                warnings.append(
                    f"In-place overwrite detected: input == output ({inp}). "
                    "ffmpeg will corrupt the input file. Use a different output path."
                )
        if (
            os.environ.get("SAFETY_REQUIRE_CONFIRM_OVERWRITE", "true").lower() == "true"
            and "-y" in args
            and Path(os.path.expanduser(output)).exists()
        ):
            warnings.append(
                f"-y overwrite of existing file: {output}. "
                "Confirm this is intentional (or set SAFETY_REQUIRE_CONFIRM_OVERWRITE=false)."
            )
        ext = Path(output).suffix.lower()
        if ext == ".mp4" and "faststart" not in cmd:
            warnings.append(
                "MP4 output without `-movflags +faststart` — browsers will have to "
                "download the full file before the first frame. Add `-movflags +faststart`."
            )
    if re.search(r"\bhls_", cmd) and "-sc_threshold" not in cmd:
        warnings.append(
            "HLS output without `-sc_threshold 0` — the encoder will insert scene-cut "
            "keyframes that break segment alignment. Add `-sc_threshold 0` and a GOP matching hls_time * fps."
        )
    if any(inp.endswith(".ts") or ":ts:" in inp for inp in inputs) and output and output.endswith(".mp4"):
        if "aac_adtstoasc" not in cmd:
            warnings.append(
                "TS \u2192 MP4 without `-bsf:a aac_adtstoasc` \u2014 MP4 muxer will reject ADTS-framed AAC. "
                "Add `-bsf:a aac_adtstoasc`."
            )
    has_crf = "-crf" in args
    has_bv = any(t in args for t in ("-b:v", "-b"))
    if has_crf and has_bv:
        warnings.append(
            "Both `-crf` AND bitrate (`-b:v`/`-b`) set \u2014 mutually exclusive rate-control modes. "
            "Pick CRF (quality-targeted) OR bitrate-based."
        )
    return warnings


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = payload.get("tool_input", {}).get("command", "")
    warnings = scan(cmd)
    if not warnings:
        return 0
    msg = "Media OS pre-flight found issues with this ffmpeg command:\n\n" + "\n".join(
        f"- {w}" for w in warnings
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": msg,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
