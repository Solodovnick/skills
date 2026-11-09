"""Find high-difference candidate cuts in a 32x18 all-frame index."""
import argparse
import json
from pathlib import Path

import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--index',type=Path,required=True)
p.add_argument('--start',type=int,required=True)
p.add_argument('--end',type=int,required=True)
p.add_argument('--threshold',type=float,default=12)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
size=a.index.stat().st_size
if not size or size % (18 * 32):
    p.error(f'Invalid 32x18 index: {a.index}')
f=np.memmap(a.index,mode='r',dtype='u1').reshape(-1,18,32)
if not (1<=a.start<a.end<=len(f)) or a.threshold < 0:
    p.error('Invalid interval or threshold')
rows=[]
for left in range(a.start,a.end,1000):
    right=min(a.end,left+1000)
    diff=np.mean(np.abs(f[left:right].astype(np.int16)-f[left-1:right-1].astype(np.int16)),axis=(1,2))
    rows.extend({'frame':int(left+i),'mae':round(float(value),3)} for i,value in enumerate(diff) if value>=a.threshold)
a.output.parent.mkdir(parents=True,exist_ok=True)
with open(a.output,'w') as out:json.dump({'index':str(a.index),'interval':[a.start,a.end],'threshold':a.threshold,'frames':rows},out,indent=2)
print(json.dumps({'candidates':len(rows),'top':sorted(rows,key=lambda x:x['mae'],reverse=True)[:30],'output':str(a.output)}))
