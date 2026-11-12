"""Check that the NAIP 2024 mosaic read from the USDA image service (naip_fetch.py --source usda) holds the tiles'
native pixels: compare windows of it with the same NAIP 2024 tiles read directly from their Cloud-Optimized GeoTIFFs on
Microsoft Planetary Computer (which added the CA 2024 items after sfo3d's survey; STAC search 2026-11-12 lists
ca_m_3712223_se_10_060_20240520 and ca_m_3712224_sw_10_060_20240520).

New for hwd3d (sfo3d inferred the native grid from pixel-boundary positions and the 2022-vs-2024 correlation; here
the two copies of the same 2024 tile are compared directly). If the USDA exportImage had resampled (bilinear,
half-pixel shift, reprojection through the service's WGS 84 mosaic), the windows would differ.

Writes refs/cache/naip/naip_grid_check.json.
usage: python3 -I hwd3d/tools/imagery/naip_grid_check.py
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import F, CACHE, geotiff_path  # noqa: E402
import naip_fetch as NF                    # noqa: E402

WINDOWS = {   # name -> (lat, lon) centre; 512 x 512 px each
    'ARP (tile 3712224_sw)': (F.ARP_LAT, F.ARP_LON),
    '10R end (tile 3712223_se)': (F.RWY_ENDS['10R']['lat'], F.RWY_ENDS['10R']['lon']),
}
TILES = {'3712224_sw': 'ca_m_3712224_sw_10_060_20240520', '3712223_se': 'ca_m_3712223_se_10_060_20240520'}


def main():
    import rasterio
    from rasterio.windows import from_bounds
    res = NF.http_json(NF.STAC, {'collections': ['naip'], 'ids': list(TILES.values()), 'limit': 10})
    items = {f['id']: f for f in res['features']}
    tok = NF.token()
    out = dict(about=__doc__.split('\n\n')[0], windows={})
    with rasterio.open(geotiff_path('2024')) as us:
        for name, (la, lo) in WINDOWS.items():
            tile = TILES[name.split('tile ')[1].rstrip(')')]
            E, N = F.ll_to_utm10(la, lo)
            e0 = np.floor(E / 0.6) * 0.6 - 256 * 0.6; n1 = np.floor(N / 0.6) * 0.6 + 256 * 0.6
            bb = (e0, n1 - 512 * 0.6, e0 + 512 * 0.6, n1)
            a = us.read(window=from_bounds(*bb, us.transform).round_offsets().round_lengths())
            href = items[tile]['assets']['image']['href']
            with rasterio.Env(CURL_CA_BUNDLE='/root/.ccr/ca-bundle.crt', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
                with rasterio.open('/vsicurl/' + href + '?' + tok) as ds:
                    b = ds.read(window=from_bounds(*bb, ds.transform).round_offsets().round_lengths())
            assert a.shape == b.shape, (a.shape, b.shape)
            d = np.abs(a.astype(int) - b.astype(int))
            # best integer offset within +-2 px (should be 0, 0)
            best = None
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    aa = a[:, 2 + dr:510 + dr, 2 + dc:510 + dc].astype(int); bbb = b[:, 2:510, 2:510].astype(int)
                    m = float(np.abs(aa - bbb).mean())
                    if best is None or m < best[0]: best = (m, dr, dc)
            out['windows'][name] = dict(pc_item=tile, pc_href=href, bbox_utm=list(map(float, bb)), shape=list(a.shape),
                                        identical_fraction=float((d == 0).all(0).mean()),
                                        mean_abs_dn=[float(d[k].mean()) for k in range(4)], max_abs_dn=int(d.max()),
                                        best_integer_offset_px=dict(rows=best[1], cols=best[2], mean_abs_dn=best[0]))
            print(name, out['windows'][name]['identical_fraction'], out['windows'][name]['mean_abs_dn'], 'best offset', best)
    json.dump(out, open(os.path.join(CACHE, 'naip_grid_check.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
