---
name: ffmpeg-composite
description: >
  Compositing, keying, masking, channel surgery, immersive/3D reprojection,
  procedural expression filters, and synthetic test media with ffmpeg. Use when
  the user asks to do a greenscreen, remove a green or blue background, chroma
  key, key out a color, composite a subject onto a new background, fix spill,
  layer transparent video; composite with masks, extract or merge alpha,
  manipulate YUV/RGB/alpha planes, roto-style composite, displacement map,
  remap pixels, split and recombine channels; convert 360 projections,
  equirectangular to cubemap, unwrap fisheye, side-by-side to top-bottom,
  anaglyph 3D, reproject VR180/VR360; build a custom per-pixel or per-sample
  filter, apply math to samples, render SVG over video, make a real-time debug
  graph, simulate feedback, write arbitrary expressions; generate test bars and
  tone, SMPTE color bars, a sine tone, silence, a solid-color background, a
  1 kHz reference tone, or synthetic assets for pipeline testing.
argument-hint: "[task] [input]"
---

# ffmpeg Composite

**Context:** $ARGUMENTS

Compositing, keying, masking, channel/plane operations, 360/stereoscopic reprojection, procedural expression filters, and synthetic lavfi source generation — all in one skill. Pick the technique below and read its reference for the full playbook (steps, gotchas, examples, troubleshooting).

Always invoke `ffmpeg-docs` first to confirm any filter, option, or flag before recommending it — it is the anti-hallucination guardrail.

## When to use

- **Greenscreen / chroma key** — remove a green or blue background, despill, composite a keyed subject onto a new background, deliver transparent (ProRes 4444 / VP9-alpha / PNG sequence).
- **Advanced compositing & masks** — masked merge through a matte, alpha merge/extract, premultiply math, displacement warp, plane surgery (extract/merge/shuffle planes), chromatic aberration, Photoshop blend modes, floodfill, edge hysteresis.
- **360 / VR & stereoscopic 3D** — convert between equirect / cubemap / EAC / fisheye projections, unwrap dual-fisheye, virtual-camera flat crop, SBS↔TAB, anaglyph, HDMI frame packing, VR180.
- **Procedural / expression filters** — hand-written per-pixel (`geq`), per-sample (`aeval`), two-input (`lut2`), metadata graph (`drawgraph`), SVG overlay (`drawvg`), feedback, lagfun trails.
- **Synthetic test media** — SMPTE bars + tone, test patterns, solid colors, gradients, mandelbrot, noise, silence, identity Hald CLUTs, colorchecker, for calibration and pipeline tests.

## Techniques

- Read `references/chromakey.md` when keying a green/blue screen, despilling, compositing a subject onto a new background, or exporting a transparent mezzanine. Then read `references/chromakey-filters.md` for per-filter option tables, alpha-capable codec/container choices, chromakey vs colorkey vs hsvkey, and real-world green/blue hex samples.
- Read `references/compose-mask.md` when compositing through a mask, plumbing alpha, doing plane surgery, displacement warps, blend modes, floodfill, or edge hysteresis. Then read `references/compose-mask-filters.md` for option tables, the pre/un-premultiply decision tree, plane-selector hex notation, and the recipe book.
- Read `references/360-3d.md` when converting 360 projections, unwrapping fisheye, doing virtual-camera crops, or converting stereoscopic layouts (SBS/TAB/anaglyph/framepack/VR180). Then read `references/360-3d-projections.md` for the full v360 type table, stereo3d code table, framepack options, and VR platform matrix.
- Read `references/geq-expr.md` when writing custom per-pixel/per-sample/two-input math, metadata graphs, SVG overlays, feedback, or lagfun. Then read `references/geq-expr-expressions.md` for the full grammar, geq constant table, store/load slots, 50+ recipes, and the drawgraph metric catalog.
- Read `references/synth.md` when generating bars+tone, test patterns, colors, gradients, noise, silence, Hald CLUTs, or other synthetic assets. Then read `references/synth-sources.md` for per-source option tables, color names, aevalsrc grammar, and the recipe gallery.

## Gotchas

- **Alpha needs an alpha-capable codec AND container.** MP4 + libx264 silently drops alpha. Use MOV (ProRes 4444 `-profile:v 4444`, qtrle), MKV (ffv1), WebM (libvpx-vp9 `-pix_fmt yuva420p`), or a PNG sequence. Verify the output with `ffprobe -show_entries stream=pix_fmt`.
- **Key pipeline order is KEY → DESPILL → COMPOSITE, never composite first.** Pure-green `0x00FF00` is almost never the real screen color (typical `0x20B040`–`0x3EB34C`); sample the source. `blend=0` gives aliased edges — always raise it slightly. Prefer `yuva444p` over `yuva420p` for clean hair edges.
- **Multi-input filters need matched width, height, and pixel format.** Scale + `format=` each branch first. `maskedmerge`/`displace` are 3-input and positional (source0, source1, mask) — reordering silently produces garbage. Masks must be single-plane `format=gray`.
- **`mergeplanes` hex selector** is `(plane_idx << 4) | input_idx` per byte; `shuffleplanes=a:b:c:d` indexes planes of input 0 only. Run `geq`/`blend`/`rgbashift` color ops through `format=gbrp` first or they operate on packed bytes / wrong color space.
- **v360 grammar is positional:** `v360=INPUT_TYPE:OUTPUT_TYPE:opt=val`. Always pass `:cubic` or `:lanczos` — default `linear` leaves cube-seam artifacts. `ih_fov`/`iv_fov` are required for fisheye inputs; `h_fov`/`v_fov` only affect rectilinear outputs. ffmpeg cannot write the SphericalVideo metadata box — use Google's spatial-media tool after rendering or platforms play it as flat 2D.
- **Expression filters silently emit black frames on a parse error** — run `-loglevel debug`, search for `Error when evaluating`, and test with `-t 2` first. `geq` is 10–100× slower than native filters; prefer `vignette`/`curves`/`colorchannelmixer` when they suffice. Inside `geq` coordinates are `X`/`Y` (uppercase); cache repeats with `st()`/`ld()`.
- **Synthetic lavfi sources run forever** unless bounded by `-t N` or `duration=N` (prefer `-t`). Each source needs its own `-f lavfi` before its `-i`; the expression is filter syntax, not a filename. Use `smptehdbars` (not `smptebars`) for HD, set `size=WxH` explicitly, and add `-frames:v 1` for still images.

## Scripts

All scripts are stdlib-only, support `--dry-run`/`--verbose`, and print the exact ffmpeg command. Invoke with `uv run ${CLAUDE_SKILL_DIR}/scripts/<file>` (or `python3`).

- `scripts/key.py` — `key` / `composite` / `identity-transparent`; picks an alpha-capable codec from the output extension. (chromakey)
- `scripts/compose.py` — `mask-merge` / `alpha-merge` / `alpha-extract` / `displace` / `planes` / `blend` / `rgbashift`. (compose-mask)
- `scripts/immersive.py` — `project` / `flat-view` / `stereo3d` / `anaglyph` / `framepack`. (360-3d)
- `scripts/expr.py` — `geq` / `aeval` / `lut2` / `drawgraph` / `feedback` / `lagfun`; autodetects RGB vs YUV for `geq`. (geq-expr)
- `scripts/synth.py` — `bars` / `test-pattern` / `color` / `tone` / `noise` / `silence` / `hald-identity`. (synth)
