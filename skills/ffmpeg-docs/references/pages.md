# FFmpeg Doc Page Catalog

The script `scripts/ffdocs.py` fetches from a fixed list of ffmpeg.org doc pages. This file documents what each page contains, when to pick it, and common section anchors worth knowing.

Pages are addressed by their short name (left column). The script turns each into `https://ffmpeg.org/<name>.html`.

---

## CLI tool pages

| Page | URL | Contents |
|---|---|---|
| `ffmpeg` | `/ffmpeg.html` | Main CLI — options, stream selection, filtering basics. |
| `ffmpeg-all` | `/ffmpeg-all.html` | All-in-one: concatenation of `ffmpeg` + every topic-specific page. Huge. |
| `ffplay` | `/ffplay.html` | `ffplay` options + keyboard shortcuts. |
| `ffplay-all` | `/ffplay-all.html` | `ffplay` + all referenced topic pages. |
| `ffprobe` | `/ffprobe.html` | `ffprobe` options, `-show_*` sections, output formats. |
| `ffprobe-all` | `/ffprobe-all.html` | `ffprobe` + all topic pages. |

**When to use `*-all` vs the topic page:** pick the topic page. It's smaller, faster to search, and has the same authoritative content. `*-all` duplicates text — wasteful to search.

---

## Topic pages

| Page | URL | Contents |
|---|---|---|
| `ffmpeg-filters` | `/ffmpeg-filters.html` | **THE** big page. Every video + audio filter: scale, crop, overlay, drawtext, hqdn3d, nlmeans, tonemap, zscale, v360, loudnorm, ebur128, etc. Also lavfi sources (`testsrc`, `sine`, `anullsrc`). |
| `ffmpeg-codecs` | `/ffmpeg-codecs.html` | Encoder/decoder options: libx264 presets/profiles/CRF, libx265, libvpx, libaom-av1, libsvtav1, NVENC, QSV, VAAPI, VideoToolbox, AMF, aac, libopus, libfdk_aac. |
| `ffmpeg-formats` | `/ffmpeg-formats.html` | Muxer + demuxer options: MP4, Matroska, WebM, MPEG-TS, HLS, DASH, image2, concat demuxer, segment muxer, tee muxer, RTP, RTSP. |
| `ffmpeg-protocols` | `/ffmpeg-protocols.html` | I/O protocols: `file`, `http/https`, `rtmp`, `srt`, `rtsp`, `udp`, `tcp`, `pipe`, `concat`, `subfile`, `tee`, `data`, `cache`, `crypto`. |
| `ffmpeg-devices` | `/ffmpeg-devices.html` | Capture + output devices: `avfoundation` (macOS), `gdigrab`/`dshow` (Windows), `x11grab`/`kmsgrab`/`v4l2` (Linux), `alsa`/`pulse`/`coreaudio`, `decklink`. |
| `ffmpeg-bitstream-filters` | `/ffmpeg-bitstream-filters.html` | `-bsf` filters: `h264_mp4toannexb`, `aac_adtstoasc`, `extract_extradata`, `filter_units`, `h264_metadata`, `setts`, `trace_headers`, etc. |
| `ffmpeg-utils` | `/ffmpeg-utils.html` | Shared primitives: time-base syntax, duration strings, color names, channel layouts, expression evaluator (`eval`, `if`, `gt`, `lt`, `hypot`, `sin`, `PTS`, `N`, `T`), filter-graph escaping rules. |
| `ffmpeg-scaler` | `/ffmpeg-scaler.html` | Software scaler options: `sws_flags`, `lanczos`/`bicubic`/`spline`, `accurate_rnd`, `full_chroma_int`, `param0/1`. |
| `ffmpeg-resampler` | `/ffmpeg-resampler.html` | Audio resampler options for `aresample`: `resampler`, `async`, `min_hard_comp`, `first_pts`, dither methods, filter length. |

---

## Library (C API) pages

| Page | URL | Use |
|---|---|---|
| `libavutil` | `/libavutil.html` | C API for the utility layer. |
| `libswscale` | `/libswscale.html` | C API for software scaling. |
| `libswresample` | `/libswresample.html` | C API for audio resampling. |
| `libavcodec` | `/libavcodec.html` | C API for codecs. |
| `libavformat` | `/libavformat.html` | C API for muxers/demuxers. |
| `libavdevice` | `/libavdevice.html` | C API for capture devices. |
| `libavfilter` | `/libavfilter.html` | C API for filters. |

**These are for building apps that LINK against FFmpeg libraries.** They rarely answer command-line questions. When the user asks "what does `-X` do in ffmpeg", skip these.

---

## Supplementary pages

| Page | URL | Contents |
|---|---|---|
| `general` | `/general.html` | Capability inventory: which codecs / containers / devices FFmpeg supports in the default build; build-time dependencies. |
| `faq` | `/faq.html` | Short Q&A on common issues (seeking accuracy, streamcopy vs re-encode, B-frame ordering, etc.). Sometimes answers a question faster than searching topic pages. |
| `platform` | `/platform.html` | How to build FFmpeg on Windows/macOS/Linux/BSD/iOS/Android. |
| `developer` | `/developer.html` | Contributor guide: code style, review process, licensing. |
| `git-howto` | `/git-howto.html` | FFmpeg's git workflow (for contributors). |
| `fate` | `/fate.html` | FATE — FFmpeg's regression test suite. |
| `security` | `/security.html` | Security policy + disclosed CVEs. |
| `legal` | `/legal.html` | LGPL/GPL/3rd-party licensing notes per feature. |

---

## Which page for which question?

Pick the page FIRST, then search it. Flat `search` across all pages works but is noisier.

| User asks... | Page |
|---|---|
| filter `X` parameters / `v360` / `tonemap` / `drawtext` / `loudnorm` / `minterpolate` / any filter name | `ffmpeg-filters` |
| codec encoder options / `libx264` CRF / `NVENC` `-preset` / `libopus` `-application` | `ffmpeg-codecs` |
| muxer options / HLS / DASH / MP4 `-movflags` / `-hls_time` / segment muxer | `ffmpeg-formats` |
| protocol options / `rtmp://` / `srt://` / HTTP headers / `-user_agent` | `ffmpeg-protocols` |
| capture device options / `avfoundation` / `x11grab` / `dshow` / `v4l2` | `ffmpeg-devices` |
| bitstream filter / `h264_mp4toannexb` / `aac_adtstoasc` / `-bsf` | `ffmpeg-bitstream-filters` |
| expression syntax / `eval` / `if(gt(T,1),...)` / time-base / channel layouts | `ffmpeg-utils` |
| `sws_flags` / scaler quality | `ffmpeg-scaler` |
| `aresample` parameters | `ffmpeg-resampler` |
| ffprobe `-show_entries` / output formats | `ffprobe-all` |
| ffplay keyboard controls / `-vf` on live playback | `ffplay` |
| "is codec X supported in my build" | `general` |
| "why is my `-ss` inaccurate" / common pitfalls | `faq` |
| "how do I build FFmpeg with vid.stab / vmaf / libplacebo" | `platform` + `general` |

---

## High-value anchor ids

Section anchors you'll often jump to with `section --page X --id Y`. Anchors may drift as FFmpeg ships new releases — if one fails, run `search` first to find the current id.

### `ffmpeg-filters`

| Anchor | Section |
|---|---|
| `scale-1` | scale filter |
| `crop` | crop filter |
| `overlay-1` | overlay filter |
| `drawtext-1` | drawtext filter |
| `subtitles-1` | subtitles filter |
| `hls-2` (when in formats page, `hls-2` there) | — |
| `tonemap-1` | tonemap |
| `zscale` | zscale |
| `libplacebo` | libplacebo |
| `v360` | v360 |
| `stereo3d` | stereo3d |
| `chromakey` | chromakey |
| `colorkey` | colorkey |
| `hsvkey` | hsvkey |
| `despill` | despill |
| `vidstabdetect` / `vidstabtransform` | vid.stab passes |
| `deshake` | deshake |
| `minterpolate` | motion-interpolation slow-mo |
| `hqdn3d` / `nlmeans-1` / `bm3d` / `atadenoise` | denoise filters |
| `cropdetect` / `silencedetect` / `blackdetect` / `freezedetect` / `scdet` / `idet` | detection filters |
| `libvmaf` / `psnr` / `ssim` | quality metric filters |
| `loudnorm` / `dynaudnorm` / `acompressor` / `compand` | audio dynamics |
| `amix` / `amerge` / `pan` | audio combine |
| `setpts_002c-asetpts` | setpts / asetpts |
| `testsrc` / `smptebars` / `sine` / `anullsrc` | lavfi sources |

### `ffmpeg-formats`

| Anchor | Section |
|---|---|
| `hls-2` | HLS muxer |
| `dash-2` | DASH muxer |
| `matroska` | Matroska/WebM muxer |
| `mov_002c-mp4_002c-ismv` | MP4/MOV muxer (`-movflags`, etc.) |
| `segment_002c-stream_005fsegment_002c-ssegment` | segment muxer |
| `concat-1` | concat demuxer |
| `tee` | tee muxer |
| `image2-1` | image2 demuxer/muxer |

### `ffmpeg-protocols`

| Anchor | Section |
|---|---|
| `rtmp` / `rtmpt` / `rtmps` | RTMP variants |
| `srt` | SRT |
| `rtsp` | RTSP |
| `udp` | UDP |
| `tcp` | TCP |
| `pipe` | pipe protocol |
| `file` | file protocol |
| `concat-2` | concat protocol |
| `tee-1` | tee protocol |
| `crypto` | encrypted read |

### `ffmpeg-codecs`

| Anchor | Section |
|---|---|
| `libx264_002c-libx264rgb` | libx264 / libx264rgb |
| `libx265` | libx265 |
| `libvpx` | libvpx / libvpx-vp9 |
| `libaom-av1` | libaom-av1 |
| `libsvtav1` | libsvtav1 |
| `h264_005fnvenc_002c-nvenc` | NVENC |
| `h264_005fqsv` / `hevc_005fqsv` | Intel Quick Sync |
| `vaapi-encoders` | VAAPI |
| `videotoolbox` | VideoToolbox (Apple) |
| `aac` / `libopus` / `libfdk_005faac` | audio encoders |

### `ffmpeg-devices`

| Anchor | Section |
|---|---|
| `avfoundation` | macOS screen/camera capture |
| `gdigrab` | Windows desktop capture |
| `dshow` | Windows DirectShow |
| `x11grab` | Linux X11 screen capture |
| `kmsgrab` | Linux DRM/KMS capture |
| `v4l2` | Linux V4L2 webcam |
| `alsa` / `pulse` / `coreaudio` | audio capture backends |

### `ffmpeg-bitstream-filters`

| Anchor | Section |
|---|---|
| `h264_005fmp4toannexb` | h264_mp4toannexb |
| `hevc_005fmp4toannexb` | hevc_mp4toannexb |
| `aac_005fadtstoasc` | aac_adtstoasc |
| `extract_005fextradata` | extract_extradata |
| `dump_005fextra` | dump_extra |
| `filter_005funits` | filter_units |
| `h264_005fmetadata` / `hevc_005fmetadata` / `av1_005fmetadata` | metadata bsfs |
| `setts` | setts |
| `trace_005fheaders` | trace_headers |

### `ffmpeg-utils`

| Anchor | Section |
|---|---|
| `Expression-Evaluation` | expression grammar |
| `Date` | date/time parsing |
| `Color` | color name reference |
| `Channel-Layout` | channel layout strings |

**Note on anchor escaping:** ffmpeg.org escapes underscores in anchors as `_002c` and `_005f`. You'll see e.g. `h264_005fmp4toannexb` for `h264_mp4toannexb`. Pass the literal escaped form to `section --id`, or use `search` to find the current id.

---

## Cache behavior

- Cache path: `~/.cache/ffmpeg-docs/` (override with `FFMPEG_DOCS_CACHE` env var).
- One text file per page: `~/.cache/ffmpeg-docs/<page>.txt`.
- Cache never expires automatically. Clear manually with `clear-cache` or by deleting the directory.
- After a new FFmpeg release drops documentation updates, clear + re-index.
- The index command fetches all pages with a 0.5s delay between requests to be polite.

## Offline readiness

Want this to work on a flight / air-gapped machine?

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ffdocs.py index
```

That's it. All 30 pages cached to disk. `search` / `section` / `fetch` now work without network.
