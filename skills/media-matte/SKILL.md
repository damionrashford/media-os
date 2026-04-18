---
name: media-matte
description: >
  AI background removal and matting for stills + video with open-source + commercial-safe models: rembg (MIT, bundles u2net / isnet / sam backends), BiRefNet (MIT, 2024 SOTA bilateral reference segmentation), RMBG-2.0 (Apache 2.0, briaai's 2025 model — note v2.0 is Apache, v1.4 was NC and is NOT used here), RobustVideoMatting / RVM (GPL-3.0, temporal-coherent video matting). No green screen required — neural nets predict alpha on arbitrary backgrounds. Use when the user asks to remove a background from an image or video, extract a subject without a greenscreen, auto-matte a person, cut out a product photo, replace a video background, create a transparent PNG from a photo, generate an alpha channel for compositing, or do video-coherent matting on moving subjects.
argument-hint: "[model] [input] [output]"
---

# Media Matte

**Context:** $ARGUMENTS

## Quick start

- **Still image → transparent PNG:** rembg (default) → Step 2 recipe A.
- **Very hard edges (hair, fur, glass):** BiRefNet → Step 2 recipe B.
- **Product photos, no humans:** RMBG-2.0 → Step 2 recipe C.
- **Video with a moving person:** RVM (RobustVideoMatting) → Step 3.
- **Composite subject onto new background:** matte, then `composite` subcommand → Step 5.

## When to use

- User says "remove background", "cut out", "no greenscreen", "matte", "transparent PNG", "alpha channel".
- Source has a subject on an arbitrary background (natural photo, phone video, product shot).
- Video has a moving subject and a per-frame `rembg` run flickers in the edges — use RVM for temporal coherence.
- Do NOT use for chroma-key on actual greenscreen footage — use `ffmpeg-chromakey` instead. A real green screen is cheaper and sharper than neural matting.
- Do NOT use for binary/hard segmentation masks for object-detection tasks — use `cv-mediapipe` / `cv-opencv`.

## Step 1 — Pick a model

| Model   | License     | Best for                              | Form                                | Video? |
|---------|-------------|---------------------------------------|-------------------------------------|--------|
| rembg   | MIT         | General still images, pip-installable | `pip install rembg` CLI + Python    | Frame-by-frame only |
| BiRefNet| MIT         | Hair, fur, semi-transparent edges     | Python (torch + HF transformers)    | Frame-by-frame only |
| RMBG-2.0| Apache 2.0  | Products, e-commerce                  | HuggingFace `briaai/RMBG-2.0`       | Frame-by-frame only |
| RVM     | GPL-3.0     | Video with temporal coherence         | Python (torch); TorchScript/ONNX    | **Yes, native**    |

**Decision rules:**

1. One photo, general subject → **rembg** with model `isnet-general-use` (default). Fastest install.
2. Photo with wispy hair or soft edges → **BiRefNet**.
3. Product/commercial shot → **RMBG-2.0**.
4. Video of a person → **RVM** (temporal model, no flicker, ~4K real-time on decent GPU).

**Do NOT use:** Adobe Sensei (proprietary cloud), backgroundremover.app (freemium SaaS), RMBG **v1.4** (CC-BY-NC — non-commercial only; the v2.0 release IS Apache 2.0 and is what this skill uses).

## Step 2 — Install + run on a still image

`scripts/matte.py install <model>` prints the platform-specific command. It does not auto-install.

```bash
# rembg (Python pip; default u2net / isnet weights bundled, Apache-2.0 weights)
uv pip install "rembg[cli]"

# BiRefNet (from HuggingFace)
uv pip install torch torchvision transformers pillow

# RMBG-2.0
uv pip install torch transformers pillow
# Then from Python: AutoModelForImageSegmentation.from_pretrained("briaai/RMBG-2.0", trust_remote_code=True)

# RVM
git clone https://github.com/PeterL1n/RobustVideoMatting
uv pip install torch torchvision av tqdm pims
# Or PyPI: uv pip install rvm   (community wrapper)
```

### Recipe A — rembg on a photo

```bash
# CLI (bundled with 'rembg[cli]')
rembg i photo.jpg photo_cutout.png
# Pick a model (-m):
rembg i -m isnet-general-use photo.jpg photo_cutout.png
# Other models: u2net, u2netp, u2net_human_seg, isnet-anime, silueta, sam (requires GPU + prompts)
# Alpha-matting for cleaner edges (slow):
rembg i -a photo.jpg photo_cutout.png
```

Driver script:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
  --model rembg --in photo.jpg --out photo_cutout.png \
  --model-name isnet-general-use
```

### Recipe B — BiRefNet (hair / fur / soft edges)

```python
# Minimal Python via transformers:
from transformers import AutoModelForImageSegmentation
from PIL import Image
import torch, torchvision.transforms as T

model = AutoModelForImageSegmentation.from_pretrained(
    "ZhengPeng7/BiRefNet", trust_remote_code=True
)
model.eval().to("cuda")  # or "cpu"

img = Image.open("photo.jpg").convert("RGB")
tx = T.Compose([T.Resize((1024, 1024)), T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with torch.no_grad():
    mask = model(tx(img).unsqueeze(0).to("cuda"))[-1].sigmoid().cpu()[0, 0]
alpha = T.Resize(img.size[::-1])(mask.unsqueeze(0))[0].numpy()
# Composite alpha into RGBA output
```

The driver wraps this:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
  --model birefnet --in photo.jpg --out photo_cutout.png
```

### Recipe C — RMBG-2.0 (e-commerce / product)

```python
from transformers import AutoModelForImageSegmentation
model = AutoModelForImageSegmentation.from_pretrained("briaai/RMBG-2.0", trust_remote_code=True)
# Same inference loop as BiRefNet — both are transformers-compatible segmentation models.
```

Driver:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
  --model rmbg2 --in product.jpg --out product_cutout.png
```

## Step 3 — Matte a video (RVM)

RVM is temporal: it looks at previous frames' hidden state so edges don't flicker.

```bash
# Upstream inference script (from the RVM repo)
python inference.py \
  --variant mobilenetv3 \
  --checkpoint rvm_mobilenetv3.pth \
  --device cuda \
  --input-source input.mp4 \
  --output-type video \
  --output-composition comp.mp4 \
  --output-alpha alpha.mp4 \
  --output-foreground fg.mp4 \
  --output-video-mbps 8 \
  --seq-chunk 1
# Variants: mobilenetv3 (fast, realtime), resnet50 (slow, higher quality)
```

Driver:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py video \
  --model rvm --in input.mp4 --out composite.mp4 \
  --variant mobilenetv3 --bg bg.png
```

The script writes:
- `composite.mp4` — subject over the supplied `--bg` (PNG, JPG, or MP4)
- `alpha.mp4` (optional via `--alpha`) — 8-bit mask video
- `fg.mp4` (optional via `--foreground`) — premultiplied subject

## Step 4 — Refine with a trimap (optional)

If the AI mask is almost right but the user has a rough trimap (black = bg, white = fg, gray = unknown), RVM and BiRefNet can refine. `rembg` supports alpha-matting (`-a`) which does a similar edge refinement via `pymatting`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py refine \
  --in photo.jpg --mask trimap.png --out refined.png
```

## Step 5 — Composite on a new background

```bash
# Still on still
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py composite \
  --fg subject_rgba.png --bg beach.jpg --out final.png

# Video on still/video — ffmpeg overlay with alpha
ffmpeg -i bg.mp4 -i alpha.mp4 -i fg.mp4 \
  -filter_complex "[1:v]format=yuva420p,alphaextract[a];[2:v][a]alphamerge[subject];[0:v][subject]overlay=shortest=1[v]" \
  -map "[v]" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p composite.mp4
```

## Gotchas

- **rembg u2net MODEL weights are Apache-2.0**, separate license from rembg's **code** (MIT). Both are commercial-safe. Document both in your product's NOTICES page. The `u2netp` variant ships with its own license — check the file header if you depend on it.
- **RMBG v1.4 is CC-BY-NC (non-commercial).** This skill does NOT use v1.4. RMBG-**2.0** is Apache 2.0 and IS commercial-safe. Confirm the HuggingFace repo id is `briaai/RMBG-2.0`, not `briaai/RMBG-1.4`.
- **Critical: RVM is GPL-3.0.** Any code that **links** to RVM becomes GPL-3.0 (copyleft propagation). If you're building a commercial closed-source product, you MUST run RVM as a subprocess (CLI boundary) — NOT import its Python modules into your product's code. The driver script in this skill invokes RVM's `inference.py` via `subprocess.run`, preserving the boundary. Do the same in your own product.
- **rembg is frame-by-frame only** — running it on video frames produces edge flicker (temporal inconsistency). Use RVM for videos.
- **BiRefNet's input size matters.** The default 1024×1024 transform is aggressive. For very large photos, consider tile-based processing or accept some quality loss.
- **Alpha channel in ffmpeg MP4 is unreliable.** For a transparent video, use `.mov` with `prores_ks -profile:v 4444` or `.webm` with VP9 (`-pix_fmt yuva420p`). MP4 does not carry alpha on most players.
- **yuva420p vs yuv420p.** RVM writes foreground as yuv420p (matte baked onto black). If you want true alpha video, use `--output-type png_sequence` and remux into ProRes 4444 / VP9+alpha.
- **GPU requirement.** BiRefNet / RMBG-2.0 / RVM run on CPU but are dramatically faster on GPU. rembg `isnet-general-use` is CPU-tolerable for single images.
- **Fine detail (hair, fur).** All four models produce a mask that's soft in hair regions. BiRefNet is currently the best open-source option for this; use alpha-matting post-process (`pymatting` / `rembg -a`) if edges still look chunky.
- **Glass / transparency.** None of these models do true transparency (the subject is classified binary foreground). For glass/liquid, consider hand-keying in DaVinci/Nuke.
- **SAM backend inside rembg** requires prompts (points or boxes). Not the right tool for "just remove the background" — that's what u2net / isnet are for.
- **BiRefNet and RMBG-2.0 are Apache-2.0** for both code and weights. Safe to use in commercial closed products.
- **Adobe Sensei / backgroundremover.app are deliberately excluded.** They are proprietary SaaS; this skill covers open-source + commercial-safe tools you can run locally.

## Examples

### Example 1: Still photo → transparent PNG

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
  --model rembg --in portrait.jpg --out portrait_cutout.png
```

### Example 2: Product photo (white background) → clean cutout

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
  --model rmbg2 --in shoe.jpg --out shoe_cutout.png
```

### Example 3: Video interview → person over a new background image

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py video \
  --model rvm --in interview.mp4 --out out.mp4 --bg office.jpg --variant mobilenetv3
```

### Example 4: Batch a folder of product photos

```bash
for f in products/*.jpg; do
  uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py image \
    --model rmbg2 --in "$f" --out "cutouts/$(basename "${f%.*}").png"
done
```

### Example 5: Check installed backends

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/matte.py check
```

## Troubleshooting

### Error: `rembg: command not found`

Cause: rembg not installed.
Solution: `uv pip install "rembg[cli]"`. CLI becomes available as `rembg`. Also run `rembg d` once to pre-download a default model (otherwise first run downloads on the fly).

### rembg output has jagged / chunky edges around hair

Cause: u2net / isnet is a segmentation model, not a matting model.
Solution: switch to BiRefNet (`--model birefnet`), or use `rembg -a` (alpha matting via pymatting), or hand off to a trimap-aware refine step.

### RVM: `ModuleNotFoundError: No module named 'model'`

Cause: RVM's `inference.py` expects to be run from inside the RVM repo (relative imports).
Solution: `cd` into the cloned `RobustVideoMatting` directory, then run. The driver script does this via `cwd=` in `subprocess.run`.

### Video composite has subject "glowing" at the edges

Cause: premultiplied vs. straight alpha mismatch.
Solution: let ffmpeg handle premultiplication: `premultiply=inplace=1` before `alphamerge`. Or export the foreground as straight alpha with RVM's `--output-foreground` and composite with `overlay=format=rgb` flags.

### `.mp4` output has no transparency

Cause: MP4 + H.264 yuv420p can't carry alpha across most players.
Solution: for transparent video use `.mov` with `prores_ks -profile:v 4444 -pix_fmt yuva444p10le`, or `.webm` with VP9 (`libvpx-vp9 -pix_fmt yuva420p`).

### Slow CPU inference (BiRefNet / RMBG-2.0)

Cause: no GPU.
Solution: smaller input size (512×512), or switch to `rembg` on CPU (still slower than GPU but acceptable for single images), or batch on a cloud GPU.

## Reference docs

- Per-model URLs, license, benchmarks, GPU/CPU notes → `references/models.md`.
- Full license table — including the v1.4 vs. v2.0 RMBG distinction and GPL-3.0 RVM implications → `references/LICENSES.md`.
