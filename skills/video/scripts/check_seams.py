"""Check decoded CFR frames around assembly seams against an unchanged source center.

The source and candidate must keep the same frame order after one leading cut.
This numerical check does not judge the restored overlay regions.
"""
import argparse
import json

import cv2
import numpy as np


def read_at(capture, index):
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f'Could not decode frame {index}')
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--source-start', type=int, required=True,
                        help='Source frame corresponding to candidate frame 0')
    parser.add_argument('--expected-frames', type=int, required=True)
    parser.add_argument('--seam', type=int, action='append', required=True,
                        help='First candidate frame of a new segment; repeat for each seam')
    parser.add_argument('--radius', type=int, default=3)
    parser.add_argument('--max-center-mae', type=float, default=10)
    args = parser.parse_args()
    if args.source_start < 0 or args.expected_frames <= 0 or args.radius < 1 or args.max_center_mae < 0:
        parser.error('Invalid source offset, frame count, radius, or threshold')
    if any(not 0 < seam < args.expected_frames for seam in args.seam):
        parser.error('Each seam must be inside the candidate')
    src, dst = cv2.VideoCapture(args.source), cv2.VideoCapture(args.candidate)
    if not src.isOpened() or not dst.isOpened():
        raise SystemExit('Could not open source or candidate')
    try:
        count = int(dst.get(cv2.CAP_PROP_FRAME_COUNT))
        if count != args.expected_frames:
            raise SystemExit(f'Candidate frame count {count} != {args.expected_frames}')
        if args.source_start + count > int(src.get(cv2.CAP_PROP_FRAME_COUNT)):
            raise SystemExit('Candidate interval exceeds source')
        indices = sorted({frame for seam in args.seam
                          for frame in range(max(0, seam - args.radius),
                                             min(count, seam + args.radius + 1))})
        checks = []
        for frame in indices:
            left = read_at(src, args.source_start + frame)
            right = read_at(dst, frame)
            if left.shape != right.shape:
                raise SystemExit(f'Frame geometry differs at {frame}')
            height, width = left.shape[:2]
            center = (slice(round(.28 * height), round(.65 * height)),
                      slice(round(.36 * width), round(.63 * width)))
            mae = float(np.mean(np.abs(left[center].astype(np.int16) -
                                       right[center].astype(np.int16))))
            checks.append({'candidate_frame': frame, 'source_frame': args.source_start + frame,
                           'mae_center': round(mae, 3)})
        summary = {'frames': count, 'seams': sorted(set(args.seam)), 'checked_frames': len(checks),
                   'max_center_mae': max(row['mae_center'] for row in checks), 'checks': checks}
        print(json.dumps(summary))
        if summary['max_center_mae'] > args.max_center_mae:
            raise SystemExit('Seam alignment FAIL')
        print('Seam alignment PASS')
    finally:
        src.release()
        dst.release()


if __name__ == '__main__':
    main()
