# Mode: vfx-pipeline

**Subagent**: `architect`
**Trigger phrases**: "VFX conform", "EXR to master", "ACES pipeline", "USD scene", "OCIO conform", "OpenColorIO", "color management", "EXR sequence", "dailies turnaround", "VFX deliver"
**Output**: `${MEDIA_WORK_DIR}/modes/vfx-pipeline/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — EXR sequence (file pattern `frame_%06d.exr`), DPX sequence, or USD stage.
  - `target_space` — final color space: `rec709-display`, `rec2020-pq`, `aces-rec709`, `aces-rec2020-pq`, `dcdm-p3`.
- **Optional**:
  - `working_space` — `acescg` (default), `aceslog`, `linear-rec709`.
  - `ocio_config` — path to OCIO config (default: ACES Studio Config 1.3).
  - `frame_range` — `1-1000` (default: all frames in sequence).
  - `lut` — additional creative LUT to apply after working-to-target conform.

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-vfx-pipeline/SKILL.md`. Read tool skills: `vfx-oiio`, `vfx-openexr`, `vfx-usd`, `ffmpeg-ocio-colorpro`, `ffmpeg-lut-grade`, `ffmpeg-hdr-color`.
2. Use `oiiotool --info <source-frame>` to capture per-channel bit depth, compression (PIZ/ZIPS/DWA/none), color space metadata (if `acesImage` chroma tag present), display window vs data window.
3. For EXR sequences: verify all frames in `frame_range` exist (`ls <pattern>` count vs expected). Surface missing frames as a STOP condition.
4. For USD stages: `usdview --no-window` headless render via Hydra (Storm/RTX) to produce an EXR sequence.
5. Validate `working_space` and `target_space` exist in the OCIO config (`ociocheck --inputconfig <ocio_config>` plus enum lookup).
6. Build the conform graph per `ffmpeg-ocio-colorpro` SKILL.md:
   - For ACES → Rec.709: `OCIOColorSpace inputspace=ACEScg outputspace="Output - Rec.709"`.
   - For Rec.2020 PQ delivery: `OCIOColorSpace inputspace=ACEScg outputspace="Utility - Linear - Rec.2020"` → then `zscale=t=linear:p=2020:m=2020nc → format=gbrpf32le → zscale=p=bt2020:t=smpte2084` for PQ encode.
   - Apply `lut` after the working-to-target conform (creative grade goes last).
7. **`mosafe`-wrap** the ffmpeg invocation (especially the zscale sandwich for HDR conform).
8. Encode out to ProRes 4444 (mezzanine) OR JPEG 2000 IMF (for IMF delivery) OR per-frame target sequence.
9. If target is HDR, write SEI/static metadata (`-metadata:s:v:0 mastering_display_metadata=...`).
10. Run `oiiotool --colorconvert <working> <target>` on a representative frame as a numerical sanity check (compare pixel values to a known reference).
11. Write `summary.md` with frame count, color path graph, codec/bit depth choices, runtime.

## Output schema

```markdown
# VFX pipeline — {slug} — {date}

## Source
- **Type**: {EXR sequence / DPX sequence / USD stage}
- **Frame range**: {start-end} ({total} frames)
- **Source space**: {ACEScg / linear-Rec.709 / scene-linear}
- **Bit depth**: {16-bit half / 32-bit float}
- **EXR compression** (if EXR): {PIZ / ZIPS / DWA / none}

## Color path
- **OCIO config**: {path}
- **Working space**: {acescg / aceslog / linear-rec709}
- **Target space**: {rec709-display / rec2020-pq / aces-rec709 / aces-rec2020-pq / dcdm-p3}
- **Creative LUT applied**: {path or none}

## Output
- **Codec**: {ProRes 4444 / JPEG 2000 / EXR sequence / DPX sequence}
- **Container**: {QuickTime MOV / MXF IMF / sequence}
- **Frame count out**: {N}
- **HDR metadata**: {present / N/A}
- **File / sequence path**: {path}

## Reference frame check
- Test frame: {frame N}
- Pre-conform pixel sample at (x,y): {R,G,B}
- Post-conform pixel sample at same (x,y): {R,G,B}
- Match against expected target value (if reference provided): {pass / fail / N/A}
```

## Quality bar

- Every frame in `frame_range` exists at start; missing frames surfaced (don't silently fill black).
- Color space conform passes the reference-frame pixel check (within ±1% tolerance for float conversions).
- Bit depth preserved through working space (never collapse to 8-bit mid-pipeline).
- For HDR target: SEI/static metadata present in output; mosafe confirmed zscale sandwich correct.
- For IMF target: hand-off to `broadcast-delivery` mode for OPL/CPL/PKL generation.
- LUT application is the LAST step (creative grade after technical conform).
