# Lens, perspective, and geometric filters — reference

## `lenscorrection`

Barrel / pincushion correction via a radial polynomial.

| option | default | notes |
|---|---|---|
| `cx` | `0.5` | Normalized center x (0..1). |
| `cy` | `0.5` | Normalized center y. |
| `k1` | `0.0` | First-order radial coefficient. NEGATIVE undistorts BARREL. POSITIVE undistorts PINCUSHION. |
| `k2` | `0.0` | Second-order radial coefficient. Same sign as `k1` typically. |
| `i` | `nearest` | Interpolation: `nearest` or `bilinear`. |
| `fc` | `black` | Fill color for undefined pixels after warp. |

### Radial distortion model

Given normalized distance `r` from the optical center, the filter maps

```
r_dst = r_src * (1 + k1 * r_src^2 + k2 * r_src^4)
```

So with `k1 < 0`, points at the periphery are pulled INWARD (undoing barrel bow).
With `k1 > 0`, points are pushed OUTWARD (undoing pincushion).

Tuning heuristic:

1. Start with `k1 = -0.3` for a wide phone/action cam or `+0.3` for telephoto.
2. Adjust in 0.05 increments until straight lines look straight in the middle third.
3. Only then add `k2` (usually same sign, ~20% magnitude of `k1`) for the outer frame.

## `lensfun`

Database-driven correction — reads a known camera/lens combo from the lensfun XML DB and applies published distortion / TCA / vignetting profiles.

**Build flag:** requires ffmpeg built with `--enable-liblensfun`. Check with `ffmpeg -filters | grep lensfun`.

**Database install:**

```bash
# Debian/Ubuntu:
sudo apt install lensfun-tools liblensfun-data-v1
sudo lensfun-update-data      # pull community DB

# macOS (Homebrew):
brew install lensfun
lensfun-update-data

# DB typically at:
/usr/share/lensfun/
/opt/homebrew/share/lensfun/
```

**Find your camera/lens strings:**

```bash
lensfun-list                      # dump every known camera + lens
lensfun-list | grep -i gopro      # filter
```

The strings you copy from `lensfun-list` go verbatim into `make=`, `model=`, `lens_model=`.

### Options

| option | required | notes |
|---|---|---|
| `make` | yes | Camera make, e.g. `GoPro`. |
| `model` | yes | Camera model, e.g. `HERO9 Black`. |
| `lens_model` | yes | Lens model string from DB. |
| `focal_length` | yes* | mm — use EXIF value. |
| `aperture` | no | f-number. Needed for vignetting mode. |
| `mode` | no | `geometry` (default) / `tca` / `vignetting` / `all`. |
| `scale` | no | Extra scale to trim edges after warp. |
| `target_geometry` | no | Output geometry: `rectilinear` (default), `fisheye`, `panoramic`, etc. |
| `interpolation` | no | `nearest` / `linear` / `lanczos`. |
| `reverse` | no | `1` to re-apply distortion (undo a prior correction). |

\*`focal_length` is required in most modes.

## `perspective`

4-corner warp — the standard keystone / trapezoid fix.

| option | notes |
|---|---|
| `x0,y0` | TOP-LEFT corner of the source quadrilateral (pixel coords). |
| `x1,y1` | TOP-RIGHT. |
| `x2,y2` | BOTTOM-LEFT. |
| `x3,y3` | BOTTOM-RIGHT. |
| `interpolation` | `linear` (default) or `cubic`. |
| `sense` | `source` (default: map source quad → output rect) or `destination` (map output rect → source quad). |
| `eval` | `init` (default) or `frame`. Use `frame` for time-varying corners with ffmpeg expressions. |

### 4-point geometry diagram

```
Source frame (W x H):

    (x0,y0)──────────────(x1,y1)        TL ──────────── TR
      │ \                   / │           │              │
      │  \                 /  │           │   output     │
      │   \               /   │           │   rectangle  │
      │    \             /    │           │              │
      │     \           /     │           │              │
    (x2,y2)──────────(x3,y3)            BL ──────────── BR
```

With `sense=source` the source quadrilateral `(x0,y0)..(x3,y3)` is warped INTO the full output rectangle (width × height of the input frame). Keystone example: if the building's corners in the FRAME are at `(300,0), (1620,0), (0,1080), (1920,1080)`, that quadrilateral gets mapped to the full `1920x1080` output — the trapezoid becomes a rectangle.

With `sense=destination` the meaning reverses: `(x0,y0)..(x3,y3)` describe WHERE the corners of the output rect should LAND INSIDE the source frame (i.e. "pull" the image).

## `vignette`

Add or remove a soft circular darkening.

| option | default | notes |
|---|---|---|
| `angle`, `a` | `PI/5` | Cone half-angle in radians. SMALLER = harsher. Can be an expression. |
| `x0` | `w/2` | Center x. |
| `y0` | `h/2` | Center y. |
| `mode` | `forward` | `forward` applies darkening; `backward` DIVIDES by the vignette (removes one). |
| `eval` | `init` | `init` or `frame` for time-varying params. |
| `dither` | `1` | `1` to dither output to 8-bit cleanly. |
| `aspect` | `1/1` | Aspect of the vignette ellipse. |

## `rotate`

Arbitrary-angle rotation.

| option | notes |
|---|---|
| `angle`, `a` | Angle in RADIANS. Use `N*PI/180` for degrees. Supports expressions (e.g. `t*PI/6` for 30°/s spin). |
| `out_w`, `ow` | Output width expression. Use `rotw(a)` for auto-expanded bounding box. |
| `out_h`, `oh` | Output height. Use `roth(a)`. |
| `bilinear` | `1` (default) or `0`. |
| `fillcolor`, `c` | Fill color for newly exposed corners (default `black`; use `none` for alpha). |

### Canvas-expansion math

For a `W × H` frame rotated by angle `A`, the minimum bounding box is:

```
rotw(A) = |W * cos(A)| + |H * sin(A)|
roth(A) = |W * sin(A)| + |H * cos(A)|
```

ffmpeg exposes these directly as `rotw(a)` and `roth(a)`, so the canonical lossless rotation is:

```
rotate=A:ow=rotw(A):oh=roth(A)
```

## `shear`

Affine skew.

| option | default | notes |
|---|---|---|
| `shx` | `0` | x-shift per unit y. `0.2` = strong skew. |
| `shy` | `0` | y-shift per unit x. |
| `fillcolor` | `black` | Corner fill. |
| `interp` | `bilinear` | `nearest` or `bilinear`. |

## `tiltandshift`

Per-frame horizontal shift across the video — a rolling-shutter-style effect (NOT a photographic tilt-shift blur).

| option | notes |
|---|---|
| `tilt` | `1` to enable tilt. |
| `start` | First frame column offset. |
| `end` | Last frame column offset. |
| `hold` | Number of frames to hold each shift step. |
| `pad` | Padding around shifted region. |

## Recipe gallery

### GoPro HERO / fisheye undistort

```bash
ffmpeg -i gopro.mp4 \
  -vf "lenscorrection=k1=-0.28:k2=-0.03,crop=iw*0.92:ih*0.92" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out.mp4
```

### iPhone ultra-wide (0.5x) correction

```bash
ffmpeg -i iphone_uw.mov \
  -vf "lenscorrection=k1=-0.18:k2=-0.04,crop=iw*0.94:ih*0.94" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out.mp4
```

### Architecture keystone fix

```bash
# Building narrows at the top. Push the top corners inward in the SOURCE quad.
ffmpeg -i building.mp4 \
  -vf "perspective=x0=300:y0=0:x1=1620:y1=0:x2=0:y2=1080:x3=1920:y3=1080:interpolation=cubic" \
  -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a copy out.mp4
```

### Cinematic vignette (add)

```bash
ffmpeg -i scene.mp4 -vf "vignette=angle=PI/6" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy graded.mp4
```

### Remove a baked-in vignette

```bash
ffmpeg -i dark_corners.mp4 -vf "vignette=angle=PI/6:mode=backward" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy fixed.mp4
```

### Dutch angle (5° rotate, expanded canvas)

```bash
ffmpeg -i in.mp4 \
  -vf "rotate=5*PI/180:ow=rotw(5*PI/180):oh=roth(5*PI/180):c=black" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy dutch.mp4
```

### GoPro + lensfun (when DB has your model)

```bash
ffmpeg -i gopro.mp4 \
  -vf "lensfun=make=GoPro:model='HERO9 Black':lens_model='HERO9 Black & GoPro Lens':focal_length=3.0:mode=all" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy corrected.mp4
```

### Un-shear a scanned/tilted scene

```bash
ffmpeg -i tilted.mp4 -vf "shear=shx=-0.08:shy=0" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy straight.mp4
```

### Rotation + scale to fixed output

```bash
# Rotate first so rotw/roth expands canvas; then scale to a delivery size.
ffmpeg -i in.mp4 \
  -vf "rotate=10*PI/180:ow=rotw(10*PI/180):oh=roth(10*PI/180):c=black,scale=1920:1080" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy out.mp4
```
