"""Report consecutive exact-looking matches for candidate CFR frame shifts."""
import argparse
import json
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--query', type=Path, required=True)
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--shift', type=int, action='append', required=True)
p.add_argument('--threshold', type=float, default=1)
p.add_argument('--min-run', type=int, default=24)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if a.threshold < 0 or a.min_run <= 0:
    p.error('Invalid threshold or minimum run')
for path in (a.query, a.reference):
    size = path.stat().st_size
    if not size or size % (18 * 32):
        p.error(f'Invalid 32x18 index: {path}')
q = np.memmap(a.query, mode='r', dtype='u1').reshape(-1, 18, 32)
r = np.memmap(a.reference, mode='r', dtype='u1').reshape(-1, 18, 32)
rows = []
for shift in a.shift:
    start = max(0, -shift)
    end = min(len(q), len(r) - shift)
    if end <= start:
        rows.append({'shift': shift, 'matched_frames': 0, 'runs': []})
        continue
    matched, runs, run_start, run_max = 0, [], None, 0.0
    for lo in range(start, end, 2000):
        hi = min(end, lo + 2000)
        error = np.mean(np.abs(q[lo:hi].astype(np.int16) - r[lo+shift:hi+shift].astype(np.int16)), axis=(1, 2))
        for frame, value in zip(range(lo, hi), error):
            if value < a.threshold:
                matched += 1
                if run_start is None:
                    run_start, run_max = frame, float(value)
                else:
                    run_max = max(run_max, float(value))
            elif run_start is not None:
                if frame - run_start >= a.min_run:
                    runs.append({'query': [run_start, frame],
                                 'reference': [run_start+shift, frame+shift],
                                 'frames': frame-run_start, 'max_mae': round(run_max, 3)})
                run_start = None
    if run_start is not None and end - run_start >= a.min_run:
        runs.append({'query': [run_start, end], 'reference': [run_start+shift, end+shift],
                     'frames': end-run_start, 'max_mae': round(run_max, 3)})
    rows.append({'shift': shift, 'matched_frames': matched, 'runs': runs})
out = {'query': str(a.query), 'reference': str(a.reference), 'threshold': a.threshold,
       'query_frames': len(q), 'reference_frames': len(r), 'offsets': rows}
a.output.parent.mkdir(parents=True, exist_ok=True)
with open(a.output, 'w') as f:
    json.dump(out, f, indent=2)
print(json.dumps({'output': str(a.output),
                  'offsets': [{'shift': row['shift'], 'matched_frames': row['matched_frames'],
                               'long_runs': row['runs']} for row in rows]}, indent=2))
