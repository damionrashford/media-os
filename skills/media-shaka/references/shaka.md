# Shaka Packager Reference

Deep reference for Shaka Packager (`packager`). Load when writing non-trivial recipes: multi-period, trick-play, encrypted FAST, live event streams, or when debugging a manifest or PSSH issue.

## 1. Protection scheme matrix

| Scheme | Full name | Cipher | Pattern | DASH | HLS fMP4 | FairPlay | Widevine | PlayReady |
|--------|-----------|--------|---------|------|----------|----------|----------|-----------|
| `cenc` | ISO/IEC 23001-7 AES-CTR | AES-CTR | full sample | Yes | Yes (legacy) | No | Yes | Yes |
| `cens` | AES-CTR pattern | AES-CTR | 1:9 crypt:skip | Yes | Some | No | Yes | Partial |
| `cbc1` | AES-CBC | AES-CBC | full sample | Yes | No | No | Yes | Partial |
| `cbcs` | AES-CBC pattern | AES-CBC | 1:9 crypt:skip | **Yes** | **Yes** | **Yes** | Yes (14.0+) | Yes |

**Modern default is `cbcs`.** It works for every mainstream DRM system as of Widevine v14+, and one set of encrypted CMAF segments can be referenced by both a DASH `.mpd` and an HLS `.m3u8`. This is the whole point of "Common Encryption" (MPEG-CENC) + CMAF.

`cenc` is still correct when:
- Target is exclusively DASH-on-Smart-TV legacy fleets that pre-date `cbcs` support.
- A certification program explicitly requires AES-CTR.

## 2. DRM system UUIDs (for PSSH / manifest signalling)

| DRM | UUID | Where used |
|-----|------|------------|
| Widevine  | `edef8ba9-79d6-4ace-a3c8-27dcd51d21ed` | Chrome, Android, Edge, Firefox, Smart TVs |
| PlayReady | `9a04f079-9840-4286-ab92-e65be0885f95` | Edge, Xbox, Windows, some Smart TVs |
| FairPlay  | `94ce86fb-07ff-4f43-adb8-93d2fa968ca2` | Safari, iOS, tvOS, macOS |
| ClearKey  | `e2719d58-a985-b3c9-781a-b030af78d30e` | Dev / testing only |
| Marlin    | `5e629af5-38da-4063-8977-97ffbd9902d4` | IPTV, Japan |

PSSH boxes include the UUID + DRM-system-specific data. Shaka auto-inserts them when the corresponding `--enable_*_encryption` flag is set. For raw key + forced PSSH: `--pssh HEX`.

## 3. Stream descriptor syntax

Full form:

```
in=INPUT,stream=STREAM[,init_segment=S][,segment_template=T][,output=O]
       [,drm_label=L][,trick_play_factor=N][,skip_encryption=0|1]
       [,language=LANG][,hls_name=NAME][,hls_group_id=GROUP]
       [,playlist_name=FILE]
```

- `in=` — input file (MP4 / WebM / MKV / fragmented MP4).
- `stream=` — `video`, `audio`, `text`, `subtitle`, or stream id.
- `output=` — monolithic fMP4 output (VOD).
- `init_segment=` / `segment_template=` — segmented live output.
- `drm_label=` — maps the stream to a `--keys label=…` or Widevine content-type level.
- `trick_play_factor=N` — declares this rendition as a trick-play track at 1/N rate.
- `skip_encryption=1` — leave this stream in the clear (typical for trick-play).
- `hls_group_id=` — HLS audio-group assignment.

Multiple descriptors in one command: just repeat them space-separated.

## 4. Manifest output options

| Flag | Output |
|------|--------|
| `--mpd_output FILE`                 | DASH `.mpd` |
| `--hls_master_playlist_output FILE` | HLS master `.m3u8` (individual variant playlists named from `hls_name`) |
| `--generate_static_live_mpd`        | Output SegmentTemplate-based MPD usable by live-clients even for VOD |
| `--dash_label LABEL`                | Period/Label for multi-period MPD |
| `--utc_timings schemeIdUri=X:value=Y` | Time source, required for low-latency / live-edge |
| `--min_buffer_time N`               | DASH `@minBufferTime` |
| `--suggested_presentation_delay N`  | DASH `@suggestedPresentationDelay` |
| `--time_shift_buffer_depth N`       | DVR window (live) |
| `--preserved_segments_outside_live_window N` | Retention after TSBD (live) |
| `--default_language LANG`           | Default language tag |

## 5. Live vs VOD

**VOD:** one `output=FILE` per stream. Shaka writes a monolithic fMP4 with sidx, plus manifests. Cheap to host on S3/R2/any static CDN.

**Live:** use `init_segment=` + `segment_template=` with `$Number$` or `$Time$` placeholders:

```
in=udp://0.0.0.0:10000,stream=video,\
  init_segment=live/video_init.mp4,\
  segment_template=live/video_$Number$.m4s
```

Live-specific flags:
- `--dash_label live_1`
- `--utc_timings schemeIdUri=urn:mpeg:dash:utc:http-head:2014:value=https://time.akamai.com/?iso`
- `--time_shift_buffer_depth 300`
- `--preserved_segments_outside_live_window 10`
- `--mpd_output live/manifest.mpd`

SCTE-35 markers in an MPEG-TS input are preserved as DASH `EventStream` with `schemeIdUri="urn:scte:scte35:2014:xml+bin"` or as EMSG events in fMP4.

## 6. License-server vendors

Not exhaustive, but all known-good drop-in integrations:

- Google Widevine cloud (direct Google partner program).
- **EZDRM** — multi-DRM, simplest onboarding.
- **PallyCon** — multi-DRM, Asia presence.
- **Axinom** — multi-DRM, European.
- **BuyDRM / KeyOS** — multi-DRM, broadcast heritage.
- **DRMtoday** (castLabs) — multi-DRM.
- **Irdeto** — broadcast-focused, multi-DRM.
- **Verimatrix VCAS** — operator / broadcast.
- **Nagra NexGuard / PRM** — studio / operator.
- **Microsoft Azure Media Services** (deprecated — do not build new pipelines on it).

For ClearKey test playback: https://shaka-player-demo.appspot.com/ accepts `{KID-base64url: KEY-base64url}`.

## 7. PSSH structure

A `pssh` box (Protection System Specific Header) lives inside the `moov` → `pssh` path (or in init segment). Its binary payload:

```
[4  bytes]  size
[4  bytes]  'pssh'
[1  byte ]  version (0 or 1)
[3  bytes]  flags (0)
[16 bytes]  SystemID UUID
[4  bytes]  KIDCount      (version 1 only)
[16*N]      KIDs          (version 1 only)
[4  bytes]  DataSize
[N  bytes]  Data (DRM-system-specific, e.g., Widevine WidevinePsshData protobuf)
```

Widevine PSSH data is a protobuf: `provider`, `content_id`, `policy`, `key_id[]`. Shaka generates it when `--enable_widevine_encryption` is set, using `content_id` you provide.

PlayReady PSSH contains an XML-ish `PlayReadyHeader` (WRMHEADER, KID, LA_URL, LUI_URL, DS_ID, CHECKSUM).

FairPlay does NOT use PSSH inside fMP4; key identification is via HLS `EXT-X-KEY` tag with `URI="skd://…"`.

## 8. Recipe book

### 8.1 FAST channel with encrypted content + encrypted ads

Use separate periods per ad break. Each period has its own PSSH and can have its own keys (or reuse).

```
packager \
  --single_period_output=false \
  in=content.mp4,stream=video,drm_label=CONTENT,output=content.mp4 \
  in=ad1.mp4,stream=video,drm_label=AD,output=ad1.mp4 \
  --enable_raw_key_encryption \
  --keys label=CONTENT:key_id=K1:key=V1,label=AD:key_id=K2:key=V2 \
  --protection_scheme cbcs \
  --mpd_output fast.mpd
```

### 8.2 Live DRM event stream (SCTE-35 preserved)

```
packager \
  'in=udp://0.0.0.0:10000?fifo_size=100000,stream=video,\
     init_segment=out/v_init.mp4,segment_template=out/v_$Number$.m4s,drm_label=HD' \
  'in=udp://0.0.0.0:10000?fifo_size=100000,stream=audio,\
     init_segment=out/a_init.mp4,segment_template=out/a_$Number$.m4s' \
  --enable_widevine_encryption \
  --key_server_url $WV \
  --signer $SIGNER --aes_signing_key $K --aes_signing_iv $IV \
  --protection_scheme cbcs \
  --time_shift_buffer_depth 300 \
  --utc_timings 'schemeIdUri=urn:mpeg:dash:utc:http-head:2014:value=https://time.akamai.com/?iso' \
  --mpd_output out/live.mpd
```

SCTE-35 markers already embedded upstream in the TS → passed through to MPD `EventStream` + in-band EMSG.

### 8.3 Trick-play (scrub preview) track

Encode a reduced rendition first with ffmpeg (e.g. 1 fps keyframes only), then declare it as trick-play:

```
in=trick_1fps.mp4,stream=video,output=trick.mp4,trick_play_factor=4,skip_encryption=1
```

Most players expose this as a second video representation used only during seek.

### 8.4 Audio-only FairPlay

Same as any FairPlay flow, but only audio descriptors. Useful for Apple Music-style delivery.

### 8.5 Multi-key / key rotation

Widevine rotates keys server-side via `--crypto_period_duration N` (seconds):

```
--crypto_period_duration 600
```

Server issues a new KID every 10 minutes; player re-requests licenses automatically.

## 9. Validators

- **DASH-IF Conformance:** https://conformance.dashif.org (upload `.mpd`, runs MPD + fMP4 validation).
- **Apple `mediastreamvalidator`:** ships with Xcode command-line tools.
  ```
  mediastreamvalidator master.m3u8
  hlsreport.pl -s master.m3u8 > report.html
  ```
- **Bento4 `mp4dump` / `mp4info`:** inspect PSSH and sample encryption sub-boxes (`sinf`, `schm`, `tenc`, `senc`, `saiz`, `saio`).
- **GPAC `MP4Box -info` / `MP4Box -diso`:** print ISOBMFF box tree as XML.
- **Shaka Player demo:** end-to-end playback against the real CDMs (Widevine on Chrome, FairPlay on Safari, PlayReady on Edge).

## 10. Gotchas & notes

- Packager does NOT mux clear + encrypted in the same representation. Pick one per rendition.
- `--clear_lead` applies per representation. Keep consistent across renditions or ABR switch will stutter.
- If you see `"Invalid key length"` — your KID/key is not 32 hex chars.
- `--enable_widevine_encryption` + `--enable_raw_key_encryption` are mutually exclusive for the same stream; multi-DRM = `--enable_widevine_encryption --enable_playready_encryption` which share a raw content key under the hood.
- When building ad-insertion pipelines, align ad break boundaries to segment edges (4-second grid) or you will see glitches.
- Shaka Packager's CLI is stable across minor versions but flags do get renamed. Pin the binary version in CI.
- The official Docker image `google/shaka-packager` is slim and reproducible — prefer it in CI.
