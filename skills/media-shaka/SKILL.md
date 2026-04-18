---
name: media-shaka
description: >
  Commercial DRM packaging with Shaka Packager (packager): Widevine (Common Encryption for DASH+HLS), PlayReady, FairPlay, multi-DRM, ClearKey, key rotation, CMAF packaging, EMSG markers, SCTE-35 ad signaling. Use when the user asks to package Widevine DRM, build FairPlay HLS, do multi-DRM DASH+HLS CMAF, integrate with a Widevine/PlayReady license server, ship studio-grade DRM-protected content, or package CENC with PSSH boxes.
argument-hint: "[operation]"
---

# Media Shaka

**Context:** $ARGUMENTS

Shaka Packager is Google's production DRM packager — the same tool used by YouTube, Netflix-style pipelines, and most commercial OTT stacks. It does NOT re-encode: inputs must already be encoded at the bitrates/resolutions you want to ship. It outputs encrypted CMAF (fMP4) segments plus DASH `.mpd` and HLS `.m3u8` manifests that point at the SAME encrypted files.

## Quick start

- **Test encryption (no license server):** ClearKey → Step 3 (CENC recipe)
- **Production Widevine (Google/YouTube):** Step 5 (license-server integration)
- **Multi-DRM DASH+HLS for studio OTT:** `cbcs` + Widevine + PlayReady → Step 4
- **FairPlay (Apple HLS):** `cbcs` + SAMPLE-AES → Step 6
- **Inspect, validate, generate keys:** `scripts/shaka.py` subcommands

## When to use

- Packaging already-encoded renditions into encrypted DASH+HLS for a commercial OTT service.
- Integrating with a Widevine / PlayReady / FairPlay license server (EZDRM, PallyCon, Axinom, BuyDRM, DRMtoday, Irdeto, or Google's Widevine cloud).
- Building CMAF with common encryption so one set of `.m4s` files plays on Android (Widevine), iOS/Safari (FairPlay), and Edge/Xbox (PlayReady).
- Generating test ClearKey streams for development against Shaka Player or dash.js.
- You do NOT use Shaka Packager for: re-encoding, stabilization, filtering. Encode first with ffmpeg, then package.

## Step 1 — Install

Pick one:

```bash
# macOS
brew install shaka-packager

# Verify
packager --version

# Docker (CI, reproducible)
docker run --rm -v "$PWD":/work -w /work google/shaka-packager \
  packager --version

# Prebuilt binary (Linux / macOS / Windows)
# https://github.com/shaka-project/shaka-packager/releases
```

`scripts/shaka.py check` wraps the version probe.

## Step 2 — Decide DRM scheme

| Scheme | Cipher | DASH | HLS | FairPlay | Notes |
|--------|--------|------|-----|----------|-------|
| `cenc`  | AES-CTR full sample | Yes | Legacy | No | DASH default pre-2018, NOT FairPlay compatible |
| `cens`  | AES-CTR pattern 1:9 | Yes | No | No | Rarely used |
| `cbc1`  | AES-CBC full sample | Yes | No | No | Legacy |
| `cbcs`  | AES-CBC pattern 1:9 | Yes | Yes | **Yes** | **Recommended for all new work** |

**Rule:** use `cbcs` unless a specific device mandate forces `cenc`. Widevine 14.0+, PlayReady, and FairPlay all support `cbcs`, so one set of `.m4s` files plays on everything. This is the whole point of CMAF.

KIDs and keys are 32-char hex (16 bytes each). KID must be unique per content (use `scripts/shaka.py gen-clearkey-keys`).

## Step 3 — Package ClearKey CENC (test / demo)

Encodes must already exist. Package a 1080p + 720p + audio ladder:

```bash
packager \
  in=1080.mp4,stream=video,output=1080.mp4,drm_label=HD \
  in=720.mp4,stream=video,output=720.mp4,drm_label=SD \
  in=audio.m4a,stream=audio,output=audio.mp4 \
  --enable_raw_key_encryption \
  --keys label=HD:key_id=11223344556677889900aabbccddeeff:key=00112233445566778899aabbccddeeff,label=SD:key_id=aabbccddeeff00112233445566778899:key=ffeeddccbbaa99887766554433221100 \
  --protection_scheme cbcs \
  --segment_duration 4 \
  --clear_lead 10 \
  --mpd_output manifest.mpd \
  --hls_master_playlist_output master.m3u8
```

- `--clear_lead 10` leaves the first 10s unencrypted so the player can start before the license arrives.
- `--segment_duration 4` matches the CMAF norm (Apple / DASH-IF recommend 4–6 s).
- Output is a DASH `.mpd` **and** an HLS `.m3u8` master, both referencing the same encrypted fragmented-MP4 files.

Test playback: https://shaka-player-demo.appspot.com/ (paste ClearKey JSON).

## Step 4 — Multi-DRM DASH+HLS (production)

Widevine + PlayReady on DASH, FairPlay on HLS, all `cbcs`, same segments:

```bash
packager \
  in=1080.mp4,stream=video,output=1080.mp4,drm_label=HD \
  in=720.mp4,stream=video,output=720.mp4,drm_label=SD \
  in=audio.m4a,stream=audio,output=audio.mp4 \
  --enable_widevine_encryption \
  --key_server_url https://license.widevine.com/cenc/getcontentkey/YOUR_PROVIDER \
  --signer "your-signer-name" \
  --aes_signing_key YOUR_AES_SIGNING_KEY_HEX \
  --aes_signing_iv YOUR_AES_SIGNING_IV_HEX \
  --enable_playready_encryption \
  --playready_key_server_url https://your-playready-license-server/rightsmanager.asmx \
  --protection_scheme cbcs \
  --segment_duration 4 \
  --mpd_output manifest.mpd \
  --hls_master_playlist_output master.m3u8
```

For vendor-managed DRM (EZDRM / PallyCon / Axinom), the vendor gives you the URL, signer, AES key, AES IV. You do NOT run your own Widevine license server unless you are a Google-certified integrator.

## Step 5 — Widevine-only (Google cloud or private license server)

```bash
packager \
  in=video.mp4,stream=video,output=video.mp4,drm_label=HD \
  in=audio.m4a,stream=audio,output=audio.mp4 \
  --enable_widevine_encryption \
  --key_server_url https://license.widevine.com/cenc/getcontentkey/YOUR_PROVIDER \
  --content_id $(printf 'my-content-42' | xxd -p) \
  --signer "your-signer-name" \
  --aes_signing_key KEY_HEX --aes_signing_iv IV_HEX \
  --protection_scheme cbcs \
  --mpd_output manifest.mpd
```

`--content_id` must be hex-encoded. PSSH is auto-inserted into the `moov` box — required for Widevine CDM to recognise the content.

## Step 6 — FairPlay HLS only

```bash
packager \
  in=video.mp4,stream=video,output=video.mp4 \
  in=audio.m4a,stream=audio,output=audio.mp4 \
  --enable_raw_key_encryption \
  --keys label=:key_id=KID_HEX:key=KEY_HEX \
  --protection_scheme cbcs \
  --hls_master_playlist_output master.m3u8
```

FairPlay uses the Apple SAMPLE-AES scheme (which is `cbcs` at the cipher level). You still need a FairPlay Key Server for production: the client sends an SPC, the server returns a CKC. Shaka Packager does the bit-level work, NOT the SPC/CKC exchange.

## Step 7 — Verify

```bash
# DASH
curl -s https://validator.dashif.org/validator/ -F "file=@manifest.mpd"

# HLS
mediastreamvalidator master.m3u8     # Apple tool
hlsreport.pl -s master.m3u8           # formatted report

# Probe PSSH boxes
MP4Box -info video.mp4                 # GPAC
mp4dump --verbosity 2 video.mp4        # Bento4
```

Shaka Player demo page is the fastest end-to-end check.

## Available scripts

- **`scripts/shaka.py check`** — report `packager --version`.
- **`scripts/shaka.py gen-clearkey-keys`** — emit a random 16-byte KID + key pair (hex).
- **`scripts/shaka.py clearkey`** — package DASH+HLS with raw key encryption.
- **`scripts/shaka.py widevine`** — package with Widevine license-server integration.
- **`scripts/shaka.py multi-drm`** — Widevine + PlayReady combined.
- **`scripts/shaka.py fairplay-hls`** — HLS-only FairPlay (`cbcs`) output.

All commands accept `--dry-run` (print the `packager` invocation) and `--verbose`. Stdlib-only, non-interactive.

## Workflow

```bash
# Generate a test key pair
uv run ${CLAUDE_SKILL_DIR}/scripts/shaka.py gen-clearkey-keys

# Package a test stream
uv run ${CLAUDE_SKILL_DIR}/scripts/shaka.py clearkey \
  --inputs-video 1080.mp4 720.mp4 \
  --input-audio audio.m4a \
  --outdir out/ \
  --scheme cbcs \
  --keys "label=HD:kid=HEX:key=HEX" "label=SD:kid=HEX:key=HEX"

# Package against a Widevine license server
uv run ${CLAUDE_SKILL_DIR}/scripts/shaka.py widevine \
  --inputs 1080.mp4 720.mp4 audio.m4a \
  --key-server https://license.widevine.com/cenc/getcontentkey/PROVIDER \
  --signer "signer-name" --aes-key HEX --aes-iv HEX \
  --outdir out/
```

## Reference docs

- Read [`references/shaka.md`](references/shaka.md) for protection-scheme matrix, DRM UUIDs, stream descriptor syntax, manifest options, live vs VOD, license-server vendor list, PSSH structure, FAST/live recipes, validator commands.

## Gotchas

- Shaka Packager does **NOT re-encode**. If your 1080p source is 9 Mbps and you pass it in, the output is 9 Mbps. Encode the ladder with ffmpeg first.
- `cbcs` is the modern default. `cenc` is still correct for legacy DASH-only players but blocks FairPlay.
- Widevine 14.0+ supports `cbcs` — that is what unified Apple + Google and killed the "package twice" era. Use `cbcs`.
- KIDs and keys are **32 hex chars (16 bytes)**. Any other length silently breaks.
- **KID must be unique per content.** Reusing a KID means one revocation kills your whole catalog.
- `drm_label=HD` / `SD` / `UHD1` / `UHD2` / `AUDIO` maps to Widevine content-type levels. HD and above requires hardware-backed CDM on Android → you must set the label correctly or the license server will refuse playback.
- `--clear_lead N` — seconds of unencrypted prefix. Typical: 10 for VOD, 0 for anti-piracy priority.
- Inputs must be MP4 (or WebM/MKV, but MP4 is strongly preferred for CMAF interop).
- Manifest output: `--mpd_output` (DASH), `--hls_master_playlist_output` (HLS). Both can coexist and reference the same `.m4s` files.
- FairPlay key delivery is **Apple proprietary**. Shaka handles the bitstream; you still need a FairPlay Key Server for SPC/CKC.
- PlayReady requires `cdm_data` for some WMDRM flows — usually the vendor console generates it.
- PSSH boxes are auto-generated for Widevine/PlayReady. For raw-key, pass `--pssh HEX` if a specific player demands it.
- SCTE-35 markers and EMSG events are **preserved** if present in the input — Shaka does not generate them. Insert them at the encode step.
- Trick-play: package a low-fps rendition with `trick_play_factor=4` in the stream descriptor.
- Shaka Packager is FOSS and costs nothing. The Widevine **service** (license server) is what costs money.
- Always validate: DASH-IF conformance tool + Apple `mediastreamvalidator`. A packager bug can ship silently and break playback on one specific device family.

## Examples

### Example 1: ClearKey test stream for Shaka Player demo

```bash
uv run scripts/shaka.py gen-clearkey-keys
# -> kid=abc...  key=def...

uv run scripts/shaka.py clearkey \
  --inputs-video 1080.mp4 720.mp4 --input-audio audio.m4a \
  --scheme cbcs \
  --keys "label=HD:kid=abc...:key=def..." "label=SD:kid=abc...:key=def..." \
  --outdir out/
```

Load `out/manifest.mpd` in https://shaka-player-demo.appspot.com with ClearKey JSON `{ "<kid-base64>": "<key-base64>" }`.

### Example 2: Production multi-DRM via EZDRM

```bash
packager \
  in=1080.mp4,stream=video,output=1080.mp4,drm_label=HD \
  in=audio.m4a,stream=audio,output=audio.mp4 \
  --enable_widevine_encryption \
  --key_server_url "https://widevine-proxy.ezdrm.com/proxy?pX=XXXXXX" \
  --signer "ezdrm" --aes_signing_key KEY --aes_signing_iv IV \
  --enable_playready_encryption \
  --playready_key_server_url "https://playready.ezdrm.com/cency/preauth.aspx?pX=XXXXXX" \
  --protection_scheme cbcs \
  --mpd_output manifest.mpd --hls_master_playlist_output master.m3u8
```

## Troubleshooting

### Error: "Key not found for DRM label HD"
Cause: `--keys` omitted the `HD` label referenced by an `in=...,drm_label=HD` descriptor.
Fix: ensure every `drm_label` appears in `--keys label=...:key_id=...:key=...`.

### Error: "PSSH box missing / CDM refused"
Cause: raw-key mode with no PSSH and a player that requires one.
Fix: add `--pssh WIDEVINE_PSSH_HEX` — generate with `packager --dump_pssh` or your license server.

### Error: "FairPlay playback fails on iOS but Android works"
Cause: used `--protection_scheme cenc`. FairPlay requires `cbcs`.
Fix: re-package with `--protection_scheme cbcs`.

### Error: "Manifest plays clear, no encryption"
Cause: forgot `--enable_raw_key_encryption` or the equivalent `--enable_widevine_encryption`.
Fix: add the appropriate enable flag.

### Error: "HD rendition refuses on Android"
Cause: Widevine L3 device, HD label requires L1. Correct — this is policy-enforced by the license server.
Fix: downgrade label to `SD`, OR test on an L1 device, OR relax policy server-side.

### Error: segments play but scrubbing jumps
Cause: `--segment_duration` too large (e.g., 10s+). Shrink to 4s.

### Performance: packaging takes hours
Shaka does not re-encode, it should be I/O bound. Hours means you accidentally pointed ffmpeg at the pipeline. Confirm you are running `packager`, not `ffmpeg`.
