# USD core-concepts cheatsheet

Load when the user asks what a Stage / Layer / Prim / Attribute / Relationship / Composition Arc is.

Source: `https://openusd.org/release/glossary.html`, `/release/intro.html`.

## Stage

The in-memory composed view of a set of Layers. A Stage has a root layer
(the file you opened) plus all layers composed into it via arcs.
`Usd.Stage.Open(path)` in Python, `UsdStage::Open` in C++.

## Layer

A single file on disk (`.usda` ASCII / `.usdc` crate binary / `.usdz` package).
Layers contain **opinions** keyed by (prim path, field). Layers are the
editable units; the Stage is the computed merge.

## Prim

A namespaced object in the stage hierarchy (the nodes of the scene graph).
Identified by a path like `/World/Hero/Geom`. Prims have a **type** (e.g.
`Xform`, `Mesh`, `Camera`, `Scope`). `Scope` = pure grouping, no transform.

## Attribute

Typed data on a prim. Examples: `points` (point3f[]), `extent` (float3[]),
`xformOp:translate` (double3). Attributes can hold a **default** value or
**timeSamples** (keyframes). Types are declared — strongly typed schema.

## Relationship

A typed connection from a prim/attribute to another target path. Examples:
material bindings (`material:binding`), shader-network connections, light
link lists. Unlike attributes, relationships don't carry data — they
carry *references* to other spec paths.

## Composition Arcs (LIVRPS strength order)

In decreasing order of strength (stronger wins):

1. **Local** — direct opinions in the current layer.
2. **Inherits** — class-like inheritance; opinions flow down.
3. **VariantSets** — named variants, one selected at a time (LOD, char skin, etc.).
4. **References** — "include this other asset here" (always loaded).
5. **Payloads** — like References but loaded on demand (`stage.Load` / `Unload`).
6. **Specializes** — "fallback" arc; only wins if nothing stronger exists.

**Sublayers** are a separate mechanism: layers stacked within one
LayerStack. Sublayer order is strength-ordered (earlier = stronger) but
the whole LayerStack is composed as "Local".

### Debugging strength

```bash
# Find out who won for a given path+field:
usdview scene.usda   # -> Composition tab -> pick prim -> see the arc stack
# Or programmatically:
python -c "from pxr import Usd; s = Usd.Stage.Open('scene.usda'); \
           p = s.GetPrimAtPath('/World/Hero'); \
           print(p.GetPrimStack())"
```

## Metadata

Unyped named values on prims/attributes/layers. Examples: `kind` (model/group/component/subcomponent/assembly), `active` (load or skip),
`documentation` (a docstring). Not timeSampled.

## Kinds

Declare a prim's role in the model hierarchy:
- `component` — a leaf referenceable asset (usually ships with all textures).
- `subcomponent` — non-leaf sub-part of a component.
- `group` — a grouping of components.
- `assembly` — a published assembly of components.
- `model` — base kind; rarely used raw.

## TimeCodes

Animation frames. `stage.SetStartTimeCode(1); stage.SetEndTimeCode(240)`.
Each attribute's timeSamples are queried at a specific timeCode; USD
interpolates linearly by default.

## Purpose

Per-prim visibility filter: `default`, `render`, `proxy`, `guide`.
Renderers typically show `default`+`render`; viewports show `default`+`proxy`.
Hidden rigs / pickers get `guide`.

## Gotchas

- **Layer save vs stage save.** `stage.GetRootLayer().Save()` only saves that layer. Sublayers / referenced layers stay dirty. Use `stage.Save()` to save the whole composed stack.
- **Strong-weak "inverse" of most engines.** Stronger = further LEFT in the LIVRPS acronym. "Local" wins.
- **Relationships are NOT symmetric.** Setting a rel target on A to B does not automatically add a rel on B pointing back.
- **VariantSet selection lives in the layer that opens the variant**, not in the variant itself. Editing a variant edits its contents, not the selection.
- **Payloads are the only unload-able arc.** Use them for environment / city / heavy crowd assets.
