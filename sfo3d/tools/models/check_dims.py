#!/usr/bin/env python3
"""Triple-check the imported aircraft models (data/models/*.sfom), the airframe table (js/aircraft/types.js) and the
ICAO type -> model mapping (js/live/aircraft.js) against the manufacturers' airport-planning documents.

What it does
  1. Decodes every .sfom (format: tools/convert_models.py / js/live/models.js) and measures the model in its own frame
     (x forward, nose at 0; y up, fuselage centreline at 0; z starboard): length, span, fin top, lowest point,
     fuselage radius/half-width, tailplane span, engine centre-line offsets, wheels (only b738 has gear).
  2. Optionally (if the FlightAirMap source .glb files are present) re-derives the same normalised frame from the source
     and measures the model's OWN door / landing-gear-door meshes, i.e. where the artist put the doors.
  3. Loads TYPES from js/aircraft/types.js with node, parses TYPE_MODELS / HEIGHT / MODEL_BASE from js/live/aircraft.js,
     and reproduces the runtime rules: uniform scale s = T.L / (model L + plugs), plug stretching (stretchFor), seating
     of gear-less models from the HEIGHT table (seatType), door docking point (gates.js doorOf: door x + 0.5 m).
  4. Compares what the app renders / uses against REF (below), transcribed by hand from the manufacturer documents.
     Every value carries its document, page and figure. Values marked 'inf' are inferred (e.g. a door centre derived
     from a dimensioned door edge + door width, or scaled off a drawing) and are not treated as hard references.

Documents (downloaded into refs/cache/acap/, gitignored):
  Boeing ACAPs  https://www.boeing.com/commercial/airports/plan-manuals  (737NG D6-58325-7 Rev C, 737 MAX D6-38A004 Rev K,
                757 D6-58327 Rev H, 767 D6-58328 Rev K, 777 D6-58329 Rev E, 777LR/ER D6-58329-2 Rev G, 777-9 D6-86073 Rev G,
                787 D6-58333 Rev Q, 747-400 D6-58326-1 Rev F, 747-8 D6-58326-3 Rev E)
  Airbus AC     https://www.aircraft.airbus.com/en/customer-care/fleet-wide-care/airport-operations-and-aircraft-characteristics/aircraft-characteristics
                (AC A319 Jul 15/25, AC A320 Jun 01/24, AC A321 Jul 15/25, AC A330 Dec 01/25, AC A350 Jul 15/25, AC A380 Dec 01/25)
  Airbus A220   A220-100 APP BD500-3AB48-22000-00 (2023-09), A220-300 APP BD500-3AB48-32000-00 (2022-05) (both marked
                superseded by the ACP, which could not be downloaded)
  Embraer APM   E175 APM-2259 (May 25/18, attachment 2 of NTSB docket DCA20IA014), E190 APM-1901 (May 21/21, web.archive.org
                copy of embraercommercialaviation.com/wp-content/uploads/2017/06/APM_190.pdf)
  Bombardier    CRJ100/200 APM CSP A-020 Rev 8, CRJ700 APM CSP B-020 Rev 15, CRJ900 APM CSP C-020 Rev 11
                (customer.aero.bombardier.com public links)

Usage:  python3 tools/models/check_dims.py [--md report.md] [--json out.json] [--fam DIR] [--tol 1.0]
"""
import argparse, gzip, json, os, re, struct, subprocess, sys
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
MODELS_DIR = os.path.join(ROOT, 'data', 'models')

# ----------------------------------------------------------------------------------------------------------------------
# Reference data (metres).  x positions are measured from the nose tip along the fuselage axis.
#   L span H(min,max = vertical-tail height range from the ground-clearance table; Airbus: MRW..light)
#   nose = nose tip -> nose-gear axle;  main = nose tip -> main-gear axle (nose + wheelbase);  track = main-gear track
#   doors = passenger door centres (1 = L1, 2 = second door on the left side, ...);  sill1 = L1 sill height range
#   'inf' in a source string marks an inferred value.
B737NG = 'Boeing D6-58325-7 Rev C (Oct 2025) 737NG ACAP'
B737MAX = 'Boeing D6-38A004 Rev K (Jul 2025) 737 MAX ACAP'
B757 = 'Boeing D6-58327 Rev H (Dec 2024) 757 ACAP'
B767 = 'Boeing D6-58328 Rev K (Dec 2024) 767 ACAP'
B777 = 'Boeing D6-58329 Rev E (Dec 2024) 777-200/-200ER/-300 ACAP'
B777LR = 'Boeing D6-58329-2 Rev G (Dec 2024) 777-200LR/-300ER/F ACAP'
B777X = 'Boeing D6-86073 Rev G (Sep 2025) 777-9 ACAP (preliminary)'
B787 = 'Boeing D6-58333 Rev Q (Oct 2025) 787 ACAP'
B744 = 'Boeing D6-58326-1 Rev F (Dec 2024) 747-400 ACAP'
B748 = 'Boeing D6-58326-3 Rev E (Jan 2026) 747-8 ACAP'
AC319 = 'Airbus AC A319 (Rev Jul 15/25)'
AC320 = 'Airbus AC A320 (Rev Jun 01/24)'
AC321 = 'Airbus AC A321 (Rev Jul 15/25)'
AC330 = 'Airbus AC A330 (Rev Dec 01/25)'
AC350 = 'Airbus AC A350 (Rev Jul 15/25)'
AC380 = 'Airbus AC A380 (Rev Dec 01/25)'
A221 = 'Airbus A220-100 APP BD500-3AB48-22000-00 (2023-09-08)'
A223 = 'Airbus A220-300 APP BD500-3AB48-32000-00 (2022-05-12)'
E175 = 'Embraer APM-2259 E175 (May 25/18; NTSB DCA20IA014 att. 2)'
E190 = 'Embraer APM-1901 E190 (May 21/21)'
CRJ2 = 'Bombardier CSP A-020 Rev 8 CRJ100/200 APM (Jan 10/2016)'
CRJ7 = 'Bombardier CSP B-020 Rev 15 CRJ700 APM (Dec 17/2015)'
CRJ9 = 'Bombardier CSP C-020 Rev 11 CRJ900 APM (Dec 17/2015)'

REF = {
    # ---- Boeing 737
    'B737': dict(crown=(5.41, 5.56), doc=B737NG, name='737-700 (winglets)', L=33.63, span=35.79, H=(12.45, 12.67), nose=4.09, main=4.09 + 12.60, track=5.72,
                 doors={1: 5.03}, sill1=(2.59, 2.74),
                 src='§2.2.4 p.2-12 (dims), §2.3.3 p.2-19 (J vertical tail, B entry door 1), §2.7.1 p.2-33 (door 1: 16 ft 6 in)'),
    'B738': dict(crown=(5.41, 5.56), doc=B737NG, name='737-800 (winglets)', L=39.47, span=35.79, H=(12.37, 12.62), nose=4.09, main=4.09 + 15.60, track=5.72,
                 doors={1: 5.03}, sill1=(2.59, 2.74), src='§2.2.6 p.2-14, §2.3.3 p.2-19, §2.7.1 p.2-33'),
    'B739': dict(crown=(5.41, 5.59), doc=B737NG, name='737-900ER (winglets)', L=42.11, span=35.79, H=(12.37, 12.62), nose=4.09, main=4.09 + 17.17, track=5.72,
                 doors={1: 5.03}, sill1=(2.59, 2.74), src='§2.2.8 p.2-16, §2.3.3 p.2-19, §2.7.1 p.2-33'),
    'B38M': dict(crown=(5.08, 5.51), doc=B737MAX, name='737-8', L=39.47, span=35.92, H=(11.86, 12.45), nose=4.09, main=4.09 + 15.60, track=5.72,
                 doors={1: 5.03, 2: 31.88}, sill1=(2.77, 3.07),
                 src='§2.2.2 p.2-10 (plan length 129 ft 6 in), §2.3.2 p.2-14 (P, B), §2.7.1 p.2-26 table (B, H)'),
    'B39M': dict(crown=(5.08, 5.51), doc=B737MAX, name='737-9', L=42.11, span=35.92, H=(11.89, 12.40), nose=4.09, main=4.09 + 17.17, track=5.72,
                 doors={1: 5.03, 2: 34.52}, sill1=(2.79, 3.07), src='§2.2.3 p.2-11, §2.3.3 p.2-15, §2.7.1 p.2-26'),
    'B3XM': dict(crown=(5.08, 5.54), doc=B737MAX, name='737-10', L=43.79, span=35.92, H=(11.91, 12.45), nose=4.09, main=4.09 + 18.34, track=5.72,
                 doors={1: 5.03, 2: 36.20}, sill1=(2.77, 3.07), src='§2.2.4 p.2-12, §2.3.4 p.2-16, §2.7.1 p.2-26 (preliminary)'),
    # ---- Boeing 757
    'B752': dict(doc=B757, name='757-200', L=47.32, span=38.05, H=(13.49, 13.74), nose=5.89, main=5.89 + 18.29, track=7.32,
                 doors={1: 5.05, 2: 13.99, 4: 38.23},
                 src='§2.2.1 p.2-10, §2.3.1 p.2-12 (K; letter->vertical tail inferred from magnitude), §2.7.1 p.2-21 table ("nose to center of door")'),
    'B753': dict(doc=B757, name='757-300', L=54.43, span=38.06, H=(13.56, 13.64), nose=5.89, main=5.89 + 22.35, track=7.32,
                 doors={1: 5.05, 2: 13.99, 3: 35.99, 4: 45.34}, src='§2.2.2 p.2-11, §2.3.2 p.2-13 (K), §2.7.1 p.2-21'),
    # ---- Boeing 767
    'B763': dict(doc=B767, name='767-300/-300ER', L=54.94, span=47.57, H=(15.39, 16.03), nose=4.55, main=4.55 + 22.76, track=9.30,
                 doors={1: 5.70, 2: 15.96, 3: 42.55}, src='§2.2.2 p.2-9, §2.3.2 p.2-13 (J), §2.7.1 p.2-30 (door 2 = optional mid-cabin door on -300/-300ER)'),
    'B764': dict(doc=B767, name='767-400ER', L=61.37, span=51.92, H=(16.68, 17.01), nose=4.56, main=4.56 + 26.2, track=9.30,
                 doors={1: 5.70, 2: 19.34, 3: 48.95}, src='§2.2.4 p.2-11, §2.3.4 p.2-15 (J), §2.7.1 p.2-30'),
    # ---- Boeing 777
    'B772': dict(doc=B777, name='777-200/-200ER', L=63.73, span=60.93, H=(18.42, 18.76), nose=5.89, main=5.89 + 25.88, track=10.97,
                 doors={1: 6.75, 2: 17.07, 3: 36.33, 4: 49.54}, src='§2.2.1 p.2-8, §2.3.1 p.2-10 (K), §2.7.1 p.2-23'),
    'B77L': dict(doc=B777LR, name='777-200LR / 777F', L=63.73, span=64.80, H=(18.48, 18.75), nose=5.89, main=5.89 + 25.89, track=10.97,
                 doors={1: 6.74, 2: 17.07, 3: 36.32, 4: 49.53}, src='§2.2.1 p.2-3, §2.3.1 p.2-6 (K), §2.7.1 p.2-19'),
    'B77W': dict(doc=B777LR, name='777-300ER', L=73.86, span=64.80, H=(18.24, 18.85), nose=5.89, main=5.89 + 31.22, track=10.97,
                 doors={1: 6.74, 2: 17.07, 3: 32.92, 4: 46.46, 5: 59.67}, src='§2.2.2 p.2-4, §2.3.2 p.2-7 (K), §2.7.1 p.2-19'),
    'B779': dict(doc=B777X, name='777-9 (wingtips folded on the ground: 64.85)', L=76.73, span=64.85, H=(19.28, 19.74), nose=5.89,
                 main=5.89 + 32.33, src='§2.2.1 Fig 2-1 p.2-3 (extended span 71.76; ground = folded 64.85), §2.3.1 p.2-4 (Q); wheelbase 106 ft 1 in inf'),
    # ---- Boeing 787
    'B788': dict(doc=B787, name='787-8', L=56.72, span=60.12, H=(16.59, 17.09), nose=5.41, main=5.41 + 22.78, track=9.80,
                 doors={1: 6.30, 2: 15.32, 3: 32.39, 4: 43.56}, src='§2.2.1 p.2-5, §2.3.1 p.2-8 (N), §2.7.1 p.2-16 table'),
    'B789': dict(doc=B787, name='787-9', L=62.81, span=60.12, H=(16.81, 17.09), nose=5.41, main=5.41 + 25.83, track=9.80,
                 doors={1: 6.30, 2: 18.36, 3: 35.43, 4: 49.66}, src='§2.2.2 p.2-6, §2.3.2 p.2-9 (N), §2.7.1 p.2-16'),
    'B78X': dict(doc=B787, name='787-10', L=68.30, span=60.12, H=(16.89, 17.02), nose=5.41, main=5.41 + 28.88, track=9.80,
                 doors={1: 6.30, 2: 21.41, 3: 38.48, 4: 55.14}, src='§2.2.3 p.2-7, §2.3.3 p.2-10 (N), §2.7.1 p.2-16'),
    # ---- Boeing 747
    'B744': dict(doc=B744, name='747-400', L=70.67, span=64.44, H=(18.80, 19.51), nose=7.75, main=7.75 + 25.60, track=11.00,
                 doors={1: 9.50, 2: 18.80, 3: 30.61, 4: 40.74, 5: 55.14},
                 src='§2.2.1 p.2-14 (span 64.44 jig / 64.92 at MGW; wing gear), §2.3.1 p.2-17 (K), §2.7.1 p.2-35'),
    'B748': dict(doc=B748, name='747-8', L=76.25, span=68.40, H=(18.97, 19.51), nose=7.74, main=7.74 + 29.66, track=10.99,
                 doors={1: 9.5, 2: 22.9, 3: 34.7, 4: 46.3, 5: 60.8}, src='§2.2.2 p.2-5 (wing gear; body gear +3.07), §2.3.2 p.2-7 (K), §2.7.1 p.2-14'),
    # ---- Airbus narrow-bodies
    'A319': dict(doc=AC319, name='A319ceo (wing-tip fence)', L=33.84, span=34.10, H=(11.89, 12.05), nose=5.07, main=5.07 + 11.04, track=7.59,
                 doors={1: 5.04, 2: 25.81}, src='2-2-0 FIG-2-2-0-991-002-A01 sh.1-2, 2-3-0 FIG-2-3-0-991-028-A01 (VT; text order, inf), 2-7-0 FIG-2-7-0-991-002-A01 sh.2'),
    'A19N': dict(doc=AC319, name='A319neo', L=33.84, span=35.80, nose=5.07, main=5.07 + 11.04, track=7.59, doors={1: 5.04, 2: 25.81},
                 src='2-2-0 FIG-2-2-0-991-008-A01, 2-7-0 FIG-2-7-0-991-002-A01'),
    'A320': dict(doc=AC320, name='A320ceo (wing-tip fence; sharklet 35.80)', L=37.57, span=34.10, nose=5.07, main=5.07 + 12.64, track=7.59,
                 doors={1: 5.04, 2: 29.53}, src='2-2-0 FIG-2-2-0-991-004-A01 sh.1-2, 2-7-0 FIG-2-7-0-991-003-A01 sh.2 (overwing exits 14.43/15.28)'),
    'A20N': dict(crown=(5.86, 5.97), doc=AC320, name='A320neo', L=37.57, span=35.80, H=(11.83, 12.08), nose=5.07, main=5.07 + 12.64, track=7.59,
                 doors={1: 5.04, 2: 29.53}, sill1=(3.38, 3.48), src='2-2-0 FIG-2-2-0-991-009-A01 p.6-7, 2-3-0 FIG-2-3-0-991-032-A01 p.6 (VT, D1), 2-7-0 FIG-2-7-0-991-003-A01'),
    'A321': dict(doc=AC321, name='A321ceo (fence; sharklet 35.80)', L=44.51, span=34.10, nose=5.07, main=5.07 + 16.90, track=7.59,
                 doors={1: 5.02, 2: 13.84, 3: 24.79, 4: 36.58}, src='2-2-0 FIG-2-2-0-991-005-A01, 2-7-0 FIG-2-7-0-991-004-A01 sh.2'),
    'A21N': dict(doc=AC321, name='A321neo (4-door; ACF/XLR: 1L 5.04, OW 18.70/19.54, 3L 26.82, 4L 36.47)', L=44.51, span=35.80,
                 nose=5.07, main=5.07 + 16.90, track=7.59, doors={1: 5.02, 2: 13.84, 3: 24.79, 4: 36.58},
                 src='2-2-0 FIG-2-2-0-991-010-A01 p.6-7, 2-7-0 FIG-2-7-0-991-004-A01 / -047-A01'),
    # ---- Airbus wide-bodies
    'A332': dict(doc=AC330, name='A330-200 (post-mod 48979)', L=58.82, span=60.30, nose=6.67, main=28.85, track=10.68,
                 doors={1: 5.85, 2: 14.56, 3: 32.77, 4: 45.63}, src='2-2-0 FIG-2-2-0-991-002-A01 sh.2, 2-7-0 FIG-2-7-0-991-006-A01 sh.2 (text order, inf)'),
    'A333': dict(crown=(7.58, 7.74), doc=AC330, name='A330-300', L=63.67, span=60.30, H=(16.72, 17.18), nose=6.67, main=32.05, track=10.68,
                 doors={1: 5.85, 2: 17.74, 3: 35.96, 4: 50.96}, sill1=(4.41, 4.55),
                 src='2-2-0 FIG-2-2-0-991-001-A01 sh.1-2 p.2-3, 2-3-0 FIG-2-3-0-991-001-A01 p.2 (VT, D1), 2-7-0 FIG-2-7-0-991-006-B01'),
    'A339': dict(doc=AC330, name='A330-900', L=63.66, span=64.00, nose=6.67, main=32.05, track=10.68,
                 doors={1: 5.85, 2: 17.74, 3: 35.96, 4: 50.96}, src='2-2-0 FIG-2-2-0-991-011-A01 p.7, 2-7-0 FIG-2-7-0-991-006-B01'),
    'A359': dict(crown=(8.50, 8.64), doc=AC350, name='A350-900', L=66.80, span=64.75, H=(17.14, 17.47), nose=4.63, main=4.63 + 28.66, track=10.60,
                 doors={1: 6.82, 2: 18.86, 3: 37.93, 4: 52.55}, sill1=(5.04, 5.36),
                 src='2-2-0 FIG-2-2-0-991-001-A01 p.2-3 (plan 66.80, side 66.61), 2-3-0 FIG-2-3-0-991-001-A01 p.2, 2-7-0 FIG-2-7-0-991-001-A01 p.3'),
    'A35K': dict(doc=AC350, name='A350-1000', L=73.79, span=64.75, nose=4.63, main=4.63 + 32.48, track=10.73,
                 doors={1: 6.82, 2: 23.30, 3: 42.38, 4: 59.53}, src='2-2-0 FIG-2-2-0-991-002-C01 (wheelbase to centre axle, inf from text order), 2-7-0 FIG-2-7-0-991-001-D01'),
    'A388': dict(crown=(10.75, 10.97), doc=AC380, name='A380-800', L=72.73, span=79.75, H=(24.12, 24.27), nose=4.97, main=33.58, doors={1: 6.32, 2: 16.50},
                 sill1=(5.10, 5.36), src='2-2-0 FIG-2-2-0-991-001-A01 p.2 (WLG 33.58, BLG 36.85), 2-3-0 FIG-2-3-0-991-001-A01 (VT, M1; U1 sill 7.87-8.08), 2-7-0 FIG-2-7-0-991-002-A01 (U1 20.94)'),
    # ---- A220
    'BCS1': dict(doc=A221, name='A220-100', L=34.9, span=35.1, track=6.7,
                 src='§2.1 Fig 1 p.4-5 (figure labels lost in the PDF; values legible, assignment of length/span/track by magnitude, inf)'),
    'BCS3': dict(doc=A223, name='A220-300', L=38.69, span=34.98, H=(11.73, 11.73), nose=3.39, main=3.39 + 15.31, track=6.73,
                 src='§2.1 Table 5 + Fig 1 (A=1523.2 in, E=1377.3 in, C=461.9 in, W=133.4 in, Z=602.6 in, Y=265.0 in)'),
    # ---- Embraer
    'E75L': dict(doc=E175, name='E175 enhanced wingtip ("long wing")', L=31.68, span=28.65, H=(9.54, 9.86), nose=4.13, main=4.13 + 11.40, track=5.20,
                 doors={1: 5.14}, src='§2.2.2 p.2-3, Fig 2.2 p.2-5 (plan view, nose left: lower = left side; door 1L forward edge 4.71, 1R 4.27; L1 centre = 4.71 + 0.85/2, inf)'),
    'E75S': dict(doc=E175, name='E175 winglet ("short wing")', L=31.68, span=26.00, H=(9.54, 9.86), nose=4.13, main=4.13 + 11.40, track=5.20,
                 doors={1: 5.14}, src='§2.2.1 p.2-3, Fig 2.1 p.2-4 (door as E75L, inf)'),
    'E190': dict(doc=E190, name='E190', L=36.24, span=28.72, H=(10.33, 10.57), nose=4.13, main=4.13 + 13.83, track=5.94,
                 doors={1: 5.14}, src='Fig 2.1 p.2-4 (door 1L forward edge 4.71 in the plan view, centre inf)'),
    'E195': dict(doc='Embraer APM-1997 E195 (Oct 07/08; web.archive.org copy)', name='E195', L=38.65, span=28.72, H=(10.29, 10.57), track=5.94,
                 doors={1: 5.14}, src='§2.2.3 p.2-3 (length), Fig 2.1 p.2-4 (span, height, track; door 1L forward edge 4.71, centre inf)'),
    # ---- CRJ
    'CRJ2': dict(doc=CRJ2, name='CRJ200', L=26.77, span=21.23, H=(6.18, 6.32), crown=(3.84, 4.04), track=3.14, doors={1: 4.72}, sill1=(1.50, 1.73),
                 src='00-02-01 Fig 2 p.5 (wheelbase 11.4; track = 2 x 1.57 m half-track, inf; door centre scaled off the drawing, inf), Fig 3 p.6 (E fin, A fuselage top, B door sill)'),
    'CRJ7': dict(doc=CRJ7, name='CRJ700', L=32.34, span=23.25, H=(7.51, 7.51), track=4.12, doors={1: 4.22 + 0.455}, sill1=(1.73, 1.73),
                 src='00-02-02 Table 1/2 p.1-2 (wheelbase 15.01), 00-02-04 Table 1 (G: passenger door FWD side to radome 4.22 m; centre inf)'),
    'CRJ9': dict(doc=CRJ9, name='CRJ900 (15036+; early a/c span 23.24)', L=36.24, span=24.85, H=(7.35, 7.35), track=4.07, doors={1: 4.22 + 0.455},
                 sill1=(1.73, 1.73), src='00-02-02 Table 1 p.1/p.8, Table 2 (wheelbase 17.30), 00-02-04 Table 1 (I: 4.22 m; centre inf)'),
}
# E-Jet heights: H = (ground-clearance table value at the loading conditions, "Height (maximum)" of §2.2): E175 APM-2259
# §2.2.1 p.30 "Height (maximum) - 9.86 m", Table 2.2 p.37 9.54 m; E190 APM-1901 Fig 2.1 p.30 10.57 m, Table 2.3 p.35-37
# 10.33 m; E195 APM-1997 Fig 2.1 p.34 10.57 m, Table 2.3 p.37 10.29 m (PyMuPDF text of the cached PDFs).
WHEELBASE = {'CRJ2': 11.4, 'CRJ7': 15.01, 'CRJ9': 17.30}   # wheelbase only (nose-gear position not dimensioned)

# ----------------------------------------------------------------------------------------------------------------------
def load_sfom(path):
    raw = gzip.decompress(open(path, 'rb').read())
    if raw[:4] != b'SFOM': raise ValueError('not an SFOM file: ' + path)
    _ver, hl = struct.unpack('<II', raw[4:12]); head = json.loads(raw[12:12 + hl]); B = 12 + hl
    q, o, nv = head['quant'], head['offsets'], head['nv']
    pq = np.frombuffer(raw, dtype=np.uint16, count=nv * 3, offset=B + o['pos']).reshape(-1, 3)
    pos = np.array(q['pmin']) + pq * np.array(q['pscale'])
    zone = np.frombuffer(raw, dtype=np.uint8, count=nv, offset=B + o['zone'])
    idx = np.frombuffer(raw, dtype=np.uint16 if head['idxType'] == 'u16' else np.uint32, count=head['ni'], offset=B + o['idx'])
    used = np.unique(idx)
    return head, pos[used].copy(), zone[used].copy()


def measure(head, P, Z):
    d = head['dims']; L = d['L']
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    out = dict(L=L, span=float(z.max() - z.min()), finTop=float(y.max()), low=float(y.min()), R=d['R'], Rz=d['Rz'], hasGear=d['hasGear'])
    aft = x < -0.84 * L                         # tailplane region (aft 16 %)
    out['hstab'] = float(2 * np.abs(z[aft]).max()) if aft.any() else None
    eng = Z == 2
    if eng.sum() > 50:
        az = np.abs(z[eng]); zs = np.sort(az)
        # one or two engines per side: split at the largest gap in |z|
        gaps = np.diff(zs); k = int(np.argmax(gaps)) if len(gaps) else 0
        if len(gaps) and gaps[k] > 1.5 and az.min() > 1.0:
            out['engZ'] = [float(np.median(zs[:k + 1])), float(np.median(zs[k + 1:]))]
        else:
            out['engZ'] = [float(np.median(az))] if az.min() > 1.0 else None  # rear-mounted engines sit near the fuselage
    if d['hasGear']:
        g = P[Z == 3]
        bottom = g[g[:, 1] < g[:, 1].min() + 0.35]
        nose = bottom[bottom[:, 0] > -0.3 * L]; mains = bottom[bottom[:, 0] < -0.3 * L]
        out['gear'] = dict(nose=float(-np.median(nose[:, 0])) if len(nose) else None,
                           main=float(-np.median(mains[:, 0])) if len(mains) else None,
                           track=float(np.median(mains[mains[:, 2] > 0][:, 2]) - np.median(mains[mains[:, 2] < 0][:, 2])) if len(mains) else None)
    return out


# ---- source-glb pass: the model's own door and gear-door meshes, in the same normalised frame as convert()
DOOR_PAX = re.compile(r'^(Door[LR]\d|door\.[lr]\d$|door[FR][LR]$|LeftDoor$|RightDoor$)', re.I)   # passenger doors only (A320 family, E-Jets, A220-100, CRJ700/900)
DOOR_GEAR = re.compile(r'(GearN|nlg|NoseGearDoor|nosegrdoor|lhnosedoor|rhnosedoor|lhfnosedoor|rhfnosedoor|^nosedoor|geardoor\.f|lgdoor\.(left|right)\.front)|'
                       r'(GearLDoor|GearRDoor|LeftGearDoor|RightGearDoor|wlg_|lhgearibdoor|rhgearibdoor|lhibdoor|rhibdoor|lhfdoor|rhfdoor|gear[LR]door|lgeardoor|rgeardoor|'
                       r'geardoor\.b|(left|right)\.main\.door|^doors$|^door\dB)', re.I)


def source_features(key, fam):
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import convert_models as cm
    if key not in cm.MODELS: return None
    src, cfg = cm.MODELS[key]
    src = os.path.join(fam, os.path.relpath(src, cm.FAM))
    if not os.path.exists(src): return None
    prims, mats, images, textures = cm.glb_primitives(src)
    # --- identical to convert(): orientation, optional length scaling, shift so the nose is at x = 0
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    top = allp[np.argmax(allp[:, 1])]
    fx = (top[0] - lo[0]) / max(hi[0] - lo[0], 1e-6); fz = (top[2] - lo[2]) / max(hi[2] - lo[2], 1e-6)
    axis, tail_pos = cfg['axis'] if cfg.get('axis') else ((0 if abs(fx - 0.5) > abs(fz - 0.5) else 2), None)
    if tail_pos is None: tail_pos = (fx if axis == 0 else fz) > 0.5
    fwd = np.zeros(3); fwd[axis] = -1.0 if tail_pos else 1.0
    R = np.stack([fwd, [0, 1.0, 0], np.cross(fwd, [0, 1.0, 0])])
    for p in prims: p['pos'] = p['pos'] @ R.T
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0); L0 = hi[0] - lo[0]
    sc = cfg['length'] / L0 if cfg.get('length') else 1.0
    if abs(sc - 1) <= 0.03: sc = 1.0
    for p in prims: p['pos'] = p['pos'] * sc
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    ft = allp[allp[:, 1] > hi[1] - 0.03 * (hi[1] - lo[1])]; zc = float(np.median(ft[:, 2])); Lm = hi[0] - lo[0]
    fw = (allp[:, 0] < hi[0] - 0.17 * Lm) & (allp[:, 0] > hi[0] - 0.33 * Lm)
    col = allp[fw & (np.abs(allp[:, 2] - zc) < 0.35)]
    if len(col) < 40 or (np.percentile(col[:, 1], 99.5) - np.percentile(col[:, 1], 0.5)) < 1.0:
        col = allp[fw & (np.abs(allp[:, 2] - zc) < 1.0)]
    cy = (np.percentile(col[:, 1], 99.5) + np.percentile(col[:, 1], 0.5)) / 2; Rf = (np.percentile(col[:, 1], 99.5) - np.percentile(col[:, 1], 0.5)) / 2
    near = allp[(np.abs(allp[:, 2] - zc) < 0.6) & (np.abs(allp[:, 1] - cy) < Rf)]
    shift = np.array([float(near[:, 0].max()), cy, zc])
    feats = {}
    for p in prims:
        name = p['node'].split('|')[0]
        kind = 'pax' if DOOR_PAX.search(name) else ('gear' if DOOR_GEAR.search(name) else None)
        if not kind: continue
        q = p['pos'] - shift
        f = feats.setdefault(name, dict(kind=kind, pts=[]))
        f['pts'].append(q)
    out = []
    for name, f in feats.items():
        q = np.concatenate(f['pts'])
        out.append(dict(name=name, kind=f['kind'], x=float(-q[:, 0].mean()), x0=float(-q[:, 0].max()), x1=float(-q[:, 0].min()),
                        z=float(q[:, 2].mean()), y=float(q[:, 1].mean())))
    return sorted(out, key=lambda r: r['x'])


# ---- runtime tables and fits: js/aircraft/types.js (TYPES, SPEC) + js/aircraft/fit.js (mapping, model fits), run in node
NODE_DUMP = r"""
import { TYPES, SPEC } from './js/aircraft/types.js';
import { TYPE_MODELS, MODEL_BASE } from './js/aircraft/fit.js';
const o = { map: TYPE_MODELS, base: MODEL_BASE, types: {} };
for (const k in TYPES) { const T = TYPES[k]; if (k !== T.key) continue; const f = T.fit || null;
  o.types[k] = { name: T.name, L: T.L, R: T.R, Hc: T.Hc, cls: T.cls, span: T.wing.span, main: T.gear.main.map(g => g.x), track: T.track,
    nose: T.gear.nose.x, xMain: T.xMain, doors: T.doors, dock2: T.dock2, dockX1: T.dockX1, dockX2: T.dockX2, dockSill: T.dockSill,
    dockSill2: T.dockSill2, dockHW: T.dockHW, spec: SPEC[k] || null,
    fit: f && { model: f.model, base: f.base, s: f.s, plugs: f.plugs, stretch: f.stretch, seat: f.seat, door: f.door, renderedSpan: f.renderedSpan, renderedH: f.renderedH } };
}
console.log(JSON.stringify(o));
"""


def load_app():
    r = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', NODE_DUMP], cwd=ROOT, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


ZONE_NOFIN = (2, 3, 7)   # engine, gear, pylon (tools/convert_models.py ZONE)


def apply_stretch(P, Z, st):
    """Python port of js/live/models.js applyStretch (wing span fit, fin height fit, fuselage plugs), model units."""
    P = P.copy()
    if not st: return P
    W, F = st.get('wing'), st.get('fin')
    if W:
        az = np.abs(P[:, 2]); m = (P[:, 0] >= W['xMin']) & (az > W['z0'])
        add = np.where(az >= W['z1'], W['dz'], (az - W['z0']) * W['dz'] / (W['z1'] - W['z0']))
        P[m, 2] += np.sign(P[m, 2]) * add[m]
    if F:
        m = (P[:, 0] < F['xF']) & (P[:, 1] > F['yF']) & ~np.isin(Z, ZONE_NOFIN)
        P[m, 1] = F['yF'] + (P[m, 1] - F['yF']) * F['k']
    if st.get('cut1') is not None:
        x = P[:, 0].copy()
        P[x < st['cut2'], 0] -= st['d1'] + st['d2']
        P[(x >= st['cut2']) & (x < st['cut1']), 0] -= st['d1']
    return P


def xr_of(st, s):
    """model station (m aft of the nose, model units, unstretched) -> rendered metres aft of the nose"""
    def f(xa):
        x = -xa
        if st and st.get('cut1') is not None:
            if x < st['cut2']: x -= st['d1'] + st['d2']
            elif x < st['cut1']: x -= st['d1']
        return -x * s
    return f


def rendered(P, Z, head, fitd, T):
    """measure the model as the app renders it (after stretch, uniform scale and seating)"""
    st = fitd['stretch']; s = fitd['s']; Q = apply_stretch(P, Z, st)
    d = head['dims']; hasGear = d['hasGear']
    L = float(Q[:, 0].max() - Q[:, 0].min())
    Hc = -float(Q[:, 1].min()) * s if hasGear else T['Hc']     # placement(): gear models on their wheels, else T.Hc
    body = (Z == 0) & (np.abs(Q[:, 2]) < 0.3) & (Q[:, 0] < -0.1 * L) & (Q[:, 0] > -0.5 * L)
    out = dict(L=L * s, span=float(Q[:, 2].max() - Q[:, 2].min()) * s, H=Hc + float(Q[:, 1].max()) * s, Hc=Hc,
               crown=Hc + float(Q[body, 1].max()) * s if body.any() else None)
    if hasGear:
        g = Q[Z == 3]; bottom = g[g[:, 1] < g[:, 1].min() + 0.35]
        mains = bottom[bottom[:, 0] < -0.3 * L]; noses = bottom[bottom[:, 0] > -0.3 * L]
        out['gear'] = dict(main=-float(np.median(mains[:, 0])) * s if len(mains) else None, nose=-float(np.median(noses[:, 0])) * s if len(noses) else None,
                           track=(float(np.median(mains[mains[:, 2] > 0][:, 2])) - float(np.median(mains[mains[:, 2] < 0][:, 2]))) * s if len(mains) else None)
    return out


def pct(a, b): return None if a is None or b is None or not b else 100.0 * (a - b) / b


# explanations of flags that remain after the fixes (docs/research/aircraft_models_check.md §11 has the sources)
_E175_DOOR = ('source model: the FAM E175 has no door object; its door is the E170 model\'s door.l1 (vertex-identical nose, '
              'tools/models/model_features.py), scaled with the E175 model (s 1.028: the FAM E175 is 0.86 m short and is scaled '
              'uniformly), so the painted door is 0.41 m aft of the APM-derived centre (1L forward edge 4.71 m + 0.85/2, inf). '
              'The bridge docks at the painted door; the 3.1 m bellows covers both')
_B738_GEAR = ('source model: the FlightGear 737-800 model\'s own main gear is 0.43 m aft of the ACAP station (nose gear +0.23 m); '
              'TYPES, ground physics and gear contact use the ACAP station, the rendered wheels are the artist\'s')
EXPLAINED = {('E75L', 'door'): _E175_DOOR, ('E75L', 'dock'): _E175_DOOR, ('E75S', 'door'): _E175_DOOR, ('E75S', 'dock'): _E175_DOOR}
for _k in ('B736', 'B737', 'B738', 'B739', 'B37M', 'B38M', 'B39M', 'B3XM'): EXPLAINED[(_k, 'mgear')] = _B738_GEAR


# ----------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--md'); ap.add_argument('--json'); ap.add_argument('--tol', type=float, default=1.0)
    a = ap.parse_args(); tol = a.tol
    app = load_app(); TY = app['types']; MAP = app['map']
    feats = json.load(open(os.path.join(MODELS_DIR, 'features.json')))
    models = {}
    for fn in sorted(os.listdir(MODELS_DIR)):
        if fn.endswith('.sfom'):
            k = fn[:-5]; head, P, Z = load_sfom(os.path.join(MODELS_DIR, fn)); models[k] = (head, P, Z)
    rows, flags = [], []
    for icao in sorted(set(MAP) | set(REF)):
        tm = MAP.get(icao); ref = REF.get(icao)
        if not tm:
            rows.append(dict(icao=icao, note='not mapped: shown as a marker (no model, no verified airframe)')); continue
        t, mk = tm['t'], tm.get('m'); T = TY[t]; S = T['spec'] or {}
        refsrc = 'REF' if ref else 'SPEC'
        R = ref or dict(name=T['name'] + ' (no independent REF: checked against SPEC in types.js)', L=S.get('L'), span=S.get('span'), H=S.get('H'),
                        crown=S.get('crown'), nose=S.get('nose'), main=(S.get('main') or [None])[0], track=S.get('track'),
                        doors={i + 1: x for i, x in enumerate(S.get('doors') or [])}, sill1=S.get('sill'))
        r = dict(icao=icao, t=t, m=mk, ref=R['name'], refsrc=refsrc, cmp=[])
        def add(what, got, want, pos=False, key=None, inf=False):
            if got is None or want is None: return
            if isinstance(want, (list, tuple)):
                lo, hi = want; want = lo if got < lo else hi if got > hi else got
            dv = got - want; p = pct(got, want)
            bad = abs(dv) > 0.01 * tol * R['L'] if pos else abs(p) > tol
            c = dict(what=what, got=round(got, 2), ref=round(want, 2), delta=round(dv, 2), pct=None if pos else round(p, 1), flag=bool(bad), inf=inf)
            if bad: c['why'] = EXPLAINED.get((icao, key)) or EXPLAINED.get((icao, what))
            r['cmp'].append(c)
        src_inf = 'inf' in (R.get('src') or '')
        if mk and mk in models:
            head, P, Z = models[mk]; f = T['fit']
            rd = rendered(P, Z, head, f, T); r['render'] = rd; r['fit'] = f
            add('length (rendered)', rd['L'], R['L'])
            add('wingspan (rendered, after span fit)', rd['span'], R['span'], key='span')
            add('height (rendered fin top)', rd['H'], R.get('H'), key='H')
            add('fuselage top above ground (rendered)', rd['crown'], R.get('crown'), pos=True, key='crown')
            if rd.get('gear'):
                add('model main gear x (rendered) vs TYPES.xMain', rd['gear']['main'], T['xMain'], pos=True, key='mgear')
                add('model main gear x (rendered)', rd['gear']['main'], R.get('main'), pos=True, key='mgear')
                add('model nose gear x (rendered)', rd['gear']['nose'], R.get('nose'), pos=True, key='ngear')
            # the model's own L1 door object, as rendered, and the painted door the bridge meets
            F = feats.get(mk, {}); dm = next((d for d in F.get('doors', []) if d['side'] == 'L'), None)
            if not dm:
                for o in F.get('sameNose', []):
                    dm = next((d for d in feats.get(o, {}).get('doors', []) if d['side'] == 'L'), None)
                    if dm: break
            if dm:
                xr = xr_of(f['stretch'], f['s'])
                r['modelDoor'] = dict(name=dm['name'], x=round(xr(dm['x']), 3), sill=round(rd['Hc'] + dm['ySill'] * f['s'], 3))
                add(f"model's own L1 door object {dm['name']} (rendered centre)", r['modelDoor']['x'], R.get('doors', {}).get(1), pos=True, key='door', inf=src_inf)
                add(f"model's own L1 door sill (rendered)", r['modelDoor']['sill'], R.get('sill1'), pos=True, key='doorsill')
                add('bridge dock x = rendered door object', T['dockX1'], r['modelDoor']['x'], pos=True, key='dockmesh')
        else:
            r['procedural'] = True
            add('wingspan (procedural TYPES)', T['span'], R['span'], key='span')
        add('length (TYPES L)', T['L'], R['L'])
        add('wingspan (TYPES: ground physics, far LOD)', T['span'], R['span'], key='tspan')
        if R.get('nose') is not None: add('nose gear x (TYPES)', T['nose'], R['nose'], pos=True)
        if R.get('main') is not None: add('main gear x (TYPES, first unit)', T['main'][0], R['main'], pos=True)
        if icao in WHEELBASE: add('wheelbase (TYPES)', T['main'][0] - T['nose'], WHEELBASE[icao], pos=True)
        if R.get('track'): add('main-gear track (TYPES)', T['track'], R['track'])
        dr = R.get('doors', {})
        if 1 in dr: add('bridge dock x, door 1L centre', T['dockX1'], dr[1], pos=True, key='dock', inf=src_inf)
        if T['dock2']:
            add(f"bridge 2 dock x, door {T['dock2']}L centre", T['dockX2'], dr.get(T['dock2']), pos=True, key='dock2')
        if T['cls'] in ('E', 'F') and not T['dock2']: r['note'] = 'wide-body without a documented second-bridge door: one bridge'
        add('bridge cab floor vs door 1L sill', T['dockSill'], R.get('sill1'), pos=True, key='sill')
        for c in r['cmp']:
            if c['flag']: flags.append((icao, c))
        rows.append(r)
    # ---- print
    print(f'ICAO type checks (rendered / used by the app vs the manufacturer documents; flag: |%| > {tol} % or position error > {tol} % of L)')
    for r in rows:
        if 'cmp' not in r: print(f"  {r['icao']}: {r.get('note')}"); continue
        f = r.get('fit') or {}
        print(f"  {r['icao']} -> TYPES {r['t']} / model {r['m']}  [{r['refsrc']}: {r['ref']}]  s={f.get('s')} seat={f.get('seat')} "
              f"plugs={f.get('plugs') and (f['plugs']['d1'], f['plugs']['d2'], f['plugs']['by'])} wing={f.get('stretch') and f['stretch'].get('wing') and f['stretch']['wing']['dz']} "
              f"fin={f.get('stretch') and f['stretch'].get('fin') and f['stretch']['fin']['k']}" + (f"  NOTE: {r['note']}" if r.get('note') else ''))
        for c in r['cmp']:
            mark = '!!' if c['flag'] and not c.get('why') else ('~~' if c['flag'] else '  ')
            print(f"      {mark} {c['what']:58s} {c['got']:8.2f} vs {c['ref']:8.2f}  d={c['delta']:+6.2f}" + (f"  {c['pct']:+5.1f}%" if c['pct'] is not None else '')
                  + (' (ref inf)' if c.get('inf') else '') + (f"   <- {c['why']}" if c.get('why') else ''))
    unexpl = [x for x in flags if not x[1].get('why')]
    print(f'\n{len(flags)} flagged items, {len(flags) - len(unexpl)} explained (~~), {len(unexpl)} unexplained (!!)')
    if a.json: json.dump(dict(rows=rows), open(a.json, 'w'), indent=1, default=float)
    if a.md:
        with open(a.md, 'w') as fo:
            fo.write('| ICAO | TYPES / model | check | app | ref | Δ | % | note |\n|---|---|---|---|---|---|---|---|\n')
            for r in rows:
                for c in r.get('cmp', []):
                    pc = '' if c['pct'] is None else '%+.1f' % c['pct']
                    fo.write(f"| {r['icao']} | {r['t']} / {r['m']} | {c['what']} | {c['got']} | {c['ref']} | {c['delta']:+.2f} | {pc} {'**!**' if c['flag'] else ''} | {c.get('why') or ''} |\n")
    return 1 if unexpl else 0


if __name__ == '__main__':
    sys.exit(main())
