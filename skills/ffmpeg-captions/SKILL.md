---
name: ffmpeg-captions
description: >
  Closed captions CEA-608/708 with ffmpeg: -a53cc 1 passthrough, readeia608 extraction, SCC and MCC and STL import/export, ccextractor handoff, 608 → SRT conversion, burning 608 to picture, preserving captions in MPEG-TS and MP4 and MOV. Use when the user asks to extract CEA-608 captions, preserve 708 captions, convert SCC to SRT, burn broadcast captions into video, pass through captions during transcode, or extract closed captions from a ProRes/MXF/TS file.
argument-hint: "[action] [input]"
---

# Ffmpeg Captions

**Context:** $ARGUMENTS

CEA-608/708 closed captions are carried **inside** the H.264 video stream (A53 SEI NAL units) or in sidecar SCC/MCC/STL files. They are NOT subtitle tracks. For subtitle-file workflows (SRT/ASS/VTT), use the `ffmpeg-subtitles` skill.

## Quick start

- **Preserve captions during H.264 re-encode:** → Step 3, `-a53cc 1` recipe
- **Check whether a file has embedded 608/708:** → Step 1, detect
- **Extract embedded CC to SRT:** → Step 3, `ccextractor` recipe
- **Remux without losing captions:** → Step 3, passthrough recipe
- **Burn captions into the picture:** → Step 3, extract then hand off to `ffmpeg-subtitles`

## When to use

- Source is MPEG-TS, MP4, MOV, or MXF with embedded 608/708 (broadcast, ATSC, FCC-compliant deliverables).
- You have a sidecar `.scc`, `.mcc`, or `.stl` and need to mux or convert it.
- You are re-encoding H.264 and must not lose the SEI caption data.
- You need a plain `.srt` from 608/708 for downstream tools.

## Step 1 — Identify caption location

Captions can live in one of five places. Check all of them:

1. **Embedded SEI A53_CC in H.264 video** (MPEG-TS, MP4, MOV, MXF) — invisible to `ffprobe -show_streams`.
2. **Dedicated c608/c708 track in MOV/MP4** — appears in `ffprobe` as `codec_name=eia_608` or `closed_caption`.
3. **SCC sidecar file** (`.scc`) — timecoded hex byte pairs, NTSC drop-frame usually.
4. **MCC sidecar file** (`.mcc`) — MacCaption, SCC's modern descendant with explicit frame-rate header.
5. **STL sidecar file** (`.stl`) — EBU 3264, European broadcast.
6. **Open (burned-in) captions in the picture** on NTSC line 21 — read via `readeia608` filter.

To detect embedded SEI captions:

```bash
ffprobe -loglevel error -select_streams v:0 -show_entries frame=side_data_list \
  -of default=noprint_wrappers=1 in.ts | grep -i a53 | head -5
```

If nothing is returned, try the filter path (picture line 21):

```bash
ffmpeg -hide_banner -i in.mov -vf "readeia608,metadata=mode=print" -an -f null - 2>&1 | head -40
```

Or hand off to the external detector:

```bash
ccextractor in.mov --stdout > /dev/null    # exits nonzero if no CC found
```

## Step 2 — Pick the operation

| Goal | Operation | Command |
| --- | --- | --- |
| Keep captions when transcoding H.264 | preserve | `-a53cc 1` on libx264 |
| Keep captions when remuxing (no re-encode) | passthrough | `-c copy` |
| Get a `.srt` from embedded 608/708 | extract | `ccextractor` |
| Get a `.srt` from `.scc` / `.mcc` | convert | `ccextractor` |
| Burn captions into the picture | burn | extract to SRT, then `ffmpeg-subtitles` |
| Import SCC as a subtitle stream into TS | mux | `-f scc -i ... -c:s copy` |

## Step 3 — Run the command

### Preserve embedded 608 during H.264 re-encode

```bash
ffmpeg -i in.ts -c:v libx264 -crf 20 -a53cc 1 -c:a copy out.ts
```

Without `-a53cc 1`, libx264 **silently discards** SEI CC data. This flag only **preserves** what the source already has — it does not create captions.

### Passthrough remux (fastest, lossless)

```bash
ffmpeg -i in.ts -c copy -map 0 out.mp4
```

Copying the video stream preserves the A53 SEI NAL units automatically. MPEG-TS → MP4 and MP4 → MOV generally survive; verify with Step 4.

### Extract 608/708 to SRT via ccextractor

```bash
ccextractor in.ts -o out.srt
ccextractor in.mov -out=srt -o out.srt           # explicit
ccextractor in.ts -o out.vtt -out=webvtt          # VTT instead
ccextractor in.mcc -o out.srt                     # MCC → SRT
ccextractor in.scc -o out.srt                     # SCC → SRT
```

Install on macOS: `brew install ccextractor`. On Debian/Ubuntu: `apt install ccextractor`.

### readeia608 filter (open captions on line 21 of NTSC)

```bash
ffmpeg -i in.mov -vf "readeia608,metadata=mode=print:file=captions.txt" \
  -an -f null -
```

This only works when 608 bytes are **drawn into the picture** on lines 0–1 (legacy NTSC line 21). It does NOT read SEI-embedded CC. Output is frame-level metadata (`lavfi.readeia608.0.cc`, `.sub`, etc.) which you then parse into SRT yourself.

### Import SCC sidecar as a subtitle stream

```bash
ffmpeg -i video.mp4 -f scc -i captions.scc \
  -c:v copy -c:a copy -c:s copy -map 0:v -map 0:a -map 1 out.mp4
```

SCC demuxer support depends on ffmpeg build; verify with `ffmpeg -formats | grep -i scc`. If missing, fall back to `ccextractor` round-trip: SCC → SRT → mux as soft subtitle (see `ffmpeg-subtitles`).

### Burn broadcast captions into the picture

Two-step: extract to SRT, then hand off.

```bash
ccextractor in.ts -o captions.srt
# now use the ffmpeg-subtitles skill:
ffmpeg -i in.ts -vf "subtitles=captions.srt" -c:a copy out.mp4
```

## Step 4 — Verify captions survived

```bash
# 1. Probe for A53 side data on first video frames
ffprobe -loglevel error -select_streams v:0 \
  -show_entries frame=side_data_list -read_intervals "%+#20" out.ts \
  | grep -i a53

# 2. Decode and re-read via readeia608 (after on-screen render)
ffmpeg -i out.ts -vf "readeia608,metadata=mode=print" -an -f null - 2>&1 \
  | grep -i 'lavfi.readeia608' | head

# 3. External sanity check
ccextractor out.ts -o /tmp/verify.srt && wc -l /tmp/verify.srt
```

If all three return empty, captions were dropped.

## Available scripts

- **`scripts/cc.py`** — detect / preserve / extract / passthrough helper around ffmpeg + ccextractor. Subcommands: `detect`, `preserve`, `extract`, `passthrough`. `--dry-run`, `--verbose`.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py detect --input in.ts
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py preserve --input in.ts --output out.ts --crf 20
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py extract --input in.ts --output captions.srt
uv run ${CLAUDE_SKILL_DIR}/scripts/cc.py passthrough --input in.ts --output out.mp4
```

## Reference docs

- Read [`references/formats.md`](references/formats.md) for CEA-608 vs 708 protocol differences, per-container carriage matrix, SCC / MCC / STL file layouts, ccextractor flag reference, SEI A53 NAL details, and the verification checklist.

## Gotchas

- **Embedded captions are invisible to most tools.** 608/708 live as SEI NAL units **inside the video bitstream** — they are not a separate subtitle track, do not appear in `ffprobe -show_streams`, and tools unaware of SEI will silently ignore them.
- **`-a53cc 1` does NOT create captions.** It only **preserves** existing SEI CC data during libx264 encode. Source must already have them.
- **Re-encoding without `-a53cc 1` silently drops captions.** No warning, no error. Always set the flag when re-encoding H.264 broadcast source.
- **`-c:v copy` preserves SEI automatically** because it copies the raw NAL units. Prefer passthrough when possible.
- **MPEG-TS preserves 608 natively** inside the video PID. Round-tripping through TS is the safest transport.
- **MP4 has two caption carriage modes:** SEI passthrough (via `-a53cc 1`) or a dedicated `c608`/`c708` track. They are different; check which one your target player expects.
- **MOV (QuickTime) uses `c608`/`c708` track types** — FCP, Resolve, Adobe Media Encoder expect this, NOT SEI.
- **ccextractor is a separate tool,** not bundled with ffmpeg. Install with `brew install ccextractor` / `apt install ccextractor`.
- **`readeia608` reads lines 0–1 of the DECODED picture,** NOT SEI or side-data. Only useful for open/burned captions on NTSC line 21.
- **708 supersedes 608** (UTF-16 vs 7-bit, more colors, positioning, languages). Most broadcast content carries **both** for backward compatibility.
- **608 has 4 channels** (CC1–CC4) plus text (T1–T4). CC1 is primary English; CC3 is often Spanish. Specify with `ccextractor --cc=1`.
- **608 → modern formats is lossy.** Roll-up, pop-on, paint-on modes, per-character colors, and precise positioning all flatten to plain SRT.
- **SCC files are timecoded to the video's SMPTE timecode** (usually 29.97 drop-frame). Mismatched timecode = shifted captions.
- **MCC has an explicit frame-rate header;** SCC assumes 29.97 DF. Never rename `.mcc` to `.scc`.
- **STL (EBU 3264) is European broadcast** — binary, not ASCII. Requires dedicated parsers.
- **Some MP4 muxers strip SEI NAL units** even with `-c:v copy`. Verify with Step 4 after every transcode.
- **`-bsf:v filter_units=...`** can accidentally strip SEI. Avoid when captions must survive.

## Examples

### Example 1: Comcast deliverable, re-encode to h264 while keeping captions

```bash
ffmpeg -i master.mxf -c:v libx264 -crf 18 -preset slow -a53cc 1 \
  -c:a aac -b:a 192k -ac 2 out.ts
ccextractor out.ts -o /tmp/verify.srt  # confirm CC1 present
```

### Example 2: Convert SCC sidecar to SRT for a web player

```bash
ccextractor broadcast.scc -o broadcast.srt
```

### Example 3: Burn CC1 into a social-media cut

```bash
ccextractor in.ts --cc=1 -o cc1.srt
ffmpeg -i in.ts -vf "subtitles=cc1.srt:force_style='FontSize=28'" \
  -c:a copy social.mp4
```

### Example 4: Remux TS → MP4 without losing captions

```bash
ffmpeg -i broadcast.ts -c copy -movflags +faststart broadcast.mp4
ffprobe -loglevel error -select_streams v:0 \
  -show_entries frame=side_data_list -read_intervals "%+#10" broadcast.mp4 \
  | grep -i a53
```

## Troubleshooting

### Error: "No closed captions found" (ccextractor exits nonzero)

Cause: source has no embedded CC, or they are in a c608 track not SEI.
Solution: run `ffprobe -show_streams in.mov | grep -i eia_608` to check for a dedicated CC track. If present, extract with `ffmpeg -i in.mov -map 0:s -c:s copy out.srt` — try `ffmpeg-subtitles` skill for the mux. If neither, the file truly has no captions.

### Captions disappeared after `ffmpeg -c copy`

Cause: the target muxer stripped SEI NAL units (some MP4 builds, WebM always).
Solution: mux to MPEG-TS instead, or re-encode with `-c:v libx264 -a53cc 1`. WebM/Matroska cannot carry 608/708 SEI — convert to a separate subtitle track.

### Captions shift by ~2 seconds after SCC → SRT

Cause: SCC timecode is drop-frame (29.97), tool interpreted as non-drop (30).
Solution: pass `--ucla` to ccextractor or explicitly set `-ff=30000/1001` on the video side. MCC files avoid this because they carry a frame-rate header.

### `readeia608` returns no output on broadcast capture

Cause: captions are in SEI, not drawn on picture line 21.
Solution: use `ccextractor` instead. `readeia608` only reads pixels from decoded video, not bitstream metadata.

### `-a53cc 1` rejected: "Option not found"

Cause: your libx264 build is too old, or you applied the flag to a non-libx264 encoder.
Solution: verify with `ffmpeg -h encoder=libx264 | grep a53cc`. Upgrade ffmpeg if missing. HEVC/AV1 have separate mechanisms (hevc: `-udu_sei 1` for SEI passthrough; AV1: `-enable-cdef` etc.).
