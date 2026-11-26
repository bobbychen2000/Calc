"""Classical structure-from-motion over the exterior video frames + listing photos (COLMAP, CPU).

    python3 -I house/tools/sfm.py prepare        # copy / mask the chosen images into refs/cache/sfm/images
    python3 -I house/tools/sfm.py features       # SIFT (affine shape + domain-size pooling)
    python3 -I house/tools/sfm.py match          # exhaustive matching + geometric verification
    python3 -I house/tools/sfm.py map            # incremental mapping -> refs/cache/sfm/sparse/<k>
    python3 -I house/tools/sfm.py report         # registered images, focal lengths, point counts, pair matches

Every video shot is one folder = one camera (same lens through the shot); every photo is its own camera.
The burnt-in titles / watermark of the video are masked out of the feature extraction.
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, 'refs', 'cache')
SFM = os.path.join(CACHE, 'sfm')
IMG = os.path.join(SFM, 'images')
MASK = os.path.join(SFM, 'masks')
DB = os.path.join(SFM, 'database.db')

# shot -> (frame prefix, first, last, step, [mask rectangles as fractions x0, y0, x1, y1])
WATERMARK = (0.0, 0.84, 0.17, 1.0)
SHOTS = {
    'v1_drone_front_high': ('seg002', 15, 31, 2, [(0.18, 0.42, 0.68, 0.64)]),
    'v2_drone_front_low': ('seg002', 33, 53, 2, [(0.0, 0.62, 0.52, 1.0)]),
    'v3_pergola': ('seg022', 7, 23, 4, [WATERMARK]),
    'v4_pool_cabana': ('seg123', 21, 35, 2, [WATERMARK]),
    'v5_cabana_house': ('seg123', 37, 61, 3, [WATERMARK]),
    'v6_pool_house': ('seg141', 7, 25, 2, [WATERMARK]),
    'v7_drone_front_right': ('seg141', 31, 49, 2, [WATERMARK]),
    'v8_drone_far': ('seg141', 57, 77, 5, [WATERMARK]),
}
PHOTOS = {
    'p30_top': 'p30_b7b282.jpg', 'p01_front_dusk': 'p01_57ca6a.jpg', 'p02_porch': 'p02_1ea535.jpg',
    'p25_pergola': 'p25_0c0464.jpg', 'p26_rear': 'p26_08c1ce.jpg', 'p27_cabana': 'p27_a7bd4e.jpg',
}


def prepare():
    for d in (IMG, MASK):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    n = 0
    for shot, (pref, a, b, step, rects) in SHOTS.items():
        os.makedirs(os.path.join(IMG, shot))
        os.makedirs(os.path.join(MASK, shot))
        for k in range(a, b + 1, step):
            name = '%s_%03d.jpg' % (pref, k)
            src = os.path.join(CACHE, 'frames', name)
            shutil.copy(src, os.path.join(IMG, shot, name))
            w, h = Image.open(src).size
            m = np.full((h, w), 255, np.uint8)
            for x0, y0, x1, y1 in rects:
                m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 0
            Image.fromarray(m).save(os.path.join(MASK, shot, name + '.png'))
            n += 1
    for folder, name in PHOTOS.items():
        os.makedirs(os.path.join(IMG, folder))
        shutil.copy(os.path.join(CACHE, 'photos', name), os.path.join(IMG, folder, name))
        n += 1
    print('prepared', n, 'images in', IMG)


def features():
    import pycolmap
    if os.path.exists(DB):
        os.remove(DB)
    ro = pycolmap.ImageReaderOptions()
    ro.mask_path = MASK
    ro.camera_model = 'SIMPLE_RADIAL'
    eo = pycolmap.FeatureExtractionOptions()
    eo.max_image_size = 2560
    eo.sift.max_num_features = 12000
    eo.sift.estimate_affine_shape = True
    eo.sift.domain_size_pooling = True
    pycolmap.extract_features(DB, IMG, camera_mode=pycolmap.CameraMode.PER_FOLDER, reader_options=ro,
                              extraction_options=eo, device=pycolmap.Device.cpu)
    print('features done')


def match():
    import pycolmap
    mo = pycolmap.FeatureMatchingOptions()
    mo.num_threads = 3
    mo.max_num_matches = 16384
    po = pycolmap.ExhaustivePairingOptions()
    po.block_size = 8          # the CPU matcher holds a search index per image of a block: 50 ran out of memory
    pycolmap.match_exhaustive(DB, matching_options=mo, pairing_options=po, device=pycolmap.Device.cpu)
    print('matching done')


def mapping():
    import pycolmap
    out = os.path.join(SFM, 'sparse')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    po = pycolmap.IncrementalPipelineOptions()
    po.min_num_matches = 12
    po.multiple_models = True
    po.min_model_size = 3
    recs = pycolmap.incremental_mapping(DB, IMG, out, options=po)
    for k, r in recs.items():
        print('model', k, r.summary())


def report():
    import pycolmap
    import sqlite3
    out = os.path.join(SFM, 'sparse')
    for k in sorted(os.listdir(out)):
        r = pycolmap.Reconstruction(os.path.join(out, k))
        print('== model', k, ':', r.num_reg_images(), 'images,', r.num_points3D(), 'points, mean reproj',
              round(r.compute_mean_reprojection_error(), 3))
        by = {}
        for im in r.images.values():
            by.setdefault(im.name.split('/')[0], []).append(im)
        for f in sorted(by):
            cam = r.cameras[by[f][0].camera_id]
            print('   %-22s %2d images  %s f=%.1f (w %d) params %s' % (
                f, len(by[f]), cam.model.name, cam.params[0], cam.width, np.round(cam.params[1:], 4).tolist()))
    con = sqlite3.connect(DB)
    names = dict(con.execute('select image_id, name from images'))
    rows = con.execute('select pair_id, rows from two_view_geometries where rows > 0').fetchall()
    agg = {}
    for pid, n in rows:
        i2 = pid % 2147483647
        i1 = (pid - i2) // 2147483647
        a, b = sorted((names[i1].split('/')[0], names[i2].split('/')[0]))
        if a != b:
            agg[(a, b)] = max(agg.get((a, b), 0), n)
    print('== best verified inlier matches between folders')
    for (a, b), n in sorted(agg.items(), key=lambda kv: -kv[1]):
        if n >= 15:
            print('   %-22s %-22s %d' % (a, b, n))


if __name__ == '__main__':
    {'prepare': prepare, 'features': features, 'match': match, 'map': mapping, 'report': report}[sys.argv[1]]()
