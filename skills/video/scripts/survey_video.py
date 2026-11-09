"""Opening, ending and timeline contact sheets for an existing CFR video."""
import argparse
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--opening-seconds', type=float, default=16)
parser.add_argument('--ending-seconds', type=float, default=50)
parser.add_argument('--timeline-step-seconds', type=float, default=100)
args = parser.parse_args()
if min(args.opening_seconds, args.ending_seconds, args.timeline_step_seconds) <= 0:
    parser.error('sampling intervals must be positive')
args.output.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(str(args.source))
if not cap.isOpened():
    parser.error(f'cannot open {args.source}')
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
if total <= 0 or fps <= 0:
    parser.error('invalid frame count or FPS')
opening = min(total, round(args.opening_seconds * fps))
ending = min(total, round(args.ending_seconds * fps))
groups = {
    'opening': list(range(0, opening, max(1, round(fps / 2)))),
    'ending': list(range(max(0, total-ending), total, max(1, round(2 * fps)))) + [total-1],
    'timeline': list(range(0, total, max(1, round(args.timeline_step_seconds * fps)))) + [total-1],
}
for group, indices in groups.items():
    indices = sorted(set(indices))
    for page in range(0, len(indices), 24):
        sub = indices[page:page+24]
        sheet = Image.new('RGB', (1920, 1800), '#111')
        draw = ImageDraw.Draw(sheet)
        for k, idx in enumerate(sub):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f'cannot decode frame {idx} of {args.source}')
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            thumb = Image.fromarray(rgb).resize((480, 270), Image.Resampling.LANCZOS)
            x, y = (k % 4) * 480, (k // 4) * 300
            sheet.paste(thumb, (x, y+25))
            draw.text((x+5, y+5), f'{idx} / {idx/fps:.3f}s', fill='white')
        sheet.save(args.output / f'{group}_{page//24+1:02d}.jpg', quality=90)
    print(group, len(indices), flush=True)
cap.release()
print('frames', total, 'fps', fps, flush=True)
