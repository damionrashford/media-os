# Parallax math — depth-driven 2D-to-stereo / 2.5D animation

Consult when tuning the forward-warp / hole-fill pipeline or implementing a custom stereo baseline model.

## Problem

Given a single RGB image `I(x, y)` and a per-pixel depth `D(x, y)` (inverse-relative, 0..1 with 1 = closest), produce a plausible "other viewpoint" image `I'(x', y)` where:

```
x' = x + f(D(x, y), baseline)
```

with `f` monotonic in D — i.e. closer pixels shift farther. This is depth-driven **horizontal parallax**. Two viewpoints (left and right) form a stereo pair.

## Forward warp vs inverse warp

- **Forward warp** — for each source pixel, scatter it to its new location. Multiple sources can land on the same destination (resolve with a Z-buffer, keeping the closest). Sources can land on no destination at all, creating **holes** (revealed background).
- **Inverse warp** — for each destination pixel, look up which source pixel should land here. Fast and antialias-friendly, but gets **occlusion handling wrong**: a destination pixel may "see through" the foreground to a background that should be hidden.

For 2D→stereo, **forward warp with Z-buffer + inpaint** is the correct approach.

## Algorithm in `depth.py stereo`

1. Normalize depth to `d ∈ [0, 1]` where 1 = closest.
2. Compute per-pixel shift: `shift(x, y) = d(x, y) * baseline_px`.
3. Initialize `dst` as black, `zbuf` as `-1` everywhere, `hole_mask` as all-ones.
4. **Scatter sources by depth order (smallest d first), so nearest pixels overwrite**:
   ```
   for each (x, y) sorted by d(x, y) ascending:
       x_new = round(x + shift(x, y))
       if 0 <= x_new < W and d(x, y) >= zbuf[y, x_new]:
           dst[y, x_new] = I[y, x]
           zbuf[y, x_new] = d(x, y)
           hole_mask[y, x_new] = 0
   ```
5. **Inpaint holes** (`hole_mask == 1`) using `cv2.inpaint(dst, hole_mask, 3, INPAINT_TELEA)`.

Both L and R views use the same algorithm with opposite-sign shift (±baseline/2).

## Why TELEA beats NS (Navier-Stokes) here

- `INPAINT_TELEA` (Telea 2004) — propagates from the hole boundary using a fast-marching method; preserves **edge continuity** in the direction of the hole. Perfect for the thin vertical strips of revealed background that parallax creates.
- `INPAINT_NS` (Bertalmio 2001) — minimizes the Laplacian across the hole; tends to blur high-frequency texture. Works better on round holes (scratches, dust), worse on the elongated holes parallax produces.

For parallax you almost always want TELEA.

## Why `radius=3` in cv2.inpaint

The holes from parallax are typically 1–`baseline_px` wide (not more than `max(shifts) - min(shifts)`). A radius of 3 is enough to propagate local edge information across a hole up to ~6–8 px wide, which covers baselines up to ~12 with typical depth ranges. Larger radii slow the algorithm without improving quality.

## Baseline scaling vs depth-range compression

With a fixed `baseline_px`, the perceived 3D effect depends on the *dynamic range* of the depth map:

- Flat depth (everything at similar distance) → small parallax even at large baseline.
- High depth contrast (close subject + distant background) → dramatic parallax.

If the stereo feels flat, **stretch the depth histogram** before warping:

```python
d = depth.astype(np.float32) / 65535.0
p5, p95 = np.percentile(d, [5, 95])
d = np.clip((d - p5) / (p95 - p5), 0, 1)
```

Don't do this for metric depth — it destroys the physical scale.

## Ken Burns / 2.5D orbit math

For animation, precompute N camera offsets `(dx_i, dy_i)` and render each frame with the same forward-warp + inpaint pipeline. The `depth.py parallax` subcommand uses:

- **orbit** — `dx = A sin(2π t)`, `dy = 0.4 A cos(2π t)`
- **pan-left/right** — monotonic linear shift
- **ken-burns** — `dx = 0.3 A sin(π t)`, plus a slight zoom (handled via crop+resize upstream)

Here `t ∈ [0, 1]` across frames, `A` is the amplitude in pixels.

Vertical parallax (`dy != 0`) works identically — just add `y + shift_y(d)` in the scatter step. The default script only does horizontal parallax because (a) human stereo vision is horizontal and (b) vertical parallax is subtle for single-image 2.5D.

## Baseline guidance

| Source resolution | `--baseline` px | Feel                                  |
|-------------------|-----------------|---------------------------------------|
| 720p              | 3–5             | Subtle 3D for phone viewing           |
| 1080p             | 5–10            | Natural stereo (human IPD-like)       |
| 1080p             | 10–16           | Exaggerated / anaglyph / VR           |
| 4K                | 10–20           | Natural                               |
| 4K                | 20–40           | VR headset native presentation        |

Above these, the hole-fill becomes visibly synthetic — switch to a larger depth model (`--size large`) or to video-aware matting before cranking the baseline further.

## Failure modes and fixes

- **Tearing on thin vertical structures** (fences, hair) → depth model misclassified the structure as background; pick a better model (`--size large`) or manually refine the depth map.
- **Smeared edges on rapid transitions** → inpaint radius too large; keep at 3.
- **Wobble in video parallax** → per-frame depth is unstable; apply temporal smoothing on the depth video before warping.
- **Uniform parallax (flat feel)** → depth dynamic range too low; stretch histogram before warping as shown above.
