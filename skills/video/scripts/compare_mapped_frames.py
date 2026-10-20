"""Sample corresponding decoded frames in two CFR videos.

Requires opencv-python and numpy. MAE is a diagnostic, not a visual QA verdict.
"""

import argparse
import json

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--left-start", required=True, type=int)
    parser.add_argument("--right-start", required=True, type=int)
    parser.add_argument("--frames", required=True, type=int)
    parser.add_argument("--step", type=int, default=250)
    parser.add_argument("--resize-width", type=int, default=480)
    parser.add_argument("--max-mae", type=float)
    args = parser.parse_args()
    if min(args.left_start, args.right_start) < 0 or min(args.frames, args.step, args.resize_width) <= 0:
        parser.error("frame starts must be nonnegative; frames, step, and resize-width must be positive")

    left = cv2.VideoCapture(args.left)
    right = cv2.VideoCapture(args.right)
    if not left.isOpened() or not right.isOpened():
        raise SystemExit("Could not open both videos")
    try:
        left_count = int(left.get(cv2.CAP_PROP_FRAME_COUNT))
        right_count = int(right.get(cv2.CAP_PROP_FRAME_COUNT))
        if args.left_start + args.frames > left_count or args.right_start + args.frames > right_count:
            raise SystemExit(f"Mapped interval exceeds video: left={left_count}, right={right_count}")

        offsets = sorted(set([0, args.frames - 1, *range(0, args.frames, args.step)]))
        checks = []
        for offset in offsets:
            pair = []
            for capture, start in ((left, args.left_start), (right, args.right_start)):
                capture.set(cv2.CAP_PROP_POS_FRAMES, start + offset)
                ok, frame = capture.read()
                if not ok:
                    raise SystemExit(f"Could not decode frame at interval offset {offset}")
                height, width = frame.shape[:2]
                target_height = max(1, round(height * args.resize_width / width))
                pair.append(cv2.resize(frame, (args.resize_width, target_height), interpolation=cv2.INTER_AREA))
            if pair[0].shape != pair[1].shape:
                raise SystemExit("Frame geometry differs after proportional resize")
            mae = float(np.mean(np.abs(pair[0].astype(np.int16) - pair[1].astype(np.int16))))
            checks.append({"offset": offset, "left_frame": args.left_start + offset,
                           "right_frame": args.right_start + offset, "mae": round(mae, 3)})
        summary = {"samples": len(checks), "max_mae": max(item["mae"] for item in checks),
                   "checks": checks}
        print(json.dumps(summary, ensure_ascii=False))
        if args.max_mae is not None and summary["max_mae"] > args.max_mae:
            raise SystemExit("Mapped-frame comparison exceeded --max-mae")
    finally:
        left.release()
        right.release()


if __name__ == "__main__":
    main()
