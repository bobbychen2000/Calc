import sys, numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from cad.mesh import *
from cad.glb import GLBBuilder

# 1. revolve cylinder: normals outward
m = revolve([(0,0.5),(2,0.5)], n=32, axis_origin=(0,0,0), axis_dir=(1,0,0))
r = m.V[:,1:]; nr = m.N[:,1:]
print('cyl outward:', np.mean(np.sum(r*nr,1))>0, 'faces agree:', np.mean(np.sum(m.face_normals()*m.N[m.F[:,0]],1))>0)
# 2. superellipsoid
s = superellipsoid((0,0,0),(1,0.5,0.3),(0.3,0.3))
print('superellipsoid outward:', np.mean(np.sum(s.V*s.N,1))>0, np.mean(np.sum(s.face_normals()*s.N[s.F[:,0]],1))>0)
# 3. grid + trim hole + loops + solidify
u = np.linspace(0,2,81); v = np.linspace(0,1,41)
U,V = np.meshgrid(u,v,indexing='ij')
P = np.stack([U, V, 0.1*np.sin(U*2)],-1)
g = grid_surface(P)
print('grid normal z>0:', g.N[:,2].mean()>0)
d = np.sqrt((g.V[:,0]-1)**2+(g.V[:,1]-0.5)**2)-0.2
h = trim(g, d, keep='positive')
loops = boundary_loops(h)
print('trim: faces', g.nf, '->', h.nf, 'loops', len(loops), [len(l) for l in loops])
plug = trim(g, d, keep='negative')
sl = solidify(plug, 0.03)
print('solid plug faces', sl.nf, 'loops of plug', len(boundary_loops(plug)))
tube = sweep_tube(np.stack([np.linspace(0,1,20), np.sin(np.linspace(0,3,20))*0.3, np.zeros(20)],1), 0.05, n=12)
print('tube ok', tube.nf)
b = box((0,0,0),(1,2,3))
print('box outward', np.mean(np.sum(b.V*b.N,1))>0, np.mean(np.sum(b.face_normals()*b.N[b.F[:,0]],1))>0)
dk = disk((0,0,0),(1,0,0),0.5)
print('disk normal', dk.face_normals().mean(0))
gb = GLBBuilder()
mat = gb.material('grey',(0.7,0.7,0.72),0.1,0.5)
ids = [gb.mesh_node('cyl', m, mat), gb.mesh_node('holey', h.translated((0,2,0)), mat), gb.mesh_node('plug', sl.translated((0,2,0.5)), mat), gb.mesh_node('tube', tube, mat), gb.mesh_node('box', b.translated((3,0,0)), mat), gb.mesh_node('se', s.translated((0,-2,0)), mat)]
root = gb.node('root', children=ids)
print('glb bytes', gb.write(str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out/test.glb", [root]))
