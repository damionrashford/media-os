# ComfyUI — node-graph basics for media-sd

ComfyUI (github.com/comfyanonymous/ComfyUI, GPL-3.0) is a Python node-graph runtime
for diffusion models. This skill uses it as the canonical runtime when a user has
an existing workflow, or wants control over sampler/scheduler/LoRA wiring.

## Architecture

- Backend: single `python main.py` process, HTTP + WebSocket on 8188.
- Workflow: a directed acyclic graph of nodes. Each node has a type (e.g. `KSampler`,
  `CLIPTextEncode`) and inputs that reference other nodes' outputs.
- Models live in `models/` subdirs: `checkpoints/`, `unet/`, `vae/`, `clip/`, `loras/`,
  `controlnet/`, `upscale_models/`, `embeddings/`.
- Custom nodes live in `custom_nodes/`. **ComfyUI-Manager** is the standard installer
  (`git clone https://github.com/ltdrdata/ComfyUI-Manager custom_nodes/ComfyUI-Manager`).

## Two JSON formats — critical

ComfyUI produces two different JSONs:

- **UI-format** (`Save` button): includes `nodes`, `links`, `groups`, `config`,
  positions, colors. Required structure has a top-level `nodes` list. The `/prompt`
  API will NOT accept this.
- **API-format** (`Save (API Format)` button, requires Settings → Enable Dev mode):
  flat dict of `node_id -> {class_type, inputs}`. This is what `/prompt` accepts.

`scripts/sd.py comfy-workflow` detects and refuses UI-format, telling the user how
to re-export.

## Minimal FLUX-schnell workflow (API format)

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "flux1-schnell.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "DualCLIPLoader",
        "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                   "clip_name2": "clip_l.safetensors", "type": "flux"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "ae.safetensors"}},
  "4": {"class_type": "CLIPTextEncode",
        "inputs": {"clip": ["2", 0], "text": "a capybara in a wizard hat"}},
  "5": {"class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
  "6": {"class_type": "KSampler",
        "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0],
                   "latent_image": ["5", 0],
                   "seed": 42, "steps": 4, "cfg": 1.0,
                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
  "7": {"class_type": "VAEDecode",
        "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
  "8": {"class_type": "SaveImage",
        "inputs": {"images": ["7", 0], "filename_prefix": "flux"}}
}
```

Note: FLUX uses `cfg=1.0` + 4 steps (the `guidance_scale=0.0` in diffusers maps to
`cfg=1.0` in ComfyUI's KSampler because ComfyUI subtracts 1 internally). Do not set
`cfg=0` in KSampler — it disables the forward pass.

## Useful nodes

| Category   | Common nodes |
|------------|--------------|
| Loading    | `CheckpointLoaderSimple`, `UNETLoader`, `VAELoader`, `CLIPLoader`, `DualCLIPLoader`, `LoraLoader` |
| Prompting  | `CLIPTextEncode`, `ConditioningCombine`, `ConditioningSetArea`, `ConditioningAverage` |
| Sampling   | `KSampler`, `KSamplerAdvanced`, `SamplerCustom`, `BasicScheduler` |
| Image      | `EmptyLatentImage`, `LatentUpscale`, `LatentUpscaleBy`, `VAEDecode`, `VAEEncode`, `LoadImage`, `SaveImage` |
| ControlNet | `ControlNetLoader`, `ControlNetApplyAdvanced` |
| LoRA stack | `LoraLoader` chainable — plug the output `MODEL`/`CLIP` into another `LoraLoader` |

## HTTP API

- `POST /prompt`  body `{"prompt": <api_graph>, "client_id": "..."}` → `{"prompt_id": "..."}`
- `GET  /history/<prompt_id>`  → outputs once done
- `GET  /view?filename=...&subfolder=...&type=output`  → binary PNG
- `GET  /object_info`  → node schema (can convert UI-format if you walk it)
- `WS  /ws?clientId=...`  → streaming progress, `executing` / `executed` events

`scripts/sd.py comfy-workflow` does POST + poll + GET view. WebSocket streaming is
omitted for simplicity; polling adds <1 s overhead.

## Common sampler/scheduler combos

- FLUX-schnell: `euler` + `simple`, 4 steps.
- Kolors / SDXL-style: `dpmpp_2m` + `karras`, 25 steps.
- Sana: `euler` + `simple`, 20 steps.
- Lumina: `midpoint` or `euler` + `simple`, 30 steps.
- PixArt-Sigma: `dpmpp_2m` + `sgm_uniform`, 20 steps.

## Custom nodes worth installing

- ComfyUI-Manager — node/model installer.
- ComfyUI-GGUF — GGUF quantized UNet loading (FLUX-schnell-Q4_K_S runs on 8 GB).
- comfyui_controlnet_aux — ControlNet preprocessors (canny, depth, openpose).
- ComfyUI-Impact-Pack — detailers, face fix.

Install via Manager to keep the folder clean; avoid random forks.

## Running headless

```bash
python main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch --dont-print-server
# behind nginx / cloudflare tunnel for remote auth.
```

For API-only use (no web UI): pass `--dont-upcast-attention --use-split-cross-attention`
as needed for your GPU, and drop `--disable-auto-launch` to skip opening a browser.
