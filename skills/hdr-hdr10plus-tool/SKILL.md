---
name: hdr-hdr10plus-tool
description: >
  Author HDR10+ dynamic metadata with hdr10plus_tool: extract (HDR10+ metadata out of HEVC/MKV to Samsung-compatible JSON with scene info), inject (HDR10+ SEI NAL units into HEVC Annex-B before slice data), remove (strip HDR10+ NAL units), plot (brightness-metadata PNG), editor (JSON-driven edits: drop frames, duplicate runs). Plus an x265-encode convenience subcommand that emits an `x265 --dhdr10-info metadata.json` command so x265 embeds HDR10+ SEI at encode time (avoids the inject step). Integrates with ffmpeg hevc_mp4toannexb bitstream filter and mkvmerge/MP4Box. Use when the user asks to author HDR10+ metadata, extract HDR10+ JSON, inject HDR10+ into an HEVC encode, verify HDR10+ SEI presence, plot HDR10+ brightness curves, or work with hdr10plus_tool.
argument-hint: "[subcommand] [args...]"
---

# HDR hdr10plus_tool

**Context:** $ARGUMENTS

## Quick start

- **Extract HDR10+ JSON from HEVC/MKV:** → Step 2 (`hdr10plus.py extract`)
- **Inject HDR10+ into HEVC:** → Step 3 (`hdr10plus.py inject`)
- **Strip HDR10+ from HEVC:** → Step 4 (`hdr10plus.py remove`)
- **Edit HDR10+ JSON with a script:** → Step 5 (`hdr10plus.py editor`)
- **Plot brightness:** → Step 6 (`hdr10plus.py plot`)
- **Build an x265 encode command that embeds HDR10+ at encode time:** → Step 7 (`hdr10plus.py x265-encode`)

## When to use

- User wants to extract HDR10+ metadata from a remux to a Samsung-compatible JSON.
- User is re-encoding with x265 and wants HDR10+ baked in via `--dhdr10-info`.
- User wants to strip HDR10+ or verify its presence.
- User wants to plot the per-frame HDR10+ brightness curve.
- For Dolby Vision (NOT HDR10+), use `hdr-dovi-tool`.
- For doc lookup, use `hdr-dynmeta-docs`.

---

## Step 1 — Install

```bash
cargo install --locked --git https://github.com/quietvoid/hdr10plus_tool
# OR: grab a pre-built binary from Releases
```

Latest at time of writing: **1.7.2 (Dec 2025)**, MSRV **Rust 1.85.0**. Check current: `hdr-dynmeta-docs fetch --page hdr10plus-releases`.

Verify:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py extract --help
```

---

## Step 2 — Extract HDR10+ to JSON

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py extract \
  --input source.hevc --output metadata.json
```

hdr10plus_tool accepts HEVC Annex-B or MKV directly (the tool can demux MKV itself). JSON is in Samsung's HDR10+ format with scene indexing.

---

## Step 3 — Inject HDR10+ into HEVC

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py inject \
  --input source.hevc --json metadata.json --output injected.hevc
```

Input MUST be HEVC Annex-B. Output is HEVC Annex-B; remux via mkvmerge/MP4Box.

---

## Step 4 — Remove HDR10+ from HEVC

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py remove \
  --input source.hevc --output plain.hevc
```

Strips all HDR10+ SEI NAL units. Base HDR10 static metadata (MDCV/MaxCLL/MaxFALL) is untouched — use ffmpeg or MediaInfo to check those.

---

## Step 5 — Edit HDR10+ JSON

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py editor \
  --input metadata.json --config edit.json --output edited.json
```

Edits include: drop frame ranges, duplicate existing runs, splice scenes. JSON edit schema is in `references/edit-schema.md`.

---

## Step 6 — Plot brightness curve

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py plot \
  --input metadata.json --output brightness.png
```

One PNG of per-frame HDR10+ luminance metadata (max RGB / average RGB / distribution percentiles). Useful for sanity-checking edits.

---

## Step 7 — x265-encode (convenience)

Instead of `encode → inject`, let x265 embed HDR10+ SEI at encode time via `--dhdr10-info`. This subcommand just prints the correct `x265` command — it does NOT reimplement x265.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py x265-encode \
  --input source.y4m --metadata metadata.json --output out.hevc \
  --crf 18 --preset slow
```

Emits a command like:

```
x265 --y4m --input source.y4m --crf 18 --preset slow \
     --colorprim bt2020 --transfer smpte2084 --colormatrix bt2020nc \
     --hdr10 --hdr10-opt --repeat-headers \
     --dhdr10-info metadata.json \
     --output out.hevc
```

Then remux:

```bash
mkvmerge -o out.mkv out.hevc
```

---

## Gotchas

- **Input to `inject` MUST be HEVC Annex-B, not MP4/MKV-muxed.** `extract` accepts MKV, but `inject` and `remove` require raw Annex-B. Convert via `ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc out.hevc`.
- **hdr10plus_tool has NO `convert`, `demux`, `mux`, or `extract-rpu` subcommands.** Those are dovi_tool-only. The full hdr10plus_tool set is: `extract`, `inject`, `remove`, `plot`, `editor` — nothing else.
- **Prefer x265's `--dhdr10-info` over inject-after-encode.** Embedding at encode time is a single pass and places SEI correctly. inject is for fixing up existing encodes you can't re-encode.
- **HDR10+ ≠ Dolby Vision.** HDR10+ uses SMPTE 2094-40 SEI NAL units in HEVC; DV uses RPU NAL units (profile-dependent). They can coexist in one stream; one tool handles each. Don't confuse the two.
- **After inject you have raw Annex-B HEVC.** mkvmerge or MP4Box is required to remux. ffmpeg's MP4 muxer for HEVC+HDR10+ is flaky; stick with mkvmerge (for MKV) or MP4Box (for MP4).
- **`remove` does NOT strip HDR10 static metadata.** It only removes HDR10+ dynamic. MaxCLL/MaxFALL/MDCV are separate VUI/SEI fields written by the encoder — use ffmpeg `-bsf:v filter_units` or re-encode without them.
- **JSON from `extract` is Samsung's format.** It's NOT the same as a Dolby Vision editor JSON or a generic metadata dump. Don't mix them.
- **Latest version: 1.7.2 (Dec 2025), Rust MSRV 1.85.0.** Older OS distros ship older Rust; use rustup if cargo fails.
- **The script is stdlib-only Python 3.** Non-interactive; prints every real `hdr10plus_tool` / `ffmpeg` / `mkvmerge` / `MP4Box` / `x265` command to stderr before running. `--dry-run` supported on every subcommand; `x265-encode` defaults to dry-run (prints the command for user review).

---

## Examples

### Example 1 — Extract HDR10+ JSON from an MKV

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py extract \
  --input remux.mkv --output metadata.json
```

### Example 2 — Re-encode a y4m with HDR10+ baked in

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py x265-encode \
  --input master.y4m --metadata metadata.json --output out.hevc \
  --crf 20 --preset slow
# then manually:
mkvmerge -o out.mkv out.hevc
```

### Example 3 — Strip HDR10+ but keep HDR10

```bash
# Extract Annex-B first:
ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc in.hevc
# Strip:
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py remove \
  --input in.hevc --output plain.hevc
# Remux:
mkvmerge -o plain.mkv plain.hevc
```

### Example 4 — Trim HDR10+ to first 10 minutes of a timeline

Author `trim.json`, then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py editor \
  --input metadata.json --config trim.json --output trimmed.json
```

### Example 5 — Sanity-check HDR10+ is still present after remux

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/hdr10plus.py extract --input final.mkv --output - | head -50
# If output shows per-frame entries, HDR10+ survived.
```

---

## Troubleshooting

### `hdr10plus_tool: command not found`

**Solution:** `cargo install --locked --git https://github.com/quietvoid/hdr10plus_tool`, or pre-built from Releases.

### `inject: Failed to parse HEVC stream`

**Cause:** Input was MP4/MKV-muxed HEVC, not Annex-B.
**Solution:** `ffmpeg -i in.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc out.hevc`.

### x265 doesn't accept `--dhdr10-info`

**Cause:** x265 build too old, or `--dhdr10-info` requires HDR10+ support at configure time.
**Solution:** Use a recent x265 (10-bit build). Verify with `x265 --help 2>&1 | grep dhdr10`.

### MKV plays HDR10 but Samsung TV doesn't see HDR10+

**Cause:** Remux dropped the SEI NAL, OR TV's HDR10+ sniffer looks at specific timestamps.
**Solution:** Verify with `hdr10plus.py extract --input final.mkv --output -` — if JSON is populated, SEI is there.

---

## Reference docs

- Verified hdr10plus_tool subcommand catalog → see `hdr-dynmeta-docs` skill's `references/subcommands.md`.
