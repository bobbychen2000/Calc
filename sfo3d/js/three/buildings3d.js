// Blender building assets (data/buildings3d/*.glb; docs/research/buildings3d.md) in the three.js renderer: loads the
// four groups (control tower, International Terminal, domestic terminals, landside), switches their levels of detail
// per building from the camera distance, applies the baked ambient occlusion (glTF occlusionTexture on TEXCOORD_1),
// casts and receives shadows, adds the night hooks (lit glazing, the tower's LED ribbon, obstruction lights) and hides
// the first-pass extrusions each group replaces once that group is on screen (js/live/world.js routes them into one item
// per group: data/buildings3d/integration.js, tools/blender/b3d_integrate.py). Until a group has loaded, or if it fails,
// the first-pass buildings stay: the scene never has a hole.
//
// Files (manifest.json#<group>.files): full = tower.glb (F1; ?b3dtower=f2 -> tower_f2.glb), itb.glb, domestic.glb,
// landside.glb (LOD0-2 each); lod2 = the *_lod2.glb subtrees alone (far / phone tier). The low tier (phones) loads the
// lod2 files; ?b3d=full|lod2|0 overrides (0 = first-pass buildings only, for old-vs-new comparisons). The artifact build
// serves them renamed (window.SFO_B3D_BASE, default 'data/buildings3d/'; window.SFO_B3D_EXT, default '.glb'; the phone
// artifact uses '.wasm' like the aircraft models, tools/build3/phone_artifact_page.py).
//
// LOD (each group's manifest lod rule; switch distances from the LOD nodes' extras.switch_m, scaled by the quality tier's
// `lod` range relative to the high tier's 1800 m): a "LOD set" is a node whose children are LOD0 / LOD1 / LOD2 nodes
// (tower, ITB and domestic: the root; landside: every building node). LOD2 is shown when the camera is beyond its switch
// distance from the set's bounding box; otherwise LOD0 or LOD1 per unit (domestic: extras.building; ITB: per part, the
// group spans 650 m; tower and landside buildings: the whole set), from the distance to the unit's bounding box (the
// nearest point, not the node origin: a 400-m pier seen from its tip is near), with 5 % hysteresis.
//
// Materials: glTF PBR as exported (GLTFLoader: MeshStandard / MeshPhysical with KHR_materials_ior / _specular), turned
// into node materials so an emission term can be added: night glow = nightE (renderer3: night factor x LAMP_M, lamp
// units -> sky units) x GLOW[kind].color x GLOW[kind].k x per-bay variation (+-15 %, 3-m cells, as objects.js does for
// the concourses), masked to the panes where the glass has a base-colour tile (mullions / frit stay dark). Kinds by
// material name / extras (the assets' own tags): hall (terminal glazing), office (hotel, CAC, station-block window bands,
// the tower's base building and shaft slots: 55 % of the bays lit, as objects.js punched windows), station (AirTrain
// station glass), roofglass (skylights, glazed roof lines, the T1 glass canopy: lit from below, weaker), cab (tower cab:
// dim, controllers keep it dark), led (tower ribbon, extras.led: the LED waterfall as objects.js id 16), beacon (red
// obstruction light, extras.obstruction_light).
// GLOW values are uniforms (Buildings3D.glow) so the environment work can retune them; inferred, not measured.
//
// Physical plausibility: the assets were checked against the stands, bridges, aircraft envelopes and taxiways by their
// groups and together by tools/blender/b3d_integrate.py (data/buildings3d/integration.json#plausibility).
import { THREE, TSL } from './lib.js';
import { hash12 } from './tsl/common.js';
import { B3D_INTEGRATION } from '../../data/buildings3d/integration.js';
const { uniform, vec2, vec3, float, mix, smoothstep, sin, floor, positionWorld, luminance, texture, uv, materialEmissive } = TSL;

export const B3D_GROUPS = ['tower', 'itb', 'domestic', 'landside'];
const FILES = { full: { tower: 'tower', itb: 'itb', domestic: 'domestic', landside: 'landside' }, lod2: { tower: 'tower_lod2', itb: 'itb_lod2', domestic: 'domestic_lod2', landside: 'landside_lod2' } };
const HYST = 0.05, LOD_REF = 1800; // QUALITY3.high.lod
// night glow per kind (lamp units, x renderer3 nightE): colour of the light behind the glass and its level. hall = the
// concourse level of objects.js (vec3(1, 0.9, 0.76) x ~0.45-2.2 x 0.8, mean ~0.8); office / station / roof / cab / LED /
// beacon as objects.js ids 6, 1, 5, 12, 16, 14. Inferred (no measured SFO night luminances).
const GLOW_DEF = {
  hall: [[1.0, 0.9, 0.76], 0.8], office: [[1.0, 0.82, 0.6], 0.9], station: [[0.95, 0.95, 1.0], 0.9], roofglass: [[1.0, 0.9, 0.76], 0.35],
  cab: [[0.25, 0.4, 0.35], 0.25], led: [[1.0, 1.0, 1.0], 1.0], beacon: [[1.0, 0.06, 0.04], 40.0],
};

function glowKind(m) {
  const n = (m.name || '').replace(/@.*$/, '').replace(/\.L\d$/, ''); const ex = m.userData || {};
  if (ex.obstruction_light || n === 'red_light') return 'beacon';
  if (ex.led) return 'led';
  if (n === 'cab_glass') return 'cab';
  if (/^(glass_roof|glass_roof_under|glass_sky|glass_canopy)$/.test(n)) return 'roofglass';
  if (/^(glass_hyatt|glass_band|cac_wall|slot|slot_glass|ribbon)$/.test(n) || /^ibf_(curtain|glass)/.test(n)) return 'office';
  if (/^station_glass$/.test(n)) return 'station';
  if (/glass|curtain/.test(n)) return 'hall';
  return null;
}

export class Buildings3D {
  // R: js/three/renderer3.js Renderer3 (engine, staticGroup, nightE, time, Q, tier, world)
  constructor(R) {
    const qs = new URLSearchParams(location.search);
    this.R = R; this.E = R.engine;
    const q = qs.get('b3d');
    this.mode = q === '0' || q === 'off' ? 'off' : q === 'lod2' || q === 'full' ? q : (R.tier === 'low' ? 'lod2' : 'full');
    this.towerFamily = qs.get('b3dtower') === 'f2' ? 'f2' : 'f1';
    this.base = window.SFO_B3D_BASE || 'data/buildings3d/'; this.ext = window.SFO_B3D_EXT || '.glb';
    this.lodScale = (R.Q && R.Q.lod ? R.Q.lod : LOD_REF) / LOD_REF;
    this.group = new THREE.Group(); this.group.name = 'buildings3d'; this.E.scene.add(this.group);
    this.loaded = {}; this.failed = {}; this.sets = []; this.cabGlass = []; this.stats = { files: {}, ms: {} };
    this.glow = {}; for (const [k, [c, v]] of Object.entries(GLOW_DEF)) this.glow[k] = { color: uniform(new THREE.Color(...c)), k: uniform(v) };
    this.done = this.mode === 'off'; this.frame = 0; this._tmpV = new THREE.Vector3(); this._tex = new Map();
    this.tower = B3D_INTEGRATION.tower || null;
  }
  start() {
    if (this.mode === 'off') { console.log('[b3d] off (?b3d=0): first-pass buildings'); return; }
    this._p = this._loadAll().catch(e => console.warn('[b3d] load', e)).finally(() => { this.done = true; });
  }
  url(g) {
    let f = FILES[this.mode][g];
    if (g === 'tower' && this.mode === 'full' && this.towerFamily === 'f2') f = 'tower_f2';
    return this.base + f + this.ext;
  }
  async _loadAll() {
    // sequential: one decode + upload + compile at a time (phones; the main thread stalls once per group, not four
    // times at once); the tower first (smallest, and the tower view), the landside last (largest, mostly far away)
    const loader = new THREE.GLTFLoader();
    for (const g of B3D_GROUPS) {
      const t0 = performance.now();
      try {
        const gltf = await loader.loadAsync(this.url(g));
        const root = gltf.scene; root.name = 'b3d_' + g;
        this._prepare(g, root);
        const t1 = performance.now();
        await this._compile(root);
        this.group.add(root); this.loaded[g] = root;
        this._swapOld();
        if (g === 'tower') this._towerCamera();
        this.stats.ms[g] = [Math.round(t1 - t0), Math.round(performance.now() - t1)];
        console.log('[b3d] ' + g + ' (' + this.url(g) + ') shown: load+prepare ' + this.stats.ms[g][0] + ' ms, compile ' + this.stats.ms[g][1] + ' ms; ' + this.stats.files[g].tris + ' tris in ' + this.stats.files[g].meshes + ' meshes');
      } catch (e) { this.failed[g] = String(e && e.message || e); console.warn('[b3d] ' + g + ' failed, first-pass buildings kept:', e); }
    }
  }
  // compile the group's programs before it is shown (all LODs and units, whatever the current view), so the first
  // frames after a LOD switch do not stall
  async _compile(root) {
    const E = this.E; const saved = [];
    root.traverse(o => { saved.push([o, o.visible, o.frustumCulled]); o.visible = true; o.frustumCulled = false; });
    try { await Promise.race([E.renderer.compileAsync(root, E.camera, E.scene), new Promise(r => setTimeout(r, 20000))]); }
    catch (e) { console.warn('[b3d] compileAsync', e); }
    for (const [o, v, f] of saved) { o.visible = v; o.frustumCulled = f; }
  }
  _prepare(g, root) {
    const R = this.R, Q = R.Q || {}; let tris = 0, meshes = 0; const mats = new Map();
    root.updateMatrixWorld(true);
    root.traverse(o => {
      o.matrixAutoUpdate = false;
      if (!o.isMesh) return;
      meshes++; const idx = o.geometry.index; tris += (idx ? idx.count : o.geometry.attributes.position.count) / 3 * (o.isInstancedMesh ? o.count : 1);
      const m0 = o.material; let m = mats.get(m0);
      if (!m) { m = this._material(m0, Q); mats.set(m0, m); }
      o.material = m;
      const transp = m.transparent || m.blending !== THREE.NormalBlending && m.blending !== THREE.NoBlending;
      o.castShadow = !transp && !(o.isInstancedMesh && R.tier === 'low'); o.receiveShadow = true;
      if (/^cab_glass/.test(m0.name || '')) this.cabGlass.push(o);
    });
    this.stats.files[g] = { url: this.url(g), tris: Math.round(tris), meshes, materials: mats.size };
    this._lodSets(g, root);
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
      const key = t.source.uuid + '|' + t.channel + '|' + t.colorSpace + '|' + t.wrapS + t.wrapT + '|' + t.offset.toArray() + t.repeat.toArray() + t.rotation;
      let c = this._tex.get(key); if (!c) { c = t; c.anisotropy = Math.max(c.anisotropy || 1, Q.aniso || 4); this._tex.set(key, c); }
      m[k] = c;
    }
    const kind = glowKind(m0); m.userData.b3dGlow = kind;
    if (kind) {
      const G = this.glow[kind], R = this.R; const night = R.nightE || uniform(0);
      const cell = floor(positionWorld.xz.div(3.0)); const hv = hash12(cell.add(vec2(13.0, 7.0)));
      let k = G.k.mul(night).mul(hv.mul(0.3).add(0.85)); let col = G.color;
      if (kind === 'office') k = k.mul(smoothstep(0.43, 0.47, hash12(cell.add(vec2(3.0, 29.0)))));
      if (kind === 'led') { // objects.js id 16: a blue-cyan wave running down the ribbon
        const wave = sin(positionWorld.y.mul(0.21).sub((R.time || uniform(0)).mul(0.9))).mul(0.45).add(0.55);
        k = k.mul(wave.mul(0.8).add(1.4)); col = mix(vec3(0.15, 0.45, 1.0), vec3(0.2, 0.9, 0.9), wave).mul(G.color);
      }
      // panes only: a base-colour tile carries the frames / frit (lighter); untextured glass glows over its whole face
      const mask = m.map ? float(1.0).sub(smoothstep(0.12, 0.35, luminance(texture(m.map, uv(m.map.channel || 0)).rgb))) : float(1.0);
      m.emissiveNode = materialEmissive.add(col.mul(k).mul(mask));
    }
    return m;
  }
  // LOD sets and units (see the header)
  _lodSets(g, root) {
    const lodIx = (o) => { const ex = o.userData || {}; if (Number.isInteger(ex.lod)) return ex.lod; const m = /^LOD(\d)(_|$)/.exec(o.name || ''); return m ? +m[1] : null; };
    const sw = (o) => { const s = (o.userData || {}).switch_m; return Array.isArray(s) ? +s[0] : (s != null ? +s : null); };
    root.traverse(P => {
      const lods = {}; for (const c of P.children) { const k = lodIx(c); if (k != null && /^LOD\d/.test(c.name || '')) lods[k] = c; }
      if (Object.keys(lods).length < 2) return;
      const S = { group: g, node: P, lods, sw: {}, box: new THREE.Box3(), units: [], cur2: null };
      for (const [k, n] of Object.entries(lods)) S.sw[k] = (sw(n) ?? { 0: 0, 1: 400, 2: 1400 }[k]) * this.lodScale;
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
        }
      }
      S.units = [...units.values()];
      // start: everything hidden except LOD2 (update() sets the real state on the next frame)
      for (const [k, n] of Object.entries(lods)) n.visible = +k === 2;
      this.sets.push(S);
    });
  }
  // per frame (renderer3 frameScene): LOD switching; the cab glass is hidden while the camera is inside the cab
  update(camPos) {
    this.frame++;
    if (this.frame % 120 === 0 && Object.keys(this.loaded).length) this._swapOld(); // items synced later
    if (!camPos || !this.sets.length) return;
    const p = this._tmpV.set(camPos[0], camPos[1], camPos[2]);
    for (const S of this.sets) {
      const d = S.box.distanceToPoint(p); const s2 = S.sw[2];
      const far = s2 != null && S.lods[2] ? (S.cur2 ? d > s2 * (1 - HYST) : d > s2 * (1 + HYST)) : false;
      if (far !== S.cur2) { S.cur2 = far; if (S.lods[2]) S.lods[2].visible = far; if (S.lods[0]) S.lods[0].visible = !far; if (S.lods[1]) S.lods[1].visible = !far; }
      if (far) continue;
      const s1 = S.sw[1] != null ? S.sw[1] : Infinity;
      for (const u of S.units) {
        const du = u.box.distanceToPoint(p);
        const want = u.cur === 1 ? (du > s1 * (1 - HYST) ? 1 : 0) : (du > s1 * (1 + HYST) ? 1 : 0);
        if (want === u.cur) continue; u.cur = want;
        for (const n of u.nodes[0]) n.visible = want === 0; for (const n of u.nodes[1]) n.visible = want === 1;
        // parts present only in LOD0 (mullions, lettering, antennas) are dropped at LOD1 by design
      }
    }
    // in-cab tower camera: the alpha-blended cab glass would darken the whole view (manifest.json#tower.integration)
    if (this.cabGlass.length && this.tower && this.tower.cab_centre_world_xz) {
      const c = this.tower.cab_centre_world_xz, g = 3.0; // GROUND_Y
      const inCab = Math.hypot(p.x - c[0], p.z - c[1]) < 9.0 && p.y > g + (this.tower.cab_floor_h || 60) - 0.5 && p.y < g + (this.tower.glass_h ? this.tower.glass_h[1] : 65) + 1.5;
      if (inCab !== this._inCab) { this._inCab = inCab; for (const o of this.cabGlass) o.material.visible = !inCab; }
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
  // the app's tower view (js/live/app.js: rig.setTower at GROUND_Y + 62 over world.towerPos) moves to the asset's cab
  // eye (x, z); towerPos is read when the view is chosen, so the array is updated in place
  _towerCamera() {
    const W = this.R.world, T = this.tower; if (!W || !W.towerPos || !T || !T.eye_world) return;
    W.towerPos[0] = T.eye_world[0]; W.towerPos[2] = T.eye_world[2];
  }
  // environment hook: retune a glow kind at run time (kind: hall | office | station | roofglass | cab | led | beacon;
  // color: linear RGB, k: level in lamp units x nightE); returns the current values
  setGlow(kind, { color, k } = {}) {
    const G = this.glow[kind]; if (!G) return null;
    if (color) G.color.value.setRGB(color[0], color[1], color[2]); if (k != null) G.k.value = k;
    return { color: G.color.value.toArray(), k: G.k.value };
  }
  info() {
    const lod = { 0: 0, 1: 0, 2: 0 }; for (const S of this.sets) { if (S.cur2) lod[2]++; else for (const u of S.units) lod[u.cur || 0]++; }
    return { mode: this.mode, tower: this.towerFamily, loaded: Object.keys(this.loaded), failed: this.failed, done: this.done, sets: this.sets.length, unitsAtLod: lod, stats: this.stats };
  }
}
