# PC-12 PRO parametric model — project notes for Claude Code

A from-scratch parametric CAD model of the **Pilatus PC-12 PRO** (NGX airframe), built in a sandbox
where no CAD packages (CadQuery/OCC/Blender) could be installed. Everything is plain Python + numpy:
a small surface-lofting kernel ("loftkit"), component builders, a glTF exporter, and a hidden-line
engineering-drawing generator. Output: `out/pc12.glb` (97 parts, ~2.11M tris of which the interior ~527k, ~35 MB
incl. the 0.5 MB G3000 page atlas, 16-bit normals; built at the tessellation quality `PC12_RES` = 2, `cad/res.py`;
hinge pivots in node extras), its light tier `out/pc12_low.glb` (the builders' own grids, `PC12_RES=1`, as judged in
review: ~1.53M tris, interior ~237k, three wheels ~77k, ~26 MB, 16-bit normals too; phones and the no-WebAssembly
fallback load it, the Specs panel offers the full model there), `out/pc12_meta.json` (build steps, BOM, construction lines, dimension checks; `stats.low` = the light tier),
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
python3 test/viewer_test.py     # viewer checks + screenshots (headless Chromium / SwiftShader, ~30 min, 145 checks; slower on a
                                #   loaded machine -- rerun once on a screenshot timeout); [T1]-[T11] the interior tour
python3 web/package.py          # static viewer bundle -> dist/ (gitignored): meshopt GLBs (both tiers; the build's own
                                #   quantisation kept: gltf-transform's API, reorder + EXT_meshopt_compression), vendored
                                #   three.js, verify step
python3 web/package_artifact.py --out DIR && python3 test/artifact_test.py --dir DIR   # the claude.ai Artifact bundle
                                #   (~57 MB: meshopt 14 + 10 MB, gzip of the light tier 15 MB, as base64 text parts)
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
  (not inside `res.coarse()`: the hidden engine modules, mount and firewall keep their own grids and are not refined),
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
  RES 2: 550k / 47.6k / 34.8k, built 527k / 45.6k / 34.8k) and printed by the build; the viewer's cockpit camera is `pc12_meta.json` 'cockpit' = `build.cockpit_camera()` at the L6 design
  eye),
  `details.py` (wing-to-body fairing: flat-bottomed belly fairing + upper root fillet / fairing nose built as a
  horizontal offset of the OML, so its side / plan outlines are the drawn ones -- the nose section is the concave
  fillet with a round-over crest (`ROOT_FILLET_ROUND`) running into the wing LE, the fillet law starts from the visible
  foot on the wing (`_visible_foot`), fit_check 16 guards its creases; flap-track canoes split at the cove lip
  into a fixed forward part and an aft part carried by the flap; cowl panel lines / latches / vent / oil-cooler exit
  (`COWL_SEAMS`, photo 188); lights, antennas, pod with its straight tapering tail under the winglet),
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
- Owner decisions: quality bar 7.5 for the visual reviews (owner 2026-09-26; the Stage-4 exterior VQA rounds 1-3 were
  judged 8 / 8 / 7.5); the drawn fairing tail lobe aft of the cargo-door seam is left un-modelled; no cargo-door gas
  struts; the main-gear leg door's pointed tip is rounded (see LD-1 below); markings: none (below).
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
  stand-in (VIEWER envMapIntensity 0.45: unoccluded, the studio washed the AI Orange runner out to pale peach); two
  model tiers: the boot script loads `PC12_CONFIG.glbLow` (out/pc12_low.glb) on the 'low' quality tier (phones) as it
  picks the 512 px HDRI, the full model elsewhere (?glb= overrides both); there the Specs panel's detail switch loads
  the full model instead (?detail=full|light, remembered in localStorage 'pc12-detail'; review r1 RES1-02); the Specs
  panel and the part cards count the tier loaded; the Artifact bundle's gzip no-WebAssembly fallback is the light tier).
  The model carries NO markings (owner decision: no logos, registration, serials, flags or lettering).
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
  window).  Inside, the cabin keeps the light theme's studio in both themes, +0.6 EV (`LOOK.interiorEV`) with the
  cabin light `CABIN.inside` 1.0 (headliner ~190 / 255; at +1 EV AgX greyed the whole cabin) (`Stage.setInteriorLook`;
  the dark studio left the headliner near black) and is lit as inside wherever the eye is (`Model.updateCabin`
  forceInside).  Exit (button / Esc / a camera preset / another build step) restores what the tour
  changed: build step, cutaway, X-ray, explode, isolate, construction lines, the phone sheet, the door it opened.
  test/viewer_test.py [T1]-[T11] check it (data current, every stop from the menu with ray / table clearances and
  exposure, walk clamps incl. the walk ends' distance to the flight deck / curtain [T5b] and the seat sidestep,
  keyboard / pointer / touch, flights, exit, phone, dark theme; [T4b] the headliner).
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
