"""Check CFR frame mapping in an untouched center region of cleaned video."""
import argparse
import json

import cv2
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--source-frame-start', type=int, required=True)
p.add_argument('--expected-frames', type=int, required=True)
p.add_argument('--max-mae', type=float, default=5.0)
a = p.parse_args()

src = cv2.VideoCapture(a.source)
dst = cv2.VideoCapture(a.candidate)
assert src.isOpened() and dst.isOpened(), 'Could not open source/candidate'
count = int(dst.get(cv2.CAP_PROP_FRAME_COUNT))
if count != a.expected_frames:
    raise SystemExit(f'Frame count {count} != {a.expected_frames}')
checks = []
for offset in sorted(set([0, min(30, count - 1), count // 2, count - 1])):
    src.set(cv2.CAP_PROP_POS_FRAMES, a.source_frame_start + offset)
    dst.set(cv2.CAP_PROP_POS_FRAMES, offset)
    ok1, s = src.read()
    ok2, d = dst.read()
    if not (ok1 and ok2) or s.shape != d.shape:
        raise SystemExit(f'Could not compare frame {offset}')
    h, w = s.shape[:2]
    center = (slice(round(.28 * h), round(.65 * h)),
              slice(round(.36 * w), round(.63 * w)))
    mae = float(np.mean(np.abs(s[center].astype(np.int16) -
                               d[center].astype(np.int16))))
    checks.append({'candidate_frame': offset,
                   'source_frame': a.source_frame_start + offset,
                   'mae_center': round(mae, 3)})
src.release()
dst.release()
print(json.dumps({'frames': count, 'checks': checks}), flush=True)
if max(item['mae_center'] for item in checks) > a.max_mae:
    raise SystemExit('Frame alignment FAIL')
print('Frame alignment PASS', flush=True)
