# OpenTimelineIO convert

**Triggers:** convert a Final Cut XML to Premiere, read an AAF, author an EDL, translate between NLE formats, filter an OTIO timeline programmatically, extract timeline stats, view a timeline. Round-trip between Premiere Pro, Final Cut Pro 7/X, Avid Media Composer, DaVinci Resolve, GStreamer Editing Services via otioconvert / otiocat / otiostat / otiotool / otiopluginfo / otioview.

## Quick start

- **Convert between NLE formats:** → Step 2 (`otio.py convert`)
- **Print / concat OTIO files:** → Step 3 (`otio.py cat`)
- **Timeline stats (track count, duration, clip count):** → Step 4 (`otio.py stat`)
- **Filter/edit timeline programmatically:** → Step 5 (`otio.py tool`)
- **List installed adapters / plugins:** → Step 6 (`otio.py plugins`)
- **View a timeline in Qt viewer:** → Step 7 (`otio.py view`)

## When to use

- User has an NLE file (EDL, FCP7 XML, FCPXML, AAF, ALE, XGES) and needs another format.
- User wants to inspect/stat/cat OTIO timelines from the shell.
- User wants to filter or transform a timeline (drop a track, trim a range, rebuild).
- User wants to know what adapters are installed.
- For deeper Python API details or class references, use the docs-search reference instead.

---

## Step 1 — Install the CLIs

OTIO is a pip package. Install core + every community adapter:

```bash
pip install OpenTimelineIO-Plugins   # installs opentimelineio core automatically
```

This gives you on PATH: `otioconvert`, `otiocat`, `otiostat`, `otiotool`, `otiopluginfo`, `otioview` (Qt; needs PyQt/PySide installed separately — `pip install PyOpenTimelineIO[view]`).

Verify install:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py plugins
```

---

## Step 2 — Convert formats

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py convert \
  --input edit.fcpxml --output edit.otio
```

Format is auto-detected from the file extension. Shortcut aliases for common source→destination pairs:

| Alias | Source → Dest |
|---|---|
| `fcp7-to-fcpx` | `.xml` (FCP7) → `.fcpxml` |
| `fcpx-to-fcp7` | `.fcpxml` → `.xml` |
| `edl-to-otio` | `.edl` → `.otio` |
| `otio-to-edl` | `.otio` → `.edl` |
| `aaf-to-otio` | `.aaf` → `.otio` |

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py convert \
  --input cut.edl --output cut.otio --preset edl-to-otio
```

The wrapper prints the real `otioconvert` command to stderr before running it; `--dry-run` echoes without executing.

---

## Step 3 — Cat / print timelines

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py cat --input edit.otio
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py cat --input a.otio --input b.otio --output combined.otio
```

Pass-through for `otiocat`: multiple `--input` = concatenate in order.

---

## Step 4 — Stats

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py stat --input edit.otio
```

Prints track count, clip count, total duration, start/end time ranges — matches `otiostat` output.

---

## Step 5 — Transform with otiotool

`otiotool` is the surgical-edit multi-tool. The wrapper passes args through:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py tool \
  --input edit.otio --output flat.otio \
  -- --flatten video --remove-transitions
```

Everything after `--` is forwarded verbatim to `otiotool`. Common flags:

| otiotool flag | Effect |
|---|---|
| `--flatten video` | collapse video tracks into one |
| `--flatten audio` | collapse audio tracks into one |
| `--remove-transitions` | drop all Transition objects |
| `--trim START END` | crop global timeline range |
| `--copy-media-refs-from FILE` | borrow media references from another OTIO |
| `--redact` | strip clip names (useful for sharing timelines) |

Consult `otiotool --help` for the full list.

---

## Step 6 — Plugin info

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py plugins
```

Enumerates: adapters, media linkers, schemadefs, hooks. Use to confirm an adapter (e.g. `aaf_adapter`, `fcpx_xml`) is installed before attempting conversion.

---

## Step 7 — View

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py view --input edit.otio
```

Launches `otioview` Qt GUI (macOS/Windows/Linux with Qt). Needs `PyOpenTimelineIO[view]` installed.

---

## Gotchas

- **`OpenTimelineIO-Plugins` is the right install for NLE round-trips.** Just `pip install opentimelineio` gives you ONLY native `otio_json` / `otiod` / `otioz` adapters — no EDL, no FCP7 XML, no AAF.
- **AAF adapter needs `pyaaf2`.** On some systems `pip install pyaaf2` has native-build hurdles. Try conda-forge: `conda install -c conda-forge pyaaf2`.
- **Extension → adapter mapping is strict.** `.edl` → `cmx_3600`, `.xml` → `fcp_xml` (NOT FCPXML), `.fcpxml` → `fcpx_xml`, `.aaf` → `aaf_adapter`, `.otio`/`.otiod`/`.otioz` → native. Passing a FCPX .fcpxml file with `.xml` extension will misroute to FCP7 adapter.
- **Round-trips lose data.** EDL has no effects, no audio metadata, no generators. FCP7↔FCPX drops clip IDs. AAF↔OTIO drops some effect parameter keyframes. `.otio` is the only lossless canonical format — hop through it.
- **`otioconvert --input-adapter` and `--output-adapter` override extension detection** when the filename doesn't match (e.g. EDL with `.txt` extension): `otioconvert -i cut.txt --input-adapter cmx_3600 -o cut.otio`.
- **`otiotool` is NOT a round-trip tool; it's an in-place transform.** It reads OTIO, applies transforms, writes OTIO. To transform an EDL → trimmed EDL, convert EDL→OTIO, run otiotool, convert OTIO→EDL.
- **Track kind is case-sensitive: `"Video"` / `"Audio"`.** `otiotool --flatten video` is lowercase arg, but the internal track.kind string is `"Video"`. Don't mix up.
- **`otioview` needs Qt.** Headless boxes (CI, SSH) can't run it. Use `otiostat` + `otiocat` for text-only inspection.
- **RationalTime is rate-aware.** `otiostat` prints durations as `value@rate` pairs. A 24fps timeline of 10 seconds shows `240@24`, NOT `10.0`. Don't interpret as seconds — divide by rate.
- **The script is stdlib-only.** It wraps the pip-installed OTIO CLIs — it doesn't reimplement OTIO logic.

---

## Examples

### Example 1 — FCPXML from Final Cut Pro → Premiere-compatible FCP7 XML

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py convert \
  --input cut.fcpxml --output cut.xml --preset fcpx-to-fcp7
```

Premiere imports both, but FCP7 XML is the stable round-trip.

### Example 2 — EDL → OTIO → quick stats

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py convert --input cut.edl --output cut.otio
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py stat --input cut.otio
```

### Example 3 — Flatten all video tracks into one

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py convert --input edit.fcpxml --output edit.otio
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py tool \
  --input edit.otio --output flat.otio -- --flatten video
```

### Example 4 — Concat two cuts into one timeline

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py cat \
  --input scene1.otio --input scene2.otio --output reel.otio
```

### Example 5 — Check AAF adapter is installed

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/otio.py plugins | grep aaf
```

---

## Troubleshooting

### `No adapter available for file 'foo.aaf'`

**Cause:** `aaf_adapter` not installed (or `pyaaf2` broken).
**Solution:** `pip install OpenTimelineIO-Plugins` (gets everything). If AAF still fails: `pip install pyaaf2` first.

### `otioview: command not found`

**Cause:** Qt/viewer extras not installed.
**Solution:** `pip install 'PyOpenTimelineIO[view]'` or install PyQt5/PySide2 manually.

### EDL round-trip loses frame rates

**Cause:** EDL headers don't carry rate; `cmx_3600` adapter defaults to 24fps.
**Solution:** Pass `--rate 29.97` (or whatever) to `otioconvert` via `otio.py convert ... -- --rate 29.97`, or include a leader with rate in the EDL header.

### Extension mismatch — `.xml` file treated as FCP7 but is actually FCPX

**Solution:** Pass explicit adapter: `otioconvert -i weird.xml --input-adapter fcpx_xml -o out.otio`. Or rename file to `.fcpxml` first.

### Wrapper prints `otioconvert: command not found`

**Solution:** Install OTIO: `pip install OpenTimelineIO-Plugins`. Make sure the venv is active (`which otioconvert`).

---

## Reference docs

- Full adapter matrix (round-trip fidelity) + install notes → see `references/adapters.md`.
- `otiotool` transform catalog → `references/otiotool.md`.
