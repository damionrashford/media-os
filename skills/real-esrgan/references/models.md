# Real-ESRGAN models, CLIs, and the Python API

Source of truth: <https://github.com/xinntao/Real-ESRGAN>. Verify a release's bundled `LICENSE` before shipping.

## ncnn-vulkan binary — full flag reference

```
Usage: realesrgan-ncnn-vulkan -i infile -o outfile [options]...
  -i input-path     input image (jpg/png/webp) OR a directory
  -o output-path    output image OR a directory
  -s scale          upscale ratio: 2, 3, 4 (default 4)
  -t tile-size      >=32, or 0=auto (default 0); use 0,0,0 per-GPU for multi-GPU
  -m model-path     folder of pre-trained models (default: models)
  -n model-name     realesr-animevideov3 (default) | realesrgan-x4plus
                    | realesrgan-x4plus-anime | realesrnet-x4plus
  -g gpu-id         GPU device (default auto); 0,1,2 for multi-GPU
  -j load:proc:save thread counts (default 1:2:2); 1:2,2,2:2 for multi-GPU
  -x                enable TTA mode (8x slower, slightly higher quality)
  -f format         jpg | png | webp (default = input ext, else png)
  -v                verbose
```

The release zip bundles the binary + a `models/` directory holding each model's `.param` + `.bin`. `-n` names a model inside that directory — it is NOT a filesystem path.

## Model selection

| Model | Scale | Notes |
|---|---|---|
| `realesrgan-x4plus` | 4x | General real-world photos. The go-to for stills. |
| `realesr-animevideov3` | 2/3/4x | Video frames + cartoons; fastest; the ncnn default. Only multi-scale model. |
| `realesrgan-x4plus-anime` | 4x | Anime/illustration stills; ~1/4 the size of x4plus; sharper line art. |
| `realesrnet-x4plus` | 4x | The non-GAN net — less synthesized texture, more faithful, softer. |

## Python package (`pip install realesrgan`)

### CLI — `inference_realesrgan.py`

```
python inference_realesrgan.py -n RealESRGAN_x4plus -i infile -o outfile [options]
  -i --input        input image or folder (default: inputs)
  -o --output       output folder (default: results)
  -n --model_name   default RealESRGAN_x4plus
  -s --outscale     final upsample scale (default 4) — can be fractional, e.g. 3.5
  -t --tile         tile size, 0 = no tiling (default 0)
  --face_enhance    route faces through GFPGAN (default False)
  --fp32            full precision (use on CPU / GPUs without fast fp16)
  --suffix          output filename suffix (default: out)
  --ext             auto | jpg | png (default auto)
```

Common: `python inference_realesrgan.py -n RealESRGAN_x4plus -i infile --outscale 3.5 --face_enhance`

### Video — `inference_realesrgan_video.py` (PyTorch, CUDA)

```bash
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth -P weights
CUDA_VISIBLE_DEVICES=0 python inference_realesrgan_video.py \
  -i inputs/video/onepiece_demo.mp4 -n realesr-animevideov3 -s 2 --suffix outx2 \
  --num_process_per_gpu 2          # multi-process to saturate the GPU
# multi-GPU: CUDA_VISIBLE_DEVICES=0,1,2,3 ... --num_process_per_gpu 2
```

### Python API — `RealESRGANer`

```python
from realesrgan import RealESRGANer
model = RealESRGANer(scale=4, model_path='realesrgan_x4plus.pth', device='cuda')
output, _ = model.enhance(image_path='input_image.png')
# output is a numpy BGR array; write with cv2.imwrite('out.png', output)
```

`RealESRGANer(..., tile=256, tile_pad=10, pre_pad=0, half=True)` controls VRAM/precision. For faces, wrap with GFPGAN's `GFPGANer(bg_upsampler=<this RealESRGANer>)`.

## Weights (PyTorch `.pth`)

Released under the repo's BSD-3-Clause. From <https://github.com/xinntao/Real-ESRGAN/releases>:
- `RealESRGAN_x4plus.pth` (v0.1.0)
- `RealESRGAN_x4plus_anime_6B.pth` (v0.2.2.4)
- `realesr-animevideov3.pth` (v0.2.5.0)
- `realesr-general-x4v3.pth` (v0.2.5.0) — general scenes, supports a denoise-strength dial

## VRAM / performance

- 4K frame @ 4x ≈ 6 GB VRAM untiled. `-t 256` tiles to ~2 GB (slower; watch for seams → `-t 512`).
- ncnn-vulkan runs on Apple Silicon (Metal via Vulkan/MoltenVK), AMD, Intel, and NVIDIA — no CUDA needed. Prefer it unless you need `--face_enhance` or fractional `--outscale` (Python only).
- `-x` TTA averages 8 flips/rotations: ~8x slower for a small quality bump — rarely worth it for video.
