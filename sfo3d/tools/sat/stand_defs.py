"""Stand layout for SFO contact gates, measured from the user's satellite screenshots (georeferenced against the
SFO Museum building outlines). Coordinates are in the airport grid frame (s along hdg 117.83 deg, t along 27.83 deg).
obs = aircraft observed parked there in imagery; inf = inferred from pitch / bridge heads (stand empty in imagery).

FRAME: every number below was measured in the LEGACY frame 'equirect-v1' (tools/geo_frame.py; the pre-24-Sep-2026
js/geo.js equirectangular projection and its grid) and is kept exactly as measured. At the end of this file the list
is mapped exactly into the current world frame ('ltp-nad83-2011'): STANDS = current frame (grid s,t + true heading),
LEGACY_STANDS = the records as measured. Displacement 1.0-2.0 m, heading change <= 0.03 deg."""
H_S, H_T = 117.83, 27.83           # headings of +s and +t directions
H_mS, H_mT = 297.83, 207.83        # headings of -s and -t
def face(names, axis, face_c, along, nose_d, hdg, cls, src, img, alias=None):
    """stand on a straight face: axis 's' -> face is t=face_c, `along` is the s of the centreline"""
    if axis == 's':
        t = face_c + nose_d * (1 if hdg == H_mT else -1)
        nose = (along, t)
    else:
        s = face_c + nose_d * (1 if hdg == H_mS else -1)
        nose = (s, along)
    return {'name': names, 'nose': nose, 'hdg': hdg, 'cls': cls, 'src': src, 'img': img, 'alias': alias or []}
STANDS = []
# ---------------------------------------------------------------- Boarding Area G (151ec51d, 3.74 px/m)
GN, GS = -733.1, -771.4
STANDS += [
    face('G10', 's', GN, -1389.4, 10.9, H_mT, 'EL', 'obs', '151ec51d', ['G14']),
    face('G9',  's', GN, -1318.8, 10.5, H_mT, 'EL', 'inf', '151ec51d'),
    face('G6',  's', GN, -1248.1, 9.9, H_mT, 'EL', 'obs', '151ec51d'),
    face('G5',  's', GN, -1176.9, 10.5, H_mT, 'EL', 'obs', '151ec51d'),
    face('G2',  's', GN, -1106.4, 9.4, H_mT, 'EL', 'obs', '151ec51d'),
    face('G1',  's', GN, -1032.1, 10.5, H_mT, 'EL', 'obs', '151ec51d'),
    face('G7',  's', GS, -1258.0, 13.6, H_T, 'EL', 'obs', '151ec51d'),
    face('G4',  's', GS, -1186.0, 13.6, H_T, 'EL', 'obs', '151ec51d'),
    face('G3',  's', GS, -1114.0, 13.6, H_T, 'EL', 'inf', '151ec51d'),
    {'name': 'G12', 'nose': (-1408.0, -769.0), 'hdg': 156.3, 'cls': 'EL', 'src': 'obs', 'img': '151ec51d', 'alias': ['G11', 'G13']},
    {'name': 'G8', 'nose': (-1378.0, -799.0), 'hdg': 90.4, 'cls': 'E', 'src': 'obs', 'img': '151ec51d', 'alias': []},
]
# ---------------------------------------------------------------- Boarding Area A (d82848c4, 4.04 px/m)
AW, AE = -799.0, -760.3
STANDS += [
    face('A3',  't', AW, -1066.5, 13.5, H_S, 'EL', 'inf', 'd82848c4', ['A4']),
    face('A5',  't', AW, -1138.5, 11.0, H_S, 'EL', 'obs', 'd82848c4'),
    face('A9',  't', AW, -1210.5, 11.0, H_S, 'EL', 'obs', 'd82848c4'),
    face('A10', 't', AW, -1282.5, 11.0, H_S, 'EL', 'obs', 'd82848c4'),
    face('A1',  't', AE, -962.0, 14.0, H_mS, 'EL', 'inf', 'd82848c4'),
    face('A2',  't', AE, -1042.0, 14.0, H_mS, 'EL', 'inf', 'd82848c4'),
    face('A6',  't', AE, -1122.0, 14.0, H_mS, 'EL', 'obs', 'd82848c4', ['A7']),
    face('A8',  't', AE, -1202.0, 14.0, H_mS, 'EL', 'inf', 'd82848c4'),
    face('A11', 't', AE, -1282.5, 13.0, H_mS, 'EL', 'obs', 'd82848c4', ['A13']),
]
import math as _m
def vec_hdg(ds, dt): return (H_S - _m.degrees(_m.atan2(dt, ds))) % 360
def obs(name, nose, tail, cls, img, alias=None, src='obs'):
    return {'name': name, 'nose': nose, 'hdg': round(vec_hdg(nose[0] - tail[0], nose[1] - tail[1]), 2), 'cls': cls, 'src': src, 'img': img, 'alias': alias or []}
def st(name, nose, hdg, cls, img, alias=None, src='inf'):
    return {'name': name, 'nose': nose, 'hdg': hdg, 'cls': cls, 'src': src, 'img': img, 'alias': alias or []}
# A: tip stand (narrowbody observed docked at the A15 bridge) and A1 nose-in to the ITB south facade (inferred from the A1 bridge)
STANDS += [
    obs('A15', (-768.8, -1339.0), (-779.6, -1374.4), 'C', 'd82848c4', ['A12', 'A14']),
]
for s_ in STANDS:
    if s_['name'] == 'A1': s_.update({'nose': (-697.0, -958.0), 'hdg': H_T, 'cls': 'E', 'src': 'inf'})
    if s_['name'] == 'G1': s_.update({'cls': 'E'})
# ---------------------------------------------------------------- Boarding Area C (03dcd4ae, 6.08 px/m)
STANDS += [
    obs('C3', (-453.3, -634.3), (-448.0, -604.0), 'C', '03dcd4ae'),
    obs('C5', (-400.0, -635.75), (-398.5, -593.0), 'CL', '03dcd4ae'),
    obs('C7', (-358.0, -638.0), (-351.25, -595.25), 'CL', '03dcd4ae', ['C9']),
    obs('C11', (-325.75, -635.0), (-303.25, -604.25), 'C', '03dcd4ae'),
    st('C4', (-395.5, -716.0), 25.8, 'C', '03dcd4ae'),
    st('C6', (-347.5, -722.0), 18.9, 'C', '03dcd4ae'),
    st('C8', (-315.0, -720.0), 351.6, 'C', '03dcd4ae'),
    st('C10', (-300.0, -683.0), H_mS, 'C', '03dcd4ae'),
]
for s_ in STANDS:
    if s_['name'] == 'A1': s_.update({'nose': (-697.0, -966.0), 'hdg': H_T, 'cls': 'C', 'src': 'inf'})
    if s_['name'] == 'A2': s_.update({'nose': (-746.3, -1047.0)})
# ---------------------------------------------------------------- Boarding Area B (b1d51b0f, 3.54 px/m)
# east face: aircraft face west; L1 doors at the parked bridge cabs -> nose 5 m ahead, centreline 2 m north of the door
def b_east(name, door, alias=None):
    return st(name, (door[0] - 5.0, door[1] + 2.0), H_mS, 'C', 'b1d51b0f', alias)
STANDS += [
    b_east('B9', (-357, -959)), b_east('B12', (-357, -1002)), b_east('B13', (-357, -1044)), b_east('B14', (-360, -1090)),
    b_east('B17', (-356, -1128)), b_east('B18', (-357, -1168)), b_east('B21', (-363, -1210)),
    # west face pods: regional-jet stands (observed pair at the B10/B11 pod, same pattern inferred for the others)
    obs('B10', (-478.0, -1030.0), (-512.0, -1030.0), 'B', 'b1d51b0f'),
    obs('B11', (-466.0, -1068.0), (-504.0, -1068.0), 'B', 'b1d51b0f'),
    st('B15', (-470.0, -1126.0), H_S, 'B', 'b1d51b0f'),
    st('B16', (-470.0, -1164.0), H_S, 'B', 'b1d51b0f'),
    st('B19', (-470.0, -1217.0), H_S, 'B', 'b1d51b0f', ['B20']),
    # tip (observed)
    obs('B26', (-480.6, -1282.8), (-525.7, -1291.6), 'CL', 'b1d51b0f'),
    obs('B27', (-463.0, -1296.0), (-486.0, -1330.0), 'CL', 'b1d51b0f'),
    obs('B23', (-378.3, -1281.7), (-346.4, -1300.4), 'C', 'b1d51b0f', ['B22']),
    st('B25', (-421.0, -1292.0), H_T, 'C', 'b1d51b0f', ['B24']),
    # root: NE diagonal (observed narrowbody at the B6/B7 bridges), T1 south facade (regional-jet stands)
    obs('B6', (-366.0, -878.8), (-333.0, -856.8), 'C', 'b1d51b0f', ['B7']),
    st('B3', (-425.0, -845.0), 252.8, 'C', 'b1d51b0f'),
    st('B8', (-360.0, -912.0), 252.8, 'C', 'b1d51b0f'),
    st('B1', (-647.0, -940.0), H_T, 'B', 'b1d51b0f'),
    st('B2', (-611.0, -935.0), H_T, 'B', 'b1d51b0f'),
    st('B4', (-541.0, -947.0), H_T, 'B', 'b1d51b0f'),
    st('B5', (-505.0, -941.0), H_T, 'B', 'b1d51b0f'),
    st('C1', (-450.0, -800.0), H_mS, 'C', 'b1d51b0f'),
]
# ---------------------------------------------------------------- Boarding Area D (bf5c7afc, 4.19 px/m)
STANDS += [
    obs('D9', (-371.0, -319.0), (-346.0, -291.0), 'C', 'bf5c7afc'),
    obs('D8', (-334.0, -334.0), (-302.0, -318.0), 'C', 'bf5c7afc'),
    obs('D16', (-512.0, -410.0), (-540.0, -409.0), 'C', 'bf5c7afc'),
    obs('D5', (-320.0, -442.5), (-288.5, -467.0), 'C', 'bf5c7afc', ['D6']),
    obs('D1', (-449.5, -502.0), (-435.5, -526.5), 'C', 'bf5c7afc'),
    st('D10', (-396.0, -272.0), H_mT, 'C', 'bf5c7afc'),
    st('D11', (-432.0, -270.0), H_mT, 'C', 'bf5c7afc'),
    st('D12', (-465.0, -280.0), H_mT, 'C', 'bf5c7afc'),
    st('D14', (-485.0, -318.0), H_S, 'C', 'bf5c7afc'),
    st('D15', (-485.0, -350.0), H_S, 'C', 'bf5c7afc'),
    st('D3', (-395.0, -449.0), H_T, 'C', 'bf5c7afc'),
    st('D4', (-355.0, -451.0), H_T, 'C', 'bf5c7afc'),
    st('D2', (-441.0, -482.0), H_T, 'C', 'bf5c7afc'),
    st('D7', (-307.0, -391.0), H_mS, 'C', 'bf5c7afc'),
]
# ---- fixes after first check
_rm = {'B8', 'D2'}
STANDS = [s_ for s_ in STANDS if s_['name'] not in _rm]
for s_ in STANDS:
    if s_['name'] == 'B6': s_['alias'] = ['B7', 'B8']
    if s_['name'] == 'D1': s_['alias'] = ['D2']
    if s_['name'] == 'C1': s_['nose'] = (-450.0, -794.0)
    # D pier: splay neighbouring stands whose bridge heads are only ~32-36 m apart (tails swung apart)
    if s_['name'] == 'D10': s_.update({'hdg': 217.83})
    if s_['name'] == 'D11': s_.update({'hdg': 202.83, 'nose': (-433.0, -271.0)})
    if s_['name'] == 'D12': s_.update({'hdg': 187.83, 'nose': (-468.0, -281.0)})
    if s_['name'] == 'D14': s_.update({'hdg': 102.83, 'nose': (-487.0, -314.0)})
    if s_['name'] == 'D15': s_.update({'hdg': 132.83, 'nose': (-487.0, -352.0)})
    if s_['name'] == 'D3': s_.update({'hdg': 20.83})
    if s_['name'] == 'D4': s_.update({'hdg': 34.83})
# ---------------------------------------------------------------- Boarding Area E (c235f3b8, 4.23 px/m)
STANDS += [
    obs('E9', (-670.0, -300.0), (-631.0, -295.5), 'C', 'c235f3b8'),
    obs('E5', (-668.5, -391.5), (-634.0, -387.0), 'C', 'c235f3b8'),
    obs('E4', (-656.5, -436.5), (-622.0, -426.0), 'C', 'c235f3b8'),
    st('E7', (-670.0, -346.0), H_mS, 'C', 'c235f3b8'),
    st('E11', (-687.0, -268.0), H_mT, 'C', 'c235f3b8'),
    obs('E10', (-761.5, -310.5), (-799.0, -295.5), 'C', 'c235f3b8'),
    obs('E13', (-757.0, -270.0), (-787.0, -247.5), 'C', 'c235f3b8', ['E12']),
    st('E8', (-757.0, -345.0), H_S, 'C', 'c235f3b8'),
    st('E6', (-757.0, -402.0), H_S, 'C', 'c235f3b8'),
    st('E3', (-810.0, -428.0), H_mT, 'C', 'c235f3b8', ['E2']),
]
# ---------------------------------------------------------------- Boarding Area F (39176bb8, 3.65 px/m)
STANDS += [
    face('F22', 's', -368.1, -1277.5, 13.2, H_mT, 'E', 'obs', '39176bb8', ['F21']),
    face('F15', 's', -368.1, -1206.0, 20.0, H_mT, 'E', 'inf', '39176bb8'),
    face('F13', 's', -368.1, -1132.6, 25.8, H_mT, 'EL', 'obs', '39176bb8'),
    face('F11', 's', -368.1, -1062.4, 33.9, H_mT, 'E', 'obs', '39176bb8'),
    face('F17', 's', -406.7, -1220.3, 9.9, H_T, 'D', 'obs', '39176bb8', ['F18']),
    face('F16', 's', -406.7, -1164.0, 9.5, H_T, 'D', 'inf', '39176bb8'),
    face('F14', 's', -406.7, -1109.0, 9.5, H_T, 'D', 'inf', '39176bb8'),
    face('F12', 's', -406.7, -1054.0, 8.3, H_T, 'D', 'obs', '39176bb8'),
    obs('F19', (-1277.3, -412.8), (-1313.4, -466.0), 'E', '39176bb8'),
    st('F20', (-1290.0, -388.0), H_S, 'C', '39176bb8'),
    # stem (regional jets observed at F8/F7 and F6)
    obs('F8', (-966.25, -286.25), (-937.5, -285.0), 'B', '39176bb8', ['F7']),
    obs('F6', (-965.0, -322.5), (-936.25, -315.0), 'B', '39176bb8'),
    st('F10', (-966.0, -250.0), H_mS, 'B', '39176bb8'),
    st('F5', (-966.0, -358.0), H_mS, 'B', '39176bb8'),
]
for s_ in STANDS:
    n_ = s_['name']
    if n_ == 'D3': s_['hdg'] = 34.83
    if n_ == 'D4': s_['hdg'] = 20.83
    if n_ == 'D14': s_['hdg'] = 132.83
    if n_ == 'D15': s_['hdg'] = 102.83
    if n_ == 'E6': s_['nose'] = (-757.0, -397.0)
    if n_ == 'E3': s_['nose'] = (-815.0, -432.0)
# B east face: centreline = hold-room point + 17.7 m (mean of the parked-bridge estimates), nose 23 m out from the facade
_BE = {'B9': -974.4, 'B12': -1015.4, 'B13': -1061.1, 'B14': -1102.0, 'B17': -1145.4, 'B18': -1184.6, 'B21': -1228.0}
for s_ in STANDS:
    if s_['name'] in _BE: s_['nose'] = (-362.0, _BE[s_['name']] + 17.7)
# B tip: the fixed walkways (building polygon) run from the B27 hold room to the western stand and from B26 to the southern one
for s_ in STANDS:
    if s_['name'] == 'B26': s_['name'] = 'B27_'
for s_ in STANDS:
    if s_['name'] == 'B27': s_['name'] = 'B26'
for s_ in STANDS:
    if s_['name'] == 'B27_': s_['name'] = 'B27'
# ---- registration correction for the G-pier screenshot (151ec51d): it had slid 17.5 m along the pier axis (verified
# against three independent overview registrations and the pier's hold-room pods); stands measured on it move with it
for s_ in STANDS:
    if s_.get('img') == '151ec51d': s_['nose'] = (round(s_['nose'][0] - 17.5, 2), round(s_['nose'][1] + 0.7, 2))
# ---- E-pier screenshot (c235f3b8) sits ~2.3 m off the consensus of the overview registrations (phase correlation vs
# 35809e3e / bc91df95 and pooled SIFT); move its stands with it
for s_ in STANDS:
    if s_.get('img') == 'c235f3b8': s_['nose'] = (round(s_['nose'][0] + 0.6, 2), round(s_['nose'][1] + 2.3, 2))
# ---- frame migration (24 Sep 2026): legacy grid -> legacy world -> NAD83(2011) lat/lon -> LTP world -> current grid;
# headings through the exact point mapping (tools/geo_frame.py). The records above stay untouched (provenance).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import geo_frame as _GF
def _migrate(s_):
    s2 = dict(s_); lx, lz = _GF.legacy_st_to_legacy_world(*s_['nose'])
    s2['nose'] = _GF.world_to_st(*_GF.legacy_to_world(lx, lz))
    s2['hdg'] = _GF.legacy_hdg_to_hdg(lx, lz, s_['hdg'])
    s2['legacy'] = {'frame': 'equirect-v1', 'nose': s_['nose'], 'hdg': s_['hdg']}
    return s2
LEGACY_STANDS = STANDS
STANDS = [_migrate(s_) for s_ in LEGACY_STANDS]
