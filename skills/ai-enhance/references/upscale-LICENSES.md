# Licenses for bundled upscale models

Every model this skill recommends is open-source AND commercial-safe.
Research-only (CodeFormer) and commercial paid (Topaz) tools are explicitly
NOT recommended here.

| Model                  | License          | Commercial use? | Closed-source-product use? | Upstream                                                |
|------------------------|------------------|-----------------|----------------------------|---------------------------------------------------------|
| Real-ESRGAN            | BSD-3-Clause     | Yes             | Yes                        | https://github.com/xinntao/Real-ESRGAN                  |
| realesrgan-ncnn-vulkan | BSD-3-Clause + MIT (ncnn wrapper) | Yes | Yes                 | https://github.com/xinntao/Real-ESRGAN                  |
| Real-CUGAN             | MIT              | Yes             | Yes                        | https://github.com/bilibili/ailab/tree/main/Real-CUGAN  |
| realcugan-ncnn-vulkan  | MIT              | Yes             | Yes                        | https://github.com/nihui/realcugan-ncnn-vulkan          |
| SwinIR                 | Apache-2.0       | Yes             | Yes                        | https://github.com/JingyunLiang/SwinIR                  |
| HAT                    | Apache-2.0       | Yes             | Yes                        | https://github.com/XPixelGroup/HAT                      |
| GFPGAN                 | Apache-2.0       | Yes             | Yes                        | https://github.com/TencentARC/GFPGAN                    |
| waifu2x-ncnn-vulkan    | MIT              | Yes             | Yes                        | https://github.com/nihui/waifu2x-ncnn-vulkan            |
| Upscayl                | AGPL-3.0         | Yes*            | No (AGPL copyleft)         | https://github.com/upscayl/upscayl                      |
| chaiNNer               | GPL-3.0          | Yes*            | No (GPL copyleft)          | https://github.com/chaiNNer-org/chaiNNer                |

\* Using Upscayl / chaiNNer *as an app* to generate outputs is fine. Linking
their code (or substantially derived code) into your own closed-source product
triggers the copyleft obligation to release source under the same license.

## NOT recommended by this skill

| Tool              | License              | Why excluded                                |
|-------------------|----------------------|---------------------------------------------|
| CodeFormer        | S-Lab License 1.0    | Non-commercial / research-only              |
| Topaz Video AI    | Commercial (paid)    | Proprietary; not open-source                |

## Model weights vs. code

- Real-ESRGAN, Real-CUGAN, SwinIR, HAT, GFPGAN, waifu2x — weights share the same
  license as the code repository. BSD / MIT / Apache-2.0 — all commercial-safe.
- Always re-check the specific release's `LICENSE` file before shipping in a
  product, in case a future release changes terms.

## Boilerplate attribution (commercial-safe use)

Below is minimal attribution for a product that ships outputs generated with
these models. Paste into your product's NOTICES / third-party licenses page:

    This product uses AI super-resolution models:
      Real-ESRGAN  (BSD-3-Clause)  https://github.com/xinntao/Real-ESRGAN
      Real-CUGAN   (MIT)           https://github.com/bilibili/ailab/tree/main/Real-CUGAN
      SwinIR       (Apache-2.0)    https://github.com/JingyunLiang/SwinIR
      HAT          (Apache-2.0)    https://github.com/XPixelGroup/HAT
      GFPGAN       (Apache-2.0)    https://github.com/TencentARC/GFPGAN
      waifu2x      (MIT)           https://github.com/nihui/waifu2x-ncnn-vulkan

BSD-3-Clause / Apache-2.0 require keeping the copyright and license text with
any distributed binary or source. MIT requires retaining the copyright line.
