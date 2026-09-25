// GLB loading, part registry, visibility and material variants
// (primer/paint sweep, cutaway clipping with lining-coloured back faces, x-ray, highlights).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Skin parts clipped by the cutaway plane (model y = 0, glTF X = 0; the port half X < 0 is removed).
export const CUT_PARTS = new Set([
  'fus_center', 'fus_fwd', 'fus_aft', 'glazing_cabin', 'glazing_flightdeck', 'door_airstair', 'door_cargo',
  'exit_hatch', 'door_frames', 'belly_fairing', 'cowl_upper', 'cowl_lower', 'chin_inlet',
  'gear_door_NR', 'gear_door_NL', 'dorsal_fin', 'structure',
]);
// Exterior shells that turn translucent in X-ray.
export const XRAY_PARTS = new Set([
  ...[...CUT_PARTS].filter((id) => id !== 'structure'),
  'wing_R', 'wing_L', 'winglet_R', 'winglet_L', 'fin', 'rudder', 'rudder_tab', 'stabilizer',
  'elevator_R', 'elevator_L', 'tail_bullet', 'flap_R', 'flap_L', 'aileron_R', 'aileron_L', 'ail_tab_R',
  'ail_tab_L', 'flap_fairings', 'strakes', 'radar_pod',
]);
// Parts that sit inside the skin (for the "use X-ray / cutaway" hint).
export const INTERNAL_PARTS = new Set([
  'structure', 'eng_rgb', 'eng_exhaust', 'eng_pt', 'eng_combustor', 'eng_compressor', 'eng_inlet_screen',
  'eng_agb', 'engine_mount', 'firewall', 'inlet_duct', 'flight_deck', 'cabin_interior', 'gear_bays',
]);
const SHADOW_CASTERS = /^(gear_|blade_|propeller|brace_|exhaust_stacks|antennas|pitot|lights)/;

const PAINT_RE = /^(paint_|trim_black$)/;
const GLASS_RE = /^glass/;
export const PRIMER_HEX = 0x9fae8c;   // light grey-green zinc-chromate-ish primer
const LINING_HEX = 0xdcd6cb;          // cabin lining (matches the 'lining' material)

export function loadGLB(url, onProgress) {
  return new Promise((resolve, reject) => {
    new GLTFLoader().load(url, resolve, (e) => onProgress && onProgress(e), (err) => reject(err instanceof Error ? err : new Error(String(err && err.message || err))));
  });
}

// Shader patch shared by the paint / cutaway / glass variants.  Uniform objects are shared so one
// write updates every material.  paint: mix primer -> livery behind a sweep plane along Z
// (the "spray" wipe, nose to tail).  lining: back faces (seen from inside a clipped skin)
// take the cabin lining colour.  glass: the tinted panes are double-sided with outward winding
// (checked), so back faces are the view from inside the cabin -- make them nearly clear.
function patchMaterial(mat, U, { paint = false, lining = false, glass = false }) {
  if (!paint && !lining && !glass) return mat;
  mat.onBeforeCompile = (sh) => {
    let vs = sh.vertexShader, fs = sh.fragmentShader;
    if (paint) {
      sh.uniforms.uPaintSweep = U.paintSweep;
      sh.uniforms.uPrimer = U.primer;
      vs = 'varying float vPaintZ;\n' + vs.replace('#include <project_vertex>',
        '#include <project_vertex>\n  vPaintZ = (modelMatrix * vec4(transformed, 1.0)).z;');
      fs = 'uniform float uPaintSweep;\nuniform vec3 uPrimer;\nvarying float vPaintZ;\n' + fs
        .replace('#include <color_fragment>', `#include <color_fragment>
  float paintK = smoothstep(-1.2, 1.2, uPaintSweep - vPaintZ);
  diffuseColor.rgb = mix(uPrimer, diffuseColor.rgb, paintK);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(0.66, roughnessFactor, paintK);
  metalnessFactor = mix(0.0, metalnessFactor, paintK);`);
    }
    if (lining) {
      sh.uniforms.uLining = U.lining;
      fs = 'uniform vec3 uLining;\n' + fs.replace('#include <normal_fragment_begin>',
        `if (!gl_FrontFacing) { diffuseColor.rgb = uLining; roughnessFactor = 0.85; metalnessFactor = 0.0; }
#include <normal_fragment_begin>`);
    }
    if (glass) {
      // transparent double-sided materials are drawn in two passes (BackSide, then FrontSide); the
      // back pass has FLIP_SIDED defined (and gl_FrontFacing flipped), so test the defines
      fs = fs.replace('#include <alphamap_fragment>', `#include <alphamap_fragment>
  #if defined( FLIP_SIDED )
    diffuseColor.a *= 0.2;
  #elif defined( DOUBLE_SIDED )
    if (!gl_FrontFacing) diffuseColor.a *= 0.2;
  #endif`);
    }
    sh.vertexShader = vs;
    sh.fragmentShader = fs;
  };
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' : ''}${glass ? 'G' : ''}`;
  mat.needsUpdate = true;
  return mat;
}

// Translucent "ghost" material: fresnel-weighted alpha, no depth write.
function makeXray(clipPlanes) {
  const m = new THREE.MeshStandardMaterial({
    color: 0x9fb6cc, roughness: 0.35, metalness: 0.0, transparent: true, opacity: 0.1,
    depthWrite: false, side: THREE.DoubleSide, emissive: 0x2a4460, emissiveIntensity: 0.25,
  });
  if (clipPlanes) m.clippingPlanes = clipPlanes;
  m.onBeforeCompile = (sh) => {
    sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  float fres = 1.0 - abs(dot(normalize(normal), normalize(vViewPosition)));
  diffuseColor.a = mix(0.05, 0.5, pow(fres, 2.2));`);
  };
  m.customProgramCacheKey = () => 'pc12:xray';
  return m;
}

function makeOverlay(color, opacity, { depthTest = true, clip = null } = {}) {
  const m = new THREE.MeshBasicMaterial({
    color, transparent: true, opacity, depthWrite: false, depthTest, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2, fog: false,
  });
  if (clip) m.clippingPlanes = clip;
  return m;
}
const noRaycast = () => {};
const _g = new THREE.Vector3();

export class Model {
  constructor(gltf, meta) {
    this.root = gltf.scene;
    this.meta = meta;
    this.parts = new Map();           // id -> part record
    this.list = [];                   // part records, parents before children
    this.meshRecs = [];
    this.meshToPart = new Map();
    this.pickables = [];
    this.U = {
      paintSweep: { value: 100 },
      primer: { value: new THREE.Color(PRIMER_HEX) },
      lining: { value: new THREE.Color(LINING_HEX) },
    };
    this.clipPlanes = [new THREE.Plane(new THREE.Vector3(1, 0, 0), 0)];
    this.cutaway = false;
    this.xray = false;
    this.structureOn = false;
    this.isolate = null;              // Set of part ids or null
    this.paint = { target: 100, cur: 100 };
    this._cut = new Map();
    this._glassX = new Map();
    this.xrayMat = makeXray(null);
    this.xrayCutMat = makeXray(this.clipPlanes);
    const accent = 0x1d7bff;
    this.ov = {
      sel: makeOverlay(accent, 0.24), selCut: makeOverlay(accent, 0.24, { clip: this.clipPlanes }),
      ghost: makeOverlay(accent, 0.08, { depthTest: false }), ghostCut: makeOverlay(accent, 0.08, { depthTest: false, clip: this.clipPlanes }),
      hover: makeOverlay(0xffb020, 0.22), hoverCut: makeOverlay(0xffb020, 0.22, { clip: this.clipPlanes }),
    };
    this.overlays = { sel: [], hover: [] };
    this.selected = null;
    this.hovered = null;
    this.groundY = 0;                 // ground drop needed so exploded parts stay above the grid

    const stepIndex = new Map(meta.steps.map((s, i) => [s.key, i]));
    const patched = new Set();
    // register parts in traversal order (parents first)
    this.root.traverse((o) => {
      const ex = o.userData;
      if (!ex || !ex.part) return;
      let parent = o.parent, prec = null;
      while (parent) { if (parent.userData && parent.userData.part) { prec = this.parts.get(parent.userData.part); break; } parent = parent.parent; }
      const rec = {
        id: ex.part, node: o, ex, parent: prec, children: [],
        restPos: o.position.clone(),
        anim: { pos: new THREE.Vector3(), quat: new THREE.Quaternion() },
        explode: new THREE.Vector3().fromArray(ex.explode || [0, 0, 0]),
        fly: 0, buildVisible: true, userHidden: false, shown: true,
        stepIndex: stepIndex.has(ex.step) ? stepIndex.get(ex.step) : 0,
        meshes: [], extras: [],
        cut: CUT_PARTS.has(ex.part), xray: XRAY_PARTS.has(ex.part),
      };
      if (prec) prec.children.push(rec);
      this.parts.set(rec.id, rec);
      this.list.push(rec);
    });
    for (const rec of this.list) {
      for (const ch of rec.node.children) {
        if (!ch.isMesh) continue;
        let base = ch.material;
        const name = base.name || '';
        if (rec.id === 'structure') {
          // frames / stringers / rib caps nearly coincide with the skins: push them back in depth
          // (own clones, so gear_bays keeps the shared zinc_chromate) to stop the skins z-fighting
          base = base.clone();
          base.polygonOffset = true;
          base.polygonOffsetFactor = 2;
          base.polygonOffsetUnits = 8;
          ch.material = base;
        }
        const mr = { mesh: ch, part: rec, base, paint: PAINT_RE.test(name), glass: GLASS_RE.test(name),
          // structure: clip the fuselage frames/stringers but keep the wing spars & ribs whole
          cut: rec.cut && !(rec.id === 'structure' && name === 'interior_green') };
        if (mr.paint && !patched.has(base)) { patchMaterial(base, this.U, { paint: true }); patched.add(base); }
        if (mr.glass && !patched.has(base)) { patchMaterial(base, this.U, { glass: true }); patched.add(base); }
        ch.castShadow = rec.xray || SHADOW_CASTERS.test(rec.id);
        ch.receiveShadow = false;
        rec.meshes.push(mr);
        this.meshRecs.push(mr);
        this.meshToPart.set(ch, rec);
        this.pickables.push(ch);
      }
    }
    this.root.updateMatrixWorld(true);
    this.box = new THREE.Box3().setFromObject(this.root);
    this._restGeometry();
  }

  // Rest-pose data used by the build fly-in, the ground drop and the camera fit (all node rotations
  // are identity at rest, so world offsets are plain sums of node positions).
  _restGeometry() {
    const tmp = new THREE.Box3(), wp = new THREE.Vector3();
    this.restLowest = Infinity;
    for (const p of this.list) {
      p.restBox = new THREE.Box3();
      for (const mr of p.meshes) {
        const g = mr.mesh.geometry;
        if (!g.boundingBox) g.computeBoundingBox();
        p.restBox.union(tmp.copy(g.boundingBox).applyMatrix4(mr.mesh.matrixWorld));
      }
      p.restMinY = p.restBox.isEmpty() ? Infinity : p.restBox.min.y;
      if (p.restMinY < this.restLowest) this.restLowest = p.restMinY;
    }
    for (const p of this.list) {
      // children of the spinning propeller (blades): lowest point over a revolution, and their
      // (radial) explode vector can point straight down at some phase
      const par = p.parent;
      p.spin = !!(par && par.ex.pivot && par.ex.pivot.kind === 'spin' && !p.restBox.isEmpty());
      if (p.spin) {
        const o = par.ex.pivot.origin, ax = new THREE.Vector3().fromArray(par.ex.pivot.axis).normalize();
        let rmax = 0;
        for (let i = 0; i < 8; i++) {
          wp.set(i & 1 ? p.restBox.max.x : p.restBox.min.x, i & 2 ? p.restBox.max.y : p.restBox.min.y, i & 4 ? p.restBox.max.z : p.restBox.min.z);
          wp.x -= o[0]; wp.y -= o[1]; wp.z -= o[2];
          wp.addScaledVector(ax, -wp.dot(ax));
          rmax = Math.max(rmax, wp.length());
        }
        p.spinMinY = o[1] - rmax;
        p.explodeR = p.explode.length();
      }
      // Build fly-in.  A part with an explode vector flies in from 3 x explode (+ a lift for top-level
      // parts), clamped so it never starts below the ground.  Parts without one (glazing, door frames,
      // bays, braces, firewall, interior, small details) would otherwise just drop through what is
      // already built, so they grow in place about their centre instead.
      const sameStepParent = par && par.stepIndex === p.stepIndex;
      p.grow = p.explode.lengthSq() < 1e-10 && !sameStepParent;
      p.flyVec = new THREE.Vector3();
      p.growC = new THREE.Vector3();
      if (p.grow) {
        const sub = new THREE.Box3();
        for (const id of this.descendants(p.id)) { const q = this.parts.get(id); if (q.stepIndex === p.stepIndex) sub.union(q.restBox); }
        p.node.getWorldPosition(wp);
        if (!sub.isEmpty()) sub.getCenter(p.growC).sub(wp);     // centre in the node frame
        p.startY = 0;
      } else {
        p.flyVec.copy(p.explode).multiplyScalar(3);
        if (!par) p.flyVec.y += 0.9;
        const baseY = sameStepParent && !par.grow ? par.startY : 0;
        if (Number.isFinite(p.restMinY)) p.flyVec.y = Math.max(p.flyVec.y, -(p.restMinY + baseY));
        p.startY = baseY + p.flyVec.y;
      }
    }
  }

  // ~4000 vertices sampled from every mesh (world, rest pose) for silhouette-tight camera fits
  silhouettePoints(target = 4000) {
    let total = 0;
    for (const mr of this.meshRecs) total += mr.mesh.geometry.attributes.position.count;
    const stride = Math.max(1, Math.floor(total / target));
    const out = [], v = new THREE.Vector3();
    for (const mr of this.meshRecs) {
      const pos = mr.mesh.geometry.attributes.position;
      for (let i = 0; i < pos.count; i += stride) {
        v.fromBufferAttribute(pos, i).applyMatrix4(mr.mesh.matrixWorld);
        out.push(v.x, v.y, v.z);
      }
    }
    return new Float32Array(out);
  }

  part(id) { return this.parts.get(id); }

  // ---------------------------------------------------------------- materials
  cutVariant(mr) {
    let m = this._cut.get(mr.base);
    if (!m) {
      m = mr.base.clone();
      m.clippingPlanes = this.clipPlanes;
      m.clipShadows = true;
      patchMaterial(m, this.U, { paint: mr.paint, lining: !mr.glass, glass: mr.glass });
      this._cut.set(mr.base, m);
    }
    return m;
  }

  glassXray(mr, cut) {
    const key = mr.base.uuid + (cut ? 'c' : '');
    let m = this._glassX.get(key);
    if (!m) {
      m = mr.base.clone();
      m.opacity = 0.35;
      m.depthWrite = false;
      if (cut) m.clippingPlanes = this.clipPlanes;
      patchMaterial(m, this.U, { glass: true });
      this._glassX.set(key, m);
    }
    return m;
  }

  applyMaterials() {
    for (const mr of this.meshRecs) {
      const p = mr.part;
      const cut = this.cutaway && mr.cut;
      let m = mr.base;
      if (this.xray && p.xray) {
        m = mr.glass ? this.glassXray(mr, cut) : (cut ? this.xrayCutMat : this.xrayMat);
      } else if (cut) {
        m = this.cutVariant(mr);
      }
      mr.mesh.material = m;
      mr.mesh.castShadow = (p.xray && !this.xray) || SHADOW_CASTERS.test(p.id);
    }
    this._refreshOverlays();
  }

  setCutaway(on) { this.cutaway = !!on; this.applyMaterials(); }
  setXray(on) { this.xray = !!on; this.applyMaterials(); }

  // paint sweep: target +100 = fully painted, -100 = all primer; animated in update()
  setPaint(on, instant) {
    const target = on ? 100 : -100;
    if (target === this.paint.target && (instant ? this.paint.cur === target : true)) return;
    this.paint.target = target;
    if (instant) { this.paint.cur = this.paint.target; this.U.paintSweep.value = this.paint.cur; }
    else if (Math.abs(this.paint.cur) > 50) {
      // start the sweep just outside the aircraft (nose for painting, tail for stripping)
      this.paint.cur = on ? -2.5 : 17.5;
      this.U.paintSweep.value = this.paint.cur;
    }
  }
  get painted() { return this.paint.target > 0; }

  updatePaint(dt) {
    const p = this.paint;
    if (p.cur === p.target) return false;
    const speed = 7.5; // m/s along the fuselage
    if (p.target > 0) {
      p.cur = Math.min(p.cur + speed * dt, 18);
      if (p.cur >= 18) p.cur = p.target;
    } else {
      p.cur = Math.max(p.cur - speed * dt, -3);
      if (p.cur <= -3) p.cur = p.target;
    }
    this.U.paintSweep.value = p.cur;
    return true;
  }

  // ---------------------------------------------------------------- visibility
  updateVisibility() {
    for (const p of this.list) {
      let shown = p.buildVisible && !p.userHidden;
      if (shown && this.isolate) shown = this.isolate.has(p.id);
      if (shown && p.id === 'structure') shown = this.structureOn;
      p.shown = shown;
      for (const mr of p.meshes) mr.mesh.visible = shown;
    }
  }

  descendants(id, out = new Set()) {
    const p = this.parts.get(id);
    if (!p) return out;
    out.add(id);
    for (const c of p.children) this.descendants(c.id, out);
    return out;
  }

  setIsolate(id) {
    this.isolate = id ? this.descendants(id) : null;
    this.updateVisibility();
  }

  // ---------------------------------------------------------------- transforms
  // node = rest + animation offset (parent frame) + explode (hierarchical, parent frame)
  // + build fly-in (flyVec, see _restGeometry) or grow-in (scale about the part centre).
  // Also works out how far the ground has to drop so no exploded part sits below it
  // (rest-frame estimate, stable while things animate; blades use their spin envelope).
  applyTransforms(explodeF) {
    let lowest = Infinity;
    for (const p of this.list) {
      const n = p.node;
      n.position.copy(p.restPos).add(p.anim.pos).addScaledVector(p.explode, explodeF);
      n.quaternion.copy(p.anim.quat);
      let oy = (p.parent ? p.parent._oy : 0) + p.explode.y * explodeF;
      if (p.fly > 0 && p.grow) {
        const s = Math.max(1e-3, 1 - p.fly);
        n.scale.setScalar(s);
        _g.copy(p.growC).applyQuaternion(p.anim.quat).multiplyScalar(1 - s);
        n.position.add(_g);
      } else {
        if (n.scale.x !== 1) n.scale.setScalar(1);
        if (p.fly > 0) { n.position.addScaledVector(p.flyVec, p.fly); oy += p.flyVec.y * p.fly; }
      }
      p._oy = oy;
      if (p.shown && p.meshes.length) {
        const m = p.spin ? p.spinMinY + p.parent._oy - p.explodeR * explodeF : p.restMinY + oy;
        if (m < lowest) lowest = m;
      }
    }
    this.groundY = Number.isFinite(lowest) ? Math.min(0, lowest - Math.min(0, this.restLowest)) : 0;
  }

  // ---------------------------------------------------------------- highlights
  _refreshOverlays() {
    for (const kind of ['sel', 'hover']) {
      for (const o of this.overlays[kind]) {
        const cut = this.cutaway && o.userData.mr.cut;
        o.material = kind === 'hover' ? (cut ? this.ov.hoverCut : this.ov.hover)
          : o.userData.ghost ? (cut ? this.ov.ghostCut : this.ov.ghost) : (cut ? this.ov.selCut : this.ov.sel);
      }
    }
  }

  setHighlight(kind, id) {
    const cur = kind === 'sel' ? this.selected : this.hovered;
    if (cur === id) return false;
    for (const o of this.overlays[kind]) o.parent && o.parent.remove(o);
    this.overlays[kind] = [];
    if (kind === 'sel') this.selected = id; else this.hovered = id;
    if (id && this.parts.has(id)) {
      for (const pid of this.descendants(id)) {
        const p = this.parts.get(pid);
        for (const mr of p.meshes) {
          const layers = kind === 'sel' ? [false, true] : [false];
          for (const ghost of layers) {
            const o = new THREE.Mesh(mr.mesh.geometry, this.ov.sel);
            o.userData = { mr, ghost };
            o.raycast = noRaycast;
            o.renderOrder = ghost ? 10 : 5;
            o.castShadow = false;
            mr.mesh.add(o);
            this.overlays[kind].push(o);
          }
        }
      }
    }
    this._refreshOverlays();
    return true;
  }

  worldBox(id, out = new THREE.Box3()) {
    out.makeEmpty();
    const p = this.parts.get(id);
    if (!p) return out;
    this.root.updateMatrixWorld(true);
    const tmp = new THREE.Box3();
    for (const pid of this.descendants(id)) {
      for (const mr of this.parts.get(pid).meshes) {
        const g = mr.mesh.geometry;
        if (!g.boundingBox) g.computeBoundingBox();
        tmp.copy(g.boundingBox).applyMatrix4(mr.mesh.matrixWorld);
        out.union(tmp);
      }
    }
    return out;
  }
}
