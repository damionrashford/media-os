# MediaPipe Tasks Catalog

Canonical docs: `https://ai.google.dev/edge/mediapipe/solutions/guide`.
Framework docs (low-level graph API): `https://ai.google.dev/edge/mediapipe/framework`.
Repo: `https://github.com/google-ai-edge/mediapipe`.
Model Maker: `https://ai.google.dev/edge/mediapipe/solutions/model_maker`.
Studio playground: `https://mediapipe-studio.webapps.google.com/`.

All Task classes live under `mediapipe.tasks.python.<domain>` where `<domain>` is `vision`, `audio`, `text`, or `genai`. Every Task supports:

- `BaseOptions(model_asset_path=..., delegate=CPU|GPU)`
- `<Task>Options(base_options=..., running_mode=..., <task-specific kwargs>)`
- `<Task>.create_from_options(opts)` — returns a context manager
- `.detect(image)` / `.classify(input)` / `.recognize(image)` / `.embed(input)` / `.generate_response(prompt)`

Run modes (vision + audio): `RunningMode.IMAGE`, `RunningMode.VIDEO`, `RunningMode.LIVE_STREAM`. Text Tasks do not take a running mode.

## Vision Tasks

| Task                   | Doc path                                 | Class                  | Input              | Output                                                                 |
|------------------------|------------------------------------------|------------------------|--------------------|------------------------------------------------------------------------|
| Object Detector        | `/solutions/vision/object_detector/`     | `ObjectDetector`       | `mp.Image`         | `detections: [Detection(bounding_box, categories[])]`                   |
| Image Classifier       | `/solutions/vision/image_classifier/`    | `ImageClassifier`      | `mp.Image`         | `classifications[0].categories[]`                                       |
| Image Segmenter        | `/solutions/vision/image_segmenter/`     | `ImageSegmenter`       | `mp.Image`         | `category_mask` (H,W uint8) + `confidence_masks[]` (H,W,1 float)        |
| Interactive Segmenter  | `/solutions/vision/interactive_segmenter/` | `InteractiveSegmenter` | `mp.Image` + ROI   | same as ImageSegmenter                                                  |
| Gesture Recognizer     | `/solutions/vision/gesture_recognizer/`  | `GestureRecognizer`    | `mp.Image`         | `gestures[][]` + `handedness[][]` + `hand_landmarks[]`                  |
| Hand Landmarker        | `/solutions/vision/hand_landmarker/`     | `HandLandmarker`       | `mp.Image`         | 21 `NormalizedLandmark` per hand, `handedness[]`, `world_landmarks[]`   |
| Face Detector          | `/solutions/vision/face_detector/`       | `FaceDetector`         | `mp.Image`         | `detections` with bbox + 6 `keypoints` (eyes / ears / nose / mouth)     |
| Face Landmarker        | `/solutions/vision/face_landmarker/`     | `FaceLandmarker`       | `mp.Image`         | 478 `NormalizedLandmark`, optional 52 blendshape scores, optional 4×4 matrix |
| Face Stylizer          | `/solutions/vision/face_stylizer/`       | `FaceStylizer`         | `mp.Image`         | stylized `mp.Image`                                                     |
| Pose Landmarker        | `/solutions/vision/pose_landmarker/`     | `PoseLandmarker`       | `mp.Image`         | 33 `NormalizedLandmark` per person + `world_landmarks[]` + optional segmentation mask |
| Holistic Landmarker    | `/solutions/vision/holistic_landmarker/` | `HolisticLandmarker`   | `mp.Image`         | face + hand + pose combined output                                      |
| Image Embedder         | `/solutions/vision/image_embedder/`      | `ImageEmbedder`        | `mp.Image`         | 1024-d (MobileNetV3) or 1408-d (EfficientNet-Lite0) float vector        |
| Image Generator        | `/solutions/vision/image_generator/`     | `ImageGenerator`       | text prompt        | generated `mp.Image` (Stable Diffusion variants)                        |

### Per-Task options (non-obvious ones)

- `ObjectDetectorOptions`: `max_results`, `score_threshold`, `category_allowlist`, `category_denylist`.
- `ImageSegmenterOptions`: `output_category_mask` (bool), `output_confidence_masks` (bool).
- `PoseLandmarkerOptions`: `num_poses`, `min_pose_detection_confidence`, `min_pose_presence_confidence`, `min_tracking_confidence`, `output_segmentation_masks`.
- `FaceLandmarkerOptions`: `num_faces`, `min_face_detection_confidence`, `min_face_presence_confidence`, `min_tracking_confidence`, `output_face_blendshapes`, `output_facial_transformation_matrixes`.
- `HandLandmarkerOptions`: `num_hands`, `min_hand_detection_confidence`, `min_hand_presence_confidence`, `min_tracking_confidence`.
- `GestureRecognizerOptions`: `num_hands`, `canned_gesture_classifier_options`, `custom_gesture_classifier_options`.

### Canned gestures (GestureRecognizer default classifier)

`None`, `Closed_Fist`, `Open_Palm`, `Pointing_Up`, `Thumb_Down`, `Thumb_Up`, `Victory`, `ILoveYou`.

## Audio Tasks

| Task                   | Doc path                                 | Class             | Input                         | Output                                                    |
|------------------------|------------------------------------------|-------------------|-------------------------------|-----------------------------------------------------------|
| Audio Classifier       | `/solutions/audio/audio_classifier/`     | `AudioClassifier` | `mpa.AudioData` (float32, 16 kHz recommended) | list of windows, each with `classifications[0].categories[]` |

YAMNet = 521 AudioSet classes, window = 975 ms at 16 kHz. `AudioClassifier.classify(audio_data)` returns one `AudioClassifierResult` per window (timestamp_ms).

## Text Tasks

| Task                   | Doc path                                 | Class              | Input  | Output                                        |
|------------------------|------------------------------------------|--------------------|--------|-----------------------------------------------|
| Text Classifier        | `/solutions/text/text_classifier/`       | `TextClassifier`   | string | `classifications[0].categories[]`             |
| Text Embedder          | `/solutions/text/text_embedder/`         | `TextEmbedder`     | string | 100–1024-d float vector (model dependent)     |
| Language Detector      | `/solutions/text/language_detector/`     | `LanguageDetector` | string | `detections` with `language_code` + probability |

Most Text Tasks ship BERT-based (`bert_classifier.tflite`) or `average_word_embedder.tflite` small models.

## GenAI — LLM Inference

Doc: `/solutions/genai/llm_inference/`. Class: `mediapipe.tasks.python.genai.inference.LlmInference`.

```python
LlmInferenceOptions(
    model_path,
    max_tokens,
    max_top_k,     # default 40
    temperature,
    top_k,
    top_p,
    random_seed,
)
inf.generate_response(prompt) -> str
inf.generate_response_async(prompt, callback) -> None  # streaming tokens
```

Supported model formats are MediaPipe-specific `.bin` bundles (quantized int4 or int8). Sources:

- Kaggle: `kaggle.com/models/google/gemma`
- HuggingFace: `huggingface.co/google/gemma-2b-it-mediapipe`, etc.
- Community conversions for Phi-2, Falcon RW-1B, StableLM-3B.

CPU backend: all models run, but 7B parameters needs 8+ GB free RAM.
GPU backend: OpenCL on Android/Linux, Metal on iOS/macOS, partial desktop support — check release notes per MediaPipe version.

## NormalizedLandmark shape

```
NormalizedLandmark:
  x: float       # 0..1 within image width
  y: float       # 0..1 within image height
  z: float       # relative depth, not metric
  visibility: float | None
  presence:   float | None
```

World landmarks (`world_landmarks`) use metric space centered at the person's hip (pose) or wrist (hand).

## Reference clients

- Python (current CPython) via `mediapipe` PyPI.
- Android via `com.google.mediapipe:tasks-vision`.
- iOS via `MediaPipeTasksVision` CocoaPods.
- Web via `@mediapipe/tasks-vision` npm.
- Cross-platform C++ via `mediapipe/tasks/cc/...`.
