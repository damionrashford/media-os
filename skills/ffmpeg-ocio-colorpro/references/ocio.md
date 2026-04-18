# OCIO / ACES / ICC Reference

Deep dive for the `ffmpeg-ocio-colorpro` skill. Cross-references `ffmpeg-lut-grade`, `ffmpeg-hdr-color`, `ffmpeg-probe`.

---

## 1. ACES config versions

ACES ships as a "config" bundle (`config.ocio` + LUT payload) that OCIO consumes. Versions are NOT drop-in compatible; role and colorspace names drift between majors.

| Version   | Released | Notable changes                                                                                     | Typical use today |
|-----------|----------|-----------------------------------------------------------------------------------------------------|-------------------|
| **1.0.3** | 2016     | First stable. Fixed matrix bugs vs 1.0.x. Small OutputTransform catalog.                            | Legacy VFX only.  |
| **1.1**   | 2018     | Added HDR OutputTransforms (Rec.2020 ST2084 1000/2000/4000 nits, P3-D65 ST2084, HLG).              | Legacy HDR.       |
| **1.2**   | 2020     | Refactored ACEScct toe. More LMTs, BMD/RED/Sony log input transforms maintained.                    | Common in Resolve 17/18. |
| **1.3**   | 2022     | Gamut Compress LMT baked into ACES Output Transforms. Improves overly saturated highlights.         | Recommended SDR/HDR default. |
| **2.0**   | 2024     | New ACES 2.0 Output Transform ("reference rendering transform v2"). Names changed (e.g. `ACES - ACES2065-1` vs `ACES2065-1`). Studio-config vs CG-config split. | Leading edge; verify compatibility with downstream tools. |

**Pin the version per project.** Distributed packages:
- OCIO v1/v2 reference configs: https://github.com/colour-science/OpenColorIO-Configs
- ACES studio-config / cg-config (v1.3+/2.0+): https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES

Environment: `export OCIO=/path/to/studio-config-v2.1.0_aces-v1.3_ocio-v2.3.ocio`

---

## 2. Color-space roles (ACES / OCIO)

OCIO "roles" are aliases that tools look up instead of hardcoding names. Relevant roles in an ACES config:

| Role                        | Typical mapping                    | Meaning |
|-----------------------------|------------------------------------|---------|
| `scene_linear`              | `ACEScg` (AP1)                     | Linear rendering space. |
| `compositing_linear`        | `ACEScg`                           | Linear for compositing. |
| `rendering`                 | `ACEScg`                           | Same. |
| `aces_interchange`          | `ACES2065-1` (AP0)                 | Portable interchange. |
| `cie_xyz_d65_interchange`   | `CIE-XYZ-D65`                      | Hard reference. |
| `color_timing`              | `ACEScct`                          | Grading/timing space. |
| `compositing_log`           | `ACEScct`                          | Log for comp ops. |
| `texture_paint`             | `sRGB - Texture` or `Utility - sRGB - Texture` | Paint textures. |
| `matte_paint`               | `sRGB`                             | Matte painting. |
| `data`                      | `Raw`                              | Non-color data (e.g. normals, IDs). |
| `default`                   | config-specific                    | Catch-all. |
| `reference`                 | `ACES2065-1`                       | Reference rendering target. |

---

## 3. ACES working-space glossary

| Space         | Primaries | Encoding | Role |
|---------------|-----------|----------|------|
| **ACES2065-1** | AP0      | Linear   | Interchange / archival. |
| **ACEScg**    | AP1       | Linear   | Rendering, compositing. |
| **ACEScc**    | AP1       | Log (pure) | Grading controls behave like Cineon. |
| **ACEScct**   | AP1       | Log w/ toe | Grading, lift/printer-point friendly. |
| **ACESproxy** | AP1       | Quantized log | 10/12-bit on-set transmission. |

AP0 > AP1 > Rec.2020 > DCI-P3 > Rec.709/sRGB in gamut coverage.

---

## 4. Input/Output colorspace catalog (ACES studio-config v1.3 names)

**Display outputs** (`poutput`):
- `Output - sRGB`
- `Output - Rec.709`
- `Output - Rec.709 (D60 sim.)`
- `Output - DCI-P3 D65`
- `Output - P3-D60 ST2084 (1000 nits)`
- `Output - Rec.2020 ST2084` (HDR10 PQ mastering)
- `Output - Rec.2020 ST2084 (1000 nits)`
- `Output - Rec.2020 ST2084 (2000 nits)`
- `Output - Rec.2020 ST2084 (4000 nits)`
- `Output - Rec.2100 HLG` (HLG HDR)
- `Output - DCDM` (X'Y'Z' 2.6)

**Camera log inputs** (`pinput`):
- ARRI: `Input - ARRI - V3 LogC (EI800)`, `Input - ARRI - LogC4 (EI800)`
- Sony: `Input - Sony - S-Log3 - S-Gamut3`, `Input - Sony - S-Log3 - S-Gamut3.Cine`
- RED: `Input - RED - Log3G10 - REDWideGamutRGB`, `Input - RED - REDLogFilm - DRAGONcolor`
- Blackmagic: `Input - Blackmagic - Pocket 4K Film Gen 4`, `Input - Blackmagic Design Film Gen 5`
- Canon: `Input - Canon - Canon-Log3 - Cinema Gamut`, `Input - Canon - Canon-Log2 - Cinema Gamut`
- Panasonic: `Input - Panasonic - V-Log - V-Gamut`
- DJI: `Input - DJI - D-Log - D-Gamut`
- GoPro: `Input - GoPro - Protune Flat - ProtuneNative`

Always `ociocheck --iconfig $OCIO` to enumerate exact strings for your config.

---

## 5. OCIO filter vs native ffmpeg `colorspace` filter

| Concern                      | `ocio` filter                                   | `colorspace` filter                    |
|------------------------------|-------------------------------------------------|----------------------------------------|
| Transform catalog            | Entire OCIO config (ACES, camera logs, LMTs)    | Built-in: bt709/bt2020/bt601/smpte240m/fcc |
| LUT baking                   | Yes (IDT/ODT + LMTs)                            | No                                     |
| Display-referred output      | Yes (full Output Transform)                     | Partial (matrix + TRC only)            |
| Requires external config     | Yes (`$OCIO`)                                   | No                                     |
| Float-precision path         | Yes (must use `format=gbrpf32le`)               | Yes                                    |
| HDR PQ / HLG math            | Yes (ACES OutputTransform)                      | Manual (via `zscale` or `libplacebo`)  |
| Compile flag                 | `--enable-libocio` (rare in stock builds)       | Always present                         |

Rule of thumb: use `ocio` when you need ACES/LMT/film-emulation fidelity; use `colorspace`/`zscale` for simple primaries/TRC changes that don't need a managed look (see `ffmpeg-hdr-color`).

---

## 6. `ociobake` usage (fallback path)

When libocio is NOT compiled into ffmpeg, bake the transform to a 3D LUT and apply via `lut3d`.

```bash
ociobake \
  --iconfig $OCIO \
  --inputspace "ACES2065-1" \
  --outputspace "Output - Rec.709" \
  --format cinespace \
  --lutsize 33 \
  > aces_to_rec709.cube

ffmpeg -i in.exr \
  -vf "format=gbrpf32le,lut3d=aces_to_rec709.cube,format=yuv420p" \
  out.mp4
```

`--format` options (common): `cinespace` (.cube, DaVinci-friendly), `resolve_cube`, `houdini`, `iridas_itx`, `iridas_look`, `lustre`, `truelight`.

Lutsize: 17 (fast preview), **33 (standard)**, 65 (archival grade). Baking loses LMT runtime-tweakability; any parameter changes require re-bake.

For `ACEScc`/`ACEScct` sources — bake a matching chain:
```bash
ociobake --iconfig $OCIO --inputspace "ACEScc" --outputspace "Output - Rec.709" ...
```

---

## 7. ICC profile primaries / TRC reference

ffmpeg's `iccgen` filter takes:
- `primaries`: `bt709`, `bt470bg`, `bt470m`, `bt2020`, `smpte170m`, `smpte240m`, `smpte428`, `smpte431` (DCI-P3), `smpte432` (P3-D65), `film`.
- `trc`: `bt709`, `iec61966-2-1` (sRGB piecewise), `iec61966-2-4` (xvYCC), `smpte2084` (PQ), `arib-std-b67` (HLG), `linear`, `gamma22`, `gamma28`, `bt2020-10`, `bt2020-12`, `smpte428`.

Common pairings:
- Web / sRGB image:   `primaries=bt709 trc=iec61966-2-1`
- Rec.709 video:      `primaries=bt709 trc=bt709`
- DCI-P3 mastering:   `primaries=smpte431 trc=gamma22` (or `smpte428` for DCDM)
- P3-D65 display:     `primaries=smpte432 trc=iec61966-2-1`
- HDR10 PQ:           `primaries=bt2020 trc=smpte2084`
- HLG:                `primaries=bt2020 trc=arib-std-b67`

**ICC detection** with `iccdetect=force=1` prints a stream-level analysis including any embedded profile. Combine with `ffprobe -show_streams` to audit `color_primaries`/`color_transfer`/`color_space` tags.

ICC in MP4 is unreliable (only iTunes-flavored `colr` atom). **Use MKV or MOV** for dependable ICC embedding.

---

## 8. Vendor-specific camera log spaces

Each OCIO ACES config ships IDTs (Input Device Transforms). When you receive camera-native log footage, pick the right `pinput`. Shortlist:

| Vendor / Camera           | Log space                             | ACES config `pinput` (v1.3 studio)                           |
|---------------------------|---------------------------------------|--------------------------------------------------------------|
| ARRI Alexa (Gen 2/3)      | LogC3                                 | `Input - ARRI - V3 LogC (EI800)` (adjust EI)                 |
| ARRI Alexa 35             | LogC4                                 | `Input - ARRI - LogC4 (EI800)`                               |
| Sony F55/Venice/FX3       | S-Log3 / S-Gamut3.Cine                | `Input - Sony - S-Log3 - S-Gamut3.Cine`                      |
| RED Helium/Monstro        | Log3G10 / REDWideGamutRGB             | `Input - RED - Log3G10 - REDWideGamutRGB`                    |
| Blackmagic URSA/Pocket    | BMD Film Gen 4 / Gen 5                | `Input - Blackmagic Design Film Gen 5`                       |
| Canon C300/C500           | Canon-Log3 / Cinema Gamut             | `Input - Canon - Canon-Log3 - Cinema Gamut`                  |
| Panasonic VariCam / GH5S  | V-Log / V-Gamut                       | `Input - Panasonic - V-Log - V-Gamut`                        |
| DJI Zenmuse X7            | D-Log / D-Gamut                       | `Input - DJI - D-Log - D-Gamut`                              |
| GoPro HERO8+              | Protune Flat                          | `Input - GoPro - Protune Flat - ProtuneNative`               |
| iPhone ProRes Log (A17+)  | Apple Log / Rec.2020                  | v1.3+: `Input - Apple - Apple Log`                           |

If the camera shoots in an output-referred space (e.g. Rec.709 broadcast), use `Utility - Rec.709 - Display` or `Output - Rec.709` as `pinput` — NEVER treat Rec.709 footage as a log space.

---

## 9. Recipe book

### LogC → Rec.709 dailies
```bash
ffmpeg -i ARRI_A001_C001.mxf \
  -vf "format=gbrpf32le,ocio=pinput=Input - ARRI - V3 LogC (EI800):poutput=Output - Rec.709,format=yuv420p" \
  -c:v libx264 -crf 18 -c:a copy dailies.mp4
```

### ACES master → HDR10 PQ Rec.2020 (1000 nit target)
```bash
ffmpeg -i master.mov \
  -vf "format=gbrpf32le,ocio=pinput=ACES2065-1:poutput=Output - Rec.2020 ST2084 (1000 nits),format=yuv420p10le" \
  -c:v libx265 -x265-params "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,50):max-cll=1000,400" \
  -pix_fmt yuv420p10le hdr10.mp4
```

### DCI-P3 D65 → Rec.709 (theatrical → SDR web trailer)
```bash
ffmpeg -i dcp_proxy.mov \
  -vf "format=gbrpf32le,ocio=pinput=Utility - Rec.709 - DCI-P3 D65:poutput=Output - Rec.709,format=yuv420p" \
  -c:v libx264 -crf 18 web_trailer.mp4
```

(Space names are config-dependent — verify with `ociocheck --iconfig $OCIO`.)

### Film emulation LMT on ACEScct → Rec.709
```bash
ffmpeg -i graded_acescct.mov \
  -vf "format=gbrpf32le,ocio=pinput=ACEScct:poutput=Output - Rec.709:look=LMT_Analog_Exposure,format=yuv420p" \
  film_look.mp4
```

### Embed sRGB ICC on a web-bound Rec.709 export
```bash
ffmpeg -i rec709.mov \
  -vf "iccgen=primaries=bt709:trc=iec61966-2-1" \
  -c:v libx264 -crf 18 -c:a copy out.mkv
```

### Strip OCIO-free fallback: bake + lut3d
```bash
ociobake --iconfig $OCIO --inputspace "ACEScct" --outputspace "Output - Rec.709" \
  --format cinespace --lutsize 33 > acescct_to_709.cube
ffmpeg -i in.mov \
  -vf "format=gbrpf32le,lut3d=acescct_to_709.cube,format=yuv420p" \
  out.mp4
```

---

## 10. QC checklist before delivery

1. `ffprobe -v error -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space,color_range out.mp4` — tags match intended poutput.
2. Vectorscope + waveform via `ffplay` (see `ffmpeg-playback`). Memory colors (skin, sky) in plausible zones.
3. For HDR: MaxCLL/MaxFALL present (`mediainfo --Full`); see `ffmpeg-hdr-color`.
4. For IMF/studio: re-verify through `ffmpeg-mxf-imf`.
5. For web: confirm ICC present in MKV/MOV; MP4 delivery — rely on `colr` atom.
6. Diff vs a Resolve render (VMAF/SSIM via `ffmpeg-quality`) on a golden frame — ffmpeg OCIO binding has known drift vs Nuke/Resolve on edge-case LMTs.
