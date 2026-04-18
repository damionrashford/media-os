# DRM schemes, signaling, and tooling matrix

Everything in this file is reference material. The `SKILL.md` covers the
happy-path recipes; come here for the "why" and for signaling templates.

---

## 1. HLS encryption modes

| Mode              | Tag in playlist                                  | Granularity            | ffmpeg support         | Typical use                     |
| ----------------- | ------------------------------------------------ | ---------------------- | ---------------------- | ------------------------------- |
| `AES-128`         | `#EXT-X-KEY:METHOD=AES-128,URI=...,IV=0x...`     | full segment, CBC      | **Full** (`-hls_enc`)  | Generic HLS AES-128             |
| `SAMPLE-AES`      | `#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT=...`     | NAL/audio sample, CBC  | Limited (no FairPlay signaling) | FairPlay (Apple)       |
| `SAMPLE-AES-CTR`  | `#EXT-X-KEY:METHOD=SAMPLE-AES-CTR,...`           | sample, CTR            | None (use Shaka)       | HLS+CMAF "CBCS-alt"             |

### Key info file — exact spec

`-hls_key_info_file` reads a 2 or 3 line UTF-8 file:

```
<line 1: key URI the player fetches — goes into EXT-X-KEY URI=...>
<line 2: local path ffmpeg uses to read the 16-byte key>
<line 3: optional IV in 32 hex chars, no 0x, no whitespace>
```

- Line 3 omitted → ffmpeg derives IV from the media sequence number
  (little-endian 64-bit counter). Standard HLS players do the same.
- CRLF vs LF: both tolerated in practice, but stick to LF.
- No BOM. No leading/trailing whitespace on any line.
- Paths may be relative to the cwd used when launching ffmpeg, but
  **absolute is always safer** (especially when ffmpeg is run by a
  daemon or a different user).

### `EXT-X-KEY` tag structure (emitted automatically)

```
#EXT-X-KEY:METHOD=AES-128,URI="https://cdn.example.com/keys/enc.key",IV=0xABCDEF0123456789ABCDEF0123456789
```

ffmpeg rewrites this tag each time the keyinfo file changes under
`periodic_rekey`.

### Key rotation strategies

| Strategy            | Implementation                                    | Pros                          | Cons                        |
| ------------------- | ------------------------------------------------- | ----------------------------- | --------------------------- |
| Static (no rotate)  | one keyinfo for the whole VOD                     | simplest                      | single compromise = full leak |
| Time-sliced         | cron rewrites keyinfo every N segments            | cheap, ffmpeg-native          | boundary alignment only     |
| Per-period (live)   | orchestrator rewrites on SCTE-35 / ad markers     | clean breaks                  | needs external signaling    |
| Commercial packager | Shaka Packager `--key_rotation_period_count`      | granular, labeled             | extra tool in pipeline      |

---

## 2. MPEG-DASH Common Encryption (CENC)

ISO/IEC 23001-7 defines four encryption schemes:

| 4CC     | Name             | Cipher mode | Sample encryption                           | DRM targets                |
| ------- | ---------------- | ----------- | ------------------------------------------- | -------------------------- |
| `cenc`  | CTR full-sample  | AES-CTR     | full NAL body                               | Widevine, PlayReady, ClearKey |
| `cens`  | CTR sub-sample   | AES-CTR     | 1-of-N NAL pattern                           | rarely used                |
| `cbc1`  | CBC full-sample  | AES-CBC     | full NAL body                               | legacy                     |
| `cbcs`  | CBC sub-sample   | AES-CBC     | 1:9 encrypt:skip NAL pattern                | FairPlay, cross-DRM CMAF   |

**ffmpeg mapping:**

- `-encryption_scheme cenc-aes-ctr` → `cenc`
- `-encryption_scheme cenc-aes-cbc` → `cbc1` (build-dependent)
- `cens` and `cbcs` patterns → not directly exposed; use Shaka Packager.

### MPD `ContentProtection` templates

ffmpeg emits the CENC `default_KID` UUID but **doesn't inject the
`<ContentProtection>` elements** most players need. Patch them in.

**ClearKey (works in all EME browsers; good for staging):**

```xml
<ContentProtection
    schemeIdUri="urn:mpeg:dash:mp4protection:2011"
    value="cenc"
    cenc:default_KID="11223344-5566-7788-0011-223344556677"/>
<ContentProtection
    schemeIdUri="urn:uuid:e2719d58-a985-b3c9-781a-b030af78d30e"
    value="1.0">
    <dashif:laurl xmlns:dashif="https://dashif.org/CPS"
        licenseType="ClearKey">https://example.com/clearkey</dashif:laurl>
</ContentProtection>
```

ClearKey license JSON returned by that URL:

```json
{
  "keys": [
    {
      "kty": "oct",
      "kid": "ESIzRFVmd4gAESIzRFVmdw",
      "k":   "q83vASNFZ4mrze8BI0VniQ"
    }
  ],
  "type": "temporary"
}
```

(`kid` and `k` are base64url-no-padding of the 16-byte KID and key.
Convert with `python -c 'import base64,sys; print(base64.urlsafe_b64encode(bytes.fromhex(sys.argv[1])).rstrip(b"=").decode())' <hex>`.)

**Widevine:**

```xml
<ContentProtection
    schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
    value="Widevine">
    <cenc:pssh>AAAA...</cenc:pssh>
</ContentProtection>
```

The `<cenc:pssh>` box must be generated by Widevine's signing API or a
packager that speaks Widevine (Shaka Packager `--enable_widevine_encryption`).
ffmpeg alone cannot produce it.

**PlayReady:**

```xml
<ContentProtection
    schemeIdUri="urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95"
    value="MSPR 2.0">
    <cenc:pssh>AAAA...</cenc:pssh>
    <mspr:pro>PRHeader...</mspr:pro>
</ContentProtection>
```

Same story — needs a PlayReady-aware packager.

**FairPlay (HLS + CBCS):**

Signaled on the HLS playlist, not the DASH MPD. `#EXT-X-KEY` with
`METHOD=SAMPLE-AES`, `KEYFORMAT="com.apple.streamingkeydelivery"`,
`KEYFORMATVERSIONS="1"`, and a `skd://` URI. Apple
`mediafilesegmenter` or Shaka Packager emit this; ffmpeg does not.

---

## 3. Browser / device DRM matrix

| DRM        | Chrome | Firefox | Edge       | Safari (macOS/iOS) | Android native | Smart TVs         |
| ---------- | ------ | ------- | ---------- | ------------------ | -------------- | ----------------- |
| ClearKey   | yes    | yes     | yes        | 14+                | yes            | some              |
| Widevine   | yes    | yes     | yes (Chromium) | no             | yes            | yes (Android TV)  |
| PlayReady  | no (direct) | no | yes (Edge)| no                 | no             | yes (Xbox, many TVs) |
| FairPlay   | no     | no      | no         | yes                | no             | Apple TV          |

**Practical multi-platform packaging:** encrypt once with `cbcs` (CMAF
CBCS), multiplex Widevine + PlayReady + FairPlay PSSH/signaling onto the
same ladder. Called "CMAF common-encryption" — requires Shaka Packager.

---

## 4. ClearKey test harness (staging only)

Minimal ClearKey license server in Python stdlib:

```python
# clearkey_server.py
import base64, http.server, json, sys
KID_HEX = "11223344556677880011223344556677"
KEY_HEX = "abcdef0123456789abcdef0123456789"
def b64url(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
PAYLOAD = json.dumps({
  "keys":[{"kty":"oct",
           "kid": b64url(bytes.fromhex(KID_HEX)),
           "k":   b64url(bytes.fromhex(KEY_HEX))}],
  "type":"temporary"}).encode()
class H(http.server.BaseHTTPRequestHandler):
  def do_POST(self):
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin","*")
    self.send_header("Content-Type","application/json")
    self.end_headers(); self.wfile.write(PAYLOAD)
http.server.HTTPServer(("",8080),H).serve_forever()
```

Point the MPD's `<dashif:laurl>` at `http://localhost:8080/clearkey`.
dash.js / Shaka Player load it out of the box.

---

## 5. When ffmpeg alone isn't enough — handoff options

| Need                                          | Tool to reach for         |
| --------------------------------------------- | ------------------------- |
| Widevine / PlayReady PSSH                     | Shaka Packager, Bento4    |
| FairPlay HLS signaling                        | Apple `mediafilesegmenter`, Shaka Packager |
| `cbcs` pattern encryption (CMAF common)       | Shaka Packager            |
| Per-track keys / key rotation labels          | Shaka Packager            |
| Low-level `mp4encrypt` / inspection           | Bento4 (`mp4encrypt`, `mp4dump`) |
| SPEKE / key-server integration                | AWS Elemental MediaConvert, Unified Streaming |

Typical hybrid pipeline:

```
source.mp4
  └─ ffmpeg (transcode + mux to fmp4, unencrypted)
       └─ Shaka Packager (encrypt with cbcs, inject Widevine+PlayReady+FairPlay PSSH)
            └─ CDN
```

ffmpeg's job in that pipeline is the encode + fmp4 mux; Shaka's is the
DRM signaling. Don't fight ffmpeg to do the DRM parts it was never
designed for.

---

## 6. Debug / inspection cheatsheet

```bash
# inspect CENC boxes in an fmp4 init segment
ffprobe -show_format -show_streams -show_entries stream_tags -of json init.m4s

# inspect EXT-X-KEY lines
grep -E '^#EXT-X-KEY' out.m3u8

# verify a segment decrypts with the claimed key
KEY_HEX=$(xxd -p enc.key)
openssl aes-128-cbc -d -K $KEY_HEX -iv <IV_HEX> -in seg_000.ts -out /tmp/plain.ts
ffprobe /tmp/plain.ts

# dump PSSH from a CENC fmp4 (needs Bento4)
mp4dump --verbosity 3 init.m4s | grep -A4 pssh
```

---

## 7. Operational checklist

- [ ] `.gitignore` includes `*.key`, `*.keyinfo`, `.env.drm`.
- [ ] Key files are `chmod 600`, owned by the packager user.
- [ ] Keys are fetched from KMS/Vault at run time, not baked into images.
- [ ] CI asserts round-trip decryption on a canary segment.
- [ ] CDN serves the key URI with correct `Access-Control-Allow-Origin`
      and auth (signed cookie, token, or mTLS to license server).
- [ ] Key rotation cadence documented; last-rotated timestamp logged.
- [ ] `EXT-X-KEY` URIs use HTTPS only.
- [ ] For DASH: `<ContentProtection>` is actually injected post-package.
- [ ] Manifest cache-control headers don't outlive the key.
