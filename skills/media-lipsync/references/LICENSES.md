# media-lipsync — strict license policy

Only MIT / Apache 2.0 / BSD lip-sync + talking-head models. No research-only, no
non-commercial, no proprietary APIs.

## INCLUDE

| Model         | License    | Commercial? | Notes |
|---------------|-----------|-------------|-------|
| LivePortrait  | MIT        | Yes         | Kuaishou 2024. Code AND weights are MIT. |
| LatentSync    | Apache 2.0 | Yes         | ByteDance 2025. Per HF model card. |

## EXCLUDE

| Model                       | License / Issue                         | Why excluded |
|-----------------------------|-----------------------------------------|--------------|
| Wav2Lip (original)          | Research-only, author's explicit ban    | Rudrabha / IIIT explicitly asks commercial users not to use; third-party forks redistribute NC-restricted weights |
| Wav2Lip-GFPGAN cascade      | GFPGAN weights are separate (Apache/MIT); Wav2Lip part still NC | Compound license problem |
| SadTalker                   | Code Apache 2.0; weights fine-tuned on SD 1.5 (OpenRAIL-M) + 3DMM priors with unclear redistribution terms | License-washed weights; don't trust at scale |
| MuseTalk                    | Weights released under Tencent License with NC restrictions | Not commercial-safe |
| VideoReTalking              | CC BY-NC-SA 4.0                          | Non-commercial |
| IP-LAP                      | Research-only                            | Author's license forbids commercial |
| HeyGen                      | Proprietary SaaS                         | Commercial API only |
| D-ID                        | Proprietary SaaS                         | Commercial API only |
| Synthesia                   | Proprietary SaaS                         | Commercial API only |
| Runway Act-One              | Proprietary                              | Commercial API |

## Why Wav2Lip in particular is excluded

Wav2Lip (IIIT Hyderabad, 2020) has an explicit commercial-use prohibition in
the repo. Dozens of forks quietly redistribute the same checkpoints — they do
not launder the license. When a user says "lip sync" they often mean Wav2Lip
from memory. Redirect: LivePortrait + LatentSync cascade gives better quality
AND is commercially clean.

## Why SadTalker is excluded despite "Apache 2.0"

SadTalker ships Apache 2.0 code but its weights are fine-tuned from:
- SD 1.5 latents (CreativeML OpenRAIL-M — field-of-use restrictions).
- PIRenderer (research-only).

The resulting weights inherit upstream license constraints. Reasonable people
disagree on whether fine-tune weights inherit license; we take the safe path
and exclude. LivePortrait is a clean-room alternative with no SD lineage.

## Ethical guardrail (not a license concern but worth flagging)

Both LivePortrait and LatentSync can produce deepfakes. Always:

- Obtain consent from the subject when retargeting expressions.
- Watermark generated content if redistributed publicly.
- Do not impersonate real people without permission.
- Comply with local AI-disclosure laws (CA, CO, EU AI Act).

## Verification

```bash
curl -sL https://raw.githubusercontent.com/KwaiVGI/LivePortrait/main/LICENSE
curl -sL https://raw.githubusercontent.com/bytedance/LatentSync/main/LICENSE
```
