# OTIO Docs — Page Catalog

## Tutorials (HTML, readthedocs)

| Page | URL | Purpose |
|---|---|---|
| `tut-quickstart` | `.../tutorials/quickstart.html` | Read / write / inspect an OTIO file from Python. |
| `tut-timeline-structure` | `.../tutorials/otio-timeline-structure.html` | Timeline / Stack / Track / Clip / Gap / Transition hierarchy. |
| `tut-time-ranges` | `.../tutorials/time-ranges.html` | `RationalTime`, `TimeRange`, rate-aware arithmetic. |
| `tut-adapters` | `.../tutorials/adapters.html` | How adapters plug in; where to find each format. |
| `tut-schemadef` | `.../tutorials/write-a-schemadef-plugin.html` | Author a custom schema extension plugin. |

## Python API reference (HTML, readthedocs)

| Page | Module | Notable contents |
|---|---|---|
| `api-py-root` | `opentimelineio` | Package root; import tree. |
| `api-opentime` | `opentimelineio.opentime` | `RationalTime`, `TimeRange`, `TimeTransform`, conversion utils. |
| `api-core` | `opentimelineio.core` | `SerializableObject`, `SerializableCollection`, `Composable`, `Composition`. |
| `api-schema` | `opentimelineio.schema` | `Timeline`, `Stack`, `Track`, `Clip`, `Gap`, `Transition`, `Marker`, `Effect`, `MediaReference`, `MissingReference`, `ExternalReference`, `GeneratorReference`, `ImageSequenceReference`. |
| `api-algorithms` | `opentimelineio.algorithms` | `track_trimmed_to_range`, `stack_trimmed_to_range`, `timeline_trimmed_to_range`. |
| `api-media-linker` | `opentimelineio.media_linker` | Hook to resolve `MissingReference` → `ExternalReference` when reading timelines. |
| `api-hooks` | `opentimelineio.hooks` | Pre/post-adapter hook registration. |
| `api-adapters-root` | `opentimelineio.adapters` | Adapter discovery + `write_to_file`, `read_from_file`, `write_to_string`, `read_from_string`. |
| `api-plugins-root` | `opentimelineio.plugins` | Plugin manifest + `Plugin` / `PythonPlugin` + manifest schema. |
| `api-versioning` | `opentimelineio.versioning` | Schema-version up/downgrade utilities for OTIO JSON. |

## GitHub READMEs (raw Markdown)

| Page | URL | Purpose |
|---|---|---|
| `github-readme` | `github.com/AcademySoftwareFoundation/OpenTimelineIO` | Canonical repo README. ASWF-hosted; source of truth. |
| `plugins-readme` | `github.com/OpenTimelineIO/OpenTimelineIO-Plugins` | Meta-package bundling community adapters (cmx_3600, fcp_xml, fcpx_xml, aaf, ale, burnins, xges, svg, maya_sequencer). |

## Notes on versioning

- OTIO's JSON schema has a versioning system (see `api-versioning` page). When you open a file authored with newer OTIO on older OTIO, opentimelineio.versioning downgrades if possible.
- The native `otio_json` adapter always writes the current schema version. Use `SchemaVersionMap` in `versioning` to target an older reader.

## Repo relocation note

The repo moved from `PixarAnimationStudios/OpenTimelineIO` to `AcademySoftwareFoundation/OpenTimelineIO` when OTIO joined the Academy Software Foundation. Old URLs redirect; always cite the ASWF location.

## CLI reference absence

Readthedocs does NOT publish HTML pages for `otioconvert` / `otiocat` / `otiostat` / `otiotool` / `otiopluginfo` / `otioview`. The only authoritative CLI reference is `--help` on each tool. For CLI workflow, see the `otio-convert` skill.
