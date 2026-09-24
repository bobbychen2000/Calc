import sys, time; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from model import fuselage_parts
from model.assemble import write_glb
t0=time.time()
parts={}
fuselage_parts.build(parts)
for k,p in parts.items(): print(f"{k:22s} tris={p.tri_count():7d}  meshes={len(p.meshes)}")
size, st = write_glb(parts, 'out/fus.glb')
print('GLB', size/1e6, 'MB', st, 'time %.1fs'%(time.time()-t0))
