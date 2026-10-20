"""Write a side-by-side contact sheet of mapped source and candidate CFR frames."""
import argparse
from pathlib import Path

import cv2
import numpy as np


def frame_at(capture, index):
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
    parser.add_argument('--offset', type=int, action='append', required=True,
                        help='Candidate frame to compare; repeat for each sample')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--crop', type=int, nargs=4, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'),
                        help='Optional source/candidate crop, in original pixel coordinates')
    parser.add_argument('--column-width', type=int, default=640)
    args = parser.parse_args()
    if args.source_start < 0 or args.column_width < 100:
        parser.error('Invalid source start or column width')
    src, dst = cv2.VideoCapture(args.source), cv2.VideoCapture(args.candidate)
    if not src.isOpened() or not dst.isOpened():
        raise SystemExit('Could not open source or candidate')
    try:
        count = int(dst.get(cv2.CAP_PROP_FRAME_COUNT))
        source_count = int(src.get(cv2.CAP_PROP_FRAME_COUNT))
        offsets = sorted(set(args.offset))
        if not offsets or offsets[0] < 0 or offsets[-1] >= count:
            parser.error('Sample offsets exceed candidate')
        if args.source_start + offsets[-1] >= source_count:
            parser.error('Sample offsets exceed source')
        geometry = None
        rows = []
        for offset in offsets:
            frames = [frame_at(src, args.source_start + offset), frame_at(dst, offset)]
            if frames[0].shape != frames[1].shape:
                raise RuntimeError(f'Frame geometry differs at offset {offset}')
            height, width = frames[0].shape[:2]
            if args.crop:
                x, y, w, h = args.crop
                if not (0 <= x < width and 0 <= y < height and w > 0 and h > 0 and
                        x + w <= width and y + h <= height):
                    parser.error('Crop exceeds video frame')
                frames = [frame[y:y+h, x:x+w] for frame in frames]
            target_height = max(1, round(frames[0].shape[0] * args.column_width / frames[0].shape[1]))
            if geometry is None:
                geometry = (args.column_width, target_height)
            elif geometry != (args.column_width, target_height):
                raise RuntimeError('Frame geometry changed during sampling')
            row = np.full((target_height + 30, args.column_width * 2, 3), 245, np.uint8)
            for column, frame in enumerate(frames):
                x0 = column * args.column_width
                row[30:, x0:x0+args.column_width] = cv2.resize(
                    frame, geometry, interpolation=cv2.INTER_AREA)
                label = f'{"source" if column == 0 else "candidate"} frame '
                label += str(args.source_start + offset if column == 0 else offset)
                cv2.putText(row, label, (x0 + 8, 21), cv2.FONT_HERSHEY_SIMPLEX,
                            .6, (20, 20, 20), 1, cv2.LINE_AA)
            rows.append(row)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(args.output), cv2.vconcat(rows),
                           [cv2.IMWRITE_JPEG_QUALITY, 92]):
            raise RuntimeError(f'Could not write {args.output}')
        print(f'{args.output}: {len(offsets)} mapped samples')
    finally:
        src.release()
        dst.release()


if __name__ == '__main__':
    main()
