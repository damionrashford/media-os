# CEA-608 / CEA-708 Closed Caption Reference

Deep reference for the `ffmpeg-captions` skill. Covers protocol differences, per-container carriage, sidecar file layouts, ccextractor flags, SEI A53 NAL internals, and a verification checklist.

## 1. CEA-608 vs CEA-708

| Aspect | CEA-608 (EIA-608) | CEA-708 (EIA-708) |
| --- | --- | --- |
| Era | NTSC analog broadcast (1980) | ATSC digital broadcast (1999) |
| Bitrate | 960 bit/s per field (480 bit/s per channel) | ~9600 bit/s shared across services |
| Charset | 7-bit ASCII + extended Western European chars | UTF-16 (full Unicode) |
| Channels / Services | 4 caption channels (CC1–CC4) + 4 text channels (T1–T4) | 63 services (Service 1–63) |
| Colors | 8 foreground, 8 background (preset) | 64-color palette, 4 opacity levels, custom ARGB |
| Positioning | 15 rows × 32 cols fixed grid | Arbitrary anchored windows, up to 8 per service |
| Modes | Pop-on, roll-up (2/3/4 rows), paint-on | Pop-on, roll-up, paint-on, plus window effects |
| Languages | English (CC1), Spanish (CC3) typical | Any language per service |
| Carrier (analog) | Line 21 field 1 (CC1/CC2/T1/T2) + field 2 (CC3/CC4/T3/T4) | N/A |
| Carrier (digital) | SEI A53 cc_data in H.264/HEVC, or c608 track | SEI A53 cc_data in H.264/HEVC, or c708 track |

**Practical rule:** modern US broadcast streams carry **both**. 608 is the fallback; 708 is the primary. The FCC mandates 608 compatibility for set-top boxes.

### Channel numbering (608)

- **CC1** — primary language, usually English pop-on.
- **CC2** — secondary, often same-language alternate (edited-for-broadcast).
- **CC3** — tertiary, frequently Spanish.
- **CC4** — fourth channel, rarely used.
- **T1–T4** — text channels, used for program data (not captions).

### Service numbering (708)

- **Service 1** — primary English.
- **Service 2** — Spanish (typical).
- Services 3–63 — unused in practice.

## 2. Container carriage matrix

| Container | SEI A53 (embedded) | Dedicated CC track | Soft subtitle track | Notes |
| --- | --- | --- | --- | --- |
| **MPEG-TS** (.ts, .m2ts) | Yes (native) | No | No | Standard for broadcast. Captions ride in video PID. |
| **MP4** (.mp4) | Yes (requires `-a53cc 1` on encode) | Yes (c608, c708) | Yes (mov_text) | Two incompatible carriage modes; pick one per workflow. |
| **MOV** (.mov) | Yes | Yes (c608, c708) | Yes | FCP/Resolve/AME expect `c608`/`c708` tracks, not SEI. |
| **MXF** (.mxf) | Yes | Yes (ANC data track) | No | Broadcast master format; SMPTE 436M ANC. |
| **MKV** (.mkv) | No (stripped by muxer) | No | Yes (SRT/ASS) | Convert 608 → SRT before muxing. |
| **WebM** | No | No | Yes (WebVTT) | Browser-oriented; extract CC to VTT. |
| **FLV** | Partial | No | No | Legacy RTMP; some builds preserve SEI. |
| **HLS (fMP4 segments)** | Yes | Limited | Sidecar (WebVTT) | Apple HLS spec allows 608/708 in video + external VTT. |
| **HLS (MPEG-TS segments)** | Yes (native) | No | Sidecar (WebVTT) | Captions preserved through `-c:v copy`. |
| **DASH** | Yes in fMP4 | Via `emsg` / separate track | Sidecar (TTML, IMSC) | IMSC1 is the DASH standard text track. |

## 3. SCC (Scenarist Closed Caption) file format

Plain ASCII, line-based. Example:

```
Scenarist_SCC V1.0

01:00:01:00   9420 9420 9470 9470 c3c8 c1d2 d3c5 e480 942f 942f

01:00:04:15   9420 9420 9470 9470 cec5 d6c5 d280 c7c9 d665 94f8
```

- **Line 1** — magic header `Scenarist_SCC V1.0`.
- **Blank line** required before data.
- **Each caption line:** `HH:MM:SS:FF   4-hex-byte-pairs...` (tab-separated, space-separated, or both).
- **Timecode** — SMPTE 29.97 **drop-frame** (semicolons sometimes substituted for the last colon: `01:00:01;00`). Non-drop uses all colons.
- **Hex pairs** — raw 608 caption control bytes, odd-parity, little-endian channel order. Each pair = two bytes of 608 data for one field.
- **End-of-caption** signalled by `942f 942f` (display command with preamble).
- **Frame rate** — assumed 29.97 DF. No header override.

SCC files match the video by **timecode**, not by wall time. Verify timecode base before remux.

## 4. MCC (MacCaption) file format

SCC's modern successor. ASCII with explicit metadata.

```
File Format=MacCaption_MCC V2.0

///////////////////////////////////////////////////////////////////////////////////
// Computer Prompters                                                           //
///////////////////////////////////////////////////////////////////////////////////

UUID=9F6112F4-D9D0-4AAD-8C1A-0123456789AB
Creation Program=Caption Inspector
Creation Date=Thursday, November 14, 2024
Creation Time=14:32:11
Time Code Rate=30DF
...

01:00:01:00	T404F4F4AD0DC940E94...
```

- **Header block** with `File Format=`, `Time Code Rate=` (`24`, `25`, `2997`, `30`, `2997DF`, `5994DF`, etc.), UUID, creation metadata.
- **Data lines** use compressed hex (run-length escape codes like `T` for run of `40`).
- Carries **both 608 and 708 payloads** (vs SCC which is 608-only).
- Frame-rate explicit — no guessing.

Never rename `.mcc` → `.scc` or vice versa; parsers will misinterpret.

## 5. STL (EBU 3264) file format

European broadcast subtitle/caption exchange. **Binary**, not ASCII.

- 1024-byte **General Subtitle Information** (GSI) header.
- N × 128-byte **Text/Timing Information** (TTI) blocks.
- Character set: **GSI CCT field** determines encoding (Latin, Latin/Cyrillic, Latin/Arabic, Latin/Greek, Latin/Hebrew).
- Timecodes in GSI are SMPTE `HH:MM:SS:FF` (25 fps for PAL/SECAM, 30 for NTSC).
- Max 4 rows × 40 chars per block; long captions span multiple blocks.

ffmpeg does not natively parse `.stl` broadcast files (only the SubRip-variant). Use `EBU-STL` tools or ccextractor plugins.

## 6. ccextractor command reference

Key flags used by this skill:

| Flag | Purpose |
| --- | --- |
| `-o FILE` | output file |
| `-out=FORMAT` | `srt`, `webvtt`, `ttml`, `sami`, `mcc`, `scc`, `raw`, `bin`, `dvdraw`, `report` |
| `-stdout` | write to stdout instead of a file |
| `-cc=N` | extract channel N (1–4); default CC1 |
| `-ucla` | strict SMPTE drop-frame handling (matches pro workflows) |
| `-trim` | trim leading/trailing spaces from captions |
| `-unicode` | force UTF-8 output |
| `-bufferinput` | buffer from stdin (for pipes) |
| `-quiet` | suppress progress |
| `-12` / `-cc1` | extract CC1 only (synonyms) |
| `-13` / `-cc3` | extract CC3 only |
| `-in=ts\|mp4\|mkv\|mxf\|gxf\|wtv` | force input format |
| `-datapid N` | MPEG-TS PID override |
| `--videotype h264\|mpeg2` | force codec for ambiguous streams |
| `-mp4` | force MP4 input |
| `-autoprogram` | pick first valid program in TS |
| `-delay MS` | shift output by N milliseconds |
| `-startat HH:MM:SS` / `-endat` | trim output to a time window |

Exit codes: `0` success, nonzero on no-CC-found or parse error.

## 7. SEI A53 NAL unit details

H.264 / HEVC carry 608/708 inside **SEI (Supplemental Enhancement Information)** NAL units, specifically:

- **NAL type 6** (H.264) / **NAL type 39** (HEVC) — SEI.
- **SEI payload type 4** — `user_data_registered_itu_t_t35`.
- **itu_t_t35_country_code = 0xB5** (USA).
- **itu_t_t35_provider_code = 0x0031** (ATSC).
- **user_identifier = 'GA94'** (0x47413934).
- **user_data_type_code = 0x03** — ATSC A/53 `cc_data`.
- Followed by `cc_count` × 3 bytes of `cc_data_pkt` (valid flag, cc_type 608-field-1/2 or 708, two data bytes).

Bitstream filters that rewrite SEI (`filter_units`, `remove_extra`, some `h264_metadata` configurations) can **drop** A53 payloads. When captions must survive, verify after every container/bitstream change.

## 8. Verification checklist

Run after any transcode, remux, or bitstream filter.

```bash
# 1. Side-data probe (first 20 frames)
ffprobe -loglevel error -select_streams v:0 \
  -show_entries frame=side_data_list \
  -read_intervals "%+#20" out.ts | grep -i 'a53\|closed caption'

# 2. Dedicated CC stream check
ffprobe -loglevel error -show_streams out.mov \
  | grep -iE 'codec_name=(eia_608|eia_708|c608|c708)'

# 3. Filter-based decode (after rendering onto picture)
ffmpeg -i out.ts -vf "readeia608,metadata=mode=print" -an -f null - 2>&1 \
  | grep 'lavfi.readeia608' | head

# 4. External extraction sanity
ccextractor out.ts -o /tmp/verify.srt -quiet && wc -l /tmp/verify.srt

# 5. Byte-level SEI hunt (for paranoia)
ffmpeg -i out.ts -c copy -bsf:v trace_headers -f null - 2>&1 \
  | grep -iE 'sei|a53|user_data_registered' | head
```

If (1) or (4) returns data, captions survived. If only (3) returns data, captions are **on picture** but not in bitstream (burned-in). If all return empty, captions were dropped.

## 9. Round-trip reference

Canonical pipelines for common tasks.

**TS → TS (re-encode H.264, keep captions):**
```bash
ffmpeg -i in.ts -c:v libx264 -crf 20 -a53cc 1 -c:a copy out.ts
```

**TS → MP4 (remux, keep captions):**
```bash
ffmpeg -i in.ts -c copy -movflags +faststart out.mp4
```

**TS → SRT (external extraction):**
```bash
ccextractor in.ts -o captions.srt
```

**SCC → SRT (sidecar conversion):**
```bash
ccextractor captions.scc -o captions.srt
```

**MP4 → MP4 with c608 track (for FCP/Resolve):**
```bash
# Extract to SCC first, then mux as c608 track (requires compatible ffmpeg build).
ccextractor in.mp4 -out=scc -o out.scc
ffmpeg -i in.mp4 -f scc -i out.scc -c copy -map 0:v -map 0:a -map 1 final.mp4
```

**MKV with CC (convert to soft sub):**
```bash
ccextractor in.mkv -o in.srt
ffmpeg -i in.mkv -i in.srt -c copy -c:s srt out.mkv
```
