# Mode: hdr-mastering

**Subagent**: `hdr`
**Trigger phrases**: "Dolby Vision", "HDR10+", "HDR master", "tone map HDR", "PQ to HLG", "HLG to PQ", "DV profile", "static HDR metadata", "dynamic HDR metadata", "MaxCLL", "MaxFALL", "ACES tone map"
**Output**: `${MEDIA_WORK_DIR}/modes/hdr-mastering/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input file (SDR or HDR).
  - `target_format` — `hdr10`, `hdr10-plus`, `dolby-vision-profile-5`, `dolby-vision-profile-7`, `dolby-vision-profile-8.4`, `hlg`, `sdr-tone-map`.
- **Optional**:
  - `mastering_display` — peak nits (default: `1000`), min nits (default: `0.005`), color primaries (default: `bt2020`).
  - `maxcll_maxfall` — `auto` (measure from content, default) or explicit `<MaxCLL>,<MaxFALL>` nits.
  - `tone_map_algo` — for SDR conversion: `reinhard` / `mobius` / `hable` (default for film) / `bt2390` (default for broadcast).

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-hdr/SKILL.md`. Read tool skills: `ffmpeg-hdr-color`, `hdr-dovi-tool`, `hdr-hdr10plus-tool`, `ffmpeg-ocio-colorpro`.
2. `moprobe --color --json <source>` to capture color primaries, transfer, matrix, MaxCLL / MaxFALL (if present), HDR side-data (DV RPU, HDR10+ JSON), bit depth.
3. **STOP** if source is 8-bit and target is HDR (HDR requires 10-bit minimum). Surface that the source must be re-mastered, not just transcoded.
4. Branch by `target_format`:
   - **`hdr10`** (static metadata) → encode with `-color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc` + `mastering_display_metadata` + `content_light_level`. Compute MaxCLL/MaxFALL with `ffmpeg -i <src> -vf signalstats -f null -` if `auto`.
   - **`hdr10-plus`** (dynamic metadata) → extract HDR10+ JSON from source via `hdr10plus_tool extract`, encode HEVC with `--repeat-headers --hdr10-plus` flags, inject via `hdr10plus_tool inject`.
   - **`dolby-vision-profile-5`** → DV-only (no HDR10 fallback). Encode HEVC + DV RPU; package as IMF or MXF.
   - **`dolby-vision-profile-7`** → DV + HDR10 fallback (dual-layer). `dovi_tool convert -m 2` for profile 7 mode.
   - **`dolby-vision-profile-8.4`** → DV + HDR10 fallback, single-layer (only DV profile that works in HLS). `dovi_tool convert -m 2 --rpu-out` then mux RPU into HEVC bitstream.
   - **`hlg`** → BBC/NHK broadcast HDR. Convert with `zscale=t=linear→format=gbrpf32le→zscale=p=bt2020:t=arib-std-b67` sandwich. NEVER direct format conversion.
   - **`sdr-tone-map`** → use `zscale=t=linear→tonemap=<algo>:peak=<peak>` chain. Default to `bt2390` for broadcast.
5. Build the ffmpeg command per branch.
6. **`mosafe`-wrap** the command. Reject if it doesn't pass — the zscale sandwich and SEI metadata patterns trip up training-data flags.
7. Encode. For DV profiles requiring RPU mux: use `dovi_tool inject` post-encode.
8. Verify output: `ffprobe -show_streams` confirms `color_primaries=bt2020`, `color_transfer=smpte2084` (or `arib-std-b67` for HLG); for DV: `dovi_tool info` shows correct profile.
9. For HDR10+: `hdr10plus_tool extract` from output and compare frame count to source JSON.
10. Run `moqc --ref <source> --out <output>` for sanity (VMAF is gamma-aware; HDR scores may be lower than SDR — that's expected).
11. Write `summary.md` with target format, mastering display config, before/after color metadata, DV/HDR10+ verification results.

## Output schema

```markdown
# HDR mastering — {slug} — {date}

## Source HDR profile
- **Color primaries / transfer / matrix**: {primaries / transfer / matrix}
- **Bit depth**: {N bits}
- **MaxCLL / MaxFALL**: {N / N nits, or N/A}
- **Dynamic metadata**: {HDR10+ JSON / DV RPU profile X / none}

## Target
- **Format**: {hdr10 / hdr10-plus / dolby-vision-profile-{5,7,8.4} / hlg / sdr-tone-map}
- **Mastering display**: {peak nits, min nits, primaries}
- **MaxCLL / MaxFALL out**: {N / N nits — auto-measured or explicit}
- **Tone-map algo** (SDR only): {reinhard / mobius / hable / bt2390}

## Output metadata verification
- **`ffprobe color_primaries`**: {bt2020 / bt709}
- **`ffprobe color_transfer`**: {smpte2084 / arib-std-b67 / bt709}
- **DV verification** (`dovi_tool info`): {profile X verified / N/A}
- **HDR10+ verification** (`hdr10plus_tool extract`): {N frames match source / N/A}

## VMAF (HDR-aware)
- **Score vs source**: {N}
- **Note**: HDR scores commonly trail SDR for the same perceived quality.

## Files
- **Master**: {path}
- **DV RPU sidecar** (if applicable): {path}
- **HDR10+ JSON sidecar** (if applicable): {path}
```

## Quality bar

- 10-bit minimum throughout pipeline.
- `mosafe` passed on the zscale sandwich (the key foot-gun for HDR conversion).
- For DV profile 8.4 targeting HLS: RPU is in-bitstream (mux verified via `dovi_tool info`).
- For HDR10+: per-frame JSON count matches source (no dropped metadata frames).
- Color metadata explicitly written, not "inherited" (specifying `bt709` defaults is a foot-gun in HDR pipelines).
- For SDR tone-map: peak nits specified explicitly (default to mastering_display peak, fall back to 400 nits if unknown).
