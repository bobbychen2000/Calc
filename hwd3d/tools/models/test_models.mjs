// Node tests of the detailed aircraft models (hwd3d Phase 3, M2).   node tools/models/test_models.mjs [--json=out/test_models.json]
// For every model in js/aircraft/models.js that exists on disk (PC12, SF50), converted with the registry's own options
// (js/aircraft/models.js MODEL_LOAD_OPTS: ground plane, added light anchors):
//   1. parse + convert (js/aircraft/glb.js): accessors decode, every triangle index in range, normals unit length
//   2. bounding box (rest pose, gear down) vs the FAA ACD dimensions in data/ga_types.json: length, span (with winglets
//      when the ACD has only that value), height (ACD "tail height at OEW") within 2 %
//   3. origin on the wheel contact: main-gear contacts symmetric about the centreline (|zL + zR| < 1 cm, x = 0), their
//      height = minus the source's documented static tyre deflection (pc12: tyres sunk into its own ground; SF50: 0)
//      +-1 mm, nose / tail wheel touching (within its deflection +-2 mm), nothing but tyres below the ground, tyres not
//      deeper than their deflection; PC-12 propeller clearance vs the sourced 0.32 m
//   4. pivots present: the kinds the drawable animates (PC12: spin, 5 pitch, 2 flap, 2 aileron, 2 tab, 2 elevator, rudder,
//      trim, 2 door, 3 gear, 2 gear_door, 6 brace; SF50: spin, 3 gear, >= 2 flap, roll and pitch surfaces); none unsupported
//   5. kinematics: brace closure (knee and leg attach point) at gear 1 / 0.5 / 0, left / right symmetry of the deflections;
//      control-surface travel vs the type certificate (sign of each surface measured from its trailing-edge motion, so an
//      inverted range fails: fix round 1, SF50 ruddervator tabs); lowest point over the whole gear sweep (retraction needs
//      that much height above the ground)
//   6. gear retracted (gear = 0): every gear vertex against the airframe's lower skin (the lowest downward-facing
//      fuselage / wing / gear-door skin point within +-0.6 m fore-aft on the same butt line +-5 cm, which bridges the
//      wheel-well openings); only tyres may protrude, by at most the documented amount (PC12: POH, tyres protrude ~1 in
//      = 25.4 mm; tolerance 10 mm), anything else <= 10 mm; also the lowest retracted point of the whole aircraft
//   7. light anchors: every light node the GLB names reaches model.lights (fix round 1: strobeTail / iceLight were
//      dropped); the anti-collision lights drawn = the documented count; landing lights where the type has them
//   8. registration panels: every field the builder wrote is kept (fix round 1: text_dir was dropped)
//   9. traffic frame: js/aircraft/models.js frame = the measured model (5 mm), withModelFrame(gaDims(type)) hands traffic /
//      ground physics the model's gear layout (fix round 1: gaDims' class rule was off by up to 0.72 m for the SF50)
//  10. type-specific shape checks: SF50 upswept wing tip at the 38.7 ft span with flush lenses, nacelle fillets and a raised
//      D inlet lip; PC-12 cabin window count, window / door stations and the wing front-view silhouette vs the Pilatus
//      drawings (fix round 2), and the remaining cabin / wing height offset (KNOWN pc12 loft item)
//  11. the drawable (js/aircraft/detailed.js, Node with a stub WebGL context): every item carries the screen-door alpha in
//      both the loaded and the placeholder path, every field js/live/aircraft.js sets is synced to the placeholder, the
//      aircraft programs read uAlpha, spinning groups keep the aircraft's motion in their prevModel, CPU arrays released
//  12. provenance: js/aircraft/models/SOURCES.json hashes = the files on disk (and = the builder's own record); every image
//      in docs/phase3 has a caption in docs/phase3/SOURCES.json, and every caption that claims to show the current model
//      names the current file hash (fix round 1: stills and SOURCES of a superseded SF50 build were presented as current)
// Exit code 1 when a check fails. Read-only: no file under pc12/ or js/ is written.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { initGL, Program } from '../../js/gl.js';
import { convertGLB, parseGLB, KINDS } from '../../js/aircraft/glb.js';
import { Kinematics, xform, rotAbout } from '../../js/aircraft/kinematics.js';
import { MODELS, MODEL_LOAD_OPTS, withModelFrame } from '../../js/aircraft/models.js';
import { DetailedAircraft, SYNC_KEYS, ACOBJ_FS, ACOBJ_SHADOW_FS, GLASS_FS, PROP_BLUR } from '../../js/aircraft/detailed.js';
import { gaDims } from '../../js/aircraft/ga_dims.js';

const HWD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const ACD = JSON.parse(fs.readFileSync(path.join(HWD, 'data/ga_types.json'), 'utf8')).types;
const results = []; let fails = 0, known = 0;
const check = (model, name, ok, detail) => {
  const kn = !ok && KNOWN[model] && KNOWN[model][name]; const isKnown = !!(kn && detail && detail[kn.key] != null && detail[kn.key] <= kn.limit);
  const status = ok ? 'PASS' : isKnown ? 'KNOWN' : 'FAIL'; if (status === 'FAIL') fails++; if (isKnown) known++;
  results.push({ model, name, ok: !!ok, status, detail, known: isKnown ? kn.note : undefined });
  console.log(`${status} ${model} ${name}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}${isKnown ? '\n      known: ' + kn.note : ''}`);
};
const info = (model, name, detail) => { results.push({ model, name, ok: null, status: 'INFO', detail }); console.log(`INFO ${model} ${name}: ${JSON.stringify(detail)}`); };
const r3 = (v) => Math.round(v * 1000) / 1000;
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const REQUIRED = {
  PC12: { spin: 1, pitch: 5, flap: 2, aileron: 2, tab: 2, elevator: 2, rudder: 1, trim: 1, door: 2, gear: 3, gear_door: 2, brace: 6 },
  SF50: { spin: 1, gear: 3, flap: 2 },
};
// Known deviations of a model from a check, measured and reported rather than hidden: the check prints KNOWN (not PASS)
// while the measured value stays within `limit`; beyond it, it FAILS. Each one is an open item in docs/phase3_models.md.
const KNOWN = {
  provenance: {
    'docs/phase3 in docs/ATTRIBUTION.md and in tools/check_airport.py SOURCES coverage': { key: 'missing', limit: 2,
      note: 'not M1 / M2 files (docs/ATTRIBUTION.md, tools/check_airport.py): the exact diffs are in docs/phase3_models.md section 8 items 5 / 6 for their owners; until then this test checks every docs/phase3 caption and licence notice itself. Must be closed before the artifact is published.' },
  },
  PC12: {
    'gear retracted: only tyres protrude (documented amount)': { key: 'other_max_protrusion_mm', limit: 70,
      note: 'pc12 model (not hwd3d): with the mains retracted, the trailing-link arm / axle near the trunnion (gear_leg material, STA ~6.03, BL ~1.74) hangs below the local wing lower skin (67 mm in pc12/out; 51 mm in the fix-round-2 build, whose wing inboard of BL 2.265 is up to 4 cm lower); the POH says only the tyres protrude (~1 in). Open item for pc12/ (owner), not changed here.' },
    'cabin crown / wing height above the ground vs Pilatus drawing 190.10.40.432': { key: 'offset_max_mm', limit: 160,
      note: 'pc12 model (not hwd3d; pc12/model/fuselage.py control lines): measured in fix round 2 on drawing 190.10.40.432 (side view registered on 9 frame stations, the spinner tip and the ground line; tail top then reads 4.266 m vs 4.26): the cabin crown is WL 2.768 on the drawing and 2.630 in pc12 (keel 0.938 vs 0.800), the wing ~0.12 m lower too, while the nose and the propeller axis agree. Fixing it moves the cabin loft, glazing, wing root, gear legs and fin: a pc12 owner item (its drawings-first method). Windows / doors are placed relative to the crown, so their look on the fuselage is right.' },
  },
};
const TYRE_PROTRUSION = { PC12: { max_m: 0.0254, src: 'POH NGX (pc12/CLAUDE.md sourced facts): main tyres protrude ~1 in when retracted' } };
// static tyre deflection of the source model (tyres sunk into its own ground plane, which is the hwd3d origin height):
// pc12/model/gear.py MAIN_AXLE z 0.265 vs MAIN_TYRE R 0.2795, NOSE_AXLE z 0.212 vs NOSE_TYRE R 0.2225
const DEFLECTION = { PC12: { main: 0.0145, nose: 0.0105, src: 'pc12/model/gear.py: axle heights vs free tyre radii' }, SF50: { main: 0, nose: 0, src: 'SF50 builder: tyres touch the ground plane' } };
// sourced propeller ground clearance (gear down, static): pc12/CLAUDE.md "prop clearance 0.32"
const PROP_CLEARANCE = { PC12: { m: 0.32, tol: 0.02, src: 'pc12/CLAUDE.md sourced facts: prop clearance 0.32 m' } };
// Control-surface travels from the type certificate (deg; up = trailing edge up). SF50: FAA TCDS A00018CH Rev. 7
// (tools/models/sf50/SF50_FACTS.md S1), read through the FAA DRS web viewer after DRS's data API answered 403. Fix round 2:
// no copy outside DRS was found (the EASA TCDS has no travels), so these values are **inf (DRS)** until the owner rules on
// that access route (docs/phase3_sf50.md section 7); the check keeps the model consistent with them, it does not make them
// obs. Each part's sign convention is MEASURED here (trailing-edge motion for a +10 deg rotation), so a range written with
// the wrong sign fails.
const TRAVEL = {
  SF50: [
    { parts: ['aileron_L', 'aileron_R'], up: 15, down: 11.5, src: '[inf (DRS): owner decision pending] TCDS A00018CH "Aileron Up 15.0 Down 11.5"' },
    { parts: ['ail_tab_L'], up: 10, down: 10, src: '[inf (DRS): owner decision pending] TCDS A00018CH "LH Aileron Trim Up 10.0 Down 10.0"' },
    { parts: ['ruddervator_L', 'ruddervator_R'], up: 20, down: 15, field: 'pitchRange', src: '[inf (DRS): owner decision pending] TCDS A00018CH "Ruddervator Pitch Up 20.0 Down 15.0"' },
    { parts: ['rv_tab_L', 'rv_tab_R'], up: 7, down: 18, src: '[inf (DRS): owner decision pending] TCDS A00018CH "Ruddervator Trim Up 7.0 Down 18.0"' },
    { parts: ['yaw_sas_L', 'yaw_sas_R'], up: 15, down: 15, src: '[inf (DRS): owner decision pending] TCDS A00018CH "Yaw SAS Up 15 Down 15"', lateral: true },
  ],
};
const ANTICOLLISION = { SF50: { n: 3, src: 'AFM P/N 31452-001 Kinds of Operation "Anti-Collision Lights 3/3" (2 tips + tail)' } };
// PC-12 reference measurements (fix round 2), re-digitised from the Pilatus "PC-12 NGX Model Building Plan"
// (https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf; the PDF and the
// rasters stay out of the repository): p.9 = drawing 190.10.40.432 at 200 dpi, side view (from port) scaled on its 9
// labelled frame lines EF1..FR40 (328.44 px/m, nominal 1:24 = 328.08; residuals <= 1.3 mm), x from the spinner tip at
// STA 0.39 (pc12 anchor), z from the drawn ground line (tail top then 4.266 m vs the published 4.26); starboard detail view
// registered on FR16; front view scaled on the 4530 track dimension (328.04 px/m), z from the tyre bottoms. Stations are
// window / door outline centres (+-~5 mm reading). Starboard windows from the p.5 livery sheet (to scale: its port windows
// agree with the drawing to <= 15 mm); the drawing's partial starboard view shows 4 openings at the mirrored port stations
// (5.602, exit 6.199, 6.978, 7.955) - a conflict between the two Pilatus documents, recorded in docs/phase3_models.md.
// SF50 AFM P/N 31452-001 Fig 1-1 front view (fix round 2), page raster 2550 x 3300 px: registered on the main-wheel bottoms
// (y 2550) at 104.9 px/m (its fuselage width 178 px = 1.697 m; the span extension lines give 102.3, the figure is not drawn
// to one scale); its fuselage max-width line then reads WL 1.56-1.58 (model 1.555-1.565). Wing outline line centres at the
// butt lines (both sides agree within 5 mm; the BL 1.6 lower line is hidden by the gear); the tip top point is 6.4 px
// (0.061 m, +-0.02 m) above the extrapolated upper line on both tips. These few numbers are measurements of a published
// figure, like the dimensions in SF50_FACTS.md; the AFM itself stays out of the repository (owner question F20).
const AFM_SF50 = {
  bl: [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.2], up: [1.165, 1.201, 1.239, 1.275, 1.311, 1.341, 1.384], lo: [0.884, 0.934, 0.987, 1.039, 1.090, 1.136, 1.206],
  top_below_maxwidth_bl1_6: 0.43, tip_rise: [0.04, 0.09],
  src: 'AFM P/N 31452-001 Fig 1-1 front view, measured in fix round 2 (tools/models/sf50/SF50_FACTS.md S5)',
};
const PILATUS_PC12 = {
  port: { airstair: 4.971, windows: [5.607, 6.201, 6.980], cargo: 8.242, cargo_window: 7.961 },
  stbd: { windows: [5.339, 6.967, 7.716, 8.469], exit: 6.203, exit_window: 6.192 },
  window_below_crown: 0.583, window_w: 0.295, window_h: 0.380, crown: 2.768,
  src_layout: 'drawing 190.10.40.432 (MBP p.9) side view (port) + starboard detail view; MBP p.5 livery sheet (starboard windows)',
  wing: { bl: [2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 7.5], up: [1.355, 1.398, 1.443, 1.532, 1.620, 1.712, 1.815, 1.873], lo: [null, 1.105, 1.166, 1.291, 1.413, 1.535, 1.654, 1.712], winglet_rise: 0.262, winglet_top_wl: 2.135 },
  src_wing: 'drawing 190.10.40.432 (MBP p.9) front view, port wing: upper / lower outline WL per butt line (BL 2.0 lower hidden by the gear)',
};

// stub WebGL2 context for the drawable test (Mesh / Program creation only; nothing is drawn)
initGL({ getContext: () => new Proxy({}, { get: (t, k) => (typeof k === 'string' && /^[A-Z0-9_]+$/.test(k) ? 1 : () => ({})) }) });

const models = {};
for (const [type, e] of Object.entries(MODELS)) {
  const file = fileURLToPath(e.url);
  if (!fs.existsSync(file)) { console.log(`SKIP ${type}: ${path.relative(HWD, file)} not present`); results.push({ model: type, name: 'present', ok: null, detail: 'file not present (skipped)' }); continue; }
  const buf = fs.readFileSync(file);
  const O = MODEL_LOAD_OPTS(type);
  // ---- 1. parse + convert
  let m, mp;
  try { m = convertGLB(buf, O); mp = convertGLB(buf, { ...O, groupBy: 'part' }); }
  catch (err) { check(type, 'parse', false, String(err)); continue; }
  models[type] = { m, mp, buf };
  let badIdx = 0, badN = 0, nv = 0;
  for (const g of m.groups) for (const d of [g.opaque, g.glass]) { if (!d) continue; const n = d.pos.length / 3; nv += n;
    for (const i of d.idx) if (i >= n) badIdx++;
    for (let i = 0; i < d.nrm.length; i += 3) { const l = Math.hypot(d.nrm[i], d.nrm[i + 1], d.nrm[i + 2]); if (!(Math.abs(l - 1) < 1e-3)) badN++; } }
  check(type, 'parse', badIdx === 0 && badN === 0 && m.stats.tris > 0, { tris: m.stats.tris, verts: nv, parts: m.stats.parts, groups: m.stats.groups, excluded: m.stats.excluded, badIndices: badIdx, nonUnitNormals: badN, textured: m.stats.textured });
  // ---- 2. dimensions vs FAA ACD
  const a = ACD[type]; const bb = m.bbox;
  const L = bb[3] - bb[0], S = bb[5] - bb[2], Hh = bb[4];
  if (a) {
    const span = a.wingspan_m ?? a.wingspan_winglets_m;
    for (const [k, mv, ref, what] of [['length', L, a.length_m, 'Length_ft'], ['span', S, span, a.wingspan_m != null ? 'Wingspan_ft_without_winglets' : 'Wingspan_ft_with_winglets'], ['height', Hh, a.tail_height_m, 'Tail_Height_at_OEW_ft']]) {
      const d = (mv - ref) / ref; check(type, 'ACD ' + k, Math.abs(d) <= 0.02, { model_m: r3(mv), acd_m: ref, acd_field: what, acd_row: a.acd_row, diff_pct: Math.round(d * 1e4) / 100 });
    }
  } else check(type, 'ACD dims', false, 'no ACD record in data/ga_types.json');
  // ---- 3. origin on the wheel contact (+ the source's static tyre deflection)
  const C = m.contacts, DF = DEFLECTION[type] || { main: 0, nose: 0 };
  if (!C) check(type, 'origin', false, 'no wheel contacts found');
  else {
    check(type, 'origin on main-gear contact', Math.abs(C.mainL[1] + DF.main) < 1e-3 && Math.abs(C.mainR[1] + DF.main) < 1e-3 && Math.abs(C.mainL[0]) < 0.01 && Math.abs(C.mainR[0]) < 0.01 && Math.abs(C.mainL[2] + C.mainR[2]) < 0.01,
      { mainL: C.mainL.map(r3), mainR: C.mainR.map(r3), origin_gl: m.originGl.map(r3), track_m: r3(m.track), ground: O.groundGl != null ? `source ground plane (glTF Y ${O.groundGl})` : 'lowest tyre point', static_deflection_m: DF.main, deflection_src: DF.src });
    if (C.nose) check(type, 'nose wheel touches the ground', Math.abs(C.nose[1] + DF.nose) < 0.002, { nose: C.nose.map(r3), expected_y: -DF.nose, wheelbase_m: r3(m.wheelbase) });
    let minTyre = Infinity, minOther = Infinity, otherPart = null;
    for (const g of mp.groups) { const d = g.opaque; if (!d) continue; for (let i = 0; i < d.pos.length; i += 3) { const y = d.pos[i + 1]; const tyre = m.materials[d.mat[i / 3]].cls === 'tyre';
      if (tyre) minTyre = Math.min(minTyre, y); else if (y < minOther) { minOther = y; otherPart = g.key; } } }
    check(type, 'nothing below the ground (rest; tyres within their static deflection)', minOther > -0.001 && minTyre > -(Math.max(DF.main, DF.nose) + 0.001),
      { lowest_non_tyre_y_m: r3(minOther), part: otherPart, lowest_tyre_y_m: r3(minTyre), allowed_tyre_y_m: -Math.max(DF.main, DF.nose) });
    const PC = PROP_CLEARANCE[type];
    const spin = m.parts.findIndex(p => p.pivot && p.pivot.kind === 'spin');
    if (PC && spin >= 0) {   // lowest point any blade tip reaches while turning: axis height - tip radius (axis ~ horizontal)
      const o = m.parts[spin].pivot.origin, ax = m.parts[spin].pivot.axis; let R = 0;
      for (const g of mp.groups) { const p = g.part >= 0 ? m.parts[g.part] : null; if (!p || !p.pivot || p.pivot.kind !== 'pitch' || !g.opaque) continue; const P = g.opaque.pos;
        for (let i = 0; i < P.length; i += 3) { const d = [P[i] - o[0], P[i + 1] - o[1], P[i + 2] - o[2]]; const t = d[0] * ax[0] + d[1] * ax[1] + d[2] * ax[2]; R = Math.max(R, Math.hypot(d[0] - ax[0] * t, d[1] - ax[1] * t, d[2] - ax[2] * t)); } }
      const clr = o[1] - R;
      check(type, 'propeller ground clearance (gear down, static)', Math.abs(clr - PC.m) <= PC.tol, { clearance_m: r3(clr), axis_y_m: r3(o[1]), tip_radius_m: r3(R), sourced_m: PC.m, src: PC.src });
    }
  }
  // ---- 4. pivots
  const kin = new Kinematics(m); const kinds = {};
  for (const i of kin.movers) { const k = m.parts[i].pivot.kind; kinds[k] = (kinds[k] || 0) + 1; }
  const req = REQUIRED[type] || {}; const missing = Object.entries(req).filter(([k, n]) => (kinds[k] || 0) < n).map(([k, n]) => `${k} ${kinds[k] || 0}/${n}`);
  if (type === 'SF50') { if (!((kinds.aileron || 0) >= 2)) missing.push('roll surfaces (aileron) < 2'); if (!((kinds.elevator || 0) + (kinds.ruddervator || 0) >= 1)) missing.push('pitch surfaces (elevator / ruddervator) none'); }
  check(type, 'pivots present', missing.length === 0 && kin.unsupported.length === 0, { kinds, missing, unsupported: kin.unsupported });
  const mism = m.parts.filter(p => p.pivot && p.pivot.originMismatch > 1e-4).map(p => `${p.id} ${r3(p.pivot.originMismatch)} m`);
  check(type, 'pivot origin = node origin', mism.length === 0, mism.length ? mism : 'all pivots at their node origins (< 0.1 mm)');
  // ---- 5. kinematics
  let worst = 0; const symm = [], pairs = new Set();
  for (const g of [1, 0.5, 0]) {
    const P = kin.pose({ gear: g, flaps: 40, roll: 0, pitch: 0.5, yaw: 0 });
    for (const b of kin.braces) { const K = xform(P[b.up], b.K0), B = xform(P[b.lo], b.B0); worst = Math.max(worst, Math.hypot(K[0] - b.K[0], K[1] - b.K[1], K[2] - b.K[2]), Math.hypot(B[0] - b.B[0], B[1] - b.B[1], B[2] - b.B[2]));
      const Bg = xform(P[b.gear], b.B0); worst = Math.max(worst, Math.hypot(Bg[0] - B[0], Bg[1] - B[1], Bg[2] - B[2])); }
    for (const l of Object.keys(kin.defl)) { if (!/L$/.test(l)) continue; const r = l.replace(/L$/, 'R'); if (!(r in kin.defl)) continue; if (g === 1) pairs.add(l + '/' + r);
      if (Math.abs(Math.abs(kin.defl[l]) - Math.abs(kin.defl[r])) > 1e-6) symm.push(`${l}/${r} at gear ${g}: ${kin.defl[l]} vs ${kin.defl[r]}`); }
  }
  if (kin.braces.length) check(type, 'brace closure', worst < 1e-4, { braces: kin.braces.length, worst_m: worst });
  check(type, 'left / right symmetry (flaps 40, pitch 0.5, gear 1 / 0.5 / 0)', symm.length === 0 && pairs.size > 0, symm.length ? symm : { pairs: [...pairs] });
  // control-surface travel: sign measured per part (+10 deg about its own pivot -> trailing-edge vertex motion)
  const teSign = (pi) => {
    const g = mp.groups.find(q => q.part === pi); if (!g || !g.opaque) return 0; const P = g.opaque.pos; let k = 0;
    for (let i = 3; i < P.length; i += 3) if (P[i] < P[k]) k = i;   // trailing edge = the aft-most vertex (local +x forward)
    const pv = m.parts[pi].pivot, p0 = [P[k], P[k + 1], P[k + 2]], p1 = xform(rotAbout(pv.origin, pv.axis, 10 * Math.PI / 180), p0);
    return p1[1] < p0[1] ? 1 : -1;   // +1: positive = trailing edge down (toward the surface's lower side)
  };
  for (const T of TRAVEL[type] || []) for (const id of T.parts) {
    const pi = m.partIndex.get(id); if (pi == null || !m.parts[pi].pivot) { check(type, `travel ${id}`, false, 'part / pivot missing'); continue; }
    const pv = m.parts[pi].pivot, rng = pv[T.field || 'range'] || pv.range; const s = T.lateral ? 1 : teSign(pi);
    const up = s > 0 ? -rng[0] : rng[1], down = s > 0 ? rng[1] : -rng[0];
    check(type, `travel ${id} vs type certificate`, Math.abs(up - T.up) < 0.05 && Math.abs(down - T.down) < 0.05,
      { range: rng, field: T.field || 'range', positive_is: T.lateral ? 'either side (symmetric)' : s > 0 ? 'TE down' : 'TE up', te_up_deg: up, te_down_deg: down, certificate: { up: T.up, down: T.down }, src: T.src });
  }
  if (type === 'SF50') {   // functional: full pull / push / yaw / roll through the kinematics, in the measured sign
    const D = (st, id) => { kin.pose(st); const pi = m.partIndex.get(id); return kin.defl[id] * teSign(pi); };   // + = TE down
    const pull = D({ pitch: 1 }, 'ruddervator_R'), push = D({ pitch: -1 }, 'ruddervator_R'), yawR = D({ yaw: 1 }, 'ruddervator_R'), yawL = D({ yaw: 1 }, 'ruddervator_L');
    const rollR = D({ roll: 1 }, 'aileron_R'), rollL = D({ roll: 1 }, 'aileron_L'); const tabPull = D({ pitch: 1 }, 'rv_tab_R'), tabPush = D({ pitch: -1 }, 'rv_tab_R');
    check(type, 'controls: pull / push / yaw / roll reach the certificate travels; geared tab not clamped',
      Math.abs(pull + 20) < 0.01 && Math.abs(push - 15) < 0.01 && Math.abs(Math.abs(yawR) - 9) < 0.01 && Math.abs(yawR + yawL) < 0.01 && Math.abs(rollR + 15) < 0.01 && Math.abs(rollL - 11.5) < 0.01 && Math.abs(tabPull - 8) < 0.01 && Math.abs(tabPush + 6) < 0.01,
      { pull_rv_deg: r3(pull), push_rv_deg: r3(push), yaw_right_rv_R_L_deg: [r3(yawR), r3(yawL)], roll_right_ail_R_L_deg: [r3(rollR), r3(rollL)], rv_tab_full_pull_push_deg: [r3(tabPull), r3(tabPush)],
        expected: 'pull -20 (TE up), push +15, yaw +-9 opposite, roll right: right aileron -15 / left +11.5, servo tab -0.4 x surface = +8 / -6 (inside [-7, 18])', sign: '+ = TE down' });
  }
  // lowest point over the gear sweep (gear 1 -> 0): retraction must start at least this high above the ground
  let sweepLow = { y: Infinity };
  for (let gi = 0; gi <= 40; gi++) { const g = 1 - gi / 40, P = kin.pose({ gear: g });
    for (const grp of mp.groups) { const d = grp.opaque; if (!d) continue; const p = grp.part >= 0 ? m.parts[grp.part] : null; if (!p) continue;
      let gearish = false; for (let q = grp.mover; q >= 0; q = kin.up[q]) { const k = m.parts[q].pivot && m.parts[q].pivot.kind; if (k === 'gear' || k === 'brace' || k === 'gear_door') gearish = true; }
      if (!gearish) continue; const Mx = grp.mover >= 0 ? P[grp.mover] : null;
      for (let i = 0; i < d.pos.length; i += 3) { const v = Mx ? xform(Mx, [d.pos[i], d.pos[i + 1], d.pos[i + 2]]) : [d.pos[i], d.pos[i + 1], d.pos[i + 2]]; if (v[1] < sweepLow.y) sweepLow = { y: v[1], gear: g, part: grp.key }; } } }
  const sweepRest = Math.min(...[C.mainL[1], C.mainR[1], C.nose ? C.nose[1] : 0]);
  const dip = Math.max(0, sweepRest - sweepLow.y);
  check(type, 'gear sweep: deepest point below the gear-down contact <= 0.05 m (retract only above that AGL)', dip <= 0.05,
    { lowest_y_m: r3(sweepLow.y), at_gear: sweepLow.gear, part: sweepLow.part, dip_below_rest_contact_m: r3(dip), note: 'Phase 3b: start retraction only above this height (plus the static deflection) AGL' });
  // ---- 6. gear retracted vs the airframe's lower skin
  const P0 = kin.pose({ gear: 0 });
  const gearMover = (mv) => { for (let q = mv; q >= 0; q = kin.up[q]) { const k = m.parts[q].pivot && m.parts[q].pivot.kind; if (k === 'gear' || k === 'brace') return true; } return false; };
  const isSkin = (p) => /^(Fuselage|Wing)$/.test(p.group || '') || (p.pivot && p.pivot.kind === 'gear_door');
  const skin = [], gearV = [];
  for (const g of mp.groups) {
    const p = g.part >= 0 ? m.parts[g.part] : null; if (!p || !g.opaque) continue; const Mx = g.mover >= 0 ? P0[g.mover] : null; const d = g.opaque;
    if (gearMover(g.mover)) {
      for (let i = 0; i < d.pos.length; i += 3) { const v = Mx ? xform(Mx, [d.pos[i], d.pos[i + 1], d.pos[i + 2]]) : [d.pos[i], d.pos[i + 1], d.pos[i + 2]]; gearV.push({ v, part: p.id, mat: m.materials[d.mat[i / 3]].name, tyre: m.materials[d.mat[i / 3]].cls === 'tyre' }); } }
    else if (isSkin(p)) for (let i = 0; i < d.pos.length; i += 3) { const n = Mx ? xform(Mx, [d.nrm[i], d.nrm[i + 1], d.nrm[i + 2]]).map((x, k) => x - Mx[12 + k]) : [d.nrm[i], d.nrm[i + 1], d.nrm[i + 2]];
      if (n[1] < -0.3) skin.push(Mx ? xform(Mx, [d.pos[i], d.pos[i + 1], d.pos[i + 2]]) : [d.pos[i], d.pos[i + 1], d.pos[i + 2]]); }
  }
  const H = new Map(), key = (z) => Math.floor(z / 0.05);
  for (const s of skin) { const k = key(s[2]); if (!H.has(k)) H.set(k, []); H.get(k).push(s); }
  const envelope = (x, z) => { let y = Infinity; for (const k of [key(z) - 1, key(z), key(z) + 1]) for (const s of H.get(k) || []) if (Math.abs(s[2] - z) <= 0.05 && Math.abs(s[0] - x) <= 0.6 && s[1] < y) y = s[1]; return isFinite(y) ? y : null; };
  const worstBy = {}; let uncovered = 0;
  for (const g of gearV) { const y0 = envelope(g.v[0], g.v[2]); if (y0 == null) { uncovered++; continue; } const pro = y0 - g.v[1]; const k = (g.tyre ? 'tyre' : 'other') + ':' + g.part;
    if (!worstBy[k] || pro > worstBy[k].pro) worstBy[k] = { pro, at: g.v.map(r3), mat: g.mat }; }
  const tyreMax = Math.max(0, ...Object.entries(worstBy).filter(([k]) => k.startsWith('tyre')).map(([, v]) => v.pro));
  const otherMax = Math.max(0, ...Object.entries(worstBy).filter(([k]) => k.startsWith('other')).map(([, v]) => v.pro));
  const doc = TYRE_PROTRUSION[type];
  const tyreOK = doc ? tyreMax <= doc.max_m + 0.010 : tyreMax <= 0.010;
  check(type, 'gear retracted: only tyres protrude (documented amount)', tyreOK && otherMax <= 0.010,
    { tyre_max_protrusion_mm: Math.round(tyreMax * 1000), other_max_protrusion_mm: Math.round(otherMax * 1000), documented: doc || 'none (flush)', gear_vertices: gearV.length, without_skin_nearby: uncovered,
      per_part: Object.fromEntries(Object.entries(worstBy).map(([k, v]) => [k, { mm: Math.round(v.pro * 1000), material: v.mat, at: v.at }])) });
  let low = { y: Infinity };
  for (const g of mp.groups) { const d = g.opaque; if (!d) continue; const Mx = g.mover >= 0 ? P0[g.mover] : null; for (let i = 0; i < d.pos.length; i += 3) { const v = Mx ? xform(Mx, [d.pos[i], d.pos[i + 1], d.pos[i + 2]]) : [d.pos[i], d.pos[i + 1], d.pos[i + 2]]; if (v[1] < low.y) low = { y: v[1], part: g.key, at: v.map(r3) }; } }
  info(type, 'gear retracted: lowest point (report)', { lowest_y_m: r3(low.y), part: low.part, at: low.at });
  // ---- 7. light anchors: nothing the GLB names is dropped; the documented anti-collision count is drawn
  const { json } = parseGLB(buf);
  const named = new Set(); for (const n of json.nodes || []) { const e = n.extras && n.extras.light; if (e) named.add(typeof e === 'string' ? e : e.kind); }
  for (const p of m.parts) { const A = p.extras && (p.extras.light_anchors || (p.extras.info && p.extras.info.light_anchors)); if (A) for (const k of Object.keys(A)) named.add(k); }
  const dropped = [...named].filter(k => !m.lights[k]);
  check(type, 'light anchors: every light the model names is kept', dropped.length === 0, { named: [...named].sort(), dropped, kinds_drawn: KINDS.filter(k => m.lights[k]), kept_not_drawn: Object.keys(m.lights).filter(k => m.lights[k] && !KINDS.includes(k)) });
  const AC = ANTICOLLISION[type]; const acl = ['beaconTop', 'beaconBot', 'strobeL', 'strobeR', 'strobeTail'].filter(k => m.lights[k]);
  if (AC) check(type, 'anti-collision lights drawn = documented count', acl.length === AC.n, { drawn: acl, documented: AC.n, src: AC.src });
  if (type === 'PC12') {   // wing landing lights (Pilatus MBP p.4 photo), separate from the nose-strut lamp (taxi)
    const L1 = m.lights.landL, R1 = m.lights.landR, Tx = m.lights.taxi;
    check(type, 'landing lights on the wings, apart from the nose-strut taxi lamp', !!(L1 && R1 && Tx) && L1.part === -1 && R1.part === -1 && Math.abs(L1.p[2] - R1.p[2]) > 2 && Math.hypot(L1.p[0] - Tx.p[0], L1.p[2] - Tx.p[2]) > 1,
      { landL: L1 && { p: L1.p.map(r3), part: L1.part }, landR: R1 && { p: R1.p.map(r3), part: R1.part }, taxi: Tx && { p: Tx.p.map(r3), part: Tx.part >= 0 ? m.parts[Tx.part].id : null }, src: L1 && L1.src });
  }
  // ---- 8. registration panels: every builder field kept
  const regSrc = m.parts.filter(p => p.extras && p.extras.info && p.extras.info.reg_panel);
  if (regSrc.length) {
    const miss = [];
    for (const p of regSrc) { const r = p.extras.info.reg_panel, q = m.regPanels.find(x => x.part === p.id); if (!q) { miss.push(p.id + ': panel'); continue; }
      for (const [k, v] of Object.entries(r)) { const kk = k === 'text_dir' ? 'textDir' : k; if (k === 'axes') continue; if (q[kk] == null && v != null) miss.push(`${p.id}.${k}`); } }
    check(type, 'registration panels keep every builder field (blank; D1)', miss.length === 0, { panels: m.regPanels.map(q => ({ part: q.part, textDir: q.textDir && q.textDir.map(r3), length: q.length, height: q.height })), missing: miss });
  }
  // ---- 9. traffic frame: registry constants = the measured model; withModelFrame hands traffic the model's layout
  const F = MODELS[type].frame, meas = { L, span: S, H: Hh, xMain: bb[3], xNose: bb[3] - m.wheelbase, track: m.track, wheelbase: m.wheelbase };
  const fd = Object.fromEntries(Object.keys(meas).map(k => [k, r3(F[k] - meas[k])]));
  check(type, 'registry frame = measured model (5 mm)', Object.values(fd).every(v => Math.abs(v) <= 0.005), { registry: Object.fromEntries(Object.keys(meas).map(k => [k, F[k]])), measured: Object.fromEntries(Object.entries(meas).map(([k, v]) => [k, r3(v)])), diff_m: fd });
  const T0 = gaDims(type), T1 = withModelFrame(T0);
  const raw = { xMain: r3(T0.xMain - meas.xMain), xNose_wheel_from_nose: r3(T0.xNose - meas.xNose), track: r3(T0.track - meas.track), wheelbase: r3((T0.xMain - T0.xNose) - meas.wheelbase), L: r3(T0.L - meas.L) };
  info(type, 'gaDims class rule vs the model (what traffic used before withModelFrame)', { delta_m: raw, basis: T0.basis });
  const ok9 = Math.abs(T1.xMain - meas.xMain) < 0.006 && Math.abs(T1.xNose - meas.xNose) < 0.006 && Math.abs(T1.track - meas.track) < 0.006 && Math.abs(T1.L - meas.L) < 0.006 && T1.ant === T0.ant && T1.dimsBase === T0 && Object.isFrozen(T1);
  check(type, 'withModelFrame(gaDims) = the model frame (ground.js nose / tail / gear contacts, traffic.js antenna offset)', ok9,
    { xMain: T1.xMain, xNose: T1.xNose, track: T1.track, L: T1.L, ant_from_nose: T1.ant, antenna_to_main_m: r3(T1.xMain - T1.ant), before: { xMain: T0.xMain, xNose: T0.xNose, track: T0.track, antenna_to_main_m: r3(T0.xMain - T0.ant) } });
}

// ---- 10. type-specific shape checks
{
  const M = models.SF50;
  if (M) {
    const { m, mp } = M; const span2 = MODELS.SF50.frame.span / 2;
    // wing outline in the front view (fix round 2): upper / lower outline of wing_R per butt line vs AFM Fig 1-1; the
    // mid-line (root height) within 0.03 m, the slope within 0.5 deg (fix round 1's wing sat 0.10 m low: Z_LE0 inferred)
    const A = AFM_SF50; const wR = mp.groups.find(q => q.key === 'wing_R').opaque.pos; const bins = new Map();
    for (let i = 0; i < wR.length; i += 3) { const k = Math.round(wR[i + 2] / 0.01); const b = bins.get(k) || { n: 0, hi: -Infinity, lo: Infinity, bl: 0 }; b.n++; b.bl += wR[i + 2]; b.hi = Math.max(b.hi, wR[i + 1]); b.lo = Math.min(b.lo, wR[i + 1]); bins.set(k, b); }
    const rowsS = [...bins.values()].filter(b => b.n >= 30).map(b => ({ bl: b.bl / b.n, hi: b.hi, lo: b.lo })).sort((a, b) => a.bl - b.bl);
    const atS = (bl, k) => { for (let i = 1; i < rowsS.length; i++) if (rowsS[i].bl >= bl) { const a = rowsS[i - 1], b = rowsS[i], t = (bl - a.bl) / (b.bl - a.bl); return a[k] + t * (b[k] - a[k]); } return null; };
    const upS = A.bl.map(b => atS(b, 'hi')), loS = A.bl.map(b => atS(b, 'lo'));
    const midOff = A.bl.map((b, i) => A.lo[i] == null ? null : (A.up[i] + A.lo[i]) / 2 - (upS[i] + loS[i]) / 2).filter(v => v != null);
    const mo = midOff.reduce((a, b) => a + b, 0) / midOff.length;
    const lsq = (X, Y) => { const n = X.length, sx = X.reduce((a, b) => a + b, 0), sy = Y.reduce((a, b) => a + b, 0), sxx = X.reduce((a, b) => a + b * b, 0), sxy = X.reduce((a, b, i) => a + b * Y[i], 0); const k1 = (n * sxy - sx * sy) / (n * sxx - sx * sx); return [(sy - k1 * sx) / n, k1]; };
    const slM = Math.atan(lsq(A.bl, upS)[1]) * 180 / Math.PI, slA = Math.atan(lsq(A.bl, A.up)[1]) * 180 / Math.PI;
    let fusW = { hw: 0, y: 0 }; for (const q of mp.groups) { if (q.key !== 'fuselage' || !q.opaque) continue; const d = q.opaque.pos; for (let i = 0; i < d.length; i += 3) if (Math.abs(d[i] - (m.originGl[2] - 4.4)) < 0.03 && Math.abs(d[i + 2]) > fusW.hw) fusW = { hw: Math.abs(d[i + 2]), y: d[i + 1] }; }
    const relTop = fusW.y - atS(1.6, 'hi');
    check('SF50', 'wing front-view outline vs AFM Fig 1-1: mid-line (root height) within 0.03 m, upper-line slope within 0.5 deg, top at BL 1.6 vs the fuselage max-width line within 0.04 m', Math.abs(mo) <= 0.03 && Math.abs(slM - slA) <= 0.5 && Math.abs(relTop - A.top_below_maxwidth_bl1_6) <= 0.04,
      { bl: A.bl, model_upper: upS.map(r3), model_lower: loS.map(r3), afm_upper: A.up, afm_lower: A.lo, midline_offset_m: r3(mo), upper_slope_deg: { model: Math.round(slM * 100) / 100, afm: Math.round(slA * 100) / 100 },
        fuselage_max_width_wl_m: r3(fusW.y), wing_top_bl1_6_below_max_width_m: { model: r3(relTop), afm: A.top_below_maxwidth_bl1_6 }, src: A.src });
    // upswept tip: the highest point outboard of the tip rib (|z| > 5.5) above the EXTRAPOLATED upper-surface line (least
    // squares over BL 3.5-5.4), the way the AFM Fig 1-1 front view is read (fix round 2: fix round 1 measured the rise
    // above the rib and cited Fig 1-1 for a >= 0.12 m limit; the figure shows ~0.06 m); and a pointed top (its chord)
    const [u0, u1] = lsq(rowsS.filter(r => r.bl >= 3.5 && r.bl <= 5.4).map(r => r.bl), rowsS.filter(r => r.bl >= 3.5 && r.bl <= 5.4).map(r => r.hi));
    for (const side of ['R', 'L']) {
      const g = mp.groups.find(q => q.key === 'wing_' + side), P = g.opaque.pos, sg = side === 'R' ? 1 : -1; let zmax = -1, top = { y: -1, bl: 0 };
      for (let i = 0; i < P.length; i += 3) { const z = P[i + 2] * sg; if (z > zmax) zmax = z; if (z > 5.5 && P[i + 1] > top.y) top = { y: P[i + 1], bl: z }; }
      const topX = []; for (let i = 0; i < P.length; i += 3) if (P[i + 2] * sg > 5.5 && top.y - P[i + 1] < 0.01) topX.push(P[i]);
      const topChord = Math.max(...topX) - Math.min(...topX);
      // lamps flush: the clear lens is an open patch whose boundary lies on the rim of the skin opening (within 2 mm of a
      // paint vertex: the old lamps were closed boxes standing on the cap, no boundary at all), and every lamp body
      // (light_*) sits behind the lens (a lens vertex within 30 mm)
      const paint = [], lensV = [], lampV = []; let lensTri = 0; const edges = new Map();
      for (const d of [g.opaque, g.glass]) { if (!d) continue; const nm = (i) => m.materials[d.mat[i]].name; const at = (i) => [d.pos[i * 3], d.pos[i * 3 + 1], d.pos[i * 3 + 2]];
        for (let i = 0; i < d.pos.length / 3; i++) { if (d.pos[i * 3 + 2] * sg < 5.3) continue; const n = nm(i); if (/^paint_/.test(n)) paint.push(at(i)); else if (/^light_/.test(n)) lampV.push(at(i)); else if (n === 'lens') lensV.push(at(i)); }
        if (d === g.glass) for (let t = 0; t < d.idx.length; t += 3) { const tri = [d.idx[t], d.idx[t + 1], d.idx[t + 2]]; if (!tri.every(i => nm(i) === 'lens' && d.pos[i * 3 + 2] * sg >= 5.3)) continue; lensTri++;
          for (let e = 0; e < 3; e++) { const a = tri[e], b = tri[(e + 1) % 3]; const k = a < b ? a + ',' + b : b + ',' + a; edges.set(k, (edges.get(k) || 0) + 1); } } }
      const hash = (pts, c) => { const H2 = new Map(); for (const p of pts) { const k = p.map(v => Math.floor(v / c)).join(','); if (!H2.has(k)) H2.set(k, []); H2.get(k).push(p); } return H2; };
      const near = (H2, c, p) => { let best = Infinity; const q = p.map(v => Math.floor(v / c)); for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let e = -1; e <= 1; e++) for (const r of H2.get([q[0] + a, q[1] + b, q[2] + e].join(',')) || []) best = Math.min(best, Math.hypot(p[0] - r[0], p[1] - r[1], p[2] - r[2])); return best; };
      const HP = hash(paint, 0.01), HL = hash(lensV, 0.03); const gl = g.glass; let bnd = 0, worstRim = 0;
      for (const [k, n] of edges) if (n === 1) { for (const i of k.split(',').map(Number)) { bnd++; worstRim = Math.max(worstRim, near(HP, 0.01, [gl.pos[i * 3], gl.pos[i * 3 + 1], gl.pos[i * 3 + 2]])); } }
      let worstOff = 0; for (const p of lampV) worstOff = Math.max(worstOff, near(HL, 0.03, p));
      const flushOK = lensTri > 0 && bnd > 0 && worstRim <= 0.002 && lampV.length > 0 && worstOff <= 0.030;
      const rise = top.y - (u0 + u1 * top.bl);
      check('SF50', `wing tip ${side}: upswept, pointed tip at the 38.7 ft span, AFM front-view height, flush lenses`, Math.abs(zmax - span2) < 0.005 && rise >= A.tip_rise[0] && rise <= A.tip_rise[1] && topChord <= 0.08 && flushOK,
        { outermost_bl_m: r3(zmax), span2_m: span2, tip_top: { bl: r3(top.bl), wl: r3(top.y) }, rise_above_extrapolated_upper_line_m: r3(rise), top_chord_m: r3(topChord), lens_triangles: lensTri, lens_boundary_vertices: bnd, worst_lens_rim_to_skin_m: r3(worstRim), lamp_vertices: lampV.length, worst_lamp_to_lens_m: r3(worstOff),
          limits: `outermost = span / 2 +-5 mm [obs 38.7 ft]; rise above the extrapolated upper line ${A.tip_rise[0]}-${A.tip_rise[1]} m [obs: AFM Fig 1-1 front view 0.06 +-0.02 m]; top chord <= 0.08 m (a point, not the fix-round-1 0.265 m square plate) [inf: Cirrus photos]; lens = an open patch in the skin opening (rim within 2 mm), lamps behind it (within 30 mm)` });
    }
    // nacelle: D inlet with a raised lip (waist behind it) and fillets into the spine
    const g = mp.groups.find(q => q.key === 'nacelle'), P = g.opaque.pos;
    const og = m.originGl[2];   // local x = origin station - FS
    const atFS = (fs) => { let w = 0; for (let i = 0; i < P.length; i += 3) { const m2 = m.materials[g.opaque.mat[i / 3]].name; if (m2 !== 'paint_white' && m2 !== 'inlet_lip') continue; if (Math.abs(P[i] - (og - fs)) < 0.012 && P[i + 1] > 1.9) w = Math.max(w, Math.abs(P[i + 2])); } return w; };
    const lipW = atFS(5.92), waistW = atFS(6.03), cowlW = atFS(6.80);
    check('SF50', 'nacelle: raised D lip (waist behind it) and fillets into the fuselage spine', lipW - waistW >= 0.010 && cowlW >= 0.356 + 0.05,
      { half_width_m: { lip_FS5_92: r3(lipW), waist_FS6_03: r3(waistW), cowl_with_fillet_FS6_80: r3(cowlW) }, afm_plan_half_width_m: 0.356, note: 'cowl half-width at its centre line unchanged (AFM Fig 1-1 plan 0.71 m); the fillet foot is wider [inf]' });
  }
  const Q = models.PC12;
  if (Q) {
    const { m, mp } = Q; const og = m.originGl[2], STA = (x) => og - x;   // local x -> pc12 station (glTF Z = STA)
    const D = PILATUS_PC12;
    // cabin windows per side: glass clusters of glazing_cabin + door / exit parts with a window
    const g = mp.groups.find(q => q.key === 'glazing_cabin'); const P = g.glass ? g.glass.pos : g.opaque.pos; const cl = [];
    for (let i = 0; i < P.length; i += 3) { const p = [P[i], P[i + 1], P[i + 2]]; let c = cl.find(c => Math.abs((c.x0 + c.x1) / 2 - p[0]) < 0.25 && Math.sign(c.z) === Math.sign(p[2]));
      if (!c) { c = { x0: p[0], x1: p[0], y0: p[1], y1: p[1], z: p[2] }; cl.push(c); } c.x0 = Math.min(c.x0, p[0]); c.x1 = Math.max(c.x1, p[0]); c.y0 = Math.min(c.y0, p[1]); c.y1 = Math.max(c.y1, p[1]); }
    const box = (d) => { if (!d || !d.pos.length) return null; const b = [Infinity, Infinity, -Infinity, -Infinity, 0]; for (let i = 0; i < d.pos.length; i += 3) { b[0] = Math.min(b[0], d.pos[i]); b[1] = Math.min(b[1], d.pos[i + 1]); b[2] = Math.max(b[2], d.pos[i]); b[3] = Math.max(b[3], d.pos[i + 1]); b[4] += d.pos[i + 2]; } b[4] /= d.pos.length / 3; return b; };
    const part = (id) => mp.groups.find(q => q.key === id);
    const doorWin = (id) => { const q = part(id); return q && q.glass && q.glass.pos.length ? Math.sign(q.glass.pos[2]) : 0; };
    const port = cl.filter(c => c.z < 0).length, stbd = cl.filter(c => c.z > 0).length;
    const dAir = doorWin('door_airstair'), dCargo = doorWin('door_cargo'), dExit = doorWin('exit_hatch');
    const portTot = port + (dAir < 0) + (dCargo < 0) + (dExit < 0), stbdTot = stbd + (dAir > 0) + (dCargo > 0) + (dExit > 0);
    const excess = Math.abs(portTot - 4) + Math.abs(stbdTot - 5);
    check('PC12', 'cabin windows per side vs the Pilatus NGX drawings', portTot === 4 && stbdTot === 5 && !dAir,
      { port_fixed: port, starboard_fixed: stbd, airstair_door_window: !!dAir, cargo_door_window: !!dCargo, exit_window: !!dExit, port_total: portTot, starboard_total: stbdTot, pilatus: 'port 3 + cargo-door window, no airstair-door window (4); starboard 5 incl. the exit (MBP p.2, p.5, p.9)', window_count_excess: excess });
    // stations (fix round 2: the count alone passed a layout with the cargo door 0.7 m aft): every window / door centre
    // vs the station measured on the Pilatus documents (+-0.03 m), heights relative to the model's own cabin crown
    let crown = -Infinity; for (const q of mp.groups) { const p = q.part >= 0 ? m.parts[q.part] : null; if (!p || p.group !== 'Fuselage' || !q.opaque) continue; const d = q.opaque.pos;
      for (let i = 0; i < d.length; i += 3) if (Math.abs(d[i + 2]) < 0.03 && Math.abs(STA(d[i]) - 6.0) < 0.06) crown = Math.max(crown, d[i + 1]); }
    const meas = { port_windows: cl.filter(c => c.z < 0).map(c => STA((c.x0 + c.x1) / 2)).sort((a, b) => a - b), stbd_windows: cl.filter(c => c.z > 0).map(c => STA((c.x0 + c.x1) / 2)).sort((a, b) => a - b) };
    const bAir = box(part('door_airstair') && part('door_airstair').opaque), bCargo = box(part('door_cargo') && part('door_cargo').opaque), bExit = box(part('exit_hatch') && part('exit_hatch').opaque);
    const bCw = box(part('door_cargo') && part('door_cargo').glass), bEw = box(part('exit_hatch') && part('exit_hatch').glass);
    meas.airstair = bAir && STA((bAir[0] + bAir[2]) / 2); meas.cargo = bCargo && STA((bCargo[0] + bCargo[2]) / 2); meas.exit = bExit && STA((bExit[0] + bExit[2]) / 2);
    meas.cargo_window = bCw && STA((bCw[0] + bCw[2]) / 2); meas.exit_window = bEw && STA((bEw[0] + bEw[2]) / 2);
    const winBelowCrown = cl.map(c => crown - (c.y0 + c.y1) / 2), winH = cl.map(c => c.y1 - c.y0), winW = cl.map(c => c.x1 - c.x0);
    const dev = []; const cmp = (k, a, b, tol = 0.03) => { if (a == null || b == null || Math.abs(a - b) > tol) dev.push(`${k}: model ${a == null ? '-' : r3(a)} vs ${b}`); };
    cmp('airstair door', meas.airstair, D.port.airstair); cmp('cargo door', meas.cargo, D.port.cargo); cmp('cargo-door window', meas.cargo_window, D.port.cargo_window); cmp('exit', meas.exit, D.stbd.exit); cmp('exit window', meas.exit_window, D.stbd.exit_window);
    if (meas.port_windows.length !== D.port.windows.length) dev.push('port windows ' + meas.port_windows.length); else D.port.windows.forEach((w, i) => cmp('port window ' + (i + 1), meas.port_windows[i], w));
    if (meas.stbd_windows.length !== D.stbd.windows.length) dev.push('starboard windows ' + meas.stbd_windows.length); else D.stbd.windows.forEach((w, i) => cmp('starboard window ' + (i + 1), meas.stbd_windows[i], w));
    for (const v of winBelowCrown) cmp('window centre below the crown', v, D.window_below_crown);
    // the glass runs 10 mm under the seal all round (pc12 build_glazing: trim at the outline + 0.010)
    for (const v of winH) cmp('window outline height (glass - 0.02)', v - 0.02, D.window_h, 0.02); for (const v of winW) cmp('window outline width (glass - 0.02)', v - 0.02, D.window_w, 0.02);
    check('PC12', 'cabin window / door / exit stations vs Pilatus drawing 190.10.40.432 + MBP p.5 (+-0.03 m)', dev.length === 0,
      { deviations: dev, measured: Object.fromEntries(Object.entries(meas).map(([k, v]) => [k, Array.isArray(v) ? v.map(r3) : v == null ? null : r3(v)])), crown_wl_m: r3(crown), window_centre_below_crown_m: [...new Set(winBelowCrown.map(r3))], window_glass_wh_m: [r3(Math.max(...winW)), r3(Math.max(...winH))], wing_rows: undefined, reference: D.src_layout });
    // wing silhouettes in the front view (fix round 2: re-digitised): upper and lower outline of wing_R per butt line vs the
    // drawing; the SHAPE (each minus its mean offset) must match within 15 mm rms, the top-line slope within 0.3 deg
    // the skin's spanwise rows are sparse: every full section row (>= 30 vertices in a 1-cm butt-line bin) gives its highest
    // and lowest vertex; the outline at a butt line is interpolated between the neighbouring rows
    const w = mp.groups.find(q => q.key === 'wing_R').opaque.pos; const bins = new Map();
    for (let i = 0; i < w.length; i += 3) { const k = Math.round(w[i + 2] / 0.01); const b = bins.get(k) || { n: 0, hi: -Infinity, lo: Infinity, bl: 0 }; b.n++; b.bl += w[i + 2]; b.hi = Math.max(b.hi, w[i + 1]); b.lo = Math.min(b.lo, w[i + 1]); bins.set(k, b); }
    const rowsW = [...bins.values()].filter(b => b.n >= 30).map(b => ({ bl: b.bl / b.n, hi: b.hi, lo: b.lo })).sort((a, b) => a.bl - b.bl);
    const at = (bl, k) => { for (let i = 1; i < rowsW.length; i++) if (rowsW[i].bl >= bl) { const a = rowsW[i - 1], b = rowsW[i], t = (bl - a.bl) / (b.bl - a.bl); return a[k] + t * (b[k] - a[k]); } return null; };
    const up = D.wing.bl.map(bl => at(bl, 'hi')), lo = D.wing.bl.map(bl => at(bl, 'lo'));
    const fit = (X, Y) => { const n = X.length, sx = X.reduce((a, b) => a + b, 0), sy = Y.reduce((a, b) => a + b, 0), sxx = X.reduce((a, b) => a + b * b, 0), sxy = X.reduce((a, b, i) => a + b * Y[i], 0); return Math.atan((n * sxy - sx * sy) / (n * sxx - sx * sx)) * 180 / Math.PI; };
    const sel = D.wing.bl.map((b, i) => i).filter(i => D.wing.bl[i] >= 3 && D.wing.bl[i] <= 7);
    const slope = fit(sel.map(i => D.wing.bl[i]), sel.map(i => up[i])), slopeD = fit(sel.map(i => D.wing.bl[i]), sel.map(i => D.wing.up[i]));
    const dU = D.wing.up.map((v, i) => v - up[i]), dL = D.wing.lo.map((v, i) => v == null ? null : v - lo[i]);
    const mean = (A) => { const B = A.filter(v => v != null); return B.reduce((a, b) => a + b, 0) / B.length; }, oU = mean(dU), oL = mean(dL);
    const rms = Math.sqrt(mean([...dU.map(v => (v - oU) ** 2), ...dL.filter(v => v != null).map(v => (v - oL) ** 2)]));
    // winglet: top point above the wing upper outline at BL 7.5 (drawing: top BL 8.04 / WL 2.135, i.e. +0.262 m)
    let wl = { y: -Infinity, bl: 0 }; for (const q of mp.groups) { if (q.key !== 'winglet_R' || !q.opaque) continue; const d = q.opaque.pos; for (let i = 0; i < d.length; i += 3) if (d[i + 1] > wl.y) wl = { y: d[i + 1], bl: d[i + 2] }; }
    const wRise = wl.y - up[D.wing.bl.indexOf(7.5)];
    check('PC12', 'wing front-view silhouette (dihedral, winglet) vs Pilatus drawing 190.10.40.432: shape rms <= 15 mm, top line within 0.3 deg, winglet rise within 0.03 m', rms <= 0.015 && Math.abs(slope - slopeD) <= 0.3 && Math.abs(wRise - D.wing.winglet_rise) <= 0.03,
      { bl: D.wing.bl, model_upper: up.map(r3), model_lower: lo.map(r3), drawing_upper: D.wing.up, drawing_lower: D.wing.lo, shape_rms_mm: Math.round(rms * 1000), top_line_deg: Math.round(slope * 100) / 100, drawing_top_line_deg: Math.round(slopeD * 100) / 100, offset_upper_m: r3(oU), offset_lower_m: r3(oL), winglet_top: { bl: r3(wl.bl), wl: r3(wl.y), rise_above_upper_BL7_5_m: r3(wRise), drawing_rise_m: D.wing.winglet_rise }, src: D.src_wing });
    // what is left: the cabin section and the wing sit lower above the ground than on the drawing (the nose and the
    // propeller axis agree) - a pc12 fuselage-loft item, measured here so it cannot grow unnoticed
    const offs = { crown: D.crown - crown, wing_upper: oU, wing_lower: oL, winglet_top: D.wing.winglet_top_wl - wl.y }; const offMax = Math.max(...Object.values(offs).map(Math.abs));
    check('PC12', 'cabin crown / wing height above the ground vs Pilatus drawing 190.10.40.432', offMax <= 0.03,
      { drawing_crown_wl_m: D.crown, model_crown_wl_m: r3(crown), offsets_m: Object.fromEntries(Object.entries(offs).map(([k, v]) => [k, r3(v)])), offset_max_mm: Math.round(offMax * 1000), note: 'nose (STA <= 3.0) and propeller axis (drawing WL 1.653, model 1.655) agree; the cabin crown and keel are both ~0.14 m lower in pc12/model/fuselage.py' });
  }
}

// ---- 11. the drawable: alpha in every path, placeholder sync, shader uniforms, motion vectors, CPU release
{
  const live = fs.readFileSync(path.join(HWD, 'js/live/aircraft.js'), 'utf8');
  const setByLive = [...new Set([...live.matchAll(/\bv\.(\w+)\s*=(?!=)/g)].map(x => x[1]))];
  const notSynced = setByLive.filter(k => !SYNC_KEYS.includes(k));
  check('runtime', 'placeholder sync covers every field js/live/aircraft.js sets', notSynced.length === 0, { set_by_live: setByLive, sync_keys: SYNC_KEYS, not_synced: notSynced });
  // Phase 3b wiring (fix round 2): every gaDims(...) call in js/live must appear in the docs/phase3_models.md diff as a '-'
  // line with a matching '+ ... modelDims(<same arguments>)' line (fix round 1's diff named 1 of the 2 traffic.js sites)
  const doc3 = fs.readFileSync(path.join(HWD, 'docs/phase3_models.md'), 'utf8').split('\n');
  const sites = []; for (const f of fs.readdirSync(path.join(HWD, 'js/live')).filter(f => f.endsWith('.js'))) { const src = fs.readFileSync(path.join(HWD, 'js/live', f), 'utf8').split('\n');
    src.forEach((l, i) => { for (const mm of l.matchAll(/(?<![\w.])gaDims\(([^)]*)\)/g)) sites.push({ file: 'js/live/' + f, line: i + 1, args: mm[1] }); }); }
  const uncovered = sites.filter(c => !(doc3.some(l => /^-/.test(l) && l.includes(`gaDims(${c.args})`)) && doc3.some(l => /^\+/.test(l) && l.includes(`modelDims(${c.args})`))));
  check('runtime', 'Phase 3b diff covers every gaDims call in js/live (withModelFrame on every path)', sites.length > 0 && uncovered.length === 0, { sites: sites.map(c => `${c.file}:${c.line} gaDims(${c.args})`), uncovered: uncovered.map(c => `${c.file}:${c.line}`) });
  check('runtime', 'aircraft programs read uAlpha (screen-door in acobj, blend alpha in acglass)', /uniform float uAlpha/.test(ACOBJ_FS) && /discard/.test(ACOBJ_FS.split('void main')[1].slice(0, 200)) && /uniform float uAlpha/.test(GLASS_FS) && /uAlpha/.test(GLASS_FS.split('writeOut')[1] || ''), 'ACOBJ_FS: bayer4 discard; GLASS_FS: alpha x uAlpha');
  for (const type of Object.keys(models)) {
    const T = withModelFrame(gaDims(type));
    // placeholder path (model not resolved yet) and loaded path
    const pending = new DetailedAircraft(T, { model: new Promise(() => {}) }); pending.alpha = 0.3;
    const itP = pending.items([0, 0, 50]);
    const m2 = convertGLB(models[type].buf, MODEL_LOAD_OPTS(type)); m2.keepCpu = false;
    const ac = new DetailedAircraft(T, { model: m2 }); await ac.ready;
    ac.pos = [0, 0, 0]; ac.fwd = [0, 0, -1]; ac.alpha = 0.3; ac.rotor = 178; ac.step(1 / 30);
    const it1 = ac.items([20, 5, 0]);
    const alphaOK = itP.length > 0 && itP.every(i => i.alpha === 0.3) && it1.length > 0 && it1.every(i => i.alpha === 0.3);
    check(type, 'drawable: every item carries the screen-door alpha (placeholder and loaded)', alphaOK, { placeholder_items: itP.length, placeholder_alpha: [...new Set(itP.map(i => i.alpha))], items: it1.length, item_alpha: [...new Set(it1.map(i => i.alpha))] });
    // motion vectors (fix round 2): a point 0.25 m OFF the spin axis (the axis point does not move under any rotation, so
    // fix round 1's check passed whatever the rotation term was), rotor speeds inside PROP_BLUR (40, 59 rad/s) and above
    // (178): with the aircraft standing still, spinning groups must show no motion; moved 2 m, exactly the 2 m
    const spinIdx = ac.res.kin.movers.find(i => m2.parts[i].pivot.kind === 'spin');
    const pv = m2.parts[spinIdx].pivot, ax = pv.axis, t1 = Math.abs(ax[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
    let u = [ax[1] * t1[2] - ax[2] * t1[1], ax[2] * t1[0] - ax[0] * t1[2], ax[0] * t1[1] - ax[1] * t1[0]]; const lu = Math.hypot(...u); u = u.map(v => v / lu);
    const off = [pv.origin[0] + 0.25 * u[0], pv.origin[1] + 0.25 * u[1], pv.origin[2] + 0.25 * u[2]];
    const rideSpin = (i) => { const grp = ac.res.gpu.groups.find(g => g.opaque === i.mesh || g.glass === i.mesh); if (!grp) return i.prog === 'acglass' && i.mesh === ac.res.gpu.disc; for (let q = grp.mover; q >= 0; q = ac.res.kin.up[q]) if (q === spinIdx) return true; return false; };
    const mvRes = {}; let mvOK = spinIdx != null;
    for (const wr of [40, 59, 178]) {
      const a2 = new DetailedAircraft(T, { model: m2 }); await a2.ready; a2.pos = [0, 0, 0]; a2.fwd = [0, 0, -1]; a2.rotor = wr;
      a2.step(1 / 30); a2.items([20, 5, 0]); a2.commit(); a2.step(1 / 30);
      const still = a2.items([20, 5, 0]).filter(rideSpin).map(i => { const a = xform(i.model, off), b = xform(i.prevModel, off); return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); });
      a2.commit(); a2.pos = [2, 0, 0]; a2.step(1 / 30);
      const moved = a2.items([20, 5, 0]).filter(rideSpin).map(i => { const a = xform(i.model, off), b = xform(i.prevModel, off); return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); });
      mvRes[wr] = { spinning_items: still.length, still_max_m: r3(Math.max(0, ...still)), moved_m: [...new Set(moved.map(r3))] };
      if (!(still.length > 0 && Math.max(...still) < 0.002 && moved.length > 0 && moved.every(d => Math.abs(d - 2) < 0.02))) mvOK = false;
    }
    check(type, 'drawable: spinning groups keep the aircraft motion in prevModel, rotation left out (point 0.25 m off the axis; 40 / 59 / 178 rad/s)', mvOK,
      { blur_from_rad_s: PROP_BLUR, has_prop_disc: !!ac.res.prop, by_rotor_rad_s: mvRes, expected: 'still 0 m, moved 2 m' });
    // shadows fade with the aircraft (fix round 2): with the aircraft programs the acobj shadow program dithers by uAlpha;
    // without them (obj fallback) and in the placeholder path no shadow below alpha 0.5
    const fakeR = { progs: {}, curRange: [0, 1e9], addProgram(n, vs, fs, d = {}) { this.progs[n] = { main: new Program(vs, fs, d), shadow: new Program(vs, 'void main(){}', Object.assign({ SHADOW_PASS: 1 }, d)) }; } };
    const shOf = async (opts, a) => { const x = new DetailedAircraft(T, opts); await x.ready; x.pos = [0, 0, 0]; x.fwd = [0, 0, -1]; x.alpha = a; x.step(1 / 30); const it = x.items([20, 5, 0]); return { n: it.length, cast: it.filter(i => i.castShadow).length, progs: [...new Set(it.filter(i => i.castShadow).map(i => i.prog))] }; };
    const sAc3 = await shOf({ model: m2, R: fakeR }, 0.3), sObj3 = await shOf({ model: m2 }, 0.3), sObj7 = await shOf({ model: m2 }, 0.7), sAc0 = await shOf({ model: m2, R: fakeR }, 0);
    const pend = new DetailedAircraft(T, { model: new Promise(() => {}) }); pend.alpha = 0.3; const pIt = pend.items([0, 0, 50]);
    const shOK = fakeR.progs.acobj && fakeR.progs.acobj.fadeShadow === true && /uniform float uAlpha/.test(ACOBJ_SHADOW_FS) && /discard/.test(ACOBJ_SHADOW_FS)
      && sAc3.cast > 0 && sAc3.progs.every(p => p === 'acobj') && sAc0.cast === 0 && sObj3.cast === 0 && sObj7.cast > 0 && pIt.every(i => !i.castShadow);
    check(type, 'drawable: the shadow fades with the aircraft (dithered acobj shadow pass; obj fallback / placeholder cast only from alpha 0.5)', shOK,
      { acobj_alpha_0_3: sAc3, acobj_alpha_0: sAc0, obj_alpha_0_3: sObj3, obj_alpha_0_7: sObj7, placeholder_alpha_0_3_casting: pIt.filter(i => i.castShadow).length, acobj_shadow_program_fades: !!(fakeR.progs.acobj && fakeR.progs.acobj.fadeShadow) });
    const released = m2.groups.every(g => (!g.opaque || g.opaque.released) && (!g.glass || g.glass.released));
    check(type, 'drawable: CPU vertex arrays released after the GPU upload (keepCpu false)', released && it1.length > 0, { groups: m2.groups.length, released });
  }
}

// ---- 12. provenance: SOURCES.json hashes, docs/phase3 captions
{
  const dir = path.join(HWD, 'js/aircraft/models'); const S = JSON.parse(fs.readFileSync(path.join(dir, 'SOURCES.json'), 'utf8'));
  const bad = [];
  for (const f of fs.readdirSync(dir).filter(f => f !== 'SOURCES.json')) { const e = S[f]; const h = sha(path.join(dir, f));
    if (!e) { bad.push(`${f}: no entry`); continue; } if (e.sha256 !== h) bad.push(`${f}: sha256 ${String(e.sha256).slice(0, 12)} != file ${h.slice(0, 12)}`);
    if ('sha256_match' in e && e.sha256_match !== (e.sha256_recorded_by_builder === h)) bad.push(`${f}: sha256_match ${e.sha256_match} but the builder recorded ${String(e.sha256_recorded_by_builder).slice(0, 12)}`); }
  for (const [type, e] of Object.entries(MODELS)) { const meta = fileURLToPath(e.meta); if (!fs.existsSync(meta)) continue; const pv = JSON.parse(fs.readFileSync(meta, 'utf8'))._provenance || {};
    if (pv.glb_sha256 && pv.glb_sha256 !== sha(fileURLToPath(e.url))) bad.push(`${type}: meta _provenance.glb_sha256 != the GLB on disk`); }
  check('provenance', 'js/aircraft/models/SOURCES.json = the files on disk', bad.length === 0, bad.length ? bad : 'every model file hashed as recorded');
  // fix round 2: the builders are identified by the hashes of their sources (tools/models is not in git, so a commit hash
  // did not identify them): the recorded per-file hashes must equal the files on disk now, i.e. a rebuild from this tree
  // reproduces the GLB (SF50: build_sf50.py _provenance; PC-12: the variant builder + the pc12 sources it ran)
  const REPO = path.resolve(HWD, '..'), treeOf = (files) => { const h = crypto.createHash('sha256'); const now = {}; for (const f of Object.keys(files).sort()) { now[f] = fs.existsSync(path.join(REPO, f)) ? sha(path.join(REPO, f)) : null; h.update(`${f} ${now[f]}\n`); } return { tree: h.digest('hex'), changed: Object.keys(files).filter(f => files[f] !== now[f]) }; };
  const prov = {}, pbad = [];
  for (const [type, e] of Object.entries(MODELS)) { const meta = fileURLToPath(e.meta); if (!fs.existsSync(meta)) continue; const M = JSON.parse(fs.readFileSync(meta, 'utf8')), pv = M._provenance || {};
    if (type === 'SF50') { if (!pv.sources_sha256) { pbad.push('SF50: no sources_sha256 in _provenance'); continue; } const t = treeOf(pv.sources_sha256);
      if (t.tree !== pv.sources_tree_sha256) pbad.push('SF50 builder sources changed since the build: ' + t.changed.join(', ')); prov.SF50 = { builder_state: pv.builder_state, sources: Object.keys(pv.sources_sha256).length, tree: String(pv.sources_tree_sha256).slice(0, 16) }; }
    if (type === 'PC12') { const v = pv.variant; if (!v) { prov.PC12 = 'pc12/out copy (no variant)'; continue; } const bs = sha(path.join(REPO, v.builder)); if (bs !== v.builder_sha256) pbad.push('PC12 variant builder changed since the build');
      const t = treeOf(v.pc12_sources || {}); if (t.tree !== v.pc12_sources_tree_sha256) pbad.push('PC12 pc12 sources changed since the variant build: ' + t.changed.join(', '));
      prov.PC12 = { variant: v.set, builder_sha256: v.builder_sha256.slice(0, 16), pc12_sources_tree: v.pc12_sources_tree_sha256.slice(0, 16), pc12_sources_dirty: v.pc12_sources_dirty }; } }
  check('provenance', 'builder sources on disk = the ones recorded at build time (rebuild reproduces the GLB)', pbad.length === 0, { problems: pbad, models: prov });
  const pdir = path.join(HWD, 'docs/phase3'), cap = fs.existsSync(path.join(pdir, 'SOURCES.json')) ? JSON.parse(fs.readFileSync(path.join(pdir, 'SOURCES.json'), 'utf8')) : {};
  const imgs = fs.readdirSync(pdir).filter(f => /\.(png|jpe?g)$/i.test(f)); const cur = Object.fromEntries(Object.entries(MODELS).map(([t, e]) => [t, sha(fileURLToPath(e.url))]));
  const noCap = imgs.filter(f => !cap[f] || !cap[f].caption || !cap[f].licence), stale = [], superseded = [];
  for (const f of imgs) { const c = cap[f]; if (!c || !c.model) continue; if (c.superseded) { superseded.push(f); continue; } if (c.model_sha256 !== cur[c.model]) stale.push(`${f}: ${String(c.model_sha256).slice(0, 12)} != ${c.model} ${cur[c.model].slice(0, 12)}`); }
  const orphan = Object.keys(cap).filter(k => k !== '_note' && !imgs.includes(k));
  check('provenance', 'docs/phase3: every image captioned (licence notice), current-model claims match the model file', noCap.length === 0 && stale.length === 0 && orphan.length === 0,
    { images: imgs.length, uncaptioned: noCap, stale_claims: stale, captions_without_image: orphan, marked_superseded: superseded.length });
  // the write-ups too (fix round 2: docs/phase3_render.md kept calling a superseded SF50 build 'final'): every
  // docs/phase3_*.md that names a model must name its CURRENT file hash (first 8 hex digits) or carry a SUPERSEDED banner in
  // its first 15 lines
  const mdBad = [];
  for (const f of fs.readdirSync(path.join(HWD, 'docs')).filter(f => /^phase3_.*\.md$/.test(f))) { const t = fs.readFileSync(path.join(HWD, 'docs', f), 'utf8'); const head = t.split('\n').slice(0, 15).join('\n');
    if (/SUPERSEDED/.test(head)) continue;
    for (const [type, re] of [['SF50', /SF50|sf50\.glb/], ['PC12', /PC-12|pc12\.glb/]]) if (cur[type] && re.test(t) && !t.includes(cur[type].slice(0, 8))) mdBad.push(`docs/${f}: names ${type} but not its current hash ${cur[type].slice(0, 8)}`); }
  // licence notice plumbing outside M1 / M2 (fix round 2, finding F12 residual): the docs/phase3 row in docs/ATTRIBUTION.md
  // and docs/phase3 in tools/check_airport.py's SOURCES scope. Not M1 / M2 files: reported as KNOWN until their owners add them
  const attr = fs.readFileSync(path.join(HWD, 'docs/ATTRIBUTION.md'), 'utf8'), chk = fs.readFileSync(path.join(HWD, 'tools/check_airport.py'), 'utf8');
  const plumb = { attribution_row: /docs\/phase3\//.test(attr), check_airport_scope: /hwd3d\/docs\/phase3/.test(chk) };
  check('provenance', 'docs/phase3 in docs/ATTRIBUTION.md and in tools/check_airport.py SOURCES coverage', plumb.attribution_row && plumb.check_airport_scope,
    { ...plumb, missing: Object.values(plumb).filter(v => !v).length, proposed_diffs: 'docs/phase3_models.md section 8 items 5 / 6' });
  check('provenance', 'docs/phase3_*.md name the current model hashes (or are marked SUPERSEDED)', mdBad.length === 0, mdBad.length ? mdBad : 'every write-up current or marked');
}

// ---- 13. a synthetic glb exercising the generic paths the pc12 file does not use (FLOAT positions in an interleaved
// buffer with byteStride, a node rotation quaternion, a node matrix, UNSIGNED_INT indices, no normals, a light anchor in
// node extras, an unknown light kind)
{
  const box = (cx, cy, cz, h) => { const P = []; for (let k = 0; k < 8; k++) P.push([cx + (k & 1 ? h : -h), cy + (k & 2 ? 2 * h : 0), cz + (k & 4 ? h : -h)]); return P; };
  const BI = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1, 2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3];
  const meshes = [[[-1, 1, 0], [1, 1, 0], [0, 2, -3]], box(0, 0, 0, 0.15), box(0, 0, 0, 0.15), box(0, 0, 0, 0.1)];
  const bin = []; const views = [], accs = [], gm = [];
  meshes.forEach((V, i) => {
    const I = V.length === 3 ? [0, 1, 2] : BI; const off = bin.length * 4;
    for (const v of V) bin.push(v[0], v[1], v[2], 0, 0, 0);
    views.push({ buffer: 0, byteOffset: off, byteLength: V.length * 24, byteStride: 24 });
    accs.push({ bufferView: views.length - 1, componentType: 5126, count: V.length, type: 'VEC3' });
    const ioff = bin.length * 4; for (const k of I) bin.push(k);
    views.push({ buffer: 0, byteOffset: ioff, byteLength: I.length * 4 }); accs.push({ bufferView: views.length - 1, componentType: 5125, count: I.length, type: 'SCALAR' });
    gm.push({ primitives: [{ attributes: { POSITION: accs.length - 2 }, indices: accs.length - 1, material: i === 0 ? 0 : 1 }] });
  });
  const f32 = new Float32Array(bin), u32 = new Uint32Array(f32.buffer);
  let o = 0; meshes.forEach((V) => { o += V.length * 6; const n = V.length === 3 ? 3 : BI.length; const I = V.length === 3 ? [0, 1, 2] : BI; for (let k = 0; k < n; k++) u32[o + k] = I[k]; o += n; });
  const q90 = [0, Math.SQRT1_2, 0, Math.SQRT1_2];
  const json = { asset: { version: '2.0' }, scene: 0, scenes: [{ nodes: [0] }], buffers: [{ byteLength: f32.byteLength }], bufferViews: views, accessors: accs, meshes: gm,
    materials: [{ name: 'paint_white', pbrMetallicRoughness: { baseColorFactor: [0.9, 0.9, 0.9, 1], metallicFactor: 0, roughnessFactor: 0.3 } }, { name: 'tire', pbrMetallicRoughness: { baseColorFactor: [0.05, 0.05, 0.05, 1], metallicFactor: 0, roughnessFactor: 0.9 } }],
    nodes: [{ name: 'AC', children: [1, 2, 3, 4, 5, 6] },
      { name: 'body', mesh: 0, extras: { part: 'body' } },
      { name: 'gear_main_L', mesh: 1, translation: [-1.5, 0, 1], extras: { part: 'gear_main_L', pivot: { origin: [-1.5, 0, 1], axis: [0, 0, 1], kind: 'gear', retract: 90 } } },
      { name: 'gear_main_R', mesh: 2, translation: [1.5, 0, 1], rotation: q90, extras: { part: 'gear_main_R', pivot: { origin: [1.5, 0, 1], axis: [0, 0, 1], kind: 'gear', retract: -90 } } },
      { name: 'gear_nose', mesh: 3, matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -2.5, 1], extras: { part: 'gear_nose', pivot: { origin: [0, 0, -2.5], axis: [1, 0, 0], kind: 'gear', retract: -95 } } },
      { name: 'nav_left', translation: [-5, 1, 0.5], extras: { light: 'navL' } },
      { name: 'ice', translation: [-1, 1.2, -1], extras: { light: 'iceLight' } }] };
  let js = new TextEncoder().encode(JSON.stringify(json)); const pad = (4 - js.length % 4) % 4; js = Uint8Array.from([...js, ...Array(pad).fill(32)]);
  const total = 12 + 8 + js.length + 8 + f32.byteLength, G = new Uint8Array(total), dv = new DataView(G.buffer);
  dv.setUint32(0, 0x46546c67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true); dv.setUint32(12, js.length, true); dv.setUint32(16, 0x4e4f534a, true); G.set(js, 20);
  dv.setUint32(20 + js.length, f32.byteLength, true); dv.setUint32(24 + js.length, 0x004e4942, true); G.set(new Uint8Array(f32.buffer), 28 + js.length);
  try {
    const S = convertGLB(G, { name: 'synthetic' }); const body = S.groups.find(g => g.key === 'static').opaque; const p2 = [body.pos[6], body.pos[7], body.pos[8]];
    const ok = Math.hypot(S.originGl[0], S.originGl[1], S.originGl[2] - 1) < 1e-6 && Math.hypot(p2[0] - 4, p2[1] - 2, p2[2]) < 1e-5 && S.lights.navL && Math.hypot(S.lights.navL.p[0] - 0.5, S.lights.navL.p[1] - 1, S.lights.navL.p[2] + 5) < 1e-6 && Math.abs(S.wheelbase - 3.5) < 1e-6 && Math.abs(S.track - 3) < 1e-6 && S.lights.iceLight;
    check('synthetic', 'generic glTF paths (FLOAT stride 24, quaternion, matrix, UINT indices, no normals, light extras incl. an unknown kind)', ok,
      { origin_gl: S.originGl, nose_vertex_local: p2, navL: S.lights.navL && S.lights.navL.p, iceLight: S.lights.iceLight && S.lights.iceLight.p, wheelbase: S.wheelbase, track: S.track, expected: 'origin (0,0,1); vertex (4,2,0); navL (0.5,1,-5); iceLight kept; wheelbase 3.5; track 3' });
  } catch (err) { check('synthetic', 'generic glTF paths', false, String(err && err.stack || err)); }
}
const out = process.argv.find(a => a.startsWith('--json=')); if (out) fs.writeFileSync(path.resolve(HWD, out.slice(7)), JSON.stringify({ when: new Date().toISOString(), fails, known, results }, null, 1));
console.log(fails ? `${fails} check(s) FAILED` : `all checks passed${known ? ` (${known} known deviation(s), see above)` : ''}`);
process.exit(fails ? 1 : 0);
