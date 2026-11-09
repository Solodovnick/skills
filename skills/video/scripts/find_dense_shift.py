"""Find an exact candidate frame offset between two 32x18 CFR indexes."""
import argparse
import json
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--query', type=Path, required=True)
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--q-start', type=int, required=True)
p.add_argument('--q-end', type=int, required=True)
p.add_argument('--shift-center', type=int, required=True)
p.add_argument('--shift-radius', type=int, default=24)
p.add_argument('--sample-step', type=int, default=24)
a = p.parse_args()
for path in (a.query, a.reference):
    size = path.stat().st_size
    if not size or size % (18 * 32):
        p.error(f'Invalid 32x18 index: {path}')
q = np.memmap(a.query, mode='r', dtype='u1').reshape(-1, 18, 32)
r = np.memmap(a.reference, mode='r', dtype='u1').reshape(-1, 18, 32)
if not (0 <= a.q_start < a.q_end <= len(q)) or a.sample_step <= 0 or a.shift_radius < 0:
    p.error('Invalid query interval, sample step or shift radius')
indices = np.arange(a.q_start, a.q_end, a.sample_step)
scores = []
for shift in range(a.shift_center - a.shift_radius, a.shift_center + a.shift_radius + 1):
    valid = indices[(indices + shift >= 0) & (indices + shift < len(r))]
    if len(valid) < .9 * len(indices):
        continue
    error = np.mean(np.abs(q[valid].astype(np.int16) - r[valid + shift].astype(np.int16)), axis=(1, 2))
    scores.append({'shift': shift, 'median_mae': round(float(np.median(error)), 3),
                   'p95_mae': round(float(np.percentile(error, 95)), 3),
                   'lt5_fraction': round(float(np.mean(error < 5)), 3)})
scores.sort(key=lambda row: (row['median_mae'], row['p95_mae']))
print(json.dumps({'sampled': len(indices), 'best': scores[:12]}, indent=2))
