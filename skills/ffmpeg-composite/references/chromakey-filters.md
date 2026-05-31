# ffmpeg chromakey / despill / compositing — filter reference

This doc is a field manual for the key-filters ffmpeg ships with, plus the
codec/container choices that actually carry alpha. Read top-to-bottom when
building a new pipeline; jump to the cheat-sheets when tuning an existing one.

---

## 1. `chromakey` — YUV/UV distance key

Operates on chroma (U, V). Ignores luma. Robust to brightness variation across
the screen. This is the default greenscreen filter.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `color` | color | `green` | Color to key out. Hex `0x00FF00` or name `green`. |
| `similarity` | float | `0.01` | Radius of color tolerance in UV space. Typical `0.05`–`0.20`. |
| `blend` | float | `0.0` | Edge softness; 0 = binary, >0 = graded alpha. Typical `0.02`–`0.10`. |
| `yuv` | bool | `false` | Treat the `color` argument as raw YUV triplet instead of RGB. |

Usage: `chromakey=0x20B040:0.12:0.05`

Output pixel format: adds an alpha plane. Always chain `,format=yuva420p` (fast) or `,format=yuva444p` (clean edges, pro).

---

## 2. `colorkey` — RGB distance key

Operates in RGB. Simpler math but fails under uneven lighting (a shadowed green
becomes a different RGB distance than a hot green).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `color` | color | `black` | Color to key out. |
| `similarity` | float | `0.01` | RGB-distance tolerance. Typically MUCH higher than chromakey — try `0.20`–`0.40`. |
| `blend` | float | `0.0` | Edge softness. Try `0.10`–`0.25`. |

Usage: `colorkey=0x00FF00:0.30:0.20`

When to pick over `chromakey`: the source already has its color math done in
RGB (screen recordings, synthetic / CG output, UI video), or `chromakey`'s UV
similarity is fighting an unusual color cast.

---

## 3. `hsvkey` — HSV range key

Operates in HSV. Easier to tune on uneven lighting because hue stays stable
even as saturation/value change. The best tool for real-world greenscreens that
were lit with fluorescents or bent fabric.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `h` | float | 0 | Target hue in degrees (green ≈ 120, blue ≈ 240). |
| `s` | float | 0 | Target saturation (0–1). |
| `v` | float | 0 | Target value/brightness (0–1). |
| `similarity` | float | 0.01 | HSV tolerance. Typical `0.02`–`0.15`. |
| `blend` | float | 0.0 | Edge softness. Typical `0.01`–`0.05`. |

Usage: `hsvkey=h=120:s=0.7:v=0.3:similarity=0.05:blend=0.02`

When it wins: uneven green (fluorescent fall-off, shadows on the screen), keep-
your-hair-detail subjects, semi-translucent material (hair, glass, veil).

---

## 4. `lumakey` — luminance key

Keys on brightness. No color at all. Useful for black-on-white slide-over text,
silhouettes, generated mattes.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `threshold` | float | 0.0 | Luma value that becomes transparent. |
| `tolerance` | float | 0.01 | Range around threshold that becomes transparent. |
| `softness` | float | 0.0 | Edge softness. |

Usage: `lumakey=threshold=0.0:tolerance=0.01:softness=0.05`

---

## 5. `despill` — removes green/blue spill from the subject

Runs AFTER the key. Reduces saturation of the spill color specifically in
edge/hair regions, rebalances toward neutral.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `type` | enum | `green` | `green` or `blue`. |
| `mix` | float | 0.5 | Blend strength (0 none, 1 full). |
| `expand` | float | 0.0 | Dilate the affected region outward (`0`–`0.5`). |
| `red`, `green`, `blue` | float | varies | Fine-grained per-channel correction. |
| `brightness` | float | 0 | Post-correction brightness trim. |
| `alpha` | bool | false | Operate only where alpha exists. |

Usage: `despill=type=green:mix=0.5:expand=0.1`

This is NOT optional on real footage. Green bouncing off the screen paints the
subject's skin/hair/white-shirt. Chain it: `chromakey=...,despill=type=green,...`.

---

## 6. `backgroundkey` — static-plate background subtraction

Requires a clean plate (the same camera framing, NO subject). Subtracts the
plate from every frame; what remains is the subject. Only works with a LOCKED
camera. Useful when the background is busy (lots of colors) and you can't
paint it green — product demos, tabletop shoots.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `threshold` | float | 0.08 | Similarity threshold for "is this plate". |
| `similarity` | float | 0.1 | Similarity tolerance. |
| `blend` | float | 0.0 | Edge softness. |

Usage: `[0:v][1:v]backgroundkey=threshold=0.08:similarity=0.1:blend=0.05[keyed]`

Input 0 is the subject-in-scene shot; input 1 is the clean plate.

---

## 7. `chromakey_cuda` — GPU variant (NVIDIA)

Same concept as `chromakey`, same options, runs on CUDA. Must be wrapped:

```
hwupload_cuda,chromakey_cuda=0x00FF00:0.1:0.05,hwdownload,format=yuva420p
```

Needs `ffmpeg -hwaccel cuda` at the top of the command AND a supported GPU.
No YUV colorspace option — always interprets `color` as RGB hex.

---

## 8. Alpha-capable codec / container matrix

| Container | Codec | Pixel format | Notes |
|---|---|---|---|
| `.mov` | `qtrle` | `rgba` | Lossless RGBA, Apple Animation. Huge files. Safe everywhere. |
| `.mov` | `prores_ks -profile:v 4444` | `yuva444p10le` | Pro finishing standard. Accepted by Resolve, AE, FCP. |
| `.mov` | `prores_ks -profile:v 4444xq` | `yuva444p10le` | Higher bitrate ProRes 4444. |
| `.webm` | `libvpx-vp9` | `yuva420p` | Web-playable alpha. Use `-auto-alt-ref 0`. |
| `.mkv` | `ffv1` | `yuva420p`/`yuva444p` | Lossless, archival, FOSS-friendly. |
| `.png` (sequence `%05d.png`) | `png` | `rgba` | Fully portable. Works in every editor. |
| `.tiff` (sequence) | `tiff` | `rgba` | Same idea, higher bit depth. |

### Containers that CANNOT carry alpha

- `.mp4` + `libx264` / `libx265` — no alpha channel in H.264/HEVC spec as normally muxed.
- `.mp4` + `libvpx-vp9` — technically VP9 supports alpha but most MP4 muxers/players drop it; prefer `.webm`.
- `.avi` + anything — legacy, avoid.

### Recipes

```bash
# ProRes 4444 .mov
-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le

# VP9 .webm with alpha
-c:v libvpx-vp9 -pix_fmt yuva420p -b:v 4M -auto-alt-ref 0

# QuickTime Animation
-c:v qtrle

# PNG sequence
-c:v png frames/keyed_%05d.png
```

---

## 9. Similarity / blend tuning cheat-sheet

| Observation | Action |
|---|---|
| Screen still visible | `similarity` + 0.02 |
| Subject edges being eaten | `similarity` − 0.02 |
| Edges are jagged / stair-stepped | `blend` + 0.02 |
| Edges are mushy / ghostly | `blend` − 0.02 |
| Green fringe on skin/hair | add `despill=type=green:mix=0.5` |
| Hair detail gone | lower `similarity`, switch to `hsvkey` |
| One side of screen keys, other doesn't | switch to `hsvkey`, adjust lighting, or pre-correct with `eq`/`colorbalance` |
| Works on static frames, fails on motion | increase `blend` slightly; check for compression artifacts eating the UV signal |

Similarity/blend math is NOT linear. Bump in steps of `0.02`; watch a hard-edge
region (shoulder silhouette) and a soft-edge region (hair) simultaneously.

---

## 10. chromakey vs colorkey vs hsvkey — decision tree

```
Is the footage uneven / badly lit / real-world green?
├─ yes → hsvkey
└─ no
   └─ is the footage CG / RGB-native (screen recording, render)?
      ├─ yes → colorkey (big similarity, big blend)
      └─ no  → chromakey (default, YUV-smart)
```

Rule of thumb: try `chromakey` first — it succeeds on 70 % of greenscreen work.
If you can't make it clean in 3 tuning passes, switch to `hsvkey`. Reach for
`colorkey` only when you know the source is RGB-clean or you're keying a
synthetic/UI color.

---

## 11. Real-world green/blue hex samples

Pure hex values from actual shoots (sample your own; these are starting points):

| Material | Typical hex | Notes |
|---|---|---|
| Rosco DigiComp Green | `0x3EB34C` | Film/TV studio standard green. |
| Rosco DigiComp Blue | `0x1B74BA` | Film/TV standard blue. |
| Chroma key fabric (cheap) | `0x20B040` – `0x4CC856` | Varies wildly; sample each shoot. |
| Painted drywall (green) | `0x2D9A3A` – `0x38B04C` | Paint batch variation. |
| News blue screen | `0x2E6DB4` | Broadcast convention. |
| Lit green (hotspot) | `0x5BCE5F` | Brighter, desaturated. |
| Lit green (shadow) | `0x1A7A2B` | Darker, less saturated. |

NEVER trust `0x00FF00`. ALWAYS sample the actual color: take a screenshot of a
flat mid-tone region of the screen, load in Preview / GIMP / any image tool,
eyedrop, read hex.

---

## 12. Despill technique catalog

All of these run after the key, before the overlay:

| Situation | Recipe |
|---|---|
| Light green fringe on skin | `despill=type=green:mix=0.3` |
| Heavy green fringe on white shirt | `despill=type=green:mix=0.7:expand=0.15` |
| Blue fringe from blue screen | `despill=type=blue:mix=0.5` |
| Spill appears on hair only | `despill=type=green:mix=0.5:alpha=1` |
| Over-corrected (subject turned magenta) | lower `mix` to `0.2`, tweak `green` channel arg |
| Subject looks sickly even after despill | add `eq=saturation=1.05` after despill to restore warmth; or `colorbalance=rs=0.05:gs=-0.05` |

Stacking: a second `despill` pass at a lower mix sometimes cleans edge detail:

```
chromakey=...,despill=type=green:mix=0.5,despill=type=green:mix=0.2:expand=0.2
```

---

## 13. Pipeline order — the only legitimate order

```
source
  └─ (optional) pre-clean: denoise, eq correction on the green
       └─ key (chromakey / colorkey / hsvkey / lumakey / backgroundkey)
            └─ despill (type=green or type=blue)
                 └─ format=yuva420p or yuva444p
                      └─ (composite only) overlay onto bg
                           └─ encode (alpha-capable codec or flat delivery)
```

NEVER composite, then try to "clean up" the green after. Once overlaid, the
green IS the new image — you can no longer separate it from the bg signal.

---

## 14. Common filter-graph snippets

```bash
# Key + flatten over a solid color (no external bg needed)
[0:v]chromakey=0x20B040:0.12:0.05,despill=type=green[k];color=c=white:s=1920x1080[bg];[bg][k]overlay[out]

# Key + composite with scaled bg
[1:v]scale=1920:1080:force_original_aspect_ratio=cover,crop=1920:1080[bg];[0:v]chromakey=0x20B040:0.12:0.05,despill=type=green[k];[bg][k]overlay[out]

# Key with pre-denoise for grainy sources
[0:v]nlmeans=s=1.0,chromakey=0x20B040:0.10:0.05,despill=type=green[k]

# Two-stage key (inner clean + outer edge)
[0:v]chromakey=0x20B040:0.08:0.0[inner];[inner]chromakey=0x20B040:0.18:0.10[k]
```
