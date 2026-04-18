---
name: ffmpeg-drm
description: >
  DRM and media encryption with ffmpeg: HLS AES-128 (-hls_key_info_file, -hls_enc, key rotation), HLS SAMPLE-AES, MPEG-DASH Common Encryption (CENC) with cenc_mp4 / cbcs schemes, ClearKey, fmp4 encrypted segments, cryptor protocol for playback. Use when the user asks to encrypt an HLS stream, set up AES-128 HLS, do sample-AES, package CENC DASH, rotate HLS keys, generate a key info file, protect VOD content, or configure ClearKey signaling.
argument-hint: "[scheme] [input]"
---

# ffmpeg-drm

**Context:** $ARGUMENTS

## Quick start

- **Encrypt HLS with AES-128:** → Steps 1 → 2 → 3 → 4
- **Package DASH CENC (ClearKey / Widevine / PlayReady-ready):** → Steps 1 → 3 → 4
- **Rotate keys mid-stream:** → Step 3 with `-hls_flags periodic_rekey`
- **Play back a `crypto:` file:** → Step 4
- **Decrypt a segment for QA:** `scripts/drm.py decrypt-segment ...`

## When to use

- You need to protect a VOD or live HLS stream with AES-128 full-segment encryption.
- You need to package MPEG-DASH with Common Encryption (CENC, cbcs, cenc-aes-ctr) for ClearKey, Widevine, PlayReady, or FairPlay-ready workflows.
- You need to generate HLS key info files, rotate keys, or signal ClearKey in an MPD.
- You need a reproducible, scripted encryption pipeline without a commercial packager.
- **Don't use for:** Widevine/PlayReady license server integration (ffmpeg can't emit PSSH boxes reliably — use Shaka Packager or Bento4), or FairPlay SAMPLE-AES-CTR signaling (use Apple `mediafilesegmenter`).

## Step 1 — Generate keys and IVs

A 16-byte (128-bit) AES key and a 16-byte IV. Both are binary; IVs are typically expressed as 32 hex chars.

```bash
# 16-byte key (binary file)
openssl rand 16 > enc.key
# or, stdlib-friendly:
dd if=/dev/urandom of=enc.key bs=16 count=1 2>/dev/null

# 32-hex-char IV (no "0x", no whitespace)
openssl rand -hex 16

# Key as hex (for ffmpeg -hls_enc_key / -encryption_key)
xxd -p enc.key     # 32 hex chars

# KID for CENC (unique per content — distinct from the key)
openssl rand -hex 16
```

Or use the helper: `scripts/drm.py gen-key --output enc.key` and `scripts/drm.py gen-iv`.

**Never commit keys to git.** Add `*.key` and `*.keyinfo` to `.gitignore`. In production, fetch keys from a KMS or licensed DRM key server.

## Step 2 — Build the HLS key info file

ffmpeg's HLS AES-128 mode reads a 3-line text file. **Format is exact — deviation breaks encryption:**

```
https://cdn.example.com/keys/enc.key
/absolute/path/to/enc.key
abcdef0123456789abcdef0123456789
```

1. **Line 1:** Key URI the *player* fetches (goes into `EXT-X-KEY URI="..."` in the playlist).
2. **Line 2:** Local path ffmpeg reads to encrypt — can be relative to the cwd used at launch, but absolute is safer.
3. **Line 3:** IV in hex, **no `0x` prefix, no whitespace**. Optional — if omitted, ffmpeg derives the IV from the segment media sequence number.

The server hosting line 1 must actually serve it with the right CORS headers and whatever auth your license scheme requires.

## Step 3 — Package and encrypt

### HLS AES-128 VOD (with key info file — recommended)

```bash
ffmpeg -i in.mp4 \
  -c:v libx264 -c:a aac \
  -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_key_info_file enc.keyinfo \
  -hls_segment_filename 'seg_%03d.ts' \
  out.m3u8
```

### HLS AES-128 inline (no key info file)

```bash
ffmpeg -i in.mp4 \
  -c:v libx264 -c:a aac \
  -f hls -hls_time 6 \
  -hls_enc 1 \
  -hls_enc_key_url 'https://cdn.example.com/keys/enc.key' \
  -hls_enc_key "$(xxd -p enc.key)" \
  -hls_enc_iv   "$(openssl rand -hex 16)" \
  out.m3u8
```

**Warning:** `-hls_enc 1` without `-hls_enc_key` / `-hls_enc_key_url` makes ffmpeg auto-generate a key and write it next to the playlist. Insecure default — always pass your own.

### HLS key rotation (periodic rekey)

```bash
ffmpeg -i in.mp4 -c:v libx264 -c:a aac \
  -f hls -hls_time 6 \
  -hls_flags periodic_rekey \
  -hls_key_info_file enc.keyinfo \
  out.m3u8
```

When you update the `enc.keyinfo` file in place during a live ingest, ffmpeg will pick up the new key on the next segment boundary and emit a new `EXT-X-KEY` tag. ffmpeg's rotation is coarser than Shaka Packager's (no per-period labels); rewrite the keyinfo file on your cadence.

### DASH Common Encryption (CENC) — cenc-aes-ctr

```bash
ffmpeg -i in.mp4 \
  -c:v libx264 -c:a aac \
  -encryption_scheme cenc-aes-ctr \
  -encryption_key  abcdef0123456789abcdef0123456789 \
  -encryption_kid  11223344556677880011223344556677 \
  -f dash \
  -use_template 1 -use_timeline 1 \
  -init_seg_name 'init-$RepresentationID$.m4s' \
  -media_seg_name 'chunk-$RepresentationID$-$Number%05d$.m4s' \
  manifest.mpd
```

- `-encryption_key` and `-encryption_kid` are both 32 hex chars (16 bytes each).
- KID must be unique per content; the *key* is the AES secret the license server hands out.
- Emits CENC-compliant fmp4 segments and an MPD. For ClearKey playback, append a `<ContentProtection>` ClearKey element (see `references/schemes.md`).

### DASH CBCS (FairPlay / mixed-DRM compatible scheme)

```bash
ffmpeg -i in.mp4 -c:v libx264 -c:a aac \
  -encryption_scheme cenc-aes-cbc \
  -encryption_key  abcdef0123456789abcdef0123456789 \
  -encryption_kid  11223344556677880011223344556677 \
  -f dash manifest.mpd
```

`cenc-aes-cbc` support depends on your ffmpeg build — verify with `ffmpeg -h muxer=dash` and `ffmpeg -h muxer=mp4`. For a fully CBCS-compliant FairPlay package you'll still typically need Shaka Packager.

## Step 4 — Verify playback / decryption

### Play an HLS AES-128 stream locally

```bash
ffplay -allowed_extensions ALL out.m3u8
```

`ffplay` fetches the key from line-1 URI of the `EXT-X-KEY` tag. If the URI is `file://` or relative, ffplay needs `-allowed_extensions ALL` and a local HTTP server.

### Decrypt one TS segment with openssl (QA)

```bash
# IV must match what ffmpeg used — line 3 of the keyinfo file
KEY_HEX=$(xxd -p enc.key)
IV_HEX=abcdef0123456789abcdef0123456789
openssl aes-128-cbc -d -K "$KEY_HEX" -iv "$IV_HEX" \
  -in seg_000.ts -out seg_000.plain.ts
ffprobe seg_000.plain.ts   # should show normal stream info
```

### `crypto:` protocol playback (raw AES-128 file)

```bash
ffplay -i "crypto:encrypted.bin?key=$(xxd -p enc.key)&iv=abcdef0123456789abcdef0123456789"
```

Use for internally encrypted assets when a full HLS/DASH wrapper is overkill.

## Available scripts

- **`scripts/drm.py`** — subcommands:
  - `gen-key --output enc.key` — 16 random bytes via `secrets.token_bytes`.
  - `gen-iv` — prints a 32-hex-char IV.
  - `hls-aes128 --input I --outdir D --key-url URL --key enc.key [--segments 6] [--rotate]` — builds `enc.keyinfo`, runs the ffmpeg HLS pipeline.
  - `dash-cenc --input I --outdir D --key HEX --kid HEX [--scheme cenc-aes-ctr|cenc-aes-cbc]`.
  - `decrypt-segment --input seg.ts --key enc.key --iv HEX --output plain.ts` — shells out to `openssl aes-128-cbc`.
  - Global flags: `--dry-run`, `--verbose` (keys only printed with `--verbose`).

## Reference docs

- Read [`references/schemes.md`](references/schemes.md) for HLS vs CENC scheme comparison, MPD ContentProtection templates, browser DRM matrix, ClearKey demo, key rotation strategies, and Shaka/Bento4 handoff when ffmpeg is insufficient.
- FFmpeg HLS options: https://ffmpeg.org/ffmpeg-formats.html#hls-2
- FFmpeg DASH CENC options: https://ffmpeg.org/ffmpeg-formats.html#dash-2
- FFmpeg crypto protocol: https://ffmpeg.org/ffmpeg-protocols.html#crypto
- Wiki: https://trac.ffmpeg.org/wiki/Encode/CommonEncryption

## Gotchas

- **Key info file format is exact.** Three lines: URI / local-path / IV-hex. A blank line, CRLF mix, or a leading `0x` on the IV silently breaks the encrypt or the player's decrypt.
- **IV is hex, no `0x`, no colons, no whitespace** — exactly 32 chars.
- **The key file must be exactly 16 bytes.** `echo "somepassword" > enc.key` is wrong — that writes ASCII plus a newline. Use `openssl rand 16` or the `gen-key` subcommand.
- **Line 1 of keyinfo is what the player fetches.** The origin serving that URL needs CORS (`Access-Control-Allow-Origin`) and whatever auth the license flow requires. A 403 there = player can't decrypt.
- **`-hls_enc 1` with no explicit key** → ffmpeg auto-generates and writes a key next to the playlist. Never ship like that.
- **ffmpeg key rotation is coarse.** `-hls_flags periodic_rekey` re-reads the keyinfo file on segment boundaries — *you* orchestrate the rotation by rewriting that file. Commercial packagers have per-period labels and time-based schedules; ffmpeg doesn't.
- **SAMPLE-AES and SAMPLE-AES-CTR (FairPlay) are not fully supported.** ffmpeg can emit AES-128 full-segment HLS and CENC fmp4, but FairPlay's `EXT-X-KEY METHOD=SAMPLE-AES` with `KEYFORMAT="com.apple.streamingkeydelivery"` signaling needs Apple `mediafilesegmenter` or Shaka Packager.
- **DASH CENC + Widevine / PlayReady:** ffmpeg does not generate the PSSH boxes those systems require. Encrypt-then-repackage with Shaka Packager (`--enable_raw_key_encryption` + Widevine/PlayReady PSSH) or Bento4 (`mp4encrypt` with `--pssh`).
- **ClearKey works cross-browser** (Chrome, Firefox, Edge, Safari 14+) and is fine for staging/internal. Not for commercial content — keys sit in the MPD.
- **`-encryption_key` and `-encryption_kid` are 32 hex chars each (16 bytes).** 64 hex would be 256-bit, which CENC does not use. Wrong length = silent no-op or "encryption key must be 16 bytes" error.
- **KID must be unique per asset.** Reusing a KID across titles conflates license lookups at the key server.
- **EXT-X-KEY tag is auto-generated** from line 1 of the keyinfo file — don't try to hand-edit the `.m3u8` afterward; the next ffmpeg run will overwrite it.
- **Never commit `.key`, `.keyinfo`, or raw hex-key env files.** Add them to `.gitignore` and `.dockerignore`.
- **Rotate keys for long VOD.** A single key for a 10-hour-per-day linear feed is an audit finding.
- **Store keys in a KMS** (AWS KMS, GCP KMS, HashiCorp Vault) or a licensed DRM server. Local `.key` files are fine for dev; never prod.
- **Test decryption on every build.** A silent `-hls_enc` fallback (encrypting with a wrong key path) will mux cleanly and fail only at the player. Add `openssl aes-128-cbc -d` round-trips to CI.

## Examples

### Example 1: Encrypt a VOD with AES-128 and a hosted key URL

Input: `talk.mp4`, key will be served from `https://cdn.example.com/keys/talk.key`.

```bash
# 1. generate
openssl rand 16 > talk.key
IV=$(openssl rand -hex 16)

# 2. keyinfo
cat > talk.keyinfo <<EOF
https://cdn.example.com/keys/talk.key
$(pwd)/talk.key
$IV
EOF

# 3. package
mkdir -p out
ffmpeg -i talk.mp4 -c:v libx264 -c:a aac \
  -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_key_info_file talk.keyinfo \
  -hls_segment_filename 'out/seg_%03d.ts' \
  out/talk.m3u8

# 4. verify one segment
openssl aes-128-cbc -d -K $(xxd -p talk.key) -iv $IV \
  -in out/seg_000.ts -out out/seg_000.plain.ts
ffprobe out/seg_000.plain.ts
```

Upload `out/` to your CDN; upload `talk.key` to `https://cdn.example.com/keys/talk.key` behind whatever auth your license flow uses.

### Example 2: DASH CENC with ClearKey for staging

```bash
KEY=$(openssl rand -hex 16)
KID=$(openssl rand -hex 16)

ffmpeg -i in.mp4 -c:v libx264 -c:a aac \
  -encryption_scheme cenc-aes-ctr \
  -encryption_key "$KEY" \
  -encryption_kid "$KID" \
  -f dash -use_template 1 -use_timeline 1 \
  staging/manifest.mpd

# Patch ContentProtection into the MPD — see references/schemes.md
```

Base64 the hex KID and key per the ClearKey EME spec (`references/schemes.md` has the exact JSON).

### Example 3: Decrypt a single segment for QA

```bash
scripts/drm.py decrypt-segment \
  --input out/seg_000.ts \
  --key talk.key \
  --iv abcdef0123456789abcdef0123456789 \
  --output /tmp/seg_000.plain.ts
ffprobe /tmp/seg_000.plain.ts
```

## Troubleshooting

### Error: `Invalid key size` / `encryption key must be 16 bytes`

Cause: key file is not 16 bytes (likely contains a trailing newline or ASCII text).
Solution: regenerate with `openssl rand 16 > enc.key`. Verify with `wc -c enc.key` → `16`.

### Error: `Unable to open key file` during ffmpeg

Cause: line 2 of the keyinfo file points to a path ffmpeg can't read (relative to wrong cwd, or permissions).
Solution: use absolute paths on line 2. `chmod 600 enc.key`.

### Player loads the manifest but segments fail to decrypt

Cause: line 1 URI returns 403/CORS-blocked, or the IV in line 3 doesn't match what the player derives.
Solution: `curl -I <line1-url>` from the player origin — must be 200 with `Access-Control-Allow-Origin`. If omitting the IV line, ensure your player derives IV from media sequence number (standard HLS behavior); otherwise pin an explicit IV.

### DASH MPD plays unencrypted or "no decryption key" error

Cause: MPD lacks a `<ContentProtection>` element, or the `default_KID` doesn't match `-encryption_kid`.
Solution: inject `ContentProtection` per `references/schemes.md`. `default_KID` must equal your `--kid` formatted with dashes (8-4-4-4-12).

### `-hls_flags periodic_rekey` didn't rotate

Cause: keyinfo file wasn't rewritten on disk, or ffmpeg checked the mtime before your write.
Solution: write to a temp file then `mv` atomically. ffmpeg re-reads the keyinfo file at each segment boundary.

### FairPlay player refuses the stream

Cause: ffmpeg emits AES-128 full-segment, not SAMPLE-AES with `KEYFORMAT="com.apple.streamingkeydelivery"`.
Solution: use Apple `mediafilesegmenter` or Shaka Packager. ffmpeg alone cannot emit a FairPlay-compliant playlist.

### Widevine / PlayReady player says "no PSSH"

Cause: ffmpeg doesn't write PSSH boxes for Widevine/PlayReady system IDs.
Solution: encrypt with ffmpeg to get raw CENC, then pass through Shaka Packager or `mp4encrypt` with `--pssh` to inject system-specific PSSH.
