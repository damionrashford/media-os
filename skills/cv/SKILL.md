---
name: cv
description: >
  Use when the user asks to detect faces, track objects, run YOLO or ONNX inference, capture or process webcam frames, calibrate a camera, stitch a panorama, find contours, run optical flow, or use OpenCV cv2 from Python; or to detect pose, hand, or face landmarks, recognize gestures, segment people, classify images, audio, or text, or run on-device LLM inference with Google MediaPipe Tasks. Covers OpenCV 4.x (imgproc, imgcodecs, videoio, calib3d, features2d, objdetect FaceDetectorYN/ArUco/QRCode, dnn ONNX/TF/Caffe/Darknet, photo, stitching, video tracking KCF/CSRT/Nano/Vit) and MediaPipe Tasks (Face/Hand/Pose/Holistic Landmarker, Gesture Recognizer, Object Detector, Image/Audio/Text Classifier, Image Segmenter, Embedders, LLM Inference) across IMAGE, VIDEO, and LIVE_STREAM run modes.
argument-hint: "[action-or-task]"
---

# Computer Vision

**Context:** $ARGUMENTS

Image and video computer vision via two complementary stacks: OpenCV 4.x (`cv2`) for classical CV, I/O, and lightweight DNN inference; Google MediaPipe Tasks for pre-trained landmark, segmentation, classification, and on-device LLM models. Use OpenCV for capture/draw/save and custom ONNX; use MediaPipe for Google's pre-trained pose/face/hand/gesture tensors. They pair naturally — MediaPipe hands you tensors, OpenCV does the I/O.

## When to use

- Face / object / landmark detection, optical flow, tracking, panorama, camera calibration, or any classical CV op → OpenCV.
- Run an ONNX / TensorFlow / Caffe / Darknet model from Python without PyTorch/TF → OpenCV `cv2.dnn`.
- Read/write video via FFmpeg, GStreamer, V4L2, AVFoundation, MSMF with one uniform API → OpenCV `VideoCapture`/`VideoWriter`.
- Pre-trained pose, face, hand, gesture, segmentation, or image/audio/text classification on CPU, including mobile/embedded targets → MediaPipe Tasks.
- On-device LLM inference (Gemma / Phi-2 / Falcon / StableLM) → MediaPipe GenAI Task.

## Techniques

- Read `references/opencv.md` when the task is OpenCV: image inspection, frame capture, YuNet face detection, object tracking, `cv2.dnn` inference, camera calibration, or panorama stitching. CLI wrapper: `scripts/cv.py`.
- Read `references/mediapipe.md` when the task is MediaPipe Tasks: face/hand/pose landmarks, gesture recognition, object detection, segmentation, image/audio/text classification, or on-device LLM inference. CLI wrapper: `scripts/mp.py`.
- Read `references/modules.md` when you need a one-line description and canonical URL for any OpenCV module group (core, imgproc, imgcodecs, videoio, calib3d, features2d, objdetect, dnn, ml, photo, stitching, video, ximgproc).
- Read `references/dnn-backends.md` when choosing a `cv2.dnn` backend × target combination, especially for GPU / OpenVINO / Vulkan deployment.
- Read `references/tasks.md` when you need the full MediaPipe Tasks catalog with input/output shapes, per-Task options, and model URLs.

## Gotchas

- **OpenCV is BGR by default; MediaPipe wants RGB.** Every `cv2.imread`/frame is BGR — `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` before wrapping in `mp.Image` (use `.SRGB` format).
- **`cv2.imread` returns `None` silently** on unreadable/non-ASCII paths. Always check `if img is None:`. On Windows use `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)`.
- **Coordinate order trap:** OpenCV APIs take `(x, y)` but numpy indexing is `(row, col) == (y, x)`. The canonical bug.
- **`cv2.findContours` returns 2 values in 4.x** (`contours, hierarchy`), not the 3 of 3.x. Never unpack 3.
- **YuNet `FaceDetectorYN` REQUIRES `setInputSize((w, h))` before `detect`**, or it throws cryptic size errors. Use YuNet, not Haar cascades, for new work.
- **`cv2.dnn.blobFromImage` ordering matters** — most ONNX models want `swapRB=True` and `scalefactor=1/255.0`. Check the model card.
- **MediaPipe: never import `mediapipe.solutions`** (deprecated) — use `mediapipe.tasks.python.vision/audio/text/genai`. Landmarks are NORMALIZED (0–1); multiply by width/height for pixels.
- **MediaPipe VIDEO/LIVE_STREAM timestamps must be monotonically increasing**; LIVE_STREAM requires a non-blocking `result_callback`. PyPI wheels (both OpenCV and MediaPipe) are CPU-only — GPU/CUDA needs a custom build.

## Scripts

- `scripts/cv.py` — OpenCV CLI: `info | capture | detect-faces | track | yolo | calibrate | stitch`. PEP 723 header declares `opencv-contrib-python`; run with `uv run ${CLAUDE_SKILL_DIR}/scripts/cv.py ...`.
- `scripts/mp.py` — MediaPipe Tasks CLI: `face-landmark | hand-landmark | pose-landmark | object-detect | segment | gesture | audio-classify | text-* | llm`, each with `--mode image|video|live`. Run with `uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py ...`.
