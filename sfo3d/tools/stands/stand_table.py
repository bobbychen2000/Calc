"""Which physical stand is which SFO stand: the explicit assignments behind tools/stands/build_stands.py, with the
evidence for every non-trivial one, and the NAIP 2024 readings of parked aircraft.

Names (name_src 'sfo'): SFO's own stand names = the AODB stand names in the flysfo flight-status feed (`stands[]`,
docs/research/gate_truth.md §3; all cached snapshots) and, for stands without an AODB name in the snapshots, the
official gate numbers (DataSF chfu-j7tc gates with operations 18-31 Aug 2026, PDDL; flysfo terminal maps).
Positions: OSM aeroway=parking_position lead-ins (ODbL), oriented by tools/stands/osm_src.py. By default a stand takes
the OSM lead-in whose ref equals its gate number; every exception is listed in OVERRIDES with its evidence.

NAIP readings (NAIP_OBS): parked aircraft visible in NAIP 2024 (USDA, public domain, 0.6 m, 2024-05-20), read by eye
on oriented patches (tools/stands/montage.py tiles, 0.1-0.2 m/px, 1 m ticks) on 24 Sep 2026: nose tip position along
the OSM lead-in (m, + = ahead of the OSM stop node) and lateral offset of the fuselage axis (m, + = right of the
line seen from the cockpit). Reading accuracy about +/- 1.5 m along (bridge cabs and shadows hide some noses; relief
displacement of the fuselage in the orthophoto up to ~1 m) and +/- 0.7 m lateral. 'group' = narrow / wide body as
seen. 'u' = uncertain reading (nose hidden under a bridge).
REVIEW ROUND 2: those accuracy statements were wrong. NAIP relief displacement moves the imaged aircraft EAST by about
0.54 m per metre of height (tools/stands/naip_relief.py fit on 25 stands, residual 0.7 m rms), i.e. 1.3-2.9 m for a
fuselage; the by-eye lateral values below (many 'lateral 0.0') did not see it. The builder now uses only the
along readings, corrected for relief at nose height, and the NUMERICALLY measured, relief-corrected fuselage centre
(refs/cache/stands/naip_relief.json) for the lateral check; the lateral column below is kept as the raw by-eye record.
"""

# SFO stand -> OSM lead-in way id(s) where the ref is missing, duplicated or differs; evidence in the comment.
OVERRIDES = {
    # A pier. A3 is a hold-room label only (no operations, gate_truth.md §4); the OSM "A3" lead-in is the stand SFO
    # names A4T (narrow-body types A321/A20N/B39M in the AODB; NAIP shows a narrow-body with its nose 1.7 m past the
    # OSM "A3" stop node). The unreferenced OSM way 1096422725 on the same axis 12.8 m further out is not used.
    'A4T': {'osm': [1096422724], 'why': 'OSM ref A3 = SFO stand A4T (A3 hold-room label only; AODB narrow-body types; NAIP narrow-body at this stop)'},
    'A1V': {'osm': [1096422742], 'why': 'AODB stand A1V (only A1 variant in the feed) on the OSM A1 lead-in'},
    'A13V': {'osm': [491836041], 'why': 'AODB stand A13V (only A13 variant in the feed) on the OSM A13 lead-in'},
    # B pier west pods: the curved lead-in is the narrow-body stand, the straight long one the wide-body alternative
    # ('S'); ADS-B: JBU413 A321 on curved B5, AAL177 A321 on curved B16, ASA811 A332 (AODB B11S) on straight B11.
    'B5': {'osm': [1376645366], 'why': 'curved OSM B5 lead-in; ADS-B A321 JBU413 at AODB B5'},
    'B5S': {'osm': [1376645365], 'why': 'straight OSM B5 lead-in = wide-body alternative (AODB B5S takes A359/B77W/A333)'},
    'B11': {'osm': [1376645369], 'why': 'curved OSM B11 lead-in (NAIP narrow-body on it)'},
    'B11S': {'osm': [1376645368], 'why': 'straight OSM B11 lead-in; ADS-B ASA811 A332 at AODB B11S'},
    'B16': {'osm': [1376645373], 'why': 'curved OSM B16 lead-in; ADS-B AAL177 A321 at AODB B16'},
    'B16S': {'osm': [1376645372], 'why': 'straight OSM B16 lead-in = wide-body alternative (AODB B16S takes B763/B76W/A339)'},
    'B20': {'osm': [1096422705], 'why': 'curved OSM B20 lead-in (NAIP narrow-body on it); straight 1096422706 has no SFO name'},
    'B23': {'osm': [1096422697], 'why': 'OSM B23 lead-in hdg 339 (NAIP + ADS-B AAL2856 A321 on it); the second OSM B23 way 1096422699 has no SFO name'},
    'B26': {'osm': [1096422702], 'why': 'OSM B26 lead-in hdg 64 (ADS-B AAL2799 B38M on it); straight 1096422703 has no SFO name'},
    'B8': {'osm': [1096393874], 'why': 'unreferenced OSM lead-in between B7 and B9 at the OSM B8 jet bridge; ADS-B ASA424 B39M at AODB B8 and NAIP narrow-body on it'},
    # C: SFO C9V takes B763/B76W; the unreferenced straight lead-in 1096422761 (hdg 268) runs from the C9 bridge
    # axis into the C9/C11 corner. Assignment inferred (no ADS-B yet) - flagged in the output.
    'C9V': {'osm': [1096422761], 'why': 'INFERRED: unreferenced OSM lead-in at the C9 bridge, the only other line there; AODB C9V = 767 alternative of C9'},
    # E: AODB E10U / E11U / E13T are the only E10 / E11 / E13 stands in the feed
    'E10U': {'osm': [895097124], 'why': 'OSM E10 lead-in; ADS-B UAL2647 B39M (AODB E10U) antenna 8.4 m behind its stop, hdg 137.8'},
    'E11U': {'osm': [895097121], 'why': 'OSM E11 lead-in (hdg 261); the unreferenced 1096433104 (hdg 297) is not used'},
    'E13T': {'osm': [895097122], 'why': 'OSM E13 lead-in'},
    # G tip: two hold-room pairs (OSM gate nodes "G11-G12" and "G13-G14"). G13S = the A380/747-8 position with three
    # bridges (OSM "G13 Jetway", "G14 Jetway" + one branch). The AODB narrow-body positions G13R / G14T have no
    # identifiable lead-in: not modelled (UNPLACED_EXTRA / DROPPED).
    'G13S': {'osm': [895097158], 'why': 'OSM G13 lead-in at the three-bridge G13-G14 hold room (AODB G13S takes A388/B748/B77W)', 'alias': ['G14']},
    # Review round 3: the wide-body stand at the G11-G12 hold room is SFO's G12S, not "G11". Evidence: (1) the AODB named
    # it once - UA900 B789 planned on G12S 24 Sep 13:38-14:52 PDT (flysfo snapshot 10:19Z; the flight was later moved);
    # (2) the SFO Museum architecture data (CDLA-Permissive-1.0) has a gate point "G12S" at (-1610.0, 53.1), ON the OSM
    # "G11" lead-in 4.5 m behind its nose (and "G12V" 7.6 m behind it); OSM's ref G11 is a mapper's hold-room label.
    # The narrow-body positions of that hold room, SFO Museum "G11R" (on the unreferenced OSM lead-in 1096433046) and
    # "G12T" (on 1096433044), are listed in UNPLACED_EXTRA. The pairing name <-> line rests on the SFO Museum points
    # (inferred where only they name it).
    'G12S': {'osm': [895097159], 'why': 'AODB G12S (UA900 B789 plan, 24 Sep) = SFO Museum gate point G12S on the OSM "G11" lead-in (4.5 m behind the nose); '
                                        'gates G11 / G12 (DataSF) share this hold room', 'alias': ['G11']},
}

# SFO position names without an AODB allocation in the cached snapshots and without a modelled stand (review round 3):
# listed in data/sfo_stands.json `unplaced` with their evidence. SFO Museum gate points (CDLA-Permissive-1.0) and the
# OSM lead-ins they sit on (ODbL). Narrow-body MARS positions: they share the hold room's two bridges with the wide-body
# stand; the data model (one bridge set per stand, shares_bridges_of for ONE alternative) cannot yet express two
# simultaneous narrow bodies on one bridge pair, so they are not modelled.
UNPLACED_EXTRA = {
    'G11R': {'osm': 1096433046, 'why': 'SFO Museum gate point G11R 1.6 m from the stop of the unreferenced OSM lead-in 1096433046 (hdg 37.9); '
                                       'narrow-body position at the G11-G12 hold room (DataSF gate G11: UA1931 B39M 19/23/24 Aug at the same time as '
                                       'UA1948 at G12); exclusive with G12S (inferred)'},
    'G12T': {'osm': 1096433044, 'why': 'SFO Museum gate point G12T 1.8 m from the stop of the unreferenced OSM lead-in 1096433044 (hdg 87.8); '
                                       'narrow-body position at the G11-G12 hold room (DataSF gate G12 simultaneous with G11); exclusive with G12S (inferred)'},
    'G12V': {'osm': None, 'why': 'SFO Museum gate point G12V on the G12S lead-in 7.6 m behind its nose (meaning of the V variant unknown; cf. A1V, C9V)'},
}


# SFO stand names without operations or without a position we can defend (not modelled; listed in the report)
DROPPED = {
    'B1': 'map/hold-room label; no operations in DataSF 18-31 Aug 2026 and no AODB stand (gate_truth.md §4)',
    'C2': 'map label; no operations, no AODB stand', 'D17': 'map label; no operations', 'D18': 'map label; no operations',
    'A3': 'hold-room label; the lead-in is SFO stand A4T', 'A7': 'no operations, no AODB stand (OSM A7 lead-in exists)',
    'A14': 'no operations, no AODB stand (OSM A14 lead-in exists)',
    'G13R': 'AODB narrow-body position at the G13 hold room (B39M / B738: UA1931, UA1948, UA1243 ... planned 24 Sep 16:14-18:42 PDT '
            'at the same time as G14T) - SFO Museum gate point G13R (-1629.3, 6.5), 11 m from the G13S nose, but no lead-in in OSM '
            'and NAIP 2024 shows a 747 on G13S over it; with G14T a MARS split of G13S (inferred). Not modelled: heading / stop unknown',
    'G14T': 'AODB narrow-body position at the G14 hold room (B39M / B738, planned 24 Sep 16:16-20:48 PDT at the same time as G13R) - '
            'SFO Museum gate point G14T (-1622.3, -28.2) only, no lead-in in OSM / NAIP. Not modelled: heading / stop unknown',
    'G11': 'DataSF gate G11 = the G11-G12 hold room; its wide-body stand is G12S (alias G11), its narrow-body position G11R (UNPLACED_EXTRA)',
    'G14': 'gate (hold room) of stand G13S (OSM gate node "G13-G14")',
}

# NAIP 2024 readings: osm way id -> (nose_along m, lateral m, group, flags)
NAIP_OBS = {
    1096393874: (-2.5, 0.0, 'narrow', ''),          # B8
    1096422724: (1.7, 0.0, 'narrow', ''),           # A4T (OSM A3)
    735028757: (4.5, 0.0, 'wide', ''),              # A9
    735028758: (-1.0, 0.0, 'wide', ''),             # A10 (KLM 777)
    491836059: (1.3, 1.0, 'wide', ''),              # A11
    491836046: (13.0, 0.0, 'wide', 'u'),            # A12 (nose under the bridge)
    491836043: (2.3, 0.3, 'narrow', ''),            # A15
    1376645363: (0.0, 0.0, 'narrow', ''),           # B2
    1376645364: (3.0, 0.0, 'narrow', ''),           # B4
    1376645369: (3.0, 0.0, 'narrow', ''),           # B11
    1376645370: (3.5, 0.0, 'narrow', ''),           # B15
    1096422705: (4.0, 0.0, 'narrow', ''),           # B20
    1096422695: (-4.0, 0.0, 'narrow', ''),          # B22
    1096422697: (0.5, 0.9, 'narrow', ''),           # B23
    895097101: (1.0, 0.0, 'narrow', ''),            # C3
    895097100: (5.0, 0.0, 'narrow', ''),            # C5
    895097099: (0.0, 0.0, 'narrow', ''),            # C7
    895097098: (1.0, 0.0, 'narrow', ''),            # C9
    # C11: review round 3 re-read (the reviewer: nose at about -4 m). The aircraft has a grey forward fuselage and grey
    # wings that merge with the concrete; the -14 m reading had taken the start of the white aft fuselage for the nose.
    # Engines at ~-11 m, wing tips ~-19 m, tail end ~-37.5 m (oriented crop, 0.1 m px, contrast-stretched) put the nose
    # of an A319 / A320 / 737-size body at about -3..0 m. The nose itself is not visible -> 'u' (not used).
    895097097: (-3.0, 0.0, 'narrow', 'u'),          # C11 (narrow body, grey forward fuselage; nose estimated)
    895097104: (-0.5, 0.3, 'narrow', ''),           # D3
    895097105: (1.0, 0.0, 'narrow', ''),            # D4
    895097106: (-1.5, -0.5, 'narrow', ''),          # D5
    895097107: (1.0, 0.0, 'narrow', ''),            # D6
    895097108: (0.0, 0.0, 'narrow', ''),            # D7
    895097112: (-6.0, 0.0, 'narrow', ''),           # D11
    895097116: (-2.0, 0.0, 'narrow', ''),           # D16
    895097117: (-1.5, 0.0, 'narrow', ''),           # E4
    895097132: (2.0, 0.0, 'narrow', ''),            # F7
    895097133: (0.0, 0.0, 'narrow', 'u'),           # F8
    895097135: (0.0, 0.0, 'narrow', ''),            # F9
    895097134: (2.0, 0.0, 'narrow', ''),            # F10
    895097137: (-5.0, -1.0, 'wide', ''),            # F13
    895097145: (3.0, 0.0, 'narrow', ''),            # F14
    895097138: (7.0, -8.0, 'wide', ''),             # F15: wide-body 8 m left of the short OSM stub
    895097152: (2.0, -5.2, 'wide', ''),             # G1
    895097163: (4.0, 1.5, 'wide', ''),              # G3
    895097162: (4.0, 1.6, 'wide', ''),              # G4
    895097155: (3.0, -0.7, 'wide', ''),             # G6
    895097161: (7.0, 2.0, 'wide', ''),              # G7
    895097160: (4.5, 0.7, 'wide', ''),              # G8
    895097156: (5.8, -2.4, 'wide', ''),             # G9
    895097157: (-0.7, -1.1, 'wide', ''),            # G10
    895097159: (7.8, -0.7, 'wide', ''),             # G11
    895097158: (5.8, -3.7, 'wide', ''),             # G13S
}

# What the NAIP 2024 image shows on the wide-body stands whose parked aircraft stopped more than 1.5 m from the model nose
# (review round 3: "record which type is parked before accepting a type stop"). By-eye readings on oriented 0.25 m
# crops (nose / tail end along the stand axis, +-3 m; span +-4 m: wing tips lean with the relief, see naip_relief.py),
# engine count and livery where visible. Candidate types are inferred from these dimensions only (ACAP lengths: B772
# 63.7, B789 62.8, B78X 68.3, A359 66.8, B77W 73.9, B744 70.7, B748 76.3 m). No registration is visible, so none of
# them is identified; the along residual stays unexplained ('conflict_along').
NAIP_IMAGED = {
    735028758: 'twin, blue KLM-style fuselage, nose -6 / tail -73 m (~67 m), span ~61 m: B772 or B78X size',        # A10
    491836046: 'twin, nose under the bridge (not visible), tail -63 m: length not measurable',                     # A12
    895097137: 'twin, blue engine cowls, nose -7 / tail -71 m (~64 m), span ~60 m: B789 or B772 size',             # F13
    895097161: 'twin, nose +3 / tail -65 m (~68 m): B78X / A359 size (span not readable at the tile edge)',        # G7
    895097156: 'twin, nose +4 / tail -68 m (~72 m), span ~63 m: B77W size',                                         # G9
    895097157: 'twin, dark (black) fuselage, nose -3 / tail -75 m (~72 m): B77W size',                              # G10
    895097159: 'twin, nose +2 / tail -67 m (~69 m): B78X / B77W size',                                              # G12S
    895097158: 'four engines, nose +2 / tail -72 m (~74 m): B744 / B748 (747)',                                     # G13S
}

# Positions taken from NAIP instead of OSM (pos_src 'naip'): the OSM line is contradicted by the imagery.
# F15: the OSM F15 way is a 24.5 m two-node stub; NAIP shows a wide-body (SFO parks B772 at F15) parallel to it,
# 8 m to its left (as imaged) with the nose 7 m ahead of the stub's end. Review round 2: the imaged fuselage leans east
# (NAIP relief, tools/stands/naip_relief.py, k = 0.54 m/m); at heading 211 deg east is to the LEFT, so the real axis is
# ~2.4 m right of the imaged one: the builder takes the relief-corrected, numerically measured reading (lateral -5.9 m,
# nose +8.3 m; 'along'/'lat' below are only the fallback by-eye values). Not 'verified' by NAIP (circular); ADS-B
# (UAL1189 B39M, adsb.lol) is the independent check.
NAIP_POS = {'F15': {'along': 7.0, 'lat': -8.0}}

# OSM jet bridges the geometric assignment cannot place (parked far from any door slot): bridge way id -> stand.
# 1096422719 "A7 Jetway": A7 is not an SFO stand; the bridge sits between A6 and A8 on the A-east face, parked
# retracted 38 m behind / 37 m left of the A6 nose. A6 is the A-east stand SFO gives A388s (AODB), which board over
# three bridges; this is taken as A6's third bridge (inferred, not verified with an A380 on stand).
BRIDGE_OVERRIDES = {1096422719: 'A6'}

# Bridges assigned explicitly, before (and outside) the geometric assignment (review round 2, B10/B11 hold room; OSM way
# geometry in world x, z; stand frames from data/sfo_stands.json):
#   1096422714 (OSM ref 'B11', building -> (-908.4, 717.6)): NAIP 2024 shows its cab at the L1 door of the narrow body on
#     the curved B11 lead-in (refs/cache/stands/view/rev2_B10B11.png) -> B11 (OSM ref and imagery agree). The
#     assignment had given it to B11S.
#   1096422712 (OSM ref 'B11S', two nodes, cab (-903.4, 659.3)): 20.7 m LEFT of / 12.4 m behind the B10 nose - the only
#     bridge on B10's door side -> B10 (geometry; the OSM ref is taken as a mapper's hold-room label - inferred).
#   1096422713 (OSM ref 'B10', cab (-897.4, 698.8)): 13.7 m to the RIGHT of the B10 axis (8 m ahead of the nose), so it
#     cannot reach a left-side door of an aircraft on B10 without crossing its nose; 14.2 m left of / 10.9 m behind the
#     B11S nose -> B11S (geometry; not the OSM ref - review round 2 asked to follow the ref, rejected on this geometry).
BRIDGE_FORCE = {1096422714: 'B11', 1096422712: 'B10', 1096422713: 'B11S'}

# OSM jet-bridge ways not used as bridges: way id -> reason
BRIDGE_IGNORE = {1102580432: 'OSM "F18 Jetway": a 7.8 m two-node stub 32-39 m ahead of the F18 nose; not a usable bridge '
                             'geometry (it would become F17\'s L1 and cross the F17 bridge)',
                  1102580433: 'OSM "F10" bridge: its building end lies right-front of the F10 nose (the stand heads 177 deg into the '
                              'pier; the boarding door is on the left) and NAIP 2024 shows the regional jet on F10 with this bridge '
                              'parked ahead of its nose. Docking would need the tunnel to cross the nose and the cab to turn ~150 deg '
                              '(review round 1; standard cab 125 deg). Not used: F10 is modelled without a bridge (boarding by stairs '
                              'or by walking - inferred, not verified).'}

# Static fix-up (26 Sep 2026; review round 4: "F5 L1 reach infeasible - decide from evidence"). Bridges that are NOT any
# Oshkosh datasheet unit, with the evidence: way id -> {why}. The builder gives them ext_range = [imaged rest length,
# longest observed docking] (rotunda centre -> cab pivot, PIVOT_TO_DOOR 2.4 m), model None, `short_unit` True.
#   1102580434 F5 L1: NAIP 2024 (refs/cache/stands/view/f5raw.png, 0.06 m/px) shows a ~3.5 m wide roof running 9.3 m from
#     the drum to the cab front; the OSM way is 9.1 m rotunda -> cab end. The shortest Oshkosh unit (AT2 41/55) is
#     12.224 m fully retracted (sell sheet), so this bridge is ~3 m shorter than any datasheet unit. Two SkyWest E175s
#     (ADS-B, SFO stand window F5, 1027 s and 273 s) stood at the model nose (+1.5 m vs the E-Jet norm), so the observed
#     dockings need 7.2-7.5 m rotunda -> pivot, within reach of a unit that rests at ~6.7-6.9 m. Maker / model not known.
BRIDGE_SHORT = {1102580434: {'why': 'NAIP 2024 roof 9.3 m drum -> cab front (OSM 9.1 m), ~3 m shorter than the shortest Oshkosh unit '
                                    'fully retracted (12.224 m); two ADS-B E175 stays at the model nose need 7.2-7.5 m: a short '
                                    'non-datasheet unit (maker / model not known; inferred from the imaged length)'}}

# Static fix-up (26 Sep 2026; review round 4: "A1 / A2 L2 ... reach - decide from evidence (manufacturer range)").
# (stand, door) -> {type: why}: an observed type the bridge does NOT dock, by decision. The 787-10's L2 door at A1 / A2
# needs 43.7 / 42.4 m rotunda -> pivot; the only manufacturer data in hand (Oshkosh sell sheet) ends at 41.381 m, and
# nothing shows SFO has longer units (TK Elevator's "14 to 50 m" gives no reference points and no SFO installation).
# Decision: the L2 bridge stays at rest for the 787-10 (boarding through L1 only); stop / rotunda uncertainty (+-1.5 m
# stop, OSM roof lean 1.3-2.1 m) could make it reachable - not proven either way.
DOCK_OUT_DECIDED = {('A1', 2): {'B78X': 'L2 docking needs 43.7 m, beyond the longest Oshkosh unit (41.4 m); no evidence of a longer unit at SFO: L2 stays at rest, L1 boards (inferred)'},
                    ('A2', 2): {'B78X': 'L2 docking needs 42.4 m, beyond the longest Oshkosh unit (41.4 m); no evidence of a longer unit at SFO: L2 stays at rest, L1 boards (inferred)'}}
