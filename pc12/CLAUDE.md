# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (98 parts, ~2.81M tris of which the interior ~945k, ~49.9 MB
incl. the 0.5 MB G3000 page atlas and the interior's baked occlusion / window light `_AO`, 16-bit normals; built at the tessellation quality `PC12_RES` = 2, `cad/res.py`;
hinge pivots in node extras), its light tier `out/pc12_low.glb` (the builders' own grids, `PC12_RES=1`, as judged in
review, but its seats, yokes, pedals, braces, nose leg and the flight deck as in the full model -- `build.LOW_FINE`; the
yokes are one mesh at every RES, model/yoke3d.py: ~2.37M tris, ~42.0 MB,
16-bit normals too; phones load it (and its gzip when
WebAssembly is refused), the Specs panel -- and once a stage chip on capable devices -- offer the full model there), `out/pc12_meta.json` (build steps, BOM, construction lines, dimension checks; `stats.low` = the light tier),
`out/drawings/L1..L6B` (the Stage-2 drawing set, drawn from the parameters: `python3 -m drawing.master`; L1-L5 the
exterior -- lines plan, glazing, openings, general arrangement, L4W wheels & tyres (`model/wheels.py` tables), livery
--, L6 / L6B the interior arrangement and its checks, L6Y / L6Y2 the yoke's design drawings),
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
                                #   flight-deck floor closed in plan, 33 the yokes over roll x pitch vs the panel / U
                                #   recess / J band / glareshield / pedestal (exact distances both ways, >= 3 mm, over
                                #   the whole travel; 33a the column in its opening / sleeve, 33b the full push every
                                #   5 deg of roll, 33c the column vs the J band / panel >= 0.5 mm, 33d where the column
                                #   shows, its finish dark); the main-gear leg
                                #   door vs the skin cut-out every 0.5 % over 90-100 %, flush outside its tyre blister);
                                #   '[open]' rows are known conflicts in the approved parameters that need an owner
                                #   decision (they do not fail)
python3 test/fit_fd_p.py        # first-principles flight deck 34-36 (also run by fit_check): prints on their surfaces,
                                #   knife-edge ratchet, every flight-deck material in interior.FD_CONSTRUCTION (~30 s alone)
python3 test/fd_dev.py --save && python3 test/fd_dev.py --out out/tmp/fp/dev.glb   # a dev GLB: the interior rebuilt +
                                #   baked over a pickled base build (~6 min a loop; not the shipped model)
python3 test/fd_cap.py DIR --glb ../out/tmp/fp/dev.glb [--views pilot,panel_408b,..] [--query '&fp=1']   # the
                                #   standard flight-deck views (crew / cabin stops, Cockpit, panel_408b, 11 close-ups)
python3 test/fd_identity.py     # hashes every flight-deck mesh (refactors must keep them byte-identical)
python3 test/consistency_2d3d.py   # the built GLB projected / sliced against the parameter outlines of sheets L1-L6
                                #   (L4W: wheels / tyres / nose yoke, 2 mm; L6Y: the built yokes in yoke-local mm vs the
                                #   L6Y front / side views, cover, inserts, pads, switch axes, 1.5 mm)
python3 test/yoke_mesh_check.py # the Stage-3 yoke mesh (~4-7 min): triangles vs build.YOKE_BUDGET (as built: cad.res
                                #   + the column), cad.res a fixed point on the cover, watertight (no same-way edge
                                #   inside a material), folds, slivers, corner
                                #   normals vs the solids, KNOBS (rev P: no corner normal > 60 deg off its own face, none
                                #   > 30 deg on a sub-0.01 mm^2 face), the frame's highlight error (interpolated vs exact
                                #   normals on the faces seen from the aft hemisphere: z-buffered visibility classes; rev
                                #   O: per face on the heads, by area on every visible round, the trim face's lunes), the
                                #   pilot yoke's legends in reading order
python3 -m drawing.master       # the Stage-2 drawing set L1-L6B incl. L4W from the parameter modules (~3 min;
                                #   `python3 -m drawing.master L6 L6B` for the interior sheets only, `L4W` the wheels,
                                #   `L6Y L6Y2` the yoke design drawings: interior.YOKE_DESIGN through the solids of
                                #   model/yoke_geom.py, exact views / sections, disk cache out/tmp/yoke_geom_cache --
                                #   keyed by yoke_geom.design_key(), which hashes yoke_geom.py's SOURCE: any edit there
                                #   re-runs every cached view / section / acceptance check and the mesher's DC / cut /
                                #   vis / deci stages (hours); printed finishes live elsewhere, e.g. model/yoke_legends.py)
python3 -m drawing.yoke_overlay # the yoke solids ray-cast through the photo cameras -> refs/cache/overlays/yoke
                                #   (private; landmarks, curated grip rows per band, pads, inboard neck -> deviations.json,
                                #   the L6Y2 photo-check tables)
python3 -m model.yoke_checks    # acceptance of the yoke solids: exact 2-D fields, nothing above the trim face / shield,
                                #   no untabled section cusps / creases (adaptive scan), smooth join fields, pads exposed
                                #   as drawn, vertex normals vs analytic (printed on L6Y2)
python3 -m drawing.sheet        # hidden-line drawings (~30 s) -> out/pc12_ga.*, out/pc12_sections.*
python3 -m drawing.verify       # measures the SVG itself against the dimensions
# dev viewer (three.js r160 expected at web/three_local -> a checkout of mrdoob/three.js tag r160):
python3 -m http.server 8765 --directory .   # then test/shot.py renders headless screenshots:
python3 test/shot.py out/x.png "f=../out/pc12.glb&cam=-9,4,-3&tgt=0,1.4,6.6&fov=40"
#   options: ortho=1&s=HALF_HEIGHT, only=part_prefix,.., hide=.., clip=1 (cutaway), f2=other.glb&f2edges=1
python3 test/viewer_test.py     # viewer checks + screenshots (headless Chromium / SwiftShader, ~60-85 min, 236 checks; slower on a
                                #   loaded machine -- rerun once on a screenshot / click timeout); [T1]-[T18] the interior tour
                                #   (--only tour: those alone on the desktop page, ~6 min; --only prop / phone / picture / sound likewise;
                                #   --only fdlook: [FD-L1]-[FD-L11] the flight-deck look, ~30 min; --only avx: [AVX-1]-[AVX-16] the
                                #   live G3000 PRIME pages, ~20 min)
node test/avx_model_test.mjs    # the live avionics' engine / atmosphere model (engine.js, env.js) against the POH / TCDS
                                #   figures and the start / feather / shutdown timings (pure JS, ~2 s)
python3 test/viewer_test.py --only sound --sound-out DIR   # the engine-sound section alone (~2 min): its checks + the
                                #   offline renders DIR/pc12_engine_sequence.wav + spectrogram.png, pc12_sound_loudest /
                                #   _close_idle / _steady / _pilot.wav (default out/tmp/viewer/sound)
python3 web/package.py          # static viewer bundle -> dist/ (gitignored): meshopt GLBs (both tiers; the build's own
                                #   quantisation kept: gltf-transform's API, reorder + EXT_meshopt_compression), vendored
                                #   three.js, verify step
python3 web/package_artifact.py --out DIR && python3 test/artifact_test.py --dir DIR   # the claude.ai Artifact bundle
                                #   (~122 MB as base64 text parts: meshopt 18 + 16 MB, gzip of the full model 28 MB for desktops and of
                                #   the light tier 24 MB for phones without WebAssembly, every part <= 10.9 MB; two publishes 58.5 + 63.1 MB; ARTIFACT.json 'publishes' = groups of <= 64 MB,
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
  column axis, + `travel_pull` / `travel_push` (MODEL axes) x |pitch command| + `rest` (the free yokes' parked offset,
  interior.YOKE rest, rev P) x (1 - |pitch command|); the elevators follow that position, `kinematics.js pitchPos`, rev
  Q: parked they hang ~8 deg trailing-edge down), `pedal` (`pedal_LL/LR/RL/RR`: hanging
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
  interior triangles are budgeted in `build.INTERIOR_BUDGET` (415k + 2 x (YOKE_BUDGET 43k - 24k), crew seat 19.5k,
  cabin seat 14k at PC12_RES=1; at RES 2: 951k / 66.3k / 40.6k, built 945k / 63.9k / 40.2k (all-lens fix r2), with
  per-part caps for the
  flight deck -- flight_deck 211k (built 207.5k), yokes 43k each at every RES (42.9k: model/yoke3d.py meshes them once),
  pedals 3k (3.0k), fd_consoles 30k (16.3k), fd_divider 18k (16.8k), interior_lining 190k (175k); counted after the
  interior-light bake's splits; flight deck fix r2 raised the crew seat 56.1k -> 59.5k and interior_lining 175k -> 190k,
  fix r3 the crew seat -> 66.3k, flight_deck 150k -> 202k, the total 814k -> 858k; the yoke merge the yokes 24k -> 43k
  and flight_deck -> 211k) and printed by the build; the viewer's cockpit camera is `pc12_meta.json` 'cockpit' = `build.cockpit_camera()` at the L6 design
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
  The model carries NO markings (owner decision: no logos, registration, serials, flags or lettering) -- except, since
  2026-10-24 (owner: "Real English words"), the cockpit placards: generic English switch / breaker / scale / limitation
  text printed on the flight deck (model/fd_print.py), still no brand names; and the live display pages' labels.
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
- Flight deck r1 GEOM A (owner 2026-10-04: "the flight deck ... 1/10", "the details are drastically missing"; the panel
  area: the owned `flightdeck.py` builders + `model/fd_detail_a.py`, L6 / L6B rev H; the G3000 PRIME / PC-12 PRO
  research of 2026-10-05 applied where it corrects the tables): YOKES -- the rev H paddle yokes (shield, paddles,
  bellows) are superseded by Yoke rev M (below).  FOOTWELLS
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
  sweeps down 111 mm over |BL| 0.575-0.660, `z_bot`; the outer plate follows it, O2 / mic sockets on them), the yoke
  columns' U recesses (Yoke rev M), ICE PROTECTION 2 x 3 rockers, the gear handle with its wheel knob and V-LE / V-LO placard,
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
  (the rev H yokes over the pull travel and 60 mm of push x roll +/-70 vs the panel detail >= 3 mm: 16.1; the rev M
  yokes: fit_check 33, Yoke rev M) and 29b [open] -- at
  the full [E] push (-90 mm) the grips reach within ~8 mm of the bare lower-panel face wings level and cross it from ~45
  deg of roll: the switch blocks under the inboard grips are hit; owner decision: a shorter [E] forward travel (~-65 mm)
  or accept (decided 2026-10-11: push 65, Yoke rev N); consistency rows select the yoke / pedal parts and the lip's leather_black (materials moved).  Triangles
  (RES 2):
  flight_deck 35.6k -> 87.3k, yokes 13.75k -> 22.6k, pedals 1.9k -> 3.0k (per-part caps in build.INTERIOR_BUDGET:
  flight_deck 150k, yoke 24k, pedal 3k; the flight deck is in build.LOW_FINE, so phones get the same detail).
  Deferred: legends on a shared legend atlas (never built: legends stay geometric strokes), the pedestal front height
  (no PNL-04 figure in hand), PANEL.mfd_z (research C7: a camera fit first).
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
  [FD-L6] p10 15, p50 73, < 20: 14 %, bands 29 / 48 / 13 %), `--only tour` 26 / 26 (the first try timed out on a
  screenshot with four SwiftShader browsers on the shared machine, load ~20; rerun clean); the full viewer_test run NOT
  run this round (~3 h at that load); web/package.py verify OK (meshopt 17.2 + 14.7 MB); the Artifact bundle 115.2 MB in
  2 publishes (62.5 + 52.7 MB), artifact_test: the no-WebAssembly scenario's 46 checks passed before the harness timed
  out loading the WebAssembly page (30 s, same load), `--only wasm,runtime` rerun 48 / 48.  Photo |
  before (d3673c2, the judges' r4 renders) | after sheets: out/tmp/fd_fix_r5/cmp_*.jpg (gitignored: they embed the
  photos).
- Yoke design drawings (owner 2026-10-05: "the yoke isn't quite right ... better design drawings?"; the 3-D yoke is
  built from them since rev M -- see "Yoke rev M / N (L6Y / L6Y2)" below; the rev H yoke and `interior.YOKE_REVH` are
  gone): `interior.YOKE_DESIGN`
  (rev M, every value source-tagged) -> the solids of `model/yoke_geom.py` (white cover with flush inserts; black body +
  grips one moulding joined by a ROLLING-BALL round `rmin_ang` (true round at an angle, none where the faces run flush),
  then each pad's pocket / groove / bead cut (`pad_finish`); each grip = its aft side (prism trimmed in the
  `head_zone` -- an exact 2-D trim distance `trim_field`, bend R 4 -- joined R 3 to the head's aft shape) cut by the
  shared walls and forward face, R r_hf where the head wraps onto the forward face; switches as solids incl. the [E]
  forward-face PTT / checklist placeholders `fwd_switch`; 2-D signed distances to C2-spline outlines sampled every
  0.05 mm (`curve_law`), exact within 0.3 mm and a C2 B-spline of exact node distances beyond (`Field2D`); the
  rolling-ball's angle eased C2 through 90 deg (`_ang_map`); the body = side and top pieces (each rounded onto the
  forward face) joined by a rolling ball, the aft face cut last (`_body_pieces`, `isect_ang`); the grips' forward
  radius cap C2 (`fwd_radius`); the inboard fall-off's directrix one tangent curve
  (`shield_directrix`); `design_key` hashes the source a process imported, so a file edited mid-run cannot re-key
  its cache) -> sheets L6Y (front / side / above / B-B) and L6Y2
  (sections with the leather pad hatched apart, grip profiles, details incl. W, corners & radii, photo check), every
  view an exact silhouette / cut; `model/yoke_checks.py` acceptance (curve law + capped fillets, cusps, one piece per
  side, normals on 9 patches, an ADAPTIVE CREASE scan of 14 views -- pixel pairs turning > 4 deg refined 2 x 16x --,
  field ridges at the rounds' own surface points + the smallest gradient norm they read, pads exposed as drawn); `drawing/yoke_overlay.py` ray-casts the solids through
  8 photo cameras (private overlays, refs/cache; the grips fitted on 6 views incl. P1046409, the AOPA press photo
  check-only: its co-pilot camera is extrapolated from the pilot-yoke solution); `drawing/yoke_station.py` the knee
  rows with the neutral moved forward.  Stage-3 route stated on L6Y (trimmed patches + swept rounds, not an implicit
  mesher).  OWNER DECISIONS 2026-10-05: L6Y rev D / L6Y2 rev C approved as the 3-D basis (rev E / D carry the judges'
  round-4 cleanup); the 95th's knee result (23.8 mm wings level vs the 25 mm criterion, kept; contact from 12.5 deg)
  ACCEPTED AS MEASURED (L6B rev M); the centre-post compass stays.  Open (owner): the fore-aft station (every posed photo
  14-65 forward of the drawn neutral); the grip toe (weak, views from inboard only; silhouettes 16.7 vs inboard pads
  ~26); the trim head's depth (weak); crown soft break vs crease; J band vs full collar; the shell skew (one pattern in
  8 views, kept symmetric); the forward-face switches ([E] placeholders, never seen).

- Yoke rev M (L6Y / L6Y2; built on wip/fd-yoke, merged 2026-10-12 -- its fit_check rows 30 / 30a-d there are 33 / 33a-d
  since the merge, fit_fd_b owns 30-32): sheets L6Y rev E / L6Y2 rev D, owner-approved 2026-10-05 as the 3-D basis; owner decisions
  of that day: the 95th-percentile knee is ACCEPTED AS MEASURED (23.8 mm wings level against the 25 mm criterion,
  contact from 12.5 deg of roll; the criterion text stays, L6B and fit_check 19 show the shortfall), the centre-post
  compass stays.  The 3-D yokes are built from exactly the solids / tables the sheets draw (`model/yoke_geom.py`,
  interior.YOKE_DESIGN) in yoke-local mm (u outboard in the co-pilot sense, h up, a aft) and placed by `yoke3d.place`
  (x = hub x + hub_whd[2] + a, y = hub y + side u, z = hub z + h; the pilot's the mirror, winding flipped); `yoke_L` /
  `yoke_R` stay own parts, children of flight_deck with the 'yoke' pivot (kinematics unchanged); the rev H builder
  (shield, paddle grips, bellows) and interior.YOKE_REVH are gone.  MESHING (smooth highlights first; one mesh at every
  RES, so the light tier's LOW_FINE yoke is the same; `yoke3d.yoke_pieces` disk-caches it in out/tmp/yoke_mesh_cache
  under the design key + the mesher sources): the black MOULDING (body + grips + rolling-ball joins =
  `yoke_mesh.moulding_smooth`, yoke_geom.moulding without the pads' pockets and the trim face's grooves) by octree dual
  contouring (DC_EPS 0.02, 547k triangles, exact gradients), the pads and the trim face cut out along their tabled edges
  (`yoke_patch.cut`: boundary vertices exactly on {field 0, cut 0}), then the HIGHLIGHT DECIMATION
  (`yoke_mesh.decimate_interp`, 2026-10-10): every dense vertex is a sample its coarse face must reproduce -- the
  corner normals interpolated there within `FRAME_TOL` 3.5 deg of its exact normal (x up to 6 on rounds tighter than
  4 mm, `curvature_tol_k`: a few pixels across; x4 on the forward faces nobody's camera sees; 20 deg, cone / turn 30 /
  40 under the cover), the face within 0.15 mm (0.40 / 0.50) -- besides decimate2's tests (flip, cone 12, turn 20 deg
  over 0.02 mm of PN bow = cad.res interior, angle, link, the cut loops sliding within 0.02 mm); the first route
  (QEM / cone bounds, 8-14 mm faces) had 43 % of the visible frame's area > 2 deg off (29 % > 4: the blotchy zebra),
  refining it afterwards spent 46k faces, a 6 deg cone 103k.  Then exact projection, PN-midpoint splits where the
  turn / bow criterion fails (not under the cover), `sliver_cleanup`.  The PAD POCKETS (`pad_pocket`: wall, groove
  floor 1.0 x 0.5, inner wall, the R 0.4 bead in 5 rows, the crowned leather as a CDT refined where its interpolated
  normals miss by > 4 deg) and the TRIM FACE (`trim_terrain`: V-grooves cut from the face plane) stitched into the
  loops on shared positions; the COVER explicit (`yoke_cover`: strip columns along the shell outline -- aft round /
  land / front rows, crease columns at the foot -- and a terrain whose groove crease chains are forced into a
  constrained Delaunay, heights exact, normals per groove piece split only along the creases, fill 2.4 / 4.0 mm plus
  centroid points wherever the interpolated normal misses its piece's by > 1 deg: 0.1 % of the area left);
  SWITCHES parametric (`yoke3d`: revolves with exact arcs -- rows <= 15 deg on rounds >= 0.6 mm, so cad.res leaves
  them --, rounded extrusions with mitred sharp corners); legend TICKS 0.35 mm slabs 0.12 proud (no letters).
  `test/yoke_mesh_check.py` (~4 min): per yoke 38.8k triangles as meshed (frame 20.0k incl. the AFCS boss 1.8k,
  pockets 6.2k, trim 0.8k, cover 6.9k, switches 4.2k, ticks 0.6k), 39.9k in the GLB part after cad.res's refinement
  (+0.9k: the cover strip's and the rounded extrusions' quad diagonals) and the column (0.2k) -- `build.YOKE_BUDGET` 40k =
  INTERIOR_BUDGET yoke_L / yoke_R, the interior total raised by 2 x (40k - 22.6k) (it was over before: flight-deck r1);
  watertight (welded by position, 0 open edges); corner normals vs the solids' gradients p95 1.90 (cover) / 1.67
  (moulding) deg; the frame's visible faces: interpolated vs exact normal p50 0.86, p95 2.97 deg, 16 % of the area
  > 2 deg, 1.2 % > 4 (zebra / studio before-after: out/tmp/yoke3d/cmp_*); 17 sliver triangles (< 5 deg) left: cover
  7 (sub-millimetre, strip foot / insert junction), trim chords' ends 4, pad_in leather 5 at the bead junction, frame 1
  (forward face).  MATERIALS (L6Y items; assemble.MATERIALS = lookdev SPEC = web/viewer/materials.json): yoke_white
  gloss pearl (clear coat), yoke_silver / yoke_silver_dark (new, metallic inserts), grip_black satin, leather_black
  (pads: ~1.1 mm pebble grain -- lookdev render_pebble; the viewer's materials.js maps it onto the band-limited
  'fleece' noise patch at the grain size), gloss_black TCS bezel, button_red AFCS cap (new, not emissive), legend_white
  ticks (new), metal_dark column, pedestal_gunmetal J band / recess.  PANEL: only the recess changed -- the lower
  panel's face is trimmed by the U (`fd_detail_a.recess_sdf`, YOKE_DESIGN column_recess: half-width 57, bottom h -72,
  R 17, 8 deep) and `column_surround` adds its walls, a rim flange over the plates' notch, the floor with the column's
  opening (column r + 1 mm, concentric with the column in the model's (y, z): the face points' offset along the tilted
  face normal had moved it 0.9 mm off the axis) and a dark sleeve closed 10 mm beyond the column's forward end at full
  push (`sleeve_depth` 0.22 m; it was 30 mm, the column ran through its cap), the J band (column_band 23 x 8, R 4
  rolled edges, flat top, leg inboard, joint line, hook about h -24) and its pan-head screw; no bellows (none in any
  PRO photo).  CHECKS: fit_check 30 (yokes over roll +/-70 x the pull travel + 60 mm push vs panel / recess / J band /
  glareshield / pedestal, exact point-triangle distances both ways >= 3 mm: 18.4 mm), 30a (the column in its opening
  and sleeve: radial 0.95 mm, its end 11 mm short of the sleeve's cap at full push), 30b [open] (the full [E] push, as
  fit_fd_a 29b: 0.0 mm), 30c [open] (the column vs the J band and the panel face above the recess: -10.7 mm -- the
  band and the recess were measured / drawn about the photos' column axis WL ~1.821, the column and roll pivot keep
  the hub WL 1.845 (the sheets' open point): the band's inboard leg runs tangent to the column, the recess top h +12
  [E] lies inside it; hidden behind the yoke from the crew / cabin stops); 19 on the yoke parts (wings level 24 mm,
  L6B 24; full roll -17, L6B -19: the accepted shortfall); consistency_2d3d L6Y (front / side silhouettes, cover,
  inserts, pads, switch axes, 1.5 mm: <= 0.4 mm, switch centres 1.2; all 157 rows pass).  Photo comparisons through the overlay cameras (P1046408 pilot /
  co-pilot, P1046409, P1046410, Mexico pilot / co-pilot, AOPA / press pilot / co-pilot: refs/cache/overlays/yoke/3d,
  private) and out/tmp/yoke3d (renders alone, viewer view_*_revM / _revH; the first mesh's _revM_qem).  Open: the AFCS
  boss (its R 0.8 edges and 1.5 mm blend hold 1.8k faces: an explicit revolve would free them), the slivers above,
  30c (closed in rev N, below),
  the inboard grip's forward-face field kink (a ~2 mm scar in the solid, hidden); the sheets' own open points (the
  fore-aft station, grip toe, trim head depth, crown soft break vs crease, J band vs full collar, shell skew, the [E]
  forward-face switches).
- Yoke rev N (3-D judges r1, 2026-10-11; L6Y rev F / L6Y2 rev E, L6 / L6B rev N): OWNER DECISIONS 2026-10-11 (the two
  [open] rows of rev M): (1) fit_check 30c -- the J band and the U recess are RE-CENTRED ON THE COLUMN AXIS (the hub, WL
  1.845: the column / roll pivot and the knee results kept); the photos read the band's joint line -- the column axis
  on the aircraft -- at WL ~1.821, 24 mm under the hub, so the band and the recess are drawn 24 mm up with the axis
  (YOKE_DESIGN column 0.330 / 1.869 / 1.845 / 1.825: joint line on the axis, screw 1.825, the leg's round top end 1.869
  -- +24 would cut the PDU row, so 3 mm under the recess top; column_band hook about h 0, concentric with the column, its
  inner edge 1.0 mm off it all round; column_recess bottom h -72 -> -48, top h 27 [E]); recorded on L6Y2 detail J
  and in the tables; (2) fit_check 30b / fit_fd_a 29b -- the PUSH travel shortened to 65 mm (YOKE travel (-0.065,
  0.090): the [E] 90 put the grips into the lower panel from ~45 deg of roll), the pull kept; the viewer pivot's
  travel_push follows (rev N's push x roll envelope `push_roll` is gone); 30 sweeps the whole travel, 30b the full push
  every 5 deg of roll, both hard (>= 3 mm), as is fit_fd_a 29b; L6 / L6B take -65 / +90 in the knee sweeps and the
  phantoms.  As built: fit_check 30 / 30b 13.5 mm (yoke_R at full push, roll 70), fit_fd_a 29 / 29b 18.4 / 13.6 mm,
  30a radial 0.95 / axial 11.0 mm, 30c +0.9 mm (the band's inner edge), 30d dark; the knees unchanged (24 / -17 mm,
  L6B 24 / -19); FIT OK with no [open] row.  COLUMN / RECESS / BAND (CR1-01 blocker, CR1-02, FID1-02, FID1-08): rev M's fit_check 30c [open] (-10.7
  mm: the column, r 22 about the hub, ran its top through the panel face above the U and the J band's leg lay tangent
  to it -- visible from the crew stops): column_recess top h 12 -> 27 (the U runs up through the titanium band under
  the PDU row, its rim flange's top edge on the band's top edge WL 1.8755, the bridge over it gone:
  `fd_detail_a.lower_panel`), column_band 23 -> 22 (the low end of the measured 22-25: 1.0 mm off the column, as the
  floor's opening), then re-centred (above); 30c a hard row (>= 0.5 mm); `_band_sweep` winds the band by its own section
  normals (FD._oriented had turned the mirrored pilot band inside-out: fit_check 23's pcl_pewter row); the column SATIN
  BLACK non-metallic (`yoke_column`, rough 0.7, specular 0.5: the metal_dark pipe read light grey where Mexico L shows
  a dark column), the recess walls / flange / floor charcoal (`fd_detail_a.RECESS_MAT` panel_dark), the band satin
  pewter (BAND_MAT pcl_pewter); 30d reports where the column shows (~100 mm of it at the drawn neutral: the fore-aft
  station, OPEN) and holds its finish dark.  DETAILS: the legends as WORDS of plain letter BLOCKS (FID1-05:
  the radial tick rows read as a dial; YOKE_DESIGN legends (r0, r1 = the cap-height band, ((from, to, letters), ...))
  + legend_style; `yoke_geom.legend_blocks / legend_quads` feed the sheets and `yoke3d.legend_pieces`; `legend_grey`, the
  lettering's mean tone; TCS / AFCS DISC / TRIM DN / TRIM UP / MAP LIGHTS by letter count -- no letters; the pilot yoke is the moulding's
  mirror image but its printed words keep their reading order -- `yoke3d.reading_blocks` reflects each block about its
  row's centre before `place()` mirrors it (`side_pieces`, `pilot_legends`): TRIM DN / TRIM UP read left to right as in
  Mexico L / the AOPA pilot view, LIGHTS on the collar's inboard arc as in Mexico L; the mirrored rows had read DN TRIM /
  UP TRIM with LIGHTS over the collar); the trim
  rocker in a recessed SLOT (trim_slot 2.5 deep, 7 deg draft, sharp edges: the solid `_trim_face_grooves`, the mesh
  `yoke_patch.Terrain` slot pieces SLOT_FLOOR / WALL / END), its lobes satin dark grey (`yoke_rocker`), the lunes gloss
  black; the badge's raised blank PLATE (FID1-06: badge_field + proud 0.3 / R 1 / edge R 0.2; the solid
  `yoke_geom.badge_plate`, in SWITCHES; the mesh a rounded extrusion); the push button's hex collar SATIN NICKEL (FID1-04,
  `yoke_nickel`).  `yoke_geom.NON_SOLID_KEYS` (legends, legend_style, column*, ptt) stay out of design_key -- printed /
  panel values do not re-key the solids' caches (`yoke3d._src_key` adds `table_key`).  MESH: visibility by Z-BUFFER
  (CR1-03: rev M's 'under the cover' proxy held the body top behind the cover's upper edge, which the crew eye sees at
  ~45 deg, to 20 deg) -- `yoke_patch.visibility`: the dense moulding + cover rasterised from 67 aft-hemisphere / 25
  forward cameras (VIS_*), each dense vertex seen from aft (256k) / only from forward (16k) / never (2.4k) ->
  FRAME_TOL / FWD_TOL_K / HIDDEN_TOL (stage 'vis', `vis_tol_k`); FRAME_TOL 3.5 -> 2.5 deg (FID1-07): frame 18.8k ->
  22.4k faces, the aft-visible faces' interpolated-vs-exact normal p50 0.67, p95 2.25 deg, > 2 deg 8.5 %, > 4 deg 0.6 %
  of the area (rev M: 0.86 / 2.97 / 16 % / 1.2 % on its proxy class); the cover a FIXED POINT of cad.res (CR1-04:
  `yoke3d.res_fixed_point` splits where cad.res would, +200 vertices projected onto the cover solid with exact normals;
  yoke_mesh_check's row restored: cover +0, moulding +74 on 29.4k); FOLDS (CR1-05: `fold_faces`, `repair_folds`,
  `fix_fold_normals` -- 24 -> 0: flipped vertex normals at the AFCS boss seam, the badge grooves' sub-0.1 mm2 end faces;
  a yoke_mesh_check row).  41.8k triangles meshed, 42.5k in the GLB part: build.YOKE_BUDGET 40k -> 43k.  VIEWER
  (FID1-01 / CR1-06): materials.js CABIN_TRIM entries 3 / 4 -- a reflection floor and the key light's share in the
  specular -- for yoke_white / yoke_silver / yoke_silver_dark / yoke_nickel (?cabTrim=name:a,b,c,d overrides), VIEWER
  yoke_silver_dark colour 0.44; at P1046408 / 09's cameras the cover 213-214 (rev M 184-197), the upper insert 0.90-0.92 and the lower 0.76 (P1046408) / 0.95 (P1046409) of it (rev M 0.50-0.76 / 0.34-0.68; photos ~0.94 / 0.84-0.87; final GLB, out/tmp/yoke3d/r1fix/final/vlook2.py); viewer_test [Y1] at the pilot stop.
  KINEMATICS (CR1-09): the push 65 mm (owner, above; a push x roll envelope -- 0.95 of the [E] 90 wings level, 0.83 at
  70 deg -- had been the interim fix).  BUDGET (CR1-07): `build.BUDGET_OPEN` printed while the interior is over (flight
  deck ~91k against the seed's cap that never landed; seat_pax3-6 34,834 / 34,800).  SHEETS: L6Y2 regenerated on the
  rev N solids -- its acceptance (model/yoke_checks.py) is disk-cached per check (`acc_part`, `ACC_VERSION`; the
  crease scan per view: one run_all had taken > 2 h on a loaded machine); the cusp scan tables the trim slot's sharp
  edges (`_trim_slot_tabled`: 25 slot corners had read as untabled cusps) and `connected` counts islands, not holes
  (h 76 cuts the slot's pocket under its lip as a closed hole); detail F's leaders re-wrapped off the notes column.
  DEFERRED (owner): FID1-03 the
  grips' fore-aft depth -- grip_depth 27 [M weak] / toe 18 are approved values; the AOPA co-pilot view (check only: its
  camera extrapolated from the pilot yoke) reads both grips narrower, but its 4-DOF cover pose misses the inboard
  button by 13.9 mm; a 6-DOF relative pose on all 9 landmarks (<= 4.2 mm) leaves the outboard grip -4.6 mean (-8.4
  low .. -0.3 high) and the inboard slot side -19.4 (out/tmp/yoke3d/r1fix/press6dof.py): a deeper grip is plausible
  but needs a fitted camera (and shortens 30b's push clearance) -- the next drawing revision, with the owner.
- Yoke rev O (3-D judges r2, 2026-10-11; L6Y rev G / L6Y2 rev F): PUSH BUTTON (FID2-01, the major; L6Y item 10, a
  table change for the owner's review): rev J-N's 17.3 hex collar was the photos' round GLOSS-BLACK LEGEND DISC (17.5-18.3
  in Mexico L / P1046409, rev I's 'collar' 16.4-17.7) -- YOKE_DESIGN button = centre, disc 17.5 x 0.75 proud (R 0.5 rim,
  gloss_black), cap 10.2 standing 5.75 over a small SATIN-NICKEL HEX 12 A/C x 1.5 (the top of the judges' 10-12: its
  corners show 0.9 past the cap as Mexico L's lit facets), the cap top 8.0 above the facet as before (`yoke_geom
  .button_dims / button_disc / hex_collar / button_cap`, `yoke3d.button_pieces`); MAP LIGHTS on the disc's rim (legends
  row 4: r 6.3-8.0, arcs widened, printed on the disc's top).  TRIM ROCKER (FID2-02): lobe ends 9.5 proud (6.5; the
  P1046409 / Mexico R projections put the outboard end past the ring, the face-on AOPA / Mexico L keep the 27 length
  inside it), each lobe CROWNED 0.6 across (trim_lunes[4], `yoke_geom.rocker_crown`), yoke_rocker near-black satin 0.02
  / rough 0.30; the side walls in rows <= 7 mm (`rounded_extrusion side_max`: 16 slivers each).  LEGENDS (FID2-06):
  blocks 0.35 of the pitch (0.70), legend_grey 0.17 (sRGB ~0.45).  BADGE (FID2-06): ONE outline groove (badge_lines[4]
  0 = no inner border: rev J-N's border 0.8 inside drew a double outline; the rectified views' second line is the
  groove's lit flank), the speed lines run into it, the plate 0.2 proud (0.3), its R 0.2 edge one row and no interior
  cap points (CR2-07: 96 slivers -> 0).  AFCS cap button_red 0.50 / 0.004 / 0.012, coat 0.15 (FID2-03; the viewer
  0.34 / 0 / 0.006: AgX compresses a bright red toward white).  MESH: CR2-01 the curvature relaxation capped at 2 x on
  every aft-visible vertex and none on the heads and their necks (`yoke_patch.CURV_KMAX_VIS / _HEADS`, HEADS_BOX |u| > 85,
  h > 50; decimated on the cached rev N stages: k 2 / 1 23.66k -> 24.31k faces, the heads' per-face p95 3.9 -> 2.8 deg;
  1 / 1 everywhere 25.4k); CR2-02 the trim face's terrain refined to the cover's 1 deg (`Terrain.interp_error`,
  TRIM_INTERP: the lunes by area p95 0.29 deg, > 4 deg 0.3 % -- the judges' raster 5.3 %); CR2-03 the leather refined at
  3.2 deg (4.0; the judges' 2.0 cost 1.4k faces a yoke, over the budget); CR2-07 budget: YOKE_BUDGET stays 43k (not
  raised; the interior total's open item stays with the owner) -- the forward-face [E] switches sampled for shape only
  (never seen), the cover strip's columns 2.4 -> 2.6 mm, the hex one edge row and no interior cap points; the AFCS-boss-as-a-revolve
  suggestion is not taken: the boss stands 1.5 proud with the R 1.5 blend into the body, so its side is all blend and its
  R 0.8 rim meets it -- only the flat aft face is a pure revolve, and that already holds few faces (its 1.8k faces are
  the rims and the blend, held to the highlight criterion).  yoke_mesh_check rows added: the heads per face (p95 <= 2 x
  FRAME_TOL), every visible round by area / per face (info), the lunes by area.  VIEWER (FID2-03..05, CR2-06;
  materials.js): CABIN_TRIM entries may be part-scoped ('yoke:grip_black') and carry a 5th 'up' (inside, reflections
  below the horizon mirrored above it: the crew seats saw the inserts reflect the studio floor) and a 6th 'win' (a
  side-window radiance where reflections turn sideways: the cover's rims, crown and arm tips get bright edge highlights;
  its planar aft face reflects one direction, the drawn face being one plane); the cover's fill share 0.4 -> 0.25 for
  headroom; the body 1.45 x fill + a 0.3 reflection floor.  viewer_test [Y1b]: at the pilot stop the cover's spread
  (p99.5 - median), the inserts / cover, body / cover, pads / body and the cap's saturation.  Kinematics comparisons use
  the rev N travel (push 0.065, pull 0.09: FID2-08; judge_fidelity_r2/vjobs.json).  DEFERRED (owner): FID2-07 = FID1-03
  (the AOPA co-pilot camera first).  AS BUILT: 41,848 triangles meshed, 42,708 in the GLB part a yoke (rev N 42,540;
  YOKE_BUDGET 43k), GLB 2,495,682 / 42.07 MB, light tier 2,027,929 / 33.70 MB, interior 645,160 (the open budget item);
  yoke_mesh_check: frame p95 2.22 deg by area, the heads per face p95 2.79 (> 4 deg 2.1 %), every visible round by area
  p95 3.18, the lunes by area p95 0.29 (> 4 deg 0.3 %), 10 slivers (the hex's straight sides 1 row: 78 -> 0), no
  same-way edge inside a material (new criterion: one isolated micro-triangle, 0.00003 mm^2, had been doubled at the
  inboard web -- `yoke3d._debris_keep` drops components of < 4 faces and < 0.001 mm^2).  Viewer, final GLB (SwiftShader,
  High, 4 passes; scratchpad vshots): pilot stop -- cover 216 (p99.5 244: spread 28), inserts 0.91 / 0.85 of it, body
  0.27, pads 0.35 (1.30 x the body), AFCS cap 185 / 43 / 41 (saturation 0.78); the pilot's eye at the yoke -- cover 210,
  inserts 0.90 / 0.82, body 0.24, cap saturation 0.82; viewer_test [Y1b] on its own page: spread 25 (>= 20; rev N 8),
  inserts 0.91 / 0.84, body 0.27, pads / body 1.27, cap saturation 0.78.  consistency_2d3d 'switch centres' takes the forward-face
  switches' own connected pieces (grip_black is one primitive with the grip body: 128 body vertices in front of the
  inboard switch's plane had moved its centroid 1.53 mm once the switch was sampled coarser; the switch itself sits
  0.00 mm on its axis; tolerance unchanged).
- Yoke rev P (3-D judges r3, 2026-10-11; L6Y rev H / L6Y2 rev G): TRIM HEAD TONES (FID3-01, major; L6Y item 9, a
  table change): rev N / O's gloss-black lunes over a satin slot read inverted against every photo (face darker than the
  body, the slot lighter than the face) -- the legend ring / lunes a flat SATIN CHARCOAL (`yoke_trim_face` 0.040, rough
  0.45, no coat; `yoke_patch.TRIM_FACE_MAT`), the slot walls / floor a near-black MATTE (`yoke_slot` 0.010, rough 0.8,
  `TRIM_SLOT_MAT`); viewer CABIN_TRIM yoke_trim_face [0, 1.0, 0.25], yoke_slot [0, 0.5] (an occluded pocket).  Measured
  (SwiftShader High, out/tmp/yoke3d/r3fix/viewer): lunes / body 1.28-1.60 (pilot eye 1.52, det_trim_L 1.28, Mexico L
  1.60, P1046409 1.37; photos 1.0-3.2), slot / lunes 0.17-0.21 (photos 0.14-0.90), rocker / lunes 0.51-0.64 (P1046409
  0.20; photos 0.36-0.74); viewer_test [Y1c] at the pilot stop.  COLUMN FROM THE SEATS (FID3-02, major; the photos cannot
  settle it -- no PRO photo looks from a seated eye): (1) the viewer PARKS the free yokes at the photos' unlocked rest,
  interior.YOKE rest -35 mm [M: Mexico -34 / -38, AOPA -14 / -26; P1046408-10's -37 .. -65 the gust lock] --
  `flightdeck.control_pivots` pivot 'rest', `kinematics.js`: position = travel x |command| + rest x (1 - |command|), so
  the full push / pull still reach travel; the drawn neutral, the knees (L6B) and fit_check 30 (whole travel) unchanged;
  the elevators stay drawn at neutral; (2) the column matte near-black (`yoke_column` 0.014, rough 0.8; CABIN_TRIM [0,
  0.5]: no fill in its recess) -- at the pilot's design eye its pixels 19,491 -> 11,454 (0.48 -> 0.30 of the cover's) at
  luminance 54 -> 23; L6Y2 detail J records it (the column's free length 107 -> 72 mm).  NICKEL HEX (FID3-03): CABIN_TRIM
  yoke_nickel [0, 1, 0, 0.35, 0, 0, 0.25] -- no reflection floor / window term, the key's glint kept, and a new 7th entry
  'refl' (materials.js: the studio reflections' own factor inside); a warmer tint (0.62 / 0.55 / 0.47): hex / cover
  median 0.28-0.35 at det_button_L / Mexico L / P1046410, 0.14 at P1046409 (photos 0.10-0.34; was 0.80-1.02); from the
  pilot's eye only the lit upper facets show (0.66, as Mexico L's tan glints).  MESH: CR3-01 junction normals --
  `yoke3d.split_junction_normals` (end of _build_pieces): a cover / moulding corner > 25 deg off the solid's gradient
  0.03 mm inside its face, the gradient > 10 deg closer to the face's plane, gets its own vertex copy with that side's
  normal (the step V's ends at |u| 12.9: 78-89 deg knobs, the lower insert's V apex), then any corner > KNOB_DEV 60 deg
  off its own face -- or > 30 deg on a sub-0.01 mm^2 face -- takes its face's other corners' mean (the badge groove ends,
  the inboard neck's DC debris); positions unchanged.  Row 4's p99 (40 deg) stays: of the cover's 521 corners > 10 deg
  off the gradient 0.03 mm inside their face, 439 lie within 10 deg of their OWN face (the face spans a groove / step
  crease and the sample point falls on the crease's other side -- the metric, not the shading), 78 are > 10 deg off their
  own face, 10 > 30 (max 50.5 deg, all on sub-0.25 mm^2 faces at the insert / badge groove ends;
  out/tmp/yoke3d/r3fix/p99/cov_p99.py) -- so a p99.9 <= 10 deg row (judges' example) would measure the crease sampling;
  the 'knobs' row bounds what shades as a knob.  CR3-02 `yoke_patch.collapse_needles` also collapses MICRO faces
  (< 0.01 mm^2 with a corner > 30 deg off: the trim ring's groove-bottom caps by the slot, 9 -> 0).  yoke_mesh_check
  row 'knobs' (0 / 0).  CR3-03 the leather crown as ROWS (`yoke_patch._crown_rows`, CROWN_ROWS 7 / 3 / 12 / 5 / 0.3:
  marching-squares contours of the smoothed inward distance the crown is built on, a row per 7 deg of slope turn,
  points along each row per 3 deg of normal turn, constraint edges) refined at the judges' 2.0 deg (LEATHER_TOL): 5,477
  leather faces a yoke (rev O 5,297), the crown's faces inside the bead interpolated vs exact normal p95 1.8-1.9 deg by
  area, > 4 deg 0.1 % (rev O's 3.2 deg hex lattice: > 4 deg on 7 %; zebra out/tmp/yoke3d/r3fix/zebraX_*); the judges'
  9-10.5 % 'facet' area is the bead's R 0.4 half round in 36 deg rows (Phong-exact on a circle; fewer rows and cad.res
  splits them back at build) -- not the crown.  CR3-04 the J band's hook ends ROUND (`fd_detail_a._band_sweep` cap1,
  BAND_HOOK_END 330 deg = the round tip, the drawn extent) and both round caps closed on top (rev M-O left a half-disc
  'D' hole in the leg's round top end).  CR3-05 legends (legend_style (0.22, 0.12, 0.35), table change): blocks 0.22 of
  the pitch with +/-35 % letter weights on a fixed sequence (`model/yoke_legends.py` -- NOT yoke_geom.py, whose source
  is the solids' design key: an edit there re-runs every cached view / section / mesh stage; its old legend_blocks /
  legend_quads stay unused), legend_grey 0.17 -> 0.13.  BUDGET: 42,010 triangles meshed, 42,876 in the GLB part a yoke
  (YOKE_BUDGET 43k), GLB 2,496,464 / 42.09 MB, light tier 2,028,571 / 33.72 MB, interior 645,942 (the open budget item).
  FID3-05 (single-pixel dark specks on the cover in det_centre_L, ~33 px apart): not the mesh (ray-cast: face interiors
  of 4 mm equilateral cover faces, 0.6-2.3 mm from their corners and 0-1 mm from their edges, normals exact to 0.0 deg
  there, no T-junction, no _AO on the yoke), not the still accumulation (?ssframes=1 the same), not 'up' / 'win'
  (?cabTrim without them the same), not the studio reflections (cabTrim yoke_white 'refl' 0: the same 7 pixels); a 5 mm
  camera shift moves them off the surface points -- view-dependent shading in the diffuse / clear-coat / key path,
  passed to the picture lens (out/tmp/yoke3d/r3fix/viewer det_centre_L_p1 / q1).  CR3-02's residual: the small V at
  the trim ring's lower edge in v_outb_head is on the moulding's R 1.5 face-edge round at r 14.7 from the ring centre
  (the ring crosses the head's front silhouette by 0.61 mm there, L6Y's trim-face row) -- the exact solid's zebra draws
  the same V (judge_craft_r3/d_trimlow_zebra0); the micro faces that darkened it are gone (lower contrast), a fairing of
  the junction is a solids change (yoke_geom.py, a drawing revision).  L6Y item 8's finish text now carries the rev O red
  (0.50 / 0.004 / 0.012, coat 0.15).  Deferred: FID3-01's secondary point (the rocker lobes' outer ends cut along the
  ring in AOPA pilot / Mexico L, not round: a photo re-trace and a solids change -- yoke_geom.rocker_lobe), FID3-04 (the
  cover flatter than P1046409: the studio env map lights a planar face uniformly; spatial falloff needs local light
  probes -- with CR3-06 (b)), FID3-06 = FID2-07 grip depth (owner, the AOPA co-pilot camera first).  Before / after
  sheets: out/tmp/yoke3d/r3fix/final/cmp_*.png (craft cameras at the drawn neutral, the J band raster, the pilot eye at
  the parked rest), refs/cache/overlays/yoke/r3fix/cmp_trim_photo_O_P / cmp_button_photo_O_P (photo crops).
  Verified on the final GLB (both tiers rebuilt byte-identical after a restart): yoke_mesh_check OK (knobs 0 / 0),
  fit_check OK (131 ok; 30 / 30a-c 13.5 / 0.95 / 0.9 mm), fit_fd_a OK, consistency_2d3d 157 / 157, drawing.master L6Y /
  L6Y2 clean; viewer_test --only tour 29 / 29 ([Y1b] spread 36 on the committed 20 -- CR3-06 (a); [Y1c] lunes / body
  1.50, slot / lunes 0.21, rocker / lunes 0.63) and its numeric section 62 / 62 (the pull row from the parked rest:
  hub +0.125 m) -- the full run was stopped at ~25 min of screenshots on a machine at load 10-12 (it would have passed
  the 2 h background limit; the sections the change touches were run instead).
- Yoke rev Q (3-D judges r4, 2026-10-12: craft 8.0, photo fidelity 7.5; L6Y rev I / L6Y2 rev H): GROOVES DARK (FID4-01,
  major): the cover's V-groove flanks -- the insert parting grooves, the step V's down-facing flank and both its round
  end cones, the lower insert's outline, the badge outline / speed lines -- are finished `yoke_groove` (dark satin 0.03,
  rough 0.6: their cavity shadow; the yoke carries no baked occlusion), the step's UP-facing flank keeps the cover white
  (`yoke_cover.groove_faces`, GROOVE_LIT; L6Y item 15, the `grooves` note): the photos' profile down the centre through
  the step reads ~190 / 3-10 / 155-231 / ~180 at P1046408 and ~130 / 0-16 / 145-197 / ~90 at the AOPA camera -- a dark
  line over a lit one (out/tmp/yoke3d/r4fix/profile.py), so the lit lower flank (the judges' 'ridge') is kept; the end
  cones dark also take CR4-07's nubs into the line.  CABIN_TRIM yoke_groove [0, 0.6].  SATIN-METAL INSERT (FID4-02,
  major): the inserts a COOL satin aluminium / smoke (yoke_silver 0.58 / 0.61 / 0.67, rough 0.34; yoke_silver_dark 0.29 /
  0.30 / 0.33, rough 0.36; viewer 0.42 / 0.44 / 0.48) and, inside, a CABIN PROBE in their reflections instead of the
  studio (`materials.js YOKE_PROBE`, installPatch 'probe'; their studio floor / 'up' / 'win' off): the studio's blurred
  overhead radiance x a cool tint (0.82 / 0.95 / 1.22) x [the dark cabin 0.22 + the headliner / windshield overhead 0.66
  (smoothstep over R.y 0.15-0.6) + the yoke's OWN side window 0.45 (reflections turned outboard -- sign of the world BL
  -- near level) + the crew's lap / seat 0.30 (below R.y 0.1)] x a near-field term 1 -+ 0.22 over WL 1.83-1.91 (the
  face's top sees the sky over the glareshield; a planar face mirroring one direction had read as one flat tone); the
  lower insert [0.20, 0.85, 0.35, 0.30, 0].  The photos disagree with each other at one reflection direction (the AOPA
  and Mexico press shots both mirror R.y ~0.26: insert / cover 0.74 vs 0.96-1.09), so the law meets the judges' targets
  (P1046408 0.93, AOPA <= 0.85, the stops <= 0.93, never above the cover).  Measured (SwiftShader High, ld page,
  out/tmp/yoke3d/r4fix/ld, metrics.py; photos in brackets): upper insert / cover P1046408 0.94 (0.93), P1046409 co-pilot
  0.94 (1.00), P1046410 0.94 (0.91), Mexico 0.87 / 0.83 (1.09 / 0.96), AOPA 0.81 (0.74), pilot stop 0.81, pilot's eye
  0.79; lower insert 0.77 (0.85), 0.82 (0.91), 0.78 (0.82), 0.74 / 0.69 (0.68 / 0.67), 0.65 (0.37); B - R insert +16..+20
  against the cover's +1..+2 (photos +35..+69 / +16..+30); the step line 0.06 of the insert (0.02), the badge region's
  p2 0.20 (~0.75 judges' bound).  viewer_test [Y1d] (new) at the P1046408 pilot-yoke camera + the pilot stop; [Y1b]'s
  insert floors 0.88 / 0.78 -> 0.75 / 0.65 (r2's came from photo-camera ratios r4 re-measured 0.74-1.00 / 0.37-0.93).
  MINORS: FID4-05 the column a SATIN DARK-GREY tube (yoke_column 0.04, metallic 0.5, rough 0.4, CABIN_TRIM [0, 0.8, 0.15]:
  ~56 at the pilot's design eye, 67 at the pilot stop -- [Y1] column <= 70; rev P's matte near-black read 23, a hole);
  FID4-06 (a) the AFCS boss in the body's satin black (`yoke3d.AFCS_BOSS_MAT` grip_black: rev M-P's lighter 'black' puck
  and rim; its R 0.8 / 1.5 rounds are solids values, kept); CR4-06 the legend letters SET (`yoke_legends`, legend_style
  [3] 0.30 radial variation -- some letters short on the baseline or hanging from the cap line -- and [4] 0.60 gap
  variation, a full mean gap kept free at each word's ends: clusters with clear word gaps, no letters); CR4-08 the
  inboard neck's forward-face DC debris (`yoke3d.repair_debris`: 2 collapses, 61 corner normals onto the solid's
  gradient; the 14-16 faces bridging the solid's own field kink -- the rev M scar, hidden -- shaded flat; yoke_mesh_check
  row 'debris' 0, the kink's corners / faces reported); CR4-05 the parked rest COUPLED to the elevators
  (`kinematics.js pitchPos`, interior.YOKE rest note: the cable run allows no forward yoke over a level elevator, and
  parked PC-12 tails droop -- LX-FLI, MSN 3008 0517 -- so parked the elevators hang +8.08 deg; the drawn neutral level;
  full pull / push -20 / +15 as before; viewer_test [CR4-05] and the pull / push rows measured from the drawn neutral).
  MESH: 42,004 triangles meshed, 42,868 in the GLB part a yoke (YOKE_BUDGET 43k; cover: white 4,336, silver 1,066, smoke
  158, groove 1,184, black 52); yoke_mesh_check OK (folds 0, knobs 0 / 0, debris 0, frame p95 2.23 deg, 12 slivers).
  NOT FIXED: FID4-03 the cover specks -- not shadow acne (no model mesh receives shadows in this branch: Model receiveShadow
  false; the sun with its receivers is the flight-deck branch's), not the GLB (ray casts: the cover's aft face, nothing
  within 3 mm, no T-junction), not the clear coat, specular, key light nor the specular-AA kernel (each off: the same 7
  pixels, 158-161 in a flat 209, every ~33 px down a line); they go only with the environment light: the diffuse
  image-light path in SwiftShader (out/tmp/yoke3d/r4fix/ld s1-s6) -- not counted in [Y1]; CR4-07's nubs (dark now; the
  cones' 1 mm past the side grooves is a solids change); FID4-06 (b) / (c) and CR4-01 (rocker lobe re-trace, the trim
  ring junction: solids / drawing); CR4-02 (cover tight-round faces: over the 43k budget); CR4-03 (J band rows); CR4-04
  (sub-pixel grooves: now dark lines; a screen-space groove AA not built); CR4-10 (the cover's planar face); FID4-04 (grip
  oblique form: owner, the AOPA co-pilot camera first).  MERGE NOTE (wip/stage2-drawings, the flight-deck look): the
  yoke's YOKE_PROBE and CABIN_TRIM entries were tuned on this branch's studio cabin light; after the merge the satin
  inserts may rather join the flight deck's REFL_DIR cabin probe -- re-measure [Y1d] there.  Verified on this build (both
  tiers rebuilt): yoke_mesh_check OK, fit_check OK (131 ok; the column row the rev Q finish rule, exposed 109 mm),
  consistency_2d3d 157 / 157, L6Y / L6Y2 regenerated (no texts crossed), viewer_test numeric 63 / 63, --only tour 30 / 30,
  the full run 221 / 221 (110 min).  Before / after: out/tmp/yoke3d/r4fix/cmp/cmp_*.png (renders only); the photo sheets
  refs/cache/overlays/yoke/r4fix/cmp_yoke_*.png (gitignored).
- Flight deck + yoke MERGE (2026-10-12; wip/fd-yoke at bddbd41 = yoke rev Q, merged into wip/stage2-drawings at
  d007ea8 = flight deck fix r5).  ONE FLIGHT DECK NOW: the panel area of GEOM A, the surround of GEOM B and the look of
  fix rounds r1-r5 (palette, sun, outside world, CABIN_LOOK law, baked occlusion / window light, posts, fleece,
  pedestal) with the yoke of the drawings-first track (sheets L6Y / L6Y2, model/yoke_*.py, `flightdeck._yokes`, the
  U recess / J band / sleeve of `fd_detail_a.column_surround`, the YOKE / YOKE_DESIGN tables) in place of GEOM A's
  paddle yoke, its well and bellows.  Conflict rule: the yoke track's yoke won over GEOM A's; everything else on this
  branch won over the yoke branch's older copies; where both changed a file for different reasons both were kept:
  `flightdeck._panel_face` the yoke's exact U trim (`fd_detail_a.recess_sdf`) on fix r1's graphite face;
  `fd_detail_a.lower_panel` fix r3's rolled lip / USB + `column_surround`; `build.INTERIOR_BUDGET` the flight deck's
  per-part caps + `YOKE_BUDGET` 43k a yoke (total + 2 x (43k - 24k)), the flight_deck cap 202k -> 211k (the column
  surround and the face's U trim after the bake's contact split: 199.6k -> 207.5k), `BUDGET_OPEN` only the aft cabin
  seats (34,834 / 34.8k, as before); fit_check runs fit_fd_a (28-29b, now all hard: the push 65 decided 29b) and
  fit_fd_b (30-32) before the yoke track's rows, renumbered 30 -> 33 / 33a-d; L6 / L6B revision tables both histories
  (H with the CB panel pairs / overhead, then the yoke revs I-N; L6's rows shortened so the table clears the title block
  -- it had overrun it: 4 overlapping text pairs, 'PILATUS PC-12 PRO' crossed; now 25 crossings as at rev H, L6B /
  L6Y / L6Y2 none); materials: the pads' leather is `yoke_leather` (the yoke track's charcoal 0.05 / rough 0.58 with
  render_pebble) -- the meshes keep `leather_black`, `flightdeck.YOKE_MAT_RENAME` renames it at placement so the yoke
  mesh cache key (`yoke3d._src_key`: the mesher sources) is unchanged; the flight deck's shared `leather_black` (hood
  lip, seat pockets, consoles) stays its darker 0.03 / 0.60; `grip_black` takes the yoke track's rough 0.42 (the panel
  knobs and pedal pads share it); `materials.js` keeps PART_TRIM / REFL_DIR / SPEC_KEEP and adds the yoke track's
  CABIN_TRIM entries 3-7 (reflection floor -- `max(floor, law)` over the facing / SPEC_KEEP / REFL_DIR law --, the
  directional light's least share in the specular, 'up', 'win', 'refl'), the 'yoke:' part-scoped entries beside
  PART_TRIM (one interior clone per material and scope), YOKE_PROBE ('probe', cache key 'Y'), render_pebble on the
  fleece patch's plain fBm form.  THE YOKE IN THE FLIGHT DECK'S LIGHT: the yoke parts carry the bake's `_AO` (the bake
  covers every Interior part; the yokes are not presplit), the sun (SUN_CASTERS / RECEIVERS `yoke_`) and the outside
  world as the image light, so rev Q's studio-tuned entries read the inserts 0.59 / 0.54 of the cover at the pilot stop
  and 0.72 at the P1046408 camera, the column 14 (the judges' 'hole'), the cap's saturation 0.76: re-tuned (look-dev
  page out/tmp/fd_yoke_merge/ld.py, `ymetrics.py` = viewer_test's [Y1]-[Y1d] measures) -- YOKE_PROBE upper [1.3, 1.2,
  0.82, 1.3, 0.22], lower [1.0, 1.53, 0.63, 1.0, 0] (the stop's reflections point aft, R.y ~0.17: only the dark-cabin
  term; P1046408's low camera mirrors the headliner), 'yoke:grip_black' [0, 1.25, 0.35], yoke_leather [0, 0.65],
  yoke_column [0, 3.0, 0.6], button_red [0, 0.75]: at the pilot stop the cover 213 (p99 242, spread 28), the inserts
  0.82 / 0.74 of it, the body 0.26, pads / body 1.18, the column 50, the cap's saturation 0.83, lunes / body 1.45, slot /
  lunes 0.15, rocker / lunes 0.63; at the P1046408 camera the insert 0.89 of the cover, B - R +34 against +12, the step
  0.14, the badge's p2 0.20; at panel_408b the cover 216 ([FD-L4] >= 190).  KEPT: the yoke track's elevator coupling
  (`kinematics.js pitchPos`: parked, the elevators hang +8.08 deg trailing edge down with the parked yokes -- photos 0517
  / LX-FLI; it changes the exterior default pose: the tailplane's horn balances stand up out of the fixed tips when parked).
  Build (both tiers rebuilt on the merged code): 2,721,764 triangles / 48.08 MB, light tier 2,296,131 / 40.33 MB;
  interior 873.0k of 896k (flight_deck 207.5k of 211k, yokes 42.9k of 43k each, crew seats 57.7k, interior_lining
  175.1k; seat_pax3-6 34,834 OVER the 34.8k cap as before).  Verified at the merge commit: fit_check FIT OK (138 ok, NO
  open row: fit_fd_a 29 / 29b 13.6 mm, 33 / 33b 13.5 mm, 33a radial 0.95 / axial 11.0 mm, 33c +0.9 mm, 33d the column
  109 mm exposed, dark satin; the knees 24 / -18 mm, L6B 24 / -19), consistency_2d3d 157 / 157 (the L6Y yoke rows
  read the pads as yoke_leather), test/yoke_mesh_check.py YOKE MESH OK (42,004 meshed, 42,868 in the GLB part),
  drawing.master (all sheets; L1-L5 / L4W / GA / sections changed only their PDF timestamps and were left alone),
  drawing.sheet + drawing.verify OK; the viewer's yoke rows [Y1]-[Y1d] and [FD-L4] measured on the look-dev page
  (above); the full viewer_test, the package and the Artifact bundle: the next entry.
- Flight deck + yoke merge, follow-up = YOKE REV R (2026-10-12; the yoke's fidelity re-judge r5 on rev Q scored 7.5 --
  FID5-01 major: the grooves an INK outline -- and ran while the merge was being verified; L6Y rev J / L6Y2 rev I, the
  YOKE_DESIGN grooves / column_band notes).  GROOVES DIRECTIONAL (FID5-01 / 07, `yoke_cover.groove_faces`): rev Q
  finished every flank of every V groove but the step's up-facing one `yoke_groove`, so the side parting grooves, the
  lower insert's outline and the badge read as a uniform near-black line on both flanks from every direction (judge:
  0.10-0.21 of the reference both sides at every camera); every photo shows ONE flank dark and the other lit, and from the
  centreline cameras the NEAR (inboard) groove dark, the FAR one light (P1046408 0.70 / 0.93, P1046410 0.37 / 0.79,
  P1046409 co-pilot 0.28 / 0.86, Mexico 0.43 / 0.87), from the aft-outboard AOPA camera the other way round (0.02 /
  0.86).  Rule: on the parting grooves between the cover and an insert (`GROOVE_INSERT_DARK`: side_l / side_r / lower)
  the flank on the INSERT's side is dark (the insert's cut edge in the gap's shadow; `yoke_geom.cover_part` just beyond
  the flank), the cover's side keeps the white (its rolled gloss edge) -- seen from aside a V shows mostly the flank
  facing the camera, the insert's on the near groove and the cover's on the far one, so the photos' near / far pattern
  follows from the geometry at every camera; the step and the badge outline / speed lines (insert on both sides) by the
  light from above (`GROOVE_LIGHT` (0, 1): the down-facing flank dark, as rev Q's step); the step's end cones keep the
  face (`GROOVE_END_LIT`: dark, they were the black nubs past the side grooves; the step's line now ends on the side
  groove's).  The cover's yoke_groove faces 1,184 -> 591 (the meshes and triangle counts unchanged: only the material
  split).
  Measured (look-dev page out/tmp/fd_yoke_merge/ldr / ldz, `edges.py` = the judge's edges.py; native / at the photo's
  px/mm): side grooves far / near at P1046408 0.85 / 0.21 (1.00 / 0.68), P1046410 0.81 / 0.22 (1.00 / 0.71), P1046409
  co-pilot 0.80 / 0.19 (0.98 / 0.58), P1046408 co-pilot 0.80 / 0.20 (1.00 / 0.73), Mexico 1.00 / 0.21 and 0.80 / 0.22
  (rev Q in the merged light: 0.19-0.21 both sides); the badge region's p2 0.57-0.62 of the insert (rev Q 0.20, photos
  0.64-0.82; the AOPA studio shot 0.19); the step line 0.13-0.14 (kept).  LOWER INSERT (FID5-02, viewer): from the stop /
  design eye its reflection points aft-DOWN (R.y ~ -0.5), from P1046408's low centreline camera aft-up-OUTBOARD -- so
  `YOKE_PROBE` yoke_silver_dark's lap term 1.0 -> 0.72 and side term 0.63 -> 1.7 (k [1.0, 1.53, 1.7, 0.72, 0]; the
  judge's 'lower k[1]' was the yoke branch's light): lower / upper 0.87 at the stop and the design eye (0.91; photos
  0.90-0.955 -- the judge's <= 0.90), lower / cover 0.77 at P1046408 (0.71; photo 0.82-0.93), 0.79 at P1046409, the stop's
  lower / cover 0.72 ([Y1] >= 0.70).  J BAND (FID5-05): its own material `yoke_band` (assemble / lookdev: satin dark grey
  0.075, metallic 0.6, rough 0.30; `fd_detail_a.BAND_MAT`) instead of the PCL grip's pcl_pewter (owner's open question:
  the PCL's colour stays); in the merged light the pewter band read 33-37 / p90 54-56 at the photo cameras (the judge's
  105-117 was the yoke branch's light), the photos 26-57 / p90 109-128 with lit rolled edges: viewer VIEWER yoke_band a
  lighter, more metallic base with a tighter sheen kept by the cabin law (color 0.16, metalness 0.9, roughness 0.22,
  specIn 2.5, SPEC_KEEP): 53-57 / p90 73-75 at P1046408 / 09 / 10 (Mexico 51 / 64).  Not taken (minors, reported):
  FID5-03 (the insert's bead-blast grain / near-field term), FID5-04 (the badge band as a raised satin field: a drawing
  revision), FID5-06 (the cover specks: SwiftShader's diffuse image light, as rev Q), FID5-08 (deferred owner items).
  viewer_test [Y1e] (new; `YOKE_LOOK_R`, `yoke_side_edges`): at the P1046408 pilot-yoke camera the far side >= 0.75 of
  the reference and the near >= 0.25 darker, the badge's p2 >= 0.40 of the insert, the lower insert >= 0.75 of the cover,
  the band 35-70; from the pilot stop lower / upper <= 0.90.  KEPT, reported: the yoke track's elevator coupling (parked,
  the elevators hang +8.08 deg TE down with the parked yokes -- photos 0517 / LX-FLI); it moves the exterior default pose
  (the horn balances stand out of the fixed tips parked).
  Build (both tiers rebuilt): 2,721,764 triangles / 48.08 MB, light tier 2,296,131 / 40.34 MB (the triangle counts of the
  merge; interior 873.0k of 896k, yokes 42,868 of 43k each).  Verified on this build: fit_check FIT OK (138 ok, no open
  row; ~69 min), consistency_2d3d 157 / 157, test/yoke_mesh_check.py YOKE MESH OK (42,004 meshed, 42,868 in the GLB
  part; cover groove 591 faces), model.yoke_checks not rerun (the solids are unchanged: only the cover's material
  split), drawing.master L6 / L6B / L6Y / L6Y2 (no text crossings on L6Y / L6Y2; L6 / L6B only their PDF timestamps,
  left alone), drawing.sheet + drawing.verify (SVGs unchanged, the same dimension table), the FULL viewer_test 231 / 231
  (132 min, beside fit_check and artifact_test: [Y1] cover 213 / inserts 175 / 153 / column 50, [Y1d] step 0.14 / badge
  0.57 / insert 0.89, [Y1e] far 0.87 / near 0.38 / badge 0.57 / lower / cover 0.77 / band 53 / stop lower / upper 0.87,
  [FD-L3] glareshield 60 (lip 71 / underside 44), [FD-L4] yoke 216, [FD-L6] p50 75 bands 26 / 51 / 13 %, [T4] pilot 94
  / fd_cabin 77, [CR4-05] the parked elevator droop, [FD-L7] the exterior default view unchanged), web/package.py verify
  OK (meshopt 17.50 + 15.03 MB), the Artifact bundle 117.8 MB in 2 publishes (63.7 + 54.2 MB), artifact_test 70 / 70.
  Photo | before (d007ea8, GEOM A's paddle yoke) | merged sheets of the standard views: out/tmp/fd_yoke_merge/cmp_*.jpg
  (pilot, copilot, fd_cabin, cockpit_preset, panel_408b, cabin_fwd_406, pedestal, pilot / copilot_eye_yoke, ext_wind,
  yoke_p408_pilot / p409_copilot / mex_pilot / press_pilot; gitignored: they embed the photos).
- Flight deck + yoke fix r1 (2026-10-12; the flight-deck judges' round 1 after the yoke merge, at 4d0f95e: owner 6.8
  (yoke 7.0), fidelity 6.8 (yoke 7.8); FDY-O1-01..06, FIDY1-01..07).  No table changed; L6 regenerated (it draws the
  lip through `interior.glareshield_lip`), L6B / L6Y / L6Y2 identical.  Look development in one viewer page again
  (out/tmp/fdy_fix_r1/ld.py jobs: `?cabTrim=` / `?partTrim=` / `?viewer=` / `?yokeProbe=` overrides on a reload, or
  in-page `LD.patch` material flags; `mstat.py` per part:material p5 / p50 / p95 and the local 9 px sd from the ID
  pass) and, for the fleece's shape, the seats-only LAB page (out/tmp/fdy_fix_r1/lab).
  HOOD (FDY-O1-03 / FIDY1-01, major): `interior.lip_dz` -- ONE C2 curve through the approved GLARESHIELD lip_dz knots (a
  natural cubic spline mirrored about BL 0, so level on the centreline; checked monotone, else the monotone PCHIP;
  straight with its end slope beyond the last knot, where the old clamp had put a second corner at |BL| 0.70 inside the
  0.71 cheek), used by `glareshield_lip` (the drawing, the design-eye camera: unchanged to 0.1 mm) and
  `flightdeck.lip_z` (hood, rolled lip, stitch rows, fascia top, `z_brow`).  np.interp had drawn the arch as a polyline
  whose slope broke 18 -> 46 deg at |BL| 0.50: the hood, its lip, the stitching and the fascia turned down at the
  outboard ends in straight facets with a V corner; the curve departs from the polyline by <= 9.3 mm (above it, |BL|
  0.45, between the knots) and turns over a >= 0.18 m radius.  `flightdeck._hood_grids` rows every ~8 mm outboard of |BL| 0.40 (129 rows, were 81 at 17.8 mm).
  FLEECE (FDY-O1-01 / FIDY1-02, major): `materials.js` fleece `locks` mode (replaces r5's `pile` worms -- veined marble /
  crumpled foil): every jittered cell of a 3-D lattice carries one LOCK, an elongated soft blob in the tangent plane
  (`locks` [freq, albedo lo, hi, bump, len min / max (cells), asp, jit, tipK, gap, seam]; `lockShape` [tip taper, bend,
  strand contrast, strands, swirl, ragged edge]) laid along the pile's flow (down the vertical faces, forward over the
  tops) turned +-0.9 rad and swirling over ~10 cm, lit toward its tip, a few fibre strands, a ragged edge; where locks
  overlap the top one wins (max, not a sum) with a dark seam between them, the dark gaps where none reaches; 100 / m
  (13-25 mm locks) over a fine 200 / m layer.  Base (0.33, 0.27, 0.27) R = G (P1046410 R = G, B - R 19), CABIN_TRIM
  0.42 -> 0.60: at panel_408b luminance ~119 (P1046408 121), local sd 13.8 (13.9), B - R +20 (photos +15..+27).  The
  lab's brighter room light had asked for a darker, contrastier mat that read as dark blue camouflage under the cabin
  law -- tune it in the viewer.  Geometry (`seats.shag`): over the r5 rolled rim a soft FRINGE of 17-27 mm locks, 0 ..
  4.2 mm out (`SK_FRINGE`, `SK_FRINGE_K`), its phase shifting round the roll (`SK_FRINGE_ROW`: lumps, not vertical
  ribs), rims every `SK_RIM_STEP_F` 7.2 mm (5 / 6.5 mm put the crew seat over its 66.3k cap): crew seats 65.3k / 65.5k.
  YOKE FINISH (FDY-O1-02 major / FIDY1-04, viewer): CABIN_TRIM entries 8-12 = a NEAR-FIELD term (x lo below WL y0 ..
  x hi above y1 on the diffuse, a 12th entry its share on the reflections: the lower stem sees the dark lap and lower
  panel, the crown the windshield over the glareshield) -- the cover [.., 0.5, 1.06, 1.79, 1.91, 0.7] (yoke close-up
  p5 206 -> 183, median 209-214 kept), the pads [.., 0.7, 1.2, 1.78, 1.92] with a 1.7 mm grain (VIEWER yoke_leather; the
  1.1 mm pebble had faded to one flat tone at every crew-seat distance); the body 'yoke:grip_black' [0, 0.40, 0.5, 1,
  0, 12] + PART_TRIM 'yoke_L / _R:grip_black' roughness 0.22, specIn 3.5, a warm specularColor (the sky's blue out of
  it): at the yoke close-up p10 / p50 / p95 45 / 58 / 106 (was 48 / 53 / 60, B - R +21 -> +9; P1046409 38 / 69 / 127),
  at the pilot stop body / cover 0.30, pads / body 1.12 ([Y1b] 0.22-0.34 / 1.0-1.4); YOKE_PROBE yoke_silver x 1.25 (+5 %
  at the close-up cameras; [Y1d] insert / cover 0.94 at the P1046408 camera, <= 0.97).
  MINORS: FDY-O1-04 the windshield / side-window retainers 12 -> 8 mm (`fuselage_parts.GLAZING_RETAINER` -4.5 / +3.5)
  in a darker satin metal (0.36, rough 0.30; assemble / lookdev): pro3001_stbd34_close / pro3005_port_close show a ~4-5
  mm light edge line, not a polished ring (the fastener rows were not added: a glazing-part change the L2 rows read);
  FDY-O1-05 the glazing seal lip 4 -> 1.8 mm (`GLAZING_TRIM seal_w`; fit_check 30 unchanged, nearest 2.9 mm);
  FDY-O1-06 the harness webbing crowned 1.2 mm across with rounded edges (`seats.ribbon` crown, `HARN_CROWN`) and a
  woven sheen (VIEWER harness sheen 0.7); FIDY1-03 pedestal_gunmetal CABIN_TRIM 0.6 -> 0.25 (panel_408b 63 -> ~48); FIDY1-06 CB panels
  (`fd_detail_b.CB`): heads r 4 -> 3 mm on thin dark-metal rings (`sleeve_mat`; the white collars read as polka dots),
  the dark label cells on a dark-grey strip framed by white rules (`cell_mat`) -- the "light-silver strips on both
  consoles" of the finding REFUTED in part: P1046410's LH and P1046409's RH front blocks show dark cells with white text
  over the bus band, only the AOPA RH rear block light silver cells, kept so; FIDY1-07 the walnut lighter and less
  saturated (VIEWER veneer_walnut (0.105, 0.078, 0.058): the divider at cabin_fwd_406 ~(55, 50, 50) against P1046406's
  (66, 53, 50)), the overhead's fill 0.5 -> 0.85 (PART_TRIM 'interior_lining:panel_dark': 30 -> 47 at cabin_fwd_406,
  P1046406 70, held by [T14] <= 50 at the crew stops, 42 / 47 -- P1046408 reads it ~45; the CB bezel frames on the
  lining share it), the
  MASTER POWER guard 0.75 of a black recess frame in the dim placard red (`OVH master_k`).  FIDY1-05 (OPEN owner
  question, the crew-seat / console tables' re-measure): evidence only -- `?seatpark=aft` parks both seats at full aft
  travel (70 mm) for photo comparisons at the P1046410 / 09 / Mexico cameras; the default is unchanged.  Look-dev
  overrides added to `materials.js`: `?partTrim=part:material={json}|..`, `?viewer=material={json}|..`.
  Build (both tiers rebuilt): 2,740,904 triangles / 48.45 MB, light tier 2,315,271 / 40.71 MB; interior 892.7k of 896k
  (crew seats 65.3k / 65.5k of 66.3k, flight_deck 210.4k of 211k, interior_lining 176.6k; seat_pax3-6 34,834 OVER the
  34.8k cap as before).  Verified on this build: fit_check FIT OK (138 ok, no open row: 27 PDU bezel tops 54 / 54, 24
  harness on the fleece +1.5 / +1.6 mm, 26 no coplanar overlaps, 30 nearest 2.9 mm, 30b / 22 all seated, 31 10.3 mm),
  consistency_2d3d 157 / 157, drawing.master L6 L6B (L6: 25 texts crossed by lines, as before; L6B unchanged),
  drawing.sheet + drawing.verify (the GA's glazing lines moved with the retainer band; the same dimension table),
  web/tour_data.py --check current, viewer_test `--only fdlook` 10 / 10 and `--only tour` 31 / 31 (the first tour try
  timed out on a screenshot beside the comparison captures; rerun clean), the FULL viewer_test 231 / 231 (~2 h beside
  artifact_test: [FD-L2] carpet 14 / consoles 16, [FD-L3] glareshield 60 (lip 72 / underside 44), [FD-L4] yoke 212,
  [FD-L5] sheepskin (113, 115, 133) lum 116, [FD-L6] p50 76, bands 26 / 50 / 13 %, [T14] overhead 42 / 47 / 48, walnut
  47, [Y1] cover 212 / up 183 / lo 153 / body 63 / pads 70, [Y1b] body 0.30, pads / body 1.12, [Y1d] insert / cover
  0.94, [Y1e] far 0.85 / near 0.38 / lower / cover 0.78 / band 53), web/package.py verify OK (meshopt 17.65 + 15.18 MB),
  the Artifact bundle 119.0 MB in 2 publishes (63.3 + 55.7 MB), artifact_test 70 / 70.  Photo | before (4d0f95e, the
  judges' renders) | after sheets of the standard views and close-ups: out/tmp/fdy_fix_r1/cmp_*.jpg (gitignored: they
  embed the photos; the comparison captures ran at pedestal_gunmetal 0.33, the shipped value is 0.25).
- Flight deck + yoke fix r2 (2026-10-16; the flight-deck judges' round 2 after the yoke merge, at e6f8914: owner 7.1
  (yoke 7.5), fidelity 6.8 (yoke 7.5); FDY-O2-01..06, FIDY2-01..08).  No table changed (L6 / L6B / L6Y / L6Y2 not
  regenerated: nothing they draw or check moved).  Look development in one viewer page again (out/tmp/fdy_fix_r2/ld2.py
  jobs; tools/furjob.py patches the fleece's fur in the page and rebuilds the shells, tools/paljob.py reloads with
  ?cabTrim= / ?viewer= / ?partTrim= / ?yokeProbe=, tools/fdm.py / mm.py the per-material medians and the judges' fleece
  texture measure under the page's own ID masks), a numpy preview of the fur field (tools/furprev.py).
  SHEEPSKIN AS SHELL FUR (FDY-O2-01 / FIDY2-01, the major of seven judge rounds; six flat 2-D pile patterns had read as
  prints -- lichen, marble, foil / worms, coral, leaf / fish-scale locks -- on a smooth slab): `materials.js` furPatch /
  addFur / furDirs -- the crew seats' fleece meshes are drawn as a stack of offset layers along the welded normal: the
  base mesh is the ROOT layer 8 mm under the drawn surface (dark, `root` 0.18), FUR.n SHELLS (14; 8 on the low quality
  tier, main.js; ?furN=, ?fur=0 the flat `fleece` patch) at even heights up to the tips 1 mm over it, drawn after the
  mesh in ONE instanced call from its onAfterRender while it carries its own material -- the ID pass, the X-ray, the
  cutaway and the highlight swap the material and draw none; they cast no shadow, are never picked and follow the mesh's
  visibility.  Each shell keeps its cross-section of one pile field evaluated at the drawn surface point (only
  gl_Position moves, so every layer of a column reads one field, one shadow, one bake): two octaves of value noise
  (`oct` [freq, weight, twist, mode, vertical stretch, warp, crease power]: 450 / m blobs + 300 / m ridged curls, 1.3 x
  longer down the faces, twisting with the height, the second domain-warped) above a threshold rising 0.05 -> 0.75
  toward the tips (`t`), 40 / m lumps (taller, +-24 % albedo), short GATED partings at 30 and 60 / m (a parting only where a
  second noise exceeds the gate: slits, not a crackle net), a 1100 / m fray; the albedo 0.18 at the root -> 1 at the
  tips (`ao`), the normal tilted down the field's slope (`tilt` 0.9), the sheen on the tips; beyond 2.2-3.2 m from the
  eye the shells thin out and the root takes the pile's mean albedo.  The root's depth is bounded by the part's other
  surfaces under the pile (furDirs `obstacles`: the leather the pads sink into and wrap -- 40 % of the fleece vertices
  have it within 11 mm -- had shown through the partings as pale holes; the root no deeper than 0.6 of the free depth,
  sampled every ~3 mm).  Base (0.245, 0.198, 0.212), sheen (0.35, 0.32, 0.34).  At panel_408b, the judges' measure
  (rows 760-845, the fleece mask eroded 6 px), model / P1046408: median 118 / 116, p10 99 / 87, p90 140 / 146, high-pass
  sd at sigma 1 / 2 / 4 / 8 8.6 / 10.4 / 11.9 / 14.5 against 6.5 / 9.7 / 12.4 / 16.9, hp4 skew +0.48 / -0.19 (the r1
  locks: +1.09, p10 101); the whole cushion (117, 118, 139) against (109, 113, 136).  The silhouette breaks up by itself
  (the photos' fuzzy outline).  Builder (`seats.py`): the pads' crown 16 / 12 -> 24 / 18 mm reached over SK_CROWN_R
  75 mm, the top roll 17 -> 22 mm (pillow() scales it to the thinner edge) -- puffy loaves instead of flat slabs, the
  apex on the drawn cushion top / back front (an 85 mm rise put the pads' rear 10 mm under the drawn top at
  consistency_2d3d's pan bins, its tolerance; 75: 5.0 mm); the pads' bottoms stay where the 16 / 12 mm crowns had them
  (SK_T_SEAT / SK_T_BACK, the edge 8 / 6 mm thinner): sunk deeper than the leather's front-roll radius the wrap
  (`_wrap`) turned the lowest rows through its axis -- an inside-out sliver coplanar with the leather (fit_check 26,
  0.9 cm2), found by a seat-only copy of that check (out/tmp/fdy_fix_r2/tools/seatcop.py, ~1 min).
  viewer_test [FD-L10] (new): both seats' fleece with the pile layers and P1046408's structure at panel_408b.
  Look-dev route: the lab and the preview showed what the structure measures cannot -- shells read as grass spikes /
  coral where the threshold falls slowly (tall prisms seen grazing), as a smooth felt where it rises late; the
  partings as isolines of one noise drew a crackle net, gated they are short slits.
  TITANIUM (FIDY2-02): the sub-panels / plates a mauve brushed metal (VIEWER panel_titanium (0.25, 0.225, 0.245),
  metalness 0.85, roughness 0.27, specIn 1.9, brushed bands +-35 % over 5 x 30 cm, streaks 15 %), CABIN_TRIM 0.8 -> 0.5
  with a near-field term (x 1.05 below WL 1.78 .. x 0.8 above 1.88, half on the reflections: the band under the PDUs had
  read 114-128 against P1046408's 91), the bake's contact pass weighted more on it (build.AO_CONTACT_POW_MAT 1.3: the
  seams, bezel feet and plate feet): at panel_408b p10 / p50 / p90 52 / 84 / 125, (82, 83, 93), against 28 / 82 / 148,
  (81, 81, 94) (was 69 / 96 / 129, neutral (94, 96, 100)); the band / the plates' foot 96 / 90 against 91 / 89.
  POSTS (FIDY2-04): lining_flightdeck 0.5 -> 0.95, lining_fd_post 0.5 -> 1.05 (panel_408b 57 / 70 -> 86 / 99 against
  P1046408's 134 / 128; the pilot stop 100 / 108, P1046410 ~108); the reveal funnel next to the glass keeps its darker
  face.  HOOD (FDY-O2-03): PART_TRIM 'flight_deck:leather_glareshield' fill [0, 0.55], specIn 0.35 -> 0.2, sunIn 0.07
  -> 0.03 -- 104 / 99 -> 73 / 69 from the pilot / co-pilot stop (P1046410 67); the lip / underside panel_408b sees keep
  their entry.  YOKE (FDY-O2-02, FIDY2-06): the pads' grain 0.9 mm at -10 / +6 % (was 1.7 mm +-15 %: granite / denim
  speckle) with a warm specular tint; the grips' satin black sharper and stronger (roughness 0.2, specIn 4.0, reflection
  floor 0.45, side-window term 14; body / cover 0.30 at the pilot stop, [Y1b] 0.22-0.34); the lower insert less blue
  (0.45, 0.46, 0.47) and its probe terms x 1.2, the side term x 1.3 (lower / upper 0.90 at panel_408b against the
  photos' 0.92-0.95, 0.88 from the pilot stop, [Y1e] <= 0.90); the cover's 'win' rim term KEPT at 25 (FIDY2-06's
  softer rim on the shaded flank: 12 / 19 took the cover's highlight spread at the pilot stop to 16 / 19, under [Y1b]'s
  20 -- the r2 yoke judges' CR2-06 edge highlights; the two findings pull against each other).  QUADRANT / PEDESTAL
  (FDY-O2-04): the trim panel's TRIM INTERRUPT a proud gloss-black cap with a rolled
  rim, the trim rockers solid gloss-black caps split across the middle (one half pressed 1.5 mm lower), one short legend
  stroke each, the AILERON TRIM outline gone (`fd_detail_a.quadrant`); 'flight_deck:black' a warm base / specular,
  specIn 0.5 (PART_TRIM `color`, new): the quadrant plate (27, 35, 53) -> (33, 32, 37), B - R +26 -> +4; pedestal
  gunmetal 0.25 -> 0.15 (45 -> 39 at panel_408b, P1046408 27); the palm tray 0.3 -> 0.42 (91 -> 106, P1046408 117).
  CB PANELS (FDY-O2-05, FIDY2-05; `fd_detail_b.CB`): the collar rings satin black, 0.5 mm (the dark-metal rings mirrored
  the windshield: bright bead chains), the label cells in the plate's black (the legend_grey cells read as light piano
  keys), the LH bus bands BLUE again (P1046410), 1.6 mm (`band_blue`).  WALNUT (FIDY2-08): (0.15, 0.123, 0.118), env
  0.6 -- (72, 69, 74) at cabin_fwd_406 against P1046406's (78, 70, 73) (was (50, 44, 40)).  RETAINER (FDY-O2-06 /
  FIDY2-07): glazing_retainer a dark satin metal 0.10 / rough 0.40 (assemble / lookdev): no light ring round the panes
  from outside; the surround's screw rows (optional in the finding) not added.
  OWNER-DELEGATED DECISIONS (2026-10-16, "use your best taste and judgement"): (1) glareshield outboard lip KEPT -- at
  the photo-fitted panel_408b the model's lip outline lies on P1046408's along the outboard sweeps within a few px (the
  judge: 10-15 px at the crown, less toward the ends); the bundle-adjusted P1046409 / 10 cameras sit 40-60 px off on the
  hood's CROWN as well (a camera error, the same at every station), so no camera shows the arc consistently > 5 mm
  larger / rounder; (2) the crew seats KEPT at the neutral SRP, no table change (FIDY2-03) -- at the bundle-adjusted P1046410
  camera the seat back fills the left third at the neutral seat and MORE at full aft travel (?seatpark=aft: closer to
  the camera), full forward still leaves it in frame (the camera, STA 4.685 WL 1.92, stands aft of and below the backs'
  tops, STA 4.35-4.46 WL 2.43), while the photo shows no back at all and its cushions near the lens: the photo's camera
  stood ahead of the backs (or they were reclined) -- the BA depth / fov trade-off, not a seat pose; at the photo-fitted
  panel_408b the cushions sit ~45-55 px under P1046408's, but the poses that lift them there (fix r5: up / forward
  travel) cover the side consoles the photo shows clear; no pose within the L6 travel fits two photos with the consoles
  visible and no table is demonstrably off in two photos (evidence: out/tmp/fdy_fix_r2/ld2 c01 / c02 / r00,
  seat_p410_neutral_aft.png: P1046410 | neutral | full aft); (3) PCL pewter, overhead tone, satin dark-grey column, the
  parked elevator droop stay; the grip depth and the badge field deferred (the yoke solids' cache
  re-runs).  ?seatpark=dy,dz (glTF Y / Z offsets, m) added for the photo comparisons.
  Build (both tiers rebuilt): 2,736,464 triangles / 48.38 MB, light tier 2,310,831 / 40.64 MB; interior 888.3k of 896k
  (crew seats 63.7k / 63.9k of 66.3k; seat_pax3-6 34,834 OVER the 34.8k cap as before).  Verified on this build:
  fit_check FIT OK (138 ok, no open row: 24 harness on the fleece +1.6 mm, 26 no coplanar overlaps, 31 10.3 mm),
  consistency_2d3d 157 / 157 (the crew cushion crown row 5.0 mm of 10), drawing.sheet + drawing.verify (SVGs
  unchanged), web/tour_data.py --check current, the FULL viewer_test 231 / 232 (~2 h, beside artifact_test) with
  [Y1b] failing at the cover rim term 19 (its highlight spread 19 < 20) -> reverted to 25 and `--only tour` rerun
  31 / 31 ([Y1b] spread 22); in the full run [FD-L2] carpet 14 / consoles 17 / titanium 84 / lining_fd 93, [FD-L3]
  glareshield 60 (lip 71 / underside 44), [FD-L4] yoke 211, [FD-L5] sheepskin (117, 119, 139) lum 120, [FD-L10] 2 x 14
  layers, hp4 skew +0.33, p10 100, sd4 12.2, sd1 8.8, [FD-L6] p50 75, bands 26 / 50 / 13 %, [T4] pilot 103 / fd_cabin 78,
  [T14] overhead 42-48, bezels 31-45, walnut 73, [Y1] cover 212 / up 183 / lo 161 / body 65 / pads 71, [Y1d] insert /
  cover 0.94, [Y1e] far 0.84 / near 0.38 / lower / cover 0.83 / band 53, pilot stop lower / upper 0.88;
  web/package.py verify OK (meshopt 17.62 + 15.16 MB), the Artifact bundle 118.8 MB in 2 publishes (63.2 + 55.6 MB).
  After a container restart, on the committed code (6a181cf; the bundle's viewer files byte-identical to it):
  artifact_test 70 / 70, `--only tour` 31 / 31 again ([Y1b] spread 22; a first try timed out on a screenshot beside the
  comparison captures), drawing.sheet + drawing.verify (SVGs unchanged, the same dimension table).  Photo | before
  (e6f8914, the judges' r2 renders) | after (ld2/p05_final) sheets of the standard views and close-ups:
  out/tmp/fdy_fix_r2/cmp_*.jpg, the cushion close-ups cmp_cushions.jpg (gitignored: they embed the photos).  Seen
  there and not tuned: on the crew seat backs seen from behind (seats_aft) and at close range the pile's gated partings
  read as scattered dark seams in the light fleece; at panel_408b the structure still measures hp4 skew +0.46 / p10 101
  against P1046408's -0.19 / 86 (the fidelity judge's target band: skew -0.4..+0.2, p10 80-90).
- Flight deck + yoke fix r3 (2026-10-16; the flight-deck judges' round 3 after the yoke merge, at 5d01757: owner 7.5
  (yoke 7.5), fidelity 7.2 provisional (yoke 7.8) -- the fidelity judge's renders had not finished under the shared
  SwiftShader load, FIDY3-00; FDY-O3-01..03, FIDY3-01..03).  No table changed (L6 / L6B / L6Y / L6Y2 not regenerated:
  nothing they draw or check moved).  Look development in one viewer page (out/tmp/fdy_fix_r3/ld.py jobs; fj.py the fur
  in-page, furstat.py the fleece structure on the page's own ID masks -- eroded 10 px, the toolbar / Panel button
  excluded: the judges' close-up masks had taken the white Panel button into the fleece's dark tail --, pmat.py model vs
  photo per part:material, ymet.py the yoke; phstat.py the photos' cushions; tools/furprev.py the pile field's albedo).
  SHEEPSKIN (FDY-O3-01 major, FIDY3-03; tuning, not a new pattern: the shell fur stays): within ~1 m the gated
  partings read as scattered dark pits / streaks -- grime on a lavender popcorn -- on the seat backs from the cabin and
  the cushion tops: the gaps fell through to a 0.18 root (0.2 of the tips), the partings raised the threshold by 0.45 /
  0.35 (straight down to the root), the 40 / m lumps blotched the albedo +-24 %.  `materials.js VIEWER sheepskin.fur`:
  root and lowest layers 0.34, the layers' albedo convex in the height (ao [0.34, 1.13, 1.8]) over a threshold that
  rises faster near the root (t power 0.9) -- the visible layers spread evenly instead of piling up at the tips with a
  long dark tail --, partings 0.2 / 0.15, lumps +-10 %, the fine tilt 0.9 -> 0.55, and a new `clump` term (furPatch:
  [freq, height, vertical stretch] -- the slope of soft 28 / 65 per m mounds 5 / 1.8 mm high tips the shading normal, so
  the clumps are lit on one side and shaded on the other: the photos' dark sits in the shaded folds); `partCap` (cap on
  the partings' threshold rise) added, unused.  High-pass skew at sigma 4 / 8 (fleece eroded 10 px): the owner judge's
  cush_close -0.70 / -0.98 -> -0.38 / -0.40 (sd8 9.3 -> 11.9), seats_aft -1.32 / -1.32 -> -0.56 / -0.46, quadrant
  -1.29 / -1.40 -> -0.47 / -0.43; P1046409 / 10's cushions -0.50 / -0.49 and -0.31 / -0.32, sd8 12.5 / 13.3; panel_408b
  (the judges' rows 760-845) skew +0.46 -> +0.18, p10 101 -> 99 -- those rows lie over the model's cushion TOPS but over
  P1046408's cushion fronts (the model's cushions sit ~45-55 px lower in that frame, the open seat-pose question), so
  the photo's p10 86 there is not the same surface.  viewer_test [FD-L10b] (new, `--only fdlook`): the close poses'
  skew >= -0.6 / -0.75 and sd8 8-17.  Also tried: lighter gaps alone (f03: the close-up skew went positive, the fleece a
  flat felt), finer tufts (aliasing at panel_408b).
  FOOTWELL (FDY-O3-03): the "brown back wall" was the footwell's front closure in the shared `black` -- fix r2's warm
  PART_TRIM 'flight_deck:black' (the quadrant plate) tinted it --: now `panel_dark`; `fd_detail_a.rudder_linkage`
  (RUDDER_LINK, builder detail [E], P1046408 / 09 brightened): per pedal pair a bell-crank horn on the torque tube, the
  push-pull rod forward to a clevis on the front closure with bright rod-end eyes, two close-coiled return springs from
  the horn's cross pin to floor eyes, the toe-brake hoses from the tube brackets forward and down to bulkhead fittings,
  a quilted crinkled-foil insulation blanket (panel_silver) on the upper front wall and two low pedal housings at the
  front (P1046408's footwells: foil blanket, dark boxes, black rods with bright bolts); in fit_fd_a 28 with the walls
  (pedals over their travel 10.1 mm -- the walls, as before --, shoes 26.7 mm, legs 20.9 mm; the housings first stood
  55 mm high and the 95th's toe at full rudder crossed them, -10 mm: now 36 mm).  Budget: flight_deck 96k -> 99.5k,
  interior total 390k -> 393.5k (RES 1 figures; 216.7k of 218.9k built at RES 2).
  YOKE CLOSE-UP (FDY-O3-02, minor): the pads (CABIN_TRIM yoke_leather) a steeper top-lit gradient x 0.6 at WL 1.80 ..
  x 1.45 at 1.90, a 0.3 reflection floor and the side-window term, glossier (VIEWER roughness 0.32, PART_TRIM specIn
  2.5): p10 / p50 / p90 60 / 70 / 76 -> 56 / 76 / 85 at the judge's yoke close-up (P1046409 68-90), the pilot stop's
  pads / body 1.24 ([Y1b] 1.0-1.4, photos 1.06-1.27).  The upper insert less blue (VIEWER yoke_silver (0.60, 0.61, 0.63),
  B - R +37 -> +33), its LUMINANCE kept, the finding refuted in part: the judge's yoke close-up is no photo's camera --
  at the photo-fitted cameras the insert is 0.94 / 0.95 of the cover (P1046409 / P1046408) against the photos' ~1.0 /
  0.93, and [Y1d] holds it <= 0.97 at P1046408's; the probe's overhead term +15 % and a warmer tint changed the
  close-up by < 1 % (the reflection there is not the overhead term); the lower insert kept ([Y1e] lower / upper <= 0.90
  from the pilot stop, 0.88).
  LINING / POSTS (FIDY3-01): measured on this build -- panel_408b lining_flightdeck 77 / post 96 against P1046408's 135
  / 123, the pilot stop 100 / 108 against P1046410's ~108: CABIN_TRIM lining_flightdeck 0.95 -> 1.15, lining_fd_post 1.05
  -> 1.2 (panel_408b 87 / 103, the pilot stop 111 / 114, fd_cabin 118 / 110); the rest of P1046408's gap is that photo's A-
  pillar region against the blown windshield / side windows (1.2 / 1.25 read 89 / 104 there and put the pilot stop 5-7
  over P1046410), so not taken further.
  TITANIUM (FIDY3-02): VIEWER panel_titanium brush band +-35 -> +-50 % and the bake's contact pass on it 1.3 -> 1.6
  (build.AO_CONTACT_POW_MAT): p10 / p50 / p90 at panel_408b 52 / 84 / 126 -> 47 / 82 / 129 (P1046408 27 / 84 / 147).
  FIDY3-00 (the provisional fidelity verdict): the numbers above are this round's own measurements under the page's ID
  masks at the photo-fitted / judges' cameras (out/tmp/fdy_fix_r3/ld b00 = before, v02 = after).
  OWNER-DELEGATED DECISIONS (2026-10-16, as fix r2 recorded): the glareshield outboard lip kept (no fitted camera shows
  the arc consistently > 5 mm larger); the crew seats at the neutral SRP, no table change (fix r2's evidence; the lead's
  decision of 12:25); PCL pewter, overhead tone, the satin dark-grey column and the parked elevator droop stay; the grip
  depth and the badge field deferred.
  Build (both tiers rebuilt): 2,743,884 triangles / 48.53 MB, light tier 2,318,251 / 40.79 MB; interior 895.8k of 903.7k
  (flight_deck 216.7k of 218.9k; seat_pax3-6 34,834 OVER the 34.8k cap as before).  Verified on this build: fit_check FIT
  OK (138 ok, no open row: 28 shoes 26.7 mm, 23 shells wound outward -- the linkage's clevis bracket at e 0.2 / nv 7 had
  folded 8 directed edges, now e 0.3 --, 24 harness +1.6 mm, 26 none), consistency_2d3d 157 / 157, the FULL viewer_test
  232 / 233 (~2 h beside fit_check and the package: [FD-L2] carpet 14 / consoles 17 / lining_fd 104 / titanium 81, [FD-L3]
  glareshield 60 (lip 71 / underside 44), [FD-L4] yoke 212, [FD-L5] sheepskin (118, 120, 141) lum 121, [FD-L6] p50 76,
  bands 26 / 50 / 13 %, [FD-L10] skew +0.07, p10 98, sd4 13.0, sd1 9.0, [T4] pilot 108 / fd_cabin 78, [T14] overhead
  42-48, bezels 31-46, walnut 72, [Y1] cover 212 / up 183 / lo 161 / pads 78, [Y1b] spread 22, body 0.30, pads / body
  1.20, [Y1d] insert / cover 0.94, [Y1e] far 0.85 / near 0.38 / lower / cover 0.83 / band 54, pilot stop lower / upper
  0.88) with [FD-L10b] the one failure -- the tour's controls hint (a dark pill with white text) lay over the fleece at
  the close poses (skew -2.50 / -1.73): the test hides it for those two shots, and `--only fdlook` 12 / 12 ([FD-L10b]
  cush_close -0.39 / -0.41, sd8 11.9; seats_aft -0.55 / -0.46, sd8 12.6); web/package.py verify OK (meshopt 17.67 +
  15.21 MB), the Artifact bundle 119.1 MB in 2 publishes (63.4 + 55.7 MB), artifact_test 70 / 70.  Photo | before
  (5d01757, the judges' r3
  renders) | after sheets of the standard views and close-ups: out/tmp/fdy_fix_r3/cmp/cmp_*.jpg (gitignored: they embed
  the photos).
- Flight deck + yoke fix r4 (2026-10-16; the flight-deck judges' round 4 after the yoke merge, at 61c8255: owner 7.8
  (yoke 7.6), fidelity 7.6 (yoke 7.7); FDY-O4-01..05, FIDY4-01..06).  No table changed (L6 / L6B / L6Y / L6Y2 not
  regenerated: nothing they draw or check moved).  Look development in one viewer page again (out/tmp/fdy_fix_r4/ld.py
  jobs, tools/paljob.py reloads with ?cabTrim= / ?partTrim= / ?viewer= / ?yokeProbe= / ?footSkip= / ?cabProbe2=,
  tools/m408.py the panel_408b checks -- the judge's knee boxes, the knob tops, the lip's column profiles, the titanium
  under P1046408 --, pmat.py / ymet.py per material); photo | judges' before (61c8255) | after sheets
  out/tmp/fdy_fix_r4/cmp/cmp_*.jpg (gitignored: they embed the photos).
  KNEE AREAS (FIDY4-01, the major): at panel_408b the cove under the outer sub-panels and the footwell's outboard walls
  read flat mid-grey -- the judge's boxes 43 / 37 against P1046408's 5 / 12; under the model's masks fd_cove 66 against
  8 (fix r3's ~41 had been read over the cove's lit rim), the consoles' forward faces (fd_consoles:lining_flightdeck)
  113 against 6 (124 in the footwell close-up, P1046409 ~31), the footwell's foil blanket / the outer plates' edge strips
  (panel_silver) 119 / 109 against ~25 / 31.  `materials.js FOOT_SKIP` (lining_flightdeck, fd_cove, panel_dark,
  panel_silver; ?footSkip=): CABIN_LOOK.foot's x 1.8 footwell fill only on the pedals, the linkage and the hoses
  (new shader flag `noFoot`); fd_cove CABIN_TRIM 1.45 -> 0.5; PART_TRIM 'fd_consoles:lining_flightdeck' fill 0.25,
  'flight_deck:panel_silver' fill 0.4 / specIn 0.3: the boxes 12 / 14, the cove 12, the console faces ~20, the blanket /
  strips ~58; [FD-L6]'s bands 29 / 49 / 12 % (P1046408 24.7 / 46.6 / 15.3).  viewer_test [FD-L11] (new): the boxes <= 22
  and the console faces <= 25 at panel_408b.  The judge's optional builder swoop not needed (the outer plate's
  outer_drop and the rolled lip are there; the walls round it were the lit part).
  KNOBS (FIDY4-04): the GFC 700's dual knobs, the BARO and GI 275 knobs in grip_black (`fd_detail_a.gfc700 /
  eyebrow_items / standby_details`; the VS wheel's slot rubber_black) -- the shared `black` carried fix r2's warm
  quadrant-plate tint, B - R -2..-5 against P1046408's +30..+37 -- and PART_TRIM 'flight_deck:grip_black' a 0.8
  reflection floor x 2.2 (the windshield on their knurled sides): 40 -> 59 at panel_408b, B - R +12 (P1046408's knob
  tops 61-82 / +34, the masks take the knobs' sides too).  The GFC face's streaky reflections of the apron:
  'flight_deck:bezel_black' roughness 0.45 (the display bezels' level kept, [T14] <= 50).
  TITANIUM (FDY-O4-01 / -02, FIDY4-06): the wavy vertical white streaks down the plates in the footwell / pedestal
  views were the cabin probe's window stripes (CABIN_LOOK probe2) mirrored by a 0.27-rough metal through fix r3's
  +-50 % bands: the stripes now fade to their mean over the roughness 0.15 .. 0.30 (and wherever a pixel spans > ~1/100
  of a stripe period; probe2 [2.0, 0.15, 0.30], ?cabProbe2=), the bands +-25 % over 12 x 60 cm (were 5 x 30 cm at +-50 %),
  the brushed streaks kept at 0.6 mm / +-15 % (1 mm at +-18 % -- FIDY4-06's finer, stronger streaks -- read as grey wood
  grain at the yoke close-up), the near-field over the PDU band x 0.9 (0.8); the
  contact pass on the titanium its own 3-10 mm reach at ^1.5 (`build.AO_CONTACT_MAT`, was 4-22 mm at ^1.6: the 30-40 mm
  soot halo round the 26-38 mm proud PARKING BRK handle gone; both tiers rebuilt).  At panel_408b p10 / p50 / p90 53 /
  85 / 116 (P1046408 28 / 82 / 148; fix r3 47 / 82 / 129): the median kept, the streaks and halos gone; the photo's
  remaining fine structure (high-pass sd 10-23 against 2-9) is mostly its lettering on the plates, which the model does
  not carry (no readable markings) -- FIDY4-06's range is only partly met.
  YOKE (FDY-O4-03, FIDY4-02 / -03): the grips and pads a flat mid-grey up close (49 / 60 / 87, 55 / 75 / 85 at the yoke
  close-up against P1046409's 38 / 60 / 183, 33 / 82 / 121): their reflections take a directional cabin probe
  (YOKE_PROBE grip_black [0.95, 0.9, 4.0, 0.12, 0.3], yoke_leather [0.25, 2.6, 2.6, 0.12, 0.35]: the dark cabin low, the
  overhead / windshield and the yoke's own side window bright), the 'yoke:grip_black' reflection floor 0.45 -> 0.3 and
  side-window term 25, PART_TRIM roughness 0.15 / specIn 5.0; the pads' floor 0.3 -> 0.1, the sun's glint 0.6,
  roughness 0.28, specIn 3.0 (?yokeProbe= now adds a probe for any yoke material): the close-up 37 / 69 / 122 (p99 148)
  and 50 / 73 / 99, from the pilot stop (both yokes, the test's 960 x 600 page) body / cover 0.28, pads / body 1.24,
  lunes / body 1.35 ([Y1b] 0.22-0.34 / 1.0-1.4, [Y1c] 1.0-1.8), panel_408b grips ~86 (P1046408 68 / 86).  (The round's
  first floor, 0.1, had been tuned on the pilot's yoke alone at 1200 x 900 -- 0.27 / 1.29 there --; the full
  viewer_test's both-yoke measure read 0.21 / 1.65 / 1.81 and failed [Y1b] / [Y1c]: 0.3 lifts the shaded flanks, hardly
  the close-up's median; tools/ytune.py runs viewer_test's yoke_look_checks on override queries.)  The upper insert's dark-cabin term +20 % and overhead -15 % (YOKE_PROBE yoke_silver k
  [1.95, 1.27, ...]: the stop's reflections point aft, R.y ~0.2-0.3, P1046408's low camera up, R.y ~0.6): 0.85-0.86 ->
  0.88-0.90 of the cover from the crew eyes, P1046408's camera unchanged ([Y1d] <= 0.97) -- the judge's 0.95 would put
  the photo-fitted camera over the photo's 0.93, so not further.
  LIP (FIDY4-05): PART_TRIM 'flight_deck:leather_black' `facing` [0.75, 2.4, -0.5, 0.5, 0.5] (new: the reflections x lo
  facing down .. x hi facing up, half of it on the diffuse): down the roll at panel_408b 80 flat -> 121 / 112 / 108 /
  103 / 96 (P1046408 ~144 -> 104); from the pilot stop the lip 81 -> ~95.
  HARNESS (FDY-O4-04): VIEWER harness a dark warm charcoal (0.036, 0.031, 0.027), the sheen 0.3 warm, the weave deeper
  (0.5 mm) and in the albedo (`leather.albedo` +-8 %, new) with the edges turned from the eye a shade darker
  (`leather.edge` 0.25, new): the cushion close-up 108 (98, 110, 130) -> 68 (67, 68, 77), the AOPA photo's dark grey
  belt.
  OUTSIDE (FDY-O4-05, `outside.js`): the hangars' roofs (`ROOFS`: a shallow gable, a barrel vault with ribs, flat with
  a parapet and roof plant), an eave band with its shadow line under every roof edge, low office annexes with ribbon
  windows in front of four of them (`ANNEX`, `officeTexture`), four generic business jets (low wing, aft engines,
  T-tail) and two high-wing singles at 60-170 m, seven light poles, ground crew in hi-vis vests, a baggage cart and a
  ground power unit (their shadows baked into the apron), a tree line of 420 crowns on the far ring, a cooler haze over
  the lowest degrees (`SKY.haze2`, as seen only) and the slab joints fading out from ~30 m (0.55 -> 0.10 alpha).  All
  of it SEEN only (`userData.seenOnly`, merged into one mesh: the image-based light is rendered without it, the
  calibrated cabin light does not move); no markings.  [FD-L1] at the crew stops: window median 194, the sky over the
  cowl 233 / 236, B - R 18.
  OWNER-DELEGATED DECISIONS (2026-10-16): the glareshield outboard lip KEPT (fix r2's measure stands: at the photo-fitted
  panel_408b the lip outline lies on P1046408's along the outboard sweeps within a few px; the bundle-adjusted P1046409 /
  10 cameras sit 40-60 px off on the hood's crown as well, a camera error -- no fitted camera shows the arc consistently
  > 5 mm larger); the crew seats KEPT at the neutral SRP, no table change (fix r2's evidence, out/tmp/fdy_fix_r2/ld2
  c01 / c02, seat_p410_neutral_aft.png: at the bundle-adjusted P1046410 camera the backs fill the frame MORE at full aft
  travel, the photo's camera stood ahead of the backs -- the BA depth / fov trade-off, not a pose; at panel_408b the
  poses that lift the cushions cover the consoles the photo shows clear); PCL pewter, the overhead tone, the satin
  dark-grey column and the parked elevator droop stay; the grip depth and the badge field deferred.
  Build (both tiers, bd26847): 2,743,884 triangles / 48.53 MB, light tier 2,318,251 / 40.79 MB (the counts of fix r3;
  interior 895.8k of 903.7k, seat_pax3-6 34,834 OVER the 34.8k cap as before).  Verified: fit_check FIT OK (138 ok, no
  open row; 26 no coplanar overlaps, 24 harness +1.6 mm) and consistency_2d3d 157 / 157 on bd26847's geometry (the
  viewer commits change no GLB); `--only fdlook` 12 / 13 on 140102a with [FD-L9] at 1 Hz rAF while a look-dev
  SwiftShader browser rendered beside it -- LOAD, not a regression: in the full runs it idles after 52 s at 46-53 Hz
  (nothing in 140102a requests frames); the first full run on 140102a 232 / 234 with [Y1b] (body 0.21, pads / body 1.65)
  and [Y1c] (lunes / body 1.81) failing -> the grips' reflection floor 0.3 (119a4fa, YOKE above), then the FULL
  viewer_test 234 / 234 on 119a4fa (101 min; [FD-L1] sky 233 / 236, B - R 18; [FD-L2] carpet 14 / consoles 7 /
  titanium 87; [FD-L3] glareshield 61, lip 71 / underside 44; [FD-L4] yoke 212; [FD-L5] sheepskin (118, 120, 141);
  [FD-L6] p10 11, p50 72, bands 29 / 48 / 13 %; [FD-L10] skew +0.08, p10 98, sd4 13.0; [FD-L10b] cush_close -0.38 /
  -0.36, seats_aft -0.55 / -0.40; [FD-L11] knee boxes 12 / 14, console face 24.5; [T4] pilot 109 / fd_cabin 76; [T14]
  overhead 41-48, bezels 27-42, walnut 72; [Y1] cover 212, inserts 188 / 161, body 59, pads 73, column 50; [Y1b] spread
  22, body 0.28, pads / body 1.24; [Y1c] lunes / body 1.35; [Y1d] insert / cover 0.94; [Y1e] far 0.85 / near 0.38,
  lower / cover 0.83, band 54), web/package.py verify OK (meshopt 17.67 + 15.21 MB), the Artifact bundle 119.2 MB in 2
  publishes (63.4 + 55.7 MB), artifact_test 70 / 70 (on 140102a's bundle and again on 119a4fa's).  L6 / L6B / L6Y /
  L6Y2 not regenerated (no table changed).
- All-lens fix r1 (2026-10-17; the all-lens judges' round 1 on every lens below the owner's 8: flightdeck 7.9, cabin
  7.4, picture 7.8, exterior 7.8, gear 7.8; FD8-01..05, CAB1-01..06, CRA1-01..06, EXT-A1-01..05, GEAR-A1-01..03). One
  table changed: `wheels.MAIN_AXLE` boss_r (L4W regenerated); no L6 / L6B / L6Y / L6Y2 table changed. Look development
  in one viewer page (out/tmp/all8_fix_r1/ld.py jobs, per part:material median / sd / p10 / p90 from the ID pass;
  xshots.py the judges' exterior cameras on a dev GLB, devbuild.py a one-tier build with the bake).
  GEAR: GEAR-A1-01 the main shock's top was a lateral web ending in mid-air 0.27 m behind the leg --
  `gear.MAIN_SHOCK_LUG`: a swept DRAG LUG (tapered superelliptic section 45 x 32 -> 35 x 25 mm, a slight arch) from the
  leg's axis at WL 0.99 aft and inboard to a fork base box under the shock's upper clevis (`build_main`); GEAR-A1-02 the
  trailing arm a forged swan-neck, not a pipe -- `gear.MAIN_ARM` a (0.044, 0.034) / b (0.024, 0.021) m half-depths (88
  -> 68 mm deep), the bow flattened to ((0.30, 0.010), (0.66, 0.006)), p 2.8, running into a 19 % larger axle boss
  (`wheels.MAIN_AXLE` boss_r 0.058 -> 0.069, a TABLE change: L4W regenerated, `drawing/wheel_sheet.py` ARM depth 0.039);
  fit_check 5 / 10 / 14 (stowed arm, shock and lug in the bay liner) pass. GEAR-A1-03 (the leg door's edge-on lean)
  REFUTED as a finding: it is the documented LD-1 deviation (the blister leans the door's lower part out; the drawn
  2358-2472 lean is the L4 call-out), kept.
  EXTERIOR: EXT-A1-01 (major) the gear-bay liner z-fought the wing's upper skin from above -- mirrored ghost 'lettering'
  at 45 m, sparkle at 90 m: `web/viewer/model.js` gives gear_bays the structure's polygon offset (factor 2, units 8);
  EXT-A1-02 the chin lip a rolled mirror -- `powerplant.CHIN_LIP_NOSE` 0.008 -> 0.018 on the lower lip, 8 mm kept on the
  arms (`CHIN_LIP_NOSE_ARM`, `chin_nose(th)` over CHIN_ARM_TH: there the face's foot stands one nose length ahead of the
  drawn LE line, and 18 mm put the polished face 18-24 mm outside the drawn side crescent -- consistency L4 'chin-inlet
  lip (side view)' 24.6 mm; now front ring 9.0 / side 7.4 mm of 10) -- the drawn lip outlines kept, `inlet_lip`
  roughness 0.12 -> 0.06 (assemble / lookdev / materials.json), the duct entry darker (viewer `inlet_dark` specular 0.3
  / env 0.35, `composite` (0.03, 0.03, 0.034)); EXT-A1-03 the root fillet's nose -- `ROOT_FILLET_ROUND` run 0.40 -> 0.60
  / behind 0.25 -> 0.35, `ROOT_FILLET_TIP_RUNIN` 0.03 -> 0.08 (fewer, broader lobes at e_rootlow; fit_check 16);
  EXT-A1-04 the canoes' crimped aft tips -- `details._canoe_profile` sampled by arc length (rows dense toward the tail
  point), `_weld_poles` merges the converging rows' coincident vertices before `_crease_split`, and aft of the flap's TE
  the top runs under the lower surface's tangent through a soft minimum (`CANOE_TAIL_SOFT` 6 mm); EXT-A1-05 the horn
  balance's exposed cut faces (its inboard cap, the fixed tip's outboard and aft gap faces) in the gap shade
  (`empennage.HORN_GAP_MAT` 'seam'), the droop kept (owner-delegated); the Z-shaped highlight at the horn's inboard
  upper corner (the oblique front-face crease meeting the end rows) is left: a horn front-face re-layout.
  CABIN: CAB1-01 (major, white clay) -- `materials.js CABIN_FORM` (lining class 0, the executive seats' leathers /
  shells class 1): aft of the divider (STA 4.55-4.75 blend) their indirect diffuse x gain x the bake's occlusion^p x the
  bake's window light (mix lo .. hi up to `formC.x`) x a facing term (inboard .. outboard, down .. up) x a height term
  (WL `formC` y / z / w: floor .. belt .. ceiling) -- the halo round each window, the side wall darker toward the sill,
  the soffit steps' shade, lit / shaded bolsters: formA [1.82, 2.2, 0.38, 1.55] / [1.5, 2.0, 0.5, 1.35] (gain, occlusion
  power, x at no / full window light), formB [0.88, 1.05, 0.8, 1.0] / [0.7, 1.2, 0.65, 1.15], formD [0.55, 1, 0.85] /
  [0.6, 1, 1.15] over WL 1.3 / 1.95 / 2.7, full window light 0.3 (`?cabFormA0=` .. `?cabFormC=` override them); look
  development a00 -> d02: at cabin_fwd_406 in the judge's boxes (lining / leather masks) the headliner centre sd 5.9 ->
  11.5, the side wall 9.6 -> 16.5, the seat backs 17.6 (the new welts and seams) -> ~30, their medians ~194-202 (AgX's
  shoulder at the near-white trim compresses the spread, so the factors run wide); [T4b] 201, [T14] lining kept;
  viewer_test [CAB1] at the photo-fitted cabin_fwd_406 (the judge's boxes, the lining / leather masks). CAB1-02 (major,
  exec seat) -- `seats.cabin_seat`: the cushion CROWNED 14 mm over 0.12 m with a rolled front (`EXEC_CUSH` roll 45 /
  roll_b 22 mm), piping welts r 3 mm (`EXEC_WELT`) round the cushion front, the back's front edge and the side panels,
  stitch rows (`EXEC_STITCH`, stitch_thread dashes) beside the V seams, the bolsters' inner edges and the cushion
  panels, a 24 mm leather apron over the legrest top on the forward-facing seats (an 11 mm slab with a 4 mm edge round:
  the 12 mm round inset its outline past itself and folded the end caps, fit_check 23), the bolster gap 6 -> 8 mm;
  consistency_2d3d's exec rows pass (the drawn L6 outlines kept). CAB1-03 the cargo door's ledge segment lit by the
  cabin law: `build.AO_DOOR_CABIN` bakes _AO on its interior-side meshes (ledge_top, ledge_panel, gloss_black,
  chrome_trim, psu_panel, black) and `materials.js` routes a door part's _AO meshes through the interior patch: at
  cargo_lining the door's ledge panel 77 against the fixed segment's 68 and its top 31 (the judge's 114 / 84 against 82
  / 22). CAB1-04 a moulded window BEZEL round every cabin window's lining hole (`interior.WINDOW_BEZEL` profile, 30 mm
  wide, 5 mm proud, rolled into the reveal; `_window_bezel`, part of the reveal: fit_check 20 / 22b clear); the shade
  cassette / pleated shade stays the deferred INT8-07 (an L6 reveal-profile change). CAB1-05 the club-table tops gloss
  black inside the walnut rim (`cabin.TABLE_TOP_MAT`; P1046404-07, the model judging r1 walnut tops superseded). CAB1-06
  the walnut grain fine and straight (viewer veneer_walnut grain scale [420, 420, 8], 3 octaves, amp 0.26, env 0.7; the
  GLB's gloss lacquer coat kept): [T14] walnut 78 at cabin_fwd (<= 90).
  FLIGHT DECK: FD8-01 the fleece's shell silhouettes -- toward the silhouette (|n.v| < 0.25) a soft coverage
  (`pcFurCov`, alpha to coverage on the shells; inside only, alpha written off by colorMask so the canvas stays opaque)
  and the outer shells thinned (`FUR.graze` 0.55), head-on the hard test as before (soft coverage everywhere had lifted
  the shaded gaps -- [FD-L5] 130, [FD-L10] p10 113, [FD-L10b] skew -1.15 -- now 121 / 98 / -0.55, as fix r4). FD8-02 the
  palm tray 15 mm shorter with its top edge kept (`fd_detail_a.STACK` pad half-length 0.0535 -> 0.046, centre 0.2815 ->
  0.274, waist 0.335 -> 0.320, flare 0.385 -> 0.372); the quadrant's trim panel already starts at the quadrant's front
  frame -- raising it means moving L6's PEDESTAL stack foot (3.719, -0.400), an L6 table with the armrest checks
  (fit_check 25): deferred to the drawing review. FD8-03 the grips' satin black -- 'yoke:grip_black' [0, 0.30, 0.22, 1,
  0, 25], PART_TRIM roughness 0.12 with a neutral specular, the pads' specular warmer (1.0, 0.92, 0.84) and their fill
  0.68 -> 0.60 (body / cover 0.28 -> 0.23, pads / body 1.36: [Y1b] 0.22-0.34 / 1.0-1.4). FD8-04 the titanium warmer
  (VIEWER (0.262, 0.236, 0.222)), the tray `tray_titanium` (0.235, 0.208, 0.198), CABIN_TRIM 0.42 -> 0.5, specIn 1.6,
  its edge a crisp 45-deg titanium CHAMFER with a small nose and a thin titanium foot lip (`fd_detail_a.TRAY_EDGE_MAT`;
  was the 4.5 mm dark-bronze bead). FD8-05 the harness a cool charcoal (0.030, 0.031, 0.034), sunIn 0.5, a coarser 700 /
  m weave.
  PICTURE: CRA1-01 the procedural footprints measure the DISPLAYED pixel -- `U.pcSS` (Picture's pass supersampling,
  `_renderSS`) scales every dFdx / dFdy / fwidth of the patches (`GLSL_SS` pcDX / pcDY / pcFW), so the still passes and
  the moving frames band-limit the leather / fleece / pebble / harness / stripes / brush alike (the sunlit sill grain no
  longer pops in after a stop); viewer_test [CRA1-01]: the sill's median 115 still / 115 moving at 480 x 320. CRA1-02
  the yoke's groove flanks on MOVING frames (`U.pcMove`): where a display pixel spans more than the 0.8 mm groove the
  flank's colour fades toward 0.7 cover + 0.3 groove (`VIEWER yoke_groove.gaa`) -- a soft continuous line instead of
  dotted specks; the still keeps its dark line. CRA1-03 phones move at their still dprMax (`scene.js` dprMoveBase =
  dprMax; Auto's _adapt still steps a slow phone down to 1). CRA1-04 inside the tour the temporal AA's motion uses >= 1
  m depth (`TAA_IN_DIST`; the orbit target 0.3 m ahead had scored a 5 cm step as 60 px). CRA1-05 a motion-weighted
  sharpen on the temporal blend (`TAA_SHARP` 0.22 x clamp(motion px / 8), clamped to the neighbourhood; ?taaSharp=).
  CRA1-06 (the light tier barely lighter) DEFERRED: of its 2.37M triangles the exterior and the lining at the judged RES
  1 grids (both tiers' own) carry ~1.4M, the LOW_FINE parts (seats, yokes, pedals, braces, nose leg, flight deck at RES
  2: GEO8-01, the smooth lens) ~0.9M; reaching ~1.6M means phones losing GEO8-01's smoothness or a separately streamed
  interior GLB (loader, bundle, tests) -- its own track.
  Budget: `build.INTERIOR_BUDGET` cabin_seat 12k -> 14k (RES 1; 40,572 / 38,328 at RES 2 against 40.6k -- it also closes
  the old 34,834 / 34,800 open item) and the total 393.5k -> 415k (938,331 of 951,000 built). Build: 2,805,993 triangles
  / 49.63 MB, light tier 2,366,262 / 41.70 MB. Verified: fit_check FIT OK (138 ok, no open row; 23 shells wound outward
  after the apron fix, 26 no coplanar overlaps, 5 / 10 / 14 the stowed tyre 33 mm under the liner roof; sections 1 / 2
  rerun on the final chin lip), consistency_2d3d 157 / 157 (L4 chin lip ring 9.0 / side 7.4 mm), drawing.master L4W,
  drawing.sheet + drawing.verify (the same dimension table), web/tour_data.py --check current, the FULL viewer_test 236
  / 236 (~115 min beside artifact_test and a look-dev page: [T4] cabin_fwd 193 / club 198, [T4b] 201, [T14] lining 197 /
  walnut 78 / ledges 51, [FD-L5] sheepskin (118, 120, 141), [FD-L10] skew +0.20 / p10 98, [FD-L10b] -0.38 / -0.55,
  [FD-L6] p50 72, bands 29 / 48 / 13 %, [Y1b] body 0.23, pads / body 1.36, [CAB1] seat backs sd 29.7 / 29.8, headliner
  11.2, [CRA1-01] sill 115 / 115), web/package.py verify OK (meshopt 18.07 + 15.54 MB), the Artifact bundle 121.6 MB in
  2 publishes (58.5 + 63.1 MB), artifact_test 70 / 70. Before / after sheets (judges' r1 renders | fix r1, and P1046406
  | fix r1): out/tmp/all8_fix_r1/cmp/cmp_*.jpg (gitignored: the cabin one embeds the photo).
- All-lens fix r2 (2026-10-18; the all-lens judges' round 2: flightdeck 7.9, cabin 7.7 (CAB2-01 major); the other lenses
  at or above 8 -- picture 8.1, exterior 8.0, gear 8.0, nav 8.2, smooth 8.0, prop 8.0; sound 7.8 exempt).  Two tables
  changed, L6 / L6B rev O regenerated (`drawing/interior_sheet.py` / `interior_checks.py`; L6 25 texts crossed by lines
  as at rev N): PEDESTAL x / stack (FD9-01) and EXEC_SEAT legrest + legrest_gap (CAB2-01).  Look development in one
  viewer page (out/tmp/all8_fix_r2/ld.py jobs, dev GLBs from devpatch.py -- a base build pickled, groups rebuilt and baked
  against it; ytune.py runs viewer_test's yoke_look_checks on override queries and measures the yoke close-ups).
  FLIGHT DECK: FD9-01 the stack / quadrant proportions -- the trim panel (TRIM INTERRUPT / ALT STAB TRIM / AILERON TRIM)
  had lain on the quadrant plate behind the PCL head, the stack face a long plain slab under the tray.  `interior.PEDESTAL`
  stack's last point (3.719, -0.400) -> (3.735, -0.4264): one straight 35-deg face from the SDU bottom down to the plate,
  x 3.730 -> 3.745 where the face meets it; `fd_detail_a.STACK` pad s 0.274 -> 0.266, waist 0.320 -> 0.312, flare_s
  0.372 -> 0.330; `QUAD trim_s` (0.322, 0.383) / `trim_hw` 0.088: the framed trim panel on the stack face right under the
  tray (was `trim_x` on the plate).  At the photo-fitted panel_408b: the tray y 678-767 of 900 (P1046408 675-769), the
  trim panel row y ~778-840 (P1046408 775-830).  fit_check 25 (armrests vs the pedestal) unchanged in result.
  FD9-02 the yoke grip body -- B - R +24 (slate blue) at the yoke close-up: a warm tint on its probe (`YOKE_PROBE
  grip_black` tint (1.04, 1.0, 0.92)) and specular (PART_TRIM 'yoke_L / _R:grip_black' specularColor (1.0, 0.94, 0.86)),
  the lobe tighter (roughness 0.12 -> 0.10), the side-window term 4 -> 6 (brighter edge glints): at the yoke close-up
  the body p10 / p50 / p90 29 / 65 / 135, B - R +11 (P1046409 38 / 60 / 183).  The fill / dark-cabin cut the judge asked
  for (-25 %) is NOT taken -- measured (out/tmp/all8_fix_r2/yt2-yt5): every darker body (fill 0.24-0.27, probe 0.71-0.80)
  put [Y1b] body / cover at 0.18-0.21, pads / body 1.55-1.73 and [Y1c] lunes / body 1.84-2.07 at the pilot stop (the photo
  bands 0.22-0.34 / 1.0-1.4 / 1.0-1.8); the pads, which the judge measured right (62 against P1046409's 62), fix the
  body's floor at pads / 1.4; the close-up body median already sits at P1046409's 60 (the judge's 96 was a crop of the lit
  arms).  At the stop now body / cover 0.23, pads / body 1.38, lunes / body 1.65.
  FD9-03 the fleece rims at the fd_cabin stop (terraced 'cauliflower' florets): the judge read r1's soft layer edges as
  not reaching the screenshots -- they do (alpha to coverage resolves on the antialiased canvas and every Picture target,
  SwiftShader included), but r1's grazing band (|n.v| < 0.25) was too narrow to show.  `materials.js` furPatch / VIEWER
  sheepskin.fur: the band widened (grazeN 0.25 -> 0.4), the outer layers thinned more there (graze 0.55 -> 0.8), the
  coverage edge widened (grazeW 0.1), and toward the silhouette the layers' root darkening and tilt (grazeFlat 0.6) and
  the sheen's growth up the pile (grazeSheen 0.6, new) flattened: the rims a soft fringe instead of stacked hard florets;
  head-on the hard test as before.  The judge's dithered coverage (an interleaved-gradient threshold per pixel,
  `fur.dither`, kept as an option, off) and a band to |n.v| 0.55 were tried first: they put sparse bright tips into
  [FD-L10]'s cushion band at panel_408b (high-pass skew +1.1 .. +1.65 against the band's +0.7 and P1046408's -0.18; look-
  dev ld3 a0-a2 / u0-u2: the dither alone +0.20 -> +0.55); the chosen set (u1) measures +0.53 there (p10 98, sd4 12.2, sd1
  8.2) and changes 5 % of the fd_cabin stop's lower-left corner by > 20 levels (before / after: ld3 w2).
  FD9-04 / CAB2-03 the walnut: (72, 68, 71) mauve-grey with no figure at cabin_fwd_406, the lavatory (89, 84, 88), the
  arch (72, 68, 70); P1046406's divider (62, 49, 46), P1046411 / 02 (48, 36, 36) / (48, 38, 37) warm dark brown.  VIEWER
  veneer_walnut base (0.094, 0.055, 0.042), the grain 150 / m across (6.7 mm streaks, 3 octaves to 600 / m) at +-35 %
  (survives the pcSS band limit at 1-3 m), a CABIN_FORM class of its own (2: everywhere inside, the divider included --
  x 0.80 .. 1.10 with the bake's window light, x 0.8 facing the aisle: the lavatory's bi-fold doors); the bake splits the
  walnut's long edges to 0.15 m (`build.AO_WALNUT_SPLIT`, 2 levels, `ao.presplit(only=)`: +5.9k triangles; 50 mm had cost
  66k) and filters both channels over 0.12 m of like-facing walnut (`AO_WALNUT_DENOISE`: the cloudy blotches).  At
  cabin_fwd_406 the divider (59, 46, 45), the lavatory close-up (64, 49, 45), the arch (57, 42, 38) -- warm, R - B
  +14..+19; the arch's grain runs vertically (along the panel, not fanned).  A satin grille plate with three slats high on the RH divider wall's aft face, 0.1 m outboard of its aisle edge (`fd_detail_b.DIV grille`;
  P1046406 -- the LH wall has a placard there).
  CABIN: CAB2-01 (major) the executive seat -- `seats.cabin_seat`: the back's panels meet in 2.5 mm creases (EXEC_SEAM:
  top radii 6-10, the panels sunk into the slab so their edges stand 2-6 mm proud; r1's 8 mm gaps between r 12 rounds
  read as grey channels), the side bolsters run on up to the top as SHOULDER WINGS (EXEC_WING: 46 mm wide above the V's
  end, crowned 10 mm prouder over the upper back), the centre and lumbar panels crowned (a lumbar bulge), the stitching a
  tone-on-tone `stitch_light` (0.8 x the leather; assemble / lookdev; CABIN_FORM class 1; the viewer 0.95 x: at the club
  stop's 2-3 m the sub-pixel dashes had read as grey dots 30-50 levels under the leather) -- and the dashes are OPEN
  SHEETS: `Geo(sheet=True)` keeps their winding (Geo.meshes' signed-volume flip had turned ~2/3 of them inward, and the
  bake traced their light into the seat: black 'cut here' dots), re-wound under a mirroring map; the headrest a separate
  plump pillow (EXEC_HEAD: edges r 36 / 40, crown 12 mm, a horizontal welt seam a third down) in place of the inset panel;
  the forward-facing seats' legrest set back 28 mm (EXEC_SEAT legrest[2] 20 -> 28) with its top `legrest_gap` 16 mm under
  the drawn cushion underside and a dark strip in the crease (EXEC_GAP), the cushion's rolled bottom (roll_b 22 -> 30)
  overhanging it -- r1's apron is gone; the cushion side panels' joint a crease (r_side 18).  consistency_2d3d's exec rows
  pass (headrest top 9.4 mm of 10 at r 42 -> r 36).  viewer_test [CAB1] now also reads the seat backs' LOW-PASS sd (6 px
  gaussian, >= 7: the form shading) and their high-pass sd (<= 12: the lines; photo 5.2 / 5.5, r1 14.5), the raw floor 20
  -> 9 (P1046406 8.8 / 11.9): the seat backs p50 201 / 199, sd 14.9 / 16.2, low-pass 10.6 / 12.6, high-pass 6.9 /
  7.6 (r1: sd ~30 of which high-pass 14.5).
  CAB2-02 the door linings: `build.AO_DOOR_CABIN` += 'lining' on door_cargo, door_airstair, door_frames (baked with the
  interior in the closed pose, both ways round -- `ao.bake` / `ao.sky` on the flipped normals, the larger kept: the cargo
  door window's reveal walls are wound into the panel -- and filtered over 0.08 m, AO_DOOR_DENOISE); the viewer's door
  parts with _AO take the interior law / CABIN_FORM (CAB1-03's route).  The cargo door's window gets the fixed windows'
  rolled bezel (`fuselage_parts.build_door` -> `interior._window_bezel` on the inner panel's hole loop).  At cargo_lining
  the door's lining 175 against the fixed wall's 178 (was 214, sd 0); the airstair door's cabin face is its stair --
  treads, risers and the recesses between them -- and reads 115 (risers ~150, the recesses under the treads darker)
  against the wall's 182 at door_closed: shaded by its own treads now, not a flat 214.
  CAB2-04 the club-table piano tops: a CABIN MIRROR (`materials.js mirrorGLSL`, PART_TRIM 'table_club_*:gloss_black'
  mirror k [ledge 0.08, wall 0.45, window 12.0, headliner 1.8, carpet 0.05], tint 0.3, blur 0.25): inside, the
  reflection ray is traced against a box cabin -- the ledge fascia (BL 0.655 below WL 1.869), the side-wall lining (BL
  0.69) with the cabin windows cut into it (fuselage_parts.FIXED_WINDOWS / DOOR_WINDOWS: Lame 0.300 x 0.385, n 4.2,
  centre WL 2.1875), the headliner (WL 2.66), the carpet -- each a multiple of the studio's blurred overhead radiance
  taken as a neutral grey (tint: 0.3 of its colour -- the sky's blue read as slate), the window outlines softened by the
  roughness over the ray length (x blur); unscaled by the cabin law's reflection weights (fill [0, 1, 1]), roughness
  0.06.  A uniform 'win' radiance had greyed the whole top to 155-185; the wall at 1.0 mirrored brighter than the wall
  itself (p405 93 / 107 / 182 / 206).  Table pixels p10 / p50 / p90 / p99: p405 61 / 71 / 193 / 218, tables_dep
  18 / 39 / 49 / 185 (look-dev ld3 x1 / w1; P1046404 / 05 / 07 38-45 / 63-106 /
  116-124 / 220-234; judges' r2 7 / 12 / 49 / 113), the windows mirrored in the outboard leaf.
  Budget: interior 944,996 of 951,000 (cabin_interior 37,148 with the walnut split, seat_pax1 / 2 39,488, pax3-6 40,212
  of 40.6k).  Build: 2,814,991 triangles / 49.91 MB, light tier 2,374,604 / 41.96 MB.  Verified: fit_check FIT OK (138 ok, no open row; 25 the armrests vs the pedestal unchanged in result; 26 builds its pairs in 20k-triangle slabs -- the same pairs, 40k ran out of memory beside a viewer run), consistency_2d3d 157 / 157 (the exec headrest top 9.4 mm of 10), drawing.master L6 / L6B rev O (L6 25 texts crossed by lines as at rev N), drawing.sheet + drawing.verify (SVGs unchanged, the same dimension table); the FULL viewer_test after a container restart at load 8-25 (two other worktrees' browsers beside it) through a harness wrapper with longer waits (SHOT_TIMEOUT 900 s, navigations 300 s: a plain run's prop-blur screenshot timed out at 240 s; no check changed) 235 / 236 -- the one failure [FD-L9] at its 300 s wait: Auto's start-up calibration had given SwiftShader the 16-pass still refinement this time, whose passes alone took ~350 s; re-measured with the refinement forced on (?quality=high) the page idled at 44 Hz after 367 s with no render requested once the passes were done, so the row's wait is now 600 s (viewer_test comment), `--only fdlook` 14 / 14 with it ([FD-L9] idle after 68 s at 37 Hz; Auto gave no refinement there); in the full run [CAB1] the seat backs p50 201 / 199, sd 14.9 / 16.2, low-pass 10.6 / 12.6, high-pass 6.9 / 7.7, the headliner centre sd 11.4; [T4] cabin_fwd 190 / club 198 / fd_cabin 77, [T4b] 202; [T14] the walnut 40 at cabin_fwd (<= 90), overhead 41-48, bezels 27-42; [FD-L2] carpet 15 / consoles 7 / titanium 88; [FD-L3] glareshield 60 (lip 72 / underside 44); [FD-L4] yoke 212; [FD-L5] sheepskin (118, 120, 140); [FD-L6] p10 11, p50 71, bands 29 / 48 / 13 %; [FD-L10] hp4 skew +0.37, p10 98, sd4 12.3; [FD-L10b] cush_close -0.37 / -0.32, seats_aft -0.55 / -0.37; [FD-L11] knee boxes 12 / 15, console face 24.5; [Y1b] spread 22, body 0.23, pads / body 1.38; [Y1c] lunes / body 1.65; [Y1d] insert / cover 0.94; [Y1e] far 0.85 / near 0.38, band 55; [CRA1-01] sill 115 / 115.  web/package.py verify OK (meshopt 18.15 + 15.62 MB), the Artifact bundle 122.2 MB in 2 publishes (58.8 + 63.4 MB), artifact_test 70 / 70 (the bundle's viewer files are the committed ones; no viewer or GLB file changed after it).  Before / after sheets (judges' r2 renders | fix r2, P1046404 / 05 / 08): out/tmp/all8_fix_r2/cmp/cmp_*.jpg, cmp2/cmp_*.jpg (gitignored: they embed the photos).
- All-lens fix r3 = cabin track (2026-10-24; track 1 of the three parallel sessions after the migration, branch
  claude/pc12-cabin-r3 from e3d0a17; cabin 7.8 shipped with major CAB3-01 "the executive seats read as flat panels on a
  boxy base").  No L6 / L6B table changed (builder detail and the viewer; the runner table ended as shipped).  Judges
  4 rounds: 7.6 (r1: separately puffed panels read as tiles) -> 7.0 (r2: over-flattened, a board with drawn outlines;
  the runner as planks) -> lead's method from then on: every candidate A/B-judged against the shipped baseline
  (e3d0a17 rendered from its own worktree, same cameras) beside the photos, judges given the baseline renders and the
  previous findings -> 7.9 -> 8.0 PASS (no blocker / major).  EXEC SEAT (`seats.cabin_seat`): the back's panels all
  lifted by ONE shell crown (`EXEC_SHELL` h 12 mm at the centreline, the bolsters' rise 18 mm + 10 over the shoulders
  over e 0.40-0.85 of the half-width) -- continuous form across every seam, the seams narrow dips where the panels'
  small edge rounds overlap (`EXEC_SEAM` gap -3 mm, radii 5-8 mm); the centre panel narrows as a U (`EXEC_V_EASE` 1.7);
  the lumbar its own panel on the same shell and sink (a crease, not a step); the panels' foot at 15 mm (the slab's
  front had shown as a black slot); the headrest winged (`EXEC_HEAD` wing 16 mm over its outer quarters), corners r 75,
  two full-height vertical seams tapering in (the horizontal welt gone); the cushion crowned 22 mm over 140 mm with a 55
  mm front roll, its side panels 12 mm under the drawn top and ending 60 mm short of the front (they had framed it as a
  tray / bulbous corner blocks), no front welt; the forward-facing seats' base box mid grey `seat_shell_grey` (the aft
  pair keep the anthracite), a framed life-vest drawer on every base (`EXEC_DRAWER`), light-grey lap belts
  `belt_grey`.  VIEWER (`materials.js`): CABIN_FORM class 3 for the seats' dark trim (`seat_shell_dark` /
  `seat_shell_grey`: gain 1.3, occlusion power 0.8 -- under the leather's power 2 and floor-level x 0.55 the bases were
  a black void, sRGB ~10 against the backs' 200 at cabin_fwd_406; now ~0.2 of the backs, P1046406 0.23); the leather a
  satin 0.62, warmer, x 0.93; the walnut's grain in a frame along the vertical / station with fine dark pore lines
  (`grain.lines` [380 / m, 0.30, 0.30, 3.5]: the r2 figure was isotropic 6.7 mm blobs on the divider -- smeared); the
  runner bands carry the field's pinstripe (lookdev `stripes` on carpet_orange / light / grey) and a cut pile (the
  `leather` patch, 280 / m, +-15 %), the light bands near-white, the field nearer black with a stronger pinstripe; the
  cabin sun on the leather / carpet x 0.2 (`sunIn`: through the deep reveals the low sun from ahead landed as thin white
  blades).  LINING DOORS (`cabin._flush_door`): the O2 / access / PULL doors' gap 2.5 -> 1.5 mm in a mid-grey
  `lining_gap` (the dark psu_panel ring drew heavy black outlines).  CARGO-DOOR WINDOW: its bezel (`interior._window_bezel`
  depth / into) runs down the whole reveal as a slight funnel, its far edge 8 mm into the opening -- the inner panel's
  hole wall and the door slab's lay within 0.5 mm of the old 4 mm strip and tied in a dotted dark hairline (ray-cast:
  two lining surfaces 0.1 mm apart along the line; not the glass).  `ledge_panel` neutral grey.  Open (reported, not
  done): the window shade cassettes (INT8-07, an L6 reveal-profile change), the PSU pods / O2 doors a little small, the
  runner bands' crisp edges, the ledge-top lids.  Note: a fresh container has no out/tmp/yoke_mesh_cache -- the first
  build re-meshes the yokes (~24 min) to 43,008 triangles each (42,868 committed before), printed OVER the 43k cap
  (track 3 raises the cap; the lead reconciles at the merge).  Tools (scratch, not committed): a look-dev pose harness
  over viewer_test's helpers, a baseline worktree of e3d0a17 rendered with its own viewer.
  Final sweep (fresh judges on the final state): cabin 8.0, exterior 8.0, gear 8.1, smooth 8.0, nav 8.2, prop 8.0, picture
  8.2, sound 7.9 (exempt) -- no blocker, no major.  Open minors they list: the leather a little white / a glassy cushion
  highlight, the chin-lip corner serration, the horn-balance S highlight, a comb highlight at the dorsal fin root, the
  disc unchanged with rpm and no blurred-prop shadow, the desktop airstair stop's framing and the blurred apron under
  it, TAA on the glazing at faster orbits, the phone's 1.5 moving DPR cap, the sound's fast start / quiet flight deck
  (track 2's engine model).  Verified (both tiers, e880898 + viewer tweaks, then merged with main a35d869): fit_check
  FIT OK (138 ok), consistency_2d3d 157 / 157, drawing.sheet + verify OK, web/package.py verify OK (meshopt 18.08 +
  15.55 MB), the full viewer_test 234 / 236 before the merge (the two rows timing races of the harness: [sound] M
  mutes now polls for the suspend, [PQ] Auto reads the latest refinement decision -- no criterion changed; --only sound
  25 / 25, the PQ row 7 / 7 on its own page) and 250 / 251 after it ([PQ] no GL errors: gl.getError() 1282 after the
  main run's context-loss section, as track 2's own full run; 0 on a fresh page), the Artifact bundle verify OK,
  artifact_test 70 / 70 before and 76 / 76 after the merge.
- Live G3000 PRIME displays + Environment knobs (track 2, branch claude/pc12-live-avionics; owner 2026-10-18 "the actual
  characteristics, not screenshots ... if I turn on props, you can see gauges moving", "some control knob ... to tweak the
  environment"; owner 2026-10-24: the labels ON by default).  Viewer only, no GLB change (the GLB's static atlas stays the
  fallback: ?avx=0, other glTF viewers, an error).  `web/viewer/avionics.js`: one CanvasTexture `g3000_live` replaces the
  'display_page' emissive map before the materials are cloned; each page (pfd_L / pfd_R / mfd / sdu_L / sdu_R at their
  GLB meta 'displays' rectangles) is drawn into its own canvas when its quantised view key changes (avx_pages.js view*),
  at most 20 Hz (phones 10; 2 Hz under 120 px on screen, none under 24 px / off screen), and uploaded alone
  (copyTextureToTexture, mips once per batch); parked and still nothing is drawn, uploaded or rendered ([AVX-14]).  While
  pages change the glass joins Stage.overlay (picture.js: the still without it, the glass composed over it), sampled with
  a texture LOD bias of -log2(the still's scale), capped at -0.5 (materials.js U.avxBias, ?avxbias=) so the pages keep the still's
  sharpness; the glass stays in the overlay for as long as the spinning propeller's disc is there (a still under the disc
  is not re-rendered for a page change).  `verify()` reads
  the GPU's copy (level 0 and 1) back against the canvases ([AVX-13]).  `avx_pages.js` the pages (PFD with SVT, HSI,
  tapes, CAS; MFD with the engine strip, map, VSD; SDU flight plan / take-off data), `avx_font.js` stroke numerals and
  LEGENDS (labels as a condensed system sans squeezed to 1.9 x the stroke layout's room; ?avxlabels=0 abstract strokes;
  no brand words -- 'SafeTaxi' became 'Airport'; a plausible EDNY RW24 departure with invented fixes).  `engine.js` ONE
  engine model (the sound reads it too, kin.gg === kin.eng): PT6E-67XP + Hartzell laws inside the POH limits (ground
  idle 64.5 % Ng / >= 1,000 rpm, T/O flat 44.3 psi to the 850 C ITT limit, reverse governed 1,615 rpm), fix r1 (pilot
  judges r1 7.4 -> r2 7.6 -> r3 8.0): the start at a PT6's pace (`START`: 13 % Ng in ~4.6 s, light-off 2 s after the fuel
  ~6.6 s at ~15 %, 1.4 .. 3.6 %/s, ground idle ~28 s, the propeller turning with the power turbine from the light-off),
  the run-down ~32 s (Ng) / ~20-25 s (propeller); running, the torque meter reads the turbine's torque at the CURRENT Ng
  (rises with Ng, idle -> T/O ~4 s; `NG_RATE` 8 / 7 %/s); feather selected with the engine running (pitch >=
  `FEATHER_SEL` 55) = Ng to ground idle and the propeller on its power balance (`J_PROP` 26 kg m^2; the static Cp stays
  high past the stall to feather) down to ~600 rpm, no torque spike; a pitch the rating cannot turn droops the propeller
  at the rating; ITT amber above 820 C, the unlit ITT follows the cooling hot section; QTY amber with fuel low;
  upper-case CAS strings (FUEL LOW, TAKEOFF CONFIG -- only with power set for take-off --, STARTER, GPU).  `env.js` the
  ISA day of the Animate tab's Environment panel (OAT, elevation, QNH inHg / hPa, wind, fuel, ground power; localStorage
  'pc12.viewer.env', ?oat= ?elev= ?qnh= ?wind= ?fuel= ?gpu=) through first principles to the engine and the air data;
  a T/O button sets the day's rating.  Tests: node test/avx_model_test.mjs (34), viewer_test --only avx [AVX-1]-[AVX-16],
  artifact_test's live-pages row per scenario; the sound / prop-spool rows retimed to the slower start (SOUND_SCRIPT:
  1,700 at 34 s, 100 s render).  Decisions (owner-delegated): the amber readouts stay reverse video (G1000 / G3000
  practice); the TRQ green arc to 40.63 kept (the recovered table); the cold-day idle Np above 1,000 kept (the power
  balance); no generator-off CAS with the engine stopped (P1046410 shows the parked pages without them).  Verified (1ce7fa0): avx_model_test 34 / 34;
  the FULL viewer_test 249 / 251 (88 min) with two [PQ] rows of the picture section (Auto's calibration under load, one
  gl.getError() 1282) -> `--only picture` 15 / 15 on a rerun; `--only avx` 16 / 16, `--only sound` 25 / 25, `--only prop`
  28 / 28 (the prop pixel rows had projected their ring through a stale camera matrix: projected after a frame now);
  web/package.py verify OK (meshopt 18.15 + 15.62 MB); the Artifact bundle in 2 publishes; artifact_test (76 rows: + the
  live pages under the CSP per scenario).  Judges r3: pilot 8.0, picture 8.0 (no blocker / major).  Open (minors): the
  close-ups a little washed out by the cover glass' reflection, a mip regeneration per upload batch at liveScale 2, the
  phone tier soft in close-up (scale 1), CAS wording / generator amps per the real NGX unknown.
  Follow-up (2026-10-25, the lead's 7 console warnings 'WebGL: INVALID_OPERATION: texSubImage2D / generateMipmap: no
  texture bound to target'): three r160's state.bindTexture skips gl.activeTexture when its cache already has the atlas on
  unit 0, so copyTextureToTexture acted on whichever unit the last draw left active -- `Avionics._upload` makes unit 0
  active before each copy, and a texture three has not created yet / with a full upload pending is uploaded whole
  (initTexture; generateMipmaps is part of three's GPU texture key, so it is not toggled during that upload).  viewer_test
  [AVX-16] sets up the stale-unit state, uploads, and checks gl.getError() and the WebGL console (the old code: 1282 and
  the lead's warnings), [AVX-16b] the same over the rest of the section ([AVX-14]'s frames, the screenshots' uploads
  right after real draws; the lead's review: the row had read the console before them; --only avx 18 / 18 with it).  Verified: --only avx 17 / 17, --only sound 25 / 25, --only picture 15 / 15,
  avx_model_test 34 / 34, web/package.py verify OK, the Artifact bundle verify OK, artifact_test 76 / 76.
- First-principles flight deck (track 3, 2026-10-24/25; owner 2026-10-18 "construct in first principles", 2026-10-19 "Show
  me some printed legends!"; branch claude/pc12-fd-first-principles).  A1: `model/fd_detail_a.py` split by area into
  `fd_kit` (frames, sections, knobs, `flush_screw`), `fd_footwell`, `fd_panel`, `fd_pedestal` (fd_detail_a re-exports
  them; test/fd_identity.py: 173 flight-deck meshes byte-identical).  A3 PRINTED LEGENDS: `model/fd_print.py` -- one
  RGBA atlas (4096^2, half size on the light tier; shelf-packed online, cells deduplicated) drawn from stroke fonts:
  real generic English placard text (owner 2026-10-24 "Real English words": switch / breaker / scale / limitation
  labels, VOCAB / CB_VOCAB for prints without their own `text`; no brands -- the first invented glyph set "read
  Russian"), group frames with titles, tick scales, dimmer arcs, dots, chevrons, stitch strips, two-ink placards; the
  decals (material `legend_print`, alpha-blended, assemble.TEXTURES / ALPHA; viewer CABIN_TRIM [0, 1.15]) lie 0.15 mm
  over planar faces, 0.25 mm over curved maps (`decal_map`), stuck-on placards 0.4 mm -- they replace every floating
  light_white strip on the panel, GFC 700 (keys / knobs), eyebrow, rocker caps, quadrant, trim panel, stack, CB panels
  (a label per breaker), overhead (one printed plate), sills, ledge / limitations placards, pull paddles, footwell.
  A2 csk flush screws on the plates.  A4 / A6 tables (interior.py, sheet L6C rev A "FLIGHT DECK CONSTRUCTION & FINISH",
  drawing/fd_construction_sheet.py): FD_CONSTRUCTION (construction / finish / edges / printing / materials per part),
  CREW_SEAT sheepskin_hide 4 + sheepskin_pile 30 (= sheepskin_t), PEDESTAL rim (14 x 6, R 20 corners, top rolled R 3:
  the quadrant frame's cast section) and blend (R 12 front edges, R 8 fillets at the stack profile's kinks); L6 / L6B
  unchanged.  A5 test/fit_fd_p.py (run by fit_check): 34 prints on their surfaces (<= 0.8 mm), 35 knife-edge ratchet
  (188 m of mid-air open edges in the flight deck's own meshes), 36 every flight-deck material in FD_CONSTRUCTION.
  Part B (judge-driven, 4 rounds of a fresh flight-deck lens judge + a realism A/B judge at 15 views -- the crew /
  cabin stops, Cockpit, panel_408b, 10 close-ups; test/fd_cap.py, dev GLBs by test/fd_dev.py): the quadrant plate
  charcoal (a neutral base reads navy under the cool shade light: the warm base kept), the stack a mid mauve satin
  metal, the flap lever a flat 30 x 28 x 12 paddle with FLAP printed, the overhead bezel 12 -> 9 mm and outlets x0.8
  with louvred rims, the windshield bus bars 4 mm inside the moulding (9 mm read as a wire in the glass), the crew
  backs' rear seams tone-on-tone, PCL metallic pewter, the eyebrow fascia lighter, the carpet neutral, the titanium's
  brush stronger; FLEECE (viewer, as shipped): 8 mm pile, 20 shell layers (8 on phones), 550 / 380 per m octaves, root
  and lowest layers 0.40 (ao [0.40, 1.13, 1.8]), the clumps' lit / shaded relief (28 / 65 per m, 5 / 1.8 mm), lumps
  +-10 %, partings 0.2 / 0.15, base (0.225, 0.188, 0.205), CABIN_TRIM 0.58 (a 160 / m curl octave read as foam, a soft
  head-on coverage edge -- furPatch q.soft, kept as an option -- as felt: both off; taller / lighter piles failed
  [FD-L10b]'s close-range skew); also 'fd_consoles:lining_flightdeck' fill 0.23 ([FD-L11]), leather_crew_shell [0, 0.8]
  ([T4] fd_cabin).  Scores: the flight-deck lens 7.4 /
  7.6 / 7.4 / 7.4 (rounds 1-4: NOT at 8 -- open majors: the fleece's close-range texture, P1046409's curly locks vs a
  fine plush pile, and the footwell reading empty against P1046408's lit linkage, which [FD-L11]'s near-black knee
  areas hold down); the realism A/B judge preferred the rebuild in every round (70 / 85 / 85 / 90 %, round 4: 11 views
  B, 4 ties, none A).  T-LIGHT: `?fp=1` (materials.js FP_LIGHT) lights the interior by the cabin law alone, no per-part
  / per-material hand trims; at panel_408b it lifted the footwell (8 -> 12), dimmed the yoke cover and flattened the
  hood against P1046408: not shipped (the lead's rule: only if it wins the A/B).  build.YOKE_BUDGET 43k -> 43.2k (the
  lost yoke mesh cache re-meshed here gives 43,008 triangles a yoke against 42,868).  Interior photos re-fetched:
  P1046401-11 (Commons thumbnails, thumb.wikimedia.org: upload.wikimedia.org refused scripted fetches); the AOPA and
  Pilatus overhead / throttle photos were not found.
  Merged claude/pc12-modeling-migration-jcghrf at 676e0f4 (the live avionics: main.js keeps it with 20 fur layers;
  materials.js CABIN_TRIM leather 0.93 from main + leather_crew_shell).  Both tiers rebuilt on the merge (01218cb):
  2,803,875 triangles / 50.23 MB, light tier 2,363,498 / 42.07 MB, interior 933,880 of 951,400 (flight_deck 218,444).
  Verified on that build: fit_check FIT OK (no open row; fit_fd_p 34-36 incl. 35 knife edges 187.3 of 188 m),
  consistency_2d3d 157 / 157, yoke_mesh_check OK, drawing.master (L1 / L3 / L5 SVGs differ from main's committed ones by
  main's own fuselage edits, the rest PDF timestamps: left alone), the FULL viewer_test 253 / 253 (fdlook [FD-L10]
  skew +0.55 / p10 101, [FD-L10b] cush_close -0.38 / -0.30, seats_aft -0.55 / -0.32, [FD-L11] knee boxes 12 / 14,
  console face 22.8), web/package.py verify OK (meshopt 18.64 + 15.91 MB), artifact_test 76 / 76.  Final captures:
  out/tmp/fp/final (judges' verdicts out/tmp/fp/judge/final_*.md).
  OWNER DECISION (2026-10-24, relayed by the lead): "For the Deck, let's aim for 8.5" -- this track is done at a
  flight-deck lens >= 8.5 with no blocker / major and the realism A/B still preferring the rebuild; the baseline is
  merged main (two fresh judges on 82f1462 scored its flight deck 8.0, no major).
  Final judge round on 01218cb: lens 7.5 with 3 majors (the fleece's texture and silhouette, the footwell empty), A/B
  88 % for the rebuild.  Then (713a65b, the lead's rule: keep a look change only where an A/B against the shipped look
  prefers it) the crew fleece went BACK to main's shipped one (materials.js sheepskin / fur, 14 layers; furPatch's
  q.soft kept as an off option) -- none of the track's fleece candidates had won; each CB panel names a breaker once
  (`fd_print.cb_names`); the overhead's captions and position words are placed clear of the switches, the levers' throws,
  the squares, the titles and each other (`fd_detail_b._ovh_captions`: four position words that fit nowhere are left
  out); the PCL a darker satin pewter (FPF-04); the footwell's foil blanket more of the fill ('flight_deck:panel_silver'
  0.55 / specIn 0.7).  Re-judged on a dev build of it: lens 8.2, NO major (the fleece / footwell / PCL re-graded minor
  as the shipped look), A/B 87 % (11 B, 4 ties, 0 A).  The lead's gate (2026-10-25): an interim merge into main at that
  state; this track continues to 8.5 on top of main.  Open for 8.5 (judge FPG-01..08): the fleece shader (curly
  locks, soft rims), the footwell's foil / linkage, the PCL, CB names unique across the paired blocks, the yoke grips
  grey at distance, the crew seat backs featureless from the cabin, the stack flank's shading.
  Verified on 61c6b1e (both tiers rebuilt on 713a65b: 2,803,875 / 2,363,498 triangles): fit_check FIT OK (no open row),
  consistency_2d3d 157 / 157, yoke_mesh_check OK, the FULL viewer_test 253 / 253.
  Merged into main at 2f33f8e (the lead, 2026-10-25).  Toward 8.5 on top of it (A/B-gated against 2f33f8e, one lens + one
  A/B judge a round): candidate 1 (8dc6578) -- each breaker named once on its console (CB_VOCAB 70 -> 112 names,
  `fd_print.cb_names` over both blocks), the PCL paddle's ends sharper (PCL_PADDLE e_end 0.38 -> 0.30), the fleece's pile
  cells stretched / warped along the flow (oct vertical stretch 1.3 -> 2.6, warp 0.5 / 0.6), a warmer base (0.255,
  0.205, 0.205), the outer layers thinned fully at the silhouette (graze 1.0): lens 8.3 (no major), A/B 67 % (5 B, 10
  ties, 0 A); a lighter-gap variant failed [FD-L10] (skew +0.85) and was not kept.  Candidate 2 (c392d30, 5fd7515) -- the
  footwell fill 0.8 -> 1.6 on the pedals / linkage / foil only (FOOT_SKIP += carpet_flightdeck: carpet 23 -> 6, and the
  pedestal metals tray_titanium / stack_gunmetal / pedestal_gunmetal: the tray had brightened 127 -> 142), four
  implausible breaker names replaced: lens 8.3 (no major), A/B 70 % (6 B, 9 ties, 0 A).  NOT at 8.5: the judges' one
  remaining lever is the fleece -- up close the shell fur's pile cells read as sponge / coral holes and its silhouettes
  as stacked florets (FPI-01 / 02); capping the partings (`partCap`) or gating them to the upper pile (`partH`, both kept
  in furPatch, off) changed nothing measurable: the holes are the pile field's own cells, so the cure is a new field (a
  lock-strand shell), its own piece of work.  Then the footwell's linkage / foil (still near-black at the judges'
  cameras), the PCL's satin band, the yoke grips grey at distance.
  Verified on 5fd7515 (both tiers rebuilt: 2,803,875 / 2,363,498 triangles): fit_check FIT OK (no open row),
  consistency_2d3d 157 / 157, yoke_mesh_check OK, the FULL viewer_test 253 / 253, web/package.py verify OK, the Artifact
  bundle verify OK, artifact_test 76 / 76.
  Merged into main at ee751b7 (the lead, 2026-10-25: second interim).  The fur-field rework below is NOT started: the
  lead put it to the owner (now / after the usage reset / accept 8.3).
  DESIGN NOTE -- a lock-strand fur field for the crew fleece (the last lever to 8.5 per both judges, ~+0.2):
  * Problem: the shell fur's coverage field is isotropic value noise above a rising threshold, so its cut contours are
    round cells -- up close a sponge / coral of dark holes, edge-on stacked florets.  Tuning (gap tone, partings, caps,
    stretch, soft coverage) only reshaped or felted the same cells (seven rounds in the old thread, three here).
  * Approach: replace the coverage field with LOCKS -- a jittered 2-D cell lattice in the surface's (flow, cross) frame
    (flow = down the vertical faces / forward over the tops, as today's stretch axis), each cell carrying one lock: a
    curved strand bundle 15-25 mm long, 3-6 mm wide, its centreline a short arc that rises with the layer height
    (t) and curls at the tip (rotation ~ t^2); coverage = the distance to the nearest few lock centrelines below a width
    that tapers to the tip, max over the neighbours (the top lock wins); the dark lives only BETWEEN locks and on each
    lock's shaded flank (its own normal from the centreline frame), never as round holes; fine fibre streaks along the
    strand; at grazing |n.v| < 0.4 the outer layers taper to the lock tips (a fringe of tips, not contour terraces).
    Same shell machinery (furPatch / addFur, one instanced draw, 14 / 8 layers), a new `q.locks` mode beside `oct`.
  * Lab first: the seats-only page (subset GLB + materials.js under a room light, ~30 s a try; the old
    out/tmp/fd_fix_r5/lab tooling) to get the lock shape right on P1046409 / 10 crops, plus tools/furprev.py's numpy
    preview of the coverage field -- no full-viewer captures until the lab reads as locks.
  * Gate: [FD-L5] tone, [FD-L10] / [FD-L10b] structure rows (P1046408 / 09 / 10) must pass, then ONE A/B judge against
    main at the 6 fleece-bearing views (fd_cabin, pedestal, quadrant, cb_left, seats_aft, footwell_l) and one lens judge
    on all 15; ship only if the A/B prefers it, else keep main's fleece.
  * Expected: 2-3 lab iterations, 1-2 viewer rounds (fdlook + 2 judges each), then the usual rebuild / full verification
    (no GLB change unless the seats' rim geometry is touched).
