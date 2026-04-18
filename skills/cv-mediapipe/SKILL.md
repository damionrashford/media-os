---
name: cv-mediapipe
description: >
  Google MediaPipe Tasks API (current supported, NOT legacy mediapipe.solutions): Vision Tasks (Face Detector, Face Landmarker, Face Stylizer, Hand Landmarker, Gesture Recognizer, Pose Landmarker, Holistic Landmarker, Object Detector, Image Classifier, Image Segmenter, Interactive Segmenter, Image Embedder, Image Generator), Audio Tasks (Audio Classifier), Text Tasks (Text Classifier, Text Embedder, Language Detector), GenAI Tasks (LLM Inference — on-device Gemma/Phi-2/Falcon/StableLM). Three run modes: IMAGE, VIDEO, LIVE_STREAM (async). Python: mediapipe.tasks.python.vision/audio/text/genai. Docs at ai.google.dev/edge/mediapipe/solutions. Model Maker for transfer learning. Use when the user asks to detect pose/face/hand landmarks, classify an image, run a body-pose model, segment people, recognize gestures, do on-device LLM inference via MediaPipe, or build a mobile/embedded CV pipeline.
argument-hint: "[task]"
---

# cv-mediapipe

**Context:** $ARGUMENTS

Google MediaPipe Tasks API (`mediapipe.tasks.python.*`). Every Task in MediaPipe follows the same four-step shape: `BaseOptions` → `<Task>Options` → `<Task>.create_from_options` → `detect`/`classify`/`recognize`/`generate`. Docs home: `https://ai.google.dev/edge/mediapipe/solutions/guide`.

## Critical gotcha — which MediaPipe?

MediaPipe has TWO Python APIs. Always use the new one.

| API                               | Status         | Import                                   |
|-----------------------------------|----------------|------------------------------------------|
| `mediapipe.solutions.*` (legacy)  | DEPRECATED     | `from mediapipe.solutions import pose`   |
| `mediapipe.tasks.python.*` (Tasks)| **CURRENT**    | `from mediapipe.tasks.python import vision` |

Never recommend the legacy `solutions` API for new work. The Tasks API has strictly more features (run modes, model hot-swap, explicit timestamps) and is the one Google ships updates for.

## Quick start

- **Face landmarks (478 points + blendshapes):** → Step 3 (`mp.py face-landmark`)
- **Hand landmarks (21 points / hand):** → Step 3 (`mp.py hand-landmark`)
- **Pose landmarks (33 points, 3D):** → Step 3 (`mp.py pose-landmark`)
- **Generic object detection:** → Step 3 (`mp.py object-detect`)
- **Selfie or interactive segmentation:** → Step 3 (`mp.py segment`)
- **Gesture classification:** → Step 3 (`mp.py gesture`)
- **Audio event classification:** → Step 3 (`mp.py audio-classify`)
- **Text classification / embedding / language-detect:** → Step 3 (`mp.py text-*`)
- **On-device LLM inference (Gemma / Phi-2):** → Step 4 (`mp.py llm`)

## When to use

- Fast, portable, pre-trained vision models for faces, hands, bodies, gestures, segmentation — on CPU, no PyTorch/TF required.
- Mobile or embedded targets (Android, iOS, Raspberry Pi) — MediaPipe is the canonical Google stack there.
- Pair with `cv-opencv` for I/O + classical CV; MediaPipe hands you landmark/bbox tensors, OpenCV draws / saves / captures.

For custom ONNX models, use `cv-opencv` dnn module or a full framework instead. Use MediaPipe only when its pre-trained Tasks fit your need.

## Step 1 — Install

```bash
pip install 'mediapipe>=0.10.14' opencv-python numpy
```

Or via the helper's PEP 723 header: `uv run scripts/mp.py ...` handles the venv + deps automatically.

The required wheel is plain `mediapipe`. `mediapipe-silicon` and `mediapipe-rpi` forks predate the current release cadence; prefer the upstream wheel.

## Step 2 — Download the Task bundle (`.task` file)

Every Vision Task loads from a single `.task` file (a Zip bundle with models + metadata). Canonical models are listed on each Task page under `ai.google.dev/edge/mediapipe/solutions/vision/<task>/#models`.

Commonly used bundles:

| Task                | Filename                                           | URL prefix                                                          |
|---------------------|----------------------------------------------------|---------------------------------------------------------------------|
| Face Detector       | `blaze_face_short_range.tflite`                    | `https://storage.googleapis.com/mediapipe-models/face_detector/...` |
| Face Landmarker     | `face_landmarker.task`                             | `https://storage.googleapis.com/mediapipe-models/face_landmarker/...` |
| Hand Landmarker     | `hand_landmarker.task`                             | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/...` |
| Pose Landmarker     | `pose_landmarker_lite.task` (or `_full`, `_heavy`) | `https://storage.googleapis.com/mediapipe-models/pose_landmarker/...` |
| Gesture Recognizer  | `gesture_recognizer.task`                          | `https://storage.googleapis.com/mediapipe-models/gesture_recognizer/...` |
| Object Detector     | `efficientdet_lite0.tflite`                        | `https://storage.googleapis.com/mediapipe-models/object_detector/...` |
| Image Classifier    | `efficientnet_lite0.tflite`                        | `https://storage.googleapis.com/mediapipe-models/image_classifier/...` |
| Image Segmenter     | `selfie_segmenter.tflite`                          | `https://storage.googleapis.com/mediapipe-models/image_segmenter/...` |
| Audio Classifier    | `yamnet.tflite`                                    | `https://storage.googleapis.com/mediapipe-models/audio_classifier/...` |
| Text Classifier     | `bert_classifier.tflite`                           | `https://storage.googleapis.com/mediapipe-models/text_classifier/...` |
| LLM Inference       | `gemma-2b-it-cpu-int4.bin` etc.                    | Kaggle / HuggingFace (see Step 4)                                   |

Full Tasks catalog with input/output shapes in [`references/tasks.md`](references/tasks.md).

## Step 3 — Generic Task pattern (applies to every Vision Task)

```python
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import mediapipe as mp

base = python.BaseOptions(model_asset_path="face_landmarker.task")
opts = vision.FaceLandmarkerOptions(
    base_options=base,
    running_mode=vision.RunningMode.IMAGE,   # IMAGE | VIDEO | LIVE_STREAM
    num_faces=5,
    output_face_blendshapes=True,
)
landmarker = vision.FaceLandmarker.create_from_options(opts)

image = mp.Image.create_from_file("photo.jpg")
result = landmarker.detect(image)
# result.face_landmarks: List[List[NormalizedLandmark]]
# result.face_blendshapes: List[List[Category]]
```

Use `with vision.<Task>.create_from_options(opts) as t:` to ensure resources release on exit.

### Run modes

- `RunningMode.IMAGE` — one frame, synchronous `.detect(image)`.
- `RunningMode.VIDEO` — frames from a video file, synchronous `.detect_for_video(image, timestamp_ms)`. Timestamps must be monotonically increasing.
- `RunningMode.LIVE_STREAM` — live feed, asynchronous `.detect_async(image, timestamp_ms)` + mandatory `result_callback=` in options. Do not block inside the callback.

CLI wrapper exposes each Task with the same `--mode image|video|live` flag:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py face-landmark \
  --model face_landmarker.task --input photo.jpg --mode image --out-json landmarks.json
```

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py pose-landmark \
  --model pose_landmarker_lite.task --input video.mp4 --mode video --out-json pose.json
```

### Output shapes (headline)

- `FaceLandmarker`: 478 landmarks per face, optional blendshapes (52 ARKit-compatible), optional transformation matrix.
- `HandLandmarker`: 21 landmarks per hand + handedness (Left/Right) + world landmarks.
- `PoseLandmarker`: 33 landmarks per person, 3D `(x, y, z, visibility, presence)`, optional segmentation mask.
- `ObjectDetector`: bounding boxes + categories.
- `ImageSegmenter`: category mask and/or confidence mask (per-class or binary).
- `GestureRecognizer`: 7 default gestures (Thumb_Up/Down, Open_Palm, Closed_Fist, Pointing_Up, Victory, ILoveYou) + landmarks + handedness.
- `ImageClassifier` / `ImageEmbedder`: top-k categories or 1024-d embedding.
- `AudioClassifier`: per-window top-k events (YAMNet = 521 classes).
- `TextClassifier` / `TextEmbedder` / `LanguageDetector`: sentence-level top-k / embedding / language code.

See [`references/tasks.md`](references/tasks.md) for full per-Task parameter catalogs.

## Step 4 — LLM Inference Task (GenAI)

The LLM Inference Task runs Gemma / Phi-2 / Falcon / StableLM fully on-device, in C++/Python/JS/Kotlin/Swift.

```python
from mediapipe.tasks.python.genai import inference as llm

opts = llm.LlmInferenceOptions(
    model_path="gemma-2b-it-cpu-int4.bin",
    max_tokens=512,
    temperature=0.8,
    top_k=40,
    random_seed=0,
)
with llm.LlmInference.create_from_options(opts) as inf:
    out = inf.generate_response("Explain WebRTC in 3 bullet points.")
    print(out)
```

Models:

- `gemma-2b-it-cpu-int4.bin`, `gemma-2b-it-gpu-int4.bin`
- `gemma-7b-it-*-int4.bin` (large — 4+ GB RAM)
- `phi-2-cpu.bin` / `phi-2-gpu.bin`
- `falcon-rw-1b-*.bin`, `stablelm-3b-*.bin`

Download via Kaggle models (`kaggle.com/models/google/gemma`) or HuggingFace (converted).

CLI:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py llm \
  --model gemma-2b-it-cpu-int4.bin --prompt "Summarize WebRTC in 3 bullets"
```

## Step 5 — Training with Model Maker (transfer learning)

```bash
pip install mediapipe-model-maker
```

Supports Object Detector, Image Classifier, Gesture Recognizer, Text Classifier, Face Stylizer. Docs: `https://ai.google.dev/edge/mediapipe/solutions/model_maker`.

```python
from mediapipe_model_maker import object_detector
dataset = object_detector.Dataset.from_coco_folder("coco_data/")
spec = object_detector.SupportedModels.MOBILENET_V2
opts = object_detector.ObjectDetectorOptions(supported_model=spec, hparams=object_detector.HParams(export_dir="exported"))
model = object_detector.ObjectDetector.create(train_data=dataset, validation_data=dataset, options=opts)
model.export_model()  # writes a .task bundle in exported/
```

## Interactive testing

MediaPipe Studio — `https://mediapipe-studio.webapps.google.com/` — is a browser playground for every Task. Useful for verifying a model before wiring it into code. Not a production tool.

## Gotchas

- **Never import `mediapipe.solutions`** for new code — it's deprecated. Use `mediapipe.tasks.python.vision` / `.audio` / `.text` / `.genai`.
- **Input is `mp.Image`, not a numpy array** directly. Wrap with `mp.Image(image_format=mp.ImageFormat.SRGB, data=np_rgb)` — note the `.SRGB` (RGB, not BGR from OpenCV).
- **Timestamps must be monotonically increasing in VIDEO / LIVE_STREAM modes** — reusing or going backwards throws. Use frame index × (1000 / fps) in ms.
- **LIVE_STREAM mode REQUIRES `result_callback`** in options. Missing it throws at `create_from_options`.
- **Do not block inside the LIVE_STREAM callback.** It runs on the MediaPipe graph thread; stash the result and return fast.
- **Pose / Hand / Face landmarks returned are NORMALIZED** (0–1 within image bounds). Multiply `x * width`, `y * height` to get pixel coords. `z` is relative depth, not metric.
- **`num_hands` / `num_faces` / `num_poses` caps detections.** Default is 1 for pose, 2 for hands, 1 for face — bump explicitly if you need more.
- **Image Segmenter `.category_mask` vs `.confidence_masks`** — pick via `output_category_mask=True` / `output_confidence_masks=True`. Both can be on; it doubles the compute.
- **GPU delegate** is available (`python.BaseOptions(model_asset_path=..., delegate=python.BaseOptions.Delegate.GPU)`) but requires a build of MediaPipe with GPU support — default pip wheel is CPU-only on desktop.
- **The `.task` file is a zip.** You can `unzip -l foo.task` to see bundled models + metadata. If a Task throws on load, the file is probably corrupt — re-download.
- **BGR vs RGB.** OpenCV gives BGR, MediaPipe wants RGB. Always `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` before wrapping in `mp.Image`.
- **For LLM Inference, CPU backend needs ~4 GB RAM for Gemma-2B-int4**. Gemma-7B needs 8–12 GB. GPU backend needs OpenCL / Metal / CUDA-capable device.

## Examples

### Example 1 — Extract 478 face landmarks + blendshapes on one photo

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py face-landmark \
  --model models/face_landmarker.task \
  --input photo.jpg \
  --mode image \
  --blendshapes \
  --out-json face.json
```

### Example 2 — Pose landmarks on every frame of a video

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py pose-landmark \
  --model models/pose_landmarker_lite.task \
  --input dance.mp4 \
  --mode video \
  --out-json pose_per_frame.json
```

### Example 3 — Run YAMNet audio classification on a wav

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py audio-classify \
  --model models/yamnet.tflite \
  --input recording.wav \
  --top-k 5 --out-json events.json
```

### Example 4 — Classify a piece of text

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py text-classify \
  --model models/bert_classifier.tflite \
  --text "I really enjoyed the movie" \
  --out-json sentiment.json
```

### Example 5 — Run Gemma-2B locally

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/mp.py llm \
  --model models/gemma-2b-it-cpu-int4.bin \
  --prompt "Give me 3 uses of MediaPipe" \
  --max-tokens 256
```

## Troubleshooting

### `ImportError: cannot import name 'tasks' from 'mediapipe'`

Cause: wheel too old, pinned to pre-0.10.
Solution: `pip install -U 'mediapipe>=0.10.14'`.

### `ValueError: Timestamp must be monotonically increasing`

Cause: re-used or went backwards in VIDEO / LIVE_STREAM mode.
Solution: track `prev_ts` and bump by at least 1 ms each call.

### Landmarks come back but `.z` is always 0

Cause: you're reading `NormalizedLandmark` on a Task that doesn't output depth (e.g., 2D-only detectors).
Solution: use world-landmark output (`HandLandmarker.world_landmarks`, `PoseLandmarker.world_landmarks`).

### `create_from_options` throws `Model has invalid format`

Cause: downloaded file is an HTML error page or truncated.
Solution: re-download with `curl -L`, verify file size matches upstream.

### `Unable to open file: /path/foo.task`

Cause: path doesn't exist or not accessible.
Solution: use absolute paths; verify with `ls -la`.

### LLM Inference `runtime_error: not enough memory`

Cause: model size > available RAM (common for Gemma-7B on 8 GB machines).
Solution: use `-int4` quantization, prefer Gemma-2B, or switch to GPU delegate.

## Reference docs

- Read [`references/tasks.md`](references/tasks.md) when you need the full Tasks catalog with input/output shapes, per-Task options, and model URLs for each Vision / Audio / Text / GenAI Task.
