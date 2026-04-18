---
name: ffmpeg-360-3d
description: >
  360° / VR and stereoscopic 3D video with ffmpeg: v360 filter (equirectangular, cubemap 3x2/6x1/1x6, fisheye, flat, hequirect, dfisheye, cylindrical, perspective, barrel, sinusoidal, half_equirectangular, stereographic, mercator, ball, hammer, pannini, eac, c3x2/c6x1/c1x6, rfish), stereo3d filter (SBS ↔ TAB ↔ interlaced ↔ anaglyph), framepack, spatial audio placeholder. Use when the user asks to convert 360 video projections, equirectangular to cubemap, unwrap fisheye, convert side-by-side 3D to top-bottom, make anaglyph 3D, reproject 360 video, or handle VR180/VR360 content.
argument-hint: "[projection] [input]"
---

# Ffmpeg 360 3D

**Context:** $ARGUMENTS

## Quick start

- **Equirect → cubemap 3x2:** → Step 3
- **Dual fisheye → equirect:** → Step 3 (dfisheye recipe)
- **SBS 3D → TAB 3D:** → Step 4
- **SBS → anaglyph (red-cyan):** → Step 4
- **Virtual camera flat view from 360:** → Step 3 (flat recipe)
- **Frame-packed HDMI 3D:** → Step 4 (framepack)

## When to use

- Converting between 360 projections (equirect ↔ cubemap ↔ EAC ↔ fisheye).
- Unwrapping GoPro Max / Insta360 / Ricoh Theta dual-fisheye footage to equirect.
- Reprojecting VR content for different platforms (YouTube EAC vs Facebook equirect).
- Converting stereoscopic 3D layouts (SBS ↔ TAB ↔ interlaced ↔ anaglyph).
- Generating a "virtual camera" flat view from a 360 video (rectilinear crop).
- Packing SBS/TAB into HDMI 1.4a frame-packed output for 3D TVs.

## Step 1 — Identify input projection

Before filtering, determine what you have:

- **Equirectangular (`e`)** — most common 360 format. 2:1 aspect ratio (e.g. 3840×1920, 4096×2048, 5760×2880). Looks like a stretched rectangular world map.
- **Cubemap 3x2 (`c3x2`)** — 6 cube faces in a 3-column, 2-row grid. 3:2 aspect. Common intermediate.
- **Cubemap 6x1 (`c6x1`) or 1x6 (`c1x6`)** — cube faces in a strip.
- **Equi-Angular Cubemap (`eac`)** — YouTube's 4K+ 360 format. Looks like a cubemap but with warped face geometry for higher quality at same bitrate.
- **Dual fisheye (`dfisheye`)** — two circular fisheye images side-by-side or stacked. Output from Insta360, GoPro Max, Ricoh Theta before stitching.
- **Single fisheye (`fisheye`)** — one circular fisheye lens image.
- **Half equirect (`hequirect`)** — half-sphere / VR180 format. 1:1 aspect per eye.

Run `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,side_data_list input.mp4` to inspect dimensions and any spherical metadata. Ratio 2:1 usually means equirect; 3:2 usually means cubemap 3×2; 1:1 per eye often means VR180 hequirect.

## Step 2 — Pick output projection and interpolation

v360 grammar: `v360=INPUT:OUTPUT:options`. Interpolation choices:

- `near` — nearest neighbor (fastest, blocky).
- `linear` — default. Acceptable for preview.
- `cubic` — good quality/speed trade (RECOMMENDED for most conversions).
- `lanczos` — best quality, slowest.
- `spline16`, `gaussian`, `mitchell` — specialty choices.

Rule of thumb: always pass `:cubic` or `:lanczos` unless speed matters — default `linear` leaves visible artifacts at cube-face seams.

## Step 3 — Run v360

### Equirectangular → cubemap 3×2

```bash
ffmpeg -i equi.mp4 -vf "v360=e:c3x2:cubic" -c:v libx264 -crf 18 -c:a copy out.mp4
```

### Cubemap 6×1 → equirectangular

```bash
ffmpeg -i cube.mp4 -vf "v360=c6x1:e:cubic" -c:v libx264 -crf 18 -c:a copy out.mp4
```

### Dual fisheye → equirect (Insta360 / GoPro Max typical 190° lenses)

```bash
ffmpeg -i dual.mp4 -vf "v360=dfisheye:e:ih_fov=190:iv_fov=190:cubic" \
  -c:v libx264 -crf 18 -c:a copy out.mp4
```

`ih_fov`/`iv_fov` describe INPUT horizontal/vertical field-of-view of each fisheye circle. Typical consumer cams are 190°–200°.

### Equirect → flat perspective (virtual camera)

```bash
ffmpeg -i equi.mp4 -vf "v360=e:flat:pitch=-15:yaw=30:h_fov=90:v_fov=60:cubic,scale=1920:1080" \
  -c:v libx264 -crf 18 -c:a copy view.mp4
```

`yaw` (left/right), `pitch` (up/down), `roll` (tilt) in degrees. `h_fov`/`v_fov` control output rectilinear FOV.

### YouTube EAC → standard equirect

```bash
ffmpeg -i youtube_eac.mp4 -vf "v360=eac:e:cubic" -c:v libx264 -crf 18 -c:a copy equi.mp4
```

### Rotate / re-orient an equirect (keep projection, change heading)

```bash
ffmpeg -i equi.mp4 -vf "v360=e:e:yaw=90:pitch=0:roll=0:cubic" \
  -c:v libx264 -crf 18 -c:a copy rotated.mp4
```

## Step 4 — Handle stereoscopic 3D (stereo3d / framepack)

### SBS (left-first) → TAB (left-first)

```bash
ffmpeg -i sbs.mp4 -vf "stereo3d=sbsl:tbl" -c:v libx264 -crf 18 -c:a copy tab.mp4
```

### SBS → anaglyph red-cyan grayscale

```bash
ffmpeg -i sbs.mp4 -vf "stereo3d=sbsl:arcg" -c:v libx264 -crf 18 -c:a copy anaglyph.mp4
```

Use `arcc` for color anaglyph, `arch` for half-color, `arcd` for Dubois.

### SBS → mono left eye only

```bash
ffmpeg -i sbs.mp4 -vf "stereo3d=sbsl:ml" -c:v libx264 -crf 18 -c:a copy mono.mp4
```

### HDMI 1.4a frame packing (for 3D TVs)

```bash
ffmpeg -i input.mp4 -vf "framepack=sbs" -c:v libx264 -crf 18 -c:a copy packed.mp4
# modes: sbs | tab | frameseq | lines | columns
```

### Spherical metadata (OUT OF FFMPEG SCOPE)

ffmpeg writes pixels but cannot inject the Google / 360 MP4/MOV SphericalVideo box. After rendering, use Google's spatial-media tool:

```bash
python spatialmedia -i --stereo=none video.mp4 video_360.mp4
# VR180 / SBS:
python spatialmedia -i --stereo=left-right --projection=equirectangular video.mp4 out.mp4
```

Without this metadata box, YouTube / Facebook / Oculus will play the file as a flat 2D video rather than 360.

## Available scripts

- **`scripts/immersive.py`** — stdlib argparse wrapper with subcommands: `project`, `flat-view`, `stereo3d`, `anaglyph`, `framepack`. Supports `--dry-run` and `--verbose`.

## Workflow

```bash
# Project conversion (any supported v360 type pair)
uv run ${CLAUDE_SKILL_DIR}/scripts/immersive.py project \
  --input equi.mp4 --output cube.mp4 --from equirect --to cubemap3x2 --interp cubic

# Virtual camera flat view from equirect
uv run ${CLAUDE_SKILL_DIR}/scripts/immersive.py flat-view \
  --input equi.mp4 --output view.mp4 --from equirect \
  --yaw 30 --pitch -15 --h-fov 90 --v-fov 60 --size 1920x1080

# Stereoscopic layout conversion
uv run ${CLAUDE_SKILL_DIR}/scripts/immersive.py stereo3d \
  --input sbs.mp4 --output tab.mp4 --from sbsl --to tbl

# Anaglyph
uv run ${CLAUDE_SKILL_DIR}/scripts/immersive.py anaglyph \
  --input sbs.mp4 --output ana.mp4 --from sbsl --mode arcg

# HDMI frame packing
uv run ${CLAUDE_SKILL_DIR}/scripts/immersive.py framepack \
  --input in.mp4 --output packed.mp4 --mode sbs
```

## Reference docs

- Read [`references/projections.md`](references/projections.md) for the full v360 type table, stereo3d code table, framepack options, and VR platform compatibility matrix.

## Gotchas

- **v360 grammar:** `v360=INPUT_TYPE:OUTPUT_TYPE:opt=val:opt=val`. Input and output types are positional — colon-separated — not `in=`/`out=`.
- **pitch / yaw / roll** rotate the view in degrees. Defaults 0. Only affect output sampling, not input parsing.
- **h_fov / v_fov** are OUTPUT field-of-view; only meaningful for rectilinear outputs (`flat`, `perspective`). Ignored for `e`, `c3x2`, etc.
- **ih_fov / iv_fov** are INPUT field-of-view; required for `fisheye` / `dfisheye` inputs because the filter cannot infer lens FOV from pixels.
- **YouTube 360 at 4K+ uses EAC** (equi-angular cubemap), not standard cubemap. Upload equirect and YouTube transcodes to EAC server-side — but if you receive an EAC source, decode with `v360=eac:e`.
- **Facebook 360 uses equirect.** Oculus/Quest plays both equirect and EAC. VR180 uses `hequirect` with SBS stereo pair.
- **stereo3d codes:** sbsl/sbsr (SBS left-first / right-first), tbl/tbr (top-bottom), al/ar (above-below alt), ml/mr (mono L/R), abl/abr (above-below), arbg (red-blue gray), arcg (red-cyan gray), arcc (red-cyan color), arch (red-cyan half-color), arcd (red-cyan Dubois), aybd (yellow-blue Dubois), agmd/agmg/agmh (green-magenta Dubois/gray/half), irl/irr (interleaved rows), icl/icr (interleaved cols), hdmi (HDMI frame-packed).
- **stereo3d cannot increase resolution.** Converting TAB → SBS keeps dimensions; each eye stays at half-resolution. To get full-res per eye you need two separate mono sources, not a stereo3d conversion.
- **Anaglyph:** prefer `arcg` for grayscale-friendly content, `arcc` for color (watch for retinal rivalry), `arcd` (Dubois) for best color quality on modern displays.
- **framepack** outputs a packed single frame at roughly 2× dimensions — intended for HDMI 1.4a 3D sinks, not playback in standard players.
- **Interpolation:** pass `:cubic` or `:lanczos`. Default `linear` produces visible seams at cube-face boundaries.
- **Verify** by uploading to YouTube (unlisted) or playing in VLC 3.x (supports 360 mouse-look), or in a headset.
- **Spherical metadata box** is a MP4/MOV sidecar. ffmpeg does NOT write it. Use Google's spatial-media Python tool on the rendered output.
- **VR180 stereoscopic** pipeline: v360 `hequirect` × stereo SBS with `in_stereo=sbs:out_stereo=sbs`. Example: `v360=hequirect:e:in_stereo=sbs:out_stereo=sbs`.

## Examples

### Example 1: Insta360 dual-fisheye to YouTube-ready equirect

Input: `insta360.mp4` — 3840×1920 dual fisheye, 2 circles 190°, side by side.

```bash
ffmpeg -i insta360.mp4 \
  -vf "v360=dfisheye:e:ih_fov=190:iv_fov=190:cubic,scale=3840:1920" \
  -c:v libx264 -crf 18 -preset slow -c:a aac -b:a 192k equi.mp4

# then inject spherical metadata (external tool):
python spatialmedia -i --stereo=none equi.mp4 equi_spherical.mp4
```

Upload `equi_spherical.mp4` to YouTube — it will detect 360 and serve as EAC.

### Example 2: Virtual cinematographer crop from 360

Input: `equi.mp4` 4K equirect. Want a 1080p "flat" view facing 45° right, 10° down.

```bash
ffmpeg -i equi.mp4 \
  -vf "v360=e:flat:yaw=45:pitch=-10:roll=0:h_fov=85:v_fov=55:cubic,scale=1920:1080" \
  -c:v libx264 -crf 18 -c:a aac -b:a 160k flat_cam.mp4
```

### Example 3: 3D Blu-ray rip (SBS) → anaglyph for monitor playback

```bash
ffmpeg -i movie_sbs.mkv -vf "stereo3d=sbsl:arcd" \
  -c:v libx264 -crf 18 -c:a copy movie_anaglyph.mkv
```

`arcd` (Dubois red-cyan) has the best color fidelity; viewer needs red-cyan glasses.

### Example 4: VR180 SBS equirect → flat single-eye view

```bash
ffmpeg -i vr180_sbs.mp4 \
  -vf "v360=hequirect:flat:in_stereo=sbs:out_stereo=mono:yaw=0:pitch=0:h_fov=90:v_fov=60:cubic" \
  -c:v libx264 -crf 18 -c:a copy left_eye_flat.mp4
```

## Troubleshooting

### Error: `[Parsed_v360_0 @ ...] Specified input format is not accurate.`

Cause: Input type (e.g. `e`) doesn't match actual pixel layout (content is 3×2 cubemap).
Solution: Re-inspect aspect ratio; pick correct input type (`c3x2`, `eac`, etc.).

### Output has visible seams at cube edges

Cause: default `linear` interpolation.
Solution: Add `:cubic` or `:lanczos` to the filter: `v360=e:c3x2:lanczos`.

### Fisheye unwrap looks squeezed or shows black wedges

Cause: wrong `ih_fov`/`iv_fov`. 190° lens treated as 180° leaves unused area; 180° lens forced to 220° stretches pixels.
Solution: check camera spec — Insta360 ONE / GoPro Max ≈ 190°–200°. Try `ih_fov=190:iv_fov=190` first, adjust ±5° until horizon is straight.

### YouTube plays my output as flat 2D, not 360

Cause: missing SphericalVideo metadata box. ffmpeg cannot write it.
Solution: run Google's `spatialmedia` tool on the rendered file to inject the box.

### stereo3d SBS → TAB output is squashed

Cause: stereo3d preserves total frame dimensions. Input 1920×1080 SBS (960×1080 per eye) → TAB becomes 1920×1080 with 1920×540 per eye. Each eye is still half-resolution; that is expected.
Solution: accept the halved resolution, or source full-resolution per-eye and encode mono streams separately.

### Anaglyph looks washed out / ghosted

Cause: using `arcc` (color) on high-contrast content; retinal rivalry.
Solution: try `arcd` (Dubois) or `arcg` (grayscale) — both reduce ghosting.
