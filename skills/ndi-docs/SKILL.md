---
name: ndi-docs
description: >
  Search and fetch official NDI documentation from docs.ndi.video (Vizrt, formerly NewTek NDI): SDK landing, release notes, port numbers (mDNS 5353, messaging 5960, streams 5961+), HDR spec (PQ and HLG), SDK vs Advanced SDK differences, NDI 6 features (native HDR, HX3, Agilex 7, NDI Bridge), plus DistroAV (the OBS plugin formerly obs-ndi) README fallback. Use when the user asks to look up an NDI API, NDIlib_send/recv/find functions, check NDI port numbers, verify NDI wire protocol details (SpeedHQ codec, NDI|HX vs NDI full, NDI 6 vs NDI 5 differences), read NDI SDK docs, check SDK-vs-Advanced-SDK feature matrix, integrate NDI with OBS via DistroAV, or verify an NDI call against the real documentation.
argument-hint: "[query]"
---

# NDI Docs

**Context:** $ARGUMENTS

## Quick start

- **Find an NDI API / feature / spec detail:** → Step 2 (`search --query <term>`)
- **Read the full section for a topic:** → Step 3 (`section --page <page> --id <anchor>`)
- **Grab a whole doc page:** → Step 4 (`fetch --page <name>`)
- **Prime cache for offline use:** → Step 5 (`index`)

## When to use

- User asks "what port does NDI use?" or "what's NDI|HX?" or "does NDI 6 support HDR?"
- Need to verify a wire-protocol detail before recommending config (mDNS 5353, TCP 5960, streams 5961+).
- Need the exact SDK-vs-Advanced-SDK feature matrix (routing, multicast, access-control, compressed passthrough).
- Need the official NDI 6 / HX3 / Agilex 7 feature list before claiming support.
- Need to cite the canonical `docs.ndi.video` URL.
- Integrating NDI with OBS → check DistroAV (not "obs-ndi" — that repo was renamed/forked).

---

## Step 1 — Know the page catalog

The script only works against a fixed list of known docs.ndi.video pages plus the DistroAV GitHub README. Get the list:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py list-pages
```

Common picks:

| Question | Page |
|---|---|
| "Which NDI SDK do I need?" | `sdk-landing` |
| "What changed in NDI 6?" | `tech-ndi6` |
| "Release notes / version history" | `sdk-release-notes` |
| "Which ports does NDI use?" | `sdk-port-numbers` |
| "Does NDI support HDR? PQ / HLG?" | `sdk-hdr` |
| "SDK vs Advanced SDK differences" | `faq-sdk-vs-advanced` |
| "OBS + NDI setup" | `distroav` |
| "NDI docs root / landing" | `docs-root` |

Read [`references/pages.md`](references/pages.md) for the full catalog + use-cases.

---

## Step 2 — Search first

When the user names an NDI feature / port / flag / function, search across all pages:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "multicast" --limit 5
```

When you know the page, scope it (faster, less noise):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "5960" --page sdk-port-numbers
```

Output format per hit:

```
--- <page>:<line> — <nearest heading>
<canonical URL with anchor>
<±3 lines of context>
```

Use `--format json` for machine-parseable output.

First run downloads the page; subsequent runs hit the local cache at `~/.cache/ndi-docs/`.

---

## Step 3 — Read one section in full

When a hit points to a specific topic and you want the whole block:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py section --page sdk-port-numbers --id discovery
```

`--id` accepts an anchor id OR a heading keyword fallback.

---

## Step 4 — Fetch a whole page

Rarely needed; search/section are almost always better.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py fetch --page tech-ndi6
```

Pair with `--format json` for structured output.

---

## Step 5 — Prime the cache (optional)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py index
```

Fetches every known page into `~/.cache/ndi-docs/`. Override with `export NDI_DOCS_CACHE=/path`.
Clear: `uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py clear-cache`.

---

## Gotchas

- **NDI is proprietary. There is NO open-source libndi reimplementation.** Every NDI-capable tool links against NewTek/Vizrt's binary `libndi.so` / `Processing.NDI.Lib.dll` / `libndi.dylib` that ships with the SDK installer. "Build NDI support from source" is not a thing.
- **The SDK cannot legally be redistributed inside ffmpeg binaries.** That's why ffmpeg's NDI support was removed from mainline (non-redistributable) and why OBS-NDI was renamed to DistroAV and must be installed separately — it dlopens the system-installed NDI runtime.
- **Wire protocol uses THREE port families.** mDNS discovery on UDP 5353 (standard Bonjour), messaging on TCP 5960, and each source opens streams starting at TCP/UDP 5961 and incrementing. Firewall rules must open 5353/udp + 5960-5999/tcp + 5960-5999/udp minimum, more if you host many sources.
- **NDI full uses the SpeedHQ codec** (Vizrt's proprietary DCT-based codec, ~15:1 compression, visually lossless on broadcast material). It is I-frame-only. Bitrate is roughly 100–250 Mbps for 1080p60.
- **NDI|HX is H.264 or H.265** (the "HX" family — HX2 = AVC, HX3 = HEVC added in NDI 6). NDI|HX is NOT SpeedHQ; it's much lower bitrate (~8–20 Mbps) at the cost of latency (P/B-frames introduce encode/decode delay). Don't confuse SpeedHQ bitrates with HX.
- **NDI 6 adds native HDR (PQ and HLG) and 10/12/16-bit pixel formats.** Before NDI 6, HDR was unofficial / metadata-only. If a user says "NDI HDR", clarify they're on NDI 6+ runtime on both sender and receiver.
- **Standard SDK is free for non-commercial use only.** Commercial redistribution requires the Advanced SDK licence. Pricing is via Vizrt sales — not publicly listed.
- **Advanced SDK unlocks routing, access-control (groups), multicast sending, compressed passthrough (send already-encoded streams without re-encode), custom frame sync, and a C++ wrapper.** Standard SDK is send/recv/find only.
- **NDI Bridge bridges NDI across subnets/WANs** using TCP relay through a server. Required when mDNS can't traverse (LAN segmentation, VLAN isolation, site-to-site). Without Bridge, NDI is LAN-only.
- **NDI Discovery Server is an alternative to mDNS** — when mDNS is blocked on a hostile network, run a Discovery Server and point clients at it via env var `NDI_DISCOVERY_SERVER=ip:port`.
- **DistroAV (the OBS plugin) is the successor to obs-ndi.** The obs-ndi GitHub repo is archived/stale. Install DistroAV from `github.com/DistroAV/DistroAV` releases or via OBS's in-app plugin installer. It requires the NDI runtime installed separately (the SDK or the standalone Tools/Runtime installer).
- **Fallback when docs.ndi.video is down:** the DistroAV README (`page=distroav`) is hosted on GitHub raw and covers install + hotkey + common config.
- **Cache is per-page only, not per-NDI-version.** After a NDI release shifts spec pages, `clear-cache` then `index`.
- **The script is stdlib-only** — no pip install. Python 3.9+.

---

## Examples

### Example 1 — "What ports does NDI need open on the firewall?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "port" --page sdk-port-numbers
```

### Example 2 — "Does NDI support HDR PQ?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "PQ" --page sdk-hdr
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py fetch --page sdk-hdr
```

### Example 3 — "What's the difference between the SDK and the Advanced SDK?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py fetch --page faq-sdk-vs-advanced
```

### Example 4 — "What did NDI 6 add?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "NDI 6" --page tech-ndi6 --limit 10
```

### Example 5 — "OBS + NDI setup steps"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndidocs.py search --query "install" --page distroav
```

---

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** Name isn't in the catalog.
**Solution:** Run `list-pages` for valid names.

### Error: `urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause:** macOS Python missing certs.
**Solution:** Run `/Applications/Python\ 3.x/Install\ Certificates.command` or set `SSL_CERT_FILE`. Don't disable SSL verification.

### Search returns zero hits

**Cause:** Term doesn't exist on the selected page or docs.ndi.video moved the page.
**Solution:** Drop `--page` to search all pages. Try broader query. Some details live in the DistroAV README rather than docs.ndi.video.

### Cache stale after an NDI SDK release

**Solution:** `clear-cache` then `index`.

---

## Reference docs

- Full URL catalog, wire-protocol summary, and SDK-vs-Advanced-SDK matrix → `references/pages.md`.
