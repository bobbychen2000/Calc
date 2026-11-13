# Shot list of the two tracking films (recording 8 Nov 2026 20:45:58.662Z + start s; data/replay.wasm of the Full build):
#   arrival   UAL900 B789 N71112 (a9825a) LHR-SFO: 28R approach over the bay, touchdown ~T 980, taxi, holds, pull-in ~T 1740
#   departure UAL857 B77W N2639U (a28dc8) SFO-PVG: push ~T 222, engine start, taxi, line-up 28R ~T 1744, lift-off ~T 1850
# Times from the ADS-B track (see the session notes); speed = recorded seconds per video second (time-lapse, shown on screen).
# Lighting: ?t= freezes the Sun per shot; t follows the recording time from a late-afternoon base (as the 6-min video).
import datetime as dt, json, math, sys
FPS = 24
THR = (1532.7, 542.3); DIR = (-0.885, -0.466); LEFT = (DIR[1], -DIR[0])   # 28R threshold, runway direction, left (south)
GY = 3.0
def rw(along, lat, h): return [round(THR[0] + DIR[0] * along + LEFT[0] * lat, 1), round(GY + h, 1), round(THR[1] + DIR[1] * along + LEFT[1] * lat, 1)]
BASE = {'arr': (dt.datetime(2026, 11, 8, 23, 45, 0), 780), 'dep': (dt.datetime(2026, 11, 8, 23, 30, 0), 222)}
HEX = {'arr': 'a9825a', 'dep': 'a28dc8'}
S = []
def shot(id, film, start, secs, speed, cam, q='high', cap=None):
    b, t0 = BASE[film]; t = (b + dt.timedelta(seconds=start - t0)).strftime('%Y-%m-%dT%H:%M:%SZ')
    off = max(0, int((start - 200) // 10 * 10))
    S.append(dict(id=id, film=film, hex=HEX[film], start=start, n=int(round(secs * FPS)), speed=speed, off=off, t=t, q=q, cam=cam, cap=cap))
# ---------------- arrival: UAL900
shot('a_bay', 'arr', 800, 9, 1, dict(type='chase', yawOff=[-50, -68], pitch=[7, 4], dist=[160, 135], fov=40), cap='approach')
shot('a_side', 'arr', 872, 8, 1, dict(type='chase', yawOff=[-78, -96], pitch=[4, 2], dist=[150, 115], fov=40), cap='approach')
shot('a_lights', 'arr', 951, 14, 1, dict(type='spot', pos=rw(-900, 75, 14), frame=[60, 75], up=0), cap='final')
shot('a_td', 'arr', 969, 16, 1, dict(type='spot', pos=rw(560, 120, 1.8), frame=[55, 80], up=0), cap='touchdown')
shot('a_roll', 'arr', 988, 11, 2, dict(type='chase', yawOff=[-35, -20], pitch=[4, 6], dist=[105, 115], fov=42), cap='rollout')
shot('a_exit', 'arr', 1012, 15, 3, dict(type='chase', yawOff=[35, 70], pitch=[12, 16], dist=[125, 145], fov=42), cap='taxi')
shot('a_taxi', 'arr', 1058, 14.5, 6, dict(type='chase', yawOff=[160, 205], pitch=[28, 22], dist=[210, 175], fov=45), cap='taxi')
shot('a_taxi2', 'arr', 1336, 18, 8, dict(type='orbit', yaw=[120, 200], pitch=[22, 27], dist=[240, 190], fov=45), cap='taxi')
shot('a_pull1', 'arr', 1622, 15, 4, dict(type='orbit', yaw=[300, 250], pitch=[26, 20], dist=[170, 135], fov=45), cap='gate')
shot('a_pull2', 'arr', 1682, 15, 4, dict(type='orbit', yaw=[210, 180], pitch=[16, 13], dist=[120, 100], fov=45), cap='gate')
shot('a_dock1', 'arr', 1742, 15, 3, dict(type='orbit', yaw=[160, 135], pitch=[14, 12], dist=[85, 72], fov=45, up=4), cap='gate')
shot('a_dock2', 'arr', 1787, 15, 3, dict(type='orbit', yaw=[250, 285], pitch=[30, 24], dist=[150, 130], fov=45), cap='dock')
# ---------------- departure: UAL857
shot('d_gate', 'dep', 200, 13, 2, dict(type='orbit', yaw=[200, 235], pitch=[22, 17], dist=[170, 140], fov=45), cap='gate')
shot('d_push1', 'dep', 214, 18, 5, dict(type='orbit', yaw=[60, 20], pitch=[24, 18], dist=[170, 150], fov=45), cap='pushstart')
shot('d_push2', 'dep', 304, 18, 5, dict(type='orbit', yaw=[300, 330], pitch=[12, 10], dist=[130, 115], fov=45), cap='push')
shot('d_away', 'dep', 642, 15, 3, dict(type='chase', yawOff=[30, 55], pitch=[6, 9], dist=[115, 125], fov=42), cap='taxi')
shot('d_taxi1', 'dep', 758, 20, 12, dict(type='chase', yawOff=[165, 200], pitch=[30, 24], dist=[230, 190], fov=45), cap='taxi')
shot('d_taxi2', 'dep', 1000, 18, 12, dict(type='orbit', yaw=[30, 100], pitch=[24, 28], dist=[260, 210], fov=45), cap='taxi')
shot('d_taxi3', 'dep', 1400, 20, 8, dict(type='chase', yawOff=[-95, -80], pitch=[8, 10], dist=[170, 150], fov=42), cap='taxi')
shot('d_lineup', 'dep', 1740, 22, 2.5, dict(type='spot', pos=rw(420, 115, 4.5), frame=[75, 62], up=0), cap='lineup')
shot('d_roll', 'dep', 1804, 20, 1, dict(type='chase', yawOff=[190, 176], pitch=[2.5, 4], dist=[85, 100], fov=42), cap='takeoff')
shot('d_rotate', 'dep', 1836, 20, 1, dict(type='spot', pos=rw(2750, 150, 1.8), frame=[60, 110], up=0), cap='takeoff')
shot('d_climb', 'dep', 1857, 16, 1, dict(type='chase', yawOff=[200, 168], pitch=[11, 15], dist=[175, 270], fov=42, up=0), cap='climb')
json.dump(S, open(sys.argv[1], 'w'), indent=1)
tot = {f: sum(s['n'] for s in S if s['film'] == f) for f in ('arr', 'dep')}
print(len(S), 'shots', tot, 'frames;', {f: round(v / FPS, 1) for f, v in tot.items()}, 's;', 'offsets', sorted({s['off'] for s in S}))
