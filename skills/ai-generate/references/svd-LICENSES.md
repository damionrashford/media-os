# media-svd — strict license policy

Only OSI-open / clearly commercial-safe video weights.

## INCLUDE

| Model              | License     | Commercial? |
|--------------------|-------------|-------------|
| LTX-Video          | Apache 2.0  | Yes         |
| CogVideoX-2B / -5B | Apache 2.0  | Yes         |
| Mochi-1            | Apache 2.0  | Yes         |
| Wan-Video 2.1      | Apache 2.0  | Yes         |
| AnimateDiff        | Apache 2.0  | Yes         |

## EXCLUDE

| Model                         | License                    | Why excluded |
|-------------------------------|----------------------------|--------------|
| Stable Video Diffusion (SVD)  | SVD Community / OpenRAIL-M | NC for most tiers; use restrictions |
| Stable Video 1.1 / XT         | Stability Community        | Not commercial-safe without license |
| Zeroscope v2 XL               | CreativeML OpenRAIL-M      | Use restrictions; not OSI-open |
| ModelScope t2v-ms             | CC BY-NC 4.0               | Non-commercial |
| Sora                          | Proprietary (OpenAI)       | Closed API |
| Runway Gen-2 / Gen-3          | Proprietary (Runway)       | Closed API |
| Kling 1.x / 2.x               | Proprietary (Kuaishou)     | Closed API |
| Luma Dream Machine            | Proprietary (Luma)         | Closed API |
| HunyuanVideo                  | Tencent License 2.0        | Commercial cap; not default. Mention only. |

## Why HunyuanVideo isn't a default

Tencent License 2.0 permits commercial use BUT imposes a monthly-active-user cap
(~100M MAU). Practical for most companies but not OSI-open. We do not expose it in
the t2v subcommand; if a user explicitly asks for Hunyuan we let them know about
the cap and redirect to LTX / CogVideoX.

## Why SVD is excluded despite being called "SVD"

Stable Video Diffusion's "Community License" (and older OpenRAIL-M variants)
restricts commercial use to low revenue tiers and imposes content-type restrictions.
The skill name `media-svd` is retained as a category label (AI video generation);
the underlying models are NOT Stable Video Diffusion.

## Verification

Check the HF repo's LICENSE file before relying on commercial use:

```bash
curl -sL https://huggingface.co/<repo>/raw/main/LICENSE
curl -sL https://huggingface.co/<repo>/raw/main/README.md | head -50
```
