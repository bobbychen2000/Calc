"""Building drawing set (2-D, drawn to the verified dimensions of tools/buildings/spec_*.json) - the owner's
"drawings first" step before the 3-D buildings are rebuilt.

  python3 tools/buildings/draw.py              # all sheets + overlays (overlays need refs/cache/naip/, ~1-2 min)
  python3 tools/buildings/draw.py BT BI        # only sheets whose id starts with BT / BI
  python3 tools/buildings/draw.py --no-naip    # vector sheets only

Writes
  docs/drawings/buildings/<id>.svg / .png   vector sheets, no imagery pixels (committable)
  docs/drawings/buildings/deviations.json   measured deviations vs NAIP 2024 (numbers only)
  docs/drawings/buildings/index.json        sheet list (id, title, paper, scales, files)
  out/buildings/drawings/<id>_naip.jpg      the plan sheets over NAIP 2024 with deviation dots (local; NAIP is public
                                            domain but the owner keeps imagery overlays out of the repo)
Sheets: BT-01..03 control tower, BI-01..03 international terminal, BD-01..02 domestic terminals, BL-01..03 landside,
BX-01 current 3-D app vs spec. Engine: draw_lib.py; inputs: draw_data.py; deviations: draw_measure.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw_lib import DOCS, ROOT, naip_available  # noqa: E402


def main(argv):
    only = [a for a in argv if not a.startswith('--')]
    naip = '--no-naip' not in argv and naip_available()
    import draw_measure, draw_tower, draw_itb, draw_domestic, draw_landside, draw_compare
    dev = draw_measure.run() if naip else json.load(open(os.path.join(DOCS, 'deviations.json')))
    jobs = [('BT-01', lambda: draw_tower.sheet_plan()), ('BT-02', draw_tower.sheet_elev), ('BT-03', draw_tower.sheet_section),
            ('BI-01', lambda: draw_itb.sheet_plan()), ('BI-02', draw_itb.sheet_elev), ('BI-03', draw_itb.sheet_section),
            ('BD-01', lambda: draw_domestic.sheet_plan()), ('BD-02', draw_domestic.sheet_elev),
            ('BL-01', draw_landside.sheet_key), ('BL-02', lambda: draw_landside.sheet_roofs()), ('BL-03', draw_landside.sheet_elev),
            ('BX-01', draw_compare.sheet)]
    if naip:
        jobs += [('BT-01n', lambda: draw_tower.sheet_plan('naip', dev)), ('BI-01n', lambda: draw_itb.sheet_plan('naip', dev)),
                 ('BD-01n', lambda: draw_domestic.sheet_plan('naip', dev)), ('BL-02n', lambda: draw_landside.sheet_roofs('naip', dev))]
    idx_path = os.path.join(DOCS, 'index.json')
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    for sid, fn in jobs:
        if only and not any(sid.startswith(o) for o in only): continue
        files = fn()
        index[sid] = [os.path.relpath(f, ROOT) for f in files]
        print(sid, ', '.join(index[sid]))
    json.dump(dict(sorted(index.items())), open(idx_path, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
