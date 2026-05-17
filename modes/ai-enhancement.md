# Mode: ai-enhancement

**Subagent**: `architect`
**Trigger phrases**: "upscale this", "interpolate frames", "denoise AI", "remove background", "rotoscope", "matte", "depth estimate", "AI upscale", "RIFE", "Real-ESRGAN", "BiRefNet", "Depth-Anything", "enhance with AI"
**Output**: `${MEDIA_WORK_DIR}/modes/ai-enhancement/{date}_{slug}/`

## Inputs

- **Required**:
  - `source` — input video or image.
  - `enhancement` — one or more of: `upscale`, `interpolate`, `denoise`, `matte`, `depth`, `lipsync`.
- **Optional**:
  - `upscale_factor` — `2x` (default), `4x`.
  - `interpolate_target_fps` — final fps (default: 2× source fps).
  - `denoise_strength` — `light` / `medium` (default) / `heavy`.
  - `matte_output` — `alpha` (default, RGBA) / `mask` (greyscale).
  - `model_override` — name a specific model (must pass license filter).

## Steps

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/workflow-ai-enhancement/SKILL.md`. Read each relevant tool-skill: `media-upscale`, `media-interpolate`, `media-denoise-ai`, `media-matte`, `media-depth`, `media-lipsync`.
2. For each requested enhancement, read `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/references/LICENSES.md` and pick the highest-quality Apache-2 / MIT / BSD / GPL model:
   - **upscale**: Real-ESRGAN (BSD) > SwinIR (Apache-2) > HAT (Apache-2). NOT: ESRGAN-Plus (research-only).
   - **interpolate**: RIFE (MIT) > FILM (Apache-2). NOT: DAIN (research-only).
   - **denoise**: DeepFilterNet (MIT, audio) > RNNoise (BSD, audio); video → custom Real-ESRGAN denoise model (BSD).
   - **matte**: BiRefNet (MIT) > rembg (MIT) > RVM (GPL). NOT: CodeFormer (research-only).
   - **depth**: Depth-Anything-V2 (Apache-2) > MiDaS (MIT).
   - **lipsync**: LivePortrait (MIT) > LatentSync (Apache-2). NOT: Wav2Lip (research-only).
3. **STOP** if `model_override` names a restricted model — surface the licensed alternative and wait for approval.
4. `moprobe --json <source>` to capture resolution, fps, duration, codec. If image, capture dimensions.
5. For each enhancement in order:
   - Run the underlying skill's helper script (`uv run ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<helper>.py --input <prev> --output <next>`).
   - On GPU-bound steps, surface estimated runtime (resolution × frame count × model factor). Confirm with operator for jobs > 1 hour.
6. After AI pass(es), run `moqc --ref <source> --out <final>` if upscale or interpolate was applied (perceptual sanity check, not a gate).
7. If output is a frame sequence, optionally re-mux to video via `ffmpeg-transcode` using the source's original codec or as specified.
8. **`mosafe`-wrap** any final re-mux ffmpeg call.
9. Write `summary.md` with model selection + license per step, runtime per step, before/after metrics.

## Output schema

```markdown
# AI enhancement — {slug} — {date}

## Source
- **Path**: {source}
- **Type**: {video / image}
- **Resolution / fps / duration**: {WxH} / {fps} / {hh:mm:ss}

## Enhancement chain
| # | Enhancement | Model | License | Runtime | Output path |
|---|---|---|---|---|---|
| 1 | ... | ... | Apache-2 / MIT / BSD / GPL | ... | ... |
| 2 | ... | ... | ... | ... | ... |

## Comparison
- **Source size**: {bytes}
- **Final size**: {bytes}
- **VMAF (final vs source upscaled-to-final)**: {N or N/A}
- **Visual delta**: {qualitative — texture detail, motion smoothness, etc.}

## Output
- **Final file**: {path}
- **Intermediate frames** (if kept): {path}
```

## Quality bar

- Every model used is Apache-2 / MIT / BSD / GPL — no NC / research-only / commercial-restricted.
- License filter checked AGAINST `references/LICENSES.md`, not inferred from model name.
- For long jobs (>1hr), runtime estimate was surfaced before launch.
- Output re-probed (resolution / fps / duration as expected for the enhancement chain).
- If enhancement chain involves both upscale and interpolate, run upscale FIRST (interpolation on higher-resolution frames is more stable).
