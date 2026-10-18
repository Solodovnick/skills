"""Compare source and cleaned audio at several points for drift or offset."""
import argparse
import json
import subprocess

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--source-start', type=float, required=True,
               help='Seconds removed from the start of the source video')
p.add_argument('--duration', type=float, required=True,
               help='Expected duration of the cleaned video in seconds')
p.add_argument('--window', type=float, default=8.0,
               help='Length of each comparison window in seconds')
a = p.parse_args()

rate = 8000
window = a.window
if window < 2 or a.duration < window + 2:
    raise SystemExit('Require window >= 2 s and duration >= window + 2 s')
offsets = sorted(set([1.0, max(0.0, (a.duration - window) / 2),
                      .75 * (a.duration - window), a.duration - window - 1.0]))


def samples(path, start):
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{start:.9f}', '-i', path,
         '-map', '0:a:0', '-t', str(window), '-ac', '1', '-ar', str(rate),
         '-f', 'f32le', 'pipe:1'], capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)


checks = []
for offset in offsets:
    ref = samples(a.source, a.source_start + offset)
    got = samples(a.candidate, offset)
    length = min(len(ref), len(got))
    assert length >= (window - .5) * rate, (offset, len(ref), len(got))
    ref, got = ref[:length], got[:length]
    # Leave a wide interior window so every candidate lag has equal support.
    maxlag = 400
    lo, hi = maxlag, length - maxlag
    x = ref[lo:hi] - np.mean(ref[lo:hi])
    xnorm = np.linalg.norm(x)
    ynorm = np.linalg.norm(got[lo:hi] - np.mean(got[lo:hi]))
    if xnorm <= 0.001:
        if ynorm > 0.001:
            raise SystemExit(f'Candidate has audio where source is silent at {offset:.3f} s')
        check = {'candidate_seconds': round(offset, 3), 'silent': True}
        checks.append(check)
        print(json.dumps(check), flush=True)
        continue
    best = None
    for lag in range(-maxlag, maxlag + 1):
        y = got[lo + lag:hi + lag]
        y = y - np.mean(y)
        corr = float(np.dot(x, y) / (xnorm * np.linalg.norm(y) + 1e-12))
        if best is None or corr > best[1]:
            best = (lag, corr)
    check = {'candidate_seconds': round(offset, 3), 'lag_ms': round(best[0] * 1000 / rate, 3),
             'correlation': round(best[1], 5)}
    checks.append(check)
    print(json.dumps(check), flush=True)
audible = [x for x in checks if not x.get('silent')]
if len(audible) < 2 or any(abs(x['lag_ms']) > 20 or x['correlation'] < .97 for x in audible):
    raise SystemExit('Audio alignment FAIL')
print('Audio alignment PASS', flush=True)
