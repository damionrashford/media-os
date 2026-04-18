# Licenses for bundled matting models

Three models here are fully commercial-safe. One (RVM) is GPL-3.0 and has
a specific usage constraint for closed-source products.

| Model    | Code license | Weights license | Commercial use? | Closed-source-product use?          | Upstream                                             |
|----------|--------------|-----------------|-----------------|--------------------------------------|------------------------------------------------------|
| rembg    | MIT          | Apache-2.0 (u2net / isnet / sam) | Yes | Yes                                 | https://github.com/danielgatis/rembg                 |
| BiRefNet | MIT          | MIT             | Yes             | Yes                                  | https://github.com/ZhengPeng7/BiRefNet               |
| RMBG-2.0 | Apache-2.0   | Apache-2.0      | Yes             | Yes                                  | https://huggingface.co/briaai/RMBG-2.0               |
| RVM      | GPL-3.0      | GPL-3.0         | Yes             | Only if you invoke it as a subprocess (see below) | https://github.com/PeterL1n/RobustVideoMatting |

## Critical RVM / GPL-3.0 note

GPL-3.0 is a **copyleft** license. If your product's code *links to* RVM
(imports the Python modules, includes the source in a bundle, or statically
links a compiled artifact), your product itself inherits GPL-3.0 — meaning
you must release your product's source code under GPL-3.0 on request.

For a **commercial closed-source product**, you MUST NOT link to RVM. Instead:

1. Run RVM as an external process — e.g. `subprocess.run(["python", "inference.py", ...])` — so the two codebases communicate only over the CLI / filesystem boundary.
2. Ship RVM's source separately (or document where to obtain it) rather than bundling.
3. In your NOTICES page, list RVM as a separately-distributed GPL-3.0 tool you invoke.

The driver `scripts/matte.py` in this skill already uses the subprocess
boundary for RVM. Do the same in your own product.

## RMBG version disambiguation

- RMBG **v1.4** — CC-BY-NC 4.0. **NON-COMMERCIAL ONLY.** This skill does NOT use v1.4.
- RMBG **v2.0** — Apache-2.0. **COMMERCIAL-SAFE.** This skill uses v2.0 only.

Always confirm the HuggingFace repo id:
- v2.0 (ok): `briaai/RMBG-2.0`
- v1.4 (not ok for commercial): `briaai/RMBG-1.4`

## rembg weights — per-model breakdown

| rembg `-m` option        | Weights license     | Notes                              |
|--------------------------|---------------------|------------------------------------|
| `u2net` (default)        | Apache-2.0          | U-2-Net, good general model        |
| `u2netp`                 | Check release       | Lighter; verify license per release |
| `u2net_human_seg`        | Apache-2.0          | Humans only                        |
| `u2net_cloth_seg`        | Apache-2.0          | Clothing only                      |
| `isnet-general-use`      | Apache-2.0          | IS-Net, newer, recommended default |
| `isnet-anime`            | Apache-2.0          | Anime-tuned                        |
| `silueta`                | MIT                 | Silueta-specific weights           |
| `sam`                    | Apache-2.0          | Meta Segment Anything, needs prompts |

## NOT recommended

| Tool                  | License            | Why excluded                        |
|-----------------------|--------------------|-------------------------------------|
| RMBG v1.4             | CC-BY-NC 4.0       | Non-commercial                      |
| Adobe Sensei          | Proprietary (SaaS) | Closed, network-only                |
| backgroundremover.app | Freemium SaaS      | Proprietary, rate-limited           |
| Remove.bg API         | Commercial SaaS    | Proprietary, paid per API call      |

## Boilerplate attribution for products that ship outputs

Paste into your NOTICES / third-party licenses page:

    This product uses AI matting models:
      rembg     (code MIT, weights Apache-2.0)  https://github.com/danielgatis/rembg
      BiRefNet  (MIT)                          https://github.com/ZhengPeng7/BiRefNet
      RMBG-2.0  (Apache-2.0)                   https://huggingface.co/briaai/RMBG-2.0

If the product ALSO invokes RVM as a subprocess for video matting, add:

      RobustVideoMatting (GPL-3.0, invoked as external tool)
        https://github.com/PeterL1n/RobustVideoMatting

MIT requires retaining the copyright + license text. Apache-2.0 requires
retaining copyright, license, and any NOTICE file. GPL-3.0 requires
making the RVM source code available to anyone receiving the RVM binary —
if you're invoking the upstream repo untouched, pointing at the upstream
GitHub URL is sufficient.
