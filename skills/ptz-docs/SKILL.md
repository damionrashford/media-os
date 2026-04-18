---
name: ptz-docs
description: >
  Search and fetch docs for PTZ camera control protocols: Sony VISCA (Command List v2.00, BRC-H900, SRG-300H, PTZOptics VISCA over IP) — byte-level serial or UDP:52381 with payload-wrapped VISCA, and ONVIF (onvif.org profiles — S streaming deprecated, T successor with H.264/H.265/metadata, G on-device recording, Q deprecated, M metadata/analytics, A/C/D access control). WS-Discovery multicast 239.255.255.250:3702, SOAP/XML with WS-Security UsernameToken digest, Device/Media/PTZ/Imaging/Events/Recording services. Use when the user asks to look up a VISCA command, find an ONVIF service, check WS-Discovery packet structure, verify PTZ protocol syntax, or read the canonical PTZ specs.
argument-hint: "[query]"
---

# PTZ Docs

**Context:** $ARGUMENTS

Anti-hallucination guardrail for PTZ protocol work. Fetches and searches the canonical Sony VISCA PDFs and the onvif.org profile pages. Pair with `ptz-visca` (wire protocol) and `ptz-onvif` (SOAP control) for actual camera operations.

## Quick start

- **Find a VISCA command byte sequence:** → Step 2 (`search --query "<command>"`)
- **Read an ONVIF profile feature list:** → Step 3 (`section --page onvif-profile-t --id <heading>`)
- **Grab a full reference page:** → Step 4 (`fetch --page <name>`)
- **Pre-cache everything for offline:** → Step 5 (`index`)
- **See the full catalog:** → Step 1 (`list-pages`)

## When to use

- Verify a VISCA command byte code (e.g. `8x 01 06 01 VV WW YY YY ZZ ZZ FF` for Pan-Tilt Drive) before sending.
- Confirm ONVIF service endpoint names (PTZ, Media, Imaging, Events, Recording, Analytics).
- Check which ONVIF profile applies (S deprecated, T replaces S, G recording, M analytics, A/C/D access).
- Cite the canonical Sony or ONVIF URL in a response.

## Step 1 — Know the page catalog

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py list-pages
```

| Page | What it is |
|---|---|
| `visca-v2` | Sony VISCA Command List v2.00 (interchangeable lens) PDF |
| `visca-brc-h900` | Sony BRC-H900 VISCA reference PDF |
| `visca-srg-300h` | Sony SRG-300H VISCA-over-IP PDF (AES6 manual) |
| `visca-ptzoptics` | PTZOptics community VISCA-over-IP reference PDF |
| `onvif-profiles` | onvif.org Profiles hub (all profiles overview) |
| `onvif-specifications` | onvif.org Profile Specifications index |
| `onvif-profile-overview` | Profile feature overview PDF (v2.1) |
| `onvif-profile-s` | Profile S (streaming — deprecated 2027-03-31) |

Only the HTML pages are text-searchable. PDF pages return a URL + note (PDF bytes aren't parsed).

## Step 2 — Search first

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py search --query "Pan Tilt" --limit 5
```

Scope to a single page when you know which one:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py search --query "GetProfiles" --page onvif-profile-s
```

Output per hit:

```
--- <page>:<line> — <nearest heading>
<URL with #anchor>
<snippet ±3 lines>
```

Use `--format json` for structured output.

## Step 3 — Read one section

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py section --page onvif-profiles --id profile-s
```

`--id` accepts an anchor id (from `[§...]` in search hits) or a heading keyword.

## Step 4 — Fetch whole page

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py fetch --page onvif-profile-s
```

## Step 5 — Pre-cache

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py index
```

Override cache via `PTZ_DOCS_CACHE=/path`. Clear: `clear-cache`.

## Gotchas

- **VISCA PDFs are binary — not searchable by this skill.** The script resolves the URL and confirms reachability but does NOT parse PDF bytes. For byte tables, download and open the PDF in a real reader, or use the curated excerpts in `references/visca-commands.md` / `ptz-visca` skill.
- **ONVIF Profile S is deprecated as of 2027-03-31.** New deployments should target Profile T (H.264 + H.265 + metadata + bidirectional audio). Profile S continues to work but won't be promoted.
- **ONVIF Profile Q is formally deprecated** — don't use it for anything new.
- **WS-Discovery does NOT cross subnets.** It's a link-local multicast at `239.255.255.250:3702`. For remote cameras, use unicast `GetCapabilities` to a known IP or run a discovery proxy on the camera subnet.
- **ONVIF uses SOAP 1.2 with WS-Security UsernameToken digest** — PasswordText is allowed by spec but many cameras reject it; always compute the digest.
- **VISCA-over-IP is NOT the same as VISCA-over-serial with a TCP tunnel.** IP wraps each serial VISCA message in an 8-byte payload header (payload type, payload length, seq#). UDP port 52381. Sony, PTZOptics, AVer use the same wrapper.
- **PTZOptics community ref isn't authoritative** but it's widely used because the Sony PDFs are paywalled/login-gated for non-partner docs. Treat as a secondary source; cross-check with the Sony BRC/SRG PDFs.
- **Fetching onvif.org PDFs** — direct PDF URLs return bytes the script can confirm but doesn't index; the HTML profile pages (`onvif-profiles`, `onvif-profile-s`) are where search actually works.

## Examples

### Example 1 — "What's the VISCA byte sequence for Pan-Tilt Drive?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py search --query "Pan.Tilt" --regex --limit 5
```

Then open the PDF URL printed in the hit for the exact byte table.

### Example 2 — "Does Profile T include metadata streaming?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py search --query "metadata" --page onvif-profile-overview
```

### Example 3 — "Which PTZ subcommand is preset recall?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py search --query "preset recall"
```

### Example 4 — "Profile S specification URL for citation"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ptzdocs.py list-pages | grep profile-s
```

## Reference docs

- [`references/visca-commands.md`](references/visca-commands.md) — curated VISCA command byte table (the big excerpt that the PDF search cannot provide).
- [`references/onvif-services.md`](references/onvif-services.md) — per-profile ONVIF service matrix (Device/Media/PTZ/Imaging/Events/Recording/Analytics) and SOAP endpoint paths.

## Troubleshooting

### Error: `unknown page: foo`

**Cause:** Not in catalog.
**Solution:** Run `list-pages`.

### PDF page returns "binary page — URL only"

**Cause:** The skill doesn't parse PDFs (stdlib only).
**Solution:** Open the printed URL in a browser/Preview/Acrobat, or search `references/visca-commands.md` which has the curated byte table.

### Search returns zero hits on ONVIF pages

**Cause:** ONVIF marketing pages are light on technical detail.
**Solution:** Drop the `--page` filter to search across all pages, or try `onvif-profile-overview` (the v2.1 PDF summary link).

### Cache stale after upstream edits

**Solution:** `clear-cache` then `index`, or `fetch --no-cache --page <name>`.
