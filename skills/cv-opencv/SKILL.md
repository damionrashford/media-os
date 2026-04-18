---
name: cv-opencv
description: >
  Computer vision on images + video with OpenCV (docs.opencv.org/4.x/): core (Mat / ndarray, linalg), imgproc (filtering, morphology, geometric transforms, color conv, histograms, contours), imgcodecs (imread/imwrite — PNG, JPEG, TIFF, WebP, EXR), videoio (VideoCapture / VideoWriter — FFMPEG, GStreamer, V4L2, AVFoundation, MSMF backends), calib3d (camera calibration, stereo, solvePnP, homography), features2d (ORB, AKAZE, BRISK, KAZE, SIFT), objdetect (FaceDetectorYN, FaceRecognizerSF, HOG, ArUco, QRCode), dnn (ONNX/TF/Caffe/Darknet, CUDA + OpenVINO + Vulkan backends, model zoo at github.com/opencv/opencv_zoo), photo (inpainting, denoising, HDR Debevec/Robertson), stitching (panorama), video (optical flow Farneback/LK/DIS, BackgroundSubtractorMOG2/KNN, tracking KCF/CSRT/MIL/Nano/Vit/DaSiamRPN). Python-first via cv2. Use when the user asks to detect faces, track objects, run YOLO inference, capture + process webcam frames, calibrate a camera, stitch a panorama, or use OpenCV from Python/C++.
argument-hint: "[action]"
---

# cv-opencv

**Context:** $ARGUMENTS

OpenCV 4.x via the Python `cv2` binding. Python is the first-class surface — the C++, Java (`javadoc`), and JS (`opencv.js`) APIs are parallel and the same concepts port over. Canonical docs: `https://docs.opencv.org/4.x/`.

## Quick start

- **Inspect an image (shape/dtype/channels):** → Step 2 (`cv.py info`)
- **Grab N frames from a webcam / file:** → Step 3 (`cv.py capture`)
- **Detect faces with the modern YuNet model:** → Step 4 (`cv.py detect-faces`)
- **Track a bounding box across frames:** → Step 5 (`cv.py track`)
- **Run an ONNX model via the dnn module:** → Step 6 (`cv.py yolo`)
- **Calibrate a camera from a chessboard:** → Step 7 (`cv.py calibrate`)
- **Stitch a panorama:** → Step 8 (`cv.py stitch`)

## When to use

- User asks for face / object / landmark detection, optical flow, tracking, panorama, camera calibration, or any classical CV operation.
- Need to run an ONNX / TensorFlow / Caffe / Darknet model from Python without heavyweight frameworks (PyTorch, TF) — `cv2.dnn` is the lightweight path.
- Need to read/write video via FFmpeg, GStreamer, V4L2, AVFoundation, or MSMF with a uniform API (`cv2.VideoCapture` / `cv2.VideoWriter`).
- For pose/face landmark models trained by Google (MediaPipe Tasks), use the `cv-mediapipe` skill instead — it's a different ecosystem with its own Tasks API.

## Step 1 — Install the right OpenCV wheel

Three PyPI wheels, mutually exclusive — picking the wrong one hides features or wastes install.

| Wheel                         | Includes                                    | Use when                          |
|-------------------------------|---------------------------------------------|-----------------------------------|
| `opencv-python`               | main repo only                              | basic imgproc/videoio/dnn         |
| `opencv-contrib-python`       | main + contrib (ximgproc, tracking, aruco)  | **recommended default**           |
| `opencv-python-headless`      | main, no GUI (no `imshow`)                  | servers / Docker                  |
| `opencv-contrib-python-headless` | contrib, no GUI                          | headless + contrib modules        |

Install exactly one:

```bash
pip install opencv-contrib-python
# or via uv: uv pip install opencv-contrib-python
```

Never install both `opencv-python` and `opencv-contrib-python` — they conflict on `cv2/*.so`.

The helper `scripts/cv.py` declares `opencv-contrib-python` via PEP 723 so `uv run` handles it in an ephemeral venv.

## Step 2 — Inspect images before processing

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py info path/to/image.png
```

Prints: shape (`H, W, C`), dtype (`uint8` / `uint16` / `float32`), channel count, min/max/mean per channel, and whether the file is readable by `cv2.imread`. If `cv2.imread` returns `None`, the file is either unreadable, the wrong format, or a non-ASCII path on Windows (use `cv2.imdecode` + `np.fromfile` in that case).

OpenCV's default channel order is **BGR**, not RGB. All operations assume BGR. Convert to RGB explicitly before handing to matplotlib / PIL / torchvision:

```python
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
```

## Step 3 — Capture video frames (file / webcam / RTSP)

```bash
# webcam 0, 30 frames
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py capture --src 0 --count 30 --out frames/
# RTSP stream
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py capture --src 'rtsp://host/stream' --count 60 --out frames/
# video file
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py capture --src in.mp4 --count 100 --out frames/
```

`VideoCapture` uses the first backend that accepts the URL. Force a backend with `cv2.VideoCapture(src, cv2.CAP_FFMPEG | cv2.CAP_GSTREAMER | cv2.CAP_AVFOUNDATION | cv2.CAP_V4L2 | cv2.CAP_MSMF)`.

On macOS, webcam access requires Terminal to hold the camera permission (System Settings → Privacy & Security → Camera). On Linux, `/dev/video0` must exist and be readable by your user.

## Step 4 — Face detection (modern FaceDetectorYN)

Do NOT use Haar cascades for new work. `cv2.FaceDetectorYN` (YuNet) is the current recommendation — small (<1 MB), fast, accurate, works on any CPU.

```bash
# downloads model if not present in models/
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py detect-faces path/to/image.jpg \
  --model models/face_detection_yunet_2023mar.onnx \
  --score-threshold 0.9
```

Download the YuNet ONNX from `https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet`. Outputs per-face bbox + 5 landmarks (eyes, nose, mouth corners).

For face recognition, pair with `cv2.FaceRecognizerSF` (SFace) — 512-d embeddings, cosine-distance matching.

## Step 5 — Object tracking

The tracker API in 4.x moved out of `cv2.legacy` for the modern trackers:

| Tracker                 | Modern API (`cv2.Tracker*_create`) | Legacy (`cv2.legacy.Tracker*_create`) | Notes                            |
|-------------------------|------------------------------------|---------------------------------------|----------------------------------|
| MIL                     | yes                                | yes                                   | slow, still accurate             |
| KCF                     | yes                                | yes                                   | fast, CSRT is better             |
| CSRT                    | yes                                | yes                                   | **best classical default**       |
| GOTURN                  | yes                                | no                                    | needs .caffemodel + .prototxt    |
| Nano                    | yes                                | no                                    | modern NN tracker, ONNX backend  |
| Vit                     | yes                                | no                                    | Vision Transformer tracker       |
| DaSiamRPN               | yes                                | no                                    | Siamese RPN, ONNX backend        |

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py track --src video.mp4 \
  --bbox "x,y,w,h" --tracker csrt --out tracked.mp4
```

Pick the bbox on the first frame; the script writes an annotated video.

## Step 6 — DNN inference (ONNX / Caffe / Darknet / TF / Torch)

Readers (in order of popularity):

- `cv2.dnn.readNetFromONNX(model.onnx)` — most modern
- `cv2.dnn.readNetFromTensorflow(frozen.pb, graph.pbtxt)`
- `cv2.dnn.readNetFromCaffe(deploy.prototxt, weights.caffemodel)`
- `cv2.dnn.readNetFromDarknet(cfg, weights)` — YOLOv3/v4
- `cv2.dnn.readNetFromTorch(model.t7)` — legacy Torch
- `cv2.dnn.readNet(path)` — auto-detect by extension

Set backend + target AFTER loading:

```python
net = cv2.dnn.readNetFromONNX("yolov8n.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)  # or CUDA / INFERENCE_ENGINE / VKCOM
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)       # or OPENCL / OPENCL_FP16 / CUDA / CUDA_FP16 / MYRIAD
```

Full backend × target compatibility matrix in `references/dnn-backends.md`.

Typical YOLO call (ONNX, letterbox-resize, NMS):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py yolo \
  --model yolov8n.onnx \
  --input image.jpg \
  --conf 0.25 --iou 0.45 \
  --labels coco.names
```

The script uses `cv2.dnn.blobFromImage` + `net.forward()` + `cv2.dnn.NMSBoxes`.

Real OpenCV Python sample apps (upstream `samples/dnn/`) cover classification, detection, segmentation, openpose, text detection, face detect — they are the best reference for wiring new models.

## Step 7 — Camera calibration

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py calibrate \
  --pattern chessboard --size 9x6 --square-mm 25 \
  --images 'calib/*.jpg' --out camera.yaml
```

Writes intrinsic matrix `K`, distortion coefficients, RMS reprojection error. 15+ images from different angles are recommended for a solid fit. For ArUco / ChArUco boards, use `cv2.aruco.CharucoBoard` + `cv2.aruco.detectMarkers` — better than chessboard at extreme angles.

## Step 8 — Panorama stitching

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py stitch pano1.jpg pano2.jpg pano3.jpg --out pano.jpg
```

Uses `cv2.Stitcher.create()`. Modes: `cv2.Stitcher.PANORAMA` (default) or `cv2.Stitcher.SCANS` (flat docs). If it returns `ERR_NEED_MORE_IMGS` / `ERR_HOMOGRAPHY_EST_FAIL`, the overlap between input images is insufficient or feature matches are too sparse — feed more overlapping shots.

## Binaries that ship with OpenCV

Real binaries (install via your distro or from source with `cmake --build . --target install`):

- `opencv_version` — prints `4.x.y`. Sanity check.
- `opencv_interactive-calibration` — guided camera calibration (replaces the old calibrator).
- `opencv_visualisation` — single-sample visualiser for cascade classifiers.
- `opencv_model_diagnostics` — dnn model inspector.
- `opencv_perf_*`, `opencv_test_*` — only present when built with `BUILD_TESTS=ON` / `BUILD_PERF_TESTS=ON`.

**Gotcha:** `opencv_traincascade` and `opencv_annotation` were **removed in OpenCV 4.x**. They exist only on the `3.4` branch. If you need to train a new cascade, either use the 3.4 binary or retarget to modern DNN workflows (YOLO / SSD / YuNet).

## Gotchas

- **BGR by default.** Every `imread` output is BGR. `cv2.imshow` expects BGR. Convert explicitly for RGB consumers.
- **`cv2.imread` returns `None` silently** on unreadable paths. Always check `if img is None:` after load.
- **Windows + non-ASCII paths** require `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)` rather than `cv2.imread`.
- **Tracker API split** — prefer `cv2.TrackerCSRT_create()`, not `cv2.legacy.TrackerCSRT_create()`, unless you explicitly need the old API.
- **`cv2.dnn` blobFromImage ordering matters** — for most ONNX models you want `swapRB=True` (BGR→RGB) and `scalefactor=1/255.0`. Check the model card.
- **HoughCircles is noisy** — `minDist`, `param1`, `param2` are extremely sensitive. Pre-blur (`cv2.GaussianBlur(img, (9,9), 2)`) before calling.
- **VideoWriter codec strings are platform-dependent.** `mp4v` writes a non-standard MP4; use `avc1` for H.264 (requires FFmpeg backend). `MJPG` always works but bloats files.
- **Coordinate order is `(x, y)` in most APIs but `(row, col) == (y, x)` when indexing numpy arrays.** The canonical bug.
- **`cv2.findContours` signature changed between OpenCV 3 → 4.** In 4.x: `contours, hierarchy = cv2.findContours(...)` (2 returns). 3.x returned 3. Never unpack 3 in 4.x code.
- **YuNet face detector REQUIRES `setInputSize` before `detect`** (or it throws cryptic size errors). Pass `(w, h)` of the actual image.
- **GPU CUDA backend needs OpenCV built WITH CUDA** — wheels from PyPI are CPU-only. Build from source if `DNN_TARGET_CUDA` is required.
- **`opencv_traincascade` is not in 4.x** — see the note above.
- **Haar cascades are legacy.** They still work (`cv2.CascadeClassifier`) but produce many false positives vs YuNet. Use YuNet for any new face-detection work.
- **ArUco moved to main repo in 4.7** — `cv2.aruco` is now bundled in `opencv-python` (no contrib needed). Older guides say contrib; check your version with `cv2.__version__`.

## Examples

### Example 1 — "Detect faces in a photo, draw boxes, save result"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py detect-faces photo.jpg \
  --model models/face_detection_yunet_2023mar.onnx \
  --out photo_faces.jpg --draw
```

Download the model once:

```bash
curl -L -o models/face_detection_yunet_2023mar.onnx \
  'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
```

### Example 2 — "Track a car in a dashcam video"

```bash
# manually pick the bbox on frame 0 (x,y,w,h)
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py track --src dashcam.mp4 \
  --bbox "640,360,120,80" --tracker csrt --out tracked.mp4
```

### Example 3 — "Run YOLOv8 ONNX on a still image"

Export from ultralytics first: `yolo export model=yolov8n.pt format=onnx`. Then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py yolo \
  --model yolov8n.onnx --input street.jpg \
  --labels coco.names --out street_det.jpg --conf 0.3
```

### Example 4 — "Calibrate a camera from a 9x6 chessboard"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py calibrate \
  --pattern chessboard --size 9x6 --square-mm 25 \
  --images 'calib/IMG_*.jpg' --out camera.yaml
```

The YAML contains `camera_matrix`, `dist_coeff`, `rms`. Load with `cv2.FileStorage`.

### Example 5 — "Stitch hand-held phone shots into a panorama"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py stitch shot1.jpg shot2.jpg shot3.jpg shot4.jpg --out pano.jpg
```

## Troubleshooting

### `cv2.error: (-215:Assertion failed) !_src.empty()`

Cause: `imread` returned `None` — the file path is wrong, unreadable, or non-ASCII on Windows.
Solution: Check `os.path.exists(path)` first; on Windows use `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)`.

### `AttributeError: module 'cv2' has no attribute 'FaceDetectorYN'`

Cause: OpenCV < 4.5.4, or the module failed to compile.
Solution: `pip install -U opencv-contrib-python`. Verify `cv2.__version__` is >= 4.8.

### `cv2.error: OpenCV(4.x) ... cv::dnn::readNetFromONNX_ ... can't open file`

Cause: model path wrong or file corrupted during download.
Solution: check file size vs upstream; re-download via `curl -L`.

### `TrackerCSRT_create` exists but `track()` returns false every frame

Cause: initial bbox empty or off-screen.
Solution: verify `(x, y, w, h)` are inside the first frame and `w > 0 and h > 0`.

### Webcam opens but returns all-black frames

Cause: OS-level camera permission not granted; wrong camera index; another app holds it.
Solution: On macOS grant Terminal/iTerm Camera permission; try indices 0, 1, 2; close Zoom / FaceTime / OBS.

### `opencv_traincascade: command not found`

Cause: Tool removed in 4.x.
Solution: Use OpenCV 3.4 branch explicitly for cascade training, or move to modern DNN detectors (YuNet, YOLO, SSD).

## Reference docs

- Read [`references/modules.md`](references/modules.md) when you need a one-line description of every OpenCV module group (core, imgproc, imgcodecs, videoio, calib3d, features2d, objdetect, dnn, ml, photo, stitching, video, ximgproc…) plus the canonical URL for each.
- Read [`references/dnn-backends.md`](references/dnn-backends.md) when choosing a `cv2.dnn` backend × target combination, especially for GPU / OpenVINO / Vulkan deployment.
