# OpenCV Module Catalog (4.x)

Canonical root: `https://docs.opencv.org/4.x/` (`/master/` is an alias).
Tutorial root: `https://docs.opencv.org/4.x/d9/df8/tutorial_root.html`.
Python tutorial root: `https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html`.
JavaScript tutorial root: `https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html`.
Javadoc: `https://docs.opencv.org/4.x/javadoc/index.html`.
Model zoo: `https://github.com/opencv/opencv_zoo`.

## Main repository modules

| Module     | URL suffix                                | One-line purpose                                                    |
|------------|-------------------------------------------|---------------------------------------------------------------------|
| core       | `d0/de1/group__core.html`                 | `Mat` (numpy ndarray in Python), linalg, basic arithmetic           |
| imgproc    | `d7/dbd/group__imgproc.html`              | filtering, morphology, geometric warps, color conversion, contours  |
| imgcodecs  | `d4/da8/group__imgcodecs.html`            | `imread`/`imwrite` — PNG, JPEG, TIFF, WebP, EXR, HEIC (build-dep)   |
| videoio    | `dd/de7/group__videoio.html`              | `VideoCapture`/`VideoWriter` — FFMPEG, GStreamer, V4L2, AVFoundation, MSMF |
| highgui    | `d7/dfc/group__highgui.html`              | `imshow`, `waitKey`, simple trackbars — desktop GUI only            |
| calib3d    | `d9/d0c/group__calib3d.html`              | camera calibration, stereo, `solvePnP`, homography, triangulation   |
| features2d | `da/d9b/group__features2d.html`           | ORB, AKAZE, BRISK, KAZE, SIFT (patent-free in 4.4+), BFMatcher      |
| objdetect  | `d5/d54/group__objdetect.html`            | `FaceDetectorYN`, `FaceRecognizerSF`, HOG, ArUco, QRCodeDetector    |
| dnn        | tutorial `d2/d58/tutorial_table_of_content_dnn.html` | ONNX/TF/Caffe/Darknet readers, OpenCV/CUDA/OpenVINO/Vulkan backends |
| ml         | `dd/ded/group__ml.html`                   | classical ML (SVM, kNN, RTrees, EM, logistic)                       |
| photo      | `d1/d0d/group__photo.html`                | inpainting, denoising (NLM, fastNlMeans), HDR (Debevec, Robertson)  |
| stitching  | `d1/d46/group__stitching.html`            | high-level panorama `cv::Stitcher`                                  |
| video      | `d7/de9/group__video.html`                | optical flow (Farneback / LK / DIS), `BackgroundSubtractor{MOG2,KNN}`, trackers |
| flann      | N/A                                       | fast approximate nearest neighbor (used by features2d matchers)     |
| gapi       | `d0/d1e/group__gapi.html`                 | graph-based image processing, OpenVINO integration                  |

## Contrib modules (ship in `opencv-contrib-python`)

- `ximgproc` — `df/d2d/group__ximgproc.html` — extra filters (guided, rolling guidance, RIC, edge boxes, DTF, AMF)
- `tracking` — legacy trackers under `cv2.legacy.*`; modern trackers moved into `video` in main
- `aruco` — marker detection (moved to main in 4.7; `cv2.aruco` works in both)
- `face` — LBPHFaceRecognizer, Eigen / Fisher
- `xphoto` — extra photo algorithms (white balance, inpainting, TonemapDurand)
- `saliency`, `bgsegm`, `bioinspired`, `optflow`, `sfm`, `text`, `dpm`, `hdf`, `plot`, `line_descriptor`

## Language bindings

- **Python**: `import cv2` (the PyPI wheels are authoritative for most users).
- **C++**: `#include <opencv2/opencv.hpp>` — all modules; link `-lopencv_<module>`.
- **Java**: `https://docs.opencv.org/4.x/javadoc/index.html` — Android + desktop.
- **JavaScript (`opencv.js`)**: `https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html` — WebAssembly build for browsers.
- **C**: legacy C API removed; `libopencv_*.so` exposes C++ only.

## Real shipping binaries

- `opencv_version` — version + build info.
- `opencv_interactive-calibration` — modern interactive calibration helper.
- `opencv_visualisation` — cascade detection visualiser.
- `opencv_model_diagnostics` — dnn model inspection.
- `opencv_perf_*`, `opencv_test_*` — built only with `BUILD_TESTS=ON` / `BUILD_PERF_TESTS=ON`.

### Removed in 4.x

- `opencv_traincascade` — only on the `3.4` branch.
- `opencv_annotation` — only on the `3.4` branch.

## Canonical sample apps (upstream `samples/dnn/`)

- `object_detection.py` — MobileNet-SSD / YOLO / Darknet
- `classification.py` — ImageNet classifiers
- `segmentation.py` — ENet, FCN
- `openpose.py` — pose keypoint detection
- `text_detection.py` — EAST text detector
- `face_detect.py` — YuNet face detection
