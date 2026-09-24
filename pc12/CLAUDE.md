# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (69 parts, ~450k tris, hinge pivots in node
extras), `out/pc12_meta.json` (build steps, BOM, construction lines, dimension checks),
`out/pc12_ga.svg|pdf` (A1 general arrangement) and `out/pc12_sections.svg|pdf` (A2 sections).

## Commands
```bash
pip install numpy scipy matplotlib pillow reportlab playwright   # lxml optional
python3 model/build.py          # build all parts -> out/pc12.glb + out/pc12_meta.json + prints 10 dimension checks
python3 test/fit_check.py       # interference check: interior/engine must lie inside the fuselage skin
python3 -m drawing.sheet        # hidden-line drawings (~30 s) -> out/pc12_ga.*, out/pc12_sections.*
python3 -m drawing.verify       # measures the SVG itself against the dimensions
# dev viewer (three.js r160 expected at web/three_local -> a checkout of mrdoob/three.js tag r160):
python3 -m http.server 8765 --directory .   # then test/shot.py renders headless screenshots:
python3 test/shot.py out/x.png "f=../out/pc12.glb&cam=-9,4,-3&tgt=0,1.4,6.6&fov=40"
#   options: ortho=1&s=HALF_HEIGHT, only=part_prefix,.., hide=.., clip=1 (cutaway), f2=other.glb&f2edges=1
```

## Coordinates & conventions
- Model axes (Python): **x = fuselage station, m aft of the W&B datum** (datum = 3.000 m ahead of the
  firewall, per POH), **y = butt line (+ starboard)**, **z = water line (ground = 0, static on gear)**.
- glTF / three.js axes: X = y, Y = z, Z = x (cyclic permutation, see `cad/glb.py:to_gl`).
- Spinner tip STA 0.39, aft-most point STA 14.79 (length 14.40). Prop axis WL 1.655.
- Movable parts carry `extras.pivot = {origin, axis (gl), kind, ...}`: kinds `spin` (propeller),
  `pitch` (blades: feather/reverse deg), `flap` (Fowler: rotate + `travel`), `aileron`, `elevator`,
  `rudder`, `trim` (stabiliser), `tab` (`gearing` × parent deflection), `door` (`open` rad),
  `gear` (`retract` deg), `gear_door` (`open` deg), `brace` (two-link over-centre strut: upper link
  rotates about A, lower link about knee K0; solve the knee with `model/brace.py:solve_knee`, the
  leg attach point B0 moves with the parent `gear` node). Geometry is built gear-down, doors closed.

## Layout
- `cad/mesh.py` kernel: `grid_surface`, `trim` (marching-triangles implicit trimming), `band`,
  `boundary_loops`, `solidify`, `revolve`, `sweep_profile/tube`, `superellipsoid`, `planar_cap`.
  **Gotcha:** when trimming twice, re-evaluate the field on the trimmed mesh (use `band()`/`trim_fn`).
- `cad/glb.py` glTF writer with KHR_mesh_quantization; `cad/sdf2d.py` 2-D signed distances.
- `model/fuselage.py` OML lofted from control lines (crown, keel, half-breadth, max-breadth WL) +
  super-ellipse section law. `fuselage_parts.py` cuts skins/doors/windows; `cockpit_glazing.py`
  defines windshield / side windows / dark surround as signed-distance constraints.
- `model/wing.py` planform **solved** from span 16.28 m, area 25.81 m², taper 0.5 and the POH aft CG
  limit (6.107 m = 46 % MAC) → LEMAC STA 5.323. Airfoils `model/airfoil.py` (LS(1)-0417MOD/0313
  reconstructions). Also Fowler flap, aileron + Flettner tab, blended winglet.
- `model/empennage.py`, `powerplant.py` (PT6E-67XP modules + Hartzell 5-blade prop), `gear.py`
  (+ `bays.py`, `brace.py`), `interior.py` (flight deck, cabin, structure), `details.py`,
  `livery.py` (original scheme, trimmed into skins), `build.py` (steps + verification),
  `drawing/` (HLR + sheets; written by a sub-agent).

## Sourced facts (keep these fixed)
Pilatus PC-12 PRO/NGX facts: span 16.28, length 14.40, height 4.26, wing area 25.81 m², tail span 5.20,
track 4.53, cabin 5.16×1.52×1.47 (floor 1.30), passenger door 0.61×1.35, cargo door 1.35×1.32,
prop 2.67 m 5-blade Hartzell composite (EASA TCDS: HC-E5A-31A/NC10245B), prop clearance 0.32.
POH NGX: datum 3.0 m fwd of firewall; three-view wheelbase 3.48; gear electromechanical, trailing-link
mains retract inward with ONE leg-mounted door each, tyres protrude ~1 in when retracted; nose retracts
aft, enclosed by doors; over-centre two-piece folding struts; ailerons with Flettner geared balance
tabs (opposite motion), elevator in two halves, rudder single piece, stabiliser trim (LE down = nose up).
Jane's: airfoils LS(1)-0417MOD root / LS(1)-0313 tip, Fowler flaps 67 % of TE, T-tail, bullet fairing,
dorsal fin + ventral strakes, tyres 22×8.50-10 / 17.5×6.25-6, NWS ±60°, Type III exit right over wing.
EASA TCDS IM.E.008: PT6E-67XP length 1,870.9 mm, diameter 481.8 mm, 2-stage RGB, 2-stage PT, 1-stage
CT, 4 axial + 1 centrifugal compressor. PC-12 PRO: pilot's direct-vision window deleted; Garmin
G3000 PRIME (3×14-in + 2×7-in touch displays); PC-24-style yokes; radome enlarged for 12-in GWX 8000.
NGX: cabin windows rectangular (PC-24 style), 10 % larger; dark windshield surround trim.
POPA variant guide: "PC-21 style winglets" from Series 10A (MSN 684+). Weather-radar pod on right wing.

## Estimated / reconstructed (open to correction)
Fuselage contours between anchors, windshield & side-window outlines (cross-checked only against an
independent FlightGear PC-12 model, FGMEMBERS/PC-12 — NOT yet against real photos), winglet
cant 30°/sweep/height, dihedral 4.5°, incidence/washout, airfoil ordinates, fin/stab planform details,
engine module proportions inside the TCDS envelope, interior layout, livery.

## Status / next steps
1. **Cockpit glazing vs real photos** — the user wants the windshield and side-window panes checked against
   actual PC-12 PRO images and design drafts (e.g. Pilatus PC-12 PRO page photos, the official
   "PC-12 NGX Model Building Plan" PDF on pilatus-aircraft.com). The previous sandbox could not download
   images. Overlay photos on orthographic renders and adjust `model/cockpit_glazing.py` (WS_PLAN,
   PILLAR, SW_*), and possibly the nose control lines in `model/fuselage.py`.
2. **Interactive viewer (not built yet)** — three.js page loading `out/pc12.glb` + `out/pc12_meta.json`:
   step-by-step build (construction lines first, then parts fly in; skins in primer until the final
   "paint" step), explode slider, cutaway (clip skins at y<0; back faces as cabin lining), X-ray
   (show `structure`), animations from the pivot extras (prop spin + feather, gear with brace IK and
   the leg door, Fowler flaps 0/15/30/40, doors, controls + geared tabs, stabiliser trim), part
   picking with BOM info, Drawings tab (embed `out/pc12_ga.svg`), Specs tab (checks + sources).
3. Optional: import `out/pc12.glb` into Blender for rendering / further detailing.
