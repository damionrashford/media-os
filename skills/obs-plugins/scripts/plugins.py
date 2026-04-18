#!/usr/bin/env python3
"""
plugins.py — OBS plugin authoring + ecosystem CLI.

Stdlib only. Non-interactive. Supports --dry-run and --verbose.

Subcommands:
    check              Report git/cmake/OBS install and plugins dir.
    scaffold           Clone obs-plugintemplate and apply substitutions.
    build              Configure + build the plugin with CMake presets.
    install-local      Copy the built artifact into the user plugins dir.
    list-installed     Enumerate installed plugins.
    install-community  Download + install a well-known community plugin.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------

COMMUNITY_PLUGINS: dict[str, dict] = {
    "obs-websocket": {
        "repo": "obsproject/obs-websocket",
        "note": "Bundled in OBS 28+ (Tools menu). Only install for pre-28.",
    },
    "streamfx": {
        "repo": "Xaymar/obs-StreamFX",
        "note": "Archived upstream. Community forks exist; verify before use.",
    },
    "asc": {
        "repo": "WarmUpTill/SceneSwitcher",
        "note": "Advanced Scene Switcher: macro-based scene automation.",
    },
    "move": {
        "repo": "exeldro/obs-move-transition",
        "note": "Animated filter value transitions.",
    },
    "ndi": {
        "repo": "obs-ndi/obs-ndi",
        "note": "Requires NDI Runtime installed separately (https://ndi.video/sdk).",
    },
    "source-record": {
        "repo": "exeldro/obs-source-record",
        "note": "Per-source recording.",
    },
    "backtrack": {
        "repo": "exeldro/obs-backtrack",
        "note": "Instant-replay time-shift buffer.",
    },
}

# ---------------------------------------------------------------------------
# platform helpers


def detect_platform() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return "linux"


def plugins_dir(plat: str) -> Path:
    home = Path.home()
    if plat == "macos":
        return home / "Library/Application Support/obs-studio/plugins"
    if plat == "windows":
        appdata = os.environ.get("APPDATA") or str(home / "AppData/Roaming")
        return Path(appdata) / "obs-studio" / "plugins"
    return home / ".config/obs-studio/plugins"


def cmake_preset(plat: str) -> str:
    if plat == "macos":
        return "macos"
    if plat == "windows":
        return "windows-x64"
    return "ubuntu-x86_64"


def obs_install_hint(plat: str) -> str | None:
    """Best-effort location of the OBS executable. Returns None if not found."""
    candidates: list[Path] = []
    if plat == "macos":
        candidates = [Path("/Applications/OBS.app")]
    elif plat == "windows":
        candidates = [
            Path("C:/Program Files/obs-studio/bin/64bit/obs64.exe"),
            Path("C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe"),
        ]
    else:
        for n in ("obs",):
            w = shutil.which(n)
            if w:
                return w
        candidates = [
            Path("/usr/bin/obs"),
            Path("/usr/local/bin/obs"),
            Path("/var/lib/flatpak/exports/bin/com.obsproject.Studio"),
        ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


# ---------------------------------------------------------------------------
# utility


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg, file=sys.stderr)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    pretty = " ".join(cmd)
    if dry_run:
        print(f"[dry-run] {pretty}{' (cwd=' + str(cwd) + ')' if cwd else ''}")
        return 0
    if verbose:
        log(f"$ {pretty}{' (cwd=' + str(cwd) + ')' if cwd else ''}")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return proc.returncode


def which_ok(bin_name: str) -> str | None:
    return shutil.which(bin_name)


def http_get_json(url: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "obs-plugins-skill/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_download(url: str, dst: Path, verbose: bool = False) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "obs-plugins-skill/1.0"})
    if verbose:
        log(f"downloading {url}")
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


# ---------------------------------------------------------------------------
# check


def cmd_check(args: argparse.Namespace) -> int:
    plat = detect_platform()
    print(f"Platform:       {plat}")
    for tool in ("git", "cmake", "curl"):
        w = which_ok(tool)
        print(f"{tool+':':15} {w or '(missing)'}")
    obs = obs_install_hint(plat)
    print(f"OBS install:    {obs or '(not auto-detected)'}")
    pdir = plugins_dir(plat)
    print(f"Plugins dir:    {pdir}")
    print(f"Dir exists:     {pdir.exists()}")
    return 0


# ---------------------------------------------------------------------------
# scaffold

BUILDSPEC_PATCHES = [
    ("name", lambda v, ns: ns.name),
    ("displayName", lambda v, ns: ns.name),
    ("version", lambda v, ns: ns.version),
    ("author", lambda v, ns: ns.author),
    ("website", lambda v, ns: ns.website or v),
    ("email", lambda v, ns: ns.email or v),
    ("description", lambda v, ns: ns.description),
    ("id", lambda v, ns: ns.bundle_id),
    ("bundleId", lambda v, ns: ns.bundle_id),
]


def _patch_buildspec(path: Path, ns: argparse.Namespace) -> None:
    data = json.loads(path.read_text())
    for key, transform in BUILDSPEC_PATCHES:
        if key in data:
            try:
                data[key] = transform(data[key], ns)
            except Exception:
                pass
    path.write_text(json.dumps(data, indent=2) + "\n")


def _patch_file_substr(path: Path, needle: str, replacement: str) -> None:
    if not path.exists():
        return
    text = path.read_text()
    new = text.replace(needle, replacement)
    if new != text:
        path.write_text(new)


def cmd_scaffold(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir).expanduser().resolve()
    dst = outdir / args.name
    if dst.exists():
        print(f"error: {dst} already exists", file=sys.stderr)
        return 2
    outdir.mkdir(parents=True, exist_ok=True)

    repo = "https://github.com/obsproject/obs-plugintemplate.git"
    rc = run(
        ["git", "clone", "--depth=1", repo, str(dst)],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc

    if args.dry_run:
        print(f"[dry-run] would patch buildspec.json in {dst}")
        return 0

    # Drop template .git history so user can init their own.
    shutil.rmtree(dst / ".git", ignore_errors=True)

    bspec = dst / "buildspec.json"
    if bspec.exists():
        _patch_buildspec(bspec, args)

    # Replace common literal identifier "obs-plugintemplate" in CMake files.
    for p in [dst / "CMakeLists.txt", dst / "CMakePresets.json"]:
        _patch_file_substr(p, "obs-plugintemplate", args.name)

    # Seed locale
    locale = dst / "data" / "locale" / "en-US.ini"
    if locale.exists():
        locale.write_text(f'{args.name}="{args.description}"\n')

    print(f"scaffolded {dst}")
    print(
        f"next: cd {dst} && ./.github/scripts/bootstrap.sh   # then: see 'build' subcommand"
    )
    return 0


# ---------------------------------------------------------------------------
# build


def cmd_build(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    if not (path / "CMakePresets.json").exists():
        print(f"error: no CMakePresets.json in {path}", file=sys.stderr)
        return 2
    plat = args.platform if args.platform != "auto" else detect_platform()
    preset = cmake_preset(plat)
    rc = run(
        ["cmake", "--preset", preset],
        cwd=path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if rc != 0:
        return rc
    return run(
        ["cmake", "--build", "--preset", preset, "--config", "RelWithDebInfo"],
        cwd=path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


# ---------------------------------------------------------------------------
# install-local


def _find_built_artifact(path: Path, plat: str) -> Path | None:
    if plat == "macos":
        # Prefer a .plugin bundle if one was produced.
        for p in path.rglob("*.plugin"):
            if p.is_dir():
                return p
        for p in path.rglob("*.dylib"):
            return p
    elif plat == "windows":
        for p in path.rglob("*.dll"):
            if "RelWithDebInfo" in str(p) or "build_x64" in str(p):
                return p
        for p in path.rglob("*.dll"):
            return p
    else:
        for p in path.rglob("*.so"):
            return p
    return None


def cmd_install_local(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    plat = detect_platform()
    art = _find_built_artifact(path, plat)
    if not art:
        print(f"error: no built artifact found under {path}", file=sys.stderr)
        return 2
    pdir = plugins_dir(plat)
    pdir.mkdir(parents=True, exist_ok=True)
    name = path.name

    if plat == "macos" and art.suffix == ".plugin":
        dest = pdir / art.name
        if args.dry_run:
            print(f"[dry-run] copytree {art} -> {dest}")
            return 0
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(art, dest, symlinks=True)
        print(f"installed: {dest}")
        return 0

    # Linux/Windows/dylib layouts -> <plugins>/<name>/bin/64bit/<artifact> plus data/
    base = pdir / name
    binsub = base / "bin" / "64bit"
    datasub = base / "data"
    if args.dry_run:
        print(f"[dry-run] mkdir {binsub} {datasub}")
        print(f"[dry-run] copy  {art} -> {binsub / art.name}")
        return 0
    binsub.mkdir(parents=True, exist_ok=True)
    datasub.mkdir(parents=True, exist_ok=True)
    shutil.copy2(art, binsub / art.name)
    # Copy data/ tree if present in source.
    src_data = path / "data"
    if src_data.exists():
        for item in src_data.iterdir():
            tgt = datasub / item.name
            if item.is_dir():
                if tgt.exists():
                    shutil.rmtree(tgt)
                shutil.copytree(item, tgt)
            else:
                shutil.copy2(item, tgt)
    print(f"installed: {binsub / art.name}")
    return 0


# ---------------------------------------------------------------------------
# list-installed


def cmd_list_installed(args: argparse.Namespace) -> int:
    plat = detect_platform()
    pdir = plugins_dir(plat)
    if not pdir.exists():
        print(f"(no plugins dir at {pdir})")
        return 0
    entries = sorted(pdir.iterdir())
    if not entries:
        print(f"(empty: {pdir})")
        return 0
    print(f"Plugins in {pdir}:")
    for e in entries:
        suffix = "/" if e.is_dir() else ""
        print(f"  {e.name}{suffix}")
    return 0


# ---------------------------------------------------------------------------
# install-community

_ASSET_PATTERNS = {
    # Very rough regex ranking per platform. First match wins.
    "macos": [
        re.compile(
            r"(?i)(macos|mac|darwin|apple|osx).*\.(pkg|dmg|zip|tar\.gz|tar\.xz)$"
        ),
        re.compile(r"(?i).*(macos|mac|darwin|apple|osx).*"),
    ],
    "windows": [
        re.compile(r"(?i)(windows|win(64|x64|_x64)?|amd64).*\.(exe|msi|zip)$"),
        re.compile(r"(?i).*(windows|win64|win).*"),
    ],
    "linux": [
        re.compile(
            r"(?i)(ubuntu|debian|linux).*\.(deb|tar\.gz|tar\.xz|zip|AppImage|rpm)$"
        ),
        re.compile(r"(?i).*(ubuntu|linux|debian).*"),
    ],
}


def _pick_asset(assets: list[dict], plat: str) -> dict | None:
    for pat in _ASSET_PATTERNS.get(plat, []):
        for a in assets:
            if pat.search(a.get("name", "")):
                return a
    return None


def cmd_install_community(args: argparse.Namespace) -> int:
    key = args.plugin
    meta = COMMUNITY_PLUGINS.get(key)
    if not meta:
        print(
            f"unknown plugin key: {key}. choices: {', '.join(sorted(COMMUNITY_PLUGINS))}",
            file=sys.stderr,
        )
        return 2
    plat = detect_platform()
    api = f"https://api.github.com/repos/{meta['repo']}/releases/latest"
    print(f"plugin:  {key}  ({meta['repo']})")
    print(f"note:    {meta['note']}")
    print(f"release: {api}")
    if args.dry_run:
        return 0
    try:
        rel = http_get_json(api)
    except urllib.error.HTTPError as e:
        print(f"error: GitHub API {e.code} for {api}", file=sys.stderr)
        return 3
    assets = rel.get("assets", []) if isinstance(rel, dict) else []
    asset = _pick_asset(assets, plat)
    if not asset:
        print("no matching asset found for this platform. Asset list:")
        for a in assets:
            print(f"  - {a.get('name')}  {a.get('browser_download_url')}")
        print(
            "manual install: download the correct asset and extract into the plugins dir."
        )
        return 4
    url = asset["browser_download_url"]
    name = asset["name"]
    suffix = name.lower()
    print(f"asset:   {name}")
    print(f"url:     {url}")
    # Package installers we do not auto-run (.pkg, .exe, .msi, .dmg, .deb, .rpm, .AppImage)
    needs_manual = any(
        suffix.endswith(ext)
        for ext in (".pkg", ".dmg", ".exe", ".msi", ".deb", ".rpm", ".appimage")
    )
    with tempfile.TemporaryDirectory(prefix="obs-plugin-") as td:
        dst = Path(td) / name
        http_download(url, dst, verbose=args.verbose)
        if needs_manual:
            # Copy to CWD for user to run.
            final = Path.cwd() / name
            shutil.copy2(dst, final)
            print(f"downloaded installer to {final}")
            print(
                "run the installer manually (installer-based; script won't auto-execute)."
            )
            return 0
        # Archives: extract into plugins dir under a subdir named after the plugin key.
        target = plugins_dir(plat) / key
        target.mkdir(parents=True, exist_ok=True)
        if suffix.endswith(".zip"):
            import zipfile

            with zipfile.ZipFile(dst) as z:
                z.extractall(target)
        elif suffix.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
            import tarfile

            with tarfile.open(dst) as t:
                t.extractall(target)
        else:
            # Unknown format: save to plugins dir and bail.
            shutil.copy2(dst, target / name)
            print(f"saved raw asset at {target / name}; extract manually.")
            return 0
    print(f"extracted to {target}")
    return 0


# ---------------------------------------------------------------------------
# argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="plugins.py", description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="report environment + plugins dir")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("scaffold", help="clone obs-plugintemplate and patch metadata")
    sp.add_argument("--name", required=True)
    sp.add_argument("--author", required=True)
    sp.add_argument("--bundle-id", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument("--outdir", required=True)
    sp.add_argument("--version", default="0.1.0")
    sp.add_argument("--website", default="")
    sp.add_argument("--email", default="")
    sp.set_defaults(func=cmd_scaffold)

    sp = sub.add_parser("build", help="run cmake configure + build for the plugin")
    sp.add_argument("--path", required=True)
    sp.add_argument(
        "--platform", default="auto", choices=["auto", "macos", "windows", "linux"]
    )
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser(
        "install-local", help="copy built artifact into user plugins dir"
    )
    sp.add_argument("--path", required=True)
    sp.set_defaults(func=cmd_install_local)

    sp = sub.add_parser("list-installed", help="enumerate installed plugins")
    sp.set_defaults(func=cmd_list_installed)

    sp = sub.add_parser(
        "install-community", help="download + install a community plugin"
    )
    sp.add_argument("--plugin", required=True, choices=sorted(COMMUNITY_PLUGINS.keys()))
    sp.set_defaults(func=cmd_install_community)

    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
