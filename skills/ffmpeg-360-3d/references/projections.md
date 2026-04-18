# 360 / VR / Stereoscopic 3D reference

Deep reference for the `v360`, `stereo3d`, and `framepack` filters plus a VR platform compatibility matrix and a note on spherical metadata.

---

## v360 — input / output projection types

`v360` is invoked as `v360=INPUT_TYPE:OUTPUT_TYPE:opt=val:opt=val`. Both the `input` and `output` values may be any of the following (ffmpeg accepts aliases where noted).

| Code | Name | Aspect / layout | Typical source |
|------|------|------------------|----------------|
| `e`, `equirect`, `equirectangular` | Equirectangular | 2:1 rectangle | YouTube 360 master, Facebook 360, most stitching tools |
| `c3x2`, `cube`, `cubemap` | Cubemap 3×2 | 3:2 grid of 6 faces | Intermediate for compression / rendering |
| `c6x1` | Cubemap 6×1 | 6:1 horizontal strip | Older WebGL players |
| `c1x6` | Cubemap 1×6 | 1:6 vertical strip | Some game engines |
| `eac` | Equi-Angular Cubemap | 3:2 but with nonlinear face mapping | YouTube 4K+ 360 serving format |
| `flat`, `rectilinear`, `gnomonic` | Flat / perspective | Normal rectangular image | Output "virtual camera" view |
| `perspective` | Perspective | Alias of `flat` with different defaults | Rendering |
| `fisheye` | Single fisheye | Circular image | Single-lens 360 cameras |
| `dfisheye` | Dual fisheye | Two circles side-by-side | Insta360 ONE / GoPro Max / Ricoh Theta RAW |
| `hequirect`, `half_equirectangular` | Half-equirect | 1:1 per eye | VR180 stereoscopic content |
| `cylindrical` | Cylindrical | Panoramic | Some panorama stitchers |
| `barrel`, `fb` | Barrel (Facebook cubemap) | 4:3 | Facebook's original 360 cubemap |
| `sinusoidal` | Sinusoidal | 2:1 squashed | Cartography |
| `stereographic` | Stereographic | Circle "tiny planet" | Stylistic projection |
| `mercator` | Mercator | 2:1 but squashed vertically | Cartography / stylistic |
| `ball` | Ball | Circle, curved | Stylistic |
| `hammer` | Hammer-Aitoff | Oval | Cartography |
| `pannini` | Pannini | Wide rectangular | Ultra-wide panoramas |
| `rfish` | Reverse fisheye | Circle | Specialty output |

---

## v360 — options

| Option | Meaning | Default | Notes |
|--------|---------|---------|-------|
| `yaw` | Rotate view around vertical axis (degrees) | 0 | left/right look |
| `pitch` | Rotate view around lateral axis (degrees) | 0 | up/down tilt |
| `roll` | Rotate view around forward axis (degrees) | 0 | camera tilt |
| `h_fov` | OUTPUT horizontal FOV (degrees) | — | only meaningful for `flat`/`perspective` outputs |
| `v_fov` | OUTPUT vertical FOV (degrees) | — | same |
| `d_fov` | OUTPUT diagonal FOV (degrees) | — | alternative to h/v |
| `ih_fov` | INPUT horizontal FOV (degrees) | — | required for `fisheye`/`dfisheye` inputs |
| `iv_fov` | INPUT vertical FOV (degrees) | — | required for fisheye inputs |
| `id_fov` | INPUT diagonal FOV (degrees) | — | alternative |
| `in_stereo` | `2d` / `sbs` / `tb` | `2d` | describes stereo layout of INPUT |
| `out_stereo` | `2d` / `sbs` / `tb` | `2d` | describes stereo layout of OUTPUT |
| `interp` | `near` / `linear` / `cubic` / `lanczos` / `spline16` / `gaussian` / `mitchell` | `linear` | use `cubic` or `lanczos` to avoid seam artifacts |
| `w`, `h` | Force output WxH | auto | rarely needed |
| `in_pad`, `out_pad` | Pixel padding | 0.0 | hides seam gaps |
| `fin_pad`, `fout_pad` | Fractional pad | 0.0 | same |
| `alpha_mask` | Generate alpha for non-image areas | 0 | useful for irregular outputs |
| `reset_rot` | Reset rotation before output | 0 | advanced |

### Example: VR180 SBS equirect flat preview

```
v360=hequirect:flat:in_stereo=sbs:out_stereo=mono:yaw=0:pitch=0:h_fov=90:v_fov=60:cubic
```

---

## stereo3d — input / output codes

Invoked as `stereo3d=IN_CODE:OUT_CODE`. Input and output are independent; the filter re-packs frames.

### Packed stereo inputs / outputs

| Code | Layout |
|------|--------|
| `sbsl` | Side-by-side, **left-first** |
| `sbsr` | Side-by-side, right-first |
| `sbs2l` | Side-by-side, left-first, half-width per eye |
| `sbs2r` | Side-by-side, right-first, half-width per eye |
| `abl` | Above-below, left-first (equivalent to top-bottom) |
| `abr` | Above-below, right-first |
| `al` | Alternating frames, left-first |
| `ar` | Alternating frames, right-first |
| `tbl` | Top-bottom, left-first |
| `tbr` | Top-bottom, right-first |
| `tb2l` | Top-bottom, left-first, half-height per eye |
| `tb2r` | Top-bottom, right-first, half-height per eye |

### Mono outputs

| Code | Meaning |
|------|---------|
| `ml` | Mono, left eye only |
| `mr` | Mono, right eye only |

### Interleaved outputs

| Code | Meaning |
|------|---------|
| `irl` | Interleaved rows, left-first |
| `irr` | Interleaved rows, right-first |
| `icl` | Interleaved columns, left-first |
| `icr` | Interleaved columns, right-first |

### Anaglyph outputs

| Code | Meaning |
|------|---------|
| `arbg` | Anaglyph red-blue gray |
| `arcg` | Anaglyph red-cyan gray |
| `arcc` | Anaglyph red-cyan color |
| `arch` | Anaglyph red-cyan half-color |
| `arcd` | Anaglyph red-cyan Dubois |
| `aybd` | Anaglyph yellow-blue Dubois |
| `agmd` | Anaglyph green-magenta Dubois |
| `agmg` | Anaglyph green-magenta gray |
| `agmh` | Anaglyph green-magenta half-color |

### HDMI

| Code | Meaning |
|------|---------|
| `hdmi` | HDMI 1.4a frame-packed (frame-sequential with blanking) |

> `stereo3d` cannot increase resolution. TAB → SBS preserves total frame dimensions; each eye stays at half resolution. Source full-resolution mono eyes separately if you need full per-eye resolution.

---

## framepack — modes

`framepack` packs two video streams (or a single pre-packed stream treated accordingly) for HDMI 1.4a 3D sinks and similar.

| Mode | Meaning |
|------|---------|
| `sbs` | Side-by-side |
| `tab` | Top-and-bottom |
| `frameseq` | Frame-sequential |
| `lines` | Interleaved lines |
| `columns` | Interleaved columns |

> Output dimensions roughly 2× input in the packing axis. Playback requires an HDMI 1.4a–compliant 3D display or receiver. For modern VR delivery (Quest, Vision Pro, YouTube VR) prefer a plain MP4 with SBS/TAB stereo and proper spherical metadata — not framepack.

---

## VR platform compatibility

| Platform | Preferred projection | Stereo support | Metadata required |
|----------|----------------------|----------------|-------------------|
| YouTube 360 (monoscopic) | equirect upload; served as EAC at 4K+ | — | SphericalVideo v1 MP4 box |
| YouTube VR / 180 | hequirect (VR180) | SBS | SphericalVideo v2 |
| Facebook 360 | equirect | SBS (TAB also works) | SphericalVideo v1 |
| Vimeo 360 | equirect | SBS | SphericalVideo v1 |
| Meta Quest (SideQuest / native player) | equirect or hequirect | SBS / TAB | Optional, filename hint suffices (`_360`, `_LR`, `_TB`) |
| Oculus Rift / Quest official app | equirect + SphericalVideo v1 | SBS | Required |
| Apple Vision Pro (MV-HEVC) | — | spatial MV-HEVC | MV-HEVC container |
| Insta360 Studio | equirect | per project | Insta360-specific tags |
| GoPro Max (GPMF) | equirect after stitching via Max Exporter | — | GPMF |
| Ricoh Theta / Theta+ | equirect | — | SphericalVideo v1 |
| VLC 3.x / 4.x | equirect | SBS / TAB | reads SphericalVideo box |

---

## Spherical metadata — ffmpeg CANNOT inject it

ffmpeg writes pixels; it does not write Google's `SphericalVideo` MP4/MOV box. After ffmpeg rendering, run Google's open-source **spatial-media** Python tool:

```bash
# Monoscopic 360
python spatialmedia -i --stereo=none video.mp4 video_spherical.mp4

# Stereoscopic VR180 / SBS
python spatialmedia -i \
  --stereo=left-right \
  --projection=equirectangular \
  video.mp4 video_spherical.mp4

# Cubemap (rare)
python spatialmedia -i \
  --stereo=none \
  --projection=cubemap \
  video.mp4 video_spherical.mp4
```

Without this sidecar injection, YouTube / Facebook / Oculus will render the file as flat 2D even if the pixel layout is correct.

Apple Vision Pro "spatial video" uses MV-HEVC container, not the Google box — use Apple's `AVAssetWriter` or third-party tools for that format.

---

## In-stereo / out-stereo with v360 for VR180

Combine v360 projection change with stereo-preserving options when handling VR180 content:

```bash
# VR180 SBS hequirect rotated 45° yaw, keep stereo
ffmpeg -i vr180.mp4 -vf \
  "v360=hequirect:hequirect:in_stereo=sbs:out_stereo=sbs:yaw=45:cubic" \
  -c:v libx264 -crf 18 -c:a copy rotated.mp4
```

Available `in_stereo` / `out_stereo` values: `2d`, `sbs`, `tb`. When converting VR180 to monoscopic flat views, set `out_stereo=mono` (single eye output).
