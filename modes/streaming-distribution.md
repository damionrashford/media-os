# Mode: streaming-distribution

**Subagent**: `delivery`
**Trigger phrases**: "HLS deliver", "DASH package", "encode for streaming", "CDN upload", "make a HLS manifest", "multi-bitrate ladder", "CMAF package", "LL-HLS", "low-latency stream", "Widevine package", "DRM package", "package for streaming"
**Output**: `${MEDIA_WORK_DIR}/modes/streaming-distribution/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input mezzanine file (master MP4/MOV/MXF).
- **Optional**:
  - `protocol` — `hls` (default), `dash`, `both`.
  - `ladder` — comma-separated kbps tiers (default derived from input resolution).
  - `vmaf_min` — minimum acceptable VMAF per tier (default from `DEFAULT_VMAF_TARGET` userConfig, fallback 93).
  - `drm` — `none` (default), `widevine`, `playready`, `fairplay`, `all` (cbcs unified).
  - `cdn` — `none` (default), `cloudflare`, `mux`, `bunny`. Reads relevant token from userConfig.
  - `captions` — caption file(s) to mux (WebVTT for HLS; TTML for DASH).

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-streaming-distribution/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-streaming/SKILL.md`. If `drm != none`, also read `${CLAUDE_PLUGIN_ROOT}/skills/ffmpeg-drm/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/skills/media-shaka/SKILL.md`.
2. `moprobe --color --json <source>` to capture: codec, profile, color primaries/transfer/matrix, HDR side-data, audio layout, duration, GOP structure.
3. **STOP** if input has HDR metadata but `protocol=hls` is requested without Dolby Vision profile 8.4 — DV 5/7 require remux; flag and recommend hdr-mastering mode first.
4. Derive bitrate ladder from input resolution if not specified:
   - 2160p source: `15000,8000,5000,3000,1500`
   - 1080p source: `8000,5000,3000,1500,750`
   - 720p source: `4000,2500,1200,600`
5. For each tier, build the `ffmpeg` re-encode command (libx264 or libx265). For HLS: `-sc_threshold 0 -keyint_min 48 -g 48 -hls_time 4 -hls_segment_type fmp4 -hls_playlist_type vod -hls_flags independent_segments`. For DASH: `-use_template 1 -use_timeline 1 -seg_duration 4 -frag_type duration`.
6. **`mosafe`-wrap every ffmpeg call.** Reject if it fails the lint.
7. Encode each tier sequentially (parallelize only if `MEDIA_WORK_DIR` is on fast SSD and operator approved fan-out).
8. Run `moqc --ref <source> --out <tier-output> --vmaf-min <vmaf_min> --format json` per tier. Tiers failing the VMAF gate get re-encoded one preset slower (`medium` → `slow` → `slower`).
9. If `drm != none`, package through Shaka: `packager --enable_raw_key_encryption --keys ... --protection_scheme cbcs --hls_master_playlist_output master.m3u8 ...`. Use cbcs scheme (unified DRM); not cenc.
10. If `captions`, mux into segments (WebVTT for HLS, TTML for DASH).
11. If `cdn != none`, push via the cloud-upload skill (`media-cloud-upload`) using the appropriate userConfig token.
12. Write `summary.md` with final manifest path, per-tier VMAF/SSIM/PSNR, DRM scheme used, CDN URL if uploaded.

## Output schema

```markdown
# Streaming distribution — {slug} — {date}

## Source
- **Path**: {source}
- **Resolution**: {WxH}
- **Codec**: {codec, profile, level}
- **Color**: {primaries / transfer / matrix} {HDR if applicable}
- **Duration**: {hh:mm:ss}
- **Audio**: {channels, codec, bitrate}

## Output ladder
| Tier | Bitrate | VMAF | SSIM | PSNR | Path |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

## Packaging
- **Protocol(s)**: {hls / dash / both}
- **DRM**: {none / widevine / playready / fairplay / all (cbcs)}
- **Captions**: {WebVTT / TTML / none}
- **Master manifest**: {path}

## CDN
- **Provider**: {none / cloudflare / mux / bunny}
- **URL**: {public URL or N/A}

## Quality gate
- **VMAF minimum**: {vmaf_min}
- **All tiers passed**: {yes / no — list failing tiers}
```

## Quality bar

- Every tier `mosafe`-clean.
- `-sc_threshold 0` present on every HLS encode.
- `-movflags +faststart` on any MP4 outputs.
- Every tier passes the VMAF gate, OR the gate failure is surfaced with the slower preset attempted.
- HEVC outputs use `-tag:v hvc1` (Apple-compatible).
- DRM uses cbcs scheme (not cenc) when targeting unified Widevine + PlayReady + FairPlay.
- Caption files muxed cleanly (re-probe segments to confirm subtitle stream present).
