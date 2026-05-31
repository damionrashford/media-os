# cv2.dnn Backend × Target Matrix

Order of calls after `readNet*`:

```python
net.setPreferableBackend(<backend>)
net.setPreferableTarget(<target>)
```

If the combination is not supported the call silently falls back to `DNN_BACKEND_OPENCV` + `DNN_TARGET_CPU`. Always check the actual perf with `net.getPerfProfile()` — it returns `(time_ms, layer_timings)`.

## Backends (`cv2.dnn.DNN_BACKEND_*`)

| Constant                  | Name                    | Requires                                              | Good for                         |
|---------------------------|-------------------------|-------------------------------------------------------|----------------------------------|
| `DNN_BACKEND_DEFAULT`     | auto                    | picks OPENCV or INFERENCE_ENGINE                      | fallback                         |
| `DNN_BACKEND_OPENCV`      | OpenCV's own impl       | always present                                        | CPU + OpenCL                     |
| `DNN_BACKEND_INFERENCE_ENGINE` | OpenVINO IR         | OpenCV built WITH `-DWITH_INF_ENGINE=ON`              | Intel CPU / iGPU / VPU           |
| `DNN_BACKEND_CUDA`        | NVIDIA CUDA             | OpenCV built WITH `-DWITH_CUDA=ON -DWITH_CUDNN=ON`    | NVIDIA GPUs                      |
| `DNN_BACKEND_VKCOM`       | Vulkan compute          | OpenCV built WITH `-DWITH_VULKAN=ON`                  | cross-vendor GPUs, mobile        |
| `DNN_BACKEND_HALIDE`      | Halide                  | Halide + `WITH_HALIDE=ON` (rare in practice)          | experimental CPU + GPU           |
| `DNN_BACKEND_TIMVX`       | VSI TIM-VX              | NPU drivers                                           | Verisilicon NPUs                 |
| `DNN_BACKEND_CANN`        | Ascend CANN             | Huawei CANN toolkit                                   | Huawei Ascend                    |
| `DNN_BACKEND_WEBNN`       | WebNN                   | WASM build                                            | browser via opencv.js            |

## Targets (`cv2.dnn.DNN_TARGET_*`)

| Constant                 | Name                       | Notes                                                 |
|--------------------------|----------------------------|-------------------------------------------------------|
| `DNN_TARGET_CPU`         | CPU                        | always works                                          |
| `DNN_TARGET_OPENCL`      | OpenCL fp32                | any OpenCL-capable GPU                                |
| `DNN_TARGET_OPENCL_FP16` | OpenCL fp16                | faster on iGPUs that support fp16                     |
| `DNN_TARGET_MYRIAD`      | Intel Movidius / NCS2      | needs INFERENCE_ENGINE backend                        |
| `DNN_TARGET_VULKAN`      | Vulkan                     | pair with `DNN_BACKEND_VKCOM`                         |
| `DNN_TARGET_CUDA`        | CUDA fp32                  | pair with `DNN_BACKEND_CUDA`                          |
| `DNN_TARGET_CUDA_FP16`   | CUDA fp16                  | Turing+ GPUs, big speedup                             |
| `DNN_TARGET_HDDL`        | Intel HDDL                 | needs INFERENCE_ENGINE                                |
| `DNN_TARGET_NPU`         | NPU (CANN / TIMVX)         | pair with the matching backend                        |
| `DNN_TARGET_FPGA`        | FPGA                       | needs INFERENCE_ENGINE                                |

## Supported pairings (rough compatibility)

| Backend \ Target          | CPU | OPENCL | OPENCL_FP16 | CUDA / FP16 | VULKAN | MYRIAD | NPU |
|---------------------------|-----|--------|-------------|-------------|--------|--------|-----|
| OPENCV                    | yes | yes    | yes         | no          | no     | no     | no  |
| INFERENCE_ENGINE          | yes | yes    | yes         | no          | no     | yes    | no  |
| CUDA                      | no  | no     | no          | yes         | no     | no     | no  |
| VKCOM                     | no  | no     | no          | no          | yes    | no     | no  |
| TIMVX / CANN              | no  | no     | no          | no          | no     | no     | yes |

## PyPI wheel realities

- `opencv-python` and `opencv-contrib-python` wheels are **CPU-only** — no CUDA, no OpenVINO, no Vulkan.
- For GPU/OpenVINO, build OpenCV from source or use a vendor build (`pip install nvidia-opencv-python` does not exist as an official package — ignore such advice).
- Apple Silicon (`arm64`): CPU + OPENCL (Metal) work; there is no CUDA on Apple GPUs. VideoToolbox is only used by `VideoCapture` / `VideoWriter`, not by dnn.

## Common pitfalls

- Setting `DNN_TARGET_CUDA` with `DNN_BACKEND_OPENCV` silently runs on CPU. Always set backend AND target.
- `DNN_TARGET_OPENCL_FP16` loses precision on some models — verify accuracy before shipping.
- `DNN_BACKEND_CUDA` requires both CUDA runtime AND cuDNN; OpenCV without cuDNN can load but slow.
- OpenVINO (`INFERENCE_ENGINE`) only speeds up Intel devices; on AMD / NVIDIA CPUs it's equivalent to `DNN_BACKEND_OPENCV` + CPU.
