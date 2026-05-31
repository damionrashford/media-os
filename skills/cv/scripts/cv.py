#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "opencv-contrib-python>=4.10",
#   "numpy>=1.24",
# ]
# ///
"""
cv.py — OpenCV 4.x CLI wrapper exposing the operations most commonly
requested of an LLM agent: image inspection, frame capture, face
detection (YuNet), object tracking, DNN inference (ONNX/YOLO),
camera calibration, panorama stitching.

Non-interactive. Each subcommand supports --dry-run and --verbose.
All subcommands print the equivalent Python / OpenCV call to stderr
before running.

Usage:
  cv.py info IMAGE
  cv.py capture --src SRC --count N --out DIR
  cv.py detect-faces IMAGE --model ONNX [--score-threshold 0.9] [--draw] [--out OUT]
  cv.py track --src SRC --bbox 'x,y,w,h' [--tracker csrt|kcf|mil|nano|vit|dasiamrpn] --out OUT
  cv.py yolo --model ONNX --input IMAGE [--labels FILE] [--conf 0.25] [--iou 0.45] [--out OUT]
  cv.py calibrate --pattern chessboard --size 9x6 --square-mm 25 --images 'calib/*.jpg' --out YAML
  cv.py stitch IMG [IMG ...] --out OUT
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except ImportError:
    print(
        "error: cv2 not importable. `pip install opencv-contrib-python` or run via `uv run`.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trace(msg: str, verbose: bool) -> None:
    if verbose:
        print(f"[cv] {msg}", file=sys.stderr)


def _emit_cmd(cmd: str, verbose: bool) -> None:
    # Print the conceptual OpenCV call we're about to perform.
    if verbose:
        print(f"[cv.call] {cmd}", file=sys.stderr)


def _read_image(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        # Non-ASCII-path fallback
        try:
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        except Exception:  # noqa: BLE001
            img = None
    if img is None:
        raise FileNotFoundError(f"cv2.imread returned None for: {path!r}")
    return img


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_info(args: argparse.Namespace) -> int:
    _emit_cmd(f"cv2.imread({args.image!r})", args.verbose)
    if args.dry_run:
        return 0
    img = _read_image(args.image)
    h, w = img.shape[:2]
    c = 1 if img.ndim == 2 else img.shape[2]
    info: dict[str, Any] = {
        "path": str(Path(args.image).resolve()),
        "shape": list(img.shape),
        "dtype": str(img.dtype),
        "height": h,
        "width": w,
        "channels": c,
        "min": float(img.min()),
        "max": float(img.max()),
        "mean": [float(v) for v in (img.mean(axis=(0, 1)) if c > 1 else [img.mean()])],
    }
    print(json.dumps(info, indent=2))
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    out = Path(args.out)
    # VideoCapture accepts int (device index) or string (path / URL)
    try:
        src: int | str = int(args.src)
    except ValueError:
        src = args.src
    _emit_cmd(
        f"cv2.VideoCapture({src!r}) -> {args.count} frames -> {out}/", args.verbose
    )
    if args.dry_run:
        return 0
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"error: VideoCapture failed for {args.src!r}", file=sys.stderr)
        return 1
    try:
        written = 0
        for i in range(args.count):
            ok, frame = cap.read()
            if not ok or frame is None:
                _trace(f"read failed at frame {i}", args.verbose)
                break
            path = out / f"frame_{i:06d}.png"
            cv2.imwrite(str(path), frame)
            written += 1
        print(json.dumps({"written": written, "out": str(out)}))
    finally:
        cap.release()
    return 0


def cmd_detect_faces(args: argparse.Namespace) -> int:
    if not args.model or not Path(args.model).exists():
        print(
            f"error: model not found: {args.model!r}.\n"
            "Download YuNet from https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
            file=sys.stderr,
        )
        return 2
    _emit_cmd(
        f"cv2.FaceDetectorYN.create({args.model!r}, ..., score_threshold={args.score_threshold})",
        args.verbose,
    )
    if args.dry_run:
        return 0
    img = _read_image(args.image)
    h, w = img.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        args.model, "", (w, h), args.score_threshold, args.nms_threshold, args.top_k
    )
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    out: list[dict] = []
    if faces is not None:
        for face in faces:
            x, y, fw, fh = face[:4].astype(int).tolist()
            landmarks = face[4:14].astype(int).reshape(5, 2).tolist()
            score = float(face[14])
            out.append({"bbox": [x, y, fw, fh], "landmarks": landmarks, "score": score})
    print(json.dumps({"faces": out}, indent=2))
    if args.draw and args.out:
        for d in out:
            x, y, fw, fh = d["bbox"]
            cv2.rectangle(img, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
            for lx, ly in d["landmarks"]:
                cv2.circle(img, (lx, ly), 2, (0, 0, 255), -1)
        cv2.imwrite(args.out, img)
        _trace(f"wrote {args.out}", args.verbose)
    return 0


_TRACKERS = {
    "mil": ("TrackerMIL_create", None),
    "kcf": ("TrackerKCF_create", None),
    "csrt": ("TrackerCSRT_create", None),
    "nano": ("TrackerNano_create", None),
    "vit": ("TrackerVit_create", None),
    "dasiamrpn": ("TrackerDaSiamRPN_create", None),
}


def cmd_track(args: argparse.Namespace) -> int:
    factory = _TRACKERS[args.tracker][0]
    if not hasattr(cv2, factory):
        print(
            f"error: tracker {args.tracker!r} ({factory}) not present in your cv2 build; "
            "install opencv-contrib-python.",
            file=sys.stderr,
        )
        return 2
    x, y, w, h = (int(v) for v in args.bbox.split(","))
    _emit_cmd(
        f"cv2.{factory}()  then .init(frame0, ({x},{y},{w},{h})) and .update() per frame",
        args.verbose,
    )
    if args.dry_run:
        return 0
    try:
        src: int | str = int(args.src)
    except ValueError:
        src = args.src
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"error: VideoCapture failed for {args.src!r}", file=sys.stderr)
        return 1
    ok, frame = cap.read()
    if not ok:
        cap.release()
        print("error: could not read first frame", file=sys.stderr)
        return 1
    tracker = getattr(cv2, factory)()
    tracker.init(frame, (x, y, w, h))
    writer = None
    if args.out:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        fh, fw = frame.shape[:2]
        writer = cv2.VideoWriter(args.out, fourcc, fps, (fw, fh))
    n = 0
    lost = 0
    try:
        while True:
            ok_up, box = tracker.update(frame)
            if ok_up:
                bx, by, bw, bh = (int(v) for v in box)
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            else:
                lost += 1
            if writer is not None:
                writer.write(frame)
            n += 1
            ok, frame = cap.read()
            if not ok:
                break
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    print(json.dumps({"frames": n, "lost": lost, "out": args.out}))
    return 0


def cmd_yolo(args: argparse.Namespace) -> int:
    if not Path(args.model).exists():
        print(f"error: model not found: {args.model!r}", file=sys.stderr)
        return 2
    labels: list[str] = []
    if args.labels and Path(args.labels).exists():
        labels = Path(args.labels).read_text().splitlines()
    _emit_cmd(
        f"net = cv2.dnn.readNetFromONNX({args.model!r}); blob = cv2.dnn.blobFromImage(img, 1/255.0, ({args.size}, {args.size}), swapRB=True)",
        args.verbose,
    )
    if args.dry_run:
        return 0
    img = _read_image(args.input)
    ih, iw = img.shape[:2]
    net = cv2.dnn.readNetFromONNX(args.model)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    blob = cv2.dnn.blobFromImage(
        img, 1 / 255.0, (args.size, args.size), swapRB=True, crop=False
    )
    net.setInput(blob)
    outputs = net.forward()
    # YOLOv8 ONNX output shape is (1, 4+nc, N); transpose to (N, 4+nc)
    if outputs.ndim == 3 and outputs.shape[1] < outputs.shape[2]:
        outputs = outputs[0].T
    else:
        outputs = outputs[0]
    boxes, scores, class_ids = [], [], []
    x_factor = iw / args.size
    y_factor = ih / args.size
    for row in outputs:
        class_scores = row[4:]
        class_id = int(np.argmax(class_scores))
        conf = float(class_scores[class_id])
        if conf < args.conf:
            continue
        cx, cy, w, h = row[:4]
        left = int((cx - w / 2) * x_factor)
        top = int((cy - h / 2) * y_factor)
        width = int(w * x_factor)
        height = int(h * y_factor)
        boxes.append([left, top, width, height])
        scores.append(conf)
        class_ids.append(class_id)
    keep = cv2.dnn.NMSBoxes(boxes, scores, args.conf, args.iou)
    detections: list[dict] = []
    if len(keep) > 0:
        for i in np.array(keep).flatten():
            detections.append(
                {
                    "bbox": boxes[i],
                    "score": scores[i],
                    "class_id": class_ids[i],
                    "label": (
                        labels[class_ids[i]] if class_ids[i] < len(labels) else None
                    ),
                }
            )
    print(json.dumps({"detections": detections}, indent=2))
    if args.out:
        vis = img.copy()
        for d in detections:
            x, y, w, h = d["bbox"]
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            lab = d["label"] or str(d["class_id"])
            cv2.putText(
                vis,
                f"{lab} {d['score']:.2f}",
                (x, max(12, y - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )
        cv2.imwrite(args.out, vis)
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    if args.pattern != "chessboard":
        print(
            f"error: only --pattern chessboard implemented (requested {args.pattern!r})",
            file=sys.stderr,
        )
        return 2
    cols, rows = (int(v) for v in args.size.lower().split("x"))
    inner = (cols, rows)
    files = sorted(glob.glob(args.images))
    if len(files) < 5:
        print(f"error: need >=5 calibration images, got {len(files)}", file=sys.stderr)
        return 1
    _emit_cmd(
        f"cv2.findChessboardCorners(..., {inner}) then cv2.calibrateCamera(...) on {len(files)} images",
        args.verbose,
    )
    if args.dry_run:
        return 0
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * args.square_mm
    objpoints, imgpoints = [], []
    last_shape = None
    for f in files:
        img = _read_image(f)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ok, corners = cv2.findChessboardCorners(gray, inner, None)
        if not ok:
            _trace(f"skip (no corners): {f}", args.verbose)
            continue
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        objpoints.append(objp)
        imgpoints.append(corners)
        last_shape = gray.shape[::-1]
    if not objpoints:
        print("error: no chessboard corners found in any image", file=sys.stderr)
        return 1
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, last_shape, None, None
    )
    fs = cv2.FileStorage(args.out, cv2.FILE_STORAGE_WRITE)
    fs.write("rms", rms)
    fs.write("camera_matrix", K)
    fs.write("dist_coeff", dist)
    fs.write("image_size", np.array(list(last_shape), dtype=np.int32))
    fs.release()
    print(json.dumps({"rms": rms, "out": args.out, "images_used": len(objpoints)}))
    return 0


def cmd_stitch(args: argparse.Namespace) -> int:
    if len(args.images) < 2:
        print("error: need >=2 images", file=sys.stderr)
        return 1
    _emit_cmd(
        f"cv2.Stitcher.create(PANORAMA).stitch({len(args.images)} images)", args.verbose
    )
    if args.dry_run:
        return 0
    imgs = [_read_image(p) for p in args.images]
    stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
    status, pano = stitcher.stitch(imgs)
    if status != cv2.Stitcher_OK:
        names = {
            cv2.Stitcher_ERR_NEED_MORE_IMGS: "NEED_MORE_IMGS",
            cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: "HOMOGRAPHY_EST_FAIL",
            cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "CAMERA_PARAMS_ADJUST_FAIL",
        }
        print(
            f"error: stitch failed status={status} ({names.get(status, 'UNKNOWN')})",
            file=sys.stderr,
        )
        return 1
    cv2.imwrite(args.out, pano)
    print(json.dumps({"out": args.out, "shape": list(pano.shape)}))
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    # Parent parser supplies global flags usable before OR after the subcommand.
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--dry-run", action="store_true", help="print call, skip execution"
    )
    parent.add_argument(
        "--verbose", action="store_true", help="trace OpenCV calls to stderr"
    )

    p = argparse.ArgumentParser(
        description="OpenCV 4.x CLI: info, capture, detect-faces, track, yolo, calibrate, stitch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[parent],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("info", help="print image shape/dtype/stats", parents=[parent])
    s1.add_argument("image")
    s1.set_defaults(fn=cmd_info)

    s2 = sub.add_parser(
        "capture", help="grab N frames via VideoCapture", parents=[parent]
    )
    s2.add_argument("--src", required=True, help="int device index, path, or RTSP URL")
    s2.add_argument("--count", type=int, default=30)
    s2.add_argument("--out", required=True, help="output directory")
    s2.set_defaults(fn=cmd_capture)

    s3 = sub.add_parser(
        "detect-faces", help="YuNet FaceDetectorYN on one image", parents=[parent]
    )
    s3.add_argument("image")
    s3.add_argument("--model", required=True, help="YuNet ONNX path")
    s3.add_argument("--score-threshold", type=float, default=0.9)
    s3.add_argument("--nms-threshold", type=float, default=0.3)
    s3.add_argument("--top-k", type=int, default=5000)
    s3.add_argument("--draw", action="store_true")
    s3.add_argument("--out", help="annotated output image (when --draw)")
    s3.set_defaults(fn=cmd_detect_faces)

    s4 = sub.add_parser("track", help="tracker on a source", parents=[parent])
    s4.add_argument("--src", required=True)
    s4.add_argument("--bbox", required=True, help="x,y,w,h on the first frame")
    s4.add_argument(
        "--tracker",
        default="csrt",
        choices=list(_TRACKERS),
        help="modern tracker (not cv2.legacy)",
    )
    s4.add_argument("--out", help="annotated mp4 output")
    s4.set_defaults(fn=cmd_track)

    s5 = sub.add_parser("yolo", help="ONNX YOLO-style inference", parents=[parent])
    s5.add_argument("--model", required=True)
    s5.add_argument("--input", required=True)
    s5.add_argument("--labels", help="newline class names file (e.g. coco.names)")
    s5.add_argument("--size", type=int, default=640)
    s5.add_argument("--conf", type=float, default=0.25)
    s5.add_argument("--iou", type=float, default=0.45)
    s5.add_argument("--out")
    s5.set_defaults(fn=cmd_yolo)

    s6 = sub.add_parser("calibrate", help="camera calibration", parents=[parent])
    s6.add_argument("--pattern", default="chessboard", choices=["chessboard"])
    s6.add_argument("--size", required=True, help="inner corners, e.g. 9x6")
    s6.add_argument("--square-mm", type=float, default=25.0)
    s6.add_argument("--images", required=True, help="glob, e.g. 'calib/*.jpg'")
    s6.add_argument("--out", required=True, help="output YAML path")
    s6.set_defaults(fn=cmd_calibrate)

    s7 = sub.add_parser("stitch", help="panorama stitch", parents=[parent])
    s7.add_argument("images", nargs="+")
    s7.add_argument("--out", required=True)
    s7.set_defaults(fn=cmd_stitch)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
