# Mode: broadcast-delivery

**Subagent**: `delivery`
**Trigger phrases**: "broadcast deliver", "MXF master", "IMF package", "ProRes master", "DPP deliver", "AS-11 deliver", "Netflix deliver", "broadcast spec deliver", "deliver for air", "create IMF"
**Output**: `${MEDIA_WORK_DIR}/modes/broadcast-delivery/{date}_{slug}/`
**Approval gate**: required — delivery files are immutable once handed off; operator confirms target spec before encode.

## Inputs

- **Required**:
  - `source` — input master (high-bit-depth, ideally ProRes 4444 / DNxHR HQX / DPX sequence / EXR sequence).
  - `target` — delivery spec: `dpp-as11`, `netflix-imf`, `apple-prores`, `broadcast-imx50`, `xdcam-hd422`, `mxf-op1a`, `imf-application2e`.
- **Optional**:
  - `frame_rate` — explicit override (default: preserve source).
  - `audio_layout` — `5.1`, `5.1+stereo`, `stereo`, `discrete-8-mono`, `dolby-atmos-9.1.6`.
  - `captions` — STL / SCC / SRT / TTML file for muxing.
  - `loudness_target` — `r128` (default), `atsc-a85`, `arib-tr-b32`, `ebu-r128-tv`.

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-broadcast-delivery/SKILL.md` plus `ffmpeg-mxf-imf` and `media-mediainfo`. For loudness: `media-ffmpeg-normalize`.
2. `moprobe --color --json <source>` plus `mediainfo --Output=JSON <source>` for full metadata extraction.
3. **STOP** if source bit depth or chroma is below target spec (e.g. delivering Netflix IMF requires 10-bit 4:2:2 minimum; 8-bit 4:2:0 source must be re-mastered, not just transcoded). Surface to operator.
4. Look up target spec table (in mode reference below) for exact codec + container + flags:
   - `dpp-as11` → MXF OP1a, AVC-Intra 100, 1080i50, BWF audio, DPP shim metadata.
   - `netflix-imf` → IMF Application 2E, JPEG 2000 IMF, OPL/CPL/PKL XML, IAB/Atmos audio.
   - `apple-prores` → ProRes 422 HQ / 4444 / 4444 XQ in QuickTime MOV.
   - `broadcast-imx50` → MPEG-2 422P@HL, 50 Mbps CBR, MXF OP1a.
   - `xdcam-hd422` → MPEG-2 4:2:2, 50 Mbps CBR, 1080i, MXF OP1a.
5. **Approval gate**: present the resolved target spec to the operator (codec, profile, bitrate, GOP structure, audio config, container, metadata sidecars). Wait for explicit approval before encoding.
6. Compose the ffmpeg command (or J2K + MXF wrap chain for IMF; ProRes single-pass for ProRes targets).
7. **`mosafe`-wrap** the command.
8. Encode. Run `mediainfo` on the output to verify codec/profile/level matches target spec exactly.
9. Run loudness measurement: `ffmpeg-normalize -nt <target> -o <normalized> --print-stats <output>`. Confirm within ±0.5 LU of target.
10. Mux captions if provided (`ffmpeg-captions` or MXF-aware tools).
11. Run `moqc` against the source for VMAF baseline (not gate — broadcast specs are about conformance, not perceptual quality).
12. Write `summary.md` with delivery checklist matrix (every spec field: pass/fail).

## Output schema

```markdown
# Broadcast delivery — {slug} — {date}

## Target spec
- **Profile**: {dpp-as11 / netflix-imf / apple-prores / ...}
- **Container**: {MXF OP1a / IMF / QuickTime / ...}
- **Video codec + bitrate**: {AVC-Intra 100 / JPEG 2000 IMF / ProRes 422 HQ / ...}
- **Audio**: {layout, codec, bitrate}
- **Frame rate**: {fps}
- **Captions**: {format or N/A}

## Conformance matrix
| Spec field | Required | Actual | Pass |
|---|---|---|---|
| Video codec | ... | ... | ✓ / ✗ |
| Bitrate | ... | ... | ✓ / ✗ |
| Chroma | ... | ... | ✓ / ✗ |
| Bit depth | ... | ... | ✓ / ✗ |
| Frame rate | ... | ... | ✓ / ✗ |
| Audio layout | ... | ... | ✓ / ✗ |
| Loudness | {target ±0.5 LU} | ... | ✓ / ✗ |
| Captions | ... | ... | ✓ / ✗ |

## VMAF vs source
- **Score**: {N}
- **Note**: broadcast conformance is the gate, not VMAF.

## Files
- **Delivery master**: {path}
- **Sidecars** (IMF only): CPL, PKL, OPL, AssetMap — {paths}
```

## Quality bar

- Every spec field passes the conformance matrix.
- Loudness within ±0.5 LU of target.
- `mediainfo` confirms exact codec/profile/level (not just "MPEG-2 video" — must be `MPEG-2 422P@HL`).
- Captions mux verified by re-probing (subtitle stream present, correct format).
- For IMF: CPL / PKL / OPL / AssetMap XML files all present and validated against IMF schema.
- For MXF: OP1a file structure verified by `mediainfo --Inform="General;%Format_Profile%"`.
