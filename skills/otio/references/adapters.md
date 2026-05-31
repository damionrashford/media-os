# OTIO Adapter Matrix

OpenTimelineIO (OTIO) is an interchange format for editorial timelines. The core `opentimelineio` package ships three native adapters; the rest live in `OpenTimelineIO-Plugins` meta-package.

## Native adapters (ship with core `pip install opentimelineio`)

| Adapter | File ext | Role | Notes |
|---|---|---|---|
| `otio_json` | `.otio` | Canonical lossless JSON | Use for round-trips; preserves everything. |
| `otiod` | directory | OTIO as a directory | Exploded form; one schema per file. Useful for VCS diffs. |
| `otioz` | `.otioz` | Zipped OTIO + media | Single portable package, bundles clips + referenced media. |

## Community adapters (install via `pip install OpenTimelineIO-Plugins`)

| Adapter | File ext / form | Source NLE | Round-trip fidelity |
|---|---|---|---|
| `cmx_3600` | `.edl` | CMX 3600 EDL (Premiere/Avid/Resolve import) | Low — EDL only carries cut list + timecode. No effects. |
| `fcp_xml` | `.xml` | Final Cut Pro 7 XML (also Premiere Pro legacy) | Medium — clips, tracks, simple effects, markers. |
| `fcpx_xml` | `.fcpxml` | Final Cut Pro X | Medium-high — preserves clip structure, effects. |
| `aaf_adapter` | `.aaf` | Avid Media Composer | Medium — needs `pyaaf2`. Clips, tracks, audio, subclips. |
| `ale` | `.ale` | Avid Log Exchange | Flat clip list metadata (no multi-track). |
| `burnins` | render pipeline | N/A — writes timecode burn-in | Renders metadata overlay to mov via ffmpeg. |
| `maya_sequencer` | Maya scene | Autodesk Maya Camera Sequencer | Converts Maya scene shots to OTIO. |
| `xges` | `.xges` | GStreamer Editing Services | Timeline via GES's XML schema. |
| `svg` | `.svg` | Render OTIO timeline as SVG | One-way output (not round-trippable). |

## Round-trip guidance

Any format → OTIO → same format should preserve essentials. Cross-format round-trips are lossy. Safe graph:

```
FCPXML  ⇄  OTIO  ⇄  FCP7-XML   (most effects lost at hop)
EDL     ⇄  OTIO              (EDL has no effects/audio/transitions)
AAF     ⇄  OTIO              (video/audio tracks yes, effects varies)
```

When in doubt:
1. Convert to `.otio` first with `otioconvert`.
2. Save that as your canonical working copy.
3. Export back out for each target NLE separately.

## Install shorthand

```bash
# Core only (native adapters only)
pip install opentimelineio

# Core + every community adapter
pip install OpenTimelineIO-Plugins

# Single adapter (e.g. just AAF)
pip install opentimelineio opentimelineio-aaf-adapter
```

Installing `OpenTimelineIO-Plugins` also installs `opentimelineio` as a dependency, so you never need both lines in requirements.

## Check what's installed at runtime

```bash
otiopluginfo          # enumerate installed adapters + schemadefs + media linkers + hooks
```

Or in Python:

```python
import opentimelineio as otio
for a in otio.adapters.available_adapter_names():
    print(a)
```

## Adapter-specific gotchas

- **`cmx_3600` (EDL):** source_in/source_out are in SOURCE timecode, not timeline timecode. Audio-only EDLs use `NONE` for source file.
- **`fcp_xml` vs `fcpx_xml`:** FCP7 XML is legacy flat-structure; FCPX uses `<ref-clip>` + `<asset>` + compound clips. Do NOT assume they're interchangeable — use the right adapter for the right NLE.
- **`aaf_adapter`:** Needs `pyaaf2` (C library with Python bindings). On some systems `pip install pyaaf2` fails — use the conda-forge version or Avid's build.
- **`xges` (GStreamer Editing Services):** GES uses nested `GESUriClip` for media and `GESGroup` for compound. Round-trip through OTIO flattens groups in some cases.
- **`maya_sequencer`:** one-direction (Maya → OTIO). To push edits back to Maya, use Maya's Python API directly.
