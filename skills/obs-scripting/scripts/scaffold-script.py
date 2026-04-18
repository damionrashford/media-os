#!/usr/bin/env python3
"""Scaffold OBS Studio Python / Lua scripts. Stdlib only, non-interactive.

Subcommands:
    check                 Report OBS install, scripts dir, Python version.
    new-python            Write a canonical Python lifecycle skeleton.
    new-lua               Write a canonical Lua lifecycle skeleton.
    new-scene-switcher    Template: register hotkey + frontend event, switch scenes.
    new-hotkey            Template: register frontend hotkey with save/load.
    new-timer             Template: periodic task via timer_add.
    install               Copy/symlink a script into the OBS scripts dir.

Global flags: --dry-run, --verbose.
"""
from __future__ import annotations

import argparse
import configparser
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Platform helpers
# --------------------------------------------------------------------------- #


def _platform() -> str:
    s = sys.platform
    if s.startswith("darwin"):
        return "macos"
    if s.startswith("linux"):
        return "linux"
    if s.startswith("win") or s.startswith("cygwin"):
        return "windows"
    return s


def obs_config_dir() -> Path:
    """OBS user config root. Matches obs-config skill semantics."""
    p = _platform()
    if p == "macos":
        return Path.home() / "Library" / "Application Support" / "obs-studio"
    if p == "linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        return (
            Path(xdg) / "obs-studio" if xdg else Path.home() / ".config" / "obs-studio"
        )
    if p == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "obs-studio"
        return Path.home() / "AppData" / "Roaming" / "obs-studio"
    return Path.home() / ".config" / "obs-studio"


def obs_global_ini() -> Path:
    return obs_config_dir() / "global.ini"


def default_scripts_dir() -> Path:
    """Per-user convention — OBS itself doesn't pick one, but this is a stable
    place to drop scripts and point OBS at them."""
    p = _platform()
    if p == "macos":
        return (
            Path.home() / "Library" / "Application Support" / "obs-studio" / "scripts"
        )
    if p == "windows":
        return obs_config_dir() / "scripts"
    return obs_config_dir() / "scripts"


def find_obs_binary() -> str | None:
    p = _platform()
    if p == "macos":
        for cand in (
            "/Applications/OBS.app/Contents/MacOS/OBS",
            "/opt/homebrew/bin/obs",
            "/usr/local/bin/obs",
        ):
            if Path(cand).exists():
                return cand
    elif p == "linux":
        for cand in (
            "/usr/bin/obs",
            "/usr/local/bin/obs",
            "/var/lib/flatpak/exports/bin/com.obsproject.Studio",
        ):
            if Path(cand).exists():
                return cand
        found = shutil.which("obs")
        if found:
            return found
    elif p == "windows":
        for cand in (
            r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
        ):
            if Path(cand).exists():
                return cand
    return None


def detect_python_candidates() -> list[tuple[str, Path]]:
    """Locations OBS is likely to accept on the current platform. Prefer 3.11."""
    p = _platform()
    out: list[tuple[str, Path]] = []
    if p == "macos":
        bases = [
            "/Library/Frameworks/Python.framework/Versions/3.11",
            "/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11",
            "/usr/local/opt/python@3.11/Frameworks/Python.framework/Versions/3.11",
            "/Library/Frameworks/Python.framework/Versions/3.12",
            "/Library/Frameworks/Python.framework/Versions/3.10",
        ]
    elif p == "linux":
        bases = [
            "/usr/lib/python3.11",
            "/usr/lib64/python3.11",
            "/usr/lib/python3.12",
            "/usr/lib/python3.10",
        ]
    elif p == "windows":
        home = str(Path.home())
        bases = [
            rf"{home}\AppData\Local\Programs\Python\Python311",
            rf"{home}\AppData\Local\Programs\Python\Python312",
            rf"{home}\AppData\Local\Programs\Python\Python310",
            r"C:\Python311",
        ]
    else:
        bases = []
    for b in bases:
        pp = Path(b)
        if pp.exists():
            m = re.search(r"3\.(1[0-2])", str(pp))
            ver = f"3.{m.group(1)}" if m else "unknown"
            out.append((ver, pp))
    return out


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #

PY_SKELETON = '''"""{name} — OBS Python script.

Loaded via OBS: Tools -> Scripts -> +. Python version must match OBS's
compiled version (usually 3.11 on OBS 30+).
"""
import obspython as obs


# ---- module-level state that survives across callbacks ----
state = {{
    "greeting": "Hello",
    "count": 5,
}}


def script_description():
    return "{name}: a short description of what this script does."


def script_properties():
    # Called whenever the properties pane needs to repaint. Do not do
    # expensive work here; return a fresh obs_properties_t.
    p = obs.obs_properties_create()
    obs.obs_properties_add_text(p, "greeting", "Greeting", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(p, "count", "Count", 1, 100, 1)
    obs.obs_properties_add_button(p, "do_it", "Do It", on_button)
    return p


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "greeting", "Hello")
    obs.obs_data_set_default_int(settings, "count", 5)


def script_update(settings):
    # Fires on first load AND on every property change. Keep idempotent.
    state["greeting"] = obs.obs_data_get_string(settings, "greeting")
    state["count"] = obs.obs_data_get_int(settings, "count")


def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)


def script_unload():
    # Remove timers, disconnect signals, drop references you hold.
    pass


def script_save(settings):
    # Persist non-property state (e.g. hotkey bindings) here.
    pass


# ---- callbacks ----

def on_button(props, prop):
    obs.script_log(
        obs.LOG_INFO,
        f"Clicked; greeting={{state['greeting']!r}}, count={{state['count']}}",
    )
    # Return True to tell OBS to refresh the property pane.
    return False


def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
        scene = obs.obs_frontend_get_current_scene()
        if scene:
            name = obs.obs_source_get_name(scene)
            obs.obs_source_release(scene)  # MUST release.
            obs.script_log(obs.LOG_INFO, f"Scene changed: {{name}}")
'''


LUA_SKELETON = """-- {name} — OBS Lua script.
-- Loaded via OBS: Tools -> Scripts -> +.

obs = obslua

local state = {{
    greeting = "Hello",
    count = 5,
}}


function script_description()
    return "{name}: a short description of what this script does."
end


function script_properties()
    local p = obs.obs_properties_create()
    obs.obs_properties_add_text(p, "greeting", "Greeting", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(p, "count", "Count", 1, 100, 1)
    obs.obs_properties_add_button(p, "do_it", "Do It", on_button)
    return p
end


function script_defaults(settings)
    obs.obs_data_set_default_string(settings, "greeting", "Hello")
    obs.obs_data_set_default_int(settings, "count", 5)
end


function script_update(settings)
    state.greeting = obs.obs_data_get_string(settings, "greeting")
    state.count = obs.obs_data_get_int(settings, "count")
end


function script_load(settings)
    obs.obs_frontend_add_event_callback(on_event)
end


function script_unload()
end


function on_button(props, prop)
    obs.script_log(obs.LOG_INFO, string.format(
        "Clicked; greeting=%q count=%d", state.greeting, state.count))
    return false
end


function on_event(event)
    if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED then
        local scene = obs.obs_frontend_get_current_scene()
        if scene ~= nil then
            local name = obs.obs_source_get_name(scene)
            obs.obs_source_release(scene)
            obs.script_log(obs.LOG_INFO, "Scene changed: " .. name)
        end
    end
end
"""


SCENE_SWITCHER_TEMPLATE = '''"""scene_switcher — Switch to a chosen scene on a hotkey or when streaming stops.
"""
import obspython as obs

HOTKEY_ID = obs.OBS_INVALID_HOTKEY_ID
target_scene = ""
switch_on_stop = False


def script_description():
    return "Switch to a chosen scene via hotkey, or automatically when streaming stops."


def script_properties():
    p = obs.obs_properties_create()
    lst = obs.obs_properties_add_list(
        p, "target", "Target scene",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING,
    )
    scenes = obs.obs_frontend_get_scenes()
    if scenes is not None:
        for s in scenes:
            name = obs.obs_source_get_name(s)
            obs.obs_property_list_add_string(lst, name, name)
        obs.source_list_release(scenes)
    obs.obs_properties_add_bool(p, "switch_on_stop", "Also switch when streaming stops")
    return p


def script_defaults(settings):
    obs.obs_data_set_default_bool(settings, "switch_on_stop", False)


def script_update(settings):
    global target_scene, switch_on_stop
    target_scene = obs.obs_data_get_string(settings, "target")
    switch_on_stop = obs.obs_data_get_bool(settings, "switch_on_stop")


def script_load(settings):
    global HOTKEY_ID
    HOTKEY_ID = obs.obs_hotkey_register_frontend(
        "scene_switcher.switch", "Switch to target scene", on_hotkey,
    )
    arr = obs.obs_data_get_array(settings, "hotkey_scene_switcher.switch")
    obs.obs_hotkey_load(HOTKEY_ID, arr)
    obs.obs_data_array_release(arr)
    obs.obs_frontend_add_event_callback(on_event)


def script_save(settings):
    arr = obs.obs_hotkey_save(HOTKEY_ID)
    obs.obs_data_set_array(settings, "hotkey_scene_switcher.switch", arr)
    obs.obs_data_array_release(arr)


def _switch_to(name):
    if not name:
        return
    src = obs.obs_get_source_by_name(name)
    if src:
        obs.obs_frontend_set_current_scene(src)
        obs.obs_source_release(src)


def on_hotkey(pressed):
    if pressed:
        _switch_to(target_scene)


def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED and switch_on_stop:
        _switch_to(target_scene)
'''


HOTKEY_TEMPLATE = '''"""hotkey_demo — Register one OBS frontend hotkey with persistent binding.
"""
import obspython as obs

HOTKEY_ID = obs.OBS_INVALID_HOTKEY_ID
HOTKEY_KEY = "hotkey_demo.fire"


def script_description():
    return "Demonstrates registering a frontend hotkey that persists across OBS restarts."


def script_properties():
    p = obs.obs_properties_create()
    obs.obs_properties_add_text(
        p, "info", "Set the hotkey in OBS Settings -> Hotkeys -> Scripts.",
        obs.OBS_TEXT_INFO,
    )
    return p


def script_load(settings):
    global HOTKEY_ID
    HOTKEY_ID = obs.obs_hotkey_register_frontend(HOTKEY_KEY, "Fire demo action", on_hotkey)
    arr = obs.obs_data_get_array(settings, HOTKEY_KEY)
    obs.obs_hotkey_load(HOTKEY_ID, arr)
    obs.obs_data_array_release(arr)


def script_save(settings):
    arr = obs.obs_hotkey_save(HOTKEY_ID)
    obs.obs_data_set_array(settings, HOTKEY_KEY, arr)
    obs.obs_data_array_release(arr)


def on_hotkey(pressed):
    if pressed:
        obs.script_log(obs.LOG_INFO, "hotkey_demo: fired")
'''


TIMER_TEMPLATE = '''"""timer_demo — Periodic task via timer_add.

timer_add runs the callback on the OBS UI thread every N milliseconds.
Do NOT block inside it. To stop, call timer_remove with the same callable.
"""
import obspython as obs

INTERVAL_MS = 5000
_active = False


def script_description():
    return "Logs the current scene every 5 seconds while enabled."


def script_properties():
    p = obs.obs_properties_create()
    obs.obs_properties_add_bool(p, "enabled", "Enabled")
    obs.obs_properties_add_int(p, "interval_ms", "Interval (ms)", 250, 600_000, 250)
    return p


def script_defaults(settings):
    obs.obs_data_set_default_bool(settings, "enabled", True)
    obs.obs_data_set_default_int(settings, "interval_ms", INTERVAL_MS)


def script_update(settings):
    global _active, INTERVAL_MS
    enabled = obs.obs_data_get_bool(settings, "enabled")
    INTERVAL_MS = obs.obs_data_get_int(settings, "interval_ms")
    # Always remove before adding to avoid multiple registrations.
    if _active:
        obs.timer_remove(_tick)
        _active = False
    if enabled:
        obs.timer_add(_tick, INTERVAL_MS)
        _active = True


def script_unload():
    global _active
    if _active:
        obs.timer_remove(_tick)
        _active = False


def _tick():
    scene = obs.obs_frontend_get_current_scene()
    if scene:
        name = obs.obs_source_get_name(scene)
        obs.obs_source_release(scene)
        obs.script_log(obs.LOG_INFO, f"timer_demo: current scene = {name}")
'''


# --------------------------------------------------------------------------- #
# Command implementations
# --------------------------------------------------------------------------- #


def _write(path: Path, content: str, *, dry_run: bool, verbose: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {path} ({len(content)} bytes)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if verbose:
        print(f"wrote {path} ({len(content)} bytes)")
    else:
        print(f"wrote {path}")


def cmd_check(args: argparse.Namespace) -> int:
    print(f"platform           : {_platform()} ({platform.platform()})")
    binp = find_obs_binary()
    print(f"OBS binary         : {binp or '(not found)'}")
    cfg = obs_config_dir()
    print(f"OBS config dir     : {cfg}  {'[exists]' if cfg.exists() else '[missing]'}")
    ini = obs_global_ini()
    print(f"OBS global.ini     : {ini}  {'[exists]' if ini.exists() else '[missing]'}")
    sd = default_scripts_dir()
    print(f"suggested scripts  : {sd}  {'[exists]' if sd.exists() else '[missing]'}")
    cands = detect_python_candidates()
    print(f"python candidates  : {len(cands)}")
    for ver, pp in cands:
        print(f"  - {ver}: {pp}")
    if not cands:
        print(
            "  (no Python framework found at standard paths; install python.org 3.11)"
        )
    return 0


def cmd_new_python(args: argparse.Namespace) -> int:
    out = Path(args.outdir).expanduser() / f"{args.name}.py"
    _write(
        out,
        PY_SKELETON.format(name=args.name),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    return 0


def cmd_new_lua(args: argparse.Namespace) -> int:
    out = Path(args.outdir).expanduser() / f"{args.name}.lua"
    _write(
        out,
        LUA_SKELETON.format(name=args.name),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    return 0


def cmd_new_scene_switcher(args: argparse.Namespace) -> int:
    out = Path(args.outdir).expanduser() / "scene_switcher.py"
    _write(out, SCENE_SWITCHER_TEMPLATE, dry_run=args.dry_run, verbose=args.verbose)
    return 0


def cmd_new_hotkey(args: argparse.Namespace) -> int:
    out = Path(args.outdir).expanduser() / "hotkey_demo.py"
    _write(out, HOTKEY_TEMPLATE, dry_run=args.dry_run, verbose=args.verbose)
    return 0


def cmd_new_timer(args: argparse.Namespace) -> int:
    out = Path(args.outdir).expanduser() / "timer_demo.py"
    _write(out, TIMER_TEMPLATE, dry_run=args.dry_run, verbose=args.verbose)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    src = Path(args.script).expanduser().resolve()
    if not src.exists():
        print(f"error: source script not found: {src}", file=sys.stderr)
        return 2
    dest_dir = default_scripts_dir()
    dest = dest_dir / src.name
    if args.dry_run:
        print(f"[dry-run] would copy {src} -> {dest}")
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"copied {src} -> {dest}")

    if not args.auto_load:
        print(
            "\nNext step: open OBS -> Tools -> Scripts -> + and select the "
            f"file above. (Use --auto-load to edit global.ini now; note that "
            f"OBS overwrites global.ini at shutdown, so adding via the UI is "
            f"more reliable.)"
        )
        return 0

    ini = obs_global_ini()
    if not ini.exists():
        print(
            f"warning: {ini} does not exist yet. Launch OBS once to create it, "
            f"then re-run with --auto-load.",
            file=sys.stderr,
        )
        return 1

    cfg = configparser.ConfigParser()
    # OBS's global.ini is not strictly RFC INI but configparser handles it.
    try:
        cfg.read(ini, encoding="utf-8")
    except configparser.Error as e:
        print(f"error: could not parse {ini}: {e}", file=sys.stderr)
        return 3

    section = "ScriptsTool"
    key = "Scripts"
    existing = cfg.get(section, key, fallback="") if cfg.has_section(section) else ""
    entries = [e for e in existing.split(":") if e]
    dest_str = str(dest)
    if dest_str in entries:
        print(f"already registered in global.ini: {dest_str}")
    else:
        entries.append(dest_str)
        if not cfg.has_section(section):
            cfg.add_section(section)
        cfg.set(section, key, ":".join(entries))
        if args.dry_run:
            print(f"[dry-run] would add {dest_str} to [ScriptsTool] Scripts in {ini}")
        else:
            with ini.open("w", encoding="utf-8") as fh:
                cfg.write(fh, space_around_delimiters=False)
            print(f"registered {dest_str} in {ini} [ScriptsTool].Scripts")
            print(
                "NOTE: OBS may overwrite global.ini at shutdown. If the entry "
                "disappears, add the script via OBS UI instead (Tools -> Scripts -> +)."
            )
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--dry-run", action="store_true", help="Print what would happen; write nothing."
    )
    ap.add_argument("--verbose", action="store_true", help="More detailed output.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="Report OBS install, scripts dir, Python.")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser(
        "new-python", help="Write a canonical Python lifecycle skeleton."
    )
    sp.add_argument("--name", required=True, help="Script base name (no extension).")
    sp.add_argument("--outdir", required=True, help="Output directory.")
    sp.set_defaults(func=cmd_new_python)

    sp = sub.add_parser("new-lua", help="Write a canonical Lua lifecycle skeleton.")
    sp.add_argument("--name", required=True, help="Script base name (no extension).")
    sp.add_argument("--outdir", required=True, help="Output directory.")
    sp.set_defaults(func=cmd_new_lua)

    sp = sub.add_parser(
        "new-scene-switcher", help="Hotkey + frontend-event scene switch template."
    )
    sp.add_argument("--outdir", required=True, help="Output directory.")
    sp.set_defaults(func=cmd_new_scene_switcher)

    sp = sub.add_parser("new-hotkey", help="Frontend hotkey with save/load template.")
    sp.add_argument("--outdir", required=True, help="Output directory.")
    sp.set_defaults(func=cmd_new_hotkey)

    sp = sub.add_parser("new-timer", help="Periodic timer_add template.")
    sp.add_argument("--outdir", required=True, help="Output directory.")
    sp.set_defaults(func=cmd_new_timer)

    sp = sub.add_parser("install", help="Copy a script into the OBS scripts dir.")
    sp.add_argument("--script", required=True, help="Path to .py or .lua to install.")
    sp.add_argument(
        "--auto-load",
        action="store_true",
        help="Also edit global.ini to autoload (advanced; OBS may overwrite).",
    )
    sp.set_defaults(func=cmd_install)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
