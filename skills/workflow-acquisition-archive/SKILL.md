---
name: workflow-acquisition-archive
description: Ingest from every source — web (yt-dlp), screen / webcam / mic capture, SDI (DeckLink), DSLR tether (gphoto2), NDI network sources, RTSP / IP cameras via MediaMTX, PTZ — then verify integrity (SHA-256 + full-decode pass), preserve metadata (EXIF / XMP / IPTC), normalize to MKV or FFV1 / J2K / ProRes archival containers, and push to cold-storage cloud (Glacier / B2 / Archive.org). Use when the user says "download YouTube playlist", "capture SDI for 24 hours", "archive IP cameras", "preserve VHS rips", "tether DSLR timelapse", "cold-storage upload", or any ingest-to-archive workflow.
argument-hint: [source]
---

# Workflow — Acquisition + Archive

**What:** Acquire from any source on planet earth, verify the bytes, preserve the metadata, normalize to an archival container, push to cold storage.

## Skills used

`media-ytdlp`, `ffmpeg-capture`, `decklink-tools`, `decklink-docs`, `gphoto2-tether`, `ndi-tools`, `ndi-docs`, `ffmpeg-streaming`, `mediamtx-server`, `ptz-visca`, `ptz-onvif`, `ffmpeg-probe`, `media-mediainfo`, `media-exiftool`, `ffmpeg-metadata`, `ffmpeg-bitstream`, `media-mkvtoolnix`, `media-gpac`, `media-ffmpeg-normalize`, `ffmpeg-transcode`, `media-batch`, `media-cloud-upload`, `ffmpeg-ocio-colorpro`, `vfx-oiio`, `media-ocr-ai`, `media-tag`.

## Pipeline

### Step 1 — Acquire

Pick per source:

| Source | Skill | Method |
|---|---|---|
| Web video (1000+ sites) | `media-ytdlp` | `bestvideo+bestaudio` merged, subs + thumbnail + description |
| Screen + webcam + mic | `ffmpeg-capture` | AVFoundation (macOS) / X11 (Linux) / GDI (Windows) |
| Broadcast SDI | `decklink-tools` | ProRes 422 HQ 10-bit + PCM 24-bit, or `v210` raw lossless |
| DSLR tethered | `gphoto2-tether` | single shot, intervalometer timelapse, live view MJPEG |
| NDI network | `ndi-tools` | `nditools.py find`, record to disk |
| RTSP / IP camera | `ffmpeg-streaming` or `mediamtx-server` | direct capture TCP, or multi-camera fanout with segmented MP4 |
| PTZ-positioned | `ptz-visca` / `ptz-onvif` | preset-recall, then any of the above |

### Step 2 — Verify integrity

- **Full-decode pass** — `ffmpeg -v error -i <file> -f null -` (non-zero exit = corrupt).
- **Deep probe** — `ffmpeg-probe` + `media-mediainfo`.
- **SHA-256 checksum** — store alongside the file.

### Step 3 — Preserve metadata

`media-exiftool` — EXIF from photos, MOV `udta`, XMP sidecars for custom archival fields. `ffmpeg-metadata` for MKV global + chapter tags.

### Step 4 — Normalize to archival container

MKV is the default — supports every codec, attachments, chapters, unlimited tracks. Attach the probe + mediainfo + checksum as sidecar files inside the MKV if using `media-mkvtoolnix`.

### Step 5 — Optional codec normalization

| Archival target | Container | Codec |
|---|---|---|
| Deep archive lossless | MKV | FFV1 |
| SMPTE-compliant | MXF | JPEG 2000 |
| Apple-friendly | MOV | ProRes 422 HQ |
| Cross-platform | MXF | DNxHR HQ |

### Step 6 — Batch

`media-batch` (GNU parallel) fans out ingest + integrity + metadata + normalize across N sources.

### Step 7 — Cold storage

`media-cloud-upload`:

| Tier | Cost | Retrieval |
|---|---|---|
| AWS Glacier Deep Archive | ~$1/TB/mo | 12 h |
| Backblaze B2 | ~$6/TB/mo | instant (warm) |
| Archive.org | free (PUBLIC) | instant |

## Variants

- **Continuous SDI with segmentation** — 1-hour segments via `segment` muxer, auto-delete after 30 days.
- **Automated content tagging** — extract keyframes, `media-tag` CLIP/SigLIP per frame, consolidate tags in sidecar JSON.
- **OCR verification** — 0.2 fps extract, `media-ocr-ai` per frame, consolidate burn-in text.
- **Color-space-aware archival** — preserve original color tags; DO NOT auto-convert to sRGB.
- **Incremental sync** — rsync + post-sync checksum verification.

## Gotchas

- **`ffmpeg -v error -i <file> -f null -` is cheap integrity.** Non-zero exit OR stderr with "Error" = corrupt.
- **Checksums are only meaningful AT CAPTURE TIME.** Checksumming an already-corrupt file is useless.
- **YouTube / Vimeo re-encode on upload.** `--format best` is NOT original quality. For true originals, you need the uploader's source.
- **yt-dlp filenames can contain non-ASCII characters.** Use `-o "%(id)s.%(ext)s"` for filesystem safety.
- **`--live-from-start` needs source support.** Most HLS windows are 20–30 min DVR — older content gone.
- **DeckLink format codes are 4-letter** (`Hp50`, `Hi59`, `2k24`). Wrong code = silent black capture. Verify with `-list_formats 1`.
- **10-bit DeckLink capture requires `-pix_fmt yuv422p10le`** AND a 10-bit-capable device.
- **gphoto2 locks USB.** One app claims the camera. Close EOS Utility / Lightroom / Capture One first.
- **gphoto2 live-view framerate is camera-dependent** (Canon ~24–30 fps, Nikon ~30 fps).
- **NDI runtime (NewTek/Vizrt) is a separate install** from the SDK.
- **`-c copy` preserves codec metadata** (HDR SEI, captions) but CONTAINER metadata (chapters, tags) may be lost when changing container.
- **MP4 `udta` varies by writer** (Apple / Sony / FFmpeg all different). ExifTool is the most robust reader.
- **MKV global / per-track / chapter / attachment tags are all separate.** Use `mkvpropedit` for in-place edits — ffmpeg is limited.
- **ExifTool `-overwrite_original` deletes the backup.** Keep backups until verified.
- **ExifTool needs `-charset filename=UTF8`** for non-ASCII paths. Fails silently otherwise.
- **MOV timecode lives in a `tmcd` track.** `ffmpeg -map 0` preserves; narrow stream selection drops it.
- **FFV1 lossless is NOT supported by consumer players** (great for LOC-grade archive, bad for distribution).
- **MKV large attachments (GB-scale) slow re-muxing.** For huge manifests, use separate sidecar files.
- **Fragmented MP4 (via GPAC `MP4Box -frag`) is streamable** but legacy tools may reject. Archive BOTH.
- **J2K encoding is CPU-heavy** (~1–2 fps/core at 4K).
- **Variable-bitrate archival is storage-expensive.** 60-min UHD FFV1 ≈ 500+ GB. Plan accordingly.
- **AWS Deep Archive min retention 180 days.** Delete before → full charge.
- **Archive.org is PUBLIC.** Good for public domain; do NOT upload private material.
- **Multi-region replication doubles storage cost** — worth it for irreplaceable originals.

## Example — Archive 24-hour SDI broadcast feed

`decklink-tools` capture → `ffmpeg` segmenter → 1-hour MP4 segments → per-segment: full-decode check + SHA-256 + MediaInfo JSON sidecar → batch-upload to Glacier Deep Archive via `media-cloud-upload` with lifecycle rule for 30-day local purge after upload confirmation.

## Related

- `workflow-broadcast-delivery` — the next step if the archive is to be mastered.
- `workflow-live-production` — the live feed that typically drives an acquisition pipeline.
- `workflow-analysis-quality` — integrity / spec verification.
