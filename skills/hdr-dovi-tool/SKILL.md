---
name: hdr-dovi-tool
description: >
  Author Dolby Vision RPU dynamic metadata with dovi_tool: info (parse RPU + per-frame JSON), generate (RPU from XML/JSON/HDR10+/madVR), editor (JSON-driven edits), export (RPU to JSON / scene markers / L5), plot (level graphs), convert (profile 7 to 8.1), demux (BL+EL split), mux (BL+EL recombine), extract-rpu (out of HEVC Annex-B), inject-rpu (into HEVC Annex-B), remove (strip DV NAL). Plus an end-to-end pipeline subcommand that chains ffmpeg hevc_mp4toannexb + extract-rpu + inject-rpu + mkvmerge/MP4Box. Supports DV profiles 4, 5, 7, 8.1, 8.4. Use when the user asks to extract or inject a Dolby Vision RPU, convert DV profile 7 to 8.1, edit a DV metadata JSON, or repackage HEVC with DV.
argument-hint: "[subcommand] [args...]"
---

# HDR dovi_tool

**Context:** $ARGUMENTS

## Quick start

- **Extract RPU from HEVC:** → Step 3 (`dovi.py extract-rpu`)
- **Inject RPU back:** → Step 4 (`dovi.py inject-rpu`)
- **Convert profile 7 (BL+EL) → 8.1 (single-layer):** → Step 5 (`dovi.py convert`)
- **Edit RPU with JSON script:** → Step 6 (`dovi.py editor`)
- **End-to-end pipeline (MKV → edited RPU → MKV):** → Step 7 (`dovi.py pipeline`)

## When to use

- User wants to strip, edit, or repackage Dolby Vision metadata.
- User wants to convert a profile-7 dual-layer source to single-layer 8.1 MKV/MP4.
- User wants a plot of per-frame brightness metadata.
- For the doc side (subcommand discovery, flag lookup), use `hdr-dynmeta-docs`.
- For HDR10+ (not Dolby Vision), use `hdr-hdr10plus-tool`.

---

## Step 1 — Install

```bash
cargo install --locked --git https://github.com/quietvoid/dovi_tool
# OR: grab a pre-built binary from the repo's Releases tab
```

Needs Rust (MSRV tracks recent — see `hdr-dynmeta-docs fetch --page dovi-releases`). Also needs ffmpeg on PATH for the `pipeline` subcommand; mkvmerge (from MKVToolNix) or MP4Box (from GPAC) for remuxing.

Verify:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py info --help
```

---

## Step 2 — Parse an existing RPU

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py info --input source.hevc --summary
```

Output: RPU header + per-frame L1/L2/L5/L6/L8/L9/L11 metadata.

---

## Step 3 — Extract RPU from HEVC

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py extract-rpu \
  --input source.hevc --output rpu.bin
```

**Input must be HEVC Annex-B**, not muxed MP4/MKV. Use ffmpeg to unpack first, or use the `pipeline` subcommand for the full chain.

---

## Step 4 — Inject RPU back

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py inject-rpu \
  --input source.hevc --rpu-in rpu.bin --output injected.hevc
```

Result is Annex-B HEVC with the RPU NAL units stitched back in. Remux to MKV/MP4 (Step 7).

---

## Step 5 — Profile 7 → 8.1

Profile 7 is dual-layer (BL+EL); profile 8.1 is single-layer. Most playback devices prefer 8.1.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py convert \
  --input source.hevc --output converted.hevc --mode 2
```

Mode 2 = "convert to 8.1 for broader compatibility" (typical ask). See upstream README for the full mode table.

---

## Step 6 — JSON-driven RPU edits

Author `edit.json` per the dovi_tool docs, then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py editor \
  --input rpu.bin --json edit.json --output edited.bin
```

Common edits: trim frame range, offset L1 brightness, inject scene-change markers.

---

## Step 7 — End-to-end pipeline

Chains:

1. `ffmpeg -bsf:v hevc_mp4toannexb` to extract Annex-B HEVC from MKV/MP4
2. `dovi_tool extract-rpu`
3. (optional) `dovi_tool editor` with a JSON
4. `dovi_tool convert` (if `--convert-profile-7-to-81`)
5. `dovi_tool inject-rpu`
6. `mkvmerge` OR `MP4Box` to repackage

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py pipeline \
  --input movie.mkv --output out.mkv --edit-json edit.json
```

Target container inferred from output extension (`.mkv` → mkvmerge, `.mp4` → MP4Box). `--strip-dv` removes DV instead of re-injecting. `--convert-profile-7-to-81` adds the convert step. `--info-only` runs info + plot without writing. Use `--dry-run` to preview without executing.

---

## Step 8 — Plot brightness

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py plot \
  --input rpu.bin --output brightness.png
```

---

## Step 9 — Export / Demux / Mux / Remove

```bash
# Export RPU to JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py export --input rpu.bin --output rpu.json

# Demux BL+EL dual-layer stream (profile 7)
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py demux \
  --input dual.hevc --bl-out bl.hevc --el-out el.hevc

# Remux them
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py mux \
  --bl bl.hevc --el el.hevc --output dual.hevc

# Strip all DV RPU from HEVC
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py remove \
  --input hasdv.hevc --output plain.hevc
```

---

## Gotchas

- **Input to extract-rpu MUST be HEVC Annex-B, not muxed MP4/MKV.** `pipeline` handles the bsf step; standalone extract-rpu/inject-rpu do not.
- **Profile 8.2 is NOT documented as supported** — don't promise it. Supported: 4, 5, 7, 8.1, 8.4.
- **After inject-rpu you have a raw .hevc bytestream.** You MUST remux it (pipeline handles this; manual chain needs `mkvmerge -o out.mkv injected.hevc` or `MP4Box -add injected.hevc:dvhe=hvcC out.mp4`).
- **ffmpeg's MP4 muxer for HEVC+RPU is flaky.** Prefer mkvmerge or MP4Box. If you must use ffmpeg, add `-tag:v dvh1` (profile 5) or `-tag:v dvhe` (profile 8) manually.
- **Profile 7→8.1 convert MODE matters.** Mode 2 is the common "give me 8.1 for compatibility" answer. Other modes preserve or diagnose. Consult README.
- **Apple TV / iOS prefer profile 5** (IPT-C2 single-layer). Profile 8.1 (bt.2020 single-layer) may not be recognized on older Apple devices — you'd need a profile 5 re-encode, which dovi_tool alone cannot do.
- **RPU NAL ordering is strict.** inject-rpu places RPU NALs immediately before slice-layer NALs; hand-spliced streams silently drop DV. Always use dovi_tool.
- **Editor JSON schema changes between versions.** Check `dovi_tool --version` against the schema you're editing. Keep edit JSONs in VCS alongside tool version.
- **The script is stdlib-only.** Non-interactive, prints every real `dovi_tool` / `ffmpeg` / `mkvmerge` / `MP4Box` command to stderr before running. `--dry-run` supported on every subcommand.

---

## Examples

### Example 1 — Convert a profile-7 Blu-ray remux to 8.1 single-layer MKV

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py pipeline \
  --input BD.mkv --output out.mkv --convert-profile-7-to-81
```

Wrapper chains: ffmpeg bsf → extract RPU → convert → inject → mkvmerge.

### Example 2 — Strip Dolby Vision from a file entirely

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py pipeline \
  --input dv.mkv --output plain.mkv --strip-dv
```

### Example 3 — Inspect DV metadata

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py pipeline --input dv.mkv --info-only
```

### Example 4 — Plot L1 brightness

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py plot --input rpu.bin --output l1.png
```

### Example 5 — Apply a JSON edit to an RPU

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/dovi.py editor \
  --input rpu.bin --json trim.json --output trimmed.bin
```

---

## Troubleshooting

### `dovi_tool: command not found`

**Solution:** `cargo install --locked --git https://github.com/quietvoid/dovi_tool` or download pre-built from Releases.

### `extract-rpu: Failed to parse HEVC stream`

**Cause:** Input was MP4/MKV-muxed HEVC, not Annex-B.
**Solution:** Pipe through ffmpeg first: `ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | dovi_tool extract-rpu -`, or use the `pipeline` subcommand.

### MKV plays SDR, not Dolby Vision

**Cause:** RPU wasn't injected, or the remux dropped the `dvh*` codec tag.
**Solution:** Use mkvmerge: `mkvmerge -o out.mkv injected.hevc`. For MP4: `MP4Box -add injected.hevc:dvhe=hvcC out.mp4`.

### Profile 7 convert mode mystery

**Solution:** `dovi_tool convert --help` lists modes. Mode 2 = common "give me 8.1" answer. Or: `hdr-dynmeta-docs section --page dovi-readme --id convert`.

---

## Reference docs

- Verified dovi_tool subcommand catalog + pipeline chain → see `hdr-dynmeta-docs` skill's `references/subcommands.md`.
- RPU editor JSON schema cheat sheet → `references/edit-schema.md` in this skill.
