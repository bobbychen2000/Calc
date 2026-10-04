# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (97 parts, ~2.37M tris of which the interior ~525k, ~40 MB
incl. the 0.5 MB G3000 page atlas, 16-bit normals; built at the tessellation quality `PC12_RES` = 2, `cad/res.py`;
hinge pivots in node extras), its light tier `out/pc12_low.glb` (the builders' own grids, `PC12_RES=1`, as judged in
review, but its seats, yokes, pedals, braces and nose leg as in the full model -- `build.LOW_FINE`: ~1.92M tris, ~32 MB,
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
                                #   materials, 27 the PDU bezel tops visible from both design eyes; the main-gear leg
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
python3 test/viewer_test.py     # viewer checks + screenshots (headless Chromium / SwiftShader, ~25-40 min, 215 checks; slower on a
                                #   loaded machine -- rerun once on a screenshot / click timeout); [T1]-[T18] the interior tour
                                #   (--only tour: those alone on the desktop page, ~6 min; --only prop / phone / picture / sound likewise)
python3 test/viewer_test.py --only sound --sound-out DIR   # the engine-sound section alone (~2 min): its checks + the
                                #   offline renders DIR/pc12_engine_sequence.wav + spectrogram.png, pc12_sound_loudest /
                                #   _close_idle / _steady / _pilot.wav (default out/tmp/viewer/sound)
python3 web/package.py          # static viewer bundle -> dist/ (gitignored): meshopt GLBs (both tiers; the build's own
                                #   quantisation kept: gltf-transform's API, reorder + EXT_meshopt_compression), vendored
                                #   three.js, verify step
python3 web/package_artifact.py --out DIR && python3 test/artifact_test.py --dir DIR   # the claude.ai Artifact bundle
                                #   (~90 MB as base64 text parts: meshopt 15 + 11 MB, gzip of the full model 23 MB for desktops and of
                                #   the light tier 16 MB for phones without WebAssembly; ARTIFACT.json 'publishes' = groups of <= 64 MB,
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
  built at), `fold` (door children -- the airstair handrails `door_airstair_rail*` / `_cable`: rotate by
  `open` x clamp((door fraction - window[0]) / (window[1] - window[0])) about their own axis, `follows` the door),
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
  `airstair.py` (the airstair door's inner body, treads, stanchions and the folding handrail children; the door opens
  145 deg -- its free edge on the 145 deg line in MSN 3008 photos 130 / 188 through the fitted cameras --, free edge
  ~0.29 m off the ground, 3 treads + the bottom step at the free edge in equal risers from the sill); the flight deck's
  side consoles `fd_consoles` and walnut divider `fd_divider`, the yokes and pedals are child parts of `flight_deck`;
  the cabin floor + runner + tracks `cabin_floor` and the club tables are children of `cabin_interior`; side-wall /
  headliner lining `interior_lining` by the L6 LINING law -- 40 mm inside the OML at the crown, 85 mm at the sides,
  `interior.lining_offset` -- with window reveals and lined door wells; frames at the Pilatus frame stations;
  interior triangles are budgeted in `build.INTERIOR_BUDGET` (250k, crew seat 14k, cabin seat 12k at PC12_RES=1; at
  RES 2: 550k / 47.6k / 34.8k, built 525k / 44.8k / 34.8k) and printed by the build; the viewer's cockpit camera is `pc12_meta.json` 'cockpit' = `build.cockpit_camera()` at the L6 design
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
