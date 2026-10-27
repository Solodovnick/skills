"""Prove frame-accurate input seeking against a full decode for selected CFR frames.

The slow reference decodes from the start with ``trim=start_frame``. The fast
candidate seeks at ``frame / fps`` before input. Compare decoded raw bytes so a
long chunk worker can use the fast command only after checking its source.
"""
import argparse
import hashlib
import json
import subprocess
from fractions import Fraction


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True)
parser.add_argument('--frame', type=int, action='append', required=True,
                    help='Zero-based source frame; repeat at early, middle and late positions')
args = parser.parse_args()

probe = subprocess.run([
    'ffprobe', '-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=avg_frame_rate,r_frame_rate,nb_frames,start_time',
    '-of', 'json', args.source,
], capture_output=True, text=True, check=True)
stream, = json.loads(probe.stdout)['streams']
fps = Fraction(stream['avg_frame_rate'])
nominal = Fraction(stream['r_frame_rate'])
if fps <= 0 or fps != nominal:
    parser.error('Expected constant nominal and average frame rate; inspect PTS for VFR')
if abs(float(stream.get('start_time', 0))) > 1e-6:
    parser.error('Nonzero video start time needs a separate PTS mapping')
count = int(stream['nb_frames'])


def decode(extra):
    return subprocess.check_output([
        'ffmpeg', '-nostdin', '-v', 'error', *extra,
        '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1',
    ])


checks = []
for frame in sorted(set(args.frame)):
    if frame < 0 or frame >= count:
        parser.error(f'Frame {frame} outside 0..{count - 1}')
    reference = decode([
        '-i', args.source,
        '-vf', f'trim=start_frame={frame}:end_frame={frame + 1},setpts=PTS-STARTPTS',
    ])
    seconds = frame * fps.denominator / fps.numerator
    sought = decode(['-ss', f'{seconds:.9f}', '-i', args.source])
    row = {'frame': frame, 'seek_seconds': round(seconds, 9),
           'raw_bytes': len(reference),
           'reference_sha256': hashlib.sha256(reference).hexdigest(),
           'seek_sha256': hashlib.sha256(sought).hexdigest(),
           'match': reference == sought}
    checks.append(row)

result = {'source': args.source, 'fps': str(fps), 'checks': checks,
          'status': 'PASS' if all(x['match'] and x['raw_bytes'] for x in checks) else 'FAIL'}
print(json.dumps(result, ensure_ascii=False), flush=True)
if result['status'] != 'PASS':
    raise SystemExit(1)
