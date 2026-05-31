# OpenEXR compression types

Load when the user asks which compression to pick, or how big / how fast /
how lossy each is.

## Cheat-sheet table

| Type | Lossless? | Speed | Ratio (typ) | Best for |
|---|---|---|---|---|
| `NONE` | yes | fastest | 1.0x | RAM debug / scratch files |
| `RLE` | yes | fast | ~1.5x | flat renders with big uniform areas |
| `ZIPS` | yes | medium | ~2.0x | general-purpose per-scanline; best random access |
| `ZIP` | yes | medium | ~2.5x | 16-line block zip; default for CG renders |
| `PIZ` | yes | slow | ~3.0x | grainy film scans, photographic noise |
| `PXR24` | no (float->24-bit) | fast | ~2.5x | deep bit-depth float where full 32-bit isn't needed |
| `B44` | no (fixed size) | fast | ~2.3x | realtime preview, guaranteed size |
| `B44A` | no | fast | ~2.3-4x | like B44 but collapses flat tiles to much smaller |
| `DWAA` | no (DCT) | medium | ~5-10x | deliverables; 32-scanline blocks |
| `DWAB` | no | medium | ~5-10x | like DWAA but 256-scanline blocks, bigger windows |
| `HTJ2K` | yes | slow | ~3.0x | EXR 3.2+; JPEG-2000-like wavelet |

## Selection guide by workflow

| Workflow | Recommended |
|---|---|
| Deep archive / no loss at all | `PIZ` (photographic) or `ZIP` (CG) |
| Renderer output (per-frame) | `ZIP` (default) |
| Texture cache (tiled) | `ZIPS` (per-scanline random access) |
| Delivery / streaming preview | `DWAA` at a moderate level |
| Deep data (deepscanline / deeptile) | `ZIPS` |
| HDR footage / plates | `PIZ` |

## Lossy knobs

- **DWAA / DWAB compression level** — set via `-dwaCompressionLevel <float>` in OpenEXR Core. Default 45.0. Lower = better quality, larger file. 100.0 is close to transparent.
- **PXR24** has no knobs — it's always float-to-24-bit-float truncation.
- **B44 / B44A** have no knobs.

## Gotchas

- **DWA is NOT lossless despite preserving float precision.** The DCT quantization happens below the noise floor of normal footage but is detectable in high-contrast edges.
- **PIZ compresses film grain extremely well** (30-50% smaller than ZIP) but is slow to decode — not great for timeline scrub.
- **ZIP vs ZIPS:** ZIP uses 16-scanline blocks, so reading one scanline means decompressing 16. ZIPS is per-scanline — better for random access, slightly worse ratio.
- **B44 gives GUARANTEED file size** (fixed 4:3 or 6:3 compression depending on channel count). Useful when you need to predict disk usage exactly.
- **HTJ2K is EXR 3.2+ only.** Older readers won't open HTJ2K files. Check `openexr.com` for your installed version.
- **Tiled EXR can use any compression** but DWAA/DWAB are less useful tiled (block boundaries cut into DCT blocks).
- **Deep images should use ZIPS, not ZIP.** The 16-line block in ZIP wreaks havoc on per-pixel variable-sample-count deep data.
