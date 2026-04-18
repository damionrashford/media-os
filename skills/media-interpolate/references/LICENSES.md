# Licenses for bundled interpolation models

Every model this skill recommends is open-source AND commercial-safe.
DAIN (research-only) is intentionally excluded.

| Model                | License     | Commercial use? | Closed-source-product use? | Upstream                                                   |
|----------------------|-------------|-----------------|----------------------------|------------------------------------------------------------|
| RIFE (code + weights)| MIT         | Yes             | Yes                        | https://github.com/hzwer/Practical-RIFE                    |
| rife-ncnn-vulkan     | MIT         | Yes             | Yes                        | https://github.com/nihui/rife-ncnn-vulkan                  |
| FILM                 | Apache-2.0  | Yes             | Yes                        | https://github.com/google-research/frame-interpolation     |
| PractCL              | MIT         | Yes             | Yes                        | https://github.com/fatheral/PractCL                        |

## NOT recommended

| Tool | License       | Why excluded                |
|------|---------------|-----------------------------|
| DAIN | Research-only | Not commercial-safe         |

## Boilerplate attribution

For a commercial product that ships outputs generated with these models,
include a NOTICES / third-party licenses page with:

    This product uses AI frame interpolation models:
      RIFE   (MIT)          https://github.com/hzwer/Practical-RIFE
      FILM   (Apache-2.0)   https://github.com/google-research/frame-interpolation
      PractCL(MIT)          https://github.com/fatheral/PractCL

MIT requires retaining the copyright notice and license text. Apache-2.0
requires retaining the copyright, license, and any NOTICE file that
accompanies the distribution.

## Model weights vs. code

For all three projects, the pretrained weights are distributed alongside
code under the same license. Always re-check the specific release's
LICENSE file before bundling weights into a closed-source product, in
case a future release changes terms.
