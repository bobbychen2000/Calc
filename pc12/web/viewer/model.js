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
export const PRIMER_HEX = 0xb4bea5;   // light grey-green zinc-chromate-ish primer
const LINING_HEX = 0xdcd6cb;          // cabin lining (matches the 'lining' material)

export function loadGLB(url, onProgress) {
  return new Promise((resolve, reject) => {
    new GLTFLoader().load(url, resolve, (e) => onProgress && onProgress(e), (err) => reject(err instanceof Error ? err : new Error(String(err && err.message || err))));
  });
}

// Shader patch shared by the paint / cutaway variants.  Uniform objects are shared so one
// write updates every material.  paint: mix primer -> livery behind a sweep plane along Z
// (the "spray" wipe, nose to tail).  lining: back faces (seen from inside a clipped skin)
// take the cabin lining colour.
function patchMaterial(mat, U, { paint = false, lining = false }) {
  if (!paint && !lining) return mat;
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
    sh.vertexShader = vs;
    sh.fragmentShader = fs;
  };
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' : ''}`;
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
  diffuseColor.a = mix(0.035, 0.42, pow(fres, 2.5));`);
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
      sel: makeOverlay(accent, 0.34), selCut: makeOverlay(accent, 0.34, { clip: this.clipPlanes }),
      ghost: makeOverlay(accent, 0.13, { depthTest: false }), ghostCut: makeOverlay(accent, 0.13, { depthTest: false, clip: this.clipPlanes }),
      hover: makeOverlay(0xffb020, 0.22), hoverCut: makeOverlay(0xffb020, 0.22, { clip: this.clipPlanes }),
    };
    this.overlays = { sel: [], hover: [] };
    this.selected = null;
    this.hovered = null;

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
        const base = ch.material;
        const name = base.name || '';
        const mr = { mesh: ch, part: rec, base, paint: PAINT_RE.test(name), glass: GLASS_RE.test(name) };
        if (mr.paint && !patched.has(base)) { patchMaterial(base, this.U, { paint: true }); patched.add(base); }
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
  }

  part(id) { return this.parts.get(id); }

  // ---------------------------------------------------------------- materials
  cutVariant(mr) {
    let m = this._cut.get(mr.base);
    if (!m) {
      m = mr.base.clone();
      m.clippingPlanes = this.clipPlanes;
      m.clipShadows = true;
      patchMaterial(m, this.U, { paint: mr.paint, lining: !mr.glass });
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
      this._glassX.set(key, m);
    }
    return m;
  }

  applyMaterials() {
    for (const mr of this.meshRecs) {
      const p = mr.part;
      const cut = this.cutaway && p.cut;
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
    this.paint.target = on ? 100 : -100;
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
  // + build fly-in (exaggerated explode + a lift for top-level parts)
  applyTransforms(explodeF) {
    for (const p of this.list) {
      const n = p.node;
      n.position.copy(p.restPos).add(p.anim.pos).addScaledVector(p.explode, explodeF + 3 * p.fly);
      if (p.fly > 0 && !p.parent) n.position.y += 0.9 * p.fly;
      n.quaternion.copy(p.anim.quat);
    }
  }

  // ---------------------------------------------------------------- highlights
  _refreshOverlays() {
    for (const kind of ['sel', 'hover']) {
      for (const o of this.overlays[kind]) {
        const cut = this.cutaway && o.userData.rec.cut;
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
            o.userData = { rec: p, ghost };
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
