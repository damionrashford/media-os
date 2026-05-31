# Mode: vod-post-production

**Subagent**: `encoder`
**Trigger phrases**: "encode VOD", "transcode for VOD", "VMAF gate encode", "x264 master", "x265 master", "two-pass encode", "encode for archive", "master encode"
**Output**: `${MEDIA_WORK_DIR}/modes/vod-post-production/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input master file.
  - `target` — target codec + container: `h264-mp4`, `h265-mp4`, `h265-mkv`, `av1-mkv`, `prores-422-hq`, `prores-4444`, `dnxhr-hqx`.
- **Optional**:
  - `bitrate` — target bitrate (kbps). If omitted, use CRF.
  - `crf` — quality-based encode (default: 18 for H.264, 20 for HEVC). Mutually exclusive with `bitrate`.
  - `preset` — `ultrafast` ... `placebo` (default: `medium` per `DEFAULT_ENCODE_PRESET` userConfig).
  - `vmaf_min` — quality gate (default from `DEFAULT_VMAF_TARGET`, fallback 93).
  - `hwaccel` — `none` (default), `videotoolbox` (macOS), `nvenc` (NVIDIA), `qsv` (Intel), `vaapi` (Linux).
  - `passes` — `1` (default), `2` (two-pass for bitrate-targeted encodes).

## Steps

1. Read tool skills: `ffmpeg-encode`, `ffmpeg-analyze`, `ffmpeg-encode`, `ffmpeg-encode`.
2. `moprobe --color --json <source>` to capture resolution, fps, color, bit depth, audio, duration.
3. **STOP** if `bitrate` AND `crf` both provided — they're mutually exclusive. Surface to operator.
4. **STOP** if HDR target requested without `hdr-mastering` mode first — VOD post-prod doesn't author HDR metadata; it preserves what's there or strips it.
5. Pick codec + flags per `target`:
   - **`h264-mp4`** → `libx264 -profile:v high -level 4.2 -pix_fmt yuv420p -movflags +faststart`.
   - **`h265-mp4`** → `libx265 -profile:v main10 -pix_fmt yuv420p10le -tag:v hvc1 -movflags +faststart` (hvc1 for Apple compat).
   - **`h265-mkv`** → `libx265 -profile:v main10 -pix_fmt yuv420p10le`.
   - **`av1-mkv`** → `libaom-av1 -row-mt 1 -cpu-used 4 -pix_fmt yuv420p10le`.
   - **`prores-422-hq`** → `prores_ks -profile:v 3 -vendor apl0 -pix_fmt yuv422p10le`.
   - **`prores-4444`** → `prores_ks -profile:v 4 -vendor apl0 -pix_fmt yuva444p10le`.
   - **`dnxhr-hqx`** → `dnxhd -profile:v dnxhr_hqx -pix_fmt yuv422p10le`.
6. Add `-c:a copy` if audio doesn't need re-encode; otherwise `-c:a aac -b:a 192k` (or `-c:a libopus -b:a 128k` for MKV).
7. **`mosafe`-wrap** the ffmpeg command. Reject if lint fails (especially missing `+faststart`, missing `hvc1` tag, conflicting CRF + bitrate).
8. If `hwaccel != none`: switch codec to hardware variant (`h264_videotoolbox`, `hevc_nvenc`, etc.) and note in summary that quality will trail software encode at same bitrate.
9. If `passes=2`: first-pass `-pass 1 -f null /dev/null`, second-pass `-pass 2 <output>`. Required for bitrate-targeted broadcast-spec encodes.
10. Encode.
11. Run `moqc --ref <source> --out <output> --vmaf-min <vmaf_min> --format json`.
12. If VMAF fails: bump preset one slower (`medium` → `slow`) and re-encode. Surface to operator if it fails again — don't infinitely retry.
13. Run `mediainfo --Output=JSON <output>` and compare to expected codec/profile/level.
14. Write `summary.md`.

## Output schema

```markdown
# VOD post-production — {slug} — {date}

## Source
- **Resolution / fps / duration**: {WxH} / {fps} / {hh:mm:ss}
- **Codec in**: {codec, profile, bit depth}
- **Color**: {primaries / transfer / matrix} {HDR if applicable}

## Target
- **Codec / container**: {h264-mp4 / h265-mp4 / av1-mkv / prores-422-hq / ...}
- **Rate control**: CRF {N} OR bitrate {kbps} {1-pass / 2-pass}
- **Preset**: {ultrafast ... placebo}
- **HW accel**: {none / videotoolbox / nvenc / qsv / vaapi}

## Quality gate
- **VMAF**: {N} (min {vmaf_min}) — {pass / fail / re-encoded at slower preset}
- **SSIM**: {N}
- **PSNR**: {N}

## Output
- **File**: {path}
- **Size**: {bytes}
- **Bitrate actual**: {kbps}
- **Reduction vs source**: {pct}%

## mediainfo verification
- **Codec ID**: {expected vs actual}
- **Profile / level**: {expected vs actual}
- **Pixel format**: {expected vs actual}
- **`hvc1` vs `hev1` tag** (HEVC only): {expected vs actual}
```

## Quality bar

- `mosafe` passed pre-encode.
- VMAF ≥ `vmaf_min` (or operator-acknowledged failure).
- For MP4 output: `-movflags +faststart` present.
- For HEVC MP4: `-tag:v hvc1` (not `hev1`) for Apple compatibility.
- For 10-bit pix_fmt: explicit (`yuv420p10le` / `yuv422p10le` / `yuv444p10le`) — never let codec default to 8-bit silently.
- 2-pass used when `bitrate` specified and target is bitrate-spec broadcast/CDN delivery.
- `mediainfo` verification passes (codec ID, profile, level, pix_fmt all match expected).

## Playbook reference (folded from workflow-vod-post-production)

**What:** Finish a video between editorial and distribution. Transcode, color, retime, caption, audio, package. Not live. Not broadcast master. Not AI-restoration. Just classic VOD finishing.

### Pipeline

#### Step 1 — Transcode to mezzanine

ProRes 422 HQ (Apple) or DNxHR HQ (Avid / cross-platform). Never cut from camera original.

#### Step 2 — Proxies for offline edit

Hardware-accelerated H.264 (NVENC / QSV / VideoToolbox). Real-time or faster on modern chips.

#### Step 3 — Cut / trim / concat

`ffmpeg-edit`:
- `trim --mode stream-copy` — FAST, keyframe-snapped.
- `trim --mode reencode` — frame-accurate.
- `concat --mode copy` — same codec.
- `concat --mode filter` — different codecs.

#### Step 4 — Color grade

`ffmpeg-color` for `.cube`/`.3dl`/Hald CLUT. `ffmpeg-color` for OCIO/ACES. Manual `eq`, `curves`, `colorbalance` filters via `ffmpeg-filter`.

#### Step 5 — Stabilize

`ffmpeg-restore` two-pass (`vidstabdetect` → `vidstabtransform`) for best quality; `deshake` single-pass for speed.

#### Step 6 — Denoise

`ffmpeg-restore`: `nlmeans` for film grain, `bm3d` heavier preserves detail, `hqdn3d` general fast.

#### Step 7 — Scale / crop / reframe

`scale`, `cropdetect` auto letterbox, `16:9 → 9:16` vertical via `crop`+`scale`.

#### Step 8 — Speed / time manipulation

`ffmpeg-edit`: `setpts`, `atempo`, `minterpolate` for smooth slow-mo, freeze frame, reverse.

#### Step 9 — Chromakey / greenscreen

`ffmpeg-composite`: `chromakey` + `despill` filters.

#### Step 10 — Text / lower thirds

`drawtext` or ASS sidecar subtitles.

#### Step 11 — Subtitles

`ffmpeg-subtitle`: soft-mux, burn-in, extract, format convert.

#### Step 12 — Audio finishing

EQ + compression via `ffmpeg-filter`, loudness via `media-audio-cli`.

#### Step 13 — Thumbnails / sprite sheets

`ffmpeg-edit`: extract every N seconds, sprite sheet for scrubber UI, animated GIF preview.

#### Step 14 — Chapters + metadata

`ffmpeg-analyze`: chapter markers + cover art.

#### Step 15 — Final delivery

HandBrake preset for prosumer; ffmpeg direct for fine-grained; AV1 for archival/bandwidth.

#### Step 16 — QC

the `analysis-quality` mode — VMAF vs reference, spec assertions.

#### Step 17 — Upload

`media-cloud-upload` (YouTube, Vimeo, S3, etc.).

### Variants

- **Batch** — `media-batch` runs `finish-xxx.sh` across N files in parallel.
- **Programmatic (MoviePy)** — when ffmpeg filtergraph gets unwieldy, drop to Python.
- **Vertical social** — face-tracking auto-crop 16:9 → 9:16.
- **360° VR edit** — equirect → stereographic "little planet" via `ffmpeg-composite`.

### Gotchas

- **`-movflags +faststart` is a SECOND pass.** Encoder runs; ffmpeg rewinds; rewrites moov atom to front. Adds time — necessary for progressive MP4.
- **`concat` demuxer requires identical codecs.** Different rates / codecs = silent failure. Use `concat` FILTER instead.
- **Slow-motion `setpts=N*PTS` needs matching `-r` input.** Without, frame drop/duplicate is odd.
- **`atempo` range is 0.5–2.0 per filter.** Chain for extreme tempo shifts.
- **`yadif` modes:** 0=single-rate, 1=double-rate, 2=spatial-only, 3=double-rate spatial.
- **`scale=-2:1080`** keeps aspect ratio with even width (required for yuv420p).
- **`libx264 -pix_fmt yuv420p` required for broadcast playback.** Many decoders don't handle `yuv422p` / `yuv444p`.
- **NVENC preset is `p1`–`p7`** (higher = better quality, slower). NOT `ultrafast`–`placebo`.
- **`h264_videotoolbox` is quality-preset only.** `-b:v` and `-q:v` are hints; quality varies.
- **`libsvtav1 -preset` is 0–13** (0 slowest). NOT 1–10 like libaom-av1.
- **`libvpx-vp9` needs `-row-mt 1 -threads 4`** to multi-thread. Single-threaded default.
- **`-shortest` stops at shortest input.** Without it, looping `-loop 1` inputs = infinite.
- **`drawtext` needs font FILE PATH, not font name.** macOS `/System/Library/Fonts/Helvetica.ttc`.
- **ASS subtitles use `&HAABBGGRR`** (ARGB). AA=alpha, BGR byte order. Wrong byte order = wrong color.
- **`chromakey` works in RGB.** YUV sources auto-convert, but precise keying wants `format=yuva420p` first.
- **`vidstab` requires `--enable-libvidstab`** ffmpeg build. Some Ubuntu stock builds lack it.
- **`atempo` preserves pitch; `asetrate` shifts pitch.** Combine carefully.
- **`-ss` before `-i`** = fast seek, non-frame-accurate. **`-ss` after `-i`** = frame-accurate, sequential. Use after for accuracy.
- **Two-pass loudnorm via `media-audio-cli`.** Single-pass applies runtime auto limits.
- **`-map 0:v:0 -map 0:a:0`** selects first video+audio. Default `-map 0` grabs ALL streams.
- **HandBrake presets are opinionated.** "Fast 1080p30" = H.264 CRF 22 + AAC 160. Sometimes wrong for source.
- **Alpha preservation needs `-pix_fmt yuva420p`** (or yuva444p) AND `-c:v qtrle` or `-c:v prores_ks -profile:v 4` (ProRes 4444). H.264 has NO alpha.

### Example — 4K camera raw → 1080p YouTube master

Probe → ProRes 422 HQ mezzanine → cut + concat → LUT color grade → `hqdn3d` → `scale=-2:1080` → `loudnorm` two-pass → `drawtext` lower third → `mov_text` subtitles → H.264 CRF 18 `yuv420p` `-movflags +faststart` → VMAF QC → YouTube upload.
