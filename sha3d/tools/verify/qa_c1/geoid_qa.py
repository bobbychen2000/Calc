import sys, math
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
import rasterio, numpy as np
from scipy.interpolate import RegularGridInterpolator
fn='/home/user/Calc/sha3d/refs/cache/geoid_egm2008/egm08_25_crop_N31.0-31.4_E121.0-121.7.tif'
ds=rasterio.open(fn); a=ds.read(1).astype(float)
print(ds.tags(), ds.tags(1), ds.profile.get('AREA_OR_POINT'), ds.tags().get('AREA_OR_POINT'))
T=ds.transform
lons = T.c + T.a*(np.arange(ds.width)+0.5); lats = T.f + T.e*(np.arange(ds.height)+0.5)
f = RegularGridInterpolator((lats[::-1], lons), a[::-1,:])
res=[]
for x in np.linspace(-4000,4000,9):
    for z in np.linspace(-4000,4000,9):
        la,lo=F.world_to_ll(x,z)
        res.append((x,z,f((la,lo)).item()))
res=np.array(res)
A=np.c_[np.ones(len(res)),res[:,0],res[:,1]]
c,*_=np.linalg.lstsq(A,res[:,2],rcond=None)
print('fit n0 dn_dx dn_dz',c, 'frame', F.GEOID_N0,F.GEOID_DN_DX,F.GEOID_DN_DZ)
print('max resid frame plane', np.abs(res[:,2]-(F.GEOID_N0+F.GEOID_DN_DX*res[:,0]+F.GEOID_DN_DZ*res[:,1])).max())
# extent N range
import json
d=json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
ring=np.array(d['extent']['ring'])
vals=[f(F.world_to_ll(x,z)).item() for x,z in ring]
print('N over extent ring', min(vals), max(vals), 'extent x range', ring[:,0].min(), ring[:,0].max(), 'z', ring[:,1].min(), ring[:,1].max())
print('max resid frame plane on ring', max(abs(v-F.geoid_n(x,z)) for v,(x,z) in zip(vals,ring)))
