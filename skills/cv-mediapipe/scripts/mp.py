#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mediapipe>=0.10.14",
#   "numpy>=1.24",
#   "opencv-python>=4.8",
# ]
# ///
"""
mp.py — MediaPipe Tasks API CLI.

Every subcommand follows the same shape: load the .task bundle,
BaseOptions -> <Task>Options -> create_from_options -> detect. JSON
output on stdout. Non-interactive. --dry-run prints the call; --verbose
traces model loading.

Usage:
  mp.py face-detect    --model MODEL --input PATH [--mode image|video] [--out-json FILE]
  mp.py face-landmark  --model MODEL --input PATH [--mode image|video] [--blendshapes] [--out-json FILE]
  mp.py hand-landmark  --model MODEL --input PATH [--mode image|video] [--num 2] [--out-json FILE]
  mp.py pose-landmark  --model MODEL --input PATH [--mode image|video] [--num 1] [--seg-mask] [--out-json FILE]
  mp.py object-detect  --model MODEL --input PATH [--mode image|video] [--score 0.5] [--out-json FILE]
  mp.py classify       --model MODEL --input PATH [--top-k 5] [--out-json FILE]
  mp.py embed          --model MODEL --input PATH [--out-json FILE]
  mp.py segment        --model MODEL --input PATH --type selfie|interactive [--out-mask FILE]
  mp.py gesture        --model MODEL --input PATH [--out-json FILE]
  mp.py audio-classify --model MODEL --input WAV [--top-k 3] [--out-json FILE]
  mp.py text-classify  --model MODEL --text STR [--out-json FILE]
  mp.py text-embed     --model MODEL --text STR [--out-json FILE]
  mp.py language-detect --model MODEL --text STR [--out-json FILE]
  mp.py llm            --model MODEL --prompt STR [--max-tokens 512] [--temp 0.8]
"""
from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2  # noqa: F401  — used for video frame reads
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import audio as mpa
    from mediapipe.tasks.python import text as mpt
    from mediapipe.tasks.python import vision as mpv
except ImportError as e:  # pragma: no cover
    print(
        f"error: required dependency missing ({e}). "
        "`pip install 'mediapipe>=0.10.14' opencv-python numpy` or use `uv run`.",
        file=sys.stderr,
    )
    sys.exit(1)


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[mp] {msg}", file=sys.stderr)


def _emit(call: str, verbose: bool) -> None:
    if verbose:
        print(f"[mp.call] {call}", file=sys.stderr)


def _as_image(path: str) -> mp.Image:
    return mp.Image.create_from_file(path)


def _iter_video_frames(path: str):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"cv2.VideoCapture failed for {path!r}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    i = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                return
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts = int(i * 1000.0 / fps)
            yield ts, img
            i += 1
    finally:
        cap.release()


def _running_mode(mode: str, domain):
    table = {
        "image": domain.RunningMode.IMAGE,
        "video": domain.RunningMode.VIDEO,
    }
    if mode not in table:
        raise ValueError(f"unsupported --mode {mode!r} (use image|video)")
    return table[mode]


def _write(obj: Any, out_json: str | None) -> None:
    text = json.dumps(obj, indent=2, default=lambda o: getattr(o, "__dict__", str(o)))
    if out_json:
        Path(out_json).write_text(text)
    print(text)


def _landmarks_to_list(lms) -> list[dict]:
    return [
        {
            "x": float(lm.x),
            "y": float(lm.y),
            "z": float(lm.z),
            "visibility": float(getattr(lm, "visibility", 0.0) or 0.0),
            "presence": float(getattr(lm, "presence", 0.0) or 0.0),
        }
        for lm in lms
    ]


# ---------------------------------------------------------------------------
# Vision Tasks
# ---------------------------------------------------------------------------


def cmd_face_detect(args: argparse.Namespace) -> int:
    _emit(f"FaceDetector.create_from_options(model={args.model!r})", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.FaceDetectorOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=_running_mode(args.mode, mpv),
    )
    with mpv.FaceDetector.create_from_options(opts) as det:
        if args.mode == "image":
            res = det.detect(_as_image(args.input))
            out = [
                {
                    "bbox": [
                        d.bounding_box.origin_x,
                        d.bounding_box.origin_y,
                        d.bounding_box.width,
                        d.bounding_box.height,
                    ],
                    "categories": [
                        {"category_name": c.category_name, "score": float(c.score)}
                        for c in d.categories
                    ],
                }
                for d in res.detections
            ]
            _write({"detections": out}, args.out_json)
        else:
            per_frame = []
            for ts, img in _iter_video_frames(args.input):
                r = det.detect_for_video(img, ts)
                per_frame.append({"ts_ms": ts, "count": len(r.detections)})
            _write({"frames": per_frame}, args.out_json)
    return 0


def cmd_face_landmark(args: argparse.Namespace) -> int:
    _emit("FaceLandmarker.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=_running_mode(args.mode, mpv),
        num_faces=args.num,
        output_face_blendshapes=args.blendshapes,
        output_facial_transformation_matrixes=False,
    )
    with mpv.FaceLandmarker.create_from_options(opts) as lm:
        if args.mode == "image":
            res = lm.detect(_as_image(args.input))
            out = {
                "face_landmarks": [
                    _landmarks_to_list(face) for face in res.face_landmarks
                ],
                "blendshapes": [
                    [{"name": c.category_name, "score": float(c.score)} for c in row]
                    for row in res.face_blendshapes
                ],
            }
            _write(out, args.out_json)
        else:
            per_frame = []
            for ts, img in _iter_video_frames(args.input):
                r = lm.detect_for_video(img, ts)
                per_frame.append(
                    {
                        "ts_ms": ts,
                        "faces": [_landmarks_to_list(f) for f in r.face_landmarks],
                    }
                )
            _write({"frames": per_frame}, args.out_json)
    return 0


def cmd_hand_landmark(args: argparse.Namespace) -> int:
    _emit("HandLandmarker.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=_running_mode(args.mode, mpv),
        num_hands=args.num,
    )
    with mpv.HandLandmarker.create_from_options(opts) as lm:
        if args.mode == "image":
            r = lm.detect(_as_image(args.input))
            out = {
                "hand_landmarks": [_landmarks_to_list(h) for h in r.hand_landmarks],
                "handedness": [
                    [{"name": c.category_name, "score": float(c.score)} for c in h]
                    for h in r.handedness
                ],
            }
            _write(out, args.out_json)
        else:
            per_frame = []
            for ts, img in _iter_video_frames(args.input):
                r = lm.detect_for_video(img, ts)
                per_frame.append(
                    {
                        "ts_ms": ts,
                        "hands": [_landmarks_to_list(h) for h in r.hand_landmarks],
                    }
                )
            _write({"frames": per_frame}, args.out_json)
    return 0


def cmd_pose_landmark(args: argparse.Namespace) -> int:
    _emit("PoseLandmarker.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=_running_mode(args.mode, mpv),
        num_poses=args.num,
        output_segmentation_masks=args.seg_mask,
    )
    with mpv.PoseLandmarker.create_from_options(opts) as lm:
        if args.mode == "image":
            r = lm.detect(_as_image(args.input))
            out = {"pose_landmarks": [_landmarks_to_list(p) for p in r.pose_landmarks]}
            _write(out, args.out_json)
        else:
            per_frame = []
            for ts, img in _iter_video_frames(args.input):
                r = lm.detect_for_video(img, ts)
                per_frame.append(
                    {
                        "ts_ms": ts,
                        "poses": [_landmarks_to_list(p) for p in r.pose_landmarks],
                    }
                )
            _write({"frames": per_frame}, args.out_json)
    return 0


def cmd_object_detect(args: argparse.Namespace) -> int:
    _emit("ObjectDetector.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.ObjectDetectorOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=_running_mode(args.mode, mpv),
        score_threshold=args.score,
    )
    with mpv.ObjectDetector.create_from_options(opts) as det:
        if args.mode == "image":
            r = det.detect(_as_image(args.input))
            out = [
                {
                    "bbox": [
                        d.bounding_box.origin_x,
                        d.bounding_box.origin_y,
                        d.bounding_box.width,
                        d.bounding_box.height,
                    ],
                    "categories": [
                        {"name": c.category_name, "score": float(c.score)}
                        for c in d.categories
                    ],
                }
                for d in r.detections
            ]
            _write({"detections": out}, args.out_json)
        else:
            per_frame = []
            for ts, img in _iter_video_frames(args.input):
                r = det.detect_for_video(img, ts)
                per_frame.append({"ts_ms": ts, "count": len(r.detections)})
            _write({"frames": per_frame}, args.out_json)
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    _emit("ImageClassifier.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.ImageClassifierOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=mpv.RunningMode.IMAGE,
        max_results=args.top_k,
    )
    with mpv.ImageClassifier.create_from_options(opts) as clf:
        r = clf.classify(_as_image(args.input))
        out = [
            {"name": c.category_name, "score": float(c.score)}
            for c in r.classifications[0].categories
        ]
        _write({"top_k": out}, args.out_json)
    return 0


def cmd_embed(args: argparse.Namespace) -> int:
    _emit("ImageEmbedder.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.ImageEmbedderOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=mpv.RunningMode.IMAGE,
    )
    with mpv.ImageEmbedder.create_from_options(opts) as emb:
        r = emb.embed(_as_image(args.input))
        vec = list(r.embeddings[0].embedding)
        _write({"embedding_len": len(vec), "embedding": vec}, args.out_json)
    return 0


def cmd_segment(args: argparse.Namespace) -> int:
    _emit(f"ImageSegmenter.create_from_options(type={args.type})", args.verbose)
    if args.dry_run:
        return 0
    # Interactive segmenter requires a RegionOfInterest; selfie segmenter does not.
    opts = mpv.ImageSegmenterOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=mpv.RunningMode.IMAGE,
        output_category_mask=True,
        output_confidence_masks=False,
    )
    with mpv.ImageSegmenter.create_from_options(opts) as seg:
        r = seg.segment(_as_image(args.input))
        mask = r.category_mask.numpy_view()
        print(
            json.dumps(
                {
                    "mask_shape": list(mask.shape),
                    "unique_classes": np.unique(mask).tolist(),
                }
            )
        )
        if args.out_mask:
            cv2.imwrite(args.out_mask, mask.astype(np.uint8))
    return 0


def cmd_gesture(args: argparse.Namespace) -> int:
    _emit("GestureRecognizer.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpv.GestureRecognizerOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        running_mode=mpv.RunningMode.IMAGE,
    )
    with mpv.GestureRecognizer.create_from_options(opts) as rec:
        r = rec.recognize(_as_image(args.input))
        out = [
            {"name": g[0].category_name, "score": float(g[0].score)}
            for g in r.gestures
            if g
        ]
        _write({"gestures": out}, args.out_json)
    return 0


# ---------------------------------------------------------------------------
# Audio Task
# ---------------------------------------------------------------------------


def cmd_audio_classify(args: argparse.Namespace) -> int:
    _emit("AudioClassifier.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    with wave.open(args.input, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        frames = w.readframes(w.getnframes())
    dtype = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
    data = np.frombuffer(frames, dtype=dtype).astype(np.float32)
    if sw == 2:
        data /= 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    opts = mpa.AudioClassifierOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        max_results=args.top_k,
    )
    with mpa.AudioClassifier.create_from_options(opts) as clf:
        audio_data = mpa.AudioData.create_from_array(data, sr)
        res = clf.classify(audio_data)
        out = [
            {
                "ts_ms": float(r.timestamp_ms),
                "top": [
                    {"name": c.category_name, "score": float(c.score)}
                    for c in r.classifications[0].categories
                ],
            }
            for r in res
        ]
        _write({"windows": out}, args.out_json)
    return 0


# ---------------------------------------------------------------------------
# Text Tasks
# ---------------------------------------------------------------------------


def cmd_text_classify(args: argparse.Namespace) -> int:
    _emit("TextClassifier.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpt.TextClassifierOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
    )
    with mpt.TextClassifier.create_from_options(opts) as clf:
        r = clf.classify(args.text)
        out = [
            {"name": c.category_name, "score": float(c.score)}
            for c in r.classifications[0].categories
        ]
        _write({"top_k": out}, args.out_json)
    return 0


def cmd_text_embed(args: argparse.Namespace) -> int:
    _emit("TextEmbedder.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpt.TextEmbedderOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
    )
    with mpt.TextEmbedder.create_from_options(opts) as emb:
        r = emb.embed(args.text)
        vec = list(r.embeddings[0].embedding)
        _write({"embedding_len": len(vec), "embedding": vec}, args.out_json)
    return 0


def cmd_language_detect(args: argparse.Namespace) -> int:
    _emit("LanguageDetector.create_from_options(...)", args.verbose)
    if args.dry_run:
        return 0
    opts = mpt.LanguageDetectorOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
    )
    with mpt.LanguageDetector.create_from_options(opts) as det:
        r = det.detect(args.text)
        out = [
            {"language_code": p.language_code, "probability": float(p.probability)}
            for p in r.detections
        ]
        _write({"languages": out}, args.out_json)
    return 0


# ---------------------------------------------------------------------------
# LLM Inference Task
# ---------------------------------------------------------------------------


def cmd_llm(args: argparse.Namespace) -> int:
    try:
        from mediapipe.tasks.python.genai import inference as llm
    except ImportError:
        print(
            "error: LLM Inference is a separate MediaPipe install "
            "(pip install mediapipe[genai]) or requires a recent mediapipe.",
            file=sys.stderr,
        )
        return 2
    _emit(
        f"LlmInference.create_from_options(model_path={args.model!r}, max_tokens={args.max_tokens})",
        args.verbose,
    )
    if args.dry_run:
        return 0
    opts = llm.LlmInferenceOptions(
        model_path=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temp,
        top_k=args.top_k,
        random_seed=args.seed,
    )
    with llm.LlmInference.create_from_options(opts) as inf:
        out = inf.generate_response(args.prompt)
        print(out)
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true")
    parent.add_argument("--verbose", action="store_true")

    p = argparse.ArgumentParser(
        description="MediaPipe Tasks API CLI (vision / audio / text / genai).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[parent],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _vision(name, help_str, fn, extra):
        sp = sub.add_parser(name, help=help_str, parents=[parent])
        sp.add_argument("--model", required=True)
        sp.add_argument("--input", required=True)
        sp.add_argument("--mode", default="image", choices=["image", "video"])
        sp.add_argument("--out-json")
        extra(sp)
        sp.set_defaults(fn=fn)
        return sp

    _vision("face-detect", "BlazeFace detector", cmd_face_detect, lambda sp: None)
    _vision(
        "face-landmark",
        "478 face landmarks + optional blendshapes",
        cmd_face_landmark,
        lambda sp: (
            sp.add_argument("--num", type=int, default=1),
            sp.add_argument("--blendshapes", action="store_true"),
        ),
    )
    _vision(
        "hand-landmark",
        "21 hand landmarks per hand",
        cmd_hand_landmark,
        lambda sp: sp.add_argument("--num", type=int, default=2),
    )
    _vision(
        "pose-landmark",
        "33 pose landmarks per person",
        cmd_pose_landmark,
        lambda sp: (
            sp.add_argument("--num", type=int, default=1),
            sp.add_argument("--seg-mask", action="store_true"),
        ),
    )
    _vision(
        "object-detect",
        "generic object detector (EfficientDet-Lite etc.)",
        cmd_object_detect,
        lambda sp: sp.add_argument("--score", type=float, default=0.5),
    )

    s_cls = sub.add_parser(
        "classify", help="image classification top-k", parents=[parent]
    )
    s_cls.add_argument("--model", required=True)
    s_cls.add_argument("--input", required=True)
    s_cls.add_argument("--top-k", type=int, default=5)
    s_cls.add_argument("--out-json")
    s_cls.set_defaults(fn=cmd_classify)

    s_emb = sub.add_parser("embed", help="image embedding", parents=[parent])
    s_emb.add_argument("--model", required=True)
    s_emb.add_argument("--input", required=True)
    s_emb.add_argument("--out-json")
    s_emb.set_defaults(fn=cmd_embed)

    s_seg = sub.add_parser("segment", help="image segmentation", parents=[parent])
    s_seg.add_argument("--model", required=True)
    s_seg.add_argument("--input", required=True)
    s_seg.add_argument("--type", choices=["selfie", "interactive"], default="selfie")
    s_seg.add_argument("--out-mask")
    s_seg.set_defaults(fn=cmd_segment)

    s_g = sub.add_parser("gesture", help="hand gesture recognizer", parents=[parent])
    s_g.add_argument("--model", required=True)
    s_g.add_argument("--input", required=True)
    s_g.add_argument("--out-json")
    s_g.set_defaults(fn=cmd_gesture)

    s_a = sub.add_parser(
        "audio-classify", help="YAMNet audio event classification", parents=[parent]
    )
    s_a.add_argument("--model", required=True)
    s_a.add_argument("--input", required=True, help="16-bit PCM wav path")
    s_a.add_argument("--top-k", type=int, default=3)
    s_a.add_argument("--out-json")
    s_a.set_defaults(fn=cmd_audio_classify)

    s_tc = sub.add_parser(
        "text-classify", help="text classifier (sentiment etc.)", parents=[parent]
    )
    s_tc.add_argument("--model", required=True)
    s_tc.add_argument("--text", required=True)
    s_tc.add_argument("--out-json")
    s_tc.set_defaults(fn=cmd_text_classify)

    s_te = sub.add_parser("text-embed", help="text embedder", parents=[parent])
    s_te.add_argument("--model", required=True)
    s_te.add_argument("--text", required=True)
    s_te.add_argument("--out-json")
    s_te.set_defaults(fn=cmd_text_embed)

    s_ld = sub.add_parser("language-detect", help="language detector", parents=[parent])
    s_ld.add_argument("--model", required=True)
    s_ld.add_argument("--text", required=True)
    s_ld.add_argument("--out-json")
    s_ld.set_defaults(fn=cmd_language_detect)

    s_llm = sub.add_parser(
        "llm", help="on-device LLM inference (Gemma/Phi-2)", parents=[parent]
    )
    s_llm.add_argument("--model", required=True)
    s_llm.add_argument("--prompt", required=True)
    s_llm.add_argument("--max-tokens", type=int, default=512)
    s_llm.add_argument("--temp", type=float, default=0.8)
    s_llm.add_argument("--top-k", type=int, default=40)
    s_llm.add_argument("--seed", type=int, default=0)
    s_llm.set_defaults(fn=cmd_llm)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
