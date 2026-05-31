#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""webrtcdocs.py — Search and fetch WebRTC specs from W3C and IETF.

Stdlib only (urllib + html.parser). Non-interactive. Caches text-extracted
pages to ~/.cache/webrtc-spec/ so repeated lookups are offline-fast.

Usage:
    webrtcdocs.py list-pages
    webrtcdocs.py list-rfcs
    webrtcdocs.py fetch --page rfc-8866
    webrtcdocs.py search --query "rtcp-fb" [--page rfc-8866]
    webrtcdocs.py section --page rfc-8866 --id 5.13
    webrtcdocs.py index
    webrtcdocs.py clear-cache

Override cache location with the WEBRTC_DOCS_CACHE env var.
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

UA = "webrtc-spec-skill/1.0 (Claude Code Agent Skill)"

# page-name -> canonical URL
PAGES: dict[str, str] = {
    # W3C TRs
    "w3c-webrtc": "https://www.w3.org/TR/webrtc/",
    "w3c-webrtc-extensions": "https://www.w3.org/TR/webrtc-extensions/",
    "w3c-webrtc-stats": "https://www.w3.org/TR/webrtc-stats/",
    "w3c-mediacapture-streams": "https://www.w3.org/TR/mediacapture-streams/",
    "w3c-screen-capture": "https://www.w3.org/TR/screen-capture/",
    "w3c-webcodecs": "https://www.w3.org/TR/webcodecs/",
    "w3c-webtransport": "https://www.w3.org/TR/webtransport/",
    # IETF RFCs
    "rfc-8825": "https://datatracker.ietf.org/doc/html/rfc8825",
    "rfc-8826": "https://datatracker.ietf.org/doc/html/rfc8826",
    "rfc-8827": "https://datatracker.ietf.org/doc/html/rfc8827",
    "rfc-8828": "https://datatracker.ietf.org/doc/html/rfc8828",
    "rfc-8829": "https://datatracker.ietf.org/doc/html/rfc8829",
    "rfc-9429": "https://datatracker.ietf.org/doc/html/rfc9429",
    "rfc-8831": "https://datatracker.ietf.org/doc/html/rfc8831",
    "rfc-8832": "https://datatracker.ietf.org/doc/html/rfc8832",
    "rfc-8834": "https://datatracker.ietf.org/doc/html/rfc8834",
    "rfc-8835": "https://datatracker.ietf.org/doc/html/rfc8835",
    "rfc-8836": "https://datatracker.ietf.org/doc/html/rfc8836",
    "rfc-8837": "https://datatracker.ietf.org/doc/html/rfc8837",
    "rfc-8866": "https://datatracker.ietf.org/doc/html/rfc8866",
    "rfc-8445": "https://datatracker.ietf.org/doc/html/rfc8445",
    "rfc-8489": "https://datatracker.ietf.org/doc/html/rfc8489",
    "rfc-8656": "https://datatracker.ietf.org/doc/html/rfc8656",
    "rfc-7064": "https://datatracker.ietf.org/doc/html/rfc7064",
    "rfc-7065": "https://datatracker.ietf.org/doc/html/rfc7065",
    "rfc-5764": "https://datatracker.ietf.org/doc/html/rfc5764",
    "rfc-3711": "https://datatracker.ietf.org/doc/html/rfc3711",
    "rfc-3550": "https://datatracker.ietf.org/doc/html/rfc3550",
    "rfc-6184": "https://datatracker.ietf.org/doc/html/rfc6184",
    "rfc-7798": "https://datatracker.ietf.org/doc/html/rfc7798",
    "rfc-7741": "https://datatracker.ietf.org/doc/html/rfc7741",
    "rfc-7587": "https://datatracker.ietf.org/doc/html/rfc7587",
    "rfc-9725": "https://datatracker.ietf.org/doc/html/rfc9725",
    "rfc-8838": "https://datatracker.ietf.org/doc/html/rfc8838",
    "rfc-9143": "https://datatracker.ietf.org/doc/html/rfc9143",
    "rfc-8853": "https://datatracker.ietf.org/doc/html/rfc8853",
    "rfc-8851": "https://datatracker.ietf.org/doc/html/rfc8851",
    "rfc-8843": "https://datatracker.ietf.org/doc/html/rfc8843",
    "draft-whep": "https://datatracker.ietf.org/doc/draft-ietf-wish-whep/",
}

# Human-readable titles for list-rfcs output
TITLES: dict[str, str] = {
    "w3c-webrtc": "WebRTC 1.0: Real-Time Communication Between Browsers (W3C REC)",
    "w3c-webrtc-extensions": "WebRTC Extensions (W3C)",
    "w3c-webrtc-stats": "Identifiers for WebRTC's Statistics API (W3C)",
    "w3c-mediacapture-streams": "Media Capture and Streams (getUserMedia) (W3C)",
    "w3c-screen-capture": "Screen Capture (W3C)",
    "w3c-webcodecs": "WebCodecs (W3C)",
    "w3c-webtransport": "WebTransport (W3C)",
    "rfc-8825": "Overview: Real-Time Protocols for Browser-Based Applications",
    "rfc-8826": "Security Considerations for WebRTC",
    "rfc-8827": "WebRTC Security Architecture",
    "rfc-8828": "WebRTC IP Address Handling Requirements",
    "rfc-8829": "JSEP — JavaScript Session Establishment Protocol (original)",
    "rfc-9429": "JSEP — JavaScript Session Establishment Protocol (bis, obsoletes 8829)",
    "rfc-8831": "WebRTC Data Channels",
    "rfc-8832": "WebRTC Data Channel Establishment Protocol (DCEP)",
    "rfc-8834": "RTP Usage for WebRTC",
    "rfc-8835": "Transports for WebRTC",
    "rfc-8836": "Congestion Control Requirements for Interactive Real-Time Media",
    "rfc-8837": "DSCP Packet Markings for WebRTC QoS",
    "rfc-8866": "SDP: Session Description Protocol (obsoletes 4566)",
    "rfc-8445": "ICE — Interactive Connectivity Establishment",
    "rfc-8489": "STUN — Session Traversal Utilities for NAT",
    "rfc-8656": "TURN — Traversal Using Relays around NAT",
    "rfc-7064": "URI Scheme for STUN",
    "rfc-7065": "URI Scheme for TURN",
    "rfc-5764": "DTLS-SRTP — Security Descriptions for Media Streams",
    "rfc-3711": "SRTP — Secure Real-time Transport Protocol",
    "rfc-3550": "RTP — Real-time Transport Protocol",
    "rfc-6184": "RTP Payload Format for H.264",
    "rfc-7798": "RTP Payload Format for HEVC",
    "rfc-7741": "RTP Payload Format for VP8",
    "rfc-7587": "RTP Payload Format for Opus",
    "rfc-9725": "WHIP — WebRTC-HTTP Ingestion Protocol",
    "rfc-8838": "Trickle ICE",
    "rfc-9143": "Negotiating Media Multiplexing Using the Session Description Protocol (BUNDLE)",
    "rfc-8853": "Using Simulcast in SDP and RTP Sessions",
    "rfc-8851": "RTP Stream Identifier Source Description (rid)",
    "rfc-8843": "Negotiating Media Multiplexing with ICE/DTLS in SDP",
    "draft-whep": "WHEP — WebRTC-HTTP Egress Protocol (draft)",
}

CACHE_DIR = Path(
    os.environ.get("WEBRTC_DOCS_CACHE", Path.home() / ".cache" / "webrtc-spec")
)


class TextExtractor(HTMLParser):
    """Convert W3C / IETF HTML pages to searchable text."""

    SKIP_TAGS = {"script", "style", "nav", "footer"}
    HEAD_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.buf: list[str] = []
        self.skip = 0
        self.in_pre = 0
        self.pending_anchor: str | None = None

    def handle_starttag(self, tag, attrs):
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
                self.buf.append(f"[§{self.pending_anchor}] ")
                self.pending_anchor = None
        elif tag in ("section", "div"):
            if "id" in a and self.pending_anchor is None:
                self.pending_anchor = a["id"]
        elif tag == "pre":
            self.in_pre += 1
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")
        elif tag == "p":
            self.buf.append("\n\n")
        elif tag == "li":
            self.buf.append("\n- ")
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "pre":
            self.in_pre = max(0, self.in_pre - 1)
            self.buf.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.buf.append("`")

    def handle_data(self, data):
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
            f"unknown page: {page!r}. Run `webrtcdocs.py list-pages` to see valid names."
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


def cmd_list_pages(args):
    width = max(len(n) for n in PAGES)
    for name, url in sorted(PAGES.items()):
        print(f"{name:{width}s}  {url}")
    return 0


def cmd_list_rfcs(args):
    rows = [(n, TITLES.get(n, ""), PAGES[n]) for n in PAGES]
    rows.sort()
    w1 = max(len(r[0]) for r in rows)
    w2 = max(len(r[1]) for r in rows)
    for n, t, u in rows:
        print(f"{n:{w1}s}  {t:{w2}s}  {u}")
    return 0


def cmd_fetch(args):
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


def cmd_index(args):
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


def cmd_search(args):
    if args.regex:
        pattern = re.compile(args.query, re.IGNORECASE)
    else:
        pattern = re.compile(re.escape(args.query), re.IGNORECASE)
    pages = [args.page] if args.page else list(PAGES)
    hits = []
    for page in pages:
        try:
            text = load_or_fetch(page, verbose=args.verbose)
        except Exception as e:
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
                    url = url.rstrip("/") + f"#{anchor}"
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


def cmd_section(args):
    text = load_or_fetch(args.page, verbose=args.verbose)
    lines = text.splitlines()
    start = None
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


def cmd_clear_cache(args):
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"cleared {CACHE_DIR}", file=sys.stderr)
    else:
        print(f"nothing to clear ({CACHE_DIR} does not exist)", file=sys.stderr)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        description="Search and fetch WebRTC specs (W3C + IETF).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list-pages", help="list known doc pages")
    p1.add_argument("--verbose", action="store_true")
    p1.set_defaults(fn=cmd_list_pages)

    pr = sub.add_parser("list-rfcs", help="list known RFCs + W3C TRs with titles")
    pr.add_argument("--verbose", action="store_true")
    pr.set_defaults(fn=cmd_list_rfcs)

    p2 = sub.add_parser("fetch", help="fetch and print a doc page as text")
    p2.add_argument("--page", required=True)
    p2.add_argument("--format", choices=["text", "json"], default="text")
    p2.add_argument("--no-cache", action="store_true")
    p2.add_argument("--verbose", action="store_true")
    p2.set_defaults(fn=cmd_fetch)

    p3 = sub.add_parser("index", help="pre-fetch every known page")
    p3.add_argument("--verbose", action="store_true")
    p3.set_defaults(fn=cmd_index)

    p4 = sub.add_parser("search", help="search for a term across cached pages")
    p4.add_argument("--query", required=True)
    p4.add_argument("--page")
    p4.add_argument("--regex", action="store_true")
    p4.add_argument("--context", type=int, default=3)
    p4.add_argument("--limit", type=int, default=20)
    p4.add_argument("--format", choices=["text", "json"], default="text")
    p4.add_argument("--verbose", action="store_true")
    p4.set_defaults(fn=cmd_search)

    p5 = sub.add_parser("section", help="extract one section by anchor or keyword")
    p5.add_argument("--page", required=True)
    p5.add_argument("--id", required=True)
    p5.add_argument("--verbose", action="store_true")
    p5.set_defaults(fn=cmd_section)

    p6 = sub.add_parser("clear-cache", help="delete the local cache directory")
    p6.add_argument("--verbose", action="store_true")
    p6.set_defaults(fn=cmd_clear_cache)

    # Harmless global that many skills expose; accept and ignore for docs fetchers.
    for sp in [p1, pr, p2, p3, p4, p5, p6]:
        sp.add_argument("--dry-run", action="store_true", help="no-op (docs fetcher)")

    return p


def main():
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
