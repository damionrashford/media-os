#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
livekit.py — LiveKit install + JWT mint + CLI wrapper.

Stdlib only. JWT HS256 signed with hmac+hashlib+base64+json — no pyjwt.

Usage:
    livekit.py install-server --dest DIR
    livekit.py install-cli --dest DIR
    livekit.py start [--config FILE] [--dev]
    livekit.py mint-token --api-key K --api-secret S --room R --identity I
                          [--name N] [--ttl 3600]
                          [--grants roomJoin=true,canPublish=true,...]
    livekit.py room-list [--url URL] [--api-key K] [--api-secret S]
    livekit.py room-join --room R --identity I [--url ...] [--api-key ...]
    livekit.py load-test --config FILE
    livekit.py egress-start --url URL --api-key K --api-secret S --room R
                            --type room-composite|track-composite|track|web|participant
                            --output mp4|hls|rtmp --dest DEST [--layout grid]
    livekit.py ingress-start --url URL --api-key K --api-secret S --room R
                             --type rtmp|whip|srt|url --identity I [--name N]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

SERVER_RELEASES = "https://api.github.com/repos/livekit/livekit/releases/latest"
CLI_RELEASES = "https://api.github.com/repos/livekit/livekit-cli/releases/latest"
UA = "livekit-skill/1.0 (Claude Code Agent Skill)"


# ---------------------------------------------------------------------------
# JWT (HS256)
# ---------------------------------------------------------------------------


def _b64url_no_pad(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt_hs256(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    enc_header = _b64url_no_pad(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
    )
    enc_payload = _b64url_no_pad(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signing_input = f"{enc_header}.{enc_payload}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{enc_header}.{enc_payload}.{_b64url_no_pad(sig)}"


GRANT_BOOL_KEYS = {
    "roomCreate",
    "roomList",
    "roomRecord",
    "roomAdmin",
    "roomJoin",
    "canPublish",
    "canSubscribe",
    "canPublishData",
    "canUpdateOwnMetadata",
    "ingressAdmin",
    "hidden",
    "recorder",
    "agent",
}


def _parse_grants(s: str) -> dict:
    out: dict = {}
    if not s:
        return out
    for kv in s.split(","):
        kv = kv.strip()
        if not kv:
            continue
        if "=" not in kv:
            raise ValueError(f"bad grant {kv!r} (expected key=value)")
        k, v = kv.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k in GRANT_BOOL_KEYS:
            out[k] = v.lower() in ("1", "true", "yes")
        else:
            out[k] = v
    return out


def cmd_mint_token(args):
    now = int(time.time())
    video = {"room": args.room}
    video.update(_parse_grants(args.grants))
    if "roomJoin" not in video:
        video["roomJoin"] = True
    payload = {
        "iss": args.api_key,
        "sub": args.identity,
        "nbf": now,
        "iat": now,
        "exp": now + int(args.ttl),
        "video": video,
    }
    if args.name:
        payload["name"] = args.name
    if args.metadata:
        payload["metadata"] = args.metadata
    token = jwt_hs256(payload, args.api_secret)
    print(token)
    return 0


# ---------------------------------------------------------------------------
# Binary installer
# ---------------------------------------------------------------------------


def _detect_platform() -> tuple[str, str]:
    system = platform.system().lower()  # darwin / linux
    mach = platform.machine().lower()  # x86_64, arm64, aarch64
    if system == "darwin":
        arch = "arm64" if mach in ("arm64", "aarch64") else "amd64"
        return "darwin", arch
    if system == "linux":
        arch = "arm64" if mach in ("aarch64", "arm64") else "amd64"
        return "linux", arch
    raise RuntimeError(f"unsupported platform: {system} {mach}")


def _http_json(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _pick_asset(release: dict, binary_prefix: str, os_name: str, arch: str) -> str:
    wanted_os = {"darwin": "darwin", "linux": "linux"}[os_name]
    for asset in release["assets"]:
        name = asset["name"].lower()
        if binary_prefix not in name:
            continue
        if wanted_os not in name:
            continue
        if arch not in name:
            continue
        if name.endswith((".tar.gz", ".tgz", ".zip")):
            return asset["browser_download_url"]
    raise RuntimeError(f"no matching asset for {binary_prefix} {os_name}/{arch}")


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def _extract_into(data: bytes, dest: Path, want_binary: str) -> Path:
    if data[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(data))
        for info in zf.infolist():
            if info.filename.endswith(want_binary) or info.filename.endswith(
                f"{want_binary}.exe"
            ):
                target = dest / Path(info.filename).name
                with zf.open(info) as src, open(target, "wb") as out:
                    out.write(src.read())
                os.chmod(target, 0o755)
                return target
    else:
        tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")
        for m in tf.getmembers():
            if m.isfile() and (
                m.name.endswith(want_binary) or m.name.endswith(f"{want_binary}.exe")
            ):
                target = dest / Path(m.name).name
                with tf.extractfile(m) as src, open(target, "wb") as out:
                    out.write(src.read())
                os.chmod(target, 0o755)
                return target
    raise RuntimeError(f"binary {want_binary!r} not found in archive")


def cmd_install_server(args):
    os_name, arch = _detect_platform()
    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    rel = _http_json(SERVER_RELEASES)
    url = _pick_asset(rel, "livekit", os_name, arch)
    print(f"[livekit] downloading {url}")
    path = _extract_into(_download(url), dest, "livekit-server")
    print(f"[livekit] installed {path}")
    return 0


def cmd_install_cli(args):
    os_name, arch = _detect_platform()
    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    rel = _http_json(CLI_RELEASES)
    url = _pick_asset(rel, "livekit-cli", os_name, arch)
    print(f"[livekit] downloading {url}")
    path = _extract_into(_download(url), dest, "lk")
    # Also symlink "livekit-cli" for compat if the release uses "lk".
    alias = dest / "livekit-cli"
    if not alias.exists():
        try:
            alias.symlink_to(path.name)
        except Exception:  # noqa: BLE001
            pass
    print(f"[livekit] installed {path}")
    return 0


# ---------------------------------------------------------------------------
# Server + CLI passthrough
# ---------------------------------------------------------------------------


def _run(cmd: list[str]) -> int:
    print(f"[livekit] {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd).returncode


def _ensure(binary: str) -> str:
    p = shutil.which(binary)
    if p is None:
        raise RuntimeError(
            f"{binary!r} not found on PATH; run install-server / install-cli"
        )
    return p


def cmd_start(args):
    binary = _ensure("livekit-server")
    if args.dev:
        return _run([binary, "--dev"])
    if not args.config:
        print(
            "error: --config FILE required (or pass --dev for a dev server)",
            file=sys.stderr,
        )
        return 2
    return _run([binary, "--config", args.config])


def _lk_args(args):
    base = [_ensure("lk")]
    if args.url:
        base += ["--url", args.url]
    if args.api_key:
        base += ["--api-key", args.api_key]
    if args.api_secret:
        base += ["--api-secret", args.api_secret]
    return base


def cmd_room_list(args):
    return _run(_lk_args(args) + ["room", "list"])


def cmd_room_join(args):
    return _run(
        _lk_args(args) + ["room", "join", "--identity", args.identity, args.room]
    )


def cmd_load_test(args):
    return _run(_lk_args(args) + ["load-test", "--config", args.config])


def cmd_egress_start(args):
    # The egress gRPC API is what `lk` wraps; emit the equivalent pointer command.
    cmd = _lk_args(args) + [
        "egress",
        "start",
        "--type",
        args.type,
        "--output",
        args.output,
        "--dest",
        args.dest,
        "--room",
        args.room,
    ]
    if args.layout:
        cmd += ["--layout", args.layout]
    return _run(cmd)


def cmd_ingress_start(args):
    cmd = _lk_args(args) + [
        "ingress",
        "create",
        "--input-type",
        args.type,
        "--room-name",
        args.room,
        "--participant-identity",
        args.identity,
    ]
    if args.name:
        cmd += ["--participant-name", args.name]
    return _run(cmd)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    p = argparse.ArgumentParser(
        description="LiveKit install + JWT mint + CLI wrapper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[parent],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser(
        "install-server", help="download livekit-server binary", parents=[parent]
    )
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_install_server)

    s = sub.add_parser(
        "install-cli", help="download lk (livekit-cli) binary", parents=[parent]
    )
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_install_cli)

    s = sub.add_parser(
        "start", help="run livekit-server (--dev or --config)", parents=[parent]
    )
    s.add_argument("--config")
    s.add_argument("--dev", action="store_true")
    s.set_defaults(fn=cmd_start)

    s = sub.add_parser(
        "mint-token", help="mint an HS256 JWT with grants", parents=[parent]
    )
    s.add_argument("--api-key", required=True)
    s.add_argument("--api-secret", required=True)
    s.add_argument("--room", required=True)
    s.add_argument("--identity", required=True)
    s.add_argument("--name")
    s.add_argument("--metadata")
    s.add_argument("--ttl", default="3600", help="seconds until exp (default 3600)")
    s.add_argument(
        "--grants",
        default="roomJoin=true,canPublish=true,canSubscribe=true",
        help="comma-separated key=value list (booleans + strings)",
    )
    s.set_defaults(fn=cmd_mint_token)

    def _add_lk_common(sp):
        sp.add_argument("--url")
        sp.add_argument("--api-key")
        sp.add_argument("--api-secret")

    s = sub.add_parser("room-list", help="lk room list", parents=[parent])
    _add_lk_common(s)
    s.set_defaults(fn=cmd_room_list)

    s = sub.add_parser("room-join", help="lk room join", parents=[parent])
    _add_lk_common(s)
    s.add_argument("--room", required=True)
    s.add_argument("--identity", required=True)
    s.set_defaults(fn=cmd_room_join)

    s = sub.add_parser("load-test", help="lk load-test", parents=[parent])
    _add_lk_common(s)
    s.add_argument("--config", required=True)
    s.set_defaults(fn=cmd_load_test)

    s = sub.add_parser("egress-start", help="lk egress start", parents=[parent])
    _add_lk_common(s)
    s.add_argument("--room", required=True)
    s.add_argument(
        "--type",
        required=True,
        choices=["room-composite", "track-composite", "track", "web", "participant"],
    )
    s.add_argument("--output", required=True, choices=["mp4", "hls", "rtmp"])
    s.add_argument("--dest", required=True)
    s.add_argument("--layout", default="grid")
    s.set_defaults(fn=cmd_egress_start)

    s = sub.add_parser("ingress-start", help="lk ingress create", parents=[parent])
    _add_lk_common(s)
    s.add_argument("--room", required=True)
    s.add_argument("--type", required=True, choices=["rtmp", "whip", "srt", "url"])
    s.add_argument("--identity", required=True)
    s.add_argument("--name")
    s.set_defaults(fn=cmd_ingress_start)

    return p


def main():
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
