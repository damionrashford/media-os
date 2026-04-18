# Acquisition + Archive Workflow

**What:** Bring media INTO your pipeline from every imaginable source — web video sites, broadcast SDI, DSLR tethered capture, NDI network sources, screen/webcam capture — then archive it with proper metadata, integrity checks, and format normalization.

**Who:** Archivists, news teams, social content teams, journalists, legal evidence collection, documentary producers, anyone who needs to preserve source material durably.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| Web download | `media-ytdlp` | 1,000+ sites (YouTube, Vimeo, Twitch, X, etc.) |
| Screen / webcam / mic | `ffmpeg-capture` | Desktop recording + webcam + mic |
| SDI capture | `decklink-tools`, `decklink-docs` | Blackmagic DeckLink broadcast input |
| DSLR tethered | `gphoto2-tether` | Canon / Nikon / Sony / Fuji remote capture |
| NDI network | `ndi-tools`, `ndi-docs` | Receive NDI streams from network fabric |
| PTZ cameras | `ptz-visca`, `ptz-onvif` | Position + capture PTZ cameras |
| RTSP cameras | `ffmpeg-streaming`, `mediamtx-server` | IP camera ingest |
| Probe | `ffmpeg-probe`, `media-mediainfo` | Validate sources |
| EXIF / IPTC metadata | `media-exiftool` | Photo / video camera metadata preservation |
| ffmpeg metadata | `ffmpeg-metadata` | Chapter / ID3 / container tags |
| Bitstream inspection | `ffmpeg-bitstream` | NAL-level verification of integrity |
| MKV archival | `media-mkvtoolnix` | Future-proof muxing with attachments |
| MP4 archival surgery | `media-gpac` | ISO-BMFF integrity / repair |
| Audio normalization | `media-ffmpeg-normalize` | Optional standardized loudness |
| Format conversion | `ffmpeg-transcode` | Codec normalization |
| Batch | `media-batch` | Parallel ingest |
| Cloud upload | `media-cloud-upload` | S3 / B2 / Archive.org |
| OCIO | `ffmpeg-ocio-colorpro`, `vfx-oiio` | Color-space preservation |
| OCR tagging | `media-ocr-ai`, `media-tag` | Content ID / auto-tag |

---

## The pipeline

### 1. Web-sourced video

```bash
# Download best quality available
uv run .claude/skills/media-ytdlp/scripts/ytd.py download \
  --url "https://www.youtube.com/watch?v=XXX" \
  --output archive/youtube/

# Best video + best audio merged
uv run .claude/skills/media-ytdlp/scripts/ytd.py download \
  --url "$URL" --format "bestvideo+bestaudio/best" --merge-output-format mkv

# With subtitles + thumbnail + description
uv run .claude/skills/media-ytdlp/scripts/ytd.py download \
  --url "$URL" \
  --write-subs --write-thumbnail --write-description \
  --embed-subs --embed-thumbnail

# Entire playlist
uv run .claude/skills/media-ytdlp/scripts/ytd.py download \
  --url "$PLAYLIST_URL" --playlist --output "archive/%(playlist_title)s/%(title)s.%(ext)s"

# Live stream capture
uv run .claude/skills/media-ytdlp/scripts/ytd.py download \
  --url "$LIVE_URL" --live-from-start --output live/%(id)s.%(ext)s
```

### 2. Screen + webcam capture

```bash
# macOS AVFoundation
uv run .claude/skills/ffmpeg-capture/scripts/capture.py screen \
  --platform macos --display 1 --output screen.mov

# Linux X11
uv run .claude/skills/ffmpeg-capture/scripts/capture.py screen \
  --platform linux --display :0 --output screen.mov

# Windows GDI
uv run .claude/skills/ffmpeg-capture/scripts/capture.py screen \
  --platform windows --output screen.mov

# Webcam
uv run .claude/skills/ffmpeg-capture/scripts/capture.py webcam \
  --device 0 --output webcam.mov

# Screen + webcam + mic combined
uv run .claude/skills/ffmpeg-capture/scripts/capture.py combined \
  --screen --webcam --mic --output combined.mov
```

### 3. Broadcast SDI (DeckLink)

```bash
# List devices + supported formats
uv run .claude/skills/decklink-tools/scripts/decklinkctl.py list-devices
uv run .claude/skills/decklink-tools/scripts/decklinkctl.py list-formats \
  --device "DeckLink Duo 2 (1)"

# Capture broadcast-grade ProRes 422 HQ
ffmpeg -f decklink -video_input sdi -audio_input embedded \
  -format_code "Hp50" \
  -i "DeckLink Duo 2 (1)" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -c:a pcm_s24le -ac 2 \
  -timecode 00:00:00:00 \
  archive/cap-$(date +%s).mov

# Capture raw (lossless, massive) for later processing
ffmpeg -f decklink -i "DeckLink Duo 2 (1)" \
  -c:v v210 -c:a pcm_s24le \
  archive/raw-$(date +%s).mov
```

### 4. DSLR tethered

```bash
# Discover cameras
uv run .claude/skills/gphoto2-tether/scripts/gphototether.py detect

# Single shot
uv run .claude/skills/gphoto2-tether/scripts/gphototether.py capture \
  --output archive/photos/

# Intervalometer (timelapse)
uv run .claude/skills/gphoto2-tether/scripts/gphototether.py intervalometer \
  --interval 5 --count 720 --output archive/timelapse/

# Live view → ffmpeg for video recording
uv run .claude/skills/gphoto2-tether/scripts/gphototether.py liveview \
  --output live.mjpeg
# Transcode to proper container
ffmpeg -i live.mjpeg -c:v libx264 -crf 18 archive/live-recording.mp4
```

### 5. NDI network sources

```bash
# Find NDI sources on LAN
uv run .claude/skills/ndi-tools/scripts/nditools.py find --timeout 5

# Record NDI source to disk
uv run .claude/skills/ndi-tools/scripts/nditools.py record \
  --source "PCNAME (OBS Output)" --output archive/ndi-$(date +%s).mov
```

### 6. RTSP / IP cameras

```bash
# Direct capture
ffmpeg -rtsp_transport tcp -i "rtsp://admin:pass@192.168.1.50:554/stream1" \
  -c copy archive/cam-$(date +%Y%m%d).mp4

# Via MediaMTX (if you have multiple cameras / want fanout too)
cat > mediamtx.yml <<'EOF'
paths:
  cam1:
    source: rtsp://admin:pass@192.168.1.50:554/stream1
    runOnReady: ffmpeg -i rtsp://localhost:8554/cam1 -c copy -f segment -segment_time 600 archive/cam1-%Y%m%d-%H%M.mp4
EOF

uv run .claude/skills/mediamtx-server/scripts/mtxctl.py start --config mediamtx.yml
```

### 7. PTZ camera positioned capture

```bash
# Position PTZ to preset first, then capture
uv run .claude/skills/ptz-visca/scripts/viscactl.py preset-recall \
  --host 192.168.1.50 --preset 3

# Then record
ffmpeg -rtsp_transport tcp -i "rtsp://192.168.1.50/stream" \
  -c copy archive/ptz-$(date +%s).mp4
```

### 8. Verify every capture

```bash
# Format check
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full archive/capture.mp4

# MediaInfo deep
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file archive/capture.mp4 --format json > archive/capture.json

# Integrity (full decode without output)
ffmpeg -v error -i archive/capture.mp4 -f null - 2>&1 | tee decode.log

# Checksum
shasum -a 256 archive/capture.mp4 > archive/capture.sha256
```

### 9. Preserve camera / source metadata

```bash
# EXIF from photos + MOV
uv run .claude/skills/media-exiftool/scripts/exif.py read \
  --input archive/photo.jpg --format json > archive/photo.exif.json

# Embed custom archival metadata
uv run .claude/skills/media-exiftool/scripts/exif.py write \
  --input archive/capture.mov \
  --tags "XMP:Creator=Archive Team,XMP:DateCreated=$(date -u +%Y-%m-%dT%H:%M:%SZ),XMP:Source=DeckLink Studio"
```

### 10. Normalize to archival format

MKV is the future-proof archival container. Supports every codec, attachments, chapters, tags, unlimited subtitle/audio tracks.

```bash
# Re-mux (no re-encode) into MKV with archival metadata
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py mux \
  --inputs archive/capture.mov,archive/captions.srt \
  --output archive/archival.mkv \
  --title "Broadcast Capture 2026-04-17" \
  --track-name "0:Main SDI Feed" \
  --track-name "1:English CC" \
  --language "0:eng" \
  --attach archive/capture.exif.json,archive/capture.sha256
```

Or for MP4 preservation:
```bash
uv run .claude/skills/media-gpac/scripts/gpacctl.py fix-integrity \
  --input archive/capture.mp4 --output archive/capture-fixed.mp4
```

### 11. Format + codec normalization (optional)

For long-term archive, many institutions normalize to a single codec. Common choices:

- **FFV1 in MKV** — lossless, widely supported in archival workflows (LOC-approved)
- **JPEG 2000 in MXF** — SMPTE standard (IMF), broadcast-grade
- **ProRes 422 HQ in MOV** — de facto industry standard
- **DNxHR HQ in MXF** — Avid-centric institutions

```bash
# FFV1 lossless
ffmpeg -i archive/capture.mov \
  -c:v ffv1 -level 3 -coder 1 -context 1 -g 1 -slicecrc 1 -slices 24 \
  -c:a flac -compression_level 12 \
  archive/ffv1.mkv

# JPEG 2000 in MXF
ffmpeg -i archive/capture.mov \
  -c:v jpeg2000 -pred 1 -pix_fmt yuv422p10le \
  -c:a pcm_s24le -f mxf \
  archive/archival.mxf
```

### 12. Batch ingest + archive

```bash
#!/usr/bin/env bash
# batch-archive.sh — called by batch runner

INPUT=$1
BASENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
ARCHIVE_DIR=$2

# 1. Verify integrity
ffmpeg -v error -i "$INPUT" -f null - 2>&1 | grep -q "Error" && { echo "CORRUPT: $INPUT"; exit 1; }

# 2. Extract metadata
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file "$INPUT" --format json > "$ARCHIVE_DIR/${BASENAME}.mediainfo.json"

uv run .claude/skills/media-exiftool/scripts/exif.py read \
  --input "$INPUT" --format json > "$ARCHIVE_DIR/${BASENAME}.exif.json"

# 3. Checksum
shasum -a 256 "$INPUT" > "$ARCHIVE_DIR/${BASENAME}.sha256"

# 4. Normalize to MKV
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py mux \
  --inputs "$INPUT" --output "$ARCHIVE_DIR/${BASENAME}.mkv" \
  --title "Archival: $BASENAME" \
  --attach "$ARCHIVE_DIR/${BASENAME}.mediainfo.json,$ARCHIVE_DIR/${BASENAME}.exif.json,$ARCHIVE_DIR/${BASENAME}.sha256"

# 5. Move original to cold storage
mv "$INPUT" "$ARCHIVE_DIR/originals/"

echo "Archived: $ARCHIVE_DIR/${BASENAME}.mkv"
```

Run at scale:
```bash
uv run .claude/skills/media-batch/scripts/batch.py run \
  --input-glob 'incoming/*.mov' \
  --output-dir archive/ \
  --jobs 4 \
  --command 'bash batch-archive.sh {in} archive/'
```

### 13. Cloud archive

```bash
# AWS Glacier / S3 Deep Archive (cheapest long-term)
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --provider aws \
  --bucket my-archive \
  --storage-class GLACIER_DEEP \
  --prefix "$(date +%Y/%m)/" \
  --file archive/archival.mkv

# Backblaze B2
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --provider backblaze --bucket archive --file archive/archival.mkv

# Archive.org (for public-domain content)
# Uses IA's s3-compatible API
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --provider archive-org --bucket my-archive-item --file archive/archival.mkv
```

---

## Variants

### Continuous camera capture with segmentation

```bash
# 1-hour segments, auto-delete after 30 days
ffmpeg -rtsp_transport tcp -i "rtsp://cam/stream" \
  -c copy -f segment -segment_time 3600 \
  -strftime 1 \
  archive/cam-%Y%m%d-%H.mp4 &

# Cleanup job (cron)
find archive/ -name "cam-*.mp4" -mtime +30 -delete
```

### Automated content tagging

```bash
# Extract keyframes
ffmpeg -i archive/capture.mp4 -vf "select='eq(pict_type,I)'" -vsync vfr keyframes/%04d.jpg

# AI tag each
for kf in keyframes/*.jpg; do
  uv run .claude/skills/media-tag/scripts/tagctl.py blip2 \
    --input "$kf" --output "tags/$(basename $kf .jpg).txt"
done

# Consolidate
cat tags/*.txt > archive/$(basename $INPUT .mp4).tags.txt
```

### OCR verification of archival footage

```bash
# Extract every 5 seconds, OCR each frame
ffmpeg -i archive/capture.mp4 -vf "fps=0.2" frames/%04d.jpg
uv run .claude/skills/media-ocr-ai/scripts/ocrctl.py paddle \
  --input frames/ --output ocr.json --batch
```

### Color-space-aware archival

Preserve the original color space (don't convert to sRGB automatically):

```bash
# Re-mux preserving color tags
ffmpeg -i source.mov \
  -c:v copy -c:a copy \
  -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc \
  archival.mov
```

Or use OIIO for EXR sequences:
```bash
uv run .claude/skills/vfx-oiio/scripts/oiiorun.py convert \
  --input "%04d.exr" --output archive.exr \
  --compression zip --colorspace-in "ACES - ACEScg"
```

### Incremental archive with rsync + verification

```bash
# One-time sync
rsync -avz --checksum archive/ remote-backup:/archive/

# Verify against server-side checksums
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py verify \
  --input archive/archival.mkv
```

---

## Gotchas

### Source integrity

- **`ffmpeg -v error -f null -` is the cheap integrity check.** Non-zero exit + stderr containing "Error" = corrupt source. Always run on ingest.
- **shasum computed AT capture time** is the only reliable proof of integrity later. Checksums on already-corrupted files are meaningless.
- **YouTube/Vimeo re-encode on upload** — even `--format best` is not "original quality."
- **yt-dlp output can contain non-ASCII characters**. Use `-o "%(id)s.%(ext)s"` for filesystem-safe names.
- **Live streams with `--live-from-start`** need the source to support it; most HLS streams have a windowed DVR (20-30 min).

### Capture formats

- **SDI via DeckLink: `Hp50` = 1080p50, `Hi59` = 1080i59.94, `2k24` = 2K 24p.** List formats per device.
- **DeckLink capture stalls on wrong format.** Starting capture at `Hp50` when signal is `Hp30` = silent black capture. Always verify with `-list_formats 1` first.
- **10-bit DeckLink requires `-pix_fmt yuv422p10le`** and a 10-bit-capable device (Duo 2, Quad HDMI, Studio 4K).
- **gphoto2 locks USB** — only one app can claim the camera at a time. Close Canon EOS Utility / Lightroom tether before running.
- **gphoto2 live view framerate is camera-dependent** (typically 24-30 fps on Canon, 30 fps on Nikon). Can't push higher.
- **NDI runtime is platform-specific and NOT bundled.** Install NewTek/Vizrt NDI Tools first.

### Metadata preservation

- **`-c copy` preserves codec-level metadata** (HDR, captions, SEI) but container-level metadata (chapter markers, tags) may be lost when changing container.
- **MP4 `udta` atom metadata varies by writer.** Apple, Sony, and FFmpeg emit different structures. ExifTool is the most robust reader.
- **MKV supports arbitrary global tags, per-track tags, chapter tags, attachment tags** — use `mkvpropedit` for in-place edits. `ffmpeg` only sets some of these.
- **ExifTool `-overwrite_original` DELETES the .jpg_original backup.** Keep backups until you've verified new metadata.
- **ExifTool UTF-8 strings need `-charset filename=UTF8`** or non-ASCII paths fail silently.
- **Timecode in MOV is in the `tmcd` track.** `ffmpeg` preserves it with `-map 0` but can lose it if stream selection narrows.

### Archival formats

- **FFV1 is lossless but NOT supported by most consumer players.** Great for archive + LOC; bad for distribution.
- **MKV with large attachments (GB-scale) makes re-muxing slow.** Separate sidecars for huge manifests.
- **MP4 fragmented vs non-fragmented.** `media-gpac` `fragment` makes content streamable but some legacy tools can't parse. Archive both forms.
- **JPEG 2000 encoding is CPU-intensive.** Budget 1-2 fps per core for 4K J2K lossless.
- **Variable-bitrate archival at high quality hides the true bit-count**. Check actual size: 60-min UHD FFV1 is 500GB+. Plan storage accordingly.

### Cloud archive

- **AWS Glacier Deep Archive**: $1/TB/month, 12-hour retrieval. Cheapest for truly cold data.
- **Backblaze B2**: $6/TB/month, instant retrieval. Good for "warm" archive.
- **Archive.org (internetarchive.org)** is FREE but content becomes publicly accessible (ok for PD works, not for private archives).
- **`--storage-class DEEP_ARCHIVE` minimum retention is 180 days.** Delete before that = full charge.
- **Multi-region replication** costs 2x storage; worth it for irreplaceable originals.

---

## Example — "Ingest SDI broadcast capture, archive with MKV + cloud"

```bash
#!/usr/bin/env bash
set -e

CAPTURE_DIR="incoming"
ARCHIVE_DIR="archive"
CLOUD_BUCKET="my-broadcast-archive"
DEVICE="DeckLink Studio 4K (1)"
FORMAT_CODE="Hp50"
DURATION=3600  # 1 hour

mkdir -p "$CAPTURE_DIR" "$ARCHIVE_DIR/originals" "$ARCHIVE_DIR/sidecars"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BASE="broadcast-$TIMESTAMP"

# 1. List formats to verify
uv run .claude/skills/decklink-tools/scripts/decklinkctl.py list-formats --device "$DEVICE"

# 2. Capture (broadcast-grade ProRes 422 HQ)
echo "Starting capture..."
ffmpeg -f decklink -video_input sdi -audio_input embedded \
  -format_code "$FORMAT_CODE" \
  -i "$DEVICE" \
  -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -c:a pcm_s24le -ac 2 \
  -timecode 01:00:00:00 \
  -t "$DURATION" \
  "$CAPTURE_DIR/$BASE.mov"

# 3. Integrity check
echo "Verifying..."
ffmpeg -v error -i "$CAPTURE_DIR/$BASE.mov" -f null - 2>&1 | tee "$ARCHIVE_DIR/sidecars/$BASE.decode.log"

# 4. Checksum
shasum -a 256 "$CAPTURE_DIR/$BASE.mov" > "$ARCHIVE_DIR/sidecars/$BASE.sha256"

# 5. Probe + MediaInfo
uv run .claude/skills/ffmpeg-probe/scripts/probe.py full "$CAPTURE_DIR/$BASE.mov" \
  > "$ARCHIVE_DIR/sidecars/$BASE.probe.json"
uv run .claude/skills/media-mediainfo/scripts/miinfo.py report \
  --file "$CAPTURE_DIR/$BASE.mov" --format json \
  > "$ARCHIVE_DIR/sidecars/$BASE.mediainfo.json"

# 6. Normalize to MKV with attachments
uv run .claude/skills/media-mkvtoolnix/scripts/mkvctl.py mux \
  --inputs "$CAPTURE_DIR/$BASE.mov" \
  --output "$ARCHIVE_DIR/$BASE.mkv" \
  --title "Broadcast Archive: $TIMESTAMP" \
  --track-name "0:SDI Video" --track-name "1:Embedded Audio" \
  --language "0:eng" --language "1:eng" \
  --attach "$ARCHIVE_DIR/sidecars/$BASE.probe.json,$ARCHIVE_DIR/sidecars/$BASE.mediainfo.json,$ARCHIVE_DIR/sidecars/$BASE.sha256"

# 7. Move original to cold storage
mv "$CAPTURE_DIR/$BASE.mov" "$ARCHIVE_DIR/originals/"

# 8. Cloud upload (Glacier Deep Archive — cheapest long-term)
uv run .claude/skills/media-cloud-upload/scripts/cloudup.py s3 \
  --provider aws \
  --bucket "$CLOUD_BUCKET" \
  --storage-class DEEP_ARCHIVE \
  --prefix "$(date +%Y/%m)/" \
  --file "$ARCHIVE_DIR/$BASE.mkv"

echo "Archived: $ARCHIVE_DIR/$BASE.mkv (cloud: $CLOUD_BUCKET/$(date +%Y/%m)/$BASE.mkv)"
```

---

## Further reading

- [`broadcast-delivery.md`](broadcast-delivery.md) — going OUT as the reverse of acquisition
- [`analysis-quality.md`](analysis-quality.md) — QC on incoming material
- [`editorial-interchange.md`](editorial-interchange.md) — after ingest, into the NLE
- [`live-production.md`](live-production.md) — real-time capture from OBS + NDI + PTZ
