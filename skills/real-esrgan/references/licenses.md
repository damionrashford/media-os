# Real-ESRGAN — license & commercial-safety

Real-ESRGAN is **commercial-safe**. Always re-check the specific release's `LICENSE` before shipping outputs or code in a product.

| Component | License | Commercial use | Weights | Source |
|---|---|---|---|---|
| Real-ESRGAN (code + weights) | BSD-3-Clause | Yes | Yes (same as code) | <https://github.com/xinntao/Real-ESRGAN> |
| `realesrgan-ncnn-vulkan` | BSD-3-Clause + MIT (ncnn wrapper) | Yes | Yes | <https://github.com/xinntao/Real-ESRGAN/releases> |
| GFPGAN (used by `--face_enhance`) | Apache-2.0 | Yes | Yes | <https://github.com/TencentARC/GFPGAN> |

## Boilerplate attribution (when bundling in a product)

```
This product uses Real-ESRGAN (BSD-3-Clause) — https://github.com/xinntao/Real-ESRGAN
Face enhancement uses GFPGAN (Apache-2.0) — https://github.com/TencentARC/GFPGAN
```

## Explicitly EXCLUDED (do not recommend, even though tutorials do)

- **CodeFormer** — S-Lab License, research-only. NOT commercial-safe.
- **Topaz Video AI / Gigapixel** — commercial paid software, not open source.
- **GFPGAN weights v1.4** are Apache-2.0 and fine; the model only *invents* face detail — never use it on identity-critical / evidentiary images without sign-off.

## Notes

- ncnn-vulkan and the Python package ship the same model weights under the same BSD-3-Clause grant.
- BSD-3-Clause requires preserving the copyright notice + disclaimer and not using the authors' names to endorse derived products. No copyleft, no source-disclosure obligation.
