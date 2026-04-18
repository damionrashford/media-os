#!/usr/bin/env python3
"""Media cloud upload CLI.

Unified wrapper around curl / rclone / aws / google-api-python-client / PyVimeo
for uploading media to Cloudflare Stream, Mux, Bunny Stream, S3, YouTube, Vimeo,
and any rclone remote. Stdlib-only for the small stuff; shells out to curl /
rclone / aws for the large transfers so we never buffer huge files into Python.

Tokens are always read from environment variables; never hardcode them.

Usage:
    python cloud.py check
    python cloud.py cloudflare-stream --file video.mp4 [--tus]
    python cloud.py mux              --file video.mp4
    python cloud.py bunny            --file video.mp4 --video-id GUID
    python cloud.py s3               --file video.mp4 --bucket B --key K [--acl public-read]
    python cloud.py rclone           --file video.mp4 --remote myremote:path/
    python cloud.py youtube          --file v.mp4 --title T --description D --tags t1,t2 --privacy unlisted
    python cloud.py vimeo            --file v.mp4 --title T --description D

Global flags: --dry-run (print command, don't run), --verbose (dump response).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path


# ---------- utilities ----------


def log(msg: str) -> None:
    print(f"[cloud] {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"[cloud] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        die(f"environment variable {name} is not set")
    return v


def run(
    cmd: list[str], *, dry_run: bool, verbose: bool, stdin: bytes | None = None
) -> str:
    printable = " ".join(shlex.quote(c) for c in cmd)
    if dry_run:
        print(printable)
        return ""
    if verbose:
        log(f"$ {printable}")
    res = subprocess.run(cmd, input=stdin, capture_output=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode("utf-8", "replace"))
        die(f"command failed (exit {res.returncode}): {printable}", res.returncode)
    out = res.stdout.decode("utf-8", "replace")
    if verbose:
        sys.stderr.write(res.stderr.decode("utf-8", "replace"))
    return out


def need(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        die(f"required binary not found on PATH: {binary}")
    return path


def file_size(path: str) -> int:
    p = Path(path)
    if not p.is_file():
        die(f"file not found: {path}")
    return p.stat().st_size


def json_or_text(text: str, verbose: bool) -> None:
    try:
        obj = json.loads(text)
        print(json.dumps(obj, indent=2) if verbose else json.dumps(obj))
    except json.JSONDecodeError:
        print(text)


# ---------- subcommands ----------


def cmd_check(_args) -> None:
    table = {
        "curl": shutil.which("curl"),
        "rclone": shutil.which("rclone"),
        "aws": shutil.which("aws"),
        "python": sys.executable,
    }
    envs = [
        "CF_TOKEN",
        "CF_ACCOUNT_ID",
        "MUX_TOKEN",
        "MUX_SECRET",
        "BUNNY_KEY",
        "BUNNY_LIB_ID",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "VIMEO_TOKEN",
    ]
    print("binaries:")
    for k, v in table.items():
        print(f"  {k:10s} {'OK  ' + v if v else 'MISSING'}")
    print("env vars:")
    for e in envs:
        print(f"  {e:24s} {'set' if os.environ.get(e) else '-'}")


def cmd_cloudflare_stream(args) -> None:
    token = env("CF_TOKEN")
    acct = env("CF_ACCOUNT_ID")
    size = file_size(args.file)
    need("curl")

    if args.tus or size > 200 * 1024 * 1024:
        # TUS resumable: request a Location, then PATCH chunks via curl.
        meta = "name " + base64.b64encode(Path(args.file).name.encode()).decode()
        url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/stream?direct_user=true"
        cmd = [
            "curl",
            "-sS",
            "-X",
            "POST",
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            "Tus-Resumable: 1.0.0",
            "-H",
            f"Upload-Length: {size}",
            "-H",
            f"Upload-Metadata: {meta}",
            "-D",
            "-",
            url,
        ]
        headers = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
        if args.dry_run:
            return
        location = ""
        for line in headers.splitlines():
            if line.lower().startswith("location:"):
                location = line.split(":", 1)[1].strip()
        if not location:
            die("cloudflare did not return a tus Location header")
        log(f"tus Location: {location}")
        # Upload body via PATCH (single shot; curl handles the bytes).
        patch_cmd = [
            "curl",
            "-sS",
            "-X",
            "PATCH",
            "-H",
            "Tus-Resumable: 1.0.0",
            "-H",
            "Upload-Offset: 0",
            "-H",
            "Content-Type: application/offset+octet-stream",
            "--data-binary",
            f"@{args.file}",
            location,
        ]
        run(patch_cmd, dry_run=False, verbose=args.verbose)
        log("tus upload complete; poll /stream/<uid> for status")
        return

    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/stream"
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        "-H",
        f"Authorization: Bearer {token}",
        "-F",
        f"file=@{args.file}",
        url,
    ]
    out = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if not args.dry_run:
        json_or_text(out, args.verbose)


def cmd_mux(args) -> None:
    tok = env("MUX_TOKEN")
    sec = env("MUX_SECRET")
    need("curl")
    body = json.dumps(
        {
            "new_asset_settings": {"playback_policy": ["public"]},
            "cors_origin": "*",
        }
    )
    create = [
        "curl",
        "-sS",
        "-X",
        "POST",
        "-u",
        f"{tok}:{sec}",
        "-H",
        "Content-Type: application/json",
        "-d",
        body,
        "https://api.mux.com/video/v1/uploads",
    ]
    out = run(create, dry_run=args.dry_run, verbose=args.verbose)
    if args.dry_run:
        return
    try:
        upload_url = json.loads(out)["data"]["url"]
    except (KeyError, json.JSONDecodeError):
        die(f"unexpected mux response: {out}")
    log(f"signed PUT url: {upload_url}")
    put = [
        "curl",
        "-sS",
        "-X",
        "PUT",
        "-H",
        "Content-Type: application/octet-stream",
        "--data-binary",
        f"@{args.file}",
        upload_url,
    ]
    run(put, dry_run=False, verbose=args.verbose)
    log(
        "upload complete; poll /video/v1/uploads/<id> for asset_id, then /video/v1/assets/<id>"
    )
    json_or_text(out, args.verbose)


def cmd_bunny(args) -> None:
    key = env("BUNNY_KEY")
    lib = args.lib_id or env("BUNNY_LIB_ID")
    need("curl")
    if not args.video_id:
        die(
            "--video-id is required (POST to /library/<lib>/videos first to get a GUID)"
        )
    url = f"https://video.bunnycdn.com/library/{lib}/videos/{args.video_id}"
    cmd = [
        "curl",
        "-sS",
        "-X",
        "PUT",
        "-H",
        f"AccessKey: {key}",
        "--upload-file",
        args.file,
        url,
    ]
    out = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if not args.dry_run:
        json_or_text(out or "{}", args.verbose)


def cmd_s3(args) -> None:
    need("aws")
    cmd = [
        "aws",
        "s3",
        "cp",
        args.file,
        f"s3://{args.bucket}/{args.key}",
        "--content-type",
        args.content_type,
    ]
    if args.acl:
        cmd += ["--acl", args.acl]
    if args.cache_control:
        cmd += ["--cache-control", args.cache_control]
    out = run(cmd, dry_run=args.dry_run, verbose=args.verbose)
    if not args.dry_run:
        print(out.strip())
        print(f"https://{args.bucket}.s3.amazonaws.com/{args.key}")


def cmd_rclone(args) -> None:
    need("rclone")
    cmd = ["rclone", "copy", "--progress", args.file, args.remote]
    if args.transfers:
        cmd += ["--transfers", str(args.transfers)]
    run(cmd, dry_run=args.dry_run, verbose=args.verbose)


def cmd_youtube(args) -> None:
    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except ImportError:
        die(
            "pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    token_path = Path(
        os.environ.get("YT_TOKEN_FILE", Path.home() / ".config/yt-upload-token.json")
    )
    client_path = Path(
        os.environ.get(
            "YT_CLIENT_SECRETS", Path.home() / ".config/yt-client-secrets.json"
        )
    )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_path.exists():
                die(f"missing OAuth client secrets at {client_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    if args.dry_run:
        print(
            f"[youtube] would upload {args.file} title={args.title!r} privacy={args.privacy}"
        )
        return

    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": args.title,
            "description": args.description,
            "tags": args.tags.split(",") if args.tags else [],
        },
        "status": {"privacyStatus": args.privacy},
    }
    media = MediaFileUpload(
        args.file, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/*"
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status and args.verbose:
            log(f"progress: {int(status.progress() * 100)}%")
    print(
        json.dumps(
            {"id": response["id"], "url": f"https://youtu.be/{response['id']}"},
            indent=2,
        )
    )


def cmd_vimeo(args) -> None:
    try:
        import vimeo  # type: ignore
    except ImportError:
        die("pip install PyVimeo")
    token = env("VIMEO_TOKEN")
    if args.dry_run:
        print(f"[vimeo] would upload {args.file} title={args.title!r}")
        return
    client = vimeo.VimeoClient(token=token)
    uri = client.upload(
        args.file, data={"name": args.title, "description": args.description or ""}
    )
    info = client.get(uri + "?fields=link,player_embed_url,uri").json()
    print(json.dumps(info, indent=2))


# ---------- argparse wiring ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cloud.py", description="Upload media to cloud platforms."
    )
    p.add_argument(
        "--dry-run", action="store_true", help="print the command(s) without running"
    )
    p.add_argument(
        "--verbose", action="store_true", help="verbose logging + pretty JSON"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(func=cmd_check)

    cf = sub.add_parser("cloudflare-stream")
    cf.add_argument("--file", required=True)
    cf.add_argument("--tus", action="store_true", help="force TUS resumable upload")
    cf.set_defaults(func=cmd_cloudflare_stream)

    mx = sub.add_parser("mux")
    mx.add_argument("--file", required=True)
    mx.set_defaults(func=cmd_mux)

    bn = sub.add_parser("bunny")
    bn.add_argument("--file", required=True)
    bn.add_argument("--lib-id")
    bn.add_argument(
        "--video-id", required=True, help="GUID from POST /library/<lib>/videos"
    )
    bn.set_defaults(func=cmd_bunny)

    s3 = sub.add_parser("s3")
    s3.add_argument("--file", required=True)
    s3.add_argument("--bucket", required=True)
    s3.add_argument("--key", required=True)
    s3.add_argument("--acl", default=None)
    s3.add_argument("--content-type", default="video/mp4")
    s3.add_argument("--cache-control", default="max-age=31536000")
    s3.set_defaults(func=cmd_s3)

    rc = sub.add_parser("rclone")
    rc.add_argument("--file", required=True)
    rc.add_argument("--remote", required=True, help="e.g. gdrive:videos/")
    rc.add_argument("--transfers", type=int, default=None)
    rc.set_defaults(func=cmd_rclone)

    yt = sub.add_parser("youtube")
    yt.add_argument("--file", required=True)
    yt.add_argument("--title", required=True)
    yt.add_argument("--description", default="")
    yt.add_argument("--tags", default="")
    yt.add_argument(
        "--privacy", choices=["public", "unlisted", "private"], default="unlisted"
    )
    yt.set_defaults(func=cmd_youtube)

    vm = sub.add_parser("vimeo")
    vm.add_argument("--file", required=True)
    vm.add_argument("--title", required=True)
    vm.add_argument("--description", default="")
    vm.set_defaults(func=cmd_vimeo)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
