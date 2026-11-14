"""M8: committed Sentinel-2 rasters vs the detailed extent (bbox, nodata outside the polygon, valid area)."""
import sys, os, json, glob
import numpy as np, rasterio
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping, box
from shapely.ops import transform
from pyproj import Transformer
ROOT = sys.argv[1]
E = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/extent_hull1km.geojson')))
g = E['features'][0]['geometry'] if 'features' in E else E['geometry'] if 'geometry' in E else E
ext_ll = shape(g)
for tif in sorted(glob.glob(os.path.join(ROOT, 'refs/cache/s2/*/*.tif'))):
    with rasterio.open(tif) as ds:
        tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
        ext = transform(lambda x, y, z=None: tr.transform(x, y), ext_ll)
        a = ds.read(1); b = ds.bounds; px = abs(ds.transform.a * ds.transform.e)
        inside = ~geometry_mask([mapping(ext)], out_shape=a.shape, transform=ds.transform, invert=False, all_touched=False)
        touch = ~geometry_mask([mapping(ext)], out_shape=a.shape, transform=ds.transform, invert=False, all_touched=True)
        nd = ds.nodata
        valid = (a != (nd if nd is not None else 0)) if a.ndim == 2 else None
        if ds.count > 1:
            allb = ds.read(); valid = np.any(allb != (nd if nd is not None else 0), axis=0)
        out_valid = int((valid & ~touch).sum())
        bb = box(*b); eb = box(*ext.bounds)
        print('%-45s bands %d px %.0f m  bbox %.2f km2 (extent bbox %.2f km2, bbox within extent bbox + 1 px: %s)  valid %.2f km2  valid pixels outside the polygon (not touching): %d  nodata=%s'
              % (os.path.relpath(tif, ROOT), ds.count, px ** 0.5, bb.area / 1e6, eb.area / 1e6, eb.buffer(px ** 0.5 + 0.01).contains(bb), valid.sum() * px / 1e6, out_valid, nd))
print('extent polygon area %.3f km2' % (ext.area / 1e6))
