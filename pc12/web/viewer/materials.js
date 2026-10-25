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
  // the supersampling factor of the pass being rendered (picture.js _renderSS): the patches' footprints x this (CRA1-01)
  pcSS: { value: 1 },
  pcMove: { value: 0 },            // 1 on the camera-moving frames (picture.js _path; the groove AA, CRA1-02)
  furSoft: { value: 0 },          // the fur shells' soft coverage on (inside: addFur's onAfterRender)
  furSeed: { value: 0 },          // the dither's per-draw offset (FD9-03: the passes / frames average it out)
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
  // the cabin's form light (all-lens review r1 CAB1-01; CABIN_FORM): per class [gain, occlusion power, x at no window light,
  // x at full], [x facing inboard (toward the aisle), x facing outboard (toward its own side wall), x facing down, x facing
  // up], [x at WL C.y, x at WL C.z, x at WL C.w, -]; and [the window light that counts as full, WL low, belt, ceiling]
  cabinFormA: { value: [new THREE.Vector4(1, 0, 1, 1), new THREE.Vector4(1, 0, 1, 1), new THREE.Vector4(1, 0, 1, 1)] },
  cabinFormB: { value: [new THREE.Vector4(1, 1, 1, 1), new THREE.Vector4(1, 1, 1, 1), new THREE.Vector4(1, 1, 1, 1)] },
  cabinFormD: { value: [new THREE.Vector4(1, 1, 1, 0), new THREE.Vector4(1, 1, 1, 0), new THREE.Vector4(1, 1, 1, 0)] },
  cabinFormC: { value: new THREE.Vector4(0.3, 1.3, 1.95, 2.7) },
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
const FP_LIGHT = Q_M.get('fp') === '1';   // the first-principles T-LIGHT experiment (upgradeMaterials)
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
  // [the opening's window stripes: x (1 + this), their fade to the mean over the roughness from .. to, -]
  // (flight deck + yoke fix r4 FDY-O4-01: the stripes drew thin wavy white streaks down the 0.27-rough titanium plates in
  // the close / oblique views -- 'water running down glass'; a satin metal blurs a 6-7 deg stripe into a soft gradient:
  // faded to their mean from roughness 0.15 to 0.30, and wherever a pixel spans more than ~1/100 of a stripe period)
  probe2: qv('cabProbe2', [2.0, 0.15, 0.30, 0]),
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
const CABIN_TRIM = { lining: [1, 1], leather: [0.5, 1], stitch_light: [0.5, 1], leather_crew: [0, 0.8], leather_dark: [0.6, 1],
  // (first-principles judge r1 FP1-05: from the cabin the crew seats' backs read as uniform slate slabs; P1046406 shows
  // the anthracite shells dark, with their highlights)
  leather_crew_shell: [0, 0.65],
  lav_white: [0.8, 1], toilet_white: [0.8, 1], psu_housing: [0.7, 1],
  // the printed legends (first-principles flight deck A3: decals carrying model/fd_print.py's atlas): a silk-screened
  // white reads ~190-220 on the plates in P1046408 / 09 -- lifted over the interior law's dark panel light
  legend_print: [0, 1.15],      // (judge r1 FP1-04: one tone dimmer -- 1.6 glowed on the overhead / quadrant)
  // the crew seats' lavender-grey sheepskin (P1046408 / 09 ~90-130 in the cabin light, B > R)
  sheepskin: [0, 0.50],     // (FDY r1: 0.42 -> 0.60 for the LOCKS fleece's darker mean albedo: panel_408b ~119, P1046408 121)
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
  // (flight deck + yoke fix r4 FIDY4-06: the band under the PDUs x 0.8 -> 0.9, a little more of the plates' range)
  // (first-principles judge r3 FP3-02: flat matte beige -- P1046408's plates run light under the PDUs to dark at their
  // foot, p10 / p90 28 / 147: the near-field term turned round and stronger, x 0.72 below WL 1.76 .. x 1.18 above 1.88)
  panel_titanium: [0, 0.56, 0, 0, 0, 0, 1, 1.05, 0.9, 1.78, 1.88, 0.5],
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
  panel_grey: [0, 0.83],        // (first-principles judge r1 FP1-09: the fascia ~85 against P1046408's ~106)
  // the dark cove below the outer sub-panels (flight deck fix r3 FID-FD3-01: P1046408's cove ~41 at the fitted camera;
  // at x 1 it read 28)
  // (flight deck + yoke fix r4 FIDY4-01: the cove read 66 at panel_408b against P1046408's 8 under the same mask -- the
  // fix r3 measure, ~41, was taken over the cove's lit rim; with the footwell fill off (FOOT_SKIP) 1.45 -> 0.5: 12)
  fd_cove: [0, 0.5],
  // flight deck fix r5: the A-pillar's round post (FDO4-02 / FID-FD4-02: P1046409 / 10 slim dark posts, ~60-90 with a
  // narrow bright edge -- its satin reflection of the glazing, SPEC_KEEP) and the palm tray's matte warm titanium floor
  // (FDO4-03: P1046408 ~128 / 117 / 132, no recognisable reflection)
  // (FDY r2 FIDY2-04 above: the post 0.5 -> 1.05; the palm tray 0.3 -> 0.42 -- 91 at panel_408b against P1046408's 117)
  lining_fd_post: [0, 1.2], tray_titanium: [0, 0.5],
  // (fix r5 FDO4-03 / FID-FD4-03: from above, the quadrant / pedestal views, the palm tray read 135-165 and the
  // stack's gunmetal shroud and the quadrant frame 100-135, light-grey plastic; P1046409 from the co-pilot's seat: the
  // tray 106 / 100 / 113, the face round it 51-60, the frame ~60-70)
  // (flight deck fix FDY r1 FIDY1-03: the quadrant frame / stack flanks read light grey, 65 / 86 / 76 at panel_408b /
  // P1046410 / P1046409's cameras against the photos' 28 / 43 / 39 under the same masks: 0.6 -> 0.25, its reflections kept;
  // 0.33 read 52 at panel_408b)
  // (flight deck fix FDY r2: the quadrant frame still 45 at panel_408b against P1046408's 27: 0.25 -> 0.15)
  stack_gunmetal: [0, 0.55], pedestal_gunmetal: [0, 0.15],
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
  // (flight deck + yoke fix r4 FDY-O4-03 / FIDY4-02: the grips and pads a flat mid-grey slate plastic up close -- the
  // range compressed, 49 / 60 / 87 and 55 / 75 / 85 at the yoke close-up against P1046409's 38 / 60 / 183 and 33 / 82 /
  // 121: the reflection floor 0.45 -> 0.1 (it lit every flank alike), their reflections a directional cabin probe
  // instead (YOKE_PROBE grip_black / yoke_leather): dark toward the cabin, lit by the overhead and the side window)
  // (fix r4 verification: at 0.1 the full viewer_test read the pilot stop's body 0.21 of the cover, the pads 1.65 x and
  // the lunes 1.81 x the body -- outside [Y1b] / [Y1c]'s photo bands (body 0.27-0.30, pads 1.06-1.27); a floor of 0.3
  // lifts the shaded flanks, hardly the median up close: the stop's body 0.28, pads / body 1.24, lunes / body 1.35; the
  // yoke close-up 37 / 69 / 122 (p99 148) against 25 / 65 / 120 at 0.1 and P1046409's 38 / 60 / 183)
  // (all-lens review r1 FD8-03: up close the grips still read as slate-blue grey plastic -- 66-75 with B - R +18 from the
  // pilot's eye, a uniform 67 / 86 / 102 at the yoke close-up, where P1046410 / 09's black satin grips put their light in
  // sharp glints: the diffuse fill -25 %, the reflection floor 0.3 -> 0.22, the lobe tighter (PART_TRIM roughness 0.12))
  yoke_nickel: [0, 1, 0, 0.35, 0, 0, 0.25], 'yoke:grip_black': [0, 0.30, 0.22, 1, 0, 40], yoke_trim_face: [0, 1.0, 0.25],
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
  // (all-lens review r1 FD8-03: with the grips' satin black darker -- body / cover 0.28 -> 0.23 -- the pads' fill 0.68 ->
  // 0.60 keeps them one near tone with it, pads / body <= 1.4 as [Y1b] and the photos 1.06-1.27)
  yoke_leather: [0, 0.60, 0.1, 0.6, 0, 20, 1, 0.6, 1.45, 1.80, 1.90, 0.5], button_red: [0, 0.75],     // (FDY r1: [0, 0.65] + near field; fix r4: floor 0.3 -> 0.1, the sun's glint 0.6)
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
  // (flight deck + yoke fix r4 FIDY4-03: from the crew eyes 0.85-0.86 of the cover, P1046409's crop ~1.0 -- the stop's
  // reflections point aft and a little up, R.y ~0.2-0.3, P1046408's low camera mostly up, R.y ~0.6: the dark-cabin term
  // +20 %, the overhead -15 %, the P1046408 camera unchanged ([Y1d] <= 0.97))
  yoke_silver: { k: [1.95, 1.27, 1.025, 1.625, 0.22], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [0.82, 0.95, 1.22] },
  // (FDY r2 FIDY2-06: the lower insert 0.84-0.86 of the upper at panel_408b against the photos' 0.92-0.95, and bluer:
  // its terms x 1.2, the side term x 1.3 -- P1046408's low camera sees it mirror the side window -- with a less blue base
  // (VIEWER): 0.91 there, lower / upper 0.89 from the pilot stop ([Y1e] <= 0.90))
  yoke_silver_dark: { k: [1.2, 1.85, 2.2, 0.84, 0], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [0.82, 0.95, 1.22] },
  // (flight deck + yoke fix r4 FDY-O4-03 / FIDY4-02) the satin-black body and the leather pads: a directional law --
  // the dark cabin behind the crew low, the overhead / windshield and the yoke's own side window bright -- so the aft
  // faces fall near-black and the rolled rims and tops catch the light (P1046409: 38 / 60 / 183 on the body)
  // (all-lens review r2 FD9-02: up close B - R +24, slate blue: a warm tint, the side-window term 4 -> 6 for brighter
  // edge glints (yoke close-up p90 120 -> 135, P1046409 183); the fill / dark-cabin cut the judge proposed (-25 %) is not
  // taken: at the pilot stop it put the body at 0.18-0.21 of the cover, pads / body 1.55-1.73, lunes / body 1.84-2.07 --
  // outside [Y1b] / [Y1c]'s photo bands -- and up close the body's median 64 already sits at P1046409's 60)
  grip_black: { k: [0.95, 0.9, 6.0, 0.12, 0.3], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [1.04, 1.0, 0.92] },
  yoke_leather: { k: [0.25, 2.6, 2.6, 0.12, 0.35], y: [0.15, 0.6, -0.4, 0.1, 1.83, 1.91], tint: [1.0, 1.0, 1.0] },
};
for (const it of (Q_M.get('yokeProbe') || '').split('|')) {          // ?yokeProbe=name:k0,..,k4,y0,..,y5[,tr,tg,tb]|...
  const k = it.slice(0, it.lastIndexOf(':')), a = it.slice(it.lastIndexOf(':') + 1).split(',').map(Number);
  if (k && a.length >= 11 && a.every(Number.isFinite)) {
    YOKE_PROBE[k] = { tint: [1, 1, 1], ...(YOKE_PROBE[k] || {}), k: a.slice(0, 5), y: a.slice(5, 11) };
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
  // (flight deck + yoke fix r4 FIDY4-05: at panel_408b the roll read one flat slate band, 80 down every column, where
  // P1046408's roll catches the sky along its top, ~144, and darkens toward the fascia, ~104: `facing` -- its reflections
  // x 0.75 facing down .. x 2.4 facing up (half of it on the diffuse): 121 -> 96 down the roll; from the pilot stop the
  // lip 81 -> ~95)
  'flight_deck:leather_black': { specIn: 1.9, specularIntensity: 1.0, specularColor: [0.30, 0.44, 0.64], roughness: 0.38,
    facing: [0.75, 2.4, -0.5, 0.5, 0.5] },
  // the side-window sills of the same leather (FDO2-03: a broad light-grey band from the seats, 86-120 in the window
  // light): a little less diffuse and sky sheen; [FD-L3] reads them at panel_408b (63 -> ~55; >= 50)
  // (first-principles judge r2 FP2-08: the co-pilot's sunlit sill (172, 137, 140) -- P1046409 ~95-120 grey: less sun)
  'interior_lining:leather_glareshield': { fill: [0, 0.8], specIn: 1.15, sunIn: 0.45 },
  // (fix r3: the PDU's display bezels, AFCS and GTC faces -- satin black plastic whose light in P1046408 is the cabin
  // and crew it mirrors: its bezels 37-58 along the columns between and round the displays, the model's read 24 at the
  // fitted camera, a black field round every display; its reflections x 2 read 37 there, 42 from the pilot stop
  // ([T14] keeps them <= 50, [FD-L6] the frame's tonal bands); the CB panels on the lining keep theirs)
  // (flight deck + yoke fix r4 FIDY4-04: the GFC 700's face mirrored the apron and hangars as streaky light bands where
  // the photo's black face is matte: a rougher 0.45, the reflections' share kept)
  'flight_deck:bezel_black': { specIn: 2.0, roughness: 0.45 },
  // (flight deck fix FDY r1 FIDY1-07: the overhead panel read near-black from the cabin, 30 at cabin_fwd_406 against
  // P1046406's lit mid-grey 70; P1046408 reads it ~45 under the windshield's light and [T14] keeps it <= 50 at the pilot /
  // fd_cabin stops: its fill 0.5 -> 0.85, ~47 there and ~48 from the cabin -- the two photos' exposures disagree)
  'interior_lining:panel_dark': { fill: [0, 0.85] },
  // (FDY r1 FDY-O1-02 / FIDY1-04: the yoke body's satin black -- sharper, stronger reflections, a warm specular tint taking
  // the world sky's blue out of it; CABIN_TRIM 'yoke:grip_black' above)
  // (FDY r2 FDY-O2-02 / FIDY2-06: still matte slate without the photos' satin streaks down the grip faces: sharper and
  // stronger reflections, neutral-cool -- the median kept dark for [Y1b], the lit edges brighter)
  // (flight deck + yoke fix r4 FDY-O4-03 / FIDY4-02: tighter and stronger again under the YOKE_PROBE law)
  // (all-lens review r2 FD9-02: up close the grip body still slate-blue -- (89, 97, 112) at the yoke close-up, B - R +24,
  // against P1046409's near-black satin with thin glints: a warm specular tint, the lobe a shade tighter)
  'yoke_L:grip_black': { roughness: 0.10, specIn: 5.0, specularColor: [1.0, 0.94, 0.86] },
  'yoke_R:grip_black': { roughness: 0.10, specIn: 5.0, specularColor: [1.0, 0.94, 0.86] },
  // (all-lens review r2 CAB2-04: the club tables' gloss-black tops read as matte slate -- p10 / p50 / p90 / p99 7 / 12 /
  // 49 / 113 deployed, P1046404 / 05 / 07 38-45 / 63-106 / 116-124 / 220-234 with the window mirrored in them: a piano
  // lacquer, roughness 0.06, mirroring the CABIN (mirrorGLSL: the ledge, the light wall, the windows, the headliner)
  // instead of the studio, unscaled by the cabin law's reflection weights (floor 1); a uniform 'win' radiance had
  // greyed the whole top to 155-185; the wall at 1.0 x the overhead radiance mirrored brighter than the wall itself --
  // the low P1046405 pose 93 / 107 / 182 / 206 --: 0.45, the windows 12, the radiance a neutral grey (tint 0.3: the sky's
  // blue had read as slate), the window outlines sharper (blur 0.25); look-dev ld3 t1 / w1)
  ...Object.fromEntries(['table_club_p', 'table_club_s', 'table_club_p_leaf', 'table_club_s_leaf'].map((p) =>
    [p + ':gloss_black', { fill: [0, 1, 1], roughness: 0.06, mirror: { k: [0.08, 0.45, 12.0, 1.8, 0.05], tint: 0.3, blur: 0.25 } }])),
  // (FDY r2 FDY-O2-02: the pads' blue-grey speckle -- a warm specular tint takes the sky's blue out of their sheen)
  // (all-lens r1 FD8-03: the pads a shade blue in their sheen, B - R +18: a warmer tint, B - R ~+10)
  'yoke_L:yoke_leather': { specularColor: [1.0, 0.92, 0.84], specIn: 3.0 },
  'yoke_R:yoke_leather': { specularColor: [1.0, 0.92, 0.84], specIn: 3.0 },
  // (FDY r2 FDY-O2-04: the quadrant plate and the flight deck's black parts read navy from above, B - R +26 at the
  // quadrant close-up, the photos satin black: a warm base and specular tint, less reflection inside)
  // (first-principles, round-3 minor: the quadrant plate read charcoal-brown; P1046408 / the Pilatus throttle photo show a
  // blue-black anodised plate)
  // (first-principles judge r1 FP1-01: a neutral base read NAVY under the flight deck's cool shade light -- the warm base
  // is what keeps the anodised plate charcoal; a shade less warm than fix r2's: B - R ~ +10 at the quadrant)
  'flight_deck:black': { color: [0.036, 0.030, 0.025], specIn: 0.5, roughness: 0.62, specularColor: [1.0, 0.94, 0.85] },
  // (flight deck + yoke fix r4 FIDY4-01 / 04) the consoles' forward faces in the knees' shade (113 at panel_408b against
  // P1046408's 6; 124 in the footwell close-up against P1046409's ~31, exposed ~1.3 x darker: 0.25 -> ~22 / ~30); the
  // panel's knobs -- cool satin
  // grip_black since this round's build -- keep the windshield's reflection on their knurled sides (a floor of 0.8 of
  // the reflections: 40 -> 59 at panel_408b, P1046408's knob tops 61-82 with B - R +30); the satin-silver trim of the
  // footwell's foil blanket and the outer plates' edge strips not a lit band in the shade (119 / 109 against ~25 / 31)
  'fd_consoles:lining_flightdeck': { fill: [0, 0.25] },
  'flight_deck:grip_black': { fill: [0, 1, 0.8], specIn: 2.2 },
  'flight_deck:panel_silver': { fill: [0, 0.4], specIn: 0.3 },
};
// ?partTrim=part:material={json}|... merges look-development overrides into PART_TRIM (as ?cabTrim for CABIN_TRIM)
for (const it of (Q_M.get('partTrim') || '').split('|')) {
  const i = it.indexOf('=');
  if (i < 1) continue;
  try { PART_TRIM[it.slice(0, i)] = { ...(PART_TRIM[it.slice(0, i)] || {}), ...JSON.parse(it.slice(i + 1)) }; } catch (e) { /* ignored */ }
}
// (flight deck + yoke fix r4 FIDY4-01) the materials CABIN_LOOK.foot's footwell fill leaves alone: the walls round the
// knees -- the consoles' forward faces and the side walls (lining_flightdeck), the cove under the outer sub-panels --
// read mid-grey walls where P1046408 / 09 show near-black sculpted console ends (5-11 at the fitted camera); the fill
// stays on the pedals, the linkage and the footwell's own dark walls
// (and the footwell's own dark walls / front closure (panel_dark) and its foil blanket / the outer plates' edge strips
// (panel_silver): P1046408's footwells read 5-17 round the pedals, the x 1.8 had them 22-43 and the blanket 119)
// CABIN FORM (all-lens review r1 CAB1-01, the cabin judge's major: aft of the divider the lining, headliner and the
// executive seats read as white clay -- within-surface spread 2-7x lower than P1046406 / 02 / 04 at matched framings: the
// light trim's flat cove / window fill sat over all shading).  Inside, aft of the divider (STA 4.55-4.75 blend), the
// class's indirect diffuse x gain x occlusion^p (the bake, full strength) x mix(lo, hi, the baked window light) x a
// facing term (fore / aft .. toward a side wall; down .. up): the light halo round each window, the walls darker toward
// the sills and between the windows, the soffit steps' shade, lit and shaded bolsters.  Classes: 0 the lining /
// headliner, 1 the executive seats' leathers and shells
// (all-lens review r2 CAB2-01: the exec seats' tone-on-tone stitching stitch_light takes the leather's form light)
// (all-lens review r2 CAB2-03 / FD9-04: the walnut a class of its own, 2 -- everywhere inside, the divider included:
// x lo where the bake's window light is low (the lavatory's bi-fold doors, the FR34 arch: P1046411 / 02 dark brown) .. x
// hi in the windows' light (the divider's daylit aft faces, P1046406 / 07), x 0.8 facing the aisle (the lavatory's
// bi-fold doors: (69, 53, 49) at the lav close-up against P1046411's (48, 36, 36), the divider's aft faces -- facing aft
// -- at cabin_fwd_406 (62, 48, 46) against P1046406's (62, 49, 46)))
const CABIN_FORM = { lining: 0, leather: 1, leather_dark: 1, seat_back_shell: 1, seat_shell_dark: 1, stitch_light: 1,
  veneer_walnut: 2 };
const qf4 = (k, d) => { const v = qv(k, d); return v; };
// tuned at the photo-fitted cabin_fwd_406 (P1046406) / cabin_fwd / p404 views in one look-dev page (out/tmp/all8_fix_r1/ld
// jobs a00 .. d02): the headliner centre's sd 5.9 -> ~11.5, the side wall's 9.6 -> ~16.5, the seat backs' 17.6 (the new
// welts / seams) -> ~30, the medians kept for [T4b] / [T14] (the light trim near-white: AgX's shoulder compresses the
// spread there, so the factors run wide -- x 0.38 .. 1.55 with the window light, 0.55 .. 1 from the floor to the belt)
CABIN_LOOK.formA = [qf4('cabFormA0', [1.82, 2.2, 0.38, 1.55]), qf4('cabFormA1', [1.5, 2.0, 0.5, 1.35]),
  qf4('cabFormA2', [1.0, 1.0, 0.80, 1.10])];
CABIN_LOOK.formB = [qf4('cabFormB0', [0.88, 1.05, 0.8, 1.0]), qf4('cabFormB1', [0.7, 1.2, 0.65, 1.15]), qf4('cabFormB2', [0.8, 1, 1, 1])];
CABIN_LOOK.formD = [qf4('cabFormD0', [0.55, 1.0, 0.85, 0]), qf4('cabFormD1', [0.6, 1.0, 1.15, 0]), qf4('cabFormD2', [1, 1, 1, 0])];
CABIN_LOOK.formC = qf4('cabFormC', [0.3, 1.3, 1.95, 2.7]);
U.cabinFormA.value.forEach((v, i) => v.set(...CABIN_LOOK.formA[i]));
U.cabinFormB.value.forEach((v, i) => v.set(...CABIN_LOOK.formB[i]));
U.cabinFormD.value.forEach((v, i) => v.set(...CABIN_LOOK.formD[i]));
U.cabinFormC.value.set(...CABIN_LOOK.formC);
const FOOT_SKIP = new Set((Q_M.get('footSkip') ?? 'lining_flightdeck,fd_cove,panel_dark,panel_silver').split(',').filter(Boolean));
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
  // the chin inlet's duct behind the lip (all-lens review r1 EXT-A1-02: mid-grey through the mouth where photo 130 shows
  // a near-black duct): the entry's near-black and the composite duct beyond it, both mostly in the duct's own shade
  inlet_dark: { specularIntensity: 0.3, envMapIntensity: 0.35 },
  composite: { color: [0.03, 0.03, 0.034], specularIntensity: 0.4, envMapIntensity: 0.35 },
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
  // (first-principles judge r1 FP1-06: the footwell carpet read navy -- B - R <= +8: a neutral charcoal loop pile)
  carpet_flightdeck: { color: [0.032, 0.030, 0.030] },
  sheepskin: { color: [0.225, 0.188, 0.205], sheenColor: [0.30, 0.28, 0.30], sunIn: 0.45,
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
    // (first-principles judge r1 FP1-02, the coral / sponge cells and terraced silhouettes within ~1 m: a taller pile
    // 10 + 1.5 mm, finer tufts 620 / 420 per m stretched 1.6 x down the faces, the clumps and partings at half, the lumps
    // +-5 %, the grazing band 0.5 / coverage edge 0.16, 20 layers; the base warmed R = G, B - R ~0 -> the cabin's cool
    // shade gives P1046409's B - R ~+10).  (Judge r2 FP2-01: still sponge pits / a white cotton fringe up close: the root
    // and lowest layers 0.58 of the tips (a gap is darker pile, not a hole), the threshold's rise 0.6 (fewer drop-outs),
    // the silhouette band flat and without its sheen lift (grazeFlat 0.9, grazeSheen 1), the base warmer: B - R ~+5)
    fur: { h: [0.010, 0.0015], root: 0.58, mean: 0.84, oct: [[800, 0.5, 0.5, 0, 1.5, 0, 0.5], [1100, 0.5, 0.6, 1, 1.4, 0.4, 0.5]], soft: [0, 0],
      // (all-lens r2 FD9-03: the grazing band wider and softer -- the outer layers thinned x graze below |n.v| grazeN,
      // the coverage edge widened there (grazeW: alpha to coverage on the multisampled canvas / targets), the layers' root
      // darkening, tilt (grazeFlat) and sheen growth up the pile (grazeSheen) flattened toward the silhouette; was 0.55 /
      // 0.25 / 0 / 0 / 0.  A per-pixel dithered coverage (dither: true) and the band at 0.55 put sparse bright tips into
      // [FD-L10]'s silhouette band at panel_408b (high-pass skew +1.1 .. +1.6; look-dev ld3 a0-a2 / u0-u2))
      graze: 0.75, grazeN: 0.38, grazeW: 0.14, grazeFlat: 0.9, grazeSheen: 1.0,
      t: [0.03, 0.6, 0.8], curl: [55, 0.8, 5.0], lump: [70, 0.18, 0.10], part: [[30, 0.1, 0.82, 40, 0.55, 1.3],
        [60, 0.08, 0.85, 80, 0.55, 1.5]], fray: [1100, 0.03], ao: [0.5, 1.08, 1.8], tilt: 0.55,
      clump: [[22, 0.010, 1.3], [55, 0.0032, 1.3]], sheen: [0.5, 1.1], far: [2.2, 3.2] },
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
  // (all-lens review r1 CAB1-06: the figure read as coarse blotchy smoke smears 10-40 mm wide; P1046411 / 07 show a fine,
  // dense, straight vertical grain, ~1-3 mm streaks under a clear lacquer that mirrors the room: the streaks 6x finer
  // across (420 / m) and 3x along (8 / m: ~45:1), three octaves -- the coarse blotch octave gone --, the lacquer's
  // reflection a little stronger)
  // (all-lens review r2 FD9-04 / CAB2-03: neutral mauve-grey with no figure from 1-3 m -- (72, 68, 71) at cabin_fwd_406
  // against P1046406's warm (62, 49, 46), the lavatory's bi-fold doors (89, 84, 88) against P1046411's (48, 36, 36): a
  // warm base, R > G > B; the figure from ~6.7 mm streaks (150 / m across, three octaves to 600 / m) at +-35 %, so it
  // survives the pcSS band limit at 1-3 m; the bake's occlusion and window light on it (CABIN_FORM class 2: its baked
  // window light hardly differs between the divider, the lavatory and the arch, 0.10-0.17, so one darker base serves
  // them -- between P1046406's divider and P1046411 / 02's lavatory / arch exposures)
  veneer_walnut: { color: [0.094, 0.055, 0.042], envMapIntensity: 0.7, grain: { amp: 0.35, rough: 0.05, scale: [150, 150, 6], oct: 3 } },
  // (all-lens r2 CAB2-01: the exec seats' tone-on-tone stitching -- at the club stop's 2-3 m its sub-pixel dashes read as
  // scattered grey dots 30-50 levels under the leather; the GLB's 0.8 x the leather -> 0.95 x: the dashes' relief and
  // the crease carry the seam up close, at a distance they melt into the leather)
  stitch_light: { color: [0.428, 0.423, 0.413] },
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
  // (flight deck + yoke fix r4 FDY-O4-01 / FIDY4-06: the +-50 % bands, 5 cm across, and the cabin probe's window stripes
  // drew wavy white streaks down the plates in the footwell / pedestal views -- water down glass; the photos an even
  // satin with a faint brush: the window stripes faded by the roughness (CABIN_LOOK probe2), the bands broad and soft,
  // +-25 % over 12 x 60 cm; the brushed streaks kept fine, 0.6 mm at +-15 % of the reflection -- 1 mm at +-18 % read as
  // grey wood grain at the yoke close-up)
  // (all-lens review r1 FD8-04: the inner sub-panel (71, 80, 94) at panel_408b -- the level right, but cool and uniform
  // against P1046408's warm (74, 71, 79) with broad bright streaks: a warmer base, R >= G >= B)
  panel_titanium: { color: [0.262, 0.236, 0.222], metalness: 0.85, roughness: 0.27, specIn: 1.9,
    brush: { aniso: 0.75, axis: [1, 0, 0], rough: 0.05, len: 0.05, w: 0.0006, spec: 0.22, band: 0.38, bandLen: 0.6,
      bandW: 0.12, up: [0.40, 0.55, 0.32, 0.15] } },
  // (FDO3-01: the graphite face, the stack / pedestal gunmetal: a fine bead-blast grain -- isotropic, `len` 3-4 mm -- in
  // the roughness and the reflection, and a weaker band wander)
  panel_graphite: { specIn: 1.5, brush: { aniso: 0.35, axis: [1, 0, 0], rough: 0.04, len: 0.05, w: 0.0008, spec: 0.12,
    band: 0.2, bandLen: 0.12 } },
  pedestal_gunmetal: { specIn: 1.5, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  // (first-principles flight deck, round-3 minor: from the cabin the stack read as a dark slate block -- P1046408 / 09 show
  // the moulding in the tray's light mauve satin titanium, ~100-120 against the tray's 117)
  // (judge r1: 0.21 / CABIN_TRIM 0.75 read as pale flat plastic -- a mid mauve satin metal, the brush kept)
  stack_gunmetal: { color: [0.16, 0.142, 0.148], metalness: 0.7, roughness: 0.32, specIn: 1.6, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  // (flight deck fix r5 FDO4-05: a translucent glass jar from the quadrant view -- the probe's streaks; a solid satin
  // pewter: fewer, broader reflections, a shade warmer -- it read 116 / 124 / 140 against P1046408's 108 / 108 / 116)
  // (first-principles judge r2 FP2-06: a matte grey lump -- satin pewter with a highlight band, P1046408 / 09)
  pcl_pewter: { specIn: 1.5, roughness: 0.30, metalness: 0.8, color: [0.22, 0.21, 0.20] },
  // (rev R, yoke judge r5 FID5-05: the J band beside the column -- in the PCL's pewter it read a light-grey thumb on the
  // yoke branch, 105-117; the photos a darker grey tube with lit rolled edges, medians 26-57, p90 109-128 at P1046408 /
  // 09 / 10.  In the merged flight deck's light the pewter read 33-37 / p90 54-56, its edges unlit; the band's own dark
  // satin metal (the GLB's 0.075 / metallic 0.6) lit only by the cabin law read 24-26: a lighter, more metallic base with
  // a tighter sheen kept by the cabin law (SPEC_KEEP) -- 53-54 / p90 73-75 at P1046408 / 09)
  yoke_band: { color: [0.16, 0.155, 0.152], metalness: 0.9, roughness: 0.22, specIn: 2.5 },
  // (fix r5 FDO4-03: the palm tray's matte floor a warm mauve-grey -- the cabin's cool light had left it 108 / 113 / 128,
  // P1046408 123 / 114 / 130, P1046409 from above 106 / 100 / 113: R > G)
  // (all-lens r1 FD8-04: a soft mauve cushion, 109 against P1046408's crisp light titanium 121: a lighter, less pink
  // floor with more of its satin sheen; CABIN_TRIM 0.42 -> 0.5)
  tray_titanium: { color: [0.235, 0.208, 0.198], specIn: 1.6 },
  // the stitched black glareshield / crew leather: a fine pebble grain (1-2 mm) in the normal and the roughness
  // (a shade glossier in the viewer, 0.40: the rolled lip's highlight line of P1046408 / 10 against the hood)
  // (flight deck fix r1 FID-FD1-04: a coarser, deeper grain -- 1.4 mm pebbles, readable from the seats -- and the
  // satin sheen kept a little stronger inside, P1046409's highlight along the hood)
  leather_glareshield: { roughness: 0.38, specIn: 1.4, leather: { freq: 450, dist: 0.0004, bump: 1.0, rough: 0.07 } },
  leather_black: { specIn: 1.3, leather: { freq: 450, dist: 0.0004, bump: 1.0, rough: 0.07 } },
  leather_dark: { leather: { freq: 700, dist: 0.00025, bump: 0.8, rough: 0.05 } },
  leather_crew: { leather: { freq: 600, dist: 0.0003, bump: 0.8, rough: 0.05 } },
  leather_crew_shell: { specIn: 0.75, leather: { freq: 600, dist: 0.0003, bump: 0.8, rough: 0.05 } },
  // the crew harness webbing (flight deck fix r2 FDO2-09: flat grey ribbons): a fine woven grain in the normal and the
  // roughness (~0.7 mm)
  // (flight deck fix r3 FDO3-06: still flat grey card) a coarser, deeper weave (~1 mm) and more roughness wander
  // (flight deck fix FDY r1 FDY-O1-06: the straps read as flat hard-edged grey CAD ribbons -- the builder crowns them
  // across, seats.ribbon crown; here the woven webbing's sheen at grazing angles, AOPA / P1046409's satin bands)
  // (flight deck + yoke fix r4 FDY-O4-04: still wide flat light blue-grey bands up close -- 108 / (98, 110, 130) at the
  // cushion close-up, 150 from behind the seats -- where the AOPA photo's webbing is a dark charcoal woven belt with a
  // soft sheen and darker edges: a darker warm base, the sheen a third of it and warm, the weave deeper (0.5 mm) and in
  // the albedo too (+-8 %), the edges turned away from the eye a shade darker)
  // (all-lens review r1 FD8-05: in the sun the shoulder straps read as warm taupe ribbons, ~(128, 121, 117), with crisp
  // edges and no weave: a neutral, slightly cool base (R <= B), the sun at 0.5 on it, a coarser twill in the albedo
  // (~1.4 mm, +-8 %) that reads at ~1 m; the sheen neutral)
  harness: { color: [0.030, 0.031, 0.034], sunIn: 0.5, leather: { freq: 700, dist: 0.0005, bump: 1.0, rough: 0.16, albedo: 0.08, edge: 0.3 },
    sheen: 0.3, sheenColor: [0.10, 0.10, 0.105], sheenRoughness: 0.45 },
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
  // (all-lens review r1 CRA1-02: the cover's 0.5-1 mm dark groove flanks are sub-pixel at the crew eyes -- moving, the
  // 4x MSAA frame dotted them into chains of dark specks on the white cover): screen-space groove AA on the MOVING frames
  // (U.pcMove; the converged still keeps the crisp dark line its 2x passes resolve, [Y1d] / [Y1e]) -- where a display
  // pixel spans more than the groove (`gaa` [width m, colour]), the flank's colour fades toward 0.7 cover + 0.3 groove, so
  // a sub-pixel groove draws as a continuous soft grey line instead of dropouts)
  yoke_groove: { gaa: [0.0008, 0.55, 0.56, 0.57] },
  // (FDY r1 FIDY1-04: the pads' pebble grain, 1.1 mm, had faded to a flat tone at every crew-seat distance -- a 1.7 mm
  // grain at +-15 % with a lower roughness, the photos' grained, softly lit leather panels)
  // (flight deck fix FDY r2 FDY-O2-02: up close the 1.7 mm grain at +-15 % read as a coarse blue-grey granite / denim
  // speckle; P1046409 / 10 show smooth black leather with a very fine grain: 0.9 mm at -10 / +6 %, half the bump)
  yoke_leather: { fleece: { freq: 1100, oct: 2, lo: 0.9, hi: 1.06, dist: 0.00012, bump: 0.5 }, roughness: 0.28 },   // (fix r4: 0.32 -> 0.28)
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
  if (V.gaa) m.userData.pc12 = { ...(m.userData.pc12 || {}), gaa: V.gaa.slice() };
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
        const sv = gv.scale || sc;
        m.userData.pc12 = { ...(m.userData.pc12 || {}), grain: { scale: [sv[1], sv[2], sv[0]], oct: gv.oct ?? Math.max(1, Math.min(5, Math.round(g.detail ?? 4))),
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
    // (all-lens review r1 CAB1-03: the port ledge segment on the cargo door -- baked with the interior, build.AO_DOOR_CABIN --
    // had taken the exterior path: a pale block 3x lighter than the fixed ledge beside it)
    const doorCabin = /^door_/.test(part || '') && !!(o.geometry && o.geometry.attributes._ao);
    if (INTERIOR_PARTS.has(part) || groupOf(o) === 'Interior' || INTERIOR_MATERIALS.has(name) || doorCabin) {
      // one interior clone per material -- or per part:material where PART_TRIM has an entry (flight deck fix r2: the
      // hood's leather apart from the side-window sills of the same leather), or per 'yoke:<material>' where CABIN_TRIM
      // has a yoke-scoped entry (the yokes' own look, yoke track); the yokes' metal inserts mirror their own cabin probe
      // (YOKE_PROBE)
      // ?fp=1 (first-principles T-LIGHT experiment): the cabin light law ALONE -- no per-part / per-material hand trims
      // (PART_TRIM, CABIN_TRIM, the footwell skip, the form classes, the yoke probes): every surface lit by the same
      // radiometric law from its baked occlusion / window light and its own measured albedo.  Opt-in only; the shipped
      // look keeps the trims until this wins an A/B (it did not, first-principles round 2: see pc12/CLAUDE.md)
      const pt = FP_LIGHT ? undefined : PART_TRIM[part + ':' + name];
      const isYoke = /^yoke_/.test(part || '');
      const yk = !FP_LIGHT && isYoke && CABIN_TRIM['yoke:' + name] ? 'yoke:' + name : null;
      const ck = pt ? part : (yk || '');
      if (!interior.has(m)) interior.set(m, new Map());
      const im = interior.get(m);
      if (!im.has(ck)) {
        const c = clonePatched(m, { interior: true, cabinFill: FP_LIGHT ? null : (pt && pt.fill) || CABIN_TRIM[yk || name] || null,
          specKeep: SPEC_KEEP.has(name), reflDir: REFL_DIR.has(name),
          ...(pt && pt.specIn ? { specIn: pt.specIn } : {}), ...(pt && pt.sunIn ? { sunIn: pt.sunIn } : {}),
          ...(pt && pt.facing ? { facing: pt.facing } : {}), ...(!FP_LIGHT && FOOT_SKIP.has(name) ? { noFoot: true } : {}),
          ...(!FP_LIGHT && name in CABIN_FORM ? { form: CABIN_FORM[name] + 1 } : {}),
          ...(pt && pt.mirror ? { mirror: pt.mirror } : {}),
          probe: (!FP_LIGHT && isYoke && YOKE_PROBE[name]) || null });
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
const GLSL_SS = `uniform float uPcSS;
#define pcDX( v ) ( dFdx( v ) * uPcSS )
#define pcDY( v ) ( dFdy( v ) * uPcSS )
#define pcFW( v ) ( fwidth( v ) * uPcSS )
`;
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
  fsHead += 'varying float vPcFurT;\nuniform float uPcFurSoft;\nuniform float uPcFurSeed;\n' + GLSL_FUR;
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
  float pcFurA = 1.0, pcFurT = vPcFurT, pcFurCov = 1.0, pcFurGw = 0.0;
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
    // (all-lens review r1 FD8-01: a hard alpha test drew the grazing silhouettes -- the seat backs' rims at the fd_cabin
    // stop -- as 14 terraced steps with pixel jaggies) the layer's coverage, smooth over a pixel of the field (alpha to
    // coverage on the shell material: addFur), and at grazing view the outer layers thinned (the threshold raised with
    // the height below |n.v| 0.3): the outline a few soft layers instead of a stack of hard contour steps
    // (only toward the silhouette, |n.v| < 0.25: head-on the hard test as before -- soft coverage there had lifted the
    // shaded gaps between the tufts, flattening the pile [FD-L5] / [FD-L10] and deepening the close-range pits [FD-L10b])
    // (all-lens review r2 FD9-03: the armrests' and seat backs' grazing rims at the fd_cabin stop still read as terraced
    // 'cauliflower' florets -- r1's band was narrow: a wider grazing band (|n.v| < q.grazeN), the coverage edge widened
    // there (q.grazeW), the outer layers thinned more (q.graze); head-on the hard test as before.  Alpha to coverage
    // resolves on the antialiased canvas and the Picture targets alike; q.dither swaps it for a DITHERED test -- a stable
    // interleaved-gradient threshold per pixel, shifted per layer and per draw (uPcFurSeed) -- which single-sample frames
    // would need, but its sparse bright tips raised [FD-L10]'s high-pass skew at panel_408b (+0.2 -> +0.55): off)
    {
      float pcGz = smoothstep( 0.06, ${f4(q.grazeN ?? 0.25)}, abs( dot( normalize( vNormal ), normalize( vViewPosition ) ) ) );
      float pcTe = pcT + ( 1.0 - pcGz ) * t * ${f4(q.graze ?? 0.55)};
      // (first-principles judge r3: head-on the hard layer contours drew the pile as crisp sponge / coral cells --
      // q.soft [share, width]: the soft coverage edge everywhere, the width in field units head-on)
      float pcFw = max( fwidth( pcF ), 1e-4 ) + ${f4(q.grazeW ?? 0)} * ( 1.0 - pcGz ) + ${f4((q.soft || [0, 0])[1])} * pcGz;
      float pcSoft = uPcFurSoft * max( 1.0 - pcGz, ${f4((q.soft || [0, 0])[0])} );
      pcFurGw = pcSoft;
      float pcCov = mix( step( pcTe, pcF ), smoothstep( pcTe - pcFw, pcTe + pcFw, pcF ), pcSoft );
      if ( ${q.dither ? 'pcSoft > 0.001' : 'false'} ) {
        vec2 pcDq = gl_FragCoord.xy + vec2( 5.588238, 5.588238 ) * ( uPcFurSeed + 13.0 * t );
        float pcIg = fract( 52.9829189 * fract( dot( pcDq, vec2( 0.06711056, 0.00583715 ) ) ) );
        if ( pcCov < mix( 0.5, pcIg, pcSoft ) ) discard;
        pcFurCov = 1.0;
      } else {
        if ( pcCov < 0.02 ) discard;
        pcFurCov = pcCov;
      }
    }
    #ifndef FLAT_SHADED
      vec3 pcFnW = normalize( ( vec4( vNormal, 0.0 ) * viewMatrix ).xyz );
    #else
      vec3 pcFnW = normalize( cross( dFdx( vPcW ), dFdy( vPcW ) ) );
    #endif
    pcFurA = mix( ${f4(ao[0])}, ${f4(ao[1])}, pow( t, ${f4(ao[2])} ) ) * ( 1.0 + ${f4(lu[2])} * ( 2.0 * pcL - 1.0 ) );
    // (FD9-03) toward the silhouette the layers' root darkening and the tufts' tilt fade (q.grazeFlat): seen edge-on the
    // dark gaps between the stacked tops and their lit / shaded sides had drawn hard florets
    pcFurA = mix( pcFurA, ${f4(q.mean ?? 0.84)}, ${f4(q.grazeFlat ?? 0)} * pcFurGw );
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
  diffuseColor.rgb *= pcFurA;
  diffuseColor.a = pcFurCov;`);
    // the tufts' sides: the normal tilted down the field's slope (world gradient per metre, scaled to the first octave)
    fs = fs.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  normal = normalize( normal - ( viewMatrix * vec4( ${f4((q.tilt ?? 0.6) / oct[0][0])} * pcFurG + pcFurC, 0.0 ) ).xyz * ( 1.0 - ${f4(q.grazeFlat ?? 0)} * pcFurGw ) );`);
  }
  const sh = q.sheen || [0.5, 1.4];
  fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_SHEEN
    material.sheenColor *= pcFurA * mix( ${f4(sh[0])}, ${f4(sh[1])}, ${shell && q.grazeSheen ? `mix( pcFurT, 0.5, ${f4(q.grazeSheen)} * pcFurGw )` : 'pcFurT'} );
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
    sm.alphaToCoverage = true;          // the layers' soft coverage (FD8-01): resolved by the MSAA targets
    SHELL_MATS.set(base, sm);
  }
  mesh.userData.pcFur = { geometry: sg, material: sm, base };
  mesh.onAfterRender = (renderer, scene, camera, geometry, material) => {
    const u = mesh.userData.pcFur;
    if (!(material === u.base && FUR.on && u.geometry.instanceCount > 0)) return;
    // soft layer edges (FD8-01) inside the closed cabin only: the shells' alpha is their coverage (alpha to coverage)
    // and the target's alpha channel is left as the opaque cabin behind them wrote it (the canvas is transparent over
    // the CSS studio); outside -- a cutaway's seats against the studio -- the hard 0 / 1 edges as before
    const soft = U.cabinIn.value > 0.5;
    U.furSoft.value = soft ? 1 : 0;
    U.furSeed.value = (U.furSeed.value + 1) % 251;      // the dither's offset per draw (FD9-03)
    const gl = soft ? renderer.getContext() : null;
    if (gl) gl.colorMask(true, true, true, false);
    renderer.renderBufferDirect(camera, scene, u.geometry, u.material, mesh, null);
    if (gl) gl.colorMask(true, true, true, true);
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
      sm.alphaToCoverage = true;
      SHELL_MATS.set(u.base, sm);
      done.set(u.base, sm);
    }
    u.material = sm;
    u.geometry.instanceCount = n;
  });
  return done.size;
}

// CABIN MIRROR (all-lens review r2 CAB2-04): a gloss surface in the cabin -- the club tables' piano-black tops --
// reflects the cabin, not the studio: inside, the reflection ray from the surface point is traced against a box cabin
// (glTF X = BL, Y = WL, Z = STA) -- the ledge fascia below the ledge top, the side-wall lining above it with the cabin
// windows cut into it (fuselage_parts.FIXED_WINDOWS / DOOR_WINDOWS: Lame outlines W 0.300 x H 0.385, n 4.2, centre WL
// 2.1875), the headliner, the carpet -- each a multiple of the studio's blurred overhead radiance (as YOKE_PROBE), the
// window outlines softened by the roughness over the ray length.  P1046404 / 05 / 07: the dark top with the windows and
// the light wall mirrored sharply in it (judge: 38-45 / 63-106 / 116-124 / 220-234 p10 / p50 / p90 / p99)
const CABIN_WINDOWS = { port: [5.605, 6.200, 6.980, 7.958], stbd: [5.359, 6.205, 6.980, 7.730, 8.494],
  cz: 2.1875, hx: 0.150, hz: 0.1925, n: 4.2 };
const CABIN_BOX = { ledgeBL: 0.655, ledgeWL: 1.869, wallBL: 0.690, ceilWL: 2.66, floorWL: 1.259 };
function mirrorGLSL(m) {
  const f = (x) => (+x).toFixed(4);
  const k = m.k || [0.08, 1.0, 3.0, 1.1, 0.05];      // [ledge fascia, wall, window, headliner, carpet]
  const W = CABIN_WINDOWS, B = CABIN_BOX;
  const win = (side, xs) => xs.map((x) => `
				{ vec2 pcMd = abs( vec2( pcMh.z - ${f(x)}, pcMh.y - ${f(W.cz)} ) ) * vec2( ${f(1 / W.hx)}, ${f(1 / W.hz)} );
				  float pcMg = pow( pow( pcMd.x, ${f(W.n)} ) + pow( pcMd.y, ${f(W.n)} ), ${f(1 / W.n)} );
				  pcMw = max( pcMw, ${side} * ( 1.0 - smoothstep( 1.0 - pcMe, 1.0 + pcMe, pcMg ) ) ); }`).join('');
  return `
			{
				vec3 pcMp = ( vec4( - vViewPosition, 0.0 ) * viewMatrix ).xyz + cameraPosition;
				vec3 pcMr = reflectVec;
				float pcMs = pcMr.x >= 0.0 ? 1.0 : - 1.0;
				float pcMax = max( abs( pcMr.x ), 1e-4 );
				float pcMt1 = max( ${f(B.ledgeBL)} - pcMs * pcMp.x, 0.0 ) / pcMax;
				float pcMt2 = max( ${f(B.wallBL)} - pcMs * pcMp.x, 0.0 ) / pcMax;
				float pcMtc = pcMr.y > 1e-4 ? ( ${f(B.ceilWL)} - pcMp.y ) / pcMr.y : 1e9;
				float pcMtf = pcMr.y < - 1e-4 ? ( ${f(B.floorWL)} - pcMp.y ) / pcMr.y : 1e9;
				float pcMy1 = pcMp.y + pcMr.y * pcMt1;
				float pcMt = pcMy1 < ${f(B.ledgeWL)} ? pcMt1 : pcMt2;
				vec3 pcMh = pcMp + pcMr * pcMt;
				float pcMe = clamp( 0.03 + ${f(m.blur ?? 0.5)} * roughness * pcMt / ${f(W.hx)}, 0.03, 0.5 );
				float pcMw = 0.0;
				if ( pcMs < 0.0 ) {${win('1.0', W.port)}
				} else {${win('1.0', W.stbd)}
				}
				float pcMk = pcMy1 < ${f(B.ledgeWL)} ? ${f(k[0])} : mix( ${f(k[1])}, ${f(k[2])}, pcMw );
				pcMk = pcMtc < pcMt ? ${f(k[3])} : pcMk;
				pcMk = pcMtf < min( pcMt, pcMtc ) ? ${f(k[4])} : pcMk;
				vec3 pcMref = textureCubeUV( envMap, vec3( 0.0, 1.0, 0.0 ), 0.9 ).rgb * envMapIntensity;
				// (the cabin's white trim, not the blue sky overhead: the radiance's luminance, ${f(m.tint ?? 0.3)} of its colour)
				pcMref = mix( vec3( dot( pcMref, vec3( 0.2126, 0.7152, 0.0722 ) ) ), pcMref, ${f(m.tint ?? 0.3)} );
				pcEnv = mix( pcEnv, pcMref * pcMk, uCabinIn );
			}`;
}

export function installPatch(mat, extra = {}) {
  const f = { ...(mat.userData.pc12 || {}), ...extra };
  mat.userData.pc12 = f;
  const { paint, lining, glass, cabinGlass, collar, interior, cabinFill, back, grooves, stripes, fleece, rest, specKeep, reflDir, ao,
    leather, brush, grain, emisIn, specIn, sunIn, liningBase, probe, fur, noFoot, facing, form, gaa, mirror } = f;
  if (!paint && !lining && !glass && !collar && !interior && !back && !grooves && !stripes && !fleece && !ao && !leather && !brush && !grain && !fur && !gaa) return mat;
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
    roughnessFactor = clamp( roughnessFactor + ${f4(q.rough)} * pcLk * ( 2.0 * pcLn - 1.0 ), 0.05, 1.0 );${q.albedo ? `
    // (flight deck + yoke fix r4 FDY-O4-04: the harness webbing) the weave in the albedo too, x 1 -+ albedo, and the
    // webbing's edges -- turned away from the eye over the crowned strap -- a shade darker (\`edge\`)
    diffuseColor.rgb *= 1.0 + ${f4(q.albedo)} * pcLk * ( 2.0 * clamp( ( pcLn - 0.3 ) / 0.4, 0.0, 1.0 ) - 1.0 );` : ''}${q.edge ? `
    diffuseColor.rgb *= 1.0 - ${f4(q.edge)} * ( 1.0 - smoothstep( 0.15, 0.65, abs( dot( normal, normalize( vViewPosition ) ) ) ) );` : ''}
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
    if (fur) { ({ vs, fs, fsHead } = furPatch(fur, vs, fs, fsHead)); sh.uniforms.uPcFurSoft = U.furSoft; sh.uniforms.uPcFurSeed = U.furSeed; }
    if (gaa) {
      // screen-space groove AA (CRA1-02): the display pixel's footprint against the groove's width
      const f5 = (x) => (+x).toFixed(5);
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  {
    float pcGa = length( fwidth( vViewPosition ) ) / ${f5(gaa[0])};
    diffuseColor.rgb = mix( diffuseColor.rgb, vec3( ${f5(gaa[1])}, ${f5(gaa[2])}, ${f5(gaa[3])} ), uPcMove * smoothstep( 0.6, 1.8, pcGa ) );
  }`);
      fsHead += 'uniform float uPcMove;\n';
      sh.uniforms.uPcMove = U.pcMove;
    }
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
    if (interior && physical && ((cabinFill && cabinFill.length > 4 && +cabinFill[4] > 0) || probe || mirror)) {
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
        'return envMapColor.rgb * envMapIntensity;', `vec3 pcEnv = envMapColor.rgb * envMapIntensity + vec3( pcWin );${prbRet}${mirror ? mirrorGLSL(mirror) : ''}
			return pcEnv;`));
    }
    if (lining || interior) {
      for (const k of ['cabinAO', 'cabinIn', 'cabinKey', 'cabinDiff', 'cabinSpec', 'cabinFill', 'cabinOcc', 'cabinSky', 'cabinGain', 'cabinKnee', 'cabinRefl', 'cabinShade', 'cabinProbe', 'cabinProbe2', 'cabinFoot', 'cabinFormA', 'cabinFormB', 'cabinFormC', 'cabinFormD']) sh.uniforms['u' + k[0].toUpperCase() + k.slice(1)] = U[k];
      const lit = !mat.isMeshBasicMaterial;   // geometryNormal / geometryViewDir: the lit materials' lights chunks
      fsHead += 'uniform float uCabinKnee;\nuniform float uCabinAO;\nuniform float uCabinIn;\nuniform float uCabinKey;\nuniform vec2 uCabinDiff;\nuniform vec2 uCabinSpec;\nuniform float uCabinFill;\nuniform vec3 uCabinOcc;\nuniform vec2 uCabinSky;\nuniform vec3 uCabinGain;\nuniform vec4 uCabinRefl;\nuniform vec4 uCabinShade;\nuniform vec4 uCabinProbe;\nuniform vec4 uCabinProbe2;\nuniform vec4 uCabinFoot;\nuniform vec4 uCabinFormA[3];\nuniform vec4 uCabinFormB[3];\nuniform vec4 uCabinFormD[3];\nuniform vec4 uCabinFormC;\n';
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
      // (flight deck + yoke fix r4 FDY-O4-01: on the brushed titanium the window stripes drew thin wavy white streaks down
      // the plates in close / oblique views -- a 0.27-rough metal blurs a 6-7 deg stripe into a soft gradient: the stripes
      // fade to their mean over the roughness probe2.y .. probe2.z, and with the pixel's own change of azimuth)
      if ( uCabinProbe2.z > uCabinProbe2.y ) {
        float pcWb = max( smoothstep( uCabinProbe2.y, uCabinProbe2.z, material.roughness ), smoothstep( 0.02, 0.06, fwidth( sqrt( pcAz ) * 34.0 ) ) );
        pcWin = mix( pcWin, 0.3 * smoothstep( 0.04, 0.10, pcAz ) * ( 1.0 - smoothstep( 0.03, 0.16, abs( pcRW.y - 0.04 ) ) ), pcWb );
      }
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
    // fleece, which reaches into that box; nor -- flight deck + yoke fix r4 FIDY4-01 -- the walls round the knees, FOOT_SKIP)${fleece || fur || noFoot ? `
    if ( false )` : ''}
    pcDi *= 1.0 + uCabinFoot.x * pcFd * ( 1.0 - smoothstep( uCabinFoot.y, uCabinFoot.y + 0.12, pcPW.y ) )
      * ( 1.0 - smoothstep( uCabinFoot.z, uCabinFoot.z + 0.15, pcPW.z ) ) * ( 1.0 - smoothstep( 0.45, 0.8, pcNW.y ) );
${form && ao ? `
    {
      // CABIN FORM (CAB1-01): aft of the divider, the class's form light on the indirect diffuse (CABIN_FORM)
      vec4 pcFa = uCabinFormA[${form - 1}], pcFb = uCabinFormB[${form - 1}], pcFh = uCabinFormD[${form - 1}];
      float pcCab = pcIn${form === 3 ? '' : ' * smoothstep( 4.55, 4.75, pcPW.z )'};     // (the walnut, class 2: everywhere)
      // (side: + facing its own side wall / windows, - facing the aisle; glTF X = BL; height: glTF Y = WL)
      float pcOb = clamp( pcNW.x * sign( pcPW.x + 1e-4 ), - 1.0, 1.0 );
      float pcHt = pcPW.y < uCabinFormC.z ? mix( pcFh.x, pcFh.y, smoothstep( uCabinFormC.y, uCabinFormC.z, pcPW.y ) )
        : mix( pcFh.y, pcFh.z, smoothstep( uCabinFormC.z, uCabinFormC.w, pcPW.y ) );
      float pcFo = pcFa.x * pow( max( vPcAO.x, 0.03 ), pcFa.y ) * mix( pcFa.z, pcFa.w, smoothstep( 0.0, uCabinFormC.x, vPcAO.y ) )
        * mix( pcFb.x, pcFb.y, 0.5 + 0.5 * pcOb ) * mix( pcFb.z, pcFb.w, 0.5 + 0.5 * pcNW.y ) * pcHt;
      pcDi *= mix( 1.0, pcFo, pcCab );
    }` : ''}
    float pcSi = pcAO * pcKs * pcSs${specIn ? ` * mix( 1.0, ${(+specIn).toFixed(3)}, pcIn )` : ''}${cabinFill && cabinFill.length > 11 ? ` * mix( 1.0, pcNf, ${(+cabinFill[11]).toFixed(3)} )` : ''};${facing ? `
    {
      // PART_TRIM 'facing' [lo, hi, n0, n1, share on the diffuse] (flight deck + yoke fix r4 FIDY4-05): inside, the
      // reflections x lo where the world normal points down (y <= n0) .. x hi where it points up (y >= n1) -- the
      // glareshield's rolled lip catches the sky along its upper roll and darkens toward the fascia under it
      float pcFc = mix( ${(+facing[0]).toFixed(3)}, ${(+facing[1]).toFixed(3)}, smoothstep( ${(+facing[2]).toFixed(3)}, ${(+facing[3]).toFixed(3)}, pcNW.y ) );
      pcSi *= mix( 1.0, pcFc, pcIn );
      pcDi *= mix( 1.0, mix( 1.0, pcFc, ${(+(facing[4] || 0)).toFixed(3)} ), pcIn );
    }` : ''}${emisIn ? `
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
    // (all-lens review r1 CRA1-01) the procedural patches' band limits measure the DISPLAYED pixel: every dFdx / dFdy /
    // fwidth of their code scaled by uPcSS, the supersampling factor of the pass (Picture sets it per target: 2 in the
    // 2x still passes, 1 at the canvas size and in the temporal AA) -- the 2x still had switched the leather grain, the
    // fleece / pebble / harness noise, the carpet stripes and the brush streaks back on that the moving frames fade out
    // (a mottled sun band popping in on the pilot's sill each time the camera stopped); three's own chunks (included
    // after this hook) keep theirs
    sh.uniforms.uPcSS = U.pcSS;
    sh.fragmentShader = GLSL_SS + (fsHead + fs).replace(/\bdFdx\s*\(/g, 'pcDX(').replace(/\bdFdy\s*\(/g, 'pcDY(')
      .replace(/\bfwidth\s*\(/g, 'pcFW(');
  };
  // the rest matrix is a uniform: programs are shared
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' + (liningBase ? liningBase.join('/') : '') : ''}${glass ? (cabinGlass ? 'G' : 'g') : ''}${interior ? 'I' : ''}${cabinFill ? 'F' + cabinFill.join('/') : ''}${back ? 'B' + back.base.join('/') + (back.opaque ? 'o' : '') : ''}${collar ? 'C' + JSON.stringify(collar) : ''}${grooves ? 'R' + JSON.stringify(grooves) : ''}${stripes ? 'S' + JSON.stringify(stripes) : ''}${fleece ? 'W' + JSON.stringify(fleece) : ''}${specKeep ? 'K' : ''}${reflDir ? 'D' : ''}${ao ? 'A' : ''}${leather ? 'E' + JSON.stringify(leather) : ''}${brush ? 'U' + JSON.stringify(brush) : ''}${grain ? 'N' + JSON.stringify(grain) : ''}${emisIn ? 'X' + emisIn : ''}${specIn ? 'Q' + specIn : ''}${sunIn ? 'Z' + sunIn : ''}${probe ? 'Y' + JSON.stringify(probe) : ''}${fur ? 'H' + JSON.stringify(fur) : ''}${noFoot ? 'V' : ''}${facing ? 'J' + facing.join('/') : ''}${form ? 'M' + form : ''}${gaa ? 'T' + gaa.join('/') : ''}${mirror ? 'O' + JSON.stringify(mirror) : ''}`;
  mat.needsUpdate = true;
  return mat;
}

// clone that keeps the patch (Material.clone() drops onBeforeCompile but copies userData)
export function clonePatched(mat, extra = {}) {
  const m = mat.clone();
  return installPatch(m, extra);
}
