# GPAC / MP4Box reference

Deep reference for MP4Box, gpac (new CLI), ISO-BMFF box anatomy, DASH profiles, CMAF distinctions, and CENC XML schema. Skim Quick-start tables; fall back to the recipe book at the end.

---

## 1. MP4Box option catalog

### 1.1 Inspection

| Option | Meaning |
|--------|---------|
| `-info` | Human-readable summary: tracks, codecs, durations, bitrate, DRM flag. |
| `-info TID` | Per-track detail (`MP4Box -info 2 in.mp4`). |
| `-diso` | Dump full box tree to `<input>_info.xml`. Every box, every field. |
| `-drtp` | Dump RTP hint tracks. |
| `-dcr` | Dump CENC data (keys, IVs). |
| `-stdb` | Print sample-size / sample-to-chunk tables. |
| `-bt` | Dump in BT (BIFS Textual) syntax for scene description. |
| `-xmt` | Dump in XMT (XML MPEG-4) syntax. |
| `-mpd` | Print MPD stats from a DASH manifest. |

### 1.2 Edit / surgery

| Option | Meaning |
|--------|---------|
| `-add file[#trackID=N]` | Append track from file. Optional track selector after `#`. |
| `-cat file` | Concatenate (append) another ISO-BMFF file. |
| `-catx file` | Concatenate preserving edits (slower but faithful). |
| `-rem TID` | Remove track. |
| `-new` | Force creating a new file rather than editing in place. |
| `-out path` | Explicit output path (recommended; prevents in-place mutation). |
| `-lang TID=LANG` | Set ISO-639-2 language on track (`jpn`, `eng`, `fra`, ...). |
| `-enable TID` / `-disable TID` | Toggle track_enabled flag in `tkhd`. |
| `-name TID=Label` | Set track name (for muxers that honor it). |
| `-delay TID=MS` | Offset track start by ±ms. |
| `-elst '0,N,1'` | Rewrite edit list: `0`=offset, `N`=duration, `1`=media rate. |
| `-time-shift N` | Adjust base-media-decode-time in fMP4. |
| `-tight` | Rewrite `moov` for streaming (≈ ffmpeg `+faststart`). |
| `-isma` | Make ISMA-compatible. |
| `-split T` | Split to T-second pieces. |
| `-splitx T1:T2` | Split by timecode range `HH:MM:SS:HH:MM:SS`. |
| `-splitg N` | Split into N equal groups. |

### 1.3 Fragmentation / DASH / CMAF

| Option | Meaning |
|--------|---------|
| `-frag MS` | Fragment MP4 (fMP4) with MS-ms fragments. |
| `-dash MS` | Enable DASH mode, MS-ms segments. |
| `-rap` | Force each segment to start at random-access point (IDR). |
| `-frag-rap` | Fragments align to RAPs (usually with `-dash`). |
| `-segment-name PAT` | Template, e.g. `seg_$RepresentationID$_$Number$`. Placeholders: `$RepresentationID$`, `$Number$`, `$Bandwidth$`, `$Time$`. |
| `-dash-profile P` | `live` / `onDemand` / `main` / `full` / `dashavc264:live` / `dashavc264:onDemand`. |
| `-dash-ctx FILE` | Persist state for continuous live packaging across runs. |
| `-mpd-title TXT` | MPD Title metadata. |
| `-mpd-info-url URL` | MPD InfoURL. |
| `-base-url URL` | Add BaseURL to MPD. |
| `-url-template` | Use `SegmentTemplate` with `$Number$`. |
| `-segment-timeline` | Use `SegmentTimeline` (variable-size segments, live). |
| `-single-segment` | One file per representation (onDemand byte-range style). |
| `-single-file` | One file for whole MPD (onDemand). |
| `-add-sidx MS` | Inject `sidx` Segment Index box with MS-ms reference points. |
| `-no-frags-default` | Don't use default sample values in `moof`. |
| `-no-cache` | Flush fragments as they're written (live). |

### 1.4 Encryption (CENC)

| Option | Meaning |
|--------|---------|
| `-crypt XML` | Apply CENC via DRM description XML. |
| `-decrypt XML` | Reverse CENC. |
| `-set-meta`, `-add-meta` | Edit `meta` box (EME signaling, HDS). |

`-crypt` writes `senc` (sample encryption) + `saio`/`saiz` (aux info offsets/sizes) per track. For ClearKey DASH, also needs a `pssh` box — add via XML.

---

## 2. ISO-BMFF box reference

Boxes are 4-char codes. Key structural ones (hierarchical):

```
ftyp                        File Type (brand = isom, dash, cmfc, iso6, ...)
moov                        Movie header (describes everything)
├── mvhd                    Movie header (timescale, duration)
├── trak                    One per track
│   ├── tkhd                Track header (track_ID, flags: enabled/in_movie/in_preview)
│   ├── edts > elst         Edit list (offsets, gaps, rate)
│   └── mdia
│       ├── mdhd            Media header (language!)
│       ├── hdlr            Handler (vide / soun / subt / meta)
│       └── minf
│           └── stbl        Sample Table (the important one)
│               ├── stsd    Sample description (codec details, sinf for CENC)
│               ├── stts    Decode time → sample
│               ├── ctts    Composition offsets (B-frames)
│               ├── stss    Sync samples (IDR positions)
│               ├── stsc    Sample-to-chunk
│               ├── stsz    Sample sizes
│               └── stco/co64  Chunk offsets
└── mvex                    Movie Extends — REQUIRED for fragmented MP4
    └── trex                Track Extends — default sample values

moof                        Movie Fragment (one per fragment in fMP4)
├── mfhd                    Fragment header (sequence_number)
└── traf                    Track fragment
    ├── tfhd                Track fragment header
    ├── tfdt                base-media-decode-time (monotonic)
    ├── trun                Track run (per-sample sizes, flags)
    ├── senc                Sample encryption (IVs + subsample info)
    ├── saiz                Sample auxiliary info sizes
    └── saio                Sample auxiliary info offsets

mdat                        Media data (actual codec bytes)

sidx                        Segment Index (byte-range DASH onDemand)
pssh                        Protection System Specific Header (DRM signaling)
emsg                        Event Message (SCTE-35, ID3 timed metadata, CMAF)
styp                        Segment Type (per-segment ftyp for CMAF)
```

### Notes

- **`moov` placement**: at the start = fast-start / streaming. At the end = requires full download to play. `MP4Box -tight` moves it.
- **`mvex` is mandatory for fMP4** — signals "expect `moof` boxes".
- **`senc` vs `saio`/`saiz`**: CENC stores per-sample IVs in `senc`. `saiz`/`saio` point from sample table to the `senc` data. MP4Box writes these consistently; don't hand-edit.
- **`pssh`**: contains DRM system UUID + system data. For ClearKey: UUID `1077efec-c0b2-4d02-ace3-3c1e52e2fb4b`. For Widevine: `edef8ba9-79d6-4ace-a3c8-27dcd51d21ed`. For PlayReady: `9a04f079-9840-4286-ab92-e65be0885f95`. For FairPlay: `94ce86fb-07ff-4f43-adb8-93d2fa968ca2`.
- **`emsg`**: CMAF event box — used for SCTE-35 ad markers, ID3 metadata, DASH event streams.
- **`styp`**: per-segment brand (CMAF mandates `cmfc`, `cmf2`, or `cmfl` brands).

---

## 3. DASH profile matrix

| Profile | URN | Segmented | sidx | Init | Fragment | Use case |
|---------|-----|-----------|------|------|----------|----------|
| **live** | `urn:mpeg:dash:profile:isoff-live:2011` | yes (.m4s files) | optional | separate `init.mp4` | yes | Live, CMAF, HLS-interop. |
| **onDemand** | `urn:mpeg:dash:profile:isoff-on-demand:2011` | single file | **required** | embedded | yes | VOD byte-range streaming. |
| **main** | `urn:mpeg:dash:profile:isoff-main:2011` | yes | optional | separate | yes | Older, less restrictive. |
| **full** | `urn:mpeg:dash:profile:full:2011` | anything | optional | any | optional | Kitchen sink; poor player support. |
| **dashavc264:live** | H.264-only live | yes | optional | separate | yes | H.264 lowest-common-denominator live. |
| **dashavc264:onDemand** | H.264-only VOD | single file | required | embedded | yes | Same, VOD. |

### MP4Box examples by profile

```bash
# Live (CMAF-ready, HLS-interop)
MP4Box -dash 4000 -frag 4000 -rap \
  -dash-profile live \
  -segment-name 'seg_$RepresentationID$_$Number$' \
  -out out/manifest.mpd \
  video.mp4 audio.mp4

# On-demand (single indexed file per representation)
MP4Box -dash 4000 -frag 4000 -rap \
  -dash-profile onDemand \
  -single-file \
  -out out/manifest.mpd \
  video.mp4 audio.mp4

# Live with continuous context (across invocations)
MP4Box -dash 4000 -frag 4000 -rap \
  -dash-profile live \
  -dash-ctx state.ctx \
  -out out/manifest.mpd \
  video.mp4

# Segment timeline (variable fragments, low-latency live)
MP4Box -dash 2000 -frag 2000 -rap \
  -dash-profile live \
  -segment-timeline \
  -out out/manifest.mpd \
  video.mp4
```

---

## 4. CMAF vs ISO-BMFF segments

CMAF (Common Media Application Format, MPEG-A part 19) is a constrained profile of ISOBMFF designed so one set of segments can be played by both DASH and HLS.

| | ISO-BMFF segment (generic DASH) | CMAF segment |
|---|---|---|
| Brand (`ftyp`/`styp`) | `iso5`, `iso6`, `dash`, ... | `cmfc`, `cmf2`, or `cmfl` (required) |
| Structure | init + `moof`+`mdat` pairs | Same |
| Media sample constraints | Few | Strict: AVC/HEVC/AAC allowed profiles, no edit lists, single-track per file |
| Edit lists | Allowed | Forbidden |
| Separate tracks | Allowed (multiplexed) | One track per CMAF track file |
| HLS compatible | Maybe | Always (CMAF fMP4 HLS) |
| Common key per representation | Optional | Required for CMAF-CENC |
| Sample encryption | CTR (`cenc`) or CBC (`cbcs`) | Same, but **`cbcs` recommended** for FairPlay-interop |

**Practical rule**: if you need one package to feed both Apple HLS and MPEG-DASH, output CMAF (`-dash-profile live`, CMAF-compatible input, CBCS encryption, `cmfc` brand).

---

## 5. CENC XML schema (GPAC)

Minimal CTR-mode ClearKey:

```xml
<GPACDRM>
  <CrypTrack trackID="1"
             IsEncrypted="1"
             IV_size="8"
             first_IV="0x0123456789abcdef"
             saiSavedBox="senc">
    <key KID="0xABCDEF01234567890ABCDEF012345678"
         value="0x112233445566778899AABBCCDDEEFF00"/>
  </CrypTrack>
</GPACDRM>
```

### CrypTrack attributes

| Attribute | Values | Meaning |
|-----------|--------|---------|
| `trackID` | int | MP4 track ID (1-based). |
| `IsEncrypted` | `0`/`1` | Enable encryption on this track. |
| `IV_size` | `8` or `16` | AES-CTR counter width. 8 = CTR-64, 16 = CTR-full. |
| `first_IV` | hex | Seed IV (hex with `0x`). 8 or 16 bytes. |
| `saiSavedBox` | `senc` / `saiz` | Which aux-info box name to use. `senc` is standard. |
| `scheme_type` | `cenc` / `cbc1` / `cens` / `cbcs` | CENC scheme. Default `cenc` (AES-CTR). `cbcs` = AES-CBC pattern, used by FairPlay and cross-DRM CMAF. |
| `scheme_version` | int (hex `0x00010000`) | CENC scheme version. |
| `crypt_byte_block` | int | CBCS pattern: number of encrypted blocks in pattern (typically 1). |
| `skip_byte_block` | int | CBCS pattern: number of skipped blocks (typically 9). |

### Multi-key / key rotation

```xml
<GPACDRM>
  <CrypTrack trackID="1" IsEncrypted="1" IV_size="8"
             first_IV="0x..." saiSavedBox="senc">
    <key KID="0xKID1..." value="0xKEY1..."/>
    <key KID="0xKID2..." value="0xKEY2..."/>  <!-- key rotation -->
  </CrypTrack>
</GPACDRM>
```

Rotation interval is expressed via the `keyRoll` attribute (in samples) or encoded externally.

### CBCS (FairPlay / multi-DRM CMAF)

```xml
<CrypTrack trackID="1" IsEncrypted="1"
           scheme_type="cbcs" scheme_version="0x00010000"
           IV_size="16" first_IV="0x000102030405060708090a0b0c0d0e0f"
           crypt_byte_block="1" skip_byte_block="9"
           saiSavedBox="senc">
  <key KID="0x..." value="0x..."/>
</CrypTrack>
```

### ClearKey pssh injection

Add a `<DRMInfo>` sibling referencing ClearKey UUID `1077efec-c0b2-4d02-ace3-3c1e52e2fb4b`:

```xml
<GPACDRM>
  <DRMInfo type="pssh" version="1">
    <BS ID128="1077efecc0b24d02ace33c1e52e2fb4b"/>
    <BS bits="32" value="1"/>       <!-- KID count -->
    <BS ID128="ABCDEF01234567890ABCDEF012345678"/>
    <BS bits="32" value="0"/>       <!-- data size -->
  </DRMInfo>
  <CrypTrack trackID="1" ...>...</CrypTrack>
</GPACDRM>
```

---

## 6. New `gpac` filter-graph CLI (vs. legacy MP4Box)

GPAC ships a newer CLI called `gpac` (lowercase) — filter-graph style like ffmpeg. Same framework, different idioms.

```bash
# Inspect file
gpac -i in.mp4 inspect

# Transcode (uses filter chain: demux → decode → encode → mux)
gpac -i in.mp4 enc:c=h264 -o out.mp4

# DASH package (equivalent to MP4Box -dash)
gpac -i in.mp4 -o out/dash.mpd:profile=live:cdur=4

# With CENC encryption
gpac -i in.mp4 cecrypt:cfile=drm.xml -o enc.mp4

# Inspect pipeline / list filters
gpac -h filters
gpac -h filter_name
```

### MP4Box → gpac cheat sheet

| MP4Box | gpac |
|--------|------|
| `MP4Box -info in.mp4` | `gpac -i in.mp4 inspect` |
| `MP4Box -diso in.mp4` | `gpac -i in.mp4 mp4box:pretty` (approx) |
| `MP4Box -dash 4000 -rap -out m.mpd in.mp4` | `gpac -i in.mp4 -o m.mpd:cdur=4:profile=live` |
| `MP4Box -crypt drm.xml -out o.mp4 in.mp4` | `gpac -i in.mp4 cecrypt:cfile=drm.xml -o o.mp4` |
| `MP4Box -raw 1 in.mp4` | `gpac -i in.mp4#trackID=1 -o out.h264` |
| `MP4Box -add-sidx 4000 in.mp4` | `gpac -i in.mp4:frag=4 -o out.mp4:sidx=1` |

For most production pipelines today, MP4Box is the sweet spot: stable, documented in many tutorials, still maintained. `gpac` (CLI) is the future.

---

## 7. Recipe book

### 7.1 DASH live with separate A/V sources

```bash
MP4Box -dash 4000 -frag 4000 -rap \
  -dash-profile live \
  -segment-name 'seg_$RepresentationID$_$Number$' \
  -profile dashavc264:live \
  -out live/manifest.mpd \
  video_1080p.mp4#video video_720p.mp4#video audio.mp4#audio
```

Result: multiple video representations in MPD, one audio, HLS-interoperable CMAF segments.

### 7.2 MP4 surgery (rebuild from raw ES)

```bash
# 1. Extract
MP4Box -raw 1 in.mp4        # → in_track1.h264
MP4Box -raw 2 in.mp4        # → in_track2.aac

# 2. Rebuild, set lang + disposition
MP4Box -add in_track1.h264:name=Main \
       -add in_track2.aac:lang=eng \
       -new -out clean.mp4

# 3. Fast-start
MP4Box -tight clean.mp4
```

### 7.3 CENC + Shaka handoff

Do MP4-level work in MP4Box, then hand off to Shaka Packager for commercial DRM signaling:

```bash
# 1. MP4Box: fragment + inject sidx
MP4Box -frag 4000 -add-sidx 4000 -out frag.mp4 master.mp4

# 2. Shaka Packager: package with Widevine + FairPlay + PlayReady
packager \
  in=frag.mp4,stream=video,output=v.mp4 \
  in=frag.mp4,stream=audio,output=a.mp4 \
  --enable_widevine_encryption \
  --key_server_url https://license.widevine.com/cenc/getcontentkey/... \
  --content_id <id> \
  --signer <signer> --aes_signing_key <hex> --aes_signing_iv <hex> \
  --mpd_output manifest.mpd \
  --hls_master_playlist_output master.m3u8
```

See `media-shaka` skill for full Shaka recipes.

### 7.4 Low-latency CMAF (LL-DASH + LL-HLS)

```bash
MP4Box -dash 2000 -frag 200 -rap \
  -dash-profile live \
  -segment-timeline \
  -single-segment false \
  -out llout/manifest.mpd \
  video.mp4
```

Key: short fragments (`-frag 200` = 200 ms) inside longer segments (`-dash 2000`), `-segment-timeline` for variable fragment emit. Pair with `Availability-Time-Offset` and HTTP chunked-transfer on the origin.

### 7.5 Repair MP4 that ffmpeg can't open

```bash
# Dump boxes to see what's broken
MP4Box -diso suspect.mp4     # writes suspect_info.xml

# Common fixes:
MP4Box -tight suspect.mp4                         # move moov to front
MP4Box -frag 2000 -add-sidx 2000 -out fix.mp4 suspect.mp4   # re-fragment + re-sidx
MP4Box -elst '0,-1,1' suspect.mp4                 # strip edit list (use -1 as "all")
```

### 7.6 Extract + re-mux without any re-encode

```bash
MP4Box -raw 1 in.mp4
MP4Box -raw 2 in.mp4
MP4Box -add in_track1.h264 -add in_track2.aac -new out.mp4
```

Zero-loss: H.264 and AAC stay in their original elementary-stream bytes.

### 7.7 Sub-track (SVC, 360°, CMAF-alt)

MP4Box supports sub-track authoring for SVC (scalable H.264) and HEVC temporal layers:

```bash
MP4Box -add base.h264 -add enhancement.h264:svc out.mp4
```

For 360° metadata:

```bash
MP4Box -add in.mp4:box=st3d=0,sv3d=eqrc in.mp4
```

(Equirectangular mono; `st3d=1` = top/bottom 3D, `st3d=2` = side-by-side.)

### 7.8 ROUTE / DVB-MABR packaging

MP4Box supports broadcast-friendly ROUTE / DVB-MABR packaging:

```bash
MP4Box -dash 2000 -frag 2000 -rap \
  -route \
  -route-src 239.255.0.1:10000 \
  -out route/manifest.mpd \
  video.mp4 audio.mp4
```

Emits a ROUTE-compliant DASH with multicast packet hints for DVB broadcast.

---

## 8. Version quick-checks

```bash
MP4Box -version         # → MP4Box version X.Y.Z
gpac -version           # newer CLI
gpac -h filters | head  # list filters
MP4Box -h dash          # DASH options
MP4Box -h crypt         # CENC options
MP4Box -h split         # splitting options
```

Upstream docs: <https://wiki.gpac.io/> — authoritative but sometimes behind master.
