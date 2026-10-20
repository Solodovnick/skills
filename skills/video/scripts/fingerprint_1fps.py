"""Decode a small grayscale frame each second for coarse repeat discovery.

This is an index, not frame-accurate proof of a match or a timing map.
"""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='Raw 96x54 uint8 frames')
    p.add_argument('--overwrite', action='store_true')
    a = p.parse_args()
    if not a.input.is_file():
        p.error(f'Input does not exist: {a.input}')
    if a.output.exists() and not a.overwrite:
        p.error(f'Output exists: {a.output}; use --overwrite to replace it')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    working = a.output.with_name(a.output.name + '.working')
    if working.exists():
        p.error(f'Incomplete output exists: {working}')
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(a.input),
               '-map', '0:v:0', '-vf', 'fps=1,scale=96:54:flags=area,format=gray',
               '-an', '-sn', '-f', 'rawvideo', '-pix_fmt', 'gray', str(working)]
    try:
        subprocess.run(command, check=True)
        size = working.stat().st_size
        if not size or size % (96 * 54):
            raise RuntimeError(f'Invalid raw output size: {size}')
        working.replace(a.output)
    except Exception:
        if working.exists():
            working.unlink()
        raise
    print(json.dumps({'input': str(a.input), 'output': str(a.output),
                      'width': 96, 'height': 54, 'sample_rate_fps': 1,
                      'samples': size // (96 * 54)}))


if __name__ == '__main__':
    main()
