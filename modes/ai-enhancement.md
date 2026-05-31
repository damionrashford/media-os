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

1. Read each relevant tool-skill: `ai-enhance`, `ai-enhance`, `ai-enhance`, `ai-understand`, `ai-understand`, `ai-lipsync`.
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
7. If output is a frame sequence, optionally re-mux to video via `ffmpeg-encode` using the source's original codec or as specified.
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

## Playbook reference (folded from workflow-ai-enhancement)

**What:** Take existing footage and make it visually/sonically better using open-source AI. Strict license discipline: Apache-2 / MIT / BSD / GPL only. NC / research-only models are documented-and-dropped.

## Pipeline

### Step 1 — Probe source

`ffmpeg-analyze`. Capture resolution, frame rate, codec artifacts, audio noise floor, color space (BT.601 / BT.709 / SDR), bit depth, chroma.

### Step 2 — Undo legacy artifacts BEFORE AI

- **Telecined 29.97i → 23.976p** — `ffmpeg-restore` (`fieldmatch → decimate`).
- **True interlaced** — `yadif` via `ffmpeg-filter`.
- **Compression noise** — `ffmpeg-restore` (`nlmeans`, `hqdn3d`).
- **Unstable handheld** — `ffmpeg-restore` two-pass (`vidstabdetect` → `vidstabtransform`).

### Step 3 — AI super-resolution

Use `ai-enhance`:
- **Real-ESRGAN x4plus** — live-action default.
- **Real-ESRGAN anime6b** — animation.
- **SwinIR** — graphics / text.
- **HAT** — best-quality slowest.
- **Face-enhance** — for close-ups; never use CodeFormer (NC).

### Step 4 — Frame interpolation

`ai-enhance`:
- **RIFE v4.6** (MIT) — handles scene cuts.
- **FILM** (Apache-2) — slightly smoother, drops on scene cuts.

Target integer multiples for clean math (23.976 → 47.952 exact 2×). 23.976 → 60 is 2.504× — quality suffers on fractional positions.

### Step 5 — AI audio denoise

`ai-enhance`:
- **DeepFilterNet** — general, 16 kHz or 48 kHz MONO only.
- **RNNoise** — lightweight, hardcoded 48 kHz mono 16-bit.
- **Resemble Enhance** — speech super-res.

Isolate stems first with `media-demucs` if source is mixed.

### Step 6 — Background removal (optional)

`ai-understand`:
- **rembg** (MIT) — fastest.
- **BiRefNet / RMBG-2.0** — stills only; per-frame for video produces temporal flicker.
- **RVM (RobustVideoMatting)** — temporally coherent, GPL-3 (propagates if shipped embedded; commercial OK via dynamic linking).

### Step 7 — Depth estimation (optional)

`ai-understand`:
- **Depth-Anything v2** (Apache-2) — fastest, relative depth.
- **MiDaS** — for relighting / 3D reprojection.

### Step 8 — Color + HDR finish

LUT (`ffmpeg-color`), OCIO ACES (`ffmpeg-color`), or SDR→HLG tone-map (`ffmpeg-color`).

### Step 9 — QC + final encode

`ffmpeg-analyze` VMAF vs source (80–95 expected). `ffmpeg-encode` to delivery: H.264 10-bit `yuv420p10le` for broad compat, AV1 for bandwidth-constrained.

## Variants

- **Animation** — Real-ESRGAN anime variant + RIFE with smooth motion.
- **Face-focused** — GFPGAN (MIT) for talking heads. NEVER CodeFormer (NC).
- **VHS → 4K archive** — detect cadence → `yadif` → heavy `hqdn3d` → upscale 480p → 1440p → color correct.
- **Game capture 30 → 120 fps** — RIFE with higher factors.
- **Handheld + upscale** — stabilize FIRST (crop introduced), THEN upscale.

## Gotchas

- **License landmines — always-drop list:** CodeFormer (NC), DAIN (research), XTTS-v2 / F5-TTS (CPML NC), Stable Video Diffusion (NC), Wav2Lip / SadTalker (research), MusicGen Meta (CC-BY-NC), Surya (commercial restriction). Each AI skill's `references/LICENSES.md` pins the allow-list.
- **Upscaling amplifies noise.** ALWAYS denoise first — upscaler + noisy source = HD noise.
- **RIFE handles scene cuts; FILM doesn't.** Watch for ghost frames on FILM output.
- **Real-ESRGAN default tile size 400** — drop to 200 if VRAM-bound. Model doesn't "see" the whole frame; artifacts at tile borders on wild tile sizes.
- **After AI upscale, force `-pix_fmt yuv420p`** (or `yuv420p10le` for 10-bit deliver). AI models often output RGB or YUV 4:4:4; consumer players need 4:2:0.
- **10-bit upscale into 8-bit codec = banding.** If upscale to 10-bit, deliver in 10-bit: `libx264 -pix_fmt yuv420p10le` or equivalent HEVC.
- **DeepFilterNet expects 16 kHz or 48 kHz MONO.** Feed right format or it downsamples badly.
- **RNNoise hardcoded 48 kHz mono 16-bit.** Resample first or it fails silently.
- **Demucs expects 44.1 kHz or 48 kHz STEREO.** Mono input → degraded stems.
- **RVM is GPL-3.** If shipped embedded in proprietary code, GPL-3 propagates. Commercial OK via dynamic linking.
- **rembg default `u2net`** is fine; `isnet-general-use` is better but heavier.
- **BiRefNet is image-only.** Per-frame video = temporal flicker. Use RVM for temporal coherence.
- **Depth-Anything v2 outputs RELATIVE depth.** Good for VFX; NOT for measurement.
- **Hugging Face model licenses can change without notice.** Pin exact commit hash in `references/LICENSES.md`.
- **AI inference benefits 10× from GPU.** On CPU, Real-ESRGAN 1080p30s = hours.
- **`ffmpeg -hwaccel` is decode-only.** AI models run on their own CUDA / Metal / ROCm paths.
- **Apple Silicon (M1–M4) MPS:** set `PYTORCH_ENABLE_MPS_FALLBACK=1` for unported ops.

## Example — Upscale + interpolate old 720p30 → 4K60

Probe source → denoise with `hqdn3d` → Real-ESRGAN x4plus to 2880×? tile=400 → RIFE v4.6 ×2 → LUT grade → ffmpeg-encode to HEVC 10-bit HDR-ready `yuv420p10le`. VMAF check against source at 720p (upscale reference). Deliver.
