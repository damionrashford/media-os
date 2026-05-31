# Mode: acquisition-archive

**Subagent**: `probe`
**Trigger phrases**: "ingest these", "probe this folder", "archive", "preserve metadata", "verify hash", "checksum tree", "batch probe", "tether DSLR", "gphoto2", "ingest from card", "camera ingest"
**Output**: `${MEDIA_WORK_DIR}/modes/acquisition-archive/{date}_{slug}/`

## Inputs

- **Required**:
  - `task` — `probe-batch`, `ingest-card`, `tether-capture`, `archive-verify`.
  - `source` — directory path (for `probe-batch` / `archive-verify`) OR card mount point (for `ingest-card`) OR camera device (for `tether-capture`).
- **Optional**:
  - `destination` — archive root (default: `${MEDIA_WORK_DIR}/archive/`).
  - `hash_algo` — `xxh3` (default, fast) / `sha256` (default for long-term archive).
  - `skip_existing` — boolean (default: `true`).
  - `tether_settings` — for `tether-capture`: ISO, aperture, shutter, format (RAW+JPEG).

## Steps

1. Read tool skills: `ffmpeg-probe`, `media-mediainfo`, `media-exiftool`, `gphoto2-tether` (for tether), `decklink-tools` (for SDI capture), `media-batch` (for parallel probe).
2. Branch by `task`:
   - **`probe-batch`**: For each media file in `source` (recursive), run `moprobe --json <file>` and `exiftool -j <file>`. Store both in a flat NDJSON at `<destination>/manifest.ndjson` keyed by path. Compute hash per `hash_algo`.
   - **`ingest-card`**: Validate card mount point. Walk DCIM/MISC/CLIP directories per common camera layouts (Sony XAVC, Canon CR3, RED R3D, ARRI MXF, GoPro MP4). Copy with verify-after-copy (read back, hash-check). Append to manifest.
   - **`tether-capture`**: For DSLR (Canon EOS / Nikon Z / Sony α): use `gphoto2 --capture-image-and-download --config iso=<n>` etc. For broadcast SDI: use `BMDStreamingServer` with DeckLink.
   - **`archive-verify`**: Walk archive root; for each file in `manifest.ndjson`, recompute hash and compare. Report mismatches as corruption candidates.
3. For media files (video / image / audio): always include in manifest:
   - File path (relative to archive root).
   - File size + mtime.
   - Hash (`xxh3` for fast, `sha256` for long-term).
   - Full `ffprobe -show_streams -show_format` JSON.
   - Full `exiftool -j` JSON (covers EXIF, IPTC, XMP, MakerNotes).
   - For video: SMPTE timecode if present, GOP count, color metadata.
4. **STOP** for `ingest-card` if card removed mid-copy (file not readable) — never silently truncate.
5. Run `media-batch` for parallel probe if file count > 100 (use GNU parallel; `parallel -j 4 moprobe ::: *.mxf`).
6. For `archive-verify`: surface ANY hash mismatch as a critical finding — could be silent disk corruption (bit rot).
7. Write `summary.md` with file count, total bytes, hash algo, manifest path, any failures or anomalies.

## Output schema

```markdown
# Acquisition + archive — {slug} — {date}

## Task
**{probe-batch / ingest-card / tether-capture / archive-verify}**

## Source
- **Path / device**: {source}
- **File count**: {N}
- **Total size**: {bytes / GB}

## Destination
- **Archive root**: {destination}
- **Manifest**: {destination}/manifest.ndjson

## Processing
- **Hash algorithm**: {xxh3 / sha256}
- **Skip existing**: {true / false}
- **Parallel jobs**: {N}
- **Started / completed**: {timestamps}
- **Duration**: {hh:mm:ss}

## Results
| Status | Count | Notes |
|---|---|---|
| Ingested | {N} | Fresh copies, hash verified |
| Skipped | {N} | Existing with matching hash |
| Updated | {N} | Existing with different hash — kept old, copied new with `.dup` suffix |
| Failed | {N} | See `failures.log` |

## Manifest sample
```ndjson
{"path":"...","size":...,"hash":"...","mtime":"...","ffprobe":{...},"exiftool":{...}}
```

## Anomalies
- {file path} — {what was wrong: hash mismatch, missing timecode, EXIF date in future, ...}

## Archive integrity (task=archive-verify)
- **Files checked**: {N}
- **Hash mismatches**: {N} — {list of paths}
- **Verdict**: {clean / N corruption candidates / archive root unreachable}
```

## Quality bar

- Every file has hash in manifest — no entries with `null` or missing hash.
- For `ingest-card`: copy is verify-after-copy (read back + hash compare); files that fail verify are surfaced, not silently kept.
- For `archive-verify`: ANY hash mismatch surfaces as a critical finding.
- For `tether-capture`: gphoto2 errors (camera lost, card full, write error) surface immediately, not buried in a log.
- Manifest is line-delimited JSON (one record per line) for streaming-friendly downstream tools.
- Re-running `probe-batch` with `skip_existing=true` is idempotent — only new/changed files are re-probed.

## Playbook reference (folded from workflow-acquisition-archive)

# Workflow — Acquisition + Archive

**What:** Acquire from any source on planet earth, verify the bytes, preserve the metadata, normalize to an archival container, push to cold storage.

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
