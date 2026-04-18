#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
mediasoup.py — scaffold + pointer runner for mediasoup projects.

Does NOT install mediasoup itself (npm install happens in the user's
project). Writes starter files and clones the reference demo. Stdlib-only.

Usage:
    mediasoup.py install
    mediasoup.py quickstart DIR
    mediasoup.py demo DIR
    mediasoup.py rtp-bridge --direction in|out --in-port N --out-port N --codec opus|vp8|h264 --out FILE
    mediasoup.py workers
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEMO_REPO = "https://github.com/versatica/mediasoup-demo"


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[mediasoup] {msg}", file=sys.stderr)


def cmd_install(args):
    print("Requirements: Node.js >= 20, Python >= 3.7, C++ toolchain, meson, ninja.")
    print("Install pointer (run inside your project):")
    print("    npm install mediasoup")
    print("Verify native build:")
    print("    ls node_modules/mediasoup/worker/out/Release/mediasoup-worker")
    return 0


PACKAGE_JSON = """\
{
  "name": "mediasoup-quickstart",
  "version": "0.1.0",
  "private": true,
  "main": "server.js",
  "scripts": { "start": "node server.js" },
  "dependencies": { "mediasoup": "^3.14.0" }
}
"""

SERVER_JS = r"""// server.js — minimal single-room mediasoup SFU.
// Bring-your-own signaling. This file exposes the routerRtpCapabilities and
// a createTransport helper; wire the WebSocket transport of your choice.

const mediasoup = require('mediasoup');

async function main() {
  const worker = await mediasoup.createWorker({
    rtcMinPort: 40000,
    rtcMaxPort: 49999,
    logLevel: 'warn',
  });
  worker.on('died', () => {
    console.error('mediasoup worker died');
    process.exit(1);
  });

  const mediaCodecs = [
    { kind: 'audio', mimeType: 'audio/opus', clockRate: 48000, channels: 2 },
    { kind: 'video', mimeType: 'video/VP8', clockRate: 90000,
      parameters: { 'x-google-start-bitrate': 1000 } },
    { kind: 'video', mimeType: 'video/H264', clockRate: 90000,
      parameters: {
        'packetization-mode': 1,
        'profile-level-id': '42e01f',
        'level-asymmetry-allowed': 1,
      } },
  ];

  const router = await worker.createRouter({ mediaCodecs });

  const listenIps = [{ ip: '0.0.0.0', announcedIp: process.env.ANNOUNCED_IP || null }];

  async function createWebRtcTransport() {
    return router.createWebRtcTransport({
      listenIps,
      enableUdp: true,
      enableTcp: true,
      preferUdp: true,
      initialAvailableOutgoingBitrate: 1_000_000,
    });
  }

  console.log('[mediasoup] ready');
  console.log('routerRtpCapabilities:', JSON.stringify(router.rtpCapabilities, null, 2));

  // TODO: wire your signaling layer. Each peer should:
  //   1. GET routerRtpCapabilities
  //   2. POST client dtlsParameters + iceParameters → server.connect
  //   3. POST produce({ kind, rtpParameters }) for each published track
  //   4. POST consume({ producerId, rtpCapabilities }) per consumed track
  //
  // Keep references to transports/producers/consumers keyed by peer id.

  module.exports = { worker, router, createWebRtcTransport };
}

main().catch((e) => { console.error(e); process.exit(1); });
"""


def cmd_quickstart(args):
    dest = Path(args.dir).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} already exists and is non-empty", file=sys.stderr)
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "package.json").write_text(PACKAGE_JSON)
    (dest / "server.js").write_text(SERVER_JS)
    print(f"[mediasoup] scaffolded {dest}")
    print(f"cd {dest} && npm install && node server.js")
    return 0


def cmd_demo(args):
    dest = Path(args.dir).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} already exists and is non-empty", file=sys.stderr)
        return 1
    if shutil.which("git") is None:
        print("error: git not found on PATH", file=sys.stderr)
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(["git", "clone", "--depth=1", DEMO_REPO, str(dest)]).returncode
    if rc != 0:
        return rc
    print(f"[mediasoup] demo cloned to {dest}")
    print(f"follow the README in {dest}/README.md")
    return 0


def cmd_rtp_bridge(args):
    direction = args.direction
    codec = args.codec
    if direction not in ("in", "out"):
        print("error: --direction must be 'in' or 'out'", file=sys.stderr)
        return 2
    payload_type = {"opus": 100, "vp8": 101, "h264": 102}.get(codec)
    if payload_type is None:
        print(f"error: unsupported --codec {codec!r}", file=sys.stderr)
        return 2
    cfg = {
        "direction": direction,
        "transport": "PlainTransport",
        "listenIp": {"ip": "127.0.0.1", "announcedIp": None},
        "rtcpMux": True,
        "comedia": direction == "in",
        "port": args.in_port if direction == "in" else args.out_port,
        "codec": codec,
        "payloadType": payload_type,
        "ssrc": 11111111,
        "ffmpeg_hint": (
            f"ffmpeg -re -i input -c:a libopus -ssrc 11111111 -payload_type 100 "
            f"-f rtp rtp://127.0.0.1:{args.in_port}"
            if direction == "in" and codec == "opus"
            else (
                f"ffmpeg -protocol_whitelist rtp,udp,file -i out.sdp -c copy out.mkv"
                if direction == "out"
                else "see mediasoup PlainTransport docs"
            )
        ),
        "node_hint": (
            "await router.createPlainTransport({ listenIp, rtcpMux:true, comedia:"
            + ("true" if direction == "in" else "false")
            + " })"
        ),
    }
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg, indent=2))
    print(f"[mediasoup] config at {out}", file=sys.stderr)
    return 0


def cmd_workers(args):
    template = {
        "explanation": (
            "Out-of-band introspection is not supported; mediasoup objects "
            "only expose state from inside your Node.js process. Call the "
            "following inside your server and JSON-serialize the output:"
        ),
        "worker.getResourceUsage()": {
            "ru_utime": "user CPU seconds",
            "ru_stime": "kernel CPU seconds",
            "ru_maxrss": "max RSS KB",
        },
        "router.dump()": "full graph of transports/producers/consumers",
        "transport.dump()": "per-transport ICE / DTLS / SCTP state",
        "producer.getStats()": "per-producer RTP stats",
        "consumer.getStats()": "per-consumer RTP stats",
        "observer_api": {
            "on('newtransport')": "emitted when a new Transport is created",
            "on('newproducer')": "emitted when a new Producer is created",
        },
    }
    print(json.dumps(template, indent=2))
    return 0


def build_parser():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    p = argparse.ArgumentParser(
        description="mediasoup scaffold + pointer runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[parent],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser(
        "install", help="print the canonical npm install pointer", parents=[parent]
    )
    s.set_defaults(fn=cmd_install)

    s = sub.add_parser(
        "quickstart", help="scaffold a minimal Node.js server", parents=[parent]
    )
    s.add_argument("dir")
    s.set_defaults(fn=cmd_quickstart)

    s = sub.add_parser(
        "demo", help="git clone versatica/mediasoup-demo", parents=[parent]
    )
    s.add_argument("dir")
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser(
        "rtp-bridge", help="write a PlainTransport bridge config", parents=[parent]
    )
    s.add_argument("--direction", required=True, choices=["in", "out"])
    s.add_argument("--in-port", type=int, default=5004)
    s.add_argument("--out-port", type=int, default=5006)
    s.add_argument("--codec", default="opus", choices=["opus", "vp8", "h264"])
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_rtp_bridge)

    s = sub.add_parser(
        "workers",
        help="print the workers/routers introspection template",
        parents=[parent],
    )
    s.set_defaults(fn=cmd_workers)

    return p


def main():
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
