#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""mtxdocs.py -- Search and fetch official MediaMTX documentation.

Sources:
    * https://mediamtx.org/docs/ (Next.js-rendered HTML)
    * https://raw.githubusercontent.com/bluenviron/mediamtx/main/README.md
      (GitHub fallback for definitive answers)

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages to ~/.cache/mediamtx-docs/.

Usage:
    mtxdocs.py list-pages
    mtxdocs.py fetch --page features/architecture
    mtxdocs.py search --query "record" [--page features/record]
    mtxdocs.py section --page features/authentication --id internal-users
    mtxdocs.py index
    mtxdocs.py clear-cache

Override cache location with MEDIAMTX_DOCS_CACHE env var.
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

BASE = "https://mediamtx.org"
UA = "mediamtx-docs-skill/1.0 (Claude Code Agent Skill)"

# name -> URL path (relative to BASE). Every page verified HTTP-200 at
# authoring time.
PAGES: dict[str, str] = {
    # Kickoff
    "kickoff/introduction": "/docs/kickoff/introduction",
    "kickoff/install": "/docs/kickoff/install",
    "kickoff/upgrade": "/docs/kickoff/upgrade",
    # Features — architecture + core flows
    "features/architecture": "/docs/features/architecture",
    "features/publish": "/docs/features/publish",
    "features/read": "/docs/features/read",
    "features/record": "/docs/features/record",
    "features/playback": "/docs/features/playback",
    "features/authentication": "/docs/features/authentication",
    "features/hooks": "/docs/features/hooks",
    "features/metrics": "/docs/features/metrics",
    "features/forward": "/docs/features/forward",
    "features/proxy": "/docs/features/proxy",
    "features/performance": "/docs/features/performance",
    # Features — per-protocol
    "features/rtsp-specific-features": "/docs/features/rtsp-specific-features",
    "features/rtmp-specific-features": "/docs/features/rtmp-specific-features",
    "features/webrtc-specific-features": "/docs/features/webrtc-specific-features",
    "features/srt-specific-features": "/docs/features/srt-specific-features",
    # Features — misc operational
    "features/absolute-timestamps": "/docs/features/absolute-timestamps",
    "features/always-available": "/docs/features/always-available",
    "features/on-demand-publishing": "/docs/features/on-demand-publishing",
    "features/decrease-packet-loss": "/docs/features/decrease-packet-loss",
    "features/extract-snapshots": "/docs/features/extract-snapshots",
    "features/remuxing-reencoding-compression": "/docs/features/remuxing-reencoding-compression",
    "features/start-on-boot": "/docs/features/start-on-boot",
    "features/embed-streams-in-a-website": "/docs/features/embed-streams-in-a-website",
    "features/expose-the-server-in-a-subfolder": "/docs/features/expose-the-server-in-a-subfolder",
    "features/logging": "/docs/features/logging",
    "features/configuration": "/docs/features/configuration",
    "features/control-api": "/docs/features/control-api",
    # References
    "references/configuration-file": "/docs/references/configuration-file",
    "references/control-api": "/docs/references/control-api",
    # Publish howtos
    "publish/ffmpeg": "/docs/publish/ffmpeg",
    "publish/gstreamer": "/docs/publish/gstreamer",
    "publish/obs-studio": "/docs/publish/obs-studio",
    "publish/python-opencv": "/docs/publish/python-opencv",
    "publish/golang": "/docs/publish/golang",
    "publish/unity": "/docs/publish/unity",
    "publish/raspberry-pi-cameras": "/docs/publish/raspberry-pi-cameras",
    "publish/web-browsers": "/docs/publish/web-browsers",
    "publish/webrtc-clients": "/docs/publish/webrtc-clients",
    "publish/webrtc-servers": "/docs/publish/webrtc-servers",
    "publish/rtsp-cameras-and-servers": "/docs/publish/rtsp-cameras-and-servers",
    "publish/rtmp-cameras-and-servers": "/docs/publish/rtmp-cameras-and-servers",
    "publish/hls-cameras-and-servers": "/docs/publish/hls-cameras-and-servers",
    "publish/srt-cameras-and-servers": "/docs/publish/srt-cameras-and-servers",
    "publish/generic-webcams": "/docs/publish/generic-webcams",
    "publish/rtsp-clients": "/docs/publish/rtsp-clients",
    "publish/rtmp-clients": "/docs/publish/rtmp-clients",
    "publish/srt-clients": "/docs/publish/srt-clients",
    "publish/rtp": "/docs/publish/rtp",
    "publish/mpeg-ts": "/docs/publish/mpeg-ts",
    # Read howtos
    "read/ffmpeg": "/docs/read/ffmpeg",
    "read/gstreamer": "/docs/read/gstreamer",
    "read/vlc": "/docs/read/vlc",
    "read/obs-studio": "/docs/read/obs-studio",
    "read/python-opencv": "/docs/read/python-opencv",
    "read/golang": "/docs/read/golang",
    "read/unity": "/docs/read/unity",
    "read/web-browsers": "/docs/read/web-browsers",
    "read/rtsp": "/docs/read/rtsp",
    "read/rtmp": "/docs/read/rtmp",
    "read/hls": "/docs/read/hls",
    "read/srt": "/docs/read/srt",
    "read/webrtc": "/docs/read/webrtc",
    # GitHub fallbacks (raw Markdown — authoritative reference for the
    # config file + control API schema at the upstream commit)
    "github-readme": "https://raw.githubusercontent.com/bluenviron/mediamtx/main/README.md",
    "github-mediamtx.yml": "https://raw.githubusercontent.com/bluenviron/mediamtx/main/mediamtx.yml",
    "github-apidocs": "https://raw.githubusercontent.com/bluenviron/mediamtx/main/apidocs/openapi.yaml",
}

CACHE_DIR = Path(
    os.environ.get("MEDIAMTX_DOCS_CACHE", Path.home() / ".cache" / "mediamtx-docs")
)


class TextExtractor(HTMLParser):
    """Convert mediamtx.org pages + GitHub HTML into searchable text."""

    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "svg"}
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
        aid = a.get("id") or a.get("name")
        if aid:
            self.pending_anchor = aid
        if tag in self.HEAD_TAGS:
            lvl = self.HEAD_TAGS[tag]
            self.buf.append("\n\n" + "#" * lvl + " ")
            if self.pending_anchor:
                self.buf.append(f"[§{self.pending_anchor}] ")
                self.pending_anchor = None
        elif tag == "pre":
            self.in_pre += 1
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "dt":
            self.buf.append("\n\n**")
            if self.pending_anchor:
                self.buf.append(f"[§{self.pending_anchor}] ")
                self.pending_anchor = None
        elif tag == "dd":
            self.buf.append("** — ")
        elif tag in ("p", "div", "section"):
            self.buf.append("\n\n")
        elif tag == "li":
            self.buf.append("\n- ")
        elif tag == "br":
            self.buf.append("\n")
        elif tag == "tr":
            self.buf.append("\n| ")
        elif tag in ("td", "th"):
            self.buf.append(" | ")

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
    safe = page.replace("/", "__").replace(":", "__")
    return CACHE_DIR / f"{safe}.txt"


def page_url(page: str) -> str:
    if page not in PAGES:
        raise ValueError(f"unknown page: {page!r}")
    target = PAGES[page]
    if target.startswith("http://") or target.startswith("https://"):
        return target
    return BASE + target


def extract_text(url: str, raw: str) -> str:
    # Raw Markdown / YAML from GitHub: pass through as-is.
    lower = url.lower()
    if (
        "raw.githubusercontent.com" in lower
        or lower.endswith(".md")
        or lower.endswith(".yaml")
        or lower.endswith(".yml")
    ):
        return raw.strip()
    parser = TextExtractor()
    parser.feed(raw)
    return parser.text()


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    cp = cache_path(page)
    if cp.exists() and not no_cache:
        return cp.read_text(encoding="utf-8")
    url = page_url(page)
    raw = fetch_url(url, verbose=verbose)
    text = extract_text(url, raw)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(n) for n in PAGES)
    for name in sorted(PAGES):
        print(f"{name:{width}s}  {page_url(name)}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    text = load_or_fetch(args.page, no_cache=args.no_cache, verbose=args.verbose)
    if args.format == "json":
        print(
            json.dumps(
                {"page": args.page, "url": page_url(args.page), "text": text},
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
            time.sleep(0.3)
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
                url = page_url(page)
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
        description="Search and fetch official MediaMTX documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known mediamtx.org doc pages")
    p1.add_argument("--verbose", action="store_true")
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page as text")
    p2.add_argument("--page", required=True, help="page name (see list-pages)")
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true", help="re-fetch, bypass cache")
    p2.add_argument("--verbose", action="store_true")
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every known page into the cache")
    p3.add_argument("--verbose", action="store_true")
    p3.set_defaults(fn=cmd_index)

    p4 = sub.add_parser("search", help="search for a term across cached pages")
    p4.add_argument("--query", required=True, help="text to search for")
    p4.add_argument("--page", help="limit to one page; default: search all pages")
    p4.add_argument("--regex", action="store_true", help="treat --query as a regex")
    p4.add_argument(
        "--context", type=int, default=3, help="lines of context around each hit"
    )
    p4.add_argument(
        "--limit", type=int, default=20, help="max hits to return (default: 20)"
    )
    p4.add_argument("--format", choices=["text", "json"], default="text")
    p4.add_argument("--verbose", action="store_true")
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser(
        "section", help="extract one section by anchor id or heading keyword"
    )
    p5.add_argument("--page", required=True)
    p5.add_argument("--id", required=True, help="anchor id or heading keyword")
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p6.add_argument("--verbose", action="store_true")
    p6.set_defaults(fn=cmd_clear_cache)

    for sp in (p1, p2, p3, p4, p5, p6):
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="echo intent to stderr; for doc fetch this only affects `index` and network fetches",
        )

    return p


def main() -> int:
    args = build_parser().parse_args()
    print("+ mtxdocs.py " + " ".join(sys.argv[1:]), file=sys.stderr)
    if getattr(args, "dry_run", False):
        print("[dry-run] exit without fetching", file=sys.stderr)
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
