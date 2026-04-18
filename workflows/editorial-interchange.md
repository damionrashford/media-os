# Editorial Interchange Workflow

**What:** Move timelines between NLEs (Premiere, Final Cut Pro, DaVinci Resolve, Avid Media Composer) without losing cuts, effects, or media links. Conform, consolidate, and validate media while keeping editorial intent intact.

**Who:** Editors, assistants, post supervisors, studios working across multiple facilities, hybrid remote/onsite teams.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| OTIO adapter docs | `otio-docs` | Pick the right adapter: FCP XML, Premiere XML, Resolve, AAF, EDL, CMX3600 |
| OTIO conversion | `otio-convert` | `otioconvert` round-trip between formats |
| MKV surgery | `media-mkvtoolnix` | Split at chapters, edit metadata, repair |
| MP4/CMAF surgery | `media-gpac` | Fragment, repair, extract tracks |
| Source analysis | `ffmpeg-probe`, `media-mediainfo` | Verify conformed media matches editorial |
| Transcode | `ffmpeg-transcode` | Proxies + online masters |
| HW encode (proxies) | `ffmpeg-hwaccel` | Fast proxy generation |
| Subtitles | `ffmpeg-subtitles` | Preserve through conform |
| Captions | `ffmpeg-captions` | CEA-608/708 preservation |
| Metadata | `media-exiftool`, `ffmpeg-metadata` | Preserve camera metadata across conforms |
| Batch | `media-batch` | Parallel conform of many clips |
| MediaInfo | `media-mediainfo` | Deep diagnostics when things don't match |

---

## The pipeline

### 1. Understand what's coming in

Every NLE exports differently:

| NLE | Native export | Fallback |
|---|---|---|
| Adobe Premiere Pro | `FCP7 XML` (FCPXML) or `AAF` | EDL |
| Final Cut Pro (X / 10.x) | `FCPXML` (NOT FCP7 XML — different schema) | XML via X2Pro |
| DaVinci Resolve | DRP (Resolve proprietary), FCPXML export, AAF, EDL, XML | |
| Avid Media Composer | AAF (primary), EDL | |
| Lightworks | `AAF`, EDL | |
| Custom timeline | `OTIO` (native) | |

Use `otio-docs` to find the right adapter for the source format:

```bash
uv run .claude/skills/otio-docs/scripts/otiodocs.py search \
  --query "premiere adapter" --page adapters
```

### 2. Convert source timeline to OTIO (or target format)

OTIO is the pivot format — convert source → OTIO → target.

```bash
# Premiere XML → OTIO
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.xml --output show.otio \
  --input-adapter fcp_xml --output-adapter otio_json

# OTIO → Resolve-compatible FCPXML
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.otio --output show-resolve.fcpxml \
  --input-adapter otio_json --output-adapter fcpx_xml

# OR direct Premiere → AAF (for Avid)
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.xml --output show.aaf \
  --input-adapter fcp_xml --output-adapter aaf_adapter
```

### 3. Extract media dependencies

Every timeline references source media. Extract the unique clip list:

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py list-media \
  --input show.otio --output media-manifest.json
```

Output:
```json
[
  {"source": "/vol/shoots/cam1/A001_C001.mov", "in": 100, "out": 220, "used": true},
  {"source": "/vol/shoots/cam1/A001_C002.mov", "in": 0, "out": 320, "used": true}
]
```

### 4. Verify source media specs

Make sure every source clip is what editorial thinks it is:

```bash
# Per-clip probe
for f in $(jq -r '.[].source' media-manifest.json); do
  uv run .claude/skills/ffmpeg-probe/scripts/probe.py streams "$f"
done

# Deep diagnostics for mismatches
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file "/vol/shoots/cam1/A001_C001.mov" --format json
```

Look for: inconsistent frame rates across clips, mixed codecs, dropped frames (drop-frame timecode but no DF flag), audio sample rate drift.

### 5. Consolidate + conform

Bring all source media to a single codec/resolution for the online:

```bash
# Transcode everything to ProRes 422 HQ for conform
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob '/vol/shoots/*/*.mov' \
  --output-dir /vol/conform/ \
  --jobs 4 \
  --command 'ffmpeg -i {in} -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -c:a pcm_s24le {out}'
```

Parallel with GNU parallel, log each command, log timings.

### 6. Remap media paths in the timeline

When the conformed media lives at new paths, update the OTIO:

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py remap-media \
  --input show.otio --output show-conformed.otio \
  --from /vol/shoots/ --to /vol/conform/
```

### 7. Generate proxies for offline edit

```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob '/vol/shoots/*/*.mov' \
  --output-dir /vol/proxies/ \
  --jobs 8 \
  --command 'ffmpeg -i {in} -vf scale=960:540 -c:v h264_videotoolbox -b:v 3M -c:a aac {out}'
```

Then emit a proxy-linked OTIO:

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py link-proxies \
  --input show.otio --output show-proxies.otio \
  --proxy-dir /vol/proxies/ --proxy-suffix -proxy.mp4
```

### 8. Package deliverables by NLE

**To Avid AAF + Avid DNxHR MXF:**

```bash
# Transcode to DNxHR
ffmpeg -i master.mov -c:v dnxhd -profile:v dnxhr_hq \
  -pix_fmt yuv422p -c:a pcm_s24le -f mxf master.mxf

# Emit AAF
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.otio --output show.aaf --output-adapter aaf_adapter
```

**To Resolve (DRP / FCPXML):**

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.otio --output show.fcpxml --output-adapter fcpx_xml
```

**To Premiere:**

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.otio --output show.xml --output-adapter fcp_xml
```

### 9. Validate on the target NLE

- Import into the NLE.
- Check: number of clips, total timeline duration, transitions preserved, audio levels matching, subclip in-points aligned.
- Spot-check 3-5 random edit points for frame accuracy.

---

## Variants

### EDL-only workflow (legacy / archival)

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show.otio --output show.edl \
  --output-adapter cmx_3600
```

CMX3600 EDLs support simple cuts + basic transitions. No effects, no overlapping tracks, no audio automation.

### Round-trip sanity check

Convert A → B → A and diff:

```bash
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input original.xml --output roundtrip.otio \
  --input-adapter fcp_xml --output-adapter otio_json

uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input roundtrip.otio --output roundtrip.xml \
  --input-adapter otio_json --output-adapter fcp_xml

diff <(xmllint --format original.xml) <(xmllint --format roundtrip.xml)
```

Differences reveal what doesn't survive the round-trip (usually: effects parameters, marker colors, audio pan envelopes).

### Conform from mixed-rate sources

Source has 23.976, 29.97, and 59.94 clips. Decide on one timeline rate and re-time:

```bash
# Convert 29.97 clips to 23.976 (drops every 5th frame — motion stutter; only if unavoidable)
ffmpeg -i clip-2997.mov -r 23.976 -vf "fps=fps=23.976" clip-2398.mov

# Or for interlaced 29.97 sourced from 23.976 telecine, use IVTC
uv run .claude/skills/ffmpeg-ivtc/scripts/ivtc.py apply \
  --input clip-2997i.mov --output clip-2398p.mov --method fieldmatch-decimate
```

### Preserve timecode through conform

```bash
ffmpeg -i source.mov -c copy -timecode $(ffprobe -v error -show_entries format_tags=timecode \
  -of csv=p=0 source.mov) conformed.mov
```

Or use MediaInfo to extract the starting timecode:
```bash
uv run .claude/skills/media-mediainfo/scripts/miinfo.py field \
  --file source.mov --field "TimeCode_FirstFrame"
```

### Transcode an MKV into a deliverable

```bash
# Extract captions
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py extract \
  --input show.mkv --tracks 2:captions.srt

# Split at chapters
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py split \
  --input show.mkv --chapters --output chapter-%02d.mkv
```

### Fragment an MP4 for CMAF

```bash
uv run .claude/skills/media-gpac/scripts/gpacctl.py fragment \
  --input master.mp4 --output master-fragmented.mp4 --fragment-duration 4000
```

---

## Gotchas

- **FCP7 XML ≠ FCPXML.** "FCP7 XML" (FCPXML 1.x in file) is what Premiere + Final Cut 7 exported — legacy schema. "FCPXML" (FCPXML 1.8+) is Final Cut Pro X / 10.x. Different adapters: `fcp_xml` vs `fcpx_xml`. Mixing them loses everything.
- **AAF is a container, not a codec.** AAF may contain MXF-wrapped essence, but AAF ≠ MXF. Media Composer uses AAF with embedded DNxHR MXF (relinked externally, not embedded).
- **Avid MXF is OP-Atom, not OP1a.** Each essence track is its own file. `ffmpeg-mxf-imf` skill defaults to OP1a; for Avid, use `-f mxf_opatom`.
- **OTIO preserves structure, not media.** An OTIO file references media by path. When media moves, you must `remap-media` or every clip will be offline.
- **Effects don't round-trip.** OTIO has a generic effect model; vendor-specific effects (Lumetri Color, Magic Bullet Looks, Avid Effects Engine, Resolve ColorTrace) collapse to "unknown effect". Budget manual recreation on the target NLE.
- **Frame rate determines timecode.** A 23.976p clip with a 29.97DF timecode reel number has ambiguous conform. Always verify with MediaInfo `TimeCode_Source`.
- **Drop-frame vs non-drop-frame timecode.** 29.97DF drops two frames every minute (except every 10th). 23.976ND is non-drop. Conforming across = offset drift. Explicit with `-timecode` flag.
- **Proxies must be frame-accurate to masters.** Generating at wrong frame rate = editorial cuts land at wrong source-timecode in the online. Use `-r` matching the source exactly.
- **Source channel layout variations.** 2-channel stereo vs dual-mono vs 5.1 — NLEs often merge-down on import. Verify with `ffprobe -show_streams`.
- **FCPXML `<media-rep>` uses file:// URLs.** Bare paths won't link. Confirm every `<asset>` src is `file:///` prefixed.
- **Premiere XML 4 ≠ XML 5.** Format migrated between Premiere versions. Specify `--version` explicitly when emitting XML.
- **Resolve DRP is opaque binary.** Round-tripping OTIO → DRP → OTIO loses information. Prefer FCPXML as the Resolve interchange.
- **AAF timecode rate** must match the essence rate. Mismatched = silent clip-offset errors across the timeline.
- **MXF `-timecode` must be 8-digit HH:MM:SS:FF.** `-timecode 01:00:00:00` not `-timecode 3600`.
- **Consolidation can break dependencies.** If the editor relied on a subclip at `/vol/shoots/cam1/A001_C001.mov#0.5s-3.2s`, the conformed file must preserve the in/out or the edit re-slips.
- **Prerendered effects bake in.** An editor may have "rendered" a color-corrected clip in their NLE. That render is the "source" from OTIO's perspective — the original camera original is not referenced.
- **MKVToolNix split modes**: `--split timestamps:...` / `--split parts:...` / `--split chapters` / `--split size:...`. Wrong mode silently produces wrong splits.
- **GPAC's MP4Box exits 0 on some recoverable errors.** Check stderr, not just exit code.
- **ExifTool overwrites in-place by default.** Use `-o output.jpg` to write to a new file, or `-overwrite_original` to confirm the overwrite.

---

## Example — "Premiere → Resolve with conform + proxies"

```bash
#!/usr/bin/env bash
set -e

SRC_XML="premiere-show.xml"
SRC_DIR="/vol/shoots"
CONFORM_DIR="/vol/conform"
PROXY_DIR="/vol/proxies"
OUT_FCPXML="show-resolve.fcpxml"

# 1. Parse the Premiere XML → OTIO
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input "$SRC_XML" --output show.otio \
  --input-adapter fcp_xml --output-adapter otio_json

# 2. List the media manifest
uv run .claude/skills/otio-convert/scripts/otioctl.py list-media \
  --input show.otio --output manifest.json

# 3. Probe every clip; fail loud on rate mismatch
jq -r '.[].source' manifest.json | while read f; do
  RATE=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$f")
  if [[ "$RATE" != "24000/1001" ]]; then
    echo "MISMATCH: $f is $RATE, expected 24000/1001 (23.976)"; exit 1
  fi
done

# 4. Conform: transcode all sources to ProRes 422 HQ
mkdir -p "$CONFORM_DIR"
uv run .claude/skills/media-batch/scripts/batch.py run \
  --manifest manifest.json \
  --output-dir "$CONFORM_DIR" \
  --jobs 4 \
  --command 'ffmpeg -i {in} -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -c:a pcm_s24le {out_stem}.mov'

# 5. Proxies (hw-accelerated)
mkdir -p "$PROXY_DIR"
uv run .claude/skills/media-batch/scripts/batch.py run \
  --manifest manifest.json \
  --output-dir "$PROXY_DIR" \
  --jobs 8 \
  --command 'ffmpeg -i {in} -vf scale=960:540 -c:v h264_videotoolbox -b:v 3M -c:a aac {out_stem}-proxy.mp4'

# 6. Remap paths + link proxies
uv run .claude/skills/otio-convert/scripts/otioctl.py remap-media \
  --input show.otio --output show-conformed.otio \
  --from "$SRC_DIR" --to "$CONFORM_DIR"
uv run .claude/skills/otio-convert/scripts/otioctl.py link-proxies \
  --input show-conformed.otio --output show-final.otio \
  --proxy-dir "$PROXY_DIR" --proxy-suffix -proxy.mp4

# 7. Emit FCPXML for Resolve
uv run .claude/skills/otio-convert/scripts/otioctl.py convert \
  --input show-final.otio --output "$OUT_FCPXML" \
  --input-adapter otio_json --output-adapter fcpx_xml

echo "Done. Import $OUT_FCPXML into DaVinci Resolve."
```

---

## Further reading

- [`vod-post-production.md`](vod-post-production.md) — after conform, the color + finish pass
- [`broadcast-delivery.md`](broadcast-delivery.md) — from finished edit to MXF/IMF
- [`vfx-pipeline.md`](vfx-pipeline.md) — sending plates out to VFX, bringing comps back
- [`analysis-quality.md`](analysis-quality.md) — verifying conformed media didn't drift
