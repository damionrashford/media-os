---
name: ffmpeg-lens-perspective
description: >
  Lens correction, perspective warp, and geometric transforms with ffmpeg: lenscorrection (barrel/pincushion), lensfun (post-processing lens DB), perspective (keystone fix), vignette (add/remove vignetting), shear, tiltandshift, rotate with interpolation. Use when the user asks to fix barrel or fisheye distortion, remove lens distortion, correct keystone / perspective, add a cinematic vignette, un-shear tilted footage, or apply lens-corrective transforms.
argument-hint: "[operation] [input]"
---

# Ffmpeg Lens Perspective

**Context:** $ARGUMENTS

## Quick start

- **Undistort GoPro/fisheye barrel:** → Step 1 → Step 2 (`lenscorrection=k1=-0.3`)
- **Pincushion (telephoto) correction:** → Step 2 (`lenscorrection=k1=0.3`)
- **4-corner keystone/perspective fix:** → Step 2 (`perspective=...`)
- **Add cinematic vignette:** → Step 2 (`vignette=angle=PI/5`)
- **Remove vignette:** → Step 2 (`vignette=angle=PI/5:mode=backward`)
- **Rotate by arbitrary degrees:** → Step 2 (`rotate=A:ow=rotw(A):oh=roth(A)`)
- **Shear (skew) correction:** → Step 2 (`shear=shx=0.2:shy=0`)
- **Camera+lens-aware correction:** → Step 2 (`lensfun=...`)

## When to use

- Footage from action cams, fisheye, wide-angle phone lenses exhibits barrel distortion (straight lines bow outward).
- Telephoto lenses show pincushion distortion (lines bow inward).
- Architectural / document shots have keystone (trapezoid) distortion from off-axis shooting.
- You want to add or remove a lens vignette (dark corners).
- You need an arbitrary-angle rotation with a proper expanded canvas.
- You need to un-shear a tilted scan or sheared frame.
- Use `ffmpeg-video-filter` instead for simple 90/180/270 rotations (`transpose`) or axis flips.
- Use `ffmpeg-360-3d` (`v360`) instead for full 360/equirectangular reprojection.

## Step 1 — Identify the distortion type

Preview with `ffplay` and inspect edges:

1. Straight lines bow OUTWARD from center → **barrel** → `lenscorrection` with NEGATIVE k1.
2. Straight lines bow INWARD toward center → **pincushion** → `lenscorrection` with POSITIVE k1.
3. Verticals converge (trapezoid) → **keystone** → `perspective` (4-corner warp).
4. Frame is rotated/skewed as a whole → **rotate** or **shear**.
5. Dark corners → **vignette** (add or `mode=backward` to remove).
6. You know camera + lens → **lensfun** (database-driven, most accurate; build-flag gated).

## Step 2 — Pick filter and apply

Core recipes:

```bash
# Barrel correction (GoPro, fisheye, wide-phone). k1 negative = undistort barrel.
ffmpeg -i in.mp4 -vf "lenscorrection=k1=-0.3:k2=0" -c:a copy out.mp4

# Pincushion (telephoto). k1 positive.
ffmpeg -i in.mp4 -vf "lenscorrection=k1=0.3:k2=0" -c:a copy out.mp4

# Database-driven (needs --enable-liblensfun + lensfun DB).
ffmpeg -i in.mp4 -vf "lensfun=make=GoPro:model='HERO9 Black':lens_model='HERO9 Black':focal_length=3.0:mode=geometry" -c:a copy out.mp4

# 4-corner keystone fix. Corners = TL, TR, BL, BR of the SOURCE quadrilateral.
ffmpeg -i in.mp4 -vf "perspective=x0=100:y0=0:x1=1820:y1=10:x2=0:y2=1080:x3=1920:y3=1070:interpolation=linear" -c:a copy out.mp4

# Add cinematic vignette. angle is the cone half-angle (radians); smaller = harsher.
ffmpeg -i in.mp4 -vf "vignette=angle=PI/5" -c:a copy out.mp4

# Remove a vignette baked into the footage.
ffmpeg -i in.mp4 -vf "vignette=angle=PI/5:mode=backward" -c:a copy out.mp4

# Shear (skew). shx = x-shift per unit y (0.2 is strong).
ffmpeg -i in.mp4 -vf "shear=shx=0.2:shy=0" -c:a copy out.mp4

# Rotate by 15 degrees with auto-expanded canvas.
ffmpeg -i in.mp4 -vf "rotate=15*PI/180:ow=rotw(15*PI/180):oh=roth(15*PI/180):c=black" -c:a copy out.mp4

# Tilt + shift (rolling-shutter-style horizontal shift across frames).
ffmpeg -i in.mp4 -vf "tiltandshift=tilt=1:start=0:hold=30:pad=30" -c:a copy out.mp4
```

## Step 3 — Tune params

- **`lenscorrection` k1/k2**: RADIAL coefficients. Typical k1 magnitude 0.05-0.5. Very lens-dependent. Start with k1 alone; add small k2 (~0.05) only if edges still curve after k1 is tuned.
- **`lenscorrection` center**: defaults to `cx=0.5:cy=0.5` (normalized). Override for off-center sensors (rare; anamorphic or cropped sensors).
- **`perspective`**: 4 corners are the SOURCE quadrilateral mapped to the output rectangle. For keystone where verticals converge at the top, push `x0`/`x1` inward (toward center). Use `sense=source` (default) or `sense=destination` to flip the mapping direction. `interpolation=linear` or `cubic` for smooth output.
- **`vignette` angle**: cone half-angle in radians. `PI/5` ≈ 36° (moderate). Smaller value = more intense darkening. Use `x0`/`y0` to offset the vignette center.
- **`rotate` angle**: RADIANS. For degrees use `N*PI/180`. Use `ow=rotw(a):oh=roth(a)` to auto-expand canvas so corners are not clipped.
- **`shear` shx/shy**: skew factor (x-shift per y, y-shift per x). 0.05-0.2 typical. Add `interp=bilinear` for smoother output.
- **`lensfun` mode**: `geometry` (distortion only), `tca` (chromatic aberration only), `vignetting` (lens vignetting only), `all`. Default is `geometry`.

## Step 4 — Verify and (optionally) clean up edges

After any geometric warp, the frame may have black borders or transparent wedges. Verify with `ffplay`, then:

- **Crop to safe area:** `crop=iw*0.9:ih*0.9` or a fixed `crop=W:H:X:Y`.
- **Scale to standard output size:** append `scale=1920:1080`.
- **Check pixel format:** add `-pix_fmt yuv420p` for broad playback compatibility.
- **Order matters:** for rotate + scale, rotate FIRST, then scale. For lens correction + crop, lenscorrection FIRST, then crop.

Example full chain (barrel-undistort a GoPro and crop the wobble):

```bash
ffmpeg -i gopro.mp4 \
  -vf "lenscorrection=k1=-0.25:k2=-0.02,crop=iw*0.92:ih*0.92,scale=1920:1080" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out.mp4
```

## Available scripts

- **`scripts/lens.py`** — argparse dispatcher with subcommands: `undistort-barrel`, `undistort-pincushion`, `lensfun`, `perspective`, `vignette`, `rotate`, `shear`. Prints the ffmpeg command, supports `--dry-run` and `--verbose`. Stdlib only.

## Workflow

```bash
# Barrel undistort
uv run ${CLAUDE_SKILL_DIR}/scripts/lens.py undistort-barrel --input in.mp4 --output out.mp4 --k1 -0.3

# Keystone fix (4 corners in pixel coordinates, TL;TR;BL;BR)
uv run ${CLAUDE_SKILL_DIR}/scripts/lens.py perspective --input in.mp4 --output out.mp4 \
  --corners "100,0;1820,10;0,1080;1920,1070"

# Rotate with auto-expanded canvas
uv run ${CLAUDE_SKILL_DIR}/scripts/lens.py rotate --input in.mp4 --output out.mp4 --degrees 15 --expand-canvas
```

## Reference docs

- Read [`references/filters.md`](references/filters.md) for per-filter option tables, the radial distortion math, lensfun database install/query, the 4-corner perspective diagram, rotation canvas-expansion math, and a recipe gallery (GoPro, iPhone wide, architecture keystone, dutch angle, cinematic vignette).

## Gotchas

- **`lenscorrection` k1/k2 are RADIAL distortion coefficients.** k1 NEGATIVE = barrel undistort; k1 POSITIVE = pincushion undistort. Magnitudes 0.1-0.5 typical, but strongly lens-dependent.
- **`lenscorrection` center** defaults to `(0.5, 0.5)` normalized. For off-center sensors override `cx`, `cy`.
- **`lensfun` requires `--enable-liblensfun` at build time** AND a lens database on disk. Install via `lensfun-tools` (Linux) or `brew install lensfun` (macOS); XML DB usually lives at `/usr/share/lensfun/` or `/opt/homebrew/share/lensfun/`. Run `lensfun-update-data` to pull the community DB.
- **`lensfun` lens model strings must match the DB exactly.** Run `lensfun-list` (or inspect XML) for the canonical make/model/lens_model strings — copying a label from the camera body does NOT guarantee a match.
- **`lensfun` `mode`**: `geometry` (default, distortion), `tca` (chromatic aberration), `vignetting`, `all`.
- **`perspective` 4 corners define the SOURCE quadrilateral** that gets mapped to the output rectangle. Default `sense=source`. Flip with `sense=destination` if your 4 points instead define where the CORNERS OF THE OUTPUT should land in the source frame.
- **`rotate` angle is in RADIANS.** For degrees use `N*PI/180`. Without `ow`/`oh` the output is cropped to the INPUT dimensions — the rotated corners will be clipped. For a clean rotation use `rotate=A:ow=rotw(A):oh=roth(A)`.
- **`vignette` `angle`** is the cone half-angle. SMALLER = harsher/darker. `mode=backward` inverts the vignette function — that is the mode for REMOVAL, not addition. `x0`/`y0` offset the vignette center.
- **Post-warp edges are black/transparent.** After perspective/rotate/shear, add a `crop` or `scale` stage to remove the letterbox wedges.
- **Lens correction is applied BEFORE any scaling.** If you need to resize, put `lenscorrection` first, then `scale`.
- **For H.264/MP4 output, always add `-pix_fmt yuv420p`** — perspective/rotate filters can emit `yuva420p` which many players reject.
- **`shear` `shx=0.2`** is x-shift per y-unit; 0.2 is already a strong skew. Start at 0.05.
- **Tilt+shift is a per-frame horizontal shift**, not a photographic tilt-shift lens blur. Read `tiltandshift` docs if you expect miniature-faking blur.

## Examples

### Example 1: GoPro HERO9 barrel undistort

Input: `gopro.mp4` shot in SuperView/wide mode, straight lines heavily bowed.
Steps:

```bash
ffmpeg -i gopro.mp4 \
  -vf "lenscorrection=k1=-0.28:k2=-0.03,crop=iw*0.92:ih*0.92" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out.mp4
```

Result: straight horizon, mild crop removes the curved black wedge at the edges.

### Example 2: Architecture keystone fix

Input: 1920×1080 building shot, top of the building narrower than the bottom.
Steps: identify source corners where the rectangular building projects; map them to the output.

```bash
ffmpeg -i building.mp4 \
  -vf "perspective=x0=300:y0=0:x1=1620:y1=0:x2=0:y2=1080:x3=1920:y3=1080:interpolation=cubic" \
  -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a copy out.mp4
```

Result: verticals become parallel, building sits in an upright rectangle.

### Example 3: Cinematic vignette

```bash
ffmpeg -i scene.mp4 -vf "vignette=angle=PI/6" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy graded.mp4
```

### Example 4: Dutch angle (5° tilt) with expanded canvas

```bash
ffmpeg -i in.mp4 \
  -vf "rotate=5*PI/180:ow=rotw(5*PI/180):oh=roth(5*PI/180):c=black" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy dutch.mp4
```

## Troubleshooting

### Error: `Option 'lensfun' not found`

Cause: ffmpeg was built without `--enable-liblensfun`.
Solution: rebuild (or `brew reinstall ffmpeg --with-lensfun` on systems that support it), or use `lenscorrection` + manual k1/k2 instead.

### Error: `Unable to find camera/lens in database`

Cause: `lensfun` `make`/`model`/`lens_model` strings do not match any DB entry.
Solution: run `lensfun-update-data`, then `lensfun-list` and copy the exact strings.

### Rotated output has clipped corners

Cause: `rotate` without `ow`/`oh` crops to input dimensions.
Solution: use `rotate=A:ow=rotw(A):oh=roth(A)`.

### Perspective output is mirrored or inverted

Cause: corners passed in wrong order (expected TL, TR, BL, BR).
Solution: reorder corners; or add `sense=destination` if your points describe output→source instead of source→output.

### Barrel undistort still shows curved edges

Cause: k1 alone is insufficient; lens has higher-order radial distortion.
Solution: add a small `k2` (~-0.05 to -0.1 same sign as k1) and iterate.

### Vignette removal leaves a halo

Cause: `angle` too large (too soft); `mode=backward` divides by vignette function so an over-wide angle undercorrects.
Solution: tighten angle (e.g., `PI/6` instead of `PI/4`) and re-run.

### Output has green/black borders in MP4

Cause: `yuva420p` pixel format with alpha, MP4 players cannot show alpha.
Solution: append `,format=yuv420p` at end of `-vf` chain, or add `-pix_fmt yuv420p`.
