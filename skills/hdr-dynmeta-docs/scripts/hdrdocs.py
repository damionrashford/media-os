#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""hdrdocs.py — Search and fetch docs for HDR dynamic-metadata CLIs.

Covers the dovi_tool (Dolby Vision RPU authoring) and hdr10plus_tool
(HDR10+ SEI authoring) READMEs and latest-release JSON on GitHub, both
authored by `quietvoid`.

Stdlib only (urllib). Non-interactive. Caches fetched pages to
~/.cache/hdr-dynmeta-docs/ so repeated lookups are offline-fast.

Usage:
    hdrdocs.py list-pages
    hdrdocs.py fetch --page dovi-readme
    hdrdocs.py search --query "extract-rpu" [--page dovi-readme]
    hdrdocs.py section --page dovi-readme --id Usage
    hdrdocs.py index
    hdrdocs.py clear-cache

Override cache location with HDR_DYNMETA_DOCS_CACHE env var.
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
from pathlib import Path

UA = "hdr-dynmeta-docs-skill/1.0 (Claude Code Agent Skill)"

PAGES: dict[str, str] = {
    "dovi-readme": (
        "https://raw.githubusercontent.com/quietvoid/dovi_tool/main/README.md"
    ),
    "dovi-releases": (
        "https://api.github.com/repos/quietvoid/dovi_tool/releases/latest"
    ),
    "hdr10plus-readme": (
        "https://raw.githubusercontent.com/quietvoid/hdr10plus_tool/main/README.md"
    ),
    "hdr10plus-releases": (
        "https://api.github.com/repos/quietvoid/hdr10plus_tool/releases/latest"
    ),
}

CACHE_DIR = Path(
    os.environ.get(
        "HDR_DYNMETA_DOCS_CACHE", Path.home() / ".cache" / "hdr-dynmeta-docs"
    )
)


def fetch_url(url: str, verbose: bool = False) -> str:
    headers = {"User-Agent": UA}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    if verbose:
        print(f"[fetch] {url}", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_text(url: str, raw: str) -> str:
    """GitHub API returns JSON release metadata; prettify. Markdown is passthrough."""
    if "api.github.com" in url:
        try:
            obj = json.loads(raw)
            lines = []
            lines.append(f"# {obj.get('name') or obj.get('tag_name')}\n")
            lines.append(f"**tag:** {obj.get('tag_name')}  ")
            lines.append(f"**published:** {obj.get('published_at')}  ")
            lines.append(f"**url:** {obj.get('html_url')}\n")
            body = obj.get("body", "") or ""
            lines.append(body.strip())
            return "\n".join(lines).strip()
        except Exception:  # noqa: BLE001
            return raw
    return raw.strip()


def cache_path(page: str) -> Path:
    return CACHE_DIR / f"{page}.txt"


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    if page not in PAGES:
        raise ValueError(
            f"unknown page: {page!r}. Run `hdrdocs.py list-pages` to see valid names."
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
                for j in range(i, -1, -1):
                    if lines[j].startswith("#"):
                        heading = lines[j].strip()
                        break
                hits.append(
                    {
                        "page": page,
                        "line": i + 1,
                        "heading": heading,
                        "url": PAGES[page],
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
        description="Search and fetch HDR dynamic-metadata tool docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known pages")
    p1.add_argument("--verbose", action="store_true")
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a page")
    p2.add_argument("--page", required=True)
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true")
    p2.add_argument("--verbose", action="store_true")
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every page")
    p3.add_argument("--verbose", action="store_true")
    p3.set_defaults(fn=cmd_index)

    p4 = sub.add_parser("search", help="search across cached pages")
    p4.add_argument("--query", required=True)
    p4.add_argument("--page", help="limit to one page")
    p4.add_argument("--regex", action="store_true")
    p4.add_argument("--context", type=int, default=3)
    p4.add_argument("--limit", type=int, default=20)
    p4.add_argument("--format", choices=["text", "json"], default="text")
    p4.add_argument("--verbose", action="store_true")
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser("section", help="extract one section by heading keyword")
    p5.add_argument("--page", required=True)
    p5.add_argument("--id", required=True, help="heading keyword")
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete local cache")
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
        return 130


if __name__ == "__main__":
    sys.exit(main())
