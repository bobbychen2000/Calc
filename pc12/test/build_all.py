import sys, time; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from model import fuselage_parts, wing
from model.assemble import write_glb
t0=time.time()
parts={}
fuselage_parts.build(parts)
wing.build(parts)
extra = sys.argv[1:] 
for mod in extra:
    __import__('model.'+mod, fromlist=['build']).build(parts)
from model import livery
livery.apply(parts)
tot=0
for k,p in parts.items():
    tot+=p.tri_count(); print(f"{k:22s} tris={p.tri_count():7d}")
size, st = write_glb(parts, 'out/all.glb')
print('GLB %.2f MB'%(size/1e6), st, 'time %.1fs'%(time.time()-t0))
