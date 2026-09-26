"""International Terminal (ITB) - roof silhouette read from a public-domain reference photograph (research aid for
tools/buildings/spec_itb.json). Numbers only are written (tools/buildings/itb_photo_skyline.json); the photo stays in
refs/cache/buildings/itb/photos/ (reference only, never a texture).

Photo: Wikimedia Commons "File:San Francisco International.jpg" by DimiCalifornia, July 2005, licence: Public domain
(https://commons.wikimedia.org/wiki/File:San_Francisco_International.jpg), 1920 px thumbnail of the 2028 x 1029
original, cached as refs/cache/buildings/itb/photos/1975704.jpg. It looks east along the airport access road at the
landside (west) elevation from a distance of several hundred metres with a long lens, so the elevation is close to
frontal and nearly orthographic - but perspective and a small yaw are NOT modelled here: heights are read at one
average scale (tip-to-tip roof length from NAIP) and carry about +-1.5 m (left/right tip readings differ by 4 m,
which is the size of the residual perspective/yaw effect).

Method: sky = pixels with blue - red > 25 and blue > 150; per column the first non-sky pixel below the top of the
search window is the roof silhouette (top of roof edge / fascia or glazed crown). Output: silhouette y(x) every 5 px,
the extrema (tips, humps, notches, crown) and their drops below the hump tops in metres.
Usage: python3 tools/buildings/itb_photo_skyline.py
"""
import json, os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PHOTO = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'itb', 'photos', '1975704.jpg')
MEAS = os.path.join(HERE, 'itb_naip_measurements.json')
OUT = os.path.join(HERE, 'itb_photo_skyline.json')
X0, X1, Y0, Y1 = 60, 1790, 250, 420            # search window (px) around the roof (by eye on the thumbnail)
TIP_L, TIP_R = 75, 1772                          # roof tips (px, by eye: outermost fascia pixels)


def main():
    im = cv2.imread(PHOTO).astype(float); B, R = im[..., 0], im[..., 2]
    sky = (B - R > 25) & (B > 150)
    xs, ys = [], []
    for x in range(X0, X1, 5):
        col = sky[Y0:Y1, x]; idx = np.where(~col)[0]; idx = idx[idx > 3]
        if len(idx): xs.append(x); ys.append(Y0 + int(idx[0]))
    xs, ys = np.array(xs), np.array(ys, float)
    # lamp posts / high masts standing in front of the roof line (x ranges read by eye on the thumbnail)
    posts = [(295, 325), (715, 735), (870, 900), (1570, 1605), (1615, 1645)]
    keep = np.array([not any(a <= x <= b for a, b in posts) for x in xs]); xs, ys = xs[keep], ys[keep]
    # remove lamp-post spikes (single columns far above their neighbours)
    med = np.array([np.median(ys[max(0, i - 3):i + 4]) for i in range(len(ys))]); ok = np.abs(ys - med) < 6
    xs, ys = xs[ok], ys[ok]
    # lamp posts in front of the roof (up to ~10 px wide) survive the spike test; a 45 px running median removes them
    ys = np.array([np.median(ys[max(0, i - 4):i + 5]) for i in range(len(ys))])
    L_naip = json.load(open(MEAS))['true_planform']['length_m']
    s = (TIP_R - TIP_L) / L_naip                 # px per metre at the facade (average)
    xc = 0.5 * (TIP_L + TIP_R)
    def pick(a, b, fn):
        m = (xs >= a) & (xs <= b); i = fn(ys[m]); return float(xs[m][i]), float(ys[m][i])
    humpL = pick(400, 650, np.argmin); humpR = pick(1380, 1650, np.argmin)
    notchL = pick(700, 900, np.argmax); notchR = pick(1150, 1330, np.argmax); crown = pick(930, 1110, np.argmin)
    tipL = (float(xs[0]), float(ys[0])); tipR = (float(xs[-1]), float(ys[-1]))
    ref = 0.5 * (humpL[1] + humpR[1])
    feat = {nm: dict(x_px=p[0], y_px=p[1], u_m=round((p[0] - xc) / s, 1), drop_below_hump_mean_m=round((p[1] - ref) / s, 2))
            for nm, p in dict(tip_north=tipL, hump_north=humpL, notch_north=notchL, crown=crown, notch_south=notchR,
                              hump_south=humpR, tip_south=tipR).items()}
    res = dict(photo='Wikimedia Commons File:San_Francisco_International.jpg (DimiCalifornia, 2005-07, Public domain)',
               cache='refs/cache/buildings/itb/photos/1975704.jpg', scale_px_per_m=round(s, 3),
               scale_from='NAIP relief-corrected roof length %.2f m (tools/buildings/itb_naip_measurements.json)' % L_naip,
               note='left of the photo = north (the camera looks east). Perspective/yaw NOT modelled: the crown is 97 px right of the tip midpoint and the two tips read 1-12 m apart, so single readings are qualitative; the north/south MEAN of each feature pair is the usable number (+-2 m)',
               pair_means_drop_m={k: round(0.5 * (feat[k + '_north']['drop_below_hump_mean_m'] + feat[k + '_south']['drop_below_hump_mean_m']), 2) for k in ('tip', 'notch')},
               features=feat, silhouette=[[int(a), int(b)] for a, b in zip(xs, ys)])
    json.dump(res, open(OUT, 'w'), indent=1)
    for k, v in feat.items(): print('%-12s u=%7.1f m  drop=%5.2f m' % (k, v['u_m'], v['drop_below_hump_mean_m']))


if __name__ == '__main__':
    main()
