#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""mtxctl.py -- Manage a MediaMTX (bluenviron/mediamtx) server.

Stdlib only. Non-interactive. Echoes every HTTP request + shell command to
stderr before executing; honours --dry-run everywhere.

Subcommands:
    install       Download the latest MediaMTX release binary to a local dir.
    init-config   Write a good starter mediamtx.yml to a chosen path.
    start         Launch mediamtx as a background process (PID tracked via a pidfile).
    stop          Signal the tracked process.
    reload        Send SIGHUP for hot-reload of the config file.
    api           Generic /v3/* caller (GET/POST/DELETE with JSON body).
    paths-list    GET /v3/paths/list with pretty JSON output.
    sessions-list Aggregate /v3/*sessions + /v3/*conns endpoints.
    recordings-list GET /v3/recordings/list.
    mint-jwt      Create an HMAC-signed JWT for the JWT auth backend.

Environment:
    MEDIAMTX_API   Base URL for the control API (default http://127.0.0.1:9997).
    MEDIAMTX_BIN   Path to the mediamtx binary (default: MediaMTX-bin/mediamtx).
    MEDIAMTX_PID   Pidfile path (default: /tmp/mediamtx.pid).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlencode

UA = "mediamtx-server-skill/1.0 (Claude Code Agent Skill)"
DEFAULT_API = os.environ.get("MEDIAMTX_API", "http://127.0.0.1:9997")
DEFAULT_BIN = Path(os.environ.get("MEDIAMTX_BIN", "MediaMTX-bin/mediamtx"))
DEFAULT_PID = Path(os.environ.get("MEDIAMTX_PID", "/tmp/mediamtx.pid"))
RELEASES_API = "https://api.github.com/repos/bluenviron/mediamtx/releases/latest"

STARTER_CONFIG = """\
# mediamtx.yml -- starter config for a small production deployment.
# Full reference: https://mediamtx.org/docs/references/configuration-file
# Upstream defaults: https://raw.githubusercontent.com/bluenviron/mediamtx/main/mediamtx.yml

# ── Global log settings ─────────────────────────────────────────────────────
logLevel: info
logDestinations: [stdout]
logFile: mediamtx.log

# ── API + metrics + pprof ──────────────────────────────────────────────────
api: yes
apiAddress: :9997

metrics: yes
metricsAddress: :9998

pprof: no

# ── Playback (read back recorded segments) ─────────────────────────────────
playback: yes
playbackAddress: :9996

# ── Protocol listeners ─────────────────────────────────────────────────────
rtsp: yes
rtspAddress: :8554
rtspTransports: [udp, multicast, tcp]
rtspAuthMethods: [basic]

rtmp: yes
rtmpAddress: :1935

hls: yes
hlsAddress: :8888
hlsAllowOrigin: "*"
hlsVariant: lowLatency     # lowLatency | mpegts | fmp4
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms

webrtc: yes
webrtcAddress: :8889
webrtcAllowOrigin: "*"
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302

srt: yes
srtAddress: :8890

# ── Authentication ─────────────────────────────────────────────────────────
# Swap to `http` or `jwt` for production. See docs/features/authentication.
authMethod: internal
authInternalUsers:
  - user: any
    pass:
    ips: []
    permissions:
      - action: publish
      - action: read
      - action: playback
  - user: admin
    pass: CHANGE_ME_ADMIN_PASSWORD
    ips: []
    permissions:
      - action: api
      - action: metrics
      - action: pprof

# ── Paths ──────────────────────────────────────────────────────────────────
# `all_others` catches every path not explicitly declared above.
pathDefaults:
  # Start `source:` only when a reader appears; keep alive for 10s after last reader.
  sourceOnDemand: no
  sourceOnDemandStartTimeout: 10s
  sourceOnDemandCloseAfter: 10s

  # Recording (disabled by default). Set record: yes per-path to turn on.
  record: no
  recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S-%f
  recordFormat: fmp4
  recordPartDuration: 1s
  recordSegmentDuration: 1h
  recordDeleteAfter: 24h

paths:
  # An on-demand path that re-publishes an upstream RTSP camera, only when
  # someone asks for it. Overwrite or remove.
  # camera1:
  #   source: rtsp://user:pass@10.0.0.42:554/Streaming/Channels/101
  #   sourceOnDemand: yes

  # Catch-all: any `publish` target becomes its own path automatically.
  all_others:
"""


def echo(cmd: str) -> None:
    print(f"+ {cmd}", file=sys.stderr)


# ── install ─────────────────────────────────────────────────────────────────


def _detect_asset_suffix() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        return f"darwin_{arch}.tar.gz"
    if system == "linux":
        if machine in ("x86_64", "amd64"):
            arch = "amd64"
        elif machine in ("aarch64", "arm64"):
            arch = "arm64v8"
        elif machine.startswith("armv7"):
            arch = "armv7"
        elif machine.startswith("armv6"):
            arch = "armv6"
        else:
            arch = "amd64"
        return f"linux_{arch}.tar.gz"
    if system == "windows":
        return "windows_amd64.zip"
    raise SystemExit(f"unsupported platform: {system}/{machine}")


def cmd_install(args: argparse.Namespace) -> int:
    dest = Path(args.dir).resolve()
    echo(f"mkdir -p {dest}")
    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    echo(f"GET {RELEASES_API}")
    if args.dry_run:
        print(
            f"[dry-run] would fetch release info + asset into {dest}", file=sys.stderr
        )
        return 0

    req = urllib.request.Request(RELEASES_API, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        info = json.load(r)
    tag = info.get("tag_name") or info.get("name") or "latest"
    suffix = _detect_asset_suffix()
    asset = next(
        (a for a in info.get("assets", []) if a.get("name", "").endswith(suffix)),
        None,
    )
    if not asset:
        print(
            f"error: no asset matching suffix {suffix!r} in release {tag}",
            file=sys.stderr,
        )
        return 1
    url = asset["browser_download_url"]
    name = asset["name"]
    archive = dest / name
    echo(f"curl -L -o {archive} {url}")
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300
    ) as r:
        archive.write_bytes(r.read())

    echo(f"extract {archive} -> {dest}")
    if name.endswith(".tar.gz"):
        with tarfile.open(archive) as tf:
            tf.extractall(dest)
    elif name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)

    # Make binary executable on POSIX.
    for candidate in (dest / "mediamtx", dest / "mediamtx.exe"):
        if candidate.exists():
            if sys.platform != "win32":
                candidate.chmod(0o755)
            print(f"installed: {candidate}  (release {tag})", file=sys.stderr)
            return 0
    print("warning: no mediamtx binary found after extraction", file=sys.stderr)
    return 1


# ── init-config ─────────────────────────────────────────────────────────────


def cmd_init_config(args: argparse.Namespace) -> int:
    target = Path(args.output).resolve()
    echo(f"write starter mediamtx.yml -> {target}")
    if target.exists() and not args.force:
        print(f"error: {target} exists (use --force to overwrite)", file=sys.stderr)
        return 1
    if args.dry_run:
        print(
            f"[dry-run] would write {len(STARTER_CONFIG)} bytes to {target}",
            file=sys.stderr,
        )
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STARTER_CONFIG, encoding="utf-8")
    return 0


# ── start / stop / reload ───────────────────────────────────────────────────


def _resolve_bin(bin_arg: str | None) -> Path:
    if bin_arg:
        p = Path(bin_arg).resolve()
    else:
        p = DEFAULT_BIN.resolve()
    if not p.exists():
        alt = shutil.which("mediamtx")
        if alt:
            return Path(alt)
        raise SystemExit(
            f"mediamtx binary not found at {p}. Run `install` first "
            f"or export MEDIAMTX_BIN or pass --bin."
        )
    return p


def cmd_start(args: argparse.Namespace) -> int:
    binp = _resolve_bin(args.bin)
    cfg = Path(args.config).resolve() if args.config else None
    pid_file = Path(args.pidfile).resolve() if args.pidfile else DEFAULT_PID
    log_file = Path(args.log).resolve() if args.log else Path("mediamtx.log").resolve()
    cmd = [str(binp)]
    if cfg:
        cmd.append(str(cfg))

    echo(" ".join(shlex.quote(c) for c in cmd) + f"  > {log_file}  2>&1 &")
    if args.dry_run:
        return 0

    # Refuse to start a second instance by accident.
    if pid_file.exists():
        try:
            existing = int(pid_file.read_text().strip())
            os.kill(existing, 0)
            print(
                f"mediamtx already running at pid {existing} (pidfile {pid_file})",
                file=sys.stderr,
            )
            return 1
        except (ValueError, ProcessLookupError, PermissionError):
            pid_file.unlink(missing_ok=True)

    log_fh = open(log_file, "ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=log_fh,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    pid_file.write_text(str(proc.pid))
    print(
        f"started pid {proc.pid} (pidfile {pid_file}, log {log_file})", file=sys.stderr
    )
    return 0


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except ValueError:
        return None


def cmd_stop(args: argparse.Namespace) -> int:
    pid_file = Path(args.pidfile).resolve() if args.pidfile else DEFAULT_PID
    pid = _read_pid(pid_file)
    if pid is None:
        print(f"no pidfile at {pid_file}", file=sys.stderr)
        return 1
    sig = signal.SIGTERM
    if args.kill:
        sig = signal.SIGKILL
    echo(f"kill -{sig} {pid}")
    if args.dry_run:
        return 0
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        print(f"pid {pid} not running; cleaning pidfile", file=sys.stderr)
        pid_file.unlink(missing_ok=True)
        return 0
    # Wait briefly for exit.
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pid_file.unlink(missing_ok=True)
            print(f"stopped pid {pid}", file=sys.stderr)
            return 0
        time.sleep(0.1)
    print(f"pid {pid} still alive after SIGTERM; re-run with --kill", file=sys.stderr)
    return 2


def cmd_reload(args: argparse.Namespace) -> int:
    pid_file = Path(args.pidfile).resolve() if args.pidfile else DEFAULT_PID
    pid = _read_pid(pid_file)
    if pid is None:
        print(f"no pidfile at {pid_file}", file=sys.stderr)
        return 1
    echo(f"kill -HUP {pid}")
    if args.dry_run:
        return 0
    try:
        os.kill(pid, signal.SIGHUP)
    except ProcessLookupError:
        print(f"pid {pid} not running", file=sys.stderr)
        return 1
    print(f"sent SIGHUP to pid {pid}", file=sys.stderr)
    return 0


# ── Control API ─────────────────────────────────────────────────────────────


def _api_call(
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    params: dict | None = None,
    auth: tuple[str, str] | None = None,
    timeout: float = 10.0,
    verbose: bool = False,
    dry_run: bool = False,
) -> tuple[int, dict | None, bytes]:
    if not path.startswith("/"):
        path = "/" + path
    url = base.rstrip("/") + path
    if params:
        sep = "&" if "?" in url else "?"
        url += sep + urlencode(params)
    data = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    echo_parts = [method, url]
    if body is not None:
        echo_parts.append(f"<body {len(data)} bytes>")
    if auth:
        echo_parts.append(f"<basic-auth user={auth[0]}>")
    echo(" ".join(echo_parts))
    if dry_run:
        return 0, None, b""

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    if verbose:
        print(f"[api] status={status} bytes={len(raw)}", file=sys.stderr)
    return status, parsed, raw


def cmd_api(args: argparse.Namespace) -> int:
    body: dict | None = None
    if args.json_body:
        body = json.loads(args.json_body)
    elif args.json_file:
        body = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    auth = None
    if args.user:
        auth = (args.user, args.password or "")
    params = None
    if args.query:
        params = dict(kv.split("=", 1) for kv in args.query)
    status, parsed, raw = _api_call(
        args.base or DEFAULT_API,
        args.path,
        method=args.method,
        body=body,
        params=params,
        auth=auth,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return 0
    if parsed is not None:
        print(json.dumps(parsed, indent=2))
    else:
        sys.stdout.buffer.write(raw)
    return 0 if 200 <= status < 300 else 1


def _simple_get(args: argparse.Namespace, path: str) -> int:
    auth = (args.user, args.password or "") if args.user else None
    status, parsed, raw = _api_call(
        args.base or DEFAULT_API,
        path,
        auth=auth,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return 0
    if parsed is not None:
        print(json.dumps(parsed, indent=2))
    else:
        sys.stdout.buffer.write(raw)
    return 0 if 200 <= status < 300 else 1


def cmd_paths_list(args: argparse.Namespace) -> int:
    return _simple_get(args, "/v3/paths/list")


def cmd_recordings_list(args: argparse.Namespace) -> int:
    return _simple_get(args, "/v3/recordings/list")


def cmd_sessions_list(args: argparse.Namespace) -> int:
    """Aggregate every session/conn endpoint into one JSON document."""
    auth = (args.user, args.password or "") if args.user else None
    endpoints = [
        "/v3/rtspconns/list",
        "/v3/rtspsessions/list",
        "/v3/rtspsconns/list",
        "/v3/rtspssessions/list",
        "/v3/rtmpconns/list",
        "/v3/rtmpsconns/list",
        "/v3/hlsmuxers/list",
        "/v3/webrtcsessions/list",
        "/v3/srtconns/list",
    ]
    out: dict[str, object] = {}
    rc = 0
    for ep in endpoints:
        try:
            status, parsed, raw = _api_call(
                args.base or DEFAULT_API,
                ep,
                auth=auth,
                verbose=args.verbose,
                dry_run=args.dry_run,
                timeout=5.0,
            )
        except Exception as e:  # noqa: BLE001
            out[ep] = {"error": str(e)}
            rc = max(rc, 1)
            continue
        if args.dry_run:
            continue
        if 200 <= status < 300:
            out[ep] = parsed
        else:
            out[ep] = {"status": status, "body": raw.decode("utf-8", "replace")}
            rc = max(rc, 1)
    if not args.dry_run:
        print(json.dumps(out, indent=2))
    return rc


# ── mint-jwt ────────────────────────────────────────────────────────────────


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def cmd_mint_jwt(args: argparse.Namespace) -> int:
    """Create an HS256 JWT with the MediaMTX permissions claim.

    MediaMTX reads either `mediamtx_permissions` (list of {action, path}) or
    falls back to default rules. See docs/features/authentication for the
    full claim shape.
    """
    if not args.secret:
        print(
            "error: --secret required (or --secret-file). "
            "For JWK-URL auth use an external issuer, not this helper.",
            file=sys.stderr,
        )
        return 2
    secret = args.secret
    if args.secret_file:
        secret = Path(args.secret_file).read_text(encoding="utf-8").strip()
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now + args.ttl
    permissions = []
    for spec in args.permission or []:
        action, _, path = spec.partition(":")
        entry = {"action": action}
        if path:
            entry["path"] = path
        permissions.append(entry)
    if not permissions:
        permissions = [
            {"action": "publish"},
            {"action": "read"},
            {"action": "playback"},
        ]
    claims = {
        "iat": now,
        "exp": exp,
        "sub": args.sub or "mtxctl",
        "mediamtx_permissions": permissions,
    }
    if args.iss:
        claims["iss"] = args.iss
    if args.aud:
        claims["aud"] = args.aud

    echo(
        f"mint HS256 JWT  sub={claims['sub']}  "
        f"ttl={args.ttl}s  perms={len(permissions)}"
    )
    if args.dry_run:
        print(json.dumps({"header": header, "claims": claims}, indent=2))
        return 0

    h_b = _b64u(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    c_b = _b64u(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing = f"{h_b}.{c_b}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing, hashlib.sha256).digest()
    token = f"{h_b}.{c_b}.{_b64u(sig)}"
    print(token)
    return 0


# ── parser ──────────────────────────────────────────────────────────────────


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run", action="store_true", help="echo intent; no side effects"
    )
    p.add_argument("--verbose", action="store_true", help="extra stderr logging")


def add_api_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--base",
        default=None,
        help=f"API base URL (default: ${{MEDIAMTX_API}} or {DEFAULT_API})",
    )
    p.add_argument("--user", help="basic-auth username (if api is behind auth)")
    p.add_argument("--password", help="basic-auth password")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Manage a MediaMTX server (install, configure, run, control via API).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("install", help="download latest MediaMTX release to a dir")
    pi.add_argument(
        "--dir",
        default="MediaMTX-bin",
        help="destination directory (default: MediaMTX-bin)",
    )
    add_common(pi)
    pi.set_defaults(fn=cmd_install)

    pc = sub.add_parser("init-config", help="write a good starter mediamtx.yml")
    pc.add_argument(
        "--output",
        default="mediamtx.yml",
        help="target YAML path (default: mediamtx.yml)",
    )
    pc.add_argument("--force", action="store_true", help="overwrite existing file")
    add_common(pc)
    pc.set_defaults(fn=cmd_init_config)

    ps = sub.add_parser("start", help="launch mediamtx in the background")
    ps.add_argument("--bin", help=f"mediamtx binary (default: {DEFAULT_BIN})")
    ps.add_argument("--config", help="mediamtx.yml path")
    ps.add_argument("--pidfile", help=f"pidfile path (default: {DEFAULT_PID})")
    ps.add_argument("--log", help="log file path (default: ./mediamtx.log)")
    add_common(ps)
    ps.set_defaults(fn=cmd_start)

    pst = sub.add_parser("stop", help="SIGTERM the tracked mediamtx process")
    pst.add_argument("--pidfile", help=f"pidfile path (default: {DEFAULT_PID})")
    pst.add_argument(
        "--kill", action="store_true", help="use SIGKILL instead of SIGTERM"
    )
    add_common(pst)
    pst.set_defaults(fn=cmd_stop)

    pr = sub.add_parser("reload", help="SIGHUP the tracked mediamtx for config reload")
    pr.add_argument("--pidfile", help=f"pidfile path (default: {DEFAULT_PID})")
    add_common(pr)
    pr.set_defaults(fn=cmd_reload)

    # Generic API
    pa = sub.add_parser("api", help="generic /v3/* caller")
    pa.add_argument("--path", required=True, help="API path (e.g. /v3/paths/list)")
    pa.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST", "PATCH", "PUT", "DELETE"],
        help="HTTP method (default: GET)",
    )
    pa.add_argument("--json-body", help="raw JSON string to send as body")
    pa.add_argument("--json-file", help="path to file whose contents are the JSON body")
    pa.add_argument(
        "--query",
        action="append",
        metavar="K=V",
        help="URL query param (repeatable)",
    )
    add_api_common(pa)
    add_common(pa)
    pa.set_defaults(fn=cmd_api)

    pl = sub.add_parser("paths-list", help="GET /v3/paths/list")
    add_api_common(pl)
    add_common(pl)
    pl.set_defaults(fn=cmd_paths_list)

    psl = sub.add_parser(
        "sessions-list",
        help="aggregate every /v3/*sessions + /v3/*conns endpoint into one JSON blob",
    )
    add_api_common(psl)
    add_common(psl)
    psl.set_defaults(fn=cmd_sessions_list)

    prl = sub.add_parser("recordings-list", help="GET /v3/recordings/list")
    add_api_common(prl)
    add_common(prl)
    prl.set_defaults(fn=cmd_recordings_list)

    pj = sub.add_parser("mint-jwt", help="create an HS256 JWT for the JWT auth backend")
    pj.add_argument(
        "--secret", help="HMAC secret (shared with mediamtx.yml jwtJWKSURL alternative)"
    )
    pj.add_argument("--secret-file", help="read the secret from a file")
    pj.add_argument("--sub", default="mtxctl", help="subject claim")
    pj.add_argument("--iss", help="issuer claim")
    pj.add_argument("--aud", help="audience claim")
    pj.add_argument(
        "--ttl", type=int, default=3600, help="seconds until expiry (default: 3600)"
    )
    pj.add_argument(
        "--permission",
        action="append",
        metavar="ACTION[:PATH]",
        help="permission entry; repeatable. E.g. publish:live/cam1",
    )
    add_common(pj)
    pj.set_defaults(fn=cmd_mint_jwt)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
