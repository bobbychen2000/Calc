// Blender building assets (data/buildings3d/*.glb; docs/research/buildings3d.md) in the three.js renderer: loads the
// groups (control tower, International Terminal, domestic terminals, elevated landside roadways, landside), switches their
// levels of detail per building from the camera distance, applies the baked ambient occlusion (glTF occlusionTexture on
// TEXCOORD_1), casts and receives shadows, adds the night hooks (lit glazing, the tower's LED ribbon, obstruction lights)
// and hides the first-pass extrusions each group replaces once that group is on screen (js/live/world.js routes them into
// one item per group: data/buildings3d/integration.js, tools/blender/b3d_integrate.py). Until a group has loaded, or if it
// fails, the first-pass buildings stay: the scene never has a hole.
//
// Files (manifest.json#<group>.files): full = tower.glb (height family F2, the default since the tower review round 1;
// ?b3dtower=f1 -> tower_f1.glb, the published-height hypothesis), itb.glb, domestic.glb, roadways.glb, landside.glb
// (LOD0-2 each); lod2 = the *_lod2.glb subtrees alone (the far LOD). The artifact build serves them renamed
// (window.SFO_B3D_BASE, default 'data/buildings3d/'; window.SFO_B3D_EXT, default '.glb'; the phone artifact uses '.wasm'
// like the aircraft models, tools/build3/phone_artifact_page.py; window.SFO_B3D_PARTS = {file: n}: a file the artifact
// split into n pieces (<name>.part<i><ext>, the 15-MB per-file limit) is fetched in pieces and joined).
// Modes (?b3d=full|near|lod2|0): high / ultra tiers 'full' (every group's full file); the low tier (phones) and the
// medium tier (deviceMemory <= 4 GB; review finding 10) 'near' (integration review round 1, finding 5: phones used to show
// only LOD2 at every distance, gate and tower views included): the lod2 files first (~6 MB, the whole airport at once),
// then each group's full file when the camera comes
// within that group's LOD2 switch distance (the tier's tighter range) of it, one file at a time; the full file replaces
// the lod2 one, so near units show LOD0 / LOD1 as on the desktop. 'lod2' = the far files only (QA), '0' = the first-pass
// buildings only (old-vs-new comparisons). Review round 2 (finding 4): the landside group comes per building
// (lsu_<unit>.glb, tools/blender/b3d_split.py; index integration.js units.landside): full mode loads every unit, near mode
// each unit within its own trigger (low tier: its LOD1 switch, medium: LOD2; x range x 1.1 + 60 m); near mode releases
// units (all due ones in one pass) and group full files (back to the lod2 file) once every trigger of theirs is beyond
// RELEASE x + 100 m for RELEASE_S; the low tier compiles only the LOD on screen (_compile).
//
// LOD (each group's manifest lod rule; switch distances from the LOD nodes' extras.switch_m, scaled by the quality tier's
// `lod` range relative to the high tier's 1800 m: low 0.56, medium 0.72): a "LOD set" is a node whose children are LOD0 /
// LOD1 / LOD2 nodes (tower, ITB, domestic and roadways: the root; landside: every building node). LOD2 is shown when the
// camera is beyond its switch distance from the set's bounding box; otherwise LOD0 or LOD1 per unit (domestic and
// roadways: extras.building; ITB: per part, the group spans 650 m; tower and landside buildings: the whole set), from
// the distance to the unit's bounding box (the nearest point, not the node origin: a 400-m pier seen from its tip is
// near), with 5 % hysteresis. Within a unit the static meshes of one material are merged at load (review finding 10:
// landside 286 -> ~190 LOD0 primitives, tower 30 -> 23; ITB / domestic units already hold one mesh per material).
//
// Materials: glTF PBR as exported (GLTFLoader: MeshStandard / MeshPhysical with KHR_materials_ior / _specular), turned
// into node materials so an emission term can be added. AO atlases (single-channel data) are repacked at load as R8
// textures (RedFormat), capped at the tier's maxTex (low 1024, medium 2048): review finding 10, six 2048-px atlases were
// ~134 MB as RGBA8 with mips, ~34 MB as R8. Night glow = nightE (renderer3: night factor x LAMP_M, lamp units -> sky
// units) x GLOW[kind].color x GLOW[kind].k x an interior pattern (review finding 2: the gate-room glazing read as
// saturated white cards): per 3 m x 4 m cell a level 0.6-1.25 (lit bays), within each 4-m storey a vertical gradient
// (floor 0.72 .. ceiling 1.08, the lamps are on the ceiling), office-type cells 55 % lit; the product is soft-capped at
// GLOW_CAP lamp units (x nightE: exposed ~0.9 at the keyed night exposure, below the grade's shoulder). Masked to the
// panes where the glass has a base-colour tile (mullions / frit stay dark). Kinds by material name / extras (the assets'
// own tags): hall (terminal glazing), office (hotel, CAC, station-block window bands, the tower's base building and shaft
// slot panes: slot_glass; the tower's perforated slot screens stay dark, photo t5), station (AirTrain station glass), roofglass (skylights, glazed roof lines, the T1 glass canopy: lit from below,
// weaker), cab (tower cab: k 0 by default, photo t5 shows it dark; close-out r3), led (tower ribbon, extras.led: the LED waterfall as objects.js
// id 16), beacon (red obstruction light, extras.obstruction_light: a lamp, not capped), soffit (garage slab undersides,
// canopy and station ceilings). GLOW values are uniforms (Buildings3D.glow / setGlow) so the environment work can retune
// them; inferred, not measured.
//
// Physical plausibility: the assets were checked against the stands, bridges, aircraft envelopes and taxiways by their
// groups and together by tools/blender/b3d_integrate.py (data/buildings3d/integration.json#plausibility).
import { THREE, TSL } from './lib.js';
import { hash12 } from './tsl/common.js';
import { B3D_INTEGRATION } from '../../data/buildings3d/integration.js';
const { uniform, vec2, vec3, float, mix, smoothstep, sin, floor, fract, positionWorld, luminance, texture, uv, materialEmissive } = TSL;

export const B3D_GROUPS = ['tower', 'itb', 'domestic', 'roadways', 'landside'];
const FILE_FULL = { tower: 'tower', itb: 'itb', domestic: 'domestic', roadways: 'roadways', landside: 'landside' };
const HYST = 0.05, LOD_REF = 1800; // QUALITY3.high.lod
const RELEASE = 1.3, RELEASE_S = 8; // near mode: a unit / group file is released beyond RELEASE x its trigger + 100 m for RELEASE_S s
// night glow per kind (lamp units, x renderer3 nightE): colour of the light behind the glass and its mean level.
// Round 1 (finding 2): hall 0.8 -> 0.30 etc.: at the keyed night exposure (renderer3 NIGHT_EXPOSURE) one lamp unit x nightE
// is exposed to KEY_NIGHT x pi / (RHO_CONC x E_STAND) = 2.2, so 0.8 x (1 +- 15 %) gave ~1.8-2.0, and with the frame-metered
// exposure and bloom the gate-room panes clipped to white. The first-pass concourse (objects.js concourse()) spans
// 0.36-1.76 over floor / walls / ceiling lamps; the assets have no interior, so the mean is lowered and the pattern below
// stands for it. Inferred (no measured SFO night luminances).
// cab (close-out round 3, integration-6): off by default - the only dusk / night photo of the tower (t5, Wikimedia Commons
// "San Francisco International Airport - April 2018 (0463)", CC BY-SA, refs/cache/buildings/review_likeness/t5.jpg) shows
// the cab glass dark under a lit LED ribbon (controllers keep the cab dark at night); the old inferred teal 0.25 glowed.
// Colour kept for setGlow('cab', {k}) (manifest.json#integration.glow: every value here is inferred and configurable).
export const GLOW_DEF = {
  hall: [[1.0, 0.9, 0.76], 0.30], office: [[1.0, 0.82, 0.6], 0.34], station: [[0.95, 0.95, 1.0], 0.32], roofglass: [[1.0, 0.9, 0.76], 0.14],
  cab: [[0.25, 0.4, 0.35], 0.0], led: [[1.0, 1.0, 1.0], 0.30], beacon: [[1.0, 0.06, 0.04], 40.0],
  // slab undersides of the garages, canopy and station ceilings: the first-pass garages' night level (objects.js id 3:
  // vec3(0.9, 0.95, 1.0) x 0.35 over the open bays), lowered with the others (inferred)
  soffit: [[0.9, 0.95, 1.0], 0.22],
};
const GLOW_CAP = 0.42; // lamp units: soft cap of every glow kind but the beacon (exposed ~0.9 at the keyed night exposure)

function glowKind(m) {
  const n = (m.name || '').replace(/@.*$/, '').replace(/\.L\d$/, ''); const ex = m.userData || {};
  if (ex.obstruction_light || n === 'red_light') return 'beacon';
  if (ex.led) return 'led';
  if (n === 'cab_glass') return 'cab';
  if (/^(glass_roof|glass_roof_under|glass_sky|glass_canopy)$/.test(n)) return 'roofglass';
  if (/^(glass_hyatt|glass_band|cac_wall|slot|slot_glass|ribbon|glass_c3c)$/.test(n) || /^ibf_(curtain|glass)/.test(n)) return 'office'; // glass_c3c: domestic C3C office block (review r2)
  if (/^station_glass$/.test(n)) return 'station';
  if (/glass|curtain/.test(n)) return 'hall';
  if (/soffit/.test(n)) return 'soffit';
  return null;
}
const lodIx = (o) => { const ex = o.userData || {}; if (Number.isInteger(ex.lod)) return ex.lod; const m = /^LOD(\d)(_|$)/.exec(o.name || ''); return m ? +m[1] : null; };
const swOf = (o) => { const s = (o.userData || {}).switch_m; return Array.isArray(s) ? +s[0] : (s != null ? +s : null); };

export class Buildings3D {
  // R: js/three/renderer3.js Renderer3 (engine, staticGroup, nightE, time, Q, tier, world)
  constructor(R) {
    const qs = new URLSearchParams(location.search);
    this.R = R; this.E = R.engine;
    const q = qs.get('b3d');
    this.mode = q === '0' || q === 'off' ? 'off' : q === 'lod2' || q === 'full' || q === 'near' ? q : (R.tier === 'low' || R.tier === 'medium' ? 'near' : 'full');
    this.towerFamily = qs.get('b3dtower') === 'f1' ? 'f1' : 'f2'; // tower.glb = F2 (default), tower_f1.glb = F1 (manifest.json#tower)
    this.base = window.SFO_B3D_BASE || 'data/buildings3d/'; this.ext = window.SFO_B3D_EXT || '.glb'; this.parts = window.SFO_B3D_PARTS || {};
    this.lodScale = (R.Q && R.Q.lod ? R.Q.lod : LOD_REF) / LOD_REF;
    this.group = new THREE.Group(); this.group.name = 'buildings3d'; this.E.scene.add(this.group);
    this.loaded = {}; this.kind = {}; this.failed = {}; this.sets = []; this.cabGlass = []; this.near = {}; this.pending = null;
    // landside per building (review round 2, finding 4): data/buildings3d/lsu_<unit>.glb (tools/blender/b3d_split.py), index
    // in integration.js; loaded per unit near the camera (near mode) or all (full mode), released when far again
    this.unitIdx = (B3D_INTEGRATION.units && B3D_INTEGRATION.units.landside) || null; this.units = {}; this.unitFar = {}; this.far = {};
    this.texRef = new Map(); // shared textures (named 'lsu:<image>' by the split): one GPU texture per image, refcounted
    this.stats = { files: {}, ms: {}, ao: [], merged: {} };
    this.glow = {}; for (const [k, [c, v]] of Object.entries(GLOW_DEF)) this.glow[k] = { color: uniform(new THREE.Color(...c)), k: uniform(v) };
    this.glowCap = uniform(GLOW_CAP);
    this.done = this.mode === 'off'; this.frame = 0; this._tmpV = new THREE.Vector3(); this._tex = new Map();
    this.tower = B3D_INTEGRATION.tower || null; // fallback anchors; replaced by the loaded tower file's own (root extras.anchors)
    const only = qs.get('b3donly'); this.groups = only ? B3D_GROUPS.filter(g => only.split(',').includes(g)) : B3D_GROUPS; // QA: ?b3donly=tower
  }
  start() {
    if (this.mode === 'off') { console.log('[b3d] off (?b3d=0): first-pass buildings'); return; }
    this._p = this._loadAll().catch(e => console.warn('[b3d] load', e)).finally(() => { this.done = true; });
  }
  file(g, kind) {
    let f = FILE_FULL[g];
    if (g === 'tower' && kind === 'full' && this.towerFamily === 'f1') f = 'tower_f1';
    return kind === 'lod2' ? f + '_lod2' : f;
  }
  url(g, kind = this.mode === 'full' ? 'full' : 'lod2') { return this.base + this.file(g, kind) + this.ext; }
  async _fetchGlb(g, kind) {
    // a file the artifact split into pieces (window.SFO_B3D_PARTS[file] = n): fetched in order and joined
    const f = this.file(g, kind), n = +(this.parts[f] || 0);
    const loader = this._loader || (this._loader = new THREE.GLTFLoader());
    if (!n) return loader.loadAsync(this.url(g, kind));
    const bufs = []; for (let i = 0; i < n; i++) { const r = await fetch(this.base + f + '.part' + i + this.ext); if (!r.ok) throw new Error(f + '.part' + i + ': HTTP ' + r.status); bufs.push(new Uint8Array(await r.arrayBuffer())); }
    const all = new Uint8Array(bufs.reduce((a, b) => a + b.length, 0)); let o = 0; for (const b of bufs) { all.set(b, o); o += b.length; }
    return loader.parseAsync(all.buffer, this.base);
  }
  async _loadAll() {
    // sequential: one decode + upload + compile at a time (phones; the main thread stalls once per group, not four
    // times at once); the tower first (smallest, and the tower view), the landside last (largest, mostly far away)
    const kind = this.mode === 'full' ? 'full' : 'lod2';
    for (const g of this.groups) {
      if (g === 'landside' && this.unitIdx && this.mode !== 'lod2') { await this._loadLandsideUnits(kind); continue; }
      await this._loadGroup(g, kind);
    }
    if (this.mode === 'near') console.log('[b3d] near mode: lod2 files shown; full files load as the camera comes near (' + Object.keys(this.near).join(', ') + ')');
  }
  async _loadGroup(g, kind) {
    const t0 = performance.now(), url = this.url(g, kind);
    try {
      const gltf = await this._fetchGlb(g, kind);
      const root = gltf.scene; root.name = 'b3d_' + g; root.userData.b3dKind = kind;
      this._prepare(g, root, kind);
      if (g === 'tower') this._towerAnchors(root);
      const t1 = performance.now();
      await this._compile(root);
      const old = this.loaded[g];
      if (g === 'landside' && this.unitIdx && this.lsBox) { this.lsBox.add(root); this.lsLod2 = root; this.loaded[g] = this.lsBox; this.kind[g] = 'units'; }
      else { this.group.add(root); this.loaded[g] = root; this.kind[g] = kind; if (old) this._drop(old); }
      if (kind === 'lod2' && this.mode === 'near' && !(g === 'landside' && this.unitIdx)) this._nearTriggers(g, root);
      this._swapOld();
      if (g === 'tower') this._towerCamera();
      const key = g + (kind === 'full' ? '' : '_lod2'); this.stats.ms[key] = [Math.round(t1 - t0), Math.round(performance.now() - t1)];
      const fs = this.stats.files[key];
      console.log('[b3d] ' + g + ' (' + url + ') shown: load+prepare ' + this.stats.ms[key][0] + ' ms, compile ' + this.stats.ms[key][1] + ' ms; ' + fs.tris + ' tris in ' + fs.meshes + ' meshes (' + fs.merged + ' merged away), ' + fs.materials + ' materials');
    } catch (e) { this.failed[g + (kind === 'full' ? '' : '_lod2')] = String(e && e.message || e); console.warn('[b3d] ' + g + ' (' + kind + ') failed, ' + (this.loaded[g] ? 'previous file kept' : 'first-pass buildings kept') + ':', e); }
  }
  // remove a replaced root (the lod2 file once the group's full file is on screen): its sets, cab glass and GPU data
  _drop(root) {
    if (root.parent) root.parent.remove(root);
    this.sets = this.sets.filter(S => S.root !== root); this.cabGlass = this.cabGlass.filter(o => o.userData.b3dRoot !== root);
    const mats = new Set();
    root.traverse(o => { if (!o.isMesh) return; o.geometry.dispose(); for (const m of [].concat(o.material)) mats.add(m); });
    // one reference per material slot (as _material counts them); a texture shared with files still on screen (the split
    // landside units' common images) stays until its last user goes
    for (const m of mats) {
      for (const k of ['map', 'normalMap', 'aoMap', 'roughnessMap', 'metalnessMap', 'emissiveMap']) {
        const t = m[k]; if (!t) continue;
        const n = (this.texRef.get(t) || 1) - 1; if (n > 0) { this.texRef.set(t, n); continue; }
        this.texRef.delete(t); t.dispose(); for (const [kk, v] of this._tex) if (v === t) this._tex.delete(kk);
      }
      m.dispose();
    }
  }
  // landside per unit (review round 2, finding 4): full mode loads every unit file; near mode the lod2 file, then the
  // units near the camera (per-unit triggers: the LOD1 switch on the low tier - phones show the landside LOD2 out to
  // the LOD1 distance -, the LOD2 switch on the medium tier; x the tier's range, + 10 % + 60 m), released when far again
  async _loadLandsideUnits(kind) {
    this.lsBox = new THREE.Group(); this.lsBox.name = 'b3d_landside'; this.group.add(this.lsBox);
    if (kind === 'lod2') {
      await this._loadGroup('landside', 'lod2');
      const tLod = this.R.tier === 'low' ? 'switch1_m' : 'switch2_m';
      this.unitTrig = this.unitIdx.map(e => ({ e, box: new THREE.Box3(new THREE.Vector3(...e.box.slice(0, 3)), new THREE.Vector3(...e.box.slice(3))), d: (e[tLod] != null ? e[tLod] : 1400) * this.lodScale * 1.1 + 60 }));
      console.log('[b3d] landside: ' + this.unitIdx.length + ' unit files on demand (trigger ' + tLod + ')');
      return;
    }
    this.lsBox.visible = false;   // full mode: the first-pass landside stays until every unit is in (no hole, no overlap)
    for (const e of this.unitIdx) await this._loadUnit(e);
    this.lsBox.visible = true; this.loaded.landside = this.lsBox; this.kind.landside = 'units'; this._swapOld();
  }
  async _loadUnit(e) {
    const t0 = performance.now(), loader = this._loader || (this._loader = new THREE.GLTFLoader());
    try {
      const gltf = await loader.loadAsync(this.base + e.file + this.ext);
      const root = gltf.scene; root.name = 'b3d_ls_' + e.unit; root.userData.b3dKind = 'unit';
      this._prepare('landside', root, 'unit:' + e.unit);
      const t1 = performance.now(); await this._compile(root);
      this.lsBox.add(root); this.units[e.unit] = root; delete this.unitFar[e.unit];
      const n = this.lsLod2 && this.lsLod2.getObjectByName(e.unit); if (n && n !== root) n.visible = false;
      const fs = this.stats.files['landside_unit:' + e.unit]; this.stats.ms['unit:' + e.unit] = [Math.round(t1 - t0), Math.round(performance.now() - t1)];
      console.log('[b3d] landside unit ' + e.unit + ' shown: ' + Math.round(t1 - t0) + ' + ' + Math.round(performance.now() - t1) + ' ms; ' + (fs ? fs.tris + ' tris' : ''));
    } catch (err) { this.failed['unit:' + e.unit] = String(err && err.message || err); console.warn('[b3d] landside unit ' + e.unit + ' failed (LOD2 kept):', err); }
  }
  _dropUnit(name) {
    const r = this.units[name]; if (!r) return;
    this._drop(r); delete this.units[name]; delete this.unitFar[name]; delete this.stats.files['landside_unit:' + name];
    const n = this.lsLod2 && this.lsLod2.getObjectByName(name); if (n) n.visible = true;
    console.log('[b3d] landside unit ' + name + ' released (far)');
  }
  // near mode: the lod2 file's LOD2 subtrees with their switch distances (scaled by the tier); update() loads the full
  // file once the camera is within one of them (+10 %, + 60 m: the file is on screen before the units would switch)
  _nearTriggers(g, root) {
    const T = []; root.updateMatrixWorld(true);
    root.traverse(P => { for (const c of P.children) if (lodIx(c) === 2) { const s = swOf(c); T.push({ box: new THREE.Box3().setFromObject(c), d: (s != null ? s : 1400) * this.lodScale * 1.1 + 60 }); } });
    this.near[g] = T;
  }
  _nearUpdate(p) {
    if (this.mode !== 'near' || !this.done || this.pending) return;
    let best = null; const now = performance.now();
    for (const g of this.groups) {
      if (this.kind[g] !== 'lod2' || this.failed[g] || !this.near[g]) continue;
      for (const t of this.near[g]) { const d = t.box.distanceToPoint(p); if (d < t.d && (!best || d - t.d < best[1])) best = [g, d - t.d]; }
    }
    for (const t of this.unitTrig || []) {
      if (this.units[t.e.unit] || this.failed['unit:' + t.e.unit]) continue;
      const d = t.box.distanceToPoint(p); if (d < t.d && (!best || d - t.d < best[1])) best = ['unit', d - t.d, t.e];
    }
    if (best) {
      this.pending = best[0] === 'unit' ? 'landside:' + best[2].unit : best[0];
      (best[0] === 'unit' ? this._loadUnit(best[2]) : this._loadGroup(best[0], 'full')).finally(() => { this.pending = null; });
      return;
    }
    // release (review round 2, finding 4: a full file was never released): a unit / group whose triggers are all farther
    // than RELEASE x their distance + 100 m for RELEASE_S goes back to its LOD2 (the unit file dropped; a group's lod2 file
    // reloaded, which drops the full one)
    // units: every one that is due goes in this pass (a drop only disposes GPU data; nothing is fetched)
    let dropped = 0;
    for (const t of this.unitTrig || []) {
      if (!this.units[t.e.unit]) continue;
      if (t.box.distanceToPoint(p) > t.d * RELEASE + 100) { const f = this.unitFar[t.e.unit] || (this.unitFar[t.e.unit] = now); if (now - f > RELEASE_S * 1000) { this._dropUnit(t.e.unit); dropped++; } }
      else delete this.unitFar[t.e.unit];
    }
    if (dropped) return;
    for (const g of this.groups) {
      if (this.kind[g] !== 'full' || !this.near[g]) continue;
      if (this.near[g].every(t => t.box.distanceToPoint(p) > t.d * RELEASE + 100)) {
        const f = this.far[g] || (this.far[g] = now);
        if (now - f > RELEASE_S * 1000) { delete this.far[g]; this.pending = g; this._loadGroup(g, 'lod2').finally(() => { this.pending = null; }); return; }
      } else delete this.far[g];
    }
  }
  // QA (tools/blender/b3d_views_job.mjs): nothing loading and no group waiting for its full file at this camera
  settled(camPos = this._lastCam) {
    if (!this.done || this.pending) return false;
    if (this.mode !== 'near' || !camPos) return true;
    const p = new THREE.Vector3(camPos[0], camPos[1], camPos[2]);
    for (const g of this.groups) if (this.kind[g] === 'lod2' && !this.failed[g] && (this.near[g] || []).some(t => t.box.distanceToPoint(p) < t.d)) return false;
    for (const t of this.unitTrig || []) if (!this.units[t.e.unit] && !this.failed['unit:' + t.e.unit] && t.box.distanceToPoint(p) < t.d) return false;
    return true;
  }
  // compile the group's programs before it is shown (all LODs and units, whatever the current view), so the first
  // frames after a LOD switch do not stall
  // Low tier (review round 2, finding 4): only the LOD each unit shows at the current camera, with frustum culling as
  // set - forcing every LOD visible with culling off uploaded all three LODs' geometry and textures of a file at once; a
  // later LOD switch compiles its programs then (one short stall on a phone instead of the whole file's GPU memory)
  async _compile(root) {
    const E = this.E; const saved = []; const low = this.R.tier === 'low';
    if (low) { if (this._lastCam) { const p = new THREE.Vector3(...this._lastCam); for (const S of this.sets) if (S.root === root) this._setLod(S, p); } }
    else root.traverse(o => { saved.push([o, o.visible, o.frustumCulled]); o.visible = true; o.frustumCulled = false; });
    try { await Promise.race([E.renderer.compileAsync(root, E.camera, E.scene), new Promise(r => setTimeout(r, 20000))]); }
    catch (e) { console.warn('[b3d] compileAsync', e); }
    for (const [o, v, f] of saved) { o.visible = v; o.frustumCulled = f; }
  }
  _prepare(g, root, kind) {
    const R = this.R, Q = R.Q || {}; const mats = new Map(); this._aoSrc = new Map(); this._otherSrc = new Set();
    root.updateMatrixWorld(true);
    root.traverse(o => {
      o.matrixAutoUpdate = false;
      if (!o.isMesh) return;
      const m0 = o.material; let m = mats.get(m0);
      if (!m) { m = this._material(m0, Q); mats.set(m0, m); }
      o.material = m; o.userData.b3dRoot = root;
      const transp = m.transparent || m.blending !== THREE.NormalBlending && m.blending !== THREE.NoBlending;
      o.castShadow = !transp && !(o.isInstancedMesh && R.tier === 'low'); o.receiveShadow = true;
      if (m.userData.ambient_only) o.receiveShadow = false; // sky light only (_material): no sun, so no shadow lookup
      if (/^cab_glass/.test(m0.name || '')) this.cabGlass.push(o);
    });
    // the original AO images (repacked as R8) are released unless another slot samples them
    for (const [src, img] of this._aoSrc) if (!this._otherSrc.has(src) && img && img.close) { try { img.close(); } catch (e) { /* not a bitmap */ } }
    const nMerged = this._lodSets(g, root);
    let tris = 0, meshes = 0;
    root.traverse(o => { if (!o.isMesh) return; meshes++; const idx = o.geometry.index; tris += (idx ? idx.count : o.geometry.attributes.position.count) / 3 * (o.isInstancedMesh ? o.count : 1); });
    const key = String(kind).startsWith('unit:') ? 'landside_' + kind : g + (kind === 'full' ? '' : '_lod2');
    this.stats.files[key] = { url: String(kind).startsWith('unit:') ? kind : this.url(g, kind), tris: Math.round(tris), meshes, materials: mats.size, merged: nMerged };
  }
  // glTF material -> node material with the night emission hook; textures get the tier's anisotropy
  _material(m0, Q) {
    const C = m0.isMeshPhysicalMaterial ? THREE.MeshPhysicalNodeMaterial : THREE.MeshStandardNodeMaterial;
    const m = new C(); for (const k in m0) { if (k === 'uuid' || k === 'id' || k === 'type' || k.startsWith('is') || k === '_listeners') continue; try { m[k] = m0[k]; } catch (e) { /* read-only */ } }
    m.name = m0.name; m.userData = { ...(m0.userData || {}) };
    // one Texture per image and sampling: GLTFLoader clones a texture for every material that reads it on TEXCOORD_1
    // (GLTFLoader.assignTexture: texCoord > 0 -> texture.clone()), and each clone is its own GPU texture: the AO atlases
    // were uploaded once per material (first headless run: 4.05 GB of textures for ~0.2 GB of images)
    for (const k of ['map', 'normalMap', 'aoMap', 'roughnessMap', 'metalnessMap', 'emissiveMap']) {
      const t = m[k]; if (!t || !t.source) continue;
      if (k === 'aoMap') { m[k] = this._aoTex(t, Q); this.texRef.set(m[k], (this.texRef.get(m[k]) || 0) + 1); continue; }
      this._otherSrc.add(t.source);
      const id = /^lsu:/.test(t.name || '') ? 'n:' + t.name : t.source.uuid;   // the split landside units share images by name
      const key = id + '|' + t.channel + '|' + t.colorSpace + '|' + t.wrapS + t.wrapT + '|' + t.offset.toArray() + t.repeat.toArray() + t.rotation;
      let c = this._tex.get(key); if (!c) { c = t; c.anisotropy = Math.max(c.anisotropy || 1, Q.aniso || 4); this._tex.set(key, c); }
      else if (c !== t) t.dispose();
      m[k] = c; this.texRef.set(c, (this.texRef.get(c) || 0) + 1);
    }
    // interior placeholders behind glass (material extras.ambient_only; the tower cab floor / consoles / shade band / ceiling,
    // tower review round 2, finding 3): sky light (IBL x AO) only. The alpha-blended glass casts no shadow, so the sun
    // reached the whole floor through the glass ring and the floor sat in the PCF penumbra (low tier: a per-pixel checker;
    // tools/blender/tower_app_job.mjs experiment: GTAO off unchanged, receiveShadow off removes it)
    if (m.userData.ambient_only) m.lightsNode = TSL.lights([]);
    const kind = glowKind(m0); m.userData.b3dGlow = kind;
    if (kind) {
      const G = this.glow[kind], R = this.R; const night = R.nightE || uniform(0);
      // interior pattern (header): 3 m cells along the facade x 4 m storeys, each its own level; a gradient up the storey
      const P = positionWorld; const cy = floor(P.y.div(4.0));
      const cell = floor(P.xz.div(3.0)).add(vec2(cy.mul(31.0), cy.mul(17.0)));
      const hv = hash12(cell.add(vec2(13.0, 7.0)));
      const grad = mix(float(0.72), float(1.08), smoothstep(0.05, 0.95, fract(P.y.div(4.0))));
      let lvl = hv.mul(0.65).add(0.6).mul(grad); let col = G.color;
      if (kind === 'office') lvl = lvl.mul(smoothstep(0.43, 0.47, hash12(cell.add(vec2(3.0, 29.0)))));
      if (kind === 'led') { // objects.js id 16: a blue-cyan wave running down the ribbon
        const wave = sin(P.y.mul(0.21).sub((R.time || uniform(0)).mul(0.9))).mul(0.45).add(0.55);
        lvl = wave.mul(0.8).add(1.4).div(1.8); col = mix(vec3(0.15, 0.45, 1.0), vec3(0.2, 0.9, 0.9), wave).mul(G.color);
        // the asset's own LED colour (material extras.led_color, linear RGB; tower: the observed photo-t5 blue, an inferred
        // default of a programmable array, manifest.json#tower): the wave then modulates the level only; GLOW.led.color tints it
        const lc = m.userData.led_color; if (Array.isArray(lc) && lc.length === 3) col = vec3(+lc[0], +lc[1], +lc[2]).mul(G.color);
      }
      if (kind === 'beacon' || kind === 'cab') lvl = float(1.0);
      // soft cap (lamp units): k x lvl -> cap x (1 - exp(-k x lvl / cap)) ~ k x lvl below ~cap / 3; the beacon is a lamp
      let kk = G.k.mul(lvl);
      if (kind !== 'beacon') kk = this.glowCap.mul(float(1.0).sub(kk.div(this.glowCap).negate().exp()));
      // panes only: a base-colour tile carries the frames / frit (lighter); untextured glass glows over its whole face
      const mask = m.map ? float(1.0).sub(smoothstep(0.12, 0.35, luminance(texture(m.map, uv(m.map.channel || 0)).rgb))) : float(1.0);
      m.emissiveNode = materialEmissive.add(col.mul(kk).mul(night).mul(mask));
    }
    return m;
  }
  // AO atlas -> R8 texture (one per image and sampling), capped at the tier's maxTex; the original is used where the
  // image cannot be read back (no 2-D canvas)
  _aoTex(t, Q) {
    const key = 'ao|' + (/^lsu:/.test(t.name || '') ? 'n:' + t.name : t.source.uuid) + '|' + t.channel + '|' + t.wrapS + t.wrapT; let c = this._tex.get(key); if (c) { if (c !== t) t.dispose(); return c; }
    const img = t.image; const w = img && img.width, h = img && img.height; const max = Q.maxTex || 0;
    c = t;
    if (w > 0 && h > 0 && typeof document !== 'undefined') {
      try {
        const s = max && Math.max(w, h) > max ? max / Math.max(w, h) : 1, W = Math.max(1, Math.round(w * s)), H = Math.max(1, Math.round(h * s));
        const cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(W, H) : Object.assign(document.createElement('canvas'), { width: W, height: H });
        const cx = cv.getContext('2d', { willReadFrequently: true }); cx.imageSmoothingQuality = 'high'; cx.drawImage(img, 0, 0, W, H);
        const px = cx.getImageData(0, 0, W, H).data; const r8 = new Uint8Array(W * H); for (let i = 0, j = 0; i < r8.length; i++, j += 4) r8[i] = px[j];
        const d = new THREE.DataTexture(r8, W, H, THREE.RedFormat, THREE.UnsignedByteType);
        d.flipY = t.flipY; d.wrapS = t.wrapS; d.wrapT = t.wrapT; d.magFilter = THREE.LinearFilter; d.minFilter = THREE.LinearMipmapLinearFilter;
        d.generateMipmaps = true; d.unpackAlignment = 1; d.channel = t.channel; d.colorSpace = THREE.NoColorSpace; d.anisotropy = Math.max(1, Math.min(4, Q.aniso || 4));
        d.offset.copy(t.offset); d.repeat.copy(t.repeat); d.rotation = t.rotation; d.center.copy(t.center); d.name = (t.name || 'ao') + '_r8';
        d.needsUpdate = true; c = d; this._aoSrc.set(t.source, img);
        this.stats.ao.push([t.name || '', w, h, W, H]);
      } catch (e) { console.warn('[b3d] AO repack failed, RGBA kept', e); c = t; }
    }
    this._tex.set(key, c); return c;
  }
  // LOD sets and units (see the header); returns the number of meshes merged away
  _lodSets(g, root) {
    let merged = 0;
    root.traverse(P => {
      const lods = {}; for (const c of P.children) { const k = lodIx(c); if (k != null && /^LOD\d/.test(c.name || '')) lods[k] = c; }
      if (Object.keys(lods).length < 2) return;
      const S = { group: g, root, node: P, lods, sw: {}, box: new THREE.Box3(), units: [], cur2: null };
      for (const [k, n] of Object.entries(lods)) S.sw[k] = (swOf(n) ?? { 0: 0, 1: 400, 2: 1400 }[k]) * this.lodScale;
      for (const n of Object.values(lods)) S.box.union(new THREE.Box3().setFromObject(n));
      // units inside LOD0 / LOD1: by extras.building, else per part when the set is large, else the whole set
      const diag = S.box.getSize(this._tmpV).length();
      const units = new Map();
      for (const k of [0, 1]) {
        const n = lods[k]; if (!n) continue;
        for (const c of n.children) {
          const b = (c.userData || {}).building; const key = b ? 'b:' + b : diag > 600 ? 'p:' + (c.name || '').replace(/^L\d_/, '') : 'all';
          const u = units.get(key) || { key, nodes: { 0: [], 1: [] }, box: new THREE.Box3(), cur: null }; units.set(key, u);
          u.nodes[k].push(c); u.box.union(new THREE.Box3().setFromObject(c));
          // nodes with extras.max_dist_m (domestic mullion fins, review r1): hidden beyond that distance to their own box
          // review round 2 (finding 2): not scaled by the tier's LOD range - the limit is the fins' size in pixels, which the
          // tier does not change (the phone tier dropped them at 89 m, so BA-B at the B20 gate view read as a black slab)
          if (k === 0 && (c.userData || {}).max_dist_m != null) (u.fade = u.fade || []).push({ node: c, d: +c.userData.max_dist_m, box: new THREE.Box3().setFromObject(c) });
        }
      }
      S.units = [...units.values()];
      for (const u of S.units) for (const k of [0, 1]) if (lods[k] && u.nodes[k].length) merged += this._mergeUnit(u, k, lods[k]);
      // start: everything hidden except LOD2 (update() sets the real state on the next frame)
      for (const [k, n] of Object.entries(lods)) n.visible = +k === 2;
      this.sets.push(S);
    });
    return merged;
  }
  // merge the static meshes of one unit and LOD that share a material and vertex layout into one mesh under the LOD
  // node (review finding 10: draw calls). Kept apart: instanced meshes (cars), fading nodes (extras.max_dist_m), nodes
  // flagged led / obstruction_light, the cab glass (hidden in the cab), transparent materials (sorted per object)
  _mergeUnit(u, k, lodNode) {
    const skip = (o) => { const e = o.userData || {}; return e.max_dist_m != null || e.led || e.obstruction_light; };
    const groups = new Map();
    const visit = (o) => {
      if (skip(o)) return;
      if (o.isMesh && !o.isInstancedMesh && !o.isSkinnedMesh && !o.morphTargetInfluences && o.geometry.index && !this.cabGlass.includes(o) && !o.material.transparent) {
        const G = o.geometry; const names = Object.keys(G.attributes).sort();
        const sig = names.map(n => { const a = G.attributes[n]; return n + a.itemSize + (a.normalized ? 'n' : '') + (a.array && a.array.constructor.name) + (a.isInterleavedBufferAttribute ? 'i' : ''); }).join(',');
        const key = o.material.uuid + '|' + sig + '|' + o.castShadow + o.receiveShadow + o.renderOrder;
        (groups.get(key) || groups.set(key, []).get(key)).push(o);
      }
      for (const c of o.children) visit(c);
    };
    for (const n of u.nodes[k]) visit(n);
    let gone = 0; const inv = new THREE.Matrix4().copy(lodNode.matrixWorld).invert(); let holder = null;
    for (const list of groups.values()) {
      if (list.length < 2) continue;
      const geo = mergeInto(list, inv); if (!geo) continue;
      const m = new THREE.Mesh(geo, list[0].material); m.name = 'merged_' + list[0].material.name; m.castShadow = list[0].castShadow; m.receiveShadow = list[0].receiveShadow; m.renderOrder = list[0].renderOrder;
      m.matrixAutoUpdate = false; m.userData.b3dRoot = list[0].userData.b3dRoot; m.userData.mergedFrom = list.length;
      if (!holder) { holder = new THREE.Group(); holder.name = 'merged_' + u.key + '_L' + k; holder.matrixAutoUpdate = false; lodNode.add(holder); u.nodes[k].push(holder); }
      holder.add(m);
      for (const o of list) { o.parent && o.parent.remove(o); o.geometry.dispose(); }
      gone += list.length - 1;
    }
    if (holder) holder.updateMatrixWorld(true);
    return gone;
  }
  // per frame (renderer3 frameScene): LOD switching; the cab glass is hidden while the camera is inside the cab
  update(camPos) {
    this.frame++;
    if (this.frame % 120 === 0 && Object.keys(this.loaded).length) this._swapOld(); // items synced later
    if (!camPos) return;
    this._lastCam = [camPos[0], camPos[1], camPos[2]];
    const p = this._tmpV.set(camPos[0], camPos[1], camPos[2]);
    if (this.frame % 10 === 0) this._nearUpdate(p.clone());
    if (!this.sets.length) return;
    for (const S of this.sets) this._setLod(S, p);
    // in-cab tower camera: the alpha-blended cab glass would darken the whole view (manifest.json#tower.integration)
    if (this.cabGlass.length && this.tower && this.tower.cab_centre_world_xz) {
      // bounds of the loaded family (_towerAnchors): inside the glass ring, cab floor - 0.5 .. glass head + 0.5
      const T = this.tower, c = T.cab_centre_world_xz, g = 3.0; // GROUND_Y
      const rIn = T.glass_head_r != null ? T.glass_head_r + 0.3 : 9.0;
      const inCab = Math.hypot(p.x - c[0], p.z - c[1]) < rIn && p.y > g + (T.cab_floor_h || 60) - 0.5 && p.y < g + (T.glass_h ? T.glass_h[1] : 65) + 0.5;
      if (inCab !== this._inCab || this._cabN !== this.cabGlass.length) { this._inCab = inCab; this._cabN = this.cabGlass.length; for (const o of this.cabGlass) o.material.visible = !inCab; }
    }
  }
  _setLod(S, p) {
    const d = S.box.distanceToPoint(p); const s2 = S.sw[2];
    const far = s2 != null && S.lods[2] ? (S.cur2 ? d > s2 * (1 - HYST) : d > s2 * (1 + HYST)) : false;
    if (far !== S.cur2) { S.cur2 = far; if (S.lods[2]) S.lods[2].visible = far; if (S.lods[0]) S.lods[0].visible = !far; if (S.lods[1]) S.lods[1].visible = !far; }
    if (far) return;
    const s1 = S.sw[1] != null ? S.sw[1] : Infinity;
    for (const u of S.units) {
      const du = u.box.distanceToPoint(p);
      const want = u.cur === 1 ? (du > s1 * (1 - HYST) ? 1 : 0) : (du > s1 * (1 + HYST) ? 1 : 0);
      if (u.fade && want === 0 && want === u.cur && this.frame % 4 === 0) for (const f of u.fade) f.node.visible = f.box.distanceToPoint(p) <= f.d;
      if (want === u.cur) continue; u.cur = want;
      for (const n of u.nodes[0]) n.visible = want === 0; for (const n of u.nodes[1]) n.visible = want === 1;
      if (u.fade && want === 0) for (const f of u.fade) f.node.visible = f.box.distanceToPoint(p) <= f.d;
      // parts present only in LOD0 (mullions, lettering, antennas) are dropped at LOD1 by design
    }
  }
  // hide the first-pass items of every shown group, show the walkway rests (js/live/world.js b3d / b3dRest)
  _swapOld() {
    const G = this.R.staticGroup; if (!G) return; let hid = 0;
    for (const o of G.children) {
      const u = o.userData || {};
      if (u.b3d) { const v = !this.loaded[u.b3d]; if (o.visible !== v) { o.visible = v; hid++; } }
      if (u.b3dRest) { const v = !!this.loaded[u.b3dRest]; if (o.visible !== v) { o.visible = v; hid++; } }
    }
    return hid;
  }
  // the loaded tower file's own anchors (root node extras.anchors, heights above grade): the tower camera and the in-cab
  // glass test follow the family on screen (F2 tower.glb / tower_lod2.glb, F1 tower_f1.glb), not the integration table
  _towerAnchors(root) {
    let an = null; root.traverse(o => { if (!an && o.userData && o.userData.anchors && o.userData.anchors.cab_eye_h != null) an = o.userData.anchors; });
    if (!an) return;
    const c = an.cab_centre_world_xz || (this.tower && this.tower.cab_centre_world_xz); if (!c) return;
    this.tower = { ...(this.tower || {}), cab_centre_world_xz: c, cab_floor_h: an.cab_floor_h, cab_eye_h: an.cab_eye_h,
      glass_h: [an.glass_sill_h, an.glass_head_h], glass_head_r: an.glass_head_r, family: an.family, eye_world: [c[0], 3.0 + an.cab_eye_h, c[1]] };
  }
  // the app's tower view (js/live/app.js: rig.setTower over world.towerPos, at towerPos.eyeY when set, else GROUND_Y + 62)
  // moves to the loaded family's cab eye; towerPos is read when the view is chosen, so the array is updated in place
  _towerCamera() {
    const W = this.R.world, T = this.tower; if (!W || !W.towerPos || !T || !T.eye_world) return;
    W.towerPos[0] = T.eye_world[0]; W.towerPos[2] = T.eye_world[2]; W.towerPos.eyeY = T.eye_world[1];
  }
  // environment hook: retune a glow kind at run time (kind: hall | office | station | roofglass | cab | led | beacon | soffit;
  // color: linear RGB, k: level in lamp units x nightE; cap: the soft cap of all kinds but the beacon); returns the values
  setGlow(kind, { color, k, cap } = {}) {
    if (cap != null) this.glowCap.value = cap;
    const G = this.glow[kind]; if (!G) return null;
    if (color) G.color.value.setRGB(color[0], color[1], color[2]); if (k != null) G.k.value = k;
    return { color: G.color.value.toArray(), k: G.k.value, cap: this.glowCap.value };
  }
  info() {
    const lod = { 0: 0, 1: 0, 2: 0 }; for (const S of this.sets) { if (S.cur2) lod[2]++; else for (const u of S.units) lod[u.cur || 0]++; }
    return { mode: this.mode, tower: this.towerFamily, loaded: Object.keys(this.loaded), kind: { ...this.kind }, pending: this.pending, failed: this.failed, done: this.done, sets: this.sets.length, unitsAtLod: lod,
      landsideUnits: Object.keys(this.units), stats: this.stats };
  }
}

// one geometry from meshes of one vertex layout, in the frame `inv` (the LOD node's inverse world matrix): positions
// and tangents by the matrix, normals by its normal matrix, triangle order flipped for mirrored meshes
function mergeInto(list, inv) {
  const G0 = list[0].geometry; const names = Object.keys(G0.attributes);
  let nv = 0, ni = 0; for (const o of list) { nv += o.geometry.attributes.position.count; ni += o.geometry.index.count; }
  const out = new THREE.BufferGeometry(); const arrs = {};
  for (const n of names) { const a = G0.attributes[n]; const C = a.array.constructor; arrs[n] = new THREE.BufferAttribute(new C(nv * a.itemSize), a.itemSize, a.normalized); }
  const idx = nv > 65535 ? new Uint32Array(ni) : new Uint16Array(ni);
  const M = new THREE.Matrix4(), N = new THREE.Matrix3(), v = new THREE.Vector3();
  let ov = 0, oi = 0;
  for (const o of list) {
    const G = o.geometry; M.multiplyMatrices(inv, o.matrixWorld); N.getNormalMatrix(M); const flip = M.determinant() < 0;
    const cnt = G.attributes.position.count;
    for (const n of names) {
      const a = G.attributes[n], b = arrs[n], s = a.itemSize;
      if (n === 'position') for (let i = 0; i < cnt; i++) { v.fromBufferAttribute(a, i).applyMatrix4(M); b.setXYZ(ov + i, v.x, v.y, v.z); }
      else if (n === 'normal') for (let i = 0; i < cnt; i++) { v.fromBufferAttribute(a, i).applyMatrix3(N).normalize(); b.setXYZ(ov + i, v.x, v.y, v.z); }
      else if (n === 'tangent') for (let i = 0; i < cnt; i++) { v.set(a.getX(i), a.getY(i), a.getZ(i)).transformDirection(M); b.setXYZW(ov + i, v.x, v.y, v.z, a.getW(i) * (flip ? -1 : 1)); }
      else for (let i = 0; i < cnt; i++) for (let c = 0; c < s; c++) b.setComponent(ov + i, c, a.getComponent(i, c));
    }
    const I = G.index;
    for (let i = 0; i < I.count; i += 3) { const a = I.getX(i), b = I.getX(i + 1), c = I.getX(i + 2); idx[oi++] = ov + a; idx[oi++] = ov + (flip ? c : b); idx[oi++] = ov + (flip ? b : c); }
    ov += cnt;
  }
  for (const n of names) out.setAttribute(n, arrs[n]);
  out.setIndex(new THREE.BufferAttribute(idx, 1)); out.computeBoundingBox(); out.computeBoundingSphere();
  return out;
}
