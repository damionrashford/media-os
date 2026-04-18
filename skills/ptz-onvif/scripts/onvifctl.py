#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""onvifctl.py — Discover and control ONVIF IP cameras.

Stdlib only (socket + http.client + hashlib + XML via regex; hand-rolled SOAP).
Non-interactive. Subcommands:

    discover                  WS-Discovery multicast probe on 239.255.255.250:3702
    info                      Device/GetDeviceInformation
    streams                   Media/GetProfiles + GetStreamUri → RTSP
    snapshot                  Media/GetSnapshotUri + HTTP fetch
    ptz continuous|absolute|stop|preset-goto|preset-set

Auth: WS-Security UsernameToken digest
    Digest = BASE64( SHA1( raw_nonce + created + password ) )

Flags common to camera ops:
    --host HOST  (or --xaddr URL)
    --user USER --password PW
    --profile-token TOKEN   (auto-discover first if omitted)
    --dry-run --verbose
    --timeout SEC (default 8)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

WSDL_DISCOVERY_ADDR = ("239.255.255.250", 3702)

NS = {
    "s": "http://www.w3.org/2003/05/soap-envelope",
    "wsa": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
    "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
    "dn": "http://www.onvif.org/ver10/network/wsdl",
    "tds": "http://www.onvif.org/ver10/device/wsdl",
    "trt": "http://www.onvif.org/ver10/media/wsdl",
    "tptz": "http://www.onvif.org/ver20/ptz/wsdl",
    "tt": "http://www.onvif.org/ver10/schema",
    "wsse": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
    "wsu": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
}

PW_DIGEST = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-username-token-profile-1.0#PasswordDigest"
)
NONCE_B64 = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-soap-message-security-1.0#Base64Binary"
)


# -----------------------------------------------------------------------------
# WS-Security digest
# -----------------------------------------------------------------------------


def make_wsse_header(user: str, password: str, time_offset: float = 0.0) -> str:
    nonce = os.urandom(16)
    created = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    if time_offset:
        # optional skew fudge
        ts = time.time() + time_offset
        created = (
            datetime.fromtimestamp(ts, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    digest = base64.b64encode(
        hashlib.sha1(
            nonce + created.encode("utf-8") + password.encode("utf-8")
        ).digest()
    ).decode()
    nonce_b64 = base64.b64encode(nonce).decode()
    return (
        f'<wsse:Security xmlns:wsse="{NS["wsse"]}" '
        f'xmlns:wsu="{NS["wsu"]}" s:mustUnderstand="1">'
        f"<wsse:UsernameToken>"
        f"<wsse:Username>{_xml_escape(user)}</wsse:Username>"
        f'<wsse:Password Type="{PW_DIGEST}">{digest}</wsse:Password>'
        f'<wsse:Nonce EncodingType="{NONCE_B64}">{nonce_b64}</wsse:Nonce>'
        f"<wsu:Created>{created}</wsu:Created>"
        f"</wsse:UsernameToken>"
        f"</wsse:Security>"
    )


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# -----------------------------------------------------------------------------
# SOAP envelope + request
# -----------------------------------------------------------------------------


def soap_envelope(body: str, wsse_header: str | None = None) -> str:
    headers = wsse_header if wsse_header else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<s:Envelope xmlns:s="{NS["s"]}" '
        f'xmlns:tds="{NS["tds"]}" '
        f'xmlns:trt="{NS["trt"]}" '
        f'xmlns:tptz="{NS["tptz"]}" '
        f'xmlns:tt="{NS["tt"]}">'
        f"<s:Header>{headers}</s:Header>"
        f"<s:Body>{body}</s:Body>"
        "</s:Envelope>"
    )


def soap_request(
    xaddr: str,
    body: str,
    user: str | None,
    password: str | None,
    *,
    action: str = "",
    timeout: float = 8.0,
    verbose: bool = False,
    dry_run: bool = False,
    time_offset: float = 0.0,
) -> str:
    wsse = make_wsse_header(user, password, time_offset) if user else None
    envelope = soap_envelope(body, wsse)
    if verbose or dry_run:
        sys.stderr.write(f"[POST {xaddr}]\n{envelope}\n")
    if dry_run:
        return ""
    req = urllib.request.Request(
        xaddr,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{action}"',
            "User-Agent": "ptz-onvif-skill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        data = e.read().decode("utf-8", errors="replace")
        if verbose:
            sys.stderr.write(f"[HTTP {e.code}]\n{data}\n")
        raise SystemExit(f"HTTP {e.code}: {data[:200]}")
    if verbose:
        sys.stderr.write(f"[reply]\n{data}\n")
    return data


def xml_find(text: str, tag: str) -> list[str]:
    """Find all values of <prefix:tag>...</prefix:tag>. Returns list of inner texts."""
    pat = re.compile(
        rf"<(?:[a-zA-Z0-9]+:)?{re.escape(tag)}[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?{re.escape(tag)}>",
        re.DOTALL,
    )
    return pat.findall(text)


def xml_attr(text: str, tag: str, attr: str) -> list[str]:
    pat = re.compile(
        rf'<(?:[a-zA-Z0-9]+:)?{re.escape(tag)}[^>]*\b{re.escape(attr)}="([^"]*)"',
        re.DOTALL,
    )
    return pat.findall(text)


# -----------------------------------------------------------------------------
# Discovery
# -----------------------------------------------------------------------------


def cmd_discover(args: argparse.Namespace) -> int:
    msg_id = f"urn:uuid:{os.urandom(16).hex()}"
    probe = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
        'xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
        'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
        'xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
        "<s:Header>"
        "<wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>"
        f"<wsa:MessageID>{msg_id}</wsa:MessageID>"
        "<wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>"
        "</s:Header>"
        "<s:Body>"
        "<d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe>"
        "</s:Body>"
        "</s:Envelope>"
    )
    if args.verbose:
        sys.stderr.write(
            f"[ws-discovery probe to {WSDL_DISCOVERY_ADDR[0]}:{WSDL_DISCOVERY_ADDR[1]}]\n"
        )
    if args.dry_run:
        print(probe)
        return 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.settimeout(0.5)
    sock.sendto(probe.encode("utf-8"), WSDL_DISCOVERY_ADDR)
    found: dict[str, dict] = {}
    end = time.time() + args.timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        text = data.decode("utf-8", errors="replace")
        xaddrs = " ".join(xml_find(text, "XAddrs"))
        for x in xaddrs.split():
            if x not in found:
                types = " ".join(xml_find(text, "Types"))
                scopes = xml_find(text, "Scopes")
                found[x] = {
                    "xaddr": x,
                    "addr": f"{addr[0]}:{addr[1]}",
                    "types": types.strip(),
                    "scopes": [s.strip() for seg in scopes for s in seg.split()],
                }
    sock.close()
    print(json.dumps(list(found.values()), indent=2))
    return 0 if found else 1


# -----------------------------------------------------------------------------
# Device / Media / PTZ helpers
# -----------------------------------------------------------------------------


def _xaddr(args: argparse.Namespace, service: str = "device_service") -> str:
    if getattr(args, "xaddr", None):
        return args.xaddr
    if not args.host:
        raise SystemExit("--host or --xaddr required")
    port = getattr(args, "port", None) or 80
    return f"http://{args.host}:{port}/onvif/{service}"


def get_device_info(args: argparse.Namespace) -> dict:
    body = "<tds:GetDeviceInformation/>"
    resp = soap_request(
        _xaddr(args, "device_service"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver10/device/wsdl/GetDeviceInformation",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
        time_offset=getattr(args, "time_offset", 0.0),
    )
    if args.dry_run:
        return {}
    return {
        "Manufacturer": (xml_find(resp, "Manufacturer") or [""])[0],
        "Model": (xml_find(resp, "Model") or [""])[0],
        "FirmwareVersion": (xml_find(resp, "FirmwareVersion") or [""])[0],
        "SerialNumber": (xml_find(resp, "SerialNumber") or [""])[0],
        "HardwareId": (xml_find(resp, "HardwareId") or [""])[0],
    }


def cmd_info(args: argparse.Namespace) -> int:
    info = get_device_info(args)
    if args.dry_run:
        return 0
    if args.format == "json":
        print(json.dumps(info, indent=2))
    else:
        for k, v in info.items():
            print(f"{k}: {v}")
    return 0


def get_profiles(args: argparse.Namespace) -> list[dict]:
    body = "<trt:GetProfiles/>"
    resp = soap_request(
        _xaddr(args, "Media"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver10/media/wsdl/GetProfiles",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return []
    # Find each <trt:Profiles ... token="..."> block
    profiles = []
    for m in re.finditer(
        r'<(?:[a-zA-Z0-9]+:)?Profiles[^>]*token="([^"]+)"[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?Profiles>',
        resp,
        re.DOTALL,
    ):
        token = m.group(1)
        block = m.group(2)
        name = (xml_find(block, "Name") or [""])[0]
        profiles.append({"token": token, "name": name})
    return profiles


def get_stream_uri(args: argparse.Namespace, profile_token: str) -> str:
    body = (
        "<trt:GetStreamUri>"
        "<trt:StreamSetup>"
        "<tt:Stream>RTP-Unicast</tt:Stream>"
        "<tt:Transport><tt:Protocol>RTSP</tt:Protocol></tt:Transport>"
        "</trt:StreamSetup>"
        f"<trt:ProfileToken>{profile_token}</trt:ProfileToken>"
        "</trt:GetStreamUri>"
    )
    resp = soap_request(
        _xaddr(args, "Media"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver10/media/wsdl/GetStreamUri",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return ""
    uris = xml_find(resp, "Uri")
    return uris[0] if uris else ""


def cmd_streams(args: argparse.Namespace) -> int:
    profiles = get_profiles(args)
    if args.dry_run:
        return 0
    out = []
    for p in profiles:
        uri = get_stream_uri(args, p["token"])
        out.append({"profile_token": p["token"], "name": p["name"], "rtsp_uri": uri})
    print(json.dumps(out, indent=2))
    return 0


def get_snapshot_uri(args: argparse.Namespace, profile_token: str) -> str:
    body = f"<trt:GetSnapshotUri><trt:ProfileToken>{profile_token}</trt:ProfileToken></trt:GetSnapshotUri>"
    resp = soap_request(
        _xaddr(args, "Media"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver10/media/wsdl/GetSnapshotUri",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return ""
    uris = xml_find(resp, "Uri")
    return uris[0] if uris else ""


def cmd_snapshot(args: argparse.Namespace) -> int:
    token = args.profile_token or (get_profiles(args) or [{"token": ""}])[0]["token"]
    if not token:
        raise SystemExit("no media profile found")
    uri = get_snapshot_uri(args, token)
    if args.dry_run:
        return 0
    if not uri:
        raise SystemExit("no SnapshotUri returned")
    # Fetch with HTTP Basic; most cameras also accept Digest.
    if args.user:
        pr = urllib.parse.urlparse(uri)
        userinfo = (
            f"{urllib.parse.quote(args.user)}:{urllib.parse.quote(args.password or '')}"
        )
        netloc = f"{userinfo}@{pr.netloc}"
        uri = urllib.parse.urlunparse(pr._replace(netloc=netloc))
    req = urllib.request.Request(uri, headers={"User-Agent": "ptz-onvif-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"snapshot fetch HTTP {e.code}")
    with open(args.output, "wb") as f:
        f.write(data)
    print(args.output)
    return 0


# -----------------------------------------------------------------------------
# PTZ
# -----------------------------------------------------------------------------


def _ptz_profile(args: argparse.Namespace) -> str:
    if args.profile_token:
        return args.profile_token
    profiles = get_profiles(args)
    if not profiles:
        raise SystemExit("no media profile found (needed for ProfileToken)")
    return profiles[0]["token"]


def cmd_ptz_continuous(args: argparse.Namespace) -> int:
    token = _ptz_profile(args)
    body = (
        "<tptz:ContinuousMove>"
        f"<tptz:ProfileToken>{token}</tptz:ProfileToken>"
        "<tptz:Velocity>"
        f'<tt:PanTilt x="{args.pan}" y="{args.tilt}"/>'
        f'<tt:Zoom x="{args.zoom}"/>'
        "</tptz:Velocity>"
        "</tptz:ContinuousMove>"
    )
    soap_request(
        _xaddr(args, "PTZ"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver20/ptz/wsdl/ContinuousMove",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.timeout_move > 0 and not args.dry_run:
        time.sleep(args.timeout_move)
        stop_body = f"<tptz:Stop><tptz:ProfileToken>{token}</tptz:ProfileToken><tptz:PanTilt>true</tptz:PanTilt><tptz:Zoom>true</tptz:Zoom></tptz:Stop>"
        soap_request(
            _xaddr(args, "PTZ"),
            stop_body,
            args.user,
            args.password,
            action="http://www.onvif.org/ver20/ptz/wsdl/Stop",
            timeout=args.timeout,
            verbose=args.verbose,
        )
    return 0


def cmd_ptz_absolute(args: argparse.Namespace) -> int:
    token = _ptz_profile(args)
    body = (
        "<tptz:AbsoluteMove>"
        f"<tptz:ProfileToken>{token}</tptz:ProfileToken>"
        "<tptz:Position>"
        f'<tt:PanTilt x="{args.pan_x}" y="{args.tilt_y}"/>'
        f'<tt:Zoom x="{args.zoom}"/>'
        "</tptz:Position>"
        "</tptz:AbsoluteMove>"
    )
    soap_request(
        _xaddr(args, "PTZ"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver20/ptz/wsdl/AbsoluteMove",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    return 0


def cmd_ptz_stop(args: argparse.Namespace) -> int:
    token = _ptz_profile(args)
    body = (
        "<tptz:Stop>"
        f"<tptz:ProfileToken>{token}</tptz:ProfileToken>"
        "<tptz:PanTilt>true</tptz:PanTilt>"
        "<tptz:Zoom>true</tptz:Zoom>"
        "</tptz:Stop>"
    )
    soap_request(
        _xaddr(args, "PTZ"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver20/ptz/wsdl/Stop",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    return 0


def cmd_ptz_preset_goto(args: argparse.Namespace) -> int:
    token = _ptz_profile(args)
    body = (
        "<tptz:GotoPreset>"
        f"<tptz:ProfileToken>{token}</tptz:ProfileToken>"
        f"<tptz:PresetToken>{args.preset_token}</tptz:PresetToken>"
        "</tptz:GotoPreset>"
    )
    soap_request(
        _xaddr(args, "PTZ"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver20/ptz/wsdl/GotoPreset",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    return 0


def cmd_ptz_preset_set(args: argparse.Namespace) -> int:
    token = _ptz_profile(args)
    body = (
        "<tptz:SetPreset>"
        f"<tptz:ProfileToken>{token}</tptz:ProfileToken>"
        f"<tptz:PresetName>{_xml_escape(args.preset_name)}</tptz:PresetName>"
        "</tptz:SetPreset>"
    )
    resp = soap_request(
        _xaddr(args, "PTZ"),
        body,
        args.user,
        args.password,
        action="http://www.onvif.org/ver20/ptz/wsdl/SetPreset",
        timeout=args.timeout,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return 0
    tokens = xml_find(resp, "PresetToken")
    print(json.dumps({"preset_token": tokens[0] if tokens else ""}, indent=2))
    return 0


# -----------------------------------------------------------------------------
# Argparse plumbing
# -----------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser, need_auth: bool = True) -> None:
    p.add_argument("--host")
    p.add_argument("--port", type=int, default=80)
    p.add_argument("--xaddr", help="full Device or service URL (overrides --host)")
    if need_auth:
        p.add_argument("--user", default=os.environ.get("ONVIF_USER"))
        p.add_argument("--password", default=os.environ.get("ONVIF_PASSWORD"))
    p.add_argument("--profile-token", default=None)
    p.add_argument("--format", choices=["text", "json"], default="json")
    p.add_argument("--timeout", type=float, default=8.0)
    p.add_argument(
        "--time-offset",
        type=float,
        default=0.0,
        help="seconds to add to Created (clock-skew workaround)",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ONVIF CLI.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("discover", help="WS-Discovery multicast probe")
    sp.add_argument("--timeout", type=float, default=3.0)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(fn=cmd_discover)

    sp = sub.add_parser("info", help="Device/GetDeviceInformation")
    _add_common(sp)
    sp.set_defaults(fn=cmd_info)

    sp = sub.add_parser("streams", help="Media/GetProfiles + GetStreamUri")
    _add_common(sp)
    sp.set_defaults(fn=cmd_streams)

    sp = sub.add_parser("snapshot", help="Media/GetSnapshotUri + HTTP fetch")
    _add_common(sp)
    sp.add_argument("--output", default="snapshot.jpg")
    sp.set_defaults(fn=cmd_snapshot)

    ptz = sub.add_parser("ptz", help="PTZ subcommands")
    ptz_sub = ptz.add_subparsers(dest="ptz_cmd", required=True)

    c = ptz_sub.add_parser("continuous")
    _add_common(c)
    c.add_argument("--pan", type=float, default=0.0)
    c.add_argument("--tilt", type=float, default=0.0)
    c.add_argument("--zoom", type=float, default=0.0)
    c.add_argument(
        "--timeout-move", type=float, default=0.0, help="auto-stop after N seconds"
    )
    c.set_defaults(fn=cmd_ptz_continuous)

    c = ptz_sub.add_parser("absolute")
    _add_common(c)
    c.add_argument("--pan-x", type=float, required=True)
    c.add_argument("--tilt-y", type=float, required=True)
    c.add_argument("--zoom", type=float, default=0.0)
    c.set_defaults(fn=cmd_ptz_absolute)

    c = ptz_sub.add_parser("stop")
    _add_common(c)
    c.set_defaults(fn=cmd_ptz_stop)

    c = ptz_sub.add_parser("preset-goto")
    _add_common(c)
    c.add_argument("--preset-token", required=True)
    c.set_defaults(fn=cmd_ptz_preset_goto)

    c = ptz_sub.add_parser("preset-set")
    _add_common(c)
    c.add_argument("--preset-name", required=True)
    c.set_defaults(fn=cmd_ptz_preset_set)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
