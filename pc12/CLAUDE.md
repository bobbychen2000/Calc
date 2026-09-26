# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (71 parts, ~750k tris, hinge pivots in node
extras), `out/pc12_meta.json` (build steps, BOM, construction lines, dimension checks),
`out/drawings/L1..L5` (the Stage-2 drawing set, drawn from the parameters: `python3 -m drawing.master`),
`out/pc12_ga.svg|pdf` (legacy A1 GA, hidden-line from the mesh) and `out/pc12_sections.svg|pdf` (A2 sections).

## Commands
```bash
pip install numpy scipy matplotlib pillow reportlab playwright   # lxml optional
python3 model/build.py          # build all parts -> out/pc12.glb + out/pc12_meta.json + prints 10 dimension checks
python3 test/fit_check.py       # interference / kinematics checks (interior + engine in the skin, spinner at the cowl,
                                #   carry-through under the floor, tail / rudder clearances, retracted gear, brace knees,
                                #   exact triangle-crossing sweeps (test/isect.py): main gear + brace in the bay liner,
                                #   nose gear vs doors / flight deck, flaps + canoes, rudder); '[open]' rows are known
                                #   conflicts in the approved parameters that need an owner decision (they do not fail)
python3 test/consistency_2d3d.py   # the built GLB projected / sliced against the parameter outlines of sheets L1-L5
python3 -m drawing.master       # the Stage-2 drawing set L1-L5 from the parameter modules (~2.5 min)
python3 -m drawing.sheet        # hidden-line drawings (~30 s) -> out/pc12_ga.*, out/pc12_sections.*
python3 -m drawing.verify       # measures the SVG itself against the dimensions
# dev viewer (three.js r160 expected at web/three_local -> a checkout of mrdoob/three.js tag r160):
python3 -m http.server 8765 --directory .   # then test/shot.py renders headless screenshots:
python3 test/shot.py out/x.png "f=../out/pc12.glb&cam=-9,4,-3&tgt=0,1.4,6.6&fov=40"
#   options: ortho=1&s=HALF_HEIGHT, only=part_prefix,.., hide=.., clip=1 (cutaway), f2=other.glb&f2edges=1
```

## Method (owner's directive: drawings first, then 3D, then rendering)
Work in this order and don't skip ahead:
1. **Reference drawings** — the Pilatus drawing 190.10.40.432 (NGX Model Building Plan p. 8/9, registered into
   model coordinates by `refs/mbp.py`) and camera-matched photos (`refs/photos.json`).
2. **Our 2-D drawing set, drawn from the parameters** (the same control lines / outline tables the 3-D builder
   uses, not from the mesh): lines plan (profile, half-breadth, body plan at the Pilatus frames), cockpit glazing +
   PRO mask detail, general layout (doors, windows, wing, tail, gear, prop), livery profiles. Each sheet is
   overlaid on the Pilatus drawing with deviation call-outs; iterate the parameters until it fits, and get the
   owner's review before moving on.
3. **3-D build** from the approved parameters (`model/build.py`), then check the mesh projects back onto the 2-D set.
4. **Rendering** — Blender (`/opt/venv-blender`, Cycles) beauty renders and the three.js viewer.
The repo is public: Pilatus drawings, photos and data extracted from them live only in the gitignored `refs/cache/`.

## Coordinates & conventions
- Model axes (Python): **x = fuselage station, m aft of the W&B datum** (datum = 3.000 m ahead of the
  firewall, per POH), **y = butt line (+ starboard)**, **z = water line (ground = 0, static on gear)**.
- glTF / three.js axes: X = y, Y = z, Z = x (cyclic permutation, see `cad/glb.py:to_gl`).
- Spinner tip STA 0.39, aft-most point STA 14.79 (length 14.40). Prop axis WL 1.655 at the disc (STA 0.925);
  thrust line 2° nose-down, 2° right (`powerplant.thrust_dir/axis_point`); engine, spinner and prop sit on it.
- The fuselage loft is defined only on STA 1.044 (cowl front) .. 13.57 (tail end): `fuselage.STRICT` makes an
  evaluation outside that range raise; take x-ranges from `F.STA` / `OML.x0/x1`. The tail cone is cut at the rudder
  leading edge (`empennage.tail_cut_*`, chord line 0.6216) and closed by a bulkhead; the rudder runs behind it.
- Cabin floor `fuselage.CABIN_FLOOR_WL` 1.259 (crown − 0.040 lining − 1.47); the wing carry-through is flattened to
  ≤ floor − 15 mm inside the fuselage (`wing.centre_section_clamp`).
- Movable parts carry `extras.pivot = {origin, axis (gl), kind, ...}`: kinds `spin` (propeller),
  `pitch` (blades: feather/reverse deg), `flap` (Fowler: rotate + `travel`), `aileron`, `elevator`,
  `rudder`, `trim` (stabiliser), `tab` (`gearing` × parent deflection), `door` (`open` rad),
  `gear` (`retract` deg), `gear_door` (`open` deg = closed -> open, `rest` = the door fraction the geometry is
  built at), `brace` (two-link over-centre strut: upper link rotates about A, lower link about knee K0; solve the knee
  with `model/brace.py:solve_knee`, the leg attach point B0 moves with the parent `gear` node). Geometry is built
  gear-down, cabin doors closed; the nose-gear clamshells are built OPEN (`rest` 1: they hang open beside the leg
  whenever the gear is down or travelling and close only once it is locked up, photo s/n 3001), so a node's rotation
  is `open * (door - rest)`. Parts without a pivot may be children of a moving part (the aft flap-track canoes
  `flap_canoes_R/L` ride on the flaps).

## Layout
- `cad/mesh.py` kernel: `grid_surface`, `trim` (marching-triangles implicit trimming), `band`,
  `boundary_loops`, `solidify`, `revolve`, `sweep_profile/tube`, `superellipsoid`, `planar_cap`.
  **Gotcha:** when trimming twice, re-evaluate the field on the trimmed mesh (use `band()`/`trim_fn`).
- `cad/glb.py` glTF writer with KHR_mesh_quantization; `cad/sdf2d.py` 2-D signed distances.
- `model/fuselage.py` OML lofted from control lines (crown, keel, half-breadth, max-breadth WL) +
  super-ellipse section law. `fuselage_parts.py` cuts skins/doors/windows; `cockpit_glazing.py`
  defines windshield / side windows / dark surround as signed-distance constraints.
- `model/wing.py` planform from the Pilatus drawing, root chord solved so that the TOTAL projected plan area
  (both halves through the fuselage, aileron kink, winglets' plan projection: `planform_area()`) is 25.81 m²:
  MAC 1.724, LEMAC STA 5.462 (the POH aft CG 6.107 = 37 % MAC), dihedral 6.23° from BL 0.70 (flat centre
  section). Airfoils `model/airfoil.py` (CST fits of the drawn LS(1)-0417MOD/0313 sections). Also Fowler flap
  (3-D body from BL 0.92, outboard of the belly fairing), constant-chord aileron + Flettner tab, winglet
  canted 51° from vertical (straight part lengthened to the official span).
- `model/empennage.py` (fin + ventral fairing, dorsal + root fillet, rudder with sloped edges, tail-cone closure,
  tailplane horn balances split off the fixed tips along the drawn horn gap and carried by the elevators),
  `powerplant.py` (PT6E-67XP modules + Hartzell 5-blade prop, chin inlet cut into the OML keel step, scarfed
  stacks), `gear.py` (+ `bays.py`, `brace.py`; nose retracts 105° into a tunnel under the pedestal, unequal-link
  braces), `interior.py` (flight deck, cabin on CABIN_FLOOR_WL, frames at the Pilatus frame stations),
  `details.py` (wing-to-body fairing: flat-bottomed belly fairing + upper root fillet / fairing nose built as a
  horizontal offset of the OML, so its side / plan outlines are the drawn ones; flap-track canoes split at the cove lip
  into a fixed forward part and an aft part carried by the flap; lights, antennas, pod),
  `livery.py` (PC-12 PRO MSN 3008 scheme; the 3-D painter trims with one-sided smooth fields so thin strokes stay
  continuous; zero-area slivers from trims are dropped by `cad/glb.py`; per-surface bands -- wing / tailplane boots,
  winglet pinstripe, blade tip bands about the thrust axis, blade LE erosion strip -- are cut with sequential
  single-sided trims, never one V-shaped max() field), `build.py` (steps + verification),
  `drawing/` (Stage-2 sheets L1-L5 via `drawing.master`; legacy HLR GA via `drawing.sheet`).

## Sourced facts (keep these fixed)
Pilatus PC-12 PRO/NGX facts: span 16.28, length 14.40, height 4.26, wing area 25.81 m², tail span 5.20,
track 4.53, cabin 5.16×1.52×1.47 (floor 1.30), passenger door 0.61×1.35, cargo door 1.35×1.32,
prop 2.67 m 5-blade Hartzell composite (EASA TCDS: HC-E5A-31A/NC10245B), prop clearance 0.32.
POH NGX: datum 3.0 m fwd of firewall; three-view wheelbase 3.48; gear electromechanical, trailing-link
mains retract inward with ONE leg-mounted door each, tyres protrude ~1 in when retracted; nose retracts
aft, enclosed by doors; over-centre two-piece folding struts; ailerons with Flettner geared balance
tabs (opposite motion), elevator in two halves, rudder single piece, stabiliser trim (LE down = nose up).
Jane's: airfoils LS(1)-0417MOD root / LS(1)-0313 tip, Fowler flaps 67 % of TE, T-tail, bullet fairing,
dorsal fin + ventral strakes, tyres 22×8.50-10 / 17.5×6.25-6, NWS ±60°, exit right over wing (Jane's says
Type III; the Pilatus drawing shows a 0.48 × 0.64 m plug hatch, which the model follows).
EASA TCDS IM.E.008: PT6E-67XP length 1,870.9 mm, diameter 481.8 mm, 2-stage RGB, 2-stage PT, 1-stage
CT, 4 axial + 1 centrifugal compressor. PC-12 PRO: pilot's direct-vision window deleted; Garmin
G3000 PRIME (3×14-in + 2×7-in touch displays); PC-24-style yokes; radome enlarged for 12-in GWX 8000.
NGX: cabin windows rectangular (PC-24 style), 10 % larger; dark windshield surround trim.
POPA variant guide: "PC-21 style winglets" from Series 10A (MSN 684+). Weather-radar pod on right wing.

## Estimated / reconstructed (open to correction)
Fuselage contours between anchors (fitted to the Pilatus drawing, RMS 1-2 mm), windshield & side-window
outlines (fitted to the drawing, checked on PRO photos), winglet height (lengthened for the official span),
incidence/washout, airfoil ordinates, engine module proportions inside the TCDS envelope, interior layout,
nose-gear stowage tunnel and brace link split, livery details (camera-matched photos).

## Status / next steps
- Stage 1-2 done: reference drawings registered, drawing set L1-L5 approved (3 review rounds).
- Stage 3 (3-D build from the approved parameters): `model/build.py` consumes the Stage-2 parameters end to end;
  `test/fit_check.py`, `test/viewer_test.py`, `drawing.sheet/verify` and `drawing.master` pass. Known open items
  (not modelled / needing an owner decision): the drawn fairing tail lobe aft of the cargo-door seam (STA 7540-8585,
  it overlaps the D2 panel; the root fillet fades out ahead of the seam instead); cargo-door gas struts; dihedral:
  decision D4 quotes 6.15 deg, the approved L4 / wing.py value (rev B airfoils) is 6.23 deg, which the model uses.
- Main-gear leg door, decision LD-1 (owner-delegated, resolved; model/gear.py comment block): the door is the wing
  lower skin carried down by the leg (`gear.leg_door_offset`), so retracted it closes flush (1 mm recess, 3 mm panel
  gap, `bays.DOOR_GAP`) and the tyre protrudes 26 mm in its own round well (`bays.well_sdf`); drawn side-view face
  kept, scalloped round the tyre (R 292) plus a tab hidden in the slot over the leg's skin crossing
  (`gear.leg_door_face`); edge-on it stands at BL 2334-2383 instead of the drawn 2358-2472 lean (call-out on L4).
  Hidden changes: trunnion STA 5978 / WL 1155 (drawn leg top 5932 / 1070), retraction 86 deg (stowed wheel along
  the ~7 deg skin), side-brace stations 6040 / 6038 and L1 split 0.19, no forward slot; liner-only pockets
  (`bays.TRUNNION_POCKET`, `BRACE_POCKET`), a black seal band on the lowest 60 mm of the main-bay liner, and a finer
  wing lower skin over the bay (wing.py sub-panel) so the cut-out corners are cut within a few mm. fit_check 5 / 10
  test flushness, protrusion (20-30 mm), the closed cut-out and every pose of the swing.
- Stage 4: Blender (Cycles) beauty renders (`render/blender_ortho.py` for calibrated views) and the three.js
  viewer (`web/`, three.js r160 in `web/three_local`).
