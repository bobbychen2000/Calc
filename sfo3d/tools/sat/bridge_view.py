import json, sys
import numpy as np, cv2
from common import *
from mosaic2 import mosaic
from stview import annotate, st_px, w2st
from stands import draw_stands
import stand_defs
from export_stands_google_legacy import door_st
def bview(box, res, out):
    m, b = mosaic(box, res)
    m = annotate(m, *box, res, grid=10, lab=50, gates=False)
    S = {s['name']: s for s in stand_defs.STANDS}
    sts = [s for s in stand_defs.STANDS if box[0] - 80 < s['nose'][0] < box[2] + 80 and box[1] - 80 < s['nose'][1] < box[3] + 80]
    m = draw_stands(m, *box, res, sts, env=False)
    data = json.load(open(ROOT + '/data/sfo_stands.json'))
    for st in data['stands']:
        if st['name'] not in S: continue
        for br in st['bridges']:
            a = w2st(*br['attach']); d = door_st(S[st['name']], br['door'])
            pa = st_px(*a, box[0], box[3], res); pd = st_px(*d, box[0], box[3], res)
            cv2.line(m, pa, pd, (0, 140, 255), 3, cv2.LINE_AA); cv2.circle(m, pa, 5, (0, 255, 255), -1)
    cv2.imwrite(out, m)
if __name__ == '__main__':
    box = tuple(float(v) for v in sys.argv[1:5]); res = float(sys.argv[5]); bview(box, res, sys.argv[6])
