---
name: vfx-usd
description: >
  Author and inspect Pixar Universal Scene Description (USD) files: usdcat (print/convert between .usda ASCII / .usdc crate binary / .usdz package), usdview (interactive Qt viewer), usdedit (round-trip edit via ASCII), usdzip (create/inspect .usdz AR packages), usdrecord (offline Hydra render to image sequence), usdresolve (asset path resolution), usdtree (stage hierarchy), usdchecker (validate schema + packaging), usddiff (structural diff), usdstitch / usdstitchclips (value-clip assembly), usdGenSchema (generate schema bindings). Core concepts: Stage, Layer, Prim, Attribute, Relationship, Composition Arcs (sublayer/reference/payload/inherit/specialize/variantSet - LIVRPS strength ordering). Schemas: UsdGeom, UsdLux, UsdShade, UsdSkel, UsdPhysics, UsdMedia, UsdRender, UsdVol, UsdUI. Docs at openusd.org/release/. Use when the user asks to work with USD files, convert between USD flavors, render a USD scene, validate USD for Apple AR delivery (.usdz), or author USD programmatically.
argument-hint: "[action]"
---

# Vfx Usd

**Context:** $ARGUMENTS

## Quick start

- **Convert between .usda / .usdc / .usdz:** -> Step 1 (`usd.py cat`)
- **Inspect a stage hierarchy:** -> Step 2 (`usd.py info`)
- **Validate for delivery (Apple .usdz, studio pipeline):** -> Step 3 (`usd.py validate`)
- **Render a frame sequence from a stage:** -> Step 4 (`usd.py record`)
- **Pack a folder of assets into .usdz:** -> Step 5 (`usd.py zip`)
- **Diff two stages:** -> Step 6 (`usd.py diff`)
- **Resolve an asset path:** -> Step 7 (`usd.py resolve`)
- **Interactive viewer:** -> Step 8 (`usd.py view`)
- **Assemble value clips:** -> Step 9 (`usd.py stitch-clips`)

## When to use

- User mentions Pixar USD, OpenUSD, .usd/.usda/.usdc/.usdz files, Hydra rendering, AR asset export.
- Validating a USD for Apple Quick Look AR delivery (.usdz).
- Converting between ASCII (.usda) and binary (.usdc) crate forms.
- Rendering an offline image sequence from a camera prim.
- Inspecting composition arcs (sublayer/reference/payload/inherit/specialize/variantSet).

---

## Step 1 — Convert between USD formats

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py cat --in scene.usdc --out scene.usda
```

Under the hood:

```bash
usdcat scene.usdc -o scene.usda
```

Use `--flatten` to resolve all composition arcs into a single layer (baking references/payloads/variants into the output):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py cat --in scene.usda --flatten --out scene_flat.usda
```

Format is auto-detected from the output extension: `.usda` -> ASCII, `.usdc` -> crate binary, `.usdz` -> package.

---

## Step 2 — Inspect a stage

Hierarchy + attribute summary:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py info scene.usda
```

Runs both:

```bash
usdtree scene.usda        # prim hierarchy
usdchecker scene.usda     # schema + packaging validation
```

---

## Step 3 — Validate

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py validate scene.usdz
```

Expands to:

```bash
usdchecker --strict scene.usdz
```

For Apple AR Quick Look .usdz delivery, add `--arkit`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py validate --arkit model.usdz
# -> usdchecker --arkit --strict model.usdz
```

---

## Step 4 — Offline render (Hydra)

Render N frames through a named camera prim, write to PNG sequence:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py record \
  --in scene.usda \
  --camera /World/MainCam \
  --out render.####.png \
  --frames 1-240
```

Expands to:

```bash
usdrecord --camera /World/MainCam --frames 1:240 scene.usda render.####.png
```

Options: `--imageWidth 1920`, `--renderer Storm|Embree|Arnold|Karma|RenderMan`.

---

## Step 5 — Zip / unzip a .usdz package

Pack a folder (root layer + referenced textures) into .usdz:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py zip --dir ./asset/ --out asset.usdz
```

Extract contents:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py unzip --in asset.usdz --dest ./asset/
```

Under the hood: `usdzip`, or on extract `unzip` / Python's `zipfile` (.usdz is just a zip).

---

## Step 6 — Diff two stages

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py diff a.usda b.usda
```

Expands to `usddiff a.usda b.usda`. Structural diff — compares opinions by spec path, not line-by-line text.

---

## Step 7 — Resolve an asset path

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py resolve "./textures/diffuse.<UDIM>.png"
```

Expands to `usdresolve "./textures/diffuse.<UDIM>.png"`. Honors the current `PXR_PLUGINPATH_NAME` / `USD_RESOLVER` configuration. Useful for verifying that asset path templates resolve correctly in your pipeline.

---

## Step 8 — Interactive viewer

Launch `usdview` on a stage:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py view scene.usda
```

Requires Qt/PySide display; blocks until you quit. Skip on headless CI.

---

## Step 9 — Stitch value clips

Animated "value clips" decouple per-frame layer swaps from the root layer. Build a manifest:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py stitch-clips \
  --clips-dir ./clips/ \
  --topology topology.usd \
  --out manifest.usd
```

Expands to `usdstitchclips --clipPath /Set --templatePath ./clips/frame.####.usd --startTimeCode 1 --endTimeCode 240 --out manifest.usd`.

---

## Gotchas

- **Canonical docs live at `https://openusd.org/release/`**, NOT `/docs/`. The `/docs/` path returns 404. Pages you care about: `/release/index.html`, `/release/intro.html`, `/release/glossary.html`, `/release/toolset.html`, `/release/tut_usd_tutorials.html`. Quickstart PDF at `/files/USD_Quickstart_Guide.pdf`.
- **Only four file extensions are canonical:** `.usd` (generic — auto-picks crate or ASCII at read time), `.usda` (explicitly ASCII), `.usdc` (crate binary), `.usdz` (zip package). `.usdnc` is NOT a standard Pixar extension — don't recommend it.
- **Composition arcs have a strict strength order: LIVRPS**
  Local > Inherits > VariantSets > References > Payloads > Specializes. Stronger opinions override weaker ones. This is the most common pipeline footgun ("my edit isn't showing up" = there's a stronger opinion elsewhere).
- **`.usdz` is just a ZIP with zero compression and specific alignment.** The alignment is what `usdzip` does that plain `zip` cannot — do NOT build .usdz with plain `zip`, Quick Look will reject it.
- **Apple's `--arkit` validator is stricter than default.** Rejects PBR textures outside 8-bit range, requires triangulated meshes, limits shader support to `UsdPreviewSurface`. Always re-validate with `--arkit` before Apple submission.
- **Tool list verified from `openusd.org/release/toolset.html`:** `usdcat`, `usdview`, `usdedit`, `usdzip`, `usdrecord`, `usdresolve`, `usdtree`, `usdchecker`, `usddiff`, `usdstitch`, `usdstitchclips`, `usdGenSchema`, `usdgenschemafromsdr`. No "usdconv" or "usdexport" — those are NOT official tools.
- **Schema docs split between user-guides and Doxygen API:** UsdLux, UsdMedia, UsdRender, UsdUI, UsdVol have TOCs on `/release/`. UsdGeom, UsdShade, UsdSkel, UsdPhysics only have API pages like `/release/api/usd_geom_page_front.html`. Read `references/schemas.md` for one-liner summaries.
- **`usdview` requires a Qt display.** Won't work in headless CI; use `usdrecord` for offline render instead.
- **Crate `.usdc` is version-stamped.** A .usdc written by USD 24.x may fail to load on 23.x. Convert to `.usda` for forward-compat or ship the matching USD runtime.
- **References vs Payloads:** References are always loaded; Payloads are loaded on demand (`stage.Load()` / `stage.Unload()`). Use Payloads for heavy environment/city models. Don't mix them up — the loading semantics differ.

---

## Examples

### Example 1: "Convert a binary crate to ASCII for git diffs"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py cat --in scene.usdc --out scene.usda
```

### Example 2: "Validate this .usdz for Apple Quick Look"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py validate --arkit model.usdz
```

### Example 3: "Render frames 1-120 from the hero camera"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py record \
  --in shot.usda --camera /Render/Cameras/hero \
  --frames 1-120 --out shot.####.png \
  --imageWidth 1920 --renderer Storm
```

### Example 4: "Pack this asset folder into a shareable .usdz"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py zip --dir ./hero_prop/ --out hero_prop.usdz
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py validate --arkit hero_prop.usdz
```

### Example 5: "Flatten all composition into one file for a hand-off"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/usd.py cat --in shot.usda --flatten --out shot_flat.usda
```

---

## Troubleshooting

### Error: `usdcat: command not found`

**Cause:** USD runtime isn't installed / not on PATH.
**Solution:** Install via NVIDIA's build, `brew install usd-core`, `pip install usd-core` (limited Python bindings), or build from source at github.com/PixarAnimationStudios/OpenUSD.

### Error: `usdchecker --arkit FAILED`

**Cause:** Apple-specific constraint (often non-triangulated mesh, missing UsdPreviewSurface, wrong texture color space, non-1-meter scale).
**Solution:** Read the error; common fixes: triangulate in DCC before export, convert all shaders to `UsdPreviewSurface`, embed textures, set `metersPerUnit=1`.

### `.usdz` opens in finder but not Quick Look

**Cause:** Built with plain `zip` (wrong alignment) or includes a directory entry.
**Solution:** Rebuild with `usdzip`, not `zip`. Don't include `__MACOSX/` or `.DS_Store`.

### Error: `Layer version too new`

**Cause:** `.usdc` written by a newer USD runtime than the reader.
**Solution:** Convert sender-side: `usdcat new.usdc -o old.usda`. Or upgrade reader.

### My override isn't showing up

**Cause:** Stronger opinion exists up the LIVRPS chain.
**Solution:** Use `usdview` → Composition tab, or `usd.py info`, to find who's "winning". Often a variantSet or specializes arc is overriding your layer.

### `usdrecord` hangs on first frame

**Cause:** Hydra renderer loading plugins. Some renderers (Arnold) take 10-30s on first invocation.
**Solution:** Wait. Pre-warm by rendering a tiny scene first, or switch to Storm (`--renderer Storm`) for speed.

---

## Reference docs

- **Core concepts cheatsheet** (Stage / Layer / Prim / Attribute / Relationship / Composition Arcs / LIVRPS) -> [`references/concepts.md`]
- **Schema one-liners** (UsdGeom / UsdLux / UsdShade / UsdSkel / UsdPhysics / UsdMedia / UsdRender / UsdVol / UsdUI) -> [`references/schemas.md`]
