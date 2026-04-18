# Verified subcommand catalog

All subcommands below were verified from the upstream READMEs (`github.com/quietvoid/dovi_tool` and `github.com/quietvoid/hdr10plus_tool`).

## dovi_tool

| Subcommand | Role |
|---|---|
| `info` | Dump RPU header + per-frame L1/L2/L5/L6/L8/L9/L11 metadata. |
| `generate` | Build an RPU from input XML/JSON, madVR measurement, or HDR10+ JSON. |
| `editor` | Apply a JSON-driven edit script to an existing RPU (trim, offset L1, scene-edit). |
| `export` | Emit RPU as JSON, scene markers, or L5 crop info. |
| `plot` | Render a brightness-over-time PNG graph. |
| `convert` | Rewrite profile 7 (BL+EL dual-layer) to profile 8.1 (single-layer). |
| `demux` | Split BL+EL into separate HEVC Annex-B streams. |
| `mux` | Recombine BL+EL back into a dual-layer stream. |
| `extract-rpu` | Pull the RPU NAL units out of an HEVC Annex-B bytestream. |
| `inject-rpu` | Stitch an RPU back into an HEVC Annex-B bytestream. |
| `remove` | Strip all DV RPU NAL units from HEVC. |

### DV profiles supported

`4`, `5`, `7`, `8.1`, `8.4`. Profile 8.2 is NOT documented as supported.

## hdr10plus_tool

| Subcommand | Role |
|---|---|
| `extract` | Pull HDR10+ SEI data out of HEVC/MKV to Samsung-compatible JSON with scene info. |
| `inject` | Insert HDR10+ SEI NAL units into HEVC Annex-B (before slice-layer NAL). |
| `remove` | Strip all HDR10+ SEI NAL units from HEVC. |
| `plot` | Render brightness-metadata PNG. |
| `editor` | JSON-driven edits: drop frames, duplicate runs, splice scenes. |

### Install / version notes

- **Latest hdr10plus_tool**: 1.7.2 (Dec 2025).
- **Min Rust**: 1.85.0.
- **dovi_tool** tracks a similar MSRV window; check `dovi-releases` page for current.
- **Install from source**: `cargo install --locked --git https://github.com/quietvoid/<tool>`.
- **Binaries**: Releases tab on each repo has pre-built Windows / Linux / macOS builds.

## HEVC Annex-B I/O

Both tools operate on raw Annex-B HEVC bitstream, not MP4/MKV containers.

### Extract Annex-B from MKV/MP4 with ffmpeg

```bash
# HEVC in MKV → raw Annex-B
ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc out.hevc

# Then:
dovi_tool extract-rpu out.hevc -o rpu.bin
hdr10plus_tool extract out.hevc -o hdr10plus.json
```

### Remux after inject

```bash
# After dovi_tool inject-rpu creates a new .hevc bytestream, remux:
mkvmerge -o out.mkv new.hevc           # MKV route (preferred)
MP4Box -add new.hevc:dvhe=hvcC out.mp4 # MP4 route via GPAC (DV profile 5 or 8.1)
```

ffmpeg's MP4 muxer for HEVC+RPU is flaky; prefer mkvmerge or MP4Box.

## Pipeline overview

```
Source (MKV/MP4)
    │  ffmpeg bsf=hevc_mp4toannexb
    ▼
HEVC Annex-B
    │  dovi_tool extract-rpu → rpu.bin
    │  dovi_tool editor (optional) → edited.bin
    │  dovi_tool inject-rpu rpu=edited.bin
    ▼
HEVC Annex-B with new RPU
    │  mkvmerge / MP4Box
    ▼
Deliverable (MKV/MP4)
```

Same shape for hdr10plus_tool: `extract` → `editor` → `inject`.
