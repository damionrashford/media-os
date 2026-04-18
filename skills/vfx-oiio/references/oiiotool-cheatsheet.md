# oiiotool cheat-sheet

Stack-based Swiss Army knife. Every input pushes on the stack; every op
consumes the top N and pushes the result. Read bottom-up if you're used
to node graphs.

Source: `https://openimageio.readthedocs.io/en/latest/oiiotool.html`.

## 1. Simplest convert

```bash
oiiotool in.exr -o out.tif
```

## 2. Inspect with stats

```bash
oiiotool --info -v in.exr --stats
```

## 3. Resize + save

```bash
oiiotool big.exr --resize 1920x1080 -o small.exr
# filter options: box, triangle, gaussian, blackman-harris, lanczos3
oiiotool big.exr --resize:filter=lanczos3 1920x1080 -o small.exr
```

## 4. Crop to a data window

```bash
oiiotool in.exr --crop 1720x880+100+100 -o out.exr
# Syntax: WIDTHxHEIGHT+X+Y
```

## 5. Composite fg over bg (premultiplied)

```bash
oiiotool bg.exr fg.exr --over -o comp.exr
```

## 6. Composite with straight-alpha input

```bash
oiiotool bg.exr fg.exr --unpremult --over --premult -o comp.exr
# --Aover is the straight-alpha native op:
oiiotool bg.exr fg.exr --Aover -o comp.exr
```

## 7. Color-convert (requires $OCIO)

```bash
oiiotool --colorconfig $OCIO in.exr --colorconvert sRGB ACEScg -o out.exr
```

## 8. Apply a display transform (for previews)

```bash
oiiotool in_acescg.exr --ociodisplay "sRGB" "Rec.709" -o preview.png
# or a look:
oiiotool in.exr --ociolook "Filmic" -o look.exr
```

## 9. Bake a LUT file

```bash
oiiotool in.exr --ociofiletransform my_look.cube -o out.exr
```

## 10. Metadata edit (set a tag)

```bash
oiiotool in.exr --attrib "owner" "Damion" -o tagged.exr
oiiotool in.exr --caption "Hero shot final" -o captioned.exr
oiiotool in.exr --keyword "lookdev" --keyword "interior" -o tagged.exr
```

## 11. Channel shuffle (rewire channels)

```bash
# Reorder RGBA -> BGRA:
oiiotool in.exr --ch B,G,R,A -o bgra.exr
# Pull just alpha out:
oiiotool in.exr --ch A -o alpha.exr
# Append a new channel:
oiiotool in.exr const_mask.exr --chappend -o in_with_mask.exr
```

## 12. Build MIP-mapped tiled texture

```bash
maketx -o texture.tx in.exr
# for an IBL preserving HDR:
maketx --hdri --filter box -o studio.tx studio.exr
# bake sRGB -> linear during texture creation:
maketx --colorconvert sRGB linear -o diffuse.tx diffuse.png
```

## 13. Deep compositing

```bash
# Convert flat RGBA to deep:
oiiotool in.exr --deepen -o deep.exr
# Merge two deep renders:
oiiotool a_deep.exr b_deep.exr --deepmerge -o merged_deep.exr
# Deep holdout matte (knock A out of B):
oiiotool b_deep.exr a_deep.exr --deepholdout -o held.exr
# Flatten deep back to RGBA:
oiiotool deep.exr --flatten -o flat.exr
```

## 14. Generators (no input image)

```bash
# A solid color:
oiiotool --create 1920x1080 4 --pattern constant:color=0.5,0.5,0.5,1 1920x1080 4 -o gray.exr
# A ramp for testing:
oiiotool --pattern "checker" 1920x1080 4 -o checker.exr
# Text burn-in:
oiiotool in.exr --text:x=100:y=100:size=48:color=1,1,1,1 "hello" -o text.exr
```

## 15. Perceptual diff with output

```bash
idiff -o diff.exr --fail 0.01 --warn 0.001 render_a.exr render_b.exr
```

## 16. Tile / pad for renderer ingest

```bash
# Pad to the nearest POT:
oiiotool in.exr --resize 2048x2048 -o pot.exr
# Add data-window overscan:
oiiotool in.exr --fullsize 2048x2048+0+0 -o padded.exr
```

## 17. Slap-comp a stack of AOVs

```bash
oiiotool \
  beauty.exr diffuse.exr specular.exr \
  --add --add \
  -o sum.exr
# 3 images, 2 --add ops, produces one summed result.
```

## Gotchas

- **Operator precedence is stack depth**, not argument order. `--resize` only looks at the top image; it doesn't know about files later in the command line.
- **`-o` consumes one image off the stack.** Multiple `-o` in one invocation = writing the stack's top image to each target in order.
- **`--unpremult` / `--premult` should wrap color ops on alpha-containing images** (scale, color-correct, resize). Skipping them produces dark halos around compositing edges.
- **`--resize` ignores aspect** if you give it `WxH`. Preserve aspect with `WxH!` syntax or use `--resample WxH --keep-aspect`.
- **`--colorconvert` honors `$OCIO`.** Without an OCIO config, only a fixed list of built-in spaces (sRGB, linear, Rec.709) is available.
