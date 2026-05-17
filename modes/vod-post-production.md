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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-vod-post-production/SKILL.md`. Read tool skills: `ffmpeg-transcode`, `ffmpeg-quality`, `ffmpeg-hwaccel`, `ffmpeg-bitstream`.
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
