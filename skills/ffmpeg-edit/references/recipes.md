# Frame & image recipe book

30+ copy-paste recipes for ffmpeg frame extraction, sprite/contact sheets, GIF authoring, and image-sequence I/O. All commands assume `ffmpeg` on `$PATH`; swap in `/opt/homebrew/bin/ffmpeg` on macOS if your shell doesn't see it.

## 1. Single screenshots

### 1. Fast thumbnail at 1m30s (keyframe-snapped)
```bash
ffmpeg -ss 00:01:30 -i in.mp4 -vframes 1 -q:v 2 out.jpg
```

### 2. Frame-accurate still at exactly 1m30.250s
```bash
ffmpeg -i in.mp4 -ss 00:01:30.250 -vframes 1 -q:v 2 exact.jpg
```

### 3. Lossless PNG poster at 10s
```bash
ffmpeg -ss 10 -i in.mp4 -vframes 1 -c:v png poster.png
```

### 4. Scaled 720p-wide thumbnail
```bash
ffmpeg -ss 30 -i in.mp4 -vframes 1 -vf "scale=720:-1" -q:v 2 720.jpg
```

### 5. WebP lossy thumbnail (smaller than JPEG at equal quality)
```bash
ffmpeg -ss 30 -i in.mp4 -vframes 1 -c:v libwebp -quality 80 thumb.webp
```

### 6. BMP (for tools that need raw bitmaps)
```bash
ffmpeg -ss 30 -i in.mp4 -vframes 1 -c:v bmp raw.bmp
```

## 2. Sequence / bulk extraction

### 7. Every second
```bash
ffmpeg -i in.mp4 -vf fps=1 frame_%04d.jpg
```

### 8. Every 10 seconds
```bash
ffmpeg -i in.mp4 -vf fps=1/10 frame_%04d.jpg
```

### 9. Every 0.25s (4 fps dump) as PNG
```bash
ffmpeg -i in.mp4 -vf fps=4 frame_%05d.png
```

### 10. All frames (careful — very many files)
```bash
ffmpeg -i in.mp4 frame_%06d.png
```

### 11. Only frames 100..200
```bash
ffmpeg -i in.mp4 -vf "select='between(n,100,200)'" -vsync vfr clip_%04d.jpg
```

### 12. Keyframes (I-frames) only
```bash
ffmpeg -i in.mp4 -vf "select='eq(pict_type,I)'" -vsync vfr key_%04d.jpg
```

### 13. Scene-change detection (threshold 0.3 = medium)
```bash
ffmpeg -i in.mp4 -vf "select='gt(scene,0.3)'" -vsync vfr scene_%04d.jpg
```

### 14. Smart thumbnail (representative frame of 100-frame window)
```bash
ffmpeg -i in.mp4 -vf "thumbnail=100,scale=640:-1" -frames:v 1 smart.jpg
```

### 15. Start numbering sequence at 1000
```bash
ffmpeg -i in.mp4 -vf fps=1 -start_number 1000 frame_%04d.jpg
```

## 3. Contact sheets (tile filter)

### 16. 4x4 sheet at 5s intervals, 320px wide cells
```bash
ffmpeg -i in.mp4 -vf "fps=1/5,scale=320:-1,tile=4x4" -frames:v 1 sheet.jpg
```

### 17. 6x6 sheet sampling every 15s
```bash
ffmpeg -i in.mp4 -vf "fps=1/15,scale=240:-1,tile=6x6" -frames:v 1 sheet6.jpg
```

### 18. Contact sheet with gaps between cells (tile `padding`)
```bash
ffmpeg -i in.mp4 -vf "fps=1/5,scale=320:-1,tile=4x4:padding=4:color=white" \
  -frames:v 1 padded.jpg
```

### 19. Contact sheet with index number burned in (select + drawtext)
```bash
ffmpeg -i in.mp4 -vf "fps=1/5,scale=320:-1,drawtext=text='%{n}':x=4:y=4:fontcolor=yellow:fontsize=16:box=1:boxcolor=black,tile=4x4" \
  -frames:v 1 numbered.jpg
```

## 4. Sprite sheets (for HLS/DASH scrubbers)

### 20. 10x10 sprite, 160px cells, every 10s
```bash
ffmpeg -i movie.mp4 -vf "fps=1/10,scale=160:-1,tile=10x10" -frames:v 1 sprites.jpg
```

### 21. Multiple sprite sheet chunks (100 thumbs per sheet, numeric output)
```bash
ffmpeg -i movie.mp4 -vf "fps=1/10,scale=160:-1,tile=10x10" sprites_%03d.jpg
```

### Sprite math for HLS `EXT-X-IMAGE-STREAM-INF`
- Pick cell size (width W, height H=W/aspect). E.g. 160x90 for 16:9.
- Pick interval I (seconds per sprite).
- Pick grid C x R. Coverage per sheet = C*R*I seconds.
- Sheets needed: `ceil(duration / (C*R*I))`.
- In the `.m3u8` image stream manifest, each `#EXT-X-TILES:RESOLUTION=WxH,LAYOUT=CxR,DURATION=I` declares the geometry for one sheet.

Example for a 90-min movie, 10s interval, 10x10 grid of 160x90:
- Coverage per sheet = 10*10*10 = 1000s.
- Sheets needed = ceil(5400/1000) = 6.

## 5. High-quality GIFs

### 22. Baseline: palette + paletteuse (two passes)
```bash
ffmpeg -i in.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,palettegen=max_colors=256" -y palette.png
ffmpeg -i in.mp4 -i palette.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  -y out.gif
```

### 23. Tiny GIF (fps 10, width 320, fewer colors)
```bash
ffmpeg -i in.mp4 -vf "fps=10,scale=320:-1:flags=lanczos,palettegen=max_colors=128" -y p.png
ffmpeg -i in.mp4 -i p.png \
  -lavfi "fps=10,scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  -y tiny.gif
```

### 24. Max-quality GIF (Floyd–Steinberg dither)
```bash
ffmpeg -i in.mp4 -vf "fps=20,scale=600:-1:flags=lanczos,palettegen=stats_mode=full" -y p.png
ffmpeg -i in.mp4 -i p.png \
  -lavfi "fps=20,scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=floyd_steinberg" \
  -y max.gif
```

### 25. Clip + GIF in one go (10s clip starting at 1:00)
```bash
ffmpeg -ss 60 -t 10 -i in.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,palettegen" -y p.png
ffmpeg -ss 60 -t 10 -i in.mp4 -i p.png \
  -lavfi "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  -y clip.gif
```

### GIF dither comparison
| Dither                      | Size (rel.) | Quality           | Use for              |
| --------------------------- | ----------- | ----------------- | -------------------- |
| `none`                      | 1.0x        | Visible banding   | Flat/cartoon content |
| `bayer:bayer_scale=5` (def) | ~1.2x       | Sweet spot        | Most videos          |
| `bayer:bayer_scale=3`       | ~1.3x       | Coarser texture   | Stylized             |
| `sierra2`                   | ~1.6x       | Smooth            | Photos               |
| `floyd_steinberg`           | ~1.8x       | Best, but biggest | Showcase GIFs        |

### GIF fps / size trade-off (480px wide, 10s clip)
| fps | approx size | smoothness  |
| --- | ----------- | ----------- |
| 10  | 1.0x        | Choppy      |
| 15  | 1.4x        | Web default |
| 20  | 1.8x        | Smooth      |
| 30  | 2.6x        | Native      |

## 6. Image sequence → video

### 26. PNG sequence at 30 fps → H.264 MP4
```bash
ffmpeg -framerate 30 -i img_%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4
```

### 27. With CRF tuning (lower = better; 18 is visually lossless-ish)
```bash
ffmpeg -framerate 30 -i img_%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p out.mp4
```

### 28. Start at a non-zero index
```bash
ffmpeg -framerate 24 -start_number 100 -i img_%04d.png out.mp4
```

### 29. Glob pattern
```bash
ffmpeg -framerate 30 -pattern_type glob -i 'frames/*.png' out.mp4
```

### 30. Loop still images to video (e.g. slideshow frame for 5s each)
```bash
# One image, looped for 5s at 30fps:
ffmpeg -loop 1 -framerate 30 -t 5 -i photo.png -c:v libx264 -pix_fmt yuv420p out.mp4
```

### 31. ProRes output from PNG sequence (editorial delivery)
```bash
ffmpeg -framerate 24 -i img_%04d.png -c:v prores_ks -profile:v 3 out.mov
```

### 32. Sequence → WebM VP9
```bash
ffmpeg -framerate 30 -i img_%04d.png -c:v libvpx-vp9 -crf 32 -b:v 0 out.webm
```

## 7. Picture format flags

### JPEG
- `-q:v N`: quality scale 2 (best) .. 31 (worst). Default ≈ 3.
- Web: `-q:v 5`. Archival: `-q:v 2`.

### PNG
- `-compression_level N`: 0 (store) .. 100 (smallest; slow). Default ≈ 100.
- `-pred mixed|avg|paeth|up`: filter choice (usually leave default).

### WebP
- `-quality 0..100`; `-lossless 1` for lossless.
- `-preset picture|photo|drawing|icon|text`.

### TIFF
- `-compression_algo none|lzw|deflate|packbits`.

### image2 demuxer options (input-side)
- `-framerate N` — read images at N fps.
- `-start_number N` — first numeric filename index.
- `-pattern_type sequence|glob|glob_sequence` — how the pattern expands.
- `-loop 1` — loop the (single) input image forever.
- `-thread_queue_size N` — if the decoder chokes on bursty I/O.

### image2 muxer options (output-side)
- `-frames:v N` — stop after N output frames (use with `tile`).
- `-q:v N` — JPEG quality.
- `-update 1` — always overwrite the same file (for single-frame outputs like `thumb.jpg`).

## 8. Seeking cheat sheet

| Syntax                            | Speed         | Accuracy                     |
| --------------------------------- | ------------- | ---------------------------- |
| `-ss T -i in.mp4` (pre-input)     | Fast          | Keyframe-snapped (±GOP)      |
| `-i in.mp4 -ss T` (post-input)    | Slow          | Frame-accurate               |
| `-ss T1 -to T2 -i in.mp4`         | Fast          | Keyframe-snapped, duration   |
| `-ss T1 -i in.mp4 -t D`           | Fast          | Keyframe start, exact length |
| `-ss T1 -i in.mp4 -ss T2 -vf ...` | Best of both  | Fast scan + frame-accurate   |

The last pattern: pre-input seek near the target, then a short post-input seek for precision. Common trick for scripted bulk extraction.

## 9. Common pitfalls (reference)

- `image2` pattern must match actual zero-padding width (`img_%04d.png` ↔ `img_0001.png`).
- `-framerate` is the image2 demuxer input rate; `-r` is the output rate.
- `tile=MxN` consumes exactly `M*N` frames per output; pair with `-frames:v 1` for a single sheet.
- `paletteuse` needs palette as input `#1` (`-i palette.png`) and the `[1:v]` label.
- `-q:v 2` only applies to lossy codecs (JPEG, MJPEG, WebP). Ignored for PNG.
- `-vsync vfr` avoids duplicate frames when using `select=`.
- Alpha channels are lost when outputting JPEG; use PNG or WebP for transparency.
