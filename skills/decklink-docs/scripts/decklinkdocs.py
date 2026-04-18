#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""decklinkdocs.py — Search and fetch Blackmagic DeckLink SDK docs.

Covers several hosts (the Blackmagic developer hub is partly login-gated;
the catalog also includes the ffmpeg decklink device pages and third-party
mirrors that expose SDK sample names + API indexes):

  * blackmagicdesign.com/developer   — landing pages (login-gated for SDK DL)
  * ffmpeg.org                       — ffmpeg-devices decklink demuxer+muxer
  * github.com                       — third-party bmdtools + SDK README mirrors

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages under ~/.cache/decklink-docs/ for offline-fast repeat lookups.

Usage:
    decklinkdocs.py list-pages
    decklinkdocs.py fetch   --page ffmpeg-devices-decklink
    decklinkdocs.py search  --query "BMDPixelFormat" [--page ffmpeg-devices-decklink]
    decklinkdocs.py section --page ffmpeg-devices-decklink --id decklink
    decklinkdocs.py index
    decklinkdocs.py clear-cache

Override the cache location with the DECKLINK_DOCS_CACHE env var.
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

UA = "decklink-docs-skill/1.0 (Claude Code Agent Skill)"

# page name -> canonical URL.
PAGES: dict[str, str] = {
    # Blackmagic developer hub (login-gated for SDK download).
    "blackmagic-developer": "https://www.blackmagicdesign.com/developer",
    "blackmagic-capture-playback": "https://www.blackmagicdesign.com/developer/product/capture-and-playback",
    "blackmagic-support": "https://www.blackmagicdesign.com/support/family/capture-and-playback",
    # ffmpeg decklink device docs (the authoritative CLI-side reference).
    "ffmpeg-devices": "https://ffmpeg.org/ffmpeg-devices.html",
    "ffmpeg-devices-decklink": "https://ffmpeg.org/ffmpeg-devices.html#decklink",
    # Third-party bmdtools (bmdcapture / bmdplay) — not part of the official SDK.
    "bmdtools-github": "https://github.com/lu-zero/bmdtools",
    # Third-party mirrors that expose the SDK README + API index
    # (the actual headers ship in the login-gated ZIP; these pages list
    # the interface names so search can still find them).
    "decklink-sdk-readme-mirror": "https://github.com/search?q=DeckLinkAPI.h&type=code",
    "decklink-samples-search": "https://github.com/search?q=CapturePreview+DeckLink&type=code",
}

CACHE_DIR = Path(
    os.environ.get("DECKLINK_DOCS_CACHE", Path.home() / ".cache" / "decklink-docs")
)


class TextExtractor(HTMLParser):
    """Convert HTML doc pages into searchable text form."""

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
            self.buf.append("\n\n" + "#" * lvl + " ")
            if self.pending_anchor:
                self.buf.append(f"[\u00a7{self.pending_anchor}] ")
                self.pending_anchor = None
        elif tag == "pre":
            self.in_pre += 1
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "dt":
            self.buf.append("\n\n**")
        elif tag == "dd":
            self.buf.append("** \u2014 ")
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
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", page)
    return CACHE_DIR / f"{safe}.txt"


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    if page not in PAGES:
        raise ValueError(
            f"unknown page: {page!r}. Run `decklinkdocs.py list-pages` to see valid names."
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
    for name, url in sorted(PAGES.items()):
        print(f"{name:{width}s}  {url}")
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
                        m = re.search(r"\[\u00a7([^\]]+)\]", heading)
                        if m:
                            anchor = m.group(1)
                        break
                url = PAGES[page]
                if anchor and "#" not in url:
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
            print(f"--- {h['page']}:{h['line']} \u2014 {h['heading']}")
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
    target = f"[\u00a7{args.id}]"
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
        description="Search and fetch Blackmagic DeckLink SDK docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known DeckLink doc pages")
    p1.add_argument("--verbose", action="store_true")
    p1.add_argument(
        "--dry-run", action="store_true", help="no-op (listing is read-only)"
    )
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page as text")
    p2.add_argument("--page", required=True, help="page name (see list-pages)")
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true", help="re-fetch, bypass cache")
    p2.add_argument("--verbose", action="store_true")
    p2.add_argument(
        "--dry-run", action="store_true", help="print URL that would be fetched"
    )
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every known page into the cache")
    p3.add_argument("--verbose", action="store_true")
    p3.add_argument(
        "--dry-run", action="store_true", help="list URLs that would be fetched"
    )
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
    p4.add_argument(
        "--dry-run", action="store_true", help="print pages that would be searched"
    )
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser(
        "section", help="extract one section by anchor id or heading keyword"
    )
    p5.add_argument("--page", required=True)
    p5.add_argument("--id", required=True, help="anchor id or heading keyword")
    p5.add_argument("--verbose", action="store_true")
    p5.add_argument(
        "--dry-run", action="store_true", help="print page that would be loaded"
    )
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p6.add_argument("--verbose", action="store_true")
    p6.add_argument(
        "--dry-run", action="store_true", help="print path that would be deleted"
    )
    p6.set_defaults(fn=cmd_clear_cache)

    return p


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, "dry_run", False):
        print(f"[dry-run] would run {args.cmd}", file=sys.stderr)
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
