"""Small grayscale index of every decoded CFR frame for exact reuse mapping."""
import argparse
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--input', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
width, height = 32, 18
if not a.input.is_file():
    p.error(f'Input does not exist: {a.input}')
if a.output.exists():
    p.error(f'Output exists: {a.output}')
a.output.parent.mkdir(parents=True, exist_ok=True)
working = a.output.with_name(a.output.name + '.working')
if working.exists():
    p.error(f'Incomplete output exists: {working}')
cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-threads', '2', '-i', str(a.input),
       '-map', '0:v:0', '-vf', f'scale={width}:{height}:flags=area,format=gray',
       '-an', '-sn', '-f', 'rawvideo', '-pix_fmt', 'gray', str(working)]
try:
    subprocess.run(cmd, check=True)
    size = working.stat().st_size
    if not size or size % (width * height):
        raise ValueError(f'Invalid index size: {size}')
    working.replace(a.output)
except Exception:
    working.unlink(missing_ok=True)
    raise
print(json.dumps({'input': str(a.input), 'output': str(a.output),
                  'width': width, 'height': height, 'frames': size // (width * height)}))
