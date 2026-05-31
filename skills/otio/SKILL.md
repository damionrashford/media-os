---
name: otio
description: >
  OpenTimelineIO (OTIO) editorial timeline conversion, inspection, transformation, and docs lookup. Use when the user asks to convert a Final Cut XML to Premiere, read an AAF, author or round-trip an EDL, translate between NLE formats (EDL, FCP7-XML, FCPXML, AAF, ALE, XGES, OTIO-JSON), round-trip between Premiere Pro, Final Cut Pro 7/X, Avid Media Composer, DaVinci Resolve, or GStreamer Editing Services, filter or flatten or trim an OTIO timeline programmatically, extract timeline stats (track/clip count, duration), concatenate or print OTIO files, list installed OTIO adapters, view a timeline, look up an OTIO class or Python binding (RationalTime, TimeRange, Timeline, Stack, Track, Clip, Gap, Transition, MediaReference), find which adapter handles a NLE format, or read OpenTimelineIO documentation. Wraps otioconvert, otiocat, otiostat, otiotool, otiopluginfo, otioview plus a readthedocs/GitHub docs searcher.
argument-hint: "[src] [dst]"
---

# OTIO

OpenTimelineIO (OTIO) is the interchange format for editorial timelines. This skill converts and transforms timelines via the OTIO CLIs and looks up OTIO docs to ground every adapter/class claim.

## When to use

- Convert an NLE file (EDL, FCP7 XML, FCPXML, AAF, ALE, XGES) to another format, or round-trip through `.otio`.
- Inspect a timeline from the shell — stats, cat, plugin list.
- Filter or transform a timeline (flatten tracks, drop transitions, trim a range, redact clip names).
- Look up an OTIO class, Python binding, or adapter before writing OTIO code or naming an adapter.
- Read OpenTimelineIO documentation (tutorials, Python API, adapter catalog).

## Techniques

Read `references/convert.md` when converting, concatenating, stat-ing, transforming, listing plugins, or viewing timelines with the `scripts/otio.py` wrapper (`convert` / `cat` / `stat` / `tool` / `plugins` / `view`). It covers the install, extension→adapter mapping, presets, and `otiotool` flags.

Install the CLIs first: `pip install OpenTimelineIO-Plugins` (auto-installs `opentimelineio` core plus EDL/FCP7/FCPXML/AAF/ALE/XGES adapters). Plain `pip install opentimelineio` gives only native `otio_json`/`otiod`/`otioz`.

## Docs lookup

Before naming an OTIO adapter, class, method, or serialization field — verify it, do not recall from memory. This is the anti-hallucination guard.

Read `references/docs-search.md` for the workflow, then run `scripts/otiodocs.py` (`search` / `section` / `fetch` / `list-pages` / `index`) against opentimelineio.readthedocs.io + github.com/AcademySoftwareFoundation/OpenTimelineIO. Full adapter matrix in `references/adapters.md`; page/URL catalog in `references/pages.md`.

## Gotchas

- **`OpenTimelineIO-Plugins` is the install for NLE round-trips.** Plain `opentimelineio` core ships ONLY native `otio_json`/`otiod`/`otioz` — no EDL, FCP7 XML, FCPXML, or AAF.
- **Extension→adapter mapping is strict.** `.edl`→`cmx_3600`, `.xml`→`fcp_xml` (FCP7, NOT FCPXML), `.fcpxml`→`fcpx_xml`, `.aaf`→`aaf_adapter`. A FCPX file saved as `.xml` misroutes to the FCP7 adapter — pass `--input-adapter fcpx_xml` to override.
- **`.otio` is the only lossless canonical format.** Hop through it. EDL drops effects/audio metadata/generators; FCP7↔FCPX drops clip IDs; AAF↔OTIO drops some effect keyframes.
- **`otiotool` is an in-place transform, not a converter.** It reads OTIO → transforms → writes OTIO. To trim an EDL: EDL→OTIO, otiotool, OTIO→EDL.
- **Track kind is case-sensitive: `"Video"` / `"Audio"`.** Lowercase is the #1 "no clips found" bug. (`otiotool --flatten video` takes the lowercase arg, but `track.kind` is `"Video"`.)
- **`RationalTime` is rate-aware, not a float.** `otiostat` prints `240@24` for 10s at 24fps — divide by rate. Do arithmetic in native rate; `rescaled_to()` to convert; never collapse to seconds early.
- **`Clip.media_reference` can be `MissingReference`, not `None`.** Check `isinstance(..., MissingReference)` before treating media as loaded.
- **AAF adapter needs `pyaaf2`.** If `OpenTimelineIO-Plugins` install fails on AAF only, `pip install pyaaf2` first (or conda-forge); `otioview` additionally needs Qt and can't run headless.
- **Canonical repo is AcademySoftwareFoundation/OpenTimelineIO** (ASWF). Old `PixarAnimationStudios` URLs redirect but are stale — don't cite them.

## Scripts

- `scripts/otio.py` — wraps `otioconvert`/`otiocat`/`otiostat`/`otiotool`/`otiopluginfo`/`otioview`. Subcommands: `convert`, `cat`, `stat`, `tool`, `plugins`, `view`. Each supports `--dry-run`/`--verbose`. See `references/convert.md`.
- `scripts/otiodocs.py` — searches/fetches OTIO readthedocs + GitHub docs. Subcommands: `search`, `section`, `fetch`, `list-pages`, `index`, `clear-cache`. See `references/docs-search.md`.

Both are stdlib-only and run via `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>.py`.
