"""Measure the translation between two registered screenshots over a world box by phase correlation of their rectified views."""
import sys
import numpy as np, cv2
from common import *
from stview import st_view
def offset(a, b, box, res=0.5):
    A = cv2.cvtColor(st_view(a, *box, res), cv2.COLOR_BGR2GRAY).astype(np.float32)
    B = cv2.cvtColor(st_view(b, *box, res), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = (A > 0) & (B > 0)
    A = np.where(m, A - A[m].mean(), 0); B = np.where(m, B - B[m].mean(), 0)
    win = cv2.createHanningWindow(A.shape[::-1], cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(A * win, B * win)
    return dx * res, -dy * res, resp  # shift in (s, t) metres: B = A shifted by (ds, dt)
if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]; box = tuple(float(v) for v in sys.argv[3:7])
    print(a, b, 'shift (ds, dt) m and response:', offset(a, b, box))
