#!/usr/bin/env python3
"""ffmpeg streaming helper.

Subcommands:
    rtmp           Push a file or live source to an RTMP ingest (YouTube, Twitch, ...).
    hls-vod        Package to HLS VOD (.m3u8 + .ts segments, fixed playlist).
    hls-live       Package to HLS live with a sliding window.
    hls-abr        Build an ABR ladder with a master playlist.
    dash           Package to MPEG-DASH (.mpd + .m4s).
    srt-listener   Start an SRT listener and serve a source.
    srt-caller     Push to an SRT receiver (caller mode).
    tee            Fan out one encode to multiple sinks via the tee muxer.

Stdlib only. Prints the ffmpeg command before running. Supports --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from typing import List, Sequence


# ---------- helpers ---------------------------------------------------------


def _print_cmd(cmd: Sequence[str]) -> None:
    """Print the exact ffmpeg command, shell-quoted so users can copy/paste."""
    quoted = " ".join(shlex.quote(c) for c in cmd)
    print(f"+ {quoted}", file=sys.stderr)


def _run(cmd: Sequence[str], dry_run: bool) -> int:
    _print_cmd(cmd)
    if dry_run:
        return 0
    try:
        return subprocess.call(list(cmd))
    except FileNotFoundError:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        return 127


def _parse_duration_seconds(s: str) -> int:
    """Accept '6', '6s', '2000ms' -> seconds (int)."""
    s = s.strip().lower()
    if s.endswith("ms"):
        return max(1, int(int(s[:-2]) / 1000))
    if s.endswith("s"):
        return int(s[:-1])
    return int(s)


def _common_live_video_flags(bitrate: str, preset: str, gop: int) -> List[str]:
    return [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-tune",
        "zerolatency",
        "-b:v",
        bitrate,
        "-maxrate",
        bitrate,
        "-bufsize",
        _twice(bitrate),
        "-pix_fmt",
        "yuv420p",
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
    ]


def _common_live_audio_flags() -> List[str]:
    return ["-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]


def _twice(bitrate: str) -> str:
    """2500k -> 5000k. Accepts k/M suffix; falls back to itself."""
    m = re.match(r"^(\d+)([kKmM]?)$", bitrate.strip())
    if not m:
        return bitrate
    n = int(m.group(1)) * 2
    return f"{n}{m.group(2).lower() if m.group(2) else ''}"


def _parse_ladder(spec: str):
    """'1080p=5000k 720p=2800k 480p=1400k' -> [(1920,1080,5000k), ...]."""
    presets = {
        "2160p": (3840, 2160),
        "1440p": (2560, 1440),
        "1080p": (1920, 1080),
        "720p": (1280, 720),
        "480p": (854, 480),
        "360p": (640, 360),
        "240p": (426, 240),
    }
    out = []
    for token in spec.split():
        name, _, br = token.partition("=")
        if name not in presets or not br:
            raise ValueError(f"bad ladder token: {token!r} (use e.g. 720p=2500k)")
        w, h = presets[name]
        out.append((w, h, br))
    if not out:
        raise ValueError("empty ladder")
    return out


# ---------- subcommand builders --------------------------------------------


def cmd_rtmp(a: argparse.Namespace) -> int:
    gop = a.fps * a.keyint_secs
    cmd = ["ffmpeg", "-hide_banner"]
    if a.re:
        cmd += ["-re"]
    cmd += ["-i", a.input]
    cmd += _common_live_video_flags(a.bitrate, a.preset, gop)
    cmd += _common_live_audio_flags()
    cmd += ["-f", "flv", a.url]
    return _run(cmd, a.dry_run)


def cmd_hls_vod(a: argparse.Namespace) -> int:
    os.makedirs(a.outdir, exist_ok=True)
    seg = _parse_duration_seconds(a.segments)
    gop = a.fps * seg
    out_m3u8 = os.path.join(a.outdir, a.name)
    seg_name = os.path.join(a.outdir, "seg_%03d.ts")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        a.input,
        "-c:v",
        "libx264",
        "-preset",
        a.preset,
        "-b:v",
        a.bitrate,
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "hls",
        "-hls_time",
        str(seg),
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        seg_name,
        out_m3u8,
    ]
    return _run(cmd, a.dry_run)


def cmd_hls_live(a: argparse.Namespace) -> int:
    os.makedirs(a.outdir, exist_ok=True)
    seg = _parse_duration_seconds(a.segment_time)
    gop = a.fps * seg
    out_m3u8 = os.path.join(a.outdir, a.name)
    seg_name = os.path.join(a.outdir, "seg_%05d.ts")
    cmd = ["ffmpeg", "-hide_banner"]
    if a.re:
        cmd += ["-re"]
    cmd += ["-i", a.input]
    cmd += _common_live_video_flags(a.bitrate, a.preset, gop)
    cmd += _common_live_audio_flags()
    cmd += [
        "-f",
        "hls",
        "-hls_time",
        str(seg),
        "-hls_list_size",
        str(a.window),
        "-hls_flags",
        "delete_segments+append_list",
        "-hls_segment_filename",
        seg_name,
        out_m3u8,
    ]
    return _run(cmd, a.dry_run)


def cmd_hls_abr(a: argparse.Namespace) -> int:
    os.makedirs(a.outdir, exist_ok=True)
    ladder = _parse_ladder(a.ladder)
    seg = _parse_duration_seconds(a.segment_time)
    gop = a.fps * seg

    # Build filter_complex
    n = len(ladder)
    split = f"[0:v]split={n}" + "".join(f"[v{i}]" for i in range(n))
    scales = ";".join(
        f"[v{i}]scale=w={w}:h={h}[v{i}out]" for i, (w, h, _) in enumerate(ladder)
    )
    fc = f"{split};{scales}"

    cmd = ["ffmpeg", "-hide_banner", "-i", a.input, "-filter_complex", fc]

    for i, (_, _, br) in enumerate(ladder):
        cmd += [
            "-map",
            f"[v{i}out]",
            f"-c:v:{i}",
            "libx264",
            f"-b:v:{i}",
            br,
            f"-maxrate:v:{i}",
            br,
            f"-bufsize:v:{i}",
            _twice(br),
        ]
    # Audio: one track replicated per rendition
    for _ in ladder:
        cmd += ["-map", "a:0?"]

    cmd += [
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-preset",
        a.preset,
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-f",
        "hls",
        "-hls_time",
        str(seg),
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        os.path.join(a.outdir, "stream_%v", "seg_%03d.ts"),
        "-master_pl_name",
        a.master,
        "-var_stream_map",
        " ".join(f"v:{i},a:{i}" for i in range(n)),
        os.path.join(a.outdir, "stream_%v", "index.m3u8"),
    ]
    # Need the variant subdirs to exist
    for i in range(n):
        os.makedirs(os.path.join(a.outdir, f"stream_{i}"), exist_ok=True)
    return _run(cmd, a.dry_run)


def cmd_dash(a: argparse.Namespace) -> int:
    os.makedirs(a.outdir, exist_ok=True)
    seg = _parse_duration_seconds(a.segment_time)
    gop = a.fps * seg
    out_mpd = os.path.join(a.outdir, a.name)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        a.input,
        "-c:v",
        "libx264",
        "-preset",
        a.preset,
        "-b:v",
        a.bitrate,
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "dash",
        "-seg_duration",
        str(seg),
        "-use_template",
        "1",
        "-use_timeline",
        "1",
        "-init_seg_name",
        "init-$RepresentationID$.m4s",
        "-media_seg_name",
        "chunk-$RepresentationID$-$Number%05d$.m4s",
        out_mpd,
    ]
    return _run(cmd, a.dry_run)


def cmd_srt_listener(a: argparse.Namespace) -> int:
    url = f"srt://0.0.0.0:{a.port}?mode=listener&latency={a.latency}"
    if a.passphrase:
        url += f"&passphrase={a.passphrase}&pbkeylen={a.pbkeylen}"
    cmd = ["ffmpeg", "-hide_banner"]
    if a.re:
        cmd += ["-re"]
    cmd += ["-i", a.input, "-c", "copy", "-f", "mpegts", url]
    return _run(cmd, a.dry_run)


def cmd_srt_caller(a: argparse.Namespace) -> int:
    cmd = ["ffmpeg", "-hide_banner"]
    if a.re:
        cmd += ["-re"]
    cmd += ["-i", a.input, "-c", "copy", "-f", "mpegts", a.url]
    return _run(cmd, a.dry_run)


def cmd_tee(a: argparse.Namespace) -> int:
    gop = a.fps * a.keyint_secs
    cmd = ["ffmpeg", "-hide_banner"]
    if a.re:
        cmd += ["-re"]
    cmd += ["-i", a.input]
    cmd += _common_live_video_flags(a.bitrate, a.preset, gop)
    cmd += _common_live_audio_flags()
    cmd += ["-map", "0:v", "-map", "0:a", "-f", "tee", a.outputs]
    return _run(cmd, a.dry_run)


# ---------- argparse --------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stream.py",
        description="ffmpeg streaming helper (HLS, DASH, RTMP, SRT, tee).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the ffmpeg command but do not execute it",
    )
    p.add_argument(
        "--verbose", action="store_true", help="echo Python-level debug info"
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    # rtmp
    r = sub.add_parser("rtmp", help="push to an RTMP ingest")
    r.add_argument("--input", "-i", required=True)
    r.add_argument("--url", required=True, help="rtmp://… destination URL")
    r.add_argument("--bitrate", default="6000k")
    r.add_argument("--preset", default="veryfast")
    r.add_argument("--fps", type=int, default=30)
    r.add_argument("--keyint-secs", type=int, default=2)
    r.add_argument(
        "--re",
        action="store_true",
        help="add -re (real-time read; for files, not live encoders)",
    )
    r.set_defaults(func=cmd_rtmp)

    # hls-vod
    hv = sub.add_parser("hls-vod", help="HLS VOD packaging")
    hv.add_argument("--input", "-i", required=True)
    hv.add_argument("--outdir", required=True)
    hv.add_argument("--name", default="index.m3u8")
    hv.add_argument(
        "--segments", default="6s", help='segment duration, e.g. "6" or "6s"'
    )
    hv.add_argument("--bitrate", default="2500k")
    hv.add_argument("--preset", default="medium")
    hv.add_argument("--fps", type=int, default=30)
    hv.set_defaults(func=cmd_hls_vod)

    # hls-live
    hl = sub.add_parser("hls-live", help="HLS live (sliding window)")
    hl.add_argument("--input", "-i", required=True)
    hl.add_argument("--outdir", required=True)
    hl.add_argument("--name", default="index.m3u8")
    hl.add_argument("--segment-time", default="4s")
    hl.add_argument(
        "--window",
        type=int,
        default=6,
        help="-hls_list_size (number of segments in the window)",
    )
    hl.add_argument("--bitrate", default="3000k")
    hl.add_argument("--preset", default="veryfast")
    hl.add_argument("--fps", type=int, default=30)
    hl.add_argument("--re", action="store_true")
    hl.set_defaults(func=cmd_hls_live)

    # hls-abr
    ha = sub.add_parser("hls-abr", help="HLS ABR ladder with master playlist")
    ha.add_argument("--input", "-i", required=True)
    ha.add_argument("--outdir", required=True)
    ha.add_argument(
        "--ladder",
        default="1080p=5000k 720p=2800k 480p=1400k",
        help='space-separated "PRESET=BITRATE" tokens',
    )
    ha.add_argument("--segment-time", default="4s")
    ha.add_argument("--master", default="master.m3u8")
    ha.add_argument("--preset", default="veryfast")
    ha.add_argument("--fps", type=int, default=30)
    ha.set_defaults(func=cmd_hls_abr)

    # dash
    d = sub.add_parser("dash", help="MPEG-DASH packaging")
    d.add_argument("--input", "-i", required=True)
    d.add_argument("--outdir", required=True)
    d.add_argument("--name", default="manifest.mpd")
    d.add_argument("--segment-time", default="4s")
    d.add_argument("--bitrate", default="2500k")
    d.add_argument("--preset", default="medium")
    d.add_argument("--fps", type=int, default=30)
    d.set_defaults(func=cmd_dash)

    # srt-listener
    sl = sub.add_parser("srt-listener", help="serve via SRT in listener mode")
    sl.add_argument("--input", "-i", required=True)
    sl.add_argument("--port", type=int, default=9000)
    sl.add_argument(
        "--latency",
        type=int,
        default=120000,
        help="SRT latency in microseconds (120000 = 120 ms)",
    )
    sl.add_argument("--passphrase", default=None)
    sl.add_argument("--pbkeylen", type=int, default=16, choices=(16, 24, 32))
    sl.add_argument("--re", action="store_true", default=True)
    sl.set_defaults(func=cmd_srt_listener)

    # srt-caller
    sc = sub.add_parser("srt-caller", help="push via SRT in caller mode")
    sc.add_argument("--input", "-i", required=True)
    sc.add_argument(
        "--url",
        required=True,
        help="srt://host:port?mode=caller&latency=120000[&passphrase=…&pbkeylen=16]",
    )
    sc.add_argument("--re", action="store_true", default=True)
    sc.set_defaults(func=cmd_srt_caller)

    # tee
    t = sub.add_parser("tee", help="fan out one encode to multiple sinks")
    t.add_argument("--input", "-i", required=True)
    t.add_argument(
        "--outputs",
        required=True,
        help="tee spec, e.g. '[f=flv]rtmp://…|[f=hls:hls_time=4]out.m3u8'",
    )
    t.add_argument("--bitrate", default="4500k")
    t.add_argument("--preset", default="veryfast")
    t.add_argument("--fps", type=int, default=30)
    t.add_argument("--keyint-secs", type=int, default=2)
    t.add_argument("--re", action="store_true")
    t.set_defaults(func=cmd_tee)

    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verbose:
        print(f"[stream.py] subcommand={args.cmd} args={vars(args)}", file=sys.stderr)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
