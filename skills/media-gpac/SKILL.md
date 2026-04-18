---
name: media-gpac
description: >
  Advanced MP4 / ISOBMFF authoring and diagnostics with GPAC (MP4Box, gpac): fragmented MP4, DASH+CMAF packaging, MP4 surgery (extract, dump, edit boxes), CENC encryption, sidx injection, sub-track management, raw track export, BIFS/LASeR, ROUTE/DVB-MABR. Use when the user asks to use MP4Box, fragment a MP4, extract tracks by ID, dump MP4 box structure, inject sidx indexing, CMAF-package for DASH, repair MP4 that ffmpeg can't, or do advanced ISO-BMFF surgery.
argument-hint: "[operation]"
---

# Media Gpac

**Context:** $ARGUMENTS

## Quick start

- **Inspect a broken MP4:** → Step 2 (`info` / `diso`)
- **Package DASH/CMAF:** → Step 3 (`dash` subcommand)
- **Fragment for fMP4:** → Step 3 (`fragment`)
- **Extract a raw track (h264/aac ES):** → Step 3 (`extract-track`)
- **CENC encrypt for ClearKey testing:** → Step 3 (`encrypt`)
- **Hand commercial DRM to Shaka instead:** → `media-shaka` skill

## When to use

- Doing ISO-BMFF surgery ffmpeg can't (box-level edits, precise track IDs, edit-list fixes).
- Packaging CMAF/DASH where fragment timing must be accurate (MP4Box beats ffmpeg's dash muxer).
- Dumping the full box tree to XML for diagnostics (`-diso`).
- Repairing broken moov/moof boxes, rewriting sidx, or setting language/default flags in-place.
- Authoring ClearKey-encrypted CENC content for pipeline testing.

## Step 1 — Install

```bash
# macOS
brew install gpac

# Debian/Ubuntu
sudo apt install gpac

# Fedora/RHEL
sudo dnf install gpac

# Verify
MP4Box -version
gpac -version
```

`MP4Box` is the legacy (stable, widely documented) CLI for ISOBMFF surgery. `gpac` is the newer filter-graph CLI (similar philosophy to ffmpeg filters). Prefer `MP4Box` for most tasks — it's documented everywhere.

## Step 2 — Pick the operation

| Task | Tool |
|------|------|
| Human-readable summary | `MP4Box -info in.mp4` |
| Full box tree as XML | `MP4Box -diso in.mp4` (writes `in_info.xml`) |
| Extract track as raw ES | `MP4Box -raw TID in.mp4` |
| Fragment for fMP4 | `MP4Box -frag 2000 in.mp4` |
| DASH / CMAF package | `MP4Box -dash 4000 -frag 4000 -rap …` |
| Inject sidx | `MP4Box -add-sidx 4000 in.mp4` |
| CENC encrypt | `MP4Box -crypt drm.xml -out o.mp4 in.mp4` |
| CENC decrypt | `MP4Box -decrypt drm.xml -out o.mp4 in.mp4` |
| Remove track | `MP4Box -rem TID in.mp4` |
| Set language | `MP4Box -lang TID=jpn in.mp4` |
| Enable/disable | `MP4Box -enable TID -disable TID in.mp4` |
| Split by time | `MP4Box -splitx T1:T2 in.mp4` |
| Edit list | `MP4Box -elst '0,N,1' in.mp4` |
| Add tracks | `MP4Box -add a.h264 -add a.aac out.mp4` |

Always pass `-out` when you want a new file — **MP4Box edits in-place otherwise**. Back up first.

## Step 3 — Run via the helper script

The `scripts/gpac.py` wrapper gives an argparse interface over these operations. Stdlib-only, non-interactive, `--dry-run` prints the command.

```bash
# Inspect
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py info --input in.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py diso --input in.mp4 --output boxes.xml

# Extract raw track 1 (ES)
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py extract-track --input in.mp4 --track 1 --output track1.h264

# Fragment (2-second fragments, in-place copy with -out)
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py fragment --input in.mp4 --output frag.mp4 --fragment-ms 2000

# DASH/CMAF (live profile)
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py dash --input in.mp4 --outdir dashout --segment-ms 4000 --profile live

# CENC ClearKey encrypt
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py encrypt \
  --input in.mp4 --output enc.mp4 \
  --key-id 0123456789abcdef0123456789abcdef \
  --key fedcba9876543210fedcba9876543210

# Remove track 2 (usually audio #2)
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py remove-track --input in.mp4 --output stripped.mp4 --track 2

# Set language on track 2
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py set-lang --input in.mp4 --track 2 --lang jpn

# Split by time
uv run ${CLAUDE_SKILL_DIR}/scripts/gpac.py split-time --input in.mp4 --output-pattern seg --start 00:00:10 --end 00:00:30
```

Add `--dry-run` to print the MP4Box command without executing. Add `--verbose` to echo the command before running.

## Step 4 — Verify

After any authoring step, confirm result with:

```bash
MP4Box -info out.mp4
```

For DASH, validate the manifest:

```bash
xmllint --noout manifest.mpd
ls -la dashout/   # should contain init.mp4 + seg_*.m4s (live) OR one onDemand file
```

For CENC: play with `ffplay -decryption_key KEY enc.mp4` or a Shaka-Player ClearKey page. For fragmented MP4: `MP4Box -info` shows `Fragmented: yes` and lists `moof` count.

## Available scripts

- **`scripts/gpac.py`** — argparse wrapper for MP4Box: `check`, `info`, `diso`, `extract-track`, `fragment`, `dash`, `encrypt`, `decrypt`, `remove-track`, `set-lang`, `split-time`. Generates DRM XML for CENC ops in a temp file.

## Reference docs

Read [`references/gpac.md`](references/gpac.md) when:

- Choosing a DASH profile (`live`, `onDemand`, `main`, `full`).
- Looking up an ISO-BMFF box (`moov`, `moof`, `sidx`, `senc`, `saio`, `saiz`, `pssh`, `mvex`).
- Writing a CENC XML by hand.
- Translating MP4Box idioms to the new `gpac` filter graph syntax.

## Gotchas

- **`MP4Box` vs `gpac`**: both ship with the GPAC framework. `MP4Box` is legacy CLI (stable, everywhere). `gpac` (lowercase) is the newer filter-graph CLI — `gpac -i input -o output` with a filter pipeline; list plugins via `gpac -h filters`. Prefer `MP4Box` unless you need filter-graph semantics.
- **In-place edits**: MP4Box mutates the input file unless you pass `-out`. Always back up or pass `-out`.
- **Track IDs start at 1**, not 0. `MP4Box -info` lists them.
- **`-raw TID` extracts the ES** (elementary stream: raw H.264 NAL units, raw AAC ADTS, etc.) — not a container. Feed it back in via `-add track.h264`.
- **`-diso` dump is huge** — dumps the entire box tree as XML. Redirect to a file; don't cat it.
- **`-dash 4000` = 4000 ms segment duration.** `-frag` is fragment duration inside each segment (usually equal to `-dash`).
- **`-rap` forces each segment to start on a random access point (IDR).** Omit and you will get unseekable DASH.
- **`sidx` = Segment Index box.** Required for byte-range DASH (`onDemand` profile). Live profile uses separate `.m4s` files and doesn't need it.
- **CMAF segments are `.m4s`** + `init.mp4`. Sent as independent files over HTTP.
- **`-dash-profile live`** → segmented, fragmented, templated URLs (`$Number$`). **`onDemand`** → single file with indexed byte ranges. **`main`/`full`** = older DASH profiles.
- **`-dash-ctx <file>`** saves packaging state — required for continuous live DASH across MP4Box invocations.
- **CENC encryption XML** follows a GPAC-specific schema (see references). `KID` and `key` are hex with `0x` prefix. `IV_size` is 8 (CTR-64) or 16 (CTR-full). `first_IV` seeds the counter.
- **MP4Box does CENC but NOT commercial DRM** (Widevine / PlayReady / FairPlay license-server signaling). For those, package with MP4Box first, then hand off to Shaka Packager — see `media-shaka` skill.
- **`senc` vs `saio`/`saiz`**: MP4Box writes the correct auxiliary-info boxes; don't mix CENC between tools mid-pipeline.
- **ffmpeg philosophy vs MP4Box**: ffmpeg is general-purpose (many containers, filters, codecs). MP4Box is ISOBMFF-surgeon — precise box manipulation ffmpeg's demuxer/muxer can't express.
- **`-tight`** reorders the `moov` box for streaming (fast-start). Equivalent to ffmpeg's `-movflags +faststart`.
- **Disk space**: MP4Box writes temp files next to the input. Large DASH packaging can briefly 2x disk use.
- **`-splitx T1:T2`** uses timecodes (e.g., `00:01:00:00:02:00`). Some versions want `-splitx T1/T2` syntax — check `MP4Box -h split` on your build.

## Examples

### Example 1: Package a mezzanine MP4 for DASH live

```bash
MP4Box -dash 4000 -frag 4000 -rap \
  -segment-name 'seg_$RepresentationID$_$Number$' \
  -dash-profile live \
  -out dashout/manifest.mpd \
  input.mp4#video input.mp4#audio
```

Result: `dashout/manifest.mpd`, per-representation `init.mp4`, and `seg_video_1.m4s`, `seg_audio_1.m4s`, ...

### Example 2: Repair an MP4 that ffmpeg can't stream

```bash
# 1. Inspect: look for missing sidx, broken edit list, or non-fragmented moov
MP4Box -info broken.mp4

# 2. Rewrite with fragments + sidx
MP4Box -frag 2000 -add-sidx 2000 -out fixed.mp4 broken.mp4

# 3. Verify
MP4Box -info fixed.mp4   # "Fragmented: yes", moof count > 0, sidx present
```

### Example 3: CENC ClearKey encrypt for pipeline testing

`drm.xml`:

```xml
<GPACDRM>
  <CrypTrack trackID="1" IsEncrypted="1" IV_size="8"
             first_IV="0x0123456789abcdef" saiSavedBox="senc">
    <key KID="0xABCDEF01234567890ABCDEF012345678"
         value="0x112233445566778899AABBCCDDEEFF00"/>
  </CrypTrack>
</GPACDRM>
```

```bash
MP4Box -crypt drm.xml -out enc.mp4 in.mp4
```

Decrypt with the same XML: `MP4Box -decrypt drm.xml -out dec.mp4 enc.mp4`.

### Example 4: Extract H.264 ES, remux into new MP4

```bash
MP4Box -raw 1 in.mp4          # writes in_track1.h264
MP4Box -raw 2 in.mp4          # writes in_track2.aac
MP4Box -add in_track1.h264 -add in_track2.aac -new combined.mp4
```

## Troubleshooting

### Error: `Cannot find adaptation set`

Cause: DASH packager couldn't correlate streams — usually bad `#video`/`#audio` track-selection syntax.
Solution: list tracks via `MP4Box -info`. Use `input.mp4#trackID=1` explicit syntax instead of `#video`.

### Error: `Segment duration not a multiple of frame rate`

Cause: `-dash 4000` doesn't align to the GOP. With 24 fps + 2s GOP, pick 4000/8000 ms (multiples of GOP ms).
Solution: re-encode source with a fixed GOP matching your segment duration, or use `-rap` and accept slightly variable segment sizes.

### Error: `Cannot write to file: permission denied`

Cause: MP4Box tries to edit input in-place and the file is read-only.
Solution: pass `-out newname.mp4` explicitly.

### Error: `Unknown track reference`

Cause: operating on a track ID that doesn't exist.
Solution: `MP4Box -info file.mp4` — track IDs are 1-based and listed in the summary.

### Error: `Encryption: wrong KID/key format`

Cause: hex values missing `0x` prefix or wrong length (KID must be 16 bytes / 32 hex chars; key must be 16 bytes / 32 hex chars).
Solution: double-check lengths. `openssl rand -hex 16` generates valid values.
