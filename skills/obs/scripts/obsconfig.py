#!/usr/bin/env python3
"""obsconfig.py — install OBS Studio and author its on-disk config (profiles,
scene collections, encoder JSON, global.ini, service.json) programmatically.

Stdlib only. Non-interactive. Cross-platform (macOS, Linux, Windows).

Subcommands:
    check                        report OBS version + config dir + profiles + collections
    install                      install OBS for current platform (--dry-run supported)
    profile list
    profile create --name N [--template 1080p60_stream|1080p30_record|720p60_stream]
    profile delete --name N
    profile set-default --name N
    collection list
    collection create --name N [--template blank|webcam|browser-overlay]
    collection delete --name N
    collection set-default --name N
    encoder set --profile N --codec x264|nvenc|qsv|vt [--bitrate 6000] [--preset veryfast] [--target stream|record]
    service set --profile N --type rtmp_custom|rtmp_common [--service Twitch] --server URL --key K
    export --profile N --output bundle.zip
    import --archive bundle.zip

All commands accept --dry-run and --verbose.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Platform + paths
# ---------------------------------------------------------------------------


def detect_platform() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "mac"
    if s == "windows":
        return "win"
    if s == "linux":
        return "linux"
    return s


def config_root(plat: str | None = None) -> Path:
    plat = plat or detect_platform()
    home = Path.home()
    if plat == "mac":
        return home / "Library" / "Application Support" / "obs-studio"
    if plat == "win":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "obs-studio"
        return home / "AppData" / "Roaming" / "obs-studio"
    # linux: prefer native, fall back to flatpak if native missing and flatpak exists
    native = home / ".config" / "obs-studio"
    flatpak = home / ".var" / "app" / "com.obsproject.Studio" / "config" / "obs-studio"
    if not native.exists() and flatpak.exists():
        return flatpak
    return native


def profiles_dir(plat: str | None = None) -> Path:
    return config_root(plat) / "basic" / "profiles"


def scenes_dir(plat: str | None = None) -> Path:
    return config_root(plat) / "basic" / "scenes"


def global_ini_path(plat: str | None = None) -> Path:
    return config_root(plat) / "global.ini"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def log(verbose: bool, *args: Any) -> None:
    if verbose:
        print("[obsconfig]", *args, file=sys.stderr)


def ensure_dir(p: Path, dry_run: bool = False, verbose: bool = False) -> None:
    if p.exists():
        return
    log(verbose, f"mkdir -p {p}")
    if not dry_run:
        p.mkdir(parents=True, exist_ok=True)


def write_text(
    p: Path, text: str, dry_run: bool = False, verbose: bool = False
) -> None:
    log(verbose, f"write {p} ({len(text)} bytes)")
    if dry_run:
        return
    p.write_text(text, encoding="utf-8")


def write_json(
    p: Path, data: Any, dry_run: bool = False, verbose: bool = False
) -> None:
    write_text(p, json.dumps(data, indent=4), dry_run=dry_run, verbose=verbose)


def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def new_uuid() -> str:
    return str(uuid.uuid4())


def obs_version() -> str | None:
    for exe in ("obs", "obs64", "obs32"):
        path = shutil.which(exe)
        if path:
            try:
                out = subprocess.run(
                    [path, "--version"], capture_output=True, text=True, timeout=5
                )
                return (out.stdout or out.stderr).strip().splitlines()[0]
            except Exception:
                return f"found at {path} (version probe failed)"
    return None


# ---------------------------------------------------------------------------
# INI read/write (OBS uses a loose INI — preserve case + comments best-effort)
# ---------------------------------------------------------------------------


def load_ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str  # preserve case (OBS keys are CamelCase)
    if path.exists():
        cp.read(path, encoding="utf-8")
    return cp


def save_ini(
    cp: configparser.ConfigParser,
    path: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    ensure_dir(path.parent, dry_run=dry_run, verbose=verbose)
    from io import StringIO

    buf = StringIO()
    cp.write(buf, space_around_delimiters=False)
    write_text(path, buf.getvalue(), dry_run=dry_run, verbose=verbose)


# ---------------------------------------------------------------------------
# Templates — profile basic.ini
# ---------------------------------------------------------------------------

PROFILE_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "1080p60_stream": {
        "General": {"Name": "__NAME__"},
        "Video": {
            "BaseCX": "1920",
            "BaseCY": "1080",
            "OutputCX": "1920",
            "OutputCY": "1080",
            "FPSType": "0",
            "FPSCommon": "60",
        },
        "Output": {
            "Mode": "Advanced",
            "RecFilePath": str(Path.home() / "Videos"),
            "RecFormat2": "mkv",
            "RecEncoder": "obs_x264",
            "StreamEncoder": "obs_x264",
        },
        "SimpleOutput": {"VBitrate": "6000", "ABitrate": "160", "RecQuality": "Stream"},
        "AdvOut": {"TrackIndex": "1", "RecType": "Standard", "RecTracks": "1"},
        "Audio": {"SampleRate": "48000", "ChannelSetup": "Stereo"},
    },
    "1080p30_record": {
        "General": {"Name": "__NAME__"},
        "Video": {
            "BaseCX": "1920",
            "BaseCY": "1080",
            "OutputCX": "1920",
            "OutputCY": "1080",
            "FPSType": "0",
            "FPSCommon": "30",
        },
        "Output": {
            "Mode": "Advanced",
            "RecFilePath": str(Path.home() / "Videos"),
            "RecFormat2": "mkv",
            "RecEncoder": "obs_x264",
            "StreamEncoder": "obs_x264",
        },
        "SimpleOutput": {"VBitrate": "12000", "ABitrate": "192", "RecQuality": "HQ"},
        "AdvOut": {"TrackIndex": "1", "RecType": "Standard", "RecTracks": "1"},
        "Audio": {"SampleRate": "48000", "ChannelSetup": "Stereo"},
    },
    "720p60_stream": {
        "General": {"Name": "__NAME__"},
        "Video": {
            "BaseCX": "1280",
            "BaseCY": "720",
            "OutputCX": "1280",
            "OutputCY": "720",
            "FPSType": "0",
            "FPSCommon": "60",
        },
        "Output": {
            "Mode": "Advanced",
            "RecFilePath": str(Path.home() / "Videos"),
            "RecFormat2": "mkv",
            "RecEncoder": "obs_x264",
            "StreamEncoder": "obs_x264",
        },
        "SimpleOutput": {"VBitrate": "4500", "ABitrate": "160", "RecQuality": "Stream"},
        "AdvOut": {"TrackIndex": "1", "RecType": "Standard", "RecTracks": "1"},
        "Audio": {"SampleRate": "48000", "ChannelSetup": "Stereo"},
    },
}


# Encoder JSON defaults per codec
ENCODER_DEFAULTS: dict[str, dict[str, Any]] = {
    "x264": {
        "bitrate": 6000,
        "keyint_sec": 2,
        "preset": "veryfast",
        "profile": "high",
        "rate_control": "CBR",
        "tune": "zerolatency",
        "x264opts": "",
    },
    "nvenc": {
        "bitrate": 6000,
        "keyint_sec": 2,
        "preset": "p5",
        "profile": "high",
        "rate_control": "CBR",
        "tune": "hq",
        "multipass": "qres",
        "lookahead": False,
        "psycho_aq": True,
    },
    "qsv": {
        "bitrate": 6000,
        "keyint_sec": 2,
        "target_usage": "balanced",
        "profile": "high",
        "rate_control": "CBR",
        "async_depth": 4,
    },
    "vt": {
        "bitrate": 6000,
        "keyint_sec": 2,
        "profile": "high",
        "rate_control": "CBR",
    },
}


ENCODER_IDS: dict[str, str] = {
    "x264": "obs_x264",
    "nvenc": "jim_nvenc",
    "qsv": "obs_qsv11",
    "vt": "com.apple.videotoolbox.videoencoder.ave.avc",
}


# Scene collection templates
def scene_template(name: str, template: str) -> dict[str, Any]:
    scene_uuid = new_uuid()
    tpl: dict[str, Any] = {
        "current_scene": name,
        "current_transition": "Fade",
        "transition_duration": 300,
        "transitions": [{"id": "fade_transition", "name": "Fade"}],
        "scene_order": [{"name": name}],
        "sources": [
            {
                "id": "scene",
                "name": name,
                "uuid": scene_uuid,
                "settings": {"items": []},
            }
        ],
        "groups": [],
        "quick_transitions": [],
        "modules": {},
    }

    scene_source = tpl["sources"][0]

    if template == "blank":
        return tpl

    if template == "webcam":
        plat = detect_platform()
        if plat == "mac":
            kind = "av_capture_input_v2"
            settings = {"device": "", "preset": "High"}
        elif plat == "win":
            kind = "dshow_input"
            settings = {"video_device_id": "", "resolution": "1280x720"}
        else:
            kind = "v4l2_input"
            settings = {"device_id": "/dev/video0", "input": 0}
        cam_uuid = new_uuid()
        tpl["sources"].append(
            {
                "id": kind,
                "name": "Webcam",
                "uuid": cam_uuid,
                "settings": settings,
                "filters": [],
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "hotkeys": {},
            }
        )
        scene_source["settings"]["items"].append(
            {
                "source_uuid": cam_uuid,
                "visible": True,
                "locked": False,
                "pos": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "bounds_type": 0,
                "align": 5,
            }
        )
        return tpl

    if template == "browser-overlay":
        plat = detect_platform()
        if plat == "mac":
            cap_kind = "display_capture"
            cap_settings = {"display": 0, "show_cursor": True}
        elif plat == "win":
            cap_kind = "monitor_capture"
            cap_settings = {"monitor": 0, "capture_cursor": True}
        else:
            cap_kind = "pipewire-screen-capture-source"
            cap_settings = {"ShowCursor": True}
        cap_uuid = new_uuid()
        ovl_uuid = new_uuid()
        tpl["sources"].append(
            {
                "id": cap_kind,
                "name": "Screen",
                "uuid": cap_uuid,
                "settings": cap_settings,
                "filters": [],
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "hotkeys": {},
            }
        )
        tpl["sources"].append(
            {
                "id": "browser_source",
                "name": "Overlay",
                "uuid": ovl_uuid,
                "settings": {
                    "url": "https://example.com/overlay",
                    "width": 1920,
                    "height": 1080,
                    "fps_custom": False,
                    "reroute_audio": False,
                },
                "filters": [],
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "hotkeys": {},
            }
        )
        scene_source["settings"]["items"].append(
            {
                "source_uuid": cap_uuid,
                "visible": True,
                "locked": False,
                "pos": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "bounds_type": 0,
                "align": 5,
            }
        )
        scene_source["settings"]["items"].append(
            {
                "source_uuid": ovl_uuid,
                "visible": True,
                "locked": False,
                "pos": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "bounds_type": 0,
                "align": 5,
            }
        )
        return tpl

    raise ValueError(f"unknown collection template: {template}")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    plat = detect_platform()
    root = config_root(plat)
    print(f"platform: {plat}")
    print(f"config_dir: {root} (exists={root.exists()})")
    ver = obs_version()
    print(f"obs_version: {ver or 'NOT INSTALLED'}")

    gini = global_ini_path(plat)
    cur_profile = cur_collection = None
    if gini.exists():
        cp = load_ini(gini)
        if cp.has_section("Basic"):
            cur_profile = cp["Basic"].get("Profile")
            cur_collection = cp["Basic"].get("SceneCollection")
    print(f"current_profile: {cur_profile or '(unset)'}")
    print(f"current_collection: {cur_collection or '(unset)'}")

    pdir = profiles_dir(plat)
    sdir = scenes_dir(plat)
    profiles = sorted(p.name for p in pdir.iterdir()) if pdir.exists() else []
    collections = sorted(p.stem for p in sdir.glob("*.json")) if sdir.exists() else []
    print(f"profiles ({len(profiles)}): {', '.join(profiles) or '(none)'}")
    print(f"collections ({len(collections)}): {', '.join(collections) or '(none)'}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    plat = args.platform
    if plat == "auto":
        plat = detect_platform()

    if plat == "mac":
        cmd = ["brew", "install", "--cask", "obs"]
    elif plat == "win":
        cmd = ["winget", "install", "-e", "--id", "OBSProject.OBSStudio"]
    elif plat == "linux":
        # Prefer flatpak if present
        if shutil.which("flatpak"):
            cmd = ["flatpak", "install", "-y", "flathub", "com.obsproject.Studio"]
        elif shutil.which("apt-get"):
            cmd = [
                "bash",
                "-c",
                "sudo add-apt-repository -y ppa:obsproject/obs-studio && "
                "sudo apt-get update && sudo apt-get install -y obs-studio",
            ]
        else:
            print(
                "error: no supported installer on this Linux (need flatpak or apt)",
                file=sys.stderr,
            )
            return 2
    else:
        print(f"error: unsupported platform {plat!r}", file=sys.stderr)
        return 2

    print("install command:", " ".join(cmd))
    if args.dry_run:
        return 0
    try:
        r = subprocess.run(cmd)
        return r.returncode
    except FileNotFoundError as e:
        print(f"error: installer not found: {e}", file=sys.stderr)
        return 127


def cmd_profile_list(args: argparse.Namespace) -> int:
    pdir = profiles_dir()
    if not pdir.exists():
        print("(no profiles dir)")
        return 0
    for p in sorted(pdir.iterdir()):
        if p.is_dir():
            print(p.name)
    return 0


def cmd_profile_create(args: argparse.Namespace) -> int:
    name = args.name
    template = args.template
    if template not in PROFILE_TEMPLATES:
        print(
            f"error: unknown template {template!r}; available: "
            f"{', '.join(PROFILE_TEMPLATES)}",
            file=sys.stderr,
        )
        return 2
    pdir = profiles_dir() / name
    if pdir.exists() and not args.force:
        print(
            f"error: profile {name!r} already exists (use --force to overwrite)",
            file=sys.stderr,
        )
        return 1
    ensure_dir(pdir, dry_run=args.dry_run, verbose=args.verbose)

    tpl = PROFILE_TEMPLATES[template]
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    for section, kv in tpl.items():
        cp[section] = {k: (name if v == "__NAME__" else v) for k, v in kv.items()}
    save_ini(cp, pdir / "basic.ini", dry_run=args.dry_run, verbose=args.verbose)

    # Default encoder JSONs (x264)
    write_json(
        pdir / "streamEncoder.json",
        ENCODER_DEFAULTS["x264"],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    write_json(
        pdir / "recordEncoder.json",
        ENCODER_DEFAULTS["x264"],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    print(f"created profile {name!r} at {pdir}")
    return 0


def cmd_profile_delete(args: argparse.Namespace) -> int:
    pdir = profiles_dir() / args.name
    if not pdir.exists():
        print(f"error: profile {args.name!r} does not exist", file=sys.stderr)
        return 1
    log(args.verbose, f"rm -rf {pdir}")
    if not args.dry_run:
        shutil.rmtree(pdir)
    print(f"deleted profile {args.name!r}")
    return 0


def _set_global_basic(key: str, value: str, dry_run: bool, verbose: bool) -> None:
    gini = global_ini_path()
    cp = load_ini(gini)
    if not cp.has_section("Basic"):
        cp["Basic"] = {}
    cp["Basic"][key] = value
    save_ini(cp, gini, dry_run=dry_run, verbose=verbose)


def cmd_profile_set_default(args: argparse.Namespace) -> int:
    pdir = profiles_dir() / args.name
    if not pdir.exists():
        print(f"error: profile {args.name!r} does not exist", file=sys.stderr)
        return 1
    _set_global_basic("Profile", args.name, args.dry_run, args.verbose)
    _set_global_basic("ProfileDir", args.name, args.dry_run, args.verbose)
    print(f"default profile set to {args.name!r}")
    return 0


def cmd_collection_list(args: argparse.Namespace) -> int:
    sdir = scenes_dir()
    if not sdir.exists():
        print("(no scenes dir)")
        return 0
    for p in sorted(sdir.glob("*.json")):
        print(p.stem)
    return 0


def cmd_collection_create(args: argparse.Namespace) -> int:
    sdir = scenes_dir()
    ensure_dir(sdir, dry_run=args.dry_run, verbose=args.verbose)
    target = sdir / f"{args.name}.json"
    if target.exists() and not args.force:
        print(
            f"error: collection {args.name!r} already exists (use --force)",
            file=sys.stderr,
        )
        return 1
    data = scene_template(args.name, args.template)
    write_json(target, data, dry_run=args.dry_run, verbose=args.verbose)
    print(f"created collection {args.name!r} at {target}")
    return 0


def cmd_collection_delete(args: argparse.Namespace) -> int:
    target = scenes_dir() / f"{args.name}.json"
    if not target.exists():
        print(f"error: collection {args.name!r} does not exist", file=sys.stderr)
        return 1
    log(args.verbose, f"rm {target}")
    if not args.dry_run:
        target.unlink()
    print(f"deleted collection {args.name!r}")
    return 0


def cmd_collection_set_default(args: argparse.Namespace) -> int:
    target = scenes_dir() / f"{args.name}.json"
    if not target.exists():
        print(f"error: collection {args.name!r} does not exist", file=sys.stderr)
        return 1
    _set_global_basic("SceneCollection", args.name, args.dry_run, args.verbose)
    _set_global_basic("SceneCollectionFile", args.name, args.dry_run, args.verbose)
    print(f"default collection set to {args.name!r}")
    return 0


def cmd_encoder_set(args: argparse.Namespace) -> int:
    if args.codec not in ENCODER_DEFAULTS:
        print(f"error: unknown codec {args.codec!r}", file=sys.stderr)
        return 2
    pdir = profiles_dir() / args.profile
    if not pdir.exists():
        print(f"error: profile {args.profile!r} not found", file=sys.stderr)
        return 1

    settings = dict(ENCODER_DEFAULTS[args.codec])
    if args.bitrate is not None:
        settings["bitrate"] = args.bitrate
    if args.preset is not None:
        settings["preset"] = args.preset

    targets: list[str]
    if args.target == "stream":
        targets = ["streamEncoder.json"]
    elif args.target == "record":
        targets = ["recordEncoder.json"]
    else:
        targets = ["streamEncoder.json", "recordEncoder.json"]

    for name in targets:
        write_json(pdir / name, settings, dry_run=args.dry_run, verbose=args.verbose)

    # Update basic.ini StreamEncoder/RecEncoder IDs
    ini = pdir / "basic.ini"
    cp = load_ini(ini)
    if not cp.has_section("Output"):
        cp["Output"] = {}
    enc_id = ENCODER_IDS[args.codec]
    if args.target in ("stream", "both"):
        cp["Output"]["StreamEncoder"] = enc_id
    if args.target in ("record", "both"):
        cp["Output"]["RecEncoder"] = enc_id
    save_ini(cp, ini, dry_run=args.dry_run, verbose=args.verbose)

    print(
        f"encoder set: profile={args.profile} codec={args.codec} "
        f"id={enc_id} target={args.target}"
    )
    return 0


def cmd_service_set(args: argparse.Namespace) -> int:
    pdir = profiles_dir() / args.profile
    if not pdir.exists():
        print(f"error: profile {args.profile!r} not found", file=sys.stderr)
        return 1
    if args.type == "rtmp_custom":
        svc = {
            "type": "rtmp_custom",
            "settings": {
                "server": args.server,
                "key": args.key,
                "use_auth": False,
            },
        }
    elif args.type == "rtmp_common":
        svc = {
            "type": "rtmp_common",
            "settings": {
                "service": args.service or "Twitch",
                "server": args.server or "auto",
                "key": args.key,
            },
        }
    else:
        print(f"error: unknown service type {args.type!r}", file=sys.stderr)
        return 2
    write_json(pdir / "service.json", svc, dry_run=args.dry_run, verbose=args.verbose)
    print(f"service set for profile {args.profile!r}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    pdir = profiles_dir() / args.profile
    if not pdir.exists():
        print(f"error: profile {args.profile!r} not found", file=sys.stderr)
        return 1
    out = Path(args.output)
    log(args.verbose, f"zip -> {out}")
    if args.dry_run:
        print(f"(dry-run) would write {out}")
        return 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pdir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f"profile/{f.relative_to(pdir)}")
        # Also include matching collection if one exists by same name
        coll = scenes_dir() / f"{args.profile}.json"
        if coll.exists():
            zf.write(coll, arcname=f"scenes/{coll.name}")
    print(f"exported {args.profile!r} -> {out}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    arc = Path(args.archive)
    if not arc.exists():
        print(f"error: archive not found: {arc}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(arc, "r") as zf:
        names = zf.namelist()
        profile_names = {
            n.split("/", 2)[1]
            for n in names
            if n.startswith("profile/") and "/" in n[8:]
        }
        # Best-effort: extract "profile/..." entries into a new profile dir
        # whose name is taken from the archive stem.
        prof_name = arc.stem
        dest_profile = profiles_dir() / prof_name
        ensure_dir(dest_profile, dry_run=args.dry_run, verbose=args.verbose)
        for n in names:
            if n.startswith("profile/") and not n.endswith("/"):
                rel = n[len("profile/") :]
                target = dest_profile / rel
                ensure_dir(target.parent, dry_run=args.dry_run, verbose=args.verbose)
                if not args.dry_run:
                    with zf.open(n) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            elif n.startswith("scenes/") and not n.endswith("/"):
                rel = n[len("scenes/") :]
                target = scenes_dir() / rel
                ensure_dir(target.parent, dry_run=args.dry_run, verbose=args.verbose)
                if not args.dry_run:
                    with zf.open(n) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    print(f"imported archive {arc} (profile={prof_name})")
    return 0


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obsconfig.py",
        description="Install OBS Studio and author its on-disk config.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="show actions without writing"
    )
    p.add_argument("--verbose", action="store_true", help="log every step to stderr")

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="report platform, config dir, profiles, collections")

    ins = sub.add_parser("install", help="install OBS for current platform")
    ins.add_argument(
        "--platform", choices=["auto", "mac", "win", "linux"], default="auto"
    )

    pp = sub.add_parser("profile", help="profile ops")
    pps = pp.add_subparsers(dest="profile_cmd", required=True)
    pps.add_parser("list")
    pc = pps.add_parser("create")
    pc.add_argument("--name", required=True)
    pc.add_argument(
        "--template", default="1080p60_stream", choices=sorted(PROFILE_TEMPLATES)
    )
    pc.add_argument("--force", action="store_true")
    pd = pps.add_parser("delete")
    pd.add_argument("--name", required=True)
    psd = pps.add_parser("set-default")
    psd.add_argument("--name", required=True)

    cc = sub.add_parser("collection", help="scene-collection ops")
    ccs = cc.add_subparsers(dest="collection_cmd", required=True)
    ccs.add_parser("list")
    ccc = ccs.add_parser("create")
    ccc.add_argument("--name", required=True)
    ccc.add_argument(
        "--template", default="blank", choices=["blank", "webcam", "browser-overlay"]
    )
    ccc.add_argument("--force", action="store_true")
    ccd = ccs.add_parser("delete")
    ccd.add_argument("--name", required=True)
    csd = ccs.add_parser("set-default")
    csd.add_argument("--name", required=True)

    en = sub.add_parser("encoder", help="encoder ops")
    ens = en.add_subparsers(dest="encoder_cmd", required=True)
    enset = ens.add_parser("set")
    enset.add_argument("--profile", required=True)
    enset.add_argument("--codec", required=True, choices=sorted(ENCODER_DEFAULTS))
    enset.add_argument("--bitrate", type=int, default=None)
    enset.add_argument("--preset", default=None)
    enset.add_argument("--target", choices=["stream", "record", "both"], default="both")

    sv = sub.add_parser("service", help="streaming service ops")
    svs = sv.add_subparsers(dest="service_cmd", required=True)
    svset = svs.add_parser("set")
    svset.add_argument("--profile", required=True)
    svset.add_argument("--type", required=True, choices=["rtmp_custom", "rtmp_common"])
    svset.add_argument(
        "--service",
        default=None,
        help="for rtmp_common: Twitch, YouTube - HLS, Facebook Live, ...",
    )
    svset.add_argument("--server", default=None)
    svset.add_argument("--key", required=True)

    ex = sub.add_parser(
        "export", help="export a profile (+ matching collection) to zip"
    )
    ex.add_argument("--profile", required=True)
    ex.add_argument("--output", required=True)

    im = sub.add_parser("import", help="import a profile+collection zip")
    im.add_argument("--archive", required=True)

    return p


DISPATCH = {
    "check": cmd_check,
    "install": cmd_install,
    ("profile", "list"): cmd_profile_list,
    ("profile", "create"): cmd_profile_create,
    ("profile", "delete"): cmd_profile_delete,
    ("profile", "set-default"): cmd_profile_set_default,
    ("collection", "list"): cmd_collection_list,
    ("collection", "create"): cmd_collection_create,
    ("collection", "delete"): cmd_collection_delete,
    ("collection", "set-default"): cmd_collection_set_default,
    ("encoder", "set"): cmd_encoder_set,
    ("service", "set"): cmd_service_set,
    "export": cmd_export,
    "import": cmd_import,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("check", "install", "export", "import"):
        fn = DISPATCH[args.command]
    elif args.command == "profile":
        fn = DISPATCH[("profile", args.profile_cmd)]
    elif args.command == "collection":
        fn = DISPATCH[("collection", args.collection_cmd)]
    elif args.command == "encoder":
        fn = DISPATCH[("encoder", args.encoder_cmd)]
    elif args.command == "service":
        fn = DISPATCH[("service", args.service_cmd)]
    else:
        print(f"unknown command: {args.command}", file=sys.stderr)
        return 2
    try:
        return fn(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
