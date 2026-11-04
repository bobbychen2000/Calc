"""Boarding Area B (Harvey Milk T1) roof features on NAIP 2024 for drawing BD-01 [obs], reproducible.

Read by eye on the NAIP 2024 world raster (refs/cache/naip/naip_2024_world_0.5m.png, public domain) on 10-m-grid crops
(4 px/m), 2026-11-04: the three planted roof wells, their two bridges, the two skylight grids (+-3 m) and the extents of
the three PV row fields (+-4 m; rows parallel to the pier axis, spec bab.pv_layout). The round-2 reviewer's boxes agree
within ~3 m. (An automatic dark-pixel segmentation was tried and rejected: shadows along the WNW wall and the jet-bridge
roofs read as dark as the PV rows on this bright raster.)
Everything is AS IMAGED: the sheets move it back by the relief of the outer roof (bab.h_roof 13.1 m x the pier's
two-epoch east lean, draw_data.dom_lean('B'), ~5.1 m) [inf: features taken at the outer-roof level].
usage: python3 tools/buildings/dom_bab_roof.py      -> tools/buildings/dom_bab_roof.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# by eye, imaged world (x, z), +-3 m [obs]
MANUAL = {
    'wells': [   # planted sunken roof courtyards on the WNW side, north to south
        [(-843.0, 627.0), (-826.0, 627.0), (-829.0, 678.0), (-845.0, 676.0)],
        [(-861.0, 686.0), (-844.0, 689.0), (-866.0, 762.0), (-885.0, 758.0)],
        [(-918.0, 772.0), (-897.0, 775.0), (-907.0, 812.0), (-926.0, 810.0)],
    ],
    'bridges': [  # bright bands crossing the wells' line (WNW -> ESE), ~7 m wide
        [(-869.0, 667.0), (-834.0, 680.0), (-836.0, 687.0), (-871.0, 674.0)],
        [(-919.0, 754.0), (-884.0, 767.0), (-886.0, 774.0), (-921.0, 761.0)],
    ],
    'pv_fields': [  # extent of the PV row fields (rows parallel to the pier axis, spec bab.pv_layout), +-4 m
        [(-832.0, 543.0), (-803.0, 535.0), (-770.0, 631.0), (-800.0, 647.0)],
        [(-800.0, 660.0), (-786.0, 668.0), (-846.0, 790.0), (-862.0, 781.0)],
        [(-957.0, 823.0), (-900.0, 813.0), (-877.0, 827.0), (-917.0, 903.0), (-957.0, 887.0)],
    ],
    'skylight_grids': [
        [(-828.0, 690.0), (-805.0, 690.0), (-803.0, 717.0), (-826.0, 717.0)],
        [(-880.0, 800.0), (-861.0, 800.0), (-860.0, 820.0), (-879.0, 820.0)],
    ],
}


def main():
    rec = dict(source='NAIP 2024 (2024-05-20) world raster 0.5 m, public domain (USDA FPAC-BC GEO)', frame='ltp-nad83-2011 world (x east, z south)',
               note='AS IMAGED (relief not removed); read by eye on 10-m-grid crops, +-3 m (PV field extents +-4 m)', manual=MANUAL)
    json.dump(rec, open(os.path.join(HERE, 'dom_bab_roof.json'), 'w'), indent=1)
    print({k: len(v) for k, v in MANUAL.items()})


if __name__ == '__main__':
    main()
