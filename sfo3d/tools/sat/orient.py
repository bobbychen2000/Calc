from register import *
import sys
def dominant_theta(name, bottom=2200, th_hint=None):
    img, E, v = image_edges(name, bottom)
    L = cv2.HoughLinesP(E.astype(np.uint8) * 255, 1, np.pi / 720, threshold=80, minLineLength=150, maxLineGap=6)
    angs = []; w = []
    for l in L[:, 0]:
        x0, y0, x1, y1 = l; dx, dy = x1 - x0, y1 - y0; ln = math.hypot(dx, dy)
        a = math.degrees(math.atan2(dx, -dy)) % 90  # screen angle mod 90 (clockwise from up)
        angs.append(a); w.append(ln)
    angs = np.array(angs); w = np.array(w)
    hist = np.zeros(900)
    for a, ww in zip(angs, w): hist[int(a * 10) % 900] += ww
    hs = np.convolve(np.concatenate([hist, hist[:30]]), np.ones(7) / 7, 'same')[:900]
    a0 = np.argmax(hs) / 10
    # refine: weighted mean of angles within 1 deg
    d = ((angs - a0 + 45) % 90) - 45; m = abs(d) < 1.0
    a = a0 + np.average(d[m], weights=w[m])
    # world grid: pier edges heading 27.8 / 117.8 => screen angle = h + theta (mod 90) -> theta = a - 27.8 (mod 90)
    th = (a - 27.8) % 90
    if th_hint is not None:
        k = round((th_hint - th) / 90); th = th + 90 * k
    return a, th, len(L), float(w[m].sum())
if __name__ == '__main__':
    import json
    comp = json.load(open(SP + 'compass.json'))
    for n in sys.argv[1:]:
        print(n, dominant_theta(n, 2200, comp[n]['north_cw_deg']))
