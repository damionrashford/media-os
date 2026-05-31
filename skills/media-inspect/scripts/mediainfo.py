#!/usr/bin/env python3
"""MediaInfo driver: deep container / stream diagnostics beyond ffprobe.

Subcommands:
  check            Print MediaInfo version.
  summary          Human-readable report (`mediainfo <file>`).
  json             Full JSON (`mediainfo --Output=JSON --Full <file>`).
  field            Extract one field via --Inform.
  hdr              Verdict: SDR / HDR10 / HDR10+ / HLG / DolbyVision + details.
  codec-profile    Parse profile + level for every video + audio stream.
  compare          Side-by-side diff of two files on common fields.
  netflix-check    Flag common Netflix UHD HDR10 deliverable spec compliance.

Stdlib only. Non-interactive. Supports --dry-run and --verbose.
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from typing import Any

VERBOSE = False
DRY_RUN = False


def log(msg: str) -> None:
    if VERBOSE:
        print(f"[mediainfo.py] {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def require_mediainfo() -> str:
    path = shutil.which("mediainfo")
    if not path:
        die(
            "mediainfo not found on PATH. Install: brew install mediainfo / apt-get install mediainfo"
        )
    return path  # type: ignore[return-value]


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(shlex.quote(c) for c in cmd))
    if DRY_RUN:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    return subprocess.run(
        cmd,
        check=False,
        capture_output=capture,
        text=True,
    )


def mediainfo_json(input_path: str, full: bool = True) -> dict[str, Any]:
    require_mediainfo()
    cmd = ["mediainfo", "--Output=JSON"]
    if full:
        cmd.append("--Full")
    cmd.append(input_path)
    res = run(cmd)
    if DRY_RUN:
        return {"media": {"track": []}}
    if res.returncode != 0:
        die(f"mediainfo failed: {res.stderr.strip()}")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        die(f"could not parse MediaInfo JSON: {e}")
        return {}


def tracks(
    data: dict[str, Any], stream_type: str | None = None
) -> list[dict[str, Any]]:
    raw = data.get("media", {}).get("track", []) or []
    if stream_type is None:
        return raw
    return [t for t in raw if t.get("@type") == stream_type]


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_check(_args: argparse.Namespace) -> int:
    require_mediainfo()
    res = run(["mediainfo", "--Version"])
    print(res.stdout.strip() or res.stderr.strip())
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    require_mediainfo()
    res = run(["mediainfo", args.input])
    sys.stdout.write(res.stdout)
    return res.returncode


def cmd_json(args: argparse.Namespace) -> int:
    data = mediainfo_json(args.input, full=True)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    require_mediainfo()
    stream = args.stream
    name = args.name
    template = f"{stream};%{name}%"
    res = run(["mediainfo", f"--Inform={template}", args.input])
    out = res.stdout.rstrip("\n")
    if out == "":
        die(
            f"empty result. Check stream type ({stream}) and field name ({name}).",
            code=2,
        )
    print(out)
    return 0


def _hdr_verdict(video: dict[str, Any]) -> dict[str, Any]:
    hdr_format = (video.get("HDR_Format") or video.get("HDR_format") or "").strip()
    hdr_commercial = (video.get("HDR_Format_Commercial") or "").strip()
    transfer = (video.get("transfer_characteristics") or "").strip()
    primaries = (video.get("colour_primaries") or "").strip()
    max_cll = video.get("MaxCLL")
    max_fall = video.get("MaxFALL")
    mastering = video.get("MasteringDisplay_ColorPrimaries")

    blob = f"{hdr_format} {hdr_commercial}".lower()
    verdict = "SDR"
    dv_profile: str | None = None

    if "dolby vision" in blob:
        verdict = "DolbyVision"
        for token in hdr_format.split():
            if (
                token.startswith("dvhe.")
                or token.startswith("dvav.")
                or token.startswith("hev1.")
                or token.startswith("avc1.")
            ):
                continue
        # Profile string lives inside the HDR_Format line: "... Profile 8.1, dvhe.08.06"
        # Pull the first occurrence of "Profile X" loosely.
        parts = hdr_format.split("Profile")
        if len(parts) > 1:
            tail = parts[1].strip().rstrip(",")
            dv_profile = tail.split(",")[0].split()[0] if tail else None
    elif "hdr10+" in blob or "smpte st 2094" in blob or "smpte 2094" in blob:
        verdict = "HDR10+"
    elif "hdr10" in blob or (transfer.upper() in {"PQ", "SMPTE ST 2084"} and mastering):
        verdict = "HDR10"
    elif transfer.upper() in {"HLG", "ARIB STD-B67"}:
        verdict = "HLG"

    return {
        "verdict": verdict,
        "dv_profile": dv_profile,
        "hdr_format": hdr_format or None,
        "transfer": transfer or None,
        "primaries": primaries or None,
        "mastering_display": mastering,
        "max_cll": max_cll,
        "max_fall": max_fall,
    }


def cmd_hdr(args: argparse.Namespace) -> int:
    data = mediainfo_json(args.input)
    vs = tracks(data, "Video")
    if not vs:
        die("no video stream found")
    result = _hdr_verdict(vs[0])
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _parse_profile(fmt_profile: str | None) -> dict[str, str | None]:
    if not fmt_profile:
        return {"profile": None, "level": None, "tier": None}
    # H.264 = "High@L4.1"
    # HEVC  = "Main 10@L5.1@High"
    # AV1   = "Main@L5.1"
    parts = [p.strip() for p in fmt_profile.split("@")]
    profile = parts[0] if parts else None
    level = None
    tier = None
    for p in parts[1:]:
        if p.lower().startswith("l"):
            level = p
        elif p.lower() in {"high", "main"}:
            tier = p
    return {"profile": profile, "level": level, "tier": tier}


def cmd_codec_profile(args: argparse.Namespace) -> int:
    data = mediainfo_json(args.input)
    out: dict[str, Any] = {"video": [], "audio": []}
    for v in tracks(data, "Video"):
        parsed = _parse_profile(v.get("Format_Profile") or v.get("Format profile"))
        out["video"].append(
            {
                "format": v.get("Format"),
                "codec_id": v.get("CodecID"),
                "bit_depth": v.get("BitDepth"),
                **parsed,
                "width": v.get("Width"),
                "height": v.get("Height"),
                "frame_rate": v.get("FrameRate"),
            }
        )
    for a in tracks(data, "Audio"):
        out["audio"].append(
            {
                "format": a.get("Format"),
                "profile": a.get("Format_Profile") or a.get("Format profile"),
                "channels": a.get("Channels"),
                "sampling_rate": a.get("SamplingRate"),
                "bit_rate": a.get("BitRate"),
                "layout": a.get("ChannelLayout"),
            }
        )
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _key_fields(data: dict[str, Any]) -> dict[str, Any]:
    g = (tracks(data, "General") or [{}])[0]
    v = (tracks(data, "Video") or [{}])[0]
    a = (tracks(data, "Audio") or [{}])[0]
    return {
        "container": g.get("Format"),
        "duration_s": g.get("Duration"),
        "overall_bitrate": g.get("OverallBitRate"),
        "file_size": g.get("FileSize"),
        "video_codec": v.get("Format"),
        "video_profile": v.get("Format_Profile") or v.get("Format profile"),
        "width": v.get("Width"),
        "height": v.get("Height"),
        "frame_rate": v.get("FrameRate"),
        "bit_depth": v.get("BitDepth"),
        "color_primaries": v.get("colour_primaries"),
        "transfer": v.get("transfer_characteristics"),
        "hdr_format": v.get("HDR_Format"),
        "audio_codec": a.get("Format"),
        "audio_channels": a.get("Channels"),
        "audio_sampling_rate": a.get("SamplingRate"),
    }


def cmd_compare(args: argparse.Namespace) -> int:
    a_path, b_path = args.inputs
    a = _key_fields(mediainfo_json(a_path))
    b = _key_fields(mediainfo_json(b_path))
    rows: list[dict[str, Any]] = []
    for key in sorted(set(a.keys()) | set(b.keys())):
        va, vb = a.get(key), b.get(key)
        rows.append({"field": key, "a": va, "b": vb, "equal": va == vb})
    json.dump({"a": a_path, "b": b_path, "rows": rows}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_netflix_check(args: argparse.Namespace) -> int:
    """Basic Netflix UHD HDR10 deliverable sanity checks.

    Not the full Netflix IMF spec — a pre-flight aligned with the most common
    rejections: HEVC Main 10 / 10-bit / BT.2020 / PQ / >=3840x2160 / HDR10 metadata.
    """
    data = mediainfo_json(args.input)
    vs = tracks(data, "Video")
    if not vs:
        die("no video stream found")
    v = vs[0]

    codec = (v.get("Format") or "").upper()
    profile = v.get("Format_Profile") or v.get("Format profile") or ""
    bit_depth = int(v.get("BitDepth") or 0)
    width = int(v.get("Width") or 0)
    height = int(v.get("Height") or 0)
    transfer = (v.get("transfer_characteristics") or "").upper()
    primaries = (v.get("colour_primaries") or "").upper()
    bitrate = v.get("BitRate")
    try:
        bitrate_bps = int(bitrate) if bitrate else None
    except (TypeError, ValueError):
        bitrate_bps = None
    bitrate_mbps = round(bitrate_bps / 1_000_000, 2) if bitrate_bps else None

    hdr = _hdr_verdict(v)

    checks = {
        "codec_is_hevc": codec == "HEVC",
        "profile_is_main10": profile.lower().startswith("main 10"),
        "bit_depth_10": bit_depth == 10,
        "resolution_uhd": width >= 3840 and height >= 2160,
        "primaries_bt2020": "2020" in primaries,
        "transfer_pq": transfer in {"PQ", "SMPTE ST 2084"},
        "hdr10_or_dovi": hdr["verdict"] in {"HDR10", "HDR10+", "DolbyVision"},
        "bitrate_ge_16mbps": (bitrate_mbps or 0) >= 16.0,
    }
    result = {
        "pass": all(checks.values()),
        "checks": checks,
        "observed": {
            "codec": codec,
            "profile": profile,
            "bit_depth": bit_depth,
            "resolution": f"{width}x{height}",
            "primaries": primaries,
            "transfer": transfer,
            "hdr": hdr["verdict"],
            "dv_profile": hdr["dv_profile"],
            "bitrate_mbps": bitrate_mbps,
        },
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result["pass"] else 3


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mediainfo.py",
        description="MediaInfo driver for deep container / stream analysis.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print commands but don't run them"
    )
    p.add_argument("--verbose", action="store_true", help="log commands to stderr")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="print MediaInfo version")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("summary", help="human-readable report")
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser("json", help="full JSON output")
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_json)

    sp = sub.add_parser("field", help="extract one field via --Inform")
    sp.add_argument("--input", required=True)
    sp.add_argument(
        "--stream",
        required=True,
        choices=["General", "Video", "Audio", "Text", "Image", "Menu", "Other"],
    )
    sp.add_argument(
        "--name",
        required=True,
        help="MediaInfo field name, e.g. Width, FrameRate, Format profile",
    )
    sp.set_defaults(func=cmd_field)

    sp = sub.add_parser("hdr", help="HDR verdict and details")
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_hdr)

    sp = sub.add_parser(
        "codec-profile", help="parse codec profile/level for each stream"
    )
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_codec_profile)

    sp = sub.add_parser("compare", help="diff two files on common key fields")
    sp.add_argument("--inputs", required=True, nargs=2, metavar=("A", "B"))
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser(
        "netflix-check", help="check basic Netflix UHD HDR10 deliverable spec"
    )
    sp.add_argument("--input", required=True)
    sp.set_defaults(func=cmd_netflix_check)

    return p


def main(argv: list[str] | None = None) -> int:
    global VERBOSE, DRY_RUN
    parser = build_parser()
    args = parser.parse_args(argv)
    VERBOSE = args.verbose
    DRY_RUN = args.dry_run
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
