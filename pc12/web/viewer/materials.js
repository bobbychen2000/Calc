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
//   fleece  the crew seats' sheepskin pile: band-limited world-space clumps in the albedo and the normal
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
  probe2: qv('cabProbe2', [2.0, 0, 0, 0]) };
U.cabinShade.value.set(...CABIN_LOOK.shade);
U.cabinProbe.value.set(...CABIN_LOOK.probe);
U.cabinProbe2.value.set(...CABIN_LOOK.probe2);
U.cabinKnee.value = CABIN_LOOK.knee;
U.cabinOcc.value.set(...CABIN_LOOK.occ);
U.cabinGain.value.set(...CABIN_LOOK.gain);
U.cabinSky.value.set(...CABIN_LOOK.sky);
U.cabinKey.value = CABIN_LOOK.key;
U.cabinDiff.value.set(...CABIN_LOOK.diff);
U.cabinSpec.value.set(...CABIN_LOOK.spec);
U.cabinFill.value = CABIN_LOOK.fill;
U.cabinRefl.value.set(...CABIN_LOOK.refl);
// per material inside: [share of the fill (uCabinFill ^ share), own factor] on the studio's diffuse light -- the light
// trim gets the cove / window light (the cabin lining all of it, the leathers part), the flight deck's grey lining
// round the windshield (centre post, pillars, the walls under the side windows: P1046408 ~70-110) faces aft-down at
// the studio's bright floor and read near-white (~200) without its own factor
// (the trim with a share of the fill keeps that share of its light out of the window sky law: the cabin lining all of
// it, T4b / T14; the flight deck's anthracite lining_flightdeck has no entry since look L5: the sky law and the baked
// occlusion darken it where the photos do)
const CABIN_TRIM = { lining: [1, 1], leather: [0.5, 1], leather_crew: [0, 0.8], leather_dark: [0.6, 1],
  lav_white: [0.8, 1], toilet_white: [0.8, 1], psu_housing: [0.7, 1],
  // the crew seats' lavender-grey sheepskin (P1046408 / 09 ~90-130 in the cabin light, B > R)
  sheepskin: [0, 0.52],     // (0.55 before the flight deck fix r1's soft knee / gain 27)
  // the graphite of the side consoles, the overhead panel, the AFCS strip: near-black (P1046408 consoles 4-9, the
  // overhead ~45 under the windshield's light; T14 <= 50)
  panel_dark: [0, 0.5],
  // the satin titanium sub-panels, band and stack (P1046408 66-78; its own reflections carry it, SPEC_KEEP; 0.45 on
  // the look track's geometry, 0.6 since the flight deck r1 merge: the proud plates and the moulded face round them
  // rendered them 64, now 72) and the graphite panel face round the PDU row and the cheek legs (the merge: 64, a shade
  // under the plates as the Garmin / brochure renders; P1046408 reads the face ~90)
  panel_titanium: [0, 0.8], panel_graphite: [0, 0.85],     // (titanium 0.6 -> 0.8 with the warmer base, fix r2 FDO2-01)
  // the near-black footwell carpet (P1046408 5-15) and the PC-24 yoke's white shield (P1046408 ~208)
  carpet_flightdeck: [0, 0.85], yoke_white: [0, 1.08],
  // the flight deck's anthracite lining -- posts, window surrounds, side walls, headliner (flight deck fix r1 FDO1-04 /
  // FID-FD1-09: with the soft-knee window light (below) the posts next to the glazing read 150-170, light grey slabs;
  // P1046410's posts 88-97, P1046408's 120-128 in its brighter frame)
  // (flight deck fix r2 FDO2-01 / 03: 0.72 -> 0.5 -- the A-pillar / side-window surround still read as a light slab,
  // 98-102 at the crew stops; now ~80 with the darker reveal face and the satin edge bead of the builder)
  lining_flightdeck: [0, 0.5],
  // the glazing surround's darker satin inner face (fix r2 FDO2-03; without a factor it read 85, as light as the lining)
  lining_fd_reveal: [0, 0.5],
  // the eyebrow fascia (flight deck fix r2b FDO2-01: the light band over the PDUs, 126 from the crew seats and 122 at
  // panel_408b against P1046408's 96-104 and P1046410's 65-91)
  panel_grey: [0, 0.72],
  // the dark cove below the outer sub-panels (flight deck fix r3 FID-FD3-01: P1046408's cove ~41 at the fitted camera;
  // at x 1 it read 28)
  fd_cove: [0, 1.45] };
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
  'flight_deck:leather_glareshield': { specIn: 0.35, roughness: 0.55, sunIn: 0.22, specularIntensity: 1.0,
    specularColor: [0.375, 0.435, 0.5] },
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
};
// the satin / gloss trim of the flight deck keeps its reflections inside (FD-J10: the facing weights cut the titanium,
// the gunmetal, the bezels, the black leather and the displays to flat matte); the sky law and the occlusion still apply
// (+ the flight deck's shared detail materials (seed) and the geometry tracks' glossy ones: the annunciator / key caps,
// the smoked acrylic sun visors.  Every other new material -- stitch_thread, rubber_black, legend_plate, the fda_ /
// fdb_ trim -- takes the interior law with no entry (diffuse x gain x occlusion x window light, reflections by facing),
// and an emissive one (legend_lit, the annunciators' glow, fdb_cb_glow_*) keeps its emission as built)
const SPEC_KEEP = new Set(['panel_titanium', 'panel_graphite', 'pedestal_gunmetal', 'stack_gunmetal', 'pcl_pewter', 'chrome_trim', 'bezel_black',
  'leather_glareshield', 'leather_black', 'yoke_white', 'display_page', 'screen',
  'annun_amber', 'annun_red', 'annun_green', 'annun_blue', 'fdb_visor',
  // flight deck fix r1: the unlit smoked caps keep their gloss (FID-FD1-03)
  'annun_off_red', 'annun_off_amber', 'annun_off_green']);
// the SPEC_KEEP trim whose reflections CABIN_LOOK `refl` weighs by where they point (flight deck fix r2b): the satin
// metals -- not the displays, screens, bezels and caps (their glass / gloss keeps the reflection it had: weighted, the
// bezels and the pages' dark fields added ~0.7 % of panel_408b's pixels under 40, [FD-L6]) nor the black leathers (the
// hood's sheen from the crew seats points at the glazing anyway; from behind, at panel_408b, weighted it took the
// glareshield from 54 to ~52, [FD-L3] >= 50)
const REFL_DIR = new Set(['panel_titanium', 'panel_graphite', 'pedestal_gunmetal', 'stack_gunmetal', 'pcl_pewter']);

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
  sheepskin: { color: [0.262, 0.232, 0.276], sheenColor: [0.37, 0.34, 0.40], sunIn: 0.45,
    fleece: { ridge: true, gamma: 1.2, bump: 0.9, stretch: [1, 1, 1], warp: 0.12, edge: [0.2, 0.8], rm: 0.42,
      layers: [[520, 0.90, 1.05, 0.0001], [200, 0.78, 1.08, 0.0003], [95, 0.74, 1.10, 0.0007]],
      clump: [24, 0.12], rim: [0.5, 0.6] }, sheenRoughness: 0.8 },
  // the pleated divider curtain: deep burnt orange in P1046406 (77/23/0), read tan (208/166/116) under the old cabin light
  curtain: { color: [0.36, 0.11, 0.012] },
  // the walnut divider / FR34 header / table tops: the lookdev's dark grey-brown under a gloss lacquer read as grey-mauve
  // plastic in the tour (review r3 NAV3-04: the unoccluded white studio in its clear coat, lifted by the interior's
  // +0.6 EV, ~154/144/139); the panels stand in a narrow passage and mirror the cabin, not the studio: less
  // environment (an occlusion stand-in) and a warmer, more saturated brown (P1046406: dark walnut, ~sRGB 75/55/40)
  // flight deck r1 LOOK (L6): the figure -- the lookdev's render_grain (streaks along the vertical, along the station on
  // the table tops) at `amp` of the albedo and +-`rough` (fd_ngx2281_cfsjets_entry_left: strong vertical streaks)
  veneer_walnut: { color: [0.075, 0.042, 0.022], envMapIntensity: 0.5, grain: { amp: 0.28, rough: 0.05 } },
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
  panel_titanium: { color: [0.235, 0.222, 0.212], metalness: 0.75, roughness: 0.26, specIn: 2.2,
    brush: { aniso: 0.75, axis: [1, 0, 0], rough: 0.05, len: 0.05, w: 0.0006, spec: 0.15, band: 0.12, bandLen: 0.16,
      bandW: 0.010, up: [0.40, 0.55, 0.32, 0.15] } },
  // (FDO3-01: the graphite face, the stack / pedestal gunmetal: a fine bead-blast grain -- isotropic, `len` 3-4 mm -- in
  // the roughness and the reflection, and a weaker band wander)
  panel_graphite: { specIn: 1.5, brush: { aniso: 0.35, axis: [1, 0, 0], rough: 0.04, len: 0.05, w: 0.0008, spec: 0.12,
    band: 0.2, bandLen: 0.12 } },
  pedestal_gunmetal: { specIn: 1.5, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  stack_gunmetal: { specIn: 1.5, brush: { aniso: 0, axis: [1, 1, 1], rough: 0.05, len: 0.0035, w: 0.0035, spec: 0.12,
    band: 0.18, bandLen: 0.10 } },
  pcl_pewter: { specIn: 1.3 },
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
  harness: { leather: { freq: 1100, dist: 0.00028, bump: 1.0, rough: 0.16 } },
  // the G3000 PRIME pages brighter inside (LK-07: x1.25 read 78-95 against the photos' >= 90 at the cabin exposure)
  display_page: { emisIn: 1.45 },
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
  if (V.fleece) m.userData.pc12 = { ...(m.userData.pc12 || {}), fleece: { ...V.fleece } };
  for (const k of ['leather', 'brush']) if (V[k]) m.userData.pc12 = { ...(m.userData.pc12 || {}), [k]: { ...V[k] } };
  if (V.emisIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), emisIn: V.emisIn };
  if (V.specIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), specIn: V.specIn };
  if (V.sunIn) m.userData.pc12 = { ...(m.userData.pc12 || {}), sunIn: V.sunIn };
  if (V.liningBase) m.userData.pc12 = { ...(m.userData.pc12 || {}), liningBase: V.liningBase };
  if (V.brush) { m.anisotropy = V.brush.aniso; }
  for (const k of ['roughness', 'metalness', 'specularIntensity', 'envMapIntensity']) if (V[k] != null) m[k] = V[k];
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
  const interior = new Map();  // material -> its interior clone
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
      // hood's leather apart from the side-window sills of the same leather)
      const pt = PART_TRIM[part + ':' + name], ck = pt ? part : '';
      if (!interior.has(m)) interior.set(m, new Map());
      const im = interior.get(m);
      if (!im.has(ck)) {
        const c = clonePatched(m, { interior: true, cabinFill: (pt && pt.fill) || CABIN_TRIM[name] || null, specKeep: SPEC_KEEP.has(name), reflDir: REFL_DIR.has(name),
          ...(pt && pt.specIn ? { specIn: pt.specIn } : {}), ...(pt && pt.sunIn ? { sunIn: pt.sunIn } : {}) });
        if (pt && pt.roughness != null) c.roughness = pt.roughness;
        if (pt && pt.specularColor && c.specularColor) c.specularColor.copy(lin(pt.specularColor));
        if (pt && pt.specularIntensity != null) c.specularIntensity = pt.specularIntensity;
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

export function installPatch(mat, extra = {}) {
  const f = { ...(mat.userData.pc12 || {}), ...extra };
  mat.userData.pc12 = f;
  const { paint, lining, glass, cabinGlass, collar, interior, cabinFill, back, grooves, stripes, fleece, rest, specKeep, reflDir, ao,
    leather, brush, grain, emisIn, specIn, sunIn, liningBase } = f;
  if (!paint && !lining && !glass && !collar && !interior && !back && !grooves && !stripes && !fleece && !ao && !leather && !brush && !grain) return mat;
  const restP = !!(rest && (collar || grooves || stripes || grain));
  const worldP = !!(fleece || leather || brush);
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
    if (fleece) {
      // sheepskin pile (review r4 INT8-04): band-limited fBm clumps in world space darken / lighten the albedo and bump
      // the normal (the stacks' surface-gradient bump, explicit forward differences); fades out where a tuft is sub-pixel
      const q = fleece, f4 = (x) => (+x).toFixed(4);
      if (q.ridge) {
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
    if (lining || interior) {
      for (const k of ['cabinAO', 'cabinIn', 'cabinKey', 'cabinDiff', 'cabinSpec', 'cabinFill', 'cabinOcc', 'cabinSky', 'cabinGain', 'cabinKnee', 'cabinRefl', 'cabinShade', 'cabinProbe', 'cabinProbe2']) sh.uniforms['u' + k[0].toUpperCase() + k.slice(1)] = U[k];
      const lit = !mat.isMeshBasicMaterial;   // geometryNormal / geometryViewDir: the lit materials' lights chunks
      fsHead += 'uniform float uCabinKnee;\nuniform float uCabinAO;\nuniform float uCabinIn;\nuniform float uCabinKey;\nuniform vec2 uCabinDiff;\nuniform vec2 uCabinSpec;\nuniform float uCabinFill;\nuniform vec3 uCabinOcc;\nuniform vec2 uCabinSky;\nuniform vec3 uCabinGain;\nuniform vec4 uCabinRefl;\nuniform vec4 uCabinShade;\nuniform vec4 uCabinProbe;\nuniform vec4 uCabinProbe2;\n';
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
    float pcKs = mix( 1.0, ${specKeep ? (reflDir ? 'mix( uCabinRefl.x, 1.0, smoothstep( uCabinRefl.y, uCabinRefl.z, dot( pcRW, normalize( vec3( 0.0, uCabinRefl.w, - 1.0 ) ) ) ) )' : '1.0') : 'mix( uCabinSpec.x, uCabinSpec.y, smoothstep( - 0.5, 0.7, pcRW.y ) )'}, pcIn );${reflDir ? `
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
    float pcDi = pcAO * pcKd * pcSd;
    float pcSi = pcAO * pcKs * pcSs${specIn ? ` * mix( 1.0, ${(+specIn).toFixed(3)}, pcIn )` : ''};${emisIn ? `
    totalEmissiveRadiance *= mix( 1.0, ${(+emisIn).toFixed(3)}, pcIn );` : ''}
    reflectedLight.directDiffuse *= pcKk; reflectedLight.directSpecular *= pcKk;
    reflectedLight.indirectDiffuse *= pcDi; reflectedLight.indirectSpecular *= pcSi;
    // the flight deck's daylight shade (flight deck fix r3 FID-FD3-02): a cool tint on the indirect diffuse, more where the
    // surface faces the glazing (forward / up / outboard)
    reflectedLight.indirectDiffuse *= mix( vec3( 1.0 ), uCabinShade.xyz, uCabinShade.w * pcFd * ( 0.6 + 0.4 * clamp( dot( pcNW, normalize( vec3( 0.0, 0.5, - 1.0 ) ) ), 0.0, 1.0 ) ) );
    // (the clear coat and the sheen take the cabin light outside too: they had kept the full studio light, so the
    // sheepskin and the lacquered walnut read near-white through the closed glazing -- flight deck r1 LOOK)
    #ifdef USE_CLEARCOAT
      clearcoatSpecularDirect *= pcKk; clearcoatSpecularIndirect *= mix( pcAO, pcSi, pcIn );
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
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' + (liningBase ? liningBase.join('/') : '') : ''}${glass ? (cabinGlass ? 'G' : 'g') : ''}${interior ? 'I' : ''}${cabinFill ? 'F' + cabinFill.join('/') : ''}${back ? 'B' + back.base.join('/') + (back.opaque ? 'o' : '') : ''}${collar ? 'C' + JSON.stringify(collar) : ''}${grooves ? 'R' + JSON.stringify(grooves) : ''}${stripes ? 'S' + JSON.stringify(stripes) : ''}${fleece ? 'W' + JSON.stringify(fleece) : ''}${specKeep ? 'K' : ''}${reflDir ? 'D' : ''}${ao ? 'A' : ''}${leather ? 'E' + JSON.stringify(leather) : ''}${brush ? 'U' + JSON.stringify(brush) : ''}${grain ? 'N' + JSON.stringify(grain) : ''}${emisIn ? 'X' + emisIn : ''}${specIn ? 'Q' + specIn : ''}${sunIn ? 'Z' + sunIn : ''}`;
  mat.needsUpdate = true;
  return mat;
}

// clone that keeps the patch (Material.clone() drops onBeforeCompile but copies userData)
export function clonePatched(mat, extra = {}) {
  const m = mat.clone();
  return installPatch(m, extra);
}
