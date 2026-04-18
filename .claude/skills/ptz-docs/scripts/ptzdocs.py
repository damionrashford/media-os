#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""ptzdocs.py — Search and fetch official PTZ camera control protocol docs.

Covers Sony VISCA (Command List v2.00, BRC-H900, SRG-300H, PTZOptics VISCA-over-IP)
and ONVIF profile pages (profiles hub, specifications, Profile S, overview v2.1).

PDF pages are listed by URL only (stdlib cannot parse PDF bytes). HTML pages
(onvif.org) are text-extracted and searchable.

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages to ~/.cache/ptz-docs/ so repeated lookups are offline-fast.

Usage:
    ptzdocs.py list-pages
    ptzdocs.py fetch --page onvif-profile-s
    ptzdocs.py search --query "Pan Tilt" [--page onvif-profiles]
    ptzdocs.py section --page onvif-profiles --id profile-t
    ptzdocs.py index
    ptzdocs.py clear-cache

Override cache location with the PTZ_DOCS_CACHE env var.
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

UA = "ptz-docs-skill/1.0 (Claude Code Agent Skill)"

# Each entry: (url, kind). kind is "html" (extract + search) or "pdf" (url only).
PAGES: dict[str, tuple[str, str]] = {
    # Sony VISCA PDFs (login/partner-gated for full content, but public URLs work)
    "visca-v2": (
        "https://pro.sony/s3/2022/09/14131603/VISCA-Command-List-Version-2.00.pdf",
        "pdf",
    ),
    "visca-brc-h900": (
        "https://pro.sony/s3/cms-static-content/uploadfile/59/1237493025759.pdf",
        "pdf",
    ),
    "visca-srg-300h": (
        "https://pro.sony/support/res/manuals/AES6/fe573c4d3e5d01ec8d5172b500b32ac1/AES61001M.pdf",
        "pdf",
    ),
    "visca-ptzoptics": (
        "https://ptzoptics.com/wp-content/uploads/2020/11/PTZOptics-VISCA-over-IP-Rev-1_2-8-20.pdf",
        "pdf",
    ),
    # ONVIF pages
    "onvif-profiles": ("https://www.onvif.org/profiles/", "html"),
    "onvif-specifications": (
        "https://www.onvif.org/profiles/specifications/",
        "html",
    ),
    "onvif-profile-overview": (
        "https://www.onvif.org/wp-content/uploads/2018/05/ONVIF_Profile_Feature_overview_v2-1.pdf",
        "pdf",
    ),
    "onvif-profile-s": ("https://www.onvif.org/profiles/profile-s/", "html"),
}

CACHE_DIR = Path(os.environ.get("PTZ_DOCS_CACHE", Path.home() / ".cache" / "ptz-docs"))


class TextExtractor(HTMLParser):
    """Convert HTML pages into searchable text with anchor-tagged headings."""

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
        if tag == "a":
            anchor = a.get("name") or a.get("id")
            if anchor:
                self.pending_anchor = anchor
        if tag in self.HEAD_TAGS:
            lvl = self.HEAD_TAGS[tag]
            self.buf.append("\n\n" + "#" * lvl + " ")
            anchor = a.get("id") or self.pending_anchor
            if anchor:
                self.buf.append(f"[§{anchor}] ")
                self.pending_anchor = None
        elif tag == "pre":
            self.in_pre += 1
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "li":
            self.buf.append("\n- ")
        elif tag in ("p", "div", "section", "article"):
            self.buf.append("\n\n")
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

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        self.buf.append(data)

    def text(self) -> str:
        out = "".join(self.buf)
        out = re.sub(r"\n{3,}", "\n\n", out)
        out = re.sub(r"[ \t]+\n", "\n", out)
        return out.strip()


def fetch_url(url: str, verbose: bool = False) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if verbose:
        print(f"[fetch] {url}", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def cache_path(page: str) -> Path:
    return CACHE_DIR / f"{page}.txt"


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    if page not in PAGES:
        raise ValueError(
            f"unknown page: {page!r}. Run `ptzdocs.py list-pages` to see valid names."
        )
    url, kind = PAGES[page]
    if kind == "pdf":
        return (
            f"# {page}\n\n"
            f"Binary PDF page — URL only (stdlib cannot parse PDF).\n\n"
            f"URL: {url}\n\n"
            f"Open in a PDF reader, or consult `references/visca-commands.md` for "
            f"curated byte tables.\n"
        )
    cp = cache_path(page)
    if cp.exists() and not no_cache:
        return cp.read_text(encoding="utf-8")
    html = fetch_url(url, verbose=verbose).decode("utf-8", errors="replace")
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(n) for n in PAGES)
    for name, (url, kind) in sorted(PAGES.items()):
        tag = "[pdf]" if kind == "pdf" else "[html]"
        print(f"{name:{width}s}  {tag:6s}  {url}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    text = load_or_fetch(args.page, no_cache=args.no_cache, verbose=args.verbose)
    url, kind = PAGES[args.page]
    if args.format == "json":
        print(
            json.dumps(
                {"page": args.page, "url": url, "kind": kind, "text": text}, indent=2
            )
        )
    else:
        print(text)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    failed: list[tuple[str, str]] = []
    for page, (_, kind) in PAGES.items():
        if kind == "pdf":
            if args.verbose:
                print(f"skipping pdf {page} (url only)", file=sys.stderr)
            continue
        print(f"indexing {page}...", file=sys.stderr)
        try:
            load_or_fetch(page, no_cache=True, verbose=args.verbose)
            time.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            failed.append((page, str(e)))
            print(f"  failed: {e}", file=sys.stderr)
    print(f"\ndone; cache at {CACHE_DIR}", file=sys.stderr)
    if failed:
        print(f"{len(failed)} page(s) failed:", file=sys.stderr)
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
        url, kind = PAGES[page]
        if kind == "pdf":
            continue  # can't search PDF bytes
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
                hit_url = url + (f"#{anchor}" if anchor else "")
                hits.append(
                    {
                        "page": page,
                        "line": i + 1,
                        "heading": heading,
                        "anchor": anchor,
                        "url": hit_url,
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
        description="Search and fetch PTZ protocol docs (VISCA + ONVIF).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known doc pages")
    p1.add_argument("--verbose", action="store_true")
    p1.add_argument("--dry-run", action="store_true", help="no effect (non-mutating)")
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page as text")
    p2.add_argument("--page", required=True)
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true")
    p2.add_argument("--verbose", action="store_true")
    p2.add_argument("--dry-run", action="store_true")
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every HTML page into the cache")
    p3.add_argument("--verbose", action="store_true")
    p3.add_argument("--dry-run", action="store_true")
    p3.set_defaults(fn=cmd_index)

    p4 = sub.add_parser("search", help="search cached HTML pages")
    p4.add_argument("--query", required=True)
    p4.add_argument("--page", help="limit to one page")
    p4.add_argument("--regex", action="store_true")
    p4.add_argument("--context", type=int, default=3)
    p4.add_argument("--limit", type=int, default=20)
    p4.add_argument("--format", choices=["text", "json"], default="text")
    p4.add_argument("--verbose", action="store_true")
    p4.add_argument("--dry-run", action="store_true")
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser("section", help="extract one section by anchor id or keyword")
    p5.add_argument("--page", required=True)
    p5.add_argument("--id", required=True)
    p5.add_argument("--verbose", action="store_true")
    p5.add_argument("--dry-run", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete local cache directory")
    p6.add_argument("--verbose", action="store_true")
    p6.add_argument("--dry-run", action="store_true")
    p6.set_defaults(fn=cmd_clear_cache)

    return p


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, "dry_run", False):
        print(f"[dry-run] would run: {args.cmd}", file=sys.stderr)
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
