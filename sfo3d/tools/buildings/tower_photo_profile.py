"""SFO ATCT - side-profile ratios from licensed reference photos (Wikimedia Commons), reproducible.

Photos are REFERENCE ONLY (CC BY-SA / CC0, author + licence in tools/buildings/spec_tower.json 'photos'); the pixels stay
in refs/cache/buildings/tower/photos/ (gitignored). Only ratios / derived numbers leave this script.

1) 'SFO - New Control Tower & A380.jpg' (Basil D Soufi, CC BY-SA 4.0, 2015-05-08): telephoto from ~1.75 km at bearing
   142 deg (camera SE of the tower) -> near-orthographic silhouette (vertical angles < 2.5 deg). Per image row: Sobel-x
   maxima in the left / right half of a fixed crop give the silhouette width. The landside fin faces ~300-320 deg, i.e.
   almost directly away from this camera, so the widths are those of the round airside body.
   Crop: preview-pixel window x 510..750, y 60..560 of a 1200-px-wide preview (= full-res origin col 1632, row 192).
   Roof rim (top of the cab-roof cap) at crop row 125; cab-roof width 405 px (rows 150-160).
2) '2025-08-12 11 57 15 The control tower ...' (Famartin, CC BY-SA 4.0): 263 m at bearing 126 deg. Manual pixel
   readings (crop origin col 491, row 171 of the 1920x2560 file, see the constants below) give the cab glass slope and a
   metric scale from the published 11-ft glass panel height (ENR 2016).

Scale: d_cab_roof = 14.3 m (spec value; from 2) and the Google/NAIP top-view fits). Anchor: roof rim = 221 ft = 67.36 m
(published height, definition assumed). Output: printed tables (copy into spec_tower.json by hand when re-measured).
usage: python3 tools/buildings/tower_photo_profile.py
"""
import math, os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PH = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'tower', 'photos')
FT = 0.3048
H_RIM = 221 * FT          # published height (FAA 2016), assumed = roof rim
D_ROOF = 14.3             # spec d_cab_roof

# --- 2) Famartin 11:57 manual readings (crop pixels; crop = full-res [171:2049, 491:1323]) --------------------------
F = dict(rim_y=127, roof_w=480, glass_top_y=220, glass_top_w=413, glass_bot_y=325, glass_bot_w=335,
         flare_w=748, waist_w=343, base_w=354, ibf_roof_y=1830, seam1_y=905, seam2_y=1395, mast_top_y=28)


def famartin():
    rad = (F['glass_top_w'] - F['glass_bot_w']) / 2; vert = F['glass_bot_y'] - F['glass_top_y']
    slope = math.degrees(math.atan2(rad, vert))
    mpp = 11 * FT * math.cos(math.radians(slope)) / vert          # 11-ft panel (ENR) seen at its slope
    print(f'Famartin 11:57: glass slope {slope:.1f} deg, vertical glass {vert} px -> {mpp:.4f} m/px')
    for k in ('roof_w', 'glass_top_w', 'glass_bot_w', 'flare_w'):
        print(f'  {k:12s} {F[k]:4d} px = {F[k] * mpp:6.2f} m')
    dist_top, dist_low = math.hypot(263, 60), math.hypot(263, 18)     # perspective: width scale ~ 1/distance
    for k in ('waist_w', 'base_w'):
        print(f'  {k:12s} {F[k]:4d} px = {F[k] * mpp * dist_low / dist_top:6.2f} m (distance-corrected)')
    print(f'  masts above rim: {(F["rim_y"] - F["mast_top_y"]) * mpp:.2f} m;  seam ratio (s1-rim)/(s2-rim) = '
          f'{(F["seam1_y"] - F["rim_y"]) / (F["seam2_y"] - F["rim_y"]):.3f}')


def a380():
    im = cv2.imread(os.path.join(PH, 'SFO_-_New_Control_Tower_A380.jpg'))
    s = im.shape[1] / 1200
    c = im[int(60 * s):int(60 * s) + 1600, int(510 * s):int(510 * s) + 768]
    g = cv2.GaussianBlur(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
    gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5))
    rim, w_roof = 125, 405.0; mpp = D_ROOF / w_roof
    print(f'A380 photo: {mpp:.4f} m/px (cab roof {D_ROOF} m = {w_roof:.0f} px); rows: m below rim, width/roof, h AGL, r')
    rows = [150, 350] + list(range(400, 1041, 50)) + list(range(1100, 1421, 40))
    for y in rows:
        if y < 1050: L = int(np.argmax(gx[y, 20:384])) + 20; R = int(np.argmax(gx[y, 384:760])) + 384
        else: L = int(np.argmax(gx[y, 200:262])) + 200; R = int(np.argmax(gx[y, 470:540])) + 470   # avoid light poles
        b = (y - rim) * mpp
        print(f'  {b:5.1f} {(R - L) / w_roof:6.3f} {H_RIM - b:5.1f} {(R - L) * mpp / 2:6.2f}')
    for name, y in (('mast tips', 30), ('glass top', 200), ('glass bottom', 282), ('sill band bottom', 305),
                    ('flare max', 350), ('slots top', 425), ('slots bottom', 640), ('seam 1', 778), ('seam 2', 1197)):
        print(f'  {name:16s} row {y:4d}: {(rim - y) * mpp:+6.2f} m from rim -> {H_RIM + (rim - y) * mpp:5.1f} m AGL')


if __name__ == '__main__':
    famartin()
    a380()
