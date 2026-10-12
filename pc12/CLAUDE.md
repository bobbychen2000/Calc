# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (98 parts, ~2.67M tris of which the interior ~825k, ~47 MB
incl. the 0.5 MB G3000 page atlas and the interior's baked occlusion / window light `_AO`, 16-bit normals; built at the tessellation quality `PC12_RES` = 2, `cad/res.py`;
hinge pivots in node extras), its light tier `out/pc12_low.glb` (the builders' own grids, `PC12_RES=1`, as judged in
review, but its seats, yokes, pedals, braces, nose leg and the flight deck as in the full model -- `build.LOW_FINE`: ~2.25M
tris, ~40 MB,
16-bit normals too; phones load it (and its gzip when
WebAssembly is refused), the Specs panel -- and once a stage chip on capable devices -- offer the full model there), `out/pc12_meta.json` (build steps, BOM, construction lines, dimension checks; `stats.low` = the light tier),
`out/drawings/L1..L6B` (the Stage-2 drawing set, drawn from the parameters: `python3 -m drawing.master`; L1-L5 the
exterior -- lines plan, glazing, openings, general arrangement, L4W wheels & tyres (`model/wheels.py` tables), livery
--, L6 / L6B the interior arrangement and its checks),
`out/pc12_ga.svg|pdf` (legacy A1 GA, hidden-line from the mesh) and `out/pc12_sections.svg|pdf` (A2 sections).

## Commands
```bash
pip install numpy scipy matplotlib pillow reportlab playwright   # lxml optional
python3 model/build.py          # build all parts -> out/pc12.glb + out/pc12_meta.json + prints 10 dimension checks
                                #   (~75 s; the light tier out/pc12_low.glb is built alongside at PC12_RES=1 in a second
                                #   process, --no-low skips it; PC12_RES=1 python3 model/build.py --no-low gives the
                                #   judged model byte for byte but for the shared quantisation grids)
python3 test/fit_check.py       # interference / kinematics checks (interior + engine in the skin, spinner at the cowl,
                                #   carry-through under the floor, tail / rudder clearances, retracted gear, brace knees,
                                #   exact triangle-crossing sweeps (test/isect.py): main gear + brace in the bay liner,
                                #   nose gear vs doors / flight deck, flaps + canoes, rudder; interior 17-21: seats
                                #   inside the lining / on the floor / on their tracks, 95th-pct knees vs the yokes,
                                #   furniture clear of windows / door + exit openings, door swings vs the interior,
                                #   the frames, skins and belly fairing (door travel every 0.02 and every 0.005
                                #   inside each handrail's unfold window); 22 every interior piece seated (within
                                #   3 mm of, or crossing, another surface), 22b lining fittings >= 0.5 mm proud of
                                #   the lining, 22c curtain vs crew tracks; 23 closed interior shells wound outward,
                                #   vertex normals with the face winding; 24 crew harness on the fleece, 25 armrests
                                #   vs the pedestal over the seat travel, 26 no coplanar overlaps of different
                                #   materials, 27 the PDU bezel tops visible from both design eyes, (fit_fd_b) 32 the
                                #   flight-deck floor closed in plan; the main-gear leg
                                #   door vs the skin cut-out every 0.5 % over 90-100 %, flush outside its tyre blister);
                                #   '[open]' rows are known conflicts in the approved parameters that need an owner
                                #   decision (they do not fail)
python3 test/consistency_2d3d.py   # the built GLB projected / sliced against the parameter outlines of sheets L1-L6
                                #   (L4W: wheels / tyres / nose yoke, 2 mm)
python3 -m drawing.master       # the Stage-2 drawing set L1-L6B incl. L4W from the parameter modules (~3 min;
                                #   `python3 -m drawing.master L6 L6B` for the interior sheets only, `L4W` the wheels)
python3 -m drawing.sheet        # hidden-line drawings (~30 s) -> out/pc12_ga.*, out/pc12_sections.*
python3 -m drawing.verify       # measures the SVG itself against the dimensions
# dev viewer (three.js r160 expected at web/three_local -> a checkout of mrdoob/three.js tag r160):
python3 -m http.server 8765 --directory .   # then test/shot.py renders headless screenshots:
python3 test/shot.py out/x.png "f=../out/pc12.glb&cam=-9,4,-3&tgt=0,1.4,6.6&fov=40"
#   options: ortho=1&s=HALF_HEIGHT, only=part_prefix,.., hide=.., clip=1 (cutaway), f2=other.glb&f2edges=1
python3 test/viewer_test.py     # viewer checks + screenshots (headless Chromium / SwiftShader, ~60-85 min, 225 checks; slower on a
                                #   loaded machine -- rerun once on a screenshot / click timeout); [T1]-[T18] the interior tour
                                #   (--only tour: those alone on the desktop page, ~6 min; --only prop / phone / picture / sound likewise;
                                #   --only fdlook: [FD-L1]-[FD-L9] the flight-deck look, ~20 min)
python3 test/viewer_test.py --only sound --sound-out DIR   # the engine-sound section alone (~2 min): its checks + the
                                #   offline renders DIR/pc12_engine_sequence.wav + spectrogram.png, pc12_sound_loudest /
                                #   _close_idle / _steady / _pilot.wav (default out/tmp/viewer/sound)
python3 web/package.py          # static viewer bundle -> dist/ (gitignored): meshopt GLBs (both tiers; the build's own
                                #   quantisation kept: gltf-transform's API, reorder + EXT_meshopt_compression), vendored
                                #   three.js, verify step
python3 web/package_artifact.py --out DIR && python3 test/artifact_test.py --dir DIR   # the claude.ai Artifact bundle
                                #   (~116 MB as base64 text parts: meshopt 18 + 16 MB, gzip of the full model 27 MB for desktops and of
                                #   the light tier 23 MB for phones without WebAssembly, every part <= 10.4 MB; two publishes 62.8 + 53.6 MB; ARTIFACT.json 'publishes' = groups of <= 64 MB,
                                #   one publish call each to the same url)
python3 web/tour_data.py        # interior tour data web/viewer/tour_data.js from the interior tables (--check: current?)
python3 render/beauty.py --preset cockpit_fwd,panel_faceon,cabin_aft_fwd,cabin_club --size 1000x750 --compare
                                # interior renders (Blender / Cycles; cameras of the photo presets fitted in
                                #   refs/cache/overlays/vqa/cams_beauty.json, compare sheets land there too)
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
  built at), `fold` (pieces moved by a door's travel, `follows` the door: rotate about their own axis by
  `curve`(door fraction) -- an angle table at `airstair.N_MOTION` + 1 even steps of the eased door fraction -- or by
  `open` x clamp((door fraction - window[0]) / (window[1] - window[0])); the airstair handrail's lower rod
  `door_airstair_rail` (the door's child) and the sleeve `door_airstair_rail_sleeve` (a fuselage part pivoting on the
  jamb bracket)), `stretch` (also scaled by `scale`(door fraction) along the built unit direction `dir` about the
  origin: the telescoping upper rod `door_airstair_rail_up`, the lower rod's child, and the restraint cables
  `door_airstair_cable`, the door's child; `joints` = their pinned ends in the built pose for tests),
  `yoke` (`yoke_L` / `yoke_R`, children of `flight_deck`: roll = roll command x `roll_deg` about the forward-pointing
  column axis, + `travel_pull` / `travel_push` (MODEL axes) x |pitch command|), `pedal` (`pedal_LL/LR/RL/RR`: hanging
  pedals, about the arm pivot under the lower panel (axis -y) by -`gearing` x yaw command x `travel_deg`;
  `flightdeck.control_pivots`), `steer` (`gear_nose_steer`, child of `gear_nose`: the steering collar, torque links,
  piston, fork and nose wheel turn about the strut axis by yaw command x `pedal_deg` (12) while the gear is down and
  locked, centred as it leaves the lock; `max_deg` 60 = the castoring range, `gear.NOSE_STEER`),
  `table` (club tables `table_club_p` / `table_club_s`, children of `cabin_interior`: open 0 = stowed -- slid
  outboard by `slide` (MODEL axes) into the ledge, the viewer clips it at the fascia plane |BL| = `fascia_bl` --,
  `rest` 0.5 = the outboard leaf out (the built pose), 1 = deployed; translation = `slide` x (s(min(1, open / 0.5)) -
  s(rest / 0.5)), s the smoothstep), `table_leaf` (`table_club_*_leaf`, child of its table: the inboard leaf, built
  folded under it, unfolds by `fold` rad about its own axis over open 0.5 .. 1; `model/cabin.py` table_parts),
  `brace` (two-link over-centre strut: upper link rotates about A, lower link about knee K0; solve the knee
  with `model/brace.py:solve_knee`, the leg attach point B0 moves with the parent `gear` node). Geometry is built
  gear-down, cabin doors closed; the nose-gear clamshells are built OPEN (`rest` 1: they hang open beside the leg
  whenever the gear is down or travelling and close only once it is locked up, photo s/n 3001), so a node's rotation
  is `open * (door - rest)`. Parts without a pivot may be children of a moving part (the aft flap-track canoes
  `flap_canoes_R/L` ride on the flaps).

## Layout
- `cad/mesh.py` kernel: `grid_surface`, `trim` (marching-triangles implicit trimming), `band`,
  `boundary_loops`, `solidify`, `revolve`, `sweep_profile/tube`, `superellipsoid`, `planar_cap`.
  **Gotcha:** when trimming twice, re-evaluate the field on the trimmed mesh (use `band()`/`trim_fn`).
  The round primitives (revolve, disk, circle2d / sweep_tube, superellipsoid, cylinder) take their segment count
  through `cad.res.seg` (up to RES x the builder's n where the chord sagitta exceeds 0.04 mm; n < 8 = polygons by
  design, kept), so a builder that relies on a primitive's vertex count must not assume n.
- `cad/res.py` the ONE tessellation-quality setting `PC12_RES` (env; default 2, 1 = the judged grids): seg() above
  (not inside `res.coarse()`: the hidden engine modules, mount and firewall keep their own grids and are not refined;
  `with res.override(2.0):` builds / refines at RES 2 whatever PC12_RES is -- the light tier's `build.LOW_FINE` parts),
  `res.factor()` for builders whose own grids were coarse where it shows (1 at RES 1, RES above: the seats' pillow rims
  `seats._rounds`, outline arcs `_arc_k`, sheepskin pad grids `_sk_h`, back outline samples; the chin-inlet duct entry
  rings `powerplant._densify_rings`), the refinement settings per viewing class (silhouette sagitta exterior 0.30 mm /
  interior 0.35 mm, facet turn 20 deg above 0.03 / 0.02 mm of bow, bow ceilings 6 / 1 mm -- interior 1 mm: at 4 mm a
  crew seat's base plate bowed 1.4 mm into the floor), triangle budgets in proportion (`budget(n, scale)`: x1.75 at
  RES 2 -- `wheels.TRI_BUDGET`; `build.INTERIOR_BUDGET` total x2.2, crew seat x3.4, cabin seat x2.9), 16-bit GLB
  normals in both tiers (`normal_bits()`: 8-bit normals broke the studio's reflected streaks on the clear-coated paint
  and the cockpit side windows into stairs -- the visible part of the first upgrade, review r1 RES1-02).
  `cad/refine.py` curvature-adaptive refinement: an edge is split where the PN-triangle cubic through its end points /
  normals bows more than the tolerance, or its end normals turn more than `turn_deg` (the new vertex on that curve:
  the smooth surface between two samples of the analytic one; original vertices never move); conforming 1->2/3/4
  splits across all meshes of a part (welded by position, so paint / patch boundaries stay watertight); open boundaries,
  creases / folds, flat faces carrying corner-averaged normals, kinked profiles drawn with averaged normals (an S in an
  edge), slivers and bows over the ceiling are kept as built -- these guards are what keeps fit_check / the consistency
  sheets passing (a seat skid sagged 3 mm into the floor, a clamped carry-through rose 0.7 mm, a fairing nose folded
  before them).  build_parts() refines every part after the livery (`res.refine_part`); `livery.paint_mesh` /
  `_winglet_pin` / `_pod_pin` / `_stab_boot` first refine the skin along the paint boundaries
  (`res.refine_for_trim`, 2 passes) so the marching-triangle trims cut smooth stroke edges.
- `cad/glb.py` glTF writer with KHR_mesh_quantization and embedded image textures (`GLBBuilder.texture`; a textured
  material's meshes carry `Mesh.UV` as TEXCOORD_0 -- only those: elsewhere `Mesh.UV` is a surface parameter); the
  touching meshes of a part share one quantisation grid (`assemble.shared_grids`: per-mesh grids left hairline cracks --
  dark specks -- along every paint edge; the joints BETWEEN parts, e.g. fus_center / fus_aft at STA 9.85, still
  quantise on each part's own grid: one grid over a whole fuselage collapses slivers at 16 bits); normals 8- or 16-bit;
  `cad/sdf2d.py` 2-D signed distances.
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
  stacks), `gear.py` (+ `bays.py`, `brace.py`, `wheels.py` -- the L4W wheel / tyre tables and the 3-D wheels built from
  them; nose retracts 105° into a tunnel under the pedestal, unequal-link braces), `interior.py` (the approved source-tagged interior tables that sheets L6 / L6B draw --
  `drawing/interior_sheet.py` / `interior_checks.py` -- and `build()`: the Stage-3 meshes built from exactly those
  tables by `flightdeck.py` (part `flight_deck`: G3000 PRIME panel -- the five pages drawn by `model/g3000_pages.py`
  (unbranded, numerals only) into one JPEG atlas that the display glass (material 'display_page') carries as its
  emissive texture (`assemble.TEXTURES`), so the GLB, the viewer and any importer show the same pages --, glareshield, PC-24-style yokes, pedals, pedestal on
  the nose-tunnel plinth, consoles, overhead, walnut divider + curtain; extras 'design eye' = `interior.design_eye`),
  `seats.py` (IPECO 3A318-type crew seats `seat_pilot` / `seat_copilot` on their tracks, PRO executive seats
  `seat_pax1..6` at `seat_map()`), `cabin.py` (part `cabin_interior`: floor + AI Orange runner, surface tracks, ledges,
  stowed tables, forward RH lavatory, drawer cabinets, FR34 veneer header + curtain; the port ledge segment rides on
  `door_cargo`; the headliner fittings -- LED coves, PSUs -- and the flight-deck overhead panel hang on
  `interior_lining`, so the viewer's cutaway clips them with the lining: `interior.build_interior`) and
  `airstair.py` (the airstair door's inner body, treads, stanchion and the handrail / cables, pinned at both ends
  through the whole swing -- owner 2026-10-04: the old stowed upper rod and cables turned up to 189 deg about mid-air
  centres, "floating in from the sky": the lower rod folds about the stanchion, the upper rail telescopes from the knee
  into a sleeve on a jamb bracket (A on the jamb's inner edge, depth 160 mm), the cables pay out of the jamb fittings;
  viewer_test [RAIL-1] follows the pinned ends, fit_check 21 sweeps them; the door opens
  145 deg -- its free edge on the 145 deg line in MSN 3008 photos 130 / 188 through the fitted cameras --, free edge
  ~0.29 m off the ground, 3 treads + the bottom step at the free edge in equal risers from the sill); the flight deck's
  side consoles `fd_consoles` and walnut divider `fd_divider`, the yokes and pedals are child parts of `flight_deck`;
  the cabin floor + runner + tracks `cabin_floor` and the club tables are children of `cabin_interior`; side-wall /
  headliner lining `interior_lining` by the L6 LINING law -- 40 mm inside the OML at the crown, 85 mm at the sides,
  `interior.lining_offset` -- with window reveals and lined door wells; frames at the Pilatus frame stations;
  interior triangles are budgeted in `build.INTERIOR_BUDGET` (390k, crew seat 19.5k, cabin seat 12k at PC12_RES=1; at
  RES 2: 858k / 66.3k / 34.8k, built 851k / 66.0k / 34.8k, with per-part caps for the flight deck -- flight_deck 202k
  (built 199k), yokes 24k (22.6k), pedals 3k (3.0k), fd_consoles 30k (16.3k), fd_divider 18k (16.8k), interior_lining
  190k (185k); counted after the interior-light bake's splits; flight deck fix r2 raised the crew seat 56.1k -> 59.5k and
  interior_lining 175k -> 190k, fix r3 the crew seat -> 66.3k, flight_deck 150k -> 202k, the total 814k -> 858k) and
  printed by the build; the viewer's cockpit camera is `pc12_meta.json` 'cockpit' = `build.cockpit_camera()` at the L6 design
  eye),
  `details.py` (wing-to-body fairing: flat-bottomed belly fairing + upper root fillet / fairing nose built as a
  horizontal offset of the OML, so its side / plan outlines are the drawn ones -- the nose section is the concave
  fillet with a round-over crest (`ROOT_FILLET_ROUND`) running into the wing LE, the fillet law starts from the visible
  foot on the wing (`_visible_foot`), fit_check 16 guards its creases; flap-track canoes split at the cove lip
  into a fixed forward part and an aft part carried by the flap; cowl panel joints / latches / vent / oil-cooler exit
  (`COWL_SEAMS`, photo 188: the ring joints at STA 2.00 / 3.00 and the split line are real grooves cut into the skin,
  `cowl_grooves` / `COWL_GROOVES`, walls painted with the skin, a dark 'seam' floor; latches and vent stay painted-on
  dark lines); lights, antennas, pod with its straight tapering tail under the winglet),
  `livery.py` (PC-12 PRO MSN 3008 scheme; the 3-D painter trims with one-sided smooth fields so thin strokes stay
  continuous; zero-area slivers from trims are dropped by `cad/glb.py`; per-surface bands -- wing / tailplane boots,
  winglet pinstripe (+ POD_PIN along the pod / winglet junction), blade tip bands about the thrust axis, blade LE
  erosion strip -- are cut with sequential single-sided trims, never one V-shaped max() field; every white stroke is
  edged by the <= 6 mm neutral-silver OUTLINE (material name 'paint_champagne' kept) and there is no navy line --
  photos 82 / 130 / 188), `assemble.py` (MATERIALS = the photo-fitted MSN 3008 glTF values
  of `render/lookdev_materials.json`, clear coat / specular as KHR extensions; `check_lookdev()` and
  `livery.check_materials()` are printed by the build), `build.py` (steps + verification),
  `drawing/` (Stage-2 sheets L1-L6B via `drawing.master`; legacy HLR GA via `drawing.sheet`).

## Sourced facts (keep these fixed)
Pilatus PC-12 PRO/NGX facts: span 16.28, length 14.40, height 4.26, wing area 25.81 m², tail span 5.20,
track 4.53, cabin 5.16×1.52×1.47 (floor 1.30), passenger door 0.61×1.35, cargo door 1.35×1.32,
prop 2.67 m 5-blade Hartzell composite (EASA TCDS: HC-E5A-31A/NC10245B), prop clearance 0.32.
POH NGX: datum 3.0 m fwd of firewall; three-view wheelbase 3.48; gear electromechanical, trailing-link
mains retract inward with ONE leg-mounted door each, tyres protrude ~1 in when retracted; nose retracts
aft, enclosed by doors; over-centre two-piece folding struts; ailerons with Flettner geared balance
tabs (opposite motion), elevator in two halves, rudder single piece, stabiliser trim (LE down = nose up).
Jane's: airfoils LS(1)-0417MOD root / LS(1)-0313 tip, Fowler flaps 67 % of TE, T-tail, bullet fairing,
dorsal fin + ventral strakes, tyres 22×8.50-10 (main: superseded, see below) / 17.5×6.25-6, NWS ±60°, exit right over wing (Jane's says
Type III; the Pilatus drawing shows a 0.48 × 0.64 m plug hatch, which the model follows).
EASA TCDS IM.E.008: PT6E-67XP length 1,870.9 mm, diameter 481.8 mm, 2-stage RGB, 2-stage PT, 1-stage
CT, 4 axial + 1 centrifugal compressor. PC-12 PRO: pilot's direct-vision window deleted; Garmin
G3000 PRIME (3×14-in + 2×7-in touch displays); PC-24-style yokes; radome enlarged for 12-in GWX 8000.
NGX: cabin windows rectangular (PC-24 style), 10 % larger; dark windshield surround trim.
POPA variant guide: "PC-21 style winglets" from Series 10A (MSN 684+). Weather-radar pod on right wing.
Main tyres: 8.50-10 Type III, 10 PR tubeless (Goodyear 850T06-3 / Michelin 025-350-0 per tyre makers and parts
listings; OD ~0.64 m, confirmed by four photo measurements and the main/nose OD ratio) — owner decision 2026-09-26,
superseding Jane's 22×8.50-10 (`model/wheels.py MAIN_TYRE_CHOICE`; sheet L4W).

## Estimated / reconstructed (open to correction)
Fuselage contours between anchors (fitted to the Pilatus drawing, RMS 1-2 mm), windshield & side-window
outlines (fitted to the drawing, checked on PRO photos), winglet height (lengthened for the official span),
incidence/washout, airfoil ordinates, engine module proportions inside the TCDS envelope, interior layout,
nose-gear stowage tunnel and brace link split, livery details (camera-matched photos).

## Status / next steps
- Stage 1-2 done: reference drawings registered, drawing set L1-L5 approved (3 review rounds); interior sheets
  L6 (arrangement) / L6B (checks) approved, drawn from the source-tagged tables in `model/interior.py`, with the
  default open points (owner): the 95th-percentile knee against the yoke at ~18 deg roll accepted, 5th-95th percentile
  male accommodation, crew seat reference point STA 4.20, surface-mounted seat tracks.
- Owner decisions: quality bar 8 for EVERY review lens (owner 2026-10-04: "Once everything get to 8, tag me." -- the
  model, interior tour, propeller, resolution / picture and sound lenses alike; it was 7.5 from 2026-09-26, when the
  Stage-4 exterior VQA rounds 1-3 were judged 8 / 8 / 7.5); the drawn fairing tail lobe aft of the cargo-door seam is
  left un-modelled; no cargo-door gas struts; the main-gear leg door's pointed tip is rounded (see LD-1 below);
  markings: none (below).
- Stage 3 (3-D build from the approved parameters): `model/build.py` consumes the Stage-2 parameters end to end,
  the interior included (L6 / L6B tables -> flightdeck / seats / cabin / airstair; two tables were corrected in
  Stage 3 and L6 / L6B regenerated: LAVATORY aft wall 5.228 -> 5.195 and the cabinets 0.75 -> 0.72 high, clear of RH
  cabin window 1; the crew tracks lengthened by the fore / aft travel);
  `test/fit_check.py`, `test/viewer_test.py`, `drawing.sheet/verify` and `drawing.master` pass. Not modelled (owner
  decisions): the drawn fairing tail lobe aft of the cargo-door seam (STA 7540-8585, it overlaps the D2 panel; the root
  fillet fades out ahead of the seam instead) and the cargo-door gas struts.  Dihedral: decision D4 quotes 6.15 deg,
  the approved L4 / wing.py value (rev B airfoils) is 6.23 deg, which the model uses.
- Interior open items (Stage 3): crew-seat finish -- s/n 3001 cream leather + anthracite shell (`seats.CREW_FINISH`
  'pro3001', default) or the MSN 3008 grey ('light'), owner's choice; `interior.exec_seat` record 'rear' is 40 mm aft
  of the drawn back profile (checks built on it are conservative); at full forward + down travel the crew back shell's
  lower inboard corner comes within 14 mm of the nose-tunnel plinth (the L6B 15 mm criterion covers cushion / pan
  only); the cabin tracks run under the RH lavatory and the
  cabinets as L6 draws them; armrests / recline / headrest / travel are baked into the seat meshes (no viewer pivot;
  the yokes, rudder pedals and club tables do have pivots).
- Interior review r1 (fidelity / craft / mechanics): tables changed and L6 / L6B regenerated -- DIVIDER curtain (flare
  top 0.85 [M: P1046406], 25 mm of the bundle tucked behind the walnut edge, an 18 mm gathered band above it) and
  LEDGES door_segment 7.575-8.905 (inside the cargo clear opening) + door_foot 0.075 (clear of the sill jamb); the door
  frames have no stop / jamb along the hinge edges (the doors' inner skins swing through there), a tan outer jamb band
  (49-75 mm) and lining inboard of it, the cargo door an inner lining panel (75 mm, like the airstair), the door-well
  reveals end on the seam at the stop depth; the lining runs flush over the exit hatch (standard window reveal); the
  upper handrail unfolds the long way round (outboard of the skin); sculpted PC-24 yoke (domed white shield, recessed
  silver insert), thick wrapped sheepskin (fleece bump in Blender, KHR_materials_sheen in the GLB), V-seamed exec seat
  backs; panel_faceon uses the refitted camera 'panel_408b' (between the seat backs, as the photo); interior renders
  gain the world only for primary rays through the (transparent) glazing, and lookdev's thin glass uses a two-sided
  Schlick Fresnel (the Fresnel node made every obliquely seen cabin window a totally reflecting mirror).
- Interior review r2: tables changed, L6 / L6B regenerated (rev D) -- CREW_SEAT sheepskin_t 34 [M] (the fleece's
  crowned outer face IS the drawn cushion top / back front; the leather and shell lie inside it: the cover had stood
  +14 / +32 mm proud of the outline the manikin checks sit on), YOKE grip r 15.5 x 140 (slim paddles, P1046408), the
  crew tracks end 15 mm past the rear foot (11 mm clear of the stowed curtain, L6B 'curtain_track').  Builders: two
  puffy thigh sleeves + tuft waves, full 4-point harness (lap halves, crotch strap), exec back V seams to the shoulders
  over a flush lumbar trapezoid, lap belt across the cushion; white yoke shield out to the grip roots (no black bar);
  warm titanium `panel_grey` on the PDU face; silver PSU pods, flush O2 doors / PULL cover with a proud dark gap all
  round, downlight bezels on the soffit normal, soffit step 18 mm; thin grey airstair treads on open brackets, grey
  inner flange; airstair top / fwd jambs lining; yokes / pedals are viewer parts with pivots; the cutaway clips the
  cabin furniture and the divider / consoles (`web/viewer/model.js` CUT_MATERIALS); hangar_port34 opens the cargo door.
- Interior review r3: L6 / L6B rev E -- executive-seat legrests (forward-facing seats), the PC-24 yoke face (white
  shield, black body, swollen grip heads), the PCL paddle, the arm-vs-pedestal criterion (L6B, 15 mm); crew lap belts
  draped over the fleece (fit_check 24), armrests vs the pedestal over the travel (25), no coplanar overlaps of
  different materials (26); `fd_consoles`, `fd_divider`, `cabin_floor` and the club tables are own parts, so the
  viewer's cutaway clips the divider, consoles, cabin furniture and tables whole while the floors, panel, seats and
  controls stay; club tables movable (pivots 'table' / 'table_leaf', viewer toggle; cockpit_fwd / cabin_club pose the
  port leaf out).
- Airstair open angle (2026-09-27): 145 deg, not 160 -- the open door's outline and free edge lie on the 145 deg line
  in both MSN 3008 photos 130 / 188 through their fitted cameras (livery/cams.json port_hangar_130, vqa/cams_beauty.json
  nose_188); the treads were re-laid horizontal at 145 (bottom step at the free edge, equal risers from the sill), the
  lower handrail's stanchion re-measured on the same photos (a short clevis post at open WL 0.70), the cable clamp kept
  on the same place on the door; the knee and the jamb fittings are fuselage / world points (unchanged).  fit_check 9 /
  21 re-run: the door + handrails clear the fairing and the interior over the whole swing; L3 notes the angle.
- Main-gear leg door, decision LD-1 (owner-delegated, resolved; model/gear.py comment block): the door is the wing
  lower skin carried down by the leg (`gear.leg_door_offset`), so retracted it closes flush (1 mm recess, 3 mm panel
  gap, `bays.DOOR_GAP`) and the tyre protrudes 24 mm in its own round well (`bays.well_sdf`); drawn side-view face
  kept WHOLE over the tyre down to the hub (model judging r1 GR1-01 removed LD-1's tyre scallop R 332: photos mx4 /
  mx5 / 0517 / 3010 show the door outboard of the tyre covering its upper-forward sidewall, its concave lower edge --
  the drawn arc, 187 mm from the axle -- hugging the hub fairing) with an outboard BLISTER over the covered tyre
  crescent (`gear.leg_door_blister`: inner face `LEG_DOOR_TYRE_CLEAR` 10 mm outboard of the tyre / wheel gear down, up
  to 27 mm; stowed it stands as deep below the skin over the protruding tyre, the rest of the door flush), plus a tab
  hidden in the slot over the leg's skin crossing (`gear.leg_door_face`); edge-on it stands at BL 2339-2383 (the
  blister leans its lower part out) instead of the drawn 2358-2472 lean (call-out on L4).
  Hidden changes: trunnion STA 5978 / WL 1155 (drawn leg top 5932 / 1070), retraction 86 deg (stowed wheel along
  the ~7 deg skin), side-brace stations 6040 / 6038, L1 split 0.19, B0 on a lug 80 mm inboard of the leg (`gear.MAIN_BRACE_LUG`) and the links offset along the knee pin (`MAIN_BRACE_CLEVIS`) so they clear the stowed leg, no forward slot; liner-only pockets
  (`bays.TRUNNION_POCKET`, `BRACE_POCKET`), a black seal band on the lowest 60 mm of the main-bay liner, and a finer
  wing lower skin over the bay (wing.py sub-panel) so the cut-out corners are cut within a few mm. fit_check 5 / 10
  test flushness, protrusion (20-30 mm), the closed cut-out and every pose of the swing.  Owner decision 2026-09-27:
  the drawn pointed tip is one round R 20 (`gear.LEG_DOOR_TIP_R`, tangent to the chamfer and the lower-edge arc) and
  the step's aft corner R 20 (`LEG_DOOR_CORNER_R`, like the aft top corner): sharp, they nicked the skin beside the
  cut-out by 2.8 / 1.3 mm at 96-99.5 % retraction (between the 10 % samples); fit_check 10 now sweeps the door against
  the skin every 0.5 % over 90-100 % (0 crossings).  The lowest point rises from the drawn WL 318 to 325 (call-out on
  L4 detail B; the drawn face stays the phantom).  The door with its blister passes the fine sweep (0 crossings) with
  the tyre 23.5 mm proud; fit_check 5 tests the flushness outside the blister, the blister depth (<= tyre + 10 mm)
  and the door-to-wheel clearance gear down.  Paint (VQA r3 RQ3-07): the outer face is the wing's lower skin, so it
  wears the wing-dark underside (`gear.LEG_DOOR_OUTER_MAT` -> `livery.SURFACES['main_gear_door']`; photo 0517's door
  G/B 0.49 is that hue), the inner face and rim the base blue (`main_gear_door_inner`).
- Wheels (`model/wheels.py` tables -> sheet L4W -> 3-D `main_wheel` / `nose_wheel`): both tyres are statically LOADED
  (axle WL = the loaded radius: main 279 with the 8.50-10's R 320, 41 mm flat; nose 207, photos 200-210, 15.5 mm flat;
  `wheels.loaded_side_outline`). The 8.50-10's stowed tyre reaches STA ~6,730 at BL 1,39, behind the 66 % rear-spar
  line: the rear spar is interrupted at the main bay (`interior.build_structure`, like the ribs) and the flap cove's
  forward bulge is recessed over the well (`wing.cove_well_recess`, flap nose >= 15 mm clear; hidden with the flaps
  up). The loaded tread lies flat on the ground across its width (`wheels._loaded_tyre`, = L4W `loaded_headon_half`).
  Nose fork = two slim arms (42-52 mm fore-aft) joined by ONE round arch over the tyre (superellipse fitted to the 3001
  head-on, `gear.NOSE_YOKE` arch_h / arch_p) under a chamfered crown saddle with the torque-link lug; hex axle nuts on
  tear-drop lock plates outside both arms; the nose doors open 92 deg so the nuts pass them (it supersedes the VQA r3
  plate fork; the nose lamp keeps the VQA r3 R 55); main trailing arm = swept swan-neck tube (`gear.MAIN_ARM`) with the
  brake hose along it. Wheel materials: the tyre is three zones (`wheels.TYRE_MATS`: `tire` sidewall, `tire_tread`,
  `tire_groove`; tests take the tyre by that tuple), main wheel halves `wheel_main` (dark cast), brake `brake_housing`
  (bright cast) / `brake_disc`, hub fairing `hub_fairing` (the leg door's outer-face navy, `paint_wing_dark`'s hue, a
  shade darker -- model judging r1 GR1-03: door and fairing one navy in 0517 --, not repainted by the livery), nose wheel `wheel`, axle nuts `steel_dark`, tie bolts / valves `cadmium`.  Triangles:
  main wheel <= 30k, nose <= 18k at PC12_RES=1 (`wheels.TRI_BUDGET`, 29.5k / 17.9k built; x1.75 at RES 2).  Blender: `render/lookdev.py` drops the
  groove shader for the geometric grooves and mottles the tyres with dust (`_dust`); beauty presets
  `wheel_main_close`, `wheel_main_inboard`, `wheel_nose_close`.
- Stage 4: Blender (Cycles) beauty renders (`render/beauty.py` presets, `--compare` photo side-by-sides; it applies
  the photo-matched materials / environments of `render/lookdev.py` right after its own material setup;
  `render/blender_ortho.py` for calibrated views; interior presets `cockpit_fwd` / `panel_faceon` (photo-fitted to
  PRO s/n 3001 P1046406 / P1046408), `cabin_aft_fwd`, `cabin_club`: env 'interior' = daylight through the glazing
  (INTERIOR_DAYLIGHT; the view through the glass gained by INTERIOR_WINDOW_VIEW for primary rays only) +
  INTERIOR_LIGHTS + the emissive displays / LED coves; every interior material is in assemble.MATERIALS
  (+ EMISSIVE) and render/lookdev.py SPEC, `python3 render/lookdev.py --json` regenerates lookdev_materials.json) and
  the three.js viewer (`web/`, three.js r160 in `web/three_local`; `web/viewer/materials.json` must stay a copy of
  `render/lookdev_materials.json`: `viewer/materials.js` turns it into MeshPhysicalMaterial by name -- emissive, the
  GLB's sheen and its textures (the display pages' emissive map) carried over --, replacing the GLB's KHR clear-coat
  materials, and keeps the GLB values for the rest; every part of the GLB group 'Interior' gets the cabin light; the
  table's `render_stripes` (cabin carpet) become a band-limited pinstripe patch, and the carpets get an occlusion
  stand-in (VIEWER envMapIntensity 0.3 and a deeper orange since review r4: unoccluded, the studio washed the AI Orange
  runner out to pale peach); two
  model tiers: the boot script loads `PC12_CONFIG.glbLow` (out/pc12_low.glb) on the 'low' quality tier (phones) as it
  picks the 512 px HDRI, the full model elsewhere (?glb= overrides both); there the Specs panel's detail switch loads
  the full model instead (?detail=full|light, remembered in localStorage 'pc12-detail'; review r1 RES1-02), and a
  stage chip offers it once after load on devices likely to take it (navigator.deviceMemory >= 4, an iPad, or an iPhone
  with a >= 1080 px screen; not on the gzip no-WebAssembly path; Load / x remembered, ignored it leaves 25 s after the
  loading screen; ?detailChip=1 forces it; review r2
  RES2-03); the Specs
  panel and the part cards count the tier loaded; the Artifact bundle's gzip no-WebAssembly fallback is the full model on desktops (data/pc12_glb.gz.bin) and the light
  tier on phones (data/pc12_low_glb.gz.bin, PC12_CONFIG.glbGzLow), so a host that refuses WebAssembly still shows the
  full resolution on a desktop).
  The model carries NO markings (owner decision: no logos, registration, serials, flags or lettering).
- Viewer picture quality (owner 2026-10-03 "smoother curves, edges and sharper crisper picture"; the picture side,
  `web/viewer/picture.js`, Stage.render() -> Picture; crisp review r1 fixes in r2): once nothing moves the canvas goes up
  to the screen's own pixel ratio (3 at most) within the profile's pixel budget (`stillDpr`: phones ~2.5x on Auto at
  390 x 844 instead of 1.5 -- CR1-01, phones sharper than before, not only smoother; desktops above 2x), then the scene
  is rendered into a multisampled render target at 1x or 2x that canvas (whatever budget is left: 8.3 MP High / Auto,
  16.6 MP Max, 2.1-8.3 MP phones; byte budget; MAX_TEXTURE / RENDERBUFFER / VIEWPORT size; 2 MSAA samples at 2x, 4 at
  1x, Max 4 / 8; fractional still scales are not used: the straddling target pixels add their own box to the filter),
  box-filtered down and accumulated over N passes jittered by Halton offsets within ONE MSAA CELL (+-1 / 2n target px:
  the n-rooks MSAA samples then fill each output pixel evenly, the box filter of a dense supersampling; a whole-pixel
  jitter made a 1.5-2 px tent) (16 High / Auto, 32 Max, 8-16 phones; frame 0 unjittered, so the switch does not shift
  the image).  The targets are 'XR' render targets (rt.isXRRenderTarget, RGBA8, sRGB colour space): three applies the
  AgX + Punchy tone mapping and sRGB encoding into them exactly as on the canvas and the passes average premultiplied,
  encoded values like the canvas' MSAA resolve -- the colours never change between paths; each carries a resolved
  depth texture.  Spinning propeller with the camera still (CR1-03, 'layered'): main.js sets Stage.overlay =
  PropBlur.overlay (disc, root band, turning hub) once the blades have faded into the blur disc and the spinner is held,
  and marks those frames overlayDirty instead of needsRender; the still passes then render WITHOUT the overlay (the
  static aircraft refines and converges as usual, also where still refinement is off: one 1x pass), and every frame
  shows that image with its depth (COMPOSE: gl_FragDepth from the target's depth texture) and draws only the overlay on
  camera layer OVERLAY_LAYER (5; the lights get it too, so the programs are the full scene's) with the canvas' MSAA
  -- a full-screen copy plus the disc instead of the 2M-triangle scene per frame.  Moving frames (CR1-02): temporal AA
  -- the scene into a multisampled target at the canvas size (4x, Max 8x) jittered within one MSAA cell (Halton, 8-cycle),
  blended with the history reprojected through the depth buffer (world position from the nearest depth of the 3 x 3
  neighbourhood; where nothing wrote depth -- the ground grid, contact and key shadows -- the ground plane under the view
  ray: without it the ground smeared), Catmull-Rom history samples (5 taps), the history clipped to the neighbourhood's
  YCoCg variance (1.25 sigma) and range, new-frame weight 0.15 rising to 0.6 from 1 px of motion a frame (TAA_ALPHA /
  TAA_FAST: the history is resampled every frame, keeping more of it went soft); the first moving frame continues from
  the still image (its camera kept as the seed), a cut (> 20 deg turn, > 0.3 x the orbit distance, fov +-20 %) starts
  afresh; shown unsharpened (a display sharpen and sharper resampling kernels measured worse).  Tuned on 8-frame orbits
  of 0.15 / 0.5 deg a frame against the converged still (out/tmp/viewer/35_picture_orbit_*.png): continuous door gaps
  and smooth edges where the plain 4x MSAA frame dots and steps them, a little softer at speed.  Where a supersampled frame is predicted from the measured
  still passes (cost per target pixel) and then measured to fit the refresh, one supersampled pass (moveSS: 1.5 Auto /
  High, 2 Max; 'movess') feeds the temporal blend; camera still while gear / door / explode animate: one supersampled
  pass up to the still scale ('busyss', no temporal blend: no motion vectors for moving parts); ?movess=1|0 forces them,
  ?taa=0 / ?layer=0 switch the temporal AA / the layered propeller off.  Targets: a pool of at most two multisampled
  targets (the still and the moving plan, shared when they agree), the accumulation pair, the history pair; each
  released after 30 s unused.  Pixel-sized effects follow the scale (grid line width uPx, construction-line opacity).
  Specular AA: three's additive `geometryRoughness` replaced in ShaderChunk.lights_physical_fragment by the
  normal-variance kernel (Tokuyoshi & Kaplanyan; Filament 0.15 / 0.2) on alpha^2, roughness floor 0.0525 (the 1k HDRI's
  256 px base mip).  Textures: max anisotropy + trilinear mipmaps (G3000 atlas, contact shadow).  Studio HDRI: 1k on
  desktops (a 2k copy measured no sharper reflections -- review CR1-06: the glazing / chrome / clear-coat roughness sits
  at the floor either way -- for 4.7 MB more before the first frame, and was dropped), 512 phones, 1k phones on Max
  (RGBELoader FloatType, the strip grade tabulated).  Key shadow: PCSS on the ground ShadowMaterial (PCFShadowMap, 4096
  desktop, phones 1024 Auto / 2048 High-Max; contact shadow 1024 desktop, 256 / 512 / 1024 phones, rendered at 512 while
  the scene animates and full size once still, same UV blur radii; a 4 deg softbox, LOOK.keyAngle) on a shadow camera
  fitted to the posed casters at each shadow render (Stage._fitShadow).  Auto: a start-up calibration = the MEDIAN of 3
  plain frames (2nd-4th), each drained with a 1-pixel read before and after (review PERF-1: no queued GPU work of frame 1
  in the sample; one over 3 s ends it: software rendering such as SwiftShader gets no refinement, the pre-2026-10
  picture); at run time fences (isolated frames) and rAF intervals (back to back) step the still budget (2x target,
  then the still canvas ratio), the passes, phone Max's moving ratio and the single-pass supersampling, and give cut
  passes back once plain frames fit the refresh (backing off 5 s, 10 s, ...).  The end of an orbit coast settles faster
  below 0.5 px / frame and is applied at once below 0.05 px (Stage.update), so stills start promptly.  Specs panel
  'Picture quality' Auto / High / Max (above the model statistics; a plain-language note; localStorage 'pc12-picture';
  a line in the '?' help); ?picture=, ?quality=high|max fix it (tests), ?ssframes= / ?sspx= override passes / budget,
  ?keyangle= the softbox.  Tests: viewer_test.py '[PQ]' / '[PERF-1]' / '[CR1-..]' rows (480 x 320 pages in High, 3-4
  passes; the phone still ratio at 390 x 844; the temporal AA against the converged still after an orbit; the layered
  propeller's frames differing only on the disc).  The door outlines are 4 mm gaps between door and skin (sub-pixel
  slivers at orbit distance: dotted under 4x MSAA alone, continuous in the still passes and the temporal blend).
  SwiftShader takes ~20-30 s per 2x frame at 800 x 500 on the shared sandbox: compare frame costs relatively, never
  tune on them.
- Flight deck r1 LOOK (owner 2026-10-04 "can you make cockpit a bit better? ... 1/10"; track 'look': the viewer's light
  and the baked interior light, no geometry): inside the closed cabin -- the tour, the Cockpit preset, any camera there
  (`main.js syncInteriorLook`: `tour.inside || model.camInside`, LK-08) -- `Stage.setInteriorLook` swaps the studio for
  the outside world, the exterior lens staying exactly as judged (viewer_test [FD-L7] renders the 3/4 view with and
  without the world / sun in the scene and after a round trip inside).  `web/viewer/outside.js`: procedural only (no
  image files, no lettering) -- a sky dome (r 440 m, through the tone mapping: zenith (0.26, 0.47, 1.0), horizon
  (1.24, 1.33, 1.43), sun glow + disc), a 400 m apron canvas (2048 px, 1024 on phones: mottled concrete, 7.5 m slab
  joints, a taxi line + lead-in arc, grass), a far ring, five pre-lit hangars (cladding / door bay / high-window facade
  texture), a ridge; no raycast, no shadows, layer 0 only, the ground / ring drawn first without depth (no z-fight at
  200 m with the 1 cm near plane); shown inside, while the ground grid, shadow catcher and contact shadow hide.  The
  image-based light inside is that world's PMREM (built once, the zenith desaturated 60 % for it, `SKY.envDesat`: the
  deep blue overhead had tinted every up-facing trim slate blue; rebuilt after a context loss).  A permanent sun
  (`scene.js LOOK.sun`, made after the key so the key stays directional shadow 0 and the light count never changes --
  no recompiles in and out; flight deck fix r1, below: now az 25 / el 45 at 8): az 125 deg from dead ahead to starboard, el 40 (`outside.js SUN`: through the co-pilot's
  side window and the forward cabin windows onto the pedestal, sub-panels and seats, the glareshield shading the PDU
  tops; the assessment's az 65 / el 26 lit only the glareshield lip), 5 inside (the brief's 3.5 left faint patches under the calibrated window-light law; 5 changes no P1046408 row --
  the sunlit pedestal 113 -> 121 only; az 95 / el 35, which lit the pilot side dramatically, put sun on the seats and
  consoles that P1046408 does not show: sheepskin 168, consoles 54) / 0 outside, its own 2048 px map (1024 phones, PCF radius 3 / 2) on a fixed
  +-1.9 m box round the flight deck, rendered on pose changes only (`shadow.autoUpdate` follows the look; the key's map
  is not rendered inside, a spinning propeller's blades leave the sun's casters); interior receivers outside that box
  are shaded (`materials.js` interior patch: getShadow's out-of-frustum default 0); inside casters / receivers
  `model.js SUN_CASTERS / SUN_RECEIVERS` (skins, cowl, glazing frames, doors, every interior part; glass and lenses
  never cast -- the exterior set, where the glazing casts with its X-ray shell, comes back on exit); the ground's PCSS
  shadow reads the key's map only (`picture.js patchShadowMaterial`).
  Baked interior light (`cad/ao.py`, `model/build.py bake_interior_ao`, in `build_parts(ao=True)` of main() and
  build_low(); written as the vertex attribute `_AO`, two normalised bytes: `cad/glb.py`): channel 0 cone-traced
  occlusion (0.36 m reach; the far steps from a 16 mm distance transform, ~5x faster than the k-d tree alone), channel 1
  the window light -- the share of the cosine-weighted hemisphere that sees out through the glazing within 2.5 m (a
  20 mm voxel march through the interior, skins, frames and doors, never the glass; out = beyond the OML) plus one
  bounce (a ray meeting the interior brings albedo x (its sky + `AO_GLOW` 0.25), the displays' / coves' glow
  `AO_EMIT`): the footwell under the dark panel 0.04, the yoke facing the seats 0.16, the glareshield 0.32.  Both are
  per vertex, deduplicated by 6 mm cell + normal; the flight deck's floor, kick panels, consoles and footwell walls are
  first split to <= 60 mm edges (`AO_SPLIT`, flat midpoints, conforming across a part's meshes: +23k triangles at RES 2,
  +20k on the light tier).  Bake ~2-4 min a tier (printed by the build).  The viewer (`materials.js` 'ao' patch + the
  interior block) inside: diffuse x `CABIN_LOOK.gain` x occ x mix(sky floor 0, 1, light) capped at 1.5 x the open
  world's (`gain` [18, 1.6, 1.5]: calibrated on the photo-fitted panel_408b against P1046408 -- yoke 204 / 208,
  sheepskin 113 / 110-134, footwell 9 / 6, eyebrow 101 / 100-113, posts 93), reflections x 1.6 x occ x mix(0.35, 1, light);
  the light trim's fill share keeps that share out of the law (the cabin lining: none of it, half its occlusion; the
  cabin fill 3.4 -> 2.3 for the brighter world: T4 cabin medians ~210 / 215, T4b headliner >= 200); reflection facing weights [0.12, 0.5] (were 0.06 / 0.3),
  with `SPEC_KEEP` (titanium, gunmetal, pewter, chrome, bezels, black leathers, yoke white, displays; for the geometry
  tracks' detail also the annunciator caps `annun_*` and the smoked visors `fdb_visor`) exempt (FD-J10).  A material
  with no entry (stitch_thread, rubber_black, legend_plate, the fda_ / fdb_ trim) takes the interior law as it is; an
  emissive one (legend_lit, the CB glow bands) keeps its emission.  ?cabGain= ?cabSky= ?cabOcc= ?cabIn= override them.
  Palette (L5, `render/lookdev.py` SPEC + `assemble.MATERIALS`): lining_flightdeck 0.10 rough 0.75 (no CABIN_TRIM; [0, 0.72] since flight deck fix r1),
  leather_glareshield 0.045 rough 0.48, panel_grey 0.20, carpet_flightdeck 0.03, sheepskin lavender-grey (0.28, 0.275,
  0.33) with sheen (0.50, 0.50, 0.60) and CABIN_TRIM [0, 0.55], leather_crew [0, 0.8], panel_dark [0, 0.5], panel_titanium [0, 0.45] (0.6 since the
  flight deck r1 merge, below; + panel_graphite [0, 0.85]), carpet_flightdeck
  [0, 0.85], yoke_white [0, 1.08] (panel_408b: titanium 72 / P1046408 66-78, carpet 13, consoles 13, yoke 202; a lower
  reflection floor `cabSky` 0.12 / 0 measured further from the photo's tonal bands: 32 / 41 / 16 % vs 25 / 47 / 15).  Viewer
  patches (L6): fleece clumps 12-20 mm with darker crevices, a fine pebble grain on the leathers, the walnut figure
  (render_grain streaks, rest pose), brushed titanium (anisotropy 0.6 along BL, streaky roughness; no env 0.6 stand-in),
  the G3000 pages x1.45 inside.  `viewer.tour.place({eye, target, fov}, {clamp: false})` puts the tour camera at an
  exact pose (the photo-fitted panel_408b / cabin_fwd_406 cameras); viewer_test `fd_look_checks` [FD-L1]-[FD-L9]
  (`--only fdlook`, 1200 x 900; [FD-L3]: panel_408b's eye is WL 2.03, ~0.2 m under the hood, so the leather it sees
  is the rolled lip over the flat underside -- the lip the brighter band, as in P1046408 along the same columns: roll
  141-169, underside 99-124; [FD-L6]: median >= 65 with P1046408's tonal bands instead of the brief's p50 85-110, which
  its own per-material targets cannot reach in that frame).  Cost: the dark one of the two directional lights (the key inside, the sun outside)
  is skipped by a uniform branch on its colour in three's `lights_fragment_begin` (`scene.js installDarkLightSkip`:
  exact, no recompiles; ?darkskip=0 off); inside, the hidden contact shadow stays dirty for the way out without asking
  for frames (main.js: it had requested a render every frame, so the inside picture never settled into its still
  refinement and the viewer never idled -- [FD-L9] measures the idle rAF rate after a stop).
- Higher-resolution model (owner 2026-10-03 "can you make the 3d modeling higher resolution?"): `cad/res.py` /
  `cad/refine.py` above -- PC12_RES=2: 1.53M -> 2.11M triangles where facets show, 16-bit normals, crack-free shared
  quantisation grids, finer round primitives.  Review r1 (RES1-01..05) re-spent the triangles: the first pass (2.63M)
  had split every big skin uniformly at 0.10 mm and left the coarse small radii alone (seats 22 % of their area
  faceted, > 12 deg between face and vertex normals); now the big skins keep their grids (0.30 mm silhouette
  tolerance, one paint-boundary pass), the turn criterion and the builders' finer rims / arcs / pad grids go to the
  seats (pax 22 -> 2 %, crew 18 -> 5 %), yokes (26 -> 8 %), pedals, braces, the chin inlet (27 -> 7 %: analytic
  normals on the sheared lip columns, `fuselage_parts.build_skin`, which took the radial streaks out; a denser duct
  entry), the blade boots (crisp folds); still faceted by that metric: the strakes, flap fairings / canoes (their
  flattened tops under the skin), the rudder / rudder tab (trim slivers, the ruled top), the nose-gear tyre grooves.
  The shape is the approved one (10
  dimension checks, consistency sheets, fit_check unchanged in tolerance).  Two consistency rows were made independent
  of the vertex spacing (no tolerance changed): the tyre side silhouette is taken along the mesh edges (a refined
  sidewall put vertices at clock angles where the tread had none), the fin / rudder slices sit 0.1 mm above their
  stations (WL 3.60 is a mesh row over the rudder-tab cut-out; 16-bit rounding put it on either side).  fit_check 26
  (coplanar overlaps) builds its pairs slab by slab (the same pairs; the refined interior's all-pairs did not fit in
  memory).
  Review r2 (RES2-01..05): the chin-inlet lip and the cowl round it -- the raised lip / cheek follow the drawn knots
  through C1 PCHIP curves (`powerplant.chin_lip_rho`, `chin_lip_x`; the polylines creased the cheek along every knot's
  polar angle and kinked the studio streaks above the inlet; <= 2 mm off the polylines the sheets draw), iso-lines of
  the face parameter s at the nose top (`CHIN_NOSE_S`: the g-levels ended at s 0.8 with ~55 deg of the nose's turn left
  across one row of large triangles -- the sawtooth light / dark line), the columns sheared onto the face up to polar
  84 deg (`CHIN_SHEAR_TH` taper 84-96, was 72-84: oblique columns at the arms' top crossed the face's iso-lines into
  ~17k sub-millimetre triangles whose quantised normals the reviewer's metric counted), the lip / cowl vertices the
  cuts left on chords snapped onto the skin (`powerplant._snap_to_skin`, not on the face / nose -- its rows folded --
  nor the mouth loop the duct is built on: the lip outline crossing the cheek's soft maximum lay up to 5 mm inside it;
  the L1 skin-on-OML row 4.3 -> 3.1 mm), and every cowl / lip vertex ahead of STA 1.80
  gets the analytic skin normal at its closest point (`fuselage_parts.skin_analytic_normals`, Gauss-Newton on
  `powerplant.cowl_section` from the vertex's UV; again after the livery and the refinement, `build.build_parts`;
  leaned to <= 50 deg of its faces where the mesh does not follow the skin, so no vertex normal is > 60 deg off its
  faces); the cowl halves and the chin inlet quantise on one grid (`assemble.JOINT_GRIDS`).  The stacks' torn streaks
  were the viewer's pixel-difference polish bump, not the mesh: `materials.js` VIEWER exhaust_polished bump 0 (the
  roughness / tint noise stays).  The flap-track canoe noses (`details.CANOE_NOSE_*`): the axis hangs 2 mm under the
  skin where it would rise above it and the lower half keeps >= 0.4 x the radius, a real tapered nose closing under the
  skin (the first ~0.25 m had been flattened onto the skin into a spiky zero-thickness sheet).  Control-surface noses
  every 7.5 deg at RES 2 (`wing._nose_n`: PN splits of the 15 deg rows drew the rudder nose's highlight as a sawtooth).
  The crew fleece's fine waves are band-limited to the judged grid's (`seats.fleece` h_judged: the finer grid drew
  them as a twisted rope).  Still faceted by the facet metric (> 12 deg): rudder 8.5 % / tab 16 % (the tab bay's flat
  face and the ruled top cap, creases drawn with averaged normals), strakes, flap fairings / canoes (flattened tops).
  Triangles 2.11M -> 2.13M (light tier 1.53M -> 1.54M); the reviewer's GLB bad-normal count on cowl_lower 103 -> 45
  (the rest: quantised sub-millimetre faces at the lip face's ends and the keel step; none in the float mesh).
  Review r3 (RES3-01 major: at the default orbit distance the old and new models rendered the same -- the old one was
  already sub-pixel there -- so the gain must be detail where the close-up cameras look, and shown to the owner as
  before / after pairs, out/tmp/owner_gallery 01-14): real geometry instead of painted lines and cut edges -- the cowl
  joints are grooves in the skin (`details.cowl_grooves`, above), the spinner's base edge a rolled R 3 edge
  (`powerplant.SPINNER_BASE_ROUND`, <= 0.9 mm off the drawn corner), the blade seal rings moulded with rolled edges
  (`BOOT_INNER_ROUND`, `BOOT_ROUND_N`; outline through `res.seg`), and 3x the spinner's profile rows at RES 2 (its
  streaks zig-zagged once per 6 mm row in the close-ups; the propeller part 58k -> 177k triangles); RES3-03 the leg
  door's tyre blister is a smooth envelope (no final max() back up to the need: smooth Gaussian lifts within
  `BLISTER_SHORT_TOL` 0.25 mm), read through a bicubic spline, sampled on a 4 mm grid over it
  (`LEG_DOOR_BLISTER_STEP`) and shaded with the analytic normal of y = leg_door_bl(x, z) (it looked dented); RES3-04
  the strakes' section has a constant thickness, a round tip edge and its root sunk 15 mm into the tail cone
  (`STRAKE_ROOT_SINK`; the 15 % root / tip ramps drew a crinkled highlight), and the canoes' flattened tops are their
  own patches (`details._crease_split`: averaged across that edge the body's normals leaned up to 45 deg); RES3-02 the
  chin lip outline is cut by two single-sided trims (the front-view outline, then the side-view crescent, both pieces
  of the first cut taking the second: no T-junctions), not one max() field; the cheek and lip edges longer than 3 mm
  beside the lip's top outboard corners are split twice before the snap (`powerplant._refine_cheek_corners`,
  CHIN_CORNER_BOX: the sheared columns' slivers drew the cowl's streak there as a zig-zag; off the lip face / nose,
  open boundaries kept); and a dark skirt from the exact mouth edge 8 mm into the duct (`chin_mouth_skirt`,
  CHIN_MOUTH_SKIRT: the duct entry's first ring resamples the jagged mouth loop at 96 points, and the up to 0.7 mm
  gaps between them showed the dark cowl interior as specks along the lip).  Not changed: the slivers on the lip face
  itself at those corners (their re-meshing is open).  Triangles 2.13M -> 2.32M (light tier 1.54M -> 1.62M).
- Viewer interior tour (owner 2026-10-03: "no good link to actually navigate into the interior"): `web/viewer/tour.js`.
  The toolbar's first group is an accent 'Go inside' menu button (also key I; the 'Cockpit' preset button / key 5 now
  enter at the pilot seat) opening a menu of 7 stops -- pilot / co-pilot seat (L6 design eye = pc12_meta 'cockpit'),
  flight deck from the cabin (divider opening), cabin forward / aft (standing, eye 1.35 above the floor), club seats
  (PAX 3's 50th-pct seated eye), airstair door (in the open door looking down the steps; the tour opens it) -- with
  flights: outside, an
  orbit round the fuselage to an approach pose, a fade through the skin and a FOV settle; inside, a Catmull-Rom path
  stop -> via -> aisle -> via -> stop (looking along the aisle only when both ends do).  Inside, a first-person camera
  (OrbitControls off, near plane 1 cm): drag / one finger looks (grab the scene), W A S D / arrows walk and turn, Q E /
  PgUp PgDn the eye height, R F pitch, wheel / pinch / two-finger drag move, 1-7 stops, Esc exits; an on-screen walk
  pad (touch only: hidden for a fine pointer until a touch), a dismissable hint, a screen-reader live region; the
  panel folds away inside on every device (exit re-opens it).  The eye is projected after every move onto the walkable
  volume of `web/viewer/tour_data.js` -- GENERATED by `python3 web/tour_data.py` from model/interior.py (seat_map,
  design_eye, cabin_pose, DIVIDER, CABINETS, BAGGAGE, CLEAR_ZONES, headliner_z / lining_crown + OVERHEAD) and
  fuselage_parts.AIRSTAIR: boxes (flight deck between the seat backs from 0.30 aft of the pedestal, eye <= 1.27 above
  the floor; `crew_gap` between the crew seats at the seated eye height, the way out of a crew seat, height weight 1;
  aisle; entry vestibule; the doorway while the airstair is open; a pocket per seated eye) under a ceiling grid held
  0.10 below the headliner / lining; a walk's end facing a full-height wall stops WALL_CLEAR 0.40 short of it (the
  divider 0.30); height weighs 0.1 in the projection, so a walk dips under the soffit / into a seat instead of
  stopping, and the kept eye height comes back (0.6 m/s) once there is room; a sidestep held by the aisle edge within
  0.5 m of a seat slides into it.  Review r1 (NAV1-01..07): the forward walk had ended over the pedestal in the
  glareshield, the aft one 12 cm from the curtain (a full-screen smear), the airstair stop looked into the jamb.
  Portrait phones: vertical FOV <= 85 and the optical axis 40 % down the view (`Stage.setViewShift`, an off-axis
  window).  Inside, the cabin keeps the light theme's studio in both themes, +0.3 EV (`LOOK.interiorEV`) with the
  cabin light `CABIN.inside` 0.8 and the CABIN_LOOK below (review r4; r2 had +0.6 EV x 1.6: headliner ~207 but every
  dark surface veiled) (`Stage.setInteriorLook`;
  the dark studio left the headliner near black) and is lit as inside wherever the eye is (`Model.updateCabin`
  forceInside, `U.cabinIn`).  Exit (button / Esc / a camera preset / another build step) restores what the tour
  changed: build step, cutaway, X-ray, explode, isolate, construction lines, the phone sheet, the door it opened.
  test/viewer_test.py [T1]-[T11] check it (data current, every stop from the menu with ray / table clearances and
  exposure, walk clamps incl. the walk ends' distance to the flight deck / curtain [T5b] and the seat sidestep,
  keyboard / pointer / touch, flights, exit, phone, dark theme; [T4b] the headliner).
  Review r2 (NAV2-01..06): `Tour.go` completes a pending exit first and goes back in from outside (a stop key / menu
  pick during the exit fade had pushed a flight on the inactive tour); a sideways step out of a seat into the aisle /
  the gap between the crew seats holds on that region's centre line until the strafe is released and pressed again
  (`Tour.latch`), an aft step held by a crew seat's pocket slides inboard into the gap (the way out), and a walk into a
  seat turns the view to its `facing` (-8 deg, 0.4 s) and carries a held sidestep on to the seated eye's `eye_bl`
  (both per seat region in tour_data); the vestibule keeps WALL_CLEAR from the closed airstair door's lining (BL
  -0.30; `vestibule_door` widens it to -0.45 while the door is open); the airstair stop looks out at -38 deg (was
  -52: a portrait phone saw only the treads).  viewer_test [T12] checks them.
  Review r3 (NAV3-01..05, viewer_test [T13]): a forward walk held at the flight deck's front face carries on down into
  `crew_gap`, the eye gliding (SINK 0.6 m/s) to the seated eye (`eye_z`) and the walk ending level with the seated
  eyes (`face_x0`, >= 0.45 m to the flight deck in the line of sight): the way back into a crew seat by walking, a
  sidestep then enters either seat; a walk
  from a stop's steep look (pilot -21, airstair -48) levels the view to -6 deg over ~0.5 s in the standing regions and
  the doorway (`Tour.pitchAuto`; any R / F / drag keeps the user's pitch); walking aft while looking aft ends
  FACE_CLEAR 0.90 short of the baggage partition (tour_data aisle `face_x1`; backing up still reaches the cabin_fwd
  stop); in a seat the walk into it turned round (`Tour.seatFlip`: an aft-facing seat from a forward walk), the
  strafe that pushes into the side wall slides back out to the aisle (a seat-type latch carries it to the aisle / gap
  centre line, whichever way the view points); the airstair stop stands inside the door frame
  (BL -0.42, `AIRSTAIR_EYE_BL`) looking -112 / -48 deg down the steps (`pitch_portrait` -38 on portrait screens), its
  hint under the toolbar; the controls hint fades 2.5 s after the first look / walk input; the walnut veneer gets a
  viewer override (`materials.js` VIEWER veneer_walnut: warmer brown, envMapIntensity 0.5 -- the studio in its clear
  coat had read as grey-mauve plastic).
- Viewer propeller in motion (owner 2026-10-03: "the propeller spinning doesn't look too real"; `web/viewer/propblur.js`,
  viewer only, no GLB change): once the blades turn more than a few degrees a frame they cross-fade into a prop disc
  (child of the spinning `propeller` node, plane of rotation on the pivot's thrust axis) whose shader draws the
  motion-blurred blades analytically from blade_1's real geometry sampled at load (per-radius section support
  functions + material-averaged colour + chord angle): each section turned by the commanded pitch and projected along
  the view ray, box-filtered over the exposure sweep S = min(72 deg, max(w / 40 s, 2.5 w dt)) -- the smear spans
  >= 2.5 frame steps, so the blades never alias; at ~290 rpm (60 fps) the pattern is the averaged disc (coverage ~20 %
  mid-span, faint white-tip / red-band rings, alpha mapped for three's display-space blend), plus a faint ghost of the
  smear that only ever moves forward (<= 0.4 blade spacing a frame); lit by the scene with the passing blade face's
  normal; the root boots blur on a band 1.5 mm outside the chrome spinner (its meridian a least-squares quadratic
  through the spinner's, normals from the fit).  Review r1 (PR1-01..04): the faded blades and boots are hidden as
  meshes (`mr.blurHidden`, kept by `Model.updateVisibility`), so they are never picked and their highlight overlays
  are not drawn; the disc is picked as 'propeller' and takes the selection / hover highlight as a tint (`uPbTint`);
  once the blur is complete the chrome spinner is held still against the spin (axisymmetric under the band; turning,
  its facets re-sampled the studio every frame and twinkled).  Spool (`kinematics.js` PROP_RPM / _spool, viewer
  estimate): start to ground idle 1,000 rpm ~12 s, governed 1,000 <-> 1,550 (low-speed mode) / 1,700 (max) ~3 s,
  shutdown run-down ~15-18 s; Off (and P cycling to 0) feathers the propeller (62 deg) as it runs down, it stays
  feathered parked (the demo ends so), and a start from feather unfeathers once it turns 300 rpm.  viewer_test
  `prop_blur_checks` covers the fade / sweep / ghost / axis / modes / spool / pixel see-through and [PR1-01/03/04].
  Review r2 (PR2-01 / 02): the standing dark notch on the band was the disc (it runs on inside the spinner, DISC_IN)
  showing through the held-still spinner's blade cut-outs, drawn after a band that wrote no depth: the band now draws
  first (renderOrder 1), writes depth, is opaque over its whole axial range (+-70 mm against the cut-outs' +-53,
  feathered over BAND_FEATHER 5 mm, its fit lifted to clear every spinner sample) and carries no ghost (black boots on
  a mirror flickered frame to frame; the disc keeps the ghost); boot outline at NZ 32 slices, ends feathered.  The
  blades cross-fade over FADE_DEG [6, 10] (24-40 rpm at 60 fps; [4, 14] left half-faded 'grey glass' blades for ~1 s;
  alpha hashing speckled them).  viewer_test [PR2-01] measures the band's frame-to-frame change, ghost and disc
  see-through on its pixels, [PR2-02] the fade window.
  Review r3 (PR3-01..03): the ghost is GHOST 0.72 over GHOST_SWEEP 0.45 blade spacings (0.35 / 0.7 left a uniform grey
  veil at every governed rpm; the photos and the 50-200 rpm spool frames show a fan of five smeared blades), still
  advancing <= GHOST_STEP 0.4 a frame, none on the band; the disc picks as the propeller only over its root smear
  (`PropBlur.pickCore`, r < 0.45 m), further out the parts behind it take the click and the disc is only the fallback
  (main.js pick()); edge-on its alpha drops to GRAZE_ALPHA 0.55 (|view . axis| < 0.03, full from 0.25: a flat disc's
  coverage tends to 1 there -- an opaque black crescent).  viewer_test: the azimuthal smoothness is measured on the
  true pattern (ghost zeroed), [PR3-01] the ghost's fan (azimuthal sd 4-35 %), [PR3-02] picks through the disc,
  [PR3-03] the edge-on disc translucent.
- Viewer engine sound (owner 2026-10-03: "add sound effect too when propellor starts rolling"; `web/viewer/sound.js`,
  viewer only): pure Web Audio synthesis from built-in nodes (no files, no AudioWorklet / blob: the Artifact CSP),
  driven every frame by the animated state -- the prop spool and a gas-generator model added beside it
  (`kinematics.js GasGenerator`: Ng %, starter to ~18 %, fuel at 12 %, light-off 0.7 s later (~2.3 s), ground idle 60 %
  with the prop ~12 s after the start, starter / igniters off at 50 %, `ngRun` from rpm x blade loading `bladeLoad`,
  run-down -(0.6 + 0.16 Ng) %/s ~18 s; the free-turbine prop stays still -- a <= 4 rpm creep -- until light-off, then
  the START law a0 55 / k 0.14).  Sources: prop blade-passing tone 5 x rpm / 60 Hz, harmonics 1-3 in phase + 4-40
  (Schroeder phases) low-passed by tip Mach, the upper ones modulated by 3-15 Hz turbulence, 1/rev + +-2 dB gusts,
  blade-passage chopped swish, reverse growl + 0.6-1.5 kHz rasp (the tone gains less, the broadband more), feather
  quiet; compressor chord 16 / 21 / 27 / 32 x Ng (100 % = 37,468 rpm assumed) with independent slow drifts, a Q 25
  noise haystack on the main tone and a 25-90 Hz roughness, 1 x Ng shaft tone at -25 dB, inlet hiss, starter whine
  (sines 2.6 / 5.2 x Ng + an 11.3 x gear mesh, low-passed 700 Hz, + a 23.4 x brush whirr to 3.2 kHz: the start is heard
  from its first ~0.3 s, small speakers too), igniter ticks, combustion roar, the light-off a ONE-SHOT 'whump'
  (`SHOTS.light`, 2.2 s buffer: a falling 95 -> 42 Hz thump, a 0.15-1.6 kHz poof, 190 / 430 Hz hollow resonances, a
  rumble; played sample-accurately when `GasGenerator.lightN` counts up) + a roar surge; the swish held up below
  ground idle while the engine burns (r^0.5, faded in over the first ~100 rpm: the blades' 'whoosh' as the prop starts
  rolling; the fuel-off run-down keeps r^1.1).  Modulators: one 4-channel unit-rms looping buffer (gust / turbulence
  / drift / roughness; gust + turbulence swells capped at 1.5 sigma, dips to 2.4: `MOD.lim`); noise: 11.3 / 13.7 s
  loops, each component its own source at its own offset with a +-1.5 % playback-rate wander (nothing repeats); the
  swish / growl / rasp / roar bands rounded above 2.5 sigma (`TAME`, a WaveShaper in sigma units) and the broadband
  chop trailing the tonal pulse by 1/8 blade passage (`CHOP`): the 3/4 view's peak-to-loudness ratio ~10-11 dB (was
  14-22).  Listener = camera: gain (D0 / d)^0.8 (D0 22 m = the 3/4 view, capped 3.0) and closer than D0 never above
  the loudness ceiling (`SOUND.ceil` 1.2 x the 3/4 view's reverse at 1,700 by the rms sum of the levels: a close-up
  at idle +9.8 LU, the loudest state +1.9), air-absorption low-pass, directivity;
  inside the cabin low-passed 0.9 kHz (flight deck) .. 0.5 kHz (aft) plus the whine's band above 1.8 kHz at -18 dB
  (`SOUND.inside.hi`), quieter aft; pan by screen side (x 0.25: ~3 dB at the edge of the view; level only -- an
  interaural delay combed phones' mono sum); rooms = two ConvolverNodes with synthesised stereo IRs
  (`ROOMS`: apron reflections 7-27 ms + 0.4 s tail outside, a boxy ~80 ms cabin inside, ~-12 dB).  Output: master =
  `SOUND.level` 0.595 x volume^2 (default volume 1.0: the slider only attenuates) -> safety limiter (`LIMITER`: fed
  x 0.41, threshold -6 / knee 3 / ratio 20, i.e. from ~+1.7 dBFS of the mix, above every peak of the 3/4 view;
  Chromium's +2.91 dB makeup taken back) -> output curve (`OUT_CURVE`: linear to 0.7, tanh shoulder to 0.95).
  Default listening level (review r2 SR2-01; BS.1770, 3/4 view, volume 1.0): crank -32 LUFS, light-off momentary
  -22 (+7.5 LU over the crank), spool-up -28, ground idle -25, 1,700 rpm -15.4, reverse -11.8, feathered -22 (it was
  -50 / -40 / -42 / -39 / -28 / -24 / -35); dBA steps kept (+10.9 idle -> 1,700, +4.4 reverse); limiter <= 0.05 dB and
  0.006 % of the samples on the output curve in the whole 3/4-view run; the loudest state (reverse 1,700, 6 m in
  the disc plane) -10 LUFS, 0.06 dB average limiting, 0.4 % of the samples on the curve.
  UX: the AudioContext is made by the gesture that starts the engine (Idle / P / the demo button; a later scripted
  start after any gesture: sticky activation) while sound is on -- an orbit drag with the engine off opens no audio
  device (default on; off under automation `navigator.webdriver` unless `?sound=1`), toggle in the Animate tab
  (+ volume) and a floating chip while the engine runs, key M, choice in localStorage `pc12.viewer.sound` /
  `.soundVolume`, suspended when muted, hidden or stopped (a timer, not frames; also when a new context starts running
  with nothing to play).  Tests: viewer_test `sound_checks` ([sound] rows, own page; `viewer.sound.render()` renders
  scripted runs offline through the same EngineVoice, with `instant` steps, the limiter's gain-reduction trace and
  `mute` for diagnostics): spectral lines vs 5 rpm / 60 and 16 Ng, dBA steps, BS.1770 loudness per phase (+ a 250 Hz
  high-passed small-speaker proxy) and through the start (onset, light-off one-shot), the limiter / output curve, tonal
  share / envelope / L-R correlation, close-ups (idle, the loudest state) under the ceiling, noise-loop repetition, the
  flight deck's whine band; the main run checks no AudioContext is made; artifact_test starts the engine with sound
  under the strict CSP (keys M + P).
- Final judge r1 fixes, MODELLING only (2026-10-03; the owner put Blender on hold until the model is signed off, so
  the r1 render-stage changes -- airfield backplate / terrain, wheel close-up catcher, beauty preset tweaks -- stay
  parked on local branch `wip/final-fix-r1-partial`): G3000 PRIME pages in the GLB (above;
  `flightdeck.display_frames()` -> GLB meta 'displays' records each page's frame and atlas rectangle); PC-24 yoke a
  full-U white shield with the grey insert a tongue low in its middle, grips 160, heads r 18 over 42, slimmer paddles
  (L6 / L6B rev F); AI Orange runner of broad 50-85 mm angular bands in 4 lanes over 0.42 m (`cabin.RUNNER`,
  crossing-free) on a navy carpet with transverse pinstripes (lookdev `stripes`, viewer patch), cream bands; dark
  satin titanium (`panel_titanium`) on the PDU face, lower sub-panels, glareshield soffit and centre-stack face;
  push-button blocks on the inner sub-panels, parking-brake T-handle, flat red FUEL / ACS pull paddles, fine pedal
  tread, polished threshold strip, carpeted flight-deck kick panels (lining below the console top), dark-grey
  glareshield leather, a lighter lavender-grey sheepskin; lighter exec back shells with a near-horizontal top edge;
  light metallic blue #7D92BA (LIV-F1-01, glTF metallic 0.65, L5 rev B) and tail-cone strokes x1.35
  (`livery.AFT_STROKES`, LIV-F1-02); airstair two-link rail on the forward stringer only (the aft rail matched nothing
  in photos 130 / 188 through their cameras), grey outer edge wall; chin-inlet lip in the stacks' polished metal;
  smaller grey oil-cooler exit (`vent_dark`); hinge-edge seal strips close the panel-seam slot (no sky line in the
  cabin); club-table slide rails.  The lookdev Blender nodes for the carpet stripes, the fleece fibre / fuzz and the
  display texture (SPEC `texture`) are written but not yet run in Blender.
- Animation review (2026-10-04, after the owner's handrail report; every pivot driver swept in the viewer, parts'
  boxes and nearest-neighbour gaps per pose): besides the airstair handrail (above) two detachments were fixed -- the
  yoke columns are built the full pull travel (YOKE travel 0.090) deeper than 30 mm behind the panel face
  (`flightdeck._yokes`: at full pull they had left their boots, the panel showing through the hole), and the main side
  braces' wing pivot A carries a fitting plate from the bay-liner roof beside the upper link's eye (`gear.MAIN_BRACE_FITTING`
  / `main_brace_fitting`, in gear_bays: the eye had hung 34 mm under the roof); clean: gear, nose clamshells, cargo
  door, flaps / canoes, ailerons / tabs, elevators / trim, rudder, pedals, steering, prop pitch, club tables.
- Model judging r1 fixes (2026-10-03, modelling only, no Blender; L6 / L6B rev G, L4 / L4W notes): INT-M1 the eyebrow
  fascia leans back 15 deg with its foot 30 mm aft of the PDU plane and 18 mm above the bezels (`flightdeck.fascia_x`,
  DETAIL brow_gap / brow_depth / fascia_lean; the leather lip overhangs it), so every PDU bezel top shows from both
  design eyes (`flightdeck.brow_visibility`, L6B row, fit_check 27); INT-M2 headliner soffit bands (`interior.LINING`
  soffit (0.050, 0.400) + flat_drop, `interior.headliner_z`, `cabin.soffit_band` / `ceiling`): a 50 mm step at the
  raised channel's edge (LED strip along its top), a straight band to the side lining at |BL| 0.40 carrying the
  downlights (BL 0.245, ~45 dia) and the PSU pods (psu_bl 0.37 -> 0.32, light satin `psu_housing`); cabin headroom
  is measured to the headliner underside (L6B: 95th 40 / 54 mm); fuselage frames stay 5 mm outside the lining
  (`interior.frame_ring` lining_clear); neutral grey sheepskin (red >= blue), walnut club-table tops (no gloss-black
  inlay), hanging rudder pedals on dark arms from the rudder-bar torque tubes (PEDALS pivot (3.170, 0.440)), overhead
  panel anthracite with white bus lines, chrome bat-handle toggles and the red MASTER POWER guard (Pilatus PRO overhead
  photo, P1046406), a lining-grey centre-post trim with the compass on it (`flightdeck.POST_TRIM`), side consoles grey
  above a dark kick panel with an R 25 edge, titanium trim, chrome cup rings, USB pair; GR1-01 / 03 leg door + hub
  fairing (above); GR1-06 airstair rim metal_dark with steel_dark rivets, a dark recess under each tread; GR1-07
  nose-wheel steering (`gear_nose_steer`, viewer `steer` pivot, state controls.steerDeg); EXT1-01 stack outlet
  full-height (STACK_ROUND b_out 0.098), sooted to the lip, larger root gap; EXT1-02 the cargo door's 120 deg checked
  on photo 130 (free edge on the photo's at 120, 135 ~90 px off: out/tmp/model_fix_r1), its note no longer claims gas
  struts.  Deferred: GR1-02 (brace wing pivot A outboard: the drawn A is BL 1.33 on the Pilatus drawing; moving it
  re-lays the verified over-centre chain), GR1-05 (oleo pre-stroke: the viewer cycles the gear on the ground, an
  extension would push the tyres into the floor); owner flag: the port ledge segment on the open cargo door is the
  approved s/n 3001 anthracite, photo 130 (MSN 3008) shows it light.
- Flight deck r1 GEOM A (owner 2026-10-04: "the flight deck ... 1/10", "the details are drastically missing"; the panel
  area: the owned `flightdeck.py` builders + `model/fd_detail_a.py`, L6 / L6B rev H; the G3000 PRIME / PC-12 PRO
  research of 2026-10-05 applied where it corrects the tables): YOKES re-measured (P1046408 at 0.70 mm/px, P1046409 at
  0.52, the JTF elevation; YOKE hub 140 x 120, the white Y shield -- horns to +/-70, +/-39 at mid-height, a round 45
  foot (hub_bot_w kept: 0.076 is the mid-height width) --, paddle grips r 16 widening to 21 over their top 90, no round
  head): shield domed 8.5 mm with two ridges along a stepped silver V funnel (an abstract bar badge), black horns from
  the grips into its corners, flat-backed D-section paddles (`fd_detail_a.paddle_grip`) with a grained leather inset in
  a moulded rim (`inset`), trim switch / knurled 4-way hat / PTT trigger, TCS on the white horn, red AP DISC on the black
  arm, a satin dark column in an 8-pleat rubber bellows carried by the yoke (`yoke_bellows`, OD 90).  FOOTWELLS
  (`footwell_walls`): dark tunnel-side and outboard walls, the panel's underside (rising 50 mm forward over the
  rudder-bar pivots), the cubby face under the cheek leg with the USB pair; pedals satin black pads with rubber ribs and
  a toe lip.  GLARESHIELD: the lip arch from both Pilatus 'Just the Facts' elevations (research C1: GLARESHIELD lip_dz,
  outboard 15-70 mm lower than rev G, whose face-on photo reading the perspective had lifted; it lowers
  build.cockpit_camera's look point: the crew stops' pitch -21.5 -> -22.1, web/viewer/tour_data.js regenerated), a
  separate rolled black
  lip (leather_black), double stitching 8 / 11.5 mm inside the lip and either side of a crown seam 0.10 forward
  (stitch_thread dashes, 6 mm pitch, `GLARE`), `flightdeck.hood_end_section()` for the sidewall sill (track B), ECS
  eyeballs in dark moulded pods (`ecs_vent`).  GFC 700 (`gfc700`, research M4 on P1046408: four sections, three dual
  concentric knurled knobs FMS / HDG / ALT, the VS thumbwheel in its slot, 13 keys, a raised frame with corner screws,
  the light sensor); BARO knobs on black plates, master WARNING / CAUTION lenses (annun_red / amber), RADIO-CALL plates,
  round recesses and fascia screws (`eyebrow_items`).  DISPLAYS: PDU bezels L 13 / R 12 / top 20 / bottom 20.5
  (`DETAIL pdu_border`), four anthracite corner pads with screws on every PDU (33 / 23 x 10) and SDU (26 / 18 x 9), a
  metal rim round the PDU glass, the MFD's light sensor (`display_details`); the GI 275 as the unit -- PANEL standby is
  its 79.4 round cut-out, `standby_unit` the 82.6 square bezel and 68.3 display (research C2), its knob lower-left (PRO
  P1046410), V-speed placards above it; SDUs 110 x 195 (C6).  LOWER PANEL (`lower_panel`, `LOWER`): the face charcoal
  (panel_dark) round the PDU row and behind titanium plates -- a band under the PDUs, inner / yoke / outer sub-panels
  split at BL 0.290 / 0.575 [M], 2 mm dark seams, pan-head screws --, the cheek LEGS (research M17: the bottom edge
  sweeps down 111 mm over |BL| 0.575-0.660, `z_bot`; the outer plate follows it, O2 / mic sockets on them), rounded yoke
  wells with a satin lip, ICE PROTECTION 2 x 3 rockers, the gear handle with its wheel knob and V-LE / V-LO placard,
  guarded FEATHER INHIBIT, the PARKING BRK lozenge; co-pilot ACS row of four lit caps, rockers, guarded DUMP, OXYGEN
  lever; skirted panel-end knobs.  STACK + PEDESTAL (`stack_shell`, `quadrant`): the waisted stack moulding (0.14 at the
  SDUs -> 0.098 waist -> the quadrant's 0.11, P1046408) with a moulded R 12 edge, the charcoal SDU surround, the recessed
  touch pad in its titanium bezel with a hand-rest lip, COM 1 / 2 VOL knobs dia 19 at BL +/-0.10 on the horns
  (research M6); the quadrant a satin-black plate in a raised gunmetal frame, the framed trim panel (TRIM INTERRUPT,
  ALT STAB TRIM / AILERON TRIM rockers, guarded FLAP INTERRUPT), brush-sealed PCL / flap slots, detent ticks, the
  striped reverse gate, the PCL a dark arm under a pewter cylinder handle, the flap paddle, 5 + 2 skirted lighting knobs
  with dimmer arcs (JTF p.18), the CCD palm dome (PEDESTAL ccd / ccd_wl: 100 x 85, top 385 [M]) with its trackball in a
  ring, rocker, keys and two green LEDs.  Legends are abstract light strokes (geometry; no text).  The flight-deck
  shared materials (leather_black, stitch_thread, rubber_black, annun_*) are `assemble.MATERIALS`' 'flight deck shared'
  block (since the merge; the track's stand-ins had the same values).  Checks: `test/fit_fd_a.py`
  28 (pedals over their travel, the 95th's shoes and legs vs the footwell walls >= 10 mm: 10.1 / 27.5 / 20.9), 29
  (yokes over the pull travel and 60 mm of push x roll +/-70 vs the panel detail >= 3 mm: 16.1) and 29b [open] -- at
  the full [E] push (-90 mm) the grips reach within ~8 mm of the bare lower-panel face wings level and cross it from ~45
  deg of roll: the switch blocks under the inboard grips are hit; owner decision: a shorter [E] forward travel (~-65 mm)
  or accept; consistency rows select the yoke / pedal parts and the lip's leather_black (materials moved).  Triangles
  (RES 2):
  flight_deck 35.6k -> 87.3k, yokes 13.75k -> 22.6k, pedals 1.9k -> 3.0k (per-part caps in build.INTERIOR_BUDGET:
  flight_deck 150k, yoke 24k, pedal 3k; the flight deck is in build.LOW_FINE, so phones get the same detail).
  Deferred: legends on a shared legend atlas (never built: legends stay geometric strokes), the pedestal front height
  (no PNL-04 figure in hand), PANEL.mfd_z (research C7: a camera fit first).
- Review r4 (owner 2026-10-04: every lens >= 8, the rendering / picture and smooth-curves lenses included):
  CABIN LOOK (NAV8-01 / INT8-01, viewer only): inside the closed cabin (`U.cabinIn`, Model.updateCabin) the interior
  materials take `materials.js CABIN_LOOK` instead of the studio x cabinAO -- no key light through the skin (it had been
  x CABIN.inside^2 = 2.6 on every up-facing surface), the studio's diffuse light weighted by the surface's facing (`diff`
  0.75 facing the floor .. 1 up), its reflections by where they point (`spec` 0.06 toward the floor / seats .. 0.3 toward
  the headliner / windows: the studio's bright floor had mirrored in every panel and display), clear coat and sheen
  likewise, and per-material `CABIN_TRIM` [share of the fill, own factor]: the lining the whole cove / window fill
  (`fill` 3.4), the leathers part, the flight deck's grey lining round the windshield 0.3, the sheepskin 0.6; with
  CABIN.inside 0.8 and +0.3 EV.  Tuned at the photo-fitted cabin_fwd (P1046406) / pilot / fd_cabin views: headliner
  ~209, walnut ~57/38/25, lower side panels ~65-75, runner hue 30 deg / saturation 0.72, overhead panel ~21, display
  bezels ~18 (all were 87-101); ?cabKey= ?cabDiff= ?cabSpec= ?cabFill= override them.  Sheepskin fibre (INT8-04): a
  `fleece` patch -- band-limited world-space fBm tufts (~4 mm) in its albedo (0.62-1.15) and a surface-gradient bump,
  sheen roughness 0.8.  viewer_test [T14] measures it through a material-ID pass (`MAT_MASK`: each group in a flat colour
  with the stage camera, the screenshot's pixels per material, eroded by one pixel).  Viewer overrides (EXT8-01 / 03):
  `deice_boot` roughness 0.6 / specular 0.18 / env 0.35 (satin neoprene: the 0.25-rough dielectric mirrored the white
  studio silver -- 170-215 at the wing_0459 camera, now ~65-80; photo 17-61); `paint_blue` / `paint_navy` env 0.75 (the
  studio fill in the clear coat had greyed the ultramarine to periwinkle).
  TOUR (NAV8-02..05): a seat-type latch stays one into the aisle (a strafe pointing back at the turned seat had held the
  eye on the aisle's edge), a released strafe stops at once round the seats (`Tour.strafeUp`, keys and the walk pad); a
  walk into a crew seat turns to its stop's pitch (tour_data seat region `pitch`, -21.5); the stop button / live region
  name where the eye is once walked away (`regionLabel`, hooks.changed on a region change; the menu marks a stop only at
  it); the airstair stop -106 / -48 on landscape screens (was -112: the walnut divider filled the right), -98 / -51 on
  portrait ones (`yaw_portrait`: the treads in the upper middle) with the walk pad right and translucent there (`.aside`)
  and the hint under the toolbar on phones too (both edges had been set: a full-height card).  viewer_test [T15]-[T18]
  drive real key events.
  MODEL: nose leg (WG8-01, photo 3008 188 at ~690 px/m): `gear.NOSE_STRUT` -- the oleo cylinder to 0.77 of the strut, a
  fixed steering-housing casting (WL ~0.82 -> 0.65) with the taxi lamp on its front (NOSE_LAMP frac 0.56), the steered
  collar with the upper torque-link lug, ~0.08 m of chrome, flat A-plate links (32 / 26 mm deep, broad across) in a
  flattened V, knee 0.14 m ahead at WL 0.59 (188: ~0.17; retracted, ahead of the strut is down -- at 0.17 it crossed the
  closed clamshells, fit_check 11); main shock (WG8-03): its lower eye in a clevis on the trailing arm ~90 mm ahead of /
  135 mm above the axle (MAIN_SHOCK, MAIN_SHOCK_CLEVIS), a forked top lug with a pin.  Cowl-front crown (GEO8-02):
  knots 1.044-1.68 sampled from a monotone-slope blend (`fuselage._top` comment: the old knots put a 1.2 deg concave dip
  at STA 1.18-1.20 that kinked every studio streak behind the cowl front), skin rows every 6-12 mm ahead of the chin
  columns; drawn crown STA 1.09-3.0 within 2.7 mm.  Leg-door blister (GEO8-03): `gear.BLISTER_SIGMA` 30 / 20 mm (no hard
  highlight along its edge; depth 29.7 mm, stowed 28.9 below the skin).  Tailplane tip (GEO8-04): horn-balance sections
  40 points per surface with the flat front face a separate creased patch (`HORN_LOOP_N`), 3 mm rows along both raked
  LEs (`STAB_RAKE_STEP`, `HORN_TIP_STEP`: the nose moves 2.08 x the row pitch aft; at 10 mm the triangles across it
  sheared into Z-shaped highlight steps); tip facet area 0.9 / 1.2 %.  Root fillet (EXT8-04): `ROOT_FILLET_ROUND` run
  0.40 / behind 0.25 (curvature along x above the foot ~1/3), `ROOT_FILLET_TAPER` 7.30 (a 0.23 m aft fade).  Chin lip
  (EXT8-02): its own neutral polished aluminium `inlet_lip` (#CFCCC6, rough 0.12; livery SURFACES, lookdev SPEC).
  Light tier (GEO8-01): `build.LOW_FINE` (seat_, yoke_, pedal_, brace_, gear_nose) rebuilt and refined at RES 2 in the
  PC12_RES=1 process (facet area: pax seats 22.5 -> 2.3 %, crew 17.6 -> 3.4, yokes 25.6 -> 8.2, pedals 50 -> 3.1, braces
  51 -> 8.2; +0.3M triangles); iPhones (no navigator.deviceMemory) with a >= 1080 px screen get the full-model chip,
  whose 25 s now counts from the loading screen's end (viewer_test [GEO8-01]; it had run out unseen behind a slow first
  render).  viewer_test CR1-01 sets Auto's measured still budget aside (the heavier light tier's SwiftShader frames cut
  it), CR1-02 compares the colours 2 px inside the blue areas (a whole-mask median moved with the edge softness).  Interior: CB panels small black heads on white collars, green legends (INT8-02); the
  pedestal's trim panel (black bezel, guarded TRIM INTERRUPT, split ALT STAB TRIM and AILERON TRIM rockers, legends),
  flap gate with detents, guarded FLAP INTERRUPT, titanium palm pad (INT8-03: the cream square was the amber box);
  `cabin.RUNNER` 0.9-2.4 m stripes, 5-60 mm breaks, more jogs, 70 % orange / 18 % light grey (`carpet_light`, no longer
  cream) / 12 % grey (INT8-05; the sheets do not draw the runner); one recessed dark pull and a latch plate on the
  lavatory's bi-fold doors (INT8-06).  Deferred: INT8-07 shade cassettes (they sit in the window reveal, which the fit
  checks keep clear: needs an L6 reveal-profile change), WG8-02 leg-door lean (the documented LD-1 deviation, L4
  call-out), GEO8-05 rudder tab bay / flap canoes / fin root facets (not visible at the review cameras), the chin lip's
  face width (the drawn lip outline; a re-trace needs the drawing review).
- Flight deck r1 GEOM B (owner 2026-10-04: the flight deck "1/10", "the details are drastically missing"; track B = the
  surround, branch wip/fd-geom-b; `model/fd_detail_b.py`, called from the owned builders `flightdeck._consoles /
  _overhead / _post_trim / _divider`, `interior.build_lining` and `seats.crew_seat`): B1 / B2 the windshield and
  side-window reveals are moulded FUNNELS (`fd_detail_b.glazing_mouldings`, added to `interior_lining` as reveals,
  `_reveal`): from the lining hole (the pane outline, as before) to a VISIBLE outline on the glass that lies inside the
  pane by a margin per edge (`GLAZING_TRIM`: windshield sill 3 / A-pillar 32 / roof 42 mm, the centre post's moulding 94
  mm wide at the glass -- P1046408 through the fitted camera; side window sill 12, aft 175, top 85, front 35 mm: the
  oval opening of the NGX panorama S15 / AOPA, the trim hiding the D-pane's aft end), profile 1 - (1 - tau)^2.4 (tangent
  to the lining, rolled into it, 1.5 mm proud over its hole edge), a 4 mm black 'seal' lip 4-5 mm inboard of the glass
  hiding the retainer band (the 8 mm first built drew a heavy black outline round every pane from the seats; the photos
  show a hairline); pane outlines matched edge by edge (`_pane_pairs`, corner bisector anchors).  The old flat reveals of
  the four flight-deck panes are gone (build_lining skips them).  The side-window reveal is LEATHER below WL 2.23
  (`SILL`: the padded sill continuing the glareshield leather at the window's front-low corner, wrapping the aft-lower
  corner), two stitch seams, abstract placards on the sill's narrow forward part (`SILL` placards: a black / white one
  and two red ones, sized by the strip's local width -- further aft the reveal fans out and they had drawn as skewed red
  parallelograms ~2x their size; legend strokes 3 rows, thin); the old fairing tube over the centre post (`_post_trim`,
  INT-m7) is replaced by the two reveals' post edges + the lining strip between them (`POST_TRIM` now only names the
  group).  B3 CB panels (`fd_detail_b.cb_panels`, group cb_panels): table `SIDE_CONSOLE` cb_panel (3.630, 4.160, 0.505,
  0.700) = the PAIR's extent, new cb_split (3.900, 3.910) and cb_grid ((12, 4), (11, 4)) (research C3: NGX POH Fig
  7-13-2 / 3; the bottom on the console top, P1046409 / AOPA); black plates 2.5 mm proud in a 6.5 mm panel_dark bezel
  frame (4 mm recess), per row black breaker heads on white collars, a label strip of abstract legend cells (`CB` label:
  backlit `fdb_cb_legend` strokes on the black plate; the RH rear block light silver `fdb_cb_label` strips with dark
  strokes and cell dividers, AOPA), a dim lit bus band (`fdb_cb_glow_*`: LH blue, RH front yellow / green, rear white),
  row marks as 1-4 dots; above it the ledge with the long stowage slot (zip teeth, pull), a satin edge strip, red
  placards, the map light, the operating-limitations placard.  B4 overhead (`overhead_panel`, `overhead_pod`): table
  `OVERHEAD` x (3.86, 4.07), w 0.47 (research C4 / C5; the P1046406 fitted camera puts this outline on the photo's panel
  within 3 px, rev G's 20-25 px off); panel_dark bezel with R 24 corners, 45 deg chamfer, plate 6 mm down, the photo's
  section frames / bus diagram (white strokes, dashed where drawn so), abstract title bars, 18 bat toggles (hex nut,
  satin lever, ball), FIRE WARN / LAMP / STARTER squares, guarded RUN lever, LANDING / PULSE paddles, MASTER POWER
  guard, screws; a pod moulding (lining) whose face lies in the panel plane (the headliner falls 28 mm across the panel)
  blended into the headliner by a smooth minimum, the two eyeball outlets on it; AUTOLAND cup kept.  B5 post
  (`post_fittings`, group post; `POST`): a round satin grab-handle bar (r 11.5, a dark screw hole near its top) from the
  pod down to its V end fitting -- a faceted satin block twice the bar's width, its top cut into a V round the bar, its
  aft face two planes on the centre ridge, on a rounded panel_grey mounting plate (P1046406 / 08 / 10, the Pilatus
  overhead photo) --, then the deviation-card holder (light card, fine table lines) and the E2B-type compass with a
  round black bezel, four screws and a square card window (dark card, white ticks, red lubber line), facing aft: the PRO
  simulator photo's order down the post.  The s/n 3001 photos (P1046406 / 08 / 09 / 10, the Mexico and AOPA photos) show
  the post below the V fitting EMPTY: the compass follows the simulator (an owner question: keep it or not).  B6 consoles
  (`console_fittings`): leather armrest pad with stitching aft of the CB pair, map pocket with an elastic lip, keypad
  (P1046409), sidewall eyeball. B7 crew seats (`seats.py`): sheepskin rims carry a silhouette shag (`pillow(shag=...)`,
  `SK_SHAG` 5 mm clumps of 33-57 mm sampled every 8 mm; the judged-grid band limit stays on the inner waves only),
  rotary buckle (black body, satin rim, ridged knob, four tongues), cam-lock adjusters, shoulder-strap guides on the
  back top, track locating holes at the POH notch pitch; 55.4k triangles per crew seat (cap 56.1k).  B8 divider
  (`divider_fittings`): half-round walnut aisle edges with a titanium inlay (the faces stop half a thickness short of
  DIVIDER open_bl), crew O2-mask cups on each wall's forward face outboard (NGX POH 7-19-2, panorama), smoke-goggle box
  (LH), headset hooks, RH document pocket, access latches, curtain-track end caps, and on the extinguisher
  (`extinguisher_fittings`) a buckle with its lever on each strap, a heel cup, the pressure gauge on the valve head
  (silver bezel, white face, green band, needle), the safety pin with its pull ring, a white label with abstract strokes.  B9 headliner (`headliner_fittings`,
  `visors`): dome lights, speaker grilles (S15 positions), smoked sun visors (`fdb_visor`) stowed above each side
  window (STA 3.975-4.30, |BL| 0.375-0.485; AOPA visor photo): a rounded panel (forward end nearly round, `visor_r` R 45
  / aft R 30) in a 5 mm satin rim with an outer wall, carried by a flat black arm along its outboard edge (satin slot
  line, slider button) from a pivot clamp on a round base plate at the forward end (`HEAD` visor_*: the first build's
  square black sheet on a rail read as a hanging slab from the seats); the PRO's round centre dome-light bezel
  at port (`HEAD` dome_c). Groups hung on interior_lining: `fd_detail_b.CEILING_GROUPS` (overhead, cb_panels, pod, sill,
  visors, post, headliner_fd).  Every interior_lining piece is built under `res.coarse()` (explicit segment counts:
  identical in both tiers).  New materials: assemble block 'flight deck detail B' (fdb_cb_glow_blue / green / yellow /
  white and fdb_cb_legend / fdb_cb_label with emissive, fdb_visor, fdb_hose_green), the same values in
  render/lookdev.py's 'flight deck detail B' SPEC block (lookdev_materials.json / web/viewer/materials.json
  regenerated); the shared names (leather_black, stitch_thread, rubber_black, legend_*, annun_*) are the 'flight deck
  shared' block of assemble.MATERIALS / lookdev SPEC since the merge.  This track also carried the planned seed's
  pieces (that commit never landed): build.INTERIOR_BUDGET per-part caps / total 814k, LOW_FINE += flight_deck, fd_;
  fit_check runs test/fit_fd_a.py / fit_fd_b.py when present.  Checks:
  fit_check 30 (the glass >= 2 mm from every interior piece near it, no crossing), 30b (the surround fittings seated
  within 3 mm), 31 (crew seats at full aft, height extremes, both headrest locks, arms down / up >= 5 mm from the
  divider / console fittings); 22b leaves the moulded surround (`_fd_glazing`) out of both its parents and its fittings
  (it runs from the lining hole to the glass; the cabin reveals as before).  Legends are geometry (thin quads in the
  legend / lit colours), not tiles of a legend atlas (none was built).
  The surface quads of the CB panels, sills and placards (`SurfMap.quads`) are split into <= 12 mm pieces so they follow
  the curved lining (one flat chord across a CB block stood ~0.5 mm off it: the RH rear block's label strips and their
  dark strokes z-fought, fit_check 26).  Build: 2.43M triangles, 41.0 MB (interior 579k of 814k: fd_consoles 8.6k,
  fd_divider 10.7k, interior_lining 134k, crew seats 55.4k), light tier 2.01M, 33.4 MB;
  seat_pax3-6 34,834 / 34.8k print OVER as at the base.  L6 draws the CB pair (both phantom boxes); L6 / L6B regenerated
  with the table changes (rev label untouched: the merge writes rev H); viewer_test [T12] NAV2-05 / [T13] NAV3-02 take
  the airstair stop's pose from web/tour_data.py (they still expected r4's -48 deg / BL -0.42 after tour review r5 and
  failed on the base).  Verified on this build: fit_check OK (26 none; 30 nearest 3.9 mm, 0 crossings; 30b all seated;
  31 nearest 10.3 mm), consistency_2d3d 138 PASS, viewer_test 216 / 216.  Owner decision (2026-10-05): the compass stays on the post
  (the PRO simulator photo and the NGX POH have it; the s/n 3001 photos show the post empty below the grab handle's V fitting).
- Flight deck r1 MERGE (2026-10-05; wip/fd-geom-a, wip/fd-geom-b and wip/fd-look merged into wip/stage2-drawings in that
  order): no source conflict but consistency_2d3d's yoke rows (track A's per-side selection from the yoke parts kept)
  and the L6 / L6B rev H description, which now names both tracks' table changes (YOKE, GLARESHIELD lip_dz, PANEL
  standby_unit / sdu_wh, PEDESTAL ccd / ccd_wl; SIDE_CONSOLE cb_panel / cb_split / cb_grid, OVERHEAD x / w); the generated
  files were rebuilt on the merged parameters (tour_data.js regenerates identical to the merged file; L1-L5, the GA and
  the sections only changed their PDF timestamps and were left alone).  The planned seed commit never landed: its
  shared materials are now a 'flight deck shared' block in assemble.MATERIALS and render/lookdev.py SPEC (leather_black,
  stitch_thread, rubber_black, legend_plate, legend_lit, annun_amber / red / green / blue: the tracks' stand-in values;
  the `SHARED_FALLBACK` setdefaults are gone; lookdev_materials.json = web/viewer/materials.json regenerated).
  The combination broke two viewer rows -- [FD-L6] (panel_408b p50 62, < 40 band 35 %) and [T4] (fd_cabin median 66):
  track A's charcoal face round the PDU row (panel_dark, the consoles' near-black) rendered 25-45 where P1046408 at its
  fitted camera reads the face ~90 (final judge r1: 88-105, like the sub-panels), and the titanium plates came out 64
  (look target 72) on the new geometry.  Fix: the moulded face and the cheek-leg faces take a new satin `panel_graphite`
  (0.13 / metallic 0.45 / rough 0.40: a shade darker than the titanium, as the Garmin / brochure renders; the edge
  returns, ECS pods, yoke wells, the stack's SDU surround and the consoles stay panel_dark), and materials.js
  CABIN_TRIM panel_titanium 0.45 -> 0.6, panel_graphite [0, 0.85] (both SPEC_KEEP): titanium 72, graphite 64,
  p50 68, bands 31 / 47 / 13 %, fd_cabin 70 (its histogram has a gap at the median: 49 % < 66, 52 % < 75 -- the row
  swings with a percent of pixels).  Other panel_408b values after the merge: carpet 4, consoles 9, glareshield 62
  (lip 57 / underside 35: the rolled lip is track A's leather_black, so [FD-L3]'s leather_glareshield columns are the
  hood), yoke 202, sheepskin 106, eyebrow fascia 119, displays 98.  Budget: the bake's split (+28.7k) counts in the
  per-part caps, fd_divider 15k -> 18k (16.8k built).  Build: 2,530,569 triangles / 44.65 MB, light tier 2,111,944 /
  37.03 MB (the flight deck at RES 2 there too); interior 681k of 814k (flight_deck 104.9k, fd_consoles 13.7k,
  fd_divider 16.8k, interior_lining 133.7k, crew seats 55.4k); the bake ~1.5 min on 444k interior vertices.  Verified:
  fit_check OK (131 ok; 29b the one open owner item), consistency_2d3d 143 / 143, drawing.master (L6: 25 texts crossed
  by lines, as track A's rev H; L4: 1 leader pair, as before), drawing.sheet / verify (SVGs unchanged), viewer_test
  225 / 225, web/package.py verify OK (_AO kept), the Artifact bundle 109.9 MB in 2 publishes (61.9 + 48.0 MB; meshopt
  17.2 + 14.6 MB, gzip 25.7 + 21.4 MB, every base64 part <= 11.5 MB).  Photo comparisons of the 8 standard views
  (photo | c5560f1 | look only | merged): out/tmp/fd_merge/gallery_* (gitignored: they embed the photos).  Open after
  the merge: 29b (full [E] push); the stack's sunlit titanium surround at panel_408b 172 against the photo's 138 (the
  pad 123 / 122 matches); the ledge placards above the CB panels read as long red bars from the pilot seat; the eyebrow
  fascia a little light (119 against the photo's 100-113).
- Flight deck fix r1 (2026-10-05; the flight-deck judges' round 1: owner 4.5, fidelity 6.5; the yoke findings FDO1-01 /
  FID-FD1-01 / 02 are the separate L6Y track's, wip/fd-yoke, and were left alone here).  No table changed (L6 / L6B not
  regenerated); builder detail, the bake and the viewer's light:
  LIGHT (FDO1-05, viewer): the interior sun moved to az 25 / el 45 (`outside.js SUN`, ahead and to starboard over the
  windshield: the hood with the posts' shadows across it, the pedestal, the armrests and seats sunlit, the panel in the
  glareshield's shade, as P1046409's sun patch on the co-pilot's fleece; az 125 / el 40 lit only the stack face from
  the seats) at intensity 8 (`scene.js LOOK.sun`; ?sunaz= ?sunel= ?sun= ?sunrad= for look development); the window-light
  law's hard cap `min(x, gain.z)` is a soft knee `2 gain.z (1 - exp(-x / 2 gain.z))` (`U.cabinKnee`, ?cabKnee=0 restores
  it) with `CABIN_LOOK.gain` [22, 1.6, 1.5] (was 18): the flight deck's median window light 0.11 x 18 had put most of its
  surfaces on the cap -- one flat level, the gradient toward the glazing gone.  `lining_flightdeck` gets CABIN_TRIM
  [0, 0.72] (the posts / surrounds next to the glazing ~90-100 at the seat stops, P1046410's posts 88-97).
  BAKE (FDO1-03 / FID-FD1-05, `build.py` / `cad/ao.py`): a second presplit box `AO_SPLIT_BOX_HI` (STA 2.85-4.30, WL
  1.75-2.75: the glareshield, the windshield / side-window surround, the posts, the flight-deck ceiling) to
  `AO_SPLIT_HI` 35 mm (+30k triangles), the window sky / bounce at `AO_SKY_K` 24 directions (was 16), and both bake
  channels filtered on the flight deck (x < `AO_DENOISE_X` 4.75) by `ao._denoise`: a normal-aware Gaussian over the
  representatives within `AO_DENOISE` 35 mm (the per-vertex estimates' noise x the law's gain had drawn the sooty blots at
  the post feet and on the hood; the cabin keeps its edge smoothing as tuned for T4 / T14).  Bake ~2.3 min a tier.
  SHEEPSKIN (FDO1-02 / FID-FD1-06, viewer `materials.js` fleece `ridge` mode): round tufts with dark crevices between
  them in three Worley layers ([freq, lo, hi, dist]: 380 / 140 / 40 per m, each faded to its mean where sub-pixel, the
  crevices pressing the normal in), the sheen lobe modulated by the same pile (unmodulated it laid a uniform blue-grey
  veil over the shaded fleece: sd ~1 level against the photos' 10-18), a neutral sheen colour and a base a shade less
  blue (viewer `sheepskin` color / sheenColor; P1046408 measures B - R ~20-25 in the shade: lavender-grey kept); the
  look L6 value-noise clouds (0.4 .. 1.1 at 12-20 mm) read as camouflage.
  FINISHES (FID-FD1-04, viewer): `specIn` (the cabin law's reflections x this inside) on the satin metals -- titanium
  1.7 (also rough 0.32, brush anisotropy 0.75, a warmer rose-grey base as P1046408's R ~ B > G), graphite / gunmetal 1.5,
  pewter 1.3 -- and the black leathers 1.4 / 1.3 with a coarser, deeper grain (freq 450, 0.4 mm).
  MODEL DETAIL: unlit smoked caps `annun_off_red / _amber / _green` (assemble 'flight deck shared', lookdev SPEC,
  SPEC_KEEP) on the brow's master WARNING / CAUTION and the ACS caps' splits, the TRIM INTERRUPT cap black with a white
  frame stroke (FID-FD1-03: every photo shows them dark on the parked aircraft); the GFC 700 knobs ~19 mm proud with a satin
  ring between outer and inner knob, charcoal key caps 4 mm proud (FID-FD1-07); the V-speed placards as text-like rows
  (two blocks of word-length strokes, the AOPA Garmin close-up; the first build's full-width bars read as a louvre); the
  eyeball-vent pods 76 mm across in the face's graphite (rr + 0.014; were 92 mm, FID-FD1-08); the display corner pads
  `panel_dark` with smaller screws (FDO1-06: the AOPA Garmin close-up shows the dark chamfered corner inserts -- kept,
  not dropped); the quadrant's brush seals in a new dark grey `brush_seal`, a chrome collar at the PCL handle's root,
  abstract POWER / flap-angle / caution-line strokes (FDO1-07; the handle stays satin pewter: P1046409 / 10 in daylight
  show it light, the throttle photo is a dark-graded studio shot); the side-window sill's stitching one tone-on-tone
  seam (`SILL stitch_rows` (10,), panel_grey dashes) and its placards one red + two dark at ~half length, the CB ledge's
  red placards 70 / 85 mm (FDO1-04); the windshield's heating bus bars -- two 0.8 mm dark-metal lines 15 / 23 mm inside
  the visible edge along each A-pillar and the centre post, 2.5 mm inside the glass (`GLAZING_TRIM wire_*`, fit_check 30 /
  22; FID-FD1-09).  OUTSIDE (FDO1-08, `outside.js`): the apron shown at 0.86 of its albedo (the image-based light keeps the
  full value, `GROUND.envK`), three generic parked single-engine aircraft and a tug (pre-lit low-poly shapes, no
  markings), cladding / door-leaf seams and grime on the hangar facades.
  Calibration after the change (panel_408b, viewer_test [FD-L2]-[FD-L6]): carpet 5, consoles 8, glareshield 63 (lip 71 /
  underside 44), yoke 206, sheepskin 127 (121 / 127 / 144), flight-deck lining 95, titanium 87; p10 6, p50 71, bands 31 /
  48 / 13 % (the gain 27: at 22 the darker shade put 33 % under 40); the CABIN_TRIM sheepskin 0.55 -> 0.52 for the soft
  knee.  Tests: fit_fd_b's 30b counts the flight-deck glass as a mounting surface (the bus bars sit on it; 30 keeps every
  piece >= 2 mm off it, so only the 2-3 mm band beside the glass can be seated by it).  Budget: interior 712.7k of 814k
  (flight_deck 126.2k -- +21.3k from the bake's finer split --, interior_lining 141.2k).  Build: 2,561,542 triangles /
  45.19 MB, light tier 2,143,157 / 37.57 MB (the flight deck at RES 2 there too).  Verified: fit_check OK (131 ok, 29b the
  open owner item), consistency_2d3d 143 / 143, viewer_test 224 / 225 with [sound] 'M mutes' timing out under load (the
  context still 'running'; `--only sound` 25 / 25), web/package.py verify OK (meshopt 16.5 + 14.1 MB), the Artifact bundle
  110.8 MB in 2 publishes (62.3 + 48.5 MB), artifact_test 70 / 70.  Photo / before (113f7d6) / after sheets of the
  standard views and the judges' close-ups: out/tmp/fd_fix_r1/cmp_* (gitignored: they embed the photos).  Deferred: the
  yoke, its column and wells (FDO1-01, FID-FD1-01 / 02: the L6Y track); the A-pillar / post section (FID-FD1-09's
  rounded tubular post: the moulded surround is GEOM B's fit to P1046408 through the fitted camera -- a re-profile is a
  surround change); a fuzzy fleece silhouette shell (the seats keep `SK_SHAG`'s shag rims).
- Flight deck fix r2 (2026-10-06; the flight-deck judges' round 2: owner 5.0, fidelity 5.5; the yoke findings FID-FD2-01
  stay with the L6Y track, wip/fd-yoke).  No table changed (L6 / L6B not regenerated); builder detail, two viewer
  mechanisms and the light.  Look development ran in one viewer page (out/tmp/fd_fix_r2/ld.py: a job queue of in-page
  material / sun changes, per part:material medians from an ID pass) instead of a page load per try.
  PALETTE (FDO2-01, FID-FD2-03): the hood's brightness from the seats (148-150 at the crew stops) was its sky SHEEN, not
  its diffuse (a diffuse cut changed nothing) -- `materials.js PART_TRIM` (new: per part:material over CABIN_TRIM /
  VIEWER, one interior clone per part where it has an entry; `fill`, `specIn`, `sunIn`, `roughness`) gives
  'flight_deck:leather_glareshield' specIn 0.6 / roughness 0.55 / sunIn 0.6 (~90-100 in the shade, ~115-130 in the sun;
  the sills of the same leather 'interior_lining:leather_glareshield' fill 0.8 / specIn 1.15, [FD-L3] reads them at
  panel_408b: 54); `lining_flightdeck` CABIN_TRIM 0.72 -> 0.5 and a warmer base (0.10, 0.098, 0.095) (posts / surround
  98-102 -> ~80); the titanium warmer -- R > G > B, VIEWER color (0.245, 0.215, 0.19), CABIN_TRIM 0.6 -> 0.8 (panel_408b
  sub-panels 85 / 87 / 93 -> ~102 / 100 / 100, P1046408 114 / 105 / 105); panel_grey (0.21, 0.195, 0.18) and
  panel_graphite (0.13, 0.122, 0.115) warm; pedestal_gunmetal darker (0.088, 0.086, 0.088) on the stack's flanks too
  (`fd_detail_a.stack_shell`: were titanium, 73 against the photo's 46) and the stack's lower face in the graphite;
  pcl_pewter (0.110, 0.106, 0.104) / metallic 0.55.
  LIGHT (FDO2-02, FID-FD2-04): the sun az 25 / el 45 -> az 20 / el 30 (`outside.js SUN`; a sweep az 20-90 / el 28-35 in
  the page: at az 20 the hood carries the centre post's and the A-pillars' shadows with hard edges from both crew stops,
  az 60 lit the pilot's sill and console, az 90 the seats -- P1046408's sheepskin 127 -> 192), PCF radius 3 -> 2
  (`scene.js LOOK.sun`); a per-material sun factor `sunIn` inside (`materials.js`, the interior law's direct light).
  SURROUND (FDO2-03): `fd_detail_b._reveal_zones` -- each glazing funnel's rows from the glass to tau 0.39 in a darker
  satin `lining_fd_reveal` (CABIN_TRIM 0.5: ~55), the lining beyond, and a satin edge bead `trim_satin` (half round r
  2.8 mm sunk 30 % into the funnel, every 12 mm, 13 profile steps) along the row between them -- the light-catching
  rolled edge of P1046409 / 10 / AOPA (the leather sill keeps its finish: its top carries the placards); a satin strip
  `panel_silver` down each outer sub-panel's outboard edge from the band to the leg's foot (`LOWER edge_strip`, P1046409's
  vertical titanium swoop beside the breakers).
  PEDESTAL (FDO2-04, FID-FD2-07): the PCL a turned grip (`fd_detail_a.PCL_GRIP`: a flared, rolled port end with a dished
  face, two finger flutes, a chrome ring inboard of the flare, the same 80 mm x <= 40 mm envelope) on a forked arm
  (`QUAD pcl_tines`: two dark tines either side of the slot centre and a clevis block in the slot); the palm tray a
  5 mm recess with graphite walls, a titanium floor and a rolled light-satin bead (`STACK pad` recess 0.003 -> 0.005);
  16 flutes on the lighting knobs.
  MINORS: sheepskin (FDO2-05, FID-FD2-02; viewer) -- the fleece patch's Worley layers [[650, 0.90, 1.04], [300, 0.86,
  1.05], [120, 0.92, 1.04]] (the 40 / m clump layer gone, the albedo range ~0.86-1.05 instead of 0.60-1.10), bump 0.85 ->
  0.5, the tufts stretched along the vertical (`stretch` [1, 0.65, 1]) and their cells warped (`warp` 0.35), the base /
  sheen R = G (0.262, 0.232, 0.276) / (0.32, 0.29, 0.34): panel_408b 119 / 122 / 143, the local 16 px sd 7.5 -> 3.5;
  sunIn 0.45 (the sunlit co-pilot back 184 -> 172); bus bars (FDO2-06, FID-FD2-05) one per edge, 9 mm inside the visible
  edge, 0.7 mm, `busbar_bronze` (was two dark-metal lines 15 / 23 mm in); the unlit caps (FID-FD2-06) near-black glass
  -- annun_off_red / amber / green (0.045, 0.030, 0.028) / (0.045, 0.038, 0.026) / (0.028, 0.040, 0.032), roughness 0.20
  under a 0.05 clear coat (saturation <= 0.3); overhead (FDO2-07) chrome bat levers ~15 mm proud thrown fore / aft
  (`OVH toggle_throw`, `bat_lever`: a revolved stem flattened into a bat) on a knurled ring and a chrome hex nut, the
  square buttons a smoked lens in a dark rim with a legend stroke; outside (FDO2-08, FID-FD2-08) the apron shown at
  0.34 (0.62 still read ~215 through AgX; the image-based light keeps its albedo, `GROUND.envK` 1.08), stains, tyre
  marks, oil spots, tie-down rings, a second taxi line, the hangars' / parked shapes' / vehicles' shadows baked into
  the apron (`boxShadow`), a distance haze on the apron and the pre-lit shapes (`GROUND.haze`, `hazeK`), a fuel truck
  off the port beam and cones; CB panels (FID-FD2-09) each breaker on a white collar sleeve, 3 mm higher, LH bus bands
  white (the blue read as diagonal lines), the ledge / sill placards a muted `placard_red_dim`; crew seats (FDO2-09)
  an anthracite piping welt round the headrest front and a stitch seam across it, chrome face plates on the cam-lock
  adjusters, a woven grain on the harness (viewer `harness` leather patch, freq 1500).  New materials (assemble
  'flight deck fix r2' / lookdev SPEC): busbar_bronze, placard_red_dim, lining_fd_reveal, trim_satin, stack_gunmetal.
  Tests: [FD-L1] now reads the sky over the cowl (upper third of the window pixels, >= 225) and the whole window >= 170
  (the darker apron the judges asked for puts the whole-window median ~210); fit_fd_b 30b also seats the new
  surround / overhead / CB materials.
- Flight deck fix r2b (2026-10-10, the same judges' round 2 continued after a restart; no table changed, L6 / L6B not
  regenerated).  WINDSHIELD RIM: the white line under the windshield from both crew stops (it had grown with r2's
  lower sun) was the mask skin's inner face under the retainer / skin overlap, seen through the lowest ~30 mm of the
  pane past the 9 mm deep seal and lit as cockpit lining by the sun (ray casts from both design eyes: 0.5-0.8 deg of
  `fus_fwd:trim_black` + `glazing_retainer` between the reveal and the sky) -- `fd_detail_b.GLAZING_TRIM` ws_margin's
  sill 3 -> 34 mm (the funnel rises up the glass: from both eyes and the fd_cabin eye no ray reaches an exterior
  part; the hood now meets the glass in a dark band as in P1046409 / 10), and the side windows' sill 12 -> 19 mm (the
  retainer's glass-side face, ~0.3 deg of polished metal: a white line along each sill).  PALETTE / SHEEN (FDO2-01,
  FID-FD2-03): `materials.js CABIN_LOOK refl` [0.7, -0.3, 0.6, 0.35] -> U.cabinRefl: the satin
  metals' reflections inside (`REFL_DIR`: titanium, graphite, gunmetals, pewter; not the displays, bezels, caps nor the
  leathers -- [FD-L3] / [FD-L6] at panel_408b) weighted by where they point -- toward the glazing kept, toward the dark cabin 0.7 -- so
  plates that mirror the windshield keep their sheen and the rest drop (0.3 tried: panel_408b median 62, 34 % of the
  pixels < 40, [FD-L6] out); the eyebrow fascia `panel_grey` CABIN_TRIM [0, 0.72] (122-126 -> ~104-108 from the stops
  and at panel_408b; P1046408 96-104); the hood (PART_TRIM 'flight_deck:leather_glareshield') specIn 0.35, sunIn 0.3
  and a sky-blue `specularColor` (0.75, 0.87, 1.0) on its sheen (130 -> ~100 from the pilot stop with the sun on it,
  P1046409 / 10 60-96 with B - R 25-45: the interior IBL's desaturated zenith had left its sheen grey).  At
  panel_408b (P1046408 boxes): eyebrow 115 -> 99 (photo 96), sub-panels 89 / 95 -> 85 / 87 (83 / 98), tray 125 -> 119
  (120), stack face 98 -> 93 (106-131); [FD-L6] bands 32 / 47 / 13 %.  Sun: an az 20-55 / el 30-32 sweep from the
  crew stops showed no stronger readable patch than az 20 / el 30 (az 55 lights the pilot's sill across the cabin), so
  the r2 sun stays.  FLEECE (FID-FD2-02 re-measured): r2's calm pile measured a local 10 px sd of 4-6 at panel_408b
  against P1046408's 10-17 (a flat lavender felt in the close-ups): the 120 / 260 per m curls at about twice the
  contrast, the crevice term's smoothstep now a parameter (`fleece.edge` 0.3 .. 0.8 with its mean `rm` 0.45; the
  default thin borders read as cobbles on a 90 / m layer and as marble veins at 70 / m), bump 0.65.  Scratch: the
  look-dev queue out/tmp/fd_fix_r2/r4 / r5 / r6 (ld2.py jobs, per part:material medians), photo | judges' before |
  after sheets out/tmp/fd_fix_r2/r6/cmp_*.jpg.  Not changed (reported): the A-pillar / surround width from the seats
  (the approved L2 glazing outline + GEOM B's surround fit; a slimmer tubular post is a drawing change), the yoke
  (wip/fd-yoke).  Tests: [FD-L1] reads the sky over the cowl in the upper QUARTER of the frame (at both crew stops the
  apron's far edge lies at 0.24-0.26 of the height: the upper third reached into the apron r2 darkened and measured
  211 / 221, B - R 8 / 7 -- r2's own threshold had never passed; now 248 / 251, B - R 11 / 9); viewer_test 224 / 225 in
  the full run (149 min beside another worktree's runs) with [FD-L1] the one failure, then `--only fdlook` 10 / 10 after
  the band change ([FD-L3] glareshield 53, lip 61 / underside 37; [FD-L6] p50 69, bands 31 / 48 / 13 %); fit_check
  (1 open owner item, unchanged) and consistency_2d3d 143 / 143 on the final geometry; artifact_test 70 / 70.
- Flight deck fix r3 (2026-10-11; the flight-deck judges' round 3: owner 5.5, fidelity 6.0; the yoke FDO3-09 stays with
  wip/fd-yoke).  No table changed (L6 / L6B not regenerated: nothing they draw or check moved); builder detail, a
  near-field occlusion pass in the bake, the viewer's cabin light / materials.  Look development in one page again
  (out/tmp/fd_fix_r3/ld.py jobs: in-page material patches / uniforms, per part:material medians); photo | before |
  after sheets out/tmp/fd_fix_r3/cmp_*.jpg.
  LARGE SURFACES (FDO3-01, FID-FD3-01): the titanium sub-panels, tray and outer plates a brushed METAL (`materials.js
  VIEWER panel_titanium`: metalness 0.75, roughness 0.26, a near-neutral base; the `brush` patch now also streaks the
  reflection -- `spec` with the fine streaks, `band` / `bandLen` / `bandW` 10 mm x 16 cm bands at +-12 %, `pcBrushK`; at
  metalness 0.85 with 4 mm bands at +-30 % it read as walnut-grain wood from the crew stops) whose reflections pointing aft
  see a CABIN PROBE (`CABIN_LOOK probe` / `probe2`, U.cabinProbe / cabinProbe2: the dark cabin 0.55, the side windows
  abeam, the lit cabin through the divider opening with its windows as azimuth stripes, the headliner -- the REFL_DIR
  metals had mirrored the open apron behind the aircraft, one flat tone); panel_graphite a weak brush, the gunmetals an
  isotropic 3.5 mm bead-blast grain.  `fd_detail_a.lower_panel`: the outer (PARKING BRK) plate ends on the sub-panel
  row's line, sweeping down `LOWER outer_drop` 26 mm over |BL| 0.615-0.70 (`z_foot`); the cheek leg below it is the dark
  cove (new material `fd_cove`, assemble / lookdev 'flight deck fix r3', CABIN_TRIM 1.45: ~40, P1046408 ~41) with a dual
  USB charger and its legend stroke (`LOWER usb`); the plates' and the band's walls `panel_dark` (the 2 mm seams read as
  dark lines); a satin rolled lip (`LOWER lip_r` 4.5 mm, trim_satin) along the row's bottom edge; the palm tray's floor
  dished 2.5 mm (`STACK dish`).  Contact darkening: `build.bake_interior_ao` adds a near-field pass over the panel /
  glareshield / stack box (`AO_CONTACT_BOX`): the box's broad triangles (>= `AO_CONTACT_AREA` 1.2 cm^2) split to
  `AO_CONTACT_SPLIT` 16 mm (cad/ao.presplit `min_area`), occluders sampled every 2.5 mm, steps 4-22 mm, 2 mm
  representatives (cad/ao.bake `cell`), multiplied in as contact^0.6 (`AO_CONTACT_POW`): the plates' seams, the bezels'
  feet, the fascia under the lip, the tray walls (~37 s; flight_deck +62k triangles at RES 2).
  SHADE / HOOD (FID-FD3-02): ahead of the divider the interior's indirect diffuse light takes a cool daylight tint
  (`CABIN_LOOK shade` [#c8d6ff at unit luminance, 0.42 x (0.6 .. 1 facing the glazing)], U.cabinShade; the sun keeps its
  warmth; shade B - R ~+10-17 at panel_408b); the hood's rolled lip / underside -- all panel_408b sees of the hood --
  `PART_TRIM 'flight_deck:leather_black'` F90 1 (specularIntensity 1, F0 kept by a sky-tinted specularColor), roughness
  0.38, specIn 1.9: the band 68 -> ~105 (P1046408 102); the hood top 'flight_deck:leather_glareshield' F90 1 too and
  sunIn 0.3 -> 0.22.
  POSTS (FDO3-02, FID-FD3-03): the slab's width is the approved L2 glazing (+ GEOM B's surround fit) -- its change stays
  the deferred owner / drawing review; its shading: `fd_detail_b.round_post_normals` (build.build_parts, after the
  refinement, before the bake) turns the A-pillar's vertex normals (interior_lining lining_flightdeck / lining_fd_reveal /
  trim_satin within `POST_ROUND` r_in .. r_out of `post_axis`, the midline of the two pane outlines on the OML) to a
  rounded section, never more than acos(min_dot 0.30) off the surface's own (fit_check 23); a satin bead `trim_satin` r 8
  mm, ~8.6 mm proud, down the post's lining strip (`POST_ROUND bead`, its ends diving under the lining) and two flush
  countersunk fasteners at its ends (`post_fasteners`, interior.build_lining); the bead lies on the lining (axis 0.6 mm in
  front of it: sunk 1.5-3 mm only 84-89 % of it stood > 0.5 mm proud, fit_check 22b).
  SHEEPSKIN (FDO3-03, FID-FD3-04): the fleece patch (`VIEWER sheepskin.fleece`) 95 / 200 / 520 per m curls, warp 0.12, no
  stretch (the r2 warp's sines lined the cells up into a herringbone, a 70 / m coarse layer read as marble), bump 0.9, a
  24 / m `clump` field (+-12 %, soft clusters) and a `rim` term (the albedo lifted up to +60 % below n.v 0.5: the fibre
  tips along the silhouette), a lighter sheen; `seats.shag` adds a ragged fringe of 18-26 mm tufts (`SK_SHAG_FINE` 2.8 mm)
  to the 0.7 x coarse clumps on rims sampled every 6.5 mm (`SK_SHAG_STEP_R3`).
  MINORS: sun (FDO3-04) -- `scene.js LOOK.sun` box +-1.35 m round the glareshield / seats (centre 3.95 / 0 / 2.05), 4096
  px on desktops (0.66 mm texels; phones 1024, 2.6 mm), normal bias 0.0035 (phones 0.006); PCL / quadrant (FDO3-05,
  FID-FD3-07) -- `fd_detail_a.PCL_GRIP` a domed port end and two 2 mm finger flutes, the chrome ring moved inboard of the
  flare, the brush seals a fringe of alternating tufts every 1.6 mm (`_bristles`), bolder flap detents, a second legend
  stroke by every lighting knob; crew seats (FDO3-06, FID-FD3-05) -- `seats._crew_back_rear`: a padded map pocket
  (leather_black, two-tone) with an elastic welt on the shell's rear face, two stitched seams up the back and one across
  (`CREW_BACK_REAR`, ray-cast onto the shell), the harness weave coarser / deeper (VIEWER harness freq 1100); outside
  (FDO3-07) -- eave shadow bands, door-leaf seams with a lit edge, a door track, personnel door, down pipes and a plinth
  on the facades, a warm haze in the sky's lowest degrees (`SKY.haze`); NOT the building behind the glare at panel_408b:
  P1046408 through its fitted camera puts a tall block 12-14 deg right of the nose ~21 deg up and a long hall 20-31 deg
  right, roof 15-18 deg up, from the cabin eye, but P1046410 / P1046409 (the same aircraft and session) show open blue
  sky down to the hood at those azimuths and elevations from the crew seats; a nearer hall there (22-50 deg right, eaves
  ~19 deg up) filled the right windshield at the pilot stop and the Cockpit preset ([FD-L1] the pilot's sky over the
  cowl 250 -> 203, [BV-5] 145 < 150) and was taken out again -- the crew-seat photos win (`outside.js HANGARS` comment); GTC pages (FID-FD3-06) -- `g3000_pages.gtc_page` redrawn as the photos' dark list
  pages (the COM box in a green frame, dark-grey key rows with light legend bars and numerals, a flight-plan list / an
  approach page, the icon row along the bottom); floor specks (FID-FD3-08) -- `flightdeck._plinth_floor`'s slot strips
  follow the plinth's rounded corners 2 mm inside (they had left slivers open to the skin either side of its aft end);
  fit_fd_b 32 rasterises the flight-deck floor plan (3 mm cells inside the lining, footwell front to divider) under the
  interior's surfaces.  Budgets: flight_deck 68k -> 92k, crew seat 17.5k -> 19.5k, interior total 370k -> 390k (RES 1
  figures; RES 2 x2.2 / x3.4).  Display bezels (fix r3: P1046408's satin black bezels read 37-58 round the displays,
  the model's 24 -- a black field round every page): `PART_TRIM 'flight_deck:bezel_black'` specIn 2.0 (37 at
  panel_408b, ~42 from the pilot stop, 40 at fd_cabin -- [T14] keeps them <= 50; 3.0 read 48 / 51); the palm tray, a
  brushed mirror of the apron behind the aircraft as streaked frosted glass from the crew stops (141 in the pedestal
  close-up): the brush patch's `up` [n0, n1, + roughness, streaks kept] -- `VIEWER panel_titanium brush.up` [0.40,
  0.55, 0.32, 0.15], the up-facing faces (the tray, normal y 0.57; the sub-panels, soffit and plates face aft / down)
  satin and isotropic (alphaT -> roughness^2): a soft gradient, 132 (look-dev out/tmp/fd_fix_r3/ld3, tray_cmp.png).
  Not changed (reported): the A-pillar / surround WIDTH from the crew seats (the approved L2 glazing outline + GEOM B's
  surround fit: a slimmer post is a drawing change for the owner's drawing review; r3 changed its shading and detail
  only), the yoke (wip/fd-yoke).  Verification: both tiers rebuilt (2,699,206 / 2,268,281 triangles, 47.65 / 39.82
  MB; interior 850k of 858k, flight_deck 199k of 202k, crew seats 66.0k of 66.3k, interior_lining 184k of 190k; the
  aft cabin seats' 34,834 against the 34,800 cap flagged OVER as in r1 / r2, unchanged); fit_check incl. fit_fd_b 32 OK (1 open owner item, unchanged),
  consistency_2d3d 143 / 143 on the final geometry; L6 / L6B not regenerated (no table they draw or check changed);
  web/package.py and the Artifact bundle (116.4 MB, 2 publishes) verify.  viewer_test: the first full run 223 / 225
  with the nearer hall ([FD-L1], [BV-5] -- above); after its removal the full run 201 / 201 checks ([FD-L1] the pilot's
  sky 248, the co-pilot's 251; [BV-5] 154; [T14] bezels 42 / 40) until the sound section's first click timed out (the
  drag's coast renders 15-35 s SwiftShader frames on the shared machine, load 8-13: HEAD's viewer measured the same,
  15-21 s, on the same page), so that one click waits SHOT_TIMEOUT (`sound_checks`; no check changed) and `--only sound`
  passes 25 / 25; artifact_test 70 / 70.
- Flight deck fix r5 (2026-10-12; the flight-deck judges' round 4: owner 6.0, fidelity 6.3; the yoke stays with
  wip/fd-yoke).  No table changed (L6 / L6B not regenerated: nothing they draw or check moved); builder detail and the
  viewer's look.  Look development: the full viewer in one page (out/tmp/fd_fix_r5/ld.py jobs, per part:material medians
  from an ID pass, `photomed.py` the photo's medians under the same masks at the photo-fitted cameras) and, for the
  fleece, a seats-only LAB page (out/tmp/fd_fix_r5/lab: `subset.py` cuts the crew seats out of the GLB, the viewer's own
  materials.js patch under a room light, ~30 s a try instead of ~4 min a view).
  A-PILLARS (FDO4-02 / FID-FD4-02): the post's width was the moulding, not the approved glazing -- `fd_detail_b
  GLAZING_TRIM` ws_margin's pillar edge 32 -> 8 mm and sw_margin's front edge 35 -> 6 mm (side projection: P1046408
  through its fitted camera shows the side window's glass right behind the post), and along the post the two funnels are
  ONE ROUND TUBE (`POST_TUBE`, `_post_tube`: each column a quarter ellipse from its glass edge, leaving it square, round to
  the post's midline 7 mm proud of the lining, faded over 16 % of the axis at both ends -- the post flares into the
  glareshield and the roof -- and from WL 2.24 up, below it the side window's leather sill) in its own darker satin
  `lining_fd_post` (assemble / lookdev 'flight deck fix r5', CABIN_TRIM 0.5, SPEC_KEEP: its round section carries the
  narrow highlight); r3's turned normals (`round_post_normals`), lining-strip bead and fasteners went (the strip lies
  hidden behind the tube).  At panel_408b the left post measures 126 / 117 / 108 px (rows 240 / 300 / 360 of the
  1920 x 1440 frame) against P1046408's 116 / 108 / 84 (it was 299 / 278 / 258); the tube is ~70 mm across at the glass,
  ~48 mm deep.  The approved L2 outline (the panes 25 mm apart in side projection, ~43 mm across the skin) does NOT force
  a wider post: no owner question.  fit_check 30: every piece >= 2 mm off the glass (nearest 2.9 mm, a bus bar).
  FLEECE (FDO4-01 / FID-FD4-01): `materials.js` fleece `pile` mode (replaces r1-r3's `ridge` Worley curls, which read as
  printed lichen / stone): `tufts` layers -- arms < 0 a CURLY WORM layer (the ridges of a domain-warped two-octave smooth
  noise at 200 / m, pow 1.7: short, bent, interlaced bright strands with dark between them, the 4-6 mm curls of P1046408
  / 09 / 10 packed tight), else a TUFT layer (Worley cells of random height `hgt` -- a short tuft sits in its neighbours'
  shade, so the dark between them is broken, not a crackle net -- with a soft dome, optional loops and spiral curls; here
  60 / m, 0.84-1.08) --, `lock` 15 / m +-12 % matted groups, fibre streaks, `rim` 0.25 tip lift, the sheen on the tips;
  stretched along the pile's flow (down the vertical faces, forward over the tops).  The lab tried 17-60 mm tufts and
  locks (rock / crazy paving), spiral curls and boucle loops (scales, craters), contour whorls (marble, caustics), fat
  worms (leopard print) before the worms.  A warm grey with a mauve cast (VIEWER color (0.30, 0.262, 0.28): R ~ G < B
  under the cabin's cool light), CABIN_TRIM 0.52 -> 0.42 ([FD-L5] at panel_408b 90-130).  Geometry (`seats.shag`): the rims' 33-57 mm clumps and 18-26 mm fringe replaced by a
  ROLLED edge -- `SK_ROLL_OUT` 7 mm outward at the rim's middle rows, half at its edge rows, with a soft 4-8 cm wave of
  `SK_WAVE` 1.8 mm, rims sampled every `SK_RIM_STEP` 10 mm (crew seat 66.0k -> 57.7k triangles).
  PEDESTAL (FDO4-03 / FDO4-05 / FID-FD4-03): the PCL a PADDLE built to PEDESTAL pcl_grip's 36 x 80 x 72 (the r2 / r3
  turned cylinder used only its width: a 40 mm can) -- `fd_detail_a PCL_PADDLE` / `pcl_paddle`: a superellipsoid across
  the slot (flat rounded ends `e_end` 0.38, an oval section `e_sec` 0.8) narrowing to 0.70 of its width and 0.72 of its
  depth at the foot (P1046408 / 09: from behind a trapezoid ~80 wide at the rounded top), tipped forward 12 deg, on a
  flared dark neck with a chrome collar; satin pewter kept (P1046408 / 09 in daylight show it light -- the Pilatus
  throttle photo is graded ~2 stops dark, its lavender sheepskin reads dark grey there too), out of REFL_DIR (the cabin
  probe's stripes ran through it as a glass jar), specIn 0.8 / roughness 0.45.  The palm tray's floor its own matte
  `tray_titanium` (CABIN_TRIM 0.3), its bead a 4.5 mm dark bronze `trim_bronze` (was a 6 mm light satin tube: a plastic
  frame), the stack's face AND its moulded edges `stack_gunmetal` (CABIN_TRIM 0.45; the edges as titanium bands read as
  light strips down the stack), the quadrant frame `pedestal_gunmetal` 0.6: at panel_408b the tray 113 against
  P1046408's 117, the stack 82 / 76; from above (P1046409) the tray ~106, the face round it 51-60.  Trim panel: bezels /
  caps x1.3 (`QUAD trim_k`), each item's title in two rows of word-length legend strokes, the AILERON TRIM bezel's white
  outline with LWD / RWD marks.
  MINORS: the titanium sub-panels warmer and satin (FID-FD4-04: VIEWER panel_titanium (0.245, 0.225, 0.205), roughness
  0.26 -> 0.34, the brush streaks' share 0.15 -> 0.07, bands +-12 -> +-7 %); the hood's sun patch (FDO4-04 / FID-FD4-05:
  PART_TRIM 'flight_deck:leather_glareshield' sunIn 0.22 -> 0.07; the sun's PCF radius 2 -> 3, `scene.js LOOK.sun`: the
  patch's edge showed the texels on the grazing-lit hood); the footwell (FDO4-04: `CABIN_LOOK.foot` [0.8, below WL 1.72
  (glTF Y), ahead of STA 3.95]: the diffuse x 1.8 there on all but the up-facing floor and the crew seats' fleece (which
  reaches into that box) -- the pedal arms, linkage and side walls in a soft light, the carpet near-black as P1046408
  ([FD-L2]: x 2.5 everywhere put it at 26, [FD-L6]'s dark share under 10 % and the cushions' fleece at 154-159),
  ?cabFoot=);
  the sky as SEEN a clear blue (`outside.js SKY.seen` [(0.50, 0.72, 1.0), sin e 0 .. 0.14]: x that tint above the horizon,
  the image-based light keeps the untinted sky so the calibrated cabin light does not move): the pilot stop's sky over
  the cowl 254 -> (221, 241, 255), L 237, B - R 34 against P1046410's (207, 232, 251); the crew seats' pose (FID-FD4-06, NOT
  changed): through the fitted panel_408b camera P1046408's cushion tops sit ~45 px (900 px frame) above the neutral
  seats', full forward or full up alone each ~40 px of the L6 travel; parked there in the viewer (35 mm forward + 25 up,
  then 40 up alone) the seats covered the side consoles at that camera, which the photo shows clear beside its raised
  cushions ([FD-L2] lost every console pixel) -- the seats / consoles disagree with the photo in plan, an L6 table
  question, not the travel; the default stays the neutral SRP, `model.js SEAT_PARK` ?seatpark=1 shows the 40 mm up.
  Build: 2,673,206 triangles / 47.21 MB, light tier 2,247,573 / 39.47 MB; interior 824.5k of 858k (flight_deck 199.6k of
  202k, crew seats 57.7k, interior_lining 175k).  Verified: fit_check OK (132 ok, 1 open owner item -- 29b, unchanged),
  consistency_2d3d 143 / 143, viewer_test `--only fdlook` 10 / 10 ([FD-L1] the sky over the cowl 234 / 238; [FD-L2]
  carpet 14, consoles 18; [FD-L3] glareshield 60, lip 70 / underside 44; [FD-L5] sheepskin 102 / 107 / 128, lum 107;
  [FD-L6] p10 15, p50 73, < 20: 14 %, bands 29 / 48 / 13 %), web/package.py verify OK (meshopt 17.2 + 14.7 MB).  Photo |
  before (d3673c2, the judges' r4 renders) | after sheets: out/tmp/fd_fix_r5/ld/cmp_*.jpg (gitignored: they embed the
  photos).
