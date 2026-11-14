"""B3: T1 roof heights from one Commons photo by ratio to the east control tower.

Photo: File:202309 Terminal 1 of Shanghai Hongqiao Airport.jpg (MNXANL, CC BY-SA 4.0), 1920 px rendition, taken from an
aircraft on RWY 18L/36R looking east. Rows were read on a 3x zoom with a 10 px grid (tools: PIL crop), in the 1920 px image:
  apron line at the building bases 704; tower cab roof 579; T1 central hall roof edge (under the sign) 639;
  airside concourse roof 677.  Reading error about +-2 px.
Angular height = H / d (small angles; the camera height cancels between base and top). With the tower at 44.5 m
(AIP mirror elevation 47 m - ground 2.5 m, A1): H = 44.5 * (px / 125) * (d / d_tower). Distances from OSM / frame:
tower 500 m (camera abeam on the runway axis), hall roof front x ~ 560 m east at 11 deg to the right -> 570 m,
concourse airside face x ~ 465 m. Check: with an iPhone 1x lens (69.4 deg hfov -> f = 1386 px at 1920 px) the tower's
125 px give 44.5 / (125 / 1386) = 494 m, close to the expected 500 m.
usage: python3 -I sha3d/tools/photos/t1_photo_ratio.py
"""
import math
ground, tower_top, hall, conc = 704, 579, 639, 677
pt = ground - tower_top
f = 960 / math.tan(math.radians(69.4 / 2))
print(f'tower {pt} px -> distance {44.5 / (pt / f):.0f} m for 44.5 m (f = {f:.0f} px)')
for name, row, d in (('T1 central hall roof', hall, 570), ('T1 airside concourse roof', conc, 465)):
    p = ground - row
    H = 44.5 * p / pt * d / 500
    lo = 44.5 * (p - 2) / (pt + 2) * (d - 50) / 500; hi = 44.5 * (p + 2) / (pt - 2) * (d + 50) / 500
    print(f'{name}: {p} px at {d} m -> {H:.1f} m (range {lo:.1f}-{hi:.1f} for +-2 px, +-50 m)')
