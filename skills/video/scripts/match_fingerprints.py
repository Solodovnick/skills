"""Find candidate repeated intervals in two 96x54 grayscale 1 fps indexes."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


WIDTH, HEIGHT = 96, 54


def read(path):
    size = path.stat().st_size
    if size == 0 or size % (WIDTH * HEIGHT):
        raise ValueError(f'Not a nonempty {WIDTH}x{HEIGHT} raw fingerprint: {path}')
    return np.memmap(path, mode='r', dtype=np.uint8).reshape(-1, HEIGHT, WIDTH)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--query', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--start-second', type=int, default=0)
    p.add_argument('--end-second', type=int)
    p.add_argument('--step', type=int, default=10)
    p.add_argument('--max-mae', type=float, default=10)
    a = p.parse_args()
    q, r = read(a.query), read(a.reference)
    end = len(q) if a.end_second is None else a.end_second
    if not (0 <= a.start_second < end <= len(q)) or a.step <= 0 or a.max_mae < 0:
        p.error('Invalid query interval, step, or MAE threshold')
    seconds = np.arange(a.start_second, end, a.step)
    shrink = lambda im: cv2.resize(im, (24, 14), interpolation=cv2.INTER_AREA).reshape(-1)
    train = np.stack([shrink(im) for im in r]).astype(np.float32)
    query = np.stack([shrink(q[s]) for s in seconds]).astype(np.float32)
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    neighbors = matcher.knnMatch(query, train, k=min(8, len(train)))
    rows = []
    for second, matches in zip(seconds, neighbors):
        candidates = []
        for item in matches:
            ref_second = item.trainIdx
            mae = float(np.mean(np.abs(q[second].astype(np.int16) - r[ref_second].astype(np.int16))))
            candidates.append({'reference_second': ref_second, 'mae': round(mae, 3)})
        candidates.sort(key=lambda item: item['mae'])
        rows.append({'query_second': int(second), 'best': candidates[:4]})
    result = {'query': str(a.query), 'reference': str(a.reference),
              'sample_step_seconds': a.step, 'width': WIDTH, 'height': HEIGHT,
              'max_mae': a.max_mae,
              'candidate_matches': sum(row['best'][0]['mae'] <= a.max_mae for row in rows),
              'sampled_points': len(rows), 'matches': rows}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(a.output), 'sampled_points': len(rows),
                      'candidate_matches': result['candidate_matches']}))


if __name__ == '__main__':
    main()
