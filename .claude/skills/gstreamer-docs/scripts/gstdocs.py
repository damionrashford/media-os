#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""gstdocs.py — Search and fetch official GStreamer documentation.

Source: https://gstreamer.freedesktop.org/documentation/ (Hotdoc-generated HTML).

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages to ~/.cache/gstreamer-docs/.

Two page shapes for elements are handled automatically:
    * multi-element plugin dirs: /<plugin>/<element>.html
      (e.g. /coreelements/filesrc.html, /playback/playbin3.html)
    * singleton plugin dirs:     /<element>/index.html
      (e.g. /videotestsrc/index.html, /x264/index.html)

Bare /<element>.html is universally 404 — the script must resolve the plugin
via the plugin landing page before fetching an element page.

Usage:
    gstdocs.py list-pages
    gstdocs.py fetch --page coreelements
    gstdocs.py fetch --element filesrc
    gstdocs.py search --query "webrtcbin" [--page webrtc]
    gstdocs.py section --page coreelements --id filesrc
    gstdocs.py element --name filesrc
    gstdocs.py resolve --element filesrc
    gstdocs.py index
    gstdocs.py clear-cache

Override cache location with the GSTREAMER_DOCS_CACHE env var.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://gstreamer.freedesktop.org/documentation"
UA = "gstreamer-docs-skill/1.0 (Claude Code Agent Skill)"

# Short-name -> relative URL under BASE.
# Each known page has been verified HTTP-200 at authoring time.
PAGES: dict[str, str] = {
    # Top-level landing
    "index": "/index.html",
    # User-facing guides
    "application-development": "/application-development/index.html",
    "tutorials": "/tutorials/index.html",
    "plugin-development": "/plugin-development/index.html",
    "deploying": "/deploying/index.html",
    "installing": "/installing/index.html",
    "frequently-asked-questions": "/frequently-asked-questions/index.html",
    "contribute": "/contribute/index.html",
    "additional": "/additional/index.html",
    # CLI tools
    "tools": "/tools/index.html",
    "gst-launch": "/tools/gst-launch.html",
    "gst-inspect": "/tools/gst-inspect.html",
    # Library / plugin indexes
    "gstreamer": "/gstreamer/gi-index.html",
    "base": "/base/index.html",
    "video": "/video/index.html",
    "audio": "/audio/index.html",
    "rtp": "/rtp/index.html",
    "webrtc": "/webrtc/index.html",
    "sdp": "/sdp/index.html",
    "pbutils": "/pbutils/index.html",
    "app": "/app/index.html",
    "coreelements": "/coreelements/index.html",
    "coretracers": "/coretracers/index.html",
    "libav": "/libav/index.html",
    # Plugin indexes commonly asked for
    "playback": "/playback/index.html",
    "rtsp": "/rtsp/index.html",
    "rtspserver": "/rtspserver/index.html",
    "hls": "/hls/index.html",
    "dash": "/dash/index.html",
    "srt": "/srt/index.html",
    "rswebrtc": "/rswebrtc/index.html",
    "x264": "/x264/index.html",
    "x265": "/x265/index.html",
    "vpx": "/vpx/index.html",
    "nvcodec": "/nvcodec/index.html",
    "isomp4": "/isomp4/index.html",
    "matroska": "/matroska/index.html",
    "videotestsrc": "/videotestsrc/index.html",
    "audiotestsrc": "/audiotestsrc/index.html",
    "opengl": "/opengl/index.html",
    "vulkan": "/vulkan/index.html",
    "v4l2": "/v4l2/index.html",
}

# Well-known element -> plugin mapping. Used by `resolve` / `element` to skip a
# plugin-landing-page crawl on the hot path. When a name isn't here, the script
# falls back to scanning the relevant plugin index's links.
ELEMENT_HINTS: dict[str, str] = {
    # coreelements
    "filesrc": "coreelements",
    "filesink": "coreelements",
    "fakesrc": "coreelements",
    "fakesink": "coreelements",
    "queue": "coreelements",
    "queue2": "coreelements",
    "tee": "coreelements",
    "identity": "coreelements",
    "capsfilter": "coreelements",
    "multiqueue": "coreelements",
    "valve": "coreelements",
    "input-selector": "coreelements",
    "output-selector": "coreelements",
    # playback
    "playbin": "playback",
    "playbin3": "playback",
    "decodebin": "playback",
    "decodebin3": "playback",
    "uridecodebin": "playback",
    "uridecodebin3": "playback",
    "urisourcebin": "playback",
    "playsink": "playback",
    # rtsp
    "rtspsrc": "rtsp",
    # rtspserver
    "rtspclientsink": "rtspserver",
    # hls
    "hlssink": "hls",
    "hlssink2": "hls",
    "hlsdemux": "hls",
    # dash
    "dashdemux": "dash",
    "dashsink": "dash",
    # srt
    "srtsrc": "srt",
    "srtsink": "srt",
    "srtclientsrc": "srt",
    "srtclientsink": "srt",
    "srtserversrc": "srt",
    "srtserversink": "srt",
    # rswebrtc (Rust)
    "webrtcsink": "rswebrtc",
    "webrtcsrc": "rswebrtc",
    # webrtc (C)
    "webrtcbin": "webrtc",
    # x264/x265/vpx
    "x264enc": "x264",
    "x265enc": "x265",
    "vp8enc": "vpx",
    "vp9enc": "vpx",
    "vp8dec": "vpx",
    "vp9dec": "vpx",
    # nvcodec
    "nvh264enc": "nvcodec",
    "nvh265enc": "nvcodec",
    "nvh264dec": "nvcodec",
    "nvh265dec": "nvcodec",
    # isomp4
    "mp4mux": "isomp4",
    "qtmux": "isomp4",
    "qtdemux": "isomp4",
    # matroska
    "matroskamux": "matroska",
    "matroskademux": "matroska",
    "webmmux": "matroska",
    # v4l2
    "v4l2src": "v4l2",
    "v4l2sink": "v4l2",
    # opengl
    "glimagesink": "opengl",
    "glupload": "opengl",
    "gldownload": "opengl",
    # standalone singleton plugins
    "videotestsrc": "videotestsrc",
    "audiotestsrc": "audiotestsrc",
    "videoconvert": "videoconvert",
    "audioconvert": "audioconvert",
    "videoscale": "videoscale",
    "audioresample": "audioresample",
    "audiomixer": "audiomixer",
    "compositor": "compositor",
    "autovideosink": "autodetect",
    "autoaudiosink": "autodetect",
    "autovideosrc": "autodetect",
    "autoaudiosrc": "autodetect",
}

# Pages we additionally discover on demand: once we resolve an element to
# (plugin, shape), we cache a synthetic page entry keyed by `element:<name>`.

SINGLETON_PLUGINS: set[str] = {
    "videotestsrc",
    "audiotestsrc",
    "videoconvert",
    "audioconvert",
    "videoscale",
    "audioresample",
    "autodetect",
    "audiomixer",
    "compositor",
    "webrtclib",
}

CACHE_DIR = Path(
    os.environ.get("GSTREAMER_DOCS_CACHE", Path.home() / ".cache" / "gstreamer-docs")
)


# ── HTML → text ─────────────────────────────────────────────────────────────


class TextExtractor(HTMLParser):
    """Convert Hotdoc-generated HTML into a searchable text form.

    Preserves headings + anchor IDs (`[§anchor]`), definition lists, inline
    code, pre blocks, paragraph breaks. Skips nav/script/style/aside chrome.
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

    def text(self) -> str:
        out = "".join(self.buf)
        out = re.sub(r"\n{3,}", "\n\n", out)
        out = re.sub(r"[ \t]+\n", "\n", out)
        return out.strip()


class LinkExtractor(HTMLParser):
    """Collect every href on a plugin landing page for element resolution."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)


# ── Fetcher ─────────────────────────────────────────────────────────────────


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
    if page in PAGES:
        return BASE + PAGES[page]
    raise ValueError(f"unknown page: {page!r}")


def load_or_fetch(page: str, *, no_cache: bool = False, verbose: bool = False) -> str:
    cp = cache_path(page)
    if cp.exists() and not no_cache:
        return cp.read_text(encoding="utf-8")
    url = page_url(page)
    html = fetch_url(url, verbose=verbose)
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(text, encoding="utf-8")
    return text


# ── Element resolution ──────────────────────────────────────────────────────


def resolve_element(name: str, *, verbose: bool = False) -> tuple[str, str] | None:
    """Return (element_url, style) for an element name, or None if unknown.

    style is 'multi' for /<plugin>/<element>.html or 'singleton' for
    /<plugin>/index.html.
    """
    plugin = ELEMENT_HINTS.get(name)
    if plugin:
        # Try singleton style first if we flagged this plugin as singleton.
        if plugin in SINGLETON_PLUGINS or plugin == name:
            url = f"{BASE}/{plugin}/index.html"
            if _head_ok(url, verbose=verbose):
                return url, "singleton"
        # Otherwise try multi-element style
        url = f"{BASE}/{plugin}/{name}.html"
        if _head_ok(url, verbose=verbose):
            return url, "multi"

    # Fallback: attempt a singleton plugin dir named after the element.
    url = f"{BASE}/{name}/index.html"
    if _head_ok(url, verbose=verbose):
        return url, "singleton"

    # Last-ditch: scan known plugin landing pages for a link to <name>.html.
    for plugin, _path in PAGES.items():
        if plugin in ("index",):
            continue
        try:
            html = fetch_url(page_url(plugin), verbose=verbose)
        except Exception:  # noqa: BLE001
            continue
        ext = LinkExtractor()
        ext.feed(html)
        for h in ext.hrefs:
            m = re.search(rf"/{re.escape(name)}\.html(?:#|$)", h)
            if m:
                if h.startswith("http"):
                    return h.split("#", 1)[0], "multi"
                if h.startswith("/"):
                    return "https://gstreamer.freedesktop.org" + h, "multi"
                return f"{BASE}/{plugin}/{name}.html", "multi"
    return None


def _head_ok(url: str, *, verbose: bool = False) -> bool:
    """Best-effort liveness check. Falls back to a tiny GET on HEAD-hostile servers."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        if verbose:
            print(f"[head] {url}", file=sys.stderr)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:  # noqa: BLE001
        # Some Hotdoc deployments reject HEAD; try a range GET.
        try:
            req2 = urllib.request.Request(
                url, headers={"User-Agent": UA, "Range": "bytes=0-0"}
            )
            with urllib.request.urlopen(req2, timeout=15) as r:
                return r.status in (200, 206)
        except Exception:  # noqa: BLE001
            return False


def fetch_element(
    name: str, *, no_cache: bool = False, verbose: bool = False
) -> tuple[str, str]:
    """Fetch and cache an element page. Returns (url, text)."""
    key = f"element__{name}"
    cp = cache_path(key)
    if cp.exists() and not no_cache:
        # First line of the file is the URL comment; rest is text.
        raw = cp.read_text(encoding="utf-8")
        if raw.startswith("# URL: "):
            first, _, body = raw.partition("\n")
            return first[len("# URL: ") :].strip(), body
        return "", raw
    resolved = resolve_element(name, verbose=verbose)
    if not resolved:
        raise ValueError(f"could not resolve element {name!r}")
    url, _style = resolved
    html = fetch_url(url, verbose=verbose)
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(f"# URL: {url}\n{text}", encoding="utf-8")
    return url, text


# ── Commands ────────────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> int:
    width = max(len(n) for n in PAGES)
    for name in sorted(PAGES):
        print(f"{name:{width}s}  {BASE}{PAGES[name]}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    if args.element:
        url, text = fetch_element(
            args.element, no_cache=args.no_cache, verbose=args.verbose
        )
        if args.format == "json":
            print(
                json.dumps(
                    {"element": args.element, "url": url, "text": text}, indent=2
                )
            )
        else:
            print(text)
        return 0
    if not args.page:
        print("error: give --page or --element", file=sys.stderr)
        return 2
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
    if args.element:
        _url, text = fetch_element(args.element, verbose=args.verbose)
    else:
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
        print(
            f"section not found: {args.id!r} on "
            f"{('element ' + args.element) if args.element else ('page ' + args.page)}",
            file=sys.stderr,
        )
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


def cmd_element(args: argparse.Namespace) -> int:
    url, text = fetch_element(args.name, no_cache=args.no_cache, verbose=args.verbose)
    if args.format == "json":
        print(json.dumps({"element": args.name, "url": url, "text": text}, indent=2))
    else:
        print(f"# URL: {url}")
        print(text)
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    r = resolve_element(args.element, verbose=args.verbose)
    if not r:
        print(f"unresolved: {args.element}", file=sys.stderr)
        return 1
    url, style = r
    print(json.dumps({"element": args.element, "url": url, "style": style}, indent=2))
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
        description="Search and fetch official GStreamer documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known gstreamer.freedesktop.org pages")
    p1.add_argument("--verbose", action="store_true")
    p1.set_defaults(fn=cmd_list)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page or element")
    p2.add_argument("--page", help="page name (see list-pages)")
    p2.add_argument("--element", help="element name (e.g. filesrc, webrtcbin)")
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
    p5.add_argument("--page", help="page name")
    p5.add_argument("--element", help="element name (resolves element page)")
    p5.add_argument("--id", required=True, help="anchor id or heading keyword")
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("element", help="fetch an element doc page by name")
    p6.add_argument("--name", required=True, help="element name (e.g. filesrc)")
    p6.add_argument("--format", choices=["text", "json"], default="text")
    p6.add_argument("--no-cache", action="store_true", help="re-fetch, bypass cache")
    p6.add_argument("--verbose", action="store_true")
    p6.set_defaults(fn=cmd_element)

    p7 = sub.add_parser("resolve", help="print the URL + shape for an element name")
    p7.add_argument("--element", required=True, help="element name to resolve")
    p7.add_argument("--verbose", action="store_true")
    p7.set_defaults(fn=cmd_resolve)

    p8 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p8.add_argument("--verbose", action="store_true")
    p8.set_defaults(fn=cmd_clear_cache)

    # --dry-run is a no-op for this doc fetcher (read-only) but the convention
    # demands it be present.
    for sp in (p1, p2, p3, p4, p5, p6, p7, p8):
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="echo intent to stderr; for doc fetch this only affects `index` and network fetches (no local writes beyond cache dir creation)",
        )

    return p


def main() -> int:
    args = build_parser().parse_args()
    # Stderr-echo the effective command before running it.
    print(
        "+ gstdocs.py " + " ".join(sys.argv[1:]),
        file=sys.stderr,
    )
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
