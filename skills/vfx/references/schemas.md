# USD schema domains — one-liner reference

Load when the user asks "which schema handles X?".

Docs sources:
- User-guides with TOCs on `https://openusd.org/release/`: UsdLux, UsdMedia, UsdRender, UsdUI, UsdVol.
- Doxygen API only: UsdGeom, UsdShade, UsdSkel, UsdPhysics (under `/release/api/`).

## UsdGeom — geometry + transforms

Basic geometry schemas and the transform stack.
- **Xform / XformCommonAPI** — transform ops (translate, rotate, scale). Canonical op order: T * R * S.
- **Mesh / Subset** — polygonal meshes; GeomSubset assigns per-face materials.
- **Points / BasisCurves / NurbsCurves / NurbsPatch** — point clouds, curves, patches.
- **Cube / Sphere / Cylinder / Cone / Capsule / Plane** — primitive shapes.
- **PointInstancer** — instance-at-scale, massive crowds.
- **Camera** — lens params (focalLength, horizontalAperture, clippingRange).
- **Boundable / Imageable / Xformable** — base classes for hierarchy.

API: `/release/api/usd_geom_page_front.html`.

## UsdLux — lights

- **DistantLight** — infinite sun/moon with angular extent.
- **SphereLight / DiskLight / RectLight / CylinderLight** — area lights.
- **DomeLight** — HDR environment map.
- **GeometryLight** — arbitrary geometry as an emitter.
- **LightAPI / ShapingAPI / ShadowAPI** — applied API schemas for shared params.
- **LightFilter** — modifiers (barn doors, gels) on a rel.
- **LightPortal** — window/portal for indoor sampling.

Docs: `/release/user_guides/luxon/schema_light_and_schema_lightfilter.html` and sibling pages.

## UsdShade — shaders + materials

- **Material** — container prim for a shader network.
- **Shader** — a node with typed inputs/outputs; references `info:id` like `UsdPreviewSurface`, `UsdUVTexture`.
- **NodeGraph** — reusable sub-network.
- **MaterialBindingAPI** — `material:binding` rel from geometry to Material.
- **Connections:** `shader.inputs:foo.connect = </Material/Tex.outputs:rgb>`.
- **UsdPreviewSurface** — the one shader every real-time and offline renderer supports. Use for interoperable delivery (especially Apple .usdz).

API: `/release/api/usd_shade_page_front.html`.

## UsdSkel — skeletal animation

- **Skeleton** — joint hierarchy (by full joint-name array).
- **SkelAnimation** — per-joint rotation/translation/scale timeSamples.
- **SkelRoot** — bounds the rigged hierarchy.
- **BlendShape / SkelBindingAPI** — blend shapes + skinning bindings on meshes.

API: `/release/api/usd_skel_page_front.html`.

## UsdPhysics — rigid-body physics

- **RigidBodyAPI / MassAPI** — dynamics enablement.
- **CollisionAPI / MeshCollisionAPI / Collider** — colliders.
- **Joint / FixedJoint / RevoluteJoint / PrismaticJoint / SphericalJoint / DistanceJoint** — constraints.
- **Scene** — physics world settings (gravity, solver).
- **MaterialAPI** — friction / restitution.

API: `/release/api/usd_physics_page_front.html`.

## UsdMedia — audio / video spatial

- **SpatialAudio** — position-audible source with `filePath`, `gain`, `startTime`, `endTime`, `mediaOffset`, `auralMode` (spatial vs nonSpatial), `playbackMode` (onceFromStart, loopFromStart, ...).

Docs: `/release/user_guides/media/index.html`.

## UsdRender — render settings

- **RenderSettings** — per-shot render-time options (resolution, aspectRatio, pixelAspectRatio, AOVs).
- **RenderProduct** — one output (RGB pass, cryptomatte, etc.) with target `orderedVars` (AOV list) + camera rel.
- **RenderVar** — a named AOV.

Docs: `/release/user_guides/render/index.html`.

## UsdVol — volumetrics

- **Volume** — container for field relationships.
- **FieldAsset / OpenVDBAsset / Field3DAsset** — per-field file pointers (.vdb, .f3d).
- **FieldBase** — abstract base for any sparse volume field.

Docs: `/release/user_guides/vol/index.html`.

## UsdUI — widgets / authoring UI

Non-rendering, DCC-UI hints:
- **Backdrop** — color rectangle behind node graphs (Maya LookDevKit, Houdini COPs).
- **NodeGraphNodeAPI** — position/size metadata for node-editor layout.
- **SceneGraphPrimAPI** — folded/expanded UI state.

Docs: `/release/user_guides/ui/index.html`.

## Applied vs typed schemas

- **Typed schema:** the prim's `typeName` IS the schema (e.g. `Mesh`, `Camera`).
- **Applied API schema:** added on top of any typed prim — `apiSchemas = ["MaterialBindingAPI", "PhysicsRigidBodyAPI"]`. Multiple applied APIs are common.

Use `prim.HasAPI(UsdPhysics.RigidBodyAPI)` to test; use
`UsdPhysics.RigidBodyAPI.Apply(prim)` to attach one.

## Gotchas

- **Don't confuse `Material:binding` (UsdShade rel) with `material:purpose` collection bindings.** The latter is for sub-set face bindings via a Collection, much more powerful, and how production rigs usually bind.
- **`UsdPreviewSurface` is the only shader guaranteed everywhere.** Apple Quick Look, three.js, Omniverse, Hydra-Storm all support it. Don't rely on MaterialX / Karma-VOPs / RenderMan pattern shaders for deliveries.
- **UsdSkel's joint array is flat, not a tree.** Use the `jointNames` order everywhere; weighted indices reference that order.
- **UsdRender is advisory.** Individual renderers (RenderMan, Arnold, Karma, Storm) interpret it differently. Always test.
