// Materials: the photo-calibrated lookdev values (viewer/materials.json, a copy of
// render/lookdev_materials.json) turned into MeshPhysicalMaterial at load, plus the shader patches the
// viewer layers on top of any material:
//   paint   primer -> livery sweep along Z (the build's "spray" wipe, nose to tail)
//   lining  back faces (the inside of the single-sided, outward-wound skins, seen through the glazing or
//           in the cutaway) render as a neutral interior lining instead of paint
//   glass   premultiplied glass: reflections are added on top of the tinted see-through, so a dark
//           pane mirrors the studio instead of turning grey; back faces (the view from inside) nearly
//           clear, or dim tinted while the camera is outside a closed cabin (U.cabinClosed)
//   cabin   interior light: IBL x cabinAO, key light x cabinAO^2 on the interior parts / linings and the
//           skins' back faces (no occlusion in the image-based light; Model.updateCabin sets it by viewpoint)
//   collar  station-dependent colour (the heat-blackened exhaust outlet), see render_collar; with render_polish
//           also the hand-polished waviness of the stacks (streaky roughness / tint noise + a small bump)
//   back    a material's own back-face colour (render_back_faces: the sooty inside of the exhaust stacks; the nose-gear
//           lamp's dark LED face behind its clear lens, drawn opaque)
//   grooves the tyres' circumferential tread grooves (render_grooves), in the mesh's own frame about the wheel axis
//   stripes woven transverse pinstripes (render_stripes: the cabin carpet), along the rest-pose station, band-limited
//   ao      the baked interior occlusion and window-sky visibility (the GLB's _AO vertex attribute, model/build.py
//           bake_interior_ao) on the cabin light inside
//   fleece  the crew seats' sheepskin pile: band-limited world-space clumps in the albedo and the normal; its plain fBm
//           form also the yoke pads' pebble-grain leather (render_pebble: yoke_leather)
//   leather a fine pebble grain (world-space bump, a little roughness wander) on the leathers
//   grain   the walnut veneer's figure: band-limited streaks along the vertical (along the station on a table top) in
//           the rest pose
//   brush   brushed metal: anisotropic highlights along a world axis (glTF X = BL) and a streaky roughness
// Patch flags live in material.userData.pc12 (JSON-able, so Material.clone() keeps them) and are
// (re)installed with installPatch().
import * as THREE from 'three';

// Uniforms shared by every patched material (one write updates all of them).
export const U = {
  paintSweep: { value: 100 },
  primer: { value: new THREE.Color(0x9fae8c) },       // light grey-green zinc-chromate-ish primer
  lining: { value: new THREE.Color() },                // set from LINING below (linear)
  liningRough: { value: 0.72 },
  // "cabin occlusion": the image-based light has no shadowing, so the inside of the fuselage (lining on
  // the skins' back faces, flight deck, cabin) would be lit like the outside.  Scaled down while the skin
  // is closed; 1 in the cutaway / X-ray / explode, where the interior is opened to the studio.  See CABIN.
  cabinAO: { value: 0.05 },
  // 1 = the camera is outside a closed fuselage: glazing seen from inside (the far-side panes, through a
  // near window) renders as dim tinted glass, as the unlit cabin does in the photos and the Cycles
  // renders, instead of letting the studio shine straight through the cabin.  0 = clear from inside.
  cabinClosed: { value: 1 },
  glassDim: { value: 0.82 },           // alpha of those far-side panes
  // 1 = the eye is inside the closed cabin (the interior tour, the cockpit preset): the cabin surfaces take the
  // CABIN_LOOK light below instead of the studio's x cabinAO (Model.updateCabin)
  cabinIn: { value: 0 },
  cabinKey: { value: 0 },
  cabinKnee: { value: 1 },
  cabinDiff: { value: new THREE.Vector2(1, 1) },
  cabinSpec: { value: new THREE.Vector2(1, 1) },
  cabinFill: { value: 1 },
  // inside (look L3): how much of the baked occlusion the cabin light takes (1 = all of it), and the floors of the window
  // sky visibility law: indirect diffuse x mix(sky.x, 1, sky), reflections x mix(sky.y, 1, sky) (CABIN_LOOK sky)
  cabinOcc: { value: new THREE.Vector3(1, 1, 0.5) },   // (share of the occlusion taken, its power on the diffuse, on the
  //                                                      reflections)
  cabinGain: { value: new THREE.Vector3(1, 1, 99) },   // inside: the world's diffuse / reflected light on the cabin trim,
  //                                                      and the most a surface takes (x the open world's)
  cabinSky: { value: new THREE.Vector2(0.10, 0.25) },
  // inside: the SPEC_KEEP trim's reflections weighted by where they point (CABIN_LOOK refl): x the share kept by a
  // reflection pointing aft / down into the dark cabin, y / z the smoothstep over dot(reflection, toward the glazing),
  // w the glazing direction's up component (forward = -Z)
  cabinRefl: { value: new THREE.Vector4(1, -0.3, 0.6, 0.35) },
  // inside, the flight deck (flight deck fix r3): the shade's daylight colour (xyz: a luminance-neutral tint, w: its share)
  // and the satin metals' cabin reflection probe ([dark, side windows, aisle, headliner] levels, see CABIN_LOOK)
  cabinShade: { value: new THREE.Vector4(1, 1, 1, 0) },
  cabinProbe: { value: new THREE.Vector4(1, 0, 0, 0) },
  cabinProbe2: { value: new THREE.Vector4(0, 0, 0, 0) },
  // inside, the flight deck's footwell (flight deck fix r5): [diffuse boost, its top (glTF Y), its aft end (glTF Z), -]
  cabinFoot: { value: new THREE.Vector4(0, 0, 0, 0) },
};
// cabin light by viewpoint (Model.updateCabin): outside a closed skin (the studio HDRI's softboxes make
// the unoccluded irradiance ~4x a real cabin's; 0.05, re-checked with the light theme's hangar grade at exposure 1.9:
// the seats read dark grey under the windshield's strip reflections, as in photo 130) / a door open / camera inside
// (eye adapted) / opened up
const Q_C = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
export const CABIN = { outside: 0.05, door: 0.45, inside: +(Q_C.get('cabIn') || 0.8), open: 1 };   // inside: review r1 NAV1-04 / r2 NAV2-04
//   had lifted it to 1.6 (with scene.js LOOK.interiorEV +0.6) for a near-white headliner -- which lifted every dark
//   surface with it (review r4 NAV8-01 / INT8-01); now 0.8 at +0.3 EV with the CABIN_LOOK below, the light trim's own
//   fill keeping the headliner at ~205 / 255
// The light inside (U.cabinIn = 1; review r4 NAV8-01 / INT8-01: the studio's unoccluded light lifted every dark surface
// -- overhead panel, bezels, ledges, walnut, carpet -- into a grey veil and washed the runner / curtain out): no key
// light through the closed skin (key: it had been x CABIN.inside^2 = 2.6 on every up-facing surface); the studio's
// diffuse light weighted by the surface's facing, diff = [facing the floor, facing up]; its reflections by where they
// point, spec = [down: the dark carpet / seats, up: the headliner / windows] (the studio's bright floor had mirrored in
// every glossy panel and display); `fill` on the light trim (lining, leathers, lavatory white: CABIN_TRIM), the cove /
// window light that keeps the headliner near-white while the dark trim keeps its own albedo.
// ?cabKey= ?cabDiff=a,b ?cabSpec=a,b ?cabFill= override them (look development).
const Q_M = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
const qv = (k, d) => {
  const s = Q_M.get(k);
  if (!s) return d;
  const a = s.split(',').map(Number);
  if (!a.every(Number.isFinite)) return d;
  return Array.isArray(d) ? d.map((x, i) => a[i] ?? a[a.length - 1]) : a[0];
};
// Tuned at the photo-fitted cabin_fwd (P1046406) and pilot / fd_cabin views, 1440 x 1080: headliner ~205, walnut ~60/42/28
// (photo 41-77 / 30-72 / 28-76), lower side panels ~70-80 (13-29 .. 60), runner hue ~32 deg / saturation >= 0.6, the
// overhead panel ~30 and the display bezels ~20 (near-black, as P1046408); before: 87-101 throughout (viewer_test [T14])
// Flight deck r1 LOOK (look L2-L4): the light inside is the outside world's (scene.js setInteriorLook: the procedural
// apron and sky as the image-based light, the sun with its own shadow map) -- `key` is the cabin materials' share of the
// directional light outside the tour (the key light; 0: no key through the closed skin), 1 inside (the sun, shadowed);
// the reflections' facing weights [down, up] x the window sky visibility (FD-J10: 0.06 / 0.3 had cut every reflection of
// the dark panel, the bezels and the titanium to nothing); the baked occlusion `occ` and the sky law `sky` (look L3)
// flight deck fix r2b (FDO2-01 / FID-FD2-03: the satin trim read as one flat tone, no sheen gradient): `refl` weighs the
// satin metals' reflections (REFL_DIR) by where they point -- [kept share pointing aft / down into the dark cabin,
// smoothstep from / to over dot(reflection, toward the glazing), the glazing direction's up component]: a titanium plate
// or the stack face that mirrors the windshield keeps its sheen, one that mirrors the cabin behind the crew goes darker
// (the unoccluded environment had lit them all alike; 0.7: panel_408b's tonal bands, [FD-L6], keep their margins --
// 0.3 put its median at 62 and 34 % of the pixels under 40)
export const CABIN_LOOK = { key: qv('cabKey', 0), diff: qv('cabDiff', [0.75, 1]), spec: qv('cabSpec', [0.12, 0.5]), fill: qv('cabFill', 2.3),
  occ: qv('cabOcc', [1, 1, 1]), sky: qv('cabSky', [0.0, 0.35]), gain: qv('cabGain', [27, 1.6, 1.5]), knee: qv('cabKnee', 1),
  refl: qv('cabRefl', [0.7, -0.3, 0.6, 0.35]),
  // flight deck fix r3 (FID-FD3-02: the photos' daylight shade is blue -- B - R 15-20 in P1046408 / 09 / 10 against the
  // model's neutral 0-7): ahead of the divider the interior's indirect diffuse light takes `shade` [tint #c8d6ff
  // normalised to unit luminance, share x (0.6 .. 1 as the surface faces the glazing)]; the sun keeps its warmth
  shade: qv('cabShade', [0.855, 0.995, 1.48, 0.42]),
  // (FDO3-01 / FID-FD3-01: the satin metals mirrored the open apron behind the aircraft wherever they pointed aft -- one
  // flat tone; P1046408's brushed sub-panels span 45-230 within a panel) the REFL_DIR metals' reflections that point aft
  // into the cabin see a cabin probe instead: [the dark cabin (seats, walnut, the crew), + the side windows (|R.x| > 0.55
  // near level), + the lit cabin through the divider opening (dead aft, level), + the headliner (up)]
  probe: qv('cabProbe', [0.55, 2.2, 1.1, 0.45]),
  // [the opening's window stripes: x (1 + this), -, -, -]
  probe2: qv('cabProbe2', [2.0, 0, 0, 0]),
  // flight deck fix r5 (FDO4-04): the footwell's soft fill -- [diffuse boost, below WL (glTF Y), ahead of STA (glTF Z), -]
  foot: qv('cabFoot', [0.8, 1.72, 3.95, 0]) };
U.cabinShade.value.set(...CABIN_LOOK.shade);
U.cabinProbe.value.set(...CABIN_LOOK.probe);
U.cabinProbe2.value.set(...CABIN_LOOK.probe2);
U.cabinFoot.value.set(...CABIN_LOOK.foot);
U.cabinKnee.value = CABIN_LOOK.knee;
U.cabinOcc.value.set(...CABIN_LOOK.occ);
U.cabinGain.value.set(...CABIN_LOOK.gain);
U.cabinSky.value.set(...CABIN_LOOK.sky);
U.cabinKey.value = CABIN_LOOK.key;
U.cabinDiff.value.set(...CABIN_LOOK.diff);
U.cabinSpec.value.set(...CABIN_LOOK.spec);
U.cabinFill.value = CABIN_LOOK.fill;
U.cabinRefl.value.set(...CABIN_LOOK.refl);
// per material inside: [share of the fill (uCabinFill ^ share), own factor(, reflection floor(, key in the specular(, up(,
// win(, refl))))))] on the world's diffuse light (the further entries: the yoke track's, below) -- the light
// trim gets the cove / window light (the cabin lining all of it, the leathers part), the flight deck's grey lining
// round the windshield (centre post, pillars, the walls under the side windows: P1046408 ~70-110) faces aft-down at
// the studio's bright floor and read near-white (~200) without its own factor
// (the trim with a share of the fill keeps that share of its light out of the window sky law: the cabin lining all of
// it, T4b / T14; the flight deck's anthracite lining_flightdeck has no entry since look L5: the sky law and the baked
// occlusion darken it where the photos do)
const CABIN_TRIM = { lining: [1, 1], leather: [0.5, 1], leather_crew: [0, 0.8], leather_dark: [0.6, 1],
  lav_white: [0.8, 1], toilet_white: [0.8, 1], psu_housing: [0.7, 1],
  // the crew seats' lavender-grey sheepskin (P1046408 / 09 ~90-130 in the cabin light, B > R)
  sheepskin: [0, 0.60],     // (FDY r1: 0.42 -> 0.60 for the LOCKS fleece's darker mean albedo: panel_408b ~119, P1046408 121)
  //                          (0.55 before the flight deck fix r1's soft knee / gain 27; fix r5: 0.52 -> 0.42 with the
  //                          curly pile -- its lighter mean albedo put panel_408b's fleece at 154-159 with the
  //                          footwell fill, P1046408 ~95-107; the fill no longer reaches it: ~110)
  // the graphite of the side consoles, the overhead panel, the AFCS strip: near-black (P1046408 consoles 4-9, the
  // overhead ~45 under the windshield's light; T14 <= 50)
  panel_dark: [0, 0.5],
  // the satin titanium sub-panels, band and stack (P1046408 66-78; its own reflections carry it, SPEC_KEEP; 0.45 on
  // the look track's geometry, 0.6 since the flight deck r1 merge: the proud plates and the moulded face round them
  // rendered them 64, now 72) and the graphite panel face round the PDU row and the cheek legs (the merge: 64, a shade
  // under the plates as the Garmin / brochure renders; P1046408 reads the face ~90)
  panel_graphite: [0, 0.85],     // (titanium 0.6 -> 0.8 with the warmer base, fix r2 FDO2-01; 0.6 since FDY r2, below)
  // (flight deck fix FDY r2 FIDY2-02: the sub-panels / plates read as flat light neutral-grey plastic -- 96 / 114 at
  // panel_408b with a 69-129 spread against P1046408's darker mauve brushed metal, 82 / 91, 28-148: a mauve base, more
  // metal and wider brushed bands (VIEWER), the fill 0.8 -> 0.5, and a NEAR-FIELD term x 1.05 below WL 1.78 .. x 0.8
  // above 1.88 (the band under the PDUs had read 114-128 against the photo's 91; half of it on the reflections): at
  // panel_408b 52 / 84 / 125, (82, 83, 93), the band 96 and the plates' foot 90 against the photo's 91 / 89)
  panel_titanium: [0, 0.5, 0, 0, 0, 0, 1, 1.05, 0.8, 1.78, 1.88, 0.5],
  // the near-black footwell carpet (P1046408 5-15)
  carpet_flightdeck: [0, 0.85],
  // the flight deck's anthracite lining -- posts, window surrounds, side walls, headliner (flight deck fix r1 FDO1-04 /
  // FID-FD1-09: with the soft-knee window light (below) the posts next to the glazing read 150-170, light grey slabs;
  // P1046410's posts 88-97, P1046408's 120-128 in its brighter frame)
  // (flight deck fix r2 FDO2-01 / 03: 0.72 -> 0.5 -- the A-pillar / side-window surround still read as a light slab,
  // 98-102 at the crew stops; now ~80 with the darker reveal face and the satin edge bead of the builder)
  // (0.5 since fix r2 FDO2-01 / 03 -- flight deck fix FDY r2 FIDY2-04: the A-pillars, centre post and surround read near-black charcoal from every interior
  // camera -- 57 / 68 at panel_408b against P1046408's light warm-grey 127 / 128, P1046410's 108: the windshield framed
  // in black where the photos frame it in grey: 0.5 -> 0.95 / 1.05, ~86 / 99 at panel_408b, ~100 / 108 from the pilot
  // stop; the funnel next to the glass keeps its darker satin reveal face)
  // (flight deck + yoke fix r3 FIDY3-01: still 30-45 % under P1046408 at its fitted camera -- lining 77 / post 96 against
  // 135 / 123 -- where P1046410 from the pilot's seat reads them ~108 against the model's 100 / 108: 0.95 -> 1.15 and the
  // post 1.05 -> 1.2, panel_408b 87 / 102, the pilot stop ~110 / 113; the rest of P1046408's gap is the A-pillar
  // region seen against the blown windshield / side windows, the model's light law keeps the stops' match)
  lining_flightdeck: [0, 1.15],
  // the glazing surround's darker satin inner face (fix r2 FDO2-03; without a factor it read 85, as light as the lining)
  lining_fd_reveal: [0, 0.5],
  // the eyebrow fascia (flight deck fix r2b FDO2-01: the light band over the PDUs, 126 from the crew seats and 122 at
  // panel_408b against P1046408's 96-104 and P1046410's 65-91)
  panel_grey: [0, 0.72],
  // the dark cove below the outer sub-panels (flight deck fix r3 FID-FD3-01: P1046408's cove ~41 at the fitted camera;
  // at x 1 it read 28)
  fd_cove: [0, 1.45],
  // flight deck fix r5: the A-pillar's round post (FDO4-02 / FID-FD4-02: P1046409 / 10 slim dark posts, ~60-90 with a
  // narrow bright edge -- its satin reflection of the glazing, SPEC_KEEP) and the palm tray's matte warm titanium floor
  // (FDO4-03: P1046408 ~128 / 117 / 132, no recognisable reflection)
  // (FDY r2 FIDY2-04 above: the post 0.5 -> 1.05; the palm tray 0.3 -> 0.42 -- 91 at panel_408b against P1046408's 117)
  lining_fd_post: [0, 1.2], tray_titanium: [0, 0.42],
  // (fix r5 FDO4-03 / FID-FD4-03: from above, the quadrant / pedestal views, the palm tray read 135-165 and the
  // stack's gunmetal shroud and the quadrant frame 100-135, light-grey plastic; P1046409 from the co-pilot's seat: the
  // tray 106 / 100 / 113, the face round it 51-60, the frame ~60-70)
  // (flight deck fix FDY r1 FIDY1-03: the quadrant frame / stack flanks read light grey, 65 / 86 / 76 at panel_408b /
  // P1046410 / P1046409's cameras against the photos' 28 / 43 / 39 under the same masks: 0.6 -> 0.25, its reflections kept;
  // 0.33 read 52 at panel_408b)
  // (flight deck fix FDY r2: the quadrant frame still 45 at panel_408b against P1046408's 27: 0.25 -> 0.15)
  stack_gunmetal: [0, 0.45], pedestal_gunmetal: [0, 0.15],
  // the yoke (3-D judges r1 FID1-01 / CR1-06): a third entry is the material's own REFLECTION floor -- the reflections
  // keep at least this share of the studio's (its clear coat / metal shows the windshield and headliner as in the
  // photos, not the floor-facing 0.06-0.3 of the dark trim) -- and a fourth the key light's share in its specular
  // only (the sun through the windshield: the photos' window streaks on the gloss cover); the gloss pearl-white cover a
  // little fill, its reflections and the key's glint, the satin-aluminium / smoke inserts their reflections near full
  // (tuned at P1046408 / 09's fitted cameras and the pilot stop -- before: cover 184-204 flat, inserts 0.50-0.76 / 0.34-0.68
  // of it; photos: cover 214-228, 0.94 / 0.84-0.87)
  // A fifth entry 'up' (3-D judges r2 FID2-04, installPatch): reflections pointing below the horizon mirrored above it
  // while inside -- from the crew seats the aft face's reflections point aft-down at the studio floor (the inserts
  // 0.72-0.83 of the cover against the photos' 0.91-0.99 / 0.81-0.93); at the photo cameras (reflections aft-up) nothing
  // changes.  A sixth, 'win' (CR2-06: the gloss cover read matte, its luminance +-2 %): a side-window radiance where the
  // reflections turn sideways -- on the cover's planar aft face nowhere (one reflection direction: the drawn face is one
  // plane), on its rolled perimeter, crown and arm tips a bright rim, the glossy edge highlights of the photos.  The
  // cover's fill share 0.4 -> 0.25 for the headroom (AgX compressed every highlight above ~225).  'yoke:<material>'
  // entries apply to the yoke parts only: the satin black moulding (FID2-05: body / cover 0.20 against the photos'
  // 0.27-0.30, the pads 1.5-1.8 x the body against 1.06-1.27) more fill and a reflection floor for its form shading.
  // Measured at the pilot stop / design eye (stats in CLAUDE.md, yoke rev O)
  // Rev P (3-D judges r3): the trim head's satin charcoal lunes take the body's light (FID3-01: face / body 1.0-1.6 as
  // the photos' footprints), its slot and the column sit in pockets the cabin light hardly reaches (no fill, half the
  // studio's diffuse, no reflection floor: the slot the darkest part of the head, the column no lit cylinder in its
  // recess -- FID3-01 / 02), and the nickel hex keeps the key's glint but no reflection floor / window term (FID3-03:
  // every facet lit, 0.8-1.0 of the cover, where the photos' hex footprint reads 0.10-0.34 with one or two glints)
  // (flight deck fix FDY r1, FDY-O1-02 / FIDY1-04 -- the yoke a flat matte cut-out up close: the cover one clipped tone,
  // p5-p95 207-210 at the yoke close-up against P1046408's 52-240, the body an even slate 55-67 (B - R +21) against the
  // photos' satin black 35-134, the pads sd 0.5 against 12): the cover's NEAR-FIELD entries 8-12 -- x 0.5 at WL 1.79 ..
  // x 1.06 at 1.91 on its diffuse, 0.7 of that on its clear coat (p5 206 -> 183, the median kept 209-214); the body
  // darker (0.40) with a reflection floor of 0.5, the side-window term 12 and PART_TRIM's sharper, stronger, slightly warm
  // reflections (p10 / p50 / p95 45 / 58 / 106, B - R +9: near-black with lit rims); the pads a near-field gradient
  // (x 0.7 .. 1.2 up the grip) and a finer grain (VIEWER yoke_leather), framed lighter than the body (pads / body 1.15)
  // (FDY r2 FIDY2-06 asked for a softer rim along the cover's shaded flank -- 'win' 12 / 19 took the cover's highlight
  // spread at the pilot stop to 16 / 19, under [Y1b]'s 20 (CR2-06: the gloss cover's edge highlights, the r2 yoke
  // judges): kept at 25)
  yoke_white: [0.25, 1, 1.4, 1, 1, 25, 1, 0.5, 1.06, 1.79, 1.91, 0.7], yoke_silver: [0.5, 1, 1, 0.6, 0, 0, 1],
  yoke_silver_dark: [0.5, 1, 1, 0.6, 0, 0, 1],
  yoke_nickel: [0, 1, 0, 0.35, 0, 0, 0.25], 'yoke:grip_black': [0, 0.40, 0.45, 1, 0, 14], yoke_trim_face: [0, 1.0, 0.25],
  yoke_slot: [0, 0.5],
  // rev Q (3-D judges r4): the cover's groove flanks are cavities -- no fill, part of the studio's diffuse (FID4-01); the
  // column a satin dark-grey tube, its reflections floored at 0.15 of the studio's (FID4-05: ~40-50 from the pilot's eye)
  yoke_groove: [0, 0.6], yoke_column: [0, 3.0, 0.6],
  // THE YOKE IN THE FLIGHT DECK'S LIGHT (the yoke track's merge, 2026-10-12): the entries above were tuned under the
  // review-r4 studio cabin light (no baked occlusion, the studio as the image light); in the merged flight deck the yoke
  // parts carry the bake's _AO (occlusion + window light, the CABIN_LOOK law on top of these entries), the sun and the
  // outside world as the image light.  Re-measured at the pilot stop (viewer_test [Y1]-[Y1c]) and the P1046408 pilot-yoke
  // camera ([Y1d]): the cover, grooves, lunes / slot / rocker and the nickel kept their entries; the satin-black body
  // 1.45 / 0.3 -> 1.25 / 0.35 (body / cover 0.28 -> 0.26: the world's sky in its reflections had read it blue-grey), the
  // pads -- 'yoke_leather' since the merge (the shared leather_black is the hood lip's) -- 0.65 (pads / body 1.42 ->
  // 1.18), the column 0.8 / 0.15 -> 3.0 / 0.6 (13.7 in its occluded recess, the 'hole' of the judges' FID4-05; now ~50),
  // the AFCS cap 0.75 (the shade's cool tint desaturated it to 0.76, the [Y1b] floor 0.75; now 0.83); the inserts' probe
  // below
  // (flight deck + yoke fix r3 FDY-O3-02: the pads one flat matte tone up close -- p10 / p50 / p90 60 / 70 / 76 at the
  // owner judge's yoke close-up against P1046409's 68-90 with sheen streaks: a steeper top-lit gradient (x 0.6 at WL 1.80
  // .. x 1.45 at 1.90), a 0.3 reflection floor and the side-window term, glossier (VIEWER roughness 0.32, PART_TRIM
  // specIn 2.5): 56 / 76 / 85 there, the pilot stop's pads / body 1.24 -- [Y1b] 1.0-1.4, the photos 1.06-1.27)
  yoke_leather: [0, 0.68, 0.3, 0, 0, 12, 1, 0.6, 1.45, 1.80, 1.90, 0.5], button_red: [0, 0.75],     // (FDY r1: [0, 0.65] + near field)
};
// Rev Q (3-D judges r4 FID4-02: the satin-aluminium insert had the cover's hue and luminance -- 0.91-0.99 of it, 1.07 at
// the AOPA camera, a p10-p90 spread of 7 levels: a flat grey paint): inside, the yoke's metal inserts mirror a CABIN
// PROBE instead of the studio (YOKE_PROBE; installPatch 'probe') -- the studio's blurred overhead radiance x a cool
// daylight tint x a law of the reflection direction: `k` [the dark cabin round and behind the crew, + the headliner /
// windshield overhead (smoothstep over R.y `y[0..1]`), + the yoke's OWN side window (reflections turned outboard, toward
// its side of the cockpit, near level: the far window lies across the cockpit behind the pedestal and the other seat),
// + the crew's lap / seat below (1 - smoothstep over R.y `y[2..3]`)], times a near-field term (1 -+ k[4] over the WL
// y[4..5], world: the face's upper part sees more of the sky over the glareshield, its lower part the lap and the panel's
// shade -- the photos' insert brightens toward the crown and darkens toward the step; a planar face mirroring one
// direction had read as one flat tone, p10-p90 7 levels against P1046408's 26).  The photos read
// the insert by where it points: P1046408's low camera mirrors the cabin roof (insert / cover 0.93), the AOPA camera from
// aft-outboard the dark cockpit centre (0.74; the smoke lower insert 0.37), and it is cooler than the cover throughout
// (B - R +35..+69 against +16..+30).  Its studio reflection floor / 'up' / 'win' are off (CABIN_TRIM).
// (the merge, 2026-10-12: the probe's reference radiance -- the image light's blurred zenith -- is the outside world's
// sky inside the merged flight deck, not the studio's softboxes, and the yoke's reflections carry the window-light law:
// rev Q's k read the upper insert 0.59 of the cover at the pilot stop and 0.72 at the P1046408 camera (the yoke branch:
// 0.81 / 0.94; [Y1] >= 0.78, [Y1d] 0.85-0.97).  From the stop the insert mirrors the cabin aft (R.y ~0.17: only k[0]),
// at P1046408's low camera the headliner (R.y ~0.6: k[0] + k[1]), so the dark-cabin term rose most: upper [0.22, 0.66,
// 0.45, 0.30] -> [1.3, 1.2, 0.82, 1.3], lower [0.20, 0.85, 0.35, 0.30] -> [1.0, 1.53, 0.63, 1.0] -- the stop 0.82 / 0.74,
// P1046408 0.89, B - R insert +34 against the cover's +12)
// (rev R, yoke judge r5 FID5-02: from the crew eyes the smoke lower insert merged with the upper -- 0.91 of it, photos
// 0.90-0.955 -- and at the P1046408 camera it was too dark, 0.71 of the cover against 0.82-0.93.  The two cameras see it
// in different directions: from the stop / design eye its reflection points aft-DOWN (R.y ~ -0.5: the lap term k[3]),
// from P1046408's low centreline camera aft-up-OUTBOARD (R.y 0.2-0.35, R across 0.39 toward its own side window: the
// side term k[2]), so the lower insert's lap term 1.0 -> 0.72 and side term 0.63 -> 1.7: lower / upper 0.87 at the stop and
// the design eye, lower / cover 0.77 at P1046408, 0.79 at P1046409 co-pilot; viewer_test [Y1e])
const YOKE_PROBE = {
  // (FDY r1 FIDY1-04: the upper insert x 1.25 -- 187 at P1046409's camera against the photo's 200-210)
  yoke_silver: { k: [1.625, 1.5, 1.025, 1.625, 0.22], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [0.82, 0.95, 1.22] },
  // (FDY r2 FIDY2-06: the lower insert 0.84-0.86 of the upper at panel_408b against the photos' 0.92-0.95, and bluer:
  // its terms x 1.2, the side term x 1.3 -- P1046408's low camera sees it mirror the side window -- with a less blue base
  // (VIEWER): 0.91 there, lower / upper 0.89 from the pilot stop ([Y1e] <= 0.90))
  yoke_silver_dark: { k: [1.2, 1.85, 2.2, 0.84, 0], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [0.82, 0.95, 1.22] },
};
for (const it of (Q_M.get('yokeProbe') || '').split('|')) {          // ?yokeProbe=name:k0,..,k4,y0,..,y5[,tr,tg,tb]|...
  const k = it.slice(0, it.lastIndexOf(':')), a = it.slice(it.lastIndexOf(':') + 1).split(',').map(Number);
  if (k && YOKE_PROBE[k] && a.length >= 11 && a.every(Number.isFinite)) {
    YOKE_PROBE[k] = { ...YOKE_PROBE[k], k: a.slice(0, 5), y: a.slice(5, 11) };
    if (a.length >= 14) YOKE_PROBE[k].tint = a.slice(11, 14);
  }
}
// A seventh entry, 'refl' (rev P, 3-D judges r3 FID3-03): the studio reflections' own factor inside -- the nickel hex
// mirrors the bright studio from every facet where the cockpit round it is dark (the photos' hex: one or two glints)
// ?cabTrim=name:share,factor,floor,key,up,win,refl|... overrides entries (look development)
for (const it of (Q_M.get('cabTrim') || '').split('|')) {
  const k = it.slice(0, it.lastIndexOf(':')), v = it.slice(it.lastIndexOf(':') + 1);   // 'yoke:grip_black:0,1.3,..'
  const a = (v || '').split(',').map(Number);
  if (k && a.length >= 2 && a.every(Number.isFinite)) CABIN_TRIM[k] = a;
}
// per part:material inside (flight deck fix r2), over CABIN_TRIM / VIEWER: `fill` as CABIN_TRIM, `specIn`, `sunIn`,
// `roughness`, `specularColor` (linear)
const PART_TRIM = {
  // the glareshield hood (FDO2-01): black leather whose brightness from the seats is its sky sheen, not its diffuse --
  // the hood top faces the windshield and took the window light law's full gain (pilot stop 148-150 against P1046410's
  // ~90-110); the side-window sills of the same leather keep theirs ([FD-L3] reads them at panel_408b)
  // (a diffuse cut changed nothing: 148 -> 151 with fill 0.45 and specIn 2.2; the sheen it is: specIn 0.6 and a softer
  // 0.55 roughness read 113 in the shade, ~95 / ~135 in and out of the posts' shadows with the sun at az 20 / el 30)
  // (+ the sun at 0.6 on it: sunlit it read ~135-140, a beige patch; now ~115-130 in the sun, ~90-100 in the shade)
  // (flight deck fix r2b FDO2-01: still 114-130 from the seats with the sun on it, 106 in the glare close-up -- a light
  // grey plastic hood against P1046409 / 10's 60-96: specIn 0.6 -> 0.35, sunIn 0.6 -> 0.3; its sheen tinted toward the
  // sky's blue, `specularColor` -- the interior's image-based light desaturates the zenith for the diffuse (outside.js
  // SKY envDesat), the photos' hood carries B - R 25-45 from the sky it mirrors)
  // (flight deck fix r3 FID-FD3-02 / FDO3-04: from panel_408b the hood's upper curve read 53-75 against P1046408's sky
  // sheen band 89-129, while the crew stops' steeper view must stay near P1046410's ~100: the leather's grazing
  // reflectance F90 1 (specularIntensity 1, F0 kept by specularColor x 0.5) -- the sheen grows toward grazing, where the
  // photo's band is -- and its sunlit patch lower, sunIn 0.3 -> 0.22: ~145 against the leather's ~120-130 in the sun)
  // (flight deck fix r5 FDO4-04 / FID-FD4-05: the sunlit patch still read near-white paint, ~160-200, where sunlit black
  // leather stays dark with a broad sheen: sunIn 0.22 -> 0.07 -- the glare close-up's patch 160 -> ~125 against the
  // shade's ~95-105, its edge softened by the sun's PCF radius 3, scene.js)
  // (flight deck fix FDY r2 FDY-O2-03: from the crew stops the hood still a mid blue-grey vinyl, 89-104 / 96 against
  // P1046410's dark charcoal 67: its fill 0.55, specIn 0.35 -> 0.2, sunIn 0.07 -> 0.03 -- 73 / 69 from the pilot /
  // co-pilot stop; panel_408b sees the rolled lip / underside, its own entry below, unchanged)
  'flight_deck:leather_glareshield': { specIn: 0.2, roughness: 0.55, sunIn: 0.03, specularIntensity: 1.0,
    specularColor: [0.375, 0.435, 0.5], fill: [0, 0.55] },
  // (fix r3 FID-FD3-02: the hood's rolled lip and underside -- what the photo-fitted panel_408b camera sees of the hood
  // from below -- read 53-75 against P1046408's sky-sheen band 86-125, B - R +31: the lip's grazing reflection of the
  // windshield; F90 1, F0 kept and tinted to the sky, a smoother 0.38, its reflections x 1.9)
  // (tuned at panel_408b: the band 68 -> ~105, P1046408 102; specIn 3.0 / roughness 0.32 read 131)
  'flight_deck:leather_black': { specIn: 1.9, specularIntensity: 1.0, specularColor: [0.30, 0.44, 0.64], roughness: 0.38 },
  // the side-window sills of the same leather (FDO2-03: a broad light-grey band from the seats, 86-120 in the window
  // light): a little less diffuse and sky sheen; [FD-L3] reads them at panel_408b (63 -> ~55; >= 50)
  'interior_lining:leather_glareshield': { fill: [0, 0.8], specIn: 1.15 },
  // (fix r3: the PDU's display bezels, AFCS and GTC faces -- satin black plastic whose light in P1046408 is the cabin
  // and crew it mirrors: its bezels 37-58 along the columns between and round the displays, the model's read 24 at the
  // fitted camera, a black field round every display; its reflections x 2 read 37 there, 42 from the pilot stop
  // ([T14] keeps them <= 50, [FD-L6] the frame's tonal bands); the CB panels on the lining keep theirs)
  'flight_deck:bezel_black': { specIn: 2.0 },
  // (flight deck fix FDY r1 FIDY1-07: the overhead panel read near-black from the cabin, 30 at cabin_fwd_406 against
  // P1046406's lit mid-grey 70; P1046408 reads it ~45 under the windshield's light and [T14] keeps it <= 50 at the pilot /
  // fd_cabin stops: its fill 0.5 -> 0.85, ~47 there and ~48 from the cabin -- the two photos' exposures disagree)
  'interior_lining:panel_dark': { fill: [0, 0.85] },
  // (FDY r1 FDY-O1-02 / FIDY1-04: the yoke body's satin black -- sharper, stronger reflections, a warm specular tint taking
  // the world sky's blue out of it; CABIN_TRIM 'yoke:grip_black' above)
  // (FDY r2 FDY-O2-02 / FIDY2-06: still matte slate without the photos' satin streaks down the grip faces: sharper and
  // stronger reflections, neutral-cool -- the median kept dark for [Y1b], the lit edges brighter)
  'yoke_L:grip_black': { roughness: 0.2, specIn: 4.0, specularColor: [0.95, 0.97, 1.0] },
  'yoke_R:grip_black': { roughness: 0.2, specIn: 4.0, specularColor: [0.95, 0.97, 1.0] },
  // (FDY r2 FDY-O2-02: the pads' blue-grey speckle -- a warm specular tint takes the sky's blue out of their sheen)
  'yoke_L:yoke_leather': { specularColor: [1.0, 0.95, 0.9], specIn: 2.5 },
  'yoke_R:yoke_leather': { specularColor: [1.0, 0.95, 0.9], specIn: 2.5 },
  // (FDY r2 FDY-O2-04: the quadrant plate and the flight deck's black parts read navy from above, B - R +26 at the
  // quadrant close-up, the photos satin black: a warm base and specular tint, less reflection inside)
  'flight_deck:black': { color: [0.036, 0.029, 0.022], specIn: 0.5, specularColor: [1.0, 0.9, 0.75] },
};
// ?partTrim=part:material={json}|... merges look-development overrides into PART_TRIM (as ?cabTrim for CABIN_TRIM)
for (const it of (Q_M.get('partTrim') || '').split('|')) {
  const i = it.indexOf('=');
  if (i < 1) continue;
  try { PART_TRIM[it.slice(0, i)] = { ...(PART_TRIM[it.slice(0, i)] || {}), ...JSON.parse(it.slice(i + 1)) }; } catch (e) { /* ignored */ }
}
// the satin / gloss trim of the flight deck keeps its reflections inside (FD-J10: the facing weights cut the titanium,
// the gunmetal, the bezels, the black leather and the displays to flat matte); the sky law and the occlusion still apply
// (+ the flight deck's shared detail materials (seed) and the geometry tracks' glossy ones: the annunciator / key caps,
// the smoked acrylic sun visors.  Every other new material -- stitch_thread, rubber_black, legend_plate, the fda_ /
// fdb_ trim -- takes the interior law with no entry (diffuse x gain x occlusion x window light, reflections by facing),
// and an emissive one (legend_lit, the annunciators' glow, fdb_cb_glow_*) keeps its emission as built)
const SPEC_KEEP = new Set(['panel_titanium', 'panel_graphite', 'pedestal_gunmetal', 'stack_gunmetal', 'pcl_pewter', 'chrome_trim', 'bezel_black',
  // rev R (yoke judge r5 FID5-05): the yoke's J band, its own satin dark-grey metal (it was the PCL's pewter)
  'yoke_band',
  // flight deck fix r5: the A-pillar post's satin edge highlight, the tray's dark bronze rim
  'lining_fd_post', 'trim_bronze',
  'leather_glareshield', 'leather_black', 'yoke_white', 'display_page', 'screen',
  'annun_amber', 'annun_red', 'annun_green', 'annun_blue', 'fdb_visor',
  // flight deck fix r1: the unlit smoked caps keep their gloss (FID-FD1-03)
  'annun_off_red', 'annun_off_amber', 'annun_off_green']);
// the SPEC_KEEP trim whose reflections CABIN_LOOK `refl` weighs by where they point (flight deck fix r2b): the satin
// metals -- not the displays, screens, bezels and caps (their glass / gloss keeps the reflection it had: weighted, the
// bezels and the pages' dark fields added ~0.7 % of panel_408b's pixels under 40, [FD-L6]) nor the black leathers (the
// hood's sheen from the crew seats points at the glazing anyway; from behind, at panel_408b, weighted it took the
// glareshield from 54 to ~52, [FD-L3] >= 50)
const REFL_DIR = new Set(['panel_titanium', 'panel_graphite', 'pedestal_gunmetal', 'stack_gunmetal']);
// (flight deck fix r5 FDO4-05: the PCL grip out of REFL_DIR -- the cabin probe's window stripes ran through its pewter
// as streaks, a glass jar from the quadrant view)

// Interior lining on the back faces.  The lookdev renders use a light grey (0.55) that Cycles darkens
// with real occlusion; the viewer's image-based light has none (a back face inside the cockpit sees the
// whole studio), so a darker neutral reads the same through the tinted glazing.
export const LINING = [0.2, 0.2, 0.195];
U.lining.value.setRGB(...LINING);

// Materials whose back faces are the aircraft interior (jamb: the door / hatch reveals, whose back faces outline the
// exit hatch and the airstair frame from inside the cabin).
const LINING_RE = /^(paint_|trim_black$|seal|jamb$)/;
// Parts inside the closed fuselage (cabin occlusion applies to all their faces: these two, and every part of the GLB
// group 'Interior' -- the seats, floor, consoles, divider, club tables, crew controls, the lining's fittings), and
// materials that only ever face the cabin (the door / hatch inner linings; the model's interior_lining part: cabin
// 'lining' and the darker 'lining_flightdeck' ahead of it).
export const INTERIOR_PARTS = new Set(['flight_deck', 'cabin_interior']);
const INTERIOR_MATERIALS = new Set(['lining', 'lining_flightdeck', 'jamb']);
const PAINT_RE = /^(paint_|trim_black$)/;
// premultiplied glass (reflections on top of the see-through); the cabin glazing also gets the view-from-inside path
// (U.cabinClosed / U.glassDim), a light lens does not (its back face is the lamp, see VIEWER.lens)
const GLASS_RE = /^(glass|lens$)/;
const CABIN_GLASS_RE = /^glass/;

// Viewer-only extras for materials the lookdev table does not cover (position lights; the G3000 PRIME displays' page
// content is emissive in the table itself).  The lights are off, as in every reference photo: glossy coloured lenses;
// setLights(true) switches them on.
const EXTRAS = {
  light_red: { color: [0.35, 0.01, 0.01], roughness: 0.1, light: [0.6, 0.02, 0.02] },
  light_green: { color: [0.01, 0.3, 0.05], roughness: 0.1, light: [0.02, 0.5, 0.1] },
  light_white: { color: [0.55, 0.55, 0.57], roughness: 0.1, light: [0.5, 0.5, 0.5] },
};
const LIGHT_MATS = new Set();

// Switch the position / strobe lights on (emissive) or off (glossy lenses).
export function setLights(on) {
  for (const m of LIGHT_MATS) {
    const x = EXTRAS[m.name];
    if (x && x.light) m.emissive.setRGB(...(on ? x.light : [0, 0, 0]), THREE.LinearSRGBColorSpace);
  }
}

// Viewer overrides on top of the lookdev values (the lookdev renders have ray-traced occlusion and many samples; the
// viewer's image-based light has neither):
//   envMapIntensity  an occlusion stand-in: the tyres, blades, wheels and legs sit under the fuselage / wing, where the
//                    unoccluded white studio made them read ~40 levels lighter than photo 130 / the Blender hangar render
//   specularIntensity also the dielectric F90 in three r160: less grazing sheen on the rubber / satin composite
//   polish           exhaust_polished render_polish: calmer than the lookdev's (whose bump / tint noise reads as blotchy
//                    camouflage at the viewer's sample count), streaks 3x longer along the stack, and NO bump: the
//                    pixel-difference bump of the value noise tore the studio's reflected streaks on the stacks and the
//                    chin-inlet lip into zig-zags at any tessellation (review r2 RES2-01c); the roughness / tint noise
//                    keeps the hand-polished waviness
//   back             render_back_faces for a material the lookdev table leaves out
const VIEWER = {
  tire: { specularIntensity: 0.5, envMapIntensity: 0.85 },
  tire_tread: { specularIntensity: 0.5, envMapIntensity: 0.85 },
  tire_groove: { specularIntensity: 0.4, envMapIntensity: 0.7 },
  wheel_main: { envMapIntensity: 0.75 },
  brake_housing: { envMapIntensity: 0.85 },
  brake_disc: { envMapIntensity: 0.75 },
  prop_blade: { specularIntensity: 0.3, envMapIntensity: 0.75 },
  wheel: { envMapIntensity: 0.75 },
  gear_leg: { envMapIntensity: 0.75 },
  exhaust_polished: { polish: { bump: 0, tint_mix: 0.12, stretch_x: 1 / 3 } },
  // the wing / tailplane de-ice boots: satin neoprene, black in every photo (3005, 0517, 130, 188); as a 0.25-rough
  // dielectric with full grazing reflectance they mirrored the white studio silver to near-white (review r4 EXT8-01:
  // sRGB 170-215 at the fitted wing_0459 camera against the photo's 17-61)
  deice_boot: { roughness: 0.6, specularIntensity: 0.18, envMapIntensity: 0.35 },
  // the deep ultramarine fuselage / fin blue: the white studio's fill in its clear coat lifted and greyed it to
  // periwinkle (review r4 EXT8-03: cowl top 81/123/184 vs photo 130's 57/111/198; B/R 2.3 vs 3.5); the light blue and
  // the white strokes keep the studio's
  paint_blue: { envMapIntensity: 0.75 },
  paint_navy: { envMapIntensity: 0.75 },
  // the cabin floor lies in the shade of the seats, ledges and furniture (P1046402 / 06: the AI Orange bands ~sRGB
  // 110/60/17 on a near-black navy); unoccluded, the studio washed the runner out to a pale peach (220/178/125)
  // (review r4 INT8-01: 0.45 left the runner tan, 205/155/93, under the cabin light; 0.3 and a deeper orange keep the
  // hue through AgX, ~P1046406's 147/83/22)
  carpet: { envMapIntensity: 0.3 },
  carpet_orange: { color: [0.69, 0.21, 0.012], envMapIntensity: 0.3 },
  carpet_light: { envMapIntensity: 0.3 },
  carpet_grey: { envMapIntensity: 0.3 },
  // the crew seats' sheepskin: a shaggy lavender-grey pile in P1046408 / 409, read as smooth white pillows (review r4
  // INT8-04): clumpy fibre noise in its albedo and normal (fleece patch, world space ~4 mm tufts), a softer sheen
  // flight deck r1 LOOK (L6): clumps of 12-20 mm (freq 65 per m) with darker crevices between them (albedo 0.4 .. 1.1,
  // `gamma` > 1 widens the dark crevices) -- the 4 mm tufts read as a smooth grey cushion at the seats' distance
  // flight deck fix r1 (FDO1-02 / FID-FD1-06): a fine curly pile -- ridged curls ~4 mm across (freq 240 per m) between
  // 0.70 and 1.06 of the albedo, a +-7 % clump wander at ~16 mm, a stronger bump; the photos' fleece varies ~+-10 %
  // locally (P1046408 / 09 16 px patches: sd 10-18 on 110-150), the look L6 clouds (0.4 .. 1.1 at 12-20 mm) read as
  // blue-grey camouflage
  // the albedo a shade less blue (B - R ~20 in the shade as P1046408 / 09, not ~30) and the sheen lobe neutral grey
  // flight deck fix r2 (FDO2-05 / FID-FD2-02: an even popcorn of round blobs with dark rims, slightly cyan): a calmer
  // pile -- the albedo between 0.86 and 1.05 (was 0.60 .. 1.10), no 40 / m clump layer, a finer 650 / m one, a 40 %
  // lower bump --, the tufts stretched along the vertical and their cells warped (curls of varying size), the base and
  // sheen R = G (P1046409's lavender 117 / 118 / 140 in the shade), and the sun at 0.45 on it (`sunIn`: the sunlit
  // co-pilot back 184 -> 172 instead of blowing out)
  // flight deck fix r2b (FID-FD2-02 re-measured: the r2 pile was too calm -- a local 10 px sd of 4-6 levels on the
  // shaded fleece at panel_408b against P1046408's 10-17, a flat lavender felt in the close-ups): the 120 / 260 per m
  // curls (~8 / 4 mm) at about twice the r2 contrast with wider, softer crevices (`edge` 0.3 .. 0.8, its mean `rm`
  // 0.45: the default's thin borders on a coarse layer read as cobbles / popcorn -- a 90 / m try --, at 70 / m as marble
  // veins), bump 0.65
  // flight deck fix r3 (FDO3-03 / FID-FD3-04: an even, fine 'cauliflower' / stone texture -- one curl size, hard lumpy
  // outlines, luminance p10-p90 93-123 against P1046408's 86-140): the curls grouped into soft clusters -- a coarse
  // 95 / m layer (~10 mm) over finer 200 / 520 / m curls, a 24 / m `clump` field (+-12 %) --, softer crevices (`edge`
  // 0.2 .. 0.8), a deeper bump, and the outline lightened (`rim`: below n.v 0.5, up to +60 %) with a lighter sheen: the
  // fibre tips glowing along the silhouette
  // (look-dev in one page, out/tmp/fd_fix_r3/ld: a 70 / m coarse layer stretched and warped read as marble from the
  // quadrant view, a 110 / m one with the r2 warp as a knitted herringbone -- the warp's sines line up the cells; with
  // the warp at 0.12 and no stretch the 95 / 200 / 520 per m curls group into soft clusters under the clump field)
  // (fix r5: a warm neutral grey with a mauve cast, R ~ G < B under the cabin's cool light -- P1046408 107 / 108 / 130,
  // P1046409 / 10 in the sun a pinkish lavender-grey; the r3 base read periwinkle, B - R 30-33)
  // (flight deck fix FDY r1, FDY-O1-01 / FIDY1-02: the r5 worms read as veined marble / crumpled foil, a cool
  // lavender-blue, local sd 7 against P1046408's 14: the LOCKS mode -- overlapping ~13-25 mm locks laid along the pile's
  // flow (+-0.9 rad, swirling over ~10 cm), lit toward their tips, ragged-edged, a few fibre strands each, dark seams and
  // gaps between them, over a fine 190 / m layer; the base warmer, R = G (P1046410's cushion R = G, B - R 19))
  // (tuned in the full viewer, out/tmp/fdy_fix_r1/ld c01-c03: at panel_408b luminance 112 -> ~119 with CABIN_TRIM 0.60,
  // local 9 px sd 13.8 against P1046408's 13.9, (109, 111, 129) B - R +20 against the photos' +15..+27; the lab's
  // brighter room light had asked for a darker, contrastier mat that read as dark blue camouflage in the cabin light)
  sheepskin: { color: [0.245, 0.198, 0.212], sheenColor: [0.35, 0.32, 0.34], sunIn: 0.45,
    fleece: { locks: [[100, 0.55, 1.08, 0.0024, 0.6, 1.15, 0.42, 0.9, 0.35, 0.45, 0.4],
      [200, 0.88, 1.06, 0.0006, 0.6, 0.9, 0.38, 0.9, 0.2, 0.25, 0.2]], lockShape: [0.25, 0.8, 0.3, 4.5, 0.8, 0.6],
      bump: 0.8, flat: [0.55, 0.85], lock: [15, 0.12], fibre: [900, 140, 0.05], rim: [0.5, 0.25], sheen: [0.5, 1.4] },
    // (flight deck fix FDY r2, FDY-O2-01 / FIDY2-01: SHELL FUR -- see furPatch.  The pile ~9 mm: the root 8 mm under the
    // drawn surface (less where the leather lies closer: furDirs), the tips 1 mm over it; two octaves of tufts, 2.2 / 3.3
    // mm (the plain blobs and the ridged curls, drawn 1.3 x longer down the faces, twisting with the height), the
    // threshold rising 0.05 -> 0.75 toward the tips, 40 / m lumps (taller, +-24 % albedo), short gated partings at 30 and
    // 60 / m, a fray at 1100 / m; the albedo from 0.18 at the root to 1 at the tips.  Tuned at panel_408b against
    // P1046408's cushions (the judges' texture measure: high-pass sd 8.9 / 10.9 / 12.4 / 14.9 at sigma 1 / 2 / 4 / 8
    // against 6.5 / 9.7 / 12.4 / 16.9, hp4 skew +0.13 / -0.19, p10 / p50 / p90 97 / 117 / 139 against 87 / 116 / 146;
    // look-dev out/tmp/fdy_fix_r2/ld2 n05)
    // (flight deck + yoke fix r3, FDY-O3-01 / FIDY3-03: within ~1 m the pile's partings read as scattered dark pits and
    // streaks -- grime / mould on a lavender popcorn -- where P1046409 / 10's cushions are a soft light clumpy pile, dark
    // only in the shaded folds.  The gaps fell through to a 0.18 root (0.2 of the tips), the gated partings raised the
    // threshold by 0.45 / 0.35 (straight down to the root) and the 40 / m lumps blotched the albedo +-24 %.  Now: the
    // root and the lowest layers 0.34 (a gap is a shadowed pile, not a hole), the layers' albedo convex in the height
    // (ao power 1.8) over a threshold that rises a little faster near the root (t power 0.9) -- the pile's tonal
    // distribution near-symmetric instead of piled up at the tips with a long dark tail --, the partings 0.2 / 0.15, the
    // lumps +-10 %, and the clumps' relief as SHADING: `clump` (furPatch) tips the normal over 28 / 65 per m mounds 5 /
    // 1.8 mm high, the fine tilt 0.9 -> 0.55.  Measured (viewer, the fleece eroded 10 px, the toolbar / Panel button out;
    // high-pass skew at sigma 4 / 8, sd at sigma 8): the owner judge's cush_close -0.70 / -0.98 -> -0.39 / -0.41, sd
    // 11.9; seats_aft -1.32 / -1.32 -> -0.56 / -0.46; quadrant -1.29 / -1.40 -> -0.47 / -0.43 -- P1046409 / 10's cushions
    // -0.50 / -0.49 and -0.31 / -0.32, sd 12.5 / 13.3; panel_408b (the judges' rows) skew +0.46 -> +0.18, p10 101 -> 99;
    // look-dev out/tmp/fdy_fix_r3/ld b00 / f02)
    fur: { h: [0.008, 0.001], root: 0.34, mean: 0.84, oct: [[450, 0.45, 0.5, 0, 1.3, 0, 0.5], [300, 0.55, 0.6, 1, 1.3, 0.4, 0.5]],
      t: [0.05, 0.75, 0.9], curl: [55, 0.8, 5.0], lump: [40, 0.10, 0.10], part: [[30, 0.2, 0.82, 40, 0.55, 1.3],
        [60, 0.15, 0.85, 80, 0.55, 1.5]], fray: [1100, 0.1], ao: [0.34, 1.13, 1.8], tilt: 0.55,
      clump: [[28, 0.005, 1.3], [65, 0.0018, 1.3]], sheen: [0.5, 1.1], far: [2.2, 3.2] },
    sheenRoughness: 0.8 },
  // the pleated divider curtain: deep burnt orange in P1046406 (77/23/0), read tan (208/166/116) under the old cabin light
  curtain: { color: [0.36, 0.11, 0.012] },
  // the walnut divider / FR34 header / table tops: the lookdev's dark grey-brown under a gloss lacquer read as grey-mauve
  // plastic in the tour (review r3 NAV3-04: the unoccluded white studio in its clear coat, lifted by the interior's
  // +0.6 EV, ~154/144/139); the panels stand in a narrow passage and mirror the cabin, not the studio: less
  // environment (an occlusion stand-in) and a warmer, more saturated brown (P1046406: dark walnut, ~sRGB 75/55/40)
  // flight deck r1 LOOK (L6): the figure -- the lookdev's render_grain (streaks along the vertical, along the station on
  // the table tops) at `amp` of the albedo and +-`rough` (fd_ngx2281_cfsjets_entry_left: strong vertical streaks)
  // (flight deck fix FDY r1 FIDY1-07: at the photo-fitted cabin_fwd_406 camera the divider read a dark saturated
  // mahogany, (41, 27, 16) against P1046406's smoky grey-brown (66, 53, 50): a lighter, less saturated walnut)
  // (flight deck fix FDY r2 FIDY2-08: still darker and warmer than P1046406's mauve-grey walnut, (50, 44, 40) against
  // (78, 70, 73) at cabin_fwd_406: lighter, R ~ B, a little more clear-coat reflection -- (72, 69, 74))
  veneer_walnut: { color: [0.15, 0.123, 0.118], envMapIntensity: 0.6, grain: { amp: 0.28, rough: 0.05 } },
  // the titanium panel face / sub-panels / stack sit under the glareshield and the cabin roof (P1046408: the face round
  // the PDUs ~sRGB 65-70, the inner sub-panels ~130); unoccluded they read as light grey plastic (~150-170)
  // flight deck r1 LOOK (L5): no occlusion stand-in any more (the baked occlusion / window sky do it); brushed along the
  // BL (glTF X): anisotropic highlights and streaky roughness (`rough` +-, streaks `len` m long, `w` m across)
  // flight deck fix r1 (FID-FD1-04): the satin metals keep more of their window / sky reflection inside (`specIn` x the
  // cabin law's reflections: P1046408 / 09 show highlights rolling across the sub-panels and the stack), the titanium a
  // shade smoother and more strongly brushed, a warmer rose-grey (P1046408: R ~ B > G on the sub-panels)
  // flight deck fix r2 (FDO2-01 / FID-FD2-03): warmer still -- R > G > B: P1046408's sub-panels 114 / 105 / 105 against
  // the render's cool 85 / 87 / 93 (the sky light inside is bluish; the metal's own tint has to carry the warmth)
  // flight deck fix r3 (FDO3-01 / FID-FD3-01: the sub-panels read as matte light-beige plaster, 105-110 with little
  // spread, where P1046408's brushed titanium spans 45-230 within a plate): a brushed METAL -- metalness 0.75, roughness
  // 0.26 --, its reflections streaked (`spec` +-15 % with the fine streaks, `band` +-12 % in 10 mm bands along it)
  // and, pointing aft, seeing the cabin probe (CABIN_LOOK probe: the windows bright, the seats dark)
  // (look-dev: metalness 0.85 / band 0.3 over 4 mm read as dark walnut-grain wood from the crew stops, the warm base
  // tinting the streaks brown; now a near-neutral base, metalness 0.75, the streak bands 10 mm x 16 cm at +-12 %)
  // (`up`: the faces turned up -- the palm tray, normal y 0.57; the sub-panels, soffit and plates face aft / down -- a
  // satin, isotropic finish, roughness + 0.32 and 15 % of the streaks: brushed, the tray mirrored the apron behind the
  // aircraft as streaked frosted glass from the crew stops, 141 in the pedestal close-up; now a soft gradient, 132)
  // (flight deck fix r5 FID-FD4-04: the brushed sub-panels overshot -- bright stainless sheet with long white streaks up
  // to ~200 and a cool steel hue, B > R, where P1046408 / 09 / 10 show a satin warm titanium with soft broad gradients,
  // R >= B: a warmer base, roughness 0.26 -> 0.34, the streaks' share of the reflection 0.15 -> 0.07 and the bands
  // +-12 -> +-7 %)
  // (flight deck fix FDY r2 FIDY2-02: a flat light neutral grey, (112, 114, 118), where P1046408 / 09 / 10 show a darker
  // mauve-bronze brushed metal, R > G, B > G, with lit bands and dark seams: a mauve base (0.25, 0.225, 0.245), metalness
  // 0.85, roughness 0.27, its reflections inside x 1.9 (2.2), the brushed bands +-35 % over 5 cm x 30 cm, the streaks
  // 15 %; the contact pass weighs more on
  // the plates' seams and feet, build.AO_CONTACT_POW_MAT)
  // (flight deck + yoke fix r3 FIDY3-02: the median and hue right, the range compressed -- p10 / p90 52 / 126 at
  // panel_408b against P1046408's 27 / 147: the bands +-35 -> +-50 % and the contact pass 1.3 -> 1.6 (build.py): 47 / 129)
  panel_titanium: { color: [0.25, 0.225, 0.245], metalness: 0.85, roughness: 0.27, specIn: 1.9,
    brush: { aniso: 0.75, axis: [1, 0, 0], rough: 0.05, len: 0.05, w: 0.0006, spec: 0.15, band: 0.5, bandLen: 0.3,
      bandW: 0.05, up: [0.40, 0.55, 0.32, 0.15] } },
  // (FDO3-01: the graphite face, the stack / pedestal gunmetal: a fine bead-blast grain -- isotropic, `len` 3-4 mm -- in
  // the roughness and the reflection, and a weaker band wander)
  panel_graphite: { specIn: 1.5, brush: { aniso: 0.35, axis: [1, 0, 0], rough: 0.04, len: 0.05, w: 0.0008, spec: 0.12,
    band: 0.2, bandLen: 0.12 } },
  pedestal_gunmetal: { specIn: 1.5, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  stack_gunmetal: { specIn: 1.5, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  // (flight deck fix r5 FDO4-05: a translucent glass jar from the quadrant view -- the probe's streaks; a solid satin
  // pewter: fewer, broader reflections, a shade warmer -- it read 116 / 124 / 140 against P1046408's 108 / 108 / 116)
  pcl_pewter: { specIn: 0.8, roughness: 0.45, color: [0.125, 0.113, 0.106] },
  // (rev R, yoke judge r5 FID5-05: the J band beside the column -- in the PCL's pewter it read a light-grey thumb on the
  // yoke branch, 105-117; the photos a darker grey tube with lit rolled edges, medians 26-57, p90 109-128 at P1046408 /
  // 09 / 10.  In the merged flight deck's light the pewter read 33-37 / p90 54-56, its edges unlit; the band's own dark
  // satin metal (the GLB's 0.075 / metallic 0.6) lit only by the cabin law read 24-26: a lighter, more metallic base with
  // a tighter sheen kept by the cabin law (SPEC_KEEP) -- 53-54 / p90 73-75 at P1046408 / 09)
  yoke_band: { color: [0.16, 0.155, 0.152], metalness: 0.9, roughness: 0.22, specIn: 2.5 },
  // (fix r5 FDO4-03: the palm tray's matte floor a warm mauve-grey -- the cabin's cool light had left it 108 / 113 / 128,
  // P1046408 123 / 114 / 130, P1046409 from above 106 / 100 / 113: R > G)
  tray_titanium: { color: [0.225, 0.185, 0.182] },
  // the stitched black glareshield / crew leather: a fine pebble grain (1-2 mm) in the normal and the roughness
  // (a shade glossier in the viewer, 0.40: the rolled lip's highlight line of P1046408 / 10 against the hood)
  // (flight deck fix r1 FID-FD1-04: a coarser, deeper grain -- 1.4 mm pebbles, readable from the seats -- and the
  // satin sheen kept a little stronger inside, P1046409's highlight along the hood)
  leather_glareshield: { roughness: 0.38, specIn: 1.4, leather: { freq: 450, dist: 0.0004, bump: 1.0, rough: 0.07 } },
  leather_black: { specIn: 1.3, leather: { freq: 450, dist: 0.0004, bump: 1.0, rough: 0.07 } },
  leather_dark: { leather: { freq: 700, dist: 0.00025, bump: 0.8, rough: 0.05 } },
  leather_crew: { leather: { freq: 600, dist: 0.0003, bump: 0.8, rough: 0.05 } },
  leather_crew_shell: { leather: { freq: 600, dist: 0.0003, bump: 0.8, rough: 0.05 } },
  // the crew harness webbing (flight deck fix r2 FDO2-09: flat grey ribbons): a fine woven grain in the normal and the
  // roughness (~0.7 mm)
  // (flight deck fix r3 FDO3-06: still flat grey card) a coarser, deeper weave (~1 mm) and more roughness wander
  // (flight deck fix FDY r1 FDY-O1-06: the straps read as flat hard-edged grey CAD ribbons -- the builder crowns them
  // across, seats.ribbon crown; here the woven webbing's sheen at grazing angles, AOPA / P1046409's satin bands)
  harness: { leather: { freq: 1100, dist: 0.00028, bump: 1.0, rough: 0.16 }, sheen: 0.7, sheenColor: [0.34, 0.34, 0.35],
    sheenRoughness: 0.35 },
  // the G3000 PRIME pages brighter inside (LK-07: x1.25 read 78-95 against the photos' >= 90 at the cabin exposure)
  display_page: { emisIn: 1.45 },
  // the yoke's smoke-silver lower insert (3-D judges r1 FID1-01): 0.30 read 0.34-0.68 of the cover in the cabin light
  // where P1046408 / 09 show 0.84-0.87 -- the viewer's image light has no window / headliner glow for its metal to
  // mirror; a lighter base (the judges' 0.45-0.5: 0.52 read 0.99 of the cover at P1046409, 0.30 0.68 at P1046408) with
  // the CABIN_TRIM reflection floor below
  yoke_silver_dark: { color: [0.45, 0.46, 0.47] },          // rev Q: cool (FID4-02); FDY r2 FIDY2-06: less blue
  // the upper satin insert a less blue aluminium (flight deck + yoke fix r3 FDY-O3-02: 'steel blue' up close -- B - R +37
  // at the yoke close-up against the cover's +13; the GLB's (0.58, 0.61, 0.67)): +33, its luminance kept ([Y1d] <= 0.97
  // at the P1046408 camera, 0.94)
  yoke_silver: { color: [0.60, 0.61, 0.63] },
  // (FDY r1 FIDY1-04: the pads' pebble grain, 1.1 mm, had faded to a flat tone at every crew-seat distance -- a 1.7 mm
  // grain at +-15 % with a lower roughness, the photos' grained, softly lit leather panels)
  // (flight deck fix FDY r2 FDY-O2-02: up close the 1.7 mm grain at +-15 % read as a coarse blue-grey granite / denim
  // speckle; P1046409 / 10 show smooth black leather with a very fine grain: 0.9 mm at -10 / +6 %, half the bump)
  yoke_leather: { fleece: { freq: 1100, oct: 2, lo: 0.9, hi: 1.06, dist: 0.00012, bump: 0.5 }, roughness: 0.32 },
  // the AFCS cap (3-D judges r2 FID2-03): AgX compresses a bright saturated red toward white -- the lookdev's 0.50 base
  // read 205/69/62 (sat 0.70) at the pilot stop; a darker deep red keeps it saturated (P1046409 199/58/78, Mexico R
  // 138/6/17)
  button_red: { color: [0.34, 0.0, 0.006] },
  // the nose-gear lamp: a clear lens with nothing modelled behind it; its back face is the dark (switched-off) LED face.
  // Clear: no milky diffuse on the front (the lookdev's light base colour is for its transmission variant)
  lens: { color: [0.02, 0.02, 0.022], back: { base: [0.03, 0.03, 0.035], rough: 0.25, opaque: true } },
};

export async function loadMaterialSpec(url = new URL('./materials.json', import.meta.url)) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}

const lin = (a) => new THREE.Color().setRGB(a[0], a[1], a[2], THREE.LinearSRGBColorSpace);

function partOf(o) {
  for (let p = o; p; p = p.parent) if (p.userData && p.userData.part) return p.userData.part;
  return null;
}
function groupOf(o) {
  for (let p = o; p; p = p.parent) if (p.userData && p.userData.part) return p.userData.group || null;
  return null;
}

// Glass: N reflecting surfaces (laminated windshield 2, double-pane cabin windows 4) reflect
// R = N F / (1 + (N - 1) F) at normal incidence (lookdev build_glass); as an F0 scale over the
// single-surface F.  It goes into specularColor (scales F0 only): three.js r160 also uses
// specularIntensity as F90 for dielectrics, so a scale > 1 there made the panes reflect 3.6x the
// environment at grazing angles (white "pill" windows).
function specularForSurfaces(e) {
  const N = e.surfaces || 1, ior = e.ior ?? 1.5;
  const F = ((ior - 1) / (ior + 1)) ** 2;
  return (N * F / (1 + (N - 1) * F)) / F;
}

// The GLB normals are int8 (KHR_mesh_quantization) on a marching-triangles tessellation: a near-mirror
// clear coat (lookdev 0.03) shows both as ripples in the softbox highlights.  The viewer floors the
// clear-coat roughness so the highlights stay smooth (the Cycles renders hide it with more samples of a
// larger light).
const CLEARCOAT_ROUGH_MIN = 0.1;

// ?viewer=material={json}|... merges look-development overrides into VIEWER (as ?cabTrim / ?partTrim)
for (const it of (Q_M.get('viewer') || '').split('|')) {
  const i = it.indexOf('=');
  if (i < 1) continue;
  try { VIEWER[it.slice(0, i)] = { ...(VIEWER[it.slice(0, i)] || {}), ...JSON.parse(it.slice(i + 1)) }; } catch (e) { /* ignored */ }
}

// glTF-style PBR entry -> MeshPhysicalMaterial (keeps side / flags of the GLB material)
function physicalFrom(name, e, src) {
  const V = VIEWER[name] || {};
  const bc = e.baseColorFactor || [1, 1, 1, 1];
  const blend = e.alphaMode === 'BLEND';
  const m = new THREE.MeshPhysicalMaterial({
    name,
    color: lin(bc),
    metalness: e.metallicFactor ?? 0,
    roughness: e.roughnessFactor ?? 0.5,
    clearcoat: e.clearcoatFactor || 0,
    clearcoatRoughness: e.clearcoatFactor ? Math.max(CLEARCOAT_ROUGH_MIN, e.clearcoatRoughnessFactor || 0) : 0,
    ior: e.ior ?? 1.5,
    specularIntensity: e.specularFactor ?? 1,
    side: e.doubleSided === false ? THREE.FrontSide : src.side,
    transparent: blend,
    opacity: blend ? bc[3] : 1,
    depthWrite: !blend,
  });
  if (e.specularFactor == null && e.surfaces > 1) m.specularColor.setScalar(specularForSurfaces(e));
  // the interior's emissive displays / LED coves / reading lights (assemble.EMISSIVE = the table's emissiveFactor)
  if (e.emissiveFactor) m.emissive = lin(e.emissiveFactor);
  // textures the GLB carries (cad/glb.py; the table's render_texture names the slot): the G3000 PRIME pages are the
  // emissive map of 'display_page' (model/g3000_pages.py atlas) -- kept, the table holds only the factors
  for (const k of ['map', 'emissiveMap']) if (src[k]) m[k] = src[k];
  // the crew sheepskin's pile (KHR_materials_sheen in the GLB: its colour lives in assemble.MATERIALS only)
  if (src.sheen > 0) { m.sheen = src.sheen; m.sheenColor.copy(src.sheenColor); m.sheenRoughness = src.sheenRoughness; }
  if (V.sheenRoughness != null) m.sheenRoughness = V.sheenRoughness;
  if (V.sheenColor) m.sheenColor.copy(lin(V.sheenColor));
  if (V.fur && FUR.on) m.userData.pc12 = { ...(m.userData.pc12 || {}), fur: { ...V.fur, role: 'root' } };
  else if (V.fleece) m.userData.pc12 = { ...(m.userData.pc12 || {}), fleece: { ...V.fleece } };
  for (const k of ['leather', 'brush']) if (V[k]) m.userData.pc12 = { ...(m.userData.pc12 || {}), [k]: { ...V[k] } };
  if (V.emisIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), emisIn: V.emisIn };
  if (V.specIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), specIn: V.specIn };
  if (V.sunIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), sunIn: V.sunIn };
  if (V.liningBase) m.userData.pc12 = { ...(m.userData.pc12 || {}), liningBase: V.liningBase };
  if (V.brush) { m.anisotropy = V.brush.aniso; }
  // pebble-grain leather (lookdev render_pebble: the yoke pads, L6Y item 6): the fleece patch's band-limited noise at
  // the grain size -- a low bump (~0.12 x the grain) and a faint albedo mottle, faded out where a grain is sub-pixel
  const pb = e.render_pebble;
  if (pb && !V.fleece) {
    m.userData.pc12 = { ...(m.userData.pc12 || {}), fleece: { freq: 1 / pb.size, oct: 2, lo: 1 - 0.4 * pb.amp,
      hi: 1 + 0.2 * pb.amp, dist: 0.12 * pb.size, bump: Math.min(1, 2 * pb.amp) } };
  }
  for (const k of ['roughness', 'metalness', 'specularIntensity', 'envMapIntensity', 'sheen']) if (V[k] != null) m[k] = V[k];
  if (V.color) m.color.copy(lin(V.color));
  const pol = polishOf(name, e);
  if (pol && pol.rough) {
    // static stand-in for the lookdev's polish noise (the collar patch adds the noise itself): the middle of the
    // roughness range, and the colour pulled half of tint_mix toward the heat tint (the noise's mean pull)
    m.roughness = 0.5 * (pol.rough[0] + pol.rough[1]);
    const tint = e.render_collar && e.render_collar.tint;
    if (tint) m.color.lerp(lin(tint), 0.5 * (pol.tint_mix ?? 0.3));
  }
  m.vertexColors = src.vertexColors;
  m.flatShading = src.flatShading;
  return m;
}

// lookdev render_polish with the viewer's overrides (VIEWER[name].polish)
function polishOf(name, e) {
  const p = e.render_polish, o = VIEWER[name] && VIEWER[name].polish;
  if (!p || !o) return p || null;
  const q = { ...p, ...o };
  if (o.stretch_x != null) { const st = (p.stretch || [1, 1, 1]).slice(); st[0] *= o.stretch_x; q.stretch = st; }
  return q;
}

// Tyre tread grooves (lookdev render_grooves; dormant since the GLB carries geometric grooves, model/wheels.py, and the
// lookdev table no longer sets render_grooves): n circumferential grooves `width` wide at +-0.1 / +-0.3 of the tread
// (tread = `tread` x the tyre width) on the crown, darkened to `floor` x the rubber and roughened to floor_rough.  The
// wheel axis and centre come from the tyre mesh itself (a surface of revolution: the principal axis of its vertices
// with the distinct variance), in the rest pose (world metres; the GLB's quantised mesh frames are scaled per axis);
// the shader evaluates them at each fragment's rest position (like the collar), so they follow the gear as it retracts.
function groovesFor(geo, g, mw) {
  const P = geo.attributes.position;
  if (!P || P.count < 16) return null;
  const n = P.count, c = [0, 0, 0], v = new THREE.Vector3();
  for (let i = 0; i < n; i++) { v.fromBufferAttribute(P, i).applyMatrix4(mw); c[0] += v.x; c[1] += v.y; c[2] += v.z; }
  c[0] /= n; c[1] /= n; c[2] /= n;
  const C = [0, 0, 0, 0, 0, 0];      // xx xy xz yy yz zz
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).applyMatrix4(mw); const x = v.x - c[0], y = v.y - c[1], z = v.z - c[2];
    C[0] += x * x; C[1] += x * y; C[2] += x * z; C[3] += y * y; C[4] += y * z; C[5] += z * z;
  }
  // power iteration on (tr I - C) finds the smallest-variance axis (the axle for a tyre wider than it is thick)
  const tr = C[0] + C[3] + C[5];
  let a = [1, 0.1, 0.1];
  for (let it = 0; it < 60; it++) {
    const b = [tr * a[0] - (C[0] * a[0] + C[1] * a[1] + C[2] * a[2]),
      tr * a[1] - (C[1] * a[0] + C[3] * a[1] + C[4] * a[2]),
      tr * a[2] - (C[2] * a[0] + C[4] * a[1] + C[5] * a[2])];
    const l = Math.hypot(...b) || 1;
    a = b.map((x) => x / l);
  }
  // width along the axis, outer radius
  let w0 = Infinity, w1 = -Infinity, R = 0;
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).applyMatrix4(mw); const x = v.x - c[0], y = v.y - c[1], z = v.z - c[2];
    const t = x * a[0] + y * a[1] + z * a[2];
    w0 = Math.min(w0, t); w1 = Math.max(w1, t);
    R = Math.max(R, Math.hypot(x - t * a[0], y - t * a[1], z - t * a[2]));
  }
  const W = w1 - w0;
  if (!(W > 0.02 && R > 1.5 * W / 2)) return null;
  const mid = 0.5 * (w0 + w1);
  const tread = (g.tread ?? 0.62) * W;
  const at = (g.n ?? 4) === 4 ? [-0.3, -0.1, 0.1, 0.3] : Array.from({ length: g.n }, (_, k) => -0.5 + (k + 0.5) / g.n);
  return {
    c: [c[0] + mid * a[0], c[1] + mid * a[1], c[2] + mid * a[2]], a, R,
    off: at.map((f) => f * tread), hw: 0.5 * (g.width ?? 0.006), rMin: R - 0.25 * W,
    floor: g.floor ?? 0.25, rough: g.floor_rough ?? 0.7,
  };
}

// Replace the GLB materials by name with the lookdev ones (and apply the lookdev's per-part
// reassignments: cabin glass / window rings, grey wheel wells, sooty stacks; a no-op on a GLB that already carries
// them, as model/assemble.py now does).  Materials missing from the table keep their GLB values.  A replaced
// material's clear coat / specular come from the table only: GLTFLoader has already turned the GLB's
// KHR_materials_clearcoat / _specular into a MeshPhysicalMaterial, which is discarded, not layered on.  Returns
// {upgraded, kept} material names for the Specs panel / tests.
export function upgradeMaterials(root, spec) {
  const M = (spec && spec.materials) || {};
  const reassign = new Map();
  for (const r of (spec && spec._model && spec._model.reassign) || []) {
    for (const p of r.parts) {
      if (!reassign.has(p)) reassign.set(p, new Map());
      reassign.get(p).set(r.from_material, r.to_material);
    }
  }
  const made = new Map();      // target name -> material
  const interior = new Map();  // material -> (part / 'yoke:' scope -> its interior clone)
  const occluded = new Map();  // interior material -> its clone reading the baked occlusion (_AO meshes)
  const upgraded = new Set(), kept = new Set();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh || !o.material || Array.isArray(o.material)) return;
    const src = o.material;
    const part = partOf(o);
    let name = src.name || '';
    const re = reassign.get(part);
    if (re && re.has(name) && M[re.get(name)]) name = re.get(name);
    const e = M[name];
    let m;
    if (e) {
      m = made.get(name);
      if (!m) { m = physicalFrom(name, e, src); made.set(name, m); }
      upgraded.add(name);
      if (e.render_collar) {
        // station-dependent colour needs the mesh's rest placement: one clone per mesh
        m = m.clone();
        const c = e.render_collar;
        m.userData.pc12 = { ...(m.userData.pc12 || {}), collar: {
          x0: c.x0, blend: c.blend ?? 0.005, tintX0: c.tint_x0 ?? c.x0 - 0.1,
          base: e.baseColorFactor.slice(0, 3), tint: c.tint || e.baseColorFactor.slice(0, 3), cbase: c.base,
          rough0: e.roughnessFactor ?? 0.1, rough1: c.rough ?? 0.45, metal1: c.metallic ?? 0.3, spec1: c.spec ?? 1,
          polish: polishOf(name, e) ? polishSpec(polishOf(name, e), e.roughnessFactor ?? 0.1) : null,
        },
        // rest world matrix (model station = glTF Z), so explode / fly-in moves the collar with the part
        rest: o.matrixWorld.toArray() };
      }
      if (e.render_grooves) {
        const g = groovesFor(o.geometry, e.render_grooves, o.matrixWorld);
        if (g) {
          m = m.clone();       // per mesh: its own axis and rest placement
          m.userData.pc12 = { ...(m.userData.pc12 || {}), grooves: g, rest: o.matrixWorld.toArray() };
        }
      }
      const gv = VIEWER[name] && VIEWER[name].grain;
      if (e.render_grain && gv) {
        // veneer figure in the rest pose (a club table slides; its figure goes with it): one clone per mesh (its rest
        // matrix is a uniform: the program is shared)
        const g = e.render_grain, sc = g.scale || [70, 70, 2.5];
        m = m.clone();
        m.userData.pc12 = { ...(m.userData.pc12 || {}), grain: { scale: [sc[1], sc[2], sc[0]], oct: Math.max(1, Math.min(5, Math.round(g.detail ?? 4))),
          amp: gv.amp ?? g.amp ?? 0.3, rough: gv.rough ?? 0 }, rest: o.matrixWorld.toArray() };
      }
      if (e.render_stripes) {
        // pinstripes along the station (model x = glTF Z) of the rest pose: one clone per mesh (its rest matrix)
        const st = e.render_stripes;
        m = m.clone();
        m.userData.pc12 = { ...(m.userData.pc12 || {}), stripes: { pitch: st.pitch ?? 0.012, duty: st.duty ?? 0.35,
          colour: (st.colour || e.baseColorFactor).slice(0, 3) }, rest: o.matrixWorld.toArray() };
      }
      const b = e.render_back_faces || (VIEWER[name] && VIEWER[name].back);
      if (b && m.side === THREE.DoubleSide && !(m.userData.pc12 && m.userData.pc12.back)) {
        // e.g. the sooty inside of the polished exhaust stacks, the lamp face behind the nose-gear lens
        if (m === made.get(name)) { m = m.clone(); made.set(name, m); }
        m.userData.pc12 = { ...(m.userData.pc12 || {}), back: { base: b.base, rough: b.rough ?? 0.8, spec: b.spec ?? 1, opaque: !!b.opaque } };
      }
    } else {
      m = src;
      kept.add(name);
      // a GLB clear coat (KHR_materials_clearcoat) on a material the table lacks (or without materials.json): the same
      // roughness floor as the lookdev ones
      if (src.isMeshPhysicalMaterial && src.clearcoat > 0) src.clearcoatRoughness = Math.max(CLEARCOAT_ROUGH_MIN, src.clearcoatRoughness);
      const x = EXTRAS[name];
      if (x && !src.userData.pc12extras) {
        if (x.color) src.color = lin(x.color);
        if (x.roughness != null) src.roughness = x.roughness;
        if (x.emissive) src.emissive = lin(x.emissive);
        if (x.light) LIGHT_MATS.add(src);
        src.userData.pc12extras = true;
      }
    }
    const f = m.userData.pc12 || (m.userData.pc12 = {});
    if (PAINT_RE.test(name)) f.paint = true;
    if (LINING_RE.test(name) && m.side === THREE.DoubleSide) f.lining = true;
    if (GLASS_RE.test(name) && m.transparent) { f.glass = true; if (CABIN_GLASS_RE.test(name)) f.cabinGlass = true; }
    installPatch(m);
    if (INTERIOR_PARTS.has(part) || groupOf(o) === 'Interior' || INTERIOR_MATERIALS.has(name)) {
      // one interior clone per material -- or per part:material where PART_TRIM has an entry (flight deck fix r2: the
      // hood's leather apart from the side-window sills of the same leather), or per 'yoke:<material>' where CABIN_TRIM
      // has a yoke-scoped entry (the yokes' own look, yoke track); the yokes' metal inserts mirror their own cabin probe
      // (YOKE_PROBE)
      const pt = PART_TRIM[part + ':' + name];
      const isYoke = /^yoke_/.test(part || '');
      const yk = isYoke && CABIN_TRIM['yoke:' + name] ? 'yoke:' + name : null;
      const ck = pt ? part : (yk || '');
      if (!interior.has(m)) interior.set(m, new Map());
      const im = interior.get(m);
      if (!im.has(ck)) {
        const c = clonePatched(m, { interior: true, cabinFill: (pt && pt.fill) || CABIN_TRIM[yk || name] || null, specKeep: SPEC_KEEP.has(name), reflDir: REFL_DIR.has(name),
          ...(pt && pt.specIn ? { specIn: pt.specIn } : {}), ...(pt && pt.sunIn ? { sunIn: pt.sunIn } : {}),
          probe: (isYoke && YOKE_PROBE[name]) || null });
        if (pt && pt.roughness != null) c.roughness = pt.roughness;
        if (pt && pt.specularColor && c.specularColor) c.specularColor.copy(lin(pt.specularColor));
        if (pt && pt.specularIntensity != null) c.specularIntensity = pt.specularIntensity;
        if (pt && pt.color) c.color.copy(lin(pt.color));
        im.set(ck, c);
      }
      m = im.get(ck);
      // the baked occlusion / window sky (look L3): the meshes carrying the GLB's _AO attribute read it
      if (o.geometry && o.geometry.attributes._ao) {
        if (!occluded.has(m)) occluded.set(m, clonePatched(m, { ao: true }));
        m = occluded.get(m);
      }
    }
    o.material = m;
  });
  return { upgraded: [...upgraded].sort(), kept: [...kept].sort() };
}

// lookdev render_polish (lookdev.py build_metal): a world-space noise (`scale` per metre, the position multiplied by
// `stretch` first: model x = station = glTF Z, so streaks run along the stack; `detail` octaves) mapped 0.3..0.7 -> 0..1
// that drives the roughness between rough[0] and rough[1], pulls the colour up to tint_mix toward the collar's heat
// tint and bumps the normal (strength `bump`, height = noise x bump_distance metres).
function polishSpec(p, rough) {
  const st = p.stretch || [1, 1, 1], k = p.scale ?? 20;
  return {
    // glTF (X, Y, Z) = model (y, z, x)
    freq: [k * (st[1] ?? 1), k * (st[2] ?? 1), k * (st[0] ?? 1)],
    oct: Math.max(1, Math.min(5, Math.round((p.detail ?? 3) + 1))),
    rough: p.rough || [rough, rough], tintMix: p.tint_mix ?? 0.3,
    bump: p.bump ?? 0, dist: p.bump_distance ?? 0.01,
  };
}

// Value noise + band-limited fBm (octaves finer than about a pixel fade out, so the stacks do not sparkle at a
// distance); pcPolishN in 0..1, mean 0.5.
const GLSL_POLISH = `
float pcHash( vec3 p ) {
  p = fract( p * 0.3183099 + 0.1 ); p *= 17.0;
  return fract( p.x * p.y * p.z * ( p.x + p.y + p.z ) );
}
float pcNoise( vec3 x ) {
  vec3 i = floor( x ), f = fract( x );
  f = f * f * ( 3.0 - 2.0 * f );
  return mix( mix( mix( pcHash( i ), pcHash( i + vec3( 1, 0, 0 ) ), f.x ),
                   mix( pcHash( i + vec3( 0, 1, 0 ) ), pcHash( i + vec3( 1, 1, 0 ) ), f.x ), f.y ),
              mix( mix( pcHash( i + vec3( 0, 0, 1 ) ), pcHash( i + vec3( 1, 0, 1 ) ), f.x ),
                   mix( pcHash( i + vec3( 0, 1, 1 ) ), pcHash( i + vec3( 1, 1, 1 ) ), f.x ), f.y ), f.z );
}
float pcFbm( vec3 p, int oct, float fw ) {
  float a = 0.5, s = 0.0, w = 0.0, fr = 1.0;
  for ( int o = 0; o < 5; o ++ ) {
    if ( o >= oct ) break;
    float k = 1.0 - smoothstep( 0.2, 0.6, fw * fr );
    s += a * k * ( pcNoise( p * fr + float( o ) * 7.13 ) - 0.5 );
    w += a;
    fr *= 2.0; a *= 0.5;
  }
  return 0.5 + s / w;
}
// surface-gradient bump (Mikkelsen 2010, unnormalised screen derivatives: heights in world units).  The height
// steps per pixel (dhx, dhy) are explicit forward differences of the noise, not dFdx( h ): those are constant over
// each 2x2 pixel quad and left the mirror-like highlights stair-stepped.
vec3 pcBump( vec3 pos, vec3 n, float dhx, float dhy, float faceDir ) {
  vec3 sx = dFdx( pos ), sy = dFdy( pos );
  vec3 r1 = cross( sy, n ), r2 = cross( n, sx );
  float det = dot( sx, r1 ) * faceDir;
  vec3 g = sign( det ) * ( dhx * r1 + dhy * r2 );
  return normalize( abs( det ) * n - g );
}
float pcPolish( vec3 p, int oct, float fw ) { return clamp( ( pcFbm( p, oct, fw ) - 0.3 ) / 0.4, 0.0, 1.0 ); }
`;

// ------------------------------------------------------------------------------------ shader patches
const GLSL_COLLAR_VS = 'uniform mat4 uRestM;\nvarying vec3 vRestP;\n';
// back face?  Transparent double-sided materials draw a BackSide pass (FLIP_SIDED defined; gl_FrontFacing is flipped
// there) and then a FrontSide pass; opaque double-sided ones one pass (DOUBLE_SIDED).
const GLSL_BACKFACE = `bool pcIsBack() {
#if defined( FLIP_SIDED )
  return true;
#elif defined( DOUBLE_SIDED )
  return !gl_FrontFacing;
#else
  return false;
#endif
}
`;

// ------------------------------------------------------------------------------------ shell fur
// The crew seats' sheepskin as SHELL FUR (flight deck fix FDY r2, FDY-O2-01 / FIDY2-01: six judge rounds of flat 2-D pile
// patterns on the cushion surface -- lichen, marble, foil / worms, coral, leaf / fish-scale locks -- read as a print on a
// smooth slab).  The fleece mesh is drawn as a stack of offset layers along its (welded) normal: the base mesh itself is
// the ROOT layer, `h[0]` inside the drawn surface (the GLB's crowned fleece face IS the drawn cushion outline, so the pile
// grows inward and its tips reach the outline, `h[1]` beyond it), dark (`root`); `n` SHELLS at even heights up to the
// tips are drawn after it in one instanced call (gl_InstanceID -> height t, outermost first) and each keeps only its
// cross-section of the pile: a dense field of curly tufts (`oct`: octaves of value noise, ridged ones the curls, each
// turned off the grid and swirled with height, `curl`) above a threshold rising with the height (`t`), grouped in lumps
// (`lump`) and frayed (`fray`) -- so the tufts taper, the gaps between them are the lower, darker layers (`ao`: the
// albedo from the root to the tips) and the silhouette breaks up by itself.  The tufts' sides tilt the normal (`tilt`),
// the sheen sits on the tips (`sheen`).  Shadow coordinates, the world position of the pile field and the baked
// occlusion stay those of the drawn surface (only gl_Position moves), so every layer of a column reads one field and
// one shadow.  Beyond `far` [from, to] m from the eye the shells thin out and the root takes the pile's mean albedo
// (`mean`): sub-pixel tufts only alias.  The shells are drawn from the base mesh's onAfterRender (addFur) while it
// carries its own material: an ID pass, the X-ray, the cutaway or a highlight swap the material and draw no shells;
// they cast no shadow (the drawn surface does), are never picked, and follow the mesh's visibility and transform.
// ?fur=0 falls back to the flat `fleece` patch, ?furN= sets the shell count (8 on the low quality tier, 14 elsewhere:
// main.js).  The root's depth is bounded by the part's other surfaces under the pile (furDirs: the leather the pads
// sink into would otherwise show through the partings as pale holes).
const Q_F = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
export const FUR = { on: Q_F.get('fur') !== '0', n: +(Q_F.get('furN') || 0) || null };

const GLSL_FUR = `
// value noise and its analytic gradient (cell units)
vec4 pcNoiseD( vec3 x ) {
  vec3 i = floor( x ), f = fract( x );
  vec3 u = f * f * ( 3.0 - 2.0 * f ), du = 6.0 * f * ( 1.0 - f );
  float a = pcHash( i ), b = pcHash( i + vec3( 1, 0, 0 ) ), c = pcHash( i + vec3( 0, 1, 0 ) ), d = pcHash( i + vec3( 1, 1, 0 ) );
  float e = pcHash( i + vec3( 0, 0, 1 ) ), g = pcHash( i + vec3( 1, 0, 1 ) ), h = pcHash( i + vec3( 0, 1, 1 ) ), k = pcHash( i + vec3( 1, 1, 1 ) );
  float k1 = b - a, k2 = c - a, k3 = e - a, k4 = a - b - c + d, k5 = a - c - e + h, k6 = a - b - e + g, k7 = - a + b + c - d + e - g - h + k;
  return vec4( a + k1 * u.x + k2 * u.y + k3 * u.z + k4 * u.x * u.y + k5 * u.y * u.z + k6 * u.z * u.x + k7 * u.x * u.y * u.z,
    du * vec3( k1 + k4 * u.y + k6 * u.z + k7 * u.y * u.z, k2 + k5 * u.z + k4 * u.x + k7 * u.z * u.x, k3 + k6 * u.x + k5 * u.y + k7 * u.x * u.y ) );
}
`;
// fixed rotations that turn each octave off the lattice (value noise shows its grid along the axes)
const FUR_ROT = [
  [0.36, 0.48, -0.80, -0.80, 0.60, 0.00, 0.48, 0.64, 0.60],
  [0.00, 0.80, 0.60, -0.80, 0.36, -0.48, -0.60, -0.48, 0.64],
  [0.60, 0.00, 0.80, 0.64, 0.60, -0.48, -0.48, 0.80, 0.36],
];

function furPatch(q, vs, fs, fsHead) {
  const f4 = (x) => (+x).toFixed(5), shell = q.role === 'shell', n = Math.max(1, q.n | 0);
  const [h0, h1] = q.h || [0.010, 0.001];
  // the welded offset direction (addFur: the mean normal of the vertices at a position, so the layers do not tear open
  // along the mesh's creases), the layer height t (0 = the root, the base mesh)
  vs = `attribute vec4 pcFurDir;\nvarying float vPcFurT;\n` + vs.replace('#include <project_vertex>', `#include <project_vertex>
  {
    float pcFt = ${shell ? `1.0 - float( gl_InstanceID ) / ${f4(n)}` : '0.0'};
    vec3 pcFd = normalize( normalMatrix * pcFurDir.xyz );
    mvPosition.xyz += pcFd * mix( ${f4(-h0)} * pcFurDir.w, ${f4(h1)}, pcFt );
    gl_Position = projectionMatrix * mvPosition;
    vPcFurT = pcFt;
  }`);
  fsHead += 'varying float vPcFurT;\n' + GLSL_FUR;
  const far = q.far || [2.0, 3.0];
  if (!shell) {
    fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float pcFurA = mix( ${f4(q.root ?? 0.3)}, ${f4(q.mean ?? 0.8)}, smoothstep( ${f4(far[0])}, ${f4(far[1])}, length( vViewPosition ) ) ), pcFurT = 0.0;
  diffuseColor.rgb *= pcFurA;`);
  } else {
    const oct = q.oct || [[220, 0.65, 0.4, 0], [480, 0.35, 0.6, 1]];
    const cu = q.curl || [60, 0.5, 6.0], lu = q.lump || [35, 0.08, 0.08], fr = q.fray || [0, 0], th = q.t || [0.2, 0.74, 1.0];
    const ao = q.ao || [0.35, 1.0, 0.8];
    const parts = !q.part ? [] : Array.isArray(q.part[0]) ? q.part : [q.part];
    // clumps (flight deck fix FDY r3): soft cm-scale mounds of the matted pile as a NORMAL tilt only -- [freq per m,
    // height m, vertical stretch]: the slope of a height field amp x noise(freq x p) (pcNoiseD) tips the shading normal,
    // so the clumps are lit on the side toward the light and shaded on the other (the photos' dark sits in the shaded
    // folds between the clumps, not in isolated pits)
    const clumps = q.clump || [];
    // octaves [freq per m, weight, twist (cells per unit height), mode, vertical stretch, warp (cells), crease power]:
    // mode 0 the noise itself (blobs), 1 ridged (raised strands along its 0.5 isolines), 2 CREASED (|2n - 1|^power:
    // broad plateaus cut by narrow dark creases along the isolines -- the lit mat parted into tufts); the vertical
    // stretch draws the tufts longer down the cushions' and backs' faces (world Y: no swimming on the curved pads), the
    // warp bends the creases into curls (a domain warp at 0.4 x the octave's frequency)
    const octs = oct.map(([fq, w, wk, ridged, stY = 1, dw = 0, cp = 0.5], i) => {
      const R = FUR_ROT[i % FUR_ROT.length];
      const S = `vec3( 1.0, ${f4(1 / stY)}, 1.0 )`;
      return `
    {
      mat3 pcR = mat3( ${R.map(f4).join(', ')} );
      vec3 pcQ = pcR * ( vPcW * ${f4(fq)} * ${S} ) + ${f4(wk)} * pcW + ${f4(5.3 + 7.1 * i)};${dw ? `
      pcQ += ${f4(2 * dw)} * ( vec3( pcNoise( pcQ * 0.4 + 1.7 ), pcNoise( pcQ * 0.4 + 9.2 ), pcNoise( pcQ * 0.4 + 15.9 ) ) - 0.5 );` : ''}
      vec4 nd = pcNoiseD( pcQ );
      ${ridged === 1 ? `float s = sign( 2.0 * nd.x - 1.0 ); nd = vec4( 1.0 - abs( 2.0 * nd.x - 1.0 ), - 2.0 * s * nd.yzw );` : ''}${ridged === 2 ? `
      { float a = abs( 2.0 * nd.x - 1.0 ) + 1e-4, s = sign( 2.0 * nd.x - 1.0 );
        nd = vec4( pow( a, ${f4(cp)} ), ${f4(2 * cp)} * pow( a, ${f4(cp - 1)} ) * s * nd.yzw ); }` : ''}
      pcF += ${f4(w)} * nd.x;
      pcG += ${f4(w * fq)} * ( ${S} * ( transpose( pcR ) * nd.yzw ) );
    }`;
    }).join('');
    const w0 = oct.reduce((a, o) => a + o[1], 0) || 1;
    fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float pcFurA = 1.0, pcFurT = vPcFurT;
  vec3 pcFurG = vec3( 0.0 ), pcFurC = vec3( 0.0 );
  {
    float pcFar = smoothstep( ${f4(far[0])}, ${f4(far[1])}, length( vViewPosition ) );
    if ( pcFar > 0.999 ) discard;
    float t = vPcFurT;
    // the curl: each octave's lookup swirls with the height, its phase a slow noise (the tufts twist as they rise)
    float pcPh = 6.2832 * pcNoise( vPcW * ${f4(cu[0])} + 3.7 ) + ${f4(cu[2])} * t;
    vec3 pcW = ${f4(cu[1])} * t * vec3( cos( pcPh ), sin( pcPh ), cos( 0.7 * pcPh + 1.3 ) );
    float pcF = 0.0; vec3 pcG = vec3( 0.0 );${octs}
    pcF /= ${f4(w0)}; pcG /= ${f4(w0)};
    // lumps: the pile taller in cm-scale patches (the threshold lower)
    float pcL = pcNoise( vPcW * ${f4(lu[0])} + 23.9 );
    float pcT = mix( ${f4(th[0])}, ${f4(th[1])}, pow( t, ${f4(th[2])} ) ) - ${f4(lu[1])} * ( 2.0 * pcL - 1.0 );${fr[1] ? `
    pcT += ${f4(fr[1])} * ( pcNoise( vPcW * ${f4(fr[0])} + vec3( 7.7, 1.3, 4.1 ) + 3.1 * t ) - 0.5 );` : ''}
${parts.map(([pf, pa, pw, gf = 0, gl = 0.5, st = 1], i) => {
      // partings: the pile parted along the 0.5 isolines of a noise (the dark creases between the lumps / curls),
      // stretched `st` down the vertical faces; with a gate [freq, level] only where a second noise exceeds the level --
      // short slits instead of a connected crackle net
      const S = `vec3( 1.0, ${f4(1 / st)}, 1.0 )`;
      return `
    {
      float pcP = smoothstep( ${f4(pw)}, 1.0, 1.0 - abs( 2.0 * pcNoise( vPcW * ${S} * ${f4(pf)} + ${f4(41.0 + 13.7 * i)} ) - 1.0 ) );${gf ? `
      pcP *= smoothstep( ${f4(gl)}, ${f4(gl + 0.2)}, pcNoise( vPcW * ${S} * ${f4(gf)} + ${f4(63.0 + 5.1 * i)} ) );` : ''}
      pcT += ${f4(pa)} * pcP;
    }`;
    }).join('')}
    pcT = mix( pcT, 1.5, pcFar );${q.partCap ? `
    pcT = min( pcT, mix( ${f4(th[0])}, ${f4(th[1])}, pow( t, ${f4(th[2])} ) ) + ${f4(q.partCap)} );` : ''}
    if ( pcF < pcT ) discard;
    #ifndef FLAT_SHADED
      vec3 pcFnW = normalize( ( vec4( vNormal, 0.0 ) * viewMatrix ).xyz );
    #else
      vec3 pcFnW = normalize( cross( dFdx( vPcW ), dFdy( vPcW ) ) );
    #endif
    pcFurA = mix( ${f4(ao[0])}, ${f4(ao[1])}, pow( t, ${f4(ao[2])} ) ) * ( 1.0 + ${f4(lu[2])} * ( 2.0 * pcL - 1.0 ) );
    pcFurG = pcG - pcFnW * dot( pcG, pcFnW );${clumps.map(([cf, ca, cs = 1], i) => {
      const S = `vec3( 1.0, ${f4(1 / cs)}, 1.0 )`;
      return `
    {
      vec4 cd = pcNoiseD( vPcW * ${S} * ${f4(cf)} + ${f4(71.0 + 9.3 * i)} );
      vec3 cg = ${f4(ca * cf)} * ( ${S} * cd.yzw );
      pcFurC += cg - pcFnW * dot( cg, pcFnW );
    }`;
    }).join('')}
  }
  diffuseColor.rgb *= pcFurA;`);
    // the tufts' sides: the normal tilted down the field's slope (world gradient per metre, scaled to the first octave)
    fs = fs.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  normal = normalize( normal - ( viewMatrix * vec4( ${f4((q.tilt ?? 0.6) / oct[0][0])} * pcFurG + pcFurC, 0.0 ) ).xyz );`);
  }
  const sh = q.sheen || [0.5, 1.4];
  fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_SHEEN
    material.sheenColor *= pcFurA * mix( ${f4(sh[0])}, ${f4(sh[1])}, pcFurT );
  #endif`);
  return { vs, fs, fsHead };
}

// the shell materials, one per base material (the shell count: main.js, 8 on the low quality tier, 14 elsewhere)
const SHELL_MATS = new WeakMap();
// the offset direction of the fur layers: the mean normal of the vertices sharing a position (object space), and in w
// the pile depth's share at the vertex -- 0.4 of the pad's local thickness (world metres, measured along the inward
// normal to the nearest opposite-facing vertex within reach; a thin pad -- the armrests' -- would otherwise have its
// root layers pushed out through the far face, dark), at most h0
function furDirs(g, mw, h0, obstacles = []) {
  const P = g.attributes.position, N = g.attributes.normal, n = P.count;
  const out = new Float32Array(4 * n), key = new Map(), acc = [], idx = new Int32Array(n);
  for (let i = 0; i < n; i++) {
    const k = `${P.getX(i).toFixed(6)},${P.getY(i).toFixed(6)},${P.getZ(i).toFixed(6)}`;
    let j = key.get(k);
    if (j === undefined) { j = acc.length; key.set(k, j); acc.push([0, 0, 0]); }
    const a = acc[j]; a[0] += N.getX(i); a[1] += N.getY(i); a[2] += N.getZ(i);
    idx[i] = j;
  }
  // world positions / normals of the welded points
  const m = acc.length, W = new Float32Array(3 * m), WN = new Float32Array(3 * m), D = new Float32Array(3 * m);
  const nm = new THREE.Matrix3().getNormalMatrix(mw), v = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    const j = idx[i];
    v.fromBufferAttribute(P, i).applyMatrix4(mw); W[3 * j] = v.x; W[3 * j + 1] = v.y; W[3 * j + 2] = v.z;
  }
  for (let j = 0; j < m; j++) {
    const a = acc[j], l = Math.hypot(a[0], a[1], a[2]) || 1;
    D[3 * j] = a[0] / l; D[3 * j + 1] = a[1] / l; D[3 * j + 2] = a[2] / l;
    v.set(D[3 * j], D[3 * j + 1], D[3 * j + 2]).applyMatrix3(nm).normalize();
    WN[3 * j] = v.x; WN[3 * j + 1] = v.y; WN[3 * j + 2] = v.z;
  }
  const C = 0.012, R = 2.5 * h0, cell = new Map(), ck = (x, y, z) => `${x},${y},${z}`;
  for (let j = 0; j < m; j++) {
    const kk = ck(Math.floor(W[3 * j] / C), Math.floor(W[3 * j + 1] / C), Math.floor(W[3 * j + 2] / C));
    let l = cell.get(kk); if (!l) cell.set(kk, l = []); l.push(j);
  }
  const share = new Float32Array(m);
  for (let j = 0; j < m; j++) {
    const px = W[3 * j], py = W[3 * j + 1], pz = W[3 * j + 2], nx = WN[3 * j], ny = WN[3 * j + 1], nz = WN[3 * j + 2];
    const cx = Math.floor(px / C), cy = Math.floor(py / C), cz = Math.floor(pz / C);
    let th = Infinity;
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++) {
      const l = cell.get(ck(cx + a, cy + b, cz + c));
      if (!l) continue;
      for (const q of l) {
        if (nx * WN[3 * q] + ny * WN[3 * q + 1] + nz * WN[3 * q + 2] > -0.2) continue;
        const dx = px - W[3 * q], dy = py - W[3 * q + 1], dz = pz - W[3 * q + 2];
        const al = dx * nx + dy * ny + dz * nz;
        if (al <= 0 || al > R) continue;
        const lat2 = dx * dx + dy * dy + dz * dz - al * al;
        if (lat2 < Math.max(9e-6, 0.64 * al * al) && al < th) th = al;
      }
    }
    share[j] = Math.min(1, Math.max(0.15, 0.4 * th / h0));
  }
  // the part's other surfaces under the pile (flight deck fix FDY r2: the pads sink into the leather cushion and wrap
  // its rolled front / the back's top -- 40 % of the fleece vertices have leather within 11 mm along the inward normal):
  // the root no deeper than 0.6 of the free depth to them, so the leather never shows through the pile's partings.
  // Their triangles near the fleece are sampled every ~3 mm (deterministic), hashed in 8 mm cells.
  if (obstacles.length) {
    let lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let j = 0; j < m; j++) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], W[3 * j + k]); hi[k] = Math.max(hi[k], W[3 * j + k]); }
    const pad = 1.3 * h0; lo = lo.map((x) => x - pad); hi = hi.map((x) => x + pad);
    const pts = [], a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), s2 = 9e-6;
    let seed = 12345;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
    for (const om of obstacles) {
      const og = om.geometry, OP = og.attributes.position, idx = og.index;
      om.updateWorldMatrix(true, false);
      const nt = idx ? idx.count / 3 : OP.count / 3;
      for (let t = 0; t < nt; t++) {
        const i0 = idx ? idx.getX(3 * t) : 3 * t, i1 = idx ? idx.getX(3 * t + 1) : 3 * t + 1, i2 = idx ? idx.getX(3 * t + 2) : 3 * t + 2;
        a.fromBufferAttribute(OP, i0).applyMatrix4(om.matrixWorld);
        b.fromBufferAttribute(OP, i1).applyMatrix4(om.matrixWorld);
        c.fromBufferAttribute(OP, i2).applyMatrix4(om.matrixWorld);
        if (Math.max(a.x, b.x, c.x) < lo[0] || Math.min(a.x, b.x, c.x) > hi[0] || Math.max(a.y, b.y, c.y) < lo[1] ||
            Math.min(a.y, b.y, c.y) > hi[1] || Math.max(a.z, b.z, c.z) < lo[2] || Math.min(a.z, b.z, c.z) > hi[2]) continue;
        const ux = b.x - a.x, uy = b.y - a.y, uz = b.z - a.z, vx = c.x - a.x, vy = c.y - a.y, vz = c.z - a.z;
        const ar = 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx);
        const ns = Math.min(4000, Math.max(1, Math.ceil(ar / s2)));
        for (let q = 0; q < ns; q++) {
          let r1 = ns === 1 ? 1 / 3 : rnd(), r2 = ns === 1 ? 1 / 3 : rnd();
          if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
          pts.push(a.x + r1 * ux + r2 * vx, a.y + r1 * uy + r2 * vy, a.z + r1 * uz + r2 * vz);
        }
      }
    }
    const np_ = pts.length / 3, OC = 0.008, ok = new Map();
    for (let q = 0; q < np_; q++) {
      const kk = ck(Math.floor(pts[3 * q] / OC), Math.floor(pts[3 * q + 1] / OC), Math.floor(pts[3 * q + 2] / OC));
      let l = ok.get(kk); if (!l) ok.set(kk, l = []); l.push(q);
    }
    const reach = 1.2 * h0, rc = Math.ceil(reach / OC);
    for (let j = 0; j < m; j++) {
      const px = W[3 * j], py = W[3 * j + 1], pz = W[3 * j + 2], nx = WN[3 * j], ny = WN[3 * j + 1], nz = WN[3 * j + 2];
      const cx = Math.floor(px / OC), cy = Math.floor(py / OC), cz = Math.floor(pz / OC);
      let free = Infinity;
      for (let ia = -rc; ia <= rc; ia++) for (let ib = -rc; ib <= rc; ib++) for (let ic = -rc; ic <= rc; ic++) {
        const l = ok.get(ck(cx + ia, cy + ib, cz + ic));
        if (!l) continue;
        for (const q of l) {
          const dx = pts[3 * q] - px, dy = pts[3 * q + 1] - py, dz = pts[3 * q + 2] - pz;
          const al = -(dx * nx + dy * ny + dz * nz);
          if (al <= 0 || al > reach || al >= free) continue;
          const lat2 = dx * dx + dy * dy + dz * dz - al * al;
          if (lat2 < Math.max(9e-6, 0.25 * al * al)) free = al;
        }
      }
      if (free < Infinity) share[j] = Math.min(share[j], Math.max(0.05, 0.6 * free / h0));
    }
  }
  for (let i = 0; i < n; i++) {
    const j = idx[i];
    out[4 * i] = D[3 * j]; out[4 * i + 1] = D[3 * j + 1]; out[4 * i + 2] = D[3 * j + 2]; out[4 * i + 3] = share[j];
  }
  return new THREE.BufferAttribute(out, 4);
}
// Shell fur on a mesh whose material carries the `fur` root flag (Model: the crew seats' sheepskin): the welded offset
// directions, an instanced copy of its geometry (the same buffers) and the shell material, drawn right after the mesh
// whenever the mesh draws with that material.  Returns true when the mesh got shells.
export function addFur(mesh, shells, obstacles = []) {
  const base = mesh.material, f = base && base.userData.pc12 && base.userData.pc12.fur;
  if (!f || f.role !== 'root' || !(shells >= 1)) return false;
  const g = mesh.geometry;
  mesh.updateWorldMatrix(true, false);
  if (!g.attributes.pcFurDir) g.setAttribute('pcFurDir', furDirs(g, mesh.matrixWorld, (f.h || [0.010])[0], obstacles));
  const sg = new THREE.InstancedBufferGeometry();
  sg.index = g.index;
  for (const k of Object.keys(g.attributes)) sg.setAttribute(k, g.attributes[k]);
  sg.instanceCount = shells;
  if (!g.boundingSphere) g.computeBoundingSphere();
  sg.boundingSphere = g.boundingSphere;
  let sm = SHELL_MATS.get(base);
  if (!sm) {
    sm = clonePatched(base, { fur: { ...f, role: 'shell', n: shells } });
    sm.side = THREE.FrontSide;
    SHELL_MATS.set(base, sm);
  }
  mesh.userData.pcFur = { geometry: sg, material: sm, base };
  mesh.onAfterRender = (renderer, scene, camera, geometry, material) => {
    const u = mesh.userData.pcFur;
    if (material === u.base && FUR.on && u.geometry.instanceCount > 0) renderer.renderBufferDirect(camera, scene, u.geometry, u.material, mesh, null);
  };
  return true;
}
// look development: rebuild the shells of the fur meshes under `root` from their base materials' current `fur` flags
// (after a patch of the root material), `shells` layers (default: as built)
export function refreshFur(root, shells = null) {
  const done = new Map();
  root.traverse((o) => {
    const u = o.isMesh && o.userData.pcFur;
    if (!u) return;
    const f = u.base.userData.pc12 && u.base.userData.pc12.fur;
    if (!f) return;
    const n = shells || u.geometry.instanceCount;
    let sm = done.get(u.base);
    if (!sm) {
      sm = clonePatched(u.base, { fur: { ...f, role: 'shell', n } });
      sm.side = THREE.FrontSide;
      SHELL_MATS.set(u.base, sm);
      done.set(u.base, sm);
    }
    u.material = sm;
    u.geometry.instanceCount = n;
  });
  return done.size;
}

export function installPatch(mat, extra = {}) {
  const f = { ...(mat.userData.pc12 || {}), ...extra };
  mat.userData.pc12 = f;
  const { paint, lining, glass, cabinGlass, collar, interior, cabinFill, back, grooves, stripes, fleece, rest, specKeep, reflDir, ao,
    leather, brush, grain, emisIn, specIn, sunIn, liningBase, probe, fur } = f;
  if (!paint && !lining && !glass && !collar && !interior && !back && !grooves && !stripes && !fleece && !ao && !leather && !brush && !grain && !fur) return mat;
  const restP = !!(rest && (collar || grooves || stripes || grain));
  const worldP = !!(fleece || leather || brush || fur);
  const physical = !!mat.isMeshPhysicalMaterial;
  if (glass) {
    // premultiplied output: src = diffuse * a + reflections, dst * (1 - a)
    mat.blending = THREE.CustomBlending;
    mat.blendEquation = THREE.AddEquation;
    mat.blendSrc = THREE.OneFactor;
    mat.blendDst = THREE.OneMinusSrcAlphaFactor;
    mat.blendSrcAlpha = THREE.OneFactor;
    mat.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
  }
  mat.onBeforeCompile = (sh) => {
    let vs = sh.vertexShader, fs = sh.fragmentShader;
    let fsHead = GLSL_BACKFACE;
    if (paint || restP) {
      // world Z (for the paint sweep) and the rest-pose world position (collar, grooves)
      vs = (paint ? 'varying float vPaintZ;\n' : '') + (restP ? GLSL_COLLAR_VS : '') + vs.replace('#include <project_vertex>',
        `#include <project_vertex>${paint ? '\n  vPaintZ = (modelMatrix * vec4(transformed, 1.0)).z;' : ''}${restP ? '\n  vRestP = (uRestM * vec4(transformed, 1.0)).xyz;' : ''}`);
      if (paint) fsHead += 'varying float vPaintZ;\n';
      if (restP) {
        sh.uniforms.uRestM = { value: new THREE.Matrix4().fromArray(rest) };
        fsHead += 'varying vec3 vRestP;\n';
      }
    }
    if (paint) {
      sh.uniforms.uPaintSweep = U.paintSweep;
      sh.uniforms.uPrimer = U.primer;
      fsHead += 'uniform float uPaintSweep;\nuniform vec3 uPrimer;\n';
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float paintK = smoothstep(-1.2, 1.2, uPaintSweep - vPaintZ);
  diffuseColor.rgb = mix(uPrimer, diffuseColor.rgb, paintK);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(0.66, roughnessFactor, paintK);
  metalnessFactor = mix(0.0, metalnessFactor, paintK);`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_CLEARCOAT
    material.clearcoat *= paintK;
  #endif`);
      }
    }
    if (collar) {
      const c = collar, P = c.polish;
      const v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(5)).join(', ')})`;
      fsHead += P ? GLSL_POLISH : '';
      // polish noise once per fragment (colour, roughness and the bump share it)
      const polishN = P ? `vec3 pcP = vRestP * ${v3(P.freq)}, pcDx = dFdx( pcP ), pcDy = dFdy( pcP );
  float pcFw = length( abs( pcDx ) + abs( pcDy ) );
  float pcPolishN = pcPolish( pcP, ${P.oct}, pcFw );\n  ` : '';
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  ${polishN}float colT = smoothstep(${(+c.tintX0).toFixed(4)}, ${(c.x0 - c.blend).toFixed(4)}, vRestP.z);
  float colK = smoothstep(${(c.x0 - c.blend / 2).toFixed(4)}, ${(c.x0 + c.blend / 2).toFixed(4)}, vRestP.z);
  vec3 pcTube = mix(${v3(c.base)}, ${v3(c.tint)}, colT);${P ? `
  pcTube = mix(pcTube, ${v3(c.tint)}, pcPolishN * ${(+P.tintMix).toFixed(3)});` : ''}
  diffuseColor.rgb = mix(pcTube, ${v3(c.cbase)}, colK);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(${P ? `mix(${(+P.rough[0]).toFixed(3)}, ${(+P.rough[1]).toFixed(3)}, pcPolishN)` : (+c.rough0).toFixed(3)}, ${(+c.rough1).toFixed(3)}, colK);
  metalnessFactor = mix(1.0, ${(+c.metal1).toFixed(3)}, colK);`);
      if (P && P.bump > 0) {
        // height = noise x bump_distance (m); Blender's bump 'strength' blends toward the bumped normal
        fs = fs.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  {
    float dhx = ( pcPolish( pcP + pcDx, ${P.oct}, pcFw ) - pcPolishN ) * ${(+P.dist).toFixed(4)};
    float dhy = ( pcPolish( pcP + pcDy, ${P.oct}, pcFw ) - pcPolishN ) * ${(+P.dist).toFixed(4)};
    normal = normalize( mix( normal, pcBump( - vViewPosition, normal, dhx, dhy, faceDirection ), ${(+P.bump).toFixed(3)} * ( 1.0 - colK ) ) );
  }`);
      }
      if (physical && c.spec1 !== 1) {
        // the collar's specular factor (KHR_materials_specular: F0 and F90)
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  material.specularColor *= mix(1.0, ${(+c.spec1).toFixed(3)}, colK);
  material.specularF90 *= mix(1.0, ${(+c.spec1).toFixed(3)}, colK);`);
      }
    }
    if (worldP) {
      // the world position (fleece, leather grain, brushed metal: world-space noise)
      vs = 'varying vec3 vPcW;\n' + vs.replace('#include <project_vertex>', '#include <project_vertex>\n  vPcW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      fsHead += 'varying vec3 vPcW;\n';
    }
    if ((worldP || grain) && !(collar && collar.polish)) fsHead += GLSL_POLISH;
    if (leather) {
      // a fine pebble grain: the fBm's surface-gradient bump (explicit forward differences) and a little roughness wander,
      // both faded out where a grain is sub-pixel
      const q = leather, f4 = (x) => (+x).toFixed(5);
      fs = fs.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  {
    vec3 pcLq = vPcW * ${f4(q.freq)}, pcLdx = dFdx( pcLq ), pcLdy = dFdy( pcLq );
    float pcLfw = length( abs( pcLdx ) + abs( pcLdy ) );
    float pcLn = pcFbm( pcLq, 2, pcLfw );
    float dhx = ( pcFbm( pcLq + pcLdx, 2, pcLfw ) - pcLn ) * ${f4(q.dist)};
    float dhy = ( pcFbm( pcLq + pcLdy, 2, pcLfw ) - pcLn ) * ${f4(q.dist)};
    float pcLk = 1.0 - smoothstep( 0.3, 0.9, pcLfw );
    normal = normalize( mix( normal, pcBump( - vViewPosition, normal, dhx, dhy, faceDirection ), ${f4(q.bump)} * pcLk ) );
    roughnessFactor = clamp( roughnessFactor + ${f4(q.rough)} * pcLk * ( 2.0 * pcLn - 1.0 ), 0.05, 1.0 );
  }`);
    }
    if (brush) {
      // brushed metal: streaky roughness (noise stretched along the brushing axis) and the anisotropic lobe turned to that
      // axis (three's tangent frame needs UVs these meshes do not carry: the axis is projected into the surface instead)
      const q = brush, f4 = (x) => (+x).toFixed(5), ax = q.axis || [1, 0, 0];
      const fr = [ax[0] ? 1 / q.len : 1 / q.w, ax[1] ? 1 / q.len : 1 / q.w, ax[2] ? 1 / q.len : 1 / q.w];
      // (flight deck fix r3 FDO3-01: + `spec` -- the same streaks in the reflection's strength, x 1 -+ spec, and a broader
      // `band` wander across the plate, x 1 -+ band over ~`bandLen` m: brushed metal's light / dark streaks; pcBrushK)
      const bl = q.bandLen || 0.12, bw = q.bandW || 0.25 * bl;
      fs = fs.replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  float pcBrushK = 1.0, pcBup = 0.0;
  {
    vec3 pcBq = vPcW * vec3( ${fr.map(f4).join(', ')} );
    float pcBfw = length( abs( dFdx( pcBq ) ) + abs( dFdy( pcBq ) ) );
    float pcBn = pcFbm( pcBq, 3, pcBfw );
    roughnessFactor = clamp( roughnessFactor + ${f4(q.rough)} * ( 2.0 * pcBn - 1.0 ), 0.05, 1.0 );
    vec3 pcBb = vPcW * vec3( ${[ax[0] ? 1 / bl : 1 / bw, ax[1] ? 1 / bl : 1 / bw, ax[2] ? 1 / bl : 1 / bw].map(f4).join(', ')} );
    float pcBbn = pcFbm( pcBb + 5.3, 2, length( abs( dFdx( pcBb ) ) + abs( dFdy( pcBb ) ) ) );
    // (the fBm's middle range 0.3 .. 0.7 stretched to -1 .. 1, as pcPolish)
    pcBrushK = ( 1.0 + ${f4(q.spec || 0)} * ( 2.0 * clamp( ( pcBn - 0.3 ) / 0.4, 0.0, 1.0 ) - 1.0 ) )
             * ( 1.0 + ${f4(q.band || 0)} * ( 2.0 * clamp( ( pcBbn - 0.3 ) / 0.4, 0.0, 1.0 ) - 1.0 ) );${q.up ? `
    {
      // \`up\` [n0, n1, + roughness, streaks kept]: the faces turned up (world normal y over n0 .. n1) a satin, isotropic
      // finish with weaker streaks -- the palm tray (fix r3: brushed like the sub-panels it mirrored the apron behind the
      // aircraft as a frosted glass, 141 against P1046408's ~129, a soft gradient there)
      #ifndef FLAT_SHADED
        vec3 pcBnW = normalize( ( vec4( vNormal, 0.0 ) * viewMatrix ).xyz ) * ( gl_FrontFacing ? 1.0 : - 1.0 );
      #else
        vec3 pcBnW = normalize( cross( dFdx( vPcW ), dFdy( vPcW ) ) );
      #endif
      pcBup = smoothstep( ${f4(q.up[0])}, ${f4(q.up[1])}, pcBnW.y );
      roughnessFactor = clamp( roughnessFactor + ${f4(q.up[2])} * pcBup, 0.05, 1.0 );
      pcBrushK = mix( pcBrushK, 1.0 + ${f4(q.up[3])} * ( pcBrushK - 1.0 ), pcBup );
    }` : ''}
  }`).replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_ANISOTROPY
  material.alphaT = mix( material.alphaT, pow2( material.roughness ), pcBup );
  {
    vec3 pcAx = normalize( ( viewMatrix * vec4( ${ax.map((x) => (+x).toFixed(3)).join(', ')}, 0.0 ) ).xyz );
    vec3 pcT = pcAx - normal * dot( pcAx, normal );
    float pcTl = length( pcT );
    pcT = pcTl > 1e-4 ? pcT / pcTl : normalize( cross( normal, vec3( 0.0, 1.0, 0.0 ) ) + 1e-4 );
    material.anisotropyT = pcT;
    material.anisotropyB = cross( normal, pcT );
  }
  #endif`);
    }
    if (grain && restP) {
      // veneer figure (lookdev _veneer_grain): fBm of the rest position stretched along the vertical (scale: glTF X, Y, Z
      // per metre), along the station where the surface faces up or down (table tops); the noise's middle range maps to
      // 1 -+ amp on the albedo, the roughness -+ rough; octaves finer than a pixel fade out (no sparkle at a distance)
      const q = grain, f4 = (x) => (+x).toFixed(4);
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  vec3 pcGn = normalize( cross( dFdx( vRestP ), dFdy( vRestP ) ) );
  float pcGup = smoothstep( 0.6, 0.8, abs( pcGn.y ) );
  vec3 pcGq = mix( vRestP * vec3( ${f4(q.scale[0])}, ${f4(q.scale[1])}, ${f4(q.scale[2])} ), vRestP.zyx * vec3( ${f4(q.scale[1])}, ${f4(q.scale[0])}, ${f4(q.scale[0])} ), pcGup );
  float pcGfw = length( abs( dFdx( pcGq ) ) + abs( dFdy( pcGq ) ) );
  float pcGr = clamp( ( pcFbm( pcGq, ${q.oct | 0}, pcGfw ) - 0.3 ) / 0.4, 0.0, 1.0 );
  diffuseColor.rgb *= 1.0 + ${f4(q.amp)} * ( 2.0 * pcGr - 1.0 );`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = clamp( roughnessFactor + ${f4(q.rough)} * ( 2.0 * pcGr - 1.0 ), 0.04, 1.0 );`);
    }
    if (fur) ({ vs, fs, fsHead } = furPatch(fur, vs, fs, fsHead));
    if (fleece) {
      // sheepskin pile (review r4 INT8-04): band-limited fBm clumps in world space darken / lighten the albedo and bump
      // the normal (the stacks' surface-gradient bump, explicit forward differences); fades out where a tuft is sub-pixel
      const q = fleece, f4 = (x) => (+x).toFixed(4);
      if (q.locks) {
        // flight deck fix FDY r1 (FDY-O1-01 / FIDY1-02: r5's curly worms read as veined marble / crumpled foil -- thin
        // bright ridges on a flat field, about half the photos' local contrast): LOCKS.  Each jittered cell of a 3-D
        // lattice carries one lock: an elongated soft blob in the surface's tangent plane (half-length `len` [min, max]
        // cells, half-width `asp` of that, tapering toward its tip, bent sideways), laid along the pile's flow (down the
        // vertical faces, forward over the tops) turned by up to +-`jit` rad, of random height; the TOP lock wins where
        // they overlap (max, not a sum), so the pile is a mat of overlapping locks, each lit toward its tip and shaded at
        // its root (`tipK`), with a dark seam where two meet (`gap`: the edge term's width; `seam` its darkening) and the
        // dark between them where none reaches.  Layers `locks`: [freq per m, albedo lo, hi, bump depth m, len min,
        // len max, asp, jit, tipK, gap, seam]; the low-frequency `lock` groups, `fibre` streaks, `rim` and `sheen` as the
        // pile mode.  Each layer fades to its mean where a cell is sub-pixel.  (P1046410 / 09 / 08: 10-20 mm locks, 5-8
        // mm wide, lit tips over dark gaps; the lab out/tmp/fdy_fix_r1/lab)
        const LL = q.locks, fl = q.flat || [0.55, 0.85];
        const fib = q.fibre, lk = q.lock, rimq = q.rim, shq = q.sheen || [1, 1], lb = q.lumpB;
        const LS = q.lockShape || [0.25, 1.0, 0.0, 6.0, 0.0, 0.0];   // [tip taper, bend, strand contrast, strands across, swirl rad, ragged edge]
        fsHead += `vec4 pcLocks( vec3 q, vec3 n, vec3 flow, float lmin, float lmax, float asp, float jit, float gk ) {
  vec3 e1 = flow - n * dot( flow, n );
  e1 = dot( e1, e1 ) > 1e-4 ? normalize( e1 ) : normalize( cross( n, vec3( 0.0, 0.0, 1.0 ) ) + 1e-4 );
  vec3 e2 = cross( n, e1 );
  float sw = ${f4(LS[4] ?? 0)} * ( 2.0 * pcNoise( q * 0.12 + 3.3 ) - 1.0 );     // the pile's flow swirls
  vec3 e1s = cos( sw ) * e1 + sin( sw ) * e2; e2 = cross( n, e1s ); e1 = e1s;
  vec3 i = floor( q ), f = fract( q ); float h1 = 0.0, h2 = 0.0, s1 = 0.0, t1 = 0.0;
  for ( int z = -1; z <= 1; z ++ ) for ( int y = -1; y <= 1; y ++ ) for ( int x = -1; x <= 1; x ++ ) {
    vec3 g = vec3( float( x ), float( y ), float( z ) ), c = i + g;
    vec3 r = f - g - vec3( pcHash( c ), pcHash( c + 17.13 ), pcHash( c + 31.71 ) );
    float ang = jit * ( 2.0 * pcHash( c + 5.7 ) - 1.0 );
    vec3 d = cos( ang ) * e1 + sin( ang ) * e2, dn = cross( n, d );
    float L = mix( lmin, lmax, pcHash( c + 2.2 ) );
    float sa = dot( r, d ) / L;
    float bend = ${f4(LS[1])} * ( pcHash( c + 8.3 ) - 0.5 );
    float w = L * asp * mix( 0.7, 1.3, pcHash( c + 6.6 ) ) * ( 1.0 - ${f4(LS[0])} * clamp( sa, 0.0, 1.0 ) );
    float t = ( dot( r, dn ) - bend * L * sa * sa ) / w;
    t += ${f4(LS[5] ?? 0)} * ( pcNoise( q * 3.1 + c ) - 0.5 );                  // ragged lock edges
    float on = dot( r, n );
    float h = mix( 0.55, 1.0, pcHash( c + 3.1 ) ) * exp( - 1.6 * sa * sa - 1.8 * t * t - 2.5 * on * on );
    if ( h > h1 ) { h2 = h1; h1 = h; s1 = sa; t1 = t + 6.2832 * pcHash( c + 4.4 ); } else if ( h > h2 ) { h2 = h; }
  }
  return vec4( h1, s1, smoothstep( 0.0, gk, h1 - h2 ), t1 );
}
`;
        const one = (ax, sv) => LL.map(([fq, lo, hi, dep, l0, l1, asp, jit, tipK, gk, seam, mode = 0], li) => {
          const A = `${f4(l0)}, ${f4(l1)}, ${f4(asp)}, ${f4(jit)}, ${f4(gk)}`;
          const flow = ax === 0 ? 'vec3( 0.0, -1.0, 0.0 )' : 'vec3( 0.0, 0.0, -1.0 )';
          const mean = lo + (hi - lo) * 0.62;
          if (mode === 1) {
            // (FDY r2) a SLIT layer: thin, bent, dark partings in the pile -- each cell's lock drawn as a crevice (the
            // albedo down to `lo` over its core, darkest toward one end by `tipK`: a comma; the height a groove of
            // `dep`), the pile lit everywhere else (`hi`): the photos' short dark slits where the curls part, on a
            // light mat (P1046408 / 09 / 10 at 1-3 px/mm)
            const meanS = hi - (hi - lo) * 0.12;
            return `
    {
      vec3 pq = vPcW * ${f4(fq)} + ${f4(2.1 + 3.3 * ax + 7.9 * li)};
      vec3 pdx = dFdx( pq ), pdy = dFdy( pq );
      float fw = length( abs( pdx ) + abs( pdy ) ), k = 1.0 - smoothstep( 0.3, 0.8, fw );
      vec4 t0 = pcLocks( pq, pcFnW, ${flow}, ${A} ), t1 = pcLocks( pq + pdx, pcFnW, ${flow}, ${A} ),
           t2 = pcLocks( pq + pdy, pcFnW, ${flow}, ${A} );
      float sl = smoothstep( ${f4(gk)}, ${f4(Math.min(0.98, gk + seam))}, t0.x );${q.slitMod ? `
      sl *= mix( ${f4(q.slitMod[1])}, ${f4(q.slitMod[2])}, smoothstep( 0.25, 0.75, pcNoise( pq * ${f4(q.slitMod[0])} + 5.5 ) ) );` : ''}
      float a = mix( ${f4(hi)}, ${f4(lo)}, sl * mix( ${f4(1 - tipK)}, 1.0, smoothstep( -1.0, 1.0, t0.y ) ) );
      ${sv}M *= mix( ${f4(meanS)}, a, k );
      ${sv}D -= k * ${f4(dep)} * vec2( t1.x - t0.x, t2.x - t0.x );
    }`;
          }
          return `
    {
      vec3 pq = vPcW * ${f4(fq)} + ${f4(2.1 + 3.3 * ax + 7.9 * li)};
      vec3 pdx = dFdx( pq ), pdy = dFdy( pq );
      float fw = length( abs( pdx ) + abs( pdy ) ), k = 1.0 - smoothstep( 0.3, 0.8, fw );
      vec4 t0 = pcLocks( pq, pcFnW, ${flow}, ${A} ), t1 = pcLocks( pq + pdx, pcFnW, ${flow}, ${A} ),
           t2 = pcLocks( pq + pdy, pcFnW, ${flow}, ${A} );
      float h0 = t0.x * mix( 0.55, 1.0, t0.z ), h1 = t1.x * mix( 0.55, 1.0, t1.z ), h2 = t2.x * mix( 0.55, 1.0, t2.z );
      float cov = smoothstep( 0.03, 0.55, t0.x );
      float tip = mix( ${f4(1 - tipK)}, ${f4(1 + 0.5 * tipK)}, smoothstep( -1.1, 1.0, t0.y ) );
      float a = mix( ${f4(lo)}, ${f4(hi)}, cov * mix( ${f4(1 - seam)}, 1.0, t0.z ) ) * mix( 1.0, tip, cov );${LS[2] > 0 ? `
      a *= 1.0 - ${f4(LS[2])} * cov * ( 1.0 - smoothstep( 0.3, 0.8, ${f4(LS[3])} * fw ) ) * ( 0.5 + 0.5 * sin( ${f4(LS[3])} * t0.w ) );` : ''}
      ${sv}M *= mix( ${f4(mean)}, a, k );
      ${sv}D += k * ${f4(dep)} * vec2( h1 - h0, h2 - h0 );${li === 0 ? `
      ${sv}T = mix( 0.5, cov * smoothstep( -1.0, 1.0, t0.y ), k );` : ''}
    }`;
        }).join('');
        fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float pcFleeceM = 1.0, pcFTip = 0.5;
  vec2 pcFdh = vec2( 0.0 );
  {
    #ifndef FLAT_SHADED
      vec3 pcFnW = normalize( ( vec4( vNormal, 0.0 ) * viewMatrix ).xyz ) * ( gl_FrontFacing ? 1.0 : - 1.0 );
    #else
      vec3 pcFnW = normalize( cross( dFdx( vPcW ), dFdy( vPcW ) ) );
    #endif
    float pcFwH = smoothstep( ${f4(fl[0])}, ${f4(fl[1])}, abs( pcFnW.y ) );
    float pcVM = 1.0, pcVT = 0.5, pcHM = 1.0, pcHT = 0.5;
    vec2 pcVD = vec2( 0.0 ), pcHD = vec2( 0.0 );
    if ( pcFwH < 0.999 ) {${one(0, 'pcV')}
    }
    if ( pcFwH > 0.001 ) {${one(1, 'pcH')}
    }
    pcFleeceM = mix( pcVM, pcHM, pcFwH );
    pcFdh = mix( pcVD, pcHD, pcFwH );
    pcFTip = mix( pcVT, pcHT, pcFwH );
  }${fib ? `
  {
    vec3 fq = vPcW * vec3( ${f4(fib[0])}, ${f4(fib[1])}, ${f4(fib[0])} ) + 9.1;
    float ffw = length( abs( dFdx( fq ) ) + abs( dFdy( fq ) ) );
    pcFleeceM *= 1.0 + ${f4(fib[2])} * ( 1.0 - smoothstep( 0.3, 0.8, ffw ) ) * ( 2.0 * pcFbm( fq, 2, ffw ) - 1.0 );
  }` : ''}${lk ? `
  {
    vec3 pcCq = vPcW * ${f4(lk[0])} + 11.7;
    float pcCn = pcFbm( pcCq, 2, length( abs( dFdx( pcCq ) ) + abs( dFdy( pcCq ) ) ) );
    pcFleeceM *= 1.0 + ${f4(lk[1])} * ( 2.0 * smoothstep( 0.2, 0.8, pcCn ) - 1.0 );
  }` : ''}${lb ? `
  {
    // soft LUMPS (FDY r2, FDY-O2-01 / FIDY2-01): the pile's depth from cm-scale matted lumps in the bump -- the photos'
    // shading comes from soft lumps, not from lit lock tips; lumpB [freq per m, depth m, albedo share]
    vec3 pcLq = vPcW * ${f4(lb[0])} + 23.9;
    vec3 pcLx = dFdx( pcLq ), pcLy = dFdy( pcLq );
    float pcLw = length( abs( pcLx ) + abs( pcLy ) );
    float pcL0 = pcFbm( pcLq, 2, pcLw ), pcL1 = pcFbm( pcLq + pcLx, 2, pcLw ), pcL2 = pcFbm( pcLq + pcLy, 2, pcLw );
    pcFdh += ${f4(lb[1])} * vec2( pcL1 - pcL0, pcL2 - pcL0 ) * ( 1.0 - smoothstep( 0.3, 0.8, pcLw ) );
    pcFleeceM *= 1.0 + ${f4(lb[2] ?? 0)} * ( 2.0 * pcL0 - 1.0 );
  }` : ''}${rimq ? `
  {
    #ifndef FLAT_SHADED
      vec3 pcVn = normalize( vNormal );
    #else
      vec3 pcVn = normalize( cross( dFdx( vViewPosition ), dFdy( vViewPosition ) ) );
    #endif
    float pcNv = abs( dot( pcVn, normalize( vViewPosition ) ) );
    pcFleeceM *= 1.0 + ${f4(rimq[1])} * ( 1.0 - smoothstep( 0.0, ${f4(rimq[0])}, pcNv ) );
  }` : ''}
  diffuseColor.rgb *= pcFleeceM;`)
          .replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_SHEEN
    material.sheenColor *= pcFleeceM * mix( ${f4(shq[0])}, ${f4(shq[1])}, pcFTip );
  #endif`)
          .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  normal = normalize( mix( normal, pcBump( - vViewPosition, normal, pcFdh.x, pcFdh.y, faceDirection ), ${f4(q.bump ?? 1)} ) );`);
      } else if (q.pile) {
        // flight deck fix r5 (FDO4-01 / FID-FD4-01: the round Worley curls of r1-r3 read as printed lichen / stone -- every
        // tuft an even dome, the borders between them one continuous dark network): a curly PILE.  `tufts`: layers [freq
        // across per m, albedo lo, hi, bump depth m, gap darkening, curl depth, curl arms, curl twist / warp, loop share,
        // loop radius / worm sharpness, loop width].  A layer with arms < 0 is CURLY WORMS (the ridges of a domain-warped
        // smooth noise, two octaves: short, bent, interlaced bright strands with dark between them -- the curls of P1046408 /
        // 09 / 10's pile at 4-6 mm; `twist` the warp in cells, `loop radius` the ridge sharpness: pow, or smoothstep from
        // its negative); otherwise TUFTS (Worley cells of random height, `hgt` [lo, hi] -- a short one sits in its
        // neighbours' shade, so the dark between them is broken, not a crackle net --, a soft round top, `dome`, or a loop,
        // and a spiral curl of `arms`).  The look-dev (out/tmp/fd_fix_r5/lab: the crew seats alone in a page, ~30 s a try)
        // tried 17-60 mm tufts and locks (rock / crazy paving), spiral curls and loops (scales, craters), contour whorls
        // (marble, caustics), fat worms (leopard print): the photos' pile is 4-6 mm curls packed tight, the worms at ~200 / m.
        // The cells are domain-warped (`warp`), the whole stretched along the pile's flow (down the vertical faces -- world
        // -Y -- and forward over the flat tops, glTF -Z, cross-faded by the normal's |y| over `flat`; `stretch` < 1
        // elongates it); `lock` [freq per m, amplitude]: matted groups (soft fBm on the albedo); `fibre` [across, along per
        // m, amp]: fine streaks; `rim` [n.v, lift] the fibre tips along the silhouette; `sheen` [crevice, tip] the glow on
        // the tips.  Each layer fades to its mean where it is sub-pixel.
        const TL = q.tufts, fl = q.flat || [0.55, 0.85], hg = q.hgt || [0.5, 1.0];
        const fib = q.fibre, lk = q.lock, rimq = q.rim, shq = q.sheen || [1, 1], st = q.stretch ?? 0.7, wp = q.warp ?? 0.45;
        const gapE = q.gapE ?? 0.3, domeE = q.dome ?? 1.0;
        fsHead += `vec3 pcPile( vec3 q, vec3 n, float gk, float arms, float twist, float loop, float lr, float lw ) {
  q += ${f4(wp)} * ( vec3( pcNoise( q * 0.45 + 1.7 ), pcNoise( q * 0.45 + 9.2 ), pcNoise( q * 0.45 + 4.4 ) ) - 0.5 );
  vec3 i = floor( q ), f = fract( q ); float d1 = 8.0, d2 = 8.0; vec3 r1 = vec3( 0.0 ), c1 = vec3( 0.0 );
  for ( int z = -1; z <= 1; z ++ ) for ( int y = -1; y <= 1; y ++ ) for ( int x = -1; x <= 1; x ++ ) {
    vec3 g = vec3( float( x ), float( y ), float( z ) ), c = i + g;
    vec3 r = g + vec3( pcHash( c ), pcHash( c + 17.13 ), pcHash( c + 31.71 ) ) - f;
    float d = dot( r, r );
    if ( d < d1 ) { d2 = d1; d1 = d; r1 = r; c1 = c; } else if ( d < d2 ) { d2 = d; }
  }
  d1 = sqrt( d1 ); d2 = sqrt( d2 );
  float hc = mix( ${f4(hg[0])}, ${f4(hg[1])}, pcHash( c1 + 3.1 ) );
  float dome = 1.0 - smoothstep( 0.0, ${f4(domeE)}, d1 );
  float gap = smoothstep( 0.0, ${f4(gapE)}, d2 - d1 );
  vec3 sd = normalize( vec3( pcHash( c1 + 5.7 ), pcHash( c1 + 8.3 ), pcHash( c1 + 1.9 ) ) - 0.5 + 1e-3 );
  vec3 e1 = normalize( cross( n, sd ) + 1e-4 ), e2 = cross( n, e1 );
  float ang = atan( dot( r1, e2 ), dot( r1, e1 ) ) * ( pcHash( c1 + 7.7 ) > 0.5 ? 1.0 : - 1.0 );
  float curl = 0.5 + 0.5 * sin( arms * ang + 6.2832 * ( twist * d1 + pcHash( c1 + 2.2 ) ) );
  // a share of the tufts are LOOPS (boucle: a ring of fibre about the tuft's centre at lr of a cell, lw wide) -- lit
  // through the bump they draw the crescent highlights of a curly pile
  float ring = exp( - pow( ( d1 - lr ) / lw, 2.0 ) );
  float shape = mix( dome, ring, step( pcHash( c1 + 9.9 ), loop ) );
  float h = hc * ( 0.35 + 0.65 * shape ) * mix( 1.0 - gk, 1.0, gap );
  return vec3( h, curl, hc * shape );
}
// curly worms: the ridges of a domain-warped smooth noise (two octaves) -- short, bent, interlaced bright strands
// with dark between them, the curls of a dense boucle pile at a few mm
vec3 pcWorm( vec3 q, float wv, float sharp ) {
  vec3 w = q + wv * ( vec3( pcNoise( q * 0.6 + 1.7 ), pcNoise( q * 0.6 + 9.2 ), pcNoise( q * 0.6 + 4.4 ) ) - 0.5 );
  float r1 = 1.0 - abs( 2.0 * pcNoise( w ) - 1.0 );
  float r2 = 1.0 - abs( 2.0 * pcNoise( w * 2.13 + 5.1 ) - 1.0 );
  float r = sharp > 0.0 ? max( pow( r1, sharp ), 0.85 * pow( r2, sharp ) ) : smoothstep( - sharp, 1.0, max( r1, 0.9 * r2 ) );
  float mass = smoothstep( 0.2, 0.8, pcNoise( q * 0.3 + 6.1 ) );
  return vec3( r * ( 0.6 + 0.4 * mass ), r, mass );
}
`;
        const one = (ax, sv) => TL.map(([fq, lo, hi, dep, gk, cd, arms, tw, lp = 0, lr = 0.35, lw = 0.18], li) => {
          const s = ax === 0 ? [fq, fq * st, fq] : [fq, fq, fq * st];
          const H = (t) => `( ${t}.x - ${f4(0.25 * cd)} * ( 1.0 - ${t}.y ) * ${t}.z )`;
          const A = `${f4(gk)}, ${f4(arms)}, ${f4(tw)}, ${f4(lp)}, ${f4(lr)}, ${f4(lw)}`;
          return `
    {
      vec3 pq = vPcW * vec3( ${s.map(f4).join(', ')} ) + ${f4(2.1 + 3.3 * ax + 7.9 * li)};
      vec3 pdx = dFdx( pq ), pdy = dFdy( pq );
      float fw = length( abs( pdx ) + abs( pdy ) ), k = 1.0 - smoothstep( 0.3, 0.8, fw );
      ${arms < 0 ? `vec3 t0 = pcWorm( pq, ${f4(tw)}, ${f4(lr)} ), t1 = pcWorm( pq + pdx, ${f4(tw)}, ${f4(lr)} ), t2 = pcWorm( pq + pdy, ${f4(tw)}, ${f4(lr)} );` : `vec3 t0 = pcPile( pq, pcFnW, ${A} ), t1 = pcPile( pq + pdx, pcFnW, ${A} ), t2 = pcPile( pq + pdy, pcFnW, ${A} );`}
      float h0 = ${H('t0')}, h1 = ${H('t1')}, h2 = ${H('t2')};
      float a = mix( ${f4(lo)}, ${f4(hi)}, t0.x ) * ( 1.0 - ${f4(cd)} * ( 1.0 - t0.y ) * t0.z );
      ${sv}M *= mix( ${f4((0.5 * (lo + hi)) * (1 - 0.3 * cd))}, a, k );
      ${sv}D += k * ${f4(dep)} * vec2( h1 - h0, h2 - h0 );${li === 0 ? `
      ${sv}T = mix( 0.5, t0.z, k );` : ''}
    }`;
        }).join('');
        fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float pcFleeceM = 1.0, pcFTip = 0.5;
  vec2 pcFdh = vec2( 0.0 );
  {
    #ifndef FLAT_SHADED
      vec3 pcFnW = normalize( ( vec4( vNormal, 0.0 ) * viewMatrix ).xyz ) * ( gl_FrontFacing ? 1.0 : - 1.0 );
    #else
      vec3 pcFnW = normalize( cross( dFdx( vPcW ), dFdy( vPcW ) ) );
    #endif
    float pcFwH = smoothstep( ${f4(fl[0])}, ${f4(fl[1])}, abs( pcFnW.y ) );
    float pcVM = 1.0, pcVT = 0.5, pcHM = 1.0, pcHT = 0.5;
    vec2 pcVD = vec2( 0.0 ), pcHD = vec2( 0.0 );
    if ( pcFwH < 0.999 ) {${one(0, 'pcV')}
    }
    if ( pcFwH > 0.001 ) {${one(1, 'pcH')}
    }
    pcFleeceM = mix( pcVM, pcHM, pcFwH );
    pcFdh = mix( pcVD, pcHD, pcFwH );
    pcFTip = mix( pcVT, pcHT, pcFwH );
  }${fib ? `
  {
    vec3 fq = vPcW * vec3( ${f4(fib[0])}, ${f4(fib[1])}, ${f4(fib[0])} ) + 9.1;
    float ffw = length( abs( dFdx( fq ) ) + abs( dFdy( fq ) ) );
    pcFleeceM *= 1.0 + ${f4(fib[2])} * ( 1.0 - smoothstep( 0.3, 0.8, ffw ) ) * ( 2.0 * pcFbm( fq, 2, ffw ) - 1.0 );
  }` : ''}${lk ? `
  {
    vec3 pcCq = vPcW * ${f4(lk[0])} + 11.7;
    float pcCn = pcFbm( pcCq, 2, length( abs( dFdx( pcCq ) ) + abs( dFdy( pcCq ) ) ) );
    pcFleeceM *= 1.0 + ${f4(lk[1])} * ( 2.0 * smoothstep( 0.2, 0.8, pcCn ) - 1.0 );
  }` : ''}${rimq ? `
  {
    #ifndef FLAT_SHADED
      vec3 pcVn = normalize( vNormal );
    #else
      vec3 pcVn = normalize( cross( dFdx( vViewPosition ), dFdy( vViewPosition ) ) );
    #endif
    float pcNv = abs( dot( pcVn, normalize( vViewPosition ) ) );
    pcFleeceM *= 1.0 + ${f4(rimq[1])} * ( 1.0 - smoothstep( 0.0, ${f4(rimq[0])}, pcNv ) );
  }` : ''}
  diffuseColor.rgb *= pcFleeceM;`)
          .replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_SHEEN
    material.sheenColor *= pcFleeceM * mix( ${f4(shq[0])}, ${f4(shq[1])}, pcFTip );
  #endif`)
          .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  normal = normalize( mix( normal, pcBump( - vViewPosition, normal, pcFdh.x, pcFdh.y, faceDirection ), ${f4(q.bump ?? 1)} ) );`);
      } else if (q.ridge) {
        // flight deck fix r1 (FDO1-02 / FID-FD1-06): a curly pile in `layers` [freq per m, lo, hi, dist] -- round tufts
        // ~1 / freq across at the albedo's `hi`, the crevices between them (Worley cells) down to `lo`; each layer faded to
        // its mean where it is sub-pixel, the crevices pressing the normal in by `dist`; the look L6 clouds (0.4 .. 1.1 at
        // 12-20 mm value noise) read as blue-grey camouflage, a ridged-noise try as marble veins
        // (flight deck fix r2b: `edge` -- the crevice term's smoothstep over the F1 distance, default 0.45 .. 0.85: thin
        // dark borders; a wider, softer 0.25 .. 0.8 lets a coarse layer read as soft lumps, not a vein network -- and
        // `rm` its mean, 0.26 / 0.49 for those two, the faded layer's level)
        const [E0, E1] = q.edge || [0.45, 0.85];
        const L = q.layers, RM = q.rm ?? 0.26;      // the crevice term's mean (Worley F1, smoothstep E0 .. E1)
        // (flight deck fix r2 FDO2-05: `stretch` -- per glTF axis -- elongates the tufts and `warp` bends their cells,
        // so the pile reads as curls of varying size and not as equal round blobs)
        const st = q.stretch || [1, 1, 1], wp = q.warp || 0;
        const lay = L.map(([fq, lo, hi], i) => `
  {
    vec3 pq = vPcW * vec3( ${st.map((x) => f4(x * fq)).join(', ')} ) + ${f4(3.7 * i)};${wp ? `
    pq += ${f4(wp)} * vec3( sin( 1.7 * pq.y + 0.3 ), sin( 1.3 * pq.z + 1.1 ), sin( 1.9 * pq.x + 2.3 ) );` : ''}
    vec3 pdx = dFdx( pq ), pdy = dFdy( pq );
    float fw = length( abs( pdx ) + abs( pdy ) ), k = 1.0 - smoothstep( 0.3, 0.8, fw );
    float r0 = pcFRidge( pq ), r1 = pcFRidge( pq + pdx ), r2 = pcFRidge( pq + pdy );
    pcFleeceM *= mix( ${f4(hi - (hi - lo) * RM)}, mix( ${f4(hi)}, ${f4(lo)}, r0 ), k );
    pcFdh -= k * ${f4(L[i][3] ?? q.dist)} * vec2( r1 - r0, r2 - r0 );
  }`).join('');
        // the crevices between round tufts: Worley F1 (distance to the nearest jittered feature point, cell units), dark
        // where it is far from every tuft centre
        fsHead += `float pcFRidge( vec3 p ) {
  vec3 i = floor( p ), f = fract( p ); float d = 8.0;
  for ( int z = -1; z <= 1; z ++ ) for ( int y = -1; y <= 1; y ++ ) for ( int x = -1; x <= 1; x ++ ) {
    vec3 g = vec3( float( x ), float( y ), float( z ) ), c = i + g;
    vec3 r = g + vec3( pcHash( c ), pcHash( c + 17.13 ), pcHash( c + 31.71 ) ) - f;
    d = min( d, dot( r, r ) );
  }
  return smoothstep( ${f4(E0)}, ${f4(E1)}, sqrt( d ) );
}\n`;
        // (flight deck fix r3 FDO3-03 / FID-FD3-04: an even small-curl 'cauliflower' with hard outlines) `clump` [freq per
        // m, amplitude]: a soft low-frequency field (2-4 cm) grouping the tufts, x 1 -+ amplitude on the albedo; `rim`
        // [n.v below which, lift]: the pile's fuzzy silhouette -- the albedo lightened toward the outline, where the eye
        // looks along the fibres' tips
        const cl = q.clump, rimq = q.rim;
        fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float pcFleeceM = 1.0;
  vec2 pcFdh = vec2( 0.0 );${lay}${cl ? `
  {
    vec3 pcCq = vPcW * ${f4(cl[0])} + 11.7;
    float pcCn = pcFbm( pcCq, 2, length( abs( dFdx( pcCq ) ) + abs( dFdy( pcCq ) ) ) );
    pcFleeceM *= 1.0 + ${f4(cl[1])} * ( 2.0 * smoothstep( 0.25, 0.75, pcCn ) - 1.0 );
  }` : ''}${rimq ? `
  {
    #ifndef FLAT_SHADED
      vec3 pcVn = normalize( vNormal );
    #else
      vec3 pcVn = normalize( cross( dFdx( vViewPosition ), dFdy( vViewPosition ) ) );
    #endif
    float pcNv = abs( dot( pcVn, normalize( vViewPosition ) ) );
    pcFleeceM *= 1.0 + ${f4(rimq[1])} * ( 1.0 - smoothstep( 0.0, ${f4(rimq[0])}, pcNv ) );
  }` : ''}
  diffuseColor.rgb *= pcFleeceM;`)
          // the sheen lobe (the pile's soft glow) follows the same curls: unmodulated, it laid a uniform blue-grey veil
          // over the shaded fleece (sd ~1 level where the photos show 10-18)
          .replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_SHEEN
    material.sheenColor *= pcFleeceM * pcFleeceM;
  #endif`)
          .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  normal = normalize( mix( normal, pcBump( - vViewPosition, normal, pcFdh.x, pcFdh.y, faceDirection ), ${f4(q.bump)} ) );`);
      } else {
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  vec3 pcFq = vPcW * ${f4(q.freq)}, pcFdx = dFdx( pcFq ), pcFdy = dFdy( pcFq );
  float pcFfw = length( abs( pcFdx ) + abs( pcFdy ) );
  float pcFn = pcFbm( pcFq, ${q.oct | 0}, pcFfw );
  diffuseColor.rgb *= mix( ${f4(q.lo)}, ${f4(q.hi)}, pow( clamp( pcFn, 0.0, 1.0 ), ${f4(q.gamma ?? 1)} ) );`)
        .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  {
    float dhx = ( pcFbm( pcFq + pcFdx, ${q.oct | 0}, pcFfw ) - pcFn ) * ${f4(q.dist)};
    float dhy = ( pcFbm( pcFq + pcFdy, ${q.oct | 0}, pcFfw ) - pcFn ) * ${f4(q.dist)};
    normal = normalize( mix( normal, pcBump( - vViewPosition, normal, dhx, dhy, faceDirection ), ${f4(q.bump)} * ( 1.0 - smoothstep( 0.4, 1.0, pcFfw ) ) ) );
  }`);
      }
    }
    if (grooves) {
      // box-filtered coverage of each groove over the fragment's footprint along the axle (sub-pixel grooves at a
      // distance average out instead of aliasing), crown only
      const g = grooves, v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(6)).join(', ')})`, f6 = (x) => (+x).toFixed(6);
      const cov = g.off.map((o) => `pcGroove += max(0.0, min(pcGt + pcGfw, ${f6(o + g.hw)}) - max(pcGt - pcGfw, ${f6(o - g.hw)}));`).join('\n  ');
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  vec3 pcGd = vRestP - ${v3(g.c)};
  float pcGt = dot(pcGd, ${v3(g.a)});
  float pcGfw = max(0.5 * fwidth(pcGt), 1e-5);
  float pcGroove = 0.0;
  ${cov}
  pcGroove = clamp(pcGroove / (2.0 * pcGfw), 0.0, 1.0) * smoothstep(${f6(g.rMin - 0.01)}, ${f6(g.rMin)}, length(pcGd - pcGt * ${v3(g.a)}));
  diffuseColor.rgb *= mix(1.0, ${f6(g.floor)}, pcGroove);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(roughnessFactor, ${f6(g.rough)}, pcGroove);`);
      if (physical) {
        // the groove floor is a cavity: its sheen is mostly occluded
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  material.specularColor *= mix(1.0, ${f6(g.floor)}, pcGroove);
  material.specularF90 *= mix(1.0, ${f6(g.floor)}, pcGroove);`);
      }
    }
    if (stripes && restP) {
      // lookdev _carpet_stripes without the wobble: stripe mask 1 within duty / 2 of each pitch line (soft woven
      // edges), widened by the fragment's footprint and faded to its mean (duty) once a pitch is under ~2 pixels, so
      // the floor does not alias into moire at a distance
      const st = stripes, f4 = (x) => (+x).toFixed(5);
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  {
    float pcPh = vRestP.z / ${f4(st.pitch)};
    float pcSw = fwidth(pcPh);
    float pcSd = abs(fract(pcPh + 0.5) - 0.5);
    float pcSm = 1.0 - smoothstep(${f4(0.5 * st.duty - 0.06)} - pcSw, ${f4(0.5 * st.duty + 0.06)} + pcSw, pcSd);
    pcSm = mix(pcSm, ${f4(st.duty)}, smoothstep(0.25, 0.6, pcSw));
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(${st.colour.map(f4).join(', ')}), pcSm);
  }`);
    }
    if (back) {
      const v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(5)).join(', ')})`;
      fs = fs.replace('#include <normal_fragment_begin>',
        `if (pcIsBack()) { diffuseColor.rgb = ${v3(back.base)}; roughnessFactor = ${(+back.rough).toFixed(3)}; metalnessFactor = 0.0;${back.opaque ? ' diffuseColor.a = 1.0;' : ''} }
#include <normal_fragment_begin>`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  if (pcIsBack()) { material.specularColor = vec3(${(0.04 * back.spec).toFixed(5)}); material.specularF90 = ${(+back.spec).toFixed(3)}; }`);
      }
    }
    if (lining) {
      sh.uniforms.uLining = U.lining;
      sh.uniforms.uLiningRough = U.liningRough;
      fsHead += 'uniform vec3 uLining;\nuniform float uLiningRough;\n';
      fs = fs.replace('#include <normal_fragment_begin>',
        `bool pcLining = pcIsBack();
  if (pcLining) { diffuseColor.rgb = ${liningBase ? `vec3(${liningBase.map((x) => (+x).toFixed(5)).join(', ')})` : 'uLining'}; roughnessFactor = uLiningRough; metalnessFactor = 0.0; }
#include <normal_fragment_begin>`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  if (pcLining) {
    material.specularColor = vec3(0.03);
    material.specularF90 = 1.0;
    #ifdef USE_CLEARCOAT
      material.clearcoat = 0.0;
    #endif
  }`);
      }
    }
    if (ao) {
      // the baked occlusion (x) and window sky visibility (y) per vertex (GLB _AO -> three '_ao', normalised bytes)
      vs = 'attribute vec2 _ao;\nvarying vec2 vPcAO;\n' + vs.replace('#include <project_vertex>', '#include <project_vertex>\n  vPcAO = _ao;');
      fsHead += 'varying vec2 vPcAO;\n';
    }
    if (interior) {
      // the sun inside (scene.js LOOK.sun) has a shadow box round the flight deck only: outside it (the cabin aft, the
      // far side of the box) an interior surface is in the skin's shade, not in the sun
      const chunk = THREE.ShaderChunk.shadowmap_pars_fragment, head = 'float shadow = 1.0;\n\t\tshadowCoord.xyz /= shadowCoord.w;';
      if (chunk.includes(head)) fs = fs.replace('#include <shadowmap_pars_fragment>', chunk.replace(head, 'float shadow = 0.0;\n\t\tshadowCoord.xyz /= shadowCoord.w;'));
    }
    if (interior && physical && ((cabinFill && cabinFill.length > 4 && +cabinFill[4] > 0) || probe)) {
      // CABIN_TRIM 'up' (3-D judges r2 FID2-04 / CR2-06): inside, the reflections that point below the horizon take the
      // environment above it (mirrored about the horizontal) -- the studio's floor stands in for the cockpit's lap /
      // pedestal / footwell, a dim grey that read the yoke's satin inserts grey and its gloss cover matte from the crew
      // seats (looking down onto the aft face, the reflections point aft-down); mirrored, they show the softbox / window
      // streaks the photos show on the cover and keep the inserts near-white; reflections above the horizon unchanged
      // A sixth entry, 'win': the side windows' light -- reflections turned sideways (|glTF X| = |BL| over ~0.35-0.65)
      // and level or up see a window of radiance win (linear, added to the studio's): the bright streaks the photos show
      // where the cover's arms and stems turn sideways (P1046408); the studio's softboxes stand overhead, the side windows
      // are what the yoke sees beside it
      // 'probe' (rev Q, YOKE_PROBE): the reflection's radiance inside is the cabin probe's, not the studio's
      const up = (+((cabinFill && cabinFill[4]) || 0)).toFixed(3), win = (+((cabinFill && cabinFill[5]) || 0)).toFixed(3);
      const f3 = (x) => (+x).toFixed(4);
      const prb = probe ? `
			vec3 pcR0 = reflectVec;
			vec3 pcPWq = ( vec4( - vViewPosition, 0.0 ) * viewMatrix ).xyz + cameraPosition;` : '';
      const prbRet = probe ? `
			float pcLaw = ${f3(probe.k[0])} + ${f3(probe.k[1])} * smoothstep( ${f3(probe.y[0])}, ${f3(probe.y[1])}, pcR0.y )
				+ ${f3(probe.k[2])} * smoothstep( 0.15, 0.5, pcR0.x * sign( pcPWq.x ) ) * ( 1.0 - smoothstep( 0.15, 0.55, abs( pcR0.y - 0.15 ) ) )
				+ ${f3(probe.k[3] || 0)} * ( 1.0 - smoothstep( ${f3(probe.y[2] ?? -0.4)}, ${f3(probe.y[3] ?? 0.1)}, pcR0.y ) );
			pcLaw *= mix( ${f3(1 - (probe.k[4] || 0))}, ${f3(1 + (probe.k[4] || 0))}, smoothstep( ${f3(probe.y[4] ?? 1.83)}, ${f3(probe.y[5] ?? 1.91)}, pcPWq.y ) );
			vec3 pcRef = textureCubeUV( envMap, vec3( 0.0, 1.0, 0.0 ), 0.9 ).rgb * envMapIntensity;
			pcEnv = mix( pcEnv, pcRef * vec3( ${probe.tint.map(f3).join(', ')} ) * pcLaw, uCabinIn );` : '';
      fs = fs.replace('#include <envmap_physical_pars_fragment>', THREE.ShaderChunk.envmap_physical_pars_fragment.replace(
        'reflectVec = inverseTransformDirection( reflectVec, viewMatrix );',
        `reflectVec = inverseTransformDirection( reflectVec, viewMatrix );${prb}
			reflectVec.y = mix( reflectVec.y, abs( reflectVec.y ), ${up} * uCabinIn );
			float pcWin = ${win} * uCabinIn * smoothstep( 0.35, 0.65, abs( reflectVec.x ) ) * smoothstep( - 0.10, 0.20, reflectVec.y );`).replace(
        'return envMapColor.rgb * envMapIntensity;', `vec3 pcEnv = envMapColor.rgb * envMapIntensity + vec3( pcWin );${prbRet}
			return pcEnv;`));
    }
    if (lining || interior) {
      for (const k of ['cabinAO', 'cabinIn', 'cabinKey', 'cabinDiff', 'cabinSpec', 'cabinFill', 'cabinOcc', 'cabinSky', 'cabinGain', 'cabinKnee', 'cabinRefl', 'cabinShade', 'cabinProbe', 'cabinProbe2', 'cabinFoot']) sh.uniforms['u' + k[0].toUpperCase() + k.slice(1)] = U[k];
      const lit = !mat.isMeshBasicMaterial;   // geometryNormal / geometryViewDir: the lit materials' lights chunks
      fsHead += 'uniform float uCabinKnee;\nuniform float uCabinAO;\nuniform float uCabinIn;\nuniform float uCabinKey;\nuniform vec2 uCabinDiff;\nuniform vec2 uCabinSpec;\nuniform float uCabinFill;\nuniform vec3 uCabinOcc;\nuniform vec2 uCabinSky;\nuniform vec3 uCabinGain;\nuniform vec4 uCabinRefl;\nuniform vec4 uCabinShade;\nuniform vec4 uCabinProbe;\nuniform vec4 uCabinProbe2;\nuniform vec4 uCabinFoot;\n';
      // the window sky law's weight: the light trim keeps its fill share out of it (the cabin lining: all of it)
      const skyW = cabinFill ? Math.max(0, 1 - cabinFill[0]) : 1;
      fs = fs.replace('#include <aomap_fragment>', `{
    // outside: indirect x AO; the key light is mostly blocked by the closed skin: direct x AO^2.  Inside (uCabinIn):
    // the CABIN_LOOK light -- the sun (shadowed) at uCabinKey, the world's image-based light weighted by the surface's
    // facing (diffuse) / its reflection's direction (specular; not on the SPEC_KEEP trim), the light trim's fill, the
    // baked occlusion and the window sky visibility (look L3: diffuse x occ x mix(sky.x, 1, sky), reflections x sqrt(occ)
    // x mix(sky.y, 1, sky))
    float pcAO = ${interior ? 'uCabinAO' : 'pcLining ? uCabinAO : 1.0'};
    float pcIn = ${interior ? 'uCabinIn' : 'pcLining ? uCabinIn : 0.0'};
    ${lit ? `vec3 pcNW = inverseTransformDirection( geometryNormal, viewMatrix );
    vec3 pcRW = inverseTransformDirection( reflect( - geometryViewDir, geometryNormal ), viewMatrix );` : 'vec3 pcNW = vec3( 0.0 ), pcRW = vec3( 0.0 );'}
    float pcOcc = ${ao ? `mix( 1.0, vPcAO.x, pcIn * uCabinOcc.x * ${(0.5 + 0.5 * skyW).toFixed(3)} )` : '1.0'};
    float pcSkyV = ${ao ? 'vPcAO.y' : '1.0'};
    // the window light law (inside, weighted by skyW): diffuse = gain x occ^p x mix(floor, 1, light), at most the open
    // world's x gain.z; reflections = gain x occ^q x mix(floor, 1, light)
    float pcOd = pow( pcOcc, uCabinOcc.y ), pcOs = pow( pcOcc, uCabinOcc.z );
    // (flight deck fix r1 FDO1-05: a soft knee toward 2 x gain.z instead of the hard min( , gain.z): the flight deck's
    // median window light 0.11 x 18 put most of its surfaces on the cap -- one flat level everywhere, the light's
    // gradient toward the glazing gone; uCabinKnee 0 restores the hard cap)
    float pcX = mix( uCabinSky.x, 1.0, pcSkyV ) * uCabinGain.x * pcOd, pcKn = 2.0 * uCabinGain.z;
    float pcSd = mix( pcOd, uCabinKnee > 0.5 ? pcKn * ( 1.0 - exp( - pcX / pcKn ) ) : min( pcX, uCabinGain.z ), pcIn * ${skyW.toFixed(3)} );
    float pcSs = mix( pcOs, mix( uCabinSky.y, 1.0, pcSkyV ) * uCabinGain.y * pcOs, pcIn * ${skyW.toFixed(3)} );
    float pcKd = mix( 1.0, mix( uCabinDiff.x, uCabinDiff.y, 0.5 + 0.5 * pcNW.y )${cabinFill ? ` * ${(+cabinFill[1]).toFixed(3)} * pow( uCabinFill, ${(+cabinFill[0]).toFixed(3)} )` : ''}, pcIn );
    // the flight deck (ahead of the divider, x 4.57: glTF Z) inside: its world position from the view position
    ${lit ? 'vec3 pcPW = ( vec4( - vViewPosition, 0.0 ) * viewMatrix ).xyz + cameraPosition;' : 'vec3 pcPW = vec3( 0.0, 0.0, 99.0 );'}
    float pcFd = pcIn * ( 1.0 - smoothstep( 4.5, 4.75, pcPW.z ) );
    float pcKs = mix( 1.0, ${cabinFill && cabinFill.length > 2 ? `max( ${(+cabinFill[2]).toFixed(3)}, ` : ''}${specKeep ? (reflDir ? 'mix( uCabinRefl.x, 1.0, smoothstep( uCabinRefl.y, uCabinRefl.z, dot( pcRW, normalize( vec3( 0.0, uCabinRefl.w, - 1.0 ) ) ) ) )' : '1.0') : 'mix( uCabinSpec.x, uCabinSpec.y, smoothstep( - 0.5, 0.7, pcRW.y ) )'}${cabinFill && cabinFill.length > 2 ? ' )' : ''}${cabinFill && cabinFill.length > 6 ? ` * ${(+cabinFill[6]).toFixed(3)}` : ''}, pcIn );${reflDir ? `
    {
      // the cabin probe (flight deck fix r3): reflections pointing aft into the cabin see its windows / opening / headliner
      // azimuth from dead aft (glTF +Z), elevation: the side windows abeam, the lit cabin through the divider opening
      // (within ~24 deg of aft, -10 .. +20 deg) with its windows as bright stripes in azimuth (the windows down both
      // walls, nearer ones wider apart), the headliner overhead; the rest the dark cabin (seats, walnut, crew)
      float pcAz = abs( atan( pcRW.x, max( pcRW.z, 1e-3 ) ) );
      float pcSide = smoothstep( 0.55, 0.85, abs( pcRW.x ) ) * ( 1.0 - smoothstep( 0.12, 0.5, abs( pcRW.y - 0.05 ) ) );
      float pcOpen = ( 1.0 - smoothstep( 0.36, 0.46, pcAz ) ) * smoothstep( - 0.22, - 0.10, pcRW.y ) * ( 1.0 - smoothstep( 0.25, 0.4, pcRW.y ) );
      float pcWin = smoothstep( 0.35, 0.95, sin( sqrt( pcAz ) * 34.0 ) ) * smoothstep( 0.04, 0.10, pcAz ) * ( 1.0 - smoothstep( 0.03, 0.16, abs( pcRW.y - 0.04 ) ) );
      float pcUp = smoothstep( 0.25, 0.85, pcRW.y );
      float pcPrb = uCabinProbe.x + uCabinProbe.y * pcSide + uCabinProbe.z * pcOpen * ( 1.0 + uCabinProbe2.x * pcWin ) + uCabinProbe.w * pcUp;
      pcKs *= mix( 1.0, pcPrb, pcFd * smoothstep( - 0.25, 0.25, pcRW.z ) );${brush ? `
      pcKs *= mix( 1.0, pcBrushK, pcIn );` : ''}
    }` : ''}
    float pcKk = mix( pcAO * pcAO, uCabinKey${sunIn ? ` * ${(+sunIn).toFixed(3)}` : ''}, pcIn );
    // (the yoke track's 4th CABIN_TRIM entry: the directional light's least share in the specular -- a glint; inside the
    // sun is at uCabinKey 1, so it only matters where a material's sunIn is below it)
    float pcKks = ${cabinFill && cabinFill.length > 3 ? `mix( pcAO * pcAO, max( uCabinKey${sunIn ? ` * ${(+sunIn).toFixed(3)}` : ''}, ${(+cabinFill[3]).toFixed(3)} ), pcIn )` : 'pcKk'};
    float pcDi = pcAO * pcKd * pcSd;${cabinFill && cabinFill.length > 10 ? `
    // CABIN_TRIM entries 8-11 (flight deck fix FDY r1, FDY-O1-02): a NEAR-FIELD term on the diffuse inside -- x lo below WL
    // y0 .. x hi above y1 (world): the yoke cover's lower stem sees the dark lap / lower panel, its crown the windshield
    // over the glareshield (the photos' white crown over a greyer V stem; the planar face had read one flat tone); a 12th
    // entry, the share of it on the reflections (the clear coat mirrors the same near field)
    float pcNf = mix( 1.0, mix( ${(+cabinFill[7]).toFixed(3)}, ${(+cabinFill[8]).toFixed(3)}, smoothstep( ${(+cabinFill[9]).toFixed(3)}, ${(+cabinFill[10]).toFixed(3)}, pcPW.y ) ), pcIn );
    pcDi *= pcNf;` : ''}
    // (flight deck fix r5 FDO4-04: the footwell under the panel read as a blue-black void with only the pedal pads; P1046408
    // / 09 show the pedal arms, linkage and side walls in a soft light from the side windows and the floor): its diffuse
    // x (1 + boost) below the panel's lower edge, ahead of the seats
    // (not the floor: the up-facing carpet stays near-black, P1046408 5-15, [FD-L2] / [FD-L6]; nor the crew seats'
    // fleece, which reaches into that box)${fleece || fur ? `
    if ( false )` : ''}
    pcDi *= 1.0 + uCabinFoot.x * pcFd * ( 1.0 - smoothstep( uCabinFoot.y, uCabinFoot.y + 0.12, pcPW.y ) )
      * ( 1.0 - smoothstep( uCabinFoot.z, uCabinFoot.z + 0.15, pcPW.z ) ) * ( 1.0 - smoothstep( 0.45, 0.8, pcNW.y ) );
    float pcSi = pcAO * pcKs * pcSs${specIn ? ` * mix( 1.0, ${(+specIn).toFixed(3)}, pcIn )` : ''}${cabinFill && cabinFill.length > 11 ? ` * mix( 1.0, pcNf, ${(+cabinFill[11]).toFixed(3)} )` : ''};${emisIn ? `
    totalEmissiveRadiance *= mix( 1.0, ${(+emisIn).toFixed(3)}, pcIn );` : ''}
    reflectedLight.directDiffuse *= pcKk; reflectedLight.directSpecular *= pcKks;
    reflectedLight.indirectDiffuse *= pcDi; reflectedLight.indirectSpecular *= pcSi;
    // the flight deck's daylight shade (flight deck fix r3 FID-FD3-02): a cool tint on the indirect diffuse, more where the
    // surface faces the glazing (forward / up / outboard)
    reflectedLight.indirectDiffuse *= mix( vec3( 1.0 ), uCabinShade.xyz, uCabinShade.w * pcFd * ( 0.6 + 0.4 * clamp( dot( pcNW, normalize( vec3( 0.0, 0.5, - 1.0 ) ) ), 0.0, 1.0 ) ) );
    // (the clear coat and the sheen take the cabin light outside too: they had kept the full studio light, so the
    // sheepskin and the lacquered walnut read near-white through the closed glazing -- flight deck r1 LOOK)
    #ifdef USE_CLEARCOAT
      clearcoatSpecularDirect *= pcKks; clearcoatSpecularIndirect *= mix( pcAO, pcSi, pcIn );
    #endif
    #ifdef USE_SHEEN
      sheenSpecularDirect *= pcKk; sheenSpecularIndirect *= mix( pcAO, pcDi, pcIn );
    #endif
  }
#include <aomap_fragment>`);
    }
    if (glass) {
      // cabin glazing: back faces = the view from inside the cabin: nearly clear, faint reflections (or dim tinted
      // while the camera is outside a closed cabin).  Other glass (a light lens) keeps both sides as they are.
      fs = fs.replace('#include <alphamap_fragment>', `#include <alphamap_fragment>
  float pcInside = ${cabinGlass ? 'pcIsBack() ? 1.0 : 0.0' : '0.0'};
  diffuseColor.a = mix(diffuseColor.a, mix(diffuseColor.a * 0.2, uGlassDim, uCabinClosed), pcInside);`);
      sh.uniforms.uCabinClosed = U.cabinClosed;
      sh.uniforms.uGlassDim = U.glassDim;
      fsHead += 'uniform float uCabinClosed;\nuniform float uGlassDim;\n';
      const out = physical || mat.isMeshStandardMaterial
        ? 'gl_FragColor = vec4(totalDiffuse * diffuseColor.a + totalSpecular * mix(1.0, mix(0.35, 0.6, uCabinClosed), pcInside) + totalEmissiveRadiance, diffuseColor.a);'
        : 'gl_FragColor = vec4(outgoingLight * diffuseColor.a, diffuseColor.a);';
      fs = fs.replace('#include <opaque_fragment>', out);
      // physical: the clear-coat block rewrites outgoingLight after totalDiffuse / totalSpecular (glass has
      // no clear coat, so the output above is complete)
    }
    sh.vertexShader = vs;
    sh.fragmentShader = fsHead + fs;
  };
  // the rest matrix is a uniform: programs are shared
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' + (liningBase ? liningBase.join('/') : '') : ''}${glass ? (cabinGlass ? 'G' : 'g') : ''}${interior ? 'I' : ''}${cabinFill ? 'F' + cabinFill.join('/') : ''}${back ? 'B' + back.base.join('/') + (back.opaque ? 'o' : '') : ''}${collar ? 'C' + JSON.stringify(collar) : ''}${grooves ? 'R' + JSON.stringify(grooves) : ''}${stripes ? 'S' + JSON.stringify(stripes) : ''}${fleece ? 'W' + JSON.stringify(fleece) : ''}${specKeep ? 'K' : ''}${reflDir ? 'D' : ''}${ao ? 'A' : ''}${leather ? 'E' + JSON.stringify(leather) : ''}${brush ? 'U' + JSON.stringify(brush) : ''}${grain ? 'N' + JSON.stringify(grain) : ''}${emisIn ? 'X' + emisIn : ''}${specIn ? 'Q' + specIn : ''}${sunIn ? 'Z' + sunIn : ''}${probe ? 'Y' + JSON.stringify(probe) : ''}${fur ? 'H' + JSON.stringify(fur) : ''}`;
  mat.needsUpdate = true;
  return mat;
}

// clone that keeps the patch (Material.clone() drops onBeforeCompile but copies userData)
export function clonePatched(mat, extra = {}) {
  const m = mat.clone();
  return installPatch(m, extra);
}
