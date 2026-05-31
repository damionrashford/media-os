#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""obsdocs.py — Search and fetch official OBS Studio documentation.

Covers docs.obsproject.com (backend, plugins, frontends, graphics, scripting,
every reference-* page), the Install wiki at obsproject.com/wiki, the
obs-plugintemplate README on GitHub, and the obs-websocket protocol reference.

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages to ~/.cache/obs-docs/ so repeated lookups are offline-fast.

Usage:
    obsdocs.py list-pages
    obsdocs.py fetch --page reference-core
    obsdocs.py search --query "obs_source_create" [--page reference-core-objects]
    obsdocs.py section --page reference-frontend-api --id obs-frontend-api-h
    obsdocs.py index
    obsdocs.py clear-cache

Override cache location with FFMPEG_DOCS_CACHE-style OBS_DOCS_CACHE env var.
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

UA = "obs-docs-skill/1.0 (Claude Code Agent Skill)"

# name -> full URL. Mix of docs.obsproject.com HTML, obsproject.com/wiki HTML,
# and GitHub raw Markdown for the plugin template + obs-websocket protocol.
PAGES: dict[str, str] = {
    # docs.obsproject.com — libobs and OBS Studio developer docs
    "index": "https://docs.obsproject.com/",
    "backend-design": "https://docs.obsproject.com/backend-design",
    "plugins": "https://docs.obsproject.com/plugins",
    "frontends": "https://docs.obsproject.com/frontends",
    "graphics": "https://docs.obsproject.com/graphics",
    "scripting": "https://docs.obsproject.com/scripting",
    "reference-core": "https://docs.obsproject.com/reference-core",
    "reference-modules": "https://docs.obsproject.com/reference-modules",
    "reference-core-objects": "https://docs.obsproject.com/reference-core-objects",
    "reference-libobs-util": "https://docs.obsproject.com/reference-libobs-util",
    "reference-libobs-callback": "https://docs.obsproject.com/reference-libobs-callback",
    "reference-libobs-graphics": "https://docs.obsproject.com/reference-libobs-graphics",
    "reference-libobs-media-io": "https://docs.obsproject.com/reference-libobs-media-io",
    "reference-frontend-api": "https://docs.obsproject.com/reference-frontend-api",
    # Install wiki (different subdomain, HTML-rendered)
    "wiki-install": "https://obsproject.com/wiki/Install-Instructions",
    # GitHub raw Markdown
    "plugintemplate-readme": "https://raw.githubusercontent.com/obsproject/obs-plugintemplate/master/README.md",
    "obs-websocket-protocol": "https://raw.githubusercontent.com/obsproject/obs-websocket/master/docs/generated/protocol.md",
}

CACHE_DIR = Path(os.environ.get("OBS_DOCS_CACHE", Path.home() / ".cache" / "obs-docs"))


class TextExtractor(HTMLParser):
    """Convert Sphinx-generated HTML into a searchable text form.

    Preserves section headings with anchor IDs (as `[§anchor]`), definition
    lists (dt/dd → `**name** — description`), code blocks, inline code, and
    paragraph breaks. Skips nav/script/style/header/footer chrome.
    """

    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside"}
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
        # Capture anchor IDs from <a id=…>, <a name=…>, or any tag with id=…
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


def extract_text(url: str, raw: str) -> str:
    """Route to HTML parser or raw-Markdown pass-through based on URL."""
    if url.endswith(".md") or "raw.githubusercontent.com" in url:
        # GitHub raw Markdown: keep as-is; our searchable-text format is
        # already Markdown-ish.
        return raw.strip()
    parser = TextExtractor()
    parser.feed(raw)
    return parser.text()


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    if page not in PAGES:
        raise ValueError(
            f"unknown page: {page!r}. Run `obsdocs.py list-pages` to see valid names."
        )
    cp = cache_path(page)
    if cp.exists() and not no_cache:
        return cp.read_text(encoding="utf-8")
    url = PAGES[page]
    raw = fetch_url(url, verbose=verbose)
    text = extract_text(url, raw)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(n) for n in PAGES)
    for name in sorted(PAGES):
        print(f"{name:{width}s}  {PAGES[name]}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    text = load_or_fetch(args.page, no_cache=args.no_cache, verbose=args.verbose)
    if args.format == "json":
        print(
            json.dumps(
                {"page": args.page, "url": PAGES[args.page], "text": text}, indent=2
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
            time.sleep(0.5)
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
        description="Search and fetch official OBS Studio documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known OBS doc pages")
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
    p5.add_argument(
        "--id",
        required=True,
        help="anchor id (e.g. obs-frontend-api-h) or heading keyword",
    )
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p6.add_argument("--verbose", action="store_true")
    p6.set_defaults(fn=cmd_clear_cache)

    return p


def main() -> int:
    args = build_parser().parse_args()
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
