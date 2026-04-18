---
name: media-mediainfo
description: >
  Deep container and stream analysis with MediaInfo (mediainfo --Output=JSON --Full --Inform): codec profiles and levels, bitrate ladders, GOP structure, HDR10 + HDR10+ + Dolby Vision metadata, audio stream channel descriptions, container quirks beyond ffprobe. Use when the user asks to get detailed media info, check codec profile/level, inspect HDR metadata, analyze bitrate distribution, see GOP structure, diagnose a container, or get professional broadcast media diagnostics.
argument-hint: "[file]"
---

# Media Mediainfo

**Context:** $ARGUMENTS

## Quick start

- **Human summary of a file:** → Step 2 (`mediainfo in.mp4`)
- **Machine-readable JSON for scripting:** → Step 2 (`--Output=JSON`) and Step 3
- **HDR10 / HDR10+ / Dolby Vision profile check:** → Step 4 (`hdr` subcommand)
- **Netflix delivery spec pre-flight:** → Step 4 (`netflix-check`)
- **Field-name crosswalk MediaInfo vs ffprobe:** → `references/mediainfo.md`

## When to use

- You need container-level detail that ffprobe silently omits (MP4 atom types, MKV cluster counts, MXF SMPTE operational patterns, CMAF moof/mdat structure).
- HDR static/dynamic metadata verification (MasteringDisplay primaries, MaxCLL, MaxFALL) — ffprobe only surfaces these via `-show_frames -show_entries side_data`; MediaInfo shows them at the stream level.
- Dolby Vision profile disambiguation (DV5 / DV7 / DV8.1 / DV8.4) — MediaInfo's DV reporting is the most reliable outside studio toolchains.
- Broadcast QC — codec profile ("High@L4.1", "Main 10@L5.1@High"), GOP structure, color description, audio channel layout description.
- Multi-file delivery audits where you script a compliance check and compare many files against a spec.

## Step 1 — Install

```bash
# macOS
brew install mediainfo

# Debian / Ubuntu
sudo apt-get install -y mediainfo

# verify
mediainfo --Version
```

Same binary and engine power the CLI and the GUI app — the JSON schema is stable across versions, so pin to JSON for automation.

## Step 2 — Pick an output format

```bash
mediainfo in.mp4                                 # human-readable default
mediainfo --Full in.mp4                          # every tag, verbose (HDR, DV, GOP live here)
mediainfo --Output=JSON in.mp4                   # machine-readable, stable schema
mediainfo --Output=XML  in.mp4                   # XML tree, same info as JSON
mediainfo --Output=HTML in.mp4 > report.html     # browseable report
mediainfo --Output=EBU  in.mxf                   # EBU Core XML for broadcast
mediainfo --Output=PBCore in.mxf                 # PBCore XML for archives
mediainfo --Output=MPEG-7 in.mp4                 # MPEG-7 description
mediainfo --Output=CSV  in.mp4                   # CSV rows
```

Specific-field templates use `--Inform="<stream>;<format>"` and `%Field%` tokens:

```bash
mediainfo --Inform="Video;%Width% x %Height% @ %FrameRate%fps"  in.mp4
mediainfo --Inform="General;%Format% %Duration/String3%ms"      in.mp4
mediainfo --Inform="Audio;%Format% %Channels%ch %SamplingRate%" in.mp4
```

`--Output` picks a preset. `--Inform` customizes. `%Field%` names are MediaInfo's (not ffprobe's) — see `references/mediainfo.md` for the catalog.

## Step 3 — Parse

Use JSON for automation. The root is `{"media": {"track": [...]}}`; each track has `"@type"` in `{General, Video, Audio, Text, Image, Menu, Other}`.

```bash
mediainfo --Output=JSON in.mp4 | jq '.media.track[] | {type: ."@type", format: .Format}'
mediainfo --Output=JSON in.mp4 | jq '.media.track[] | select(."@type"=="Video") | {w:.Width, h:.Height, prof:."Format profile", bd:.BitDepth}'
mediainfo --Output=JSON in.mp4 | jq '.media.track[] | select(."@type"=="Audio") | {codec:.Format, ch:.Channels, layout:.ChannelLayout}'
```

HDR / Dolby Vision inspection:

```bash
mediainfo --Full in.mkv | grep -i -E "colour|HDR|mastering|MaxCLL|MaxFALL|Dolby Vision|DV"
mediainfo --Full in.mp4 | grep -i dv                 # DV profile lines
```

GOP structure + codec profile:

```bash
mediainfo --Full in.mp4 | grep -i -E "format profile|gop|bframe|reference frame"
```

Per-codec profile strings:
- H.264 → `"High@L4.1"`, `"High 10@L5.1"`, `"Baseline@L3.0"`
- HEVC  → `"Main 10@L5.1@High"` (profile / level / tier)
- AV1   → `"Main@L5.1"`
- AAC   → `"LC"`, `"HE"`, `"HE v2"`

## Step 4 — Use with diagnostics (this skill's script)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py check
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py summary      --input in.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py json         --input in.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py field        --input in.mp4 --stream Video --name Width
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py hdr          --input in.mkv
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py codec-profile --input in.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py compare      --inputs a.mp4 b.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py netflix-check --input in.mp4
```

`hdr` returns a verdict (`SDR / HDR10 / HDR10+ / HLG / DolbyVision`) plus details. `codec-profile` parses profile + level for every video + audio stream. `netflix-check` flags common Netflix IMF/4K deliverables: HEVC Main 10, 10-bit, BT.2020, PQ, 3840x2160 or higher, ≥ 16 Mb/s for 4K.

## Gotchas

- **MediaInfo > ffprobe for container-level info.** MP4 atom types, MKV cluster counts, fragmented-MP4 moof/mdat structure, MXF SMPTE operational pattern — all visible in MediaInfo; ffprobe often omits them.
- **HDR10 static metadata is visible in MediaInfo `--Full`** as `MasteringDisplay_ColorPrimaries`, `MasteringDisplay_Luminance`, `MaxCLL`, `MaxFALL`. ffprobe only surfaces these via `-show_frames -show_entries side_data` — expensive and requires decoding.
- **Dolby Vision profile** (5 / 7 / 8.1 / 8.4) reporting is reliable in MediaInfo. The line you want: `HDR format : Dolby Vision, Version 1.0, Profile 8.1, dvhe.08.06`.
- **GOP structure** (B-frame pattern, reference frame count, closed vs open GOP) is only visible via MediaInfo's deeper parse — ffprobe needs `-show_frames` frame-by-frame to infer it.
- **JSON schema is stable across versions.** Use it for automation. The human-readable output is NOT stable.
- **Streams from URLs work:** `mediainfo https://example.com/file.mp4` — MediaInfo partial-downloads headers and index, no full file required.
- **`--Output` (capital O) vs `--Inform`:** `--Output` picks a preset format (JSON, XML, HTML, EBU, PBCore, MPEG-7, CSV). `--Inform` customizes output using `%Field%` templates.
- **`%Field%` syntax uses MediaInfo's names, NOT ffprobe's.** `%Width%` not `width`. `%FrameRate%` not `r_frame_rate`. See the crosswalk in `references/mediainfo.md`.
- **FrameRate variants:** `FrameRate` is the current effective rate; `FrameRate_Original` is the pre-conversion rate (important for IVTC'd / telecined sources).
- **`Duration/String3` is milliseconds as a formatted string** ("01:23:45.678"). Raw `Duration` is seconds as a float string. `BitRate` is integer bps; `BitRate/String` is `"8 000 kb/s"` formatted.
- **Format profile strings:** H.264 = `"High@L4.1"`, HEVC = `"Main 10@L5.1@High"` (profile / level / tier), AV1 = `"Main@L5.1"`. Parse on `@`.
- **MediaInfo CLI and GUI share one engine.** Output differs only by renderer.
- **Some fields require codec metadata in the bitstream** (SPS/PPS for H.264, VPS for HEVC). If a codec was muxed without them, MediaInfo reports less. Fall back to ffprobe for bitstream-derived fields in that rare case.
- **MXF:** MediaInfo shows SMPTE operational patterns (OP1a / OP1b / OP-Atom) better than ffprobe.
- **3GPP / AMR / small containers:** MediaInfo handles gracefully where ffprobe can choke.
- **CMAF fragmented MP4:** MediaInfo shows `moof`/`mdat` structure and fragment count; ffprobe sees only the muxed logical stream.

## Examples

### Example 1 — Is this file HDR10 or Dolby Vision?

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py hdr --input in.mkv
# {"verdict":"DolbyVision","dv_profile":"8.1","transfer":"PQ","primaries":"BT.2020","max_cll":1000,"max_fall":400}
```

### Example 2 — Netflix 4K HDR10 delivery pre-flight

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py netflix-check --input master.mxf
# {"pass":true,"checks":{"codec":"HEVC","profile":"Main 10","bit_depth":10,"resolution":"3840x2160","hdr":"HDR10","bitrate_mbps":18.4}}
```

### Example 3 — Extract one field for scripting

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py field --input in.mp4 --stream Video --name "Format profile"
# High@L4.1
```

### Example 4 — Compare two encodes

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mediainfo.py compare --inputs src.mov encode.mp4
```

## Troubleshooting

### Error: `mediainfo: command not found`

Cause: MediaInfo is not installed.
Solution: `brew install mediainfo` (macOS) or `apt-get install mediainfo` (Linux). Verify with `mediainfo --Version`.

### Field is missing in the JSON

Cause: Codec metadata (SPS/PPS/VPS) not present in the muxed bitstream, or the field is only surfaced by `--Full`.
Solution: Re-run with `--Full`. If still missing, fall back to ffprobe `-show_streams -show_frames` for bitstream-derived values.

### HDR / Dolby Vision not detected

Cause: Streaming segment without the init/header segment; or a partial file truncated before the config record.
Solution: Point MediaInfo at the init segment (`init.mp4`) or the full file. For DASH/CMAF, run MediaInfo on the init segment concatenated with one media segment.

### URL input hangs

Cause: Server does not support HTTP Range requests; MediaInfo tries to stream blindly.
Solution: Download with `curl -o file.mp4 URL` then run MediaInfo on the local file.

### `--Inform` returns nothing

Cause: Wrong stream name (case matters: `Video` not `video`) or unknown field name.
Solution: Check `references/mediainfo.md` for the exact `%Field%` catalog per stream type.
