# media-sd — strict license policy

This skill only lists weights that are **OSI-open OR clearly commercial-safe**.
The list below is the authoritative INCLUDE/EXCLUDE policy. When a user asks for a
model not on the INCLUDE list, refuse and point them to a permissive alternative.

## INCLUDE (safe to recommend and run)

| Model              | License                  | Commercial? | Notes |
|--------------------|--------------------------|-------------|-------|
| FLUX.1 [schnell]   | Apache 2.0               | Yes         | Default. |
| Kolors             | Apache 2.0               | Yes         | |
| Sana (Apache)      | Apache 2.0               | Yes         | |
| Lumina-Next        | Apache 2.0               | Yes         | |
| PixArt-Sigma-XL    | Apache 2.0 (this repo)   | Yes         | Older PixArt-alpha may differ — verify per repo. |
| HunyuanDiT v1.2    | Tencent License 2.0      | Yes up to ~100M MAU | Not OSI-open; MAU cap. Flag before use at scale. |

## EXCLUDE (do NOT recommend, do NOT add presets for)

| Model                            | License                          | Why excluded |
|----------------------------------|----------------------------------|--------------|
| FLUX.1 [dev]                     | FLUX.1 [dev] Non-Commercial      | NC — non-commercial only. |
| Stable Diffusion 1.5 / 2.1       | CreativeML OpenRAIL-M            | Contains use-case restrictions; not OSI-open. |
| SDXL base / refiner              | CreativeML Open RAIL++-M         | Use restrictions; not OSI-open. |
| Stable Diffusion 3 / 3.5 base    | Stability Community / Research   | Commercial requires separate license; restrictions apply. |
| Stable Video Diffusion (SVD)     | SVD Community / OpenRAIL-M NC    | Non-commercial for many tiers. |
| Midjourney                       | Proprietary SaaS                 | Commercial API, not open. |
| DALL-E 2/3                       | Proprietary (OpenAI)             | Commercial API. |
| Imagen (Google)                  | Proprietary                      | Not open. |
| Firefly (Adobe)                  | Proprietary                      | Not open. |
| Ideogram                         | Proprietary                      | Not open. |

## Why we exclude CreativeML OpenRAIL-M

The **Responsible AI License (RAIL)** family is not recognized by the OSI. It
imposes use-case restrictions — no generation of illegal content, no harm, no
discrimination, etc. These are all reasonable requests, but they are **license
terms**, not mere policy; they restrict the field of use. An OSI-open license
cannot restrict the field of use. Therefore OpenRAIL-M models are not
redistributable in the same way Apache-licensed models are. Downstream users
must carry those restrictions forward.

## Why we flag HunyuanDiT but keep it

Tencent License 2.0 is "commercial except if you are really big". The 100M MAU
cap is well above most companies, so it's a practical commercial license for the
vast majority of use cases. It's NOT OSI-open, because OSI forbids any field-of-use
or user-size restrictions. Document the cap in Gotchas; don't default to it.

## Verification

When in doubt, fetch the current LICENSE file directly from the model's
HuggingFace repo — licenses can change per-checkpoint. Especially for PixArt,
Kolors forks, and community re-uploads.

```bash
curl -sL https://huggingface.co/<repo>/raw/main/LICENSE
```
