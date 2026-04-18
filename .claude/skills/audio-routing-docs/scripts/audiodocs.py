#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""audiodocs.py — Search and fetch docs for system-level audio routing subsystems.

Covers four hosts:
  * docs.pipewire.org      — PipeWire (Linux)
  * jackaudio.org          — JACK Audio Connection Kit
  * developer.apple.com    — Apple Core Audio (archive + modern)
  * learn.microsoft.com    — Windows WASAPI / Core Audio APIs

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages under ~/.cache/audio-routing-docs/ for offline-fast repeat lookups.

Usage:
    audiodocs.py list-pages
    audiodocs.py fetch   --page pipewire-programs
    audiodocs.py search  --query "pw-link" [--page pipewire-programs]
    audiodocs.py section --page pipewire-programs --id pw-link
    audiodocs.py index
    audiodocs.py clear-cache

Override the cache location with the AUDIO_ROUTING_DOCS_CACHE env var.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA = "audio-routing-docs-skill/1.0 (Claude Code Agent Skill)"

# page name -> canonical URL. Four hosts, grouped by subsystem.
PAGES: dict[str, str] = {
    # ── PipeWire ───────────────────────────────────────────────────────────
    "pipewire-home": "https://docs.pipewire.org/",
    "pipewire-programs": "https://docs.pipewire.org/page_programs.html",
    "pipewire-man-pipewire": "https://docs.pipewire.org/page_man_pipewire_1.html",
    "pipewire-man-pw-cli": "https://docs.pipewire.org/page_man_pw-cli_1.html",
    "pipewire-man-pw-dump": "https://docs.pipewire.org/page_man_pw-dump_1.html",
    "pipewire-man-pw-link": "https://docs.pipewire.org/page_man_pw-link_1.html",
    "pipewire-man-pw-cat": "https://docs.pipewire.org/page_man_pw-cat_1.html",
    "pipewire-man-pw-top": "https://docs.pipewire.org/page_man_pw-top_1.html",
    "pipewire-man-pw-metadata": "https://docs.pipewire.org/page_man_pw-metadata_1.html",
    "pipewire-man-pw-loopback": "https://docs.pipewire.org/page_man_pw-loopback_1.html",
    "pipewire-man-pw-midiplay": "https://docs.pipewire.org/page_man_pw-midiplay_1.html",
    "pipewire-man-pw-midirecord": "https://docs.pipewire.org/page_man_pw-midirecord_1.html",
    "pipewire-man-pw-jack": "https://docs.pipewire.org/page_man_pw-jack_1.html",
    "pipewire-man-pw-mon": "https://docs.pipewire.org/page_man_pw-mon_1.html",
    "pipewire-man-pw-profiler": "https://docs.pipewire.org/page_man_pw-profiler_1.html",
    "pipewire-man-pw-reserve": "https://docs.pipewire.org/page_man_pw-reserve_1.html",
    "pipewire-man-pw-config": "https://docs.pipewire.org/page_man_pw-config_1.html",
    "wireplumber-home": "https://pipewire.pages.freedesktop.org/wireplumber/",
    # ── JACK ───────────────────────────────────────────────────────────────
    "jack-home": "https://jackaudio.org/",
    "jack-api": "https://jackaudio.org/api/",
    "jack-faq": "https://jackaudio.org/faq/",
    "jack-stanford": "https://ccrma.stanford.edu/docs/common/JACK.html",
    "jacktrip-docs": "https://jacktrip.github.io/jacktrip/",
    "jacktrip-github": "https://github.com/jacktrip/jacktrip",
    # ── Apple Core Audio ───────────────────────────────────────────────────
    "coreaudio-overview": "https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/WhatisCoreAudio/WhatisCoreAudio.html",
    "coreaudio-essentials": "https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/CoreAudioEssentials/CoreAudioEssentials.html",
    "coreaudio-frameworks": "https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/CoreAudioFrameworks/CoreAudioFrameworks.html",
    "coreaudio-glossary": "https://developer.apple.com/library/archive/documentation/MusicAudio/Reference/CoreAudioGlossary/Glossary/core_audio_glossary.html",
    "coreaudio-modern": "https://developer.apple.com/documentation/coreaudio",
    "switchaudio-osx": "https://github.com/deweller/switchaudio-osx",
    "blackhole-github": "https://github.com/ExistentialAudio/BlackHole",
    # ── Windows WASAPI ─────────────────────────────────────────────────────
    "wasapi-overview": "https://learn.microsoft.com/en-us/windows/win32/coreaudio/about-the-windows-core-audio-apis",
    "wasapi-spec": "https://learn.microsoft.com/en-us/windows/win32/coreaudio/wasapi",
    "wasapi-exclusive": "https://learn.microsoft.com/en-us/windows/win32/coreaudio/exclusive-mode-streams",
    "wasapi-device-formats": "https://learn.microsoft.com/en-us/windows/win32/coreaudio/device-formats",
    "wasapi-mmdevice": "https://learn.microsoft.com/en-us/windows/win32/coreaudio/mmdevice-api",
    "wasapi-soundvolumeview": "https://www.nirsoft.net/utils/sound_volume_view.html",
    "wasapi-svcl": "https://www.nirsoft.net/utils/sound_volume_command_line.html",
    "wasapi-audiodevicecmdlets": "https://github.com/frgnca/AudioDeviceCmdlets",
    "wasapi-vbcable": "https://vb-audio.com/Cable/",
    "wasapi-voicemeeter": "https://voicemeeter.com/",
}

CACHE_DIR = Path(
    os.environ.get(
        "AUDIO_ROUTING_DOCS_CACHE", Path.home() / ".cache" / "audio-routing-docs"
    )
)


class TextExtractor(HTMLParser):
    """Convert HTML doc pages into searchable text (headings, dt/dd, code, lists)."""

    SKIP_TAGS = {"script", "style", "nav", "footer"}
    HEAD_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.buf: list[str] = []
        self.skip = 0
        self.in_pre = 0
        self.pending_anchor: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag in self.SKIP_TAGS:
            self.skip += 1
            return
        if tag == "a":
            anchor = a.get("name") or a.get("id")
            if anchor:
                self.pending_anchor = anchor
        if tag in self.HEAD_TAGS:
            lvl = self.HEAD_TAGS[tag]
            anchor = a.get("id") or self.pending_anchor
            self.buf.append("\n\n" + "#" * lvl + " ")
            if anchor:
                self.buf.append(f"[§{anchor}] ")
                self.pending_anchor = None
        elif tag == "pre":
            self.in_pre += 1
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "dt":
            self.buf.append("\n\n**")
        elif tag == "dd":
            self.buf.append("** — ")
        elif tag in ("p", "div"):
            self.buf.append("\n\n")
        elif tag == "li":
            self.buf.append("\n- ")
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "pre":
            self.in_pre = max(0, self.in_pre - 1)
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "dd":
            self.buf.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        self.buf.append(data)

    def text(self) -> str:
        out = "".join(self.buf)
        out = re.sub(r"\n{3,}", "\n\n", out)
        out = re.sub(r"[ \t]+\n", "\n", out)
        return out.strip()


def fetch_url(url: str, verbose: bool = False) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if verbose:
        print(f"[fetch] {url}", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def cache_path(page: str) -> Path:
    return CACHE_DIR / f"{page}.txt"


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    if page not in PAGES:
        raise ValueError(
            f"unknown page: {page!r}. Run `audiodocs.py list-pages` to see valid names."
        )
    cp = cache_path(page)
    if cp.exists() and not no_cache:
        return cp.read_text(encoding="utf-8")
    html = fetch_url(PAGES[page], verbose=verbose)
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(n) for n in PAGES)
    # Group output by host for readability.
    groups: dict[str, list[tuple[str, str]]] = {}
    for name, url in PAGES.items():
        host = url.split("/")[2]
        groups.setdefault(host, []).append((name, url))
    for host in sorted(groups):
        print(f"\n# {host}")
        for name, url in sorted(groups[host]):
            print(f"  {name:{width}s}  {url}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    text = load_or_fetch(args.page, no_cache=args.no_cache, verbose=args.verbose)
    if args.format == "json":
        print(
            json.dumps(
                {"page": args.page, "url": PAGES[args.page], "text": text},
                indent=2,
            )
        )
    else:
        print(text)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    failed: list[tuple[str, str]] = []
    for page in PAGES:
        print(f"indexing {page}...", file=sys.stderr)
        try:
            load_or_fetch(page, no_cache=True, verbose=args.verbose)
            time.sleep(0.4)
        except Exception as e:  # noqa: BLE001
            failed.append((page, str(e)))
            print(f"  failed: {e}", file=sys.stderr)
    print(f"\ndone; cache at {CACHE_DIR}", file=sys.stderr)
    if failed:
        print(f"{len(failed)} page(s) failed to index:", file=sys.stderr)
        for page, err in failed:
            print(f"  {page}: {err}", file=sys.stderr)
        return 1
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    if args.regex:
        pattern = re.compile(args.query, re.IGNORECASE)
    else:
        pattern = re.compile(re.escape(args.query), re.IGNORECASE)
    pages = [args.page] if args.page else list(PAGES)
    hits: list[dict] = []
    for page in pages:
        try:
            text = load_or_fetch(page, verbose=args.verbose)
        except Exception as e:  # noqa: BLE001
            if args.verbose:
                print(f"skip {page}: {e}", file=sys.stderr)
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - args.context)
                end = min(len(lines), i + args.context + 1)
                snippet = "\n".join(lines[start:end])
                heading = ""
                anchor = ""
                for j in range(i, -1, -1):
                    if lines[j].startswith("#"):
                        heading = lines[j].strip()
                        m = re.search(r"\[§([^\]]+)\]", heading)
                        if m:
                            anchor = m.group(1)
                        break
                url = PAGES[page]
                if anchor:
                    url += f"#{anchor}"
                hits.append(
                    {
                        "page": page,
                        "line": i + 1,
                        "heading": heading,
                        "anchor": anchor,
                        "url": url,
                        "snippet": snippet,
                    }
                )
                if len(hits) >= args.limit:
                    break
        if len(hits) >= args.limit:
            break
    if args.format == "json":
        print(json.dumps(hits, indent=2))
    else:
        for h in hits:
            print(f"--- {h['page']}:{h['line']} — {h['heading']}")
            if h["url"]:
                print(h["url"])
            print(h["snippet"])
            print()
        print(f"[{len(hits)} hit(s) for {args.query!r}]", file=sys.stderr)
    return 0 if hits else 1


def cmd_section(args: argparse.Namespace) -> int:
    text = load_or_fetch(args.page, verbose=args.verbose)
    lines = text.splitlines()
    start: int | None = None
    target = f"[§{args.id}]"
    for i, line in enumerate(lines):
        if target in line:
            start = i
            break
    if start is None:
        pat = re.compile(re.escape(args.id), re.IGNORECASE)
        for i, line in enumerate(lines):
            if line.startswith("#") and pat.search(line):
                start = i
                break
    if start is None:
        print(f"section not found: {args.id!r} on page {args.page!r}", file=sys.stderr)
        return 1
    m = re.match(r"^(#+)\s", lines[start])
    lvl = len(m.group(1)) if m else 1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        mm = re.match(r"^(#+)\s", lines[j])
        if mm and len(mm.group(1)) <= lvl:
            end = j
            break
    print("\n".join(lines[start:end]))
    return 0


def cmd_clear_cache(args: argparse.Namespace) -> int:
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"cleared {CACHE_DIR}", file=sys.stderr)
    else:
        print(f"nothing to clear ({CACHE_DIR} does not exist)", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search and fetch docs for PipeWire / JACK / CoreAudio / WASAPI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known doc pages grouped by host")
    p1.add_argument("--verbose", action="store_true")
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page as text")
    p2.add_argument("--page", required=True, help="page name (see list-pages)")
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true", help="re-fetch, bypass cache")
    p2.add_argument(
        "--dry-run",
        action="store_true",
        help="print the URL that would be fetched without hitting the network",
    )
    p2.add_argument("--verbose", action="store_true")
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every known page into the cache")
    p3.add_argument(
        "--dry-run",
        action="store_true",
        help="list the URLs that would be fetched without hitting the network",
    )
    p3.add_argument("--verbose", action="store_true")
    p3.set_defaults(fn=cmd_index)

    p4 = sub.add_parser("search", help="search for a term across cached pages")
    p4.add_argument("--query", required=True, help="text (or regex with --regex)")
    p4.add_argument("--page", help="limit to one page; default: search all pages")
    p4.add_argument("--regex", action="store_true", help="treat --query as a regex")
    p4.add_argument(
        "--context",
        type=int,
        default=3,
        help="lines of context around each hit (default: 3)",
    )
    p4.add_argument(
        "--limit", type=int, default=20, help="max hits to return (default: 20)"
    )
    p4.add_argument("--format", choices=["text", "json"], default="text")
    p4.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be searched without running",
    )
    p4.add_argument("--verbose", action="store_true")
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser(
        "section", help="extract one section by anchor id or heading keyword"
    )
    p5.add_argument("--page", required=True)
    p5.add_argument(
        "--id", required=True, help="anchor id (e.g. pw-link) or heading keyword"
    )
    p5.add_argument("--dry-run", action="store_true")
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p6.add_argument("--dry-run", action="store_true")
    p6.add_argument("--verbose", action="store_true")
    p6.set_defaults(fn=cmd_clear_cache)

    return p


def main() -> int:
    args = build_parser().parse_args()
    # --dry-run: just print what we would do and exit 0.
    if getattr(args, "dry_run", False):
        if args.cmd == "fetch":
            print(f"+ GET {PAGES[args.page]}", file=sys.stderr)
        elif args.cmd == "index":
            for page, url in PAGES.items():
                print(f"+ GET {url}  ({page})", file=sys.stderr)
        elif args.cmd == "search":
            target = args.page or "all pages"
            print(f"+ search {args.query!r} across {target}", file=sys.stderr)
        elif args.cmd == "section":
            print(f"+ section {args.id!r} on {PAGES[args.page]}", file=sys.stderr)
        elif args.cmd == "clear-cache":
            print(f"+ rm -rf {CACHE_DIR}", file=sys.stderr)
        return 0
    try:
        return args.fn(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
