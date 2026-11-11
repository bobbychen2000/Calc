import json, sys
G, LT, B, N = '2026-11-09T00:30:00Z', '2026-11-09T00:48:00Z', '2026-11-09T01:32:00Z', '2026-11-09T03:30:00Z'
FOG = 'METAR KSFO 082056Z 27006KT 3/4SM BR OVC004 13/12 A3010'; RAIN = 'METAR KSFO 090156Z 18015G24KT 3SM RA BR BKN008 OVC015 13/12 A2985'
def orb(i, ch, tg, t, yaw, pitch, dist, off=0, fov=48, ty=None, metar=None): return dict(id=i, ch=ch, kind='orbit', target=tg, t=t, yaw=yaw, pitch=pitch, dist=dist, off=off, fov=fov, ty=ty, metar=metar)
def ch(i, ch_, kind, t, off, yo, pitch, dist, fov=40): return dict(id=i, ch=ch_, kind='chase', wait=kind, t=t, off=off, yawOff=yo, pitch=pitch, dist=dist, fov=fov)
def gt(i, ch_, pre, t, off, heavy=False, metar=None): return dict(id=i, ch=ch_, kind='gate', gate=pre, heavy=heavy, t=t, off=off, metar=metar)
S = [
 orb('open_aerial', 0, 'hub', G, [205, 232], [26, 20], [2100, 1700]),
 orb('itb', 1, 'gates:A|G', G, [200, 232], [24, 19], [700, 540], 120),
 orb('t1', 1, 'gates:B|C', G, [170, 200], [24, 19], [650, 520], 240),
 orb('t2', 1, 'gates:D|E', LT, [300, 328], [24, 19], [650, 520], 360),
 orb('t3', 1, 'gates:F', LT, [320, 345], [24, 19], [650, 520], 480),
 orb('tower_close', 1, 'tower', LT, [198, 238], [3, 8], [150, 115], 600, 42, 44),
 orb('bay_gold', 1, 'hub', G, [104, 116], [9, 7], [2600, 2300], 720, 45),
 ch('arr1', 2, 'arrival', G, 40, [78, 112], [3, 6], [95, 82]),
 ch('arr2', 2, 'arrival', None, 160, [250, 280], [4, 7], [110, 90]),
 ch('arr3', 2, 'arrival', G, 300, [150, 175], [5, 8], [120, 100]),
 ch('arr4', 2, 'arrival', LT, 430, [60, 95], [2, 5], [90, 80]),
 ch('arr5', 2, 'arrival', None, 720, [100, 130], [6, 4], [140, 100]),
 ch('arr6', 2, 'arrival', G, 900, [265, 300], [3, 6], [95, 85]),
 ch('arr7', 2, 'arrival', None, 1160, [90, 120], [4, 6], [100, 90]),
 ch('arr8', 2, 'arrival', G, 1400, [240, 270], [3, 6], [95, 85]),
 ch('taxi1', 3, 'taxi', G, 0, [140, 160], [9, 9], [85, 85]),
 gt('gateG', 3, 'G', G, 60, True),
 ch('taxi2', 3, 'taxi', None, 300, [200, 230], [8, 10], [90, 80]),
 gt('gateA', 3, 'A', LT, 180, True),
 gt('gateB', 3, 'B|C', G, 420),
 ch('taxi3', 3, 'taxi', LT, 600, [120, 90], [10, 7], [80, 95]),
 gt('gateD', 3, 'D|E', None, 540),
 gt('gateF', 3, 'F', G, 780),
 ch('taxi4', 3, 'taxi', G, 900, [165, 190], [6, 9], [100, 85]),
 gt('gateC', 3, 'C', None, 1300),
 ch('taxi5', 3, 'taxi', None, 1200, [150, 170], [8, 8], [90, 90]),
 gt('gateE', 3, 'E', G, 1700),
 ch('taxi6', 3, 'taxi', G, 1500, [130, 100], [7, 9], [95, 85]),
 gt('gate2G', 3, 'G', LT, 1000),
 ch('dep1', 4, 'takeoff', LT, 0, [105, 150], [4, 7], [105, 135]),
 ch('dep2', 4, 'takeoff', G, 400, [250, 215], [5, 8], [110, 140]),
 ch('dep3', 4, 'takeoff', None, 800, [160, 180], [6, 10], [100, 150]),
 ch('dep4', 4, 'takeoff', LT, 1200, [80, 120], [3, 7], [100, 130]),
 ch('dep5', 4, 'takeoff', G, 1600, [120, 165], [5, 9], [110, 150]),
 ch('dep6', 4, 'takeoff', None, 2000, [100, 140], [4, 8], [105, 140]),
 orb('tower_high', 5, 'tower', G, [250, 290], [18, 12], [260, 210], 200, 48, 40),
 orb('itb_low', 5, 'gates:A|G', LT, [235, 255], [8, 6], [380, 320], 500, 45, 20),
 orb('hub_garage', 5, 'hub', None, [150, 190], [35, 30], [900, 760], 800),
 orb('t2_low', 5, 'gates:D|E', G, [80, 110], [10, 8], [420, 360], 1100, 48, 15),
 orb('itb_g2', 5, 'gates:G', G, [300, 330], [20, 16], [500, 420], 1800, 48, 10),
 orb('t3_low', 5, 'gates:F', LT, [20, 50], [12, 9], [450, 380], 2100, 48, 15),
 orb('tod_noon', 6, 'hub', None, [210, 220], [24, 24], [1500, 1500], 0),
 orb('tod_gold', 6, 'hub', G, [220, 230], [24, 24], [1500, 1500], 0),
 orb('tod_blue', 6, 'hub', B, [230, 240], [24, 24], [1500, 1500], 0),
 orb('tod_night', 6, 'hub', N, [240, 250], [24, 24], [1500, 1500], 0),
 orb('fog_itb', 6, 'gates:A|G', None, [215, 235], [14, 11], [380, 300], 300, 48, None, FOG),
 gt('rain_gate', 6, 'G', B, 900, True, RAIN),
 ch('night_arr', 7, 'arrival', B, 160, [80, 110], [3, 6], [95, 85]),
 gt('blue_gate', 7, 'B|C', B, 1500),
 ch('night_taxi', 7, 'taxi', B, 300, [140, 160], [9, 9], [85, 85]),
 orb('night_tower', 7, 'tower', N, [200, 236], [3, 8], [160, 120], 900, 42, 44),
 orb('night_itb', 7, 'gates:A|G', N, [210, 232], [26, 20], [800, 620], 600),
 dict(orb('night_rw', 7, 'rw28t', N, [128, 112], [12, 10], [340, 280], 1200, 45), expo=1.8),
 orb('close_blue', 8, 'hub', B, [230, 250], [22, 30], [1500, 2400], 0, 50),
]
for s in S: s.setdefault('n', 168)
# chase shots: 'high' tier (all effects on; 2048 shadow map, 1.8 km LOD): the real-time event wait at ultra fills the
# software-GL GPU process before capture starts (OOM at the session's memory cap)
for s in S:
    if s['kind'] == 'chase': s['q'] = 'high'
json.dump(S, open(sys.argv[1], 'w'), indent=0); print(len(S), 'shots'); print(sorted({s['off'] for s in S}))
